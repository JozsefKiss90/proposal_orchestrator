# 02 — Rubric grading resumes from the response checkpoint, bound to content

Status: needs-triage
Type: task
Blocked by: 01
Source: `discovery/architecture-review-harness-2026-11-03.html`, candidate C. Grill skipped by the
operator on 2026-11-03; every recommendation below was accepted as the decision.
Findings: F6 (known bug) · E5f · not on the DN path

> `needs-triage` until the Step 3 scope cut admits it; then `ready-for-agent`.
> Blocked by 01 because both change how the response checkpoint is driven (discard, redraw, replay
> marking). Landing 01 first means this ticket inherits those rules instead of re-implementing them.

## What to build

A resumed rubric grading run grades exactly the section content the interrupted run graded, or it
refuses and names what moved. Today resume is keyed by a directory name: on 2026-08-10 a checkpoint
"resumed" a cell whose section had been deleted and rewritten. After this ticket, rubric grading
resumes the way blind assessment does. Every raw draw is checkpointed as it arrives. A resume replays
the draws through the same code, and the cells and the claim verdict cache are rebuilt in memory. The
binding includes a content hash of the graded sections. The pickle checkpoint is gone.

## Decisions (operator accepted recommendations, 2026-11-03)

- **Replace, don't patch.** The pickle checkpoint (completed cells + verdict cache) is removed. The
  response checkpoint is the one resume module in the harness.
- **Binding.** It holds:
  - the candidate hash over the section artifacts in the grid (the same formatting-invariant hash
    blind assessment uses);
  - the judge pin, the rubric-set fingerprint, the profile version when a profile is given, the pack
    token budget, the span budget fraction, and n.
  A changed, added or removed section changes the candidate hash, so the resume is refused with every
  moved field named.
- **Additive binding change.** The rubric fields join the existing binding with empty defaults.
  Checkpoints already written by blind assessment, including DN runs, must still open and resume
  unchanged.
- **CLI.** A new run writes a new numbered checkpoint. Resuming names an existing checkpoint
  explicitly. Opening an existing file without asking to resume is refused, as in blind assessment.
  The `--fresh` flag and the fixed default pickle path go.
- **Daily budget stop.** It still stops cleanly between cells. The next run resumes by replay without
  spending the stopped run's draws again.
- **Report.** The rubric report and the E4 rubric baseline carry the candidate hash and the
  replayed / live draw counts. This is additive.
- **Stale pickle.** The existing `harness/rubric_reports/rubric_run_checkpoint.pkl` is not migrated.
  It is already known to be stale. The operator deletes it.

## Acceptance criteria

Failing tests first:

- [ ] A section's content is replaced after a partial run, then resumed: the resume is refused, naming the candidate hash as checkpoint vs current.
- [ ] A section is added or removed between runs: the resume is refused in the same way.
- [ ] An interrupted run, resumed: every already-drawn response is replayed (zero live draws for them) and the finished grid equals an uninterrupted run's.
- [ ] A daily budget stop, then a resume: the run continues from the first undrawn call.
- [ ] A blind-assessment checkpoint header written before this change still opens, resumes, and reports no binding differences.
- [ ] No pickle is written anywhere by rubric grading.

Then:

- [ ] The rubric report and frozen rubric baseline carry the candidate hash and replayed / live draw counts; a baseline frozen before this change still loads.
- [ ] `--plan-only` budget accounting is unchanged.
- [ ] The module docstring and `harness/HARNESS.md` describe the new resume rule.
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md`.
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/02-rubric-grading-resumes-from-response-checkpoint.md   Base commit: <sha at start>
Read first: CLAUDE.md §16–17, CONTEXT-MAP.md (+ harness/CONTEXT.md), docs/agents/*.md,
            plans/overhaul/BASELINE.md, issue 01 (landed)
Seam: the response checkpoint binding (additive fields) — rubric grading's resume moves onto it
Do not touch: blind-assessment binding semantics or existing checkpoint format, §17 call graph,
      runner/, Tier 1–3 docs, the claim verdict cache's content-keyed rule
Tests first: the six listed above (tdd)
Size: small–medium; removes more than it adds
Admission rule 5: does not apply (no blind_*/evidence_*/execution_receipt/anonymisation_*/transport changes);
      run the PE-09 acceptance lane anyway if the response checkpoint module changes beyond the additive fields
```
