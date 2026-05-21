


Here is the exact Claude prompt for this fix — structured in your standard deterministic, implementation-ready format:

Claude Prompt — Fix Phase 2 Summary Coverage Semantics
Title
Revise concept-alignment-check to explicitly encode Tier 2B scope coverage in concept_refinement_summary.json

Context
Phase 2 (n02_concept_refinement) consistently reaches exit gate evaluation, but fails semantic predicate:

g03_p06 = no_unresolved_scope_conflicts

The failure is not due to actual concept misalignment, but due to incomplete representation of scope coverage in the Phase 2 summary artifact.

Observed Failure
From the Phase 2 gate result:

Deterministic predicates: all pass

Semantic predicate g03_p06: fail

Failure reason:

scope_conflict_log is empty ([])

BUT mandatory Tier 2B scope requirements:

SR-09 (ADRA / GenAI4EU cohesion activities)

SR-11 (AI Factories / Data Labs linkage)

have no documented coverage in concept_refinement_summary.json

Result:

The system interprets these as unresolved scope conflicts by omission, even though the concept text and topic-scope-check confirm they are in scope.

Root Cause
concept-alignment-check currently produces a summary with:

topic_mapping_rationale (EO-focused)

scope_conflict_log (only for flagged conflicts)

strategic_differentiation

It does NOT:

Record positive coverage of mandatory Tier 2B scope requirements

Provide any structured mapping between:

Tier 2B scope elements (SR-xx / CC-xx)

Tier 3 evidence

Therefore:

Semantic predicate no_unresolved_scope_conflicts

Cannot distinguish between:

“covered but not logged”

“not covered”

→ Fail-closed triggers incorrectly.

Goal
Revise concept-alignment-check so that:

concept_refinement_summary.json explicitly encodes coverage status for all mandatory Tier 2B scope requirements, not only EO mappings and conflicts.

This must allow semantic predicates to:

deterministically verify coverage

distinguish:

covered

unresolved

intentionally out-of-scope (with justification)

Design Requirements
1. Introduce new top-level field
Add:

"scope_coverage": {
  "<scope_element_id>": {
    "scope_element_id": "SR-09",
    "constraint_ref": "CC-03",
    "coverage_status": "covered",
    "coverage_description": "...",
    "tier2b_source_ref": "...",
    "tier3_evidence_ref": "...",
    "notes": "...optional..."
  }
}
2. Coverage scope
scope_coverage MUST include ALL mandatory Tier 2B elements, including at minimum:

SR-09 (ADRA / GenAI4EU cohesion)

SR-10 (AI-on-demand platform sharing)

SR-11 (AI Factories / Data Labs linkage)

SR-07 (sector demonstrators)

SR-06 (KPIs / benchmarking)

CC constraints relevant to Phase 2 (CC-01, CC-03, CC-05, CC-07, etc.)

Source of truth:

scope_requirements.json

call_constraints.json

3. Coverage status enum
Allowed values:

"covered" → explicit Tier 3 evidence exists

"partially_covered" → incomplete but not blocking

"unresolved" → MUST also appear in scope_conflict_log

"not_applicable" → only if explicitly justified by Tier 2B

Fail-closed rule:

Any mandatory element not present in scope_coverage → treated as unresolved

4. Mandatory consistency rules
Enforce:

If coverage_status == "unresolved"
→ MUST appear in scope_conflict_log

If scope_conflict_log == []
→ ALL mandatory elements MUST have:

coverage_status == "covered" or "partially_covered"

Every entry MUST include:

tier2b_source_ref

tier3_evidence_ref

5. No weakening of semantics
DO NOT:

Auto-mark everything as "covered"

Suppress legitimate conflicts

Infer coverage without Tier 3 evidence

This is not a cosmetic fix — it is a semantic contract completion

Implementation Steps
Step 1 — Update skill spec
File:

.claude/skills/concept-alignment-check.md
Modify:

Output schema section

Add scope_coverage definition

Execution steps

