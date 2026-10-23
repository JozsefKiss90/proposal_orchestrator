# R4 — verification report

| Field | Value |
|---|---|
| Verified by / on | agent (Claude) / 2026-10-24 (round 1 read 2026-10-23 ~22:22 UTC before execution; round 2 read 2026-10-23 ~22:45 UTC) |
| Step sheet | `STEPS.md` (steps 01–10), run in three rounds: 01–04, then 05–09 after the operator's go on the change set, then 10 (`RUNLOG.md`) |
| Secret scan | Operator: step 10, `R4_10_secret-scan.txt` → `CLEAN`, `exit=0`. Agent re-run in the device shell after round 2 → `CLEAN`. |
| Old-ID guard | Operator: step 10, `R4_10_old-id-guard.txt` → `CLEAN` (20 ids). Agent re-run after round 2 over the default v2 scope (this report included) → `CLEAN`. |
| Stack | `proposal-orchestrator-network`, created 2026-10-23T22:20:45Z (change set `r4-create-01`, executed ~22:30Z), `CREATE_COMPLETE`. Nothing with an hourly cost. Credits 199.99 USD before and after. |

Every check below was re-run by the agent on the saved files (`utf-8-sig`), not taken from the
operator's pasted terminal output.

## Criteria

| Step | Criterion | Evidence file | Status | Reason |
|---|---|---|---|---|
| 01 | `FREE`, `ACTIVE`, credits ≥ 199.00, expiration starts 2027-04-19 | `R4_01_plan-state.json` | PASS | FREE, ACTIVE, 199.99 USD, `2027-04-19T09:00:47…`. First attempt ran with an expired session and was repeated after `aws login --profile po-r1` (`RUNLOG.md`) |
| 01 | One budget `My Monthly Cost Budget`, limit 10.0, spend < 8.5 | `R4_01_budgets.json` | PASS | One budget, limit `10.0`, spend `0.006` |
| 01 | Three notifications, each `OK` | `R4_01_budget-notifications.json` | PASS | ACTUAL 100, ACTUAL 85, FORECASTED 100, all `OK`; STOP rule not triggered |
| 02 | `Account` 797661577394; `Arn` starts `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/` | `R4_02_caller-identity.json` | PASS | As required (workstation, profile `po-r1`) |
| 03 | `cfn-lint 1.57.2` / `cfn-lint exit=0`, nothing between | `R4_03_cfn-lint.txt` | PASS | Exactly those two lines, all six templates, `--regions eu-north-1` |
| 03 | `CLEAN: 6 template(s)`; `exit=0` | `R4_03_template-guard.txt` | PASS | As required; the guard now also refuses `AWS::EC2::Route` (R4-D4) |
| 03 | `CLEAN … (20 ids checked)`; `exit=0` | `R4_03_old-id-guard.txt` | PASS | As required |
| 03 | `Python 3.10`; `N passed`, nothing failed/error/skipped | `R4_03_pytest.txt` | PASS | `platform win32 -- Python 3.10.6`; `121 passed in 1.33s` over `test_aws_iac_contract.py`, `test_aws_template_guard.py`, `test_aws_network_template.py`, `test_old_id_guard.py` |
| 04 | `Id` / `StackId` ARNs in eu-north-1, account 797661577394, change set `r4-create-01`, stack `proposal-orchestrator-network` | `R4_04_create-change-set.json` | PASS | Both prefixes as required |
| 04 | `CREATE_COMPLETE` / `AVAILABLE` / `CREATE`; `Capabilities []`; `project` tag; seven parameters; **exactly eight** `Add` entries with the listed ids and types; nothing hourly | `R4_04_change-set.json` | PASS | Agent compared the `{LogicalResourceId: ResourceType}` map with the expected one: equal, all `Add`. Parameters: ExpectedAccountId 797661577394, ExpectedRegion eu-north-1, AvailabilityZone eu-north-1a, S3PrefixListId pl-c3aa4faa, VpcCidr 10.60.0.0/24, PrivateSubnetCidr 10.60.0.0/25, ProjectName proposal-orchestrator. Operator confirmed the go in session before step 05. **F-OD6r3-2:** CloudFormation accepted `Ref AWS::AccountId` / `AWS::Region` inside the `DeployTarget` rule at change-set creation (no error, `StatusReason` null) — **Confirmed** that the rule is accepted and passes when the values match; **Inferred** (not shown by R4) that a mismatch would be refused, since no mismatch was tried. The caller-identity check (step 02) covers the account either way. **Exit condition 1, first half.** |
| 05 | `execute-change-set exit=0` | `R4_05_execute-exit.txt` | PASS | As required |
| 05 | `status` `CREATE_COMPLETE`; `project` tag | `R4_05_stack-status.json` | PASS | `CREATE_COMPLETE`, `reason` null, tag present, created `2026-10-23T22:20:45.410000+00:00` (the change-set time; the stack object exists from change-set creation) |
| 05 | `CREATE_COMPLETE` for all eight logical ids and the stack; no `_FAILED`, no `ROLLBACK` | `R4_05_stack-events.json` | PASS | All nine ids reached `CREATE_COMPLETE`; no failed or rollback event. **Exit condition 1, second half** (first real stack creation in the account: `cloudformation:CreateStack` is not SCP-denied in eu-north-1 — F-OD1r1-4 now Confirmed) |
| 06 | Seven outputs, the contract keys, `ExportName` `proposal-orchestrator-network-<Key>`, id prefixes | `R4_outputs.json` | PASS | Key set equals the contract; every export name as required; `vpc-`, `subnet-`, `eu-north-1a`, `rtb-`, `sg-`, `sg-`, `vpce-`. **Exit condition 1: "its outputs are saved."** |
| 07 | One VPC = output, `10.60.0.0/24`, `available`, `IsDefault` false, `Name`/`project` tags, three `aws:cloudformation:*` tags | `R4_07_vpc.json` | PASS | As required; `Name` `proposal-orchestrator-vpc` |
| 07 | `EnableDnsSupport.Value` true | `R4_07_vpc-dns-support.json` | PASS | `true` (**PL-8**) |
| 07 | `EnableDnsHostnames.Value` true | `R4_07_vpc-dns-hostnames.json` | PASS | `true` (**PL-8**) |
| 07 | `InternetGateways` `[]` | `R4_07_internet-gateways.json` | PASS | `[]` (**exit condition 2**, OD3) |
| 07 | `NatGateways` `[]` | `R4_07_nat-gateways.json` | PASS | `[]` |
| 07 | One subnet in the VPC, `10.60.0.0/25`, `eu-north-1a`, `MapPublicIpOnLaunch` false, `AssignIpv6AddressOnCreation` false, `available` | `R4_07_subnet.json` | PASS | As required; zone id `eun1-az1` (the R3 choice) |
| 07 | One route table in the VPC; one association = the subnet, not main; **exactly two routes**: `10.60.0.0/24` → `local` and `pl-c3aa4faa` → the endpoint; no `igw-`/`nat-`/`eni-`/`pcx-`/`0.0.0.0/0` | `R4_07_route-table.json` | PASS | Two routes, both `active`, the prefix-list route's `GatewayId` = `vpce-0770a3016be1317ef`; association `subnet-018cd285bbe5cbdaf`, `Main` false; none of the forbidden strings in the file (**exit condition 2**, **DC-06**) |
| 07 | Host SG: no ingress; egress `tcp` 443 to `pl-c3aa4faa` and to the endpoint SG. Endpoint SG: ingress `tcp` 443 from the host SG only; egress one entry `-1` to `127.0.0.1/32` with the placeholder description. `Name` and `project` tags | `R4_07_security-groups.json` | PASS | As required. Note: `describe-security-groups` merges the host SG's two egress rules into **one** `IpPermissionsEgress` entry (same protocol and port) carrying both `PrefixListIds` `[pl-c3aa4faa]` and `UserIdGroupPairs` `[sg-03cd8ea2cf5dae72c]`; the rule-level file below shows them as two rules. The step-sheet wording "two entries" is read at rule level. Group names are CloudFormation-generated (`proposal-orchestrator-network-HostSecurityGroup-…`, `…-EndpointSecurityGroup-…`); `Name` tags `proposal-orchestrator-host-sg`, `proposal-orchestrator-endpoint-sg` |
| 07 | Exactly four rules; the three real ones `tcp` 443; the fourth the loopback placeholder; no `0.0.0.0/0` or `::/0` | `R4_07_security-group-rules.json` | PASS | Four rules: host egress → `pl-c3aa4faa`; host egress → endpoint SG; endpoint ingress ← host SG; endpoint egress `-1` → `127.0.0.1/32`. No open CIDR anywhere (**DC-03 and DC-07, security-group halves**; R4-D1 placeholder as decided) |
| 07 | One Gateway endpoint, `com.amazonaws.eu-north-1.s3`, `available`, on the one route table; policy: one Allow statement, Principal `*`, actions exactly GetObject/ListBucket/GetBucketLocation, the deploy bucket and its objects, both account conditions; no other bucket | `R4_07_vpc-endpoint.json` | PASS | As required: resources `arn:aws:s3:::proposal-orchestrator-deploy-797661577394` and `…/*`; `StringEquals` `aws:ResourceAccount` and `aws:PrincipalAccount` = 797661577394. No AL2023, trail or SSM bucket named (OD9; R4-D3). (**Exit condition 3**, F7, **DC-05 S3 half**) |
| 07 | Seven exports of this stack, names and values equal to `R4_outputs.json` | `R4_07_exports.json` | PASS | Seven, all `ExportingStackId` of this stack, name/value map equal to the outputs |
| 08 | Before: exactly two rules on the default group (not the host or endpoint group): egress `-1` `0.0.0.0/0`, ingress `-1` self-referencing | `R4_08_default-sg-before.json` | PASS | `sg-0a2fca76dd2129439`: egress `-1` `0.0.0.0/0`; ingress `-1` referencing itself — AWS's two default rules |
| 08 | Revoke egress: `Return` true, the egress rule id | `R4_08_default-sg-revoke-egress.json` | PASS | `sgr-040367bf59df45ece` revoked |
| 08 | Revoke ingress: `Return` true, the ingress rule id | `R4_08_default-sg-revoke-ingress.json` | PASS | `sgr-04a111493bce30032` revoked |
| 08 | After: `SecurityGroupRules` `[]` | `R4_08_default-sg-after.json` | PASS | `[]` (**R4-D2**, lasting rule) |
| 08 | One group `default`, in the VPC, `IpPermissions` `[]`, `IpPermissionsEgress` `[]` | `R4_08_default-sg.json` | PASS | As required; nothing attached to it |
| 09 | `FREE`, `ACTIVE`, credits equal to step 01 | `R4_09_plan-state-after.json` | PASS | 199.99 USD, unchanged |
| 10 | `CLEAN: docs/infrastructure_security/evidence_v2/R4`; `exit=0` | `R4_10_secret-scan.txt` | PASS | As required (operator, 2026-10-23 ~22:50 UTC, over the finished folder incl. this report); agent re-run after round 2 also CLEAN |
| 10 | `CLEAN … (20 ids checked)`; `exit=0` | `R4_10_old-id-guard.txt` | PASS | As required; operator's `pytest` over the five test files (E0 scaffold + four AWS files): `143 passed`, Python 3.10.6 |

