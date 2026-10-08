# V01 completion report — pin the extraction environment

Date: 2026-10-08
Branch: `msca-dn-pre-eval`, from `621ec1a`
Ticket: `plans/msca_dn_historical_validation_tickets.md` V01
Closes: finding F01 of `plans/reports/MSCA_DN_Readiness_Audit_2026-10-08.md`
Decision record: `docs/tier4_orchestration_state/decision_log/msca-dn-extraction-environment-pin_2026-10-08.json`

Five of six acceptance criteria are met. Criterion 4 is met in part and its
remainder is referred to the operator. V01 is not closed by this report.

## The environment

| | Value |
|---|---|
| Interpreter | Python 3.10.6, 64-bit, win32 |
| Extraction library | PyMuPDF 1.28.2 with MuPDF 1.28.2 |
| pytest | 9.0.2 |
| Pin now in the repository | `requirements.txt`: `pymupdf==1.28.2`; `runner/extraction_environment.py`: `PINNED_PYMUPDF`, `PINNED_MUPDF`, `MEASURED_PYTHON`, `REPRODUCING_BUILDS` |

## Both check commands, twice

Run from the repository root under that environment. Verbatim output:

```
### run 1
up to date          # py -3.10 -m tools.import_external_proposal --check   → exit 0
up to date          # py -3.10 -m tools.author_msca_dn_workspace --check   → exit 0
### run 2
up to date          # py -3.10 -m tools.import_external_proposal --check   → exit 0
up to date          # py -3.10 -m tools.author_msca_dn_workspace --check   → exit 0
```

`git status --porcelain` lists only the six files in **Changed files** below. No
PDF, document record, import manifest, fidelity register, source index,
preflight, frozen baseline or freeze record changed. Both committed document
versions, `@bdb8670f6987e4db` and `@b51a103520b58ded`, were reproduced from the
PDFs. Nothing was regenerated to match a new extraction.

## The cause

Not extraction-library variation presumed. Measured, with the interpreter held
at Python 3.10.6 so the library was the only variable:

| PyMuPDF | MuPDF | Reproduces the committed artifacts |
|---|---|---|
| 1.24.0 | — | No. The wheel exposes no `pymupdf` module, so `extract_document` raises `ModuleNotFoundError`. This is the lower bound `requirements.txt` declared. |
| 1.26.6 | 1.26.11 | No. The audit's library. Derives `@842a80dea6920270`. |
| 1.26.7 | 1.26.12 | No. Same identifier. |
| 1.27.1 | 1.27.1 | No. Same identifier. |
| 1.27.2.3 | 1.27.2 | No. Same identifier. |
| 1.28.0 | 1.29.0 | Yes. Off pin: it carries a MuPDF build the pin does not name. |
| 1.28.2 | 1.28.2 | Yes. The pin. |

PyMuPDF 1.26.6 through 1.27.2 split the first wrapped line of a numbered list
item into a text block of its own. 1.28.x return each list item whole. The
importer makes one paragraph per text block. Eight list items therefore split
in two, five of them in sub-section 1.1 and three in 1.3. `join_segments` does
not rejoin them. Its join rule applies across a page boundary, and all eight
splits sit inside one page. All four off-pin builds derive the same identifier.
The divergence is one stable behavioural difference, not version-to-version
noise.

### The four register differences

Measured by rendering
`docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register.json`
read-only under PyMuPDF 1.26.6 and comparing it field by field with the
committed file. These four differences are the whole of the divergence.

| Register measure | Committed | Off pin | Difference |
|---|---:|---:|---:|
| Sub-section 1.1 paragraphs | 302 | 307 | +5 |
| Sub-section 1.1 characters | 19,601 | 19,606 | +5 |
| Sub-section 1.3 paragraphs | 66 | 69 | +3 |
| Sub-section 1.3 characters | 10,010 | 10,013 | +3 |

The characters rise while the extracted text shrinks. Each split drops the one
space the whitespace collapse put between the two halves of the single block,
and gains a two-character paragraph separator. That is why the divergence does
not read as a loss.

### The interpreter is not the variable

