"""
Candidate-bound blind assessment — one candidate, one profile, one pinned assessor.

The blind pre-evaluation lane assesses a *specified* candidate against a
versioned pre-evaluation profile with an injectable assessor, without running
the production pipeline.  The report is bound to what it judged: every report
and every cell carries the candidate's content hash, the profile version and
the assessor pin.  A report loaded against a candidate whose hash differs is
rejected, so a verdict can never be re-attached to a different draft.

What this module enforces, in code:

* **Candidate binding.**  The candidate hash is the harness's formatting-
  invariant artifact hash (:func:`~harness.profile.canonical_hash`) over the
  parsed section artifacts, keyed by section id — whitespace, key order and a
  BOM are inert; a changed sentence is not.  :func:`load_report` recomputes the
  hash from disk and raises :class:`CandidateHashMismatch` naming both hashes.
* **Coverage scope is explicit.**  The profile's criterion-to-section map
  names the sections a candidate must hold.  A candidate missing one is still
  assessed over what it holds, but the report is labelled
  :data:`SCOPE_PARTIAL` and carries the missing sections by name.  A candidate
  holding none of them is refused.
* **The assessor is the existing judge.**  Each cell is one
  :func:`~harness.expectation_coverage.grade_expectation` call: the rubric's
  versioned pack, an N≥3 majority panel, provenance for every sample.  A
  malformed response raises through the judge (no silent repair) and no report
  is written.
* **Advisory by construction, immutable on disk.**  :class:`BlindAssessmentReport`
  enforces ``advisory=True, blocking=False`` like every harness report; the
  writer never overwrites — each run lands in a new file and historical
  reports stay byte-identical.
* **Evidence through the dev-graph, blind view only.**  The document route
  (:func:`build_blind_evidence`) builds the snapshot, asks the dev-graph
  package builder for the evidence around the document under the
  ``blind_pre_evaluation`` view policy, and materialises the package's
  passages and claims as the section artifacts the grader consumes.  Nothing
  else reaches the assessor.  The older directory route (``--candidate``)
  grades whatever section artifacts the operator supplies; it is kept for
  offline profile work, carries no package, cannot stamp an intake, and its
  report says so (``evidence_source``).
* **Leakage guard, hard failure.**  Before any assessor call,
  :func:`assert_no_leakage` walks every included item and raises
  :class:`LeakageError` on a forbidden type (assessment, finding, change
  request) or a historical-feedback tag (``historical_feedback``,
  ``historical_score``, ``target_score``, ``repair_plan``).  The view policy
  is the first check; this is the second.  A violation stops the command
  with nothing written.
* **ESR is intake state, never inferred.**  The report stamps the ESR
  availability from the intake record it was given (``unknown`` without
  one).  An intake whose permitted purpose is ``esr_informed_review`` is
  refused: that is a separately labelled task (:class:`ReviewTask`) and the
  report's ``task_label`` can only ever be :data:`BLIND_TASK_LABEL`.

Grounding (E5d) is deliberately not part of the blind lane: an evaluator sees
the candidate, not the Tier-3 sources behind it.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA; reads candidate artifacts
    read-only and writes only harness-owned report and provenance files.
    Never a runtime gate.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from runner.atomic_write import atomic_write_json
from runner.dev_graph import (
    ESR_AVAILABILITY,
    HISTORICAL_FEEDBACK_TAGS,
    PERMITTED_PURPOSES,
    POLICY_VERSION,
    DevGraphError,
    EsrIntake,
    Package,
    Snapshot,
    build_package,
    build_snapshot,
)
from runner.dev_graph.schema import CURRENT_DOCUMENT_STATES
from harness.evidence_pack import DEFAULT_PACK_TOKEN_BUDGET, DEFAULT_SPAN_BUDGET_FRACTION
from harness.expectation_coverage import CoverageGrade, grade_expectation
from harness.judge import Judge
from harness.profile import PreEvaluationProfile, canonical_hash
from harness.rubrics import ProfileBundle
from harness.verdict import MIN_MAJORITY_SAMPLES

__all__ = [
    "BLIND_REPORT_RECORD_TYPE",
    "BLIND_ASSESSMENT_METRIC",
    "SCOPE_COMPLETE",
    "SCOPE_PARTIAL",
    "DEFAULT_REPORTS_DIR",
    "DEFAULT_PROVENANCE_PATH",
    "BLIND_VIEW",
    "BLIND_TASK_LABEL",
    "ESR_INFORMED_TASK_LABEL",
    "TASK_LABELS",
    "LEAKAGE_FORBIDDEN_TYPES",
    "DEFAULT_PACKAGE_BUDGET",
    "EVIDENCE_SOURCE_DEV_GRAPH",
    "EVIDENCE_SOURCE_DIRECTORY",
    "BlindAssessmentError",
    "CandidateHashMismatch",
    "LeakageError",
    "ReviewTask",
    "BlindEvidence",
    "resolve_document",
    "assert_no_leakage",
    "materialise_candidate",
    "build_blind_evidence",
    "MissingSection",
    "Candidate",
    "required_sections",
    "load_candidate",
    "candidate_hash",
    "assessor_pin",
    "BlindCell",
    "BlindAssessmentReport",
    "assess_candidate",
    "write_report",
    "load_report",
    "render_report",
]

#: The ``record_type`` of a persisted blind assessment report.
BLIND_REPORT_RECORD_TYPE: str = "blind_assessment_report"

#: The metric name stamped on the report.
BLIND_ASSESSMENT_METRIC: str = "blind_pre_evaluation"

#: Coverage scope labels.
SCOPE_COMPLETE: str = "complete"
SCOPE_PARTIAL: str = "partial"

#: Where the command writes reports by default (harness-owned, repo-relative).
DEFAULT_REPORTS_DIR: Path = Path("harness/blind_reports")

#: Default provenance trail for the command (harness-owned, repo-relative).
DEFAULT_PROVENANCE_PATH: Path = Path("harness/provenance/blind_assessment.jsonl")

#: Report file name: ``blind_<12 hex of the candidate hash>_<NNNN>.json``.
_REPORT_NAME_RE = re.compile(r"^blind_(?P<hash>[0-9a-f]{12})_(?P<seq>\d{4})\.json$")

#: The only dev-graph view the blind lane builds evidence under.
BLIND_VIEW: str = "blind_pre_evaluation"

#: Task labels.  A blind assessment and an ESR-informed review are two tasks
#: with two labels; the labels are the intake record's permitted purposes.
BLIND_TASK_LABEL: str = "blind_pre_evaluation"
ESR_INFORMED_TASK_LABEL: str = "esr_informed_review"
TASK_LABELS: frozenset[str] = frozenset({BLIND_TASK_LABEL, ESR_INFORMED_TASK_LABEL})
if TASK_LABELS != PERMITTED_PURPOSES:  # pragma: no cover - guards a vocabulary drift
    raise RuntimeError("harness task labels must equal runner.dev_graph.PERMITTED_PURPOSES")

#: Where the assessed sections came from: the dev-graph blind view (guarded)
#: or a candidate directory the operator supplied (not guarded by this module).
EVIDENCE_SOURCE_DEV_GRAPH: str = "dev_graph_blind_view"
EVIDENCE_SOURCE_DIRECTORY: str = "candidate_directory"

#: Node types the leakage guard refuses in a blind package, whatever the
#: view policy said.
LEAKAGE_FORBIDDEN_TYPES: frozenset[str] = frozenset({"assessment", "finding", "change_request"})

#: Default size budget for the dev-graph package (its own deterministic
#: unit, see ``runner.dev_graph.packages.estimate_cost``).
DEFAULT_PACKAGE_BUDGET: int = 200_000

#: Where the document route materialises candidates, under the reports dir.
_CANDIDATES_SUBDIR: str = "candidates"

Clock = Callable[[], str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BlindAssessmentError(Exception):
    """The candidate, report or profile is unusable (fail-closed)."""


class CandidateHashMismatch(BlindAssessmentError):
    """The report was produced over a different candidate than the one on disk."""


class LeakageError(BlindAssessmentError):
    """Historical feedback reached the blind package.  Hard failure: nothing
    is assessed and nothing is written."""


@dataclass(frozen=True)
class ReviewTask:
    """A labelled review task over one document.

    The label is one of :data:`TASK_LABELS`.  An ESR-informed review carries
    :data:`ESR_INFORMED_TASK_LABEL` and is never blind; only a task whose
    label is :data:`BLIND_TASK_LABEL` may be reported by this module.
    """

    label: str
    document: str

    def __post_init__(self) -> None:
        if self.label not in TASK_LABELS:
            raise ValueError(f"unknown task label {self.label!r}; one of {sorted(TASK_LABELS)}.")

    @property
    def is_blind(self) -> bool:
        return self.label == BLIND_TASK_LABEL


# --------------------------------------------------------------------------- #
# Evidence through the dev-graph — blind view, leakage guard, materialisation
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class BlindEvidence:
    """The evidence the document route hands to the assessor.

    ``document`` is the document snapshot node id and ``document_id`` the
    document's own id; ``package`` the dev-graph package built under
    :data:`BLIND_VIEW` that passed :func:`assert_no_leakage`;
    ``candidate_dir`` the materialised section artifacts (the hash input).
    """

    document: str
    document_id: str
    snapshot_id: str
    package: Package
    candidate_dir: Path


def resolve_document(snapshot: Snapshot, document: str) -> dict[str, Any]:
    """The current document snapshot node *document* names, fail-closed.

    *document* is a node id (``<document_id>@<hex>``) or a document id.  A
    document id resolves only when exactly one current version exists: state
    ``imported`` or ``draft`` and not superseded.  A submitted or superseded
    snapshot is history, never a candidate.
    """
    nodes = {n["id"]: n for n in snapshot.nodes if n["type"] == "artifact_version"}
    superseded = {e["target"]["id"] for e in snapshot.edges if e["predicate"] == "supersedes"}

    def _current(node: Mapping[str, Any]) -> bool:
        return node["content"].get("state") in CURRENT_DOCUMENT_STATES and node["id"] not in superseded

    if document in nodes:
        node = nodes[document]
        if not _current(node):
            raise BlindAssessmentError(
                f"document snapshot {document} is {node['content'].get('state')!r}"
                f"{' and superseded' if document in superseded else ''}; not a current candidate."
            )
        return node
    matches = [n for n in nodes.values() if n["content"].get("document_id") == document]
    current = [n for n in matches if _current(n)]
    if len(current) == 1:
        return current[0]
    if not matches:
        raise BlindAssessmentError(f"no document snapshot named {document!r} in the current build.")
    if not current:
        raise BlindAssessmentError(
            f"document {document!r} has no current version ({len(matches)} historical: "
            f"{', '.join(sorted(n['id'] for n in matches))})."
        )
    raise BlindAssessmentError(
        f"document {document!r} has {len(current)} current versions "
        f"({', '.join(sorted(n['id'] for n in current))}); name the node id."
    )


def _item_tags(item: Mapping[str, Any]) -> frozenset[str]:
    tags = (item.get("content") or {}).get("tags", [])
    return frozenset(t for t in tags if isinstance(t, str)) if isinstance(tags, list) else frozenset()


def assert_no_leakage(package: Package) -> None:
    """Raise :class:`LeakageError` unless *package* is clean for a blind assessor.

    The package must have been built under :data:`BLIND_VIEW`, and no
    included item may be of a type in :data:`LEAKAGE_FORBIDDEN_TYPES` or
    carry a tag in ``HISTORICAL_FEEDBACK_TAGS``.  Every item is checked; the
    first violation is named.
    """
    view = package.manifest.get("view")
    if view != BLIND_VIEW:
        raise LeakageError(
            f"package {package.package_id} was built under view {view!r}, not {BLIND_VIEW!r}; "
            "a blind assessment takes evidence from the blind view only."
        )
    for item in package.items:
        if item.get("type") in LEAKAGE_FORBIDDEN_TYPES:
            raise LeakageError(
                f"leakage: item {item.get('id')} of type {item.get('type')!r} is in the blind "
                "package; assessment, finding and change_request never reach the assessor."
            )
        leaked = _item_tags(item) & HISTORICAL_FEEDBACK_TAGS
        if leaked:
            raise LeakageError(
                f"leakage: item {item.get('id')} carries {', '.join(sorted(leaked))}; "
                "historical feedback never reaches the blind assessor."
            )


def materialise_candidate(package: Package, document: str, target_dir: Path) -> Path:
    """Write the package's passages and claims of *document* as section artifacts.

    One ``<section_id>.json`` per passage, with the document's claims of that section
    as the claim ledger (declared status lowercased, the verified span id as
    ``source_ref``).  Derived from the package alone, so the same package lands the
    same bytes.

    The sub-sections are the section's **declared** ones when it has any, preserved in
    declaration order with their ids intact.  That is what lets a profile grade this
    route at all: a profile's rubrics anchor below the section, and
    ``build_evidence_pack`` fails closed on an anchor absent from the artifact, so
    synthesising one sub-section named for its section made every anchored profile
    unusable here.  Which ids a profile anchors on is the profile's business and never
    this module's.

    A section declaring none falls back to that single synthesised sub-section, which
    is what every section produced before sub-sections existed.  A record written
    against the old shape therefore still grades, against a profile whose anchors are
    its section ids.
    """
    passages = [
        i for i in package.items
        if i["type"] == "passage" and i["content"].get("document") == document
    ]
    if not passages:
        raise BlindAssessmentError(f"package {package.package_id} holds no passage of {document}.")
    claims = [
        i for i in package.items
        if i["type"] == "claim" and i["content"].get("document") == document
    ]
    target_dir.mkdir(parents=True, exist_ok=True)
    for p in sorted(passages, key=lambda i: i["id"]):
        c = p["content"]
        sid = str(c["section_id"])
        ledger = []
        for cl in sorted(claims, key=lambda i: i["id"]):
            cc = cl["content"]
            if cc.get("section_id") != sid:
                continue
            span = cc.get("verified_span")
            ledger.append(
                {
                    "claim_id": str(cc.get("claim_id")),
                    "claim_summary": str(cc.get("text", "")),
                    "status": str(cc.get("declared_status", "")).lower(),
                    "source_ref": str(span["id"]) if isinstance(span, Mapping) and span.get("id") else "",
                    "approval": cc.get("approval"),
                }
            )
        artifact = {
            "section_id": sid,
            "document": document,
            "passage": {"id": p["id"], "version": p["version"]},
            "sub_sections": [
                {
                    "sub_section_id": str(sub["sub_section_id"]),
                    "title": str(sub.get("title", "")),
                    "content": str(sub.get("content", "")),
                }
                for sub in c["sub_sections"]
            ]
            if c.get("sub_sections")
            else [
                {"sub_section_id": sid, "title": str(c.get("title", "")), "content": str(c.get("content", ""))}
            ],
            "validation_status": {"claim_statuses": ledger},
        }
        atomic_write_json(artifact, target_dir / f"{sid}.json", prefix="blind_candidate_")
    return target_dir


def build_blind_evidence(
    graph_root: Path | str,
    document: str,
    *,
    profile_version: str,
    out_dir: Path | str,
    budget: int = DEFAULT_PACKAGE_BUDGET,
    project: str | None = None,
) -> BlindEvidence:
    """Snapshot, blind-view package, leakage guard, materialised candidate.

    Order matters: the guard runs on the package before a single byte is
    materialised or any assessor exists.  An incomplete package (something
    the view permitted did not fit the budget) is refused, so a missing
    section is always the candidate's, never the budget's.
    """
    root = Path(graph_root)
    snapshot = build_snapshot(root)
    node = resolve_document(snapshot, document)
    doc_id = node["id"]
    package = build_package(
        snapshot,
        task=doc_id,
        view=BLIND_VIEW,
        budget=budget,
        policy_version=POLICY_VERSION,
        expected_snapshot_id=snapshot.snapshot_id,
        project=project or str(node["content"].get("document_id")),
        profile_version=profile_version,
    )
    assert_no_leakage(package)
    if package.manifest.get("completeness") != "complete":
        raise BlindAssessmentError(
            f"package {package.package_id} is incomplete under budget {budget}; raise the "
            "package budget so nothing the blind view permits is dropped."
        )
    candidate_dir = materialise_candidate(
        package, doc_id, Path(out_dir) / _CANDIDATES_SUBDIR / doc_id
    )
    return BlindEvidence(
        document=doc_id,
        document_id=str(node["content"].get("document_id")),
        snapshot_id=snapshot.snapshot_id,
        package=package,
        candidate_dir=candidate_dir,
    )


# --------------------------------------------------------------------------- #
# Candidate — the profile-required sections and their content hash
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MissingSection:
    """One profile-required section the candidate does not hold."""

    criterion_id: str
    section_id: str
    reason: str = "missing"

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "section_id": self.section_id,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class Candidate:
    """A candidate directory resolved against a profile.

    ``sections`` maps each present section id to its artifact path;
    ``contents`` holds the parsed artifacts (the hash input); ``missing`` names
    the profile-required sections that are absent.
    """

    root: Path
    sections: Mapping[str, Path]
    contents: Mapping[str, Any]
    missing: tuple[MissingSection, ...]

    @property
    def scope(self) -> str:
        return SCOPE_PARTIAL if self.missing else SCOPE_COMPLETE


def required_sections(profile: PreEvaluationProfile) -> tuple[tuple[str, str], ...]:
    """Every ``(criterion_id, section_id)`` the profile grades, in profile order."""
    return tuple(
        (spec.id, sid) for spec in profile.criteria for sid in spec.section_ids
    )


def load_candidate(candidate_dir: Path | str, profile: PreEvaluationProfile) -> Candidate:
    """Resolve *candidate_dir* against the profile's required sections, fail-closed.

    Each required section is expected at ``<candidate_dir>/<section_id>.json``.
    A present artifact must be valid JSON; an absent one is recorded as missing.
    A directory that holds none of the required sections is refused — there is
    nothing to assess.
    """
    root = Path(candidate_dir)
    if not root.is_dir():
        raise BlindAssessmentError(f"candidate {root} is not a directory.")
    sections: dict[str, Path] = {}
    contents: dict[str, Any] = {}
    missing: list[MissingSection] = []
    for criterion_id, section_id in required_sections(profile):
        path = root / f"{section_id}.json"
        if section_id in contents or any(m.section_id == section_id for m in missing):
            continue  # the same section mapped by two criteria: counted once
        if not path.is_file():
            missing.append(MissingSection(criterion_id=criterion_id, section_id=section_id))
            continue
        try:
            contents[section_id] = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            raise BlindAssessmentError(
                f"candidate section {path} is not valid JSON: {exc}"
            ) from exc
        sections[section_id] = path
    if not sections:
        raise BlindAssessmentError(
            f"candidate {root} holds none of the {len(missing)} section(s) profile "
            f"{profile.profile_id!r} requires ({', '.join(m.section_id for m in missing)})."
        )
    return Candidate(root=root, sections=sections, contents=contents, missing=tuple(missing))


def candidate_hash(candidate: Candidate) -> str:
    """The formatting-invariant content hash of the candidate's present sections."""
    return canonical_hash({sid: candidate.contents[sid] for sid in sorted(candidate.contents)})


