# Acceptance record — template

Status: **template. Not an approval.** Nothing here is signed, and no agent signs it.

Authored under ticket V06 of `plans/msca_dn_historical_validation_tickets.md`, which requires the
acceptance record to state which grounding scope was performed. Ticket V15 fills this template in,
adds the remaining acceptance content its own criteria name, and the operator signs it. A copy of
this file with blanks still in it is not closure evidence.

Source of the decision text: section 14 of `plans/reports/MSCA_DN_Readiness_Audit_2026-10-08.md`.

---

## 1. What is being accepted

Every value below is read from the frozen baseline, not retyped from memory. The freeze record is
`<baseline-dir>/blind_baseline_<sha12>.freeze.json`.

| Field | Value | Where it is read from |
|---|---|---|
| Candidate hash | `________` | `bindings.candidate_hash` |
| Profile version | `________` | `bindings.profile_version` |
| Code revision | `________` | `git rev-parse HEAD` at the time of the run |
| Frozen report hash | `________` | `report_sha256` |
| Preflight pack-set hash | `________` | `bindings.preflight_pack_set_hash` |
| Assessor pin and transport | `________` | `bindings.assessor_pin`, `bindings.assessor_transport` |

## 2. Grounding scope performed

The audit allows two scope choices and no third. Strike the one that was not performed.

| Scope | What it claims | What it requires |
|---|---|---|
| `content_focused` | The blind assessment judged proposal content and credibility. Grounding was unassessable, and a human reviewed the sources and the extraction fidelity instead. | The other gates. Grounding is reported unassessable, prominently, in the preflight, the report and the freeze. |
| `source_grounded` | The proposal has been source-grounded or factually verified. | Ticket X01 first: imported-section claims loading with resolvable sources, supported claim statuses backed by evidence, and E2 grounding running over that ledger. Until X01 closes, this declaration is refused by the command, by the report and by the freeze. |

Fill in from the freeze record's `grounding_scope` block:

| Field | Value | Where it is read from |
|---|---|---|
| Declared scope | `________` | `grounding_scope.declared` |
| Declaration source | `________` | `grounding_scope.declaration_source` |
| Measured grounding | `________` | `grounding_scope.measured` |
| Graded units carrying a claim ledger | `___ of ___` | `grounding_scope.with_claims`, `grounding_scope.total` |
| Reason | `________` | `grounding_scope.reason` |

Complete the audit's sentence with the half the record supports:

> Imported-source grounding is **[ validated / explicitly unassessable ]**.

A declared scope of `content_focused` supports *explicitly unassessable* and nothing stronger. Only
a `source_grounded` declaration supports *validated*, and only after X01 is implemented and
validated. A measured grounding of `unassessable` cannot be accepted as *validated* whatever the
declaration says.

Proposal-internal coherence, scientific plausibility, fidelity to the submitted text and independent
factual support are four different claims. A source span inside the proposal establishes what was
submitted. It does not prove a partner commitment, an access entitlement or a scientific result.

## 3. Scope approved for 2026 work

`________`

## 4. Residual uncertainties, deferred matters and owners

Every row of the V11 open-deferral register is resolved here or carried forward with its owner named.

| Item | Owner | What would close it | Resolved or carried forward |
|---|---|---|---|
| `________` | `________` | `________` | `________` |

## 5. Prioritised revision backlog

Each item names its source and the human confirmation it needs before any drafting acts on it.

| Priority | Item | Source | Human confirmation required |
|---|---|---|---|
| `___` | `________` | `________` | `________` |

## 6. Gate closure evidence

| Gate | Closure evidence | Reference |
|---|---|---|
| G1 reproducible import | `________` | `________` |
| G2 original intake and configuration | `________` | `________` |
| G3 historical profile authority | `________` | `________` |
| G4 acceptance and reporting controls | `________` | `________` |
| G5 private execution readiness | `________` | `________` |
| G6 original historical validation | `________` | `________` |

## 7. What this record does not establish

- The result is advisory. It is not a funding forecast.
- One proposal establishes no population-level predictive accuracy.
- Within-assessor spreads are repeatability only. They are not an accuracy interval, and they are not
  a panel of independent reviewers.
- Preparing the Stage B resubmission lane (V16) is not a precondition. This record names V16 as
  downstream work and may be signed with V16 unstarted.

## 8. Approval

| Field | Value |
|---|---|
| Approval identity | `________` |
| Date | `________` |
| Reference | `________` |

The operator signs. An inherited approval, a generated report, a listed command or an empty
placeholder is not closure evidence.
