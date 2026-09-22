# PURGE MANIFEST — FIELDWISE project purge (2026-09-22)

Phase 1 inventory. Nothing listed here has been deleted. Base: branch `ESR` at `e56ede2`.

Legend: T = tracked by git (`git rm`), U = untracked or ignored (plain delete).

## Summary

| Group | Files | Tracked | Size |
|---|---:|---:|---:|
| A. Tier 3 project instantiation | 28 | 28 | 14.4 MB |
| B. Tier 4 orchestration state | 205 | 205 | 1.6 MB |
| C. Tier 5 deliverables | 21 | 21 | 3.7 MB |
| D. Plans, prompts, reports | 45 | 45 | 1.7 MB |
| E. Root-level strays | 10 | 7 | 1.4 MB |
| G. Instance-#1 vault (MSCA/) | 421 | 218 | 19.6 MB |
| F. Ignored runtime state | 1411 | 0 | 33.0 MB |
| **Total (A–G)** | **2141** | **524** | **75.3 MB** |

## A. Tier 3 project instantiation

28 files, 28 tracked, 14.4 MB.

| Path | T/U | Size | Reason |
|---|:-:|---:|---|
| `docs/tier3_project_instantiation/architecture_inputs/impacts.json` | T | 18.2 KB | FIELDWISE architecture seeds |
| `docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json` | T | 7.2 KB | FIELDWISE architecture seeds |
| `docs/tier3_project_instantiation/architecture_inputs/objectives.json` | T | 6.8 KB | FIELDWISE architecture seeds |
| `docs/tier3_project_instantiation/architecture_inputs/outcomes.json` | T | 8.7 KB | FIELDWISE architecture seeds |
| `docs/tier3_project_instantiation/architecture_inputs/risks.json` | T | 6.0 KB | FIELDWISE architecture seeds |
| `docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json` | T | 29.9 KB | FIELDWISE architecture seeds |
| `docs/tier3_project_instantiation/call_binding/compliance_profile.json` | T | 809 B | Project binding to the call; a new project re-derives it |
| `docs/tier3_project_instantiation/call_binding/confirmation_checklist.json` | T | 38.2 KB | Project binding to the call; a new project re-derives it |
| `docs/tier3_project_instantiation/call_binding/selected_call.json` | T | 5.0 KB | Project binding to the call; a new project re-derives it |
| `docs/tier3_project_instantiation/call_binding/topic_mapping.json` | T | 6.6 KB | Project binding to the call; a new project re-derives it |
| `docs/tier3_project_instantiation/consortium/capabilities.json` | T | 48.3 KB | FIELDWISE consortium data |
| `docs/tier3_project_instantiation/consortium/partners.json` | T | 33.5 KB | FIELDWISE consortium data |
| `docs/tier3_project_instantiation/consortium/roles.json` | T | 18.3 KB | FIELDWISE consortium data |
| `docs/tier3_project_instantiation/hand_lift_provenance.json` | T | 26.3 KB | FIELDWISE project-level record |
| `docs/tier3_project_instantiation/project_brief/concept_note.md` | T | 12.3 KB | FIELDWISE concept and positioning |
| `docs/tier3_project_instantiation/project_brief/project_summary.json` | T | 7.6 KB | FIELDWISE concept and positioning |
| `docs/tier3_project_instantiation/project_brief/strategic_positioning.md` | T | 7.8 KB | FIELDWISE concept and positioning |
| `docs/tier3_project_instantiation/project_brief/training_and_career_development.md` | T | 15.5 KB | FIELDWISE concept and positioning |
| `docs/tier3_project_instantiation/source_materials/consolidated_pack_2026-08-28/decision_inputs_2026-08.md` | T | 32.7 KB | FIELDWISE evidence base (CV, references, drafts, packs) |
| `docs/tier3_project_instantiation/source_materials/consolidated_pack_2026-08-28/FIELDWISE_Consolidated_Partner_Review_Pack_2026-08-28.docx` | T | 63.5 KB | FIELDWISE evidence base (CV, references, drafts, packs) |
| `docs/tier3_project_instantiation/source_materials/consolidated_pack_2026-08-28/FIELDWISE_Consolidated_Partner_Review_Pack_2026-08-28.extracted.txt` | T | 69.0 KB | FIELDWISE evidence base (CV, references, drafts, packs) |
| `docs/tier3_project_instantiation/source_materials/cv/JT_CV-HUN-2025-MGI-Janda-Tibor.pdf` | T | 340.9 KB | FIELDWISE evidence base (CV, references, drafts, packs) |
| `docs/tier3_project_instantiation/source_materials/operator_input_pack/fieldwise_operator_input_pack.md` | T | 179.1 KB | FIELDWISE evidence base (CV, references, drafts, packs) |
| `docs/tier3_project_instantiation/source_materials/part_b_draft_v0/FIELDWISE_MSCA_Master_Draft.docx` | T | 54.7 KB | FIELDWISE evidence base (CV, references, drafts, packs) |
| `docs/tier3_project_instantiation/source_materials/references/fieldwise_references.bib` | T | 26.0 KB | FIELDWISE evidence base (CV, references, drafts, packs) |
| `docs/tier3_project_instantiation/source_materials/submitted_2025/PLANTDIGISENSE_Part_B1.pdf` | T | 708.1 KB | FIELDWISE evidence base (CV, references, drafts, packs) |
| `docs/tier3_project_instantiation/working_assumptions.json` | T | 39.9 KB | FIELDWISE project-level record |
| `docs/tier2a_instrument_schemas/application_forms/msca/Tpl_Application Form (Part B) (HE MSCA PF) másolata.rtf` | T | 12.7 MB | FIELDWISE-filled copy of the Part B form misfiled in Tier 2A (§13.11 precedent; 40 FIELDWISE hits). The blank template beside it stays |

## B. Tier 4 orchestration state

205 files, 205 tracked, 1.6 MB.

