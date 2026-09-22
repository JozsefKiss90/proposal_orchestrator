# Grill Brief → Plan of Record — Full-Scale Phase 8 Drafting, Obsidian Graph Integration, and MSCA Re-Instantiation

> **Version 3 (2026-07-10) — RESOLVED PLAN OF RECORD.** The milestone-1 `/grilling` session walked the full decision tree to resolution and reached shared understanding. **Stage 0 (constitutional ratification) is complete and applied.** This document is now the narrative of record; the canonical locked-decisions ledger is **`MILESTONE1_DECISION_RECORD.md`**, and the constitutional detail lives in the `CLAUDE.md` §8/§16/§17 amendment records (drafts: `PROPOSED_CONSTITUTIONAL_AMENDMENTS_milestone1.md`; insert-ready records: `RATIFICATION_CLAUDE_md_amendment_records.md`).
>
> **What v3 changes from v2.** The whole tree is resolved. The headline moves: the **Obsidian graph is deferred *in toto* to milestone 2** (D2 → decomposed drafting now); the **chunked writer is struck** and replaced by a **deterministic array-append assembler** (D3); granularity is **profile-driven**, "per-WP" struck as a RIA-ism (D5); the purge branches off **`backend_migration`** and pins the embedded `MSCA/` repo (D10); the unconfirmed-facts problem is handled by the **β block-default + operator-declared-assumption** mechanism with a hard **anti-bypass predicate (W1)** (D11); the budget amendment is **Option 1 — strict internal unit-cost derivation**, ratified as **C1** (D12); "done" is **B1-only, `.docx`** (D14).
>
> **Constitutional status.** C1 (§8/§7 budget), C2 (§17.5.3 deterministic components + `AgentResult.invoked_components`), and C3 (§16.5 bindable vocabulary) are **ratified and applied** to `CLAUDE.md` (§14.5). W1's operator-declared-`Assumed` guardrail needs **no** amendment — it *strengthens* a gate (§13.7-clean).

---

## 0. TL;DR (thesis — attacked and survived)

Two problems hid under "Part B is too short," and the grilling separated them:

**Transport (soft, cheap).** Each drafting skill is one `claude -p` call whose *only* hard limit is "total JSON < 20 KB"; the "3–5 sentences per sub-section" rules are soft prompt guidance. The Phase 8 gates enforce structure, traceability, and canonical-term preservation — **no length minimum anywhere across the 138 predicates**. So lifting length is cheap: raise the soft caps and split drafting into bounded units, composed by a deterministic assembler. **No Obsidian subsystem and no chunked writer are required** — decomposed `enrich_artifact`-style drafting already ships in Phases 5–6, and `_atomic_write` has no size limit, so a section of any length is assembled from ceiling-safe pieces.

**Substance (binding, hard).** Honest 40 pp needs 40 pp of *grounded* Tier 3. MAESTRO is fictional (and slated for purge); the MSCA vault is `source_grounded` on methodology but its researcher, host, and call are unconfirmed or absent. No prompt-ceiling change manufactures grounded content. **This is the real constraint**, and it is why the honest-block behaviour — not the page count — is the headline.

The resolved plan:

1. **Goal, not instrument (D1 = G3).** Instrument-parameterise; run the MSCA project honestly now; keep 40–50 pp RIA reachable later with a real consortium project.
2. **Length = decomposed drafting + a deterministic assembler (D2/D3/D5), no graph, no chunked writer.** Bounded per-sub-section calls → `section_drafts/` → array-append assembler → section JSON, validated by a byte-equal replay check.
3. **Honesty = β (D11).** Engine default blocks on unconfirmed identities; the operator may *declare* working assumptions to buy a conscious green, and a hard predicate (W1) makes "the engine never invents" true by construction.
4. **Budget = internal deterministic unit-cost (D12/C1).** The categorical block is preserved; only the budget *source* is instrument-conditional.
5. **The Obsidian graph is a separate, call-agnostic track (milestone 2)** — earned on authoring, traceability, and multi-project reuse, not on length. Deferring it *is* the proof it's separable (§2.7).

---

## 1. Current state — verified findings

All paths and numbers below were read from the repository and re-verified by four parallel fact-check agents (2026-07-09/10). Confidence is **Confirmed** unless marked.

### 1.1 What Phase 8 produces today

