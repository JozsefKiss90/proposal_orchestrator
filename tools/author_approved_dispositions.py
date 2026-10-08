"""The PE-08 operator approval, carried into successor dispositions and notes.

On 2026-10-08 the operator approved the PE-08 decision package
(``docs/tier4_orchestration_state/msca_dn/reviews/operator_approval_2026-10-08.md``):
fifteen review decisions D01-D15, two validation corrections V01 and V02, a
table of original-dependent questions explicitly deferred to the private
network, and the boundaries of what the approval does and does not confer.
This module writes that approval into the artifacts the harness reads.

What this module is
-------------------
A deterministic, Claude-free transform, in the shape of
:mod:`tools.author_successor_dispositions`. It reads the committed R05 record
and applies a fixed, enumerated set of changes, each tied to a decision id:

* every row carries a ``review_status`` that says what the approval did to it
  — ``operator_confirmed`` where a decision settles the row's disposition,
  ``operator_decision_required`` where the approval deferred the row to the
  private network, and ``agent_recommended_pending_operator_review`` where it
  said nothing, because "the other agent-drafted observations are not
  blanket-confirmed by this approval";
* a confirmed row names the decision ids it rests on, and a deferred row
  states what the private network has to establish;
* ``ESR-Q-03`` moves to ``partially_observable`` on the integrity audit's one
  timing finding (D06), re-cited against the audit written after D11 retired
  the undeclared-dependency findings;
* every miss declares its failure mode (D03), with ESR-E-03's described as an
  absence from the recorded output and not as evidence unread (D02);
* ``ESR-I-S02`` gains a beyond-ESR improvement conditional on the original
  (D07), and ``ESR-I-02``'s plan gains a separately labelled societal-impact
  subtask (D08); neither proposes an indicator, a target, a funding source or
  a partner commitment;
* the record is schema 1.2, so ``derived/sub_sections/8/characters`` and
  ``derived/sub_sections/5/characters`` on ESR-Q-S02 and ESR-Q-S03 resolve
  by identity (V02) and the review notes' character counts are corrected.

Everything else is carried through byte for byte. The successor review notes
are the R03 notes with the recorded decisions transcribed under their ids and
the deferred questions restated, bound to the comparison written from the
successor dispositions; they are rendered only once that comparison exists.

What this module does not do
----------------------------
It confirms no evidence: an operator approval is an authority fact and the
four statuses describe evidence (approval record, "Revision and approval
boundaries"). It adopts no declaration (D13), applies no provenance
correction (D14), edits no proposal text, and runs no assessor. The seven
preservation-qualified misses stay provisional.

Usage::

    py -3.10 -m tools.author_approved_dispositions          # write
    py -3.10 -m tools.author_approved_dispositions --check   # byte-equal replay
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from runner.atomic_write import atomic_write_text, canonical_json_bytes
from runner.paths import find_repo_root
from tools.author_successor_dispositions import (
    AUDIT_DIR,
    COMPARISON_DIR,
    ESR_DIR,
    ESR_RECORD_REL,
    FIRST_REVISION_AUDIT_REL,
    REGISTER_REL,
    REVIEW_DIR,
    ROLES,
    SUCCESSOR_REL as PREDECESSOR_REL,
    SuccessorError,
    _read_json,
    _sha256,
)
from tools.fidelity_declarations import file_sha256

SUCCESSOR_REL = ESR_DIR / "dispositions_f60ae6e0a2a1_approved.json"
NOTES_PREDECESSOR_REL = ESR_DIR / "review_notes_f60ae6e0a2a1_r03.json"
NOTES_SUCCESSOR_REL = ESR_DIR / "review_notes_f60ae6e0a2a1_approved.json"
APPROVAL_REL = REVIEW_DIR / "operator_approval_2026-10-08.md"
ADJUDICATIONS_REL = ESR_DIR / "semantic_adjudications_f60ae6e0a2a1.json"
PREDECESSOR_COMPARISON_REL = COMPARISON_DIR / "comparison_f60ae6e0a2a1_0002.json"
SUCCESSOR_AUDIT_REL = AUDIT_DIR / "integrity_242f1afb02c8_0003.json"
PREDECESSOR_AUDIT_REL = AUDIT_DIR / "integrity_242f1afb02c8_0002.json"
DECLARATION_DRAFT_REL = Path("docs/tier4_orchestration_state/msca_dn/declarations/draft_resolved_fixes.json")

SCHEMA_VERSION = "1.2"
REVIEW_STATE = "operator_reviewed"
DECLARED_ON = "2026-10-08"
APPROVED_AT = "2026-10-08T10:37:26+02:00"
APPROVAL_INSTRUCTION = "Approve this decision package"

STATUS_CONFIRMED = "operator_confirmed"
STATUS_REQUIRED = "operator_decision_required"
STATUS_AGENT = "agent_recommended_pending_operator_review"


# --------------------------------------------------------------------------- #
# The decisions, transcribed from the approval record
# --------------------------------------------------------------------------- #

#: Decision id -> the approved decision and the limit retained, verbatim from
#: the approval record's table. Only the ids a row rests on are copied into
#: that row; the record is the authority and this is its transcription.
DECISIONS: Mapping[str, Mapping[str, str]] = {
    "D01": {
        "subject": "E-01/E-02 shared ESR sentence",
        "decision": (
            "Keep methods and clinical-data security as separate clause-level observations. "
            "Report their shared sentence and severity cluster."
        ),
        "limit": (
            "Do not present them as separate evaluator sentences, independent deductions, or "
            "inflate cluster-level detection."
        ),
    },
    "D02": {
        "subject": "E-03 validation design",
        "decision": "Accept non-detection of the criticism in the recorded output.",
        "limit": (
            "Do not claim absence from output proves the model did not read the evidence. "
            "Qualify or replace the `evidence_not_read` causal description in successor "
            "documentation. Preservation remains separately qualified."
        ),
    },
    "D03": {
        "subject": "E-07/E-09 adequacy disagreements",
        "decision": (
            "Count missed ESR criticisms in the same detection summary, subject to "
            "preservation; distinguish adequacy disagreement from an unmentioned topic."
        ),
        "limit": (
            "Report failure-mode breakdowns separately. Detection is not an overall accuracy "
            "or calibration claim."
        ),
    },
    "D04": {
        "subject": "Q-01/Q-03 contradicted milestone citation",
        "decision": (
            "Withdraw the contradicted citation and retain it as an assessor validation case "
            "for PE-09."
        ),
        "limit": "Never edit proposal milestones to satisfy the false absence claim.",
    },
    "D05": {
        "subject": "Q-02 table conflation",
        "decision": "Record the deliverable/milestone conflation as an assessor validation case.",
        "limit": (
            "A missing validation column does not prove inadequate deliverable validation. "
            "Review relevant prose and original-dependent evidence before finalising the "
            "proposal judgment."
        ),
    },
    "D06": {
        "subject": "Q-03 detection credit",
        "decision": (
            "Replace full detection with provisional partial detection; integrity audit is "
            "the only contributing lane."
        ),
        "limit": (
            "The surviving finding concerns timing only. Definitions are not detected; timing "
            "interpretation remains Unresolved. If original context removes the alleged "
            "conflict, revisit detection credit."
        ),
    },
    "D07": {
        "subject": "I-S02 sustainability funding",
        "decision": (
            "Prepare an optional improvement beyond the ESR, conditional on checking the "
            "original."
        ),
        "limit": (
            "No funding source, budget, maintenance duty or partner commitment is approved. "
            "Preserve the ESR strength."
        ),
    },
    "D08": {
        "subject": "I-S05 societal indicators",
        "decision": (
            "Add a separately labelled societal-impact subtask within the broader impact "
            "revision package."
        ),
        "limit": (
            "Keep it distinct from the ESR economic/technological criticism. No invented "
            "indicators, numerical targets or promised clinical outcomes."
        ),
    },
    "D11": {
        "subject": "A03 milestone dependencies",
        "decision": (
            "Retire missing deliverable references as defect findings. Check explicit "
            "references for nonexistent deliverables or contradictory sequencing."
        ),
        "limit": (
            "Links may be suggested as drafting advice. Do not assume every milestone depends "
            "on a deliverable or invent a link."
        ),
    },
    "D12": {
        "subject": "M7.3 scheduling decision",
        "decision": (
            "Defer date changes and relocation until duration, WP scope and intended "
            "follow-up timing are privately verified."
        ),
        "limit": (
            "The two existing alternatives are not exhaustive. Retaining the date with "
            "adequate explanation may be justified by the original context."
        ),
    },
}

#: Observation id -> the decision ids that settle its disposition. A row listed
#: here is ``operator_confirmed``; the decision text is on the notes row.
CONFIRMED: Mapping[str, Sequence[str]] = {
    "ESR-E-01": ["D01"],
    "ESR-E-03": ["D02"],
    "ESR-E-07": ["D03"],
    "ESR-E-09": ["D03"],
    "ESR-I-S02": ["D07"],
    "ESR-I-S05": ["D08"],
    "ESR-Q-01": ["D04"],
    "ESR-Q-02": ["D05"],
    "ESR-Q-03": ["D06", "D12"],
}

#: Observation id -> what the approval record defers to the private network,
#: verbatim from its table of original-dependent decisions. A row listed here
#: is ``operator_decision_required``; a row listed in both tables is confirmed
#: on its disposition and still carries the deferral.
#: The approval's deferral table, one entry per cell. Several cells name more
#: than one observation, and the operator wrote one disposition for the whole
#: cell: the text is transcribed verbatim onto each row of its group, and the
#: row says which group it shares, so an instruction addressed to one
#: observation is not read as addressed to its neighbour.
DEFERRED_CELLS: tuple[Mapping[str, Any], ...] = (
    {
        "observation_ids": ("ESR-E-02", "ESR-E-04", "ESR-E-08"),
        "required_private_evidence": (
            "Original security, hospital/operator diversity and entrepreneurship mechanisms; "
            "compare relevant passages with sanitised text."
        ),
        "disposition": (
            "Preservation is unconfirmed. Withdraw E-04's cohort-size citation now; do not "
            "settle miss versus not-assessable from an absence in this copy."
        ),
    },
    {
        "observation_ids": ("ESR-E-05",),
        "required_private_evidence": "Original registry/database and contributing-clinician passages.",
        "disposition": "Keep not-assessable pending evidence.",
    },
    {
        "observation_ids": ("ESR-E-S03", "ESR-E-S05"),
        "required_private_evidence": (
            "Original repository/preprint commitments, supervisor mapping and track-record evidence."
        ),
        "disposition": "Do not adopt blind criticisms as established proposal weaknesses.",
    },
    {
        "observation_ids": ("ESR-I-S01",),
        "required_private_evidence": (
            "Original secondment rows, host-sector classifications and the denominator for the "
            "80% claim."
        ),
        "disposition": (
            "Recompute privately before approving a correction. Identify the actual source "
            "subsection; do not guess one."
        ),
    },
    {
        "observation_ids": ("ESR-I-S04",),
        "required_private_evidence": "Original target-group/indicator tables, figures and prose.",
        "disposition": "Do not attribute the disagreement to sanitisation as a confirmed cause.",
    },
    {
        "observation_ids": ("ESR-Q-01",),
        "required_private_evidence": "Original dependencies, Gantt and sequencing evidence.",
        "disposition": (
            "Keep partial classification qualified; absence of embedded images alone does not "
            "establish that every figure was lost."
        ),
    },
    {
        "observation_ids": ("ESR-Q-S02", "ESR-Q-S03"),
        "required_private_evidence": "Original capacity and hosting evidence.",
        "disposition": (
            "Correct identity references now; original-dependent adequacy remains unresolved."
        ),
    },
    {
        "observation_ids": ("ESR-Q-03",),
        "required_private_evidence": (
            "Actual project duration, WP scope, funding/activity windows and follow-up intent."
        ),
        "disposition": "No date or participation changes approved.",
    },
)


def _deferred_rows() -> dict[str, dict[str, str]]:
    """One entry per deferred observation, each naming the cell it shares."""
    rows: dict[str, dict[str, str]] = {}
    for cell in DEFERRED_CELLS:
        ids = tuple(cell["observation_ids"])
        shared = ""
        if len(ids) > 1:
            shared = (
                " This cell of the approval's deferral table covers "
                + ", ".join(ids)
                + ", and its text is the cell's, not one row's alone."
            )
        for oid in ids:
            rows[oid] = {
                "required_private_evidence": str(cell["required_private_evidence"]),
                "disposition": str(cell["disposition"]),
                "shared_cell": shared,
            }
    return rows


#: The deferred rows, keyed by observation id.
DEFERRED: Mapping[str, Mapping[str, str]] = _deferred_rows()

#: The failure mode of every miss (D03), each with the adjudication or review
#: note it is drawn from. ``absent_from_recorded_output`` describes the recorded
#: baseline and nothing more (D02).
FAILURE_MODES: Mapping[str, Mapping[str, str]] = {
    "ESR-E-02": {
        "failure_mode": "absent_from_recorded_output",
        "failure_mode_basis": (
            "R03 review note ESR-E-02: no blind sample, cell rationale or audit check names "
            "security of clinical data. This describes the recorded output; it does not "
            "establish that the passage was not read."
        ),
    },
    "ESR-E-03": {
        "failure_mode": "absent_from_recorded_output",
        "failure_mode_basis": (
            "Adjudication A07 measured zero occurrences of 'prospective', 'shadow' or "
            "'retrospective' in the 15 criterion samples and 10 cells of the frozen baseline. "
            "Per D02 that is an absence from the recorded output, not evidence that the "
            "model did not read the passage; A07's own 'evidence_not_read' label is "
            "superseded by this description."
        ),
    },
    "ESR-E-04": {
        "failure_mode": "absent_from_recorded_output",
        "failure_mode_basis": (
            "Adjudication A06: no sample and no cell names a site count, an operator count or "
            "representativeness. Whether the row is a miss at all is deferred to the private "
            "network; the mode describes the recorded output only."
        ),
    },
    "ESR-E-07": {
        "failure_mode": "read_and_rated_adequate",
        "failure_mode_basis": (
            "Adjudication A08: the exc-training cell passed 3 of 3, its members stating that "
            "the complementarity of network-wide and local programmes is explicitly stated. "
            "An adequacy disagreement, counted as a miss per D03."
        ),
    },
    "ESR-E-08": {
        "failure_mode": "absent_from_recorded_output",
        "failure_mode_basis": (
            "R03 review note ESR-E-08: no blind sample and no cell rationale names "
            "entrepreneurship. This describes the recorded output only."
        ),
    },
    "ESR-E-09": {
        "failure_mode": "read_and_rated_adequate",
        "failure_mode_basis": (
            "Adjudication A09: the exc-supervision cell passed 2 of 3, its members listing "
            "annual progress reports and feedback questionnaires among the structure they "
            "rate adequate. An adequacy disagreement, counted as a miss per D03."
        ),
    },
    "ESR-Q-02": {
        "failure_mode": "read_and_misattributed",
        "failure_mode_basis": (
            "Adjudication A10: four of five implementation samples credit the deliverables "
            "table with the milestones table's verification column. Recorded as assessor "
            "validation case AVC-02 per D05."
        ),
    },
}

#: The assessor validation cases the approval records for PE-09 (D04, D05).
ASSESSOR_VALIDATION_CASES: Sequence[Mapping[str, Any]] = (
    {
        "id": "AVC-01",
        "decision_id": "D04",
        "observation_ids": ["ESR-Q-01", "ESR-Q-03"],
        "adjudication_ids": ["A05", "A11"],
        "case": (
            "One implementation sample stated that no intermediate milestones are shown. The "
            "input that assessor received carries the milestones table with a due month for "
            "each of sixteen milestones over ten distinct months. The citation is withdrawn "
            "from both rows and kept as a case for the PE-09 assessor validation."
        ),
        "limit": DECISIONS["D04"]["limit"],
    },
    {
        "id": "AVC-02",
        "decision_id": "D05",
        "observation_ids": ["ESR-Q-02"],
        "adjudication_ids": ["A10"],
        "case": (
            "Four of five implementation samples attribute verification means to the "
            "deliverables and milestones tables jointly, while only the milestones table "
            "carries that column. The lane credited one table with the other's property."
        ),
        "limit": DECISIONS["D05"]["limit"],
    },
)

_AUDIT_CITATION = {
    "report": SUCCESSOR_AUDIT_REL.as_posix(),
    "check": "milestone_dependencies",
    "index": 0,
}

MISSES = tuple(FAILURE_MODES)


# --------------------------------------------------------------------------- #
# Row changes
# --------------------------------------------------------------------------- #

_Q03_EXPLANATION = (
    "One finding carries this row, and it carries the timing half of the ESR sentence only: "
    "M7.3 is due M48 and its related WP7 runs M1-M36, an out-of-window finding of the "
    "integrity audit. The operator replaced full detection with provisional partial "
    "detection (D06): the integrity audit is the only contributing lane, the definitions "
    "half is detected by no finding, and what the timing gap means stays Unresolved. The "
    "citation is re-filed against the audit written after D11 retired the "
    "undeclared-dependency findings, where the same M7.3 finding is the check's first; the "
    "audit the predecessor cited stays on disk. The register entry named is the derived "
    "measurement of 3.1, the sub-section that carries the milestones table. Whether M7.3 "
    "moves, is relocated out of the table, or keeps its date with an adequate explanation is "
    "deferred until duration, WP scope and the intended follow-up timing are verified "
    "privately (D12); if that context removes the conflict, the detection credit is to be "
    "revisited."
)

_E03_QUALIFICATION = (
    " The operator accepted non-detection of the criticism in the recorded output (D02). "
    "That acceptance describes the recorded output: no lane output engages the evaluation "
    "design either way. It does not establish that the model did not read the evidence, and "
    "the preservation of the evidence remains separately qualified as Assumed."
)

_Q01_QUALIFICATION = (
    " The withdrawal of the contradicted citation is confirmed and kept as assessor "
    "validation case AVC-01 (D04). The partial classification is retained qualified: the "
    "register's zero-image measurement does not by itself establish that every figure was "
    "lost, so whether the submission carried a Gantt or dependency figure is deferred to the "
    "private network."
)

_Q02_QUALIFICATION = (
    " The conflation of the two tables is recorded as assessor validation case AVC-02 (D05). "
    "A missing validation column does not prove inadequate deliverable validation: the "
    "relevant prose and the original-dependent evidence are to be reviewed before the "
    "proposal judgment is finalised."
)

_QS02_QUALIFICATION = (
    " Under schema 1.2 the register pointer derived/sub_sections/8/characters resolves by "
    "identity to sub-section 8 itself (V02); under the earlier rule it resolved to the ninth "
    "list element, sub-section 3.1, so the character count the earlier review quoted for "
    "section 8 was 3.1's."
)

_QS03_QUALIFICATION = (
    " Under schema 1.2 the register pointer derived/sub_sections/5/characters resolves by "
    "identity to sub-section 5 itself (V02); under the earlier rule it resolved to the sixth "
    "list element, sub-section 2.2, so the character count the earlier review quoted for "
    "section 5 was 2.2's."
)

_I_S02_REVISION: Mapping[str, Any] = {
    "text": (
        "Optional, beyond the ESR: if the submitted original states the post-project funding "
        "plan as the sanitised copy does (a list of programme names), name for each sustained "
        "element the mechanism that carries it after the funded period and who owns it. The "
        "ESR praised this aspect; the improvement answers two blind findings, not the "
        "evaluators, and is written only if the original check warrants it."
    ),
    "declared_status": "Assumed",
    "scope": "beyond_esr",
    "label": "post_project_sustainability_funding",
    "revision_plan": {
        "evidence": [
            "the two contesting blind impact shortcomings cited on this row, resolved against the frozen baseline",
            "ESR-I-S02, page 3, Criterion 2 comment: the praised strength this improvement must preserve",
            "operator decision D07 of the approval record",
        ],
        "responsible_role": dict(ROLES["innovation_committee"]),
        "requires_confirmation": [
            "that the submitted original's post-project funding passage is the one the sanitised copy carries (PE-09)",
            "whether a mechanism per sustained element can be named without a new commitment",
        ],
        "proposal_location": ["impact_section/2.1, the post-project sustainability block"],
        "commitment_kind": "requires_original_check",
        "approved_limit": DECISIONS["D07"]["limit"],
    },
}

_I_02_SUBTASK: Mapping[str, Any] = {
    "label": "societal_impact_indicators",
    "scope": "beyond_esr",
    "approved_by": "D08",
    "commitment_kind": "requires_study_design",
    "text": (
        "Separately from the economic and technological magnitude the ESR asks for, state "
        "how the societal pathway (patient benefit, health-system resilience, policy uptake) "
        "would be evidenced. No indicator, numerical target or clinical outcome is proposed "
        "here; the responsible body names candidates for confirmation."
    ),
    "requires_confirmation": [
        "which societal indicators the consortium can evidence without a promised clinical outcome",
        "that the societal subtask stays distinct from the economic and technological magnitude ESR-I-02 asks for",
    ],
    "approved_limit": DECISIONS["D08"]["limit"],
}


def _review_status(oid: str) -> str:
    if oid in CONFIRMED:
        return STATUS_CONFIRMED
    if oid in DEFERRED:
        return STATUS_REQUIRED
    return STATUS_AGENT


def _apply_row_changes(row: dict[str, Any], esr_kind: str) -> dict[str, Any]:
    """Apply this row's enumerated changes; carry everything else through."""
    oid = row["observation_id"]
    row["review_status"] = _review_status(oid)
    if oid in CONFIRMED:
        row["operator_decision_ids"] = list(CONFIRMED[oid])
    if oid in DEFERRED:
        d = DEFERRED[oid]
        row["deferred_to_private_network"] = (
            f"{d['required_private_evidence']} Disposition under this approval: "
            f"{d['disposition']}{d['shared_cell']}"
        )
    if oid == "ESR-Q-03":
        row["disposition"] = "partially_observable"
        row["declared_status"] = "Inferred"
        row["audit_findings"] = [dict(_AUDIT_CITATION)]
        row["evidence_basis"] = ["derived/sub_sections/3.1"]
        row["explanation"] = _Q03_EXPLANATION
        plan = row["proposed_revision"]["revision_plan"]
        plan["requires_confirmation"] = [
            "the actual project duration, the WP7 scope and the intended timing of the follow-up proposal (D12)",
            "whether M7.3 moves inside the window, is relocated out of the milestones table, or keeps M48 with an adequate explanation; the three are not exhaustive",
            "whether any milestone should name a deliverable it depends on, as drafting advice only (D11); no link is assumed",
            "the evaluation endpoint M4.2 is defined against",
        ]
        plan["approved_limit"] = DECISIONS["D12"]["limit"]
    elif oid == "ESR-E-03":
        row["explanation"] = row["explanation"] + _E03_QUALIFICATION
    elif oid == "ESR-Q-01":
        row["explanation"] = row["explanation"] + _Q01_QUALIFICATION
    elif oid == "ESR-Q-02":
        row["explanation"] = row["explanation"] + _Q02_QUALIFICATION
        plan = row["proposed_revision"]["revision_plan"]
        plan["requires_confirmation"] = list(plan["requires_confirmation"]) + [
            "a review of the relevant prose and the original-dependent evidence before the proposal judgment is finalised (D05)",
        ]
    elif oid == "ESR-Q-S02":
        row["explanation"] = row["explanation"] + _QS02_QUALIFICATION
    elif oid == "ESR-Q-S03":
        row["explanation"] = row["explanation"] + _QS03_QUALIFICATION
    elif oid == "ESR-I-S02":
        row["proposed_revision"] = copy.deepcopy(dict(_I_S02_REVISION))
    elif oid == "ESR-I-02":
        plan = row["proposed_revision"]["revision_plan"]
        plan["subtasks"] = [copy.deepcopy(dict(_I_02_SUBTASK))]
    if row["disposition"] == "not_detected_despite_sufficient_preserved_evidence":
        mode = FAILURE_MODES.get(oid)
        if mode is None:
            raise SuccessorError(f"{oid} is a miss under schema {SCHEMA_VERSION} and no failure mode is enumerated for it.")
        row.update(mode)
    if esr_kind == "strength" and oid != "ESR-I-S02" and "proposed_revision" in row:
        raise SuccessorError(
            f"{oid} is a strength and carries a proposed revision. Only ESR-I-S02 may, "
            "under operator decision D07, and its scope must be 'beyond_esr'."
        )
    return row


