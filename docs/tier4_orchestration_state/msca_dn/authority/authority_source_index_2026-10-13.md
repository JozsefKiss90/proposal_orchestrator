# Authority source index — the authority documents of the 2025 MSCA Doctoral Networks call and of the 2026 call the current profile was written for

Authored 2026-10-13. Index `msca_dn_authority_sources_2026-10-13`, schema `authority_source_index/2`,
written by `tools/author_msca_dn_authority_matrix.py`.

Review state: **agent drafted pending operator review**.
The index's own reading of its documents is declared **Inferred**.
Relationship to earlier versions: the authority source index and equivalence matrix authored on 2026-10-12, `docs/tier4_orchestration_state/msca_dn/authority/authority_source_index_2026-10-12.json` (sha256 6a93702973a16f7daccea522c9a7543e129a3d4a170be6215b7265029bc4cae5) and `docs/tier4_orchestration_state/msca_dn/authority/equivalence_matrix_2025_2026-10-12.json` (sha256 115949d3fe4858340128a6ce1fc3afe83f28a085347714752ccf1ca9d9453bcd). Those two declared four 2025 documents absent. Three of them have since been obtained and the fourth is not a document this repository needs, so the entries and the rows resting on their absence are restated here. The superseded pair stays in the tree unedited: a correction to an index is a successor index, and the record of what was believed on 2026-10-12 is part of the evidence.

16 documents are indexed. 15 are obtained and pinned by sha256, and 1 required ones are not
obtained. The 2025 era is the submission's; the 2026 era is the one the current profile was
written for. A citation of an unobtained document fails `harness.authority_matrix.check`.

## What is obtained

| Document | Era | Class | States |
|---|---|---|---|
| `docs/tier2a_instrument_schemas/application_forms/msca/af_he-msca-dn_en.pdf` (v5.0) | historical | instrument application form | the MSCA Doctoral Networks application form of the 2025 call, Part B template included |
| `docs/tier2a_instrument_schemas/application_forms/msca/Tpl_Application Form (Part B) (HE MSCA DN).pdf` (v6.0) | current | instrument application form | the Part B template of the 2026 call |
| `docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_en.pdf` (v2.2) | current | instrument evaluation form | the evaluation form the 2026 scorecard is derived from |
| `docs/tier1_normative_framework/programme_guidance/wp-15-general-annexes_horizon-2026-2027_en.pdf` | current | programme guidance | the General Annexes of the 2026-2027 work programme |
| `docs/tier2b_topic_and_call_sources/work_programmes/msca/wp-2-marie-sklodowska-curie-actions_horizon-2026-2027_en.pdf` | current | work programme | the MSCA part of the 2026-2027 work programme |
| `docs/tier2b_topic_and_call_sources/work_programmes/msca/wp-2-msca-actions_horizon-2023-2025_en.pdf` | historical | work programme | the MSCA part of the work programme the 2025 call was opened under, carrying that call's own conditions and topic text, its award criteria, its weighting and its funding threshold |
| `docs/tier1_normative_framework/programme_guidance/wp-14-general-annexes_horizon-2025_en.pdf` | historical | programme guidance | the General Annexes of the work programme the 2025 call was opened under, whose award-criteria table refers training and mobility actions to the work programme part pinned above |
| `docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_v2.0_2025-02-28.pdf` (v2.0) | historical | instrument evaluation form | the version of the evaluation form served at the issuing body's template address through the 2025 call window, carrying that form's own scoring, threshold and weighting statements |
| `docs/tier4_orchestration_state/msca_dn/esr/msca-dn-2025-esr.json` | historical | evaluation output | the 2025 evaluation's own recorded result, criterion by criterion |
| `docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register.json` | historical | submission record | the fidelity register over the sanitised copy, with the submission's declared facts |
| `docs/tier4_orchestration_state/decision_log/msca-dn-pe01-workspace_2026-10-04.json` | cross_era | repository decision | the PE-01 decision, which declares the 2025 call identifier Assumed |
| `harness/evaluator_scorecard_msca_dn.json` (v2.2) | current | derived configuration | the scoring contract derived from the 2026 evaluation form |
| `harness/profiles/msca_dn_2026_default.json` | current | derived configuration | the 2026 pre-evaluation profile the matrix compares against |
| `harness/criterion_appendix_mapping_msca_dn.json` | current | derived configuration | the criterion-to-table routing derived from the 2026 form |
| `plans/msca_dn_pre_evaluation_spec.md` | cross_era | repository decision | the pre-evaluation specification, which fixes the harness's own scoring method |

