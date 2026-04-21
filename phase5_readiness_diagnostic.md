# Phase 5 Readiness Diagnostic and Migration Plan

**Date:** 2026-04-21
**Branch:** `phase4_refactor`
**Post:** Phase 4 gate pass (validated)
**Scope:** Phase 5 — Impact Architecture (`n05_impact_architecture`)

---

## 1. Phase 5 Structural Summary

### 1.1 Node and Agent Binding

| Field | Value |
|-------|-------|
| Node ID | `n05_impact_architecture` |
| Phase ID | `phase_05_impact_architecture` |
| Phase Number | 5 |
| Agent | `impact_architect` |
| Entry Gate | None (no entry gate defined) |
| Exit Gate | `phase_05_gate` |
| Terminal | `false` |
| Source File | `workflow_phases/phase_05_impact_architecture.yaml` |

### 1.2 Skill Sequence

| Order | Skill ID | Purpose | Execution Mode |
|-------|----------|---------|----------------|
| 1 | `impact-pathway-mapper` | Map project outputs to call expected impacts; produce impact_architecture.json | cli-prompt (catalog: no `execution_mode` set) |
| 2 | `dissemination-exploitation-communication-check` | Validate DEC plan specificity against call/instrument requirements | cli-prompt |
| 3 | `proposal-section-traceability-check` | Apply Confirmed/Inferred/Assumed/Unresolved status to claims | cli-prompt |
| 4 | `gate-enforcement` | Evaluate phase_05_gate predicates; return payload to agent | tapm |

### 1.3 Inputs Consumed

#### Phase 2 Outputs (via `e02_to_05`, `e03_to_05`)
| Artifact | Path | Status |
|----------|------|--------|
| Concept refinement summary | `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json` | **EXISTS, GATE PASSED** (run `3bb41e14`, 2026-04-18) |
| Phase 2 gate result | `docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/gate_result.json` | **PASS** |

#### Phase 3 Outputs
| Artifact | Path | Status |
|----------|------|--------|
| WP structure | `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json` | **EXISTS, GATE PASSED** (run `ca7cb19a`, 2026-04-20) |
| Phase 3 gate result | `docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/gate_result.json` | **PASS** |

#### Tier 3 Architecture Inputs
| Artifact | Path | Status | Content |
|----------|------|--------|---------|
| Outcomes seed | `docs/tier3_project_instantiation/architecture_inputs/outcomes.json` | **EXISTS, NON-EMPTY** (85 lines) | 8 outcomes (OUT-1 through OUT-9): neuro-symbolic planning, memory architecture, coordination protocols, clinical decision support, manufacturing optimization, logistics demonstrator, tool orchestration, open-source framework |
| Impacts seed | `docs/tier3_project_instantiation/architecture_inputs/impacts.json` | **EXISTS, NON-EMPTY** (90 lines) | 6 impacts (IMP-1 through IMP-6): scientific, societal, economic, policy dimensions with indicators and timeline |

#### Tier 2B Extracted Files
| Artifact | Path | Status | Content |
|----------|------|--------|---------|
| Expected outcomes | `docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json` | **EXISTS, NON-EMPTY** | 2 expected outcomes (EO-01, EO-02): AI agent autonomy improvements; multi-agent frameworks |
| Expected impacts | `docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json` | **EXISTS, NON-EMPTY** | 5 expected impacts (EI-01 through EI-05): Apply AI Strategy, EDIHs, AI-on-demand platform, strategic autonomy, economic potential |
| Evaluation priority weights | `docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json` | **EXISTS, NON-EMPTY** | 3 evaluation criteria with call-specific priority notes |

### 1.4 Outputs Produced

| Artifact | Canonical Path | Schema ID |
|----------|---------------|-----------|
| Impact architecture | `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json` | `orch.phase5.impact_architecture.v1` |
| Gate result | `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/gate_result.json` | `orch.gate_result.v1` |
| Validation report (DEC check) | `docs/tier4_orchestration_state/validation_reports/dec_check_*.json` | N/A (validation artifact) |

**Current state of output directory:** Does not exist yet (correct; created at execution time).

### 1.5 Gate: `phase_05_gate`

#### Predicates (9 total, all deterministic)