# --------------------------------------------------------------------------- #
# The dispositions record
# --------------------------------------------------------------------------- #


def render(repo_root: Path) -> dict[str, Any]:
    predecessor = _read_json(repo_root, PREDECESSOR_REL)
    esr = _read_json(repo_root, ESR_RECORD_REL)
    kinds = {str(o["id"]): str(o["kind"]) for o in esr["observations"]}
    if not (repo_root / APPROVAL_REL).is_file():
        raise SuccessorError(f"{APPROVAL_REL.as_posix()} is absent; nothing to transcribe.")
    rows = [
        _apply_row_changes(copy.deepcopy(row), kinds[str(row["observation_id"])])
        for row in predecessor["rows"]
    ]
    unknown = sorted((set(CONFIRMED) | set(DEFERRED) | set(FAILURE_MODES)) - set(kinds))
    if unknown:
        raise SuccessorError(f"the approval names unknown observation(s): {', '.join(unknown)}.")
    by_status = {
        status: sorted(r["observation_id"] for r in rows if r["review_status"] == status)
        for status in (STATUS_CONFIRMED, STATUS_REQUIRED, STATUS_AGENT)
    }
    return {
        "record_type": "esr_dispositions",
        "schema_version": SCHEMA_VERSION,
        "artifact_purpose": (
            "The declared half of the PE-08 comparison as the operator approved it on "
            "2026-10-08. One disposition per observation of the same ESR record, over the same "
            "frozen baseline and the same candidate as the R05 record it supersedes, with the "
            "approved decisions D01-D08, D11 and D12 applied, the deferred rows marked, every "
            "miss carrying its failure mode, and register pointers resolved by identity. The "
            "R05 record and its comparison stay on disk and stay replayable."
        ),
        "spec": "plans/msca_dn_pre_evaluation_spec.md",
        "ticket": (
            "PE-08 operator approval and PE-09 handover decisions, "
            + APPROVAL_REL.as_posix()
            + ", after R05 of plans/pe08_review_and_pe09_handoff_tickets.md"
        ),
        "advisory": True,
        "blocking": False,
        "review_state": REVIEW_STATE,
        "operator_approval": {
            "record": APPROVAL_REL.as_posix(),
            "sha256": _sha256(repo_root, APPROVAL_REL),
            "approved_at": APPROVED_AT,
            "instruction": APPROVAL_INSTRUCTION,
            "scope": (
                "The approval approves review policies, preparation of optional improvements, "
                "explicit deferrals and required validation corrections. It does not certify "
                "new tests, approve every draft row as fact, adopt declarations into active "
                "registers, or authorise a new assessor run. Operator approval is an authority "
                "fact; Confirmed, Inferred, Assumed and Unresolved describe evidence status, and "
                "no row's status is raised by the approval."
            ),
            "decisions_applied": sorted({d for ids in CONFIRMED.values() for d in ids} | {"D11"}),
            "decisions_transcribed": {k: dict(v) for k, v in DECISIONS.items()},
        },
        "review_status_note": (
            "operator_confirmed: a decision of the approval record settles the row's "
            "disposition, and operator_decision_ids names it. operator_decision_required: the "
            "approval defers the row to the private network, and deferred_to_private_network "
            "states what has to be established there. agent_recommended_pending_operator_review: "
            "the approval says nothing about the row; its provenance and uncertainty are carried "
            "forward, and it is not blanket-confirmed. A row may be confirmed on its disposition "
            "and still carry a deferral."
        ),
        "written_by": "tools/author_approved_dispositions.py",
        "supersedes": PREDECESSOR_REL.as_posix(),
        "supersedes_sha256": _sha256(repo_root, PREDECESSOR_REL),
        "supersession_note": (
            "The R05 record stays as written and the comparison rendered from it stays as the "
            "operator reviewed it. This record is what the approval decided over it, and a "
            "later correction is a successor of this one."
        ),
        "baseline_report_sha256": str(predecessor["baseline_report_sha256"]),
        "baseline_dir": str(predecessor["baseline_dir"]),
        "esr_record": ESR_RECORD_REL.as_posix(),
        "esr_record_sha256": _sha256(repo_root, ESR_RECORD_REL),
        "candidate": str(predecessor["candidate"]),
        "historical_candidate": str(predecessor["historical_candidate"]),
        "fidelity_register": REGISTER_REL.as_posix(),
        "fidelity_register_sha256": _sha256(repo_root, REGISTER_REL),
        "fidelity_register_note": (
            "The same register, byte for byte, as the R05 record and the PE-08 record cite. "
            "Adoption of the R04 declaration drafts is deferred (D13), so the declared half is "
            "still empty. Under validation correction V01 a Confirmed evidence_preserved_status "
            "needs the declared half's fidelity_to_submitted_original claim, Confirmed in the "
            "scope fidelity_against_the_submitted_original with evidence naming the row; a "
            "presence declaration alone no longer carries it. Every miss here declares Assumed "
            "or Unresolved, and the seven preservation-qualified misses remain provisional. "
            "The body-point-size qualification (D14) is prepared in "
            + DECLARATION_DRAFT_REL.as_posix()
            + " and is not applied here, because applying it changes the register's bytes and "
            "every binding on them."
        ),
        "pointer_resolution_note": (
            "Schema 1.2: a bare segment of a register pointer into a keyed list names a "
            "sub-section id, never a position (V02). derived/sub_sections/8/characters and "
            "derived/sub_sections/5/characters on ESR-Q-S02 and ESR-Q-S03 therefore resolve to "
            "sub-sections 8 and 5; under the predecessor's schema they resolved to the ninth "
            "and sixth list elements (3.1 and 2.2), and the review notes' character counts for "
            "those sections were those sub-sections'. The predecessor comparison keeps its "
            "recorded values under the documented legacy rule."
        ),
        "audits": [SUCCESSOR_AUDIT_REL.as_posix(), FIRST_REVISION_AUDIT_REL.as_posix()],
        "audit_note": (
            "ESR-Q-03's one citation is filed against "
            + SUCCESSOR_AUDIT_REL.as_posix()
            + ", written after D11 retired the undeclared-dependency findings: the "
            "milestone_dependencies check now lists the sixteen milestones that name no "
            "deliverable in its context as drafting advice and reports one finding, the M7.3 "
            "out-of-window, at index 0. "
            + PREDECESSOR_AUDIT_REL.as_posix()
            + " carried the same finding at index 15 and stays on disk. The first-revision "
            "audit is passed for the historical copy."
        ),
        "review_inputs": {
            "approval_record": APPROVAL_REL.as_posix(),
            "approval_record_sha256": _sha256(repo_root, APPROVAL_REL),
            "predecessor_comparison": PREDECESSOR_COMPARISON_REL.as_posix(),
            "predecessor_comparison_sha256": _sha256(repo_root, PREDECESSOR_COMPARISON_REL),
            "review_notes": NOTES_PREDECESSOR_REL.as_posix(),
            "review_notes_sha256": _sha256(repo_root, NOTES_PREDECESSOR_REL),
            "adjudication_record": ADJUDICATIONS_REL.as_posix(),
            "adjudication_record_sha256": _sha256(repo_root, ADJUDICATIONS_REL),
            "declaration_draft": DECLARATION_DRAFT_REL.as_posix(),
            "declaration_draft_note": (
                "cited by path and not by hash, for the reason the R05 record gives: the "
                "draft enumerates every artifact that names the register, this record "
                "included."
            ),
        },
        "declared_by": (
            "transcribed in a Claude Code session, 2026-10-08, from the operator approval "
            "record over the R05 dispositions. The decisions are the operator's; every other "
            "declaration is the agent's and is marked as such on its row"
        ),
        "declared_on": DECLARED_ON,
        "declared_status_note": (
            "declared_status is the status of the disposition judgment itself (CLAUDE.md "
            "section 12.2). ESR-Q-03 moves from Unresolved to Inferred because the approval "
            "settled which disposition the one finding carries; what the timing gap means "
            "stays Unresolved in the deferral. ESR-E-04 stays Unresolved on both statuses "
            "because the approval deferred the miss-versus-not-assessable choice. No status is "
            "raised to Confirmed by the approval."
        ),
        "decision_state": {
            "state": REVIEW_STATE,
            "statement": (
                "The operator approved the decision package on 2026-10-08. "
                f"{len(by_status[STATUS_CONFIRMED])} rows are confirmed on their disposition, "
                f"{len(by_status[STATUS_REQUIRED])} are deferred to the private network, and "
                f"the remaining {len(by_status[STATUS_AGENT])} carry an agent's declaration the "
                "approval did not address. "
                + ", ".join(sorted(set(CONFIRMED) & set(DEFERRED)))
                + " are confirmed on their disposition and also carry a deferral: the "
                "disposition is settled and an original-dependent question stays open."
            ),
            "rows_operator_confirmed": by_status[STATUS_CONFIRMED],
            "rows_operator_decision_required": by_status[STATUS_REQUIRED],
            "rows_agent_recommended": by_status[STATUS_AGENT],
            "rows_whose_declarations_changed": ["ESR-Q-03"],
            "rows_whose_explanation_was_qualified": [
                "ESR-E-03", "ESR-Q-01", "ESR-Q-02", "ESR-Q-S02", "ESR-Q-S03",
            ],
            "rows_whose_revision_changed": ["ESR-I-02", "ESR-I-S02", "ESR-Q-02", "ESR-Q-03"],
            "preservation_provisional_rows": sorted(MISSES),
            "preservation_note": (
                "The seven preservation-qualified misses remain provisional unless supported in "
                "the required claim scope (V01). They are not upgraded by any extraction-only "
                "declaration, and the counts the comparison recomputes from these rows carry "
                "that qualification."
            ),
        },
        "assessor_validation_cases": [dict(c) for c in ASSESSOR_VALIDATION_CASES],
        "open_operator_decisions": [
            {
                "observation_id": oid,
                "required_private_evidence": d["required_private_evidence"],
                "current_review_disposition": d["disposition"],
                "declared_pending": True,
            }
            for oid, d in DEFERRED.items()
        ],
        "failure_mode_note": (
            "Every miss declares a failure_mode and its basis (D03). The comparison reports "
            "the breakdown beside the detection figures and never folds it into them. "
            "absent_from_recorded_output replaces the adjudication record's evidence_not_read "
            "on ESR-E-03 (D02): it describes the recorded output and does not claim the model "
            "did not read the evidence."
        ),
        "shared_sentence_note": (
            "ESR-E-01 and ESR-E-02 are clause-level observations of one ESR sentence (D01). "
            "The comparison reports the shared sentence and its cluster beside the rows; the "
            "two are not presented as separate evaluator sentences, independent deductions or "
            "a cluster-level detection."
        ),
        "revision_plan_note": (
            "Every plan the R05 record carried stands. ESR-Q-03's confirmation list follows "
            "D12 and D11; ESR-Q-02's adds the prose review D05 requires. ESR-I-S02 carries an "
            "optional improvement beyond the ESR (D07) and ESR-I-02's plan a separately "
            "labelled societal-impact subtask (D08); both are listed apart in the revisions "
            "artifact as beyond-ESR work, and neither proposes an indicator, a target, a "
            "funding source, a maintenance duty or a partner commitment. All fifteen ESR "
            "shortcomings remain open revision-review items."
        ),
        "addressed_rows": str(predecessor["addressed_rows"]),
        "rows": rows,
    }


