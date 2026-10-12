# V11 completion report — the open-deferral register

Date: 2026-10-12.
Branch: `msca-dn-pre-eval`, from `7214a10`.
Ticket: V11 of `plans/msca_dn_historical_validation_tickets.md`.
Closes: finding F11 of `plans/reports/MSCA_DN_Readiness_Audit_2026-10-08.md`.
Decision record: `docs/tier4_orchestration_state/decision_log/msca-dn-open-deferrals_2026-10-12.json`.

Five of five acceptance criteria are closed. F11 closes, and V11 no longer blocks V14. No row in the
register is closed. No assessor ran, no quota was spent, and the frozen 74.60 baseline is untouched.

One check did not run. The acceptance lane was killed by the host for low memory on four attempts, so
its single-process result is unmeasured and the decision record declares that `Unresolved`. Section 6.1
states what was measured in its place. Nothing in this change reports a lane figure.

Environment: Python 3.10.6, the pin V01 established
(`docs/tier4_orchestration_state/decision_log/msca-dn-extraction-environment-pin_2026-10-08.json`).

## 1. What was wrong

The approval of 2026-10-08 settled some things and deferred others. The deferred ones sat in four
records at once, and no artifact held them together. Measured on the committed records:

| Record | What it leaves open |
|---|---|
| `dispositions_f60ae6e0a2a1_approved.json` | 10 `operator_decision_required` rows, 10 `agent_recommended_pending_operator_review` rows, 12 `open_operator_decisions`, 2 assessor validation cases, 1 row declared Unresolved |
| `operator_approval_2026-10-08.md` | a separate 8-row original-dependent deferred table |
| `pe08_review_and_pe09_handoff_tickets.md` | 1 unchecked R04 criterion, its precondition deferred by D13 |

That is 34 open items. A ticket checkbox holds none of them, because a checkbox has no room for the
evidence that would close it. A milestone that accepted the package would close all 34 by silence,
and an inherited deferral has no owner, no closure evidence and no record that it is still open.

## 2. What was built

`harness/deferral_register.py` is new. It holds the vocabulary, the reader and the check, and imports
nothing else from the harness. It carries no instrument-name literal: the subject is the declaration's,
as a profile's criteria are the profile's.

A `Row` names four things: what is open, who closes it, the evidence that would close it, and whether
that evidence needs the submitted original. The loader refuses a missing field, an unknown kind, an
unknown state and an unknown source role, so a half-declaration cannot report a green check over half
a claim.

The register declares four more things the ledger's shared constraints require of a new artifact. Its
inputs are the eight bound records. Its `review_state` is `agent_drafted_pending_operator_review`. It
states its relationship to earlier versions, and it declares its own `declared_status` — **Inferred**,
not Confirmed. Each row's existence is read off a
committed record, which is evidence; that a row is still *open* is read off the absence of a closing
decision, and an absence is not a confirmation. The register's `uncertainties` travel in the record
too, not only in this report.

`tools/author_deferral_register.py` derives the register. Every group is read off a record rather than
typed:

| Group | Rows | Derived from |
|---|---|---|
| `ticket_criterion` | 1 | the unchecked R04 box in the predecessor ledger |
| `operator_decision_required` | 10 | `decision_state/rows_operator_decision_required` |
| `agent_recommendation` | 10 | `decision_state/rows_agent_recommended` |
| `qualified_interpretation` | 2 | `rows_operator_confirmed` ∩ `open_operator_decisions`, computed |
| `assessor_validation_case` | 2 | `assessor_validation_cases` |
| `unresolved_disposition` | 1 | every row whose `declared_status` is Unresolved, computed |
| `deferred_question` | 8 | the approval record's own table |

ESR-Q-01, ESR-Q-03 and ESR-E-04 are computed, not named in the tool. Each validation case's
`original_required` is read off its own recorded limit: AVC-02's limit names original-dependent
evidence, AVC-01's does not. Adding a row therefore means a record changed, and `--check` then reports
the register stale rather than letting the two drift apart.