**B-note.** The decision log holds 30 engine-governing rulings (the 2026-08-11 split's 'retained' group plus `c1-consistency-gate12…`). The spec puts the whole log in scope. Two modules cite rulings by id in comments only (`runner/graph_determinism_check.py` cites dod-1c, `runner/checkpoint_publisher.py` cites chk-1); no code reads them. They are marked in the reason column. Decision 3 covers where the record of this purge lives.

| Path | T/U | Size | Reason |
|---|:-:|---:|---|
| `docs/tier4_orchestration_state/checkpoints/ARCHIVE_NOTE_fieldwise-run-01.md` | T | 984 B | FIELDWISE run checkpoint / archive note |
| `docs/tier4_orchestration_state/checkpoints/ARCHIVE_NOTE_fieldwise-run-02.md` | T | 1.1 KB | FIELDWISE run checkpoint / archive note |
| `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` | T | 1.3 KB | FIELDWISE run checkpoint / archive note |
| `docs/tier4_orchestration_state/decision_log/archive/demo-run/13b-real-data-consolidation_2026-07-16.json` | T | 6.0 KB | Archived instance-#0 (demo-run) project decisions; superseded twice |
| `docs/tier4_orchestration_state/decision_log/archive/demo-run/action-confirmation-msca-pf_2026-07-13.json` | T | 4.2 KB | Archived instance-#0 (demo-run) project decisions; superseded twice |
| `docs/tier4_orchestration_state/decision_log/archive/demo-run/synthetic-concept-override-extension_2026-07-14.json` | T | 8.8 KB | Archived instance-#0 (demo-run) project decisions; superseded twice |
| `docs/tier4_orchestration_state/decision_log/archive/demo-run/synthetic-spine-demo-override_2026-07-13.json` | T | 5.9 KB | Archived instance-#0 (demo-run) project decisions; superseded twice |
| `docs/tier4_orchestration_state/decision_log/archive/demo-run/tier3-hand-lift-msca-pf_2026-07-13.json` | T | 4.6 KB | Archived instance-#0 (demo-run) project decisions; superseded twice |
| `docs/tier4_orchestration_state/decision_log/archive/drafting_review_status copy.json` | T | 12.8 KB | Archived instance-#0 (demo-run) project decisions; superseded twice |
| `docs/tier4_orchestration_state/decision_log/archive/drafting_review_status.json` | T | 14.1 KB | Archived instance-#0 (demo-run) project decisions; superseded twice |
| `docs/tier4_orchestration_state/decision_log/archive/phase8_checkpoint.json` | T | 790 B | Archived instance-#0 (demo-run) project decisions; superseded twice |
| `docs/tier4_orchestration_state/decision_log/archive/phase8_checkpoint_03.json` | T | 1.3 KB | Archived instance-#0 (demo-run) project decisions; superseded twice |
| `docs/tier4_orchestration_state/decision_log/archive/phase8_checkpoint_03b_pre-g11uc02-rerun.json` | T | 1.3 KB | Archived instance-#0 (demo-run) project decisions; superseded twice |
| `docs/tier4_orchestration_state/decision_log/c1-consistency-gate12-unit-cost-conditionalisation_2026-09-03.json` | T | 4.2 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/chk-1-checkpoint-provenance-quad_2026-07-24.json` | T | 6.6 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/d14-refinement-finalization-standard_2026-07-14.json` | T | 4.8 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/decision-log-update_0395b136.json` | T | 4.0 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/decision-log-update_1e1b9408.json` | T | 2.5 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/decision-log-update_30665934.json` | T | 3.5 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/decision-log-update_49159a5c.json` | T | 2.9 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/decision-log-update_49dc10ca.json` | T | 5.3 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/decision-log-update_584ecd9f.json` | T | 4.1 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/decision-log-update_7612dbaf.json` | T | 4.5 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/decision-log-update_778b12ad.json` | T | 3.6 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/decision-log-update_7860a89a.json` | T | 4.2 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/decision-log-update_7acc143b.json` | T | 3.5 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/decision-log-update_7b67fe1d.json` | T | 4.9 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/decision-log-update_9468e1cf.json` | T | 4.1 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/decision-log-update_9e27694f.json` | T | 4.3 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/decision-log-update_d00fc75d.json` | T | 4.6 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/decision-log-update_fieldwis.json` | T | 3.3 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/dod-1-phase1-3-gate-result-conflict-resolution_2026-07-27.json` | T | 8.3 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/dod-1c-determinism-recheck-from-graph_2026-07-28.json` | T | 9.9 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/dod-1d-open-q4-parallel-explicit-promote_2026-07-28.json` | T | 11.1 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/dod-1e-n08f-checkpoint-published_2026-07-28.json` | T | 10.9 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/drafting-review-status-skill_2026-07-30.json` | T | 5.9 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/e2-status-aware-faithfulness-framework_2026-07-20.json` | T | 14.8 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/e3-claim-ledger-completeness_2026-07-21.json` | T | 13.9 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/e3.1-materiality-calibration_2026-08-03.json` | T | 6.1 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/e4-regression-golden-set_2026-07-21.json` | T | 5.9 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/e5f-rubric-grading-budget_2026-08-10.json` | T | 3.7 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/fieldwise-authorisation_2026-08-12.json` | T | 19.8 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-c5-unconditional-and-narrative-revert_2026-08-14.json` | T | 8.8 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-hollos-employment-reversal_2026-08-28.json` | T | 2.7 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-item13-security-green-charter_2026-08-12.json` | T | 2.7 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-item14-page-budget_2026-08-12.json` | T | 3.3 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-item3-ethics_2026-08-12.json` | T | 2.5 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-item4-governance_2026-08-12.json` | T | 4.0 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-item5-kpis_2026-08-12.json` | T | 4.0 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-item6-career-development-plan_2026-08-12.json` | T | 4.1 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-item8-person-months_2026-08-12.json` | T | 5.8 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-item9-unit-cost-lines_2026-08-12.json` | T | 4.4 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-mobility-confirmed-override_2026-08-14.json` | T | 6.4 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-open-items-fold_2026-08-14.json` | T | 11.4 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-p06-communication-route_2026-08-15.json` | T | 3.7 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-placeholder-fold_2026-08-14.json` | T | 16.4 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-placement-hosting_2026-08-12.json` | T | 8.0 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-placement-ip-declaration_2026-08-15.json` | T | 4.7 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-proposal-issues-triage_2026-08-31.json` | T | 5.6 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-purge-and-decision-log-split_2026-08-11.json` | T | 13.0 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-run-02-baseline_2026-08-28.json` | T | 7.2 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-run02-supersessions_2026-08-28.json` | T | 6.4 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-run03-instantiation_2026-09-02.json` | T | 13.0 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-switch-evidence-gates_2026-08-28.json` | T | 3.3 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-ticket6-fold_2026-08-12.json` | T | 10.7 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-ticket7-open-items_2026-08-12.json` | T | 7.5 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-ticket7-review-round2_2026-08-12.json` | T | 8.4 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-tier3-lift_2026-08-11.json` | T | 16.6 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/fieldwise-training-career-lift_2026-08-13.json` | T | 8.2 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/final-export-writer-component_2026-07-30.json` | T | 6.4 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/gate-result-schema-id-fix-and-backfill_2026-07-22.json` | T | 3.5 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/gate10b-canonical-cross-reference-false-positive_2026-07-17.json` | T | 5.1 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/gate_failure_phase_05_gate_impact_architect_2026-08-13T12_00_00Z.json` | T | 1.5 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/gate_failure_phase_05_gate_impact_architect_2026-08-14T00_00_00Z.json` | T | 1.4 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/gate_failure_phase_05_gate_impact_architect_2026-08-15T00_00_00Z.json` | T | 992 B | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/gate_failure_phase_05_gate_impact_architect_2026-08-29T00_00_00Z.json` | T | 1.2 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/graph-topology-d8-absorb_2026-07-16.json` | T | 5.9 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/hyg-1-bffe89d-conflict-marker-corruption-sweep_2026-07-27.json` | T | 12.6 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/lg1-coarse-claim-ledger-measured_2026-07-27.json` | T | 10.3 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/lg1_ledger_granularity_measurement_2026-07-27.json` | T | 11.2 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/milestone1-engine-integration-proof_2026-07-15.json` | T | 6.1 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/ms2-ticket8-author-proposal-graph_2026-07-20.json` | T | 12.5 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/ms2-ticket9-agnosticism-proof_2026-07-20.json` | T | 11.7 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/n08b-impact-claim-provenance-correction_2026-08-29.json` | T | 5.1 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/n08f-gate12-ei05-and-agrovir-status-corrections_2026-08-29.json` | T | 7.4 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/obsidian-graph-role-fieldwise_2026-08-17.json` | T | 6.9 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/od-round3-resolutions_2026-09-04.json` | T | 12.8 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/phase7-8-deferral_2026-07-14.json` | T | 5.8 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/runtime-skillresult-envelope-normalization_2026-07-14.json` | T | 5.7 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/runtime-truncation-fix_2026-07-14.json` | T | 7.6 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/section-type-taxonomy-drift-correction_2026-07-29.json` | T | 5.0 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/st-1-content-based-staleness_2026-07-27.json` | T | 10.0 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/stage4-partb1-condensation_2026-09-04.json` | T | 9.5 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/stage4-partb1-eligibility-language-and-footnotes_2026-09-04.json` | T | 4.8 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/stage4-partb1-prose-revision_2026-09-04.json` | T | 3.4 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/stage4-partb1-references_2026-09-04.json` | T | 2.9 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/status-vocabulary-correction_2026-07-13.json` | T | 4.2 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/tier2a-project-draft-misplacement-correction_2026-08-11.json` | T | 3.0 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/decision_log/topic-scope-check_0395b136.json` | T | 6.1 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/topic-scope-check_11d4fcae.json` | T | 7.4 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/topic-scope-check_30665934.json` | T | 5.2 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/topic-scope-check_4993d771.json` | T | 6.7 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/topic-scope-check_7acc143b.json` | T | 7.9 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/topic-scope-check_d00fc75d.json` | T | 9.5 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/topic-scope-check_fieldwis.json` | T | 7.8 KB | Runner-written run record; regenerable |
| `docs/tier4_orchestration_state/decision_log/transport-stream-json-reassembly_2026-07-30.json` | T | 5.3 KB | Engine-governing ruling (precedent 'retained' group, now in scope per spec); see B-note |
| `docs/tier4_orchestration_state/decision_log/vault-supersession-fieldwise_2026-08-11.json` | T | 4.8 KB | FIELDWISE project decision |
| `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json` | T | 3.6 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/gate_01_result.json` | T | 1.1 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/gate_result.json` | T | 1.3 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` | T | 22.3 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/gate_result.json` | T | 1.6 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/gate_result.json` | T | 1.5 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | T | 16.0 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` | T | 7.3 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gate_result.json` | T | 1.8 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/scheduling_constraints.json` | T | 4.7 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/gate_result.json` | T | 1.8 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | T | 19.7 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/gate_result.json` | T | 2.0 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | T | 24.1 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | T | 1.2 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/gate_result.json` | T | 3.7 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/unit_cost_budget.json` | T | 2.3 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/canonical_reference_pack.json` | T | 19.9 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/component_suppression_n08a_excellence_drafting.json` | T | 542 B | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/component_suppression_n08b_impact_drafting.json` | T | 526 B | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/component_suppression_n08c_implementation_drafting.json` | T | 558 B | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json` | T | 13.3 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_10a_result.json` | T | 1.4 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_10b_result.json` | T | 1.4 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_10c_result.json` | T | 1.4 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_10d_result.json` | T | 1.6 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_11_result.json` | T | 1.2 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_12_result.json` | T | 2.1 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/section_drafts/excellence/1.1.draft.json` | T | 20.2 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/section_drafts/excellence/1.2.draft.json` | T | 31.9 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/section_drafts/excellence/1.3.draft.json` | T | 29.0 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/section_drafts/excellence/1.4.draft.json` | T | 15.1 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/section_drafts/excellence/section_spine.json` | T | 283 B | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/section_drafts/impact/2.1.draft.json` | T | 26.2 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/section_drafts/impact/2.2.draft.json` | T | 24.9 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/section_drafts/impact/2.3.draft.json` | T | 19.3 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/section_drafts/impact/section_spine.json` | T | 575 B | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/section_drafts/implementation/3.1.draft.json` | T | 22.7 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/section_drafts/implementation/3.2.draft.json` | T | 30.4 KB | FIELDWISE phase output |
| `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/section_drafts/implementation/section_spine.json` | T | 723 B | FIELDWISE phase output |
| `docs/tier4_orchestration_state/reinstantiation_provenance.json` | T | 6.5 KB | FIELDWISE orchestration record |
| `docs/tier4_orchestration_state/reuse/phase8/archive/n08a_excellence_drafting.reuse.json` | T | 675 B | Phase 8 reuse cache of FIELDWISE sections |
| `docs/tier4_orchestration_state/reuse/phase8/archive/n08b_impact_drafting.reuse.json` | T | 659 B | Phase 8 reuse cache of FIELDWISE sections |
| `docs/tier4_orchestration_state/reuse/phase8/n08a_excellence_drafting.reuse.json` | T | 735 B | Phase 8 reuse cache of FIELDWISE sections |
| `docs/tier4_orchestration_state/reuse/phase8/n08b_impact_drafting.reuse.json` | T | 719 B | Phase 8 reuse cache of FIELDWISE sections |
| `docs/tier4_orchestration_state/reuse/phase8/n08c_implementation_drafting.reuse.json` | T | 751 B | Phase 8 reuse cache of FIELDWISE sections |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_1b25a128.json` | T | 6.4 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_2649ff21.json` | T | 6.9 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_2ba83477.json` | T | 6.8 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_424f577d.json` | T | 3.7 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_49dc10ca.json` | T | 6.2 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_584ecd9f.json` | T | 6.6 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_5dd0e971.json` | T | 7.4 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_7612dbaf.json` | T | 7.8 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_77de89e4.json` | T | 7.4 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_7860a89a.json` | T | 5.5 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_7b67fe1d.json` | T | 6.3 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_8167365d.json` | T | 5.8 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_822eae16.json` | T | 9.5 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_83c1f939.json` | T | 6.4 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_845413cf.json` | T | 8.8 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_9468e1cf.json` | T | 6.6 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_9a5dfb55.json` | T | 9.6 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_9aa8ea49.json` | T | 6.1 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_9e27694f.json` | T | 6.7 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_aa75ca3c.json` | T | 7.1 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_ec01fb84.json` | T | 7.2 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/constitutional-compliance-check_fieldwis.json` | T | 6.8 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/dissemination-exploitation-communication-check_42707c43.json` | T | 7.5 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/dissemination-exploitation-communication-check_46f0dc6d.json` | T | 10.6 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/dissemination-exploitation-communication-check_77eeb21d.json` | T | 9.3 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/dissemination-exploitation-communication-check_caa465d8.json` | T | 10.2 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/dissemination-exploitation-communication-check_fieldwis.json` | T | 9.8 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/fieldwise_authorisation_packet_2026-08-12.md` | T | 41.2 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/milestone-consistency-check_1b25a128.json` | T | 1.9 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/milestone-consistency-check_1e1b9408.json` | T | 1.9 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/milestone-consistency-check_424f577d.json` | T | 1.9 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/milestone-consistency-check_49159a5c.json` | T | 1.9 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/milestone-consistency-check_4caa2586.json` | T | 976 B | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/milestone-consistency-check_778b12ad.json` | T | 1.9 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/milestone-consistency-check_77de89e4.json` | T | 1.9 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/milestone-consistency-check_8167365d.json` | T | 1.9 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/milestone-consistency-check_9aa8ea49.json` | T | 1.9 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/milestone-consistency-check_bd337f0b.json` | T | 1.1 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/milestone-consistency-check_fab35320.json` | T | 1.6 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/milestone-consistency-check_fieldwis.json` | T | 1.6 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/proposal-section-traceability-check_2649ff21.json` | T | 29.0 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/proposal-section-traceability-check_2ba83477.json` | T | 21.0 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/proposal-section-traceability-check_5dd0e971.json` | T | 23.3 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/proposal-section-traceability-check_7612dbaf.json` | T | 31.6 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/proposal-section-traceability-check_7860a89a.json` | T | 3.4 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/proposal-section-traceability-check_822eae16.json` | T | 16.8 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/proposal-section-traceability-check_83c1f939.json` | T | 24.5 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/proposal-section-traceability-check_845413cf.json` | T | 2.8 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/proposal-section-traceability-check_9a5dfb55.json` | T | 31.2 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/proposal-section-traceability-check_aa75ca3c.json` | T | 32.4 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/proposal-section-traceability-check_ec01fb84.json` | T | 30.1 KB | Run-scoped validation report |
| `docs/tier4_orchestration_state/validation_reports/proposal-section-traceability-check_fieldwis.json` | T | 3.1 KB | Run-scoped validation report |

## C. Tier 5 deliverables

21 files, 21 tracked, 3.7 MB.

| Path | T/U | Size | Reason |
|---|:-:|---:|---|
| `docs/tier5_deliverables/assembled_drafts/part_b_assembled_draft.json` | T | 12.5 KB | FIELDWISE drafted section / draft / review packet |
| `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_final_2026-09-09.docx` | T | 209.8 KB | FIELDWISE export (docx/pdf/png/json) |
| `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_gantt_2026-09-06.png` | T | 58.2 KB | FIELDWISE export (docx/pdf/png/json) |
| `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_gantt_refactored_2026-09-08.png` | T | 75.2 KB | FIELDWISE export (docx/pdf/png/json) |
| `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_manual-condensed_2026-08-30.docx` | T | 196.0 KB | FIELDWISE export (docx/pdf/png/json) |
| `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_manual-condensed_2026-09-06 másolata.docx` | T | 101.4 KB | FIELDWISE export (docx/pdf/png/json) |
| `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_manual-condensed_2026-09-06.docx` | T | 108.3 KB | FIELDWISE export (docx/pdf/png/json) |
| `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_refactored_2026-09-08.docx` | T | 108.6 KB | FIELDWISE export (docx/pdf/png/json) |
| `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_refactored_2026-09-08.pdf` | T | 436.2 KB | FIELDWISE export (docx/pdf/png/json) |
| `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_Rositsa_Cholakova_v0.docx` | T | 426.4 KB | FIELDWISE export (docx/pdf/png/json) |
| `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B_draft_run-03_2026-09-04_annotated.docx` | T | 74.1 KB | FIELDWISE export (docx/pdf/png/json) |
| `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B_draft_run-03_2026-09-04_resolved.docx` | T | 78.0 KB | FIELDWISE export (docx/pdf/png/json) |
| `docs/tier5_deliverables/final_exports/final_export.json` | T | 845 B | FIELDWISE export (docx/pdf/png/json) |
| `docs/tier5_deliverables/final_exports/part_b_draft.docx` | T | 69.6 KB | FIELDWISE export (docx/pdf/png/json) |
| `docs/tier5_deliverables/final_exports/part_b_json_bundle.json` | T | 239.8 KB | FIELDWISE export (docx/pdf/png/json) |
| `docs/tier5_deliverables/proposal_sections/excellence_section.json` | T | 97.0 KB | FIELDWISE drafted section / draft / review packet |
| `docs/tier5_deliverables/proposal_sections/impact_section.json` | T | 72.7 KB | FIELDWISE drafted section / draft / review packet |
| `docs/tier5_deliverables/proposal_sections/implementation_section.json` | T | 55.1 KB | FIELDWISE drafted section / draft / review packet |
| `docs/tier5_deliverables/review_packets/review_packet.json` | T | 17.4 KB | FIELDWISE drafted section / draft / review packet |
| `docs/tier5_deliverables/submitted/FIELDWISE_101373105_submitted_2026-09-07.pdf` | T | 1.1 MB | Sealed FIELDWISE submission (preserved in tag + bundle) |
| `docs/tier5_deliverables/submitted/FIELDWISE_Part_B1_10_pages.docx` | T | 157.9 KB | Sealed FIELDWISE submission (preserved in tag + bundle) |

## D. Plans, prompts, reports

45 files, 45 tracked, 1.7 MB.

| Path | T/U | Size | Reason |
|---|:-:|---:|---|
| `plans/FIELDWISE_Part_B1_Scoring_Improvement_Brief_round2_2026-09-09.md` | T | 81.5 KB | FIELDWISE scoring brief |
| `plans/FIELDWISE_placeholder_corrections_2026-08-14.md` | T | 9.9 KB | FIELDWISE correction list |
| `plans/fieldwise_operator_input_pack.md` | T | 179.1 KB | FIELDWISE operator input pack (183 KB of project text) |
| `plans/fieldwise_reinstantiation_plan.md` | T | 21.2 KB | FIELDWISE re-instantiation plan (precedent; cited by hash in the purge record) |
| `plans/fieldwise_tickets.md` | T | 23.3 KB | FIELDWISE ticket board (precedent; cited by hash in the purge record) |
| `plans/proposal_issues.md` | T | 2.6 KB | FIELDWISE proposal issue list |
| `plans/tickets_proposal_issues_2026-09.md` | T | 10.3 KB | FIELDWISE issue tickets |
| `plans/decision_inputs.md` | T | 32.7 KB | Checked: FIELDWISE partner text (HUN-REN, crop modelling); duplicate of Tier 3 consolidated pack input |
| `plans/partb_final_drafting_strategy_2026-09-03.md` | T | 11.7 KB | FIELDWISE Part B endgame strategy |
| `plans/tickets_obsidian_graph_alignment.md` | T | 6.2 KB | Vault alignment tickets for FIELDWISE |
| `plans/prompts/FIELDWISE_ESR_evaluation_prompt_2026-09-08.md` | T | 50.2 KB | FIELDWISE ESR prompt |
| `plans/prompts/FIELDWISE_ESR_evaluation_prompt_round2_2026-09-08.md` | T | 34.9 KB | FIELDWISE ESR prompt |
| `plans/reports/~$ELDWISE_open_decisions.docx` | T | 162 B | Word lock file committed by accident |
| `plans/reports/FIELDWISE_Consolidated_Partner_Review_Pack_2026-08-28.docx` | T | 63.5 KB | FIELDWISE partner pack |
| `plans/reports/FIELDWISE_ESR_2026-09-08.json` | T | 99.4 KB | FIELDWISE evaluation summary report |
| `plans/reports/FIELDWISE_ESR_2026-09-08.md` | T | 251.6 KB | FIELDWISE evaluation summary report |
| `plans/reports/FIELDWISE_ESR_round2_2026-09-08.json` | T | 93.9 KB | FIELDWISE evaluation summary report |
| `plans/reports/FIELDWISE_ESR_round2_2026-09-08.md` | T | 208.3 KB | FIELDWISE evaluation summary report |
| `plans/reports/FIELDWISE_open_decisions.docx` | T | 41.7 KB | FIELDWISE open decisions |
| `plans/reports/FIELDWISE_open_decisions_round2_2026-08-31.docx` | T | 32.1 KB | FIELDWISE open decisions |
| `plans/reports/FIELDWISE_open_decisions_round2_2026-08-31.md` | T | 9.9 KB | FIELDWISE open decisions |
| `plans/reports/FIELDWISE_open_decisions_round3_2026-09-04.docx` | T | 43.6 KB | FIELDWISE open decisions |
| `plans/reports/FIELDWISE_open_decisions_round3_2026-09-04.md` | T | 19.4 KB | FIELDWISE open decisions |
| `plans/reports/FIELDWISE_open_decisions_round3_2026-09-04_reply.md` | T | 5.7 KB | FIELDWISE open decisions |
| `plans/reports/FIELDWISE_open_decisions_updated_2026-08-26.docx` | T | 44.0 KB | FIELDWISE open decisions |
| `plans/reports/FIELDWISE_Part_B1_refactoring_report_2026-09-08.md` | T | 40.2 KB | FIELDWISE refactor report |
| `plans/reports/FIELDWISE_Part_B1_Scoring_Improvement_Brief_2026-09-08.md` | T | 77.6 KB | FIELDWISE scoring brief |
| `plans/reports/FIELDWISE_PartB_draft_review_copy.docx` | T | 74.1 KB | FIELDWISE draft review copy |
| `plans/reports/fieldwise-run-03_flags.md` | T | 4.3 KB | FIELDWISE run-03 flag list |
| `plans/reports/fieldwise-run-03_inputs.md` | T | 1.9 KB | FIELDWISE run-03 inputs |
| `plans/reports/HANDOFF_n08a_readiness_2026-08-14.md` | T | 16.9 KB | FIELDWISE Phase 8 run handoff (11 project hits) |
| `plans/reports/HANDOFF_n08a_results_and_n08b_readiness_2026-08-15.md` | T | 11.4 KB | FIELDWISE Phase 8 run handoff |
| `plans/reports/HANDOFF_n08b_results_and_n08c_readiness_2026-08-16.md` | T | 9.3 KB | FIELDWISE Phase 8 run handoff |
| `plans/reports/HANDOFF_n08d_results_and_n08e_n08f_readiness_2026-08-16.md` | T | 10.2 KB | FIELDWISE Phase 8 run handoff |
| `plans/reports/HANDOFF_n08e_results_n08f_readiness_2026-08-16.md` | T | 5.5 KB | FIELDWISE Phase 8 run handoff |
| `plans/reports/HANDOFF_n08f_gate12_fixes_and_manual_partb1_2026-08-30.md` | T | 8.2 KB | FIELDWISE gate_12 fixes + manual Part B-1 handoff |
| `plans/reports/HOST_SWITCH_ASSESSMENT_2026-08-24.md` | T | 16.3 KB | FIELDWISE host switch assessment |
| `plans/reports/NCP_eligibility_query_2026-08-24.md` | T | 10.3 KB | FIELDWISE resubmission eligibility query |
| `plans/reports/OBSIDIAN_GRAPH_ROLE_FIELDWISE.md` | T | 2.1 KB | Vault role note for FIELDWISE |
| `plans/reports/p07_placement_ip_declaration_options.md` | T | 7.2 KB | FIELDWISE placement IP options |
| `plans/reports/partb1_prose_detect_2026-09-04.md` | T | 6.5 KB | FIELDWISE Part B-1 prose pass |
| `plans/reports/partb_draft_anchor_map_2026-09.json` | T | 17.0 KB | FIELDWISE draft anchor map |
| `plans/reports/partb_stage1_verification_2026-09.json` | T | 636 B | FIELDWISE stage verification |
| `plans/reports/partb_stage3_verification_2026-09.json` | T | 635 B | FIELDWISE stage verification |
| `plans/FIELDWISE_Part_B1_Scoring_Improvement_Plan_2026-09-08` | T | 30.2 KB | FIELDWISE scoring improvement plan (extension-less markdown file) |

## E. Root-level strays

10 files, 7 tracked, 1.4 MB.

| Path | T/U | Size | Reason |
|---|:-:|---:|---|
| `Claude outputs/FIELDWISE_Part_B2.docx` | T | 22.5 KB | FIELDWISE Part B-2 draft |
| `Claude outputs/FIELDWISE_Section_3.1_tabular.docx` | T | 100.1 KB | FIELDWISE section export |
| `Claude outputs/FIELDWISE_Section_3.1_tabular-1.docx` | T | 99.7 KB | FIELDWISE section export |
| `n08f_chat.md` | T | 14.5 KB | Chat about a FIELDWISE export |
| `image.png` | T | 1.0 MB | Loose 1 MB image dated 2026-08-31 (proposal-era) |
| `1786192761074 (1).jpeg` | T | 208.1 KB | Loose photo dated 2026-08-31 (proposal-era) |
| `runner_fieldwise-run-02.log` | U | 2.5 KB | FIELDWISE run-02 runner log (untracked, *.log ignored) |
| `runner_run02_detached.err.log` | U | 521 B | FIELDWISE run-02 runner log (untracked, *.log ignored) |
| `runner_run02_detached.out.log` | U | 289 B | FIELDWISE run-02 runner log (untracked, *.log ignored) |
| `docs/tier5_deliverables/final_exports/~$ELDWISE_Part_B1_refactored_2026-09-08.docx` | T | 0 B | Word lock file, already deleted in the working tree; `git rm` finalises it |

## G. Instance-#1 vault (MSCA/)

421 files, 218 tracked, 19.6 MB.

**G-note (migration check).** `templates/obsidian_graph_vault/` has all 21 folders (00–18, 90, 99), a noun-free `graph.config.yaml`, a meta node and two dashboards. Three things exist only in `MSCA/`, and none is a migration. First, the `smart-connections` Obsidian plugin (tracked, 3 files) is an editor convenience, not an engine dependency. Second, the `19_proposal_sections/` folder holds 12 FIELDWISE section nodes. The template binds `proposal_section` by node type, not by folder, so no folder is required; an empty `19_proposal_sections/.gitkeep` in the template is an optional nicety. Third, the three `99_governance/` nodes carry `domain: crop_water_stress / irrigation_decision_support` front matter and 4–6 project-noun hits each, so they are instance content, not generic prose. The generic template is complete as it stands.

| Path | T/U | Size | Reason |
|---|:-:|---:|---|
| `MSCA/.claude/settings.local.json` | U | 1.5 KB | Vault root file (instance #1) |
| `MSCA/.claude/skills/ask-matt/SKILL.md` | T | 4.3 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/codebase-design/DEEPENING.md` | T | 2.5 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/codebase-design/DESIGN-IT-TWICE.md` | T | 2.7 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/codebase-design/SKILL.md` | T | 6.4 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/diagnosing-bugs/scripts/hitl-loop.template.sh` | T | 1.2 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/diagnosing-bugs/SKILL.md` | T | 8.5 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/domain-modeling/ADR-FORMAT.md` | T | 2.7 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/domain-modeling/CONTEXT-FORMAT.md` | T | 2.3 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/domain-modeling/SKILL.md` | T | 3.4 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/grill-me/SKILL.md` | T | 154 B | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/grill-with-docs/SKILL.md` | T | 252 B | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/grilling/SKILL.md` | T | 676 B | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/handoff/SKILL.md` | T | 894 B | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/improve-codebase-architecture/HTML-REPORT.md` | T | 6.6 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/improve-codebase-architecture/SKILL.md` | T | 5.4 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/prototype/LOGIC.md` | T | 5.5 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/prototype/SKILL.md` | T | 3.0 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/prototype/UI.md` | T | 6.7 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/setup-matt-pocock-skills/domain.md` | T | 2.0 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/setup-matt-pocock-skills/issue-tracker-github.md` | T | 1.9 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/setup-matt-pocock-skills/issue-tracker-gitlab.md` | T | 2.2 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/setup-matt-pocock-skills/issue-tracker-local.md` | T | 857 B | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/setup-matt-pocock-skills/SKILL.md` | T | 7.3 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/setup-matt-pocock-skills/triage-labels.md` | T | 1.0 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/tdd/mocking.md` | T | 1.5 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/tdd/refactoring.md` | T | 397 B | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/tdd/SKILL.md` | T | 4.3 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/tdd/tests.md` | T | 1.7 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/teach/GLOSSARY-FORMAT.md` | T | 2.1 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/teach/LEARNING-RECORD-FORMAT.md` | T | 2.8 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/teach/MISSION-FORMAT.md` | T | 1.5 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/teach/RESOURCES-FORMAT.md` | T | 1.9 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/teach/SKILL.md` | T | 9.4 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/to-issues/SKILL.md` | T | 3.3 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/to-prd/SKILL.md` | T | 3.0 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/triage/AGENT-BRIEF.md` | T | 8.0 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/triage/OUT-OF-SCOPE.md` | T | 4.7 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/triage/SKILL.md` | T | 6.5 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/writing-great-skills/GLOSSARY.md` | T | 16.6 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.claude/skills/writing-great-skills/SKILL.md` | T | 8.9 KB | Dev skills duplicated at repo-root .claude/skills; no migration needed |
| `MSCA/.gitignore` | T | 1.0 KB | Vault root file (instance #1) |
| `MSCA/.mcp.json` | T | 476 B | Vault root file (instance #1) |
| `MSCA/.obsidian/app.json` | T | 2 B | Obsidian config/plugins (see G-note on smart-connections) |
| `MSCA/.obsidian/appearance.json` | T | 2 B | Obsidian config/plugins (see G-note on smart-connections) |
| `MSCA/.obsidian/community-plugins.json` | T | 39 B | Obsidian config/plugins (see G-note on smart-connections) |
| `MSCA/.obsidian/core-plugins.json` | T | 696 B | Obsidian config/plugins (see G-note on smart-connections) |
| `MSCA/.obsidian/graph.json` | U | 511 B | Obsidian config/plugins (see G-note on smart-connections) |
| `MSCA/.obsidian/plugins/dataview/main.js` | T | 1.3 MB | Obsidian config/plugins (see G-note on smart-connections) |
| `MSCA/.obsidian/plugins/dataview/manifest.json` | T | 368 B | Obsidian config/plugins (see G-note on smart-connections) |
| `MSCA/.obsidian/plugins/dataview/styles.css` | T | 3.0 KB | Obsidian config/plugins (see G-note on smart-connections) |
| `MSCA/.obsidian/plugins/smart-connections/data.json` | T | 65 B | Obsidian config/plugins (see G-note on smart-connections) |
| `MSCA/.obsidian/plugins/smart-connections/main.js` | T | 1.1 MB | Obsidian config/plugins (see G-note on smart-connections) |
| `MSCA/.obsidian/plugins/smart-connections/manifest.json` | T | 418 B | Obsidian config/plugins (see G-note on smart-connections) |
| `MSCA/.obsidian/plugins/smart-connections/styles.css` | T | 12.1 KB | Obsidian config/plugins (see G-note on smart-connections) |
| `MSCA/.obsidian/workspace.json` | U | 8.5 KB | Obsidian config/plugins (see G-note on smart-connections) |
| `MSCA/.scratch/research-demonstrator/adr-rq-dependencies.md` | U | 6.0 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/adr-rq-dependencies.mmd` | U | 3.2 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/adr-rq-dependencies.png` | U | 406.6 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/adr-rq-dependencies.svg` | U | 54.7 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/methodology-diagram.md` | U | 8.0 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/methodology-diagram.mmd` | U | 5.9 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/methodology-diagram.png` | U | 285.6 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/methodology-diagram.svg` | U | 79.8 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/methodology-presentation.pptx` | U | 2.0 MB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/msca-methodology-presentation.pptx` | U | 2.2 MB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/PRD.md` | U | 33.6 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/build_pptx.py` | U | 18.0 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/mmdc-config.json` | U | 117 B | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/s1-red-thread.mmd` | U | 903 B | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/s1-red-thread.png` | U | 49.9 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/s2-infrastructure.mmd` | U | 847 B | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/s2-infrastructure.png` | U | 132.1 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/s3-diagnostic-routes.mmd` | U | 1.2 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/s3-diagnostic-routes.png` | U | 221.1 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/s4-interface.mmd` | U | 960 B | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/s4-interface.png` | U | 238.3 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/s5-prognostic.mmd` | U | 1.1 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/s5-prognostic.png` | U | 338.2 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/s6-ground-truth.mmd` | U | 1.0 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/s6-ground-truth.png` | U | 158.3 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/s7-evaluation.mmd` | U | 1.1 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/s7-evaluation.png` | U | 211.8 KB | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/s8-deliverable.mmd` | U | 783 B | Untracked vault runtime state |
| `MSCA/.scratch/research-demonstrator/slides/s8-deliverable.png` | U | 126.6 KB | Untracked vault runtime state |
| `MSCA/.serena/.gitignore` | U | 28 B | Untracked vault runtime state |
| `MSCA/.serena/project.local.yml` | U | 402 B | Untracked vault runtime state |
| `MSCA/.serena/project.yml` | U | 7.5 KB | Untracked vault runtime state |
| `MSCA/.smart-env/embedding_models/embedding_models.ajson` | U | 249 B | Untracked vault runtime state |
| `MSCA/.smart-env/event_logs/event_logs.ajson` | U | 6.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/CLAUDE_md.ajson` | U | 11.4 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/CONTEXT_md.ajson` | U | 90.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_adr_0001-processing-tomato-as-lead-crop_md.ajson` | U | 26.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_adr_0001-two-routes-one-shared-decision-engine_md.ajson` | U | 59.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_adr_0002-diagnostic-target-is-minimal-aquacrop-ingestible-state_md.ajson` | U | 53.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_adr_0002-end-to-end-uncertainty-propagation_md.ajson` | U | 51.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_adr_0003-processing-tomato-as-lead-crop_md.ajson` | U | 48.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_adr_0003-risk-adjusted-expected-profit-objective_md.ajson` | U | 31.7 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_adr_0004-diagnostic-target-is-minimal-aquacrop-ingestible-state_md.ajson` | U | 60.5 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_adr_0004-sentinel-backbone-planetscope-optional_md.ajson` | U | 24.7 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_adr_0005-asymmetric-two-route-commitment_md.ajson` | U | 34.5 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_adr_0006-operator-aligned-depth-over-breadth-ground-truth_md.ajson` | U | 34.4 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_adr_0007-uncertainty-evaluation-decision-primary_md.ajson` | U | 34.4 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_adr_0008-covariation-validation-incremental-information_md.ajson` | U | 57.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_adr_0009-pilot-success-validated-hindcast_md.ajson` | U | 46.5 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_adr_0010-trl-target-validated-research-demonstrator_md.ajson` | U | 34.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_agents_domain_md.ajson` | U | 43.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_agents_issue-tracker_md.ajson` | U | 21.5 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/docs_agents_triage-labels_md.ajson` | U | 14.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/llm_wiki_md.ajson` | U | 90.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_00_meta__writetest_md.ajson` | U | 10.8 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_00_meta_index_md.ajson` | U | 104.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_00_meta_log_md.ajson` | U | 61.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_00_meta_Methodology_Graph_-_Meta_Node_md.ajson` | U | 108.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_01_sources_Source_-_Literature_Review_md.ajson` | U | 97.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_01_sources_Source_-_LLM_Wiki_Method_md.ajson` | U | 51.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_01_sources_Source_-_Methodology_Idea_md.ajson` | U | 93.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_01_sources_Source_-_Methodology_Synthesis_Prompt_md.ajson` | U | 131.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_02_core_architecture_Core_Architecture_md.ajson` | U | 92.5 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_02_core_architecture_Diagnostic_Branch_md.ajson` | U | 89.7 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_02_core_architecture_Observation_to_Decision_Pipeline_md.ajson` | U | 79.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_02_core_architecture_Prognostic_Branch_md.ajson` | U | 97.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_02_core_architecture_Uncertainty_Chain_md.ajson` | U | 97.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_03_state_of_the_art_Meteorological_and_Soil_Sensor_Integration_md.ajson` | U | 55.4 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_03_state_of_the_art_Operational_Decision_Support_Gap_md.ajson` | U | 55.7 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_03_state_of_the_art_PlanetScope_Usage_Gap_md.ajson` | U | 64.5 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_03_state_of_the_art_Probabilistic_Fusion_Novelty_Claim_md.ajson` | U | 66.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_03_state_of_the_art_Research_Gap_Matrix_md.ajson` | U | 63.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_03_state_of_the_art_Sentinel_1_and_Sentinel_2_Integration_md.ajson` | U | 64.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_03_state_of_the_art_State_of_the_Art_-_Multi_Sensor_Crop_Water_Stress_Monitoring_md.ajson` | U | 71.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_04_methodological_routes_Control_Stand_Variant_md.ajson` | U | 74.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_04_methodological_routes_Downscaling_Critique_md.ajson` | U | 74.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_04_methodological_routes_Route_A_-_Direct_Probabilistic_Fusion_md.ajson` | U | 102.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_04_methodological_routes_Route_B_-_Homogeneous_Patch_Proxy_md.ajson` | U | 85.5 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_04_methodological_routes_Route_Comparison_md.ajson` | U | 64.4 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_04_methodological_routes_Sub_Pixel_Problem_md.ajson` | U | 64.7 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_05_decision_framework_AquaCrop_Decision_Interface_md.ajson` | U | 80.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_05_decision_framework_Counterfactual_Irrigation_Simulation_md.ajson` | U | 77.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_05_decision_framework_Decision_Recommendation_Logic_md.ajson` | U | 72.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_05_decision_framework_Profit_Based_Objective_Function_md.ajson` | U | 73.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_05_decision_framework_Uncertainty_Aware_AquaCrop_Calibration_md.ajson` | U | 88.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_05_decision_framework_Weather_Ensemble_Scenario_Evaluation_md.ajson` | U | 61.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_06_infrastructure_AquaCrop_Simulation_Runtime_md.ajson` | U | 61.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_06_infrastructure_Decision_Engine_Layer_md.ajson` | U | 66.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_06_infrastructure_Earth_Observation_Layer_md.ajson` | U | 86.8 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_06_infrastructure_Geospatial_and_Time_Series_Data_Platform_md.ajson` | U | 76.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_06_infrastructure_Ground_Sensing_Layer_md.ajson` | U | 81.7 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_06_infrastructure_Infrastructure_Architecture_md.ajson` | U | 75.4 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_06_infrastructure_Probabilistic_Modelling_Runtime_md.ajson` | U | 67.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_06_infrastructure_Validation_and_Field_Trial_Layer_md.ajson` | U | 65.8 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_06_infrastructure_Weather_and_Climate_Data_Layer_md.ajson` | U | 80.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_06_infrastructure_Web_MVP_and_User_Interface_Layer_md.ajson` | U | 61.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_07_risks_and_swot_Data_Access_Risks_md.ajson` | U | 58.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_07_risks_and_swot_Methodology_SWOT_Matrix_md.ajson` | U | 66.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_07_risks_and_swot_Model_Complexity_Risks_md.ajson` | U | 61.5 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_07_risks_and_swot_Operationalisation_Risks_md.ajson` | U | 59.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_07_risks_and_swot_Risk_Register_md.ajson` | U | 48.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_07_risks_and_swot_Validation_Risks_md.ajson` | U | 59.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_08_partners_AgroVIR_Validation_Partner_Role_md.ajson` | U | 57.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_08_partners_ELTE_Role_md.ajson` | U | 52.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_08_partners_Methodology_Contributor_Role_md.ajson` | U | 67.7 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_08_partners_Partner_Roles_Overview_md.ajson` | U | 79.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_08_partners_PI_Role_md.ajson` | U | 64.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_08_partners_Unconfirmed_Partner_Placeholders_md.ajson` | U | 57.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_AquaCrop_md.ajson` | U | 45.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Bayesian_Hierarchical_Model_md.ajson` | U | 42.8 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Cokriging_md.ajson` | U | 34.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Counterfactual_Simulation_md.ajson` | U | 39.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Covariate_md.ajson` | U | 31.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Crop_Water_Stress_md.ajson` | U | 39.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Data_Fusion_md.ajson` | U | 30.7 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Decision_Regret_md.ajson` | U | 38.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Downscaling_md.ajson` | U | 31.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Evapotranspiration_md.ajson` | U | 39.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Expected_Profit_md.ajson` | U | 39.4 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Expected_Utility_md.ajson` | U | 38.7 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Gaussian_Process_md.ajson` | U | 36.5 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Ground_Truth_md.ajson` | U | 31.4 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Irrigation_Water_Requirement_md.ajson` | U | 39.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Latent_Field_State_md.ajson` | U | 32.8 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Multimodal_Fusion_md.ajson` | U | 37.4 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_NDMI_md.ajson` | U | 38.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_NDVI_md.ajson` | U | 38.8 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_NDWI_md.ajson` | U | 38.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_PlanetScope_md.ajson` | U | 38.8 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Posterior_Distribution_md.ajson` | U | 40.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Probabilistic_Machine_Learning_md.ajson` | U | 34.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Root_Zone_Soil_Moisture_md.ajson` | U | 40.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_SAR_md.ajson` | U | 38.4 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Sentinel_1_md.ajson` | U | 38.7 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Sentinel_2_md.ajson` | U | 39.5 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Uncertainty_Propagation_md.ajson` | U | 40.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_09_terminology_Weather_Ensemble_md.ajson` | U | 39.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_10_research_questions_Ten_Research_Questions_md.ajson` | U | 85.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_11_objectives_OBJ-1_Probabilistic_multi-sensor_diagnosis_of_the_latent_field_state_md.ajson` | U | 22.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_11_objectives_OBJ-2_Uncertainty-aware_decision_engine_for_water-use-efficient_irrigation_choice_md.ajson` | U | 28.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_11_objectives_OBJ-3_Field_validation_and_honest_uncertainty_calibration_md.ajson` | U | 18.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_11_objectives_OBJ-4_Standalone_research_demonstrator_(web_MVP)_md.ajson` | U | 17.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_11_objectives_OBJ-5_Advancement_of_the_fellow's_competences_and_career_md.ajson` | U | 16.8 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_12_outcomes_OUT-1_Probabilistic_multi-sensor_field-state_diagnosis_method_md.ajson` | U | 26.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_12_outcomes_OUT-2_Uncertainty-aware_AquaCrop_decision_engine_md.ajson` | U | 27.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_12_outcomes_OUT-3_Field-validation_dataset_and_uncertainty-calibration_evidence_md.ajson` | U | 22.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_12_outcomes_OUT-4_Standalone_research_demonstrator_(web_MVP)_md.ajson` | U | 13.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_12_outcomes_OUT-5_Peer-reviewed_publications_and_open_science_outputs_md.ajson` | U | 26.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_12_outcomes_OUT-6_Enhanced_researcher_competences_and_career_readiness_md.ajson` | U | 17.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_13_impacts_IMP-1_Scientific_advance_in_probabilistic_multi-sensor_crop-water-state_estimation_md.ajson` | U | 28.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_13_impacts_IMP-2_Economic_and_societal_impact_water-use_efficiency_and_farm_resilience_md.ajson` | U | 27.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_13_impacts_IMP-3_Environmental_co-benefit_through_landscape-compatible_sensing_md.ajson` | U | 17.7 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_13_impacts_IMP-4_Advancement_of_the_researcher's_career_and_the_European_Research_Area_md.ajson` | U | 18.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_14_work_packages_WP1_Probabilistic_multi-sensor_diagnosis_of_the_field_state_md.ajson` | U | 27.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_14_work_packages_WP2_Uncertainty-aware_decision_engine_and_demonstrator_integration_md.ajson` | U | 28.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_14_work_packages_WP3_Field_validation,_ground_truth_and_uncertainty_calibration_md.ajson` | U | 27.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_14_work_packages_WP4_Training,_supervision_and_two-way_transfer_of_knowledge_md.ajson` | U | 17.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_14_work_packages_WP5_Dissemination,_exploitation,_communication_and_management_md.ajson` | U | 17.7 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_15_timeline_MS1_Multi-sensor_data_pipeline_operational;_Data_Management_Plan_delivered_md.ajson` | U | 21.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_15_timeline_MS2_Diagnostic_method_v1_producing_calibrated_field-state_posteriors_md.ajson` | U | 26.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_15_timeline_MS3_Uncertainty-aware_decision_engine_integrated_md.ajson` | U | 26.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_15_timeline_MS4_Standalone_research_demonstrator_exercises_the_end-to-end_pipeline_md.ajson` | U | 12.8 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_15_timeline_MS5_Field_validation_and_uncertainty_calibration_complete_md.ajson` | U | 17.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_15_timeline_MS6_Results_disseminated_and_fellowship_outcomes_consolidated_md.ajson` | U | 17.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_16_risks_RISK-01_PlanetScope_costaccess_not_secured,_weakening_high-resolution_coverage_of_small_plots_md.ajson` | U | 13.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_16_risks_RISK-02_Spatialtemporal_resolution_harmonisation_across_heterogeneous_sources_fails_or_degrades_fu_md.ajson` | U | 17.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_16_risks_RISK-03_Cloud_limits_optical;_dense_vegetation_reduces_SAR_retrieval_accuracy_md.ajson` | U | 13.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_16_risks_RISK-04_Sparse_dense_ground-truth_leaves_validation_under-powered_md.ajson` | U | 12.8 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_16_risks_RISK-05_Route_B_patchcontrol-stand_covariation_not_actually_proven_md.ajson` | U | 21.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_16_risks_RISK-06_Reported_uncertainty_is_not_well_calibrated_md.ajson` | U | 22.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_16_risks_RISK-07_Route_A_too_demanding_(expertise_validation_data_compute)_md.ajson` | U | 21.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_16_risks_RISK-08_Overconfidence_-_collapsing_to_one_parameter_set_instead_of_an_honest_range_md.ajson` | U | 17.4 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_16_risks_RISK-09_Sensor_calibrationintegration_complexity_md.ajson` | U | 17.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_16_risks_RISK-10_Prototype_does_not_reach_a_usable_pilot_(operational-frameworks_gap)_md.ajson` | U | 22.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_17_budget_BUDGET-living_allowance_md.ajson` | U | 15.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_17_budget_BUDGET-management_and_indirect_md.ajson` | U | 15.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_17_budget_BUDGET-mobility_allowance_md.ajson` | U | 14.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_17_budget_BUDGET-research_training_networking_md.ajson` | U | 15.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_17_budget_BUDGET-total_md.ajson` | U | 15.7 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_19_proposal_sections_PS-excellence-1_1_Quality_and_pertinence_of_the_project's_research_and_innovat_md.ajson` | U | 59.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_19_proposal_sections_PS-excellence-1_2_Soundness_of_the_proposed_methodology_(including_interdiscip_md.ajson` | U | 69.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_19_proposal_sections_PS-excellence-1_3_Quality_of_the_supervision,_training_and_of_the_two-way_tran_md.ajson` | U | 81.4 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_19_proposal_sections_PS-excellence-1_4_Quality_and_appropriateness_of_the_researcher's_professional_md.ajson` | U | 112.7 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_19_proposal_sections_PS-excellence-1_Excellence_md.ajson` | U | 245.8 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_19_proposal_sections_PS-impact-2_1_Credibility_of_the_measures_to_enhance_the_career_perspectiv_md.ajson` | U | 83.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_19_proposal_sections_PS-impact-2_2_Suitability_and_quality_of_the_measures_to_maximise_expected_md.ajson` | U | 96.4 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_19_proposal_sections_PS-impact-2_3_The_magnitude_and_importance_of_the_project's_contribution_t_md.ajson` | U | 105.7 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_19_proposal_sections_PS-impact-2_Impact_md.ajson` | U | 198.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_19_proposal_sections_PS-implementation-3_1_Quality_and_effectiveness_of_the_work_plan,_assessment_of_ri_md.ajson` | U | 17.1 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_19_proposal_sections_PS-implementation-3_2_Quality_and_capacity_of_the_host_institutions_and_participat_md.ajson` | U | 17.0 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_19_proposal_sections_PS-implementation-3_Quality_and_Efficiency_of_the_Implementation_md.ajson` | U | 17.2 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_90_dashboards_Methodology_Graph_Dashboard_md.ajson` | U | 40.8 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_99_governance__BUILD_BRIEF_md.ajson` | U | 964.9 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_99_governance_Graph_Maintenance_Rules_md.ajson` | U | 95.3 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_99_governance_Methodology_Graph_Schema_md.ajson` | U | 93.8 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/methodology_graph_99_governance_Source_Traceability_Register_md.ajson` | U | 72.4 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/sources_methodology_idea_txt.ajson` | U | 9.4 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/sources_prompt_txt.ajson` | U | 9.4 KB | Untracked vault runtime state |
| `MSCA/.smart-env/multi/Welcome_md.ajson` | U | 9.6 KB | Untracked vault runtime state |
| `MSCA/.smart-env/smart_env.json` | U | 2.2 KB | Untracked vault runtime state |
| `MSCA/CLAUDE.md` | T | 521 B | Vault root file (instance #1) |
| `MSCA/CONTEXT.md` | T | 15.6 KB | Vault root file (instance #1) |
| `MSCA/docs/adr/0001-processing-tomato-as-lead-crop.md` | T | 2.2 KB | FIELDWISE architecture decision records |
| `MSCA/docs/adr/0002-diagnostic-target-is-minimal-aquacrop-ingestible-state.md` | T | 2.6 KB | FIELDWISE architecture decision records |
| `MSCA/docs/adr/0003-risk-adjusted-expected-profit-objective.md` | T | 2.5 KB | FIELDWISE architecture decision records |
| `MSCA/docs/adr/0004-sentinel-backbone-planetscope-optional.md` | T | 2.0 KB | FIELDWISE architecture decision records |
| `MSCA/docs/adr/0005-asymmetric-two-route-commitment.md` | T | 2.5 KB | FIELDWISE architecture decision records |
| `MSCA/docs/adr/0006-operator-aligned-depth-over-breadth-ground-truth.md` | T | 3.4 KB | FIELDWISE architecture decision records |
| `MSCA/docs/adr/0007-uncertainty-evaluation-decision-primary.md` | T | 2.6 KB | FIELDWISE architecture decision records |
| `MSCA/docs/adr/0008-covariation-validation-incremental-information.md` | T | 2.6 KB | FIELDWISE architecture decision records |
| `MSCA/docs/adr/0009-pilot-success-validated-hindcast.md` | T | 2.6 KB | FIELDWISE architecture decision records |
| `MSCA/docs/adr/0010-trl-target-validated-research-demonstrator.md` | T | 2.1 KB | FIELDWISE architecture decision records |
| `MSCA/docs/agents/domain.md` | T | 2.0 KB | Vault-local dev conventions (generic, but not used by the engine) |
| `MSCA/docs/agents/issue-tracker.md` | T | 857 B | Vault-local dev conventions (generic, but not used by the engine) |
| `MSCA/docs/agents/triage-labels.md` | T | 1.0 KB | Vault-local dev conventions (generic, but not used by the engine) |
| `MSCA/graph.config.yaml` | T | 4.3 KB | Vault root file (instance #1) |
| `MSCA/llm_wiki.md` | T | 11.8 KB | Vault root file (instance #1) |
| `MSCA/methodology_graph/00_meta/index.md` | T | 4.1 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/00_meta/log.md` | T | 4.9 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/00_meta/Methodology Graph - Meta Node.md` | T | 6.7 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/01_sources/Source - Literature Review.md` | T | 11.0 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/01_sources/Source - LLM Wiki Method.md` | T | 4.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/01_sources/Source - Methodology Idea.md` | T | 8.1 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/01_sources/Source - Methodology Synthesis Prompt.md` | T | 9.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/02_core_architecture/Core Architecture.md` | T | 6.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/02_core_architecture/Diagnostic Branch.md` | T | 5.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/02_core_architecture/Observation to Decision Pipeline.md` | T | 5.0 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/02_core_architecture/Prognostic Branch.md` | T | 5.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/02_core_architecture/Uncertainty Chain.md` | T | 5.6 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/03_state_of_the_art/Meteorological and Soil Sensor Integration.md` | T | 4.1 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/03_state_of_the_art/Operational Decision Support Gap.md` | T | 4.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/03_state_of_the_art/PlanetScope Usage Gap.md` | T | 4.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/03_state_of_the_art/Probabilistic Fusion Novelty Claim.md` | T | 5.7 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/03_state_of_the_art/Research Gap Matrix.md` | T | 3.8 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/03_state_of_the_art/Sentinel 1 and Sentinel 2 Integration.md` | T | 4.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/03_state_of_the_art/State of the Art - Multi Sensor Crop Water Stress Monitoring.md` | T | 5.5 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/04_methodological_routes/Control Stand Variant.md` | T | 4.1 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/04_methodological_routes/Downscaling Critique.md` | T | 4.7 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/04_methodological_routes/Route A - Direct Probabilistic Fusion.md` | T | 5.8 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/04_methodological_routes/Route B - Homogeneous Patch Proxy.md` | T | 5.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/04_methodological_routes/Route Comparison.md` | T | 4.6 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/04_methodological_routes/Sub Pixel Problem.md` | T | 4.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/05_decision_framework/AquaCrop Decision Interface.md` | T | 5.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/05_decision_framework/Counterfactual Irrigation Simulation.md` | T | 4.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/05_decision_framework/Decision Recommendation Logic.md` | T | 4.7 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/05_decision_framework/Profit Based Objective Function.md` | T | 4.6 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/05_decision_framework/Uncertainty Aware AquaCrop Calibration.md` | T | 5.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/05_decision_framework/Weather Ensemble Scenario Evaluation.md` | T | 3.5 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/06_infrastructure/AquaCrop Simulation Runtime.md` | T | 4.5 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/06_infrastructure/Decision Engine Layer.md` | T | 4.8 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/06_infrastructure/Earth Observation Layer.md` | T | 5.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/06_infrastructure/Geospatial and Time Series Data Platform.md` | T | 4.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/06_infrastructure/Ground Sensing Layer.md` | T | 5.0 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/06_infrastructure/Infrastructure Architecture.md` | T | 6.0 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/06_infrastructure/Probabilistic Modelling Runtime.md` | T | 5.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/06_infrastructure/Validation and Field Trial Layer.md` | T | 4.8 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/06_infrastructure/Weather and Climate Data Layer.md` | T | 4.6 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/06_infrastructure/Web MVP and User Interface Layer.md` | T | 4.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/07_risks_and_swot/Data Access Risks.md` | T | 4.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/07_risks_and_swot/Methodology SWOT Matrix.md` | T | 6.5 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/07_risks_and_swot/Model Complexity Risks.md` | T | 4.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/07_risks_and_swot/Operationalisation Risks.md` | T | 4.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/07_risks_and_swot/Risk Register.md` | T | 6.1 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/07_risks_and_swot/Validation Risks.md` | T | 4.8 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/08_partners/AgroVIR Validation Partner Role.md` | T | 3.9 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/08_partners/ELTE Role.md` | T | 3.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/08_partners/Methodology Contributor Role.md` | T | 4.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/08_partners/Partner Roles Overview.md` | T | 5.8 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/08_partners/PI Role.md` | T | 4.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/08_partners/Unconfirmed Partner Placeholders.md` | T | 4.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/AquaCrop.md` | T | 2.5 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Bayesian Hierarchical Model.md` | T | 2.6 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Cokriging.md` | T | 2.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Counterfactual Simulation.md` | T | 2.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Covariate.md` | T | 2.5 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Crop Water Stress.md` | T | 2.5 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Data Fusion.md` | T | 2.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Decision Regret.md` | T | 2.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Downscaling.md` | T | 2.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Evapotranspiration.md` | T | 2.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Expected Profit.md` | T | 2.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Expected Utility.md` | T | 2.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Gaussian Process.md` | T | 2.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Ground Truth.md` | T | 2.7 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Irrigation Water Requirement.md` | T | 2.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Latent Field State.md` | T | 2.7 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Multimodal Fusion.md` | T | 2.5 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/NDMI.md` | T | 2.0 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/NDVI.md` | T | 2.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/NDWI.md` | T | 2.1 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/PlanetScope.md` | T | 2.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Posterior Distribution.md` | T | 2.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Probabilistic Machine Learning.md` | T | 2.5 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Root Zone Soil Moisture.md` | T | 2.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/SAR.md` | T | 2.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Sentinel 1.md` | T | 2.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Sentinel 2.md` | T | 2.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Uncertainty Propagation.md` | T | 2.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/09_terminology/Weather Ensemble.md` | T | 2.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/10_research_questions/Ten Research Questions.md` | T | 9.0 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/11_objectives/OBJ-1 Probabilistic multi-sensor diagnosis of the latent field state.md` | T | 2.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/11_objectives/OBJ-2 Uncertainty-aware decision engine for water-use-efficient irrigation choice.md` | T | 2.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/11_objectives/OBJ-3 Field validation and honest uncertainty calibration.md` | T | 2.8 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/11_objectives/OBJ-4 Standalone research demonstrator (web MVP).md` | T | 1.5 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/11_objectives/OBJ-5 Advancement of the fellow's competences and career.md` | T | 2.9 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/12_outcomes/OUT-1 Probabilistic multi-sensor field-state diagnosis method.md` | T | 2.0 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/12_outcomes/OUT-2 Uncertainty-aware AquaCrop decision engine.md` | T | 1.8 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/12_outcomes/OUT-3 Field-validation dataset and uncertainty-calibration evidence.md` | T | 1.9 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/12_outcomes/OUT-4 Standalone research demonstrator (web MVP).md` | T | 1.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/12_outcomes/OUT-5 Peer-reviewed publications and open science outputs.md` | T | 1.7 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/12_outcomes/OUT-6 Enhanced researcher competences and career readiness.md` | T | 2.1 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/13_impacts/IMP-1 Scientific advance in probabilistic multi-sensor crop-water-state estimation.md` | T | 2.6 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/13_impacts/IMP-2 Economic and societal impact water-use efficiency and farm resilience.md` | T | 2.1 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/13_impacts/IMP-3 Environmental co-benefit through landscape-compatible sensing.md` | T | 1.8 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/13_impacts/IMP-4 Advancement of the researcher's career and the European Research Area.md` | T | 2.7 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/14_work_packages/WP1 Probabilistic multi-sensor diagnosis of the field state.md` | T | 2.1 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/14_work_packages/WP2 Uncertainty-aware decision engine and demonstrator integration.md` | T | 2.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/14_work_packages/WP3 Field validation, ground truth and uncertainty calibration.md` | T | 2.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/14_work_packages/WP4 Training, supervision and two-way transfer of knowledge.md` | T | 3.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/14_work_packages/WP5 Dissemination, exploitation, communication and management.md` | T | 1.8 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/15_timeline/MS1 Multi-sensor data pipeline operational; Data Management Plan delivered.md` | T | 1.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/15_timeline/MS2 Diagnostic method v1 producing calibrated field-state posteriors.md` | T | 1.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/15_timeline/MS3 Uncertainty-aware decision engine integrated.md` | T | 1.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/15_timeline/MS4 Standalone research demonstrator exercises the end-to-end pipeline.md` | T | 1.1 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/15_timeline/MS5 Field validation and uncertainty calibration complete.md` | T | 1.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/15_timeline/MS6 Results disseminated and fellowship outcomes consolidated.md` | T | 1.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/16_risks/RISK-01 PlanetScope costaccess not secured, weakening high-resolution coverage of small plots.md` | T | 1.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/16_risks/RISK-02 Spatialtemporal resolution harmonisation across heterogeneous sources fails or degrades fu.md` | T | 1.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/16_risks/RISK-03 Cloud limits optical; dense vegetation reduces SAR retrieval accuracy.md` | T | 1.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/16_risks/RISK-04 Sparse dense ground-truth leaves validation under-powered.md` | T | 1.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/16_risks/RISK-05 Route B patchcontrol-stand covariation not actually proven.md` | T | 1.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/16_risks/RISK-06 Reported uncertainty is not well calibrated.md` | T | 1.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/16_risks/RISK-07 Route A too demanding (expertise validation data compute).md` | T | 1.4 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/16_risks/RISK-08 Overconfidence - collapsing to one parameter set instead of an honest range.md` | T | 1.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/16_risks/RISK-09 Sensor calibrationintegration complexity.md` | T | 1.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/16_risks/RISK-10 Prototype does not reach a usable pilot (operational-frameworks gap).md` | T | 1.6 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/17_budget/BUDGET-living_allowance.md` | T | 956 B | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/17_budget/BUDGET-management_and_indirect.md` | T | 939 B | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/17_budget/BUDGET-mobility_allowance.md` | T | 909 B | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/17_budget/BUDGET-research_training_networking.md` | T | 970 B | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/17_budget/BUDGET-total.md` | T | 1.1 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/18_phase_gate_state/.gitkeep` | T | 227 B | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/19_proposal_sections/PS-excellence-1 Excellence.md` | T | 44.6 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/19_proposal_sections/PS-excellence-1.1 Quality and pertinence of the project's research and innovat.md` | T | 30.8 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/19_proposal_sections/PS-excellence-1.2 Soundness of the proposed methodology (including interdiscip.md` | T | 43.0 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/19_proposal_sections/PS-excellence-1.3 Quality of the supervision, training and of the two-way tran.md` | T | 40.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/19_proposal_sections/PS-excellence-1.4 Quality and appropriateness of the researcher's professional.md` | T | 33.7 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/19_proposal_sections/PS-impact-2 Impact.md` | T | 30.1 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/19_proposal_sections/PS-impact-2.1 Credibility of the measures to enhance the career perspectiv.md` | T | 29.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/19_proposal_sections/PS-impact-2.2 Suitability and quality of the measures to maximise expected.md` | T | 43.5 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/19_proposal_sections/PS-impact-2.3 The magnitude and importance of the project's contribution t.md` | T | 50.6 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/19_proposal_sections/PS-implementation-3 Quality and Efficiency of the Implementation.md` | T | 39.0 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/19_proposal_sections/PS-implementation-3.1 Quality and effectiveness of the work plan, assessment of ri.md` | T | 37.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/19_proposal_sections/PS-implementation-3.2 Quality and capacity of the host institutions and participat.md` | T | 23.2 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/90_dashboards/Methodology Graph Dashboard.md` | T | 3.3 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/99_governance/Graph Maintenance Rules.md` | T | 4.6 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/99_governance/Methodology Graph Schema.md` | T | 5.6 KB | Authored FIELDWISE graph node |
| `MSCA/methodology_graph/99_governance/Source Traceability Register.md` | T | 5.5 KB | Authored FIELDWISE graph node |
| `MSCA/OBJ-1.md` | T | 0 B | Vault root file (instance #1) |
| `MSCA/skills-lock.json` | T | 4.3 KB | Vault root file (instance #1) |
| `MSCA/sources/literature_review.pdf` | T | 526.1 KB | FIELDWISE source texts |
| `MSCA/sources/methodology_idea.txt` | T | 4.3 KB | FIELDWISE source texts |
| `MSCA/sources/prompt.txt` | T | 11.3 KB | FIELDWISE source texts |
| `MSCA/Untitled.canvas` | T | 2 B | Vault root file (instance #1) |
| `MSCA/Welcome.md` | T | 207 B | Vault root file (instance #1) |

## F. Ignored runtime state

Directory totals; every file inside is untracked or ignored. Plain delete.

| Path | Files | Size | Reason |
|---|---:|---:|---|
| `.claude/runs` | 41 | 49.4 KB | 14 run contexts incl. fieldwise-run-02; §9.2 runtime memory |
| `.claude/logs` | 53 | 1.2 MB | Runner logs |
| `.claude/benchmark` | 280 | 522.8 KB | Benchmark runtime output |
| `.claude/skill_diag` | 501 | 3.0 MB | Skill diagnostics from FIELDWISE runs |
| `.pytest_cache` | 5 | 641.6 KB | Test cache |
| `.mypy_cache` | 18 | 13.4 MB | Type-check cache |
| `harness/rubric_reports/rubric_run_checkpoint.pkl` | 0 | 0 B | E5f run-local pickle checkpoint (ignored) |
| `**/__pycache__ (23 dirs)` | 513 | 14.2 MB | Bytecode caches |

## Ambiguous — listed, not proposed for deletion

| Path | Assessment |
|---|---|
| `plans/DEBUG_KICKOFF_phase8_calibration.md` | Engine Phase 8 calibration brief (0 project hits) — keep |
| `plans/tickets_phase8_review.md` | Engine Phase 8 review tickets (0 hits) — keep |
| `plans/tickets_phase8_stepwise_execution.md` | Engine stepwise-execution tickets (1 incidental hit) — keep, scrub the one line |
| `plans/reports/HANDOFF_tapm_hang_2026-08-12.md` | Engine transport bug handoff (1 incidental hit) — keep, scrub the one line |
| `plans/reports/n08b_fail_diag.md` | Engine failure diagnosis (1 hit) — keep, scrub the one line |
| `plans/reports/PHASE8_FULLSCALE_AND_OBSIDIAN_GRILL_BRIEF.md` | Engine plan of record (1 hit) — keep, scrub the one line |
| `plans/milestones/WAVE6_STATE_HANDOFF.md` | Engine milestone handoff (1 hit) — keep, scrub the one line |
| `plans/reports/chat.md` | Engine chat transcript, 147 KB, 0 hits — keep or delete as clutter; your call |
| `plans/reports/prompt.md` | Engine fix summary transcript, 0 hits — keep or delete as clutter; your call |
| `plans/reports/project_structure.md` | Stale directory dump, 96 KB, 0 hits — will be wrong after the purge; recommend delete |
| `MSCA-preabsorb-b4d9e57.bundle` | 3.5 MB git bundle of the pre-absorb MSCA vault (instance #1 history). Project-scoped; recommend delete — the new archive bundle supersedes it |
| `screenshots/` | 5 Hungarian-named screenshots dated 2026-07-28 (AWS deployment era, not FIELDWISE). Recommend delete as clutter, not as purge |
| `costs/` | AWS Bedrock cost CSVs (deployment telemetry, not FIELDWISE). Keep |
| `bedrock-all-events.json, bedrock-all-events-full.json, bedrock-converse-events.json` | AWS CloudTrail exports (UTF-16, 2.9 MB). Deployment telemetry, not FIELDWISE. Keep, or delete as clutter |
| `docs/benchmark_json/` | 8 benchmark-engine run JSONs, 0 project hits. Keep |
| `.claude/worktrees/e5f-implementation-status-f7651c` | A LIVE git worktree (63 MB, branch claude/e5f-implementation-status-f7651c, at main). Not FIELDWISE. Removing it means `git worktree remove`, not `rm`. Recommend leave |
| `harness/regression_baselines/*.golden.json + provenance_grounding_freeze.jsonl` | E4 golden baselines frozen from drafter-era Tier 5 (16+22+11 AgroVIR/Cholakova hits). Project-derived, tracked. Recommend delete + re-freeze on the next project; tests/harness/test_regression_golden.py will need a fixture decision |
| `harness/materiality_sets/materiality_positives_ledger.jsonl + materiality_negatives_TEMPLATE.jsonl` | E3 ledgers from drafter-era sections (47 + 4 project hits). Project-derived. Same recommendation as the goldens |
| `harness/gold_sets/*, harness/labeling/*, harness/provenance/expectation_rubric.jsonl` | Human-labelled calibration sets over drafter-era text (1 Cholakova hit in gold_excellence). Expensive labels; keep only if you accept the residual nouns, else delete |
| `harness/rubric_reports/rubric_run_budget.json` | E5f budget ledger of the FIELDWISE-era grading run; tracked. Recommend delete |
| `scripts/vote_results/` | Engine review-vote records (skip-id / preseed lanes), 0 project hits. Keep |

## H. References from surviving files — not deleted

| Path | Finding |
|---|---|
| `CONTEXT.md` | Entire file is the FIELDWISE glossary (supervision spine, Farmer 2, MVCRI…). Reset to a generic template |
| `runner/agnosticism_lint.py` | Denylist of instance-#1 nouns (Cholakova, AgroVIR, ELTE, crop, irrigation…). Decision 2 |
| `runner/phase8_canonical_pack.py` | 4 docstring mentions: 'FIELDWISE Tier-3 spelling' of objective/outcome keys. Behaviour is generic; rename the comments |
| `runner/decomposed_drafting.py` | 1 error-message example 'placement_supervisor_title_AgroVIR'. Replace with a placeholder token |
| `tools/build_partb1_refactored.py` | 83 hits. FIELDWISE-only build tool (hard-codes the submitted docx path) |
| `tools/build_partb1_condensed.py` | 42 hits. FIELDWISE-only build tool |
| `tools/partb1_refactor_lib.py` | FIELDWISE Part B-1 editing primitives |
| `tools/partb1_refactor_report.py` | 17 hits. FIELDWISE report generator |
| `tools/annotate_part_b_draft.py` | Hard-codes the run-03 annotated docx filename |
| `tools/export_open_decisions_docx.py` | Hard-codes plans/reports/FIELDWISE_open_decisions_round3 path |
| `tools/author_msca_proposal_graph.py` | Docstring names the FIELDWISE spine; writes into MSCA/methodology_graph (deleted in G) |
| `tests/runner/test_fieldwise_purge.py` | Pins the 2026-08-11 partial purge (decision log split). Decision 1 |
| `tests/runner/test_fieldwise_ticket4_seed.py` | Asserts on FIELDWISE architecture_inputs. Decision 1 |
| `tests/runner/test_fieldwise_ticket5_seed.py` | Asserts on FIELDWISE consortium files. Decision 1 |
| `tests/runner/test_fieldwise_ticket6_fold.py` | Asserts on FIELDWISE fold state. Decision 1 |
| `tests/runner/test_fieldwise_ticket7_authorisation.py` | Asserts on the FIELDWISE authorisation record. Decision 1 |
| `tests/tools/test_build_partb1_refactored.py, tests/tools/test_partb1_refactor_lib.py` | Tests for the FIELDWISE-only tools above (AgroVIR in fixture strings) |
| `tests/runner/test_annotate_part_b_draft.py, tests/runner/test_export_open_decisions_docx.py` | Tests for the FIELDWISE-only tools above |
| `tests/harness/test_status_faithfulness.py` | Uses 'Dr. Cholakova' as a fixture literal. Replace with a placeholder name |
| `tests/runner/test_phase8_consistency_layer.py` | Test names/docstrings say 'FIELDWISE source field names'. Rename to 'hand-lift spelling' |
| `tests/runner/test_agnosticism_lint.py, tests/runner/test_vault_scaffold.py, tests/runner/test_excellence_decomposed_drafting.py` | Use denylist nouns as test inputs. Follow decision 2 |
| `.claude/skills/work-package-normalization.md:131` | Example lead strings `"MATE + ELTE"`, `"MATE -> MVCRI"` are instance-#1 organisation names. Replace with placeholder organisations (prose diff) |
| `docs/infrastructure_security/** (3 lines)` | 'ELTE DPO' review note in AWS hardening evidence. Institutional, not project; keep |
| `docs/index/*.json` | 0 FIELDWISE entries; document/instrument/rule registries are already empty ('[]'). Nothing to reset |
| `.claude/settings.json, .mcp.json, manifest.compile.yaml, README.md, CLAUDE.md, AGENTS.md, Proposal_Engine_Operator_Manual.md, .claude/agents/*.md, .agents/skills/**` | 0 hits. No prose scrub needed beyond CONTEXT.md |
## Simulated purge — test impact (evidence for decision 1)

The 524 tracked paths in groups A–E and G, plus the tracked harness data listed under Ambiguous, were `git rm`'d in a throwaway worktree (`../purge_sim`, detached from `ESR`). The full suite was then run there and on unmodified `ESR`.

| Run | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| Baseline `ESR` | 4874 | 147 | 22 | 42 |
| Simulated purge | 4561 | 212 | 179 | 133 |

Newly failing after the purge, by cause:

| Test file | New red | Cause | Disposition |
|---|---:|---|---|
| `tests/runner/test_fieldwise_ticket4_seed.py` … `ticket7_authorisation.py`, `test_fieldwise_purge.py` | 242 | Assert on FIELDWISE Tier 3/4 files. 73 of them were already red on `ESR` | Decision 1 |
| `tests/harness/test_expectations.py`, `test_regression_golden.py`, `test_measure_ledger_granularity.py` | 21 | Read live Tier 5 sections and the E4 goldens (`TestRealSubstrate`, `TestGoldenSetStanding`) | Harness "real substrate" lanes; mark skip-when-empty or delete with the goldens (Ambiguous F) |
| `tests/runner/test_phase6_field_production.py` | 5 | `test_current_artifact_*` read the live Phase 6 output | Same class: pins a run artifact, not an invariant |
| `tests/runner/test_promote_graph_staging.py::TestOpenQ4DecisionEntry` | 4 | Reads decision-log entry `dod-1d` | Engine ruling deleted in group B; decision 3 |
| `tests/runner/test_graph_projector.py::test_real_tier4_*` | 2 | Read live Tier 4 gate states | Same class as Phase 6 |

Newly passing after the purge: 38 tests, all of which asserted on FIELDWISE state that had drifted (`test_dod1e_checkpoint_close`, `test_graph_claim_verifier`, `test_phase8_gate_content`, `test_claim_ledger`, part of the ticket tests).

Rule 3 applies: none of these is patched here. Each is a decision.
