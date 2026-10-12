# Open-deferral register — MSCA-DN-2025_sanitised_part_b@b51a103520b58ded, under the operator approval of 2026-10-08

Authored 2026-10-12. Register `open_deferrals_2026-10-12`,
schema `deferral_register/1`, written by `tools/author_deferral_register.py`.

Review state: **agent drafted pending operator review**.
The register's own reading of its records is declared **Inferred**.
Relationship to earlier versions: nothing. This is the first register of the deferrals of the operator approval of 2026-10-08. The records it binds are its predecessors in evidence, not in version: the approved dispositions supersede the R05 record, and this register reads the approved one. A correction to this register is a successor register, never an edit.

34 items are open and none is closed. 22 of the open ones need the submitted original, which this
repository does not hold. They are not 34 independent items: 32 rows name 23 distinct observations
between them, and the other 2 name none. Closing one row closes neither the other rows over its
observation nor the observation itself. Every row is derived from a record bound below by sha256.
A row marked closed without closure evidence fails `harness.deferral_register.check`.

## What is open

| Kind | Open | Needs the original |
|---|---|---|
| ticket criterion | 1 | 0 |
| operator decision required | 10 | 10 |
| agent recommendation | 10 | 0 |
| qualified interpretation | 2 | 2 |
| assessor validation case | 2 | 1 |
| unresolved disposition | 1 | 1 |
| deferred question | 8 | 8 |
| **total** | **34** | **22** |

## What the numbers do not say

**S1.** The integrity audit's recorded 40 to 29 to 13 finding sequence is three readings of one unchanged candidate. All three carry the same candidate hash and the same document id, so the fall reflects changed interpretation and changed audit rules — operator decision D11 and ticket R03 retired 27 findings as rules, not as repairs. It is not 27 repaired proposal defects, and no proposal text changed between the three readings.

| Measurement | Record | Field |
|---|---|---|
| the reading before R03 records 40 findings | `integrity_242f1afb02c8_0001.json` | `findings_total` |
| the reading after R03 records 29 findings | `integrity_242f1afb02c8_0002.json` | `findings_total` |
| the approved reading records 13 findings | `integrity_242f1afb02c8_0003.json` | `findings_total` |
| the reading before R03 is of the same candidate bytes | `integrity_242f1afb02c8_0001.json` | `candidate_hash` |
| the reading before R03 is of the same document | `integrity_242f1afb02c8_0001.json` | `document_id` |
| the reading after R03 is of the same candidate bytes | `integrity_242f1afb02c8_0002.json` | `candidate_hash` |
| the reading after R03 is of the same document | `integrity_242f1afb02c8_0002.json` | `document_id` |
| the approved reading is of the same candidate bytes | `integrity_242f1afb02c8_0003.json` | `candidate_hash` |
| the approved reading is of the same document | `integrity_242f1afb02c8_0003.json` | `document_id` |

**S2.** All 15 evaluation-summary criticisms still have open revision work — the record's 8 shortcomings and 7 minor shortcomings. The approved revision plan carries every one of them as open and closes none. Retiring an audit finding retired an audit rule, and changed nothing an evaluation-summary criticism names.

| Measurement | Record | Field |
|---|---|---|
| 15 criticisms carry open revision work | `revisions_f60ae6e0a2a1_0003.json` | `open` |
| the evaluation summary records 29 observations, of which these 15 are the criticisms | `msca-dn-2025-esr.json` | `observations` |
| none is closed | `revisions_f60ae6e0a2a1_0003.json` | `closed` |

## The rows

### Ticket criterion (1)

#### TC-R04-05

