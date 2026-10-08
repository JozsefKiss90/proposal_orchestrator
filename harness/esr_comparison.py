"""
ESR comparison over a frozen blind baseline (spec PE-08).

Three inputs, two outputs, no assessor call.

Inputs
------
* The **ESR record**: the historical Evaluation Summary Report transcribed by
  the operator, one observation per labelled point, text verbatim, severity
  taken from the ESR's own wording (spec decision 13). Strengths are recorded
  too, so a blind finding the evaluators praised can be caught.
* The **dispositions**: the operator's declared half, bound to one frozen
  baseline by the baseline report's sha256. For every observation it names a
  disposition from the closed set below, the blind findings and audit
  findings it rests on, the candidate passages it quotes, the fidelity
  register entries it relies on, and an explanation. A declaration never
  becomes a measurement: every reference is resolved against the artifact it
  names and every quote is found in the candidate text, or the comparison is
  refused and nothing is written.
* The **frozen baseline** (``load_frozen_baseline``), the materialised
  candidate it is bound to, the fidelity register, and any integrity-audit
  reports the dispositions cite.

Dispositions (the closed set, spec PE-08)
-----------------------------------------
``independently_detected``
    A blind finding, or an integrity-audit finding, names the same point.
    The row says which lane detected it.
``partially_observable``
    Part of the point was found, or the copy preserves only part of the
    evidence the ESR rested on. Needs at least one finding reference and at
    least one register entry.
``not_assessable_from_this_copy``
    The evidence the ESR rested on was removed by sanitisation. Needs a
    register entry. Never counted as a model failure and never dropped.
``not_detected_despite_sufficient_preserved_evidence``
    The copy preserves the evidence (quoted and verified) and no finding
    names the point. The only disposition that counts against the lane. The
    quote is measured; the *sufficiency* of the evidence is a declaration, and
    a ``Confirmed`` one needs the register's declared half to say so
    (:func:`check_preservation_claim`). Under dispositions schema 1.1 the row
    also names the register entry its preservation claim rests on.
``addressed``
    The revision the baseline assesses no longer exhibits the point. Needs a
    verified quote from the historical copy and one from the current copy.

A proposed revision may carry a ``revision_plan`` (ticket R05): the evidence
it rests on, the human role that owns it with the source that names it, what
has to be confirmed before it can be written, where in the proposal it goes,
and what carrying it out commits someone to. :func:`check_revision_plan`
refuses an incomplete plan, and refuses one that names a commitment and
nothing to confirm. A row that declares no plan carries no plan key.

Criterion scores are compared separately from the qualitative rows. No
deduction is attributed to any individual criticism, and the difference from
the historical total is not interpretable as model error (spec section 1).

Outputs
-------
``comparison_<sha12>_<NNNN>.json`` (the rows, the summary, the score table,
every binding) and ``revisions_<sha12>_<NNNN>.json`` (the proposed revisions
in priority order, a separate artifact per the ticket's acceptance). The
sequence number follows the audit and blind-report writers: nothing is ever
overwritten. ``<sha12>`` is the frozen baseline report's hash.

Advisory, never run-blocking.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from runner.atomic_write import atomic_write_json
from harness.blind_assessment import (
    BlindAssessmentError,
    Candidate,
    candidate_hash,
    next_report_path,
)
from harness.blind_baseline import FrozenBaseline, _portable
from harness.evidence_preflight import file_sha256
from harness.integrity_audit import IntegrityAuditError, fold_ligatures, load_audit

ESR_RECORD_TYPE = "esr_record"
DISPOSITIONS_RECORD_TYPE = "esr_dispositions"
COMPARISON_RECORD_TYPE = "esr_comparison_report"
REVISIONS_RECORD_TYPE = "esr_revision_priorities"
COMPARISON_SCHEMA_VERSION = "1.0"

OBSERVATION_KIND_SHORTCOMING = "shortcoming"
OBSERVATION_KIND_MINOR = "minor_shortcoming"
OBSERVATION_KIND_STRENGTH = "strength"
OBSERVATION_KINDS: tuple[str, ...] = (
    OBSERVATION_KIND_SHORTCOMING,
    OBSERVATION_KIND_MINOR,
    OBSERVATION_KIND_STRENGTH,
)

DISPOSITION_INDEPENDENTLY_DETECTED = "independently_detected"
DISPOSITION_PARTIALLY_OBSERVABLE = "partially_observable"
DISPOSITION_NOT_ASSESSABLE = "not_assessable_from_this_copy"
DISPOSITION_NOT_DETECTED = "not_detected_despite_sufficient_preserved_evidence"
DISPOSITION_ADDRESSED = "addressed"
DISPOSITIONS: tuple[str, ...] = (
    DISPOSITION_INDEPENDENTLY_DETECTED,
    DISPOSITION_PARTIALLY_OBSERVABLE,
    DISPOSITION_NOT_ASSESSABLE,
    DISPOSITION_NOT_DETECTED,
    DISPOSITION_ADDRESSED,
)

#: Blind-report reference kinds and the keys each needs.
BLIND_REFERENCE_KINDS: Mapping[str, tuple[str, ...]] = {
    "criterion_shortcoming": ("criterion_id", "sample_index", "index"),
    "criterion_strength": ("criterion_id", "sample_index", "index"),
    "cell": ("expectation_key",),
    "cell_member": ("expectation_key", "member_index"),
}

#: The four status categories of CLAUDE.md §12.2, for declared fields.
DECLARED_STATUSES: tuple[str, ...] = ("Confirmed", "Inferred", "Assumed", "Unresolved")

#: Dispositions record versions this module reads. 1.0 is the PE-08 record; 1.1
#: adds the R05 rule that a miss names the register entry its preservation
#: claim rests on, and is otherwise identical; 1.2 (the PE-08 operator approval
#: of 2026-10-08) resolves register pointers by identity (V02), makes every
#: miss declare its failure mode (D03), and reports a shared ESR sentence (D01).
#: An unknown version is refused rather than read under the rules of a version
#: it does not declare.
DISPOSITIONS_SCHEMA_VERSIONS: tuple[str, ...] = ("1.0", "1.1", "1.2")

#: The versions that hold a miss to naming its register basis. 1.0 does not:
#: the PE-08 record named one on a single row of six, and tightening the rule
#: under its own version would make that comparison unreplayable.
VERSIONS_REQUIRING_A_MISS_BASIS: tuple[str, ...] = ("1.1", "1.2")

#: The versions whose register pointers resolve a bare segment of a keyed list
#: by identity only (:func:`resolve_pointer`). Under 1.0 and 1.1 a bare digit
#: was read as a position first, so ``derived/sub_sections/8/characters``
#: resolved to the ninth sub-section and not to sub-section 8 (validation
#: correction V02). Those records recorded their values under that rule and
#: replay only under it, so the legacy rule stays, named and version-gated.
VERSIONS_WITH_IDENTITY_POINTERS: tuple[str, ...] = ("1.2",)

#: The versions whose summary reports the ESR sentences that two observations
#: share (operator decision D01). A separate gate from the pointer rule above:
#: both arrived with schema 1.2 and neither implies the other.
VERSIONS_REPORTING_SHARED_SENTENCES: tuple[str, ...] = ("1.2",)

#: How a comparison says it resolved its register pointers. Recorded on the
#: ``fidelity_register`` block only when the identity rule applied, so an older
#: comparison keeps the shape it was written with. :func:`pointer_rule_of` reads
#: it back for a reader that has the comparison and not the dispositions.
POINTER_RESOLUTION_IDENTITY = "identity"
POINTER_RESOLUTION_LEGACY = "legacy_positional"

#: The declared-half field that carries the per-sub-section judgment on the step
#: from the submission to this copy, and the claim scope it must declare. Both
#: names are the R04 draft's (``tools/draft_fidelity_declarations.py``); a
#: Confirmed preservation claim on a miss rests on this field and on nothing
#: else in the register (validation correction V01).
ORIGINAL_FIDELITY_FIELD = "fidelity_to_submitted_original"
ORIGINAL_FIDELITY_SCOPE = "fidelity_against_the_submitted_original"

#: Why a lane missed a point, declared per miss under schema 1.2 and reported
#: as its own breakdown (operator decision D03). None is a verdict on the
#: model: an absence from the recorded output does not establish that the
#: evidence was not read (D02), and detection is not an accuracy or
#: calibration claim.
FAILURE_MODE_ABSENT = "absent_from_recorded_output"
FAILURE_MODE_RATED_ADEQUATE = "read_and_rated_adequate"
FAILURE_MODE_MISATTRIBUTED = "read_and_misattributed"
FAILURE_MODE_UNDETERMINED = "undetermined"
MISS_FAILURE_MODES: tuple[str, ...] = (
    FAILURE_MODE_ABSENT,
    FAILURE_MODE_RATED_ADEQUATE,
    FAILURE_MODE_MISATTRIBUTED,
    FAILURE_MODE_UNDETERMINED,
)
VERSIONS_REQUIRING_A_FAILURE_MODE: tuple[str, ...] = ("1.2",)

#: What a proposed revision answers. A revision on a praised point is by
#: definition work beyond the ESR (operator decisions D07 and D08) and must
#: say so; a revision on a criticism answers it unless it declares otherwise.
REVISION_SCOPE_ESR = "esr_response"
REVISION_SCOPE_BEYOND = "beyond_esr"
REVISION_SCOPES: tuple[str, ...] = (REVISION_SCOPE_ESR, REVISION_SCOPE_BEYOND)

#: The review state a dispositions record and each of its rows may declare
#: (ticket R05 item 2 and acceptance criterion 2). A record that declares none
#: is read exactly as before; a record that declares one has that state
#: carried into the comparison, so no reading of the artifact can take an
#: agent's recommendation for an operator's decision.
REVIEW_STATE_AGENT_DRAFTED = "agent_drafted_pending_operator_review"
REVIEW_STATE_OPERATOR_REVIEWED = "operator_reviewed"
RECORD_REVIEW_STATES: tuple[str, ...] = (
    REVIEW_STATE_AGENT_DRAFTED,
    REVIEW_STATE_OPERATOR_REVIEWED,
)

#: The review state of one row.
ROW_REVIEW_STATES: tuple[str, ...] = (
    "agent_recommended_pending_operator_review",
    "operator_decision_required",
    "operator_confirmed",
)

#: What a revision plan must say (ticket R05 item 6).
REVISION_PLAN_FIELDS: tuple[str, ...] = (
    "evidence",
    "responsible_role",
    "requires_confirmation",
    "proposal_location",
    "commitment_kind",
)

#: What carrying out a revision commits a human to. The four non-editorial
#: commitments are the four things ticket R05 item 6 says must stay proposals
#: until a human confirms them: a numerical target, a study design, data or
#: site access, and a partner commitment. The fifth is the one this repository
#: cannot settle at all — a claim that needs the submitted original (PE-09).
REVISION_COMMITMENT_EDITORIAL = "editorial_change"
REVISION_COMMITMENT_KINDS: tuple[str, ...] = (
    REVISION_COMMITMENT_EDITORIAL,
    "requires_numerical_target",
    "requires_study_design",
    "requires_data_access",
    "requires_partner_commitment",
    "requires_original_check",
)

LANE_BLIND = "blind_lane"
LANE_AUDIT = "integrity_audit"

_COMPARISON_PREFIX = "comparison"
_REVISIONS_PREFIX = "revisions"

_SCORE_STATEMENT = (
    "Criterion scores are compared separately from the qualitative rows. No "
    "deduction is attributed to any individual criticism. The candidate is a "
    "sanitised derivative of the assessed document, so a difference from the "
    "historical score is not interpretable as model error: it may equally be "
    "changed wording, removed evidence or assessor variance. The blind spread "
    "is within-assessor repeatability and cannot decompose that difference."
)
_NOT_ASSESSABLE_STATEMENT = (
    "A 'not assessable from this copy' row is counted separately. It is never a "
    "model failure, never a detection, and never dropped from the row count."
)
_DETECTION_BASIS = (
    "shortcomings and minor shortcomings whose disposition is not 'addressed' "
    "and not 'not_assessable_from_this_copy'; strengths are reported but not rated"
)
_REVIEW_STATE_DRAFT = (
    "The dispositions this comparison resolves are agent-drafted and pending "
    "operator review. Every count below is a count of declarations in that "
    "state, and nothing here records an operator decision. The general note on "
    "this report describes the dispositions as the operator's; for this record "
    "that reading is wrong, and this field governs."
)
_REVIEW_STATE_REVIEWED = (
    "The dispositions this comparison resolves record an operator review. The "
    "review is of the declarations, not of the measurements: every reference "
    "was resolved against the artifact it names either way. Which rows the "
    "review confirmed is stated per row under review_status and listed here; a "
    "row not marked operator_confirmed carries an agent's declaration, and an "
    "approved review policy is an authority fact, not Confirmed evidence."
)
_NOTE = (
    "Advisory to a human, never run-blocking. Every disposition is declared by "
    "the operator; every reference it rests on was resolved against the frozen "
    "baseline, the integrity audits, the candidate text or the fidelity register "
    "before this report was written. One proposal-ESR pair is a case study, not "
    "a validation of scoring accuracy."
)


class EsrComparisonError(BlindAssessmentError):
    """A comparison input that cannot be used; nothing is written."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path, what: str) -> dict[str, Any]:
    if not path.is_file():
        raise EsrComparisonError(f"{what} not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise EsrComparisonError(f"{what} {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, Mapping):
        raise EsrComparisonError(f"{what} {path} must hold a JSON object.")
    return dict(data)


# --------------------------------------------------------------------------- #
# The ESR record
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class EsrRecord:
    path: Path
    sha256: str
    data: Mapping[str, Any]
    observations: tuple[Mapping[str, Any], ...]

    @property
    def criterion_scores(self) -> Mapping[str, Mapping[str, Any]]:
        result = self.data.get("evaluation_result") or {}
        return {str(c["criterion_id"]): c for c in result.get("criteria") or []}


def load_esr_record(path: Path | str) -> EsrRecord:
    """Load and validate the operator-authored ESR record, fail-closed."""
    p = Path(path)
    data = _read_json(p, "ESR record")
    if data.get("record_type") != ESR_RECORD_TYPE:
        raise EsrComparisonError(f"{p} is not an {ESR_RECORD_TYPE!r} record.")
    for key in ("intake_id", "source", "evaluation_result", "observations"):
        if key not in data:
            raise EsrComparisonError(f"ESR record {p} lacks {key!r}.")
    result = data["evaluation_result"]
    if not isinstance(result, Mapping) or not isinstance(result.get("criteria"), list):
        raise EsrComparisonError(f"ESR record {p}: evaluation_result.criteria must be a list.")
    for c in result["criteria"]:
        for key in ("criterion_id", "score", "threshold", "weight_pct"):
            if key not in c:
                raise EsrComparisonError(f"ESR record {p}: a criterion lacks {key!r}.")
        for key in ("score", "threshold", "weight_pct"):
            if not isinstance(c[key], (int, float)) or isinstance(c[key], bool):
                raise EsrComparisonError(
                    f"ESR record {p}: criterion {c['criterion_id']!r} has a non-numeric {key!r}."
                )
    if not isinstance(result.get("total"), (int, float)):
        raise EsrComparisonError(f"ESR record {p}: evaluation_result.total must be a number.")
    observations = data["observations"]
    if not isinstance(observations, list) or not observations:
        raise EsrComparisonError(f"ESR record {p} holds no observations.")
    seen: set[str] = set()
    for obs in observations:
        if not isinstance(obs, Mapping):
            raise EsrComparisonError(f"ESR record {p}: every observation must be an object.")
        oid = obs.get("id")
        if not isinstance(oid, str) or not oid:
            raise EsrComparisonError(f"ESR record {p}: an observation lacks an id.")
        if oid in seen:
            raise EsrComparisonError(f"ESR record {p}: observation id {oid!r} is repeated.")
        seen.add(oid)
        for key in ("criterion_id", "aspect_id", "kind", "text", "esr_location"):
            if key not in obs:
                raise EsrComparisonError(f"ESR record {p}: observation {oid} lacks {key!r}.")
        if obs["kind"] not in OBSERVATION_KINDS:
            raise EsrComparisonError(
                f"ESR record {p}: observation {oid} has kind {obs['kind']!r}; "
                f"one of {', '.join(OBSERVATION_KINDS)} is required."
            )
        if not isinstance(obs["text"], str) or not obs["text"].strip():
            raise EsrComparisonError(f"ESR record {p}: observation {oid} has empty text.")
    return EsrRecord(path=p, sha256=file_sha256(p), data=data, observations=tuple(observations))


# --------------------------------------------------------------------------- #
# The dispositions
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Dispositions:
    path: Path
    sha256: str
    data: Mapping[str, Any]
    rows: Mapping[str, Mapping[str, Any]]

    @property
    def baseline_report_sha256(self) -> str:
        return str(self.data.get("baseline_report_sha256") or "")

    @property
    def schema_version(self) -> str:
        return str(self.data.get("schema_version") or "")

    @property
    def review_state(self) -> str | None:
        """The state the record declares, or ``None`` when it declares none."""
        state = self.data.get("review_state")
        return str(state) if state is not None else None


def load_dispositions(path: Path | str) -> Dispositions:
    """Load the operator's dispositions, fail-closed on shape."""
    p = Path(path)
    data = _read_json(p, "dispositions")
    if data.get("record_type") != DISPOSITIONS_RECORD_TYPE:
        raise EsrComparisonError(f"{p} is not an {DISPOSITIONS_RECORD_TYPE!r} record.")
    for key in ("baseline_report_sha256", "esr_record_sha256", "declared_by", "rows"):
        if key not in data:
            raise EsrComparisonError(f"dispositions {p} lack {key!r}.")
    state = data.get("review_state")
    if state is not None and state not in RECORD_REVIEW_STATES:
        raise EsrComparisonError(
            f"dispositions {p} declare review_state {state!r}; one of "
            f"{', '.join(RECORD_REVIEW_STATES)} is required when the field is present."
        )
    version = data.get("schema_version")
    if version not in DISPOSITIONS_SCHEMA_VERSIONS:
        raise EsrComparisonError(
            f"dispositions {p} declare schema_version {version!r}; this module reads "
            f"{', '.join(DISPOSITIONS_SCHEMA_VERSIONS)}."
        )
    rows = data["rows"]
    if not isinstance(rows, list) or not rows:
        raise EsrComparisonError(f"dispositions {p} hold no rows.")
    by_id: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        if not isinstance(row, Mapping) or not isinstance(row.get("observation_id"), str):
            raise EsrComparisonError(f"dispositions {p}: every row needs an observation_id.")
        oid = row["observation_id"]
        if oid in by_id:
            raise EsrComparisonError(f"dispositions {p}: observation {oid} is disposed twice.")
        by_id[oid] = row
    return Dispositions(path=p, sha256=file_sha256(p), data=data, rows=by_id)


@dataclass(frozen=True)
class Register:
    path: Path
    sha256: str
    data: Mapping[str, Any]


def load_register(path: Path | str) -> Register:
    """Load the fidelity register, fail-closed on shape."""
    p = Path(path)
    data = _read_json(p, "fidelity register")
    if data.get("record_type") != "fidelity_register":
        raise EsrComparisonError(f"{p} is not a 'fidelity_register' record.")
    return Register(path=p, sha256=file_sha256(p), data=data)


# --------------------------------------------------------------------------- #
# Resolution: every declared reference against the artifact it names
# --------------------------------------------------------------------------- #


_RE_WS = re.compile(r"\s+")
_QUOTE_MAP = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"', " ": " "})


def normalise_text(text: str) -> str:
    """The comparison form of candidate text: ligatures spelled out, quotes
    straightened, whitespace collapsed. Matching only; nothing quotes it."""
    return _RE_WS.sub(" ", fold_ligatures(text).translate(_QUOTE_MAP)).strip()


def _sub_section_content(candidate: Candidate, section_id: str, sub_section_id: str) -> str:
    section = candidate.contents.get(section_id)
    if section is None:
        raise EsrComparisonError(
            f"section {section_id!r} is not present in the candidate at {candidate.root}."
        )
    for sub in section.get("sub_sections") or []:
        if str(sub.get("sub_section_id")) == str(sub_section_id):
            content = sub.get("content")
            if not isinstance(content, str):
                raise EsrComparisonError(
                    f"sub-section {sub_section_id!r} of {section_id!r} carries no text content."
                )
            return content
    raise EsrComparisonError(
        f"sub-section {sub_section_id!r} is not present in {section_id!r} of the candidate."
    )


def _occurs(candidate: Candidate, ref: Mapping[str, Any]) -> bool:
    """Whether the quote of *ref* occurs in that sub-section of *candidate*."""
    try:
        content = _sub_section_content(candidate, ref["section_id"], ref["sub_section_id"])
    except EsrComparisonError:
        return False
    return normalise_text(ref["quote"]) in normalise_text(content)


def verify_evidence(candidate: Candidate, ref: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    """Resolve one ``{section_id, sub_section_id, quote}`` against the candidate.

    The quote must occur in the named sub-section's text (ligatures folded,
    whitespace collapsed). The returned record carries the quote as declared
    and ``verified: True``; an absent quote refuses the comparison.
    """
    for key in ("section_id", "sub_section_id", "quote"):
        if not isinstance(ref.get(key), str) or not ref[key].strip():
            raise EsrComparisonError(f"{label}: an evidence reference lacks {key!r}.")
    content = _sub_section_content(candidate, ref["section_id"], ref["sub_section_id"])
    if normalise_text(ref["quote"]) not in normalise_text(content):
        raise EsrComparisonError(
            f"{label}: the quote {ref['quote'][:60]!r}... is not found in "
            f"{ref['section_id']}/{ref['sub_section_id']} of the candidate."
        )
    return {
        "section_id": ref["section_id"],
        "sub_section_id": ref["sub_section_id"],
        "quote": ref["quote"],
        "verified": True,
    }


def resolve_blind_reference(report: Mapping[str, Any], ref: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    """Resolve one blind-report reference and quote what it points at."""
    kind = str(ref.get("kind"))
    if kind not in BLIND_REFERENCE_KINDS:
        raise EsrComparisonError(
            f"{label}: blind reference kind {ref.get('kind')!r}; one of "
            f"{', '.join(BLIND_REFERENCE_KINDS)} is required."
        )
    for key in BLIND_REFERENCE_KINDS[kind]:
        if key not in ref:
            raise EsrComparisonError(f"{label}: blind reference of kind {kind!r} lacks {key!r}.")
    scoring = report.get("criterion_scoring") or {}
    if kind in ("criterion_shortcoming", "criterion_strength"):
        scores = [s for s in scoring.get("scores") or [] if s.get("criterion_id") == ref["criterion_id"]]
        if not scores:
            raise EsrComparisonError(
                f"{label}: the baseline scores no criterion {ref['criterion_id']!r}."
            )
        samples = scores[0].get("samples") or []
        try:
            sample = samples[int(ref["sample_index"])]
        except (IndexError, ValueError, TypeError):
            raise EsrComparisonError(
                f"{label}: criterion {ref['criterion_id']!r} has no sample "
                f"{ref['sample_index']!r} (panel of {len(samples)})."
            ) from None
        field_name = "shortcomings" if kind == "criterion_shortcoming" else "strengths"
        items = sample.get(field_name) or []
        try:
            text = items[int(ref["index"])]
        except (IndexError, ValueError, TypeError):
            raise EsrComparisonError(
                f"{label}: sample {ref['sample_index']} of {ref['criterion_id']!r} has no "
                f"{field_name[:-1]} {ref['index']!r} ({len(items)} listed)."
            ) from None
        return {
            "kind": kind,
            "criterion_id": ref["criterion_id"],
            "sample_index": int(ref["sample_index"]),
            "index": int(ref["index"]),
            "text": str(text),
            "polarity": "shortcoming" if kind == "criterion_shortcoming" else "strength",
        }
    cells = [c for c in report.get("cells") or [] if c.get("expectation_key") == ref["expectation_key"]]
    if not cells:
        raise EsrComparisonError(f"{label}: the baseline has no cell {ref['expectation_key']!r}.")
    cell = cells[0]
    if kind == "cell":
        return {
            "kind": kind,
            "expectation_key": ref["expectation_key"],
            "criterion_id": cell.get("criterion_id"),
            "covered": bool(cell.get("covered")),
            "addressal": cell.get("addressal"),
            "grounding": cell.get("grounding"),
            "score": cell.get("score"),
            "text": str(((cell.get("coverage") or {}).get("verdict") or {}).get("rationale") or ""),
            "polarity": "strength" if cell.get("covered") else "shortcoming",
        }
    members = ((cell.get("coverage") or {}).get("verdict") or {}).get("members") or []
    try:
        member = members[int(ref["member_index"])]
    except (IndexError, ValueError, TypeError):
        raise EsrComparisonError(
            f"{label}: cell {ref['expectation_key']!r} has no member "
            f"{ref['member_index']!r} ({len(members)} in the panel)."
        ) from None
    return {
        "kind": kind,
        "expectation_key": ref["expectation_key"],
        "criterion_id": cell.get("criterion_id"),
        "member_index": int(ref["member_index"]),
        "passed": member.get("passed"),
        "score": member.get("score"),
        "text": str(member.get("rationale") or ""),
        "polarity": "strength" if member.get("passed") else "shortcoming",
    }


@dataclass(frozen=True)
class LoadedAudit:
    key: str
    path: Path
    sha256: str
    data: Mapping[str, Any]


def load_audits(paths: Sequence[Path | str], *, repo_root: Path | None) -> dict[str, LoadedAudit]:
    """Load every audit report the command was given, keyed by its portable path."""
    audits: dict[str, LoadedAudit] = {}
    for raw in paths:
        p = Path(raw)
        if not p.is_absolute() and repo_root is not None:
            p = repo_root / p
        try:
            data = load_audit(p)
        except IntegrityAuditError as exc:
            raise EsrComparisonError(str(exc)) from exc
        key = _portable(p, repo_root)
        audits[key] = LoadedAudit(key=key, path=p, sha256=file_sha256(p), data=data)
    return audits


def resolve_audit_reference(
    audits: Mapping[str, LoadedAudit], ref: Mapping[str, Any], *, label: str
) -> dict[str, Any]:
    """Resolve one ``{report, check, index}`` against a loaded audit report."""
    for key in ("report", "check", "index"):
        if key not in ref:
            raise EsrComparisonError(f"{label}: an audit reference lacks {key!r}.")
    audit = audits.get(str(ref["report"]))
    if audit is None:
        raise EsrComparisonError(
            f"{label}: audit report {ref['report']!r} was not given to the command "
            f"(loaded: {', '.join(sorted(audits)) or 'none'})."
        )
    checks = [c for c in audit.data.get("checks") or [] if c.get("check_id") == ref["check"]]
    if not checks:
        raise EsrComparisonError(f"{label}: audit {audit.key} ran no check {ref['check']!r}.")
    findings = checks[0].get("findings") or []
    try:
        finding = findings[int(ref["index"])]
    except (IndexError, ValueError, TypeError):
        raise EsrComparisonError(
            f"{label}: check {ref['check']!r} of {audit.key} has no finding "
            f"{ref['index']!r} ({len(findings)} reported)."
        ) from None
    return {
        "report": audit.key,
        "report_sha256": audit.sha256,
        "candidate_hash": audit.data.get("candidate_hash"),
        "check": ref["check"],
        "index": int(ref["index"]),
        "finding_kind": finding.get("kind"),
        "subject": finding.get("subject"),
        "text": str(finding.get("detail") or ""),
    }


def _is_keyed_list(node: list) -> bool:
    """A list whose elements carry an identity (``sub_section_id`` or ``id``)."""
    return any(
        isinstance(x, Mapping) and ("sub_section_id" in x or "id" in x) for x in node
    )


def _by_identity(node: list, seg: str, pointer: str) -> Any:
    matches = [
        x for x in node
        if isinstance(x, Mapping) and str(x.get("sub_section_id", x.get("id"))) == seg
    ]
    if not matches:
        raise EsrComparisonError(f"register pointer {pointer!r}: no element {seg!r}.")
    return matches[0]


def _by_position(node: list, index: str, pointer: str) -> Any:
    if not index.isdigit() or int(index) >= len(node):
        raise EsrComparisonError(
            f"register pointer {pointer!r}: position #{index} is outside a list of {len(node)}."
        )
    return node[int(index)]


def resolve_pointer(
    data: Mapping[str, Any], pointer: str, *, legacy_positional: bool = False
) -> Any:
    """Resolve a ``/``-separated pointer into *data*.

    A segment indexes an object by key. Into a list it is typed:

    * ``#N`` is a position, on any list;
    * a bare segment on a **keyed** list (elements carrying ``sub_section_id``
      or ``id``) is an identity, and only an identity. ``8`` names the
      sub-section whose id is ``8``, never the ninth element, whatever its
      position (validation correction V02);
    * a bare digit on a plain list is a position, since there is no identity
      to name.

    ``/`` rather than ``.`` because sub-section ids carry dots.

    *legacy_positional* is the rule dispositions schema 1.0 and 1.1 were
    recorded under: a bare digit within range is read as a position first and
    as an identity only past the end. It exists so those comparisons replay
    from their documented inputs, and :func:`run_comparison` selects it from
    the record's own ``schema_version``. It is never the default.
    """
    node: Any = data
    for seg in [s for s in pointer.split("/") if s != ""]:
        if isinstance(node, Mapping):
            if seg not in node:
                raise EsrComparisonError(f"register pointer {pointer!r}: no key {seg!r}.")
            node = node[seg]
        elif isinstance(node, list):
            if seg.startswith("#"):
                node = _by_position(node, seg[1:], pointer)
            elif not _is_keyed_list(node):
                node = _by_position(node, seg, pointer)
            elif legacy_positional and seg.isdigit() and int(seg) < len(node):
                node = node[int(seg)]
            else:
                node = _by_identity(node, seg, pointer)
        else:
            raise EsrComparisonError(f"register pointer {pointer!r}: {seg!r} indexes a scalar.")
    return node


def resolve_register_pointer(
    register: Mapping[str, Any], pointer: str, *, label: str, legacy_positional: bool = False
) -> dict[str, Any]:
    try:
        value = resolve_pointer(register, pointer, legacy_positional=legacy_positional)
    except EsrComparisonError as exc:
        raise EsrComparisonError(f"{label}: {exc}") from None
    return {"pointer": pointer, "value": value}


def pointer_rule_of(comparison: Mapping[str, Any]) -> str:
    """Which pointer rule a written comparison recorded its values under.

    One reader of the field, so one polarity. A comparison written under the
    identity rule says so on its ``fidelity_register`` block; one written under
    schema 1.0 or 1.1 says nothing, and its values are legacy positional.
    """
    block = comparison.get("fidelity_register") or {}
    recorded = str(block.get("pointer_resolution") or "")
    if recorded == POINTER_RESOLUTION_IDENTITY:
        return POINTER_RESOLUTION_IDENTITY
    return POINTER_RESOLUTION_LEGACY


# --------------------------------------------------------------------------- #
# Rules: what each disposition must rest on
# --------------------------------------------------------------------------- #


def _declared(row: Mapping[str, Any], key: str, *, label: str, required: bool) -> str | None:
    """The declared status of a judgment field, one of the four §12.2 categories."""
    value = row.get(key)
    if value is None:
        if required:
            raise EsrComparisonError(f"{label}: {key!r} is required.")
        return None
    if value not in DECLARED_STATUSES:
        raise EsrComparisonError(
            f"{label}: {key!r} is {value!r}; one of {', '.join(DECLARED_STATUSES)} is required."
        )
    return str(value)


def declared_half_entry(register: Mapping[str, Any], sub_section_id: str) -> Mapping[str, Any] | None:
    """The register's declared-half row for *sub_section_id*, or ``None``.

    The declared half is the operator's per-sub-section statement; the derived
    half is the importer's measurement of the PDF. Only the declared half says
    anything about the step from the submission to this copy, which is what a
    claim of preserved evidence is about.
    """
    declared = register.get("declared")
    if not isinstance(declared, Mapping):
        return None
    for entry in declared.get("sub_sections") or []:
        if isinstance(entry, Mapping) and str(entry.get("sub_section_id")) == str(sub_section_id):
            return entry
    return None


def _presence_declared(entry: Mapping[str, Any]) -> bool:
    """Whether a declared-half entry states a presence value."""
    presence = entry.get("presence")
    if isinstance(presence, str):
        return bool(presence.strip())
    if isinstance(presence, Mapping):
        return bool(str(presence.get("value") or "").strip())
    return False


def _names_declared_entry(register_refs: Sequence[Mapping[str, Any]], sub: str) -> bool:
    """Whether a row's register pointers name the declared-half entry for *sub*."""
    for ref in register_refs:
        segs = [s for s in str(ref.get("pointer") or "").split("/") if s != ""]
        if segs[:3] == ["declared", "sub_sections", sub]:
            return True
    return False


def _evidence_names_observation(evidence: Any, observation_id: str) -> bool:
    """Whether a declaration's evidence list carries an item for this row."""
    if not isinstance(evidence, list):
        return False
    for item in evidence:
        if not isinstance(item, Mapping):
            continue
        ids = item.get("observation_ids")
        if isinstance(ids, str):
            ids = [ids]
        if not isinstance(ids, list) or observation_id not in [str(x) for x in ids]:
            continue
        if str(item.get("source") or "").strip() and str(item.get("statement") or "").strip():
            return True
    return False


def check_preservation_claim(
    register: Mapping[str, Any],
    *,
    current: Sequence[Mapping[str, Any]],
    status: str | None,
    label: str,
    observation_id: str,
    register_refs: Sequence[Mapping[str, Any]],
) -> None:
    """What a declared ``evidence_preserved_status`` is held to.

    The quote on a miss is a measurement: ``verify_evidence`` found it in the
    named sub-section of this candidate. The *sufficiency* of that evidence is
    a claim about the submission, which no artifact here measures. So the
    status stays a declaration, and only a ``Confirmed`` one is constrained
    (validation correction V01 of the PE-08 operator approval). For every
    sub-section the preserved passage is quoted from, the register's declared
    half must carry an entry that:

    * states a ``presence`` (the extraction claim, which on its own says only
      that this PDF was read and unlocks nothing);
    * carries :data:`ORIGINAL_FIDELITY_FIELD`, the per-sub-section judgment on
      the step from the submission to this copy, declared in the scope
      :data:`ORIGINAL_FIDELITY_SCOPE`, with status ``Confirmed`` and a basis;
    * supports *this* row: the field's ``evidence`` list carries an item that
      names the observation, with a source and a statement. A generic basis
      that names no row is not evidence for the proposition the row makes.

    And the row must name that entry among its ``evidence_basis`` pointers, so
    the declaration it rests on is the one the comparison resolved and
    recorded. An ``Inferred``, ``Assumed`` or ``Unresolved`` status says the
    claim rests on reasoning or on nothing, and stands as declared.

    The rule is not version-gated: no committed 1.0 or 1.1 row declares
    ``Confirmed``, which a test pins, so their replay does not exercise it.
    """
    if status != "Confirmed":
        return
    for ref in current:
        sub = str(ref.get("sub_section_id"))
        entry = declared_half_entry(register, sub)
        if entry is None:
            raise EsrComparisonError(
                f"{label}: 'evidence_preserved_status' is 'Confirmed', but the register's "
                f"declared half carries no entry for sub-section {sub}. Confirmed "
                "preservation is a declaration about the submission; the derived half "
                "measures this PDF's extraction and cannot carry it."
            )
        if not _presence_declared(entry):
            raise EsrComparisonError(
                f"{label}: the register's declared half declares no 'presence' for "
                f"sub-section {sub}, so 'Confirmed' preservation has no basis."
            )
        claim = entry.get(ORIGINAL_FIDELITY_FIELD)
        if not isinstance(claim, Mapping):
            raise EsrComparisonError(
                f"{label}: the declared-half entry for sub-section {sub} carries no "
                f"'{ORIGINAL_FIDELITY_FIELD}' claim. A 'presence' declaration is an "
                "extraction claim about this PDF and does not unlock 'Confirmed' "
                "preservation from the submission."
            )
        if claim.get("claim_scope") != ORIGINAL_FIDELITY_SCOPE:
            raise EsrComparisonError(
                f"{label}: sub-section {sub}'s '{ORIGINAL_FIDELITY_FIELD}' declares "
                f"claim_scope {claim.get('claim_scope')!r}; 'Confirmed' preservation needs "
                f"{ORIGINAL_FIDELITY_SCOPE!r}."
            )
        if claim.get("declared_status") != "Confirmed":
            raise EsrComparisonError(
                f"{label}: sub-section {sub}'s '{ORIGINAL_FIDELITY_FIELD}' is declared "
                f"{claim.get('declared_status')!r}, so preservation cannot be 'Confirmed'."
            )
        if not str(claim.get("basis") or "").strip():
            raise EsrComparisonError(
                f"{label}: sub-section {sub}'s '{ORIGINAL_FIDELITY_FIELD}' is 'Confirmed' "
                "with no basis."
            )
        if not _evidence_names_observation(claim.get("evidence"), observation_id):
            raise EsrComparisonError(
                f"{label}: sub-section {sub}'s '{ORIGINAL_FIDELITY_FIELD}' carries no "
                f"evidence item naming {observation_id} with a source and a statement; a "
                "basis that supports no particular proposition does not support this one."
            )
        if not _names_declared_entry(register_refs, sub):
            raise EsrComparisonError(
                f"{label}: 'Confirmed' preservation rests on the declared-half entry for "
                f"sub-section {sub}, and the row's evidence_basis does not name it "
                f"(declared/sub_sections/{sub}/...)."
            )


def check_revision_plan(revision: Mapping[str, Any], *, label: str) -> None:
    """Refuse a revision plan that does not say who owns the change (ticket R05).

    A proposed revision is a sentence anyone can write. A plan names the
    evidence it rests on, the human role that owns it, what has to be
    confirmed before it can be written, where in the proposal it goes, and
    whether carrying it out commits someone to something new. A plan that
    needs a commitment and names nothing to confirm is refused: that is the
    shape in which a proposal passes itself off as a decision.
    """
    plan = revision.get("revision_plan")
    if plan is None:
        return
    if not isinstance(plan, Mapping):
        raise EsrComparisonError(f"{label}: revision_plan must be an object.")
    for key in REVISION_PLAN_FIELDS:
        if key not in plan:
            raise EsrComparisonError(f"{label}: revision_plan lacks {key!r}.")
    for key in ("evidence", "proposal_location"):
        value = plan[key]
        if not isinstance(value, list) or not value or not all(
            isinstance(v, str) and v.strip() for v in value
        ):
            raise EsrComparisonError(
                f"{label}: revision_plan {key!r} must be a non-empty list of strings."
            )
    role = plan["responsible_role"]
    if not isinstance(role, Mapping) or not str(role.get("role") or "").strip() or not str(
        role.get("source") or ""
    ).strip():
        raise EsrComparisonError(
            f"{label}: revision_plan responsible_role needs a 'role' and the 'source' that "
            "names it; a role invented here would be a project fact (CLAUDE.md §13.3)."
        )
    kind = plan["commitment_kind"]
    if kind not in REVISION_COMMITMENT_KINDS:
        raise EsrComparisonError(
            f"{label}: revision_plan commitment_kind {kind!r}; one of "
            f"{', '.join(REVISION_COMMITMENT_KINDS)} is required."
        )
    confirm = plan["requires_confirmation"]
    if not isinstance(confirm, list) or not all(isinstance(v, str) and v.strip() for v in confirm):
        raise EsrComparisonError(
            f"{label}: revision_plan requires_confirmation must be a list of strings."
        )
    if kind != REVISION_COMMITMENT_EDITORIAL and not confirm:
        raise EsrComparisonError(
            f"{label}: revision_plan commitment_kind is {kind!r} and names nothing to "
            "confirm; a revision that commits a human states what they must confirm."
        )
    check_subtasks(plan, label=label)


def check_failure_mode(row: Mapping[str, Any], *, label: str) -> str:
    """A miss under schema 1.2 says how the lane missed the point (D03).

    The mode is a declaration drawn from the adjudication record, and the row
    names its basis. It is reported beside the detection summary and never
    folded into it: an adequacy disagreement and an unmentioned topic are both
    misses, counted in one figure, and told apart in another.
    """
    mode = row.get("failure_mode")
    if mode not in MISS_FAILURE_MODES:
        raise EsrComparisonError(
            f"{label}: a miss under this schema declares a failure_mode; {mode!r} is not one "
            f"of {', '.join(MISS_FAILURE_MODES)}."
        )
    basis = row.get("failure_mode_basis")
    if not isinstance(basis, str) or not basis.strip():
        raise EsrComparisonError(f"{label}: failure_mode {mode!r} needs a failure_mode_basis.")
    return str(mode)


def check_revision_scope(
    revision: Mapping[str, Any], *, kind: str, label: str
) -> str:
    """What a proposed revision answers (operator decisions D07 and D08).

    A revision on a strength is work beyond the ESR and must declare it, so
    no reading of the revision list can present an improvement as a response
    to a criticism. A revision on a criticism answers it unless it declares
    otherwise.
    """
    scope = revision.get("scope", REVISION_SCOPE_ESR)
    if scope not in REVISION_SCOPES:
        raise EsrComparisonError(
            f"{label}: scope {scope!r}; one of {', '.join(REVISION_SCOPES)} is required."
        )
    if kind == OBSERVATION_KIND_STRENGTH and scope != REVISION_SCOPE_BEYOND:
        raise EsrComparisonError(
            f"{label}: a revision on a strength is work beyond the ESR and must declare "
            f"scope {REVISION_SCOPE_BEYOND!r}."
        )
    return str(scope)


def check_subtasks(plan: Mapping[str, Any], *, label: str) -> None:
    """A plan may carry labelled subtasks (D08); each is scoped and confirmable."""
    subtasks = plan.get("subtasks")
    if subtasks is None:
        return
    if not isinstance(subtasks, list) or not subtasks:
        raise EsrComparisonError(f"{label}: revision_plan subtasks must be a non-empty list.")
    seen: set[str] = set()
    for i, task in enumerate(subtasks):
        if not isinstance(task, Mapping):
            raise EsrComparisonError(f"{label}: subtask {i} must be an object.")
        name = str(task.get("label") or "").strip()
        if not name:
            raise EsrComparisonError(f"{label}: subtask {i} needs a label.")
        if name in seen:
            raise EsrComparisonError(f"{label}: subtask label {name!r} is used twice.")
        seen.add(name)
        if task.get("scope") not in REVISION_SCOPES:
            raise EsrComparisonError(
                f"{label}: subtask {name!r} scope {task.get('scope')!r}; one of "
                f"{', '.join(REVISION_SCOPES)} is required."
            )
        if not str(task.get("text") or "").strip():
            raise EsrComparisonError(f"{label}: subtask {name!r} needs a text.")
        confirm = task.get("requires_confirmation")
        if not isinstance(confirm, list) or not confirm or not all(
            isinstance(v, str) and v.strip() for v in confirm
        ):
            raise EsrComparisonError(
                f"{label}: subtask {name!r} must name what has to be confirmed."
            )
        kind = task.get("commitment_kind")
        if kind is not None and kind not in REVISION_COMMITMENT_KINDS:
            raise EsrComparisonError(
                f"{label}: subtask {name!r} commitment_kind {kind!r}; one of "
                f"{', '.join(REVISION_COMMITMENT_KINDS)} is required when present."
            )


def check_row_rules(
    observation: Mapping[str, Any],
    disposition: str,
    *,
    blind: Sequence[Mapping[str, Any]],
    audit: Sequence[Mapping[str, Any]],
    current: Sequence[Mapping[str, Any]],
    historical: Sequence[Mapping[str, Any]],
    register_refs: Sequence[Mapping[str, Any]],
    register: Mapping[str, Any],
    row: Mapping[str, Any],
    label: str,
    schema_version: str,
) -> None:
    """Refuse a disposition whose declared basis does not carry it.

    *register_refs* are the register pointers this row resolved; *register* is
    the register record itself, which the preservation rule reads. Both are
    required: a default would quietly apply the laxer rule to a caller that
    forgot one.
    """
    kind = observation["kind"]
    findings = len(blind) + len(audit)
    explanation = row.get("explanation")
    if not isinstance(explanation, str) or not explanation.strip():
        raise EsrComparisonError(f"{label}: an explanation is required.")
    if disposition == DISPOSITION_INDEPENDENTLY_DETECTED:
        if findings == 0:
            raise EsrComparisonError(
                f"{label}: 'independently_detected' needs at least one blind or audit finding."
            )
        if kind != OBSERVATION_KIND_STRENGTH and not current:
            raise EsrComparisonError(
                f"{label}: 'independently_detected' needs the current passage the finding rests on."
            )
    elif disposition == DISPOSITION_PARTIALLY_OBSERVABLE:
        if findings == 0:
            raise EsrComparisonError(
                f"{label}: 'partially_observable' needs at least one blind or audit finding."
            )
        if not register_refs:
            raise EsrComparisonError(
                f"{label}: 'partially_observable' needs a fidelity-register entry naming "
                "what the copy preserves only in part."
            )
    elif disposition == DISPOSITION_NOT_ASSESSABLE:
        if not register_refs:
            raise EsrComparisonError(
                f"{label}: 'not_assessable_from_this_copy' needs a fidelity-register entry "
                "naming what sanitisation removed."
            )
    elif disposition == DISPOSITION_NOT_DETECTED:
        if findings:
            raise EsrComparisonError(
                f"{label}: 'not_detected_despite_sufficient_preserved_evidence' cannot cite a "
                "finding; a finding that names the point makes it detected or partial."
            )
        if not current:
            raise EsrComparisonError(
                f"{label}: 'not_detected_despite_sufficient_preserved_evidence' needs the "
                "preserved passage quoted from the current copy."
            )
        status = _declared(row, "evidence_preserved_status", label=label, required=True)
        if schema_version in VERSIONS_REQUIRING_A_MISS_BASIS and not register_refs:
            raise EsrComparisonError(
                f"{label}: 'not_detected_despite_sufficient_preserved_evidence' needs a "
                "fidelity-register entry naming what the copy preserves; the disposition "
                "claims preservation and the register is what records it."
            )
        check_preservation_claim(
            register, current=current, status=status, label=label,
            observation_id=str(observation["id"]), register_refs=register_refs,
        )
        if schema_version in VERSIONS_REQUIRING_A_FAILURE_MODE:
            check_failure_mode(row, label=label)
    elif disposition == DISPOSITION_ADDRESSED:
        if kind == OBSERVATION_KIND_STRENGTH:
            raise EsrComparisonError(f"{label}: a strength cannot be 'addressed'.")
        if not current or not historical:
            raise EsrComparisonError(
                f"{label}: 'addressed' needs a verified quote from the historical copy and "
                "one from the current copy."
            )
    else:  # pragma: no cover - guarded by the caller
        raise EsrComparisonError(f"{label}: unknown disposition {disposition!r}.")


# --------------------------------------------------------------------------- #
# The comparison
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ComparisonReport:
    """The comparison and the revision priorities, both bound and advisory."""

    data: dict[str, Any]
    revisions: dict[str, Any]
    baseline_report_sha256: str

    @property
    def flags(self) -> tuple[str, ...]:
        return tuple(self.data.get("flags") or ())


_KIND_RANK = {OBSERVATION_KIND_SHORTCOMING: 0, OBSERVATION_KIND_MINOR: 1, OBSERVATION_KIND_STRENGTH: 2}
_DISPOSITION_RANK = {
    DISPOSITION_NOT_DETECTED: 0,
    DISPOSITION_INDEPENDENTLY_DETECTED: 1,
    DISPOSITION_PARTIALLY_OBSERVABLE: 2,
    DISPOSITION_NOT_ASSESSABLE: 3,
    DISPOSITION_ADDRESSED: 4,
}


def _criterion_weights(baseline: Mapping[str, Any]) -> dict[str, float]:
    weights: dict[str, float] = {}
    scoring = baseline.get("criterion_scoring") or {}
    for s in scoring.get("scores") or []:
        if s.get("weight") is not None:
            weights[str(s["criterion_id"])] = float(s["weight"])
    return weights


def _round(value: float) -> float:
    """Two decimals; ``+ 0.0`` turns a ``-0.0`` difference into ``0.0``."""
    return round(value + 0.0, 2)


def run_comparison(
    *,
    frozen: FrozenBaseline,
    esr: EsrRecord,
    dispositions: Dispositions,
    candidate: Candidate,
    candidate_path: str,
    register: Register,
    historical_candidate: Candidate | None = None,
    historical_candidate_path: str | None = None,
    audits: Mapping[str, LoadedAudit] | None = None,
    repo_root: Path | str | None = None,
    clock: Callable[[], str] | None = None,
) -> ComparisonReport:
    """Resolve every disposition against its artifacts and build the report.

    Raises :class:`EsrComparisonError` on the first input that cannot carry
    its declaration. Nothing is written here.
    """
    audits = dict(audits or {})
    baseline = json.loads(frozen.copy_path.read_text(encoding="utf-8-sig"))
    bindings = frozen.record.get("bindings") or {}
    report_sha = str(frozen.record.get("report_sha256") or "")

    # Bind: the dispositions to this baseline and this ESR record, the
    # candidate to the baseline, every audit to a candidate in play.
    if dispositions.baseline_report_sha256 != report_sha:
        raise EsrComparisonError(
            f"the dispositions are bound to baseline report {dispositions.baseline_report_sha256[:12]}, "
            f"the frozen baseline is {report_sha[:12]}."
        )
    if dispositions.data.get("esr_record_sha256") != esr.sha256:
        raise EsrComparisonError(
            "the dispositions are bound to another ESR record "
            f"({str(dispositions.data.get('esr_record_sha256'))[:12]} vs {esr.sha256[:12]})."
        )
    current_hash = candidate_hash(candidate)
    if current_hash != bindings.get("candidate_hash"):
        raise EsrComparisonError(
            f"the candidate at {candidate_path} hashes to {current_hash[:19]}, the frozen "
            f"baseline is bound to {str(bindings.get('candidate_hash'))[:19]}."
        )
    flags: list[str] = []
    if not bindings.get("intake_id"):
        flags.append("the frozen baseline carries no intake id; the ESR record's intake is unbound")
    elif esr.data.get("intake_id") != bindings.get("intake_id"):
        raise EsrComparisonError(
            f"the ESR record is for intake {esr.data.get('intake_id')!r}, the baseline "
            f"for {bindings.get('intake_id')!r}."
        )
    historical_hash = candidate_hash(historical_candidate) if historical_candidate is not None else None
    if historical_hash is not None and historical_hash == current_hash:
        raise EsrComparisonError(
            "the historical candidate is the current candidate; 'addressed' needs two copies."
        )
    in_play = {h for h in (current_hash, historical_hash) if h}
    for audit in audits.values():
        if audit.data.get("candidate_hash") not in in_play:
            raise EsrComparisonError(
                f"audit {audit.key} is over candidate {str(audit.data.get('candidate_hash'))[:19]}, "
                "which is neither the current nor the historical candidate."
            )

    # The ESR's criteria and aspects must be the baseline's.
    baseline_criteria = {str(s.get("criterion_id")) for s in (baseline.get("criterion_scoring") or {}).get("scores") or []}
    esr_criteria = set(esr.criterion_scores)
    if esr_criteria != baseline_criteria:
        raise EsrComparisonError(
            f"the ESR record scores {sorted(esr_criteria)}, the baseline {sorted(baseline_criteria)}."
        )
    aspects = {str(c.get("expectation_key")): c for c in baseline.get("cells") or []}
    weights = _criterion_weights(baseline)

    # Every observation disposed, every disposition for a known observation.
    obs_ids = [str(o["id"]) for o in esr.observations]
    missing = [oid for oid in obs_ids if oid not in dispositions.rows]
    if missing:
        raise EsrComparisonError(
            f"{len(missing)} observation(s) have no disposition: {', '.join(missing)}."
        )
    unknown = sorted(set(dispositions.rows) - set(obs_ids))
    if unknown:
        raise EsrComparisonError(
            f"dispositions name observation(s) the ESR record does not: {', '.join(unknown)}."
        )

    version = dispositions.schema_version
    identity_pointers = version in VERSIONS_WITH_IDENTITY_POINTERS
    shared = (
        _shared_sentences(esr.observations)
        if version in VERSIONS_REPORTING_SHARED_SENTENCES
        else {}
    )

    rows: list[dict[str, Any]] = []
    for obs in esr.observations:
        oid = str(obs["id"])
        row = dispositions.rows[oid]
        label = f"observation {oid}"
        disposition = row.get("disposition")
        if disposition not in DISPOSITIONS:
            raise EsrComparisonError(
                f"{label}: disposition {disposition!r}; one of {', '.join(DISPOSITIONS)} is required."
            )
        if obs["criterion_id"] not in baseline_criteria:
            raise EsrComparisonError(f"{label}: criterion {obs['criterion_id']!r} is not scored by the baseline.")
        if obs["aspect_id"] not in aspects:
            raise EsrComparisonError(f"{label}: aspect {obs['aspect_id']!r} is not a baseline cell.")
        blind = [
            resolve_blind_reference(baseline, ref, label=label)
            for ref in row.get("blind_findings") or []
        ]
        audit_refs = [
            resolve_audit_reference(audits, ref, label=label)
            for ref in row.get("audit_findings") or []
        ]
        current = [
            verify_evidence(candidate, ref, label=f"{label} (current evidence)")
            for ref in row.get("current_evidence") or []
        ]
        historical_refs = row.get("historical_evidence") or []
        if historical_refs and historical_candidate is None:
            raise EsrComparisonError(
                f"{label}: historical evidence is quoted but no historical candidate was given."
            )
        historical = [
            verify_evidence(historical_candidate, ref, label=f"{label} (historical evidence)")
            for ref in historical_refs
        ] if historical_candidate is not None else []
        if historical_candidate is not None and not historical_refs:
            # No separate historical quote declared: the current quotes that also
            # occur in the historical copy stand for it, each re-verified there.
            historical = [
                dict(verify_evidence(historical_candidate, ref, label=label), same_as_current=True)
                for ref in current if _occurs(historical_candidate, ref)
            ]
        register_refs = [
            resolve_register_pointer(
                register.data, str(ptr), label=label, legacy_positional=not identity_pointers
            )
            for ptr in row.get("evidence_basis") or []
        ]
        revision = row.get("proposed_revision")
        if revision is not None:
            if not isinstance(revision, Mapping) or not str(revision.get("text") or "").strip():
                raise EsrComparisonError(f"{label}: proposed_revision needs a text.")
            _declared(revision, "declared_status", label=f"{label} (proposed_revision)", required=True)
            check_revision_scope(revision, kind=obs["kind"], label=f"{label} (proposed_revision)")
            check_revision_plan(revision, label=f"{label} (proposed_revision)")
        _declared(row, "evidence_preserved_status", label=label, required=False)
        review_status = row.get("review_status")
        if review_status is not None and review_status not in ROW_REVIEW_STATES:
            raise EsrComparisonError(
                f"{label}: review_status {review_status!r}; one of "
                f"{', '.join(ROW_REVIEW_STATES)} is required when the field is present."
            )
        deferred = row.get("deferred_to_private_network")
        if deferred is not None and (not isinstance(deferred, str) or not deferred.strip()):
            raise EsrComparisonError(
                f"{label}: deferred_to_private_network must be text naming what the "
                "private network has to establish, or absent."
            )
        decision_ids = row.get("operator_decision_ids")
        if decision_ids is not None and (
            not isinstance(decision_ids, list) or not decision_ids
            or not all(isinstance(d, str) and d.strip() for d in decision_ids)
        ):
            raise EsrComparisonError(
                f"{label}: operator_decision_ids must be a non-empty list of decision ids "
                "from the approval record the dispositions name, or absent."
            )
        if decision_ids is not None and not dispositions.data.get("operator_approval"):
            raise EsrComparisonError(
                f"{label}: operator_decision_ids are declared but the dispositions record "
                "names no operator_approval record they could be found in."
            )
        check_row_rules(
            obs, disposition,
            blind=blind, audit=audit_refs, current=current, historical=historical,
            register_refs=register_refs, register=register.data, row=row, label=label,
            schema_version=dispositions.schema_version,
        )
        lanes = sorted({LANE_BLIND for _ in blind} | {LANE_AUDIT for _ in audit_refs})
        contests = obs["kind"] == OBSERVATION_KIND_STRENGTH and any(
            b.get("polarity") == "shortcoming" for b in blind
        )
        counted = obs["kind"] != OBSERVATION_KIND_STRENGTH and disposition not in (
            DISPOSITION_ADDRESSED, DISPOSITION_NOT_ASSESSABLE
        )
        cell = aspects[obs["aspect_id"]]
        rows.append({
            "observation_id": oid,
            "cluster_id": obs.get("cluster_id"),
            "criterion_id": obs["criterion_id"],
            "aspect_id": obs["aspect_id"],
            "kind": obs["kind"],
            "severity_wording": obs.get("severity_wording"),
            "historical_finding": obs["text"],
            "historical_location": obs["esr_location"],
            "proposal_location": obs.get("proposal_location"),
            "historical_proposal_evidence": {
                "note": (
                    "The submitted document is not available in this environment; the "
                    "historical evidence is quoted from the earlier sanitised copy, which "
                    "stands for the submission only as far as the fidelity register says."
                    if historical_candidate is not None
                    else "The submitted document is not available in this environment; no "
                    "historical copy was given, so the current copy stands for both."
                ),
                "quotes": historical,
            },
            "current_proposal_evidence": current,
            "blind_findings": blind,
            "audit_findings": audit_refs,
            "detected_by": lanes,
            "blind_cell": {
                "covered": bool(cell.get("covered")),
                "addressal": cell.get("addressal"),
                "grounding": cell.get("grounding"),
                "score": cell.get("score"),
            },
            "evidence_basis": register_refs,
            "evidence_preserved_status": row.get("evidence_preserved_status"),
            "disposition": disposition,
            "disposition_status": _declared(row, "declared_status", label=label, required=True),
            "explanation": row["explanation"],
            "counted_in_detection_rate": counted,
            "contests_historical_strength": contests,
            "proposed_revision": row.get("proposed_revision"),
            # Only a row that declares a review status carries one, so a record
            # that declares none keeps the row shape it had before ticket R05.
            # The same holds for every field below: each is emitted only when
            # the record declares it, so an older comparison replays unchanged.
            **({"review_status": review_status} if review_status is not None else {}),
            **({"failure_mode": row["failure_mode"],
                "failure_mode_basis": row.get("failure_mode_basis")}
               if row.get("failure_mode") is not None else {}),
            **({"shares_esr_sentence_with": shared[oid]} if shared.get(oid) else {}),
            **({"deferred_to_private_network": deferred} if deferred is not None else {}),
            **({"operator_decision_ids": list(decision_ids)} if decision_ids is not None else {}),
        })

    summary = _summarise(rows, baseline_criteria)
    if version in VERSIONS_REQUIRING_A_FAILURE_MODE:
        summary["misses_by_failure_mode"] = _misses_by_failure_mode(rows)
    if shared:
        summary["shared_esr_sentences"] = _shared_sentence_report(rows, shared)
    unresolved = [
        r["observation_id"] for r in rows if r.get("disposition_status") == "Unresolved"
    ]
    if unresolved:
        # A count has to count something, so an Unresolved row is counted under
        # the disposition it declares. CLAUDE.md §12.2 says such a status needs
        # resolution before downstream use, so the figures are provisional on
        # these rows and the summary says which.
        summary["declarations_unresolved"] = {
            "rows": unresolved,
            "statement": (
                f"{len(unresolved)} row(s) declare a disposition status of 'Unresolved' "
                "(CLAUDE.md §12.2: resolution required before downstream use). Each is "
                "counted above under the disposition it declares, because a count must "
                "count something. Every figure that includes one is provisional on the "
                "operator decision the dispositions record names for that row."
            ),
        }
    scores = _compare_scores(esr, baseline, frozen.record)
    revisions = _prioritise(rows, weights, esr_criteria=sorted(esr_criteria))
    open_without_revision = [
        r["observation_id"] for r in rows
        if r["kind"] != OBSERVATION_KIND_STRENGTH
        and r["disposition"] != DISPOSITION_ADDRESSED
        and not (isinstance(r.get("proposed_revision"), Mapping) and r["proposed_revision"].get("text"))
    ]
    if open_without_revision:
        flags.append(
            "open shortcoming(s) without a proposed revision: " + ", ".join(open_without_revision)
        )
    now = (clock or _utc_now)()
    data: dict[str, Any] = {
        "record_type": COMPARISON_RECORD_TYPE,
        "schema_version": COMPARISON_SCHEMA_VERSION,
        "metric": "esr_comparison",
        "advisory": True,
        "blocking": False,
        "compared_at": now,
        "baseline": {
            "baseline_dir": _portable(frozen.freeze_path.parent, repo_root),
            "freeze_record": frozen.freeze_path.name,
            "report_copy": frozen.record.get("report_copy"),
            "report_sha256": report_sha,
            "candidate_hash": bindings.get("candidate_hash"),
            "profile_id": bindings.get("profile_id"),
            "profile_version": bindings.get("profile_version"),
            "assessor_pin": bindings.get("assessor_pin"),
            "assessor_transport": bindings.get("assessor_transport"),
            "snapshot_id": bindings.get("snapshot_id"),
            "package_id": bindings.get("package_id"),
            "intake_id": bindings.get("intake_id"),
        },
        "esr_record": {"path": _portable(esr.path, repo_root), "sha256": esr.sha256,
                       "source": esr.data.get("source")},
        "dispositions": {
            "path": _portable(dispositions.path, repo_root),
            "sha256": dispositions.sha256,
            "declared_by": dispositions.data.get("declared_by"),
            "declared_on": dispositions.data.get("declared_on"),
            **({"review_state": dispositions.review_state}
               if dispositions.review_state is not None else {}),
        },
        "candidate": {
            "path": candidate_path,
            "candidate_hash": current_hash,
            "document": _document_of(candidate),
        },
        "historical_candidate": None if historical_candidate is None else {
            "path": historical_candidate_path,
            "candidate_hash": historical_hash,
            "document": _document_of(historical_candidate),
        },
        "fidelity_register": {
            "path": _portable(register.path, repo_root),
            "sha256": register.sha256,
            # Recorded only under the identity rule: an older comparison was
            # written under the legacy rule and keeps the shape it had.
            **({"pointer_resolution": POINTER_RESOLUTION_IDENTITY} if identity_pointers else {}),
        },
        "audits": [
            {"path": a.key, "sha256": a.sha256, "candidate_hash": a.data.get("candidate_hash")}
            for a in audits.values()
        ],
        "dispositions_vocabulary": list(DISPOSITIONS),
        "rows": rows,
        "summary": summary,
        "score_comparison": scores,
        "revisions_artifact": None,
        "flags": flags,
        "notes": _NOTE,
    }
    if dispositions.review_state is not None:
        # The generic note says the dispositions are the operator's. A record
        # that declares a review state says whose they actually are, and the
        # comparison must carry that rather than leave a reader to find it two
        # files away.
        data["review_state"] = {
            "state": dispositions.review_state,
            "statement": (
                _REVIEW_STATE_DRAFT
                if dispositions.review_state == REVIEW_STATE_AGENT_DRAFTED
                else _REVIEW_STATE_REVIEWED
            ),
            "rows_needing_an_operator_decision": [
                r["observation_id"] for r in rows
                if r.get("review_status") == "operator_decision_required"
            ],
            # An operator-reviewed record says which rows the review confirmed
            # and which it left as an agent's; an agent-drafted record has no
            # confirmed row and keeps the block it had.
            **({
                "rows_operator_confirmed": [
                    r["observation_id"] for r in rows
                    if r.get("review_status") == "operator_confirmed"
                ],
                "rows_agent_recommended": [
                    r["observation_id"] for r in rows
                    if r.get("review_status") == "agent_recommended_pending_operator_review"
                ],
                "operator_approval": dispositions.data.get("operator_approval"),
            } if dispositions.review_state == REVIEW_STATE_OPERATOR_REVIEWED else {}),
        }
    revisions_record = {
        "record_type": REVISIONS_RECORD_TYPE,
        "schema_version": COMPARISON_SCHEMA_VERSION,
        "advisory": True,
        "blocking": False,
        "compared_at": now,
        "baseline_report_sha256": report_sha,
        "candidate_hash": current_hash,
        "esr_record_sha256": esr.sha256,
        "dispositions_sha256": dispositions.sha256,
        "priority_rule": (
            "severity first (shortcoming before minor shortcoming before strength), then the "
            "criterion's weight, then disposition (not detected, detected, partial, not "
            "assessable), then the ESR's own order. 'addressed' rows are listed as closed. "
            "The order is derived from the declared rows; no priority is declared by hand."
        ),
        **revisions,
        "notes": _NOTE,
    }
    beyond = _beyond_esr_improvements(rows)
    if beyond:
        revisions_record["beyond_esr_improvements"] = beyond
    return ComparisonReport(data=data, revisions=revisions_record, baseline_report_sha256=report_sha)


def _shared_sentences(observations: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    """Observation id -> the other ids transcribed from the same ESR sentence.

    Measured from the ESR record's own text (operator decision D01): the
    transcription may split one evaluator sentence into clause-level
    observations, and the comparison must say so rather than present the
    clauses as separate evaluator sentences.
    """
    groups: dict[str, list[str]] = {}
    for obs in observations:
        groups.setdefault(normalise_text(str(obs["text"])), []).append(str(obs["id"]))
    return {
        oid: [other for other in ids if other != oid]
        for ids in groups.values() if len(ids) > 1
        for oid in ids
    }


def _shared_sentence_report(
    rows: Sequence[Mapping[str, Any]], shared: Mapping[str, Sequence[str]]
) -> dict[str, Any]:
    by_id = {r["observation_id"]: r for r in rows}
    groups: list[dict[str, Any]] = []
    seen: set[str] = set()
    for oid in [r["observation_id"] for r in rows]:
        if oid in seen or oid not in shared:
            continue
        members = [oid, *shared[oid]]
        seen.update(members)
        groups.append({
            "observation_ids": members,
            "cluster_id": by_id[oid].get("cluster_id"),
            "severity_wording": by_id[oid].get("severity_wording"),
            "dispositions": {m: by_id[m]["disposition"] for m in members},
            "detected_by": {m: list(by_id[m]["detected_by"]) for m in members},
        })
    return {
        "groups": groups,
        "statement": (
            "Each group is one evaluator sentence that the ESR record transcribes as "
            "clause-level observations. The counts above are per observation, so one "
            "sentence appears once per clause and is not a separate evaluator sentence, "
            "an independent deduction, or a cluster-level detection; the cluster and the "
            "severity wording are the sentence's own."
        ),
    }


def _misses_by_failure_mode(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    misses = [r for r in rows if r["disposition"] == DISPOSITION_NOT_DETECTED]
    return {
        "by_mode": {
            mode: [r["observation_id"] for r in misses if r.get("failure_mode") == mode]
            for mode in MISS_FAILURE_MODES
        },
        "statement": (
            "Every miss is counted in the detection figures above whatever its mode "
            "(operator decision D03). The breakdown here is separate: an adequacy "
            f"disagreement ('{FAILURE_MODE_RATED_ADEQUATE}') and an unmentioned topic "
            f"('{FAILURE_MODE_ABSENT}') are different failures of the same count. "
            f"'{FAILURE_MODE_ABSENT}' describes the recorded output and does not establish "
            "that the model did not read the evidence (D02). Neither the count nor the "
            "breakdown is an overall accuracy or calibration claim."
        ),
    }


def _beyond_esr_improvements(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Every proposed revision or subtask declared beyond the ESR, kept apart."""
    out: list[dict[str, Any]] = []
    for r in rows:
        rev = r.get("proposed_revision") if isinstance(r.get("proposed_revision"), Mapping) else None
        if rev is None:
            continue
        plan = rev.get("revision_plan") if isinstance(rev.get("revision_plan"), Mapping) else {}
        if rev.get("scope") == REVISION_SCOPE_BEYOND:
            out.append({
                "observation_id": r["observation_id"],
                "kind": r["kind"],
                "label": rev.get("label"),
                "proposed_revision": rev.get("text"),
                "revision_status": rev.get("declared_status"),
                "commitment_kind": plan.get("commitment_kind"),
                "requires_confirmation": list(plan.get("requires_confirmation") or []),
            })
        for task in plan.get("subtasks") or []:
            if isinstance(task, Mapping) and task.get("scope") == REVISION_SCOPE_BEYOND:
                out.append({
                    "observation_id": r["observation_id"],
                    "kind": r["kind"],
                    "label": task.get("label"),
                    "proposed_revision": task.get("text"),
                    "revision_status": rev.get("declared_status"),
                    "commitment_kind": task.get("commitment_kind", plan.get("commitment_kind")),
                    "requires_confirmation": list(task.get("requires_confirmation") or []),
                    "within_revision_of": r["observation_id"],
                })
    return out


def _document_of(candidate: Candidate) -> str | None:
    for content in candidate.contents.values():
        doc = content.get("document") if isinstance(content, Mapping) else None
        if doc:
            return str(doc)
    return None


def _summarise(rows: Sequence[Mapping[str, Any]], criteria: set[str]) -> dict[str, Any]:
    def block(subset: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        total = len(subset)
        by_disposition = {d: sum(1 for r in subset if r["disposition"] == d) for d in DISPOSITIONS}
        by_kind = {k: sum(1 for r in subset if r["kind"] == k) for k in OBSERVATION_KINDS}
        not_assessable = by_disposition[DISPOSITION_NOT_ASSESSABLE]
        assessable = total - not_assessable
        rated = [r for r in subset if r["counted_in_detection_rate"]]
        detected = sum(1 for r in rated if r["disposition"] == DISPOSITION_INDEPENDENTLY_DETECTED)
        partial = sum(1 for r in rated if r["disposition"] == DISPOSITION_PARTIALLY_OBSERVABLE)
        missed = sum(1 for r in rated if r["disposition"] == DISPOSITION_NOT_DETECTED)
        n = len(rated)
        return {
            "observations": total,
            "by_kind": by_kind,
            "by_disposition": by_disposition,
            "assessable": assessable,
            "not_assessable": not_assessable,
            "assessable_fraction": None if total == 0 else _round(assessable / total),
            "detection": {
                "basis": _DETECTION_BASIS,
                "rated": len(rated),
                "independently_detected": detected,
                "partially_observable": partial,
                "not_detected": missed,
                "rate_detected": None if not n else _round(detected / n),
                "rate_detected_or_partial": None if not n else _round((detected + partial) / n),
                "rate_note": (
                    "rate_detected counts only 'independently_detected'; "
                    "rate_detected_or_partial adds 'partially_observable', whose rows rest "
                    "in part on evidence this copy lacks. Neither counts 'not assessable'."
                ),
                "by_lane": {
                    LANE_BLIND: sum(1 for r in rated if LANE_BLIND in r["detected_by"]),
                    LANE_AUDIT: sum(1 for r in rated if LANE_AUDIT in r["detected_by"]),
                },
            },
            "strengths_contested_by_blind_findings": sum(
                1 for r in subset if r["contests_historical_strength"]
            ),
        }

    return {
        **block(rows),
        "not_assessable_counted_as_failure": False,
        "not_assessable_dropped": False,
        "statement": _NOT_ASSESSABLE_STATEMENT,
        "by_criterion": {
            cid: block([r for r in rows if r["criterion_id"] == cid]) for cid in sorted(criteria)
        },
    }


def _compare_scores(esr: EsrRecord, baseline: Mapping[str, Any], freeze: Mapping[str, Any]) -> dict[str, Any]:
    scoring = baseline.get("criterion_scoring") or {}
    blind = {str(s.get("criterion_id")): s for s in scoring.get("scores") or []}
    criteria = []
    for cid, hist in esr.criterion_scores.items():
        b = blind[cid]
        criteria.append({
            "criterion_id": cid,
            "historical_score": hist["score"],
            "blind_median": b.get("score"),
            "blind_spread": b.get("spread"),
            "blind_samples": len(b.get("samples") or []),
            "difference": None if b.get("score") is None else _round(float(b["score"]) - float(hist["score"])),
            "threshold": hist["threshold"],
            "weight_pct": hist["weight_pct"],
        })
    result = esr.data["evaluation_result"]
    return {
        "criteria": criteria,
        "total": {
            "historical": result["total"],
            "blind": scoring.get("total"),
            "difference": None if scoring.get("total") is None else _round(float(scoring["total"]) - float(result["total"])),
            "overall_threshold": result.get("overall_threshold", scoring.get("overall_threshold")),
            "formula": scoring.get("formula"),
        },
        "spread_label": freeze.get("spread_label") or scoring.get("spread_label"),
        "no_deduction_attributed_to_individual_criticism": True,
        "statement": _SCORE_STATEMENT,
    }


def _prioritise(rows: Sequence[Mapping[str, Any]], weights: Mapping[str, float], *, esr_criteria: Sequence[str]) -> dict[str, Any]:
    order = {oid: i for i, oid in enumerate(r["observation_id"] for r in rows)}

    def key(r: Mapping[str, Any]) -> tuple:
        return (
            _KIND_RANK[r["kind"]],
            -weights.get(r["criterion_id"], 0.0),
            _DISPOSITION_RANK[r["disposition"]],
            order[r["observation_id"]],
        )

    def entry(r: Mapping[str, Any], rank: int | None) -> dict[str, Any]:
        rev = r.get("proposed_revision") if isinstance(r.get("proposed_revision"), Mapping) else None
        out = {
            "priority": rank,
            "observation_id": r["observation_id"],
            "criterion_id": r["criterion_id"],
            "aspect_id": r["aspect_id"],
            "kind": r["kind"],
            "disposition": r["disposition"],
            "historical_finding": r["historical_finding"],
            "proposed_revision": None if rev is None else rev.get("text"),
            "revision_status": None if rev is None else rev.get("declared_status"),
            "needs_private_network": r["disposition"] == DISPOSITION_NOT_ASSESSABLE,
        }
        # Only a row that declares a plan carries one, so a dispositions record
        # that declares none keeps the artifact shape it had before ticket R05.
        plan = None if rev is None else rev.get("revision_plan")
        if plan is not None:
            out["revision_plan"] = plan
        return out

    open_rows = sorted(
        [r for r in rows if r["disposition"] != DISPOSITION_ADDRESSED and r["kind"] != OBSERVATION_KIND_STRENGTH],
        key=key,
    )
    contested = sorted(
        [r for r in rows if r["kind"] == OBSERVATION_KIND_STRENGTH and r["contests_historical_strength"]],
        key=key,
    )
    closed = [r for r in rows if r["disposition"] == DISPOSITION_ADDRESSED]
    return {
        "open": [entry(r, i + 1) for i, r in enumerate(open_rows)],
        "contested_strengths": [entry(r, None) for r in contested],
        "closed": [entry(r, None) for r in closed],
        "criteria_order": list(esr_criteria),
    }


# --------------------------------------------------------------------------- #
# Persistence and rendering
# --------------------------------------------------------------------------- #


def write_comparison(report: ComparisonReport, out_dir: Path | str) -> tuple[Path, Path]:
    """Write ``comparison_<sha12>_<NNNN>.json`` and ``revisions_<sha12>_<NNNN>.json``;
    never overwrite. The two share a sequence number."""
    out = Path(out_dir)
    digest = "sha256:" + report.baseline_report_sha256
    target = next_report_path(out, digest, prefix=_COMPARISON_PREFIX)
    seq = target.name.rsplit("_", 1)[1]
    revisions = out / f"{_REVISIONS_PREFIX}_{report.baseline_report_sha256[:12]}_{seq}"
    if revisions.exists():
        raise EsrComparisonError(f"{revisions} already exists; nothing overwritten.")
    out.mkdir(parents=True, exist_ok=True)
    data = dict(report.data)
    data["revisions_artifact"] = (Path(out_dir) / revisions.name).as_posix()
    data["writes"] = [(Path(out_dir) / target.name).as_posix(), data["revisions_artifact"]]
    atomic_write_json(report.revisions, revisions, prefix="esr_revisions_")
    atomic_write_json(data, target, prefix="esr_comparison_")
    return target, revisions


def load_comparison(path: Path | str) -> dict[str, Any]:
    p = Path(path)
    data = _read_json(p, "comparison report")
    if data.get("record_type") != COMPARISON_RECORD_TYPE:
        raise EsrComparisonError(f"{p} is not an {COMPARISON_RECORD_TYPE!r} record.")
    if data.get("advisory") is not True or data.get("blocking") is not False:
        raise EsrComparisonError(f"comparison {p} must carry advisory=true and blocking=false.")
    for key in ("baseline", "rows", "summary", "score_comparison"):
        if key not in data:
            raise EsrComparisonError(f"comparison {p} lacks {key!r}.")
    return data


def render_comparison(data: Mapping[str, Any]) -> str:
    """One screen: bindings, the disposition counts, the score table."""
    b = data.get("baseline") or {}
    s = data.get("summary") or {}
    lines = [
        f"ESR COMPARISON  baseline {str(b.get('report_sha256') or '')[:12]}  "
        f"candidate {str(b.get('candidate_hash') or '')[:19]}",
        f"assessor:      {b.get('assessor_pin')}  transport={b.get('assessor_transport')}",
        f"ESR record:    {(data.get('esr_record') or {}).get('path')}",
        f"dispositions:  {(data.get('dispositions') or {}).get('path')}",
        *(
            [f"review state:  {(data['review_state'])['state']}  "
             f"(operator decisions required on "
             f"{len(data['review_state']['rows_needing_an_operator_decision'])} row(s))"]
            if data.get("review_state") else []
        ),
        f"observations:  {s.get('observations')}  assessable {s.get('assessable')} "
        f"({s.get('assessable_fraction')})  not assessable {s.get('not_assessable')}",
    ]
    for d, n in (s.get("by_disposition") or {}).items():
        lines.append(f"  - {d}: {n}")
    det = s.get("detection") or {}
    lines.append(
        f"detection:     {det.get('independently_detected')} detected + "
        f"{det.get('partially_observable')} partial / {det.get('rated')} rated "
        f"(detected {det.get('rate_detected')}, with partial {det.get('rate_detected_or_partial')}; "
        "not assessable never counted)"
    )
    lines.append(f"contested strengths: {s.get('strengths_contested_by_blind_findings')}")
    sc = data.get("score_comparison") or {}
    lines.append("scores (historical vs blind median, spread):")
    for c in sc.get("criteria") or []:
        lines.append(
            f"  - {c.get('criterion_id')}: {c.get('historical_score')} vs "
            f"{c.get('blind_median')} (spread {c.get('blind_spread')}, diff {c.get('difference')})"
        )
    t = sc.get("total") or {}
    lines.append(f"  total: {t.get('historical')} vs {t.get('blind')} (diff {t.get('difference')})")
    lines.append("no deduction is attributed to any individual criticism")
    unresolved = (s.get("declarations_unresolved") or {}).get("rows") or []
    if unresolved:
        lines.append(
            f"provisional: {len(unresolved)} row(s) declare an Unresolved status "
            f"({', '.join(unresolved)})"
        )
    for flag in data.get("flags") or []:
        lines.append(f"FLAG: {flag}")
    return "\n".join(lines)


__all__ = [
    "COMPARISON_RECORD_TYPE",
    "DECLARED_STATUSES",
    "DISPOSITIONS",
    "DISPOSITIONS_RECORD_TYPE",
    "DISPOSITIONS_SCHEMA_VERSIONS",
    "ESR_RECORD_TYPE",
    "OBSERVATION_KINDS",
    "RECORD_REVIEW_STATES",
    "REVISIONS_RECORD_TYPE",
    "REVISION_COMMITMENT_EDITORIAL",
    "REVISION_COMMITMENT_KINDS",
    "REVISION_PLAN_FIELDS",
    "REVIEW_STATE_AGENT_DRAFTED",
    "REVIEW_STATE_OPERATOR_REVIEWED",
    "ROW_REVIEW_STATES",
    "VERSIONS_REQUIRING_A_MISS_BASIS",
    "VERSIONS_REQUIRING_A_FAILURE_MODE",
    "VERSIONS_WITH_IDENTITY_POINTERS",
    "VERSIONS_REPORTING_SHARED_SENTENCES",
    "POINTER_RESOLUTION_IDENTITY",
    "POINTER_RESOLUTION_LEGACY",
    "ORIGINAL_FIDELITY_FIELD",
    "ORIGINAL_FIDELITY_SCOPE",
    "MISS_FAILURE_MODES",
    "REVISION_SCOPES",
    "REVISION_SCOPE_BEYOND",
    "REVISION_SCOPE_ESR",
    "ComparisonReport",
    "Dispositions",
    "EsrComparisonError",
    "EsrRecord",
    "LoadedAudit",
    "Register",
    "load_register",
    "check_preservation_claim",
    "check_failure_mode",
    "check_revision_scope",
    "check_subtasks",
    "check_revision_plan",
    "check_row_rules",
    "declared_half_entry",
    "load_audits",
    "load_comparison",
    "load_dispositions",
    "load_esr_record",
    "normalise_text",
    "render_comparison",
    "resolve_audit_reference",
    "resolve_blind_reference",
    "pointer_rule_of",
    "resolve_pointer",
    "run_comparison",
    "verify_evidence",
    "write_comparison",
]
