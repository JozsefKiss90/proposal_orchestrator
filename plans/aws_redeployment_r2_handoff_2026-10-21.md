# AWS redeployment: handoff for R2 (Bedrock access check, closing OD7)

| Field | Value |
|---|---|
| Date | 2026-10-21 |
| Branch at writing | `msca-dn-pre-eval` at `399ee02` (R1 committed) |
| For | The agent that runs ticket R2 with the operator in a new session |
| Read first | `CLAUDE.md`; `plans/aws_redeployment_tickets.md` (R2 and the inherited constraints at the top); `plans/aws_redeployment_handoff_2026-10-21.md` §4 F2, §5 OD7, §7, §7a; `docs/infrastructure_security/evidence_v2/README.md` |
| Status | E0, R0, R1 done. R9e closed N/A then **reopened**. R2 is next; R3, R9, R9e, R10 are also on the frontier. |

## 1. What changed since the first handoff (read this before anything else)

The first handoff assumed a standalone account in us-east-1 with a root user. R1 measured otherwise.
These records govern; the R0 record's OD1 and OD11 are superseded:

| Fact | Record / evidence |
|---|---|
| Account `797661577394` was created through **"Sign up for AWS (new)"**: it is a *project account* ("Future Unicorn") in an AWS-managed organization `o-81s4kwxswn` (management account `323258891184`, not ours to touch). No usable root user. | `aws-redeployment-od11-admin-identity-r2_2026-10-21.json`; `evidence_v2/R1/R1_00_*`, `R1_32_aws-settings-projects.png` |
| **Admin identity (OD11-r2):** the operator's Builder ID with MFA → `assumed-role/AccountFullAccessRole/<session>` (`AdministratorAccess`). No IAM users, no access keys. IAM console users are impossible here. | same |
| **Region (OD1-r1): eu-north-1**, Bedrock through **`eu.` cross-Region inference profiles**. AWS-managed SCPs deny every regional action outside eu-north-1; us-east-1 and us-west-2 allow only global services (statement `UsEast1Partitional`). | `aws-redeployment-od1-region-r1_2026-10-21.json`; `R1_25`, `R1_26`, `R1_27` |
| **Free plan**, ACTIVE, ~200 USD credits, ends 2027-04-19. OD10 unchanged: no upgrade before ELTE approval, operator only. | `R1_00_plan-state.json` |
| Budget e-mail alerts cannot be delivered (SCP denies notification-contact verification). Credits and alert states are watched **by CLI at the start of every session** (R1-D2). | `aws-redeployment-r1-baseline-deviations_2026-10-21.json` |
| Already measured for R2: 26 Anthropic profiles visible in eu-north-1 (`eu.` and `global.`), 14 Anthropic models, all `INFERENCE_PROFILE` only; one Converse call through `eu.anthropic.claude-haiku-4-5-20251001-v1:0` returned `OK`. So the Free plan does **not** block Bedrock, and the use-case form is evidently already accepted for that model. | `R1_28_*`, `R1_29_*` |

## 2. How the operator works (keep doing this)

- The operator runs every AWS command; the agent writes the step sheet, reads the pasted output, keeps
  `RUNLOG.md` from what the operator reports in session (marked as such), and verifies.
- **CloudShell stays in us-east-1** (its home dir `~/R1`, `~/R2` lives there; CloudShell homes are per
  Region). Every regional command names `--region eu-north-1`. IAM, STS, Budgets are global.
- Workstation CLI: `aws login --profile po-r1` (aws-cli 2.34.54, profile Region eu-north-1). In
  PowerShell always `| Out-File -Encoding utf8 <file>`, never `>`.
