# Operator review — the 29 ESR observations of msca-dn-2025-sanitised-v1

Generated: 2026-10-07T18:42:46.441115+00:00  
Review state: **agent_drafted_pending_operator_review**  
Drafted by: drafted in a Claude Code session, 2026-10-07: the R02 rows unchanged except the seven R03 adjudicated, whose basis now cites the adjudication record. Every row is still a provisional reading for operator review and none records an operator decision  
Adjudications: `docs/tier4_orchestration_state/msca_dn/esr/semantic_adjudications_f60ae6e0a2a1.json`  
Ticket: R02 of `plans/pe08_review_and_pe09_handoff_tickets.md`

Every recommendation, uncertainty and proposed revision in this report is agent-drafted and provisional. None of it is an operator decision, and nothing here records one.

The R02 record stays as written and the report rendered from it stays as written. This file is the R03 reading of the same comparison: seven rows carry recommendation 'adjudicated', the reasoning behind each lives in the adjudication record, and no disposition is changed here. A recommended change is still a question for the operator.

This report reads the committed PE-08 comparison. It changes no disposition, writes no revision and calls no assessor. Every reference below was resolved again, against the artifact the comparison names, before this file was written.

Advisory to a human, never run-blocking (`harness/HARNESS.md`): this report evaluates no gate and blocks no phase. Its inputs carry `advisory: true` and `blocking: false`, and so do the review notes it rests on.

## 1. Inputs

| Role | Path | sha256 (or content hash) | Note |
|---|---|---|---|
| comparison report | `docs/tier4_orchestration_state/msca_dn/comparisons/comparison_f60ae6e0a2a1_0001.json` | `9732dde500397981…` | the PE-08 output this review reads; not modified |
| ESR record | `docs/tier4_orchestration_state/msca_dn/esr/msca-dn-2025-esr.json` | `2c880e6cbe5a40c8…` | the historical evaluation summary, verbatim; the observation id set is its own |
| dispositions | `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1.json` | `5c0da82c111582d8…` | the declared half of the comparison, drafted by Claude and under review here |
| frozen blind baseline | `docs/tier4_orchestration_state/msca_dn/baselines/resolved_fixes_2026-10-06/blind_baseline_f60ae6e0a2a1.json` | `f60ae6e0a2a1ddcd…` | assessor claude-sonnet-5@claude-cli-subscription@2026-10-06; no new assessor call was made |
| candidate | `docs/tier4_orchestration_state/msca_dn/audit/candidates/MSCA-DN-2025_sanitised_part_b@b51a103520b58ded` | sha256:242f1afb02c8a0acd2c6a1d2178a9904ebcbf2b9f332c92672f849f61088dbdc | the materialised sanitised copy every quote below is checked against |
| historical candidate | `docs/tier4_orchestration_state/msca_dn/audit/candidates/MSCA-DN-2025_sanitised_part_b@bdb8670f6987e4db` | sha256:13ad3ad81d7ee231b1e09922c9d74268dddb3cd43ed819f72bf757e01d2dd355 | the earlier sanitised copy; historical quotes resolve here |
| fidelity register | `docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register_resolved_fixes.json` | `aafed265f4e9b43b…` | the register this comparison binds; the derived half is measured and the declared half is the operator's (ticket R01). Another revision's register, where one exists, is not an input of this report |
| integrity audit | `docs/tier4_orchestration_state/msca_dn/audit/integrity_242f1afb02c8_0001.json` | `8d81965489e36c1d…` | over candidate sha256:242f1afb02c8 |
| integrity audit | `docs/tier4_orchestration_state/msca_dn/audit/integrity_13ad3ad81d7e_0001.json` | `1b66a7cc0823b8e1…` | over candidate sha256:13ad3ad81d7e |
| review notes | `docs/tier4_orchestration_state/msca_dn/esr/review_notes_f60ae6e0a2a1_r03.json` | `37c4797249f67ad3…` | the declared half of this report |
| semantic adjudications | `docs/tier4_orchestration_state/msca_dn/esr/semantic_adjudications_f60ae6e0a2a1.json` | `354db83d36727c05…` | the reasoning behind every row this review reports as adjudicated |

Each hash above was recomputed from the file on disk. A mismatch refuses the report. The assessor pin is `claude-sonnet-5@claude-cli-subscription@2026-10-06`; no assessor ran for this review.

## 2. Counts

Of the 15 rows the comparison calls `independently_detected`, 9 are strengths the blind lane praised as the evaluators did and 6 are criticisms it caught. The two are counted apart below.

The ESR records **29 observations**: **15 criticisms** (8 shortcomings, 7 minor shortcomings) and **14 strengths**.

### Criticisms

| Disposition | Shortcomings | Minor | All criticisms | What it means here |
|---|---|---|---|---|
| `independently_detected` | 2 | 4 | 6 | a blind or audit finding names the same point |
| `partially_observable` | 2 | 0 | 2 | part of the point was found, or the copy preserves part of the evidence |
| `not_assessable_from_this_copy` | 1 | 0 | 1 | sanitisation removed the evidence; never counted as a failure |
| `not_detected_despite_sufficient_preserved_evidence` | 3 | 3 | 6 | the evidence is preserved and no finding names it |
| `addressed` | 0 | 0 | 0 | the assessed revision no longer exhibits the point |

### Strengths

| Disposition | Count |
|---|---|
| `independently_detected` | 9 |
| `partially_observable` | 5 |

**8** of the 14 strengths carry a blind finding that contests the praised point.

### Lane attribution

These buckets are exclusive: a row both lanes found is counted once, under `both lanes`. The comparison's own `summary.detection.by_lane` counts membership instead, so its integrity-audit figure includes that row.

| Lane | Criticisms | Strengths |
|---|---|---|
| blind lane only | 7 | 14 |
| integrity audit only | 0 | 0 |
| both lanes | 1 | 0 |
| neither lane | 7 | 0 |

Criterion scores are compared in the comparison artifact and are not re-interpreted here. No deduction is attributed to any individual criticism.

## 3. Decisions required

19 of 29 rows need an operator decision. The full question is repeated in each row below, and alone in the companion decisions file.

| # | Observation | Agreement | Recommendation | Decision |
|---|---|---|---|---|
| 1 | `ESR-E-01` | agreed | retain | Confirm that splitting one ESR sentence into ESR-E-01 and ESR-E-02 is intended. It is the only such split, and it puts one sentence on both sides of the detection count. |
| 2 | `ESR-E-02` | not_applicable | revisit_after_declaration | Decide whether a miss may be counted against the lane on Assumed preservation. If the R04 declaration for 1.2 cannot say the security content is no thinner than the submission's, this row belongs in 'partially observable' or 'not assessable'. |
| 3 | `ESR-E-03` | not_applicable | adjudicated | Confirm that the measurement closes R02's open question and that the row stands as a plain miss, with failure mode evidence_not_read recorded in A07. |
| 4 | `ESR-E-04` | disputed | adjudicated | The partial detection rests on no finding and the disposition cannot stay partially_observable. Choose not_detected_despite_sufficient_preserved_evidence, on the ground that the missing site and operator counts are readable from this copy, or not_assessable, on the ground that the register records rephrased prose for Task 4.3. |
| 5 | `ESR-E-05` | not_applicable | revisit_after_private_network | Confirm against the submitted original whether a registry or database passage with contributing clinicians existed, and whether sanitisation removed it. Until then this row carries no verdict on the lane. |
| 6 | `ESR-E-S03` | unresolved | revisit_after_private_network | Confirm whether the submission named repositories and preprint venues under 1.2. If it did, the blind contest is a sanitisation artifact and must not enter the revision plan as a weakness. |
| 7 | `ESR-E-07` | not_applicable | adjudicated | Decide whether a passage the lane cited approvingly counts against it in the same detection figure as a point it never reached. ESR-E-09 has the same shape; ESR-Q-02 has a third, recorded in A10. |
| 8 | `ESR-E-08` | not_applicable | revisit_after_declaration | Confirm in the R04 declaration for 1.3 and 2.2 that the entrepreneurship passages are preserved. On that confirmation this row is the cleanest of the six misses. |
| 9 | `ESR-E-S05` | unresolved | revisit_after_private_network | Confirm the supervisor track-record figures in this copy are the submission's. Then decide whether the uneven-track-record finding is a point the evaluators did not make, or an artifact of reading anonymised profiles. |
| 10 | `ESR-E-09` | not_applicable | adjudicated | Taken with ESR-E-07; one decision covers both. |
| 11 | `ESR-I-S01` | agreed | revisit_after_declaration | Confirm the appendix secondment months in this copy are the submission's. If they are, decide whether the 80% contradiction enters the R05 revision plan as a correction the ESR did not ask for. |
| 12 | `ESR-I-S02` | agreed | retain | Decide whether the post-project funding plan is revised in R05 even though the ESR praised this aspect. A revision here is an improvement beyond the ESR, not a response to it. |
| 13 | `ESR-I-S04` | unresolved | revisit_after_private_network | Confirm whether 2.3 carried a target-group or indicator table or figure in the submission. The failing cell is the only one of three in impact, so this answer changes how the impact score difference is read. |
| 14 | `ESR-I-S05` | agreed | retain | Decide whether the societal-impact indicator gap enters the R05 revision plan. ESR-I-02 already asks for magnitude on the economic and technological pathways; extending it to the societal pathway goes beyond the ESR. |
| 15 | `ESR-Q-01` | disputed | adjudicated | Confirm the withdrawal of the sample-0 citation. The dependency point stands on the other two findings and the disposition partially_observable does not change. |
| 16 | `ESR-Q-02` | not_applicable | adjudicated | Confirm that the misattribution is reported to the assessor's own account in PE-09, with A05, as a lane defect rather than a scoring disagreement. |
| 17 | `ESR-Q-03` | disputed | adjudicated | Two decisions. First, confirm that detected_by narrows to the integrity audit and the citations narrow from four findings to one, or move the row to partially_observable because no finding addresses the definitions of the milestones. Second, decide whether M7.3 after the work plan ends is a misalignment to correct or an intentional commitment to move out of the milestone table. |
| 18 | `ESR-Q-S02` | unresolved | revisit_after_private_network | Confirm whether section 8 carried track-record evidence in the submission. If it did, the three contesting findings describe the sanitisation and not the proposal. |
| 19 | `ESR-Q-S03` | unresolved | revisit_after_private_network | Confirm what section 5 carried in the submission. Then decide whether four findings against a point the evaluators called credible count as a lane disagreement or as a reading of a shortened section. |

## 4. The rows at a glance

`Refs` is how many references the row rests on; each one was resolved against the artifact it names, or this report would not have been written. The ESR closes each group of related points with one severity sentence, so rows in one cluster share a severity and none is invented per row.

