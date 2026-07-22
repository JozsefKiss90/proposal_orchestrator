# Milestone 2 — Scope (CORRECTED)

> **This file previously contained a wrong scope** (extending the β / identity-spine substrate to Phases 2–6). That was **off-roadmap and is retracted.** The β mechanism is a *milestone-1* device (D11); it is not milestone 2. See the retraction note at the bottom.

**Milestone 2 is the Obsidian graph track**, exactly as defined in the plan of record
`PHASE8_FULLSCALE_AND_OBSIDIAN_GRILL_BRIEF.md` §2.2–2.7 and the milestone-2 deferrals in §3. This file is a pointer, not a re-authoring — the brief is the single source of truth.

## What milestone 2 is

Milestone 1 fixes **length and honesty inside the current drafting engine for one real MSCA project**. Milestone 2 **changes the authoring surface itself** — graph-as-source-of-truth — and **generalizes the system into a reusable, call-agnostic, multi-project tool.** It is earned on authoring, traceability, and multi-project reuse, *not* on length (which milestone 1 solves independently). Deferring it entirely is itself the proof that it is separable (brief §2.7).

## The deferred decisions that constitute it (from the brief §3)

- **D6** — Graph⇄docs sync ownership; the `sync_direction` no-overlap invariant (`graph_to_docs` = Tier 3 + Part B prose; `docs_to_graph` = Tier 4 state + gate mirror).
- **D7** — Graph schema extension (new `node_type`s; additive front-matter superset).
- **D8** — Graph placement + embedded-`MSCA/`-repo topology (submodule vs absorb; owns the topology deferred by D10).
- **D9** — Compiler placement (`runner/graph_compiler.py`, deterministic, `--from-graph`, Step-0/`call_slicer`-style; **no §17 / DAG / gate change**).
- **D13-graph** — Canonical reference pack generated from graph nodes.
- **D15** — Config-driven binding (`graph.config.yaml`) so one generic layer instantiates per project.
- **D16** — Generic template home + an `obsidian-graph` scaffolding skill.

## Milestone-2 architecture (brief §2.2–2.7, in one paragraph)

Retain the Tier 5 section schemas as the validator contract, but move authoring of the evaluator-facing narrative **into the graph** as `proposal_section` nodes (one per sub-section). A pure-Python, deterministic compiler (modelled on `runner/call_slicer.py`) reads node front-matter + body and **extracts** canonical Tier 3 JSON + Part B section metadata into the exact `docs/**` paths the runner and gates already consume — carrying `evidence_strength → claim_statuses[].status` so provenance is preserved end to end (`source_grounded → Confirmed`, `synthesis/inference → Inferred`, `unconfirmed → not finalizable`; Appendix B). The graph is expanded from methodology-only (87 nodes / 13 folders today) to the whole proposal (new folders binding Tier 3/4 artifacts). The **entire layer is defined generically** — schema, taxonomy, compiler — and a per-project vault instantiates it via `graph.config.yaml`; `MSCA/methodology_graph/` becomes reference instance #1. **Test of done for agnosticism:** the generic layer passes a "no project nouns" lint and a throwaway second instance compiles with only its config changed. (Prerequisite: enable Dataview in the vault — installed but currently disabled, so dashboards are inert.)

## Sequenced milestone-2 stages (brief §4, final paragraph)

1. Generic template + config (D7/D15/D16, incl. enabling Dataview).
2. Compiler + projector (D6/D9).
3. Author the proposal graph + pack-from-graph (D13-graph).
4. Then **B2** (CV / capacities / ethics) and **G2 / RIA-40 pp** (needs its own real consortium project).

## Prerequisite: milestone 1 must land first

Milestone 2 stages begin **"once the honest MSCA-PF run is green-or-blocked"** (brief §4). Milestone 1 is **not yet there** — the end-to-end Phase-8 finalization (D14/Stage 7) has not run. Do not start milestone 2 until milestone 1's deliverable exists. See `MILESTONE1_STATUS.md`.

---

### Retraction note

The prior contents of this file proposed extending the β / operator-declared-`Assumed` substrate across Phases 2–6 with W1-equivalent guards. That was wrong for two reasons: (1) it mislocated a milestone-1 mechanism (D11) as milestone 2; and (2) it pointed the architecture toward institutionalizing `Assumed` as a permanent pipeline input, when the intended finalization standard is **Confirmed / Inferred only** — `Assumed`/`Unresolved` are pre-consolidation scaffolding. Retracted 2026-07-14 on operator correction.
