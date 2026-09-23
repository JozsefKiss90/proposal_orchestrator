# Tickets: Milestone 2 — Obsidian Graph Track

Build tickets for milestone 2 — moving the authoring surface **into the Obsidian graph** and generalizing the system into a reusable, call-agnostic, multi-project tool. A deterministic, generic, config-driven compiler (modelled on `runner/call_slicer.py`) reads `proposal_section` + Tier-3/4-binding nodes from a per-project vault and **extracts** the canonical `docs/**` artifacts the runner and gates already consume; a projector mirrors Tier 4 state back into the graph. Source spec: `PHASE8_FULLSCALE_AND_OBSIDIAN_GRILL_BRIEF.md` §2.2–2.7 / §3 (milestone-2 deferrals) / §4; pointer: `MILESTONE2_SCOPE.md`.

"Done" for the milestone is earned on **authoring, traceability, and multi-project reuse** — *not* on length (milestone 1 solves that independently). The layer is proven generic when it passes a "no project nouns" lint and a throwaway second instance compiles with only its `graph.config.yaml` changed (§2.7).

## ⚠️ Prerequisite gate — milestone 1 must land first

Per `MILESTONE2_SCOPE.md` and `MILESTONE1_STATUS.md`, milestone 2 stages begin **"once the honest MSCA-PF run is green-or-blocked"** — milestone 1's **13B finalization** has **not** landed. Reading (operator decision: **pragmatic**):

- **Foundation / engine** tickets (1–7, 9) may start now. They run against artifacts that already exist — the `MSCA/` vault, the ticket-14 hand-lifted Tier 3 (explicitly "the compiler's test fixture"), and the milestone-1 deriver/schema — so they do not require the finalization run.
- **Authoring + real E2E** tickets (8, 10, 11) are gated on **milestone 1 (13B) landing** and on the real project data being consolidated to Confirmed/Inferred. They are marked accordingly and must not begin before then.

## Work the frontier

Pick any ticket whose blockers are all done (and whose prerequisite gate, if any, is satisfied).

- **Wave 0 (start now, parallel):** 1, 2
- **Wave 1:** 3, 4, 5
- **Wave 2:** 6, 7, 8
- **Wave 3:** 9, 10
- **Wave 4:** 11

## Orienting facts

- **Constitutional guardrails (span several tickets).** The compiler is pure-Python, deterministic, and **Step-0-style** — it runs *before* node dispatch (`--from-graph`) and makes **no change to §17 contracts, the DAG scheduler, or gate evaluation** (§2.4 / D9). The sync split is one-directional and non-overlapping (D6): `graph_to_docs` (compiler) owns **Tier 3 + Part B prose**; `docs_to_graph` (projector) owns **Tier 4 state + gate mirror**. Provenance is carried end-to-end via `evidence_strength → claim_statuses[].status` (Appendix B: `source_grounded→Confirmed`, `synthesis/inference→Inferred`, `unconfirmed→not finalizable`), so an unconfirmed node yields a claim the gates correctly block.
- **Ticket 1 is a prefactor.** It builds the generic schema/config/reader substrate once, so the compiler (3/6), projector (4), and pack-from-graph (7) are mechanical to add on top — the same "substrate first" pattern milestone 1 used (its tickets 1 and 15).
- **The compiler has a ready oracle.** Milestone-1 ticket 14 hand-lifted Tier 3 from the vault *specifically so the milestone-2 compiler can regenerate and diff against it*. Ticket 3's correctness check is `compile(vault) ≈ hand_lift`.
- **Two milestone-2-internal decisions are still open.** *(a) Open-Q #4* — whether the graph *becomes* the authoritative Tier 3 source or stays a parallel/diff surface — is deferred to ticket 10; tickets 3/6 stay **non-destructive (compile-and-diff)** until then. *(b)* The topology (submodule vs absorb) is ticket 2's to resolve.

*Out of scope. **G2 / RIA-40 pp** — the brief is explicit it "needs its own real consortium project"; it is a separate future milestone, not milestone-2-graph work. The milestone-1 build tickets (decomposed drafting, β/W1, unit-cost budget, `.docx`) live in `tickets.md`.*

---

## 1. Generic graph contract + deterministic vault reader

**What to build:** The project-agnostic substrate the whole track stands on — the schema superset (D7), the `graph.config.yaml` binding contract (D15), and a pure-Python reader. No extraction or output yet; this is the prefactor that makes tickets 3, 4, 6, and 7 mechanical.