### Three questions, asked separately

Byte integrity asks whether the bytes are fixed and reproducible. Source authenticity asks whether
they are the ones the issuing body published. Historical applicability asks whether this was the
version in force for the era the document states rules for. They are different questions with
different answers, and one column answering all three is how a file hashed locally comes to read
as an authenticated authority.

| Document | Byte integrity | Source authenticity | Historical applicability |
|---|---|---|---|
| `af_he-msca-dn_en.pdf` | computed only | unrecorded | unresolved |
| `Tpl_Application Form (Part B) (HE MSCA DN).pdf` | computed only | unrecorded | not applicable |
| `ef_he-msca_en.pdf` | computed only | independently corroborated | not applicable |
| `wp-15-general-annexes_horizon-2026-2027_en.pdf` | computed only | unrecorded | not applicable |
| `wp-2-marie-sklodowska-curie-actions_horizon-2026-2027_en.pdf` | computed only | unrecorded | not applicable |
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | computed only | independently corroborated | in force confirmed |
| `wp-14-general-annexes_horizon-2025_en.pdf` | computed only | independently corroborated | in force confirmed |
| `ef_he-msca_v2.0_2025-02-28.pdf` | computed only | retrieved from web archive | bracketed not conclusive |
| `msca-dn-2025-esr.json` | operator supplied | not applicable | not applicable |
| `fidelity_register.json` | operator supplied | not applicable | not applicable |
| `msca-dn-pe01-workspace_2026-10-04.json` | computed only | unrecorded | not applicable |
| `evaluator_scorecard_msca_dn.json` | computed only | unrecorded | not applicable |
| `msca_dn_2026_default.json` | computed only | unrecorded | not applicable |
| `criterion_appendix_mapping_msca_dn.json` | computed only | unrecorded | not applicable |
| `msca_dn_pre_evaluation_spec.md` | computed only | unrecorded | not applicable |

| Document | Axis | What it rests on |
|---|---|---|
| `ef_he-msca_en.pdf` | source authenticity | an independent archive of the issuing body's template address serves these bytes. The file was already in this tree, and the archived capture was read afterwards and agrees with it byte for byte |
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | source authenticity | retrieved from the issuing body's published address and, the same day, from that body's own second site for this work programme; the two downloads agree byte for byte, and both agree with the file pinned here |
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | historical applicability | the document states the call it governs. Page 23 carries the 2025 Doctoral Networks call heading with its identifier, its opening date and its deadline, and the cover carries the Commission Decision the General Annexes pinned here carry too |
| `wp-14-general-annexes_horizon-2025_en.pdf` | source authenticity | the operator placed the file, and the issuing body's published address was read afterwards and served the same bytes; the placement and the retrieval are independent of each other and agree |
| `wp-14-general-annexes_horizon-2025_en.pdf` | historical applicability | the document's cover names the 2025 work programme and the Commission Decision that adopted it, which is the decision the work programme part pinned here carries as well, so the two are parts of one adopted programme |
| `ef_he-msca_v2.0_2025-02-28.pdf` | source authenticity | the template address serves whichever version is current and now serves a later one, so these bytes come from an independent archive of that address. One archive is one witness: no second, independent copy of this version was found |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical applicability | three captures of the template address carry one archive digest, dated inside the call window and the last of them twenty days before the deadline, and the next distinct digest is months after it. That brackets the window without closing it. A version served between two captures and never captured would leave no trace here |
| `msca-dn-2025-esr.json` | byte integrity | an operator transcription of the 2025 report, dated 2026-10-07, stated in the record's own `authored_by` field; no hash from an issuing body |
| `fidelity_register.json` | byte integrity | the operator, named in the register's own `provenance/declared_by` field; no hash from an issuing body |

A rank that claims evidence must name it. `check` reports any entry whose authentication,
authenticity or applicability claims more than `unrecorded` and records no basis. No entry carries
a hash published by its issuing body, so no row may declare Confirmed on byte integrity alone; and
a row citing a historical source whose applicability is bracketed or unresolved may not declare
Confirmed either, because that source fixes a wording and not a rule in force.

## Where the bytes came from

