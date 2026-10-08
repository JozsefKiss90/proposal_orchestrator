# Operator decisions — msca-dn-2025-sanitised-v1

Generated: 2026-10-08T10:54:31.046022+00:00  
Review state: **agent_drafted_pending_operator_review**  
Ticket: R02 of `plans/pe08_review_and_pe09_handoff_tickets.md`  
Adjudications: `docs/tier4_orchestration_state/msca_dn/esr/semantic_adjudications_f60ae6e0a2a1.json`  
Full report: `operator_review_14508ee2def5_0001.md` (same directory)  
Comparison: `docs/tier4_orchestration_state/msca_dn/comparisons/comparison_f60ae6e0a2a1_0003.json`

Every recommendation, uncertainty and proposed revision in this report is agent-drafted and provisional. A row marked 'decision recorded' carries an operator decision transcribed from the approval record listed among the inputs, under the decision id that record uses; no other line here is an operator decision, and an approved review policy is not a confirmed fact.

Advisory to a human, never run-blocking (`harness/HARNESS.md`): this report evaluates no gate and blocks no phase. Its inputs carry `advisory: true` and `blocking: false`, and so do the review notes it rests on.

## Recorded decisions

9 row(s) carry a decision transcribed from `docs/tier4_orchestration_state/msca_dn/reviews/operator_approval_2026-10-08.md`, under the id that record uses.

- **ESR-E-01** — D01: D01: Keep methods and clinical-data security as separate clause-level observations. Report their shared sentence and severity cluster. Limit retained: Do not present them as separate evaluator sentences, independent deductions, or inflate cluster-level detection.
- **ESR-E-03** — D02: D02: Accept non-detection of the criticism in the recorded output. Limit retained: Do not claim absence from output proves the model did not read the evidence. Qualify or replace the `evidence_not_read` causal description in successor documentation. Preservation remains separately qualified.
- **ESR-E-07** — D03: D03: Count missed ESR criticisms in the same detection summary, subject to preservation; distinguish adequacy disagreement from an unmentioned topic. Limit retained: Report failure-mode breakdowns separately. Detection is not an overall accuracy or calibration claim.
- **ESR-E-09** — D03: D03: Count missed ESR criticisms in the same detection summary, subject to preservation; distinguish adequacy disagreement from an unmentioned topic. Limit retained: Report failure-mode breakdowns separately. Detection is not an overall accuracy or calibration claim.
- **ESR-I-S02** — D07: D07: Prepare an optional improvement beyond the ESR, conditional on checking the original. Limit retained: No funding source, budget, maintenance duty or partner commitment is approved. Preserve the ESR strength.
- **ESR-I-S05** — D08: D08: Add a separately labelled societal-impact subtask within the broader impact revision package. Limit retained: Keep it distinct from the ESR economic/technological criticism. No invented indicators, numerical targets or promised clinical outcomes.
- **ESR-Q-01** — D04: D04: Withdraw the contradicted citation and retain it as an assessor validation case for PE-09. Limit retained: Never edit proposal milestones to satisfy the false absence claim.
- **ESR-Q-02** — D05: D05: Record the deliverable/milestone conflation as an assessor validation case. Limit retained: A missing validation column does not prove inadequate deliverable validation. Review relevant prose and original-dependent evidence before finalising the proposal judgment.
- **ESR-Q-03** — D06, D12: D06: Replace full detection with provisional partial detection; integrity audit is the only contributing lane. Limit retained: The surviving finding concerns timing only. Definitions are not detected; timing interpretation remains Unresolved. If original context removes the alleged conflict, revisit detection credit. D12: Defer date changes and relocation until duration, WP scope and intended follow-up timing are privately verified. Limit retained: The two existing alternatives are not exhaustive. Retaining the date with adequate explanation may be justified by the original context.

## Open decisions

12 decisions, in the ESR's own order. Each names the row, what the reviewer could and could not establish, and the question.

### 1. ESR-E-02 — shortcoming, `not_detected_despite_sufficient_preserved_evidence`

> However, AI/ML plans- specifically conceptual paradigms, methods, and validation metrics, as well as critical security aspects for handling clinical data with AI are insufficiently detailed.

