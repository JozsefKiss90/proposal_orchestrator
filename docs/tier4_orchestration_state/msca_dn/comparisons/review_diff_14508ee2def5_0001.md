# ESR comparison: predecessor to successor

Generated: 2026-10-08T10:54:31.452863+00:00  
Advisory to a human, never run-blocking. This artifact declares nothing: every line is a difference measured between two written comparisons. Which reading is right is the operator's decision, and neither comparison records one.

## What is being compared

| | Predecessor | Successor |
|---|---|---|
| Comparison | `docs/tier4_orchestration_state/msca_dn/comparisons/comparison_f60ae6e0a2a1_0002.json` | `docs/tier4_orchestration_state/msca_dn/comparisons/comparison_f60ae6e0a2a1_0003.json` |
| sha256 | `b9a6b4bc5302fc754be5fa9d5ab4fcef6ac25ce583d245f61980b2ad176a45b9` | `14508ee2def5ebe4887dc7458dc8fe2444cd5d5267a94cf6400e36c5bb518937` |
| Revisions | `docs/tier4_orchestration_state/msca_dn/comparisons/revisions_f60ae6e0a2a1_0002.json` | `docs/tier4_orchestration_state/msca_dn/comparisons/revisions_f60ae6e0a2a1_0003.json` |
| Dispositions | `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_r05.json` | `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json` |
| Dispositions sha256 | `fbed6abdb1c7bcf78aed5455b0616dd07bd05a30262c1e5ab8a01e61ae819576` | `90484fcbd26ded9b85364eb86f6069c140a8954a8b2e8a2e655d4a03482ea9ef` |
| Review state | `agent_drafted_pending_operator_review` | `operator_reviewed` |
| Register sha256 | `aafed265f4e9b43b9d88d13f394fef2e812cbfa5405d53bb6720cb303c9ecfc1` | `aafed265f4e9b43b9d88d13f394fef2e812cbfa5405d53bb6720cb303c9ecfc1` |
| Audits | `docs/tier4_orchestration_state/msca_dn/audit/integrity_242f1afb02c8_0002.json, docs/tier4_orchestration_state/msca_dn/audit/integrity_13ad3ad81d7e_0001.json` | `docs/tier4_orchestration_state/msca_dn/audit/integrity_242f1afb02c8_0003.json, docs/tier4_orchestration_state/msca_dn/audit/integrity_13ad3ad81d7e_0001.json` |
| Written | `2026-10-07T22:16:57.191012+00:00` | `2026-10-08T10:54:21.289367+00:00` |

Both are over baseline report `f60ae6e0a2a1`, ESR record `2c880e6cbe5a` and candidate `sha256:242f1afb02c8`, and both cover all 29 observations. The criterion scores are identical in both: no assessor ran.

## Counts

