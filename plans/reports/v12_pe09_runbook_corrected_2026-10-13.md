# V12 completion report — the PE-09 runbook describes only what the code does

| Field | Value |
|---|---|
| Date | 2026-10-13 |
| Branch | `msca-dn-pre-eval` |
| Ticket | V12, gates G2, G4 and G5 |
| Closes | Finding F12, and V12's share of F04 |
| Decision record | `docs/tier4_orchestration_state/decision_log/msca-dn-pe09-runbook_2026-10-13.json` |
| Status | Agent-drafted. Acceptance is the operator's. |

## 1. What was wrong

The runbook is the only artifact of this milestone a human executes. It executes in a private
network, against a build nobody here can watch. A stale claim in it is therefore found by the
operator, mid-run, at the cost of a step.

Seven claims had gone stale or were never true.

| Claim | What the code does |
|---|---|
| The freeze checks fifteen conditions, including the planted-marker test | It runs 22 conditions. None is a marker check. The planted-marker test is a transport and isolation test |
| Checkpointing is a flag to remember | Checkpointing is the default, with a derived path and three flags that change it |
| No 2025 call text is in this repository, so copy the 2026 profile and list the differences | V09 pinned the 2025 authorities; V10 authored the profile from the matrix over them |
| The importer takes `--check` and `--repo-root` alone | V07 made the document configuration selectable with `--document` |
| Stage B uses the commands of Sections 4 to 6 | Stage B has no ESR, so `compare`, `review` and `diff` have nothing to read |
| The model and version pins read as properties of the run | Both are declared strings. The report records `model@version` and nothing else |
| A cross-baseline `diff` on the success path, refused by design | The refusal is certain, so the command is not a step |

The isolation controls were listed as what they enforce, with nothing on what they do not. An
external working directory is not an operating-system sandbox. An empty tool list is not permission
to send private proposal content to a provider.

## 2. What was built

A corrected runbook, and a test that keeps it correct.

`tests/test_msca_dn_pe09_runbook.py` reads the runbook rather than reviewing it. It takes every
documented command line, asks that command for its own `--help`, and fails on two conditions:

- a documented flag the parser does not accept;
- a flag the parser marks required that the documented line omits.

The second is the V06 failure mode. V06 made `--grounding-scope` required, and every documented
`preflight` and `assess` line was silently wrong until V06 corrected them by hand.

Four more checks hold the rest of the ticket:

| Check | What it refuses |
|---|---|
| The enumerated freeze conditions equal `BASELINE_CHECKS`, and the stated count equals its length | A documented condition list that drifts from the code's |
| Neither freeze heading mentions a marker, and the isolation section cites the test by name | The corrected claim quietly returning |
| Every backticked repository path, test module and test class resolves | A pointer to something that has been renamed or removed |
| No command line names the public comparison, and the refusal is still explained | The refused pair returning to the success path |

14 command lines are covered, over 12 commands: eight `blind_assessment` sub-commands, the
historical-profile check, its author, the importer and the dry import.

## 3. The guard is not vacuous

A guard over a document is worth only what it fails on. Measured: renaming `--grounding-scope` to
`--grounding-scopes` on one line, and dropping one letter from one condition name, failed three
checks — the documented-flag check, the required-flag check and the enumeration check. The runbook
was then restored from a copy taken before the mutation.

The flag reader is also checked against its own false-positive risk. Flags are read from the rows
argparse writes for each option, never from a description, so `--tools` — which appears only in help
prose — is correctly not treated as a flag the parser accepts.

## 4. What the corrected runbook now says

- **Section 3.** Two Doctoral Networks profiles exist, each with its call. Stage A loads the 2025
  historical one, and two commands check it against the pinned source index and the matrix. The two
  elements whose matrix rows are open are named, and no element is Confirmed.
- **Section 4.** The import route is V07's `--document official_original`, which reports
  `importable: false` and names five undeclared required fields. The measurement that would supply
  them is V08's dry import, and its procedure document is the authority for it.
- **Section 5.** The preflight, the assessment, checkpointing and its recovery, what the pins are,
  what isolation is not, and the freeze with its 22 conditions enumerated.
- **Section 6.** The audit, the comparison and the review, then a labelled manual reading in place of
  the refused `diff`. The `diff` that remains is the one that applies, between two comparisons over
  the same private baseline.
- **Section 8.** Stage B reuses Sections 4 and 5 and the `audit` command. The ESR comparison, its
  review and its diff are excluded, with the reason stated.
- **Section 11.** The gaps table loses the historical-profile row, which V10 closed, and gains the
  original's undeclared configuration fields, the missing register renderer for a submitted document,
  the cross-baseline reading and V13's readiness receipt.

## 5. Recovery is not a licence

One correction is a rule rather than a fact. The checkpoint exists so that a run which fails at call
44 does not discard 43 paid-for responses. It does not exist to let anyone draw again.

