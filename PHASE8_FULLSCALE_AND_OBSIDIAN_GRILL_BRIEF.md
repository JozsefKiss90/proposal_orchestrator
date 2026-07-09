# Grill Brief — Full-Scale Phase 8 Drafting, Obsidian Graph Integration, and MSCA Re-Instantiation

> **Purpose.** This is the seed document for a `/grilling` session (`.claude/skills/grill-me` → `.claude/skills/grilling`). It states the problems, the proposed solutions, an implementation-and-purge plan, and — most importantly — a **decision tree** in which every node carries a *recommended answer*. During grilling we walk the tree one decision at a time, resolving dependencies before moving on. Nothing here is enacted until we reach shared understanding and you confirm.
>
> **Scope confirmed with the operator (2026-07-09):**
> 1. Target instrument is treated as an **open fork** (Decision D1, the root); Phase 8 is designed instrument-parameterised.
> 2. This brief includes a **sequenced implementation plan and an exact purge/retain manifest** (nothing executed here).
> 3. The Obsidian graph is an **authoring surface + deterministic compiler to canonical JSON**; the DAG runner's runtime contracts stay unchanged.
> 4. The Obsidian integration is **call-agnostic and configurable across all projects** — a generic template/schema/compiler that a per-project vault instantiates — mirroring the orchestrator's §2 agnosticism. Added on operator instruction, 2026-07-09; see §2.7 and D15–D16.
>
> **Constitutional note.** Several proposed changes touch `CLAUDE.md` (§8 budget, §17 runtime, phase/gate definitions). Per §14, constitutional amendments require explicit human instruction. Where a change is constitutional, it is tagged **[AMENDMENT]** and must be ratified before implementation, not folded in silently.

---

## 0. TL;DR (the thesis to attack)

The orchestrator does not under-produce Part B because of the schema or the gates. It under-produces because **each drafting skill is a single Claude-transport invocation capped at ~18–20 KB of JSON** ("3–5 concise sentences per sub-section"). The gates enforce *structure, traceability, and canonical-term preservation* — **none of them enforce a length minimum**, and several *canonical-preservation* predicates actually get **easier** as prose gets longer and more complete.

