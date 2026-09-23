# Handoff — CHK-1: Checkpoint provenance quad (Option 2: retire the skill)

**For:** a fresh session that will *implement* CHK-1.
**Branch:** `graph` (working tree was clean at session start).
**Status:** design **complete and operator-confirmed**; grilling (ticket criterion 1) **done in the prior session** — this doc is its durable record. **No code written yet.**

---

## 0. What this is

Ticket **CHK-1** in `plans/tickets_phase8_review.md` §2 (lines 40–57). Read that ticket for the
five acceptance criteria — they are the definition of done and are **not** duplicated here.

The prior session ran the `/grilling` session the ticket's first criterion mandates, resolved every
open decision with the operator, and confirmed the implementation plan. Your job is to **enact it**.

Do **not** re-grill. Do **not** re-derive the design. The decisions below are settled.

---

## 1. The bug (verify first, then fix)

Phase-scoped runs (`--phase 8`) bootstrap phases 1–7 from a prior run's durable gate evidence, so those
gate results legitimately carry a **prior `run_id`**. `checkpoint-publish` hard-fails on that mismatch,
blocking n08f.

Trace it in the code as it stands (ticket asks you to re-verify against current code):

- `runner/dag_scheduler.py:177` `bootstrap_phase_prerequisites` — seeds upstream nodes `released` from
  durable gate results; at **:279–283** records the acceptance via
  `ctx.record_accepted_upstream_gate(gate_id, original_run_id, evidence_path)`.
- `runner/run_context.py:314` `record_accepted_upstream_gate` writes
  `accepted_upstream_gates[gate_id] = {original_run_id, evidence_path, accepted_at, status}` into the run
  manifest under `.claude/runs/<run_id>/run_manifest.json` (**clearable runtime state, CLAUDE.md §9.2**).
  Reader: `:344` `get_accepted_upstream_gate`.
- `runner/predicates/gate_pass_predicates.py:96` `_check_continuation_acceptance` +
  `:370–392` — the **gate-evaluation** path *already* tolerates the run_id mismatch for a bootstrapped gate.
  So gate evaluation is fine today; **only** the `checkpoint-publish` skill's own check still fails.
- `.claude/skills/checkpoint-publish.md:61` — Step 2 "Run ID: `run_id` must match the current run_id"
  hard-fails with `MALFORMED_ARTIFACT`. **This is the sole remaining blocker.**

In a `--phase 8` run the 6 gates the checkpoint confirms split into: **`gate_09_budget_consistency`**
(phase 7, *bootstrapped → prior run_id*) and **`gate_10a/b/c/d`, `gate_11`** (phase 8, *current run_id*).
Only the cross-run ones need provenance.

Vote that surfaced this: `scripts/vote_results/B-checkpoint-decision.json` (REFUTED 2–1). Narrative:
`HANDOFF_phase8_adversarial_review_2026-07-23.md` §3.3 and the §4 register row for CHK-1.

---

## 2. Confirmed design decisions (settled — do not reopen)

| # | Decision | Choice |
|---|----------|--------|
| D1 | Authorization of a cross-run `run_id` at publish time | **Deterministic set-membership** against `accepted_upstream_gates`. The quad is assembled by a **deterministic component**, recorded via the `inherited_artifacts` idiom. Claude makes **no** provenance judgment. |
| D2 | Composition (who writes the checkpoint) | **Option 2 — retire `checkpoint-publish` as a skill.** It was determined to be 100% mechanical (see §3). A single deterministic component `checkpoint_publisher` writes the **whole** checkpoint incl. the authorized quad. No companion artifact, no Claude in the provenance path. The operator explicitly accepted shedding the ~370 lines of skill-spec tests as debt. |
| D3 | Schema version | **Keep `orch.checkpoints.phase8_checkpoint.v1`.** `inherited_gate_provenance` is optional/additive (absent for all-current-run), exactly like `inherited_artifacts` was added to gate_result with no bump. Existing committed checkpoint stays valid; no migration. |
| D4 | gate_12 reader strictness | **Consistency-only, record fingerprint.** The predicate re-validates the quad against durable gate results; it does **not** recompute `input_fingerprint` from current inputs (that content-freshness step belongs to **ST-1**, a separate ticket — keep them consistent, not merged). Record the fingerprint durably so ST-1 can build on it. |

