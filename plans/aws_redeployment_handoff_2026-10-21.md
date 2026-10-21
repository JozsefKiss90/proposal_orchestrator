# AWS private-network redeployment: handoff for ticketing

| Field | Value |
|---|---|
| Date | 2026-10-21 |
| Branch at writing | `msca-dn-pre-eval` at `f3feec9` |
| Audience | The agent that turns this document into tickets, then the agents and the operator who carry them out |
| Status | Handoff. Nothing here is implemented. No AWS call was made to write it. |
| Authority | Execution aid under `CLAUDE.md` §10.2. Operator decisions are marked as such and stay the operator's. |
| Source reviewed | All of `docs/infrastructure_security/` (control register, worklog, deployment guide, audit package, evidence CG1–CG11), `plans/msca_dn_an12_host_runbook.md`, `deploy/`, `runner/transport/config.py`, `runner/skill_runtime.py`, `runner/semantic_dispatch.py`, `runner/decomposed_drafting.py` |
| Related | `docs/infrastructure_security/audit_package/ADR-001-security-decisions.md`, `plans/msca_dn_anonymisation_handoff_2026-10-14.md` (AN-ledger), `docs/tier4_orchestration_state/decision_log/msca-dn-an12-offline-bundle_2026-10-16.json` |

---

## 1. What this is for

The hardened Bedrock environment documented in `docs/infrastructure_security/` lived in AWS account
`232538551827` (us-east-1). That account is no longer available. The operator has opened a **new
account** and wants the whole environment rebuilt there, using the old setup as the starting point,
so that the application can again be used securely over AWS.

The goal is the same security posture as before: inference only through Amazon Bedrock over
PrivateLink, a host with no internet route, role-based credentials, a customer-managed KMS key,
CloudTrail without prompt logging, and the application's production-mode guards. The goal is
**not** a byte-for-byte copy. Section 4 lists defects in the old setup that must be fixed rather
than carried over.

### Workloads the rebuilt environment must serve, in order

1. **AN12 host run** (`plans/msca_dn_an12_host_runbook.md`): the anonymisation bundle, its verify
   record, the A0–A7 pipeline on the synthetic fixture, and the Converse blind pass. It was written
   for the old host and never executed there.
2. **AN13 and the V14 private session** (AN-ledger): the DN original processed inside the network.
3. **DC-38**: a full orchestrator DAG run under production configuration. It was deferred in the old
   account and never closed. Finding F5 blocks it today.

The deadline that drives priority is the MSCA Doctoral Networks submission on 2026-11-23
(operator-stated). Tickets that serve workload 1 come first.

---

## 2. Starting state (facts as of 2026-10-21)

| Item | State | Source |
|---|---|---|
| New AWS account | `797661577394` | Operator console URL |
| Plan | AWS **Free plan**, 200 USD credits (100 sign-up + 100 Explore AWS), free period ends 2027-04-19 | Operator screenshots |
| Free-plan behaviour | No charges. When credits run out or the period ends, the account is suspended, and deleted after 90 days unless upgraded. Some services that would exhaust credits are unavailable on the Free plan. | AWS Free Tier FAQ |
| Billing identity | Operator's personal details for now. ELTE billing details (Eötvös Loránd Tudományegyetem, 1053 Budapest, Egyetem tér 1–3, VAT HU15308744) are entered **only at the upgrade to the paid plan**. | Operator decision |
| Funding | About 300,000 HUF from Kovács Péter's OTKA/NKKP project, for the MSCA DN proposal. Approval of the reimbursement route by the ELTE IK financial office is **pending**. | Operator; e-mail thread 2026-10-14/16 |
| Cost guard | AWS Budgets monthly cost budget of 10 USD exists. Its e-mail recipient (`kissjozsef@inf.elte.hu`) is **unverified**, so it sends no alerts yet. | Operator screenshot |
| Leftovers from Explore AWS | EC2 test instance in **eu-north-1** (operator was told to terminate it), plus possibly its key pair and the `launch-wizard-1` security group. Lambda/RDS state unknown. | Operator screenshots |
| Old account resources | Unreachable. Every ID in the old docs (account, VPC, subnets, SGs, endpoints, KMS key, instance, bucket names) is **dead** and must not be reused. | — |
| Bedrock model access in the new account | Unknown. Not tested from the CLI. Anthropic models need the one-time use-case form, and possibly an AWS Marketplace subscription. | — |

---

## 3. How to read the old documentation

The old docs are the **design baseline**, not a script to replay. Use them like this:

