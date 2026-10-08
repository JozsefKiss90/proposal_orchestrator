"""
The original-to-successor diff of two ESR comparisons (ticket R05).

PE-08 wrote one comparison. R03 adjudicated seven of its rows and R05 records
the reviewed reading as a *successor* dispositions record and a second
comparison. Both comparisons stay on disk: the first is what the operator read
and the second is what the review recommends. A reader needs to see what moved
between them without diffing two 2,700-line JSON files by eye.

What this module measures
-------------------------
Everything. It declares nothing. The two comparisons are written artifacts;
this reads them, re-hashes them, and reports the difference:

* **Bindings.** Both must be over the same frozen baseline report, the same ESR
  record and the same candidate, and must cover the same observation ids. A
  comparison against another baseline is not a successor of this one, and
  diffing the two would present two readings of different evidence as a
  revision of one. Refused, nothing written.
* **Rows.** Per observation: the disposition and its status, the declared
  preservation status, the lanes credited, the blind and audit citations, the
  register pointers, the quoted passages, whether the explanation moved,
  whether the proposed revision moved, and whether a revision plan was added.
* **Counts.** Every figure of the summary, before and after, recomputed by
  neither side: both were computed by ``esr_comparison`` from its own rows.
* **Priorities.** The rank each open shortcoming holds in the two revision
  artifacts, found beside each comparison under the name it recorded.
* **Retention.** Every ESR shortcoming must still be open in the successor
  unless its row is ``addressed``. A shortcoming that left the revision list
  any other way is a flag: the harness missing a point is not a reason to stop
  proposing the fix (ticket R05 item 7).

The score comparison must be identical in both: it derives from the baseline
and the ESR record, which the bindings already pin, and no assessor runs here.
A difference means the inputs are not what they claim, so it is refused.

Outputs
-------
``review_diff_<sha12>_<NNNN>.json`` and ``review_diff_<sha12>_<NNNN>.md``,
sharing a sequence number, under the output directory; ``<sha12>`` is the
*successor* comparison's hash. Nothing is overwritten.

Constitutional standing: an advisory Tier 4 artifact, never run-blocking. It
evaluates no gate, invokes no Claude and coins no ``schema_id``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from runner.atomic_write import atomic_write_json, atomic_write_text

from harness.blind_assessment import BlindAssessmentError, next_report_path
from harness.blind_baseline import _portable
from harness.esr_comparison import (
    DISPOSITION_ADDRESSED,
    OBSERVATION_KIND_STRENGTH,
    POINTER_RESOLUTION_IDENTITY,
    pointer_rule_of,
    load_comparison,
)
from harness.evidence_preflight import file_sha256

DIFF_RECORD_TYPE = "esr_comparison_diff"
DIFF_SCHEMA_VERSION = "1.0"

_DIFF_PREFIX = "review_diff"
_MARKDOWN_SUFFIX = ".md"

#: The row fields the diff compares, in report order.
ROW_FIELDS: tuple[str, ...] = (
    "disposition",
    "disposition_status",
    "evidence_preserved_status",
    "detected_by",
    "blind_findings",
    "audit_findings",
    "evidence_basis",
    "evidence_basis_values",
    "current_proposal_evidence",
    "explanation",
    "proposed_revision",
    "revision_plan",
    "priority",
    "review_status",
    "failure_mode",
    "deferred_to_private_network",
)

#: The fields a successor written under dispositions schema 1.2 (the PE-08
#: operator approval) may carry, compared only when the successor declares the
#: identity pointer rule, so an older pair keeps the diff shape it was written
#: with. ``evidence_basis_values`` is the V02 case: a pointer whose text did not
#: move but whose resolved value did.
_APPROVAL_FIELDS: tuple[str, ...] = ("review_status", "failure_mode", "deferred_to_private_network")

_NOTE = (
    "Advisory to a human, never run-blocking. This artifact declares nothing: "
    "every line is a difference measured between two written comparisons. "
    "Which reading is right is the operator's decision, and neither comparison "
    "records one."
)


class ComparisonDiffError(BlindAssessmentError):
    """Two comparisons that cannot be diffed; nothing is written."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Loading: a comparison and the revisions artifact it recorded
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LoadedComparison:
    """A written comparison, its hash, and the revisions artifact beside it."""

    path: Path
    sha256: str
    data: Mapping[str, Any]
    revisions_path: Path
    revisions_sha256: str
    revisions: Mapping[str, Any]

    @property
    def rows(self) -> dict[str, Mapping[str, Any]]:
        return {str(r["observation_id"]): r for r in self.data.get("rows") or []}

    @property
    def priorities(self) -> dict[str, int | None]:
        """The rank each observation holds in the open revision list."""
        return {
            str(e["observation_id"]): e.get("priority")
            for e in self.revisions.get("open") or []
        }


