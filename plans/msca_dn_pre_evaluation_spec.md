# MSCA-DN assessment framework, tested on a sanitised historical case

**Milestone specification.** Written 2026-10-04. Supersedes the conversation transcript in
`plans/msca_dn_scoring_and_pre_evaluation.md`, which remains as the originating discussion.

This document records what will be built, why each design decision was taken, and what the
milestone cannot establish. It is a plan under `CLAUDE.md` §10.2, not an authority.

---

## 1. What is being evaluated

A completed MSCA Doctoral Networks proposal, submitted to the 2025 DN call and scored 85.80%
by its Evaluation Summary Report. The artifact available here is a **sanitised derivative** of
that submission, not the submitted document.

| Role | Artifact | sha256 (first 16) |
|---|---|---|
| Current assessment artifact | `sanitized_proposal_final.pdf`, 84 pages (reflow of a 34-page original) | `5474569f33d20174` |
| Historical evaluation | `MSCA DN ESR.pdf`, 4 pages | `40a885e8aa593367` |
| Instrument schema, evaluation | `ef_he-msca_en.pdf` V2.2, 17.12.2025 | `f7478ef7f1eac4c3` |
| Instrument schema, application — form the submission was written against | `af_he-msca-dn_en.pdf` V5.0, 29.04.2025 (2025 call) | `b77f148e8875359a` |
| Instrument schema, application — form governing the 2026 call | `Tpl_Application Form (Part B) (HE MSCA DN).pdf` V6.0, 04.04.2026 | `f19042696e492ce4` |
| Same template, RTF | `Tpl_Application Form (Part B) (HE MSCA DN).rtf` | `00a48b993fe013ac` |

The proposal declares itself a **standard Doctoral Network**, not an Industrial Doctorate and not
a Joint Doctorate (p. 32).

The baseline runs under a **2026 profile** and is labelled resubmission readiness for
`HORIZON-MSCA-2026-DN-01` (deadline 2026-11-24). It is not an attempt to reproduce 85.80.

### What this milestone cannot establish

- That the harness reproduces the original score. The copy differs from the assessed document.
- That grounding judgments are accurate. The supporting sources were generalised away.
- The final resubmission's quality. That requires the authoritative candidate inside the
  private network.

A difference from 85.80 will not be interpretable as model error. It may equally be changed
wording, removed evidence, or assessor variance. **Prompts and rubrics will not be tuned toward
85.80.**

---

## 2. Corrections to the originating plan

Each was verified against the repository.

**2.1 The DN criteria need no network access.** `ef_he-msca_en.pdf` is on disk and tags ten DN
aspects on pp. 4–6. The ESR quotes all ten verbatim and identically, which independently confirms
the set and shows the aspect texts did not change between the submission-era form and V2.2.

**2.2 A candidate directory cannot carry an intake, and is never leakage-checked.**
`harness/blind_assessment.py:729` refuses an intake unless the evidence came from the document
route, and `EVIDENCE_SOURCE_DIRECTORY` is documented as "not guarded by this module". PE-03 must
therefore import into a dev-graph. Writing candidate JSON directly is not an option.

**2.3 F12's cause is not a key mismatch.** `runner/dev_graph/builder.py:401` does enrich
`verified_span` with an `id`, so `materialise_candidate`'s lookup is correct. The actual defect is
that the demo's document record carries **147 claims and zero `verified_span` values** while
declaring 90 of them `source_grounded`. Nothing in `documents.py::_claim` forbids that.

**2.4 No criterion-score machinery exists.** `weight_pct` is parsed and validated at
`harness/profile.py:354` and then used by nothing. The 0–5 holistic score is entirely new work.

**2.5 Aspect averaging is forbidden by Tier 1, not merely inadvisable.** General Annexes
2026-2027, Part 15 p. 27: *"Evaluation scores will be awarded for the criteria, and not for the
different aspects listed in the table."*

**2.6 The per-criterion threshold comes from Tier 1.** Same page: *"The threshold for individual
criteria will be 3."* The scorecard needs nothing from the ESR. Annex D's generic overall
threshold is 10 on the unweighted sum of three; the MSCA evaluation form overrides it with 70 on a
weighted total out of 100, which the ESR confirms. That override is a tier interaction and goes in
the decision log per §12.3.

**2.7 The sanitised copy has zero figures, and its work-package dependencies are sparse and
informal.** No images on any page. No Gantt chart and no work-package dependency diagram. DN AF
V5.0 mandates neither, so this is not a template omission.

**Measured.** The strings `dependenc`, `interdepend`, `Gantt` and `critical path` occur **zero**
times across all 84 pages.

**Also measured, and it bounds the claim.** Inter-work-package relations do appear, stated without
those words:

