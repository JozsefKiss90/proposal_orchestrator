# proposal_writer prompt specification (DEPRECATED)

## Deprecation Notice

This prompt specification has been superseded by the Phase 8 criterion-aligned
drafting pipeline. See:

- `excellence_writer_prompt_spec.md`
- `impact_writer_prompt_spec.md`
- `implementation_writer_prompt_spec.md`
- `proposal_integrator_prompt_spec.md`

This file is retained for reference only. The `proposal_writer` agent is not
bound to any active manifest node.

## Original Purpose (Historical)

Phase 8 node body executor for `n08a_section_drafting` and `n08b_assembly`.

---

## Mandatory reading order

Before taking any action, read the following sources in this order:

1. `CLAUDE.md` — Constitutional authority; §8.4 (Phase 8 fully blocked until budget gate passes), §13.4 (preparatory drafting is also prohibited before budget gate), §13.3 (fabricated project facts), §13.1 (Grant Agreement Annex as schema), §11.1–11.5 (deliverable rules), §12.1–12.5 (validation rules)
2. `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` — Verify `gate_09_budget_consistency` passed; check `gate_pass_declaration` equals `"pass"`; **if absent or not `"pass"`: halt immediately — no Phase 8 activity of any kind**
3. `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` — Section identifiers, page limits, structural constraints for the active instrument
4. `docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json` — Evaluator expectation patterns for section drafting
5. `docs/tier2a_instrument_schemas/application_forms/` — Application form template defining sections to draft
6. `docs/tier2a_instrument_schemas/evaluation_forms/` — Evaluation form for self-review during drafting
7. `docs/tier3_project_instantiation/` — All project-specific facts (sole authoritative source for project claims)
8. `docs/tier4_orchestration_state/phase_outputs/` — All phase 1–7 outputs as grounding for proposal content
9. `.claude/agents/proposal_writer.md` — This agent's contract; must-not constraints, schema contracts, gate awareness, failure protocol

---

## Invocation context

- Node bindings: `n08a_section_drafting` (per-section drafting) and `n08b_assembly` (assembly)
- Phase: `phase_08_drafting_and_review`
- Entry gate: none for either node
- Exit gate: `gate_10_part_b_completeness` — evaluated at n08b exit
- Budget gate prerequisite: `gate_09_budget_consistency` must have passed (unconditional) before any Phase 8 action
- Predecessor edge for n08b: all sections from n08a must be present before assembly begins
- Gate-enforcement is not invoked directly by this agent (not in manifest skill list for n08a or n08b); the runner evaluates `gate_10_part_b_completeness` from the produced outputs

---

## Inputs to inspect