def load_pair_member(path: Path | str, *, what: str) -> LoadedComparison:
    """Load one comparison and the revisions artifact it names beside it.

    The comparison records its revisions artifact as an absolute path from the
    run that wrote it, so the *name* is what carries over and the directory is
    the comparison's own. A comparison whose companion is missing cannot have
    its priorities compared, and a partial diff would be the quieter failure.
    """
    p = Path(path)
    data = load_comparison(p)
    recorded = data.get("revisions_artifact")
    if not isinstance(recorded, str) or not recorded.strip():
        raise ComparisonDiffError(f"the {what} comparison {p} names no revisions artifact.")
    revisions_path = p.parent / Path(recorded).name
    if not revisions_path.is_file():
        raise ComparisonDiffError(
            f"the {what} comparison names revisions artifact {revisions_path.name}, "
            f"which is not beside it in {p.parent}."
        )
    revisions = json.loads(revisions_path.read_text(encoding="utf-8-sig"))
    if revisions.get("record_type") != "esr_revision_priorities":
        raise ComparisonDiffError(
            f"{revisions_path} is not an 'esr_revision_priorities' record."
        )
    return LoadedComparison(
        path=p,
        sha256=file_sha256(p),
        data=data,
        revisions_path=revisions_path,
        revisions_sha256=file_sha256(revisions_path),
        revisions=revisions,
    )


def _bind(before: LoadedComparison, after: LoadedComparison) -> dict[str, Any]:
    """Refuse a pair that is not two readings of one body of evidence."""
    checks = (
        ("baseline report", ("baseline", "report_sha256")),
        ("ESR record", ("esr_record", "sha256")),
        ("candidate", ("candidate", "candidate_hash")),
    )
    for name, (outer, inner) in checks:
        a = (before.data.get(outer) or {}).get(inner)
        b = (after.data.get(outer) or {}).get(inner)
        if a != b:
            raise ComparisonDiffError(
                f"the two comparisons are over different {name}s "
                f"({str(a)[:19]} vs {str(b)[:19]}); a successor shares its predecessor's evidence."
            )
    if before.sha256 == after.sha256:
        raise ComparisonDiffError(
            f"both paths name the same comparison ({before.sha256[:12]}); there is nothing to diff."
        )
    missing = sorted(set(before.rows) - set(after.rows))
    added = sorted(set(after.rows) - set(before.rows))
    if missing or added:
        raise ComparisonDiffError(
            "the two comparisons cover different observations"
            + (f"; dropped: {', '.join(missing)}" if missing else "")
            + (f"; added: {', '.join(added)}" if added else "")
            + "."
        )
    if before.data.get("score_comparison") != after.data.get("score_comparison"):
        raise ComparisonDiffError(
            "the score comparison differs between the two reports. Both derive from the "
            "same baseline and ESR record and no assessor ran here, so a difference "
            "means an input is not what it claims."
        )
    return {
        "baseline_report_sha256": (before.data.get("baseline") or {}).get("report_sha256"),
        "esr_record_sha256": (before.data.get("esr_record") or {}).get("sha256"),
        "candidate_hash": (before.data.get("candidate") or {}).get("candidate_hash"),
        "observations": len(before.rows),
    }


# --------------------------------------------------------------------------- #
# Row comparison: the citation sets reduced to comparable keys
# --------------------------------------------------------------------------- #


