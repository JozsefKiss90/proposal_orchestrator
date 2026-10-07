# Fidelity declaration drafts — operator review checklist

Ticket: R04 of plans/pe08_review_and_pe09_handoff_tickets.md  
Specification: `plans/msca_dn_pre_evaluation_spec.md`  
Review state: `agent_drafted_pending_operator_review`  
Drafted on: 2026-10-07

Both declaration inputs are absent today, so both registers carry an empty declared
half. These drafts propose what each input could say. Nothing here is an operator
declaration, and nothing here changes a disposition.

## The three claims, kept apart

| Claim | Where it is checkable | Status in these drafts |
|---|---|---|
| extraction fidelity against the sanitised PDF | here, in the derived half and the import manifest | Confirmed |
| difference between the sanitised revisions | here, in the manifest's page-by-page comparison | Confirmed |
| fidelity against the submitted original | the private network only (PE-09) | Unresolved, every sub-section of both revisions |

A present passage and a zero extraction loss are facts about the step from the PDF to
its extraction. Neither bounds the step from the submission to the PDF.

The register's `transformation` field sits on the third claim, one step above the
per-sub-section judgment. It carries the operator's PE-01 declaration about the document
as a whole, so its status is Assumed. The part that matters per sub-section — how much
prose moved — has no measurement anywhere in this repository.

## Revision `sanitised_v1`

- Draft: `docs/tier4_orchestration_state/msca_dn/declarations/draft_sanitised_v1.json`
- Adoption target: `docs/tier3_project_instantiation/source_materials/msca_dn/declarations/sanitised_v1.json`
- Register: `docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register.json` `5c9ce4e34af8c120…`
- Sub-sections declared: 15 of 15 in the derived inventory
- Carried through from the operator unchanged: none

| Sub-section | Presence | Revision difference | Original fidelity | Dependent ESR rows | Decision needed |
|---|---|---|---|---|---|
| `1.1` | Confirmed | first revision, no predecessor | Unresolved | — | confirm presence and transformation |
| `1.2` | Confirmed | first revision, no predecessor | Unresolved | — | confirm presence and transformation |
| `1.3` | Confirmed | first revision, no predecessor | Unresolved | — | confirm presence and transformation |
| `1.4` | Confirmed | first revision, no predecessor | Unresolved | — | confirm presence and transformation |
| `2.1` | Confirmed | first revision, no predecessor | Unresolved | — | confirm presence and transformation |
| `2.2` | Confirmed | first revision, no predecessor | Unresolved | — | confirm presence and transformation |
| `2.3` | Confirmed | first revision, no predecessor | Unresolved | — | confirm presence and transformation |
| `2.4` | Confirmed | first revision, no predecessor | Unresolved | — | confirm presence and transformation |
| `3.1` | Confirmed, 1 caveat(s) | first revision, no predecessor | Unresolved | — | confirm presence and transformation |
| `3.2` | Confirmed, 1 caveat(s) | first revision, no predecessor | Unresolved | — | confirm presence and transformation |
| `4` | Confirmed | first revision, no predecessor | Unresolved | — | confirm presence and transformation |
| `5` | Confirmed | first revision, no predecessor | Unresolved | — | confirm presence and transformation |
| `6` | Confirmed | first revision, no predecessor | Unresolved | — | confirm presence and transformation |
| `7` | Confirmed | first revision, no predecessor | Unresolved | — | confirm presence and transformation |
| `8` | Confirmed, 1 caveat(s) | first revision, no predecessor | Unresolved | — | confirm presence and transformation |

### Declarations checked against measurement

| Declaration | Verdict |
|---|---|
| `docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register.json#provenance/transformation/figures` | holds |
| `docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register.json#provenance/transformation/citations` | holds |
| `docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register.json#provenance/transformation/reformatting/body_point_size` | holds |
| `docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register.json#provenance/transformation/reformatting/table_3_1a` | qualified_in_place |

No declaration of this revision is contradicted by measurement.

### What adoption changes

Register sha256 before adoption: `5c9ce4e34af8c120ce266effba7ee7719e92cff91671de1be1f3bcb3e205e4e9`

Adopting a declaration rewrites this register, so every artifact that pinned its
bytes has to be re-recorded or explained. Measured, not listed by hand:

