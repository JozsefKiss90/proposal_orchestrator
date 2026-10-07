"""
The operator review table over a written ESR comparison (ticket R02).

PE-08 resolved every reference the dispositions declared, but the dispositions
and the proposed revisions were drafted by Claude.  A human has to read them.
This module renders that reading material: one Markdown report covering each
historical observation exactly once, and a short companion listing only the
decisions the operator has to take.

What it measures and what it carries
------------------------------------
Measured here, every run:

* every input the comparison names is re-hashed on disk and refused on a
  mismatch (the ESR record, the dispositions, the fidelity register, each
  integrity audit, the frozen baseline report, the candidate's content hash);
* every reference the comparison recorded is resolved again through the
  comparison's own resolvers, against the artifact it names, and its text is
  compared with the text the comparison recorded;
* every count in the report is recomputed from the rows and cross-checked
  against the comparison's own summary.

Carried, never computed: the operator-facing judgments of the review notes
(:data:`REVIEW_NOTES_RECORD_TYPE`) — whether a resolved reference supports the
same proposition as the ESR observation, what the ESR actually complains of,
the uncertainty, the recommendation and the decision the operator must take.
Those are declarations.  The notes are agent-drafted and say so: the only
permitted review state is :data:`REVIEW_STATE_PENDING`, so no rendering of
this artifact can read as operator approval.

The separation the ticket asks for
----------------------------------
Reference validity and semantic agreement are two fields, not one.  A blind
finding can resolve perfectly against the baseline and still be about a
different proposition than the ESR sentence it was filed under; that is the
subject of R03, and this report is where such a row is named and handed over.
A notes record may then name the adjudication record that took the row up
(``adjudication_record``, recommendation ``adjudicated``). The report lists it
among its inputs with its own hash, and the row still names the decision left
for the operator: an adjudication is a reading and not an approval.
Counts keep strengths apart from criticisms for the same reason: the
comparison's ``independently_detected`` rows include strengths the blind lane
praised as the evaluators did, and nothing here may present that total as
criticisms caught.

Nothing is interpreted: this module never changes a disposition, never writes
a revision and never calls an assessor.  It writes two Markdown files under
its output directory and overwrites neither (the sequence number follows the
comparison writer's).

Constitutional standing: an advisory Tier 4 artifact, never run-blocking.  It
evaluates no gate, invokes no Claude and coins no ``schema_id``.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from runner.atomic_write import atomic_write_text
from harness.blind_assessment import (
    BlindAssessmentError,
    Candidate,
    PreEvaluationProfile,
    candidate_hash,
    load_candidate,
    next_report_path,
)
from harness.blind_baseline import FrozenBaseline, _portable, load_frozen_baseline
from harness.esr_comparison import (
    DECLARED_STATUSES,
    DISPOSITION_ADDRESSED,
    DISPOSITION_INDEPENDENTLY_DETECTED,
    DISPOSITION_NOT_ASSESSABLE,
    DISPOSITION_NOT_DETECTED,
    DISPOSITION_PARTIALLY_OBSERVABLE,
    DISPOSITIONS,
    LANE_AUDIT,
    LANE_BLIND,
    OBSERVATION_KIND_MINOR,
    OBSERVATION_KIND_SHORTCOMING,
    OBSERVATION_KIND_STRENGTH,
    EsrComparisonError,
    load_audits,
    load_comparison,
    load_esr_record,
    load_register,
    resolve_audit_reference,
    resolve_blind_reference,
    resolve_register_pointer,
    verify_evidence,
)
from harness.evidence_preflight import file_sha256

REVIEW_NOTES_RECORD_TYPE = "esr_review_notes"
REVIEW_SCHEMA_VERSION = "1.0"

#: The only review state a notes file may declare.  An agent drafts; the
#: operator decides elsewhere.  There is deliberately no "approved" value:
#: approval is recorded by the operator in R05, not by this artifact.
REVIEW_STATE_PENDING = "agent_drafted_pending_operator_review"
REVIEW_STATES: tuple[str, ...] = (REVIEW_STATE_PENDING,)

#: Does the resolved evidence support the same proposition as the ESR sentence?
AGREEMENT_AGREED = "agreed"
AGREEMENT_DISPUTED = "disputed"
AGREEMENT_UNRESOLVED = "unresolved"
AGREEMENT_NOT_APPLICABLE = "not_applicable"
AGREEMENTS: tuple[str, ...] = (
    AGREEMENT_AGREED,
    AGREEMENT_DISPUTED,
    AGREEMENT_UNRESOLVED,
    AGREEMENT_NOT_APPLICABLE,
)

#: What the ESR complains of: a detail the proposal does not carry, or one it
#: carries without explaining it well enough.  The ticket asks for the
#: distinction; ``other`` covers an observation that faults neither, such as a
#: misalignment between two things both present.
COMPLAINT_ABSENT = "absent_detail"
COMPLAINT_INADEQUATE = "inadequately_explained"
COMPLAINT_BOTH = "both"
COMPLAINT_OTHER = "other"
COMPLAINT_NOT_APPLICABLE = "not_applicable"
COMPLAINTS: tuple[str, ...] = (
    COMPLAINT_ABSENT,
    COMPLAINT_INADEQUATE,
    COMPLAINT_BOTH,
    COMPLAINT_OTHER,
    COMPLAINT_NOT_APPLICABLE,
)

#: What the reviewer recommends happen to the row next.  ``adjudicated`` is for
#: a row a later semantic adjudication has taken up: the reasoning lives in the
#: record the notes name in ``adjudication_record``, and what is left for the
#: human is still named in ``operator_decision``.  It is not an approval.
RECOMMENDATION_RETAIN = "retain"
RECOMMENDATION_R03 = "revisit_in_r03"
RECOMMENDATION_ADJUDICATED = "adjudicated"
RECOMMENDATION_AFTER_DECLARATION = "revisit_after_declaration"
RECOMMENDATION_AFTER_PRIVATE_NETWORK = "revisit_after_private_network"
RECOMMENDATIONS: tuple[str, ...] = (
    RECOMMENDATION_RETAIN,
    RECOMMENDATION_R03,
    RECOMMENDATION_ADJUDICATED,
    RECOMMENDATION_AFTER_DECLARATION,
    RECOMMENDATION_AFTER_PRIVATE_NETWORK,
)

CRITICISM_KINDS: tuple[str, ...] = (OBSERVATION_KIND_SHORTCOMING, OBSERVATION_KIND_MINOR)

_REVIEW_PREFIX = "operator_review"
_DECISIONS_PREFIX = "operator_decisions"
_MARKDOWN_SUFFIX = ".md"

_PROVISIONAL = (
    "Every recommendation, uncertainty and proposed revision in this report is "
    "agent-drafted and provisional. None of it is an operator decision, and "
    "nothing here records one."
)
_ADVISORY = (
    "Advisory to a human, never run-blocking (`harness/HARNESS.md`): this report "
    "evaluates no gate and blocks no phase. Its inputs carry `advisory: true` and "
    "`blocking: false`, and so do the review notes it rests on."
)
_SCORE_WARNING = (
    "Criterion scores are compared in the comparison artifact and are not "
    "re-interpreted here. No deduction is attributed to any individual "
    "criticism."
)


class OperatorReviewError(BlindAssessmentError):
    """A review input that cannot be used; nothing is written."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _count_warning(counts: Mapping[str, Any]) -> str:
    """The detection count, stated so it cannot be read as criticisms caught."""
    criticisms = counts["criticisms"]["by_disposition"][DISPOSITION_INDEPENDENTLY_DETECTED]
    strengths = counts["strengths"]["by_disposition"][DISPOSITION_INDEPENDENTLY_DETECTED]
    return (
        f"Of the {criticisms + strengths} rows the comparison calls "
        f"`{DISPOSITION_INDEPENDENTLY_DETECTED}`, {strengths} are strengths the blind lane "
        f"praised as the evaluators did and {criticisms} are criticisms it caught. The two "
        "are counted apart below."
    )