| Observation | Criterion | Aspect | Kind | ESR cluster | Disposition | Lane | Refs | Agreement | Decision? |
|---|---|---|---|---|---|---|---|---|---|
| `ESR-E-S01` | excellence | exc-obj | strength | — | independently_detected | blind lane only | 4 | agreed | no |
| `ESR-E-S02` | excellence | exc-method | strength | — | independently_detected | blind lane only | 3 | agreed | no |
| `ESR-E-01` | excellence | exc-method | shortcoming | ESR-C1 (shortcoming, 5 observations) | independently_detected | blind lane only | 9 | agreed | yes |
| `ESR-E-02` | excellence | exc-method | shortcoming | ESR-C1 (shortcoming, 5 observations) | not_detected_despite_sufficient_preserved_evidence | neither lane | 5 | not_applicable | yes |
| `ESR-E-03` | excellence | exc-method | shortcoming | ESR-C1 (shortcoming, 5 observations) | not_detected_despite_sufficient_preserved_evidence | neither lane | 6 | not_applicable | yes |
| `ESR-E-04` | excellence | exc-method | shortcoming | ESR-C1 (shortcoming, 5 observations) | partially_observable | blind lane only | 6 | disputed | yes |
| `ESR-E-05` | excellence | exc-method | shortcoming | ESR-C1 (shortcoming, 5 observations) | not_assessable_from_this_copy | neither lane | 2 | not_applicable | yes |
| `ESR-E-06` | excellence | exc-method | minor_shortcoming | ESR-C2 (minor_shortcoming) | independently_detected | blind lane only | 9 | agreed | no |
| `ESR-E-S03` | excellence | exc-method | strength | — | partially_observable | blind lane only | 6 | unresolved | yes |
| `ESR-E-S04` | excellence | exc-training | strength | — | independently_detected | blind lane only | 4 | agreed | no |
| `ESR-E-07` | excellence | exc-training | minor_shortcoming | ESR-C3 (minor_shortcoming, 2 observations) | not_detected_despite_sufficient_preserved_evidence | neither lane | 4 | not_applicable | yes |
| `ESR-E-08` | excellence | exc-training | minor_shortcoming | ESR-C3 (minor_shortcoming, 2 observations) | not_detected_despite_sufficient_preserved_evidence | neither lane | 4 | not_applicable | yes |
| `ESR-E-S05` | excellence | exc-supervision | strength | — | partially_observable | blind lane only | 7 | unresolved | yes |
| `ESR-E-09` | excellence | exc-supervision | minor_shortcoming | ESR-C4 (minor_shortcoming) | not_detected_despite_sufficient_preserved_evidence | neither lane | 2 | not_applicable | yes |
| `ESR-I-S01` | impact | imp-structuring | strength | — | independently_detected | blind lane only | 6 | agreed | yes |
| `ESR-I-S02` | impact | imp-structuring | strength | — | independently_detected | blind lane only | 5 | agreed | yes |
| `ESR-I-S03` | impact | imp-career | strength | — | independently_detected | blind lane only | 4 | agreed | no |
| `ESR-I-S04` | impact | imp-dissemination | strength | — | partially_observable | blind lane only | 9 | unresolved | yes |
| `ESR-I-01` | impact | imp-dissemination | minor_shortcoming | ESR-C5 (minor_shortcoming) | independently_detected | blind lane only | 7 | agreed | no |
| `ESR-I-S05` | impact | imp-magnitude | strength | — | independently_detected | blind lane only | 4 | agreed | yes |
| `ESR-I-02` | impact | imp-magnitude | minor_shortcoming | ESR-C6 (minor_shortcoming) | independently_detected | blind lane only | 8 | agreed | no |
| `ESR-Q-S01` | implementation | impl-workplan | strength | — | independently_detected | blind lane only | 5 | agreed | no |
| `ESR-Q-01` | implementation | impl-workplan | shortcoming | ESR-C7 (shortcoming, 3 observations) | partially_observable | blind lane only | 10 | disputed | yes |
| `ESR-Q-02` | implementation | impl-workplan | shortcoming | ESR-C7 (shortcoming, 3 observations) | not_detected_despite_sufficient_preserved_evidence | neither lane | 4 | not_applicable | yes |
| `ESR-Q-03` | implementation | impl-workplan | shortcoming | ESR-C7 (shortcoming, 3 observations) | independently_detected | both lanes | 8 | disputed | yes |
| `ESR-Q-04` | implementation | impl-workplan | minor_shortcoming | ESR-C8 (minor_shortcoming) | independently_detected | blind lane only | 7 | agreed | no |
| `ESR-Q-S02` | implementation | impl-participants | strength | — | partially_observable | blind lane only | 9 | unresolved | yes |
| `ESR-Q-S03` | implementation | impl-participants | strength | — | partially_observable | blind lane only | 7 | unresolved | yes |
| `ESR-Q-S04` | implementation | impl-participants | strength | — | independently_detected | blind lane only | 4 | agreed | no |

## 5. The two groups the ticket asks to highlight

### The alleged misses (6)

A miss is counted against the lane only where the copy preserves the evidence. The preservation of that evidence is a declaration, not a measurement, which is why each row names the status it rests on.

| Observation | ESR complains of | Preservation status | Agreement | Decision |
|---|---|---|---|---|
| `ESR-E-02` | both | Assumed | not_applicable | Decide whether a miss may be counted against the lane on Assumed preservation. If the R04 declaration for 1.2 cannot say the security content is no thinner than the submission's, this row belongs in 'partially observable' or 'not assessable'. |
| `ESR-E-03` | both | Assumed | not_applicable | Confirm that the measurement closes R02's open question and that the row stands as a plain miss, with failure mode evidence_not_read recorded in A07. |
| `ESR-E-07` | inadequately_explained | Assumed | not_applicable | Decide whether a passage the lane cited approvingly counts against it in the same detection figure as a point it never reached. ESR-E-09 has the same shape; ESR-Q-02 has a third, recorded in A10. |
| `ESR-E-08` | absent_detail | Assumed | not_applicable | Confirm in the R04 declaration for 1.3 and 2.2 that the entrepreneurship passages are preserved. On that confirmation this row is the cleanest of the six misses. |
| `ESR-E-09` | inadequately_explained | Assumed | not_applicable | Taken with ESR-E-07; one decision covers both. |
| `ESR-Q-02` | absent_detail | Assumed | not_applicable | Confirm that the misattribution is reported to the assessor's own account in PE-09, with A05, as a lane defect rather than a scoring disagreement. |

### The contested strengths (8)

The evaluators praised the point and the blind lane faulted it. Either the blind lane is right and the evaluators were generous, or the evidence that earned the praise did not survive sanitisation. The register says which is possible; only the original says which is true.

| Observation | Disposition | Agreement | Decision |
|---|---|---|---|
| `ESR-E-S03` | partially_observable | unresolved | Confirm whether the submission named repositories and preprint venues under 1.2. If it did, the blind contest is a sanitisation artifact and must not enter the revision plan as a weakness. |
| `ESR-E-S05` | partially_observable | unresolved | Confirm the supervisor track-record figures in this copy are the submission's. Then decide whether the uneven-track-record finding is a point the evaluators did not make, or an artifact of reading anonymised profiles. |
| `ESR-I-S01` | independently_detected | agreed | Confirm the appendix secondment months in this copy are the submission's. If they are, decide whether the 80% contradiction enters the R05 revision plan as a correction the ESR did not ask for. |
| `ESR-I-S02` | independently_detected | agreed | Decide whether the post-project funding plan is revised in R05 even though the ESR praised this aspect. A revision here is an improvement beyond the ESR, not a response to it. |
| `ESR-I-S04` | partially_observable | unresolved | Confirm whether 2.3 carried a target-group or indicator table or figure in the submission. The failing cell is the only one of three in impact, so this answer changes how the impact score difference is read. |
| `ESR-I-S05` | independently_detected | agreed | Decide whether the societal-impact indicator gap enters the R05 revision plan. ESR-I-02 already asks for magnitude on the economic and technological pathways; extending it to the societal pathway goes beyond the ESR. |
| `ESR-Q-S02` | partially_observable | unresolved | Confirm whether section 8 carried track-record evidence in the submission. If it did, the three contesting findings describe the sanitisation and not the proposal. |
| `ESR-Q-S03` | partially_observable | unresolved | Confirm what section 5 carried in the submission. Then decide whether four findings against a point the evaluators called credible count as a lane disagreement or as a reading of a shortened section. |

## 6. The observations

### ESR-E-S01 — excellence / exc-obj

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 1.1

**ESR text (verbatim):**

> The proposal presents clear objectives to develop AI-technologies for cardiovascular healthcare, with concrete measures that make them overall verifiable and achievable within the project's timeframe. The individual projects of the recruited researchers are appropriately articulated and convincingly integrated to support and strengthen the coherent outcomes of the research programme. The project goes beyond the state of the art in cardiovascular care and it is ambitious.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Every criterion sample lists the four-pillar architecture and the nine integrated DC projects as strengths, and the exc-obj cell passes 3/3 with the 'Beyond the state of the art' subsection named. The blind lane praises the same points the evaluators praised. Its shortcomings on the KPIs (process counts, no comparators) do not contradict the ESR, which calls the objectives 'overall verifiable'.

**Findings, as resolved:**

- blind lane · criterion_strength · excellence sample 0 #0
  > Clear four-pillar architecture (Trustworthiness, Interoperability, Awareness, Clinical adaptation) coherently links objectives O1-O4, methodology, training and the nine DC projects
- blind lane · criterion_strength · excellence sample 0 #6
  > Nine DC projects are individually well-specified with objectives, expected results, secondments and explicit contribution to the network, giving a credible, non-generic research programme
- blind lane · criterion_strength · excellence sample 3 #0
  > Four-pillar architecture (Trustworthiness, Interoperability, Awareness, Clinical Adaptation) gives a coherent, well-structured and ambitious research programme with explicit, measurable KPIs for each objective.
- blind lane · cell · exc-obj
  > majority over n=3; passed=True (3 true / 0 false, agreement 100%); mean score=0.760

**Reference check (measured):**

- resolved: 4 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 4 of 4 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** Three criterion strengths name the four-pillar architecture linking O1-O4 and the nine individually specified DC projects, which are the two things the ESR praises. The exc-obj cell passes 3/3. No finding contests the objectives.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-E-S02 — excellence / exc-method

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 1.2

**ESR text (verbatim):**

> Overall, the methodology is clearly described, including the underlying concepts and models are mostly detailed. Several aspects of interdisciplinary approaches are coherent, and well-integrated to carry out the objectives of the proposal.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> The methodology's closed-loop pipeline and its discipline integration are listed as strengths in four of five samples and the exc-method cell passes 3/3 at the highest cell score of the report (0.79). The blind lane's 'conceptual level' shortcomings are the ESR's own next sentence (ESR-E-01), not a contradiction of this strength.

**Findings, as resolved:**

- blind lane · criterion_strength · excellence sample 3 #2
  > Methodology explicitly integrates computer science, clinical science, regulatory/legal expertise and social science across work packages, with a defined closed-loop causal-to-assurance pipeline applied consistently.
- blind lane · criterion_strength · excellence sample 4 #2
  > Well-specified closed-loop methodological pipeline integrating causal inference, federated/privacy-preserving learning, and clinical evaluation across disciplines
- blind lane · cell · exc-method
  > majority over n=3; passed=True (3 true / 0 false, agreement 100%); mean score=0.793

**Reference check (measured):**

- resolved: 3 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 3 of 3 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** Two criterion strengths name the closed-loop pipeline and the integration of computer science, clinical, regulatory and social science across work packages. That is the ESR's 'methodology clearly described' and 'interdisciplinary approaches coherent'. The exc-method cell is the report's highest at 0.79.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-E-01 — excellence / exc-method

**Kind:** shortcoming · **ESR severity cluster:** ESR-C1 (shortcoming, 5 observations) · **Proposal location:** 1.2

**ESR text (verbatim):**

> However, AI/ML plans- specifically conceptual paradigms, methods, and validation metrics, as well as critical security aspects for handling clinical data with AI are insufficiently detailed.
>
> Together, these constitute a shortcoming.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> All five criterion samples say the causal-AI methodology stays at pipeline level without named techniques, estimators or validation metrics. That is the ESR's first clause (conceptual paradigms, methods, validation metrics). The quoted passage is the pipeline the blind lane describes; the copy preserves it in full.

**Findings, as resolved:**

- blind lane · criterion_shortcoming · excellence sample 1 #1
  > The causal-AI and identifiability methodology is described at a conceptual/pipeline level (Causal Question→Identifiability→...) without naming specific causal-inference techniques, estimators or validation metrics to be used
- blind lane · criterion_shortcoming · excellence sample 0 #2
  > Methodological pipeline (Causal Question→...→Assurance) is presented schematically without technical detail on identifiability strategy, choice of causal estimators, or how selection diagrams will be operationalised