| Predicate ID | Type | Function | Target | Prose Condition |
|-------------|------|----------|--------|-----------------|
| g06_p01 | gate_pass | `gate_pass_recorded` | phase_02_gate | Phase 2 gate must have passed |
| g06_p02 | gate_pass | `gate_pass_recorded` | phase_03_gate | Phase 3 gate must have passed |
| g06_p03 | file | `non_empty_json` | impact_architecture.json | Full impact architecture written to Tier 4 |
| g06_p03b | file | `artifact_owned_by_run` | impact_architecture.json | Artifact owned by current run |
| g06_p04 | coverage | `all_impacts_mapped` | impact_architecture.json vs expected_impacts.json | All call expected impacts have at least one mapped project output |
| g06_p05 | coverage | `kpis_traceable_to_wps` | impact_architecture.json vs wp_structure.json | KPI set is defined and traceable to WP deliverables |
| g06_p06 | schema | `json_field_present` | impact_architecture.json `dissemination_plan` | Dissemination logic defined |
| g06_p07 | schema | `json_field_present` | impact_architecture.json `exploitation_plan` | Exploitation logic defined |
| g06_p08 | schema | `json_field_present` | impact_architecture.json `sustainability_mechanism` | Sustainability mechanism defined |

**No semantic predicates** in `phase_05_gate`. All 9 predicates are deterministic.

#### Upstream Dependency from `UPSTREAM_REQUIRED_INPUTS`

```python
"phase_05_gate": [
    "docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json",
    "docs/tier3_project_instantiation/architecture_inputs/outcomes.json",
    "docs/tier3_project_instantiation/architecture_inputs/impacts.json",
    "docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json",
    "docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json",
]
```

**All 5 upstream required inputs exist and are non-empty.**

### 1.6 Upstream Artifact Confirmation

| Upstream artifact | Present? | Schema-valid? | Gate-passed? |
|-------------------|----------|---------------|-------------|
| `concept_refinement_summary.json` | Yes | `orch.phase2.concept_refinement_summary.v1` | Yes (phase_02_gate: pass) |
| `wp_structure.json` | Yes | `orch.phase3.wp_structure.v1` | Yes (phase_03_gate: pass) |
| `outcomes.json` (Tier 3) | Yes | Manually placed; 8 entries with required fields | N/A (no gate) |
| `impacts.json` (Tier 3) | Yes | Manually placed; 6 entries with required fields | N/A (no gate) |
| `expected_outcomes.json` (Tier 2B) | Yes | 2 entries with source_section/source_document | Produced by Phase 1 (phase_01_gate: pass) |
| `expected_impacts.json` (Tier 2B) | Yes | 5 entries with source_section/source_document | Produced by Phase 1 (phase_01_gate: pass) |
| `evaluation_priority_weights.json` (Tier 2B) | Yes | 3 criteria entries with source fields | Produced by Phase 1 (phase_01_gate: pass) |

**All required upstream artifacts are present, schema-valid, and (where applicable) gate-passed.**

---

## 2. Readiness Verdict

### **VERDICT: CONDITIONALLY READY**

Phase 5 is structurally complete and all mandatory inputs are present. Execution can proceed. However, output quality depends on Claude's ability to produce a schema-compliant impact_architecture.json on first attempt within the cli-prompt transport's prompt-size and timeout constraints. This has NOT been validated.

### 2.1 Structural Readiness

**READY.** All required specifications, schemas, predicates, and input artifacts are in place:

- Agent spec (`impact_architect.md`): 233 lines, complete with constitutional constraints, must-not obligations, decision-log write obligations
- Primary skill (`impact-pathway-mapper.md`): 274 lines, 8-step execution logic, 3 constitutional constraints, 5 failure categories
- Secondary skill (`dissemination-exploitation-communication-check.md`): 246 lines, 5 validation checks
- Gate predicates: All 9 implemented and verified (`all_impacts_mapped` and `kpis_traceable_to_wps` confirmed in `coverage_predicates.py`)
- Artifact schema: `orch.phase5.impact_architecture.v1` fully defined with 7 required top-level fields

### 2.2 Semantic Readiness

**CONDITIONALLY READY.** Phase 2 output provides concept alignment, but:

- Phase 2 `concept_refinement_summary.json` was produced under a prior run (`3bb41e14`). The `gate_pass_recorded` predicate checks this via the reuse policy or stale-upstream-mismatch check. If the scheduler uses `--phase 5` with a new `run_id`, the gate_pass predicates `g06_p01` and `g06_p02` must find the prior gate results. The scheduler resolves this by scanning for gate result artifacts on disk (not by run_id match on the gate_pass check — `gate_pass_recorded` looks for a gate result file with `status: "pass"`, not necessarily matching the current run_id).

  **RISK:** If `gate_pass_recorded` implementation strictly requires `run_id == current_run_id`, the gate will fail because Phase 2 and Phase 3 were run under different run_ids. This would require either:
  (a) A reuse policy file, or
  (b) Confirmation that `gate_pass_recorded` uses cross-run gate result acceptance

  This is a **conditional risk** — it depends on the exact implementation of `gate_pass_recorded`.

