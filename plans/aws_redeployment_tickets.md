# Tickets: AWS private-network redeployment

These tickets rebuild the hardened Bedrock environment in the new AWS account `797661577394`. They
fix findings F1 to F9 instead of carrying them over. Source: `plans/aws_redeployment_handoff_2026-10-21.md`.
Ticket ids follow its §6 R-ids, so each one traces back to its exit condition there.

Work the **frontier**: any ticket whose blockers are all done. E0, R0 and R10 can start immediately.
Clear context between tickets.

Every ticket inherits the handoff's §7 constraints and §7a evidence protocol:

- The operator performs every AWS step. The agent writes the step sheet, then verifies the evidence
  the operator saves. The agent never ticks a ticket on its own say-so.
- A ticket is done only when every `VERIFICATION.md` criterion is PASS (or N/A with a reason), the
  register v2 rows are updated, a worklog entry exists, and the operator confirms in session.
- A FAIL produces a follow-up step sheet. Nobody fixes a FAIL by editing evidence.
- No Internet Gateway, NAT Gateway, `0.0.0.0/0` route or `0.0.0.0/0` host egress rule, not even
  temporarily.
- Bedrock model invocation logging stays disabled.
- Nothing billable by the hour exists before R11, and R11 needs the operator's explicit go.
- Only the operator upgrades the account or enters billing and tax details.
- No secret value, credential, prompt text or proposal content goes into the repository.
- No old-account id appears in a resource name or policy.
- Tests run with `py -3.10`.
- No ticket amends `CLAUDE.md`, touches Tier 1–3 sources or dispatches a runner phase.

## E0 Evidence protocol scaffold

**What to build:** A prefactor that every later ticket uses. It creates the new evidence tree beside
the old one, with templates for the step sheet, the run log and the verification report. It adds a
secret-scan check that the agent runs over a ticket folder before accepting evidence. The check
refuses any file that matches `AKIA`, `aws_secret`, `SecretString` or `SessionToken`. It also creates
a control register v2 skeleton: all 41 controls (DC-01 to DC-40, PL-8) marked "not started", with an
evidence-path column. Register v1 and the v1 evidence tree stay untouched as history.

**Blocked by:** None — can start immediately.

- [x] The new evidence tree exists. No file in the v1 tree changed.
- [x] The templates match the §7a fields: numbered steps with commands in both PowerShell and
      CloudShell forms, evidence file names, and a PASS criterion per file.
- [x] A test plants each of the four forbidden patterns in a fixture folder, and the scan refuses
      each one. A clean folder passes.
- [x] Register v2 lists all 41 controls, carries no old-account id, and links register v1 as history.

## R0 Operator decisions OD1–OD13

**What to build:** A Tier 4 decision record that holds the operator's answer to each of OD1–OD13. It
gives the reason for each answer, and the consequence wherever the operator chose against the
suggested default. OD7 (the model set) is recorded as deferred to R2, because only R2 shows which
models the account can call.

**Blocked by:** None — can start immediately.

- [x] Each OD has an answer, or is marked "deferred" with its consequence stated.
- [x] OD7 is marked deferred to R2.
- [x] The OD1 reason is recorded, whichever region is chosen.
- [x] The record is committed to the decision log.

## R1 Account baseline

**What to build:** The operator brings the new account to a clean, guarded baseline by following a
step sheet:

- root MFA, and an admin identity per OD11;
- a verified budget e-mail recipient, and budgets per OD13;
- account-level EBS default encryption and account-level S3 Block Public Access;
- an IMDSv2-required instance metadata default;
- the Explore AWS leftovers removed in every region used: EC2, key pair, security group, Lambda, and
  RDS with its snapshots;
- the console home region set to the OD1 region.

**Blocked by:** E0, R0.

