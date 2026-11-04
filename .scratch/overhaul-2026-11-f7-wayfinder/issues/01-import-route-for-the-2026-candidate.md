# 01 — Can the 2026 candidate be imported as its own document with today's code?

Type: research
Status: open
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
