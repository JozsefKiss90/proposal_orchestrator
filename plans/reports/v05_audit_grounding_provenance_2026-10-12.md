# V05 completion report — audit grounding and identity wording derived from candidate provenance

Date: 2026-10-12.
Branch: `msca-dn-pre-eval`, from `0b281a4`.
Ticket: V05 of `plans/msca_dn_historical_validation_tickets.md`.
Closes: finding F06 of `plans/reports/MSCA_DN_Readiness_Audit_2026-10-08.md`, and criterion 2 of V02a,
transferred to V05 by `plans/reports/v03_acceptance_lane_completion_2026-10-09.md`.
Decision record: `docs/tier4_orchestration_state/decision_log/msca-dn-audit-grounding-provenance_2026-10-12.json`.

Five of six acceptance criteria are closed. Criterion 4 stays open, for the reason in section 5, and is
not read as a pass anywhere. F06 closes. Gate G4 does not: V06 is still open. No assessor ran, no quota
was spent, and the frozen 74.60 baseline is untouched.

Environment: Python 3.10.6 and PyMuPDF 1.28.2 over MuPDF 1.28.2 — the pin V01 established
(`docs/tier4_orchestration_state/decision_log/msca-dn-extraction-environment-pin_2026-10-08.json`).

## 1. What was wrong

Three statements the integrity audit made about every candidate were module constants, not facts about
the document it read:

| Statement | Where it came from at `0b281a4` |
|---|---|
| Why every ledger claim is Unresolved | `GROUNDING_REASON = "supporting sources removed by sanitisation"` |
| What status a ledger entry should declare | `_LEDGER_EXPECTED_STATUS = "unresolved"` |
| Why a host line cannot be compared with the recruitment table | a sentence appended to every DC finding |

The official original carries its references and its real identities. Applied to it unchanged, all
three would be false. Its sources were never removed. The status its ledger declares is its own
import's to state. Its host line is comparable with its table, and an anonymised-host assumption would
suppress a comparison the sources support.

## 2. What was built

`harness/candidate_provenance.py` derives the three statements from the records each candidate's own
import wrote. The first is the import manifest under
`<graph-root>/docs/tier4_orchestration_state/dev_graph/imports/`, matched by `document.node_id` so one
revision's manifest is never read for another's. The second is the fidelity register that manifest
names.

The register holds two halves, and they are different kinds of evidence. `provenance.transformation` is
the operator's declaration about what the transformation did. `derived` is the importer's measurement
over the stored bytes. Where they disagree the measurement decides and the disagreement is flagged.

| Grounding cause | What has to hold | Reason the rows carry |
|---|---|---|
| `supporting_sources_removed_by_sanitisation` | the register declares the citations removed, the importer measured no citation marker, and the register declares the file is not the submitted document | *supporting sources removed by sanitisation* — the wording both committed audits carry |
| `supporting_sources_present_and_unresolved` | a measured citation-marker count above zero | the candidate carries source markers and no imported-claim route resolves them |
| `unstated` | anything else, a missing manifest included | the cause is Unresolved, and the gap is flagged |

The identity scope comes from the declared `identifiers` value. No measurement distinguishes a real
partner name from a generalised one. `identifiers_as_submitted` is the only scope under which the audit
compares the recruiting participant with the host line of its project in 1.1. A host line names the
institution and often adds a country or an abbreviation the recruitment table omits, so the comparison
is containment over the module's own normaliser and not equality. A disagreement is an `inconsistency`
naming both values. The other two scopes report `not_comparable`, each with its own reason.

A declared transformation value is prose. Only its leading word is read, against a closed vocabulary,
after an optional leading `all`. A phrasing the vocabulary does not hold produces an explicit gap and a
flag. The rule can fail to recognise a value. It cannot invent one.

The persisted report gained no key. `AUDIT_SCHEMA_VERSION` stays at `1.0.0`, which is what keeps the
committed audits reproducible. The derivation is printed beside the rendered report instead: the cause,
the records read, and one basis line per statement it rests on.

## 3. The acceptance criteria