- [x] Each item has CLI output or console evidence, verified against its PASS criterion. (Console home Region N/A on the Free plan: `aws-redeployment-r1-baseline-deviations_2026-10-21`, R1-D1.)
- [x] The budget recipient shows as verified, and a test alert has arrived. (Replaced, operator-approved: recipient verification is SCP-denied; the test alert reached `ALARM` and credits and alert states are checked by CLI — R1-D2.)
- [x] No billable resource is running outside the plan, in any region.

## R2 Bedrock access check, closing OD7

**What to build:** The operator proves which Claude models the account can call in the OD1 region,
working from CloudShell. The steps are:

- the Anthropic use-case form, and a Marketplace subscription if asked;
- a listing of the inference profiles;
- one Converse call per candidate model, returning a fixed test string;
- the token and request quotas per candidate.

The agent turns the results into a
successor decision record that settles OD7. That record names the orchestrator model, two distinct
models for AN12 A3 and A5, and an assessor that differs from the drafter in every id form (AN1c).

**Blocked by:** R1.

- [x] A table lists each usable model by profile id, with its quotas and the regions it routes to. (`docs/infrastructure_security/evidence_v2/R2/VERIFICATION.md`, "Usable models": Opus 4.6, Sonnet 4.6, Haiku 4.5; newer models refused for this account.)
- [x] The OD7 successor decision record is committed. (`aws-redeployment-od7-model-set_2026-10-21`, commit `690f90c`.)
- [x] If the Free plan blocks Bedrock, the ticket stops here. The agent reports the block to the
      operator as an input to OD10 and builds nothing on top of it. (N/A: Bedrock is not blocked. The
      account-level model restriction and the RPM cut were reported as OD10 input, F-R2-1 to F-R2-3.)

## R3 IaC skeleton and old-ID guard

**What to build:** The infrastructure layout chosen in OD6, with two stacks: a base stack (network,
IAM, KMS, audit) and an endpoints-and-host stack (the part that costs money). Parameters cover the
account id, region, AZs, the model list and bucket names with an account suffix. Every resource
carries the tag `project=proposal-orchestrator`. A lint step runs on the workstation. A test greps
the infrastructure and new evidence for the old account id, the old `vpce-`, `sg-` and `subnet-` ids,
and the old instance id.

**Blocked by:** R0.

- [x] The templates lint cleanly on the workstation. (`docs/infrastructure_security/evidence_v2/R3/R3_03_cfn-lint.txt`: cfn-lint 1.57.2, exit 0 on all six templates; `R3_08_validate-*.json`: validate-template exit 0 in eu-north-1.)
- [x] The old-ID test fails on a planted old id and passes on the real tree. (`tests/test_old_id_guard.py`, `tools/old_id_guard.py`; `R3_11_pytest.txt`, `R3_11_old-id-guard.txt`.)
- [x] The stack outputs are named, so later tickets and the evidence collector can read ids from them. (`deploy/aws/outputs_contract.json`, checked by `tests/test_aws_iac_contract.py`. Layout revised from two stacks to six, operator-decided: `aws-redeployment-od6-stack-layout-r3_2026-10-22`, commit `be3198f`.)

## R12a Parameterised evidence collector

**What to build:** The old evidence collector rebuilt so that it hard-codes nothing. It takes the
account, the region and every resource id from saved stack outputs, and it writes only into the v2
evidence tree. Running it against the old tree is impossible by construction. This ticket is code
only; it collects nothing yet.

**Blocked by:** E0, R3.

- [ ] A test runs the collector against fixture stack outputs and confirms that every id it uses
      comes from them.
- [ ] A test confirms that the collector refuses an output path inside the v1 tree.
- [ ] The R3 old-ID test passes over the collector.

## R9 Runtime configuration from the secret (F4, F6)

**What to build:** The host process gets its configuration from where the documents say. Under
OD8 (a), a launcher reads the runtime secret and exports its values. Under OD8 (b), it reads a
root-owned env file instead. Either way it exports `AWS_REGION`, which the Converse backend reads.
Production mode refuses to run when `AWS_REGION` is missing, so a call can never silently go to the
default region.

