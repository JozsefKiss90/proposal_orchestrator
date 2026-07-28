# Handoff — Phase 8 adversarial-review pass (schemaid · preseed · checkpoint)

**Date:** 2026-07-23 · **Repo:** `C:\Code\proposal_demo\proposal_orchestrator` · **Branch:** `graph`
**Continues:** `HANDOFF_phase8_m2t10_2026-07-22.md` (references it; does not duplicate it).
**Scope of this session:** an adversarial-review + rework pass over the three *landed-fix / decision*
items from the prior handoff — the schema_id fix, the preseed-suppression fix, and the checkpoint-publish
run_id decision. Driven by an operator harness (`scripts/lane_launcher.py`, see §6). This was **not** a
full pass over the m2t10 backlog; most of it is untouched (§5).

> Convention (inherited): reference artifacts by path; read the referenced files rather than trusting
> summaries. Every finding below is tagged with its confirmation status — several are *vote-surfaced*
> (three independent Opus-4.8 skeptics) but **not yet confirmed against the code by a human**.

---

## 0. Status at a glance

| Item | State | Latest verdict | What remains |
|------|-------|----------------|--------------|
| **schema_id** | ✅ CLOSED (committed) | HOLDS UP 3–0 | 2 latent, non-blocking backfill-robustness follow-ups (SCH-1/2) |
| **preseed suppression** | 🟡 IN FLIGHT (round 2, uncommitted) | REFUTED 2–1 | 1 blocking bug (PRE-1) + 1 design (PRE-2) + 1 latent (PRE-3) |
| **checkpoint run_id** | 🟠 DECIDED, NOT BUILT | REFUTED 2–1 (design) | Implement provenance quad (CHK-1); confirm against skill source |
| m2t10 backlog (4.2/4.3/4.4/DoD) | ⬜ UNTOUCHED | — | Carried forward (§5) |

**One-line read:** one of three review items closed, one a single concrete bug from done, one designed
but unbuilt, and the wider handoff backlog not started. We are **not** near closing the m2t10 handoff.

---

## 1. Immediate hygiene — do this first

1. **Commit or stash the uncommitted preseed round-2 work** (as of last terminal state, 6 files:
   `runner/agent_runtime.py`, `runner/claim_status.py`, `runner/dag_scheduler.py`,
   `runner/phase8_preseed.py`, `runner/phase8_reuse.py`, `tests/runner/test_preseed_suppression_scheduler.py`,
   plus `scripts/vote_results/B-review-preseed.json` and `scripts/vote_results/apply_log.jsonl`). Don't
   start the next item on top of it.
2. **Verify the schema_id commit is whole:** `git show --stat 6761c13` should list the 11 fix files
   (gate_evaluator.py, gate_result_registry.py, gate_pass_predicates.py, the backfill tool, the fixtures,
   the tests). It was briefly committed with only `apply_log.jsonl` because `git add .` was run from
   `scripts/` (cwd-relative). **Lesson for the next session: run `git` from the repo root, or `git add -A`.**
3. **Untracked leftover to remove:** `plans/reports/PHASE8_FULLSCALE_AND_OBSIDIAN_GRILL_BRIEF.md` (a stray
   copy an `apply` run made; the root original was restored).

---

## 2. Method used this session (and its limits)

The harness runs **cheap adversarial fan-out → majority vote → apply → re-vote**: for each item, three
independent Opus-4.8 skeptics (each a different "lens") try to *refute* the fix/decision and emit a
machine-parsed `VERDICT_JSON`; Python majority-tallies and persists the verdict. A refuted item goes
through an `apply` lane (fix + regression test); a held item's test is locked via `seams`. Full mechanics
in §6.

