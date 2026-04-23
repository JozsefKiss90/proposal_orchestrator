---
skill_id: constitutional-compliance-check
purpose_summary: >
  Verify that a phase output or deliverable does not violate any prohibition in
  CLAUDE.md, checking for fabricated project facts, fabricated call constraints,
  budget-dependent content before the budget gate, grant annex schema usage, and
  other constitutional violations.
used_by_agents:
  - compliance_validator
  - call_analyzer
  - concept_refiner
  - proposal_writer
  - revision_integrator
  - budget_gate_validator
reads_from:
  - CLAUDE.md
optional_reads_from:
  - docs/tier5_deliverables/
writes_to:
  - docs/tier4_orchestration_state/validation_reports/
  - docs/tier4_orchestration_state/decision_log/
constitutional_constraints:
  - "Must check against CLAUDE.md Section 13 prohibitions as a minimum"
  - "Constitutional violations must be flagged; they must not be silently resolved"
  - "CLAUDE.md governs this skill; this skill does not govern CLAUDE.md"
---

## Input Access (TAPM Mode)

This skill executes in Tool-Augmented Prompt Mode (TAPM). Claude reads
declared inputs from disk via the Read tool during execution.

**Mandatory reads:**
1. `CLAUDE.md` — the repository constitution; source of all §13 checks.
2. The artifact at `artifact_path` (supplied by the invoking agent via
   caller context) — the single artifact being audited.

**Input boundary rules:**
- Read ONLY `CLAUDE.md` and the file at `artifact_path`. Do not
  recursively read `docs/tier4_orchestration_state/phase_outputs/` or
  any other phase output directory.
- For Phase 6 invocations, `artifact_path` resolves to
  `docs/tier4_orchestration_state/phase_outputs/phase6_implementation_architecture/implementation_architecture.json`.
  Audit that artifact only.
- `docs/tier5_deliverables/` is optional. If present and the artifact
  being audited is a Tier 5 deliverable, read the specific artifact at
  `artifact_path`. Do not scan the entire Tier 5 directory.
- All 12 §13 checks (13.1–13.12) remain mandatory. Checks that are
  structurally non-applicable to the artifact type (e.g. 13.5, 13.6,
  13.11, 13.12) must still appear in the output with `check_status:
  "pass"` and an explicit reason for non-applicability.

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `CLAUDE.md` | Repository constitution | Section 13 prohibitions (13.1–13.12); Section 7 gate conditions; Section 8 budget integration rules; Section 11 deliverable rules | N/A — constitutional document | The binding authority that defines all prohibited actions; every violation check is mapped to a named section in this document |
| `artifact_path` (caller context) | The specific phase output or deliverable artifact to audit | Phase-specific canonical artifact fields (varies by phase: call_analysis_summary, concept_refinement_summary, wp_structure, gantt, impact_architecture, implementation_architecture, budget_gate_assessment, drafting_review_status) | Context-dependent: the schema_id of the artifact being checked | The targeted artifact being audited for constitutional violations; checked for fabricated facts, schema mismatches, gate bypasses, and other Section 13 violations. In TAPM mode, read this single artifact from disk — do not scan the entire phase_outputs/ directory |
| `docs/tier5_deliverables/` | Deliverable directory — proposal_sections/, assembled_drafts/, review_packets/, final_exports/ | content fields; traceability_footer; validation_status; section_completion_log | Context-dependent: orch.tier5.proposal_section.v1, orch.tier5.assembled_draft.v1, orch.tier5.review_packet.v1, orch.tier5.final_export.v1 | Deliverables being audited for constitutional violations; checked for budget-dependent content before gate pass, unsupported Tier 5 claims, and grant annex schema usage |

### Outputs

