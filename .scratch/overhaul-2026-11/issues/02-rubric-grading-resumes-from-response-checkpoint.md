# 02 — Rubric grading resumes from the response checkpoint, bound to content

Status: done
Type: task
Blocked by: 01, 03
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
- **Stale pickle.** No checkpoint file exists in this tree (checked 2026-11-05): `harness/rubric_reports/` holds only `.gitkeep`, and the pickle path is gitignored, so it was never committed. The 2026-08-10 checkpoint lived in another working tree. There is nothing to migrate or delete.

## Acceptance criteria

Failing tests first:

- [x] A section's content is replaced after a partial run, then resumed: the resume is refused, naming the candidate hash as checkpoint vs current.
- [x] A section is added or removed between runs: the resume is refused in the same way.
- [x] An interrupted run, resumed: every already-drawn response is replayed (zero live draws for them) and the finished grid equals an uninterrupted run's.
- [x] A daily budget stop, then a resume: the run continues from the first undrawn call.
- [x] A blind-assessment checkpoint header written before this change still opens, resumes, and reports no binding differences.
- [x] No pickle is written anywhere by rubric grading.

Then:

- [x] The rubric report and frozen rubric baseline carry the candidate hash and replayed / live draw counts; a baseline frozen before this change still loads.
- [x] `--plan-only` budget accounting is unchanged.
- [x] The module docstring and `harness/HARNESS.md` describe the new resume rule.
- [x] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md`.
- [x] `code-review` run since the base commit, with no gaps on the spec axis.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/02-rubric-grading-resumes-from-response-checkpoint.md   Base commit: 69995f1e
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

## Comments

- Deferred at Step 3 (2026-11-06): rubric lane, off the V14/V16 path (W03 §4). Still blocked by 01.
- Wave 2c (2026-11-06): also after 03, because both edit rubric grading (collision edge, not a functional dependency).
- 2026-11-11, base 69995f1e (branch `ticket/02-rubric-resume-checkpoint`): targeted 40 modules (every test module importing `harness.response_cache`, `harness.rubric`, `harness.regression` or `harness.commands`): 1,902 passed, 1 failed, 6 skipped; the failure is the BASELINE §5 id `tests/test_demo_candidate_blind_baseline.py::TestTheReportsNumbersAreTheArtifactsOwn::test_the_leakage_scan_file_count_is_re_derivable`. PE-09 acceptance lane run from the worktree (the binding's header form now filters empty rubric fields): GREEN, 3,662 passed, 0 failed, 17 declared exclusions. Review (standards + spec axes): glossary wording fixed (draw, short form), shared `next_checkpoint_path` reused, plan note left unchanged; no open spec gap. Judgement calls for the operator: the checkpoint is kept after a completed run (blind assessment's rule; the pickle was deleted); the judge pin is bound in the existing `assessor_pin` field; the profile version is always bound because the command always loads a profile bundle (the default one when `--profile` is absent); the report renders a `candidate: ... draws: N live, M replayed` header line only when it carries a candidate hash; the two retired pickle lines left `.gitignore`. Full suite not run.
- 2026-11-11, operator: confirmed (1) the checkpoint is kept after a completed run; (2) the judge pin is bound in `assessor_pin`; (4) the rubric report's new header line, only with a candidate hash; (5) the separate `.harness/rubric_checkpoints/` folder; (6) the two pickle lines removed from `.gitignore`. Still open with the operator: (3) the profile version is always bound, and (7) `plans/harness_plan/tickets_eval_harness.md` line 200 still describes `--fresh` and the pickle.
- 2026-11-11, operator: (3) accepted: the command always binds the loaded profile's version (the default profile when `--profile` is absent); only a direct `run_grading` call without one binds it empty. (7) accepted: `plans/harness_plan/tickets_eval_harness.md` keeps its ticked line as history, with a superseded note under it.
- 2026-11-11, closed: merged by the operator as `67224ced`. Suite at `7697524c`: 43 failed, 9,689 passed, 87 skipped (`suite-o3.txt`). 42 failed node ids equal BASELINE §5; the 43rd, `tests/test_evidence_protocol_scaffold.py::test_evidence_v2_tree_is_itself_clean`, was caused by the agent's R11 `RUNLOG.md` (committed `69995f1e`), which named the four secret patterns literally; the line is reworded and the module passes (22 passed). Lane GREEN: 3,746 tests, 0 failed, 0 errors, 17 declared exclusions (`lane-o3.xml`).