- p. 44, Task 3.1: *"Explainability methods will be integrated in collaboration with WP1."*
- p. 48, Task 4.6: *"Transfer methods developed in earlier work packages into industrial
  medical-device environments."*

Plus four `in WP<n>` references and one `builds on`.

**Reviewed judgment, not measurement.** An earlier draft of this section concluded there was "no
dependency description in any form". Zero keyword matches do not establish that. What the evidence
supports is that relations exist but are sparse and informal, with no systematic account. That is
consistent with the ESR's Implementation shortcoming, *"the description of dependencies between
work packages"*, which criticises an inadequate description rather than a missing one.

The keyword counts go in the register's derived half. This judgment goes in the declared half, per
decision 9, and the operator owns it.

**2.8 The sanitised copy has zero citations.** No bracketed numbers, no author-year, no DOIs, no
URLs, no reference list. The prose still asserts *"Systematic reviews confirm that adoption is
slowed by fragmented data environments"* (p. 1) with nothing behind it. The ESR, assessing the
original, found the project *"goes beyond the state of the art … and it is ambitious"*. This
single fact drives decision 14.

**2.9 Part B2 section 8 is present.** Earlier in the discussion I said it was absent; that was
wrong. Participating Organisations runs pp. 76–84, unlabelled, with nine beneficiary entries and
five associated partners, ending cleanly. AF §6 Supervisory board is folded into the copy's §5
(p. 69). AF §9 Letters of pre-agreement is DN-JD only and not applicable. AF §10 Declaration on
the use of AI is absent.

**2.10 `assessment` and `finding` nodes cannot exist.** They are in `NODE_TYPES`, the layer map,
the relationship specs and the view policies, but the builder emits neither and no record source
feeds them. `bind_assessment` is a pure helper nothing calls with real data. The
`historical_feedback_analysis` view is therefore empty by construction.

**2.13 The blind assessor is not blind. The CLI contract is the opposite of what the harness
assumes.** `claude --help` on this build documents `--tools`:

> Specify the list of available tools from the built-in set. Use `""` to disable all tools,
> `"default"` to use all tools, or specify tool names.

Omitting the flag is therefore **not** the same as passing an empty list. The transport appends it
only when the list is truthy (`runner/claude_transport.py:877`), and the judge backend passes
`tools=None` under the comment *"No tools. This is what keeps the assessor blind"*
(`harness/commands/_subscription_judge.py:177`). Its module docstring states the assessor "cannot
open the drafting context, the assembled draft or the phase outputs, because it cannot open
anything."

Measured on 2026-10-04, from the repository root, model `claude-sonnet-5`:

| Invocation | Prompt | Result |
|---|---|---|
| no `--tools` flag — the harness's shape | read `./CLAUDE.md`, else say `NO_TOOLS` | returned `# CLAUDE.md — Repository Constitution` |
| `--tools ""`, prompt on stdin — the transport's argv shape | same | returned `NO_TOOLS` |

So the assessor can read the repository, and `Popen` is called with no `cwd`
(`runner/claude_transport.py:911`), so it inherits the repository root — where
`docs/tier4_orchestration_state/msca_dn/esr/` is about to live.

**Why no test caught it.** `tests/harness/test_subscription_judge.py:65` asserts
`calls[0]["tools"] is None`. That pins the Python keyword, not the capability.

**A CLI usage trap inside the fix.** `--tools` is variadic. `--tools "" "<prompt>"` absorbs the
prompt into the tool list and the CLI then refuses for want of input. Use `--tools=` with a
positional prompt, or `--tools ""` with the prompt on stdin, which is what the transport already
does.

**Blast radius beyond this milestone.** `runner/skill_runtime.py:917` and `:1842` — cli-prompt
mode — also omit `tools`, while TAPM passes `["Read", "Glob"]` explicitly. The intended
distinction between the two modes may not exist at the CLI. The demo's blind baseline of
2026-10-02 ran this transport from the repository root, so its leakage result is established for
the *package* and not for the *assessor*. Nothing on disk settles whether tools were exercised:
the report stores metadata only and the backend never persists the stream-json. This is recorded
here and belongs to the demo's own finding register, not to a DN ticket.

**2.12 Two application-form vintages are on disk, and the baseline needs the later one.** The
spec as first written cited only V5.0. The operator has since supplied V6.0.

- `af_he-msca-dn_en.pdf` is **V5.0, 29.04.2025**, 56 pages, Part A form plus the Part B template.
  Its instructions read *"For the 2025 call"*. This is the form the submitted proposal was written
  against.
- `Tpl_Application Form (Part B) (HE MSCA DN).pdf` is **V6.0, 04.04.2026**, 34 pages, Part B only.
  Its instructions read *"For the 2026 call"*. This is the structural authority for the baseline.

The form's own HISTORY OF CHANGES gives the whole delta across the two versions:

