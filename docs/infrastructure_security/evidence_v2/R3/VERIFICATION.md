# R3 — verification report

| Field | Value |
|---|---|
| Verified by / on | agent (Claude) / 2026-10-23 |
| Step sheet | `STEPS.md` (steps 01–12), run in two rounds: 01–10 on 2026-10-22, 11–12 on 2026-10-23 (`RUNLOG.md`) |
| Secret scan | Operator: `py -3.10 -m tools.evidence_secret_scan docs/infrastructure_security/evidence_v2/R3` → `CLEAN`, `exit=0` (`R3_12_secret-scan.txt`). Agent re-run 2026-10-23 → `CLEAN` (exit 0), 23 `R3_*` files. |
| Old-ID guard | Operator `R3_11_old-id-guard.txt` → `CLEAN`; agent re-run 2026-10-23 over the default v2 scope (this report included) → `CLEAN` |

## Criteria

| Step | Criterion | Evidence file | Status | Reason |
|---|---|---|---|---|
| 01 | `accountPlanType` FREE; `accountPlanStatus` ACTIVE; credits ≥ 199.00; expiration starts 2027-04-19 | `R3_01_plan-state.json` | PASS | FREE, ACTIVE, 199.99 USD, `2027-04-19T09:00:47…` |
| 01 | Exactly one budget `My Monthly Cost Budget`, limit 10.0, spend < 8.5 | `R3_01_budgets.json` | PASS | One budget, limit `10.0`, spend `0.006` |
| 01 | Three notifications, each `OK` | `R3_01_budget-notifications.json` | PASS | ACTUAL 100, ACTUAL 85, FORECASTED 100, all `OK`; STOP rule not triggered |
| 02 | `Account` 797661577394; `Arn` starts `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/` | `R3_02_caller-identity.json` | PASS | As required (workstation, profile `po-r1`) |
| 03 | First line `cfn-lint 1.57.2`; last line `cfn-lint exit=0`; nothing between | `R3_03_cfn-lint.txt` | PASS | Exactly those two lines, over all six templates, `--regions eu-north-1`. **Exit condition 1.** |
| 04 | Non-empty; every entry `availability-zone`; at least one `available` | `R3_04_availability-zones.json` | PASS | eu-north-1a (eun1-az1), -1b (eun1-az2), -1c (eun1-az3); all `available`, `opt-in-not-required` |
| 05 | Six entries, each `Interface` with private DNS; non-empty zone intersection | `R3_05_endpoint-services.json` | PASS | bedrock-runtime, ec2messages, secretsmanager, ssm, ssmmessages, sts; each in all three zones. Chosen: **eu-north-1a** (first by name), written to `deploy/aws/parameters/network.json` as `AvailabilityZone` |
| 06 | One entry, `com.amazonaws.eu-north-1.s3`, owner `AWS`, `create-complete`, id `pl-` | `R3_06_s3-prefix-list.json` | PASS | `pl-c3aa4faa`; written to `network.json` as `S3PrefixListId`. Not the old us-east-1 list (old-ID guard clean) |
| 07 | One `found` entry with `ami-` value; `invalid` empty | `R3_07_al2023-ami-parameter.json` | PASS | `ami-0111419d42d14a400` (modified 2026-10-22); `invalid` `[]`. The host template's `LatestAmiId` default resolves in eu-north-1 |
| 08 | Six lines, each `exit=0` | `R3_08_validate-exit.txt` | PASS | network, iam, kms, audit, secret, host: all `exit=0` |
| 08 | `Parameters` key set = template's declared parameters; `Description` present; no `Capabilities`; no error | `R3_08_validate-<stack>.json` (6) | PASS | Agent compared each file with the parsed template: all six match; `Description` present; no `Capabilities` or other keys. CloudFormation answers in eu-north-1 and no SCP refused it |
| 09 | `[]` | `R3_09_stacks.json` | PASS | `[]` |
| 09 | `Exports` is `[]` | `R3_09_exports.json` | PASS | `{"Exports": []}` |
| 10 | FREE, ACTIVE; credits equal to step 01 | `R3_10_plan-state-after.json` | PASS | 199.99 USD, unchanged |
| 11 | Header `Python 3.10`; last line `N passed`, no failed / error / skipped | `R3_11_pytest.txt` | PASS | `platform win32 -- Python 3.10.6`; `105 passed in 1.48s`; 105 `PASSED` lines, none failed or skipped. Run after `network.json` was filled, so the evidence-bound parameter tests ran in their strict form |
| 11 | `CLEAN: 6 template(s)`; `exit=0` | `R3_11_template-guard.txt` | PASS | As required |
| 11 | `CLEAN: no old-account id in default v2 scope (20 ids checked)`; `exit=0` | `R3_11_old-id-guard.txt` | PASS | As required |
| 12 | `CLEAN: docs/infrastructure_security/evidence_v2/R3`; `exit=0` | `R3_12_secret-scan.txt` | PASS | As required |