| Artifact | Records |
|---|---|
| `docs/tier4_orchestration_state/decision_log/msca-dn-pe03-external-proposal-import_2026-10-04.json` | the full sha256 |
| `docs/tier4_orchestration_state/validation_reports/msca-dn-pe03-external-proposal-import_2026-10-04.json` | the full sha256 |

Artifacts that name the register by path, hash or not: `docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register_resolved_fixes.json`, `docs/tier4_orchestration_state/decision_log/msca-dn-fidelity-declaration-drafts_2026-10-07.json`, `docs/tier4_orchestration_state/decision_log/msca-dn-fidelity-declaration-input_2026-10-07.json`, `docs/tier4_orchestration_state/decision_log/msca-dn-pe01-workspace_2026-10-04.json`, `docs/tier4_orchestration_state/decision_log/msca-dn-pe03-external-proposal-import_2026-10-04.json`, `docs/tier4_orchestration_state/decision_log/msca-dn-pe03-resolved-fixes-revision_2026-10-06.json`, `docs/tier4_orchestration_state/decision_log/msca-dn-pe07-label-aware-wp-header_2026-10-06.json`, `docs/tier4_orchestration_state/decision_log/msca-dn-semantic-adjudication_2026-10-07.json`, `docs/tier4_orchestration_state/validation_reports/msca-dn-pe03-external-proposal-import_2026-10-04.json`, `workspaces/msca_dn/docs/tier4_orchestration_state/dev_graph/imports/MSCA-DN-2025_sanitised_part_b.json`, `workspaces/msca_dn/docs/tier4_orchestration_state/dev_graph/imports/MSCA-DN-2025_sanitised_part_b.resolved_fixes.json`, `workspaces/msca_dn/docs/tier4_orchestration_state/dev_graph/intake/msca-dn-2025-sanitised-v1.json`, `plans/pe08_review_and_pe09_handoff_tickets.md`.

The import manifest `workspaces/msca_dn/docs/tier4_orchestration_state/dev_graph/imports/MSCA-DN-2025_sanitised_part_b.json` is unaffected. The manifest renders the derived half and the page comparison. Neither reads a declaration, so adoption leaves its bytes as they are. Artifacts pinning its bytes: none.

The historical artifacts stay as written. A comparison that pinned the old hash stays replayable from the register version it names, so a re-recording is a successor artifact and never an edit in place.

Steps:

