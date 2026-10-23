# AWS redeployment: handoff for R3 (IaC skeleton and old-ID guard)

| Field | Value |
|---|---|
| Date | 2026-10-22 |
| Branch at writing | `msca-dn-pre-eval` at `3c312f0` (R1 and R2 closed) |
| For | The agent that runs ticket R3 with the operator in a new session |
| Read first | `CLAUDE.md`; `plans/aws_redeployment_tickets.md` (inherited constraints at the top, R3, and R4–R8, R11, R12a for what the skeleton must hold); `plans/aws_redeployment_handoff_2026-10-21.md` §4 F2, F3, F7, F9, F10, §5 OD2–OD6, §7, §7a, §9; `plans/aws_redeployment_r2_handoff_2026-10-21.md` §2 (how the operator works); `docs/infrastructure_security/evidence_v2/README.md` |
| Decision records in force | `docs/tier4_orchestration_state/decision_log/`: `aws-redeployment-operator-decisions_2026-10-21` (R0), `aws-redeployment-od1-region-r1_2026-10-21`, `aws-redeployment-od11-admin-identity-r2_2026-10-21`, `aws-redeployment-r1-baseline-deviations_2026-10-21`, `aws-redeployment-od7-model-set_2026-10-21` |
| Status | E0, R0, R1, R2 done. Frontier: **R3**, R9, R9e, R10 (independent of each other). R4, R5 and R12a wait for R3. |

## 1. Facts that govern R3