- blind lane · criterion_shortcoming · excellence sample 2 #1
  > Methodology section remains largely programmatic/generic (e.g., 'causal AI', 'federated learning', 'sensitivity analysis') without naming specific technical frameworks, estimators or identification strategies that would demonstrate methodological rigor beyond stated intentions
- blind lane · criterion_shortcoming · excellence sample 3 #7
  > The causal methodology pipeline (Causal Question → ... → Assurance) is stated at a high level without specifying the causal-identification frameworks, estimators, or statistical validation procedures to be used.
- blind lane · criterion_shortcoming · excellence sample 4 #3
  > Methodology section stays at a conceptual/framework level (causal question → identifiability → federated prep → model → evaluation → assurance) without specifying concrete causal-inference techniques, identification strategies, or statistical validation methods

**Candidate passages (quote verified in the named sub-section):**

- `excellence_section` / `1.2`
  > The resulting closed-loop methodology follows the sequence:
- `excellence_section` / `1.2`
  > and is consistently applied across all research projects and healthcare use cases.

**The same passages in the earlier sanitised copy:** 2 quote(s), verified.

**Reference check (measured):**

- resolved: 5 blind finding(s), 0 audit finding(s), 2 candidate quote(s), 2 historical quote(s), 0 register entr(ies) — 9 of 9 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** All five criterion samples fault the causal-AI methodology for naming no techniques, estimators or validation metrics. That is the first clause of the ESR sentence, word for word in substance.
- **The ESR complains of:** `inadequately_explained`
- **Uncertainty:** This observation and ESR-E-02 carry the same ESR sentence: the operator's transcription split one sentence into its AI/ML clause and its security clause. The blind lane covers the first clause only, so the sentence counts once as detected and once as missed. Every other observation has text of its own.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** Confirm that splitting one ESR sentence into ESR-E-01 and ESR-E-02 is intended. It is the only such split, and it puts one sentence on both sides of the detection count.

**Proposed revision (drafted, declared Assumed):**

> Under 1.2, add one paragraph per pipeline stage naming the identification strategy, the estimators and the validation metrics each DC project will use, with the retrospective cohort it applies to. Prefer a table: stage, method, metric, DC.

---

### ESR-E-02 — excellence / exc-method

**Kind:** shortcoming · **ESR severity cluster:** ESR-C1 (shortcoming, 5 observations) · **Proposal location:** 1.2

**ESR text (verbatim):**

> However, AI/ML plans- specifically conceptual paradigms, methods, and validation metrics, as well as critical security aspects for handling clinical data with AI are insufficiently detailed.
>
> Together, these constitute a shortcoming.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> The methodology sub-section is present and carries only passing references to data protection; no passage describes security measures for clinical data handled by AI, which is what the ESR found insufficient. No blind shortcoming or cell rationale names security. The register records prose as 'some passages omitted or rephrased', so the preservation of this gap is declared, not measured: a security passage may have been removed, but the ESR says the submission itself lacked detail, so the copy cannot have less than the evaluators saw in kind.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `excellence_section` / `1.2`
  > Open science is implemented within the constraints imposed by medical-data protection and high-risk AI governance.
- `excellence_section` / `1.2`
  > data-protection regulations.

**The same passages in the earlier sanitised copy:** 2 quote(s), verified.

**Fidelity register entries the row rests on:**

- `provenance/transformation/prose` = "some passages omitted or rephrased"

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 2 candidate quote(s), 2 historical quote(s), 1 register entr(ies) — 5 of 5 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Inferred)
- **Basis:** No blind sample, cell rationale or audit check names security of clinical data, so there is no finding whose proposition could agree or disagree. The copy carries two passing references to data protection and no security passage.
- **The ESR complains of:** `both`
- **Uncertainty:** The disposition counts this as a miss on the ground that the ESR itself found the submission thin, so the copy cannot be thinner in kind. That is a reading of the ESR's wording, not a measurement: the register records prose 'some passages omitted or rephrased', so a security passage may have been removed. The preservation status is declared Assumed.
- **Recommendation:** `revisit_after_declaration`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Decide whether a miss may be counted against the lane on Assumed preservation. If the R04 declaration for 1.2 cannot say the security content is no thinner than the submission's, this row belongs in 'partially observable' or 'not assessable'.

**Proposed revision (drafted, declared Assumed):**

> Add a short 'Security of clinical data' paragraph under 1.2 (or 1.2's open science block): threat model, access control for federated nodes, encryption in transit and at rest, audit logging, and who owns incident response. Cross-reference the ethics self-assessment.

---

### ESR-E-03 — excellence / exc-method

**Kind:** shortcoming · **ESR severity cluster:** ESR-C1 (shortcoming, 5 observations) · **Proposal location:** 1.2, 1.1, 3.1

**ESR text (verbatim):**

> It is also not fully clear how some of the chosen methods will deliver key objectives: cardiovascular AI models are evaluated only retrospectively with limited plans for prospective validation;
>
> Together, these constitute a shortcoming.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> The copy states retrospective evaluation in the objectives, the WP4 tasks and the state-of-the-art section, and names no prospective validation beyond 'shadow-mode'. The blind lane did not raise the retrospective-only design in any sample, nor in the exc-method or impl-workplan cells. The evidence the ESR rested on is present in the copy.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `excellence_section` / `1.1`
  > Conduct retrospective evaluations across:
- `implementation_section` / `3.1`
  > Retrospective multicentre evaluation of multimodal causal AI models in structural heart disease.
- `excellence_section` / `1.1`
  > The programme performs healthcare-embedded case studies that progress from retrospective analyses toward shadow-mode and implementation-oriented evaluations.

**The same passages in the earlier sanitised copy:** 3 quote(s), verified.

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 3 candidate quote(s), 3 historical quote(s), 0 register entr(ies) — 6 of 6 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Confirmed)
- **Basis:** No finding raises the retrospective-only evaluation design, and R03 measured why: the frozen baseline never uses the words prospective, shadow or retrospective, in any of the 15 criterion samples or any of the 10 cells. The lane did not weigh the evaluation design and rate it adequate; it never reached the point (A07).
- **The ESR complains of:** `both`
- **Uncertainty:** None remains on this ground. R02 left open whether a lane reading the shadow-mode sentence as a prospective plan would be wrong; the measurement withdraws that reading, because no lane output mentions the design either way.
- **Recommendation:** `adjudicated`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Confirm that the measurement closes R02's open question and that the row stands as a plain miss, with failure mode evidence_not_read recorded in A07.

**Proposed revision (drafted, declared Assumed):**

> State a prospective validation plan for at least one cardiovascular use case: a shadow-mode or silent-trial design with pre-registered endpoints, the site(s), the month window and the DC responsible, and say why the other use cases stay retrospective.

---

### ESR-E-04 — excellence / exc-method

**Kind:** shortcoming · **ESR severity cluster:** ESR-C1 (shortcoming, 5 observations) · **Proposal location:** 3.1, 1.2

**ESR text (verbatim):**

> the cohort is not sufficient concerning the multihospital, multi-operator design needed to reflect contemporary European TAVI practice to capture the diversity;
>
> Together, these constitute a shortcoming.

**Disposition:** `partially_observable` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> One sample states that feasibility details for the clinical cohorts, TAVI included, such as sample sizes are not specified. The ESR's point is narrower: a multihospital, multi-operator design for contemporary European TAVI practice. No finding names the site or operator dimension, so part of the point was found. Task 4.3 says 'multicentre' and lists data sources but no cohort size, number of sites or operators; the register records prose omitted or rephrased, so whether the submission said more about the cohort is not measurable here.

**Findings, as resolved:**

- blind lane · criterion_shortcoming · excellence sample 0 #3
  > Feasibility details for the clinical cohorts (ALS, TAVI, HF, critical care) such as sample sizes, data access timelines or power considerations are not specified

**Candidate passages (quote verified in the named sub-section):**

- `implementation_section` / `3.1`
  > Task 4.3 – AI Implementation for Transcatheter Aortic Valve Implantation (TAVI)
- `implementation_section` / `3.1`
  > Data sources include:

**The same passages in the earlier sanitised copy:** 2 quote(s), verified.

**Fidelity register entries the row rests on:**

- `provenance/transformation/prose` = "some passages omitted or rephrased"

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 2 candidate quote(s), 2 historical quote(s), 1 register entr(ies) — 6 of 6 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `disputed` (declared Inferred)
- **Basis:** The one cited finding names sample sizes, data-access timelines and power. The ESR's point is a multihospital, multi-operator design. Cohort magnitude and cohort composition are different properties, and no sample or cell names a site count, an operator count or representativeness, so the citation does not support the ESR's proposition (A06).
- **The ESR complains of:** `absent_detail`
- **Uncertainty:** Task 4.3 survives, says multicentre and gives no counts, so the gap is readable from this copy. The register records prose omitted or rephrased for this task, which is the only ground for calling the row unmeasurable instead.
- **Recommendation:** `adjudicated`, disposition `not_detected_despite_sufficient_preserved_evidence` (**a change from the comparison**)
- **Operator decision required:** The partial detection rests on no finding and the disposition cannot stay partially_observable. Choose not_detected_despite_sufficient_preserved_evidence, on the ground that the missing site and operator counts are readable from this copy, or not_assessable, on the ground that the register records rephrased prose for Task 4.3.

**Proposed revision (drafted, declared Assumed):**

> Give Task 4.3 its cohort: number of hospitals and countries, number of operators and procedures per site, the years covered, and how site and operator heterogeneity enter the causal model as variables.

---

### ESR-E-05 — excellence / exc-method

**Kind:** shortcoming · **ESR severity cluster:** ESR-C1 (shortcoming, 5 observations) · **Proposal location:** 1.2, 1.1

**ESR text (verbatim):**

> and the number of contributing clinicians to the database is not well-specified.
>
> Together, these constitute a shortcoming.

**Disposition:** `not_assessable_from_this_copy` (declared Assumed) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> The ESR refers to 'the database' and its contributing clinicians. The copy contains no passage describing a database with clinician contributors: the word does not occur in Part B. The referent was either generalised with the identifiers or omitted with the passages the register records as 'omitted or rephrased', so neither the blind lane nor a reader of this copy can assess the point. The closest blind finding (small clinician samples in KPIs) concerns KPI targets, not the database.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Fidelity register entries the row rests on:**

- `provenance/transformation/prose` = "some passages omitted or rephrased"
- `provenance/transformation/identifiers` = "generalised (project acronym, partner names, people, places)"

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 2 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Inferred)
- **Basis:** No finding names the database or its contributing clinicians, and the word does not occur in the copy's Part B. There is nothing in this copy for a finding to be about.
- **The ESR complains of:** `absent_detail`
- **Uncertainty:** Two causes of the absence cannot be told apart here: the referent was generalised away with the identifiers, or the submission introduced the database in a passage the register records as omitted. The disposition's 'not assessable from this copy' is the honest reading either way, and it is the only such row of the 29.
- **Recommendation:** `revisit_after_private_network`, disposition `not_assessable_from_this_copy` (unchanged)
- **Operator decision required:** Confirm against the submitted original whether a registry or database passage with contributing clinicians existed, and whether sanitisation removed it. Until then this row carries no verdict on the lane.

**Proposed revision (drafted, declared Assumed):**

> Where the registry or database is introduced, state the number of contributing clinicians and sites, their roles in data curation, and the governance of contributions. If the database was named in the submission, keep the passage.

---

### ESR-E-06 — excellence / exc-method

**Kind:** minor_shortcoming · **ESR severity cluster:** ESR-C2 (minor_shortcoming) · **Proposal location:** 1.2

**ESR text (verbatim):**

