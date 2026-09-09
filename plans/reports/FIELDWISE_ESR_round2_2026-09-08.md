# Evaluation Summary Report — FIELDWISE (101373105), round two

**Simulated; Part B1 only; current export, not an evidenced portal submission.**

| Item | Value |
|---|---|
| Proposal | FIELDWISE, 101373105, HORIZON-MSCA-2026-PF-01-01 (MSCA Postdoctoral Fellowships 2026, European Fellowship), ENV panel |
| Assessed artefact | `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_refactored_2026-09-08.pdf` |
| SHA-256 (computed in this review) | `6fb56e517df9eef5bd5de3258d414b67e0781f44c90a095aad4d0fefcc643371` (match) |
| Size / pages | 446,718 bytes; 10 physical pages, A4, unencrypted, all fonts embedded |
| Repository commit at review | `e8e8d23895d0f223a70cccbf986d62ba86b8ad1a`, branch `ESR` |
| Assessed content | Part B1 Sections 1–3, physical pages 1–10 |
| Portal submission | Not verified. This file is a refactored export. No submission ID, seal or timestamp attaches to it. The original submission receipt (SEP-211392861, 2026-09-07) belongs to a different file. |
| Sources (normative) | Evaluation Form (HE MSCA) V2.2, 17 December 2025; MSCA Work Programme 2026–2027 (repository copy, every page watermarked DRAFT); Part B template (HE MSCA PF) V5.0, 27 March 2026 |
| Scope limitation | Part A and Part B2 were not assessed. The scores below are a **B1-only diagnostic on the official criterion scale**, not an official or complete-application evaluation. No funding, ranking or Seal outcome is implied. |
| Method | Three isolated evaluator agents (E1 physiology/agronomy, E2 Earth observation/statistical learning, E3 experienced MSCA PF evaluator) scored the PDF independently against the official sources only. The coordinator reconciled them, froze the results (2026-09-09T07:00:10Z UTC), and only then opened the round-one ESR, brief and refactoring report for the closure audit in Part II. |
| Report pair | `plans/reports/FIELDWISE_ESR_round2_2026-09-08.md` and `plans/reports/FIELDWISE_ESR_round2_2026-09-08.json` |

# Part I — ESR-style assessment

## 1. EVALUATION

Applications are evaluated as submitted. Shortcomings are reflected in the score. Page references are physical pages of the assessed PDF.

### 1. Excellence

**Strengths**

- The proposal poses one falsifiable research question and four measurable objectives, each bound to named deliverables and months (p. 1, §1.1).
- The methodology fixes the physiological stress reference, predictor definitions, metrics and decision criteria before any fitting, freezes the model at M3 and tests it prospectively so that outcomes cannot be optimised retrospectively (pp. 2–3, §1.2).
- Validation is leakage-safe: outer leave-one-year-out over five seasons, with imputation, feature selection, tuning and calibration confined to training folds and group-aware uncertainty (pp. 2–3, §1.2).
- The experimental unit is correctly identified; plants, pixels and repeated dates are not treated as replicates, and two seasons on one field are described as temporal replication (p. 3, §1.2).
- The sensing chain is handled correctly at the level described: versioned Sentinel-2 spectral response functions, band integration before index computation, no reconstruction of uncovered bands and separate proximal and satellite corrections (p. 2, §1.2).
- Open science is integral to the method: timestamped protocol registration before fitting, a versioned model card, deposits with persistent identifiers, BSD-3-Clause code, preprints and publication of unsuccessful transfer results (pp. 3–4, §1.2).
- The gender dimension is justified as not relevant to the biological content, with diversity considered in end-user interaction (p. 3, §1.2).
- Supervision is structured through named responsibilities, a Project Steering Group tied to the decision gates, monthly written monitoring and quarterly Career Development Plan reviews; training is embedded in implementation and assessed by output (p. 4, §1.3).
- The rationale for the non-academic placement is specific to competences not available academically (p. 5, §1.3).
- The researcher's physiological competences match the reference she must define, her recent processing-tomato work is directly relevant and the career break is presented transparently (p. 5, §1.4).

**Weaknesses**

- The five-season MATE archive on which O1 and O2 depend is not characterised: plot numbers and sizes, treatments, cultivars, the physiological variables measured in each season, sampling frequency and the spectral range of the instruments are not stated, so the adequacy of the training base for leave-one-year-out validation and for a control-relative reference cannot be judged (p. 1, §1.1; p. 2, §1.2; p. 10, §3.2). [R2-F-01]
- The engineering screen that decides which spectral predictors are retained does not state what the "median absolute index discrepancy" is measured against; historical plots have no plot-level Sentinel-2 counterpart, so the screen cannot test proximal-to-satellite transfer before the freeze, and its thresholds are not justified (p. 2, §1.2). [R2-F-02]
- The Sentinel-2 sampling rules are under-specified: a 40 × 40 m interior core contains four whole 20 m pixels only when aligned to the pixel grid and no alignment requirement is stated; the matching window between physiological campaigns and valid acquisitions is not given; the 30% attrition assumption is asserted while the risk register rates "too few matched dates" as high likelihood (pp. 2–3, §1.2; p. 9). [R2-F-03]
- The prospective test rests on 12 experimental units per season and about 202 clustered area-dates, yet no precision, minimum detectable advantage or power consideration accompanies the decision criteria; the locked agronomic comparator and the frozen reference model are not identified; the lead-time metric is not defined against a reference event (p. 3, §1.2; p. 8, K6). [R2-F-04]
- The declared fallbacks change the nature of the evidence without corresponding updates: a continuous primary endpoint leaves the classification criteria unmapped, a failed spectral screen removes the hyperspectral-to-Sentinel result family relied on in §2.2 and §2.3, and rephasing alters K5, K6 and the evidential basis of MS3 (p. 2, §1.2; pp. 6–7; p. 9). [R2-F-05]
- The supervisors' experience is thinly evidenced: the primary supervisor's advanced-level supervision record is one co-supervised doctorate (2023), no postdoctoral supervision or topic-specific track record is shown, the co-supervisor's expertise is evidenced by one 2010 publication, the deputy is unnamed and the conflict-resolution route is not described (p. 4, §1.3). [R2-F-06]
- The 12-month ELTE secondment is at the permitted maximum, its added value is described functionally rather than argued, and ATK-located practicals are scheduled inside the M1–M3 and M10–M12 secondment blocks, so the content of the secondment months is unclear (p. 4, §1.3; p. 5, §2.1; p. 8; p. 10). [R2-F-07]
- The researcher's modelling and Earth-observation competence, on which O2 rests, is evidenced by short training stays, a traineeship and an undescribed prototype; the publication record is described qualitatively (p. 5, §1.4). [R2-F-08]
- The state-of-the-art positioning rests on five references and does not review satellite-scale crop water-stress detection, so the categorical novelty statement is asserted more than demonstrated (pp. 1–2, §1.1). [R2-F-09]
- The logistics that protect the control-relative stomatal-conductance reference during a multi-hour campaign over about 7.7 ha are not stated (measurement window, block order, personnel) (p. 3, §1.2). [R2-F-10]
- The fellow-to-host transfer overlaps the host's own declared expertise; the fellow's distinctive assets are not linked to what the hosts gain (p. 4, §1.3). [R2-F-11]
- Transferable-skills training is entirely embedded in project work with no named course or provider, and innovation and entrepreneurship training is absent although spin-off exploration is foreseen (p. 4, §1.3; p. 6). [R2-F-12]

**Score 1 (0–5): 4.1** — **Weighting: 50%**

### 2. Impact

**Strengths**

- The career target is defined precisely and consistently, two realistic trajectories are named, and the measures are tabulated with mechanism, evidence and month, including dated independence measures and a career KPI (pp. 5–6, §2.1).
- The non-academic placement is integral, with its own work package, deliverables and gates (p. 5, §1.3; p. 8).
- The dissemination, exploitation and communication plan is organised by strand, target group, measures and timing, commits to publishing unsuccessful as well as successful transfer results, and releases a registered protocol, model card and outputs with persistent identifiers (p. 6, §2.2).
- Communication states main messages per audience with dated outputs and indicators reported in a deliverable (p. 6, §2.2).
- The exploitation pathway is auditable and names four result families; intellectual property is handled through separate rights layers, a dated baseline declaration and a bounded disclosure review (pp. 4, 6–7).
- Uptake indicators are project-controlled and honestly qualified, and three impact scales are kept distinct (p. 7, §2.3).
- The action maps onto the fellowship outcomes of the work programme, each with an evidencing output (p. 7, §2.3).

**Weaknesses**

- No quantified indication of magnitude or importance is given for the agricultural, economic or societal impacts: no target-group size, no plausible range of effects, and the eligible-uptake denominator is deferred to the placement (p. 7, §2.3). [R2-F-13]
- The tools and channels for reaching the wider public are not identified, and public engagement is one-way (p. 6, §2.2). [R2-F-14]
- Post-MSCA exploitation is a list of options without owners or decision points and depends on agreements still to be concluded (pp. 6–7, §2.2). [R2-F-15]
- Post-fellowship positioning relies on the skills acquired; no concrete positioning measure is described and the MVCRI route is explicitly uncommitted (p. 5, §2.1; p. 10, §3.2). [R2-F-16]
- End-user engagement is concentrated in M25–M30 and depends on the placement host; before M25 it consists of a practitioner brief and requirements feedback (pp. 6–8). [R2-F-17]

**Score 2 (0–5): 4.1** — **Weighting: 30%**

### 3. Quality and efficiency of the implementation

**Strengths**

- The work plan is complete and internally consistent: five work packages with tasks, months, deliverables, KPIs and gates; effort totals reconcile (pp. 8–9, §3.1).
- Six milestones are decision gates with verifiable content; the critical path is explicit; the calendar logic is testable and the slippage rule is pre-decided (p. 9).
- Effort is explained by phase, and partner support is stated as additional to fellow effort (p. 9).
- The risk table gives likelihood, impact, trigger responses and owners, and treats poor transfer as a reportable scientific result (p. 9).
- The Gantt chart covers the mandatory elements and matches the text (p. 9).
- Hosting arrangements at the beneficiary are concrete, partner roles are delimited without overlap, paid engineering is contracted before development with a lean-MVP contingency, and resources are prioritised to protect the scientific core (p. 10, §3.2).
- The status of every third-party arrangement is declared honestly (p. 10, §3.2).

**Weaknesses**

- The commercial field for the prospective validation (O3; WP2, 9.0 PM) is unidentified. The requirements are demanding (12 independently irrigated areas including unirrigated and deficit regimes on about 7.7 ha, ready for planting at M4, two consecutive seasons on one field); no incentive, compensation or agronomic acceptability for the producer is described; the backup site is unidentified; a first season missed at M4 cannot be recovered within the 24 months; the two-season design fits only a narrow start window; and the contingency narrows the central objective (p. 3, §1.2; p. 9; p. 10, §3.2). [R2-F-18]
- The first three months carry the archive audit and harmonisation, protocol lock, pipeline construction, validation, benchmark and the irreversible model freeze (2.2 PM), together with site, contractor and placement agreements, the Career Development Plan, training at two institutions, induction and the first secondment block; the freeze is the least resourced point of the plan, and the risk table covers non-reproducibility of the pipeline by M3 but not slippage of the freeze relative to planting (p. 4, §1.3; pp. 8–9, §3.1). [R2-F-19]
- Effort is tilted toward software and operational work (WP3 6.0 PM against WP1 5.0 PM, of which 2.2 PM precede the freeze; 38% of effort on WP3 and WP4) without justification (p. 8, §3.1). [R2-F-20]
- The risk register omits agronomic risks (a wet season removing the stress contrast, heat, pests), calendar slippage of the freeze and the M4 launch, mid-season producer withdrawal, resourcing and the M20–M21 analysis compression; contingencies for loss of the engineering provider or the placement name no alternative (p. 9). [R2-F-21]
- The Gantt shows work-package bars only, with unlabeled milestones and abbreviated deliverables; the field-readiness gate invoked in §1.2 and §3.2 is not an explicit milestone (p. 9). [R2-F-22]
- Access rights to the MATE archive are fixed only by an M1 audit, and the R1 fallback "redesign O1–O2" is not a specified plan (p. 9; p. 10, §3.2). [R2-F-23]
- Capacity for the field programme, placement supervision and engineering is asserted: no AgroVIR supervisor is named, Krumatic's capacity is not outlined, field-campaign staffing and instrumentation are unquantified, and the season-2 campaigns run from the ELTE secondment block (p. 4, §1.3; p. 10, §3.2). [R2-F-24]

**Score 3 (0–5): 3.7** — **Weighting: 20%**

| | |
|---|---|
| **Total score (B1-only diagnostic)** | **80.40 / 100** = 10 × 4.1 + 6 × 4.1 + 4 × 3.7 = 41.00 + 24.60 + 14.80 |
| Criterion threshold (3.0 each; WP p. 84) | Met on all three criteria |
| Overall threshold (70; WP p. 84; EF p. 2) | Met |
| Seal of Excellence score condition (85; WP p. 86) | Not met by the B1 diagnostic total. The Seal itself depends on a complete-application evaluation and on the budget outcome; nothing here awards or predicts it. |
| Qualification | This total covers Part B1 only. A real evaluation considers the full application, including Part A and Part B2. |

## 2. OTHER QUESTIONS

| Question | Opinion (B1-supported observations only) |
|---|---|
| Scope of the application | In scope. Part B1 describes an original research project with advanced training, a 12-month secondment and a 6-month non-academic placement, corresponding to the PF topic description (WP pp. 25–27); the ENV panel is appropriate to the content. |
| Exceptional funding | Not applicable on B1 content: no third-country participant or international organisation appears. |
| Use of human embryonic stem cells | Not assessed in this B1-only review. B1 states that the research involves no human or animal biological data (p. 3). |
| Use of human embryos | Not assessed in this B1-only review (same B1 statement). |
| Activities excluded from funding | Not assessed in this B1-only review. B1 describes plant and irrigation research only. |
| Exclusive focus on civil applications | Not assessed in this B1-only review. B1 describes civil agricultural applications only. The formal answers depend on the Part A declarations. |
| Lump-sum cost assessment | Not applicable (unit-cost instrument). |

## 3. COMMENTS

**Overall comments**

Part B1 presents a pertinent, falsifiable and unusually well-specified research project: a physiologically referenced water-stress model frozen before deployment and tested prospectively across sensing scales, with leakage-safe validation and open-science practice integrated into the method. The career-development, dissemination and exploitation measures are specific, dated and honest about the boundary between evidence and adoption. The main shortcomings are evidential and logistical rather than conceptual: the training archive is not characterised, the spectral predictor screen cannot test what it is named for, the sampling geometry and the statistical resolution of the prospective test are not shown, the supervision record is thin, the magnitude of impact is not quantified, and the central field validation depends on an unidentified commercial producer with a compressed first quarter and no schedule slack. The B1 diagnostic passes the criterion thresholds and the 70-point overall threshold and falls below the 85-point Seal-of-Excellence score condition. This is a Part B1-only simulated diagnostic; Part A and Part B2 were not assessed and no funding, ranking or Seal outcome is implied.

# Part I-bis — Diagnostic scoring and compliance sheet

Nothing in this part is an official score. It records how the Part I scores were reached and what was measured.

## I-bis.1 Lens scores, consensus and disagreement resolution

| Criterion | E1 (physiology/agronomy) | E2 (EO/statistical learning) | E3 (experienced PF evaluator) | Spread | Consensus |
|---|---|---|---|---|---|
| Excellence | 4.1 | 3.9 | 4.3 | 0.4 | **4.1** |
| Impact | 4.2 | 4.0 | 4.2 | 0.2 | **4.1** |
| Quality and efficiency of the implementation | 3.8 | 3.6 | 3.8 | 0.2 | **3.7** |
| Total (10E + 6I + 4Impl) | 81.40 | 77.40 | 83.40 | 6.00 | **80.40** |

No criterion spread exceeds 0.5. The consensus is reasoned, not averaged:

- **Excellence.** E3 weighs the methodological architecture and complete template coverage as near-exemplary. E2 weighs the undefined predictor screen, the undisclosed archive spectra, the pixel geometry and the absence of any precision statement as substantive gaps in the very chain that constitutes the claimed advance. E1 sits between. The panel accepts E2's findings because they are verifiable in the PDF text (the screen's comparator is not named; alignment is not stated; no power statement exists) and accepts E3's view that the architecture is very strong. Four findings are retained as major (R2-F-01, R2-F-02, R2-F-04, R2-F-06); two of them were raised independently by two or three lenses. This exceeds "minor shortcomings" but none undermines the objectives, so the criterion sits in the lower half of the "very good" band.
- **Impact.** All three lenses raise the same major point (magnitude unquantified) and the same minors (public channels; exploitation options). E2 additionally weighs the research-only collapse of technological exploitation. Very good with one substantive and several minor shortcomings.
- **Implementation.** All three lenses rate the unidentified field site and the compressed M1–M3 window as major. E2 additionally weighs the narrow start window and the M20–M21 compression. Upper "good" band: the plan's structure is very good, but its two critical dependencies are inadequately supported.

Individual concerns rejected at consensus: E3-W13 (publication volume and timing) because manuscript timing follows the deliverable months and a floor of two peer-reviewed papers is proportionate to a 24-month fellowship. Concerns rejected by the lenses and confirmed rejected: absence of letters of commitment (not required for EF secondments or the placement), same-country secondment (permitted), 12-month secondment length (equal to, not exceeding, half), logistic regression as unambitious, the gender-dimension justification, the AgroVIR hectare figure as inflation (it is disclaimed), paid engineering as such, reliance on Fv/Fm, pseudo-replication, single crop, the career break, UAV use. Dissents recorded: E3 rates the secondment finding (R2-F-07) and the researcher's modelling competence (R2-F-08) as major; consensus keeps both minor. E2 rates the pixel-geometry finding (R2-F-03) as major on its own; consensus keeps it major after merging the matching-window and attrition points. The full disposition table for every individual weakness is in Annex A.

## I-bis.2 Aspect diagnostics (non-official; not used to compute criterion scores)

| Aspect | E1 | E2 | E3 | Consensus diagnostic | Note |
|---|---|---|---|---|---|
| exc-obj | 4.5 | 4.2 | 4.5 | 4.4 | Measurable, falsifiable objectives; state of the art thin (R2-F-09) |
| exc-method | 4.0 | 3.7 | 4.7 | 4.0 | Architecture excellent; archive, screen, geometry, precision and fallbacks under-specified (R2-F-01…05, R2-F-10) |
| exc-supervision | 3.8 | 3.9 | 3.7 | 3.8 | Strong governance; thin evidenced record; secondment content blurred (R2-F-06, 07, 11, 12) |
| exc-researcher | 4.2 | 4.0 | 3.9 | 4.0 | Physiological fit strong; modelling record emerging (R2-F-08) |
| imp-career | 4.5 | 4.3 | 4.4 | 4.4 | Specific, dated measures; positioning generic (R2-F-16) |
| imp-dissemination | 4.2 | 4.1 | 4.2 | 4.2 | Complete plan; public channels and post-project ownership thin (R2-F-14, 15, 17) |
| imp-magnitude | 3.8 | 3.6 | 3.6 | 3.7 | Honest, bounded, unquantified (R2-F-13) |
| impl-workplan | 3.7 | 3.6 | 3.7 | 3.7 | Consistent, gated; field dependency, M1–M3, risk gaps (R2-F-18…22) |
| impl-host | 3.9 | 3.6 | 3.7 | 3.7 | Concrete ATK hosting; field, archive and partner capacity asserted (R2-F-23, 24) |

The consensus diagnostic column is a reading aid for the revision handout. The criterion scores in Part I were assigned holistically from the descriptors; no aspect value was averaged into them, no per-finding tariff was subtracted and no severity cap was applied.

## I-bis.3 Score arithmetic, uncertainty and threshold limitations

- Total = 10 × 4.1 + 6 × 4.1 + 4 × 3.7 = 41.00 + 24.60 + 14.80 = **80.40**.
- Official thresholds verified: 3.0 per criterion and 70% overall (WP p. 84; EF p. 2, overall threshold 70); Seal of Excellence at ≥ 85% for proposals that cannot be funded for budget reasons (WP p. 86). All values are read from the repository copy of the work programme, which carries a DRAFT watermark; the portal topic page returned no readable text when fetched, so the adopted text was not consulted. The evaluation form V2.2 (final) states the overall threshold of 70.
- Uncertainty: the lens totals span 77.40–83.40. A one-decimal change in Excellence moves the total by 1.0 point, in Impact by 0.6 and in Implementation by 0.4. The consensus total should be read as "about 80 ± 3" rather than as a point estimate.
- Legacy benchmark: round one reported distance to 92. The current diagnostic is 11.60 below 92. That figure is **a legacy internal benchmark, not an official threshold or a demonstrated funding line**; no verified 2026 funding cutoff is known to this review.
- Not determined: official award status, eligibility, actual fundability, Seal award.

## I-bis.4 Independent PDF and template checks

Rules are quoted from the template V5.0 instructions. Measurements were made with PyMuPDF 1.28.2 on the identified PDF (span boxes, vector drawings, embedded images, content-stream operators), with all ten pages rendered at 120 dpi and inspected, plus 300–450 dpi zooms of the Gantt, the risk table and a page edge. Tolerances: ±0.2 mm for text and rules; ±0.5 pt for raster text. The DOCX was opened after the freeze for layout diagnostics only.

| ID | Rule (source) | Measured evidence | Pages | Status | Consequence | Distinct from scoring | Confidence |
|---|---|---|---|---|---|---|---|
| FC-01 | Artefact identity | SHA-256 and byte size match the prompt table; HEAD e8e8d23 | all | pass | none | yes | high |
| FC-02 | Sections 1–3 ≤ 10 pages including tables, figures, references (template; WP p. 80) | 10 physical pages; no cover page or table of contents | all | pass | none | yes | high |
| FC-03 | A4 (template) | 210.0 × 297.0 mm on every page | all | pass | none | yes | high |
| FC-04 | All margins ≥ 15 mm excluding headers and footers (template) | Body text ink: left 15.0 mm, right 15.0 mm (span boxes end 14.0 mm from the edge because each line ends in a space of 0.97 mm advance; DOCX margins 15.01 mm on all sides); top: body starts 25.7–26.4 mm below the edge (template header at 13.0 mm); bottom: body and footnotes end ≥ 20 mm above the edge (template footer at 18.2 mm) | all | pass (corrected post-freeze, see I-bis.6) | none | yes | high |
| FC-04b | Same rule applied to table rules | Vector table borders reach 13.6 mm from the right edge on pp. 5, 6, 7, 10 and 14.5 mm from the left edge on p. 9 (table indent 150 and 57 twips in the DOCX); table text stays ≥ 15.5 mm from the edge | 5, 6, 7, 9, 10 | fail (minor) | Border lines protrude ≤ 1.4 mm into the margin; a conservative checker may measure it; repair costs no space | yes | high |
| FC-05 | Reference body font Times New Roman (template) | Body 11.04 pt Times New Roman; headings 12 pt bold italic and 14 pt bold | all | pass | none | yes | high |
| FC-06 | Minimum 11 pt "for the body text, including text in tables" (template) | Prose 11.04 pt. All six tables at 9.96 pt (training table pp. 5–6, dissemination table p. 6, impact table p. 7, risk table p. 9, capacity table p. 10): about 11,700 characters, roughly a quarter of the body content, including narrative on training, dissemination, impact, risks and hosting | 5, 6, 7, 9, 10 | **fail** | Formatting condition not met; experts are instructed to verify formatting compliance. The sealed submission used 11 pt tables, so this is a regression introduced by the refactoring. Repair grows the tables by about 30 lines (I-bis.5 and II.5) | yes | high |
| FC-07 | Non-body elements legible and ≥ 8 pt (template) | Footnotes 9.0 pt (pp. 1, 4): pass. Template header 8.04 pt and footer 8.52 pt: pass. Gantt raster (1416 × 506 px placed at 180 mm width, about 200 ppi): label extents 6.1–6.8 pt, axis digits about 6 pt, i.e. nominal 6–7 pt after the image height was reduced from 8.26 cm to 6.43 cm | 9 | **fail (Gantt only)** | Figure text below the 8 pt floor; legible on screen, small in print. Regression relative to the sealed Gantt (about 8.5 pt). Repair by re-rendering at the same height costs no space | yes | medium (raster ±0.5 pt) |
| FC-08 | Minimum single line spacing (template) | Body pitch 12.6–12.8 pt at 11 pt (Word single for TNR 11 = 12.65 pt); table pitch 11.5 pt at 10 pt | all | pass | none | yes | high |
| FC-09 | Standard character spacing (template) | No horizontal scaling or word-spacing operators; per-glyph Tc adjustments between −0.13 and +0.06 pt (Word justification); DOCX carries no character-spacing attributes | all | pass | none | yes | high |
| FC-10 | Template headings and structure for B1 | 1, 1.1–1.4, 2, 2.1–2.3, 3, 3.1–3.2 present in order; pointers to Part B2 Sections 4 and 5 correct | all | pass | none | yes | high |
| FC-11 | Gantt with WPs, deliverables, milestones, secondments, placement; elapsed months, no dates (template) | All present; months 1–30; consistent with the text | 9 | pass (content) | none; readability handled under FC-07 and R2-F-22 | yes | high |
| FC-12 | No clipped, overlapped, hidden or illegible content; no placeholders, comments, tracked changes, blank or extra pages | Visual inspection of ten renders and a content-stream scan for white, tiny or invisible text: none found | all | pass | none | yes | high |
| FC-13 | PDF with embedded fonts (template) | 11 of 11 font programs embedded; PDF 1.7; unencrypted; producer Word 2024 | all | pass | none | yes | high |
| FC-14 | Header and footer; page numbering | Template header on every page; footer "Part B - Page N of 10" correct | all | pass | none | yes | high |
| FC-15 | No hyperlinks designed to expand the proposal (template) | Nine links, all footnote URLs or DOIs | 1, 4 | pass | none | yes | high |
| FC-16 | Portal submission evidence | Not a portal export; no receipt, seal or timestamp attaches to this file | — | not_applicable | `portal_submission_verified` = false | yes | high |

