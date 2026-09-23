# Debug + Calibration Kickoff Brief — Phase 8 / M2-T10

**Purpose:** stage (not execute) a debugging + calibration pass over the residuals in
`HANDOFF_phase8_m2t10_2026-07-22.md`, using the `diagnosing-bugs` skill and Opus-4.8 adversarial
review agents where each actually fits. Nothing here is a finding — these are ready-to-run scaffolds
(loop designs, refutation prompts, test seams) for **you** to run in your own environment.

> **Core rule you're staging around (from `diagnosing-bugs`):** *the skill IS Phase 1 — a tight,
> red-capable feedback loop. No red-capable loop → no hypothesising.* So the skill only earns its keep
> where a residual reduces to a loop. Most of this backlog does **not**. Assign lanes deliberately.

---

## Lane assignment (the whole point)

| # | Residual | Is it a bug? | Lane | Where it runs |
|---|----------|--------------|------|---------------|
| 4.2 | Transport 2-h hang on Windows | **Yes** — robustness bug | **A · diagnosing-bugs** (single loop) | **Local Windows only** |
| 4.3 | Phase 3–6 mtime-staleness | Borderline (provenance) | **A-lite · differential loop** | Mostly offline / sandbox-ok |
| §2 | checkpoint-publish run_id | **No** — contract decision | **B · adversarial decision review** | Anywhere (reasoning) |
| 4.5a | Preseed-suppression fix (untested) | Fix, not a hunt | **B · adversarial fix review + seam** | Sandbox-ok |
| 4.5b | schema_id emit/backfill (untested) | Fix, not a hunt | **B · adversarial fix review + seam** | Sandbox-ok |
| 4.4 | Coarse claim ledger | **No** — calibration | **C · eval harness E2/E3** | Offline, zero-DAG |
| §3 | gate_10b appositive guard (committed + 2 tests) | Done | optional single adversarial sanity pass | Sandbox-ok |

**Read of your proposed setup:** using `diagnosing-bugs` + Opus-4.8 + Ultracode is a *good* idea, but
as a **split**, not one monolithic "run the skill on the handoff":

- The skill is **Lane A only** — really just the transport hang (the one genuine loop-able bug), and
  its Phase-1 loop needs the local CLI, so it **cannot run in a cloud session**. That's the skill's own
  "when you genuinely cannot build a loop → get access to the env that reproduces it" clause.
- Opus-4.8 adversarial agents (Ultracode) are the **higher-leverage half**, but pointed at **Lane B** —
  the two *decisions* and the two *untested fixes*, where cost is dominated by *being wrong* and there
  is no test to catch a bad call. This is the same "cost-of-being-wrong → top model + adversarial
  verification" logic as before.
- **How they compose:** adversarial agents plug into `diagnosing-bugs` at **Phase 3** (attack the 3–5
  ranked hypotheses) and **Phase 5/6** (try to refute the proposed fix) — **never at Phase 1**. Don't
  let a swarm reason about code *without* a loop; that's exactly the failure the skill exists to prevent.
- **Lane C is neither** — the coarse ledger is a measurement, not a bug; send it to E2/E3.

**Suggested sequence (cheapest-high-value first, per handoff §7):** C (offline E2/E3) → B decision
(checkpoint contract, unblocks the close) → B fixes (+seams, then commit) → A transport (local).

---

## Lane A — `diagnosing-bugs` (run locally)

### 4.2 Transport 2-hour hang — **the one true skill target**
**Symptom to make the loop go red:** a *stalled* `claude` CLI call must fail at the timeout, not hang
~2 h. `runner/claude_transport.py` currently uses `subprocess.run(timeout=1200)`, which on Windows does
not kill the CLI's Node child-process **tree**.

**Phase-1 loop to build (deterministic, fast, local):**
1. Write a fake "unkillable" child: a script that spawns a **grandchild** which sleeps forever / ignores
   `SIGTERM` (mimics the Node tree). 
2. Invoke it through the *same* transport code path with a short timeout (e.g. 3 s).
3. Assert **both**: (a) the call returns/raises within `timeout + epsilon`; (b) **zero orphaned PIDs**
   remain afterward (`tasklist` / `ps` check). Symptom (b) is what a naive fix silently fails.