## Ticket checklist

| Ticket criterion (from `plans/aws_redeployment_tickets.md`) | Status | Evidence |
|---|---|---|
| The stack deploys, and its outputs are saved. | PASS | `R4_04_change-set.json` (read before execution), `R4_05_stack-status.json` `CREATE_COMPLETE`, `R4_05_stack-events.json`, `R4_outputs.json` (seven exported ids), `R4_07_exports.json` |
| The route table shows no `igw-` or `nat-` target, and the VPC has no Internet Gateway. | PASS | `R4_07_route-table.json` (two routes: `local`, `pl-c3aa4faa` → `vpce-…`), `R4_07_internet-gateways.json` `[]`, `R4_07_nat-gateways.json` `[]` |
| The S3 endpoint policy restricts by resource account and names the project buckets. It admits the AL2023 repository buckets only if OD9 added them. | PASS | `R4_07_vpc-endpoint.json`: `aws:ResourceAccount` (and `aws:PrincipalAccount`) = 797661577394; the deploy bucket and its objects, read-only; no AL2023 bucket (OD9 added none). The trail bucket is not named: CloudTrail writes service-side (R4-D3). The runtime role cannot be named yet (R5); R5 and R7 narrow further |
| DC-06 and PL-8 are evidenced, together with the security-group halves of DC-03 and DC-07. DC-07's wording is corrected in register v2. | PASS | DC-06: `R4_07_route-table.json`; PL-8: `R4_07_vpc-dns-support.json`, `R4_07_vpc-dns-hostnames.json`; DC-03 / DC-07 halves: `R4_07_security-groups.json`, `R4_07_security-group-rules.json` (and `R4_08_default-sg-after.json`: the VPC's default group carries no rule). Register v2: DC-07 wording corrected (host egress to the endpoint SG **and** the S3 prefix list), DC-03 wording carries the placeholder note (R4-D1); DC-05 S3 half `IN_PROGRESS` |