# --------------------------------------------------------------------------- #
# The notes: the declared half of this report
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ReviewNotes:
    """The agent-drafted review judgments, one row per observation."""

    path: Path
    sha256: str
    data: Mapping[str, Any]
    rows: Mapping[str, Mapping[str, Any]]

    @property
    def comparison(self) -> str:
        return str(self.data.get("comparison") or "")

    @property
    def comparison_sha256(self) -> str:
        return str(self.data.get("comparison_sha256") or "")

    @property
    def review_state(self) -> str:
        return str(self.data.get("review_state") or "")

    @property
    def declared_by(self) -> str:
        return str(self.data.get("declared_by") or "")

    @property
    def supersession_note(self) -> str:
        """Why this notes record exists beside an earlier one, or ``""``.

        A later ticket may re-read a comparison the first notes already read.
        The note says what changed and what did not. The report prints it, so a
        reader of the second rendering is not left to diff the two.
        """
        return str(self.data.get("supersession_note") or "")

    @property
    def adjudication_record(self) -> str:
        """Repository path of the semantic adjudication record, or ``""``.

        A later ticket may adjudicate rows this file first drafted. The notes
        then name the record that holds the reasoning, and the report lists it
        among its inputs with its own hash.
        """
        return str(self.data.get("adjudication_record") or "")


def _text(row: Mapping[str, Any], key: str, *, label: str, required: bool) -> str | None:
    value = row.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise OperatorReviewError(f"{label}: {key!r} is required and must not be empty.")
        return None
    if not isinstance(value, str):
        raise OperatorReviewError(f"{label}: {key!r} must be text, not {type(value).__name__}.")
    return value.strip()


def _one_of(row: Mapping[str, Any], key: str, allowed: Sequence[str], *, label: str) -> str:
    value = row.get(key)
    if value not in allowed:
        raise OperatorReviewError(
            f"{label}: {key!r} is {value!r}; one of {', '.join(allowed)} is required."
        )
    return str(value)


def load_review_notes(path: Path | str) -> ReviewNotes:
    """Load the review notes, fail-closed on shape and vocabulary.

    A row needs a judgment (``semantic_agreement``), the basis for it, the
    status of that judgment in the four categories of CLAUDE.md §12.2, what
    the ESR complains of, and a recommendation.  A row that is anything other
    than "agreed, retain" needs a concrete question for the operator: a
    disputed row without one hands the operator a disagreement and no decision
    to take.
    """
    p = Path(path)
    try:
        raw = p.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise OperatorReviewError(f"review notes {p} cannot be read: {exc}") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OperatorReviewError(f"review notes {p} are not valid JSON: {exc}") from exc
    if not isinstance(data, Mapping) or data.get("record_type") != REVIEW_NOTES_RECORD_TYPE:
        raise OperatorReviewError(f"{p} is not an {REVIEW_NOTES_RECORD_TYPE!r} record.")
    for key in (
        "schema_version",
        "comparison",
        "comparison_sha256",
        "declared_by",
        "declared_on",
        "review_state",
    ):
        if not isinstance(data.get(key), str) or not str(data[key]).strip():
            raise OperatorReviewError(f"review notes {p} lack {key!r}.")
    if data["schema_version"] != REVIEW_SCHEMA_VERSION:
        raise OperatorReviewError(
            f"review notes {p} are schema version {data['schema_version']!r}; this module "
            f"reads {REVIEW_SCHEMA_VERSION!r}."
        )
    if data.get("advisory") is not True or data.get("blocking") is not False:
        raise OperatorReviewError(
            f"review notes {p} must carry advisory=true and blocking=false: the review is "
            "advisory to a human and gates nothing (harness/HARNESS.md)."
        )
    if data["review_state"] not in REVIEW_STATES:
        raise OperatorReviewError(
            f"review notes {p}: review_state is {data['review_state']!r}; only "
            f"{', '.join(REVIEW_STATES)} is permitted. An agent-drafted review never "
            "records operator approval."
        )
    if "adjudication_record" in data and not (
        isinstance(data["adjudication_record"], str) and data["adjudication_record"].strip()
    ):
        raise OperatorReviewError(
            f"review notes {p}: 'adjudication_record' must be the repository path of the "
            "record that holds the adjudication reasoning, or absent."
        )
    if "supersession_note" in data:
        _text(data, "supersession_note", label=f"review notes {p}", required=True)
    rows = data.get("rows")
    if not isinstance(rows, list) or not rows:
        raise OperatorReviewError(f"review notes {p} hold no rows.")
    by_id: dict[str, Mapping[str, Any]] = {}
    for position, row in enumerate(rows):
        if not isinstance(row, Mapping) or not isinstance(row.get("observation_id"), str):
            raise OperatorReviewError(f"review notes {p}: row {position} needs an observation_id.")
        oid = row["observation_id"]
        label = f"review note {oid}"
        if oid in by_id:
            raise OperatorReviewError(f"review notes {p}: observation {oid} is reviewed twice.")
        agreement = _one_of(row, "semantic_agreement", AGREEMENTS, label=label)
        _one_of(row, "esr_complaint", COMPLAINTS, label=label)
        recommendation = _one_of(row, "recommendation", RECOMMENDATIONS, label=label)
        _one_of(row, "declared_status", DECLARED_STATUSES, label=label)
        _one_of(row, "recommended_disposition", DISPOSITIONS, label=label)
        _text(row, "agreement_basis", label=label, required=True)
        _text(row, "uncertainty", label=label, required=False)
        decision = _text(row, "operator_decision", label=label, required=False)
        if decision is None and (
            agreement != AGREEMENT_AGREED or recommendation != RECOMMENDATION_RETAIN
        ):
            raise OperatorReviewError(
                f"{label}: semantic_agreement {agreement!r} with recommendation "
                f"{recommendation!r} needs an 'operator_decision' naming the question to "
                "put to the operator."
            )
        by_id[oid] = row
    return ReviewNotes(path=p, sha256=file_sha256(p), data=data, rows=by_id)