- Tier 3 `outcomes.json` (8 entries) and `impacts.json` (6 entries) provide adequate project-side data for pathway construction. The `expected_impact_alignment` field in `impacts.json` already cross-references Tier 2B expected impact IDs, which should facilitate the mapping task.

### 2.3 Dependency Integrity

**NO INCONSISTENCIES DETECTED.**

- Phase 2 and Phase 3 outputs are consistent: `wp_structure.json` references the same consortium partners as Phase 2's `concept_refinement_summary.json`.
- Tier 3 `impacts.json` entries include `linked_outcomes` fields that cross-reference `outcomes.json` entries.
- Tier 2B `expected_impacts.json` has 5 entries (EI-01 through EI-05); Tier 3 `impacts.json` has 6 entries (IMP-1 through IMP-6) which should provide sufficient coverage.

### 2.4 Gate Feasibility

**ALL PREDICATES REALISTICALLY SATISFIABLE.**

| Predicate | Satisfiability |
|-----------|---------------|
| g06_p01 (Phase 2 gate passed) | Satisfied — gate result exists with status: pass |
| g06_p02 (Phase 3 gate passed) | Satisfied — gate result exists with status: pass |
| g06_p03 (impact_architecture.json non-empty) | Satisfiable — depends on skill producing valid output |
| g06_p03b (artifact owned by run) | Satisfiable — run_id will be injected by skill runtime |
| g06_p04 (all impacts mapped) | Satisfiable if Claude maps all 5 expected_impact_ids to pathways with non-empty project_outputs. 8 project outcomes and 6 project impacts provide adequate coverage material. |
| g06_p05 (KPIs traceable to WPs) | Satisfiable if Claude uses deliverable_ids from wp_structure.json. Risk: Claude may generate non-existent deliverable_ids. |
| g06_p06 (dissemination_plan present) | Satisfiable — straightforward field inclusion |
| g06_p07 (exploitation_plan present) | Satisfiable — straightforward field inclusion |
| g06_p08 (sustainability_mechanism present) | Satisfiable — straightforward field inclusion |

### 2.5 Risk Classification

#### Blocking Risks (must fix before Phase 5)

1. **`gate_pass_recorded` cross-run behavior** — If the predicate strictly requires `run_id` match with the current run, Phase 5 will fail at g06_p01/g06_p02 because Phase 2 and Phase 3 were run under different run_ids. **Mitigation:** Verify the predicate implementation or create a reuse policy file.

#### Degradation Risks (Phase 5 runs but produces weak output)

1. **Deliverable ID hallucination** — `impact-pathway-mapper` must reference `deliverable_id` values from `wp_structure.json` in both `impact_pathways[].project_outputs` and `kpis[].traceable_to_deliverable`. Claude may generate plausible but non-existent IDs. **Detection:** `kpis_traceable_to_wps` predicate (g06_p05) will catch KPI violations. `all_impacts_mapped` only checks `expected_impact_id` presence, not deliverable existence in `project_outputs`. **Mitigation:** Skill spec includes explicit instruction to read and reference actual deliverable_ids from wp_structure.json.

2. **Impact pathway completeness** — The skill must map all 5 expected_impact_ids (EI-01 through EI-05). Missing even one triggers g06_p04 failure. Two of the 5 (EI-04, EI-05) have status "Inferred" in expected_impacts.json, meaning they were derived from the topic destination context rather than explicit call text. **Detection:** `all_impacts_mapped` predicate. **Mitigation:** Skill spec explicitly requires mapping or flagging all expected impacts.

3. **Prompt size under cli-prompt** — `impact-pathway-mapper` reads from 5 source paths across 3 tiers. The total serialized input will include `outcomes.json` (85 lines), `impacts.json` (90 lines), `expected_outcomes.json` (17 lines), `expected_impacts.json` (44 lines), `wp_structure.json` (~30KB), plus concept refinement summary. Estimated total: ~40-60KB. The backend_migration_plan classifies `impact-pathway-mapper` as "tapm: Later" with "4 paths across tiers (~80KB)". This is within the current cli-prompt tolerance but at the moderate-to-high end. **Detection:** Timeout or truncated output. **Mitigation:** `SKILL_MAX_TOKENS` is 8192; this may be insufficient for the impact_architecture.json artifact which has 7 required top-level fields with nested arrays. Consider increasing to 16384.

4. **`proposal-section-traceability-check` skip behavior** — This skill is listed in the n05 skill sequence, but it audits Tier 5 deliverables which don't exist yet at Phase 5. Per `_TIER5_AUDIT_SKILLS` in `agent_runtime.py`, this skill will be skipped as "not_applicable". This is correct behavior, not a failure. **Non-risk.**