| Version | Date | Change |
|---|---|---|
| 5.1 | 05.11.2025 | Tags removed |
| 6.0 | 26.03.2026 | Part B2 gains section 11, RAISE DN, for applicants of `HORIZON-RAISE-2026-01-MSCA` |

**Consequence — decision 3 is now measured, not assumed.** For
`HORIZON-MSCA-2026-DN-01-01`, the two forms are structurally identical:

- The same ten numbered aspect headings, §1.1 to §3.2.
- The same Tables 3.1 a to 3.1 e.
- The same two-document split, with Part B1 capped at 34 pages and sections 1–3 at 30, section 1
  starting on page 5.
- The same Part B2 sections 4 to 10.

Section 11 is the only addition and it belongs to a different call. So assessing a V5.0 submission
under a V6.0 profile introduces no structural mismatch. The spec previously carried that as a
declared risk; it is now a checkable fact.

**Two defects in the source.** V5.1 records *"Tags removed"*, but two template tags survive in
V6.0: `#@APP-FORM-HEMSCADN@#` and `#@REL-EVA-RE@#`, the latter glued to the Excellence heading as
`Excellence #@REL-EVA-RE@#`. V5.0 still carries eight distinct tags in sixteen places. Any
heading derived from either PDF must strip `#@...@#` before use. Separately, the history table
dates V6.0 to 26.03.2026 while every page footer dates it 04.04.2026; the footer is cited here and
the discrepancy is recorded, not resolved.

**2.11 The page count carries no information about the proposal.** The copy runs 84 pages and DN
Part B1 is capped at 34. Earlier in the discussion I treated that gap as a signal, which was
wrong.

The operator states the copy is an almost verbatim transcript of the 34-page original, reformatted
during sanitisation. Three measurements agree:

- The body is set at 12 pt — 117,953 of 118,993 characters.
- Table 3.1 a has become label-value lines (`WP Number:`, `WP title:`, `Lead participant`),
  pp. 42–51.
- Bullet lists print one item per line, each bullet on its own two lines.

Tables 3.1 b, c, d and e survived as real tables, 17 of them across pp. 51–65. So the copy holds
the assessed content at roughly the assessed volume, spread over more pages.

**Consequences.** No page-based judgment of length, density or page-limit compliance may be made
from this file. The original's compliance with the 34-page cap is not in question here and is not
testable from the copy. The reflow is a declared transformation in the fidelity register, not a
finding.

---

## 3. The DN evaluation bundle

### 3.1 The ten DN aspects

Derived from `ef_he-msca_en.pdf` pp. 4–6 by option tag, cross-confirmed verbatim against the ESR.

| Anchor | Aspect id | Criterion | Option tag | Form page |
|---|---|---|---|---|
| 1.1 | `exc-obj` | Excellence | MSCA Doctoral networks, Postdoctoral fellowships | 4 |
| 1.2 | `exc-method` | Excellence | MSCA Doctoral networks, Postdoctoral fellowships | 4 |
| 1.3 | `exc-training` | Excellence | MSCA Doctoral networks | 4 |
| 1.4 | `exc-supervision` | Excellence | MSCA Doctoral networks | 4 |
| 2.1 | `imp-structuring` | Impact | MSCA Doctoral networks | 5 |
| 2.2 | `imp-career` | Impact | *untagged, see 3.2* | 5 |
| 2.3 | `imp-dissemination` | Impact | all MSCA except Special needs allowances and COFUND Choose Europe | 6 |
| 2.4 | `imp-magnitude` | Impact | MSCA Doctoral networks, Postdoctoral fellowships and Staff exchanges | 6 |
| 3.1 | `impl-workplan` | Implementation | all MSCA except Special needs allowances and COFUND Choose Europe | 6 |
| 3.2 | `impl-participants` | Implementation | MSCA Doctoral networks and Staff exchanges | 6 |

Excluded, and the scorecard must say so: the PF-only `exc-supervision` two-way-transfer aspect and
`exc-researcher` professional experience; every Staff exchanges, COFUND, COFUND Choose Europe and
Special needs allowances variant.

### 3.2 A defect in the source form, resolved

The Impact bullet *"Credibility of the measures to enhance the career perspectives and
employability of researchers and contribution to their skills development."* carries a closing
`]` with **no opening `[OPTION …`**. The DN bracket opened at `imp-structuring` and closed at
*"developing sustainable elements of doctoral programmes. ]"*.

It is resolved to DN on three grounds, all recorded in the scorecard and the decision log:

1. The plural *"researchers … their"* matches DN; the PF variant immediately below is singular
   (*"the researcher … his/her"*).
2. The ESR, assessing a DN proposal, lists it as one of the four Impact aspects considered.
3. No other variant's bracket is open at that point in the document.

### 3.3 Scoring

