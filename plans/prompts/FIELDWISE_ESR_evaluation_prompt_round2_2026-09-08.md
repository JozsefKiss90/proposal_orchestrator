# FIELDWISE — Round-two ESR-equivalent evaluation prompt

Prepared: 2026-09-08  
Repository: `JozsefKiss90/proposal_orchestrator`, branch `ESR`  
Purpose: independent scoring of the refactored Part B1, followed by a round-one closure audit and a surgical revision handout.

## Operator notes — read before running

This prompt follows the structure of `plans/prompts/FIELDWISE_ESR_evaluation_prompt_2026-09-08.md`: three evaluator lenses, consensus ESR, diagnostic scoring sheet, revision handout and machine-readable findings. It changes the assessed artefact and limits the assessment to Part B1. It does **not** evaluate the complete application, certify eligibility, predict a funding decision or rewrite the proposal.

The current PDF is a refactored export, not an evidenced new portal submission. Do not attach the original submission receipt, seal or submission timestamp to it.

| Version identifier | Value verified when this prompt was prepared |
|---|---|
| Repository commit | `e8e8d23895d0f223a70cccbf986d62ba86b8ad1a` |
| Current PDF | `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_refactored_2026-09-08.pdf` |
| SHA-256 | `6fb56e517df9eef5bd5de3258d414b67e0781f44c90a095aad4d0fefcc643371` |
| File size | 446,718 bytes |
| Physical pages | 10; A4; unencrypted |
| Assessed content | Part B1 Sections 1–3; physical PDF pages 1–10 |

Run the text between the agent-prompt markers in Claude Code or another document-capable reviewing environment. For a genuinely fresh assessment, start a new session. Give independent evaluator agents only the permitted first-pass materials, not this prompt's post-score audit checklist or historical context. If isolated agents are unavailable, use three sequential simulated lenses and disclose that they are not genuinely independent.

Important departures from round one:

- The official documents govern scoring; the earlier prompt's numerical severity caps and 92-point “fundable zone” are not official rules and must not be inherited as such.
- The earlier ESR, answer bank and refactoring report are withheld until current-version scores and comments are frozen.
- Part A and Part B2 are excluded. Their absence is a scope limitation, not a new weakness or an automatic deduction.
- Formatting is rechecked against the actual 2026 RTF template. Its 11-point minimum applies to body text **including text in tables**. The earlier refactoring instructions' blanket treatment of tables as “other text” must not override this rule.
- No source file is modified. Only the two new round-two reports are written; temporary extraction/rendering files may be created separately.

Suggested location for this prompt: `plans/prompts/FIELDWISE_ESR_evaluation_prompt_round2_2026-09-08.md`.

=== AGENT PROMPT BEGINS ===

# 0. Mission and assessment boundary

Produce a second-round, explicitly **simulated, Part-B1-only ESR-equivalent assessment** of FIELDWISE, proposal 101373105, for HORIZON-MSCA-2026-PF-01-01, European Fellowship, ENV panel.

Deliver, in this order:

1. A fresh assessment of the current PDF against the official PF award criteria, including three individual evaluations and a reasoned consensus.
2. A diagnostic scoring and technical-compliance sheet, clearly separate from the ESR-style comments.
3. A comparison against the first ESR and its individual evaluations, identifying genuine resolutions, residual weaknesses, regressions and new weaknesses.
4. A prioritised, page-budget-aware Part B1 revision handout, with honest safe responses where owner facts remain unavailable.

Evaluate what the current PDF actually says, not what its authors intended, what the brief recommended or what a future revision could achieve. Do not assume that refactoring improves the score. Do not assume that an accepted answer is scientifically adequate merely because the user accepted it.

Do not rewrite or edit the proposal, change its Gantt, modify Tier 3, create agreements, contact organisations, commit, push or upload anything to the submission portal.

# 1. Sources and evidence firewall

## 1.1 Repository instructions

