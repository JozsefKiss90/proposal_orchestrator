# Engine-Readiness Audit — can the orchestrator finalize?

**Date:** 2026-07-14 · **Question:** Is the orchestrator in sufficient shape to run Phase 8 live and produce a full-length proposal section? · **Method:** static read of the Stage 3–6 build, manifest wiring, gate registry, and the live vs. test call graph. No DAG run.

---

## Verdict

**NOT READY to run Phase 8 live — one critical gap, and it is well-scoped.** The length-fix machinery is architecturally complete and unit-test-green, but the **live producer of per-sub-section drafts is not wired into the node body.** A live Phase 8 run today would skip drafting, find no `section_drafts/`, and fail at the assembler / `gate_10a`. This is exactly the "governed node binding + live skill rewrite" that tickets 7 and 11 explicitly deferred to ticket 13 — i.e. it is ticket 13A's core unfinished task, not a regression.

Deferring the finalization run was therefore **doubly right**: even with quota, Phase 8 could not currently produce output.

---

## What is sound (green)

- **Manifest topology.** n08a/b/c/d/e/f present; budget gate fans out to the three drafting nodes; assembly → review → revision edges correct.
- **All 8 deterministic components registered** in `runner/deterministic_components.py`: three section assemblers, three assumption-appliers, the unit-cost budget deriver, the canonical-pack deriver.
- **Gate wiring complete in the manifest registry** — not just the library. W1 is bound on all three drafting gates (`g09a_p11`, `g09b_p12`, `g09c_p11`, prose "Every assumed claim is operator-declared"); the canonical-preservation predicates (partner names, deliverable identity, titles, measurable targets) are bound; `gate_09` carries its unit-cost branch (`g08_uc01/uc02/uc03`). **The historical inertness bug — W1 defined in the library but not referenced in the manifest — is fixed.**
- **Components + unit tests exist** on disk, including the byte-equal replay checks (`assembler(drafts) == section_json`; `unit_cost_budget(…) == figure`).
- **Transport robustness improved today.** The two live-run defects found while running Phases 1–6 — front-truncation and the SkillResult success-envelope — are fixed fail-closed with regression tests.

## The critical gap (red) — the length fix has no live producer

The intended Phase-8 content flow is: **decomposed drafting** (bounded per-sub-section Claude calls) writes `phase8_drafting_review/section_drafts/<slug>/`, then the **deterministic assembler** array-appends those into the section JSON.

The live path implements only the **second half**:

- `runner/agent_runtime.py` (`_ASSEMBLER_SUPERSEDES_DRAFTING_SKILL`) **skips** the monolithic drafting skill when a `*_section_assembler` component is bound — marking it `superseded_by_decomposed_assembler` — and relies on the assembler to compose from `section_drafts/`.
- But **nothing live produces `section_drafts/`.** The producer `draft_section_decomposed` and the live drafter factory `_default_claude_drafter` (which *does* call the transport correctly, and correctly instructs the model to emit `Confirmed/Inferred/Unresolved` and *never* self-declare `Assumed`) are invoked **only from tests**. The module docstring states it plainly: *"the live path is never exercised in CI."*
- There is **no decomposed-drafting skill in the catalog** (only the monolithic `excellence/impact/implementation-section-drafting` skills — the ones being skipped) and **no preseed directory** present.

**Consequence of a live run now:** n08a skips the drafting skill → `canonical_pack_deriver` + `assumption_applier` run → `excellence_section_assembler` reads an absent `section_drafts/excellence/` → assembler fails or yields an empty section → `gate_10a` fails on a missing/empty artifact. **No proposal section is produced.**

## Secondary risks to shake out when 13A is wired (amber)

- **The live drafter has its own parser.** `_parse_drafter_response` (naive outermost-brace `find('{')`/`rfind('}')`) is **separate** from the `skill_runtime._extract_json_response` I hardened today. It is fail-closed (raises rather than silently repairing, §17.5.4 — good), but it does **not** carry the front-truncation / envelope tolerance, and the per-sub-section drafting calls are exactly the large-single-JSON shape that hit those two bugs. Expect to port the hardening here.
- **The whole Phase 7 → canonical-pack → Phase 8 live sequence has never run.** Every phase we ran live (2, 3, 5, 6) needed at least one fix. Budget quota for integration shakeout, not a clean pass.

## Implication for the plan

- **Precondition (b) — engine readiness — is NOT met.** It fails on one concrete, well-bounded item: wire the live decomposed drafter.
- This is **engine-side code work, independent of project-data consolidation (precondition a).** It can be built and tested without the real project data — the α/β/scaffolding data exercises it.
- It is **not a redesign.** Producer, driver, assembler, appliers, canonical pack, W1, and gates all exist. The missing piece is the wire: invoke `draft_section_decomposed` with `_default_claude_drafter` in the n08a/b/c node body, before the assembler component runs.

## The next build task (ticket 13A, precisely scoped)

1. **Wire the live decomposed drafter into the node body.** In the agent runtime, when a `*_section_assembler` is bound, invoke `draft_section_decomposed(run_id, repo_root, slug, drafter=_default_claude_drafter(repo_root), …)` to produce `section_drafts/<slug>/` **before** the assembler component runs (so supersession of the monolithic skill is replaced by an actual producer, not a void). Record it in `AgentResult.invoked_components` per §17.4.2/§16.5.
2. **Port the fail-closed truncation/envelope hardening** into `_parse_drafter_response` (or route the drafter through the shared parser), and raise the output ceiling per sub-section as needed.
3. **Add a live-path integration test** (mocked transport) that exercises node-body drafting → assembler → `gate_10a`, closing the "live path never exercised in CI" gap the docstring admits.
4. **Then** a single live Excellence-only slice (quota-aware) to confirm full-length output before committing to the whole B1.

Once (1)–(3) land, precondition (b) is met and 13A can run; 13B (finalization) still additionally needs precondition (a), the real data consolidated to Confirmed/Inferred.