#### Non-Risks (explicitly ruled out)

1. **Missing Tier 3 inputs** — Both `outcomes.json` and `impacts.json` are present with substantive, structured content.
2. **Missing Tier 2B inputs** — All three relevant extracted files exist and are non-empty.
3. **Predecessor gate failures** — Both phase_02_gate and phase_03_gate have passed.
4. **Budget gate interference** — Phase 5 precedes the budget gate; no budget-dependent content is produced.
5. **Dependency cycle propagation** — Phase 5 does not consume Phase 4 dependency data; it uses Phase 3 WP structure only.
6. **Missing gate predicate implementations** — Both `all_impacts_mapped` and `kpis_traceable_to_wps` are implemented and verified in `coverage_predicates.py`.

---

## 3. TAPM Suitability Assessment for Phase 5

### Per-Skill Classification

#### `impact-pathway-mapper`

| Factor | Assessment |
|--------|-----------|
| Input size | ~40-80KB across 5 read paths (Tier 3 outcomes/impacts, Tier 2B expected_outcomes/impacts, Phase 3 wp_structure) |
| Cross-tier reads | 3 tiers (Tier 2B extracted, Tier 3 architecture_inputs, Tier 4 phase_outputs) |
| Reasoning complexity | HIGH — must construct novel impact pathways mapping project outputs to call expectations; requires cross-referencing deliverable_ids across artifacts |
| Prompt-bloat risk | MODERATE-HIGH — wp_structure.json alone is ~30KB; skill spec is ~33KB |
| **Classification** | **tapm (migrate later)** |
| **Justification** | Input size (~80KB) matches the backend_migration_plan's assessment. Not in the "migrate first" cohort but a clear TAPM candidate. However, first execution should validate output quality in cli-prompt mode before migration. |

#### `dissemination-exploitation-communication-check`

| Factor | Assessment |
|--------|-----------|
| Input size | ~30KB (impact_architecture.json + section_schema_registry + expected_impacts) |
| Cross-tier reads | 2 tiers (Tier 2B extracted, Tier 4 phase_outputs) |
| Reasoning complexity | MODERATE — validation/flagging task, not generative |
| Prompt-bloat risk | LOW-MODERATE — reads Phase 5 output (which must exist) + two small reference files |
| **Classification** | **cli-prompt (keep)** |
| **Justification** | Listed in backend_migration_plan as "cli-prompt: Never" with "Phase 5 + extracted (~30KB)". Input size is within cli-prompt tolerance. |

#### `proposal-section-traceability-check`

| Factor | Assessment |
|--------|-----------|
| Input size | N/A at Phase 5 — skill is skipped (Tier 5 not yet populated) |
| **Classification** | **N/A at Phase 5** |
| **Justification** | Skipped via `_TIER5_AUDIT_SKILLS` logic in agent_runtime.py. Will be evaluated for TAPM at Phase 8. |

#### `gate-enforcement`

| Factor | Assessment |
|--------|-----------|
| Input size | ~10-20KB (phase-specific canonical artifact + gate condition definition) |
| **Classification** | **tapm (already)** |
| **Justification** | Already set to `execution_mode: "tapm"` in skill_catalog.yaml. |

### Phase 5 TAPM Migration Decision

**Recommendation: Defer TAPM migration for Phase 5 until after first successful execution.**

Rationale:
1. `impact-pathway-mapper` is the only skill with TAPM-relevant input size (~80KB), and the backend_migration_plan already classifies it as "tapm: Later"
2. First execution should validate that the skill spec produces a gate-passing artifact under cli-prompt before changing the execution mode
3. The primary risk is output quality (deliverable_id accuracy, impact mapping completeness), not prompt size — TAPM does not directly mitigate these risks
4. After a successful Phase 5 run, `impact-pathway-mapper` can be migrated to TAPM as part of the Step 5 rollout in the backend_migration_plan

---

## 4. Failure Mode Analysis

### FM-1: Missing or Weak Tier 3 Data

| Attribute | Value |
|-----------|-------|
| **Root cause** | `outcomes.json` or `impacts.json` absent, empty, or lacking required fields |
| **Current status** | **NOT TRIGGERED** — both files present with substantive content |
| **Detection mechanism** | Skill-level input validation (Step 1 of impact-pathway-mapper: presence/schema checks); `MISSING_INPUT` failure category |
| **Mitigation** | Already mitigated — files are populated. Future-proofing: gate could add `non_empty_json` checks on Tier 3 inputs (not currently in predicate set). |

### FM-2: Inconsistent Outcomes vs Impacts