## Done conditions (handoff §7a)

- [x] Every criterion above is PASS.
- [x] Register v2 updated for DC-03, DC-05, DC-06, DC-07, PL-8 (2026-10-24).
- [x] Worklog v2 entry: 2026-10-24T00:55:00Z (verification), after 2026-10-24T00:40:00Z (template, decisions, step sheet).
- [x] Operator confirmed in session on 2026-10-24 (after committing R4 as `5819488`, 45 files, 143 tests passed).

## Notes for later tickets

- **Ids:** `R4_outputs.json` is the source. VpcId `vpc-0f33f9ced5a78b09f`; PrivateSubnetId `subnet-018cd285bbe5cbdaf` (eu-north-1a / eun1-az1); PrivateRouteTableId `rtb-043f4e86aa0b174e2`; HostSecurityGroupId `sg-0c4e5657a1bd246ff`; EndpointSecurityGroupId `sg-03cd8ea2cf5dae72c`; S3GatewayEndpointId `vpce-0770a3016be1317ef`. The default security group of the VPC is `sg-0a2fca76dd2129439` and carries no rule (R4-D2); R12a checks it stays so.
- **R5–R8, R11** import by export name `proposal-orchestrator-network-<Key>`; an exported value cannot change while imported (OD6-r3-layout consequence).
- **R7:** the deploy bucket must be named exactly `proposal-orchestrator-deploy-797661577394`, since the endpoint policy already names it; flow logs go on `subnet-018cd285bbe5cbdaf`.
- **R11:** attach `sg-03cd8ea2cf5dae72c` to the six interface endpoints and `sg-0c4e5657a1bd246ff` to the host; that closes DC-03 and DC-07. If Run Command fails for want of the SSM Agent's regional S3 buckets, that ticket adds a statement to the endpoint policy by an UPDATE change set (R4-D3 known gap), never by widening the security groups.
- **R12a:** add the default-security-group check (zero rules on the `default` group of the VpcId in `R4_outputs.json`).
- **F-OD6r3-2:** accepted at change-set creation; enforcement on a mismatch stays Inferred. No template change needed.
- **F-OD1r1-4** (`cloudformation:CreateStack` allowed in eu-north-1): now Confirmed by this stack.

## Follow-up

none