The deployment guide names `ORCHESTRATOR_TRANSPORT_MODEL`, not `SKILL_MODEL`. F6 is
decided: either the `bedrock` backend leaves the production set, or the guide states that only
`bedrock_converse` is valid on the private host. Code only.

**Done 2026-10-27** (`docs/infrastructure_security/evidence_v2/R9/VERIFICATION.md`; decision record
`aws-redeployment-r9-runtime-config_2026-10-27`; operator confirmed in session).

**Blocked by:** R0.

- [x] A test shows that production mode with no `AWS_REGION` is refused.
- [x] A test shows that the launcher exports the configured values without logging any of them.
- [x] The F6 decision is in a test or in the guide, and the decision log records which.
      (In tests, R9-D7.)
- [x] The full suite shows no new failures.

Note (R9, decision record `aws-redeployment-r9-runtime-config_2026-10-27`, F-R9-1 / R9-D21): the full
suite makes outbound HTTP requests on the workstation (a harness `.env.harness` load leaks into
`os.environ` and the cached provider; the OpenAI-compatible transport tests reach real hosts). Proposed
follow-up, outside R9: test isolation (an autouse fixture restoring `os.environ` and resetting the
transport caches; network guards in those tests). R9e also inherits the list in that record's `for_r9e`.

## R9e EU region support

**What to build:** This ticket applies only if OD1 picks an EU region. It adds a Converse preset for
that region with `eu.` profiles. It parameterises the transport tests that fix `us-east-1`. It
updates the AN12 runbook's region lines and its id rule, together with the guard test that parses
the runbook. If OD1 keeps us-east-1, the ticket closes as N/A with that reason.

**Done 2026-10-28** (`docs/infrastructure_security/evidence_v2/R9e/VERIFICATION.md`; decision record
`aws-redeployment-r9e-eu-region_2026-10-27`; operator confirmed in session).

**Blocked by:** R0, R9.

- [x] An EU Converse preset exists and is tested.
      The preset is named `BEDROCK_CONVERSE_EU` (backend `bedrock_converse`, default Region eu-north-1,
      `eu.` profiles): the R8 secret stores that name (decision record
      `aws-redeployment-r8-secret_2026-10-26`, R8-D3). A test asserts that the preset name stored by
      `deploy/aws/templates/50-secret.yaml` exists in `runner/transport/config.py`.
- [x] No transport test fixes the region.
- [x] The runbook guard test passes on the edited runbook.
- [ ] Or: the ticket is closed N/A, with OD1 cited. (Closed N/A 2026-10-21, **reopened** the same day: OD1 is now eu-north-1, decision record `aws-redeployment-od1-region-r1_2026-10-21`.)

## R10 Phase 8 drafter through the transport layer (F5)

**What to build:** The decomposed drafter resolves its provider through the transport layer, as the
skill runtime and semantic dispatch already do. Under production mode, it reaches the Converse
backend or refuses with a production-mode error. It never reaches the Claude CLI transport. This
closes the one known production-mode bypass, whether or not DC-38 is in scope.

**Done 2026-10-28** (`docs/infrastructure_security/evidence_v2/R10/VERIFICATION.md`; decision record
`aws-redeployment-r10-drafter-transport_2026-10-28`; operator confirmed in session). Findings for
later tickets: F-R10-1 (the skill runtime's failure reason carries a response head at any diagnostic
level; R12b or a new ticket), F-R10-2 (Converse throttling with no retry; R11, R16).

**Blocked by:** None — can start immediately. OD12 only sets its priority.

- [x] A test that fails on today's code: under `ORCHESTRATOR_PRODUCTION_MODE=true`, the drafter never
      calls the Claude CLI transport. (`tests/runner/test_decomposed_drafting_transport.py`; failing on
      `265f88d`, `evidence_v2/R10/R10_02_head-criterion1.txt`.)