| Criterion | Evidence |
|---|---|
| 1 — the reason and the host-identity explanations derive from recorded provenance and capabilities | `harness/candidate_provenance.py`; `TestGrounding::test_a_referenced_candidate_gets_its_own_reason`, `TestIdentityComparison` (12 checks), `test_candidate_provenance.py::TestSanitisedCandidate` and `TestReferencedCandidate` |
| 2 — expected claim status comes from the candidate's own ledger | `TestGrounding::test_the_expected_status_is_the_one_the_candidates_provenance_records` and `test_without_a_recorded_contract_no_entry_is_checked_against_one`. **Source substitution, declared:** the expectation is read from the manifest's `claims.declared_status` — the import's declaration *about* that ledger — not from the ledger array. Reading the ledger as its own expectation is circular, so no contradiction could ever be reported. The ticket box records the same |
| 3 — table schema and identity comparisons revalidated for a referenced document with real identities | identities: `test_identifiers_as_submitted_are_compared_and_agree` and `test_a_disagreement_between_two_real_names_is_an_inconsistency`. Table schema: `test_references_in_the_prose_do_not_change_what_the_tables_parse`. Bracketed markers, a DOI, a URL and a reference list added to the prose leave every table, row count, header field, DC project and finding identical |
| 4 — both committed sanitised audits reproduce byte-equal | **Open.** Section 5 |
| 5 — an unstated cause yields an explicit Unresolved reason, not a borrowed one | `TestGrounding::test_an_unstated_cause_is_reported_unresolved_not_borrowed`; `TestCommand::test_without_import_records_the_reason_is_unresolved_and_flagged`; `TestFindAndResolve::test_resolving_nothing_yields_an_explicit_gap` |
| 6 — inherited from V02a criterion 2 | Section 4 |

## 4. V02a criterion 2, closed

The criterion reads: *the two integrity-audit integration failures pass against the reproduced document
identity and the V05 provenance-derived wording.* V02a closed its first half on 2026-10-09 and left the
second open. V03 transferred it here rather than recording it as a pass.

No earlier record resolves "the two integrity-audit integration checks" to test identifiers. A pass over
an unnamed pair would not be checkable. So this report names the two integration checks in
`tests/harness/test_integrity_audit.py` that depend on both the document identity and the wording:

| Check | What it depends on | Result |
|---|---|---|
| `TestMscaDnWorkspace::test_the_committed_pe07_report_over_the_first_copy_is_unchanged` | the reproduced document identity: the committed audit names the node id `ie.node_id_of` derives for `sanitised_v1` | passes |
| `TestMscaDnWorkspace::test_grounding_axis` | the wording: 45 claims, each Unresolved, each carrying the reason | passes, and the reason is now derived from the candidate's own records |

Two further checks keep the second row from silently reverting to a constant. One is
`TestMscaDnWorkspace::test_the_hosts_are_not_comparable_for_the_reason_the_records_state`. The other is
`TestTheCommittedAudits`, whose eight checks re-derive both committed audits from the records of the
candidate each describes.

## 5. Criterion 4 — what reproduces, and why the box stays open

Both audits are historical evidence under the ledger's immutable-artifact constraint. Neither file was
edited. Both are pinned by sha256 in the test, so an edit fails a check rather than passing quietly.

| Audit | Candidate | Grounding axis | Identity findings | Whole check payload |
|---|---|---|---|---|
| `integrity_242f1afb02c8_0003.json` | `…@b51a103520b58ded` | byte-equal | byte-equal, 9 findings | byte-equal |
| `integrity_13ad3ad81d7e_0001.json` | `…@bdb8670f6987e4db` | byte-equal | byte-equal, 9 findings | does not reproduce |

Everything V05's derivation produces reproduces byte-equal for both. The first copy's other findings do
not, and did not before V05 either. That audit predates operator decision D11 and ticket R03, which
retired twenty-seven of its findings. Sixteen are `undeclared_dependency`, now an inventory entry, and
nine are `out_of_window` appointments, now a check note. The last two are the whole-cohort package sets
WP6 and WP7, now compared in one direction. Nothing is new.

`TestTheCommittedAudits::test_the_first_copys_payload_differs_only_by_the_retired_rules` enumerates all
twenty-seven by name, so the divergence is measured rather than asserted.
`TestMscaDnWorkspace::test_d11_retires_exactly_the_sixteen_undeclared_findings_of_the_r03_audit` and its
two neighbours already pinned it before V05.

