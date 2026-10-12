# V07 — Externalise the document configuration

Date: 2026-10-12
Branch: `msca-dn-pre-eval`
Ticket: V07 of `plans/msca_dn_historical_validation_tickets.md`
Gate: G2. Closes the code half of F02 of `plans/reports/MSCA_DN_Readiness_Audit_2026-10-08.md`.
Decision record: `docs/tier4_orchestration_state/decision_log/msca-dn-document-configuration_2026-10-12.json`

## What the problem was

The import wrapper's extraction substrate is generic. Its application layer was not. Nine module
constants and four typed values described one document: a sanitised derivative of 84 pages, with that
copy's page map, source-id prefix, intake and description.

| Assumption | Where it was |
|---|---|
| `DOCUMENT_TITLE`, `EXPECTED_PAGES`, `SOURCE_ID_FORMAT` | module constants |
| `SECTIONS`, `SUB_SECTIONS`, `CRITERION_HEADING_MARKERS`, `MARKER_PAGE_TOLERANCE` | module constants |
| `BODY_POINT_SIZE`, `WP_HEADER_LABELS` | module constants |
| Workspace location, intake id | aliases of the workspace tool's constants |
| `is_submitted_document: false` | typed at three sites in the importer, one in the workspace tool |
| The beneficiary marker `Beneficiary A` | an entry of `SUB_SECTIONS` |

Importing the official original meant editing those constants. That edit would have reinterpreted the
committed copy, whose document record, page texts and spans are historical evidence.

## What was built

A `DocumentConfig` record above the existing `Revision`. It carries 26 fields, 15 of them required, one
of which is a four-field `WorkPackageLayout`. `Revision` keeps only what is per-PDF: the file, the
source-id prefix, the manifest name, the register, the role and version strings, an optional page count
of its own, and what it supersedes.

Two documents are declared. `sanitised_derivative` is the copy PE-03 imported, with both of its
revisions. `official_original` is the submitted text. `--document` selects one. `--describe` prints the
selected document's identity and writes nothing.

A configuration is selected, never merged. Nothing is inherited from another document's configuration.
An undeclared required field is missing, and `require_complete()` refuses the import naming every
missing field.

## The five acceptance criteria

**1. Every assumption is configuration.** The nine constants are retired. So are the six aliases that
bound one document's workspace, intake, register, scorecard and revisions to module scope. A test
asserts the module carries none of the fifteen names.

The workspace location, intake id, title, page count, section and sub-section maps, criterion anchors,
marker tolerance, beneficiary marker, source-id template and submitted-document flag are fields of the
selected configuration. The committed manifests, source index and registers read the flag and the title
from it rather than from a literal.

Four more assumptions moved with them, beyond the ticket's list. The body point size. The work-package
table layout: its sub-section, its labels, the three labels the register's provenance header declares,
and the consequence of a collapsed header. The two sentences a source record uses to say what the
document and each page are. The ticket's own problem statement names table interpretation among what the
original must establish itself.

**2. The original has its own identity and role.** `official_original` declares its own config id,
title, role, intake id, short name, page statement, reader caveat and manifest key vocabulary. It
renders `is_submitted_document: true`. It declares no page map, no page count, no body point size, no
work-package layout and no revisions. A test asserts that the words *sanitised*, *derivative* and *84*
appear in none of its identity or description fields.

Its graph root is deliberately undeclared. The original and the text extracted from it stay in the
private network and are not committed here (V08). An in-repository graph root declared now would invite
exactly that commit.

**3. The original is not a descendant of the copy.** Its intake id differs, so its document id does. Its
graph root differs, so its page texts cannot resolve as the copy's. `__post_init__` refuses a revision
whose `supersedes` names a revision of another document. The registry refuses any collision of config
id, intake id, graph root or revision id between documents.

**4. Both sanitised configurations reproduce byte-equal.**