# --------------------------------------------------------------------------- #
# The successor review notes
# --------------------------------------------------------------------------- #

#: Observation id -> the corrected uncertainty text, where the R03 note quoted a
#: character count that the legacy pointer rule had resolved to another
#: sub-section (V02). The counts are read from the register at render time.
_UNCERTAINTY_TEMPLATES: Mapping[str, str] = {
    "ESR-Q-S02": (
        "The register records identifiers generalised, and section 8 reaches this copy as "
        "unnamed 'Academic Beneficiary A-I' profiles across {chars:,} characters in "
        "{paras} paragraphs (derived/sub_sections/8, resolved by identity; the earlier note's "
        "28,087 was sub-section 3.1's count under the positional rule). Prior grants, named "
        "facilities and publication records are what that generalisation removes."
    ),
    "ESR-Q-S03": (
        "Section 5, the network organisation, reaches this copy as {chars:,} characters in "
        "{paras} paragraphs with identifiers generalised (derived/sub_sections/5, resolved by "
        "identity; the earlier note's 3,135 was sub-section 2.2's count under the positional "
        "rule). Per-institution hosting detail the evaluators may have read there does not "
        "reach this copy, and the contest cannot be reconciled with the praise from what "
        "remains."
    ),
}


#: The sub-section each corrected note measures.
_UNCERTAINTY_SUB_SECTION: Mapping[str, str] = {"ESR-Q-S02": "8", "ESR-Q-S03": "5"}


