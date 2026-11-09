# Ultrareview — slice 2 (audit and records), 2026-11-06

Run: `claude ultrareview 2` (**free run 3 of 3**; the slice-1 note's "2 of 3 left" was off by one) on draft
PR #2 (`ur/review-records` → `ur/base-records`). Code reviewed = `msca-dn-pre-eval` @ `de226401`; PR diff =
exactly the slice: 9 files, +5,958 −0. Result: 49 found, 29 verified, 32 refuted → **10 findings** after
synthesis. Raw output: operator's `~/ultrareview-records.txt`.

**Slice 3 (ESR side, PR #3) did not run:** "Free ultrareviews used. Turn on usage credits to continue."
Its disposition is an operator decision (see the end).

## Slice 2 files

`harness/integrity_audit.py`, `harness/candidate_provenance.py`, `harness/grounding_scope.py`,
`harness/profile.py`, `harness/historical_profile.py`, `harness/commands/historical_profile.py`,
`harness/acceptance_lane.py`, `harness/commands/acceptance_lane.py`, `harness/criterion_scoring.py`.

## Findings (as reported; 🔴 = reported important)

| # | Location | Finding |
|---|----------|---------|
| 1 🔴 | `harness/commands/historical_profile.py:86` | The CLI calls `hp.check(profile, rows, repo_root)` without `matrix_status`, so the documented sixth check (a status the matrix cannot carry) never runs from the command. |
| 2 🔴 | `harness/candidate_provenance.py:484-490` | `find_import_manifest` falls back to a `document_id` match even when the caller gave a `node_id` that matched nothing, so it can silently pick up another revision's manifest. |
| 3 🔴 | `harness/commands/acceptance_lane.py:194-209` | With `--junit PATH`, a JUnit file left at PATH by an earlier run is read when pytest writes no new report, and the pytest return code is ignored: a run where pytest never ran can reconcile GREEN. |
| 4 🔴 | `harness/acceptance_lane.py:471-489` | `reconcile`/`green` never check that the JUnit report covers the lane's modules; `collected`/`skipped` are not compared with `declared_skips` or the module set, so a narrowed run reconciles GREEN and certified. |
| 5 🔴 | `harness/integrity_audit.py:1445` | `_check_dcs` keys DC projects by number; with two prose blocks carrying the same DC number the last silently wins and no finding is raised. `_parse_dc_projects` scans every section, not just §1.1. |
| 6 🔴 | `harness/integrity_audit.py:1119-1121` (+ `:1048`) | Two parse loops consume the paragraph after a match without their own stop checks (`j += 2` after "Contribution to the Network"); if that heading is not followed by exactly one same-sub-section paragraph, the next `DC<n> – title` heading is skipped and that DC project disappears. |
| 7 | `harness/commands/acceptance_lane.py:180-182` | With `--from-junit`, certification comes from the machine re-reading the report, not the build that produced it: an uncertified report re-read on a pinned machine exits 0 as certified GREEN. |
| 8 | `harness/commands/acceptance_lane.py:235-253` | A narrowed run (`--area` or `-k`) exits 0 like a GREEN run, though the docstring says a narrowed run is never an acceptance result. |
| 9 | `harness/acceptance_lane.py:512-517` | `one_line` (+ `_WS`) re-implements `harness.record_binding.one_line`. |
| 10 | `harness/historical_profile.py:41-51` | Unused imports (`one_line`, `field`). |

## Triage (2026-11-06) against the V14/V16 route and the overhaul gates

"On path" = code the V14/V16 private-host run executes. The runbook's audit step
(`plans/msca_dn_pe09_runbook.md:467`, `blind_assessment audit … --candidate-provenance <manifest>`) runs the
integrity audit; the historical-profile check (`:181`) runs before V14 loads its profile.

| Finding | On path? | Covered by | Proposed disposition at Step 3 |
|---------|----------|------------|--------------------------------|
| 3, 4, 8 (+7) | **gate, not run path.** The PE-09 acceptance lane is the rule-5 "green" every DN-path ticket must show; a false GREEN voids that check. | none | **New ticket UR-D, "The acceptance lane is GREEN only when this run proved it."** Fresh report per run (refuse a pre-existing `--junit` file), pytest return code honoured, coverage of lane modules and `declared_skips` checked, narrowed runs exit non-zero. 7 rides along if cheap. Until it lands: every lane run uses a new `--junit` path, no `-k`/`--area`, no `--from-junit`, and the pytest exit code is read. |
| 5, 6 | **yes, V14 and V16** (audit of a DN candidate with DC projects) | none | **New ticket UR-E, "The integrity audit never loses or overwrites a DC project."** Duplicate DC numbers become a finding; the two consume-next-paragraph loops respect their stop conditions. Failing tests from synthetic Part B prose. |
| 2 | **V16** if provenance is resolved from the graph root (the runbook passes `--candidate-provenance` explicitly for the audit, so the audit itself is safe when that path is given) | none; relates to W01 (import route) | **Small fix:** a `node_id` that matches nothing returns "not found", never another revision. Candidate to pair with 1 as one "two refusals" ticket (no interface change in either module, so rule 1 holds), or fold into a W01 must-land item. |
| 1 | **V14 only** (profile check before loading) | none | **Small fix:** pass `matrix_status` from the CLI. Pair with 2 (above). |
| 9, 10 | — | — | Hygiene; defer. |

All new UR tickets change `harness/` DN code, so rule 5 applies: PE-09 acceptance lane green, which for
UR-D means the lane checks itself (write UR-D's failing tests to run outside the lane command first).

## Slice 3 (ESR side) — operator decision

Not run. ESR comparison, operator review, comparison diff, deferral register and authority matrix are used
by **V14 only** (V16 has no ESR). Options: (a) turn on usage credits and run PR #3; (b) run the repo's local
`code-review` skill over the 7 files instead (free, less thorough); (c) skip, accepting that the ESR side is
reviewed only by its existing tests. Recommendation: (b) if W05 puts V14 before 23 Nov, else (c).

## Clean-up once slice 3 is settled

Close PRs #1, #2 (and #3) without merging; delete `ur/base-*` / `ur/review-*` locally and on `origin`;
`git worktree remove ..\ur_slices`.