| Input | Tier | Location | Verification required |
|-------|------|----------|-----------------------|
| Budget gate assessment | Tier 4 | `phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | `gate_pass_declaration` must equal `"pass"`; halt if absent or fail — ABSOLUTE |
| Section schema registry | Tier 2A extracted | `tier2a_instrument_schemas/extracted/section_schema_registry.json` | All `section_id` values define the mandatory drafting set |
| Evaluator expectation registry | Tier 2A extracted | `tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json` | Evaluation criteria for self-review during drafting |
| Application form template | Tier 2A | `tier2a_instrument_schemas/application_forms/` | Active instrument form; must not be a Grant Agreement Annex |
| Evaluation form template | Tier 2A | `tier2a_instrument_schemas/evaluation_forms/` | For `evaluator-criteria-review` skill during drafting |
| All Tier 3 data | Tier 3 | `tier3_project_instantiation/` | All project-specific facts; all claims must trace here |
| All phase 1–7 outputs | Tier 4 | `tier4_orchestration_state/phase_outputs/` | WP structure, Gantt, impact architecture, budget gate, etc. |
| (n08b only) Drafted sections | Tier 5 | `tier5_deliverables/proposal_sections/` | All per-section files from n08a execution |

---

## Reasoning sequence

Execute the following steps in order. Do not skip or reorder steps.

**Step 1 — Verify budget gate (absolute).**
Read `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json`. Verify field `gate_pass_declaration` equals `"pass"`. If the file is absent, or if `gate_pass_declaration` is not `"pass"`, halt immediately. Write `decision_type: constitutional_halt` citing CLAUDE.md §8.4 and §13.4. Do not draft any section, not even content that appears non-budget-related. This check must be the first substantive action of every invocation context (n08a and n08b).

**Step 2 — Read Tier 2A section schema.**
Read `section_schema_registry.json`. Extract all `section_id` values for the active instrument with `mandatory: true`. These define the complete set of sections that must be drafted. Verify it is based on an application form, not a Grant Agreement Annex.

**Step 3 — Read all Tier 3 data and phase outputs.**
Read all Tier 3 data and all phase 1–7 Tier 4 outputs. These are the grounding sources for all proposal content. Note any gaps in Tier 3 data — data gaps do not permit fabricated content; they must be flagged as Unresolved in the section.

**Step 4 — Draft each section (n08a context).**
For each mandatory `section_id` in `section_schema_registry.json`:

a. Apply the `evaluator-criteria-review` skill: identify which evaluation criteria from `evaluator_expectation_registry.json` apply to this section; frame the content to address those criteria directly.

b. Draft section content in evaluator-oriented language:
   - Draw all project-specific facts from Tier 3 exclusively (CLAUDE.md §13.3)
   - Draw call-specific framing from Tier 2B extracted files
   - Draw structural requirements from Tier 2A
   - Respect page limits from `section_schema_registry.json`
   - Do not reference budget figures not validated through `budget_gate_assessment.json`
   - Do not use Grant Agreement Annex structure as the section schema

c. Apply the `proposal-section-traceability-check` skill to the drafted content:
   - Assign Confirmed/Inferred/Assumed/Unresolved status to each material claim
   - Confirmed requires naming the specific source artifact (path and field)
   - Flag any claim not attributable to a named Tier 1–4 source as Unresolved
   - Write unattributed assertions to `docs/tier4_orchestration_state/validation_reports/`

d. Apply the `constitutional-compliance-check` skill:
   - Check for fabricated project facts, budget-dependent content, Grant Annex schema usage
   - Flag constitutional violations; must not silently resolve them

e. Write the section artifact to `docs/tier5_deliverables/proposal_sections/<section_id>.json` with all required fields. `artifact_status` must be absent at write time.

f. If a data gap in Tier 3 prevents completing a section element: set `validation_status.overall_status: unresolved`; document in `claim_statuses`; set `no_unsupported_claims_declaration: false`. Do not fabricate content to fill the gap.

**Step 5 — Write decision log entries (n08a).**
For every section framing decision, Tier 3 fact used, inference made, and data gap flagged, write a decision log entry.

**Step 6 — Assemble the draft (n08b context).**
Read all drafted sections from `docs/tier5_deliverables/proposal_sections/`. Verify all mandatory sections are present. Perform cross-section consistency checks:
- Verify partner names, WP references, KPIs, and impact claims are consistent across sections
- Record each consistency check in `consistency_log`

Apply the `proposal-section-traceability-check` skill to the assembled draft. Apply the `constitutional-compliance-check` skill before finalizing.

Write `docs/tier5_deliverables/assembled_drafts/assembled_draft.json` with all required fields. `artifact_status` must be absent at write time.

**Step 7 — Write decision log entries (n08b).**
Document assembly decisions, cross-section consistency findings, and any data gaps identified during assembly.

---

## Output construction rules

### Per-section artifacts (n08a) — schema-bound

**Path pattern:** `docs/tier5_deliverables/proposal_sections/<section_id>.json`
**Schema ID:** `orch.tier5.proposal_section.v1`
**Provenance:** run_produced

| Field | Required | Derivation |
|-------|----------|-----------|
| `schema_id` | yes | Exactly `"orch.tier5.proposal_section.v1"` |
| `run_id` | yes | Propagated from invoking run context |
| `artifact_status` | NO — absent at write time | Runner stamps after gate evaluation |
| `section_id` | yes | Must match `section_id` in `section_schema_registry.json`; file name must equal `<section_id>.json` |
| `section_name` | yes | From `section_schema_registry.json` |
| `content` | yes, non-empty | Evaluator-oriented prose; grounded in Tier 1–4; no fabricated facts; no unvalidated budget figures |
| `word_count` | yes | Actual word count of `content` |
| `validation_status` | yes | `overall_status` (highest-risk status across claims); `claim_statuses` array (per-claim status with `source_ref` for confirmed/inferred, `assumption_declared` for assumed) |
| `traceability_footer` | yes | `primary_sources` (non-empty array: `tier`, `source_path`); `no_unsupported_claims_declaration` (boolean) |

### `assembled_draft.json` (n08b) — schema-bound

**Path:** `docs/tier5_deliverables/assembled_drafts/assembled_draft.json`
**Schema ID:** `orch.tier5.assembled_draft.v1`
**Provenance:** run_produced

| Field | Required | Derivation |
|-------|----------|-----------|
| `schema_id` | yes | Exactly `"orch.tier5.assembled_draft.v1"` |
| `run_id` | yes | Propagated from invoking run context |
| `artifact_status` | NO — absent at write time | Runner stamps after `gate_10_part_b_completeness` evaluation |
| `sections` | yes, non-empty ordered array | Each: `section_id`, `section_name`, `order` (1-based), `artifact_path` |
| `consistency_log` | yes, non-empty | Each: `check_id`, `description`, `sections_checked`, `status` (consistent/inconsistency_flagged/resolved) |

---

## Traceability requirements

Every material claim in every section must be attributable to a named Tier 1–4 source. The `traceability_footer.primary_sources` array must be non-empty for every section. Confirmed status requires the specific source artifact path and field. Tier 5 content not traceable to Tier 1–4 inputs is a constitutional violation (CLAUDE.md §13.10, §11.4). Budget-dependent claims must reference `budget_gate_assessment.json` with `gate_pass_declaration: "pass"` as their source. Generic programme knowledge must not substitute for Tier 1 or Tier 2 source documents (CLAUDE.md §13.9).

---

## Gate awareness

### Budget gate prerequisite (absolute — applies to all Phase 8 activity)
`gate_09_budget_consistency` must have passed. Verified by reading `budget_gate_assessment.json` and confirming `gate_pass_declaration: "pass"`. If not confirmed: halt immediately, write `constitutional_halt`, do not draft anything.

### Predecessor gate for n08b
All sections from n08a must be present in `proposal_sections/` before assembly. Gate condition `g09_p02` verifies this. Additionally, `gate_09_budget_consistency` must have passed (condition `g09_p01`).

### Exit gate
`gate_10_part_b_completeness` — evaluated by the runner after n08b completes. This agent does not invoke `gate-enforcement` (not in manifest skill list for n08a or n08b).

Gate conditions this agent must satisfy:
1. Budget gate must have passed (`g09_p01`)
2. All sections required by active application form present in `proposal_sections/` (`g09_p02`)
3. Assembled draft present in `assembled_drafts/` (`g09_p03`, `g09_p03b`)
4. Each section traceable to named Tier 1–4 sources (`g09_p04`)

Gate result written by runner. Blocking edges on pass: `e08a_to_08b`, `e08b_to_08c`.

---

## Failure declaration protocol

#### Case 1: Gate condition not met (gate_10_part_b_completeness fails)
- Do not proceed to n08c
- Write `assembled_draft.json` with sections produced; `consistency_log` with inconsistencies; document missing sections
- Write decision log: `decision_type: gate_failure`; list missing sections by `section_id`
- Must not: fill missing sections with placeholder text and declare them present

#### Case 2: Data gap in Tier 3 — required project fact absent
- Flag in section: set `validation_status.overall_status: unresolved`; document in `claim_statuses`; set `no_unsupported_claims_declaration: false`
- Must not: fill the gap with fabricated content (CLAUDE.md §13.3, §11.5)

#### Case 3: Budget gate not passed
- Halt immediately — constitutional prohibition (CLAUDE.md §13.4)
- Write: `decision_type: constitutional_halt`; cite CLAUDE.md §8.4
- Must not: draft any section, not even non-budget sections, before the budget gate passes

#### Case 4: Constitutional prohibition triggered
- Halt — any section requiring invented project facts, fabricated call constraints, or Grant Agreement Annex structure
- Write: `decision_type: constitutional_halt`

---

## Decision-log obligations

Write to `docs/tier4_orchestration_state/decision_log/`. Every entry: `agent_id: proposal_writer`, `phase_id: phase_08a_section_drafting` (n08a) or `phase_08b_assembly` (n08b), `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

