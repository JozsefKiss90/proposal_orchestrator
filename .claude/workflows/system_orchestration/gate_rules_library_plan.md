# Gate Rules Library — Implementation Plan

**Status:** Plan only. No implementation has been performed.
**Applies to:** `system_orchestration` package v1.1
**Approach:** Rules library (Approach A) as bridge to inline manifest predicates (Approach B)
**Scope:** All 12 quality gates across 8 phases plus entry gate

---

## 1. Problem Statement

The compiled manifest (`manifest.compile.yaml`) and phase source files store gate conditions as prose strings. This is appropriate for governance and human review but is not executable by a DAG runner. The runner needs a deterministic way to evaluate whether a gate has passed or failed.

The two long-term approaches are:

- **Approach A (this plan):** A side-car rules library that maps each `gate_id` to a list of executable predicates. The manifest is untouched. The runner loads the library at evaluation time and resolves predicates against the live repository state.
- **Approach B (future):** The manifest itself grows machine-readable predicate entries alongside prose conditions. The library becomes the implementation registry; the manifest is the source of predicate composition.

This plan implements Approach A and is designed to make Approach B a straightforward migration.

---

## 2. Library File

**Path:** `.claude/workflows/system_orchestration/gate_rules_library.yaml`

This file is co-located with the rest of the system_orchestration package. It is a source file, not a compiled artifact. It must not be used as the DAG-runner entry point; only `manifest.compile.yaml` has that role.

**Top-level structure:**

```yaml
library_version: "1.0"
source_package: .claude/workflows/system_orchestration/
constitutional_authority: CLAUDE.md
gate_rules:
  - gate_id: <gate_id_from_manifest>
    evaluated_at: <node_id and entry/exit>
    predicates:
      - predicate_id: <unique_within_gate>
        type: <predicate_type>
        function: <function_name>
        args: { ... }
        fail_message: "<human-readable failure description>"
        prose_condition: "<the exact prose string from the manifest this predicate implements>"
```

The `prose_condition` field is mandatory. It creates an explicit link between each executable predicate and the governance prose it implements. This field is the migration bridge: when Approach B is adopted, the manifest condition entry gains a `predicate_refs` list pointing to these predicate IDs.

---

## 3. Predicate Taxonomy

All predicates belong to one of eight types. The type determines how the runner evaluates the predicate and whether agent invocation is required.

| Type | Description | Evaluation |
|------|-------------|------------|
| `file` | File or directory existence and non-emptiness | Pure filesystem |
| `schema` | JSON parseability, field presence, conformance to a known schema | Parse and inspect |
| `source_ref` | All items in a JSON array carry a source reference field | Parse and traverse |
| `coverage` | Every item in artifact A has a corresponding entry in artifact B | Cross-artifact join |
| `cycle` | A dependency graph represented in an artifact is acyclic | Graph algorithm |
| `timeline` | Task or milestone scheduling is consistent with duration and dependency constraints | Arithmetic on parsed data |
| `gate_pass` | A prior gate's recorded pass result exists in Tier 4 | File lookup |
| `semantic` | Requires judgment: coherence, conflict absence, constitutional compliance | Agent-evaluated |

**Evaluation order within a gate:**

The runner must evaluate types in this order for each gate:

1. `file` — fail fast on missing artifacts
2. `gate_pass` — confirm upstream gates have passed (enforces DAG ordering)
3. `schema` — confirm artifacts are structurally usable
4. `source_ref` — confirm traceability requirements
5. `coverage` — cross-artifact consistency
6. `cycle` — structural correctness of graphs
7. `timeline` — scheduling consistency
8. `semantic` — judgment-requiring checks (invoked only if all preceding types pass)

This ordering is mandatory. Semantic predicates are expensive (require agent invocation) and often depend on the same artifacts checked by deterministic predicates. A gate that fails a `file` check must not invoke an agent for semantic evaluation.

---

## 4. Predicate Function Catalogue

These are the predicate functions required across all gates. Each function defines a contract: inputs, return type, and failure semantics. Implementation is not part of this plan.

### 4.1 File Predicates

| Function | Signature | Pass condition |
|----------|-----------|----------------|
| `exists(path)` | `path: str` | The path exists (file or directory) |
| `non_empty(path)` | `path: str` | File exists and byte size > 0 |
| `non_empty_json(path)` | `path: str` | File is valid JSON and not `{}`, `[]`, or `null` |
| `dir_non_empty(path)` | `path: str` | Directory exists and contains at least one non-empty file |
| `artifact_owned_by_run(path, run_id)` | `path: str, run_id: str` | The artifact at `path` contains a top-level `run_id` field matching the current run. Fails if field is absent, null, or mismatched. |

**`dir_non_empty` is a coarse preliminary check only.** It is appropriate for externally-supplied source directories (`work_programmes/`, `call_extracts/`, `received/`, `validation/`) where no single canonical file can be mandated. For phase output directories, predicates in §5 must target the specific canonical artifact file defined in §7, not the directory. A non-empty directory may contain stale files from prior runs, placeholder files, or files from a different call. `dir_non_empty` alone does not satisfy a gate-critical artifact check. For all canonical phase output artifacts, `dir_non_empty` is replaced by `non_empty_json(canonical_file_path)` plus `artifact_owned_by_run(canonical_file_path, run_id)` in §5.

### 4.2 Schema Predicates

| Function | Signature | Pass condition |
|----------|-----------|----------------|
| `json_field_present(path, field)` | `path: str, field: str` | JSON file contains the named top-level field with a non-null value |
| `json_fields_present(path, fields)` | `path: str, fields: list[str]` | All named fields are present and non-null |
| `instrument_type_matches_schema(call_path, schema_path)` | `call_path: str, schema_path: str` | The `instrument_type` field in `call_path` matches at least one entry in the schema registry at `schema_path` |
| `interface_contract_conforms(response_path, contract_path)` | `response_path: str, contract_path: str` | All files in `response_path` conform to the JSON schema defined in `contract_path` |

### 4.3 Source Reference Predicates

| Function | Signature | Pass condition |
|----------|-----------|----------------|
| `source_refs_present(path)` | `path: str` | Every item in the JSON array or object at `path` contains a non-empty `source_ref` or `source_section` field |
| `all_mappings_have_source_refs(path)` | `path: str` | Every mapping entry in the file (e.g., topic_mapping.json) carries both a Tier 2B source reference and a Tier 3 project evidence source |

### 4.4 Coverage Predicates