**Assessable portion.** No content is excluded by the page limit. The formatting failures (FC-06, FC-07, FC-04b) do not exclude content; they make the file non-compliant with the template's formatting conditions. The PDF is readable and received the substantive assessment above; it is **not submission-ready**.

## I-bis.5 Page-by-page visual results

| Page | Content | Body min pt | Table / figure min pt | Right margin (ink) | Slack below last line (11 pt lines) | Observations |
|---|---|---|---|---|---|---|
| 1 | Title, 1, 1.1, footnotes 1–7 | 11.04 | — (footnotes 9.0) | 15.0 mm | 0.8 | clean; footnotes legible |
| 2 | 1.1 end, 1.2 start | 11.04 | — | 15.0 mm | 1.0 | dense justified prose |
| 3 | 1.2 stages, challenges, integration, gender, open science | 11.04 | — | 15.0 mm | 0.9 | clean |
| 4 | open science end, 1.3, footnotes 8–9 | 11.04 | — (footnotes 9.0) | 15.0 mm | 1.1 | clean |
| 5 | placement, 1.4, 2, 2.1, training table start | 11.04 | 9.96 | 15.0 mm; table rule 13.6 mm | 0.9 | table header row repeats on p. 6 |
| 6 | training table end, 2.2, dissemination table | 11.04 | 9.96 | 15.0 mm; table rule 13.6 mm | 0.5 | page full |
| 7 | exploitation pathway, reach, 2.3, impact table, impact paragraph | 11.04 | 9.96 | 15.0 mm; table rule 13.6 mm | 6.2 | about 79 pt blank at the foot (Section 3 starts on a new page) |
| 8 | 3, 3.1, WP1–WP5 | 11.04 | — | 15.0 mm | 1.4 | page full |
| 9 | gates, critical path, risk control, risk table, Gantt | 11.04 | 9.96; Gantt ≈ 6–7 pt | 15.0 mm; risk-table left rule 14.5 mm | 1.9 | Gantt ends 25 pt above the body limit |
| 10 | 3.2, capacity table | 11.04 | 9.96 | 15.0 mm; table rule 13.6 mm | 6.4 | about 81 pt blank at the foot |

Total measured slack: about 21 lines of 11-pt prose, but it is region-bound: pages 1–7 flow continuously (11.4 lines, of which 6.2 on p. 7), pages 8–10 flow continuously after the forced page break before Section 3 (9.7 lines, of which 6.4 on p. 10), and the Gantt must stay on page 9.

## I-bis.6 Source and exposure log; post-freeze corrections

**Sources and read stage**

| # | Source | Version | Role | Stage |
|---|---|---|---|---|
| S1 | `docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_en.pdf` | V2.2, 17 December 2025 | normative | first pass |
| S2 | `docs/tier2b_topic_and_call_sources/work_programmes/msca/wp-2-marie-sklodowska-curie-actions_horizon-2026-2027_en.pdf` | WP 2026–2027 part 2; PDF created 2025-12-08; DRAFT watermark on every page | normative | first pass (viewer pp. 22–29, 78–87, 106–108) |
| S3 | `docs/tier2a_instrument_schemas/application_forms/msca/Tpl_Application Form (Part B) (HE MSCA PF).rtf` | V5.0, 27 March 2026 (verbatim text conversion) | normative | first pass |
| S4 | `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_refactored_2026-09-08.pdf` | SHA-256 6fb56e51…3371 | scoring evidence (sole source of project facts) | first pass |
| S5 | Official topic page (portal) | fetched 2026-09-09; JavaScript shell only | rule verification attempt | first pass; no content obtained |
| S6 | `plans/prompts/FIELDWISE_ESR_evaluation_prompt_2026-09-08.md` | 2026-09-08 | post_score_context (historical method) | after freeze |
| S7 | `plans/reports/FIELDWISE_ESR_2026-09-08.md` and `.json` | 2026-09-08 14:10 | post_score_context | after freeze |
| S8 | `plans/reports/FIELDWISE_Part_B1_Scoring_Improvement_Brief_2026-09-08.md` | 2026-09-08 | post_score_context | after freeze |
| S9 | `plans/reports/FIELDWISE_Part_B1_refactoring_report_2026-09-08.md` | 2026-09-08 | post_score_context (claims to verify) | after freeze |
| S10 | `docs/tier5_deliverables/submitted/FIELDWISE_101373105_submitted_2026-09-07.pdf`, physical pp. 24–33 only | SHA-256 c3bfb51f…81dbe (verified) | post_score_context (textual comparison) | after freeze |
| S11 | `…/FIELDWISE_Part_B1_refactored_2026-09-08.docx`; `…/FIELDWISE_Part_B1_gantt_refactored_2026-09-08.png` | as exported | post_score_context (layout diagnostics only) | after freeze |

**Exposure.** The coordinator's session held a project memory index whose one-line entries name the existence of a round-one ESR, a brief and a refactoring; no memory note, no file under `plans/`, no DOCX and no submitted PDF was opened before the freeze. The three evaluator agents ran in fresh, isolated contexts with access only to S1–S4 and declared that the same index headings were visible to them; none opened them. Evaluator isolation was therefore genuine between lenses, and not fully blind to the fact that an earlier round existed. The freeze was sealed at 2026-09-09T07:00:10Z (UTC) with SHA-256 hashes of the three lens reports and the coordinator notes.

**Post-freeze corrections (transparent re-opening log)**

| # | Item | Original verdict | New evidence | Revised verdict | Score effect |
|---|---|---|---|---|---|
| PF-C1 | FC-04 right margin | fail (13.9–14.1 mm) | Span boxes include the trailing space of each line (0.97 mm at 11 pt, 1.06 mm at 12 pt); the DOCX margins are 15.01 mm; 14.05 + 0.97 = 15.02 mm reconciles exactly | pass for body text; new FC-04b fail (minor) for table rules that protrude ≤ 1.4 mm | none |
| PF-C2 | FC-09 character spacing | pass (provisional) | DOCX contains no character-spacing attributes | pass (confirmed) | none |
| PF-C3 | FC-06, FC-07 origin | fail | Refactoring report §12 records the sealed tables at 11 pt and the Gantt height reduced from 8.26 cm to 6.43 cm | fail, classified as regressions relative to the sealed version | none |
| PF-C4 | R2-F-19 wording ("slippage is not in the risk table") | as frozen | Risk R1 (p. 9) covers "pipeline not reproducible by M3"; calendar slippage of the freeze relative to planting is not covered | wording corrected in Part I and the register to "covers non-reproducibility but not calendar slippage"; R2-F-21 wording aligned | none |

No score, severity or consensus disposition was changed after the freeze.

# Part II — Round-two revision handout

No proposal file was edited. Anchors point at the current refactored PDF (physical pages) and, for edits, at the current DOCX, which reproduces it. The sealed 2026-09-07 document is not the revision baseline.

## II.0 Executive verdict: substantive quality versus formal readiness

**Substantive quality (B1 diagnostic).** Excellence 4.1, Impact 4.1, Implementation 3.7, total **80.40**. Every criterion clears 3.0 and the total clears 70. The total is below the 85 Seal-of-Excellence score condition and 11.60 below the legacy 92 benchmark, which is not an official line. The refactoring made the scientific design assessable: the transfer chain, the field design, the reference definition, the model, the validation logic, the decision criteria, the open-science plan, the training schedule, the communication plan, the risk table and the hosting plan are now specified. What remains is evidential and logistical: the archive is uncharacterised, the spectral screen is undefined, the prospective test carries no precision statement, the supervision record is thin, the magnitude of impact is unquantified, and the two-season field validation depends on an unidentified producer at a compressed, zero-slack M3–M4.

**Formal readiness.** **Not submission-ready.** Three formatting defects exist, two of them regressions introduced by the refactoring: all table text is at 10 pt where the template requires 11 pt for body text including text in tables (FC-06); the Gantt labels are about 6–7 pt effective where figure text must be at least 8 pt (FC-07); table border lines protrude up to 1.4 mm into the margins (FC-04b). The refactoring report labelled the first two as PASS on an incorrect reading of the rule and a measurement artefact (II.7.3). Repairing FC-06 costs about 30 lines of table growth; the identified cut pool and slack cover the repair plus the three P1 consistency actions with margins of about 0.4 to 2.5 lines per region. Final pagination is unverified until a compliant export is rendered and re-measured.

**Recommended order.** (1) Formal repairs R2-A-01…03 with the cut ledger of II.5. (2) P1 consistency actions R2-A-04…06 and the zero-space editorial items. (3) Compliant re-export, page count, row-integrity and typography re-measurement. (4) P2 actions only against measured compression savings. (5) P3 items as owner facts arrive, never as invented facts.

## II.1 Findings register: residual, new and regressed weaknesses

Severity is diagnostic (consequence), not a tariff. Origin: residual = a round-one concern that persists in narrower or equal form; new = first raised in round two; regressed = an element that was compliant or stronger in the sealed version. Old links use the round-one identifiers (F, W, E-lens own findings, OD).

| ID | Criterion / aspect | Sev. | Origin | Weakness | Current anchor | Lenses | Consensus disposition | Old links |
|---|---|---|---|---|---|---|---|---|
| R2-F-01 | Excellence / exc-method | major | residual | Archive uncharacterised: plots, treatments, cultivars, variables per season, sampling frequency, spectrometer range | p. 1 §1.1 O1; p. 2 §1.2 Stage 1; p. 10 §3.2 MATE row | E1, E2 | retained | F-01, F-02 (archive component), W12, W13, E2-b, OD-E5 |
| R2-F-02 | Excellence / exc-method | major | new | Predictor screen comparator undefined; cannot test proximal-to-satellite transfer pre-freeze; thresholds unjustified; cover-fraction confound undiagnosed | p. 2 §1.2 "A predictor is retained only if it passes the D1.2 engineering screen" | E2 | retained (single lens, textually verified) | F-01 (context), brief R01 steps 5–6 |
| R2-F-03 | Excellence / exc-method | major | new | Sentinel-2 sampling geometry and matching under-specified: 40 × 40 m core holds four whole 20 m pixels only if grid-aligned; no alignment rule; matching window absent; 30% attrition asserted against R3 "H" | pp. 2–3 §1.2; p. 9 R3 | E1, E2 | retained (merged) | E2-f, W12 |
| R2-F-04 | Excellence / exc-method | major | residual | No precision, minimum detectable advantage or power statement for the decision criteria; comparator and reference model unidentified; lead-time reference event undefined | p. 3 §1.2 decision criteria; p. 8 K6 | E1, E2 | retained (merged) | F-02 (sample-size component), brief R02 sample-size answer (not included, refactoring report §14), R03 |
| R2-F-05 | Excellence / exc-method | minor | new | Fallbacks change the evidence type without mapped consequences: continuous endpoint vs classification criteria; failed screen removes the transfer result family; rephasing alters K5/K6/MS3 | p. 2 §1.2; pp. 6–7 §2.2–2.3; p. 9 | E2, E3 | retained | F-01/F-02 fallback wording; brief R01/R02 alternatives |
| R2-F-06 | Excellence / exc-supervision | major | residual | Supervision record thinly evidenced: one 2023 co-supervision; no postdoctoral supervision; no topic-specific record; co-supervisor evidenced by one 2010 paper; deputy unnamed; conflict route undescribed | p. 4 §1.3 | E1, E2, E3 | retained | F-06, W16, OD-E4 (safe response used) |
| R2-F-07 | Excellence / exc-supervision | minor (E3: major) | new | Secondment at the permitted maximum with functional rather than argued added value; ATK practicals scheduled inside ELTE blocks M1–M3 and M10–M12; K11 counts 12 secondment months | p. 4 §1.3; p. 5 §2.1; p. 8 K11; p. 10 ELTE row | E1, E2, E3 | retained; E3 dissent recorded | F-07, W17 (introduced by the timed schedule) |
| R2-F-08 | Excellence / exc-researcher | minor (E3: major) | residual | Modelling and EO competence under-evidenced; publication record qualitative; DrR functions undescribed | p. 5 §1.4 | E1, E2, E3 | retained; E3 dissent recorded | F-08, W18, OD-E18 |
| R2-F-09 | Excellence / exc-obj | minor | residual | State-of-the-art positioning on five references; satellite-scale water-stress detection not reviewed | pp. 1–2 §1.1 | E2, E3 | retained | F-05, W14, OD-E17 |
| R2-F-10 | Excellence / exc-method (cross: impl-workplan) | minor | residual | Campaign logistics protecting the control-relative reference unstated (window, order, personnel) | p. 3 §1.2 | E1 (+E2 staffing) | retained | E1-own-3 (logistics part), brief R02 |
| R2-F-11 | Excellence / exc-supervision | minor | new | Fellow-to-host transfer overlaps host expertise; distinctive assets not linked | p. 4 §1.3 | E2, E3 | retained | — |
| R2-F-12 | Excellence / exc-supervision | minor | new | Transferable-skills training only embedded; no innovation or entrepreneurship element despite spin-off route | p. 4 §1.3; p. 6 §2.1–2.2 | E3 | retained | — |
| R2-F-13 | Impact / imp-magnitude | major | residual | Magnitude and importance unquantified; eligible-uptake denominator deferred | p. 7 §2.3 | E1, E2, E3 | retained | F-11, W21, OD-E8 |
| R2-F-14 | Impact / imp-dissemination | minor | residual | Public tools and channels unnamed; one-way | p. 6 §2.2 Communication row | E1, E2, E3 | retained | F-12 (channels component), W20, OD-E9 |
| R2-F-15 | Impact / imp-dissemination | minor | new | Post-MSCA exploitation is a list of options without owners or decision points; pending agreements | pp. 6–7 §2.2 | E1, E2 | retained | — |
| R2-F-16 | Impact / imp-career | minor | new | Post-fellowship positioning generic; MVCRI route uncommitted | p. 5 §2.1; p. 10 MVCRI row | E2, E3 | retained | F-13 (angle changed), OD-E16 |
| R2-F-17 | Impact / imp-dissemination | minor | new | End-user engagement concentrated in M25–M30 and placement-dependent | pp. 6–8 | E3 | retained (single lens) | — |
| R2-F-18 | Implementation / impl-workplan (cross: impl-host, exc-method) | major | residual | Unidentified commercial field; demanding requirements at M4; no incentive or compensation; unidentified backup; zero slack; narrow start window; contingency narrows O3; same-field two seasons vs rotation (E1) | p. 3 §1.2; p. 9 critical path and R2; p. 10 farmer row | E1, E2, E3 | retained | F-16 (field component), F-18, W9, W24, E1-own-3, OD-E7, OD-E11 |
| R2-F-19 | Implementation / impl-workplan | major | residual | M1–M3 overload; irreversible freeze least resourced; calendar slippage of the freeze not in the risk table (R1 covers non-reproducibility only) | p. 4 §1.3; pp. 8–9 §3.1 | E1, E2, E3 | retained | F-17, W10, OD-E7 |
| R2-F-20 | Implementation / impl-workplan | minor | residual | Effort tilted to software and operational work (WP3 6.0 > WP1 5.0; 38% on WP3+WP4) without justification | p. 8 §3.1 | E1, E3 | retained | W11 (folded in round one, never addressed) |
| R2-F-21 | Implementation / impl-workplan | minor | new | Risk register omits agronomic risks, calendar slippage, mid-season producer withdrawal, resourcing, M20–M21 compression; no alternatives for provider or placement loss | p. 9 risk table | E1, E2, E3 | retained | F-21, W22 (old omissions resolved; new ones) |
| R2-F-22 | Implementation / impl-workplan | minor | new | Gantt shows WP bars only; unlabeled milestones; abbreviated deliverables; field-readiness gate not an explicit milestone | p. 9 | E3 (+E1, E2 note) | retained | F-23 (Gantt regenerated), OD-E20 |
| R2-F-23 | Implementation / impl-host | minor | residual | Archive access fixed only at the M1 audit; R1 fallback "redesign O1–O2" unspecified | p. 9 R1; p. 10 MATE row | E1 | retained | F-16 (archive component), F-22, OD-E11 |
| R2-F-24 | Implementation / impl-host | minor | residual | Capacity asserted: no AgroVIR supervisor named; Krumatic capacity not outlined; field staffing and instrumentation unquantified; season-2 campaigns from the ELTE block | p. 10 §3.2; p. 4 §1.3 | E1, E2, E3 | retained | F-16 (capacity component), F-22, E1-own-3, OD-E12, OD-E13 |
| R2-F-25 | formal (no score) | major (formal) | **regressed** | Table text at 9.96 pt in all six tables; template requires 11 pt for body text including text in tables; sealed version used 11 pt | pp. 5, 6, 7, 9, 10 | coordinator | formal check FC-06 | refactoring report §12 "Table text size … PASS" (incorrect) |
| R2-F-26 | formal (no score) | minor (formal) | **regressed** | Gantt labels about 6–7 pt effective after height reduction; figure text must be ≥ 8 pt; sealed labels about 8.5 pt | p. 9 | coordinator | formal check FC-07 | refactoring report §12 Gantt "PASS" (incorrect) |
| R2-F-27 | formal (no score) | minor (formal) | new | Table border lines protrude ≤ 1.4 mm into the right margin (pp. 5, 6, 7, 10) and 0.5 mm into the left margin (p. 9) | pp. 5, 6, 7, 9, 10 | coordinator | formal check FC-04b | refactoring report §11 "R 14.0" (artefact-based measurement) |

## II.2 Prioritised surgical revision actions and minimum feasible set

Priorities: P0 evidenced formal defect; P1 factual inconsistency or design contradiction with material consequence; P2 score-relevant improvement from supported facts or accepted design; P3 requires an unavailable owner fact or a new decision; P4 polish. Target for every action: `PART_B1_DOCX`. Lines are gross estimates at compliant typography (11 pt, about 103 characters per prose line; table cells about 85 characters per line at 11 pt). Cut IDs refer to II.5; each is allocated once. Leverage is qualitative and non-additive.

### II.2.1 Action table

| ID | P | Findings | Class | Anchor (current PDF / DOCX) | Instruction | Owner | Safe alternative | Depends on | Lines +/− | Cut IDs | Verification | Effort | Regression risk | Leverage |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R2-A-01 | P0 | R2-F-25 | formatting | All tables (DOCX table style "FW Table", 10 pt) | Set every table run and paragraph style to 11 pt; keep single spacing; do not shrink any other element to compensate | operator | none: the rule is unconditional | R2-CUT-01…13 applied first | +29.5 / 0 (table growth ≈ 374 pt) | formal-repair allocation: R2-CUT-01, 02, 07, 08, 12 (region A); R2-CUT-09, 10, 13 (region B); R2-CUT-03, 04 (region C) | PyMuPDF: minimum non-superscript span size inside every table bbox ≥ 10.95 pt; page count = 10; Gantt still on p. 9; §2.1 table rows intact across pp. 5–6 | medium | high (reflow of table row breaks; §2.1 split) | high (compliance) |
| R2-A-02 | P0 | R2-F-26 | formatting | p. 9 Gantt image; source `tools/build_partb1_refactored.py` figure | Re-render the Gantt at the same 17.99 × 6.43 cm frame with label and tick font scaled so the effective size is ≥ 8 pt (row pitch 18 pt allows 9 pt); export ≥ 300 ppi; keep content identical | operator | none | — | 0 / 0 | — | Raster measurement: ascender-to-descender extents ≥ 9 pt (nominal ≥ 8 pt); labels legible at 100% | low | low | high (compliance) |
| R2-A-03 | P0 | R2-F-27 | formatting | DOCX tables: `tblInd` 150 (five tables) and 57 (risk table) | Set table indent to 0 and table width ≤ text width (10,204 → ≤ 10,204 twips inside the margins) so that borders sit inside 15 mm | operator | none | — | 0 / 0 | — | PyMuPDF drawings bbox: x0 ≥ 42.5 pt and x1 ≤ 552.8 pt on every page | low | low | medium |
| R2-A-04 | P1 | R2-F-07 | accepted_design_consistency | p. 4 §1.3 "Planned training activities" s2: "M1–M3 at ATK (Prof. Janda, Dr Takács)" and "M1–M3 and M10–M12 at ATK (Dr Hollós)" | Remove the location clash with the ELTE blocks: relabel the two ATK-provider practicals as delivered through the fortnightly joint sessions already stated, without moving any month | operator | wording W1 below (no new fact: the joint sessions are already in the text) | none | 0 / 0 | — | Text search: no "at ATK" inside a month range that equals an ELTE block; K11 "12 secondment months evidenced" remains consistent | low | low | medium |
| R2-A-05 | P1 | R2-F-02 | accepted_design_consistency | p. 2 §1.2 Stage 1, sentence "A predictor is retained only if it passes the D1.2 engineering screen (…)" | State what the screen compares (archive cross-instrument and cross-season consistency of synthetic indices) and that the prospective paired-spectra discrepancy applies the same tolerance diagnostically; classifications used in the screen are reference-defined, not model outputs | operator (implements brief R01 steps 5–6) | wording W2 below | none | +2 / 0 | R2-CUT-06 | Readers can identify both quantities of the discrepancy; no model output enters predictor selection outside the folds | low | low | high |
| R2-A-06 | P1 | R2-F-05 | accepted_design_consistency | p. 2 §1.2 "Without a common two-marker reference … becomes the primary reference"; p. 2 "otherwise the model uses the defensible common predictors alone …" | Add the consequence mapping for both fallbacks (criteria restated as regression/calibration criteria in D1.2 with classification KPIs secondary; negative transfer result reported and MVP limited to baseline functions) | operator (brief R01/R02 alternatives already accepted) | wording W3 below | none | +2 / 0 | R2-CUT-05 | Every fallback names its effect on criteria, KPIs and result families | low | low | medium |
| R2-A-07 | P2 | R2-F-03 | accepted_design_consistency (window value: needs_decision) | p. 3 §1.2 Stage 2 s2 "…and about 7.68 ha before access and isolation land."; p. 10 farmer row | Add the grid-alignment requirement and the matching window rule (value fixed in D1.2 if not decided) | operator; fellow for the window value | "aligned to the Sentinel-2 20 m grid where the field permits" and "matched within a window fixed in D1.2" | R2-A-01 re-export | +2 / 0 | — (unmeasured compression, II.5.3) | The ≥ 4-pixel rule is attainable by construction or its non-attainment is handled | low | low | medium |
| R2-A-08 | P2 | R2-F-04 | editorial + accepted_design_consistency | p. 3 §1.2 decision criteria sentence | Name the locked comparator (the pre-specified AquaCrop/soil-water rule) and the reference model (the soil-water/meteorological baseline), and state that D1.2 fixes the required interval precision and that criteria are judged on interval bounds where estimable | operator (brief R03) | wording W4 below | none | +2 / 0 | — (unmeasured compression, II.5.3) | Comparator, reference model and precision rule are identifiable in one sentence | low | low | high |
| R2-A-09 | P2 | R2-F-18 | accepted_design_consistency | p. 10 farmer row after "no site is described as secured." | Add the field-use terms procedure: crop-loss compensation for deficit and unirrigated areas and irrigation-control responsibilities agreed with the producer before planting, under the host-approved arrangement | operator (brief R12/R15) | wording W5 below | R2-A-01 (table growth) | +1 / 0 (table) | — (region C margin) | The producer's burden is named with an owner and a deadline; no site or payment is claimed | low | low | medium |
| R2-A-10 | P2 | R2-F-18 | editorial | p. 9 critical path: "a feasible start is chosen within the permitted grant window before launch" | Insert the start window that fits the design: "between February and March" (brief R13) | operator | none needed | none | +0.5 / 0 | — | Sentence still reads as a plan, not a date | low | low | low |
| R2-A-11 | P2 | R2-F-23 | accepted_design_consistency | p. 9 risk table R1 "redesign O1–O2 if the core archive is absent" | Replace "redesign O1–O2" with the accepted re-scope rule: O1–O2 re-scoped to the accessible seasons and variables, recorded in D1.1 and D1.2 | operator (brief R12) | wording W6 below | R2-A-01 | +1 / 0 (table) | — (region B margin) | R1 names a decision and a record, not an open redesign | low | low | medium |
| R2-A-12 | P2 | R2-F-21 | accepted_design_consistency | p. 9 risk table R2 and R3 | Add "producer withdrawal within a season" to R2 with the existing rephase/narrow response; add "weak stress contrast in a wet season" to R3 with the response "reported as reduced power under K6" | operator (K6 non-estimability already accepted) | wording W7 below | R2-A-01 | +1 / 0 (table) | — (region B margin) | The two most likely delivery risks have triggers and responses | low | low | medium |
| R2-A-13 | P2 | R2-F-22 | editorial | p. 9 "MS1 (M3): protocol lock precedes fitting and model freeze; field launch plan/CDP agreed." | Insert "field-readiness gate decided;" so the gate invoked in §1.2 and §3.2 is a milestone element | operator | none needed | none | 0 / 0 | — | "field-readiness gate" appears in the MS1 definition | low | low | low |
| R2-A-14 | P2 | R2-F-14 | accepted_design_consistency | p. 6 §2.2 Communication row, public sub-item | Name the channel under project control: explainers, tutorial and summaries published on a fellow-maintained project page, with host and AgroVIR channels used where the hosts agree (brief R09 fallback) | operator | wording W8 below | R2-A-01 | +1 / 0 (table) | — (unmeasured compression, II.5.3) | A tool and channel exists for the wider-public target group | low | low | medium |
| R2-A-15 | P2 | R2-F-15 | editorial | p. 6 §2.2 Exploitation row, "Post-MSCA routes include …" | Append "each route assigned an owner and a decision gate in the D4.2 roadmap (K10)" | operator | none needed (K10 already states it) | none | +0.5 / 0 (table) | — | Exploitation options are tied to an owner and decision point | low | low | low |
| R2-A-16 | P2 | R2-F-07 | editorial | p. 4 §1.3 "The 12-month ELTE secondment (…) hosts the EO strands." | Add the added-value clause: the secondment provides instrument, laboratory and supervision access for the EO strands that HUN-REN ATK does not hold (facts in §3.2 ELTE row) | operator | none needed | none | +1 / 0 | — (unmeasured compression, II.5.3) | The template's "rationale and added value of the secondment" is answered in one sentence | low | low | medium |
| R2-A-17 | P2 | R2-F-11 | editorial | p. 4 §1.3 "Two-way transfer" s2 "The fellow contributes …" | Name the fellow's distinctive assets already in §1.4 (vegetable-crop field phenotyping in Bulgarian production systems, UAV qualification, the DrR prototype) and what the hosts gain from them | operator | none needed | none | +1 / 0 | — (unmeasured compression, II.5.3) | Both transfer directions name distinct content | low | low | low |
| R2-A-18 | P2 | R2-F-10 | accepted_design_consistency | p. 3 §1.2 Stage 2 "sample five spatially distributed plants per area." | Add the campaign protocol clause: fixed morning measurement window, blocks measured in rotating order with controls and treatments interleaved, time of day logged (brief R02) | operator | wording W9 below | none | +1 / 0 | — (unmeasured compression, II.5.3) | The control-relative reference is protected against within-campaign drift | low | low | medium |
| R2-A-19 | P2 | R2-F-20 | editorial | p. 9 effort paragraph after "Training within scientific tasks is counted once." | Add one clause: WP3 fellow effort covers specification, acceptance tests and scientific-consistency testing (T3.1–T3.4); engineering is contracted (Krumatic) | operator | none needed | none | +1 / 0 | — (unmeasured compression, II.5.3) | The WP3 share is explained without changing PM | low | low | low |
| R2-A-20 | P2 | R2-F-12 | editorial | p. 4 §1.3 "M22–M30, ATK support and AgroVIR, grant-writing clinic and FMIS evaluation" | Rename the clinic "grant-writing, valorisation and entrepreneurship clinic" (the exploitation section already foresees spin-off exploration; no new provider claimed) | operator | none needed | none | 0 / 0 | — | Training list covers innovation and entrepreneurship | low | low | low |
| R2-A-21 | P4 | — | editorial | p. 10 farmer row "An independent Hungarian farmer/producer, irrespective of gender," | Delete "irrespective of gender," | operator | none | none | 0 / 0 | — | Phrase absent | low | low | low |
| R2-A-22 | P3 | R2-F-01 | needs_fact | p. 1 O1; p. 2 Stage 1; p. 10 MATE row | State instrument, spectral range, plots per season, treatments, variables measured per season and dates, once MATE supplies them (OD-E5) | MATE / Dr Takács | Keep the current conditional wording; add "the M1 audit (D1.1) fixes the instrument range and per-season variable coverage; SWIR coverage is not assumed" | none | +2 / 0 (facts); +1 / 0 (safe) | none available without compression | Archive dimensions appear or their absence is explicit | low | low | high (if facts arrive) |
| R2-A-23 | P3 | R2-F-06 | needs_fact | p. 4 §1.3 supervisory architecture | Add verified supervision totals (PhD/postdoctoral, completed/current), one or two named current collaborations, and the deputy's role, if the supervisors supply them (OD-E4) | Prof. Janda, Prof. Jung, Dr Hollós | Keep the documentary examples; never state totals | none | +2 / 0 | none available without compression | Totals and collaborations are sourced | low | low | high |
| R2-A-24 | P3 | R2-F-13 | needs_fact | p. 7 §2.3 "Impact is measured …" three-scale sentence | Insert the eligible-uptake subset (farms, hectares, definition, date) and a sourced irrigated processing-tomato area if AgroVIR and the host supply them (OD-E8) | AgroVIR; host | Keep the current bounded statement; no national figure was established in this review | none | +2 / 0 | none available without compression | Every number carries a source and denominator | low | medium | high |
| R2-A-25 | P3 | R2-F-08 | needs_fact | p. 5 §1.4 "developed DrR – Digital Agronomist, a pre-existing desktop research prototype" | Add the prototype's version or dated declaration, implemented functions and one reproducible demonstration; name training certificates (OD-E18) | fellow | Keep the current wording | none | +1 / 0 | none available without compression | Functions are named; no mature-software claim | low | low | medium |
| R2-A-26 | P3 | R2-F-24 | needs_fact | p. 10 AgroVIR, Krumatic and farmer rows; p. 4 §1.3 | Name the AgroVIR operational supervisor, outline Krumatic's team and track record, and state who staffs the campaign days and which instruments are provided (OD-E12, OD-E13) | AgroVIR; Krumatic; ATK | Keep the procedural wording; do not claim staff or instrument allocation | none | +2 / 0 (table) | none available without compression | Each capacity claim has an owner | low | low | medium |
| R2-A-27 | P3 | R2-F-09 | needs_fact | pp. 1–2 §1.1 Pertinence, footnote set | Add one satellite-scale crop water-stress reference supplied by the fellow and one positioning clause (OD-E17) | fellow | Keep the current comparators | page-count check (footnote) | +1 text / +2 footnote | none available without compression | Reference resolvable; claim proportionate | low | medium | low |
| R2-A-28 | P3 | R2-F-17 | needs_decision | p. 6 §2.2 Communication row (M12 practitioner brief) | Decide whether the M12 brief opens a structured feedback round with the growers recruited through AgroVIR, moving part of the end-user evaluation before M25 | host; AgroVIR | Keep the current M25–M30 concentration | none | +1 / 0 (table) | none available without compression | Feedback before M25 has an owner and a month | low | low | low |
| R2-A-29 | P3 | R2-F-16 | needs_decision | p. 5 §2.1 "Two realistic post-fellowship trajectories" | Name one positioning measure (a specific scheme or position type and month) if the fellow decides it; do not name a scheme without eligibility | fellow | Keep the current trajectories | none | +1 / 0 | none available without compression | Measure is a decision, not a promise of award | low | low | low |
| R2-A-30 | P3 | R2-F-04 | needs_fact | p. 3 §1.2 decision criteria | Replace the precision rule (R2-A-08) with simulated interval precision from archive counts when MATE supplies them (brief R02 sample-size answer) | MATE; fellow; Dr Hollós | R2-A-08 rule statement | R2-A-22 | +1 / 0 | none available without compression | Precision figures traceable to counts | medium | low | high |
| R2-A-31 | P3 | R2-F-24, R2-F-21 | needs_fact | p. 10 Krumatic row; p. 10 §3.2 intro | State the funding source of the remunerated engineering and of field instrumentation (OD-E13) | host | Keep the resource-priority order | none | +1 / 0 (table) | none available without compression | Source named without a Part A change | low | low | medium |
| R2-A-32 | P3 | R2-F-07 | needs_decision | p. 4 §1.3; p. 10 ELTE row | Confirm with ELTE the content of each secondment block beyond the module and the clinic (OD-E15 residual) | Prof. Jung | R2-A-04 and R2-A-16 | none | 0 / 0 | — | Block content matches K11 | low | low | low |