| Attribute | Value |
|-----------|-------|
| **Root cause** | `impacts.json` `linked_outcomes` references outcome_ids not present in `outcomes.json`; or project impacts don't align with call expected impacts |
| **Current status** | **LOW RISK** — `impacts.json` entries include `expected_impact_alignment` field that explicitly maps to EI-xx IDs from expected_impacts.json |
| **Detection mechanism** | Skill-level validation (Step 2); `CONSTRAINT_VIOLATION` failure category; gate predicate `all_impacts_mapped` for call coverage |
| **Mitigation** | Skill spec requires mapping all expected impact IDs or flagging as uncovered. The `expected_impact_alignment` field in Tier 3 provides a mapping seed. |

### FM-3: Malformed Impact Architecture

| Attribute | Value |
|-----------|-------|
| **Root cause** | Claude produces JSON that doesn't conform to `orch.phase5.impact_architecture.v1` — missing required fields, wrong types, extra fields |
| **Current status** | **MEDIUM RISK** — first execution; no prior baseline |
| **Detection mechanism** | `_validate_skill_output()` in skill_runtime.py; gate predicates g06_p03, g06_p06, g06_p07, g06_p08 verify field presence |
| **Mitigation** | Schema enforcement in skill spec (Step 5 of impact-pathway-mapper). If malformed: `MALFORMED_ARTIFACT` failure, node blocked at exit. |

### FM-4: Gate Predicate Failures — `all_impacts_mapped` (g06_p04)

| Attribute | Value |
|-----------|-------|
| **Root cause** | Claude fails to map all 5 expected_impact_ids (EI-01 through EI-05) to pathways with non-empty `project_outputs` |
| **Current status** | **MEDIUM RISK** — EI-04 and EI-05 are "Inferred" status, meaning Claude must interpret destination-level context |
| **Detection mechanism** | `all_impacts_mapped` predicate (coverage_predicates.py:978-1075); checks every expected_impact_id appears in `impact_pathways[]` with non-empty `project_outputs` |
| **Mitigation** | Skill spec explicitly requires mapping or flagging. If unmapped: skill returns `INCOMPLETE_OUTPUT`. On predicate failure: gate logs missing impact_ids in failure details. Rerun with improved prompt or Tier 3 data. |

### FM-5: Gate Predicate Failures — `kpis_traceable_to_wps` (g06_p05)

| Attribute | Value |
|-----------|-------|
| **Root cause** | Claude generates KPIs with `traceable_to_deliverable` values that don't exist in `wp_structure.json` |
| **Current status** | **MEDIUM-HIGH RISK** — this is the most likely failure mode for first execution. Claude must correctly reference deliverable_ids (e.g., "D1-01", "D2-01") from a ~30KB WP structure. |
| **Detection mechanism** | `kpis_traceable_to_wps` predicate (coverage_predicates.py:1078-1183); checks each KPI's deliverable reference against the deliverable_id set from wp_structure.json |
| **Mitigation** | Skill spec instructs Claude to read and reference actual deliverable_ids. Under TAPM (future), Claude would Read wp_structure.json directly, improving accuracy. For cli-prompt mode, the full WP structure is serialized in the prompt, so the data is available but attention may not focus on exact IDs. |

### FM-6: Hallucinated Impact Pathways

| Attribute | Value |
|-----------|-------|
| **Root cause** | Claude produces pathways with impact narratives that are not grounded in project-specific mechanisms; uses generic programme-level language |
| **Current status** | **MEDIUM RISK** — inherent to generative AI; mitigated by constitutional constraints in skill spec |
| **Detection mechanism** | No deterministic predicate detects this (would require semantic evaluation). Constitutional compliance check in Phase 6 and Phase 8 gates catches generic language. dissemination-exploitation-communication-check flags generic phrases. |
| **Mitigation** | Skill spec constitutional constraint 3: "Impact narratives must be project-specific, not generic; failure triggers CONSTRAINT_VIOLATION." The DEC check skill validates specificity with a list of disallowed generic strings. |

### FM-7: Non-Traceable Outcomes

| Attribute | Value |
|-----------|-------|
| **Root cause** | Impact pathways reference project outcomes not traceable to WP activities or deliverables |
| **Current status** | **LOW-MEDIUM RISK** — skill spec requires traceability but verification is limited to KPI→deliverable link (g06_p05); pathway→deliverable link is not checked by a dedicated predicate |
| **Detection mechanism** | Partial: `kpis_traceable_to_wps` checks KPIs; no predicate specifically checks `impact_pathways[].project_outputs[]` against wp_structure.json deliverable_ids. The `all_impacts_mapped` predicate checks only that `project_outputs` is non-empty, not that the referenced deliverables exist. |
| **Mitigation** | **GAP IDENTIFIED.** The `all_impacts_mapped` predicate does not cross-validate `project_outputs[]` deliverable_ids against wp_structure.json. This is a validation gap — impact pathways could claim non-existent deliverables as evidence. **Recommended fix:** Add a predicate or extend `all_impacts_mapped` to verify project_outputs deliverable_ids exist in wp_structure.json. This is a **non-blocking** enhancement; the existing KPI traceability check provides partial coverage. |