| Fact | Record / evidence |
|---|---|
| Account `797661577394` is a "Sign up for AWS (new)" project account in an AWS-managed organization. AWS-managed SCPs allow regional actions **only in eu-north-1**; us-east-1 and us-west-2 allow global services only. | OD1-r1; `evidence_v2/R1/R1_25_*`, `R1_26_region-access.txt` |
| Everything regional is in **eu-north-1**. No template may hard-code a Region except as a parameter default (F9). | OD1-r1 |
| In eu-north-1, EC2 dry runs with real ids succeed for VPC, subnet, SG, route table, bedrock-runtime interface endpoint, S3 gateway endpoint, flow logs and a t3.medium launch (encrypted gp3, IMDSv2). `cloudformation:CreateStack` is **not SCP-denied there (Inferred)**: no stack has been created in this account yet; R4 is the first real proof. | OD1-r1 F-OD1r1-3, F-OD1r1-4; `R1_27_scp-probe-eu-north-1.json` |
| Admin identity: Builder ID → `assumed-role/AccountFullAccessRole/<session>` (`AdministratorAccess`). There is no IAM user and no root user. Where a policy needs an admin principal (R6 key policy, R8 secret policy), it is the role `arn:aws:iam::797661577394:role/AccountFullAccessRole` or the account root. | OD11-r2; `R1_00_role*.json` |
| Account-level EBS default encryption and IMDSv2-required defaults are set in eu-north-1; R11 still sets both on the host. | R1-D3 |
| **OD7 model set:** profiles `eu.anthropic.claude-opus-4-6-v1` (orchestrator, A5) and `eu.anthropic.claude-sonnet-4-6` (A3, assessor). Each routes to eu-north-1, eu-west-3, eu-south-1, eu-south-2, eu-west-1, eu-central-1. R5/R11 need the 2 profile ARNs and the 12 foundation-model ARNs, listed in the record's `OD7-resources`. `global.` profiles are denied. Opus 4.6 is interim; **the target is Opus 5 or newer**, so the model list must be a parameter, never a literal in a policy. | OD7 record; `evidence_v2/R2/VERIFICATION.md` |
| Free plan, ~200 USD credits. Budget e-mails cannot be delivered; credits and alert states are checked by CLI as the **first step of every step sheet that touches AWS** (R1-D2). | R1-D2 |
| CloudShell: R1 ran in the us-east-1 home (`~/R1`), R2 in the **eu-north-1** home (`~/R2`). Use the eu-north-1 CloudShell from R3 on (`~/R3`); every regional command still names `--region eu-north-1`. | R2 RUNLOG step 02 |
| `deploy/` already holds the AN12 host install (`install_host.sh`, `offline_bundle.json`, `requirements-host.txt`). The IaC goes beside it, in `deploy/aws/` (OD6's suggestion), not into it. | repository |

## 2. R3 as it reads

Ticket exit conditions:

1. **The templates lint cleanly on the workstation.** CloudFormation (OD6), with `cfn-lint` run by the
   operator in PowerShell with `py -3.10` (pin the version, for example in `deploy/aws/requirements-lint.txt`).
   Save the lint output as R3 evidence.
2. **The old-ID test fails on a planted old id and passes on the real tree.**
3. **The stack outputs are named**, so R4–R11 save them as `<ticket>_outputs.json` and R12a's collector
   reads every id from them.

Every resource carries `project=proposal-orchestrator`. Parameters cover account id, Region, AZ, the
model list and bucket names with the account suffix. R3 creates nothing in AWS and nothing billable.

### The old-ID guard

- The dead ids are in the first handoff §9: account `232538551827`; VPC `vpc-050a09774560fd774`; subnets
  `subnet-023c6e3ea5451ea47`, `subnet-01d969bb1421a3042`; route table `rtb-085481996de5e3ed9`; SGs
  `sg-076f724aed2429771`, `sg-013d5e4d4eb55dfd9`; seven `vpce-` ids; flow logs `fl-03c1ed4c967c50073`,
  `fl-0948b876901308e70`; KMS key `887638e8-358b-4664-9270-368aec0ea1f1`; host `i-0045af36dbf5f1272`. The
  ticket requires at least the account, `vpce-`, `sg-`, `subnet-` and instance ids; covering the whole
  §9 list costs nothing.
- **Match the exact old ids, never a prefix pattern.** R1 evidence legitimately holds new-account ids
  (the eu-north-1 default VPC `vpc-0fcb706a089aeb352` and the deleted `sg-085c137a9e87fc7ba`).
- **Scope:** `deploy/aws/`, `docs/infrastructure_security/evidence_v2/`, register v2, and the
  `aws-redeployment-*` decision records. Not in scope: the v1 tree (`evidence/`, `audit_package/`, v1
  register and worklog), `deployment_guide.md` (R13 rewrites it) and `plans/` (the handoffs list old
  ids on purpose). A `git grep` on 2026-10-22 found none of the old ids in the in-scope paths.
- Assemble the old ids at run time in the test, as `tests/test_evidence_protocol_scaffold.py` does,
  so the test file is not itself a finding. R12a must be able to run the same guard over its
  collector, so a reusable module with a CLI (in the style of `tools/evidence_secret_scan.py`) plus a
  test is a better shape than a test alone.

### Cheap guard tests worth adding (suggestion, not a ticket criterion)

Parsed-template checks, with `py -3.10`: no `AWS::EC2::InternetGateway`, `NatGateway` or `EIP`; no
`0.0.0.0/0` in any route or SG rule; every taggable resource carries `project=proposal-orchestrator`;
no policy or resource name or description containing "temporary" or "validation" (R5); no Region
literal outside parameter defaults (F9). Short-form intrinsics (`!Ref`, `!Sub`) need a YAML loader
that understands them; check what is installed before choosing.

## 3. Points to settle with the operator

- **Stack layout.** OD6 says two stacks: base (network, IAM, KMS, audit) and endpoints-and-host (the
  costed part). The tickets that follow speak of a network stack (R4), an IAM stack (R5) and an audit
  stack (R7). Proposal: keep OD6's split between free and costed, but build the free part as one small
  stack per ticket, deployed in ticket order with exports: network (R4) → iam (R5) → kms (R6) → audit
  and storage (R7) → secret (R8). The costed endpoints-and-host stack (R11) imports from them and is
  created and deleted per session (OD5). Reasons: each ticket deploys and rolls back on its own, every
  template stays under the 51,200-byte `--template-body` / `deploy` limit without an S3 staging bucket
  (none exists before R7), and the evidence stays per ticket. Alternative: one base stack that each
  ticket updates. If the operator chooses the split, record it as a successor to OD6 in the decision
  log.
- **Parameters and where their values come from.** Account id (assert it equals `AWS::AccountId`;
  check whether CloudFormation `Rules` accept the pseudo parameter, otherwise assert in the deploy
  step), Region (`eu-north-1` as default, guarded), one AZ (OD4), the OD7 profile ids and routed
  Regions as lists, and bucket names `proposal-orchestrator-deploy-797661577394` and
  `proposal-orchestrator-cloudtrail-797661577394` (§9).
- **Does R3 need an AWS step sheet?** Proposal: a short read-only one, so later parameter values come
  from evidence, not from memory (§7a): session check (R1-D2); which eu-north-1 AZs offer all six
  interface endpoint services (`bedrock-runtime`, `sts`, `secretsmanager`, `ssm`, `ssmmessages`,
  `ec2messages`) via `describe-vpc-endpoint-services`; the S3 prefix-list id; whether the AL2023 AMI
  public SSM parameter is readable; and `aws cloudformation validate-template --region eu-north-1` for
  each skeleton template (read-only; shows the service answers and no SCP refuses it). Nothing is
  created.
- **Output names.** Propose stable `OutputKey`s and export names (for example
  `proposal-orchestrator-<stack>-<Key>`) for every id the later tickets and R12a need: VPC, subnet,
  route table, both SGs, S3 gateway endpoint, role and instance-profile names and ARNs, key ARN and
  alias, bucket names, trail ARN, log group, secret ARN, endpoint ids, instance id.

## 4. Files

| Path | What |
|---|---|
| `deploy/aws/` | The templates, a README stating the stack order and deploy commands, and the lint requirements |
| `tools/` and `tests/` | The old-ID guard and its test; any template guard tests |
| `docs/infrastructure_security/evidence_v2/R3/` | `STEPS.md` (from `_templates/`), `RUNLOG.md`, the lint output and any read-only lookups as `R3_<NN>_<name>`, `VERIFICATION.md` |
| `docs/infrastructure_security/aws_hardening_worklog_v2.md` | One entry per R3 milestone, same fields |
| `docs/tier4_orchestration_state/decision_log/` | An OD6 successor record, only if the stack layout changes |

No register v2 row names R3; register v2 is unchanged unless a guard test touches a control.

## 5. Done for R3

Every `VERIFICATION.md` criterion PASS (or N/A with reason), the tests pass with `py -3.10`, a worklog
entry exists, the operator commits and confirms in session. Then tick R3 in
`plans/aws_redeployment_tickets.md`. R4, R5 and R12a are then on the frontier.
