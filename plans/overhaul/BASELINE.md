# Overhaul baseline — full pytest suite

Plan: `plans/overhaul_2026-11_plan.md` §2, Step 0(b). This is the red line no Step 4 ticket may cross:
targeted tests and the full suite must end **at or above** these numbers, judged **by node id** (no new
failure, no passing test turned red), not by totals alone.

> **Provisional: Linux run. The Windows run is still owed.** The plan asks for `py -3.10 -m pytest -q`
> on Windows. This run was made from a Linux VM on the operator's machine against the same working tree,
> because no Windows shell was available to the agent. Fill in §4 after the Windows run; the Windows
> numbers then become the binding baseline and this run stays as the cross-check.

## 1. Run

| Field | Value |
|-------|-------|
| Date | 2026-11-05 |
| Branch @ commit | `harness_overhaul` @ `09baceac` (`09baceac59cfc93f833b76f664e1e9d7817fd1da`) |
| Working tree | uncommitted: ticket 02 edit and three `.scratch/overhaul-2026-11/` notes only (no code) |
| Platform | Linux VM (Ubuntu, 2 CPUs), Python 3.10.12, pytest 9.2.0 |
| Dependencies | fresh venv from `requirements.txt` + `pytest` |
| Command | `python -m pytest -q -o addopts= -p no:cacheprovider` per batch of files |
| Collected | 9,367 tests in 267 files (`--collect-only`: 19 s) |

**How it was run.** The VM stops background processes and limits one command to 3 minutes, so the suite
ran as one pytest process per group of up to 6 files, with results collected as JUnit XML. Two files
(`tests/test_msca_dn_declaration_drafts.py`, `tests/test_msca_dn_import.py`) needed over 3 minutes on the
mounted folder (slow file I/O rebuilding module fixtures) and were run from a local copy of the tree; their
one failure was then re-run on the real checkout and fails there too. Consequences:

- **Wall time is not comparable to a single-process run.** Summed batch wall time ≈ 31 min; summed per-test
  time 1,492 s (≈ 25 min). Take wall time from the Windows run.
- Per-file process isolation can hide or create order-dependent results; none was observed, but the
  Windows single-process run is authoritative.

## 2. Result

| Passed | Failed | Errors | Skipped | Total |
|-------:|-------:|-------:|--------:|------:|
| 9,228 | 50 | 0 | 89 | 9,367 |

Of the 50 failures, **18 are caused by this Linux sandbox** (expected to pass on Windows) and
**32 look like real repository state** (expected to fail on Windows too). Neither is confirmed until the
Windows run.

## 3. Failures by cause

### Sandbox cannot delete files in the mounted folder (`PermissionError` on atomic-write cleanup) — 8 (sandbox)

- `tests/test_demo_change_scenarios.py::TestTheAdvisoryIsNotConsumed::test_rewriting_the_records_changes_no_byte`
- `tests/test_demo_change_scenarios.py::TestTheAdvisoryIsNotConsumed::test_the_input_fingerprint_is_the_same_with_an_advisory_present[n08a_excellence_drafting]`
- `tests/test_demo_change_scenarios.py::TestTheAdvisoryIsNotConsumed::test_the_input_fingerprint_is_the_same_with_an_advisory_present[n08b_impact_drafting]`
- `tests/test_demo_change_scenarios.py::TestTheAdvisoryIsNotConsumed::test_the_input_fingerprint_is_the_same_with_an_advisory_present[n08c_implementation_drafting]`
- `tests/test_demo_change_scenarios.py::TestTheAdvisoryIsNotConsumed::test_the_reuse_decision_is_the_same_with_an_advisory_present[n08a_excellence_drafting]`
- `tests/test_demo_change_scenarios.py::TestTheAdvisoryIsNotConsumed::test_the_reuse_decision_is_the_same_with_an_advisory_present[n08b_impact_drafting]`
- `tests/test_demo_change_scenarios.py::TestTheAdvisoryIsNotConsumed::test_the_reuse_decision_is_the_same_with_an_advisory_present[n08c_implementation_drafting]`
- `tests/test_demo_phase7_budget_gate.py::TestTheRequestConforms::test_it_recomposes_byte_equal`

### Windows `working_directory` judged against a POSIX repo root (`invocation_evidence` check) — 8 (sandbox)