def assessor_pin(judge: Judge) -> str:
    """The ``model@version`` pin recorded on the report and every cell."""
    return f"{judge.config.model}@{judge.config.version}"


# --------------------------------------------------------------------------- #
# Cells and the report — bound, advisory
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class BlindCell:
    """One (expectation, section) coverage grade bound to the candidate."""

    criterion_id: str
    expectation_key: str
    section_id: str
    candidate_hash: str
    profile_version: str
    assessor_pin: str
    coverage: CoverageGrade

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "expectation_key": self.expectation_key,
            "section_id": self.section_id,
            "candidate_hash": self.candidate_hash,
            "profile_version": self.profile_version,
            "assessor_pin": self.assessor_pin,
            "covered": self.coverage.judge_passed is True,
            "clean_pass": self.coverage.passed,
            "score": self.coverage.score,
            "coverage": self.coverage.to_dict(),
        }


#: The advisory boundary sentence stamped on every report.
_ADVISORY_NOTE: str = (
    "Advisory to a human, never run-blocking. The report is bound to the "
    "candidate hash, profile version and assessor pin it carries; a report "
    "whose candidate hash differs from the candidate on disk is rejected on "
    "load (see harness/HARNESS.md)."
)


@dataclass(frozen=True)
class BlindAssessmentReport:
    """The blind assessment of one candidate — bound, advisory, immutable.

    Construction fails when ``advisory`` is not ``True`` or ``blocking`` is
    not ``False``, when any cell carries a different candidate hash, profile
    version or assessor pin than the report, or when the scope label
    disagrees with the partial-coverage list.
    """

    candidate_hash: str
    candidate_path: str
    profile_id: str
    profile_version: str
    assessor_model: str
    assessor_version: str
    assessor_pin: str
    scope: str
    partial_coverage: tuple[MissingSection, ...]
    cells: tuple[BlindCell, ...]
    assessed_at: str
    rubric_set_id: str = ""
    rubric_set_version: str = ""
    rubric_set_fingerprint: str = ""
    scorecard_id: str = ""
    scorecard_version: str = ""
    task_label: str = BLIND_TASK_LABEL
    esr_availability: str = "unknown"
    intake_id: str = ""
    snapshot_id: str = ""
    package_id: str = ""
    policy_version: str = ""
    evidence_view: str = ""
    evidence_source: str = EVIDENCE_SOURCE_DIRECTORY
    notes: str = _ADVISORY_NOTE
    advisory: bool = True
    blocking: bool = False

    def __post_init__(self) -> None:
        if self.task_label != BLIND_TASK_LABEL:
            raise ValueError(
                f"BlindAssessmentReport.task_label must be {BLIND_TASK_LABEL!r}, got "
                f"{self.task_label!r} — an ESR-informed review is a separately labelled "
                "task and never shares the blind label."
            )
        if self.evidence_source not in (EVIDENCE_SOURCE_DEV_GRAPH, EVIDENCE_SOURCE_DIRECTORY):
            raise ValueError(f"unknown evidence_source {self.evidence_source!r}.")
        if self.evidence_source == EVIDENCE_SOURCE_DEV_GRAPH and not self.package_id:
            raise ValueError("a dev-graph evidence source needs a package_id.")
        if self.esr_availability not in ESR_AVAILABILITY:
            raise ValueError(
                f"unknown esr_availability {self.esr_availability!r}; one of {sorted(ESR_AVAILABILITY)}."
            )
        if self.advisory is not True:
            raise ValueError(
                "BlindAssessmentReport.advisory must be True — the blind assessment "
                "advises a human, never a run."
            )
        if self.blocking is not False:
            raise ValueError(
                "BlindAssessmentReport.blocking must be False — no eval metric may "
                "wire into the runtime DAG as a fail-closed gate."
            )
        if not str(self.candidate_hash).startswith("sha256:"):
            raise ValueError("BlindAssessmentReport.candidate_hash must be a sha256: hash.")
        if self.scope not in (SCOPE_COMPLETE, SCOPE_PARTIAL):
            raise ValueError(f"unknown scope {self.scope!r}.")
        if (self.scope == SCOPE_PARTIAL) != bool(self.partial_coverage):
            raise ValueError(
                "scope must be 'partial' exactly when partial_coverage is non-empty."
            )
        for cell in self.cells:
            for attr in ("candidate_hash", "profile_version", "assessor_pin"):
                if getattr(cell, attr) != getattr(self, attr):
                    raise ValueError(
                        f"cell {cell.expectation_key}/{cell.section_id} carries "
                        f"{attr} {getattr(cell, attr)!r}, the report "
                        f"{getattr(self, attr)!r} — every cell must be bound to the "
                        "report's candidate, profile and assessor."
                    )

    @property
    def summary(self) -> dict[str, Any]:
        by_criterion: dict[str, dict[str, Any]] = {}
        for cell in self.cells:
            entry = by_criterion.setdefault(
                cell.criterion_id, {"cells": 0, "covered": 0, "clean_pass": 0, "scores": []}
            )
            entry["cells"] += 1
            entry["covered"] += int(cell.coverage.judge_passed is True)
            entry["clean_pass"] += int(cell.coverage.passed)
            if cell.coverage.score is not None:
                entry["scores"].append(float(cell.coverage.score))
        criteria = {
            cid: {
                "cells": e["cells"],
                "covered": e["covered"],
                "clean_pass": e["clean_pass"],
                "mean_score": (sum(e["scores"]) / len(e["scores"])) if e["scores"] else None,
            }
            for cid, e in by_criterion.items()
        }
        return {
            "scope": self.scope,
            "cells": len(self.cells),
            "covered": sum(1 for c in self.cells if c.coverage.judge_passed is True),
            "clean_pass": sum(1 for c in self.cells if c.coverage.passed),
            "missing_sections": len(self.partial_coverage),
            "criteria": criteria,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": BLIND_REPORT_RECORD_TYPE,
            "metric": BLIND_ASSESSMENT_METRIC,
            "advisory": self.advisory,
            "blocking": self.blocking,
            "candidate_hash": self.candidate_hash,
            "candidate_path": self.candidate_path,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "assessor_model": self.assessor_model,
            "assessor_version": self.assessor_version,
            "assessor_pin": self.assessor_pin,
            "scope": self.scope,
            "partial_coverage": [m.to_dict() for m in self.partial_coverage],
            "assessed_at": self.assessed_at,
            "rubric_set_id": self.rubric_set_id,
            "rubric_set_version": self.rubric_set_version,
            "rubric_set_fingerprint": self.rubric_set_fingerprint,
            "scorecard_id": self.scorecard_id,
            "scorecard_version": self.scorecard_version,
            "task_label": self.task_label,
            "esr_availability": self.esr_availability,
            "intake_id": self.intake_id,
            "snapshot_id": self.snapshot_id,
            "package_id": self.package_id,
            "policy_version": self.policy_version,
            "evidence_view": self.evidence_view,
            "evidence_source": self.evidence_source,
            "notes": self.notes,
            "summary": self.summary,
            "cells": [c.to_dict() for c in self.cells],
        }