Scale 0–5, one decimal place. Levels verbatim from the form p. 2: 0 fails to address or cannot be
assessed; 1 Poor; 2 Fair; 3 Good; 4 Very Good; 5 Excellent.

Weights 50 / 30 / 20. Total out of 100:

    S = 10·E + 6·I + 4·Q

Thresholds: 3 per criterion (General Annexes p. 27), 70 overall out of 100 (form p. 2). The ESR's
4.20 / 4.50 / 4.20 → 85.80 confirms the arithmetic.

### 3.4 Proposed artifacts

| Artifact | Content |
|---|---|
| `harness/evaluator_scorecard_msca_dn.json` | Ten aspects verbatim, `dn_scope_rule`, `excluded_aspects`, scoring block, provenance pinning both forms and the General Annexes page, the Annex-D override note, and the §3.2 resolution |
| `harness/rubrics_msca_dn.json` | Ten rubrics, specificity-based per decision 14, anchors as above, generously authored `selection_terms` |
| `harness/profiles/msca_dn_default.json` | `applicable_variant: "Doctoral networks"`, the three criteria, the component pins |
| DN entry in `evaluator_expectation_registry.json` | Additive third instrument alongside RIA and MSCA-PF |

---

## 4. The candidate

### 4.1 Page map of the sanitised copy

| Pages | Maps to | Notes |
|---|---|---|
| 1–13 | `1.1` | Unlabelled. Carries the AF's three required sub-headings |
| 14–21 | `1.2` | |
| 22–26 | `1.3` | With 1.3.1–1.3.4 |
| 27–31 | `1.4` | With 1.4.1–1.4.2 |
| 32–33 | `2.1` | With 2.1.1–2.1.3 |
| 34–35 | `2.2` | |
| 36–38 | `2.3` | |
| 39–40 | `2.4` | |
| 41–64 | `3.1` | WP descriptions pp. 42–50 are Table 3.1 a, unlabelled and flowed to prose |
| 51 | Table 3.1 b | Deliverables List (Sanitized) |
| 58 | Table 3.1 c | Milestones List (Sanitized) |
| 61 | Table 3.1 d | DC Table (Sanitized) |
| 62 | Table 3.1 e | Project Risks (Sanitized) |
| 65–66 | `3.2` | |
| 67 | `4` | Recruitment strategy |
| 68–72 | `5` | Network organisation (Fully Sanitized); carries AF §6 Supervisory board |
| 73–74 | `6` | Ethics Self-Assessment (Sanitized); matches no AF Part B2 section |
| 74–75 | `7` | Green Charter (Sanitized) |
| 76–84 | `8` | Participating Organisations, unlabelled |

### 4.2 Candidate shape

Three section artifacts, materialised by the existing document route.

    excellence_section.json       sub_sections: 1.1 1.2 1.3 1.4
    impact_section.json           sub_sections: 2.1 2.2 2.3 2.4
    implementation_section.json   sub_sections: 3.1 3.2 4 5 6 7 8

Rubric anchors stay 1.1–1.4, 2.1–2.4, 3.1–3.2, so each aspect's dedicated answer keeps its
`ANCHOR_SCORE_BONUS`. The Part B2 sub-sections carry no anchor and compete on selection terms,
which is what lets aspect 3.2 reach the hosting and partner-role prose the ESR's Implementation
comment rests on.

---

## 5. Decisions

