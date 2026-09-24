"""
Contradiction detector + rubric report — the E5c × E5d combination (E5e).

E5's two axes stay separate all the way to the report: **coverage** (E5c,
"does the section substantively address this expectation?") and **grounding**
(E5d, "is what it says traceable to grounded claims?").  This module owns the
deterministic combination rule over the two — the 2×2 grid whose headline cell
is the **high-coverage / weak-grounding contradiction**: the section answers
the evaluator's question well while the answer does not rest on grounded
claims.  A single blended score would average exactly that cell away, which is
why no blend exists anywhere in this module — structurally: :class:`RubricReport`
carries no blended field, and the renderer prints the two axes side by side.

What this module enforces, in code:

* **Deterministic combination, no judge.**  :func:`combine_axes` is arithmetic
  over one :class:`~harness.expectation_coverage.CoverageGrade` and one
  :class:`~harness.expectation_grounding.GroundingGrade`; it renders no prompt
  and invokes nothing.  The *covered* axis of the cell uses the judge's **raw
  majority** (``judge_passed``), not the clean ``passed`` — the E5b truncation
  override forces ``passed=False`` over an ``insufficient_context`` pack, and
  letting that override move a genuinely-covered expectation out of the
  contradiction column would *hide* the headline cell behind the budget.  Both
  clean bits stay on the cell and in the render, so the override remains
  visible, never silent.
* **The contradiction names its claims.**  A
  :data:`CONTRADICTION_COVERAGE_GROUNDING` finding carries the offending
  grounding rows (entry key, status, severity) — a failed confirmed
  entailment, an unresolved confirmed claim, an expectation answered only by
  assumed/inferred claims, or a budget-truncated claim set — never just a low
  number in a table.
* **Spine-awareness.**  The Tier-3 spine register
  (``call_binding/confirmation_checklist.json``) + the operator declaration
  substrate (``working_assumptions.json``) are loaded into a
  :class:`SpineRegistry`; each grading cell is cross-referenced against the
  spine facts its claims rest on (matched by ``claim_id`` token or by a
  checklist-referencing ``source_ref`` naming the token).  An expectation
  whose coverage scored well while a linked spine fact is **not Confirmed**
  (undeclared, operator-declared ``Assumed``, ``Inferred``, or ``Unresolved``)
  surfaces as a named :data:`CONTRADICTION_SPINE` finding — "Implementation
  scored well on host capacity while the host is undeclared" is a sentence in
  the report, not an inference left to the reader.
* **Advisory by construction.**  :class:`RubricReport` enforces
  ``advisory=True, blocking=False`` exactly like
  :class:`~harness.regression.RegressionReport` — a report that could block a
  run cannot be constructed, and nothing in ``runner`` imports this module
  (the standing boundary test).  The CLI's non-zero exit advises a human.

CLI: ``py -3.10 -m harness.rubric grade`` runs the profile's expectations over
their mapped frozen sections under the pinned judge (E5f owns pacing/budget);
``py -3.10 -m harness.rubric report`` re-renders a persisted report offline.
Exit codes mirror ``harness.regression``: ``0`` clean, ``1`` contradiction(s)
found (**advisory** — a human decides), ``2`` the grading/report could not run
(fail-closed).

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate; reads frozen section
    artifacts and Tier-3 state read-only, writes only harness-owned report and
    provenance files.  Never a runtime gate.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from runner.atomic_write import atomic_write_json
from runner.working_assumptions import (
    WorkingAssumptions,
    WorkingAssumptionsError,
    load_working_assumptions,
)
from harness.evidence_pack import (
    DEFAULT_PACK_TOKEN_BUDGET,
    DEFAULT_SPAN_BUDGET_FRACTION,
    EXCLUDED_OVER_BUDGET,
    EvidencePackError,
    KIND_CLAIM,
)
from harness.expectation_coverage import (
    CoverageError,
    CoverageGrade,
    grade_expectation,
)
from harness.expectation_grounding import (
    GroundingError,
    GroundingGrade,
    VerdictCache,
    derive_expectation_grounding,
)
from harness.expectations import ExpectationError, section_paths_for
from harness.judge import Judge, JudgeError, resolve_judge_config
from harness.provenance import ProvenanceLog
from harness.profile import PreEvaluationProfile
from harness.rubrics import ProfileBundle, RubricError, RubricSet, load_profile_bundle
from harness.status_faithfulness import SEVERITY_NONE, STATUS_CONFIRMED
from harness.verdict import MIN_MAJORITY_SAMPLES

__all__ = [
    "EXPECTATION_RUBRIC_METRIC",
    "RUBRIC_REPORT_RECORD_TYPE",
    "DEFAULT_CHECKLIST_PATH",
    "DEFAULT_REPORT_PATH",
    "DEFAULT_PROVENANCE_PATH",
    "SPINE_STATUSES",
    "STATUS_SPINE_CONFIRMED",
    "KIND_SPINE_IDENTITY",
    "KIND_PROJECT_DECISION",
    "CELL_COVERED_GROUNDED",
    "CELL_COVERED_UNGROUNDED",
    "CELL_UNCOVERED_GROUNDED",
    "CELL_UNCOVERED_UNGROUNDED",
    "CONTRADICTION_COVERAGE_GROUNDING",
    "CONTRADICTION_SPINE",
    "RubricReportError",
    "SpineFact",
    "SpineRegistry",
    "load_spine_registry",
    "Contradiction",
    "ExpectationCell",
    "combine_axes",
    "RubricReport",
    "build_rubric_report",
    "render_report",
    "main",
]

#: The metric name stamped on the combined report (the grid identity for E4).
EXPECTATION_RUBRIC_METRIC: str = "expectation_rubric_grid"

#: The ``record_type`` of a persisted report file.
RUBRIC_REPORT_RECORD_TYPE: str = "rubric_grade_report"

#: The Tier-3 spine register the detector cross-references (repo-relative).
DEFAULT_CHECKLIST_PATH: Path = Path(
    "docs/tier3_project_instantiation/call_binding/confirmation_checklist.json"
)

#: Default persisted-report path (CLI ``grade --out`` default; harness-owned).
DEFAULT_REPORT_PATH: Path = Path("harness/rubric_reports/rubric_report.json")

#: Default provenance trail for a CLI grading run (harness-owned).
DEFAULT_PROVENANCE_PATH: Path = Path("harness/provenance/expectation_rubric.jsonl")

#: The §12.2 validation-status vocabulary — the only statuses a spine fact may
#: carry.  Anything else is registry drift and fails the load.
SPINE_STATUSES: frozenset[str] = frozenset(
    {"Confirmed", "Inferred", "Assumed", "Unresolved"}
)

#: The one spine status that does not raise a contradiction.
STATUS_SPINE_CONFIRMED: str = "Confirmed"

#: Spine-fact kinds — the two status-carrying lists of the checklist.
KIND_SPINE_IDENTITY: str = "spine_identity"
KIND_PROJECT_DECISION: str = "project_decision"

#: The 2×2 cells.  "Covered" is the coverage judge's raw majority
#: (``judge_passed is True``); "grounded" is E5d's clean outcome.
CELL_COVERED_GROUNDED: str = "covered_grounded"
#: The headline cell: high coverage, weak grounding — the contradiction.
CELL_COVERED_UNGROUNDED: str = "covered_ungrounded"
CELL_UNCOVERED_GROUNDED: str = "uncovered_grounded"
CELL_UNCOVERED_UNGROUNDED: str = "uncovered_ungrounded"

#: Contradiction kinds.
CONTRADICTION_COVERAGE_GROUNDING: str = "high_coverage_weak_grounding"
CONTRADICTION_SPINE: str = "unconfirmed_spine_fact"


class RubricReportError(Exception):
    """The combination/report inputs are inconsistent or unusable (fail-closed)."""


def _ascii(text: str) -> str:
    """Render *text* ASCII-safe for the console (cp125x codepages survive)."""
    return str(text).encode("ascii", "backslashreplace").decode("ascii")


# --------------------------------------------------------------------------- #
# Spine registry — the Tier-3 identity spine + operator declarations
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SpineFact:
    """One status-carrying fact of the Tier-3 spine register.

    ``checklist_status`` is the §12.2 status the checklist itself records;
    ``declared`` whether an operator declaration (``working_assumptions.json``)
    backs the fact; ``effective_status`` combines the two: a checklist
    ``Confirmed`` stands, an unconfirmed-but-declared fact is ``Assumed``
    (declared, never confirmed — the D11 discipline), anything else keeps the
    checklist status.  ``unconfirmed`` is what the contradiction detector
    keys on.
    """

    fact_id: str
    kind: str
    role: str
    checklist_status: str
    declared: bool

    @property
    def effective_status(self) -> str:
        if self.checklist_status == STATUS_SPINE_CONFIRMED:
            return STATUS_SPINE_CONFIRMED
        if self.declared:
            return "Assumed"
        return self.checklist_status

    @property
    def unconfirmed(self) -> bool:
        """Whether this fact is anything other than ``Confirmed``."""
        return self.effective_status != STATUS_SPINE_CONFIRMED

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "kind": self.kind,
            "role": self.role,
            "checklist_status": self.checklist_status,
            "declared": self.declared,
            "effective_status": self.effective_status,
            "unconfirmed": self.unconfirmed,
        }


#: Word-boundary within the spine-token alphabet: ``HOST`` must not match
#: inside ``HOSTING`` or ``NON_HOST``.
def _token_pattern(fact_id: str) -> re.Pattern[str]:
    return re.compile(
        r"(?<![A-Za-z0-9_])" + re.escape(fact_id) + r"(?![A-Za-z0-9_])"
    )


@dataclass(frozen=True)
class SpineRegistry:
    """The loaded spine register, cross-checkable against grading cells.

    ``checklist_name`` is the filename a claim's ``source_ref`` must mention
    for the source-ref token bridge to apply (so a stray ``DURATION`` in an
    unrelated path never links).
    """

    facts: tuple[SpineFact, ...]
    source_path: str = ""
    checklist_name: str = "confirmation_checklist"

    def by_id(self) -> dict[str, SpineFact]:
        return {f.fact_id: f for f in self.facts}

    def unconfirmed(self) -> tuple[SpineFact, ...]:
        return tuple(f for f in self.facts if f.unconfirmed)

    def facts_for_claim(self, claim_id: str, source_ref: str) -> tuple[SpineFact, ...]:
        """The spine facts one ledger claim rests on — the deterministic bridge.

        Two link forms, both observed in the committed ledgers:

        * ``claim_id`` **is** the spine token (excellence/impact style:
          ``HOST``, ``FELLOW`` entries), or
        * ``source_ref`` references the confirmation checklist **and** names
          the token (implementation style: ``…confirmation_checklist.json
          (spine items FELLOWSHIP_TYPE, DURATION, HOST)``).
        """
        linked: list[SpineFact] = []
        ref_is_checklist = self.checklist_name in source_ref
        for fact in self.facts:
            if claim_id == fact.fact_id:
                linked.append(fact)
            elif ref_is_checklist and _token_pattern(fact.fact_id).search(source_ref):
                linked.append(fact)
        return tuple(linked)


def _spine_fact(entry: Any, kind: str, role_key: str, index: int) -> tuple[str, str, str]:
    """Extract ``(id, role, status)`` from one checklist entry, fail-closed."""
    if not isinstance(entry, Mapping):
        raise RubricReportError(f"checklist {kind}[{index}] is not an object.")
    fact_id = str(entry.get("id", "")).strip()
    if not fact_id:
        raise RubricReportError(f"checklist {kind}[{index}] has no id.")
    status = str(entry.get("status", "")).strip()
    if status not in SPINE_STATUSES:
        raise RubricReportError(
            f"checklist {kind} {fact_id!r} carries status {status!r} — not in "
            f"the §12.2 vocabulary {sorted(SPINE_STATUSES)} (registry drift; "
            "fail-closed)."
        )
    return fact_id, str(entry.get(role_key, "")), status


def load_spine_registry(
    repo_root: Path | str = Path("."),
    *,
    checklist_path: Path | str | None = None,
    working_assumptions: WorkingAssumptions | None = None,
) -> SpineRegistry:
    """Load the Tier-3 spine register + declaration overlay, fail-closed.

    Reads the checklist's two status-carrying lists (``spine_identity`` and
    ``project_decisions``) and marks each fact ``declared`` when the operator
    declaration substrate carries a matching entry (by ``checklist_ref`` or by
    declaration ``key`` — the two lookups the shared reader offers).  A
    missing/malformed checklist, an empty spine, a status outside the §12.2
    vocabulary, or a duplicate fact id raises :class:`RubricReportError` —
    spine-awareness must never silently degrade to "no spine facts".

    *working_assumptions* defaults to loading the canonical Tier-3 file under
    *repo_root* (an absent file is the honest α state, not an error).
    """
    root = Path(repo_root)
    path = Path(checklist_path) if checklist_path is not None else root / DEFAULT_CHECKLIST_PATH
    if not path.is_file():
        raise RubricReportError(
            f"spine confirmation checklist not found: {path} — the contradiction "
            "detector cannot run spine-unaware."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise RubricReportError(f"checklist {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, Mapping):
        raise RubricReportError(f"checklist {path} is not a JSON object.")

    spine_raw = data.get("spine_identity")
    if not isinstance(spine_raw, list) or not spine_raw:
        raise RubricReportError(
            f"checklist {path} has no spine_identity array — an empty spine "
            "register cannot vouch for anything."
        )
    decisions_raw = data.get("project_decisions", [])
    if not isinstance(decisions_raw, list):
        raise RubricReportError(f"checklist {path}: project_decisions must be an array.")

    wa = (
        working_assumptions
        if working_assumptions is not None
        else load_working_assumptions(root)
    )

    def declared(fact_id: str) -> bool:
        return bool(wa.by_checklist_ref(fact_id)) or wa.declaration(fact_id) is not None

    facts: list[SpineFact] = []
    seen: set[str] = set()
    for kind, role_key, entries in (
        (KIND_SPINE_IDENTITY, "role", spine_raw),
        (KIND_PROJECT_DECISION, "question", decisions_raw),
    ):
        for i, entry in enumerate(entries):
            fact_id, role, status = _spine_fact(entry, kind, role_key, i)
            if fact_id in seen:
                raise RubricReportError(
                    f"checklist {path} carries duplicate fact id {fact_id!r}."
                )
            seen.add(fact_id)
            facts.append(
                SpineFact(
                    fact_id=fact_id,
                    kind=kind,
                    role=role,
                    checklist_status=status,
                    declared=declared(fact_id),
                )
            )
    return SpineRegistry(facts=tuple(facts), source_path=path.as_posix())


# --------------------------------------------------------------------------- #
# The combination rule — deterministic, no judge
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Contradiction:
    """One named contradiction finding — the detector's unit of output.

    ``offending_claims`` names the ledger rows the finding rests on (entry
    key, status, severity); ``spine_fact`` is the cross-referenced spine
    fact's record for :data:`CONTRADICTION_SPINE` findings, ``None`` otherwise.
    """

    kind: str
    expectation_key: str
    section_id: str
    detail: str
    offending_claims: tuple[dict[str, Any], ...] = ()
    spine_fact: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "expectation_key": self.expectation_key,
            "section_id": self.section_id,
            "detail": self.detail,
            "offending_claims": [dict(c) for c in self.offending_claims],
            "spine_fact": dict(self.spine_fact) if self.spine_fact else None,
        }


def _claim_ref(row: Any) -> dict[str, Any]:
    """The named form of one grounding row (entry key, status, severity)."""
    return {
        "entry_key": row.claim.entry_key,
        "status": row.claim.status,
        "severity": row.severity,
        "source_ref": row.claim.source_ref,
    }


def _weak_grounding_explanation(grounding: GroundingGrade) -> tuple[str, tuple[dict[str, Any], ...]]:
    """Why the grounding axis is weak, with the rows that make it so.

    Priority order mirrors E5d's severity semantics: a confirmed entailment
    failure dominates; then unresolved/failed confirmed claims generally; an
    expectation with **no** confirmed claims is named as resting entirely on
    assumed/inferred rows; a budget-truncated claim set is named as such.
    """
    reasons: list[str] = []
    offending: list[dict[str, Any]] = []

    integrity = grounding.integrity_failures()
    if integrity:
        reasons.append(
            "confirmed claim(s) failed entailment: "
            + ", ".join(r.claim.entry_key for r in integrity)
        )
    flagged_confirmed = [
        r
        for r in grounding.confirmed_rows
        if r.severity != SEVERITY_NONE and r not in integrity
    ]
    if flagged_confirmed:
        reasons.append(
            "confirmed claim(s) below their bar: "
            + ", ".join(f"{r.claim.entry_key} ({r.severity})" for r in flagged_confirmed)
        )
    offending.extend(_claim_ref(r) for r in integrity)
    offending.extend(_claim_ref(r) for r in flagged_confirmed)

    if grounding.confirmed_total == 0:
        non_confirmed = [r for r in grounding.rows if r.claim.status != STATUS_CONFIRMED]
        reasons.append(
            "no confirmed claims back it — rests entirely on "
            f"{len(non_confirmed)} assumed/inferred claim(s)"
        )
        offending.extend(_claim_ref(r) for r in non_confirmed)

    if grounding.claims_truncated:
        reasons.append(
            "relevant claims were excluded over budget (grade computed on a "
            "truncated claim set)"
        )

    if not reasons:  # defensive: grounded=False must always be explicable
        reasons.append("grounding did not meet the clean bar")
    return "; ".join(reasons), tuple(offending)


@dataclass(frozen=True)
class ExpectationCell:
    """One (expectation, section) cell of the 9×2 grid — both axes, never a blend.

    ``cell`` classifies by (coverage raw majority) × (clean grounding);
    ``contradictions`` carries the named findings; ``spine_facts`` records
    every spine fact the cell's claims rest on (confirmed ones included — the
    audit trail of what was cross-referenced, not only what fired).
    """

    expectation_key: str
    criterion_id: str
    section_id: str
    cell: str
    coverage: CoverageGrade
    grounding: GroundingGrade
    spine_facts: tuple[SpineFact, ...]
    contradictions: tuple[Contradiction, ...]

    @property
    def covered(self) -> bool:
        """The coverage axis of the cell: the judge's raw majority said addressed."""
        return self.coverage.judge_passed is True

    @property
    def grounded(self) -> bool:
        """The grounding axis of the cell: E5d's clean outcome."""
        return self.grounding.grounded

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": EXPECTATION_RUBRIC_METRIC,
            "expectation_key": self.expectation_key,
            "criterion_id": self.criterion_id,
            "section_id": self.section_id,
            "cell": self.cell,
            "covered": self.covered,
            "grounded": self.grounded,
            "coverage": self.coverage.to_dict(),
            "grounding": self.grounding.to_dict(),
            "spine_facts": [f.to_dict() for f in self.spine_facts],
            "contradictions": [c.to_dict() for c in self.contradictions],
        }