# --------------------------------------------------------------------------- #
# The inputs: re-hashed, re-bound, nothing taken on the comparison's word
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class InputRecord:
    """One row of the report's input inventory."""

    role: str
    path: str
    sha256: str | None
    note: str


@dataclass(frozen=True)
class ResolvedInputs:
    """Everything the comparison names, loaded and re-bound."""

    comparison_path: Path
    comparison_sha256: str
    #: The root every path in the report is written relative to, so the
    #: rendering does not depend on the directory the command ran from.
    repo_root: Path
    comparison: Mapping[str, Any]
    esr: Mapping[str, Any]
    baseline_report: Mapping[str, Any]
    frozen: FrozenBaseline
    candidate: Candidate
    historical_candidate: Candidate | None
    register: Mapping[str, Any]
    audits: Mapping[str, Any]
    inventory: tuple[InputRecord, ...]


def _under(repo_root: Path, raw: str) -> Path:
    p = Path(raw)
    return p if p.is_absolute() else repo_root / p


def _expect_sha(path: Path, declared: Any, *, role: str) -> str:
    if not path.is_file():
        raise OperatorReviewError(f"the comparison names {role} at {path}, which is not a file.")
    actual = file_sha256(path)
    if isinstance(declared, str) and declared and actual != declared:
        raise OperatorReviewError(
            f"{role} at {path} hashes to {actual[:12]}, the comparison recorded "
            f"{declared[:12]}. The review is refused: the artifact moved under the report."
        )
    return actual


def resolve_inputs(
    comparison_path: Path | str,
    *,
    repo_root: Path,
    profile: PreEvaluationProfile,
) -> ResolvedInputs:
    """Load the comparison and every artifact it names, re-hashing each one.

    The review takes its inputs from the comparison rather than from the
    command line on purpose: a report that could be rendered against a
    different ESR record or a different candidate than the comparison used
    would be a new interpretation wearing the comparison's bindings.
    """
    cmp_path = Path(comparison_path)
    try:
        data = load_comparison(cmp_path)
    except EsrComparisonError as exc:
        raise OperatorReviewError(str(exc)) from exc
    cmp_sha = file_sha256(cmp_path)
    inventory: list[InputRecord] = [
        InputRecord(
            role="comparison report",
            path=_portable(cmp_path, repo_root),
            sha256=cmp_sha,
            note="the PE-08 output this review reads; not modified",
        )
    ]

    esr_block = data.get("esr_record") or {}
    esr_path = _under(repo_root, str(esr_block.get("path") or ""))
    esr_sha = _expect_sha(esr_path, esr_block.get("sha256"), role="the ESR record")
    try:
        esr = load_esr_record(esr_path)
    except EsrComparisonError as exc:
        raise OperatorReviewError(str(exc)) from exc
    inventory.append(
        InputRecord(
            role="ESR record",
            path=_portable(esr_path, repo_root),
            sha256=esr_sha,
            note="the historical evaluation summary, verbatim; the observation id set is its own",
        )
    )

    disp_block = data.get("dispositions") or {}
    disp_path = _under(repo_root, str(disp_block.get("path") or ""))
    disp_sha = _expect_sha(disp_path, disp_block.get("sha256"), role="the dispositions")
    inventory.append(
        InputRecord(
            role="dispositions",
            path=_portable(disp_path, repo_root),
            sha256=disp_sha,
            note="the declared half of the comparison, drafted by Claude and under review here",
        )
    )

    baseline_block = data.get("baseline") or {}
    baseline_dir = _under(repo_root, str(baseline_block.get("baseline_dir") or ""))
    try:
        frozen = load_frozen_baseline(baseline_dir)
    except BlindAssessmentError as exc:
        raise OperatorReviewError(str(exc)) from exc
    report_sha = str(frozen.record.get("report_sha256") or "")
    if report_sha != baseline_block.get("report_sha256"):
        raise OperatorReviewError(
            f"the frozen baseline at {baseline_dir} is report {report_sha[:12]}, the "
            f"comparison was built over {str(baseline_block.get('report_sha256'))[:12]}."
        )
    baseline_report = json.loads(frozen.copy_path.read_text(encoding="utf-8-sig"))
    inventory.append(
        InputRecord(
            role="frozen blind baseline",
            path=_portable(frozen.copy_path, repo_root),
            sha256=report_sha,
            note=f"assessor {baseline_block.get('assessor_pin')}; no new assessor call was made",
        )
    )

    cand_block = data.get("candidate") or {}
    cand_dir = _under(repo_root, str(cand_block.get("path") or ""))
    try:
        candidate = load_candidate(cand_dir, profile)
    except BlindAssessmentError as exc:
        raise OperatorReviewError(str(exc)) from exc
    actual_hash = candidate_hash(candidate)
    if actual_hash != cand_block.get("candidate_hash"):
        raise OperatorReviewError(
            f"the candidate at {cand_dir} hashes to {actual_hash[:19]}, the comparison "
            f"was built over {str(cand_block.get('candidate_hash'))[:19]}."
        )
    inventory.append(
        InputRecord(
            role="candidate",
            path=_portable(cand_dir, repo_root),
            sha256=actual_hash,
            note="the materialised sanitised copy every quote below is checked against",
        )
    )

    historical: Candidate | None = None
    hist_block = data.get("historical_candidate") or {}
    if hist_block.get("path"):
        hist_dir = _under(repo_root, str(hist_block["path"]))
        try:
            historical = load_candidate(hist_dir, profile)
        except BlindAssessmentError as exc:
            raise OperatorReviewError(str(exc)) from exc
        hist_hash = candidate_hash(historical)
        if hist_hash != hist_block.get("candidate_hash"):
            raise OperatorReviewError(
                f"the historical candidate at {hist_dir} hashes to {hist_hash[:19]}, the "
                f"comparison was built over {str(hist_block.get('candidate_hash'))[:19]}."
            )
        inventory.append(
            InputRecord(
                role="historical candidate",
                path=_portable(hist_dir, repo_root),
                sha256=hist_hash,
                note="the earlier sanitised copy; historical quotes resolve here",
            )
        )

    reg_block = data.get("fidelity_register") or {}
    reg_path = _under(repo_root, str(reg_block.get("path") or ""))
    reg_sha = _expect_sha(reg_path, reg_block.get("sha256"), role="the fidelity register")
    try:
        register = load_register(reg_path).data
    except EsrComparisonError as exc:
        raise OperatorReviewError(str(exc)) from exc
    inventory.append(
        InputRecord(
            role="fidelity register",
            path=_portable(reg_path, repo_root),
            sha256=reg_sha,
            note=(
                "the register this comparison binds; the derived half is measured and the "
                "declared half is the operator's (ticket R01). Another revision's register, "
                "where one exists, is not an input of this report"
            ),
        )
    )

    declared_audit_paths: list[str] = []
    audit_paths: list[str] = []
    for entry in data.get("audits") or []:
        declared = str(entry.get("path") or "")
        a_path = _under(repo_root, declared)
        a_sha = _expect_sha(a_path, entry.get("sha256"), role="an integrity audit")
        declared_audit_paths.append(declared)
        audit_paths.append(str(a_path))
        inventory.append(
            InputRecord(
                role="integrity audit",
                path=_portable(a_path, repo_root),
                sha256=a_sha,
                note=f"over candidate {str(entry.get('candidate_hash'))[:19]}",
            )
        )
    try:
        loaded = load_audits(audit_paths, repo_root=repo_root)
    except EsrComparisonError as exc:
        raise OperatorReviewError(str(exc)) from exc
    # Key the audits by the spelling the comparison's own references use, so a
    # reference resolves against the report the comparison named.
    audits = dict(zip(declared_audit_paths, loaded.values()))

    return ResolvedInputs(
        comparison_path=cmp_path,
        comparison_sha256=cmp_sha,
        repo_root=Path(repo_root),
        comparison=data,
        esr=esr.data,
        baseline_report=baseline_report,
        frozen=frozen,
        candidate=candidate,
        historical_candidate=historical,
        register=register,
        audits=audits,
        inventory=tuple(inventory),
    )