| # | Decision | Reason |
|---|---|---|
| 1 | Branch `msca-dn-pre-eval` from `dev_graph_demo`; the real project gets its own graph root | The demo's 267 nodes and its BIODIV `sources.json` must not enter the assessment. Isolation by path, not by discipline |
| 2 | Move both PDFs to `docs/tier3_project_instantiation/source_materials/msca_dn/` | Stops the demo's Tier 3 and the real project's Tier 3 sharing a directory, and gives the fidelity register a home beside its subject |
| 3 | One profile, `msca_dn_2026_default`, pinned to on-disk 2026-2027 sources and to AF **V6.0** | The 2025 call and work programme are absent. A 2025 profile would rest on generic programme knowledge, which §10.6 and §13.9 forbid while sources are reachable elsewhere. §2.12 now shows the V5.0 and V6.0 forms are structurally identical for this call, so the vintage mismatch costs nothing |
| 4 | The blind cell reports addressal and grounding as two values; ledger grounding is withheld from the blind lane and owned by the integrity audit | The ledger is not trustworthy for an imported proposal — 90 of the demo's claims declare source-grounding with no span. `expectation_grounding.py` already owns that axis, and `rubric.py` combines the two without blending. Two values is what stops an unassessable half from reading as a clean score |
| 5 | A separate criterion-grading stage, five samples per criterion, for the holistic 0–5 score | General Annexes p. 27 awards scores for criteria, not aspects. The cells inform the grading; they are never arithmetic input. "One extra call" was the earlier wording and contradicted decision 11 and PE-04, which both specify N=5 |
| 6 | Add `include_claims: bool = True` to `build_evidence_pack`; the DN blind lane passes `False` | Makes decision 4 structural rather than prompt-level. One record then serves both lanes, so integrity findings and the baseline share a candidate hash |
| 7 | Import all of Part B1 and B2; B2 as implementation sub-sections | Dropping B2 would make several ESR observations unassessable for a reason the import caused |
| 8 | Tables render to pipe-delimited rows, one paragraph per row | Row boundaries survive, each row is independently selectable, and the budget filler never splits a row. Byte-reproducible from the PDF |
| 9 | Fidelity register carries derived and declared halves, each marked. Every sub-section carries two independent fields, `presence` and `transformation` | A declaration must never be mistaken for a measurement. The missing figures, the keyword counts and Table 3.1 a's flattening to label-value lines are checks that rerun; the reflow, the dependency judgment and the per-sub-section fidelity are declarations only the operator can make. Two fields because a present but heavily sanitised section is not an absent one, and collapsing them would send a false evidence gap into PE-08 |
| 10 | Assessor: `--transport claude-cli`, `claude-sonnet-5`, version tag naming the transport | The Groq pin's key returned 401, and its TPM ceiling forces the 3000-token pack budget that predetermined the demo's grades. The drafter here is a human, so grader–generator model independence is not at stake. Transport and vendor independence are lost and the report's pin says so |
| 11 | N=3 for the ten cells, N=5 for the three criterion scores; report median and spread, labelled **within-assessor repeatability** | The quoted number gets the most evidence. The spread measures one pinned assessor's run-to-run variability over an identical prompt, and nothing else. It cannot say how much of the distance from 85.80 is assessor variance: that would need a second assessor, and the ESR's figures come from human evaluators. An earlier wording claimed the decomposition and the report must not |
| 12 | The ESR lives as an immutable Tier 4 artifact the builder never reads. Separately, the assessor runs with `--tools ""` from a working directory outside the repository, and a planted-marker test checks the rendered prompts | Snapshot exclusion makes the ESR unreachable *through the package*, and that is all it makes. It says nothing about what the assessor process can open. §2.13 measured that gap and found it open. The two controls are independent and the spec needs both. `finding` nodes have no record source anyway (§2.10) |
| 13 | ESR observations are operator-authored, verbatim, severity from the ESR's own wording; strengths recorded too | Nothing inferred in the one artifact that must stay verbatim. The ESR already labels eight shortcoming clusters. Strengths let the comparison catch a blind finding the evaluators praised |
| 14 | Every DN rubric keeps a substantiation step. Where the pack carries no claim ledger the cell reports grounding **unassessable**, never failed and never passed. Specificity is judged in addition, not instead | Sanitisation removed the reference apparatus (§2.8), but the rubric set is reused at PE-09 and for the resubmission. Deleting a dimension to suit one damaged candidate would carry the workaround into the authoritative evaluation. Unassessable keeps the instrument whole and still refuses to penalise a sanitisation artifact |
| 15 | PE-07 audits internal consistency now; the grounding axis is wired but reports every claim Unresolved with reason "supporting sources removed by sanitisation" | A claim extracted from the proposal is trivially entailed by the proposal. Consistency is substantive here and is where the ESR actually found a shortcoming |
| 16 | Preflight is a separate command whose hash `assess` requires and re-binds. It binds **two** hashes: the realised pack set and the import manifest | Keeps the harness advisory to the pipeline while making the preflight mandatory to the operator. Mirrors the existing `verify` discipline. The pack-set hash detects any change in selected evidence. It is not provenance: a hash of an output cannot identify the process that produced it, so two extractor versions that happen to agree byte-for-byte are indistinguishable by it. An earlier wording claimed the pack hash covered extraction and normalisation versions, which was wrong |
| 17 | Schema bump to `orch.dev_graph.document_snapshot.v2`, which requires a span for `source_grounded`; v1 is grandfathered | Closing the hole in place would break the demo record, 72 committed package manifests, 4 snapshot artifacts, and a test that pins the blank `source_ref` as expected behaviour. The demo closed on 2026-10-03 |
| 18 | Sanitisation provenance goes in a `provenance` header on the fidelity register, which the intake references | `EsrIntake`'s eight fields are fixed and none can carry it. A new artifact beats a schema extension, consistent with decision 12 |

### Consequences recorded rather than decided

- The consistency audit parses the rendered pipe-delimited rows at audit time. Decision 8 keeps a
  single import pipeline, and the rendering is the structure.
- PE-07 must run **after** the baseline is frozen. Writing Tier 3 records moves the snapshot id,
  which the blind report stamps.
- Candidate hash is unaffected by Tier 3 records: `candidate_hash` covers only the materialised
  passages and claims.
