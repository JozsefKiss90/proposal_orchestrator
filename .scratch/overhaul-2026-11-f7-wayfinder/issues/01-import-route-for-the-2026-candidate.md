# 01 — Can the 2026 candidate be imported as its own document with today's code?

Type: research
Status: resolved
Blocked by: None
Map: ../map.md

## Question

Can the revised 2026 DN Part B be imported on the private host as a **new candidate** with its own intake
id, revision entry, manifest, fidelity register, declarations and preflight, using only the existing
route? That route is `tools/import_external_proposal.py --config-input` (V07), dry import and provenance
(V08), the configuration route (V17) and the submitted-document register (V18), as the runbook §7
describes. Or does any step assume "the 2025 original" or "the sanitised copy" in code (hard-coded intake
ids, profile ids, document versions, register renderers)?

Answer with: a yes/no per step, every code assumption found (file:line), and for each one either "config
only" or "code change needed (est. size)". Read only. Use synthetic or template config, never private content.

## Answer (2026-11-06)

Full findings: [../W01-findings.md](../W01-findings.md).

- **No with today's code, but only because the importer's document set is closed** (`DOCUMENTS`, three
  entries; `tools/import_external_proposal.py:1042`, refusals at `:1093`, `:1224`; `dry_import_original.py:593`).
  The 2026 resubmission cannot be a revision of `official_original`, whose identity is the 2025 submission.
- **Every step's behaviour is generic** (keyed on the configuration and `is_submitted_document`), so after
  the entry V08, V17, V18, preflight, assessment, freeze, audit and receipt are config only.
- **Must-land W-1:** declare a fourth, submitted-document `DocumentConfig` for the 2026 resubmission
  (~60–80 lines, one module, tests parametrised over both submitted documents). Assumes the 2026 Part B keeps
  the three MSCA-DN sections; W02 to confirm.
