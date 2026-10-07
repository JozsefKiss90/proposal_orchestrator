# Operator decisions — msca-dn-2025-sanitised-v1

Generated: 2026-10-07T18:42:46.441115+00:00  
Review state: **agent_drafted_pending_operator_review**  
Ticket: R02 of `plans/pe08_review_and_pe09_handoff_tickets.md`  
Adjudications: `docs/tier4_orchestration_state/msca_dn/esr/semantic_adjudications_f60ae6e0a2a1.json`  
Full report: `operator_review_9732dde50039_0002.md` (same directory)  
Comparison: `docs/tier4_orchestration_state/msca_dn/comparisons/comparison_f60ae6e0a2a1_0001.json`

Every recommendation, uncertainty and proposed revision in this report is agent-drafted and provisional. None of it is an operator decision, and nothing here records one.

Advisory to a human, never run-blocking (`harness/HARNESS.md`): this report evaluates no gate and blocks no phase. Its inputs carry `advisory: true` and `blocking: false`, and so do the review notes it rests on.

19 decisions, in the ESR's own order. Each names the row, what the reviewer could and could not establish, and the question.

## 1. ESR-E-01 — shortcoming, `independently_detected`

> However, AI/ML plans- specifically conceptual paradigms, methods, and validation metrics, as well as critical security aspects for handling clinical data with AI are insufficiently detailed.

- **Agreement:** `agreed` — All five criterion samples fault the causal-AI methodology for naming no techniques, estimators or validation metrics. That is the first clause of the ESR sentence, word for word in substance.
- **Uncertainty:** This observation and ESR-E-02 carry the same ESR sentence: the operator's transcription split one sentence into its AI/ML clause and its security clause. The blind lane covers the first clause only, so the sentence counts once as detected and once as missed. Every other observation has text of its own.
- **Recommendation:** `retain`
- **Decision:** Confirm that splitting one ESR sentence into ESR-E-01 and ESR-E-02 is intended. It is the only such split, and it puts one sentence on both sides of the detection count.

## 2. ESR-E-02 — shortcoming, `not_detected_despite_sufficient_preserved_evidence`

> However, AI/ML plans- specifically conceptual paradigms, methods, and validation metrics, as well as critical security aspects for handling clinical data with AI are insufficiently detailed.

- **Agreement:** `not_applicable` — No blind sample, cell rationale or audit check names security of clinical data, so there is no finding whose proposition could agree or disagree. The copy carries two passing references to data protection and no security passage.
- **Uncertainty:** The disposition counts this as a miss on the ground that the ESR itself found the submission thin, so the copy cannot be thinner in kind. That is a reading of the ESR's wording, not a measurement: the register records prose 'some passages omitted or rephrased', so a security passage may have been removed. The preservation status is declared Assumed.
- **Recommendation:** `revisit_after_declaration`
- **Decision:** Decide whether a miss may be counted against the lane on Assumed preservation. If the R04 declaration for 1.2 cannot say the security content is no thinner than the submission's, this row belongs in 'partially observable' or 'not assessable'.

## 3. ESR-E-03 — shortcoming, `not_detected_despite_sufficient_preserved_evidence`

> It is also not fully clear how some of the chosen methods will deliver key objectives: cardiovascular AI models are evaluated only retrospectively with limited plans for prospective validation;

- **Agreement:** `not_applicable` — No finding raises the retrospective-only evaluation design, and R03 measured why: the frozen baseline never uses the words prospective, shadow or retrospective, in any of the 15 criterion samples or any of the 10 cells. The lane did not weigh the evaluation design and rate it adequate; it never reached the point (A07).
- **Uncertainty:** None remains on this ground. R02 left open whether a lane reading the shadow-mode sentence as a prospective plan would be wrong; the measurement withdraws that reading, because no lane output mentions the design either way.
- **Recommendation:** `adjudicated`
- **Decision:** Confirm that the measurement closes R02's open question and that the row stands as a plain miss, with failure mode evidence_not_read recorded in A07.

## 4. ESR-E-04 — shortcoming, `partially_observable`

> the cohort is not sufficient concerning the multihospital, multi-operator design needed to reflect contemporary European TAVI practice to capture the diversity;

- **Agreement:** `disputed` — The one cited finding names sample sizes, data-access timelines and power. The ESR's point is a multihospital, multi-operator design. Cohort magnitude and cohort composition are different properties, and no sample or cell names a site count, an operator count or representativeness, so the citation does not support the ESR's proposition (A06).
- **Uncertainty:** Task 4.3 survives, says multicentre and gives no counts, so the gap is readable from this copy. The register records prose omitted or rephrased for this task, which is the only ground for calling the row unmeasurable instead.
- **Recommendation:** `adjudicated`
- **Decision:** The partial detection rests on no finding and the disposition cannot stay partially_observable. Choose not_detected_despite_sufficient_preserved_evidence, on the ground that the missing site and operator counts are readable from this copy, or not_assessable, on the ground that the register records rephrased prose for Task 4.3.

