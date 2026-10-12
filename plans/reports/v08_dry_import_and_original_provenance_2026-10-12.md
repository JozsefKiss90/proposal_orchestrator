# V08 — Dry-import inventory and original-provenance records

Date: 2026-10-12
Branch: `msca-dn-pre-eval`
Ticket: V08 of `plans/msca_dn_historical_validation_tickets.md`
Gate: G2. Closes the review half of F02 of `plans/reports/MSCA_DN_Readiness_Audit_2026-10-08.md`.
With V07's code half, F02 closes.
Procedure: `plans/msca_dn_v08_original_dry_import_procedure.md`
Decision record: `docs/tier4_orchestration_state/decision_log/msca-dn-dry-import-and-original-provenance_2026-10-12.json`

## What the problem was

Extraction accounting is not semantic fidelity. A balanced non-whitespace character count says one
thing: the importer dropped no character of the text it could see. It says nothing about reading order,
cell association, mathematical meaning, image content or figure completeness. A deficit on one page can
also offset a surplus on another inside a total.

Two zeros make this concrete. A Gantt chart drawn as vector paths is not an embedded image and carries
no characters. So a document whose figures are intact and a document whose figures were stripped both
measure zero embedded images and zero character loss.

The sanitised copy's derived half records both zeros. Its figures really are gone — but the operator's
PE-01 declaration established that, not the measurement. Reading either zero as preservation would turn
a measurement that cannot discriminate into evidence that it did.

## What was built

| Component | What it is |
|---|---|
| `runner/dry_import.py` | The measurement. Takes a PDF and nothing else; writes nothing. |
| `tools/dry_import_original.py` | The operator's CLI, the records, the worksheet and the refusals. |
| `plans/msca_dn_v08_original_dry_import_procedure.md` | The procedure for the real original. |
| `DRY_IMPORT_REQUIRED_FIELDS` | A weaker precondition than an import, on `DocumentConfig`. |

A dry import is deliberately weaker than an import. It declares no page map, because the page map is
what it exists to establish. It needs no graph root, because it writes flat files into a directory the
operator names. It checks the page count against no expected value, because finding the count out is
the point.

So `official_original` is measurable and still not importable. `require_dry_importable()` asks for the
ten identity fields; `require_complete()` still refuses the import and names `workspace_rel`,
`sub_sections`, `expected_pages`, `body_point_size` and `revisions`.

## The six acceptance criteria

**1. A dry-import mode, without graph state.** `measure(pdf)` returns the inventory. It carries the
authenticated hash, the measured page count and its basis, and one row per page. It carries the table
inventory with every header row, the graphical census and the candidate section headings. It carries
the point-size distribution, the citation marker counts, the character accounting and the extraction
limitations.

The CLI writes six files into `--out`:

| File | What it holds |
|---|---|
| `dry_import_inventory.json` | the measurement |
| `reconciliation_worksheet.md` | the same measurement as tables to work through against the PDF |
| `<intake_id>.json` | the document's own ESR intake record |
| `original_document_provenance.json` | which file, which bytes, which environment, where it is kept |
| `extraction_fidelity_acceptance.json` | seven classes of evidence, every one unreconciled |
| `unresolved_extraction_limitations.json` | six limitations, every one Unresolved |

No document record, no source index, no snapshot, no intake directory. Nothing the run produces can be
read as an imported document.

The page map is offered, never inferred. `heading_candidates()` lists every prose block that opens with
a number and a full stop, with its marker, its pages and its text. `section_map.declared` is `false`.
Inferring a map from the candidates would be the project fact §13.3 forbids.

**2. Two records, and an authenticated hash.** The intake record holds what is known about the
submission: its id, its call, whether a prior submission exists, ESR availability and the purpose an
ESR may serve. The provenance record holds the document's own provenance.

The provenance record names the separation rather than leaving a reader to notice it. The sanitised
copy's intake carries its sanitisation provenance inside `esr_reference`, so one field answers two
questions. This pair does not.

The hash is authenticated and not merely computed. `--expect-sha256` is the hash the operator took from
the authoritative source, and the run refuses — writing nothing — unless the file hashes to it:

```
refused: fixture_part_b.pdf hashes to 7f3c…, and the operator declared 0000…. This is not the
authenticated file; nothing was written.
```

A hash the tool computed from an unauthenticated file would say only that some file was read.

**3. Seven classes of evidence, each explicit.** `gantt_chart`, `diagrams`, `embedded_images`,
`footnotes`, `table_headers`, `bibliographic_references`, `supporting_part_b_material`. Each item
carries what must be reconciled, the measurement that bears on it, and why that measurement does not
settle it. Every item starts `unreconciled` and the record is not `complete`.

`check_acceptance` reports `item_missing` for a class the record does not name, so an item cannot be
dropped and left unreconciled by omission.

**4. Neither zero is proof.** `MEASUREMENT_ONLY_BASES` names five bases:

`zero_character_loss`, `zero_embedded_images`, `character_accounting`, `extraction_accounting`,
`balanced_page_accounting`.

`check_acceptance` reports `measurement_basis_not_proof` when one stands behind a `preserved` or
`partly_lost` verdict. The asymmetry is deliberate: a measurement may stand behind `lost`, because an
absence can be measured. Presence has to be looked at.

The basis vocabulary is closed, `ACCEPTANCE_BASES`, and a basis outside it is an `unknown_basis`
finding. Free text would let a measurement in under a wording of its own: a set-membership test alone
admits `basis: "no characters were lost"`. The admissible half is four operator bases, each of which
rests on something a measurement cannot supply.

The rule is reachable. `py -3.10 -m tools.dry_import_original --check-acceptance <record>` prints every
finding and exits 1 on any, and it needs no PDF. A rule reachable only by pasting a Python expression
is a rule nobody runs.

The fixture carries the case, measured rather than argued. A Gantt-shaped vector figure, a vector table:
zero embedded images on every page, zero character loss on every page, and graphical evidence on both.

`GRAPHICAL_PROOF_STATEMENT` travels with the records. It appears in the inventory's figure block, in the
acceptance record's rule, in the limitations record, and in the worksheet beside the two zeros it is
about.

**5. Limitations recorded before assessment.** Six rows, every one `Unresolved`. Ligatures, prose below
the largest point size, and table cells outside the page reading order. Graphical evidence absent from
the extracted text, no declared page map, and citation markers counted rather than resolved.

The record carries the span statement verbatim:

> A page reference or a source span locates an assertion in the extracted text. It does not corroborate
> it. The span says where the sentence sits; it says nothing about whether the sentence is true, whether
> the evidence it names exists, or whether a figure the sentence points at survived extraction.

The record is written by the dry import, which precedes the import and therefore every result over the
document. Its `recorded_when` says so.

**6. Nothing private reaches this repository.** For a document declared as the submitted text, the tool
refuses a PDF path or an output path that resolves inside the repository, and writes nothing.
`official_original.workspace_rel` is still undeclared.

The provenance record's two storage flags are measured from the paths the run was given, not declared
from the document's role. For the submitted text both are false, because the run refuses otherwise.

What counts as inside the repository is not an argument. `THIS_REPOSITORY` resolves from the module's
own location, so no flag moves it. A caller-supplied root would let an operator point the check at an
empty directory, write the derived text here anyway, and have the record state that nothing was stored
here. The working directory is not the answer either: the tool runs from the private network, where
there is no repository to walk up to.

Tests assert that no intake record and no document record for the original is committed, and that the
procedure document carries no 64-digit hex string and no path into the private network.

## Checks run

| Suite | Result |
|---|---|
| `tests/runner/test_dry_import.py` | 52 passed (new) |
| `tests/test_msca_dn_dry_import.py` | 57 passed (new) |
| `tests/test_msca_dn_import.py` | 145 passed |
| `tests/test_msca_dn_workspace.py` | 21 passed |
| `tests/test_msca_dn_fidelity_declarations.py` | 50 passed |
| `tests/test_msca_dn_declaration_drafts.py` | 76 passed |
| `tests/test_extraction_environment.py` | 29 passed |
| `tests/runner/test_agnosticism_lint.py` | 27 passed |
| `tests/harness/test_acceptance_lane.py` | 68 passed |
| `tests/harness/test_integrity_audit.py` | 126 passed |
| Adjacent total | 474 passed in 276s |
| New total | 109 passed |

