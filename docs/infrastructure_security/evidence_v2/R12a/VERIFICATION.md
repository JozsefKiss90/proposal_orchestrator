# R12a — verification

| Field | Value |
|---|---|
| Ticket | R12a (parameterised evidence collector) |
| Step sheet | `STEPS.md` |
| Decision record | `docs/tier4_orchestration_state/decision_log/aws-redeployment-r12a-collector_2026-10-28.json` |
| Verified by | agent (Claude), device shell, files read as `utf-8-sig`, failure sets compared by script |
| Status | **All criteria PASS; operator confirmed in session 2026-10-29 ("zárd le az R12a-t", ~00:03 UTC); R12a DONE** |

## Round 1 — step 01 (baseline) and step 02 (the R12a tests on the start commit)

| Criterion | Evidence | Result | Reason |
|---|---|---|---|
| Commit and tree | `R12a_01_commit.txt` | PASS (deviation recorded) | HEAD `215727b5c66d34365a6bea95df0db9589fbef77d starting R12a`, then `265f88d tick R9e`; `265f88d..HEAD` the 21 expected files (R10 change, evidence and record, register and worklog v2, tickets, this handoff); status only this folder. No `close R10` commit: R12a-D22 |
| Interpreter and libraries | `R12a_01_versions.txt` | PASS | Python 3.10.6; boto3 1.42.68, botocore 1.42.68, python-dotenv 1.2.2, pytest 9.0.2. `.venv-lint` was deactivated before the block |
| Baseline recorded | `R12a_01_baseline-pytest.txt` | PASS | `200 failed, 9016 passed, 86 skipped, 2 warnings in 854.96s`; `exit=1`; no `ERROR`. The 200 ids equal the R10 after-run set (`R10_04`) id for id |
| The R12a tests fail on the start commit | `R12a_02_head-criteria.txt` | PASS | Device VM, `git archive 215727b` + the new test module, its fixtures and the amended guard test only: the module cannot import the collector (`exit=2`); `test_default_scope_is_the_v2_side_only` fails on the old scope (`exit=1`) |

## Round 2 — steps 03–05 (on the R12a change, before its commit)

