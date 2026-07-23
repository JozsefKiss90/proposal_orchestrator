# Handoff — Phase 8 / M2-T10 → full-scale overview & calibration

**Date:** 2026-07-22
**Repo:** `C:\Code\proposal_demo\proposal_orchestrator` · **branch:** `milestone_2` · **constitution:** `CLAUDE.md`
**Next-session focus (per operator):** stop the Phase-8 whack-a-mole; do a *full-scale app overview*, check overall state, define a clean deduplicated task backlog, and stand up debugging + calibration. This doc forwards the Phase-8 / M2-T10 thread so nothing is lost.

> Convention: this handoff **references** artifacts by path rather than duplicating them. Read the referenced files.

---

## 1. Where M2-T10 (graph-sourced run) actually stands

- **The substantive win:** the graph-authored Part B (from the ticket-8 vault) passed the **entire Phase-8 evaluator gate chain** on run `msca-pf-graph-01` — `gate_10a` (excellence), `gate_10b` (impact), `gate_10c` (implementation), `gate_10d` (cross-section), `gate_11` (evaluator review) all green. The M2 thesis — *vault -> `--from-graph` compile -> promote -> runner -> gates* — works end to end.
- **Open-Q #4** was resolved for this run as **"parallel + explicit promote"**: `--from-graph` compiles to staging (non-destructive), then `tools/promote_graph_staging.py` promotes staging -> `docs/`. The promote surfaced that the graph Part B has **byte-identical prose** to the M1 drafts but a **coarse claim ledger** (5/4/3 node-level `claim_status` vs the drafter's 191/119/96 granular). Operator chose to proceed graph-sourced and record the granularity as a known property.
- **Blocked only at n08f (revision)** on the `checkpoint-publish` housekeeping skill (see section 2).
- **DoD back-half not done:** projector mirror (Tier 4 -> vault folder `18_phase_gate_state`), independent claim->node re-verify, determinism re-check (re-run `--from-graph`, confirm byte-identical staging), decision-log entry for open-Q #4 + coarse-ledger.

## 2. The current blocker — a bootstrap <-> checkpoint design tension (NOT a quick fix)

- **Failure:** `checkpoint-publish` -> *"Gate result at `.../phase7_budget_gate/gate_result.json` has run_id mismatch: found 'msca-pf-real-01', expected 'msca-pf-graph-01'"*.
- **Root cause:** phase-scoped runs (`--phase 8`) under a fresh run-id **bootstrap phases 1-7 from the prior run's (`msca-pf-real-01`) durable gate evidence**; those gate-result files legitimately carry `run_id: msca-pf-real-01`. `checkpoint-publish` requires **every** gate result to carry the **current** run_id -> systemic mismatch on all bootstrapped gates (1, 2, 7).
- **Why this is a design decision, not a patch:** it is the same class as the `schema_id` bug just fixed (bootstrapped, foreign-run artifacts failing a current-run validation). Backfilling `schema_id` was legitimate (static field); **backfilling run_id would falsify provenance** (misrepresent which run produced the gate) — the wrong fix. The operator's instinct that "this won't be definitively solved here" is correct: it needs a contract decision.
- **Options for the next session to weigh:**
  1. **Relax `checkpoint-publish`** to accept bootstrapped gate results (validate against bootstrap provenance / `original_run_id`, not require current run_id). Cleanest; aligns with how phase-scoped bootstrap is designed to work. *(Recommended starting point.)*
  2. **Full fresh 1-8 run** (no bootstrap) so every gate result is written under the current run-id. Expensive (re-runs phase 1-6 agents) but also clears the section 4.3 staleness — the literal "1-8 green" close.
  3. **Bootstrap re-stamps run_id** on seeded gate results (as preseed does for sections). Falsifies provenance — *not recommended.*

## 3. Fixes already landed this session (do not redo)

