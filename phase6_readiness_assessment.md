# Phase 6 Readiness Diagnostics and Migration Planning Assessment

**Date:** 2026-04-23
**Branch:** phase5_refactor
**Assessment scope:** n06_implementation_architecture dispatch readiness
**Constitution version:** CLAUDE.md (in force)
**Migration plan version:** backend_migration_plan.md Rev 3.0

---

## 1. PHASE 6 PREREQUISITE VALIDATION

### Verdict: CONDITIONAL — Phase 4 gate is STALE

Phase 6 (n06_implementation_architecture) requires three upstream gates to have passed and remain fresh: `phase_03_gate`, `phase_04_gate`, and `phase_05_gate` (manifest edges e03_to_06, e04_to_06, e05_to_06).

#### Phase 3 — wp_structure.json

| Check | Result | Evidence |
|-------|--------|----------|
| Gate status | PASS | gate_result.json: `status: "pass"` |
| Gate run_id | `40b0bbbd-82e1-48d6-b8d2-e05f0e898092` | 2026-04-22T20:39:53Z |
| Deterministic predicates | 8/8 passed | g04_p01–p07 + g04_p02b |
| WP count | 9 WPs | Within RIA instrument limit |
| Tasks per WP | 3 each (27 total) | All have responsible partners |
| Deliverables | 24 total | All WPs have ≥1 deliverable + lead partner |
| Dependency map | 36 nodes, 17 edges | All `data_input` type; DAG confirmed acyclic |
| Partner coverage | 8 partners | All present in Tier 3 partners.json |
| Structural issues | Advisory: objectives/tasks synthesized from seed titles, not from detailed seed data | Non-blocking |

**Freshness status:** FRESH. Evaluated 2026-04-22, most recent among all upstream gates.

#### Phase 4 — gantt.json + scheduling_constraints.json

| Check | Result | Evidence |
|-------|--------|----------|
| Gate status | PASS | gate_result.json: `status: "pass"` |
| Gate run_id | `47e1adcc-8419-4892-aef1-43171871fb04` | 2026-04-21T13:15:40Z |
| Deterministic predicates | 11/11 passed | g05_p01–p08 + g05_p02b–p02d |
| Tasks scheduled | 27/27 | All have start_month and end_month |
| Timeline bounds | All ≤ 48 months | Consistent with selected_call.json |
| Milestones | 11 defined | All have verifiable criteria and due months |
| Critical path | Present | T2-01 → T2-02 → T2-03 → T8-02 → T8-03 |
| Strict constraints | 3 task-level finish_to_start | Enforced by g05_p08 |
| Non-strict constraints | 40 (reclassified + data_input) | Correctly documented |
| Dependency-schedule consistency | PASS | g05_p08 verified |

**Freshness status: STALE.** Phase 4 gate evaluated at 2026-04-21T13:15:40Z. Phase 3 was re-run on 2026-04-22 (run `40b0bbbd`), rewriting `wp_structure.json`. Since `wp_structure.json` is in `UPSTREAM_REQUIRED_INPUTS[phase_04_gate]`, its mtime (2026-04-22) exceeds Phase 4's `evaluated_at` (2026-04-21). The Phase 4 gate fails the freshness check.

**Impact:** The DAG scheduler bootstrap for `--phase 6` will reject Phase 4 as stale and abort with `overall_status: aborted`. Even if bootstrap were bypassed, exit gate predicates `g07_p02` (`gate_pass_recorded` for `phase_04_gate`) would also fail the freshness check. **Phase 4 must be re-run before Phase 6 can dispatch.**

#### Phase 5 — impact_architecture.json

| Check | Result | Evidence |
|-------|--------|----------|
| Gate status | PASS | gate_result.json: `status: "pass"` |
| Gate run_id | `e3caae21-094e-4537-94a6-6a26b826d8ce` | 2026-04-22T20:56:18Z |
| Deterministic predicates | 9/9 passed | g06_p01–p08 + g06_p03b |
| Impact pathways | 5 (PATH-01 to PATH-05) | All 5 expected impacts from Tier 2B mapped |
| KPIs | 10 (KPI-01 to KPI-10) | All traceable to WP deliverables |
| DEC fields | All non-null | dissemination_plan (8 activities), exploitation_plan (5 activities), sustainability_mechanism present |
| DEC validation | 47/47 checks passed, 0 flagged | dissemination-exploitation-communication-check_e3caae21.json |