| Path | Artifact | Schema ID | Required Fields (from artifact_schema_specification.yaml) | run_id Required | Derivation Source |
|------|----------|-----------|----------------------------------------------------------|-----------------|-------------------|
| `docs/tier4_orchestration_state/validation_reports/` | Per-invocation constitutional compliance report file (e.g., `compliance_check_<artifact>_<timestamp>.json`) | N/A — validation report | report_id; skill_id: "constitutional-compliance-check"; invoking_agent; run_id_reference; artifact_audited (path); section13_checks (array: prohibition_id[e.g., "13.1"], prohibition_description, check_status[pass/violation], violation_evidence, severity[critical/major]); summary (total_prohibitions_checked, violations_found); timestamp | No — validation reports are not phase output canonical artifacts | section13_checks: each prohibition in CLAUDE.md §13 applied to the artifact being audited; violation_evidence quotes specific content from the audited artifact; critical violations must block downstream use |
| `docs/tier4_orchestration_state/decision_log/` | Constitutional violation decision log entry (when a violation is found and a resolution decision is made) | N/A — decision log entry | decision_id; decision_type: "constitutional_violation"; violation_id; constitutional_rule_ref (e.g., "CLAUDE.md §13.3"); artifact_affected; resolution_status; resolution_note; tier_authority_applied; timestamp | No | Entries written when a constitutional violation requires an explicit resolution decision; the resolution must identify the tier authority applied and why |

### Artifact Registry Cross-Reference

| Output Path | Registered in manifest.compile.yaml artifact_registry? | Producing Node |
|-------------|--------------------------------------------------------|----------------|
| `docs/tier4_orchestration_state/validation_reports/` | Not registered as a discrete artifact_id in the artifact_registry | Multiple nodes (context-dependent per invoking agent) |
| `docs/tier4_orchestration_state/decision_log/` | Not registered as a discrete artifact_id in the artifact_registry | Multiple nodes (context-dependent per invoking agent) |

## Execution Specification

### 1. Input Validation Sequence

- Step 1.1: Confirm the invoking agent provides the path of the artifact to be audited as context parameter `artifact_path`. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="artifact_path required; invoking agent must specify which artifact to audit") and halt.
- Step 1.2: Presence check — confirm the artifact at `artifact_path` exists and is readable. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="Artifact at <artifact_path> not found") and halt.
- Step 1.3: Confirm `CLAUDE.md` is accessible at the repository root. If absent: return SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason="CLAUDE.md not found; cannot perform constitutional compliance check") and halt.
- Step 1.4: Read CLAUDE.md §13 (prohibitions 13.1–13.12). These 12 prohibitions define the exact checks to apply. If the §13 content cannot be read: halt.

### 2. Core Processing Logic

Apply each of the 12 checks below to the artifact at `artifact_path`. For each check: assign `check_status` as "pass" or "violation". If a violation is found: record `violation_evidence` (quoted text from the artifact that evidences the violation) and `severity` (critical or major).

**Check 13.1 — Grant Agreement Annex as schema source:**
- Read the artifact's content. If the artifact is a proposal section (schema_id = "orch.tier5.proposal_section.v1") or a phase output: check whether any structural reference in the content or traceability_footer identifies a Grant Agreement Annex, Model Grant Agreement Annex, or "AGA" template as a schema source.
- Specific detection: look for strings matching "Annex [0-9]", "Grant Agreement Annex", "AGA Template", "Model Grant Agreement template" used as a structural authority (not as a citation). If found: violation. Severity: critical.

**Check 13.2 — Invented call constraints:**
- Applicable to: any artifact that makes claims about what the call requires, excludes, or mandates.
- For each claim in the artifact that asserts a call requirement, scope boundary, or eligibility condition: check whether the claim's `traceability_footer.primary_sources[]` contains a reference pointing to a path within `docs/tier2b_topic_and_call_sources/extracted/`. If a call requirement claim carries no Tier 2B source reference in the artifact's traceability footer: violation. Severity: critical. Note: this skill does not read `docs/tier2b_topic_and_call_sources/extracted/` directly (not in reads_from); it checks only whether the artifact provides a Tier 2B source reference, not whether the referenced entry is present in the Tier 2B files.

