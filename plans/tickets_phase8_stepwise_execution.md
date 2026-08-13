# Tickets: Phase 8 stepwise execution (n08a–f)

Make Phase 8 **operator-steppable**: run n08a → n08f one sub-phase per invocation, so the operator
can judge each step's output before releasing the next, without corrupting upstream state. Source:
`plans/reports/HANDOFF_phase8_stepwise_execution_2026-08-13.md`. The DAG is **not** redesigned — the
manifest already defines the six nodes, gates and edges. What changes is invocation granularity.

Work the **frontier**: any ticket whose blockers are all done. Tickets 1 and 2 can start now.

## State verified at ticket creation (2026-08-13, tree `fieldwise-run-01`)

- Run `9468e1cf-2c71-49e8-91fb-57f6e7192126`: `n01`–`n07` released, `n08a`–`n08f` pending,
  `gate_09` passed under `budget_regime: unit_cost`. Phase 8 has never run on this instantiation.
  Tier 5 is empty and `phase_outputs/phase8_drafting_review/` does not exist.
- Findings re-confirmed against current code this session:
  - `runner/__main__.py::_parse_phase` (L63) collapses `8a` → `8`.
  - `substep` is read by nothing in `runner/`.
  - `bootstrap_phase_prerequisites` (`dag_scheduler.py:228`) refuses to seed nodes inside the
    requested phase.
  - The manifest artifact registry (L848–911) still lists retired node ids in `consumed_by`.

## Operator decisions (2026-08-13, recorded here per the ticket session's remit)

1. **One run-id** for the whole a→f sequence. Each step resumes the same `RunContext`
   (`load_or_initialize` preserves node states). No new intra-phase bootstrap channel is built.
   Ticket 3 hardens and tests the resume path instead.
2. **Single-node scope only.** No `--stop-after-node` semantic.
3. **Rerun of an already-gated sub-phase: refuse by default.** An explicit force flag re-runs it,
   forward-invalidates successor gate acceptance, and writes a decision-log entry (§9.4).

## Invariants (non-negotiable, from the handoff §4)

- §13.7 — no silent reordering, no weakened gate conditions. A step that cannot prove its
  predecessor passed fails closed.
- §17.6.2 — gates stay scheduler-owned.
- §6.3/§9.4 — a sub-phase counts as released only on a durable Tier 4 gate result with
  `status: pass`. Operator assertion and in-memory state do not count.
- §16.5 — node, agent, skill, component and gate bindings come from the manifest only.

---

## 1. Manifest hygiene — retire stale Phase 8 node ids from the artifact registry

**What to build:** The manifest's artifact registry references only live node ids, so any feature
that resolves registry entries (including the stepping work below) can never land on a retired node.
Today `n08a_section_drafting` and `n08c_evaluator_review` — node ids retired by the Phase 8
decomposition — survive in `consumed_by` entries (manifest ~L848–911). Pure prefactor; no behaviour
change intended.

**Blocked by:** None — can start immediately.

- [x] Re-verify the finding against current code: the retired ids are still present in the artifact
      registry. Confirm whether anything in `runner/` currently resolves them (expected: nothing
      breaks, the ids are simply dangling). *(Verified 2026-08-13: `consumed_by` is read by nothing
      in `runner/` or `tests/`; only `produced_by` is consumed, via
      `agent_runtime._load_artifact_registry`. The retired ids appeared only in `consumed_by` lists
      plus two `dag_scheduler.py` docstring examples.)*