### II.2.2 Proposed short wording (replacement clauses only; not rewritten sections)

- **W1 (R2-A-04)**: replace "M1–M3 at ATK (Prof. Janda, Dr Takács), physiological-reference and irrigation-design practical" with "M1–M3 (Prof. Janda, Dr Takács, through the fortnightly joint sessions), physiological-reference and irrigation-design practical"; replace "M1–M3 and M10–M12 at ATK (Dr Hollós)" with "M1–M3 and M10–M12 (Dr Hollós, joint sessions)".
- **W2 (R2-A-05)**: after "(median absolute index discrepancy ≤0.25 historical standard deviations, ≤10% change in stress classifications on a locked sensitivity set)" insert "; the screen compares synthetic indices across archive instruments and seasons, and the stress classes it uses are reference-defined, not model outputs; the prospective paired spectra apply the same tolerance as a diagnostic without altering the frozen model".
- **W3 (R2-A-06)**: after "one continuous physiological endpoint becomes the primary reference" insert ", D1.2 restates the decision criteria as pre-specified regression and calibration criteria, and the classification KPIs are reported as secondary"; after "failed spectral transfer is reported" insert " as a negative transfer result, and the transfer methodology is delivered as that report while the MVP is limited to the baseline functions".
- **W4 (R2-A-08)**: replace "a demonstrated advantage over a locked agronomic comparator" with "a demonstrated advantage over the locked agronomic comparator (the pre-specified AquaCrop/soil-water rule)"; replace "positive Brier skill against a frozen reference model" with "positive Brier skill against the frozen soil-water/meteorological baseline"; append "D1.2 fixes the interval precision required for each criterion, which is judged on interval bounds where estimable."
- **W5 (R2-A-09)**: append to the farmer row: "Field-use terms, including irrigation-control responsibilities and compensation for yield loss in deficit and unirrigated areas, are agreed with the producer before planting under the host-approved arrangement."
- **W6 (R2-A-11)**: replace "redesign O1–O2 if the core archive is absent" with "if the accessible subset lacks the common variables, O1–O2 are re-scoped to the accessible seasons and variables and the reduced scope is recorded in D1.1 and D1.2".
- **W7 (R2-A-12)**: R2 trigger: add "or producer withdrawal within a season"; R3 trigger: add "or weak stress contrast in a wet season", response: add "; a low-contrast season is reported as reduced power under K6".
- **W8 (R2-A-14)**: in the Communication row, after "three illustrated explainers (M3, M12, M24)" insert ", published on a fellow-maintained project page and, where the hosts agree, through HUN-REN ATK, ELTE and AgroVIR channels".
- **W9 (R2-A-18)**: after "sample five spatially distributed plants per area" insert ", measured within a fixed morning window with blocks in rotating order and controls interleaved with treatments, time of day logged".

### II.2.3 Minimum feasible set

| Element | Actions | Gross lines | Region |
|---|---|---|---|
| Formal repair | R2-A-01, R2-A-02, R2-A-03 | table growth ≈ +29.5 equivalent lines (region A ≈ +16.9; region B ≈ +4.2; region C ≈ +8.5); Gantt and indents 0 | A, B, C |
| P1 consistency | R2-A-04 (0), R2-A-05 (+2), R2-A-06 (+2) | +4 | A |
| Zero-space editorial | R2-A-10 (+0.5), R2-A-13 (0), R2-A-15 (+0.5), R2-A-20 (0), R2-A-21 (0) | +1 | A, B |
| Cuts and slack applied | R2-CUT-01…13; measured slack | region A: −12.5 cuts, −11.4 slack; region B: −3 cuts, −9.7 slack shared with C; region C: −2.5 cuts | |

Budget by region (II.5): region A (pp. 1–7) needs +16.9 + 4 + 0.5 = 21.4 against 11.4 slack + 12.5 cuts = 23.9 → margin about 2.5 lines; region B (pp. 8–9, Gantt fixed on p. 9) needs +4.2 + 0.5 against 3.3 slack + 3 cuts = 6.3 → margin about 1.6 lines, but the risk table must not push the Gantt; region C (p. 10) needs +8.5 against 6.4 slack + 2.5 cuts = 8.9 → margin about 0.4 lines. **Final fit unverified.** A net-zero estimate is not proof of pagination; the compliant export must be rendered and re-measured (II.6) before any P2 action is added. Ordering: cuts first, then R2-A-01, then R2-A-04…06, then zero-space items, then re-export and measure.

**Residual weaknesses after the minimum set**: R2-F-01, 03, 04, 06, 08, 09, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21 (partly), 23, 24 remain; the set removes R2-F-02, R2-F-05, R2-F-07 (location clash), R2-F-12 (naming), R2-F-22 (gate), R2-F-25, R2-F-26, R2-F-27 and narrows R2-F-15. Its leverage is compliance and design coherence, not a score gain; no numerical gain is projected.

**Second wave (P2, conditional on measured savings).** R2-A-07, 08, 09, 11, 12, 14, 16, 17, 18, 19 need about +12 gross lines beyond the minimum set. Fundable only from in-place compressions whose savings are unmeasured (II.5.3) or from further cuts that would touch credited content. Apply in the order 08, 09, 07, 11, 12, 14, 16, 18, 17, 19 with a page-count check after each region.

## II.3 Do-not-touch list and regression audit

### II.3.1 Protected content (carried from round one and the brief; verified present in the current PDF)

| Location (current PDF) | Status on recheck | Reason |
|---|---|---|
| p. 2 §1.1 "Beyond the state of the art" (four assumptions, three advances) | verbatim vs sealed (300-char check) | Clearest statement of ambition; credited by all lenses in both rounds |
| p. 1–2 §1.1 "Measurability and verifiability" (metrics, M3 freeze, falsifiable hypothesis) | verbatim | Strongest sentences; credited by all lenses |
| p. 3 §1.2 Stage 2 s1 and s4–s6 (frozen model, primary before recalibration) | s1 verbatim; s2 replaced as permitted | Frozen-model logic |
| p. 3 §1.2 Methodological challenges (i)–(vi) | present; UAV sentences cut as permitted | Mitigation list credited by E1/E2 |
| p. 3 §1.2 Gender dimension and diversity | verbatim | Accepted justified non-relevance statement |
| p. 4 §1.3 Structured supervision and governance | verbatim | Governance credited by E3 |
| p. 4 §1.3 Two-way transfer s2–s4 | verbatim | Concrete transfer (R2-A-17 adds to s2 without removing content) |
| p. 5 §1.3 Placement rationale s1–s5 | verbatim | Compliance-critical placement wording |
| pp. 6–7 §2.2 Exploitation row, IP row, Exploitation pathway | verbatim | Strongest Impact strand (R2-A-15 appends inside the row) |
| p. 7 §2.3 "no numerical water-saving benefit is claimed in advance" | verbatim, magnitude clause added beside it as permitted | Honest bounding |
| pp. 8–9 §3.1 WP headers, task months, PM figures, deliverable months, K1–K14, MS1–MS6 | consistent set; D1.3/D1.4 renumbered as authorised | Reconciles with the Gantt |
| p. 9 §3.1 Decision gates; Risk control integrity rule | verbatim | Named approvers; integrity rule |
| p. 9 Gantt | image; re-render only for R2-A-02 (fonts) | Page 9 must keep the Gantt |
| pp. 5–6 §2.1 table split | row-break sensitive | Check row integrity after every edit in §1.x–§2.1 |
| pp. 1, 4 footnotes 1–9 | 9 pt; page fill non-linear | Add footnotes (R2-A-27) only with a page-count check |

New protections from this round: the three-scale magnitude sentence (p. 7), the §3.2 dependency statement and resource-priority order (p. 10), the R1–R6 decision-specific triggers (p. 9), the timed training schedule (p. 4) and the Communication row (p. 6) are credited strengths; edits to them are limited to the appends in II.2.

### II.3.2 Regression audit (sealed 2026-09-07 B1 versus current export)

- **Text preservation.** 135 of 304 sealed sentences survive verbatim (44%); 5,847 words became 6,415 (+9.7%), absorbed by the 10 pt tables and the removed blank lines. All twelve protected passages spot-checked are verbatim or changed only where the round-one list permitted. The refactoring report's protected-passage assertions were consistent with the check.
- **Substantive strengths.** Preserved: falsifiability, independent physiology, blocked historical validation, freeze before prospective outcomes, primary results before adaptation, supplementary-only UAV status, one-crop/two-season limits, two-way transfer, placement rationale, rights layers, evidence-based MVP gates, water-saving boundary, poor-transfer-as-result rule. No credited strength was lost; several were strengthened (reference definition, sensing chain, open science, risk triggers, hosting).
- **Qualified claims.** Every owner-dependent claim is conditional and consistently so ("none is claimed as signed or held", "no site is described as secured", "not a guaranteed position"). One tension, not a contradiction: "the producer hosts field trials" (p. 8) and "provides the commercial field" (p. 10) are role statements beside the disclaimer.
- **Compression effects.** Sentences over 35 words rose from 18 to 45 (refactoring report §12). E3 rates readability below content quality. No identifiable scoring loss from density alone; two compression-induced defects: the ATK/ELTE month clash (R2-F-07, new) and the stray phrase "irrespective of gender" (R2-A-21).
- **Formal regressions.** Table text 11 pt → 10 pt (R2-F-25); Gantt labels about 8.5 pt → about 6–7 pt after the height reduction (R2-F-26). Both were reported as PASS in the refactoring report. Table borders now protrude ≤ 1.4 mm (R2-F-27); the sealed export was not re-measured for this item.
- **Implementation-audit deviations without scoring loss.** Accepted details not included (refactoring report §14): the 60–70% replacement deficit level, the 1,440 plant-visit total, BRDF/geometry recording, the paired-metric reporting list, the simulated precision from archive counts (owner counts unavailable), the calibration-method choice. Of these, the precision simulation is score-relevant and appears as R2-F-04/R2-A-30; the others belong in D1.2.

### II.3.3 Regression checks for the next export

1. Protected passages remain verbatim (whitespace-normalised) after all edits.
2. WP totals 5.0/9.0/6.0/5.4/4.6 = 30.0; 24.0 in M1–M24; 6.0 in M25–M30; WP1 2.2 + 2.8.
3. Deliverable months and Gantt labels unchanged (D1.1 M2; D1.2, D1.3, D5.1 M3; D5.2 M6; D2.1 M20; D1.4, D2.2 M21; D3.1–3.2 M24; D4.1–4.2, D5.3 M30); MS1–MS6 at 3/12/21/24/27/30.
4. ELTE blocks M1–M3, M10–M12, M16–M21 (12 months) and placement M25–M30 unchanged everywhere, including K11.
5. CDP cadence identical in §1.3, §2.1 table and §3.1.
6. No new fact about access, allocation, agreement status, supervision totals, deputies, providers, budgets or results.
7. Section 3 still starts at the top of p. 8; the Gantt still ends on p. 9; §3.2 on p. 10.

## II.4 Unresolved owner facts and decisions, with safe responses

No owner fact became available in this round. The brief's safe responses remain in force and were found consistently applied. The table records what stays open, when it is needed, and the residual consequence if it stays open.

| ID | Owner | Missing fact or decision | Needed by (activity) | Safe response now in B1 | Residual consequence | Round-two link |
|---|---|---|---|---|---|---|
| R2-OD-01 | MATE / Dr Takács | Archive instrument and spectral range; plots, treatments, variables and dates per season; analysis and reuse permissions | before the M1 audit (D1.1) and the M3 freeze | conditional conversion; legally accessible subset; M1 rights audit | R2-F-01, R2-F-23 remain major/minor | OD-E5, OD-E11; R2-A-22 |
| R2-OD-02 | Producer + ATK | Site identity or description, polygons, irrigation control, two-season availability, compensation, backup site | field-readiness gate before planting (M3–M4) | adopted requirements; "no site is described as secured"; backup only if genuinely available | R2-F-18 remains major | OD-E11; R2-A-09 |
| R2-OD-03 | Prof. Janda, Prof. Jung, Dr Hollós | Supervision totals; current collaborations; deputy identity; committed time | before submission text is finalised | documentary examples; deputy arrangement without identity | R2-F-06 remains major | OD-E4; R2-A-23 |
| R2-OD-04 | AgroVIR; host | Eligible-uptake subset (farms, hectares, definition, date); irrigated processing-tomato area with source; recruitment capacity | before submission text is finalised (uptake denominator otherwise during the placement) | dated public footprint as context; targets not commitments | R2-F-13 remains major | OD-E8; R2-A-24 |
| R2-OD-05 | Fellow | DrR version/functions; training certificates; manuscript status | before submission text is finalised | prototype wording; "under review" | R2-F-08 remains minor | OD-E18; R2-A-25 |
| R2-OD-06 | ELTE / Prof. Jung | Paired-spectrum access, instrument and operator time per block; content of each secondment block | before each block (M1, M10, M16) | access "arranged before each block"; no allocation claimed | R2-F-07 remains minor | OD-E15; R2-A-32 |
| R2-OD-07 | Host (ATK) | Funding source for engineering and instrumentation; field-campaign staffing; AgroVIR supervisor name; Krumatic capacity | before paid development (T3.1, M1–M3) and before season 1 | resource-priority order; procedural wording | R2-F-24, R2-F-21 remain minor | OD-E12, OD-E13; R2-A-26, R2-A-31 |
| R2-OD-08 | Fellow + supervisors | Matching-window value; precision requirement; a satellite-scale reference; positioning measure; earlier feedback round | before D1.2 (M3); text items before submission | D1.2 records the decisions | R2-F-03, R2-F-04, R2-F-09, R2-F-16, R2-F-17 | R2-A-07, R2-A-08, R2-A-27, R2-A-28, R2-A-29, R2-A-30 |
| R2-OD-09 | Operator | Confirmation of the adopted work programme text (the repository copy is a DRAFT) | before relying on thresholds in any external communication | values consistent with the final evaluation form | none for scoring | Part I-bis.3 |

Out of this round's scope and unchanged: OD-E1 (Part A secondment host), OD-E2/OD-E3 (CV), OD-E14 (ethics table), OD-E19 (B2 declaration). Ignored as irrelevant to scoring: none of the brief's items was found irrelevant; each maps above or is excluded by scope.

## II.5 Current cut pool, one-use ledger and compliant-layout budget

### II.5.1 Round-one cuts: status

The round-one pool listed 22 cuts (CUT-1…5, 7…20, 22, 23, 25). The refactoring ledger consumed all 22, each once. No round-one cut remains available. The current pool below is new, identified in the current text, verified present, and each ID is allocated once.

### II.5.2 Round-two cut pool (verified present in the current PDF; lines at 11 pt)

| ID | Location (current PDF / DOCX) | Text to compress or remove | Lines | Why safe | Allocated to |
|---|---|---|---|---|---|
| R2-CUT-01 | p. 5 §2.1 table row "ATK modelling training and 12-month ELTE secondment", mechanism cell | Compress to two lines: "ATK practicals (physiology, design, modelling); ELTE EO strands per Section 1.3" | −3 | Duplicates the timed schedule in §1.3 | formal repair (R2-A-01), region A |
| R2-CUT-02 | p. 7 §2.3 table "Scientific" row, contribution cell | Compress "Leakage-safe modelling links … independent commercial field." to one line | −2 | Duplicates §1.1–§1.2 | formal repair (R2-A-01), region A |
| R2-CUT-03 | p. 10 §3.2 ATK row s2 | Remove "Prof. Tibor Janda is the primary supervisor (…); Dr Roland Hollós supports the predictive-modelling/ML strand." | −1.5 | Stated in §1.3 | formal repair (R2-A-01), region C |
| R2-CUT-04 | p. 10 §3.2 ELTE row | Remove the per-block task list "band-integration and QC notebook (M1–M3), transfer diagnostics (M10–M12) and the paired-sensing clinic (M16–M21)"; keep "access arranged before each block" | −1 | Stated in §1.3 | formal repair (R2-A-01), region C |
| R2-CUT-05 | p. 6 §2.1 "By completion, the fellow will have taken one research concept through …" | Compress the four-line sentence to two lines | −2 | Trajectory stated in §1.4 and §2.1 opener | R2-A-06 |
| R2-CUT-06 | p. 3 §1.2 Integration of methods, last sentence "The fellow integrates these disciplines: …" | Compress to "The fellow integrates these disciplines under the protocol and the validated predictor specification." | −1 | Generic closer; accountabilities sentence carries the content | R2-A-05 |
| R2-CUT-07 | p. 7 §2.2 "Reach and uptake" second half (repeat of the counts: two demonstrations, one workshop, three explainers, one tutorial, two summaries) | Remove the repeated counts; keep the growers/FMIS-user evaluation targets and "attendance is not adoption" | −1.5 | Counts are in the Communication row | formal repair (R2-A-01), region A |
| R2-CUT-08 | p. 5 §1.4 "Fit and development potential" sentence "The fellowship addresses the next step in her progression: …" | Compress to one line | −1.5 | Duplicates the §2.1 opener | formal repair (R2-A-01), region A |
| R2-CUT-09 | p. 8 §3.1 opening paragraph s2 "ELTE secondment blocks are M1–M3, M10–M12 and M16–M21 (12 months); they are locations of work within the allocated effort." | Remove; the blocks are in §1.3, §3.2, the Gantt and K11 | −1 | Duplicate | formal repair (R2-A-01), region B |
| R2-CUT-10 | p. 8 §3.1 WP5 "Lead: fellow/ATK; supervisors and host support services contribute." | Merge into the T5.1 line | −0.5 | No content lost | formal repair (R2-A-01), region B |
| R2-CUT-11 | p. 7 §2.3 intro "Impact is bounded to what the action demonstrates directly: …" | not offered | 0 | Credited bounding statement | — |
| R2-CUT-12 | p. 5 §1.4 duplicated fit clause "… deepened through the distributed ELTE secondment and specialist supervision at HUN-REN ATK." | Remove the clause | −1.5 | Secondment and supervision are described in §1.3 | formal repair (R2-A-01), region A |
| R2-CUT-13 | p. 9 risk table R4 and R6 response cells | Shorten "limit MVP and placement to supported functions; a negative result still fulfils the reporting objective" and "replacement provider only if secured; placement change resolved with the host" to one line each | −1.5 (table) | The integrity rule above the table carries the principle | formal repair (R2-A-01), region B |

Pool total: 18 lines identified (region A 12.5; region B 3.0; region C 2.5), plus measured slack (region A 11.4; regions B+C 9.7). Every cut except R2-CUT-05 (R2-A-06) and R2-CUT-06 (R2-A-05) is consumed by the formal repair R2-A-01. P2 actions must be funded by the unmeasured compressions in II.5.3; no cut is allocated twice.

### II.5.3 In-place compression candidates (savings unmeasured; do not count until rendered)

- Consolidate the pipeline description repeated in §1.1 (objectives), §1.2 (stages), §2.3 (Scientific row) and §3.1 (WP1 tasks) while keeping each section's purpose.
- Merge the three statements of the "independent Agricultural Data Scientist" target (§1.4, §2.1 opener, §2.1 "By completion").
- Use identical short asset names across the open-science paragraph (p. 3–4) and the Dissemination row (p. 6).
- §3.2 ATK row: the hosting plan sentence could lose "each in place before first use" if the intro's dependency statement is retained.

### II.5.4 Compliant-layout budget

