# Tickets: Milestone 1 — MSCA-PF Honest Run

Build tickets for an honest MSCA-PF end-to-end run via **decomposed drafting** (bounded per-sub-section Claude calls composed by deterministic assembly). Source spec: `MILESTONE1_DECISION_RECORD.md` (Stage 0 constitutional ratification — C1/C2/C3 — is already applied to `CLAUDE.md`; these tickets are the pending build, Stages 1–7). Narrative: `PHASE8_FULLSCALE_AND_OBSIDIAN_GRILL_BRIEF.md`.

"Done" for the milestone = a proposal that is either **all-green** (every claim confirmed or operator-declared) or **honestly blocked** on named unconfirmed facts — both correct terminal states (§12.4, §15).

**Work the frontier:** pick any ticket whose blockers are all done.

- **Wave 0 (start now, parallel):** 1, 2, 3
- **Wave 1:** 4, 5, 6
- **Wave 2:** 7, 8, 12
- **Wave 3:** 9
- **Wave 4:** 10
- **Wave 5:** 11 #done
- **Wave 6:** 13

Two orienting facts. **Ticket 1 is a prefactor** — it generalizes the one existing hardcoded deterministic pass (the n04 dependency-normalizer) into a manifest-bound mechanism, making the other four components mechanical to add. And the three drafting gates (`gate_10a/b/c`) each **re-assert the budget gate** (§8.4), so no section reaches gate-*green* until unit-cost `gate_09` (ticket 8) passes — by decision, per-section tickets deliver a verified section artifact and the whole DAG goes green at E2E (ticket 13).

*Out of scope (milestone 2): the Obsidian graph track (D6–D9, D13-graph, D15, D16), B2 (CV / participating-org capacities / ethics), and G2 / RIA-40pp.*

---

## 1. Deterministic-component binding substrate (C2/C3)

**What to build:** The agent runtime can invoke deterministic, Claude-free composition components declared in the manifest, and records each invocation for audit — so the four milestone-1 components (assembler, assumption-applier, canonical-pack deriver, budget deriver) bind and log uniformly instead of being hardcoded. The one existing hardcoded component runs through this same generic path unchanged.

**Blocked by:** None — can start immediately.

- [ ] A node spec can declare one or more deterministic components via a manifest binding key (§16.5/C3), resolved by the node resolver.
- [ ] The agent runtime invokes bound components within the node body and records each in the new additive `AgentResult.invoked_components` field (C2).
- [ ] A component fault sets `failure_origin="agent_body"`, `failure_category="AGENT_EXECUTION_ERROR"`, and `can_evaluate_exit_gate=False`.
- [ ] The n04 dependency-normalizer is migrated from its hardcoded branch to a manifest-bound component with byte-identical output (regression).
- [ ] The skill contract is unaffected: components cannot evaluate gates, cannot be invoked by skills, and Python still owns all writes (§17.5.3, §17.6).

## 2. Instrument-profile resolver

**What to build:** Phase 8 and its gates read the mandatory section set, hard page limit, budget regime, and in-scope phases from a per-instrument profile keyed on the selected call's `instrument_type` — so the same engine serves MSCA-PF now and RIA later with no RIA assumptions baked into the drafting path.

**Blocked by:** None — can start immediately.

- [ ] An instrument profile resolves from the selected call's `instrument_type` and returns: sub-section set, hard page limit, budget regime (lump-sum | unit-cost), and phases-in-scope.
- [ ] The instrument registry is populated for RIA from the existing extracted schemas; the resolver returns the correct RIA profile.
- [ ] Phase 8 section structure and target length are read from the profile, not assumed — no RIA literal remains on the drafting path.
- [ ] The resolver fails closed (no silent default) when `instrument_type` is absent or unknown.

## 3. Purge to skeleton & re-instantiate on the MSCA work branch (Stage 1)

**What to build:** The repo is reset from the MAESTRO/RIA demo to an MSCA-PF skeleton on a fresh work branch, with the old demo preserved for regression and the embedded MSCA vault pinned as provenance — the framework/engine survive, the project-specific data is blanked.

**Blocked by:** None — can start immediately.