- [x] The existing Phase 8 drafting tests still pass on the workstation's non-production path.
- [x] Phase 8 dispatch is untouched apart from provider resolution. The gates, scheduler and node
      states are unchanged. (`R10_03_diff-stat.txt`.)

## R4 Network base stack

**What to build:** The network layer, deployed at no hourly cost:

- a VPC per OD3 with DNS hostnames and DNS support on, and no Internet Gateway;
- private subnets per OD4;
- a route table with only the local route and the S3 prefix list;
- a host security group allowing egress 443 to the endpoint security group and to the S3 prefix list;
- an endpoint security group allowing ingress 443 from the host group only, with no egress;
- an S3 gateway endpoint whose policy admits only this account's buckets (F7).

**Blocked by:** E0, R1, R3.

- [x] The stack deploys, and its outputs are saved. (`evidence_v2/R4/R4_outputs.json`; stack `proposal-orchestrator-network` created 2026-10-23.)
- [x] The route table shows no `igw-` or `nat-` target, and the VPC has no Internet Gateway.
- [x] The S3 endpoint policy restricts by resource account and names the project buckets. It
      admits the AL2023 repository buckets only if OD9 added them. (Read-only on the deploy bucket, `aws:ResourceAccount` + `aws:PrincipalAccount`; no AL2023, trail or SSM bucket — `aws-redeployment-r4-network_2026-10-24` R4-D3.)
- [x] DC-06 and PL-8 are evidenced, together with the security-group halves of DC-03 and DC-07.
      DC-07's wording is corrected in register v2. (Also: the VPC's default security group emptied, lasting rule R4-D2.)

## R5 IAM stack: the hardened role is the runtime role

**What to build:** The host's runtime identity is the hardened one (F1). Under OD2 (a), one host role
and instance profile carry:

- the permission boundary, extended for exactly the SSM actions the host needs;
- the explicit deny, updated for the chosen profile prefix;
- an invoke policy that names the OD7 profiles and every region they route to (F2);
- the supporting-services policy;
- a deploy-bucket read scoped to its prefixes.

A flow-logs role completes the stack. No policy is named or described as temporary.

**Blocked by:** R2, R3.

- [x] IAM simulation allows invoke for each OD7 model and its routed foundation models. (`evidence_v2/R5/R5_09_allow-profiles.json` and twelve `R5_09_allow-fm-*.json`; the live routed call is R11, F-R5-2.)
- [x] IAM simulation denies admin actions, non-Claude models, `global.` profiles (unless OD7 chose
      them), and S3, EC2 and IAM actions outside the policy. (`R5_09_deny-*.json`, `R5_12_deny-*.json`; seven step-09 files superseded by `STEPS_fix1.md`.)
- [x] The boundary and explicit deny are attached to the role the instance profile uses. DC-09 to
      DC-13 are evidenced on that role. (DC-10–DC-13 VERIFIED_PASS; DC-09 IN_PROGRESS until R11 shows the host uses the profile — `aws-redeployment-r5-iam_2026-10-25` R5-D9.)
- [x] No policy in the account carries "temporary" or "validation" in its name or description. (`R5_03_local-policies-before.json`, `R5_08_local-policies-after.json`, `R5_08_policy-*.json`; stack `proposal-orchestrator-iam`, commit `8dccd77`.)

## R6 KMS key