| Figure | Before | After |
|---|---|---|
| `by_criterion/implementation/by_disposition/independently_detected` | 4 | 3 |
| `by_criterion/implementation/by_disposition/partially_observable` | 3 | 4 |
| `by_criterion/implementation/detection/independently_detected` | 2 | 1 |
| `by_criterion/implementation/detection/partially_observable` | 1 | 2 |
| `by_criterion/implementation/detection/rate_detected` | 0.5 | 0.25 |
| `by_disposition/independently_detected` | 15 | 14 |
| `by_disposition/partially_observable` | 6 | 7 |
| `declarations_unresolved/rows` | ESR-E-04, ESR-Q-03 | ESR-E-04 |
| `declarations_unresolved/statement` | 2 row(s) declare a disposition status of 'Unresolved' (CLAUDE.md §12.2: resolution required before downstream use). Each is counted above under the disposition it declares, because a count must count something. Every figure that includes one is provisional on the operator decision the dispositions record names for that row. | 1 row(s) declare a disposition status of 'Unresolved' (CLAUDE.md §12.2: resolution required before downstream use). Each is counted above under the disposition it declares, because a count must count something. Every figure that includes one is provisional on the operator decision the dispositions record names for that row. |
| `detection/independently_detected` | 6 | 5 |
| `detection/partially_observable` | 1 | 2 |
| `detection/rate_detected` | 0.43 | 0.36 |
| `misses_by_failure_mode/by_mode/absent_from_recorded_output` | — | ESR-E-02, ESR-E-03, ESR-E-04, ESR-E-08 |
| `misses_by_failure_mode/by_mode/read_and_misattributed` | — | ESR-Q-02 |
| `misses_by_failure_mode/by_mode/read_and_rated_adequate` | — | ESR-E-07, ESR-E-09 |
| `misses_by_failure_mode/by_mode/undetermined` | — | — |
| `misses_by_failure_mode/statement` | — | Every miss is counted in the detection figures above whatever its mode (operator decision D03). The breakdown here is separate: an adequacy disagreement ('read_and_rated_adequate') and an unmentioned topic ('absent_from_recorded_output') are different failures of the same count. 'absent_from_recorded_output' describes the recorded output and does not establish that the model did not read the evidence (D02). Neither the count nor the breakdown is an overall accuracy or calibration claim. |
| `shared_esr_sentences/groups` | — | {'observation_ids': ['ESR-E-01', 'ESR-E-02'], 'cluster_id': 'ESR-C1', 'severity_wording': 'Together, these constitute a shortcoming.', 'dispositions': {'ESR-E-01': 'independently_detected', 'ESR-E-02': 'not_detected_despite_sufficient_preserved_evidence'}, 'detected_by': {'ESR-E-01': ['blind_lane'], 'ESR-E-02': []}} |
| `shared_esr_sentences/statement` | — | Each group is one evaluator sentence that the ESR record transcribes as clause-level observations. The counts above are per observation, so one sentence appears once per clause and is not a separate evaluator sentence, an independent deduction, or a cluster-level detection; the cluster and the severity wording are the sentence's own. |

## Rows that moved

20 of 29 rows changed.

### ESR-E-01 — excellence (shortcoming)

> However, AI/ML plans- specifically conceptual paradigms, methods, and validation metrics, as well as critical security aspects for handling clinical data with AI are insufficiently detailed.

| Field | Before | After |
|---|---|---|
| review_status | operator_decision_required | operator_confirmed |

### ESR-E-02 — excellence (shortcoming)

> However, AI/ML plans- specifically conceptual paradigms, methods, and validation metrics, as well as critical security aspects for handling clinical data with AI are insufficiently detailed.

| Field | Before | After |
|---|---|---|
| failure_mode | — | absent_from_recorded_output |
| deferred_to_private_network | — | Original security, hospital/operator diversity and entrepreneurship mechanisms; compare relevant passages with sanitised text. Disposition under this approval: Preservation is unconfirmed. Withdraw E… |

### ESR-E-03 — excellence (shortcoming)

> It is also not fully clear how some of the chosen methods will deliver key objectives: cardiovascular AI models are evaluated only retrospectively with limited plans for prospective validation;

| Field | Before | After |
|---|---|---|
| explanation | rewritten | see the successor comparison |
| review_status | operator_decision_required | operator_confirmed |
| failure_mode | — | absent_from_recorded_output |

### ESR-E-04 — excellence (shortcoming)

> the cohort is not sufficient concerning the multihospital, multi-operator design needed to reflect contemporary European TAVI practice to capture the diversity;

| Field | Before | After |
|---|---|---|
| failure_mode | — | absent_from_recorded_output |
| deferred_to_private_network | — | Original security, hospital/operator diversity and entrepreneurship mechanisms; compare relevant passages with sanitised text. Disposition under this approval: Preservation is unconfirmed. Withdraw E… |

### ESR-E-05 — excellence (shortcoming)

> and the number of contributing clinicians to the database is not well-specified.

| Field | Before | After |
|---|---|---|
| deferred_to_private_network | — | Original registry/database and contributing-clinician passages. Disposition under this approval: Keep not-assessable pending evidence. |

