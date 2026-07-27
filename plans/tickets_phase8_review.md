# Tickets: Phase 8 adversarial-review findings + carried m2t10 backlog

The tracking layer for the open findings from `HANDOFF_phase8_adversarial_review_2026-07-23.md` (§4 register)
plus the backlog carried forward from `HANDOFF_phase8_m2t10_2026-07-22.md`. This file replaces the harness's
flat `vote_results/*.json` state as the source of truth for what remains open.

Work the **frontier**: any ticket whose blockers are all done. Tickets 1, 2, 4, 5, 6, 7 can all start now.

## State verified at ticket creation (2026-07-24, branch `graph`)

The prior handoff's §1 hygiene items are **done** — do not redo: the schema_id fix is fully committed
(`5787d7c`; the truncated `6761c13` is superseded), preseed round-2 is committed (`7e878fa` + `b5eb816`),
the stray brief copy is removed, and the tree is clean. Findings were re-verified against current code:
PRE-1 is confirmed live; PRE-2 is *partially* addressed by `b5eb816` (manifest-derived supersession now
carried into the skip set; the hardcoded-table origin and silent no-op on unmatched ids remain); CHK-1's
"confirm against the checkpoint-publish skill source" caveat is resolved — the skill's Step 2 hard-fails on
a `run_id` mismatch and the checkpoint schema has no provenance field, so the design premise holds.

Several findings are vote-surfaced (3 Opus skeptics) but not human-confirmed in every detail — each ticket's
first criterion is to re-verify its finding against the code as it stands when picked up.

---

## 1. PRE-1 — Close the preseed status-case gate bypass

**What to build:** A section artifact whose `validation_status.overall_status` says unresolved — in *any*
casing — must fail `gate_10a`. Today the claim-status roll-up logic normalises case while the
`no_unresolved_material_claims` criterion predicate compares the raw string exactly, so a preseeded
section carrying `'Unresolved'` sails through the gate while the canonical pack republishes a never-applied
declaration as in force. This is a fail-closed bypass — the one blocking bug left in the preseed item.

**Blocked by:** None — can start immediately.

- [x] Re-verify the mismatch (roll-up lowercases; the criterion predicate compares exactly) against current code. — confirmed live at `criterion_predicates.py:218` vs `claim_status.py`.
- [x] The status comparison is case-normalised consistently; audit the sibling criterion predicates for the same exact-match pattern and fix any others. — added single normalisation point `runner.claim_status.normalize_status`; routed the gate predicate + 3 reuse-admission siblings (`phase8_reuse.py`) through it. W1 already lowercased; coverage/resolution/revision-action compares are different vocabularies (whitelist-guarded), not the preseed surface.
- [x] A red-capable regression test proves a section with `'Unresolved'` fails `gate_10a` (test fails on the pre-fix code, passes after). — parametrized `Unresolved`/`UNRESOLVED`/`UnReSoLvEd` at the gate_10a criterion predicate (red pre-fix, green post-fix) + reuse-path + `normalize_status` unit coverage.
- [ ] `python scripts/lane_launcher.py vote B-review-preseed` re-run: PRE-1 no longer refutes. — **DEFERRED** (operator decision 2026-07-24): billed Opus vote; SDK not installed; lane stays REFUTED overall on the separate PRE-2/PRE-3 lenses. Fold into ticket 3's re-vote.
- [x] Zero new test failures against the pre-existing-failure baseline; committed from the repo root. — full-suite failing set byte-identical to pristine HEAD (28 failed + 6 errors, all pre-existing); committed `bcd5d60` from repo root.

## 2. CHK-1 — Checkpoint provenance quad: grill the design, then implement

**What to build:** Phase-scoped runs bootstrap phases 1–7 from a prior run's durable gate evidence, so those
gate results legitimately carry the prior `run_id` — and `checkpoint-publish` currently hard-fails on them,
blocking n08f. The decided direction: record the provenance quad `{original_run_id, evidence_path,
input_fingerprint, versions}` in the durable checkpoint artifact itself (mirroring the existing
`inherited_artifacts` idiom), and relax the skill's current-run_id input check **only in tandem** — so
cross-run inheritance is declared in the durable Tier-4 record, never validated against clearable
`.claude/runs/` state and never falsified by re-stamping. This changes a durable contract
("validated checkpoints must not be overwritten"), so the design is stress-tested before any code.