| File | Use it for | Do not |
|---|---|---|
| `aws_hardening_control_register.md` | The 41 controls (DC-01 to DC-40, PL-8): requirement, evidence form, pass criteria | Copy reviewer notes or IDs |
| `aws_hardening_worklog.md` | Order of the original build (CG1 → CG10) and what was found at each review | — |
| `evidence/01_privatelink/aws_implementation_steps.md`, `evidence/02_iam/aws_iam_implentation_steps.md`, `evidence/0x_*/CGx_steps.txt` | Exact CLI command shapes per control group | Run them unchanged; they hard-code the old account |
| `evidence/**/*.json` policy files (`bedrock-invoke-policy.json`, `explicit-deny-policy.json`, `boundary-policy.json`, `kms_key_policy.json`, `trail_bucket_policy.json`, `lifecycle_policy.json`, flow-log policies, `secret_resource_policy.json`) | Templates for the new policies, after the fixes in §4 | Reuse the two `validation-*` policies (temporary, see F1) |
| `deployment_guide.md` | Offline-bundle route, S3 gateway SG rule, SSM Run Command usage, smoke tests, troubleshooting, "approaches that do not work" | Treat §6's `export SKILL_MODEL=…` as effective (see F4) |
| `audit_package/*` | ADR decisions 1–9 and amendment A1, risk register, data flow, operational procedure | Overwrite; amend instead (§6, R13) |
| `evidence/11_audit_package/collect_evidence.ps1` | Re-verification of all controls | Run unchanged; it hard-codes 18 old IDs and writes into the old evidence tree, which would overwrite the baseline |

**Keep the old evidence.** It is the historical record of the first hardening (CG1–CG10, 38/41
VERIFIED_PASS). New evidence goes to a new location (see R12), and the register gets a new version.

---

## 4. Findings: what the old setup left open or got wrong

These come from reading the evidence against the code. Each one is either a ticket or an input to an
operator decision. "Old" means account `232538551827`.

### F1. The hardened role was not the role that ran (security, must fix)

- The host ran under `proposal-orchestrator-ec2-ssm-role`. Its instance profile replaced
  `proposal-orchestrator-bedrock-profile` during CG2 (`02_iam/IAM_Least_Privilege_logs.txt`, the
  `replace-iam-instance-profile-association` step), because the bedrock role's permission boundary
  does not allow SSM.
- All Bedrock calls in CloudTrail come from `assumed-role/proposal-orchestrator-ec2-ssm-role`
  (DC-14, DC-26, DC-37).
- The permission boundary (DC-12), the explicit denies (DC-11) and the trust-policy checks (DC-09,
  DC-13) were verified on `proposal-orchestrator-bedrock-role`, which **no running process used**.
- The runtime role held: `AmazonSSMManagedInstanceCore`, `proposal-orchestrator-bedrock-invoke`, two
  policies created as **temporary** (`proposal-orchestrator-validation-bedrock-us-east-2`,
  `proposal-orchestrator-validation-sonnet46-full`), the secret-read policy and the deploy-bucket
  access policy (broad S3). It had **no boundary and no explicit deny**.
- The KMS key policy grants Decrypt only to the bedrock role. The runtime role got Decrypt from an
  IAM policy instead.

Consequence: DC-09 to DC-13 passed on paper, but the identity that handled proposal data was the
least restricted one. The rebuild must make the hardened identity the runtime identity. Operator
decision OD2 chooses how.

### F2. Cross-region inference was not modelled in IAM (functional and security)

- `us.anthropic.claude-sonnet-4-6` is a cross-region inference profile. Bedrock routes it to
  foundation models in us-east-1, us-east-2 and us-west-2.
- The designed invoke policy (`bedrock-invoke-policy.json`: `foundation-model/anthropic.claude-*`
  plus `inference-profile/us.anthropic.claude-*`, condition `aws:RequestedRegion ∈ {eu-west-1,
  us-east-1}`) was not enough on its own. The operator had to add the two `validation-*` policies,
  which name the profile ARN and the routed foundation-model ARNs in all three US regions, before
  the call succeeded.
- `explicit-deny-policy.json` (DenyNonClaudeModels, NotResource) and the endpoint policy only allow
  `us.anthropic.claude-*` profiles. `eu.*`, `global.*` and application inference profiles would be
  **denied**. That is correct for `global.*`, which may route outside the chosen jurisdiction, but
  it blocks an EU deployment unless it is changed deliberately.

The new invoke policy must state the chosen profiles and their routed regions explicitly, and must be
tested with IAM simulation **and** a live call before any "temporary" policy is considered. No
policy named or described as temporary may survive into the verified state.

### F3. The old VPC was the account's default VPC (hardening)