**Check 13.3 — Invented project facts:**
- Applicable to: all artifacts containing project-specific content.
- For each claim naming a specific partner (by name or identifier), capability, objective, prior experience, budget figure, team size, or equipment item: check whether the claim's `traceability_footer.primary_sources[]` contains a reference pointing to a path within `docs/tier3_project_instantiation/`. If a project-fact claim carries no Tier 3 source reference in the artifact's traceability footer: violation. Severity: critical. Note: this skill does not read `docs/tier3_project_instantiation/` directly (not in reads_from); it checks only whether the artifact provides a Tier 3 source reference, not whether the referenced fact is present in the Tier 3 files.

**Check 13.4 — Phase 8 activity before budget gate:**
- Applicable to: all Phase 8 artifacts (schema_id begins with "orch.tier5." or "orch.phase8.").
- Check whether `docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json` exists with `gate_pass_declaration: "pass"`. If the artifact is a Phase 8 artifact AND this budget_gate_assessment either does not exist or has `gate_pass_declaration: "fail"`: violation. Severity: critical.
- For proposal sections: scan content for any budget figure references (patterns like "€[0-9]+", "[0-9]+ EUR", "[0-9]+ person-months" used as confirmed values). If any budget-dependent claims are present without a passing budget gate: violation.

**Check 13.5 — Durable decisions held only in agent memory:**
- Not directly checkable by reading an artifact. Skip for artifact-level check. Record check_status: "pass" (cannot verify from artifact content alone; this is enforced by decision-log-update skill).

**Check 13.6 — Skill becoming a de facto constitutional authority:**
- Not directly checkable from an artifact. Skip. Record check_status: "pass".

**Check 13.7 — Silent phase reordering:**
- Check whether the artifact references activities from a phase higher than the current phase in its `run_id` or phase context. If a Phase 3 artifact (wp_structure.json) references Phase 5 outputs as inputs: violation. Severity: critical.

**Check 13.8 — Finalised text with incomplete source state:**
- Applicable to: Tier 5 deliverable artifacts.
- For each proposal section: check `validation_status.overall_status`. If `overall_status: "unresolved"`: the section contains unresolved content. Check whether this is flagged in the section's content with explicit language (e.g., "[DATA REQUIRED: ...]", "INCOMPLETE:", "FLAGGED AS INCOMPLETE"). If unresolved status is present but NOT explicitly flagged in the section content: violation (the section appears complete but has unresolved claims). Severity: critical.

**Check 13.9 — Generic programme knowledge as substitute for Tier 1 documents:**
- Check whether any claim in the artifact that references Horizon Europe rules (participation conditions, grant agreement terms, financial regulation) has a `source_ref` in `traceability_footer.primary_sources[]` pointing to a path within `docs/tier1_normative_framework/extracted/`. If a regulatory claim carries no Tier 1 source reference in the artifact's traceability footer: violation. Severity: major. Note: this skill does not read `docs/tier1_normative_framework/extracted/` directly (not in reads_from); it checks only whether the artifact's traceability footer contains a Tier 1 path reference, not whether the referenced file exists.

**Check 13.10 — Tier 5 outputs not traceable to Tier 1–4:**
- Applicable to: all Tier 5 artifacts.
- Check `traceability_footer.no_unsupported_claims_declaration`. If false: examine `validation_status.claim_statuses[]` for any entries with status "unresolved" that lack a source_ref. For each unresolved claim with no source_ref in traceability_footer: violation. Severity: critical.

**Check 13.11 — Tier 1 or Tier 2 source documents modified to reflect project assumptions:**
- Not checkable from a phase output or deliverable artifact. Skip. Record check_status: "pass".

**Check 13.12 — CLAUDE.md treated as advisory:**
- Not directly checkable from an artifact. Skip. Record check_status: "pass".

- Step 2.2: For each violation found: determine whether a resolution decision is needed (i.e., whether the violation must be logged to the decision log because it may affect future interpretation). A violation requires a decision log entry if: it is severity critical, OR if the invoking agent has flagged it as requiring durable recording.