1. Record the operator review of this draft, row by row.
2. Correct each row the review changes, and replace every row's 'declared_by' with the operator's own attribution.
3. Write the reviewed payload to docs/tier3_project_instantiation/source_materials/msca_dn/declarations/sanitised_v1.json (py -3.10 -m tools.draft_fidelity_declarations --emit-input sanitised_v1 prints this draft's payload unchanged).
4. py -3.10 -m tools.author_msca_dn_workspace  (the first revision's register)
5. py -3.10 -m tools.import_external_proposal  (every revision's register)
6. py -3.10 -m tools.author_msca_dn_workspace --check  and  py -3.10 -m tools.import_external_proposal --check  (both exit 0)
7. Re-record the register hash in every artifact this draft lists under adoption/pinned_by_hash, or state why each stays as written.

## Revision `resolved_fixes`

- Draft: `docs/tier4_orchestration_state/msca_dn/declarations/draft_resolved_fixes.json`
- Adoption target: `docs/tier3_project_instantiation/source_materials/msca_dn/declarations/resolved_fixes.json`
- Register: `docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register_resolved_fixes.json` `aafed265f4e9b43b…`
- Sub-sections declared: 15 of 15 in the derived inventory
- Carried through from the operator unchanged: none

| Sub-section | Presence | Revision difference | Original fidelity | Dependent ESR rows | Decision needed |
|---|---|---|---|---|---|
| `1.1` | Confirmed | unchanged from sanitised_v1 | Unresolved | ESR-E-03 | confirm presence and transformation; the draft carries an open question on ESR-E-03 |
| `1.2` | Confirmed | unchanged from sanitised_v1 | Unresolved | ESR-E-01, ESR-E-02, ESR-E-06 | confirm presence and transformation; the draft carries an open question on ESR-E-01, ESR-E-02 |
| `1.3` | Confirmed | unchanged from sanitised_v1 | Unresolved | ESR-E-07, ESR-E-08 | confirm presence and transformation; the draft carries an open question on ESR-E-07, ESR-E-08 |
| `1.4` | Confirmed | unchanged from sanitised_v1 | Unresolved | ESR-E-09 | confirm presence and transformation; the draft carries an open question on ESR-E-09 |
| `2.1` | Confirmed | unchanged from sanitised_v1 | Unresolved | — | confirm presence and transformation |
| `2.2` | Confirmed | unchanged from sanitised_v1 | Unresolved | ESR-E-08 | confirm presence and transformation; the draft carries an open question on ESR-E-08 |
| `2.3` | Confirmed | unchanged from sanitised_v1 | Unresolved | ESR-I-01 | confirm presence and transformation |
| `2.4` | Confirmed | unchanged from sanitised_v1 | Unresolved | ESR-I-02 | confirm presence and transformation |
| `3.1` | Confirmed, 1 caveat(s) | changed from sanitised_v1: re-typeset page(s) 45; paragraphs 145 → 142, characters 27977 → 28087 | Unresolved | ESR-E-03, ESR-E-04, ESR-Q-01, ESR-Q-02, ESR-Q-03, ESR-Q-04 | confirm presence and transformation; the draft carries an open question on ESR-E-03, ESR-E-04, ESR-Q-01, ESR-Q-02, ESR-Q-03 |
| `3.2` | Confirmed, 1 caveat(s) | unchanged from sanitised_v1 | Unresolved | ESR-Q-01 | confirm presence and transformation; the draft carries an open question on ESR-Q-01 |
| `4` | Confirmed | unchanged from sanitised_v1 | Unresolved | — | confirm presence and transformation |
| `5` | Confirmed | unchanged from sanitised_v1 | Unresolved | ESR-Q-S03 | confirm presence and transformation; the draft carries an open question on ESR-Q-S03 |
| `6` | Confirmed | unchanged from sanitised_v1 | Unresolved | — | confirm presence and transformation |
| `7` | Confirmed | unchanged from sanitised_v1 | Unresolved | — | confirm presence and transformation |
| `8` | Confirmed, 1 caveat(s) | unchanged from sanitised_v1 | Unresolved | ESR-Q-S02 | confirm presence and transformation; the draft carries an open question on ESR-Q-S02 |

### Declarations checked against measurement

| Declaration | Verdict |
|---|---|
| `docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register_resolved_fixes.json#provenance/transformation/figures` | holds |
| `docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register_resolved_fixes.json#provenance/transformation/citations` | holds |
| `docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register_resolved_fixes.json#provenance/transformation/reformatting/body_point_size` | contradicted |
| `docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register_resolved_fixes.json#provenance/transformation/reformatting/table_3_1a` | qualified_in_place |

### Corrections proposed

- `docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register_resolved_fixes.json#provenance/transformation/reformatting/body_point_size`
  - declared: 12
  - measured: derived/body_point_size: the body is 12.0 pt; other sizes 10.0 pt over 1040 character(s), 9.8 pt over 458 character(s); other_sizes_are_bullets_and_spaces_only = false
  - proposed: Replace the bare declaration 12 with a statement that the body of this revision is set at 12.0 pt except for 458 character(s) at 9.8 pt that carry prose rather than bullets, and name derived/body_point_size as the measurement. The declaration is the operator's, so this correction is a proposal: applying it edits the provenance literal in tools/author_msca_dn_workspace.py and changes the register's bytes.
  - status of the contradiction: Confirmed — the contradiction is measured, in the derived half of this register. Which page carries the smaller prose is Inferred and not asserted here: the only changed page of this revision is the one the import manifest names, and the derived half records no page for the size.
  - reviewer status: `agent_drafted_pending_operator_review`

### Declaration-dependent rows with no sub-section

The dispositions record names no sub-section for these, so nothing here assigns
one. Each needs the operator to name it.

- **ESR-I-S01** (independently_detected)
  - Confirm the appendix secondment months in this copy are the submission's. If they are, decide whether the 80% contradiction enters the R05 revision plan as a correction the ESR did not ask for.
  - Name the sub-section whose declaration this row depends on. Nothing here infers it from the wording.

### What adoption changes

Register sha256 before adoption: `aafed265f4e9b43b9d88d13f394fef2e812cbfa5405d53bb6720cb303c9ecfc1`

Adopting a declaration rewrites this register, so every artifact that pinned its
bytes has to be re-recorded or explained. Measured, not listed by hand:

| Artifact | Records |
|---|---|
| `docs/tier4_orchestration_state/msca_dn/comparisons/comparison_f60ae6e0a2a1_0001.json` | the full sha256 |
| `docs/tier4_orchestration_state/msca_dn/esr/semantic_adjudications_f60ae6e0a2a1.json` | the full sha256 |
| `docs/tier4_orchestration_state/msca_dn/reviews/operator_review_9732dde50039_0001.md` | the first 16 characters |
| `docs/tier4_orchestration_state/msca_dn/reviews/operator_review_9732dde50039_0002.md` | the first 16 characters |

Artifacts that name the register by path, hash or not: `docs/tier4_orchestration_state/decision_log/msca-dn-fidelity-declaration-drafts_2026-10-07.json`, `docs/tier4_orchestration_state/decision_log/msca-dn-fidelity-declaration-input_2026-10-07.json`, `docs/tier4_orchestration_state/decision_log/msca-dn-pe03-resolved-fixes-revision_2026-10-06.json`, `docs/tier4_orchestration_state/decision_log/msca-dn-pe07-label-aware-wp-header_2026-10-06.json`, `docs/tier4_orchestration_state/decision_log/msca-dn-semantic-adjudication_2026-10-07.json`, `docs/tier4_orchestration_state/msca_dn/comparisons/comparison_f60ae6e0a2a1_0001.json`, `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1.json`, `docs/tier4_orchestration_state/msca_dn/esr/semantic_adjudications_f60ae6e0a2a1.json`, `docs/tier4_orchestration_state/msca_dn/reviews/operator_review_9732dde50039_0001.md`, `docs/tier4_orchestration_state/msca_dn/reviews/operator_review_9732dde50039_0002.md`, `workspaces/msca_dn/docs/tier4_orchestration_state/dev_graph/imports/MSCA-DN-2025_sanitised_part_b.resolved_fixes.json`.

The import manifest `workspaces/msca_dn/docs/tier4_orchestration_state/dev_graph/imports/MSCA-DN-2025_sanitised_part_b.resolved_fixes.json` is unaffected. The manifest renders the derived half and the page comparison. Neither reads a declaration, so adoption leaves its bytes as they are. Artifacts pinning its bytes: none.

The historical artifacts stay as written. A comparison that pinned the old hash stays replayable from the register version it names, so a re-recording is a successor artifact and never an edit in place.

Steps:

1. Record the operator review of this draft, row by row.
2. Correct each row the review changes, and replace every row's 'declared_by' with the operator's own attribution.
3. Write the reviewed payload to docs/tier3_project_instantiation/source_materials/msca_dn/declarations/resolved_fixes.json (py -3.10 -m tools.draft_fidelity_declarations --emit-input resolved_fixes prints this draft's payload unchanged).
4. py -3.10 -m tools.author_msca_dn_workspace  (the first revision's register)
5. py -3.10 -m tools.import_external_proposal  (every revision's register)
6. py -3.10 -m tools.author_msca_dn_workspace --check  and  py -3.10 -m tools.import_external_proposal --check  (both exit 0)
7. Re-record the register hash in every artifact this draft lists under adoption/pinned_by_hash, or state why each stays as written.

## What stays open

- Every `fidelity_to_submitted_original` row is Unresolved. Only a reading against the
  submitted original, inside the private network, can change that (PE-09).
- A declaration drafted here is an agent's proposal. Each row's `declared_by` says so,
  and the operator replaces it on adoption.
- Adoption is the operator's act. This renderer never writes into
  `docs/tier3_project_instantiation/source_materials/msca_dn/declarations`.

## The adoption record this review still owes

No adoption or provenance record exists yet, because no operator review has been
recorded. When one is, it must carry:

- the reviewer, the date, and the draft sha256 the review was taken over
- a per-row decision: adopted as drafted, adopted as corrected, or withheld
- the register sha256 before and after, and what each pinned artifact now records
- every row whose status the review changed, and the evidence that moved it
- which proposed corrections to the provenance header were applied, and which stand