### ESR-E-S03 — excellence (strength)

> Open science practices, such as preprints, and repositories, are included and adequately described in the proposed methodology.

| Field | Before | After |
|---|---|---|
| deferred_to_private_network | — | Original repository/preprint commitments, supervisor mapping and track-record evidence. Disposition under this approval: Do not adopt blind criticisms as established proposal weaknesses. This cell of… |

### ESR-E-07 — excellence (minor_shortcoming)

> While network-wide training overall complements the local training programmes, there is a slight limitation in clarity and depth in systematic description of complementation of local training.

| Field | Before | After |
|---|---|---|
| review_status | operator_decision_required | operator_confirmed |
| failure_mode | — | read_and_rated_adequate |

### ESR-E-08 — excellence (minor_shortcoming)

> In addition, some details for training are not properly described, for example, the integration of entrepreneurship training lacks clear mechanisms for practical application.

| Field | Before | After |
|---|---|---|
| failure_mode | — | absent_from_recorded_output |
| deferred_to_private_network | — | Original security, hospital/operator diversity and entrepreneurship mechanisms; compare relevant passages with sanitised text. Disposition under this approval: Preservation is unconfirmed. Withdraw E… |

### ESR-E-S05 — excellence (strength)

> The supervisors are experienced and highly qualified in their scientific roles. They demonstrate appropriate international and local experience across all relevant areas and facilitating the adequate and effective completion the individual research projects. The well-structured and multi-layered approach of supervision practices is solid and overall sound. It ensures effective progress monitoring…

| Field | Before | After |
|---|---|---|
| deferred_to_private_network | — | Original repository/preprint commitments, supervisor mapping and track-record evidence. Disposition under this approval: Do not adopt blind criticisms as established proposal weaknesses. This cell of… |

### ESR-E-09 — excellence (minor_shortcoming)

> However, the description remains slightly generic on how the quality of supervisory practices will be measured.

| Field | Before | After |
|---|---|---|
| review_status | operator_decision_required | operator_confirmed |
| failure_mode | — | read_and_rated_adequate |

### ESR-I-S01 — impact (strength)

> Non-academic sector contribution to doctoral training is well described and compelling; they have a meaningful and tangible role through structured secondments in hospitals, SMEs, and regulatory bodies, ensuring hands-on exposure to clinical workflows, compliance, and innovation. Industry and regulatory partners actively co-supervise doctoral candidates (DCs), participate the Individual Training…

| Field | Before | After |
|---|---|---|
| deferred_to_private_network | — | Original secondment rows, host-sector classifications and the denominator for the 80% claim. Disposition under this approval: Recompute privately before approving a correction. Identify the actual so… |

### ESR-I-S02 — impact (strength)

> Several elements are convincingly sustained after the project; these include e.g. the development of a virtual knowledge hub. The robust strategies and mechanisms described ensure a sustained long-term collaboration, and foster future international and intersectoral research and cooperation.

| Field | Before | After |
|---|---|---|
| proposed_revision | — | Optional, beyond the ESR: if the submitted original states the post-project funding plan as the sanitised copy does (a list of programme names), name for each sustained element the mechanism that car… |
| revision_plan | added | see the revisions artifact |
| review_status | operator_decision_required | operator_confirmed |

### ESR-I-S04 — impact (strength)

> The dissemination, exploitation, and communication measures are comprehensive, and well-structured, with clear objectives and monitoring through measurable indicators. The target groups for these measures are clearly identified. The outline of intellectual property management strategy is mostly appropriately addressed.

| Field | Before | After |
|---|---|---|
| deferred_to_private_network | — | Original target-group/indicator tables, figures and prose. Disposition under this approval: Do not attribute the disagreement to sanitisation as a confirmed cause. |

### ESR-I-S05 — impact (strength)

> The expected scientific impact is highly credible with clear breakthroughs in causal modelling. For example, the integration of regulatory-grade pipelines aligned with regulatory frameworks adds robustness. Indicators, such as cross-site transportability, make the scientific outcomes measurable and realistic. Societal impact is well-justified: effective and safe integration of AI in healthcare an…

