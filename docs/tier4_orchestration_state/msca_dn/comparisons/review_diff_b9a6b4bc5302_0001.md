# ESR comparison: predecessor to successor

Generated: 2026-10-07T22:17:12.940021+00:00  
Advisory to a human, never run-blocking. This artifact declares nothing: every line is a difference measured between two written comparisons. Which reading is right is the operator's decision, and neither comparison records one.

## What is being compared

| | Predecessor | Successor |
|---|---|---|
| Comparison | `docs/tier4_orchestration_state/msca_dn/comparisons/comparison_f60ae6e0a2a1_0001.json` | `docs/tier4_orchestration_state/msca_dn/comparisons/comparison_f60ae6e0a2a1_0002.json` |
| sha256 | `9732dde500397981a133461e29d93ae657ba444199a31d84d39731f9c5ec7848` | `b9a6b4bc5302fc754be5fa9d5ab4fcef6ac25ce583d245f61980b2ad176a45b9` |
| Revisions | `docs/tier4_orchestration_state/msca_dn/comparisons/revisions_f60ae6e0a2a1_0001.json` | `docs/tier4_orchestration_state/msca_dn/comparisons/revisions_f60ae6e0a2a1_0002.json` |
| Dispositions | `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1.json` | `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_r05.json` |
| Dispositions sha256 | `5c0da82c111582d8ad30306a69daad721b4f0ab18d74adfc5fd9c3ca6ab6c0ff` | `fbed6abdb1c7bcf78aed5455b0616dd07bd05a30262c1e5ab8a01e61ae819576` |
| Review state | `—` | `agent_drafted_pending_operator_review` |
| Register sha256 | `aafed265f4e9b43b9d88d13f394fef2e812cbfa5405d53bb6720cb303c9ecfc1` | `aafed265f4e9b43b9d88d13f394fef2e812cbfa5405d53bb6720cb303c9ecfc1` |
| Audits | `docs/tier4_orchestration_state/msca_dn/audit/integrity_242f1afb02c8_0001.json, docs/tier4_orchestration_state/msca_dn/audit/integrity_13ad3ad81d7e_0001.json` | `docs/tier4_orchestration_state/msca_dn/audit/integrity_242f1afb02c8_0002.json, docs/tier4_orchestration_state/msca_dn/audit/integrity_13ad3ad81d7e_0001.json` |
| Written | `2026-10-07T11:25:02.051172+00:00` | `2026-10-07T22:16:57.191012+00:00` |

Both are over baseline report `f60ae6e0a2a1`, ESR record `2c880e6cbe5a` and candidate `sha256:242f1afb02c8`, and both cover all 29 observations. The criterion scores are identical in both: no assessor ran.

## Counts

| Figure | Before | After |
|---|---|---|
| `by_criterion/excellence/by_disposition/not_detected_despite_sufficient_preserved_evidence` | 5 | 6 |
| `by_criterion/excellence/by_disposition/partially_observable` | 3 | 2 |
| `by_criterion/excellence/detection/by_lane/blind_lane` | 3 | 2 |
| `by_criterion/excellence/detection/not_detected` | 5 | 6 |
| `by_criterion/excellence/detection/partially_observable` | 1 | 0 |
| `by_criterion/excellence/detection/rate_detected_or_partial` | 0.38 | 0.25 |
| `by_criterion/implementation/detection/by_lane/blind_lane` | 3 | 2 |
| `by_disposition/not_detected_despite_sufficient_preserved_evidence` | 6 | 7 |
| `by_disposition/partially_observable` | 7 | 6 |
| `declarations_unresolved/rows` | — | ESR-E-04, ESR-Q-03 |
| `declarations_unresolved/statement` | — | 2 row(s) declare a disposition status of 'Unresolved' (CLAUDE.md §12.2: resolution required before downstream use). Each is counted above under the disposition it declares, because a count must count something. Every figure that includes one is provisional on the operator decision the dispositions record names for that row. |
| `detection/by_lane/blind_lane` | 8 | 6 |
| `detection/not_detected` | 6 | 7 |
| `detection/partially_observable` | 2 | 1 |
| `detection/rate_detected_or_partial` | 0.57 | 0.5 |

## Rows that moved

15 of 29 rows changed.

### ESR-E-01 — excellence (shortcoming)

> However, AI/ML plans- specifically conceptual paradigms, methods, and validation metrics, as well as critical security aspects for handling clinical data with AI are insufficiently detailed.

| Field | Before | After |
|---|---|---|
| revision_plan | added | see the revisions artifact |
| priority | 3 | 4 |

### ESR-E-02 — excellence (shortcoming)

> However, AI/ML plans- specifically conceptual paradigms, methods, and validation metrics, as well as critical security aspects for handling clinical data with AI are insufficiently detailed.

| Field | Before | After |
|---|---|---|
| evidence_basis | provenance/transformation/prose | derived/sub_sections/1.2, provenance/transformation/prose |
| revision_plan | added | see the revisions artifact |

### ESR-E-03 — excellence (shortcoming)

> It is also not fully clear how some of the chosen methods will deliver key objectives: cardiovascular AI models are evaluated only retrospectively with limited plans for prospective validation;

| Field | Before | After |
|---|---|---|
| evidence_basis | — | derived/sub_sections/1.1, derived/sub_sections/3.1, provenance/transformation/prose |
| revision_plan | added | see the revisions artifact |

### ESR-E-04 — excellence (shortcoming)

> the cohort is not sufficient concerning the multihospital, multi-operator design needed to reflect contemporary European TAVI practice to capture the diversity;

