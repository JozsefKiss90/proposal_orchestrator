# Milestone 1 — Decision Record (MSCA-PF Honest Run)

> **Status:** Locked. **Stage 0 (constitutional ratification) complete and applied.** Build not yet started.
> **Date:** 2026-07-10.
> **Provenance:** Output of the milestone-1 `/grilling` session (`grill-me` → `grilling`) over `PHASE8_FULLSCALE_AND_OBSIDIAN_GRILL_BRIEF.md`, reconciled with the shared-understanding ledger. Constitutional items ratified per §14.5 and applied to `CLAUDE.md`. Amendment detail is **not restated here** — see `PROPOSED_CONSTITUTIONAL_AMENDMENTS_milestone1.md`, `RATIFICATION_CLAUDE_md_amendment_records.md`, and the §8 / §16 / §17 amendment records in `CLAUDE.md`.

## Scope

Milestone 1 delivers an **honest MSCA-PF end-to-end run** produced by **decomposed drafting** — bounded per-sub-section Claude calls composed by a deterministic assembler. The length shortfall was diagnosed as a *decomposition* problem, not a transport-ceiling or graph problem, so the **entire Obsidian graph subsystem is deferred to milestone 2** — where deferring it is itself the proof it is the call-agnostic add-on §2.7 claims. "Done" is a proposal that is either **all-green** (every claim confirmed or operator-declared) or **honestly blocked** on named unconfirmed facts — both correct terminal states (§12.4, §15).

## Locked decisions

| # | Decision | Resolution |
|---|---|---|
| **D1** | Live goal / instrument | **G3** — MSCA-PF now, built **instrument-parameterised**; "full-scale" ≡ up to the instrument's page limit, not 40 pp by default. PF is the *inferred* action — confirm against the form in Stage 2. RIA-40 pp (G2) stays reachable later with its own real project. |
| **D2** | Content-production model | **Decomposed drafting now**; Obsidian graph **entirely deferred to milestone 2**. The graph is *not* the length fix; decomposed `enrich_artifact`-style drafting already ships. |
| **D3** | `content` + write path | **Full prose** in `sub_sections[].content`; a **deterministic array-append assembler** (§17.5.3-class) composes per-sub-section drafts into the section JSON; `enrich_artifact` field-merge reserved for genuine enrichment (DEC, risk register). **Chunked writer struck** — not deferred. *Build check:* confirm the shipped merge is field-only → the assembler is primary. |
| **D4** | Schema versioning | **v1, additive-optional, zero required additions**; `page_estimate` optional. Verified instrument-generic (free-string `sub_section_id`, no RIA enum in schema or gates; sub-section enumeration lives in Tier 2A). |
| **D5** | Granularity + coherence | Granularity = **profile sub-section set** (Stage 2, from the PF form); guiding principle = **coarsest ceiling-safe unit** (each split adds coherence tax). "Per WP / per pathway" **struck as RIA-isms**. Coherence = **sequential context-passing** now; escalation trigger = **front-of-section drift**; ordered draft-layer / byte-equal-safe deepenings: deterministic coherence lint → Claude coherence-revision pass. Outline pre-pass available as an optional *prevention* rung. |
| **D10** | MAESTRO purge / git | Create `archive/maestro-demo` from the **current pre-purge commit** (keeps the demo runnable for regression); re-instantiation work **branches off `backend_migration`**; the embedded `MSCA/` repo is **pin-and-record** (commit to a clean SHA, record it as re-instantiation provenance, §9.5) — submodule-vs-absorb topology deferred to **D8**. Skeleton-reset per the §5 manifest; §5.3 fail-closed dry-run. |
| **D11** | Unconfirmed facts | **β — block-default + operator-declared-assumption override.** Engine default = honest block (identity claims → `Unresolved`, enumerated + confirmation checklist). The operator may author `working_assumptions.json` to declare working assumptions → flagged `Assumed` → conscious green. **The engine never invents**; enforced mechanically by **W1**. |
| **D12** | Budget regime | **Option 1 — strict + internal.** Unit-cost budget derived **internally, deterministically** (`months × rates × host_coeff`, byte-equal CI); `gate_09` instrument-conditional on **source only**, with the **categorical block preserved verbatim**. An **informative blocked assessment** (host-independent lines computed) rides free under a block, with no amendment. Ratified as **C1**. |
| **D13-r** | Canonical pack (milestone 1) | Generated **deterministically from the same source as the prose** — Tier 3 confirmed facts **+** `working_assumptions.json` declared values — with **per-entry provenance** so an assumed value never enters the pack as a confirmed canonical fact. (Pack-from-graph = **D13-graph**, milestone 2.) Load-bearing because the canonical-preservation gates are contradiction detectors. |
| **D14** | Definition of done | **B1-only**; **`.docx` primary**; **B2 deferred-by-scope**. Done = every Phase-8 gate **green** (every `Assumed` operator-declared, W1 satisfied) **OR an honest block** naming the unconfirmed claims; every material claim traceable to Tier 3 / a declared assumption; both CI checks pass; an **independent subagent re-verifies** traceability. |
| **D17** | Depth of the honest block | **Folds into β (D11).** The run exercises the `source_grounded` methodology through Phases 1–7 and blocks-or-greens on the spine (researcher / host / call), which the operator supplies as confirmed facts or β-declared assumptions — so the block lands *informatively*, not at the door. |

