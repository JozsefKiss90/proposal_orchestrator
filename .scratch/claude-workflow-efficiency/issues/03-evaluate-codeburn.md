# 03 — Evaluate CodeBurn against the measurement evidence

Status: ready-for-human
Blocked by: 02
Candidate: C04 CodeBurn (https://github.com/getagentseal/codeburn) — pin an exact release or commit before install
Surface: development session
Effort: claude-workflow-efficiency
PRD: ../PRD.md

## Problem

Ticket 02 measures with built-in reporting and transcript evidence. That may be coarse, laborious, or
silent on some required metric. CodeBurn claims local usage analytics over the same transcripts.

The claim needs checking against something, and the something already exists. Two risks matter more than
convenience. A reporting tool can disagree with the transcript it reads. A reporting tool can present
API-equivalent dollars that neither match a subscription invoice nor reconstruct the provider's allowance
formula.

## Outcome

A decision of adopt, defer or reject, resting on agreement or disagreement with evidence the repository
already holds.

## Scope

Install the pinned candidate for the development session. Run its reporting over transcripts for tasks
ticket 02 already measured. Compare. Decide. Record.

The comparison reuses ticket 02 tasks. No new benchmark task is created for this ticket.

## Inputs

- `evidence/02-measurement-protocol.md` and `evidence/02-baseline.md`.
- The CLI session transcript evidence for the tasks already measured.
- `evidence/01-environment-record.md`, for the Windows and WSL finding.
- Upstream installation instructions, license, dependencies and authentication at the pinned release.

## Deliverables

- `evidence/03-codeburn-assessment.md`, holding the cross-check table and the decision.
- An uninstall record, applied if the decision is defer or reject.

## Acceptance criteria

- [ ] Records the pinned release or commit, license, dependencies and authentication requirement.
- [ ] Runs on the recorded environment, with native Windows or WSL support stated as observed, not assumed.
- [ ] Cross-checks its per-task output against built-in reporting and against transcript evidence, with
      disagreements quantified rather than described.
- [ ] States coverage: which required metric classes it reports, and which it does not.
- [ ] Separates any API-equivalent dollar estimate from subscription usage and from allowance consumption,
      and states that the estimate is neither of those.
- [ ] Records its own overhead: install footprint, run time, and any usage it adds to a session.
- [ ] Records observed network behaviour, including any endpoint contacted and any telemetry setting.
- [ ] Determines whether the CLI alone suffices, so the optional MCP server need not be registered.
- [ ] Tests the failure case of a missing or unreadable transcript, and records the behaviour.
- [ ] Closes with adopt, defer or reject, with the evidence for the decision stated.
- [ ] Confirms in writing that tickets 04, 05, 06 and 07 remain runnable under the ticket 02 method if the
      decision is defer or reject.

## Verification evidence

The cross-check table, showing per-task figures from all three sources side by side. A decision without
that table is not a close.

## Cost and data handling

The candidate is free to install. Any usage its optional MCP server or UI adds is counted and reported.
No separately metered service is introduced. Transcripts contain task content, so no transcript excerpt
naming confidential proposal or assessment material is copied into the deliverable.

## Collisions

Registering the optional MCP server adds a tool surface to every session, on top of the servers ticket 01
recorded. Prefer the CLI. If the MCP server is registered, record the added tool footprint.

## Rollback

Uninstall the candidate and remove any MCP registration. Ticket 02 reporting continues unchanged, because
it never depended on this candidate.

## Non-goals

- Evaluating ccusage (C18) or any other alternative instrument.
- Re-running the ticket 02 tasks to produce a new baseline.
- Adopting the candidate because its dashboard reports tokens saved.
- Blocking any other pilot on this decision.

## Comments