> Gender and other diversity characteristics relevant to this research are mostly appropriately considered in the research methodology as scientific variables (disaggregated data, subgroup calibration, bias mitigation), however, they are not detailed enough regarding their essential role in clinical issues in cardiology.
>
> This is a minor shortcoming.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> All five samples say the gender and diversity dimension is stated in general terms without concrete operational links to the cohorts or cardiology-specific issues, which is the ESR's point. The ESR also credits the variables approach; the blind strengths of sample 4 do the same.

**Findings, as resolved:**

- blind lane · criterion_shortcoming · excellence sample 0 #7
  > Gender/diversity dimension is described in general principle terms ('treated as scientific variables') without concrete operational links to the specific cohorts/datasets used
- blind lane · criterion_shortcoming · excellence sample 1 #4
  > Gender/diversity integration into causal graphs is asserted generically ('represented as potential causes, effects or mediators') without a concrete worked example or methodological protocol
- blind lane · criterion_shortcoming · excellence sample 2 #2
  > Gender/diversity dimension in methodology is described at a high level ('treated as scientific variables') without concrete analytic protocols or examples of how sex/gender will be operationalised in specific causal graphs
- blind lane · criterion_shortcoming · excellence sample 3 #6
  > Gender dimension in the methodology is treated mainly as a bias-detection variable; the training section's gender/diversity content is only briefly mentioned as a module topic without further elaboration.
- blind lane · criterion_shortcoming · excellence sample 4 #4
  > Gender/diversity dimension is described only generically ('treated as scientific variables', 'subgroup assessments') without concrete data sources, variables, or analysis protocols

**Candidate passages (quote verified in the named sub-section):**

- `excellence_section` / `1.2`
  > Sex, gender and additional diversity characteristics are treated as scientific variables.
- `excellence_section` / `1.2`
  > represented in causal structures as potential causes, effects or mediators,

**The same passages in the earlier sanitised copy:** 2 quote(s), verified.

**Reference check (measured):**

- resolved: 5 blind finding(s), 0 audit finding(s), 2 candidate quote(s), 2 historical quote(s), 0 register entr(ies) — 9 of 9 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** All five samples fault the gender and diversity dimension for being stated as a principle without operational links to the specific cohorts and datasets. That is the ESR's complaint that the consideration is not detailed enough for clinical issues in cardiology, and the cohorts in question are the cardiology cohorts.
- **The ESR complains of:** `inadequately_explained`
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

**Proposed revision (drafted, declared Assumed):**

> Add two or three cardiology-specific examples under 'Gender dimension and diversity aspects': sex differences in presentation and outcomes for the TAVI, heart-failure and critical-care cohorts, the variables available in each dataset, and the subgroup analyses planned.

---

### ESR-E-S03 — excellence / exc-method

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 1.2

**ESR text (verbatim):**

> Open science practices, such as preprints, and repositories, are included and adequately described in the proposed methodology.

**Disposition:** `partially_observable` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> One sample lists open science as concretely specified; three say no repositories, licences or governance are named. The ESR credits 'preprints, and repositories', which means the submission named them. The register records identifiers generalised and citations removed, so the names the evaluators saw are the kind of content sanitisation strips. The blind contest therefore rests in part on removed evidence and the strength is only partly observable here.

**Findings, as resolved:**

- blind lane · criterion_strength · excellence sample 0 #3
  > Open science practices are concretely specified (FAIR principles, persistent identifiers, reproducible workflows, 'as open as possible, as closed as necessary')
- blind lane · criterion_shortcoming · excellence sample 1 #5
  > Open-science commitments are stated at principle level ('as open as possible, as closed as necessary') without naming specific repositories, licences or governance for the synthetic datasets/software to be released
- blind lane · criterion_shortcoming · excellence sample 3 #5
  > Open-science commitment is generic ('as open as possible, as closed as necessary') without concrete data-sharing timelines, repositories, or licence commitments for the stated software/synthetic-dataset releases.
- blind lane · criterion_shortcoming · excellence sample 4 #5
  > Open science section lists FAIR principles and 'open as possible, closed as necessary' without naming repositories, licensing, or concrete data-sharing protocols

**Fidelity register entries the row rests on:**

- `provenance/transformation/identifiers` = "generalised (project acronym, partner names, people, places)"
- `provenance/transformation/citations` = "all removed; no bracketed numbers, author-year, DOIs, URLs or reference list"

**Reference check (measured):**

- resolved: 4 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 2 register entr(ies) — 6 of 6 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `unresolved` (declared Unresolved)
- **Basis:** The ESR credits open science practices 'such as preprints, and repositories', which means the submission named them. Three samples fault the commitments for naming no repositories, licences or governance. The two readings cannot both describe the same text.
- **Uncertainty:** The register records identifiers generalised and every citation removed. Named repositories and venues are the kind of content that sanitisation strips, so the contest may rest on evidence this copy lacks rather than on a weakness of the proposal.
- **Recommendation:** `revisit_after_private_network`, disposition `partially_observable` (unchanged)
- **Operator decision required:** Confirm whether the submission named repositories and preprint venues under 1.2. If it did, the blind contest is a sanitisation artifact and must not enter the revision plan as a weakness.

---

### ESR-E-S04 — excellence / exc-training

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 1.3

**ESR text (verbatim):**

> In general, a solid training framework with meaningful network-wide events - supporting well-structured scientific and transferable training - is described in the proposal. The training programme effectively integrates intersectoral and transferable skills through training schools, courses, conferences and secondments.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Four of five samples list the training programme (named events, TG1-TG6 mapping, triple-i) as a strength and the exc-training cell passes 3/3. Sample 0's shortcoming that the description is an events listing is a nuance the ESR shares in cluster C3.

**Findings, as resolved:**

- blind lane · criterion_strength · excellence sample 0 #4
  > Training programme operationalises TG1-TG6 via Personal Career Development Plans and a concrete table of seven network-wide events mapped to training goals
- blind lane · criterion_strength · excellence sample 2 #1
  > Detailed, specific and well-structured training programme with named network-wide events, TG1-TG6 mapping and triple-i (international/intersectoral/interdisciplinary) implementation
- blind lane · criterion_strength · excellence sample 3 #3
  > Training programme operationalises MSCA triple-i principles with six explicit training goals (TG1-6) mapped to work packages and a detailed, dated schedule of network-wide training events with clear content per day.
- blind lane · cell · exc-training
  > majority over n=3; passed=True (3 true / 0 false, agreement 100%); mean score=0.760

**Reference check (measured):**

- resolved: 4 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 4 of 4 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** Three criterion strengths name the TG1-TG6 mapping, the Personal Career Development Plans and the table of network-wide events, and the exc-training cell passes 3/3. That is the ESR's solid training framework with meaningful network-wide events.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-E-07 — excellence / exc-training

**Kind:** minor_shortcoming · **ESR severity cluster:** ESR-C3 (minor_shortcoming, 2 observations) · **Proposal location:** 1.3

**ESR text (verbatim):**

> While network-wide training overall complements the local training programmes, there is a slight limitation in clarity and depth in systematic description of complementation of local training.
>
> These constitute a minor shortcoming.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> The local-training paragraph survives in full under 1.3.4 and is the only place the copy relates local and network-wide training. The exc-training cell members read it as 'complementarity explicitly stated' and no sample faults its depth. The evaluators found the systematic description of complementation thin; the blind lane read the same paragraph and did not.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `excellence_section` / `1.3`
  > Wherever possible, these courses are made available on-site or online to DCs from other beneficiary institutions, thereby increasing efficiency and coherence.
- `excellence_section` / `1.3`
  > Local training at host organizations

**The same passages in the earlier sanitised copy:** 2 quote(s), verified.

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 2 candidate quote(s), 2 historical quote(s), 0 register entr(ies) — 4 of 4 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Confirmed)
- **Basis:** No finding faults the depth of the local-training description, and the exc-training cell passed with 3 of 3 members in agreement, its members stating that complementarity of network-wide and local programmes is explicitly stated. The lane read the paragraph the evaluators read and rated it sufficient (A08).
- **The ESR complains of:** `inadequately_explained`
- **Uncertainty:** The row is a miss either way: the lane produced no criticism. What is unsettled is whether a calibration disagreement of this kind belongs in the same figure as a point the lane never reached, such as ESR-E-03.
- **Recommendation:** `adjudicated`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Decide whether a passage the lane cited approvingly counts against it in the same detection figure as a point it never reached. ESR-E-09 has the same shape; ESR-Q-02 has a third, recorded in A10.

**Proposed revision (drafted, declared Assumed):**

> Add a short table under 1.3.4: for each host, the local doctoral-school modules each DC takes, the network-wide event that builds on them, and the ECTS or hours. One row per DC makes the complementation systematic.

---

### ESR-E-08 — excellence / exc-training

**Kind:** minor_shortcoming · **ESR severity cluster:** ESR-C3 (minor_shortcoming, 2 observations) · **Proposal location:** 1.3, 2.2

**ESR text (verbatim):**

> In addition, some details for training are not properly described, for example, the integration of entrepreneurship training lacks clear mechanisms for practical application.
>
> These constitute a minor shortcoming.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> Entrepreneurship training appears as a training goal (TG5), as a session topic led by non-academic partners and as a sentence under 2.2; none says how fellows apply it. No blind sample or cell names entrepreneurship. The passages the ESR judged are present.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `impact_section` / `2.2`
  > Training in IP protection, entrepreneurship, innovation management and the use of a Research-to-Innovation (R2I) canvas enables fellows to identify and articulate the scientific, technological and societal value of their work.
- `excellence_section` / `1.3`
  > TG5 – Innovation, entrepreneurship and impact

**The same passages in the earlier sanitised copy:** 2 quote(s), verified.

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 2 candidate quote(s), 2 historical quote(s), 0 register entr(ies) — 4 of 4 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Inferred)
- **Basis:** No blind sample and no cell rationale names entrepreneurship. The quoted passages show the TG5 goal and the 2.2 sentence survive, and neither says how a fellow applies the training.
- **The ESR complains of:** `absent_detail`
- **Uncertainty:** The missing thing is a mechanism, which is an absence the lane could have named from this copy. The preservation status is Assumed, as for every miss.
- **Recommendation:** `revisit_after_declaration`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Confirm in the R04 declaration for 1.3 and 2.2 that the entrepreneurship passages are preserved. On that confirmation this row is the cleanest of the six misses.

**Proposed revision (drafted, declared Assumed):**

> Give TG5 a mechanism: a business-case or R2I-canvas exercise per DC with a deliverable month, a pitch session at a named network event, and a mentor from an industrial partner. Say which deliverable records it.

---

### ESR-E-S05 — excellence / exc-supervision

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 1.4

**ESR text (verbatim):**

> The supervisors are experienced and highly qualified in their scientific roles. They demonstrate appropriate international and local experience across all relevant areas and facilitating the adequate and effective completion the individual research projects. The well-structured and multi-layered approach of supervision practices is solid and overall sound. It ensures effective progress monitoring, feedback and support for the fellows; for example, well-defined and reviewed Personal Career Development Plans ensure systematic tracking of training objectives.

**Disposition:** `partially_observable` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> The supervision structure (ITP, PCDP, Supervisory Board, escalation) is listed as a strength in every sample, matching the ESR's 'well-structured and multi-layered approach'. The supervisors' experience is contested: three samples call the profiles uneven or anonymised, and one cell member fails the cell. The register records identifiers generalised, so the profiles the evaluators read as 'experienced and highly qualified' reach this copy as 'Supervisor A-K' with no names, which is what the blind lane faults. The strength is observable for the structure and not for the people.

**Findings, as resolved:**

- blind lane · criterion_strength · excellence sample 2 #4
  > Supervision section provides quantifiable track-record evidence (H-index, publication counts, years and number of completed PhDs) and a concrete governance structure (ITP, PCDP, Supervisory Board, escalation procedure)
- blind lane · criterion_strength · excellence sample 4 #4
  > Supervision governance is detailed and procedurally sound: ITP, PCDP with 6-month review cycles, Supervisory Board oversight, and a two-step conflict-resolution escalation path
