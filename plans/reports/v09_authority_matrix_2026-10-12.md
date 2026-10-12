# V09 completion report — the 2025 authority sources and the equivalence matrix

Date: 2026-10-12.
Branch: `msca-dn-pre-eval`, from `ab0fd35`.
Ticket: V09 of `plans/msca_dn_historical_validation_tickets.md`.
Closes: the source half of finding F05 of `plans/reports/MSCA_DN_Readiness_Audit_2026-10-08.md`.
Decision record: `docs/tier4_orchestration_state/decision_log/msca-dn-authority-matrix_2026-10-12.json`.

Four of five acceptance criteria are closed. Criterion 1 is closed for the index and its
authentication contract, and open for the obtaining: four 2025 documents are not in this repository
and the operator supplies them. V09 no longer blocks V10 on anything but those four documents.

No assessor ran, no quota was spent, and the frozen 74.60 baseline is untouched. No row of the matrix
is Confirmed, and no gate is closed.

One check did not run to completion. The acceptance lane gains an `authority` area; its declaration is
reconciled and every module this change touches passes, but the lane's own single-process result is
unmeasured and the decision record declares that `Unresolved`. Section 7.1 states what was measured in
its place. No lane figure appears anywhere in this change.

Environment: Python 3.10.6, PyMuPDF 1.28.2 with MuPDF 1.28.2 — the pin V01 established
(`docs/tier4_orchestration_state/decision_log/msca-dn-extraction-environment-pin_2026-10-08.json`).

## 1. What was wrong

The runbook proposes preparing the historical profile as a copy of the 2026 one:

> Where no source states a difference, the rule stays as the 2026 profile has it and the profile says
> so.
>
> — `plans/msca_dn_pe09_runbook.md` section 3

That sentence is a defaulting policy. It carries a 2026 rule into a 2025 assessment on the strength of
nobody having looked, and a record that calls the result equivalence has turned an absence of evidence
into a sourced fact. The audit's F05 says the same thing in one line: *a rule affecting interpretation
or numerical scoring cannot silently become "2025" because evidence of a difference was not found.*

The second half of F05 is subtler. The specification's decision 3 pinned one 2026 profile and justified
the vintage mismatch on a form-equivalence record — section 2.12's measurement that the V5.0 and V6.0
Part B templates are structurally identical for this call. That record is real and it is cited here.
But it measured headings, tables, page caps and section numbering. Reading it as equivalence of the
weights, the thresholds, the level descriptions or the tag grammar would be reading more out of it than
it measured.

## 2. What was built

Two artifacts and one reader.

| Artifact | What it is |
|---|---|
| `…/msca_dn/authority/authority_source_index_2026-10-12.json` | 16 documents, 12 obtained and pinned, 4 recorded absent |
| `…/msca_dn/authority/equivalence_matrix_2025_2026-10-12.json` | 26 rows over 9 areas, 72 citations, 36 measurements |
| `harness/authority_matrix.py` | the vocabulary, the two loaders, the check and both renderings |
| `harness/commands/authority_matrix.py` | the command that checks a matrix and writes both readings |
| `tools/author_msca_dn_authority_matrix.py` | the deterministic deriver, with a byte-equal replay |

The reader carries no instrument name, no call identifier and no year. The areas a matrix must cover
are the declaration's `required_areas`; the era labels are the declaration's; the rows are the tool's.
`tests/harness/test_profile.py` lints that separation over all of `harness`.

### 2.1 The vocabulary has no verdict for *we did not find a difference*

| Verdict | Rows | What it means |
|---|---:|---|
| `equivalent` | 12 | a 2025 source states the rule, and it is the rule the 2026 profile holds |
| `differs` | 1 | a 2025 source states a different rule |
| `defaulted` | 5 | the 2026 rule is carried forward because no 2025 source states it — **not** equivalence |
| `unresolved` | 2 | no source states the rule, and the limitation is recorded |
| `era_neutral` | 3 | the rule is the harness's own, and no call document of either year states it |

