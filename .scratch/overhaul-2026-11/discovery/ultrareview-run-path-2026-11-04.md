# Ultrareview — slice 1 (run path), 2026-11-04

Run: `claude ultrareview 1` (free run 1 of 3) on draft PR #1 (`ur/review-run-path` → `ur/base-run-path`).
Code reviewed = `msca-dn-pre-eval` @ `de226401`. The base is that commit with the slice reverted to `main`,
so the PR diff is exactly the slice: 12 files, +7,281 −67.
Result: 16 found, 18 verification passes, 6 refuted → **10 verified findings**. Raw output: operator's
`~/ultrareview-run-path.txt` (not in the repo).

## Scope decisions (operator, 2026-11-04)

- No path filter exists, and the diff cap is 8,000 lines, so the plan's single run became **three slices**:
  1 run path (this file), 2 audit and records, 3 ESR side.
- **Anonymisation (`runner/anonymisation_*`) is excluded entirely.** The AN-built code the run executes
  (Converse backend, receipt by transport, drafter refusal) lives in `harness/` and `runner/transport/`,
  and slice 1 covers it.
- Method: a branch review is refused ("Repo is too large"), so use PR mode. Per slice: a base branch
  (`msca-dn-pre-eval` with the slice reverted to `main`) and a review branch (base + a revert of the
  revert), plus a **draft PR whose base is the base branch**, not `main`.

## Slice 1 files

`harness/blind_assessment.py`, `harness/commands/blind_assessment.py`, `harness/blind_baseline.py`,
`harness/evidence_preflight.py`, `harness/execution_receipt.py`, `harness/commands/execution_receipt.py`,
`harness/commands/_converse_judge.py`, `harness/response_cache.py`, `harness/evidence_pack.py`,
`harness/judge.py`, `runner/transport/bedrock_converse.py`, `runner/transport/config.py`.

## Findings (as reported; 🔴 = reported important)

| # | Location | Finding |
|---|----------|---------|
| 1 🔴 | `harness/commands/blind_assessment.py:667-677` | `_pack_params` picks the `--budget` default per transport but not `--criterion-budget`. On the OpenAI-compatible transport (a per-minute-ceiling provider), criterion prompts of up to 32,768 tokens are rejected as non-retryable after all cell calls were paid for. |
| 2 🔴 | `harness/evidence_preflight.py:347-352` | Preflight records a rubric whose declared anchor is missing from the candidate as a "not built" pack, and `check_preflight` accepts it. `assess` then crashes mid-run, after spending quota, when `build_evidence_pack` raises. |
| 3 | `harness/blind_assessment.py:1021-1037` | `--criterion-n` below the majority minimum is rejected only after every cell call (`grade_criterion`, `criterion_scoring.py:722`). `n` is checked up front (line 977); `criterion_samples` is not. The checkpoint binding includes `criterion_samples`, so a corrected value cannot resume. |
| 4 | `harness/commands/_converse_judge.py:161-169` | Converse misconfiguration (no `AWS_REGION` in production mode, no model, backend not allowed in production) raises a plain `ValueError` that is neither in `_CLI_ERRORS` nor a transport error. `assess --transport bedrock-converse` ends in a traceback, not the fail-closed exit code 2. |
| 5 | `harness/judge.py:513-527` | A resumed run writes a new provenance record, with a fresh timestamp and no replay mark, for every replayed checkpoint response. The provenance trail double-counts replays as live draws. |
| 6 | `harness/response_cache.py:116-131` | `CacheBinding` claims to carry "the sampling parameters" but holds only `n` and `criterion_samples`, not temperature or max_tokens. Replay is keyed by prompt hash, so `--resume` after a max-tokens change is accepted and mixes two inference configurations. |
| 7 | `harness/commands/execution_receipt.py:108-118` | The "refuse a receipt stored inside this repository" guard checks against `--repo-root` (default `.`), not the repository. Run from elsewhere, or with `--repo-root` pointed at the profile's directory, an in-repo receipt is accepted. `converse_smoke.check_receipt` anchors on `THIS_REPOSITORY` correctly. |
| 8 | `harness/commands/blind_assessment.py:1095-1118` | `_salvage` repeats the cell-grid loop and rebuilds every pack, though `cell_grid()` is "the one definition" and `main` already holds `realised` packs. The same pattern is at `evidence_preflight.py:339`. |
| 9 | `harness/evidence_preflight.py:161-163` | `file_sha256` duplicates `harness.record_binding.file_sha256`. |
| 10 | `harness/evidence_preflight.py:985-996` | `_ascii`, `_table` and `_utc_now` duplicate `harness/blind_assessment.py` byte for byte. |

## Triage (2026-11-04) against the V14/V16 route and existing tickets

"On path" = code the V14/V16 private-host blind assessment executes (wayfinder map decisions 2–3).

| Finding | On path? | Covered by | Proposed disposition at Step 3 |
|---------|----------|------------|--------------------------------|
| 2, 3, 4 | yes | none | **New ticket UR-A, "Refuse a bad configuration before the first assessor call."** One seam (the assess command's pre-flight checks). Finding 4 only bites if V14/V16 use Converse. |
| 1 | no (OpenAI-compatible transport only) | none | Ride along in UR-A if it stays cheap; otherwise defer. |
| 6 | yes (V14 requires a resume) | none (ticket 02 is the rubric lane, not blind assessment) | **New ticket UR-B, "The resume binding covers the inference configuration."** |
| 7 | yes (V13 receipt; private-content guard) | none | **New ticket UR-C, "Anchor the receipt guard on this repository."** Small. |
| 5 | yes ("audited") | partly ticket 01 (judge writes every record, marks replays) | **Amend ticket 01:** add a box saying a replayed *valid* draw writes no new live record and is marked replayed. |
| 8 | yes (salvage) | ticket 01 reworks salvage | Note in ticket 01; no separate ticket. |
| 9 | — | ticket 04 (file hash ×3 incl. evidence preflight) | None; ticket 04 already covers it. |
| 10 | — | none | Hygiene; defer. |

Every new UR ticket changes `harness/blind_*`, `evidence_*` or `execution_receipt` code, so all need the
**PE-09 acceptance lane green** (admission rule 5).

## Side finding for wayfinder ticket 03

The PE-09 runbook's V14 commands (`plans/msca_dn_pe09_runbook.md` ~334–378) use `--transport claude-cli`.
The runbook (V12, 2026-10-13) predates the Converse assessor (AN1a, 2026-10-14). The F7 map's decision 3
says V14/V16 run on Converse on the private host. Ticket 03 must settle V14's transport, since that decides
whether findings 1 and 4 are on the path.

## Still to run

- Slice 2 (audit and records): `integrity_audit.py`, `candidate_provenance.py`, `grounding_scope.py`,
  `profile.py`, `historical_profile.py`, `acceptance_lane.py` + `commands/acceptance_lane.py`,
  `criterion_scoring.py`. About 6,000 lines; free run 2.
- Slice 3 (ESR side): `esr_comparison.py`, `operator_review.py`, `comparison_diff.py`,
  `deferral_register.py`, `authority_matrix.py`. About 6,700 lines; free run 3. V14 only (V16 has no ESR).
- Close PR #1 without merging, and delete the `ur/*` branches once all slices are done.
