# HANDOFF — gate_12 fixes, rerun staging (open), manual Part B-1 condensation

**Date:** 2026-08-30 · **Branch:** `fieldwise-run-02` · **Run-id:** `fieldwise-run-02` · **Session:** "n08f"

## 1. Where the run stands

The 2026-08-29 `n08f_revision` run failed `gate_12_constitutional_compliance` on two semantic predicates
(`gate_12_result.json`, evaluated 16:30:36Z). Both root causes are identified and fixed **at the Tier 4
draft layer**; the rerun that would propagate them into Tier 5 is **staged but deliberately not executed**
(operator decision, 2026-08-30). Tier 5 sections therefore still carry the pre-fix text.

## 2. The two gate_12 failures and their fixes

### g11_p11 — "EI-05 nuclear impact" (identifier-namespace collision, not a nuclear claim)
- Tier 3 `architecture_inputs/impacts.json` numbers its own coverage entries EI-01..EI-06; its EI-05 is
  the R&I-capacity/knowledge-transfer impact. Tier 2B `expected_impacts.json` EI-05 is the call slice's
  **Euratom nuclear** impact (inapplicable to FIELDWISE). Phase 5 had already flagged the id-vs-description
  conflict (pathway `IP-EI-05` = `uncovered_flagged`; R&I content carried by `IP-EI-06`).
- The Impact 2.2 drafter cited the Tier 3 numbering in evaluator-facing text, where EI-xx reads as Tier 2B.
- **Fix** (in `section_drafts/impact/2.2.draft.json`): all four EI-05 citations re-pointed to EI-06
  (two prose spots, claims c2 and c19). `impact_pathway_refs`/spine untouched (listing the flagged-uncovered
  pathway is honest declaration, not coverage assertion). Tier 3 NOT renumbered (would ripple into Phase 5).