`check` reports a row marked `equivalent` or `differs` with no citation into an **obtained**
**historical** source. That single finding is criterion 4 enforced rather than stated: there is no way
to spell defaulting as equivalence and keep the check green. A `defaulted` row additionally has to name
the rule its defaulting affects, and `check` reports one that does not.

### 2.2 Every row is derived, not typed

The row set is a measurement of the records, in the shape `tools/author_deferral_register.py`
established. Nine refusals stop the tool rendering a claim the records no longer support:

| Refusal | What it protects |
|---|---|
| a declared quote not on the page it cites | every document citation |
| a declared passage absent from a prose record | the citations into the specification |
| the last-occurrence rule breaking | the ten aspect-heading citations |
| the first-occurrence rule breaking | the eleven appendix cross-references |
| the two forms' criteria tables carrying different anchor sets | SM-01's second direction |
| a vouched authentication with no basis, or a basis a record no longer states | the two `operator_supplied` entries |
| an `[OPTION for` tag in an application form | EI-04's reasoning about which form owns the tag grammar |
| the total formula not reproducing the recorded total | SA-01 |
| the call identifier stopping being Assumed | CI-01 |
| a 2025 document arriving at its destination | the four absence entries |

The page rules deserve a word, because two different rules look arbitrary until you see what validates
them. A heading occurs twice or three times in a form: in the section instructions and again in the
evaluation-criteria table at the back. The scorecard cites the table, which is the *last* occurrence —
and the tool refuses unless the last occurrence in the 2026 form is still the page the scorecard
declares. An appendix cross-reference is cited at its *first*, instructional occurrence, validated the
same way against the mapping's own declared page. Each rule is a measurement against a committed
record, not a habit.

## 3. What the sources actually settle

This is where the work went, and it is the part a reader should check hardest.

### 3.1 One 2025 call document is held

`docs/tier2a_instrument_schemas/application_forms/msca/af_he-msca-dn_en.pdf` is the V5.0 application
form — the form of the 2025 call. It was already in the tree, cited by the form-equivalence record, and
nothing had read it as a 2025 authority in its own right. It is one, and it carries five rows:

| Row | What the 2025 form states |
|---|---|
| SM-01 | all ten numbered Part B aspect headings, verbatim, one citation each |
| SM-02 | the 34-page Part B1 cap and the 30 pages for sections 1 to 3 |
| SM-03 | Part B2 ends at section 10 |
| AM-01 | all eleven cross-reference sentences the appendix mapping routes on |
| VA-02 | the implementation modes a Part B header must declare |

AM-01 is the row the form-equivalence record could not have settled. Its eleven sentences are
instructional text, not structure, and the record's measured scope does not reach them. They are
located in the 2025 form instead, each verified on the page it cites.

### 3.2 Two 2025 sources are about this submission, not about the call

The Evaluation Summary Report and the fidelity register are 2025-era, and they are strong evidence —
of what was applied to *this* submission. They are not authorities on a rule of the 2025 call. The
matrix enforces the distinction rather than noting it: a row declares `settles`, and `check` reports a
`call_wide` conclusion resting only on a source whose class is `evaluation_output` or
`submission_record`.

Fourteen rows settle as applied to this submission. Twelve settle call-wide. Five of those twelve
assert a relation between the two eras, and each of the five carries a 2025 call document behind it.
The other seven are defaulted or unresolved, which is what the absent documents leave them as.

What the ESR settles is worth stating plainly, because it is more than the audit assumed was available:

| Row | 2025 evidence |
|---|---|
| CR-01 | three criterion scores, named Excellence, Impact, Implementation, in that order |
| WT-01 | the weights 50, 30 and 20 percent, recorded beside each score |
| TH-01 | the per-criterion threshold of 3 out of 5, recorded three times |
| TH-02 | the overall threshold of 70 out of 100, in the result wording |
| TH-04 | the maximum of 5.00, printed beside each criterion score |
| EI-03 | three criterion scores and 29 observations, none carrying a score |
| SA-01 | the weighted total the formula has to reproduce |

