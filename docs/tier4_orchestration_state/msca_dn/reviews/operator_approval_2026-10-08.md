# PE-08 operator approval and PE-09 handover decisions

Date: 2026-10-08  
Operator: József Kiss  
Repository: `JozsefKiss90/proposal_orchestrator`  
Branch: `msca-dn-pre-eval`  
Suggested repository location: `docs/tier4_orchestration_state/msca_dn/reviews/operator_approval_2026-10-08.md`

## Approval authority and scope

The operator approved the decision package in this conversation on 2026-10-08 at 10:37:26 UTC+02:00, using the exact instruction:

> Approve this decision package

The time above is written as a UTC offset. The branch's anonymity rule forbids a place
name in Tier 3, Tier 4 and Tier 5, and the offset names the same instant.

This document transcribes that approval. It approves the review policies, preparation of optional improvements, explicit deferrals, and required validation corrections below. It does not certify new tests, approve every draft row as fact, adopt declarations into active registers, or authorise a new assessor run in this workspace.

Implementation reports identify R01 `5159e5a`, R02 `0943b1d`, R03 `1eddc81`, R04 `76a794e`, and R05 `047f64d`. Their reported verification is historical evidence, not a fresh independent test run performed for this approval.

The frozen blind baseline remains **74.60/100**. Preserve baseline, ESR record, PDFs, candidate evidence, historical registers, dispositions, comparisons and reports. New decisions and corrected results must be successor artifacts.

## Reviewed inputs

- `plans/pe08_review_and_pe09_handoff_tickets.md` (the attached ticket document; reconcile any differently named repository copy).
- `docs/tier4_orchestration_state/msca_dn/reviews/operator_decisions_9732dde50039_0002.md`.
- `docs/tier4_orchestration_state/msca_dn/esr/semantic_adjudications_f60ae6e0a2a1.json`.
- `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_r05.json`.
- `docs/tier4_orchestration_state/msca_dn/declarations/review_checklist.md` and both R04 declaration drafts.
- `harness/esr_comparison.py`, specifically preservation validation and register-pointer resolution.

Before writing the repository decision record, resolve actual paths, record the current revision and compute the input hashes. No hash is invented in this document. If inputs have substantively changed since review, state the differences; this approval applies to the reviewed propositions, not unknown later edits.

## Approved review decisions

| ID | Subject | Approved decision | Limit retained |
|---|---|---|---|
| D01 | E-01/E-02 shared ESR sentence | Keep methods and clinical-data security as separate clause-level observations. Report their shared sentence and severity cluster. | Do not present them as separate evaluator sentences, independent deductions, or inflate cluster-level detection. |
| D02 | E-03 validation design | Accept non-detection of the criticism in the recorded output. | Do not claim absence from output proves the model did not read the evidence. Qualify or replace the `evidence_not_read` causal description in successor documentation. Preservation remains separately qualified. |
| D03 | E-07/E-09 adequacy disagreements | Count missed ESR criticisms in the same detection summary, subject to preservation; distinguish adequacy disagreement from an unmentioned topic. | Report failure-mode breakdowns separately. Detection is not an overall accuracy or calibration claim. |
| D04 | Q-01/Q-03 contradicted milestone citation | Withdraw the contradicted citation and retain it as an assessor validation case for PE-09. | Never edit proposal milestones to satisfy the false absence claim. |
| D05 | Q-02 table conflation | Record the deliverable/milestone conflation as an assessor validation case. | A missing validation column does not prove inadequate deliverable validation. Review relevant prose and original-dependent evidence before finalising the proposal judgment. |
| D06 | Q-03 detection credit | Replace full detection with provisional partial detection; integrity audit is the only contributing lane. | The surviving finding concerns timing only. Definitions are not detected; timing interpretation remains Unresolved. If original context removes the alleged conflict, revisit detection credit. |
| D07 | I-S02 sustainability funding | Prepare an optional improvement beyond the ESR, conditional on checking the original. | No funding source, budget, maintenance duty or partner commitment is approved. Preserve the ESR strength. |
| D08 | I-S05 societal indicators | Add a separately labelled societal-impact subtask within the broader impact revision package. | Keep it distinct from the ESR economic/technological criticism. No invented indicators, numerical targets or promised clinical outcomes. |
| D09 | A01 appointment and WP windows | Keep M40 versus M36 arithmetic as context. Verify actual duration and M37–M40 activities privately before schedule recommendations. | Overlap is a limited consistency test, not proof of compliance or feasibility. Do not infer project duration from WP dates. |
| D10 | A02 DC participation | Accept directional containment as a documented audit assumption. Do not restore reverse differences as defect findings. | Research-host lines need not list all training/dissemination participation. Form headers are evidence of field meaning, not a quoted containment requirement. |
| D11 | A03 milestone dependencies | Retire missing deliverable references as defect findings. Check explicit references for nonexistent deliverables or contradictory sequencing. | Links may be suggested as drafting advice. Do not assume every milestone depends on a deliverable or invent a link. |
| D12 | M7.3 scheduling decision | Defer date changes and relocation until duration, WP scope and intended follow-up timing are privately verified. | The two existing alternatives are not exhaustive. Retaining the date with adequate explanation may be justified by the original context. |
| D13 | Fidelity declarations | Accept separation of extraction, revision-difference and original-fidelity claim scopes. Defer active-register adoption. | All original-fidelity statements remain Unresolved. Acceptance of the design is not per-row adoption or confirmed preservation. |
| D14 | Body-point-size description | Accept preparation of the measured qualification: predominantly 12 pt with the recorded 458 prose characters at 9.8 pt. | This is about the sanitised revision; it does not establish an original-proposal formatting defect or a page locator. Apply through a successor provenance update with bindings preserved. |
| D15 | Handover | Permit R06 preparation after the review decisions are recorded. | Runbook preparation may proceed while private facts remain open. PE-09 execution remains pending in the approved private environment. |

