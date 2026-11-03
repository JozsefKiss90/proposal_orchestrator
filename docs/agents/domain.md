# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

This repo is **multi-context**. `CLAUDE.md` (the constitution) outranks every file listed here.

## Before exploring, read these

- **`CONTEXT-MAP.md`** at the repo root — it points at one `CONTEXT.md` per context. Read each one relevant to the topic:
  - `CONTEXT.md` (root) — proposal-domain vocabulary (Tier 3 / submission terms).
  - `runner/CONTEXT.md` — orchestration runtime vocabulary (phase, node, gate, skill, …).
  - `harness/CONTEXT.md` — evaluation harness vocabulary (judge, assessor, candidate, blind baseline, …).
- **`plans/reports/RUNTIME_MAP.md`** — a module/file navigation aid for `runner/` (not a glossary).
- **`docs/adr/`** — engineering ADRs that touch the area you're about to work in.

If any of these files don't exist, **proceed silently**. Don't flag their absence; don't suggest creating them upfront. The `/domain-modeling` skill creates them lazily when terms or decisions actually get resolved.

## Where decisions go

- **Engineering decisions** (module seams, refactors, test strategy) → `docs/adr/NNNN-*.md`.
- **Decisions that affect orchestration interpretation, traceability or reproducibility** → `docs/tier4_orchestration_state/decision_log/` (CLAUDE.md §9.4). An ADR does not satisfy §9.4.
- **Anything that changes constitutional meaning** → not an ADR. Surface it to the operator as a proposed amendment (CLAUDE.md §14.5).

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in the relevant `CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-0007 (…) — but worth reopening because…_
