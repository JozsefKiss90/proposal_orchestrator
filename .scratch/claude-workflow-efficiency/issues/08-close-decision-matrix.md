# 08 — Close the decision matrix and verify the selected configuration

Status: ready-for-human
Blocked by: 03, 04, 05, 06, 07
Candidate: whichever of C01 to C05 ticket 03 to 07 decided to adopt
Surface: development session, repository-local configuration
Effort: claude-workflow-efficiency
PRD: ../PRD.md

## Problem

Five pilots produce five decisions in isolation. Nothing in them tests the combination.

Adopted tools can interact. Two of them may index the same repository, add startup cost twice, and present
the same content to a session from two sources. A compression layer and a memory layer can disagree about
what a session already knows. Each pilot measured one arm against a baseline, so none of them measured the
sum.

Two loose ends also need closing. Rejected candidates may still be installed. And the effort needs one
record of why each of the five decisions landed where it did.

## Outcome

One decision record for all five candidates, a verified configuration for whatever was adopted, and a clean
machine with nothing rejected left installed.

## Scope

A ticket is resolved for this ticket's purpose when it reached adopt, defer or reject. All three are
resolved outcomes. A reject is not a blocker.

Collect the five decisions. If anything was adopted, install the selected combination together and test it.
Document the configuration and its uninstall path. Remove rejected installations.

If nothing was adopted, this ticket still closes. It records five decisions and a clean machine.

## Inputs

- `evidence/03-codeburn-assessment.md`.
- `evidence/04-headroom-pilot.md`.
- `evidence/05-ponytail-pilot.md`.
- `evidence/06-code-review-assessment.md`.
- `evidence/07-claude-mem-isolation.md` and, if written, `evidence/07-claude-mem-pilot.md`.
- `evidence/02-baseline.md`, as the comparison for the combined configuration.

## Deliverables

- `evidence/08-decision-matrix.md`, the five decisions with their evidence.
- `evidence/08-selected-configuration.md`, the adopted configuration, its installation path, its uninstall
  path and its rollback. Written even when the adopted set is empty.
- An updated PRD candidate matrix, recording the decision reached for each candidate.

## Acceptance criteria

- [ ] Records a resolved outcome for all five candidates, with the evidence file for each, and treats adopt,
      defer and reject alike as resolved.
- [ ] Tests the selected combination together, not one tool at a time.
- [ ] Reports duplicate context in the combined configuration: content a session receives twice, from two
      sources.
- [ ] Reports interactions observed between adopted tools, including any disagreement about session state.
- [ ] Reports total overhead of the combination against the ticket 02 baseline, including startup cost and
      any continuous observer spend.
- [ ] Reports correctness for the combined configuration on at least one task per scenario class.
- [ ] Documents the chosen configuration precisely enough to reproduce on another machine, with pinned
      versions.
- [ ] Documents the installation and uninstallation path for every adopted tool, and verifies the
      uninstallation path by running it at least once.
- [ ] Confirms every rejected or deferred candidate is uninstalled, with every hook, MCP registration, store
      and index removed.
- [ ] Confirms no adopted tool became a runtime gate, a second status authority, or an authority over
      documented state.
- [ ] Confirms no constitutional text was amended by this effort.
- [ ] States that tooling adoption created no dependency on any historical-validation ticket, and closed
      none.

## Verification evidence

The combined-configuration table against the baseline, with duplicate context and startup cost shown. The
uninstall path is evidenced by having been run, not by having been written.

## Cost and data handling

Combined testing spends subscription usage on a small number of tasks. Any continuous observer spend from an
adopted memory tool is reported as a standing cost, separately from per-task cost. No separately metered
service is adopted. Any remaining optional cloud feature is recorded with its state.

## Collisions

This ticket is where collisions are resolved rather than only recorded. Duplicate indexing, duplicate
context, invocation-name conflicts and hook ordering are each either resolved in the configuration or
recorded as an accepted cost.

## Rollback

The whole effort has one rollback: uninstall everything adopted, following the verified uninstall paths, and
restore the environment ticket 01 recorded. The planning artifacts remain as the record.

## Non-goals

- Reopening a pilot decision. A decision is revisited by a new ticket, not by this one.
- Adopting a candidate outside C01 to C05.
- Promoting any adopted tool into the orchestrator runtime, the harness gates, or the assessor path.
- Making a historical-validation ticket depend on this effort, or closing one here.

## Comments