| Artifact | Path | Size | Shape |
|---|---|---|---|
| Excellence section | `docs/tier5_deliverables/proposal_sections/excellence_section.json` | 14.7 KB | 2 sub-sections (B.1.1 ~430 w, B.1.2 ~520 w) |
| Impact section | `…/proposal_sections/impact_section.json` | 11.2 KB | sub-sections + `dec_coverage`, `impact_pathway_refs` |
| Implementation section | `…/proposal_sections/implementation_section.json` | 20.6 KB | sub-sections + `wp_table_refs`, `gantt_ref`, `milestone_refs`, `risk_register_ref` |
| Assembled draft | `…/assembled_drafts/part_b_assembled_draft.json` | — | `sections[]` (by reference) + `consistency_log[]` |
| Review packet | `…/review_packets/review_packet.json` | — | `findings[]` (severity), `revision_actions[]` |

The three sections total ~3,350 words (Excellence 950, Impact 730, Implementation 1,670). A RIA/IA Part B hard limit is **40 pages (45 for lump-sum)** — `section_schema_registry.json → part_b_page_limit_hard: 40`. That is the ~10× gap the operator describes. For an MSCA action the relevant limit is different and shorter — see D1.

### 1.2 Why it is short — the real root cause

The cap is in the **drafting skills**, not the schema or gates:

| Skill | Output ceiling | Per-sub-section rule |
|---|---|---|
| `excellence-section-drafting.md` | **< 20,000 chars** total JSON | content < 2,500 chars; "3–5 concise sentences" |
| `impact-section-drafting.md` | **< 18,000 chars** | content < 2,000 chars |
| `implementation-section-drafting.md` | **< 20,000 chars** | content < 2,000 chars; "one paragraph per partner" |

**Only the `< 20 KB total JSON` line is imperative** — the per-sub-section "3–5 sentences" / "< 2,000–2,500 chars" rules are *soft prompt guidance* to the writer agent; nothing downstream enforces them (confirmed against `phase8_section_predicates.py`). So the transport ceiling is real but shallow: raising the soft caps is close to a one-line prompt change, and exceeding 20 KB per section is handled by **splitting drafting into bounded units and composing them with a deterministic assembler** (D2/D3/D5) — `_atomic_write` itself has no size limit, so no chunked/streamed writer is needed. **The ceiling is a transport constraint, not a quality decision — and not the binding constraint on a full-length proposal** (that is substance; §1.4 and Section 6).

### 1.3 What the Phase 8 gates actually check (the contract we must not break)

From `gate_rules_library.yaml` (gates `gate_10a/b/c` completeness, `gate_10d` consistency, `gate_11` review closure, `gate_12` constitutional compliance). None checks a minimum word or page count. What they *do* check:

- **Budget gate passed** (`gate_09_budget_consistency`) — the three drafting gates re-assert it directly (`g09a_p01`…); `gate_10d/11/12` uphold it transitively / via `budget_gate_confirmation_present`. Constitutional §8.4/§13.4.
- **Artifact hygiene** — `non_empty_json`, `artifact_owned_by_run` (run_id match), `schema_id_matches`.
- **Fields present** — `traceability_footer`, `validation_status`.
- **No unresolved claims** — `no_unresolved_material_claims` (fails iff `validation_status.overall_status == "unresolved"`; passes on `assumed`).
- **Canonical preservation vs `phase8_drafting_review/canonical_reference_pack.json`:**
  - `partner_names_preserved`, `deliverable_identity_preserved`, `canonical_terms_preserved`, `measurable_targets_preserved`.
- **Impact-specific** — `dec_coverage`, `impact_pathway_refs`. **Implementation-specific** — `wp_table_refs`, `gantt_ref`, `milestone_refs`, `risk_register_ref`.
- **Assembly/review** — `gate_10d` cross-section consistency; `gate_11` findings-by-severity + non-empty `revision_actions`; `gate_12` final constitutional compliance.

**Key consequence for the design (corrected in grilling).** The canonical-preservation predicates in `phase8_section_predicates.py` are **contradiction detectors, not completeness requirers**: `partner_names_preserved` does *not* demand a legal name beside every short name — it fires when a short name is conflated with the *wrong* legal name. So longer prose is **harder**, not easier: more text = more surface for a contradictory apposition. Two consequences: (i) the binding constraint on length remains the constitutional one — *no fabricated facts; everything traceable to Tier 1–4*; and (ii) the canonical reference pack must be generated from the **same** source as the prose (Tier 3 confirmed + declared assumptions), or the two drift into exactly the contradictions these gates catch — which makes **D13-r load-bearing**. `no_unresolved_material_claims` passing on `assumed` is precisely the lever the β mechanism (D11) uses.