Three decisions carry the work.

**A row marked closed with no evidence fails.** That is the register's reason to exist, and
`harness.deferral_register.check` also fails a closure with no date, and closure evidence filed
against a row still marked open. All three are ways a row could read as finished without being
finished.

**The register binds what it reads, under two roles.** `immutable_evidence` covers the approval
record, the dispositions, the revision plan, the evaluation summary and the three integrity audits.
Its bytes moving is an edit, reported as one. `tracked_input` covers the ticket ledger, where moved
bytes mean the register is stale. Both fail the check, as separate findings, because an edited
historical record and a stale register are different defects with different fixes. Every row cites
one of those eight records as `path#pointer`, and the pointer has to resolve: by field into a JSON
record, as text into any other. A reworded criterion fails rather than pointing nowhere.

**Statements are measured.** A `Statement` with no `Measurement` fails the check, and a measurement
the records contradict fails it too. That is V05's rule — the audit's grounding wording stopped coming
from a constant — applied here before the same defect could appear.

## 3. The two statements the ticket requires

**S1.** The 40 to 29 to 13 finding sequence is three readings of one unchanged candidate.

Nine measurements carry it: each audit's own `findings_total`, and each audit's `candidate_hash` and
`document_id` against the single value all three share. The tool refuses to render if the three stop
sharing a candidate. So the fall is changed interpretation and changed audit rules — D11 and R03
retired 27 findings as rules — and not 27 repaired proposal defects. No proposal text changed between
the three readings, and the identical candidate hash is what says so.

**S2.** All 15 evaluation-summary criticisms still have open revision work.

Three measurements: the approved revision plan's `open` has length 15, its `closed` has length 0, and
the evaluation summary records 29 observations. The tool additionally refuses to render if a revision
row has closed, or if the plan's open rows are not exactly the summary's eight shortcomings and seven
minor shortcomings. Retiring an audit finding retired an audit rule. It changed nothing an
evaluation-summary criticism names.

## 4. The overlap is shown, not hidden

32 of the 34 rows name 23 distinct observations between them. ESR-E-04 is open three times — as a
deferred disposition, as the one Unresolved status, and inside the approval table's first row.
ESR-Q-01 is open three times too. The rendered reading cross-references them:

| Observation | Rows |
|---|---|
| ESR-E-04 | ODR-ESR-E-04, UNR-ESR-E-04, DQ-01 |
| ESR-Q-01 | QI-ESR-Q-01, AVC-01, DQ-06 |

Without that table, 34 rows read as 34 independent items. The register says instead that closing one
row closes neither the other rows over its observation nor the observation itself.

The two rows naming no observation are the R04 ticket criterion and DQ-08, whose subject is
"M7.3 and appointments" — a milestone and a schedule question, not an observation. The normaliser
leaves it out rather than coercing it to an id.

## 5. The author does not judge its own output

The first implementation put the reader, the check and the rendering in the authoring tool. That
failed `tests/harness/test_boundary.py::TestOneWayDependency::test_tools_and_scripts_do_not_import_harness_into_runtime`:
`tools/` may not import `harness/`.

The fix moved the reader, the check and the rendering to the harness side. `tools/` writes the
register JSON and replays it byte-equal. `harness.commands.deferral_register` reads it and writes the
Markdown reading beside it. It is the command that can fail.

The split is right on its own terms. A tool that both wrote a record and certified it would be judging
its own output.

It costs one duplicated constant: the schema string exists as
`tools.author_deferral_register.SCHEMA` and as `harness.deferral_register.SCHEMA`. That is deliberate
double entry, and
`tests/test_msca_dn_deferral_register.py::TestTheRenderer::test_the_authoring_tool_and_the_reader_declare_one_schema`
asserts the two agree. The sha256 helper comes from `tools.fidelity_declarations`, the spelling the
tools that pin artifacts already share.