Read applicable `CLAUDE.md` instructions for this review and for writing its reports. Do not launch an unrelated proposal-generation workflow. Treat project facts encountered in repository instructions as outside the scoring evidence set.

## 1.2 First-pass inputs — assessment evidence only

Read these before scoring:

1. `docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_en.pdf` — scoring descriptors, PF criteria and ESR structure. Verify the version; the earlier evaluation used V2.2, 17 December 2025.
2. `docs/tier2b_topic_and_call_sources/work_programmes/msca/wp-2-marie-sklodowska-curie-actions_horizon-2026-2027_en.pdf` — PF scope, expected outcomes, secondments, placement, award criteria, thresholds and evaluation procedure. Locate by headings; do not assume viewer page numbers equal printed pages.
3. `docs/tier2a_instrument_schemas/application_forms/msca/Tpl_Application Form (Part B) (HE MSCA PF).rtf` — actual Part B1 instructions and formatting rules, including table text. Do not replace it with an older template or a previous prompt's paraphrase.
4. `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_refactored_2026-09-08.pdf` — all ten pages, including footnotes, tables and the rendered Gantt.

If an applicable rule needs verification, consult the official call page and its official linked documents only:

`https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/HORIZON-MSCA-2026-PF-01-01`

Record source versions and any conflict. Distinguish binding call/template rules from diagnostic preferences. Do not introduce rules from another MSCA action. Do not use the internet, source DOCX, partner websites, repository background files or author reports to supply missing proposal evidence. A citation in the PDF is evidence of what the proposal cites, not permission to import an entire external biography or research paper into the application.

## 1.3 Materials withheld until scores are frozen

Only after completing and freezing the current-version E1–E3 evaluations, consensus comments and scores, read:

- `plans/prompts/FIELDWISE_ESR_evaluation_prompt_2026-09-08.md` — historical method, not overriding instructions.
- `plans/reports/FIELDWISE_ESR_2026-09-08.md` — especially `1. EVALUATION`, `II.1 Findings Register`, `II.3 Do-not-touch`, `II.4 Open Decisions for Owners` and Annex A, E1–E3.
- `plans/reports/FIELDWISE_ESR_2026-09-08.json` — finding IDs, watchlist relationships, actions and owner decisions.
- `plans/reports/FIELDWISE_Part_B1_Scoring_Improvement_Brief_2026-09-08.md` — accepted answers, safe responses, protected material and cut pool.
- `plans/reports/FIELDWISE_Part_B1_refactoring_report_2026-09-08.md` — claimed edits, substitutions, omissions and validation results; these are claims to verify, not proof.
- `docs/tier5_deliverables/submitted/FIELDWISE_101373105_submitted_2026-09-07.pdf` — **only Part B1, physical pages 24–33**, for textual comparison. Its original SHA-256 is `c3bfb51f93b4c0c36221d0bd83dab77efaa619eee4f3dd937e58d728c3f81dbe`.
- `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_refactored_2026-09-08.docx` and `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_gantt_refactored_2026-09-08.png`, only if useful for diagnostic layout/source checks or actionable edit anchors. They cannot replace the rendered PDF as assessment evidence.
- The user's latest edited refactoring prompt, if supplied, only as operator context for implementation-intent and do-not-touch checks.

Freeze means preserve the first-pass text and numerical results in working notes before opening these materials. Record the assessment sequence and any unavoidable prior exposure. Do not claim blindness if the same session already read the old ESR or brief.

Historical material may reveal a missed current-PDF issue. Re-open an assessment only for a specific, independently verifiable current-PDF or official-rule error, recording the original verdict, new evidence, revised verdict and reason. Never silently adjust the fresh score towards an earlier score or target.

# 2. Scope exclusions and fair treatment of missing facts

