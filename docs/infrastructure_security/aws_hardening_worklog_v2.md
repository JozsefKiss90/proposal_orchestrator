# AWS Hardening Worklog — v2

## Proposal Orchestrator — redeployment in account `797661577394`

**Created:** 2026-10-21 (ticket E0)
**Plan:** `plans/aws_redeployment_handoff_2026-10-21.md`
**Tickets:** `plans/aws_redeployment_tickets.md`
**History:** worklog v1, [`aws_hardening_worklog.md`](aws_hardening_worklog.md), records the first hardening and is not continued.

---

## Log Format

Each entry records the same fields as v1:
- **Timestamp** — date and time of action (UTC)
- **Control ID** — DC-xx / PL-8 reference from register v2, or the ticket id for scaffolding work
- **Action Taken** — what was done
- **Evidence Requested** — what evidence was asked from the operator
- **Evidence Received** — what evidence was provided (path under `evidence_v2/`, or "pending")
- **Verification Result** — PASS / FAIL / PENDING / N/A
- **Next Action** — what happens next

---

## Entries

### 2026-10-21 — E0: Evidence protocol scaffold

| Field | Value |
|---|---|
| Timestamp | 2026-10-21T08:29:00Z |
| Control ID | E0 (no control; all 41 set up as NOT_STARTED) |
| Action Taken | Created `evidence_v2/` (README, `_templates/STEPS.md`, `RUNLOG.md`, `VERIFICATION.md`), the secret scan `tools/evidence_secret_scan.py` with tests `tests/test_evidence_protocol_scaffold.py`, register v2 and this worklog. v1 register, worklog and evidence untouched. |
| Evidence Requested | — (no AWS step) |
| Evidence Received | `evidence_v2/E0/VERIFICATION.md` |
| Verification Result | PASS on all four E0 criteria. Operator confirmed 2026-10-21 after a Windows re-run (`py -3.10`: 20 passed; probe refused, exit 1; `evidence_v2` CLEAN). E0 DONE. |
| Next Action | Operator confirms E0. Then R0 (OD1–OD13 decision record); R10 can run in parallel. |

---

### 2026-10-21 — R0: Operator decisions OD1–OD13

| Field | Value |
|---|---|
| Timestamp | 2026-10-21T08:44:00Z |
| Control ID | R0 (no control) |
| Action Taken | Recorded the operator's decisions in `docs/tier4_orchestration_state/decision_log/aws-redeployment-operator-decisions_2026-10-21.json`. OD1 = us-east-1 with `us.` profiles (operator reason: the region used before, more reliable for the models used). OD2–OD6, OD8–OD13 = suggested defaults. OD7 deferred to R2. |
| Evidence Requested | — (no AWS step) |
| Evidence Received | `evidence_v2/R0/VERIFICATION.md` |
| Verification Result | All 4 criteria PASS. Committed as `806660d`; operator confirmed 2026-10-21. R0 DONE. |
| Next Action | Operator commits E0 + R0 and confirms R0. Then R9e closes N/A; R1 (account baseline step sheet) is next on the frontier, with R3, R9 and R10 also open. |

---

### 2026-10-21 — R9e: EU region support — closed N/A

| Field | Value |
|---|---|
| Timestamp | 2026-10-21T08:52:00Z |
| Control ID | R9e (no control) |
| Action Taken | Closed N/A: OD1 keeps us-east-1 (decision record `aws-redeployment-operator-decisions_2026-10-21`). |
| Evidence Requested | — |
| Evidence Received | `evidence_v2/R9e/VERIFICATION.md` |
| Verification Result | N/A with OD1 cited. R9e DONE. |
| Next Action | R1 account baseline: step sheet `evidence_v2/R1/STEPS.md`. |

---

### 2026-10-21 — E0 follow-up: secret scan reads UTF-16

| Field | Value |
|---|---|
| Timestamp | 2026-10-21T09:08:00Z |
| Control ID | E0 (no control) |
| Action Taken | `tools/evidence_secret_scan.py` decodes files that start with a UTF-16 byte-order mark before matching, because Windows PowerShell 5.1 writes UTF-16 on `>` redirection and a byte match would miss the patterns. Two tests added (22 in total, all pass). |
| Evidence Requested | — |
| Evidence Received | — |
| Verification Result | PASS (tests) |
| Next Action | Done: operator re-ran `py -3.10 -m pytest tests/test_evidence_protocol_scaffold.py` on Windows on 2026-10-21, 22 passed; committed as `777c686`. `.gitattributes` now keeps `*.sh` at LF so CloudShell scripts survive a Windows checkout. |

---

### 2026-10-21 — R1: Account baseline — step sheet delivered

| Field | Value |
|---|---|
| Timestamp | 2026-10-21T09:08:00Z |
| Control ID | R1 (account baseline; no control directly) |
| Action Taken | OD11 revised in `decision_log/aws-redeployment-od11-admin-identity_2026-10-21.json` (IAM user `po-admin` with MFA, no access keys, CLI via CloudShell and `aws login`; Identity Center would join an organization and upgrade the Free plan). Wrote `evidence_v2/R1/STEPS.md` (Parts A and B, steps 01–23) and the read-only inventory script `evidence_v2/R1/r1_inventory.sh`. |
| Evidence Requested | R1_02, R1_07–R1_22 as listed in `STEPS.md` |
| Evidence Received | Pending |
| Verification Result | PENDING |
| Next Action | Operator runs Parts A and B and hands back after step 23; agent writes `STEPS_cleanup.md` from the inventory. |

---

### 2026-10-21 — R1: account model measured; OD11 and OD1 revised; R9e reopened