**Threat-model boundary (must be stated in the decision-log entry):** the quad closes the *silent
provenance-loss* path — a durable checkpoint asserting inherited gates as its own run's product. It gives
**internal consistency + auditability against durable Tier-4 evidence**. It is **not** tamper-proofing
against a malicious `docs/` writer — that is out of scope, identical to every other Tier-4 artifact
(anyone with `docs/` write access can fabricate). "Self-validating without `.claude/runs/`" means the
checkpoint + durable gate results are internally consistent and traceable; run-time *entitlement* to
inherit (the freshness decision made at bootstrap) is inherently not re-derivable from cleared state and
is not claimed to be.

---

## 3. Why Option 2 is justified (the "is it mechanical?" finding)

Every step of `.claude/skills/checkpoint-publish.md` is a deterministic transform of its inputs:

- Step 1 — existing-checkpoint guard: file-exists + `status=="published"` → halt. Pure lookup.
- Step 2 — validate 6 gates: presence, `schema_id==`, `status=="pass"`, `run_id` match. Equality checks.
- Step 3 — Tier-3 snapshot: `call_id`/`topic_id`/`partner_ids` via `data.get(...)`; "absent → note" is a
  trivial conditional.
- Step 4 — write: `gate_results_confirmed` is a fixed list of gate_ids; assemble JSON, write.