- `tests/harness/test_blind_baseline.py::TestTheCommittedMscaDnBaseline::test_the_unmodified_control_still_freezes_at_74_6`
- `tests/harness/test_blind_baseline.py::TestTheCommittedMscaDnBaseline::test_the_freeze_records_the_measured_grounding_of_the_undeclared_run`
- `tests/harness/test_blind_baseline.py::TestTheCommittedMscaDnBaseline::test_the_rendered_freeze_states_the_grounding_prominently`
- `tests/harness/test_blind_baseline.py::TestTheCommittedMscaDnBaseline::test_the_three_renderers_print_the_same_derived_line`
- `tests/harness/test_blind_baseline.py::TestTheCommittedMscaDnBaseline::test_a_freeze_record_written_before_the_block_still_renders_grounding`
- `tests/harness/test_blind_baseline.py::TestTheCommittedMscaDnBaseline::test_a_freeze_record_whose_counts_cannot_be_measured_says_so`
- `tests/harness/test_blind_baseline.py::TestTheCommittedMscaDnBaseline::test_the_control_reproduces_the_committed_identity`
- `tests/harness/test_blind_baseline.py::TestTheCommittedMscaDnBaseline::test_the_committed_report_passes_every_check_by_name`

### `ORCHESTRATOR_CLAUDE_CLI_PATH` in the environment is a Windows path — 1 (sandbox)

- `tests/runner/test_claude_transport_treekill.py::TestStdinWriteDeadline::test_timeout_fires_when_child_never_reads_stdin`

### `httpx` not installed (not listed in `requirements.txt`) — 1 (sandbox)

- `tests/test_bedrock_env_readiness.py::TestBuildOpenaiBackend::test_api_key_read_from_env_at_build_time`

### Leakage scan: 9 new instance-one leaks over 445 files, and tests pinned to the scan's output — 9 (repo state)

- `tests/runner/test_leakage_scan.py::TestTheTreeScan::test_no_new_leak`
- `tests/runner/test_leakage_scan.py::TestTheTreeScan::test_the_branch_is_not_clean_and_says_so`
- `tests/test_demo_architecture_seeds.py::TestAnonymity::test_the_branch_is_no_less_ok_than_before`
- `tests/test_demo_candidate_blind_baseline.py::TestTheReportsNumbersAreTheArtifactsOwn::test_the_leakage_scan_file_count_is_re_derivable`
- `tests/test_demo_concept.py::TestAnonymity::test_the_brief_adds_no_new_leak_to_the_branch`
- `tests/test_demo_consortium.py::TestAnonymity::test_the_leakage_scan_is_clean_over_tiers_3_to_5_and_the_vault`
- `tests/test_demo_dev_graph_snapshot.py::TestAnonymity::test_the_new_artifacts_are_scanned_and_carry_no_new_leak`
- `tests/test_demo_report.py::TestTheBlindLaneFigures::test_the_scan_count_is_the_scans_own`
- `tests/test_demo_sources.py::TestAnonymity::test_the_branch_is_no_less_ok_than_before`

### Skill-spec size and leanness limits (drafting skill `.md` files over their caps) — 7 (repo state)

- `tests/runner/test_drafting_skill_hygiene.py::TestSizeLimits::test_under_size_limit[excellence-section-drafting.md]`
- `tests/runner/test_drafting_skill_hygiene.py::TestSizeLimits::test_under_size_limit[impact-section-drafting.md]`
- `tests/runner/test_drafting_skill_hygiene.py::TestSizeLimits::test_under_size_limit[implementation-section-drafting.md]`
- `tests/runner/test_phase8_canonicalization.py::TestSpecLeanness::test_impact_no_component_keyword_scan`
- `tests/runner/test_phase8_consistency_layer.py::TestDraftingSkillHygiene::test_under_size_limit[excellence-section-drafting.md]`
- `tests/runner/test_phase8_consistency_layer.py::TestDraftingSkillHygiene::test_under_size_limit[impact-section-drafting.md]`
- `tests/runner/test_phase8_consistency_layer.py::TestDraftingSkillHygiene::test_under_size_limit[implementation-section-drafting.md]`

### Phase 6/8 artifact state and the dev-graph demo (assumed claims, role ids, legal names, Phase 8 outputs present, fictional-label read) — 6 (repo state)