| Function | Signature | Pass condition |
|----------|-----------|----------------|
| `wp_budget_coverage_match(wp_path, budget_path)` | `wp_path: str, budget_path: str` | Every WP identifier in the Phase 3 output exists as a budget entry in the received budget response |
| `partner_budget_coverage_match(partners_path, budget_path)` | `partners_path: str, budget_path: str` | Every partner identifier in Tier 3 `partners.json` has a corresponding effort or cost allocation in the budget response |
| `all_impacts_mapped(impact_path, expected_impacts_path)` | `impact_path: str, expected_impacts_path: str` | Every expected impact identifier in Tier 2B `expected_impacts.json` appears in the impact architecture with at least one mapped project output |
| `kpis_traceable_to_wps(impact_path, wp_path)` | `impact_path: str, wp_path: str` | Every KPI defined in the impact architecture references a named deliverable from the Phase 3 WP output |
| `all_sections_drafted(sections_path, schema_path)` | `sections_path: str, schema_path: str` | Every section identifier required by the active instrument schema in `section_schema_registry.json` has a corresponding artifact in `proposal_sections/` |
| `all_partners_in_tier3(wp_path, partners_path)` | `wp_path: str, partners_path: str` | Every partner assigned as lead or contributor in the WP structure exists in Tier 3 `partners.json` |
| `all_management_roles_in_tier3(impl_path, partners_path)` | `impl_path: str, partners_path: str` | Every management role named in the implementation architecture references a partner present in Tier 3 `partners.json` |
| `all_tasks_have_months(gantt_path, wp_path)` | `gantt_path: str, wp_path: str` | Every task identifier present in the Phase 3 WP output also appears in the Gantt output with non-null start and end months |
| `instrument_sections_addressed(impl_path, schema_path)` | `impl_path: str, schema_path: str` | Every mandatory implementation section listed in the section schema registry for the active instrument is present in the Phase 6 output |
| `all_sections_have_traceability_footer(sections_path)` | `sections_path: str` | Every section artifact in `proposal_sections/` contains a non-empty traceability footer field |
| `all_wps_have_deliverable_and_lead(wp_path)` | `wp_path: str` | Every WP in the Phase 3 output has at least one deliverable and a non-empty lead partner field |

### 4.5 Cycle Predicates

| Function | Signature | Pass condition |
|----------|-----------|----------------|
| `no_dependency_cycles(wp_path)` | `wp_path: str` | The dependency map in the Phase 3 output is a directed acyclic graph; no cycle is detectable |

### 4.6 Timeline Predicates

| Function | Signature | Pass condition |
|----------|-----------|----------------|
| `timeline_within_duration(gantt_path, call_path)` | `gantt_path: str, call_path: str` | All task end months in the Gantt output are ≤ the project duration specified in `selected_call.json` |
| `all_milestones_have_criteria(gantt_path)` | `gantt_path: str` | Every milestone in the Phase 4 output has a non-empty `verifiable_criterion` field and a non-null `due_month` |
| `wp_count_within_limit(wp_path, schema_path)` | `wp_path: str, schema_path: str` | The count of WPs in the Phase 3 output does not exceed the maximum WP count specified in the section schema registry for the active instrument |
| `critical_path_present(gantt_path)` | `gantt_path: str` | The Phase 4 output contains a non-empty `critical_path` field or section |

### 4.7 Gate-Pass Predicates

| Function | Signature | Pass condition |
|----------|-----------|----------------|
| `gate_pass_recorded(gate_id, run_id, tier4_root)` | `gate_id: str, run_id: str, tier4_root: str` | A gate result file for `gate_id` exists at the canonical result path (§6.3) with `status: pass`, a `run_id` field matching the current run, and an `input_fingerprint` field present. The gate result's `evaluated_at` timestamp must not predate the modification time of any artifact listed in the upstream phase's `required_inputs`. |

This predicate enforces DAG ordering independently of the manifest edge registry. It is safe for rerunnable systems only when all three of the following hold:

**Run identity match.** The `run_id` in the gate result must equal the `run_id` established at DAG-runner startup. A result with a matching `gate_id` but a different `run_id` is a stale artifact from a prior run and must not satisfy the predicate. The predicate must not fall back to the most recent result file regardless of run identity.

**Input fingerprint match.** The `input_fingerprint` in the gate result must equal the hash of the combined content of all `required_inputs` for the upstream phase at the time the current run read those inputs. If any required input has been modified since the gate result was written, the fingerprint will not match and the predicate fails, triggering re-evaluation of the upstream gate before the downstream phase can proceed.

**Freshness bound.** The `evaluated_at` timestamp in the gate result must not predate the `mtime` of any artifact in the upstream phase's `required_inputs`. This is a secondary safety check: a fingerprint collision (two different artifact contents producing the same hash) would still be caught by the timestamp bound if any input changed after the gate was evaluated.

These three requirements together mean that a cached `pass` result is reused only when nothing that could have invalidated it has changed. Without run-scope semantics, stale-state contamination can satisfy gate ordering while the upstream phase's artifacts are in a different state than when the gate passed.

### 4.8 Canonical Field Predicates

These are schema-adjacent predicates that check for the presence and validity of named structured fields within a specific canonical artifact file. **All predicates in this section take a canonical file path, not a directory path.** The canonical file for each phase output is defined in §7. No predicate in this section may scan a directory for any matching file; it must read the single canonical file and inspect it.

The former `field_present_and_non_empty(dir_path, field_name)` pattern is removed. Different files in the same directory may contain competing structures, duplicate field names, or partial in-progress content written before gate evaluation. Resolving an ambiguous directory scan to a gate-relevant field is not safe. All canonical field checks must resolve to a named file path.

| Function | Signature | Pass condition |
|----------|-----------|----------------|
| `risk_register_populated(path)` | `path: str` (canonical file) | `path` is a valid JSON file; top-level `risk_register` array is non-empty; each entry has non-null `likelihood`, `impact`, and `mitigation` fields |
| `ethics_assessment_explicit(path)` | `path: str` (canonical file) | `path` is a valid JSON file; top-level `ethics_assessment` field is present, non-null, not an empty string, and not equal to a placeholder sentinel value |
| `governance_matrix_present(path)` | `path: str` (canonical file) | `path` is a valid JSON file; top-level `governance_matrix` field is present and contains at least one non-empty entry |
| `no_blocking_inconsistencies(path)` | `path: str` (canonical file) | `path` is a valid JSON file; the `blocking_inconsistencies` array either is absent or contains no entry with `resolution: unresolved` |
| `budget_gate_confirmation_present(path)` | `path: str` (canonical file) | `path` is a valid JSON file; top-level `gate_pass_declaration` field equals `pass` |
| `findings_categorised_by_severity(path)` | `path: str` (canonical file) | `path` is a valid JSON file; all entries in the `findings` array have a non-null `severity` field drawn from `{critical, major, minor}` |
| `revision_action_list_present(path)` | `path: str` (canonical file) | `path` is a valid JSON file; top-level `revision_actions` array is non-empty |
| `all_critical_revisions_resolved(path)` | `path: str` (canonical file) | `path` is a valid JSON file; no entry in the `revision_actions` array has `severity: critical` and `status: unresolved` without a non-empty `reason` field |
| `checkpoint_published(path)` | `path: str` (canonical file) | The file at `path` exists, is valid JSON, and contains `status: published` |