**Blocked by:** None — can start immediately.

- [x] A `/grilling` session stress-tests the decision before implementation (per operator instruction): at minimum — is the quad sufficient to make the checkpoint self-validating without `.claude/runs/`; how does it interact with the never-overwrite rule and with reruns; does relaxing the input check open any provenance-falsification path the quad doesn't close; does the checkpoint schema version need bumping. Outcome recorded in `docs/tier4_orchestration_state/decision_log/` (§9.4). — grilling done in the prior session; durable record `decision_log/chk-1-checkpoint-provenance-quad_2026-07-24.json` (D1–D4 + threat-model boundary + no-amendment rationale).
- [x] The checkpoint artifact schema gains the provenance quad for bootstrapped gate evidence; the checkpoint-publish skill spec's run_id validation accepts a bootstrapped gate result iff its provenance is declared in the quad — the two changes land together, never the relaxation alone. — **Option 2 (skill retired):** schema §1.9 gains optional/additive `inherited_gate_provenance` (v1, no bump); the deterministic `checkpoint_publisher` component (`runner/checkpoint_publisher.py`) authorizes cross-run gates by set-membership against `accepted_upstream_gates` and records the quad. Component + schema + reader land together (commit `2cafe8b`).
- [x] Any validator/predicate reading the checkpoint artifact accepts (and checks) the new field; a checkpoint claiming inheritance it can't evidence fails closed. — `checkpoint_published` predicate (consistency-only, D4) re-validates the quad vs durable gate results; fails closed on hidden inheritance or quad drift; all-current-run still passes.
- [x] Regression tests cover: all-current-run (unchanged behaviour), legitimately bootstrapped (passes with quad recorded), mismatched run_id with no declared provenance (still fails). — `tests/runner/test_checkpoint_publisher.py` + `predicates/test_schema_predicates.py::TestCheckpointPublishedProvenanceQuad`. Full suite: failing set byte-identical to baseline (28 failed + 6 errors), zero new failures.
- [x] The previously blocked n08f `checkpoint-publish` scenario (bootstrapped phase 1–7 gates under a fresh phase-8 run_id) passes end to end. — component→predicate e2e (`TestComponentPredicateIntegration`) + manual drive: component writes the checkpoint with quad, gate_12 `checkpoint_published` passes. Unblocks DOD-1.

## 3. PRE-2 + PRE-3 — Single authoritative skip-binding source, fail-closed on drift

**What to build:** The preseed/reuse drafting-skill skip is driven by hardcoded name-string tables
(`PRESEED_NODE_CONFIG`, `REUSE_SKIP_SKILLS`, `REUSE_ELIGIBLE_NODES`) that are never checked against the
manifest's resolved `skill_ids`. Two consequences: an unmatched skip id is a silent no-op, so a skill
rename lets the monolithic drafter overwrite a preseeded section while the audit record falsely claims it
was skipped (PRE-2); and eligibility and skip live in separate tables consulted at different times, with
the `drafting_skipped_audit_executed` decision persisted to Tier 4 *before* the skip lookup — a node
eligible but absent from the skip table records "drafting skipped" and still recomposes over stale drafts
(PRE-3, latent). One design closes both: a single authoritative binding, resolved against the manifest,
failing closed on any drift. Note: the manifest-derived supersession carry-forward already landed in
`b5eb816` partially covers the drift case for deterministic components — verify what remains before designing.

**Blocked by:** PRE-1 (keep the preseed surface stable until its re-vote holds and is committed).