## 5. ESR-E-05 — shortcoming, `not_assessable_from_this_copy`

> and the number of contributing clinicians to the database is not well-specified.

- **Agreement:** `not_applicable` — No finding names the database or its contributing clinicians, and the word does not occur in the copy's Part B. There is nothing in this copy for a finding to be about.
- **Uncertainty:** Two causes of the absence cannot be told apart here: the referent was generalised away with the identifiers, or the submission introduced the database in a passage the register records as omitted. The disposition's 'not assessable from this copy' is the honest reading either way, and it is the only such row of the 29.
- **Recommendation:** `revisit_after_private_network`
- **Decision:** Confirm against the submitted original whether a registry or database passage with contributing clinicians existed, and whether sanitisation removed it. Until then this row carries no verdict on the lane.

## 6. ESR-E-S03 — strength, `partially_observable`

> Open science practices, such as preprints, and repositories, are included and adequately described in the proposed methodology.

- **Agreement:** `unresolved` — The ESR credits open science practices 'such as preprints, and repositories', which means the submission named them. Three samples fault the commitments for naming no repositories, licences or governance. The two readings cannot both describe the same text.
- **Uncertainty:** The register records identifiers generalised and every citation removed. Named repositories and venues are the kind of content that sanitisation strips, so the contest may rest on evidence this copy lacks rather than on a weakness of the proposal.
- **Recommendation:** `revisit_after_private_network`
- **Decision:** Confirm whether the submission named repositories and preprint venues under 1.2. If it did, the blind contest is a sanitisation artifact and must not enter the revision plan as a weakness.

## 7. ESR-E-07 — minor_shortcoming, `not_detected_despite_sufficient_preserved_evidence`

> While network-wide training overall complements the local training programmes, there is a slight limitation in clarity and depth in systematic description of complementation of local training.

- **Agreement:** `not_applicable` — No finding faults the depth of the local-training description, and the exc-training cell passed with 3 of 3 members in agreement, its members stating that complementarity of network-wide and local programmes is explicitly stated. The lane read the paragraph the evaluators read and rated it sufficient (A08).
- **Uncertainty:** The row is a miss either way: the lane produced no criticism. What is unsettled is whether a calibration disagreement of this kind belongs in the same figure as a point the lane never reached, such as ESR-E-03.
- **Recommendation:** `adjudicated`
- **Decision:** Decide whether a passage the lane cited approvingly counts against it in the same detection figure as a point it never reached. ESR-E-09 has the same shape; ESR-Q-02 has a third, recorded in A10.

## 8. ESR-E-08 — minor_shortcoming, `not_detected_despite_sufficient_preserved_evidence`

> In addition, some details for training are not properly described, for example, the integration of entrepreneurship training lacks clear mechanisms for practical application.

- **Agreement:** `not_applicable` — No blind sample and no cell rationale names entrepreneurship. The quoted passages show the TG5 goal and the 2.2 sentence survive, and neither says how a fellow applies the training.
- **Uncertainty:** The missing thing is a mechanism, which is an absence the lane could have named from this copy. The preservation status is Assumed, as for every miss.
- **Recommendation:** `revisit_after_declaration`
- **Decision:** Confirm in the R04 declaration for 1.3 and 2.2 that the entrepreneurship passages are preserved. On that confirmation this row is the cleanest of the six misses.

## 9. ESR-E-S05 — strength, `partially_observable`

> The supervisors are experienced and highly qualified in their scientific roles. They demonstrate appropriate international and local experience across all relevant areas and facilitating the adequate and effective completion the individual research projects. The well-structured and multi-layered approach of supervision practices is solid and overall sound. It ensures effective progress monitoring, feedback and support for the fellows; for example, well-defined and reviewed Personal Career Development Plans ensure systematic tracking of training objectives.

- **Agreement:** `unresolved` — The supervision structure the ESR calls well-structured and multi-layered is named as a strength in every sample, so that half agrees. The supervisors' experience is contested by three samples and by a failing cell member, which the ESR calls experienced and highly qualified.
- **Uncertainty:** Two of the contesting findings fault the anonymisation itself ('Supervisor A-K', no DC mapping), which is sanitisation and not a property of the submission. One faults H-index figures that did survive into this copy, so that part of the contest is readable here; whether those figures are the submission's own is a register question, since prose was omitted or rephrased.
- **Recommendation:** `revisit_after_private_network`
- **Decision:** Confirm the supervisor track-record figures in this copy are the submission's. Then decide whether the uneven-track-record finding is a point the evaluators did not make, or an artifact of reading anonymised profiles.

