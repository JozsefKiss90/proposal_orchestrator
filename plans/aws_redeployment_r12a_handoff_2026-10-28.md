# AWS redeployment: handoff for R12a (parameterised evidence collector)

| Field | Value |
|---|---|
| Date | 2026-10-28 |
| Branch at writing | `msca-dn-pre-eval`; HEAD `265f88d tick R9e`. R10 is done and ticked in the working tree but **not yet committed**: the operator commits it as `close R10` (the R10 change, `evidence_v2/R10/`, the decision record, register v2, worklog and the ticket tick together) before R12a starts. This file is the operator's to commit too (`starting R12a`). |
| For | The agent that runs ticket R12a with the operator in a new session |
| Read first | `CLAUDE.md` (§9, §13; `tools/` is outside `runner/`, so §17 does not govern the collector, but §9.4 and §12 govern its evidence); `plans/aws_redeployment_tickets.md` (inherited constraints; R12a; R11, R12b, R13 for what the collector must later serve); `plans/aws_redeployment_handoff_2026-10-21.md` §4 (F1–F9), §6 R12, §7, §7a, §8, §9 (old-to-new map); §2 of this file and of the R4–R10 handoffs; decision records `aws-redeployment-operator-decisions_2026-10-21` (OD3–OD5, OD9, OD12, OD13), `aws-redeployment-od1-region-r1_2026-10-21`, `aws-redeployment-od6-stack-layout-r3_2026-10-22`, `aws-redeployment-od7-model-set_2026-10-21`, `aws-redeployment-r1-baseline-deviations_2026-10-21` (R1-D1, R1-D2), `aws-redeployment-r8-secret_2026-10-26`, `aws-redeployment-r9-runtime-config_2026-10-27`, `aws-redeployment-r10-drafter-transport_2026-10-28` (F-R10-1); `deploy/aws/outputs_contract.json`, `deploy/aws/README.md`, `deploy/aws/parameters/*.json`; `docs/infrastructure_security/evidence_v2/README.md` and `_templates/`; `docs/infrastructure_security/aws_hardening_control_register_v2.md` (all 41 rows, the Ticket column); the old collector `docs/infrastructure_security/evidence/11_audit_package/collect_evidence.ps1` (**read only, history; v1 tree, never edited**); `tools/old_id_guard.py`, `tools/evidence_secret_scan.py`, `tools/env_config_digest.py`, `runner/host_env.py`; tests `tests/test_aws_iac_contract.py`, `tests/test_old_id_guard.py`, `tests/test_evidence_protocol_scaffold.py`; evidence `evidence_v2/R4/`–`R8/` (`<ticket>_outputs.json` shape), `evidence_v2/R10/` (`STEPS.md` format) |
| Decision records in force | as listed in the R10 handoff, plus `aws-redeployment-r10-drafter-transport_2026-10-28` |
| Status | E0, R0–R10, R9e done (R10 pending its commit). Frontier: **R12a**. R11 is unblocked but **held by the operator** (2026-10-28: R11 only when it is really needed, because of its hourly cost); R12b, R13, R14, R15 and R16 all wait on R11. |

## 1. Facts that govern R12a