**Blocked by:** None — can start immediately.

- [ ] The methodology-graph schema is extended to an **additive superset**: new `node_type`s (at minimum `proposal_section`, plus Tier-3/4-binding types for objectives / outcomes / impacts / work packages / timeline / budget / phase-gate state) and additive-optional front-matter (`tier`, `phase`, `artifact_path`, `sub_section_id`). Every existing 87 methodology node still validates unchanged — no new required field.
- [ ] A `graph.config.yaml` contract binds folders / `node_type`s → target tier + canonical `artifact_path` **generically**: the config file carries the project-specific bindings, the schema and reader carry none.
- [ ] A pure-Python reader (no Claude, no domain reasoning) deterministically parses a vault — YAML front-matter, body prose, and wikilinks (basename resolution) — and resolves `graph.config.yaml`. Same vault ⇒ same parse.
- [ ] The Appendix-B mapping (`source_grounded→Confirmed`, `synthesis→Inferred (framing)`, `inference→Inferred`, `unconfirmed→Assumed/Unresolved / not-finalizable`) is encoded as a **pure lookup**, no inference.
- [ ] The reader fails closed on a malformed or missing-front-matter node (naming the node), never a crash or a silent skip.

## 2. Graph topology decision + execution (D8)

**What to build:** Resolve and execute the embedded-`MSCA/`-repo topology that D10 deferred to D8 (submodule vs absorb), and fix where the generic-template home lives — without invalidating milestone-1's recorded re-instantiation provenance.

**Blocked by:** None — can start immediately.

- [ ] The submodule-vs-absorb decision is made and recorded in `docs/tier4_orchestration_state/decision_log/` with its rationale (§9.4).
- [ ] The chosen topology is executed: `MSCA/` becomes a proper submodule **or** is absorbed into the repo, with history/provenance handled per the decision.
- [ ] Milestone-1's recorded pin SHA (its ticket 3 / §9.5) stays traceable — the provenance record is **updated, not silently broken**.
- [ ] The generic-template home location (ticket 5) is fixed by this topology and documented.
- [ ] The engine, existing runs, and the `--from-graph` path read the vault from a stable, documented path under the chosen topology.

## 3. Graph→docs compiler — Tier 3 extraction (walking skeleton)

**What to build:** The first vertical slice of `runner/graph_compiler.py` — a deterministic Step-0-style pass that regenerates Tier 3 `architecture_inputs` JSON from existing vault nodes and diffs it against the ticket-14 hand-lift, non-destructively. The cheapest end-to-end proof the mechanism works, with a built-in oracle.

**Blocked by:** 1 (Generic graph contract + reader).

