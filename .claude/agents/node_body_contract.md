# Node Body Contract
## Universal obligations for every agent in the Horizon Europe Proposal Orchestration System

**Authority:** Subordinate to `CLAUDE.md`. This contract operationalizes the constitutional requirements from `CLAUDE.md` §10 and the generation requirements from `agent-generation-plan.md` §3. It does not override either.

**Applies to:** Every `.claude/agents/<agent_id>.md` file, without exception.

**Cross-reference:** `agent-generation-plan.md` §3 is the normative source for each section below. This document is the agent-facing summary.

---

## §1 — Agent Identity

Every agent must declare:

| Field | Rule |
|-------|------|
| `agent_id` | Must exactly match the `id` field in `agent_catalog.yaml`. No variation, abbreviation, or alias permitted. |
| `role_summary` | ≤ 2 sentences. Must not expand scope beyond what is stated in `agent_catalog.yaml`. |
| `constitutional_scope` | Must match `constitutional_scope` from `agent_catalog.yaml`. Scope may not be widened in the agent body. |

---

## §2 — Allowed Scope

An agent may only:
- Read from paths listed in its `reads_from` in `agent_catalog.yaml`
- Write to paths listed in its `writes_to` in `agent_catalog.yaml`

An agent must not access any path outside these declared lists. Accessing an undeclared path is a scope violation.

Cross-phase reads (e.g. a Phase 5 agent reading Phase 3 outputs) are permitted only where the cross-phase path is explicitly listed in the agent's `reads_from` in `agent_catalog.yaml`.

---

## §3 — Must-Not Constraints

The agent body must enumerate every `must_not` entry from `agent_catalog.yaml` as a hard-coded refusal condition. These are never advisory.

**Universal must-not constraints — apply to every agent regardless of catalog entry:**

1. Must not fabricate project facts (partner names, capabilities, roles, objectives, budgets, team sizes) not present in Tier 3.
2. Must not invent call constraints, scope requirements, expected outcomes, or expected impacts not present in Tier 2B source documents.
3. Must not declare a gate passed without confirming every gate condition from `quality_gates.yaml` and `manifest.compile.yaml` is satisfied.
4. Must not proceed if the predecessor gate condition for its phase has not passed.
5. Must not store a material decision only in agent memory; must write it to `docs/tier4_orchestration_state/decision_log/`.
6. Must not produce outputs that are not traceable to named Tier 1–4 sources.
7. Must not substitute generic Horizon Europe programme knowledge for Tier 1 source documents when those documents are present and accessible (CLAUDE.md §10.6, §13.9).
8. Must not commence any Phase 8 activity if `gate_09_budget_consistency` has not passed (CLAUDE.md §13.4, §8.4).
9. Must not use Grant Agreement Annex templates as a proposal schema source (CLAUDE.md §13.1).
10. Must not introduce new artifact paths not defined in `manifest.compile.yaml` or `artifact_schema_specification.yaml` (agent-generation-plan §5.4).

---

## §4 — Canonical Inputs

Before acting, the agent must verify that every required input artifact:
- Is present at its declared path
- Is non-empty
- Carries the expected `schema_id` value (for structured JSON artifacts)

If a mandatory input is absent: declare blocked state, write the missing input path and reason to the decision log, halt. Do not substitute, infer, or hallucinate missing content.

---

## §5 — Canonical Outputs

Every output artifact written by an agent must:
- Be written to its canonical path as defined in `agent_catalog.yaml` `writes_to` and the `manifest.compile.yaml` artifact registry
- Carry `schema_id` set to the `schema_id_value` from `artifact_schema_specification.yaml`
- Carry `run_id` inherited from the invoking run context
- Leave the `artifact_status` field absent (the DAG runner stamps this field after gate evaluation — agents must not set it)
- Populate all `required: true` fields as defined in `artifact_schema_specification.yaml`

---

## §6 — Artifact Schema Obligations

For every canonical output artifact:

1. Read the schema entry in `artifact_schema_specification.yaml` before constructing the output.
2. Set `schema_id` to the exact `schema_id_value` — any other value causes the runner to treat the artifact as `MALFORMED_ARTIFACT`.
3. Populate every field marked `required: true`.
4. Do not set `artifact_status` — this is runner-managed.
5. On rerun: write deterministically from declared inputs. Do not rely on previously cached state from a prior run.

---

## §7 — Skill Invocation Discipline

Skills listed in `invoked_skills` must be:
- Invoked only for purposes within the skill's `purpose` definition in `skill_catalog.yaml`
- Invoked in the order listed
- Not used to perform actions outside the skill's declared `writes_to` paths

An agent must not invoke a skill that is not listed in its `invoked_skills` front matter without a plan amendment.

---

## §8 — Gate Awareness

Every node-bound agent must:
- Know its `exit_gate` (from `manifest.compile.yaml`)
- Know which predecessor gates must have passed before it may begin (from the edge registry and gate conditions)
- Verify predecessor gates are passed as its first execution step; halt if they have not
- Produce the artifacts required by its exit gate predicates
- Write the gate result to the canonical path defined by `GATE_RESULT_PATHS` in the runner

**Special rule for `gate_09_budget_consistency` (Phase 7):**
If any budget artifact is absent from `docs/integrations/lump_sum_budget_planner/received/`, the gate result is `fail` unconditionally. There is no hold state. Absent artifacts are not a deferral condition; they are a blocking gate failure (CLAUDE.md §8.4, manifest `absent_artifacts_behavior: blocking_gate_failure`).

---

## §9 — Failure Behaviour

Implement all four failure cases explicitly:

| Case | Required action |
|------|----------------|
| Gate condition not met | Write a gate failure report to the canonical Tier 4 phase output path, stating which conditions failed and why. Do not proceed downstream. Do not fabricate completion. |
| Required input absent | Declare blocked state. Write missing input path and reason to decision log. Do not substitute or hallucinate. |
| Mandatory predecessor gate not passed | Halt immediately. Write a constitutional precondition violation note to the decision log. |
| Constitutional prohibition triggered (CLAUDE.md §13) | Halt immediately. Do not produce partial output. Write the triggered prohibition reference to the decision log. |

---

## §10 — Decision-Log Obligations

Write a decision log entry for every:
- Material decision made during execution
- Assumption adopted where source data was absent or ambiguous
- Scope conflict or tier inconsistency encountered
- Gate pass or gate failure declared

**Mandatory fields in each decision log entry:**

```json
{
  "agent_id": "<agent_id>",
  "phase_id": "<phase_id>",
  "run_id": "<run_id from context>",
  "timestamp": "<UTC ISO-8601>",
  "decision_type": "<material_decision | assumption | scope_conflict | gate_pass | gate_failure | constitutional_halt>",
  "rationale": "<explanation with source references to named Tier 1-4 artifacts>"
}
```

Decisions held only in agent memory are not durable. CLAUDE.md §9.4 and §9.5 govern.

---

## §11 — DAG Execution Context

- The scheduler is **synchronous**. One node executes at a time. Do not attempt parallel dispatch.
- `run_id` is passed at invocation. Propagate it to every artifact written.
- The scheduler calls `evaluate_gate()` after the agent completes. Agents do not call `evaluate_gate()`.
- `run_summary.json` is owned by `runner/dag_scheduler.py`. Agents must not write to it.
- Gate failure is a correct and valid output. Fabricated completion is a constitutional violation.

---

*Node body contract. Effective from creation. All agent files in `.claude/agents/` are bound by this contract. Amendments require explicit human instruction per `CLAUDE.md` §14.*
