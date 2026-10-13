# Operator procedure — dry import of the original Part B (V08)

Ticket: V08 of `plans/msca_dn_historical_validation_tickets.md`.
Gate: G2. Closes the review half of F02 of `plans/reports/MSCA_DN_Readiness_Audit_2026-10-08.md`.
Tool: `tools/dry_import_original.py`, on the measurement in `runner/dry_import.py`.

**This procedure has not been run in this repository.** No original PDF is stored here, no page map
for it is declared, and its intake record does not exist. The real dry import is the operator's, and
it runs inside the private network. What is built and tested here is the machinery, exercised against
a non-sensitive fixture in `tests/test_msca_dn_dry_import.py`.

## Why a dry import comes first

Extraction accounting is not semantic fidelity. A balanced character count says that the importer
dropped no character of the text it could see. It says nothing about reading order, cell association,
mathematical meaning, image content or figure completeness. A deficit on one page can also offset a
surplus on another inside a total.

Two zeros make this concrete. A Gantt chart drawn as vector paths is not an embedded image and carries
no characters. So a document whose figures are intact and a document whose figures are gone both
measure zero embedded images and zero character loss. Neither zero is evidence of preservation, and
`runner/dry_import.py` refuses to let one stand behind a `preserved` verdict.

## Before you start

1. Work inside the private network, in a directory outside this repository. The tool refuses a PDF
   path or an output path that resolves inside the repository when the selected document is the
   submitted text.
2. Take the sha256 of the Part B from the authoritative source: the submission system's own record, or
   the archived file whose integrity you already trust. Do not take it from the copy you are about to
   measure.
3. Check the extraction environment. `py -3.10 -m tools.import_external_proposal --environment` prints
   the measured build against the pin in `runner/extraction_environment.py`. An off-pin MuPDF build
   changes the paragraph stream, so the inventory records the build it was measured under.
4. Have the proposal number and the 2025 call id to hand. Neither is derivable from the PDF, so the
   tool takes both as declarations and defaults neither. The call id stays Assumed until V09 pins the
   2025 sources.

## Step 1 — run the dry import

```
py -3.10 -m tools.dry_import_original \
    --pdf <private>/part_b_as_submitted.pdf \
    --expect-sha256 <hash from the authoritative source> \
    --out <private>/v08_dry_import \
    --submission-id <the proposal number> \
    --call-id <the 2025 call id>
```

The default `--document` is `official_original`. Add `--prior-submission`, `--esr-availability` and
`--esr-reference` if the intake record should carry them; availability is declared and never inferred,
and `available` needs a reference.

To measure without authoring an intake record, add `--inventory-only`. That writes the inventory and
the worksheet alone.

The run refuses, and writes nothing, when:

| Refusal | Cause |
|---|---|
| `is not a sha256` | `--expect-sha256` is not 64 lower-case hex digits |
| `hashes to … and the operator declared …` | the file is not the authenticated one |
| `resolves inside this repository` | the PDF or the output directory is in the repository |
| `cannot be measured: … not declared` | the document configuration lacks an identity field |

## Step 2 — what it writes

Six files, into `--out`:

| File | What it holds |
|---|---|
| `dry_import_inventory.json` | the measurement: page count, per-page accounting, tables and headers, the graphical census, candidate section headings, extraction limitations |
| `reconciliation_worksheet.md` | the same measurement as tables to work through against the PDF |
| `msca-dn-2025-original.json` | the document's own ESR intake record, under the intake schema |
| `original_document_provenance.json` | which file, which authenticated bytes, which environment, and that nothing is stored in the repository |
| `extraction_fidelity_acceptance.json` | the seven classes of evidence, every one `unreconciled` |
| `unresolved_extraction_limitations.json` | what the extraction loses, every row `Unresolved` |

No graph state is written. There is no document record, no source index, no snapshot and no intake
directory, so nothing the run produces can be read as an imported document.

## Step 3 — reconcile the worksheet against the PDF

Open `reconciliation_worksheet.md` beside the document. Work through it page by page.

- **Pages.** Confirm the page count, and that each page's character count is plausible for what you
  see. A page of mostly figure with a low character count is the expected shape, not a fault.
- **Candidate section headings.** The tool lists every block that opens with a number and a full stop.
  Mark which ones are sub-section openings. This is the page map, and the import refuses until it is
  declared.
- **Tables.** Check each table's header row, and that the data rows below it still associate with the
  header cell above them. A row that parses into the right number of cells can still carry the cells
  in the wrong order.
- **Graphical evidence.** Count the figures on the page yourself. Compare your count with the embedded
  image and vector drawing counts. A mismatch is the finding; the measurement alone is not.

## Step 4 — fill in the fidelity acceptance record

`extraction_fidelity_acceptance.json` carries one item per class of evidence:

`gantt_chart`, `diagrams`, `embedded_images`, `footnotes`, `table_headers`,
`bibliographic_references`, `supporting_part_b_material`.

