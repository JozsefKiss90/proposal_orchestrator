# G4 acceptance and the V05 criterion 4 amendment — completion report

Date: 2026-10-12.
Branch: `msca-dn-pre-eval`, from `aa0d464`.
Scope: the operator's acceptance of V04, V05 and V06 of
`plans/msca_dn_historical_validation_tickets.md`, the amendment of V05 criterion 4, and the closure of
gate G4 for infrastructure readiness.
Acceptance record: `docs/tier4_orchestration_state/msca_dn/reviews/operator_acceptance_g4_2026-10-12.md`.
Decision record: `docs/tier4_orchestration_state/decision_log/msca-dn-g4-acceptance_2026-10-12.json`.

The operator instructed this work in session on 2026-10-12. No code moved. No committed artifact was
edited. No assessor ran and no quota was spent. The amendment changes what V05 criterion 4 asks, not
what V05 built.

Environment: Python 3.10.6, the pin V01 established
(`docs/tier4_orchestration_state/decision_log/msca-dn-extraction-environment-pin_2026-10-08.json`).

## 1. What the amendment changes

V05 criterion 4 required both committed sanitised integrity audits to reproduce byte-equal. V05 left it
open and said why: `integrity_13ad3ad81d7e_0001.json` predates operator decision D11 and ticket R03,
which retired twenty-seven of its findings. The current checks cannot emit the payload that file
carries, and V05 is not what changed them. Closing the box needed a successor audit over that
candidate, or an amendment.

The operator chose the amendment. Four conditions replace whole-file reproduction:

1. Historical audit artifacts remain byte-unchanged and hash-verifiable.
2. Grounding and identity outputs reproduce for both sanitised revisions.
3. The current revision's complete check payload reproduces.
4. The older revision's differences match exactly the twenty-seven findings retired by D11 and R03.

Each condition states something the derivation guarantees. Condition 4 is the one that carries the
divergence: it holds the older copy's difference to an enumerated set rather than to zero.

## 2. What the amendment does not say

The older revision's audit does not reproduce in full under the current rules. The amended criterion
says so in its own box, the acceptance record says so, and the decision record says so. A successor
audit over `MSCA-DN-2025_sanitised_part_b@bdb8670f6987e4db` stays unwritten and stays the operator's to
commission.

The original wording is quoted in the criterion, with its prior annotation "Open, and not V05's to
close" and the reason it could not hold. Amending a criterion does not overwrite its history.

## 3. Verification of the four conditions

`tests/harness/test_integrity_audit.py::TestTheCommittedAudits` — eight cases, all passing. Each
condition is measured against the committed files, not asserted.

| Condition | Check | Result |
|---|---|---|
| 1 | `test_the_committed_bytes_are_untouched`, both audits | Each file verifies against its recorded sha256 |
| 2 | `test_the_grounding_axis_reproduces_byte_equal`, both audits | Byte-equal; the reason is derived from each candidate's own provenance |
| 2 | `test_every_identity_finding_reproduces_byte_equal`, both audits | Byte-equal; nine findings each |
| 3 | `test_the_current_revisions_whole_check_payload_reproduces_byte_equal` | Byte-equal; five checks, 13 findings for 13 |
| 4 | `test_the_first_copys_payload_differs_only_by_the_retired_rules` | The difference is exactly the twenty-seven retired findings, and nothing is new |

The twenty-seven, by rule:

| Rule | Retired by | Count | Now |
|---|---|---|---|
| `undeclared_dependency` on a milestone naming no deliverable | D11 | 16 | An inventory entry in the check's context |
| `out_of_window` on an appointment period against a package window | R03 | 9 | A check note |
| `inconsistency` on the whole-cohort package sets WP6 and WP7 | R03 | 2 | Compared in one direction |

Regenerating the older candidate's audit yields 15 findings where the committed file carries 42. 42
less 27 is 15, one for one.

| Audit | sha256 | Committed findings | Regenerated |
|---|---|---|---|
| `integrity_242f1afb02c8_0003.json` | `a295e66f…99a9` | 13 | 13, byte-equal |
| `integrity_13ad3ad81d7e_0001.json` | `1b66a7cc…ff13` | 42 | 15, differing by the enumerated 27 |

Byte-equality here is of the derivation-dependent payload, not of a whole persisted file. A persisted
report carries its own `audited_at` timestamp and the absolute path of the machine that wrote it.
Neither is a derivation output. V05's report section 5 states the same limit.

## 4. The G4 closure, and what it leaves open

G4 is closed for infrastructure readiness over V04 (`82fa9b4`), V05 (`437ca89`) and V06 (`aa0d464`).
F03, F06 and the required half of F07 close with their tickets.

G4's documentation share is not closed. The gate as the readiness audit wrote it also names a corrected
runbook, which is V12. V12's substantive corrections stay open, F04 and F12 stay open, and V12 remains
blocked by V07 and V10. "Closed for infrastructure readiness" is therefore the honest reading, and both
the ledger and the acceptance record carry it in those words.

