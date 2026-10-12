# V06 completion report — the grounding scope is declared in preflight, report and freeze

Date: 2026-10-12.
Branch: `msca-dn-pre-eval`, from `82fa9b4`.
Ticket: V06 of `plans/msca_dn_historical_validation_tickets.md`.
Closes: the required half of finding F07 of `plans/reports/MSCA_DN_Readiness_Audit_2026-10-08.md`.
Decision record: `docs/tier4_orchestration_state/decision_log/msca-dn-grounding-scope_2026-10-12.json`.

Five of five acceptance criteria are closed. The required half of F07 closes. Its conditional half is
X01, which is not implemented, and every source-grounded declaration is refused until it is. No
assessor ran, no quota was spent, and the frozen 74.60 baseline still passes the gate.

Environment: Python 3.10.6, the pin V01 established
(`docs/tier4_orchestration_state/decision_log/msca-dn-extraction-environment-pin_2026-10-08.json`).

## 1. What was wrong

The blind lane runs `--no-claims`. The claim ledger is never opened, so no cell's grounding is judged.
Measured on the committed artifacts:

| Record | What it said about grounding |
|---|---|
| `blind_baseline_f60ae6e0a2a1.json` | `include_claims: false`, and ten cells each `grounding: unassessable` |
| `preflight_242f1afb02c8_0001.json` | `params.include_claims: false`, nothing else |
| `blind_baseline_f60ae6e0a2a1.freeze.json` | nothing |

The per-cell value was there. The run-level statement was not, in any of the three, and none of the
three rendered screens printed one. A reader saw ten graded cells, a total of 74.6 and no grounding
findings — which is what an assessed run with nothing to report also looks like.

That matters because four different claims are at stake. Proposal-internal coherence, scientific
plausibility, fidelity to the submitted text and independent factual support are not the same thing. A
source span inside a proposal establishes what was submitted. It does not prove a partner commitment,
an access entitlement or a scientific result.

## 2. What was built

`harness/grounding_scope.py` is new. It holds the vocabulary and the arithmetic, imports nothing from
the rest of the harness, and is read by the preflight, the report, the freeze and the command.

A grounding scope is two things recorded side by side.

**The declaration** is the operator's, and `--grounding-scope` is required on `preflight`, `assess` and
`salvage`. It takes the audit's two choices and no third:

| Choice | What it claims |
|---|---|
| `content_focused` | Proposal content and credibility were assessed. Grounding was unassessable, and a human reviews the sources. |
| `source_grounded` | The proposal has been source-grounded or factually verified. Refused — see section 4. |

**The measurement** is `unassessable`, `partly_assessed` or `assessed`, counted from the packs the
preflight realised or the cells the report graded. It cannot be overstated, because it is arithmetic
over records that already exist.

`GroundingScope.reason` is a property, not a stored sentence, so the wording cannot drift from the
numbers beside it. That is V05's rule — the audit's grounding wording stopped coming from a constant —
applied here before the same defect could appear.

Three decisions carry the work.

**One statement of the vocabulary.** `GROUNDING_IN_VERDICT` and `GROUNDING_UNASSESSABLE` moved out of
`harness/blind_assessment.py` into the new module and are re-exported from it. The cell value and the
run-level measurement are the same axis; two definitions of `unassessable` would be two things to keep
in step. No importer changed.

**The declaration is checked against the cells at construction.** `BlindAssessmentReport` re-measures
its own cells and refuses a scope whose counts or `include_claims` they contradict. A report declaring
one thing and grading another cannot be built, the way a cell carrying a foreign assessor pin cannot.

**The declaration is outside the pack-set hash, and still has to match.** Declaring a scope selects no
evidence, so it must not move the hash that binds what the assessor reads. A test asserts
`run_preflight` gives one `pack_set_hash` whether a scope is declared or not. The committed
preflight's `sha256:25d8aae9b31c...` is therefore unchanged, and the freeze's `preflight_rebound`
check still passes against it. `check_preflight` compares `grounding_scope.declared` as its own field
instead. The preflight is the record the operator reviewed before spending quota, and a run under
another declared scope is not the run they reviewed.