**What to build:** A customer-managed key with alias `alias/proposal-orchestrator` and rotation on.
Its key policy grants the account root, the runtime role per OD2, CloudTrail (scoped by source ARN)
and CloudWatch Logs (scoped to the project's log-group prefix). The runtime role decrypts through the
key policy, not through an IAM side grant.

**Blocked by:** R5.

- [x] Rotation is on, and the alias resolves to the new key. (`evidence_v2/R6/R6_08_rotation-status.json`: on, 365 days; `R6_08_describe-by-alias.json`, `R6_08_aliases-of-key.json`.)
- [x] The key policy names the runtime role. No IAM policy grants that role Decrypt separately. (`R6_08_key-policy.json`, equal to the template by script; `R6_08_runtime-role-attached.json`/`-inline.json` unchanged, `R6_08_key-grants.json` `[]`, `R6_09_deny-kms-identity-grant.json` `implicitDeny`.)
- [x] DC-18 and DC-19 are evidenced. (DC-18 VERIFIED_PASS; DC-19 VERIFIED_PASS at policy level, grants exercised in R7 and R8/R11 — `aws-redeployment-r6-kms_2026-10-26` R6-D9; stack `proposal-orchestrator-kms`, commit `0487e68`.)

## R7 Audit and storage stack

**What to build:** The audit trail and the two project buckets:

- the trail bucket, with versioning, Block Public Access, the old bucket policy with new ARNs, and a
  lifecycle of 90 days to Glacier Instant Retrieval and expiry at 365 days;
- the deploy bucket, encrypted with the CMK, with Block Public Access, versioning and access limited
  to the runtime role's prefixes (the handoff named this bucket but gave it no ticket);
- the trail, with log-file validation and the CMK;
- a flow-log group (CMK, 90-day retention) and flow logs on every subnet.

The ticket confirms that Bedrock invocation logging is unset.

**Blocked by:** R4, R6.

- [x] Both buckets show Block Public Access, versioning and the CMK.
- [x] The trail validates log files and logs to the trail bucket.
- [x] Flow logs are active on every subnet. (One flow log on the VPC, ACTIVE / SUCCESS; records follow in R11, R7-D18.)
- [x] The invocation-logging configuration is empty.
- [x] DC-08, DC-23 to DC-25 and DC-27 to DC-30 are evidenced. DC-26 waits for R11. (All VERIFIED_PASS; DC-08 on configuration, R7-D18 — `aws-redeployment-r7-audit_2026-10-26`; stack `proposal-orchestrator-audit`, commit `874edeb`.)

## R8 Runtime secret

**What to build:** Under OD8 (a), the runtime secret is encrypted with the CMK. Its resource policy
names only the runtime identity, plus an admin role if one exists. It holds the transport preset,
production mode on, diagnostic level `metadata`, `AWS_REGION` and the transport model. Under OD8 (b),
the ticket evidences the root-owned env file design instead, and DC-20 and DC-21 are restated in
register v2.

**Done 2026-10-27** (`docs/infrastructure_security/evidence_v2/R8/VERIFICATION.md`; decision record
`aws-redeployment-r8-secret_2026-10-26`; operator confirmed in session).

**Blocked by:** R5, R6.

- [x] The secret uses the CMK, and its policy names no principal outside the allowed set.
- [x] Evidence records the key names and metadata only. The E0 scan passes on the folder.
- [x] DC-20 and DC-21 are evidenced or restated.

## R11 Endpoints and host: first PrivateLink call

**What to build:** The tracer bullet, and the first ticket with an hourly cost. The operator approves
each creation. The endpoints-and-host stack creates:

- interface endpoints for `bedrock-runtime`, `sts`, `secretsmanager`, `ssm`, `ssmmessages` and
  `ec2messages`, with private DNS, in the OD4 zones;
- a Bedrock endpoint policy naming the runtime role and the OD7 resources;
- a host per OD9 with no public IP, IMDSv2 required with hop limit 1, an encrypted gp3 root volume
  with `DeleteOnTermination=true`, and the R5 instance profile.

SSM Run Command reaches the host. One Converse call from the host returns a fixed test string over
PrivateLink, and CloudTrail attributes it to the hardened runtime role. Then the stack is deleted and
recreated once.

**Blocked by:** R4, R5, R6, R7, R8.

- [ ] All endpoints show `available`. The host has no public IP.
- [ ] A Run Command invocation returns `Success`.
- [ ] The Converse call succeeds. CloudTrail shows the runtime role as caller, with the boundary
      attached (closes F1).
- [ ] DC-01, DC-02, DC-04, DC-05, DC-14, DC-26 and DC-37 are evidenced.
- [ ] The stack deletes cleanly, leaves the base stack intact, and recreates from the templates.

## R14 Operations and cost

**What to build:** The operator can run the billable stack safely on credits. This ticket adds start,
stop and teardown scripts for the endpoints-and-host stack, in PowerShell and CloudShell forms. It
adds a weekly cost check that reports spend against the credits and the approved HUF amount,
including Bedrock tokens per run. Every unit price comes from the AWS pricing pages for the OD1
region, not from the handoff's estimates. The ticket also writes the OD10 upgrade checklist: ELTE
billing details, VAT number, tax settings and raised budgets. Only the operator carries out that
checklist.

**Blocked by:** R11.

- [ ] Each script ran once end to end, with evidence.
- [ ] The cost check ran once. Every price in it cites its pricing page and date.
- [ ] The upgrade checklist exists and is marked operator-only.

## R12b Full re-evidence and register v2

**What to build:** Every control is evidenced again in the new account by the R12a collector. This
ticket adds the evidence that the old programme never collected: the F7 negative test (a presigned
PUT from the host to a bucket outside the account is refused) and the in-host DC-15 negative tests.
DC-33 to DC-35 are evidenced through the R9 launcher reading the configuration on the host. DC-40 is
re-assessed.

**Blocked by:** R12a, R9, R11.

- [ ] Register v2 shows every control as VERIFIED_PASS, NOT_APPLICABLE with a reason, or DEFERRED
      with a reason, and gives a v2 evidence path for each.
- [ ] The presigned PUT to an outside bucket fails from the host (closes F7).
- [ ] The DC-15 in-host tests are collected.
- [ ] DC-40 is re-assessed. It stays N/A unless the account joined an Organization.

## R15 AN12 host run

**What to build:** The operator runs AN12 on the new host per its runbook, with the new deploy
bucket, the OD1 region and the OD7 models substituted. The offline bundle verifies with the
no-internet probe. The synthetic-fixture pipeline and the Converse blind pass then run. The agent
writes a successor decision record to the 2026-10-16 AN12 offline-bundle record.

**Blocked by:** R9, R9e, R11, R12b.

- [ ] `runner.offline_bundle verify --probe-no-internet` passes on the host.
- [ ] Each AN12 criterion the runbook defines is met, with evidence.
- [ ] The successor decision record is committed.

## R13 Documentation amendments

**What to build:** The security documents describe the new account. The agent drafts:

- ADR-001 amendment A2: the new account, the F1, F2, F3 and F7 changes, and the region per OD1;
- the risk register: the new account, the overdue review held, RSK-14 closed or restated, and an F7
  risk if R12b left anything open;
- the data flow document: the region and transfers;
- the operational procedure: stack lifecycle, start, stop and teardown;
- the deployment guide: ids taken from stack outputs, and the corrected variables.

The operator approves the drafts, and then the agent applies them, as was done for A1. The old
documents are amended, not overwritten.

**Blocked by:** R12b.

- [ ] The operator approved each amendment in session before it was applied.
- [ ] No document cites an old-account id as current. The R3 old-ID test passes over them.
- [ ] Each amendment records its prior text, its new text and the reason.

## R16 Orchestrator bundle and DC-38

**What to build:** This ticket applies only if OD12 put DC-38 in scope. The orchestrator is bundled
for the host, and the operator dispatches a full DAG run under production configuration. The run
summary is the DC-38 evidence. If OD12 kept DC-38 deferred, the ticket stays open as deferred with
that reason.

**Blocked by:** R9, R10, R11.

- [ ] DC-38 is marked VERIFIED_PASS or VERIFIED_FAIL, with the run summary as evidence.
- [ ] Or: DC-38 is DEFERRED in register v2, with OD12 cited.