So the criterion as written cannot hold for the first copy, and it is not V05's to close. Closing it
needs a successor audit over that candidate under the current rules, which is a new artifact and the
operator's decision, or an amendment to the criterion. The box therefore stays open and says so, and
`tests/harness/test_acceptance_lane.py::TestTheDependencyGate::test_a_criterion_conceding_partial_reproduction_is_never_checked`
fails if it is ever checked while it still explains what does not reproduce.

Byte-equality here is of the derivation-dependent payload, not of a whole file. A persisted report's
header carries its own `audited_at` timestamp and a `writes` entry holding the absolute path of the
machine that wrote it, and `write_audit` never overwrites. Those fields are not derivation outputs.

## 6. Tests

| Command | Result |
|---|---|
| `py -3.10 -m pytest tests/harness/test_candidate_provenance.py` | 48 passed |
| `py -3.10 -m pytest tests/harness/test_integrity_audit.py` | 126 passed |
| `py -3.10 -m pytest tests/harness/test_acceptance_lane.py` | 55 passed |
| `py -3.10 -m pytest tests/harness/test_boundary.py tests/harness/test_commands.py` | 26 passed |
| `py -3.10 -m pytest tests/harness/test_profile.py -k Instrument` | 1 passed — no instrument literal entered `harness/` |
| `py -3.10 -m mypy` over the three changed modules | no error in any of them |

Five existing checks changed, and one fixture gained the import records a real candidate carries. Each
is a wording change the ticket requires, not a weakened assertion:

| Check | Change |
|---|---|
| `TestGrounding::test_every_claim_is_unresolved_for_the_one_reason` | renamed `…_for_the_candidates_own_reason`; asserts the derived reason, not the module constant |
| `TestGrounding::test_a_declaration_other_than_unresolved_is_flagged_…` | renamed `…_against_the_recorded_contract_…`; the expectation comes from the candidate's records |
| `TestCheckDcs::test_the_host_is_reported_not_comparable_with_both_values` | runs under a sanitised provenance; the asserted values are unchanged |
| `TestTheDependencyGate::test_neither_reconciled_criterion_is_checked` | split in three: V02c stays open, V02a criterion 2 is checked with its evidence, and V05 criterion 4 stays open |
| `_dn_findings` | resolves each revision's own provenance before running the checks |
| the synthetic `world` fixture | writes an import manifest and a register, so the command tests exercise the resolved path. A separate check deletes the manifest and asserts the unstated path |

## 7. The acceptance lane

`py -3.10 -m harness.commands.acceptance_lane`, run on 2026-10-12 from the development tree under the
V01 pin:

| | The lane, 2026-10-09 (V03) | The lane, 2026-10-12 (V05) |
|---|---:|---:|
| Passed | 2,121 | 2,202 |
| Failed | 0 | 0 |
| Errors | 0 | 0 |
| Skipped | 17, every one declared | 17, the same declared rows |
| Collected | 2,138 | 2,219 |

GREEN, with no new skip and no new failure. The three modules this work touched account for the added
cases: `test_candidate_provenance.py` is new and collects 48, `test_integrity_audit.py` now collects
126, and `test_acceptance_lane.py` 55.

The lane's first run of this work failed on
`TestTheDependencyGate::test_neither_reconciled_criterion_is_checked`, because V02a criterion 2 had been
checked and that test pinned both reconciled criteria as open. That is the ledger's own guard working:
a box cannot change state without a reader deciding whether its evidence exists. The criterion 4
problem in section 5 came from the review of this change, not from the lane.

## 8. What this does not say

- Not that the official original has been imported, audited or validated. V07 and V08 externalise the
  document configuration, and V09 is the operator's.
- Not that any claim in any candidate is corroborated. Every claim stays Unresolved. Only the stated
  reason for that changed.
- Not that a grounding scope is declared in the preflight, report or freeze. That is V06, still open,
  and a `--no-claims` run remains unassessable by design until it lands.
- Not that the X01 imported-claim route exists. The sources-present reason names its absence. It does
  not substitute for it.
- The identity comparison is exercised by fixtures only. No committed candidate declares its
  identifiers as submitted, so nothing in the tree reaches that branch yet.