- With zero claims the blind pack still gets only `span_budget_fraction` of the budget unless
  `include_claims=False` reclaims it, which decision 6 does.

---

## 6. Workspace layout

    proposal_orchestrator/
      docs/tier3_project_instantiation/source_materials/msca_dn/
        sanitized_proposal_final.pdf          the originals, never rewritten
        MSCA DN ESR.pdf
      docs/tier4_orchestration_state/msca_dn/
        esr/msca-dn-2025-esr.json             never snapshotted
        comparisons/<blind report hash>.json
      workspaces/msca_dn/                     <-- --graph-root
        docs/tier3_project_instantiation/source_materials/sources.json
        docs/tier4_orchestration_state/dev_graph/
          documents/  intake/  snapshots/  packages/

`--graph-root` is a repository root: `build_snapshot` resolves `sources.json` and `documents/`
relative to it, and those nine relative paths are module constants.
`tests/harness/test_blind_leakage.py:170` already passes a minimal tree this way.

Source provenance uses one `source` record per PDF page, `SRC-DN-P01` … `SRC-DN-P84`, each holding
that page's extracted text. A `verified_span{source_id, start, end}` then resolves to a page and an
offset, and `runner/dev_graph/builder.py:395` validates the offsets against the text at snapshot
time. The source schema is permissive, so this needs no engine change.

---

## 7. Tickets

### PE-01 — Workspace, intake and provenance freeze

Create the branch. Move both PDFs. Build `workspaces/msca_dn/`.

Author the intake record with `prior_submission: true`, `esr_availability: "available"`, an
`esr_reference` and `permitted_purpose: "blind_pre_evaluation"`.

The two call bindings are distinct and each has one owner:

| Binding | Owner | Value |
|---|---|---|
| Call the ESR evaluated | the intake's `call_id`, with `submission_id` | the 2025 DN call |
| Call the baseline targets | the profile, the run label and the report | `HORIZON-MSCA-2026-DN-01` |

`EsrIntake` carries one `submission_id` and one `call_id`, documented as the identifiers of the
submission the intake concerns, and the record is immutable. Putting the 2026 target there would
make a permanent false statement about which call the ESR evaluated. No schema change is needed.

Nothing enforces this today. `blind_assessment` reads only `permitted_purpose`, `document_id`,
`esr_availability` and `intake_id`; `call_id` is read by nothing, so the wrong value would fail
nothing and sit in an immutable record.

Author the fidelity register's `provenance` header. It declares five things:

- Historical submission: MSCA-DN 2025.
- Current assessment artifact: a sanitised derivative.
- Transformation: identifiers generalised, some prose omitted or rephrased, all figures lost, all
  citations removed, and the whole reformatted — 12 pt body, Table 3.1 a flattened to
  label-value lines, one bullet per line — which reflows 34 pages to 84.
- Relationship to the ESR: same underlying project, different assessment text.
- Authoritative original: available only inside the private network.

**Acceptance.** Every input has a declared version and role. No demo record is reachable from the
real graph root. The sanitised candidate is nowhere described as the submitted version. A test
asserts the intake's `call_id` is the historical call and differs from the profile's target call,
since no engine path checks it.

### PE-02 — DN evaluation bundle

The four artifacts of §3.4.

Scoring authority is the evaluation form. Structural authority is AF **V6.0**, with the V5.0
equivalence of §2.12 recorded in the bundle's provenance. Part B2 section 11, RAISE DN, is listed
among the excluded aspects: it belongs to `HORIZON-RAISE-2026-01-MSCA`, not to this call.

A fifth artifact: the **criterion appendix mapping**, naming which table rows each criterion
receives beyond its own section. It is versioned with the rubric set, not assembled at scoring
time, because a silent change to it changes scores.

**Acceptance.** All ten aspect texts byte-match the evaluation form, derived from the PDF and not
typed, after `#@...@#` tags are stripped per §2.12. The AF V6.0 section headings §1.1 to §3.2
confirm the ten anchors one-to-one, and a test pins that correspondence. The §3.2 bracket
resolution is recorded with its three grounds. The RIA and MSCA-PF registry entries are
byte-identical after the DN entry is added — a test pins all three, because Phase 1 has destroyed
the MSCA-PF entry before. A test asserts the PF-only researcher-experience and two-way
knowledge-transfer aspects cannot enter a DN assessment, and that section 11 cannot.

### PE-03 — External proposal import

`tools/import_external_proposal.py` does seven things:

- Extract text per page.
- Write the 84 source records.
- Map sections and sub-sections per §4.1.
- Render the tables per decision 8.
- Extract the audit claim ledger.
- Emit a v2 document record.
- Write the fidelity register's derived half.

**The ledger is an input, frozen here.** An earlier draft of this ticket emitted a record with no
claims. That contradicted decision 6, whose only purpose is to let one record serve both lanes
with the claims excluded structurally from blind packs, and decision 15, which enumerates every
claim as Unresolved. Over zero claims both are inoperative.

