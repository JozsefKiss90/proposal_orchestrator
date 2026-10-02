"""
Dev-graph shadow comparison — the planner's advisory against the reuse
decision the scheduler actually recorded.

An operator names an advisory plan and a run. The comparison reads the plan
and the run manifest's ``reuse_decisions`` and emits one diagnostic from the
closed set :data:`DIAGNOSTICS`:

* ``agreed`` — for every compared node the planner and the scheduler reach
  the same verdict;
* ``planner_narrower`` — the planner would retain something the scheduler
  reran (planner ``reuse``, scheduler ``rerun``);
* ``planner_broader`` — the planner would rerun something the scheduler
  retained (planner ``rerun``, scheduler ``reuse``). This is the finding
  that matters for the whole-Tier-3 fingerprint's safety, so it outranks
  ``planner_narrower`` when both occur; every row is kept.

Verdicts, all lookups over declared data:

* **Scheduler**: a recorded decision with status ``reused`` is ``reuse``;
  ``not_reused`` is ``rerun``.
* **Planner**: when the plan says nothing changed, ``reuse`` for every
  node. Otherwise the run records whose path is the node's artifact path
  are looked up in the plan's entries: any ``rerun`` action is ``rerun``;
  only ``reuse-under-policy`` (or no entry, unaffected) is ``reuse``; no
  run record at all is ``rerun``, because the planner cannot vouch for an
  artifact it has no dependency record for.
* **Binding**: a node is compared through its artifact path — the path the
  reused decision itself carries, else the caller's ``artifact_paths``,
  else the reuse layer's eligibility table. A node with no binding is a
  refusal, not a silent skip.

Shadow mode. Nothing consumes the diagnostic at runtime: the scheduler
does not read it, no gate predicate reads it, and this module writes no
reuse metadata and no run manifest. The whole-Tier-3 reuse fingerprint
stays the sole authority over what executes; the comparison only records
where the two would have differed.

Constitutional authority:
    Subordinate to CLAUDE.md. Writes only the comparison under Tier 4
    dev_graph/shadow_comparisons through :func:`write_shadow_comparison`.
    Evaluates no gate, invokes no Claude, invents no facts (§13.3).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from runner.atomic_write import atomic_write_json
from runner.dev_graph.identity import HASH_PREFIX, content_hash
from runner.dev_graph.impact import (
    IMPACT_PLANS_REL,
    PLAN_SCHEMA_ID,
    ImpactPlan,
    plan_identity,
    plan_nothing_changed,
)
from runner.dev_graph.schema import DevGraphError
from runner.run_context import (
    PRESERVED_RUN_RECORD_SCHEMA_ID,
    PRESERVED_RUN_RECORDS_REL,
    RUN_MANIFEST_FILENAME,
    RUNS_DIR_REL,
    is_plain_run_id,
    run_id_slug,
)

SHADOW_SCHEMA_ID = "orch.dev_graph.shadow_comparison.v1"

_DEV_GRAPH = "docs/tier4_orchestration_state/dev_graph"
#: One immutable comparison per comparison id.
SHADOW_COMPARISONS_REL = f"{_DEV_GRAPH}/shadow_comparisons"
#: The operator request the writer reads: ``{"plan_id": ..., "run_id": ...}``.
SHADOW_REQUEST_REL = f"{_DEV_GRAPH}/shadow_request.json"
#: The run manifest layout, the run id rule and the preserved-record layout
#: are owned by ``runner.run_context`` and imported from there, so a move
#: cannot leave this reader silently pointing at nothing. Read here, never
#: written. The live layout is addressed only with a plain run id; a run
#: whose id breaks the rule is reachable only through the record
#: ``tools/preserve_run_manifests.py`` writes under its slug.
_RUNS_DIR_REL = RUNS_DIR_REL
_RUN_MANIFEST = RUN_MANIFEST_FILENAME

DIAGNOSTICS: frozenset[str] = frozenset({"agreed", "planner_narrower", "planner_broader"})
VERDICTS: frozenset[str] = frozenset({"rerun", "reuse"})
_DECISION_STATUSES: Mapping[str, str] = {"reused": "reuse", "not_reused": "rerun"}
_RANK: Mapping[str, int] = {"agreed": 0, "planner_narrower": 1, "planner_broader": 2}

#: Node ids and reuse-decision keys. The same shape as ``RUN_ID_RE`` in
#: ``runner.run_context`` by coincidence, not by contract: a node id is a
#: manifest concept and a run id a directory name, and they may diverge.
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_SHORT_HEX = 16


@dataclass(frozen=True)
class ShadowComparison:
    """An immutable diagnostic with a content-derived identity."""

    comparison_id: str
    plan_id: str
    run_id: str
    diagnostic: str
    rows: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": SHADOW_SCHEMA_ID,
            "comparison_id": self.comparison_id,
            "advisory": True,
            "mode": "shadow",
            "consumed_at_runtime": False,
            "plan_id": self.plan_id,
            "run_id": self.run_id,
            "diagnostic": self.diagnostic,
            "rows": list(self.rows),
        }


def _refuse(kind: str, offender: str, message: str) -> DevGraphError:
    return DevGraphError(kind, offender, message)


# ---------------------------------------------------------------------------
# Inputs (validation is pure)
# ---------------------------------------------------------------------------


def _plan_dict(plan: Any) -> dict[str, Any]:
    if isinstance(plan, ImpactPlan):
        plan = plan.to_dict()
    if not isinstance(plan, Mapping):
        raise _refuse("malformed_record", "plan", f"plan is not a mapping ({type(plan).__name__})")
    if plan.get("schema_id") != PLAN_SCHEMA_ID:
        raise _refuse("malformed_record", "plan", f"plan is not a {PLAN_SCHEMA_ID} document")
    plan_id = plan.get("plan_id")
    if not isinstance(plan_id, str) or not plan_id.startswith(HASH_PREFIX):
        raise _refuse("malformed_record", "plan", "plan has no content-derived plan_id")
    if not isinstance(plan.get("nothing_changed"), bool):
        raise _refuse("malformed_record", plan_id, "plan has no boolean nothing_changed")
    entries = plan.get("entries")
    if not isinstance(entries, list) or not all(isinstance(e, Mapping) for e in entries):
        raise _refuse("malformed_record", plan_id, "plan entries must be a list of objects")
    return dict(plan)


def _decisions(raw: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(raw, Mapping):
        raise _refuse("malformed_record", "reuse_decisions", "reuse_decisions must be a mapping")
    if not raw:
        raise _refuse("no_reuse_decision", "reuse_decisions", "no reuse decision recorded for the run")
    out: dict[str, dict[str, Any]] = {}
    for node_id in sorted(raw):
        dec = raw[node_id]
        if not isinstance(node_id, str) or not _ID_RE.match(node_id):
            raise _refuse("malformed_record", str(node_id), "reuse decision key is not a plain node id")
        if not isinstance(dec, Mapping) or dec.get("status") not in _DECISION_STATUSES:
            raise _refuse(
                "malformed_record", node_id, f"{node_id}: reuse decision status must be one of {sorted(_DECISION_STATUSES)}"
            )
        out[node_id] = dict(dec)
    return out


def _default_artifact_paths() -> dict[str, str]:
    """The reuse layer's eligibility table, read as data. Imported lazily so
    the pure comparison carries no runtime dependency when a binding is
    passed in."""
    from runner.phase8_reuse import REUSE_ELIGIBLE_NODES

    return {node_id: cfg["artifact_path"] for node_id, cfg in REUSE_ELIGIBLE_NODES.items()}


# ---------------------------------------------------------------------------
# Public entry point (pure)
# ---------------------------------------------------------------------------


def _planner_verdict(plan: Mapping[str, Any], artifact_path: str) -> tuple[str, list[str], list[str], str]:
    """``(verdict, record_ids, actions, detail)`` for one artifact path."""
    if plan["nothing_changed"]:
        return "reuse", [], [], "the advisory says nothing changed"
    matching = [e for e in plan["entries"] if e.get("kind") in ("artifact", "check") and e.get("path") == artifact_path]
    if not matching:
        return "rerun", [], [], "no run record for this artifact; the planner cannot vouch for reuse"
    record_ids = sorted({str(e["id"]) for e in matching})
    actions = sorted({str(e.get("action")) for e in matching})
    if "rerun" in actions:
        return "rerun", record_ids, actions, "the advisory says rerun"
    return "reuse", record_ids, actions, "the advisory retains the result only under an explicit policy"


def compare_shadow(
    plan: ImpactPlan | Mapping[str, Any],
    reuse_decisions: Mapping[str, Mapping[str, Any]],
    *,
    run_id: str,
    artifact_paths: Mapping[str, str] | None = None,
) -> ShadowComparison:
    """Compare the advisory *plan* with the scheduler's *reuse_decisions*.

    *run_id* names the compared run inside the artifact; it is never used
    as a path here, so an id that is not a plain identifier is recorded as
    it is rather than refused (the reader decides where such a run's
    manifest can be found).

    Raises :class:`DevGraphError` with kind ``malformed_record`` on a plan
    or decision of the wrong shape, ``no_reuse_decision`` on an empty
    decision set, ``malformed_request`` on an empty run id or a node with
    no artifact binding. Deterministic: identical inputs yield an identical
    comparison and id.
    """
    plan_doc = _plan_dict(plan)
    decisions = _decisions(reuse_decisions)
    if not isinstance(run_id, str) or not run_id:
        raise _refuse("malformed_request", str(run_id), "run_id must be a non-empty string")
    bindings = dict(_default_artifact_paths() if artifact_paths is None else artifact_paths)

    rows: list[dict[str, Any]] = []
    for node_id, dec in decisions.items():
        path = dec.get("artifact_path") if isinstance(dec.get("artifact_path"), str) else bindings.get(node_id)
        if not path:
            raise _refuse("malformed_request", node_id, f"{node_id}: no artifact path bound for comparison")
        scheduler = _DECISION_STATUSES[dec["status"]]
        planner, record_ids, actions, detail = _planner_verdict(plan_doc, path)
        if planner == scheduler:
            diagnostic = "agreed"
        elif planner == "reuse":
            diagnostic = "planner_narrower"
        else:
            diagnostic = "planner_broader"
        rows.append(
            {
                "node_id": node_id,
                "artifact_path": path,
                "scheduler_status": dec["status"],
                "scheduler": scheduler,
                "planner": planner,
                "planner_actions": actions,
                "record_ids": record_ids,
                "diagnostic": diagnostic,
                "detail": detail,
            }
        )

    diagnostic = max((r["diagnostic"] for r in rows), key=_RANK.__getitem__)
    comparison_id = content_hash(
        {"plan_id": plan_doc["plan_id"], "run_id": run_id, "diagnostic": diagnostic, "rows": rows}
    )
    return ShadowComparison(
        comparison_id=comparison_id,
        plan_id=plan_doc["plan_id"],
        run_id=run_id,
        diagnostic=diagnostic,
        rows=rows,
    )


# ---------------------------------------------------------------------------
# The registered writer
# ---------------------------------------------------------------------------


def _read_json(path: Path, rel: str, kind: str) -> Any:
    if not path.is_file():
        raise _refuse("malformed_request", rel, f"{kind} not found")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise _refuse("malformed_record", rel, f"unreadable JSON: {exc}") from exc


def read_shadow_request(repo_root: Path) -> tuple[str, str]:
    """``(plan_id, run_id)`` named by :data:`SHADOW_REQUEST_REL`."""
    raw = _read_json(Path(repo_root) / SHADOW_REQUEST_REL, SHADOW_REQUEST_REL, "shadow request file")
    if not isinstance(raw, dict) or not isinstance(raw.get("plan_id"), str) or not isinstance(raw.get("run_id"), str):
        raise _refuse("malformed_request", SHADOW_REQUEST_REL, "expected an object with a plan_id and a run_id")
    return raw["plan_id"], raw["run_id"]


def read_plan(repo_root: Path, plan_id: str) -> dict[str, Any]:
    """The stored advisory plan, checked against its own id. A plan whose
    content no longer hashes to its id is refused."""
    if not isinstance(plan_id, str) or not plan_id.startswith(HASH_PREFIX):
        raise _refuse("malformed_request", str(plan_id), "plan_id is not a content hash")
    rel = f"{IMPACT_PLANS_REL}/{plan_id[len(HASH_PREFIX):][:_SHORT_HEX]}/plan.json"
    doc = _plan_dict(_read_json(Path(repo_root) / rel, rel, "advisory plan"))
    if doc["plan_id"] != plan_id or plan_identity(doc) != plan_id:
        raise _refuse("malformed_record", rel, "stored plan does not hash to the requested plan id")
    cs = doc.get("change_set")
    origins = doc.get("origins")
    if isinstance(cs, Mapping) and isinstance(origins, list):
        if plan_nothing_changed(cs, origins) != doc["nothing_changed"]:
            raise _refuse("malformed_record", rel, "stored plan's nothing_changed contradicts its change set")
    return doc


def locate_run_manifest(repo_root: Path, run_id: str) -> str:
    """The repo-relative path of the manifest for *run_id*, or refuse.

    A plain identifier addresses the live manifest under
    ``.claude/runs/<run_id>/`` and nothing else: the id is a directory name
    there, and a stale Tier 4 copy must not stand in for a live manifest
    that is simply absent. An id that is not a plain identifier cannot be
    spelled into that path at all, so it is served from the record
    ``tools/preserve_run_manifests.py`` writes under the id's slug, which
    carries the true run id inside and is checked against the one asked
    for. A run not held where its id says is a ``malformed_request``.
    """
    if not isinstance(run_id, str) or not run_id:
        raise _refuse("malformed_request", str(run_id), "run_id must be a non-empty string")
    root = Path(repo_root)
    if is_plain_run_id(run_id):
        live = f"{_RUNS_DIR_REL}/{run_id}/{_RUN_MANIFEST}"
        if (root / live).is_file():
            return live
        raise _refuse("malformed_request", live, "run manifest not found")
    preserved = f"{PRESERVED_RUN_RECORDS_REL}/{run_id_slug(run_id)}.json"
    if (root / preserved).is_file():
        return preserved
    raise _refuse(
        "malformed_request",
        preserved,
        f"run id is not a plain identifier and no preserved run record exists at {preserved}",
    )


def read_reuse_decisions(repo_root: Path, run_id: str) -> dict[str, Any]:
    """The ``reuse_decisions`` map recorded for *run_id*. A plain read: the
    manifest is never written from here.

    The manifest is the one :func:`locate_run_manifest` names. A preserved
    record must carry the preserved schema id and name the run asked for,
    else it is ``malformed_record``. A manifest that records no decision
    — no key, or a null or empty map — is ``no_reuse_decision``: a fact
    about the run, not a bad request.
    """
    rel = locate_run_manifest(repo_root, run_id)
    doc = _read_json(Path(repo_root) / rel, rel, "run manifest")
    if not isinstance(doc, dict):
        raise _refuse("malformed_record", rel, "run manifest is not an object")
    if rel.startswith(PRESERVED_RUN_RECORDS_REL):
        if doc.get("schema_id") != PRESERVED_RUN_RECORD_SCHEMA_ID:
            raise _refuse("malformed_record", rel, f"preserved run record is not a {PRESERVED_RUN_RECORD_SCHEMA_ID} document")
        if doc.get("run_id") != run_id:
            raise _refuse("malformed_record", rel, f"preserved run record names a different run: {doc.get('run_id')!r}")
    decisions = doc.get("reuse_decisions")
    if decisions is None:
        what = "preserved run record" if rel.startswith(PRESERVED_RUN_RECORDS_REL) else "run manifest"
        raise _refuse("no_reuse_decision", rel, f"{what} records no reuse decision")
    return decisions


def write_shadow_comparison(repo_root: Path) -> list[Path]:
    """Compare the plan and run named by the request; write the comparison.

    Returns the one absolute path written. The directory is named by the
    first sixteen hex characters of the comparison id, so the same plan
    against the same recorded decisions lands on the same path with the
    same bytes. Refuses before writing anything when the plan or the run
    manifest is missing or malformed.
    """
    root = Path(repo_root)
    plan_id, run_id = read_shadow_request(root)
    plan = read_plan(root, plan_id)
    comparison = compare_shadow(plan, read_reuse_decisions(root, run_id), run_id=run_id)
    target = root / SHADOW_COMPARISONS_REL / comparison.comparison_id[len(HASH_PREFIX):][:_SHORT_HEX] / "comparison.json"
    atomic_write_json(comparison.to_dict(), target)
    return [target]


def run_shadow_comparison_writer(run_id: str, repo_root: Path) -> list[Path]:
    """Component adapter: ``(run_id, repo_root) -> written``. The component's
    run id does not enter the artifact; the compared run is the one the
    request names."""
    del run_id
    return write_shadow_comparison(repo_root)