- **Agreement:** `not_applicable` — No blind sample, cell rationale or audit check names security of clinical data, so there is no finding whose proposition could agree or disagree. The copy carries two passing references to data protection and no security passage.
- **Uncertainty:** The disposition counts this as a miss on the ground that the ESR itself found the submission thin, so the copy cannot be thinner in kind. That is a reading of the ESR's wording, not a measurement: the register records prose 'some passages omitted or rephrased', so a security passage may have been removed. The preservation status is declared Assumed.
- **Recommendation:** `revisit_after_declaration`
- **Decision:** Deferred to the private network by the approval record. Required private evidence: Original security, hospital/operator diversity and entrepreneurship mechanisms; compare relevant passages with sanitised text. Current review disposition: Preservation is unconfirmed. Withdraw E-04's cohort-size citation now; do not settle miss versus not-assessable from an absence in this copy. This cell of the approval's deferral table covers ESR-E-02, ESR-E-04, ESR-E-08, and its text is the cell's, not one row's alone.

### 2. ESR-E-04 — shortcoming, `not_detected_despite_sufficient_preserved_evidence`

> the cohort is not sufficient concerning the multihospital, multi-operator design needed to reflect contemporary European TAVI practice to capture the diversity;

- **Agreement:** `disputed` — The one cited finding names sample sizes, data-access timelines and power. The ESR's point is a multihospital, multi-operator design. Cohort magnitude and cohort composition are different properties, and no sample or cell names a site count, an operator count or representativeness, so the citation does not support the ESR's proposition (A06).
- **Uncertainty:** Task 4.3 survives, says multicentre and gives no counts, so the gap is readable from this copy. The register records prose omitted or rephrased for this task, which is the only ground for calling the row unmeasurable instead.
- **Recommendation:** `adjudicated`
- **Decision:** Deferred to the private network by the approval record. Required private evidence: Original security, hospital/operator diversity and entrepreneurship mechanisms; compare relevant passages with sanitised text. Current review disposition: Preservation is unconfirmed. Withdraw E-04's cohort-size citation now; do not settle miss versus not-assessable from an absence in this copy. This cell of the approval's deferral table covers ESR-E-02, ESR-E-04, ESR-E-08, and its text is the cell's, not one row's alone.

### 3. ESR-E-05 — shortcoming, `not_assessable_from_this_copy`

> and the number of contributing clinicians to the database is not well-specified.

- **Agreement:** `not_applicable` — No finding names the database or its contributing clinicians, and the word does not occur in the copy's Part B. There is nothing in this copy for a finding to be about.
- **Uncertainty:** Two causes of the absence cannot be told apart here: the referent was generalised away with the identifiers, or the submission introduced the database in a passage the register records as omitted. The disposition's 'not assessable from this copy' is the honest reading either way, and it is the only such row of the 29.
- **Recommendation:** `revisit_after_private_network`
- **Decision:** Deferred to the private network by the approval record. Required private evidence: Original registry/database and contributing-clinician passages. Current review disposition: Keep not-assessable pending evidence.

### 4. ESR-E-S03 — strength, `partially_observable`

> Open science practices, such as preprints, and repositories, are included and adequately described in the proposed methodology.

- **Agreement:** `unresolved` — The ESR credits open science practices 'such as preprints, and repositories', which means the submission named them. Three samples fault the commitments for naming no repositories, licences or governance. The two readings cannot both describe the same text.
- **Uncertainty:** The register records identifiers generalised and every citation removed. Named repositories and venues are the kind of content that sanitisation strips, so the contest may rest on evidence this copy lacks rather than on a weakness of the proposal.
- **Recommendation:** `revisit_after_private_network`
- **Decision:** Deferred to the private network by the approval record. Required private evidence: Original repository/preprint commitments, supervisor mapping and track-record evidence. Current review disposition: Do not adopt blind criticisms as established proposal weaknesses. This cell of the approval's deferral table covers ESR-E-S03, ESR-E-S05, and its text is the cell's, not one row's alone.

### 5. ESR-E-08 — minor_shortcoming, `not_detected_despite_sufficient_preserved_evidence`

> In addition, some details for training are not properly described, for example, the integration of entrepreneurship training lacks clear mechanisms for practical application.