### g11_p13 — AgroVIR 745,000-ha footprint Confirmed in Excellence, Assumed elsewhere
- Root cause: Tier 3 is internally split. `consortium/capabilities.json` CAP5 carries the figure as
  **Confirmed** ("company's published figures"), while the same file's `participant_capacity` record and
  `working_assumptions.json` key `agrovir_relevant_track_record` carry it as operator-declared **Assumed**
  (pending AgroVIR's written confirmation). Excellence cited CAP5; Impact/Implementation cited the declaration.
- **Fix** (in `section_drafts/excellence/1.3.draft.json`): claim re-keyed to the declaration exactly as the
  assumption-applier would produce it (`agrovir_relevant_track_record`, declared value verbatim, `assumed`,
  `assumption_declared: true`, source `working_assumptions.json` — W1-resolvable). Prose gained the standard
  "operator's declared position pending written confirmation" qualifier.
- **Open Tier 3 item (operator's):** align CAP5 to Assumed, or file the written confirmation and promote
  everywhere. Recorded in the decision log.

Decision log: `decision_log/n08f-gate12-ei05-and-agrovir-status-corrections_2026-08-29.json`.

## 3. Rerun staging — READY, NOT EXECUTED

The chain `n08a → n08b → n08d → n08e → n08f` is fully staged:

1. **Checkpoint archived** (write-once guard): the failed run published `checkpoints/phase8_checkpoint.json`
   at 16:25Z (components run before the exit gate). Operator moved it to
   `decision_log/archive/phase8_checkpoint.json`. `checkpoints/` is clear.
2. **Reuse trap defused:** `reuse/phase8/n08{a,b}_*.reuse.json` moved to `reuse/phase8/archive/`.
   Rationale: the reuse fingerprint (`FINGERPRINT_INPUTS`) does **not** cover `section_drafts/`, the section
   artifacts and recorded gate passes still match, so reuse would have validated, the scheduler would have
   dropped the applier+assembler (`agent_runtime.py` — draft-consuming components partitioned out on the
   reuse path), and the stale sections would re-fail gate_12 identically after paying for n08e.
   Missing metadata = documented fail-closed fallback to normal execution. `n08c` metadata retained.
3. **Node states reset** in `.claude/runs/fieldwise-run-02/run_manifest.json` (n08d-handoff lesson 3):
   n08a, n08b, n08d, n08e, n08f → `pending`; **n08c stays `released`** (untouched; gate_10c content-fresh).

Commands (operator-run, in order, each after the previous releases):
```
py -3.10 -m runner --run-id fieldwise-run-02 --node 8a
py -3.10 -m runner --run-id fieldwise-run-02 --node 8b
py -3.10 -m runner --run-id fieldwise-run-02 --node 8d
py -3.10 -m runner --run-id fieldwise-run-02 --node 8e
py -3.10 -m runner --run-id fieldwise-run-02 --node 8f
```
Expected behavior: 8a/8b do **not** redraft. The current-run spine+drafts mark the drafting skill
`reuse_skipped`. The applier no-ops (the hand-set claim is already final-form). The assembler recomposes
from the corrected drafts, and the audit skills run. 8e is the one expensive step (fresh evaluator review).
8f rewrites exports, republishes the checkpoint, re-evaluates gate_12.

## 4. Operator decision: skip the rerun for now, submit via manual pass

- gate_12 stays failed and Tier 5 stays pre-fix until the chain runs; this divergence is **known and chosen**.
- A fresh `part_b.docx` was rendered 2026-08-30 via the standalone deterministic exporter
  (`py -3.10 -m runner.docx_exporter`, no Claude, no node dispatch) from current (pre-fix) Tier 5 content.
- The EI-05 and AgroVIR fixes must ride along in any manual edit of exported content.

## 5. Page-limit finding (drives the manual condensation)

MSCA-PF Part B-1 hard limit: **10 pages** (sections 1–3; excess auto-hidden). Operator page budget exists:
confirmation checklist **item 14** (2026-08-11): 1.1=2.25, 1.2=2.25, 1.3=1.0, 1.4=0.5, 2.1=0.75, 2.2=0.5,
2.3=0.75, 3.1=1.75, 3.2=0.25 (Σ=10.0). Current draft: **12,911 words ≈ 20 pages** at ~650 w/p — ~2× over,
concentrated in 3.2 (10.9×), 2.2 (3.7×), 2.3 (3.3×), 1.4 (2.5×), 2.1 (2.3×), 1.3 (2.2×). Only 1.1/1.2 fit.
No gate enforces length (size-cap tests are among the known pre-existing failures).

## 6. Manual Part B-1 condensation (this session's closing task)

Operator instruction (2026-08-30): condense the draft into the MSCA-PF Part B template structure, with
the two fixes applied and at most half a page for images. Excellence keeps extensive narrative; Impact and
Implementation prefer tables over narrative. Formatting reference =
`docs/tier3_project_instantiation/source_materials/submitted_2025/PLANTDIGISENSE_Part_B1.pdf`.

**Constitutional note:** the output is written as a NEW file alongside the Tier 2A template — never over
`docs/tier2a_instrument_schemas/application_forms/msca/Tpl_Application Form (Part B) (HE MSCA PF).rtf`
itself (§13.11: Tier 2 sources must not be modified with project content). The condensed document is an
**operator-requested manual-edit artifact**, not a gate-validated Tier 5 deliverable: it derives from the
drafted (gate_10a/b/c-passed) sections plus the two Tier 4 fixes, but has not passed gates 11/12 in this
form (§13.8 flag). It is the basis for the operator's hand-finishing before submission.

**Outcome (2026-08-30):** delivered as
`docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_manual-condensed_2026-08-30.docx` — 9 of 10 pages,
5,168 words, Word-verified. Excellence 1.1–1.4 is condensed narrative; Impact 2.1–2.3 and Implementation
3.1–3.2 are PLANTDIGISENSE-style tables (WP plan, milestones, ten-row risk register, organisation
capacities). The Gantt is a generated figure under half a page (single-hue ramp, photocopy-safe; identity
carried by row labels). Formatting follows the template's binding conditions: A4, 15 mm margins, Times New
Roman ≥11 pt including table text, single spacing. Internal EO-xx/EI-xx codes were dropped from
evaluator-facing text; the AgroVIR footprint is qualified as the company's declared position in 1.3, 2.3
and 3.2. Builder script kept in the session scratchpad (`build_partb1.py`).

**Citations added (same day):** 18 footnotes carrying 29 references, all drawn verbatim from the
operator-authorised `source_materials/references/fieldwise_references.bib` (item 10). Distribution:
Excellence 1.1/1.2/1.4 (areas 1–8 of the bib's area map) plus the 2.3 impact-magnitude sources R36–R40.
Deliberately excluded: `tarraf2024` and `wilks2001` (bib flags both as needing re-verification before
submission) and DrR (uncitable per the item-10 decision — deposit on Zenodo to close). Footnotes are
Times New Roman 8 pt (template floor for non-body text). Result: exactly 10 of 10 pages, with roughly
0.4 page of slack on the final page. Inserter script: scratchpad `add_footnotes.py` (Word COM).
