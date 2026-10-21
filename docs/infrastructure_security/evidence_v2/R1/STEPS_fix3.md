# R1 — Account baseline: step sheet, fix 3

| Field | Value |
|---|---|
| Replaces | `STEPS_fix2.md` step 24's reading (see RUNLOG "24 (agent correction)"). Adds steps 26–29. |
| Why | Step 25 decoded the create-vpc refusal: SCP statement `UsEast1Partitional` denies every regional action in us-east-1 except a list of global ones. Step 26 found that of 17 Regions only **eu-north-1** allows regional calls: it is the project's Region. The step 24 probe ran in us-east-1 with placeholder ids and over-reported `allowed`; `r1_scp_probe.sh` is fixed and now takes the Region as an argument. |
| Written by / on | agent (Claude) / 2026-10-21 |
| Account / region | `797661577394` / `eu-north-1` (project Region) |

Nothing in this sheet creates a resource. Step 29 makes one Bedrock call of at most 5 output tokens,
which the credits cover (a fraction of a cent).

### Step 26 — Region access (already run)

| Evidence file | PASS criterion |
|---|---|
| `R1_26_region-access.txt` | Exactly one Region is `ALLOWED` (records which) |

### Step 27 — SCP probe in the project Region

Re-upload the fixed script (**Actions → Upload file** → `docs/infrastructure_security/evidence_v2/R1/r1_scp_probe.sh`; it replaces the old copy in `~`), then:

```bash
mv -f ~/r1_scp_probe.sh ~/R1/ && cd ~/R1 && sed -i 's/\r$//' r1_scp_probe.sh
bash r1_scp_probe.sh R1_27_scp-probe-eu-north-1.json eu-north-1
jq '{real_ids_used, default_vpc}' R1_27_scp-probe-eu-north-1.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_27_scp-probe-eu-north-1.json` | `real_ids_used` = `true`; no probe is `UNEXPECTED_SUCCESS`. Outcomes are analysed by the agent. |

### Step 28 — Claude inference profiles visible in eu-north-1 (read-only)

```bash
aws bedrock list-inference-profiles --region eu-north-1 --output json \
  --query "inferenceProfileSummaries[?contains(inferenceProfileId, 'anthropic')].{id: inferenceProfileId, status: status, regions: models[].modelArn}" \
  > R1_28_claude-profiles-eu-north-1.json 2>&1
jq -r '.[].id' R1_28_claude-profiles-eu-north-1.json 2>/dev/null || cat R1_28_claude-profiles-eu-north-1.json
aws bedrock list-foundation-models --region eu-north-1 --by-provider anthropic --output json \
  --query 'modelSummaries[].{id: modelId, inference: inferenceTypesSupported}' \
  > R1_28_claude-models-eu-north-1.json 2>&1
cat R1_28_claude-models-eu-north-1.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_28_claude-profiles-eu-north-1.json` | Lists the Anthropic inference profiles and the Regions each routes to (fact) |
| `R1_28_claude-models-eu-north-1.json` | Lists the Anthropic models and whether any supports `ON_DEMAND` in eu-north-1 itself (fact) |

### Step 29 — One Converse call through an `eu.` profile (5 output tokens)

Takes the first Haiku profile from step 28 (the cheapest):

```bash
PROFILE=$(jq -r '[.[].id | select(test("haiku"))][0] // .[0].id' R1_28_claude-profiles-eu-north-1.json); echo "$PROFILE"
aws bedrock-runtime converse --region eu-north-1 --model-id "$PROFILE" \
  --messages '[{"role":"user","content":[{"text":"Reply with exactly: OK"}]}]' \
  --inference-config maxTokens=5 --output json \
  --query '{text: output.message.content[0].text, stop: stopReason, usage: usage}' \
  > R1_29_converse-eu-profile.json 2>&1
echo "$PROFILE" > R1_29_converse-eu-profile-model.txt
cat R1_29_converse-eu-profile.json
```

| Evidence file | PASS criterion |
|---|---|
| `R1_29_converse-eu-profile.json` | Either `text` = `OK` (cross-Region inference works from the project), or the error text, which tells whether an SCP, a missing model-access form or something else blocks it (fact; R2 builds on it) |