Score only Part B1 Sections 1–3. Do not assess or request fixes to Part A, Part B2, portal participant registration, CV date formatting, residence tables, ethics tick boxes or receipt details. Do not recreate the Part A abstract or participant table in the ESR header. Use only identifiers and organisational roles supported by the current B1, with operator-supplied administrative identifiers labelled as metadata.

Because a real PF evaluation considers the full application, prominently state that these scores are a **B1-only diagnostic using the official criterion scale**, not an official or complete-application evaluation. Do not mark excluded questions “No” or “compliant”; use “not assessed in this B1-only review”. A B1 requirement may still be insufficiently addressed, but do not insist that every item normally located in B2 be duplicated in B1.

Distinguish:

- **A proposed project commitment:** an assessable future protocol, activity, target, gate or resource-provision plan.
- **An existing fact:** secured access, allocated equipment, a signed contract, an awarded qualification, proven capacity or past results.
- **A contingent fallback:** a route that must preserve scientific validity and be feasible within the stated time and resources.

Do not demand written confirmations merely because an agreement is not reproduced in B1. Verify whether a document is actually required at submission for this EF action. Do not import Global Fellowship outgoing-host letter requirements into EF secondments or placements. Arrangements obtainable after submission but required before access or activity must be assessed through the stated responsibility, deadline, dependency and contingency.

Conversely, honest conditional wording does not automatically remove a delivery weakness. Identify any critical dependency that remains inadequately supported, explain its scoring consequence, and distinguish that from a missing mandatory submission document. Missing evidence is not proof that an agreement, facility or capability does not exist.

# 3. Evaluators and scoring method

Use three lenses; each evaluates all three criteria:

- **E1 — physiology, agronomy and irrigation:** independent stress reference, experimental units, replication, crop-stage effects, validation precision, field logistics and agronomic relevance.
- **E2 — Earth observation and statistical learning:** spectral/scale transfer, leakage prevention, model/reference compatibility, uncertainty, calibration, prospective testing, reproducibility and research-to-software boundaries.
- **E3 — experienced MSCA PF evaluator:** objectives and instrument fit, supervision, training, researcher development, two-way transfer, dissemination/exploitation/communication, magnitude, implementation, hosting and formal presentation.

Use isolated evaluator contexts if supported. Each receives the current PDF and official sources, records all criterion scores before seeing another evaluator's opinion, and returns exact page/section anchors. Otherwise disclose sequential simulation. Do not require a fixed number of weaknesses: an arbitrary quota must not manufacture findings.

## 3.1 Official criteria and diagnostic aspect IDs

Read the exact aspect wording from the official sources. Use these identifiers consistently:

| Criterion | Weight | Diagnostic aspect IDs |
|---|---:|---|
| Excellence | 50% | `exc-obj`, `exc-method`, `exc-supervision`, `exc-researcher` |
| Impact | 30% | `imp-career`, `imp-dissemination`, `imp-magnitude` |
| Quality and efficiency of the implementation | 20% | `impl-workplan`, `impl-host` |

Score each criterion holistically from 0 to 5, to one decimal, using the official descriptors. Compute:

`total = 10 × Excellence + 6 × Impact + 4 × Implementation`

Report the total to two decimals. Verify the applicable criterion thresholds, overall threshold and Seal conditions from the official documents; the round-one sources specify 3.0 per criterion, 70 overall and 85 for the Seal score condition.

Severity labels are diagnostic: critical, major or minor, with an explanation of consequence. Do not subtract a fixed tariff per finding, impose the earlier prompt's 4.4/3.0 caps, or mathematically average aspect scores into criterion scores. Optional aspect scores must be clearly labelled non-official diagnostics. Avoid double-counting overlapping symptoms. Assign a primary scoring aspect and identify any genuinely distinct cross-criterion consequence.

State whether the B1 diagnostic reaches the relevant numerical thresholds. Do not claim an actual Seal, guaranteed eligibility, actual fundability or a known 2026 panel funding cutoff. If reporting distance to 92 for continuity with round one, label it **a legacy internal benchmark, not an official threshold or demonstrated funding line**. Do not import unverified historical success rates.