### 4.9 Semantic Predicates

Semantic predicates cannot be evaluated by deterministic file inspection alone. They require an agent to read artifacts and apply judgment. They produce a structured result rather than a binary file check.

| Function | Description | Agent | Constitutional rule |
|----------|-------------|-------|---------------------|
| `no_unresolved_scope_conflicts(phase2_path, scope_path)` | No scope conflict between the Phase 2 refined concept output and Tier 2B scope requirements remains unresolved | `concept_refiner` | CLAUDE.md §7 Phase 2 gate |
| `no_cross_tier_contradictions(sections_path, tier3_path)` | No factual claim in Tier 5 proposal sections contradicts confirmed Tier 3 project facts | `constitutional_compliance_check` skill | CLAUDE.md §11.4, §13.3 |
| `no_unsupported_tier5_claims(sections_path, tier3_path)` | No project fact asserted in Tier 5 (partner name, capability, role, objective, prior experience, budget figure, team size, equipment) is absent from Tier 3 | `constitutional_compliance_check` skill | CLAUDE.md §13.3 |
| `no_budget_gate_contradiction(sections_path, phase7_path)` | No Tier 5 section references a specific budget figure, effort allocation, or resource commitment that is not present in the validated budget response | `constitutional_compliance_check` skill | CLAUDE.md §8.4, §13.4 |
| `no_higher_tier_contradiction(sections_path, tier2a_path, tier2b_path)` | No Tier 5 section asserts a call constraint, scope boundary, expected outcome, or expected impact not traceable to Tier 2A or Tier 2B source documents | `constitutional_compliance_check` skill | CLAUDE.md §13.2, §11.3 |
| `no_forbidden_schema_authority(sections_path)` | No Tier 5 section is structured according to a Grant Agreement Annex template rather than the active application form (Tier 2A) | `constitutional_compliance_check` skill | CLAUDE.md §13.1 |
| `no_gap_masked_as_confirmed(sections_path)` | No Tier 5 section presents content with `Confirmed` validation status where the underlying source is `Unresolved` or `Assumed` in the relevant Tier 4 phase output | `constitutional_compliance_check` skill | CLAUDE.md §12.2 |

**Rationale for splitting `no_constitutional_violations`:** A single catch-all constitutional judgment function would replicate constitutional authority in an opaque execution layer, violating CLAUDE.md §10.6 (agents must not substitute their prior knowledge for source documents) and §13.6 (an execution aid must not become a de facto constitutional authority). Each named predicate above is constrained to a specific, listed constitutional rule. The runner records the violated rule ID, not a narrative finding. The agent must return evidence paths, not conclusions.

**Semantic predicate result schema:**

```yaml
predicate_id: <id>
function: no_unsupported_tier5_claims
status: pass | fail
agent: constitutional_compliance_check
constitutional_rule: "CLAUDE.md §13.3"
artifacts_inspected:
  - <path>
findings:
  - claim: "<the asserted fact>"
    violated_rule: "CLAUDE.md §13.3"
    evidence_path: "<path to the Tier 5 section containing the claim>"
    tier3_lookup: "<path checked in Tier 3; absent or contradicted>"
    severity: critical | major
fail_message: "<summary if status is fail>"
```

Each finding must include `violated_rule` as a named constitutional section and `evidence_path` pointing to the specific artifact. Narrative-only findings without a rule ID and evidence path must be rejected by the runner and treated as a predicate evaluation error, not a pass.

A semantic predicate fails if `status: fail`. The runner must include the full finding list in the gate failure report.

---

## 5. Gate-by-Gate Predicate Mapping

For each gate, the predicates are listed in evaluation order. `prose_condition` cross-references the exact string in the manifest. Predicate IDs use the format `g<gate_number>_p<sequence>` where gate_number follows the gate sequence (01 = gate_01_source_integrity, 02 = phase_01_gate, etc.).

---

### gate_01_source_integrity — Phase 1 Entry

| ID | Type | Function | Args | prose_condition |
|----|------|----------|------|-----------------|
| g01_p01 | file | `non_empty_json` | `path: docs/tier3_project_instantiation/call_binding/selected_call.json` | selected_call.json must be present and non-empty |
| g01_p02 | schema | `json_fields_present` | `path: …/selected_call.json, fields: [call_id, topic_code, instrument_type, work_programme_area]` | Call identifier, topic code, and instrument type must be present |
| g01_p03 | file | `dir_non_empty` | `path: docs/tier2b_topic_and_call_sources/work_programmes/` | At least one work programme document must be present |
| g01_p04 | file | `dir_non_empty` | `path: docs/tier2b_topic_and_call_sources/call_extracts/` | At least one call extract matching the topic code must be present |
| g01_p05 | file | `dir_non_empty` | `path: docs/tier2a_instrument_schemas/application_forms/` | An application form template for the resolved instrument type must be present |
| g01_p06 | file | `dir_non_empty` | `path: docs/tier2a_instrument_schemas/evaluation_forms/` | An evaluation form for the resolved instrument type must be present |

---

### phase_01_gate — Phase 1 Exit