| Field | Before | After |
|---|---|---|
| review_status | operator_decision_required | operator_confirmed |

### ESR-I-02 — impact (minor_shortcoming)

> Economic and technological impacts, such as validated causal AI and interoperability with European Health Data Space/Fast Healthcare Interoperability Resources (EHDS/FHIR), and human capital development through multi-sector training, are overall valid, especially in a long-term, however, the magnitude in terms of specific measures is insufficiently presented in the proposal.

| Field | Before | After |
|---|---|---|
| revision_plan | changed | see the revisions artifact |

### ESR-Q-01 — implementation (shortcoming)

> However, several aspects lack appropriate detail such as the description of dependencies between work packages.

| Field | Before | After |
|---|---|---|
| explanation | rewritten | see the successor comparison |
| priority | 8 | 7 |
| review_status | operator_decision_required | operator_confirmed |
| deferred_to_private_network | — | Original dependencies, Gantt and sequencing evidence. Disposition under this approval: Keep partial classification qualified; absence of embedded images alone does not establish that every figure was… |

### ESR-Q-02 — implementation (shortcoming)

> In addition, the validation strategy for certain deliverables is not fully specified

| Field | Before | After |
|---|---|---|
| explanation | rewritten | see the successor comparison |
| revision_plan | changed | see the revisions artifact |
| review_status | operator_decision_required | operator_confirmed |
| failure_mode | — | read_and_misattributed |

### ESR-Q-03 — implementation (shortcoming)

> and the definitions and timing of some milestones is not well aligned with the overall proposal.

| Field | Before | After |
|---|---|---|
| disposition | independently_detected | partially_observable |
| disposition_status | Unresolved | Inferred |
| audit_findings | integrity_242f1afb02c8_0002.json:milestone_dependencies:15 | integrity_242f1afb02c8_0003.json:milestone_dependencies:0 |
| audit_findings withdrawn | integrity_242f1afb02c8_0002.json:milestone_dependencies:15 | — |
| audit_findings added | — | integrity_242f1afb02c8_0003.json:milestone_dependencies:0 |
| evidence_basis | — | derived/sub_sections/3.1 |
| explanation | rewritten | see the successor comparison |
| revision_plan | changed | see the revisions artifact |
| priority | 7 | 8 |
| review_status | operator_decision_required | operator_confirmed |
| deferred_to_private_network | — | Actual project duration, WP scope, funding/activity windows and follow-up intent. Disposition under this approval: No date or participation changes approved. |

### ESR-Q-S02 — implementation (strength)

> The participating organisations have the required high-quality infrastructure and capacity to implement research of high quality and their tasks. The international consortium is well-structured, integrating academic and non-academic partners with expertise, complementary strengths, and interdisciplinary knowledge, matching with the project's objectives, and reinforcing the structural and function…

| Field | Before | After |
|---|---|---|
| evidence_basis_values | — | — |
| explanation | rewritten | see the successor comparison |
| deferred_to_private_network | — | Original capacity and hosting evidence. Disposition under this approval: Correct identity references now; original-dependent adequacy remains unresolved. This cell of the approval's deferral table co… |

### ESR-Q-S03 — implementation (strength)

> Hosting arrangements via accredited doctoral schools and international offices are credible and supportive.

| Field | Before | After |
|---|---|---|
| evidence_basis_values | — | — |
| explanation | rewritten | see the successor comparison |
| deferred_to_private_network | — | Original capacity and hosting evidence. Disposition under this approval: Correct identity references now; original-dependent adequacy remains unresolved. This cell of the approval's deferral table co… |

## Rows that did not move

ESR-E-S01, ESR-E-S02, ESR-E-06, ESR-E-S04, ESR-I-S03, ESR-I-01, ESR-Q-S01, ESR-Q-04, ESR-Q-S04

## Shortcomings left out of the revision list

None. Every ESR shortcoming still carries a proposed revision.