**Freshness status:** FRESH. Evaluated 2026-04-22, after the Phase 3 rerun.

#### Gate Freshness Summary

| Gate | Status | Evaluated At | Run ID | Fresh? | Blocking? |
|------|--------|-------------|--------|--------|-----------|
| phase_03_gate | PASS | 2026-04-22T20:39:53Z | 40b0bbbd | YES | No |
| phase_04_gate | PASS | 2026-04-21T13:15:40Z | 47e1adcc | **NO** | **YES — BLOCKING** |
| phase_05_gate | PASS | 2026-04-22T20:56:18Z | e3caae21 | YES | No |

**Prerequisite validation result: CONDITIONAL.**
Phase 6 cannot dispatch until Phase 4 is re-run with a fresh run ID to produce a gate result with `evaluated_at` ≥ wp_structure.json mtime.

---

## 2. PHASE 6 INPUT ADEQUACY ANALYSIS

### Verdict: SUFFICIENT (with one verification required)

#### Tier 3 Consortium Data

| File | Status | Content |
|------|--------|---------|
| partners.json | Present, 8 partners | ATU (DE, coordinator), CERIA (FR), BIIS (NL), ISIA (IT), NIHS (SE), ELI (CH), BAL (FI), FIIT (ES) |
| roles.json | Present, 8 entries | Maps partner → consortium_role, scientific_role, wp_lead, wp_participant, key_responsibilities |
| capabilities.json | Present | File exists with content |
| compliance_profile.json | Present | `eligibility_confirmed: false`, `ethics_review_required: true`, `gender_plan_required: true` |

**Assessment:** Consortium data is complete for Phase 6. All 8 partners have roles, responsibilities, and WP assignments. The `eligibility_confirmed: false` flag does not block Phase 6 — no predicate checks this at the Phase 6 gate. The `ethics_review_required: true` flag correctly signals that the ethics self-assessment must be substantive (not a placeholder "N/A").

#### Tier 3 Risk Seeds

| File | Status | Content |
|------|--------|---------|
| risks.json | Present, 11 entries | RISK-01 to RISK-11 across technical (5), regulatory (2), operational (2), management (1), technical (1) categories |

Each risk has: probability, impact, affected_objectives, affected_work_packages, mitigation, contingency, risk_owner.

**Assessment:** Risk seeds are comprehensive and well-structured. The risk-register-builder skill can operate directly on these without additional enrichment.

#### Phase 3–5 Output Adequacy for Phase 6

| Artifact | Required By | Semantic Richness | Missing Join Keys | Gap? |
|----------|-------------|-------------------|-------------------|------|
| wp_structure.json | governance-model-builder, risk-register-builder | 9 WPs, 27 tasks, 24 deliverables, partner_role_matrix | None | No |
| gantt.json | risk-register-builder | 27 tasks with months, 11 milestones | None | No |
| scheduling_constraints.json | risk-register-builder | 3 strict + 40 non-strict edges | None | No |
| impact_architecture.json | implementation_architect reads_from | 5 pathways, 10 KPIs, full DEC | None | No |
| compliance_profile.json | implementation_architect reads_from | Ethics/gender/open-science flags | None | No |
| section_schema_registry.json | instrument_sections_addressed predicate | Instrument RIA sections defined | None | No |

#### Cross-Artifact Alignment

