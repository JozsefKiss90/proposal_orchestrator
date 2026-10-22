# R2 — Bedrock access check, closing OD7: step sheet

> **Extended by `STEPS_fix1.md` (2026-10-21).** Step 07 found four of the five candidates refused for
> this account. Fix 1 adds steps 13–15 (newest usable Opus and Sonnet), run before steps 08–12. This
> sheet is otherwise unchanged.

| Field | Value |
|---|---|
| Ticket | `R2` in `plans/aws_redeployment_tickets.md` |
| Handoff exit condition | `plans/aws_redeployment_handoff_2026-10-21.md` §6, R2, as adapted in `plans/aws_redeployment_r2_handoff_2026-10-21.md` §3 |
| Decisions applied | OD1-r1 eu-north-1 with `eu.` profiles (`aws-redeployment-od1-region-r1_2026-10-21`); OD11-r2 Builder ID → `AccountFullAccessRole` (`aws-redeployment-od11-admin-identity-r2_2026-10-21`); R1-D2 session-start check (`aws-redeployment-r1-baseline-deviations_2026-10-21`); OD10 Free plan, no upgrade |
| Written by / on | agent (Claude) / 2026-10-21 |
| Account / region | `797661577394` / `eu-north-1` (Bedrock, Service Quotas); IAM, STS, Budgets, Free Tier are global |
| IDs taken from | `../R1/R1_28_claude-profiles-eu-north-1.json` (profile ids). R2 creates no resource and writes no `R2_outputs.json`. |
| Controls touched | DC-36 (model availability). Feeds DC-10 / DC-16 (R5 invoke policy and approved Regions) and the R11 endpoint policy. |
| Hourly cost created | none. Step 07 makes one Converse call per candidate, at most 5 output tokens each (well under 0.05 USD in total, paid from credits). |

## Before you start

- Run every step yourself, in order. Report each one in session; the agent keeps `RUNLOG.md` from your
  reports and marks it so.
- **Where commands run.** All AWS steps run in **CloudShell in us-east-1**, in `~/R2` (CloudShell homes
  are per Region; `~/R1` lives there too). Every regional command names `--region eu-north-1`. CloudShell
  writes UTF-8 and needs no workstation credentials, so the commands are given in that one form.
  PowerShell is used only in step 12 (bringing the evidence home). If you ever run an AWS command in
  PowerShell instead, pipe it to `Out-File -Encoding utf8 <file>`; never `>`.
- Paste the multi-line blocks into CloudShell as they are; they are loops over the candidate file.
- Never save secret values, access keys, session tokens, passwords or MFA material. The only model
  output allowed in evidence is the fixed string `OK`. Do not change the test prompt.
- No Internet Gateway, NAT Gateway, `0.0.0.0/0` route or egress rule. Do **not** turn on Bedrock model
  invocation logging. Do not upgrade the account, accept a paid offer or enter billing or tax details
  (OD10).
- **Do not use `global.` profiles** in any step. They may route outside the EU (OD1-r1 chose EU
  processing); whether R5 denies them explicitly is settled in session (see "To settle in session").
- If a step fails, stop, report the error, and do not improvise a fix. The only pre-planned retry is the
  one in step 07.

---

## Steps

### Step 01 — Session-start check: credits, budget, alert states (R1-D2)

What it does: confirms the Free plan is active, the credits are intact and no budget alert is in
`ALARM` before anything spends credits.

```bash
mkdir -p ~/R2 && cd ~/R2
aws freetier get-account-plan-state --output json > R2_01_plan-state.json 2>&1
aws budgets describe-budgets --account-id 797661577394 \
  --query 'Budgets[].{name:BudgetName,limit:BudgetLimit.Amount,spend:CalculatedSpend.ActualSpend.Amount}' \
  --output json > R2_01_budgets.json 2>&1
aws budgets describe-notifications-for-budget --account-id 797661577394 --budget-name "My Monthly Cost Budget" \
  --query 'Notifications[].{type:NotificationType,threshold:Threshold,state:NotificationState}' \
  --output json > R2_01_budget-notifications.json 2>&1
cat R2_01_plan-state.json R2_01_budgets.json R2_01_budget-notifications.json
```

| Evidence file | PASS criterion |
|---|---|
| `R2_01_plan-state.json` | `accountPlanType` = `FREE`; `accountPlanStatus` = `ACTIVE`; `accountPlanRemainingCredits.amount` ≥ `199.00` (R1 left 199.99 and nothing billable runs); `accountPlanExpirationDate` starts `2027-04-19` |
| `R2_01_budgets.json` | Exactly one budget, `My Monthly Cost Budget`, `limit` = `10.0`, `spend` < `8.5` (the 85 % alert). `po-alert-test` is gone (deleted in R1). |
| `R2_01_budget-notifications.json` | Three notifications (ACTUAL 85, ACTUAL 100, FORECASTED 100), each `state` = `OK` |

