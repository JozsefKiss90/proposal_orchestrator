# 06 — Evaluate Anthropic code-review against the existing reviewer

Status: ready-for-human
Blocked by: 01
Candidate: C03 Anthropic code-review (https://github.com/anthropics/claude-code/tree/main/plugins/code-review) — pin an exact commit before install
Surface: development session, repository-local plugin
Effort: claude-workflow-efficiency
PRD: ../PRD.md

## Problem

Review fan-out is a named source of waste. A multi-agent reviewer with confidence filtering may find more
than the single existing reviewer, and it will certainly cost more than one agent.

A `code-review` skill already loads from the Matt Pocock set, under that exact name. Adding a plugin that
claims the same verb risks a collision that decides which reviewer runs by accident.

The measurement problem here differs from the other pilots. The question is finding quality, not task
usage, and previously reviewed diffs are not exhaustive ground truth. A reviewer that reports something no
earlier review mentioned may be right.

## Outcome

A side-by-side comparison on fixed historical cases against an adjudicated reference, with fan-out usage
counted, and a decision on which reviewer to reach for.

## Scope

This ticket owns the verification of its own review-specific measurement method. It may reuse the ticket 02
protocol for the usage half when that protocol exists. It does not wait for the engineering baseline, and
it does not depend on CodeBurn being adopted.

Install the pinned plugin. Select fixed historical cases. Build the adjudicated reference. Run both
reviewers. Compare. Decide.

## Inputs

- `evidence/01-environment-record.md`, for the loaded `code-review` skill and the invocation names in use.
- Fixed historical commits from this repository, selected and pinned by revision.
- Any earlier review record for those commits, as reference input rather than as the reference itself.
- The existing `code-review` skill, as the comparison arm.

## Deliverables

- `evidence/06-code-review-assessment.md`, holding the measurement method, the adjudicated reference, the
  comparison and the decision.
- An uninstall record, applied if the decision is defer or reject.

## Acceptance criteria

- [ ] Records the pinned commit, license, dependencies and authentication.
- [ ] Confirms the plugin supports the chosen invocation workflow before any comparison is attempted.
- [ ] Pins the historical cases by revision, and states why each was selected.
- [ ] Defines and records the adjudicated reference, stating explicitly that previously reviewed diffs are
      not exhaustive ground truth, and naming who adjudicated each disputed finding.
- [ ] Defines the review-specific measurement method, and verifies it by having a second pass over one case
      reproduce the same classification.
- [ ] Reports per arm: actionable findings, true positives, false positives, duplicate findings, and
      findings missed against the adjudicated reference.
- [ ] Reports the full agent fan-out usage per arm, counting every subagent and retry as part of the review
      cost.
- [ ] Records command-name collisions with the existing skill, and how the collision was resolved during the
      pilot.
- [ ] Records proactive trigger behaviour, including any case where the plugin invoked itself unasked.
- [ ] Confirms the plugin posted nothing automatically, and that no result gated a run.
- [ ] Closes with a decision stating which reviewer to reach for, selected by the kind of changed behaviour.

## Verification evidence

The per-arm finding table against the adjudicated reference, with the fan-out usage figure beside it. The
reproduced classification pass is recorded as the method's own check.

## Cost and data handling

Subscription usage only, and the fan-out makes it the heaviest usage per task in this effort. The cost is
bounded by the number of pinned cases, which stays small. Review input is repository code and diffs. No
confidential proposal content and no assessment material is used.

## Collisions

The loaded `code-review` skill holds the same name. Record whether both are reachable, which one an
unqualified invocation resolves to, and whether the plugin triggers without being named.

## Rollback

Uninstall the plugin and remove its registration. The existing `code-review` skill is left untouched, so it
remains the reviewer by default.

## Non-goals

- Comparing against the PR Review Toolkit (C14) or any other reviewer outside this effort.
- Automatic posting of review results anywhere.
- Making any review finding a runtime gate, or letting one fail-close a run. The reviewer stays advisory.
- Reviewing confidential proposal content or assessment material.

## Comments
