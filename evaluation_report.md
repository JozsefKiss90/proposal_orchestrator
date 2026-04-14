 Repository Readiness Evaluation

  1. Verdict

  The orchestration engine is structurally complete and execution-ready. Source data population is the sole remaining prerequisite for live testing.

  The runtime stack, workflow specification, agent definitions, skill definitions, gate library, and test suite are all complete, internally consistent, and passing. No code changes are required. 
  What remains is populating the tiered source documents that the engine operates on.

  ---
  2. Engine Readiness — PASS

  ┌─────────────────┬───────────────────┬────────────────────────────────────────────────────────────────────────────────────┐
  │    Component    │      Status       │                                       Detail                                       │
  ├─────────────────┼───────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ Test suite      │ 988/988 pass      │ 772 existing + 216 new (Steps 8–9)                                                 │
  ├─────────────────┼───────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ Module imports  │ All succeed       │ 10 core modules, zero circular dependencies                                        │
  ├─────────────────┼───────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ CLI entry point │ Operational       │ python -m runner --run-id X --dry-run boots and reports n01_call_analysis as ready │
  ├─────────────────┼───────────────────┼────────────────────────────────────────────────────────────────────────────────────┤
  │ Anthropic SDK   │ v0.88.0 installed │ ANTHROPIC_API_KEY not yet set — required for live runs                             │
  └─────────────────┴───────────────────┴────────────────────────────────────────────────────────────────────────────────────┘

  Runtime Stack (6,092 lines)

  ┌───────────────────┬──────────────────────┬───────┬───────────────────────────────────────────────────┐
  │       Layer       │        Module        │ Lines │                      Status                       │
  ├───────────────────┼──────────────────────┼───────┼───────────────────────────────────────────────────┤
  │ Data contracts    │ runtime_models.py    │ 218   │ Frozen dataclasses, 3 constant sets               │
  ├───────────────────┼──────────────────────┼───────┼───────────────────────────────────────────────────┤
  │ Node resolution   │ node_resolver.py     │ 215   │ Manifest → agent/skill/phase mapping              │
  ├───────────────────┼──────────────────────┼───────┼───────────────────────────────────────────────────┤
  │ Skill runtime     │ skill_runtime.py     │ 813   │ Claude API adapter, atomic writes                 │
  ├───────────────────┼──────────────────────┼───────┼───────────────────────────────────────────────────┤
  │ Agent runtime     │ agent_runtime.py     │ 946   │ Skill sequencing, sub-agent/pre-gate coordination │
  ├───────────────────┼──────────────────────┼───────┼───────────────────────────────────────────────────┤
  │ DAG scheduler     │ dag_scheduler.py     │ 1,310 │ 11-node DAG, 5-step dispatch contract             │
  ├───────────────────┼──────────────────────┼───────┼───────────────────────────────────────────────────┤
  │ Gate evaluator    │ gate_evaluator.py    │ 692   │ 59 predicates, semantic dispatch                  │
  ├───────────────────┼──────────────────────┼───────┼───────────────────────────────────────────────────┤
  │ Run context       │ run_context.py       │ 339   │ State persistence, HARD_BLOCK propagation         │
  ├───────────────────┼──────────────────────┼───────┼───────────────────────────────────────────────────┤
  │ Semantic dispatch │ semantic_dispatch.py │ 607   │ Claude-backed semantic predicates                 │
  ├───────────────────┼──────────────────────┼───────┼───────────────────────────────────────────────────┤
  │ CLI               │ __main__.py          │ 198   │ Exit codes 0/1/2/3, --dry-run, --json             │
  └───────────────────┴──────────────────────┴───────┴───────────────────────────────────────────────────┘

  Workflow Specification

  ┌────────────────────┬────────────────────────────────┬─────────────────────────────────────────────────────────┐
  │      Artifact      │             Count              │                        Integrity                        │
  ├────────────────────┼────────────────────────────────┼─────────────────────────────────────────────────────────┤
  │ Manifest nodes     │ 11                             │ All have agent, skills, phase_id, exit_gate             │
  ├────────────────────┼────────────────────────────────┼─────────────────────────────────────────────────────────┤
  │ Manifest edges     │ 13                             │ Acyclic DAG, single entry (n01), single terminal (n08d) │
  ├────────────────────┼────────────────────────────────┼─────────────────────────────────────────────────────────┤
  │ Manifest artifacts │ 27                             │ All with path, tier, produced_by                        │
  ├────────────────────┼────────────────────────────────┼─────────────────────────────────────────────────────────┤
  │ Gate rules         │ 11 gates, 98 predicates        │ All manifest-referenced gates defined                   │
  ├────────────────────┼────────────────────────────────┼─────────────────────────────────────────────────────────┤
  │ Agent catalog      │ 16 agents                      │ All 12 manifest-bound agents + 4 utility agents         │
  ├────────────────────┼────────────────────────────────┼─────────────────────────────────────────────────────────┤
  │ Skill catalog      │ 19 skills                      │ All manifest-referenced skills defined                  │
  ├────────────────────┼────────────────────────────────┼─────────────────────────────────────────────────────────┤
  │ Artifact schemas   │ 15 schemas, 25 canonical paths │ All with schema_id_value and required fields            │
  └────────────────────┴────────────────────────────────┴─────────────────────────────────────────────────────────┘

  Agent & Skill Definitions (13,144 lines of specification)

  ┌───────────────────┬───────┬───────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │     Category      │ Files │ Lines │                                                Completeness                                                │
  ├───────────────────┼───────┼───────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Agent definitions │ 16    │ 4,194 │ All have: identity, scope, canonical I/O, skills, gate awareness, failure behaviour, constitutional review │
  ├───────────────────┼───────┼───────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Prompt specs      │ 16    │ 3,570 │ 1:1 match with agent definitions                                                                           │
  ├───────────────────┼───────┼───────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Skill definitions │ 19    │ 5,380 │ All have: canonical I/O, execution spec, constraints, failure protocol (5 categories), schema validation   │
  ├───────────────────┼───────┼───────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ Contracts         │ 2     │ 288   │ node_body_contract.md, skill_runtime_contract.md                                                           │
  └───────────────────┴───────┴───────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  Cross-reference: zero orphans, zero gaps. Every manifest node resolves to an agent, every agent has a prompt spec, every agent's skills resolve to skill definitions.

  ---
  3. Source Data Population — BLOCKING

  This is where live testing is blocked. The engine is ready; the data is not.

  What is populated (source documents present)

  ┌──────────────────────────────┬──────────────────────────────────────────────────────────┬───────┬─────────────┐
  │             Tier             │                         Content                          │ Files │    Size     │
  ├──────────────────────────────┼──────────────────────────────────────────────────────────┼───────┼─────────────┤
  │ Tier 1 — Normative           │ Legislation, programme guidance, grant architecture PDFs │ 10    │ ~20 MB      │
  ├──────────────────────────────┼──────────────────────────────────────────────────────────┼───────┼─────────────┤
  │ Tier 2A — Instrument schemas │ Application form PDFs (RIA/IA, MSCA, ERC, CSA, COFUND)   │ 12    │ substantial │
  ├──────────────────────────────┼──────────────────────────────────────────────────────────┼───────┼─────────────┤
  │ Tier 2A — Evaluation forms   │ Evaluation form PDFs (RIA/IA, CSA, MSCA)                 │ 3     │ partial     │
  ├──────────────────────────────┼──────────────────────────────────────────────────────────┼───────┼─────────────┤
  │ Tier 2B — Work programmes    │ All 12 Horizon Europe cluster work programmes 2026–2027  │ 12    │ ~24 MB      │
  ├──────────────────────────────┼──────────────────────────────────────────────────────────┼───────┼─────────────┤
  │ Integration reference        │ Lump sum grant management guide                          │ 1     │ 307K        │
  └──────────────────────────────┴──────────────────────────────────────────────────────────┴───────┴─────────────┘

  What is empty (all {} stubs)

  ┌────────────────────────┬──────────────────────┬───────────────────────────────────────────────────────────────────────┐
  │          Tier          │     Empty files      │                                Impact                                 │
  ├────────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────┤
  │ Tier 1 extracted/      │ 4 JSON stubs         │ No extracted rules for compliance checking                            │
  ├────────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────┤
  │ Tier 2A extracted/     │ 4 JSON stubs         │ No section schemas or evaluator expectations                          │
  ├────────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────┤
  │ Tier 2B extracted/     │ 6 JSON stubs         │ Blocks Phase 1 gate — no call constraints, expected outcomes, impacts │
  ├────────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────┤
  │ Tier 2B call_extracts/ │ 0 files              │ No topic-specific call extracts                                       │
  ├────────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────┤
  │ Tier 3 (all)           │ 18 JSON + 2 MD stubs │ Blocks Phase 2+ gates — no project data whatsoever                    │
  ├────────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────┤
  │ Tier 4 (all)           │ 0 files              │ Empty (expected — populated by orchestration)                         │
  ├────────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────┤
  │ Tier 5 (all)           │ 0 files              │ Empty (expected — populated by orchestration)                         │
  ├────────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────┤
  │ Integration contract   │ 1 JSON stub          │ Blocks Phase 7 gate — no budget interface                             │
  ├────────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────┤
  │ Index registries       │ 5 JSON stubs         │ No master indices                                                     │
  └────────────────────────┴──────────────────────┴───────────────────────────────────────────────────────────────────────┘

  Gate cascade analysis

  The system will fail at the very first gate:

  gate_01_source_integrity (entry gate for n01)
    → requires non-empty files in docs/tier2b_topic_and_call_sources/
    → WILL PASS (work programme PDFs are present)

  phase_01_gate (exit gate for n01)
    → requires populated docs/tier2b_topic_and_call_sources/extracted/ JSONs
    → WILL FAIL (all 6 extracted files are {} stubs)
    → n01 blocks at exit → n02–n08d all stall → RunAbortedError

  Even if Phase 1 were manually satisfied, Phase 2 requires Tier 3 project data (concept_note.md, project_summary.json), and Phase 7 requires a validated budget response — both completely empty.  

  ---
  4. Path to Live Testing

  Minimum viable population (in dependency order)

  Step A — Select a target call and populate Tier 3 call binding:
  - docs/tier3_project_instantiation/call_binding/selected_call.json — identify cluster, topic ID, instrument type, call deadline
  - This is the seed from which all call-specific extraction flows

  Step B — Extract Tier 2B call data (Phase 1 input):
  - Populate the 6 extracted/ JSON files from the relevant work programme PDF
  - call_constraints.json, expected_outcomes.json, expected_impacts.json, scope_requirements.json, eligibility_conditions.json, evaluation_priority_weights.json
  - This can be done by running Phase 1 manually or by pre-populating from source reading

  Step C — Populate Tier 3 project data (Phase 2+ input):
  - project_brief/concept_note.md — project concept
  - consortium/partners.json — at minimum partner names, roles, countries
  - architecture_inputs/objectives.json — project objectives
  - architecture_inputs/outcomes.json, impacts.json — expected outcomes/impacts

  Step D — Extract Tier 2A schemas:
  - extracted/section_schema_registry.json — application form section structure for the selected instrument
  - extracted/instrument_registry.json — instrument type definitions

  Step E — Extract Tier 1 rules:
  - extracted/compliance_principles.json — participation rules, eligibility, financial regulation constraints

  Step F — Budget integration (Phase 7 blocker):
  - integrations/lump_sum_budget_planner/interface_contract.json — define request/response schema
  - Prepare a budget request template and receive/validate a budget response

  Step G — Set ANTHROPIC_API_KEY:
  - Required for run_skill() (Claude API adapter) and dispatch_semantic_predicate()

  Recommended first live test

  Populate Steps A–C above for a single concrete RIA/IA topic from one of the 2026–2027 work programmes. Run:

  export ANTHROPIC_API_KEY=sk-ant-...
  python -m runner --run-id first-live-001

  The system will execute the full DAG, invoking Claude for each skill via run_skill(), evaluating gates, and either progressing through phases or declaring explicit gate failures with full       
  node_failure_details in run_summary.json. Phase 7 will fail (no budget response) and HARD_BLOCK Phase 8 — this is constitutionally correct behaviour.

  ---
  5. Quantitative Summary

  ┌────────────────────────────────────┬───────────────────────┐
  │               Metric               │         Value         │
  ├────────────────────────────────────┼───────────────────────┤
  │ Python modules                     │ 16 core + 7 predicate │
  ├────────────────────────────────────┼───────────────────────┤
  │ Lines of runtime code              │ 6,092                 │
  ├────────────────────────────────────┼───────────────────────┤
  │ Lines of agent/skill specification │ 13,144                │
  ├────────────────────────────────────┼───────────────────────┤
  │ Workflow nodes                     │ 11                    │
  ├────────────────────────────────────┼───────────────────────┤
  │ Workflow edges                     │ 13                    │
  ├────────────────────────────────────┼───────────────────────┤
  │ Gate predicates                    │ 98 across 11 gates    │
  ├────────────────────────────────────┼───────────────────────┤
  │ Predicate functions                │ 59                    │
  ├────────────────────────────────────┼───────────────────────┤
  │ Test functions                     │ 988 (all passing)     │
  ├────────────────────────────────────┼───────────────────────┤
  │ Source PDFs loaded                 │ 35 (~44 MB)           │
  ├────────────────────────────────────┼───────────────────────┤
  │ Extracted JSON files               │ 20 (all empty stubs)  │
  ├────────────────────────────────────┼───────────────────────┤
  │ Tier 3 data files                  │ 20 (all empty stubs)  │
  └────────────────────────────────────┴───────────────────────┘

  Engine completeness: 100%. Data completeness: 0%. The gap is data, not code.