## Deferred to milestone 2 (the graph track)

| # | Deferred item |
|---|---|
| **D6** | Graph⇄docs sync ownership (the `sync_direction` no-overlap invariant) |
| **D7** | Graph schema extension (new `node_type`s, front-matter superset) |
| **D8** | Graph placement **+ embedded-`MSCA/`-repo topology** (submodule-vs-absorb) |
| **D9** | Compiler placement (`runner/graph_compiler.py`, deterministic, `--from-graph`) |
| **D13-graph** | Canonical pack generated from graph nodes |
| **D15** | Config-driven binding (`graph.config.yaml`) |
| **D16** | Generic template home + `obsidian-graph` scaffolding skill |
| **B2** | CV / participating-org capacities / ethics (identity-saturated; wants real confirmed facts) |
| **G2 / RIA-40pp** | Full 40–50 pp RIA demo — needs its own real consortium-grade project |

## Stage-0 constitutional ledger — COMPLETE (ratified & applied 2026-07-10)

Per §14.5. Records are written into `CLAUDE.md`; drafts in `PROPOSED_CONSTITUTIONAL_AMENDMENTS_milestone1.md`; insert-ready records in `RATIFICATION_CLAUDE_md_amendment_records.md`. **Not restated here.**

| ID | Sections | Substance | Kind | Status |
|---|---|---|---|---|
| **C1** | §8.1; §8.4/§7 (+§13.4 xref) | Budget gate instrument-conditional on **source** (lump-sum external / unit-cost internal deterministic derivation, byte-equal replay); categorical block preserved verbatim | Substantive | **Ratified & applied** |
| **C2** | §17.5.3 (+§17.4.2) | Agent runtime may invoke deterministic, Claude-free node-body components; `AgentResult.invoked_components` added | Clarification | **Ratified & applied** |
| **C3** | §16.5 | Bindable vocabulary widened to include deterministic components | Clarification | **Ratified & applied** |

## Workflow-level build artifacts (no CLAUDE.md amendment — to build & register)

**W1 — anti-bypass predicate `assumed_claims_are_operator_declared`** (folded into the Phase-8 drafting gates `gate_10a/b/c`, not a new gate node). Every `status: assumed` claim maps by `claim_id` to a `manually_placed` `working_assumptions.json` entry **and** `claim_summary == declared value`; a `run_produced` artifact can never back an `Assumed`; any `Assumed` without a backing declaration fails the gate. Strengthens gates (§13.7-clean — adding, not weakening). **Boundary:** closes marked-`Assumed` laundering; prose that fabricates *without emitting a claim* remains the semantic gates' job (`no_unsupported_tier5_claims`, `no_gap_masked_as_confirmed`).

