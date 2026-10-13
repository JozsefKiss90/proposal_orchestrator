# V10 completion report — the historical profile, authored from the matrix

| Field | Value |
|---|---|
| Date | 2026-10-13 |
| Branch | `msca-dn-pre-eval` |
| Ticket | V10, gate G3 |
| Closes | Finding F05 |
| Decision record | `docs/tier4_orchestration_state/decision_log/msca-dn-historical-profile_2026-10-13.json` |
| Status | Agent-drafted. Acceptance is the operator's. |

## 1. What was wrong

One Doctoral Networks profile existed, written for the 2026 call. Assessing the submitted 2025
original under it would score a historical submission by a later year's configuration. Nothing in the
artifact would have said so.

A copy of that profile under a new identifier has the same defect. The binding to the matrix is the
ticket, not a decoration on it.

## 2. What was built

A second profile, beside the 2026 one rather than replacing it. Every element either names the matrix
rows that establish the 2025 rule, or declares what the matrix left open.

| Count | What |
|---|---|
| 13 | elements sourced to matrix rows |
| 2 | elements carrying a declared limitation, because their row is open |
| 2 | elements declared this harness's own, because no call states them |
| 27 | matrix rows, every one of them read by some element |

The deriver refuses rather than writing a profile it cannot justify:

| Refusal | What it catches |
|---|---|
| An element names a row that is not in the matrix | A source that is a label, not a citation |
| An element is sourced to a row whose verdict cannot establish a value | The profile claiming the matrix settled what it recorded as open |
| A limitation over a row the matrix has since sourced | The profile understating what is known |
| A matrix row no element reads | A rule the profile ignores in silence |
| An element declared the harness's own whose row is a call's rule | A reuse dressed as a finding |

The second is the one the ticket exists for. It is checked in both directions: the deriver refuses
before writing, and `harness.historical_profile` reports it over the written profile.

## 3. What differs from the 2026 profile

| Element | 2026 | 2025 | Matrix rows |
|---|---|---|---|
| Target call | `HORIZON-MSCA-2026-DN-01`, deadline 2026-11-24 | `HORIZON-MSCA-2025-DN-01`, opened 2025-05-28, deadline 2025-11-25 | CI-01 |
| Structural authority | the 2026 Part B template, version 6.0 | the 2025 application form, version 5.0 | SM-01, SM-02, SM-03 |
| Part B2 section list | carries the added section | does not | SM-03 |
| Printed total | the weighted total out of 100 | recorded and not used: the 2025 form prints an unweighted total out of 15 | TH-06 |

The 2025 call's identifier, opening and deadline come from the work programme the call was opened
under. Before V09 retrieved it, none of the three had a source of their own year.

### 3.1 A kept rule with no subject

The appendix mapping excludes a Part B2 section that the 2025 form does not have. The rule is kept and
recorded as vacuous rather than deleted. Deleting it would make the two profiles differ by a rule
nobody could trace, and the matrix row SM-03 is what makes the vacuity legible.

## 4. What is reused, and the difference between the two reasons

The scorecard is reused because every scoring rule it carries is sourced to a 2025 document by the
rows the profile names. The weights, the maximum, the resolution, the thresholds and the six score
levels are all stated by the 2025 work programme or the 2025 evaluation form.

The rubrics are reused for a different reason. They are this harness's grading instrument, and no call
document of either year states them. The matrix carries them as era-neutral, and the profile declares
the reuse as a reuse.

Collapsing those two reasons would be the error the matrix's `era_neutral` verdict exists to prevent.
One is an equivalence with a citation. The other is an instrument this repository chose.

## 5. What stays open

Two elements carry a declared limitation, each naming the matrix row that keeps it open:

- **`target_call`** — the call exists and its dates are stated by a document of its own year. That
  this submission was entered into it is declared by two records and evidenced by neither. CI-01.
- **`scorecard`** — every scoring rule it carries is sourced, and which version of the evaluation form
  the 2025 evaluators were given is not established. EI-02.

Four more gaps are recorded and not closed. No matrix row is Confirmed, so no element is. The 2025
application form has no recorded origin. The rubrics are the harness's own instrument. And no
assessment has been run under this profile.

## 6. The 2026 profile is unchanged, and that is measured

The historical profile pins the 2026 profile's sha256. An edit to it fails the check and a test.

The ticket's fourth criterion also holds: the 2026 profile's own applicability question stays open for
Stage B, and nothing here touches it.

One test contract changed. `tests/test_msca_dn_workspace.py` asserted the 2026 profile was the only
Doctoral Networks profile in the tree. It now asserts there are two, that each names its own call, and
that their identifiers differ. That is a stronger statement, and it is the one this ticket makes true.

## 7. Reuse across a pair is refused

The refusal is the existing machinery's, not new code. The preflight compares `profile_id` and
`profile_version` against the loaded bundle, and the freeze binds both.

The two profiles carry different document hashes, so a report made under one is a mismatch against the
other rather than a figure silently reused. Tests assert the comparison is in both modules and that
the hashes differ.

## 8. Checks run

| Check | Result |
|---|---|
| `tools.author_msca_dn_historical_profile --check` | `up to date` — byte-equal replay |
| `harness.commands.historical_profile` | green over 9 findings |
| `tests/test_msca_dn_historical_profile.py` | 28 passed |
| `tests/harness/test_historical_profile.py` | 21 passed |
| `tests/harness/` plus the workspace modules | 1,774 passed, 17 skipped |
| The agnosticism lint | passes; the command finds its declaration by schema, not by filename |

The acceptance lane's profile area now names both new modules, and the lane document's table row
matches the declaration. The lane itself was not run: its single-process result is not measured here.

No assessor ran. No scoring was performed. No quota was spent, and the 74.60 baseline is untouched.

## 9. What this is not evidence of

- That the 2025 evaluators would score this text as this profile scores it.
- That the harness's scoring method is correct.
- That the 2026 profile's applicability question is settled.
- That V10 is accepted. Acceptance is the operator's.

## 10. Artifacts

| Path | What |
|---|---|
| `harness/profiles/msca_dn_2025_historical.json` + `.md` | The profile and its reading |
| `tools/author_msca_dn_historical_profile.py` | The deterministic author |
| `harness/historical_profile.py` | The reader, with nine findings |
| `harness/commands/historical_profile.py` | The check and the reading |
| `tests/test_msca_dn_historical_profile.py` | 28 tests over the committed profile |
| `tests/harness/test_historical_profile.py` | 21 tests over a synthetic profile and matrix |
| `harness/acceptance_lanes/msca_dn_historical.json` | The lane's profile area, extended |
| `docs/tier4_orchestration_state/decision_log/msca-dn-historical-profile_2026-10-13.json` | The decision record |