The ledger cannot live in a separate artifact. `build_evidence_pack` calls
`load_section_claims(section_path)` on the same file as the prose
(`harness/evidence_pack.py:575`), reading `validation_status.claim_statuses`. It raises on an
absent array, so `include_claims: False` must skip the load rather than be handed an empty file.

Claims are extracted before any assessment runs, so candidate identity is fixed at import.
Audit **findings** are the integrity audit's output and go to its report, never into the record.
No extracted claim may declare `source_grounded`: these are proposal assertions with no external
source, which is why decision 17's v2 tightening does not bite here.

**Acceptance.** Sub-section prose matches the PDF verbatim under a declared normalisation.
Re-running the importer produces byte-identical output. All 17 tables render and every row parses.
Extraction losses are recorded, including the zero figures and the zero dependency strings. The
originals are untouched.

### PE-04 — Evaluator scoring contract

`include_claims` threaded from the CLI to `build_evidence_pack`. A criterion-score grader: holistic
0–5 per criterion, official descriptors, named shortcomings, N=5, median and spread, and
`S = 10E + 6I + 4Q` with both thresholds checked. New report fields.

**What the scorer reads.** The complete criterion section verbatim, not a selected pack. Aspect
findings may accompany it and may never replace it: a scorer fed only the ten findings grades the
harness's own summaries.

Whole sections fit the `claude-cli` pack budget of 32,768:

| Criterion | Pages | Characters | ≈ tokens |
|---|---|---|---|
| Excellence 1.1–1.4 | 1–31 | 45,679 | 11,400 |
| Impact 2.1–2.4 | 32–40 | 18,290 | 4,600 |
| Implementation 3.1–8 | 41–84 | 59,274 | 14,800 |

So the criterion lane carries no selection at all — no `not_relevant` exclusions, no budget
filler, and nothing for the preflight to bind beyond the section bytes.

Cross-section evidence is the one case needing design. `build_evidence_pack` takes a single
`section_path`, and the profile maps each criterion to one section. So an Impact aspect reaching
the deliverables table in `implementation_section` is not expressible as one pack. Those rows are
named as a declared appendix rather than left to term matching.

There is no pack in this lane, so there is no pack status to inherit. The criterion input is the
section bytes plus the appendix rows the PE-02 mapping declares, and both need their own
accounting.

**Acceptance.** Every criterion score names its **complete** input by hash — section bytes and
appendix rows together, not the section alone. A completeness check covers that whole input: every
declared appendix row resolved, and the assembled input fit the budget without truncation. The
appendix mapping version is recorded on every score. No criterion score is produced from aspect
findings alone, and a test asserts that.

**Acceptance.** With `include_claims=False` no claim is loaded, rendered or charged to the budget,
and prose receives the whole usable budget. PF and RIA behaviour is unchanged. No code path derives
a criterion score from cell arithmetic. A test pins 4.20 / 4.50 / 4.20 → 85.80.

### PE-05 — Evidence preflight

A command reporting seven things:

- Anchors present, against the ten the profile declares.
- `not_relevant` exclusions per expectation, with their token cost.
- `over_budget` exclusions.
- Table rendering and row-parse counts.
- Package completeness under the package budget.
- The leakage scan, including that `esr/` is never snapshotted.
- The pins, which are the candidate, the profile and the policy, **and** every input that selects
  evidence.

`assess` requires its hash and refuses on mismatch.

**What the pins must cover.** Candidate, profile and policy hashes leave the budgets unbound, and
the budgets decide what the assessor sees. This is not hypothetical here: the demo recorded F9 on
2026-10-02, where a provider's rate-limit-derived pack ceiling predetermined every grade.

The complete set of inputs to `build_evidence_pack` is `expectation_key`, `section_path`,
`selection_terms`, `anchor_sub_section_ids`, `token_budget`, `span_budget_fraction`,
`max_token_budget`, plus `include_claims`. The profile's rubric-set version covers the terms and
the anchors. The three budgets arrive as CLI flags and are covered by nothing.

So the preflight binds the **realised pack set**, which is deterministic in all of the above and
so detects any change in selected evidence, including from parameters nobody enumerated.

It binds the **import manifest** separately. A hash of an output cannot identify the process that
made it: two extractor or normalisation versions that produce byte-identical packs are
indistinguishable by the pack hash. That is adequate for replaying this baseline and inadequate as
provenance, which matters at PE-09, where the same extractor meets the unsanitised original. The
manifest carries the extractor version, the normalisation version and the table-rendering version.

The parameter values are reported alongside both hashes, because a bare mismatch does not say what
moved.

