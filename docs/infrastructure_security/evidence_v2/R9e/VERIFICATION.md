# R9e — verification

| Field | Value |
|---|---|
| Ticket | R9e (EU region support) |
| Step sheet | `STEPS.md` |
| Decision record | `docs/tier4_orchestration_state/decision_log/aws-redeployment-r9e-eu-region_2026-10-27.json` |
| Verified by | agent (Claude), device shell, files read as `utf-8-sig`, failure sets compared by script |
| Status | **All criteria PASS; awaiting the operator's confirmation in session** |

## Round 1 — step 01 (baseline)

| Criterion | Evidence | Result | Reason |
|---|---|---|---|
| Commit and tree | `R9e_01_commit.txt` | PASS (deviation recorded) | HEAD `d1e767ba0df92c9a2ea36444f029dccbf872ab5e close R9`; the `starting R9e` commit had not been made, so status shows the staged handoff (`A`) and this folder's files. Code tree equal to `d1e767b`. Accepted by the operator ("19 a", R9e-D19); the commit followed as step 02b |
| Interpreter and libraries | `R9e_01_versions.txt` | PASS | Python 3.10.6; boto3 1.42.68, botocore 1.42.68, python-dotenv 1.2.2, pytest 9.0.2 |
| Baseline recorded | `R9e_01_baseline-pytest.txt` | PASS | Python 3.10.6; `202 failed, 8953 passed, 86 skipped, 2 warnings in 738.47s`; `exit=1`; 202 `FAILED` ids, no `ERROR`, no collection error. One id outside every R9 run, a WinError 32 file lock (F-R9e-1, R9e-D20) |

## Round 2 — steps 02b–05 (on the R9e change, before its commit)