| Cross-Reference | Status |
|----------------|--------|
| WP leads (wp_structure) ↔ roles (roles.json) | Consistent — all 8 lead partners present in both |
| WP partners (wp_structure) ↔ Tier 3 partners.json | Verified by g04_p07 (passed) |
| KPI deliverable refs (impact_architecture) ↔ WP deliverables (wp_structure) | Verified by g06_p05 (passed) |
| Milestone responsible WPs (gantt) ↔ WP IDs (wp_structure) | Consistent |
| Risk affected_work_packages (risks.json) ↔ WP IDs (wp_structure) | WP1–WP9 referenced; consistent with 9 WP structure |

#### Verification Required: Ethics + Instrument Sections Production

The Phase 6 gate requires two fields in `implementation_architecture.json` that are **not explicitly listed** as outputs of any single skill:

| Field | Gate Predicate | Produced By |
|-------|---------------|-------------|
| `ethics_assessment` | g07_p06 (`ethics_assessment_explicit`) | **Unclear** — not in governance-model-builder declared outputs (governance_matrix, management_roles), not in risk-register-builder declared outputs (risk_register) |
| `instrument_sections_addressed` | g07_p09 (`instrument_sections_addressed`) | **Unclear** — same concern |

**Analysis:** The governance-model-builder is the first skill invoked and creates the base `implementation_architecture.json`. Its skill spec likely instructs Claude to produce ALL required fields (including ethics_assessment and instrument_sections_addressed) as part of the initial artifact creation. The merge-on-write model ("reads existing file to avoid overwriting risk_register, ethics_assessment, instrument_sections_addressed") confirms these fields are expected to exist in the artifact. However, this must be verified in the actual skill spec's Claude instructions before execution.

**Input adequacy result: SUFFICIENT**, contingent on verifying that governance-model-builder's Claude instructions produce ethics_assessment and instrument_sections_addressed alongside governance_matrix and management_roles.

---

## 3. TAPM MIGRATION STATUS FOR PHASE 6

### Phase 6 Skill Inventory

| Skill | Current Mode | Declared reads_from | Estimated Input Size | TAPM Status |
|-------|-------------|--------------------|--------------------|-------------|
| governance-model-builder | cli-prompt | consortium/ + phase3_wp_design/ | ~38KB base + ~15KB spec = **~53KB prompt** | **RECOMMENDED** |
| risk-register-builder | cli-prompt | risks.json + phase3_wp_design/ + phase4_gantt_milestones/ | ~65KB base + ~15KB spec = **~80KB prompt** | **STRONGLY RECOMMENDED** |
| milestone-consistency-check | cli-prompt | phase3_wp_design/ + gantt.json (FULL mode) | ~50KB base + ~10KB spec = **~60KB prompt** | Recommended |
| constitutional-compliance-check | cli-prompt (pending Phase 8 TAPM) | implementation_architecture.json + CLAUDE.md sections | ~35KB for Phase 6 context | Acceptable on cli-prompt |
| gate-enforcement | **TAPM (migrated)** | Canonical phase artifact + gate-relevant context | ~15KB | Already migrated |

### Skill-Level Assessment

#### governance-model-builder — RECOMMENDED for TAPM

- **Current mode:** cli-prompt (no `execution_mode` field in skill_catalog.yaml)
- **Estimated prompt:** ~53KB (consortium ~8KB + wp_structure ~30KB + skill spec ~15KB)
- **Risk of prompt bloat:** MODERATE. At 53KB, this is above the 50KB cli-prompt budget (backend_migration_plan.md §12.2) but below the threshold where timeouts were observed (~74-78KB).
- **Recommendation:** Migrate to TAPM before Phase 6 execution if possible. Not strictly blocking — Phase 6 may succeed on cli-prompt — but exceeds the constitutional prompt budget.

#### risk-register-builder — STRONGLY RECOMMENDED for TAPM