**Acceptance.** No required evidence is omitted without an explanation in the report. A changed
candidate invalidates the preflight. `not_relevant` volume is visible, since that exclusion does
**not** flip the pack to `insufficient_context` (`harness/evidence_pack.py:593`).

### PE-06 — Blind baseline, frozen

Run and freeze. Review before PE-07 and PE-08 begin.

**Acceptance.** The report binds to the candidate hash, profile version, assessor pin, snapshot id
and package id, and the preflight pack-set hash. The assessor pin names the transport. Cells and
criterion scores are both present, with spreads.

Blindness is tested, not asserted. Three conditions, all required:

1. The assessor is invoked with `--tools ""` and a working directory outside the repository, per
   §2.13 and decision 12.
2. A test plants a unique marker string in the ESR artifact and in a Tier 5 draft, then asserts
   neither marker appears in any rendered prompt.
3. A test asserts the invocation carries an explicit empty tool list, at the argv level rather
   than at the Python keyword, which is where `test_subscription_judge.py:65` stops.

### PE-07 — Integrity audit

Internal consistency over the parsed table rows. Five checks:

- Work-package table against work-package prose: lead, start and end month, DCs involved.
- Each deliverable's work package exists, and its month fits that package's window.
- Each milestone's month against the months of the deliverables it depends on.
- DC table against the individual DC research projects described in 1.1.
- Risk table against the mitigations named in prose, and whether any threshold is stated.

The grounding axis enumerates the PE-03 ledger and reports every claim Unresolved with its
reason. It has claims to enumerate because PE-03 extracts them; an empty ledger would make this
and decision 15 vacuous. The five consistency checks above need no ledger — they read parsed table
rows — so only this axis depends on the import.

**Acceptance.** Unsupported claims, missing sources and uncertain facts stay visible as separate
findings. No consistency finding is reported as a proposal-quality score. The baseline's snapshot
id is unchanged by anything PE-07 writes, or the report says the baseline was re-derived.

### PE-08 — ESR comparison and handoff

Author the ESR record. Build the comparison command over the frozen blind report. One row per
observation with: historical finding and location, criterion and aspect, historical proposal
evidence, current proposal evidence, corresponding blind finding if any, disposition, explanation.

Dispositions: *independently detected*, *partially observable*, *not assessable from this copy*,
*not detected despite sufficient preserved evidence*, *addressed*. Criterion scores are compared
separately from qualitative findings, and no deduction is attributed to any individual criticism.

**Acceptance.** Every historical observation has a traceable disposition. The report states how
much of the comparison was assessable. *Not assessable* is never counted as a model failure and
never silently dropped. Proposed revisions are prioritised in a separate artifact.

### PE-09 — Private-network validation (declared, not built)

An acceptance stage, not work in this milestone. Inside the approved environment, in order:

1. Import the original submission and check extraction fidelity against it.
2. Freeze a blind historical assessment before the ESR is introduced.
3. Investigate score differences and missed findings.
4. Assess the final resubmission as a new candidate under its applicable profile.

Historical and resubmission profiles stay separate wherever their rules differ.

---

## 8. Risks

| Risk | Status |
|---|---|
| The copy is an 84-page reflow of a 34-page original | Declared in the register (§2.11); no page-based judgment is admissible, and none is made |
| Zero citations survived | Grounding is reported unassessable per decision 14, never failed and never passed. The substantiation step stays in the rubric set for PE-09 |
| The assessor process can read the repository (§2.13) | Open until decision 12's `--tools ""`, the external working directory and PE-06's planted-marker test are in place. Wider than this milestone: cli-prompt mode shares the defect |
| Zero figures survived | Recorded. Bears on the ESR's work-package dependency shortcoming, but does not by itself establish that dependencies are undescribed — see §2.7, where the keyword counts are derived and the adequacy judgment is declared |
| The 2025 call and work programme are absent | Decision 3 avoids depending on them. For the application form the gap is closed: §2.12 measures V5.0 against V6.0 and finds no structural difference for this call. The work programme and call text remain 2026-only |
| §5 Network organisation is heavily sanitised | Recorded `presence: present`, `transformation: identifiers removed`. It carries 9,830 characters across pp. 68–72, including the Supervisory Board and work-package leads. It is **not** `omitted`, and labelling it so would send a false evidence gap into PE-08 |
| Ethics occupies the §6 slot, which matches no AF Part B2 section | Recorded in the mapping; not graded by any DN aspect |
| AF §10 Declaration on the use of AI is absent | Recorded; not graded by any DN aspect |
| Repeated samples measure repeatability, not expert agreement | Stated on every report carrying a spread |
| One proposal–ESR pair is a case study | Stated; not treated as validation of scoring accuracy |
| The impact planner stays in shadow mode; the harness stays advisory | Unchanged by this milestone |

The repository's existing test failures stay documented. Every new assessment-path check must pass
before the baseline is relied on.