`py -3.10 -m tools.import_external_proposal --check` exits 0: both sanitised revisions still reproduce
byte-equal. `py -3.10 -m tools.author_msca_dn_workspace --check` exits 0.

`py -3.10 -m harness.commands.acceptance_lane` reports **GREEN**: 2,570 passed, 0 failed, 0 errors, 17
declared exclusions. The environment is on the pin and reproduces the committed import artifacts.

`mypy -m runner.dry_import -m tools.dry_import_original -m tools.import_external_proposal` reports 9
errors, all in `runner/source_index.py` and `runner/dev_graph/documents.py`. Neither file is touched
here, so all 9 are pre-existing and are the same 9 V07 recorded.

### The full suite, against a measured baseline

The repository suite is not green on this branch and was not green before this change. The baseline was
measured in a `git worktree` at HEAD, with the gitignored `.env` copied in.

| Run | Failed | Passed | Skipped |
|---|---|---|---|
| HEAD in a worktree | 205 | 7,199 | 107 |
| This change | 194 | 7,340 | 86 |

Set comparison of the two failure lists: **no test fails here that passes at HEAD.** Eleven tests fail
at HEAD and pass here, all byte-binding checks in the demo and deferral-register modules, which a fresh
worktree checkout renders differently. That accounts for the 205 against 194, and for the skipped
counts.

One test did regress mid-change and was fixed:
`test_acceptance_lane.py::TestAreas::test_the_lane_covers_every_module_of_the_audits_focused_command`,
which is V03's own guard against a focused-command module nobody assigned. The lane now declares the
area.

## Preserved bindings

| Binding | State |
|---|---|
| `@bdb8670f6987e4db`, `@b51a103520b58ded` | Reproduced from the PDFs, unchanged |
| Both import manifests, both fidelity registers, the source index | Byte-identical; both `--check` exit 0 |
| `preflight_242f1afb02c8_0001.json` and its manifest pin | Untouched |
| The frozen 74.60 baseline and its freeze record | Untouched |
| The approval records, approved dispositions, comparison, revision plan | Untouched |
| The committed integrity audits and the open-deferral register | Untouched |
| `PageExtract` and `versions()` | Unchanged; the graphical census opens the PDF itself |

The graphical census reads images and vector drawings from the PDF rather than from a `PageExtract`,
so no byte-bound rendering was touched to get them.

The acceptance lane gained an area. `tests/harness/test_acceptance_lane.py` refuses a test module
inside the audit's focused command and outside every area, which is what a new `tests/test_msca_dn*.py`
module is. So the lane declares a `dry_import` area over both new modules, and `tests/runner/`'s one is
registered as a module added beyond the focused command. The area is marked not depended on by the
historical run: Stage A reads the sanitised copy.

Two documentation files changed. `harness/HARNESS.md` gains the dry-import section.

`workspaces/msca_dn/README.md` gains three lines, written through its renderer. They say that the
submitted original is not in the graph root, and how it is measured instead. `--check` exits 0
after, and the file's line endings are unchanged.

## What is unresolved

**1. The candidate heading rule is a numbering convention.** `heading_candidates()` matches a leading
`<digits>.` with optional dotted parts. A sub-section the original opens without a number — as
sub-sections 1.1 and 8 of the copy do — is not a candidate, and the operator finds it by reading. The
output is a candidate list and never a map, so a missed candidate costs reading rather than producing a
wrong boundary. Owner: the operator reconciling the worksheet.

**2. The acceptance catalogue is fixed at seven items.** They are the ticket's seven. A document
carrying a class none of them names needs a catalogue entry, which is a code change and a test. A
free-text item would let an operator rename a class and lose the check that every named class is
present.

**3. `supporting_part_b_material` cannot be measured for absence.** The inventory measures the pages it
was given. A page nobody supplied is not reported missing, because there is no count to compare
against. The item says so in its own text and stays the operator's.