| Field | Value |
|---|---|
| Timestamp | 2026-10-21T10:56:00Z |
| Control ID | R1 (baseline); DC-16, DC-28, DC-40 noted |
| Action Taken | Measured that account 797661577394 is a "Sign up for AWS (new)" project account (Builder ID owner, AccountFullAccessRole, AWS-managed organization and SCPs, Free plan). OD11 revised (r2: Builder ID through AccountFullAccessRole; STEPS_fix1). us-east-1 SCP refusals (STEPS_fix2, step 25 decode) and Region access (step 26) led to OD1 revised to eu-north-1 with eu. profiles (`aws-redeployment-od1-region-r1_2026-10-21`), operator decision. SCP probe re-run in eu-north-1 (step 27, real ids): networking, endpoints, flow logs and t3.medium allowed; Bedrock eu. profile Converse returned OK (step 29). R9e reopened. Probe script corrected (false positives in step 24 recorded in RUNLOG). STEPS_fix3 and STEPS_fix4 written. |
| Evidence Requested | Remaining R1 steps per STEPS_fix4 |
| Evidence Received | In CloudShell `~/R1` (R1_00_*, R1_13, R1_24–R1_29); R1_01, R1_10 in the repository |
| Verification Result | PENDING |
| Next Action | Operator continues R1 per STEPS_fix4; confirms OD11-r2. |

---

### 2026-10-21 — R1: Account baseline — evidence verified

| Field | Value |
|---|---|
| Timestamp | 2026-10-21T12:07:00Z |
| Control ID | R1 (baseline); DC-28 observed (invocation logging empty in eu-north-1) |
| Action Taken | Verified 42 evidence files against STEPS.md and fixes 1–4 and STEPS_cleanup.md. Recorded the operator-approved deviations in `aws-redeployment-r1-baseline-deviations_2026-10-21`. Explore AWS leftovers removed (Lambda with public URL, its log group, SG, key pair, three roles). |
| Evidence Requested | — |
| Evidence Received | `evidence_v2/R1/` (42 files), `evidence_v2/R1/VERIFICATION.md` |
| Verification Result | All criteria PASS or N/A with reason. Operator confirmed 2026-10-21 (commit `399ee02`). R1 DONE. |
| Next Action | Operator confirms R1. Then R2 (Bedrock access and quotas, settles OD7) and R3 (IaC skeleton for eu-north-1); R9e (EU preset) and R10 can run in parallel. |

---

### 2026-10-21 — R2: Bedrock access check — evidence verified, OD7 settled

| Field | Value |
|---|---|
| Timestamp | 2026-10-21T21:05:00Z |
| Control ID | DC-36 (R2 part); feeds DC-04, DC-10, DC-16; DC-28 observed (invocation logging empty after the calls) |
| Action Taken | Step sheet `STEPS.md` and operator-decided extension `STEPS_fix1.md` run from CloudShell (eu-north-1 home). Session-start check (R1-D2) clean: FREE / ACTIVE, 199.99 USD, all budget alerts OK. Converse through `eu.` profiles: Opus 4.6 and Sonnet 4.6 answer `OK`; Opus 5.5, 5, 4.8, 4.7, Sonnet 5.5, 5 and Haiku 5.5 refused ("not available for this account"). Applied cross-Region RPM 5 (Opus 4.6) and 10 (Sonnet 4.6, Haiku 4.5) against 10,000 default; TPM at default. OD7 settled with the operator: `aws-redeployment-od7-model-set_2026-10-21` (orchestrator Opus 4.6 interim, Opus 5 target; A3 Sonnet 4.6, A5 Opus 4.6; assessor Sonnet 4.6; `global.` excluded and denied). |
| Evidence Requested | — |
| Evidence Received | `evidence_v2/R2/` (45 `R2_*` files), `evidence_v2/R2/VERIFICATION.md` |
| Verification Result | All step criteria PASS (agent secret scan CLEAN). Ticket open until the operator's scan line, the commit of the OD7 record and the operator's confirmation. |
| Next Action | Operator re-runs the secret scan, commits R2 and the OD7 record, confirms R2. Operator's option (OD10 input): an Account and billing support case asking for newer Claude models and higher RPM. Then R3; R9e (eu-north-1 preset, AN12 runbook ids, AN1c drafter on the host) and R10 in parallel; R5 uses the OD7 resource list. |

---

### 2026-10-22 — R2: Bedrock access check — closed

| Field | Value |
|---|---|
| Timestamp | 2026-10-22T13:40:00Z |
| Control ID | DC-36 (R2 part verified; stays IN_PROGRESS until R11) |
| Action Taken | Operator re-ran the secret scan (`CLEAN`), committed the R2 evidence, the OD7 record `aws-redeployment-od7-model-set_2026-10-21`, register v2 and worklog as `690f90c`, and confirmed R2 in session. R2 ticked in `plans/aws_redeployment_tickets.md`. |
| Evidence Requested | — |
| Evidence Received | `evidence_v2/R2/VERIFICATION.md` (all criteria PASS or N/A with reason) |
| Verification Result | R2 DONE. |
| Next Action | Frontier: R3 (IaC skeleton, model list as a parameter), R9 / R9e (eu-north-1 Converse preset, AN12 runbook ids, AN1c drafter on the host), R10. R5 uses the OD7 resource list once R3 is done. Operator's option for OD10: an Account and billing support case for newer Claude models and higher RPM. |

---

### 2026-10-22 — R3: IaC skeleton and guards — written, step sheet ready

| Field | Value |
|---|---|
| Timestamp | 2026-10-22T14:40:00Z |
| Control ID | R3 (scaffolding); prepares DC-06 and PL-8 (R4) and the handoff §7 old-ID constraint |
| Action Taken | Settled the four R3 handoff §3 points and three smaller ones with the operator in session; recorded as `aws-redeployment-od6-stack-layout-r3_2026-10-22` (successor to OD6): six stacks (network, iam, kms, audit, secret as the exporting base; host per session, no exports), skeleton templates with a no-cost placeholder, change-set deploys. Wrote `deploy/aws/` (six templates, parameter files, `outputs_contract.json`, `requirements-lint.txt` pinning cfn-lint 1.57.2, README), `tools/old_id_guard.py`, `tools/aws_template_guard.py`, three test files, `.venv-lint/` in `.gitignore`. Found that the admin role ARN carries the `/managed/` path (F-OD6r3-1); `AdminRoleArn` is taken from R1 evidence. Agent pre-run in the device shell (not evidence): cfn-lint exit 0, both guards CLEAN, 105 tests passed. |
| Evidence Requested | `evidence_v2/R3/STEPS.md` steps 01–10 (session check, caller identity, lint, read-only lookups, validate-template, no stacks), then 11–12 (tests, guards, secret scan) after the agent fills `network.json` |
| Evidence Received | pending |
| Verification Result | PENDING |
| Next Action | Operator runs R3 steps 01–10 from PowerShell and reports. Agent fills `AvailabilityZone` and `S3PrefixListId` from steps 05–06, operator runs steps 11–12, agent writes `VERIFICATION.md`. |