# 4. Fresh assessment procedure

## Step 0 — Identify the artefact and check presentation

The target is `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_refactored_2026-09-08.pdf` on branch `ESR` of `JozsefKiss90/proposal_orchestrator`. Its expected SHA-256 is `6fb56e517df9eef5bd5de3258d414b67e0781f44c90a095aad4d0fefcc643371` (446,718 bytes; repository commit when verified: `e8e8d23895d0f223a70cccbf986d62ba86b8ad1a`). Compute the hash independently. If different, stop the scoring and report the version mismatch; do not silently evaluate another artefact. Verify page count independently. A page-count defect in the identified file is a reportable defect, not permission to repair it.

Extract the PDF text, inspect fonts and geometry, and render **all ten pages**. Inspect the actual page images, particularly tables, references and the Gantt. Record what was measured versus merely inferred; unavailable checks remain unverified.

Check against the actual template:

- Ten-page maximum for the assessed sections, including their tables, references and figures; distinguish this official limit from the user's exact-ten-page delivery target.
- A4, margins of at least 15 mm excluding permitted header/footer elements, standard character spacing and at least single line spacing.
- Body text at least 11 pt, **including substantive body text in tables**; the 8-point minimum for genuinely non-body elements must not be used to shrink proposal narrative inside tables.
- Reference font/equivalence rules, required headings and template tags where applicable, headers and footers, readable Gantt and complete section structure.
- No clipped, overlapped, hidden or illegible content; no placeholders, comments, tracked-change artefacts or blank/extra pages.
- Embedded fonts, encryption status and correct page numbering, distinguishing technical submission checks from award criteria.

Report measurements for each page, including left/right/top/bottom content extents, table/body font minima and any raster text whose effective size cannot be reliably established. Check rendered content and table borders, not just DOCX margin settings. Distinguish superscripts and permitted header/footer text from body content. State measurement tolerance; do not round a material shortfall up to compliance.

Keep formal defects in a separate table with the exact rule, measured evidence, consequence and confidence. Do not invent automatic rejection rules or a numerical score penalty. If the official rule excludes overlength content, identify the assessable portion and apply that rule transparently. A readable but non-compliant PDF may still receive a clearly qualified substantive assessment; do not label it submission-ready.

## Step 1 — Current-PDF fact sheet and consistency scan

Extract objectives, WPs, task periods, fellow PM, deliverables, milestones, KPIs, physiological reference, model selection/freeze sequence, historical and prospective data roles, secondments, placement, partner roles, gates and risks. Include the Gantt as visual evidence, not just OCR text.

Check arithmetic and cross-references across all ten pages. Distinguish independent units from repeated measurements and total observation counts. Test whether fallbacks change the outcome type, required inputs, statistical model, metrics, claims, timing or MVP scope without corresponding updates elsewhere.

## Step 2 — Individual evaluations

For E1, E2 and E3, give specific strengths and weaknesses for every criterion, current-PDF anchors, one-decimal criterion scores and a concise rationale. Include concerns found by only one evaluator. Do not promote every individual concern to consensus without adjudication.

## Step 3 — Consensus and freeze

Reconcile each criterion on evidence, not automatic averaging. Explain meaningful disagreement, especially a spread exceeding 0.5 points. Record which individual weaknesses are retained, merged or rejected and why.

Write the ESR-style assessment in third-person, present-tense, declarative language. Separate strengths and weaknesses. No advice, replacement wording, hypothetical improvements, author intentions, historical comparisons or score-target language belongs in Part I. Every weakness has a current-PDF page/section anchor; use short exact quotations only where needed.

Freeze the individual evaluations, consensus comments, scores, numerical calculation and first-pass evidence list before proceeding.

# 5. Post-score comparison and targeted stress tests

Now read the withheld sources. This is a diagnostic audit, not a source of extra submitted evidence.

