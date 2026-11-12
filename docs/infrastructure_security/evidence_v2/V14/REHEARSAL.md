# V14 — workstation rehearsal

| Field | Value |
|---|---|
| Asked by | The operator, 2026-11-12 (V14-OP6): rehearse §4 and §5, and extend to the §6 commands over the committed sanitised artifacts, in the bundle-only tree |
| Run by / on | agent (Claude) / 2026-11-12, workstation, Python 3.10.6, PyMuPDF 1.28.2 |
| Model calls | None. `assess` ran with `boto3.client` replaced by a scripted Converse client (`rehearsal/trace_run.py --fake-converse`) |
| AWS calls | None |
| Proposal content | None. §4 and §5 ran over an invented eleven-page Part B. Route (ii) used the ESR record's observation ids only, with synthetic dispositions (`rehearsal/synth_dispositions.py`). §6 ran over committed public artifacts, read by the commands only; the agent printed exit codes, hashes, counts and paths |
| Scripts | `rehearsal/` (this folder). Traces stayed in the session scratchpad; this record carries what they showed |

## Trees

- **Full tree.** `C:/Code/proposal_demo/freeze_bundle` at `17e32d54`, clean, and a `git archive` of the tag into scratch (2,826 files).
- **Bundle-only tree.** The tag's files under the bundle's nine roots (`deploy/offline_bundle.json`): 299 files. An
  empty `.git` folder was added, because the bundle tarball adds the same marker as `app/.git`
  (`runner/offline_bundle.py`) and `harness.commands._common` needs it to find its root.
- **Private roots.** Scratch folders outside every checkout.

Each command ran under `trace_run.py`, which records every file the process opens (a Python audit hook). A file the
code only tests for existence is not recorded, so each list below was confirmed by a run without the file.

## Results

| # | Run | Tree | Result |
|---|---|---|---|
| R1 | §4: `--describe`, `--environment`, dry import, acceptance check, `author_original_workspace` | full | All exit 0 |
| R2 | §4 step 1c as the runbook writes it (`py -m tools.import_external_proposal … --config-input … --repo-root …`) | full | **Refused**, exit 1: `revision 'as_submitted_v1' belongs to no declared document` (V14-F3). It wrote one file, `…/source_materials/sources.json`, before refusing |
| R3 | The same importer, called in-process (`-c "…import_external_proposal as m; sys.exit(m.main())"`) | full | Exit 0. Wrote the document version, the import manifest and the register. 0 findings, 0 unchecked |
| R4 | §5 preflight, assess (scripted), freeze; §6 audit, historical profile, default `--repo-root` | full | Preflight 0, no flags; assess 0, **45 calls** (30 cell, 15 criterion), every request `maxTokens` 2048; freeze 0, 22 of 22 checks. Audit refused: the register resolves under `--repo-root`, the code tree |
| R5 | The same with `--repo-root <private root>` | full | Every profile-named file then resolves under the private root, so the bundle's own files must be there too |
| R6 | R4 with `--repo-root <private root>`, adding each file a run named as missing, from the tag | bundle-only | Four iterations: the registry, then the MSCA-DN scorecard, rubrics and appendix mapping. Then preflight 0, assess 0, freeze 0 (22 of 22), audit 1 (advisory flags on the thin fixture; the audit returns 1 when it flags) |
| R7 | §6 `audit`, `compare` (with `--historical-candidate`), `review`, `diff` over the committed sanitised artifacts, 2026 default profile | full | All exit 0. `review` takes the committed comparison 0003, because the approved notes bind it |
| R8 | R7 with `--repo-root <root>` holding only the sanitised inputs and the R6 files | bundle-only | `audit`, `compare`, `review` exit 0. `diff` needed three more: `harness/profiles/msca_pf_default.json`, its scorecard and its rubrics (V14-F4). Then all exit 0 |
| R9 | Which private-root files R6 opened | bundle-only | Only the workspace, the register, the supplement and the run's own outputs. Not the PDF, the dry-import records or the configuration input |
| R10 | R6 on a root without the PDF, the dry-import records and the configuration input | bundle-only | Same exits; pack set `d229a16f…` unchanged |
| R11 | `workstation/v14_pack.py` on a fresh root, twice; then its refusals | full | 19 members, 48,914 bytes, the same sha256 both times. Refused: output inside the root, an ESR record planted under the root, a root inside a worktree, a worktree not at the O5 revision |
| R12 | R11's archive unpacked into an empty folder; R6 on it | bundle-only | Preflight 0, assess 0 (45 calls), freeze 0 (22 of 22), audit 1 as R6; pack set `d229a16f…` |
| R13 | Plain `py -3.10 -m … preflight --repo-root <root>`, as the operator will run it | full | Exit 0, no flags, pack set `d229a16f…` |