Python 3.11.9 reproduces both committed document versions at the pinned
library. Python 3.10.6 reproduces the audit's divergence exactly at the audit's
library. The audit ran Python 3.12.14 with PyMuPDF 1.26.6; its failure is
attributable to the library alone. Python 3.12 at the pinned library is
**Unresolved**: no 3.12 interpreter is installed on this machine.

## Changed files

| File | Change |
|---|---|
| `requirements.txt` | `pymupdf>=1.24.0` → `pymupdf==1.28.2` |
| `runner/extraction_environment.py` | New. The pin, the measurement, the two verdicts, the shared `--environment` flag. |
| `tests/test_extraction_environment.py` | New. 29 tests. |
| `tools/import_external_proposal.py` | `--environment`; a stale `--check` reports the environment verdict. |
| `tools/author_msca_dn_workspace.py` | The same two additions. |
| `docs/tier4_orchestration_state/decision_log/msca-dn-extraction-environment-pin_2026-10-08.json` | New. The diagnosis, the matrix, the four differences, three open matters. |

Two verdicts, kept apart, because they differ for a real build. *Can this build
reproduce the committed artifacts?* is the suite's hard assertion. *Is this the
declared environment?* is informational. PyMuPDF 1.28.0 reproduces every
committed artifact and is off pin, so a suite that failed on the pin would
report a problem not shown to exist. No command refuses on the environment:
`--check` still answers the question it was asked and its exit status still
follows the staleness alone.

Beyond the letter of the acceptance criteria: `--environment` on both tools,
and the environment verdict printed when `--check` finds staleness. V01 asks
that the environment be "recorded where a future replay can reconstruct it";
these are how an engineer reads it. The audit's opaque exit 1 now carries its
own diagnosis.

## Checks run

| Check | Result |
|---|---|
| `tests/test_extraction_environment.py` | 29 passed |
| `tests/test_msca_dn_import.py`, `tests/test_msca_dn_workspace.py` | 120 passed |
| `tests/test_msca_dn_declaration_drafts.py` | 72 passed, 1 failed — pre-existing, measured below |
| `mypy runner/extraction_environment.py tests/test_extraction_environment.py` | 0 errors in those files; the 9 reported are pre-existing in `runner/source_index.py` and `runner/dev_graph/documents.py` |
| Same two test modules under PyMuPDF 1.26.6 | The gate fails with its reason named, which is what it is for |
| Full suite | **Did not run.** Excluded by scope; see **Full suite** below |

## Open matters

Three, all recorded in the decision record under `open`, each with a
`declared_status` of `Unresolved` and an owner.

**1. Criterion 4's manifest half is not done, and cannot be as written.**
The criterion asks for the runtime versions recorded in the import manifest,
beside the four version strings already there. One function,
`runner.external_proposal.versions()`, renders that block. It renders into both
manifests, the source index and both fidelity registers.

The resolved-fixes manifest is pinned by sha256 inside
`harness/blind_reports/preflight_242f1afb02c8_0001.json`, which also copies its
`versions` block verbatim. That preflight is bound into the frozen 74.60
baseline. Writing the runtime versions there would rewrite four artifacts this
ticket lists as immutable historical evidence, and would break the freeze. V01
instructs the opposite on both counts: both checks pass with no committed
artifact changing, and hashes are reproduced rather than regenerated.

The smallest change satisfying both: the pin is recorded in `requirements.txt`,
in `runner/extraction_environment.py` and in the decision record, which is
where a replay reconstructs it. The manifest embedding costs nothing at the
first manifest that is authored rather than reproduced — V07 externalises the
document configuration and V08 dry-imports the original. Carried to V07 and
V11. Owner: operator.

**2. The interpreter is declared, not packaged.** `MEASURED_PYTHON` declares
3.10 and 3.11, a test holds the declaration to the record, and `--environment`
reports the running interpreter against it. There is no packaging-level pin:
`requires-python` lives in a `[project]` table, `pyproject.toml` has none, and
adding one would declare this repository an installable distribution it is not.
An exact interpreter pin was also not asserted because the criterion's premise
was measured false — two interpreters reproduce. Carried to V11.