SA-01 is arithmetic evidence rather than quoted wording. The scorecard's formula applied to the 2025
evaluation's own recorded criterion scores reproduces its own recorded total, and the tool refuses to
render if it stops doing so. That is the only row in the matrix whose 2025 application is evidenced by
a computation.

EI-03 rests on a measured **absence**: no observation carries a score field. An absence evidences that
the rule was applied. It does not confirm the rule's text, which is why the row is `Inferred` and says
so in its own `status_basis`.

### 3.3 The form-equivalence record settles section structure, and the index enforces it

The scorecard's entry in the index carries a `scope_restrictions` block: the field prefix
`provenance/v5_equivalence`, settling the area `section_mapping`, with what it measured spelled out. A
citation of that passage from a row in any other area is the finding
`citations_outside_their_declared_scope`.

It is cited exactly once, from SM-02, inside the area it measured — and SM-02 does not rest on it
anyway: the 2025 form's own two sentences are what settle the row, and the record corroborates. A test
over the committed index builds a synthetic row that cites the same passage from `thresholds` and
asserts the finding fires, so the restriction is enforced and not merely declared.

### 3.4 No row is Confirmed, and the reason is in the index

Each entry declares how its bytes are vouched for:

| Authentication | Entries | What it says |
|---|---:|---|
| `issuer_hash_confirmed` | 0 | an expected hash from the issuing body, matched |
| `operator_supplied` | 2 | the operator supplied the document, and the entry names the field recording that |
| `computed_only` | 10 | hashed in this tree; nothing records where the bytes came from |
| `not_obtained` | 4 | absent |

`check` reports a `Confirmed` row with no `issuer_hash_confirmed` source behind it. Since there is no
such source, no row is Confirmed — eighteen are `Inferred`, seven `Assumed` and one `Unresolved`. That
is not pessimism about the documents. It is the difference between pinning a file and authenticating
it, and the V08 contract — an operator's expected hash from the authoritative source — is what would
move any of them.

A rank is evidence too, so it carries its own. Both `operator_supplied` entries name the field where
that provenance is recorded: the ESR record's own `authored_by`, which states an operator
transcription, and the register's `provenance/declared_by`, which states the operator. The deriver
resolves each field and refuses if the record has stopped saying it, and `check` reports any entry
claiming a rank above `computed_only` with no basis. Without that, the rank would rest on the index
author's word, which is what a rank is supposed to improve on.

## 4. What is missing, and which rows it holds open

Four 2025 documents are not here. Each index entry records the destination it will be filed at. A
destination is not a claim about a file. Each entry also records the rows it would settle, derived
from the rows themselves, so the two cannot drift.

| Document | Rows it would settle |
|---|---|
| the evaluation form version in force for the 2025 call | CR-02, EI-01, EI-02, EI-04, TH-03, TH-05, WT-02 |
| the conditions and topic text of the 2025 call | CI-01, EI-02 |
| the MSCA work programme in force for the 2025 call | CI-01 |
| the General Annexes in force for the 2025 call | TH-03 |

Seven of the eight unsourced rows trace to the evaluation form. That is the single largest gap in the
historical lane, and EI-01 is the sharpest instance: the six score-level descriptions are what *a 4*
means, and a changed level sentence changes every grade the assessor awards. A comparison between the
assessor's median and 85.80 rests on EI-01 being equivalent, and nothing in this repository says it is.

CI-01 is the prerequisite nobody can work around. Which call the 2025 submission was evaluated under is
**Assumed** — the ESR names no call and no proposal number, and two records declare the identifier the
operator's declaration. The four documents above cannot be fetched until it is settled, and every
2025-side citation in the matrix is addressed to a call identified by declaration.

## 5. The one difference