- [x] Each stale entry is mapped to the correct current node(s) by what the artifact actually feeds
      under the decomposed design (a,b,c drafting / d assembly / e review / f revision) — not a
      blind one-for-one rename. The mapping rationale is stated in the commit message. *(Mapping
      grounded in each Phase 8 skill's declared `reads_from`.)*
- [x] A load-time or test-time consistency check asserts every `consumed_by`/`produced_by` id in the
      artifact registry resolves to a node in the node registry, so a future retirement cannot
      re-introduce dangling ids. *(Test-time: `tests/runner/test_manifest_artifact_registry.py`;
      consumers may also be gate ids, producers may be the `external_system` sentinel — both are
      deliberate registry vocabulary.)*
- [x] Zero new test failures against the baseline; committed from the repo root.

## 2. Single-node CLI scope resolved via the manifest `substep` field

**What to build:** An operator can invoke exactly one Phase 8 sub-phase, and the scheduler
dispatches that node and nothing else. The node is named by id (e.g. `n08b_impact_drafting`) or by
phase+substep shorthand (e.g. `8b`), resolved through the manifest's currently-unread `substep`
field. The scope flag is mutually exclusive with `--phase`. Gate evaluation is untouched: the node's
entry and exit gates run exactly as inside a full-phase run, evaluated by the scheduler.

**Blocked by:** None — can start immediately.

- [x] Re-verify the finding against current code: `_parse_phase` still collapses `8a` to `8`, the
      dispatch loop still drains every ready in-scope node, and `substep` is still read by nothing
      in `runner/`. *(Verified 2026-08-13: all three findings held before this ticket.)*
- [x] The CLI accepts a single-node scope in both spellings. It is mutually exclusive with `--phase`
      (distinct argument error when both are given). Scope resolution reads the manifest only
      (§16.5). An id or substep that matches no manifest node is a distinct argument error, not a
      silent empty run. *(`--node` flag; `ManifestGraph.resolve_node_scope` resolves via the
      manifest `phase_number`/`substep` fields only; argparse mutually-exclusive group; unknown
      scope → exit 3 with a distinct message. `_parse_phase` now rejects `8a`-style input with a
      pointer to `--node` instead of silently collapsing it.)*
- [x] A scoped run dispatches exactly the named node. A scoped node whose predecessors are not
      released in the loaded `RunContext` fails closed with a report naming the unmet predecessors —
      it is never dispatched (§13.7). (Durable-evidence re-verification of those predecessors is
      ticket 3, not this one.) *(Abort message + `[BLOCKED]` console/JSON lines name each unmet
      predecessor and its gate; no gate is evaluated for a never-dispatched node.)*
- [x] Entry-gate and exit-gate evaluation paths are unchanged and remain scheduler-owned (§17.6.2).
      `--dry-run` and `--json` work under node scope. *(`_dispatch_node` untouched; node scope
      reuses the same `scope_node_ids` filter as phase scope. Upstream-phase bootstrap reuses
      `bootstrap_phase_prerequisites` with the node's phase number — in-phase siblings are never
      seeded, per operator decision 1.)*
- [x] Regression tests cover: single-node dispatch (only that node runs), substep shorthand
      resolution, unknown id/substep rejection, `--phase`/node mutual exclusion, and the
      not-ready fail-closed path. *(`tests/runner/test_node_scoped_execution.py`, 28 tests, incl.
      in-process CLI runs with hermetic transport patches.)*
- [x] Zero new test failures against the baseline; committed from the repo root.

## 3. Same-run-id resume — predecessors proven by durable evidence, fail-closed

**What to build:** The sanctioned way to step a→f is one run-id resumed across six invocations
(operator decision 1). Today `RunContext.load_or_initialize` preserves node states, but that path is
untested for the sequence — and a persisted state string in `.claude/runs/` is runtime memory, not
source truth (§9.2). This ticket makes resume trustworthy. When a scoped step counts a predecessor
as released, that claim must be backed by the predecessor's durable Tier 4 gate result artifact
(`status: pass`, at its canonical `gate_result_registry` path). The claim must also pass the
existing content-based freshness check (`is_gate_fresh`). A `RunContext` that says released without
durable, fresh evidence fails closed (§6.3/§9.4).

**Blocked by:** 1. Manifest hygiene, 2. Single-node CLI scope.

- [ ] Re-verify the finding against current code: resume preserves node states verbatim, and nothing
      re-checks a released predecessor's durable gate result or freshness on resume. Confirm the
      in-phase bootstrap refusal (`upstream_needed -= phase_nodes`) still stands, so same-run-id
      resume is the only in-phase evidence carrier.
- [ ] On a scoped step, every predecessor treated as released is re-verified against its durable
      gate result artifact: present, schema-valid, `status: pass`, and content-fresh. Verification
      is read-only and scheduler-side. No gate result is written or re-stamped (§17.6.3).
- [ ] A predecessor with released state but a missing, failed, or unreadable durable gate result
      fails the step closed with a distinct reason. Stale evidence (fingerprint mismatch) fails
      closed with its own distinct reason. Neither is silently re-accepted or silently re-run.
- [ ] Regression tests cover: resume with durable fresh evidence proceeds; released-in-context but
      no durable artifact fails closed; durable artifact present but stale fails closed;
      upstream-phase (1–7) acceptance via `accepted_upstream_gates` still works unchanged alongside.
- [ ] Zero new test failures against the baseline; committed from the repo root.

## 4. Rerun of an already-gated sub-phase — refuse by default, force + decision log

**What to build:** Re-running a sub-phase after its successors have gated on its output currently
produces the `531ec9f0` failure mode. The re-run rewrites an artifact a downstream gate was
evaluated on, and every later run dies at `STALE_UPSTREAM_MISMATCH`. Encode operator decision 3:
scoping a node whose exit gate has passed, when downstream gates have passed on its output, is
**refused by default** with a report naming the at-risk downstream gates. An explicit force flag
re-runs the node, forward-invalidates successor gate acceptance transitively, and writes a
decision-log entry (§9.4) recording what was invalidated and why. Invalidated successors must then
re-run and re-gate — nothing auto-passes (§13.7).

**Blocked by:** 3. Same-run-id resume.

- [ ] Re-verify the finding against current code: a naive re-run would still reproduce the
      `531ec9f0` precedent, and no refusal or invalidation mechanism exists yet. (Precedent: an
      `n08f` re-run staled the `review_packet.json` that `gate_11` had gated on, failing
      `gate_12/g11_p01`.)
- [ ] Scoping an already-released node with gated successors refuses by default, naming each
      downstream gate whose evidence is at risk. Scoping an already-released node with **no** gated
      successors needs no force (nothing downstream to corrupt).
- [ ] The force path re-runs the node and marks all transitive successors' gate acceptance invalid,
      so they must re-execute and re-gate. Prior gate result artifacts are superseded with an audit
      trail, not silently deleted or overwritten.
- [ ] Every forced re-run writes a decision-log entry to
      `docs/tier4_orchestration_state/decision_log/` before the re-run proceeds: node, downstream
      gates invalidated, operator-supplied reason.
- [ ] Regression tests cover: default refusal with the at-risk gate list; force path invalidates
      transitively and writes the log entry; no-gated-successors re-run proceeds without force;
      post-force re-stepping re-gates the successors (no auto-pass).
- [ ] Zero new test failures against the baseline; committed from the repo root.

## 5. Operator inspection surface after each step

**What to build:** After a scoped step finishes, the operator can judge it without spelunking. One
report shows the node's terminal state, the artifacts written, the skills and deterministic
components invoked with statuses, and the exit gate's per-predicate detail (pass/fail with reasons).
The report is derived from durable state (`RunContext`, gate result artifacts, `run_summary.json`).
It introduces no new writer of gate results (§17.6.3) and no new binding source (§16.5). It survives
the console — durable file or reconstructible on demand — so the judgment basis for releasing the
next step is auditable.

**Blocked by:** 2. Single-node CLI scope.

- [ ] Re-verify against current code what a scoped step already emits (`--json` progress,
      `run_summary.json` `node_failure_details`, the durable gate result's predicate detail). State
      precisely which of the four report elements above are missing or scattered.
- [ ] One step-report surface (console + durable/reconstructible form) covers: node terminal state,
      artifacts written, skills and deterministic components invoked with statuses, and
      per-predicate exit-gate detail — for both a passing and a blocked step.
- [ ] The report is read-only over durable state: no gate result writes, no new state files that a
      gate or bootstrap would later trust (it is an account, not evidence).
- [ ] Regression tests cover report content for a passing step and for each blocking origin
      (entry gate, agent body, exit gate).
- [ ] Zero new test failures against the baseline; committed from the repo root.

## 6. Stepped-equivalence regression — six invocations ≡ one `--phase 8`

**What to build:** Proof that stepping is safe: a→f as six single-node invocations under one
resumed run-id ends where a single `--phase 8` run ends — same terminal node states, same durable
gate results, on mocked transport. And proof that stepping fails closed: a step whose predecessor
gate evidence is missing does not proceed. This is the integration seal over tickets 2–4. It lands
as tests only.

**Blocked by:** 2. Single-node CLI scope, 3. Same-run-id resume, 4. Rerun policy.

- [ ] Re-verify the semantics tickets 2–4 actually landed (flags, refusal shapes, invalidation
      markers) before writing the equivalence harness against them.
- [ ] Equivalence test: a→f in six scoped invocations (same run-id, mocked `invoke_claude_text`)
      reaches the same terminal node states and gate result statuses as one `--phase 8` run over
      the same fixtures.
- [ ] Fail-closed test: a scoped step whose predecessor lacks a durable passing gate result is
      refused, and the refusal is observable in the step report.
- [ ] Rerun-cycle test: force-re-running a mid-sequence node invalidates its successors, and
      re-stepping from there reconverges to a fully released a→f with re-evaluated gates.
- [ ] Zero new test failures against the baseline; committed from the repo root.
