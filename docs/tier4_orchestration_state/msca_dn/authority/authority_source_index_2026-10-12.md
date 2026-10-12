# Authority source index — the authority documents of the 2025 MSCA Doctoral Networks call and of the 2026 call the current profile was written for

Authored 2026-10-12. Index `msca_dn_authority_sources_2026-10-12`, schema `authority_source_index/1`,
written by `tools/author_msca_dn_authority_matrix.py`.

Review state: **agent drafted pending operator review**.
The index's own reading of its documents is declared **Inferred**.
Relationship to earlier versions: nothing. This is the first authority source index on this branch. The 2026-only pinning the specification's decision 3 recorded stands as the state it replaces, and a correction to this index is a successor index, never an edit.

16 documents are indexed. 12 are obtained and pinned by sha256, and 4 required ones are not
obtained. The 2025 era is the submission's; the 2026 era is the one the current profile was
written for. A citation of an unobtained document fails `harness.authority_matrix.check`.

## What is obtained

| Document | Era | Class | Bytes vouched for | How | States |
|---|---|---|---|---|---|
| `docs/tier2a_instrument_schemas/application_forms/msca/af_he-msca-dn_en.pdf` (v5.0) | historical | instrument application form | computed only | — | the MSCA Doctoral Networks application form of the 2025 call, Part B template included |
| `docs/tier2a_instrument_schemas/application_forms/msca/Tpl_Application Form (Part B) (HE MSCA DN).pdf` (v6.0) | current | instrument application form | computed only | — | the Part B template of the 2026 call |
| `docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_en.pdf` (v2.2) | current | instrument evaluation form | computed only | — | the evaluation form the 2026 scorecard is derived from |
| `docs/tier1_normative_framework/programme_guidance/wp-15-general-annexes_horizon-2026-2027_en.pdf` | current | programme guidance | computed only | — | the General Annexes of the 2026-2027 work programme |
| `docs/tier2b_topic_and_call_sources/work_programmes/msca/wp-2-marie-sklodowska-curie-actions_horizon-2026-2027_en.pdf` | current | work programme | computed only | — | the MSCA part of the 2026-2027 work programme |
| `docs/tier4_orchestration_state/msca_dn/esr/msca-dn-2025-esr.json` | historical | evaluation output | operator supplied | an operator transcription of the 2025 report, dated 2026-10-07, stated in the record's own `authored_by` field; no hash from an issuing body | the 2025 evaluation's own recorded result, criterion by criterion |
| `docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register.json` | historical | submission record | operator supplied | the operator, named in the register's own `provenance/declared_by` field; no hash from an issuing body | the fidelity register over the sanitised copy, with the submission's declared facts |
| `docs/tier4_orchestration_state/decision_log/msca-dn-pe01-workspace_2026-10-04.json` | cross_era | repository decision | computed only | — | the PE-01 decision, which declares the 2025 call identifier Assumed |
| `harness/evaluator_scorecard_msca_dn.json` (v2.2) | current | derived configuration | computed only | — | the scoring contract derived from the 2026 evaluation form |
| `harness/profiles/msca_dn_2026_default.json` | current | derived configuration | computed only | — | the 2026 pre-evaluation profile the matrix compares against |
| `harness/criterion_appendix_mapping_msca_dn.json` | current | derived configuration | computed only | — | the criterion-to-table routing derived from the 2026 form |
| `plans/msca_dn_pre_evaluation_spec.md` | cross_era | repository decision | computed only | — | the pre-evaluation specification, which fixes the harness's own scoring method |

No document here is authenticated by a hash from its issuing body. A document pinned in this tree
with no recorded download provenance is `computed_only`: its bytes are fixed, and nothing says
they are the official ones. A row resting only on such a document may not declare Confirmed, and
the check reports it if it does.

## What is not obtained

| Document | Era | Class | Rows it would settle |
|---|---|---|---|
| the MSCA part of the work programme in force for the 2025 call | historical | work programme | CI-01 |
| the General Annexes in force for the 2025 call | historical | programme guidance | TH-03 |
| the conditions and topic text of the 2025 Doctoral Networks call | historical | call document | CI-01, EI-02 |
| the version of the evaluation form in force for the 2025 call | historical | instrument evaluation form | CR-02, EI-01, EI-02, EI-04, TH-03, TH-05, WT-02 |

Each row is open because of a document in this table. The operator supplies them; nothing in this
repository fetches one, and no row closes by assuming what one would say.

## What a record settles, and no more

| Record | Passage | Settles | Measured |
|---|---|---|---|
| `evaluator_scorecard_msca_dn.json` | `provenance/v5_equivalence` | section mapping | the ten numbered aspect headings, Tables 3.1 a to 3.1 e, the 34-page Part B1 cap with sections 1 to 3 at 30, and Part B2 sections 4 to 10 — structure, and nothing about a scoring rule, a weight, a threshold or an evaluator instruction |

A record that measured one thing can be read as settling another. A citation of a restricted
passage from a row outside its areas is a finding, not an accepted source.

## What the author of this index is unsure of

- No entry is authenticated by a hash from its issuing body, so no matrix row may declare Confirmed and none does.
- The four unobtained documents cannot be fetched until the 2025 call identifier is settled, which row CI-01 records as unresolved.
- The stored evaluation form declares a version date later than the 2025 call's own year, and whether it was in force for that call is row EI-02's open question.
- Four entries are tracked inputs: the scorecard, the 2026 profile, the appendix mapping and the specification. Any edit to one makes the matrix stale until it is re-derived.
