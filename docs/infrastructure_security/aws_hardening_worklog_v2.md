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
| Next Action | Frontier: R5 (IAM stack; OD7 lists as parameters; imports nothing from R4 but its policies may name the deploy bucket by derived name), R12a (collector; add the default-SG check, R4-D2), R9, R9e, R10. R7 waits on R6; R11 on R5–R8. Operator: "Close R4" commit (tickets file, VERIFICATION, RUNLOG, worklog). |