- [ ] `archive/maestro-demo` exists at the current pre-purge commit and still runs the MAESTRO demo end-to-end (regression safety).
- [ ] A new work branch is cut from `backend_migration`.
- [ ] The embedded `MSCA/` repo is committed to a clean SHA and that SHA is recorded as re-instantiation provenance (§9.5); submodule-vs-absorb topology stays deferred (D8).
- [ ] The §5 purge/retain manifest is executed: MAESTRO Tier 3/4/5 and RIA `extracted/` sets are blanked to skeletons; framework, engine, and source documents are retained.
- [ ] The §5.3 fail-closed dry-run passes on the reset skeleton (enumerates ready nodes, evaluates no gates, exits clean).

## 4. Section assembler + `section_drafts/` contract + byte-equal CI

**What to build:** A deterministic assembler composes per-sub-section drafts into a section JSON by array-append — carrying claim and validation status up verbatim — with a byte-equal replay check that makes "no synthesis" true by construction. This is the composition half of the length fix; no chunked writer is needed.

**Blocked by:** 1 (Deterministic-component binding substrate).

- [ ] Per-sub-section drafts placed in `section_drafts/` are composed into the section's `sub_sections[]` by array-append, bound as a deterministic component.
- [ ] `claim_statuses` / `validation_status` are carried up verbatim; only `word_count` and the `source_refs` union are derived; the write is atomic.
- [ ] A byte-equal check `assembler(drafts) == section_json` passes and is wired as a test (establishes the net-new byte-equal CI home).
- [ ] The section schema gains an additive-optional `page_estimate` field — schema stays v1, zero required additions, instrument-generic `sub_section_id` confirmed (D4).
- [ ] The assembler emits no prose and performs no inference (enforced by the byte-equal check on fixture drafts).

## 5. MSCA-PF Tier 2A extraction

**What to build:** The MSCA-PF application form is confirmed as the target action and its structure — sub-section set and hard page limit — is extracted into the registries, so the profile resolver returns a real MSCA-PF profile instead of a RIA-only one.

**Blocked by:** 2 (Instrument-profile resolver), 3 (Purge & re-instantiate).

- [ ] The action is confirmed as PF (vs dn / se / cofund / cofund-ce) against the form, and the confirmation is recorded in the decision log.
- [ ] The MSCA-PF sub-section set and hard page limit are extracted, with the page limit **read from the PF Part B template** and cited to a form page (§10.6) — not assumed.
- [ ] The instrument / section-schema / evaluator registries carry the MSCA-PF entry; the profile resolver returns the MSCA-PF profile.
- [ ] No RIA assumption leaks into the MSCA extraction — every extracted value traces to the form.

## 6. MSCA Tier 2B re-derivation + unit-cost rates + Phase 1 green

**What to build:** The call-specific extracts are regenerated for the MSCA-PF call and the MSCA unit-cost rate table is created, so Phase 1 (call analysis) passes for MSCA-PF and the budget deriver has an authoritative rate source.

**Blocked by:** 3 (Purge & re-instantiate).

- [ ] The six Tier 2B extracted files (call constraints, eligibility, expected outcomes, expected impacts, scope requirements, evaluation priority weights) are regenerated for the MSCA-PF call from the MSCA work programme; a PF call extract exists.
- [ ] A net-new unit-cost rates artifact exists (living / mobility / family allowances, institutional unit costs, host-country coefficient) with per-rate provenance to the work programme / AGA.
- [ ] All six extracts are non-empty and traceable to identified source sections; `selected_call.json` is consistent with them.
- [ ] The Phase 1 call-analysis gate is green for MSCA-PF.

## 7. Excellence decomposed drafting → assembled section (tracer bullet)

**What to build:** The Excellence section is drafted as bounded per-sub-section Claude calls (no longer one monolithic call), written to `section_drafts/`, and composed by the assembler into a full-length, traceable Excellence section — the first end-to-end proof that decomposition fixes the ~10× length shortfall without a chunked writer. (Full `gate_10a`-green is realized at E2E once the budget gate lands in ticket 8.)

**Blocked by:** 4 (Section assembler), 2 (Instrument-profile resolver), 5 (MSCA-PF Tier 2A extraction).