| Field | Before | After |
|---|---|---|
| disposition | partially_observable | not_detected_despite_sufficient_preserved_evidence |
| disposition_status | Inferred | Unresolved |
| evidence_preserved_status | — | Unresolved |
| detected_by | blind_lane | — |
| blind_findings | criterion_shortcoming:excellence:sample0:3 | — |
| evidence_basis | provenance/transformation/prose | derived/sub_sections/3.1, provenance/transformation/prose |
| explanation | rewritten | see the successor comparison |
| revision_plan | added | see the revisions artifact |
| priority | 4 | 3 |

### ESR-E-05 — excellence (shortcoming)

> and the number of contributing clinicians to the database is not well-specified.

| Field | Before | After |
|---|---|---|
| revision_plan | added | see the revisions artifact |

### ESR-E-06 — excellence (minor_shortcoming)

> Gender and other diversity characteristics relevant to this research are mostly appropriately considered in the research methodology as scientific variables (disaggregated data, subgroup calibration, bias mitigation), however, they are not detailed enough regarding their essential role in clinical issues in cardiology.

| Field | Before | After |
|---|---|---|
| revision_plan | added | see the revisions artifact |

### ESR-E-07 — excellence (minor_shortcoming)

> While network-wide training overall complements the local training programmes, there is a slight limitation in clarity and depth in systematic description of complementation of local training.

| Field | Before | After |
|---|---|---|
| evidence_basis | — | derived/sub_sections/1.3, provenance/transformation/prose |
| revision_plan | added | see the revisions artifact |

### ESR-E-08 — excellence (minor_shortcoming)

> In addition, some details for training are not properly described, for example, the integration of entrepreneurship training lacks clear mechanisms for practical application.

| Field | Before | After |
|---|---|---|
| evidence_basis | — | derived/sub_sections/1.3, derived/sub_sections/2.2, provenance/transformation/prose |
| revision_plan | added | see the revisions artifact |

### ESR-E-09 — excellence (minor_shortcoming)

> However, the description remains slightly generic on how the quality of supervisory practices will be measured.

| Field | Before | After |
|---|---|---|
| evidence_basis | — | derived/sub_sections/1.4, provenance/transformation/prose |
| revision_plan | added | see the revisions artifact |

### ESR-I-01 — impact (minor_shortcoming)

> However, suitable strategies to protect industrial and other relevant outcomes are not convincingly elaborated; this is a minor shortcoming.

| Field | Before | After |
|---|---|---|
| revision_plan | added | see the revisions artifact |

### ESR-I-02 — impact (minor_shortcoming)

> Economic and technological impacts, such as validated causal AI and interoperability with European Health Data Space/Fast Healthcare Interoperability Resources (EHDS/FHIR), and human capital development through multi-sector training, are overall valid, especially in a long-term, however, the magnitude in terms of specific measures is insufficiently presented in the proposal.

| Field | Before | After |
|---|---|---|
| revision_plan | added | see the revisions artifact |

### ESR-Q-01 — implementation (shortcoming)

> However, several aspects lack appropriate detail such as the description of dependencies between work packages.

| Field | Before | After |
|---|---|---|
| blind_findings | criterion_shortcoming:implementation:sample0:3, criterion_shortcoming:implementation:sample2:1, criterion_shortcoming:implementation:sample3:4 | criterion_shortcoming:implementation:sample2:1, criterion_shortcoming:implementation:sample3:4 |
| explanation | rewritten | see the successor comparison |
| revision_plan | added | see the revisions artifact |

### ESR-Q-02 — implementation (shortcoming)

> In addition, the validation strategy for certain deliverables is not fully specified

| Field | Before | After |
|---|---|---|
| evidence_basis | — | derived/sub_sections/3.1, provenance/transformation/reformatting/tables_3_1b_to_e |
| revision_plan | added | see the revisions artifact |

### ESR-Q-03 — implementation (shortcoming)

> and the definitions and timing of some milestones is not well aligned with the overall proposal.

| Field | Before | After |
|---|---|---|
| disposition_status | Inferred | Unresolved |
| detected_by | blind_lane, integrity_audit | integrity_audit |
| blind_findings | criterion_shortcoming:implementation:sample0:3 | — |
| audit_findings | integrity_242f1afb02c8_0001.json:milestone_dependencies:15, integrity_242f1afb02c8_0001.json:milestone_dependencies:16, integrity_242f1afb02c8_0001.json:milestone_dependencies:9 | integrity_242f1afb02c8_0002.json:milestone_dependencies:15 |
| audit_findings withdrawn | integrity_242f1afb02c8_0001.json:milestone_dependencies:15, integrity_242f1afb02c8_0001.json:milestone_dependencies:16, integrity_242f1afb02c8_0001.json:milestone_dependencies:9 | — |
| audit_findings added | — | integrity_242f1afb02c8_0002.json:milestone_dependencies:15 |
| explanation | rewritten | see the successor comparison |
| revision_plan | added | see the revisions artifact |

### ESR-Q-04 — implementation (minor_shortcoming)

> Risk management is present and generally credible, with several appropriate mitigation measures. However, certain descriptions of risks remain generic and oversimplified, without measurable thresholds for activation of the mitigation.

| Field | Before | After |
|---|---|---|
| revision_plan | added | see the revisions artifact |

## Rows that did not move

ESR-E-S01, ESR-E-S02, ESR-E-S03, ESR-E-S04, ESR-E-S05, ESR-I-S01, ESR-I-S02, ESR-I-S03, ESR-I-S04, ESR-I-S05, ESR-Q-S01, ESR-Q-S02, ESR-Q-S03, ESR-Q-S04

## Shortcomings left out of the revision list

None. Every ESR shortcoming still carries a proposed revision.