| ID | Type | Function | Args | prose_condition |
|----|------|----------|------|-----------------|
| g02_p01 | file | `non_empty_json` | `path: docs/tier2b_topic_and_call_sources/extracted/call_constraints.json` | All six Tier 2B extracted JSON files are non-empty |
| g02_p02 | file | `non_empty_json` | `path: …/extracted/expected_outcomes.json` | All six Tier 2B extracted JSON files are non-empty |
| g02_p03 | file | `non_empty_json` | `path: …/extracted/expected_impacts.json` | All six Tier 2B extracted JSON files are non-empty |
| g02_p04 | file | `non_empty_json` | `path: …/extracted/scope_requirements.json` | All six Tier 2B extracted JSON files are non-empty |
| g02_p05 | file | `non_empty_json` | `path: …/extracted/eligibility_conditions.json` | All six Tier 2B extracted JSON files are non-empty |
| g02_p06 | file | `non_empty_json` | `path: …/extracted/evaluation_priority_weights.json` | All six Tier 2B extracted JSON files are non-empty |
| g02_p07 | source_ref | `source_refs_present` | `path: …/extracted/call_constraints.json` | All six Tier 2B extracted JSON files have source section references |
| g02_p08 | source_ref | `source_refs_present` | `path: …/extracted/expected_outcomes.json` | All six Tier 2B extracted JSON files have source section references |
| g02_p09 | source_ref | `source_refs_present` | `path: …/extracted/expected_impacts.json` | All six Tier 2B extracted JSON files have source section references |
| g02_p10 | source_ref | `source_refs_present` | `path: …/extracted/scope_requirements.json` | All six Tier 2B extracted JSON files have source section references |
| g02_p11 | source_ref | `source_refs_present` | `path: …/extracted/eligibility_conditions.json` | All six Tier 2B extracted JSON files have source section references |
| g02_p12 | source_ref | `source_refs_present` | `path: …/extracted/evaluation_priority_weights.json` | All six Tier 2B extracted JSON files have source section references |
| g02_p13 | schema | `instrument_type_matches_schema` | `call_path: …/selected_call.json, schema_path: …/extracted/section_schema_registry.json` | Instrument type resolved to a Tier 2A application form and evaluation form |
| g02_p14 | file | `non_empty_json` | `path: docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | Instrument type resolved to a Tier 2A application form and evaluation form |
| g02_p15 | file | `non_empty_json` | `path: docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json` | Instrument type resolved to a Tier 2A evaluation form |
| g02_p16 | file | `non_empty_json` | `path: docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/call_analysis_summary.json` | Evaluation matrix and compliance checklist written to Tier 4 phase output |
| g02_p17 | file | `artifact_owned_by_run` | `path: …/phase1_call_analysis/call_analysis_summary.json, run_id: <current_run_id>` | Evaluation matrix and compliance checklist written to Tier 4 phase output |

---

### phase_02_gate — Phase 2 Exit

| ID | Type | Function | Args | prose_condition |
|----|------|----------|------|-----------------|
| g03_p01 | gate_pass | `gate_pass_recorded` | `gate_id: phase_01_gate, run_id: <current_run_id>` | Phase 1 gate must have passed |
| g03_p02 | file | `non_empty_json` | `path: docs/tier3_project_instantiation/call_binding/topic_mapping.json` | topic_mapping.json is non-empty |
| g03_p03 | source_ref | `all_mappings_have_source_refs` | `path: …/topic_mapping.json` | All mappings carry source references |
| g03_p04 | file | `non_empty_json` | `path: docs/tier3_project_instantiation/call_binding/compliance_profile.json` | compliance_profile.json is non-empty |
| g03_p05 | file | `non_empty_json` | `path: docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` | Phase 2 summary written to Tier 4 |
| g03_p07 | file | `artifact_owned_by_run` | `path: …/phase2_concept_refinement/concept_refinement_summary.json, run_id: <current_run_id>` | Phase 2 summary written to Tier 4 |
| g03_p06 | semantic | `no_unresolved_scope_conflicts` | `phase2_path: …/phase2_concept_refinement/, scope_path: …/extracted/scope_requirements.json` | No unresolved scope conflicts between concept and Tier 2B |

---

### phase_03_gate — Phase 3 Exit

| ID | Type | Function | Args | prose_condition |
|----|------|----------|------|-----------------|
| g04_p01 | gate_pass | `gate_pass_recorded` | `gate_id: phase_02_gate, run_id: <current_run_id>` | Phase 2 gate must have passed |
| g04_p02 | file | `non_empty_json` | `path: docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | Full WP structure written to Tier 4 |
| g04_p02b | file | `artifact_owned_by_run` | `path: …/phase3_wp_design/wp_structure.json, run_id: <current_run_id>` | Full WP structure written to Tier 4 |
| g04_p03 | schema | `json_field_present` | `path: …/phase3_wp_design/wp_structure.json, field: dependency_map` | Dependency map written to Tier 4 |
| g04_p04 | coverage | `all_wps_have_deliverable_and_lead` | `wp_path: …/phase3_wp_design/` | All WPs have at least one deliverable and a responsible lead |
| g04_p05 | timeline | `wp_count_within_limit` | `wp_path: …/phase3_wp_design/, schema_path: …/extracted/section_schema_registry.json` | WP count compliant with Tier 2A instrument constraints |
| g04_p06 | cycle | `no_dependency_cycles` | `wp_path: …/phase3_wp_design/` | No dependency cycles in the dependency map |
| g04_p07 | coverage | `all_partners_in_tier3` | `wp_path: …/phase3_wp_design/, partners_path: docs/tier3_project_instantiation/consortium/partners.json` | All assigned partners present in Tier 3 consortium data |

---

### phase_04_gate — Phase 4 Exit

| ID | Type | Function | Args | prose_condition |
|----|------|----------|------|-----------------|
| g05_p01 | gate_pass | `gate_pass_recorded` | `gate_id: phase_03_gate, run_id: <current_run_id>` | Phase 3 gate must have passed |
| g05_p02 | file | `non_empty_json` | `path: docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gantt.json` | Gantt structure and milestone table written to Tier 4 |
| g05_p02b | file | `artifact_owned_by_run` | `path: …/phase4_gantt_milestones/gantt.json, run_id: <current_run_id>` | Gantt structure and milestone table written to Tier 4 |
| g05_p03 | coverage | `all_tasks_have_months` | `gantt_path: …/phase4_gantt_milestones/gantt.json, wp_path: …/phase3_wp_design/wp_structure.json` | All tasks assigned to months within project duration |
| g05_p04 | timeline | `timeline_within_duration` | `gantt_path: …/phase4_gantt_milestones/gantt.json, call_path: …/selected_call.json` | All tasks assigned to months within project duration |
| g05_p05 | timeline | `all_milestones_have_criteria` | `gantt_path: …/phase4_gantt_milestones/gantt.json` | All milestones have verifiable criteria and due months |
| g05_p06 | timeline | `critical_path_present` | `gantt_path: …/phase4_gantt_milestones/gantt.json` | Critical path identified and consistent with dependency map |
| g05_p07 | file | `non_empty_json` | `path: docs/tier3_project_instantiation/architecture_inputs/milestones_seed.json` | milestones_seed.json populated in Tier 3 |

---

### phase_05_gate — Phase 5 Exit