SM-03. The 2026 form adds a Part B2 section 11, RAISE DN, reserved for applicants of another call. The
2025 form's section 10 is followed by its example block; the 2026 form's section 10 is followed by
section 11, and the form's own history table dates the addition to V6.0.

Its consequence is small and worth recording anyway: the appendix mapping's `never_received` rule,
which excludes section 11, has no subject under the 2025 form. The historical profile keeps the rule
and records that it is vacuous. Deleting it would carry a 2025 workaround into the instrument V10 and
Stage B both reuse.

## 6. Declared deviations

None is in V09's five acceptance criteria.

**Criterion 1 is half closed, and the half that is open is the operator's.** The index exists, it pins
twelve documents by sha256, and it records the four absences with their destinations. It obtains
nothing. The ticket's own verification sentence assigns that to the operator — *the operator supplies
the source documents* — and the authentication contract is V08's: an expected hash from the
authoritative source, matched before anything is written. Nothing here fetches a document, and no row
closes by assuming what one would say.

**A ninth area beyond the ticket's eight.** The ticket names criteria, weights, thresholds, evaluator
instructions, DN variant, section and appendix mapping, and scoring assumptions. `required_areas` is
exactly those eight, and a test asserts it against the ticket. `call_identity` is one row more. The
call the 2025 submission was evaluated under is the prerequisite for addressing the index at all.
Leaving it out would have made it the one unexamined assumption under every other row.

**Five rows are `era_neutral` rather than sourced.** SA-02 to SA-06 are the harness's own
assumptions, and each affects a number or an interpretation, which is why criterion 2 reaches them:

| Row | The assumption |
|---|---|
| SA-02 | five samples per criterion, reported as a median with its spread |
| SA-03 | grounding reported unassessable where no claim ledger reaches the pack |
| SA-04 | the assessed text is a sanitised derivative, not the submitted document |
| SA-05 | a cell reports addressal and grounding as two values, never blended |
| SA-06 | the scorer reads the whole criterion section, inside the budget, with no selection |

None is a call rule, so neither equivalence nor defaulting applies, and calling one `equivalent` would
have been the same error in a new place. Each declares why no era states it.

**Twenty-five findings where the ticket asked for one.** The ticket asks that no row be marked
equivalent because no difference was found. The full set, and why each is there:

| Finding | Why it is in the check |
|---|---|
| `equivalence_without_historical_evidence` | the asked rule |
| `defaulting_without_an_affected_rule` | criterion 4's second half: defaulting named as defaulting |
| `rows_missing_field` | an empty rule, basis or consequence is a row nobody can act on |
| `duplicate_row_ids` | two rows under one id hide one of them |
| `areas_required_but_not_covered` | criterion 2: the eight areas |
| `differences_not_described` | a `differs` row that does not say what differs |
| `unresolved_without_a_limitation` | criterion 3's second branch: the limitation is the artifact |
| `era_neutral_without_a_justification` | the escape verdict, kept from becoming an escape |
| `rows_without_a_citation` | criterion 3: a row resolves to a document or records why it cannot |
| `citations_of_undeclared_sources` | criterion 3: a citation of a document the index has not pinned |
| `citations_of_unobtained_sources` | criterion 1: a row resting on a document nobody has |
| `citations_that_do_not_resolve` | the same row pointing nowhere inside a pinned document |
| `document_citations_without_a_quote` | criterion 3: a page number alone locates nothing |
| `citations_outside_their_declared_scope` | criterion 5: a record read past what it measured |
| `rows_naming_an_undeclared_future_source` | a row promising that a document nobody has declared would settle it |
| `call_wide_claims_on_submission_evidence` | criterion 5's species: one submission read as the call |
| `confirmed_without_an_authenticated_source` | a status the bytes cannot carry |
| `missing_sources` | a pinned document absent from the tree |
| `edited_immutable_sources` | a historical record whose bytes moved |
| `stale_tracked_inputs` | the matrix out of date against a record allowed to move |
| `stale_source_index` | the matrix bound to an index that has since changed |
| `unobtained_sources_declared_with_pages` | a page count over a document nobody has |
| `authentications_claimed_without_a_basis` | a vouched rank with nothing recording who vouched |
| `measurements_of_undeclared_sources`, `failed_measurements` | criterion 3 for a measurement |

