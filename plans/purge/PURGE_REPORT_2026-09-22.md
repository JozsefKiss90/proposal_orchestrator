# PURGE REPORT — FIELDWISE project purge (2026-09-22)

Branch `engine-base`, created from `ESR` at `e56ede2`. Spec: `PURGE_SPEC_2026-09-22.md`.
Manifest as approved: `PURGE_MANIFEST_2026-09-22.md`. Operator approved the manifest and the
three recommended decisions on 2026-09-22 with the instruction "no FIELDWISE data should remain".

## 1. Archive

| Item | Value |
|---|---|
| Tag | `fieldwise-final-2026-09-22`, annotated, on `ESR` `e56ede2` |
| Bundle | `C:\Code\proposal_demo\fieldwise-archive.bundle`, 224 MB |
| Bundle refs | `ESR`, `fieldwise-run-01`, `fieldwise-run-02`, `fieldwise-run-03`, the tag |
| Verify | `git bundle verify`: "The bundle records a complete history" |
| Branches | `ESR`, `fieldwise-run-01/02/03` still exist. Deleting them is a separate operator step. |

## 2. What was removed

One commit per manifest group, in order:

| Commit | Group | Tracked files removed |
|---|---|---:|
| `9af07fe`, `9a9deb1` | A. Tier 3 + misfiled Tier 2A copy | 28 |
| `da9f846` | B. Tier 4 (incl. whole decision log) | 205 |
| `c6a6da0` | C. Tier 5 (incl. sealed submission) | 22 |
| `9d8c46b` | D. Plans, prompts, reports (+ stale `project_structure.md`) | 46 |
| `1a60008` | E. Root strays (+ pre-absorb MSCA bundle) | 7 |
| `73ff469` | G. `MSCA/` vault | 218 |
| `fd38b0a` | F. Harness instance-derived data | 19 |
| `4943bf8` | H. FIELDWISE-only tools and tests | 16 |
| `ca21334` | H. Prose scrub (no deletions) | 0 |

Untracked or ignored state deleted without a commit: `.claude/runs`, `.claude/logs`,
`.claude/benchmark`, `.claude/skill_diag`, `.pytest_cache`, `.mypy_cache`, all `__pycache__`,
the E5f rubric pickle, the run-02 runner logs, and the untracked half of `MSCA/`.

Every emptied directory still exists with a `.gitkeep`: Tier 3 (five subfolders plus
`source_materials/`), Tier 4 (all phase-output folders down to `section_drafts/*`), Tier 5
(five subfolders), `harness/provenance/`, `harness/rubric_reports/`.

## 3. What was intentionally kept

- **Tier 0 to Tier 2B** in `docs/`: unchanged except the removal of the FIELDWISE-filled
  Part B form copy from Tier 2A. The blank MSCA Part B template stays.
- **Engine**: `runner/`, `tools/` (minus seven FIELDWISE-only tools), `scripts/`, `tests/`
  (minus nine FIELDWISE-only modules), `harness/` code, rubrics, scorecard, READMEs, the
  labelling guide and the blank E3.1 template.
- **Constitutional config**: `CLAUDE.md`, `AGENTS.md`, `.claude/agents|skills|workflows|output-styles`,
  `.mcp.json`, `prose.config.json`, `skills-lock.json`. None named FIELDWISE.
- **Vault template** `templates/obsidian_graph_vault/`: complete on its own (21 folders, noun-free
  config, meta node, two dashboards). Nothing generic lived only in `MSCA/`.
- **Registries** `docs/index/*.json`: no reset needed, the document, instrument and rule
  registries were already empty lists.
- **`working_assumptions.json`**: not restored. The loader returns an explicit empty state when
  the file is absent, so nothing requires it.
- **Engine history** in `plans/`: milestones, harness plan, phase-refactor tickets, engine
  handoffs. Six of them had one passing instance reference each, now reworded.
- **AWS telemetry**: `costs/`, `bedrock-*.json`, `screenshots/`, `docs/benchmark_json/`.
- **Live git worktree** `.claude/worktrees/e5f-implementation-status-f7651c`: a dirty checkout of
  `main` (583 changed paths). Its files contain FIELDWISE text from `main`. Removing it means
  `git worktree remove --force`, which discards uncommitted work, so it was left for you.

## 4. Residual references and their justification

`git grep -inE "fieldwise|cholakova|agrovir|mvcri|101373105"` on `engine-base`, excluding
`plans/purge/` (the purge record itself) and the seed decision entry:

| File | Hits | Justification |
|---|---:|---|
| `runner/agnosticism_lint.py` | 3 | Denylist of instance-#1 nouns, the standing guard that the generic layer is noun-free (decision 2, keep). |
| `tests/runner/test_agnosticism_lint.py` | 4 | Tests the denylist with its own nouns (decision 2). |
| `tests/runner/test_vault_scaffold.py` | 1 | Noun regex asserting the scaffolded vault is noun-free (decision 2). |

Untracked or ignored paths: only regenerated `.pyc` files of the two modules above, and the
live worktree noted in §3. No other file in the checkout matches.