## 10. ESR-E-09 — minor_shortcoming, `not_detected_despite_sufficient_preserved_evidence`

> However, the description remains slightly generic on how the quality of supervisory practices will be measured.

- **Agreement:** `not_applicable` — No sample asks how supervisory quality is measured, and the exc-supervision cell passed with 2 of 3 members, its members listing annual progress reports and feedback questionnaires among the structure they rate adequate. The lane read the one sentence that answers the question and judged it sufficient (A09).
- **Uncertainty:** As with ESR-E-07, the miss stands and the open question is how a calibration disagreement should be counted.
- **Recommendation:** `adjudicated`
- **Decision:** Taken with ESR-E-07; one decision covers both.

## 11. ESR-I-S01 — strength, `independently_detected`

> Non-academic sector contribution to doctoral training is well described and compelling; they have a meaningful and tangible role through structured secondments in hospitals, SMEs, and regulatory bodies, ensuring hands-on exposure to clinical workflows, compliance, and innovation. Industry and regulatory partners actively co-supervise doctoral candidates (DCs), participate the Individual Training Panels, and the Supervisory Board, and lead network-wide training sessions.

- **Agreement:** `agreed` — Three criterion strengths name the structured secondments, the non-academic co-supervision and the Supervisory Board and ITP roles, and the imp-structuring cell passes 3/3. Those are the ESR's own examples.
- **Uncertainty:** Two samples add an arithmetic contradiction the evaluators did not record: section 2.1 claims at least 80% of secondment months in non-academic settings, while the DC table sums to about 74% and DC7 shows ten secondment months with none non-academic. That is computed from the appendix table as this copy carries it.
- **Recommendation:** `revisit_after_declaration`
- **Decision:** Confirm the appendix secondment months in this copy are the submission's. If they are, decide whether the 80% contradiction enters the R05 revision plan as a correction the ESR did not ask for.

## 12. ESR-I-S02 — strength, `independently_detected`

> Several elements are convincingly sustained after the project; these include e.g. the development of a virtual knowledge hub. The robust strategies and mechanisms described ensure a sustained long-term collaboration, and foster future international and intersectoral research and cooperation.

- **Agreement:** `agreed` — Three criterion strengths name the knowledge hub, the ECTS integration, the alumni hub and the Innovation and Sustainability Committee. The ESR names the virtual knowledge hub and the sustained long-term collaboration.
- **Uncertainty:** Two samples fault the post-project funding plan as a list of programme names. The ESR does not fault it. The finding is about a different sentence of 2.1 than the praise rests on.
- **Recommendation:** `retain`
- **Decision:** Decide whether the post-project funding plan is revised in R05 even though the ESR praised this aspect. A revision here is an improvement beyond the ESR, not a response to it.

## 13. ESR-I-S04 — strength, `partially_observable`

> The dissemination, exploitation, and communication measures are comprehensive, and well-structured, with clear objectives and monitoring through measurable indicators. The target groups for these measures are clearly identified. The outline of intellectual property management strategy is mostly appropriately addressed.

- **Agreement:** `unresolved` — The ESR credits clear objectives, measurable indicators and clearly identified target groups. Four samples fault the communication plan for having no audience segmentation and no communication indicators, and the imp-dissemination cell fails 2 of 3. The readings contradict each other on the same sub-section.
- **Uncertainty:** The register measures zero images on any page and records every figure lost. A dissemination table or figure of target groups and indicators is exactly what that loss removes, so the cell failure may be an artifact of the copy.
- **Recommendation:** `revisit_after_private_network`
- **Decision:** Confirm whether 2.3 carried a target-group or indicator table or figure in the submission. The failing cell is the only one of three in impact, so this answer changes how the impact score difference is read.

## 14. ESR-I-S05 — strength, `independently_detected`

> The expected scientific impact is highly credible with clear breakthroughs in causal modelling. For example, the integration of regulatory-grade pipelines aligned with regulatory frameworks adds robustness. Indicators, such as cross-site transportability, make the scientific outcomes measurable and realistic. Societal impact is well-justified: effective and safe integration of AI in healthcare and regulatory frameworks will largely affect the quality of the cardiovascular care provided to patients, and is addressing patient benefit, healthcare-system resilience, and policy uptake.

- **Agreement:** `agreed` — Two criterion strengths credit the scientific, economic and societal pathways as distinct and coherent, which is the ESR's 'highly credible' and 'well-justified'. The cross-site transportability indicator the ESR names survives in the copy.
- **Uncertainty:** Two samples contest the societal half: no evaluation mechanism ties training outputs to health-system outcomes, and the societal claims carry no endpoints. The ESR praises the societal justification, so the contest and the praise are about the same passage.
- **Recommendation:** `retain`
- **Decision:** Decide whether the societal-impact indicator gap enters the R05 revision plan. ESR-I-02 already asks for magnitude on the economic and technological pathways; extending it to the societal pathway goes beyond the ESR.