The old VPC was `172.31.0.0/16`, i.e. the account's default VPC. Its default subnets have
`MapPublicIpOnLaunch=true` and it had an Internet Gateway attached. Isolation depended on a custom
route table (`proposal-orchestrator-private-rt`) associated with two default subnets, and on
`--no-associate-public-ip-address` at launch. One wrong association, or one launch without that
flag, would have restored an internet path. Prefer a dedicated VPC with no Internet Gateway at all
(OD3).

### F4. Runtime configuration was not read from where the docs say (correctness)

- No code under `runner/`, `harness/`, `tools/` or `deploy/` reads Secrets Manager. The secret
  `proposal-orchestrator/env-config` (DC-20, DC-21, DC-33 to DC-35) was verified for its *content*,
  but the runtime took its configuration from shell `export`s in `run.sh` and the SSM commands.
- `SKILL_MODEL` exported in the guide does nothing on the Bedrock path. `runner/skill_runtime.py`
  pins `SKILL_MODEL = "claude-opus-4-8"` as a constant for the CLI path. The Converse model comes
  from `ORCHESTRATOR_TRANSPORT_MODEL` or the preset default (`us.anthropic.claude-sonnet-4-6`).
- The Converse backend reads its region from `AWS_REGION`, defaulting to `us-east-1`
  (`runner/transport/config.py`). The guide sets only `AWS_DEFAULT_REGION`. This worked by accident
  in us-east-1 and would silently call the wrong region anywhere else.
- `BEDROCK_CONVERSE_US` is the only Converse preset. The EU presets use the `bedrock` backend
  (`bedrock-mantle.{region}.api.aws`), which no VPC endpoint covers.

### F5. Phase 8 decomposed drafting bypasses the transport layer (security and DC-38 blocker)

`runner/decomposed_drafting.py` (the live drafter, around line 304) imports
`runner.claude_transport.invoke_claude_text` directly instead of resolving the provider through
`resolve_provider_config()`. `runner/claude_transport.py` has no production-mode guard. So:

- On the private host there is no `claude` binary (DC-31), and Phase 8 sub-section drafting fails.
  DC-38 cannot pass.
- On a workstation with production mode on, the drafter would still call the Claude CLI. That is
  exactly the backend DC-33 is meant to refuse.

The skill runtime and `semantic_dispatch` do route through the transport layer correctly. This is
the one known bypass. A ticket must route it through the transport layer (or refuse under
production mode), with a test that fails today.

### F6. A production-allowed backend that the network does not support (hygiene)

`PRODUCTION_BACKENDS = {"bedrock_converse", "bedrock"}`. The `bedrock` backend targets
`bedrock-mantle.{region}.api.aws`, which has no VPC endpoint in this design. On the host it fails
closed (no route). Either drop it from the production set or document that only
`bedrock_converse` is valid on the private host.

### F7. The S3 gateway path is an exfiltration route (security, must fix)

The host SG allows TCP 443 to the S3 prefix list (deployment guide §2, rule
`sgr-0cc4c7112cd8277c2`), and the S3 gateway endpoint kept AWS's **default full-access endpoint
policy**. Traffic to *any* S3 bucket in the region therefore leaves the host. That includes buckets
owned by other accounts, reachable with presigned URLs or foreign credentials, so no IAM permission
on the host is needed. The old risk assessment only considered the host role's own S3 permissions.

Fix: an S3 gateway endpoint policy restricted to the project's own buckets (for example,
`aws:ResourceAccount` = the new account, plus explicit bucket ARNs; allow the AL2023 repository
buckets only if OD9 adds them). Also scope the host role's S3 permissions to the deploy bucket's
prefixes. Add a negative test: a presigned PUT to a bucket outside the account is refused.

### F8. Gaps the old programme declared but never closed

| Gap | Where declared | Rebuild action |
|---|---|---|
| S3 Block Public Access on the trail bucket not evidenced | DC-25 notes | Enable it on the account and on each bucket; evidence it |
| EBS default encryption not verified; `DeleteOnTermination` not confirmed | RSK-14 | Enable account-level EBS default encryption before the first launch; evidence both |
| IMDSv2 not enforced (`run-instances` set no `--metadata-options`) | not declared | Require IMDSv2 (`HttpTokens=required`, hop limit 1) at account default and at launch |
| MFA on operator identities "institutional responsibility" | RSK-02 | Root MFA, plus a non-root admin identity with MFA for daily work (OD11) |
| In-host negative tests for DC-15 not collected | DC-15 notes | Collect them in the new evidence |
| DC-07 wording never updated after the S3 rule | deployment guide §2 | Update it in the new register |
| Risk register review due 2026-09-03 not held | risk register §5 | Hold it as part of R13 |
| `collect_evidence.ps1` hard-codes old IDs and overwrites the baseline | script header | Parameterise it (R12) |