| Criterion | Evidence | Result | Reason |
|---|---|---|---|
| Diff and tree | `R12a_03_diff-stat.txt` | PASS | HEAD `215727b … starting R12a`; working-tree diff exactly `deploy/aws/README.md` (9+), `tests/test_old_id_guard.py` (4+), `tools/old_id_guard.py` (12 lines): 3 files, 22+, 3−; status `??` only for the collector, its host scripts, the inputs file, the test module, the fixtures, the decision record and this folder. No `runner/`, `harness/`, v1 tree or register path (R12a-D13). git's LF→CRLF warnings are not errors |
| R12a tests and touched modules | `R12a_03_pytest.txt` | PASS | Python 3.10.6; `230 passed, 1 skipped`; `exit=0`; no `FAILED` / `ERROR`. The skip is `TestCriterion2::test_a_symlink_into_the_v1_tree_is_refused` (Windows without the symlink privilege); it passes on the device VM (decision record, known gap) |
| Old-ID guard over the collector | `R12a_03_old-id-guard-collector.txt` | PASS | `CLEAN: no old-account id in tools/collect_evidence_v2.py, tools/collector_host_checks, tests/tools/test_collect_evidence_v2.py, tests/tools/fixtures/collector, deploy/aws/collector_inputs.json (20 ids checked)`; `exit=0` |
| Plan over the real files | `R12a_03_collector-plan.txt` | PASS | `exit=0`; 95 lines; every command `--profile po-r1`; `--region eu-north-1` on every command but `iam` and `organizations`, which carry none (R12a-D24); no `get-secret-value`; the 13 host-dependent checks `not collected: host stack outputs absent (--host-outputs)`; every id-shaped token is a value of `R4_outputs.json`–`R8_outputs.json`, the parameter files or `collector_inputs.json` (agent script); no `R12a_03_collector` folder created |
| Full suite after | `R12a_04_full-pytest.txt` | PASS | Python 3.10.6; `200 failed, 9080 passed, 87 skipped, 2 warnings in 1065.14s`; `exit=1`. By id against step 01: the same 200 ids, **no new failure**, none gone; no `ERROR`. 9080 = 9016 + 64 and 87 = 86 + 1: the 65 R12a tests, the symlink case skipped as in step 03 |
| Old-ID guard (default scope) | `R12a_05_old-id-guard.txt` | PASS | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0`. The scope now includes the collector, its scripts and its fixtures (R12a-D11) |
| Secret scan (last) | `R12a_05_secret-scan.txt` | PASS | `CLEAN: docs/infrastructure_security/evidence_v2/R12a`; `exit=0`. Re-run by the agent after this report was written: CLEAN |

## Ticket criteria (`plans/aws_redeployment_tickets.md`, R12a)

| # | Criterion | Result | Evidence and reason |
|---|---|---|---|
| 1 | A test runs the collector against fixture stack outputs and confirms that every id it uses comes from them | PASS | `tests/tools/test_collect_evidence_v2.py::TestCriterion1`: a full run against `tests/tools/fixtures/collector/` with a fake AWS CLI; every id-shaped token of every recorded command (SSM host scripts included) is a fixture atom, and every fixture account, Region and resource id is used; rewriting the fixture ids rewrites the commands; no fixture value equals a real one and no real value reaches a fixture run; the module and the host scripts hold no id. Failing on `215727b` (`R12a_02`), passing in `R12a_03_pytest.txt` and `R12a_04_full-pytest.txt`. The plan over the real files (`R12a_03_collector-plan.txt`) shows the same on the repository's own outputs |
| 2 | A test confirms that the collector refuses an output path inside the v1 tree | PASS | `TestCriterion2`: `evidence/`, `evidence/11_audit_package`, a ticket-shaped folder under `evidence/`, `audit_package/`, register v1, a `..` path and an absolute path into the v1 tree are refused with exit 2, before any AWS call and with the tree unchanged; also any path outside `evidence_v2/`, a non-derived folder, an existing run folder and a missing ticket folder. The symlink case is skipped on Windows and passes on the device VM |
| 3 | The R3 old-ID test passes over the collector | PASS | `R12a_03_old-id-guard-collector.txt` CLEAN; `test_old_id_guard_is_clean_over_the_collector`; the guard's default scope covers the collector from now on (`tests/test_old_id_guard.py`, `R12a_05_old-id-guard.txt`) |

Also settled (decision record): host checks through SSM with fixed scripts and their SHA-256 (R12a-D4, D16);
F7 and DC-15 in-host checks written (R12a-D5, D17); DC-40 with the organization and an expected
`AccessDeniedException` on SCP listing (R12a-D18); DC-33–35 through the R9 launcher (R12a-D19); the
coverage map ties all 41 register v2 rows (R12a-D7); read-only verbs (R12a-D8); stale outputs refused
(R12a-D3, D26). Findings: F-R12a-1 (register v2 summary table stale; R12b), F-R12a-2 (DC-26 right after
the Converse call may be early; R12b), F-R12a-3 (the host bundle and the outside bucket have no owner yet;
R12b).

Register v2: no change (R12a-D12, D21). Worklog: entry of 2026-10-29, R12a.

## Baseline failure set (200, by id)

Identical in `R12a_01_baseline-pytest.txt` and `R12a_04_full-pytest.txt`.

```
FAILED tests/runner/test_budget_validation_artifact.py::TestAnIncompleteResponseFailsRatherThanLandingHalf::test_a_response_without_the_validation_fields_fails
FAILED tests/runner/test_budget_validation_artifact.py::TestItRefusesArtifactStatusRatherThanDroppingIt::test_the_response_is_rejected
FAILED tests/runner/test_budget_validation_artifact.py::TestOneResponseWritesBothFiles::test_both_canonical_paths_are_written
FAILED tests/runner/test_budget_validation_artifact.py::TestOneResponseWritesBothFiles::test_the_assessment_still_carries_its_metadata
FAILED tests/runner/test_budget_validation_artifact.py::TestOneResponseWritesBothFiles::test_the_directory_now_holds_a_json_file_for_the_disk_check
FAILED tests/runner/test_budget_validation_artifact.py::TestOneResponseWritesBothFiles::test_the_validation_file_carries_its_own_fields_only
FAILED tests/runner/test_budget_validation_artifact.py::TestThePromptNamesBothAnchorFields::test_both_anchors_appear_in_the_assembled_prompt
FAILED tests/runner/test_budget_validation_artifact.py::TestThePromptNamesBothAnchorFields::test_the_directive_asks_for_no_metadata_field
FAILED tests/runner/test_caller_context.py::TestCliPromptCallerContext::test_context_merged_into_prompt
FAILED tests/runner/test_caller_context.py::TestFailClosedAbsentSources::test_run_agent_passes_none_when_sources_absent
FAILED tests/runner/test_claude_transport.py::TestCliPathResolution::test_unset_pin_uses_absolute_path_search_result
FAILED tests/runner/test_constitutional_compliance_check_tapm.py::TestConstitutionalComplianceCheckTapmInvocation::test_phase6_does_not_require_tier5
FAILED tests/runner/test_constitutional_compliance_check_tapm.py::TestConstitutionalComplianceCheckTapmInvocation::test_prompt_size_bounded_at_runtime
FAILED tests/runner/test_constitutional_compliance_check_tapm.py::TestConstitutionalComplianceCheckTapmInvocation::test_tapm_invocation_passes_tools
FAILED tests/runner/test_constitutional_compliance_check_tapm.py::TestConstitutionalComplianceCheckTapmInvocation::test_tapm_prompt_not_cli_prompt
FAILED tests/runner/test_constitutional_compliance_check_tapm.py::TestConstitutionalComplianceCheckTapmInvocation::test_tapm_timeout_uses_1200s
FAILED tests/runner/test_dod1e_checkpoint_close.py::test_real_checkpoint_predicate_passes_directly
FAILED tests/runner/test_dod1e_checkpoint_close.py::test_real_checkpoint_published
FAILED tests/runner/test_dod1e_checkpoint_close.py::test_real_checkpoint_records_gate09_quad_verbatim
FAILED tests/runner/test_drafting_skill_hygiene.py::TestSizeLimits::test_under_size_limit[excellence-section-drafting.md]
FAILED tests/runner/test_drafting_skill_hygiene.py::TestSizeLimits::test_under_size_limit[impact-section-drafting.md]
FAILED tests/runner/test_drafting_skill_hygiene.py::TestSizeLimits::test_under_size_limit[implementation-section-drafting.md]
FAILED tests/runner/test_gate10d_consistency_fix.py::TestImplementationPartnerLegalNames::test_partners_json_has_correct_legal_names
FAILED tests/runner/test_leakage_scan.py::TestTheTreeScan::test_no_new_leak
FAILED tests/runner/test_leakage_scan.py::TestTheTreeScan::test_the_branch_is_not_clean_and_says_so
FAILED tests/runner/test_output_contract_routing.py::TestDefaultOutputContract::test_default_contract_uses_single_artifact
FAILED tests/runner/test_output_contract_routing.py::TestGateEnforcementFailClosed::test_missing_deterministic_predicates_fails
FAILED tests/runner/test_output_contract_routing.py::TestGateEnforcementFailClosed::test_missing_gate_id_fails
FAILED tests/runner/test_output_contract_routing.py::TestGateEnforcementFailClosed::test_missing_overall_status_fails
FAILED tests/runner/test_output_contract_routing.py::TestGateEnforcementFailClosed::test_multiple_missing_fields_all_reported
FAILED tests/runner/test_output_contract_routing.py::TestGateEnforcementFailClosed::test_run_id_mismatch_fails
FAILED tests/runner/test_output_contract_routing.py::TestGateEnforcementPayloadValidation::test_decision_log_entry_extracted_and_written
FAILED tests/runner/test_output_contract_routing.py::TestGateEnforcementPayloadValidation::test_no_canonical_artifact_written_to_phase_outputs
FAILED tests/runner/test_output_contract_routing.py::TestGateEnforcementPayloadValidation::test_response_not_validated_against_unrelated_schemas
FAILED tests/runner/test_output_contract_routing.py::TestGateEnforcementPayloadValidation::test_skillresult_shaped_success_envelope_unwrapped
FAILED tests/runner/test_output_contract_routing.py::TestGateEnforcementPayloadValidation::test_valid_gate_fail_response_accepted
FAILED tests/runner/test_output_contract_routing.py::TestGateEnforcementPayloadValidation::test_valid_gate_pass_response_accepted
FAILED tests/runner/test_output_contract_routing.py::TestGateEnforcementPayloadValidation::test_wrapped_envelope_with_incomplete_payload_still_fails
FAILED tests/runner/test_output_contract_routing.py::TestMultiArtifactNotTriggeredByInputs::test_single_artifact_with_many_inputs
FAILED tests/runner/test_output_contract_routing.py::TestPhase3NoRegression::test_gate_enforcement_succeeds_in_phase3_context
FAILED tests/runner/test_output_contract_routing.py::TestPhase3NoRegression::test_wp_normalization_still_works_as_single_artifact
FAILED tests/runner/test_output_contract_routing.py::TestTrueMultiArtifactStillWorks::test_missing_sub_artifact_fails
FAILED tests/runner/test_output_contract_routing.py::TestTrueMultiArtifactStillWorks::test_multi_artifact_explicit_declaration_works
FAILED tests/runner/test_phase2_artifact_production.py::TestCallBindingFailClosed::test_missing_compliance_fields_in_response_fails
FAILED tests/runner/test_phase2_artifact_production.py::TestCallBindingFailClosed::test_missing_mappings_in_response_fails
FAILED tests/runner/test_phase2_artifact_production.py::TestCallBindingSkillWrite::test_binding_output_paths_correct
FAILED tests/runner/test_phase2_artifact_production.py::TestCallBindingSkillWrite::test_both_tier3_artifacts_written
FAILED tests/runner/test_phase2_artifact_production.py::TestSummarySkillWrite::test_missing_rationale_fails
FAILED tests/runner/test_phase2_artifact_production.py::TestSummarySkillWrite::test_summary_artifact_written
FAILED tests/runner/test_phase2_artifact_production.py::TestSummarySkillWrite::test_summary_output_path_correct
FAILED tests/runner/test_phase3_execution_fixes.py::TestDecisionLogWriteWindows::test_timestamp_colons_sanitized_in_decision_log
FAILED tests/runner/test_phase3_execution_fixes.py::TestPhase3SkillSequenceIntegration::test_instrument_failure_does_not_block_as_malformed
FAILED tests/runner/test_phase3_execution_fixes.py::TestSkillResultInterception::test_constitutional_halt_intercepted
FAILED tests/runner/test_phase3_execution_fixes.py::TestSkillResultInterception::test_missing_input_failure_intercepted
FAILED tests/runner/test_phase3_execution_fixes.py::TestSkillResultInterception::test_success_status_not_intercepted
FAILED tests/runner/test_phase3_execution_fixes.py::TestSkillResultInterception::test_valid_artifact_not_intercepted
FAILED tests/runner/test_phase4_artifact_production.py::TestGanttScheduleBuilderArtifactProduction::test_cross_wp_depends_on_tasks_accepted_by_schema
FAILED tests/runner/test_phase4_artifact_production.py::TestGanttScheduleBuilderArtifactProduction::test_response_missing_required_field_rejected
FAILED tests/runner/test_phase4_artifact_production.py::TestGanttScheduleBuilderArtifactProduction::test_response_missing_run_id_rejected
FAILED tests/runner/test_phase4_artifact_production.py::TestGanttScheduleBuilderArtifactProduction::test_response_with_artifact_status_rejected
FAILED tests/runner/test_phase4_artifact_production.py::TestGanttScheduleBuilderArtifactProduction::test_response_wrong_schema_id_rejected
FAILED tests/runner/test_phase4_artifact_production.py::TestGanttScheduleBuilderArtifactProduction::test_valid_response_without_milestone_dependency_fields
FAILED tests/runner/test_phase4_artifact_production.py::TestGanttScheduleBuilderArtifactProduction::test_valid_response_writes_gantt_json
FAILED tests/runner/test_phase5_decomposition.py::TestCoreBuilderExecution::test_uses_600s_timeout
FAILED tests/runner/test_phase5_decomposition.py::TestCoreBuilderExecution::test_uses_tapm_tools
FAILED tests/runner/test_phase5_decomposition.py::TestCoreBuilderExecution::test_writes_partial_artifact
FAILED tests/runner/test_phase5_decomposition.py::TestDecEnricherExecution::test_preserves_pathways_and_kpis
FAILED tests/runner/test_phase5_decomposition.py::TestDecEnricherExecution::test_writes_complete_artifact
FAILED tests/runner/test_phase5_decomposition.py::TestFullSequence::test_sequential_execution_produces_complete_artifact
FAILED tests/runner/test_phase5_tapm_migration.py::TestDecCheckTapmInvocation::test_no_input_serialization_in_prompt
FAILED tests/runner/test_phase5_tapm_migration.py::TestDecCheckTapmInvocation::test_tapm_invocation_passes_tools
FAILED tests/runner/test_phase5_tapm_migration.py::TestDecCheckTapmInvocation::test_tapm_timeout_uses_1200s
FAILED tests/runner/test_phase5_tapm_migration.py::TestDecCheckTapmInvocation::test_validation_report_written
FAILED tests/runner/test_phase5_tapm_migration.py::TestPhase5ArtifactProductionPath::test_canonical_artifact_written
FAILED tests/runner/test_phase5_tapm_migration.py::TestPhase5ArtifactProductionPath::test_tapm_invocation_passes_tools
FAILED tests/runner/test_phase5_tapm_migration.py::TestPhase5ArtifactProductionPath::test_tapm_timeout_uses_1200s
FAILED tests/runner/test_phase6_field_production.py::TestComplianceProfileDerivativeLabeling::test_current_artifact_wp9_cites_tier2b_for_ai_on_demand
FAILED tests/runner/test_phase6_field_production.py::TestComplianceProfileDerivativeLabeling::test_response_with_compliance_only_mandate_is_detectable
FAILED tests/runner/test_phase6_field_production.py::TestComplianceProfileDerivativeLabeling::test_response_with_tier2b_backed_open_science_is_valid
FAILED tests/runner/test_phase6_field_production.py::TestGenderDimensionTraceability::test_safe_wording_contains_tier2b_deferral
FAILED tests/runner/test_phase6_field_production.py::TestGenderDimensionTraceability::test_safe_wording_has_no_violating_phrase
FAILED tests/runner/test_phase6_field_production.py::TestGenderDimensionTraceability::test_tier2b_backed_assertion_is_permitted
FAILED tests/runner/test_phase6_field_production.py::TestGenderDimensionTraceability::test_violating_response_detectable_in_artifact
FAILED tests/runner/test_phase6_field_production.py::TestGovernanceModelBuilderFieldProduction::test_output_contains_ethics_assessment
FAILED tests/runner/test_phase6_field_production.py::TestGovernanceModelBuilderFieldProduction::test_output_contains_instrument_sections
FAILED tests/runner/test_phase6_field_production.py::TestGovernanceModelBuilderFieldProduction::test_risk_register_is_placeholder
FAILED tests/runner/test_phase6_field_production.py::TestRiskRegisterBuilderFieldPreservation::test_ethics_assessment_preserved_after_risk_enrichment
FAILED tests/runner/test_phase6_field_production.py::TestRiskRegisterBuilderFieldPreservation::test_instrument_sections_preserved_after_risk_enrichment
FAILED tests/runner/test_phase6_field_production.py::TestRiskRegisterBuilderFieldPreservation::test_risk_register_is_populated
FAILED tests/runner/test_phase6_field_production.py::TestTraceabilityFooterProduction::test_existing_fields_preserved_with_traceability_footer
FAILED tests/runner/test_phase6_field_production.py::TestTraceabilityFooterProduction::test_traceability_footer_contains_tier1_paths
FAILED tests/runner/test_phase6_field_production.py::TestTraceabilityFooterProduction::test_traceability_footer_preserved_after_risk_enrichment
FAILED tests/runner/test_phase6_field_production.py::TestTraceabilityFooterProduction::test_traceability_footer_uses_full_paths
FAILED tests/runner/test_phase6_field_production.py::TestTraceabilityFooterProduction::test_traceability_footer_written_to_artifact
FAILED tests/runner/test_phase6_tapm_migration.py::TestGovernanceModelBuilderTapmInvocation::test_tapm_invocation_passes_tools
FAILED tests/runner/test_phase6_tapm_migration.py::TestGovernanceModelBuilderTapmInvocation::test_tapm_timeout_uses_1200s
FAILED tests/runner/test_phase6_tapm_migration.py::TestRiskRegisterBuilderTapmInvocation::test_tapm_invocation_passes_tools
FAILED tests/runner/test_phase6_tapm_migration.py::TestRiskRegisterBuilderTapmInvocation::test_tapm_path_invoked_not_cli_prompt
FAILED tests/runner/test_phase6_tapm_migration.py::TestRiskRegisterBuilderTapmInvocation::test_tapm_timeout_uses_1200s
FAILED tests/runner/test_phase8_canonicalization.py::TestSpecLeanness::test_impact_no_component_keyword_scan
FAILED tests/runner/test_phase8_consistency_layer.py::TestDraftingSkillHygiene::test_under_size_limit[excellence-section-drafting.md]
FAILED tests/runner/test_phase8_consistency_layer.py::TestDraftingSkillHygiene::test_under_size_limit[impact-section-drafting.md]
FAILED tests/runner/test_phase8_consistency_layer.py::TestDraftingSkillHygiene::test_under_size_limit[implementation-section-drafting.md]
FAILED tests/runner/test_phase8_gate_content.py::TestCurrentArtifactState::test_excellence_no_assumed_claims
FAILED tests/runner/test_phase8_gate_content.py::TestCurrentArtifactState::test_excellence_overall_status_not_assumed
FAILED tests/runner/test_risk_register_builder_completion.py::TestRiskRegisterBuilderCompletion::test_completes_with_non_empty_risk_register
FAILED tests/runner/test_risk_register_builder_completion.py::TestRiskRegisterBuilderCompletion::test_ethics_assessment_preserved
FAILED tests/runner/test_risk_register_builder_completion.py::TestRiskRegisterBuilderCompletion::test_governance_matrix_preserved
FAILED tests/runner/test_risk_register_builder_completion.py::TestRiskRegisterBuilderCompletion::test_instrument_sections_preserved
FAILED tests/runner/test_risk_register_builder_completion.py::TestRiskRegisterBuilderCompletion::test_management_roles_preserved
FAILED tests/runner/test_risk_register_builder_completion.py::TestRiskRegisterBuilderConstraints::test_base_artifact_missing_fails
FAILED tests/runner/test_risk_register_builder_completion.py::TestRiskRegisterBuilderSchemaValidation::test_merged_artifact_has_all_required_fields
FAILED tests/runner/test_risk_register_builder_completion.py::TestRiskRegisterBuilderSchemaValidation::test_schema_id_mismatch_in_patch_fails
FAILED tests/runner/test_skill_applicability.py::TestOtherSkillsUnaffected::test_non_tier5_skills_always_invoked
FAILED tests/runner/test_skill_applicability.py::TestPhase2SkillSkipped::test_traceability_skip_does_not_block_other_skills
FAILED tests/runner/test_skill_applicability.py::TestPhase2SkillSkipped::test_traceability_skipped_in_phase2
FAILED tests/runner/test_skill_runtime.py::TestCanonicalInputBinding::test_caller_provided_inputs_override_disk
FAILED tests/runner/test_skill_runtime.py::TestCanonicalInputBinding::test_file_input_resolved_from_disk
FAILED tests/runner/test_skill_runtime.py::TestExcellenceOutputRobustness::test_valid_concise_excellence_json_writes_correctly
FAILED tests/runner/test_skill_runtime.py::TestMultiArtifactCanonicalPathKeys::test_basename_keyed_still_works
FAILED tests/runner/test_skill_runtime.py::TestMultiArtifactCanonicalPathKeys::test_canonical_path_keyed_response
FAILED tests/runner/test_skill_runtime.py::TestMultiArtifactCanonicalPathKeys::test_flat_shape_still_works
FAILED tests/runner/test_skill_runtime.py::TestMultiArtifactCanonicalPathKeys::test_stem_keyed_still_works
FAILED tests/runner/test_skill_runtime.py::TestMultiArtifactLogging::test_success_logs_an_ok_line
FAILED tests/runner/test_skill_runtime.py::TestMultiArtifactLogging::test_validation_failure_logs_a_fail_line
FAILED tests/runner/test_skill_runtime.py::TestMultiTargetWritesTo::test_flat_mixed_response_both_written
FAILED tests/runner/test_skill_runtime.py::TestMultiTargetWritesTo::test_missing_field_in_multi_field_target
FAILED tests/runner/test_skill_runtime.py::TestMultiTargetWritesTo::test_missing_first_target_fails
FAILED tests/runner/test_skill_runtime.py::TestMultiTargetWritesTo::test_missing_second_target_fails
FAILED tests/runner/test_skill_runtime.py::TestMultiTargetWritesTo::test_nested_keyed_multi_field_target
FAILED tests/runner/test_skill_runtime.py::TestOptionalReadsFrom::test_no_optional_field_means_empty_list
FAILED tests/runner/test_skill_runtime.py::TestOptionalReadsFrom::test_optional_present_is_resolved
FAILED tests/runner/test_skill_runtime.py::TestPhase8FileLevelArtifactWrite::test_impact_section_writes_to_exact_path
FAILED tests/runner/test_skill_runtime.py::TestPhase8FileLevelArtifactWrite::test_implementation_section_writes_to_exact_path
FAILED tests/runner/test_skill_runtime.py::TestRunSkillSchemaValidation::test_artifact_status_present_in_response
FAILED tests/runner/test_skill_runtime.py::TestRunSkillSchemaValidation::test_missing_run_id_in_response
FAILED tests/runner/test_skill_runtime.py::TestRunSkillSchemaValidation::test_wrong_run_id_in_response
FAILED tests/runner/test_skill_runtime.py::TestRunSkillSuccess::test_artifact_status_absent_in_written_artifact
FAILED tests/runner/test_skill_runtime.py::TestRunSkillSuccess::test_run_id_propagated_to_written_artifact
FAILED tests/runner/test_skill_runtime.py::TestRunSkillSuccess::test_schema_id_in_written_artifact
FAILED tests/runner/test_skill_runtime.py::TestRunSkillSuccess::test_success_with_valid_inputs
FAILED tests/runner/test_skill_runtime.py::TestTapmTransportFailureDiagnostics::test_cliprompt_diagnostic_has_no_tapm_tools
FAILED tests/runner/test_skill_runtime.py::TestTapmTransportFailureDiagnostics::test_tapm_diagnostic_includes_declared_inputs
FAILED tests/runner/test_skill_runtime.py::TestTapmTransportFailureDiagnostics::test_tapm_diagnostic_includes_prompt_sizes
FAILED tests/runner/test_skill_runtime.py::TestTapmTransportFailureDiagnostics::test_tapm_diagnostic_includes_tools_metadata
FAILED tests/runner/test_skill_runtime.py::TestTapmTransportFailureDiagnostics::test_tapm_timeout_writes_diagnostic
FAILED tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_empty_output_classified_correctly
FAILED tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_generic_transport_error_writes_diagnostic
FAILED tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_nonzero_exit_classified_correctly
FAILED tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_prompt_size_metadata_in_diagnostic
FAILED tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_rate_limit_classified_correctly
FAILED tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_timeout_failure_reason_includes_diag_path
FAILED tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_timeout_returns_failure_result
FAILED tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_timeout_with_node_id
FAILED tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_timeout_writes_prompt_files
FAILED tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_timeout_writes_stdout_stderr_files
FAILED tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_timeout_writes_transport_diag_json
FAILED tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactMissingInputs::test_missing_base_artifact
FAILED tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactMissingInputs::test_missing_catalog_config
FAILED tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactResponseFormat::test_compact_valid_json_accepted
FAILED tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactResponseFormat::test_model_signaled_failure_intercepted
FAILED tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactResponseFormat::test_non_json_response_rejected
FAILED tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactSuccess::test_all_seven_fields_present_in_merged
FAILED tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactSuccess::test_base_fields_preserved
FAILED tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactSuccess::test_enrichment_merges_patch_into_base
FAILED tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactSuccess::test_gate_sees_nonnull_dec_fields
FAILED tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactValidation::test_artifact_status_in_patch_rejected
FAILED tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactValidation::test_merged_result_missing_required_field_rejected
FAILED tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactValidation::test_run_id_mismatch_rejected
FAILED tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactValidation::test_schema_id_mismatch_rejected
FAILED tests/runner/test_skill_runtime_tapm.py::TestRunSkillTapmMode::test_default_mode_is_cli_prompt
FAILED tests/runner/test_skill_runtime_tapm.py::TestRunSkillTapmMode::test_node_id_forwarded_to_tapm_prompt
FAILED tests/runner/test_skill_runtime_tapm.py::TestRunSkillTapmMode::test_node_id_none_works_for_tapm
FAILED tests/runner/test_skill_runtime_tapm.py::TestRunSkillTapmMode::test_tapm_mode_passes_tools
FAILED tests/runner/test_skill_runtime_tapm.py::TestRunSkillTapmMode::test_tapm_mode_schema_validation_failure
FAILED tests/runner/test_skill_runtime_tapm.py::TestRunSkillTapmMode::test_tapm_mode_skips_resolve_inputs
FAILED tests/runner/test_skill_runtime_tapm.py::TestRunSkillTapmMode::test_tapm_mode_skips_skill_prompt_assembly
FAILED tests/runner/test_skill_runtime_tapm.py::TestRunSkillTapmMode::test_tapm_mode_writes_artifact
FAILED tests/test_demo_architecture_seeds.py::TestAnonymity::test_the_branch_is_no_less_ok_than_before
FAILED tests/test_demo_candidate_blind_baseline.py::TestTheReportsNumbersAreTheArtifactsOwn::test_the_leakage_scan_file_count_is_re_derivable
FAILED tests/test_demo_concept.py::TestAnonymity::test_the_brief_adds_no_new_leak_to_the_branch
FAILED tests/test_demo_consortium.py::TestAnonymity::test_the_leakage_scan_is_clean_over_tiers_3_to_5_and_the_vault
FAILED tests/test_demo_dev_graph_snapshot.py::TestAnonymity::test_the_new_artifacts_are_scanned_and_carry_no_new_leak
FAILED tests/test_demo_fictional_budget_override.py::TestThePhase7DispatchReachedTheGate::test_tier_5_content_carries_the_fictional_label
FAILED tests/test_demo_phase7_budget_gate.py::TestTheHardBlockIsIntact::test_no_phase_8_output_exists
FAILED tests/test_demo_report.py::TestTheBlindLaneFigures::test_the_scan_count_is_the_scans_own
FAILED tests/test_demo_sources.py::TestAnonymity::test_the_branch_is_no_less_ok_than_before
FAILED tests/test_msca_dn_declaration_drafts.py::TestDeterminismAndTheCommittedArtifacts::test_the_committed_artifacts_are_reproducible
FAILED tests/test_tier2b_biodiv_intake.py::TestStaleExtractedFinding::test_the_extracted_files_still_belong_to_another_call
FAILED tests/test_tier2b_biodiv_intake.py::TestTierBoundaries::test_phase_1_still_owns_tier_2b_extracted
FAILED tests/test_transport_openai_compatible.py::TestErrorHandling::test_400_raises_malformed_request
FAILED tests/test_transport_openai_compatible.py::TestErrorHandling::test_403_raises_auth_error
FAILED tests/test_transport_openai_compatible.py::TestErrorHandling::test_404_raises_model_not_found
FAILED tests/test_transport_openai_compatible.py::TestErrorHandling::test_429_raises_rate_limit_error
FAILED tests/test_transport_openai_compatible.py::TestErrorHandling::test_500_raises_provider_error
FAILED tests/test_transport_openai_compatible.py::TestErrorHandling::test_503_raises_provider_error
FAILED tests/test_transport_openai_compatible.py::TestErrorHandling::test_connection_error_raises_provider_error
FAILED tests/test_transport_openai_compatible.py::TestErrorHandling::test_timeout_raises_timeout_error
FAILED tests/test_transport_openai_compatible.py::TestResponseParsing::test_call_sends_post_and_returns_parsed
FAILED tests/test_transport_openai_compatible.py::TestResponseParsing::test_tool_calls_round_trip
```