| ID | Type | Function | Args | prose_condition |
|----|------|----------|------|-----------------|
| g06_p01 | gate_pass | `gate_pass_recorded` | `gate_id: phase_02_gate, run_id: <current_run_id>` | Phase 2 gate must have passed |
| g06_p02 | gate_pass | `gate_pass_recorded` | `gate_id: phase_03_gate, run_id: <current_run_id>` | Phase 3 gate must have passed |
| g06_p03 | file | `non_empty_json` | `path: docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | Full impact architecture written to Tier 4 |
| g06_p03b | file | `artifact_owned_by_run` | `path: …/phase5_impact_architecture/impact_architecture.json, run_id: <current_run_id>` | Full impact architecture written to Tier 4 |
| g06_p04 | coverage | `all_impacts_mapped` | `impact_path: …/phase5_impact_architecture/impact_architecture.json, expected_impacts_path: …/extracted/expected_impacts.json` | All call expected impacts have at least one mapped project output |
| g06_p05 | coverage | `kpis_traceable_to_wps` | `impact_path: …/phase5_impact_architecture/impact_architecture.json, wp_path: …/phase3_wp_design/wp_structure.json` | KPI set is defined and traceable to WP deliverables |
| g06_p06 | schema | `json_field_present` | `path: …/phase5_impact_architecture/impact_architecture.json, field: dissemination_plan` | Dissemination and exploitation logic is defined |
| g06_p07 | schema | `json_field_present` | `path: …/phase5_impact_architecture/impact_architecture.json, field: exploitation_plan` | Dissemination and exploitation logic is defined |
| g06_p08 | schema | `json_field_present` | `path: …/phase5_impact_architecture/impact_architecture.json, field: sustainability_mechanism` | Sustainability mechanism is defined |

---

### phase_06_gate — Phase 6 Exit

| ID | Type | Function | Args | prose_condition |
|----|------|----------|------|-----------------|
| g07_p01 | gate_pass | `gate_pass_recorded` | `gate_id: phase_03_gate, run_id: <current_run_id>` | Phase 3 gate must have passed |
| g07_p02 | gate_pass | `gate_pass_recorded` | `gate_id: phase_04_gate, run_id: <current_run_id>` | Phase 4 gate must have passed |
| g07_p03 | gate_pass | `gate_pass_recorded` | `gate_id: phase_05_gate, run_id: <current_run_id>` | Phase 5 gate must have passed |
| g07_p04 | file | `non_empty_json` | `path: docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json` | Implementation architecture written to Tier 4 |
| g07_p04b | file | `artifact_owned_by_run` | `path: …/phase6_implementation_architecture/implementation_architecture.json, run_id: <current_run_id>` | Implementation architecture written to Tier 4 |
| g07_p05 | schema | `risk_register_populated` | `path: …/phase6_implementation_architecture/implementation_architecture.json` | Risk register is populated |
| g07_p06 | schema | `ethics_assessment_explicit` | `path: …/phase6_implementation_architecture/implementation_architecture.json` | Ethics self-assessment is explicitly present (not omitted) |
| g07_p07 | schema | `governance_matrix_present` | `path: …/phase6_implementation_architecture/implementation_architecture.json` | Governance matrix is defined |
| g07_p08 | coverage | `all_management_roles_in_tier3` | `impl_path: …/phase6_implementation_architecture/implementation_architecture.json, partners_path: …/consortium/partners.json` | All management roles assigned to Tier 3 consortium members |
| g07_p09 | coverage | `instrument_sections_addressed` | `impl_path: …/phase6_implementation_architecture/implementation_architecture.json, schema_path: …/extracted/section_schema_registry.json` | All instrument-mandated implementation sections addressed per Tier 2A schema |

---

### gate_09_budget_consistency — Phase 7 Exit

| ID | Type | Function | Args | prose_condition |
|----|------|----------|------|-----------------|
| g08_p01 | gate_pass | `gate_pass_recorded` | `gate_id: phase_06_gate, run_id: <current_run_id>` | Phase 6 gate must have passed |
| g08_p02 | file | `dir_non_empty` | `path: docs/integrations/lump_sum_budget_planner/received/` | Non-empty budget response artifact present in integrations/received/ |
| g08_p03 | file | `dir_non_empty` | `path: docs/integrations/lump_sum_budget_planner/validation/` | Validation artifact present in integrations/validation/ |
| g08_p04 | schema | `interface_contract_conforms` | `response_path: …/received/, contract_path: …/interface_contract.json` | Interface contract conformance confirmed |
| g08_p05 | coverage | `wp_budget_coverage_match` | `wp_path: …/phase3_wp_design/, budget_path: …/received/` | All Phase 3 WPs have corresponding budget entries |
| g08_p06 | coverage | `partner_budget_coverage_match` | `partners_path: …/consortium/partners.json, budget_path: …/received/` | All consortium partners have corresponding budget allocations |
| g08_p07 | schema | `no_blocking_inconsistencies` | `path: …/phase7_budget_gate/budget_gate_assessment.json` | No blocking inconsistency logged without resolution |
| g08_p08 | file | `non_empty_json` | `path: docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | Budget gate assessment written to Tier 4 |
| g08_p09 | file | `artifact_owned_by_run` | `path: …/phase7_budget_gate/budget_gate_assessment.json, run_id: <current_run_id>` | Budget gate assessment written to Tier 4 |

**Note:** gate_09 is `mandatory: true, bypass_prohibited: true`. The runner must treat a failure of g08_p02 (`dir_non_empty` on `received/`) not as a recoverable partial state but as a hard blocking gate failure that halts all downstream nodes. There is no predicate combination that can substitute for a missing budget response. `received/` and `validation/` are externally-supplied directories and do not have canonical single-file artifacts; `dir_non_empty` is the appropriate check for their presence, but run-scope ownership cannot be enforced on external content. The `interface_contract_conforms` predicate (g08_p04) provides the structural validity check that partially compensates.

---

### gate_10_part_b_completeness — Phase 8b Exit

| ID | Type | Function | Args | prose_condition |
|----|------|----------|------|-----------------|
| g09_p01 | gate_pass | `gate_pass_recorded` | `gate_id: gate_09_budget_consistency, run_id: <current_run_id>` | Budget gate must have passed |
| g09_p02 | coverage | `all_sections_drafted` | `sections_path: docs/tier5_deliverables/proposal_sections/, schema_path: …/extracted/section_schema_registry.json` | All sections required by active application form present in proposal_sections/ |
| g09_p03 | file | `non_empty_json` | `path: docs/tier5_deliverables/assembled_drafts/assembled_draft.json` | Assembled draft present in assembled_drafts/ |
| g09_p03b | file | `artifact_owned_by_run` | `path: …/assembled_drafts/assembled_draft.json, run_id: <current_run_id>` | Assembled draft present in assembled_drafts/ |
| g09_p04 | coverage | `all_sections_have_traceability_footer` | `sections_path: docs/tier5_deliverables/proposal_sections/` | Each section traceable to named Tier 1-4 sources |

