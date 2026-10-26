# R5 — run log

Kept by the agent from what the operator reports in session (marked as such).

| Field | Value |
|---|---|
| Step sheet | `STEPS.md` |
| Run date (UTC) | 2026-10-25 (round 1, steps 01–03, 14:27–14:28 UTC; round 1b, steps 04–05, 14:42–14:43 UTC; round 2 and 3, steps 06–11, evening of 2026-10-25, handed back ~21:40 UTC) |
| Operator | the operator (József) |
| Where run | PowerShell in the VS Code terminal on the workstation, repository root, profile `po-r1` (`aws login --profile po-r1` at ~14:25 UTC as `assumed-role/AccountFullAccessRole/<session>`) |
| Hourly-cost go given | n/a (R5 creates nothing with an hourly cost) |

## Steps

| Step | Started (UTC) | Run by | Result | Deviation from the step sheet | Error, and what was done about it |
|---|---|---|---|---|---|
| 01 | 14:27 | operator (terminal output shared in session) | ok | none | none. Plan FREE / ACTIVE, credits 199.99 USD, expires 2027-04-19; one budget `My Monthly Cost Budget` 10.0 USD, spend 0.006; notifications ACTUAL 100, ACTUAL 85, FORECASTED 100 all `OK`. STOP rule not triggered. |
| 02 | 14:27 | operator (terminal output shared in session) | ok | none | none. `Account` 797661577394; `Arn` assumed-role/AccountFullAccessRole/<session>. |
| 03 | 14:27–14:28 | operator (terminal output shared in session) | ok | none by the operator. **Step-sheet error (agent):** 03d's criterion said `exit=255`; the CLI v2 returns 254 for a service error, and PowerShell wrapped the error text in the file. Criterion corrected in `STEPS.md` with a dated note; evidence unchanged (F-R5-5). | Expected error only (03d: `ValidationError … Stack with id proposal-orchestrator-iam does not exist`, `exit=254`). `AmazonSSMManagedInstanceCore` default version `v2`, 25 actions; no local policy; no instance profile; 13 roles, none `proposal-orchestrator-*` (three AWS-managed under `/managed/`, ten service-linked); seven Amazon foundation models listed (e.g. `amazon.nova-pro-v1:0`). |
| 04 | ~14:42 | operator (terminal output shared in session) | ok | `.venv-lint` was active; `py -3.10` still resolved to the system Python 3.10.6 (pytest header), so no effect. | none. cfn-lint 1.57.2 exit 0; template guard CLEAN (6); old-ID guard CLEAN (20 ids); pytest `146 passed` (Python 3.10.6, pytest 9.0.2). |
| 05 | 14:42–14:43 | operator (terminal output shared in session) | ok | none by the operator. **Step-sheet error (agent):** the criterion asked for `ChangeSetType` = `CREATE`, a field `describe-change-set` does not return (absent in R4 too). Criterion corrected in `STEPS.md` with a dated note; evidence unchanged. | none. Change set `r5-create-01` `CREATE_COMPLETE` / `AVAILABLE`, created 14:42:58 UTC; nine `Add` entries, exactly the expected logical ids and types; `Capabilities` `["CAPABILITY_NAMED_IAM"]`; tag `project`; six parameters equal to `iam.json` plus `ProjectName`. Agent compared the change map and parameters programmatically: equal. |
| 06 | evening | operator (terminal output shared in session, after the go on the change set) | ok | Re-signed in with `aws login --profile po-r1` first (new window, `.venv-lint` active). | none. `execute exit=0`; stack `CREATE_COMPLETE`, `CAPABILITY_NAMED_IAM`, tag `project`; events: the nine resources and the stack `CREATE_COMPLETE`, no failure or rollback. |
| 07 | evening | operator | ok | none | none. Seven outputs with export names; `R5_07_exports.json` matches. |
| 08 | evening | operator | ok | none | none. 19 files. Six customer-managed policies; documents equal the template with the parameters filled in (agent compared statement by statement). |
| 09 | evening | operator | partly superseded | none by the operator. **Step-sheet error (agent):** seven cases carried no `aws:RequestedRegion` context and were decided by the organization's SCP (`AllowedByOrganizations` false), not by R5's policies. | 21 of 28 files as expected, each with `AllowedByOrganizations` true. The seven SCP-decided files stay as history; re-run in `STEPS_fix1.md` step 12. |
| 10 | evening | operator | ok | none | none. FREE / ACTIVE, 199.99 USD, unchanged. |
| 11 | evening | operator | FAIL (re-collect) | Run before the agent's round-2 verification (the sheet put it in round 3); harmless. **Step-sheet error (agent):** pytest's verbose ids of the scaffold tests contain the four forbidden pattern names, so the log tripped `test_evidence_v2_tree_is_itself_clean` (`1 failed, 167 passed`) and a fresh scan of the folder now refuses it. No secret in it (agent read the lines). | Secret scan and old-ID guard ran before pytest: both CLEAN. Re-collected by `STEPS_fix1.md` step 13 (`-q`, scan after the tests). |