### 3. Output Construction

**Compliance report file (e.g., `compliance_check_<artifact_slug>_<timestamp>.json`):**
- `report_id`: `"compliance_check_<artifact_slug>_<agent_id>_<ISO8601_timestamp>"`
- `skill_id`: `"constitutional-compliance-check"`
- `invoking_agent`: from agent context
- `run_id_reference`: from agent context
- `artifact_audited`: the `artifact_path` provided by the invoking agent
- `section13_checks`: array — one entry per prohibition 13.1–13.12: `{prohibition_id (e.g., "13.1"), prohibition_description (short description), check_status ("pass"/"violation"), violation_evidence (quoted text or null), severity ("critical"/"major" or null)}`
- `summary`: `{total_prohibitions_checked: 12, violations_found: <count of violation entries>}`
- `timestamp`: ISO 8601

**Decision log entry (written ONLY when a violation is found and requires durable recording):**
- `decision_id`: `"constitutional_violation_<agent_id>_<ISO8601_timestamp>"`
- `decision_type`: `"constitutional_violation"`
- `violation_id`: `"<prohibition_id>_<artifact_slug>_<timestamp>"`
- `constitutional_rule_ref`: e.g., `"CLAUDE.md §13.3"`
- `artifact_affected`: the `artifact_path`
- `resolution_status`: `"unresolved"` (violations are flagged; they are not resolved by this skill)
- `resolution_note`: `"Constitutional violation detected; requires human operator resolution"`
- `tier_authority_applied`: `"CLAUDE.md §13"`
- `timestamp`: ISO 8601

### 4. Conformance Stamping

Validation reports and decision log entries are not phase output canonical artifacts. No `schema_id` or `artifact_status` applies.

### 5. Write Sequence

- Step 5.1: Write the compliance report to `docs/tier4_orchestration_state/validation_reports/<report_id>.json`
- Step 5.2: For each violation requiring a decision log entry: write to `docs/tier4_orchestration_state/decision_log/<decision_id>.json`

## Constitutional Constraint Enforcement

*Step 6 implementation — skill plan §4.6 and §7 Step 6. Each constraint from `skill_catalog.yaml` is mapped to a specific decision point in the execution logic and enforced as a hard failure. Cross-checked against CLAUDE.md §13.*

---

### Constraint 1: "Must check against CLAUDE.md Section 13 prohibitions as a minimum"

**Decision point in execution logic:** Step 1.4 and Step 2 — at the point CLAUDE.md §13 is read and all 12 checks (13.1–13.12) are applied.

**Exact failure condition:** (a) The skill does not apply all 12 §13 checks to the artifact (i.e., any check is skipped without a recorded justification that it is not applicable); OR (b) CLAUDE.md is not read before the checks are applied (i.e., checks are applied from agent memory of §13 rather than from reading the current CLAUDE.md); OR (c) fewer than 12 `section13_checks` entries appear in the compliance report.

**Enforcement mechanism:** In Step 1.4, reading CLAUDE.md §13 is mandatory and must occur before Step 2. In Step 2, all 12 checks must appear in the `section13_checks` output array — including those that are skipped for the specific artifact (13.5, 13.6, 13.11, 13.12), which must be recorded with `check_status: "pass"` and an explicit reason for not being applicable to artifact-level checks. If the compliance report would have fewer than 12 entries: return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="compliance report has <n> section13_checks entries; all 12 CLAUDE.md §13 prohibitions must be checked as a minimum"). No compliance report written.

**Failure output:** SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT"). No report written.

**Hard failure confirmation:** Yes — all 12 §13 checks are mandatory; any omission makes the report constitutionally incomplete.

**CLAUDE.md §13 cross-reference:** This constraint is self-referential: the skill's own constitutionality depends on checking all 12 §13 prohibitions. §10.1 — "Every agent operating in this repository must consult this constitution before taking action."

---

### Constraint 2: "Constitutional violations must be flagged; they must not be silently resolved"