**STOP rule.** If the plan is not `ACTIVE`, the credits are below 199.00 USD, or any notification is in
`ALARM`, stop here and report it. Nothing below runs until the agent and you have found the cause.

### Step 02 — Who is calling

What it does: records that CloudShell runs as the OD11-r2 identity in the right account.

```bash
cd ~/R2
aws sts get-caller-identity --output json > R2_02_caller-identity.json 2>&1
jq -r '.Account, .Arn' R2_02_caller-identity.json; echo "AWS_REGION=$AWS_REGION"
```

Write the printed `AWS_REGION` (expected `us-east-1`) in your report.

| Evidence file | PASS criterion |
|---|---|
| `R2_02_caller-identity.json` | `Account` = `797661577394`; `Arn` starts with `arn:aws:sts::797661577394:assumed-role/AccountFullAccessRole/` |

### Step 03 — Anthropic inference profiles in eu-north-1 (read-only)

What it does: a fresh listing with profile ARNs and routed Regions, so R2 does not rely on R1's copy.

```bash
cd ~/R2
aws bedrock list-inference-profiles --region eu-north-1 --output json \
  --query "inferenceProfileSummaries[?contains(inferenceProfileId, 'anthropic')].{id: inferenceProfileId, arn: inferenceProfileArn, type: type, status: status, regions: models[].modelArn}" \
  > R2_03_profiles.json 2>&1
jq -r '.[] | "\(.id)\t\(.status)\t\([.regions[] | split(":")[3] | if . == "" then "(global)" else . end] | unique | join(","))"' \
  R2_03_profiles.json | sort
```

| Evidence file | PASS criterion |
|---|---|
| `R2_03_profiles.json` | A JSON array of Anthropic profiles (fact). Every `eu.` profile is `ACTIVE` and routes only to Regions whose name starts with `eu-`. The agent compares the set with `R1_28_claude-profiles-eu-north-1.json` (26 profiles) and notes any change. |

### Step 04 — The candidate list

What it does: fixes the models R2 tests, so steps 05–09 loop over one file.

**Confirm or change the list in session before running this step.** The agent's proposal, and why:

| Candidate `eu.` profile | Why it is on the list |
|---|---|
| `eu.anthropic.claude-opus-4-8` | Same model as today's pins (`SKILL_MODEL`, `AGENT_MODEL`, `_DRAFTER_MODEL` = `claude-opus-4-8`); orchestrator/drafter with no behaviour change |
| `eu.anthropic.claude-opus-5-5` | Newest Opus; orchestrator or AN12 A5 alternative |
| `eu.anthropic.claude-sonnet-5-5` | Assessor candidate (differs from the Opus 4.8 drafter in every id form, AN1c); A3 or A5 candidate |
| `eu.anthropic.claude-sonnet-4-6` | The model behind the old `BEDROCK_CONVERSE_US` default (`us.anthropic.claude-sonnet-4-6`); continuity with earlier AN12 tests |
| `eu.anthropic.claude-haiku-5-5` | Cheapest current model; A3 candidate |

Not proposed: Haiku 4.5 (already answered in R1, step 29; no workload needs it); Opus 5, Sonnet 5,
Opus 4.7, 4.6, 4.5 and Sonnet 4.5 (superseded); Fable 5 and Fable 5.1 (in eu-north-1 only as
`global.` profiles, so excluded under OD1-r1).

```bash
cd ~/R2
cat > R2_04_candidates.txt <<'EOF'
eu.anthropic.claude-opus-4-8
eu.anthropic.claude-opus-5-5
eu.anthropic.claude-sonnet-5-5
eu.anthropic.claude-sonnet-4-6
eu.anthropic.claude-haiku-5-5
EOF
for id in $(grep -v '^[[:space:]]*$' R2_04_candidates.txt); do
  if jq -e --arg id "$id" 'any(.[]; .id == $id and .status == "ACTIVE")' R2_03_profiles.json > /dev/null
  then echo "$id PRESENT"; else echo "$id ABSENT"; fi
done | tee R2_04_candidates-check.txt
```

If you changed the list, the changed list is what goes into the file; report the change.

| Evidence file | PASS criterion |
|---|---|
| `R2_04_candidates.txt` | Every line starts with `eu.anthropic.`; it matches the list confirmed in session |
| `R2_04_candidates-check.txt` | Every candidate is `PRESENT` |

### Step 05 — Model access status per candidate (read-only)

What it does: asks Bedrock, without invoking, whether the account is authorised for each model and
whether a Marketplace agreement is in place, so a refusal in step 07 can be read.