def blind_key(ref: Mapping[str, Any]) -> str:
    """One blind citation as a stable, readable key."""
    kind = str(ref.get("kind"))
    if kind in ("criterion_shortcoming", "criterion_strength"):
        return f"{kind}:{ref.get('criterion_id')}:sample{ref.get('sample_index')}:{ref.get('index')}"
    if kind == "cell_member":
        return f"cell_member:{ref.get('expectation_key')}:{ref.get('member_index')}"
    return f"{kind}:{ref.get('expectation_key')}"


def audit_key(ref: Mapping[str, Any]) -> str:
    """One audit citation as a stable, readable key."""
    return f"{Path(str(ref.get('report'))).name}:{ref.get('check')}:{ref.get('index')}"


def _keys(refs: Sequence[Any], fn: Callable[[Mapping[str, Any]], str]) -> list[str]:
    return sorted({fn(r) for r in refs or []})


#: One row field reduced to the comparable key set the diff reports.
_KeySet = Callable[[Sequence[Any]], list[str]]


def _register_keys(refs: Sequence[Any]) -> list[str]:
    return sorted({str(r.get("pointer")) for r in refs or []})


def _quote_keys(refs: Sequence[Any]) -> list[str]:
    return sorted({f"{r.get('sub_section_id')}: {r.get('quote')}" for r in refs or []})


def _set_change(before: Sequence[str], after: Sequence[str]) -> dict[str, Any] | None:
    """The withdrawn and added members of one citation set, or ``None``."""
    withdrawn = [k for k in before if k not in set(after)]
    added = [k for k in after if k not in set(before)]
    if not withdrawn and not added:
        return None
    return {
        "before": list(before),
        "after": list(after),
        "withdrawn": withdrawn,
        "added": added,
    }


def _revision_of(row: Mapping[str, Any]) -> Mapping[str, Any]:
    rev = row.get("proposed_revision")
    return rev if isinstance(rev, Mapping) else {}


def _register_values(refs: Sequence[Any]) -> dict[str, Any]:
    return {str(r.get("pointer")): r.get("value") for r in refs or []}


def diff_row(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    priority_before: int | None,
    priority_after: int | None,
    extended: bool = False,
) -> dict[str, Any]:
    """One observation's row, before and after, with the fields that moved.

    *extended* compares the schema-1.2 fields as well (see
    :data:`_APPROVAL_FIELDS`); the caller sets it from the successor's own
    declared pointer rule.
    """
    rev_b, rev_a = _revision_of(before), _revision_of(after)
    fields: dict[str, Any] = {}
    scalar = ("disposition", "disposition_status", "evidence_preserved_status")
    if extended:
        scalar += _APPROVAL_FIELDS
    for key in scalar:
        if before.get(key) != after.get(key):
            fields[key] = {"before": before.get(key), "after": after.get(key)}
    if extended:
        vals_b, vals_a = _register_values(before.get("evidence_basis") or []), _register_values(
            after.get("evidence_basis") or []
        )
        moved = {
            ptr: {"before": vals_b[ptr], "after": vals_a[ptr]}
            for ptr in vals_b
            if ptr in vals_a
            and json.dumps(vals_b[ptr], sort_keys=True) != json.dumps(vals_a[ptr], sort_keys=True)
        }
        if moved:
            fields["evidence_basis_values"] = moved
    citations: tuple[tuple[str, _KeySet], ...] = (
        ("blind_findings", lambda refs: _keys(refs, blind_key)),
        ("audit_findings", lambda refs: _keys(refs, audit_key)),
        ("detected_by", lambda refs: sorted(str(x) for x in refs)),
        ("evidence_basis", _register_keys),
        ("current_proposal_evidence", _quote_keys),
    )
    for key, as_keys in citations:
        change = _set_change(as_keys(before.get(key) or []), as_keys(after.get(key) or []))
        if change is not None:
            fields[key] = change
    if before.get("explanation") != after.get("explanation"):
        fields["explanation"] = {"rewritten": True, "after": after.get("explanation")}
    if rev_b.get("text") != rev_a.get("text"):
        fields["proposed_revision"] = {"before": rev_b.get("text"), "after": rev_a.get("text")}
    plan_b, plan_a = rev_b.get("revision_plan"), rev_a.get("revision_plan")
    if plan_b != plan_a:
        fields["revision_plan"] = {
            "state": "added" if plan_b is None else "withdrawn" if plan_a is None else "changed",
            "after": plan_a,
        }
    if priority_before != priority_after:
        fields["priority"] = {"before": priority_before, "after": priority_after}
    return {
        "observation_id": str(after["observation_id"]),
        "criterion_id": after.get("criterion_id"),
        "kind": after.get("kind"),
        "historical_finding": after.get("historical_finding"),
        "changed": [f for f in ROW_FIELDS if f in fields],
        "changes": fields,
    }


