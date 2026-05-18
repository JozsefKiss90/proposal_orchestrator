# Proposal Orchestrator — Architecture Pitch

*Presentation script for `docs/architecture_diagram.mmd` (~1.5–2 minutes)*

---

## Opening — What It Is

This is the Proposal Orchestrator: a DAG-driven engine that transforms Horizon Europe call documents, programme rules, and project data into evaluator-ready proposal drafts. Eight phases, thirteen execution nodes, eleven gates, and over a hundred deterministic predicates — all governed by a single constitutional document.

## The Foundation — Tier Model

Everything starts with data, organized into a strict tier hierarchy. Tiers 1 and 2 are the normative and structural authorities — EU legislation, programme guidance, application form schemas, and the specific call's expected outcomes and impacts. Tier 3 is where the project becomes real: the consortium, the objectives, the work package seeds. Tiers 4 and 5 are outputs — orchestration state and the final deliverables. Nothing in Tier 5 may introduce a claim that isn't grounded in Tiers 1 through 4. An external budget integration sits alongside, because this system does not compute budgets — it consumes validated budget data from an external planner.

## The Flow — DAG Execution

The workflow is a directed acyclic graph. Phase 1 parses the call and extracts six structured constraint files. Phase 2 aligns the project concept against those constraints. Phase 3 designs the work packages; then Phase 4 builds the timeline and Phase 5 constructs the impact architecture — these two run in parallel once Phase 3 releases. Phase 6 assembles the implementation architecture once both converge. Phase 7 is the budget gate — a hard block. No drafting begins until a validated external budget is present. Phase 8 fans out into three parallel drafting nodes — Excellence, Impact, Implementation — each producing a criterion-aligned section. These converge into assembly, then evaluator review, then final revision.

## The Engine — Runtime Stack

Three layers execute this graph. The DAG scheduler dispatches nodes in topological order and evaluates gates. The agent runtime orchestrates skill invocations within each node. The skill runtime is a Claude transport adapter — it assembles prompts, invokes Claude through the local CLI, parses structured JSON responses, validates them against schemas, and writes artifacts atomically. No domain reasoning lives in the runtime; all of it is delegated to Claude through the skill specifications.

## The Contract — Node Dispatch

Every node follows a five-step contract. Set state to running. Evaluate the entry gate — if it fails, the node never executes. Run the agent body. Evaluate the exit gate — if the agent couldn't produce its artifacts, the gate is skipped entirely. Return the result. Three failure origins are tracked: entry gate, agent body, and exit gate. A gate failure at the budget node triggers a hard block that freezes all Phase 8 nodes downstream.

## The Guarantee — Predicates and Authority

The predicate modules are the enforcement layer. File predicates check existence. Schema predicates check structure. Coverage predicates perform cross-artifact joins — does every expected impact have a mapped pathway, does every WP partner exist in the consortium data. Source reference predicates verify traceability. All deterministic predicates run before any semantic check is dispatched to Claude. And above everything sits the authority hierarchy: human instruction overrides the constitution, the constitution overrides programme rules, programme rules override project data, and project data overrides agent memory. Conflicts are logged, not silently resolved.

## The Constitution — Why It Matters

The Repository Constitution — CLAUDE.md — is not a style guide or a set of recommendations. It is the highest-priority interpretive authority after an explicit human instruction. Every agent, skill, and workflow must read and comply with it before taking action. It defines what tiers mean, what gates enforce, what actions are forbidden, and what happens when sources conflict. Without it, the runtime is just plumbing — with it, the system has a single, auditable point of truth that no automated process can override, amend, or silently reinterpret.

## Close

The result: a system where an honest gate failure is a correct output, fabricated completion is a constitutional violation, and every claim in the final proposal can be traced back to its source document.