**W2 — supporting artifacts:**
- `working_assumptions.json` — Tier 3, `provenance_class: manually_placed`, user-authored; the engine reads it, never writes it.
- `phase8_drafting_review/section_drafts/` — Tier 4 per-sub-section drafts, **retained** (§9.5 audit of a non-deterministic step), **freshness-excluded**; the section JSON is the sole gate/freshness artifact.
- `AgentResult.invoked_components` — additive field (delivered under C2).
- Instrument-profile resolver + MSCA Tier 2A/2B extraction (Stage 2).
- **CI checks:** `assembler(drafts) == section_json` (byte-equal — enforces no-synthesis); `unit_cost_budget(months, rates, host_coeff) == figure` (byte-equal — enforces deterministic budget).

**Deterministic-component roster (C2 / §16.5-bound):**

| Component | Role | Determinism guarantee |
|---|---|---|
| Section assembler | Per-sub-section drafts → section JSON (array-append; carries `claim_statuses`/`validation_status` up verbatim; never synthesises) | `assembler(drafts) == section_json` |
| Assumption-applier | Flips enumerated `Unresolved → Assumed` from `working_assumptions.json`, **pre-assembly** (preserves byte-equal) | lookup only; self-declares nothing |
| Canonical-pack deriver | `canonical_reference_pack.json` from Tier 3 confirmed + declared values | same-source ⇒ no drift; per-entry provenance |
| Unit-cost budget deriver | `months × rates × host_coeff` (unit-cost instruments) | `unit_cost_budget(…) == figure` |

All four: agent-runtime-invoked (C2), manifest-bound (C3), logged in `AgentResult.invoked_components`; on fault → `failure_origin="agent_body"`, `failure_category="AGENT_EXECUTION_ERROR"`, `can_evaluate_exit_gate=False`.

## Corrected staging

| Stage | Work | Status |
|---|---|---|
| **0** | Ratify C1/C2/C3 (§14.5), apply to `CLAUDE.md`, run §14.3 review + §14.4 consistency check | **DONE (2026-07-10)** |
| **1** | Purge: `archive/maestro-demo` from current pre-purge commit; work branch off `backend_migration`; pin + record `MSCA/` subrepo SHA; skeleton-reset per §5; §5.3 fail-closed dry-run | Pending |
| **2** | Confirm the MSCA action + call; add the `instrument_profile` resolver; extract MSCA-PF Tier 2A from the form (**page limit read, not assumed**, §10.6); re-derive Tier 2B for the call; Phase 1 gate green | Pending |
| **3–6** | Build the decomposed-drafting path — **Excellence-only vertical slice first** (operator steer): drafting skills (profile granularity, soft caps lifted, sequential context-passing) → `section_drafts/` → assembler → assumption-applier → canonical-pack deriver → **W1** predicate on `gate_10a/b/c` → instrument-conditional `gate_09` + informative blocked assessment → CI checks. Then extend to Impact + Implementation. | Pending |
| **7** | End-to-end MSCA-PF run — two modes: **α** (no declarations → fail-closed block) / **β** (host+ declared → full B1); `.docx` export; **independent subagent** traceability re-verify | Pending |

*Milestone 2 (graph track): generic template + config (D7/D15/D16), compiler + projector (D6/D9), graph authoring + pack-from-graph (D13-graph); plus B2 and G2/RIA-40 pp.*

---
*Canonical ledger for milestone 1. Narrative & analysis: `PHASE8_FULLSCALE_AND_OBSIDIAN_GRILL_BRIEF.md` (v3). Constitutional detail: `CLAUDE.md` §8/§16/§17 amendment records + `PROPOSED_CONSTITUTIONAL_AMENDMENTS_milestone1.md` + `RATIFICATION_CLAUDE_md_amendment_records.md`. Stage 0 applied; **Stage 1 (purge) is the next action.***