- [x] Re-verify both findings against current code, accounting for the `b5eb816` carry-forward; record what is already covered. — confirmed live: four tables name "the drafting skill" (`PRESEED_NODE_CONFIG[.]["skipped_skill"]`, `REUSE_SKIP_SKILLS`, `REUSE_ELIGIBLE_NODES` eligibility, `agent_runtime._ASSEMBLER_SUPERSEDES_DRAFTING_SKILL`), none checked against manifest `skill_ids`. `b5eb816` only *carries the manifest-derived supersession into the skip set* (Step 3) — a no-op-on-drift mitigation for assembler-bound nodes; it neither fails closed (PRE-2) nor fixes the reuse decision being persisted at `dag_scheduler.py:1714` *before* the `REUSE_SKIP_SKILLS.get` lookup at 1717 (PRE-3, latent). Both open.
- [x] Skip-skill ids are resolved against the manifest's resolved `skill_ids` for the node; a skip id that matches nothing is a hard failure (fail-closed), not a silent no-op. — new `runner/phase8_skip_binding.validate_skip_binding`; scheduler blocks `blocked_at_exit`/`CONSTRAINT_VIOLATION` on drift (preseed validates *before apply*, reuse *before persist*). The b5eb816 carry-forward loop is removed — subsumed by the fail-closed guard. Verified live manifest names all three drafting skills, so real runs pass.
- [x] Eligibility and skip-binding come from a single source (or the tables are asserted in agreement at load time), so "audit says skipped" and "drafting actually suppressed" can never diverge. — `PHASE8_DRAFTING_SKILL_BY_NODE` is the single source; `PRESEED_NODE_CONFIG.skipped_skill` and `REUSE_SKIP_SKILLS` derive from it; `REUSE_ELIGIBLE_NODES` node-set and `_ASSEMBLER_SUPERSEDES_DRAFTING_SKILL` values asserted in agreement at import (`SkipBindingError` on drift).
- [x] The Tier-4 reuse/preseed decision record is written only when the suppression it describes is actually in force. — preseed skip binding validated before `maybe_apply_phase8_preseed` (no artifact/audit on failure); reuse decision `record_reuse_decision` moved *after* the binding check (blocks + records `not_reused` on failure, never a false `drafting_skipped_audit_executed`).
- [x] Regression tests cover: renamed/unmatched skip id (hard failure, not overwrite), eligible-but-unbound node (no false audit record), and the normal agree case (unchanged behaviour). — `TestSkipBindingFailsClosedOnDrift` (rewrote the two b5eb816 drift tests to assert fail-closed + added eligible-but-unbound + normal-agree) + new `tests/runner/test_phase8_skip_binding.py` (`validate_skip_binding`, single-source agreement, load-time helpers). Targeted files green; full suite: zero new failures vs baseline (the sole non-run is the pre-existing TR-1 hang in `test_skill_runtime.py`, untouched by this ticket).
- [ ] `python scripts/lane_launcher.py vote B-review-preseed` re-run: verdict HOLDS UP. — **DEFERRED** (same operator basis as PRE-1 item #4): billed Opus vote, Claude Agent SDK not installed locally. Left for the operator to run; not blocking the code changes.

## 4. SCH-1 + SCH-2 — schema_id backfill tool: registry-driven discovery + root validation

**What to build:** The one-time backfill tool discovers gate results by globbing `phase_outputs/**` and
duck-typing, which misses gate results written to fallback/non-standard locations (e.g. the evaluator's
fallback directory and the `alpha_honest_block` result) — and when pointed at a wrong `--repo-root` it
scans nothing and exits 0, indistinguishable from "all conforming". Both are latent (the live backfill
already ran clean) but make the tool untrustworthy for any future re-run.

**Blocked by:** None — can start immediately.

- [ ] Re-verify both findings against the current tool.
- [ ] Discovery is driven by the gate-result registry (the runtime's own knowledge of where gate results live), not by glob + duck-typing; the previously missed locations are found.
- [ ] An invalid or wrong `--repo-root` is rejected with a distinct error; "scanned zero files" is reported distinctly from "all conforming" (different exit/report), never a silent success.
- [ ] Tests cover: fallback-location discovery, wrong-root rejection, zero-scan vs all-conforming distinction, and the existing conflict-fail-closed behaviour still intact.

## 5. TR-1 — Transport timeout: kill the process tree (carried from m2t10 §4.2)

**What to build:** On Windows, `subprocess.run(timeout=...)` does not kill the `claude` CLI's Node child
process tree, so a stalled CLI call hangs indefinitely (~2h observed, Ctrl-C dead) instead of failing at
the configured timeout. A timed-out transport invocation must terminate the whole tree (`taskkill /F /T`
on Windows, process-group kill on POSIX) and surface the existing timeout error. High-value robustness fix;
the final validation needs the local CLI — the harness's unused `A-transport` lane (`diagnosing-bugs`
entry point) is the intended vehicle.

**Blocked by:** None — can start immediately. Must run locally (not in a cloud sandbox).

- [ ] On timeout the transport kills the full child process tree on both platforms and raises the existing timeout exception — no orphaned Node processes.
- [ ] A unit test with a dummy long-running child (spawning its own child) proves the tree dies at timeout; mocked-transport tests are unaffected.
- [ ] Live validation on the local CLI (the `A-transport` lane or a manual stalled-call reproduction): the call fails at the configured timeout instead of hanging.
- [ ] No change to transport semantics on the success path (same result contract, same exceptions).

## 6. ST-1 — Phase 3–6 staleness: content, not mtime (carried from m2t10 §4.3)

**What to build:** The Tier-3 promote rewrote `architecture_inputs/*.json` (adding a provenance field), so
their mtimes postdate the phase 3–6 gate results and bootstrap rejects them as stale — even though the
content the gates validated is residual-0 identical. Bootstrapped evidence should be judged stale by
*content* (fingerprint/hash of the gate-relevant inputs), not wall-clock mtime, or via an explicitly
sanctioned re-validation path. Small design decision first; it touches the same bootstrap-evidence contract
as CHK-1, so keep the two consistent.

**Blocked by:** None — can start immediately (coordinate the contract language with CHK-1 if both are in flight).

- [ ] Re-verify the staleness rejection against the current bootstrap logic and the promoted artifacts.
- [ ] The chosen staleness mechanism (content-fingerprint comparison, or a sanctioned re-validation) is decided and recorded in the decision log (§9.4).
- [ ] A content-identical artifact with a newer mtime is accepted by bootstrap; a genuinely changed artifact is still rejected.
- [ ] Regression tests cover both directions (identical-content/newer-mtime passes; changed-content fails).

## 7. LG-1 — Coarse claim ledger, measured (carried from m2t10 §4.4)

**What to build:** Graph-sourced Part B sections carry a node-level claim ledger (≈1 `claim_status` per
sub-section) versus the drafter's granular ledger (~38 per sub-section) over byte-identical prose. The
operator accepted this provisionally; the eval harness's E2/E3 (status-aware faithfulness + ledger
completeness) exist precisely to quantify it — offline, zero DAG runs. This ticket produces the numbers
and converts the provisional acceptance into a recorded decision (accept coarse, or enrich the compiler's
ledger derivation).