- **Current mode:** cli-prompt (no `execution_mode` field in skill_catalog.yaml)
- **Estimated prompt:** ~80KB (risks.json ~5KB + wp_structure ~30KB + gantt.json ~20KB + scheduling_constraints ~10KB + skill spec ~15KB)
- **Risk of prompt bloat:** HIGH. The 80KB estimate exceeds the threshold where timeouts with zero output were observed for `instrument-schema-normalization` (78KB, run 0ace9e49) and `topic-scope-check` (74KB). Original backend_migration_plan.md classified this as "Never migrate" based on a ~30KB estimate, but actual serialization includes the full phase output directories, not just individual files.
- **Recommendation:** **Must migrate to TAPM before Phase 6 execution.** The cli-prompt path risks timeout failure at 80KB+ prompt size. This follows the precedent of reclassifying skills after runtime telemetry revealed actual prompt sizes exceeded static estimates (backend_migration_plan.md §4.2 reclassification note).

#### milestone-consistency-check — ACCEPTABLE on cli-prompt

- **Current mode:** cli-prompt
- **Estimated prompt:** ~60KB in FULL mode (wp_structure ~30KB + gantt.json ~20KB + spec ~10KB)
- **Recommendation:** Migrate to TAPM if convenient, but not blocking. This skill ran successfully on cli-prompt during Phase 4 (run 47e1adcc).

#### constitutional-compliance-check — ACCEPTABLE on cli-prompt for Phase 6

- **Current mode:** cli-prompt (pending Phase 8 TAPM migration)
- **Estimated prompt:** ~35KB for Phase 6 (implementation_architecture.json ~15-20KB + CLAUDE.md sections ~10KB + spec ~5KB)
- **Recommendation:** No migration needed for Phase 6. Phase 8 inputs are much larger (~150KB+), where TAPM becomes essential.

#### gate-enforcement — ALREADY MIGRATED

- **Current mode:** TAPM (validated, per migration status table)
- **No action required.**

### TAPM Migration Summary

| Priority | Skill | Action | Justification |
|----------|-------|--------|---------------|
| **MUST** | risk-register-builder | Migrate to TAPM | ~80KB prompt exceeds timeout threshold (78KB precedent) |
| **SHOULD** | governance-model-builder | Migrate to TAPM | ~53KB prompt exceeds 50KB budget rule |
| MAY | milestone-consistency-check | Migrate to TAPM | Consistency; not blocking |
| NO | constitutional-compliance-check | Keep cli-prompt | ~35KB for Phase 6 context; adequate |
| DONE | gate-enforcement | Already TAPM | — |

---

## 4. RISK & FAILURE MODE ANALYSIS

### R1: Phase 4 Gate Staleness — BLOCKING

| Dimension | Value |
|-----------|-------|
| **Severity** | HIGH |
| **Likelihood** | CERTAIN |
| **Detectability** | Gate-detected (bootstrap freshness check rejects stale gate) |
| **Failure mode** | DAG scheduler aborts with `overall_status: aborted`, `unsatisfied_conditions: [phase_04_gate]` |
| **Root cause** | Phase 3 re-run (2026-04-22) updated wp_structure.json mtime after Phase 4 gate evaluation (2026-04-21) |
| **Resolution** | Re-run Phase 4 with fresh run ID |

### R2: risk-register-builder Prompt Timeout

| Dimension | Value |
|-----------|-------|
| **Severity** | HIGH |
| **Likelihood** | HIGH (~80KB prompt; 78KB caused zero-output timeout in prior skills) |
| **Detectability** | Runtime — agent_body failure with `failure_category: AGENT_EXECUTION_ERROR` or 300s timeout with zero output |
| **Failure mode** | n06 blocked_at_exit with `failure_origin: agent_body`; risk_register field missing from implementation_architecture.json |
| **Root cause** | cli-prompt serializes full phase output directories (~65KB data) + skill spec (~15KB) into single prompt |
| **Resolution** | Migrate risk-register-builder to TAPM before Phase 6 execution |

### R3: Ethics/Instrument Sections Field Gap

| Dimension | Value |
|-----------|-------|
| **Severity** | HIGH (gate predicates g07_p06, g07_p09 will fail if fields missing) |
| **Likelihood** | LOW-MEDIUM (governance-model-builder likely produces these as part of base artifact creation, but not explicitly confirmed in skill catalog output declarations) |
| **Detectability** | Gate-detected (deterministic predicates check field presence) |
| **Failure mode** | phase_06_gate fails on g07_p06 (`ethics_assessment_explicit`) or g07_p09 (`instrument_sections_addressed`) |
| **Root cause** | Potential skill decomposition gap — no skill explicitly declares ethics_assessment or instrument_sections_addressed as output |
| **Resolution** | Verify governance-model-builder.md Claude instructions include these fields; if not, extend the skill spec |