## 3. Where it is recorded, and how prominently

| Record | Key | Rendered |
|---|---|---|
| Preflight report | `grounding_scope` | the headline and its reason, after the pins |
| Blind report | `grounding_scope` | the same, **above the cell table** — a test asserts the order |
| Freeze record | `grounding_scope`, top level | the same, above the spread label |

All three print the same two lines through one function, `scope_lines`, and both lines are re-derived
from the record's counts rather than read from its file. So a stored sentence can never be printed
beside numbers it contradicts, and a recorded `measured` the counts do not give is refused rather than
shown. A `--no-claims` run reads

```
GROUNDING  [UNASSESSABLE]  declared scope: content_focused  (0 of 10 cell(s) carried a claim ledger)
           the claim ledger was withheld from every evidence pack, so no cell carries one and
           grounding could not be judged
```

A record carrying no block at all still gets a line, measured from its own graded units. The committed
report, the committed preflight and the committed freeze record — schema 1.0.0, written before the
block existed — all render one now, with `none declared` in place of a scope. An absent grounding line
is the defect this block exists to close, so the renderers never print nothing: a record whose numbers
cannot be measured prints `GROUNDING [NOT MEASURABLE]` and the reason.

`run_preflight` raises one flag, and so exit 1: the claim ledger was offered and no pack carried an
entry. A withheld ledger is the declared lane and raises nothing — flagging it would make every
intended run exit 1. Section 8 declares this flag as work the ticket did not ask for.

## 4. The source-grounded refusal

Criterion 5 asks for a refusal. It is one flag, read in four places.

`IMPORTED_CLAIM_ROUTE_IMPLEMENTED` is `False`. The refusal names the three integrations X01 owes:
imported-section claims loading with resolvable sources, supported claim statuses backed by evidence,
and E2 grounding running over that ledger.

| Where | What happens |
|---|---|
| The command | `check_declarable` at parse time, before the snapshot, the packs or the assessor exist. A test asserts the backend recorded zero calls. |
| `run_preflight` | `declare_scope` refuses; nothing is written. |
| `assess_candidate` | `declare_scope` refuses; no report is built. |
| The freeze | the `grounding_scope` check refuses by name, and the baseline directory is never created. |

A second rule outlives X01: `source_grounded` over a run whose grounding did not measure `assessed` is
refused on the measurement. With the flag patched on, a synthetic run with one ungrounded cell is still
refused and a fully grounded one is accepted. So the refusal is the capability, not a hardcoded no.

And derivation can never reach it. `measured_only` produces a measurement and leaves `declared` null;
`source_grounded` is a declaration and never a measurement.

## 5. The freeze binds it

The freeze is where a later stage would read "this run was source-grounded", so `BASELINE_CHECKS`
gained a 22nd name. `grounding_scope` re-derives the scope from the report's own cells and gives one of
four outcomes.

| Outcome | When |
|---|---|
| Refused | the recorded measurement is not what the cells' grounding values give, or `source_grounded` over a run that did not assess every cell |
| Refused | a `source_grounded` declaration while X01 is open |
| Refused | the report declares nothing **and** grounded at least one cell: there is a grounding result, so the baseline must say which scope produced it |
| Not applicable | the report declares nothing **and** its cells are unanimously unassessable |

The last row is the committed baseline. It predates the declaration, so there is nothing to check — and
the freeze records the measurement instead, which can only read `unassessable`. This is the third
outcome V04's `BaselineCheckRun` was built for: a check the report cannot answer is recorded with its
reason, never claimed as a pass. `checks_passed` stays derived.

`BASELINE_FREEZE_SCHEMA_VERSION` moves 1.1.0 → 1.2.0. The block is top level rather than inside
`bindings`, so the committed freeze's 25 bindings still reproduce exactly.

