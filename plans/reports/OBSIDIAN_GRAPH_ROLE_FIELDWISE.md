# Obsidian graph — role for FIELDWISE

**Status:** decided 2026-08-17, operator-approved.
**Durable record:** `docs/tier4_orchestration_state/decision_log/obsidian-graph-role-fieldwise_2026-08-17.json`.
**Execution:** `plans/tickets_obsidian_graph_alignment.md` tickets 2-6.

This doc is a pointer, not the decision. The decision-log entry carries the full reasoning.

## The role in one paragraph

The graph is a parallel authoring and review surface plus a Tier-4 dashboard mirror. Nothing in the Phase 1-8 execution path reads the vault. It becomes authoritative for Tier 3 / Part B content only through the explicit human promote of DOD-1d (`dod-1d-open-q4-parallel-explicit-promote_2026-07-28.json`, "parallel + explicit promote"). The projector mirror is derived, read-only state.

## The four pinned points

### 1. Vault identity

The FIELDWISE vault is `MSCA/methodology_graph`, re-authored in place — not a fresh scaffold. This follows the standing quarantine record (`vault-supersession-fieldwise_2026-08-11.json`) and fieldwise ticket 12. Neutral folders (meta, sources, terminology, dashboards, governance) survive.

### 2. Sequencing

Ticket 12 said "after the run"; starting before n08f is a conscious, recorded relaxation. The authoring tool is deterministic, so later Tier 3 movement just means a cheap re-run.

### 3. Direction of authority

Unchanged from DOD-1d and the D6 split. Tier 4 flows docs→graph via the projector only; Tier 3 / Part B flow graph→docs via staging plus explicit promote only.

### 4. Revision cycle

Handout confirmations are authored in the vault, staged, diffed, then promoted into Tier 3. That feeds the A-2/A-5/A-8 resolutions n08f will disposition.

## Node-type vocabulary

No extension is sanctioned. Findings, actions and assumptions are surfaced through dashboards over existing node front-matter. Extending `NODE_TYPES` is a generic-layer change and needs its own recorded decision.

## What this does not do

It does not close the vault-supersession record. Closure still requires `graph_claim_verifier` green against the committed FIELDWISE Tier 5 sections (alignment ticket 5).