The pack-set hash was the same in R4 (full tree, default root), R6 (bundle-only, private root) and R13 (workstation,
plain). A preflight on the workstation therefore measures the pack set the host will assess, given the same root.

## The supplement

`supplement.json` lists ten files from the tag, with sha256 and size. One is outside the bundle (the expectation
registry). Eight are bundle files that must also sit under the private root, because every command runs with
`--repo-root <private root>`. The tenth is the dispositions template, which no command reads; runbook §6 tells the
operator to copy its rows. The ESR record is not in it (V14-OP1).

The historical profile also names the authority index and the equivalence matrix. No command in R4–R12 opened
them, so they are not in the supplement.

## Per-call overhead, measured

From the scripted assess in R6, characters per request beyond the pack or criterion input:

| Call | Count | Largest overhead | Tokens at 4 characters | At 3 characters |
|---|---|---|---|---|
| Cell (expectation × sample) | 30 | 2,847 characters | 712 | 949 |
| Criterion (criterion × sample) | 15 | 4,564 characters | 1,141 | 1,522 |

The cost statement assumed 4,000 tokens per call. `workstation/v14_cost.py` uses the measured figures.

## What also came out

- **The provenance log follows `--repo-root`.** `assess` appends one line per call, rationale included, to
  `harness/provenance/blind_assessment.jsonl` under `--repo-root`. With the private root, it stays there (R6, R12).
  In R4 it went into the freeze worktree: 90 lines of scripted text, removed with
  `git checkout -- harness/provenance/blind_assessment.jsonl`. The worktree is clean at `17e32d54`.
- **The checkpoint follows `--repo-root` too**: `<private root>/.harness/checkpoints/`.
- **The bundle-only tree took no writes.** Every output landed in the private root or the named output folders.
- **`--config-input` is read two ways.** `author_original_workspace` takes it relative to `--root`; the importer
  takes a path and refuses one not under `--repo-root`. The step sheet writes both forms out.

## Not rehearsed

- `compare`, `review` and `diff` under the historical profile. They need private dispositions and notes. R8 covers
  their code paths under the 2026 profile. The historical profile adds only the files R6 found (Inferred).
- The register re-render was rehearsed after the operator's V14-F5 answer: see "Route (ii)" below.
- The readiness receipt (runbook §1.1) for V14. Its host scripts are written with the host steps.

## Route (ii): the register re-rendered after the freeze

Asked by the operator, 2026-11-12, with the V14-F5 answer. Host side: a copy of the R12 root (unpacked archive,
frozen baseline, first audit), with the committed ESR record placed at its repository path, as H08 will. Workstation
side: a copy of the R11 root. The bundle-only tree for every host command; the freeze worktree for the re-render.

| # | Run | Result |
|---|---|---|
| R14 | First comparison (route iii): 29 synthetic rows; the miss `ESR-E-01` declared `evidence_preserved_status: Inferred`, no declaration | `compare` exit 1 (advisory flag); E-01 `Inferred` |
| R15 | Workstation: a declaration input at `private/msca_dn_original/declarations/as_submitted_v1.json` with a `fidelity_to_submitted_original` block for 1.1; importer `--check`, then the in-process import (STEPS.md W05 form) | `--check`: exactly one file would change, the register. The import wrote that one file. Every other file under the root, the document version, the manifest and the candidate included, is byte-identical. The freeze worktree stayed clean |
| R16 | The new register copied into the host root. Successor dispositions: E-01 `Confirmed`, citing `declared/sub_sections/1.1/fidelity_to_submitted_original`, `supersedes` the first | `compare` exit 1 (the same advisory flag); E-01 `Confirmed`; baseline `b9b85763…` in both comparisons; register `938cca93…` then `e0ccd3b3…`. It ran against the first audit, made over the old register |
| R17 | Control: the same Confirmed dispositions against the old register | Refused, exit 2: `register pointer 'declared/sub_sections/1.1/fidelity_to_submitted_original': position #1.1 is outside a list of 0` |
| R18 | A successor audit over the new register | Exit 1 (advisory); `baseline: bound - candidate hash and snapshot id equal the frozen baseline's` |
| R19 | `compare` again, citing the successor audit | Exit 1; written |
| R20 | `diff` first comparison → successor | **Refused**, exit 2: `the fidelity register moved after the comparison was written` (V14-F6) |
| R21 | `diff` between the two comparisons over the new register (R16 → R19) | Exit 0 |
| R22 | The frozen baseline's two files and the blind report, sha256 before R16 and after R21 | Unchanged |