## 6. The control still freezes

`tests/harness/test_blind_baseline.py::TestTheCommittedMscaDnBaseline` runs the real `freeze_baseline`
over the committed report, with the real candidate and
`load_profile_bundle('harness/profiles/msca_dn_2026_default.json')`. Every case works on its own copy
under `tmp_path`.

- 21 of 22 checks passed, `grounding_scope` not applicable, 10 cells, 3 criterion scores, total 74.6.
- The freeze record reproduces the committed freeze's `report_sha256`, its `report_copy` name and every
  one of its 25 bindings; the copy is byte-identical to the committed report.
- Its `grounding_scope` block reads `declared: null`, `measured: unassessable`, 0 of 10, and the string
  `source_grounded` appears nowhere in it.
- Each of the readiness audit's four probes is still refused by name, plus three new ones: a planted
  `source_grounded` declaration, a declaration the cells contradict, and an undeclared report that
  grounded a cell.

Two V04 assertions were updated rather than satisfied, and both are honest widenings:

| Assertion | Before | Now |
|---|---|---|
| `checks_passed` on the control | every name in `BASELINE_CHECKS` | every name but `grounding_scope`, which is not applicable |
| a dropped or duplicated cell | one failure, `cell_identity` | two, `cell_identity` and `grounding_scope` |

The second is a strengthening. Deleting a cell also moves the recorded counts, so the grounding scope
is an independent second witness to a deleted record — which is the failure mode V04 existed to catch.

Nothing under `docs/` was written by any test. The committed baseline, its freeze record, its
preflight, both fidelity registers, the approval records and the committed audits are untouched.

## 7. Checks run

| Check | Result |
|---|---|
| `tests/harness/test_grounding_scope.py` | 41 passed |
| `tests/harness/test_blind_baseline.py` | 88 passed |
| `tests/harness/test_blind_assessment.py` | 39 passed |
| `tests/harness/test_evidence_preflight.py` | 44 passed |
| `tests/harness/` (whole directory) | 1,551 passed, 17 skipped — the 17 declared exclusions, unchanged |
| `tests/test_msca_dn_*.py`, `tests/runner/test_agnosticism_lint.py`, `tests/harness/test_boundary.py` | 286 passed |
| `tools.import_external_proposal --check`, `tools.author_msca_dn_workspace --check` | both `up to date`, exit 0 |
| `py -3.10 -m harness.commands.acceptance_lane` | GREEN, exit 0 — section 7.1 |

No new skip was introduced, so the lane's declared count of 17 still reconciles.

### 7.1 The acceptance lane

`py -3.10 -m harness.commands.acceptance_lane`, run after the last change in this ticket:

| | audit `ca0a443` | V04 at `82fa9b4` | this lane |
|---|---|---|---|
| passed | 1,864 | 2,244 | 2,308 |
| failed | 44 | 0 | 0 |
| errors | 48 | 0 | 0 |
| skipped (declared exclusions) | 8 | 17 | 17 |
| collected | 1,964 | 2,261 | 2,325 |

`GREEN: 2,308 passed, 0 failed, 0 errors, 17 declared exclusions`, exit 0. No new skip, so the
declaration's count of 17 still reconciles.

The lane's `freeze` area invariant gained this ticket's half:

> The baseline freeze binds what it froze and refuses what it must. The frozen 74.60 report still
> passes the gate it was frozen under. Every preflight, report and freeze declares its grounding
> scope beside the measurement of what the run could judge.

`tests/harness/test_grounding_scope.py` is declared in that area.

## 8. Changes the ticket did not ask for, declared

Four things in this diff are not in V06's five criteria. Each is named here rather than left to read as
required work.