# --------------------------------------------------------------------------- #
# References: resolved again, and to the same text
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ReferenceCheck:
    """How many references of one row resolved, by kind."""

    blind: int
    audit: int
    current_quotes: int
    historical_quotes: int
    register_entries: int

    @property
    def total(self) -> int:
        return (
            self.blind
            + self.audit
            + self.current_quotes
            + self.historical_quotes
            + self.register_entries
        )


def _same_text(recorded: Any, resolved: Any, *, label: str, what: str) -> None:
    """Refuse when a reference now resolves to text other than the recorded one."""
    if not isinstance(recorded, str) or not recorded:
        return
    if str(resolved).strip() != recorded.strip():
        raise OperatorReviewError(
            f"{label}: {what} resolves to text the comparison did not record. "
            f"recorded {recorded[:60]!r}..., resolved {str(resolved)[:60]!r}...; "
            "the review is refused rather than quoting either."
        )


def check_references(row: Mapping[str, Any], inputs: ResolvedInputs) -> ReferenceCheck:
    """Resolve every reference of one comparison row against its named artifact.

    Uses the comparison's own resolvers, so a reference that resolved when the
    comparison was written and does not resolve now is a refusal here, naming
    the row.  Resolution is a measurement; whether the resolved text supports
    the ESR sentence is a separate, declared field.
    """
    oid = str(row.get("observation_id"))
    label = f"observation {oid}"
    for ref in row.get("blind_findings") or []:
        resolved = resolve_blind_reference(inputs.baseline_report, ref, label=label)
        _same_text(ref.get("text"), resolved.get("text"), label=label, what="a blind finding")
    for ref in row.get("audit_findings") or []:
        resolved = resolve_audit_reference(inputs.audits, ref, label=label)
        _same_text(ref.get("text"), resolved.get("text"), label=label, what="an audit finding")
    for ref in row.get("current_proposal_evidence") or []:
        verify_evidence(inputs.candidate, ref, label=label)
    historical = (row.get("historical_proposal_evidence") or {}).get("quotes") or []
    target = inputs.historical_candidate or inputs.candidate
    for ref in historical:
        verify_evidence(target, ref, label=label)
    for ref in row.get("evidence_basis") or []:
        pointer = str(ref.get("pointer") or "")
        resolved = resolve_register_pointer(inputs.register, pointer, label=label)
        if json.dumps(resolved.get("value"), sort_keys=True) != json.dumps(
            ref.get("value"), sort_keys=True
        ):
            raise OperatorReviewError(
                f"{label}: register pointer {pointer!r} now holds "
                f"{json.dumps(resolved.get('value'))[:60]}, the comparison recorded "
                f"{json.dumps(ref.get('value'))[:60]}."
            )
    return ReferenceCheck(
        blind=len(row.get("blind_findings") or []),
        audit=len(row.get("audit_findings") or []),
        current_quotes=len(row.get("current_proposal_evidence") or []),
        historical_quotes=len(historical),
        register_entries=len(row.get("evidence_basis") or []),
    )


# --------------------------------------------------------------------------- #
# Counts: recomputed from the rows, cross-checked against the comparison
# --------------------------------------------------------------------------- #


def _lane_label(detected_by: Sequence[str]) -> str:
    """Which of the four exclusive lane buckets a row falls in."""
    lanes = set(detected_by or ())
    if lanes == {LANE_BLIND, LANE_AUDIT}:
        return LANE_BOTH
    if lanes == {LANE_BLIND}:
        return LANE_BLIND_ONLY
    if lanes == {LANE_AUDIT}:
        return LANE_AUDIT_ONLY
    return LANE_NEITHER


#: The lane buckets of this report.  They are exclusive: a row detected by
#: both lanes is counted once, under "both lanes".  The comparison's own
#: ``summary.detection.by_lane`` counts membership instead, so its figure for a
#: lane includes the rows this report lists under "both lanes".
LANE_BLIND_ONLY = "blind lane only"
LANE_AUDIT_ONLY = "integrity audit only"
LANE_BOTH = "both lanes"
LANE_NEITHER = "neither lane"
LANE_LABELS: tuple[str, ...] = (LANE_BLIND_ONLY, LANE_AUDIT_ONLY, LANE_BOTH, LANE_NEITHER)