## Required validation corrections

### V01 — Preservation guard

Current code accepts a Confirmed preservation claim when the subsection's declared half merely contains a non-empty `presence` value. An extraction-only presence declaration must not unlock confirmed preservation from the original.

- [x] Validate the relevant original-fidelity claim scope, status, basis and matching subsection before accepting Confirmed preservation.
- [x] Require explicit evidence supporting the preservation proposition relevant to the ESR row; a generic non-empty basis is insufficient.
- [x] Reject extraction-only Confirmed presence when original fidelity is Unresolved.
- [x] Add focused tests for that refusal, unrelated scopes, missing basis, mismatched subsection and a valid supported declaration.
- [x] Preserve schema-1.0 historical replay through a documented compatibility approach; do not rewrite old artifacts to make validation pass.

### V02 — Register-pointer ambiguity

`resolve_pointer` prioritises integer array positions before subsection IDs. Thus `derived/sub_sections/8/characters` and `/5/characters` can resolve successfully to the wrong subject. The section-8 and section-5 length statements in Q-S02/Q-S03 must not be accepted as supported.

- [x] Define an unambiguous typed ID-reference syntax or equivalent resolver behaviour for subsection lists; retain a documented legacy positional path for historical replay if needed.
- [x] Test IDs `4`–`8`, dotted IDs, reordered lists, missing IDs and legacy positional references.
- [x] Re-resolve Q-S02/Q-S03 by identity, correct text and references, and generate successor evidence/reports without altering their predecessors.

## Original-dependent decisions explicitly deferred

| Observations | Required private evidence | Current review disposition |
|---|---|---|
| E-02, E-04, E-08 | Original security, hospital/operator diversity and entrepreneurship mechanisms; compare relevant passages with sanitised text. | Preservation is unconfirmed. Withdraw E-04's cohort-size citation now; do not settle miss versus not-assessable from an absence in this copy. |
| E-05 | Original registry/database and contributing-clinician passages. | Keep not-assessable pending evidence. |
| E-S03, E-S05 | Original repository/preprint commitments, supervisor mapping and track-record evidence. | Do not adopt blind criticisms as established proposal weaknesses. |
| I-S01 | Original secondment rows, host-sector classifications and the denominator for the 80% claim. | Recompute privately before approving a correction. Identify the actual source subsection; do not guess one. |
| I-S04 | Original target-group/indicator tables, figures and prose. | Do not attribute the disagreement to sanitisation as a confirmed cause. |
| Q-01 | Original dependencies, Gantt and sequencing evidence. | Keep partial classification qualified; absence of embedded images alone does not establish that every figure was lost. |
| Q-S02, Q-S03 | Original capacity and hosting evidence. | Correct identity references now; original-dependent adequacy remains unresolved. |
| M7.3 and appointments | Actual project duration, WP scope, funding/activity windows and follow-up intent. | No date or participation changes approved. |

The seven preservation-qualified misses in R05 remain provisional unless supported in the required claim scope. Do not mechanically upgrade them after adopting extraction-only declarations. Recompute counts from actual successor rows; do not hard-code a target total or claim validated harness accuracy.

## Revision and approval boundaries

