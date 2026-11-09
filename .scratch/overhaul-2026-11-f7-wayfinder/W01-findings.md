# W01 findings — can the 2026 candidate be imported as its own document with today's code?

Ticket: `issues/01-import-route-for-the-2026-candidate.md` · researched 2026-11-06 on `harness_overhaul`
@ `1bfe147e` · read only, no private content.

## Answer

**No, but the gap is one small, declarative code change.** The import route (V07 → V08 → V17 → V18) is
generic in its *behaviour*: every step is keyed on a document's configuration and its
`is_submitted_document` flag, never on the 2025 original's ids. But the set of documents is
**closed by design**. `DOCUMENTS` declares exactly three: the sanitised derivative, the official 2025
original and the anonymised derivative (`tools/import_external_proposal.py:1042-1046`), and every entry
point refuses a configuration id outside it. The 2026 resubmission cannot be imported as a revision of
`official_original` either: that document's identity is the 2025 submission (`intake_id`
`msca-dn-2025-original`, title "MSCA-DN 2025 Part B, as submitted", `:921-929`), and the runbook (§8) and
the code (`:970-973`, "a revision of one document may not supersede a revision of another") require stage
B's candidate to be a document of its own.

So **one must-land code item**: declare the 2026 resubmission as a fourth `DocumentConfig`. Everything
else is the operator's private configuration.

## Per step

| Step | Entry point | Works for a 2026 document today? | Code assumption found | Config only, or code change |
|------|-------------|----------------------------------|-----------------------|-----------------------------|
| V07 import, `--config-input` | `tools/import_external_proposal.py --document <id> --config-input …` (runbook :289) | **no** | `DOCUMENTS` is a closed tuple (`:1042-1046`); `document_by_id` refuses unknown ids (`:1224-1231`); `register_document` refuses a config id `DOCUMENTS` does not declare (`:1093-1097`); `complete_from_input` requires the input to name the selected config (`:1128-1132`) | **code change**: add a fourth entry (below) |
| V08 dry import + provenance | `tools/dry_import_original.py --document … --submission-id … --call-id …` (runbook :231) | **no**, same cause | `--document` choices are `[doc.config_id for doc in DOCUMENTS]` (`tools/dry_import_original.py:593`). Otherwise generic: submission id and call id are required arguments, never defaulted (`:659-666`); the private-path refusals key on `is_submitted_document` (`:519-521`); the ESR intake accepts `not_applicable` and `blind_pre_evaluation` (`runner/dev_graph/intake.py:49-56`) | the same entry, then config only (`--call-id <the 2026 call id>`, ESR availability `not_applicable`) |
| V17 configuration route | `tools/author_original_workspace.py`, `runner/original_configuration.py` | **yes, after the entry** | keyed on the input's `config_id` (`tools/author_original_workspace.py:753-755`) and the `is_submitted_document` flag (`:413-417`); no 2025 literals in `runner/original_configuration.py` | config only (the operator's private configuration input: page map, page count, body size, work-package layout, revisions, from the 2026 PDF's own V08 inventory) |
| V18 submitted-document register | register renderer | **yes, after the entry** | the renderer is chosen by flag, not id (`tools/import_external_proposal.py:2401-2408`) | config only |
| Preflight, assess, freeze, audit | `harness.commands.blind_assessment …` | **yes** | no document ids or "2025" in `harness/{candidate_provenance,integrity_audit,blind_assessment,evidence_preflight,blind_baseline}.py` or the command; `--intake` is an optional free id (`commands/blind_assessment.py:429`); provenance reads the register's `is_submitted_document` declaration (`harness/candidate_provenance.py:279`) | config only |
| Readiness receipt | `harness.commands.execution_receipt --expect-candidate … --expect-profile …` | **yes** | the bound pair is generic (candidate document id + profile id); only the refusal messages say "Stage A" (`harness/execution_receipt.py:334, 1010-1015`) | config only; wording nit, not a blocker |

## The must-land item (candidate W-1 for the Step 3 cut)

**"Declare the 2026 resubmission as its own document in the importer."**

- Add a fourth `DocumentConfig` to `tools/import_external_proposal.py`, of the same kind as
  `OFFICIAL_ORIGINAL` (`is_submitted_document=True`, `workspace_rel=None`, nothing inherited, refuses until
  the operator's private input completes it), with its own `config_id`, `intake_id`, `document_id`,
  `title`, `role`, `page_statement`, `first_revision_key`, `summary`, and the same
  `declaration_fields` / `declared_status="Assumed"`. Names are the operator's; e.g. `resubmission_2026`,
  `msca-dn-2026-resubmission`, `MSCA-DN-2026_part_b_resubmission`.
- Add it to `DOCUMENTS` (`_index_documents` then enforces unique ids and graph root).
- `sections=MSCA_DN_PART_B_SECTIONS` (`:771-775`, Excellence / Impact / Implementation) is an
  **assumption** that the 2026 Part B template keeps the same three sections. W02 (profile applicability)
  should confirm it against the 2026 template.
- Tests: parametrise the existing original-route tests (`tests/test_msca_dn_original_import_route.py`,
  `tests/test_msca_dn_dry_import.py`, `tests/test_msca_dn_import.py`) over both submitted documents, plus
  one test that a 2026 revision cannot supersede a 2025 one.
- Size: about 60–80 changed non-test lines in one module, no interface change. The precedent, AN10
  (`e90aa682`), was ~1,900 lines only because the derivative was a new *kind* (a derivation and its own
  register renderer); the resubmission is the existing submitted-document kind, so V17/V18 code is reused
  as is.
- Admission: one seam (no interface change), behaviour change is the point (failing test first: today
  `--document <new id>` is refused), fits one session, no amendment. Not under the rule-5 paths, but
  `tests/test_msca_dn_import.py` and the dry-import tests are acceptance-lane modules, so the lane stays green.
- Contains no private content: like `OFFICIAL_ORIGINAL`, every value about the PDF stays undeclared in
  the repository and comes from the private input.

## Related

- **Ultrareview slice 2, finding 2** (provenance borrows another revision's manifest): low risk for V16,
  because each document has its own graph root (`workspace_rel` is unique across `DOCUMENTS`), so a 2026
  graph root holds no 2025 manifests. Passing `--import-manifest` / `--candidate-provenance` explicitly, as
  the runbook does, removes the fallback entirely. Keep it as a small fix, not a V16 blocker.
- The runbook's stage B section (§8) needs the new `--document` id once W-1 lands (V16 runbook delta).