**What it is good for:** catching plausible-but-wrong fixes (it refuted all three items on the first pass,
and caught that the first schema_id/preseed attempts were inadequate). **What it is not:** it is *not*
spec-driven (scope is conveyed by prompt prose, not derived from CLAUDE.md/tickets), it has *no issue
tracker* (state = the flat `vote_results/*.json` + `apply_log.jsonl` + git history), and the
`diagnosing-bugs` skill it references **never actually ran** (only the unused `A-transport` lane invokes
it). This handoff exists partly to convert that ad-hoc state into trackable tickets (§4).

---

## 3. Item detail

### 3.1 schema_id — CLOSED ✅ (committed `6761c13`, verified HOLDS UP 3–0)

**Fix applied** (all confirmed against code during the apply run):
- New `GATE_RESULT_SCHEMA_ID` constant in `runner/gate_result_registry.py` — single source of truth so
  evaluator / predicate / backfill can't drift from the spec.
- `tools/backfill_gate_result_schema_id.py` — a present-but-different `schema_id` is now reported as a
  **conflict**, never rewritten; CLI exits 1. Only an absent/null field is added (§17.6.5: a wrong
  schema_id is a validation failure, not auto-correctable). Was `…:55` `{k:v … if k != "schema_id"}`.
- `runner/predicates/gate_pass_predicates.py` — `schema_id` added to `_MANDATORY_FIELDS` + a value check
  → `MALFORMED_ARTIFACT`, as `artifact_schema_specification.yaml:2163-2166` mandates. Closes the
  "caught only at n08f" gap.
- `runner/gate_evaluator.py` — stamps the shared constant (writer at `…:877`, the only runtime writer).
- 5 fixtures/builders updated; regression seams `tests/runner/test_gate_result_schema_id.py` (15) + 2 in
  `test_gate_pass_predicates.py`; **red-capable verified** (reverted fixes → 6 assertions failed → restored).
- Test state: pre-existing failures only (13 fail + 6 err in `tests/runner`, 15 in `tests/`, all
  reproduced on a clean stash); zero new. Live backfill dry-run: `changed=0 already_ok=9 conflicts=0`.

**Open (non-blocking, latent):** SCH-1, SCH-2 in §4.

### 3.2 preseed suppression — IN FLIGHT 🟡 (round 2 uncommitted; REFUTED 2–1)