**Decision point in execution logic:** Step 2 — at the point each violation is found and classified; and Step 3 — at the point the compliance report and decision log entry are written.

**Exact failure condition:** (a) A violation is detected during execution but assigned `check_status: "pass"` in the output; OR (b) a critical violation is found but no decision log entry is written when a decision log write is required (when the violation requires durable recording per Step 2.2); OR (c) a violation is "resolved" by the skill itself (e.g., the skill modifies the artifact it is checking, or records the violation as resolved in the decision log rather than as unresolved requiring human operator action).

**Enforcement mechanism:** In Step 2, if any check identifies a violation: `check_status` must be set to "violation" — it must not be downgraded to "pass" by agent judgment. In Step 3, the decision log entry (when required) must have `resolution_status: "unresolved"` — this skill does not resolve constitutional violations, it flags them. Setting `resolution_status: "resolved"` in a decision log entry written by this skill is a constitutional violation. If a violation is found but the compliance report write fails: return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason="Compliance report write failed; constitutional violations must be flagged in the durable report per CLAUDE.md §12.3"). If a decision log write fails for a critical violation: return SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT"). Silently absorbing a violation (recording it internally but not writing it to the compliance report) is prohibited.

**Failure output:** Report write failure → SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT"). Violation silencing → SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT").

**Hard failure confirmation:** Yes — violation silencing is a constitutional violation; accurate flagging is the only permitted response.

**CLAUDE.md §13 cross-reference:** §12.3 — "Contradictions between tiers must be resolved explicitly … A contradiction must not be silently resolved by selecting the more convenient source." §15 — "A declared failure is an honest and correct output. A fabricated completion is a constitutional violation."

---

### Constraint 3: "CLAUDE.md governs this skill; this skill does not govern CLAUDE.md"

**Decision point in execution logic:** This constraint applies to the skill's scope definition — it is enforced by what the skill does NOT do, verified at the scope boundary.

**Exact failure condition:** (a) The skill modifies, amends, or overwrites CLAUDE.md at any point during its execution; OR (b) the skill interprets a §13 check in a way that narrows or expands CLAUDE.md's prohibitions (e.g., deciding a check "doesn't apply" to certain artifacts without CLAUDE.md stating that exception); OR (c) the skill makes a "policy decision" about whether a §13 prohibition is valid or appropriate — i.e., it treats CLAUDE.md as advisory.

**Enforcement mechanism:** CLAUDE.md is declared in `reads_from` — the skill reads it as a source of checks to apply. It is not declared in `writes_to` — the skill must never write to CLAUDE.md. If any output construction step would produce a write to CLAUDE.md: return SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason="This skill attempted to write to CLAUDE.md; CLAUDE.md is the governing constitution and may not be modified by any skill per CLAUDE.md §14.5 and §10.2"). The checks in Step 2 are applied as stated in CLAUDE.md §13 — the skill has no authority to add, remove, or reinterpret checks. If a check's applicability to a specific artifact type is uncertain: the check must be applied conservatively (assume it applies) and the result documented — not silently skipped.

**Failure output:** SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT") for any attempt to modify CLAUDE.md.

**Hard failure confirmation:** Yes — any attempt to modify or override CLAUDE.md by this skill is an unconditional constitutional violation.

**CLAUDE.md §13 cross-reference:** §14.5 — "Amendments may not be made by agents, skills, or workflows operating autonomously." §10.2 — "Skills defined in .claude/skills/ are execution aids … A skill may not redefine phase meanings, tier meanings, gate logic, or the authority hierarchy."

<!-- Step 6 complete: constitutional constraint enforcement implemented -->

## Failure Protocol

*Step 7 implementation — skill plan §4.8 and §7 Step 7. All five failure categories are handled. For every failure: SkillResult(status="failure", failure_category=<category>, failure_reason=<non-null string>). No artifact is written to a canonical output path when a failure is declared.*

---

### MISSING_INPUT