def recount(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Every count this report states, derived from the rows alone."""
    criticisms = [r for r in rows if r.get("kind") in CRITICISM_KINDS]
    strengths = [r for r in rows if r.get("kind") == OBSERVATION_KIND_STRENGTH]

    def by_disposition(subset: Sequence[Mapping[str, Any]]) -> dict[str, int]:
        return {d: sum(1 for r in subset if r.get("disposition") == d) for d in DISPOSITIONS}

    def by_lane(subset: Sequence[Mapping[str, Any]]) -> dict[str, int]:
        labels = [_lane_label(r.get("detected_by") or ()) for r in subset]
        return {label: labels.count(label) for label in LANE_LABELS}

    return {
        "observations": len(rows),
        "kinds": {
            OBSERVATION_KIND_SHORTCOMING: sum(
                1 for r in rows if r.get("kind") == OBSERVATION_KIND_SHORTCOMING
            ),
            OBSERVATION_KIND_MINOR: sum(
                1 for r in rows if r.get("kind") == OBSERVATION_KIND_MINOR
            ),
            OBSERVATION_KIND_STRENGTH: len(strengths),
        },
        "criticisms": {
            "total": len(criticisms),
            "by_disposition": by_disposition(criticisms),
            "by_disposition_and_kind": {
                kind: by_disposition([r for r in criticisms if r.get("kind") == kind])
                for kind in CRITICISM_KINDS
            },
            "by_lane": by_lane(criticisms),
        },
        "strengths": {
            "total": len(strengths),
            "by_disposition": by_disposition(strengths),
            "by_lane": by_lane(strengths),
            "contested": sum(1 for r in strengths if r.get("contests_historical_strength")),
        },
        "revisions_proposed": sum(1 for r in rows if r.get("proposed_revision")),
    }


def cross_check_counts(counts: Mapping[str, Any], summary: Mapping[str, Any]) -> None:
    """Refuse when the recomputed counts and the comparison's summary disagree."""
    if counts["observations"] != summary.get("observations"):
        raise OperatorReviewError(
            f"the rows hold {counts['observations']} observations, the comparison's summary "
            f"says {summary.get('observations')}."
        )
    declared_kinds = summary.get("by_kind") or {}
    for kind, number in counts["kinds"].items():
        if declared_kinds.get(kind, 0) != number:
            raise OperatorReviewError(
                f"the rows hold {number} observation(s) of kind {kind!r}, the comparison's "
                f"summary says {declared_kinds.get(kind, 0)}."
            )
    declared_disp = summary.get("by_disposition") or {}
    for disposition in DISPOSITIONS:
        total = (
            counts["criticisms"]["by_disposition"][disposition]
            + counts["strengths"]["by_disposition"][disposition]
        )
        if declared_disp.get(disposition, 0) != total:
            raise OperatorReviewError(
                f"the rows hold {total} row(s) disposed {disposition!r}, the comparison's "
                f"summary says {declared_disp.get(disposition, 0)}."
            )
    declared_contested = summary.get("strengths_contested_by_blind_findings")
    if declared_contested is not None and declared_contested != counts["strengths"]["contested"]:
        raise OperatorReviewError(
            f"the rows hold {counts['strengths']['contested']} contested strength(s), the "
            f"comparison's summary says {declared_contested}."
        )


# --------------------------------------------------------------------------- #
# The review: rows, counts, decisions
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ReviewRow:
    """One observation: the comparison's measured half and the notes' declared half."""

    observation_id: str
    comparison: Mapping[str, Any]
    note: Mapping[str, Any]
    references: ReferenceCheck

    @property
    def is_criticism(self) -> bool:
        return self.comparison.get("kind") in CRITICISM_KINDS

    @property
    def decision(self) -> str | None:
        value = self.note.get("operator_decision")
        return str(value).strip() if isinstance(value, str) and value.strip() else None


@dataclass(frozen=True)
class Review:
    """The whole report, ready to render."""

    inputs: ResolvedInputs
    notes: ReviewNotes
    rows: tuple[ReviewRow, ...]
    counts: Mapping[str, Any]
    generated_at: str
    #: The semantic adjudication record, when the notes name one.
    adjudication: InputRecord | None = None

    @property
    def decisions(self) -> tuple[ReviewRow, ...]:
        return tuple(r for r in self.rows if r.decision is not None)


def build_review(
    inputs: ResolvedInputs,
    notes: ReviewNotes,
    *,
    clock: Callable[[], str] | None = None,
) -> Review:
    """Bind the notes to the comparison, resolve every reference, recount.

    Raises :class:`OperatorReviewError` on the first input that cannot carry
    the report.  Nothing is written here.
    """
    if notes.comparison_sha256 != inputs.comparison_sha256:
        raise OperatorReviewError(
            f"the review notes are bound to comparison {notes.comparison_sha256[:12]}, "
            f"this one is {inputs.comparison_sha256[:12]}."
        )
    rows = list(inputs.comparison.get("rows") or [])
    row_ids = [str(r.get("observation_id")) for r in rows]
    esr_ids = [str(o.get("id")) for o in inputs.esr.get("observations") or []]
    if row_ids != esr_ids:
        missing = [oid for oid in esr_ids if oid not in row_ids]
        extra = [oid for oid in row_ids if oid not in esr_ids]
        raise OperatorReviewError(
            "the comparison's rows are not the ESR record's observations "
            f"(missing: {', '.join(missing) or 'none'}; unknown: {', '.join(extra) or 'none'})."
        )
    missing_notes = [oid for oid in row_ids if oid not in notes.rows]
    if missing_notes:
        raise OperatorReviewError(
            f"{len(missing_notes)} observation(s) have no review note: "
            f"{', '.join(missing_notes)}."
        )
    unknown_notes = sorted(set(notes.rows) - set(row_ids))
    if unknown_notes:
        raise OperatorReviewError(
            f"the review notes name observation(s) the comparison does not: "
            f"{', '.join(unknown_notes)}."
        )

    built: list[ReviewRow] = []
    for row in rows:
        oid = str(row.get("observation_id"))
        note = notes.rows[oid]
        references = check_references(row, inputs)
        if note.get("recommended_disposition") != row.get("disposition") and not (
            isinstance(note.get("operator_decision"), str) and note["operator_decision"].strip()
        ):
            raise OperatorReviewError(
                f"review note {oid}: it recommends {note.get('recommended_disposition')!r} "
                f"where the comparison holds {row.get('disposition')!r}, and names no "
                "'operator_decision'. A recommended change is a question for the operator."
            )
        built.append(
            ReviewRow(observation_id=oid, comparison=row, note=note, references=references)
        )

    counts = recount(rows)
    cross_check_counts(counts, inputs.comparison.get("summary") or {})
    return Review(
        inputs=inputs,
        notes=notes,
        rows=tuple(built),
        counts=counts,
        generated_at=(clock or _utc_now)(),
        adjudication=_adjudication_record(inputs, notes),
    )


def _adjudication_record(inputs: ResolvedInputs, notes: ReviewNotes) -> InputRecord | None:
    """Hash the adjudication record the notes name, or refuse when it is gone."""
    declared = notes.adjudication_record
    if not declared:
        return None
    path = _under(inputs.repo_root, declared)
    if not path.is_file():
        raise OperatorReviewError(
            f"the review notes name adjudication record {declared!r}, which is not a file. "
            "A report may not cite reasoning it cannot hash."
        )
    return InputRecord(
        role="semantic adjudications",
        path=_portable(path, inputs.repo_root),
        sha256=file_sha256(path),
        note="the reasoning behind every row this review reports as adjudicated",
    )


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


_WS = re.compile(r"\s+")


def _cell(value: Any) -> str:
    """One table cell: whitespace collapsed, pipes escaped, never empty."""
    if value is None:
        return "—"
    text = _WS.sub(" ", str(value)).strip().replace("|", "\\|")
    return text or "—"


def _quote(text: str) -> str:
    """A blockquote line.  Quotes never go in table cells: candidate rows carry pipes."""
    return "> " + _WS.sub(" ", str(text)).strip()


def _cluster(review: Review, row: ReviewRow) -> str:
    """The ESR's own severity cluster for the row, or none.

    The ESR closes each group of related points with one severity sentence.
    An observation carries its cluster's severity; no severity is invented per
    row, and a cluster holding several rows says so here.
    """
    cluster_id = row.comparison.get("cluster_id")
    if not cluster_id:
        return "—"
    cluster = (review.inputs.esr.get("clusters") or {}).get(str(cluster_id)) or {}
    members = sum(1 for r in review.rows if r.comparison.get("cluster_id") == cluster_id)
    severity = str(cluster.get("severity") or row.comparison.get("kind") or "")
    shared = f", {members} observations" if members > 1 else ""
    return f"{cluster_id} ({severity}{shared})"


def _lane_of(row: ReviewRow) -> str:
    return _lane_label(row.comparison.get("detected_by") or ())


def _subject(review: Review) -> str:
    """What the review is of, taken from the comparison's own bindings.

    The intake id when the baseline carries one, else the candidate document,
    else nothing.  No instrument or call name is written into this module: the
    harness is instrument-agnostic and the subject is data (test_profile.py's
    agnosticism lint).
    """
    baseline = review.inputs.comparison.get("baseline") or {}
    candidate = review.inputs.comparison.get("candidate") or {}
    for value in (baseline.get("intake_id"), candidate.get("document")):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def render_review(review: Review) -> str:
    """The full Markdown review report."""
    data = review.inputs.comparison
    baseline = data.get("baseline") or {}
    counts = review.counts
    out: list[str] = []
    add = out.append

    subject = _subject(review)
    add(
        f"# Operator review — the {counts['observations']} ESR observations"
        + (f" of {subject}" if subject else "")
    )
    add("")
    add(f"Generated: {review.generated_at}  ")
    add(f"Review state: **{review.notes.review_state}**  ")
    add(f"Drafted by: {review.notes.declared_by}  ")
    if review.adjudication is not None:
        add(f"Adjudications: `{_cell(review.adjudication.path)}`  ")
    add("Ticket: R02 of `plans/pe08_review_and_pe09_handoff_tickets.md`")
    add("")
    add(_PROVISIONAL)
    add("")
    if review.notes.supersession_note:
        add(review.notes.supersession_note)
        add("")
    add(
        "This report reads the committed PE-08 comparison. It changes no disposition, "
        "writes no revision and calls no assessor. Every reference below was resolved "
        "again, against the artifact the comparison names, before this file was written."
    )
    add("")
    add(_ADVISORY)
    add("")

    add("## 1. Inputs")
    add("")
    add("| Role | Path | sha256 (or content hash) | Note |")
    add("|---|---|---|---|")
    for item in review.inputs.inventory:
        digest = item.sha256 or ""
        short = digest if digest.startswith("sha256:") else f"`{digest[:16]}…`"
        add(f"| {_cell(item.role)} | `{_cell(item.path)}` | {_cell(short)} | {_cell(item.note)} |")
    add(
        f"| review notes | `{_cell(_portable(review.notes.path, review.inputs.repo_root))}` "
        f"| `{_cell(review.notes.sha256[:16])}…` | the declared half of this report |"
    )
    if review.adjudication is not None:
        a = review.adjudication
        add(
            f"| {_cell(a.role)} | `{_cell(a.path)}` | `{_cell((a.sha256 or '')[:16])}…` "
            f"| {_cell(a.note)} |"
        )
    add("")
    add(
        "Each hash above was recomputed from the file on disk. A mismatch refuses the "
        f"report. The assessor pin is `{_cell(baseline.get('assessor_pin'))}`; no assessor "
        "ran for this review."
    )
    add("")

    add("## 2. Counts")
    add("")
    add(_count_warning(counts))
    add("")
    k = counts["kinds"]
    add(
        f"The ESR records **{counts['observations']} observations**: "
        f"**{counts['criticisms']['total']} criticisms** "
        f"({k[OBSERVATION_KIND_SHORTCOMING]} shortcomings, {k[OBSERVATION_KIND_MINOR]} minor "
        f"shortcomings) and **{counts['strengths']['total']} strengths**."
    )
    add("")
    add("### Criticisms")
    add("")
    add("| Disposition | Shortcomings | Minor | All criticisms | What it means here |")
    add("|---|---|---|---|---|")
    meanings = {
        DISPOSITION_INDEPENDENTLY_DETECTED: "a blind or audit finding names the same point",
        DISPOSITION_PARTIALLY_OBSERVABLE: (
            "part of the point was found, or the copy preserves part of the evidence"
        ),
        DISPOSITION_NOT_ASSESSABLE: (
            "sanitisation removed the evidence; never counted as a failure"
        ),
        DISPOSITION_NOT_DETECTED: "the evidence is preserved and no finding names it",
        DISPOSITION_ADDRESSED: "the assessed revision no longer exhibits the point",
    }
    per_kind = counts["criticisms"]["by_disposition_and_kind"]
    for disposition in DISPOSITIONS:
        add(
            f"| `{disposition}` "
            f"| {per_kind[OBSERVATION_KIND_SHORTCOMING][disposition]} "
            f"| {per_kind[OBSERVATION_KIND_MINOR][disposition]} "
            f"| {counts['criticisms']['by_disposition'][disposition]} "
            f"| {_cell(meanings[disposition])} |"
        )
    add("")
    add("### Strengths")
    add("")
    add("| Disposition | Count |")
    add("|---|---|")
    for disposition in DISPOSITIONS:
        number = counts["strengths"]["by_disposition"][disposition]
        if number:
            add(f"| `{disposition}` | {number} |")
    add("")
    add(
        f"**{counts['strengths']['contested']}** of the {counts['strengths']['total']} "
        "strengths carry a blind finding that contests the praised point."
    )
    add("")
    add("### Lane attribution")
    add("")
    add(
        "These buckets are exclusive: a row both lanes found is counted once, under "
        "`both lanes`. The comparison's own `summary.detection.by_lane` counts "
        "membership instead, so its integrity-audit figure includes that row."
    )
    add("")
    add("| Lane | Criticisms | Strengths |")
    add("|---|---|---|")
    for lane in LANE_LABELS:
        add(
            f"| {_cell(lane)} | {counts['criticisms']['by_lane'][lane]} "
            f"| {counts['strengths']['by_lane'][lane]} |"
        )
    add("")
    add(_SCORE_WARNING)
    add("")

    add("## 3. Decisions required")
    add("")
    decisions = review.decisions
    if not decisions:
        add("None: every row is agreed and retained as it stands.")
    else:
        add(
            f"{len(decisions)} of {len(review.rows)} rows need an operator decision. The "
            "full question is repeated in each row below, and alone in the companion "
            "decisions file."
        )
        add("")
        add("| # | Observation | Agreement | Recommendation | Decision |")
        add("|---|---|---|---|---|")
        for number, row in enumerate(decisions, start=1):
            add(
                f"| {number} | `{row.observation_id}` "
                f"| {_cell(row.note.get('semantic_agreement'))} "
                f"| {_cell(row.note.get('recommendation'))} "
                f"| {_cell(row.decision)} |"
            )
    add("")

    add("## 4. The rows at a glance")
    add("")
    add(
        "`Refs` is how many references the row rests on; each one was resolved against "
        "the artifact it names, or this report would not have been written. The ESR "
        "closes each group of related points with one severity sentence, so rows in one "
        "cluster share a severity and none is invented per row."
    )
    add("")
    add(
        "| Observation | Criterion | Aspect | Kind | ESR cluster | Disposition | Lane "
        "| Refs | Agreement | Decision? |"
    )
    add("|---|---|---|---|---|---|---|---|---|---|")
    for row in review.rows:
        add(
            f"| `{row.observation_id}` "
            f"| {_cell(row.comparison.get('criterion_id'))} "
            f"| {_cell(row.comparison.get('aspect_id'))} "
            f"| {_cell(row.comparison.get('kind'))} "
            f"| {_cell(_cluster(review, row))} "
            f"| {_cell(row.comparison.get('disposition'))} "
            f"| {_cell(_lane_of(row))} "
            f"| {row.references.total} "
            f"| {_cell(row.note.get('semantic_agreement'))} "
            f"| {'yes' if row.decision else 'no'} |"
        )
    add("")

    add("## 5. The two groups the ticket asks to highlight")
    add("")
    misses = [
        r for r in review.rows if r.comparison.get("disposition") == DISPOSITION_NOT_DETECTED
    ]
    add(f"### The alleged misses ({len(misses)})")
    add("")
    add(
        "A miss is counted against the lane only where the copy preserves the evidence. "
        "The preservation of that evidence is a declaration, not a measurement, which is "
        "why each row names the status it rests on."
    )
    add("")
    add("| Observation | ESR complains of | Preservation status | Agreement | Decision |")
    add("|---|---|---|---|---|")
    for row in misses:
        add(
            f"| `{row.observation_id}` | {_cell(row.note.get('esr_complaint'))} "
            f"| {_cell(row.comparison.get('evidence_preserved_status'))} "
            f"| {_cell(row.note.get('semantic_agreement'))} | {_cell(row.decision)} |"
        )
    add("")
    contested = [r for r in review.rows if r.comparison.get("contests_historical_strength")]
    add(f"### The contested strengths ({len(contested)})")
    add("")
    add(
        "The evaluators praised the point and the blind lane faulted it. Either the "
        "blind lane is right and the evaluators were generous, or the evidence that "
        "earned the praise did not survive sanitisation. The register says which is "
        "possible; only the original says which is true."
    )
    add("")
    add("| Observation | Disposition | Agreement | Decision |")
    add("|---|---|---|---|")
    for row in contested:
        add(
            f"| `{row.observation_id}` | {_cell(row.comparison.get('disposition'))} "
            f"| {_cell(row.note.get('semantic_agreement'))} | {_cell(row.decision)} |"
        )
    add("")

    add("## 6. The observations")
    add("")
    for row in review.rows:
        out.extend(_render_row(review, row))
    add("## 7. What this report does not settle")
    add("")
    add(
        "- Whether a resolved finding is about the ESR's proposition is a judgment, "
        "recorded above as `semantic_agreement` and adjudicated in R03."
    )
    add(
        "- Whether the copy preserves the evidence an ESR observation rested on is an "
        "operator declaration, prepared in R04. Every alleged miss and every partially "
        "observable row depends on it."
    )
    add(
        "- Whether a praised point survives sanitisation can be settled only against "
        "the submitted original, inside the private network (PE-09)."
    )
    add(
        "- No disposition, revision, count or score in the comparison artifact was "
        "changed by this report. Successor artifacts are R05's."
    )
    add(
        "- Relationship to earlier versions: an earlier review of this comparison, if "
        "one exists, stays in this directory under a lower sequence number. Nothing "
        "here supersedes an artifact in place, and a review of a successor comparison "
        "is a new file, not an edit of this one."
    )
    add("")
    return "\n".join(out) + "\n"


def _render_row(review: Review, row: ReviewRow) -> list[str]:
    """One observation, in full."""
    c = row.comparison
    note = row.note
    out: list[str] = []
    add = out.append
    kind = c.get("kind")
    add(f"### {row.observation_id} — {_cell(c.get('criterion_id'))} / {_cell(c.get('aspect_id'))}")
    add("")
    add(
        f"**Kind:** {_cell(kind)} · **ESR severity cluster:** {_cell(_cluster(review, row))} "
        f"· **Proposal location:** "
        f"{_cell(', '.join(str(x) for x in c.get('proposal_location') or []) or None)}"
    )
    add("")
    add("**ESR text (verbatim):**")
    add("")
    add(_quote(c.get("historical_finding") or ""))
    if c.get("severity_wording"):
        add(">")
        add(_quote(c["severity_wording"]))
    add("")
    add(
        f"**Disposition:** `{_cell(c.get('disposition'))}` "
        f"(declared {_cell(c.get('disposition_status'))}) · **Lane:** {_cell(_lane_of(row))}"
    )
    add("")
    add("**Why the disposition says so (from the dispositions):**")
    add("")
    add(_quote(c.get("explanation") or ""))
    add("")

    blind = c.get("blind_findings") or []
    audit = c.get("audit_findings") or []
    if blind or audit:
        add("**Findings, as resolved:**")
        add("")
        for ref in blind:
            where = ref.get("expectation_key") or (
                f"{ref.get('criterion_id')} sample {ref.get('sample_index')}"
                f" #{ref.get('index')}"
            )
            add(f"- blind lane · {_cell(ref.get('kind'))} · {_cell(where)}")
            add(f"  {_quote(ref.get('text') or '')}")
        for ref in audit:
            add(
                f"- integrity audit · check `{_cell(ref.get('check'))}` #{_cell(ref.get('index'))} "
                f"· subject {_cell(ref.get('subject'))} "
                f"· `{_cell(Path(str(ref.get('report') or '')).name)}`"
            )
            add(f"  {_quote(ref.get('text') or '')}")
        add("")
    else:
        add("**Findings, as resolved:** none. No blind sample and no audit check names this point.")
        add("")

    current = c.get("current_proposal_evidence") or []
    if current:
        add("**Candidate passages (quote verified in the named sub-section):**")
        add("")
        for ref in current:
            add(f"- `{_cell(ref.get('section_id'))}` / `{_cell(ref.get('sub_section_id'))}`")
            add(f"  {_quote(ref.get('quote') or '')}")
        add("")
    historical = (c.get("historical_proposal_evidence") or {}).get("quotes") or []
    if historical:
        add(
            "**The same passages in the earlier sanitised copy:** "
            f"{len(historical)} quote(s), verified."
        )
        add("")

    register = c.get("evidence_basis") or []
    if register:
        add("**Fidelity register entries the row rests on:**")
        add("")
        for ref in register:
            add(
                f"- `{_cell(ref.get('pointer'))}` = "
                f"{_cell(json.dumps(ref.get('value'), ensure_ascii=False))}"
            )
        add("")
    if c.get("evidence_preserved_status"):
        add(
            f"**Evidence preservation:** declared {_cell(c.get('evidence_preserved_status'))}. "
            "Preservation of the evidence the evaluators read is not measurable from this copy."
        )
        add("")

    add("**Reference check (measured):**")
    add("")
    refs = row.references
    add(
        f"- resolved: {refs.blind} blind finding(s), {refs.audit} audit finding(s), "
        f"{refs.current_quotes} candidate quote(s), {refs.historical_quotes} historical "
        f"quote(s), {refs.register_entries} register entr(ies) — "
        f"{refs.total} of {refs.total} against the artifact each names."
    )
    add("")
    add("**Semantic agreement (declared, provisional):**")
    add("")
    add(
        f"- **Does the evidence support the ESR's proposition?** "
        f"`{_cell(note.get('semantic_agreement'))}` (declared {_cell(note.get('declared_status'))})"
    )
    add(f"- **Basis:** {_cell(note.get('agreement_basis'))}")
    if kind in CRITICISM_KINDS:
        add(f"- **The ESR complains of:** `{_cell(note.get('esr_complaint'))}`")
    if note.get("uncertainty"):
        add(f"- **Uncertainty:** {_cell(note.get('uncertainty'))}")
    add(
        f"- **Recommendation:** `{_cell(note.get('recommendation'))}`, disposition "
        f"`{_cell(note.get('recommended_disposition'))}`"
        + (
            " (unchanged)"
            if note.get("recommended_disposition") == c.get("disposition")
            else " (**a change from the comparison**)"
        )
    )
    if row.decision:
        add(f"- **Operator decision required:** {_cell(row.decision)}")
    else:
        add("- **Operator decision required:** none.")
    add("")
    revision = c.get("proposed_revision") or {}
    if revision:
        add(f"**Proposed revision (drafted, declared {_cell(revision.get('declared_status'))}):**")
        add("")
        add(_quote(revision.get("text") or ""))
        add("")
    add("---")
    add("")
    return out


def render_decisions(review: Review, *, review_name: str | None = None) -> str:
    """The companion file: only what the operator has to decide.

    *review_name* is the file name of the full report written in the same run,
    so the two name each other.  The writer always passes it.
    """
    out: list[str] = []
    add = out.append
    subject = _subject(review)
    add("# Operator decisions" + (f" — {subject}" if subject else ""))
    add("")
    add(f"Generated: {review.generated_at}  ")
    add(f"Review state: **{review.notes.review_state}**  ")
    add("Ticket: R02 of `plans/pe08_review_and_pe09_handoff_tickets.md`  ")
    if review.adjudication is not None:
        add(f"Adjudications: `{_cell(review.adjudication.path)}`  ")
    add(f"Full report: `{review_name or _REVIEW_PREFIX}` (same directory)  ")
    add(
        "Comparison: "
        f"`{_portable(review.inputs.comparison_path, review.inputs.repo_root)}`"
    )
    add("")
    add(_PROVISIONAL)
    add("")
    add(_ADVISORY)
    add("")
    decisions = review.decisions
    if not decisions:
        add("No decision is outstanding.")
        add("")
        return "\n".join(out) + "\n"
    add(
        f"{len(decisions)} decisions, in the ESR's own order. Each names the row, what the "
        "reviewer could and could not establish, and the question."
    )
    add("")
    for number, row in enumerate(decisions, start=1):
        c = row.comparison
        add(
            f"## {number}. {row.observation_id} — {_cell(c.get('kind'))}, "
            f"`{_cell(c.get('disposition'))}`"
        )
        add("")
        add(_quote(c.get("historical_finding") or ""))
        add("")
        add(
            f"- **Agreement:** `{_cell(row.note.get('semantic_agreement'))}` — "
            f"{_cell(row.note.get('agreement_basis'))}"
        )
        if row.note.get("uncertainty"):
            add(f"- **Uncertainty:** {_cell(row.note.get('uncertainty'))}")
        add(f"- **Recommendation:** `{_cell(row.note.get('recommendation'))}`")
        add(f"- **Decision:** {_cell(row.decision)}")
        add("")
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- #
# Writing
# --------------------------------------------------------------------------- #


def next_markdown_path(out_dir: Path, digest: str, *, prefix: str) -> Path:
    """The next free ``<prefix>_<hash12>_<NNNN>.md`` under *out_dir*.

    The shared sequencer of every harness writer, with the Markdown suffix;
    *digest* is ``sha256:<hex>`` as that sequencer expects.  Nothing is ever
    overwritten: an earlier review of the same comparison stays as the
    operator read it.
    """
    return next_report_path(out_dir, digest, prefix=prefix, suffix=_MARKDOWN_SUFFIX)


def write_review(review: Review, out_dir: Path | str) -> tuple[Path, Path]:
    """Write the review and the decisions list; never overwrite either.

    The two share a sequence number, as the comparison and its revisions do.
    """
    out = Path(out_dir)
    short = review.inputs.comparison_sha256[:12]
    target = next_markdown_path(
        out, "sha256:" + review.inputs.comparison_sha256, prefix=_REVIEW_PREFIX
    )
    seq = target.stem.rsplit("_", 1)[1]
    decisions = out / f"{_DECISIONS_PREFIX}_{short}_{seq}{_MARKDOWN_SUFFIX}"
    if decisions.exists():
        raise OperatorReviewError(f"{decisions} already exists; nothing overwritten.")
    out.mkdir(parents=True, exist_ok=True)
    atomic_write_text(render_review(review), target, prefix="operator_review_")
    atomic_write_text(
        render_decisions(review, review_name=target.name), decisions, prefix="operator_decisions_"
    )
    return target, decisions


def render_summary(review: Review) -> str:
    """One screen for the terminal: the bindings and the counts."""
    counts = review.counts
    crit = counts["criticisms"]
    lines = [
        f"OPERATOR REVIEW  comparison {review.inputs.comparison_sha256[:12]}  "
        f"notes {review.notes.sha256[:12]}",
        f"state:         {review.notes.review_state}",
        f"observations:  {counts['observations']}  "
        f"criticisms {crit['total']}  strengths {counts['strengths']['total']} "
        f"({counts['strengths']['contested']} contested)",
        "criticisms by disposition:",
    ]
    for disposition in DISPOSITIONS:
        number = crit["by_disposition"][disposition]
        if number:
            lines.append(f"  - {disposition}: {number}")
    lines.append(
        "lanes (criticisms):  "
        + ", ".join(f"{lane} {crit['by_lane'][lane]}" for lane in crit["by_lane"])
    )
    lines.append(f"decisions required:  {len(review.decisions)} of {len(review.rows)} rows")
    lines.append("every reference re-resolved against the artifact it names")
    return "\n".join(lines)


__all__ = [
    "AGREEMENTS",
    "COMPLAINTS",
    "CRITICISM_KINDS",
    "LANE_AUDIT_ONLY",
    "LANE_BLIND_ONLY",
    "LANE_BOTH",
    "LANE_LABELS",
    "LANE_NEITHER",
    "RECOMMENDATIONS",
    "REVIEW_NOTES_RECORD_TYPE",
    "REVIEW_SCHEMA_VERSION",
    "REVIEW_STATES",
    "REVIEW_STATE_PENDING",
    "InputRecord",
    "OperatorReviewError",
    "ReferenceCheck",
    "ResolvedInputs",
    "Review",
    "ReviewNotes",
    "ReviewRow",
    "build_review",
    "check_references",
    "cross_check_counts",
    "load_review_notes",
    "next_markdown_path",
    "recount",
    "render_decisions",
    "render_review",
    "render_summary",
    "resolve_inputs",
    "write_review",
]
