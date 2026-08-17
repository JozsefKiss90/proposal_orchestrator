# Tickets: Obsidian graph alignment for FIELDWISE

Bring the milestone-2 graph substrate up to speed with the live FIELDWISE run. Clarify the vault's role, re-author the quarantined vault for FIELDWISE, mirror the phase 1-8 state into it, and make it the working surface for the revision cycle. This is the meanwhile-track while the two handouts (`FIELDWISE_open_decisions.docx`, `FIELDWISE_PartB_draft_review_copy.docx`) are out for feedback. Nothing here touches run-id `845413cf` or the pending n08f node.

Work the **frontier**: any ticket whose blockers are all done.

## 1. Graph role clarification for FIELDWISE

**What to build:** A durable decision-log entry (per §9.4) plus a short role doc. It states what the graph is for this project, so no later session re-litigates it.

The decision must cover four points, reconciled with the standing `vault-supersession-fieldwise_2026-08-11.json` record. First, the FIELDWISE vault is the quarantined `MSCA/methodology_graph` re-authored in place (per fieldwise ticket 12), with neutral folders preserved — not a fresh scaffold. Second, the config is re-targeted with a FIELDWISE project id, and the before-n08f sequencing relaxation is recorded explicitly. Third, direction of authority per data class: Tier 4 flows docs-to-graph via the projector mirror; Tier 3 and Part B flow graph-to-docs only through compile staging plus the explicit human promote (the DOD-1d decision applies unchanged). Fourth, where the vault sits in the revision cycle once handout feedback returns.

**Blocked by:** None — can start immediately.

- [x] Decision-log entry written under Tier 4 with the four points above (`obsidian-graph-role-fieldwise_2026-08-17.json`)
- [x] Role doc in `plans/reports/` linking the standing records rather than restating them (`OBSIDIAN_GRAPH_ROLE_FIELDWISE.md`)
- [x] Explicit statement of whether any node-type vocabulary extension is sanctioned (decided: no)

## 2. Re-target the quarantined vault to FIELDWISE

**What to build:** The `MSCA/methodology_graph` vault prepared for re-authoring, per the role decision. Re-target `MSCA/graph.config.yaml` to `project_id: fieldwise-msca-pf`. Inventory the folders: neutral ones (00, 01, 09, 90, 99) stay; superseded project-specific content (02-08, 10-17, 19) is either purged here or listed for regeneration by tickets 4-5, with the disposition written down.

**Blocked by:** Graph role clarification for FIELDWISE.

- [ ] Config loads with the new project id; vault reads clean; no-overlap check holds
- [ ] Folder disposition inventory recorded (kept / purged / regenerated-by-which-ticket)
- [ ] Vault opens in Obsidian; dashboards render without stale-project noise
- [ ] Agnosticism lint still green; full test suite: no new reds beyond the known claim-verifier reds the supersession record already owns

## 3. Mirror live gate state into the vault

**What to build:** The real phase 1-8 gate map, visible in Obsidian. Run the docs-to-graph projector against the repo so the run-`845413cf` gate results appear as mirror nodes in the vault's phase-gate-state folder.

**Blocked by:** Re-target the quarantined vault to FIELDWISE.

- [ ] All durable Tier 4 gate results for the current run appear as `PGS-*` mirror nodes
- [ ] Mirror content matches the gate-result artifacts (spot-check gate_10d and gate_11)
- [ ] Re-running the projector on unchanged Tier 4 is byte-idempotent
- [ ] No `docs/**` path written; no-overlap check green

## 4. Author FIELDWISE Tier-3 binding nodes, prove round-trip

**What to build:** The vault's binding folders populated from the committed FIELDWISE Tier 3 architecture inputs, deterministically. Follow the `author_msca_proposal_graph.py` pattern: a deterministic lift tool, status-preserving, honest `evidence_strength`, no invented facts (§13.3).

The oracle is convergence: compiling the authored vault back to staging must reproduce the committed Tier 3 with residual 0.

**Blocked by:** Re-target the quarantined vault to FIELDWISE.

- [ ] Deterministic authoring tool lifts objectives, outcomes, impacts, work packages, timeline, risks into folders 11-17
- [ ] `--from-graph` staging converges: residual 0 against committed Tier 3
- [ ] Determinism re-check green (byte-identical modulo `compiled_at`)
- [ ] Staging only — no promote; committed `docs/**` untouched

## 5. Part B section nodes and claim-trace green

**What to build:** `proposal_section` nodes for the drafted FIELDWISE Part B sections, so the independent claim verifier passes over the live drafts — the same 12/12-style trace the MSCA vault achieved, now on real FIELDWISE state.

**Blocked by:** Author FIELDWISE Tier-3 binding nodes, prove round-trip.

- [ ] One `proposal_section` node per drafted sub-section, statuses matching the claim ledgers
- [ ] `graph_claim_verifier` passes: every claim id resolves to a node, status map honest
- [ ] Assumed claims remain visibly assumed in the vault (no silent upgrade to confirmed)
- [ ] Determinism re-check still green with Part B nodes present
- [ ] `vault-supersession-fieldwise` record closed out per its `closed_by` clause (contradiction_status → Confirmed, closing commit named)

## 6. Utilize: revision-cycle surface for the handout returns

**What to build:** The vault as the working surface for closing the revision cycle. The n08e review packet (8 findings, 8 actions) and the declared working assumptions become visible in the vault, within the existing node-type vocabulary (ticket 1 decided: no extension). A dashboard traces assumption to claim to section to open action.

When handout feedback lands, confirmations are authored here first, then flow through compile staging and the explicit promote into Tier 3 — feeding the A-2/A-5/A-8 resolutions (and A-1 once literature sources enter Tier 3) that n08f will disposition.

**Blocked by:** Mirror live gate state into the vault; Part B section nodes and claim-trace green.

- [ ] Review findings and actions represented in the vault, traceable to the review packet artifact
- [ ] Dashboard renders the assumption → claim → section → action trace
- [ ] Dry-run demonstrated: one sample confirmation authored, compiled to staging, diff shown, not promoted
- [ ] Promote path documented as the only write route into committed Tier 3 (DOD-1d)