Fifteen of the twenty-five serve criteria 1 to 5 directly. The ones that go beyond are
`duplicate_row_ids`, `era_neutral_without_a_justification`, `stale_source_index`,
`unobtained_sources_declared_with_pages`, `authentications_claimed_without_a_basis`,
`rows_naming_an_undeclared_future_source`, the two source-role findings and
`confirmed_without_an_authenticated_source`. Each is a way the matrix could read as honest while
having stopped being so. None weakens the asked rule.

**Five rows changed after review, and two are new.** The first draft of this matrix carried defects
of the kind its own check exists to catch, and the review found them:

| Row | What was wrong | What it is now |
|---|---|---|
| TH-04 | one row claimed the maximum *and* the one-decimal resolution `equivalent`, with the 2025 record printing `4.20` to two decimals and stating no resolution rule | the maximum alone, which the record does print |
| TH-05 | — | the resolution, `defaulted`, with the rule it affects, its risk and the document that would settle it |
| SM-01 | claimed set equality from ten inclusion citations | the second direction is measured, and refuses |
| AM-01 | claimed equivalence of the cross-references without saying the claim is an inclusion | the unmeasured direction is stated in the row and in the matrix's `uncertainties` |
| SA-05, SA-06 | two harness assumptions that affect a number were absent | `era_neutral` rows cited to the specification |

TH-04's defect is worth naming, because it is exactly what criterion 4 forbids. All three recorded
scores end in zero, which is consistent with a one-decimal rule and is not evidence of one. Calling it
equivalent recorded the absence of a visible difference as agreement.

**An authentication rank now carries its own evidence.** Both `operator_supplied` entries name the
field recording that provenance, the deriver resolves it, and the check reports a vouched rank with no
basis. The rank previously rested on the deriver's own word.

**`resolve_field` moved to a module of its own.** `harness/record_pointer.py` now holds the pointer
grammar, and `harness/deferral_register.py` re-exports it. The alternative was duplicating eighteen
lines of resolver inside one package. V11's 94 checks pass unchanged.

**The rows are built area by area.** Nine functions, one per area, over a single parsed `_Records`,
in the shape `tools/author_deferral_register.py` established. The four refusals about the records
rather than about one row run once, before any row is built. The index's two tables are frozen
dataclasses rather than tuples. The replay is byte-equal across the whole refactor, which is what
says it changed nothing.

**Four tracked inputs cost what V11's ledger binding cost.** The scorecard, the 2026 profile, the
appendix mapping and the pre-evaluation specification are allowed to move, and any edit to one makes
the matrix stale until it is re-derived. The alternative was rows pointing at records nothing pins. The
matrix's own `uncertainties` carry the same note.

**The runbook is cited by path and not bound.** Its section 3 is the policy this matrix replaces, and
V12 is the ticket that corrects it. Binding it would have made V12's edit turn the `authority` lane
area red for a reason unrelated to the matrix, which is the cycle R05 cut the same way.

## 7. Tests

| Command | Result |
|---|---|
| `py -3.10 -m pytest tests/harness/test_authority_matrix.py` | 68 passed |
| `py -3.10 -m pytest tests/test_msca_dn_authority_matrix.py` | 63 passed |
| `py -3.10 -m pytest tests/harness/` | 1,695 passed, 17 skipped |
| `py -3.10 -m pytest tests/test_msca_dn_declaration_drafts.py` | 80 passed |
| `py -3.10 -m pytest tests/` (whole suite) | 7,479 passed, 194 failed, 86 skipped |
| `py -3.10 -m tools.author_msca_dn_authority_matrix --check` | up to date, exit 0 |
| `py -3.10 -m harness.commands.authority_matrix --matrix …` | 26 rows, check green, exit 0 |
| `py -3.10 -m harness.commands.acceptance_lane --list` | 70 modules in 16 areas, exit 0 |