- blind lane · criterion_shortcoming · excellence sample 0 #4
  > Supervisor track records are uneven (e.g., H-index ~13-16 for some associate professors) for a network expected to deliver cutting-edge causal AI research
- blind lane · criterion_shortcoming · excellence sample 2 #4
  > Supervisor profiles are anonymised and generic (Supervisor A-K) with no explicit mapping to which DC each supervises, making it harder to verify fit-for-purpose supervision per project
- blind lane · criterion_shortcoming · excellence sample 4 #6
  > Supervisor quality is presented via anonymised/sanitised profile tables, limiting verifiable assessment of individual supervisory track records and co-supervision fit for each DC
- blind lane · cell_member · exc-supervision
  > The section provides concrete supervisor profiles (H-indices, publication counts, years of supervision, ongoing/completed PhDs) and a detailed, specific supervision structure (ITP, PCDP within 3 months reviewed every 6 months, 2-4 week supervisor meetings, biannual ITP meetings, Supervisory Board oversight, conflict-resolution escalation per span 1.4¶66-77), which goes beyond a bare assertion of 'experienced supervisors.' However, joint supervision is explicitly declared not mandatory (span 1.4¶78: 'the project is a standard Doctoral Network, not an Industrial or Joint Doctorate'), and the pack's claim ledger is withheld entirely, so grounding of these load-bearing supervision-experience and process claims is UNASSESSABLE rather than verified — per the rubric this must not be reported as a clean pass.

**Fidelity register entries the row rests on:**

- `provenance/transformation/identifiers` = "generalised (project acronym, partner names, people, places)"

**Reference check (measured):**

- resolved: 6 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 1 register entr(ies) — 7 of 7 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `unresolved` (declared Unresolved)
- **Basis:** The supervision structure the ESR calls well-structured and multi-layered is named as a strength in every sample, so that half agrees. The supervisors' experience is contested by three samples and by a failing cell member, which the ESR calls experienced and highly qualified.
- **Uncertainty:** Two of the contesting findings fault the anonymisation itself ('Supervisor A-K', no DC mapping), which is sanitisation and not a property of the submission. One faults H-index figures that did survive into this copy, so that part of the contest is readable here; whether those figures are the submission's own is a register question, since prose was omitted or rephrased.
- **Recommendation:** `revisit_after_private_network`, disposition `partially_observable` (unchanged)
- **Operator decision required:** Confirm the supervisor track-record figures in this copy are the submission's. Then decide whether the uneven-track-record finding is a point the evaluators did not make, or an artifact of reading anonymised profiles.

---

### ESR-E-09 — excellence / exc-supervision

**Kind:** minor_shortcoming · **ESR severity cluster:** ESR-C4 (minor_shortcoming) · **Proposal location:** 1.4

**ESR text (verbatim):**

> However, the description remains slightly generic on how the quality of supervisory practices will be measured.
>
> This is minor shortcoming.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> The one sentence on measuring supervisory quality survives. The exc-supervision cell members cite it as a strength (feedback questionnaires) and no sample asks how quality is measured. The evaluators found it generic; the blind lane did not.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `excellence_section` / `1.4`
  > Training and supervision quality are monitored through annual progress reports, PCDP updates and anonymous feedback questionnaires completed by DCs after major training events.

**The same passages in the earlier sanitised copy:** 1 quote(s), verified.

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 1 historical quote(s), 0 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Confirmed)
- **Basis:** No sample asks how supervisory quality is measured, and the exc-supervision cell passed with 2 of 3 members, its members listing annual progress reports and feedback questionnaires among the structure they rate adequate. The lane read the one sentence that answers the question and judged it sufficient (A09).
- **The ESR complains of:** `inadequately_explained`
- **Uncertainty:** As with ESR-E-07, the miss stands and the open question is how a calibration disagreement should be counted.
- **Recommendation:** `adjudicated`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Taken with ESR-E-07; one decision covers both.

**Proposed revision (drafted, declared Assumed):**

> Name the measures: a supervision-quality questionnaire with a stated instrument, its cadence, the indicator thresholds that trigger Supervisory Board action, and the person who reviews the results.

---

### ESR-I-S01 — impact / imp-structuring

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 2.1

**ESR text (verbatim):**

> Non-academic sector contribution to doctoral training is well described and compelling; they have a meaningful and tangible role through structured secondments in hospitals, SMEs, and regulatory bodies, ensuring hands-on exposure to clinical workflows, compliance, and innovation. Industry and regulatory partners actively co-supervise doctoral candidates (DCs), participate the Individual Training Panels, and the Supervisory Board, and lead network-wide training sessions.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Every sample lists the structured secondments, non-academic co-supervision and Supervisory Board roles as strengths, and the imp-structuring cell passes 3/3. Three samples add that the '80% of secondment months in non-academic settings' target is contradicted by the DC table (about 74%, DC7 with none). The evaluators did not note that arithmetic; it is a blind finding on a praised point and is carried as contested.

**Findings, as resolved:**

- blind lane · criterion_strength · impact sample 0 #0
  > Concrete, measurable training-structuring commitments: unified curriculum, ≥3 joint doctoral courses, ≥3 transferable-skills modules, and a clear 4-6 month secondment structure co-supervised by non-academic partners.
- blind lane · criterion_strength · impact sample 2 #0
  > Concrete, measurable commitments for structuring doctoral training: ≥80% of secondment months in non-academic settings, at least three joint courses and three transferable-skills modules, and named Supervisory Board/ITP non-academic co-supervision roles
- blind lane · criterion_strength · impact sample 4 #0
  > Non-academic sector contribution is made credible with a concrete, measurable target (≥80% of secondment months in non-academic settings, ≥3 joint courses/skills modules) and governance links via Supervisory Board/ITP
- blind lane · criterion_shortcoming · impact sample 0 #0
  > Section 2.1 claims '≥80% of secondment months in non-academic settings' but the DC table in the declared appendix (Table 3.1 d) sums to roughly 61/82 ≈ 74% non-academic secondment months, and DC7 shows 10 secondment months with 0 months in the non-academic sector, directly contradicting the stated target.
- blind lane · criterion_shortcoming · impact sample 3 #0
  > Claimed '≥80% of secondment months in non-academic settings' (2.1.1) is contradicted by the DC Table appendix: actual ratio is ~61/82 ≈74%, and DC7 shows 10 secondment months but 0 months in the non-academic sector, undermining the credibility of this quantitative target.
- blind lane · cell · imp-structuring
  > majority over n=3; passed=True (3 true / 0 false, agreement 100%); mean score=0.740

**Reference check (measured):**

- resolved: 6 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 6 of 6 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** Three criterion strengths name the structured secondments, the non-academic co-supervision and the Supervisory Board and ITP roles, and the imp-structuring cell passes 3/3. Those are the ESR's own examples.
- **Uncertainty:** Two samples add an arithmetic contradiction the evaluators did not record: section 2.1 claims at least 80% of secondment months in non-academic settings, while the DC table sums to about 74% and DC7 shows ten secondment months with none non-academic. That is computed from the appendix table as this copy carries it.
- **Recommendation:** `revisit_after_declaration`, disposition `independently_detected` (unchanged)
- **Operator decision required:** Confirm the appendix secondment months in this copy are the submission's. If they are, decide whether the 80% contradiction enters the R05 revision plan as a correction the ESR did not ask for.

---

### ESR-I-S02 — impact / imp-structuring

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 2.1

**ESR text (verbatim):**

> Several elements are convincingly sustained after the project; these include e.g. the development of a virtual knowledge hub. The robust strategies and mechanisms described ensure a sustained long-term collaboration, and foster future international and intersectoral research and cooperation.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> The knowledge hub, ECTS integration, alumni hub and the Innovation and Sustainability Committee are listed as strengths in every sample, matching the ESR's 'virtual knowledge hub' and sustained collaboration. Two samples find the post-project funding plan a list of programme names; the ESR does not fault it. Carried as contested.

**Findings, as resolved:**

- blind lane · criterion_strength · impact sample 0 #2
  > Clear sustainability mechanism for doctoral training via the European AI Training Academy, alumni hub, ECTS-credit integration into partner curricula, and an Innovation and Sustainability Committee tracking indicators post-funding.
- blind lane · criterion_strength · impact sample 1 #2
  > Sustainability is addressed through a concrete institutional mechanism (European AI Training Academy / knowledge hub, ECTS integration into partner curricula, Innovation and Sustainability Committee with tracked indicators).
- blind lane · criterion_strength · impact sample 3 #2
  > Sustainability is addressed with specific, named mechanisms (European AI Training Academy, Innovation and Sustainability Committee, alumni hub, ECTS integration) rather than vague intentions.
- blind lane · criterion_shortcoming · impact sample 1 #5
  > Post-project sustainability funding strategy ('jointly target further funding ... MSCA Staff Exchanges, EIT, Erasmus+, etc.') is a list of possible programmes rather than a concrete plan with named next steps or committed resources.
- blind lane · criterion_shortcoming · impact sample 2 #4
  > Post-project sustainability funding plan (2.1.3) is a generic list of programme names (MSCA Staff Exchanges, EIT, Erasmus+, COST) without concrete commitments, named targets or responsible actors

**Reference check (measured):**

- resolved: 5 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 5 of 5 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** Three criterion strengths name the knowledge hub, the ECTS integration, the alumni hub and the Innovation and Sustainability Committee. The ESR names the virtual knowledge hub and the sustained long-term collaboration.
- **Uncertainty:** Two samples fault the post-project funding plan as a list of programme names. The ESR does not fault it. The finding is about a different sentence of 2.1 than the praise rests on.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** Decide whether the post-project funding plan is revised in R05 even though the ESR praised this aspect. A revision here is an improvement beyond the ESR, not a response to it.

---

### ESR-I-S03 — impact / imp-career

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 2.2

**ESR text (verbatim):**

> The project provides a robust and well-structured framework and environment to equip fellows with both technical and transferable skills, significantly enhancing and ensuring the future employability in both academia and industry. Specifically, the profile of fellows in trustworthy AI for clinical issues is highly relevant for hospitals, industry R&D departments, start-ups and research infrastructures. Transferable skills are integrated in the training, and intersectoral secondments and co-supervision expose fellows to hospitals, SMEs, and regulatory bodies, ensuring practical experience and networking. The measures to enhance the career perspectives of fellows are highly relevant and comprehensive and designed to prepare fellows for multidisciplinary careers.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> The PCDP within three months, the multi-mentor PhD committee and the transferable-skills modules are listed as strengths in every sample and the imp-career cell passes 3/3 at 0.78. No sample contests the career measures.

**Findings, as resolved:**

- blind lane · criterion_strength · impact sample 0 #1
  > Credible, well-specified career development architecture: PCDP established within 3 months, multi-mentor PhD committees spanning academic/non-academic/clinical supervisors, and clearly differentiated career pathways (academia, hospitals, industry, regulatory bodies).
- blind lane · criterion_strength · impact sample 1 #1
  > Career development measures are concrete and credible: PCDP established within 3 months, annual review, and a multi-mentor PhD committee spanning academic, clinical and secondment-host supervisors.
- blind lane · criterion_strength · impact sample 4 #2
  > Career development measures are detailed and credible: PCDP within 3 months, multi-sector PhD committees, transferable-skills curriculum, and explicit positioning across four career-path categories
- blind lane · cell · imp-career
  > majority over n=3; passed=True (3 true / 0 false, agreement 100%); mean score=0.780

**Reference check (measured):**

- resolved: 4 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 4 of 4 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** Three criterion strengths name the PCDP within three months, the multi-mentor PhD committee and the differentiated career pathways, and the imp-career cell passes 3/3 at 0.78. No sample contests the career measures.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-I-S04 — impact / imp-dissemination

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 2.3

**ESR text (verbatim):**