- Evidence comes home by zip: `cd ~ && zip -r R2_evidence.zip R2` → Actions → Download file →
  `Expand-Archive` into `$env:TEMP`, `Copy-Item … docs\infrastructure_security\evidence_v2\R2\`.
- Scripts uploaded to CloudShell: check they arrived (`ls ~`) and strip CR (`sed -i 's/\r$//'`).
  `*.sh` is kept at LF by `.gitattributes`.
- Before accepting evidence: `py -3.10 -m tools.evidence_secret_scan docs/infrastructure_security/evidence_v2/R2`.
- The agent's device shell cannot delete files, so it cannot run `git commit`; the operator commits.
- Lesson from R1: a probe that fails on a placeholder id is not evidence of permission. Use real ids,
  or say "inconclusive".

**Session-start check (R1-D2), first step of every step sheet:**

```bash
aws freetier get-account-plan-state --output json
aws budgets describe-budgets --account-id 797661577394 --query 'Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}' --output json
aws budgets describe-notifications-for-budget --account-id 797661577394 --budget-name "My Monthly Cost Budget" --query 'Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}' --output json
```

## 3. R2 as it now reads

Exit conditions from the ticket, adapted to eu-north-1 and `eu.` profiles:

1. A table of each usable candidate model by **`eu.` profile id**, with its token and request quotas
   in eu-north-1 and the **EU Regions it routes to** (`aws bedrock get-inference-profile --region
   eu-north-1 --inference-profile-identifier <id>` → `models[].modelArn`). R5's invoke policy needs
   exactly these foundation-model ARNs (F2).
2. One Converse call per candidate (maxTokens ≤ 5, fixed string `OK`), each saved as evidence.
3. Quotas: `aws service-quotas list-service-quotas --service-code bedrock --region eu-north-1`
   (and `list-aws-default-service-quotas`), filtered to the candidates' cross-Region tokens-per-minute
   and requests-per-minute lines. Record applied value and default.
4. **OD7 successor decision record**, settled with the operator: the orchestrator model; two
   **distinct** models for AN12 A3 and A5; an assessor that differs from the drafter in every id form
   (AN1c, `harness-an1c-shared-provider-independence_2026-10-15.json`).
5. If any candidate is refused (form, Marketplace, SCP), record the error verbatim (no secrets) and
   stop for that model; report it to the operator.

Points to settle with the operator while doing it:

- **`global.` profiles route outside the EU.** OD1-r1 chose EU processing; propose excluding
  `global.` and denying it in R5's explicit deny, unless the operator decides otherwise.
- Current code pins, for the OD7 discussion (R2 changes no code): `runner/skill_runtime.py`
  `SKILL_MODEL`, `runner/semantic_dispatch.py` `AGENT_MODEL`, `runner/decomposed_drafting.py`
  `_DRAFTER_MODEL` are all `claude-opus-4-8` (CLI transport names). On the host the model comes from
  `ORCHESTRATOR_TRANSPORT_MODEL` (R8/R9). `runner/transport/config.py` has only
  `BEDROCK_CONVERSE_US` (us-east-1, default `us.anthropic.claude-sonnet-4-6`); the eu-north-1 preset
  is R9e's job, not R2's.
- `plans/msca_dn_an12_host_runbook.md` §A3/A5 and the assessor step still say `us.` / us-east-1;
  R9e rewrites them. R2 only supplies the ids.
- Every Converse call spends credits; keep calls tiny. Nothing in R2 is billable by the hour.

## 4. Files

| Path | What |
|---|---|
| `docs/infrastructure_security/evidence_v2/R2/` | Create it: `STEPS.md` (from `_templates/`), `RUNLOG.md`, evidence `R2_<NN>_<name>.json`, `VERIFICATION.md` |
| `docs/infrastructure_security/aws_hardening_control_register_v2.md` | Update DC-36 (model availability) when R2 verifies |
| `docs/infrastructure_security/aws_hardening_worklog_v2.md` | One entry per R2 milestone, same fields |
| `docs/tier4_orchestration_state/decision_log/` | OD7 successor record, e.g. `aws-redeployment-od7-model-set_<date>.json`, in the style of the R1 records |

## 5. Done for R2

Every `VERIFICATION.md` criterion PASS (or N/A with reason), register v2 DC-36 updated, worklog
entry, OD7 record committed by the operator, operator confirms in session. Then tick R2 in
`plans/aws_redeployment_tickets.md`.