Three limits are retained by instruction:

- The legacy 74.60 baseline keeps its undeclared grounding scope and its not-applicable
  `grounding_scope` freeze outcome, with the reason V06 declared. It is not a defect to repair.
- X01 stays mandatory for any source-grounded assessment. A `source_grounded` declaration stays refused
  at V06 and V15 until X01 is implemented and validated.
- V12's substantive runbook corrections stay open.

The acceptance authorises nothing further. The readiness audit's NO-GO on running and freezing the
official assessment stands, the official 2025 baseline is not validated, no fidelity declaration is
adopted, and no proposal change is approved.

## 5. The retired guard

`tests/harness/test_acceptance_lane.py::TestTheDependencyGate::test_a_criterion_conceding_partial_reproduction_is_never_checked`
held that V05's reproduction box must stay unchecked while it explains what does not reproduce. V05's
report section 5 cites it. That guard was correct for the criterion as written and its premise is
retired by the amendment, so it is replaced rather than deleted:

| New check | What it holds |
|---|---|
| `test_the_reproduction_criterion_is_checked_only_as_amended` | The box is checked only while it names the amendment, all four conditions and its evidence |
| `test_the_amendment_keeps_the_original_wording_and_its_history` | The superseded wording and the prior annotation stay readable |
| `test_the_amendment_never_claims_the_older_audit_fully_reproduces` | The ledger states that the older audit does not reproduce in full, and that the successor audit is unwritten |

`TestTheG4Acceptance` adds seven checks over the acceptance itself, eleven cases with their
parametrisation: the authority and the scope wording,
each accepted ticket's commit and completion record, the three acceptance artifacts committed where the
ledger cites them, the decision record's amendment and limit fields, the three retained limits, V12's
own open statement, and that no other gate moved.

V05's report is left as written. It is the record of the implementation, and its section 5 citation is
superseded by this report rather than corrected in place.

## 6. Files

| File | Change |
|---|---|
| `plans/msca_dn_historical_validation_tickets.md` | V05 criterion 4 amended, checked and dated, original wording kept; V05's status split into the as-implemented and post-amendment readings; a G4 acceptance section; pointers from V04, V06 and V12 |
| `docs/tier4_orchestration_state/msca_dn/reviews/operator_acceptance_g4_2026-10-12.md` | New: the acceptance record |
| `docs/tier4_orchestration_state/decision_log/msca-dn-g4-acceptance_2026-10-12.json` | New: the decision record |
| `tests/harness/test_acceptance_lane.py` | The retired guard replaced; `TestTheG4Acceptance` added |
| `plans/reports/g4_acceptance_and_v05_criterion4_amendment_2026-10-12.md` | New: this report |

No file under `docs/tier4_orchestration_state/msca_dn/audit/`, `…/baselines/`, `…/esr/`,
`…/comparisons/`, or any register, PDF, page source or import manifest was touched.

## 7. Tests

| Command | Result |
|---|---|
| `py -3.10 -m pytest tests/harness/test_integrity_audit.py::TestTheCommittedAudits` | 8 passed |
| `py -3.10 -m pytest tests/harness/test_acceptance_lane.py` | 68 passed |
| `py -3.10 -m pytest tests/harness/test_integrity_audit.py` | 126 passed |
| `py -3.10 -m pytest tests/harness/test_blind_baseline.py` | 88 passed |
| `py -3.10 -m tools.draft_fidelity_declarations --check` | up to date, before and after |
| `py -3.10 -m pytest tests/runner/test_leakage_scan.py` | 47 passed; no new identity noun in the new Tier 4 artifact |
| `py -3.10 -m harness.commands.acceptance_lane` | 2,320 passed, 1 failed, 17 declared exclusions — see below |

**The lane was not re-measured green after this report was written, and this report does not claim it
was.** The lane ran once during this work, before the report file existed, and reported one failure:
`TestTheG4Acceptance::test_the_acceptance_evidence_is_committed_where_the_ledger_cites_it` on the
missing `plans/reports/g4_acceptance_and_v05_criterion4_amendment_2026-10-12.md`. Writing this file is
what that check asks for, and the module carrying it now passes 68 of 68 on its own. Two full-lane
reruns after the file was written were killed by host memory pressure before collection finished, so no
post-fix whole-lane figure was measured. The rerun is the operator's command, as V03 recorded.

The measured figures stand against the audit's own baseline at `ca0a443`: 1,864 passed, 44 failed, 48
errors. The 17 skips are the lane's declared exclusions, documented in `harness/DATASET_DISPOSITIONS.md`
and recorded as exclusions rather than passes.

## 8. What this does not say

- It does not say the older sanitised audit reproduces. It says its differences are enumerated.
- It does not say G4's documentation share is done. V12 owns it and V12 is open.
- It does not say the 74.60 baseline was assessed for grounding. Its grounding stays unassessable and
  undeclared, by retention.
- It does not authorise V14 or V15. Both stay the operator's decisions.