> The dissemination, exploitation, and communication measures are comprehensive, and well-structured, with clear objectives and monitoring through measurable indicators. The target groups for these measures are clearly identified. The outline of intellectual property management strategy is mostly appropriately addressed.

**Disposition:** `partially_observable` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> The ESR credits clear objectives, measurable indicators and identified target groups. The blind lane lists the R2I canvas and IP framework as strengths but four samples find the communication plan generic, with no audience segmentation or communication KPIs, and the imp-dissemination cell fails 2/3. The register records every figure lost and identifiers generalised; a dissemination table or figure of target groups and indicators, and named journals and venues, are what sanitisation removes. The contest may rest on removed evidence, so the strength is partly observable.

**Findings, as resolved:**

- blind lane · criterion_strength · impact sample 0 #3
  > Structured exploitation framework combining R2I Canvas, IP Management Plan, and TTO involvement, aligned with Horizon Europe open-science and access-rights requirements.
- blind lane · criterion_shortcoming · impact sample 0 #1
  > Section 2.3's dissemination/communication plan is largely generic (Q1-D1 journals, conferences, open-access repositories, website/social media) with little detail on tailored public- or patient-facing communication activities, audience segmentation, or measurable communication KPIs.
- blind lane · criterion_shortcoming · impact sample 1 #1
  > The dissemination/communication plan is heavy on scientific publication metrics (≥27 outputs) but offers little specificity for non-academic/public communication channels, audience segmentation, or communication-specific KPIs beyond generic references to symposia and workshops.
- blind lane · criterion_shortcoming · impact sample 3 #1
  > Section 2.3 (dissemination/exploitation) is largely generic HE boilerplate: 'Prestigious Q1-D1 journals' and 'top-tier AI conferences' are not named, and no concrete communication KPIs beyond a raw publication count (~27 outputs) are given.
- blind lane · criterion_shortcoming · impact sample 4 #1
  > Communication activities are described only at a generic level (joint conference sessions, symposia, workshops) with no audience-segmented strategy, channel-specific KPIs, or quantified reach/engagement targets beyond the M0.1 website/social-media milestone
- blind lane · cell · imp-dissemination
  > majority over n=3; passed=False (1 true / 2 false, agreement 67%); mean score=0.557

**Fidelity register entries the row rests on:**

- `derived/figures/images_on_any_page` = 0
- `provenance/transformation/figures` = "all lost; the copy carries zero images on any page"
- `provenance/transformation/identifiers` = "generalised (project acronym, partner names, people, places)"

**Reference check (measured):**

- resolved: 6 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 3 register entr(ies) — 9 of 9 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `unresolved` (declared Unresolved)
- **Basis:** The ESR credits clear objectives, measurable indicators and clearly identified target groups. Four samples fault the communication plan for having no audience segmentation and no communication indicators, and the imp-dissemination cell fails 2 of 3. The readings contradict each other on the same sub-section.
- **Uncertainty:** The register measures zero images on any page and records every figure lost. A dissemination table or figure of target groups and indicators is exactly what that loss removes, so the cell failure may be an artifact of the copy.
- **Recommendation:** `revisit_after_private_network`, disposition `partially_observable` (unchanged)
- **Operator decision required:** Confirm whether 2.3 carried a target-group or indicator table or figure in the submission. The failing cell is the only one of three in impact, so this answer changes how the impact score difference is read.

---

### ESR-I-01 — impact / imp-dissemination

**Kind:** minor_shortcoming · **ESR severity cluster:** ESR-C5 (minor_shortcoming) · **Proposal location:** 2.3

**ESR text (verbatim):**

> However, suitable strategies to protect industrial and other relevant outcomes are not convincingly elaborated; this is a minor shortcoming.
>
> this is a minor shortcoming.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Three samples say the IP strategy restates Horizon Europe boilerplate without naming which results are protectable or how. That is the ESR's point that strategies to protect industrial outcomes are not convincingly elaborated. The quoted passages are the generic commitments the blind lane describes.

**Findings, as resolved:**

- blind lane · criterion_shortcoming · impact sample 1 #4
  > IP management description is largely procedural/boilerplate (Consortium Agreement, IP Management Plan, TTO) without identifying which specific anticipated results are likely patentable or commercially relevant.
- blind lane · criterion_shortcoming · impact sample 2 #3
  > IP management strategy (2.3) largely restates standard Horizon Europe boilerplate (Consortium Agreement, royalty-free access, 'fair and reasonable' licensing) without project-specific protection measures or concrete examples of protectable results
- blind lane · criterion_shortcoming · impact sample 3 #3
  > The IP management strategy (2.3) restates standard Horizon Europe IP boilerplate (Consortium Agreement, IP Management Plan, TTO) without linking it to the specific anticipated outputs (e.g., which deliverables are patentable vs. open) of this particular network.

**Candidate passages (quote verified in the named sub-section):**

- `impact_section` / `2.3`
  > Beneficiaries will protect commercially relevant results through appropriate intellectual- property instruments.
- `impact_section` / `2.3`
  > Regular IP reviews will identify protectable outcomes and recommend appropriate exploitation routes, including:

**The same passages in the earlier sanitised copy:** 2 quote(s), verified.

**Reference check (measured):**

- resolved: 3 blind finding(s), 0 audit finding(s), 2 candidate quote(s), 2 historical quote(s), 0 register entr(ies) — 7 of 7 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** Three samples say the IP strategy restates Horizon Europe boilerplate without naming which results are protectable or how. That is the ESR's finding that strategies to protect industrial outcomes are not convincingly elaborated. The quoted passages are the generic commitments the findings describe.
- **The ESR complains of:** `inadequately_explained`
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

**Proposed revision (drafted, declared Assumed):**

> Under the IP strategy, list the three or four results most likely to carry industrial value (per WP), the protection route for each (patent, trade secret, open licence), the owner, and the decision point in months. Tie each to its R2I canvas.

---

### ESR-I-S05 — impact / imp-magnitude

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 2.4

**ESR text (verbatim):**

> The expected scientific impact is highly credible with clear breakthroughs in causal modelling. For example, the integration of regulatory-grade pipelines aligned with regulatory frameworks adds robustness. Indicators, such as cross-site transportability, make the scientific outcomes measurable and realistic. Societal impact is well-justified: effective and safe integration of AI in healthcare and regulatory frameworks will largely affect the quality of the cardiovascular care provided to patients, and is addressing patient benefit, healthcare-system resilience, and policy uptake.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Two samples credit the scientific, economic and societal impact pathways as distinct and coherent, the ESR's 'highly credible' and 'well-justified'. Two samples contest the societal side: no evaluation mechanism ties training outputs to health-system outcomes and the claims carry no indicators. The ESR's 'cross-site transportability' indicator survives in 1.1 and 1.2. Carried as contested.

**Findings, as resolved:**

- blind lane · criterion_strength · impact sample 1 #4
  > Impact claims span scientific, economic and societal dimensions with distinct, multi-pathway framing (clinical decision support, interoperable infrastructures, human capital, policy uptake), showing breadth of consideration.
- blind lane · criterion_strength · impact sample 4 #4
  > Scientific, economic and societal impact sections are each structured into three clearly labelled complementary pathways, giving the magnitude claims some organisational coherence even where quantification is missing
- blind lane · criterion_shortcoming · impact sample 2 #1
  > No explicit causal/evaluation mechanism links training-level outputs to the claimed health-system or societal outcomes, leaving the scale of societal impact asserted rather than demonstrated
- blind lane · criterion_shortcoming · impact sample 4 #4
  > Societal impact claims (diagnostic accuracy, reduced delays, system resilience) are not tied to measurable indicators or evaluation endpoints in the case studies described elsewhere in the proposal

**Reference check (measured):**

- resolved: 4 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 4 of 4 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** Two criterion strengths credit the scientific, economic and societal pathways as distinct and coherent, which is the ESR's 'highly credible' and 'well-justified'. The cross-site transportability indicator the ESR names survives in the copy.
- **Uncertainty:** Two samples contest the societal half: no evaluation mechanism ties training outputs to health-system outcomes, and the societal claims carry no endpoints. The ESR praises the societal justification, so the contest and the praise are about the same passage.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** Decide whether the societal-impact indicator gap enters the R05 revision plan. ESR-I-02 already asks for magnitude on the economic and technological pathways; extending it to the societal pathway goes beyond the ESR.

---

### ESR-I-02 — impact / imp-magnitude

**Kind:** minor_shortcoming · **ESR severity cluster:** ESR-C6 (minor_shortcoming) · **Proposal location:** 2.4

**ESR text (verbatim):**

> Economic and technological impacts, such as validated causal AI and interoperability with European Health Data Space/Fast Healthcare Interoperability Resources (EHDS/FHIR), and human capital development through multi-sector training, are overall valid, especially in a long-term, however, the magnitude in terms of specific measures is insufficiently presented in the proposal.
>
> This is a minor shortcoming.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Every sample and all three imp-magnitude cell members say the magnitude of impact is stated qualitatively with no quantified targets; the cell is the lowest of the report (0.48, uncovered). The ESR's finding is the same, limited to economic and technological impact. The quoted passage is the human-capital pathway the ESR names.

**Findings, as resolved:**

- blind lane · criterion_shortcoming · impact sample 0 #2
  > Section 2.4 lists scientific, economic and societal impacts qualitatively (three advances/pathways/benefits each) but does not quantify the magnitude of expected impact (e.g., patient numbers reached, cost/efficiency estimates, market scale), weakening the 'magnitude and importance' aspect specifically.
- blind lane · criterion_shortcoming · impact sample 1 #2
  > Expected scientific, societal and economic impacts are described largely in qualitative, aspirational language ('improved model robustness', 'improved diagnostic accuracy') without baseline comparators, quantified targets, or magnitude estimates that would let reviewers judge the scale of contribution.
- blind lane · criterion_shortcoming · impact sample 2 #0
  > Expected scientific, societal and economic impacts (2.4) are stated almost entirely in qualitative terms (e.g. 'improved diagnostic accuracy', 'reduce delays in care') with no quantified targets, baselines or comparators against which 'magnitude' could be assessed
- blind lane · criterion_shortcoming · impact sample 3 #2
  > Section 2.4 (magnitude/importance) lacks any quantification of expected impact magnitude — no baseline comparisons, target populations, cost/efficiency estimates, or numeric indicators are provided for the scientific, economic or societal impact claims, leaving 'magnitude and importance' largely asserted rather than demonstrated.