def _sub_section_measure(repo_root: Path, sub: str) -> Mapping[str, Any]:
    register = _read_json(repo_root, REGISTER_REL)
    for entry in register["derived"]["sub_sections"]:
        if str(entry.get("sub_section_id")) == sub:
            return entry
    raise SuccessorError(f"the register's derived half lists no sub-section {sub}.")


def successor_comparison(repo_root: Path) -> Optional[Path]:
    """The comparison written from the successor dispositions, if one exists."""
    target = repo_root / SUCCESSOR_REL
    if not target.is_file():
        return None
    sha = file_sha256(target)
    for path in sorted((repo_root / COMPARISON_DIR).glob("comparison_*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            continue
        block = data.get("dispositions") or {}
        if block.get("path") == SUCCESSOR_REL.as_posix() and block.get("sha256") == sha:
            return path
    return None


def _decision_text(ids: Sequence[str]) -> str:
    return " ".join(f"{d}: {DECISIONS[d]['decision']} Limit retained: {DECISIONS[d]['limit']}" for d in ids)


def render_notes(repo_root: Path, comparison: Path) -> dict[str, Any]:
    predecessor = _read_json(repo_root, NOTES_PREDECESSOR_REL)
    approval_sha = _sha256(repo_root, APPROVAL_REL)
    rows: list[dict[str, Any]] = []
    for row in predecessor["rows"]:
        row = copy.deepcopy(row)
        oid = str(row["observation_id"])
        if oid in CONFIRMED:
            row["decision_recorded"] = {
                "decision_id": ", ".join(CONFIRMED[oid]),
                "record": APPROVAL_REL.as_posix(),
                "text": _decision_text(CONFIRMED[oid]),
            }
            row.pop("operator_decision", None)
        if oid in DEFERRED:
            d = DEFERRED[oid]
            row["operator_decision"] = (
                f"Deferred to the private network by the approval record. Required private "
                f"evidence: {d['required_private_evidence']} Current review disposition: "
                f"{d['disposition']}{d['shared_cell']}"
            )
        if oid == "ESR-Q-03":
            row["recommended_disposition"] = "partially_observable"
            row["recommendation"] = "adjudicated"
        if oid == "ESR-E-03":
            row["uncertainty"] = (
                "None remains on whether a lane output engages the evaluation design: none "
                "does, in any sample or cell. That describes the recorded output; per D02 it "
                "does not establish that the model did not read the evidence, and the "
                "preservation of the passage stays separately qualified as Assumed."
            )
        if oid in _UNCERTAINTY_TEMPLATES:
            measure = _sub_section_measure(repo_root, _UNCERTAINTY_SUB_SECTION[oid])
            row["uncertainty"] = _UNCERTAINTY_TEMPLATES[oid].format(
                chars=int(measure["characters"]), paras=int(measure["paragraphs"])
            )
        rows.append(row)
    return {
        "record_type": "esr_review_notes",
        "schema_version": "1.0",
        "advisory": True,
        "blocking": False,
        "artifact_purpose": (
            "The declared half of the operator review over the approved comparison: the R03 "
            "notes with the operator's recorded decisions transcribed under their ids, the "
            "deferred questions restated as the approval record states them, and the two "
            "character counts the legacy pointer rule had misattributed corrected. Resolution "
            "of a reference is measured by harness/operator_review.py; agreement is judged "
            "here, and remains the agent's."
        ),
        "spec": "plans/msca_dn_pre_evaluation_spec.md",
        "ticket": "PE-08 operator approval, " + APPROVAL_REL.as_posix(),
        "comparison": comparison.relative_to(repo_root).as_posix(),
        "comparison_sha256": file_sha256(comparison),
        "declared_by": (
            "transcribed in a Claude Code session, 2026-10-08: the R03 rows unchanged except "
            "where a recorded decision replaces an open question, a deferral restates one, "
            "ESR-Q-03 follows D06, ESR-E-03's uncertainty follows D02, and ESR-Q-S02 and "
            "ESR-Q-S03 carry identity-resolved counts. Every agreement judgment is still the "
            "agent's; only the recorded decisions are the operator's"
        ),
        "declared_on": DECLARED_ON,
        "review_state": "agent_drafted_pending_operator_review",
        "operator_approval": {"record": APPROVAL_REL.as_posix(), "sha256": approval_sha},
        "declared_status_note": str(predecessor.get("declared_status_note") or ""),
        "vocabulary_note": (
            str(predecessor.get("vocabulary_note") or "")
            + " A row may carry decision_recorded instead of, or beside, operator_decision: "
            "a decision transcribed from the approval record under its id, with the limit "
            "the record retains. The notes' review_state stays agent-drafted, because the "
            "judgments are; the decisions are the operator's and each names its record."
        ),
        "adjudication_record": ADJUDICATIONS_REL.as_posix(),
        "supersedes": NOTES_PREDECESSOR_REL.as_posix(),
        "supersession_note": (
            "The R03 record stays as written and the reports rendered from it stay as "
            f"written. This file is the reading of the approved comparison: {len(CONFIRMED)} "
            f"rows carry a recorded decision, {len(DEFERRED)} carry the question the approval "
            "deferred, and the rest are the R03 rows unchanged."
        ),
        "rows": rows,
    }


# --------------------------------------------------------------------------- #
# Rendering, checking, writing
# --------------------------------------------------------------------------- #


def render_all(repo_root: Path) -> dict[str, bytes]:
    out = {SUCCESSOR_REL.as_posix(): canonical_json_bytes(render(repo_root))}
    comparison = successor_comparison(repo_root)
    if comparison is not None:
        out[NOTES_SUCCESSOR_REL.as_posix()] = canonical_json_bytes(render_notes(repo_root, comparison))
    return out


def check(repo_root: Path) -> list[str]:
    """Relative paths whose bytes differ from the rendering, or are absent."""
    rendered = render_all(repo_root)
    stale = [
        rel for rel, data in rendered.items()
        if not (repo_root / rel).is_file() or (repo_root / rel).read_bytes() != data
    ]
    notes = NOTES_SUCCESSOR_REL.as_posix()
    if notes not in rendered and (repo_root / notes).is_file():
        # Notes exist but no comparison is bound to the current dispositions:
        # they were rendered over another comparison and are stale.
        stale.append(notes)
    return stale


def write(repo_root: Path) -> list[str]:
    changed: list[str] = []
    for rel, data in render_all(repo_root).items():
        target = repo_root / rel
        if target.is_file() and target.read_bytes() == data:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(data.decode("utf-8"), target)
        changed.append(rel)
    return changed


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--check", action="store_true", help="exit 1 if any output would change")
    parser.add_argument("--repo-root", type=Path, default=None)
    args = parser.parse_args(argv)
    repo_root = args.repo_root or find_repo_root()
    try:
        if args.check:
            stale = check(repo_root)
            for rel in stale:
                print(f"would change: {rel}")
            print("up to date" if not stale else f"{len(stale)} file(s) would change")
            return 1 if stale else 0
        changed = write(repo_root)
        for rel in changed:
            print(f"wrote: {rel}")
        if successor_comparison(repo_root) is None:
            print(
                "notes not rendered: no comparison is bound to the successor dispositions yet; "
                "run the compare command, then this tool again"
            )
        print("no change" if not changed else f"{len(changed)} file(s) written")
        return 0
    except SuccessorError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