The denylist also contains `ELTE`, `Jung`, `Budapest`, `Hungary`, `MSCA` and the domain nouns.
Those appear in engine-history documents under `plans/milestones/` and in the AWS hardening
evidence ("ELTE DPO review"). They are outside the spec's grep pattern and were left.

## 5. Verification output

`git status --porcelain` after the closing commit: clean.

`py -3.10 -m runner.agnosticism_lint`:

```
[agnosticism-lint] OK — 15 generic-layer file(s) scanned, no project nouns found.
```

`py -3.10 -m pytest` (full suite):

| Run | Passed | Failed | Errors | Skipped |
|---|---:|---:|---:|---:|
| Baseline `ESR` before the purge | 4874 | 147 | 22 | 42 |
| `engine-base` after the purge | 4523 | 58 | 22 | 108 |

Newly failing versus baseline: **none**. Every one of the 58 failures and 22 errors was already
failing on `ESR` before any deletion, so none is a purge consequence:

| Test file | Count | Pre-existing cause |
|---|---:|---|
| `tests/harness/test_rubrics.py` | 18 F + 8 E | E5f rubric backend fixtures (Groq lane), red on ESR |
| `tests/harness/test_expectations.py` | 12 | Scorecard vs registry drift ("recruiting institutions" row), red on ESR |
| `tests/harness/test_expectation_coverage.py` | 11 E | Same scorecard drift |
| `tests/test_transport_openai_compatible.py` | 10 | Optional OpenAI-compatible transport lane, red on ESR |
| `tests/runner/test_skill_applicability.py`, `test_drafting_skill_hygiene.py`, `test_phase8_consistency_layer.py`, `test_phase8_canonicalization.py` | 10 | Skill-spec size and leanness limits, red on ESR |
| `tests/harness/test_evidence_pack.py` | 3 E | Pack fixtures, red on ESR |
| eight single failures (transport, presets, persistence, caller context, gate10d, rubric report, boundary) | 8 | Red on ESR |

Of the 89 red entries that disappeared, 73 were in the deleted `test_fieldwise_*` and
FIELDWISE-tool test modules, and 16 in surviving modules turned green because they had asserted
on drifted FIELDWISE state. Tests that now skip with a stated reason: 66 additional skips, all
"no live Tier 4/5 substrate in this checkout".

**Dry-run instantiation smoke test.** With Tier 3 empty:

```
py -3.10 -m runner --run-id 00000000-0000-4000-8000-00000000c1ea --dry-run
[BACKEND] transport=claude_cli  model=(default)  preset=CLAUDE_REFERENCE  production_mode=False
[RUN]   run_id=00000000-0000-4000-8000-00000000c1ea
[READY] n01_call_analysis
```

The manifest loads, the graph bootstraps and Phase 1 is the ready node. Evaluating the Phase 1
entry gate in-process (`evaluate_gate("gate_01_source_integrity", …)`, no Claude call) returns
`status: fail` because `call_binding/selected_call.json` is absent. That is the correct
fail-closed state (§12.4): the engine reaches Phase 1 and stops at the first missing operator
input, and it invokes no agent body. No FIELDWISE artifact was needed to get there. The two
probe gate-result files were deleted after the check. A live Phase 1 was not run: it would spend
subscription quota and would block at the same predicate.

**Size and count delta** (excluding `.git/`):

| | Before | After | Delta |
|---|---:|---:|---:|
| Working tree size | 461 MB | 382 MB | -79 MB |
| Tracked files | 1496 | 954 | -542 |
| Files on disk (excl. the live worktree) | 4825 | 1238 | -3587 |

(`.git/` itself is unchanged at 830 MB. History is intact; run `git gc` only after you delete
the FIELDWISE branches, and only if you want the objects gone locally too.)

## 6. Test changes made (not engine logic)

Seven modules gained a skip guard that fires only when the substrate is absent. Once the next
project has run, these re-arm on their own.

- `tests/runner/test_phase6_field_production.py`: five production-artifact checks.
- `tests/runner/test_graph_projector.py`: three real-Tier-4 tests.
- `tests/runner/test_promote_graph_staging.py`: the `dod-1d` decision-entry checks.
- `tests/harness/test_regression_golden.py` and `tests/harness/test_measure_ledger_granularity.py`.
- `tests/harness/test_expectations.py`: two path-resolution tests.
- `tests/harness/test_gold_set.py`: the seeded template.

`tools/prose_detect.py` lost its `--builder` mode, which imported a deleted FIELDWISE builder.
JSON mode is unchanged.

## 7. Open items for you

1. Delete the FIELDWISE branches when you have seen `engine-base` build: `ESR`,
   `fieldwise-run-01`, `fieldwise-run-02`, `fieldwise-run-03` (local and `origin/ESR`,
   `origin/fieldwise-run-02`, `origin/fieldwise-run-03`).
2. Decide about the dirty worktree `.claude/worktrees/e5f-implementation-status-f7651c`.
3. The pre-existing 58 failures and 22 errors are engine backlog, not purge fallout. The
   scorecard-vs-registry drift (`test_expectations`) is the one most worth a ticket.
4. The throwaway simulation worktree `C:\Code\proposal_demo\purge_sim` was removed after use.