| Region | Content flow | Table growth at 11 pt (≈ +21% height) | Other P0 cost | Slack measured | Cuts identified | P1 + zero-space additions | Net margin |
|---|---|---|---|---|---|---|---|
| A: pp. 1–7 | continuous until the forced break before Section 3 | +214 pt ≈ 16.9 lines (tables pp. 5, 6, 7) | 0 | 11.4 lines (6.2 on p. 7) | 12.5 lines | +4.5 lines | ≈ +2.5 lines |
| B: pp. 8–9 | continuous; Gantt anchored on p. 9 | +53 pt ≈ 4.2 lines (risk table) | Gantt re-render 0 | 3.3 lines | 3.0 lines | +0.5 line | ≈ +1.6 lines, on condition that the risk-table growth does not push the Gantt |
| C: p. 10 | continues from p. 9 | +107 pt ≈ 8.5 lines (capacity table) | 0 | 6.4 lines | 2.5 lines | 0 | ≈ +0.4 line |

The growth factor 1.21 assumes a 10 → 11 pt scaling of both line length and pitch (11.5 → 12.65 pt); table header repeats and row breaks can add one to two lines per table. The budget is therefore marginal in every region. **Final fit is unverified** until a compliant DOCX is exported to PDF and re-measured; no B1 content may be moved to B2 to make it fit.

## II.6 Part B1 pre-export and pre-upload checks (no claim of full submission clearance)

1. Apply cuts before additions; keep a region ledger; check page count after each region.
2. Export from Word; verify with PyMuPDF: 10 pages; A4; all non-superscript spans in table boxes ≥ 10.95 pt; all non-superscript body spans ≥ 10.95 pt; footnotes ≥ 8 pt; Gantt label extents ≥ 9 pt; no drawing or text inside 42.5 pt of any page edge except the template header and footer; line pitch ≥ 12.6 pt at 11 pt; no character-spacing attributes in the DOCX; fonts embedded; no encryption.
3. Confirm Section 3 starts on p. 8, the Gantt ends on p. 9 and §3.2 fills p. 10 without overflow.
4. Run II.3.3 regression checks 1–7 and the protected-passage verbatim check.
5. Text checks: no "[", "OWNER", "TBD", tracked changes, comments or highlighting; no "at ATK" within an ELTE block; "field-readiness gate" appears in MS1; "irrespective of gender" absent.
6. Cross-reference checks: deliverable numbers and months in §1.1, §3.1 and the Gantt; K11 wording; CDP cadence; placement months.
7. Record the applied action set, the cut ledger and the new PDF hash in the decision log before any upload. Part A, Part B2, portal validation and receipt are outside this handout.

## II.7 Round-one closure matrix and qualified score comparison

### II.7.1 Closure matrix (one row per distinct concern)

Statuses: resolved; partially_resolved; unresolved; regressed; not_supported_on_recheck; out_of_scope. "Addressed" in the refactoring report means an edit was made; the status here judges the weakness.

| Old ID(s) | Concern | Owner decision / route | Current page and anchor | Status | Evidence and residual scoring consequence | Round-two ID(s) |
|---|---|---|---|---|---|---|
| F-01, W12, E2-f | Hyperspectral-to-Sentinel-2 harmonisation unspecified | OD-E5 partly (design supplied; archive facts pending) | p. 2 §1.2 Stage 1 | partially_resolved | Chain now specified (SRF integration, band exclusion, corrections, L2A, 20 m grid, pixel rules); comparator of the screen undefined and archive range undisclosed | R2-F-01, R2-F-02, R2-F-03 |
| F-02, W13, E1-own-1, E2-b | Design not dimensioned; reference deferred; no phenology; no pre-registration | OD-E6 partly | p. 2–3 §1.2 | partially_resolved | Dimensioned, reference defined, stages named, registration committed; precision and geometry not shown; archive size still absent | R2-F-01, R2-F-03, R2-F-04 |
| F-03, E2-a, E2-c | Model unnamed; no prospective proximal spectra | brief R03 | p. 2–3 §1.2 | resolved | Logistic regression + GBT benchmark; calibration in folds; paired spectra diagnostic | comparator identity residual in R2-F-04 |
| F-04, W15, E2-d | Open science at principle level | OD-E10 | pp. 3–4 §1.2; p. 6 | resolved | Registration, Zenodo, BSD-3, preprints, DMP, 30-day review, negative results | — |
| F-05, W14 | State of the art thin; bare EEA link | OD-E17 (references supplied) | pp. 1–2 §1.1 | partially_resolved | EEA indicator sourced; three comparators cited; satellite-scale literature absent | R2-F-09 |
| F-06, W16 | Supervisors asserted | OD-E4 unresolved; safe response | p. 4 §1.3 | partially_resolved | Documentary examples added, no totals; record still thin (major) | R2-F-06 |
| F-07, W17 | Training by topic; conditional teaching; M1–M3 supervision | OD-E15 partly | p. 4 §1.3 | resolved, with a new inconsistency | Timed schedule, providers, outputs, continuity measures; ATK practicals now clash with ELTE blocks | R2-F-07, R2-F-12 |
| F-08, W18 | Researcher outputs thin; DrR undocumented | OD-E18 unresolved | p. 5 §1.4 | partially_resolved | Competence-to-task links; manuscripts labelled under review; DrR functions still undescribed | R2-F-08 |
| F-09, W2; F-29 | CV template content; career-break documentation | OD-E3 | Part B2 | out_of_scope | Not a B1 finding | — |
| F-10, W4 | MSc claim inconsistency | OD-E2 (safe response: omit) | p. 5 §1.4 | resolved (B1 component) | Disputed credential omitted | — |
| F-11, W21 | Magnitude unquantified | OD-E8 unresolved | p. 7 §2.3 | partially_resolved | Three scales, policy and WP-outcome links, 700,000 ha as context; no quantified estimate (major) | R2-F-13 |
| F-12, W20 | Communication lacks messages, tools, channels, timing | OD-E9 partly | p. 6 §2.2 | partially_resolved | Messages, outputs, timing, indicators per audience; public channels unnamed (minor) | R2-F-14 |
| F-13, W19 | Career skills not measures | OD-E16 | p. 6 §2.1 | resolved | Dated clinic, grant application, mentoring, PANGEOS, venues | new angle R2-F-16 |
| F-14, E3-own CDP | CDP cadence inconsistent | A-04 | pp. 4, 5, 8 | resolved | Consistent in three places | — |
| F-15, E1-own-2 | Data/software vehicles unspecific; EO-only venues | OD-E16 | p. 6 §2.2 | resolved | Release assets named; Irrigation Science / ISHS added | — |
| F-16, W24 (field component), E1-own-3 | Unnamed farmer; field undescribed; compensation absent | OD-E11 unresolved; safe response | p. 3; p. 9 R2; p. 10 farmer row | partially_resolved | Requirements and gate stated; site unidentified; compensation still absent (major) | R2-F-18 |
| F-16 (archive and contractor components), F-22, W8 | Informal roles; no agreements; no resource plan | OD-E11, OD-E13 unresolved | p. 10 §3.2 intro and rows | partially_resolved | Dependency statement, M1 rights audit, contract-before-development, priority order; sources of funds and capacities unstated (minor) | R2-F-23, R2-F-24 |
| F-17, W10 | M1–M3 concurrency; WP1 PM unjustified | OD-E7 (February assumption) | pp. 8–9 §3.1 | partially_resolved | Split 2.2/2.8 explained; content load unchanged; all lenses still major | R2-F-19 |
| W11 | Effort profile WP1 vs WP2/WP3 (folded in round one) | — | p. 8 | unresolved | Never addressed; WP3 share unjustified (minor) | R2-F-20 |
| F-18, W9 | No start month; no contingency | OD-E7 | p. 9 critical path | partially_resolved | February start, slip rule; window narrow and contingency narrows O3 | R2-F-18, R2-F-05 |
| F-19, W1 | Secondment host absent from Part A | OD-E1 | Part A | out_of_scope | Not a B1 finding | — |
| F-20, W23, E2-e | Hosting generic; no compute | OD-E12 (safe plan) | p. 10 ATK row | resolved | Induction, workstation, storage, remote EO, HR/IP/grants support | — |
| F-21, W22 | Risk register undifferentiated; omissions | A-10 / brief R17 | p. 9 | resolved; new omissions | Six decision-specific rows; old omissions covered; new gaps | R2-F-21 |
| F-23, W5, OD-E20 | D1.3 numbering gap | A-03 | pp. 1, 8, 9 | resolved | Renumbered; Gantt regenerated | Gantt readability new: R2-F-22 |
| F-24, W7; F-28 | Ethics table; AI page pointer | OD-E14 | Part A | out_of_scope | — | — |
| F-25, W3; F-26, W6; F-27, E3-own | B2 footer; Part A cosmetics; B2 declaration | — | Part A / B2 | out_of_scope | — | — |
| E1-own-4 | Completeness of the 2026 season not stated | — | p. 1 | unresolved (note, not scored) | Still not stated; no scoring consequence assigned | — |
| W25 | Placement and secondment compliance | preserve | pp. 4, 5, 8, 10 | not a weakness; confirmed compliant on recheck | 12 of 24 months; M25–M30 non-academic EU host | — |
| E3-own end-user co-creation | Strength to retain | — | pp. 6–7, 10 | retained | Structured evaluation and requirements feedback present | — |
| Formal S0-2 (sealed typography compliant) | Tables 11 pt; Gantt ≈ 8.5 pt | refactoring | pp. 5–10 | regressed | Tables 10 pt; Gantt ≈ 6–7 pt | R2-F-25, R2-F-26 |

### II.7.2 Round-two verification watchlist: verdicts

| # | Hypothesis | Verdict on the current PDF |
|---|---|---|
| 1 | Transfer chain and freeze | Predictors, SRF integration, band exclusion, corrections and grid are defensible as stated; the screen cannot be applied to proximal-to-satellite transfer before M3 because no historical Sentinel-2 counterpart exists (R2-F-02); prospective spectra are diagnostic only and T1.4 forbids changing the primary model (confirmed); sensing and environmental effects are honestly reported as a combined gap when inseparable (confirmed). |
| 2 | Field design and uncertainty | 12 independently managed areas and 288/202 area-dates are correctly presented as records, not sample size (confirmed); interior-pixel yield after alignment and screening is not shown (R2-F-03); matched physiological sampling is stated; group-aware or hierarchical uncertainty is credible in principle but interval stability with 12 units and two seasons is not addressed beyond "non-estimability explained" (R2-F-04). |
| 3 | Outcome/model compatibility | Two-marker reference, indeterminate class, control normalisation and threshold provenance are coherent (confirmed); the continuous-endpoint fallback leaves the classification model, Brier skill and alert KPIs unmapped (R2-F-05); no regression pipeline was invented here. |
| 4 | Performance criteria | Historical-only selection, nested preprocessing and calibration, research-only consequences and interval-bounded lead time are stated (confirmed); comparator and reference model are "locked" but unidentified; no uncertainty around performance or comparator advantage (R2-F-04); targets are presented as decision criteria, not results (confirmed). |
| 5 | Novelty | Thermal/CWSI, ET/AquaCrop and ML irrigation work are engaged with three citations; "none has been tested…" is narrowly framed but rests on five references; crop, environment and scale limits are stated (confirmed); satellite-scale literature absent (R2-F-09). |
| 6 | Supervision, training, researcher | Documentary examples, no totals (confirmed); deputy is a proposed routine, not a designated person (consistent, R2-F-06 sub-point); supervisor-led modules replace course enrolment (confirmed); competence-to-task links present; manuscripts "under review" and DrR "pre-existing desktop research prototype" (confirmed); no MSc claim (confirmed). New clash: ATK practicals inside ELTE blocks (R2-F-07). |
| 7 | Impact and career | Audiences, messages, timing and outputs present; public tools/channels absent (R2-F-14); delivery, channel and eligible users distinguished (confirmed); 700,000 ha attributed and bounded (confirmed); no water-saving claim (confirmed); career measures credible; CDP cadence consistent (confirmed); magnitude unquantified (R2-F-13). |
| 8 | Open science and IP | Registration before fitting, frozen artefacts, identifiable release milestones (D1.2 M3, D1.3 M3, D5.2 M6, D2.1 M20, D2.2 M21), licence and rights boundaries, metadata/synthetic alternatives, negative results, 30-day review subject to institutional clearance: all present; proprietary layers do not withhold the evidence package (confirmed; no finding). |
| 9 | Calendar, effort, gates | M3 freeze with February start; two seasons by M20; five WP totals and 30 PM; 12 ELTE months; M25–M30 placement; D1.1–D1.4, D5.1 and Gantt labels all consistent (confirmed). Early workload beyond arithmetic confirmed (R2-F-19). Dependency deadlines precede activities (T2.1 M1–M4, T3.1 M1–M3) but the field deadline coincides with first observations (zero slack, R2-F-18) and the field-readiness gate is not a milestone (R2-F-22). |
| 10 | Host/partner dependencies | Safe responses consistently conditional (confirmed); role statements in present tense beside disclaimers are not contradictions; MVCRI is not counted as a delivery resource (confirmed); field, archive and capacity dependencies remain (R2-F-18, R2-F-23, R2-F-24). |
| 11 | Regression and compression | Strengths and qualified claims preserved; poor-transfer value, placement added value, two-way transfer, layered IP logic intact; density increased without identifiable scoring loss; one new inconsistency (R2-F-07) and one stray phrase; formal regressions in tables and Gantt (II.3.2). |
| 12 | Validation-report reliability | Margins: the report lists "L 15.0 / R 14.0" per page yet marks margins PASS; the 14.0 mm figure is the trailing-space artefact of span boxes (this review made the same measurement first and corrected it against the DOCX and the glyph advance); true ink margin ≈ 15.0 mm; table rules protrude ≤ 1.4 mm. Table text: the report's "plan permits tables ≥ 8 pt: PASS" contradicts the template ("including text in tables"): FAIL and a regression from 11 pt. Gantt: reported "sharp … PASS" but labels fell below 8 pt after the height reduction: FAIL. Keyword-presence checks (67 required phrases) passed while the ATK/ELTE month clash was introduced, so presence does not establish consistency. Cross-reference checks (D1.3, PM totals, CDP cadence, Gantt) were independently confirmed correct. |

### II.7.3 Score comparison, qualified

| Criterion | Round one (sealed full application, 2026-09-08) | Round two (current B1 only) | Arithmetic difference |
|---|---|---|---|
| Excellence | 3.6 | 4.1 | +0.5 |
| Impact | 3.7 | 4.1 | +0.4 |
| Implementation | 3.5 | 3.7 | +0.2 |
| Total | 72.20 | 80.40 | +8.20 |

**The arithmetic difference is not a like-for-like Part B1 improvement estimate.** The round-one assessment covered the full submission (Part A, B1, B2), reconstructed criterion scores as 5.0 minus summed per-finding deductions, applied a 4.4 cap for any major finding, and reported a 92-point "fundable zone". Round two assesses B1 alone, scores holistically from the official descriptors without caps or tariffs, and excludes Part A and B2 items from both weaknesses and improvements. No separate baseline-B1 assessment under the current method was performed; `like_for_like_delta` is therefore null.

**Qualitative attribution.**

- Improvements evidenced in the current text: the transfer chain, field design, reference definition, model and validation logic, decision criteria and open-science plan are now assessable (F-01…F-04 narrowed); comparators engaged (F-05 narrowed); timed training, continuity and CDP cadence (F-07, F-14 resolved); communication messages and timing (F-12 narrowed); career measures (F-13 resolved); release plan and venues (F-15 resolved); hosting plan (F-20 resolved); risk triggers (F-21 resolved); numbering (F-23 resolved); honest dependency statements (F-16 narrowed).
- Unchanged in substance: archive characterisation, supervision record, magnitude quantification, field-site identity and terms, M1–M3 load, start-window narrowness. These carry the same owner dependencies as in round one.
- Regressions: table typography and Gantt label size (formal); the ATK/ELTE month clash (minor, new).
- Method effects that inflate the arithmetic difference: removal of the 4.4 cap and of the tariff reconstruction; exclusion of the Part A/B2 findings (F-09, F-19, F-24…F-29) that contributed deductions in round one.

# Annex A — Individual evaluations E1, E2, E3

Three fresh, isolated evaluator contexts received only the current PDF (all ten pages, plus page renders), the evaluation form V2.2 text, the work programme text (PF pages) and the template V5.0 text. None saw another lens's output, the coordinator's notes, the watchlist or any round-one material. Each declared prior exposure limited to the session's memory-index headings, which none opened. Full reports are preserved in the review's temporary directory; this annex reproduces the fact sheet, every weakness with its anchor, the scores and the consensus disposition.

## A.0 Current-PDF fact sheet (coordinator, Step 1)

- **Fellow.** Dr Rositsa Cholakova; PhD Plant Physiology 2020 (Agricultural University of Plovdiv); Assistant Professor 2015–2020; Chief Assistant Professor at MVCRI; career break 2021–2024; EU A1/A3 drone qualification; developer of the pre-existing DrR desktop prototype; five years of teaching; 2025 proceedings paper; two 2026 manuscripts under review; MATE stays (10 + 14 days, 2025); three-month ELTE traineeship (2026) (p. 5).
- **Host and team.** HUN-REN ATK (Prof. Tibor Janda primary supervisor; Dr Roland Hollós modelling); ELTE (Prof. András Jung co-supervisor and secondment supervisor; Dr Zsófia Varga UAV); MATE (Dr Sándor Takács, Prof. Gábor Milics); Krumatic EOOD (paid engineering); AgroVIR Kft. (placement host); unidentified commercial producer (field); MVCRI (Prof. Ganeva, post-MSCA route only) (pp. 4, 10).
- **Duration and effort.** 24 months + 6-month placement; 30.0 PM (24.0 M1–M24; 6.0 M25–M30); WP1 5.0 (2.2 pre-freeze, 2.8 later), WP2 9.0, WP3 6.0, WP4 5.4, WP5 4.6; ELTE secondment M1–M3, M10–M12, M16–M21 (12 months); placement M25–M30 (pp. 4, 8–9).
- **Objectives and outputs.** O1 archive harmonisation and reference protocol (D1.1 M2, D1.2 M3); O2 regularised logistic regression with gradient-boosted benchmark, frozen at M3 (D1.3); O3 two-season prospective validation (D2.1 M20, D2.2 M21); O4 DrR web MVP and AgroVIR evaluation (D3.1–3.2 M24, D4.1–4.2 M30); D1.4 transfer specification M21; D5.1 CDP M3; D5.2 DMP M6; D5.3 M30; MS1–MS6 at M3/12/21/24/27/30; K1–K14; R1–R6 (pp. 1, 8–9).
- **Reference and model.** Stomatal conductance relative to stage- and campaign-matched controls, corroborated by leaf water status; Fv/Fm complementary; indeterminate class; limits from historical controls and repeatability; fallback continuous endpoint. Synthetic Sentinel-2 predictors from canopy spectra via versioned SRFs; out-of-range bands dropped; L2A, 20 m grid, ≥ 90% cover, ≥ 4 valid pixels; D1.2 engineering screen (≤ 0.25 SD, ≤ 10% class change); leave-one-year-out with fold-internal preprocessing; group-aware uncertainty; abstention flag; decision criteria (balanced accuracy ≥ 0.70 with comparator advantage; positive Brier skill; sensitivity ≥ 0.80 at FPR ≤ 0.20; interval-bounded lead time) (pp. 2–3).
- **Field design.** 3 regimes × 4 blocks = 12 areas of about 80 × 80 m, 20 m buffer, 40 × 40 m core, 7.68 ha; 12 campaigns per season, 5 plants per area; 288 area-dates, about 202 under 30% attrition; paired proximal spectra diagnostic only (p. 3).
- **Calendar.** February start assumed; MS1 April (M3); first observations May (M4); second harvest by M20; slip rule stated (p. 9).
- **Consistency scan.** PM totals, area-date arithmetic, secondment months, Gantt versus text, deliverable months, KPI numbering, objective–deliverable mapping, placement months and supervisor roles all pass. Open items: pixel geometry versus the ≥ 4-pixel rule; continuous-endpoint fallback versus classification criteria; archive size; M1–M3 load; producer incentive; screen comparator; comparator and reference identities; matching window; SWIR coverage; the stray phrase "irrespective of gender" (p. 10).

## A.1 Lens E1 — plant physiology, agronomy, irrigation

**Scores:** Excellence 4.1; Impact 4.2; Implementation 3.8; total 81.40. Threshold statement: all criteria above 3.0; total above 70 and below 85 (B1-only diagnostic).

**Checks performed (all pass unless stated):** PM sums and splits; area, core and area-date arithmetic; secondment at the 50% ceiling; placement rules; Gantt versus text (D5.2 reviews and D5.3 update not drawn: minor); deliverable months across sections; KPI cross-references; February calendar; decision-criteria coherence; training locations versus secondment blocks (**fail**: ATK practicals inside ELTE blocks); mandatory WP deliverables; gender justification.

**Strengths (condensed):** falsifiable question and frozen model; objectives bound to deliverables and metrics; careful independent physiological reference; circularity avoided; leakage-safe validation; sound spectral harmonisation with a declared fallback; pre-specified decision criteria; correct experimental unit; concrete interdisciplinary integration; gender justification; strong open science; structured supervision; output-assessed training; specific placement rationale; researcher's physiological fit and transparent career break.

**Weaknesses (ID · aspect · severity · anchor · summary):**
- E1-W01 · exc-method · major · p. 1 §1.1, p. 2 §1.2, p. 10 · archive dimensions, treatments, variables, controls per season and spectrometer range not stated.
- E1-W02 · exc-method · major · p. 3 §1.2, p. 8 K6 · 12 units per season; no precision or minimum detectable difference; spectral increment over the agronomic comparator not isolated.
- E1-W03 · exc-supervision · major · p. 4 §1.3 · one co-supervised doctorate; no postdoctoral supervision; no numbers for Jung or Hollós.
- E1-W04 · exc-supervision · minor · p. 4 §1.3 · ATK practicals in M1–M3 and M10–M12 coincide with ELTE blocks.
- E1-W05 · exc-method · minor · p. 3 §1.2 · campaign logistics (window, order, personnel) and satellite matching window unstated.
- E1-W06 · exc-method · minor · pp. 2–3 · 40 × 40 m core holds four whole 20 m pixels only if grid-aligned; ≥ 4-pixel rule at the limit.
- E1-W07 · exc-researcher · minor · p. 5 §1.4 · EO/data-science outputs and training thin for the M3 freeze.
- E1-W08 · exc-method · minor · pp. 2–3, 7 · lead time undefined against a reference event; coarse resolution.
- E1-W09 · imp-magnitude · major · p. 7 §2.3 · no quantified magnitude or importance.
- E1-W10 · imp-dissemination · minor · p. 6 · public communication small and channel-less.
- E1-W11 · imp-dissemination · minor · pp. 6–7, 10 · exploitation depends on pending agreements; post-MSCA routes undetermined.
- E1-W12 · impl-workplan · major · p. 3, p. 9, p. 10 · unidentified field; demanding requirements; no incentive; no recoverable first season; contingency narrows O3.
- E1-W13 · impl-workplan · major · pp. 8–9, p. 4 · M1–M3 overload; irreversible freeze compressed.
- E1-W14 · impl-workplan · major · pp. 2–3, 10 · two consecutive tomato seasons on one commercial field conflicts with rotation practice (medium confidence).
- E1-W15 · impl-workplan · minor · p. 4, p. 8, p. 10 · season-2 campaigns fall inside the ELTE block; field support unstated.
- E1-W16 · impl-workplan · minor · p. 9 · risk register omits wet season, heat, pests, fellow contingency.
- E1-W17 · impl-workplan · minor · p. 8–9 · WP3 6.0 PM exceeds WP1 5.0 PM.
- E1-W18 · impl-host · minor · p. 10, p. 9 R1 · archive rights unsettled until the M1 audit.

**Rationale (E1):** very good objectives and methodology; archive uncharacterised, power unshown, supervision record thin; implementation plan structurally very good but its critical dependencies inadequately supported.

**Lens-specific notes:** signal ordering (optical indices lag stomatal closure; lead time likely from soil-water predictors); comparator overlap; information concentrated in the deficit regime; late-season deficit is a quality-management practice; genotype effects; unbounded indeterminate fraction; sensor density unstated. Rejected: letters of commitment; Fv/Fm reliance; pseudo-replication; secondment length; absence of thermal sensing; single crop; gender; DrR conflict-of-interest speculation; UAV.

**Aspect diagnostics (non-official):** exc-obj 4.5; exc-method 4.0; exc-supervision 3.8; exc-researcher 4.2; imp-career 4.5; imp-dissemination 4.2; imp-magnitude 3.8; impl-workplan 3.7; impl-host 3.9.

## A.2 Lens E2 — Earth observation and statistical learning

**Scores:** Excellence 3.9; Impact 4.0; Implementation 3.6; total 77.40. All criteria above 3.0; total above 70 and below 85.

**Checks performed:** PM sums, splits and full-time equivalence; area-dates; area, core; pixel geometry (**fail/tension**: four whole pixels only if grid-aligned; ≥ 90% rule admits buffer pixels); threshold coherence; secondment and placement rules; calendar with harvest months; Gantt versus text; deliverable months (D1.4 absent from the O1–O4 list: minor); mandatory deliverables; milestone consistency; KPI cross-references; training locations versus secondment (**fail**); attrition assumption versus R3 "H" (tension); MVCRI role consistency; partner roles; mono-beneficiary rules. Fallback tests: continuous endpoint (partial fail), failed spectral transfer (fail), rephasing (fail), research-only outcome (pass with note).

**Strengths (condensed):** falsifiable hypothesis and frozen model; bounded novelty claim with three advances; pre-registration and circularity avoidance; unusually leakage-aware validation; correct unit; correct sensing chain at the level described; diagnostic-only prospective spectra; conservative fallbacks; named accountabilities; integral open science; gender justification; specified governance; embedded, output-assessed training; specific placement rationale; researcher's physiological fit and archive co-authorship.