**3. The declaration drafts' adoption scan is stale.** `tools.draft_fidelity_declarations`
`check()` reports `draft_sanitised_v1.json`, `draft_resolved_fixes.json` and
`review_checklist.md` as stale, and
`tests/test_msca_dn_declaration_drafts.py::TestDeterminismAndTheCommittedArtifacts::test_the_committed_artifacts_are_reproducible`
fails.

Baseline: with the V01 decision record removed from the tree, `check()` still
reports `draft_resolved_fixes.json` and `review_checklist.md`. `621ec1a` added
`plans/reports/MSCA_DN_Readiness_Audit_2026-10-08.md`, which names the register
path, and the drafts' scan lists every artifact that does. **The test fails at
`621ec1a` independently of V01.**

What V01 adds is one entry: `draft_sanitised_v1.json` would gain the decision
record under `adoption.referenced_by_path`, because that record names the
register among its inputs as `CLAUDE.md` §12.1 requires. No declaration, no
hash and no measured value changes. This report adds a second such entry for
the same reason, and says so rather than omitting the path. The record refers
to the manifest hash by twelve characters, below the scan's sixteen, so it does
not become a hash dependent as well.

V01 did not regenerate the drafts. They and the checklist are what the operator
is reviewing under R04 and R05, approved at PE-08 with deferred rows open.
Re-rendering would change the document under review and silently absorb the
audit report's entry, which the operator has not seen. Carried to V02a and V03,
which classify and green the residual suite failures.

## Preserved bindings

| Binding | State |
|---|---|
| `@bdb8670f6987e4db`, `@b51a103520b58ded` | Reproduced from the PDFs, unchanged |
| Both fidelity registers, both import manifests, the source index | Byte-identical; `--check` exits 0 |
| `preflight_242f1afb02c8_0001.json` and its manifest pin | Untouched |
| The frozen 74.60 baseline and its freeze record | Untouched |
| The approval records, approved dispositions, comparison, revision plan | Untouched |
| `.gitattributes` line-ending protections | Unchanged |

Criterion 5 is not engaged. No extraction upgrade proved necessary, so no new
document version, no rewritten hash and no successor binding.

## Full suite — excluded by scope, not passed

**The full suite did not run to completion on this machine, and this report
makes no claim about it.** Five attempts were killed by the host's low-memory
watchdog: three whole-suite runs, one `tests/harness` run, and one loop running
each test file in its own process. At the last measurement the host had 0.78 GB
free of 15.3 GB, with a single browser process holding 2.3 GB. The pytest
process itself was 190 MB, so the constraint is the host, not the suite.

One whole-suite run did finish earlier, reporting 208 failed, 6,799 passed, 77
skipped and 5 errors in 544s. **That number is soft and is not offered as
evidence:** the tree changed under it, because the review fixes landed while it
was running. It is recorded only because it sits beside this branch's known
whole-run baseline of 207 failures, against a per-directory baseline of 54.

### Replacement evidence

Every test module that imports anything this ticket changed, run to completion
under the pin after the tree settled:

| Module | Result |
|---|---|
| `tests/test_extraction_environment.py` | 29 passed |
| `tests/test_msca_dn_import.py`, `tests/test_msca_dn_workspace.py` | 120 passed |
| `tests/harness/test_integrity_audit.py`, `tests/runner/test_external_proposal.py`, `tests/test_msca_dn_fidelity_declarations.py` | 170 passed |
| `tests/test_msca_dn_declaration_drafts.py` | 72 passed, 1 failed — baseline measured in **Open matters 3** |

That is 392 tests across the six modules reached by this change. The blast
radius is closed: `grep` over `tests/` finds no other module importing
`runner.extraction_environment`, `tools.import_external_proposal` or
`tools.author_msca_dn_workspace`.

### What is still owed

One command, on a host with memory headroom:

```
py -3.10 -m pytest -p no:randomly -q
```

Compare the result against the 207-failure whole-run baseline. A delta of one
is expected and is accounted for in **Open matters 3**.

## What V01 does not do

V01 confers no authority to close gate G1. G1 also requires V02a, V02b, V02c,
V02d and V03. No acceptance box in the ticket file was ticked by this work, and
criterion 4 needs the operator's decision before V01 can be accepted as
written.