- [ ] Excellence drafting runs as bounded per-sub-section calls at profile granularity, soft caps lifted, with sequential context-passing for coherence; each writes a draft to `section_drafts/`.
- [ ] The assembler composes the drafts into a full-length `excellence_section.json` that materially exceeds the prior monolithic length and carries claim / validation status.
- [ ] Every material claim is traceable to Tier 3 (or flagged); `traceability_footer` and `validation_status` are present.
- [ ] The byte-equal assembler check passes on the real Excellence drafts.
- [ ] (Stretch) An optional coherence rung — deterministic coherence lint and/or a Claude coherence-revision pass — is available when front-of-section drift is detected.
- [ ] `gate_09` is never stubbed, mocked, or bypassed to let drafting run (§8.4 / §13.4 / §13.7).
      Either this ticket is scoped to a test/scratch harness (fixture drafts; no governed Phase-8
      node execution; no artifact written to `docs/tier5_deliverables/`), or ticket 8 is a blocker
      and the section is produced only after `gate_09` passes.

## 8. Unit-cost budget deriver + instrument-conditional `gate_09` (C1 code)

**What to build:** MSCA budgets are derived internally and deterministically from published unit costs, and the budget gate branches on instrument type — unit-cost internal derivation for MSCA, external lump-sum for RIA — while the categorical block on Phase 8 stays intact and instrument-independent. This lands the C1 code that the constitutional text already anticipates.

**Blocked by:** 2 (Instrument-profile resolver), 6 (MSCA Tier 2B rates), 1 (Component-binding substrate).

- [ ] A deterministic deriver computes the unit-cost budget as `months × rates × host_coeff` from confirmed effort and the Tier 2B rates, bound as a component.
- [ ] A byte-equal check `unit_cost_budget(months, rates, host_coeff) == figure` passes and is wired as a test.
- [ ] `gate_09` is instrument-conditional on source (unit-cost internal derivation vs lump-sum external `received/`), with the categorical HARD_BLOCK on Phase 8 preserved verbatim (§8.4 / §13.4).
- [ ] Every budget component — including host-dependent lines — resolves to Confirmed or operator-declared Assumed before the gate passes; an unresolved host coefficient blocks.
- [ ] Under a block, an informative blocked assessment is emitted with host-independent lines computed (no amendment; rides free under the block).

## 9. β honesty layer: `working_assumptions.json` + assumption-applier + W1

**What to build:** The operator can declare working assumptions that turn an honest block into a conscious green, and a hard predicate guarantees the engine never invents — every `Assumed` claim must trace to an operator declaration. Proven on the Excellence section.

**Blocked by:** 4 (Section assembler), 7 (Excellence decomposed drafting).

- [x] A Tier 3 `working_assumptions.json` convention exists (`provenance_class: manually_placed`, user-authored); the engine reads it and never writes it. *(Convention delivered by ticket 15; the applier and W1 read it, never write it.)*
- [x] The assumption-applier flips only enumerated `Unresolved → Assumed` from declared assumptions, pre-assembly, preserving the byte-equal assembler guarantee; bound as a component. *(`runner/assumption_applier.py`; registered as `{excellence,impact,implementation}_assumption_applier`. Node binding on n08a/b/c deferred to ticket 13, per the assembler pattern.)*
- [x] The W1 predicate `assumed_claims_are_operator_declared` is appended to `gate_10a`: every `status: assumed` claim maps by `claim_id` to a `manually_placed` declaration with `claim_summary == declared value`. *(`g09a_p11`; `runner/predicates/criterion_predicates.py`. The manifest `gate_registry` wiring — required for the predicate to actually run under Approach-B resolution — was completed in ticket 11 alongside `gate_10b`/`gate_10c`; the library-only definition here was inert at runtime until then.)*
- [x] A `run_produced` artifact can never back an `Assumed`; any `Assumed` without a backing declaration fails the gate. *(The reader parses only the `manually_placed` file, so no `run_produced` value can appear as a declaration.)*
- [x] Demonstrated both ways on Excellence: with a declaration an `Unresolved` claim greens as `Assumed`; without it, W1 blocks. *(`tests/runner/test_w1_assumed_claims.py::TestBothWaysOnExcellence`.)*