## 5.1 Round-one closure matrix

Reconcile **all** first-round Part B1 weaknesses in `1. EVALUATION`, Annex A E1–E3, the Findings Register, JSON, watchlist verdicts and owner-decision table. Do not assume the Findings Register exhausts the individual evaluations.

Use one row per distinct underlying concern, with:

`old F-ID(s) / W-ID(s) / evaluator concern / owner decision → current page and anchor → status → evidence and residual scoring consequence → round-two finding ID(s)`.

Statuses: `resolved`, `partially_resolved`, `unresolved`, `regressed`, `not_supported_on_recheck`, `out_of_scope`. New concerns receive new IDs and origin `new`; do not force them into old findings.

In particular, F-09 and F-19 are outside this B1-only scope, not successfully repaired B1 findings. Classify remaining Part A/B2-only items similarly. Mixed findings are split so only the B1-scoring component is assessed. Map F-01–F-23's in-scope components, W1–W25 verdicts, and any additional Annex A or owner-table concern without inventing missing IDs.

An “addressed” label in the refactoring report is not proof of resolution. Distinguish a fulfilled editing instruction from an adequately resolved evaluation weakness.

## 5.2 Round-two verification watchlist — hypotheses, not predetermined weaknesses

Verify these against the final PDF. A concern changes the scored assessment only through the transparent re-opening procedure in Section 1.3.

1. **Transfer chain and freeze:** defensible historical-to-Sentinel predictors; wavelength and calibration limits; leaf/canopy/field scale; spectral-response integration; atmospheric correction; purity, grid and missingness rules. Can the stated discrepancy screen be applied before M3 with available historical evidence? Are prospective spectra diagnostic only, or is a later predictor-retention decision implicitly allowed to alter the frozen primary model? Do the available measurements separate sensing and environmental effects, or support only a combined transfer claim?
2. **Field design and uncertainty:** three regimes, four blocks and twelve independently managed areas; irrigation isolation; nominal area versus actually usable interior pixels after grid alignment and quality screening; two-season calendar; matched physiological sampling. Do 288 area-date records and the attrition scenario provide a credible precision/feasibility argument rather than being mistaken for independent sample size? Are uncertainty methods credible with the actual independent groups and seasons?
3. **Outcome/model compatibility:** the two-marker physiological reference, continuous-endpoint fallback, indeterminate outcomes, control normalisation and threshold provenance. If a continuous endpoint becomes primary, are the logistic/classification model, probability interpretation, Brier skill and classification KPIs still defined coherently? Do not invent a missing regression pipeline or discretisation rule for the applicant.
4. **Performance criteria:** historical-only model selection and alert-threshold choice; properly nested preprocessing and calibration; locked comparators; uncertainty around performance and comparator advantage; realistic lead-time resolution; research-only consequences. Numerical targets are not achieved results or universal physiological standards.
5. **Novelty:** engagement with thermal/CWSI, ET/AquaCrop and existing ML irrigation work; whether categorical statements such as “none has been tested” are proportionate to the evidence cited; limits on crop, environment and sensing-scale generalisation.
6. **Supervision, training and researcher:** documentary examples versus unsupported totals; a proposed continuity routine versus an already designated deputy; assessed supervisor-led learning versus guaranteed course enrolment; competence-to-task links; under-review manuscripts and the existing DrR prototype accurately characterised; no unsupported MSc award.
7. **Impact and career:** specific audiences, channels, timing, outputs and assessment of usability; project delivery versus AgroVIR's wider channel versus eligible future users; attributed company hectares not project adoption; no advance water-saving claim; credible career, mentoring, teaching and grant-preparation measures; consistent CDP cadence.
8. **Open science and IP:** protocol registration before fitting, reproducible frozen artefacts, identifiable release milestones, licence/rights boundaries, metadata and synthetic alternatives, unsuccessful transfer results, institutional review versus project targets. Check that proprietary layers do not make the scientific evidence package inaccessible.
9. **Calendar, effort and gates:** M3 freeze and assumed start month; two seasons by M20; five WP totals and 30 PM including placement; early workload beyond arithmetic; twelve ELTE months and M25–M30 placement; D1.1–D1.4, D5.1 and all Gantt labels; critical dependency deadlines that actually precede the relevant activity.
10. **Host/partner dependencies:** MATE archive and rights, farmer geometry/irrigation/access, ELTE instrument/operator access, ATK hosting, Krumatic engineering/resources/IP, AgroVIR placement and recruitment, MVCRI continuation. Are safe responses operationally credible and consistently conditional, or contradicted by stronger statements elsewhere? Do not count MVCRI's speculative post-project route as a secured core delivery resource.
11. **Regression and compression:** preservation of substantive strengths, qualified claims, the scientific value of poor transfer, placement added value, two-way transfer and layered exploitation/IP logic. Dense prose is not itself a deduction, but assess any resulting ambiguity or loss of essential evidence. A verbatim-preservation deviation is an implementation-audit issue unless it causes an identifiable scoring loss.
12. **Validation-report reliability:** compare the report's claimed coverage and formatting PASS labels with the actual PDF and current template. Specifically investigate reported margins around 14 mm against the 15 mm requirement and 10-point substantive table text against the body-text rule. Do not simply copy the report's technical checks or claim that keyword presence establishes scientific consistency.