### R4: governance-model-builder Prompt Budget Violation

| Dimension | Value |
|-----------|-------|
| **Severity** | MEDIUM |
| **Likelihood** | MEDIUM (~53KB exceeds 50KB cli-prompt budget from backend_migration_plan.md §12.2) |
| **Detectability** | Runtime — slow execution or partial output |
| **Failure mode** | Degraded output quality or timeout; governance_matrix or management_roles incomplete |
| **Resolution** | Migrate to TAPM (recommended, not blocking) |

### R5: Milestone Timing Validation Noise

| Dimension | Value |
|-----------|-------|
| **Severity** | LOW |
| **Likelihood** | CERTAIN (9/11 milestones flagged in Phase 4 validation) |
| **Detectability** | Validation report (not gate-blocking) |
| **Failure mode** | milestone-consistency-check in Phase 6 context produces advisory flags about milestone-to-task timing misalignment |
| **Root cause** | Design pattern: milestones mark intermediate delivery points, not WP completion. Valid but generates noise in validation reports. |
| **Resolution** | No action; advisory only. Milestone timing is architecturally intentional. |

### R6: Partner Management Role Assignment Failure

| Dimension | Value |
|-----------|-------|
| **Severity** | HIGH (gate predicate g07_p08 blocks on non-Tier-3 partners) |
| **Likelihood** | LOW (consortium is well-defined; governance-model-builder constrained to Tier 3 partners) |
| **Detectability** | Gate-detected (coverage predicate `all_management_roles_in_tier3`) |
| **Failure mode** | phase_06_gate fails on g07_p08 |
| **Root cause** | Claude assigns a management role to a partner_id not in partners.json |
| **Resolution** | Skill spec constraint + gate enforcement catch this; re-run if needed |

### R7: TAPM Containment Violation

| Dimension | Value |
|-----------|-------|
| **Severity** | MEDIUM (context access invariant violation, but output still schema-validated) |
| **Likelihood** | LOW (prompt-based containment has worked reliably in Phases 1-5) |
| **Detectability** | Post-hoc audit of `--output-format stream-json` Read tool calls |
| **Failure mode** | Claude reads undeclared files outside `reads_from` set |
| **Resolution** | Audit Read tool invocations against declared `reads_from`; flag violations |

### Risk Matrix Summary

| Risk | Severity | Likelihood | Category |
|------|----------|------------|----------|
| R1: Phase 4 staleness | HIGH | CERTAIN | **BLOCKING** |
| R2: risk-register-builder timeout | HIGH | HIGH | **BLOCKING** |
| R3: Ethics/instrument field gap | HIGH | LOW-MEDIUM | Verify before execution |
| R4: governance-model-builder prompt budget | MEDIUM | MEDIUM | Recommended fix |
| R5: Milestone timing noise | LOW | CERTAIN | Advisory only |
| R6: Partner role assignment | HIGH | LOW | Gate-protected |
| R7: TAPM containment | MEDIUM | LOW | Audit post-execution |

---

## 5. PHASE 6 MIGRATION PLAN

### A. Preconditions (must be satisfied before running Phase 6)

**A1. Re-run Phase 4** (resolves R1)

Phase 4 gate is stale. wp_structure.json was rewritten on 2026-04-22 (Phase 3 rerun), after Phase 4 gate evaluation on 2026-04-21. The bootstrap freshness check and exit gate predicate g07_p02 both require a fresh Phase 4 gate.

```bash
python -m runner --run-id $(python -c "import uuid; print(uuid.uuid4())") --phase 4 --verbose
```