```bash
cd ~/R2
: > R2_05_availability-exit.txt
for id in $(grep -v '^[[:space:]]*$' R2_04_candidates.txt); do
  short=$(echo "${id#eu.anthropic.claude-}" | tr ':.' '--')
  aws bedrock get-foundation-model-availability --region eu-north-1 --model-id "${id#eu.}" \
    --output json > "R2_05_availability-$short.json" 2>&1
  echo "$id exit=$?" >> R2_05_availability-exit.txt
done
cat R2_05_availability-exit.txt
for f in R2_05_availability-*.json; do echo "== $f"; jq -c '{modelId, agreement: .agreementAvailability.status, auth: .authorizationStatus, entitlement: .entitlementAvailability, region: .regionAvailability}' "$f" 2>/dev/null || cat "$f"; done
```

| Evidence file | PASS criterion |
|---|---|
| `R2_05_availability-exit.txt` | One line per candidate (fact) |
| `R2_05_availability-<model>.json` | Fact per candidate: `agreementAvailability.status`, `authorizationStatus`, `entitlementAvailability`, `regionAvailability`. If the CLI does not know the command (`Invalid choice`), the step is N/A and step 07 alone decides access. |

### Step 06 — Where each candidate routes (read-only)

What it does: records each profile's ARN and the foundation-model ARNs it routes to. R5's invoke
policy needs exactly these ARNs (F2).

```bash
cd ~/R2
: > R2_06_profile-exit.txt
for id in $(grep -v '^[[:space:]]*$' R2_04_candidates.txt); do
  short=$(echo "${id#eu.anthropic.claude-}" | tr ':.' '--')
  aws bedrock get-inference-profile --region eu-north-1 --inference-profile-identifier "$id" \
    --output json > "R2_06_profile-$short.json" 2>&1
  echo "$id exit=$?" >> R2_06_profile-exit.txt
done
cat R2_06_profile-exit.txt
for f in R2_06_profile-*.json; do jq -r '"\(.inferenceProfileId)\t\(.status)\t\(.type)\t\([.models[].modelArn | split(":")[3]] | join(","))"' "$f" 2>/dev/null || cat "$f"; done
```

| Evidence file | PASS criterion |
|---|---|
| `R2_06_profile-exit.txt` | `exit=0` for every candidate |
| `R2_06_profile-<model>.json` | `status` = `ACTIVE`; `type` = `SYSTEM_DEFINED`; `inferenceProfileArn` = `arn:aws:bedrock:eu-north-1:797661577394:inference-profile/<id>`; every `models[].modelArn` is in a Region starting with `eu-`, and one of them is in `eu-north-1` |

### Step 07 — One Converse call per candidate (≤ 5 output tokens each)

What it does: proves each candidate answers from eu-north-1 through its `eu.` profile. This is the
only step that spends credits.

```bash
cd ~/R2
: > R2_07_converse-exit.txt
for id in $(grep -v '^[[:space:]]*$' R2_04_candidates.txt); do
  short=$(echo "${id#eu.anthropic.claude-}" | tr ':.' '--')
  aws bedrock-runtime converse --region eu-north-1 --model-id "$id" \
    --messages '[{"role":"user","content":[{"text":"Reply with exactly: OK"}]}]' \
    --inference-config maxTokens=5 --output json \
    --query '{text: output.message.content[0].text, stop: stopReason, usage: usage}' \
    > "R2_07_converse-$short.json" 2>&1
  echo "$id exit=$?" >> R2_07_converse-exit.txt
  sleep 2
done
cat R2_07_converse-exit.txt
for f in R2_07_converse-*.json; do echo "== $f"; cat "$f"; done
```

**The one pre-planned retry.** If a candidate's error says its Marketplace subscription or access is
still being set up and to try again later, wait two minutes and run that candidate once more, saving to
`R2_07_converse-<model>-attempt2.json` (same command, that file name). Any other error: stop for that
model, keep the error as it is, and report it (handoff R2 §3 point 5). Do not submit forms, accept
offers or change anything to make a model work; that is decided in session.

| Evidence file | PASS criterion |
|---|---|
| `R2_07_converse-exit.txt` | One line per candidate (fact; non-zero exits are read in the files below) |
| `R2_07_converse-<model>.json` (and `-attempt2.json` if run) | Usable: `text` = `OK` and `stop` is `end_turn` or `max_tokens`. Refused: the file holds the error verbatim; that model is recorded as not usable with that reason. Either outcome is acceptable evidence; at least one candidate must be usable for R2 to continue (otherwise the ticket stops and the block goes to the operator as OD10 input). |

### Step 08 — Applied quotas for Claude in eu-north-1 (read-only)

```bash
cd ~/R2
aws service-quotas list-service-quotas --service-code bedrock --region eu-north-1 --output json \
  --query "Quotas[?contains(QuotaName, 'Claude')].{code: QuotaCode, name: QuotaName, value: Value, unit: Unit, adjustable: Adjustable}" \
  > R2_08_quotas-applied.json 2>&1
jq -r '.[] | select(.name | test("(?i)cross-region")) | "\(.value)\t\(.name)"' R2_08_quotas-applied.json | sort -t$'\t' -k2
```

