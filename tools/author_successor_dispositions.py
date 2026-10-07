"""R05 — the successor ESR dispositions, drafted for operator review.

PE-08 wrote one dispositions record and one comparison. R02 rendered them for a
human, R03 adjudicated the seven rows that review disputed, and R04 drafted what
the fidelity register's declared half could say. None of that changed a
disposition: an adjudication is a reading, and a recommended change is a
question. R05 is where the reading is written down as a *successor* record, so
the operator reads one artifact instead of three.

What this module is
-------------------
A deterministic, Claude-free transform. It reads the committed predecessor
dispositions and applies a fixed, enumerated set of changes: the citations R03
withdrew, the one disposition R03 recommends moving, and one revision plan per
ESR shortcoming. Every other row is carried through byte for byte, so the diff
between the two records shows what the review moved and nothing else.

Nothing here is measured. The predecessor's references were resolved by
``harness.esr_comparison`` when PE-08 was written and are resolved again when
the successor is compared; this module only decides what the successor
*declares*. Every declaration it writes is an agent recommendation pending
operator review, and :data:`REVIEW_STATE` says so in the record.

The three rows the review moves
-------------------------------
``ESR-E-04``
    A06 found the one cited blind shortcoming to be about cohort *magnitude*
    (sample size, power) where the ESR is about cohort *composition* (hospitals,
    operators, representativeness). Two different properties, so the citation is
    withdrawn and ``partially_observable`` loses the finding it requires. The
    R03 note recommends ``not_detected_despite_sufficient_preserved_evidence``;
    the alternative, ``not_assessable_from_this_copy``, turns on whether the
    register's record of rephrased prose means the submission may have carried
    the counts. That choice is the operator's, so both statuses on the row are
    ``Unresolved`` and the question is listed under
    :data:`OPEN_OPERATOR_DECISIONS`.

``ESR-Q-01``
    A05 found one of the three cited blind shortcomings contradicted by the
    input that assessor received: it says no intermediate milestones are shown,
    and the section it read carries the milestones table with ten distinct due
    months. The citation is withdrawn. The dependency point stands on the other
    two, so the disposition does not move.

``ESR-Q-03``
    A05 withdraws its blind citation and A03 withdraws its two
    ``undeclared_dependency`` citations, which rest on no sourced requirement —
    a dependency is not a column of the milestones table. What remains is the
    M7.3 window finding, re-cited against the *successor* audit, whose
    ``milestone_dependencies`` findings are index-for-index those of the audit
    the predecessor cited. So the row stays ``independently_detected`` by the
    integrity audit alone, and whether the definitions half of the ESR sentence
    leaves it partial is the operator's decision.

The revision plans
------------------
Ticket R05 item 6: a proposed revision must name its evidence, the human role
that owns it, what has to be confirmed, where in the proposal it goes, and
whether carrying it out commits anyone to anything new. Every role is quoted
from the candidate's own governance and work-package text (:data:`ROLES`);
inventing a role would be inventing a project fact (CLAUDE.md §13.3). No plan
is ``editorial_change``: not one of the fifteen can be written from what the
copy already carries.

Determinism
-----------
Every hash in the record is computed from the file on disk at render time, so a
moved input is caught by ``--check`` rather than carried as a stale binding.
``--check`` is a byte-equal replay and writes nothing.

Usage::

    py -3.10 -m tools.author_successor_dispositions          # write
    py -3.10 -m tools.author_successor_dispositions --check   # byte-equal replay
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
from tools.fidelity_declarations import file_sha256

ESR_DIR = Path("docs/tier4_orchestration_state/msca_dn/esr")
AUDIT_DIR = Path("docs/tier4_orchestration_state/msca_dn/audit")
COMPARISON_DIR = Path("docs/tier4_orchestration_state/msca_dn/comparisons")
REVIEW_DIR = Path("docs/tier4_orchestration_state/msca_dn/reviews")
DECLARATIONS_DIR = Path("docs/tier4_orchestration_state/msca_dn/declarations")

PREDECESSOR_REL = ESR_DIR / "dispositions_f60ae6e0a2a1.json"
SUCCESSOR_REL = ESR_DIR / "dispositions_f60ae6e0a2a1_r05.json"
ESR_RECORD_REL = ESR_DIR / "msca-dn-2025-esr.json"
REVIEW_NOTES_REL = ESR_DIR / "review_notes_f60ae6e0a2a1_r03.json"
ADJUDICATIONS_REL = ESR_DIR / "semantic_adjudications_f60ae6e0a2a1.json"
PREDECESSOR_COMPARISON_REL = COMPARISON_DIR / "comparison_f60ae6e0a2a1_0001.json"
OPERATOR_REVIEW_REL = REVIEW_DIR / "operator_review_9732dde50039_0002.md"
REGISTER_REL = Path(
    "docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register_resolved_fixes.json"
)
SUCCESSOR_AUDIT_REL = AUDIT_DIR / "integrity_242f1afb02c8_0002.json"
CITED_AUDIT_REL = AUDIT_DIR / "integrity_242f1afb02c8_0001.json"
FIRST_REVISION_AUDIT_REL = AUDIT_DIR / "integrity_13ad3ad81d7e_0001.json"
DECLARATION_DRAFT_REL = DECLARATIONS_DIR / "draft_resolved_fixes.json"

SCHEMA_VERSION = "1.1"
REVIEW_STATE = "agent_drafted_pending_operator_review"
DECLARED_ON = "2026-10-07"


class SuccessorError(RuntimeError):
    """An input the successor record cannot be built from; nothing is written."""


def _read_json(repo_root: Path, rel: Path) -> dict[str, Any]:
    """One committed input, refused by name rather than by traceback."""
    path = repo_root / rel
    if not path.is_file():
        raise SuccessorError(f"{rel.as_posix()} is absent.")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise SuccessorError(f"{rel.as_posix()} is not readable JSON: {exc}") from None
    if not isinstance(data, dict):
        raise SuccessorError(f"{rel.as_posix()} is not a JSON object.")
    return data


def _sha256(repo_root: Path, rel: Path) -> str:
    """The sha256 of one committed input, by the same helper the R04 renderer uses."""
    path = repo_root / rel
    if not path.is_file():
        raise SuccessorError(f"{rel.as_posix()} is absent.")
    return file_sha256(path)


# --------------------------------------------------------------------------- #
# Roles, each quoted from the candidate's own text
# --------------------------------------------------------------------------- #

#: Role id -> the role as the candidate names it, the sub-section that names it
#: as ``<section_id>/<sub_section_id>``, a verbatim anchor from that
#: sub-section's text, and why that body owns the change. A role this
#: repository cannot point at would be a project fact invented here
#: (CLAUDE.md 13.3), so every anchor is resolved against the candidate by
#: ``tests/test_msca_dn_successor_dispositions.py``.
ROLES: Mapping[str, Mapping[str, str]] = {
    "coordinator": {
        "role": "Project Coordinator",
        "source": "implementation_section/5",
        "anchor": "Project Coordinator and Management Team",
        "basis": (
            "the Coordinating Beneficiary is responsible for overall scientific, "
            "administrative and financial coordination, and monitors deliverables, "
            "milestones, risks and compliance across all work packages"
        ),
    },
    "supervisory_board": {
        "role": "Supervisory Board (SB)",
        "source": "implementation_section/5",
        "anchor": "Monitoring supervision quality and training implementation",
        "basis": (
            "the Supervisory Board monitors supervision quality and training "
            "implementation, including Individual Training Panels, PhD Committees and "
            "Personal Career Development Plans"
        ),
    },
    "dec_committee": {
        "role": "Dissemination, Exploitation and Communication (DEC) Committee",
        "source": "implementation_section/5",
        "anchor": "Defining and monitoring key performance indicators",
        "basis": (
            "the DEC Committee defines and monitors the key performance indicators, "
            "including publications, software releases, policy outputs and outreach"
        ),
    },
    "ip_panel": {
        "role": "IP and Exploitation Panel",
        "source": "implementation_section/5",
        "anchor": "an IP and Exploitation Panel reviews",
        "basis": "the panel sits within the DEC governance structure and reviews inventions",
    },
    "innovation_committee": {
        "role": "Innovation and Sustainability Committee",
        "source": "implementation_section/5",
        "anchor": "the Innovation and Sustainability Committee",
        "basis": "one of the four key bodies of the governance structure",
    },
    "wp_leads_1_4": {
        "role": "the lead participants of WP1-WP4",
        "source": "implementation_section/3.1",
        "anchor": "Lead participant",
        "basis": (
            "each work-package block of the work plan carries a 'Lead participant' line, "
            "and the methods, dependencies and deliverables at issue are those packages'"
        ),
    },
    "wp2_lead": {
        "role": "the lead participant of WP2",
        "source": "implementation_section/3.1",
        "anchor": "WP Number: 2",
        "basis": (
            "implementation_section/3.2 places secure medical-data and interoperability "
            "infrastructures at Academic Beneficiaries E and G, and data-protection "
            "expertise at G and H, supporting WP2"
        ),
    },
    "wp4_lead": {
        "role": "the lead participant of WP4",
        "source": "implementation_section/3.1",
        "anchor": "WP title: Clinical Adaptation & Case Studies",
        "basis": "WP4 runs the clinical adaptation and case studies the ESR criticises",
    },
}


def _role(key: str) -> dict[str, str]:
    return dict(ROLES[key])


# --------------------------------------------------------------------------- #
# One revision plan per ESR shortcoming (ticket R05 item 6)
# --------------------------------------------------------------------------- #

REVISION_PLANS: Mapping[str, Mapping[str, Any]] = {
    "ESR-E-01": {
        "evidence": [
            "ESR-E-01, page 2, Criterion 1 comment, cluster C1 point 1",
            "the blind excellence shortcoming cited on this row, resolved against the frozen baseline",
            "the two 1.2 passages quoted on this row, verified in the candidate",
        ],
        "responsible_role": _role("wp_leads_1_4"),
        "requires_confirmation": [
            "the identification strategy and the estimator each DC project will use",
            "the validation metric per pipeline stage and the retrospective cohort it applies to",
        ],
        "proposal_location": ["excellence_section/1.2, the AI/ML methodology block"],
        "commitment_kind": "requires_study_design",
    },
    "ESR-E-02": {
        "evidence": [
            "ESR-E-02, page 2, Criterion 1 comment, cluster C1 point 1",
            "the two 1.2 passages quoted on this row: data protection is mentioned, security is not described",
            "fidelity_register#provenance/transformation/prose: some passages omitted or rephrased",
        ],
        "responsible_role": _role("wp2_lead"),
        "requires_confirmation": [
            "the threat model and the access-control design for the federated nodes",
            "who owns incident response across the hosts",
            "that the ethics self-assessment carries the same account",
        ],
        "proposal_location": [
            "excellence_section/1.2, the open-science and data-protection block",
            "implementation_section/6, the ethics self-assessment",
        ],
        "commitment_kind": "requires_study_design",
    },
    "ESR-E-03": {
        "evidence": [
            "ESR-E-03, page 2, Criterion 1 comment, cluster C1 point 2",
            "the 1.1 and 3.1 passages quoted on this row: evaluation is retrospective",
            "adjudication A07: the dispute R02 raised is not sustained and the row is a plain miss",
        ],
        "responsible_role": _role("wp4_lead"),
        "requires_confirmation": [
            "that a shadow-mode or silent-trial design is feasible at a named clinical site",
            "the pre-registered endpoints and the month window",
            "which DC project carries the prospective arm",
        ],
        "proposal_location": [
            "implementation_section/3.1, the WP4 task that evaluates cardiovascular models",
            "excellence_section/1.2, the methodology block",
        ],
        "commitment_kind": "requires_study_design",
    },
    "ESR-E-04": {
        "evidence": [
            "ESR-E-04, page 2, Criterion 1 comment, cluster C1 point 3",
            "the Task 4.3 passages quoted on this row: multicentre, with data sources listed and no counts",
            "adjudication A06: cohort magnitude and cohort composition are different properties",
        ],
        "responsible_role": _role("wp4_lead"),
        "requires_confirmation": [
            "the number of hospitals, countries, operators and procedures per site available to Task 4.3",
            "the years the cohort covers",
            "whether site and operator heterogeneity can enter the causal model as variables",
        ],
        "proposal_location": ["implementation_section/3.1, Task 4.3"],
        "commitment_kind": "requires_data_access",
    },
    "ESR-E-05": {
        "evidence": [
            "ESR-E-05, page 2, Criterion 1 comment, cluster C1 point 4",
            "fidelity_register#provenance/transformation/identifiers: partner, people and place names generalised",
            "fidelity_register#provenance/transformation/prose: some passages omitted or rephrased",
        ],
        "responsible_role": _role("coordinator"),
        "requires_confirmation": [
            "whether the submitted original named the registry or database and its contributing clinicians (PE-09)",
            "the number of contributing clinicians and sites, and their roles in data curation",
        ],
        "proposal_location": [
            "excellence_section/1.2, where the registry or database is introduced",
            "excellence_section/1.1",
        ],
        "commitment_kind": "requires_original_check",
    },
    "ESR-E-06": {
        "evidence": [
            "ESR-E-06, page 2, Criterion 2 comment, cluster C2",
            "the two 1.2 passages quoted on this row, under 'Gender dimension and diversity aspects'",
            "the blind excellence shortcoming cited on this row",
        ],
        "responsible_role": _role("wp4_lead"),
        "requires_confirmation": [
            "which sex- and gender-disaggregated variables each cohort dataset actually carries",
            "which subgroup analyses are powered in the TAVI, heart-failure and critical-care cohorts",
        ],
        "proposal_location": [
            "excellence_section/1.2, 'Gender dimension and diversity aspects'",
        ],
        "commitment_kind": "requires_study_design",
    },
    "ESR-E-07": {
        "evidence": [
            "ESR-E-07, page 3, Criterion 1 comment, cluster C3",
            "the two 1.3 passages quoted on this row, in the network-wide training block",
            "adjudication A08: a lane read the passage and rated it adequate rather than missing it",
        ],
        "responsible_role": _role("supervisory_board"),
        "requires_confirmation": [
            "the local doctoral-school modules each host requires of its DC",
            "the ECTS or hours per local module and per network-wide event",
        ],
        "proposal_location": ["excellence_section/1.3, section 1.3.4"],
        "commitment_kind": "requires_partner_commitment",
    },
    "ESR-E-08": {
        "evidence": [
            "ESR-E-08, page 3, Criterion 1 comment, cluster C3",
            "the 1.3 and 2.2 passages quoted on this row: TG5 and the Research-to-Innovation canvas",
            "fidelity_register#provenance/transformation/prose",
        ],
        "responsible_role": _role("innovation_committee"),
        "requires_confirmation": [
            "an industrial partner willing to mentor the exercise and host the pitch session",
            "the deliverable and month that record the business-case exercise",
        ],
        "proposal_location": [
            "excellence_section/1.3, TG5",
            "impact_section/2.2",
        ],
        "commitment_kind": "requires_partner_commitment",
    },
    "ESR-E-09": {
        "evidence": [
            "ESR-E-09, page 3, Criterion 1 comment, cluster C4",
            "the 1.4 passage quoted on this row",
            "adjudication A09: a lane read the supervision passage and asked a different question of it",
        ],
        "responsible_role": _role("supervisory_board"),
        "requires_confirmation": [
            "the supervision-quality instrument and its cadence",
            "the indicator thresholds that trigger Supervisory Board action",
            "who reviews the results and when",
        ],
        "proposal_location": ["excellence_section/1.4, supervision quality"],
        "commitment_kind": "requires_partner_commitment",
    },
    "ESR-I-01": {
        "evidence": [
            "ESR-I-01, page 3, Criterion 2 comment, cluster C5",
            "the two 2.3 passages quoted on this row, under 'Strategy for the management of "
            "intellectual property and foreseen protection measures'",
            "the blind impact shortcoming cited on this row",
        ],
        "responsible_role": _role("ip_panel"),
        "requires_confirmation": [
            "which results carry industrial value, per work package, and who owns each",
            "the protection route and the decision month for each result",
        ],
        "proposal_location": [
            "impact_section/2.3, the intellectual-property and protection block",
        ],
        "commitment_kind": "requires_partner_commitment",
    },
    "ESR-I-02": {
        "evidence": [
            "ESR-I-02, page 4, Criterion 2 comment, cluster C6",
            "the 2.4 passage quoted on this row: three impact pathways, stated without magnitude",
            "the blind impact shortcoming cited on this row",
        ],
        "responsible_role": _role("dec_committee"),
        "requires_confirmation": [
            "the adoption numbers per pathway at M36 and M60, and the baseline for each",
            "that each number is defensible without a market study the project does not run",
        ],
        "proposal_location": [
            "impact_section/2.4, expected economic and technological impact",
        ],
        "commitment_kind": "requires_numerical_target",
    },
    "ESR-Q-01": {
        "evidence": [
            "ESR-Q-01, page 4, Criterion 3 comment, cluster C7 point 1",
            "the two remaining blind implementation shortcomings cited on this row",
            "fidelity_register#derived/figures/images_on_any_page: zero images on any page",
        ],
        "responsible_role": _role("wp_leads_1_4"),
        "requires_confirmation": [
            "for each work package, the inputs it needs from others with the deliverable id and month",
            "whether the submission carried a Gantt or dependency figure that sanitisation removed (PE-09)",
        ],
        "proposal_location": ["implementation_section/3.1, the work-plan block"],
        "commitment_kind": "requires_study_design",
    },
    "ESR-Q-02": {
        "evidence": [
            "ESR-Q-02, page 4, Criterion 3 comment, cluster C7 point 2",
            "the two 3.1 passages quoted on this row, from the deliverables table",
            "adjudication A10: the one blind sentence about this point misattributes a "
            "neighbouring artifact's property, so no lane carries it",
        ],
        "responsible_role": _role("wp_leads_1_4"),
        "requires_confirmation": [
            "the acceptance test or benchmark for each technical deliverable",
            "the clinical reviewer who signs off each clinical deliverable",
        ],
        "proposal_location": [
            "implementation_section/3.1, the scientific deliverables table",
        ],
        "commitment_kind": "requires_study_design",
    },
    "ESR-Q-03": {
        "evidence": [
            "ESR-Q-03, page 4, Criterion 3 comment, cluster C7 point 3",
            "the surviving audit finding: M7.3 is due M48 and its related WP7 runs M1-M36",
            "the M7.3 and M4.2 milestone rows quoted on this row",
            "adjudication A04: the window conflict is a timing misalignment the copy itself declares",
        ],
        "responsible_role": _role("coordinator"),
        "requires_confirmation": [
            "whether M7.3 moves inside the project window or becomes a post-project commitment",
            "the deliverable each milestone depends on, and that its due month follows them",
            "the evaluation endpoint M4.2 is defined against",
        ],
        "proposal_location": [
            "implementation_section/3.1, the milestones table",
        ],
        "commitment_kind": "requires_partner_commitment",
    },
    "ESR-Q-04": {
        "evidence": [
            "ESR-Q-04, page 4, Criterion 3 comment, cluster C8",
            "the two 3.1 passages quoted on this row, from the risk table",
            "the blind implementation shortcoming cited on this row",
        ],
        "responsible_role": _role("coordinator"),
        "requires_confirmation": [
            "a measurable trigger per risk: a month, a count or a percentage",
            "the owner who acts on each trigger",
            "the two or three technical risks WP1-WP3 carry and their triggers",
        ],
        "proposal_location": ["implementation_section/3.1, the risk table"],
        "commitment_kind": "requires_numerical_target",
    },
}


# --------------------------------------------------------------------------- #
# The register basis the 1.1 rule requires of every miss
# --------------------------------------------------------------------------- #

#: Schema 1.1 makes a miss name the register entry its preservation claim rests
#: on. Two pointers per row: the derived measurement of the sub-section the
#: passage was quoted from, which is what this copy can show, and the
#: document-wide prose declaration, which is what it cannot.
MISS_EVIDENCE_BASIS: Mapping[str, Sequence[str]] = {
    "ESR-E-02": ["derived/sub_sections/1.2", "provenance/transformation/prose"],
    "ESR-E-03": [
        "derived/sub_sections/1.1",
        "derived/sub_sections/3.1",
        "provenance/transformation/prose",
    ],
    "ESR-E-04": ["derived/sub_sections/3.1", "provenance/transformation/prose"],
    "ESR-E-07": ["derived/sub_sections/1.3", "provenance/transformation/prose"],
    "ESR-E-08": [
        "derived/sub_sections/1.3",
        "derived/sub_sections/2.2",
        "provenance/transformation/prose",
    ],
    "ESR-E-09": ["derived/sub_sections/1.4", "provenance/transformation/prose"],
    "ESR-Q-02": [
        "derived/sub_sections/3.1",
        "provenance/transformation/reformatting/tables_3_1b_to_e",
    ],
}


# --------------------------------------------------------------------------- #
# The three rows the review moves
# --------------------------------------------------------------------------- #

_AUDIT_CITATION = {
    "report": SUCCESSOR_AUDIT_REL.as_posix(),
    "check": "milestone_dependencies",
    "index": 15,
}

EXPLANATIONS: Mapping[str, str] = {
    "ESR-E-04": (
        "Adjudication A06 compared the one cited blind shortcoming with the ESR sentence and "
        "found two different properties of a cohort: the finding names sample sizes, data-access "
        "timelines and power, the ESR names the multihospital, multi-operator design needed to "
        "reflect contemporary European practice. No sample and no cell names a site count, an "
        "operator count or representativeness. The citation is therefore withdrawn, and "
        "'partially_observable' loses the finding it requires. Task 4.3 survives, says "
        "multicentre, lists data sources and gives no counts, so the absence is readable here "
        "and this row records a miss. The alternative reading is 'not_assessable_from_this_copy': "
        "the register records prose omitted or rephrased for this task, so the submission may "
        "have carried the counts. Both statuses on this row are Unresolved until the operator "
        "chooses."
    ),
    "ESR-Q-01": (
        "Two of the three blind shortcomings the predecessor cited carry the ESR's point squarely: "
        "inter-WP dependencies and critical-path logic are not mapped beyond narrative "
        "cross-references, and no Gantt or dependency diagram is shown. The third is withdrawn. "
        "Adjudication A05 found it contradicted by the input that assessor received: it states "
        "that no intermediate milestones are shown, and the implementation section it read "
        "carries the milestones table with a due month for each of sixteen milestones across ten "
        "distinct months. The dependency point stands on the two remaining citations. The "
        "register measures zero images on any page, so a Gantt or dependency figure in the "
        "submission would have been lost and part of the lane's basis is an absence this copy "
        "created. That is why the row stays partial rather than detected."
    ),
    "ESR-Q-03": (
        "One finding survives of the four the predecessor cited. Adjudication A03 withdraws the "
        "two 'undeclared_dependency' citations: a dependency is not a column of the milestones "
        "table, so the finding records an absent column and not a misaligned milestone. "
        "Adjudication A05 withdraws the blind citation, which the assessor's own input "
        "contradicts. What remains, per A04, is the M7.3 window finding: M7.3 is due M48 and its "
        "related WP7 runs M1-M36, a timing misalignment the copy itself declares. The citation is "
        "re-filed against the successor audit, whose milestone_dependencies findings are "
        "index-for-index those of the audit the predecessor cited. So the row is detected by the "
        "integrity audit alone, on timing. No finding addresses the definitions half of the ESR "
        "sentence, which is why the operator is asked whether the row stays "
        "'independently_detected' or becomes 'partially_observable'."
    ),
}


OPEN_OPERATOR_DECISIONS: Sequence[Mapping[str, Any]] = (
    {
        "observation_id": "ESR-E-04",
        "adjudication_id": "A06",
        "question": (
            "Is the absence of site and operator counts readable from this copy, or may the "
            "submission have carried them?"
        ),
        "options": [
            "not_detected_despite_sufficient_preserved_evidence (what this record declares)",
            "not_assessable_from_this_copy",
        ],
        "effect_if_changed": (
            "the rated shortcomings fall from 14 to 13, 'not assessable' rises from 1 to 2, and "
            "the miss count falls from 7 to 6; rate_detected rises from 0.43 to 0.46"
        ),
        "declared_pending": True,
    },
    {
        "observation_id": "ESR-Q-03",
        "adjudication_id": "A12",
        "question": (
            "Does one audit finding on milestone timing carry an ESR sentence about both the "
            "definitions and the timing of milestones?"
        ),
        "options": [
            "independently_detected, by the integrity audit alone (what this record declares)",
            "partially_observable, the definitions half being carried by no finding",
        ],
        "effect_if_changed": (
            "detected falls from 6 to 5 and partial rises from 1 to 2; "
            "rate_detected falls from 0.43 to 0.36 and rate_detected_or_partial is unchanged"
        ),
        "declared_pending": True,
    },
    {
        "observation_id": "ESR-Q-03",
        "adjudication_id": "A04",
        "question": (
            "Is M7.3 at M48 against a WP7 window of M1-M36 an inconsistency to fix, or an "
            "intended post-project commitment to move out of the milestone table?"
        ),
        "options": [
            "fix the window",
            "move the commitment out of the milestones table",
        ],
        "effect_if_changed": "the proposed revision, not the disposition",
        "declared_pending": True,
    },
    {
        "observation_id": "ESR-Q-01",
        "adjudication_id": "A05, A11",
        "question": "Confirm that a citation its own assessor input contradicts is withdrawn rather than caveated.",
        "options": ["withdraw (what this record declares)", "retain with a caveat"],
        "effect_if_changed": "the citation set of ESR-Q-01 and ESR-Q-03; no disposition",
        "declared_pending": True,
    },
    {
        "observation_id": "ESR-I-S02",
        "adjudication_id": None,
        "question": (
            "Does the post-project funding plan enter the revision plan even though the "
            "evaluators praised this aspect?"
        ),
        "options": ["leave as praised", "revise against the contesting blind finding"],
        "effect_if_changed": "one more open revision; no disposition and no count",
        "declared_pending": True,
    },
    {
        "observation_id": "ESR-I-S05",
        "adjudication_id": None,
        "question": (
            "Does the societal-impact indicator gap enter the revision plan, given that ESR-I-02 "
            "already asks for magnitude on the economic pathway?"
        ),
        "options": ["fold into ESR-I-02's revision", "give it its own revision"],
        "effect_if_changed": "one more open revision; no disposition and no count",
        "declared_pending": True,
    },
)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def rows_needing_an_operator_decision(repo_root: Path) -> set[str]:
    """Every observation a human still has to rule on, from both records.

    This record lists the questions R03's adjudications left open. The R03
    review notes list a question on every row whose reading the review could
    not close, and those stand: a successor that marked only its own five
    would read as if the other fourteen were settled.
    """
    notes = _read_json(repo_root, REVIEW_NOTES_REL)
    from_notes = {
        str(row["observation_id"])
        for row in notes.get("rows") or []
        if str(row.get("operator_decision") or "").strip()
    }
    return from_notes | {str(d["observation_id"]) for d in OPEN_OPERATOR_DECISIONS}


def _apply_row_changes(
    row: dict[str, Any], esr_kind: str, *, needs_decision: bool
) -> dict[str, Any]:
    """Apply this row's enumerated changes; carry everything else through."""
    oid = row["observation_id"]
    if oid == "ESR-E-04":
        row.pop("blind_findings", None)
        row["disposition"] = "not_detected_despite_sufficient_preserved_evidence"
        row["declared_status"] = "Unresolved"
        row["evidence_preserved_status"] = "Unresolved"
    elif oid == "ESR-Q-01":
        row["blind_findings"] = [
            ref for ref in row.get("blind_findings") or []
            if not (ref.get("sample_index") == 0 and ref.get("index") == 3)
        ]
    elif oid == "ESR-Q-03":
        row.pop("blind_findings", None)
        row["audit_findings"] = [dict(_AUDIT_CITATION)]
        row["declared_status"] = "Unresolved"
    if oid in EXPLANATIONS:
        row["explanation"] = EXPLANATIONS[oid]
    if row["disposition"] == "not_detected_despite_sufficient_preserved_evidence":
        basis = MISS_EVIDENCE_BASIS.get(oid)
        if basis is None:
            raise SuccessorError(
                f"{oid} is a miss under schema {SCHEMA_VERSION} and no register basis is "
                "enumerated for it."
            )
        row["evidence_basis"] = list(basis)
    row["review_status"] = (
        "operator_decision_required" if needs_decision
        else "agent_recommended_pending_operator_review"
    )
    if esr_kind != "strength":
        plan = REVISION_PLANS.get(oid)
        if plan is None:
            raise SuccessorError(f"{oid} is a shortcoming with no revision plan.")
        revision = row.get("proposed_revision")
        if not isinstance(revision, dict):
            raise SuccessorError(f"{oid} is a shortcoming with no proposed revision to plan.")
        revision["revision_plan"] = copy.deepcopy(dict(plan))
    return row