The committed-artifact module re-derives every verbatim passage. All 35 document citations are
re-extracted from the page they cite through `runner.source_index.read_page_text`. That is the route
the evaluation bundle used, so a quote located here is located in the text every other derivation in
this repository sees. Each refusal is exercised against the real documents with one record mutated,
rather than against a fixture that cannot drift. The anchor comparison is re-measured independently
in the test, including that neither page bounding the criteria table carries an anchor.

The whole suite's 194 failures are measured against a baseline rather than asserted to be
pre-existing. `ab0fd35` was checked out into a separate worktree, with the gitignored `.env` copied
in. Both suites ran from the same checkout state. The baseline gives **205 failed, 7,308
passed, 107 skipped**. The two failing node id sets were compared with `comm`: every one of this
change's 194 appears in the baseline's 205, and the difference set is empty. The baseline's extra 11
failures and extra 21 skips come from artifacts a fresh worktree does not carry, which is why the
comparison is of node ids and not of counts.

### 7.1 The acceptance lane

The lane gains an `authority` area holding the two new modules, declared **not** depended on. V03's
first acceptance criterion names seven depended-on areas, and
`tests/harness/test_acceptance_lane.py::TestAreas::test_exactly_the_areas_v03_names_are_the_depended_on_ones`
asserts exactly those seven. The matrix is what V10's historical profile is authored *from*; the
`profile` area, which is depended on, is what checks the profile a Stage A run loads. An eighth
depended-on area would amend an accepted measurement without covering anything the run reads.

**The lane was not run to completion in this change, and no lane result is recorded here.** What was
measured instead, and what each measurement is worth:

| Check | Result | What it does not cover |
|---|---|---|
| `harness.commands.acceptance_lane --list` | exit 0 | runs no test; it proves the declaration loads, every declared module is in the tree, no module belongs to two areas, and every exclusion sits in an area the run does not depend on |
| `tests/harness/test_acceptance_lane.py` | 68 passed | the declaration's own invariants, including that the new area's modules are assigned and that the lane document names every area |
| `tests/harness/` whole | 1,695 passed, 17 skipped | every harness module, in one process — but not the lane's own MSCA-DN modules under `tests/` |

The operator's `py -3.10 -m harness.commands.acceptance_lane` is what closes it. No figure for the
lane's passed, failed, errors, skipped or collected is stated anywhere in this change.

### 7.2 One other ticket's artifact had to be re-rendered

The R04 declaration drafts carry an adoption-cost scan that reads every committed file under `docs/`,
`workspaces/` and `plans/` for each fidelity register's path and hash. The authority index pins the
sanitised revision's register and the matrix names it, so the sanitised draft and the shared checklist
both gained three dependent rows and their tool's `--check` started failing.

That coupling is the scan's stated design: *a new committed artifact that names a register makes the
drafts stale, and the fix is to re-render.* So the two files were re-rendered, and a successor
re-render record states the before and after hashes of the two that moved. The resolved-fixes draft is
untouched, because no new artifact names its register.

The re-render test moved from a single record to the series. It now resolves, for each rendered draft,
the newest record stating its hash, and checks that statement against the committed bytes. The older
record is unedited and still describes the one file this re-render did not move. The invariant is the
one it always was: a stated hash describes the committed bytes.

## 8. What this is not evidence of

- **That the 2025 rules are known.** Five rows are defaulted and two unresolved. A `defaulted` row
  declares that a rule is unsourced, which is neither a finding that it is wrong nor permission to
  read a number as if it were established.
- **A closed gate G3.** V10 closes F05 by authoring the historical profile from this matrix. V09
  closes its source half.
- **A complete source index.** Four required 2025 documents are absent, and criterion 1's obtaining
  half is open.