# --------------------------------------------------------------------------- #
# Assessment
# --------------------------------------------------------------------------- #


def _check_intake(intake: EsrIntake | None, evidence: BlindEvidence | None) -> None:
    if intake is None:
        return
    if intake.permitted_purpose != BLIND_TASK_LABEL:
        raise BlindAssessmentError(
            f"intake {intake.intake_id} permits {intake.permitted_purpose!r}, not "
            f"{BLIND_TASK_LABEL!r}; that is a separately labelled task, never a blind assessment."
        )
    if evidence is None:
        raise BlindAssessmentError(
            f"intake {intake.intake_id} binds document {intake.document_id!r}, but a candidate "
            "directory names no document; assess through the document route to stamp an intake."
        )
    if intake.document_id != evidence.document_id:
        raise BlindAssessmentError(
            f"intake {intake.intake_id} concerns document {intake.document_id!r}, "
            f"the assessed document is {evidence.document_id!r}."
        )


def assess_candidate(
    judge: Judge,
    bundle: ProfileBundle,
    candidate_dir: Path | str | None = None,
    *,
    evidence: BlindEvidence | None = None,
    intake: EsrIntake | None = None,
    token_budget: int = DEFAULT_PACK_TOKEN_BUDGET,
    span_budget_fraction: float = DEFAULT_SPAN_BUDGET_FRACTION,
    n: int = MIN_MAJORITY_SAMPLES,
    clock: Clock | None = None,
) -> BlindAssessmentReport:
    """Assess one candidate against *bundle* with *judge*; return the bound report.

    The candidate is either a directory of section artifacts
    (*candidate_dir*) or the materialised evidence of the document route
    (*evidence*, from :func:`build_blind_evidence`); exactly one is given.
    Every rubric is graded over each present section its criterion maps to
    (:func:`~harness.expectation_coverage.grade_expectation`: versioned pack,
    N≥3 majority, provenance).  Missing sections are skipped and reported as
    partial coverage.  A malformed assessor response propagates as a
    :class:`~harness.judge.JudgeResponseError`; nothing is written here.

    *intake*, when given, must permit a blind assessment and concern the
    assessed document; its ESR availability is stamped on the report.
    """
    if n < MIN_MAJORITY_SAMPLES:
        raise BlindAssessmentError(
            f"n must be at least {MIN_MAJORITY_SAMPLES} (the majority rule); got {n}."
        )
    if (candidate_dir is None) == (evidence is None):
        raise BlindAssessmentError("give exactly one of candidate_dir or evidence.")
    _check_intake(intake, evidence)
    if evidence is not None:
        assert_no_leakage(evidence.package)
        source: Path | str = evidence.candidate_dir
    elif candidate_dir is not None:
        source = candidate_dir
    else:  # pragma: no cover - excluded by the check above
        raise BlindAssessmentError("give exactly one of candidate_dir or evidence.")
    candidate = load_candidate(source, bundle.profile)
    digest = candidate_hash(candidate)
    pin = assessor_pin(judge)
    cells: list[BlindCell] = []
    for rubric in bundle.rubric_set.rubrics:
        for section_id in bundle.profile.section_ids_for(rubric.criterion_id):
            path = candidate.sections.get(section_id)
            if path is None:
                continue
            coverage = grade_expectation(
                judge,
                rubric,
                path,
                token_budget=token_budget,
                span_budget_fraction=span_budget_fraction,
                n=n,
            )
            cells.append(
                BlindCell(
                    criterion_id=rubric.criterion_id,
                    expectation_key=rubric.expectation_key,
                    section_id=section_id,
                    candidate_hash=digest,
                    profile_version=bundle.version,
                    assessor_pin=pin,
                    coverage=coverage,
                )
            )
    rubric_set = bundle.rubric_set
    return BlindAssessmentReport(
        candidate_hash=digest,
        candidate_path=candidate.root.as_posix(),
        profile_id=bundle.profile_id,
        profile_version=bundle.version,
        assessor_model=judge.config.model,
        assessor_version=judge.config.version,
        assessor_pin=pin,
        scope=candidate.scope,
        partial_coverage=candidate.missing,
        cells=tuple(cells),
        assessed_at=(clock or _utc_now)(),
        rubric_set_id=rubric_set.rubric_set_id,
        rubric_set_version=rubric_set.version,
        rubric_set_fingerprint=rubric_set.fingerprint,
        scorecard_id=rubric_set.scorecard_id,
        scorecard_version=rubric_set.scorecard_version,
        task_label=BLIND_TASK_LABEL,
        esr_availability=intake.esr_availability if intake is not None else "unknown",
        intake_id=intake.intake_id if intake is not None else "",
        snapshot_id=evidence.snapshot_id if evidence is not None else "",
        package_id=evidence.package.package_id if evidence is not None else "",
        policy_version=str(evidence.package.manifest["policy_version"]) if evidence is not None else "",
        evidence_view=str(evidence.package.manifest["view"]) if evidence is not None else "",
        evidence_source=EVIDENCE_SOURCE_DEV_GRAPH if evidence is not None else EVIDENCE_SOURCE_DIRECTORY,
    )