### F9. Region is hard-coded throughout

`us-east-1` is fixed in the deployment guide, operational procedure, data flow document, ADR-001,
the AN12 runbook (its `--region us-east-1` lines, and the rule that A3/A5 ids must be `us.` or bare
ids "in us-east-1"), `collect_evidence.ps1` and the transport tests
(`tests/test_transport_config.py`, `tests/test_transport_presets.py`).
`tests/test_anonymisation_host_runbook.py` parses the runbook's `python -m` lines, so editing the
runbook is a code change with tests. Moving to an EU region (OD1) has a measurable cost and must be
its own ticket.

### F10. Things that were right and carry over unchanged

- No IGW/NAT route, ever. NAT for package installs was rejected (ADR-001 D8). Keep that rejection.
- The offline bundle route (D8) and the AN12 interpreter amendment (A1): wheels pinned by hash,
  `--no-index --require-hashes`, and `runner.offline_bundle verify` with `--probe-no-internet`.
- SSM Run Command for long operations (sessions time out).
- Bedrock model invocation logging stays **disabled** (DC-28, DC-29).
- `ORCHESTRATOR_PRODUCTION_MODE=true` and `ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata`.
- CloudTrail with log-file validation, CMK, versioned bucket, deny-insecure-transport, lifecycle.
- Flow logs to a CMK-encrypted log group with 90-day retention.
- No `aws:SourceVpc` condition on the EC2 trust policy, because IMDS does not traverse VPC endpoints
  (deliberate, DC-13).
- `.git/` marker directory under the install root (`find_repo_root()`).

---

## 5. Decisions the operator must make

The ticketing agent should open one decision ticket (R0) that records these in Tier 4
(`docs/tier4_orchestration_state/decision_log/`) before any build ticket that depends on them. The
"suggested default" is what the build tickets should assume if the operator accepts it.

| Id | Question | Options | Suggested default | What depends on it |
|---|---|---|---|---|
| OD1 | **Region** for the host, endpoints, key, trail and Bedrock | (a) us-east-1 with `us.` profiles, as before. Lowest change; the AN12 runbook and tests work as written. Proposal IP transits to the US under the DPF/SCC basis in the data flow doc §4.3. (b) An EU region with `eu.` profiles. Stronger residency story for ELTE; needs F4 and F9 fixes plus doc amendments, and model availability must be confirmed first. | (a) for the November deadline, unless ELTE's DPO or the funding terms require EU processing. Record the reason either way. | Everything regional; IAM resource lists; AN12 runbook; data flow doc; ADR amendment |
| OD2 | **Runtime identity** (F1) | (a) One host role that is itself hardened: boundary and explicit deny attached, boundary extended for exactly the SSM actions `AmazonSSMManagedInstanceCore` needs, plus a narrow deploy-bucket read. (b) Two roles: the host role keeps SSM and S3, and the application assumes the bedrock role through STS. Needs a trust-policy change and code that assumes the role. | (a). Simpler, no code change, and the hardened identity is the one CloudTrail shows. | IAM, KMS key policy, secret policy, endpoint policy, evidence |
| OD3 | **VPC** (F3) | (a) A dedicated VPC with no IGW. (b) Reuse the default VPC as before. | (a) | Network tickets |
| OD4 | **Availability zones** for interface endpoints | 1 AZ (half the endpoint cost; one AZ outage stops work) or 2 AZs (as before) | 1 AZ while on credits and a single host; revisit for long-term use | Cost (§8) |
| OD5 | **Endpoint lifecycle** | Always on, or created per working session from a template and deleted afterwards | Per session, from a separate stack, until the DN work is done | IaC layout; operational procedure |
| OD6 | **How the infrastructure is written** | CloudFormation (native, free, runs from CloudShell), plain CLI scripts (as before), or Terraform (needs installing) | CloudFormation, split into stacks: base (network, IAM, KMS, audit) and endpoints-and-host (the costed part) | Every build ticket |
| OD7 | **Model set** | Which Claude models the host may call: orchestrator skills; AN12 A3 and A5 (must differ); the assessor (must differ from the drafter in every id form, AN1c) | Decide after R1 shows which models the new account can call in the chosen region; list them by profile id | Invoke policy, explicit deny, endpoint policy, runbook arguments |
| OD8 | **Configuration source** (F4) | (a) The launcher reads `proposal-orchestrator/env-config` from Secrets Manager and exports it. (b) Drop the secret; keep a root-owned env file and evidence that instead. | (a). Keeps ADR-001 D4 true in practice. | Secret, code ticket, DC-33 to DC-35 evidence |
| OD9 | **Host image and size** | AL2023 x86_64 as before (system Python 3.9; the AN12 bundle brings 3.11). Instance type: t3.micro (smoke), t3.medium (full DAG, recommended in guide §9), larger for PyMuPDF work | AL2023 x86_64, t3.medium, stopped when idle. Check that the Free plan allows it. | Bundle platform tags; cost |
| OD10 | **When to leave the Free plan** | Stay on credits as long as possible; upgrade when Bedrock or the workload needs it | Upgrade only after the ELTE financial office approves the reimbursement route, with ELTE billing details entered at the same moment. **Only the operator does this.** | Bedrock availability; budget alarms |
| OD11 | **Admin identity** | Keep using root, or create an IAM Identity Center user (or IAM admin user) with MFA for daily work and lock root away | Identity Center user with MFA; root MFA on and unused | R1, CloudTrail attribution |
| OD12 | **Is DC-38 in scope now?** | Fix F5 and run the full DAG in this redeployment, or limit verification to the AN12/AN13/V14 workloads and keep DC-38 deferred | Keep DC-38 deferred, but fix F5 anyway, because it is a production-mode bypass | Code ticket priority |
| OD13 | **Cost guardrails** | Budget amounts and alert levels; whether an AWS Budgets action stops the instance automatically | Two budgets: 10 USD/month while on credits; after the upgrade, the approved HUF amount converted to USD with alerts at 50/80/100%. No automatic actions on IAM. | R1, R14 |