- All 15 ESR shortcomings remain open revision-review items. Approval of their review policy does not approve the proposed scientific answer or close an ESR criticism.
- Optional improvements D07/D08 remain identifiable as beyond-ESR work.
- Scientific methods, study designs, numerical targets, data-access arrangements, budgets and partner commitments still require confirmation by their responsible humans.
- The other agent-drafted observations are not blanket-confirmed by this approval. Carry their provenance and uncertainty forward.
- Operator approval is an authority fact; Confirmed/Inferred/Assumed/Unresolved describe evidence status. Do not convert every approved policy or acknowledged row to Confirmed evidence.
- No active-register adoption, proposal editing, private-source upload or new assessor run is authorised by this record.

## Claude implementation checklist

- [x] Commit this approval record at the suggested path or the repository's equivalent canonical location; record input hashes and the actual branch revision.
- [x] Reconcile ticket checkboxes with implementation evidence and the scope above. Check approved decision items now; leave unimplemented corrections and private factual checks open.
- [x] Complete V01/V02 and retire the A03 defect rule through a focused general correction with tests and successor audit output where required.
- [x] Write successor dispositions, notes, comparison, revision plan and review diff carrying this operator approval only where it applies.
- [x] Apply D01–D08 reporting corrections, including output-versus-reading language and provisional Q-03 partial credit.
- [x] Add the optional tasks without fabricating commitments. Recompute counts and dependency inventories through supported tooling.
- [x] Verify original artifacts, 74.60 baseline and score block remain unchanged and historical replay still works.
- [x] Start R06 preparation; list all deferrals and validation cases in its private-environment prerequisites.

Further permission is not needed for these authorised corrections and preparation. Ask for factual confirmation only where missing original evidence or a new scientific/partner commitment requires it.

## Resolved inputs and revision

Transcribed into the repository on 2026-10-08. The approval was given against the
branch at revision `047f64dfaf85842caac3c8df64efb4ea7572c8a4` (`msca-dn-pre-eval`, the
R05 commit). Every hash below is the sha256 of the file as it stood at that revision, so
the propositions this approval applies to are pinned to the bytes that were reviewed.

| Reviewed input | sha256 at `047f64d` |
|---|---|
| `plans/pe08_review_and_pe09_handoff_tickets.md` | `6c1bfdfcf92b950e9b67b863f344bcef9a4068861a0e066789b1ace9719c3200` |
| `docs/tier4_orchestration_state/msca_dn/reviews/operator_decisions_9732dde50039_0002.md` | `abbf4fc398e54ceb4f54855b5871d7dceb06acccbc4ccf4fc9df5127a26a0300` |
| `docs/tier4_orchestration_state/msca_dn/esr/semantic_adjudications_f60ae6e0a2a1.json` | `354db83d36727c05c03a348a8040c65bfb721b0f41fa8889ac60fa24a3c7f6af` |
| `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_r05.json` | `fbed6abdb1c7bcf78aed5455b0616dd07bd05a30262c1e5ab8a01e61ae819576` |
| `docs/tier4_orchestration_state/msca_dn/declarations/review_checklist.md` | `d18837c3caa2dee52473155e0486bea4ab87772862042ea3d3e1bbf841c7e6aa` |
| `docs/tier4_orchestration_state/msca_dn/declarations/draft_sanitised_v1.json` | `e5f00f6bbfb027eef65fd165dd686e758db330ada75f24592b2e7e350d7b3203` |
| `docs/tier4_orchestration_state/msca_dn/declarations/draft_resolved_fixes.json` | `b508a3767406ce174387f7a09cfbc12a69cd6a92ac4f2b534a23dd2c35bbcaea` |
| `harness/esr_comparison.py` | `c3a0f67b86c62fbac915761b3599627a89dd776667a8b8911d7f0ef87e09dec9` |

The ticket document in the repository is the attached one, under the name above; no
differently named copy exists. None of the reviewed inputs had changed between the review
and this transcription. Five of them change after it, by design and not by edit.

- `harness/esr_comparison.py` is the subject of V01 and V02.
- `plans/pe08_review_and_pe09_handoff_tickets.md` is reconciled, which is item 2 of the
  checklist below.
- The two declaration drafts and the review checklist are re-rendered by their own R04
  tool. The checklist's adoption-cost scan enumerates every artifact that names a fidelity
  register, so each new artifact here moves it. The drafts restate each row's open operator
  question from the active review notes, which are now the approved ones.

No drafted declaration, no status and no basis moves in that re-render.

The implementation that carries this approval out is recorded in
`docs/tier4_orchestration_state/decision_log/msca-dn-operator-approval_2026-10-08.json`,
which pins the hash of every artifact written under it. The successor dispositions name
this record by path and by hash, so this file is final once that record exists; a later
correction is a successor record, never an edit here.
