# 05 — Pilot Ponytail while preserving required validation

Status: ready-for-human
Blocked by: 02
Candidate: C02 Ponytail (https://github.com/dietrichgebert/ponytail) — pin an exact release or commit before install
Surface: development session, repository-local skills
Effort: claude-workflow-efficiency
PRD: ../PRD.md

## Problem

Sessions generate code and prose beyond what a task required. Ponytail favours reuse, standard features,
smaller correct implementations and focused review.

Smaller is only better when it stays correct. This repository has validation that looks like excess from
the outside: deterministic gate predicates, fail-closed paths, byte-equal replay checks, declared status
categories, and traceability from a claim to its tier. A tool that shrinks output by skipping one of those
produces a cheaper run and a worse repository.

The constitution already settles the authority question. A skill is a bounded execution aid under section
10.2, and silent gate weakening is prohibited under section 13.7. The pilot measures whether the candidate
behaves accordingly.

## Outcome

A measured comparison against the existing workflow, including one case designed to catch the candidate
omitting required validation, and a decision of adopt, defer or reject.

## Scope

Install the pinned candidate for the development session. Run bounded tasks in two arms: the existing
workflow and skills, and the candidate. Include the negative case. Measure both output size and
correctness. Decide.

## Inputs

- `evidence/02-measurement-protocol.md` and `evidence/02-baseline.md`.
- `evidence/01-environment-record.md`, for the skills that already load and the invocation names in use.
- `CLAUDE.md` sections 10.2, 12.2 and 13.7, as the constraints the candidate may not reinterpret.
- The existing skill set, as the comparison arm.

## Deliverables

- `evidence/05-ponytail-pilot.md`, holding the two-arm comparison, the negative-case result and the
  decision.
- An uninstall record, applied if the decision is defer or reject.

## Acceptance criteria

- [ ] Records the pinned release or commit, license, dependencies and authentication.
- [ ] Runs each bounded task in both arms, with the required test result recorded per arm.
- [ ] Reports output size and complete task usage per arm, including any review or question turns the
      candidate adds.
- [ ] Includes a negative case: a task whose smallest plausible implementation omits a required validation
      step. Records whether the candidate omitted it, and whether it argued for omitting it.
- [ ] Treats an omission the operator had to catch as a pilot failure, whatever the usage result.
- [ ] Records whether any candidate output proposed changing an architectural constraint, a gate, a status
      category, or constitutional text. Any such proposal is reported, never applied.
- [ ] States the overlap with the existing skills by name, and whether the candidate addresses a gap those
      skills leave.
- [ ] Records operator rework per arm, as part of the task cost.
- [ ] Closes with adopt, defer or reject, naming which tasks the decision covers.

## Verification evidence

The two-arm table, with the required test result beside the usage figure for every task. The negative case
is reported with the candidate's own output quoted, so the omission or its absence is visible.

## Cost and data handling

Subscription usage only. No separately metered service. Pilot tasks run on fixtures and code, never on
confidential proposal content or immutable source evidence.

## Collisions

Invocation-name collision with the existing skill set is the live risk, because several Matt Pocock skills
already occupy review, test and implementation verbs. Record every collision ticket 01 predicted and every
new one observed.

## Rollback

Uninstall the candidate and remove any skill or plugin registration. No repository skill file is modified
by this pilot, so the existing workflow needs no restoration.

## Non-goals

- Deleting or rewriting an existing skill to reduce overlap.
- Any amendment to constitutional text, or any cleanup justified as removing duplication from it.
- Weakening a gate, a predicate, or a required test to make a smaller implementation pass.
- Adopting the candidate on the basis of output size alone.

## Comments
