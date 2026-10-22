# R2 — Bedrock access check: step sheet, fix 1 (newest usable Opus and Sonnet)

| Field | Value |
|---|---|
| Extends | `STEPS.md`. Adds steps 13–15 and runs them before steps 08–12, which then stand as written. |
| Why | Step 07: `eu.` Opus 4.8, Opus 5.5, Sonnet 5.5 and Haiku 5.5 were refused with AccessDeniedException "… is not available for this account … contact AWS Sales"; only Sonnet 4.6 answered (`R2_07_converse-*.json`, `R2_07_availability-after-*.json`). The operator decided in session (2026-10-21, "Bővítés. Opus és Sonnetből a legújabb kell."): find the newest usable Opus and the newest usable Sonnet. |
| Written by / on | agent (Claude) / 2026-10-21 |
| Account / region | `797661577394` / `eu-north-1`; CloudShell home eu-north-1, folder `~/R2` (as for steps 01–07) |
| Hourly cost created | none. At most five Converse calls of ≤ 5 output tokens; a refused call costs nothing. |

## How the order is chosen

Newest first, and stop at the first model that answers, so no older model gets a Marketplace agreement
it does not need (a successful first call creates one, `R2_07_availability-after-sonnet-4-6.json`).

- **Sonnet:** only `eu.anthropic.claude-sonnet-5` is newer than Sonnet 4.6. If it is refused, Sonnet 4.6
  (step 07) is the newest usable Sonnet; Sonnet 4.5 is older and is not tried.
- **Opus**, below the refused 5.5 and 4.8: `eu.anthropic.claude-opus-5` → `-opus-4-7` → `-opus-4-6-v1` →
  `-opus-4-5-20251101-v1:0`, stopping at the first that answers.
- Haiku is not tried: not asked for, and Haiku 4.5 already answered in R1 (step 29).

The rules of `STEPS.md` "Before you start" apply. The step 07 retry rule applies to steps 14 too: only an
error that says access is still being set up and to try again gets one retry after two minutes, saved as
`R2_14_converse-<model>-attempt2.json`. Any other error is kept as it is.

### Step 13 — The extension list

```bash
cd ~/R2
printf '%s\n' eu.anthropic.claude-sonnet-5 eu.anthropic.claude-opus-5 eu.anthropic.claude-opus-4-7 \
  eu.anthropic.claude-opus-4-6-v1 'eu.anthropic.claude-opus-4-5-20251101-v1:0' > R2_13_candidates-ext.txt
for id in $(cat R2_13_candidates-ext.txt); do
  if jq -e --arg id "$id" 'any(.[]; .id == $id and .status == "ACTIVE")' R2_03_profiles.json > /dev/null
  then echo "$id PRESENT"; else echo "$id ABSENT"; fi
done | tee R2_13_candidates-ext-check.txt
```

| Evidence file | PASS criterion |
|---|---|
| `R2_13_candidates-ext.txt` | The five ids above, in that order |
| `R2_13_candidates-ext-check.txt` | All five `PRESENT` |

### Step 14 — Converse: Sonnet 5, then the Opus cascade

```bash
cd ~/R2
: > R2_14_converse-exit.txt
try_model() {
  local id="$1" short rc
  short=$(echo "${id#eu.anthropic.claude-}" | tr ':.' '--')
  aws bedrock-runtime converse --region eu-north-1 --model-id "$id" \
    --messages '[{"role":"user","content":[{"text":"Reply with exactly: OK"}]}]' \
    --inference-config maxTokens=5 --output json \
    --query '{text: output.message.content[0].text, stop: stopReason, usage: usage}' \
    > "R2_14_converse-$short.json" 2>&1
  rc=$?
  echo "$id exit=$rc" >> R2_14_converse-exit.txt
  sleep 2
  return $rc
}
try_model eu.anthropic.claude-sonnet-5
for id in eu.anthropic.claude-opus-5 eu.anthropic.claude-opus-4-7 eu.anthropic.claude-opus-4-6-v1 'eu.anthropic.claude-opus-4-5-20251101-v1:0'; do
  try_model "$id" && break
done
cat R2_14_converse-exit.txt
for f in R2_14_converse-*.json; do echo "== $f"; cat "$f"; done
```

| Evidence file | PASS criterion |
|---|---|
| `R2_14_converse-exit.txt` | One line for Sonnet 5; Opus lines stop at the first `exit=0` (or run through all four) |
| `R2_14_converse-<model>.json` | Usable: `text` = `OK` and `stop` is `end_turn` or `max_tokens`. Refused: the error verbatim. Either is acceptable evidence. If no Opus answers, that is the finding and goes to the operator as OD10 input. |

### Step 15 — Routing and agreement state of the models that answered (read-only)

```bash
cd ~/R2
for id in $(awk '$2 == "exit=0" {print $1}' R2_14_converse-exit.txt); do
  short=$(echo "${id#eu.anthropic.claude-}" | tr ':.' '--')
  aws bedrock get-inference-profile --region eu-north-1 --inference-profile-identifier "$id" \
    --output json > "R2_15_profile-$short.json" 2>&1
  jq -r '"\(.inferenceProfileId)\t\(.status)\t\(.type)\t\(.inferenceProfileArn)\t\([.models[].modelArn | split(":")[3]] | join(","))"' "R2_15_profile-$short.json" 2>/dev/null || cat "R2_15_profile-$short.json"
  aws bedrock get-foundation-model-availability --region eu-north-1 --model-id "${id#eu.}" \
    --output json > "R2_15_availability-$short.json" 2>&1
  jq -c '{modelId, agreement: .agreementAvailability.status, auth: .authorizationStatus}' "R2_15_availability-$short.json" 2>/dev/null || cat "R2_15_availability-$short.json"
done
```

| Evidence file | PASS criterion |
|---|---|
| `R2_15_profile-<model>.json` | As step 06: `ACTIVE`; `SYSTEM_DEFINED`; ARN `arn:aws:bedrock:eu-north-1:797661577394:inference-profile/<id>`; every routed Region starts with `eu-`, one is eu-north-1 |
| `R2_15_availability-<model>.json` | Fact: agreement state after the successful call |

## Order from here

13 → 14 → 15 → `STEPS.md` 08 → 09 → 10 → 11 → 12 → hand back.