- **Agreement:** `not_applicable` — No blind sample and no cell rationale names entrepreneurship. The quoted passages show the TG5 goal and the 2.2 sentence survive, and neither says how a fellow applies the training.
- **Uncertainty:** The missing thing is a mechanism, which is an absence the lane could have named from this copy. The preservation status is Assumed, as for every miss.
- **Recommendation:** `revisit_after_declaration`
- **Decision:** Deferred to the private network by the approval record. Required private evidence: Original security, hospital/operator diversity and entrepreneurship mechanisms; compare relevant passages with sanitised text. Current review disposition: Preservation is unconfirmed. Withdraw E-04's cohort-size citation now; do not settle miss versus not-assessable from an absence in this copy. This cell of the approval's deferral table covers ESR-E-02, ESR-E-04, ESR-E-08, and its text is the cell's, not one row's alone.

### 6. ESR-E-S05 — strength, `partially_observable`

> The supervisors are experienced and highly qualified in their scientific roles. They demonstrate appropriate international and local experience across all relevant areas and facilitating the adequate and effective completion the individual research projects. The well-structured and multi-layered approach of supervision practices is solid and overall sound. It ensures effective progress monitoring, feedback and support for the fellows; for example, well-defined and reviewed Personal Career Development Plans ensure systematic tracking of training objectives.

- **Agreement:** `unresolved` — The supervision structure the ESR calls well-structured and multi-layered is named as a strength in every sample, so that half agrees. The supervisors' experience is contested by three samples and by a failing cell member, which the ESR calls experienced and highly qualified.
- **Uncertainty:** Two of the contesting findings fault the anonymisation itself ('Supervisor A-K', no DC mapping), which is sanitisation and not a property of the submission. One faults H-index figures that did survive into this copy, so that part of the contest is readable here; whether those figures are the submission's own is a register question, since prose was omitted or rephrased.
- **Recommendation:** `revisit_after_private_network`
- **Decision:** Deferred to the private network by the approval record. Required private evidence: Original repository/preprint commitments, supervisor mapping and track-record evidence. Current review disposition: Do not adopt blind criticisms as established proposal weaknesses. This cell of the approval's deferral table covers ESR-E-S03, ESR-E-S05, and its text is the cell's, not one row's alone.

### 7. ESR-I-S01 — strength, `independently_detected`

> Non-academic sector contribution to doctoral training is well described and compelling; they have a meaningful and tangible role through structured secondments in hospitals, SMEs, and regulatory bodies, ensuring hands-on exposure to clinical workflows, compliance, and innovation. Industry and regulatory partners actively co-supervise doctoral candidates (DCs), participate the Individual Training Panels, and the Supervisory Board, and lead network-wide training sessions.

- **Agreement:** `agreed` — Three criterion strengths name the structured secondments, the non-academic co-supervision and the Supervisory Board and ITP roles, and the imp-structuring cell passes 3/3. Those are the ESR's own examples.
- **Uncertainty:** Two samples add an arithmetic contradiction the evaluators did not record: section 2.1 claims at least 80% of secondment months in non-academic settings, while the DC table sums to about 74% and DC7 shows ten secondment months with none non-academic. That is computed from the appendix table as this copy carries it.
- **Recommendation:** `revisit_after_declaration`
- **Decision:** Deferred to the private network by the approval record. Required private evidence: Original secondment rows, host-sector classifications and the denominator for the 80% claim. Current review disposition: Recompute privately before approving a correction. Identify the actual source subsection; do not guess one.

### 8. ESR-I-S04 — strength, `partially_observable`

> The dissemination, exploitation, and communication measures are comprehensive, and well-structured, with clear objectives and monitoring through measurable indicators. The target groups for these measures are clearly identified. The outline of intellectual property management strategy is mostly appropriately addressed.

- **Agreement:** `unresolved` — The ESR credits clear objectives, measurable indicators and clearly identified target groups. Four samples fault the communication plan for having no audience segmentation and no communication indicators, and the imp-dissemination cell fails 2 of 3. The readings contradict each other on the same sub-section.
- **Uncertainty:** The register measures zero images on any page and records every figure lost. A dissemination table or figure of target groups and indicators is exactly what that loss removes, so the cell failure may be an artifact of the copy.
- **Recommendation:** `revisit_after_private_network`
- **Decision:** Deferred to the private network by the approval record. Required private evidence: Original target-group/indicator tables, figures and prose. Current review disposition: Do not attribute the disagreement to sanitisation as a confirmed cause.

### 9. ESR-Q-01 — shortcoming, `partially_observable`

> However, several aspects lack appropriate detail such as the description of dependencies between work packages.