After EO mapping:

Iterate all Tier 2B scope elements

Evaluate coverage

Populate scope_coverage

Conflict handling

Ensure unresolved items populate BOTH:

scope_coverage

scope_conflict_log

Output construction

Add scope_coverage to final JSON

Step 2 — Update schema validation
File:

artifact_schema_specification.yaml
Update:

orch.phase2.concept_refinement_summary.v1
Add:

scope_coverage as required field

Validate:

presence of mandatory scope elements

valid coverage_status

required references present

Step 3 — Update semantic predicate compatibility
File:

runner/predicates/gate_pass_predicates.py
For:

no_unresolved_scope_conflicts
Update logic:

Prefer scope_coverage as primary source

Only fall back to scope_conflict_log if missing

New condition:

FAIL if:

any mandatory element:

missing from scope_coverage

OR coverage_status == "unresolved"

Step 4 — Tests
Add/modify:

tests/runner/test_phase2_summary_coverage.py
Test cases:

All mandatory elements covered → PASS

Missing SR-09 → FAIL

Missing SR-11 → FAIL

scope_conflict_log == [] but missing coverage → FAIL

Covered + valid references → PASS

Unresolved → appears in both structures → PASS (correct fail behavior)

Expected Result
After fix:

concept_refinement_summary.json explicitly encodes all Tier 2B scope coverage

Semantic predicate:

no longer infers missing coverage from absence

evaluates deterministically

Phase 2 gate:

passes when coverage is genuinely complete

fails only on real gaps

Non-Goals
Do NOT modify:

scheduler

continuation logic

TAPM execution

Do NOT alter:

Tier 3 source files

Do NOT weaken:

fail-closed semantics

Verification
Run:

python -m runner --phase phase2 --verbose
Confirm:

g03_p06 passes

no semantic_fail due to missing SR-09 / SR-11

concept_refinement_summary.json contains full scope_coverage

This is the correct next structural fix — it aligns the artifact contract with the semantic gate expectations instead of patching symptoms.



artifact_schema_specification.yaml
File

gate_rules_library_plan.md
File

concept-alignment-check.md
File

run_manifest.json
File

run_summary.json
File

gate_evaluator.py
Python

scope_coverage_predicates.py
Python

concept_refinement_summary.json
File

gate_result.json
File

decision-log-update_3bb41e14.json
File

topic-scope-check_3bb41e14.json
File
PS C:\Code\proposal_demo\proposal_orchestrator> python -m runner --run-id (python -c "import uuid; print(uuid.uuid4())") --phase phase2 --verbose
[INFO]   Bootstrap: n01_call_analysis -> released (evidence: docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/gate_result.json, original_run_id: a634da9d-ef08-4aca-98e1-57e9c9f6de89)
[BOOTSTRAP] Seeded 1 upstream node(s) from prior evidence: ['n01_call_analysis']
[RUN]   run_id=3bb41e14-a388-4cbc-8c24-81e1475d1393  phase=2
[INFO] Call slice generated: C:\Code\proposal_demo\proposal_orchestrator\docs\tier2b_topic_and_call_sources\call_extracts\HORIZON-CL4-2026-05-DIGITAL-EMERGING-02.slice.json       
[INFO] Phase-scoped execution: phase=2  nodes=['n02_concept_refinement']
[INFO]   Dispatching: n02_concept_refinement
[INFO]   [n02_concept_refinement] state -> running
[INFO]   [n02_concept_refinement] agent dispatch: agent=concept_refiner
[INFO]   skill START  id=concept-alignment-check  mode=tapm  node=-  run=3bb41e14
[INFO]   skill INVOKE id=concept-alignment-check  sys=1235  user=34674  timeout=600s
[INFO]   skill OK     id=concept-alignment-check  outputs=1  elapsed=482.3s
[INFO]   skill START  id=concept-call-binding-derivation  mode=tapm  node=-  run=3bb41e14
[INFO]   skill INVOKE id=concept-call-binding-derivation  sys=1299  user=16101  timeout=600s
[INFO]   skill START  id=topic-scope-check  mode=tapm  node=-  run=3bb41e14
[INFO]   skill INVOKE id=topic-scope-check  sys=1114  user=48272  timeout=600s
[INFO]   skill OK     id=topic-scope-check  outputs=1  elapsed=301.5s
[INFO]   skill START  id=decision-log-update  mode=cli-prompt  node=-  run=3bb41e14
[INFO]   skill INVOKE id=decision-log-update  sys=691  user=108129  timeout=300s
[INFO]   skill OK     id=decision-log-update  outputs=1  elapsed=73.4s
[INFO]   [n02_concept_refinement] agent result: status=success  can_evaluate_exit=True
[INFO]   [n02_concept_refinement] exit gate phase_02_gate -> pass
[INFO]   [n02_concept_refinement] state -> released
[INFO] Run complete: overall_status=pass  dispatched=1  stalled=0
[SUMMARY] overall_status=pass  nodes_released=2  stalled=0  hard_blocked=0  phase=2