# --------------------------------------------------------------------------- #
# Persistence — new file per run, never overwrite; reject on hash mismatch
# --------------------------------------------------------------------------- #


def _next_report_path(reports_dir: Path, digest: str) -> Path:
    short = digest.split(":", 1)[1][:12]
    taken = 0
    if reports_dir.is_dir():
        for existing in reports_dir.iterdir():
            m = _REPORT_NAME_RE.match(existing.name)
            if m and m.group("hash") == short:
                taken = max(taken, int(m.group("seq")))
    return reports_dir / f"blind_{short}_{taken + 1:04d}.json"


def write_report(
    report: BlindAssessmentReport, reports_dir: Path | str, *, path: Path | None = None
) -> Path:
    """Write *report* as a new file under *reports_dir* and return its path.

    The default name is ``blind_<hash12>_<NNNN>.json`` with the next free
    sequence number for this candidate hash.  An existing path — default or
    explicit — is never overwritten: historical reports are immutable.
    """
    out_dir = Path(reports_dir)
    target = Path(path) if path is not None else _next_report_path(out_dir, report.candidate_hash)
    if target.exists():
        raise BlindAssessmentError(
            f"report {target} already exists — historical reports are immutable; "
            "a rerun writes a new file."
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(report.to_dict(), target, prefix="blind_assessment_")
    return target


def load_report(
    path: Path | str,
    candidate_dir: Path | str,
    profile: PreEvaluationProfile,
    *,
    profile_version: str | None = None,
) -> dict[str, Any]:
    """Load a persisted report and bind-check it against the candidate on disk.

    Rejects a file that is not a blind assessment record, one whose advisory/
    blocking flags were tampered with, one whose candidate hash differs from
    the recomputed hash of *candidate_dir* (:class:`CandidateHashMismatch`,
    naming both hashes), and — when *profile_version* is given — one produced
    under a different profile version.
    """
    p = Path(path)
    if not p.is_file():
        raise BlindAssessmentError(f"report file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise BlindAssessmentError(f"report {p} is not valid JSON: {exc}") from exc
    if not isinstance(data, Mapping) or data.get("record_type") != BLIND_REPORT_RECORD_TYPE:
        raise BlindAssessmentError(f"{p} is not a {BLIND_REPORT_RECORD_TYPE!r} record.")
    if data.get("advisory") is not True or data.get("blocking") is not False:
        raise BlindAssessmentError(
            f"report {p} must carry advisory=true and blocking=false; got "
            f"advisory={data.get('advisory')!r}, blocking={data.get('blocking')!r}."
        )
    if data.get("task_label", BLIND_TASK_LABEL) != BLIND_TASK_LABEL:
        raise BlindAssessmentError(
            f"report {p} carries task_label {data.get('task_label')!r}; only a "
            f"{BLIND_TASK_LABEL!r} report is a blind assessment."
        )
    recorded = str(data.get("candidate_hash", ""))
    current = candidate_hash(load_candidate(candidate_dir, profile))
    if recorded != current:
        raise CandidateHashMismatch(
            f"report {p} was produced over candidate hash {recorded}, but the "
            f"candidate at {Path(candidate_dir).as_posix()} now hashes to {current} — "
            "the report does not describe this candidate."
        )
    if profile_version is not None and data.get("profile_version") != profile_version:
        raise BlindAssessmentError(
            f"report {p} was produced under profile version "
            f"{data.get('profile_version')!r}, not {profile_version!r}."
        )
    for i, cell in enumerate(data.get("cells", [])):
        if not isinstance(cell, Mapping):
            raise BlindAssessmentError(f"report {p}: cells[{i}] is not an object.")
        for attr in ("candidate_hash", "profile_version", "assessor_pin"):
            if cell.get(attr) != data.get(attr):
                raise BlindAssessmentError(
                    f"report {p}: cells[{i}] carries {attr} {cell.get(attr)!r}, the "
                    f"report {data.get(attr)!r} — the cell is not bound to this report."
                )
    return dict(data)


# --------------------------------------------------------------------------- #
# Rendering — ASCII-safe
# --------------------------------------------------------------------------- #


def _ascii(text: str) -> str:
    return str(text).encode("ascii", "backslashreplace").decode("ascii")


def _fmt_bool(value: Any) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "-"


def render_report(report: Mapping[str, Any]) -> str:
    """Render a report dict (fresh ``to_dict()`` or a loaded file) as text."""
    cells = report.get("cells", [])
    if not isinstance(cells, list):
        raise BlindAssessmentError("report 'cells' must be an array.")
    scope = str(report.get("scope", "")).upper()
    header = (
        f"BLIND ASSESSMENT [{scope}] - {len(cells)} cell(s)\n"
        f"candidate: {str(report.get('candidate_hash') or '')[:19]}  "
        f"{report.get('candidate_path', '')}\n"
        f"profile:   {report.get('profile_id', '') or '-'} "
        f"[{str(report.get('profile_version') or '')[:19]}]  "
        f"assessor: {report.get('assessor_pin', '-')}\n"
        f"advisory={report.get('advisory')} blocking={report.get('blocking')}\n"
    )
    lines = [header]
    if report.get("package_id"):
        lines.append(
            f"evidence:  source={report.get('evidence_source', '-')} view={report.get('evidence_view', '-')} "
            f"package={str(report.get('package_id') or '')[:19]} "
            f"snapshot={str(report.get('snapshot_id') or '')[:19]} "
            f"esr={report.get('esr_availability', 'unknown')}"
            + (f" intake={report['intake_id']}" if report.get("intake_id") else "")
            + "\n"
        )
    else:
        lines.append(
            f"evidence:  source={report.get('evidence_source', EVIDENCE_SOURCE_DIRECTORY)} "
            "(no dev-graph package; the leakage guard did not run)\n"
        )
    missing = report.get("partial_coverage") or []
    if missing:
        lines.append("PARTIAL COVERAGE - required sections missing from the candidate:")
        for m in missing:
            lines.append(f"  - {m.get('section_id')} (criterion {m.get('criterion_id')})")
        lines.append("")
    rows: list[tuple[str, ...]] = [("criterion", "expectation", "section", "covered", "clean", "score")]
    for cell in cells:
        score = cell.get("score")
        rows.append(
            (
                str(cell.get("criterion_id", "")),
                str(cell.get("expectation_key", "")),
                str(cell.get("section_id", "")),
                _fmt_bool(cell.get("covered")),
                _fmt_bool(cell.get("clean_pass")),
                f"{score:.2f}" if isinstance(score, (int, float)) else "-",
            )
        )
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    for i, row in enumerate(rows):
        lines.append("  ".join(col.ljust(widths[j]) for j, col in enumerate(row)).rstrip())
        if i == 0:
            lines.append("  ".join("-" * w for w in widths))
    summary = report.get("summary")
    if summary:
        lines.append("")
        lines.append(
            "summary: "
            + json.dumps(summary, sort_keys=True, ensure_ascii=True, separators=(", ", ": "))
        )
    return _ascii("\n".join(lines))