## Ticket checklist

| Ticket criterion (from `plans/aws_redeployment_tickets.md`) | Status | Evidence |
|---|---|---|
| The templates lint cleanly on the workstation. | PASS | `R3_03_cfn-lint.txt` (cfn-lint 1.57.2, pinned in `deploy/aws/requirements-lint.txt`, own venv `.venv-lint`); `R3_08_validate-*.json` (service-side parse) |
| The old-ID test fails on a planted old id and passes on the real tree. | PASS | `R3_11_pytest.txt`: `test_guard_refuses_each_planted_old_id` (20 cases, one per old id), `test_real_tree_is_clean`; `R3_11_old-id-guard.txt`. The test also checks that the guard covers every old id of handoff §9 and the F7 rule, matches exactly (not by prefix) and never prints the id |
| The stack outputs are named, so later tickets and the evidence collector can read ids from them. | PASS | `deploy/aws/outputs_contract.json` (6 stacks, 32 outputs, export names `proposal-orchestrator-<stack>-<Key>`, consumers per output); `tests/test_aws_iac_contract.py` (template Outputs ⊆ contract while the skeleton placeholder exists, = contract once filled) |
| Parameters cover account id, Region, AZ, model list, bucket names with account suffix; every resource tagged `project=proposal-orchestrator` (ticket text) | PASS | `ExpectedAccountId` / `ExpectedRegion` with a `DeployTarget` rule; `AvailabilityZone`; `InferenceProfileArns`, `FoundationModelArns`, `RoutedRegions`; bucket names derived `${ProjectName}-<kind>-${AWS::AccountId}`; tag enforced by `tools/aws_template_guard.py` and the change-set stack tag. Values checked against R1 evidence, OD1, OD7 and R3 evidence by `tests/test_aws_iac_contract.py` |
| Stack layout (OD6) | PASS, revised | Six stacks per `aws-redeployment-od6-stack-layout-r3_2026-10-22` (successor to OD6, operator-decided 2026-10-22) instead of the ticket text's two |

## Done conditions (handoff §7a)

- [x] Every criterion above is PASS.
- [x] Register v2 updated for: none. No register v2 row names R3 (R3 handoff §4); no guard test touches a control.
- [x] Worklog v2 entry: 2026-10-23T14:45:00Z (verification), after 2026-10-22T14:40:00Z (written).
- [ ] Operator confirmed in session on `<YYYY-MM-DD>`.

## Notes for later tickets

- R4: `network.json` holds `AvailabilityZone` = `eu-north-1a` and `S3PrefixListId` = `pl-c3aa4faa`, both from this folder. F-OD6r3-2: R4's first change set shows whether CloudFormation evaluates the `DeployTarget` rule's pseudo-parameter references; the deploy step's caller-identity check covers the account either way.
- R6, R8: `AdminRoleArn` carries the `/managed/` path (F-OD6r3-1).
- Each filling ticket removes `SkeletonPlaceholder`; the contract test then requires exactly the contract outputs.
- Outside R3: `tests/test_evidence_protocol_scaffold.py::test_register_v2_lists_all_41_controls_as_not_started` has failed since R2 set DC-36 to `IN_PROGRESS` (commit `690f90c`). It is a stale E0 criterion, reported to the operator; not run in step 11.

## Follow-up

none
