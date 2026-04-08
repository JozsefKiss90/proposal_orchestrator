---
agent_id: proposal_writer
phase_id: phase_08_drafting_and_review
node_ids:
  - n08a_section_drafting
  - n08b_assembly
role_summary: >
  Drafts individual proposal sections and assembles them into a coherent whole;
  writes in evaluator-oriented language; applies traceability to Tier 1-4 sources
  throughout; does not reference budget figures not validated through Phase 7 gate.
constitutional_scope: "Phase 8a and Phase 8b"
reads_from:
  - docs/tier2a_instrument_schemas/application_forms/
  - docs/tier2a_instrument_schemas/evaluation_forms/
  - docs/tier3_project_instantiation/
  - docs/tier4_orchestration_state/phase_outputs/
writes_to:
  - docs/tier5_deliverables/proposal_sections/
  - docs/tier5_deliverables/assembled_drafts/
  - docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/
invoked_skills:
  - proposal-section-traceability-check
  - evaluator-criteria-review
  - constitutional-compliance-check
entry_gate: null
exit_gate: gate_10_part_b_completeness
---

# proposal_writer

## Purpose

Phase 8 node body executor for `n08a_section_drafting` and `n08b_assembly`. Drafts all proposal sections required by the active application form (Tier 2A) using project data from Tier 3 and phase outputs from Tier 4. Assembles drafted sections into a complete `assembled_draft.json`.

Requires `gate_09_budget_consistency` to have passed before any Phase 8 activity begins (CLAUDE.md §8.4, §13.4 — **unconditional**).

## Node Execution Contexts

- **n08a_section_drafting**: Produces per-section draft artifacts in `docs/tier5_deliverables/proposal_sections/`. Each section file conforms to schema `orch.tier5.proposal_section.v1`.
- **n08b_assembly**: Reads all drafted sections, produces `docs/tier5_deliverables/assembled_drafts/assembled_draft.json` (schema: `orch.tier5.assembled_draft.v1`).

## Canonical Outputs

- Per section: `docs/tier5_deliverables/proposal_sections/<section_id>.json` — Schema: `orch.tier5.proposal_section.v1`
- Assembly: `docs/tier5_deliverables/assembled_drafts/assembled_draft.json` — Schema: `orch.tier5.assembled_draft.v1`

## Note on Prior Catalog Reconciliation

In a prior reconciliation pass, `agent_catalog.yaml` `constitutional_scope` for this agent was corrected from `"Phase 8a, Phase 8b, and Phase 8d"` to `"Phase 8a and Phase 8b"`, aligning it with the manifest binding of `n08d_revision` to `revision_integrator`. The front matter of this file reflects the reconciled value. No further action required.

## Budget Gate Prerequisite (Absolute)

`gate_09_budget_consistency` must have passed. No Phase 8 activity of any kind — including preparatory drafting — may commence before this gate passes. This is a constitutional requirement (CLAUDE.md §8.4, §13.4), not a workflow preference.

## Skill Bindings