- `tests/runner/test_gate10d_consistency_fix.py::TestImplementationPartnerLegalNames::test_partners_json_has_correct_legal_names`
- `tests/runner/test_phase6_field_production.py::TestComplianceProfileDerivativeLabeling::test_current_artifact_wp9_cites_tier2b_for_ai_on_demand`
- `tests/runner/test_phase8_gate_content.py::TestCurrentArtifactState::test_excellence_no_assumed_claims`
- `tests/runner/test_phase8_gate_content.py::TestCurrentArtifactState::test_excellence_overall_status_not_assumed`
- `tests/test_demo_fictional_budget_override.py::TestThePhase7DispatchReachedTheGate::test_tier_5_content_carries_the_fictional_label`
- `tests/test_demo_phase7_budget_gate.py::TestTheHardBlockIsIntact::test_no_phase_8_output_exists`

### Tier 2B extracted state vs the BIODIV intake finding — 2 (repo state)

- `tests/test_tier2b_biodiv_intake.py::TestStaleExtractedFinding::test_the_extracted_files_still_belong_to_another_call`
- `tests/test_tier2b_biodiv_intake.py::TestTierBoundaries::test_phase_1_still_owns_tier_2b_extracted`

### Agent runtime skill loop (caller context, skill applicability) — 4 (repo state)

- `tests/runner/test_caller_context.py::TestFailClosedAbsentSources::test_run_agent_passes_none_when_sources_absent`
- `tests/runner/test_skill_applicability.py::TestPhase2SkillSkipped::test_traceability_skipped_in_phase2`
- `tests/runner/test_skill_applicability.py::TestPhase2SkillSkipped::test_traceability_skip_does_not_block_other_skills`
- `tests/runner/test_skill_applicability.py::TestOtherSkillsUnaffected::test_non_tier5_skills_always_invoked`

### Cross-run checkpoint (DoD-1e) — 3 (repo state)

- `tests/runner/test_dod1e_checkpoint_close.py::test_real_checkpoint_published`
- `tests/runner/test_dod1e_checkpoint_close.py::test_real_checkpoint_records_gate09_quad_verbatim`
- `tests/runner/test_dod1e_checkpoint_close.py::test_real_checkpoint_predicate_passes_directly`

### MSCA-DN declaration drafts: committed artifacts not reproducible (also fails on the real checkout) — 1 (repo state)

- `tests/test_msca_dn_declaration_drafts.py::TestDeterminismAndTheCommittedArtifacts::test_the_committed_artifacts_are_reproducible`

Notes for the overhaul:

- **DN path.** The 8 `test_blind_baseline.py` failures sit in blind-assessment code (admission rule 5).
  They fail here only because a Windows path is checked against a Linux repo root; confirm they pass on
  Windows before any rule-5 ticket starts, or that ticket cannot show "at or above baseline".
- **`httpx`.** `test_bedrock_env_readiness` imports it, but `requirements.txt` does not list it.
- **Side effect of this run.** Tests that rewrite records left 17 `*.tmp` files in `docs/` because the
  sandbox blocked their cleanup; they were deleted afterwards. No tracked file changed.

## 3b. Skipped (89), by reason

| Count | Reason (truncated) |
|------:|--------------------|
| 33 | Fixture benchmark data not found |
| 17 | EXCLUDED (not a pass) |
| 12 | MSCA graph.config.yaml not present |
| 7 | MSCA methodology vault not present |
| 4 | reference graph.config.yaml not present |
| 4 | open-Q #4 decision entry not in this checkout (decision log emptied by the 2026- |
| 3 | Real manifest not available |
| 2 | Real skill catalog not available |
| 1 | durable gate_09 result belongs to run 'import uuid; print(uuid.uuid4())', not th |
| 1 | live β fixtures for excellence not captured yet |
| 1 | live β fixtures for impact not captured yet |
| 1 | live β fixtures for implementation not captured yet |
| 1 | live α budget fixture not captured yet |
| 1 | Tier 2A states no maximum work package count for RIA |
| 1 | Windows-specific reserved name test |

## 4. Windows run (to fill in)

From a clean tree at the commit above (or note the new one):

```powershell
py -3.10 -m pytest -q -rfEs | Tee-Object -FilePath $HOME\baseline-windows.txt
```

| Field | Value |
|-------|-------|
| Commit | |
| Python / pytest | |
| Passed / Failed / Errors / Skipped | |
| Wall time | |
| Failures not listed in §3 | |
| §3 failures that pass on Windows | |
