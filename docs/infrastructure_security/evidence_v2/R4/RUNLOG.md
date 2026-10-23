# R4 — run log

Kept by the agent from what the operator reports in session (marked as such).

| Field | Value |
|---|---|
| Step sheet | `STEPS.md` |
| Run date (UTC) | 2026-10-23 (round 1, steps 01–04, 22:20–22:21 UTC; round 2, steps 05–09, 22:30–22:41 UTC; round 3, step 10, ~22:50 UTC) |
| Operator | the operator (József) |
| Where run | PowerShell in the VS Code terminal on the workstation, repository root, profile `po-r1` (`aws login --profile po-r1` at ~22:19 UTC as `assumed-role/AccountFullAccessRole/<session>`) |
| Hourly-cost go given | n/a (R4 creates nothing with an hourly cost) |

## Steps

| Step | Started (UTC) | Run by | Result | Deviation from the step sheet | Error, and what was done about it |
|---|---|---|---|---|---|
| 01 | 22:20 | operator (reported in session) | ok | First attempt ran with an expired `po-r1` session (three `Your session has expired` errors into the `R4_01_*` files); `aws login` without `--profile` offered to overwrite the `default` profile and was declined (`n`) three times, correctly. Repeated after `aws login --profile po-r1`; the files were overwritten. | none on the final run. Plan FREE / ACTIVE, credits 199.99 USD, expires 2027-04-19; one budget `My Monthly Cost Budget` 10.0 USD, spend 0.006; notifications ACTUAL 100, ACTUAL 85, FORECASTED 100 all `OK`. STOP rule not triggered. |
| 02 | 22:20 | operator (reported in session) | ok | none | none. `Account` 797661577394; `Arn` assumed-role/AccountFullAccessRole/<session>. |
| 03 | 22:20 | operator (reported in session) | ok | none | none. cfn-lint 1.57.2 exit 0; template guard CLEAN (6); old-ID guard CLEAN (20 ids); pytest `121 passed` (Python 3.10.6, pytest 9.0.2) over the four AWS test files. |
| 04 | 22:20–22:21 | operator (reported in session) | ok | none | none. Change set `r4-create-01` `CREATE_COMPLETE` / `AVAILABLE`; eight `Add` entries, exactly the expected logical ids and types; `Capabilities` `[]`; tag `project`; seven parameters as in `network.json` plus defaults. **F-OD6r3-2:** CloudFormation accepted the `DeployTarget` rule's `Ref AWS::AccountId` / `AWS::Region` at change-set creation (no rejection, no `StatusReason`). Agent re-checked every round-1 file in the device shell against the criteria: all PASS; secret scan and old-ID guard CLEAN. |
| 05 | 22:30 | operator (reported in session, after the go given ~22:28 UTC on the change set) | ok | none | none. `execute-change-set exit=0`; `wait stack-create-complete` returned; stack `CREATE_COMPLETE`, tag `project`; events: all eight resources and the stack `CREATE_COMPLETE`, no failure or rollback. |
| 06 | 22:35 | operator (reported in session) | ok | none | none. Seven outputs with export names; ids as in `R4_outputs.json`. |
| 07 | 22:36–22:37 | operator (reported in session) | ok | none | none. Eleven files. (Two command lines appeared wrapped in the pasted terminal output as `--outputjson` and `-Encodingutf8`; the files on disk are correct JSON written with the right options — a paste artefact, not a deviation.) |
| 08 | 22:39 | operator (reported in session) | ok | none | none. Default group `sg-0a2fca76dd2129439`: two rules before (egress all, self-ingress all), both revoked by rule id (`Return` true each), `[]` after. |
| 09 | 22:41 | operator (reported in session) | ok | none | none. FREE / ACTIVE, 199.99 USD, unchanged. |
| 10 | ~22:50 | operator (reported in session) | ok | none | none. Secret scan `CLEAN`, old-ID guard `CLEAN` (20 ids), both `exit=0`; pytest `143 passed` over the five files. Committed as `5819488` (`completed R4`). |

## Notes

- Round 2 (steps 05–09) handed back 2026-10-23 ~22:43 UTC; agent verification in `VERIFICATION.md` (all PASS). Round 3 (step 10) run and committed 2026-10-23 ~22:52 UTC; operator confirmed R4 in session 2026-10-24.
- Round 1 (steps 01–04) handed back 2026-10-23 ~22:22 UTC. The agent's reading of `R4_04_change-set.json`: exactly the eight planned resources, nothing with an hourly cost; go for step 05 asked of the operator in session.
