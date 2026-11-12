# R12b — verification report

| Field | Value |
|---|---|
| Verified by / on | agent (Claude) / 2026-11-12 |
| Step sheets | `STEPS.md` (steps 01–12, points 1–9) as amended by `STEPS_fix1.md` (F01–F11, the rewritten F05 and the combined blocks), run as in `RUNLOG.md` |
| Decisions | `aws-redeployment-r12b-reevidence_2026-11-12` (R12b-D1–D12, F-R12b-1–6); R12a-D3–D26 (`aws-redeployment-r12a-collector_2026-10-28`) |
| Collector run | `R12b_09_collector/`: started 00:37:25Z, finished 00:42:16Z; `exit=0`; 93 collected, 1 expected error (DC-40 SCP list), 1 not collected (the launcher check, point 1); 102 files with `MANIFEST.sha256` re-hashed by the agent; the collector's own secret scan and old-ID guard CLEAN |
| Stacks | `proposal-orchestrator-host`, twice. Round 2 (`r12b-create-01`): 2026-11-11 23:36:41 – ~23:45, collector refused before any AWS call (F7 URL file missing). Fix 1 (`r12b-create-02`): 2026-11-12 00:34:46 – ~00:45, the run this report rests on. Both deleted in the session |
| Cost | Hourly: two creations of six interface endpoints and one `c7i-flex.large` host, about 9 and 10 minutes. Credits 199.25 USD at F01 (billing delayed). R14 prices it |
| Secret scan | Agent over `evidence_v2/R12b` after each edit: CLEAN. Operator step 12 (2026-11-12): CLEAN, `exit=0` |

Every check below was re-run by the agent on the saved files (`utf-8-sig`), by script. Host ids come
from `R12b_outputs.json` (the fix-1 creation); base ids from `R4_outputs.json`–`R8_outputs.json`.

## Criteria

| Step | Criterion | Evidence | Status | Reason |
|---|---|---|---|---|
| 01 | Plan, budget, notifications, caller | `R12b_01_*` | PASS | FREE / ACTIVE, 199.25 USD; 0.492 of 10.0; three `OK`; account 797661577394 |
| 02 | Nothing left by R11; base stacks and exports as R11 step 03 | `R12b_02_*` | PASS | Host stack absent; only the S3 gateway endpoint; no ENI, no instance; base stacks and 25 exports equal `R11_03_*` |
| 03 | Lint, guards, 324 tests, collector plan | `R12b_03_*` | PASS | cfn-lint exit 0; both guards CLEAN; `324 passed, 1 skipped` (symlink case); plan `exit=0`, 82 commands, every id from the outputs files |
| 04 | Change set `r12b-create-01` | `R12b_04_*` | PASS | Seven `Add`; parameter values equal `R11_fix1_05`; same image |
| 05–11 (round 2) | First creation and collection | `R12b_06_*`, `R12b_08_*`, `R12b_09_collector-console.txt`, `R12b_10_*`, `R12b_11_*` | FAIL, superseded | Creation and delete PASS; the collector refused (`the F7 URL file cannot be read`, `exit=2`); step 11 ran without a collector folder. Superseded by fix 1 (R12b-D6) |
| F01 | Session check | `R12b_fix1_01_*` | PASS | As step 01; `F01_ok=True` |
| F04 | Change set `r12b-create-02` | `R12b_fix1_04_*` | PASS | Equal to `R12b_04_change-set.json` in status, tag, the seven `Add` and every parameter value |
| F05 | URL signed and read by the collector before the stack exists | `R12b_fix1_05b_collector-plan.txt` | PASS | Plan `exit=0`, `PO_F7_URL='<f7-url>'` masked, no URL in the file. First attempts: `R12b_fix1_05_collector-plan.txt` (refused, file missing), RUNLOG rows |
| F06 | Execute `r12b-create-02` | `R12b_fix1_06_*` | PASS | `execute exit=0`, `CREATE_COMPLETE`, 24 events, none failed |
| F07 | New outputs | `R12b_outputs.json` | PASS | Seven keys, no export, seven new ids (none equal to R11's or round 2's) |
| F08 | Host `Online` | `R12b_fix1_08_instance-information.json` | PASS | Try 0 |
| F09 | Collector run, exit 0, no error | `R12b_fix1_09_collector-console.txt`, `R12b_09_collector/` | PASS, with three defects | `exit=0`, `error 0`. Defects: DC-15's last test misreads the CLI (F-R12b-2); three DC-11 files were written to NTFS alternate data streams (F-R12b-3, recovered in `R12b_fix1_09_ads-recovered/` with `RECOVERY.sha256`); seven simulations ran without Region context (F-R12b-4) |
| F09 | Host checks `Success` and `RESULT=expected` | `R12b_09_collector/*_host-*.json` | PASS except DC-15 and F7 | DC-02, DC-14, DC-17, DC-31, DC-32, DC-37 expected. DC-15 `unexpected` from F-R12b-2 only. F7 below |
| F09 | F7: `403`, `AccessDenied`, names the VPC endpoint policy | `R12b_09_collector/DC-05_host-f7-presigned-put.json` | **FAIL (inconclusive)** | `http_status=404`, `NoSuchBucket`, `message_names_vpc_endpoint_policy=no`: S3 answered for a bucket that does not exist before the endpoint policy refused. F7 stays open; retest in the next host session (operator, 2026-11-12; R12b-D9) |
| F10 | Delete; nothing left; base stacks unchanged | `R12b_fix1_10_*` | PASS | `delete exit=0`; stack absent; no ENI, instance or project volume; base stacks equal step 02; URL file removed |
| F11 | CloudTrail `Converse` event, metadata only (DC-26) | `R12b_fix1_11_*` | PASS | One event at 00:42:02Z, `eu-north-1`, `AssumedRole`, caller the runtime role with the host's session, issuer `RuntimeRoleArn`, `vpcEndpointId` = `BedrockRuntimeEndpointId` of `R12b_outputs.json`, model `eu.anthropic.claude-opus-4-6-v1`, no error; only the listed fields |
| 12 | Tests, guards, scan last | `R12b_12_*` | Pending | After this report. Expected: `346 passed, 1 skipped` (agent run 2026-11-12; the skip is the symlink case) |

