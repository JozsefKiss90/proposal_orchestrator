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
  - docs/tier4_orchestration_state/phase_outputs/
  - docs/tier5_deliverables/
writes_to:
  - docs/tier4_orchestration_state/validation_reports/
  - docs/tier4_orchestration_state/decision_log/
constitutional_constraints:
  - "Must check against CLAUDE.md Section 13 prohibitions as a minimum"
  - "Constitutional violations must be flagged; they must not be silently resolved"
  - "CLAUDE.md governs this skill; this skill does not govern CLAUDE.md"
---

## Canonical Inputs and Outputs

### Inputs

| Path | Artifact / Content | Fields Extracted | Schema ID | Purpose |
|------|--------------------|-----------------|-----------|---------|
| `CLAUDE.md` | Repository constitution | Section 13 prohibitions (13.1–13.12); Section 7 gate conditions; Section 8 budget integration rules; Section 11 deliverable rules | N/A — constitutional document | The binding authority that defines all prohibited actions; every violation check is mapped to a named section in this document |
| `docs/tier4_orchestration_state/phase_outputs/` | Phase output directory — canonical artifacts from phases 1–8 | Phase-specific canonical artifact fields (varies by phase: call_analysis_summary, concept_refinement_summary, wp_structure, gantt, impact_architecture, implementation_architecture, budget_gate_assessment, drafting_review_status) | Context-dependent: the schema_id of the artifact being checked | Phase outputs being audited for constitutional violations; checked for fabricated facts, schema mismatches, gate bypasses, and other Section 13 violations |
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

<!-- Step 3 complete: front matter populated from skill_catalog.yaml -->