- **Agreement:** `disputed` — Two of the three cited findings carry the ESR's point: dependencies and critical-path logic are not mapped beyond narrative cross-references, and no Gantt or dependency diagram is shown. The third is withdrawn: it states that no intermediate milestones are shown, and the implementation section the assessor received carries the milestones table with a due month for each of 16 milestones (A05, A11).
- **Uncertainty:** The register measures zero images on any page, so a Gantt or dependency figure in the submission would have been lost. That is why the row is partial and not detected, and it is a question for the private-network review, not for this copy.
- **Recommendation:** `adjudicated`
- **Decision:** Deferred to the private network by the approval record. Required private evidence: Original dependencies, Gantt and sequencing evidence. Current review disposition: Keep partial classification qualified; absence of embedded images alone does not establish that every figure was lost.

### 10. ESR-Q-03 — shortcoming, `partially_observable`

> and the definitions and timing of some milestones is not well aligned with the overall proposal.

- **Agreement:** `disputed` — Of the four cited findings, one survives. The blind citation is withdrawn (A05). The two undeclared-dependency findings rest on no sourced requirement: the milestones table the application form fixes has no dependency column (A03). The M7.3 window finding stands and matches the ESR's point on timing: a milestone due M48 related to a package the copy itself declares as M1-M36 (A04).
- **Uncertainty:** What the gap means is not settled. M7.3 is the submission of a follow-up proposal, which a consortium may intend after the funded period, and the copy declares no project duration against which M48 could be placed. Tier 2B holds no extract for this call.
- **Recommendation:** `adjudicated`
- **Decision:** Deferred to the private network by the approval record. Required private evidence: Actual project duration, WP scope, funding/activity windows and follow-up intent. Current review disposition: No date or participation changes approved.

### 11. ESR-Q-S02 — strength, `partially_observable`

> The participating organisations have the required high-quality infrastructure and capacity to implement research of high quality and their tasks. The international consortium is well-structured, integrating academic and non-academic partners with expertise, complementary strengths, and interdisciplinary knowledge, matching with the project's objectives, and reinforcing the structural and functional capability of the Doctoral Network.

- **Agreement:** `unresolved` — The infrastructure-to-WP mapping and the three-axis complementarity argument the ESR praises are named as strengths in every sample, and the impl-participants cell passes 3/3. Three samples contest the capacity claims as generic institutional boilerplate without track record, which the ESR calls high-quality infrastructure and capacity.
- **Uncertainty:** The register records identifiers generalised, and section 8 reaches this copy as unnamed 'Academic Beneficiary A-I' profiles across 8,249 characters in 209 paragraphs (derived/sub_sections/8, resolved by identity; the earlier note's 28,087 was sub-section 3.1's count under the positional rule). Prior grants, named facilities and publication records are what that generalisation removes.
- **Recommendation:** `revisit_after_private_network`
- **Decision:** Deferred to the private network by the approval record. Required private evidence: Original capacity and hosting evidence. Current review disposition: Correct identity references now; original-dependent adequacy remains unresolved. This cell of the approval's deferral table covers ESR-Q-S02, ESR-Q-S03, and its text is the cell's, not one row's alone.

### 12. ESR-Q-S03 — strength, `partially_observable`

> Hosting arrangements via accredited doctoral schools and international offices are credible and supportive.

- **Agreement:** `unresolved` — Four samples call the hosting arrangements generic, a single sentence on accredited doctoral schools and international offices. The ESR calls the same arrangements credible and supportive. One cell member reads the per-beneficiary profiles as tying named infrastructure to work packages.
- **Uncertainty:** Section 5, the network organisation, reaches this copy as 7,221 characters in 64 paragraphs with identifiers generalised (derived/sub_sections/5, resolved by identity; the earlier note's 3,135 was sub-section 2.2's count under the positional rule). Per-institution hosting detail the evaluators may have read there does not reach this copy, and the contest cannot be reconciled with the praise from what remains.
- **Recommendation:** `revisit_after_private_network`
- **Decision:** Deferred to the private network by the approval record. Required private evidence: Original capacity and hosting evidence. Current review disposition: Correct identity references now; original-dependent adequacy remains unresolved. This cell of the approval's deferral table covers ESR-Q-S02, ESR-Q-S03, and its text is the cell's, not one row's alone.