def combine_axes(
    coverage: CoverageGrade,
    grounding: GroundingGrade,
    spine: SpineRegistry,
) -> ExpectationCell:
    """Combine one expectation's two axis grades into its grid cell, fail-closed.

    Deterministic — no judge, no I/O.  The two grades must be for the same
    ``(expectation, section)`` pair (a cross-pairing would attribute one
    expectation's grounding to another's coverage).  The cell's *covered* axis
    is the coverage judge's raw majority (``judge_passed``), so the E5b
    truncation override — visible on ``coverage.passed`` — cannot move a
    genuinely-covered expectation out of the contradiction column; the
    *grounded* axis is E5d's clean outcome, so a truncated claim set or an
    assumed-only answer counts as weak grounding, exactly the cell E5e exists
    to flag.

    Contradictions raised:

    * :data:`CONTRADICTION_COVERAGE_GROUNDING` — the cell is
      :data:`CELL_COVERED_UNGROUNDED`; the offending grounding rows are named.
    * :data:`CONTRADICTION_SPINE` — coverage's raw majority passed while a
      spine fact linked to the cell's claims is not ``Confirmed``.  Fires
      regardless of the grounding outcome: an operator-declared (``Assumed``)
      host can leave every claim individually clean while the expectation
      still rests on an unconfirmed spine item.  The claim↔spine bridge
      covers the judged grounding rows **and** the pack claims excluded
      ``over_budget`` — on a truncated pack the spine claim is often among
      the excluded, and the budget must not silently drop the named finding.
    """
    if coverage.expectation_key != grounding.expectation_key:
        raise RubricReportError(
            f"axis mismatch: coverage is for {coverage.expectation_key!r}, "
            f"grounding for {grounding.expectation_key!r} — refusing to combine "
            "grades of different expectations."
        )
    if coverage.section_id != grounding.section_id:
        raise RubricReportError(
            f"axis mismatch: coverage graded section {coverage.section_id!r}, "
            f"grounding {grounding.section_id!r} — refusing a cross-section "
            "combination."
        )
    if coverage.criterion_id != grounding.criterion_id:
        raise RubricReportError(
            f"axis mismatch: criterion {coverage.criterion_id!r} vs "
            f"{grounding.criterion_id!r} for {coverage.expectation_key!r}."
        )

    covered = coverage.judge_passed is True
    grounded = grounding.grounded
    if covered:
        cell = CELL_COVERED_GROUNDED if grounded else CELL_COVERED_UNGROUNDED
    else:
        cell = CELL_UNCOVERED_GROUNDED if grounded else CELL_UNCOVERED_UNGROUNDED

    key, section = coverage.expectation_key, coverage.section_id
    contradictions: list[Contradiction] = []

    if cell == CELL_COVERED_UNGROUNDED:
        explanation, offending = _weak_grounding_explanation(grounding)
        contradictions.append(
            Contradiction(
                kind=CONTRADICTION_COVERAGE_GROUNDING,
                expectation_key=key,
                section_id=section,
                detail=(
                    f"{key} / {section}: coverage majority passed"
                    + (
                        f" (score {coverage.score:.2f})"
                        if coverage.score is not None
                        else ""
                    )
                    + f" while grounding is weak — {explanation}."
                ),
                offending_claims=offending,
            )
        )

    # -- spine cross-reference (dedup facts, keep registry order) ---------- #
    # Two sources of linked claims: the judged grounding rows, and the pack
    # claims excluded ``over_budget`` — on real (truncated) packs the spine
    # claim itself is often among the excluded, and losing the *named* spine
    # finding to the budget would be a silent cap on the headline output.
    linked: dict[str, SpineFact] = {}
    linked_rows: dict[str, list[Any]] = {}
    linked_excluded: dict[str, list[dict[str, Any]]] = {}
    for row in grounding.rows:
        for fact in spine.facts_for_claim(row.claim.claim_id, row.claim.source_ref):
            linked.setdefault(fact.fact_id, fact)
            linked_rows.setdefault(fact.fact_id, []).append(row)
    for item in coverage.pack_record.get("excluded", []):
        if item.get("kind") != KIND_CLAIM or item.get("reason") != EXCLUDED_OVER_BUDGET:
            continue
        entry_key = str(item.get("key", ""))
        claim_id = entry_key.split("#", 1)[0]
        for fact in spine.facts_for_claim(claim_id, str(item.get("source_ref", ""))):
            linked.setdefault(fact.fact_id, fact)
            linked_excluded.setdefault(fact.fact_id, []).append(
                {
                    "entry_key": entry_key,
                    "status": item.get("status", ""),
                    "severity": None,
                    "source_ref": item.get("source_ref", ""),
                    "excluded": EXCLUDED_OVER_BUDGET,
                }
            )
    if covered:
        for fact in linked.values():
            if not fact.unconfirmed:
                continue
            rows = linked_rows.get(fact.fact_id, [])
            excluded_refs = linked_excluded.get(fact.fact_id, [])
            declared_note = " (operator-declared, not confirmed)" if fact.declared else ""
            via = ", ".join(
                [r.claim.entry_key for r in rows]
                + [e["entry_key"] for e in excluded_refs]
            )
            excluded_note = (
                " (claim(s) "
                + ", ".join(e["entry_key"] for e in excluded_refs)
                + " were relevant but excluded over budget and not judged)"
                if excluded_refs
                else ""
            )
            contradictions.append(
                Contradiction(
                    kind=CONTRADICTION_SPINE,
                    expectation_key=key,
                    section_id=section,
                    detail=(
                        f"{key} / {section}: coverage majority passed while spine "
                        f"fact {fact.fact_id} ({fact.role}) is "
                        f"{fact.effective_status}{declared_note} — the expectation "
                        f"rests on an unconfirmed spine item, via claim(s) {via}."
                        + excluded_note
                    ),
                    offending_claims=tuple(_claim_ref(r) for r in rows)
                    + tuple(excluded_refs),
                    spine_fact=fact.to_dict(),
                )
            )

    return ExpectationCell(
        expectation_key=key,
        criterion_id=coverage.criterion_id,
        section_id=section,
        cell=cell,
        coverage=coverage,
        grounding=grounding,
        spine_facts=tuple(linked.values()),
        contradictions=tuple(contradictions),
    )