**Weaknesses:**
- E2-W01 · exc-method · major · p. 2 · engineering screen comparator undefined; cannot test proximal-to-satellite transfer pre-freeze; thresholds unjustified; possible selection outside folds if classifications are model outputs.
- E2-W02 · exc-method · major · pp. 1–2 · archive spectral range, instruments, footprints and counts undisclosed; SWIR synthesis unknown; no index named.
- E2-W03 · exc-method · major · pp. 2–3, 10 · core geometry versus ≥ 4-pixel rule; no grid-alignment requirement; buffer pixels admitted by the cover rule.
- E2-W04 · exc-method · major · p. 3 · no precision, minimum detectable advantage or power; point versus interval unspecified; alert threshold on out-of-fold or in-sample predictions unspecified.
- E2-W05 · exc-method · minor · pp. 2–3 · comparator and reference model unidentified; Brier skill undefined in the failed-transfer branch; no dichotomisation rule in the continuous branch.
- E2-W06 · exc-method · minor · p. 3, p. 9 · matching window absent; 30% attrition asserted against R3 "H".
- E2-W07 · exc-method · minor · pp. 2–3 · canopy-cover fraction confound between proximal footprint and 20 m pixel undiagnosed.
- E2-W08 · exc-obj · minor · pp. 1–2 · universal negative on a narrow citation base; satellite-scale work not engaged.
- E2-W09 · exc-supervision · minor · p. 4 · supervision record one co-supervised doctorate; collaborations undated.
- E2-W10 · exc-supervision · minor · p. 4 · ATK practicals double-booked with ELTE blocks.
- E2-W11 · exc-researcher · minor · p. 5 · four months of EO training and no modelling publication for an M3 freeze.
- E2-W12 · exc-supervision · minor · p. 4 · fellow-to-host transfer overlaps host expertise.
- E2-W13 · imp-magnitude · major · p. 7 · no quantified magnitude for any dimension.
- E2-W14 · imp-dissemination · minor · p. 6 · public tools and channels unnamed.
- E2-W15 · imp-dissemination · minor · pp. 6–7 · post-project exploitation options without owners; collapses to methodology if research-only.
- E2-W16 · imp-career · minor · p. 5, p. 10 · MVCRI route uncommitted.
- E2-W17 · impl-workplan · major · pp. 8–9 · 2.2 PM pre-freeze workload; freeze slip forces loss of season 1 or a post-collection freeze.
- E2-W18 · impl-workplan · major · p. 9 · two-season design fits only a December–April start; rephasing changes outcome type, K5, K6, D2.x and MS3 basis.
- E2-W19 · impl-host · major · p. 10, p. 8, p. 9 · no identified producer; demanding requirements at planting time; no compensation or infrastructure plan.
- E2-W20 · impl-workplan · minor · p. 3, p. 10 · campaign staffing undescribed.
- E2-W21 · impl-workplan · minor · p. 8 · D2.1 M20 at harvest; D2.2, D1.4 and MS3 at M21.
- E2-W22 · impl-workplan · minor · p. 9 · freeze and start slippage not tabulated; attrition tension.
- E2-W23 · impl-host · minor · p. 10, p. 9 · procurement route and provider/placement alternatives unstated.

**Rationale (E2):** architecture very good; the EO transfer chain that constitutes the claimed advance carries an undefined screen, undisclosed archive spectra, geometry that needs alignment and no precision statement; implementation compressed at the start and dependent on an unidentified producer.

**Lens-specific notes:** the screen cannot test what its name claims; grid alignment decides the sample; radiometric shift is the measured quantity (acceptable if comparators are locked); soil-water predictors may dominate; relative label versus absolute operation under heat waves; cover-fraction confound; L2A processing-baseline versioning unmentioned. Rejected: letters; logistic regression as unambitious; fellow's ML record as a quality failure per se; secondment dilution; gender; DrR/Krumatic inter-relationship (B2 matter); archive rights beyond disclosure; Gantt legibility (not scored).

**Aspect diagnostics (non-official):** exc-obj 4.2; exc-method 3.7; exc-supervision 3.9; exc-researcher 4.0; imp-career 4.3; imp-dissemination 4.1; imp-magnitude 3.6; impl-workplan 3.6; impl-host 3.6.

## A.3 Lens E3 — experienced MSCA PF evaluator

**Scores:** Excellence 4.3; Impact 4.2; Implementation 3.8; total 83.40. All criteria above 3.0; total above 70 and below 85.

**Checks performed:** PM sums, phase split, M1–M3 effort; secondment at the limit (permitted; same country permitted); placement rules; duration; deliverable months; Gantt versus text (tasks, milestone labels, D5.2 reviews and D5.3 update not shown); gates versus milestones; CDP cadence (pass; WP deliverable timing rules met); KPI numbering; calendar; field arithmetic; training locations versus secondment (**fail, minor**); field-readiness gate versus milestones (ambiguous); communication timing versus placement; roles across §1.3 and §3.2; design consistency across §1.1, §1.2, §3.2; template headings; template minimum aspects per sub-section (all addressed; 1.3 secondment rationale implicit; 2.2 public channels; 2.3 quantified estimates withheld; 3.1 Gantt minimal; 3.2 field host unidentified and no AgroVIR person).

**Strengths (condensed):** falsifiable question with verifiable objectives; quantitative pre-fixed criteria with consequences; rigorous methodology for a single-fellow action; explicit sensing-scale handling; stated sample and limits; concrete state-of-the-art argument; integral open science; correct gender treatment; multi-layered supervision with continuity in M1–M3; output-assessed training with transferable skills per WP; two-way transfer; explicit placement rationale; researcher's fit and transparent break.

**Weaknesses:**
- E3-W01 · exc-supervision · major · p. 4 · primary supervisor's supervision and topic record thin; collaborations as past stays.
- E3-W02 · exc-supervision · minor · p. 4 · co-supervisor's currency evidenced by a 2010 paper.
- E3-W03 · exc-supervision · major · pp. 4, 5, 8, 10 · secondment at the maximum, same country, no dedicated added-value statement; blurred by ATK training inside blocks; prior three-month ELTE traineeship.
- E3-W04 · exc-supervision · minor · p. 4 · conflict route undescribed; deputy unnamed; meeting frequency after M3 unstated.
- E3-W05 · exc-supervision · minor · p. 4, p. 6 · transferable skills only embedded; no innovation/entrepreneurship training despite spin-off route.
- E3-W06 · exc-researcher · major · p. 5 · modelling competence for O2 evidenced by short stays, a traineeship and an undescribed prototype.
- E3-W07 · exc-researcher · minor · p. 5 · publication record qualitative.
- E3-W08 · exc-obj · minor · pp. 1–2 · five references; satellite-scale state of the art not reviewed; ambition self-limited.
- E3-W09 · exc-method · minor · pp. 2–3 · single environment; spectral strand may be dropped before the prospective test; O3 wording broader than the design.
- E3-W10 · exc-supervision · minor · p. 4 · fellow-to-host transfer overlaps host expertise.
- E3-W11 · imp-magnitude · major · p. 7 · no quantified magnitude or importance.
- E3-W12 · imp-dissemination · minor · p. 6 · no public tool or channel; one-way.
- E3-W13 · imp-dissemination · minor · pp. 6–7 · publication floor of two; submission months not scheduled; conferences without years.
- E3-W14 · imp-career · minor · p. 5, p. 10 · trajectories generic; no positioning measure; MVCRI uncommitted.
- E3-W15 · imp-dissemination · minor · pp. 6–8 · end-user engagement concentrated in M25–M30 and placement-dependent.
- E3-W16 · impl-workplan · major · p. 3, p. 9, p. 10 · unidentified field; zero slack at M4; no incentive; contingency degrades O3.
- E3-W17 · impl-workplan · major · p. 4, pp. 8–9 · overloaded M1–M3 with the irreversible freeze; integration into the host team effectively from M4.
- E3-W18 · impl-workplan · minor · p. 8 · 38% of effort on software/operational work; WP3 6.0 PM unjustified.
- E3-W19 · impl-workplan · minor · p. 9 · schedule risk to MS1/M4, mid-season producer withdrawal and resourcing omitted.
- E3-W20 · impl-workplan · minor · p. 9 · Gantt minimal; field-readiness gate not a milestone.
- E3-W21 · impl-host · minor · p. 10 · no AgroVIR person; Krumatic capacity not outlined; field-campaign logistics unstated.

**Rationale (E3):** objectives and methodology near-exemplary for a PF; a small number of shortcomings in supervision evidence, secondment rationale and researcher's modelling record; Impact very good with unquantified magnitude; Implementation upper "good" because of the field dependency and the overloaded first quarter.

**Formal-presentation observations (non-scoring):** headings complete; tables effective; dense prose on pp. 2–3 and 8–9; Gantt legible but without caption, task rows or milestone labels; "2.3." heading carries a trailing full stop. Rejected: same-country secondment; letters; gender; 30-month duration; AgroVIR hectares as inflation; paid engineering; ELTE block during the field season; career break.

**Aspect diagnostics (non-official):** exc-obj 4.5; exc-method 4.7; exc-supervision 3.7; exc-researcher 3.9; imp-career 4.4; imp-dissemination 4.2; imp-magnitude 3.6; impl-workplan 3.7; impl-host 3.7.

## A.4 Dissent and disposition of every individual weakness

| Individual | Disposition | Consensus finding |
|---|---|---|
| E1-W01, E2-W02 | retained, merged (major) | R2-F-01 |
| E2-W01, E2-W07 (sub-point) | retained; single-lens origin, textually verified (major) | R2-F-02 |
| E1-W06, E2-W03, E2-W06, E1-W05 (window part) | retained, merged (major) | R2-F-03 |
| E1-W02, E2-W04, E2-W05 (identities), E1-W08 (sub-point) | retained, merged (major) | R2-F-04 |
| E2-W05 (fallbacks), E2-W18 (consequence mapping), E3-W09 | retained (minor); single-environment part rejected as a declared limitation | R2-F-05 |
| E1-W03, E2-W09, E3-W01, E3-W02, E3-W04 | retained, merged (major) | R2-F-06 |
| E1-W04, E2-W10, E3-W03 | retained (minor); **E3 dissent: major** | R2-F-07 |
| E1-W07, E2-W11, E3-W06, E3-W07 | retained (minor); **E3 dissent: major** | R2-F-08 |
| E2-W08, E3-W08 | retained (minor) | R2-F-09 |
| E1-W05 (logistics part) | retained (minor) | R2-F-10 |
| E2-W12, E3-W10 | retained (minor) | R2-F-11 |
| E3-W05 | retained (minor) | R2-F-12 |
| E1-W09, E2-W13, E3-W11 | retained (major) | R2-F-13 |
| E1-W10, E2-W14, E3-W12 | retained (minor) | R2-F-14 |
| E1-W11, E2-W15 | retained (minor) | R2-F-15 |
| E2-W16, E3-W14 | retained (minor) | R2-F-16 |
| E3-W15 | retained (minor; single lens) | R2-F-17 |
| E1-W12, E1-W14 (aggravating sub-point, medium confidence), E2-W18 (slack part), E2-W19, E3-W16 | retained, merged (major) | R2-F-18 |
| E1-W13, E2-W17, E3-W17 | retained (major) | R2-F-19 |
| E1-W17, E3-W18 | retained (minor) | R2-F-20 |
| E1-W16, E2-W21, E2-W22, E2-W23, E3-W19 | retained, merged (minor) | R2-F-21 |
| E3-W20 | retained (minor) | R2-F-22 |
| E1-W18 | retained (minor) | R2-F-23 |
| E1-W15, E2-W20, E3-W21 | retained, merged (minor) | R2-F-24 |
| E3-W13 | **rejected at consensus**: manuscript timing follows deliverable months; two papers proportionate | — |

No individual concern was silently dropped; rejected and merged items remain traceable above.

# Annex B — Machine-readable packet

Exact content of `plans/reports/FIELDWISE_ESR_round2_2026-09-08.json` (schema `orch.tier5.esr_review_packet.round2.v1`, status `local_extension`).

