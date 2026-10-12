# G4 operator acceptance — V04, V05 and V06, and the V05 criterion 4 amendment

Date: 2026-10-12  
Operator: József Kiss  
Repository: `JozsefKiss90/proposal_orchestrator`  
Branch: `msca-dn-pre-eval`  
Location: `docs/tier4_orchestration_state/msca_dn/reviews/operator_acceptance_g4_2026-10-12.md`

## Authority and scope

The operator accepted V04, V05 and V06 of `plans/msca_dn_historical_validation_tickets.md` in session
on 2026-10-12, and approved the amendment of V05 criterion 4 and the closure of gate G4 for
infrastructure readiness, subject to recording the supporting evidence. That instruction is the
authority for this record. It is an authority fact and it raises no evidence status.

The acceptance covers infrastructure readiness only. It does not authorise the private assessment, and
the readiness audit's NO-GO on running and freezing the official assessment stands. It does not
validate the official 2025 baseline. It adopts no fidelity declaration. It approves no proposal change.

## The three accepted tickets

| Ticket | Commit | Completion record | Decision record |
|---|---|---|---|
| V04 — the freeze refuses incomplete and inconsistent reports | `82fa9b4` | `plans/reports/v04_freeze_refuses_incomplete_reports_2026-10-12.md` | `docs/tier4_orchestration_state/decision_log/msca-dn-freeze-completeness_2026-10-12.json` |
| V05 — provenance-derived audit grounding and identity wording | `437ca89` | `plans/reports/v05_audit_grounding_provenance_2026-10-12.md` | `docs/tier4_orchestration_state/decision_log/msca-dn-audit-grounding-provenance_2026-10-12.json` |
| V06 — declared grounding scope in preflight, report and freeze | `aa0d464` | `plans/reports/v06_grounding_scope_declared_2026-10-12.md` | `docs/tier4_orchestration_state/decision_log/msca-dn-grounding-scope_2026-10-12.json` |

V04 closed seven of seven criteria, V06 five of five, and V05 five of six as implemented. The sixth is
the amended criterion below. F03, F06 and the required half of F07 close with their tickets.

Each report's verification is the evidence recorded at implementation time. The amendment's four
conditions were re-measured for this acceptance; see the verification section.

## The amendment to V05 criterion 4

The criterion required both committed sanitised integrity audits to reproduce byte-equal. The box stood
open, annotated "Open, and not V05's to close", because whole-file reproduction cannot hold for the
older copy: that audit predates operator decision D11 and ticket R03, which retired twenty-seven of its
findings. Closing it needed either a successor audit over that candidate or an amendment.

The operator chose the amendment. The criterion now requires four conditions:

1. Historical audit artifacts remain byte-unchanged and hash-verifiable.
2. Grounding and identity outputs reproduce for both sanitised revisions.
3. The current revision's complete check payload reproduces.
4. The older revision's differences match exactly the twenty-seven findings retired by D11 and R03.

The original wording and this amendment history are preserved in the criterion's own box in the ticket
ledger. V05's implementation did not change. What changed is what the criterion asks of it.

The older revision's audit still does not reproduce in full under the current rules. The amendment does
not say otherwise, and no record here may be read as saying otherwise. A successor audit over that
candidate stays unwritten and stays the operator's to commission.

## Verification of the four conditions

Measured on 2026-10-12 at the checkout of `aa0d464`, by
`tests/harness/test_integrity_audit.py::TestTheCommittedAudits` — eight cases, all passing.

| Condition | Check | Result |
|---|---|---|
| 1 — bytes unchanged | `test_the_committed_bytes_are_untouched`, both audits | Both files verify against their recorded sha256 |
| 2 — grounding reproduces | `test_the_grounding_axis_reproduces_byte_equal`, both audits | Byte-equal, reason "supporting sources removed by sanitisation" derived from each candidate's own provenance |
| 2 — identity reproduces | `test_every_identity_finding_reproduces_byte_equal`, both audits | Byte-equal, nine findings each |
| 3 — current payload | `test_the_current_revisions_whole_check_payload_reproduces_byte_equal` | Byte-equal, five checks and 13 findings for 13 |
| 4 — enumerated differences | `test_the_first_copys_payload_differs_only_by_the_retired_rules` | The difference is exactly the twenty-seven retired findings, and nothing is new |

The twenty-seven are sixteen `undeclared_dependency` milestones retired by D11, nine `out_of_window`
appointment findings retired by R03, and the two whole-cohort package sets WP6 and WP7, now compared in
one direction. Regenerating the older candidate's audit yields 15 findings where the committed file
carries 42.

| Audit | sha256 |
|---|---|
| `docs/tier4_orchestration_state/msca_dn/audit/integrity_242f1afb02c8_0003.json` | `a295e66fa39dce1857b4e03225de23775a087794dccb0b4407e5e03f9af799a9` |
| `docs/tier4_orchestration_state/msca_dn/audit/integrity_13ad3ad81d7e_0001.json` | `1b66a7cc0823b8e13692ec00aaebe632ad0c3bf775fe9d567c892c97864bff13` |

Byte-equality here is of the derivation-dependent payload, not of a whole persisted file. A persisted
report carries its own `audited_at` timestamp and the absolute path of the machine that wrote it, and
neither is a derivation output.

## Gate G4

**Closed for infrastructure readiness, 2026-10-12.** The code and artifact controls the gate names are
in place: the freeze refuses incomplete, duplicated, out-of-range and internally inconsistent reports;
the integrity audit states the true grounding reason for whichever candidate it reads; and every
preflight, report and freeze carries a declared grounding scope that the freeze binds.

G4's documentation share is not closed. V12's substantive runbook corrections stay open, and this
acceptance closes none of them.

## Retained limits

- **The legacy 74.60 baseline keeps its undeclared grounding scope.** Its `grounding_scope` freeze check
  stays recorded not applicable, with the reason V06 declared: the report predates the declaration, and
  derivation over its unanimously unassessable cells can only ever read `unassessable`. That outcome is
  retained deliberately. It is not a defect to repair, and the committed report is not re-declared.
- **X01 stays mandatory for any source-grounded assessment.** Until the imported-source grounding route
  is implemented and validated, a `source_grounded` declaration stays refused at V06 and V15.
- **V12's substantive runbook corrections stay open.** F04 and F12 are open, and V12 remains blocked by
  V07 and V10.
- **The 74.60 frozen total and the 85.80 historical total stay as recorded.** No assessor ran for this
  acceptance and no quota was spent.

## What was not done

- No assessor call, no new preflight, no new freeze, no new baseline.
- No committed audit, register, baseline, disposition, comparison or report was edited.
- No successor integrity audit was written over the older candidate.
- No runner phase was dispatched.
- No gate other than G4 moved.