### FM-8: `gate_pass_recorded` Cross-Run Failure

| Attribute | Value |
|-----------|-------|
| **Root cause** | Phase 5 runs under a new run_id, but Phase 2 and Phase 3 gate results were produced under different run_ids. If `gate_pass_recorded` strictly requires the current run_id, g06_p01 and g06_p02 will fail. |
| **Current status** | **POTENTIALLY BLOCKING** — depends on implementation |
| **Detection mechanism** | Gate evaluation at g06_p01/g06_p02; `STALE_UPSTREAM_MISMATCH` failure category |
| **Mitigation** | Options: (a) Verify `gate_pass_recorded` accepts cross-run gate results on disk (likely, based on `--phase` semantics in README: "reads the durable node states from prior runs via gate result artifacts in Tier 4"). (b) Create a reuse policy file per run. (c) If blocking, re-run Phase 2 and Phase 3 under the same run_id as Phase 5 (expensive). |

### FM-9: `SKILL_MAX_TOKENS` Insufficient

| Attribute | Value |
|-----------|-------|
| **Root cause** | impact_architecture.json requires 7 required top-level fields with deeply nested arrays. At 8192 max_tokens, the output may be truncated. |
| **Current status** | **MEDIUM RISK** — Phase 4 encountered similar issues; gantt.json is also a large artifact |
| **Detection mechanism** | `_extract_json_response()` failure in skill_runtime.py → `MALFORMED_ARTIFACT`; or output parsed but missing required fields → gate failure |
| **Mitigation** | The skill_runtime.py docstring notes: "the claude -p CLI transport does NOT enforce a --max-tokens flag. Response length is bounded by prompt design." However, if the response is cut off by the transport's internal limits or timeout, the artifact will be incomplete. Monitor output size on first run. Consider per-skill `max_tokens` override if needed. |

---

## 5. Migration Plan for Phase 5

### Step A — Pre-Execution Validation

Before running Phase 5, verify the following:

1. **`gate_pass_recorded` cross-run behavior** (BLOCKING CHECK)
   ```bash
   # Verify that gate_pass_recorded accepts prior-run gate results
   # Check the implementation:
   grep -n "gate_pass_recorded" runner/predicates/*.py runner/gate_evaluator.py
   ```
   If the predicate requires `run_id` match, create a reuse policy file for the Phase 5 run_id authorizing the Phase 2 and Phase 3 gate results.

2. **Confirm all upstream inputs exist**
   ```bash
   python -c "
   import json, os
   files = [
       'docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/concept_refinement_summary.json',
       'docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json',
       'docs/tier3_project_instantiation/architecture_inputs/outcomes.json',
       'docs/tier3_project_instantiation/architecture_inputs/impacts.json',
       'docs/tier2b_topic_and_call_sources/extracted/expected_outcomes.json',
       'docs/tier2b_topic_and_call_sources/extracted/expected_impacts.json',
       'docs/tier2b_topic_and_call_sources/extracted/evaluation_priority_weights.json',
   ]
   for f in files:
       exists = os.path.exists(f)
       size = os.path.getsize(f) if exists else 0
       valid = False
       if exists and size > 0:
           try:
               json.loads(open(f).read())
               valid = True
           except: pass
       status = 'OK' if (exists and size > 0 and valid) else 'FAIL'
       print(f'{status} {f} ({size} bytes)')
   "
   ```

3. **Dry-run Phase 5 to verify readiness**
   ```bash
   python -m runner --run-id $(python -c "import uuid; print(uuid.uuid4())") --phase 5 --dry-run --verbose
   ```
   Expected: n05_impact_architecture shows as READY. If it shows as stalled with unsatisfied conditions, the `gate_pass_recorded` issue (FM-8) is blocking.

4. **Verify deliverable_id inventory from wp_structure.json**
   ```bash
   python -c "
   import json
   wp = json.loads(open('docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json').read())
   ids = set()
   for wp_entry in wp.get('work_packages', []):
       for d in wp_entry.get('deliverables', []):
           ids.add(d.get('deliverable_id', ''))
   print(f'{len(ids)} deliverable_ids available for KPI traceability:')
   for did in sorted(ids):
       print(f'  {did}')
   "
   ```
   This inventory will be the validation reference for g06_p05.