- **A Confirmed anything.** No source is authenticated by its issuing body, so no row is Confirmed.
- **Operator approval.** Both declarations are `agent_drafted_pending_operator_review`.
- **A historical profile.** V09 authors none. The 2026 profile is unchanged, byte for byte.
- **A new assessor run.** No quota was spent and no assessor was called.

## 9. Remaining uncertainties

**The call identifier gates the obtaining.** CI-01 is unresolved, and the four absent documents cannot
be fetched until the operator settles which call the 2025 submission was evaluated under. Every
2025-side citation in the matrix is addressed to a call identified by declaration.

**The evaluation form carries seven rows.** If the 2025 form differs from the stored V2.2 in its level
descriptions, its score resolution, its tag grammar or its criterion-to-aspect assignment, three
numbers move and the comparison with 85.80 compares two decompositions. EI-02 records that the version in force is unknown
and that whether the stored form's date precedes the 2025 evaluation is itself unrecorded.

**The matrix quotes the 2025 figures.** It sits in `docs/tier4_orchestration_state/msca_dn/`, outside
the dev-graph root at `workspaces/msca_dn/`, so no snapshot reads it and it cannot reach an evidence
pack. That is the position the ESR record already holds under specification decision 12, and the blind
lane's isolation rests on that exclusion plus the assessor running with no tools from a working
directory outside the repository. A test asserts the path, and the matrix declares the reasoning in its
own `isolation_note`. V10 inherits a sharper constraint: the historical profile lives in
`harness/profiles/`, which the assessor path does read, so it may cite a matrix row and must not carry
a 2025 score.

**Two claims are inclusions, not equalities.** AM-01 settles that every cross-reference the 2026
mapping routes on is in the 2025 form. A 2025 cross-reference the mapping has no row for would not
have been seen, and cannot be searched for without the 2025 mapping's own list. SM-01's anchor
comparison bounds what such a sentence could reroute, and the matrix carries the residual as an
uncertainty.

**Completeness within an area is this author's judgement.** The check reads what each row cites and
refuses an unsourced relation. It cannot report a scoring-relevant rule nobody wrote a row for, and
the matrix says so.

**No row has ever been authenticated.** The `issuer_hash_confirmed` path and the `Confirmed` status it
permits are covered by synthetic cases only. Exercising them needs a hash this repository does not
hold.

## 10. Artifacts

| Path | What it is |
|---|---|
| `harness/authority_matrix.py` | the vocabulary, the loaders, the check and both renderings |
| `harness/commands/authority_matrix.py` | the command that checks a matrix and writes its readings |
| `harness/record_pointer.py` | the shared pointer grammar, extracted from the deferral register |
| `harness/record_binding.py` | the shared source-role vocabulary and byte-binding check, extracted the same way |
| `tools/author_msca_dn_authority_matrix.py` | the deterministic deriver, with a byte-equal replay |
| `docs/…/msca_dn/authority/authority_source_index_2026-10-12.json` + `.md` | the index and its reading |
| `docs/…/msca_dn/authority/equivalence_matrix_2025_2026-10-12.json` + `.md` | the matrix and its reading |
| `docs/…/decision_log/msca-dn-authority-matrix_2026-10-12.json` | the decision record |
| `harness/acceptance_lanes/msca_dn_historical.json` | the lane's new `authority` area |
| `harness/ACCEPTANCE_LANE.md` | sixteen areas, the new one documented |
| `harness/HARNESS.md` | the matrix's section and its row in the module table |
| `tests/harness/test_authority_matrix.py` | 65 checks on the loaders, the check, the renderings and the command |
| `tests/test_msca_dn_authority_matrix.py` | 53 checks reconciling the committed artifacts |
| `docs/…/declarations/draft_sanitised_v1.json` + `review_checklist.md` | re-rendered; three dependent rows added |
| `docs/…/decision_log/msca-dn-declaration-draft-rerender_2026-10-12.json` | the successor re-render record |
| `tests/test_msca_dn_declaration_drafts.py` | the re-render test reads the record series |