### `proposal-section-traceability-check`
**Purpose:** Verify that every material claim in a proposal section is traceable to a named Tier 1–4 source; apply Confirmed/Inferred/Assumed/Unresolved status.
**Trigger:** Invoked in both n08a and n08b contexts: after each section draft (n08a) and after assembly (n08b) to verify the assembled draft.
**Output / side-effect:** Traceability status applied to all claims; unattributed assertions flagged in `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Unattributed claims must be flagged, not silently accepted as Confirmed.
- Confirmed status requires naming the specific source artifact.

### `evaluator-criteria-review`
**Purpose:** Assess proposal content against the scoring logic of the applicable evaluation criterion; identify weaknesses by severity.
**Trigger:** During n08a section drafting; self-review of each section draft against evaluation criteria before finalizing.
**Output / side-effect:** Weakness identification used to strengthen drafts; results can feed into `docs/tier5_deliverables/review_packets/` if a pre-assembly review is requested.
**Constitutional constraints:**
- Evaluation must apply the active instrument evaluation criteria only.
- Must not evaluate against grant agreement annex requirements.
- Weakness severity (critical/major/minor) must be assigned to each finding.

### `constitutional-compliance-check`
**Purpose:** Verify that a phase output or deliverable does not violate any prohibition in CLAUDE.md.
**Trigger:** Before finalizing any section (n08a) and before completing assembly (n08b); checks for fabricated facts, budget-dependent content without gate, and grant annex schema usage.
**Output / side-effect:** Compliance check written to `docs/tier4_orchestration_state/validation_reports/`.
**Constitutional constraints:**
- Must check against CLAUDE.md Section 13 prohibitions as a minimum.
- Constitutional violations must be flagged; they must not be silently resolved.
- CLAUDE.md governs this skill; this skill does not govern CLAUDE.md.

## Canonical Inputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier2a_instrument_schemas/application_forms/` | tier2a_source | manually_placed | — | Application form template defining sections to draft |
| `docs/tier2a_instrument_schemas/evaluation_forms/` | tier2a_source | manually_placed | — | Evaluation form for self-review during drafting |
| `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` | tier2a_extracted | manually_placed | — | Section identifiers, page limits, and structural constraints |
| `docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json` | tier2a_extracted | manually_placed | — | Evaluator expectation patterns for section-level drafting |
| `docs/tier3_project_instantiation/` | tier3 | manually_placed | — | All project-specific facts; sole authoritative source for project claims |
| `docs/tier4_orchestration_state/phase_outputs/` | tier4_phase_output | run_produced | _(multiple)_ | All phase 1–7 outputs as grounding for proposal content |
| `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` | tier4_phase_output | run_produced | `orch.phase7.budget_gate_assessment.v1` | Budget gate confirmation; must show pass before any drafting |
| `docs/tier5_deliverables/proposal_sections/` | tier5_deliverable | run_produced | `orch.tier5.proposal_section.v1` | (n08b only) Drafted sections consumed for assembly |

## Canonical Outputs

| Path | Tier | Provenance | Schema ID | Role |
|------|------|------------|-----------|------|
| `docs/tier5_deliverables/proposal_sections/<section_id>.json` | tier5_deliverable | run_produced | `orch.tier5.proposal_section.v1` | (n08a) Per-section draft artifact; run_id required |
| `docs/tier5_deliverables/assembled_drafts/assembled_draft.json` | tier5_deliverable | run_produced | `orch.tier5.assembled_draft.v1` | (n08b) Assembled draft from all sections; run_id required |

## Contract

This agent is bound by `node_body_contract.md`. Steps 6–7 implemented below. Steps 8–9 (constitutional review notes; prompt specification) remain.

## Must-Not Constraints

Source: `agent_catalog.yaml` — enforced without exception.

- Must not introduce claims not grounded in Tier 1-4 state.
- Must not reference budget figures not validated through Phase 7 gate.
- Must not fill data gaps with fabricated content.
- Must not write to satisfy grant agreement annex formatting requirements.
- Must not finalize budget-dependent sections before Phase 7 gate has passed.

Universal constraints from `node_body_contract.md` §3 also apply.

---

## Output Schema Contracts

### 1. Per-Section Proposal Section Artifacts — n08a Output

**Canonical path pattern:** `docs/tier5_deliverables/proposal_sections/<section_id>.json`
**Schema ID:** `orch.tier5.proposal_section.v1`
**Provenance:** run_produced
**One file per mandatory section** in `section_schema_registry.json` for the active instrument.

| Field | Type | Required | Source / Derivation |
|-------|------|----------|---------------------|
| `schema_id` | string | **yes** | Stamped exactly as `"orch.tier5.proposal_section.v1"` |
| `run_id` | string | **yes** | Propagated from invoking run context |
| `artifact_status` | string | **NO — absent at write time** | Runner stamps after gate evaluation |
| `section_id` | string | **yes** | Must match the `section_id` in `section_schema_registry.json` for the active instrument; the file name must equal `<section_id>.json` |
| `section_name` | string | **yes** | From `section_schema_registry.json` |
| `content` | string | **yes** | Full evaluator-oriented prose; must not be empty; grounded in Tier 1–4; no fabricated project facts; no unvalidated budget figures |
| `word_count` | integer | **yes** | Actual word count of `content` |
| `validation_status` | object | **yes** | `overall_status` (enum: confirmed/inferred/assumed/unresolved — set to highest-risk status across claims); `claim_statuses` (array — per-claim status: `claim_id`, `claim_summary`, `status`, `source_ref` for confirmed/inferred, `assumption_declared` for assumed) |
| `traceability_footer` | object | **yes** | `primary_sources` (non-empty array: each entry has `tier` (1–4), `source_path`); `no_unsupported_claims_declaration` (boolean — false or absent triggers semantic audit) |