| Check | Result |
|---|---|
| `py -3.10 -m tools.import_external_proposal --check` | exit 0, up to date |
| `py -3.10 -m tools.author_msca_dn_workspace --check` | exit 0, up to date |
| `render_all(REPO, SANITISED_DERIVATIVE)` vs `render_all(REPO)` | equal |
| Every rendered file vs the committed bytes | equal |
| Either committed manifest gaining a field | none |

**5. A configuration missing a required field fails closed.** `missing_fields()` returns the undeclared
required fields in field order and `require_complete()` names them all in its refusal.

```
$ py -3.10 -m tools.import_external_proposal --document official_original --check
refused: document 'official_original' cannot be imported: workspace_rel, sub_sections,
expected_pages, body_point_size, revisions not declared. Nothing is inherited from another
document's configuration, so each is declared from this document itself.
```

`require_provenance()` refuses separately, and names the intake record rather than the undeclared path
field, because what is missing is the document's provenance:

```
document 'official_original' has no provenance of its own: its intake record
msca-dn-2025-original.json has no graph root to be read from, because workspace_rel is not declared.
```

The ticket's verification is that pair of refusals.

## The V01 carry

V01's criterion 4 asked for the runtime versions in the import manifest and could not have them. Both
manifests are bound by hash into the frozen 74.60 baseline. Writing the block there would have rewritten
four artifacts the milestone holds immutable. The carry named V07.

`manifest_records_runtime_environment` is now a configuration flag. It is false for the copy, so
`_runtime_environment_block()` returns an empty mapping and no bound manifest changes. It is true for the
original, where the block carries `PINNED_PYMUPDF`, `PINNED_MUPDF`, `MEASURED_PYTHON` and the decision
record path. The values are the declared pin, never a measurement of the writing machine.

What this is not: the pin recorded in a file. The flag is true only on a configuration that
`require_complete()` refuses, so the block reaches no manifest and is exercised by a unit call alone. It
also fixes a shape V08 may want to change. **V01's criterion 4 stays open and is the operator's.**

## Checks run

| Suite | HEAD | After |
|---|---|---|
| `tests/test_msca_dn_import.py` | 99 passed | 145 passed |
| `tests/test_msca_dn_workspace.py` | 21 passed | 21 passed |
| `tests/test_msca_dn_fidelity_declarations.py` | 50 passed | 50 passed |
| `tests/test_msca_dn_declaration_drafts.py` | 76 passed | 76 passed |
| `tests/test_extraction_environment.py` | 29 passed | 29 passed |
| `tests/harness/test_integrity_audit.py` | 126 passed | 126 passed |
| Total | 401 passed | 447 passed |

The 46 new tests are `TestDocumentConfiguration`, one group per acceptance criterion.

`mypy -m tools.import_external_proposal -m tools.author_msca_dn_workspace -m
tools.draft_fidelity_declarations` reports 9 errors, all in `runner/source_index.py` and
`runner/dev_graph/documents.py`. Neither file is touched by this change, so all 9 are pre-existing.

### The full suite, against a measured baseline

The repository suite is not green on this branch and was not green before this change. The baseline was
measured in a `git worktree` at HEAD, with the gitignored `.env` copied in.

| Run | Failed | Passed | Skipped |
|---|---|---|---|
| HEAD in a worktree | 205 | 7,153 | 107 |
| This change | 194 | 7,231 | 86 |

Set comparison of the two failure lists: **no test fails here that passes at HEAD.** Eleven tests fail
at HEAD and pass here, all of them byte-binding checks in the demo and deferral-register modules, which
a fresh worktree checkout renders differently. That accounts for the 205 against 194, and for the
skipped counts.

The failures are concentrated in `tests/runner/` and `tests/test_transport_*`: the skill runtime, the
phase artifact-production modules and the transport presets. The largest groups are
`test_skill_runtime.py` with 41, `test_phase6_field_production.py` with 18 and
`test_output_contract_routing.py` with 18. None touches the importer, the workspace tool or the MSCA-DN
records.

## Preserved bindings