| Criterion | Evidence | Result | Reason |
|---|---|---|---|
| Commit of the handoff | operator's report (RUNLOG 02b) | PASS | `175441e starting R9e`, 1 file, 90 insertions; nothing else staged |
| Diff and tree | `R9e_03_diff-stat.txt` | PASS | HEAD `175441e starting R9e`, then `d1e767b close R9`; `d1e767b..HEAD` only the handoff; working-tree diff exactly the 16 expected files (501+, 63−); status adds only this folder's files and the decision record. LF→CRLF warnings for already-LF files (R9e-D18), recorded in `RUNLOG.md` |
| R9e tests and touched modules | `R9e_03_pytest.txt` | PASS | Python 3.10.6; `573 passed in 100.79s`; no `FAILED`, no `ERROR`; `exit=0` (equal to the agent's device run) |
| Full suite after | `R9e_04_full-pytest.txt` | PASS | Python 3.10.6; `200 failed, 8997 passed, 86 skipped`; `exit=1`. By id: 200 failing, all in the baseline set; **no new failure**; no `ERROR`; no amended or new R9e test fails. No longer failing: `tests/test_transport_presets.py::TestPresetRegistry::test_registry_count` (amended away, R9e-D3) and `tests/test_demo_change_scenarios.py::TestTheAdvisoryIsNotConsumed::test_the_input_fingerprint_is_the_same_with_an_advisory_present[n08a_excellence_drafting]` (F-R9e-1; recorded, not counted, R9-D23) |
| Old-ID guard | `R9e_05_old-id-guard.txt` | PASS | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0` |
| Secret scan (last) | `R9e_05_secret-scan.txt` | PASS | `CLEAN: docs/infrastructure_security/evidence_v2/R9e`; `exit=0`. Re-run by the agent after this report was written: CLEAN |

## Ticket criteria (`plans/aws_redeployment_tickets.md`, R9e)

| # | Criterion | Result | Evidence and reason |
|---|---|---|---|
| 1 | An EU Converse preset exists and is tested (`BEDROCK_CONVERSE_EU`, backend `bedrock_converse`, default Region eu-north-1, `eu.` profiles; a test that the name stored by `50-secret.yaml` exists in `runner/transport/config.py`) | PASS | `runner/transport/config.py` `BEDROCK_CONVERSE_EU` (R9e-D1). `tests/test_transport_presets.py` `TestBedrockConverseEuPreset` (9 tests); `tests/test_aws_env_config_template.py` `test_the_stored_preset_exists_and_is_production_suitable` and `test_the_launcher_accepts_the_templates_value` (R9e-D2); `tests/test_host_env_launcher.py` `TestTheRealSecretsPreset::test_the_real_secrets_preset_is_accepted`, now unconditional (R9e-D15). Passing in `R9e_03` and `R9e_04` |
| 2 | No transport test fixes the region | PASS | The only Region literals that fixed a transport value (two mantle endpoint-override pairs with `us-east-1`) now use a sentinel (R9e-D4, F-R9e-5): `tests/test_transport_config.py::TestBedrockConfig::test_bedrock_with_explicit_endpoint`, `tests/test_transport_presets.py::TestEnvOverrides::test_endpoint_override`. New tests read Regions from a preset's attribute, the deployment parameters or sentinels; `test_definition` states the preset's own eu-north-1, which criterion 1 defines. The mantle presets' own `eu-west-1` assertions stay as attribute tests (R9e-D4) |
| 3 | The runbook guard test passes on the edited runbook | PASS | `plans/msca_dn_an12_host_runbook.md`: every host line through `runner.host_env --region eu-north-1 --secret-id proposal-orchestrator/env-config --`, no `export` lines, eu-north-1 Region lines, the `eu.` id rule, tag `bedrock-converse-eu-north-1@…`, steps 12–13 repaired (R9e-D6, D7, D17). `tests/test_anonymisation_host_runbook.py` (launcher prefix by the launcher's parser, Regions, exports, id rule; R9e-D14) passes in `R9e_03` and `R9e_04` |
| 4 | Or: closed N/A | N/A | Superseded: OD1 is eu-north-1 (decision record `aws-redeployment-od1-region-r1_2026-10-21`); R9e was built |

Also from the R9 record's `for_r9e`: `ALLOWED_REGIONS` holds eu-north-1 (R9e-D5); `converse_smoke` takes the Region from `AWS_REGION` only (R9e-D9, F-R9-7); the AN1c guard counts the host's drafter model under production mode (R9e-D8; `tests/harness/test_judge.py` `TestDrafterModelsOnTheHost`, `tests/harness/test_converse_judge.py` `TestTheHostsEnvironment`).

Register v2: no row (R9e touches no control, R9e-D10). Worklog: entry of 2026-10-28, R9e.

## Baseline failure set (202, by id)

Step 04 is compared against this set by id. Tests amended on purpose by R9e are listed in the decision record (`amended_test_ids`).

```
tests/runner/test_budget_validation_artifact.py::TestAnIncompleteResponseFailsRatherThanLandingHalf::test_a_response_without_the_validation_fields_fails
tests/runner/test_budget_validation_artifact.py::TestItRefusesArtifactStatusRatherThanDroppingIt::test_the_response_is_rejected
tests/runner/test_budget_validation_artifact.py::TestOneResponseWritesBothFiles::test_both_canonical_paths_are_written
tests/runner/test_budget_validation_artifact.py::TestOneResponseWritesBothFiles::test_the_assessment_still_carries_its_metadata
tests/runner/test_budget_validation_artifact.py::TestOneResponseWritesBothFiles::test_the_directory_now_holds_a_json_file_for_the_disk_check
tests/runner/test_budget_validation_artifact.py::TestOneResponseWritesBothFiles::test_the_validation_file_carries_its_own_fields_only
tests/runner/test_budget_validation_artifact.py::TestThePromptNamesBothAnchorFields::test_both_anchors_appear_in_the_assembled_prompt
tests/runner/test_budget_validation_artifact.py::TestThePromptNamesBothAnchorFields::test_the_directive_asks_for_no_metadata_field
tests/runner/test_caller_context.py::TestCliPromptCallerContext::test_context_merged_into_prompt
tests/runner/test_caller_context.py::TestFailClosedAbsentSources::test_run_agent_passes_none_when_sources_absent
tests/runner/test_claude_transport.py::TestCliPathResolution::test_unset_pin_uses_absolute_path_search_result
tests/runner/test_constitutional_compliance_check_tapm.py::TestConstitutionalComplianceCheckTapmInvocation::test_phase6_does_not_require_tier5
tests/runner/test_constitutional_compliance_check_tapm.py::TestConstitutionalComplianceCheckTapmInvocation::test_prompt_size_bounded_at_runtime
tests/runner/test_constitutional_compliance_check_tapm.py::TestConstitutionalComplianceCheckTapmInvocation::test_tapm_invocation_passes_tools
tests/runner/test_constitutional_compliance_check_tapm.py::TestConstitutionalComplianceCheckTapmInvocation::test_tapm_prompt_not_cli_prompt
tests/runner/test_constitutional_compliance_check_tapm.py::TestConstitutionalComplianceCheckTapmInvocation::test_tapm_timeout_uses_1200s
tests/runner/test_dod1e_checkpoint_close.py::test_real_checkpoint_predicate_passes_directly
tests/runner/test_dod1e_checkpoint_close.py::test_real_checkpoint_published
tests/runner/test_dod1e_checkpoint_close.py::test_real_checkpoint_records_gate09_quad_verbatim
tests/runner/test_drafting_skill_hygiene.py::TestSizeLimits::test_under_size_limit[excellence-section-drafting.md]
tests/runner/test_drafting_skill_hygiene.py::TestSizeLimits::test_under_size_limit[impact-section-drafting.md]
tests/runner/test_drafting_skill_hygiene.py::TestSizeLimits::test_under_size_limit[implementation-section-drafting.md]
tests/runner/test_gate10d_consistency_fix.py::TestImplementationPartnerLegalNames::test_partners_json_has_correct_legal_names
tests/runner/test_leakage_scan.py::TestTheTreeScan::test_no_new_leak
tests/runner/test_leakage_scan.py::TestTheTreeScan::test_the_branch_is_not_clean_and_says_so
tests/runner/test_output_contract_routing.py::TestDefaultOutputContract::test_default_contract_uses_single_artifact
tests/runner/test_output_contract_routing.py::TestGateEnforcementFailClosed::test_missing_deterministic_predicates_fails
tests/runner/test_output_contract_routing.py::TestGateEnforcementFailClosed::test_missing_gate_id_fails
tests/runner/test_output_contract_routing.py::TestGateEnforcementFailClosed::test_missing_overall_status_fails
tests/runner/test_output_contract_routing.py::TestGateEnforcementFailClosed::test_multiple_missing_fields_all_reported
tests/runner/test_output_contract_routing.py::TestGateEnforcementFailClosed::test_run_id_mismatch_fails
tests/runner/test_output_contract_routing.py::TestGateEnforcementPayloadValidation::test_decision_log_entry_extracted_and_written
tests/runner/test_output_contract_routing.py::TestGateEnforcementPayloadValidation::test_no_canonical_artifact_written_to_phase_outputs
tests/runner/test_output_contract_routing.py::TestGateEnforcementPayloadValidation::test_response_not_validated_against_unrelated_schemas
tests/runner/test_output_contract_routing.py::TestGateEnforcementPayloadValidation::test_skillresult_shaped_success_envelope_unwrapped
tests/runner/test_output_contract_routing.py::TestGateEnforcementPayloadValidation::test_valid_gate_fail_response_accepted
tests/runner/test_output_contract_routing.py::TestGateEnforcementPayloadValidation::test_valid_gate_pass_response_accepted
tests/runner/test_output_contract_routing.py::TestGateEnforcementPayloadValidation::test_wrapped_envelope_with_incomplete_payload_still_fails
tests/runner/test_output_contract_routing.py::TestMultiArtifactNotTriggeredByInputs::test_single_artifact_with_many_inputs
tests/runner/test_output_contract_routing.py::TestPhase3NoRegression::test_gate_enforcement_succeeds_in_phase3_context
tests/runner/test_output_contract_routing.py::TestPhase3NoRegression::test_wp_normalization_still_works_as_single_artifact
tests/runner/test_output_contract_routing.py::TestTrueMultiArtifactStillWorks::test_missing_sub_artifact_fails
tests/runner/test_output_contract_routing.py::TestTrueMultiArtifactStillWorks::test_multi_artifact_explicit_declaration_works
tests/runner/test_phase2_artifact_production.py::TestCallBindingFailClosed::test_missing_compliance_fields_in_response_fails
tests/runner/test_phase2_artifact_production.py::TestCallBindingFailClosed::test_missing_mappings_in_response_fails
tests/runner/test_phase2_artifact_production.py::TestCallBindingSkillWrite::test_binding_output_paths_correct
tests/runner/test_phase2_artifact_production.py::TestCallBindingSkillWrite::test_both_tier3_artifacts_written
tests/runner/test_phase2_artifact_production.py::TestSummarySkillWrite::test_missing_rationale_fails
tests/runner/test_phase2_artifact_production.py::TestSummarySkillWrite::test_summary_artifact_written
tests/runner/test_phase2_artifact_production.py::TestSummarySkillWrite::test_summary_output_path_correct
tests/runner/test_phase3_execution_fixes.py::TestDecisionLogWriteWindows::test_timestamp_colons_sanitized_in_decision_log
tests/runner/test_phase3_execution_fixes.py::TestPhase3SkillSequenceIntegration::test_instrument_failure_does_not_block_as_malformed
tests/runner/test_phase3_execution_fixes.py::TestSkillResultInterception::test_constitutional_halt_intercepted
tests/runner/test_phase3_execution_fixes.py::TestSkillResultInterception::test_missing_input_failure_intercepted
tests/runner/test_phase3_execution_fixes.py::TestSkillResultInterception::test_success_status_not_intercepted
tests/runner/test_phase3_execution_fixes.py::TestSkillResultInterception::test_valid_artifact_not_intercepted
tests/runner/test_phase4_artifact_production.py::TestGanttScheduleBuilderArtifactProduction::test_cross_wp_depends_on_tasks_accepted_by_schema
tests/runner/test_phase4_artifact_production.py::TestGanttScheduleBuilderArtifactProduction::test_response_missing_required_field_rejected
tests/runner/test_phase4_artifact_production.py::TestGanttScheduleBuilderArtifactProduction::test_response_missing_run_id_rejected
tests/runner/test_phase4_artifact_production.py::TestGanttScheduleBuilderArtifactProduction::test_response_with_artifact_status_rejected
tests/runner/test_phase4_artifact_production.py::TestGanttScheduleBuilderArtifactProduction::test_response_wrong_schema_id_rejected
tests/runner/test_phase4_artifact_production.py::TestGanttScheduleBuilderArtifactProduction::test_valid_response_without_milestone_dependency_fields
tests/runner/test_phase4_artifact_production.py::TestGanttScheduleBuilderArtifactProduction::test_valid_response_writes_gantt_json
tests/runner/test_phase5_decomposition.py::TestCoreBuilderExecution::test_uses_600s_timeout
tests/runner/test_phase5_decomposition.py::TestCoreBuilderExecution::test_uses_tapm_tools
tests/runner/test_phase5_decomposition.py::TestCoreBuilderExecution::test_writes_partial_artifact
tests/runner/test_phase5_decomposition.py::TestDecEnricherExecution::test_preserves_pathways_and_kpis
tests/runner/test_phase5_decomposition.py::TestDecEnricherExecution::test_writes_complete_artifact
tests/runner/test_phase5_decomposition.py::TestFullSequence::test_sequential_execution_produces_complete_artifact
tests/runner/test_phase5_tapm_migration.py::TestDecCheckTapmInvocation::test_no_input_serialization_in_prompt
tests/runner/test_phase5_tapm_migration.py::TestDecCheckTapmInvocation::test_tapm_invocation_passes_tools
tests/runner/test_phase5_tapm_migration.py::TestDecCheckTapmInvocation::test_tapm_timeout_uses_1200s
tests/runner/test_phase5_tapm_migration.py::TestDecCheckTapmInvocation::test_validation_report_written
tests/runner/test_phase5_tapm_migration.py::TestPhase5ArtifactProductionPath::test_canonical_artifact_written
tests/runner/test_phase5_tapm_migration.py::TestPhase5ArtifactProductionPath::test_tapm_invocation_passes_tools
tests/runner/test_phase5_tapm_migration.py::TestPhase5ArtifactProductionPath::test_tapm_timeout_uses_1200s
tests/runner/test_phase6_field_production.py::TestComplianceProfileDerivativeLabeling::test_current_artifact_wp9_cites_tier2b_for_ai_on_demand
tests/runner/test_phase6_field_production.py::TestComplianceProfileDerivativeLabeling::test_response_with_compliance_only_mandate_is_detectable
tests/runner/test_phase6_field_production.py::TestComplianceProfileDerivativeLabeling::test_response_with_tier2b_backed_open_science_is_valid
tests/runner/test_phase6_field_production.py::TestGenderDimensionTraceability::test_safe_wording_contains_tier2b_deferral
tests/runner/test_phase6_field_production.py::TestGenderDimensionTraceability::test_safe_wording_has_no_violating_phrase
tests/runner/test_phase6_field_production.py::TestGenderDimensionTraceability::test_tier2b_backed_assertion_is_permitted
tests/runner/test_phase6_field_production.py::TestGenderDimensionTraceability::test_violating_response_detectable_in_artifact
tests/runner/test_phase6_field_production.py::TestGovernanceModelBuilderFieldProduction::test_output_contains_ethics_assessment
tests/runner/test_phase6_field_production.py::TestGovernanceModelBuilderFieldProduction::test_output_contains_instrument_sections
tests/runner/test_phase6_field_production.py::TestGovernanceModelBuilderFieldProduction::test_risk_register_is_placeholder
tests/runner/test_phase6_field_production.py::TestRiskRegisterBuilderFieldPreservation::test_ethics_assessment_preserved_after_risk_enrichment
tests/runner/test_phase6_field_production.py::TestRiskRegisterBuilderFieldPreservation::test_instrument_sections_preserved_after_risk_enrichment
tests/runner/test_phase6_field_production.py::TestRiskRegisterBuilderFieldPreservation::test_risk_register_is_populated
tests/runner/test_phase6_field_production.py::TestTraceabilityFooterProduction::test_existing_fields_preserved_with_traceability_footer
tests/runner/test_phase6_field_production.py::TestTraceabilityFooterProduction::test_traceability_footer_contains_tier1_paths
tests/runner/test_phase6_field_production.py::TestTraceabilityFooterProduction::test_traceability_footer_preserved_after_risk_enrichment
tests/runner/test_phase6_field_production.py::TestTraceabilityFooterProduction::test_traceability_footer_uses_full_paths
tests/runner/test_phase6_field_production.py::TestTraceabilityFooterProduction::test_traceability_footer_written_to_artifact
tests/runner/test_phase6_tapm_migration.py::TestGovernanceModelBuilderTapmInvocation::test_tapm_invocation_passes_tools
tests/runner/test_phase6_tapm_migration.py::TestGovernanceModelBuilderTapmInvocation::test_tapm_timeout_uses_1200s
tests/runner/test_phase6_tapm_migration.py::TestRiskRegisterBuilderTapmInvocation::test_tapm_invocation_passes_tools
tests/runner/test_phase6_tapm_migration.py::TestRiskRegisterBuilderTapmInvocation::test_tapm_path_invoked_not_cli_prompt
tests/runner/test_phase6_tapm_migration.py::TestRiskRegisterBuilderTapmInvocation::test_tapm_timeout_uses_1200s
tests/runner/test_phase8_canonicalization.py::TestSpecLeanness::test_impact_no_component_keyword_scan
tests/runner/test_phase8_consistency_layer.py::TestDraftingSkillHygiene::test_under_size_limit[excellence-section-drafting.md]
tests/runner/test_phase8_consistency_layer.py::TestDraftingSkillHygiene::test_under_size_limit[impact-section-drafting.md]
tests/runner/test_phase8_consistency_layer.py::TestDraftingSkillHygiene::test_under_size_limit[implementation-section-drafting.md]
tests/runner/test_phase8_gate_content.py::TestCurrentArtifactState::test_excellence_no_assumed_claims
tests/runner/test_phase8_gate_content.py::TestCurrentArtifactState::test_excellence_overall_status_not_assumed
tests/runner/test_risk_register_builder_completion.py::TestRiskRegisterBuilderCompletion::test_completes_with_non_empty_risk_register
tests/runner/test_risk_register_builder_completion.py::TestRiskRegisterBuilderCompletion::test_ethics_assessment_preserved
tests/runner/test_risk_register_builder_completion.py::TestRiskRegisterBuilderCompletion::test_governance_matrix_preserved
tests/runner/test_risk_register_builder_completion.py::TestRiskRegisterBuilderCompletion::test_instrument_sections_preserved
tests/runner/test_risk_register_builder_completion.py::TestRiskRegisterBuilderCompletion::test_management_roles_preserved
tests/runner/test_risk_register_builder_completion.py::TestRiskRegisterBuilderConstraints::test_base_artifact_missing_fails
tests/runner/test_risk_register_builder_completion.py::TestRiskRegisterBuilderSchemaValidation::test_merged_artifact_has_all_required_fields
tests/runner/test_risk_register_builder_completion.py::TestRiskRegisterBuilderSchemaValidation::test_schema_id_mismatch_in_patch_fails
tests/runner/test_skill_applicability.py::TestOtherSkillsUnaffected::test_non_tier5_skills_always_invoked
tests/runner/test_skill_applicability.py::TestPhase2SkillSkipped::test_traceability_skip_does_not_block_other_skills
tests/runner/test_skill_applicability.py::TestPhase2SkillSkipped::test_traceability_skipped_in_phase2
tests/runner/test_skill_runtime.py::TestCanonicalInputBinding::test_caller_provided_inputs_override_disk
tests/runner/test_skill_runtime.py::TestCanonicalInputBinding::test_file_input_resolved_from_disk
tests/runner/test_skill_runtime.py::TestExcellenceOutputRobustness::test_valid_concise_excellence_json_writes_correctly
tests/runner/test_skill_runtime.py::TestMultiArtifactCanonicalPathKeys::test_basename_keyed_still_works
tests/runner/test_skill_runtime.py::TestMultiArtifactCanonicalPathKeys::test_canonical_path_keyed_response
tests/runner/test_skill_runtime.py::TestMultiArtifactCanonicalPathKeys::test_flat_shape_still_works
tests/runner/test_skill_runtime.py::TestMultiArtifactCanonicalPathKeys::test_stem_keyed_still_works
tests/runner/test_skill_runtime.py::TestMultiArtifactLogging::test_success_logs_an_ok_line
tests/runner/test_skill_runtime.py::TestMultiArtifactLogging::test_validation_failure_logs_a_fail_line
tests/runner/test_skill_runtime.py::TestMultiTargetWritesTo::test_flat_mixed_response_both_written
tests/runner/test_skill_runtime.py::TestMultiTargetWritesTo::test_missing_field_in_multi_field_target
tests/runner/test_skill_runtime.py::TestMultiTargetWritesTo::test_missing_first_target_fails
tests/runner/test_skill_runtime.py::TestMultiTargetWritesTo::test_missing_second_target_fails
tests/runner/test_skill_runtime.py::TestMultiTargetWritesTo::test_nested_keyed_multi_field_target
tests/runner/test_skill_runtime.py::TestOptionalReadsFrom::test_no_optional_field_means_empty_list
tests/runner/test_skill_runtime.py::TestOptionalReadsFrom::test_optional_present_is_resolved
tests/runner/test_skill_runtime.py::TestPhase8FileLevelArtifactWrite::test_impact_section_writes_to_exact_path
tests/runner/test_skill_runtime.py::TestPhase8FileLevelArtifactWrite::test_implementation_section_writes_to_exact_path
tests/runner/test_skill_runtime.py::TestRunSkillSchemaValidation::test_artifact_status_present_in_response
tests/runner/test_skill_runtime.py::TestRunSkillSchemaValidation::test_missing_run_id_in_response
tests/runner/test_skill_runtime.py::TestRunSkillSchemaValidation::test_wrong_run_id_in_response
tests/runner/test_skill_runtime.py::TestRunSkillSuccess::test_artifact_status_absent_in_written_artifact
tests/runner/test_skill_runtime.py::TestRunSkillSuccess::test_run_id_propagated_to_written_artifact
tests/runner/test_skill_runtime.py::TestRunSkillSuccess::test_schema_id_in_written_artifact
tests/runner/test_skill_runtime.py::TestRunSkillSuccess::test_success_with_valid_inputs
tests/runner/test_skill_runtime.py::TestTapmTransportFailureDiagnostics::test_cliprompt_diagnostic_has_no_tapm_tools
tests/runner/test_skill_runtime.py::TestTapmTransportFailureDiagnostics::test_tapm_diagnostic_includes_declared_inputs
tests/runner/test_skill_runtime.py::TestTapmTransportFailureDiagnostics::test_tapm_diagnostic_includes_prompt_sizes
tests/runner/test_skill_runtime.py::TestTapmTransportFailureDiagnostics::test_tapm_diagnostic_includes_tools_metadata
tests/runner/test_skill_runtime.py::TestTapmTransportFailureDiagnostics::test_tapm_timeout_writes_diagnostic
tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_empty_output_classified_correctly
tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_generic_transport_error_writes_diagnostic
tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_nonzero_exit_classified_correctly
tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_prompt_size_metadata_in_diagnostic
tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_rate_limit_classified_correctly
tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_timeout_failure_reason_includes_diag_path
tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_timeout_returns_failure_result
tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_timeout_with_node_id
tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_timeout_writes_prompt_files
tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_timeout_writes_stdout_stderr_files
tests/runner/test_skill_runtime.py::TestTransportFailureDiagnostics::test_timeout_writes_transport_diag_json
tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactMissingInputs::test_missing_base_artifact
tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactMissingInputs::test_missing_catalog_config
tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactResponseFormat::test_compact_valid_json_accepted
tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactResponseFormat::test_model_signaled_failure_intercepted
tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactResponseFormat::test_non_json_response_rejected
tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactSuccess::test_all_seven_fields_present_in_merged
tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactSuccess::test_base_fields_preserved
tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactSuccess::test_enrichment_merges_patch_into_base
tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactSuccess::test_gate_sees_nonnull_dec_fields
tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactValidation::test_artifact_status_in_patch_rejected
tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactValidation::test_merged_result_missing_required_field_rejected
tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactValidation::test_run_id_mismatch_rejected
tests/runner/test_skill_runtime_enrich.py::TestEnrichArtifactValidation::test_schema_id_mismatch_rejected
tests/runner/test_skill_runtime_tapm.py::TestRunSkillTapmMode::test_default_mode_is_cli_prompt
tests/runner/test_skill_runtime_tapm.py::TestRunSkillTapmMode::test_node_id_forwarded_to_tapm_prompt
tests/runner/test_skill_runtime_tapm.py::TestRunSkillTapmMode::test_node_id_none_works_for_tapm
tests/runner/test_skill_runtime_tapm.py::TestRunSkillTapmMode::test_tapm_mode_passes_tools
tests/runner/test_skill_runtime_tapm.py::TestRunSkillTapmMode::test_tapm_mode_schema_validation_failure
tests/runner/test_skill_runtime_tapm.py::TestRunSkillTapmMode::test_tapm_mode_skips_resolve_inputs
tests/runner/test_skill_runtime_tapm.py::TestRunSkillTapmMode::test_tapm_mode_skips_skill_prompt_assembly
tests/runner/test_skill_runtime_tapm.py::TestRunSkillTapmMode::test_tapm_mode_writes_artifact
tests/test_demo_architecture_seeds.py::TestAnonymity::test_the_branch_is_no_less_ok_than_before
tests/test_demo_candidate_blind_baseline.py::TestTheReportsNumbersAreTheArtifactsOwn::test_the_leakage_scan_file_count_is_re_derivable
tests/test_demo_change_scenarios.py::TestTheAdvisoryIsNotConsumed::test_the_input_fingerprint_is_the_same_with_an_advisory_present[n08a_excellence_drafting]
tests/test_demo_concept.py::TestAnonymity::test_the_brief_adds_no_new_leak_to_the_branch
tests/test_demo_consortium.py::TestAnonymity::test_the_leakage_scan_is_clean_over_tiers_3_to_5_and_the_vault
tests/test_demo_dev_graph_snapshot.py::TestAnonymity::test_the_new_artifacts_are_scanned_and_carry_no_new_leak
tests/test_demo_fictional_budget_override.py::TestThePhase7DispatchReachedTheGate::test_tier_5_content_carries_the_fictional_label
tests/test_demo_phase7_budget_gate.py::TestTheHardBlockIsIntact::test_no_phase_8_output_exists
tests/test_demo_report.py::TestTheBlindLaneFigures::test_the_scan_count_is_the_scans_own
tests/test_demo_sources.py::TestAnonymity::test_the_branch_is_no_less_ok_than_before
tests/test_msca_dn_declaration_drafts.py::TestDeterminismAndTheCommittedArtifacts::test_the_committed_artifacts_are_reproducible
tests/test_tier2b_biodiv_intake.py::TestStaleExtractedFinding::test_the_extracted_files_still_belong_to_another_call
tests/test_tier2b_biodiv_intake.py::TestTierBoundaries::test_phase_1_still_owns_tier_2b_extracted
tests/test_transport_openai_compatible.py::TestErrorHandling::test_400_raises_malformed_request
tests/test_transport_openai_compatible.py::TestErrorHandling::test_403_raises_auth_error
tests/test_transport_openai_compatible.py::TestErrorHandling::test_404_raises_model_not_found
tests/test_transport_openai_compatible.py::TestErrorHandling::test_429_raises_rate_limit_error
tests/test_transport_openai_compatible.py::TestErrorHandling::test_500_raises_provider_error
tests/test_transport_openai_compatible.py::TestErrorHandling::test_503_raises_provider_error
tests/test_transport_openai_compatible.py::TestErrorHandling::test_connection_error_raises_provider_error
tests/test_transport_openai_compatible.py::TestErrorHandling::test_timeout_raises_timeout_error
tests/test_transport_openai_compatible.py::TestResponseParsing::test_call_sends_post_and_returns_parsed
tests/test_transport_openai_compatible.py::TestResponseParsing::test_tool_calls_round_trip
tests/test_transport_presets.py::TestPresetRegistry::test_registry_count
```

## History: the 2026-10-21 report (superseded)

> # R9e — verification report
>
> > **Superseded 2026-10-21: R9e is reopened.** OD1 was revised to eu-north-1 (`aws-redeployment-od1-region-r1_2026-10-21`). The N/A closing below no longer holds; R9e is to be built and verified anew.
>
> | Field | Value |
> |---|---|
> | Verified by / on | agent (Claude) / 2026-10-21 |
> | Outcome | **N/A** — closed without work |
>
> ## Ticket checklist
>
> | Ticket criterion (from `plans/aws_redeployment_tickets.md`) | Status | Evidence |
> |---|---|---|
> | An EU Converse preset exists and is tested. | N/A | OD1 keeps us-east-1. |
> | No transport test fixes the region. | N/A | OD1 keeps us-east-1; the region-fixed tests match the chosen region. |
> | The runbook guard test passes on the edited runbook. | N/A | The AN12 runbook's region lines stand unchanged under OD1. |
> | Or: the ticket is closed N/A, with OD1 cited. | PASS | `docs/tier4_orchestration_state/decision_log/aws-redeployment-operator-decisions_2026-10-21.json`, OD1 (us-east-1, `us.` profiles); its consequence states that R9e closes N/A and reopens if OD1 is reopened. |
>
> ## Done conditions (handoff §7a)
>
> - [x] Every criterion above is PASS or N/A with a stated reason.
> - [x] Register v2 updated for: none — R9e touches no control.
> - [x] Worklog v2 entry: 2026-10-21T08:52:00Z.
> - [x] Operator confirmed in session on 2026-10-21 (closing R0 with OD1 = us-east-1).
>
> Note: R9 still exports `AWS_REGION` (F4); that is R9's work, not R9e's.