## 5.3 Score comparison without misleading uplift

Show the original recorded criterion scores and current scores in a comparison table, but explicitly state that the original assessment covered the full submission and used additional calibration conventions. A simple subtraction is **not** a like-for-like Part B1 improvement estimate.

Default to qualitative, evidence-based attribution of improvements and regressions. Do not back-calculate a “corrected baseline” by adding back estimated deductions. A numeric like-for-like delta is permitted only if a separate baseline-B1 assessment uses the same evidence boundary and current scoring method, with the additional assessment and its non-blind limitations disclosed. Keep it distinct from the historical ESR.

# 6. Revision handout — no proposal edits

Prioritise remaining B1 actions by scoring relevance, evidence strength, feasibility and regression risk. Address individual-evaluator residual concerns even when consensus does not retain them; label their status clearly.

Use:

- `P0`: evidenced B1 formal/submission defect, kept distinct from a scored weakness.
- `P1`: factual inconsistency or design contradiction with material consequences.
- `P2`: score-relevant improvement achievable using already supported facts or accepted design decisions.
- `P3`: score-relevant dependency requiring an unavailable owner fact or a genuinely new decision.
- `P4`: optional polish, only where justified.

For every action include: current-PDF anchor, linked findings, target `PART_B1_DOCX`, action class, precise local instruction, rationale, owner if relevant, safe alternative, dependencies, estimated lines added/removed, compensating cut ID, verification test, effort and regression risk. Short replacement clauses are allowed in the handout; a rewritten section or proposal is not.

The user has already accepted the brief's preferred answers. Do not reopen those choices routinely. No new owner facts are currently available. Do not block the review awaiting answers. Where an accepted design remains inadequate, distinguish a need for clearer implementation from a genuinely new scientific decision; provide a reasoned option and fallback for the latter.

For unavailable host/partner/supervisor facts, use the brief's safe response or a narrower honest alternative. Never manufacture capacity, equipment allocations, supervision totals, signed agreements, fields, deputies, providers, budgets, access rights or future results. Do not insert owner placeholders into proposed submission-ready wording. Record unresolved facts separately with the activity deadline and residual consequence.

Ignore confirmations irrelevant to scoring or submission. Where an arrangement can legitimately be completed after submission, formulate an activity-gated procedure and scientifically honest fallback rather than an unsupported statement that it is already secured. Do not promise a backup site, facility or provider that has not been evidenced.

## Page budget, protected strengths and cut accounting