No inference, no domain reasoning. Only `published_at` is non-deterministic — a publication stamp like
`gate_result.evaluated_at`, not derived content. This is precisely the C2 (§17.5.3) deterministic-component
pattern ("canonical-pack generation, assumption-application are deterministic transforms that write
canonical artifacts"). Modelling it as a Claude skill was the anti-pattern.

---

## 4. Change surface (the implementation plan)

Reference files by the paths below; read them before editing.

### 4.1 New deterministic component
- `runner/checkpoint_publisher.py` (new) — `publish_checkpoint(run_id, repo_root) -> Path | None`.
  Logic, in order:
  1. **Write-once guard:** if `docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json` exists
     with `status=="published"` → **raise** (preserve the never-overwrite contract; today the skill
     returns `CONSTRAINT_VIOLATION` — a raised component fault becomes `AGENT_EXECUTION_ERROR`, which is
     the correct fail-closed for a component).
  2. Read + validate the 6 gate results (presence, `schema_id == GATE_RESULT_SCHEMA_ID`, `status=="pass"`).
  3. **Authorize:** for any of the 6 whose `run_id != current run_id`, require a matching
     `accepted_upstream_gates` entry (`RunContext.load(repo_root, run_id).get_accepted_upstream_gate(...)`,
     `original_run_id` + `status=="pass"` match); else **raise** (fail closed).
  4. Build `inherited_gate_provenance`: one entry per authorized inherited gate —
     `{gate_id, original_run_id, evidence_path, input_fingerprint, versions:{manifest_version,
     library_version, constitution_version}}`, all **copied verbatim** from the durable gate result.
  5. Tier-3 snapshot (`selected_call.json` → call_id/topic_id; `partners.json` → partner_ids; absent → null/empty + note).
  6. Atomic write `phase8_checkpoint.json`: `schema_id` v1, current `run_id`, `status="published"`,
     `published_at`, `gate_results_confirmed`, `tier3_snapshot`, and `inherited_gate_provenance`
     **omitted when empty** (→ byte-identical to today's all-current-run checkpoint).
  - Determinism guarantee (document in the module docstring): pure lookup + copy over gate results and
    authorized provenance; `published_at` excluded from the replay invariant, mirroring
    `gate_result.evaluated_at`.
- `runner/deterministic_components.py` — add `_run_checkpoint_publisher` adapter (mirror
  `_run_canonical_pack_deriver` at :139) and register `"checkpoint_publisher"` in `COMPONENT_REGISTRY`
  (:171). **Do NOT** add it to `DRAFT_CONSUMING_COMPONENTS` (:208) — it doesn't read `section_drafts/`.
- Find the atomic-write helper the existing components use (`_atomic_write`) — check
  `runner/phase8_canonical_pack.py` / `runner/section_assembler.py`; reuse it.

### 4.2 Manifest
- `.claude/workflows/system_orchestration/manifest.compile.yaml` node `n08f_revision` (:279–293):
  remove `checkpoint-publish` from `skills` (:291); add `deterministic_components:\n  - checkpoint_publisher`.
  Copy the binding shape from n04 (:100), n07 (:154), or n08a (:194). Update the node comment.

### 4.3 Schema
- `.claude/workflows/system_orchestration/artifact_schema_specification.yaml` §1.9 `phase8_checkpoint`
  (:1402–1443): add optional `inherited_gate_provenance` (mirror `inherited_artifacts` item_schema at
  :2351–2367). **Also fix stale text:** the `gate_results_confirmed` description (:1441–1442) still names
  `gate_10_part_b_completeness`/`gate_12` (pre-decomposition); and "Produced by: runner after gate_12 …
  passes" (:1404) is wrong — the checkpoint is written in the n08f *body* (now by the component) and
  *verified* by gate_12's `checkpoint_published` predicate. Correct both.
- Check `docs/index/schema_registry.json` and the schema list at `artifact_schema_specification.yaml:3113`
  — schema_id is unchanged (v1) so likely no registry edit, but confirm.

### 4.4 Reader predicate
- `runner/predicates/schema_predicates.py:1691` `checkpoint_published` — today only checks
  `status=="published"`. Extend (self-contained; derive `tier4_root` from the checkpoint path's parents;
  import `GATE_RESULT_PATHS`/`GATE_RESULT_SCHEMA_ID` from `runner.gate_result_registry`):
  - For each gate in `gate_results_confirmed`, read its durable gate_result. If
    `gate_result.run_id != checkpoint.run_id`, it **must** have an `inherited_gate_provenance` entry
    (else fail — hidden inheritance).
  - Each quad entry: `evidence_path` exists, is a valid passing gate_result, with
    `run_id == original_run_id`, `input_fingerprint` matches, `versions` match. Fail closed on any drift.
  - Keep it backward-compatible: all-current-run checkpoint (no quad) still passes.

### 4.5 Housekeeping (unbind the retired skill)
- `.claude/workflows/system_orchestration/skill_catalog.yaml` — remove/deprecate the `checkpoint-publish`
  entry (currently `execution_mode: tapm`).
- Check `used_by_agents` refs: `.claude/agents/revision_integrator.md`, `.claude/agents/state_recorder.md`,
  `.claude/workflows/system_orchestration/agent_catalog.yaml`. Unbind cleanly.
- Decide whether to delete `.claude/skills/checkpoint-publish.md` or leave it deprecated/unreferenced.
- `.agents/skills/handoff/…` and `MSCA/.claude/…` are unrelated — leave alone.

### 4.6 Decision-log entry — **DO THIS FIRST** (ticket criterion 1, §9.4)
Write `docs/tier4_orchestration_state/decision_log/chk-1-checkpoint-provenance-quad_2026-07-24.json`
(match the shape of a recent sibling, e.g. `gate-result-schema-id-fix-and-backfill_2026-07-22.json`).
Content: the grilling outcome; decisions D1–D4 from §2; the **threat-model boundary** verbatim from §2;
and the **no-CLAUDE.md-amendment rationale** (see §5). This is the durable record the grilling criterion
requires — the design currently lives only in this handoff, which is not Tier-4.

---

## 5. No constitutional amendment needed (record the reason)

Retiring one skill and moving checkpoint publication to a deterministic component is a straight
**application** of already-ratified rules — the C2 amendment (§17.5.3: components read declared inputs and
write canonical artifacts) and C3 (§16.5: manifest-bound components). Nothing in the constitution mandates
that checkpoint publication be a *skill*. §17.6.2 (components can't evaluate gates — the component writes
the checkpoint; the *scheduler* still evaluates gate_12) and §17.6.4 (skills don't invoke skills — n/a) are
respected. State this in the decision-log entry so a future reader doesn't mistake it for an un-recorded
constitutional change (§14.1).

---

## 6. Key runtime facts (already verified — trust these)

- **Components run before skills** in the node body: `runner/agent_runtime.py:1198–1233` ("Phase B+"),
  outputs refreshed into skill inputs at :1216. A component fault → `AGENT_EXECUTION_ERROR`,
  `can_evaluate_exit_gate=False`, exit gate skipped → n08f `blocked_at_exit`. So the component's
  fail-closed fires **before** anything is written — no "premature published checkpoint" hazard.
- **6 checkpoint gates + paths:** `runner/gate_result_registry.py` `GATE_RESULT_PATHS`;
  `GATE_RESULT_SCHEMA_ID == "orch.gate_result.v1"`. gate_09 → `phase_outputs/phase7_budget_gate/gate_result.json`.
- **Gate results always carry** `manifest_version`, `library_version`, `constitution_version`,
  `input_fingerprint`, `run_id`, `evaluated_at` (mandatory set at `gate_pass_predicates.py:40–50`) — so
  every quad field is a straight copy.
- `checkpoint_published` is checked at **n08f's exit gate (gate_12)** — see manifest gate at
  `manifest.compile.yaml` (the gate `evaluated_at: n08f_revision exit`, predicate `g11_p06`).

---

## 7. Tests (TDD; run with `py -3.10`)

Per repo memory: run pytest/runner with `py -3.10` (3.11 lacks pyyaml/pytest). **Establish the
pre-existing-failure baseline first** (`py -3.10 -m pytest -q` on `graph` HEAD before touching anything)
so you can prove "zero *new* failures" at the end, per the ticket's discipline.

- **Replace** `tests/runner/test_checkpoint_publish_spec.py` (skill-spec tests — now obsolete) with
  `tests/runner/test_checkpoint_publisher.py` (component tests):
  - all-current-run → checkpoint written, no quad, valid.
  - bootstrapped gate_09 with an `accepted_upstream_gates` entry → quad recorded correctly.
  - cross-run gate **not** in `accepted_upstream_gates` → component **raises** (fail closed).
  - write-once guard: existing published checkpoint → raises.
  - missing / non-pass / wrong-schema gate → raises.
- Predicate tests for `checkpoint_published` (extend its existing test module): all-current-run passes;
  valid quad passes; **cross-run gate with no quad entry fails**; quad entry with wrong
  `original_run_id`/`input_fingerprint`/`versions` fails.
- **Criterion 4** (regression): all-current-run unchanged; legitimately bootstrapped passes with quad;
  mismatched run_id with no declared provenance still fails.
- **Criterion 5** (end-to-end): n08f under a **fresh phase-8 run_id** with a bootstrapped gate_09 →
  checkpoint published with quad → gate_12 `checkpoint_published` passes. A component+predicate
  integration test that stages the bootstrap scenario (see the setup in
  `tests/runner/test_phase_continuation_bootstrap.py` for how to write gate results + record
  `accepted_upstream_gates`) is sufficient — a full mocked DAG run is not required.
- Update the manifest-consistency assertions that previously asserted `checkpoint-publish ∈ n08f.skills`
  to assert `checkpoint_publisher ∈ n08f.deterministic_components` and `checkpoint-publish ∉ skills`.

Finish with the full suite once (`py -3.10 -m pytest -q`) and diff the failing set against the baseline.

---

## 8. Suggested skills for the implementing session

- **`/tdd`** — build the component, the predicate extension, and the tests test-first at the seams above.
- **`/verify`** — after wiring, drive the bootstrapped-under-fresh-run_id scenario end to end and observe
  the checkpoint + gate_12 pass, not just green unit tests.
- **`/code-review`** — review the branch diff before committing (the `/implement` flow calls for it).
- (Do **not** re-run `/grilling` — the design is settled and recorded here.)

Commit to the current branch (`graph`) when green, per the `/implement` flow.

---

## 9. Definition of done (from the ticket — check every box)

`plans/tickets_phase8_review.md` §2 checkboxes 1–5. In this plan they map to: (1) decision-log entry
(§4.6) + this grilling record; (2) component + schema + reader land together (§4.1–4.4); (3) reader checks
the field, fails closed (§4.4); (4) the four regression cases (§7); (5) the bootstrapped-under-fresh-run_id
e2e (§7 criterion 5). Ticket **DOD-1** (§8 of the tickets file) is *blocked on CHK-1* — landing this
unblocks the previously-blocked n08f revision node.