So the path to full-scale (up to the active instrument's hard page limit) is:

1. **Decouple authoring from the transport ceiling.** Full Part B prose is authored/curated as Obsidian graph nodes (the natural home for evaluator-facing narrative), not squeezed through one sub-20 KB skill call.
2. **Keep the Tier 5 JSON schema as the validator contract.** A deterministic compiler *extracts* the section artifacts (`sub_sections[]`, `word_count`, `validation_status.claim_statuses[]`, `traceability_footer`) from the graph, carrying provenance from graph front-matter (`source_refs`, `evidence_strength`) into the exact fields the gates read. Runtime contracts (Section 17) are untouched.
3. **Make the whole thing instrument-parameterised**, because the live target (MSCA, single-researcher) is a different instrument from the demo (RIA, 8-partner consortium), with different sections, a different page limit, and a *different budget regime* (unit costs, not lump sum).
4. **Purge the MAESTRO instantiation** from Tier 3/4/5 (and the call-specific Tier 2B/2A extracts) and re-instantiate from the MSCA vault — honestly, which means most MSCA project facts start life flagged `unconfirmed`, and the gates *should* block finalization until they are confirmed. That is the constitution working, not failing.

5. **Keep the graph layer itself generic.** The whole Obsidian integration is a call-agnostic engine capability — a generic schema/taxonomy/compiler configured per project — that the MSCA vault merely *instantiates*. It ships empty and project-neutral, exactly like the tiers (§2.7).

If that thesis is wrong, the cheapest place to break it is Section 2 (the length root-cause) and Section 3 (the validator contract).

---

## 1. Current state — verified findings

All paths and numbers below were read from the repository on 2026-07-09. Confidence is **Confirmed** unless marked.

### 1.1 What Phase 8 produces today

| Artifact | Path | Size | Shape |
|---|---|---|---|
| Excellence section | `docs/tier5_deliverables/proposal_sections/excellence_section.json` | 14.7 KB | 2 sub-sections (B.1.1 ~430 w, B.1.2 ~520 w) |
| Impact section | `…/proposal_sections/impact_section.json` | 11.2 KB | sub-sections + `dec_coverage`, `impact_pathway_refs` |
| Implementation section | `…/proposal_sections/implementation_section.json` | 20.6 KB | sub-sections + `wp_table_refs`, `gantt_ref`, `milestone_refs`, `risk_register_ref` |
| Assembled draft | `…/assembled_drafts/part_b_assembled_draft.json` | — | `sections[]` (by reference) + `consistency_log[]` |
| Review packet | `…/review_packets/review_packet.json` | — | `findings[]` (severity), `revision_actions[]` |

The three sections total well under ~3,000 words of prose. A RIA/IA Part B hard limit is **40 pages (45 for lump-sum)** — `section_schema_registry.json → part_b_page_limit_hard: 40`. That is the ~10× gap the operator describes. (For MSCA-PF the relevant limit is different — see D1.)

### 1.2 Why it is short — the real root cause

The cap is in the **drafting skills**, not the schema or gates:

| Skill | Output ceiling | Per-sub-section rule |
|---|---|---|
| `excellence-section-drafting.md` | **< 20,000 chars** total JSON | content < 2,500 chars; "3–5 concise sentences" |
| `impact-section-drafting.md` | **< 18,000 chars** | content < 2,000 chars |
| `implementation-section-drafting.md` | **< 20,000 chars** | content < 2,000 chars; "one paragraph per partner" |

These ceilings exist for a sound architectural reason (Section 17.5): a skill is one `claude -p` call that returns **one JSON object**, which Python then parses, `_validate_skill_output()`s, and `_atomic_write()`s. A 40-page section cannot survive that path as a single response without truncation/parse risk. **The ceiling is a transport constraint, not a quality decision** — which is exactly why we can lift the length without touching the gate logic.

### 1.3 What the Phase 8 gates actually check (the contract we must not break)

From `gate_rules_library.yaml` (gates `gate_10a/b/c` completeness, `gate_10d` consistency, `gate_11` review closure, `gate_12` constitutional compliance). None checks a minimum word or page count. What they *do* check:

- **Budget gate passed** (`gate_09_budget_consistency`) — every Phase 8 predicate re-asserts it (`g09a_p01`…). Constitutional §8.4/§13.4.
- **Artifact hygiene** — `non_empty_json`, `artifact_owned_by_run` (run_id match), `schema_id_matches`.
- **Fields present** — `traceability_footer`, `validation_status`.
- **No unresolved claims** — `no_unresolved_material_claims` (fails if `validation_status.overall_status == "unresolved"`).
- **Canonical preservation vs `phase8_drafting_review/canonical_reference_pack.json`:**
  - `partner_names_preserved` — short names must carry canonical legal names.
  - `deliverable_identity_preserved` — deliverable IDs keep correct title/parent-WP/due-month.
  - `canonical_terms_preserved` — objective/WP titles not shortened or paraphrased.
  - `measurable_targets_preserved` — every quantitative component of each `measurable_target` appears verbatim.
- **Impact-specific** — `dec_coverage` (dissemination/exploitation/communication booleans), `impact_pathway_refs`.
- **Implementation-specific** — `wp_table_refs`, `gantt_ref`, `milestone_refs`, `risk_register_ref`.
- **Assembly/review** — `gate_10d` cross-section consistency; `gate_11` findings-by-severity + non-empty `revision_actions`; `gate_12` final constitutional compliance.

**Key consequence for the design:** longer, more complete prose makes the *canonical-preservation* predicates **easier** (more room to spell out full legal names, full targets). The predicate that gets **harder** at 40 pages is the constitutional one — *no fabricated facts; everything traceable to Tier 1–4*. That is the real budget we spend when we scale length, and it is the reason the graph's provenance metadata (`source_refs`, `evidence_strength`) has to flow into `claim_statuses` and `traceability_footer`.

### 1.4 The demo project vs the live target (the mismatch that drives everything)

| | Demo (in `docs/` now) | Live target (`MSCA/` vault) |
|---|---|---|
| Project | **MAESTRO** — multi-agent AI orchestration (fictional) | Crop water-stress monitoring & irrigation decision support (real, "MSCA-style") |
| Instrument | **RIA** (`selected_call.json → HORIZON-CL4-2026-05`, `instrument_type: RIA`) | MSCA — most consistent with **Postdoctoral Fellowship (PF)**: PI + host (ELTE) + associated partner (AgroVIR) |
| Consortium | 8 partners (ATU, BIIS, CERIA, …) with legal names, roles | **Largely unconfirmed** — "AgroVIR-*like*" partner only; "ELTE does not appear in any source"; PI inferred from authorship |
| Part B length | 40 pp (45 lump-sum) | MSCA-PF B1 is materially shorter (~10 pp) with a different section set |
| Budget | Lump-sum planner integration (placeholder response present) | MSCA is **unit-cost** (living/mobility/family + institutional unit costs) — the lump-sum gate does not apply as-is |

Two facts make this more than a content swap:

- **Tier 2A is RIA-only.** `instrument_registry.json` is `{}`; `section_schema_registry.json` and `evaluator_expectation_registry.json` describe RIA/IA. The MSCA form PDFs exist (`application_forms/msca/af_he-msca-pf_en.pdf` and four others) but are **unextracted**. Switching instrument means extracting MSCA Tier 2A schemas.
- **Tier 2B extracts are call-specific to MAESTRO.** `extracted/expected_impacts.json` cites `HORIZON-CL4-2026-05-DIGITAL-EMERGING-02.slice.json`. The MSCA work programme source *is* present (`work_programmes/msca/wp-2-marie-sklodowska-curie-actions_horizon-2026-2027_en.pdf` + `HORIZON-MSCA.json`), so re-extraction is feasible — but the current extracts must be purged and regenerated for the MSCA call.

**Instrument-agnosticism is a constitutional value** (§2: "programme-agnostic and project-agnostic by default"). The demo quietly hard-coded RIA assumptions into extracted registries and the budget gate. Re-instantiation is the moment to make that parameterisation real.

### 1.5 The Obsidian graph today

`MSCA/methodology_graph/` is a mature Obsidian vault (Dataview + Smart Connections plugins) of ~90 nodes across numbered folders `00_meta … 10_research_questions`, `90_dashboards`, `99_governance`. It covers **methodology only** — core architecture, state of the art, routes, decision framework, infrastructure, risks/SWOT, partners, terminology, research questions. Governance is explicit:

- **`Methodology Graph Schema`** fixes a YAML front-matter contract for every node: `id` (`METH-<CAT>-<NNN>`), `node_type` (controlled vocab), `evidence_strength` ∈ {`source_grounded`, `synthesis`, `inference`, `unconfirmed`}, `confidence`, `maturity`, `source_refs`, `evidence_basis`, `upstream_nodes`/`downstream_nodes`/`related_nodes`, `open_questions`, `validation_needs`, etc.
- **Wikilinks resolve by basename**; every node links up to a hub and cites ≥1 source.
- **Dashboards** are Dataview queries over `#methodology-graph`.

**The load-bearing alignment:** the graph's `evidence_strength` taxonomy is essentially the constitution's validation taxonomy (§12.2):

| Graph `evidence_strength` | Constitution `validation_status` |
|---|---|
| `source_grounded` | **Confirmed** |
| `synthesis` | Inferred (framing) |
| `inference` | **Inferred** |
| `unconfirmed` | **Assumed / Unresolved** |

This is why the graph is the right authoring surface: it already speaks the orchestrator's provenance language. What it lacks is **coverage of the other phases** (objectives, WPs, timeline, impact pathways, implementation/governance, budget, and the phase/gate state itself) and **the front-matter fields that bind a node to a tier, a phase, and a canonical artifact path** so the compiler and the runner can find it.

---

## 2. Proposed solution architecture

Five moving parts. Each maps to decisions in Section 3.

### 2.1 Instrument-parameterised Phase 8 (serves RIA *and* MSCA)

Introduce an **instrument profile** resolved from `selected_call.json → instrument_type` that supplies, per instrument: the mandatory section/sub-section set, the hard page limit, the budget regime, and which upstream phases are in scope. Phase 8 reads target length and section structure from the profile instead of assuming RIA. This satisfies §2 agnosticism and means the full-length capability we build for MSCA also serves a future RIA at 40–45 pp.

- RIA/IA → Excellence / Impact / Implementation, 40 pp (45 lump-sum), lump-sum budget gate.
- MSCA-PF → B1 Excellence / Impact / Implementation (≈10 pp) + B2 (CV, capacities, ethics), unit-cost budget (lump-sum gate N/A → **[AMENDMENT]** to §8, see D12).

The criterion-aligned n08a/n08b/n08c DAG maps cleanly to *both* (MSCA-PF B1 is literally an Excellence/Impact/Implementation triptych), so the DAG topology does not change — only the profile behind it.

### 2.2 Author full prose in the graph; **extract** the JSON (the operator's instinct, made precise)

Retain the Tier 5 section schemas as the validator contract. Move authoring of the evaluator-facing narrative into the graph as new `proposal_section` nodes (one per sub-section). A **deterministic compiler** (Section 2.4) then produces `excellence_section.json` etc. by extraction, not generation:

| Tier 5 JSON field (unchanged) | Extracted from graph |
|---|---|
| `sub_sections[].sub_section_id`, `title` | node front-matter (`sub_section_id`, `title`) keyed to the instrument profile |
| `sub_sections[].content` | node body prose (the full-length text — no 2.5 KB ceiling) |
| `sub_sections[].word_count` | computed by the compiler |
| `validation_status.claim_statuses[]` | node `claims[]` / inline claim tags → `status` from `evidence_strength`, `source_ref` from `source_refs`/`evidence_basis` |
| `traceability_footer.primary_sources[]` | union of node `source_refs` resolved to tier + canonical path |

Because the compiler carries `evidence_strength` into `claim_statuses[].status`, an `unconfirmed` graph node produces an **`unresolved`/`assumed`** claim — which the gate `no_unresolved_material_claims` will (correctly) catch. Honesty is enforced end-to-end.

### 2.3 What `content` holds, and schema evolution (backward-compatible only)

Recommended: `sub_sections[].content` holds the **full prose** so the gates validate the real text; add **optional, additive** fields so nothing existing breaks:

```jsonc
// excellence_section.json (additions only; all optional ⇒ backward compatible)
"sub_sections": [{
  "sub_section_id": "B.1.1",
  "title": "Objectives and ambition",
  "content": "<full-length prose…>",   // no ceiling; validators read this
  "word_count": 1840,
  "source_nodes": [                      // NEW (optional): graph provenance
    "17_excellence/Objectives and Ambition"
  ],
  "page_estimate": 2.1                    // NEW (optional): profile-relative
}]
```

Schemas stay at `…v1` if additions are optional; if we prefer strictness, bump to `…v2` and update `schema_id_matches` expectations (D4). The transport ceiling is removed for the *extraction* skill because it no longer generates prose — it emits structured metadata plus already-authored text read from disk (TAPM `Read`), and the runtime writes it (chunked write if needed, D3).

### 2.4 The graph→JSON compiler (Step 0-style, deterministic, runner unchanged)

A pure-Python compiler modelled on the existing `runner/call_slicer.py` (deterministic pre-pass, no Claude):

- **Reads** the graph vault (front-matter + body) for nodes tagged with a `tier`/`phase`/`artifact_path`.
- **Emits** the canonical Tier 3 JSON (objectives, WPs, partners, …) and the Part B section metadata into the exact `docs/**` paths the runner and gates already consume.
- **Runs before node dispatch** (like Step 0), so `run_agent()`/`run_skill()`/gates see ordinary canonical JSON. **No change to Section 17 contracts, the DAG scheduler, or gate evaluation.**
- Is **idempotent and auditable**: same graph ⇒ same JSON; a compile report lists every node→artifact mapping and any unresolved links.

This is the concrete meaning of "map all previous phases to the graph for DAG-runner retrieval": the graph is the human-facing source, the compiler is the retrieval bridge, and the runner keeps reading JSON.

### 2.5 Full-proposal graph expansion (methodology → whole proposal)

The full-proposal graph is defined once, **generically**, as a template taxonomy that any project vault instantiates (§2.7); `MSCA/methodology_graph/` is reference instance #1. The generic template adds phase/tier-aligned categories and node types on top of the existing methodology schema, reusing its dashboards:

| New folder | Node types | Binds to (tier/phase → artifact) |
|---|---|---|
| `11_objectives` | `objective`, `outcome` | T3 `architecture_inputs/objectives.json`, `outcomes.json` (Phase 2) |
| `12_work_packages` | `work_package`, `task`, `deliverable` | T4 `phase3_wp_design/wp_structure.json` |
| `13_timeline` | `milestone`, `schedule` | T4 `phase4_gantt_milestones/gantt.json` |
| `14_impact` | `impact_pathway`, `kpi` | T4 `phase5_impact_architecture/impact_architecture.json` |
| `15_implementation` | `governance_role`, `risk` (link to 07) | T4 `phase6_implementation_architecture/…json` |
| `16_budget` | `budget_item` | `integrations/lump_sum_budget_planner/received/…` (or unit-cost profile) |
| `17_proposal_sections` | `proposal_section` | T5 `proposal_sections/*.json` (authoring surface for §2.2) |
| `18_phases_gates` | `phase`, `gate` | T4 phase outputs + `gate_*_result.json` (state mirror) |

Front-matter additions (superset of the existing schema, additive):

```yaml
tier: 3                 # 1..5 (or 2a/2b)
phase: 3                # 1..8 (nullable for tier-1/2 nodes)
artifact_path: "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/wp_structure.json"
artifact_key: "WP2"     # entity id within the artifact
schema_id: "orch.tier4.wp_structure.v1"
provenance_class: run_produced | user_authored | source_extracted
gate_refs: ["phase_03_gate"]
sync_direction: graph_to_docs | docs_to_graph   # per §2.6
```

`evidence_strength`/`confidence` are retained and reused as the Confirmed/Inferred/Assumed/Unresolved signal. New dashboards (Dataview): per-phase completeness, gate-status board, and a **traceability register** mapping each section claim → source node → tier artifact.

### 2.6 Sync direction (who owns what)

- **Author in graph → compile to docs (`graph_to_docs`):** Tier 3 project data and the Part B prose (`11`, `12`-seeds, `14`-seeds, `15`-seeds, `16`-seeds, `17`). Humans curate; the compiler emits canonical JSON.
- **Mirror docs → graph (`docs_to_graph`):** Tier 4 run-produced state and gate results (`18`, and the *derived* views of `12`/`13`). The runner produces these; a projector refreshes the graph for navigation. **Never** fed back into the runner (avoids a cycle).

The two directions must never overlap on the same field — that is the single most important invariant to nail during grilling (D6).

### 2.7 Call-agnostic, multi-project design (operator requirement, 2026-07-09)

The graph integration is an **engine capability, not an MSCA artifact**. It is agnostic by default and acquires project-specificity only when a project's vault is populated — exactly mirroring §2 ("programme-agnostic and project-agnostic by default … acquires call-specificity when Tier 2B is populated … project-specificity when Tier 3 is populated"). Split it into two layers:

- **Generic layer (call- and project-agnostic; ships with the engine):** the graph-schema specification (front-matter contract, `node_type` vocabulary, `sync_direction` rules), the folder-taxonomy template (`00…18`, `90`, `99`), the Dataview dashboard *templates* (written over tags/fields, never over project names), and the deterministic `graph_compiler.py` / `graph_projector.py`. Nothing here names a project, a call, or a domain.
- **Instance layer (one per project):** the actual node content. `MSCA/methodology_graph/` becomes **reference instance #1**, retrofitted to the generic schema. MAESTRO, or any future call, is simply another instance created from the same template.

**Configuration is what makes it "configurable across all projects."** A per-project `graph.config.yaml` (analogous to the existing `tier_bindings.yaml`) declares: vault root path, instrument profile, graph-schema version, the `node_type/folder → tier/phase/artifact_path` binding, and sync-direction ownership per folder. The compiler reads this config and hard-codes nothing project-specific. A new project = drop a vault that conforms to the schema plus a config, and the same compiler, projector, and gates work unchanged.

**Neutral naming.** `methodology_graph` and `#methodology-graph` are MSCA-legacy names; the generic concept is a **proposal graph**. The template and tags use neutral terms (introduce `#proposal-graph`, keep `#methodology-graph` as an alias during migration); per-project vault folder names are free but must carry the schema tags and ID scheme.

**Test of done for agnosticism:** the generic layer passes a "no project nouns" lint, and a throwaway second instance (e.g. a stub MAESTRO vault) compiles through the same pipeline with only its `graph.config.yaml` changed. See D15 (config mechanism) and D16 (template home + scaffolding).

---

## 3. Decision tree (the grilling spine)

Walk top-to-bottom; children assume their parent is resolved. Each node states the question, why it matters, dependencies, options, and a **Recommended** answer to react to.

### D1 — Target instrument for the live MSCA run *(root; unlocks D2, D5, D11, D12, D14)*

Why it matters: sets page target, section set, budget regime, and whether the WP/governance phases apply.

- **(a)** MSCA Postdoctoral Fellowship — matches the project shape; ~10 pp B1; needs MSCA Tier 2A extraction; unit-cost budget (lump-sum gate N/A).
- **(b)** Keep RIA/IA — reuse existing Tier 2A; 40–45 pp; but forces a single-fellow project into a multi-partner consortium schema (fabrication pressure).
- **(c)** Another MSCA action (DN/SE/COFUND) — different again; not supported by the vault's single-PI framing.

**Recommended: (a) MSCA-PF**, *and* build Phase 8 instrument-parameterised (§2.1) so the same machinery still demonstrates a 40–45 pp RIA later. Rationale: the vault is unambiguously a single-researcher fellowship; (b) would require inventing consortium facts, which §13.3 forbids. If the *demo goal* is specifically "show 40–50 pp," raise that now — it changes the recommendation toward keeping RIA with a *different, consortium-grade* project rather than the MSCA one.

### D2 — Phase 8 content-production model *(depends on D1)*

- **(a)** Author-in-graph + deterministic extraction (§2.2).
- **(b)** Decomposed multi-invocation drafting (one skill call per sub-section/WP, then merge — mirrors the existing Phase 5/6 `enrich_artifact` pattern).
- **(c)** Hybrid: graph is the source of truth; where a sub-section is not yet authored, a decomposed drafting skill proposes a draft *into the graph* for human curation.

**Recommended: (c) Hybrid**, with (a) as the steady state. The graph holds the authoritative prose; decomposed drafting is the "cold-start" helper that never writes Tier 5 directly — it writes graph nodes a human then blesses. Keeps humans in the evaluator-quality loop and keeps every transport call bounded.

### D3 — What `sub_sections[].content` holds, and how it is written *(depends on D2)*

- **(a)** Full prose in `content`; runtime does a chunked/streamed atomic write to escape the 20 KB response ceiling.
- **(b)** `content` holds a faithful extract/summary; full prose lives only in the graph and the exported Part B document; add `content_ref`.

**Recommended: (a)** — validators must see the real text (esp. `measurable_targets_preserved`, `canonical_terms_preserved`). Add optional `source_nodes` for provenance. Implement a chunked writer in `skill_runtime.py` for extraction outputs only.

### D4 — Schema versioning *(depends on D3)*

- **(a)** Keep `…v1`, additions optional (fully backward compatible; existing runs still validate).
- **(b)** Bump to `…v2`, make `source_nodes` required, update `schema_id_matches` + `artifact_schema_specification.yaml`.

**Recommended: (a)** for the first working end-to-end run; revisit (b) once the graph is the sole author. Lower blast radius.

### D5 — Drafting/extraction granularity *(depends on D1, D2)*

**Recommended:** per **sub-section** for Excellence/Impact; per **work package** for the Implementation work plan; per **impact pathway** for Impact's pathway prose. Each unit is independently under any transport bound and independently traceable.

### D6 — Graph⇄docs sync ownership *(depends on nothing; gates the compiler)*

The invariant: no field is authored in both directions. **Recommended:** `graph_to_docs` owns Tier 3 + Part B prose; `docs_to_graph` owns Tier 4 state + gate results (mirror only). Enforce with a `sync_direction` front-matter field the compiler and projector both honour, and a lint that fails if a node claims both.

### D7 — Graph schema extension *(depends on D6)*

**Recommended:** additive superset of `Methodology Graph Schema` (§2.5 fields), new `node_type` values (`objective`, `work_package`, `task`, `deliverable`, `milestone`, `impact_pathway`, `kpi`, `governance_role`, `budget_item`, `proposal_section`, `phase`, `gate`), reuse `evidence_strength`/`confidence`. Amend `99_governance/Methodology Graph Schema.md` and `Graph Maintenance Rules.md` accordingly.

### D8 — Graph placement *(depends on D7)*

- **(a)** Extend `MSCA/methodology_graph/` in place (rename conceptually to "proposal graph").
- **(b)** New `MSCA/proposal_graph/` vault cross-linked to the methodology one.

**Recommended: (a) one vault per project** — for the MSCA instance keep a single graph (one dashboard set, one link namespace; add folders `11…18`); the methodology content becomes the Excellence/§B.1.2 evidence base rather than a separate island. Per §2.7 this vault is **reference instance #1 of a call-agnostic template**, not a bespoke structure; where the *generic* template lives is D16.

### D9 — Compiler placement in the run *(depends on D2, D6)*

**Recommended:** a new deterministic pre-pass `runner/graph_compiler.py`, invoked **before** the Call Slicer, gated behind a `--from-graph` flag (opt-in) so existing JSON-first runs are unaffected. Emits a compile report to `docs/tier4_orchestration_state/`. Explicitly **not** a skill (no Claude), so Section 17 is untouched.

### D10 — MAESTRO purge strategy *(depends on nothing; blocks re-instantiation)*

- **(a)** Hard-delete MAESTRO artifacts from Tier 3/4/5 + call-specific extracts.
- **(b)** Snapshot to a git branch/tag first, then reset to empty skeletons.

**Recommended: (b)** — `git switch -c archive/maestro-demo && git commit`, tag it, then reset on `main`. Non-destructive, reproducible, and the demo stays runnable for regression. Detailed manifest in Section 5.

### D11 — Unconfirmed MSCA facts *(depends on D1)*

The vault says partners are unconfirmed (ELTE absent from sources; AgroVIR only "-like"). §13.3 forbids inventing them.

**Recommended:** populate Tier 3 with **only** confirmed facts; represent everything else as explicit placeholders with `evidence_strength: unconfirmed` → compiled to `Assumed`/`Unresolved`. Let the gates block finalization until the operator confirms real identities. Add a "confirmation checklist" dashboard driven by `validation_needs`/`open_questions`. This is the system behaving correctly, and it is the honest state of the project today.

### D12 — MSCA budget regime **[AMENDMENT]** *(depends on D1)*

`CLAUDE.md` §8 hard-codes lump-sum and forbids internal budget computation; §7 Phase 7 is mandatory and lump-sum-shaped. MSCA-PF uses fixed EU unit costs.

- **(a)** Amend §8/§7 to make the budget gate instrument-conditional: lump-sum for RIA; a **unit-cost consistency check** for MSCA (recruited-months × published unit rates), which is arithmetic on official rates, not estimation.
- **(b)** Keep the external-planner contract and feed it MSCA unit costs (awkward; the planner is lump-sum-specific).

**Recommended: (a)**, drafted as a formal §14 amendment record. This is the single biggest constitutional change and must be ratified explicitly before Phase 7 can pass for MSCA.

### D13 — Canonical reference pack for full-length prose *(depends on D2, D3)*

The gate compares prose against `canonical_reference_pack.json`. At 40 pp the pack must be complete.

**Recommended:** generate the pack from the graph's confirmed nodes as part of compilation, so canonical names/targets/deliverables come from the same source as the prose — eliminating drift between what is written and what is checked.

### D14 — Definition of done for "full-scale, end-to-end" *(depends on D1)*

**Recommended:** a single `--from-graph` run for the MSCA-PF call that (i) compiles graph→docs, (ii) passes Phases 1–7 with confirmed-or-flagged Tier 3, (iii) produces B1 sections at the profile's page target with all Phase 8 gates green, (iv) exports a human-readable Part B (`docx`/`pdf`), and (v) leaves every claim traceable to a graph node. Anything still `unconfirmed` is surfaced, not hidden.

### D15 — Config-driven binding mechanism *(new; depends on D6, D9)*

How does the compiler learn a project's graph→artifact mapping without hard-coding it?

- **(a)** A per-project `graph.config.yaml` (vault path, instrument profile, `node_type/folder → tier/phase/artifact_path` binding, sync-direction ownership), read by the compiler; the engine ships a default template config.
- **(b)** Convention-only — fixed folder names imply fixed bindings; no config file.

**Recommended: (a)** — an explicit config mirrors `tier_bindings.yaml`, absorbs differently-shaped instruments/projects (RIA vs MSCA-PF have different folders in scope), and keeps the compiler project-agnostic. (b) breaks the moment an instrument needs a different taxonomy.

### D16 — Generic template home + scaffolding *(new; depends on D8, D15)*

Where does the reusable template live, and how is a new project's graph created?

- **(a)** Generic schema + taxonomy + dashboard templates + config template under the engine (e.g. `.claude/workflows/system_orchestration/graph_schema_specification.yaml` + a `graph_template/` skeleton), plus an `obsidian-graph` **scaffolding skill** that stamps a new project vault and `graph.config.yaml`.
- **(b)** Document the schema only; authors hand-copy the MSCA vault per new project.

**Recommended: (a)** — a scaffolding skill is what makes "configurable across all projects" real, and keeps every instance schema-conformant from birth. The MSCA vault's `Methodology Graph Schema` node is already ~90% generic; generalize it *into* the template, then re-stamp MSCA as instance #1.

---

## 4. Sequenced implementation plan

Ordered so each stage is independently verifiable and nothing is executed before its decisions are ratified. Stages 0–2 are prerequisites; 3–6 are the build; 7 is validation.

**Stage 0 — Ratify constitutional changes (blocks everything instrument-related).** Draft §14 amendment records for D12 (budget regime) and any phase/gate scope change from D1. Human sign-off. *Verify:* amendment records exist in `CLAUDE.md`; affected workflows reviewed (§14.3).

**Stage 1 — Snapshot & purge (D10).** Branch `archive/maestro-demo`, tag, then reset the MAESTRO instantiation per the Section 5 manifest. *Verify:* `git status` clean on `main`; purged paths are empty skeletons; archive branch runs the old demo.

**Stage 2 — Instrument profile + MSCA Tier 2A/2B extraction (D1).** Add an `instrument_profile` resolver keyed on `selected_call.json`. Extract MSCA-PF Tier 2A (`section_schema_registry`, `evaluator_expectation_registry`, `instrument_registry`, page limit) from `af_he-msca-pf_en.pdf`; re-derive Tier 2B extracts from the MSCA work programme for the chosen call. *Verify:* Phase 1 gate passes for the MSCA call; `instrument_registry.json` non-empty; page limit reflects MSCA-PF.

**Stage 3 — Generic graph template + config (D7, D8, D15, D16).** Generalize the methodology schema into a call-agnostic template: schema spec + folder taxonomy `11…18` + dashboard *templates* + `graph.config.yaml` template + optional `obsidian-graph` scaffolding skill. Re-stamp `MSCA/methodology_graph/` as instance #1 conforming to it. *Verify:* Dataview dashboards render; schema-lint passes; the **"no project nouns" lint passes on the generic layer**; a throwaway second instance scaffolds and compiles cleanly with only its config changed.

**Stage 4 — Compiler + projector (D6, D9).** Build `runner/graph_compiler.py` (graph→docs, deterministic, pre-Call-Slicer, `--from-graph`) and the `docs_to_graph` projector for Tier 4/gate mirror nodes. *Verify:* compile is idempotent (byte-stable re-emit); compile report maps every node→artifact; `sync_direction` lint passes; **no Section 17 module touched**.

**Stage 5 — Author MSCA proposal graph (D11).** Populate `11…17` from the methodology graph + confirmed facts only; unconfirmed → flagged placeholders. Author Part B prose nodes in `17` to the profile's page target. *Verify:* traceability dashboard shows every intended claim linked to a source; confirmation checklist lists exactly the known gaps.

**Stage 6 — Phase 8 extraction path (D2, D3, D4, D5, D13).** Add the extraction skill(s) that read `17` nodes and emit section JSON; add the chunked writer; generate `canonical_reference_pack.json` from the graph. Keep decomposed drafting as the cold-start helper writing *into the graph*. *Verify:* section JSONs validate against schema; all `gate_10a/b/c` predicates green on full-length content; `canonical_*_preserved` pass.

**Stage 7 — End-to-end MSCA run + export (D14).** `--from-graph` run for the MSCA-PF call through Phases 1–8; export Part B to `docx`/`pdf`. *Verify:* all gates green or honestly blocked on named unconfirmed facts; exported page count within the profile limit; spot-check 10 claims trace to graph nodes. **Use a subagent to re-verify traceability independently.**

---

## 5. Purge / retain manifest (proposal — not executed)

Executed only after D10 is ratified and the archive branch exists. "Reset" = delete contents, keep directory + a `.gitkeep`/skeleton.

### 5.1 Purge (MAESTRO-specific, run-produced, or call-specific)

| Path | Action | Why |
|---|---|---|
| `docs/tier3_project_instantiation/project_brief/*` | Reset | MAESTRO concept/summary/positioning |
| `docs/tier3_project_instantiation/consortium/*` | Reset | MAESTRO partners/roles/capabilities |
| `docs/tier3_project_instantiation/call_binding/{selected_call,topic_mapping,compliance_profile}.json` | Reset | CL4 AI-agents call binding |
| `docs/tier3_project_instantiation/architecture_inputs/*` | Reset | MAESTRO objectives/outcomes/impacts/WP/risks/milestones |
| `docs/tier3_project_instantiation/integration/*` | Reset | MAESTRO budget request/response/refs |
| `docs/tier4_orchestration_state/phase_outputs/phase{1..8}_*/**` | Reset | All MAESTRO run state incl. gate results, `canonical_reference_pack.json` |
| `docs/tier4_orchestration_state/{decision_log,validation_reports,checkpoints,reuse}/*` | Reset | MAESTRO run history (dozens of entries) |
| `docs/tier5_deliverables/{proposal_sections,assembled_drafts,review_packets,final_exports}/*` | Reset | MAESTRO Part B |
| `docs/tier2b_topic_and_call_sources/extracted/*` | Reset & regenerate | CL4-specific slices |
| `docs/tier2a_instrument_schemas/extracted/*` | Regenerate for MSCA (if D1≠RIA) | Currently RIA-only |
| `docs/integrations/lump_sum_budget_planner/{received,validation}/*` | Reset | MAESTRO placeholder budget |
| `.claude/runs/*` | Reset | MAESTRO run contexts |

### 5.2 Retain (infrastructure, sources, programme-agnostic truth)

| Path | Why |
|---|---|
| `docs/tier1_normative_framework/**` (incl. `extracted/`) | Programme-agnostic legal/regulatory truth |
| `docs/tier2a_instrument_schemas/application_forms/**`, `evaluation_forms/**` | Source form PDFs (incl. all MSCA forms) |
| `docs/tier2b_topic_and_call_sources/work_programmes/**`, `call_extracts/**` | Source work-programme PDFs/JSON (incl. MSCA) |
| `docs/integrations/lump_sum_budget_planner/{interface_contract.json,request_templates/}` | Contract (still valid for RIA profile) |
| `runner/**`, `.claude/workflows/**`, `.claude/skills/**`, `.claude/agents/**`, `tests/**` | Engine, workflow, skills, agents, tests |
| `docs/index/*` | Registries — **update**, don't delete, to reflect new state (§9.6) |
| `CLAUDE.md`, `README.md`, `MSCA/**` | Constitution, docs, the source vault |

### 5.3 Post-purge integrity

After reset, run `python -m runner --run-id <uuid> --phase 1 --dry-run` and confirm a clean gate-failure that names the missing Tier 3 inputs (a correct fail-closed state, per §12.4), not a crash.

---

## 6. Risks, tensions, and things most likely to be wrong

- **Full length × no-fabrication (the central tension).** 40 pp of RIA prose needs enough Tier 3 substance to ground every sentence; the MSCA vault is thin and partly unconfirmed. Mitigation: MSCA-PF's ~10 pp target is a far better fit; the confirmation checklist makes gaps explicit. If we insist on 40–50 pp from the MSCA project, we will hit the fabrication wall — that is a reason to reconsider D1, not to weaken §13.3.
- **Constitutional surface area.** D12 (budget) and any D1 phase-scope change are real amendments (§14). If we under-scope Stage 0, later stages will be blocked by the very gates we are trying to pass.
- **Compiler as a shadow authority.** If the compiler starts *inferring* rather than *extracting*, it becomes an unlogged decision-maker (violates §9.4/§16). Keep it strictly deterministic; every inference belongs in a graph node with an `evidence_strength`, not in Python.
- **Sync cycles.** If any field is both `graph_to_docs` and `docs_to_graph`, the graph and docs can silently diverge. The `sync_direction` lint (D6) is load-bearing.
- **Gate freshness.** Introducing the compiler adds inputs; per README "Upstream Gate Freshness", generated helper artifacts must be excluded from freshness tracking or they will false-invalidate gates. The compile report and compiled JSON need the same treatment as the call slice.
- **MSCA instrument specifics** *(Inferred, confidence: medium — confirm against `af_he-msca-pf_en.pdf`).* PF B1 page limit and exact sub-section headings are stated from general Horizon knowledge, not yet read from the form. Stage 2 must extract them from the PDF before they are trusted (§10.6: source docs govern over prior knowledge).
- **Instance leakage into the generic layer.** The core agnosticism risk: a dashboard query, binding, or compiler branch that references MSCA specifics (crop terms, the `methodology_graph` path). Mitigation — the generic layer must pass a "no project nouns" lint; every project specific lives in the instance vault + `graph.config.yaml`, never in engine code or template queries. This is the graph-layer analogue of §13.2/§13.3 (no invented call/project facts baked into the engine).

---

## 7. Open questions to resolve during grilling

1. Is the live goal genuinely MSCA-PF, or is "40–50 pp" a hard requirement that points back at RIA with a different project? (D1, D14)
2. Who confirms the real consortium (PI name, ELTE role, AgroVIR commitment)? Until then, how much may a run legitimately produce? (D11)
3. Are we willing to make the §8 budget amendment now, or defer MSCA Phase 7 behind a documented block? (D12)
4. Does the graph become *the* project source of truth (Tier 3 authored only in Obsidian), or a parallel surface we reconcile? (D6)
5. `v1`-additive vs `v2`-strict for the section schema on the first end-to-end run? (D4)
6. Export target for the human-readable Part B — `docx`, `pdf`, or both? (D14)
7. Where should the generic graph template live (`.claude/` vs a top-level `graph_template/`), and is an `obsidian-graph` scaffolding skill in scope this iteration? (D15, D16)

---

## Appendix A — Verified fact base (read 2026-07-09)

- Drafting ceilings: excellence/implementation < 20,000 chars, impact < 18,000; per-sub-section 2,000–2,500 chars, "3–5 sentences". Source: the four `*-section-drafting.md` skills.
- No length predicate in `gate_rules_library.yaml` for `gate_10a/b/c/d`, `gate_11`, `gate_12`; canonical-preservation predicates compare against `phase8_drafting_review/canonical_reference_pack.json`.
- RIA Part B hard limit 40 pp (45 lump-sum): `tier2a…/extracted/section_schema_registry.json`.
- `instrument_registry.json` (Tier 2A extracted) = `{}`; section/evaluator registries are RIA-only. MSCA form PDFs present but unextracted.
- Tier 2B extracts reference `HORIZON-CL4-2026-05-DIGITAL-EMERGING-02`; MSCA work programme PDF + `HORIZON-MSCA.json` present.
- `selected_call.json` = RIA, CL4, 48 months, €19M.
- Budget integration is lump-sum-specific (`how-to-manage-your-lump-sum-grants_en.pdf`, placeholder response present).
- MSCA vault: ~90 methodology nodes, strict YAML schema, `evidence_strength` taxonomy, Dataview + Smart Connections, partners largely `unconfirmed`.

## Appendix B — Graph `evidence_strength` ⇄ constitution mapping

`source_grounded → Confirmed`; `synthesis → Inferred (framing)`; `inference → Inferred`; `unconfirmed → Assumed/Unresolved`. Used by the compiler to populate `validation_status.claim_statuses[].status` and to decide whether `no_unresolved_material_claims` can pass.

---

*Seed for `/grilling`. Do not enact until we reach shared understanding and you confirm. Constitutional amendments (D12, D1 scope) require explicit human ratification per `CLAUDE.md` §14.*
