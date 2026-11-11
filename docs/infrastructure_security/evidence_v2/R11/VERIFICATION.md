# R11 — verification report

| Field | Value |
|---|---|
| Verified by / on | agent (Claude) / 2026-11-11 (round 1 before 19:30 UTC; round 1b ~20:55; steps 06–15 ~21:10–21:30; steps 17–22 ~22:10) |
| Step sheets | `STEPS.md` (steps 01–23) as amended by `STEPS_fix1.md` (F01–F05, and the amendment table for steps 06, 09, 14, 18), run as in `RUNLOG.md` |
| Decisions | `aws-redeployment-r11-host_2026-11-11` (R11-D1–D12, F-R11-1–6); OD9-r1 `aws-redeployment-od9-host-size-r1_2026-11-11` (operator confirmed 21:00 UTC) |
| Secret scan | Operator: step 23 run 1 and run 2 (after this report, last) → `CLEAN`, `exit=0`. Agent re-run over `evidence_v2/R11` after each edit → `CLEAN` |
| Old-ID guard | Operator: F04 and step 23 run 1 → `CLEAN` (20 ids) |
| Stacks | `proposal-orchestrator-host`, three lives. Round 2 (`r11-create-01`, `t3.medium`): 20:12:14–20:19:02, `ROLLBACK_COMPLETE`, deleted in F02. Round 2b first creation (`r11-fix1-create-01`): `CREATE_COMPLETE` 21:04:56, deleted in step 13. Recreation (`r11-create-02`): `CREATE_COMPLETE` 21:52:44, deleted in step 19. Each go recorded before execution in rounds 1b and 2b (21:00:40, 21:45:33); round 2's go was not |
| Cost | Hourly: six interface endpoints and one `c7i-flex.large` host per creation, plus round 2's endpoints for about seven minutes. Credits 199.25 USD before and after (billing delayed). R14 prices it |

Every check below was re-run by the agent on the saved files (`utf-8-sig`), by script, not taken from the
pasted output. Ids come from `R4_outputs.json`, `R5_outputs.json`, `R7_outputs.json`, `R11_outputs.json`
and `R11_17_outputs-recreated.json`; the Bedrock endpoint policy was compared with `host.json`; the DNS
answers were matched to the endpoint interfaces through each endpoint's ENI id.

## Criteria

