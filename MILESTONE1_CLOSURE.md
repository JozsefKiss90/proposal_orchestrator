# Milestone 1 — Closure Record

**Date:** 2026-07-14 · **Branch:** `msca-pf-milestone1` · **Run:** `msca-pf-syn-01`

Milestone 1 is closed with **both intended outcomes captured**, one live and one deferred. This document is the honest account of what exists, what is deferred, and what must be committed.

---

## 1. Headline: the governed DAG runs, and it runs *honestly*

The system is now an executable orchestration engine, not a specification. On real inputs it does the two things the milestone set out to prove:

- **α — it refuses to fabricate.** On the honest Tier 3 (spine Unresolved), the live governed DAG **blocks at Phase 2**: the scope-alignment gate will not proceed while the researcher/host/supervisor spine is unknown. That block is the milestone's headline artifact.
- **Option 0 — it can produce a full green when the inputs exist.** With the spine populated (synthetically, under a logged override), Phases 1–6 run green end to end.

Both are real. The first is the more important one.

---

## 2. What is DONE

### 2.1 Phases 1–6 — green and durable

| Phase | Node | State | Exit gate |
|-------|------|-------|-----------|
| 1 Call Analysis | n01 | released | phase_01_gate ✓ |
| 2 Concept Refinement | n02 | released | phase_02_gate ✓ |
| 3 WP Design | n03 | released | phase_03_gate ✓ |
| 4 Gantt & Milestones | n04 | released | phase_04_gate ✓ |
| 5 Impact Architecture | n05 | released | phase_05_gate ✓ |
| 6 Implementation Architecture | n06 | released | phase_06_gate ✓ |

Phase outputs are durable in `docs/tier4_orchestration_state/phase_outputs/`. Run-scoped gate-pass records are in `.claude/runs/msca-pf-syn-01/` (runtime state, clearable per §9.2).

### 2.2 α — captured and tagged

- Tag **`alpha-honest-block`** → the honest-block evidence commit.
- Evidence: `docs/tier4_orchestration_state/alpha_honest_block/` (Phase-2 gate result, concept summary, run log).
- Tag **`honest-tier3-unresolved-spine`** → the pre-override honest state (spine Unresolved).

### 2.3 SYN-SPINE-01 — the demo shortcut, fully logged

The identity spine (fellow / host / supervisor / partners) was filled with **synthetic** demo data under an explicit **§3 operator override** of §13.3, scoped and logged. It is **not real and not submittable**.

- `decision_log/synthetic-spine-demo-override_2026-07-13.json` — spine identity.
- `decision_log/synthetic-concept-override-extension_2026-07-14.json` — concept content (SR-04 training dimensions, SR-05 CDP timing) needed to clear Phase 2.
- Propagated across Tier 3; `consortium/partners.json` derived from `roles.json` to satisfy the Phase-3 partner-coverage gate.

### 2.4 Runtime robustness — two defects found and fixed *by running the thing*

Running the DAG on real inputs surfaced two transport/parse bugs that no unit test had caught. Both are now fixed and logged; both make the runtime **fail closed on bad responses while correctly parsing good ones**.

- **Front-truncation** (`decision_log/runtime-truncation-fix_2026-07-14.json`): an over-long generation returned only its tail, and the parser silently salvaged a leading fragment — surfacing as a misleading "required field missing". Fixed the parser to fail closed on interior fragments, and raised the CLI output ceiling so large single-object artifacts are not cut off.
- **SkillResult-shaped success envelope** (`decision_log/runtime-skillresult-envelope-normalization_2026-07-14.json`): the model sometimes wraps the gate payload in `{status:"success", payload:{…}}`. The runtime already normalized the *failure* envelope; the *success* analog (Phase D.6) was added, with a regression test that also proves an incomplete wrapped payload still fails closed.

---

## 3. What is DEFERRED (and why that is correct)

Phases 7 and 8 are **pending**, deliberately. See `decision_log/phase7-8-deferral_2026-07-14.json`.

- **Phase 7 (budget).** Not "unlocked" — it did not need to be. `budget_regime = unit_cost`, so gate_09 takes the deterministic unit-cost branch: it checks a Claude-free derivation (`confirmed_months × published_rates × HU coefficient`), with no cost breakdown and no external budget planner. That is already the trivial gate the operator wanted. A blanket "unlock by default" was **refused** — it would weaken gate_09 for lump-sum instruments and require a §14 amendment, not a silent flip.
- **Phase 8 (drafting).** Deferred on constitutional grounds, not just token cost: §11.5 and §13.8 forbid finalizing proposal text from incomplete or unvalidated state. The methodology is not finalised and the spine is synthetic, so a "completed" Part B now would be exactly the fabrication the engine exists to prevent. Deferral is the honest call.

**Option 0 (full-green B1 + marked `.docx`) is therefore deferred**, to be completed after the weekly quota resets (~3 days) by running Phase 7 then the β tail (`scripts/run_msca_pf_e2e.py beta`).

---

## 4. ⚠️ ACTION REQUIRED — commit the working tree

All of today's work is **uncommitted**. `HEAD` is still `8af56ef` ("Wave 6 state record… Phase 2 blocked"), which predates:

- `consortium/partners.json`
- the two runtime fixes (`runner/skill_runtime.py`, `runner/claude_transport.py`) and the new regression tests
- the Phase-3/4/5/6 successful phase outputs in Tier 4
- the four new decision-log records (concept override extension, truncation fix, envelope normalization, 7/8 deferral)

The Phases 1–6 *durable* outputs are on disk, but the run-scoped gate-pass records live in `.claude/runs/` (clearable). **Commit before any git operation** or the milestone evidence and the runner fixes can be lost. Suggested:

```
git add -A
git commit -m "Milestone 1: Phases 1-6 green on SYN-SPINE-01; runtime truncation + envelope fixes; 7/8 deferred"
git tag milestone1-phases1-6-green
```

---

## 5. Next: milestone 2

Scoped in `MILESTONE2_SCOPE.md`. In one line: **extend the β declaration substrate to Phases 2–6** so the spine can be honestly *declared* rather than needing the SYN-SPINE-01 synthetic shortcut — the honest fix for the gap this milestone exposed.