**4. The graphical census depends on the PyMuPDF build.** `get_drawings()` and `get_images()` are
MuPDF's. The inventory records the measured build, the pin and whether the build is on it, so a count
is read with its environment. No count is bound by hash anywhere, so an off-pin build costs a different
number rather than a broken replay.

**5. The fixture cannot carry a ligature.** Base-14 Helvetica cannot encode U+FB01, so the fixture PDF
holds none and the inventory reports none. The ligature counting is exercised against a `PageExtract`
the test wrote instead, and the test says why.

**6. The declared document id is double entry.** The intake record owns the document id for an imported
document. The configuration declares it as well. A dry import needs it, to author an intake record for
a document that has none. `_document_id()` refuses a drift between the two, and a test holds the copy's
declaration equal to its recorded id. That is what keeps the duplication safe.

**7. Nothing consumes the acceptance record yet.** The operator checks it with `--check-acceptance`,
which measures nothing and exits 1 on a finding. Nothing else reads it. The consumer that should gate
on it is the import of the original, and that cannot run until a page map is declared, so an
inadmissible `preserved` verdict is reported and blocks nothing elsewhere. Owner: whoever imports the
original, which is after V08.

## Declared deviations

- **The records are written outside this repository.** Criterion 2 says the intake and provenance
  records exist. They do not exist here, and the reason is not that criterion 6 forbids them: a sha256
  and an intake record are neither the original PDF nor text derived from it, and this repository
  already commits PDF hashes elsewhere. The reason is that the document they describe is not here. The
  authenticated hash is the operator's, taken from the authoritative source, and authoring either
  record now would mean inventing it (§13.3). The ticket's own verification says so — *the operator
  performs the real dry import* — so what is committed is the deterministic builder of each record,
  exercised against a fixture, plus the procedure. Criterion 6 then keeps the derived text out once the
  operator runs it.
- **`--inventory-only` is an addition.** The ticket names one dry-import mode; this one writes the
  inventory and the worksheet and no provenance record, so a document can be measured before its
  submission identifiers are settled.
- **The importer's field count moved and V07's accepted text was not edited.** `DocumentConfig` gains
  `document_id`, so it carries 27 fields where V07's accepted status paragraph says 26. The required
  count is unchanged at 15: an import still reads the document id from the intake record, which is
  authoritative, so the declaration is required for a dry import alone. No word of V07's accepted text
  was changed.
- **A fifth file was added.** The ticket names the inventory and three records. The reconciliation
  worksheet renders the inventory as tables, because criterion 1's inventory is one "to reconcile
  against the PDF" and JSON is not what a reconciliation is done against.
- **The limitations are their own record.** Criterion 5 asks that they be recorded before assessment.
  They are, in `unresolved_extraction_limitations.json`, rather than as a block inside the provenance
  record, so a later reader of a span finds the span statement in the record that is about limitations.
- **The path refusal is scoped to the submitted document.** Criterion 6 is about the private original,
  so the refusal fires when `is_submitted_document` is true. A dry import of the committed sanitised
  copy is not refused for being in the repository, because that rule is not about it.
- **V08's residuals are not rows in the open-deferral register.** That register's declared scope is the
  deferrals of the operator approval of 2026-10-08, and its own rule is that a correction to it is a
  successor register, never an edit. These arose after it. Whether they join a successor register is
  the operator's call.

## Not evidence of

- An imported, assessed or frozen original. No original PDF is stored here, no page map for it is
  declared, and its intake record does not exist.
- A measured original. The fixture is a two-page PDF this test suite writes. Every number in it is the
  fixture's.
- A reconciled fidelity acceptance. Every item starts unreconciled, and the record refuses to call
  itself complete while one is.
- A resolved extraction limitation. Six rows stand Unresolved, and listing one resolves nothing.
- An assessor run. None was invoked and no quota was spent.
- A validated 2025 baseline. V09 and V10 own the 2025 sources and the historical profile.
- A corrected PE-09 runbook. V12 owns that and stays blocked by V10 as well.
- A closed V01 criterion 4. The runtime-environment block still reaches no committed manifest, and V08
  did not change its shape.