## 15. ESR-Q-01 — shortcoming, `partially_observable`

> However, several aspects lack appropriate detail such as the description of dependencies between work packages.

- **Agreement:** `disputed` — Two of the three cited findings carry the ESR's point: dependencies and critical-path logic are not mapped beyond narrative cross-references, and no Gantt or dependency diagram is shown. The third is withdrawn: it states that no intermediate milestones are shown, and the implementation section the assessor received carries the milestones table with a due month for each of 16 milestones (A05, A11).
- **Uncertainty:** The register measures zero images on any page, so a Gantt or dependency figure in the submission would have been lost. That is why the row is partial and not detected, and it is a question for the private-network review, not for this copy.
- **Recommendation:** `adjudicated`
- **Decision:** Confirm the withdrawal of the sample-0 citation. The dependency point stands on the other two findings and the disposition partially_observable does not change.

## 16. ESR-Q-02 — shortcoming, `not_detected_despite_sufficient_preserved_evidence`

> In addition, the validation strategy for certain deliverables is not fully specified

- **Agreement:** `not_applicable` — No sample or cell asks how deliverables are validated. R03 found the cause: four of the five implementation samples attribute verification means to the deliverables and milestones tables jointly, while only the milestones table carries that column. The lane credited one table with the other's property and never asked the question (A10).
- **Uncertainty:** The absence is readable from the copy, which is why the row counts against the lane. The application form asks for no validation column, so the ESR's point is one of substance rather than form compliance.
- **Recommendation:** `adjudicated`
- **Decision:** Confirm that the misattribution is reported to the assessor's own account in PE-09, with A05, as a lane defect rather than a scoring disagreement.

## 17. ESR-Q-03 — shortcoming, `independently_detected`

> and the definitions and timing of some milestones is not well aligned with the overall proposal.

- **Agreement:** `disputed` — Of the four cited findings, one survives. The blind citation is withdrawn (A05). The two undeclared-dependency findings rest on no sourced requirement: the milestones table the application form fixes has no dependency column (A03). The M7.3 window finding stands and matches the ESR's point on timing: a milestone due M48 related to a package the copy itself declares as M1-M36 (A04).
- **Uncertainty:** What the gap means is not settled. M7.3 is the submission of a follow-up proposal, which a consortium may intend after the funded period, and the copy declares no project duration against which M48 could be placed. Tier 2B holds no extract for this call.
- **Recommendation:** `adjudicated`
- **Decision:** Two decisions. First, confirm that detected_by narrows to the integrity audit and the citations narrow from four findings to one, or move the row to partially_observable because no finding addresses the definitions of the milestones. Second, decide whether M7.3 after the work plan ends is a misalignment to correct or an intentional commitment to move out of the milestone table.

## 18. ESR-Q-S02 — strength, `partially_observable`

> The participating organisations have the required high-quality infrastructure and capacity to implement research of high quality and their tasks. The international consortium is well-structured, integrating academic and non-academic partners with expertise, complementary strengths, and interdisciplinary knowledge, matching with the project's objectives, and reinforcing the structural and functional capability of the Doctoral Network.

- **Agreement:** `unresolved` — The infrastructure-to-WP mapping and the three-axis complementarity argument the ESR praises are named as strengths in every sample, and the impl-participants cell passes 3/3. Three samples contest the capacity claims as generic institutional boilerplate without track record, which the ESR calls high-quality infrastructure and capacity.
- **Uncertainty:** The register records identifiers generalised, and section 8 reaches this copy as unnamed 'Academic Beneficiary A-I' profiles across 28,087 characters. Prior grants, named facilities and publication records are what that generalisation removes.
- **Recommendation:** `revisit_after_private_network`
- **Decision:** Confirm whether section 8 carried track-record evidence in the submission. If it did, the three contesting findings describe the sanitisation and not the proposal.

## 19. ESR-Q-S03 — strength, `partially_observable`

> Hosting arrangements via accredited doctoral schools and international offices are credible and supportive.

- **Agreement:** `unresolved` — Four samples call the hosting arrangements generic, a single sentence on accredited doctoral schools and international offices. The ESR calls the same arrangements credible and supportive. One cell member reads the per-beneficiary profiles as tying named infrastructure to work packages.
- **Uncertainty:** Section 5, the network organisation, reaches this copy as 3,135 characters with identifiers generalised. Per-institution hosting detail the evaluators may have read there does not reach this copy, and the contest cannot be reconciled with the praise from what remains.
- **Recommendation:** `revisit_after_private_network`
- **Decision:** Confirm what section 5 carried in the submission. Then decide whether four findings against a point the evaluators called credible count as a lane disagreement or as a reading of a shortened section.