**Blocked by:** None — can start immediately. Caveat: the harness lives on the `harness` branch — run E2/E3
against this branch's artifacts (merge or cherry-pick as needed; the harness is one-way isolated from `runner/`).

- [ ] E2/E3 run against the current graph-sourced Tier-5 sections and the drafter-era ledgers, producing comparable metrics for both.
- [ ] The granularity gap is quantified (per-section metric deltas), not just described.
- [ ] An accept-or-enrich decision, with the numbers as evidence, is recorded in the decision log (§9.4).
- [ ] If "enrich" is chosen, a follow-up ticket is filed with the measured target — the enrichment itself is out of scope here.

## 8. DOD-1 — M2-T10 definition-of-done back-half (carried from m2t10 §1)

**What to build:** The graph-sourced run passed the whole Phase-8 gate chain but the milestone-2 T10 DoD
back-half was never closed: the projector mirror of Tier-4 state back into the vault's phase-gate-state
folder, an independent claim→node re-verification, a determinism re-check (re-run `--from-graph`, confirm
byte-identical staging), and the outstanding decision-log entries (open-Q #4 resolution "parallel +
explicit promote", coarse-ledger property). With the checkpoint contract from CHK-1 in place, this also
closes the previously blocked n08f revision node — the literal end of M2-T10.

**Blocked by:** CHK-1 (n08f is blocked on checkpoint-publish until the provenance contract lands).
LG-1's numbers feed the coarse-ledger decision-log entry if available, but do not gate this ticket.

- [ ] Tier-4 phase/gate state is mirrored into the vault's phase-gate-state folder by the projector and validates against the graph schema.
- [ ] An independent claim→node re-verification confirms every Part B claim traces to its vault node (not merely that the compile ran).
- [ ] `--from-graph` re-run produces byte-identical staging output (determinism re-check).
- [ ] Decision-log entries exist for open-Q #4 and the coarse-ledger property.
- [ ] The previously blocked n08f completes: checkpoint published under the CHK-1 contract, closing M2-T10.