| Change | Why it is here |
|---|---|
| `--grounding-scope` is **required**, not defaulted | A default would let the record say an operator declared `content_focused` when nobody chose it — the class of false provenance V04 and V05 closed. The cost is that nine test modules and two runbook command lines must name the flag. All were updated. |
| `plans/msca_dn_pe09_runbook.md` gains the flag on its two command lines | V12 owns the runbook and is blocked by this ticket. But a required flag is a break *this* ticket caused: an operator following those lines before V12 would hit a hard refusal. Repairing what this change broke is not V12's four substantive corrections, which are untouched — the fifteen-check claim, the planted-marker claim, historical defaulting and the cross-baseline `diff` all still stand uncorrected. |
| `GROUNDING_IN_VERDICT` and `GROUNDING_UNASSESSABLE` moved module | Criterion 2 needs the run-level and cell-level values to agree on the word `unassessable`. Two definitions in two modules would be two things to keep in step. They are re-exported from `blind_assessment`, so no importer changed. |
| The preflight flags an offered-but-empty ledger | The ticket asks for the declaration, not a flag. This one exists because a ledger the operator asked for that reached no pack is a surprise worth reading before quota — the run would grade addressal alone, and nothing else said so. A withheld ledger raises nothing. |
| The acceptance-record template carries the whole decision-text field set | Criterion 4 asks only for the scope statement, and no template existed. A template with one section would be filled in beside an ad-hoc record. It is marked "Not an approval", every value is a blank, and V15 owns filling and signing it. |

## 9. What this is not evidence of

- **Not a closed F07.** V06 closes the required half; the conditional half is X01, which is not
  implemented. Every `source_grounded` declaration is refused until it is.
- **Not grounded evaluation.** The declaration records that grounding was not judged. It does not judge
  it.
- **Not a closed gate G4 on its own.** G4's closure is the operator's call against the audit's evidence
  requirement, over V04, V05 and this ticket together.
- **Not a corrected runbook.** The two command lines this change would otherwise have broken now carry
  `--grounding-scope`, and nothing else in `plans/msca_dn_pe09_runbook.md` was touched. It still
  describes fifteen freeze checks, still claims the planted-marker test is one of them, still proposes
  historical defaulting, and still lists a cross-baseline `diff` guaranteed to refuse. All four are
  V12's.
- **Not an imported, assessed or frozen original.** V07 to V10 are open.
- **Not a new assessor run.** No quota was spent and no assessor was called.

## 10. Remaining uncertainties

- **The preflight counts packs; the report counts cells.** A pack the preflight could not build counts
  in its total and carries no ledger, while `assess` skips the missing section and grades no cell for
  it. On a partial candidate the two counts can differ. That is why `check_preflight` compares the
  declaration and not the counts, and why the unit travels inside each record.
- **A library caller may still declare nothing.** `assess_candidate` and `run_preflight` take
  `grounding_scope=None` and then record the measurement alone. The command always declares. Requiring
  it in the dataclass would have refused every report written before this ticket, the committed
  baseline included.
- **`partly_assessed` has no committed instance.** No real run has produced it, so it is covered by
  the synthetic world and by unit cases rather than by a committed artifact.
- **The four counts travel as four keyword arguments.** `include_claims`, `with_claims`, `total` and
  `unit` pass together through `measure`, `scope_for`, `declare_scope`, `measured_only` and
  `GroundingScope`. A `GroundingCounts` type would name the clump, but its only job would be to be
  unpacked into `GroundingScope`, which already holds the four fields. `scope_for` removes the
  duplication that mattered — the "declared, else measured" branch, which had been written out at all
  three producers.
- **The capability flag is a declaration, not a measurement.** `IMPORTED_CLAIM_ROUTE_IMPLEMENTED` is a
  constant. A test asserts it is `False` while X01 is open, but flipping it without building the route
  would be a false declaration that no check here could catch. X01 owns both halves.
- **The freeze's non-applicability is a judgement about derivability.** An undeclared report whose
  cells are unanimously unassessable is recorded not applicable rather than refused. The argument is
  that derivation can only produce the conservative value, so the record cannot overstate. An
  undeclared report that grounded a cell is refused, which closes the route by which omitting the
  declaration could dodge the check.