| Document | Title it gives itself | Retrieved | From |
|---|---|---|---|
| `ef_he-msca_en.pdf` | Horizon Europe Evaluation Form (HE MSCA) v2.2, 2025-12-17 | 2026-10-13 | https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/temp-form/ef/ef_he-msca_en.pdf |
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | Horizon Europe Work Programme 2023-2025, 2. Marie Sklodowska-Curie Actions, 2025-05-14 | 2026-10-13 | https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-2-msca-actions_horizon-2023-2024_en.pdf |
| `wp-14-general-annexes_horizon-2025_en.pdf` | Horizon Europe Work Programme 2025, 14. General Annexes, 2025-05-14 | 2026-10-13 | placed by the operator, then read from the published address |
| `ef_he-msca_v2.0_2025-02-28.pdf` | Horizon Europe Evaluation Form (HE MSCA) v2.0, 2025-02-28 | 2026-10-13 | https://web.archive.org/web/20250619081843id_/https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/temp-form/ef/ef_he-msca_en.pdf |

**`ef_he-msca_en.pdf`**

- Published address: https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/temp-form/ef/ef_he-msca_en.pdf
- Captured 2026-03-12 by an independent archive, archive digest `FQSNHZPEEYLINX6FCJHO566PIL27Y6UK`
- Same bytes from https://web.archive.org/web/20260312122434id_/https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/temp-form/ef/ef_he-msca_en.pdf — the archived capture of the published address, read into a scratch file and hashed; it is this entry's bytes

**`wp-2-msca-actions_horizon-2023-2025_en.pdf`**

- Published address: https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2023-2024/wp-2-msca-actions_horizon-2023-2024_en.pdf
- Same bytes from https://marie-sklodowska-curie-actions.ec.europa.eu/sites/default/files/2025-05/wp-2-msca-actions_horizon-2023-2024_en.pdf — the issuing body's second site for this work programme, a different host and a different path from the published address
- Stored filename: stored under the edition its cover declares. The published filename says 2023-2024, which names neither the edition nor the decision the document itself carries, and a reader who trusted it would cite the wrong year

**`wp-14-general-annexes_horizon-2025_en.pdf`**

- Published address: https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2025/wp-14-general-annexes_horizon-2025_en.pdf
- Same bytes from https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2025/wp-14-general-annexes_horizon-2025_en.pdf — the published address, read after the operator placed the file

**`ef_he-msca_v2.0_2025-02-28.pdf`**

- Published address: https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/temp-form/ef/ef_he-msca_en.pdf
- Captured 2025-06-19 by an independent archive, archive digest `ODDXOSHI52ABE7ZJQ4EWCIHCNHHR5YBU`
- Captured 2025-10-03 by an independent archive, archive digest `ODDXOSHI52ABE7ZJQ4EWCIHCNHHR5YBU`
- Captured 2025-11-05 by an independent archive, archive digest `ODDXOSHI52ABE7ZJQ4EWCIHCNHHR5YBU`
- Stored filename: stored under its declared version and date. The published address carries one filename for every version, and that filename is already taken in this tree by the later version pinned above

## What is not obtained

| Document | Era | Class | Rows it would settle |
|---|---|---|---|
| the submission's own acknowledgement of receipt, which would bind this submission to a call identifier rather than leaving the binding declared | historical | submission record | CI-01 |

Each row is open because of a document in this table. No row closes by assuming what one would
say, and a citation of one fails the check.

## What a record settles, and no more

| Record | Passage | Settles | Measured |
|---|---|---|---|
| `evaluator_scorecard_msca_dn.json` | `provenance/v5_equivalence` | section mapping | the ten numbered aspect headings, Tables 3.1 a to 3.1 e, the 34-page Part B1 cap with sections 1 to 3 at 30, and Part B2 sections 4 to 10 — structure, and nothing about a scoring rule, a weight, a threshold or an evaluator instruction |

A record that measured one thing can be read as settling another. A citation of a restricted
passage from a row outside its areas is a finding, not an accepted source.

## What the author of this index is unsure of

- No entry is authenticated by a hash from its issuing body, so no matrix row may declare Confirmed and none does. Three documents are corroborated by a second independent copy, which is evidence of origin and not an issuer's hash.
- The 2025 evaluation form's place in the call is bracketed and not closed. Three captures of its published address carry one digest, the last of them twenty days before the deadline, and a version served between captures and never captured would leave no trace. Row EI-02 keeps that open.
- The 2025 application form has no recorded origin and no established place in the call. It was in this tree before any retrieval was made, and the five rows citing it are Inferred for that reason.
- No separate 2025 call document is held, and none is needed: the work programme part pinned here carries the call's own conditions and topic text, and the rows about them cite its pages.
- The submission's binding to a call identifier is declared, not evidenced. The one unobtained entry is the document that would settle it.
- Four entries are tracked inputs: the scorecard, the 2026 profile, the appendix mapping and the specification. Any edit to one makes the matrix stale until it is re-derived.