**Answer.** Yes. A register re-rendered after the freeze loads against the frozen baseline. The re-render changes
the register alone, so the candidate hash and snapshot id the freeze bound do not move. `compare` binds the
successor dispositions to the same baseline, and a successor audit reports itself bound. What does not carry
across the swap is `diff` from the route (iii) comparison, because it re-hashes the register that comparison
recorded (V14-F6).

## Part H scripts on a simulated host

Run by the agent, 2026-11-13, after the operator's W01–W08. The host scripts of `host/` ran under Git Bash with their
rehearsal overrides: `V14_APP` a copy of the bundle-only tree (plus a `bundle_manifest.json` naming `17e32d54`),
`V14_PY` Python 3.10 with `boto3.client` replaced by the scripted Converse client, `V14_LAUNCH=none` (no runtime
secret; the scripted client sets `AWS_REGION` and the transport environment), and `V14_LOCAL_ARCHIVE` in place of
the bucket. The input was R11's synthetic archive. No AWS call, no model call. The synthetic root has its own pack
set, so `V14_EXPECT_PACK_SET` was relaxed for R24 only.

| # | Run | Result |
|---|---|---|
| R23 | `v14_inbound.sh`, kind `input` | `RESULT=expected`: 19 members, workspace 8, register 1, supplement 10, one manifest, no ESR record; `in_app_equal=8`, `in_app_differ=0`. A second run refused: the root exists |
| R24 | `v14_h05a_prepare.sh` | Preflight exit 0 (the fixture raises no flag), package `complete` under 400000, 10 packs; the draft with the thirteen placeholders; the rendered request `eu.anthropic.claude-sonnet-4-6`, temperature 0, `maxTokens` 2048, no tool configuration, `eu-north-1` |
| R25 | `v14_h05b_receipt.sh` | `placeholders_left=none`; the validator exit 0, `receipt check: green` |
| R26 | `v14_h06_assess.sh` | Receipt green before; assess exit 0, 45 live calls, `requests=45`, no tool configuration, no child process; freeze exit 0, 22 of 22 conditions, two baseline files; receipt green after, against the report |
| R27 | The pass cut by a scripted outage after 20 calls, then `PO_RESUME=yes` | The cut run left the checkpoint and no report. The resume: 20 replayed, 25 live, freeze 22 of 22, receipt green (V14-D2) |
| R28 | The same cut after 30 calls, with the exception now caught | `assess_exit=exception:RuntimeError`, `report_count=0`, `checkpoint_lines=31`: the evidence says where it stopped |
| R29 | `workstation/v14_pack_one.py --esr`, then `v14_inbound.sh` kind `esr`, then `v14_h08_audit.sh` first | The member sha256 `5c9b9c8e…` checked on both sides; the ESR placed at its repository path. Audit exit 1 (advisory), one report, `baseline_bound=bound` |
| R30 | `v14_pack_one.py --register` over route (ii)'s re-rendered register, then kind `register`, the successor audit, `v14_status.sh` | Register `938cca93…` → `e0ccd3b3…`, as R16; the old copy kept. Successor audit bound. Status listed paths, sizes and hashes only |
| R31 | `v14_h09_return.sh`, `v14_h11_credcheck.sh` | The return printed numbers, booleans, hashes and identifiers only. Two fixes came out of it: `assessed_at` was withheld for its `+`, now allowed; the criterion spread label is a fixed sentence, now not printed. The credential check found nothing on the simulated root, and caught a planted key-shaped string |

Not rehearsed here: every AWS call (the sender, the bucket's version deletes, the lifecycle, the snapshot, CloudTrail),
the launcher (R15 ran it on the host), and Linux file modes (the scripts check `root_mode=700` only on Linux).