## 10. Canonical-pack deriver extension

**What to build:** The canonical reference pack — which the preservation gates check prose against — is generated from the *same* source as the prose (Tier 3 confirmed facts + declared assumptions) with per-entry provenance, so an assumed value can never masquerade as a confirmed canonical fact and drift into the contradictions those gates catch.

**Blocked by:** 9 (β honesty layer), 1 (Component-binding substrate).

- [ ] The canonical-pack deriver reads `working_assumptions.json` in addition to Tier 3 confirmed facts.
- [ ] Every pack entry carries provenance (confirmed vs assumed); an assumed value is never emitted as confirmed.
- [ ] The deriver is migrated from scheduler-built to an agent-runtime-invoked component and recorded in `invoked_components` (per the C2 roster).
- [ ] The canonical-preservation gates (contradiction detectors) still pass against the regenerated pack for the Excellence section.

## 11. Extend decomposed drafting to Impact + Implementation

**What to build:** The whole decomposed-drafting stack proven on Excellence is applied to the Impact and Implementation sections, so all three criterion sections draft, assemble, honor declared assumptions, and pass their section-specific checks.

**Blocked by:** 7 (Excellence decomposed drafting), 9 (β honesty layer), 10 (Canonical-pack deriver extension).

- [x] Impact and Implementation draft as bounded per-sub-section calls → assembler → section JSON, mirroring Excellence. *(The driver `draft_section_decomposed` and `assemble_section` were already slug-generic; the tracer bullet `tests/runner/test_impact_implementation_decomposed_drafting.py` proves the decompose→compose chain for both sections — full-length, sequential context, byte-equal replay, section-specific `extra_fields` carried. Governed node binding + live skill rewrite stay with the E2E run, ticket 13, per ticket 7's scope.)*
- [x] W1 is appended to `gate_10b` and `gate_10c`; the assumption-applier and canonical pack cover all three sections. *(`g09b_p12` / `g09c_p11` added to `gate_rules_library.yaml` **and** the manifest `gate_registry` predicate_refs — ticket 9 had defined `g09a_p11` in the library only, so W1 was inert under Approach-B resolution even on Excellence; that manifest omission is now fixed too, so W1 runs on all three drafting gates. Appliers already registered for all three slugs; the canonical pack is section-agnostic.)*
- [x] Impact-specific checks pass (`dec_coverage`, `impact_pathway_refs`); Implementation-specific checks pass (`wp_table_refs`, `gantt_ref`, `milestone_refs`, `risk_register_ref`). *(`impact_pathways_covered` (`g09b_p06`) and `implementation_coverage_complete` (`g09c_p06`) validate these fields; the tracer bullet asserts both pass on the real assembled sections.)*
- [x] `gate_10d` cross-section consistency is green across the three assembled sections. *(`cross_section_consistency` (`g09d_p07`) is green across the three decomposed→assembled sections in `TestGate10dGreenAcrossThreeSections`; a flagged `consistency_log` still blocks, guarding the green.)*

## 12. `.docx` exporter

**What to build:** The assembled Part B is rendered to a `.docx` file — the primary deliverable format (D14) — from the section / assembled JSON, replacing the JSON-only output today.

**Blocked by:** 4 (Section assembler — establishes the section shape).

- [ ] A renderer converts assembled Part B JSON into a `.docx` written to `final_exports/`.
- [ ] The exporter is dependency-declared (adds `python-docx`) and runnable from the run entry point.
- [ ] It renders whatever sections exist; the full B1 (all three sections) renders once Impact + Implementation (ticket 11) land.
- [ ] The `.docx` reflects section content, headings, and structure faithfully — no content is invented at export.

## 13. End-to-end MSCA-PF run (α/β) + independent re-verify

**What to build:** A full-DAG MSCA-PF run that is either honestly blocked or all-green depending on what the operator declares — the milestone's definition of done (D14) — with the `.docx` export and an independent traceability re-verification.

**Blocked by:** 8 (Unit-cost budget + `gate_09`), 10 (Canonical-pack deriver extension), 11 (Impact + Implementation), 12 (`.docx` exporter).

- [ ] Mode **α** (no declarations): the run fails closed with an informative block on the researcher / host / call spine — enumerated unconfirmed claims + a confirmation checklist (a correct terminal state, §13.4).
- [ ] Mode **β** (host+ declared): every Phase-8 gate is green (every `Assumed` operator-declared, W1 satisfied), producing a full B1.
- [ ] The `.docx` is exported for the β run.
- [ ] Both CI byte-equal checks pass (assembler; unit-cost budget).
- [ ] An independent subagent re-verifies that every material claim traces to Tier 3 or a declared assumption.

## 14. Hand-lift MSCA Tier 3 from the vault (project instantiation)

**What to build:** Tier 3 is populated with the MSCA project's *confirmed* substance, lifted once
by hand from the `MSCA/` vault (the graph compiler is milestone 2, D2-A) — so the engine has
grounded project data to run Phases 1–8 against. The researcher / host / call spine is left
explicitly unresolved and enumerated, because that is what makes the honest block honest.

**Blocked by:** 3 (Purge & re-instantiate — Tier 3 must be skeletonised and the `MSCA/` SHA pinned first).

- [x] Tier 3 `project_brief/` (concept note, project summary, strategic positioning) and
      `architecture_inputs/` (objectives, outcomes, impacts, workpackage seed, risks, milestones seed)
      are populated from the vault's methodology.
- [x] **Only `source_grounded` vault content is lifted as Confirmed.** Vault nodes marked
      `synthesis` / `inference` are lifted at most as Inferred and flagged; `unconfirmed` nodes are
      not lifted as fact (Appendix B mapping). No vault inference is promoted to a Tier 3 fact.
- [x] **The spine is not invented.** Researcher, host, supervisor, and any consortium partner remain
      absent/Unresolved — ELTE is *refuted*, not merely unconfirmed ("ELTE not mentioned in any
      source; do not invent a role"). Each gap is enumerated in a confirmation checklist.
- [x] `selected_call.json` carries the **operator-confirmed** MSCA-PF call (call id, topic,
      `instrument_type`, deadline, duration). If the operator cannot confirm the call, it is declared
      via `working_assumptions.json` (ticket 15) — never guessed by the engine.
- [x] Provenance is recorded: the lift cites the pinned `MSCA/` SHA (ticket 3, §9.5) and, per lifted
      fact, its source vault node — so milestone-2's graph compiler can regenerate and diff against
      this hand-lift (it is the compiler's test fixture).
- [x] `gate_01_source_integrity` is satisfied on the populated Tier 3 — or blocks naming the missing
      input, not a crash.

## 15. `working_assumptions.json` declaration substrate (Tier 3)

**What to build:** The Tier 3 file convention by which a human operator declares working assumptions —
the single mechanism that turns an honest block into a *conscious* green. Both consumers read it:
the budget gate (host-country coefficient) and the claim layer (`Assumed` claims). One host
declaration therefore unlocks both gates (D11/D12). The engine reads it and never writes it.
(The applier and the W1 predicate remain ticket 9; this is the convention, schema, and reader.)

**Blocked by:** 3 (Purge & re-instantiate — Tier 3 skeleton exists).

- [x] A Tier 3 `working_assumptions.json` convention exists with `provenance_class: manually_placed`:
      user-authored, engine-read-only. No `run_produced` path can create, modify, or back it.
- [x] Per-entry schema carries a stable key (`claim_id` / declaration key), the operator-declared
      value, and attribution + timestamp — sufficient for W1's `claim_summary == declared value`
      check (ticket 9) and for the budget deriver's host-coefficient lookup (ticket 8).
- [x] A shared reader serves **both** consumers, so a single host declaration resolves the
      living-allowance coefficient *and* the `Assumed` claims from one source (D11/D12).
- [x] Declarations are never silent: each declared assumption is surfaced (confirmation checklist /
      traceability) so a green bought by declaration is legible as **declared**, not confirmed.
      (Substrate: the shared reader's `as_surface()` renders each declaration legible-as-declared,
      and the budget path already surfaces the declared host as `Assumed`; wiring into the
      confirmation-checklist / traceability outputs lands in tickets 9/13.)
- [x] An absent or empty `working_assumptions.json` is a **valid** state — it yields the honest
      block (α), not an error.