# Context map

`CLAUDE.md` is the constitution and outranks everything below. Each CONTEXT.md is a glossary only.

## Contexts

- [Proposal domain](./CONTEXT.md) — vocabulary of the instantiated proposal (Tier 3) and its submission.
- [Orchestration runtime](./runner/CONTEXT.md) — phases, nodes, gates, agents, skills, deterministic components.
- [Evaluation harness](./harness/CONTEXT.md) — judge, assessor, candidates, blind assessment, DN pre-evaluation.

Navigation aid (files and modules, not vocabulary): [`plans/reports/RUNTIME_MAP.md`](./plans/reports/RUNTIME_MAP.md).

## Relationships

- **Runtime → Proposal domain**: the runtime turns Tier 3 instantiation data into Tier 4 state and Tier 5 sections.
- **Harness → Runtime**: one-way. The harness reads runtime artifacts and may import runtime code; the runtime never depends on the harness, and no harness output is ever a gate.
- **Harness ↔ Proposal domain**: a candidate is either a pipeline output (Tier 5 sections) or an imported candidate that never passed through Tier 3.

## Decisions

Engineering ADRs: `docs/adr/`. Orchestration decisions: `docs/tier4_orchestration_state/decision_log/`.