Use the current refactored PDF/DOCX as the revision baseline, not the old sealed document. Verify every proposed cut still exists. Exclude cuts already consumed in the refactoring ledger. Give each remaining cut a unique ID; allocate it once only. Do not finance several additions with the same deletion.

Respect the brief's and ESR's do-not-touch content. Any exception must be an explicitly authorised cut, numbering correction or strictly necessary consistency update. Do not propose sacrificing an established strength to add a weaker generic claim.

Estimate both gross additions and gross cuts at **compliant** typography. If tables must be enlarged or margins repaired, include that space cost before claiming a minimum action set fits. A net-zero word/line estimate is not proof of ten-page pagination. Since this is a review, label final fit unverified until a downstream compliant export is rendered and inspected. Do not move scored B1 material into B2 to evade the page limit.

Avoid additive score-gain promises. Use qualitative leverage (`high`, `medium`, `low`) with rationale; any optional numerical scenario must be clearly non-official, non-additive and not a predicted outcome.

# 7. Required outputs

Create only:

1. `plans/reports/FIELDWISE_ESR_round2_2026-09-08.md`
2. `plans/reports/FIELDWISE_ESR_round2_2026-09-08.json`

Preserve the first ESR and all source documents. If a round-two output already exists, preserve it and use a consistent timestamped suffix for the new pair, reporting the chosen paths. Temporary working notes, text extracts and page renders belong in a separate temporary directory.

## 7.1 Markdown structure

```text
# Evaluation Summary Report — FIELDWISE (101373105), round two
Simulated; Part B1 only; current export, not an evidenced portal submission
Artefact identity, hash, commit, sources and scope limitation

# Part I — ESR-style assessment
1. EVALUATION
   1. Excellence: Strengths / Weaknesses / Score / Weight
   2. Impact: Strengths / Weaknesses / Score / Weight
   3. Quality and efficiency of the implementation: same
   Total and numerical-threshold statement, qualified to B1-only scope
2. OTHER QUESTIONS
   Only B1-supported observations; excluded questions not assessed
3. COMMENTS
   Overall evidence-based assessment; no recommendations

# Part I-bis — Diagnostic scoring and compliance sheet
E1/E2/E3 and consensus scores; disagreement resolution; aspect diagnostics
Score arithmetic, uncertainty and threshold limitations
Independent PDF/template checks and page-by-page visual results
Source/exposure log and any transparent post-freeze correction

# Part II — Round-two revision handout
II.0 Executive verdict: substantive quality versus formal readiness
II.1 Findings register: residual, new and regressed weaknesses
II.2 Prioritised surgical revision actions and minimum feasible set
II.3 Do-not-touch list and regression audit
II.4 Unresolved owner facts/decisions and safe responses
II.5 Current cut pool, one-use ledger and compliant-layout budget
II.6 Part B1 pre-export/pre-upload checks; no claim of full submission clearance
II.7 Round-one closure matrix and qualified score comparison

# Annex A — Individual evaluations E1, E2, E3
Current-PDF fact sheet, anchors, scores, dissent and its disposition

# Annex B — Machine-readable packet
Exact JSON content of the companion file
```

Keep the ESR-style section concise and evaluator-like; place detailed technical analysis in the diagnostic sheet and handout. No arbitrary minimum number of weaknesses. If a criterion has no evidenced material weakness, say so.

## 7.2 JSON contract

Use valid UTF-8 JSON, no comments, NaN, unresolved template placeholders or invented measurements. Retain familiar round-one concepts, but label this a **local round-two extension**, not a validated repository schema unless actual schema validation succeeds. Use `schema_id: "orch.tier5.esr_review_packet.round2.v1"` and `schema_status: "local_extension"`; do not overwrite or silently change the round-one schema.

Include these top-level fields:

