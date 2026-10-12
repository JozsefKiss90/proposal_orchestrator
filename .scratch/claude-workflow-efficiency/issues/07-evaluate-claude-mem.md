# 07 — Evaluate Claude-Mem, with isolation as the first gate

Status: ready-for-human
Blocked by: 02
Candidate: C05 Claude-Mem (https://github.com/thedotmack/claude-mem) — pin an exact release or commit before install
Surface: development session only, never the blind assessor
Effort: claude-workflow-efficiency
PRD: ../PRD.md

## Problem

Session reconstruction after a context reset is a named source of waste. Claude-Mem records observations,
summarises them with model calls, and retrieves them later.

Automatic retrieval is the problem. A blind assessor must never receive an Evaluation Summary Report, a
prior score, a comparison, revision advice, or any memory derived from them. The assessor is isolated by
three things together: `--tools ""`, `--strict-mcp-config`, and a working directory outside the
repository. The transport source records that operator MCP servers survive `--tools ""` on its own, so
only the second flag removes them.

That leaves routes a tool list cannot close. A startup hook is not a tool. A shared store on disk is not a
tool. An inherited launch setting is not a tool. Directory separation closes none of them by itself.

So isolation is a gate, tested before the candidate is trusted with anything real. Failing it early is
cheap. Failing it late means an assessment is contaminated.

## Outcome

An isolation verdict first, from canary probes. Then, only if the gate passes, a measured development-recall
comparison and a decision of adopt, defer or reject.

## Scope

Two stages, strictly ordered.

**Stage one, the gate.** Install the pinned candidate in a pinned configuration. Seed synthetic canaries
that represent prohibited material. Probe an assessor-shaped session for every retrieval route. Record the
verdict.

A failed check rejects the configuration under test, not necessarily the candidate. Containment and a
retest are permitted. If no configuration passes, the candidate is rejected and stage two never runs.

**Stage two, the pilot.** Run the ticket 02 cross-session recall arm. Measure. Decide.

## Inputs

- `evidence/02-measurement-protocol.md` and `evidence/02-baseline.md`, for the recall scenario.
- `evidence/01-environment-record.md`, for hooks, user-level servers, inherited settings, and the recorded
  assessor isolation mechanism.
- Synthetic canary content, authored for this ticket. Distinctive, traceable, and representing the shape of
  prohibited material without being any of it.
- The existing `mcpvault` and `smart-connections` integrations, as the comparison arm.
- `CLAUDE.md` sections 9.3, 9.4 and 13.5, which keep memory subordinate to documented state.

## Deliverables

- `evidence/07-claude-mem-isolation.md`, the gate verdict with each probed route and its result.
- `evidence/07-claude-mem-pilot.md`, the recall comparison and the decision. Written only if the gate passes.
- An uninstall record, applied if the gate fails or the decision is defer or reject.

## Acceptance criteria

Stage one, the gate:

- [ ] Records the pinned release or commit, the pinned configuration, license, dependencies and authentication.
- [ ] Seeds synthetic canaries only. No Evaluation Summary Report, no real score, no real comparison and no
      real proposal content is admitted to the candidate at any point.
- [ ] Probes, and records a result for, every retrieval route: direct tool access, the search index, startup
      hooks, shared on-disk stores, injected prompt content, and inherited launch settings.
- [ ] Probes an assessor-shaped session carrying `--tools ""` without `--strict-mcp-config`, and records
      whether a canary reaches it. This is the route the transport source already flags.
- [ ] Probes the real assessor configuration, with both flags and the out-of-repository working directory,
      and records whether any canary reaches it by any route.
- [ ] States that directory separation alone was not accepted as evidence of isolation.
- [ ] On any canary arrival, rejects the tested configuration and records the route. Containment and a
      retest are permitted, and each retest is recorded as its own verdict.
- [ ] Runs no proposal assessment, no assessor invocation against real material, and no official scoring.

Stage two, the pilot, only after the gate passes:

- [ ] Reports the cross-session recall arm against the baseline, with correctness per task.
- [ ] Counts observer calls, summary calls and injection overhead as part of the task cost, not beside it.
- [ ] Tests stale memory: a memory that contradicts current documented state. Records whether the session
      preferred the memory, and whether documented state governed as section 9.3 requires.
- [ ] Compares against `mcpvault` and `smart-connections` on the same recall arm, and states whether the
      candidate addresses a gap those leave.
- [ ] Records that no memory became a durable decision record, and that the decision log and Tier 4 remain
      the only authority for durable decisions.
- [ ] Closes with adopt, defer or reject, naming the configuration the decision applies to.

## Verification evidence

The route-by-route gate table, including the deliberately weakened assessor-shaped probe and its result.
Then the recall comparison table with observer and injection overhead included in the task total.

## Cost and data handling

Observer and summary calls are model calls, so the candidate spends usage continuously rather than per
task. Record that spend. If the candidate offers a hosted option, record it and leave it off. Local
storage and cloud sync are separate decisions, and this ticket authorizes neither.

Canaries are synthetic by construction. Keep development recall separate from any assessment execution.
No immutable source evidence is admitted to the candidate.

## Collisions

Two existing knowledge integrations already index this repository, `mcpvault` and `smart-connections`.
Record whether the candidate indexes the same content a third time, and what that costs at startup. Record
any hook collision with those recorded in ticket 01.

## Rollback

Uninstall the candidate, remove every hook and MCP registration, and delete its store and index. Confirm
afterwards that an assessor-shaped session reaches no residual store. Restore the inherited settings ticket
01 recorded.

## Non-goals

- Admitting any real Evaluation Summary Report, score, comparison or revision advice to the candidate.
- Running a new proposal assessment, a freeze, or a report comparison.
- Enabling a hosted memory service or cloud sync.
- Letting a memory override documented Tier 3 or Tier 4 state, or substitute for the decision log.
- Treating a passed gate as permanent. The verdict binds the pinned configuration only.

## Comments