---

## 6. Work to be ticketed

The ticketing agent may re-slice, but must keep the dependencies and the exit conditions. "Operator"
means the step needs the operator's AWS session (CloudShell or the console). Unless the operator
grants credentials explicitly, agents write templates, scripts and checklists, and do not hold AWS
credentials.

| Id | Ticket | Depends on | Exit condition |
|---|---|---|---|
| R0 | Record OD1–OD13 as a Tier 4 decision record | none | Decision record committed; each OD has an answer or an explicit "deferred" with its consequence |
| R1 | **Account baseline** (operator, guided): root MFA; admin identity per OD11; verify the budget e-mail recipient; budgets per OD13; account-level EBS default encryption; account-level S3 Block Public Access; EC2 IMDSv2 default (`modify-instance-metadata-defaults`); clean up the Explore AWS leftovers in every region used (EC2, key pair, SG, Lambda, RDS and its snapshots); set the console home region to the OD1 region | R0 (OD1, OD11, OD13) | Checklist evidence (CLI output) for each item; zero running billable resources outside the plan |
| R2 | **Bedrock access check** (operator, guided), in the OD1 region: Anthropic use-case form; Marketplace subscription if asked; `list-inference-profiles`; one Converse call per candidate model from CloudShell; service quotas (tokens and requests per minute) for each candidate; whether the Free plan allows these calls at all | R1 | A table of usable model ids and their quotas. If the Free plan blocks Bedrock, report it to the operator; this feeds OD10. Input to OD7. |
| R3 | **IaC skeleton**: repository location (suggest `deploy/aws/`), naming and tags (`project=proposal-orchestrator`), parameters (account id, region, AZs, model list, bucket names with an account suffix); a lint step (`cfn-lint` or equivalent) runnable on the workstation | R0 (OD6) | Templates validate locally; no old ID anywhere (asserted by a test that greps for `232538551827`, the old `vpce-`/`sg-`/`subnet-` ids and `i-0045af36dbf5f1272`) |
| R4 | **Network base stack**: VPC per OD3 with DNS hostnames and support on; private subnet(s) per OD4; route table with local and S3 prefix list only; host SG (egress 443 to the VPCE SG, plus 443 to the S3 prefix list); VPCE SG (ingress 443 from the host SG only, no egress); S3 gateway endpoint **with a restrictive policy** (F7) | R3 | Stack deploys at no hourly cost; evidence for DC-06, PL-8 and the SG halves of DC-03/DC-07; route table shows no `igw-` or `nat-` |
| R5 | **IAM stack** per OD2: host role and instance profile; invoke policy built from the OD7 profile ids and their routed regions (F2); supporting-services policy; explicit deny updated for the chosen profile prefix; boundary covering exactly what the runtime role needs; flow-logs role. No temporary policies. | R3, R0 (OD2, OD7), R2 | IAM simulations: allowed invoke per model; explicit deny for admin, non-Claude, `global.` (unless chosen), s3/ec2/iam; the runtime role has the boundary attached (DC-09 to DC-13 now evidenced **on the runtime role**) |
| R6 | **KMS**: CMK, alias `alias/proposal-orchestrator`, rotation on; key policy with root, the runtime role per OD2, CloudTrail (SourceArn), CloudWatch Logs (log-group prefix) | R5 | DC-18, DC-19 evidence |
| R7 | **Audit stack**: trail bucket (versioning, BPA, bucket policy as old with new ARNs, lifecycle 90d → GLACIER_IR, expire 365d); trail with validation and CMK; flow-log log group (CMK, 90d) and flow logs on every subnet; confirm Bedrock invocation logging is unset | R4, R6 | DC-08, DC-23 to DC-25, DC-27 to DC-30 evidence (DC-26 waits for R10) |
| R8 | **Secret** per OD8: `proposal-orchestrator/env-config` with CMK and a resource policy naming only the runtime identity (and an admin role if one exists); values `ORCHESTRATOR_TRANSPORT_PRESET`, `ORCHESTRATOR_PRODUCTION_MODE=true`, `ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata`, `AWS_REGION`, `ORCHESTRATOR_TRANSPORT_MODEL` | R5, R6 | DC-20, DC-21 evidence; no secret value in any evidence file |
| R9 | **Code: runtime configuration** (F4, F6, optionally F9): a launcher that loads the secret (OD8) and exports `AWS_REGION`; correct the guide's variable names (`ORCHESTRATOR_TRANSPORT_MODEL`, not `SKILL_MODEL`); if OD1 = EU, add a Converse preset for the region and parameterise the tests; decide F6 | R0 | Tests with `py -3.10`; a test that a missing `AWS_REGION` under production mode is refused or logged, per the ticket's choice |
| R10 | **Code: Phase 8 drafter through the transport layer** (F5) | R0 (OD12 sets priority) | A test that fails today: under `ORCHESTRATOR_PRODUCTION_MODE=true` the decomposed drafter never reaches `claude_transport`; it reaches the Converse backend, or refuses with a production-mode error |
| R11 | **Endpoints-and-host stack** (the part that costs money, created per OD5): interface endpoints `bedrock-runtime`, `sts`, `secretsmanager`, `ssm`, `ssmmessages`, `ec2messages` with private DNS; Bedrock endpoint policy naming the runtime role and the OD7 resources; host per OD9 with no public IP, IMDSv2 required, encrypted gp3 root with `DeleteOnTermination=true`, and the instance profile. **Operator approves each creation.** | R4–R8, R0 (OD4, OD5, OD9) | Endpoints `available`; SSM Run Command reaches the host; DC-01, DC-02, DC-04, DC-05, DC-14, DC-37 evidence; the stack deletes cleanly and leaves R4–R8 intact |
| R12 | **Verification tooling and evidence**: parameterise `collect_evidence.ps1` (account, region and all IDs from stack outputs; output to a new tree such as `docs/infrastructure_security/evidence_v2/` or a dated folder); add F7's negative test and the in-host DC-15 tests; produce control register v2, keeping v1 as history | R11 | All controls re-evidenced in the new account; the register shows each DC's status with new evidence paths; DC-40 re-assessed (still N/A unless the account joins an Organization) |
| R13 | **Documentation amendments**: ADR-001 amendment A2 (new account; F1/F2/F3/F7 changes; region per OD1); risk register (new account, review held, RSK-14 closed or restated, a new risk for F7 if not fully closed); data flow doc (region, transfers); operational procedure (stack lifecycle, start/stop, teardown); deployment guide (new IDs from stack outputs, corrected variables). Draft first, operator approves, then apply, as was done for A1. | R12 | Approved amendments applied; no document cites an old ID as current |
| R14 | **Operations and cost**: start/stop and teardown scripts for the endpoints-and-host stack; a weekly cost check against credits and the approved HUF amount; an upgrade checklist for OD10 (ELTE billing details, VAT number, tax settings, budgets raised), operator-only | R11 | Scripts tested once end to end; the checklist exists |
| R15 | **Deploy and run AN12** on the new host per `plans/msca_dn_an12_host_runbook.md`, with the new bucket name and the OD1 region and OD7 models substituted (operator) | R11, R12 (at least DC-01, DC-02, DC-32 verified) | The AN12 criteria as the runbook defines them; a successor decision record to `msca-dn-an12-offline-bundle_2026-10-16` |
| R16 | **Orchestrator bundle and DC-38** (only if OD12 says so) | R10, R11 | DC-38 VERIFIED_PASS or VERIFIED_FAIL with the run summary as evidence |