```json
{
 "schema_id": "orch.tier5.esr_review_packet.round2.v1",
 "schema_status": "local_extension",
 "schema_note": "Local round-two extension of orch.tier5.esr_review_packet.v1; not validated against a repository schema; the round-one schema is unchanged.",
 "proposal_id": "101373105",
 "acronym": "FIELDWISE",
 "round": 2,
 "assessment_scope": "B1_only",
 "simulated": true,
 "generated_at": "2026-09-09T07:37:51+00:00",
 "evaluated_version": {
  "pdf_path": "docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_refactored_2026-09-08.pdf",
  "sha256_measured": "6fb56e517df9eef5bd5de3258d414b67e0781f44c90a095aad4d0fefcc643371",
  "bytes": 446718,
  "physical_pages": 10,
  "repository_commit": "e8e8d23895d0f223a70cccbf986d62ba86b8ad1a",
  "branch": "ESR",
  "portal_submission_verified": false,
  "portal_submission_id": null,
  "sealed_at": null,
  "seal_hash": null,
  "assessed_content": "Part B1 Sections 1–3, physical pages 1–10",
  "note": "Refactored export; the original submission receipt SEP-211392861 belongs to a different file (sha256 c3bfb51f93b4c0c36221d0bd83dab77efaa619eee4f3dd937e58d728c3f81dbe)."
 },
 "sources": [
  {
   "id": "S1",
   "path": "docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_en.pdf",
   "version": "V2.2, 17 December 2025",
   "role": "normative",
   "read_stage": "first_pass"
  },
  {
   "id": "S2",
   "path": "docs/tier2b_topic_and_call_sources/work_programmes/msca/wp-2-marie-sklodowska-curie-actions_horizon-2026-2027_en.pdf",
   "version": "WP 2026–2027 part 2; PDF created 2025-12-08; DRAFT watermark",
   "role": "normative",
   "read_stage": "first_pass",
   "pages_used": "22–29, 78–87, 106–108 (viewer)"
  },
  {
   "id": "S3",
   "path": "docs/tier2a_instrument_schemas/application_forms/msca/Tpl_Application Form (Part B) (HE MSCA PF).rtf",
   "version": "V5.0, 27 March 2026",
   "role": "normative",
   "read_stage": "first_pass"
  },
  {
   "id": "S4",
   "path": "docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_refactored_2026-09-08.pdf",
   "version": "6fb56e517df9eef5bd5de3258d414b67e0781f44c90a095aad4d0fefcc643371",
   "role": "scoring_evidence",
   "read_stage": "first_pass"
  },
  {
   "id": "S5",
   "path": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/screen/opportunities/topic-details/HORIZON-MSCA-2026-PF-01-01",
   "version": "fetched 2026-09-09; JavaScript shell, no readable content",
   "role": "normative",
   "read_stage": "first_pass_attempt"
  },
  {
   "id": "S6",
   "path": "plans/prompts/FIELDWISE_ESR_evaluation_prompt_2026-09-08.md",
   "version": "2026-09-08",
   "role": "post_score_context",
   "read_stage": "post_freeze"
  },
  {
   "id": "S7",
   "path": "plans/reports/FIELDWISE_ESR_2026-09-08.md",
   "version": "2026-09-08",
   "role": "post_score_context",
   "read_stage": "post_freeze"
  },
  {
   "id": "S8",
   "path": "plans/reports/FIELDWISE_ESR_2026-09-08.json",
   "version": "orch.tier5.esr_review_packet.v1, generated 2026-09-08T14:10:00+02:00",
   "role": "post_score_context",
   "read_stage": "post_freeze"
  },
  {
   "id": "S9",
   "path": "plans/reports/FIELDWISE_Part_B1_Scoring_Improvement_Brief_2026-09-08.md",
   "version": "2026-09-08",
   "role": "post_score_context",
   "read_stage": "post_freeze"
  },
  {
   "id": "S10",
   "path": "plans/reports/FIELDWISE_Part_B1_refactoring_report_2026-09-08.md",
   "version": "2026-09-08",
   "role": "post_score_context",
   "read_stage": "post_freeze"
  },
  {
   "id": "S11",
   "path": "docs/tier5_deliverables/submitted/FIELDWISE_101373105_submitted_2026-09-07.pdf",
   "version": "sha256 c3bfb51f93b4c0c36221d0bd83dab77efaa619eee4f3dd937e58d728c3f81dbe (verified); pp. 24–33 only",
   "role": "post_score_context",
   "read_stage": "post_freeze"
  },
  {
   "id": "S12",
   "path": "docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_refactored_2026-09-08.docx",
   "version": "as exported 2026-09-08",
   "role": "post_score_context",
   "read_stage": "post_freeze",
   "use": "layout diagnostics only"
  }
 ],
 "assessment_method": {
  "evaluator_isolation": "three fresh agent contexts (E1, E2, E3) with access to S1–S4 only; no access to each other's output, the coordinator's notes or the watchlist",
  "prior_exposure": "coordinator and evaluators saw a project memory index whose headings name the existence of a round-one ESR, a brief and a refactoring; none opened; no round-one file read before the freeze",
  "freeze_sequence": [
   "Step 0 identity and presentation",
   "official sources read",
   "Step 1 fact sheet and consistency scan",
   "Step 2 isolated lens evaluations",
   "Step 3 consensus",
   "freeze sealed 2026-09-09T07:00:10Z with sha256 of lens reports and notes",
   "post-freeze: S6–S12 opened"
  ],
  "freeze_timestamp_utc": "2026-09-09T07:00:10Z",
  "post_freeze_correction_log": [
   {
    "id": "PF-C1",
    "item": "FC-04 right margin",
    "original": "fail (13.9–14.1 mm)",
    "new_evidence": "span boxes include the trailing-space advance (0.97 mm at 11 pt); DOCX margins 15.01 mm; 14.05 + 0.97 = 15.02 mm",
    "revised": "pass for body text; FC-04b fail (minor) for table rules protruding ≤ 1.4 mm",
    "score_effect": "none"
   },
   {
    "id": "PF-C2",
    "item": "FC-09 character spacing",
    "original": "pass (provisional)",
    "new_evidence": "no character-spacing attributes in the DOCX",
    "revised": "pass",
    "score_effect": "none"
   },
   {
    "id": "PF-C3",
    "item": "FC-06/FC-07 origin",
    "original": "fail",
    "new_evidence": "refactoring report §12: sealed tables 11 pt; Gantt height reduced 8.26→6.43 cm",
    "revised": "fail, classified as regressions",
    "score_effect": "none"
   },
   {
    "id": "PF-C4",
    "item": "R2-F-19 wording",
    "original": "'slippage is not in the risk table'",
    "new_evidence": "R1 covers 'pipeline not reproducible by M3'",
    "revised": "'covers non-reproducibility but not calendar slippage'",
    "score_effect": "none"
   }
  ],
  "scores_changed_after_freeze": false
 },
 "scores": {
  "consensus": {
   "excellence": 4.1,
   "impact": 4.1,
   "implementation": 3.7
  },
  "weights": {
   "excellence": 0.5,
   "impact": 0.3,
   "implementation": 0.2
  },
  "formula": "total = 10*excellence + 6*impact + 4*implementation",
  "total": 80.4,
  "thresholds": {
   "per_criterion": 3.0,
   "overall": 70,
   "seal_of_excellence_score_condition": 85,
   "source": "WP 2026–2027 pp. 84, 86 (repository copy, DRAFT watermark); EF V2.2 p. 2"
  },
  "threshold_results": {
   "excellence_ge_3": true,
   "impact_ge_3": true,
   "implementation_ge_3": true,
   "total_ge_70": true,
   "total_ge_85": false
  },
  "official_award_status": "not_determined",
  "seal_statement": "Conditional: the B1-only diagnostic total is below the 85 score condition; a Seal depends on a complete-application evaluation and the budget outcome; no Seal is claimed or predicted.",
  "legacy_benchmark_92": {
   "distance": 11.6,
   "note": "legacy internal benchmark from round one; not an official threshold or demonstrated funding line"
  },
  "b1_only_qualification": "Part A and Part B2 not assessed; not an official or complete-application evaluation."
 },
 "lens_scores": {
  "E1": {
   "excellence": 4.1,
   "impact": 4.2,
   "implementation": 3.8,
   "total": 81.4
  },
  "E2": {
   "excellence": 3.9,
   "impact": 4.0,
   "implementation": 3.6,
   "total": 77.4
  },
  "E3": {
   "excellence": 4.3,
   "impact": 4.2,
   "implementation": 3.8,
   "total": 83.4
  },
  "spread": {
   "excellence": 0.4,
   "impact": 0.2,
   "implementation": 0.2
  }
 },
 "aspect_assessments": {
  "status": "non_official_diagnostic; not used to compute criterion scores",
  "exc-obj": {
   "E1": 4.5,
   "E2": 4.2,
   "E3": 4.5,
   "consensus": 4.4
  },
  "exc-method": {
   "E1": 4.0,
   "E2": 3.7,
   "E3": 4.7,
   "consensus": 4.0
  },
  "exc-supervision": {
   "E1": 3.8,
   "E2": 3.9,
   "E3": 3.7,
   "consensus": 3.8
  },
  "exc-researcher": {
   "E1": 4.2,
   "E2": 4.0,
   "E3": 3.9,
   "consensus": 4.0
  },
  "imp-career": {
   "E1": 4.5,
   "E2": 4.3,
   "E3": 4.4,
   "consensus": 4.4
  },
  "imp-dissemination": {
   "E1": 4.2,
   "E2": 4.1,
   "E3": 4.2,
   "consensus": 4.2
  },
  "imp-magnitude": {
   "E1": 3.8,
   "E2": 3.6,
   "E3": 3.6,
   "consensus": 3.7
  },
  "impl-workplan": {
   "E1": 3.7,
   "E2": 3.6,
   "E3": 3.7,
   "consensus": 3.7
  },
  "impl-host": {
   "E1": 3.9,
   "E2": 3.6,
   "E3": 3.7,
   "consensus": 3.7
  }
 },
 "consensus_resolution": {
  "method": "reasoned reconciliation on evidence; no averaging; no tariff; no caps",
  "excellence": "E3 4.3 vs E2 3.9: E2's textual findings (undefined screen comparator, undisclosed archive spectra, unaligned pixel geometry, no precision statement) accepted as verifiable; E3's view of the architecture accepted; four major findings retained; lower half of 'very good' -> 4.1",
  "impact": "all lenses: magnitude unquantified (major) plus minors; E2 additionally weighs research-only collapse -> 4.1",
  "implementation": "all lenses: unidentified field and M1–M3 compression major; E2 adds start window and M20–M21 -> upper 'good' 3.7",
  "rejected_at_consensus": [
   {
    "id": "E3-W13",
    "reason": "manuscript timing follows deliverable months; two papers proportionate to a 24-month EF"
   }
  ],
  "dissents": [
   {
    "finding": "R2-F-07",
    "lens": "E3",
    "lens_severity": "major",
    "consensus_severity": "minor"
   },
   {
    "finding": "R2-F-08",
    "lens": "E3",
    "lens_severity": "major",
    "consensus_severity": "minor"
   }
  ],
  "disposition_table": "Annex A.4 of the Markdown report"
 },
 "formal_checks": [
  {
   "id": "FC-01",
   "rule": "artefact identity (prompt table)",
   "measured": "sha256 and size match; HEAD e8e8d23",
   "pages": "all",
   "status": "pass",
   "consequence": "none",
   "distinct_from_scoring": true,
   "confidence": "high"
  },
  {
   "id": "FC-02",
   "rule": "Sections 1–3 ≤ 10 pages incl. tables/figures/references (template; WP p. 80)",
   "measured": "10 physical pages; no cover or TOC",
   "pages": "all",
   "status": "pass",
   "consequence": "none",
   "distinct_from_scoring": true,
   "confidence": "high"
  },
  {
   "id": "FC-03",
   "rule": "A4 (template)",
   "measured": "210.0 × 297.0 mm all pages",
   "pages": "all",
   "status": "pass",
   "consequence": "none",
   "distinct_from_scoring": true,
   "confidence": "high"
  },
  {
   "id": "FC-04",
   "rule": "margins ≥ 15 mm excl. header/footer (template)",
   "measured": "body ink left 15.0 mm, right 15.0 mm (span boxes 14.0 mm due to trailing space); top body 25.7–26.4 mm; bottom ≥ 20 mm; DOCX 15.01 mm",
   "pages": "all",
   "status": "pass",
   "consequence": "none",
   "distinct_from_scoring": true,
   "confidence": "high",
   "correction": "PF-C1"
  },
  {
   "id": "FC-04b",
   "rule": "margins ≥ 15 mm applied to table rules",
   "measured": "borders at 13.6 mm right (pp. 5,6,7,10) and 14.5 mm left (p. 9); table text ≥ 15.5 mm",
   "pages": "5,6,7,9,10",
   "status": "fail",
   "consequence": "≤ 1.4 mm protrusion; repair costs no space",
   "distinct_from_scoring": true,
   "confidence": "high"
  },
  {
   "id": "FC-05",
   "rule": "reference body font TNR (template)",
   "measured": "body TNR 11.04 pt",
   "pages": "all",
   "status": "pass",
   "consequence": "none",
   "distinct_from_scoring": true,
   "confidence": "high"
  },
  {
   "id": "FC-06",
   "rule": "min 11 pt body text including text in tables (template)",
   "measured": "all six tables at 9.96 pt (~11,700 chars, ~25% of body content)",
   "pages": "5,6,7,9,10",
   "status": "fail",
   "consequence": "formatting condition not met; regression from sealed 11 pt; repair ≈ +30 lines",
   "distinct_from_scoring": true,
   "confidence": "high"
  },
  {
   "id": "FC-07",
   "rule": "non-body elements legible and ≥ 8 pt (template)",
   "measured": "footnotes 9.0 pt pass; header 8.04/footer 8.52 pass; Gantt raster labels ≈ 6–7 pt",
   "pages": "1,4,9",
   "status": "fail",
   "consequence": "Gantt text below 8 pt; regression from ≈ 8.5 pt; repair by re-render, no space",
   "distinct_from_scoring": true,
   "confidence": "medium"
  },
  {
   "id": "FC-08",
   "rule": "≥ single line spacing (template)",
   "measured": "12.6–12.8 pt at 11 pt; 11.5 pt at 10 pt",
   "pages": "all",
   "status": "pass",
   "consequence": "none",
   "distinct_from_scoring": true,
   "confidence": "high"
  },
  {
   "id": "FC-09",
   "rule": "standard character spacing (template)",
   "measured": "no Tz/Tw; Tc −0.13…+0.06 pt kerning; DOCX no spacing attributes",
   "pages": "all",
   "status": "pass",
   "consequence": "none",
   "distinct_from_scoring": true,
   "confidence": "high",
   "correction": "PF-C2"
  },
  {
   "id": "FC-10",
   "rule": "template headings/structure B1",
   "measured": "1, 1.1–1.4, 2, 2.1–2.3, 3, 3.1–3.2 in order; B2 pointers correct",
   "pages": "all",
   "status": "pass",
   "consequence": "none",
   "distinct_from_scoring": true,
   "confidence": "high"
  },
  {
   "id": "FC-11",
   "rule": "Gantt content and elapsed months (template)",
   "measured": "WPs, deliverables, milestones, secondments, placement; months 1–30; consistent with text",
   "pages": "9",
   "status": "pass",
   "consequence": "none",
   "distinct_from_scoring": true,
   "confidence": "high"
  },
  {
   "id": "FC-12",
   "rule": "no clipped/hidden content, placeholders, comments, tracked changes, blank pages",
   "measured": "renders and content-stream scan: none",
   "pages": "all",
   "status": "pass",
   "consequence": "none",
   "distinct_from_scoring": true,
   "confidence": "high"
  },
  {
   "id": "FC-13",
   "rule": "PDF with embedded fonts (template)",
   "measured": "11/11 embedded; PDF 1.7; unencrypted",
   "pages": "all",
   "status": "pass",
   "consequence": "none",
   "distinct_from_scoring": true,
   "confidence": "high"
  },
  {
   "id": "FC-14",
   "rule": "header/footer and page numbering",
   "measured": "template header; 'Part B - Page N of 10' correct",
   "pages": "all",
   "status": "pass",
   "consequence": "none",
   "distinct_from_scoring": true,
   "confidence": "high"
  },
  {
   "id": "FC-15",
   "rule": "no hyperlinks designed to expand the proposal (template)",
   "measured": "9 footnote URLs/DOIs",
   "pages": "1,4",
   "status": "pass",
   "consequence": "none",
   "distinct_from_scoring": true,
   "confidence": "high"
  },
  {
   "id": "FC-16",
   "rule": "portal submission evidence",
   "measured": "not a portal export",
   "pages": null,
   "status": "not_applicable",
   "consequence": "portal_submission_verified=false",
   "distinct_from_scoring": true,
   "confidence": "high"
  }
 ],
 "findings": [
  {
   "finding_id": "R2-F-01",
   "origin": "residual",
   "criterion": "excellence",
   "aspect_id": "exc-method",
   "severity": "major",
   "description": "The five-season MATE archive on which O1 and O2 depend is not characterised: plot numbers and sizes, treatments, cultivars, physiological variables per season, sampling frequency and the spectral range of the instruments are not stated.",
   "evidence": "\"unusually rich five-season (2022–2026) archive of physiological, soil, meteorological and proximal-spectral observations\" (p. 1); \"bands outside the instrument's range are dropped, not reconstructed\" (p. 2)",
   "location": {
    "pdf_pages": [
     1,
     2,
     10
    ],
    "section": "1.1; 1.2 Stage 1; 3.2 MATE row",
    "anchor_kind": "prose",
    "anchor": "§1.1 O1; §1.2 ¶Stage 1 (WP1); §3.2 table row MATE"
   },
   "rationale": "Adequacy of the training base for leave-one-year-out validation and for a control-relative reference cannot be judged; SWIR synthesis unknown.",
   "affected_lenses": [
    "E1",
    "E2"
   ],
   "consensus_disposition": "retained",
   "linked_old_ids": [
    "F-01",
    "F-02",
    "W12",
    "W13",
    "E2-b",
    "OD-E5"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-02",
   "origin": "new",
   "criterion": "excellence",
   "aspect_id": "exc-method",
   "severity": "major",
   "description": "The D1.2 engineering screen does not state what the median absolute index discrepancy is measured against; with no plot-level Sentinel-2 counterpart for historical plots it cannot test proximal-to-satellite transfer before the freeze; its thresholds are unjustified; the canopy-cover confound is not named among the diagnostics.",
   "evidence": "\"A predictor is retained only if it passes the D1.2 engineering screen (median absolute index discrepancy ≤0.25 historical standard deviations, ≤10% change in stress classifications on a locked sensitivity set)\" (p. 2)",
   "location": {
    "pdf_pages": [
     2
    ],
    "section": "1.2 Stage 1",
    "anchor_kind": "prose",
    "anchor": "§1.2 ¶Stage 1 (WP1), screen sentence"
   },
   "rationale": "Predictor retention rests on an undefined comparison; if the stress classifications are model outputs the screen is a selection step outside the outer folds.",
   "affected_lenses": [
    "E2"
   ],
   "consensus_disposition": "retained (single lens, textually verified)",
   "linked_old_ids": [
    "F-01",
    "R01"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-03",
   "origin": "new",
   "criterion": "excellence",
   "aspect_id": "exc-method",
   "severity": "major",
   "description": "Sentinel-2 sampling geometry and matching are under-specified: a 40 × 40 m core holds four whole 20 m pixels only if grid-aligned and no alignment rule is stated; the physiology-to-acquisition matching window is absent; the 30% attrition assumption is asserted while R3 rates 'too few matched dates' as high likelihood.",
   "evidence": "\"a 20 m inward buffer leaving a 40 × 40 m interior core\"; \"≥4 valid pixels per area and date\" (pp. 2–3); \"R3 | WP2 | H/M\" (p. 9)",
   "location": {
    "pdf_pages": [
     2,
     3,
     9
    ],
    "section": "1.2 Stage 2; 3.1 risk table",
    "anchor_kind": "prose/table",
    "anchor": "§1.2 ¶Stage 2 (WP2) s2; §3.1 risk table row R3"
   },
   "rationale": "The 202 area-date basis may be smaller than presented or rely on buffer pixels.",
   "affected_lenses": [
    "E1",
    "E2"
   ],
   "consensus_disposition": "retained (merged)",
   "linked_old_ids": [
    "E2-f",
    "W12"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-04",
   "origin": "residual",
   "criterion": "excellence",
   "aspect_id": "exc-method",
   "severity": "major",
   "description": "No precision, minimum detectable advantage or power statement accompanies the decision criteria for a test with 12 experimental units per season and about 202 clustered area-dates; the locked agronomic comparator and the frozen reference model are not identified; the lead-time metric has no reference event.",
   "evidence": "\"balanced accuracy ≥0.70 with a demonstrated advantage over a locked agronomic comparator, positive Brier skill against a frozen reference model\" (p. 3); K6 \"with uncertainty or non-estimability explained\" (p. 8)",
   "location": {
    "pdf_pages": [
     3,
     8
    ],
    "section": "1.2 decision criteria; 3.1 K6",
    "anchor_kind": "prose",
    "anchor": "§1.2 ¶Stage 1 decision-criteria sentence; §3.1 WP2 K6"
   },
   "rationale": "MS3 decisions may rest on estimates whose uncertainty spans the thresholds.",
   "affected_lenses": [
    "E1",
    "E2"
   ],
   "consensus_disposition": "retained (merged)",
   "linked_old_ids": [
    "F-02",
    "R02",
    "R03"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-05",
   "origin": "new",
   "criterion": "excellence",
   "aspect_id": "exc-method",
   "severity": "minor",
   "description": "Declared fallbacks change the evidence type without corresponding updates: a continuous primary endpoint leaves the classification criteria unmapped; a failed spectral screen removes the hyperspectral-to-Sentinel result family relied on in §2.2 and §2.3; rephasing alters K5, K6 and the MS3 evidential basis.",
   "evidence": "\"one continuous physiological endpoint becomes the primary reference\" (p. 2); \"the hyperspectral-to-Sentinel transfer methodology\" (p. 7); \"formally rephased or the evidence claim narrowed\" (p. 9)",
   "location": {
    "pdf_pages": [
     2,
     6,
     7,
     9
    ],
    "section": "1.2; 2.2; 2.3; 3.1",
    "anchor_kind": "prose/table",
    "anchor": "§1.2 ¶Overall methodology fallback; §2.2 Exploitation pathway; §3.1 ¶Critical path"
   },
   "rationale": "Coherence gap between fallbacks and the criteria, KPIs and result families.",
   "affected_lenses": [
    "E2",
    "E3"
   ],
   "consensus_disposition": "retained",
   "linked_old_ids": [
    "F-01",
    "F-02",
    "R01",
    "R02"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-06",
   "origin": "residual",
   "criterion": "excellence",
   "aspect_id": "exc-supervision",
   "severity": "major",
   "description": "Supervisors' experience is thinly evidenced: one co-supervised doctorate (2023) for the primary supervisor, no postdoctoral supervision or topic-specific record, the co-supervisor evidenced by one 2010 publication, an unnamed deputy and an undescribed conflict-resolution route.",
   "evidence": "\"co-supervisor of a 2023 doctoral dissertation at Széchenyi István University\"; \"a documented continuity arrangement designates a deputy for prolonged absence\" (p. 4)",
   "location": {
    "pdf_pages": [
     4
    ],
    "section": "1.3",
    "anchor_kind": "prose",
    "anchor": "§1.3 ¶Supervisory architecture; ¶Planned training activities"
   },
   "rationale": "Template asks for supervision experience at PhD and postdoctoral level; met only partly.",
   "affected_lenses": [
    "E1",
    "E2",
    "E3"
   ],
   "consensus_disposition": "retained",
   "linked_old_ids": [
    "F-06",
    "W16",
    "OD-E4"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-07",
   "origin": "new",
   "criterion": "excellence",
   "aspect_id": "exc-supervision",
   "severity": "minor",
   "description": "The 12-month ELTE secondment is at the permitted maximum, its added value is described functionally rather than argued, and ATK-located practicals are scheduled inside the M1–M3 and M10–M12 secondment blocks while K11 counts 12 secondment months.",
   "evidence": "\"M1–M3 at ATK (Prof. Janda, Dr Takács)\"; \"M1–M3 and M10–M12 at ATK (Dr Hollós)\" (p. 4); \"12 secondment months evidenced\" (p. 8)",
   "location": {
    "pdf_pages": [
     4,
     5,
     8,
     10
    ],
    "section": "1.3; 2.1; 3.1 K11; 3.2 ELTE row",
    "anchor_kind": "prose/table",
    "anchor": "§1.3 ¶Planned training activities s2; §3.1 K11"
   },
   "rationale": "Content of the secondment months is unclear; E3 rates this major.",
   "affected_lenses": [
    "E1",
    "E2",
    "E3"
   ],
   "consensus_disposition": "retained; E3 dissent (major) recorded",
   "linked_old_ids": [
    "F-07",
    "W17"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-08",
   "origin": "residual",
   "criterion": "excellence",
   "aspect_id": "exc-researcher",
   "severity": "minor",
   "description": "The researcher's modelling and Earth-observation competence for O2 is evidenced by short training stays, a traineeship and an undescribed prototype; the publication record is described qualitatively.",
   "evidence": "\"with working use of Python, R and EO tools\"; \"a pre-existing desktop research prototype\" (p. 5)",
   "location": {
    "pdf_pages": [
     5
    ],
    "section": "1.4",
    "anchor_kind": "prose",
    "anchor": "§1.4 ¶A profile matched"
   },
   "rationale": "Feasibility of the M3 freeze rests on supervision intensity; E3 rates this major.",
   "affected_lenses": [
    "E1",
    "E2",
    "E3"
   ],
   "consensus_disposition": "retained; E3 dissent (major) recorded",
   "linked_old_ids": [
    "F-08",
    "W18",
    "OD-E18"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-09",
   "origin": "residual",
   "criterion": "excellence",
   "aspect_id": "exc-obj",
   "severity": "minor",
   "description": "State-of-the-art positioning rests on five references and does not review satellite-scale crop water-stress detection; the categorical novelty statement is asserted more than demonstrated.",
   "evidence": "\"none has been tested as a model frozen before deployment and carried, with its uncertainty, across years, an independent field and the proximal-to-satellite scale\" (p. 1)",
   "location": {
    "pdf_pages": [
     1,
     2
    ],
    "section": "1.1",
    "anchor_kind": "prose",
    "anchor": "§1.1 ¶Pertinence"
   },
   "rationale": "Ambition is real but its location relative to satellite-based work is not shown.",
   "affected_lenses": [
    "E2",
    "E3"
   ],
   "consensus_disposition": "retained",
   "linked_old_ids": [
    "F-05",
    "W14",
    "OD-E17"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-10",
   "origin": "residual",
   "criterion": "excellence",
   "aspect_id": "exc-method",
   "severity": "minor",
   "description": "Campaign logistics that protect the control-relative stomatal-conductance reference over a multi-hour campaign on about 7.7 ha are not stated (measurement window, block order, personnel).",
   "evidence": "\"sample five spatially distributed plants per area\" (p. 3)",
   "location": {
    "pdf_pages": [
     3
    ],
    "section": "1.2 Stage 2",
    "anchor_kind": "prose",
    "anchor": "§1.2 ¶Stage 2 (WP2) s2"
   },
   "rationale": "Within-campaign drift can bias the relative reference; staffing unknown (cross-consequence in impl-workplan).",
   "affected_lenses": [
    "E1",
    "E2"
   ],
   "consensus_disposition": "retained",
   "linked_old_ids": [
    "E1-own-3",
    "R02"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-11",
   "origin": "new",
   "criterion": "excellence",
   "aspect_id": "exc-supervision",
   "severity": "minor",
   "description": "The fellow-to-host transfer overlaps the host's own declared expertise; the fellow's distinctive assets are not linked to what the hosts gain.",
   "evidence": "\"The fellow contributes drought-stress physiology, remotely monitored plant-stress responses, field physiological phenotyping\" (p. 4)",
   "location": {
    "pdf_pages": [
     4
    ],
    "section": "1.3",
    "anchor_kind": "prose",
    "anchor": "§1.3 ¶Two-way transfer s2"
   },
   "rationale": "Two-way transfer is asymmetric in substance.",
   "affected_lenses": [
    "E2",
    "E3"
   ],
   "consensus_disposition": "retained",
   "linked_old_ids": [],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-12",
   "origin": "new",
   "criterion": "excellence",
   "aspect_id": "exc-supervision",
   "severity": "minor",
   "description": "Transferable-skills training is entirely embedded with no named course or provider, and innovation/entrepreneurship training is absent although spin-off exploration is foreseen.",
   "evidence": "\"grant-writing clinic and FMIS evaluation\" (p. 4); \"researcher-led start-up/spin-off exploration\" (p. 6)",
   "location": {
    "pdf_pages": [
     4,
     6
    ],
    "section": "1.3; 2.1; 2.2",
    "anchor_kind": "prose/table",
    "anchor": "§1.3 ¶Planned training activities; §2.2 Exploitation row"
   },
   "rationale": "Work programme expects innovation and entrepreneurship training where applicable.",
   "affected_lenses": [
    "E3"
   ],
   "consensus_disposition": "retained",
   "linked_old_ids": [],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-13",
   "origin": "residual",
   "criterion": "impact",
   "aspect_id": "imp-magnitude",
   "severity": "major",
   "description": "No quantified indication of magnitude or importance for agricultural, economic or societal impacts; the eligible-uptake denominator is deferred to the placement.",
   "evidence": "\"no numerical water-saving benefit is claimed in advance\"; \"quantified during the placement (denominator, date, definition)\" (p. 7)",
   "location": {
    "pdf_pages": [
     7
    ],
    "section": "2.3",
    "anchor_kind": "prose/table",
    "anchor": "§2.3 table Agricultural & environmental row; ¶Impact is measured"
   },
   "rationale": "Template asks for credible quantified estimates where possible; contribution beyond science cannot be sized.",
   "affected_lenses": [
    "E1",
    "E2",
    "E3"
   ],
   "consensus_disposition": "retained",
   "linked_old_ids": [
    "F-11",
    "W21",
    "OD-E8"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-14",
   "origin": "residual",
   "criterion": "impact",
   "aspect_id": "imp-dissemination",
   "severity": "minor",
   "description": "Tools and channels for the wider public are not identified; public engagement is one-way.",
   "evidence": "\"three illustrated explainers (M3, M12, M24)\" with \"views and downloads\" but no platform (p. 6)",
   "location": {
    "pdf_pages": [
     6
    ],
    "section": "2.2",
    "anchor_kind": "table",
    "anchor": "§2.2 table Communication row"
   },
   "rationale": "Template requires tools and channels per target group.",
   "affected_lenses": [
    "E1",
    "E2",
    "E3"
   ],
   "consensus_disposition": "retained",
   "linked_old_ids": [
    "F-12",
    "W20",
    "OD-E9"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-15",
   "origin": "new",
   "criterion": "impact",
   "aspect_id": "imp-dissemination",
   "severity": "minor",
   "description": "Post-MSCA exploitation is a list of options without owners or decision points and depends on agreements still to be concluded.",
   "evidence": "\"Post-MSCA routes include FMIS integration, MVCRI crop extension and HUN-REN/HUNRENTECH-supported licensing or researcher-led start-up/spin-off exploration\" (p. 6)",
   "location": {
    "pdf_pages": [
     6,
     7
    ],
    "section": "2.2",
    "anchor_kind": "table",
    "anchor": "§2.2 table Exploitation row; ¶Exploitation pathway"
   },
   "rationale": "Exploitation after the project is undetermined in B1 (K10 defers to D4.2).",
   "affected_lenses": [
    "E1",
    "E2"
   ],
   "consensus_disposition": "retained",
   "linked_old_ids": [],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-16",
   "origin": "new",
   "criterion": "impact",
   "aspect_id": "imp-career",
   "severity": "minor",
   "description": "Post-fellowship positioning relies on acquired skills; no concrete positioning measure; the MVCRI route is explicitly uncommitted.",
   "evidence": "\"it is not a guaranteed position, funded activity or multi-crop validation programme\" (p. 10)",
   "location": {
    "pdf_pages": [
     5,
     10
    ],
    "section": "2.1; 3.2",
    "anchor_kind": "prose/table",
    "anchor": "§2.1 ¶Two realistic trajectories; §3.2 MVCRI row"
   },
   "rationale": "Credibility of the post-fellowship step rests on skills rather than positioning.",
   "affected_lenses": [
    "E2",
    "E3"
   ],
   "consensus_disposition": "retained",
   "linked_old_ids": [
    "F-13",
    "OD-E16"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-17",
   "origin": "new",
   "criterion": "impact",
   "aspect_id": "imp-dissemination",
   "severity": "minor",
   "description": "End-user engagement is concentrated in M25–M30 and depends on the placement host; before M25 only a practitioner brief and requirements feedback exist.",
   "evidence": "\"two demonstrations at the AgroVIR evaluation (M25–M29), one workshop of about 20 participants (M29–M30)\" (p. 6)",
   "location": {
    "pdf_pages": [
     6,
     7,
     8
    ],
    "section": "2.2; 3.1",
    "anchor_kind": "table/prose",
    "anchor": "§2.2 Communication row; §3.1 WP4"
   },
   "rationale": "User needs enter the MVP late; no independent venue if the placement changes.",
   "affected_lenses": [
    "E3"
   ],
   "consensus_disposition": "retained (single lens)",
   "linked_old_ids": [],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-18",
   "origin": "residual",
   "criterion": "implementation",
   "aspect_id": "impl-workplan",
   "severity": "major",
   "description": "The commercial field for the prospective validation is unidentified; requirements are demanding (12 independently irrigated areas incl. unirrigated and deficit regimes on about 7.7 ha, ready at M4, two consecutive seasons on one field); no incentive, compensation or agronomic acceptability is described; the backup is unidentified; a first season missed at M4 cannot be recovered; the start window is narrow; the contingency narrows O3.",
   "evidence": "\"no site is described as secured\" (p. 10); \"activate an identified comparable site only if genuinely available; otherwise rephase or narrow the evidence claim before planting\" (p. 9)",
   "location": {
    "pdf_pages": [
     3,
     9,
     10
    ],
    "section": "1.2 Stage 2; 3.1 critical path and R2; 3.2 farmer row",
    "anchor_kind": "prose/table",
    "anchor": "§1.2 ¶Stage 2 (WP2); §3.1 ¶Critical path; §3.1 risk table row R2; §3.2 table row Commercial farmer/producer"
   },
   "rationale": "Critical dependency of O3 and 9.0 PM; honest wording does not remove the delivery weakness; cross-consequence in impl-host and exc-method.",
   "affected_lenses": [
    "E1",
    "E2",
    "E3"
   ],
   "consensus_disposition": "retained (merged; E1 rotation point as aggravating sub-point, medium confidence)",
   "linked_old_ids": [
    "F-16",
    "F-18",
    "W9",
    "W24",
    "E1-own-3",
    "OD-E7",
    "OD-E11"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-19",
   "origin": "residual",
   "criterion": "implementation",
   "aspect_id": "impl-workplan",
   "severity": "major",
   "description": "Months 1–3 carry the archive audit and harmonisation, protocol lock, pipeline, validation, benchmark and the irreversible freeze (2.2 PM), plus site, contractor and placement agreements, the CDP, training at two institutions, induction and the first secondment block; the risk table covers non-reproducibility by M3 but not calendar slippage of the freeze relative to planting.",
   "evidence": "\"Pre-freeze WP1 effort is 2.2 PM of the 3.0 PM in M1–M3\" (p. 9); R1 \"pipeline not reproducible by M3: … freeze the specified baseline\" (p. 9)",
   "location": {
    "pdf_pages": [
     4,
     8,
     9
    ],
    "section": "1.3; 3.1",
    "anchor_kind": "prose",
    "anchor": "§3.1 ¶Critical path effort sentences; §1.3 ¶Planned training activities"
   },
   "rationale": "The freeze is the least resourced point of the plan; a rushed freeze weakens the tested model, a late freeze breaks the pre-registration logic.",
   "affected_lenses": [
    "E1",
    "E2",
    "E3"
   ],
   "consensus_disposition": "retained",
   "linked_old_ids": [
    "F-17",
    "W10",
    "OD-E7"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-20",
   "origin": "residual",
   "criterion": "implementation",
   "aspect_id": "impl-workplan",
   "severity": "minor",
   "description": "Effort is tilted toward software and operational work (WP3 6.0 PM against WP1 5.0 PM, 2.2 PM pre-freeze; 38% on WP3 and WP4) without justification.",
   "evidence": "\"WP3 — DrR web MVP and readiness | M1–M24 | 6.0 PM\" (p. 8)",
   "location": {
    "pdf_pages": [
     8
    ],
    "section": "3.1",
    "anchor_kind": "prose",
    "anchor": "§3.1 WP headers"
   },
   "rationale": "Balance between research training and software oversight not explained.",
   "affected_lenses": [
    "E1",
    "E3"
   ],
   "consensus_disposition": "retained",
   "linked_old_ids": [
    "W11"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-21",
   "origin": "new",
   "criterion": "implementation",
   "aspect_id": "impl-workplan",
   "severity": "minor",
   "description": "The risk register omits agronomic risks (wet season removing stress contrast, heat, pests), calendar slippage of the freeze and the M4 launch, mid-season producer withdrawal, resourcing and the M20–M21 analysis compression; contingencies for provider or placement loss name no alternative.",
   "evidence": "R1–R6 (p. 9); \"replacement provider only if secured; placement change resolved with the host\" (p. 9)",
   "location": {
    "pdf_pages": [
     9
    ],
    "section": "3.1 risk table",
    "anchor_kind": "table",
    "anchor": "§3.1 risk table rows R1–R6"
   },
   "rationale": "Mitigation weakest for the risks most likely to determine whether two seasons are achieved.",
   "affected_lenses": [
    "E1",
    "E2",
    "E3"
   ],
   "consensus_disposition": "retained (merged)",
   "linked_old_ids": [
    "F-21",
    "W22"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-22",
   "origin": "new",
   "criterion": "implementation",
   "aspect_id": "impl-workplan",
   "severity": "minor",
   "description": "The Gantt shows work-package bars only, with unlabeled milestones and abbreviated deliverables; the field-readiness gate invoked in §1.2 and §3.2 is not an explicit milestone.",
   "evidence": "Gantt rows 'Milestones', 'Deliverables A/B' (p. 9); MS1 definition (p. 9)",
   "location": {
    "pdf_pages": [
     9
    ],
    "section": "3.1 Gantt; decision gates",
    "anchor_kind": "gantt",
    "anchor": "§3.1 Gantt; ¶Decision gates MS1"
   },
   "rationale": "The single most important go/no-go decision is not separately visible.",
   "affected_lenses": [
    "E3",
    "E1",
    "E2"
   ],
   "consensus_disposition": "retained",
   "linked_old_ids": [
    "F-23",
    "OD-E20"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-23",
   "origin": "residual",
   "criterion": "implementation",
   "aspect_id": "impl-host",
   "severity": "minor",
   "description": "Access rights to the MATE archive are fixed only by an M1 audit; the R1 fallback 'redesign O1–O2' is not a specified plan.",
   "evidence": "\"redesign O1–O2 if the core archive is absent\" (p. 9); \"An M1 archive and rights audit fixes the accessible years, variables and permitted analysis\" (p. 10)",
   "location": {
    "pdf_pages": [
     9,
     10
    ],
    "section": "3.1 R1; 3.2 MATE row",
    "anchor_kind": "table",
    "anchor": "§3.1 risk table row R1; §3.2 table row MATE"
   },
   "rationale": "Second principal input unsettled at submission; contingency unspecified.",
   "affected_lenses": [
    "E1"
   ],
   "consensus_disposition": "retained",
   "linked_old_ids": [
    "F-16",
    "F-22",
    "OD-E11"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-24",
   "origin": "residual",
   "criterion": "implementation",
   "aspect_id": "impl-host",
   "severity": "minor",
   "description": "Capacity for the field programme, placement supervision and engineering is asserted: no AgroVIR supervisor named, Krumatic's capacity not outlined, field-campaign staffing and instrumentation unquantified, season-2 campaigns run from the ELTE block.",
   "evidence": "\"AgroVIR operational supervision\" (p. 8); \"The project installs soil-water and meteorological monitoring and conducts all specialised observations\" (p. 10)",
   "location": {
    "pdf_pages": [
     4,
     8,
     10
    ],
    "section": "1.3; 3.1; 3.2",
    "anchor_kind": "table/prose",
    "anchor": "§3.2 table rows AgroVIR, Krumatic, Commercial farmer; §3.1 WP4 lead"
   },
   "rationale": "Quality and capacity of two participating organisations and field logistics asserted rather than outlined.",
   "affected_lenses": [
    "E1",
    "E2",
    "E3"
   ],
   "consensus_disposition": "retained (merged)",
   "linked_old_ids": [
    "F-16",
    "F-22",
    "E1-own-3",
    "OD-E12",
    "OD-E13"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-25",
   "origin": "regressed",
   "criterion": "formal",
   "aspect_id": "none",
   "severity": "major_formal",
   "description": "All table text is set at 9.96 pt; the template requires 11 pt for body text including text in tables; the sealed submission used 11 pt tables.",
   "evidence": "PyMuPDF spans in six tables: 9.96 pt (about 11,700 characters); template V5.0: \"The minimum font size allowed is 11 points … This applies to the body text, including text in tables.\"",
   "location": {
    "pdf_pages": [
     5,
     6,
     7,
     9,
     10
    ],
    "section": "2.1; 2.2; 2.3; 3.1 risk; 3.2",
    "anchor_kind": "table",
    "anchor": "all tables"
   },
   "rationale": "Formatting condition not met; not a score deduction; repair costs about 30 lines.",
   "affected_lenses": [
    "coordinator"
   ],
   "consensus_disposition": "formal check FC-06",
   "linked_old_ids": [
    "S0-2 (sealed OK)",
    "refactoring report §12 PASS label"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-26",
   "origin": "regressed",
   "criterion": "formal",
   "aspect_id": "none",
   "severity": "minor_formal",
   "description": "Gantt labels are about 6–7 pt effective after the image height was reduced from 8.26 cm to 6.43 cm; figure text must be legible and not less than 8 pt; the sealed Gantt labels were about 8.5 pt.",
   "evidence": "Raster measurement: WP labels 17–19 px at 0.36 pt/px = 6.1–6.8 pt extents; axis digits about 6 pt",
   "location": {
    "pdf_pages": [
     9
    ],
    "section": "3.1 Gantt",
    "anchor_kind": "gantt",
    "anchor": "§3.1 Gantt image"
   },
   "rationale": "Below the 8 pt floor; repair by re-rendering costs no space.",
   "affected_lenses": [
    "coordinator"
   ],
   "consensus_disposition": "formal check FC-07",
   "linked_old_ids": [
    "S0-2 (sealed ≈ 8.5 pt)",
    "refactoring report §12 PASS label"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  },
  {
   "finding_id": "R2-F-27",
   "origin": "new",
   "criterion": "formal",
   "aspect_id": "none",
   "severity": "minor_formal",
   "description": "Table border lines protrude up to 1.4 mm into the right margin (pp. 5, 6, 7, 10) and 0.5 mm into the left margin (p. 9); table text stays inside the margins.",
   "evidence": "Vector drawings x1 = 556.4 pt (13.6 mm from the edge); DOCX tblInd 150 and 57 twips",
   "location": {
    "pdf_pages": [
     5,
     6,
     7,
     9,
     10
    ],
    "section": "tables",
    "anchor_kind": "table",
    "anchor": "table borders"
   },
   "rationale": "Marginal infraction of the 15 mm rule; repair costs no space.",
   "affected_lenses": [
    "coordinator"
   ],
   "consensus_disposition": "formal check FC-04b",
   "linked_old_ids": [
    "refactoring report §11 R 14.0 (artefact)"
   ],
   "score_effect": "reflected in the holistic criterion score; no tariff"
  }
 ],
 "round1_comparison": {
  "prior_sources": [
   "S6",
   "S7",
   "S8",
   "S9",
   "S10",
   "S11"
  ],
  "prior_scores": {
   "excellence": 3.6,
   "impact": 3.7,
   "implementation": 3.5,
   "total": 72.2,
   "scope": "full application (Part A, B1, B2)",
   "calibration": "5.0 minus per-finding deductions; 4.4 cap per major finding; 92-point fundable zone"
  },
  "current_scores": {
   "excellence": 4.1,
   "impact": 4.1,
   "implementation": 3.7,
   "total": 80.4,
   "scope": "B1 only",
   "calibration": "holistic official descriptors; no caps; no tariff"
  },
  "arithmetic_difference": {
   "excellence": 0.5,
   "impact": 0.4,
   "implementation": 0.2,
   "total": 8.2,
   "is_like_for_like": false
  },
  "like_for_like_delta": null,
  "scope_and_calibration_differences": "Round one covered Part A/B2 findings (F-09, F-19, F-24…F-29) and applied caps and tariffs; round two excludes them and scores holistically; no baseline-B1 assessment under the current method was performed.",
  "qualitative_attribution": {
   "improved": [
    "F-01…F-04 narrowed (transfer chain, design, reference, model, validation, open science)",
    "F-05 narrowed (comparators)",
    "F-07, F-14 resolved (training, continuity, CDP)",
    "F-12 narrowed (communication)",
    "F-13 resolved",
    "F-15 resolved",
    "F-16 narrowed (dependency statements)",
    "F-20 resolved",
    "F-21 resolved",
    "F-23 resolved"
   ],
   "unchanged": [
    "archive characterisation",
    "supervision record",
    "magnitude quantification",
    "field-site identity and terms",
    "M1–M3 load",
    "start-window narrowness"
   ],
   "regressed": [
    "table typography 11→10 pt (formal)",
    "Gantt label size (formal)",
    "ATK/ELTE month clash (minor, new)"
   ]
  },
  "closure_rows": [
   {
    "old_ids": [
     "F-01",
     "W12",
     "E2-f"
    ],
    "status": "partially_resolved",
    "current_anchor": "p. 2 §1.2 Stage 1",
    "round2_ids": [
     "R2-F-01",
     "R2-F-02",
     "R2-F-03"
    ],
    "note": "chain specified; screen comparator and archive range missing"
   },
   {
    "old_ids": [
     "F-02",
     "W13",
     "E1-own-1",
     "E2-b"
    ],
    "status": "partially_resolved",
    "current_anchor": "pp. 2–3 §1.2",
    "round2_ids": [
     "R2-F-01",
     "R2-F-03",
     "R2-F-04"
    ],
    "note": "dimensioned; precision and geometry not shown"
   },
   {
    "old_ids": [
     "F-03",
     "E2-a",
     "E2-c"
    ],
    "status": "resolved",
    "current_anchor": "pp. 2–3 §1.2",
    "round2_ids": [
     "R2-F-04"
    ],
    "note": "model named; paired spectra; comparator identity residual"
   },
   {
    "old_ids": [
     "F-04",
     "W15",
     "E2-d"
    ],
    "status": "resolved",
    "current_anchor": "pp. 3–4 §1.2; p. 6",
    "round2_ids": [],
    "note": "registration, Zenodo, BSD-3, preprints"
   },
   {
    "old_ids": [
     "F-05",
     "W14"
    ],
    "status": "partially_resolved",
    "current_anchor": "pp. 1–2 §1.1",
    "round2_ids": [
     "R2-F-09"
    ],
    "note": "comparators cited; satellite-scale literature absent"
   },
   {
    "old_ids": [
     "F-06",
     "W16"
    ],
    "status": "partially_resolved",
    "current_anchor": "p. 4 §1.3",
    "round2_ids": [
     "R2-F-06"
    ],
    "note": "documentary examples; no totals"
   },
   {
    "old_ids": [
     "F-07",
     "W17"
    ],
    "status": "resolved",
    "current_anchor": "p. 4 §1.3",
    "round2_ids": [
     "R2-F-07",
     "R2-F-12"
    ],
    "note": "timed schedule; new location clash"
   },
   {
    "old_ids": [
     "F-08",
     "W18"
    ],
    "status": "partially_resolved",
    "current_anchor": "p. 5 §1.4",
    "round2_ids": [
     "R2-F-08"
    ],
    "note": "links added; DrR functions undescribed"
   },
   {
    "old_ids": [
     "F-09",
     "W2",
     "F-29"
    ],
    "status": "out_of_scope",
    "current_anchor": "Part B2",
    "round2_ids": [],
    "note": "CV"
   },
   {
    "old_ids": [
     "F-10",
     "W4"
    ],
    "status": "resolved",
    "current_anchor": "p. 5 §1.4",
    "round2_ids": [],
    "note": "disputed credential omitted (B1 component)"
   },
   {
    "old_ids": [
     "F-11",
     "W21"
    ],
    "status": "partially_resolved",
    "current_anchor": "p. 7 §2.3",
    "round2_ids": [
     "R2-F-13"
    ],
    "note": "three scales and links; no quantified estimate"
   },
   {
    "old_ids": [
     "F-12",
     "W20"
    ],
    "status": "partially_resolved",
    "current_anchor": "p. 6 §2.2",
    "round2_ids": [
     "R2-F-14"
    ],
    "note": "messages/timing; public channels unnamed"
   },
   {
    "old_ids": [
     "F-13",
     "W19"
    ],
    "status": "resolved",
    "current_anchor": "p. 6 §2.1",
    "round2_ids": [
     "R2-F-16"
    ],
    "note": "dated measures; new angle on positioning"
   },
   {
    "old_ids": [
     "F-14",
     "E3-own-CDP"
    ],
    "status": "resolved",
    "current_anchor": "pp. 4, 5, 8",
    "round2_ids": [],
    "note": "cadence consistent"
   },
   {
    "old_ids": [
     "F-15",
     "E1-own-2"
    ],
    "status": "resolved",
    "current_anchor": "p. 6 §2.2",
    "round2_ids": [],
    "note": "release assets; irrigation venue"
   },
   {
    "old_ids": [
     "F-16 (field)",
     "W24",
     "E1-own-3"
    ],
    "status": "partially_resolved",
    "current_anchor": "p. 3; p. 9 R2; p. 10 farmer row",
    "round2_ids": [
     "R2-F-18"
    ],
    "note": "requirements and gate; site unidentified; compensation absent"
   },
   {
    "old_ids": [
     "F-16 (archive, contractor)",
     "F-22",
     "W8"
    ],
    "status": "partially_resolved",
    "current_anchor": "p. 10 §3.2",
    "round2_ids": [
     "R2-F-23",
     "R2-F-24"
    ],
    "note": "dependency statement; sources and capacities unstated"
   },
   {
    "old_ids": [
     "F-17",
     "W10"
    ],
    "status": "partially_resolved",
    "current_anchor": "pp. 8–9 §3.1",
    "round2_ids": [
     "R2-F-19"
    ],
    "note": "split explained; load unchanged"
   },
   {
    "old_ids": [
     "W11"
    ],
    "status": "unresolved",
    "current_anchor": "p. 8",
    "round2_ids": [
     "R2-F-20"
    ],
    "note": "folded in round one; never addressed"
   },
   {
    "old_ids": [
     "F-18",
     "W9"
    ],
    "status": "partially_resolved",
    "current_anchor": "p. 9 critical path",
    "round2_ids": [
     "R2-F-18",
     "R2-F-05"
    ],
    "note": "February start; narrow window; contingency narrows O3"
   },
   {
    "old_ids": [
     "F-19",
     "W1"
    ],
    "status": "out_of_scope",
    "current_anchor": "Part A",
    "round2_ids": [],
    "note": "secondment host registration"
   },
   {
    "old_ids": [
     "F-20",
     "W23",
     "E2-e"
    ],
    "status": "resolved",
    "current_anchor": "p. 10 ATK row",
    "round2_ids": [],
    "note": "hosting plan"
   },
   {
    "old_ids": [
     "F-21",
     "W22"
    ],
    "status": "resolved",
    "current_anchor": "p. 9",
    "round2_ids": [
     "R2-F-21"
    ],
    "note": "old omissions covered; new gaps"
   },
   {
    "old_ids": [
     "F-23",
     "W5",
     "OD-E20"
    ],
    "status": "resolved",
    "current_anchor": "pp. 1, 8, 9",
    "round2_ids": [
     "R2-F-22"
    ],
    "note": "renumbered; Gantt readability new"
   },
   {
    "old_ids": [
     "F-24",
     "W7",
     "F-28"
    ],
    "status": "out_of_scope",
    "current_anchor": "Part A",
    "round2_ids": [],
    "note": "ethics table; AI pointer"
   },
   {
    "old_ids": [
     "F-25",
     "W3",
     "F-26",
     "W6",
     "F-27",
     "E3-own-declaration"
    ],
    "status": "out_of_scope",
    "current_anchor": "Part A / B2",
    "round2_ids": [],
    "note": "cosmetics; B2 declaration"
   },
   {
    "old_ids": [
     "E1-own-4"
    ],
    "status": "unresolved",
    "current_anchor": "p. 1",
    "round2_ids": [],
    "note": "2026 season completeness not stated; note only, not scored"
   },
   {
    "old_ids": [
     "W25"
    ],
    "status": "not_a_weakness",
    "current_anchor": "pp. 4, 5, 8, 10",
    "round2_ids": [],
    "note": "placement and secondment compliant on recheck"
   },
   {
    "old_ids": [
     "E3-own-co-creation"
    ],
    "status": "retained_strength",
    "current_anchor": "pp. 6–7, 10",
    "round2_ids": [],
    "note": "end-user evaluation present"
   },
   {
    "old_ids": [
     "S0-2 (sealed typography OK)"
    ],
    "status": "regressed",
    "current_anchor": "pp. 5–10",
    "round2_ids": [
     "R2-F-25",
     "R2-F-26"
    ],
    "note": "tables 10 pt; Gantt ≈ 6–7 pt"
   }
  ],
  "watchlist_verdicts": "Part II.7.2 of the Markdown report (12 items)"
 },
 "revision_actions": [
  {
   "action_id": "R2-A-01",
   "priority": "P0",
   "finding_ids": [
    "R2-F-25"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "formatting",
   "anchor": "all tables (DOCX style FW Table 10 pt)",
   "instruction": "Set every table run and paragraph to 11 pt; keep single spacing; do not shrink any other element.",
   "rationale": "Template applies the 11 pt minimum to text in tables; the sealed version complied.",
   "owner": "operator",
   "safe_response": null,
   "dependencies": [
    "R2-CUT-01",
    "R2-CUT-02",
    "R2-CUT-03",
    "R2-CUT-04",
    "R2-CUT-05",
    "R2-CUT-06",
    "R2-CUT-07",
    "R2-CUT-09",
    "R2-CUT-10",
    "R2-CUT-12",
    "R2-CUT-13"
   ],
   "gross_lines_added": 29.5,
   "gross_lines_removed": 0,
   "cut_ids": [
    "R2-CUT-01",
    "R2-CUT-02",
    "R2-CUT-03",
    "R2-CUT-04",
    "R2-CUT-07",
    "R2-CUT-08",
    "R2-CUT-09",
    "R2-CUT-10",
    "R2-CUT-12",
    "R2-CUT-13"
   ],
   "verification": "PyMuPDF: min non-superscript span size in every table bbox ≥ 10.95 pt; page count 10; Gantt on p. 9; §2.1 rows intact across pp. 5–6",
   "effort": "medium",
   "regression_risk": "high",
   "leverage": "high"
  },
  {
   "action_id": "R2-A-02",
   "priority": "P0",
   "finding_ids": [
    "R2-F-26"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "formatting",
   "anchor": "p. 9 Gantt image (source figure in tools/build_partb1_refactored.py)",
   "instruction": "Re-render at the same 17.99 × 6.43 cm frame with label and tick fonts scaled to ≥ 8 pt effective (row pitch 18 pt allows 9 pt); export ≥ 300 ppi; content unchanged.",
   "rationale": "Figure text must be ≥ 8 pt.",
   "owner": "operator",
   "safe_response": null,
   "dependencies": [],
   "gross_lines_added": 0,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Raster extents ≥ 9 pt; labels legible at 100%",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "high"
  },
  {
   "action_id": "R2-A-03",
   "priority": "P0",
   "finding_ids": [
    "R2-F-27"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "formatting",
   "anchor": "DOCX tables tblInd 150 (five tables) and 57 (risk table)",
   "instruction": "Set table indent to 0 and keep table width within the text width so borders sit inside 15 mm.",
   "rationale": "All margins ≥ 15 mm.",
   "owner": "operator",
   "safe_response": null,
   "dependencies": [],
   "gross_lines_added": 0,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Drawings bbox x0 ≥ 42.5 pt and x1 ≤ 552.8 pt on every page",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "medium"
  },
  {
   "action_id": "R2-A-04",
   "priority": "P1",
   "finding_ids": [
    "R2-F-07"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "accepted_design_consistency",
   "anchor": "p. 4 §1.3 ¶Planned training activities s2",
   "instruction": "Relabel the two ATK-provider practicals in M1–M3 and M10–M12 as delivered through the fortnightly joint sessions already stated; move no month.",
   "rationale": "Removes the location clash with the ELTE blocks and keeps K11 consistent.",
   "owner": "operator",
   "safe_response": "Wording W1 uses only facts already in the text.",
   "dependencies": [],
   "gross_lines_added": 0,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "No 'at ATK' inside a month range equal to an ELTE block; K11 unchanged",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "medium",
   "proposed_wording": "M1–M3 (Prof. Janda, Dr Takács, through the fortnightly joint sessions), physiological-reference and irrigation-design practical; M1–M3 and M10–M12 (Dr Hollós, joint sessions), blocked validation, calibration and uncertainty practical"
  },
  {
   "action_id": "R2-A-05",
   "priority": "P1",
   "finding_ids": [
    "R2-F-02"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "accepted_design_consistency",
   "anchor": "p. 2 §1.2 ¶Stage 1 screen sentence",
   "instruction": "State what the screen compares (archive cross-instrument and cross-season consistency of synthetic indices), that the stress classes it uses are reference-defined, and that the prospective paired spectra apply the same tolerance diagnostically.",
   "rationale": "Implements brief R01 steps 5–6 as accepted; removes an undefined comparison and a possible selection outside folds.",
   "owner": "operator",
   "safe_response": "Wording W2.",
   "dependencies": [],
   "gross_lines_added": 2,
   "gross_lines_removed": 0,
   "cut_ids": [
    "R2-CUT-06"
   ],
   "verification": "Both quantities of the discrepancy identifiable; no model output enters predictor selection outside folds",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "high",
   "proposed_wording": "; the screen compares synthetic indices across archive instruments and seasons, and the stress classes it uses are reference-defined, not model outputs; the prospective paired spectra apply the same tolerance as a diagnostic without altering the frozen model"
  },
  {
   "action_id": "R2-A-06",
   "priority": "P1",
   "finding_ids": [
    "R2-F-05"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "accepted_design_consistency",
   "anchor": "p. 2 §1.2 fallback sentences (continuous endpoint; failed spectral transfer)",
   "instruction": "Add the consequence mapping for both fallbacks: criteria restated as regression/calibration criteria in D1.2 with classification KPIs secondary; negative transfer result reported and MVP limited to baseline functions.",
   "rationale": "The brief's alternatives are accepted; their consequences for criteria, KPIs and result families were not carried into the text.",
   "owner": "operator",
   "safe_response": "Wording W3.",
   "dependencies": [],
   "gross_lines_added": 2,
   "gross_lines_removed": 0,
   "cut_ids": [
    "R2-CUT-05"
   ],
   "verification": "Every fallback names its effect on criteria, KPIs and result families",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "medium",
   "proposed_wording": "…becomes the primary reference, D1.2 restates the decision criteria as pre-specified regression and calibration criteria, and the classification KPIs are reported as secondary. … failed spectral transfer is reported as a negative transfer result, the transfer methodology is delivered as that report, and the MVP is limited to the baseline functions."
  },
  {
   "action_id": "R2-A-07",
   "priority": "P2",
   "finding_ids": [
    "R2-F-03"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "accepted_design_consistency",
   "anchor": "p. 3 §1.2 Stage 2 s2 end; p. 10 farmer row",
   "instruction": "Add the grid-alignment requirement and the matching-window rule (value fixed in D1.2 if not decided).",
   "rationale": "Makes the ≥ 4-pixel rule attainable by construction or its non-attainment handled.",
   "owner": "operator; fellow for the window value",
   "safe_response": "aligned to the Sentinel-2 20 m grid where the field permits; matched within a window fixed in D1.2",
   "dependencies": [
    "R2-A-01"
   ],
   "gross_lines_added": 2,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Alignment and window statements present",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "medium"
  },
  {
   "action_id": "R2-A-08",
   "priority": "P2",
   "finding_ids": [
    "R2-F-04"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "editorial",
   "anchor": "p. 3 §1.2 decision-criteria sentence",
   "instruction": "Name the locked comparator (pre-specified AquaCrop/soil-water rule) and the reference model (soil-water/meteorological baseline); state that D1.2 fixes the required interval precision and that criteria are judged on interval bounds where estimable.",
   "rationale": "Brief R03 already prescribes agreeing precision before fitting; both comparators are mentioned elsewhere in the text.",
   "owner": "operator",
   "safe_response": "Wording W4.",
   "dependencies": [],
   "gross_lines_added": 2,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Comparator, reference model and precision rule identifiable in one sentence",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "high",
   "proposed_wording": "…over the locked agronomic comparator (the pre-specified AquaCrop/soil-water rule), positive Brier skill against the frozen soil-water/meteorological baseline … D1.2 fixes the interval precision required for each criterion, which is judged on interval bounds where estimable."
  },
  {
   "action_id": "R2-A-09",
   "priority": "P2",
   "finding_ids": [
    "R2-F-18"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "accepted_design_consistency",
   "anchor": "p. 10 §3.2 farmer row after 'no site is described as secured.'",
   "instruction": "Add the field-use terms procedure: irrigation-control responsibilities and compensation for yield loss in deficit and unirrigated areas agreed before planting under the host-approved arrangement.",
   "rationale": "Brief R12/R15 accepted; names the producer's burden with owner and deadline without claiming a site or payment.",
   "owner": "operator",
   "safe_response": "Wording W5.",
   "dependencies": [
    "R2-A-01"
   ],
   "gross_lines_added": 1,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Producer burden named with owner and deadline; no site or payment claimed",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "medium",
   "proposed_wording": "Field-use terms, including irrigation-control responsibilities and compensation for yield loss in deficit and unirrigated areas, are agreed with the producer before planting under the host-approved arrangement."
  },
  {
   "action_id": "R2-A-10",
   "priority": "P2",
   "finding_ids": [
    "R2-F-18"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "editorial",
   "anchor": "p. 9 ¶Critical path 'a feasible start is chosen within the permitted grant window before launch'",
   "instruction": "Insert the start window that fits the design: 'between February and March'.",
   "rationale": "Brief R13 calendar option.",
   "owner": "operator",
   "safe_response": null,
   "dependencies": [],
   "gross_lines_added": 0.5,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Sentence still reads as a plan",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "low"
  },
  {
   "action_id": "R2-A-11",
   "priority": "P2",
   "finding_ids": [
    "R2-F-23"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "accepted_design_consistency",
   "anchor": "p. 9 risk table R1 'redesign O1–O2 if the core archive is absent'",
   "instruction": "Replace with the accepted re-scope rule: O1–O2 re-scoped to the accessible seasons and variables, recorded in D1.1 and D1.2.",
   "rationale": "Brief R12 fallback; a decision and a record instead of an open redesign.",
   "owner": "operator",
   "safe_response": "Wording W6.",
   "dependencies": [
    "R2-A-01"
   ],
   "gross_lines_added": 1,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "R1 names a decision and a record",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "medium",
   "proposed_wording": "if the accessible subset lacks the common variables, O1–O2 are re-scoped to the accessible seasons and variables and the reduced scope is recorded in D1.1 and D1.2"
  },
  {
   "action_id": "R2-A-12",
   "priority": "P2",
   "finding_ids": [
    "R2-F-21"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "accepted_design_consistency",
   "anchor": "p. 9 risk table R2 and R3",
   "instruction": "Add 'producer withdrawal within a season' to R2 with the existing rephase/narrow response; add 'weak stress contrast in a wet season' to R3 with the response 'reported as reduced power under K6'.",
   "rationale": "K6 non-estimability and the R2 procedure are accepted design.",
   "owner": "operator",
   "safe_response": "Wording W7.",
   "dependencies": [
    "R2-A-01"
   ],
   "gross_lines_added": 1,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Two most likely delivery risks have triggers and responses",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "medium"
  },
  {
   "action_id": "R2-A-13",
   "priority": "P2",
   "finding_ids": [
    "R2-F-22"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "editorial",
   "anchor": "p. 9 ¶Decision gates MS1",
   "instruction": "Insert 'field-readiness gate decided;' into the MS1 definition.",
   "rationale": "The gate invoked in §1.2 and §3.2 becomes a milestone element.",
   "owner": "operator",
   "safe_response": null,
   "dependencies": [],
   "gross_lines_added": 0,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "'field-readiness gate' appears in MS1",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "low"
  },
  {
   "action_id": "R2-A-14",
   "priority": "P2",
   "finding_ids": [
    "R2-F-14"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "accepted_design_consistency",
   "anchor": "p. 6 §2.2 Communication row, public sub-item",
   "instruction": "Name the channel under project control: a fellow-maintained project page, with host and AgroVIR channels where the hosts agree.",
   "rationale": "Brief R09 fallback; supplies a tool and channel for the wider-public target group.",
   "owner": "operator",
   "safe_response": "Wording W8.",
   "dependencies": [
    "R2-A-01"
   ],
   "gross_lines_added": 1,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "A tool and channel exists for the public target group",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "medium",
   "proposed_wording": ", published on a fellow-maintained project page and, where the hosts agree, through HUN-REN ATK, ELTE and AgroVIR channels"
  },
  {
   "action_id": "R2-A-15",
   "priority": "P2",
   "finding_ids": [
    "R2-F-15"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "editorial",
   "anchor": "p. 6 §2.2 Exploitation row 'Post-MSCA routes include …'",
   "instruction": "Append 'each route assigned an owner and a decision gate in the D4.2 roadmap (K10)'.",
   "rationale": "K10 already states it.",
   "owner": "operator",
   "safe_response": null,
   "dependencies": [],
   "gross_lines_added": 0.5,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Options tied to an owner and decision point",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "low"
  },
  {
   "action_id": "R2-A-16",
   "priority": "P2",
   "finding_ids": [
    "R2-F-07"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "editorial",
   "anchor": "p. 4 §1.3 'The 12-month ELTE secondment (…) hosts the EO strands.'",
   "instruction": "Add: the secondment provides instrument, laboratory and supervision access for the EO strands that HUN-REN ATK does not hold.",
   "rationale": "Facts in the §3.2 ELTE row; answers the template's secondment rationale.",
   "owner": "operator",
   "safe_response": null,
   "dependencies": [],
   "gross_lines_added": 1,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Secondment added value stated in one sentence",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "medium"
  },
  {
   "action_id": "R2-A-17",
   "priority": "P2",
   "finding_ids": [
    "R2-F-11"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "editorial",
   "anchor": "p. 4 §1.3 ¶Two-way transfer s2",
   "instruction": "Name the fellow's distinctive assets already in §1.4 (vegetable-crop field phenotyping in Bulgarian production systems, UAV qualification, the DrR prototype) and what the hosts gain.",
   "rationale": "Facts already in §1.4.",
   "owner": "operator",
   "safe_response": null,
   "dependencies": [],
   "gross_lines_added": 1,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Both directions name distinct content",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "low"
  },
  {
   "action_id": "R2-A-18",
   "priority": "P2",
   "finding_ids": [
    "R2-F-10"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "accepted_design_consistency",
   "anchor": "p. 3 §1.2 Stage 2 'sample five spatially distributed plants per area.'",
   "instruction": "Add the campaign protocol clause: fixed morning window, blocks in rotating order, controls interleaved with treatments, time of day logged.",
   "rationale": "Brief R02 records time of day and VPD; protects the relative reference.",
   "owner": "operator",
   "safe_response": "Wording W9.",
   "dependencies": [],
   "gross_lines_added": 1,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Reference protected against within-campaign drift",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "medium",
   "proposed_wording": ", measured within a fixed morning window with blocks in rotating order and controls interleaved with treatments, time of day logged"
  },
  {
   "action_id": "R2-A-19",
   "priority": "P2",
   "finding_ids": [
    "R2-F-20"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "editorial",
   "anchor": "p. 9 effort paragraph after 'Training within scientific tasks is counted once.'",
   "instruction": "Add: WP3 fellow effort covers specification, acceptance tests and scientific-consistency testing (T3.1–T3.4); engineering is contracted.",
   "rationale": "Explains the WP3 share without changing PM.",
   "owner": "operator",
   "safe_response": null,
   "dependencies": [],
   "gross_lines_added": 1,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "WP3 share explained",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "low"
  },
  {
   "action_id": "R2-A-20",
   "priority": "P2",
   "finding_ids": [
    "R2-F-12"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "editorial",
   "anchor": "p. 4 §1.3 'grant-writing clinic and FMIS evaluation'",
   "instruction": "Rename to 'grant-writing, valorisation and entrepreneurship clinic'.",
   "rationale": "Exploitation already foresees spin-off exploration; no new provider claimed.",
   "owner": "operator",
   "safe_response": null,
   "dependencies": [],
   "gross_lines_added": 0,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Training list covers innovation and entrepreneurship",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "low"
  },
  {
   "action_id": "R2-A-21",
   "priority": "P4",
   "finding_ids": [],
   "target_document": "PART_B1_DOCX",
   "action_class": "editorial",
   "anchor": "p. 10 farmer row 'An independent Hungarian farmer/producer, irrespective of gender,'",
   "instruction": "Delete 'irrespective of gender,'.",
   "rationale": "Stray phrase.",
   "owner": "operator",
   "safe_response": null,
   "dependencies": [],
   "gross_lines_added": 0,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Phrase absent",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "low"
  },
  {
   "action_id": "R2-A-22",
   "priority": "P3",
   "finding_ids": [
    "R2-F-01"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "needs_fact",
   "anchor": "p. 1 O1; p. 2 Stage 1; p. 10 MATE row",
   "instruction": "State instrument, spectral range, plots per season, treatments, variables and dates once MATE supplies them (OD-E5).",
   "rationale": "Archive is the sole training base.",
   "owner": "MATE / Dr Takács",
   "safe_response": "Keep conditional wording; add 'the M1 audit (D1.1) fixes the instrument range and per-season variable coverage; SWIR coverage is not assumed'",
   "dependencies": [],
   "gross_lines_added": 2,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Dimensions appear or their absence is explicit",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "high"
  },
  {
   "action_id": "R2-A-23",
   "priority": "P3",
   "finding_ids": [
    "R2-F-06"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "needs_fact",
   "anchor": "p. 4 §1.3 ¶Supervisory architecture",
   "instruction": "Add verified supervision totals, one or two named current collaborations and the deputy's role if supplied (OD-E4).",
   "rationale": "Template asks for supervision experience.",
   "owner": "Prof. Janda; Prof. Jung; Dr Hollós",
   "safe_response": "Keep documentary examples; never state totals",
   "dependencies": [],
   "gross_lines_added": 2,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Totals and collaborations sourced",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "high"
  },
  {
   "action_id": "R2-A-24",
   "priority": "P3",
   "finding_ids": [
    "R2-F-13"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "needs_fact",
   "anchor": "p. 7 §2.3 three-scale sentence",
   "instruction": "Insert the eligible-uptake subset (farms, hectares, definition, date) and a sourced irrigated processing-tomato area if supplied (OD-E8).",
   "rationale": "Template asks for quantified estimates.",
   "owner": "AgroVIR; host",
   "safe_response": "Keep the bounded statement; no national figure established",
   "dependencies": [],
   "gross_lines_added": 2,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Every number has a source and denominator",
   "effort": "low",
   "regression_risk": "medium",
   "leverage": "high"
  },
  {
   "action_id": "R2-A-25",
   "priority": "P3",
   "finding_ids": [
    "R2-F-08"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "needs_fact",
   "anchor": "p. 5 §1.4 DrR clause",
   "instruction": "Add prototype version or dated declaration, implemented functions, one reproducible demonstration; name training certificates (OD-E18).",
   "rationale": "Evidence of modelling competence.",
   "owner": "fellow",
   "safe_response": "Keep current wording",
   "dependencies": [],
   "gross_lines_added": 1,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Functions named; no mature-software claim",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "medium"
  },
  {
   "action_id": "R2-A-26",
   "priority": "P3",
   "finding_ids": [
    "R2-F-24"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "needs_fact",
   "anchor": "p. 10 AgroVIR, Krumatic and farmer rows; p. 4 §1.3",
   "instruction": "Name the AgroVIR operational supervisor, outline Krumatic's team and track record, state campaign staffing and instruments (OD-E12, OD-E13).",
   "rationale": "Capacity of participating organisations.",
   "owner": "AgroVIR; Krumatic; ATK",
   "safe_response": "Keep procedural wording; do not claim allocation",
   "dependencies": [],
   "gross_lines_added": 2,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Each capacity claim has an owner",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "medium"
  },
  {
   "action_id": "R2-A-27",
   "priority": "P3",
   "finding_ids": [
    "R2-F-09"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "needs_fact",
   "anchor": "pp. 1–2 §1.1 ¶Pertinence; footnotes",
   "instruction": "Add one satellite-scale crop water-stress reference and a positioning clause (OD-E17).",
   "rationale": "Novelty proportionality.",
   "owner": "fellow",
   "safe_response": "Keep current comparators",
   "dependencies": [
    "page-count check"
   ],
   "gross_lines_added": 3,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Reference resolvable; claim proportionate",
   "effort": "low",
   "regression_risk": "medium",
   "leverage": "low"
  },
  {
   "action_id": "R2-A-28",
   "priority": "P3",
   "finding_ids": [
    "R2-F-17"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "needs_decision",
   "anchor": "p. 6 §2.2 Communication row (M12 brief)",
   "instruction": "Decide whether the M12 brief opens a structured feedback round with growers recruited through AgroVIR.",
   "rationale": "Earlier user input; independence from the placement.",
   "owner": "host; AgroVIR",
   "safe_response": "Keep the M25–M30 concentration",
   "dependencies": [],
   "gross_lines_added": 1,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Feedback before M25 has owner and month",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "low"
  },
  {
   "action_id": "R2-A-29",
   "priority": "P3",
   "finding_ids": [
    "R2-F-16"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "needs_decision",
   "anchor": "p. 5 §2.1 ¶Two realistic trajectories",
   "instruction": "Name one positioning measure (scheme or position type and month) if the fellow decides it; no scheme without eligibility.",
   "rationale": "Career credibility.",
   "owner": "fellow",
   "safe_response": "Keep current trajectories",
   "dependencies": [],
   "gross_lines_added": 1,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Measure is a decision, not a promised award",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "low"
  },
  {
   "action_id": "R2-A-30",
   "priority": "P3",
   "finding_ids": [
    "R2-F-04"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "needs_fact",
   "anchor": "p. 3 §1.2 decision criteria",
   "instruction": "Replace the precision rule with simulated interval precision from archive counts when supplied (brief R02).",
   "rationale": "Statistical resolution of the central test.",
   "owner": "MATE; fellow; Dr Hollós",
   "safe_response": "R2-A-08 rule statement",
   "dependencies": [
    "R2-A-22"
   ],
   "gross_lines_added": 1,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Precision figures traceable to counts",
   "effort": "medium",
   "regression_risk": "low",
   "leverage": "high"
  },
  {
   "action_id": "R2-A-31",
   "priority": "P3",
   "finding_ids": [
    "R2-F-24",
    "R2-F-21"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "needs_fact",
   "anchor": "p. 10 Krumatic row; §3.2 intro",
   "instruction": "State the funding source of the engineering and instrumentation (OD-E13).",
   "rationale": "Resource credibility.",
   "owner": "host",
   "safe_response": "Keep the priority order",
   "dependencies": [],
   "gross_lines_added": 1,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Source named without a Part A change",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "medium"
  },
  {
   "action_id": "R2-A-32",
   "priority": "P3",
   "finding_ids": [
    "R2-F-07"
   ],
   "target_document": "PART_B1_DOCX",
   "action_class": "needs_decision",
   "anchor": "p. 4 §1.3; p. 10 ELTE row",
   "instruction": "Confirm with ELTE the content of each secondment block beyond the module and the clinic (OD-E15 residual).",
   "rationale": "E3 dissent on secondment value.",
   "owner": "Prof. Jung",
   "safe_response": "R2-A-04 and R2-A-16",
   "dependencies": [],
   "gross_lines_added": 0,
   "gross_lines_removed": 0,
   "cut_ids": [],
   "verification": "Block content matches K11",
   "effort": "low",
   "regression_risk": "low",
   "leverage": "low"
  }
 ],
 "do_not_touch": [
  {
   "location": "p. 2 §1.1 Beyond the state of the art",
   "reason": "clearest statement of ambition; credited by all lenses"
  },
  {
   "location": "pp. 1–2 §1.1 Measurability and verifiability",
   "reason": "metrics, M3 freeze, falsifiable hypothesis"
  },
  {
   "location": "p. 3 §1.2 Stage 2 s1, s4–s6",
   "reason": "frozen-model logic"
  },
  {
   "location": "p. 3 §1.2 Methodological challenges (i)–(vi)",
   "reason": "mitigation list credited by E1/E2"
  },
  {
   "location": "p. 3 §1.2 Gender dimension",
   "reason": "accepted justified statement"
  },
  {
   "location": "p. 4 §1.3 Structured supervision and governance",
   "reason": "governance credited"
  },
  {
   "location": "p. 4 §1.3 Two-way transfer s2–s4",
   "reason": "concrete transfer (R2-A-17 appends only)"
  },
  {
   "location": "p. 5 §1.3 Placement rationale s1–s5",
   "reason": "compliance-critical placement wording"
  },
  {
   "location": "pp. 6–7 §2.2 Exploitation row, IP row, Exploitation pathway",
   "reason": "strongest Impact strand (R2-A-15 appends inside the row)"
  },
  {
   "location": "p. 7 §2.3 'no numerical water-saving benefit is claimed in advance'",
   "reason": "honest bounding"
  },
  {
   "location": "pp. 8–9 §3.1 WP headers, task months, PM, deliverable months, K1–K14, MS1–MS6",
   "reason": "reconciles with the Gantt"
  },
  {
   "location": "p. 9 §3.1 Decision gates; Risk control integrity rule",
   "reason": "named approvers; integrity rule"
  },
  {
   "location": "p. 9 Gantt",
   "reason": "re-render only for fonts (R2-A-02)"
  },
  {
   "location": "pp. 5–6 §2.1 table split",
   "reason": "row-break sensitive"
  },
  {
   "location": "pp. 1, 4 footnotes 1–9",
   "reason": "page fill non-linear"
  },
  {
   "location": "p. 7 three-scale magnitude sentence; p. 10 dependency statement and priority order; p. 9 R1–R6 triggers; p. 4 timed training; p. 6 Communication row",
   "reason": "new credited strengths; appends only"
  }
 ],
 "regression_checks": [
  "protected passages verbatim after edits (whitespace-normalised)",
  "WP totals 5.0/9.0/6.0/5.4/4.6 = 30.0; 24.0 in M1–M24; 6.0 in M25–M30; WP1 2.2 + 2.8",
  "deliverable months and Gantt labels unchanged; MS1–MS6 at 3/12/21/24/27/30",
  "ELTE blocks M1–M3, M10–M12, M16–M21 (12 months) and placement M25–M30 unchanged incl. K11",
  "CDP cadence identical in §1.3, §2.1 table, §3.1",
  "no new fact about access, allocation, agreements, supervision totals, deputies, providers, budgets or results",
  "Section 3 starts p. 8; Gantt ends p. 9; §3.2 on p. 10"
 ],
 "open_decisions": [
  {
   "id": "R2-OD-01",
   "owner": "MATE / Dr Takács",
   "fact": "archive instrument, spectral range, plots, treatments, variables, dates, permissions",
   "needed_by": "before M1 audit (D1.1) and M3 freeze",
   "safe_response": "conditional conversion; accessible subset; M1 rights audit",
   "residual": "R2-F-01, R2-F-23",
   "links": [
    "OD-E5",
    "OD-E11",
    "R2-A-22"
   ]
  },
  {
   "id": "R2-OD-02",
   "owner": "producer + ATK",
   "fact": "site identity/description, polygons, irrigation control, two-season availability, compensation, backup",
   "needed_by": "field-readiness gate before planting (M3–M4)",
   "safe_response": "adopted requirements; 'no site is described as secured'",
   "residual": "R2-F-18",
   "links": [
    "OD-E11",
    "R2-A-09"
   ]
  },
  {
   "id": "R2-OD-03",
   "owner": "Prof. Janda, Prof. Jung, Dr Hollós",
   "fact": "supervision totals; current collaborations; deputy identity; committed time",
   "needed_by": "before text is finalised",
   "safe_response": "documentary examples; deputy arrangement without identity",
   "residual": "R2-F-06",
   "links": [
    "OD-E4",
    "R2-A-23"
   ]
  },
  {
   "id": "R2-OD-04",
   "owner": "AgroVIR; host",
   "fact": "eligible-uptake subset; sourced crop area; recruitment capacity",
   "needed_by": "before text is finalised (denominator otherwise during placement)",
   "safe_response": "dated public footprint as context; targets not commitments",
   "residual": "R2-F-13",
   "links": [
    "OD-E8",
    "R2-A-24"
   ]
  },
  {
   "id": "R2-OD-05",
   "owner": "fellow",
   "fact": "DrR version/functions; certificates; manuscript status",
   "needed_by": "before text is finalised",
   "safe_response": "prototype wording; 'under review'",
   "residual": "R2-F-08",
   "links": [
    "OD-E18",
    "R2-A-25"
   ]
  },
  {
   "id": "R2-OD-06",
   "owner": "ELTE / Prof. Jung",
   "fact": "paired-spectrum access; instrument/operator time; block content",
   "needed_by": "before each block (M1, M10, M16)",
   "safe_response": "access arranged before each block; no allocation claimed",
   "residual": "R2-F-07",
   "links": [
    "OD-E15",
    "R2-A-32"
   ]
  },
  {
   "id": "R2-OD-07",
   "owner": "host (ATK)",
   "fact": "funding source for engineering and instrumentation; campaign staffing; AgroVIR supervisor; Krumatic capacity",
   "needed_by": "before paid development (M1–M3) and before season 1",
   "safe_response": "resource-priority order; procedural wording",
   "residual": "R2-F-24, R2-F-21",
   "links": [
    "OD-E12",
    "OD-E13",
    "R2-A-26",
    "R2-A-31"
   ]
  },
  {
   "id": "R2-OD-08",
   "owner": "fellow + supervisors",
   "fact": "matching window; precision requirement; satellite-scale reference; positioning measure; earlier feedback round",
   "needed_by": "before D1.2 (M3); text items before submission",
   "safe_response": "D1.2 records the decisions",
   "residual": "R2-F-03, R2-F-04, R2-F-09, R2-F-16, R2-F-17",
   "links": [
    "R2-A-07",
    "R2-A-08",
    "R2-A-27",
    "R2-A-28",
    "R2-A-29",
    "R2-A-30"
   ]
  },
  {
   "id": "R2-OD-09",
   "owner": "operator",
   "fact": "confirmation of the adopted work programme text (repository copy is a DRAFT)",
   "needed_by": "before external reliance on thresholds",
   "safe_response": "values consistent with the final evaluation form",
   "residual": "none for scoring",
   "links": []
  }
 ],
 "cut_pool": [
  {
   "cut_id": "R2-CUT-01",
   "location": "p. 5 §2.1 table row 'ATK modelling training and 12-month ELTE secondment', mechanism cell",
   "text": "compress to two lines",
   "lines": 3,
   "region": "A",
   "why_safe": "duplicates §1.3 timed schedule",
   "allocated_to": "R2-A-01"
  },
  {
   "cut_id": "R2-CUT-02",
   "location": "p. 7 §2.3 table Scientific row, contribution cell",
   "text": "compress to one line",
   "lines": 2,
   "region": "A",
   "why_safe": "duplicates §1.1–§1.2",
   "allocated_to": "R2-A-01"
  },
  {
   "cut_id": "R2-CUT-03",
   "location": "p. 10 §3.2 ATK row s2 (supervisor sentence)",
   "text": "remove",
   "lines": 1.5,
   "region": "C",
   "why_safe": "stated in §1.3",
   "allocated_to": "R2-A-01"
  },
  {
   "cut_id": "R2-CUT-04",
   "location": "p. 10 §3.2 ELTE row per-block task list",
   "text": "remove the list; keep 'access arranged before each block'",
   "lines": 1,
   "region": "C",
   "why_safe": "stated in §1.3",
   "allocated_to": "R2-A-01"
  },
  {
   "cut_id": "R2-CUT-05",
   "location": "p. 6 §2.1 'By completion, the fellow will have taken …'",
   "text": "compress to two lines",
   "lines": 2,
   "region": "A",
   "why_safe": "trajectory stated in §1.4 and §2.1 opener",
   "allocated_to": "R2-A-06"
  },
  {
   "cut_id": "R2-CUT-06",
   "location": "p. 3 §1.2 Integration of methods, last sentence",
   "text": "compress to one clause",
   "lines": 1,
   "region": "A",
   "why_safe": "generic closer",
   "allocated_to": "R2-A-05"
  },
  {
   "cut_id": "R2-CUT-07",
   "location": "p. 7 §2.2 Reach and uptake, repeated counts",
   "text": "remove repeated counts",
   "lines": 1.5,
   "region": "A",
   "why_safe": "counts in the Communication row",
   "allocated_to": "R2-A-01"
  },
  {
   "cut_id": "R2-CUT-08",
   "location": "p. 5 §1.4 'The fellowship addresses the next step in her progression …'",
   "text": "compress to one line",
   "lines": 1.5,
   "region": "A",
   "why_safe": "duplicates §2.1 opener",
   "allocated_to": "R2-A-01"
  },
  {
   "cut_id": "R2-CUT-09",
   "location": "p. 8 §3.1 opening paragraph s2 (ELTE blocks sentence)",
   "text": "remove",
   "lines": 1,
   "region": "B",
   "why_safe": "duplicate of §1.3, §3.2, Gantt, K11",
   "allocated_to": "R2-A-01"
  },
  {
   "cut_id": "R2-CUT-10",
   "location": "p. 8 §3.1 WP5 'Lead: …' line",
   "text": "merge into T5.1",
   "lines": 0.5,
   "region": "B",
   "why_safe": "no content lost",
   "allocated_to": "R2-A-01"
  },
  {
   "cut_id": "R2-CUT-11",
   "location": "p. 7 §2.3 intro bounding sentence",
   "text": "not offered",
   "lines": 0,
   "region": "A",
   "why_safe": "credited strength",
   "allocated_to": null
  },
  {
   "cut_id": "R2-CUT-12",
   "location": "p. 5 §1.4 clause '… deepened through the distributed ELTE secondment and specialist supervision at HUN-REN ATK.'",
   "text": "remove clause",
   "lines": 1.5,
   "region": "A",
   "why_safe": "described in §1.3",
   "allocated_to": "R2-A-01"
  },
  {
   "cut_id": "R2-CUT-13",
   "location": "p. 9 risk table R4 and R6 response cells",
   "text": "shorten to one line each",
   "lines": 1.5,
   "region": "B",
   "why_safe": "integrity rule carries the principle",
   "allocated_to": "R2-A-01"
  }
 ],
 "cut_ledger": [
  {
   "cut_id": "R2-CUT-01",
   "consumer": "R2-A-01",
   "lines": 3,
   "region": "A"
  },
  {
   "cut_id": "R2-CUT-02",
   "consumer": "R2-A-01",
   "lines": 2,
   "region": "A"
  },
  {
   "cut_id": "R2-CUT-03",
   "consumer": "R2-A-01",
   "lines": 1.5,
   "region": "C"
  },
  {
   "cut_id": "R2-CUT-04",
   "consumer": "R2-A-01",
   "lines": 1,
   "region": "C"
  },
  {
   "cut_id": "R2-CUT-05",
   "consumer": "R2-A-06",
   "lines": 2,
   "region": "A"
  },
  {
   "cut_id": "R2-CUT-06",
   "consumer": "R2-A-05",
   "lines": 1,
   "region": "A"
  },
  {
   "cut_id": "R2-CUT-07",
   "consumer": "R2-A-01",
   "lines": 1.5,
   "region": "A"
  },
  {
   "cut_id": "R2-CUT-08",
   "consumer": "R2-A-01",
   "lines": 1.5,
   "region": "A"
  },
  {
   "cut_id": "R2-CUT-09",
   "consumer": "R2-A-01",
   "lines": 1,
   "region": "B"
  },
  {
   "cut_id": "R2-CUT-10",
   "consumer": "R2-A-01",
   "lines": 0.5,
   "region": "B"
  },
  {
   "cut_id": "R2-CUT-12",
   "consumer": "R2-A-01",
   "lines": 1.5,
   "region": "A"
  },
  {
   "cut_id": "R2-CUT-13",
   "consumer": "R2-A-01",
   "lines": 1.5,
   "region": "B"
  }
 ],
 "minimum_revision_set": {
  "action_ids": [
   "R2-A-01",
   "R2-A-02",
   "R2-A-03",
   "R2-A-04",
   "R2-A-05",
   "R2-A-06",
   "R2-A-10",
   "R2-A-13",
   "R2-A-15",
   "R2-A-20",
   "R2-A-21"
  ],
  "ordering": [
   "apply all cuts R2-CUT-01…13 except none withheld",
   "R2-A-01",
   "R2-A-02",
   "R2-A-03",
   "R2-A-04",
   "R2-A-05",
   "R2-A-06",
   "R2-A-10",
   "R2-A-13",
   "R2-A-15",
   "R2-A-20",
   "R2-A-21",
   "re-export and measure (II.6)"
  ],
  "page_budget_assumptions": {
   "table_growth_factor_10_to_11pt": 1.21,
   "table_growth_lines": 29.5,
   "region_A": {
    "additions": 21.4,
    "slack": 11.4,
    "cuts": 12.5,
    "margin": 2.5
   },
   "region_B": {
    "additions": 4.7,
    "slack": 3.3,
    "cuts": 3.0,
    "margin": 1.6,
    "condition": "risk-table growth must not push the Gantt off p. 9"
   },
   "region_C": {
    "additions": 8.5,
    "slack": 6.4,
    "cuts": 2.5,
    "margin": 0.4
   },
   "formal_repair_costs_included": true,
   "b1_to_b2_moves": "none permitted"
  },
  "residual_weaknesses": [
   "R2-F-01",
   "R2-F-03",
   "R2-F-04",
   "R2-F-06",
   "R2-F-08",
   "R2-F-09",
   "R2-F-10",
   "R2-F-11",
   "R2-F-13",
   "R2-F-14",
   "R2-F-15",
   "R2-F-16",
   "R2-F-17",
   "R2-F-18",
   "R2-F-19",
   "R2-F-20",
   "R2-F-21",
   "R2-F-23",
   "R2-F-24"
  ],
  "removed_or_narrowed": [
   "R2-F-02",
   "R2-F-05",
   "R2-F-07 (location clash)",
   "R2-F-12 (naming)",
   "R2-F-15 (narrowed)",
   "R2-F-22 (gate)",
   "R2-F-25",
   "R2-F-26",
   "R2-F-27"
  ],
  "second_wave_conditional": [
   "R2-A-08",
   "R2-A-09",
   "R2-A-07",
   "R2-A-11",
   "R2-A-12",
   "R2-A-14",
   "R2-A-16",
   "R2-A-18",
   "R2-A-17",
   "R2-A-19"
  ],
  "leverage": "compliance and design coherence; no numerical gain projected",
  "final_pagination_verified": false
 },
 "limitations": [
  "Part B1 only; Part A and Part B2 not assessed; not an official or complete-application evaluation",
  "simulated evaluators; genuine isolation between lenses but not blind to the existence of an earlier round (memory-index headings)",
  "work programme thresholds read from a DRAFT-watermarked repository copy; portal topic page not readable",
  "raster text sizes measured with ±0.5 pt tolerance; table growth at 11 pt estimated with a 1.21 factor",
  "no baseline-B1 assessment under the current method; like_for_like_delta null",
  "no owner facts became available; safe responses remain",
  "final pagination of any revised export unverified"
 ],
 "validation_results": {
  "json_parses": true,
  "ids_unique": true,
  "references_resolve": true,
  "cuts_single_use": true,
  "scores_match_markdown": true,
  "errors": [],
  "schema_validation": "not performed (local extension)"
 }
}
```