| Step | Criterion | Evidence file | Status | Reason |
|---|---|---|---|---|
| 01–05 | Round 1 | `R11_01_*`–`R11_05_*` | PASS | `RUNLOG.md` round 1 (22 files). The `t3.medium` change set was later refused (step 06 round 2) |
| 06 (round 2) | `execute exit=0`, `CREATE_COMPLETE` | `R11_06_*` | FAIL, superseded | `Host` `CREATE_FAILED` 20:13:25, "not eligible for Free Tier"; rollback complete. Kept as evidence of the refusal (OD9-r1, R11-D12) |
| F01 | Plan, budget, identity | `R11_fix1_01_*` | PASS | FREE / ACTIVE, 199.25 USD; spend 0.478 of 10.0; three notifications OK; account 797661577394 |
| F02 | Rolled-back stack deleted; VPC as at step 03 | `R11_fix1_02_*` | PASS | `ROLLBACK_COMPLETE` → does not exist; only the S3 gateway endpoint; no interface, no instance |
| F03 | `c7i-flex.large` eligible and offered in eu-north-1a; dry run | `R11_fix1_03_*` | PASS | Six eligible types, no `t3.medium`; both types offered in eu-north-1a; `DryRunOperation`. F03d (credit option) also `DryRunOperation`, informational |
| F04 | Lint, guards, 260 tests | `R11_fix1_04_*` | PASS | cfn-lint 1.57.2 exit 0; both guards CLEAN; Python 3.10.6, 260 passed |
| F05 | Change set `r11-fix1-create-01` | `R11_fix1_05_*` | PASS | `CREATE_COMPLETE` / `AVAILABLE`; no capability; tag; parameters = `host.json` or defaults, `InstanceType` `c7i-flex.large`; image = step 03's; seven `Add` |
| 06 | `execute exit=0`; `CREATE_COMPLETE`; no failure | `R11_fix1_06_*` | PASS | Executed once 21:03:42; 24 events, none failed; `capabilities` null; tag `project` |
| 07 | Seven contract keys, no export, distinct ids | `R11_outputs.json` | PASS | Six `vpce-…` and `i-03308c50670917059` |
| 08 | Six interface endpoints: `available`, private DNS, one subnet, endpoint SG, one ENI (DC-01, DC-02, DC-03, DC-05) | `R11_08_vpc-endpoints.json` | PASS | All six services; ids equal `R11_outputs.json` |
| 08 | Bedrock endpoint policy = template (DC-04) | `R11_08_bedrock-endpoint-policy.json` | PASS | Two statements by `Sid`; `Allow`, `Principal` `*`, the two invoke actions, the 14 ARNs of `host.json`, `ArnEquals aws:PrincipalArn` = `RuntimeRoleArn`; nothing else |
| 08 | Seven interfaces, no public IP; groups (DC-07 attached) | `R11_08_network-interfaces.json` | PASS | Six `vpc_endpoint` with the endpoint SG; one `interface` on the host with the host SG |
| 09 | Host: `c7i-flex.large` (amended), no public IP, IMDSv2 hop 1, profile, no key (DC-14) | `R11_09_instance.json` | PASS | x86_64, eu-north-1a, step 03's image, `10.60.0.11`, one block device, tags `Name` and `project` |
| 09 | Root volume gp3, encrypted with the default EBS key, `deleteOnTermination` | `R11_09_root-volume.json` | PASS | gp3, encrypted, `deleteOnTermination` true, tag `project`. Key `key/3ac821af-…` = `alias/aws/ebs`, AWS-managed, `Enabled` (`R11_23a_ebs-default-key-resolved.json`, F-R11-6) |
| 09 | Profile associated (DC-14, DC-09) | `R11_09_profile-association.json` | PASS | `associated`, `InstanceProfileArn` |
| 09 | Credit specification | `R11_09_credit-specification.json` | Recorded (no criterion, amended) | `CpuCredits` `standard` (F-R11-2) |
| 10 | SSM `Online`; Run Command `Success` | `R11_10_*` | PASS | Amazon Linux 2023, agent 3.3.5700.0, IP = step 09's; output `R11_RUN_COMMAND_OK`, `x86_64`, no stderr |
| 11 | Private DNS, IMDS, identity, secret read (DC-02, DC-14, DC-09; DC-19–DC-21) | `R11_11_host-checks.json` | PASS | Six names resolve to the endpoint ENI addresses in `10.60.0.0/25`; `imdsv1_http=401`; token issued; profile ARN; caller the runtime role with session `i-03308c50670917059`; `aws-cli/2.38.0`; `secret_read=AWSCURRENT` |
| 12 | One Converse call (DC-37) | `R11_12_converse.json` | PASS | `call_utc=2026-11-11T21:08:57Z`, `converse_exit=0`, `reply=DEPLOY_OK`, runtime-role caller; no stderr |
| 13 | Runtime role: boundary and explicit deny (F1); delete | `R11_13_*` | PASS | ARN and boundary = `R5_outputs.json`; four policies = `R5_08_runtime-role-attached.json`; `delete exit=0`; stack does not exist |
| 14 | Deletion clean; base stacks and exports unchanged | `R11_14_*` | PASS (criterion corrected) | Only the S3 gateway endpoint; no interface; instance `terminated`; volume `NotFound`; stacks and 25 exports = step 03. Imports: no list names the host stack (corrected criterion, R11-D11) |
| 15 | Change set `r11-create-02` | `R11_15_*` | PASS | Parameters and changes = `R11_fix1_05_change-set.json` |
| 17 | Recreation `CREATE_COMPLETE`; new ids | `R11_17_*` | PASS | `execute exit=0`; 24 events, none failed; all seven ids differ from step 07's |
| 18 | Re-check | `R11_18_*` | PASS | As step 08 and 09 for the new ids; `c7i-flex.large`; same volume key as step 09; Run Command `Success`, DNS = the new ENI addresses |
| 19 | Delete; nothing left; base stacks unchanged | `R11_19_*` | PASS | `delete exit=0`; stack does not exist; no interface, instance or project volume; stacks = step 03 |
| 20 | CloudTrail `Converse` event, metadata only (DC-26, DC-37, F1) | `R11_20_*` | PASS | 21:08:58Z, `eu-north-1`, `AssumedRole`, runtime-role caller with the host's session, issuer = `RuntimeRoleArn`, `vpcEndpointId` = step 07's Bedrock endpoint, model = `TransportModelId`, no error; only the listed fields |
| 21 | Flow-log delivery (DC-08 note) | `R11_21_*` | PASS | ACTIVE / SUCCESS; 14 streams of R11 interfaces after 21:03:42; 50 events (the query limit). R5-D4 gap answered (F-R11-4) |
| 22 | Invocation logging unset (DC-28); no Bedrock log group (DC-29); credits | `R11_22_*` | PASS | `exit=0`, no configuration; `logGroups` `[]`; 199.25 USD |
| 23 | 260 passed; guards CLEAN; scan last | `R11_23_*`, `R11_23a_*` | PASS | Run 2 after this report: Python 3.10.6, 260 passed; old-ID guard and secret scan CLEAN, `exit=0`, scan last. Run 1 (before the report) had the same results |