# --------------------------------------------------------------------------- #
# Counts and retention
# --------------------------------------------------------------------------- #


def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
    """A nested summary flattened to ``a/b/c`` keys, leaves only."""
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, sub in value.items():
            out.update(_flatten(sub, f"{prefix}/{key}" if prefix else str(key)))
        return out
    return {prefix: value}


def diff_counts(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    """Every leaf of the two summaries, and the ones that moved.

    Every leaf, with no exception for the prose the summary carries: a changed
    basis sentence or rate note is a change to how a figure is to be read, and
    a diff that hid it would report "no count moved" over a summary that says
    something else.
    """
    flat_b, flat_a = _flatten(before), _flatten(after)
    moved = {
        key: {"before": flat_b.get(key), "after": flat_a.get(key)}
        for key in sorted(set(flat_b) | set(flat_a))
        if flat_b.get(key) != flat_a.get(key)
    }
    return {"changed": moved, "before": before, "after": after}


def check_retention(
    after: LoadedComparison, rows: Mapping[str, Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    """Every ESR shortcoming must still carry a revision in the successor.

    A row whose point the harness missed is still a point the evaluators made.
    The only ground for leaving the revision list is ``addressed`` — the
    revision already happened — and such a row is listed as closed rather than
    dropped. Anything else is a flag.
    """
    open_ids = set(after.priorities)
    closed_ids = {str(e["observation_id"]) for e in after.revisions.get("closed") or []}
    dropped: list[dict[str, Any]] = []
    flags: list[str] = []
    for oid, row in rows.items():
        if row.get("kind") == OBSERVATION_KIND_STRENGTH:
            continue
        if oid in open_ids:
            continue
        entry = {
            "observation_id": oid,
            "disposition": row.get("disposition"),
            "listed_as_closed": oid in closed_ids,
        }
        dropped.append(entry)
        if row.get("disposition") != DISPOSITION_ADDRESSED:
            flags.append(
                f"{oid} is a shortcoming the successor leaves out of the revision list "
                f"with disposition {row.get('disposition')!r}; only 'addressed' closes a row."
            )
    return dropped, flags


# --------------------------------------------------------------------------- #
# The diff
# --------------------------------------------------------------------------- #


def diff_comparisons(
    before: LoadedComparison,
    after: LoadedComparison,
    *,
    repo_root: Path | str | None = None,
    clock: Callable[[], str] | None = None,
) -> dict[str, Any]:
    """Bind the pair, diff every row and every count, and flag what is left open."""
    bindings = _bind(before, after)
    rows_b, rows_a = before.rows, after.rows
    pri_b, pri_a = before.priorities, after.priorities
    extended = pointer_rule_of(after.data) == POINTER_RESOLUTION_IDENTITY
    rows = [
        diff_row(
            rows_b[oid], rows_a[oid],
            priority_before=pri_b.get(oid), priority_after=pri_a.get(oid),
            extended=extended,
        )
        for oid in rows_a
    ]
    changed = [r for r in rows if r["changed"]]
    unchanged = [r["observation_id"] for r in rows if not r["changed"]]
    dropped, flags = check_retention(after, rows_a)
    counts = diff_counts(before.data.get("summary") or {}, after.data.get("summary") or {})

    def side(c: LoadedComparison) -> dict[str, Any]:
        return {
            "comparison": _portable(c.path, repo_root),
            "comparison_sha256": c.sha256,
            "revisions": _portable(c.revisions_path, repo_root),
            "revisions_sha256": c.revisions_sha256,
            "dispositions": (c.data.get("dispositions") or {}).get("path"),
            "dispositions_sha256": (c.data.get("dispositions") or {}).get("sha256"),
            "review_state": (c.data.get("review_state") or {}).get("state"),
            "fidelity_register_sha256": (c.data.get("fidelity_register") or {}).get("sha256"),
            "audits": [a.get("path") for a in c.data.get("audits") or []],
            "compared_at": c.data.get("compared_at"),
        }

    return {
        "record_type": DIFF_RECORD_TYPE,
        "schema_version": DIFF_SCHEMA_VERSION,
        "metric": "esr_comparison_diff",
        "advisory": True,
        "blocking": False,
        "diffed_at": (clock or _utc_now)(),
        "bindings": bindings,
        "predecessor": side(before),
        "successor": side(after),
        "score_comparison_unchanged": True,
        "rows_changed": len(changed),
        "rows_unchanged": unchanged,
        "rows": changed,
        "counts": counts,
        "shortcomings_left_out_of_the_revision_list": dropped,
        "flags": flags,
        "notes": _NOTE,
    }


def write_diff(diff: Mapping[str, Any], out_dir: Path | str) -> tuple[Path, Path]:
    """Write the diff as JSON and as Markdown; never overwrite either."""
    out = Path(out_dir)
    sha = str(diff["successor"]["comparison_sha256"])
    target = next_report_path(out, "sha256:" + sha, prefix=_DIFF_PREFIX)
    seq = target.stem.rsplit("_", 1)[1]
    markdown = out / f"{_DIFF_PREFIX}_{sha[:12]}_{seq}{_MARKDOWN_SUFFIX}"
    if markdown.exists():
        raise ComparisonDiffError(f"{markdown} already exists; nothing overwritten.")
    out.mkdir(parents=True, exist_ok=True)
    data = dict(diff)
    data["writes"] = [(out / target.name).as_posix(), (out / markdown.name).as_posix()]
    atomic_write_text(render_diff(data), markdown, prefix="review_diff_")
    atomic_write_json(data, target, prefix="review_diff_")
    return target, markdown


def load_diff(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8-sig"))
    if data.get("record_type") != DIFF_RECORD_TYPE:
        raise ComparisonDiffError(f"{p} is not an {DIFF_RECORD_TYPE!r} record.")
    if data.get("advisory") is not True or data.get("blocking") is not False:
        raise ComparisonDiffError(f"diff {p} must carry advisory=true and blocking=false.")
    return data


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def _cell(value: Any) -> str:
    """One value in a Markdown table cell: pipes escaped, newlines flattened."""
    if value is None:
        return "—"
    if isinstance(value, (list, tuple)):
        return ", ".join(_cell(v) for v in value) if value else "—"
    text = str(value).replace("|", "\\|").replace("\n", " ").strip()
    return text or "—"


def _truncate(text: str, limit: int = 160) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def render_diff(diff: Mapping[str, Any]) -> str:
    """The diff as the Markdown a reviewer reads. LF throughout."""
    lines: list[str] = []
    add = lines.append
    pre, suc = diff["predecessor"], diff["successor"]
    add("# ESR comparison: predecessor to successor")
    add("")
    add(f"Generated: {diff['diffed_at']}  ")
    add(_truncate(str(diff["notes"]), 400))
    add("")
    add("## What is being compared")
    add("")
    add("| | Predecessor | Successor |")
    add("|---|---|---|")
    for label, key in (
        ("Comparison", "comparison"),
        ("sha256", "comparison_sha256"),
        ("Revisions", "revisions"),
        ("Dispositions", "dispositions"),
        ("Dispositions sha256", "dispositions_sha256"),
        ("Review state", "review_state"),
        ("Register sha256", "fidelity_register_sha256"),
        ("Audits", "audits"),
        ("Written", "compared_at"),
    ):
        add(f"| {label} | `{_cell(pre.get(key))}` | `{_cell(suc.get(key))}` |")
    add("")
    b = diff["bindings"]
    add(
        f"Both are over baseline report `{str(b['baseline_report_sha256'])[:12]}`, ESR record "
        f"`{str(b['esr_record_sha256'])[:12]}` and candidate `{str(b['candidate_hash'])[:19]}`, "
        f"and both cover all {b['observations']} observations. The criterion scores are "
        "identical in both: no assessor ran."
    )
    add("")
    add("## Counts")
    add("")
    changed = diff["counts"]["changed"]
    if not changed:
        add("No count moved.")
    else:
        add("| Figure | Before | After |")
        add("|---|---|---|")
        for key, pair in changed.items():
            add(f"| `{key}` | {_cell(pair['before'])} | {_cell(pair['after'])} |")
    add("")
    add("## Rows that moved")
    add("")
    add(f"{diff['rows_changed']} of {b['observations']} rows changed.")
    add("")
    for row in diff["rows"]:
        add(f"### {row['observation_id']} — {row['criterion_id']} ({row['kind']})")
        add("")
        add(f"> {_truncate(str(row['historical_finding']), 400)}")
        add("")
        add("| Field | Before | After |")
        add("|---|---|---|")
        for field in row["changed"]:
            change = row["changes"][field]
            if field == "explanation":
                add("| explanation | rewritten | see the successor comparison |")
            elif field == "revision_plan":
                add(f"| revision_plan | {_cell(change['state'])} | see the revisions artifact |")
            elif "withdrawn" in change:
                add(f"| {field} | {_cell(change['before'])} | {_cell(change['after'])} |")
                # A row that only lost members, or only gained them, is already
                # stated by the before/after pair; the breakdown earns its line
                # when the set moved in both directions.
                if change["withdrawn"] and change["added"]:
                    add(f"| {field} withdrawn | {_cell(change['withdrawn'])} | — |")
                    add(f"| {field} added | — | {_cell(change['added'])} |")
            else:
                add(
                    f"| {field} | {_truncate(_cell(change.get('before')), 200)} | "
                    f"{_truncate(_cell(change.get('after')), 200)} |"
                )
        add("")
    add("## Rows that did not move")
    add("")
    add(_cell(diff["rows_unchanged"]))
    add("")
    add("## Shortcomings left out of the revision list")
    add("")
    dropped = diff["shortcomings_left_out_of_the_revision_list"]
    if not dropped:
        add("None. Every ESR shortcoming still carries a proposed revision.")
    else:
        add("| Observation | Disposition | Listed as closed |")
        add("|---|---|---|")
        for entry in dropped:
            add(
                f"| {entry['observation_id']} | {_cell(entry['disposition'])} | "
                f"{'yes' if entry['listed_as_closed'] else 'no'} |"
            )
    add("")
    if diff["flags"]:
        add("## Flags")
        add("")
        for flag in diff["flags"]:
            add(f"- {flag}")
        add("")
    return "\n".join(lines) + "\n"


def render_summary(diff: Mapping[str, Any]) -> str:
    """One screen for the terminal."""
    b = diff["bindings"]
    lines = [
        f"COMPARISON DIFF  {str(diff['predecessor']['comparison_sha256'])[:12]} -> "
        f"{str(diff['successor']['comparison_sha256'])[:12]}",
        f"baseline:      {str(b['baseline_report_sha256'])[:12]}  "
        f"candidate {str(b['candidate_hash'])[:19]}",
        f"observations:  {b['observations']}  changed {diff['rows_changed']}  "
        f"unchanged {len(diff['rows_unchanged'])}",
        f"counts moved:  {len(diff['counts']['changed'])}",
        "scores:        identical in both reports; no assessor ran",
    ]
    for row in diff["rows"]:
        lines.append(f"  - {row['observation_id']}: {', '.join(row['changed'])}")
    for flag in diff["flags"]:
        lines.append(f"  ! {flag}")
    return "\n".join(lines)


__all__ = [
    "DIFF_RECORD_TYPE",
    "DIFF_SCHEMA_VERSION",
    "ROW_FIELDS",
    "ComparisonDiffError",
    "LoadedComparison",
    "audit_key",
    "blind_key",
    "check_retention",
    "diff_comparisons",
    "diff_counts",
    "diff_row",
    "load_diff",
    "load_pair_member",
    "render_diff",
    "render_summary",
    "write_diff",
]
