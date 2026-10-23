# AWS redeployment: handoff for R4 (network base stack)

| Field | Value |
|---|---|
| Date | 2026-10-23 |
| Branch at writing | `msca-dn-pre-eval` at `f5d8d2a` (R3 committed as `be3198f`; the "Close R3" commit, which ticks R3 in the tickets file, `VERIFICATION.md` and worklog v2, is the operator's to make if `git log` does not show it yet) |
| For | The agent that runs ticket R4 with the operator in a new session |
| Read first | `CLAUDE.md`; `plans/aws_redeployment_tickets.md` (inherited constraints at the top, R4; R7, R11, R12a for what consumes R4's outputs); `plans/aws_redeployment_handoff_2026-10-21.md` §4 F3, F7, F10, §5 OD3, OD4, OD9, §7, §7a; `plans/aws_redeployment_r2_handoff_2026-10-21.md` §2 (how the operator works) and §2 of this file; `docs/tier4_orchestration_state/decision_log/aws-redeployment-od6-stack-layout-r3_2026-10-22.json`; `deploy/aws/README.md`; `docs/infrastructure_security/evidence_v2/R3/VERIFICATION.md` |
| Decision records in force | `docs/tier4_orchestration_state/decision_log/`: `aws-redeployment-operator-decisions_2026-10-21` (R0), `aws-redeployment-od1-region-r1_2026-10-21`, `aws-redeployment-od11-admin-identity-r2_2026-10-21`, `aws-redeployment-r1-baseline-deviations_2026-10-21`, `aws-redeployment-od7-model-set_2026-10-21`, `aws-redeployment-od6-stack-layout-r3_2026-10-22` |
| Status | E0, R0, R1, R2, R3 done. Frontier: **R4**, R5, R12a, R9, R9e, R10. R4 is the **first real stack creation** in this account. R7 and R11 wait for R4. |

## 1. Facts that govern R4

| Fact | Record / evidence |
|---|---|
| Account `797661577394`, Free plan, ~200 USD credits; everything regional in **eu-north-1** (the only Region the AWS-managed SCPs allow). | OD1-r1; `evidence_v2/R3/R3_10_plan-state-after.json` (199.99 USD on 2026-10-22) |
| Six stacks; R4 fills **`proposal-orchestrator-network`** (`deploy/aws/templates/10-network.yaml`), the first of the five exporting base stacks. | OD6-r3; `deploy/aws/outputs_contract.json` |
| Deploy by change set: `create-change-set` → `describe-change-set` saved as evidence → operator reads it → `execute-change-set`; stack tag `project=proposal-orchestrator`. No `--capabilities` needed (no IAM resource). | OD6-r3-deploy; `deploy/aws/README.md` "Deploying a stack" |
| `deploy/aws/parameters/network.json` is complete: `ExpectedAccountId` 797661577394, `ExpectedRegion` eu-north-1, `AvailabilityZone` **eu-north-1a** (eun1-az1), `S3PrefixListId` **pl-c3aa4faa**. `VpcCidr` 10.60.0.0/24 and `PrivateSubnetCidr` 10.60.0.0/25 are template defaults. | `evidence_v2/R3/R3_05_endpoint-services.json`, `R3_06_s3-prefix-list.json`; checked by `tests/test_aws_iac_contract.py` |
| The seven outputs R4 must add are fixed, with exports `proposal-orchestrator-network-<Key>`: `VpcId`, `PrivateSubnetId`, `PrivateSubnetAz`, `PrivateRouteTableId`, `HostSecurityGroupId`, `EndpointSecurityGroupId`, `S3GatewayEndpointId`. Once `SkeletonPlaceholder` is removed, the contract test requires exactly these. | `deploy/aws/outputs_contract.json` |
| **F-OD6r3-2 (Inferred):** cfn-lint accepts `Ref AWS::AccountId` / `AWS::Region` inside the `DeployTarget` rule, but whether CloudFormation evaluates it at change-set creation is unproven. R4's first change set is that proof. If CloudFormation rejects the rule, stop, record the error verbatim, and settle with the operator (drop the rule and rely on the caller-identity check, or a successor record) before changing the template. | OD6-r3 known_gaps |
| `cloudformation:CreateStack` not SCP-denied in eu-north-1 is **Inferred** (F-OD1r1-4); R3 showed `validate-template` answers. R4 is the first real proof. | `evidence_v2/R3/R3_08_validate-*.json` |
| OD9 adds **no** AL2023 package-repository buckets (the host installs from the offline bundle, F10 / ADR-001 D8), so the S3 gateway endpoint policy admits only this account's project buckets. | R0 OD9; handoff F7 |
| The admin role ARN carries its path (`role/managed/AccountFullAccessRole`). R4 has no policy that names it, but do not write the path-less form anywhere. | F-OD6r3-1 |
| Template rules enforced by `tools/aws_template_guard.py`: no IGW / egress-only IGW / NAT / EIP / gateway attachment; no `0.0.0.0/0` or `::/0` anywhere; project tag on every taggable resource; no "temporary"/"validation" in ids, names, descriptions; no Region literal outside a parameter default; no account literal; ≤ 51,200 bytes. | `tools/aws_template_guard.py`, `tests/test_aws_template_guard.py` |

## 2. How the operator works (additions from R3)

Everything in the R2 handoff §2 still holds, with these changes measured in R3:

- **The operator now runs everything from PowerShell in the VS Code terminal on the workstation**,
  repository root, `--profile po-r1` (after `aws login --profile po-r1`), every regional command with
  `--region eu-north-1`. Evidence lands directly in `docs\infrastructure_security\evidence_v2\R4\`; no
  CloudShell zip round-trip. Give CloudShell forms only as a fallback.
- **`$E` must be set in every new PowerShell window** (`$E = "docs\infrastructure_security\evidence_v2\R4"`).
  In R3, a new window left it empty and `Out-File` targeted `C:\` (access denied). Put the line at
  the top of each step that writes a file, or remind the operator at the start of every round.
- The lint venv `.venv-lint` may be active in the operator's window. Tests must run with plain
  `py -3.10` after `deactivate`; lint runs with `.\.venv-lint\Scripts\cfn-lint.exe`.
- Windows PowerShell `Out-File -Encoding utf8` writes **UTF-8 with BOM**; read evidence with
  `utf-8-sig` (the R3 tests and `tools.evidence_secret_scan` already do).
- Two rounds worked well: AWS steps, hand back, agent edits from evidence, then test and scan steps.
- **Agent-side lesson:** one `device_commit_files` call in R3 wrote a stale copy of a file. After
  delivering files to the operator's folder, compare `sha256sum` on both sides, or edit in place
  with `device_bash`. The agent still cannot run `git commit`; the operator commits.

## 3. R4 as it reads

Ticket exit conditions:

1. **The stack deploys, and its outputs are saved** (`R4_outputs.json`, from `describe-stacks
   … --query "Stacks[0].Outputs"`).
2. **The route table shows no `igw-` or `nat-` target, and the VPC has no Internet Gateway.**
3. **The S3 endpoint policy restricts by resource account and names the project buckets.** It admits
   the AL2023 repository buckets only if OD9 added them (it did not).
4. **DC-06 and PL-8 are evidenced, together with the security-group halves of DC-03 and DC-07.**
   DC-07's wording is corrected in register v2 (it still reads "to the endpoint SG only"; the host SG
   also has 443 to the S3 prefix list). Register v2 also assigns the S3 half of DC-05 to R4.

What the template must hold (ticket R4, handoff §6 R4, F3, F7):

- VPC `VpcCidr`, `EnableDnsHostnames` and `EnableDnsSupport` true, no Internet Gateway (OD3).
- One private subnet in `AvailabilityZone`, `PrivateSubnetCidr`, `MapPublicIpOnLaunch` false (OD4).
- One route table associated with that subnet; its only routes are `local` and the S3 prefix-list
  route the gateway endpoint adds.
- Host SG: egress TCP 443 to the endpoint SG and to `S3PrefixListId`; nothing else.
- Endpoint SG: ingress TCP 443 from the host SG only; **no egress**.
- S3 gateway endpoint on that route table, with a restrictive policy (F7).
- `project` tag (and a `Name` tag) on every taggable resource; the seven contract outputs with
  exports; `SkeletonPlaceholder` removed.

## 4. Points to settle with the operator before writing the template

- **Removing default egress (CloudFormation behaviour to verify against the
  `AWS::EC2::SecurityGroup` reference page before relying on it).** A security group created without
  an egress rule gets AWS's default allow-all egress, which the template guard forbids and DC-03
  forbids for the endpoint SG. Proposal: give the endpoint SG one inline placeholder egress rule
  that matches nothing usable (AWS's documented pattern is `IpProtocol: "-1"`, `CidrIp: 127.0.0.1/32`),
  which replaces the default rule. Give the host SG its S3 prefix-list egress inline, and its egress
  to the endpoint SG as a standalone `AWS::EC2::SecurityGroupEgress`. The endpoint SG's ingress
  from the host SG goes inline. This avoids a circular reference between the two groups and still
  removes both default rules. Confirm with the operator that a 127.0.0.1/32 placeholder is
  acceptable evidence for "no egress" (describe-security-groups will show that one rule), or
  choose another way.
- **The VPC's default security group.** A new VPC comes with a default SG that allows all egress
  and self-ingress. Nothing will use it, but it is attachable. CloudFormation cannot change it.
  Options: (a) leave it and record it as unattached in evidence; (b) an operator CLI step after
  the stack is created that revokes its rules (`revoke-security-group-ingress/egress` on the
  `GroupId` from `describe-security-groups --filters Name=vpc-id,… Name=group-name,Values=default`),
  evidenced before and after. Proposal: (b). It is cheap, and DC-06 / DC-07 then hold for every SG
  in the VPC. Record the choice in RUNLOG and VERIFICATION. A decision record is needed only if the
  operator wants a lasting rule.
- **S3 gateway endpoint policy.** Proposal: one Allow statement, `Principal: "*"`, actions limited
  to what the host needs on the deploy bucket (`s3:GetObject`, `s3:ListBucket`, plus
  `s3:GetBucketLocation` if the CLI needs it), resources
  `arn:${AWS::Partition}:s3:::${ProjectName}-deploy-${AWS::AccountId}` and `…/*`. Add
  `Condition: StringEquals: aws:ResourceAccount: ${AWS::AccountId}` and
  `aws:PrincipalAccount: ${AWS::AccountId}`. The runtime role does not exist yet (R5 follows R4),
  so the policy cannot name it. R5's role policy and R7's bucket policy narrow it further. Whether
  the trail bucket belongs in it: CloudTrail writes service-side, not through the endpoint, so
  propose leaving it out. Whether the SSM agent needs its regional S3 buckets for Run Command is
  unknown; propose leaving them out and letting R11 show it (fail-closed).
- **Does R4 need a guard-test extension?** Candidates: no `AWS::EC2::Route` resource at all (only
  the gateway endpoint adds a route), and the endpoint policy's resources all end in
  `${AWS::AccountId}`. Cheap, in `tests/` next to the R3 tests. Check
  `UNTAGGABLE_TYPES` in `tools/aws_template_guard.py` against the CloudFormation reference before
  adding any type. Let cfn-lint tell you whether `AWS::EC2::VPCEndpoint` takes `Tags`.
- **Evidence for register v2.** Which rows R4 moves and to what: DC-06, PL-8 → `VERIFIED_PASS` if
  the evidence holds. DC-03, DC-07 → `IN_PROGRESS` (the SG half; attachment is R11). DC-05 (S3 half)
  → `IN_PROGRESS`. Plus the DC-07 wording fix. The E0 test now checks that every status is
  defined and that `VERIFIED_PASS` names an `evidence_v2/` path.

## 5. Step sheet outline (suggestion)

`evidence_v2/R4/STEPS.md` from `_templates/`, PowerShell first:

1. Session-start check (R1-D2): plan state, budgets, notification states; STOP rule as in R3.
2. Caller identity.
3. Lint (`cfn-lint` via `.venv-lint`), template guard, old-ID guard and the R3/R4 tests on the
   filled template, before anything is created.
4. `create-change-set` (CREATE), `wait change-set-create-complete`, `describe-change-set` →
   `R4_04_change-set.json`. **The operator reads it and confirms in session** that it lists exactly
   the expected resources and nothing with an hourly cost. This is also where F-OD6r3-2 shows.
5. `execute-change-set`, `wait stack-create-complete`, `describe-stack-events` (on failure:
   stop, save the events, do not retry before the stack in `ROLLBACK_COMPLETE` is deleted with the
   operator's go).
6. `describe-stacks` Outputs → `R4_outputs.json`.
7. Read-only evidence, ids **only from `R4_outputs.json`**: `describe-vpcs` and
   `describe-vpc-attribute` for both DNS attributes (PL-8); `describe-internet-gateways` and
   `describe-nat-gateways` filtered by the VPC (both empty); `describe-subnets` (zone,
   `MapPublicIpOnLaunch` false); `describe-route-tables` (only `local` and the `pl-` route, the
   association); `describe-security-groups` and `describe-security-group-rules` for both groups
   (DC-03, DC-07 halves); `describe-vpc-endpoints` with the policy document (F7).
8. Default-SG handling per §4 (before/after evidence), if chosen.
9. Session-end credits; then tests, guards and secret scan over `evidence_v2/R4`.

Nothing in R4 has an hourly cost. VPC, subnet, route table, security groups and the S3 gateway
endpoint are free. Say so in the step sheet's header, and still read the change set before
executing it.

## 6. Files

| Path | What |
|---|---|
| `deploy/aws/templates/10-network.yaml` | Filled: resources, Outputs with exports; `SkeletonPlaceholder` removed |
| `deploy/aws/parameters/network.json` | Unchanged unless the operator overrides a default |
| `tests/` | Any R4 guard-test additions; the R3 contract test must pass unchanged |
| `docs/infrastructure_security/evidence_v2/R4/` | `STEPS.md`, `RUNLOG.md`, `R4_<NN>_<name>`, `R4_outputs.json`, `VERIFICATION.md` |
| `docs/infrastructure_security/aws_hardening_control_register_v2.md` | DC-03, DC-05, DC-06, DC-07 (incl. wording), PL-8 |
| `docs/infrastructure_security/aws_hardening_worklog_v2.md` | One entry per R4 milestone, same fields |
| `docs/tier4_orchestration_state/decision_log/` | A record only if a §4 point becomes a lasting rule, or F-OD6r3-2 forces a template change |

## 7. Done for R4

Every `VERIFICATION.md` criterion PASS (or N/A with reason); the R3 tests and any R4 tests pass with
`py -3.10`; the template guard and the old-ID guard are CLEAN; the secret scan of `evidence_v2/R4` is
CLEAN; register v2 rows updated; worklog entry; the operator commits and confirms in session. Then
tick R4 in `plans/aws_redeployment_tickets.md`. R7 then waits only on R6; R11 still waits on R5–R8.