| Fact | Record / evidence |
|---|---|
| **R12a is code only. It collects nothing yet.** No AWS call, no resource, no cost. Evidence is test output and the repository diff, as in R9, R9e and R10. The first real run is R12b (after R11). | ticket R12a |
| **The ticket's three criteria:** (1) a test runs the collector against fixture stack outputs and confirms every id it uses comes from them; (2) a test confirms it refuses an output path inside the v1 tree; (3) the R3 old-ID test passes over the collector. | ticket R12a |
| **The old collector** (`evidence/11_audit_package/collect_evidence.ps1`, 749 lines, PowerShell, CRLF) hard-codes the old account, 18 resource ids and us-east-1, writes into the v1 tree (`-EvidenceRoot` defaults to `evidence/`), and has a `-SkipHostTests` switch: its host tests (DNS, caller identity, live negative Region, secret retrieval, no Claude CLI, egress, config keys, an end-to-end Converse call) ran **as local commands**, so they only worked when the script itself ran on the host. Its structure is a useful map (one evidence file per control check, CG1–CG10, an integrity manifest); its ids, Region, model ids and paths are not. It stays unchanged (E0: no file in the v1 tree changes). | file read 2026-10-28; handoff 2026-10-21 §4 |
| **Where ids come from:** `deploy/aws/outputs_contract.json` names 6 stacks and 32 outputs, each with its consumers (R12a consumes nearly all of them). Its `outputs_file_rule`: after each create or update the operator saves `describe-stacks … Outputs` as `evidence_v2/<ticket>/<ticket>_outputs.json`, and "later step sheets and the collector take ids only from those files". Present today: `R4`–`R8_outputs.json` (lists of `{OutputKey, OutputValue, Description, ExportName}`). The `host` stack (R11, `lifecycle: per_session`, `hourly_cost: true`) has no outputs file yet, and once R11 runs it is deleted and recreated per session, so its ids change. | contract; `deploy/aws/README.md` |
| **Account and Region** are in every parameter file (`ExpectedAccountId`, `ExpectedRegion`); `tests/test_aws_iac_contract.py` ties them to `R1_00_caller-identity.json` and OD1-r1 (eu-north-1). IAM is global; us-east-1 only for global services (register v2 header). The OD7 model ids and the routed Regions are in `deploy/aws/parameters/iam.json` and `host.json` (`InferenceProfileArns`, `FoundationModelArns`, `RoutedRegions`). | parameter files; register v2 |
| **The old-ID guard** (`tools/old_id_guard.py`) has a default v2 scope (`deploy/aws/`, `evidence_v2/`, register and worklog v2, `aws-redeployment-*` records) and takes explicit paths; its docstring already names the expected collector path: `py -3.10 -m tools.old_id_guard deploy/aws tools/collect_evidence_v2.py`. It matches old ids exactly and assembles them from fragments; `plans/` is out of its scope on purpose. **This handoff names no old id.** | `tools/old_id_guard.py` |
| **The secret scan** (`tools/evidence_secret_scan.py`) refuses evidence carrying secret values, keys or tokens; `evidence_v2/README.md` forbids prompt or proposal text and model responses beyond a fixed test string. The R8 key-names digest (`tools/env_config_digest.py`) is the precedent for evidencing the secret by key names and SHA-256 only. | README; R8 |
| **What the collector must later serve (R12b):** every row of register v2 VERIFIED_PASS, NOT_APPLICABLE with a reason, or DEFERRED; the F7 negative test (a presigned PUT to an outside bucket fails from the host); the in-host DC-15 tests (no long-term access keys on the host); DC-40 re-assessed. Host-side checks (DC-02, DC-14, DC-15, DC-17 live, DC-21 retrieval, DC-31, DC-32, DC-33–35 key names, DC-37) cannot run on the workstation: the host has no inbound path and the operator reaches it only through SSM (R11 criterion: Run Command returns `Success`; R1's SCP probe found `ssm:SendCommand` allowed). | tickets R11, R12b; register v2; R1 evidence |
| **Register v2 today:** 19 rows VERIFIED_PASS or NOT_APPLICABLE (R4–R8), the rest NOT_STARTED or IN_PROGRESS, waiting for R11 or R12b. R12a changes no row. | register v2 |
| **Full suite.** The R10 baseline and after-run (200 failed each, identical ids) are in `evidence_v2/R10/`; the suite is order-dependent and makes outbound HTTP requests (F-R9-1); one test writes into Tier 4 and can hit a Windows file lock (F-R9e-1). "No new failures" is judged by id (R9-D23). A new baseline on the R12a start commit is still the clean reference. | R10 evidence |

## 2. How the operator works

Everything in the R4–R10 handoffs' §2 holds. Added in R10:

- The operator answers "1–N a"; new points get new numbers, including points found after the baseline.
- **The operator may skip a commit or run a step out of order** (R10: no `starting R10` commit, the handoff went into `tick R9e`; R10-D13). Check `git log` and `git status` at every hand-back and record a deviation rather than asking for a rerun when the tree is the same.
- **`.venv-lint` may be active** when a block runs (R10 step 01). `py -3.10` names the version, so the run stands; record it.
- **The tick may precede the commit** (R10): the operator then commits the change, the evidence and the tick together.
- The device can disconnect mid-call. Before retrying any write, check whether it took effect; never re-append.
- **Agent-side lessons (R9–R10):**
  - Never run a git command that writes in the connected folder. Compare on `git archive HEAD | tar -x -C $HOME/<dir>` copies; run `git init -q` in each copy.
  - **The device VM's git has no `core.autocrlf`:** in the connected folder it shows CRLF files as rewritten whole. Read the real diff with `git -c core.autocrlf=true diff --stat` (read-only).
  - A device VM venv: `uv venv $HOME/r9venv --python 3.10`; `uv pip install --python $HOME/r9venv/bin/python python-dotenv==1.2.2 boto3==1.42.68 pytest httpx pyyaml jsonschema pymupdf==1.28.2`. python-docx is absent: leave `tests/runner/test_docx_exporter.py` out of both sides. The session's `$HOME` may be new; re-create it.
  - A device call is capped at ~180 s and background processes die with it. Run the suite in chunks (`tests/harness`; `tests/tools` + `tests/runner/benchmark` + `tests/runner/predicates`; the ~190 `tests/runner/test_*.py` and `tests/test_*.py` files in 10–11 parts), HEAD copy and change copy in parallel, compare failure sets by id. A part that holds `tests/test_msca_dn_*` can run >140 s per copy: split it. A new test file absent from the HEAD copy makes pytest exit 4 there: filter the arguments per copy.
  - Edit with an exact-match, all-or-nothing read-modify-write that keeps each file's line endings (R9e-D18); write the change in a VM copy first, test it, then apply the same script to the connected folder and check equality modulo line endings. New `.py` files beside CRLF neighbours are written CRLF; decision records LF.
  - Run the secret scan on every evidence draft, and the old-ID guard; the decision record holds no scan pattern and no old id (F-R9-5).

## 3. R12a as it reads

1. **A test runs the collector against fixture stack outputs and confirms that every id it uses comes from them.**
2. **A test confirms that the collector refuses an output path inside the v1 tree.**
3. **The R3 old-ID test passes over the collector.**

## 4. Points to settle with the operator before writing code

1. **Language and shape.** (a) A Python module `tools/collect_evidence_v2.py` with a CLI (`py -3.10 -m tools.collect_evidence_v2 …`), the name the old-ID guard already expects; it runs AWS CLI commands through one injected runner, so the evidence keeps the CLI JSON shape of R4–R8 and the tests replace the runner with a fake; (b) the same in Python with boto3; (c) a PowerShell port of the old script. Proposal: (a) — pytest-testable (criteria 1–2), one language with the rest of `tools/`, and the operator's evidence so far is AWS CLI output.
2. **Inputs.** Ids only from the `<ticket>_outputs.json` files the contract names, located through `outputs_contract.json` (stack → ticket → path); account and Region from the parameter files' `ExpectedAccountId` / `ExpectedRegion`, cross-checked at run time against `sts get-caller-identity` and refused on a mismatch; model ids and routed Regions from `iam.json` / `host.json`. No id literal in the module. Proposal: so.
3. **The per-session host stack.** Its outputs file does not exist before R11 and changes with each recreate. (a) Host-dependent checks need an explicit `--host-outputs <path>` (default: the contract's `R11_outputs.json`); without it they are recorded as "not collected: host stack outputs absent", never guessed, and at run time every host id is first confirmed live (`describe-instances`, `describe-vpc-endpoints`) or the run refuses as stale; (b) refuse the whole run without host outputs. Proposal: (a), so the base-stack part can run any time.
4. **Host-side checks.** (a) Run from the workstation through SSM Run Command (`send-command` with a fixed script per check, then `get-command-invocation`), the scripts kept in the repository and asserted by tests; (b) a separate host-side mode run inside an SSM session. Proposal: (a) — reproducible from one command, and the R11 criterion already proves Run Command.
5. **F7 and DC-15 in-host tests.** (a) Written in R12a as host checks (code and offline tests only), run first in R12b; (b) left to R12b. Proposal: (a) — R12b's ticket expects them collected, and R12a is the code ticket.
6. **Output location and the v1 refusal (criterion 2).** The output path must resolve (symlinks resolved) inside `docs/infrastructure_security/evidence_v2/`; anything inside the v1 tree (`docs/infrastructure_security/evidence/`, `audit_package/`, register and worklog v1) is refused before any AWS call, as is any path outside `evidence_v2/`; an existing non-empty folder is refused (no overwrite). Files follow §7a naming (`<run>_<NN>_<short-name>.json|txt`), with a SHA-256 manifest written last. Proposal: so, with a test per refusal.
7. **Coverage map.** One declarative table: control id → check(s), each naming the contract outputs and parameters it uses, its command, its evidence file and whether it is account-, Region-, global- or host-scoped; every one of the 41 register v2 rows appears, with non-command rows marked (DC-22 N/A per R8, DC-38 R16/OD12, DC-39 document review, DC-40 Organization check). A test ties the table to register v2's row set. Proposal: so.
8. **Read-only by construction.** Only read verbs (`describe-*`, `get-*`, `list-*`, `lookup-events`, `simulate-principal-policy`, `get-caller-identity`) plus `ssm send-command` / `get-command-invocation` for host checks; the host scripts themselves are read-only except the F7 presigned PUT, which must fail; never `secretsmanager get-secret-value` from the workstation, and on the host the secret only as key names and SHA-256 (R8 digest precedent); the Converse check sends a fixed test string and records only that string back. A test asserts the verb allowlist over the table. Proposal: so.
9. **Criterion 1's test.** Fixture outputs and parameters with synthetic ids of the real shapes (not the real ones); the fake runner records every command; the test extracts every AWS-id-shaped token (account numbers, `arn:`, `vpc-`, `subnet-`, `sg-`, `vpce-`, `rtb-`, `i-`, key ids, bucket and trail names, model and profile ids, Region names) from every recorded command and script and asserts each is in the fixtures. A second test swaps the fixture ids and asserts the commands change with them. Proposal: so.
10. **After a run.** The collector runs the secret scan over its own output folder and exits non-zero on a finding; it never edits a file to pass. It exits non-zero on any AWS error other than an expected one (e.g. `AWSOrganizationsNotInUseException` for DC-40), and summarises per control: collected, not collected (reason), error. Proposal: so.
11. **Criterion 3 and the guard.** `py -3.10 -m tools.old_id_guard tools/collect_evidence_v2.py <host-scripts folder> <tests and fixtures>` CLEAN as step evidence; whether the collector's paths join the guard's default scope (a change to `tools/old_id_guard.py` and its test). Proposal: add them to the default scope, so every later guard run covers the collector.
12. **Evidence.** As R10: `evidence_v2/R12a/` with `STEPS.md`, `RUNLOG.md`, `R12a_<NN>_*`, `VERIFICATION.md`; baseline on the `starting R12a` commit; the R12a tests and the touched modules; full suite after, by id; old-ID guard over the default scope and the collector; secret scan last. Register v2: no row changes (a note that the collector exists, at most). Decision record `aws-redeployment-r12a-collector_<date>`. Proposal: so.
13. **Scope.** R12a makes no AWS call, not even read-only against the base stacks; does not touch the old collector or the v1 tree; does not change register rows; does not fix F-R10-1 (skill runtime failure reason) or F-R9-1. Proposal: confirm. (Option the operator may prefer: one read-only, no-cost run of the base-stack part against R4–R8 as extra evidence in R12a; it needs a sign-in and is not in the ticket.)
14. **R16 without R11 (raised 2026-10-28, separate from R12a).** R16's second criterion (DC-38 DEFERRED in register v2 with OD12 cited) needs nothing from R11 in substance, but R16 is blocked by R11 in the ticket list. Closing it now would be a recorded override of that dependency. Proposal: ask after R12a; not part of R12a.

## 5. Step sheet outline (suggestion)

`evidence_v2/R12a/STEPS.md`, workstation only.

1. Baseline: commit `close R10` and `starting R12a` first (or record the deviation); `git log -2` and status; versions; full suite → `R12a_01_baseline-pytest.txt`. Hand back.
2. The agent writes the collector, its host-check scripts, fixtures, tests and the decision record, and runs its subset and the chunked suite comparison in the VM copies.
3. Diff stat; the R12a tests, `tests/test_old_id_guard.py`, `tests/test_aws_iac_contract.py`, `tests/test_evidence_protocol_scaffold.py` → `R12a_03_*`; the old-ID guard over the collector → `R12a_03_old-id-guard-collector.txt`.
4. Full suite after → `R12a_04_full-pytest.txt`, compared by id.
5. Old-ID guard (default scope); secret scan last. Commit; confirm.

## 6. Files (expected)

| Path | What |
|---|---|
| `tools/collect_evidence_v2.py` | the collector (point 1) |
| `tools/collector_host_checks/` (or inside the module) | the fixed host-check scripts run through SSM (points 4, 5) |
| `tools/old_id_guard.py`, `tests/test_old_id_guard.py` | default scope extended (point 11 (a) only) |
| `tests/tools/test_collect_evidence_v2.py`, `tests/tools/fixtures/collector/` | tests and synthetic fixtures (points 6–10) |
| `docs/tier4_orchestration_state/decision_log/aws-redeployment-r12a-collector_<date>.json` | the §4 answers |
| `docs/infrastructure_security/evidence_v2/R12a/` | `STEPS.md`, `RUNLOG.md`, `R12a_<NN>_*`, `VERIFICATION.md` |
| `docs/infrastructure_security/aws_hardening_worklog_v2.md` | entries |
| `plans/aws_redeployment_tickets.md` | R12a ticked |

## 7. Done for R12a

Every `VERIFICATION.md` criterion PASS; the three ticket criteria PASS; the full suite shows no failure that is not in the R12a baseline (by id); the old-ID guard CLEAN over the default scope and the collector; secret scan CLEAN (last); worklog entry; the operator commits and confirms. Then tick R12a. R12b then needs only R11; R11 stays held until the operator decides it is needed (cost: §8 of the 2026-10-21 handoff, to be verified for eu-north-1 in R14).
