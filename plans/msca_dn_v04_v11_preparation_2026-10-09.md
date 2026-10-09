# Preparation for the five unblocked tickets

Date: 2026-10-09.
Branch: `msca-dn-pre-eval`.
Ledger: `plans/msca_dn_historical_validation_tickets.md`.
Written at the close of V03. This note prepares work; it executes none of it.

## What is unblocked, and what is not

V01 and V03 are closed, and V02a to V02d are closed or dispositioned. Five tickets are ready to start.

V03 did not unblock them. Four — V04, V05, V09 and V11 — are the ledger's own *"Seven tickets can
start immediately"*, minus V02c and V02d, which are done. V07 was unblocked by V01. The one ticket V03
appears in is V14's `Blocked by`, and V14 still waits on V05, V06, V11 and V13. What V03 closed is G1
and finding F08, which is why the five are now the frontier rather than newly admissible.

Reading the ledger's dependency table against the current state:

| Ticket | Gate | Blocked by | State |
|---|---|---|---|
| V04 — the freeze refuses incomplete reports | G4 | none | **Unblocked**, startable since the ledger was written |
| V05 — provenance-derived audit wording | G4 | none | **Unblocked**, and it now carries V02a's transferred criterion |
| V07 — externalise the document configuration | G2 | V01 ✔ | **Unblocked** |
| V09 — pin the 2025 authority documents | G3 | none | **Unblocked**, operator-supplied sources |
| V11 — open-deferral register | G7 prereq | none | **Unblocked** |
| V06 | G4 | V04 | Blocked |
| V08 | G2 | V07 | Blocked |
| V10 | G3 | V09 | Blocked |
| V12 | G2, G4, G5 | V04, V06, V07, V10 | Blocked |
| V13 | G5 | V08, V10, V12 | Blocked |
| V14 | G6 | V03 ✔, V05, V06, V11, V13 | Blocked |
| V15 | G7 | V14 | Blocked |

Five tickets are ready. Two of the five need something an agent cannot supply.

## Suggested order, and why

**V05 first.** It is the only unblocked ticket another closed ticket is waiting on. V02a's second
criterion sits in V05's list, so V05 closes two boxes rather than one. It is also the narrowest: one
module, `harness/integrity_audit.py`, and two committed audits that must reproduce byte-equal.

**V04 second.** It is the largest piece of engineering among the five, and the one the frozen baseline
constrains hardest: the hardened gate must still accept `blind_baseline_f60ae6e0a2a1.json` with its
recorded total of 74.6. V06 waits on it, and V06 in turn gates V12.

**V11 third.** It is authoring, not engineering: one successor register plus a test that a closed row
without evidence fails. It touches no committed artifact. It unblocks nothing by itself, but V14 needs
it, and it is the cheapest of the five.

**V07 fourth.** Mechanical refactoring with a hard replay constraint: both sanitised configurations must
reproduce byte-equal under the V01 pin, and both `--check` commands must still exit 0. V08 waits on it.

**V09 last of the five, and it is the operator's.** The 2025 call and work-programme documents are not
in the repository. The ticket's own verification line says the operator supplies them. An agent can
build the matrix skeleton and the source index shape; it cannot obtain or authenticate the sources, and
it must not mark a row equivalent because it found no difference.

## What each ticket needs read first

The ledger's shared constraint is to inspect current command help and tests before documenting a
command, and never to invent a flag. Per ticket, the files that decide the work:

| Ticket | Read before writing |
|---|---|
| V04 | `harness/blind_baseline.py` (`BASELINE_CHECKS`, `freeze_baseline`), `tests/harness/test_blind_baseline.py`, the audit's four reproduced negative probes in section 6 of the readiness audit, and the committed freeze record's own check list |
| V05 | `harness/integrity_audit.py` (the grounding-reason constant and the host-identity explanations), `tests/harness/test_integrity_audit.py`, both committed sanitised audits, and the candidate's recorded provenance |
| V07 | `tools/import_external_proposal.py` (the application layer: `DOCUMENT_TITLE`, `EXPECTED_PAGES`, `SECTIONS`, `SUB_SECTIONS`, `CRITERION_HEADING_MARKERS`, `SOURCE_ID_FORMAT`), `runner/external_proposal.py` (`Revision`), `tests/test_msca_dn_import.py::TestReplay` |
| V09 | `harness/profiles/msca_dn_2026_default.json`, `harness/rubrics_msca_dn.json`, `harness/evaluator_scorecard_msca_dn.json`, and the runbook's defaulting proposal, which the ticket rejects |
| V11 | The approved dispositions and the successor dispositions under `docs/tier4_orchestration_state/msca_dn/esr/`, the 2026-10-08 approval records, and the R04 criterion the D13 deferral leaves open |

## Constraints that apply to all five

These are the ledger's, restated because each of the five can break one of them cheaply.

- **No quota.** V01 to V13 run no new assessor. V04's negative probes work on isolated copies of the
  committed report; they do not re-score anything.
- **The frozen baseline stays.** The recorded total of 74.6, the criterion medians and spreads, and
  every binding stay reproducible. V04 is the ticket that proves it rather than the one that risks it.
- **Immutable artifacts.** The committed PDFs, document records, page sources, import manifests, both
  fidelity registers, the ESR record, the frozen baseline, the approval records, the approved
  dispositions and the committed integrity audits are historical evidence. A new decision goes into a
  successor record.
- **No box checked without its evidence.** V11 exists because an unchecked box is information. A row
  marked closed without closure evidence must fail a check, not read as progress.
- **An exclusion is never a pass.** V03 recorded two: the V02c real-file half, and the thirteen dataset
  rows. Neither reads as a passing check anywhere.
- **The lane runs after each ticket.** `py -3.10 -m harness.commands.acceptance_lane` reconciles the
  result against its declaration. A new skip fails it until the skip is declared.

## What this note does not do

It starts no ticket. It runs no assessor, spends no quota and closes no gate. The official 2025 baseline
is not validated: V05 to V14 stand open, G6 and G7 are the operator's decisions, and the 2025 authority
documents that G3 depends on are not yet in the repository.