- `proposal_id`, `acronym`, `round: 2`, `assessment_scope: "B1_only"`, `simulated: true`, `generated_at`.
- `evaluated_version`: PDF path, measured SHA-256, bytes, physical page count, repository commit, `portal_submission_verified: false`, and null submission ID/seal fields unless separately evidenced for this exact PDF.
- `sources`: path/URL, version, role (`normative`, `scoring_evidence`, `post_score_context`), read stage.
- `assessment_method`: evaluator isolation, prior exposure, freeze sequence and post-freeze correction log.
- `scores`: consensus criterion scores, weights, total, threshold values, numerical-threshold results, `official_award_status: "not_determined"`, and an explicitly conditional Seal-score statement.
- `lens_scores`, `aspect_assessments`, `consensus_resolution`.
- `formal_checks`: ID, rule/source, measured evidence, page(s), status (`pass`, `fail`, `unverified`, `not_applicable`), consequence and whether it is distinct from scoring.
- `findings`: new IDs `R2-F-01` onward; origin (`residual`, `new`, `regressed`); criterion/aspect; severity; description; exact evidence; current PDF page, section and prose/table/Gantt anchor; rationale; affected lenses; consensus disposition; linked old finding/watchlist IDs.
- `round1_comparison`: prior sources, scope/calibration differences, closure rows, original recorded scores, current scores, and `like_for_like_delta: null` unless the separately justified same-scope assessment was performed.
- `revision_actions`: IDs `R2-A-01` onward; finding references; priority; `target_document: "PART_B1_DOCX"`; class (`editorial`, `accepted_design_consistency`, `needs_fact`, `needs_decision`, `formatting`); anchor; instruction; optional short proposed wording; safe response; owner; dependencies; gross added/removed lines; cut IDs; verification; effort; regression risk; qualitative leverage.
- `do_not_touch`, `regression_checks`, `open_decisions`, `cut_pool`, `cut_ledger`.
- `minimum_revision_set`: action IDs, ordering, page-budget assumptions including formal repair costs, residual weaknesses, and `final_pagination_verified: false` because this review does not re-export a revised proposal.
- `limitations`, `validation_results`.

Keep current IDs distinct from historical F/W IDs. Allow arrays for many-to-many mappings. Use null for unknowns, not zero. Findings rejected at consensus remain traceable as individual concerns and are not silently counted as consensus deductions. Keep all JSON facts, scores and statuses identical to the Markdown.

# 8. Completion checks

Before delivery, verify:

1. The scored artefact is the identified new PDF; the old seal was not assigned to it.
2. All ten pages were read and visually inspected, or any unavailable check is plainly disclosed.
3. The current PDF alone supplied project evidence for the first-pass score; historical material was used only after the recorded freeze, subject to disclosed corrections.
4. Every consensus and individual weakness is anchored and reconciled; all distinct historical B1 concerns have a closure verdict.
5. Part A/B2 exclusions were not treated as unresolved scoring defects or false improvements.
6. Criterion scores follow official descriptors without legacy caps; total and threshold arithmetic are correct; no funding or Seal award is promised.
7. Proposed commitments are distinguished from existing facts; unavailable owner facts were not invented and safe wording was not automatically credited as sufficient feasibility.
8. Actual template rules govern formatting, especially body text in tables and margins; the refactoring report's PASS labels were independently checked.
9. Every action is surgical, current-anchored, supported and linked to a finding; protected strengths and already-used cuts are respected; formal repair costs are included in the space budget.
10. JSON parses; IDs are unique; every reference resolves; cut IDs are not allocated twice; Markdown and JSON agree.
11. Only the two new reports and temporary review files were written. No proposal, branch, decision log or portal submission was changed.

Finish with the two report paths, the three B1 diagnostic scores and weighted total, a short separation of substantive and formal readiness, the highest-priority residual issues, and the remaining owner-dependent limits. Make clear that this was an evaluation and revision handout, not a proposal rewrite or an official funding decision.

=== AGENT PROMPT ENDS ===