## Ticket checklist

| Ticket criterion (from `plans/aws_redeployment_tickets.md`) | Status | Evidence |
|---|---|---|
| All endpoints show `available`. The host has no public IP. | PASS | `R11_08_vpc-endpoints.json`, `R11_18_vpc-endpoints.json`; `R11_09_instance.json`, `R11_18_instance.json`, both `*_network-interfaces.json` |
| A Run Command invocation returns `Success`. | PASS | `R11_10_run-command.json`, `R11_11_host-checks.json`, `R11_12_converse.json`, `R11_18_run-command.json` |
| The Converse call succeeds. CloudTrail shows the runtime role as caller, with the boundary attached (closes F1). | PASS | `R11_12_converse.json`; `R11_20_converse-events.json` (caller and issuer the runtime role, through the Bedrock endpoint); `R11_13_runtime-role.json`, `R11_13_runtime-role-attached.json` (boundary and explicit deny on that role) |
| DC-01, DC-02, DC-04, DC-05, DC-14, DC-26 and DC-37 are evidenced. | PASS | Register v2 rows updated 2026-11-11, with DC-03 and DC-07 (attachment halves), DC-09, and notes on DC-08, DC-19–DC-21, DC-28 |
| The stack deletes cleanly, leaves the base stack intact, and recreates from the templates. | PASS | `R11_13_*`, `R11_14_*` (corrected imports criterion), `R11_15_*`, `R11_17_*`, `R11_18_*`, `R11_19_*` |

## Done conditions (handoff §7a)

- [x] Every criterion above is PASS, except step 06 round 2 (superseded, R11-D12).
- [x] Register v2 updated (2026-11-11).
- [x] Worklog v2 entry 2026-11-11T22:15:00Z.
- [x] Step 23 run 2, with check 23a, after this report (2026-11-11): 260 passed, both CLEAN; F-R11-6 closed.
- [ ] Operator reviews `aws-redeployment-r11-host_2026-11-11` (R11-D11, R11-D12) and confirms R11 in session; the agent then ticks R11.

## Notes for later tickets

- **R12a / R12b:** no host exists now. A collector run needs a new creation with the operator's go; save its outputs and pass them with `--host-outputs`.
- **R14:** price `c7i-flex.large` and six interface endpoints per hour in eu-north-1, for 21:03:42 to the step 13 delete, 21:51:19 to the step 19 delete, and round 2's seven minutes. Credits were 199.25 USD before and after.
- **Contract:** add R11 as a consumer of `proposal-orchestrator-network-VpcId` in `outputs_contract.json` (R11-D7).
- **Endpoint policies:** the five supporting endpoints keep the AWS default policy (R11-D4).