- **`gate_10b` `canonical_terms_preserved` false-positive** (WP appositive = a deliverable's exact id+title was misread as a botched WP title). Fixed with an `_appositive_is_other_entity` guard + 2 regression tests. **Committed `6ab3a92`.** Ref: `docs/tier4_orchestration_state/decision_log/gate10b-canonical-cross-reference-false-positive_2026-07-17.json`.
- **Preseed suppression of draft-consuming components** — `runner/dag_scheduler.py` (uncommitted): in preseed mode, drop `*_section_assembler` + `*_assumption_applier` (keep `canonical_pack_deriver`), so a preseeded section isn't re-composed over by stale `section_drafts` (was failing on spine run_id mismatch). **Needs a regression test.**
- **Gate-result `schema_id`** — `runner/gate_evaluator.py` (uncommitted) now emits `schema_id: "orch.gate_result.v1"` (required by `artifact_schema_specification.yaml` but historically omitted from all gate results). One-time backfill of 13 legacy results via `tools/backfill_gate_result_schema_id.py`. Ref: `docs/tier4_orchestration_state/decision_log/gate-result-schema-id-fix-and-backfill_2026-07-22.json`. **Needs a regression test.**
- **Decomposed-drafting enriched empty-content error** — `runner/decomposed_drafting.py`. **Committed `b95e0ee`.**

## 4. Open issues / residuals for the debugging + calibration pass

1. **checkpoint-publish run_id (section 2)** — the immediate blocker; a bootstrap/checkpoint contract decision.
2. **Transport 2-hour hang on Windows** — `runner/claude_transport.py` uses `subprocess.run(timeout=1200)`; on Windows this does not kill the `claude` CLI's Node child-process tree, so a *stalled* CLI call hangs indefinitely (observed ~2h; Ctrl-C dead) instead of failing at 20 min. Fix: `Popen` + process-tree kill on timeout (`taskkill /F /T` on Windows, `os.killpg` on POSIX). **NOT DONE.** High-value robustness fix; **untestable from a sandbox** (needs the local CLI) — validate live.
3. **Phase 3-6 mtime-staleness** — the Tier-3 promote rewrote `architecture_inputs/*.json` (adding a `provenance_detail` field), so their mtime postdates the phase 3-6 gate results -> bootstrap rejects them as stale. Content is **residual-0-identical**; cosmetic for the run (Phase 8 dispatched off the budget gate) but a DoD gap. A full fresh 1-8 (section 2 option 2) clears it.
4. **Coarse claim ledger** — graph `proposal_section` nodes emit 1 `claim_status`/sub-section (node-level `evidence_strength`) vs the drafter's ~38/sub-section. Prose identical; traceability granularity coarser. **This is exactly the axis the eval-harness E2/E3 exist to measure** (`tickets_eval_harness.md`).
5. **Missing regression tests** for the section-3 dag_scheduler preseed-suppression and gate_evaluator schema_id fixes.

## 5. Uncommitted state on `milestone_2` (reconcile early in the overview)

- `runner/gate_evaluator.py` (schema_id), `runner/dag_scheduler.py` (preseed suppression), `runner/predicates/phase8_section_predicates.py` + its test (possibly further operator edits on top of `6ab3a92`).
- New: `tools/promote_graph_staging.py`, `tools/backfill_gate_result_schema_id.py`.
- `docs/tier3` + `docs/tier5` promoted to graph-sourced; `docs/tier4_.../graph_compile/` (staging, diff_report, part_b_report, `pre_promote_backup/`, `promote_record.json`); 13 backfilled gate results; `docs/tier4_.../preseed/phase8/` sections; 2 new decision logs.
- Also present: the operator's own uncommitted M2 work (~30 `.claude/agents/*.md` prompt specs) — **not mine; leave for the operator.**
- **Recommendation:** triage + commit in logical groups. The M1 engine fixes (predicate, preseed suppression, schema_id) are branch-independent and must be preserved into whatever branch runs the final close.

## 6. Key references (read, don't duplicate)

- Constitution & runtime contract: `CLAUDE.md` (esp. section 6 phases/gates, section 8 budget, section 17 runtime).
- Runtime code: `runner/dag_scheduler.py`, `agent_runtime.py`, `gate_evaluator.py`, `claude_transport.py`, `phase8_preseed.py`, `decomposed_drafting.py`, `section_assembler.py`, `predicates/phase8_section_predicates.py`.
- Graph (M2) track: `runner/graph_compiler.py`, `graph_config.py`, `vault_reader.py`, `graph_projector.py`, `vault_scaffold.py`; `MSCA/graph.config.yaml`; `tickets_milestone2.md` (T8, T9 done; T10 in progress per section 1; T11 pending).
- Eval / calibration plan: `tickets_eval_harness.md` (E1-E9, earn-its-lane, E1-E3 as M3's independent verifier) + `EVALUATION_HARNESS_STRATEGY.md` + `EVAL_HARNESS_TICKETS_REVIEW.md`.
- M3 (composition) scope: `MILESTONE3_SCOPE.md`.
- Decision logs: `docs/tier4_orchestration_state/decision_log/` (this session's two, plus `13b-real-data-consolidation_2026-07-16.json`).

## 7. Suggested approach for the overview + calibration

- **Baseline the whole app, not just Phase 8.** Inventory nodes/gates/agents/skills/predicates against `CLAUDE.md` section 17; the graph track (compiler/projector/pack) against `tickets_milestone2.md`; the eval-harness plan as the calibration backbone.
- **Define one deduplicated backlog** spanning: the checkpoint/bootstrap decision (section 2), the transport hardening (section 4.2), the staleness handling (section 4.3), the two missing regression tests (section 4.5), and the M2-T10 DoD back-half (section 1). The current TaskCreate list (tasks 1-8) is Phase-8/M2-centric and should be re-baselined.
- **First calibration signal:** eval-harness **E1-E3** (status-aware faithfulness + ledger completeness) are **offline, zero-DAG-run**, and directly quantify the coarse-ledger question (section 4.4) against the current artifacts. Cheapest high-value starting point.

## Suggested skills

- Fresh agent should use the **Explore** / **general-purpose** sub-agents to inventory the codebase for the overview (read-only fan-out).
- **`skill-creator`** — if building eval/calibration or debugging skills for the harness.
- **`docx`** or **`pdf`** — if the overview is delivered as a formal document.
- Note: Ragas / DeepEval / PromptFoo (the eval frameworks in `tickets_eval_harness.md`) are **not** Claude skills — confirm their current APIs against docs at build time (they predate the May-2025 knowledge cutoff).