Thought for 7s
Yes — Phase 2 is now genuinely passing.

The run completed with overall_status: "pass", phase_scope: 2, and n02_concept_refinement in released state. 

 


More importantly, phase_02_gate itself now passes:

all deterministic predicates passed

semantic predicate g03_p06 also passed

gate status is pass 


What changed is exactly the fix you targeted:

concept-alignment-check now requires and emits scope_coverage in concept_refinement_summary.json, alongside topic_mapping_rationale, scope_conflict_log, and strategic_differentiation 


the new deterministic predicate all_mandatory_scope_covered exists specifically to stop the old ambiguity between “covered but not logged” and “not covered” 


the generated Phase 2 summary now explicitly records coverage for SR-09, SR-10, SR-11 and the relevant call constraints, rather than leaving them implicit 


The resulting summary is now semantically consistent enough for the gate:

both EO-01 and EO-02 are Confirmed

scope_conflict_log is empty

mandatory scope items are explicitly represented in scope_coverage 


The decision log also reflects the intended interpretation:

the concept is confirmed aligned with the topic

mandatory scope requirements are covered

partially covered items such as CC-08 to CC-13 are treated as submission-stage or later-stage matters, not Phase 2 blockers 


One nuance worth keeping in mind:
topic-scope-check still returns some advisory flagged findings around logistics, autonomous-driving portfolio positioning, and SME/open-source framing. But those are no longer treated as unresolved Phase 2 gate blockers, and the passing decision log explicitly classifies them as proposer-attention items rather than scope failures. 

 


So the answer is:

Phase 2 is complete and released.
You can proceed to Phase 3 (n03_wp_design) without rerunning Phase 1 or Phase 2.



backend_migration_plan.md
File

CLAUDE.md
File

README.md
File
Write a Claude prompt for Phase 3 readiness/first-run diagnostics and plan the next steps for the Phase 3 migration. Refer to the coverage of Phase 2 and instruct Claude to update the documentation (claude.md readme.md and the backend migration plan), if necessary. 

Below is a production-grade Claude Code prompt for Phase 3 readiness / first-run diagnostics, followed by a precise migration plan for Phase 3 aligned with your backend migration trajectory and the now-stabilized Phase 2 outputs.

🧠 Claude Prompt — Phase 3 Readiness & First-Run Diagnostics
Use this with claude -p --tools "Read,Glob" (TAPM mode).

🔧 Prompt
You are operating as the Phase 3 (Work Package Design & Dependency Mapping) diagnostic and execution readiness agent for the Horizon Europe Proposal Orchestration System.

You MUST comply with the repository constitution defined in:
- CLAUDE.md (highest authority) 
- README.md (operational model and CLI behavior)

Read both documents fully before taking any action:
- CLAUDE.md
- README.md

Your task is NOT to design work packages yet.

