# Milestone 1 — Status (NOT closed)

**Date:** 2026-07-14 · **Run:** `msca-pf-syn-01` · **Plan of record:** `PHASE8_FULLSCALE_AND_OBSIDIAN_GRILL_BRIEF.md`

> **Correction.** An earlier note framed milestone 1 as "closed." That was premature. Per D14 / Stage 7, milestone 1's done-condition is the **end-to-end MSCA-PF run through Phase 8, exported to `.docx`, independently re-verified** — the drafting engine actually producing length + honesty **for one real MSCA project.** That has not happened. This document is the honest status.

## Engine-integration proof — ACHIEVED (2026-07-15)

The live governed DAG ran **Phases 1–8** on `msca-pf-syn-01`. **The length fix is proven:** the Excellence section drafted **20,780 words** across 5 sub-sections (vs the old ~950) — the transport ceiling is gone, and decomposed drafting → deterministic assembly → gate ran end-to-end live. `gate_10a` then **honestly blocked** on 21 unresolved material claims (the synthetic spine + open vault decisions) and two canonical-preservation slips, while **W1 passed** — the anti-fabrication guarantee held. Both poles of the milestone thesis are demonstrated: full-length content *and* honest refusal to finalize unconfirmed content, exactly the D14 standard. Detail: `decision_log/milestone1-engine-integration-proof_2026-07-15.json`.

Remaining for a *real* finalization (13B) is project-side + tuning: real Confirmed/Inferred data, drafter canonical-preservation tuning, soft-cap tuning to the page limit, and Impact/Implementation `extra_fields` (task #9).

## Definition of done (brief D14 / Stage 7), as refined

Milestone 1 fixes **length and honesty inside the current drafting engine for one real MSCA project.** Done requires:

1. The confirmed MSCA-PF call run through **Phases 1–8**.
2. Every Phase-8 gate **green**, or an **honest block** naming the unconfirmed claims.
3. Part B exported to **`.docx`** within the profile page limit.
4. Both CI byte-equal checks pass (`assembler(drafts) == section_json`; `unit_cost_budget(…) == figure`).
5. An **independent subagent** re-verifies traceability.

**Operator refinement (2026-07-14) — ADOPTED** (`decision_log/d14-refinement-finalization-standard_2026-07-14.json`): a *finalized* proposal admits only **Confirmed / Inferred (proven)** claims. `Assumed`/`Unresolved` — and the SYN-SPINE-01 synthetic spine — were scaffolding to exercise the phases before the real project data is consolidated. β/W1 remain the honest interim-run mechanism and the anti-fabrication guard, but a β-green *on declared `Assumed`* is **not** a finalized proposal. Ticket 13 is now split: **13A** engine-integration (provable on scaffolding data) and **13B** finalization (requires real data consolidated to Confirmed/Inferred). The α honest block remains a valid terminal state.

## Done

- **Stage 0 — constitutional ratification.** C1 (§8/§7 budget), C2 (§17.5.3 + `invoked_components`), C3 (§16.5) ratified and applied to `CLAUDE.md`.
- **Stage 1 — re-instantiation.** MAESTRO purged; the project re-instantiated to MSCA; `MSCA/` vault pinned. *(Verify: `archive/maestro-demo` branch/tag + recorded SHA.)*
- **Stage 2 — instrument profile + MSCA extraction (partial).** `budget_regime = unit_cost` set; `instrument_profile` resolver present; Phase 1 gate passes for the MSCA call (Tier 2B slice generates). *(Verify: Tier 2A MSCA schemas extracted; page limit read from `af_he-msca-pf_en.pdf`, not general knowledge — brief §10.6 / Risk §6.)*
- **Stages 3–6 — drafting engine built (ticket 13).** Decomposed drafting, deterministic array-append assembler, assumption-applier, canonical-pack deriver, W1 predicate, unit-cost budget deriver, docx exporter — committed and unit-test-green. **Not yet exercised end-to-end on a full-length section.**
- **Runtime robustness (today).** Two transport/parse defects found by *running* the DAG and fixed fail-closed with regression tests: front-truncation (`runtime-truncation-fix_2026-07-14.json`) and the SkillResult success-envelope (`runtime-skillresult-envelope-normalization_2026-07-14.json`). `consortium/partners.json` created for the Phase-3 partner-coverage gate.
- **Phases 1–6 ran green** — but **on the SYN-SPINE-01 synthetic spine**, not real project data. This proves the DAG executes; it does **not** satisfy "one real MSCA project."
- **α captured** (tag `alpha-honest-block`): the honest block on the Unresolved spine — the headline that the engine refuses to fabricate.

## Remaining (the gap to done)

1. **Consolidate the real project data to Confirmed/Inferred.** The methodology has ~10 open research decisions (RQ1–RQ10) and the identity spine was synthetic. Until these are the researcher's actual confirmed decisions, there is nothing finalizable. *(This is partly outside the orchestrator — it is the researcher's project work.)*
2. **Verify the orchestrator is in sufficient shape to finalize.** Stages 3–6 machinery is built and unit-tested but never run end-to-end producing a full-length section. Audit readiness before committing tokens to a finalization run.
3. **Stage 7 — the finalization run.** Phases 7 → β tail (canonical pack → Phase 8 decomposed drafting → assembly → review) → `.docx`, on consolidated Confirmed/Inferred data. Deferred also by the weekly quota (`phase7-8-deferral_2026-07-14.json`).
4. **Independent traceability re-verification** (D14) — and, on real data, it verifies truth, not merely mechanism.

## The two preconditions for finalizing, stated plainly

Finalization needs **both**: (a) the **data** consolidated to Confirmed/Inferred (project-side), and (b) the **orchestrator** proven ready to draft at length without breaking a gate (engine-side). Neither is met today. (b) is the part that can be driven now, token-free, by auditing the Stage 3–6 build.

## ⚠️ Commit the working tree

Today's work is uncommitted (`HEAD` = `8af56ef`, pre-run). The two runner fixes, `partners.json`, the Phase 3–6 outputs, and the new decision-log records are on disk only. Commit before any git operation.