**Trigger conditions in this skill:**
- Step 1.1: Invoking agent does not provide the `artifact_path` context parameter → `failure_reason="artifact_path required; invoking agent must specify which artifact to audit"`
- Step 1.2: Artifact at `artifact_path` does not exist or is not readable → `failure_reason="Artifact at <artifact_path> not found"`
- Step 1.3: `CLAUDE.md` is not accessible at the repository root → `failure_reason="CLAUDE.md not found; cannot perform constitutional compliance check"`

**Required response:** `SkillResult(status="failure", failure_category="MISSING_INPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No artifact written to any canonical output path. Skill halts immediately.

---

### MALFORMED_ARTIFACT

**Trigger conditions in this skill:**
This skill reads artifacts for auditing rather than for structured field extraction; schema mismatches in audited artifacts are findings recorded in the compliance report, not MALFORMED_ARTIFACT failures of the skill itself. No MALFORMED_ARTIFACT conditions are defined for this skill's own inputs.

**Artifact write behavior:** Not applicable for this skill.

---

### CONSTRAINT_VIOLATION

**Trigger conditions in this skill:**
No CONSTRAINT_VIOLATION conditions are defined for this skill; all constitutional constraint failures use CONSTITUTIONAL_HALT or INCOMPLETE_OUTPUT as appropriate.

**Artifact write behavior:** Not applicable.

---

### INCOMPLETE_OUTPUT

**Trigger conditions in this skill:**
- Constraint 1 (all 12 §13 checks applied): Compliance report would have fewer than 12 `section13_checks` entries → `failure_reason="compliance report has <n> section13_checks entries; all 12 CLAUDE.md §13 prohibitions must be checked as a minimum"`
- Constraint 2 (violations flagged, not silently resolved): Compliance report write fails after a violation is detected → `failure_reason="Compliance report write failed; constitutional violations must be flagged in the durable report per CLAUDE.md §12.3"`
- Constraint 2 (decision log write failure for critical violation): Decision log write fails for a critical violation requiring durable recording → `failure_reason="Decision log write failed for critical violation <violation_id>"`

**Required response:** `SkillResult(status="failure", failure_category="INCOMPLETE_OUTPUT", failure_reason=<specific reason>)`

**Artifact write behavior:** No partial write to any canonical output path. Skill halts before writing.

---

### CONSTITUTIONAL_HALT

**Trigger conditions in this skill:**
- Constraint 2 (violations not silently resolved): A violation is detected but the skill attempts to assign `check_status: "pass"` to suppress it → `failure_reason="Attempted to silence a constitutional violation by assigning pass status; accurate flagging is the only permitted response per CLAUDE.md §12.3 and §15"`
- Constraint 3 (CLAUDE.md governs this skill): Any output construction step would produce a write to `CLAUDE.md` → `failure_reason="This skill attempted to write to CLAUDE.md; CLAUDE.md is the governing constitution and may not be modified by any skill per CLAUDE.md §14.5 and §10.2"`

**Required response:** `SkillResult(status="failure", failure_category="CONSTITUTIONAL_HALT", failure_reason=<specific reason>)`

**Artifact write behavior:** Immediate halt. No canonical artifact written. A decision log entry MAY be written to `docs/tier4_orchestration_state/decision_log/` documenting the constitutional halt, as `decision_log/` is in this skill's declared `writes_to` scope.

---

### Universal Failure Rules

1. Every failure returns `SkillResult(status="failure")` with a non-null `failure_reason` string.
2. No canonical output artifact is written (partially or fully) when any failure category fires.
3. Exceptions: this skill's `writes_to` includes both `docs/tier4_orchestration_state/validation_reports/` and `docs/tier4_orchestration_state/decision_log/`; failure records MAY be written to those paths even when the primary output fails.
4. The invoking agent receives the `SkillResult` and is responsible for logging the failure and halting phase execution per its own failure protocol.
5. Failure is a correct and valid output. Fabricated completion is a constitutional violation per CLAUDE.md §15.

<!-- Step 7 complete: failure protocol implemented -->

## Schema Validation

*Step 8 implementation — skill plan §7 Step 8. Group C skill with dual output: a validation report and, conditionally, a decision log entry. Neither has a canonical `schema_id` in `artifact_schema_specification.yaml`; conformance is governed by CLAUDE.md §9.4, §12.1, §12.2, §12.3.*

---

### Artifact 1: `compliance_check_<artifact_slug>_<timestamp>.json` (validation report)

**Canonical schema:** None — operational validation report, not registered.

**Output Construction fields verification:**
| Field | Set by skill? | Governance | Conformant? |
|-------|---------------|------------|-------------|
| `report_id` | Yes (Step 3) | skill-defined | Yes |
| `skill_id` | Yes | matches frontmatter | Yes |
| `invoking_agent` | Yes | agent context | Yes |
| `run_id_reference` | Yes | agent context | Yes |
| `artifact_audited` | Yes | `artifact_path` input | Yes |
| `section13_checks[]` | Yes (Step 2, Step 3) | 12 entries, one per §13.1–§13.12 prohibition; each entry has prohibition_id, prohibition_description, check_status (enum: pass/violation), violation_evidence, severity (enum: critical/major or null) | Yes — 12-entry coverage is enforced by Constraint 1 (INCOMPLETE_OUTPUT) |
| `summary` | Yes | total_prohibitions_checked (=12), violations_found | Yes |
| `timestamp` | Yes | ISO 8601 | Yes |

### Artifact 2: `constitutional_violation_<agent_id>_<timestamp>.json` (decision log entry, conditional)

**Canonical schema:** None — operational decision log entry, not registered.

**Output Construction fields verification:**
| Field | Set by skill? | Governance | Conformant? |
|-------|---------------|------------|-------------|
| `decision_id` | Yes (Step 3) | skill-defined | Yes |
| `decision_type` | Yes — "constitutional_violation" | skill-defined | Yes |
| `violation_id` | Yes | skill-defined | Yes |
| `constitutional_rule_ref` | Yes | e.g., "CLAUDE.md §13.3" | Yes — references a named CLAUDE.md section as required by §14.2 |
| `artifact_affected` | Yes | `artifact_path` | Yes |
| `resolution_status` | Yes — "unresolved" | skill-defined; Constraint 2 prohibits "resolved" | Yes — matches §12.2 Unresolved semantics |
| `resolution_note` | Yes | explicit human-action requirement | Yes |
| `tier_authority_applied` | Yes — "CLAUDE.md §13" | required per CLAUDE.md §9.4 | Yes |
| `timestamp` | Yes | ISO 8601 | Yes |

**CLAUDE.md §12.2 vocabulary compliance:** The decision log entry uses `resolution_status: "unresolved"` — directly matches the §12.2 Unresolved category (conflicting evidence or missing information; resolution required before downstream use). The compliance report's per-check `check_status` uses (pass/violation) — a domain-specific operational enum for this skill's audit function. A "violation" finding semantically corresponds to Unresolved per §12.2 (the constitutional issue must be resolved before the audited artifact may advance). `violation_evidence` satisfies the §12.2 requirement to state the basis for the finding. No correction required.

**`schema_id` / `artifact_status`:** Step 4 correctly states these do not apply to either artifact.

**reads_from compliance:** Reads `CLAUDE.md`, `docs/tier4_orchestration_state/phase_outputs/`, and `docs/tier5_deliverables/`. All three declared in frontmatter. Compliant.

**writes_to compliance:** Writes to both `docs/tier4_orchestration_state/validation_reports/` and `docs/tier4_orchestration_state/decision_log/`. Both declared in frontmatter. Compliant.

**Gaps identified:** None.

**Corrections applied:** None.

<!-- Step 8 complete: schema validation performed -->

## Runtime Contract

This skill is governed by the skill runtime contract at `.claude/skills/skill_runtime_contract.md`. All execution behaviour — SkillResult envelope, failure protocol, schema stamping, artifact_status abstention, and scheduler separation — must conform to that contract.