---

### gate_11_review_closure — Phase 8c Exit

| ID | Type | Function | Args | prose_condition |
|----|------|----------|------|-----------------|
| g10_p01 | gate_pass | `gate_pass_recorded` | `gate_id: gate_10_part_b_completeness, run_id: <current_run_id>` | gate_10 must have passed |
| g10_p02 | file | `non_empty_json` | `path: docs/tier5_deliverables/review_packets/review_packet.json` | Review packet present in review_packets/ |
| g10_p02b | file | `artifact_owned_by_run` | `path: …/review_packets/review_packet.json, run_id: <current_run_id>` | Review packet present in review_packets/ |
| g10_p03 | schema | `findings_categorised_by_severity` | `path: docs/tier5_deliverables/review_packets/review_packet.json` | All critical findings categorised by severity |
| g10_p04 | schema | `revision_action_list_present` | `path: docs/tier5_deliverables/review_packets/review_packet.json` | Prioritised revision action list produced |

---

### gate_12_constitutional_compliance — Phase 8d Exit

| ID | Type | Function | Args | prose_condition |
|----|------|----------|------|-----------------|
| g11_p01 | gate_pass | `gate_pass_recorded` | `gate_id: gate_11_review_closure, run_id: <current_run_id>` | gate_11 must have passed |
| g11_p02 | coverage | `all_sections_drafted` | `sections_path: docs/tier5_deliverables/proposal_sections/, schema_path: …/extracted/section_schema_registry.json` | All sections required by active application form present |
| g11_p03 | file | `non_empty_json` | `path: docs/tier5_deliverables/review_packets/review_packet.json` | Review packet present |
| g11_p04 | schema | `all_critical_revisions_resolved` | `path: docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/drafting_review_status.json` | All critical revision actions resolved or explicitly logged as unresolvable with reason |
| g11_p05 | file | `non_empty_json` | `path: docs/tier5_deliverables/final_exports/final_export.json` | Final export present in final_exports/ |
| g11_p05b | file | `artifact_owned_by_run` | `path: …/final_exports/final_export.json, run_id: <current_run_id>` | Final export present in final_exports/ |
| g11_p06 | schema | `checkpoint_published` | `path: docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` | Phase 8 checkpoint published |
| g11_p07 | schema | `budget_gate_confirmation_present` | `path: docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | Budget gate confirmation present |
| g11_p08 | semantic | `no_cross_tier_contradictions` | `sections_path: docs/tier5_deliverables/proposal_sections/, tier3_path: docs/tier3_project_instantiation/` | No section contains content contradicted by a higher tier — CLAUDE.md §11.4, §13.3 |
| g11_p09 | semantic | `no_unsupported_tier5_claims` | `sections_path: docs/tier5_deliverables/proposal_sections/, tier3_path: docs/tier3_project_instantiation/` | No invented project facts in Tier 5 — CLAUDE.md §13.3 |
| g11_p10 | semantic | `no_budget_gate_contradiction` | `sections_path: docs/tier5_deliverables/proposal_sections/, phase7_path: …/phase7_budget_gate/budget_gate_assessment.json` | No budget-dependent finalization before gate pass — CLAUDE.md §8.4, §13.4 |
| g11_p11 | semantic | `no_higher_tier_contradiction` | `sections_path: docs/tier5_deliverables/proposal_sections/, tier2a_path: docs/tier2a_instrument_schemas/extracted/, tier2b_path: docs/tier2b_topic_and_call_sources/extracted/` | No invented call constraints or undercutting of higher tier — CLAUDE.md §13.2, §11.3 |
| g11_p12 | semantic | `no_forbidden_schema_authority` | `sections_path: docs/tier5_deliverables/proposal_sections/` | No Grant Agreement Annex schema used as proposal structure — CLAUDE.md §13.1 |
| g11_p13 | semantic | `no_gap_masked_as_confirmed` | `sections_path: docs/tier5_deliverables/proposal_sections/` | No Unresolved content presented as Confirmed — CLAUDE.md §12.2 |

---

## 6. Runner Integration Contract

### 6.1 Evaluation Flow

```
runner.evaluate_gate(gate_id, run_id, repo_root) -> GateResult

1. Load gate_rules_library.yaml
2. Retrieve predicate list for gate_id; fail if gate_id not found
3. Partition predicates into deterministic (types: file, gate_pass, schema,
   source_ref, coverage, cycle, timeline) and semantic (type: semantic)
4. Sort deterministic predicates by type in the order defined in §3
5. Compute input_fingerprint: hash the combined content of all required_inputs
   for this gate's owning phase as they exist on disk at evaluation time
6. Evaluate each deterministic predicate against the live repo state,
   passing run_id to gate_pass_recorded predicates and artifact_owned_by_run
   predicates; pass input_fingerprint to gate_pass_recorded predicates
   - On any failure: record failed predicate; continue evaluating remaining
     deterministic predicates to collect all failures in one pass
7. If any deterministic predicate failed:
   - Declare gate failure
   - Write GateResult to Tier 4 (see §6.2)
   - Return without invoking semantic predicates
8. If all deterministic predicates passed:
   - Invoke each semantic predicate via its designated agent/skill
   - Collect structured semantic results; reject any finding without
     violated_rule and evidence_path fields (treat as evaluation error)
9. If any semantic predicate failed:
   - Declare gate failure
10. If all predicates passed:
    - Declare gate pass
11. Write GateResult to Tier 4 (see §6.2), including run_id and input_fingerprint
12. Return GateResult
```

### 6.2 GateResult Schema

```yaml
gate_id: <str>
run_id: <str>                    # must match the DAG-runner startup run_id
input_fingerprint: <str>         # hash of combined required_inputs content at evaluation time
evaluated_at: <ISO 8601 timestamp>
repo_root: <str>
status: pass | fail
deterministic_predicates:
  passed: [<predicate_id>, ...]
  failed:
    - predicate_id: <str>
      type: <predicate_type>
      function: <str>
      args: { ... }
      fail_message: <str>
      prose_condition: <str>
semantic_predicates:
  passed: [<predicate_id>, ...]
  failed:
    - predicate_id: <str>
      function: <str>
      agent: <str>
      constitutional_rule: <str>   # e.g. "CLAUDE.md §13.3"; required
      findings:
        - claim: <str>
          violated_rule: <str>     # named constitutional section; required
          evidence_path: <str>     # path to artifact containing the violation; required
          severity: critical | major
      fail_message: <str>