## DC-39 document review (point 8)

AWS Service Terms, https://aws.amazon.com/service-terms/, "Last Updated: November 5, 2026", read
2026-11-12:

- §1.14.1: "These Service Terms incorporate the AWS Data Processing Addendum ("DPA"), when you use AWS
  Services to process Customer Data (as defined in the DPA)."
- §1.14.3 incorporates the Standard Contractual Clauses approved by Commission Implementing Decision (EU)
  2021/914. They apply when the GDPR applies to the processing and Customer Data is transferred outside
  the EEA to a country without an adequacy decision.

The DPA applies through the Service Terms, without a separate signature, whenever the account processes
Customer Data. Not read: the DPA PDF's own text (not text-extractable in the agent's fetch). Status
proposed: VERIFIED_PASS, Inferred.

## Ticket checklist

| Ticket criterion (`plans/aws_redeployment_tickets.md`, R12b) | Status | Evidence |
|---|---|---|
| Register v2 shows every control as VERIFIED_PASS, NOT_APPLICABLE with a reason, or DEFERRED with a reason, and gives a v2 evidence path for each | PASS | Register v2 of 2026-11-12: 35 VERIFIED_PASS, 4 DEFERRED (DC-33–35 to R15, DC-38 per OD12), 2 NOT_APPLICABLE (DC-22, DC-40); every row names a v2 path; Summary table refreshed (F-R12a-1) |
| The presigned PUT to an outside bucket fails from the host (closes F7) | PASS (addendum below) | 2026-11-12 run: `DC-05_host-f7-presigned-put.json`, `404 NoSuchBucket`, inconclusive. Retest in R14 step 08: `R12b_fix2_08_*`, `403 AccessDenied` naming the endpoint policy. Closed by the operator |
| The DC-15 in-host tests are collected | PASS | `DC-15_host-no-long-term-keys.json` collected; content clean, script defect in its last test (F-R12b-2) |
| DC-40 is re-assessed. It stays N/A unless the account joined an Organization | PASS | `DC-40_organization.json`, `DC-40_scp-list.txt`: the account is in an organization with a management account outside the project; NOT_APPLICABLE with that reason (point 7, operator-confirmed) |

## Done conditions

- [x] Every criterion above is PASS, except round 2 (superseded) and F7 (open, carried forward).
- [x] Register v2 updated (2026-11-12), Summary table included.
- [x] Decision record `aws-redeployment-r12b-reevidence_2026-11-12` drafted.
- [x] Step 12 after this report (run 2026-11-12, after the confirmation): Python 3.10.6, `346 passed, 1 skipped` (the symlink case), as stated; old-ID guard CLEAN (20 ids), `exit=0`; secret scan CLEAN over `evidence_v2/R12b`, `exit=0`, run last.
- [x] Operator confirmed R12b (2026-11-12 01:14 UTC), taken as the review of R12b-D8, D10–D12; criteria 1, 3 and 4 ticked, criterion 2 (F7) left open.

## Addendum, 2026-11-12: F7 retest (R14 step 08)

Run in the R14 creation B session (`evidence_v2/R14/RUNLOG.md`, row 08; R14-D3), by the operator, from
the workstation. The bucket was created in this account in `eu-north-1` with a random name, so it
existed when the host sent the PUT (R12b-D9).

| Evidence | Criterion | Status | Reason |
|---|---|---|---|
| `R12b_fix2_08_bucket.txt` | The bucket exists | PASS | `create_bucket_exit=0`, `head_bucket_exit=0` |
| `R12b_fix2_08_f7-presigned-put.json` | `403`, `AccessDenied`, names the VPC endpoint policy; no URL in the file | PASS | Run Command `Success`; `http_status=403`, `error_code=AccessDenied`, `message_names_vpc_endpoint_policy=yes`, `RESULT=expected`; no `https://` (checked by script) |
| `R12b_fix2_08_bucket-removed.txt` | First line `0`; `rb_exit=0` | Deviation, operator-accepted | First line `None`; `rb_exit=0`. Inferred: no object arrived, because S3 answered the only PUT with `403`. The empty bucket's listing returned no `KeyCount` (F-R14-3) |

The operator accepted F7 as closed on 2026-11-12 ("accept F7 as closed"). Criterion 2 is ticked.

## Notes for later tickets

- **Next host session (R14 scripts or R15):** the F7 retest (R12b-D9). The test must use a bucket that
  exists, so that S3 reaches the endpoint policy.
- **Collector fixes before its next run (F-R12b-2, -3, -4):** the DC-15 credential-type parse; file names
  without `:`; `aws:RequestedRegion` context on the seven non-Bedrock simulations (R5 VERIFICATION
  lesson), with `AllowedByOrganizations` checked.
- **R15:** DC-33–35 through the launcher on the O5 bundle.
- **R14:** price both R12b creations (about 9 and 10 minutes) with R11's.