**Expected outcome:** Phase 4 re-runs with:
1. dependency_normalizer reads current wp_structure.json → produces fresh scheduling_constraints.json
2. gantt-schedule-builder produces fresh gantt.json
3. milestone-consistency-check validates in FULL mode
4. gate-enforcement evaluates phase_04_gate → PASS
5. New gate_result.json with `evaluated_at` ≥ wp_structure.json mtime

**Verification:**
- `phase_04_gate` gate_result.json: `status: "pass"`, `evaluated_at` > 2026-04-22T20:39:53Z
- gantt.json: 27 tasks, all with months, timeline ≤ 48 months
- scheduling_constraints.json: no unresolved constraints

**A2. Verify ethics_assessment production** (resolves R3)

Before Phase 6 execution, confirm that governance-model-builder.md's Claude instructions include ethics_assessment and instrument_sections_addressed as output fields. Read the skill spec body and verify the output schema instructions.

If these fields are NOT in the skill spec's output instructions:
- Extend governance-model-builder.md to include ethics_assessment and instrument_sections_addressed field requirements
- OR create a separate `implementation-sections-builder` skill

**A3. Verify Phase 6 gate predicate implementations exist**

Confirm the following predicate functions are implemented in `runner/predicates/`:
- `risk_register_populated` (g07_p05)
- `ethics_assessment_explicit` (g07_p06)
- `governance_matrix_present` (g07_p07)
- `all_management_roles_in_tier3` (g07_p08)
- `instrument_sections_addressed` (g07_p09)

```bash
python -m pytest tests/ -k "phase_06 or g07" -v --co
```

### B. Required Fixes

**B1. Migrate risk-register-builder to TAPM** (resolves R2)

The risk-register-builder cli-prompt size (~80KB) exceeds the timeout threshold observed for other skills (78KB). This is a probable execution failure.

Steps:
1. Add `execution_mode: "tapm"` to risk-register-builder entry in `skill_catalog.yaml`
2. Add TAPM input-boundary instructions to `.claude/skills/risk-register-builder.md`:
   ```
   ## Input Access (TAPM Mode)
   Read the files listed in the Declared Inputs section from disk using the Read tool.
   Do not read files outside the declared input set.
   Return your output as a single JSON object in your response.
   ```
3. Verify `reads_from` paths are specific files (not directory trees)

**B2. Migrate governance-model-builder to TAPM** (resolves R4, recommended)

The governance-model-builder cli-prompt size (~53KB) exceeds the 50KB prompt budget. TAPM migration is recommended.

Steps: Same as B1, applied to governance-model-builder.

### C. TAPM Actions

| Order | Skill | Action | Dependency |
|-------|-------|--------|------------|
| 1 | risk-register-builder | Add `execution_mode: "tapm"` + input boundary instructions | None |
| 2 | governance-model-builder | Add `execution_mode: "tapm"` + input boundary instructions | None |
| 3 | (optional) milestone-consistency-check | Add `execution_mode: "tapm"` | Not blocking |

Both migrations follow the validated TAPM pattern from Phases 1-5:
- Transport already supports `tools=["Read", "Glob"]` (Step 1 complete)
- TAPM prompt assembly (`_assemble_tapm_prompt`) already implemented (Step 2 complete)
- Mode selection in `run_skill()` already functional (Step 3 complete)
- Only per-skill `execution_mode` field and input boundary instructions needed

### D. Execution Plan

#### Step D1: TAPM migrations (B1 + B2)

```bash
# Verify test suite passes before changes
python -m pytest tests/ -v --tb=short
```

Edit `skill_catalog.yaml`: add `execution_mode: "tapm"` to risk-register-builder and governance-model-builder.
Edit corresponding `.claude/skills/*.md`: add TAPM input boundary instructions.

```bash
# Verify test suite still passes
python -m pytest tests/ -v --tb=short
```

#### Step D2: Re-run Phase 4

```bash
python -m runner --run-id $(python -c "import uuid; print(uuid.uuid4())") --phase 4 --verbose
```

**Validation checkpoint:**
- `overall_status: "pass"` in run_summary.json
- `phase_04_gate` status: "pass"
- gantt.json has `run_id` matching this run
- scheduling_constraints.json has `run_id` matching this run

