# 02 — Define the measurement protocol and establish the baseline

Status: ready-for-human
Blocked by: 01
Candidate: none (the protocol must not depend on any candidate)
Surface: development session
Effort: claude-workflow-efficiency
PRD: ../PRD.md

## Problem

No pilot in this effort can produce a defensible number yet. The repository has no protocol that measures
a task the same way twice, and no baseline for any task.

Two traps sit in the way. The first is adopting a candidate measurement tool and then measuring candidates
with it, which makes the instrument unfalsifiable. The second is recording an absent measurement as zero,
which turns a gap into a saving.

## Outcome

A pinned protocol, plus baseline evidence produced by running it. Later pilots compare against this
baseline and change nothing about how it was measured.

## Scope

Author the protocol. Run it on the defined task set twice. Record the result, including what could not be
measured. No candidate is installed and no candidate is required.

Measurement uses built-in reporting and the CLI session transcript evidence for this project. CodeBurn
adoption is explicitly not a prerequisite. Ticket 03 may later improve the instrument. If it does, the
baseline is re-expressed under the better instrument rather than the protocol being rewritten.

## Inputs

- `evidence/01-environment-record.md` from ticket 01, for version, settings and the startup footprint.
- Existing test and report fixtures, and bounded engineering tasks reproducible from them.
- The CLI session transcript directory for this project, as raw per-call evidence.
- The measurement requirements in the PRD.

## Deliverables

- `evidence/02-measurement-protocol.md`, the pinned protocol.
- `evidence/02-baseline.md`, the recorded baseline with per-run and per-task figures.
- An explicit unresolved list naming every required metric the protocol could not obtain, and why.

## Acceptance criteria

- [ ] Pins the repository revision, the task fixtures, and the model and effort settings for every arm.
- [ ] Defines the recording method, naming its source and its limits for each metric class.
- [ ] Defines a correctness check per task, so a cheaper run that fails the task is visibly a failure.
- [ ] Defines the repeat strategy, and states what two runs can and cannot establish.
- [ ] Defines three scenario classes: representative engineering work, retrieval of compressed or
      summarised output, and cross-session recall after a context reset.
- [ ] Defines arm isolation, including how cache state and any accumulated memory are prevented from
      carrying between arms, and how isolation is confirmed rather than assumed.
- [ ] Records, for each task, the token classes, wall-clock time, model and tool calls, repeated reads and
      context resets named in the PRD measurement list.
- [ ] Records subagent, observer, retry and recall usage as part of the task total, not separately from it.
- [ ] Records every unobtainable metric as unresolved with a reason. No metric is recorded as zero by
      default.
- [ ] States in the baseline document that two runs verify the recording method and expose variability,
      and that they do not establish a savings claim.
- [ ] Sets no numerical acceptance target that the baseline evidence does not support.
- [ ] Runs no proposal assessment, no assessor invocation, and no official scoring.

## Verification evidence

The two runs are recorded separately, with their variance stated per metric. The transcript evidence for
at least one task is reconciled against the built-in report, and any disagreement between the two sources
is recorded as a limit of the instrument.

## Cost and data handling

This ticket spends subscription usage by design, because it runs tasks. The spend is bounded by the task
set, which stays small. No separately metered service is used and none is required. Tasks operate on
fixtures and isolated copies, never on immutable source evidence.

## Collisions

The protocol runs on the environment as ticket 01 found it. Any skill, hook or MCP server that affects the
baseline is named in the protocol, so a later pilot cannot silently change it.

## Rollback

Protocol and baseline are documents. Any scratch copies created for task isolation are removed on close.
The repository working tree is left unchanged by the runs themselves.

## Non-goals

- Installing or evaluating CodeBurn, or any other candidate.
- Producing a savings percentage, or any projection beyond the measured tasks.
- Benchmarking a proposal assessment, a freeze, or a report comparison.
- Setting acceptance thresholds for the pilots before the baseline exists.

## Comments