# --------------------------------------------------------------------------- #
# The report — advisory by construction, no blended score
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RubricReport:
    """The whole 9×2 grid + contradictions — advisory, never run-blocking.

    ``advisory``/``blocking`` are enforced exactly like
    :class:`~harness.regression.RegressionReport` and
    :class:`~harness.report.HarnessReport`: a report that could block a run
    cannot be constructed, and nothing in ``runner`` reads it.  There is —
    deliberately, structurally — **no blended score field**: the two axes
    travel separately into :meth:`to_dict` and the renderer, because a blend
    would average away exactly the contradiction cell this report exists to
    surface.
    """

    cells: tuple[ExpectationCell, ...]
    rubric_set_id: str = ""
    rubric_set_version: str = ""
    rubric_set_fingerprint: str = ""
    scorecard_id: str = ""
    scorecard_version: str = ""
    profile_id: str = ""
    profile_version: str = ""
    judge_model: str | None = None
    judge_version: str | None = None
    spine_source: str = ""
    notes: str = ""
    advisory: bool = True
    blocking: bool = False

    def __post_init__(self) -> None:
        if self.advisory is not True:
            raise ValueError(
                "RubricReport.advisory must be True — the rubric grid is "
                "advisory to a human, never authoritative over a run."
            )
        if self.blocking is not False:
            raise ValueError(
                "RubricReport.blocking must be False — no eval metric may wire "
                "into the runtime DAG as a fail-closed gate."
            )

    @property
    def contradictions(self) -> tuple[Contradiction, ...]:
        return tuple(c for cell in self.cells for c in cell.contradictions)

    @property
    def summary(self) -> dict[str, Any]:
        by_cell: dict[str, int] = {}
        for cell in self.cells:
            by_cell[cell.cell] = by_cell.get(cell.cell, 0) + 1
        contradictions = self.contradictions
        return {
            "cells": len(self.cells),
            "covered": sum(1 for c in self.cells if c.covered),
            "grounded": sum(1 for c in self.cells if c.grounded),
            "clean_pass": sum(1 for c in self.cells if c.coverage.passed),
            "cells_by_class": by_cell,
            "contradictions": len(contradictions),
            "spine_contradictions": sum(
                1 for c in contradictions if c.kind == CONTRADICTION_SPINE
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": RUBRIC_REPORT_RECORD_TYPE,
            "metric": EXPECTATION_RUBRIC_METRIC,
            "advisory": self.advisory,
            "blocking": self.blocking,
            "rubric_set_id": self.rubric_set_id,
            "rubric_set_version": self.rubric_set_version,
            "rubric_set_fingerprint": self.rubric_set_fingerprint,
            "scorecard_id": self.scorecard_id,
            "scorecard_version": self.scorecard_version,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "judge_model": self.judge_model,
            "judge_version": self.judge_version,
            "spine_source": self.spine_source,
            "notes": self.notes,
            "summary": self.summary,
            "cells": [c.to_dict() for c in self.cells],
        }


#: The advisory boundary sentence stamped on every report.
_ADVISORY_NOTE: str = (
    "Advisory to a human, never run-blocking: both axes are reported "
    "side by side and no blended score exists; the contradiction findings "
    "name the claims and spine facts they rest on (see harness/HARNESS.md)."
)


def build_rubric_report(
    cells: Iterable[ExpectationCell],
    *,
    rubric_set: RubricSet | None = None,
    profile: ProfileBundle | None = None,
    judge_model: str | None = None,
    judge_version: str | None = None,
    spine_source: str = "",
    notes: str = _ADVISORY_NOTE,
) -> RubricReport:
    """Assemble the :class:`RubricReport`, pinned to its rubric set, profile and judge."""
    return RubricReport(
        cells=tuple(cells),
        rubric_set_id=rubric_set.rubric_set_id if rubric_set else "",
        rubric_set_version=rubric_set.version if rubric_set else "",
        rubric_set_fingerprint=rubric_set.fingerprint if rubric_set else "",
        scorecard_id=rubric_set.scorecard_id if rubric_set else "",
        scorecard_version=rubric_set.scorecard_version if rubric_set else "",
        profile_id=profile.profile_id if profile else "",
        profile_version=profile.version if profile else "",
        judge_model=judge_model,
        judge_version=judge_version,
        spine_source=spine_source,
        notes=notes,
    )


# --------------------------------------------------------------------------- #
# Rendering — the two axes side by side; ASCII-safe
# --------------------------------------------------------------------------- #


def _fmt_bool(value: Any) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "-"


def _coverage_summary(cov: Mapping[str, Any]) -> str:
    score = cov.get("score")
    score_s = f"{score:.2f}" if isinstance(score, (int, float)) else "-"
    return (
        f"judge={_fmt_bool(cov.get('judge_passed'))} "
        f"clean={_fmt_bool(cov.get('passed'))} "
        f"score={score_s} pack={cov.get('pack_status', '-')}"
    )


def _grounding_summary(grd: Mapping[str, Any]) -> str:
    rate = grd.get("grounding_rate")
    rate_s = f"{rate:.2f}" if isinstance(rate, (int, float)) else "-"
    return (
        f"grounded={_fmt_bool(grd.get('grounded'))} "
        f"rate={rate_s} "
        f"confirmed={grd.get('confirmed_grounded', 0)}/{grd.get('confirmed_total', 0)} "
        f"assumed={grd.get('assumed_total', 0)} inferred={grd.get('inferred_total', 0)}"
    )


def render_report(report: Mapping[str, Any]) -> str:
    """Render a report dict (fresh ``to_dict()`` or a loaded file) as text.

    The grid prints the two axes **side by side** per (expectation, section)
    row — deliberately never a blended number — followed by every
    contradiction with its named claims.  Output is ASCII-safe (the Windows
    console commonly runs a cp125x codepage).
    """
    cells = report.get("cells", [])
    if not isinstance(cells, list):
        raise RubricReportError("report 'cells' must be an array.")
    summary = report.get("summary", {})

    fingerprint = str(report.get("rubric_set_fingerprint") or "")[:19]
    header = (
        f"EXPECTATION RUBRIC GRID - coverage x grounding "
        f"({len(cells)} cells; no blended score)\n"
        f"rubric_set: {report.get('rubric_set_id', '')} "
        f"v{report.get('rubric_set_version', '')} "
        f"[{fingerprint}]  "
        f"judge: {report.get('judge_model')}/{report.get('judge_version')}\n"
        f"profile: {report.get('profile_id', '') or '-'} "
        f"[{str(report.get('profile_version') or '')[:19]}]\n"
        f"advisory={report.get('advisory')} blocking={report.get('blocking')}\n"
    )

    rows: list[tuple[str, str, str, str, str]] = [
        ("expectation", "section", "coverage", "grounding", "cell")
    ]
    for cell in cells:
        rows.append(
            (
                str(cell.get("expectation_key", "")),
                str(cell.get("section_id", "")),
                _coverage_summary(cell.get("coverage", {})),
                _grounding_summary(cell.get("grounding", {})),
                str(cell.get("cell", "")),
            )
        )
    widths = [max(len(r[i]) for r in rows) for i in range(5)]
    lines = [header]
    for i, row in enumerate(rows):
        lines.append("  ".join(col.ljust(widths[j]) for j, col in enumerate(row)).rstrip())
        if i == 0:
            lines.append("  ".join("-" * w for w in widths))

    contradictions = [
        c for cell in cells for c in cell.get("contradictions", [])
    ]
    lines.append("")
    if contradictions:
        lines.append(f"CONTRADICTIONS ({len(contradictions)}):")
        for i, c in enumerate(contradictions, 1):
            lines.append(f" {i}. [{c.get('kind')}] {c.get('detail')}")
            offending = c.get("offending_claims") or []
            if offending:
                lines.append(
                    "    claims: "
                    + ", ".join(
                        f"{o.get('entry_key')} ({o.get('status')}/{o.get('severity')})"
                        for o in offending
                    )
                )
    else:
        lines.append("CONTRADICTIONS: none")
    if summary:
        lines.append("")
        lines.append(
            "summary: "
            + json.dumps(summary, sort_keys=True, ensure_ascii=True, separators=(", ", ": "))
        )
    return _ascii("\n".join(lines))


# --------------------------------------------------------------------------- #
# Grading orchestration (the CLI `grade` body; E5f drives pacing around this)
# --------------------------------------------------------------------------- #


def grade_all(
    judge: Judge,
    rubric_set: RubricSet,
    spine: SpineRegistry,
    *,
    repo_root: Path | str = Path("."),
    sections_dir: Path | str | None = None,
    working_assumptions: WorkingAssumptions | None = None,
    token_budget: int = DEFAULT_PACK_TOKEN_BUDGET,
    span_budget_fraction: float = DEFAULT_SPAN_BUDGET_FRACTION,
    n: int = MIN_MAJORITY_SAMPLES,
    verdict_cache: VerdictCache | None = None,
    profile: PreEvaluationProfile | None = None,
) -> tuple[ExpectationCell, ...]:
    """Grade every rubric over its mapped section(s) and combine the axes.

    One shared :data:`~harness.expectation_grounding.VerdictCache` spans the
    whole run, so the same ``(claim, source_ref)`` pair is never judged twice
    across the nine expectations (the E5d budget discipline).  Section
    resolution goes through the profile's criterion↔section map (the default
    profile when *profile* is ``None``) — the grader never guesses which
    artifact answers which expectation.
    """
    root = Path(repo_root)
    wa = (
        working_assumptions
        if working_assumptions is not None
        else load_working_assumptions(root)
    )
    cache: VerdictCache = verdict_cache if verdict_cache is not None else {}
    section_kwargs: dict[str, Any] = {"repo_root": root, "profile": profile}
    if sections_dir is not None:
        section_kwargs["sections_dir"] = sections_dir

    cells: list[ExpectationCell] = []
    for rubric in rubric_set.rubrics:
        for section_path in section_paths_for(rubric.criterion_id, **section_kwargs):
            coverage = grade_expectation(
                judge,
                rubric,
                section_path,
                token_budget=token_budget,
                span_budget_fraction=span_budget_fraction,
                n=n,
            )
            grounding = derive_expectation_grounding(
                rubric,
                section_path,
                token_budget=token_budget,
                span_budget_fraction=span_budget_fraction,
                judge=judge,
                repo_root=root,
                working_assumptions=wa,
                n=n,
                verdict_cache=cache,
            )
            cells.append(combine_axes(coverage, grounding, spine))
    return tuple(cells)


def _build_judge(provenance_path: Path) -> Judge:
    """The CLI's judge: env-pinned config + a durable provenance trail."""
    return Judge(resolve_judge_config(), provenance_log=ProvenanceLog(provenance_path))


# --------------------------------------------------------------------------- #
# CLI — grade / report (advisory)
# --------------------------------------------------------------------------- #

#: Every fail-closed error the CLI converts to exit code 2 — the harness's own
#: contract errors plus the I/O layer; a programming error (e.g. a stray
#: ``ValueError``) deliberately tracebacks instead of masquerading as a
#: fail-closed outcome.
_CLI_ERRORS = (
    RubricReportError,
    RubricError,
    ExpectationError,
    EvidencePackError,
    CoverageError,
    GroundingError,
    JudgeError,
    WorkingAssumptionsError,
    OSError,
)


def main(argv: Sequence[str] | None = None) -> int:
    """``python -m harness.rubric`` — grade the expectation grid or re-render a report.

    Exit codes: ``0`` clean; ``1`` contradiction(s) found (**advisory** — a
    human decides what to do about a high-coverage / weak-grounding or
    unconfirmed-spine finding; nothing run-blocking consumes this); ``2`` the
    grading/report could not run (fail-closed).
    """
    parser = argparse.ArgumentParser(
        prog="harness.rubric",
        description=(
            "E5e rubric grid: combine the coverage (E5c) and grounding (E5d) "
            "axes per profile evaluator expectation, detect high-coverage/"
            "weak-grounding and unconfirmed-spine contradictions, and render "
            "both axes side by side. Advisory to a human; never a runtime gate."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_grade = sub.add_parser(
        "grade", help="grade the profile's expectations over their mapped sections"
    )
    p_grade.add_argument("--repo-root", default=".")
    p_grade.add_argument(
        "--profile",
        default=None,
        help="pre-evaluation profile JSON (default: the harness default profile)",
    )
    p_grade.add_argument("--sections", default=None, help="override the sections dir")
    p_grade.add_argument("--out", default=str(DEFAULT_REPORT_PATH))
    p_grade.add_argument("--provenance", default=str(DEFAULT_PROVENANCE_PATH))
    p_grade.add_argument("--budget", type=int, default=DEFAULT_PACK_TOKEN_BUDGET)
    p_grade.add_argument("--n", type=int, default=MIN_MAJORITY_SAMPLES)

    p_report = sub.add_parser("report", help="re-render a persisted report")
    p_report.add_argument("--in", dest="in_path", default=str(DEFAULT_REPORT_PATH))

    args = parser.parse_args(argv)
    try:
        if args.command == "grade":
            root = Path(args.repo_root)
            bundle = load_profile_bundle(args.profile, repo_root=root)
            rubric_set = bundle.rubric_set
            wa = load_working_assumptions(root)
            spine = load_spine_registry(root, working_assumptions=wa)
            judge = _build_judge(Path(args.provenance))
            cells = grade_all(
                judge,
                rubric_set,
                spine,
                repo_root=root,
                sections_dir=args.sections,
                working_assumptions=wa,
                token_budget=args.budget,
                n=args.n,
                profile=bundle.profile,
            )
            report = build_rubric_report(
                cells,
                rubric_set=rubric_set,
                profile=bundle,
                judge_model=judge.config.model,
                judge_version=judge.config.version,
                spine_source=spine.source_path,
            )
            data = report.to_dict()
            print(render_report(data))
            if args.out:
                atomic_write_json(data, Path(args.out), prefix="rubric_report_")
            return 1 if report.contradictions else 0

        # -- report ------------------------------------------------------- #
        path = Path(args.in_path)
        if not path.is_file():
            raise RubricReportError(f"report file not found: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise RubricReportError(f"report {path} is not valid JSON: {exc}") from exc
        if not isinstance(data, Mapping) or data.get("record_type") != RUBRIC_REPORT_RECORD_TYPE:
            raise RubricReportError(
                f"{path} is not a {RUBRIC_REPORT_RECORD_TYPE!r} record."
            )
        print(render_report(data))
        contradiction_count = sum(
            len(c.get("contradictions", [])) for c in data.get("cells", [])
        )
        return 1 if contradiction_count else 0
    except _CLI_ERRORS as exc:
        print(f"rubric grid could not run (fail-closed): {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