---

### 2026-10-23 — R3: IaC skeleton and guards — evidence verified

| Field | Value |
|---|---|
| Timestamp | 2026-10-23T14:45:00Z |
| Control ID | R3 (scaffolding); prepares DC-06 and PL-8 (R4) and the handoff §7 old-ID constraint |
| Action Taken | Operator ran `evidence_v2/R3/STEPS.md` from PowerShell on the workstation: steps 01–10 on 2026-10-22, 11–12 on 2026-10-23. Session check clean (FREE / ACTIVE, 199.99 USD before and after, all alerts OK). cfn-lint 1.57.2 exit 0 on all six templates; validate-template exit 0 for all six in eu-north-1. Read-only lookups: zones eu-north-1a/b/c all offer the six interface services, chosen eu-north-1a; S3 prefix list `pl-c3aa4faa`; AL2023 AMI parameter readable. No stack and no export exist. Agent wrote `AvailabilityZone` and `S3PrefixListId` into `deploy/aws/parameters/network.json` from that evidence; then 105 tests passed under `py -3.10` (3.10.6), both guards CLEAN, secret scan CLEAN. |
| Evidence Requested | — |
| Evidence Received | `evidence_v2/R3/` (23 `R3_*` files), `evidence_v2/R3/VERIFICATION.md` |
| Verification Result | All criteria PASS. Ticket open until the operator's commit and confirmation. |
| Next Action | Operator commits R3 (`deploy/aws/`, the two tools, three tests, the OD6-r3 record, `.gitignore`, evidence, worklog) and confirms R3; agent ticks R3. Then R4, R5 and R12a join the frontier (with R9, R9e, R10). Separate small fix to decide: the stale E0 test case on register v2 status. |

---

### 2026-10-23 — E0: stale register v2 test case replaced

| Field | Value |
|---|---|
| Timestamp | 2026-10-23T14:50:00Z |
| Control ID | E0 (scaffolding); register v2 |
| Action Taken | `tests/test_evidence_protocol_scaffold.py::test_register_v2_lists_all_41_controls_as_not_started` had failed since R2 legitimately set DC-36 to `IN_PROGRESS` (commit `690f90c`); it froze the scaffold-time state. Replaced, at the operator's request, by `test_register_v2_lists_all_41_controls_with_a_defined_status`: all 41 controls, the same set as v1, seven columns, each status one the register's "Status Definitions" table defines; `NOT_STARTED` has no evidence path; `EVIDENCE_SUBMITTED` / `VERIFIED_*` name an `evidence_v2/` path; `NOT_APPLICABLE` / `DEFERRED` / `BLOCKED` carry a reason. Register v2 itself unchanged. |
| Evidence Requested | — |
| Evidence Received | Agent run in the device shell: the E0 test file 22 passed; three planted register defects (undefined status, evidence path on `NOT_STARTED`, `VERIFIED_PASS` without evidence) each refused. |
| Verification Result | PASS (agent). Operator to re-run with `py -3.10` and commit. |
| Next Action | Operator: `py -3.10 -m pytest tests/test_evidence_protocol_scaffold.py`, then commit. |

---

### 2026-10-23 — R3: IaC skeleton and old-ID guard — closed

| Field | Value |
|---|---|
| Timestamp | 2026-10-23T14:55:00Z |
| Control ID | R3 (scaffolding) |
| Action Taken | Operator committed R3 as `be3198f` and the E0 test fix as `f5d8d2a` (E0 test file 22 passed under `py -3.10` 3.10.6), and confirmed R3 in session. R3 ticked in `plans/aws_redeployment_tickets.md`; `evidence_v2/R3/VERIFICATION.md` done conditions completed. |
| Evidence Requested | — |
| Evidence Received | `evidence_v2/R3/VERIFICATION.md` (all criteria PASS) |
| Verification Result | R3 DONE. |
| Next Action | Frontier: R4 (network stack; `network.json` complete), R5 (IAM stack; OD7 list as parameters), R12a (parameterised collector, reads `outputs_contract.json`), with R9, R9e, R10. R4 is the first real stack creation and first shows whether the `DeployTarget` rule evaluates (F-OD6r3-2). |

---

### 2026-10-24 — R4: network template filled, decisions recorded, step sheet written