skipped_semantic: <bool>   # true if gate failed on deterministic predicates
report_written_to: <path>  # Tier 4 gate result artifact path
```

`run_id` and `input_fingerprint` are mandatory fields. A GateResult without both fields is malformed and must be rejected by `gate_pass_recorded`. A GateResult with `status: pass` but a mismatched `run_id` is a stale artifact and must not satisfy any downstream `gate_pass_recorded` predicate.

### 6.3 Gate Result Artifact Location

Each gate result is written to the Tier 4 phase output for the phase that owns the gate:

| Gate | Result path |
|------|-------------|
| `gate_01_source_integrity` | `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/gate_01_result.json` |
| `phase_01_gate` | `docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/gate_result.json` |
| `phase_02_gate` | `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/gate_result.json` |
| `phase_03_gate` | `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/gate_result.json` |
| `phase_04_gate` | `docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/gate_result.json` |
| `phase_05_gate` | `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/gate_result.json` |
| `phase_06_gate` | `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/gate_result.json` |
| `gate_09_budget_consistency` | `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/gate_result.json` |
| `gate_10_part_b_completeness` | `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_10_result.json` |
| `gate_11_review_closure` | `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_11_result.json` |
| `gate_12_constitutional_compliance` | `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_12_result.json` |

The `gate_pass_recorded(gate_id, run_id, tier4_root)` predicate reads from this table to locate the canonical gate result artifact, then verifies `status: pass`, matching `run_id`, present `input_fingerprint`, and freshness against upstream artifact modification times.

### 6.4 Mandatory Gate Handling

Gates with `mandatory: true` and `bypass_prohibited: true` (currently only `gate_09_budget_consistency`) require additional runner behaviour:

- The runner must check `mandatory` and `bypass_prohibited` flags from the manifest before any gate evaluation
- If `dir_non_empty(docs/integrations/lump_sum_budget_planner/received/)` fails on gate_09, the runner must emit a `HARD_BLOCK` result code in addition to the standard `fail` status
- A `HARD_BLOCK` must propagate to all downstream nodes immediately; no downstream node may be placed in a queued or pending state
- The runner must surface the `HARD_BLOCK` to the human operator with the specific missing artifact paths

---

## 7. Canonical Artifact Ownership

### 7.1 Ownership Rules

Every gate-relevant field must be owned by exactly one canonical artifact file. These rules are non-negotiable for predicate stability:

1. **One canonical file per phase-owned structured artifact.** Each phase output directory has exactly one canonical structured JSON artifact. Auxiliary files (logs, partial outputs, draft files) may exist alongside the canonical artifact but are invisible to predicates.
2. **One schema ID per canonical file.** Each canonical artifact must declare a top-level `schema_id` field identifying which schema specification it conforms to. This allows the runner to reject a file whose schema_id does not match the expected schema.
3. **No duplicate field ownership.** A gate-relevant field name may appear in only one canonical file per phase output directory. If the same logical concept appears in multiple files (e.g., a risk list in a summary and a risk list in the canonical artifact), the canonical artifact governs and the duplicate is non-authoritative.
4. **Partial files are prohibited at gate evaluation time.** A canonical artifact must be complete before a gate is evaluated. An agent that writes partial content to the canonical artifact before phase completion is in violation. Agents must write to a staging location and atomically move to the canonical path on phase completion.
5. **Mandatory vs. auxiliary.** The canonical file for each phase is mandatory: its absence is a gate failure. All other files in the output directory are auxiliary and are neither checked nor relied upon by predicates.

### 7.2 Canonical File Registry

| Phase output directory | Canonical artifact file | Mandatory gate-relevant top-level fields |
|------------------------|------------------------|------------------------------------------|
| `phase_outputs/phase1_call_analysis/` | `call_analysis_summary.json` | `schema_id`, `run_id`, `evaluation_matrix`, `compliance_checklist`, `resolved_instrument_type` |
| `phase_outputs/phase2_concept_refinement/` | `concept_refinement_summary.json` | `schema_id`, `run_id`, `topic_mapping_rationale`, `scope_conflict_log`, `strategic_differentiation` |
| `phase_outputs/phase3_wp_design/` | `wp_structure.json` | `schema_id`, `run_id`, `work_packages`, `dependency_map`, `partner_role_matrix` |
| `phase_outputs/phase4_gantt_milestones/` | `gantt.json` | `schema_id`, `run_id`, `tasks` (each: `task_id`, `start_month`, `end_month`, `responsible_partner`), `milestones` (each: `milestone_id`, `due_month`, `verifiable_criterion`, `responsible_wp`), `critical_path` |
| `phase_outputs/phase5_impact_architecture/` | `impact_architecture.json` | `schema_id`, `run_id`, `impact_pathways`, `kpis`, `dissemination_plan`, `exploitation_plan`, `sustainability_mechanism` |
| `phase_outputs/phase6_implementation_architecture/` | `implementation_architecture.json` | `schema_id`, `run_id`, `risk_register`, `ethics_assessment`, `governance_matrix`, `management_roles` |
| `phase_outputs/phase7_budget_gate/` | `budget_gate_assessment.json` | `schema_id`, `run_id`, `gate_pass_declaration`, `wp_coverage_results`, `partner_coverage_results`, `blocking_inconsistencies` |
| `phase_outputs/phase8_drafting_review/` | `drafting_review_status.json` | `schema_id`, `run_id`, `section_completion_log`, `revision_actions`, `revision_log` |
| `checkpoints/` | `phase8_checkpoint.json` | `schema_id`, `run_id`, `status` (must equal `published`) |
| `tier5_deliverables/assembled_drafts/` | `assembled_draft.json` | `schema_id`, `run_id`, `sections` (ordered array), `consistency_log` |
| `tier5_deliverables/review_packets/` | `review_packet.json` | `schema_id`, `run_id`, `findings` (each: `severity`, `criterion`, `description`), `revision_actions` |
| `tier5_deliverables/final_exports/` | `final_export.json` | `schema_id`, `run_id`, `export_format`, `export_path`, `section_index` |

All gate result artifacts (named `gate_result.json` or per the §6.3 table) are a thirteenth canonical artifact type and must conform to the GateResult schema in §6.2.

### 7.3 Predicate Argument Resolution

All predicates that previously accepted a directory path (`dir_path`, `impl_path`, `impact_path`, `gantt_path`, `wp_path`, `review_path`, `phase8_path`) now accept the full path of the canonical artifact file listed in §7.2. Directory path arguments are not valid for schema, coverage, cycle, timeline, or canonical field predicates. The function signatures in §4.2–§4.8 use `path: str` to denote a canonical file path.

The sole exception is `dir_non_empty(path)` in §4.1, which remains a directory-level check and is restricted to the cases identified in §5: externally-supplied source directories where no canonical single-file artifact can be mandated.

### 7.4 Artifact Schema Specification

The field-level schemas for each canonical artifact (data types, required vs. optional fields, array item schemas, enum values) belong in a separate **artifact schema specification** document. That document is a prerequisite for implementing the predicate functions. The canonical file names and mandatory fields in §7.2 are a structural contract between this plan and the artifact schema specification. The schema specification must not introduce canonical file names or gate-relevant field names that conflict with §7.2 without amending this plan.

---

## 8. Implementation Sequence

The following sequence minimises blocked work and enables incremental testing. Each step produces something independently testable.

**Step 1 — Artifact schema specification**
Author the artifact schema document that defines the exact JSON structure each phase output artifact must follow (see §7). Without this, predicate functions cannot be implemented with stable contracts. This is the critical path prerequisite.

**Step 2 — Library file scaffolding**
Create `gate_rules_library.yaml` with all 12 gate entries and all predicate entries fully populated with `predicate_id`, `type`, `function`, `args`, `fail_message`, and `prose_condition`. Leave implementation of the predicate functions to subsequent steps. The library file is data; it can be authored before any code is written.

**Step 3 — File predicates**
Implement `exists`, `non_empty`, `non_empty_json`, `dir_non_empty`. These have no dependencies on other predicates or artifact schemas. They can be tested against the current (partially populated) repository immediately.

**Step 4 — Gate-pass predicate**
Implement `gate_pass_recorded(gate_id, run_id, tier4_root)`. This predicate reads the canonical gate result artifact from §6.3, confirms `status: pass`, confirms `run_id` matches the current run, confirms `input_fingerprint` is present, and confirms `evaluated_at` is not older than the mtime of any artifact in the upstream phase's `required_inputs`. Testing requires: (a) a synthetic gate result with a matching run_id (should pass), (b) a synthetic gate result with a mismatched run_id (must fail — stale artifact), (c) a synthetic gate result with status: pass but a modified upstream artifact since `evaluated_at` (must fail — freshness violation), (d) a synthetic gate result with a missing `input_fingerprint` field (must fail — malformed). The `run_id` itself must be established by the runner at DAG startup (Step 10) and passed into every `evaluate_gate` call; it is not a gate-level concern but a runner-level concern.

**Step 5 — Schema predicates**
Implement `json_field_present`, `json_fields_present`, `instrument_type_matches_schema`, `interface_contract_conforms`, and the structural field predicates (`risk_register_populated`, `ethics_assessment_explicit`, etc.). These depend on the artifact schema specification from Step 1.

**Step 6 — Source reference predicates**
Implement `source_refs_present` and `all_mappings_have_source_refs`. These traverse JSON arrays and check for the presence of reference fields.

**Step 7 — Coverage predicates**
Implement the cross-artifact join predicates: `wp_budget_coverage_match`, `partner_budget_coverage_match`, `all_impacts_mapped`, `kpis_traceable_to_wps`, `all_sections_drafted`, `all_partners_in_tier3`, `all_management_roles_in_tier3`, `all_tasks_have_months`, `instrument_sections_addressed`, `all_sections_have_traceability_footer`, `all_wps_have_deliverable_and_lead`. Each requires two artifact paths and performs a set-membership or join check.

**Step 8 — Cycle predicate**
Implement `no_dependency_cycles`. This requires parsing the `dependency_map` from the WP structure artifact and running a cycle detection algorithm (DFS or topological sort).

**Step 9 — Timeline predicates**
Implement `timeline_within_duration`, `all_milestones_have_criteria`, `wp_count_within_limit`, `critical_path_present`. These are arithmetic checks on parsed Gantt data.

**Step 10 — Runner evaluate_gate function**
Implement the runner integration described in §6.1. Establish `run_id` at DAG startup (a UUID or timestamp-based identifier, written to a run manifest file at the start of execution). Pass `run_id` into every `evaluate_gate` call. The runner must compute `input_fingerprint` before evaluating each gate, stamp `run_id` and `input_fingerprint` into every GateResult, and reject GateResult artifacts that are missing either field. Wire the runner to load the library, partition predicates by type, evaluate in order, and write GateResult artifacts.

**Step 11 — Semantic predicate dispatch layer**
Implement the semantic predicate dispatch layer: the runner calls the designated agent or skill with the specified artifact paths, receives a structured result conforming to the semantic predicate result schema, and integrates it into the GateResult. At this point all 12 gates are fully executable.

**Step 12 — Test fixtures**
Author test fixtures for each gate: one fixture representing a passing state and one representing each category of failure (missing artifact, malformed artifact, coverage gap, cycle, scope conflict). These fixtures allow the predicate functions to be tested in isolation and the runner to be tested end-to-end.

---

## 9. Migration Path to Approach B

Approach B embeds machine-readable predicates directly in the manifest alongside prose conditions. The migration from Approach A to Approach B is a manifest evolution, not a predicate reimplementation.

**Migration steps when ready:**

1. For each gate in the manifest `gate_registry`, add a `predicate_refs` list to each condition entry:
   ```yaml
   conditions:
     - prose: "All six Tier 2B extracted JSON files are non-empty with source section references"
       predicate_refs: [g02_p01, g02_p02, g02_p03, g02_p04, g02_p05, g02_p06,
                        g02_p07, g02_p08, g02_p09, g02_p10, g02_p11, g02_p12]
   ```

2. The runner is updated to read predicates from the manifest `predicate_refs` list rather than the library by gate_id lookup. The library becomes the implementation registry only; the manifest is the composition source.

3. The library file structure is unchanged. Predicate function implementations are unchanged. Only the runner's library-lookup step is replaced by a manifest-read step.

4. The `manifest.compile.yaml` compilation step is updated to include predicate_refs in its output, sourced from the phase YAML files (which also gain predicate_refs fields).

5. After migration, the library file can be renamed to `predicate_implementations.yaml` to reflect its new role as an implementation registry rather than a gate composition source.

The `prose_condition` field in each library predicate entry is the migration anchor: it is the text that will become the `prose` field in the manifest condition entry when the migration is performed.

---

## 10. Out of Scope for This Plan

The following are explicitly out of scope and must be planned separately before or alongside implementation:

- The artifact schema specification (§7) — prerequisite for Steps 5–9
- The runner DAG execution engine itself — this plan specifies only the gate evaluation contract
- Agent implementations for semantic predicates — these depend on existing agent catalog entries
- The compiled manifest regeneration process — `manifest.compile.yaml` is not modified by this plan
- CLAUDE.md amendments — the library is a new file and does not modify any existing constitutional document

---

*Plan document. No implementation. No changes to existing files.*
*To implement: begin with the artifact schema specification (§7, Step 1).*