- blind lane · criterion_shortcoming · impact sample 4 #0
  > Magnitude of scientific, societal and economic impact is described mainly in qualitative, generic terms (e.g. 'improved model robustness', 'strengthen Europe's competitiveness') without quantified targets, baselines or comparators that would let reviewers judge the actual scale of contribution
- blind lane · cell · imp-magnitude
  > majority over n=3; passed=False (0 true / 3 false, agreement 100%); mean score=0.483

**Candidate passages (quote verified in the named sub-section):**

- `impact_section` / `2.4`
  > Human capital and innovation ecosystems The project will train a cohort of specialists with expertise at the intersection of AI, healthcare, governance and implementation, strengthening Europe's competitiveness and innovation capacity in digital health.

**The same passages in the earlier sanitised copy:** 1 quote(s), verified.

**Reference check (measured):**

- resolved: 6 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 1 historical quote(s), 0 register entr(ies) — 8 of 8 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** Every sample and all three imp-magnitude cell members say the magnitude of impact is stated qualitatively with no quantified targets, baselines or comparators. The cell is the report's lowest at 0.48 and uncovered. The ESR's finding is the same, limited to the economic and technological pathways.
- **The ESR complains of:** `absent_detail`
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

**Proposed revision (drafted, declared Assumed):**

> Under 2.4 economic and technological impact, give one magnitude per pathway: number of hospitals and SMEs adopting the toolkit by M36 and M60, number of trained specialists and their destinations, the EHDS/FHIR-aligned components released, and a baseline for each. Keep the three pathways; add the numbers.

---

### ESR-Q-S01 — implementation / impl-workplan

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 3.1

**ESR text (verbatim):**

> The work plan is overall of good quality. The work packages (WPs) are clearly aligned with the project objectives, and the allocation of WPs and tasks is coherent. Each WP includes generally well-defined and appropriate deliverables and milestones.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Every sample lists the seven-WP structure with objectives, tasks, leads and DCs, and the deliverables and milestones tables, as strengths; the impl-workplan cell passes 3/3 at 0.78. This is the ESR's 'overall of good quality' with coherent allocation and well-defined deliverables and milestones.

**Findings, as resolved:**

- blind lane · criterion_strength · implementation sample 0 #0
  > Comprehensive 7-WP structure with clearly stated objectives, tasks, leads, participants and involved DCs, showing a logical flow from foundational AI methods (WP1-2) through human-AI collaboration (WP3) to clinical/industrial translation (WP4).
- blind lane · criterion_strength · implementation sample 2 #0
  > Work plan is unusually complete: seven WPs each with objectives, numbered tasks, lead/participant/DC assignments, linked to a full deliverables table (type, dissemination level, lead, due month) and milestones table with verifiable means.
- blind lane · criterion_strength · implementation sample 4 #0
  > Work plan is fully specified with objectives, tasks, leads, participants and DC involvement for every WP, cross-referenced to a detailed deliverables table (titles, type, dissemination level, lead, due month) and a milestones table with verifiable means of verification
- blind lane · criterion_strength · implementation sample 0 #1
  > Detailed deliverables and milestones tables with explicit leads, types, dissemination levels and verification means support traceable monitoring of implementation.
- blind lane · cell · impl-workplan
  > majority over n=3; passed=True (3 true / 0 false, agreement 100%); mean score=0.780

**Reference check (measured):**

- resolved: 5 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 5 of 5 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** Four criterion strengths name the seven work packages with objectives, tasks, leads and DCs, and the deliverables and milestones tables with their verification means. The impl-workplan cell passes 3/3 at 0.78. That is the ESR's work plan of good quality with coherent allocation.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-Q-01 — implementation / impl-workplan

**Kind:** shortcoming · **ESR severity cluster:** ESR-C7 (shortcoming, 3 observations) · **Proposal location:** 3.1

**ESR text (verbatim):**

> However, several aspects lack appropriate detail such as the description of dependencies between work packages.
>
> These issues together are a shortcoming.

**Disposition:** `partially_observable` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Three samples say inter-WP dependencies and the critical path are not mapped beyond narrative cross-references, and that no Gantt or dependency diagram is shown. That is the ESR's point. The register measures zero figures on any page and zero occurrences of 'dependenc', 'Gantt' or 'critical path'; a Gantt or PERT figure in the submission would have been lost. The blind detection may therefore rest partly on evidence the copy lacks, which is why the row is partial rather than detected. The quoted cross-references are the only dependency statements the copy carries.

**Findings, as resolved:**

- blind lane · criterion_shortcoming · implementation sample 0 #3
  > All WPs run uniformly M1-M36 with no intermediate milestones or Gantt-style sequencing shown, giving limited insight into task dependencies and critical path.
- blind lane · criterion_shortcoming · implementation sample 2 #1
  > Inter-WP dependencies and critical-path logic (e.g., how WP1 explainability outputs feed WP2/WP3/WP4 timing) are not mapped beyond occasional narrative cross-references.
- blind lane · criterion_shortcoming · implementation sample 3 #4
  > No Gantt chart, task-dependency diagram, or explicit timeline justification beyond uniform M1-M36 spans for all WPs, limiting assessment of workplan sequencing logic

**Candidate passages (quote verified in the named sub-section):**

- `implementation_section` / `3.1`
  > Explainability methods will be integrated in collaboration with WP1.
- `implementation_section` / `3.2`
  > Foundational AI outputs flow into infrastructure and deployment activities and then into clinical and digital-health pilots

**The same passages in the earlier sanitised copy:** 2 quote(s), verified.

**Fidelity register entries the row rests on:**

- `derived/figures/images_on_any_page` = 0
- `provenance/transformation/figures` = "all lost; the copy carries zero images on any page"
- `derived/dependency_keyword_counts` = {"dependenc": 0, "interdepend": 0, "Gantt": 0, "critical path": 0, "in WP<n>": 4, "build(s/ing) (up)on": 1}

**Reference check (measured):**

- resolved: 3 blind finding(s), 0 audit finding(s), 2 candidate quote(s), 2 historical quote(s), 3 register entr(ies) — 10 of 10 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `disputed` (declared Confirmed)
- **Basis:** Two of the three cited findings carry the ESR's point: dependencies and critical-path logic are not mapped beyond narrative cross-references, and no Gantt or dependency diagram is shown. The third is withdrawn: it states that no intermediate milestones are shown, and the implementation section the assessor received carries the milestones table with a due month for each of 16 milestones (A05, A11).
- **The ESR complains of:** `both`
- **Uncertainty:** The register measures zero images on any page, so a Gantt or dependency figure in the submission would have been lost. That is why the row is partial and not detected, and it is a question for the private-network review, not for this copy.
- **Recommendation:** `adjudicated`, disposition `partially_observable` (unchanged)
- **Operator decision required:** Confirm the withdrawal of the sample-0 citation. The dependency point stands on the other two findings and the disposition partially_observable does not change.

**Proposed revision (drafted, declared Assumed):**

> Add a dependency table to 3.1: for each WP, the inputs it needs from other WPs with the deliverable id and month, and the outputs it hands on. Reinstate the Gantt with milestone markers if one existed; a table survives reflow where a figure may not.

---

### ESR-Q-02 — implementation / impl-workplan

**Kind:** shortcoming · **ESR severity cluster:** ESR-C7 (shortcoming, 3 observations) · **Proposal location:** 3.1

**ESR text (verbatim):**

> In addition, the validation strategy for certain deliverables is not fully specified
>
> These issues together are a shortcoming.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> The deliverables table survives with 28 parsed rows and carries no validation or acceptance column; the milestones table carries 'Means of Verification' but the deliverables do not. The blind lane praised the deliverables table in every sample and no sample or cell asks how deliverables are validated; the audit's deliverable check found no window violations and does not test validation. The evaluators' point is observable in the table as it stands.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `implementation_section` / `3.1`
  > | Numbe r | Deliverable Title | Short Description | W P | Lead Beneficiary | Typ e | Disseminatio n | Due |
- `implementation_section` / `3.1`
  > | D1.2 | Sensitivity & Uncertainty Quantification Methodologies | Clinician- facing tools to enable safe human-in-the- loop interaction. | 1 | Academic Beneficiary D | PDE | PU | M18 |

**The same passages in the earlier sanitised copy:** 2 quote(s), verified.

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 2 candidate quote(s), 2 historical quote(s), 0 register entr(ies) — 4 of 4 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Confirmed)
- **Basis:** No sample or cell asks how deliverables are validated. R03 found the cause: four of the five implementation samples attribute verification means to the deliverables and milestones tables jointly, while only the milestones table carries that column. The lane credited one table with the other's property and never asked the question (A10).
- **The ESR complains of:** `absent_detail`
- **Uncertainty:** The absence is readable from the copy, which is why the row counts against the lane. The application form asks for no validation column, so the ESR's point is one of substance rather than form compliance.
- **Recommendation:** `adjudicated`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Confirm that the misattribution is reported to the assessor's own account in PE-09, with A05, as a lane defect rather than a scoring disagreement.

**Proposed revision (drafted, declared Assumed):**

> Add a 'Validation' column to the scientific deliverables table, or one sentence per technical deliverable (D1.x-D4.x) naming the acceptance test, the benchmark or the clinical reviewer that signs it off.

---

### ESR-Q-03 — implementation / impl-workplan

**Kind:** shortcoming · **ESR severity cluster:** ESR-C7 (shortcoming, 3 observations) · **Proposal location:** 3.1

**ESR text (verbatim):**

> and the definitions and timing of some milestones is not well aligned with the overall proposal.
>
> These issues together are a shortcoming.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** both lanes

**Why the disposition says so (from the dispositions):**

> The integrity audit finds M7.3 due at M48 while WP7 runs M1-M36, and that no milestone names a deliverable it depends on. One blind sample notes the uniform M1-M36 spans with no intermediate sequencing. Together these are the ESR's 'definitions and timing of some milestones not well aligned'. Detected by the audit lane in the specific, by the blind lane in the general.

**Findings, as resolved:**

- blind lane · criterion_shortcoming · implementation sample 0 #3
  > All WPs run uniformly M1-M36 with no intermediate milestones or Gantt-style sequencing shown, giving limited insight into task dependencies and critical path.
- integrity audit · check `milestone_dependencies` #15 · subject M7.3 · `integrity_242f1afb02c8_0001.json`
  > M7.3 is due M48; its related WP7 runs M1-M36
- integrity audit · check `milestone_dependencies` #16 · subject M7.3 · `integrity_242f1afb02c8_0001.json`
  > M7.3 names no deliverable it depends on; the deliverables of its related package(s) and their months are listed as context, not judged
- integrity audit · check `milestone_dependencies` #9 · subject M4.2 · `integrity_242f1afb02c8_0001.json`
  > M4.2 names no deliverable it depends on; the deliverables of its related package(s) and their months are listed as context, not judged

**Candidate passages (quote verified in the named sub-section):**

- `implementation_section` / `3.1`
  > | M7.3 | Follow-up research proposal | 7 | Academic Beneficiary H | M48 | Submission of at least one follow-up collaborative research proposal |
- `implementation_section` / `3.1`
  > | M4.2 | Evaluation of AI models in retrospective clinical studies | 4 | All beneficiaries | M24 | Scientific publications and evaluation reports derived from clinical case studies |

**The same passages in the earlier sanitised copy:** 2 quote(s), verified.

**Reference check (measured):**

- resolved: 1 blind finding(s), 3 audit finding(s), 2 candidate quote(s), 2 historical quote(s), 0 register entr(ies) — 8 of 8 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `disputed` (declared Inferred)
- **Basis:** Of the four cited findings, one survives. The blind citation is withdrawn (A05). The two undeclared-dependency findings rest on no sourced requirement: the milestones table the application form fixes has no dependency column (A03). The M7.3 window finding stands and matches the ESR's point on timing: a milestone due M48 related to a package the copy itself declares as M1-M36 (A04).
- **The ESR complains of:** `other`
- **Uncertainty:** What the gap means is not settled. M7.3 is the submission of a follow-up proposal, which a consortium may intend after the funded period, and the copy declares no project duration against which M48 could be placed. Tier 2B holds no extract for this call.
- **Recommendation:** `adjudicated`, disposition `independently_detected` (unchanged)
- **Operator decision required:** Two decisions. First, confirm that detected_by narrows to the integrity audit and the citations narrow from four findings to one, or move the row to partially_observable because no finding addresses the definitions of the milestones. Second, decide whether M7.3 after the work plan ends is a misalignment to correct or an intentional commitment to move out of the milestone table.

**Proposed revision (drafted, declared Assumed):**

> Move M7.3 inside the project window or make it a post-project commitment outside the milestone table. For every milestone, name the deliverable(s) it depends on and check the due month follows them. Define M4.2 against a stated evaluation endpoint rather than 'publications'.

---

### ESR-Q-04 — implementation / impl-workplan

**Kind:** minor_shortcoming · **ESR severity cluster:** ESR-C8 (minor_shortcoming) · **Proposal location:** 3.1

**ESR text (verbatim):**