| Evidence file | PASS criterion |
|---|---|
| `R2_08_quotas-applied.json` | For every candidate usable in step 07: a cross-Region **tokens per minute** line and a cross-Region **requests per minute** line naming that model, each with a numeric `value`. The agent matches names to profile ids. A value of `0`, or a missing line, is reported as a limit on that model. |

### Step 09 — Default quotas for the same lines (read-only)

```bash
cd ~/R2
aws service-quotas list-aws-default-service-quotas --service-code bedrock --region eu-north-1 --output json \
  --query "Quotas[?contains(QuotaName, 'Claude')].{code: QuotaCode, name: QuotaName, value: Value, unit: Unit, adjustable: Adjustable}" \
  > R2_09_quotas-default.json 2>&1
jq length R2_08_quotas-applied.json R2_09_quotas-default.json
```

| Evidence file | PASS criterion |
|---|---|
| `R2_09_quotas-default.json` | Holds a default `value` for every quota code the agent uses from step 08 |

### Step 10 — Invocation logging is still off

What it does: confirms the Converse calls did not run with model invocation logging on (handoff §7).

```bash
cd ~/R2
aws bedrock get-model-invocation-logging-configuration --region eu-north-1 --output json \
  > R2_10_invocation-logging.json 2>&1
echo "bytes: $(wc -c < R2_10_invocation-logging.json)"; cat R2_10_invocation-logging.json
```

| Evidence file | PASS criterion |
|---|---|
| `R2_10_invocation-logging.json` | Empty, or `{}`: no `loggingConfig` key (as in R1, F-OD1r1-6) |

### Step 11 — Credits after the calls

```bash
cd ~/R2
aws freetier get-account-plan-state --output json > R2_11_plan-state-after.json 2>&1
jq -c '{accountPlanStatus, accountPlanRemainingCredits}' R2_11_plan-state-after.json
```

| Evidence file | PASS criterion |
|---|---|
| `R2_11_plan-state-after.json` | `accountPlanStatus` = `ACTIVE`; remaining credits ≥ the step 01 amount − 0.10 USD (the figure usually lags by hours, so an equal value is expected) |

### Step 12 — Bring the evidence home and scan it

CloudShell:

```bash
cd ~ && rm -f R2_evidence.zip && zip -r R2_evidence.zip R2 && unzip -l R2_evidence.zip
```

CloudShell **Actions → Download file** → `R2_evidence.zip`. Then in PowerShell, from the repository root:

```powershell
Expand-Archive -Path "$HOME\Downloads\R2_evidence.zip" -DestinationPath "$env:TEMP\R2_evidence" -Force
Copy-Item "$env:TEMP\R2_evidence\R2\R2_*" docs\infrastructure_security\evidence_v2\R2\
py -3.10 -m tools.evidence_secret_scan docs/infrastructure_security/evidence_v2/R2
```

No evidence file. Report the file count and the scan result. A refusal means the evidence is collected
again, never edited.

---

## After hand-back (agent)

1. Reads every file against the criteria above and writes `VERIFICATION.md`.
2. Builds the R2 table: per usable candidate, the `eu.` profile id and ARN, the routed EU Regions and
   foundation-model ARNs, applied and default cross-Region TPM and RPM, and the step 07 result.
3. Drafts the OD7 successor record
   (`docs/tier4_orchestration_state/decision_log/aws-redeployment-od7-model-set_2026-10-21.json`) from
   the points settled in session, then updates register v2 DC-36 and the worklog.

## To settle in session (not steps)

- **`global.` profiles.** Proposal: excluded from OD7 and denied in R5's explicit deny. Consequence:
  Fable 5 / 5.1 are unavailable to the host.
- **Orchestrator model** (`ORCHESTRATOR_TRANSPORT_MODEL` on the host; R2 changes no code pin).
- **AN12 A3 and A5:** two distinct models.
- **Assessor:** must differ from the drafter in every id form (AN1c). With the drafter on Opus 4.8,
  every `claude-opus-4-8` form is ruled out for the assessor.
- The AN12 runbook's `us.` / us-east-1 lines are R9e's to rewrite; R2 supplies only the ids.

## Order

01 (STOP rule) → 02 → 03 → 04 (list confirmed in session first) → 05 → 06 → 07 → 08 → 09 → 10 → 11 →
12 → hand back.

## Before you hand back

- [ ] Every evidence file listed above exists in this folder, under exactly its name.
- [ ] You opened the step 07 files and saw nothing but `OK` or an error message.
- [ ] The secret scan in step 12 reported clean.