| Binding | State |
|---|---|
| `@bdb8670f6987e4db`, `@b51a103520b58ded` | Reproduced from the PDFs, unchanged |
| Both import manifests, both fidelity registers, the source index | Byte-identical; both `--check` exit 0 |
| `preflight_242f1afb02c8_0001.json` and its manifest pin | Untouched |
| The frozen 74.60 baseline and its freeze record | Untouched |
| The approval records, approved dispositions, comparison, revision plan | Untouched |
| The committed integrity audits and the open-deferral register | Untouched |
| `.gitattributes` line-ending protections | Unchanged |

One artifact changed: `workspaces/msca_dn/README.md` gains two sentences, written through its renderer.
Its page-id span is now derived from the configuration and reproduces the committed line byte for byte.
The file is under a `-text` tree; its line endings were preserved, and its diff is three added lines.

## What is unresolved

**1. Two manifest key names are configuration rather than renamed.**
`not_the_submitted_text` and `is_the_first_sanitised_derivative` carry the derivative's vocabulary. Both
appear in manifests bound by hash, so neither can be renamed. Each is a required configuration field
instead, declaring nothing by default, and the original declares `the_submitted_text_itself` and
`is_the_first_version_of_the_original`. A reader of the copy's manifests still sees the old names, which
is what keeps them replayable. Owner: whoever retires those manifests, if anyone ever does.

**2. The register's provenance header is still the copy's.** It declares a sanitisation, a transformation
and a reflow — the copy's facts. `render_register` now refuses a submitted document rather than labelling
the original with them, so the original has no register renderer. V08 owns its provenance records.

**3. The candidate role sentence is declared twice.** The workspace tool's `INPUTS` holds the candidate
row's role and the configuration holds the document's. The workspace tool cannot import the
configuration at module scope, because the importer imports the workspace tool. A test holds the two
equal, so a drift fails rather than producing a register that describes a document the importer does not
import.

**4. Nothing about the original is Confirmed.** Its title, role, short name, page statement and reader
caveat are operator declarations about a document this repository does not hold. The configuration says
so: `declared_status` is `Assumed` and `status_note` states which values a measurement settles. For the
copy that note names the page count, the body point size, the work-package layout and every start page,
each re-derived from the PDF. For the original it names none, because none exists yet.

**5. The runtime-environment block reaches no file.** See *The V01 carry*. V01's criterion 4 stays open.

## Declared deviations

- **`source_id_template` and `criterion_heading_markers` are not required.** The spelling of a page id is
  generic rather than a fact about one document, so the template keeps a module default and stays
  overridable. A document may legitimately carry no criterion-level heading, so the empty tuple is a
  declaration and demanding a non-empty one would refuse without cause.
- **`scorecard_rel` is required conditionally.** Only a sub-section the document carries no heading block
  for, and declares no title for, takes its title from the application form. One predicate,
  `needs_form_title()`, decides that for both `missing_fields()` and `build_import`, so the two cannot
  disagree about which shapes need a scorecard.
- **One blank line was inserted into V04's accepted Status paragraph** in the ticket ledger, to split a
  seven-sentence paragraph the prose linter rejects. No word of that accepted text changed.
- **V07's residuals are not rows in the open-deferral register.** That register's declared scope is the
  deferrals of the operator approval of 2026-10-08, and its own rule is that a correction to it is a
  successor register, never an edit. These five arose after it. They live in this report and in the
  decision record, and whether they join a successor register is the operator's call.

## Not evidence of

- A closed F02. V07 closes its code half. The review half is V08: a dry import, an inventory the
  operator reconciles against the PDF, and the original's own intake and provenance records.
- An imported, assessed or frozen original. No original PDF is stored here, no page map for it is
  declared, and its intake record does not exist.
- A page map for the original. The configuration refuses precisely because none is declared.
- An assessor run. None was invoked and no quota was spent.
- A corrected PE-09 runbook. V12 owns that and stays blocked by V10 as well.