| Field | Value |
|---|---|
| Timestamp | 2026-10-24T00:40:00Z |
| Control ID | DC-03, DC-05, DC-06, DC-07, PL-8 (preparation; nothing created yet) |
| Action Taken | Operator settled the four open points of `plans/aws_redeployment_r4_handoff_2026-10-23.md` §4 in session ('1a, 2b + record igen, 3a read-only, 3c igen, 4 a+b'); recorded as `docs/tier4_orchestration_state/decision_log/aws-redeployment-r4-network_2026-10-24.json` (R4-D1 loopback placeholder replaces the default egress; R4-D2 lasting rule: the VPC's default security group carries no rule; R4-D3 read-only endpoint policy on the deploy bucket with `aws:ResourceAccount` and `aws:PrincipalAccount`; R4-D4 `AWS::EC2::Route` forbidden by the template guard plus `tests/test_aws_network_template.py`). `deploy/aws/templates/10-network.yaml` filled: VPC (DNS on), one private subnet, route table + association, host SG (egress 443 to prefix list inline, to endpoint SG standalone), endpoint SG (ingress 443 from host SG, placeholder egress), S3 gateway endpoint, seven contract outputs; `SkeletonPlaceholder` removed. `tools/aws_template_guard.py` refuses `AWS::EC2::Route` (reported once); guard test fixtures adjusted; `deploy/aws/README.md` updated. `evidence_v2/R4/STEPS.md` (10 steps, three rounds; change set read before execution) and `RUNLOG.md` skeleton written. |
| Evidence Requested | `R4_01`–`R4_10`, `R4_outputs.json` per `STEPS.md` |
| Evidence Received | none yet. Agent checks in the device shell (Linux, Python 3.10.12): cfn-lint 1.57.2 `--regions eu-north-1` exit 0 on all six templates; template guard `CLEAN: 6 template(s)`; old-ID guard `CLEAN (20 ids checked)`; secret scan of `evidence_v2/R4` `CLEAN`; `pytest` 143 passed over the four AWS test files and the E0 scaffold test (121 over the four AWS files). |
| Verification Result | Pending operator run. |
| Next Action | Operator: round 1 (steps 01–04), hand back; both read `R4_04_change-set.json` (eight `Add` entries, nothing hourly; F-OD6r3-2 shows here) before step 05. |

### 2026-10-24 — R4: network stack created and verified

| Field | Value |
|---|---|
| Timestamp | 2026-10-24T00:55:00Z |
| Control ID | DC-06, PL-8 (VERIFIED_PASS); DC-03, DC-07 (IN_PROGRESS, SG halves); DC-05 (IN_PROGRESS, S3 half) |
| Action Taken | Operator ran `evidence_v2/R4/STEPS.md` steps 01–09 on 2026-10-23 22:20–22:41 UTC (PowerShell, profile `po-r1`). Change set `r4-create-01` read by both before execution: eight `Add` entries, nothing hourly. Stack `proposal-orchestrator-network` `CREATE_COMPLETE` (first stack in the account; `cloudformation:CreateStack` allowed in eu-north-1, F-OD1r1-4 Confirmed; the `DeployTarget` rule's pseudo-parameter references accepted, F-OD6r3-2 Confirmed as accepted, enforcement on mismatch Inferred). Outputs saved to `R4_outputs.json`. The VPC's default security group emptied by rule id (R4-D2). Credits 199.99 USD before and after. |
| Evidence Requested | `R4_01`–`R4_09`, `R4_outputs.json` |
| Evidence Received | All 29 files; agent re-checked each against the step-sheet criteria in the device shell (`VERIFICATION.md`: every criterion PASS; step 10 pending). Secret scan and old-ID guard CLEAN on the agent's run. |
| Verification Result | PASS for every criterion of rounds 1–2; ticket criteria 1–4 PASS. Register v2 rows DC-03, DC-05, DC-06, DC-07 (wording corrected), PL-8 updated. |
| Next Action | Operator: round 3 (step 10: secret scan and old-ID guard over the finished folder), then `py -3.10 -m pytest tests/test_evidence_protocol_scaffold.py` (register v2 statuses) and commit; confirm in session. Agent then ticks R4. R7 then waits only on R6; R11 on R5–R8. |

### 2026-10-24 — R4: network base stack — closed

| Field | Value |
|---|---|
| Timestamp | 2026-10-24T01:05:00Z |
| Control ID | DC-06, PL-8 (VERIFIED_PASS); DC-03, DC-05, DC-07 (IN_PROGRESS) |
| Action Taken | Operator ran step 10 (secret scan `CLEAN`, old-ID guard `CLEAN`), `pytest` 143 passed under `py -3.10` 3.10.6, committed R4 as `5819488` and confirmed in session. R4 ticked in `plans/aws_redeployment_tickets.md`; `evidence_v2/R4/VERIFICATION.md` done conditions completed. |
| Evidence Requested | — |
| Evidence Received | `evidence_v2/R4/VERIFICATION.md` (all criteria PASS), `R4_10_secret-scan.txt`, `R4_10_old-id-guard.txt` |
| Verification Result | R4 DONE. |
| Next Action | Frontier: R5 (IAM stack; OD7 lists as parameters; imports nothing from R4 but its policies may name the deploy bucket by derived name), R12a (collector; add the default-SG check, R4-D2), R9, R9e, R10. R7 waits on R6; R11 on R5–R8. R5 handoff written: `plans/aws_redeployment_r5_handoff_2026-10-24.md`. Operator: "Close R4" commit (tickets file, VERIFICATION, RUNLOG, worklog, R5 handoff). |

### 2026-10-25 — R5: IAM template filled, decisions recorded, step sheet written

| Field | Value |
|---|---|
| Timestamp | 2026-10-25T14:50:00Z |
| Control ID | DC-09, DC-10, DC-11, DC-12, DC-13, DC-16 (preparation; nothing created yet) |
| Action Taken | Operator settled the R5 handoff §4 points in session ('1-9 a opció'); recorded as `docs/tier4_orchestration_state/decision_log/aws-redeployment-r5-iam_2026-10-25.json` (R5-D1 lasting rule `bundles/` prefix; R5-D2 S3 deny outside it; R5-D3 invoke conditions corrected for cross-Region inference, F-R5-2; R5-D4 lasting rule flow-log group `/proposal-orchestrator/vpc-flow-logs`; R5-D5 fixed names; R5-D6 no GenerateDataKey, ViaService in R6; R5-D7 SSM actions from evidence; R5-D8 guard and tests; R5-D9 register statuses). Round 1 read-only lookups run by the operator (`R5_01`–`R5_03`). `deploy/aws/templates/20-iam.yaml` filled (nine resources, seven contract outputs); `tools/aws_template_guard.py` UNTAGGABLE_TYPES += ManagedPolicy, InstanceProfile; `tests/test_aws_iam_template.py` (24 tests); guard test extended; `deploy/aws/README.md` updated. `evidence_v2/R5/STEPS.md` written. |
| Evidence Requested | `R5_01`–`R5_11`, `R5_outputs.json` per `STEPS.md` |
| Evidence Received | `R5_01`–`R5_03` (all PASS; 03d criterion corrected, F-R5-5). Agent checks: cfn-lint 1.57.2 exit 0; template guard CLEAN (6); old-ID guard CLEAN; 146 passed over the five AWS test files. |
| Verification Result | Round 1 PASS; template ready for the change set. |
| Next Action | Operator: steps 04–05; both read `R5_05_change-set.json` before execution. |

### 2026-10-25 — R5: IAM stack created and verified

| Field | Value |
|---|---|
| Timestamp | 2026-10-25T21:55:00Z |
| Control ID | DC-10, DC-11, DC-12, DC-13 (VERIFIED_PASS); DC-09, DC-16 (IN_PROGRESS) |
| Action Taken | Operator ran steps 04–05 (lint, guards, 146 passed; change set `r5-create-01`, nine `Add`, `CAPABILITY_NAMED_IAM`), gave the go, ran steps 06–11 and `STEPS_fix1.md` steps 12–13. Stack `proposal-orchestrator-iam` `CREATE_COMPLETE`. Three step-sheet errors of the agent, each recorded and corrected without editing evidence: 05 criterion asked for a field `describe-change-set` does not return; 09 left seven cases without `aws:RequestedRegion`, so the organization's SCP decided them (re-run as step 12); 11 and the first step 13 wrote pattern names into the scanned folder (re-collected; step 13 revised). |
| Evidence Requested | — |
| Evidence Received | `evidence_v2/R5/` (`VERIFICATION.md`: every criterion PASS, seven superseded step-09 files N/A); `R5_outputs.json`; `R5_11_pytest.txt` 168 passed; secret scan and old-ID guard CLEAN. Credits 199.99 USD before and after. |
| Verification Result | PASS; ticket criteria 1–4 PASS. Register v2 rows DC-09–DC-13, DC-16 updated. |
| Next Action | Operator: commit R5 and confirm in session; agent then ticks R5. Frontier then: R6 (imports `RuntimeRoleArn`), R12a, R9, R9e, R10. R6 handoff written: `plans/aws_redeployment_r6_handoff_2026-10-25.md`. |

### 2026-10-26 — R5: IAM stack — closed

| Field | Value |
|---|---|
| Timestamp | 2026-10-26T16:20:00Z |
| Control ID | DC-10, DC-11, DC-12, DC-13 (VERIFIED_PASS); DC-09, DC-16 (IN_PROGRESS) |
| Action Taken | Operator committed R5 as `8dccd77` (template, guard, tests, decision record, register, worklog, `evidence_v2/R5/`, R6 handoff) and confirmed in session. R5 ticked in `plans/aws_redeployment_tickets.md`; `evidence_v2/R5/VERIFICATION.md` done conditions completed. |
| Evidence Requested | — |
| Evidence Received | `evidence_v2/R5/VERIFICATION.md` (all criteria PASS; seven superseded step-09 files N/A), `R5_11_pytest.txt` 168 passed, `R5_11_secret-scan.txt`, `R5_11_old-id-guard.txt` |
| Verification Result | R5 DONE. |
| Next Action | Frontier: R6 (handoff `plans/aws_redeployment_r6_handoff_2026-10-25.md`), R12a, R9, R9e, R10. R7 waits on R6; R8 on R6; R11 on R6–R8. Operator: "Close R5" commit (tickets file, VERIFICATION, worklog, R6 handoff header). |


### 2026-10-26 — R6: KMS template filled, decisions recorded, change set ready

| Field | Value |
|---|---|
| Timestamp | 2026-10-26T16:50:00Z |
| Control ID | DC-18, DC-19 (preparation; the key is not created yet) |
| Action Taken | Operator settled the R6 handoff §4 points in session ('1–9 a', 4b included; 1 USD/month key fee acknowledged as the OD6-r3 'free (key: monthly)' case) and the agent's added point 10 ('10a'); recorded as `docs/tier4_orchestration_state/decision_log/aws-redeployment-r6-kms_2026-10-26.json` (R6-D1 cost; R6-D2 lasting rule trail `proposal-orchestrator-bedrock-trail`, home eu-north-1; R6-D3 runtime grant via Secrets Manager and S3 only; R6-D4 no admin statement, `AdminRoleArn` out of the kms stack, superseding OD6-r3-parameters for kms only; R6-D5 Retain, 30-day window; R6-D6 rotation 365; R6-D7 tests; R6-D8 exit-condition-2 evidence; R6-D9 register statuses; R6-D10 lasting rule: no CloudTrail decrypt, no S3 Bucket Key on the trail bucket). Round 1 read-only lookups run by the operator (`R6_01`–`R6_03`). `deploy/aws/templates/30-kms.yaml` filled (key, alias, three contract outputs); `parameters/kms.json` without `AdminRoleArn`; `tests/test_aws_kms_template.py` (12 tests); contract test's admin-role case narrowed to the secret stack; `deploy/aws/README.md` updated. `evidence_v2/R6/STEPS.md` steps 01–05 written. Round 1b run by the operator. |
| Evidence Requested | `R6_01`–`R6_11`, `R6_outputs.json` per `STEPS.md` |
| Evidence Received | `R6_01`–`R6_05` (all PASS). Change set `r6-create-01`: two `Add` (`ProjectKey`, `ProjectKeyAlias`), no capability, no `AdminRoleArn`. Agent checks: cfn-lint 1.57.2 exit 0; template guard CLEAN (6); old-ID guard CLEAN; 157 passed (agent Python 3.10.12, operator Python 3.10.6); secret scan of `evidence_v2/R6` CLEAN. |
| Verification Result | Rounds 1 and 1b PASS; change set ready for the operator's go. |
| Next Action | Operator: read `R6_05_change-set.json` and give the go in session (starts the key's monthly fee); agent then adds steps 06–11. |

### 2026-10-26 — R6: KMS stack created and verified

| Field | Value |
|---|---|
| Timestamp | 2026-10-26T17:05:00Z |
| Control ID | DC-18, DC-19 (VERIFIED_PASS) |
| Action Taken | Operator gave the go on change set `r6-create-01` ("mehet") and ran steps 06–10. Stack `proposal-orchestrator-kms` `CREATE_COMPLETE`: key `4ccc45a1-f205-4775-aa0b-195290bf1561` and `alias/proposal-orchestrator`. Agent verified every file by script and compared the live key policy with the resolved template statement by statement (equal). |
| Evidence Requested | `R6_11_*` (round 3: tests, old-ID guard, secret scan) |
| Evidence Received | `evidence_v2/R6/R6_01`–`R6_10`, `R6_outputs.json` (`VERIFICATION.md`: every criterion PASS except step 11, pending). Rotation on, 365 days; alias resolves to the key; five-statement key policy; no grants; runtime role unchanged since R5; IAM simulation `implicitDeny` for `kms:Decrypt`/`DescribeKey` with the boundary and organizations allowing. Credits 199.99 USD before and after. |
| Verification Result | Rounds 1–2 PASS; ticket criteria 1–3 PASS. Register v2 rows DC-18, DC-19 updated (R6-D9). |
| Next Action | Operator: step 11 (tests `-q`, old-ID guard, secret scan last), commit R6 and confirm in session; agent then completes `VERIFICATION.md` and ticks R6. Then R7 (trail name and Bucket-Key rule from R6-D2, R6-D10) and R8 open. |

### 2026-10-26 — R6: KMS stack — closed

| Field | Value |
|---|---|
| Timestamp | 2026-10-26T17:10:00Z |
| Control ID | DC-18, DC-19 (VERIFIED_PASS) |
| Action Taken | Operator ran step 11 (Python 3.10.6, 179 passed; old-ID guard and secret scan CLEAN, scan last), committed R6 as `0487e68` (template, parameter file, README, tests, decision record, register, worklog, `evidence_v2/R6/`) and confirmed in session. R6 ticked in `plans/aws_redeployment_tickets.md`; `evidence_v2/R6/VERIFICATION.md` done conditions completed. R7 handoff written. |
| Evidence Requested | — |
| Evidence Received | `evidence_v2/R6/VERIFICATION.md` (every criterion PASS, no N/A), `R6_11_pytest.txt`, `R6_11_old-id-guard.txt`, `R6_11_secret-scan.txt` |
| Verification Result | R6 DONE. |
| Next Action | Frontier: R7 (handoff `plans/aws_redeployment_r7_handoff_2026-10-26.md`), R8, R12a, R9, R9e, R10. R11 waits on R7 and R8. Operator: "Close R6" commit (tickets file, VERIFICATION, worklog, R7 handoff). |

### 2026-10-26 — R7: audit template filled, decisions recorded, change set ready

| Field | Value |
|---|---|
| Timestamp | 2026-10-26T17:37:00Z |
| Control ID | DC-08, DC-23, DC-24, DC-25, DC-27, DC-28, DC-29, DC-30 (preparation; nothing created yet) |
| Action Taken | Operator settled the R7 handoff §4 points and the agent's points 11–16 in session ('1–16 a, 2 = 2a igen + 2b (b), 3 (b), 5 (a) 600 s'); recorded as `docs/tier4_orchestration_state/decision_log/aws-redeployment-r7-audit_2026-10-26.json` (R7-D1 to R7-D16). Round 1 read-only lookups run by the operator (`R7_01`–`R7_03`). Agent read the CloudFormation reference pages of the five resource types and the S3 / CloudTrail guides (F-R7-3 to F-R7-5), filled `deploy/aws/templates/40-audit.yaml` (two buckets with policies, trail, flow-log group, VPC flow log, six contract outputs), changed `outputs_contract.json` (`VpcId` consumer R7, `PrivateSubnetId` no longer R7; R7-D11), wrote `tests/test_aws_audit_template.py` (20 tests) and updated `deploy/aws/README.md`. `evidence_v2/R7/STEPS.md` steps 01–05 written. Round 1b run by the operator. |
| Evidence Requested | `R7_01`–`R7_12`, `R7_outputs.json` per `STEPS.md` |
| Evidence Received | `R7_01`–`R7_05` (all PASS). Change set `r7-create-01`: seven `Add`, no capability. Agent checks: cfn-lint 1.57.2 exit 0; template guard CLEAN (6); old-ID guard CLEAN; 177 passed (agent Python 3.10.12, operator Python 3.10.6); secret scan of `evidence_v2/R7` CLEAN. |
| Verification Result | Rounds 1 and 1b PASS; change set ready for the operator's go. |
| Next Action | Operator: go on `R7_05_change-set.json`; point 17 (test uploads). |

### 2026-10-26 — R7: audit stack created and verified

| Field | Value |
|---|---|
| Timestamp | 2026-10-26T19:40:00Z |
| Control ID | DC-08, DC-23, DC-24, DC-25, DC-27, DC-28, DC-29, DC-30 (VERIFIED_PASS); DC-19 (note) |
| Action Taken | Operator gave the go and point 17 ('17 a, go 06') and ran steps 06–10; later point 18 ('18a') and steps 11 and 11b. Stack `proposal-orchestrator-audit` `CREATE_COMPLETE` (trail logging since 17:44:09Z). Agent verified every file by script and compared both live bucket policies with the resolved template (equal); added R7-D17, R7-D18 and findings F-R7-6 to F-R7-8 to the decision record; dropped a planned simulation of the runtime role against the bucket policy (F-R7-7). |
| Evidence Requested | `R7_12_*` (tests, old-ID guard, secret scan last) |
| Evidence Received | `evidence_v2/R7/R7_06`–`R7_11b`, `R7_outputs.json` (`VERIFICATION.md`: every criterion PASS except step 12, pending). Both buckets CMK-encrypted (Bucket Key off on the trail bucket, on on the deploy bucket), BPA, versioning, owner-enforced; policies as the template; trail delivering SSE-KMS log and digest objects without a CloudTrail decrypt grant (R6-D10 holds); `validate-logs` 2/2 digests and 12/12 log files valid; one log group (CMK, 90 days); VPC flow log ACTIVE / SUCCESS, no records before R11; invocation logging unset, no `/aws/bedrock` group; deploy bucket refused `AES256` and key-less `aws:kms` uploads and accepted a header-less one with the CMK. Credits 199.99 USD before and after. |
| Verification Result | Rounds 1–3 PASS; ticket criteria 1–5 PASS. Register v2 rows DC-08, DC-23, DC-24, DC-25, DC-27, DC-28, DC-29, DC-30 updated; DC-19 note updated (R7-D10, R7-D18). |
| Next Action | Operator: step 12 (tests `-q`, old-ID guard, secret scan last), commit R7 and confirm in session; agent then completes `VERIFICATION.md` and ticks R7. R11 then waits only on R8. |

### 2026-10-26 — R7: audit and storage stack — closed

| Field | Value |
|---|---|
| Timestamp | 2026-10-26T20:40:00Z |
| Control ID | DC-08, DC-23, DC-24, DC-25, DC-27, DC-28, DC-29, DC-30 (VERIFIED_PASS); DC-19 (note) |
| Action Taken | Operator ran step 12 (Python 3.10.6, 177 passed; old-ID guard and secret scan CLEAN, scan last), committed R7 as `874edeb` (template, contract, README, test, decision record, register, worklog, `evidence_v2/R7/`) and confirmed in session. R7 ticked in `plans/aws_redeployment_tickets.md`; `evidence_v2/R7/VERIFICATION.md` done conditions completed. |
| Evidence Requested | — |
| Evidence Received | `evidence_v2/R7/VERIFICATION.md` (every criterion PASS, no N/A), `R7_12_pytest.txt`, `R7_12_old-id-guard.txt`, `R7_12_secret-scan.txt` |
| Verification Result | R7 DONE. |
| Next Action | Frontier: R8, R12a, R9, R9e, R10. R11 waits only on R8. Operator: "Close R7" commit (tickets file, VERIFICATION, worklog). Open for R11: flow-log records and the R5-D4 gap (R7-D18), DC-26, the deploy bucket's runtime-role denies by live calls (F-R7-7). |

### 2026-10-26 — R8: secret template filled, decisions recorded, change set ready

| Field | Value |
|---|---|
| Timestamp | 2026-10-26T22:20:00Z |
| Control ID | DC-20, DC-21, DC-22 (planned: NOT_APPLICABLE, R8-D14); DC-19, DC-33–DC-35 (notes) |
| Action Taken | Operator settled the R8 handoff points 1–10 and agent points 11–16 ('1-16a') and ran round 1 (steps 01–03, read-only). Agent verified the files by script, then filled `50-secret.yaml` (retained secret with the imported KeyArn, five non-credential values built in the template, preset `BEDROCK_CONVERSE_EU`; deny-only resource policy with `BlockPublicPolicy` and a lockout-safe admin exception), wrote `tests/test_aws_env_config_template.py`, `tools/env_config_digest.py` and decision record `aws-redeployment-r8-secret_2026-10-26`, updated the README and ticket R9e (R8-D3), and added steps 04–05. |
| Evidence Requested | `R8_04_*` (lint, guards, tests), `R8_05_*` (change set `r8-create-01`, scan) |
| Evidence Received | `evidence_v2/R8/R8_01`–`R8_03`: name free, no secret in the Region (scheduled deletions included), no secret stack, key Enabled with the R6 policy, admin role `/managed/AccountFullAccessRole`, 23 exports equal to the outputs files; eu-north-1 prices 0.40 USD per secret-month and 0.05 USD per 10,000 requests (Price List API). Credits 199.99 USD. |
| Verification Result | Round 1 PASS; secret scan and old-ID guard CLEAN. Agent's run: cfn-lint exit 0, template guard CLEAN (6), 196 passed. |
| Next Action | Operator: steps 04–05, then the go on `R8_05_change-set.json` (exactly two `Add`). |

### 2026-10-27 — R8: secret stack created and verified

| Field | Value |
|---|---|
| Timestamp | 2026-10-27T16:05:00Z |
| Control ID | DC-20, DC-21 (VERIFIED_PASS); DC-22 (NOT_APPLICABLE); DC-19, DC-33–DC-35 (notes) |
| Action Taken | Operator gave the go ('go') and ran steps 06–10; a first attempt of 07–10 ran before step 06 and step 06 was repeated before the in-order re-run (both recorded in `RUNLOG.md`; point 17 '17a', R8-D17). Stack `proposal-orchestrator-secret` `CREATE_COMPLETE` 15:56:29Z. Agent verified every file by script, compared the live resource policy with the resolved template (equal), wrote `VERIFICATION.md`, updated register v2 and the decision record (F-R8-9, R8-D17). |
| Evidence Requested | `R8_11_*` (tests, old-ID guard, secret scan last) |
| Evidence Received | `evidence_v2/R8/R8_06`–`R8_10`, `R8_outputs.json`: secret `…/env-config-KTsWow` with the R6 `KeyArn`, one `AWSCURRENT` version, no rotation or replica; deny-only policy as the template; the admin role's digest read `MATCH` (five keys) and not denied. Credits 199.99 → 199.98 USD. |
| Verification Result | Rounds 1–2 PASS (step 06 exit file by substitute evidence, R8-D17); ticket criteria 1–3 PASS, the final scan pending. Register v2 rows DC-20, DC-21, DC-22 updated; DC-19 and DC-33–DC-35 notes. |
| Next Action | Operator: step 11 (tests `-q`, old-ID guard, secret scan last), commit R8 and confirm in session; agent then completes `VERIFICATION.md` and ticks R8. R11 is then unblocked (explicit go for hourly cost). |

### 2026-10-27 — R8: runtime secret — closed

| Field | Value |
|---|---|
| Timestamp | 2026-10-27T16:15:00Z |
| Control ID | DC-20, DC-21 (VERIFIED_PASS); DC-22 (NOT_APPLICABLE); DC-19, DC-33–DC-35 (notes) |
| Action Taken | Operator ran step 11 (Python 3.10.6, 196 passed; old-ID guard and secret scan CLEAN, scan last) and confirmed in session ("Zárd le az R8-at és commitolok"). Agent completed `evidence_v2/R8/VERIFICATION.md` (every criterion PASS; step 06's exit file on substitute evidence, R8-D17), re-ran the scan and the old-ID guard after the edit (CLEAN), and ticked R8 in `plans/aws_redeployment_tickets.md`. The operator commits R8 and this closing together. |
| Evidence Requested | — |
| Evidence Received | `evidence_v2/R8/VERIFICATION.md`, `R8_11_pytest.txt`, `R8_11_old-id-guard.txt`, `R8_11_secret-scan.txt` |
| Verification Result | R8 DONE. |
| Next Action | Frontier: R12a, R9, R9e, R10; R11 is unblocked and needs the operator's explicit go (first hourly cost). Open for R9e: the `BEDROCK_CONVERSE_EU` preset (R8-D3). Open for R11: the runtime role's first read of the secret (DC-19, DC-20, DC-21 runtime half). |

### 2026-10-27 — R9: runtime configuration from the secret — verified

| Field | Value |
|---|---|
| Timestamp | 2026-10-27T17:50:00Z |
| Control ID | DC-33–DC-35 (notes); F4, F6 |
| Action Taken | Operator settled the R9 handoff points 1–12 and agent points 13–20 ('1–20 a') and, after the baseline, points 21–23 ('21–23 a'). Operator ran step 01 (baseline on `8c20087`: 202 failed, 8890 passed, 86 skipped). Agent wrote the launcher `runner/host_env.py`, the production-mode Region refusal and F6 in `runner/transport/config.py`, the required Region in `runner/transport/bedrock_converse.py`, the `AWS_REGION` rule in `runner/offline_bundle.py`, `tests/test_host_env_launcher.py` and additions in three test modules, and decision record `aws-redeployment-r9-runtime-config_2026-10-27` (R9-D1 to R9-D23, F-R9-1 to F-R9-7). Operator ran steps 03–05. Agent error recorded in `RUNLOG.md`: a `git stash` in the connected folder left a lock file (renamed) and a temporary object; no change lost. |
| Evidence Requested | `R9_01_*`, `R9_03_*`, `R9_04_full-pytest.txt`, `R9_05_*` |
| Evidence Received | `evidence_v2/R9/`: R9 and transport tests 1 failed (baseline `test_registry_count`), 302 passed; full suite 201 failed, all in the baseline set, 8954 passed; old-ID guard and secret scan CLEAN (scan last). |
| Verification Result | Every `VERIFICATION.md` criterion PASS; ticket criteria 1–4 PASS. F-R9-1: the test suite makes outbound HTTP requests (follow-up proposed, outside R9). |
| Next Action | Operator: confirm in session; agent then ticks R9 and re-runs the scan; operator commits ("Close R9") and deletes `.git/stale-index-lock-r9-20261027` and `.git/objects/09/tmp_obj_pEjQci`; operator checks whether the `.env.harness` key needs revoking. Then R9e (preset `BEDROCK_CONVERSE_EU`, `for_r9e`), R10 rebases on R9; R12b needs R11 and R12a. |

### 2026-10-27 — R9: runtime configuration from the secret — closed

| Field | Value |
|---|---|
| Timestamp | 2026-10-27T17:50:00Z |
| Control ID | DC-33–DC-35 (notes); F4, F6 |
| Action Taken | Operator confirmed in session ("Zárd le az R9-et"). Agent ticked R9 in `plans/aws_redeployment_tickets.md` and completed `evidence_v2/R9/VERIFICATION.md` (every criterion PASS). |
| Evidence Requested | — |
| Evidence Received | `evidence_v2/R9/VERIFICATION.md`, `R9_04_full-pytest.txt`, `R9_05_old-id-guard.txt`, `R9_05_secret-scan.txt` |
| Verification Result | R9 DONE. |
| Next Action | Operator: commit "Close R9"; delete `.git/stale-index-lock-r9-20261027` and `.git/objects/09/tmp_obj_pEjQci`; check the `.env.harness` key (F-R9-1). Frontier: R9e (unblocked; `for_r9e` in the R9 record), R10 (rebases on R9), R12a; R11 needs the operator's explicit go (first hourly cost). |


### 2026-10-28 — R9e: EU region support — verified

| Field | Value |
|---|---|
| Timestamp | 2026-10-27T23:35:00Z |
| Control ID | none (no register row, R9e-D10); F9 for the code, the transport tests and the AN12 runbook |
| Action Taken | Operator settled the R9e handoff points 1–11 and agent points 12–18 ('1–18 a') and, after the baseline, points 19–20 ('19–20 a'). Operator ran step 01 (baseline on `d1e767b`, handoff staged: 202 failed, 8953 passed, 86 skipped; deviation R9e-D19) and committed the handoff (`175441e starting R9e`). Agent added the preset `BEDROCK_CONVERSE_EU` to `runner/transport/config.py`, eu-north-1 to `ALLOWED_REGIONS`, the host's drafter model to the AN1c guard under production mode (`harness/judge.py`), the `AWS_REGION`-only rule to `harness/commands/converse_smoke.py`, the launcher, Region and id rule to `plans/msca_dn_an12_host_runbook.md`, the tests in 10 test modules, and decision record `aws-redeployment-r9e-eu-region_2026-10-27`. |
| Evidence Requested | `R9e_01_*`, `R9e_03_*`, `R9e_04_full-pytest.txt`, `R9e_05_*` |
| Evidence Received | `evidence_v2/R9e/`: R9e tests and touched modules 573 passed; full suite 200 failed, all in the baseline set, 8997 passed; old-ID guard and secret scan CLEAN (scan last). |
| Verification Result | Every `VERIFICATION.md` criterion PASS; ticket criteria 1–3 PASS (4 N/A, superseded). F-R9e-1: a transient Windows file lock failed one baseline test that writes into Tier 4. |
| Next Action | Operator: confirm in session; agent then ticks R9e and re-runs the scan; operator commits ("close R9e"). Then R15 needs R11 and R12b; R13 has the record's `for_r13` list. |

### 2026-10-28 — R9e: EU region support — closed

| Field | Value |
|---|---|
| Timestamp | 2026-10-28T16:35:00Z |
| Control ID | none; F9 (code, transport tests, AN12 runbook) |
| Action Taken | Operator confirmed in session ("zárd le a R9e-t") and committed the R9e change and evidence (`47a32d4 close r9e`). Agent then ticked R9e in `plans/aws_redeployment_tickets.md` and set `evidence_v2/R9e/VERIFICATION.md` to DONE (every criterion PASS). |
| Evidence Requested | — |
| Evidence Received | `evidence_v2/R9e/VERIFICATION.md`, `R9e_04_full-pytest.txt`, `R9e_05_old-id-guard.txt`, `R9e_05_secret-scan.txt` |
| Verification Result | R9e DONE. |
| Next Action | Operator: commit the tick, VERIFICATION, RUNLOG and worklog. Frontier: R10, R12a; R11 needs the operator's explicit go (first hourly cost); R15 needs R11 and R12b; R13 (after R12b) has the R9e record's `for_r13` list. |