### Step B — First Execution Strategy

**Execution command:**
```bash
python -m runner --run-id $(python -c "import uuid; print(uuid.uuid4())") --phase 5 --verbose
```

**TAPM status:** NOT enabled for Phase 5 skills (except `gate-enforcement` which is already TAPM). `impact-pathway-mapper` and `dissemination-exploitation-communication-check` run in cli-prompt mode.

**Dry-run:** Not used for execution (only in Step A for readiness verification).

**Expected execution flow:**
1. Scheduler evaluates n05_impact_architecture readiness
2. Verifies incoming edges: e02_to_05 (phase_02_gate) and e03_to_05 (phase_03_gate) are satisfied
3. Sets node state to `running`
4. `run_agent("impact_architect", ...)` invoked
5. Agent sequences skills:
   - `impact-pathway-mapper` → produces `impact_architecture.json`
   - `dissemination-exploitation-communication-check` → validates DEC plan
   - `proposal-section-traceability-check` → **SKIPPED** (Tier 5 not populated)
   - `gate-enforcement` → evaluates phase_05_gate predicates
6. Agent determines `can_evaluate_exit_gate` from disk state
7. Scheduler evaluates `phase_05_gate` (9 deterministic predicates)
8. On pass: node released; e05_to_06 unblocked for Phase 6

### Step C — Evaluation Criteria

**Phase 5 is successful when:**

1. `impact_architecture.json` exists at canonical path with:
   - `schema_id: "orch.phase5.impact_architecture.v1"`
   - `run_id` matching the current run
   - Non-empty `impact_pathways` array covering all 5 expected_impact_ids (EI-01 through EI-05)
   - Non-empty `kpis` array with all `traceable_to_deliverable` values matching existing deliverable_ids from wp_structure.json
   - Non-null `dissemination_plan`, `exploitation_plan`, `sustainability_mechanism` fields

2. Gate `phase_05_gate` passes all 9 predicates:
   - g06_p01, g06_p02: predecessor gates confirmed
   - g06_p03, g06_p03b: file existence and run ownership
   - g06_p04: all 5 expected impacts mapped with non-empty project_outputs
   - g06_p05: all KPIs traceable to WP deliverables
   - g06_p06, g06_p07, g06_p08: required fields present

3. Run summary shows `n05_impact_architecture: released`

4. Gate result written to `docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/gate_result.json` with `status: "pass"`

**Verification commands:**
```bash
# Check artifact exists and has correct schema
python -c "
import json
ia = json.loads(open('docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/impact_architecture.json').read())
print(f'schema_id: {ia.get(\"schema_id\")}')
print(f'run_id: {ia.get(\"run_id\")}')
print(f'impact_pathways: {len(ia.get(\"impact_pathways\", []))} entries')
print(f'kpis: {len(ia.get(\"kpis\", []))} entries')
print(f'dissemination_plan: {\"present\" if ia.get(\"dissemination_plan\") else \"MISSING\"}')
print(f'exploitation_plan: {\"present\" if ia.get(\"exploitation_plan\") else \"MISSING\"}')
print(f'sustainability_mechanism: {\"present\" if ia.get(\"sustainability_mechanism\") else \"MISSING\"}')
# Check expected impact coverage
mapped = {p.get('expected_impact_id') for p in ia.get('impact_pathways', []) if p.get('project_outputs')}
expected = {'EI-01', 'EI-02', 'EI-03', 'EI-04', 'EI-05'}
missing = expected - mapped
print(f'Expected impact coverage: {len(mapped)}/{len(expected)}')
if missing:
    print(f'MISSING: {missing}')
"
```

### Step D — TAPM Migration (Deferred)

**Decision: Defer TAPM migration for Phase 5 to after first successful execution.**

If/when migrating:

1. **Skill to migrate:** `impact-pathway-mapper`
   - Set `execution_mode: "tapm"` in skill_catalog.yaml
   - Add input-boundary instructions to `.claude/skills/impact-pathway-mapper.md`
   - Update `reads_from` to list specific file paths (not directories)
   - Expected prompt reduction: ~80KB → ~15KB

2. **Order:** After Step 5 of the backend_migration_plan (Phase 2-6 TAPM rollout)

3. **Rollback:** Revert `execution_mode` to `"cli-prompt"` in skill_catalog.yaml. One line change.

4. **Skills NOT migrated:**
   - `dissemination-exploitation-communication-check` — 30KB input, within cli-prompt tolerance
   - `proposal-section-traceability-check` — skipped at Phase 5
   - `gate-enforcement` — already TAPM

### Step E — Post-Execution Validation

Before proceeding to Phase 6:

1. **Verify gate result**
   ```bash
   python -c "
   import json
   gr = json.loads(open('docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/gate_result.json').read())
   print(f'Gate: {gr.get(\"gate_id\")}')
   print(f'Status: {gr.get(\"status\")}')
   print(f'Deterministic passed: {len(gr.get(\"deterministic_predicates\", {}).get(\"passed\", []))}')
   print(f'Deterministic failed: {len(gr.get(\"deterministic_predicates\", {}).get(\"failed\", []))}')
   "
   ```

2. **Verify Phase 6 prerequisites are met**
   Phase 6 requires Phases 3, 4, AND 5 gates to have passed. Confirm:
   - phase_03_gate: PASS (already confirmed)
   - phase_04_gate: PASS (confirmed by Phase 4 remediation)
   - phase_05_gate: PASS (just completed)

3. **Check for quality issues in impact_architecture.json**
   - Are impact narratives project-specific (not generic)?
   - Do KPI targets reference measurable quantities?
   - Does the dissemination plan name specific target audiences (not just "stakeholders")?
   - Does the sustainability mechanism identify responsible partners?

4. **Verify decision log entries were written**
   ```bash
   ls docs/tier4_orchestration_state/decision_log/
   ```

5. **Update backend_migration_plan.md Phase 5 status**
   Change from "NOT YET ATTEMPTED" to "OPERATIONAL" or "OPERATIONAL (gate passed)" with notes on any issues encountered.

---

## 6. Required Fixes

### 6.1 Potentially Blocking

| # | Location | Fix | Reason | Blocking? |
|---|----------|-----|--------|-----------|
| 1 | `runner/predicates/` — `gate_pass_recorded` implementation | Verify cross-run gate result acceptance; if not supported, create reuse policy template | Phase 5 runs under a new run_id but depends on Phase 2/3 gate results from prior runs. If the predicate requires run_id match, Phase 5 cannot pass g06_p01/g06_p02. | **POTENTIALLY BLOCKING** — must verify before execution |

### 6.2 Non-Blocking Quality Improvements

| # | Location | Fix | Reason | Blocking? |
|---|----------|-----|--------|-----------|
| 2 | `gate_rules_library.yaml` — `phase_05_gate` | Consider adding a predicate to validate `impact_pathways[].project_outputs[]` deliverable_ids against wp_structure.json | FM-7: `all_impacts_mapped` checks only that `project_outputs` is non-empty, not that referenced deliverables exist. This is a traceability gap. | Non-blocking |
| 3 | `skill_catalog.yaml` — `impact-pathway-mapper` | Verify or add `execution_mode: "cli-prompt"` explicitly (currently absent = default) | Explicit declaration prevents ambiguity | Non-blocking |
| 4 | `runner/skill_runtime.py` — `SKILL_MAX_TOKENS` | Consider per-skill `max_tokens` override mechanism or increase global default for Phase 5 | impact_architecture.json is a large artifact with 7 required top-level fields and nested arrays; 8192 tokens may be insufficient | Non-blocking (transport doesn't enforce, but output truncation risk) |

### 6.3 Tier 3 Data Requirements

**No additional Tier 3 data is required.** Both `outcomes.json` (8 entries) and `impacts.json` (6 entries) are substantively populated with structured data including cross-references to call expected impacts. The data is sufficient for Phase 5 execution.

---

## 7. Summary

| Section | Key Finding |
|---------|-------------|
| **1. Structural Summary** | n05_impact_architecture: 1 node, 1 agent (impact_architect), 4 skills, 9 gate predicates. All upstream artifacts present and gate-passed. |
| **2. Readiness Verdict** | **CONDITIONALLY READY** — all inputs present and structurally valid. Conditional on: (a) `gate_pass_recorded` accepting cross-run gate results, (b) first-run output quality being gate-sufficient. |
| **3. TAPM Classification** | `impact-pathway-mapper`: tapm (defer to post-first-run). `dissemination-exploitation-communication-check`: cli-prompt (keep). Phase 5 TAPM migration deferred. |
| **4. Failure Modes** | 9 failure modes identified. Highest risk: FM-5 (KPI deliverable_id hallucination), FM-8 (cross-run gate_pass), FM-9 (max_tokens insufficiency). |
| **5. Migration Plan** | Step A: verify gate_pass_recorded + dry-run. Step B: `python -m runner --phase 5 --verbose`. Step C: 9 predicates must pass. Step D: TAPM deferred. Step E: verify gate result + check Phase 6 readiness. |
| **6. Required Fixes** | 1 potentially blocking (gate_pass_recorded cross-run). 3 non-blocking improvements. 0 Tier 3 data gaps. |
