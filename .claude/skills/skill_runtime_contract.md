# Skill Runtime Contract
## Horizon Europe Proposal Orchestration System — Skill Layer

**Applies to:** All skill implementation files in `.claude/skills/`
**Constitutional authority:** Subordinate to `CLAUDE.md`. This contract operationalizes; it does not override.
**Version:** 1.0 (system_orchestration package v1.1)

---

## Purpose

This document is the shared contract that every skill implementation file in `.claude/skills/` must conform to. It defines the minimum obligations that apply to every skill regardless of its specific purpose or phase.

Every skill file must reference this contract. A skill that conforms to its own front matter but violates this contract is constitutionally invalid.

---

## Contract Body

### C.1 Skill Identity

- `skill_id` must exactly match the `id` field in `skill_catalog.yaml`.
- `purpose_summary` must accurately represent the `purpose` in `skill_catalog.yaml` without expanding scope.
- `used_by_agents` must exactly match the `used_by_agents` list in `skill_catalog.yaml`.

### C.2 Scope Boundaries

- The skill reads only from paths declared in `reads_from` in `skill_catalog.yaml`.
- The skill writes only to paths declared in `writes_to` in `skill_catalog.yaml`.
- Scope violations are hard failures. There are no advisory scope warnings.

### C.3 Input Validation (mandatory before any execution)

1. Confirm each declared input path exists.
2. Confirm each input artifact is non-empty.
3. For canonical JSON artifacts: confirm `schema_id` matches the expected `schema_id_value` from `artifact_schema_specification.yaml`. Mismatch → `MALFORMED_ARTIFACT` failure.
4. For artifacts carrying `artifact_status`: confirm the value is `valid`. An `artifact_status: invalid` artifact must not be used as skill input.
5. Any validation failure → return `SkillResult(status="failure")` immediately. Do not proceed.

### C.4 Output Requirements

- All outputs written to declared `writes_to` paths only.
- For canonical Tier 4 / Tier 5 artifacts: `schema_id` must be stamped at write time.
- For canonical Tier 4 / Tier 5 artifacts: `run_id` must be propagated from the invoking agent.
- `artifact_status` must be **absent** at write time. The DAG scheduler runner stamps this field post-gate.
- Partial outputs are not permitted. If a complete, conformant artifact cannot be produced, declare failure and write nothing to the canonical output path.

### C.5 Determinism

- Same inputs + same documented state → same outputs.
- No hidden state, no agent memory reads, no randomness.
- No reads from `.claude/agent-memory/`, `.claude/cache/`, or `.claude/runs/`.

### C.6 Constitutional Constraint Enforcement

- Every constraint in `constitutional_constraints` is a hard failure condition.
- Enforcement must be explicit in the execution specification body.
- No constraint may be treated as advisory.

### C.7 Validation Status Vocabulary

Where the skill produces a validation report or claim-bearing artifact, every evaluated element must be assigned one of:
- **Confirmed** — directly evidenced by a named source in Tier 1–3; source artifact named
- **Inferred** — derived by logical reasoning; inference chain stated
- **Assumed** — adopted in absence of evidence; assumption declared
- **Unresolved** — conflicting or missing; resolution required before downstream use

### C.8 Failure Protocol

| Failure category | Trigger | Required response |
|-----------------|---------|------------------|
| `MISSING_INPUT` | Required input absent or empty | `SkillResult(status="failure", failure_category="MISSING_INPUT")`; no partial write |
| `MALFORMED_ARTIFACT` | Input `schema_id` mismatch or required field absent | `SkillResult(status="failure", failure_category="MALFORMED_ARTIFACT")`; no partial write |
| `CONSTRAINT_VIOLATION` | Constitutional constraint triggered | `SkillResult(status="failure", failure_category="CONSTRAINT_VIOLATION")`; write to decision log if in scope |
| `INCOMPLETE_OUTPUT` | Cannot produce complete, conformant output | `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT")`; no partial write to canonical path |
| `CONSTITUTIONAL_HALT` | CLAUDE.md §13 prohibition triggered | `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT")`; halt immediately; write to decision log if in scope |

Failure is a correct and valid output. Fabricated completion is a constitutional violation.

### C.9 Side-Effect Control

Skills may only:
- Write artifacts to declared `writes_to` paths
- Write validation reports (only if `validation_reports/` is in `writes_to`)
- Write decision log entries (only if `decision_log/` is in `writes_to`)

Skills must not:
- Call another skill
- Call an agent
- Issue any command to the DAG scheduler
- Write to any path outside declared `writes_to`
- Modify Tier 1 or Tier 2 source documents
- Modify `CLAUDE.md`, `manifest.compile.yaml`, `skill_catalog.yaml`, or `agent_catalog.yaml`
- Overwrite a validated checkpoint artifact

### C.10 Invocation Interface

Every skill is invoked through:

```
run_skill(
    skill_id:   str,
    run_id:     str,
    repo_root:  Path,
    inputs:     dict
) -> SkillResult
```

`SkillResult` fields:
- `status`: `"success"` | `"failure"`
- `outputs_written`: `list[str]` — paths of artifacts written (relative to `repo_root`)
- `validation_report`: `str | None` — path to validation report written, if any
- `failure_reason`: `str | None` — required when `status == "failure"`
- `failure_category`: `str | None` — one of the five failure categories in §C.8

### C.11 Scheduler Separation

- The DAG scheduler never calls a skill directly.
- Skills are called only by agents.
- Skills never call other skills, agents, or the scheduler.
- `artifact_status` is set by the scheduler after gate evaluation — never by a skill.
- `run_summary.json` is owned by `runner/dag_scheduler.py` — skills must not write to it.

---

*Skill runtime contract. Effective from creation. Amendments require explicit human instruction. No amendment may weaken any constraint, introduce scheduler coupling, or relax any constitutional prohibition from CLAUDE.md.*