Two apply rounds. Round 1 covered the reuse path (the original "reuse path missed at
`dag_scheduler.py:1673`" is addressed). Round 2's vote still refutes, but the surface has narrowed to one
concrete blocking bug plus a standing design issue:

- **PRE-1 (BLOCKING):** `rollup_inconsistency` lowercases `overall_status` (`claim_status.py:84,104`) but
  `no_unresolved_material_claims` compares *exactly* (`criterion_predicates.py:218`) → a preseeded section
  with `'Unresolved'` passes `gate_10a` while `canonical_pack_deriver` republishes the never-applied
  declaration as in force. **This is a fail-closed bypass — the one thing to fix before preseed is done.**
- **PRE-2 (design):** the carried-forward drafting-skill skip is hardcoded name-string matching across
  three tables, never checked against the manifest's resolved `skill_ids`; an unmatched skip id is a
  silent no-op, so a skill rename lets the monolithic drafter overwrite a preseeded section while the
  audit record falsely claims it was skipped.
- **PRE-3 (latent, holds_up=True):** suppression is gated on `REUSE_SKIP_SKILLS.get(node_id)` truthy while
  the `drafting_skipped_audit_executed` reuse decision is persisted to Tier 4 *before* that lookup — a
  node in `REUSE_ELIGIBLE_NODES` but absent from `REUSE_SKIP_SKILLS` would record drafting-skipped and
  still recompose over stale drafts. Latent only (the two tables currently share keys).

**Recommendation:** one more `apply preseed` targeting PRE-1 likely closes the blocker; PRE-2/PRE-3 are
better as tracked design tickets than another loop.

### 3.3 checkpoint run_id — DECIDED, NOT BUILT 🟠 (REFUTED 2–1; no code written)

The vote is unanimous on the shape even where it "holds": relaxing the input run_id check alone (handoff
§2 option 1) just relocates option-3's provenance falsification into the durable Tier-4
`phase8_checkpoint.json`, whose schema has no field for cross-run inheritance, validated against ephemeral
`.claude/runs/` state (§9.2 clearable). **Decision (CHK-1):** record the provenance quad
`{original_run_id, evidence_path, input_fingerprint, versions}` into the checkpoint artifact itself
(mirroring the existing `inherited_artifacts` idiom), and relax the input check only in tandem. **Not yet
confirmed against the `checkpoint-publish` skill source** — the votes could not read it. This is a design
change to a durable contract: implement deliberately (this is the item most worth `/grill-me`), not via
an autonomous apply loop.

---

## 4. Open findings register (ticket-ready)

Feed this to `to-tickets`. Severity: **B**locking / **D**esign / **L**atent. "Confirmed?" = whether a
human/apply has verified it against code (vs vote-surfaced only).

| ID | Item | Sev | Evidence (verify first) | Fix direction | Confirmed? |
|----|------|-----|-------------------------|---------------|-----------|
| PRE-1 | preseed | **B** | `claim_status.py:84,104` (lowercases) vs `criterion_predicates.py:218` (exact) | normalize case on both sides of the status compare; `'Unresolved'` must fail `gate_10a` | vote ×3, unconfirmed |
| CHK-1 | checkpoint | **B** | `phase8_checkpoint.json` schema has no inheritance field; validates vs `.claude/runs/` | add provenance quad to the durable checkpoint; relax input check in tandem | decided; confirm vs `checkpoint-publish` source |
| PRE-2 | preseed | **D** | drafting-skill skip = name-string match across 3 tables, not manifest `skill_ids` | resolve skip ids against manifest; fail-closed on unmatched id | vote ×3, unconfirmed |
| PRE-3 | preseed | **L** | `REUSE_SKIP_SKILLS.get(node_id)` vs audit persisted before lookup; `REUSE_ELIGIBLE_NODES` | single source for eligible↔skip; assert the two tables agree | vote ×3, latent |
| SCH-1 | schema_id | **L** | backfill globs `phase_outputs/**/*result*.json`; misses fallback `gate_evaluator.py:337` dir + `alpha_honest_block/phase2_gate_result_HONEST_BLOCK.json` | discover via `GATE_RESULT_PATHS`, not glob+duck-type | vote ×3, latent |
| SCH-2 | schema_id | **L** | backfill exits 0 when `--repo-root` wrong (rglob on missing dir → nothing; root unvalidated) | validate repo root; distinguish "scanned nothing" from "all conforming" | vote ×3, latent |

Carried-forward backlog items (full detail in `HANDOFF_phase8_m2t10_2026-07-22.md`), also ticket-able:
**TR-1** transport 2-h Windows hang (§4.2 — needs local `diagnosing-bugs`; `Popen` + tree-kill);
**ST-1** phase 3–6 mtime-staleness (§4.3); **LG-1** coarse claim ledger (§4.4 — measure with E2/E3);
**DOD-1** M2-T10 DoD back-half (projector mirror, independent claim→node re-verify, determinism re-check,
decision-log entries).

---

## 5. Untouched (carried forward verbatim from m2t10)

This session did not touch: the **transport hang (4.2)**, **mtime staleness (4.3)**, **coarse ledger
(4.4)**, or the **M2-T10 DoD back-half** (§1 of the prior handoff). Read
`HANDOFF_phase8_m2t10_2026-07-22.md` for their full context — nothing there is superseded except that the
schema_id and preseed "missing regression tests" it flags (its §4.5) are now partially addressed
(schema_id done; preseed's seam exists but the votes judge it inadequate — see PRE-2).

---

## 6. The harness (`scripts/lane_launcher.py`) — tooling reference

Operator tool; **separate from the §17 runtime — do not wire into the DAG scheduler.** Drives the Claude
Agent SDK; each "lane" is one `query()` session. Runs on the local `claude` CLI via your Max subscription
(no API key — confirm `echo $env:ANTHROPIC_API_KEY` is empty, or billing diverts to the API).

**Commands**
- `python lane_launcher.py vote <B-checkpoint-decision|B-review-preseed|B-review-schemaid> [n]` — n Opus
  skeptics, majority verdict → `scripts/vote_results/<lane>.json`.
- `python lane_launcher.py apply <preseed|schemaid|checkpoint>` — reads that verdict, applies fix + test
  (refuted) or writes the seam (held); leaves changes uncommitted; logs to `apply_log.jsonl`.
- `python lane_launcher.py seams [item]` — verdict-gated: writes the seam only for items that HELD UP.
- `python lane_launcher.py log` — prints the apply-log (what ran, when, files changed).
- `python lane_launcher.py <C-calibration|A-transport>` — single-session lanes (A-transport is the
  unused `diagnosing-bugs` entry point for the transport hang; must run locally).
- `LANE_VERBOSE=1` restores the raw SDK message stream.

**Config = three dict tables:** `LANES`, `VOTE_LANES` (carry `lenses`), `APPLY_ITEMS` (map item →
verdict file + in-scope files). Adding a lane = adding a dict entry. `_make_options()` sets the SDK knobs:
`cwd`, `setting_sources=["project"]`, `skills="all"`, `allowed_tools`, `model` (None→default Opus),
`system_prompt` (preset + injected brief/handoff/CONTEXT), `max_turns`, effort.

**Known limits (see §2):** scope is prompt-directed not spec-enforced; no issue tracking beyond flat
files; `diagnosing-bugs` unused; the brief (`plans/DEBUG_KICKOFF_phase8_calibration.md`) is hand-authored,
not spec-derived.

---

## 7. Recommended next steps

1. **Hygiene** (§1): commit/stash preseed round 2; verify `6761c13`; delete the stray brief copy.
2. **Close preseed:** one targeted `apply preseed` for **PRE-1**, re-vote, commit when it holds.
3. **Convert this register to tickets** (`to-tickets` on §4) — this is the tracking layer the harness lacks.
4. **`/grill-me` the checkpoint decision (CHK-1)** before implementing — it changes a durable contract.
5. **Stop using the SDK loop as a general workflow.** It earned its keep on fix-verification; the
   remaining work (checkpoint design, the m2t10 backlog) wants tracked, spec-grounded tickets.

**Resuming this in a new session — pick one:**
- *Best:* fresh session with `/grill-me` + `to-tickets` — closes the structure/tracking gap directly.
- *Simpler:* a blank ultracode session given this handoff — it can review/plan/reason and run adversarial
  passes natively, **but it runs in the cloud** and cannot drive your local `claude` CLI or pipeline, so
  keep code-touching + local-CLI work (PRE-1 apply, TR-1 transport loop) on your machine.

---

## 8. Key references

- Prior handoff: `HANDOFF_phase8_m2t10_2026-07-22.md` (backlog, blocker context, DoD).
- Constitution: `CLAUDE.md` (§6 gates, §8 budget, §17 runtime, §9.2 `.claude/runs/`, §17.6.5 no-silent-repair).
- Runtime map: `CONTEXT.md`.
- Harness: `scripts/lane_launcher.py`; verdicts `scripts/vote_results/*.json`; run log `apply_log.jsonl`.
- Brief (hand-authored, non-spec): `plans/DEBUG_KICKOFF_phase8_calibration.md`.
- Commits (branch `graph`, as last observed): `efb64bd` preseed r1 · `453f2eb` tooling · `6761c13`
  schema_id (verify contents) · preseed r2 uncommitted.
- Eval/calibration: `tickets_eval_harness.md`, `EVALUATION_HARNESS_STRATEGY.md` (E2/E3 for LG-1).
