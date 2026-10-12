# 04 — Pilot Headroom on the development-session surface

Status: ready-for-human
Blocked by: 02
Candidate: C01 Headroom (https://github.com/headroomlabs-ai/headroom) — pin an exact release or commit before install
Surface: development session only
Effort: claude-workflow-efficiency
PRD: ../PRD.md

## Problem

Large reads and large outputs are a named source of waste. Headroom offers context compression with
retrieval of the originals, and ships in several forms: library, proxy, wrapper and MCP server.

The proxy and wrapper forms are the concern. The orchestrator transport invokes the local `claude` CLI as
a subprocess. A wrapper or proxy that intercepts that path would alter what the pipeline sends, and the
pipeline depends on declared inputs and byte-equal replay checks.

Whether the candidate actually reaches that path is unverified. Treat it as a risk requiring evidence, not
as a finding. A wrapper confined to the operator's interactive shell may never touch a pipeline
invocation. The pilot decides which is true here.

A second, smaller risk is duplication. The candidate's wrapper can install Serena, and a user-level
`serena` server is already configured.

## Outcome

A measured comparison on the development session surface, plus a recorded data-flow and fence finding, plus
a decision of adopt, defer or reject.

## Scope

Install the pinned candidate for the development session. Establish the fence before measuring. Run the
ticket 02 arms. Test retrieval and failure behaviour. Decide.

The fence is a precondition of the pilot, not an outcome of it. If the candidate cannot be confined to the
development session, the pilot stops and records that as the finding.

## Inputs

- `evidence/02-measurement-protocol.md` and `evidence/02-baseline.md`.
- `evidence/01-environment-record.md`, for inherited settings, hooks and the existing `serena` registration.
- `CLAUDE.md` section 17, for the runtime contracts the fence protects.
- Upstream documentation at the pinned release, covering transport, cache behaviour, exact-data exclusions
  and optional features.

## Deliverables

- `evidence/04-headroom-pilot.md`, holding the fence finding, the measured comparison, the failure-mode
  results, the data-flow record and the decision.
- An uninstall record, applied if the decision is defer or reject.

## Acceptance criteria

- [ ] Records the pinned release or commit, the installed form, license, dependencies and authentication.
- [ ] States the fence explicitly: the candidate may not interpose on any orchestrator runtime invocation.
- [ ] Verifies the fence by evidence, naming what was checked: inherited settings, hooks, environment
      variables, wrapper or shim placement on the executable path, and whether a pipeline invocation
      resolves to the wrapped or the unwrapped CLI.
- [ ] Records whether runtime contract and replay incompatibility is real here, with the observation that
      supports the answer. An unverified incompatibility is recorded as a risk, not as a conclusion.
- [ ] Records every endpoint contacted, every optional cloud feature, every model download, and every
      telemetry setting, with its on or off state.
- [ ] Confirms no duplicate Serena registration results, and records the resolution if the candidate
      attempts one.
- [ ] Verifies that retrieval returns the original content, by comparing retrieved content against the
      source byte for byte on at least one case.
- [ ] Tests three failure modes and records the behaviour of each: compression dropping a detail the task
      needed, empty retrieval, and endpoint failure.
- [ ] Reports complete task cost against the baseline, including retrieval calls and any retry, with
      correctness stated per task.
- [ ] States whether a cheaper run lost evidence, changed an exact source value, or required operator
      rework. Any of those fails the quality requirement regardless of the usage result.
- [ ] Closes with adopt, defer or reject, naming the surface the decision applies to.

## Verification evidence

The byte-for-byte retrieval comparison, the fence check, and the per-task cost and correctness table
against the ticket 02 baseline.

## Cost and data handling

Compression and indexing may run locally while the model endpoint remains remote. Local processing does
not make the endpoint private. The deliverable records which content left the machine and to where.

No confidential proposal content, verbatim extract, assessment material or evidence-pack anchor is used as
pilot input. Pilot input is fixture and code content only.

## Collisions

The existing user-level `serena` server, the three project MCP servers, and any hook ticket 01 recorded.
If the candidate adds a hook, record whether it collides with an existing one.

## Rollback

Uninstall the candidate, remove any wrapper or shim from the executable path, remove any MCP registration
and any hook, and restore the environment variables ticket 01 recorded. Confirm an unwrapped CLI
invocation afterwards.

## Non-goals

- Comparing against Context Mode (C10). The pilot records whether its result justifies opening that
  comparison.
- Any change to the orchestrator runtime transport, declared inputs, or replay checks.
- Enabling the candidate's memory or learning features. Memory is ticket 07, and no candidate may
  reinterpret constitutional instructions.
- Compressing immutable source evidence for any purpose.

## Comments
