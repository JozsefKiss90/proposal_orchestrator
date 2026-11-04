# Decision record — candidate E (retire cli-prompt mode / close the §17 TAPM banner)

Date: 2026-11-04 · Decided by: operator · HEAD `5ba39e2d`
Source: `architecture-review-runtime-2026-11-03.html`, candidate E · plan §6 "§17 TAPM banner"

## Decision

**Not yet.** The §17 "MIGRATION IN PROGRESS" banner and the pending Backend-Migration amendment record stay
as they are. No ticket for E. Ticket 09 keeps both prompt modes.

## Evidence (corrects the report)

The report and the handoff said "all 24 catalog entries that declare a mode declare `tapm`" and called
cli-prompt dormant. At HEAD:

- `skill_catalog.yaml` has **27** entries: 24 declare `execution_mode: "tapm"`, and **3 declare none**:
  `milestone-consistency-check`, `budget-interface-validation`, `decision-log-update`.
- `run_skill` defaults a missing mode to `cli-prompt` (`runner/skill_runtime.py:1522`).
- All three are bound in `manifest.compile.yaml` and agent specs. `budget-interface-validation` runs in
  n07, in both the pre-gate and primary loops, at the budget gate (gate_09).

So cli-prompt is a live production path, and "a missing mode fails closed" would break n07 today.

## What would have to be true to revisit

1. The three entries declare `execution_mode: "tapm"`, and a real run shows them working on TAPM
   (n07's budget gate included). This is a catalog change, and it is the operator's call.
2. Benchmark harness and runtime tests that rely on the cli-prompt default are migrated or deleted.
3. The operator amends `CLAUDE.md` §17 and closes the Backend-Migration amendment record (§14.5: no
   agent-made amendments). Only then is a removal ticket written.