**Candidate hypotheses to seed Phase 3 (test, don't assume):**
- H1: `subprocess.run` timeout only signals the direct child; the grandchild tree survives → hang.
- H2: `stdout=PIPE` without draining deadlocks the child *before* the timeout logic runs.
- H3: even with `Popen`, killing after natural exit hits **PID reuse** and nukes the wrong process.

**When you write the fix (`Popen` + tree-kill), have the adversarial agents refute these:**
- POSIX: `os.killpg` needs the child started with `start_new_session=True` (setsid) or it kills nothing.
- Windows: `taskkill /F /T /PID` — check availability + exit codes; confirm it walks the whole tree.
- Race: guard the post-timeout kill against the process having already exited (PID reuse).
- Pipe: use `communicate(timeout=…)` or a reader thread so H2 can't mask the timeout.
- Is 20 min even the right ceiling for a single call?

### 4.3 Phase 3–6 mtime-staleness — **A-lite differential loop (offline)**
Root cause per handoff: the Tier-3 promote rewrote `architecture_inputs/*.json` (added
`provenance_detail`), bumping mtime past the phase 3–6 gate results → bootstrap rejects as stale.
- **Offline loop:** re-run `--from-graph` and byte-compare staging (determinism), **and/or** hash
  `architecture_inputs` with `provenance_detail` stripped to prove residual-0-identical.
- **Adversarial angle to test, not assume:** "content-identical so it's safe" — what real failure is the
  mtime check *guarding against*, and does silently accepting a rewritten-but-identical file defeat it?
- **Root-cause fix to weigh:** should `promote_graph_staging.py` be **write-if-changed** (never bump
  mtime for byte-identical content) so the staleness never arises at source?

---

## Lane B — Opus-4.8 adversarial review (Ultracode) — decisions + untested fixes

Spawn N independent Opus-4.8 skeptics, each prompted to **refute**, majority-vote the verdict. Give
each the staged file map below. These are the prompts to point them at:

### §2 checkpoint-publish run_id — **decision, not a bug (do NOT build a loop)**
> Invariant to protect: a gate result's `run_id` must *truthfully* identify the run that **produced**
> it. Pressure-test handoff-recommended **option 1** (accept bootstrapped results, validate against
> `original_run_id`): does it preserve that truth, or quietly weaken it? What becomes spoofable? When is
> **option 2** (fresh 1–8, which also clears 4.3 and yields a literal "1–8 green" close) the correct
> spend instead? **Option 3 (re-stamp) falsifies provenance — treat as the trap, not a candidate.**
> Output: the one-line contract to write into `checkpoint-publish`, e.g. *"accept a gate result whose
> `run_id` ≠ current iff it is recorded as a bootstrap input with a verifiable `original_run_id`
> provenance chain."* Name what you'd grep in the `checkpoint-publish` skill source to confirm first.

### 4.5a Preseed-suppression fix (uncommitted, untested)
> `dag_scheduler.py` drops `*_section_assembler` + `*_assumption_applier` in preseed mode but keeps
> `canonical_pack_deriver`. Refute: can `canonical_pack_deriver` consume working-assumptions that are
> now *never applied*, yielding a pack inconsistent with the preseeded prose? Is the suppression a robust
> signal or a brittle name-suffix match? **Missing seam to write:** a scheduler-in-preseed-mode test over
> a fixture (preseeded section + stale `section_drafts`) asserting the preseeded prose survives un-recomposed.

### 4.5b schema_id emit + backfill (uncommitted, untested)
> Refute: does the emit cover **every** gate-result write path (not just the happy one)? Is the backfill
> idempotent/safe to re-run? Does `"orch.gate_result.v1"` actually match `artifact_schema_specification.yaml`
> (verify — don't assume)? **Missing seam to write:** assert-**at-the-writer** that every emitted
> gate_result carries `schema_id`, not a shallow per-caller test.

### §3 gate_10b (already committed + 2 tests) — optional single pass
> One Opus pass on the *false-negative* direction only: does `_appositive_is_other_entity` now wave
> through a genuinely botched WP title? Do the 2 tests assert that direction, or only the original fix?

---

## Lane C — Calibration (eval harness, offline)

### 4.4 Coarse claim ledger — **not a bug; measure it**
Graph `proposal_section` nodes emit ~1 `claim_status`/sub-section vs the drafter's ~38; prose identical.
Convert it to a number the operator can track with **E2 (status-aware faithfulness)** and **E3 (ledger
completeness)** from `tickets_eval_harness.md` — offline, zero-DAG-run, directly on current artifacts.
This is the handoff's own "cheapest high-value starting point." No debugging loop involved.

---

## Context / file map to hand the agents
Base: `C:\Code\proposal_demo\proposal_orchestrator\`
- **Contract:** `CLAUDE.md` (gates §6, budget §8, runtime §17)
- **4.2:** `runner/claude_transport.py`
- **4.3:** `tools/promote_graph_staging.py`, the `architecture_inputs/*.json` set
- **§2:** the `checkpoint-publish` skill source + `CLAUDE.md` checkpoint clause + a bootstrapped
  `gate_result.json` (e.g. under the `msca-pf-real-01` durable evidence)
- **4.5a:** `runner/dag_scheduler.py`, `runner/phase8_preseed.py`
- **4.5b:** `runner/gate_evaluator.py`, `tools/backfill_gate_result_schema_id.py`,
  `artifact_schema_specification.yaml`
- **§3:** `runner/predicates/phase8_section_predicates.py` + its test
- **4.4:** `tickets_eval_harness.md`, `EVALUATION_HARNESS_STRATEGY.md`

## What cloud can't do (run these locally)
- **4.2 transport loop** — needs the local Windows `claude` CLI; untestable in a cloud sandbox.
- Any lane that runs the **actual pipeline** — needs your Max-subscription auth + local runtime.
- Lanes B (reasoning), C (offline eval on artifacts), and the 4.3 offline diff are environment-agnostic.

---

## How to start the session (runbook)

**Handing Claude this file is the right start, but it won't auto-run everything from one drop.** Two
things to know: (a) a skill fires when the task matches its *description* — `diagnosing-bugs` triggers on
"diagnose / debug this / broken / failing / slow", so open the debugging lane with those words (or invoke
it by name); (b) this brief spans **three lanes**, and only **Lane A is a `diagnosing-bugs` invocation** —
don't expect one skill call to cover the decisions or the calibration. **Drive it one lane per session**
(keeps context clean), in the order **C → B → A**. Copy-paste openers:

**Lane C — calibration (do first, offline, cheapest):**
> Read `plans/DEBUG_KICKOFF_phase8_calibration.md`. Lane C only: run eval-harness **E2 + E3** offline on
> the current artifacts to quantify the coarse claim ledger (handoff §4.4). This is measurement, not
> debugging — do not invoke `diagnosing-bugs`.

**Lane B — checkpoint contract decision (unblocks the close):**
> Read `plans/DEBUG_KICKOFF_phase8_calibration.md`. Lane B, checkpoint-publish run_id (§2). This is a
> **contract decision, not a bug — do not build a repro loop.** Under Ultracode, spawn 3 Opus-4.8
> adversarial agents to refute **option 1** using the brief's prompt; majority-vote; output the one-line
> contract and what to grep in the `checkpoint-publish` skill source first.

**Lane B — the two untested fixes (before you commit them):**
> Read the brief. Lane B: adversarially review the **preseed-suppression** and **schema_id** fixes
> (§4.5) with Opus-4.8 skeptics per the brief's prompts. For each: decide `holds_up`, then write the
> **missing regression seam** the brief specifies. Don't commit until the seam is green.

**Lane A — transport hang (run LOCALLY, with the CLI):**
> Read the brief. **Use the `diagnosing-bugs` skill** on the transport 2-hour hang (§4.2). Build the
> Phase-1 red-capable loop it describes (fake unkillable child + orphaned-PID assertion) and **show it
> going red before any hypothesis.** Only then propose the `Popen` + tree-kill fix, and have Opus
> skeptics refute it (killpg/setsid, taskkill, PID-reuse race, PIPE deadlock) at Phase 5.

**Optional — auto-orientation:** `diagnosing-bugs` reads a root `CONTEXT.md` on entry if one exists;
there isn't one yet. If you want the skill to self-orient on the runtime modules, add a short
`CONTEXT.md` mapping `runner/` — separate from this brief (which is the *plan*, not the module map).
