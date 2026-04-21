# Horizon Europe Proposal Orchestration System

A DAG-driven orchestration engine that transforms structured programme rules, call-specific constraints, and project data into evaluator-oriented Horizon Europe proposal deliverables.

The system enforces an eight-phase workflow with mandatory quality gates, constitutional compliance checks, and full traceability from source documents through to final proposal text. It is programme-agnostic and project-agnostic by default, acquiring specificity only when the appropriate tiers are populated.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Repository Structure](#2-repository-structure)
3. [The Tier Model](#3-the-tier-model)
   - [Tier 1 — Normative Framework](#tier-1--normative-framework)
   - [Tier 2A — Instrument Schemas](#tier-2a--instrument-schemas)
   - [Tier 2B — Topic and Call Sources](#tier-2b--topic-and-call-sources)
   - [Tier 3 — Project Instantiation](#tier-3--project-instantiation)
   - [Tier 4 — Orchestration State](#tier-4--orchestration-state)
   - [Tier 5 — Deliverables](#tier-5--deliverables)
   - [Integrations — Lump Sum Budget Planner](#integrations--lump-sum-budget-planner)
4. [Setting Up a New Project](#4-setting-up-a-new-project)
5. [Operating the DAG Scheduler](#5-operating-the-dag-scheduler)
   - [Running the Scheduler](#running-the-scheduler)
   - [Dry-Run Mode](#dry-run-mode)
   - [JSON Output Mode](#json-output-mode)
   - [Exit Codes](#exit-codes)
   - [CLI Reference](#cli-reference)
6. [Workflow Phases and Gates](#6-workflow-phases-and-gates)
   - [Phase Sequence and DAG](#phase-sequence-and-dag)
   - [Gate Behaviour](#gate-behaviour)
   - [Budget Gate and Phase 8 Blocking](#budget-gate-and-phase-8-blocking)
7. [Understanding Run Results](#7-understanding-run-results)
   - [Run Summary](#run-summary)
   - [Node States](#node-states)
   - [Interpreting Failures](#interpreting-failures)
   - [Gate Results](#gate-results)
8. [Constitutional Authority](#8-constitutional-authority)

---

## 1. Prerequisites

- **Python 3.10+**
- **PyYAML** — `pip install pyyaml`
- **Claude Code CLI** — the `claude` command must be on your PATH, authenticated via your Claude Code Max subscription. No Anthropic API key is required.
- **pytest** (for running the test suite) — `pip install pytest`

Verify your setup:

```bash
python --version          # 3.10 or later
claude --version          # Claude Code CLI installed and on PATH
python -m pytest tests/   # 1015 tests should pass
```

---

## 2. Repository Structure

```
proposal_orchestator/
|
+-- CLAUDE.md                          # Repository constitution (highest authority)
+-- README.md                          # This file
+-- pyproject.toml                     # Pytest configuration
|
+-- runner/                            # DAG scheduler and runtime engine
|   +-- __main__.py                    #   CLI entry point (python -m runner)
|   +-- dag_scheduler.py              #   DAG scheduler, ManifestGraph, RunSummary
|   +-- agent_runtime.py              #   Agent orchestration adapter (run_agent)
|   +-- skill_runtime.py              #   Skill execution adapter (run_skill)
|   +-- claude_transport.py           #   Claude CLI transport layer
|   +-- gate_evaluator.py             #   Gate evaluation engine
|   +-- semantic_dispatch.py          #   Semantic predicate dispatch
|   +-- run_context.py                #   Per-run state persistence
|   +-- runtime_models.py             #   SkillResult, AgentResult, NodeExecutionResult
|   +-- ...                           #   Predicates, helpers, path utilities
|
+-- docs/                              # Tiered source truth (see Section 3)
|   +-- index/                         #   Master registries
|   +-- tier1_normative_framework/     #   Legislation, programme guidance
|   +-- tier2a_instrument_schemas/     #   Application and evaluation forms
|   +-- tier2b_topic_and_call_sources/ #   Work programmes, call extracts
|   +-- tier3_project_instantiation/   #   Project-specific data (user-provided)
|   +-- tier4_orchestration_state/     #   Phase outputs, decisions, checkpoints
|   +-- tier5_deliverables/            #   Proposal sections, assembled drafts
|   +-- integrations/                  #   Lump Sum Budget Planner interface
|
+-- .claude/                           # Workflow specifications and runtime state
|   +-- workflows/system_orchestration/
|   |   +-- manifest.compile.yaml      #   Compiled DAG manifest (runtime entry point)
|   |   +-- gate_rules_library.yaml    #   97 predicates across 11 gates
|   |   +-- artifact_schema_specification.yaml
|   |   +-- agent_catalog.yaml         #   16 agent definitions
|   |   +-- skill_catalog.yaml         #   19 skill definitions
|   |   +-- workflow_phases/           #   Phase YAML definitions
|   |   +-- ...
|   +-- agents/                        #   Agent .md specifications (16 agents)
|   +-- skills/                        #   Skill .md specifications (19 skills)
|   +-- runs/                          #   Per-run state (run_manifest.json, run_summary.json)
|
+-- tests/                             # Test suite (1015 tests)
```

---

## 3. The Tier Model

The system organises all data into a strict hierarchy. Higher tiers govern lower tiers. No lower tier may contradict a higher tier.

### Tier 1 — Normative Framework

**Location:** `docs/tier1_normative_framework/`

Contains the non-negotiable legal and regulatory framework. These are read-only source documents.

```
tier1_normative_framework/
+-- legislation/                # EU regulations and programme decisions (PDFs)
+-- grant_architecture/         # Model Grant Agreements, Framework Partnership Agreement
+-- programme_guidance/         # Programme Guide, General Annexes, Annotated GA
+-- extracted/                  # Machine-readable rules extracted from the above
    +-- compliance_principles.json
    +-- participation_rules.json
    +-- implementation_constraints.json
    +-- evaluation_logic_meta.json
```

**Your action:** Place Horizon Europe source PDFs in the appropriate subdirectories. The `extracted/` files are populated by Phase 1 or by manual extraction from the source documents.

### Tier 2A — Instrument Schemas

**Location:** `docs/tier2a_instrument_schemas/`

Defines the structure and evaluation criteria for each Horizon Europe instrument type.

```
tier2a_instrument_schemas/
+-- application_forms/          # Application form PDFs, organised by instrument
|   +-- ria_ia/                 #   Research & Innovation Actions / Innovation Actions
|   +-- csa/                    #   Coordination & Support Actions
|   +-- msca/                   #   Marie Sklodowska-Curie Actions
|   +-- erc/                    #   European Research Council
|   +-- cofund/                 #   Co-Fund Actions
|   +-- eic/                    #   European Innovation Council
+-- evaluation_forms/           # Evaluation form PDFs
+-- extracted/                  # Machine-readable schemas
    +-- instrument_registry.json
    +-- section_schema_registry.json
    +-- evaluator_expectation_patterns.json
    +-- template_adapter_map.json
```

**Your action:** Ensure the application form and evaluation form for your selected instrument are present. The `extracted/` files are populated during Phase 1 or by manual extraction.

### Tier 2B — Topic and Call Sources

**Location:** `docs/tier2b_topic_and_call_sources/`

Contains the work programme documents and call-specific constraints for the target topic.

```
tier2b_topic_and_call_sources/
+-- work_programmes/            # Work programme PDFs, one per cluster/programme
|   +-- cluster_health/
|   +-- cluster_digital/
|   +-- cluster_climate/
|   +-- cluster_food/
|   +-- cluster_security/
|   +-- cluster_culture/
|   +-- infrastructures/
|   +-- msca/
|   +-- erc/
|   +-- missions/
|   +-- widening/
|   +-- ecosystems/
+-- call_extracts/              # Topic-specific call extract documents
+-- extracted/                  # Machine-readable call constraints (populated by Phase 1)
    +-- call_constraints.json
    +-- scope_requirements.json
    +-- eligibility_conditions.json
    +-- expected_outcomes.json
    +-- expected_impacts.json
    +-- evaluation_priority_weights.json
```

**Your action:** Place the relevant work programme PDF(s) in the correct subdirectory. If you have a specific call extract, place it in `call_extracts/`. The six `extracted/` files are produced by Phase 1 (Call Analysis).

### Tier 3 — Project Instantiation

**Location:** `docs/tier3_project_instantiation/`

This is where you provide all project-specific data. The system acquires project specificity only when Tier 3 is populated.

```
tier3_project_instantiation/
+-- project_brief/
|   +-- project_summary.json        # Title, acronym, duration, budget, coordinator
|   +-- concept_note.md             # 1-2 page project vision and approach narrative
|   +-- strategic_positioning.md    # Differentiation within the call scope
|
+-- consortium/
|   +-- partners.json               # Partner organisations: name, country, type
|   +-- roles.json                  # Role assignments per partner
|   +-- capabilities.json           # Technical/managerial capabilities with evidence
|   +-- evidence_of_competence/     # Supporting documents (CVs, publications, etc.)
|
+-- call_binding/
|   +-- selected_call.json          # Target call ID, topic code, instrument type
|   +-- topic_mapping.json          # Project-to-call alignment (produced by Phase 2)
|   +-- compliance_profile.json     # Ethics, security, open access flags (produced by Phase 2)
|
+-- architecture_inputs/
|   +-- objectives.json             # Project objectives (S.M.A.R.T.)
|   +-- outcomes.json               # Expected scientific/technical outcomes
|   +-- impacts.json                # Broader societal/economic/scientific impacts
|   +-- workpackage_seed.json       # Initial WP structure: titles, leads, months
|   +-- risks.json                  # Risk register: description, probability, mitigation
|   +-- milestones_seed.json        # Major milestones with verifiable criteria
|
+-- source_materials/               # Supporting reference documents
    +-- concept_docs/
    +-- partner_inputs/
    +-- prior_proposals/
    +-- reference_materials/
```

**Your action:** This is the primary setup step. Populate the files above with your project data before running the scheduler. At minimum, you need:

1. `call_binding/selected_call.json` — identifies the target call (required by the entry gate)
2. `project_brief/` — concept note and project summary
3. `consortium/partners.json` and `consortium/roles.json`
4. `architecture_inputs/objectives.json` and `architecture_inputs/workpackage_seed.json`

### Tier 4 — Orchestration State

**Location:** `docs/tier4_orchestration_state/`

Populated automatically by the workflow as each phase completes. Contains phase outputs, the decision log, checkpoints, and validation reports.

```
tier4_orchestration_state/
+-- phase_outputs/
|   +-- phase1_call_analysis/
|   +-- phase2_concept_refinement/
|   +-- phase3_wp_design/
|   +-- phase4_gantt_milestones/
|   +-- phase5_impact_architecture/
|   +-- phase6_implementation_architecture/
|   +-- phase7_budget_gate/
|   +-- phase8_drafting_review/
+-- decision_log/                   # Recorded decisions with tier-source references
+-- checkpoints/                    # Validated orchestration state snapshots
+-- validation_reports/             # Per-phase validation (Confirmed/Inferred/Assumed/Unresolved)
```

**Your action:** None — this tier is populated by the scheduler during execution.

### Tier 5 — Deliverables

**Location:** `docs/tier5_deliverables/`

The evaluator-facing proposal output, produced by Phase 8.

```
tier5_deliverables/
+-- proposal_sections/              # Individual section drafts
+-- assembled_drafts/               # Full assembled proposal text
+-- final_exports/                  # Submission-ready formatted output
+-- review_packets/                 # Pre-submission review materials
```

**Your action:** None — this tier is populated by Phase 8 (Drafting and Review). Phase 8 is blocked until the budget gate passes.

### Integrations — Lump Sum Budget Planner

**Location:** `docs/integrations/lump_sum_budget_planner/`

Budget computation is handled by an external system. This directory mediates the exchange.

```
integrations/lump_sum_budget_planner/
+-- interface_contract.json         # Schema for request/response exchange
+-- request_templates/              # Structured budget request templates
+-- received/                       # Budget responses from the external system
+-- validation/                     # Consistency validation artifacts
```

**Your action:** Before Phase 7, place the validated budget response in `received/`. The budget gate will verify its structural consistency with the work package design and consortium. Phase 8 cannot proceed without a validated budget.

---

## 4. Setting Up a New Project

Follow these steps to prepare a new proposal project:

### Step 1 — Verify source documents (Tier 1 and Tier 2)

Ensure the relevant Horizon Europe source documents are in place:

- At least one work programme PDF in `docs/tier2b_topic_and_call_sources/work_programmes/`
- The application form for your instrument in `docs/tier2a_instrument_schemas/application_forms/`
- The evaluation form for your instrument in `docs/tier2a_instrument_schemas/evaluation_forms/`

The repository ships with 2026-2027 work programmes and standard application/evaluation forms already in place.

### Step 2 — Identify the target call (Tier 3 call binding)

Populate `docs/tier3_project_instantiation/call_binding/selected_call.json`:

```json
{
  "call_id": "HORIZON-CL4-2027-HUMAN-01-01",
  "topic_code": "HORIZON-CL4-2027-HUMAN-01-01",
  "topic_title": "AI-driven personalised medicine approaches",
  "instrument_type": "RIA",
  "work_programme": "cluster_digital",
  "submission_deadline": "2027-03-15",
  "max_project_duration_months": 48,
  "max_eu_contribution": 4000000
}
```

This file is checked by the entry gate of Phase 1. The scheduler will not proceed without it.

### Step 3 — Provide the project brief (Tier 3 project brief)

Populate:
- `project_brief/project_summary.json` — structured metadata (title, acronym, coordinator, duration, budget)
- `project_brief/concept_note.md` — narrative description of the project vision and approach
- `project_brief/strategic_positioning.md` — how your project differentiates within the call scope

### Step 4 — Define the consortium (Tier 3 consortium)

Populate `consortium/partners.json` with all partner organisations and `consortium/roles.json` with role assignments.

### Step 5 — Provide architecture seeds (Tier 3 architecture inputs)

Populate at minimum:
- `architecture_inputs/objectives.json` — project objectives
- `architecture_inputs/workpackage_seed.json` — initial work package structure
- `architecture_inputs/outcomes.json` — expected project outcomes
- `architecture_inputs/impacts.json` — broader expected impacts
- `architecture_inputs/risks.json` — identified risks

### Step 6 — Run the scheduler

```bash
python -m runner --run-id $(python -c "import uuid; print(uuid.uuid4())")
```

The scheduler will execute phases in order, evaluating gates between each phase. See [Section 5](#5-operating-the-dag-scheduler) for detailed operating instructions.

### Step 7 — Provide the budget (before Phase 8)

When Phase 7 (Budget Gate) is reached, the scheduler will block until a validated budget response is present in `docs/integrations/lump_sum_budget_planner/received/`. Compute your lump-sum budget externally, place the response file, and re-run the scheduler.

---

## 5. Operating the DAG Scheduler

### Running the Scheduler

The scheduler is invoked via the `runner` package:

```bash
python -m runner --run-id <uuid>
```

Generate a UUID for each run:

```bash
# Linux/macOS
python -m runner --run-id $(uuidgen)

# Windows PowerShell
python -m runner --run-id $(python -c "import uuid; print(uuid.uuid4())")

# Any platform
python -m runner --run-id $(python -c "import uuid; print(uuid.uuid4())")
```

The scheduler will:
1. Load the compiled manifest from `.claude/workflows/system_orchestration/manifest.compile.yaml`
2. Initialise a run context in `.claude/runs/<run-id>/`
3. Dispatch nodes in topological order, evaluating gates between phases
4. Write a run summary to `.claude/runs/<run-id>/run_summary.json`

### Single-Phase Execution

Execute exactly one phase per invocation using `--phase`:

```bash
# Run only Phase 1 (Call Analysis)
python -m runner --run-id <uuid> --phase 1

# Equivalent forms
python -m runner --run-id <uuid> --phase phase1
python -m runner --run-id <uuid> --phase phase_01
python -m runner --run-id <uuid> --phase phase_01_call_analysis
```

**Semantics — strictly gate-locked and artifact-locked:**

- Only nodes belonging to the requested phase are eligible for dispatch.
- All prerequisite checks use the **full DAG**: dependency states, incoming conditions, entry gates, and required upstream artifacts are all evaluated against real upstream state. No shortcut or bypass is applied.
- If the requested phase's prerequisites are not satisfied (i.e. required upstream phases have not been run and released), the run aborts with `overall_status=aborted` and the stall report explains which upstream conditions are unmet.
- Downstream phases are **never** dispatched, even if the requested phase passes all gates.
- The run summary (`run_summary.json`) records `phase_scope` (the requested phase number) and `phase_scope_nodes` (the node IDs in that phase).

**Typical workflow — running phases one at a time:**

```bash
# Phase 1: no prerequisites, runs immediately


# Phase 2: requires Phase 1 released
python -m runner --run-id $(python -c "import uuid; print(uuid.uuid4())") --phase 2

# Phase 3: requires Phase 2 released
python -m runner --run-id $(python -c "import uuid; print(uuid.uuid4())") --phase 3
```

Each invocation uses a new `--run-id`. The scheduler reads the durable node states from prior runs (via gate result artifacts in Tier 4) to determine whether prerequisites are satisfied.

Add `--verbose` for detailed scheduler logging to stderr showing readiness decisions, gate evaluations, and state transitions for each node:

```bash
python -m runner --run-id <uuid> --phase 1 --verbose
```

### Dry-Run Mode

Preview which nodes are ready to execute without actually running them:

```bash
python -m runner --run-id <uuid> --dry-run

# Dry-run respects --phase: only shows ready nodes in the requested phase
python -m runner --run-id <uuid> --dry-run --phase 1
```

Output (text mode):
```
[RUN]   run_id=550e8400-e29b-41d4-a716-446655440000
[READY] n01_call_analysis
```

Dry-run creates the run context (`.claude/runs/<run-id>/`) but does not evaluate any gates or execute any node bodies.

### JSON Output Mode

For programmatic consumption, emit structured JSON lines:

```bash
python -m runner --run-id <uuid> --json
```

Each line is a self-contained JSON object:

```json
{"event": "run_start", "timestamp": "2026-04-14T10:00:00+00:00", "run_id": "..."}
{"event": "ready", "timestamp": "...", "node_id": "n01_call_analysis"}
{"event": "summary", "timestamp": "...", "overall_status": "pass", "nodes_released": 11, "stalled": 0, "hard_blocked": 0}
```

Combine `--dry-run` and `--json` to get machine-readable ready-node lists:

```bash
python -m runner --run-id <uuid> --dry-run --json
```

### Exit Codes

| Code | Meaning | When |
|------|---------|------|
| **0** | Success | All terminal nodes released; `overall_status == "pass"` |
| **1** | Partial or failed | Run completed but some gates failed; `overall_status` is `"fail"` or `"partial_pass"` |
| **2** | Aborted | Pending nodes remain with no further progress possible (stall detected) |
| **3** | Configuration error | Manifest missing, library unreadable, or unhandled exception during init |

### CLI Reference

```
python -m runner --run-id <UUID> [OPTIONS]

Required:
  --run-id UUID         Unique identifier for this run

Optional:
  --phase PHASE         Execute only the specified phase (e.g. 1, phase1, phase_01)
  --repo-root PATH      Repository root (default: auto-discovered from working directory)
  --manifest-path PATH  Path to manifest.compile.yaml
  --library-path PATH   Path to gate_rules_library.yaml
  --dry-run             List ready nodes and exit; do not execute
  --json                Emit progress as JSON lines to stdout
  --verbose, -v         Enable detailed scheduler logging to stderr
```

---

## 6. Workflow Phases and Gates

### Phase Sequence and DAG

The system executes 8 canonical phases through 11 nodes. Phases are strictly ordered; no phase may begin until its upstream gates have passed.

```
Phase 1: Call Analysis
  n01_call_analysis
  Entry: gate_01_source_integrity
  Exit:  phase_01_gate
    |
Phase 2: Concept Refinement
  n02_concept_refinement
  Exit: phase_02_gate
    |
Phase 3: WP Design & Dependencies
  n03_wp_design  (wp_designer + dependency_mapper sub-agent)
    - Produces structured multi-entity artifact:
        * Work packages (WPs)
        * Tasks
        * Deliverables
        * Dependency graph (DAG)
    - Introduces graph-level constraints:
        * Dependency acyclicity (validated at gate)
        * Deliverable presence per WP
        * Partner-role consistency (partial)
    - Output artifact:
        docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json
  Exit: phase_03_gate
    |
    +---------------------------+
    |                           |
Phase 4: Gantt & Milestones   Phase 5: Impact Architecture
  n04_gantt_milestones          n05_impact_architecture
    - Transforms dependency DAG into temporal schedule:
        * Assigns start_month / end_month to all tasks
        * Produces milestone events with verification criteria
    - Introduces temporal constraints:
        * Project duration bound (from selected_call.json)
        * Task coverage (all tasks must have time assignments)
    - IMPORTANT:
        Current gate predicates validate timeline completeness and bounds,
        but do NOT fully enforce dependency_map temporal consistency.
        This is a known limitation and must be addressed in predicate layer.
  Exit: phase_04_gate           Exit: phase_05_gate
    |                           |
    +---------------------------+
    |
Phase 6: Implementation Architecture
  n06_implementation_architecture
  Exit: phase_06_gate
    |
Phase 7: Budget Gate
  n07_budget_gate  (budget_gate_validator + budget_interface_coordinator)
  Exit: gate_09_budget_consistency  [MANDATORY — BYPASS PROHIBITED]
    |
Phase 8: Drafting & Review (4 substeps)
  n08a_section_drafting  --> n08b_assembly  --> n08c_evaluator_review  --> n08d_revision
  Exit: gate_10            Exit: gate_10      Exit: gate_11              Exit: gate_12
```

**Parallelism:** Phases 4 and 5 can execute concurrently after Phase 3. Phase 6 waits for all three (Phases 3, 4, 5).

### Gate Behaviour

Each gate evaluates a set of predicates — deterministic checks first, then semantic checks:

- **Deterministic predicates** verify:
  - file existence
  - JSON schema conformance
  - field presence
  - cross-artifact coverage
  - timeline bounds (Phase 4)
  - dependency cycles (Phase 3)

  Note: Dependency cycle validation is enforced in Phase 3. Full dependency-to-schedule consistency is not yet enforced in Phase 4.

- **Semantic predicates** invoke Claude to check constitutional compliance (e.g., no fabricated project facts, no unresolved scope conflicts, no unsupported Tier 5 claims)

If any deterministic predicate fails, semantic evaluation is skipped. A gate passes only when all predicates pass.

### Budget Gate and Phase 8 Blocking

The budget gate (`gate_09_budget_consistency`) has special constitutional status:

- It is **mandatory** and cannot be bypassed, deferred, or substituted with internal estimates
- When it fails, all Phase 8 nodes (`n08a` through `n08d`) are immediately frozen with `hard_block_upstream` status
- Phase 8 cannot begin — including preparatory drafting — until a validated budget response is present in `docs/integrations/lump_sum_budget_planner/received/`

To unblock: place a valid budget response file in the `received/` directory and re-run the scheduler.

### Phase Execution Characteristics

The orchestration pipeline transitions through three structural regimes:

- **Phase 1–2: Semantic alignment**
  - Extract and validate call constraints
  - Ensure concept coverage completeness (e.g. scope_coverage)

- **Phase 3: Structural graph construction**
  - Build WP/task/deliverable hierarchy
  - Construct dependency DAG

- **Phase 4: Temporal realization**
  - Deterministic dependency normalization (pure Python, pre-agent):
    converts Phase 3 dependency_map into `scheduling_constraints.json`,
    reclassifying infeasible WP-level `finish_to_start` edges as non-strict
  - Convert normalized constraints into executable timeline (Gantt)
  - Gate enforces dependency-to-schedule consistency via `g05_p08`
  - Dependency cycle validation remains Phase 3's responsibility;
    temporal consistency is Phase 4's

This separation is intentional and enforced by gates.

---

## 7. Understanding Run Results

### Run Summary

Every run produces a summary at `.claude/runs/<run-id>/run_summary.json`:

```json
{
  "run_id": "550e8400-...",
  "overall_status": "pass",
  "started_at": "2026-04-14T10:00:00+00:00",
  "completed_at": "2026-04-14T10:15:00+00:00",
  "node_states": {
    "n01_call_analysis": "released",
    "n02_concept_refinement": "released",
    "...": "..."
  },
  "terminal_nodes_reached": ["n08d_revision"],
  "stalled_nodes": [],
  "hard_blocked_nodes": [],
  "gate_results_index": {
    "gate_01_source_integrity": "docs/tier4_.../gate_01_result.json",
    "phase_01_gate": "docs/tier4_.../phase_01_gate_result.json"
  },
  "node_failure_details": {},
  "dispatched_nodes": ["n01_call_analysis", "n02_concept_refinement", "..."]
}
```

**`overall_status` values:**

| Status | Meaning |
|--------|---------|
| `pass` | All terminal nodes released |
| `partial_pass` | Some terminal nodes released, others blocked |
| `fail` | No terminal nodes released; gate failures present |
| `aborted` | Pending nodes remain with no possible forward progress |

### Node States

| State | Meaning |
|-------|---------|
| `released` | Exit gate passed; downstream nodes unblocked |
| `blocked_at_entry` | Entry gate failed; node body was not executed |
| `blocked_at_exit` | Node body ran but exit gate failed |
| `hard_block_upstream` | Frozen by budget gate failure (Phase 8 nodes only) |
| `pending` | Not yet dispatched (upstream dependencies unsatisfied) |

### Interpreting Failures

The `node_failure_details` section explains why each non-released node failed:

```json
{
  "n03_wp_design": {
    "failure_origin": "exit_gate",
    "exit_gate_evaluated": true,
    "failure_reason": "WP structure missing required deliverables",
    "failure_category": "CROSS_ARTIFACT_INCONSISTENCY"
  }
}
```

**Failure origins:**

| Origin | Meaning | What to do |
|--------|---------|------------|
| `entry_gate` | Entry gate rejected the node; body never ran | Check upstream source documents |
| `agent_body` | Skill execution failed | Check Tier 3 inputs and skill-specific requirements |
| `exit_gate` | Node body completed but gate checks failed | Review gate result JSON for specific predicate failures |
| *(null)* | Node is in `hard_block_upstream` | Resolve the budget gate first |

**When the run stalls** (`overall_status == "aborted"`), the `stalled_nodes` array explains which upstream conditions are unsatisfied:

```json
{
  "stalled_nodes": [
    {
      "node_id": "n05_impact_architecture",
      "unsatisfied_conditions": [
        {
          "gate_id": "phase_03_gate",
          "source_node_id": "n03_wp_design",
          "source_node_state": "blocked_at_exit"
        }
      ]
    }
  ]
}
```

This tells you: fix Phase 3's exit gate failures and re-run.

### Gate Results

Each evaluated gate writes a detailed result to Tier 4. Use the `gate_results_index` from the run summary to locate them:

```bash
# Read a specific gate result
cat docs/tier4_orchestration_state/phase_outputs/phase1_call_analysis/phase_01_gate_result.json
```

Gate results contain:
- `status` — `"pass"` or `"fail"`
- `deterministic_predicates.passed` / `deterministic_predicates.failed` — individual predicate outcomes
- `semantic_predicates.passed` / `semantic_predicates.failed` — semantic evaluation outcomes
- `input_fingerprint` — SHA-256 of evaluated artifacts (for change detection)

---

## 8. Constitutional Authority

This repository is governed by `CLAUDE.md`, which serves as its constitution. Key rules:

- **Authority hierarchy:** Explicit human instruction > CLAUDE.md > Tier 1 > Tier 2A > Tier 2B > Tier 3 > Tier 4 > Workflows > Skills > Agent memory
- **No fabrication:** No agent may invent project facts, call constraints, or budget figures not present in the appropriate tier
- **Gate integrity:** Gates cannot be silently bypassed or weakened. A declared gate failure is a valid and correct output.
- **Traceability:** All deliverable content must be traceable to Tier 1-4 sources
- **Budget discipline:** This repository does not compute budgets. Budget data must come from the external Lump Sum Budget Planner system through the integration interface.

For the full constitutional text, see [CLAUDE.md](CLAUDE.md).