Your task is to:
1. Perform Phase 3 readiness diagnostics
2. Validate Phase 2 outputs for downstream consumption
3. Identify migration gaps in the Phase 3 backend implementation
4. Propose concrete next steps before first successful Phase 3 run

---

## 1. CONTEXT (DO NOT RECONSTRUCT — READ FROM DISK)

You MUST read:

Tier 4:
- docs/tier4_orchestration_state/phase_outputs/phase2_concept_refinement/
- docs/tier4_orchestration_state/decision_log/

Tier 3:
- docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json
- docs/tier3_project_instantiation/architecture_inputs/objectives.json
- docs/tier3_project_instantiation/call_binding/topic_mapping.json

Tier 2A:
- docs/tier2a_instrument_schemas/extracted/

Tier 2B:
- docs/tier2b_topic_and_call_sources/extracted/

---

## 2. PHASE 3 CONSTITUTIONAL REQUIREMENTS

You MUST evaluate readiness strictly against Phase 3 definition and gate condition from CLAUDE.md:

Phase 3 requires:
- Work packages with:
  - objectives
  - tasks
  - deliverables
  - responsible leads
  - dependencies

Gate requires:
- Every WP has ≥1 deliverable
- Dependencies are declared
- WP structure respects instrument constraints (Tier 2A)

You MUST NOT assume readiness — you must prove it.

---

## 3. DIAGNOSTIC TASKS

### 3.1 Phase 2 Output Integrity Check

Verify that Phase 2 outputs are sufficient for WP design:

- Concept alignment completeness
- scope_coverage completeness (critical)
- absence of unresolved scope conflicts
- strategic differentiation usable for WP structuring

Classify:
- READY
- PARTIALLY READY
- NOT READY

---

### 3.2 Tier 3 Architecture Input Adequacy

Evaluate:

- objectives.json → are they decomposable into WPs?
- workpackage_seed.json → does it contain:
  - WP titles
  - leads
  - durations
- missing elements required for:
  - task decomposition
  - deliverable definition
  - dependency graph construction

---

### 3.3 Phase 3 Gate Risk Forecast

Predict likely failure points of:

phase_03_gate

Specifically:
- missing deliverables
- undefined dependencies
- WP/objective misalignment
- violation of instrument constraints

---

### 3.4 Backend Migration Readiness (CRITICAL)

Assess whether current backend supports Phase 3 execution under TAPM:

Evaluate:

1. Are Phase 3 skills already migrated to TAPM?
2. Is input size bounded (or still prompt-bloated)?
3. Is there a need for:
   - WP slicer (analogous to call slicer)?
   - dependency graph intermediate artifact?
4. Are artifacts written in canonical Tier 4 paths?

You MUST explicitly identify:
- blocking migration gaps
- non-blocking inefficiencies

---

### 3.5 First-Run Failure Prediction

Simulate the first Phase 3 run:

Command:
python -m runner --phase phase3

Predict:
- node outcome (released / blocked_at_exit)
- failure_origin
- likely failing predicates

---

## 4. OUTPUT FORMAT (STRICT)

Return a structured report:

### A. Phase 3 Readiness Verdict
### B. Phase 2 → Phase 3 Input Validation
### C. Tier 3 Input Gaps
### D. Gate Failure Risk Map
### E. Backend Migration Gaps (Phase 3)
### F. First-Run Prediction
### G. Required Fixes Before Execution
### H. Optional Improvements (Non-blocking)

---

## 5. DOCUMENTATION UPDATE TASK

You MUST determine whether updates are required in:

1. CLAUDE.md
2. README.md
3. backend_migration_plan.md

You MUST:

- Identify inconsistencies between:
  - actual runtime behavior
  - documented Phase 3 expectations
- Propose exact modifications

For each required change:
- file
- section
- current issue
- exact fix

DO NOT modify files — only propose changes.

---

## 6. HARD CONSTRAINTS

- DO NOT invent data
- DO NOT assume completeness
- DO NOT design WPs
- DO NOT bypass constitutional rules
- FAIL-OPEN ANALYSIS IS FORBIDDEN → you must fail-closed