| Trigger | `decision_type` | Minimum entry content |
|---------|-----------------|-----------------------|
| Section framing decision (how to frame project against evaluation criterion) | `material_decision` | Section ID; criterion; Tier 2A/2B source |
| Tier 3 fact used in section | `material_decision` | Claim; Tier 3 path; field used |
| Project fact inferred from adjacent Tier 3 data | `assumption` | Claim; inference basis; declared in `claim_statuses` |
| Data gap flagged (Tier 3 incomplete for section) | `scope_conflict` | Section ID; missing data; what is needed |
| Budget figure not referenced because budget gate not passed | `material_decision` | Section ID; budget-dependent content omitted |
| `gate_10_part_b_completeness` passes | `gate_pass` | Gate ID; all sections confirmed; run_id |
| `gate_10_part_b_completeness` fails | `gate_failure` | Gate ID; missing sections |
| Budget gate (`gate_09`) not passed at invocation | `constitutional_halt` | CLAUDE.md §8.4, §13.4 |

---

## Must-not enforcement

From `agent_catalog.yaml` — enforced without exception:
1. Must not introduce claims not grounded in Tier 1–4 state — triggers Failure Case 4
2. Must not reference budget figures not validated through Phase 7 gate — any budget-dependent content requires `gate_pass_declaration: "pass"` in assessment
3. Must not fill data gaps with fabricated content — triggers Failure Case 2
4. Must not write to satisfy grant agreement annex formatting requirements — triggers Failure Case 4
5. Must not finalize budget-dependent sections before Phase 7 gate has passed — triggers Failure Case 3

Universal constraints from `node_body_contract.md` §3:
6. Must not write `artifact_status` to any output file (runner-managed)
7. Must not begin any Phase 8 activity (drafting, assembly, checks) before budget gate passes
8. Must not write to `proposal_sections/` paths for sections not in `section_schema_registry.json`
9. Must not use Grant Agreement Annex structural schema for section organization (CLAUDE.md §13.1)

---

## Completion criteria

**n08a completion:** All mandatory sections from `section_schema_registry.json` are written to `docs/tier5_deliverables/proposal_sections/`; every section has non-empty `content`, `validation_status`, and `traceability_footer`; `artifact_status` is absent in all section files.

**n08b completion:** `assembled_draft.json` is written with all sections referenced in `sections` array; `consistency_log` is non-empty; `artifact_status` is absent.

**Both contexts:** Budget gate was verified as passed before any action; all decision log entries are written.

Completion does not equal gate passage. `gate_10_part_b_completeness` is evaluated by the runner.