## 6. Tests

| Command | Result |
|---|---|
| `py -3.10 -m pytest tests/harness/test_deferral_register.py` | 59 passed |
| `py -3.10 -m pytest tests/test_msca_dn_deferral_register.py` | 35 passed |
| `py -3.10 -m pytest tests/harness/test_boundary.py` | 13 passed |
| `py -3.10 -m pytest tests/harness/test_acceptance_lane.py` | 68 passed |
| `py -3.10 -m pytest tests/harness/test_profile.py` | 23 passed, the agnosticism lint included |
| `py -3.10 -m tools.author_deferral_register --check` | up to date, exit 0 |
| `py -3.10 -m harness.commands.deferral_register --register …` | 34 open, 0 closed, check green, exit 0 |
| `py -3.10 -m tools.import_external_proposal --check` | up to date, exit 0 |
| `py -3.10 -m tools.author_msca_dn_workspace --check` | up to date, exit 0 |

### 6.1 The acceptance lane

The lane gains a `deferrals` area holding the two new modules, declared **not** depended on. V03's
first acceptance criterion names seven depended-on areas, and
`tests/harness/test_acceptance_lane.py::TestAreas::test_exactly_the_areas_v03_names_are_the_depended_on_ones`
asserts exactly those seven. The register gates the milestone's acceptance — V11 blocks V14 — not the
correctness of a Stage A reading, so an eighth depended-on area would amend an accepted measurement
for nothing.

**The lane was not run to completion on this machine, and no lane result is recorded here.** Four
attempts were killed by the host for low memory: three runs of
`py -3.10 -m harness.commands.acceptance_lane`, at three different points, and one attempt that ran the
same 66 modules as eight smaller processes. The host reported 377 MB free of 15.7 GB while all 365
processes together held 4 GB, so the shortfall was not this work's to reclaim. An earlier run on this
branch, before the code-review fixes, did complete in 685 s — the obstruction is the machine's state,
not the lane.

What was measured instead, and what each measurement is worth:

| Check | Result | What it does not cover |
|---|---|---|
| `py -3.10 -m harness.commands.acceptance_lane --list` | exit 0 | runs no test; it proves the declaration loads, every declared module is in the tree, no module belongs to two areas, and every exclusion sits in an area the run does not depend on |
| `tests/harness/test_acceptance_lane.py` | 68 passed | the declaration's own invariants, including that the new area's modules are assigned and that the lane document carries its invariant verbatim |
| the five module runs in the table above | all passed | each module in its own process, so no cross-module interaction |

So the declaration is reconciled and every module touched by this change passes, but **the lane's own
single-process result is unmeasured and the `lane` block of the decision record is declared
`Unresolved`**. The operator's `py -3.10 -m harness.commands.acceptance_lane` is what closes it. No
figure for passed, failed, errors, skipped or collected is stated anywhere in this change, because
none was measured after the final fix.

## 7. Declared deviations

None is in V11's five acceptance criteria.

**The register is JSON and the reading is rendered.** The ticket says "one register". It is one
record — the JSON — with a Markdown reading rendered from it by a second command. The reading carries
no fact the JSON does not, and `--check` proves it reproduces.

**The schema string exists twice.** Forced by the one-way import boundary, guarded by an equality
assertion. Section 5.

**Thirteen findings where the ticket asked for one.** The ticket asks that a closed row with no
evidence fail. `RegisterCheck` carries thirteen categories. The full set, and why each is there:

| Finding | Why it is in the check |
|---|---|
| `closed_without_evidence` | the asked rule |
| `closed_without_date` | a closure that cannot be placed against its records |
| `open_rows_carrying_closure` | evidence filed on an open row: a closure nobody checked, or the wrong row |
| `rows_missing_field` | criterion 2: an empty owner or closure evidence is an item nobody can finish |
| `duplicate_row_ids` | two rows under one id hide one of them |
| `rows_citing_undeclared_source` | criterion 4: a row pointing at a record the register has not bound |
| `rows_whose_pointer_does_not_resolve` | the same row pointing nowhere inside a bound record |
| `measurements_citing_undeclared_source` | criterion 5, the same rule for a measurement |
| `missing_sources` | a bound record absent from the tree |
| `edited_immutable_sources` | criterion 4: the approval record or dispositions edited |
| `stale_tracked_inputs` | the register out of date against the ledger it reads |
| `statements_without_measurement` | criterion 5: a claim with nothing measuring it |
| `failed_measurements` | criterion 5: a claim the records contradict |

Nine of the thirteen serve criteria 2, 4 and 5 rather than exceeding them. The four that genuinely go
beyond the ticket are `closed_without_date`, `open_rows_carrying_closure`,
`rows_whose_pointer_does_not_resolve` and `duplicate_row_ids`. Each is a way the register could read as
honest while having stopped being so. None weakens the asked rule.

**`stale_tracked_inputs` has a cost the ticket did not ask for.** Binding
`plans/pe08_review_and_pe09_handoff_tickets.md` means any edit to that ledger — including one nothing
to do with R04 — turns the `deferrals` lane area red until the register is re-derived. The alternative
was the R04 row pointing at a record nothing pins. Section 9 carries the same note, and so does the
register's own `uncertainties`.

**The lane gained an area.** Two new test modules fall inside the audit's focused globs, so the lane
refused to run until they belonged to one. Section 6.1.

## 8. What this is not evidence of

- **A closed deferral.** All 34 rows are open. The register closes none, and no agent-authored record
  may close one.
- **Operator approval of anything.** The register is a successor artifact that transcribes and points.
  The approval of 2026-10-08 stands as written and was not edited: it still carries the sha256 the
  approved dispositions pinned on 2026-10-08, and a test asserts it.
- **A resolved ESR-E-04, ESR-Q-01 or ESR-Q-03.** Their rows record what is open about them.
- **27 repaired proposal defects.** S1 exists to stop that reading.
- **A closed gate G7.** V11 is only a prerequisite; G7 follows G6, which needs the operator's V14.
- **A new assessor run.** No quota was spent and no assessor was called.

## 9. Remaining uncertainties

**The ledger is a tracked input and will move.** `plans/pe08_review_and_pe09_handoff_tickets.md` is
bound because the R04 row points into it. Any edit to that file — including one unrelated to R04 —
makes the register stale and the check fail until it is re-derived. That is the intended cost; the
alternative was a row pointing at a record nothing pins.

**The R04 row closes on a decision this repository cannot make.** Its closure needs adoption into an
active register once D13's deferral lifts. The tool refuses to re-derive the row as open once the
ledger checks the box, so a human has to supply the closure evidence rather than letting the row
vanish.

**No row has ever been closed.** The closure path — `closed_by` plus `closed_on`, checked — is covered
by synthetic cases only. No committed row exercises it, because closing one needs evidence this
repository does not hold.

## 10. Artifacts

| Path | What it is |
|---|---|
| `harness/deferral_register.py` | the vocabulary, the reader, the check and the rendering |
| `harness/commands/deferral_register.py` | the command that checks a register and writes its reading |
| `tools/author_deferral_register.py` | the deterministic deriver, with a byte-equal replay |
| `docs/…/msca_dn/deferrals/open_deferral_register_2026-10-12.json` | the register |
| `docs/…/msca_dn/deferrals/open_deferral_register_2026-10-12.md` | its reading |
| `docs/…/decision_log/msca-dn-open-deferrals_2026-10-12.json` | the decision record |
| `tests/harness/test_deferral_register.py` | 59 checks on the reader, the check and the command |
| `tests/test_msca_dn_deferral_register.py` | 35 checks reconciling the committed register |