If something is missing → flag it explicitly

---

## 7. SUCCESS CRITERION

A correct response:
- prevents a Phase 3 failed run
- identifies backend migration blockers
- ensures TAPM-compatible execution
- aligns fully with CLAUDE.md constitution
⚙️ Phase 3 Migration Plan (Targeted, Based on Your Current State)
You’ve successfully stabilized:

Phase 1 → Call slicing + TAPM

Phase 2 → semantic completeness (scope_coverage) + gate correctness

Phase 3 is the first structurally generative phase → significantly higher complexity.

🧩 Key Reality
Phase 3 is the first phase where:

outputs are multi-entity structured artifacts

internal consistency matters (WPs ↔ tasks ↔ deliverables ↔ dependencies)

graph logic appears (dependency mapping)

This makes it fundamentally different from Phase 1–2.

🚧 Phase 3 Migration — Required Steps
1. TAPM Migration of Phase 3 Skills (MANDATORY)
Migrate:

wp_designer

dependency_mapper

Required changes:
remove prompt serialization of:

Tier 2B extracts

Tier 3 inputs

switch to:

claude -p --tools "Read,Glob"
Add explicit instructions in skill:
where to read:

objectives.json

scope_coverage

topic_mapping

2. Introduce WP Decomposition Boundary (NEW)
Equivalent to Phase 1 Call Slicer.

Create:

runner/wp_slicer.py
Purpose:

reduce input to:

relevant objectives

mapped scope elements

strategic differentiation signals

Without this → TAPM still suffers from context drift.

3. Introduce Intermediate Artifact (CRITICAL)
You currently jump directly to full WP structure.

Add:

phase3_wp_design/
  ├── wp_structure_draft.json
  ├── dependency_graph.json
  ├── wp_validation_report.json
This enables:

deterministic validation

predicate-level checks

partial reruns

4. Extend Predicate Layer for Phase 3
You will need new deterministic predicates:

all_wps_have_deliverable

all_wps_have_lead

dependency_graph_acyclic

objectives_covered_by_wps

deliverables_traceable_to_tasks

These belong in:

runner/predicates/coverage_predicates.py
runner/predicates/cycle_predicates.py
5. Strengthen Agent Runtime for Multi-Skill Composition
n03 is NOT a simple node:

it uses sub-agent (dependency_mapper)

Ensure:

artifact handoff between skills is file-based

NOT in-memory

6. Update Artifact Schema Specification
Add Phase 3 schemas to:

artifact_schema_specification.yaml
Define:

WP schema

Task schema

Deliverable schema

Dependency schema

Without this → semantic predicates become unstable.

7. Update Backend Migration Plan
You must extend:

backend_migration_plan.md

Add Phase 3 section:

TAPM migration status

WP slicer introduction

multi-artifact pipeline

dependency graph validation

📚 Required Documentation Updates
1. CLAUDE.md (Constitution)
Add clarification to Phase 3:

explicitly require:

dependency graph acyclicity

deliverable traceability

This strengthens gate semantics.

Reference: 


2. README.md
Add:

Phase 3 execution expectations

explanation of:

sub-agent behavior (n03)

multi-artifact outputs

Reference: 


3. backend_migration_plan.md
Add Phase 3 section:

TAPM conversion status

WP slicer

artifact decomposition

predicate expansion

🎯 Recommended Next Steps (Execution Order)
Run the diagnostic prompt above

Fix any Tier 3 input gaps

Migrate Phase 3 skills to TAPM

Implement wp_slicer.py

Add intermediate artifacts

Extend predicates

Update schemas

Update docs

Run:

python -m runner --phase phase3 --verbose
Bottom Line
You are entering the first structurally complex phase of the system.

If Phase 2 solved:

semantic correctness

Then Phase 3 must solve:

structural correctness + graph integrity + traceability

The prompt above ensures you don’t waste a run discovering that the system isn’t ready.