### 1.4 The demo project vs the live target (the mismatch that drives everything)

| | Demo (in `docs/` now) | Live target (`MSCA/` vault) |
|---|---|---|
| Project | **MAESTRO** — multi-agent AI orchestration (fictional) | Crop water-stress monitoring & irrigation decision support (real, "MSCA-style") |
| Instrument | **RIA** (`selected_call.json → HORIZON-CL4-2026-05`, `instrument_type: RIA`) | **"MSCA-style"** (the vault's own word). PF is the likeliest of *five* MSCA forms on disk (`pf/dn/se/cofund/cofund-ce`) but is itself an **inference**, not a vault statement — to be confirmed in Stage 2, not assumed |
| Spine / consortium | 8 partners (ATU, BIIS, CERIA, …) with legal names, roles | Researcher-at-a-host spine is *definitional* for a fellowship, yet **all three of researcher, host, supervisor are unconfirmed or absent**. **The assumed host is refuted, not merely unconfirmed** — the vault host-role node: "host not mentioned in any source; do not invent a role." AgroVIR appears only as "AgroVIR-*like*"; PI inferred from authorship |
| Part B length | 40 pp (45 lump-sum) | MSCA-PF B1 is materially shorter (~10 pp) with a different section set |
| Budget | Lump-sum planner integration (placeholder response present) | MSCA is **unit-cost** (living/mobility/family + institutional unit costs) — handled by **C1** (instrument-conditional gate) |

Two facts make this more than a content swap:

- **Tier 2A is RIA-only.** `instrument_registry.json` is `{}`; `section_schema_registry.json` and `evaluator_expectation_registry.json` describe RIA/IA (a single `RIA` entry from the combined RIA/IA form — nothing IA-specific materialised). The MSCA form PDFs exist (`application_forms/msca/af_he-msca-pf_en.pdf` and four others) but are **unextracted**. Switching instrument means extracting MSCA Tier 2A schemas (Stage 2).
- **Tier 2B extracts are call-specific to MAESTRO.** All six cite `HORIZON-CL4-2026-05-DIGITAL-EMERGING-02.slice.json`. The MSCA work programme source *is* present (`work_programmes/msca/wp-2-marie-sklodowska-curie-actions_horizon-2026-2027_en.pdf` + `HORIZON-MSCA.json`), so re-extraction is feasible — the current extracts must be purged and regenerated for the MSCA call.

**Instrument-agnosticism is a constitutional value** (§2). The demo quietly hard-coded RIA assumptions into extracted registries and the budget gate. Re-instantiation (+ C1's source-conditionalisation) is the moment to make that parameterisation real.

### 1.5 The Obsidian graph today (milestone-2 input)

`MSCA/methodology_graph/` is a mature Obsidian vault of **87 nodes across 13 folders** (`00_meta … 10_research_questions`, `90_dashboards`, `99_governance`). It covers **methodology only** — there are **no** folders for objectives, WPs, timeline, impact, implementation, budget, proposal sections, or phase/gate state (so §2.5's expansion is greenfield). Governance is explicit:

- **`Methodology Graph Schema`** fixes a YAML front-matter contract for every node: `id` (`METH-<CAT>-<NNN>`), `node_type` (controlled vocab), `evidence_strength` ∈ {`source_grounded`, `synthesis`, `inference`, `unconfirmed`}, `confidence`, `maturity`, `source_refs`, `evidence_basis`, `upstream_nodes`/`downstream_nodes`/`related_nodes`, `open_questions`, `validation_needs`.
- **Wikilinks resolve by basename**; every node links up to a hub and cites ≥1 source.
- **Dashboards** are Dataview queries over `#methodology-graph` — but **Dataview is installed and *not enabled*** (only Smart Connections is enabled in `community-plugins.json`), so every dashboard is currently inert. Enabling Dataview is a milestone-2 prerequisite.

**The load-bearing alignment** (why the graph is the right *milestone-2* authoring surface): its `evidence_strength` taxonomy is essentially the constitution's validation taxonomy (§12.2) — `source_grounded → Confirmed`, `synthesis → Inferred (framing)`, `inference → Inferred`, `unconfirmed → Assumed/Unresolved`. It already speaks the orchestrator's provenance language.

---

## 2. Solution architecture

### 2.1 Instrument-parameterised Phase 8 (milestone 1 — serves MSCA now, RIA later)

An **instrument profile** resolved from `selected_call.json → instrument_type` supplies, per instrument: the mandatory section/sub-section set, the hard page limit, the budget regime, and which upstream phases are in scope. Phase 8 reads target length and section structure from the profile instead of assuming RIA. This satisfies §2 agnosticism and means the capability built for MSCA also serves a future RIA at 40–45 pp.

- MSCA-PF → B1 Excellence / Impact / Implementation (≈10 pp) + B2 (**deferred**), unit-cost budget (**C1**, ratified).
- RIA/IA → Excellence / Impact / Implementation, 40 pp (45 lump-sum), lump-sum budget gate (**G2**, later).

The criterion-aligned n08a/n08b/n08c DAG maps cleanly to both (MSCA-PF B1 is an Excellence/Impact/Implementation triptych), so the **DAG topology does not change** — only the profile behind it.

### 2.1.1 Milestone-1 content path (decomposed drafting → deterministic assembly)

Length is fixed with shipped machinery plus one new deterministic component:

- **Decomposed drafting (D2/D5).** Bounded per-sub-section `claude -p` calls (profile granularity, soft caps lifted, **sequential context-passing** for coherence) each write a per-sub-section draft to Tier 4 `phase8_drafting_review/section_drafts/`.
- **Deterministic array-append assembler (D3, §17.5.3-class).** Reads the drafts, array-appends them into `sub_sections[]`, carries `claim_statuses`/`validation_status` up **verbatim**, derives only `word_count` + `source_refs` union, and `_atomic_write`s the section JSON. Closed by the CI check `assembler(drafts) == section_json`. **No chunked writer; no `run_skill` change; §17 untouched** (C2 clarified the agent-runtime invocation).
- **β assumption-applier + W1 (D11).** Pre-assembly, a deterministic lookup flips enumerated `Unresolved → Assumed` from `working_assumptions.json`; the hard predicate `assumed_claims_are_operator_declared` on `gate_10a/b/c` guarantees every `Assumed` is operator-backed.

> **The graph-as-author path (§2.2–§2.7 below) is milestone 2.** It is the steady-state model for substance and traceability — *not* the length fix, which §2.1.1 solves independently. Everything in §2.2–§2.7 is deferred behind the decisions marked *(milestone 2)* in Section 3.

### 2.2 (Milestone 2) Author full prose in the graph; **extract** the JSON

Retain the Tier 5 section schemas as the validator contract. Move authoring of the evaluator-facing narrative into the graph as `proposal_section` nodes (one per sub-section); a deterministic compiler (§2.4) produces `excellence_section.json` etc. by extraction, carrying `evidence_strength → claim_statuses[].status` so an `unconfirmed` node yields an `unresolved`/`assumed` claim the gates correctly catch.

### 2.3 (Milestone 2) `content` and schema evolution

`sub_sections[].content` holds full prose (validators read the real text). Additive optional graph-provenance fields (`source_nodes`, `page_estimate`) — backward-compatible, schema stays `…v1` (D4). *(Milestone-1 note: `content` = full prose is already locked in D3; `source_nodes` is the milestone-2 graph field.)*

### 2.4 (Milestone 2) The graph→JSON compiler (Step-0-style, deterministic, runner unchanged)

A pure-Python compiler modelled on `runner/call_slicer.py`: reads the vault front-matter+body for nodes tagged with `tier`/`phase`/`artifact_path`; emits canonical Tier 3 JSON + Part B section metadata into the exact `docs/**` paths the runner and gates consume; runs before node dispatch (`--from-graph`); idempotent and auditable. **No change to §17 contracts, the DAG scheduler, or gate evaluation.**

### 2.5–2.7 (Milestone 2) Full-proposal graph, sync direction, and the call-agnostic multi-project design

The graph is expanded from methodology-only to whole-proposal (new folders `11…18` binding to Tier 3/4 artifacts); sync ownership is split `graph_to_docs` (Tier 3 + Part B prose) vs `docs_to_graph` (Tier 4 state + gate mirror), with a `sync_direction` no-overlap invariant (D6). The whole thing is defined **generically** — a call-agnostic schema/taxonomy/compiler that a per-project vault instantiates via `graph.config.yaml` (D15), scaffolded by an `obsidian-graph` skill (D16); `MSCA/methodology_graph/` becomes reference instance #1. **Test of done for agnosticism:** the generic layer passes a "no project nouns" lint and a throwaway second instance compiles with only its config changed.

---

## 3. Decision tree — RESOLVED

Every node is resolved. The canonical one-line ledger with build detail is **`MILESTONE1_DECISION_RECORD.md`**; the summaries below give the resolution and its rationale.

### Milestone-1 decisions (locked)

- **D1 — Live goal — RESOLVED: G3.** Instrument → *goal* was the real root. Run MSCA now, **instrument-parameterised**; "full-scale" ≡ up to the instrument limit; RIA-40 pp (G2) later with its own project. PF is inferred — confirm in Stage 2, don't hard-code.
- **D2 — Content-production model — RESOLVED: decomposed drafting now; graph → milestone 2.** The length fix is decomposed `enrich_artifact`-style drafting, already shipping. The graph earns its place on authoring/traceability/agnosticism, not length, and is deferred *in toto*.
- **D3 — `content` + write — RESOLVED: full prose + deterministic array-append assembler; chunked writer STRUCK.** `enrich_artifact` reserved for genuine enrichment (DEC, risk). Escaping the 20 KB *response* ceiling is decomposition + merge, not a streamed *write* (`_atomic_write` has no size limit).
- **D4 — Schema versioning — RESOLVED: v1, additive-optional, zero required.** Verified instrument-generic (free-string `sub_section_id`); enumeration lives in Tier 2A. `page_estimate` optional.
- **D5 — Granularity + coherence — RESOLVED: profile sub-section set; coarsest ceiling-safe unit.** "Per WP/pathway" struck as RIA-isms. Coherence = sequential context-passing now; escalation on front-of-section drift → deterministic lint → Claude revision (all draft-layer / byte-equal-safe); optional outline pre-pass.
- **D10 — Purge / git — RESOLVED.** `archive/maestro-demo` from the current pre-purge commit; work branches off **`backend_migration`**; embedded `MSCA/` = **pin-and-record SHA** (topology → D8). Skeleton-reset per §5; §5.3 fail-closed dry-run.
- **D11 — Unconfirmed facts — RESOLVED: β (block-default + operator-declared-assumption override).** Engine default blocks (identities → `Unresolved`, enumerated + checklist); operator may declare `working_assumptions.json` → flagged `Assumed` → conscious green. Enforced by **W1** (`assumed_claims_are_operator_declared`): every `Assumed` ⇔ a `manually_placed` declaration with `claim_summary == declared value`; `run_produced` can never back `Assumed`. **The engine never invents.**
- **D12 — Budget — RESOLVED: Option 1 (strict + internal), ratified as C1.** Unit-cost derived internally, deterministically (`months × rates × host_coeff`, byte-equal CI); `gate_09` instrument-conditional on **source only**; **categorical block preserved verbatim**; informative blocked assessment (host-independent lines computed) rides free.
- **D13 — Canonical pack — RESOLVED (split).** *D13-r (milestone 1):* generated deterministically from Tier 3 confirmed + `working_assumptions` declared values, **per-entry provenance** (same source as prose ⇒ no drift). *D13-graph (milestone 2):* pack from graph nodes.
- **D14 — Definition of done — RESOLVED: B1-only, `.docx` primary, B2 deferred.** Done = every Phase-8 gate **green** (all `Assumed` operator-declared) **or an honest block** naming the unconfirmed claims; every claim traceable to Tier 3 / a declared assumption; both CI checks pass; **independent subagent** re-verifies.
- **D17 — Depth of the honest block — RESOLVED: folds into β.** The run exercises the `source_grounded` methodology through Phases 1–7 and blocks-or-greens on the spine (researcher/host/call) supplied as confirmed facts or β-declared assumptions — so the block lands informatively.

### Milestone-2 deferrals (the graph track)

- **D6 — Graph⇄docs sync ownership** (the `sync_direction` no-overlap invariant).
- **D7 — Graph schema extension** (new `node_type`s, additive front-matter superset).
- **D8 — Graph placement + embedded-`MSCA/`-repo topology** (submodule-vs-absorb; owns the topology deferred by D10).
- **D9 — Compiler placement** (`runner/graph_compiler.py`, deterministic, `--from-graph`).
- **D13-graph — Canonical pack from graph nodes.**
- **D15 — Config-driven binding** (`graph.config.yaml`).
- **D16 — Generic template home + `obsidian-graph` scaffolding skill.**
- **B2** (CV / capacities / ethics — identity-saturated) and **G2 / RIA-40 pp** (needs its own real consortium project).

---

## 4. Sequenced implementation plan (corrected)

Milestone-1 stages. Milestone-2 (graph) stages follow once the honest MSCA-PF run is green-or-blocked. Full status table in `MILESTONE1_DECISION_RECORD.md`.

**Stage 0 — Ratify constitutional changes — ✅ DONE (2026-07-10).** C1 (§8/§7 budget, instrument-conditional source; block preserved), C2 (§17.5.3 deterministic node-body components + `AgentResult.invoked_components`), C3 (§16.5 bindable vocabulary) ratified per §14.5 and **applied** to `CLAUDE.md`; §14.3 review + §14.4 consistency check run. *Detail: the `CLAUDE.md` §8/§16/§17 amendment records; `RATIFICATION_CLAUDE_md_amendment_records.md`.* **W1** (the `assumed_claims_are_operator_declared` predicate) needs no ratification — build it in Stage 3–6.

**Stage 1 — Snapshot & purge (D10).** Create + tag `archive/maestro-demo` from the **current pre-purge commit** (keeps the MAESTRO demo runnable). Start the re-instantiation work on a branch off **`backend_migration`**. Commit the embedded `MSCA/` subrepo to a clean state and **record its SHA** as re-instantiation provenance (§9.5). Reset the MAESTRO instantiation per the §5 manifest. *Verify:* archive branch runs the old demo; `MSCA/` SHA recorded; purged paths are empty skeletons; §5.3 dry-run yields a clean fail-closed gate error naming missing Tier 3 inputs, not a crash.

**Stage 2 — Instrument profile + MSCA Tier 2A/2B extraction (D1).** First **confirm the actual MSCA action + call** the operator will submit to (PF likely, not assumed). Add an `instrument_profile` resolver keyed on `selected_call.json`. Extract that action's Tier 2A (`section_schema_registry`, `evaluator_expectation_registry`, `instrument_registry`, **page limit read from the form**) from its PDF; re-derive Tier 2B extracts from the MSCA work programme for the chosen call. Confirm the MSCA budget formula (living-allowance = base × host-country coefficient; other lines fixed) against the WP/AGA (§10.6) before the rates are trusted. *Verify:* Phase 1 gate passes for the MSCA call; `instrument_registry.json` non-empty; page limit from the form.

**Stages 3–6 — Build the decomposed-drafting path (D2, D3, D4, D5, D11, D12, D13-r) — Excellence-only vertical slice first.** Per the operator steer, the first build increment is a **single Excellence vertical slice**, not the full path. Build order: decomposed drafting skills (profile granularity, soft caps lifted, sequential context-passing) → `section_drafts/` intermediates → the deterministic **array-append assembler** → the **assumption-applier** (pre-assembly) → the **canonical-pack deriver** (Tier 3 + declared values, per-entry provenance) → the **W1** predicate on `gate_10a/b/c` → the instrument-conditional **`gate_09`** unit-cost deriver + informative blocked assessment. *Verify:* the Excellence section JSON validates; `assembler(drafts) == section_json` and `unit_cost_budget(…) == figure` byte-equal; `gate_10a` predicates green on full-length content; W1 rejects any un-declared `Assumed`. Then extend to Impact + Implementation.

**Stage 7 — End-to-end MSCA-PF run + export (D14, D17).** Run the confirmed MSCA-PF call through Phases 1–8 in two modes: **α** (no declarations → Phase 7 fail-closed block, informative assessment) and **β** (operator declares host+ → full B1). Export Part B to **`.docx`**. *Verify (per D14):* every gate is **green or honestly blocked on a named unconfirmed fact** — a legitimate block is a pass, not a failure; exported page count within the profile limit; spot-check 10 claims trace to Tier 3 / declared assumptions. **Use an independent subagent to re-verify traceability.**

*Milestone-2 stages (graph track): generic template + config (D7/D15/D16, incl. enabling Dataview) → compiler + projector (D6/D9) → author the proposal graph + pack-from-graph (D13-graph) → then B2 and G2/RIA-40 pp.*

---

## 5. Purge / retain manifest

Executed only in Stage 1, after the archive branch exists. "Reset" = delete contents, keep directory + a `.gitkeep`/skeleton. **D10 note:** archive from the *current* pre-purge commit; work branch off `backend_migration`; handle the embedded `MSCA/` gitlink by committing it to a clean recorded SHA (topology decision deferred to D8).

### 5.1 Purge (MAESTRO-specific, run-produced, or call-specific)

| Path | Action | Why |
|---|---|---|
| `docs/tier3_project_instantiation/project_brief/*` | Reset | MAESTRO concept/summary/positioning |
| `docs/tier3_project_instantiation/consortium/*` | Reset | MAESTRO partners/roles/capabilities |
| `docs/tier3_project_instantiation/call_binding/{selected_call,topic_mapping,compliance_profile}.json` | Reset | CL4 AI-agents call binding |
| `docs/tier3_project_instantiation/architecture_inputs/*` | Reset | MAESTRO objectives/outcomes/impacts/WP/risks/milestones |
| `docs/tier3_project_instantiation/integration/*` | Reset | MAESTRO budget request/response/refs |
| `docs/tier4_orchestration_state/phase_outputs/phase{1..8}_*/**` | Reset | All MAESTRO run state incl. gate results, `canonical_reference_pack.json` |
| `docs/tier4_orchestration_state/{decision_log,validation_reports,checkpoints,reuse}/*` | Reset | MAESTRO run history |
| `docs/tier5_deliverables/{proposal_sections,assembled_drafts,review_packets,final_exports}/*` | Reset | MAESTRO Part B |
| `docs/tier2b_topic_and_call_sources/extracted/*` | Reset & regenerate | CL4-specific slices → regenerate for the MSCA call |
| `docs/tier2a_instrument_schemas/extracted/*` | Regenerate for MSCA-PF | Currently RIA-only (D1 = MSCA) |
| `docs/integrations/lump_sum_budget_planner/{received,validation}/*` | Reset | MAESTRO placeholder budget (contract + templates retained) |
| `.claude/runs/*` | Reset | MAESTRO run contexts |

### 5.2 Retain (infrastructure, sources, programme-agnostic truth)

| Path | Why |
|---|---|
| `docs/tier1_normative_framework/**` (incl. `extracted/`) | Programme-agnostic legal/regulatory truth |
| `docs/tier2a_instrument_schemas/application_forms/**`, `evaluation_forms/**` | Source form PDFs (incl. all MSCA forms) |
| `docs/tier2b_topic_and_call_sources/work_programmes/**`, `call_extracts/**` | Source work-programme PDFs/JSON (incl. MSCA) |
| `docs/integrations/lump_sum_budget_planner/{interface_contract.json,request_templates/}` | Contract (retained; lump-sum only, per C1) |
| `runner/**`, `.claude/workflows/**`, `.claude/skills/**`, `.claude/agents/**`, `tests/**` | Engine, workflow, skills, agents, tests |
| `docs/index/*` | Registries — **update**, don't delete, to reflect new state (§9.6) |
| `CLAUDE.md`, `README.md`, `MSCA/**` | Constitution, docs, the source vault |

### 5.3 Post-purge integrity

After reset, run `python -m runner --run-id <uuid> --phase 1 --dry-run` and confirm a clean gate-failure that names the missing Tier 3 inputs (a correct fail-closed state, §12.4), not a crash.

---

## 6. Risks, tensions, and things most likely to be wrong

- **Full length × no-fabrication (the central tension).** Honest length needs grounded Tier 3; the MSCA vault is thin and partly unconfirmed. Mitigation: MSCA-PF's ~10 pp target fits; β makes the gaps explicit and blockable; RIA-40 pp is deferred to a project that can fill it. Insisting on 40–50 pp from the MSCA project would hit the fabrication wall — a reason to hold G2 for its own project, never to weaken §13.3.
- **The assembler / assumption-applier as shadow authorities.** If any deterministic component *infers* rather than *composes/looks-up*, it becomes an unlogged decision-maker (§9.4/§16). Mitigation: the byte-equal CI checks (`assembler(drafts) == section_json`) and W1 make "never synthesises / never invents" verifiable, not trusted.
- **Canonical-pack drift.** Because the canonical gates are contradiction detectors, pack and prose must share a source (D13-r). Per-entry provenance keeps a declared value from entering the pack as a confirmed canonical fact.
- **β misuse.** `Assumed`-status laundering is closed by W1; prose that fabricates *without emitting a claim* is the semantic gates' job (`no_unsupported_tier5_claims`, `no_gap_masked_as_confirmed`) — two threats, two mechanisms, no gap.
- **Gate freshness.** The `section_drafts/` intermediates are freshness-excluded; the section JSON is the sole gate/freshness artifact — otherwise re-drafting would false-invalidate gates.
- **MSCA instrument specifics** *(Inferred, confidence: medium — confirm against `af_he-msca-pf_en.pdf`).* PF B1 page limit, sub-section headings, and the unit-cost rate structure are stated from general Horizon knowledge, not yet read from the form. Stage 2 must extract them before they are trusted (§10.6).
- **Milestone-2 instance leakage.** When the graph track lands, a dashboard query/binding/compiler branch referencing MSCA specifics would break agnosticism — guarded by the "no project nouns" lint (§2.7). Not a milestone-1 concern.

---

## 7. Open questions — status

1. **Resolved: G3.** Residual for Stage 2: which specific MSCA action + call does the live run target (PF likely, unconfirmed), and who confirms it? (D1, D17)
2. **Resolved: β (D11).** The operator confirms the real spine or declares it via `working_assumptions.json`; until then the run legitimately blocks on named gaps.
3. **Resolved & applied: C1 (D12).** The §8 budget amendment is ratified; MSCA Phase 7 runs the internal unit-cost gate.
4. **Deferred to milestone 2 (D6):** whether the graph becomes *the* Tier 3 source of truth vs a parallel surface.
5. **Resolved: v1-additive (D4).**
6. **Resolved: `.docx` primary (D14).**
7. **Deferred to milestone 2 (D15/D16):** generic template home + scaffolding skill.

---

## Appendix A — Verified fact base (read 2026-07-09/10)

- Drafting ceilings: excellence/implementation < 20,000 chars, impact < 18,000; per-sub-section 2,000–2,500 chars, "3–5 sentences" — **soft except the `< 20 KB JSON` line** (confirmed vs `phase8_section_predicates.py`).
- No length predicate in `gate_rules_library.yaml` across the Phase-8 gates; canonical-preservation predicates are **contradiction detectors** comparing against `phase8_drafting_review/canonical_reference_pack.json`.
- `no_unresolved_material_claims` fails iff `overall_status == "unresolved"` (passes on `assumed`).
- RIA Part B hard limit 40 pp (45 lump-sum): `section_schema_registry.json` (single `RIA` entry from the RIA/IA form). `instrument_registry.json` = `{}`; MSCA forms present but unextracted.
- Tier 2B extracts reference `HORIZON-CL4-2026-05-DIGITAL-EMERGING-02`; MSCA WP PDF + `HORIZON-MSCA.json` present. `selected_call.json` = RIA, CL4, 48 mo, €19M. Budget integration lump-sum-specific, placeholder response present.
- MSCA vault: **87 methodology nodes / 13 folders**, strict YAML schema, `evidence_strength` taxonomy. **Dataview installed but *disabled***; dashboards inert until enabled. Researcher/host/call **unconfirmed or refuted** (ELTE explicitly "do not invent").
- Runtime: `call_slicer.py` deterministic Step-0 precedent; `run_skill` has only `cli-prompt`/`tapm` (both Claude); **no chunked writer** (`_atomic_write` only, no size limit); `enrich_artifact` decomposition already ships (Phase 5 `impact-dec-enricher`, Phase 6 `risk-register-builder`).
- Git: repo on branch **`AWS_deployment`**; `MSCA/` is an **embedded repo** (gitlink, no `.gitmodules`); `archive/maestro-demo` does not yet exist; `backend_migration` exists (the milestone-1 work base). Engine counts: **13 nodes / 14 gates / 20 agents / 27 skills / 138 predicates (52 distinct functions)**.

## Appendix B — Graph `evidence_strength` ⇄ constitution mapping

`source_grounded → Confirmed`; `synthesis → Inferred (framing)`; `inference → Inferred`; `unconfirmed → Assumed/Unresolved`. Used (milestone 2) by the compiler to populate `validation_status.claim_statuses[].status`; and (milestone 1) mirrored by the β assumption-applier, which flips only operator-declared `Unresolved → Assumed`.

---

*Plan of record (v3, 2026-07-10). Canonical ledger: `MILESTONE1_DECISION_RECORD.md`. Constitutional detail: `CLAUDE.md` §8/§16/§17 amendment records + `PROPOSED_CONSTITUTIONAL_AMENDMENTS_milestone1.md` + `RATIFICATION_CLAUDE_md_amendment_records.md`. Stage 0 applied; Stage 1 (purge) is the next action. Constitutional amendments require explicit human instruction per §14.*
