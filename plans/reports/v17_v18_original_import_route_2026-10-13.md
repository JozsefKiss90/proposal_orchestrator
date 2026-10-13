# V17 and V18 — the original's configuration route and its register

| Field | Value |
|---|---|
| Date | 2026-10-13 |
| Branch | `msca-dn-pre-eval` |
| Tickets | V17 and V18, gate G2 |
| Closes | Both implementation-gap rows the PE-09 runbook listed as blocking stage A step 1 |
| Decision record | `docs/tier4_orchestration_state/decision_log/msca-dn-original-import-route_2026-10-13.json` |
| Status | Agent-drafted. Acceptance is the operator's. |

## 1. What was missing

V07 made every assumption the importer had hard-coded into a field of a selectable document
configuration. V08 built the dry import that measures a document before it is imported. Between them
the original could still not be imported, for two reasons the runbook recorded as gaps.

**Its configuration had nowhere to live.** The five fields `--describe` names — the page map, the
page count, the body point size, the work-package layout and the graph root — are facts about a PDF
held in a private network. The V08 procedure told the operator to declare them on `OFFICIAL_ORIGINAL`
in this repository, which would have put the submitted document's structure here.

**Its register had no renderer.** The fidelity register's provenance header declares a sanitisation,
a transformation and a reflow, so V07 made `render_register` refuse the submitted text rather than
label it with the copy's facts. The importer renders a register per revision, so that refusal blocked
the import outright.

## 2. What was built

| Artifact | What it is |
|---|---|
| `runner/original_configuration.py` | The configuration input: schema, fail-closed reader, and the check against the measurement |
| `tools/original_configuration_template.json` | The form the operator fills in, refused as a configuration |
| `tools/author_original_workspace.py` | The private graph root, and the submitted document's register |
| `tests/test_msca_dn_original_import_route.py` | 135 cases over a four-page non-sensitive fixture |
| `plans/msca_dn_pe09_runbook.md` §4 | Steps 1b and 1c, no longer marked future |
| `plans/msca_dn_v08_original_dry_import_procedure.md` | Steps 5 to 7, the operator's own path |

## 3. The route

The operator copies the template to the private root and answers it. Nothing about the original is
declared in this repository: its graph root, its declaration directory and its configuration input
are all undeclared here, and a test asserts it.

The reader refuses before anything is checked. A missing field, an empty one, an unfilled
placeholder, a status outside CLAUDE.md §12.2's four, a duplicate sub-section, an empty page map, or
a silence where null is an answer. The committed template is refused twice over: every value is a
placeholder, and it sits inside this repository, which no private root may contain.

Then the declaration stands against the dry import's own inventory. The page count, the body point
size, every numbered marker, the criterion headings, the coverage of the map and the declared PDF's
own hash are all compared with what was measured. That is twenty-five findings. Four answers no
measurement can confirm are reported as unchecked rather than as agreeing. A sub-section the document
opens with, one whose marker is a whole block, a document with no work-package table, and a later
revision's bytes.

Both lists come from the reader's own source in the test, so a finding nobody wrote a case for fails
rather than passing unnoticed.

Two refusals matter more than the rest. A configuration whose inventory measured other bytes is
refused, so a page map declared from one file cannot be used to import another. And a configuration
that is already complete may not be redeclared, so the copy's page map stays the one its hash-bound
manifests were measured under.

A page the map does not reach is a finding unless the input declares it with a basis. A cover page is
a legitimate answer; silence is not.

## 4. The register of a submitted document

The copy's register answers how a derivative differs from the submission. This one answers what
reading the submission through an extraction costs, which is a different question with a different
evidence base.

Its header declares the submitted document's own facts. The assessed file is the authenticated
original. The transformation block records that none was applied, and the reflow block that none
happened. The ESR statement is the copy's inverted: the ESR evaluated this text, so a difference from
its total is not explained by changed wording or removed evidence.

The transformation block says in so many words that it is not a claim the extraction preserved
everything. What the extraction loses is the V08 reconciliation, and the register will not be written
over an open one. An item still `unreconciled` refuses the write. So does a record marked complete
over an open item, and so does a `preserved` verdict resting on a measurement equally true of a
document whose figures are gone.

Its declared half asks for a `presence` and an `extraction_fidelity` per sub-section, under a record
type of its own. A transformation declared about the submitted text would read as a sanitisation of
it, which is the confusion the original refusal existed to prevent.

The integrity audit still reads it. The test resolves the private candidate's provenance through
`harness/candidate_provenance.py` end to end. It finds the manifest in the private graph root, reads
the register the manifest names, and reports the identity scope as the submitted document's own.

## 5. One defect found on the way

The import manifest's claim block carried one sentence of prose: *the sanitisation removed every
citation*. That is a fact about the copy, rendered by a generic renderer. The original's manifest
would have asserted a sanitisation of the submitted text.

It is the same class of defect V07 fixed, missed because the original was never importable. The
sentence is now a required configuration field. The copy declares what it was already rendering, so
its manifests keep their bytes; the original declares that no claim of its own is resolved to a
source until ticket X01. The manifest's ticket field moved the same way, because the original is not
imported at PE-03.

## 6. Verification

The whole route runs end to end in the test, on a four-page Part B shape built with pymupdf in a
temporary directory outside the repository. Six steps: dry import, configuration, private graph
root, import, register, and both `--check` replays.

| Check | Result |
|---|---|
| `tests/test_msca_dn_original_import_route.py` | 135 passed |
| The modules V17 changed | 403 passed across six modules, no failure |
| `tests/harness/test_acceptance_lane.py` | 68 passed |
| `mypy` on both new modules | no error of their own |
| Twelve mutation runs | each failed at least one check; five failed the page-count rule |
| The 25 findings and 4 unchecked answers | every one produced by a case, 21 of them by a single mutation |
| Prose | the runbook, the procedure and the ledger pass with no error |
| The whole suite, in three chunks | 7,985 passed, 37 failed, 86 skipped, 8,108 collected |

None of the 37 failures is this change's. `tests/harness` and `tests/runner` return the figures V13
measured against a HEAD worktree, case for case: 1,843 passed with 17 skips, and 4,353 passed with 19
failures. The third chunk fails 18, in the same eight modules V13 recorded — the transport migration
line, the demo instance's data, and one missing optional extra the lane's exclusion document names.
No msca-dn module fails.

No quota was spent. No assessor ran, no runner phase was dispatched, no scoring was performed, and
the frozen 74.60 baseline is untouched. Both committed registers and both import manifests still
reproduce byte-equal.

## 7. What this is not evidence of

- That the original has been imported. It has not, here or anywhere this repository can see.
- That a page map exists for it. The route is here and the declaration is the operator's.
- That the extraction of the original preserves anything. The reconciliation settles that, page by
  page, and the register refuses to be written until it is complete.
- That a result over the original would be comparable with the ESR's. The profile, the assessor
  variance and what the extraction lost all remain.
- That V17 or V18 is accepted. Acceptance is the operator's.

## 8. Open

- `register_document` holds a completed configuration for the life of the process, because its
  revisions are declared at run time. A configuration id this tool does not declare cannot be
  registered, and a revision another document owns cannot be taken.
- The register names the ESR by path and not by hash. The ESR is a public artifact of this
  repository, and a hash the private root cannot produce is not restated there.
- The scorecard a sub-section with no heading takes its title from is copied into the private root
  from this repository. It is public, so nothing private moves, but the import then depends on that
  copy rather than on the committed file.
- V14's second criterion is what these two tickets unblock. The run itself stays the operator's.