- [ ] `runner/graph_compiler.py` reads the vault via the ticket-1 reader and extracts Tier 3 `architecture_inputs` (objectives, outcomes, impacts, WP seed, risks, milestones seed) into the exact `docs/tier3_.../architecture_inputs/*.json` shapes the runner + gates consume.
- [ ] Invoked via a `--from-graph` entry point that runs **before node dispatch** (call_slicer-style), pure-Python and deterministic (same graph ⇒ byte-identical output, modulo timestamp), with **no change to §17 contracts, the DAG scheduler, or gate evaluation** (regression: an unchanged run schedules and gates identically).
- [ ] **Compile-and-diff is non-destructive:** the compiler writes to a diff/staging location and reports the diff against the existing ticket-14 hand-lift; it does **not** overwrite the hand-lift here (the graph-as-authoritative-source cutover, open-Q #4, is deferred to ticket 10).
- [ ] `evidence_strength` is carried into each extracted fact's status via the Appendix-B lookup — a `synthesis`/`inference` node never lands as a Confirmed Tier 3 fact.
- [ ] The compiler fails closed (naming the offending node/field) when a node binds a `tier`/`artifact_path` it cannot satisfy; it never fabricates a missing fact.
- [ ] A test asserts `compile(vault) ≈ hand_lift`, with any residual diff explained (the hand-lift is the compiler's fixture, per milestone-1 ticket 14).

## 4. Docs→graph projector + `sync_direction` no-overlap invariant (D6)

**What to build:** The `docs_to_graph` half of the sync split — mirror Tier 4 phase/gate state back into graph nodes so the dashboards reflect run state — plus the enforced no-overlap invariant that keeps the two directions from fighting over any artifact.

**Blocked by:** 1 (Generic graph contract + reader).

- [ ] A deterministic projector reads Tier 4 phase outputs + gate results and writes/updates `docs_to_graph`-owned graph nodes (a phase/gate-state mirror) via the substrate — no domain reasoning.
- [ ] The `sync_direction` invariant is enforced and tested: `graph_to_docs` owns Tier 3 + Part B prose; `docs_to_graph` owns Tier 4 state + gate mirror; **no `docs/**` path or graph field is written by both directions** (cross-checked against the compiler write-set from ticket 3's contract).
- [ ] The projector is idempotent (re-running on unchanged Tier 4 state changes nothing) and never mutates `graph_to_docs`-owned content.
- [ ] Projecting gate/phase state does not alter gate evaluation or freshness — the mirror is derived, downstream-read-only state.

## 5. Generic template home + `obsidian-graph` scaffolding skill + enable Dataview (D16)

**What to build:** The generic (no-project-nouns) template, a skill that scaffolds a fresh per-project vault from it, and Dataview enabled so dashboards stop being inert — the reusable multi-project entry point.

**Blocked by:** 1 (Generic graph contract), 2 (Graph topology — fixes the template home).

- [ ] A generic vault template lives at the topology-fixed home (ticket 2), carrying the schema superset (ticket 1), the folder skeleton (`00…18`), and template dashboards — with zero project nouns.
- [ ] An `obsidian-graph` scaffolding skill instantiates a fresh per-project vault from the template + a `graph.config.yaml`, producing a vault the reader/compiler accept.
- [ ] Dataview is **enabled** in the vault (`community-plugins.json` includes it and the plugin is present); the existing dashboards render live (no longer inert).
- [ ] The template passes the "no project nouns" lint (the lint is delivered/exercised in ticket 9); it carries no MSCA / crop / irrigation / partner nouns.

## 6. Extend compiler to Part B `proposal_section` extraction

**What to build:** The headline authoring move — compile full Part B prose from `proposal_section` nodes (one per sub-section) into the section JSON the retained Tier 5 schema and the Phase-8 gates consume, carrying provenance so unconfirmed content stays non-finalizable.

**Blocked by:** 3 (Compiler — Tier 3 extraction).

- [ ] The compiler extracts `proposal_section` nodes into `docs/tier5_.../proposal_sections/{excellence,impact,implementation}_section.json`, with `sub_sections[].content` = the node's **full body prose** (validators read the real text).
- [ ] `evidence_strength → validation_status.claim_statuses[].status` is carried per Appendix B; an `unconfirmed` node yields an `unresolved`/`assumed` claim the drafting gates correctly catch. Schema stays `…v1`; only additive-optional `source_nodes` / `page_estimate` are added (D4).
- [ ] The emitted section JSON validates against the retained Tier 5 section schema and is byte-stable for an unchanged graph.
- [ ] No prose is authored by the compiler — it extracts node bodies verbatim; a fixture-based test proves no synthesis (mirrors the milestone-1 assembler byte-equal guarantee).
- [ ] Section-specific fields the gates require (`impact_pathway_refs`, `dec_coverage`; `wp_table_refs`, `gantt_ref`, `milestone_refs`, `risk_register_ref`) are emitted from bound nodes, or the compiler fails closed naming the missing binding — it does not invent them.

## 7. Pack-from-graph — canonical reference pack from graph nodes (D13-graph)

**What to build:** Generate the canonical reference pack — which the preservation gates check prose against — from **graph nodes** with per-entry provenance. The graph-sourced successor to the milestone-1 (ticket-10) Tier-3-sourced deriver, so pack and prose share one source and cannot drift.

**Blocked by:** 3 (Compiler — establishes the reader/extraction path over nodes).

- [ ] A deriver produces `phase8_drafting_review/canonical_reference_pack.json` from graph nodes (partner names, deliverable identities, canonical terms, measurable targets), reusing the reader.
- [ ] Every pack entry carries provenance (source node + `evidence_strength`); an `unconfirmed`/assumed value is never emitted as a Confirmed canonical fact.
- [ ] Because pack and Part B prose share the graph as source, the canonical-preservation gates (contradiction detectors) pass against the regenerated pack for the compiled sections — no pack/prose drift.
- [ ] The deriver is deterministic and non-inferential (byte-stable for an unchanged graph).

## 8. Author the MSCA proposal graph (Stage 3 authoring)

**What to build:** Author the real proposal content into the vault — `proposal_section` nodes plus the Tier-3/4-binding folders — expanding it from methodology-only (87 nodes / 13 folders) to whole-proposal, so the compiler has real content to compile end-to-end.

**Blocked by:** 1 (Schema superset), 5 (Template + Dataview to author against). **⚠️ Prerequisite: milestone 1 (13B) must land first — real Confirmed/Inferred data.**

- [ ] New folders (`11…18`) bind the Tier 3 architecture inputs + Tier 4 / gate state per the schema (ticket 1); the vault covers objectives, WPs, timeline, impact, implementation, budget, and proposal sections — not only methodology.
- [ ] `proposal_section` nodes are authored (one per B1 sub-section) with `evidence_strength` set **honestly** per node — no `unconfirmed` content dressed as `source_grounded`.
- [ ] The researcher / host / call spine is authored as its real Confirmed/Inferred state **or** left explicitly `unconfirmed` — the graph does not invent the spine (ELTE remains refuted per the vault: "do not invent a role").
- [ ] The authored nodes compile cleanly through tickets 3 + 6 — the compiler accepts them with no fail-closed on missing bindings.

## 9. Agnosticism proof — "no project nouns" lint + throwaway second instance (D15 test-of-done)

**What to build:** The capstone generality check for the whole layer — the concrete "test of done for agnosticism" from §2.7: the generic layer carries no project nouns, and a second, unrelated vault compiles with only its config changed.

**Blocked by:** 5 (Generic template), 6 (Part B compiler — the full extraction surface to prove generic).

- [ ] A "no project nouns" lint runs over the generic layer (schema, reader, compiler, template) and **fails** if a project-specific noun (MSCA / crop / irrigation / partner names) appears; it passes on the current generic layer.
- [ ] A throwaway **second vault instance** (minimal, unrelated toy content) compiles to valid `docs/**` artifacts with **only its `graph.config.yaml` changed** — no code edit.
- [ ] The proof is captured (the second instance + its config diff) as the recorded test-of-done for agnosticism.

## 10. End-to-end graph-sourced MSCA-PF run + independent re-verify (Stage 3 E2E)

**What to build:** The full graph-sourced run that ties compiler + projector + pack + authoring together — compile the authored graph, run Phases 1–8, mirror state back, export — with independent verification, and resolve the graph-as-source-of-truth cutover.

**Blocked by:** 4 (Projector), 6 (Part B compiler), 7 (Pack-from-graph), 8 (Authored graph). **⚠️ Prerequisite: milestone 1 (13B) must land first.**

- [ ] `--from-graph` compiles the authored graph (ticket 8) → Tier 3 + Part B artifacts → Phases 1–8 run to a **green-or-honest-block** terminal state → the projector mirrors phase/gate state back into the graph → pack-from-graph feeds the preservation gates → Part B exports to `.docx`.
- [ ] Graph-sourced Tier 3 matches the ticket-14 hand-lift (or the residual diff is explained and accepted) — the compiler reproduces the hand-authored baseline.
- [ ] **Open-Q #4 is resolved and recorded in the decision log:** whether the graph *becomes* the authoritative Tier 3 source (compiler overwrites the hand-lift) or remains a parallel/diff surface.
- [ ] An **independent subagent** re-verifies that every material claim in the exported B1 traces to a specific graph node, and that no `docs_to_graph` / `graph_to_docs` overlap occurred.
- [ ] Both determinism checks hold on the graph-sourced artifacts (compiler byte-stability; pack byte-stability).

## 11. (Extension) B2 sections graph-authored

**What to build:** The identity-saturated B2 section set (researcher CV / participating-organisation capacities / ethics), authored in the graph and compiled + gated like B1 — the section set the graph surface is meant to make tractable.

**Blocked by:** 6 (Part B compiler), 8 (Authored graph). **⚠️ Prerequisite: milestone 1 (13B) must land first.**

- [ ] B2 sub-sections (researcher CV, participating-organisation capacities, ethics) are authored as `proposal_section` / binding nodes and compile to their canonical artifacts.
- [ ] The identity spine (researcher, host, supervisor) is honestly statused — `unconfirmed` where unconfirmed; the B2 sections **block honestly rather than fabricate**.
- [ ] B2 artifacts pass their instrument-mandated gates (or block naming the missing input), consistent with the MSCA-PF profile.