## Notes

- Round 1 handed back 2026-10-25 ~14:30 UTC. Agent checked every file in the device shell against the
  criteria: all PASS (03d after the criterion correction); secret scan and old-ID guard CLEAN. The two
  `/managed/` roles besides `AccountFullAccessRole` (`AWSManagedAccountManagementAccessRole`,
  `AWSManagedAdvancedFeaturesActivationRole`) are AWS-managed roles of the account's organization model
  (F-OD11r2-4), created with the account on 2026-08-11; not a concern for R5.
- Agent then filled `20-iam.yaml`, extended the template guard, wrote `tests/test_aws_iam_template.py`
  and decision record `aws-redeployment-r5-iam_2026-10-25`, and added steps 04–05 to `STEPS.md`. Agent's
  own run in the device shell (Python 3.10.12, cfn-lint 1.57.2): lint exit 0, template guard CLEAN (6),
  old-ID guard CLEAN, `146 passed` over the five AWS test files.
- Round 1b handed back 2026-10-25 ~14:45 UTC. Agent re-checked the round-1b files in the device shell: all PASS (step 05 after the criterion correction); secret scan and old-ID guard CLEAN. Agent added steps 06–11 to `STEPS.md`. Step 06 waits for the operator's go on the change set.
- Round 2/3 handed back 2026-10-25 ~21:40 UTC. Agent verification: steps 06, 07, 08, 10 PASS; step 09 PASS for 21 files, 7 superseded; step 11 to re-collect. `STEPS_fix1.md` written (steps 12 and 13).
- `STEPS_fix1.md` step 12 run 2026-10-25 ~21:47 UTC: eight files, all PASS (each result `AllowedByOrganizations` true; allowed cases also `AllowedByPermissionsBoundary` true; both `explicitDeny` cases matched `proposal-orchestrator-explicit-deny`).
- `STEPS_fix1.md` step 13, first run ~21:47 UTC: FAIL again, by the agent's error: the sheet's own explanation quoted a pattern name (`STEPS_fix1.md:26`), so the scaffold test failed and printed the finding into `R5_11_pytest.txt`, and the refused scan wrote the pattern names into `R5_11_secret-scan.txt`. Sheet text corrected (dated note); step 13 revised to remove the two refused files before re-collecting. Agent checked on a copy of the tree without those two files: scan CLEAN.
- `STEPS_fix1.md` step 13, second run ~21:53 UTC (operator, after removing the two refused files): `168 passed` (Python 3.10.6, quiet output, no pattern string), secret scan `CLEAN` `exit=0`, old-ID guard `CLEAN` `exit=0`. Agent re-checked: PASS; whole `evidence_v2` tree CLEAN. `VERIFICATION.md` written.