A malformed response stays in the checkpoint verbatim, with its hash and the parser's own message,
and is marked discarded. Nothing repairs it. A malformed criterion draw is asked again over the
identical prompt, at most twice. A parseable sample stands, whatever it says: only the parsers
discard a response, and a sample the operator dislikes is evidence rather than an accident. The
runbook now says this where the recovery flags are documented.

## 6. Checks run

| Check | Result |
|---|---|
| `tests/test_msca_dn_pe09_runbook.py` | 19 passed |
| `tests/harness/test_acceptance_lane.py` | 68 passed |
| The mutation run described in §3 | 3 checks failed, as intended |
| The repository's prose linter on the runbook | no errors |
| `py -3.10 -m tools.author_msca_dn_historical_profile --check` | `up to date` |
| `py -3.10 -m harness.commands.historical_profile --check` | `profile check: green` |
| `py -3.10 -m tools.import_external_proposal --environment` | on pin, reproduces the committed artifacts |
| `py -3.10 -m tools.import_external_proposal --document official_original --describe` | `importable: false`, five fields named |
| The full suite, `py -3.10 -m pytest tests` | 7,575 passed, 194 failed, 86 skipped |

No assessor ran. No runner phase was dispatched. No quota was spent, and the frozen 74.60 baseline is
untouched.

The 194 whole-run failures are the branch's known whole-run inflation, measured at 207 on 2026-10-07
against 54 per directory. None is in a module this ticket touches, and the three it does touch pass:
19, 68 and 29 checks.

## 7. One test contract changed

`tests/harness/test_acceptance_lane.py` held that no acceptance box in the V12 ticket section is
checked. That was right while V12 was open: the G4 acceptance of 2026-10-12 was then the only thing
that could have checked one, and it closed none of these corrections.

V12's own work closed them. The test now holds the attribution instead. The section keeps the
acceptance's limit as written, and a checked box must be accompanied by the dated status of the work
that closed it.

## 8. What this is not evidence of

- That PE-09 has been executed. No command here has been run against the original.
- That the documented sequence is sufficient. Each command it names exists, with the flags it names.
- That the private environment permits any content to leave it. Section 10 defers that to the
  environment's own rules.
- That V12 is accepted. Acceptance is the operator's.

## 9. What stays open

- Five required fields of the original's document configuration, and a fidelity register renderer for
  a submitted document. Both block Stage A step 1.
- No tool compares two comparisons over different baselines. The cross-baseline reading is manual and
  labelled as such.
- The grounding axis stays unassessable for an imported proposal until ticket X01.
- The operator's pre-run evidence about the assessor CLI, its version and the permitted processing
  route is a record without a validator until V13, which this ticket unblocks.
- The evidence half of F04 belongs to V13.
- **The runbook is over its length budget, and this report does not resolve it.**
  `docs/style/internal-docs-profile.md` §5 budgets a Plan at 2,500 words and says an over-budget
  document is split rather than compressed. The runbook was 2,525 words before this ticket and is
  3,577 now, because stating what the code does takes more words than asserting it. Compressing it
  would undo the ticket. The smallest split that would satisfy both is Section 2, whose deferral table
  already exists as `open_deferral_register_2026-10-12.json`, which the section now points at. That is
  an operator-facing deletion, so it is proposed here rather than made.

## 10. What the two-axis review changed

A standards review and a spec review ran in parallel over the finished change. Five findings were
acted on.

| Finding | Change |
|---|---|
| The `salvage` line omitted `--n` and `--criterion-n`, which bind the checkpoint as surely as the candidate does | Both are on the line, with `--out-dir` and a sentence on `--skip-criterion-scores` |
| Sections 5 and 6 both claimed "step 3" | Section 6 is step 4 |
| The same-baseline `diff` named no input that produces its after-side | It names one: a revised set of dispositions, as the public lineage did three times over one baseline |
| The four-item investigation list read as that `diff`'s output | The list has its own heading |
| `harness/HARNESS.md` still said the lane document names sixteen areas | Seventeen, which is what it names |

Three findings were not acted on, and each is stated rather than silently dropped. The flags are read
from `--help` rather than from a parser object, which is the surface the operator reads and the only
surface these twelve commands share. The ticket section's dated status is this ledger's own convention
for a closed ticket. The `handoff` lane area is required by V03's rule that a new MSCA-DN test module
joins the lane.

## 11. Artifacts

| Path | What |
|---|---|
| `plans/msca_dn_pe09_runbook.md` | The corrected runbook |
| `tests/test_msca_dn_pe09_runbook.py` | The guard, 19 checks |
| `harness/acceptance_lanes/msca_dn_historical.json` | The lane's new `handoff` area |
| `harness/ACCEPTANCE_LANE.md` | Its row in the lane document |
| `docs/tier4_orchestration_state/decision_log/msca-dn-pe09-runbook_2026-10-13.json` | The decision record |