#### Step D3: Verify A2 + A3 (ethics/instrument field production + predicate implementations)

Read governance-model-builder.md skill spec. Confirm output instructions include all 5 required fields of implementation_architecture.json:
1. governance_matrix
2. management_roles
3. risk_register (handled by risk-register-builder via merge)
4. ethics_assessment
5. instrument_sections_addressed

Run predicate implementation check:
```bash
python -m pytest tests/ -k "g07" -v --co 2>/dev/null | head -30
```

#### Step D4: Execute Phase 6

```bash
python -m runner --run-id $(python -c "import uuid; print(uuid.uuid4())") --phase 6 --verbose
```

**Validation checkpoints during execution:**
- Bootstrap accepts n03, n04, n05 as released (all fresh)
- Agent body invokes skills in order: governance-model-builder → risk-register-builder → milestone-consistency-check → constitutional-compliance-check → gate-enforcement
- implementation_architecture.json written to `phase6_implementation_architecture/`
- All 5 required fields present and non-null
- gate-enforcement returns PASS payload

#### Step D5: Post-execution validation

```bash
# Verify gate result
python -c "
import json
with open('docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/gate_result.json') as f:
    gr = json.load(f)
print(f'Status: {gr[\"status\"]}')
print(f'Predicates passed: {len(gr[\"deterministic_predicates\"][\"passed\"])}')
print(f'Predicates failed: {len(gr[\"deterministic_predicates\"][\"failed\"])}')
"
```

Expected: status=pass, 9 deterministic predicates passed (g07_p01-p09 including g07_p04b), 0 failed.

### E. Success Criteria

Phase 6 is considered successfully passed when ALL of the following are true:

| # | Criterion | Verification |
|---|-----------|-------------|
| 1 | `phase_06_gate` status is `"pass"` | gate_result.json |
| 2 | All 9 deterministic predicates passed (g07_p01–p09 + g07_p04b) | gate_result.json `deterministic_predicates.passed` |
| 3 | `implementation_architecture.json` exists, non-empty, owned by current run | g07_p04, g07_p04b |
| 4 | Upstream gates fresh: phase_03_gate, phase_04_gate, phase_05_gate | g07_p01, g07_p02, g07_p03 |
| 5 | risk_register non-empty, all entries have likelihood + impact + mitigation | g07_p05 |
| 6 | ethics_assessment explicitly present with non-empty self_assessment_statement | g07_p06 |
| 7 | governance_matrix non-empty with body compositions and decision scopes | g07_p07 |
| 8 | All management roles assigned to Tier 3 consortium partners | g07_p08 |
| 9 | All instrument-mandated implementation sections addressed per Tier 2A | g07_p09 |
| 10 | Schema ID = `orch.phase6.implementation_architecture.v1` | Artifact validation |
| 11 | No TAPM containment violations (undeclared file reads) | Post-hoc stream-json audit |

---

## Summary

| Section | Verdict | Key Finding |
|---------|---------|-------------|
| 1. Prerequisite Validation | **CONDITIONAL** | Phase 4 gate is STALE — must re-run Phase 4 |
| 2. Input Adequacy | **SUFFICIENT** | Verify ethics/instrument field production in skill spec |
| 3. TAPM Migration | **2 migrations required** | risk-register-builder MUST migrate; governance-model-builder SHOULD migrate |
| 4. Risk Analysis | **2 BLOCKING risks** | R1 (Phase 4 staleness — certain), R2 (risk-register-builder timeout — high) |
| 5. Migration Plan | **4-step execution** | TAPM migration → Phase 4 rerun → verify skill spec → execute Phase 6 |

**Phase 6 is NOT ready for immediate execution.** Two blocking issues must be resolved first:
1. Phase 4 must be re-run to produce a fresh gate result
2. risk-register-builder must be migrated to TAPM to avoid prompt timeout

After these two actions, Phase 6 can be dispatched with high confidence of gate passage.