def render(repo_root: Path) -> dict[str, Any]:
    """The successor dispositions record, built from the committed predecessor."""
    predecessor = _read_json(repo_root, PREDECESSOR_REL)
    esr = _read_json(repo_root, ESR_RECORD_REL)
    kinds = {str(o["id"]): str(o["kind"]) for o in esr["observations"]}
    needs_decision = rows_needing_an_operator_decision(repo_root)
    rows = [
        _apply_row_changes(
            copy.deepcopy(row),
            kinds[str(row["observation_id"])],
            needs_decision=str(row["observation_id"]) in needs_decision,
        )
        for row in predecessor["rows"]
    ]
    unknown = sorted(set(REVISION_PLANS) - {str(r["observation_id"]) for r in rows})
    if unknown:
        raise SuccessorError(f"revision plans name unknown observation(s): {', '.join(unknown)}.")
    return {
        "record_type": "esr_dispositions",
        "schema_version": SCHEMA_VERSION,
        "artifact_purpose": (
            "The successor declared half of the PE-08 comparison (ticket R05). One disposition "
            "per observation of the same ESR record, over the same frozen baseline and the same "
            "candidate as the predecessor, with the citations R03 withdrew removed, the one "
            "disposition R03 recommends moving moved, and one revision plan per ESR "
            "shortcoming. The predecessor stays on disk and stays replayable; this record is "
            "what the review recommends, not what the operator has decided."
        ),
        "spec": "plans/msca_dn_pre_evaluation_spec.md",
        "ticket": "R05 of plans/pe08_review_and_pe09_handoff_tickets.md",
        "advisory": True,
        "blocking": False,
        "review_state": REVIEW_STATE,
        "review_status_note": (
            "Every row carries its own review_status, which the comparison carries through. "
            "'operator_decision_required' is every observation this record or the R03 review "
            "notes still put a question on; the rest are "
            "'agent_recommended_pending_operator_review'. No row is 'operator_confirmed', "
            "because no operator has reviewed this record."
        ),
        "written_by": "tools/author_successor_dispositions.py",
        "supersedes": PREDECESSOR_REL.as_posix(),
        "supersedes_sha256": _sha256(repo_root, PREDECESSOR_REL),
        "supersession_note": (
            "The PE-08 dispositions stay as written and the comparison rendered from them stays "
            "as the operator read it. Nothing here edits either. A successor record exists "
            "because a reviewed reading must be citable without destroying the reading it "
            "reviewed: the predecessor is the provisional interpretation, this is the "
            "recommendation, and the operator's decision is still outstanding on the rows listed "
            "under open_operator_decisions."
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
            "The same register, byte for byte, as the predecessor cites. R04 drafted what its "
            "declared half could say and the operator has not adopted it, so the declared half "
            "is still empty and no row's preservation claim can be Confirmed: "
            "harness.esr_comparison refuses a Confirmed evidence_preserved_status that no "
            "declared-half presence statement carries. Every miss here declares Assumed or "
            "Unresolved. Adopting "
            + DECLARATION_DRAFT_REL.as_posix()
            + " would change the register's bytes and therefore the hash this record and the "
            "predecessor's comparison pin; see that draft's adoption block for what else pins it."
        ),
        "audits": [SUCCESSOR_AUDIT_REL.as_posix(), FIRST_REVISION_AUDIT_REL.as_posix()],
        "audit_note": (
            "ESR-Q-03's one surviving audit citation is filed against the successor audit "
            + SUCCESSOR_AUDIT_REL.as_posix()
            + ", which R03 wrote after correcting two rules. It is bound to the same candidate "
            "and the same snapshot as "
            + CITED_AUDIT_REL.as_posix()
            + ", which the predecessor cited and which stays on disk as historical evidence; its "
            "milestone_dependencies findings are index-for-index the same, so the citation names "
            "the same finding. The first-revision audit is passed for the historical copy."
        ),
        "review_inputs": {
            "predecessor_comparison": PREDECESSOR_COMPARISON_REL.as_posix(),
            "predecessor_comparison_sha256": _sha256(repo_root, PREDECESSOR_COMPARISON_REL),
            "operator_review": OPERATOR_REVIEW_REL.as_posix(),
            "review_notes": REVIEW_NOTES_REL.as_posix(),
            "review_notes_sha256": _sha256(repo_root, REVIEW_NOTES_REL),
            "adjudication_record": ADJUDICATIONS_REL.as_posix(),
            "adjudication_record_sha256": _sha256(repo_root, ADJUDICATIONS_REL),
            "declaration_draft": DECLARATION_DRAFT_REL.as_posix(),
            "declaration_draft_note": (
                "cited by path and not by hash. The draft's own adoption block enumerates every "
                "artifact that names the register, this record included, so hashing the draft "
                "here would make the two records chase each other: a re-render of the draft "
                "would move this record, which would move the comparison written from it, whose "
                "hash names the diff artifact, which the draft would then have to enumerate. The "
                "draft is a review input, not a binding this comparison rests on."
            ),
        },
        "declared_by": (
            "drafted in a Claude Code session, 2026-10-07, from the R02 review table and the R03 "
            "adjudication record. Every disposition is an agent recommendation pending operator "
            "review; none records an operator decision"
        ),
        "declared_on": DECLARED_ON,
        "declared_status_note": (
            "declared_status is the status of the disposition judgment itself (CLAUDE.md "
            "section 12.2): Inferred where it follows from resolved findings and verified quotes, "
            "Assumed where it rests on a register declaration about what sanitisation removed, "
            "Unresolved where the adjudication left the reading to the operator. "
            "evidence_preserved_status is the status of the preservation claim a miss makes. It "
            "is Assumed where the document-wide provenance declaration is the only basis, and "
            "Unresolved on ESR-E-04, where the choice between a miss and an unassessable row is "
            "open. A Confirmed value would need the register's declared half, which is empty."
        ),
        "decision_state": {
            "state": REVIEW_STATE,
            "statement": (
                "No row of this record is operator-approved. Four rows carry a question the "
                "operator has to answer before this record can be called a decision, and two "
                "more ask whether a contested strength enters the revision plan. The comparison "
                "written from this record is a labelled draft for the same reason."
            ),
            "rows_whose_declarations_changed": ["ESR-E-04", "ESR-Q-01", "ESR-Q-03"],
            "rows_whose_register_basis_grew": sorted(MISS_EVIDENCE_BASIS),
            "register_basis_note": (
                "Schema 1.1 makes every miss name the register entry its preservation claim "
                "rests on, so each of the seven carries the derived measurement of the "
                "sub-section the passage was quoted from alongside the document-wide prose "
                "declaration. Nothing a row declares about the point itself changes with it."
            ),
            "revision_plans_added": len(REVISION_PLANS),
            "rows_needing_an_operator_decision": sorted(needs_decision),
            "rows_carried_through_untouched": 14,
            "rows_carried_through_note": (
                "the fourteen ESR strengths: no plan, no register basis and no declaration moves "
                "on any of them"
            ),
        },
        "open_operator_decisions": [dict(d) for d in OPEN_OPERATOR_DECISIONS],
        "revision_plan_note": (
            "Each proposed revision carries a plan: the evidence it rests on, the human role "
            "that owns it quoted from the candidate's own governance and work-package text, what "
            "has to be confirmed before it can be written, where in the proposal it goes, and "
            "what carrying it out commits someone to. The four commitment kinds other than "
            "editorial_change and requires_original_check are the four things ticket R05 item 6 "
            "keeps as proposals until a human confirms them: a numerical target, a study design, "
            "data or site access, a partner commitment. None of the fifteen is editorial: not "
            "one can be written from what this copy already carries."
        ),
        "addressed_rows": str(predecessor["addressed_rows"]),
        "rows": rows,
    }


def render_all(repo_root: Path) -> dict[str, bytes]:
    return {SUCCESSOR_REL.as_posix(): canonical_json_bytes(render(repo_root))}


def check(repo_root: Path) -> list[str]:
    """Relative paths whose bytes differ from the rendering, or are absent."""
    return [
        rel
        for rel, data in render_all(repo_root).items()
        if not (repo_root / rel).is_file() or (repo_root / rel).read_bytes() != data
    ]


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
    parser.add_argument(
        "--check", action="store_true", help="exit 1 if the successor record would change"
    )
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
        print("no change" if not changed else f"{len(changed)} file(s) written")
        return 0
    except SuccessorError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