### Order that keeps credits safe

R0 → R1 → R2 → R3 → R4, R5, R6, R7, R8 (no hourly cost) → R9, R10 in parallel (code only) →
R11 (hourly cost starts) → R12 → R15 → R13, R14 → R16. Nothing billable by the hour (interface
endpoints, EC2, NAT, which is never used) is created before R11, and R11 needs the operator's
explicit go.

---

## 7. Constraints every ticket inherits

- `CLAUDE.md` governs. None of this work amends the constitution, touches Tier 1–3 sources, or
  dispatches a runner phase. The operator dispatches phases.
- Never add an Internet Gateway, a NAT Gateway, a `0.0.0.0/0` route, or a `0.0.0.0/0` egress rule
  on the host SG, not even temporarily (ADR-001 D2, D7, D8).
- Never enable Bedrock model invocation logging.
- Never put credentials, secret values, prompt text or proposal content into the repository,
  evidence files, logs or tickets. Evidence records metadata only (CG5 rule: "Do NOT capture the
  secret value itself").
- No resource name or policy may contain an ID from the old account (R3 test).
- Creating anything with an hourly charge needs the operator's explicit go in the session. Upgrading
  the account to the paid plan, and entering billing or tax details, is **only the operator's** to
  do (OD10).
- The operator works from Windows PowerShell and from CloudShell. Give commands in both forms where
  quoting differs, as the old guide did.
- Tests run with `py -3.10`, as in the rest of the repository.
- Every infra change is logged in the worklog with the same fields as before (timestamp, control
  IDs, action, evidence requested and received, verification result, next action).

---

## 7a. Evidence protocol: how a ticket gets ticked

The operator performs every AWS step (console or terminal). Agents prepare the steps and verify
the results; they never tick a ticket on their own say-so.

**Per ticket, the agent first writes a step sheet** at
`docs/infrastructure_security/evidence_v2/<ticket-id>/STEPS.md`: numbered steps, the exact
command for each (PowerShell and CloudShell forms where quoting differs) or the exact console path,
the evidence file each step must produce, and the PASS criterion for each file.

**The operator runs the steps and saves the outputs** into the same folder:

- File name: `<ticket-id>_<NN>_<short-name>.<json|txt|png>`, for example
  `R4_03_route-table.json`. Use `--output json` and redirect to the file wherever the CLI allows.
- Console-only steps: a screenshot (`.png`), or the page text pasted into a `.txt`.
- Host-side steps (SSM Run Command): save the `get-command-invocation` output, including `Status`
  and `StandardOutputContent`.
- One `RUNLOG.md` per ticket: date and time (UTC), who ran each step, deviations from `STEPS.md`,
  and any error together with what was done about it.

**Never save in evidence:** secret values, access keys, session tokens, passwords, MFA seeds,
prompt or proposal text, or model responses beyond a fixed test string such as `OK` or
`DEPLOY_OK`. Before committing, the operator checks each file for these. The agent re-checks and
refuses the evidence if it finds any (`grep` for `AKIA`, `aws_secret`, `SecretString`,
`SessionToken`).

**The agent then verifies:** it reads every file against the PASS criteria in `STEPS.md` and
writes `VERIFICATION.md` in the folder. It gives one line per criterion: PASS / FAIL /
MISSING, the evidence file, and the reason.

**A ticket is ticked only when:**

1. every criterion in `VERIFICATION.md` is PASS (or N/A with a stated reason);
2. control register v2 is updated for every DC the ticket touches, with the new evidence paths;
3. a worklog entry exists (timestamp, control IDs, action, evidence received, verification result,
   next action);
4. the operator confirms in session. The agent then marks the ticket done.

A FAIL produces a follow-up step sheet in the same folder (`STEPS_fix1.md`). It is never fixed
by editing the evidence.

**Resource IDs:** after each stack or creation step, the operator saves the stack outputs, or the
create command's output, as `<ticket-id>_outputs.json`. Later step sheets take IDs only from these
files, never from memory or from the old docs.

## 8. Cost model (to verify, not to rely on)

Prices below are approximate AWS list prices for us-east-1 as known at writing. Ticket R14 must
check them on the AWS pricing pages for the OD1 region before reporting any figure to the operator.

| Item | Approximate unit price | Old design | With OD4 = 1 AZ |
|---|---|---|---|
| Interface endpoint | about 0.01 USD per endpoint per AZ per hour, plus about 0.01 USD/GB | 6 endpoints × 2 AZ ≈ 0.12 USD/h ≈ 86 USD per 30 days | ≈ 43 USD per 30 days |
| EC2 t3.medium | about 0.04 USD/h | ≈ 1 USD per day running | Stop when idle |
| EBS gp3 | about 0.08 USD per GB-month | 8–30 GB | — |
| KMS CMK | about 1 USD/month, plus requests | 1 key | — |
| Secrets Manager | about 0.40 USD per secret per month | 1 secret | — |
| CloudTrail | first management-event trail free; S3 storage small | 1 trail | — |
| CloudWatch Logs (flow logs) | about 0.50 USD per GB ingested | small | — |
| Bedrock tokens | per model and per million tokens; check the Bedrock pricing page for each OD7 model | Old Phase 1 smoke run: about 439k tokens in 6 minutes (ADR-001 D1) | — |

Implications:

- Always-on endpoints in two AZs would use the 200 USD credit in a little over two months with no
  other activity. That is why OD4 and OD5 matter.
- Bedrock tokens, not infrastructure, will dominate once the DN work starts. R2's quota table and
  R14's weekly check should report tokens per run.
- The funding is about 300,000 HUF. Convert it at the day's rate when OD13 sets the post-upgrade
  budget.

---

## 9. Old-to-new resource map

The new IDs come from stack outputs; nothing below is reused. Logical names may stay the same,
except that bucket names must change because they carry the account id.

| Logical resource | Old value (dead) | New |
|---|---|---|
| Account | `232538551827` | `797661577394` |
| Region | `us-east-1` | OD1 |
| VPC | `vpc-050a09774560fd774` (default VPC, 172.31.0.0/16) | Dedicated VPC (OD3) |
| Private subnets | `subnet-023c6e3ea5451ea47`, `subnet-01d969bb1421a3042` | OD4 |
| Private route table | `rtb-085481996de5e3ed9` | Stack output |
| Host SG / VPCE SG | `sg-076f724aed2429771` / `sg-013d5e4d4eb55dfd9` | Stack outputs |
| S3 prefix list | `pl-63a5400a` | Region-specific; look it up |
| Endpoints | bedrock-runtime `vpce-0843d225c5b1ef6d5`, secretsmanager `vpce-08ba482a3b11f7d64`, sts `vpce-067abd500c89e2bc4`, s3 `vpce-0ee5648ce182bf85a`, ssm `vpce-06a268f54ecc1f754`, ssmmessages `vpce-0824e9fbb2f099e37`, ec2messages `vpce-0ec79b44974bfd85b` | Stack outputs |
| Roles | `proposal-orchestrator-bedrock-role`, `proposal-orchestrator-ec2-ssm-role`, `proposal-orchestrator-flow-logs-role` | Per OD2 |
| Instance profile | `proposal-orchestrator-ec2-ssm-profile` | Per OD2 |
| KMS key | `887638e8-358b-4664-9270-368aec0ea1f1` | New key, same alias |
| Secret | `proposal-orchestrator/env-config` | Same name, new ARN |
| Trail / bucket | `proposal-orchestrator-bedrock-trail` / `proposal-orchestrator-cloudtrail-232538551827` | Same trail name / `proposal-orchestrator-cloudtrail-797661577394` |
| Deploy bucket | `proposal-orchestrator-deploy-232538551827` | `proposal-orchestrator-deploy-797661577394` |
| Flow logs | `fl-03c1ed4c967c50073`, `fl-0948b876901308e70`, group `/proposal-orchestrator/vpc-flow-logs` | New flow logs, same group name |
| Host | `i-0045af36dbf5f1272` (t3.micro, AL2023) | OD9 |

---

## 10. Done means

The redeployment is complete when all of the following hold:

1. Control register v2 shows every control VERIFIED_PASS, NOT_APPLICABLE with a reason, or DEFERRED
   with a reason (DC-38 per OD12). The evidence was collected in account `797661577394` by the
   parameterised script.
2. The identity that CloudTrail shows calling Bedrock is the hardened identity, with the boundary
   and explicit deny attached (F1 closed).
3. No temporary IAM policy exists (F2 closed). A presigned PUT to an outside bucket fails from the
   host (F7 closed).
4. `runner.offline_bundle verify --probe-no-internet` passes on the new host (private endpoint
   resolution and no internet route).
5. ADR-001 amendment A2 and the other document amendments are approved and applied.
6. The billable stack can be deleted and recreated from the templates, and a cost check against
   credits has run at least once.

---

## 11. Out of scope

- Running AN13, V14 or any proposal content through the new environment. Those are operator runs,
  done after R15.
- Choosing between OCRE, a direct AWS contract or card reimbursement. That is the ELTE financial
  office's and the operator's decision, recorded elsewhere.
- Self-hosted models (`docs/internal_llm_migration_plan.md`).
- CI/CD for deployments (ADR-001 D8 trade-off, P2-4). It stays manual.
