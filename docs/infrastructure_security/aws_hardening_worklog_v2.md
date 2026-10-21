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
| Next Action | Operator re-runs `py -3.10 -m pytest tests/test_evidence_protocol_scaffold.py` on Windows. |

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