R04 acceptance criterion 5 is unchecked: Draft declarations survive the supported generation workflow after adoption. (open: the R01 retention tests and the R04 temporary-checkout exercise show the workflow survives a drafted declaration, but adoption into an active register is deferred by D13, so the criterion's own precondition is unmet and the box stays unchecked)

- Precondition: D13 defers adoption of the R04 declaration drafts into an active register, so the criterion's precondition is unmet. The box is not checkable and not failing.
- Owner: the operator
- Closes on: Adoption of a declaration into an active register, once D13's deferral lifts, followed by a regeneration exercise over the adopted register with the new register hash and the affected bindings recorded. Adopting an original-fidelity claim additionally needs the original; adopting an extraction-fidelity claim does not, which is why this row does not require it.
- Needs the original: no
- State: open
- Source: `plans/pe08_review_and_pe09_handoff_tickets.md#Draft declarations survive the supported generation workflow after adoption.`

### Operator decision required (10)

#### ODR-ESR-E-02

ESR-E-02 (shortcoming) is declared not_detected_despite_sufficient_preserved_evidence with status Inferred. The approval deferred the row to the private network, so its disposition is not settled.

- Owner: the private operator
- Closes on: Original security, hospital/operator diversity and entrepreneurship mechanisms; compare relevant passages with sanitised text. The approval's disposition stands until then: Preservation is unconfirmed. Withdraw E-04's cohort-size citation now; do not settle miss versus not-assessable from an absence in this copy.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#open_operator_decisions/#0`

#### ODR-ESR-E-04

ESR-E-04 (shortcoming) is declared not_detected_despite_sufficient_preserved_evidence with status Unresolved. The approval deferred the row to the private network, so its disposition is not settled.

- Owner: the private operator
- Closes on: Original security, hospital/operator diversity and entrepreneurship mechanisms; compare relevant passages with sanitised text. The approval's disposition stands until then: Preservation is unconfirmed. Withdraw E-04's cohort-size citation now; do not settle miss versus not-assessable from an absence in this copy.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#open_operator_decisions/#1`

#### ODR-ESR-E-05

ESR-E-05 (shortcoming) is declared not_assessable_from_this_copy with status Assumed. The approval deferred the row to the private network, so its disposition is not settled.

- Owner: the private operator
- Closes on: Original registry/database and contributing-clinician passages. The approval's disposition stands until then: Keep not-assessable pending evidence.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#open_operator_decisions/#3`

#### ODR-ESR-E-08

ESR-E-08 (minor_shortcoming) is declared not_detected_despite_sufficient_preserved_evidence with status Inferred. The approval deferred the row to the private network, so its disposition is not settled.

- Owner: the private operator
- Closes on: Original security, hospital/operator diversity and entrepreneurship mechanisms; compare relevant passages with sanitised text. The approval's disposition stands until then: Preservation is unconfirmed. Withdraw E-04's cohort-size citation now; do not settle miss versus not-assessable from an absence in this copy.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#open_operator_decisions/#2`

#### ODR-ESR-E-S03

ESR-E-S03 (strength) is declared partially_observable with status Inferred. The approval deferred the row to the private network, so its disposition is not settled.

- Owner: the private operator
- Closes on: Original repository/preprint commitments, supervisor mapping and track-record evidence. The approval's disposition stands until then: Do not adopt blind criticisms as established proposal weaknesses.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#open_operator_decisions/#4`

#### ODR-ESR-E-S05

ESR-E-S05 (strength) is declared partially_observable with status Inferred. The approval deferred the row to the private network, so its disposition is not settled.

- Owner: the private operator
- Closes on: Original repository/preprint commitments, supervisor mapping and track-record evidence. The approval's disposition stands until then: Do not adopt blind criticisms as established proposal weaknesses.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#open_operator_decisions/#5`

#### ODR-ESR-I-S01

ESR-I-S01 (strength) is declared independently_detected with status Inferred. The approval deferred the row to the private network, so its disposition is not settled.

- Owner: the private operator
- Closes on: Original secondment rows, host-sector classifications and the denominator for the 80% claim. The approval's disposition stands until then: Recompute privately before approving a correction. Identify the actual source subsection; do not guess one.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#open_operator_decisions/#6`

#### ODR-ESR-I-S04

ESR-I-S04 (strength) is declared partially_observable with status Inferred. The approval deferred the row to the private network, so its disposition is not settled.

- Owner: the private operator
- Closes on: Original target-group/indicator tables, figures and prose. The approval's disposition stands until then: Do not attribute the disagreement to sanitisation as a confirmed cause.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#open_operator_decisions/#7`

#### ODR-ESR-Q-S02

ESR-Q-S02 (strength) is declared partially_observable with status Inferred. The approval deferred the row to the private network, so its disposition is not settled.

- Owner: the private operator
- Closes on: Original capacity and hosting evidence. The approval's disposition stands until then: Correct identity references now; original-dependent adequacy remains unresolved.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#open_operator_decisions/#9`

#### ODR-ESR-Q-S03

ESR-Q-S03 (strength) is declared partially_observable with status Inferred. The approval deferred the row to the private network, so its disposition is not settled.

- Owner: the private operator
- Closes on: Original capacity and hosting evidence. The approval's disposition stands until then: Correct identity references now; original-dependent adequacy remains unresolved.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#open_operator_decisions/#10`

### Agent recommendation (10)

#### AGR-ESR-E-06

ESR-E-06 (minor_shortcoming) carries the agent's declaration independently_detected with status Inferred. The approval addressed no decision to it.

- Owner: the operator
- Closes on: An operator decision on this row, recorded in a successor review record. The approval states that the other agent-drafted observations are not blanket-confirmed by it, so silence is not confirmation.
- Needs the original: no
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#decision_state/rows_agent_recommended/#0`

#### AGR-ESR-E-S01

ESR-E-S01 (strength) carries the agent's declaration independently_detected with status Inferred. The approval addressed no decision to it.

- Owner: the operator
- Closes on: An operator decision on this row, recorded in a successor review record. The approval states that the other agent-drafted observations are not blanket-confirmed by it, so silence is not confirmation.
- Needs the original: no
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#decision_state/rows_agent_recommended/#1`

#### AGR-ESR-E-S02

ESR-E-S02 (strength) carries the agent's declaration independently_detected with status Inferred. The approval addressed no decision to it.

- Owner: the operator
- Closes on: An operator decision on this row, recorded in a successor review record. The approval states that the other agent-drafted observations are not blanket-confirmed by it, so silence is not confirmation.
- Needs the original: no
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#decision_state/rows_agent_recommended/#2`

#### AGR-ESR-E-S04

ESR-E-S04 (strength) carries the agent's declaration independently_detected with status Inferred. The approval addressed no decision to it.

- Owner: the operator
- Closes on: An operator decision on this row, recorded in a successor review record. The approval states that the other agent-drafted observations are not blanket-confirmed by it, so silence is not confirmation.
- Needs the original: no
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#decision_state/rows_agent_recommended/#3`

#### AGR-ESR-I-01

ESR-I-01 (minor_shortcoming) carries the agent's declaration independently_detected with status Inferred. The approval addressed no decision to it.

- Owner: the operator
- Closes on: An operator decision on this row, recorded in a successor review record. The approval states that the other agent-drafted observations are not blanket-confirmed by it, so silence is not confirmation.
- Needs the original: no
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#decision_state/rows_agent_recommended/#4`

#### AGR-ESR-I-02

ESR-I-02 (minor_shortcoming) carries the agent's declaration independently_detected with status Inferred. The approval addressed no decision to it.

- Owner: the operator
- Closes on: An operator decision on this row, recorded in a successor review record. The approval states that the other agent-drafted observations are not blanket-confirmed by it, so silence is not confirmation.
- Needs the original: no
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#decision_state/rows_agent_recommended/#5`

#### AGR-ESR-I-S03

ESR-I-S03 (strength) carries the agent's declaration independently_detected with status Inferred. The approval addressed no decision to it.

- Owner: the operator
- Closes on: An operator decision on this row, recorded in a successor review record. The approval states that the other agent-drafted observations are not blanket-confirmed by it, so silence is not confirmation.
- Needs the original: no
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#decision_state/rows_agent_recommended/#6`

#### AGR-ESR-Q-04

ESR-Q-04 (minor_shortcoming) carries the agent's declaration independently_detected with status Inferred. The approval addressed no decision to it.

- Owner: the operator
- Closes on: An operator decision on this row, recorded in a successor review record. The approval states that the other agent-drafted observations are not blanket-confirmed by it, so silence is not confirmation.
- Needs the original: no
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#decision_state/rows_agent_recommended/#7`

#### AGR-ESR-Q-S01

ESR-Q-S01 (strength) carries the agent's declaration independently_detected with status Inferred. The approval addressed no decision to it.

- Owner: the operator
- Closes on: An operator decision on this row, recorded in a successor review record. The approval states that the other agent-drafted observations are not blanket-confirmed by it, so silence is not confirmation.
- Needs the original: no
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#decision_state/rows_agent_recommended/#8`

#### AGR-ESR-Q-S04

ESR-Q-S04 (strength) carries the agent's declaration independently_detected with status Inferred. The approval addressed no decision to it.

- Owner: the operator
- Closes on: An operator decision on this row, recorded in a successor review record. The approval states that the other agent-drafted observations are not blanket-confirmed by it, so silence is not confirmation.
- Needs the original: no
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#decision_state/rows_agent_recommended/#9`

### Qualified interpretation (2)

#### QI-ESR-Q-01

ESR-Q-01 (shortcoming) is confirmed on its disposition by D04, and an original-dependent question stays open. The settled disposition does not settle the interpretation.

- Owner: the private operator
- Closes on: Original dependencies, Gantt and sequencing evidence. The approval's disposition stands until then: Keep partial classification qualified; absence of embedded images alone does not establish that every figure was lost.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#open_operator_decisions/#8`

#### QI-ESR-Q-03

ESR-Q-03 (shortcoming) is confirmed on its disposition by D06, D12, and an original-dependent question stays open. The settled disposition does not settle the interpretation.

- Owner: the private operator
- Closes on: Actual project duration, WP scope, funding/activity windows and follow-up intent. The approval's disposition stands until then: No date or participation changes approved.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#open_operator_decisions/#11`

### Assessor validation case (2)

#### AVC-01

AVC-01 is kept for the next assessor run, not acted on. One implementation sample stated that no intermediate milestones are shown. The input that assessor received carries the milestones table with a due month for each of sixteen milestones over ten distinct months. The citation is withdrawn from both rows and kept as a case for the PE-09 assessor validation.

- Owner: the private operator
- Closes on: The case re-read against a new assessor reading, with the recorded limit carried: Never edit proposal milestones to satisfy the false absence claim.
- Needs the original: no
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#assessor_validation_cases/#0`

#### AVC-02

AVC-02 is kept for the next assessor run, not acted on. Four of five implementation samples attribute verification means to the deliverables and milestones tables jointly, while only the milestones table carries that column. The lane credited one table with the other's property.

- Owner: the private operator
- Closes on: The case re-read against a new assessor reading, with the recorded limit carried: A missing validation column does not prove inadequate deliverable validation. Review relevant prose and original-dependent evidence before finalising the proposal judgment.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#assessor_validation_cases/#1`

### Unresolved disposition (1)

#### UNR-ESR-E-04

ESR-E-04 (shortcoming) is declared Unresolved. Its row states the readings that remain open and the operator has chosen none, so none may be carried forward as the disposition.

- Owner: the private operator
- Closes on: The operator's choice between the readings the row records, plus Original security, hospital/operator diversity and entrepreneurship mechanisms; compare relevant passages with sanitised text. The approval's disposition stands until then: Preservation is unconfirmed. Withdraw E-04's cohort-size citation now; do not settle miss versus not-assessable from an absence in this copy.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json#rows/#5`

### Deferred question (8)

#### DQ-01

The approval explicitly defers the original-dependent decision on E-02, E-04, E-08. Its current review disposition is: Preservation is unconfirmed. Withdraw E-04's cohort-size citation now; do not settle miss versus not-assessable from an absence in this copy.

- Owner: the private operator
- Closes on: Original security, hospital/operator diversity and entrepreneurship mechanisms; compare relevant passages with sanitised text.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/reviews/operator_approval_2026-10-08.md#E-02, E-04, E-08`

#### DQ-02

The approval explicitly defers the original-dependent decision on E-05. Its current review disposition is: Keep not-assessable pending evidence.

- Owner: the private operator
- Closes on: Original registry/database and contributing-clinician passages.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/reviews/operator_approval_2026-10-08.md#E-05`

#### DQ-03

The approval explicitly defers the original-dependent decision on E-S03, E-S05. Its current review disposition is: Do not adopt blind criticisms as established proposal weaknesses.

- Owner: the private operator
- Closes on: Original repository/preprint commitments, supervisor mapping and track-record evidence.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/reviews/operator_approval_2026-10-08.md#E-S03, E-S05`

#### DQ-04

The approval explicitly defers the original-dependent decision on I-S01. Its current review disposition is: Recompute privately before approving a correction. Identify the actual source subsection; do not guess one.

- Owner: the private operator
- Closes on: Original secondment rows, host-sector classifications and the denominator for the 80% claim.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/reviews/operator_approval_2026-10-08.md#I-S01`

#### DQ-05

The approval explicitly defers the original-dependent decision on I-S04. Its current review disposition is: Do not attribute the disagreement to sanitisation as a confirmed cause.

- Owner: the private operator
- Closes on: Original target-group/indicator tables, figures and prose.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/reviews/operator_approval_2026-10-08.md#I-S04`

#### DQ-06

The approval explicitly defers the original-dependent decision on Q-01. Its current review disposition is: Keep partial classification qualified; absence of embedded images alone does not establish that every figure was lost.

- Owner: the private operator
- Closes on: Original dependencies, Gantt and sequencing evidence.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/reviews/operator_approval_2026-10-08.md#Q-01`

#### DQ-07

The approval explicitly defers the original-dependent decision on Q-S02, Q-S03. Its current review disposition is: Correct identity references now; original-dependent adequacy remains unresolved.

- Owner: the private operator
- Closes on: Original capacity and hosting evidence.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/reviews/operator_approval_2026-10-08.md#Q-S02, Q-S03`

#### DQ-08

The approval explicitly defers the original-dependent decision on M7.3 and appointments. Its current review disposition is: No date or participation changes approved.

- Owner: the private operator
- Closes on: Actual project duration, WP scope, funding/activity windows and follow-up intent.
- Needs the original: yes
- State: open
- Source: `docs/tier4_orchestration_state/msca_dn/reviews/operator_approval_2026-10-08.md#M7.3 and appointments`

## Rows that name the same observation

Several rows over one observation is the normal case. One row can defer a question while another
carries an unresolved status over the same observation. The rows are not independent items, and
closing one closes neither the other nor the observation.

| Observation | Rows |
|---|---|
| ESR-E-02 | ODR-ESR-E-02, DQ-01 |
| ESR-E-04 | ODR-ESR-E-04, UNR-ESR-E-04, DQ-01 |
| ESR-E-05 | ODR-ESR-E-05, DQ-02 |
| ESR-E-08 | ODR-ESR-E-08, DQ-01 |
| ESR-E-S03 | ODR-ESR-E-S03, DQ-03 |
| ESR-E-S05 | ODR-ESR-E-S05, DQ-03 |
| ESR-I-S01 | ODR-ESR-I-S01, DQ-04 |
| ESR-I-S04 | ODR-ESR-I-S04, DQ-05 |
| ESR-Q-01 | QI-ESR-Q-01, AVC-01, DQ-06 |
| ESR-Q-03 | QI-ESR-Q-03, AVC-01 |
| ESR-Q-S02 | ODR-ESR-Q-S02, DQ-07 |
| ESR-Q-S03 | ODR-ESR-Q-S03, DQ-07 |

## What the author of this register is unsure of

- The ticket ledger is bound as a tracked input, so any edit to it - including one unrelated to the R04 criterion - makes this register stale until it is re-derived.
- The R04 row closes on adoption into an active register once D13's deferral lifts, which is a decision this repository cannot make.
- No row has ever been closed, so the closure path is covered by synthetic cases only.
- Several rows name one observation on purpose. ESR-E-04 carries three and ESR-Q-01 three. The cross-reference is what keeps them from being counted as separate items.
- DQ-08's subject, the M7.3 milestone and the appointment windows, is not an evaluation summary observation, so it joins the ticket criterion as a row naming none.

## The records this register binds

| Record | Role | Holds |
|---|---|---|
| `docs/tier4_orchestration_state/msca_dn/reviews/operator_approval_2026-10-08.md` | immutable evidence | the operator approval of 2026-10-08, its fifteen decisions and its original-dependent deferred table |
| `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json` | immutable evidence | the approved dispositions: the review status of all 29 observations, the twelve deferred decisions, and the two assessor validation cases |
| `docs/tier4_orchestration_state/msca_dn/comparisons/revisions_f60ae6e0a2a1_0003.json` | immutable evidence | the approved revision plan, which carries the open revision work per criticism |
| `docs/tier4_orchestration_state/msca_dn/esr/msca-dn-2025-esr.json` | immutable evidence | the evaluation summary this comparison is against |
| `docs/tier4_orchestration_state/msca_dn/audit/integrity_242f1afb02c8_0001.json` | immutable evidence | the integrity audit as it stood before R03 |
| `docs/tier4_orchestration_state/msca_dn/audit/integrity_242f1afb02c8_0002.json` | immutable evidence | the integrity audit after R03's two rule corrections |
| `docs/tier4_orchestration_state/msca_dn/audit/integrity_242f1afb02c8_0003.json` | immutable evidence | the integrity audit the approved dispositions cite, after D11 retired the undeclared-dependency rule |
| `plans/pe08_review_and_pe09_handoff_tickets.md` | tracked input | the predecessor ticket ledger, which carries the unchecked R04 criterion |

An immutable record whose bytes move is an edit and fails the check. A tracked input is allowed to
move, and the register is then stale and has to be re-derived.