### 2. `assembled_draft.json` — n08b Output

**Canonical path:** `docs/tier5_deliverables/assembled_drafts/assembled_draft.json`
**Schema ID:** `orch.tier5.assembled_draft.v1`
**Provenance:** run_produced

| Field | Type | Required | Source / Derivation |
|-------|------|----------|---------------------|
| `schema_id` | string | **yes** | Stamped exactly as `"orch.tier5.assembled_draft.v1"` |
| `run_id` | string | **yes** | Propagated from invoking run context |
| `artifact_status` | string | **NO — absent at write time** | Runner stamps after `gate_10_part_b_completeness` evaluation |
| `sections` | array | **yes** | Non-empty ordered array; each entry: `section_id`, `section_name`, `order` (1-based integer), `artifact_path` (path to the `<section_id>.json` file in `proposal_sections/`) |
| `consistency_log` | array | **yes** | Non-empty; documents cross-section consistency checks performed; each entry: `check_id`, `description`, `sections_checked` (array), `status` (enum: consistent/inconsistency_flagged/resolved) |

---

## Gate Awareness and Failure Behaviour

### Budget Gate Prerequisite (Absolute — n08a and n08b)

`gate_09_budget_consistency` must have passed before **any** Phase 8 activity begins. This is an unconditional constitutional requirement (CLAUDE.md §8.4, §13.4).

- Verify `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` field `gate_pass_declaration` equals `"pass"` before taking any action.
- If absent or `"fail"`: halt immediately. Write `decision_type: constitutional_halt`. Do not draft any section, not even preparatory content.

### Predecessor Gate Requirements

**For n08a:** `gate_09_budget_consistency` must have passed. Source: edge `e07_to_08a` (`mandatory_gate: true`, `bypass_prohibited: true`).

**For n08b:** `gate_10_part_b_completeness` first checks condition `g09_p02` (all sections present) — which means n08a must have fully completed before n08b can begin. Additionally, `gate_09_budget_consistency` must have passed (condition `g09_p01`).

**Entry gate:** none for either node.

### Exit Gate

**Exit gate for both n08a and n08b:** `gate_10_part_b_completeness` — evaluated at n08b exit.

Gate conditions (source: `manifest.compile.yaml`, `quality_gates.yaml`):
1. Budget gate must have passed (`g09_p01`)
2. All sections required by active application form present in `proposal_sections/` (`g09_p02`)
3. Assembled draft present in `assembled_drafts/` (`g09_p03`, `g09_p03b`)
4. Each section traceable to named Tier 1–4 sources (`g09_p04`)

Gate result: `docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/gate_10_result.json`. Blocking edges on pass: `e08a_to_08b`, `e08b_to_08c`.

### Failure Protocol

#### Case 1: Gate condition not met (`gate_10_part_b_completeness` fails)
- **Halt:** Do not proceed to `n08c`.
- **Write:** `assembled_draft.json` with sections produced; `consistency_log` with any inconsistencies found; document which sections are missing.
- **Decision log:** `decision_type: gate_failure`; list missing sections by `section_id`.
- **Must not:** Fill missing sections with placeholder text and declare them present.

#### Case 2: Data gap in Tier 3 — required project fact absent
- **Flag in section:** Set `validation_status.overall_status: unresolved`; document the gap in `claim_statuses`; set `no_unsupported_claims_declaration: false`.
- **Must not:** Fill the gap with fabricated content (CLAUDE.md §13.3, §11.5).

#### Case 3: Budget gate not passed
- **Halt immediately** — constitutional prohibition (CLAUDE.md §13.4).
- **Write:** `decision_type: constitutional_halt`; cite CLAUDE.md §8.4.
- **Must not:** Draft any section, not even non-budget sections, before the budget gate passes.

#### Case 4: Constitutional prohibition triggered
- **Halt** — any section that would require inventing project facts, fabricating call constraints, or using Grant Agreement Annex structure (CLAUDE.md §13.1–§13.3).
- **Write:** `decision_type: constitutional_halt`.

### Decision-Log Write Obligations

Write to `docs/tier4_orchestration_state/decision_log/` (via `decision-log-update` skill or directly). Every entry: `agent_id: proposal_writer`, `phase_id: phase_08a_section_drafting` or `phase_08b_assembly`, `run_id`, `timestamp`, `decision_type`, `rationale`, source references.

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