Each starts `unreconciled`. For each one, set `verdict`, `basis`, `reconciled_by`, `reconciled_on` and
a `note` saying what you compared. Then set `complete` to `true` only when no item is still
unreconciled.

Verdicts: `preserved`, `partly_lost`, `lost`, `not_applicable`.

The basis vocabulary is closed, and a basis outside it is refused. Free text would let a measurement in
under a wording of its own.

| Basis | Admissible for |
|---|---|
| `operator_visual_comparison` | any verdict; you compared the page against the PDF |
| `operator_page_by_page_check` | any verdict; you went through every page |
| `operator_declaration` | any verdict; you state a fact about the document |
| `not_present_in_this_document` | any verdict; the class does not occur here |
| `zero_character_loss`, `zero_embedded_images`, `character_accounting`, `extraction_accounting`, `balanced_page_accounting` | `lost` and `not_applicable` only |

A measurement may stand behind `lost`, because an absence can be measured. It may not stand behind
`preserved` or `partly_lost`. Presence has to be looked at. Name the pages you compared in the note.

Validate what you filled in:

```
py -3.10 -m tools.dry_import_original \
    --check-acceptance <private>/v08_dry_import/extraction_fidelity_acceptance.json
```

It measures nothing, writes nothing, and needs no PDF. Exit 0 and *admissible as it stands* means the
record holds. Otherwise every finding is printed and the exit status is 1. The codes are
`item_missing`, `unknown_item`, `unknown_verdict`, `verdict_without_attestation`, `unknown_basis`,
`measurement_basis_not_proof` and `complete_with_unreconciled_item`.

Set `complete` to `true` once every class carries a verdict. The register of the submitted document
reads this record and will not be written while an item is still `unreconciled`, or while a
`preserved` verdict rests on a measurement (V18). So an inadmissible record blocks the import rather
than only being reported here.

## Step 5 — declare the configuration, in the private network (V17)

The page map you reconciled is a fact about a document this repository does not hold, so it is
declared where that document is. Copy `tools/original_configuration_template.json` to the private
root and answer every angle-bracketed value. Nothing about the original is declared in this
repository, and the committed copy of the template is refused as a configuration: it sits inside the
repository, and a placeholder is not a declaration.

What the form asks for, beyond the five fields the importer names:

| Field | What to answer |
|---|---|
| `authenticated_sha256` | the hash from Step 1, so the import cannot read a file you did not authenticate |
| `measurement` | the inventory's path and its own sha256, so the declaration is bound to one measurement |
| `dry_import_dir` | where the V08 records sit, so the register can bind each by hash |
| `workspace_rel` | the private graph root, relative to the private root |
| `declarations_dir_rel` | where your per-sub-section declarations will live |
| `pages_outside_the_map` | every page no sub-section covers, each with a basis |
| `dn_type` | the network type and the page that states it, or `null` to leave it Unresolved |

Then author the graph root. The tool writes the README, records the intake, and creates the
dev-graph directories the importer needs:

```
py -3.10 -m tools.author_original_workspace --root <private root> --config-input <configuration input relative to that root>
```

It refuses a root that resolves inside this repository, and a configuration input that sits outside
the private root. It re-reads the dry import's inventory and reports every declared value that
disagrees with it, writing nothing. The intake record is the one the dry import authored: it is
recorded into the graph root rather than re-declared, so the proposal number is declared once.

## Step 6 — import the original (V17, V18)

```
py -3.10 -m tools.import_external_proposal --document official_original --config-input <configuration input> --repo-root <private root>
```

This writes the page sources, the document record, the import manifest and the fidelity register,
all under the private root. The register is the submitted document's own (V18). It declares that
nothing stands between the submission and the text assessed. It also says, in so many words, that
this is not a claim the extraction preserved everything. Its declared half asks for a `presence` and an
`extraction_fidelity` per sub-section, under a record type of its own.

Both tools have a `--check` that exits 1 if any file they own would change, so the import replays
byte-equal. The copy's configuration cannot be redeclared through an input: its manifests are bound
by hash into the frozen baseline.

## Step 7 — what is still not done

- The grounding axis. A claim this document carries is extracted, counted and never resolved to a
  source: the imported-source route is ticket X01. Until it lands, no cell may declare
  `source_grounded`.
- The 2025 profile is `harness/profiles/msca_dn_2025_historical.json` (V10). A result over the
  original scored under `msca_dn_2026_default.json` would score a historical submission by a later
  year's configuration.
- The readiness receipt (V13) is validated before the run, in the private network, by
  `py -3.10 -m harness.commands.execution_receipt`.
- Nothing in this procedure authorises the run. What may be sent and what may leave are the private
  environment's rules, and `plans/msca_dn_pe09_runbook.md` §10 states none of them.

## What a span buys

The limitations record carries this statement, and it governs every later reading of the extracted
text:

> A page reference or a source span locates an assertion in the extracted text. It does not corroborate
> it. The span says where the sentence sits; it says nothing about whether the sentence is true,
> whether the evidence it names exists, or whether a figure the sentence points at survived extraction.