> Risk management is present and generally credible, with several appropriate mitigation measures. However, certain descriptions of risks remain generic and oversimplified, without measurable thresholds for activation of the mitigation.
>
> This is a minor shortcoming.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Three samples say several mitigations are generic and carry no quantitative thresholds or contingency owners, which is the ESR's finding. The copy preserves the risk table in full: one risk states a 60% trigger and the others none, so the audit's threshold check reports nothing while the blind lane reads the generic rows the ESR read.

**Findings, as resolved:**

- blind lane · criterion_shortcoming · implementation sample 2 #3
  > Some risk mitigations (e.g., for data-sharing delays, data integration, limited domain-expert availability) are stated at a generic level without quantitative thresholds or named contingency owners beyond the recruitment risk.
- blind lane · criterion_shortcoming · implementation sample 3 #1
  > Risk table skews toward Low/Medium likelihood items with only generic mitigations (e.g., 'ongoing support, supervision and monitoring mechanisms' for thesis non-completion), suggesting limited depth of risk assessment
- blind lane · criterion_shortcoming · implementation sample 0 #1
  > Risk table covers generic recruitment/attrition risks and some technical risks (data integration, generalisation) but offers no explicit likelihood/severity methodology and leaves several technical risks (e.g., causal-model validity failure, cross-site federated-learning failure, XAI framework integration delays) unaddressed.

**Candidate passages (quote verified in the named sub-section):**

- `implementation_section` / `3.1`
  > Ongoing support, supervision and monitoring mechanisms during thesis preparation.
- `implementation_section` / `3.1`
  > If not deemed sufficient after 60% of the intended recruitment period, efofrts will be reinforced.

**The same passages in the earlier sanitised copy:** 2 quote(s), verified.

**Reference check (measured):**

- resolved: 3 blind finding(s), 0 audit finding(s), 2 candidate quote(s), 2 historical quote(s), 0 register entr(ies) — 7 of 7 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** Three samples say several mitigations are generic and carry no quantitative thresholds or named contingency owners. That is the ESR's finding. The quoted passages are the generic mitigation and the one risk that does state a 60% trigger.
- **The ESR complains of:** `both`
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

**Proposed revision (drafted, declared Assumed):**

> For each risk give a measurable trigger (a month, a count or a percentage) and the owner who acts on it, as risk 1 already does with its 60% rule. Add two or three technical risks for WP1-WP3 (causal-model validity, federated-learning failure) with the same structure.

---

### ESR-Q-S02 — implementation / impl-participants

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 3.2, 8

**ESR text (verbatim):**

> The participating organisations have the required high-quality infrastructure and capacity to implement research of high quality and their tasks. The international consortium is well-structured, integrating academic and non-academic partners with expertise, complementary strengths, and interdisciplinary knowledge, matching with the project's objectives, and reinforcing the structural and functional capability of the Doctoral Network.

**Disposition:** `partially_observable` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> The infrastructure-to-WP mapping and the three-axis complementarity argument are listed as strengths in every sample and the impl-participants cell passes 3/3. Three samples contest capacity: the organisation descriptions are 'generic institutional boilerplate' with no track record. The register records identifiers generalised, and section 8 reaches this copy as unnamed 'Academic Beneficiary A-I' profiles, so the track-record evidence the evaluators read is what sanitisation removed. Observable for the structure, not for the capacity claims.

**Findings, as resolved:**

- blind lane · criterion_strength · implementation sample 0 #3
  > Section 3.2 clearly maps complementary infrastructure (HPC/AI labs, clinical registries, interoperability and privacy-preserving facilities) to specific WPs and articulates how consortium expertise spans the full innovation chain from methods to clinical deployment.
- blind lane · criterion_strength · implementation sample 3 #3
  > Participant capacity section maps specific infrastructure (HPC/AI labs, national AI infrastructure, secure medical-data facilities, registries/biobanks, biomedical measurement labs, HCI testbeds) directly onto the WPs they support, demonstrating task-aligned resourcing
- blind lane · criterion_strength · implementation sample 3 #4
  > Consortium complementarity is explicitly argued along three axes (methodological depth, clinical/data breadth, regulatory/interoperability expertise) rather than merely listed, and each DC is said to combine at least two environments via co-supervision/secondments
- blind lane · criterion_shortcoming · implementation sample 0 #4
  > Participant descriptions (Section 3.2 and Section 8) list facilities and generic expertise areas but provide no track-record evidence (e.g., prior grants, key publications, named PI qualifications) to substantiate claimed capacity.
- blind lane · criterion_shortcoming · implementation sample 1 #2
  > Participant descriptions in Section 8 are largely generic institutional boilerplate ('leading Central European research university', 'major European university') without concrete track-record evidence (prior grants, rankings, publication output) to substantiate claimed quality and capacity.
- blind lane · criterion_shortcoming · implementation sample 4 #1
  > Participant capacity claims are largely generic promotional language ('leading', 'major', 'internationally recognised') without concrete track-record evidence (e.g., prior comparable projects, key publications, named facility capacities)
- blind lane · cell · impl-participants
  > majority over n=3; passed=True (3 true / 0 false, agreement 100%); mean score=0.730

**Fidelity register entries the row rests on:**

- `provenance/transformation/identifiers` = "generalised (project acronym, partner names, people, places)"
- `derived/sub_sections/8/characters` = 28087

**Reference check (measured):**

- resolved: 7 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 2 register entr(ies) — 9 of 9 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `unresolved` (declared Unresolved)
- **Basis:** The infrastructure-to-WP mapping and the three-axis complementarity argument the ESR praises are named as strengths in every sample, and the impl-participants cell passes 3/3. Three samples contest the capacity claims as generic institutional boilerplate without track record, which the ESR calls high-quality infrastructure and capacity.
- **Uncertainty:** The register records identifiers generalised, and section 8 reaches this copy as unnamed 'Academic Beneficiary A-I' profiles across 28,087 characters. Prior grants, named facilities and publication records are what that generalisation removes.
- **Recommendation:** `revisit_after_private_network`, disposition `partially_observable` (unchanged)
- **Operator decision required:** Confirm whether section 8 carried track-record evidence in the submission. If it did, the three contesting findings describe the sanitisation and not the proposal.

---

### ESR-Q-S03 — implementation / impl-participants

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 3.2, 5

**ESR text (verbatim):**

> Hosting arrangements via accredited doctoral schools and international offices are credible and supportive.

**Disposition:** `partially_observable` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Four samples call the hosting arrangements generic: one sentence under 3.2 on accredited doctoral schools and international offices. The evaluators found the same arrangements credible. Section 5 (network organisation) is recorded as fully sanitised with identifiers removed, and the per-institution hosting detail the evaluators may have read there does not reach this copy. The blind contest and the ESR's credit cannot be reconciled from this copy.

**Findings, as resolved:**

- blind lane · criterion_shortcoming · implementation sample 0 #5
  > Hosting arrangements are described only generically ('accredited doctoral schools... clear hosting arrangements') without institution-specific supervisory capacity or infrastructure-to-DC mapping detail.
- blind lane · criterion_shortcoming · implementation sample 1 #4
  > Hosting-arrangement detail is generic ('accredited doctoral schools', 'international offices support housing') rather than institution-specific, limiting assessment of concrete hosting capacity.
- blind lane · criterion_shortcoming · implementation sample 2 #4
  > Hosting-arrangement detail is thin — a single generic sentence on doctoral-school embedding and international-office support, with no institution-specific hosting conditions.
- blind lane · criterion_shortcoming · implementation sample 3 #3
  > Hosting-arrangement description is generic ('accredited doctoral schools...international offices support housing') rather than specific per beneficiary/DC
- blind lane · cell_member · impl-participants
  > Section 3.2 and the per-beneficiary profiles (span 8, e.g. Beneficiary A/B/C/H 'HPC clusters and AI labs...supporting AI model development in WP1', Beneficiary I 'Electrophysiology laboratories/Neurophysiology infrastructure' for WP3-4) tie named infrastructure to specific WPs/tasks, the WP tables (span 3.1¶12,22,30,111-135) assign leads/participants to concrete tasks, and spans 3.2¶10-24 explicitly lay out consortium complementarity (methodological vs clinical vs regulatory expertise) and associated-partner roles (Non-academic Beneficiary D, Industrial Partners A-C), satisfying the specificity bar; hosting is addressed generically ('embedded in accredited doctoral schools...clear hosting arrangements') plus concrete DC-level tables (span 3.1¶203-213). No claim-ledger entries are present in this pack, so grounding of these load-bearing statements is UNASSESSABLE rather than confirmed.

**Fidelity register entries the row rests on:**

- `derived/sub_sections/5/characters` = 3135
- `provenance/transformation/identifiers` = "generalised (project acronym, partner names, people, places)"

**Reference check (measured):**

- resolved: 5 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 2 register entr(ies) — 7 of 7 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `unresolved` (declared Unresolved)
- **Basis:** Four samples call the hosting arrangements generic, a single sentence on accredited doctoral schools and international offices. The ESR calls the same arrangements credible and supportive. One cell member reads the per-beneficiary profiles as tying named infrastructure to work packages.
- **Uncertainty:** Section 5, the network organisation, reaches this copy as 3,135 characters with identifiers generalised. Per-institution hosting detail the evaluators may have read there does not reach this copy, and the contest cannot be reconciled with the praise from what remains.
- **Recommendation:** `revisit_after_private_network`, disposition `partially_observable` (unchanged)
- **Operator decision required:** Confirm what section 5 carried in the submission. Then decide whether four findings against a point the evaluators called credible count as a lane disagreement or as a reading of a shortened section.

---

### ESR-Q-S04 — implementation / impl-participants

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 3.2, 8

**ESR text (verbatim):**

> The roles of all associated partners are described in detail

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Four samples list the associated partners' differentiated roles (industrial secondment hosts, causal-AI co-supervision, external cohorts) as strengths and the cell members cite 3.2's partner paragraphs. This is the ESR's 'roles of all associated partners are described in detail'. Sample 3 adds that their infrastructure is less detailed than the beneficiaries'; the ESR does not fault it.

**Findings, as resolved:**

- blind lane · criterion_strength · implementation sample 0 #4
  > Associated partners' roles (industrial secondment hosts, specialised causal-AI partner) are explicitly tied into supervision and translational tasks, reinforcing consortium complementarity.
- blind lane · criterion_strength · implementation sample 1 #4
  > Associated partners' roles (industrial secondment hosting, regulatory expertise, specialised datasets) are clearly differentiated from academic beneficiaries, strengthening the complementarity argument.
- blind lane · criterion_strength · implementation sample 3 #5
  > Associated partners' roles (industrial secondment hosts, causal-AI specialist co-supervision, external cohort/dataset provision) are differentiated and tied to specific translational needs of WP4/WP2
- blind lane · criterion_strength · implementation sample 4 #4
  > Associated partners' roles (causal-AI expertise, industrial secondments, external validation cohorts) are clearly differentiated and integrated into governance and supervision structures

**Reference check (measured):**

- resolved: 4 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 4 of 4 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** Four criterion strengths name the associated partners' differentiated roles as industrial secondment hosts, causal-AI co-supervision and external cohort providers. That is the ESR's 'roles of all associated partners are described in detail'. The one nuance a sample adds, that their infrastructure is less detailed than the beneficiaries', is not an ESR point.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

## 7. What this report does not settle

- Whether a resolved finding is about the ESR's proposition is a judgment, recorded above as `semantic_agreement` and adjudicated in R03.
- Whether the copy preserves the evidence an ESR observation rested on is an operator declaration, prepared in R04. Every alleged miss and every partially observable row depends on it.
- Whether a praised point survives sanitisation can be settled only against the submitted original, inside the private network (PE-09).
- No disposition, revision, count or score in the comparison artifact was changed by this report. Successor artifacts are R05's.
- Relationship to earlier versions: an earlier review of this comparison, if one exists, stays in this directory under a lower sequence number. Nothing here supersedes an artifact in place, and a review of a successor comparison is a new file, not an edit of this one.

