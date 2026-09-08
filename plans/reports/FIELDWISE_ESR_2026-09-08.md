# Evaluation Summary Report — FIELDWISE (101373105)

*Simulated ESR prepared 2026-09-08 for the version sealed by the Funding & Tenders Portal on 2026-09-07 17:25:34 CET (submission SEP-211392861; 38 pages; SHA-256 `c3bfb51f93b4c0c36221d0bd83dab77efaa619eee4f3dd937e58d728c3f81dbe`, verified). Part I uses only the sealed PDF, the HE MSCA Evaluation Form V2.2 and the MSCA Work Programme 2026–2027.*

## PROJECT

| Field | Value |
|---|---|
| Project number | 101373105 |
| Project name | FIELDWISE — The Digital Agronomist: Physiologically Validated Plant-Based Water-Stress Prediction for Transferable Irrigation Decision Support in High-Value Horticulture |
| Project acronym | FIELDWISE |
| Coordinator contact | Prof. Tibor JANDA, HUN-REN Agrártudományi Kutatóközpont |
| Call | HORIZON-MSCA-2026-PF-01 |
| Topic | HORIZON-MSCA-2026-PF-01-01 |
| Type of action | HORIZON-TMA-MSCA-PF-EF |
| Responsible service | REA |
| Project duration | 30 months (24-month fellowship + 6-month non-academic placement) |

## PARTICIPANTS

| Number | Role | Short name | Legal name | Country | PIC |
|---|---|---|---|---|---|
| 1 | COO | HUN-REN Agrártudományi Kutatóközpont | HUN-REN Agrartudomanyi Kutatokozpont | HU | 866599553 |
| 2 | AP | Agrovir | AGROVIR Uzletviteli Tanacsado Korlatolt Felelossegu Tarsasag | HU | 891807622 |

¹ Part B-2, table 5.1, additionally lists Eötvös Loránd University (ELTE, PIC 999896468) as "associated partner for secondment", hosting 12 of the 24 fellowship months. ELTE does not appear in Part A.

## PROJECT ABSTRACT

FIELDWISE addresses a central limitation in current crop water-stress prediction: the lack of physiologically validated models whose predictive validity is tested explicitly across years, environments and sensing scales before operational deployment. Building on a five-season (2022–2026) processing-tomato archive, the project will integrate physiological, soil-water, meteorological and proximal hyperspectral observations within a harmonised framework and derive Sentinel-2-compatible predictor definitions. An interpretable, uncertainty-aware probabilistic model will be developed under leakage-safe unseen-year validation and frozen before any prospective-field outcome is observed. Its transferability will then be evaluated over two commercial-field seasons using actual Sentinel-2, soil-water and meteorological inputs, while coordinated plant-physiological measurements provide independent evidence of realised stress. FIELDWISE will quantify not only predictive discrimination, but also calibration, uncertainty, false-alarm behaviour, warning lead time and the magnitude of the experimental-to-commercial-field transfer gap before any limited recalibration. Only scientifically validated functions will be incorporated into the MVP, which will then be tested by a commercial farm-management information system (FMIS) software company within its network of farmers to assess operational usability, interoperability and practical relevance under operational farming conditions. The project therefore aims to establish a transferable and auditable framework for precision-irrigation decision support, distinguishing components that remain robust across sensing scales and production environments from those requiring crop-specific recalibration and revalidation.

## EVALUATION

| Field | Value |
|---|---|
| Evaluation model | single |
| Panel | ENV |
| Evaluators | E1, E2, E3 (simulated) |

## 1. EVALUATION

### 1. Excellence

**Strengths:**

- The four objectives are bound to dated deliverables and pre-specified metrics (balanced accuracy, F1, ROC-AUC, reliability and Brier score, warning lead time, false-alarm rate), so they are measurable and verifiable (Section 1.1).
- The validation logic makes the central hypothesis falsifiable: model, predictors and evaluation rules are frozen at month 3, tested under blocked unseen-year validation on a five-season archive, then tested prospectively over two commercial-field seasons with primary performance reported before any recalibration (Sections 1.1 and 1.2).
- The stress construct is physiologically anchored: irrigation treatments and AquaCrop-based crop-water demand define the imposed deficit, while chlorophyll fluorescence and stomatal conductance provide independent evidence of realised stress (Sections 1.1 and 1.2).
- The integration of plant physiology, agronomy, Earth observation, predictive modelling and software engineering is explicit and role-assigned, proximal and satellite observations are treated as non-interchangeable, and the gender dimension is addressed with a justified non-relevance statement (Section 1.2).
- Supervision is structured (one-to-one meetings, specialist sessions, monthly written monitoring, a Project Steering Group with pre-defined decision responsibilities), the two-way transfer of knowledge is concrete in both directions, and the non-academic placement is integral, end-positioned and justified for the project and the researcher's career (Section 1.3).
- The researcher's physiological measurement competences match the measurement programme, and her transition towards Earth observation and data science is documented through named training stays (Section 1.4; Part B-2, Section 4).

**Weaknesses:**

- The hyperspectral-to-Sentinel-2 harmonisation on which the frozen model depends is not specified: the historical plots are too small for plot-level Sentinel-2 retrieval, the conversion of handheld hyperspectral measurements is committed only "where technically possible", and no spectral-response, correction, scaling or acceptance procedure is given (Section 1.2).
- The experimental and statistical design is not dimensioned: number and size of treatment areas and replicates, observations per campaign, campaigns per season and sample sizes are absent, the stress-reference rule and the acceptance thresholds are deferred to deliverable D1.2, growth stage is not considered, and the model family and the uncertainty and calibration methods are not named (Sections 1.1 and 1.2).
- The state of the art rests on four references, one of them a bare institutional web address, without engagement with existing crop water-stress indicators for tomato; open-science practices name no repository, licence, preprint or pre-registration, and code sharing is conditional on institutional, commercial and IP rights (Sections 1.1 and 1.2).
- The supervisors' qualifications are asserted rather than evidenced: no record of PhD or postdoctoral supervision and no named international collaborations are given, and the supporting outputs are one cited paper each for the modelling and Earth-observation supervisors (Section 1.3; Part B-2, Section 5.2).
- Training is described by topic only, without named courses, providers or timing; teaching in Plovdiv is planned "where feasible"; primary supervision during the first secondment block (months 1–3), which coincides with the model freeze, is not described (Section 1.3).
- The researcher's water-stress and Earth-observation outputs are one 2025 proceedings paper and two manuscripts under review; the data-science training is unnamed and the DrR prototype is not documented (Section 1.4; Part B-2, Section 4).
- The CV omits full dates for positions, degrees and the career break, gives no significance or open-access notes for outputs, and lists no invited presentations, funding or supervision; Section 1.4 states that the researcher holds an Environmental Engineering Master's degree, whereas the CV lists it as ongoing studies (Section 1.4; Part B-2, Section 4).

**Score 1 (0–5): 3.6** — **Weighting: 50 %**

### 2. Impact

**Strengths:**

- The career-development measures are concrete and evidenced: two named post-fellowship trajectories, a Career Development Plan due at month 3, a table linking each measure to a deliverable or KPI (K11), and a six-month placement with its own deliverables (Section 2.1).
- The exploitation and intellectual-property strand is mature for a fellowship: four exploitable result families, separate rights layers for background, results, institutional datasets and contracted code, a dated baseline declaration for the pre-existing prototype, and a defined host–contractor agreement (Section 2.2).
- Dissemination targets are quantified and dated (at least two open-access peer-reviewed manuscripts, EGU/ECPA presentations, a model card, at least one end-user workshop by month 30) (Sections 2.2 and 3.1).
- Impact claims are bounded to what the action measures, and end-users are involved in requirements gathering and operational evaluation, in line with the action's expectation of end-user co-creation (Sections 1.2, 2.3 and 3.2).

**Weaknesses:**

- The magnitude of the contribution is not quantified: no irrigated area, number of growers or FMIS users, size of the software partner's farmer network, or link to European water or agricultural policy frames and to the work programme's expected impacts is given; the "European & societal" row is generic, and the statement that "no numerical water-saving benefit is claimed in advance" is not accompanied by any other quantified estimate (Section 2.3).
- The communication strategy lacks the main messages, tools, channels and timing per target group: "public-facing articles", a "farmer/end-user workshop" and "institutional and public-engagement activities" are listed without specification, and "reach indicators" are undefined (Section 2.2).
- Leadership, grant writing and network building are listed as skills but are not converted into measures (no planned grant application, network membership or mentoring role); teaching in Plovdiv is conditional (Sections 1.3 and 2.1).
- The Career Development Plan review cadence is inconsistent: quarterly reviews in Sections 1.3 and 3.1 against reviews at months 3, 12, 21, 24 and 27 in the Section 2.1 table.
- Data and software as impact vehicles are unspecific: "monitoring of repository use after release" names no repository, no release plan (licence, identifier) exists for the harmonised archive or the prospective dataset, whose reuse rights depend on undetermined archive terms, and the dissemination venues are Earth-observation and precision-agriculture forums only (Sections 2.2 and 3.2).

**Score 2 (0–5): 3.7** — **Weighting: 30 %**

### 3. Quality and efficiency of the implementation

**Strengths:**

- The work plan is complete and internally consistent: five work packages with monthly task windows, thirteen dated deliverables, six milestones, fourteen KPIs, effort summing to 30.0 person-months, and a Gantt chart in elapsed months showing secondment blocks and placement (Section 3.1).
- Milestones operate as decision gates with named approvers and an explicit critical path from model freeze to prospective evidence, permitted functions, release and external evaluation (Section 3.1).
- Each risk has an owner and a trigger response, monitoring is monthly, and poor transfer is declared a reportable result that does not authorise unsupported advice (Section 3.1).
- Host and partner capacity is documented: phenotyping and Fitotron facilities and prior MSCA and Horizon Europe experience at the beneficiary, a geoinformatics laboratory with field-spectroscopy and UAV capacity at the secondment host, FMIS infrastructure at the placement host (Part B-2, Section 5.2).

**Weaknesses:**

- Four of the seven organisations in the capacity table (archive owner, software contractor, the unnamed commercial farmer and the Bulgarian institute) hold no formal role although objectives O1–O3 depend on the archive and the commercial field; access is "documented before analysis and exploitation", no existing agreement or commitment is stated, and field size, irrigation system and treatment layout are not described (Section 3.2; Part B-2, Section 5.1).
- Months 1–3 concentrate archive audit and harmonisation, protocol lock, pipeline construction, model fitting and freeze, field-access and IP agreements and the Career Development Plan, all during the first secondment block; the feasibility of this concurrency and the 5.0 person-months assigned to WP1 are not justified (Section 3.1).
- The plan states that "the crop calendar must place MS1 before season 1 and the second harvest by M20", yet gives no assumed start month and no contingency for a start outside the transplanting window; risk R2 presupposes a compatible start (Section 3.1).
- Part A lists two participating organisations while Part B-2 lists the secondment host, which hosts twelve of the twenty-four months, as a formal participant; the secondment is not anchored in the administrative forms (Part A; Part B-2, Section 5.1).
- Hosting arrangements are generic ("scientific environment, infrastructure, workspace, administration and project support"), with no team-integration, onboarding, contractual, relocation or computing detail at the beneficiary (Section 3.2; Part B-2, Section 5.2).
- The risk register rates five of six risks identically and omits farm commitment, archive reuse rights, partner withdrawal and supervisor availability; no resource plan links remunerated engineering, field monitoring, UAV flights and open-access fees to the requested contributions; deliverable D1.3 is absent from the numbering (Section 3.1; Part A).

**Score 3 (0–5): 3.5** — **Weighting: 20 %**

| | |
|---|---|
| **Total score** | **72.20 / 100** |
| Overall threshold | 70 |
| Thresholds passed | yes (Excellence 3.6 ≥ 3; Impact 3.7 ≥ 3; Implementation 3.5 ≥ 3; total 72.20 ≥ 70) |

## 2. OTHER QUESTIONS

| Question | Opinion |
|---|---|
| Scope of the application | In scope: the application corresponds to the topic description (a postdoctoral researcher holding a PhD, international mobility from Bulgaria to Hungary, advanced interdisciplinary training, an inter-sectoral placement). |
| Exceptional funding | Not applicable: no third-country participant or international organisation is involved. |
| Use of human embryonic stem cells (hESC) | No. |
| Use of human embryos | No. |
| Activities excluded from funding | No: the proposal includes none of the excluded activities (Part A, declarations). |
| Exclusive focus on civil applications | Yes (Part A, declarations and security self-assessment). |

## 3. COMMENTS

**Overall comments**

The proposal presents a coherent, physiologically grounded fellowship with a falsifiable validation design, a mature exploitation strand and an internally consistent work plan, and it fits the purpose of the Postdoctoral Fellowships action. Its shortcomings lie in specification and evidence rather than in concept. The two steps that carry the central hypothesis, the hyperspectral-to-Sentinel-2 harmonisation and the prospective experimental design, are not detailed enough for their soundness to be assessed. The supervisory track record is not documented, and the researcher's CV does not meet the template's minimum content. The magnitude of the expected impact is not quantified, and the communication measures are generic. Critical dependencies rest on organisations without a formal role, on a compressed first quarter and on an unstated start-date assumption, and the secondment host is absent from the administrative forms. The proposal passes all thresholds with a total score of 72.20.

# Part I-bis — Diagnostic scoring sheet (not part of the official ESR)

## Lens scores and consensus

| Criterion | E1 (agronomy) | E2 (EO/ML) | E3 (MSCA generalist) | Spread | Consensus |
|---|---|---|---|---|---|
| Excellence | 3.7 | 3.5 | 3.7 | 0.2 | **3.6** |
| Impact | 3.8 | 3.8 | 3.6 | 0.2 | **3.7** |
| Implementation | 3.6 | 3.5 | 3.5 | 0.1 | **3.5** |
| Total (formula §3.3) | 73.20 | 71.80 | 71.80 | | **72.20** |

Total = (3.6 × 0.50 + 3.7 × 0.30 + 3.5 × 0.20) × 20 = (1.80 + 1.11 + 0.70) × 20 = **72.20**.

No criterion score diverged by more than 0.5 between lenses, so no score arbitration was needed. Three severity divergences were reconciled, as recorded below.

## Consensus notes (Step 3)

| Item | Lens positions | Resolution and deciding evidence |
|---|---|---|
| Aspect `exc-method` | E1 3.3, E2 3.2, E3 4.2 | The two domain specialists both found the harmonisation step and the experimental design under-specified at "major" severity; the generalist read them as minor. The specialists' evidence decided: the sealed text commits the conversion only "where technically possible" (p. 25) and dimensions nothing (p. 26). Consensus 3.4. |
| W9 crop-calendar dependency | E1 major; E2, E3 minor (the applicant chooses the start date) | Treated as major at the low end (−0.3): the plan itself states that "the crop calendar must place MS1 before season 1 and the second harvest by M20" (p. 32) and offers no assumption or contingency; O3 depends on both seasons landing. |
| W20 communication strategy | E3 major (template-explicit); E1, E2 minor | Treated as major at the low end (−0.35): the template's minimum content (main messages, tools, channels per target group) is absent, not merely thin. |
| W2 CV template content | E3 major; E1 minor | Treated as minor (−0.05) because the omissions do not hide eligibility-relevant facts (Part A carries the PhD date and residence data) and the career break is treated fairly; the inconsistency W4 is folded in at 0.0. |
| W11 effort profile | all lenses | Folded into W10 (F-17); not scored twice. |
| E1's phenology finding | E1 major | Folded into F-02 (design and stress reference under-specified). |
| E2's compute/EO-infrastructure finding | E2 minor | Folded into F-20 (hosting arrangements generic). |

## Per-aspect diagnostic sub-scores (targeting instrument, not official scores)

| Aspect | E1 | E2 | E3 | Consensus | One-line reason |
|---|---|---|---|---|---|
| exc-obj | 4.2 | 4.2 | 4.4 | **4.2** | Measurable, deliverable-bound, falsifiable objectives on a rich archive; state of the art thin (F-05). |
| exc-method | 3.3 | 3.2 | 4.2 | **3.4** | Validation architecture excellent; harmonisation, design, stress reference, model family and open-science specifics missing (F-01…F-04). |
| exc-supervision | 3.5 | 3.6 | 3.5 | **3.5** | Structured governance and concrete two-way transfer; no supervision record, sparse evidence, generic training (F-06, F-07). |
| exc-researcher | 3.8 | 3.5 | 3.5 | **3.6** | Physiology fit strong and transition documented; thin water-stress/EO record, undocumented prototype, CV template gaps (F-08…F-10). |
| imp-career | 4.0 | 3.9 | 4.3 | **4.1** | Credible trajectories, CDP and KPI; leadership/grant/network measures unspecified, cadence inconsistent (F-13, F-14). |
| imp-dissemination | 3.8 | 4.0 | 3.8 | **3.8** | Exploitation/IP strand strong and targets quantified; communication generic, release plan absent (F-12, F-15). |
| imp-magnitude | 3.3 | 3.3 | 3.3 | **3.3** | Honest bounding but no quantified reach, policy or work-programme link (F-11). |
| impl-workplan | 3.5 | 3.4 | 3.6 | **3.5** | Consistent, gated plan; front-loaded M1–M3, calendar dependency, undifferentiated risks, no resource plan, D1.3 gap (F-17, F-18, F-21…F-23). |
| impl-host | 3.5 | 3.4 | 3.4 | **3.4** | Capacity documented; four informal critical partners, generic hosting arrangements, secondment host absent from Part A (F-16, F-19, F-20). |

Reconstruction of the criterion scores from the findings register (score-impact estimates in Annex B): Excellence 5.0 − 1.40 = 3.6; Impact 5.0 − 1.30 = 3.7; Implementation 5.0 − 1.50 = 3.5. Caps (§4.1): each criterion carries at least one major finding, so none may exceed 4.4; no critical finding exists, so no criterion is capped at 3.0.

## Funding-zone verdict

| Zone (calibration rule 3) | Range | FIELDWISE |
|---|---|---|
| Fundable | ≥ 92 | 19.80 points away |
| Seal of Excellence | 85 – 91.9 | 12.80 points away |
| Above threshold, not competitive | 70 – 84.9 | **72.20 — here** |
| Below threshold | < 70 | 2.20 points above the threshold |

The proposal passes all thresholds but sits in the lower part of the "above threshold, not competitive" zone. Reaching Seal-of-Excellence territory requires roughly +0.6 on each criterion, which is the size of the P3 set in Part II (design and harmonisation specification, supervision record, magnitude figures, agreement status, start window). The fundable zone is not reachable by editorial work alone.

## Formal pre-check (Step 0)

| # | Check | Evidence (PDF page) | Status | Consequence |
|---|---|---|---|---|
| S0-1 | Part B-1 page count = 10 | pp. 24–33, footer "Part B - Page 1…10 of 10" | OK | none |
| S0-2 | B-1 typesetting (A4, ≥ 15 mm margins, Times New Roman ≥ 11 pt body, ≥ 8 pt other) | pp. 24–33: 595 × 842 pt; body TimesNewRomanPSMT 11.0 pt; footnotes 9.0 pt; margins L 15.0 / R 14.9 mm; body text ≥ 25 mm from top and ≥ 23 mm from bottom (template header/footer excluded); Gantt labels ≈ 8.5 pt — confirmed with PyMuPDF on 2026-09-08 | OK | none (0.1 mm right-margin rounding) |
| S0-3 | B-2 completeness §4–§9 + AI disclosure | §4 pp. 34–35; §5.1 p. 35; §5.2 pp. 35–37 (ATK, ELTE, AgroVIR, each ≈ ½ page); §6, §7, §8 (≈ ⅓ page), §9 n/a, AI disclosure p. 37 | OK | none |
| S0-4 | B-2 footers | pp. 34–37 "Part B - Page 3…6 of [Page limit]" — unreplaced placeholder, numbering starts at 3 | Check | cosmetic; not scored (W3) |
| S0-5 | Participants Part A vs B-2 table 5.1 | A p. 4: HUN-REN ATK (Coordinator), AgroVIR (Associated). B-2 p. 35: ATK (866599553), ELTE (999896468, AP for secondment), AgroVIR (891807622); "Only formal MSCA participating organisations are listed." | Risk | ELTE (12 of 24 months) absent from Part A; Part A ↔ B-2 inconsistent (W1). Operator to confirm the Part A requirement with the Guide for Applicants / NCP |
| S0-6 | Duration 24 + 6 | A p. 16 (24 Hungary; placement 6 Hungary); B-1 §3.1 p. 31; §2.3 p. 30 | OK | none |
| S0-7 | Placement host, country, length, position | AgroVIR Kft., Budaörs HU (A p. 12: research organisation No, non-profit No, academic No); 6 months at the end (M25–M30, pp. 27, 31); rationale p. 27 | OK | placement evaluable (WP pp. 27, 83) |
| S0-8 | Secondment vs 50 % cap | B-1 §3.1 p. 31: M1–M3, M10–M12, M16–M21 = 12 of 24 months; ELTE, Hungary | OK | equals the cap ("cannot exceed half"); same country permitted (WP p. 26) |
| S0-9 | Supervisor identity | A p. 7 Prof Tibor Janda, Head of Department; B-1 §1.3 p. 26; B-2 §5.1 p. 35, §5.2 p. 36 | OK | none |
| S0-10 | Researcher identity / PhD date | A p. 8: Rositsa Cholakova, doctorate 14/10/2020; B-2 p. 34: "PhD in Plant Physiology, Agricultural University of Plovdiv, 2020" | Check | CV lacks dd/mm/yyyy (template); no contradiction (W2) |
| S0-11 | PhD held at deadline | A p. 8 (14/10/2020) | OK | eligible on this point |
| S0-12 | Research experience ≤ 8 y FTE | 14/10/2020 → 09/09/2026 = 5.90 y elapsed; declared break 34 months (2021–2024) → ≈ 3.07 y | OK | below 8 y even without the deduction; the break is undated — to be double-checked by the applicant that documentation exists |
| S0-13 | Mobility rule (≤ 12 months in HU in the 36 months before 09/09/2026) | A p. 9: Hungary 09/03/2026–04/06/2026 = 87 days; Bulgaria otherwise (1,884 + 96 days); no gaps. CV lists MATE stays of 10 + 14 days (2025) not in the table (short stays) | OK | 87 (at most ≈ 111) days ≪ 365 |
| S0-14 | Residence table vs CV | ELTE traineeship "3 months (2026)" (p. 34) ↔ Hungary 09/03–04/06/2026 (p. 9) | OK | consistent |
| S0-15 | Budget arithmetic (A p. 16) | 0.787 × 6 350 × 24 = 119 938.8; 710 × 24 = 17 040; 660 × 24 = 15 840; 1 000 × 24 = 24 000; 650 × 24 = 15 600; placement rows analogous; grand total 240 523.5 | OK | "Management and indirect" Total cell prints 0 although the grand total includes 19 500 — portal rendering artefact; not assessed by the panel |
| S0-16 | Ethics table vs self-assessment | A p. 17: human participants No; personal data No; AI Yes (page "6"). A pp. 19–20 and B-2 §6 p. 37: voluntary feedback under informed consent; personal data under GDPR, coded/pseudonymised | Check | not scored; ethics screening may query the "No" answers (W7); AI page pointer ambiguous |
| S0-17 | Scope vs topic | Topic HORIZON-MSCA-2026-PF-01-01 (all domains); PhD holder, mobility BG → HU, inter-sectoral placement, interdisciplinary training | OK | in scope |
| S0-18 | Other questions (EF pp. 7–9) | in scope; no exceptional funding; hESC No; embryos No; excluded activities none (A p. 3); civil applications exclusive (A pp. 3, 22) | OK | none |
| S0-19 | Part A text fields | p. 8 "Plant physyology"; p. 15 "Bonafarm G", "navigation and excha"; p. 13 AgroVIR department block empty | Check | cosmetic (W6) |
| S0-20 | B-2 §5 inter-relationship declaration | none; CV shows co-authorship with MATE (Takács) and MVCRI (Ganeva) staff who appear in §3.2 | Check | template item; no scoring consequence |
| S0-21 | Resubmission question | A p. 2: No | OK | none |
| S0-22 | ERA Fellowships opt-in | A p. 23: Yes (host in Hungary) | OK | fallback funding line available |
| S0-23 | Employment | B-2 p. 36 "sole beneficiary and employing organisation"; full living allowance requested (A p. 16) | OK | employment contract implied, not stated in B-1 |

Eligibility is REA's decision. Every check above reports what the PDF supports; the two residual points to be double-checked by the applicant before the deadline are the documentation of the career break (S0-12) and the Part A registration of the secondment host (S0-5).

# Part II — Revision handout

Anchors follow §7.4 of the evaluation prompt and point at the sealed PDF (the only authoritative text until a docx reproduces it sentence for sentence). The update workflow verifies each anchor against its docx before editing. Page-budget deltas are **net** lines at the sealed typesetting (≈ 103 characters per line, 11 pt; the §3.2 and risk-table cells run ≈ 85–90 characters per line); an insertion's gross lines and its compensating cut are stated in the instruction. Observed slack in the sealed B-1: ≈ 5 lines at the end of Part B page 7 (PDF p. 30, before the forced start of Section 3) and ≈ 4 lines at the end of Part B page 10 (PDF p. 33); Part B page 9 (PDF p. 32) ends with the Gantt image and has no slack at all. The slack is a safety margin, not a budget: the minimum set nets 0 lines.

## II.0 Verdict and re-upload recommendation

**Verdict.** Total 72.20 (Excellence 3.6, Impact 3.7, Implementation 3.5): all thresholds passed, "above threshold, not competitive" zone, 12.80 points below Seal-of-Excellence territory and 19.80 below the fundable zone.

**Re-upload: recommended.** One P0 defect (secondment host absent from Part A, A-01) and five P1 defects (A-02 to A-06) exist, and the P2 set is editorial, uses only facts already in the PDF and nets 0 lines in Part B-1.

**Minimum set (deliverable with low regression risk):** A-01, A-02, A-03, A-04, A-05, A-06, A-07, A-08. Net Part B-1 delta: 0 lines. Projected scores after the minimum set, applied cleanly and nothing else changed: Excellence 3.9, Impact 3.8, Implementation 3.7 → **76.60**. After all P0–P2 actions (adds A-09, A-10, A-12, A-14, A-16, A-33): 3.9 / 4.0 / 3.8 → **78.20**. Both projections stay in the "above threshold, not competitive" zone.

**What moves the proposal further.** Only the P3 items (II.4) carry the weight to reach Seal-of-Excellence territory: design and harmonisation specification (A-20, A-21), supervision record (A-18, A-19), magnitude figures (A-13), agreement status (A-26) and the start window (A-11). If every owner answers by 12:00 on 2026-09-09 and every P3 action is applied, the indicative total is about 87–88. The fundable zone (≥ 92) is not reachable within the day; the realistic aim of the re-upload is to remove the P0/P1 defects, bank the editorial gains and secure the ERA-Fellowship and Seal fallbacks (Part A p. 23 opt-in is already "Yes").

**Sequence.**

1. Portal edits as soon as OD-E1 and OD-E14 are answered: A-01, A-06, A-32.
2. Part B-2 edits (no page limit): A-05, A-07, then A-19, A-29, A-30, A-31 as answers arrive.
3. Part B-1 P1 and P2 in this order: A-02, A-04, A-33, A-08, A-09, A-12, A-14, A-16 (Part B pages 1–7, then a page-count check), A-10 (pages 8–9, check that the Gantt still ends page 9), A-03 last because it touches the Gantt image (fallback: keep numbering).
4. Part B-1 P3 in order of expected gain as answers arrive: A-20, A-26, A-18, A-21, A-11, A-13, A-25, A-22, A-15, A-17, A-24, A-23, A-27, A-28, A-34. Region budgets: Part B pages 1–7 net ≤ +4 lines against ≈ 5 lines of slack; pages 8–9 net ≤ 0; page 10 net ≤ +2 against ≈ 4 lines of slack. A page-count check follows every region.
5. Export both parts to PDF, run II.5, upload both files, obtain the new acknowledgement of receipt.

**Point of no return.** Start the final upload no later than **15:30 Brussels time on 2026-09-09**; hold the new acknowledgement of receipt by 16:00. Owner answers arriving after 13:00 are not integrated. If anything in II.5 fails after 15:30, do not upload: the sealed version stands and remains a valid, above-threshold submission.

## II.1 Findings register

Severity per §4.2; the score-impact estimate is the consensus deduction attributed to the finding (Excellence deductions sum to −1.40, Impact to −1.30, Implementation to −1.50; formal findings carry no score). Full evidence quotes and anchors are in Annex B.

| ID | Criterion / aspect | Severity | Location | Weakness (as the evaluator states it) | Score impact | Watch-list |
|---|---|---|---|---|---|---|
| F-01 | excellence / `exc-method` | major | Part B1 §1.2, PDF p. 25 | The hyperspectral-to-Sentinel-2 harmonisation on which the frozen model depends is not specified: no spectral-response, correction, scaling or acceptance procedure, no plot dimensions or instrument, and the step is committed only 'where technically possible'; the frozen model therefore never sees a real Sentinel-2 predictor before deployment and the resulting domain shift is neither bounded nor estimated. | -0.30 | W12 |
| F-02 | excellence / `exc-method` | major | Part B1 §1.2, PDF p. 26 | The experimental and statistical design is not dimensioned: number and size of treatment areas and replicates, observations per campaign, campaigns per season and target sample sizes are absent; the physiological stress-reference rule and the acceptance thresholds are deferred to D1.2; crop growth stage is not considered; no pre-registration is committed. | -0.30 | W13 |
| F-03 | excellence / `exc-method` | minor | Part B1 §1.2, PDF p. 25 | The model family and the uncertainty-quantification and calibration methods are not named; no proximal spectral measurement is planned in the prospective seasons, so sensing-scale and environmental transfer cannot be separated as the transfer specification (D1.5) intends. | -0.05 | — |
| F-04 | excellence / `exc-method` | minor | Part B1 §1.2, PDF p. 26 | Open-science practices stop at principles: no repository, licence, preprint or public pre-registration is named, and code sharing is conditional on institutional, commercial and IP rights. | -0.10 | W15 |
| F-05 | excellence / `exc-obj` | minor | Part B1 §1.1, PDF p. 24 | The state of the art rests on four references, one of them a bare institutional web address, and does not engage with existing crop water-stress indicators or scheduling approaches for tomato (thermal or CWSI-type indices, sensor- or ET-based scheduling). | -0.10 | W14 |
| F-06 | excellence / `exc-supervision` | major | Part B1 §1.3, PDF p. 26 | The supervisors' qualifications are asserted rather than evidenced: no record of PhD or postdoctoral supervision and no named international collaborations are given; supporting outputs are one cited paper each for the modelling and Earth-observation supervisors, and the primary supervisor's outputs appear only in Part A. | -0.30 | W16 |
| F-07 | excellence / `exc-supervision` | minor | Part B1 §1.3, PDF p. 27 | Training is described by topic only, without named courses, providers or timing; teaching in Plovdiv is conditional; the arrangements for primary supervision during the first secondment block (M1-M3), which coincides with the protocol lock and model freeze, are not described. | -0.05 | W17 |
| F-08 | excellence / `exc-researcher` | minor | Part B1 §1.4, PDF p. 28 | The researcher's water-stress and Earth-observation outputs are limited to one 2025 proceedings paper (watermelon) and two manuscripts under review; the data-science training is unnamed, the Kleffmann employment is undated and the existing DrR prototype is not documented (repository, version, implemented functions). | -0.15 | W18 |
| F-09 | excellence / `exc-researcher` | minor | Part B2 §4, PDF p. 34 | The CV omits the template's minimum content: no dd/mm/yyyy dates for professional experience, education or the career break; the current position and the Kleffmann employment are undated; outputs carry no significance or open-access notes; invited presentations, funding and supervision/mentoring are not listed (or marked 'none'). | -0.05 | W2 |
| F-10 | excellence / `exc-researcher` | minor | Part B1 §1.4, PDF p. 28 | Section 1.4 states that the researcher holds an Environmental Engineering Master's degree, whereas the CV lists it as ongoing studies (2025-2026); held or in progress is undetermined. Scored within F-09. | +0.00 | W4 |
| F-11 | impact / `imp-magnitude` | major | Part B1 §2.3, PDF p. 30 | The magnitude of the contribution is not quantified: no irrigated processing-tomato or horticultural area, no number of growers or FMIS users, no size of the software partner's farmer network, no link to European water or agricultural policy frames or to the work programme's expected impacts; the 'European & societal' row is generic. | -0.50 | W21 |
| F-12 | impact / `imp-dissemination` | major | Part B1 §2.2, PDF p. 29 | The communication strategy lacks the main messages, tools, channels and timing per target group that the template requires; 'public-facing articles', a workshop and 'institutional and public-engagement activities' are listed without specification and 'reach indicators' are undefined. | -0.35 | W20 |
| F-13 | impact / `imp-career` | minor | Part B1 §2.1, PDF p. 28 | Leadership, grant writing and network building are listed as skills but not converted into measures (no planned grant application, network membership or mentoring role); teaching in Plovdiv is conditional ('where feasible', Section 1.3). | -0.20 | W19 |
| F-14 | impact / `imp-career` | minor | Part B1 §1.3, PDF p. 27 | The Career Development Plan review cadence is inconsistent: quarterly reviews in Sections 1.3 and 3.1 against reviews at months 3, 12, 21, 24 and 27 in the Section 2.1 table. | -0.10 | — |
| F-15 | impact / `imp-dissemination` | minor | Part B1 §2.2, PDF p. 30 | Data and software as impact vehicles are unspecific: 'monitoring of repository use after release' names no repository, and no release plan (licence, identifier) exists for the harmonised archive or the prospective dataset D2.1, whose reuse rights depend on undetermined archive terms; dissemination venues are Earth-observation and precision-agriculture forums only (EGU/ECPA), with no horticultural or irrigation-science forum. | -0.15 | — |
| F-16 | implementation / `impl-host` | major | Part B1 §3.2, PDF p. 33 | Four of the seven organisations in the capacity table (archive owner MATE, contractor Krumatic, the unnamed commercial farmer and MVCRI) hold no formal role although O1-O3 depend on the archive and the commercial field; access is 'documented before analysis', which describes a procedure; no existing agreement, letter or commitment is stated; field size, irrigation system and treatment layout are not described. | -0.40 | W24 |
| F-17 | implementation / `impl-workplan` | major | Part B1 §3.1, PDF p. 31 | Months 1-3 concentrate the audit and harmonisation of five archive seasons, protocol lock, pipeline construction, fitting and freeze, field-access agreements (T2.1), the IP/architecture agreement (T3.1), the CDP and the initial dissemination strategy, all during the first ELTE block; the feasibility of this concurrency and the 5.0 PM assigned to WP1 (about 3 PM before the freeze, 2 PM of synthesis after it) are not justified. | -0.40 | W10 |
| F-18 | implementation / `impl-workplan` | major | Part B1 §3.1, PDF p. 32 | Season 1 (T2.2, M4-M12) and season 2 (T2.3, M13-M20, second harvest by M20) fit the Hungarian processing-tomato calendar only for a start in a narrow window; the proposal states the constraint but gives no assumed start month and no contingency for a start outside the transplanting window; R2 presupposes a calendar-compatible start. | -0.30 | W9 |
| F-19 | implementation / `impl-host` | minor | Part A §2, PDF p. 4 | Part A lists two participating organisations while Part B-2 table 5.1 lists ELTE, which hosts twelve of the twenty-four months, as a formal participant with a PIC; the secondment arrangement is not anchored in the administrative forms. | -0.10 | W1 |
| F-20 | implementation / `impl-host` | minor | Part B1 §3.2, PDF p. 33 | Hosting arrangements are generic: no description of team integration, onboarding, contractual, HR or relocation support, and no computing or Earth-observation data infrastructure described at the beneficiary. | -0.10 | W23 |
| F-21 | implementation / `impl-workplan` | minor | Part B1 §3.1, PDF p. 32 | The risk register rates five of six risks identically (M/H) and omits farm commitment, archive reuse rights, AgroVIR withdrawal and supervisor or secondment availability. | -0.10 | W22 |
| F-22 | implementation / `impl-workplan` | minor | Part B1 §3.1, PDF p. 31 | No resource plan links remunerated software engineering, soil-water and meteorological monitoring, UAV acquisition, conferences and open-access fees to the requested contributions (research, training and networking contribution EUR 30,000 over 30 months) or to any other source. | -0.05 | W8 |
| F-23 | implementation / `impl-workplan` | minor | Part B1 §3.1, PDF p. 31 | Deliverable numbering has a gap: D1.1, D1.2, D1.4 and D1.5 exist; D1.3 appears nowhere in Sections 1.1, 3.1 or the Gantt. | -0.05 | W5 |
| F-24 | formal / `impl-host` | minor | Part A §4, PDF p. 17 | The ethics table answers 'No' to human participants and to personal-data processing, while the self-assessment (pp. 19-20) and Part B-2 Section 6 describe voluntary grower and user feedback under informed consent and personal data processed under GDPR with pseudonymisation. Not scored by the panel; ethics-screening consistency. | +0.00 | W7 |
| F-25 | formal / `impl-host` | minor | Part B2 §4-8, PDF p. 34 | The Part B-2 footer carries an unreplaced template placeholder and its numbering starts at 3. Cosmetic. | +0.00 | W3 |
| F-26 | formal / `impl-host` | minor | Part A §2, PDF p. 8 | Part A free-text fields contain a typo and two truncations at the field limit; the AgroVIR department block is empty. Cosmetic. | +0.00 | W6 |
| F-27 | formal / `impl-host` | minor | Part B2 §5.1, PDF p. 35 | Part B-2 Section 5 contains no declaration of inter-relationships between participating organisations and individuals, although the CV shows co-authorship with MATE (Takács) and MVCRI (Ganeva) staff named in Section 3.2. Template item; not scored. | +0.00 | — |
| F-28 | formal / `impl-host` | minor | Part A §4, PDF p. 18 | The page pointer '6' for the AI item does not match where AI is discussed (Part A pp. 19-20; Part B-1 p. 26, i.e. Part B page 3); Part B-2 Section 6 does not mention AI. Not scored. | +0.00 | — |
| F-29 | formal / `exc-researcher` | minor | Part B2 §4, PDF p. 35 | The career break is stated in months and years only; eligibility on research experience holds even without the deduction (5.90 years elapsed since 14/10/2020), but the applicant is to double-check that the break can be documented if requested. Not scored (fair treatment of the break); the CV format aspect is scored in F-09. | +0.00 | — |

## II.2 Revision actions (ordered by priority, then expected gain)

Every action carries the fields of §7.2 in Annex B (instruction, exact proposed text, compensating cut, owner, fallback, ripple, verification). The table below is the working view.

| ID | Prio | Target | Class | Findings | Owner | Net Δ B-1 lines | Effort / risk | Expected gain |
|---|---|---|---|---|---|---|---|---|
| A-01 | P0 | PART_A_PORTAL | portal_admin | F-19 | operator | n/a | S / low | +0.1 on Implementation |
| A-05 | P1 | PART_B2_DOCX | needs_fact | F-09, F-29 | fellow | n/a | M / low | +0.1 on Excellence |
| A-03 | P1 | PART_B1_DOCX | editorial | F-23 | operator | 0 | M / medium | +0.05 on Implementation |
| A-04 | P1 | PART_B1_DOCX | editorial | F-14 | operator | 0 | S / low | +0.05 on Impact |
| A-02 | P1 | PART_B1_DOCX | needs_fact | F-10 | fellow | 0 | S / low | +0.0 (consistency; removes an inconsistency the panel reads as carelessness) |
| A-06 | P1 | PART_A_PORTAL | needs_decision | F-24, F-28 | operator | n/a | S / low | +0.0 (not scored; ethics-screening consistency) |
| A-07 | P2 | PART_B2_DOCX | editorial | F-06 | operator | n/a | S / low | +0.1 on Excellence |
| A-08 | P2 | PART_B1_DOCX | editorial | F-08 | operator | 0 | S / low | +0.1 on Excellence |
| A-10 | P2 | PART_B1_DOCX | editorial | F-21, F-16 | operator | 0 | S / medium | +0.1 on Implementation |
| A-12 | P2 | PART_B1_DOCX | editorial | F-11 | operator | 0 | S / low | +0.1 on Impact |
| A-14 | P2 | PART_B1_DOCX | editorial | F-12 | operator | 0 | S / low | +0.1 on Impact |
| A-09 | P2 | PART_B1_DOCX | editorial | F-17 | operator | 0 | S / low | +0.05 on Implementation |
| A-16 | P2 | PART_B1_DOCX | editorial | F-13 | operator | 0 | S / low | +0.05 on Impact |
| A-33 | P2 | PART_B1_DOCX | editorial | F-14 | operator | 0 | S / low | +0.0 (consistency guard) |
| A-13 | P3 | PART_B1_DOCX | needs_fact | F-11 | partner:AgroVIR | 0 | M / low | +0.3 on Impact |
| A-20 | P3 | PART_B1_DOCX | needs_fact | F-01, F-03 | fellow | 0 | M / medium | +0.3 on Excellence |
| A-26 | P3 | PART_B1_DOCX | needs_fact | F-16 | host | 1 | M / low | +0.3 on Implementation |
| A-11 | P3 | PART_B1_DOCX | needs_decision | F-18 | fellow | 0 | M / medium | +0.2 on Implementation |
| A-18 | P3 | PART_B1_DOCX | needs_fact | F-06 | supervisor | 0 | S / low | +0.2 on Excellence |
| A-21 | P3 | PART_B1_DOCX | needs_fact | F-02 | fellow | -1 | M / medium | +0.2 on Excellence |
| A-15 | P3 | PART_B1_DOCX | needs_fact | F-12 | host | -1 | S / low | +0.1 on Impact |
| A-17 | P3 | PART_B1_DOCX | needs_decision | F-13 | fellow | 0 | S / low | +0.1 on Impact |
| A-19 | P3 | PART_B2_DOCX | needs_fact | F-06 | supervisor | n/a | S / low | +0.1 on Excellence (with A-18) |
| A-22 | P3 | PART_B1_DOCX | needs_decision | F-04, F-15 | fellow | 0 | S / low | +0.1 on Excellence |
| A-23 | P3 | PART_B1_DOCX | needs_fact | F-05 | fellow | 3 | M / medium | +0.1 on Excellence |
| A-24 | P3 | PART_B1_DOCX | needs_fact | F-07 | supervisor | 2 | M / medium | +0.1 on Excellence |
| A-25 | P3 | PART_B1_DOCX | needs_fact | F-20 | host | -1 | M / low | +0.1 on Implementation |
| A-34 | P3 | PART_B1_DOCX | needs_decision | F-17 | fellow | 0 | L / high | +0.1 on Implementation |
| A-27 | P3 | PART_B1_DOCX | needs_fact | F-22 | host | 1 | S / low | +0.05 on Implementation |
| A-28 | P3 | PART_B1_DOCX | needs_decision | F-15 | fellow | 0 | S / low | +0.05 on Impact |
| A-29 | P3 | PART_B2_DOCX | needs_fact | F-08 | fellow | n/a | S / low | +0.05 on Excellence |
| A-30 | P4 | PART_B2_DOCX | editorial | F-25 | operator | n/a | S / low | +0.0 (cosmetic) |
| A-31 | P4 | PART_B2_DOCX | needs_fact | F-27 | fellow | n/a | S / low | +0.0 (template completeness) |
| A-32 | P4 | PART_A_PORTAL | portal_admin | F-26 | operator | n/a | S / low | +0.0 (cosmetic) |

### Action sheets

#### A-01 · P0 · PART_A_PORTAL · portal_admin · findings F-19
- **Anchor:** A p.4 2 - Participants > List of participating organisations (p. 4)
- **Instruction:** In the submission wizard add Eötvös Loránd University (ELTE, PIC 999896468) as an associated partner (associated partner for secondment), so that Part A lists the same three organisations as Part B-2 table 5.1. Do this only after the operator has confirmed with the Guide for Applicants / NCP that secondment hosts are registered in Part A for European Fellowships.
- **Proposed text:** null
- **Net page-budget delta (B-1 lines):** n/a (no page limit) · **Compensating cut:** none needed
- **Owner:** operator · **Fallback:** If the Guide does not require the secondment host in Part A, leave Part A unchanged; Part B-2 table 5.1 already states the role and PIC.
- **Ripple:** Part A participant list and any participant-specific pages generated by the wizard; Part B-2 §5.1 unchanged (already lists ELTE)
- **Verification:** Regenerated Part A p. 4 lists 3 organisations (ATK Coordinator, ELTE Associated, AgroVIR Associated); PIC 999896468 appears in Part A; Part B-2 §5.1 unchanged.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.1 on Implementation

#### A-05 · P1 · PART_B2_DOCX · needs_fact · findings F-09, F-29
- **Anchor:** B2 §4 list "Education and research qualifications" and list "Professional experience" (p. 34); ¶"Career break" (p. 35)
- **Instruction:** Give every education and professional-experience entry full consecutive dates (dd/mm/yyyy–dd/mm/yyyy), consistent with Part A: PhD award 14/10/2020 (Part A p. 8); date the MVCRI position, the Kleffmann employment and the assistant professorship; date the career break; add a one-clause significance note and the open-access status to each listed output; add the template categories that are absent with an entry or 'none' (invited presentations, conference organisation, prizes/awards, funding, supervising/mentoring).
- **Proposed text:** • PhD in Plant Physiology, Agricultural University of Plovdiv, awarded 14/10/2020. … • Chief Assistant Professor, MVCRI, Plovdiv, [OWNER-CONFIRM: dd/mm/yyyy]–present … • Assistant Professor …, Agricultural University of Plovdiv, [OWNER-CONFIRM: dd/mm/yyyy]–[OWNER-CONFIRM: dd/mm/yyyy] … • Agricultural data work, Kleffmann Group Bulgaria, [OWNER-CONFIRM: dd/mm/yyyy]–[OWNER-CONFIRM: dd/mm/yyyy] … Career break: full-time parenting, [OWNER-CONFIRM: dd/mm/yyyy]–[OWNER-CONFIRM: dd/mm/yyyy] (34 months). … Invited presentations: [OWNER-CONFIRM: list | none]. Funding: [OWNER-CONFIRM: list | none]. Supervising/mentoring: [OWNER-CONFIRM: list | none]. Each output: [OWNER-CONFIRM: one-clause significance]; open access: [OWNER-CONFIRM: yes/no].
- **Net page-budget delta (B-1 lines):** n/a (no page limit) · **Compensating cut:** none needed
- **Owner:** fellow · **Fallback:** Insert only the PhD award date from Part A (14/10/2020) and the fixed 34-month duration; leave the other entries as sealed.
- **Ripple:** Part A p. 9 residence table must remain consistent with any dated stay abroad; A-02 (MSc status)
- **Verification:** Every bullet under Education and Professional experience contains two dd/mm/yyyy dates (or one date and 'present'); the career-break line contains two dd/mm/yyyy dates; every publication entry ends with an open-access flag; the three added categories are present.
- **Effort:** M · **Regression risk:** low · **Expected gain:** +0.1 on Excellence

#### A-03 · P1 · PART_B1_DOCX · editorial · findings F-23
- **Anchor:** B1 §3.1 ¶"D1.1 archive/QC map (M2)" s1 (p. 31)
- **Instruction:** Renumber D1.4 → D1.3 and D1.5 → D1.4 everywhere: §1.1 O2 '(D1.4)' (p. 24), §1.2 'D1.4 includes a model card' (p. 26), §2.1 table row 'ATK scientific and modelling training' cell Evidence 'D1.4' (p. 28), §2.2 table row 'Dissemination' cell Evidence 'D1.4 M3' (p. 29), §3.1 WP1 deliverable line (p. 31), Gantt labels '1.2/4' → '1.2/3' and '1.5' → '1.4' (p. 32).
- **Proposed text:** D1.1 archive/QC map (M2); D1.2 protocol and D1.3 model/card (M3); D1.4 transfer specification (M21).
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** none needed
- **Owner:** operator · **Fallback:** If the Gantt image cannot be re-rendered, leave the numbering unchanged everywhere (a consistent gap is better than a text/Gantt mismatch).
- **Ripple:** Gantt image p. 32 (re-render); §1.1 p. 24; §1.2 p. 26; §2.1 table p. 28; §2.2 table p. 29
- **Verification:** grep -c 'D1.5' in B-1 = 0; grep -c 'D1.3' ≥ 4; Gantt row 'Deliverables B' shows '1.2/3; 5.1' at M3 and '1.4; 2.2' at M21; B-1 page count = 10.
- **Effort:** M · **Regression risk:** medium · **Expected gain:** +0.05 on Implementation

#### A-04 · P1 · PART_B1_DOCX · editorial · findings F-14
- **Anchor:** B1 §2.1 table "Measure" row "Career Development Plan" cell Evidence (p. 28)
- **Instruction:** Harmonise the review cadence with §1.3 and T5.1 by stating both facts already in the PDF in the Evidence cell; leave §1.3 and §3.1 unchanged.
- **Proposed text:** D5.1 (M3); quarterly reviews; gate reviews M12/M21/M24/M27; K11
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** none needed
- **Owner:** operator · **Fallback:** n/a (editorial)
- **Ripple:** none
- **Verification:** grep 'quarterly' in B-1 returns §1.3, §2.1 table and T5.1; the row height is governed by the middle cell (4 lines), so the table does not grow; B-1 page count = 10.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.05 on Impact

#### A-02 · P1 · PART_B1_DOCX · needs_fact · findings F-10
- **Anchor:** B1 §1.4 ¶"A profile matched to the" s9 (p. 28)
- **Instruction:** Replace the clause 'is holding Environmental Engineering Master’s degree' with the confirmed status, worded identically to the CV.
- **Proposed text:** [OWNER-CONFIRM: holds an MSc in Environmental Engineering (awarded dd/mm/yyyy) | is completing an Environmental Engineering MSc (2025–2026)]
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** none needed
- **Owner:** fellow · **Fallback:** Use the CV wording (studies in progress, 2025–2026), the weaker of the two statements already in the PDF.
- **Ripple:** B2 §4 list "Education and research qualifications" bullet 4 (p. 34): same status and dates (dd/mm/yyyy if awarded)
- **Verification:** grep 'Environmental Engineering' in B-1 and B-2 returns the same status in both; 'is holding' count = 0; §1.4 paragraph line count unchanged.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.0 (consistency; removes an inconsistency the panel reads as carelessness)

#### A-06 · P1 · PART_A_PORTAL · needs_decision · findings F-24, F-28
- **Anchor:** A p.17 4 - Ethics & security > Ethics Issues Table > 2. Humans and 4. Personal data (p. 17); A p.18 > 8. Artificial intelligence > Page (p. 18)
- **Instruction:** Decide whether the voluntary grower/advisor/software-user feedback (self-assessment pp. 19–20, Part B-2 §6) constitutes involvement of human participants and processing of personal data. If yes, set both answers to Yes and enter the self-assessment page; if no, leave the table and keep the self-assessment. In both cases replace the AI page pointer '6' with the Part B-1 page where AI is discussed (Part B page 3) or with the self-assessment page.
- **Proposed text:** [OWNER-CONFIRM: Humans = Yes/No; Personal data = Yes/No; AI page pointer = 3 (Part B-1) | self-assessment page]
- **Net page-budget delta (B-1 lines):** n/a (no page limit) · **Compensating cut:** none needed
- **Owner:** operator · **Fallback:** Leave the table as sealed; the self-assessment already describes consent, data minimisation and GDPR compliance, and the panel does not score the ethics table.
- **Ripple:** Ethics self-assessment text unchanged; Part B-2 §6 unchanged
- **Verification:** Ethics table answers match the self-assessment narrative; the AI page pointer resolves to a page that mentions AI.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.0 (not scored; ethics-screening consistency)

#### A-07 · P2 · PART_B2_DOCX · editorial · findings F-06
- **Anchor:** B2 §5.2 table (Beneficiary) row "Role and profile of supervisor" (p. 36)
- **Instruction:** Append to the supervisor-profile cell the supervisory team's outputs already listed in Part A p. 11, with the same descriptors.
- **Proposed text:** Recent outputs of the supervisory team: Janda et al., 2025, Scientific Reports (water-deficit physiology; chlorophyll fluorescence, stomatal conductance, SPAD); Szalai et al., 2025, Plant Physiology and Biochemistry (whole-plant abiotic-stress physiology); Li et al., 2026, Nature Plants (plant signalling and stress-response physiology); Hollós et al., 2026, Geoscientific Model Development (machine learning, leave-one-year-out validation, independent testing, SHAP); Birinyi et al., 2024, Remote Sensing (EO-based maize condition mapping).
- **Net page-budget delta (B-1 lines):** n/a (no page limit) · **Compensating cut:** none needed
- **Owner:** operator · **Fallback:** n/a (editorial; facts in Part A p. 11)
- **Ripple:** B1 §1.3 unchanged unless A-18 is applied
- **Verification:** grep 'Scientific Reports' and 'Geoscientific Model Development' in B-2 §5.2 each return 1; descriptors identical to Part A p. 11.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.1 on Excellence

#### A-08 · P2 · PART_B1_DOCX · editorial · findings F-08
- **Anchor:** B1 §1.4 ¶"A profile matched to the" s7 (p. 28), after '…satellite/UAV data.'
- **Instruction:** Insert one sentence naming the two under-review tomato water-stress manuscripts and the MATE training stays already listed in Part B-2 §4 (+3 lines). Pay for it with CUT-1: delete §1.1 ¶"Pertinence. Three linked scientific" s4–s5 ('These objectives also advance the fellow … inter-sectoral profile.', −3 lines), which duplicates §2.1.
- **Proposed text:** Two manuscripts under review document her recent water-stress and Earth-observation work: evapotranspiration estimation in tomato fields from multispectral and thermal UAV data, and proximal hyperspectral signatures of water stress in processing tomato validated against physiology and soil water, co-authored with the MATE and MVCRI colleagues named in Section 3.2 (Part B-2, Section 4).
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** B1 §1.1 ¶"Pertinence. Three linked scientific" s4–s5 (p. 24): 'These objectives also advance the fellow … inter-sectoral profile.' (−3 lines)
- **Owner:** operator · **Fallback:** n/a (editorial; facts in Part B-2 pp. 34–35)
- **Ripple:** §1.1 'Pertinence' paragraph shrinks from 9 to 6 lines; pages 24–28 reflow by −3/+3 lines
- **Verification:** grep 'Proximal Hyperspectral Signatures' in B-1 §1.4 (case-insensitive) = 1; grep 'These objectives also advance the fellow' = 0; Part B page 5 still starts with '…based stress assessment' or later; B-1 page count = 10.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.1 on Excellence

#### A-10 · P2 · PART_B1_DOCX · editorial · findings F-21, F-16
- **Anchor:** B1 §3.1 table "Risk; likelihood/impact" after row "R6" (p. 32)
- **Instruction:** Add a seventh risk row for partner and access failure, built only from mitigations already in the plan (R2 backup site by M3; T5.2 access rules from M1; T3.1 AgroVIR requirements M1–M3; MS4 placement-scope decision) (+3 lines). Pay for it with CUT-5 (delete 'Required administrative outputs: … two years later.' at the end of the WP5 paragraph, pp. 31–32, −2 lines) and CUT-14 (delete §3.1 ¶"The fellow leads the scientific work" s2 'Five WPs connect … career development.', −1 line). Do not touch the Gantt.
- **Proposed text:** R7 | WP2–4 | M/H — Partner or access failure (producer field, MATE archive reuse, AgroVIR requirements/placement): backup site and access documentation agreed by M3 (T2.1, T5.2); AgroVIR requirements reviews from M1 (T3.1); placement scope re-confirmed at MS4. Owner: fellow/ATK.
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** B1 §3.1 ¶"D5.1 CDP (M3); D5.2 DMP" last sentence 'Required administrative outputs: … two years later.' (pp. 31–32, −2 lines) + B1 §3.1 ¶"The fellow leads the scientific work" s2 (p. 31, −1 line)
- **Owner:** operator · **Fallback:** n/a (editorial; all mitigations already in the PDF)
- **Ripple:** Part B page 9 must still end with the Gantt; if the Gantt moves to page 10, revert CUT-14 first, then the row
- **Verification:** Risk table has 7 rows; grep 'Required administrative outputs' = 0; the Gantt is still on Part B page 9; B-1 page count = 10.
- **Effort:** S · **Regression risk:** medium · **Expected gain:** +0.1 on Implementation

#### A-12 · P2 · PART_B1_DOCX · editorial · findings F-11
- **Anchor:** B1 §2.3 table "Dimension" row "European & societal" (p. 30)
- **Instruction:** Rewrite the row so that it names the work-programme expected outcomes and impacts the action serves, using only facts in the PDF (Bulgarian fellow, Hungarian academic host, university secondment host, non-academic FMIS company placement, MVCRI return route, open-science outputs) (+1 line). Pay for it with CUT-8: delete §2.1 ¶"By completion, the fellow will" s3 ('The 12-month ELTE secondment adds … non-academic experience.', −1 line), which duplicates the table above it.
- **Proposed text:** Contribution: a Bulgarian researcher trained in Hungary across an academic host, a university secondment host and a non-academic FMIS company, with a defined return route through MVCRI. Magnitude and importance: brain circulation and knowledge transfer across the ERA between two Member States; inter-sectoral mobility into the non-academic sector; open-science outputs (pre-specified protocol, model card, FAIR data, at least two open-access papers); a reusable transfer methodology applicable to further irrigated crops through MVCRI.
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** B1 §2.1 ¶"By completion, the fellow will" s3 (p. 29): 'The 12-month ELTE secondment adds … non-academic experience.' (−1 line)
- **Owner:** operator · **Fallback:** n/a (editorial; work-programme terms and PDF facts only)
- **Ripple:** §2.3 table row height grows by ~1 line; Part B page 7 has ~5 lines of slack
- **Verification:** grep 'brain circulation' in B-1 §2.3 = 1; grep 'The 12-month ELTE secondment adds' = 0; B-1 page count = 10.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.1 on Impact

#### A-14 · P2 · PART_B1_DOCX · editorial · findings F-12
- **Anchor:** B1 §2.2 table "Strand" row "Communication" cell "Measures and outputs" (p. 29)
- **Instruction:** Restructure the cell by target group with main message, tool and timing, using only facts in the PDF (messages from §1.1–§2.3; the end-user workshop by M30 from K13; demonstrations during the M25–M30 placement; T5.3 strategy at M3) (+2 lines). Pay for it with CUT-13: delete §2.1 ¶"FIELDWISE is designed to consolidate" s2 ('The fellowship builds on competences … inter-sectoral exploitation.', −2 lines), which duplicates §1.4.
- **Proposed text:** Growers and advisors (HU/BG) — message: when and where water stress needs attention, shown as stress probability with uncertainty, never beyond measured evidence; tools: practitioner demonstrations of the DrR outputs during the AgroVIR placement (M25–M30), one farmer/end-user workshop by M30 (K13), practitioner articles. Public — message: physiologically validated, open-science irrigation decision support; tools: institutional communication of HUN-REN ATK and ELTE, public-facing articles. Strategy documented at M3 (T5.3); reach indicators reported in D5.3.
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** B1 §2.1 ¶"FIELDWISE is designed to consolidate" s2 (p. 28): 'The fellowship builds on competences … inter-sectoral exploitation.' (−2 lines)
- **Owner:** operator · **Fallback:** n/a (editorial; facts in the PDF)
- **Ripple:** §2.1 opening paragraph shrinks from 6 to 4 lines; the §2.1 table may re-split across Part B pages 5–6 — check row integrity
- **Verification:** Communication cell contains 'M25–M30' and 'by M30 (K13)'; grep 'The fellowship builds on competences' = 0; §2.1 table rows intact; B-1 page count = 10.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.1 on Impact

#### A-09 · P2 · PART_B1_DOCX · editorial · findings F-17
- **Anchor:** B1 §1.1 ¶"Realistically achievable. FIELDWISE combines" s2 (p. 25), after '…support feasibility.'
- **Instruction:** Insert one sentence establishing that familiarity with the MATE archive predates the action (facts in Part B-2 §4), which addresses the credibility of the M1–M3 audit-to-freeze sequence (+3 lines). Pay for it with CUT-7: delete §2.3 ¶"Impact is measured through project-controlled" s3 ('Delivery is tracked through K1–K14, … implementation.', −3 lines), which duplicates §3.1.
- **Proposed text:** Familiarity with the archive predates the action: the fellow completed a COST PANGEOS Short-Term Scientific Mission and Erasmus+ RGB/hyperspectral training at MATE in 2025 and co-authored, with Dr Takács, a manuscript under review on proximal hyperspectral signatures of water stress in processing tomato (Part B-2, Section 4).
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** B1 §2.3 ¶"Impact is measured through project-controlled" s3 (p. 30): 'Delivery is tracked through K1–K14, … implementation.' (−3 lines)
- **Owner:** operator · **Fallback:** n/a (editorial; facts in Part B-2 pp. 34–35)
- **Ripple:** §2.3 closing paragraph shrinks by 3 lines; Part B page 7 gains slack
- **Verification:** grep 'Familiarity with the archive predates' in B-1 = 1; grep 'Delivery is tracked through K1' = 0; §3 still starts at the top of Part B page 8; B-1 page count = 10.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.05 on Implementation

#### A-16 · P2 · PART_B1_DOCX · editorial · findings F-13
- **Anchor:** B1 §2.1 table "Measure" row "Scientific visibility and leadership" cell "Skills and employability mechanism" (p. 29)
- **Instruction:** Name the network already in the PDF (COST Action CA22136 PANGEOS, Part B-2 §4) and the teaching venues (MATE; Agricultural University–Plovdiv) as the concrete network and teaching measures (+1 line). Pay for it with CUT-12 if not already used by A-13; otherwise with CUT-20 (delete §1.3 ¶"Two-way transfer of knowledge. FIELDWISE" s1, −1 line).
- **Proposed text:** Co-authored publications, conference presentations, seminars and guest lectures at MATE and the Agricultural University–Plovdiv, and continued participation in COST Action CA22136 PANGEOS strengthen international visibility, communication, network building and future supervision capacity.
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** B1 §1.3 ¶"Two-way transfer of knowledge. FIELDWISE" s1 (p. 27): 'FIELDWISE connects internationally recognised … expertise.' (−1 line)
- **Owner:** operator · **Fallback:** n/a (editorial; PANGEOS and the teaching venues are in the PDF)
- **Ripple:** §1.3 'Two-way transfer' paragraph loses its opening sentence; the paragraph still names both directions of transfer
- **Verification:** grep 'PANGEOS' in B-1 §2.1 = 1; grep 'FIELDWISE connects internationally recognised' = 0; B-1 page count = 10.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.05 on Impact

#### A-33 · P2 · PART_B1_DOCX · editorial · findings F-14
- **Anchor:** B1 §3.1 ¶"Lead: fellow/ATK; supervisors and host" T5.1 (p. 31)
- **Instruction:** Keep 'quarterly reviews' in T5.1 (consistent with §1.3); no text change unless CUT-15 (A-11) condenses the paragraph, in which case retain the word 'quarterly'.
- **Proposed text:** T5.1: CDP, quarterly reviews, technical/transferable skills, knowledge exchange.
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** none needed
- **Owner:** operator · **Fallback:** n/a
- **Ripple:** A-04; A-11 (CUT-15)
- **Verification:** grep 'quarterly' in B-1 §3.1 = 1.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.0 (consistency guard)

#### A-13 · P3 · PART_B1_DOCX · needs_fact · findings F-11
- **Anchor:** B1 §2.3 table "Dimension" row "Agricultural & environmental" cell "Magnitude and importance" (p. 30)
- **Instruction:** Append a quantified addressable target group to the cell (+2 lines). Pay for it with CUT-11 (delete §1.3 ¶"Rationale and added value of the" s6 'Commercially sensitive evaluation uses protected, coded or appropriately aggregated data.', −1) and CUT-12 (condense §1.2 ¶"Stage 3 (WP3–WP4) operationalises only" to one sentence, −1).
- **Proposed text:** The addressable group comprises [OWNER-CONFIRM: n] farms and [OWNER-CONFIRM: ha] under AgroVIR farm-management software and [OWNER-CONFIRM: ha] of irrigated processing tomato in Hungary and Bulgaria [OWNER-CONFIRM: source]; the two validation seasons cover [OWNER-CONFIRM: ha] of it.
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** B1 §1.3 ¶"Rationale and added value of the" s6 (p. 27, −1) + B1 §1.2 ¶"Stage 3 (WP3–WP4) operationalises only" condensed to one sentence (p. 26, −1)
- **Owner:** partner:AgroVIR · **Fallback:** Apply A-12 only; leave the cell as sealed (no invented figures).
- **Ripple:** Part A abstract ('within its network of farmers') stays consistent; A-14 communication reach figures use the same numbers
- **Verification:** The cell contains no '[OWNER-CONFIRM' after the owner answers and at least one numeral with a unit (farms or ha); B-1 page count = 10.
- **Effort:** M · **Regression risk:** low · **Expected gain:** +0.3 on Impact

#### A-20 · P3 · PART_B1_DOCX · needs_fact · findings F-01, F-03
- **Anchor:** B1 §1.2 ¶"Stage 1 (WP1) harmonises the" s2–s3 and s5 (p. 25)
- **Instruction:** Replace the hedged harmonisation sentence with the method the fellow and Prof. Jung commit to, and name the model family, uncertainty and calibration method in s5 (+4 lines). Pay for it with CUT-18 (delete §1.1 ¶"Realistically achievable. FIELDWISE combines" s3 'Previous MATE research established … alone.', −2, already evidenced by footnotes 3–4), CUT-9 (compress the partner list in §1.2 ¶"Integration of methods and disciplines." s2 to the four role assignments, −1) and CUT-22 (delete §1.2 ¶"Overall methodology: concepts, models and" s2 'Operational predictors comprise spectral, soil-water and meteorological variables.', −1).
- **Proposed text:** Historical plots ([OWNER-CONFIRM: a × b m]) are too small for plot-level Sentinel-2 retrieval; handheld hyperspectral reflectance ([OWNER-CONFIRM: instrument, spectral range]) is therefore converted into Sentinel-2 band-equivalent reflectance and indices by [OWNER-CONFIRM: method, e.g. convolution with the Sentinel-2 MSI spectral response functions] after [OWNER-CONFIRM: correction applied], and a predictor is retained only where [OWNER-CONFIRM: acceptance test] holds, before model freeze. … Blocked, leakage-safe unseen-year validation tests temporal transfer; a [OWNER-CONFIRM: model family, e.g. regularised logistic model] with [OWNER-CONFIRM: uncertainty method] and [OWNER-CONFIRM: calibration method] is compared with a [OWNER-CONFIRM: nonlinear benchmark, e.g. gradient-boosted trees].
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** B1 §1.1 ¶"Realistically achievable. FIELDWISE combines" s3 (p. 25, −2) + B1 §1.2 ¶"Integration of methods and disciplines." s2 compressed (p. 26, −1) + B1 §1.2 ¶"Overall methodology: concepts, models and" s2 (p. 25, −1)
- **Owner:** fellow · **Fallback:** No change; the sealed sentences stand (no invented method).
- **Ripple:** R4 (clouds/mixed pixels) and §3.2 ELTE row stay consistent with the named method; D1.2 protocol description in §1.1 O1 unchanged
- **Verification:** grep 'where technically possible' in B-1 = 0; the two sentences contain no '[OWNER-CONFIRM' after the owner answers; grep 'Previous MATE research established' = 0; B-1 page count = 10.
- **Effort:** M · **Regression risk:** medium · **Expected gain:** +0.3 on Excellence

#### A-26 · P3 · PART_B1_DOCX · needs_fact · findings F-16
- **Anchor:** B1 §3.2 table "Organisation" rows "MATE", "Krumatic EOOD", "Commercial farmer/producer" (p. 33)
- **Instruction:** State the status of each informal arrangement (agreement signed, letter held, producer identified) with dates (+3 lines). Pay for it with CUT-4 (condense the MVCRI row to three lines, −2) and the ≈4 lines of slack at the end of Part B page 10.
- **Proposed text:** MATE: data-access and reuse agreement [OWNER-CONFIRM: signed dd/mm/yyyy | to be signed before M1]. Krumatic: development agreement [OWNER-CONFIRM: signed dd/mm/yyyy | draft agreed], covering deliverables, source-code delivery, ownership, licensing and access. Producer: [OWNER-CONFIRM: named farm/region, field of x ha with drip/sprinkler irrigation], commitment letter [OWNER-CONFIRM: held dd/mm/yyyy]; backup site [OWNER-CONFIRM: identified].
- **Net page-budget delta (B-1 lines):** 1 · **Compensating cut:** B1 §3.2 table row "MVCRI, Plovdiv" condensed to 3 lines (p. 33, −2) + Part B page 10 slack (≈4 lines) — mandatory page-count check
- **Owner:** host · **Fallback:** Apply A-10 (risk row) only; leave the rows as sealed (no invented agreements).
- **Ripple:** R7 (A-10) wording stays consistent; Part B-2 §5.1 note on informal organisations may add the same status
- **Verification:** Each of the three rows contains 'agreement' or 'commitment' with a date or status and no '[OWNER-CONFIRM'; B-1 page count = 10.
- **Effort:** M · **Regression risk:** low · **Expected gain:** +0.3 on Implementation

#### A-11 · P3 · PART_B1_DOCX · needs_decision · findings F-18
- **Anchor:** B1 §3.1 ¶"Critical path: MS1 model freeze" s3 (p. 32)
- **Instruction:** Extend the crop-calendar sentence with the assumed start window and the slipped-start contingency decided by the fellow and the host (+2 lines). Pay for it with CUT-15 (condense the WP5 'Lead:' paragraph on p. 31 to three lines, −1) and CUT-16 (condense K5 in the WP2 deliverable paragraph on p. 31, −1).
- **Proposed text:** The crop calendar must place MS1 before season 1 and the second harvest by M20; the plan assumes a start between [OWNER-CONFIRM: month] and [OWNER-CONFIRM: month], fixed at grant signature, and a start outside this window moves season 1 to the next transplanting window while T1.4 and T3.2 absorb the interval.
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** B1 §3.1 ¶"Lead: fellow/ATK; supervisors and host" (p. 31, condense to 3 lines, −1) + B1 §3.1 ¶"D2.1 dataset/prediction log (M20)" K5 clause 'all scheduled observation opportunities accounted for, with' (p. 31, −1)
- **Owner:** fellow · **Fallback:** No change; the sealed sentence stands and the weakness remains.
- **Ripple:** Risk row R2 wording ('Switch comparable site before the crop window') stays consistent; Part B page 9 must still end with the Gantt
- **Verification:** grep 'the plan assumes a start between' in B-1 = 1 and contains no '[OWNER-CONFIRM' after the owner answers; the Gantt is still on Part B page 9; B-1 page count = 10.
- **Effort:** M · **Regression risk:** medium · **Expected gain:** +0.2 on Implementation

#### A-18 · P3 · PART_B1_DOCX · needs_fact · findings F-06
- **Anchor:** B1 §1.3 ¶"Supervisory architecture and qualifications. FIELDWISE" s7 (p. 27): 'The host also provides demonstrated European-project experience: … TUdi.'
- **Instruction:** Replace the European-project sentence (duplicated in Part B-2 §5.2) in place with the supervisors' supervision record and named international collaborations (2 lines out, 2–3 lines in).
- **Proposed text:** Prof. Janda has supervised [OWNER-CONFIRM: n] PhD and [OWNER-CONFIRM: m] postdoctoral researchers to completion and collaborates with [OWNER-CONFIRM: two named international groups]; Prof. Jung has supervised [OWNER-CONFIRM: n/m] and collaborates with [OWNER-CONFIRM: named group]. ATK's MSCA and Horizon Europe record is given in Part B-2, Section 5.2.
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** in place: B1 §1.3 ¶"Supervisory architecture and qualifications. FIELDWISE" s7 (p. 27): 'The host also provides demonstrated European-project experience: … TUdi.' (−2 lines)
- **Owner:** supervisor · **Fallback:** Leave the sentence as sealed; apply A-07 (outputs in Part B-2) only.
- **Ripple:** A-19 (same numbers in Part B-2 §5.2); Part B-2 §5.2 must keep the LANDRACES / AI4SoilHealth / COUSIN record (it does)
- **Verification:** grep 'has supervised' in B-1 §1.3 ≥ 1 with no '[OWNER-CONFIRM'; grep 'The host also provides demonstrated' = 0; §1.3 paragraph line count ≤ +1; B-1 page count = 10.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.2 on Excellence

#### A-21 · P3 · PART_B1_DOCX · needs_fact · findings F-02
- **Anchor:** B1 §1.2 ¶"Stage 2 (WP2) prospectively tests" s2 (p. 26); ¶"Overall methodology: concepts, models and" s5 (p. 25)
- **Instruction:** Dimension the prospective design in s2 and fix the stress-reference rule in the D1.2 sentence (+4 lines). Pay for it with CUT-19 (delete the two UAV sentences in §1.2 ¶"Methodological challenges and mitigation." — 'If clouds or acquisition timing … transferability assessment.' — which R4 and the §3.2 ELTE row already state, −2), CUT-23 (delete §1.3 ¶"Planned training activities and ELTE secondment." s5 'These activities advance the fellow … interface.', −1) and CUT-25 (delete §1.1 ¶"Problem and overarching aim. European" s2 'High-value horticultural irrigation often relies … unnecessary irrigation.', −2).
- **Proposed text:** Controlled irrigation creates well-watered, deficit-irrigated and unirrigated conditions in [OWNER-CONFIRM: n] replicate treatment areas of at least [OWNER-CONFIRM: a × b m] each, so that [OWNER-CONFIRM: k] interior Sentinel-2 pixels per area are valid; [OWNER-CONFIRM: c] physiological campaigns per season sample [OWNER-CONFIRM: p] plants per area at [OWNER-CONFIRM: growth stages]. … Before model fitting, D1.2 fixes the stress reference as [OWNER-CONFIRM: rule, e.g. Fv/Fm and stomatal-conductance deviation from the well-watered control, stratified by growth stage] and the acceptance thresholds for K6.
- **Net page-budget delta (B-1 lines):** -1 · **Compensating cut:** B1 §1.2 ¶"Methodological challenges and mitigation." UAV sentences (p. 26, −2) + B1 §1.3 ¶"Planned training activities and ELTE secondment." s5 (p. 27, −1) + B1 §1.1 ¶"Problem and overarching aim. European" s2 (p. 24, −2)
- **Owner:** fellow · **Fallback:** No change; the sealed sentences stand (no invented design numbers).
- **Ripple:** K5 in §3.1 (biological sample size reported) stays consistent; R2/R3 wording unchanged; MATE (Dr Takács) to confirm the reference rule
- **Verification:** The Stage 2 sentence contains at least three numerals and no '[OWNER-CONFIRM'; grep 'If clouds or acquisition timing' = 0; B-1 page count = 10.
- **Effort:** M · **Regression risk:** medium · **Expected gain:** +0.2 on Excellence

#### A-15 · P3 · PART_B1_DOCX · needs_fact · findings F-12
- **Anchor:** B1 §2.2 table "Strand" row "Communication" cell "Evidence/timing" (p. 29)
- **Instruction:** Replace 'Demonstrations, workshops, reach indicators' with named channels and reach targets supplied by the host and AgroVIR (+1 line). Pay for it with CUT-17: delete §2.2 ¶"FIELDWISE uses a targeted strategy" s2 ('Target groups are research communities, … wider public.', −2 lines), which the table repeats.
- **Proposed text:** [OWNER-CONFIRM: n] demonstrations; workshop [OWNER-CONFIRM: month]; articles in [OWNER-CONFIRM: outlet]; channels [OWNER-CONFIRM: ATK/ELTE/AgroVIR channels]; reach ≥ [OWNER-CONFIRM: n] growers
- **Net page-budget delta (B-1 lines):** -1 · **Compensating cut:** B1 §2.2 ¶"FIELDWISE uses a targeted strategy" s2 (p. 29): 'Target groups are research communities, … wider public.' (−2 lines)
- **Owner:** host · **Fallback:** Apply A-14 only; keep 'Demonstrations, workshops, reach indicators'.
- **Ripple:** A-13 numbers, if any, reused for reach
- **Verification:** Evidence/timing cell contains at least one numeral and one named channel and no '[OWNER-CONFIRM'; B-1 page count = 10.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.1 on Impact

#### A-17 · P3 · PART_B1_DOCX · needs_decision · findings F-13
- **Anchor:** B1 §2.1 table "Measure" row "Transferable-skills portfolio" cell "Evidence" (p. 28)
- **Instruction:** Turn grant writing and mentoring into dated commitments if the fellow and supervisor agree (+1 line within the existing cell height; no cut needed if the middle cell remains the tallest).
- **Proposed text:** CDP-tracked training and project outputs; [OWNER-CONFIRM: one grant application (scheme) submitted by M24]; [OWNER-CONFIRM: co-supervision of n MSc/BSc students at ATK or ELTE]
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** none needed
- **Owner:** fellow · **Fallback:** No change; the sealed cell stands.
- **Ripple:** §1.3 training paragraph should mention the same commitments only if space allows (not required)
- **Verification:** The cell contains no '[OWNER-CONFIRM' after the owner answers; row height unchanged (Evidence cell ≤ 4 lines); B-1 page count = 10.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.1 on Impact

#### A-19 · P3 · PART_B2_DOCX · needs_fact · findings F-06
- **Anchor:** B2 §5.2 table (Beneficiary) row "Role and profile of supervisor" (p. 36); table (Associated partner for secondment) row "Role and profile of supervisor" (p. 36)
- **Instruction:** Add to each supervisor-profile cell the supervision record (PhD / postdoctoral researchers supervised, completed) and two or three named international collaborations.
- **Proposed text:** Supervision record: [OWNER-CONFIRM: n PhD, m postdoctoral researchers supervised; k completed]. Main international collaborations: [OWNER-CONFIRM: named institutions/groups].
- **Net page-budget delta (B-1 lines):** n/a (no page limit) · **Compensating cut:** none needed
- **Owner:** supervisor · **Fallback:** No change; A-07 stands alone.
- **Ripple:** A-18 (Part B-1 sentence uses the same numbers)
- **Verification:** Both supervisor cells contain 'Supervision record:' with numerals and no '[OWNER-CONFIRM'.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.1 on Excellence (with A-18)

#### A-22 · P3 · PART_B1_DOCX · needs_decision · findings F-04, F-15
- **Anchor:** B1 §1.2 ¶"Open science practices. FIELDWISE follows" s8 (p. 26)
- **Instruction:** Replace the conditional sharing sentence in place with named repository, licence and preprint commitments decided by the fellow and the host (same length ±1 line; trim the same sentence to fit).
- **Proposed text:** Analysis code, the model card and non-sensitive derived outputs are deposited in [OWNER-CONFIRM: repository] under [OWNER-CONFIRM: licence] at each milestone release, each manuscript is posted as a preprint on [OWNER-CONFIRM: server], and commercially protectable results are assessed before disclosure.
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** in place: the replaced sentence (p. 26, 2 lines)
- **Owner:** fellow · **Fallback:** No change; the sealed sentence stands.
- **Ripple:** §2.2 ¶"Reach and uptake are tracked" 'monitoring of repository use after release' now refers to a named repository; D5.2 DMP description unchanged
- **Verification:** grep 'where institutional, commercial and IP rights permit' in B-1 = 0; sentence contains no '[OWNER-CONFIRM'; B-1 page count = 10.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.1 on Excellence

#### A-23 · P3 · PART_B1_DOCX · needs_fact · findings F-05
- **Anchor:** B1 §1.1 ¶"Pertinence. Three linked scientific" s3 (p. 24), after '…plant physiological responses2.'
- **Instruction:** Add one sentence positioning the approach against existing tomato water-stress indicators, with two references supplied by the fellow as footnotes (+1 text line, +2 footnote lines). No compensating cut remains in Part B pages 1–7 that does not touch a strength; use the ≈5 lines of slack on Part B page 7 and verify the page count. Lowest priority among the P3 items.
- **Proposed text:** Existing tomato water-stress indicators — [OWNER-CONFIRM: e.g. crop water stress index / thermal, stem-water-potential and evapotranspiration-based scheduling][OWNER-CONFIRM: ref A],[OWNER-CONFIRM: ref B] — are calibrated locally and rarely tested prospectively across years or sensing scales.
- **Net page-budget delta (B-1 lines):** 3 · **Compensating cut:** none without touching a strength; consumes Part B page 7 slack (≈5 lines) — mandatory page-count check
- **Owner:** fellow · **Fallback:** No change.
- **Ripple:** Footnote numbering 3–6 shifts by two; Part B page 7 slack reduced accordingly
- **Verification:** Footnote count in B-1 = 8; B-1 page count = 10; §3 still starts at the top of Part B page 8.
- **Effort:** M · **Regression risk:** medium · **Expected gain:** +0.1 on Excellence

#### A-24 · P3 · PART_B1_DOCX · needs_fact · findings F-07
- **Anchor:** B1 §1.3 ¶"Planned training activities and ELTE secondment." s6 (p. 27)
- **Instruction:** Replace 'Guest lectures and practical activities at MATE and, where feasible, Agricultural University–Plovdiv build on previous university teaching experience.' with named courses/providers with timing and firm teaching venues (+2 lines). Uses Part B page 7 slack (see A-23); apply only if A-23 is not applied or slack remains.
- **Proposed text:** Formal training: [OWNER-CONFIRM: course, provider, month] (open science/FAIR), [OWNER-CONFIRM: course, provider, month] (responsible AI), [OWNER-CONFIRM: course, provider, month] (grant writing/IP). Teaching: guest lectures and practical activities at MATE [OWNER-CONFIRM: month] and at the Agricultural University–Plovdiv [OWNER-CONFIRM: month].
- **Net page-budget delta (B-1 lines):** 2 · **Compensating cut:** none remaining without touching a strength; Part B page 7 slack — mandatory page-count check
- **Owner:** supervisor · **Fallback:** No change.
- **Ripple:** §2.1 table row 'Transferable-skills portfolio' stays consistent; CDP (D5.1) will list the same courses
- **Verification:** grep 'where feasible' in B-1 §1.3 = 0; sentence contains no '[OWNER-CONFIRM'; B-1 page count = 10.
- **Effort:** M · **Regression risk:** medium · **Expected gain:** +0.1 on Excellence

#### A-25 · P3 · PART_B1_DOCX · needs_fact · findings F-20
- **Anchor:** B1 §3.2 table "Organisation" row "HUN-REN ATK" s5 (p. 33)
- **Instruction:** Replace the generic hosting sentence with concrete arrangements supplied by the host (+3 lines). Pay for it with CUT-2 (delete the ATK row sentence 'Where available and formally assigned early-stage female researchers … participation.', −2) and CUT-3 (delete the ELTE row sentence 'Where available, female students … participation.', −2); both describe team balance, which the panel does not score.
- **Proposed text:** ATK employs the fellow under [OWNER-CONFIRM: full-time employment contract with full social security], integrates her in the Plant Physiology and Metabolomics Department with [OWNER-CONFIRM: office/laboratory and computing provision], provides [OWNER-CONFIRM: HR onboarding, relocation and family support, language support] and applies its gender equality plan (Part A); project administration is supported by [OWNER-CONFIRM: grants office].
- **Net page-budget delta (B-1 lines):** -1 · **Compensating cut:** B1 §3.2 table row "HUN-REN ATK" s4 (p. 33, −2) + B1 §3.2 table row "ELTE" s5 (p. 33, −2)
- **Owner:** host · **Fallback:** Delete nothing and insert only 'ATK applies a gender equality plan (Part A)' if space allows; otherwise no change.
- **Ripple:** Part A p. 5 'Gender equality plan: Yes' is the source for the GEP clause; Part B-2 §5.2 'General description' cell may repeat the contract statement
- **Verification:** ATK row contains 'employs the fellow under' and no '[OWNER-CONFIRM'; grep 'female' in B-1 §3.2 = 0; Part B page 10 ends with the MVCRI row; B-1 page count = 10.
- **Effort:** M · **Regression risk:** low · **Expected gain:** +0.1 on Implementation

#### A-34 · P3 · PART_B1_DOCX · needs_decision · findings F-17
- **Anchor:** B1 §3.1 ¶"WP1 — Data harmonisation, stress definition" header and ¶"Lead: fellow/ATK; MATE and ELTE" (p. 31)
- **Instruction:** If the fellow and supervisor decide to re-phase, move the model freeze from M3 to M4 (T1.3 M2–M4; MS1 M4; D1.2/D1.3 M4) and keep T2.2 at M4–M12 only if the start window (A-11) allows; otherwise leave as sealed. Any change must be propagated to the Gantt, MS1, D5.1 and §1.1.
- **Proposed text:** [OWNER-CONFIRM: T1.3 (M2–M4): build the pipeline; after protocol lock, fit and freeze the model/benchmark. … D1.2 protocol and D1.3 model/card (M4) … MS1 (M4)]
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** none needed
- **Owner:** fellow · **Fallback:** No change (re-phasing without the start-window decision would create new inconsistencies).
- **Ripple:** Gantt p. 32 (re-render); §1.1 O1/O2 deliverable months; §3.1 milestone list and critical path; §2.1 table (D5.1 M3 review) if D5.1 moves
- **Verification:** Every occurrence of 'M3' tied to MS1/D1.2/D1.3 reads 'M4'; Gantt milestone 1 at month 4; B-1 page count = 10.
- **Effort:** L · **Regression risk:** high · **Expected gain:** +0.1 on Implementation

#### A-27 · P3 · PART_B1_DOCX · needs_fact · findings F-22
- **Anchor:** B1 §3.2 table "Organisation" row "Krumatic EOOD" s1 (p. 33)
- **Instruction:** Append the funding source of the remunerated services and of the field equipment (+1 line; Part B page 10 slack).
- **Proposed text:** The services and the soil-water and meteorological monitoring equipment are funded from [OWNER-CONFIRM: the research, training and networking contribution (EUR 1 000 per month) | host co-funding | other source].
- **Net page-budget delta (B-1 lines):** 1 · **Compensating cut:** Part B page 10 slack (≈4 lines, shared with A-26) — mandatory page-count check
- **Owner:** host · **Fallback:** No change.
- **Ripple:** Part A budget unchanged (unit contributions are fixed)
- **Verification:** Krumatic row contains 'funded from' and no '[OWNER-CONFIRM'; B-1 page count = 10.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.05 on Implementation

#### A-28 · P3 · PART_B1_DOCX · needs_decision · findings F-15
- **Anchor:** B1 §2.2 table "Strand" row "Dissemination" cell "Measures and outputs" (p. 29): 'EGU/ECPA presentations'
- **Instruction:** Add one horticultural or irrigation-science venue chosen by the fellow (in-cell, no line change expected).
- **Proposed text:** EGU/ECPA and [OWNER-CONFIRM: horticultural or irrigation-science conference] presentations
- **Net page-budget delta (B-1 lines):** 0 · **Compensating cut:** none needed
- **Owner:** fellow · **Fallback:** No change.
- **Ripple:** K13 (≥2 conference presentations) unchanged
- **Verification:** Dissemination cell names three venues and no '[OWNER-CONFIRM'; row height unchanged; B-1 page count = 10.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.05 on Impact

#### A-29 · P3 · PART_B2_DOCX · needs_fact · findings F-08
- **Anchor:** B2 §4 list "Professional experience" bullet 4 'Independent developer of the pre-existing DrR – Digital Agronomist desktop research prototype.' (p. 34)
- **Instruction:** Document the prototype: version, repository or dated declaration, implemented functions, and name the data-science training providers in the 'Methods and technical competences' paragraph.
- **Proposed text:** Independent developer of the pre-existing DrR – Digital Agronomist desktop research prototype (version [OWNER-CONFIRM: x.y], [OWNER-CONFIRM: repository URL | dated declaration dd/mm/yyyy]; implements [OWNER-CONFIRM: functions, e.g. data ingestion, index computation, stress-status display]). … formal training in AI, Data Science, Machine Learning and Python ([OWNER-CONFIRM: provider, year]).
- **Net page-budget delta (B-1 lines):** n/a (no page limit) · **Compensating cut:** none needed
- **Owner:** fellow · **Fallback:** No change.
- **Ripple:** Optional one-clause echo in B1 §1.4 only if Part B page 7 slack remains (not required)
- **Verification:** B-2 §4 DrR bullet contains a version and a repository or declaration date and no '[OWNER-CONFIRM'.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.05 on Excellence

#### A-30 · P4 · PART_B2_DOCX · editorial · findings F-25
- **Anchor:** B2 footer pp. 34–37
- **Instruction:** Replace the footer field '[Page limit]' with the actual page count and restart numbering at 1 for Part B-2 (or remove the 'of [Page limit]' fragment).
- **Proposed text:** Part B – Page 1 of 4
- **Net page-budget delta (B-1 lines):** n/a (no page limit) · **Compensating cut:** none needed
- **Owner:** operator · **Fallback:** n/a (cosmetic)
- **Ripple:** none
- **Verification:** grep '[Page limit]' in the exported PDF = 0.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.0 (cosmetic)

#### A-31 · P4 · PART_B2_DOCX · needs_fact · findings F-27
- **Anchor:** B2 §5.1 ¶"Only formal MSCA participating organisations" (p. 35), append
- **Instruction:** Add the inter-relationship declaration the template asks for, confirmed by the fellow and the host.
- **Proposed text:** Inter-relationships: [OWNER-CONFIRM: none between the participating organisations and individuals beyond the co-authorships listed in Section 4 (MATE, MVCRI) | list].
- **Net page-budget delta (B-1 lines):** n/a (no page limit) · **Compensating cut:** none needed
- **Owner:** fellow · **Fallback:** No change.
- **Ripple:** none
- **Verification:** grep 'Inter-relationships:' in B-2 §5.1 = 1 with no '[OWNER-CONFIRM'.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.0 (template completeness)

#### A-32 · P4 · PART_A_PORTAL · portal_admin · findings F-26
- **Anchor:** A p.8 Researcher > Current Department/Faculty/Institute/Laboratory name; A p.15 AgroVIR previous projects and infrastructure (500/300-character fields); A p.13 AgroVIR Departments
- **Instruction:** Correct 'Plant physyology' to 'Plant physiology'; shorten the two AgroVIR fields so that they end inside the character limit (e.g. end the infrastructure text at 'satellite-map use and navigation.' and the project-name field at 'SMART-GAZDA, Bonafarm'); fill the AgroVIR department block or mark it not applicable.
- **Proposed text:** Plant physiology
- **Net page-budget delta (B-1 lines):** n/a (no page limit) · **Compensating cut:** none needed
- **Owner:** operator · **Fallback:** n/a (cosmetic)
- **Ripple:** none
- **Verification:** Regenerated Part A pp. 8, 13, 15 show no truncated words and no typo.
- **Effort:** S · **Regression risk:** low · **Expected gain:** +0.0 (cosmetic)

### Cut pool for Part B-1 (compensating cuts, all duplicates or unscored content)

| Cut | Anchor (PDF page) | Text removed | Lines | Why it is safe |
|---|---|---|---|---|
| CUT-1 | B1 §1.1 ¶"Pertinence. Three linked scientific" s4–s5 (p. 24) | "These objectives also advance the fellow … inter-sectoral profile." | −3 | Duplicates §2.1 (career trajectory). Used by A-08. |
| CUT-7 | B1 §2.3 ¶"Impact is measured through project-controlled" s3 (p. 30) | "Delivery is tracked through K1–K14, … implementation." | −3 | Duplicates the §3.1 KPI list. Used by A-09. |
| CUT-13 | B1 §2.1 ¶"FIELDWISE is designed to consolidate" s2 (p. 28) | "The fellowship builds on competences … inter-sectoral exploitation." | −2 | Duplicates §1.4 "Fit and development potential". Used by A-14. |
| CUT-8 | B1 §2.1 ¶"By completion, the fellow will" s3 (p. 29) | "The 12-month ELTE secondment adds … non-academic experience." | −1 | Duplicates the §2.1 table. Used by A-12. |
| CUT-10 | B1 §1.3 ¶"Supervisory architecture and qualifications." s7 (p. 27) | "The host also provides demonstrated European-project experience: … TUdi." | −2 | Duplicated in B-2 §5.2. Replaced in place by A-18. |
| CUT-11 | B1 §1.3 ¶"Rationale and added value of the" s6 (p. 27) | "Commercially sensitive evaluation uses protected, coded or appropriately aggregated data." | −1 | Duplicated in Part A ethics self-assessment and B-2 §6. Used by A-13. |
| CUT-12 | B1 §1.2 ¶"Stage 3 (WP3–WP4) operationalises only" (p. 26) | Condense the four-line paragraph to one sentence | −1 | Duplicates §2.2 exploitation row. Used by A-13. |
| CUT-17 | B1 §2.2 ¶"FIELDWISE uses a targeted strategy" s2 (p. 29) | "Target groups are research communities, … wider public." | −2 | The table's "Target groups" column repeats it. Used by A-15. |
| CUT-20 | B1 §1.3 ¶"Two-way transfer of knowledge. FIELDWISE" s1 (p. 27) | "FIELDWISE connects internationally recognised … expertise." | −1 | Generic opener; s2–s4 carry the content. Used by A-16. |
| CUT-18 | B1 §1.1 ¶"Realistically achievable. FIELDWISE combines" s3 (p. 25) | "Previous MATE research established … alone." | −2 | Already evidenced by footnotes 3–4. Used by A-20. |
| CUT-9 | B1 §1.2 ¶"Integration of methods and disciplines." s2 (p. 26) | Compress the partner list to the four role assignments | −1 | Roles repeated in §1.3 and §3.2; the role assignment itself is kept (E3 strength). Used by A-20. |
| CUT-22 | B1 §1.2 ¶"Overall methodology: concepts, models and" s2 (p. 25) | "Operational predictors comprise spectral, soil-water and meteorological variables." | −1 | Restated in Stage 1 and Stage 2. Used by A-20. |
| CUT-19 | B1 §1.2 ¶"Methodological challenges and mitigation." UAV sentences (p. 26) | "If clouds or acquisition timing … transferability assessment." | −2 | Stated again in R4 and in the §3.2 ELTE row. Used by A-21. |
| CUT-23 | B1 §1.3 ¶"Planned training activities and ELTE secondment." s5 (p. 27) | "These activities advance the fellow … interface." | −1 | The "Agricultural Data Scientist" trajectory appears five times in B-1. Used by A-21. |
| CUT-25 | B1 §1.1 ¶"Problem and overarching aim. European" s2 (p. 24) | "High-value horticultural irrigation often relies … unnecessary irrigation." | −2 | Generic problem framing; gap (i)–(iii) in "Pertinence" carries the argument. Used by A-21. |
| CUT-5 | B1 §3.1 ¶"D5.1 CDP (M3); D5.2 DMP" last sentence (pp. 31–32) | "Required administrative outputs: … two years later." | −2 | Grant obligations, not scored. Used by A-10. |
| CUT-14 | B1 §3.1 ¶"The fellow leads the scientific work" s2 (p. 31) | "Five WPs connect … career development." | −1 | Summary sentence; the WP list follows. Used by A-10. |
| CUT-15 | B1 §3.1 ¶"Lead: fellow/ATK; supervisors and host" (p. 31) | Condense T5.1–T5.4 to three lines, keeping "quarterly reviews" | −1 | No content lost beyond verbs. Used by A-11. |
| CUT-16 | B1 §3.1 ¶"D2.1 dataset/prediction log (M20)" K5 (p. 31) | "all scheduled observation opportunities accounted for, with" | −1 | K5 keeps "valid coverage and biological sample size reported". Used by A-11. |
| CUT-2 | B1 §3.2 table row "HUN-REN ATK" s4 (p. 33) | "Where available and formally assigned early-stage female researchers … participation." | −2 | Team balance, not scored (evaluation form: gender dimension concerns research content). Used by A-25. |
| CUT-3 | B1 §3.2 table row "ELTE" s5 (p. 33) | "Where available, female students … participation." | −2 | Same. Used by A-25. |
| CUT-4 | B1 §3.2 table row "MVCRI, Plovdiv" (p. 33) | Condense to three lines, keeping "no core in-action validation role" | −2 | Post-MSCA route; the §2.1 and §2.3 text carries it. Used by A-26. |

Pool totals: Part B pages 1–7 −25 lines (of which P0–P2 use −10 and P3 use −15), pages 8–9 −5 lines, page 10 −6 lines. Cuts not listed here touch a strength (II.3) and are not offered.

## II.3 Do-not-touch list

| Location | Reason |
|---|---|
| B1 §1.1 ¶"Beyond the state of the art," (p. 25) | The four challenged assumptions and the three citable advances are the clearest statement of ambition; every lens credited it. |
| B1 §1.1 ¶"Measurability and verifiability.Model development" (p. 25) | Metric set, M3 freeze and falsifiable hypothesis — the strongest sentences in the proposal (E1, E2, E3). Only the missing space after 'verifiability.' may be fixed. |
| B1 §1.2 ¶"Stage 2 (WP2) prospectively tests" s1, s4–s6 (p. 26) | Frozen-model, primary-before-recalibration logic; edit only s2 (A-21). |
| B1 §1.2 ¶"Methodological challenges and mitigation." items (i)–(vi) (p. 26) | Dense mitigation list valued by E1 and E2; only the two UAV sentences are a permitted cut (CUT-19). |
| B1 §1.2 ¶"Gender dimension and other diversity aspects." (p. 26) | Accepted by all lenses as an adequate justified non-relevance statement; rewording risks turning it into a team-balance claim. |
| B1 §1.3 ¶"Structured supervision and governance." (p. 27) | Governance detail credited by E3; the only permitted change is none (cadence is harmonised in §2.1 by A-04). |
| B1 §1.3 ¶"Two-way transfer of knowledge." s2–s4 (p. 27) | Concrete two-directional transfer credited by all lenses; only the generic opening sentence is a permitted cut (CUT-20). |
| B1 §1.3 ¶"Rationale and added value of the" s1–s5 (p. 27) | Compliance-critical placement wording ('integral', 'M25–M30', non-academic, added value for project and career); only s6 is a permitted cut (CUT-11). |
| B1 §2.2 table rows "Exploitation" and "IP and knowledge management" and ¶"Exploitation pathway." (pp. 29–30) | The strongest Impact strand (rights layers, dated DrR baseline, four result families); preserve verbatim. |
| B1 §2.3 table row "Agricultural & environmental" sentence 'no numerical water-saving benefit is claimed in advance' (p. 30) | Honest bounding credited by E1; keep it and add magnitude beside it (A-13) rather than replace it. |
| B1 §3.1 WP headers, task months, PM figures, deliverable months, K1–K14, MS1–MS6 (pp. 31–32) | Internally consistent set that reconciles with the Gantt; any change ripples into the Gantt image and Part A (duration). |
| B1 §3.1 ¶"Decision gates and dependencies." and ¶"Risk control." s2 (p. 32) | Named approvers and the integrity rule ('Poor transfer is a reportable scientific result…') were quoted as strengths. |
| B1 §3.1 Gantt (p. 32) | Image; Part B page 9 is full — any text pushed from page 8 moves the Gantt to page 10 and overflows the limit. Re-render only for A-03 labels. |
| Part A pp. 8–9 (researcher data, residence table), p. 16 (budget, 24 + 6 months, countries) | Eligibility- and budget-critical; consistent with Part B; do not edit. |
| B2 §5.1 table (PICs, roles) and §5.2 EU-project record (pp. 35–36) | Consistent with Part A after A-01; the LANDRACES/AI4SoilHealth/COUSIN record is the host's MSCA evidence. |
| B1 §2.1 table split across Part B pages 5–6 (pp. 28–29) | Row-break sensitive: any reflow above it can move a row and change the page fill unpredictably; check row integrity after every edit in §1.x–§2.1. |
| B1 footnotes 1–6 (pp. 24, 27) | 9-pt footnotes change page fill non-linearly; add footnotes (A-23) only with a page-count check. |

## II.4 Open decisions for owners

Each item lifts a score only if the owner supplies the fact or takes the decision; each has an honest fallback that never strengthens a claim. Answers are needed by **12:00 Brussels time on 2026-09-09** (10:00 for OD-E1 and OD-E20), enter the text through the paired action only after the owner confirms, and are recorded in the decision-log entry `esr-revision_2026-09-09.json` together with the applied action set.

| ID | Question (paired action) | Owner | Needed by | Fallback |
|---|---|---|---|---|
| OD-E1 | Does the Guide for Applicants require the secondment host (ELTE) to be registered as an associated partner in Part A for a European Fellowship? (A-01) | operator | 2026-09-09T10:00+02:00 | Leave Part A unchanged; Part B-2 table 5.1 already states role and PIC. |
| OD-E2 | Is the Environmental Engineering MSc held (award date dd/mm/yyyy) or in progress (2025–2026)? (A-02) | fellow | 2026-09-09T12:00+02:00 | Use the CV wording (in progress) in both Part B-1 and Part B-2. |
| OD-E3 | Full dd/mm/yyyy dates for every position, degree and the career break; one-clause significance and open-access status per output; entries or 'none' for invited presentations, funding, supervision/mentoring. (A-05) | fellow | 2026-09-09T12:00+02:00 | Insert only the PhD award date 14/10/2020 from Part A. |
| OD-E4 | Supervision record (PhD / postdoctoral researchers supervised and completed) and two or three named international collaborations for Prof. Janda and Prof. Jung (and Dr Hollós). (A-18, A-19) | supervisor | 2026-09-09T12:00+02:00 | Apply A-07 (outputs from Part A into Part B-2) only. |
| OD-E5 | Hyperspectral-to-Sentinel-2 harmonisation: instrument and spectral range, plot dimensions, conversion method, correction applied, acceptance test; model family, uncertainty and calibration method; benchmark. (A-20) | fellow | 2026-09-09T12:00+02:00 | No change to the sealed sentences. |
| OD-E6 | Prospective design: number and size of replicate treatment areas, valid interior pixels per area, campaigns per season, plants per area, growth stages sampled; the stress-reference rule to be fixed in D1.2. (A-21) | fellow | 2026-09-09T12:00+02:00 | No change to the sealed sentences. |
| OD-E7 | Assumed start window (months) compatible with the tomato calendar, and the slipped-start contingency; whether to re-phase MS1 to M4. (A-11, A-34) | fellow | 2026-09-09T12:00+02:00 | No change; the calendar dependency stays as sealed. |
| OD-E8 | Addressable magnitude: farms and hectares under AgroVIR software, irrigated processing-tomato area in Hungary and Bulgaria (with source), hectares covered by the validation field. (A-13) | partner:AgroVIR | 2026-09-09T12:00+02:00 | Apply A-12 (editorial European row) only. |
| OD-E9 | Communication channels (ATK/ELTE/AgroVIR), number and timing of demonstrations, workshop month, article outlets, reach target. (A-15) | host | 2026-09-09T12:00+02:00 | Apply A-14 (editorial restructuring) only. |
| OD-E10 | Open-science commitments: repository, licence, preprint server, milestone release schedule. (A-22) | fellow | 2026-09-09T12:00+02:00 | No change. |
| OD-E11 | Status of the MATE data-access/reuse agreement, the ATK–Krumatic development agreement, the producer's identity, field and commitment letter, and the backup site. (A-26) | host | 2026-09-09T12:00+02:00 | Apply A-10 (risk row R7) only. |
| OD-E12 | Hosting arrangements: contract type, office/laboratory/computing provision, HR onboarding, relocation and family support, language support, grants-office support. (A-25) | host | 2026-09-09T12:00+02:00 | Insert only the gender-equality-plan clause (Part A p. 5) if space allows. |
| OD-E13 | Funding source of Krumatic's remunerated services, monitoring equipment, UAV flights and open-access fees. (A-27) | host | 2026-09-09T12:00+02:00 | No change. |
| OD-E14 | Ethics table: do grower/user feedback activities count as human participants and personal-data processing? Which page pointer for the AI item? (A-06) | operator | 2026-09-09T12:00+02:00 | Leave the table as sealed. |
| OD-E15 | Named training courses, providers and months; firm teaching venues and months. (A-24) | supervisor | 2026-09-09T12:00+02:00 | No change. |
| OD-E16 | Career commitments: one grant application (scheme, month) and a co-supervision/mentoring role; a horticultural or irrigation-science conference venue. (A-17, A-28) | fellow | 2026-09-09T12:00+02:00 | Apply A-16 (PANGEOS, teaching venues) only. |
| OD-E17 | Two references on existing tomato water-stress indicators (CWSI/thermal, stem-water potential, ET-based scheduling) and the one-sentence positioning. (A-23) | fellow | 2026-09-09T12:00+02:00 | No change. |
| OD-E18 | DrR prototype: version, repository or dated declaration, implemented functions; data-science training providers and years. (A-29) | fellow | 2026-09-09T12:00+02:00 | No change. |
| OD-E19 | Inter-relationship declaration for Part B-2 §5 (none beyond listed co-authorships, or list). (A-31) | fellow | 2026-09-09T12:00+02:00 | No change. |
| OD-E20 | Can the Gantt image be re-rendered from its source with the renumbered deliverable labels? (A-03) | operator | 2026-09-09T10:00+02:00 | Keep the sealed deliverable numbering everywhere. |

## II.5 Pre-upload checklist

1. The sealed PDF `docs/tier5_deliverables/submitted/FIELDWISE_101373105_submitted_2026-09-07.pdf` is unchanged (SHA-256 `c3bfb51f…81dbe` re-verified) and the re-uploaded PDF is stored beside it under `docs/tier5_deliverables/submitted/`.
2. The Part B-1 and Part B-2 docx used for editing reproduce the sealed PDF sentence for sentence before the first edit (`FIELDWISE_Part_B1_sealed-source_2026-09-07.docx`, `FIELDWISE_Part_B2_sealed-source_2026-09-07.docx`); every anchor was verified against the docx before editing.
3. Part B-1 re-exported to PDF: page count = 10 with the §3.2 table, the Gantt, the risk table and footnotes inside the 10 pages; the Gantt still ends Part B page 9; Section 3 still starts at the top of Part B page 8.
4. Typesetting unchanged: Times New Roman 11 pt body, footnotes ≥ 8 pt, margins ≥ 15 mm, single spacing; fonts embedded in the PDF (check with `pdffonts`).
5. No template placeholders (`[Page limit]`, `[OWNER-CONFIRM`), no tracked changes, no comments, no highlighting in either exported PDF (`pdftotext` + grep).
6. Part A ↔ Part B ↔ Part B-2 cross-checks re-run: participants (Part A p. 4 vs B-2 §5.1), duration 24 + 6, placement host/country/length, supervisor and researcher identity, PhD date 14/10/2020, residence table, MSc status (A-02), deliverable numbering (A-03), CDP cadence (A-04), ethics table vs self-assessment (A-06).
7. Every applied action's verification test (Annex B, `verification`) passed and is logged with the action id; every unapplied P3 action is logged with its fallback.
8. Part B-1 and Part B-2 both attached in the wizard; Part A saved after the portal edits (A-01, A-06, A-32); the wizard's validation shows no error.
9. Submission completed and a new acknowledgement of receipt downloaded well before 17:00 Brussels time (target: acknowledgement in hand by 16:00; final upload started no later than 15:30).
10. Decision-log entry `esr-revision_2026-09-09.json` written with the applied action set, the owner answers used, the fallbacks taken and the new PDF's SHA-256.

## II.6 Machine-readable appendix

The block below is byte-identical to `plans/reports/FIELDWISE_ESR_2026-09-08.json`.

```json
{
  "schema_id": "orch.tier5.esr_review_packet.v1",
  "proposal_id": "101373105",
  "acronym": "FIELDWISE",
  "evaluated_version": {
    "portal_submission_id": "SEP-211392861",
    "sealed_at": "2026-09-07 17:25:34 CET (portal stamp)",
    "pdf_sha256": "c3bfb51f93b4c0c36221d0bd83dab77efaa619eee4f3dd937e58d728c3f81dbe"
  },
  "generated_at": "2026-09-08T14:10:00+02:00",
  "scores": {
    "excellence": 3.6,
    "impact": 3.7,
    "implementation": 3.5,
    "total": 72.2,
    "thresholds_passed": true,
    "funding_zone": "above_threshold_not_competitive"
  },
  "lens_scores": {
    "E1": {
      "excellence": 3.7,
      "impact": 3.8,
      "implementation": 3.6
    },
    "E2": {
      "excellence": 3.5,
      "impact": 3.8,
      "implementation": 3.5
    },
    "E3": {
      "excellence": 3.7,
      "impact": 3.6,
      "implementation": 3.5
    }
  },
  "aspect_scores": {
    "exc-obj": 4.2,
    "exc-method": 3.4,
    "exc-supervision": 3.5,
    "exc-researcher": 3.6,
    "imp-career": 4.1,
    "imp-dissemination": 3.8,
    "imp-magnitude": 3.3,
    "impl-workplan": 3.5,
    "impl-host": 3.4
  },
  "formal_checks": [
    {
      "check": "Part B-1 page count = 10",
      "evidence": "PDF pp. 24-33, footer 'Part B - Page 1...10 of 10'",
      "status": "OK",
      "consequence": "none"
    },
    {
      "check": "Part B-1 typesetting (A4, margins >= 15 mm, Times New Roman, body >= 11 pt, other >= 8 pt, single spacing)",
      "evidence": "pp. 24-33: 595 x 842 pt; body TimesNewRomanPSMT 11.0 pt; footnotes 9.0 pt; margins L 15.0 mm / R 14.9 mm; body text >= 25 mm from top and >= 23 mm from bottom (template header/footer excluded); Gantt labels ~8.5 pt",
      "status": "OK",
      "consequence": "none (0.1 mm rounding on the right margin)"
    },
    {
      "check": "Part B-2 completeness (sections 4-9, generative-AI disclosure)",
      "evidence": "Section 4 pp. 34-35; 5.1 p. 35; 5.2 pp. 35-37 (beneficiary and two associated partners, ~1/2 page each); 6, 7, 8 (~1/3 page), 9 n/a, AI disclosure p. 37",
      "status": "OK",
      "consequence": "none"
    },
    {
      "check": "Part B-2 footers",
      "evidence": "pp. 34-37: 'Part B - Page 3...6 of [Page limit]' (unreplaced placeholder; numbering starts at 3)",
      "status": "Check",
      "consequence": "cosmetic; not scored (W3)"
    },
    {
      "check": "Participants: Part A vs Part B-2 table 5.1",
      "evidence": "Part A p. 4 lists HUN-REN ATK (Coordinator) and AgroVIR (Associated). Part B-2 p. 35 lists ATK (866599553), ELTE (999896468, associated partner for secondment) and AgroVIR (891807622); 'Only formal MSCA participating organisations are listed.'",
      "status": "Risk",
      "consequence": "The secondment host (12 of 24 months) is absent from Part A; Part A and Part B-2 are inconsistent (W1). Operator confirms the Part A requirement with the Guide for Applicants / NCP before editing."
    },
    {
      "check": "Duration 24 + 6 months",
      "evidence": "Part A p. 16 (fellowship 24, Hungary; placement 6, Hungary); Part B-1 3.1 p. 31 (24 months, placement M25-M30); 2.3 p. 30",
      "status": "OK",
      "consequence": "none"
    },
    {
      "check": "Non-academic placement: host, country, length, position",
      "evidence": "AgroVIR Kft., Budaors, Hungary (Part A p. 12: research organisation No, non-profit No, academic No); six months at the end (M25-M30, pp. 27, 31); rationale p. 27",
      "status": "OK",
      "consequence": "placement evaluable (WP pp. 27, 83)"
    },
    {
      "check": "Secondment vs 50 % cap",
      "evidence": "Part B-1 3.1 p. 31: ELTE blocks M1-M3, M10-M12, M16-M21 = 12 of 24 months, Hungary",
      "status": "OK",
      "consequence": "equals the cap ('cannot exceed half'); same country as the beneficiary is permitted (WP p. 26: 'any country worldwide')"
    },
    {
      "check": "Supervisor identity",
      "evidence": "Part A p. 7 Prof. Tibor Janda, Head of Department; Part B-1 1.3 p. 26; Part B-2 5.1 p. 35 and 5.2 p. 36",
      "status": "OK",
      "consequence": "none"
    },
    {
      "check": "Researcher identity and PhD date",
      "evidence": "Part A p. 8: Rositsa Cholakova, doctorate awarded 14/10/2020; Part B-2 p. 34: 'PhD in Plant Physiology, Agricultural University of Plovdiv, 2020'",
      "status": "Check",
      "consequence": "CV lacks the dd/mm/yyyy date the template requires; no contradiction (W2)"
    },
    {
      "check": "PhD held at the deadline",
      "evidence": "Part A p. 8: 14/10/2020",
      "status": "OK",
      "consequence": "none"
    },
    {
      "check": "Research experience <= 8 years full-time equivalent",
      "evidence": "14/10/2020 to 09/09/2026 = 5.90 years elapsed; declared 'Full-time parenting career break: 34 months (2021-2024)' (p. 35) gives ~3.07 years",
      "status": "OK",
      "consequence": "below 8 years even without the deduction; the break carries no start/end dates - applicant to double-check that supporting documentation exists"
    },
    {
      "check": "Mobility rule (<= 12 months in Hungary in the 36 months before 09/09/2026)",
      "evidence": "Part A p. 9: Hungary 09/03/2026-04/06/2026 = 87 days; Bulgaria otherwise (1,884 + 96 days); no gaps. CV p. 34 lists MATE stays of 10 + 14 days (2025) not in the table (short stays)",
      "status": "OK",
      "consequence": "87 (at most ~111) days, far below 365"
    },
    {
      "check": "Residence table vs CV",
      "evidence": "ELTE traineeship '3 months (2026)' (p. 34) matches Hungary 09/03-04/06/2026 (p. 9)",
      "status": "OK",
      "consequence": "none"
    },
    {
      "check": "Budget arithmetic (Part A p. 16)",
      "evidence": "0.787 x 6350 x 24 = 119,938.8; 710 x 24 = 17,040; 660 x 24 = 15,840; 1,000 x 24 = 24,000; 650 x 24 = 15,600; placement rows analogous; grand total 240,523.5",
      "status": "OK",
      "consequence": "the 'Management and indirect' total cell prints 0 although the grand total includes 19,500 - portal rendering artefact, not applicant-editable; not assessed by the panel"
    },
    {
      "check": "Ethics table vs ethics self-assessment",
      "evidence": "Part A p. 17: human participants No; personal data No; AI Yes (page '6'). Part A pp. 19-20 and Part B-2 6 p. 37: growers and users give voluntary structured feedback under informed consent; personal data processed under GDPR, coded/pseudonymised",
      "status": "Check",
      "consequence": "not scored by the panel; ethics screening may query the two 'No' answers (W7); the AI page pointer '6' does not match where AI is discussed"
    },
    {
      "check": "Scope against the topic description",
      "evidence": "Topic HORIZON-MSCA-2026-PF-01-01 (all domains eligible); PhD holder, international mobility BG -> HU, inter-sectoral placement, interdisciplinary training (physiology / EO / ML)",
      "status": "OK",
      "consequence": "in scope"
    },
    {
      "check": "Other questions of the evaluation form",
      "evidence": "in scope: yes; exceptional funding: no third-country participant; hESC: No (p. 17); human embryos: No; excluded activities: none (p. 3); exclusive civil focus: yes (pp. 3, 22)",
      "status": "OK",
      "consequence": "none"
    },
    {
      "check": "Part A free-text fields",
      "evidence": "p. 8 'Plant physyology'; p. 15 'Bonafarm G' and 'navigation and excha' (field-length truncation); p. 13 AgroVIR department block empty",
      "status": "Check",
      "consequence": "cosmetic (W6)"
    },
    {
      "check": "Part B-2 section 5 inter-relationship declaration",
      "evidence": "No declaration given; the CV shows co-authorship with MATE (Takacs) and MVCRI (Ganeva) staff who appear in Part B-1 3.2",
      "status": "Check",
      "consequence": "template asks for a declaration; no scoring consequence"
    },
    {
      "check": "Resubmission question",
      "evidence": "Part A p. 2: No",
      "status": "OK",
      "consequence": "none"
    },
    {
      "check": "ERA Fellowships opt-in",
      "evidence": "Part A p. 23: Yes (host in Hungary)",
      "status": "OK",
      "consequence": "fallback funding line available"
    },
    {
      "check": "Employment of the fellow",
      "evidence": "Part B-2 p. 36: 'sole beneficiary and employing organisation'; full living allowance requested (Part A p. 16)",
      "status": "OK",
      "consequence": "employment contract implied; contract type not stated in Part B-1"
    }
  ],
  "findings": [
    {
      "finding_id": "F-01",
      "criterion": "excellence",
      "aspect_id": "exc-method",
      "severity": "major",
      "location": {
        "part": "B1",
        "section": "1.2",
        "pdf_page": 25,
        "anchor": "B1 §1.2 ¶\"Stage 1 (WP1) harmonises the\" s2 (p. 25)"
      },
      "evidence": "Historical plots are too small for defensible plot-level Sentinel-2 retrieval; handheld hyperspectral measurements will therefore be transformed, where technically possible, into Sentinel-2-compatible predictors before model freeze.",
      "description": "The hyperspectral-to-Sentinel-2 harmonisation on which the frozen model depends is not specified: no spectral-response, correction, scaling or acceptance procedure, no plot dimensions or instrument, and the step is committed only 'where technically possible'; the frozen model therefore never sees a real Sentinel-2 predictor before deployment and the resulting domain shift is neither bounded nor estimated.",
      "score_impact_estimate": -0.3,
      "watchlist_ref": "W12"
    },
    {
      "finding_id": "F-02",
      "criterion": "excellence",
      "aspect_id": "exc-method",
      "severity": "major",
      "location": {
        "part": "B1",
        "section": "1.2",
        "pdf_page": 26,
        "anchor": "B1 §1.2 ¶\"Stage 2 (WP2) prospectively tests\" s2 (p. 26); ¶\"Overall methodology: concepts, models and\" s5 (p. 25)"
      },
      "evidence": "Controlled irrigation creates well-watered, deficit-irrigated and unirrigated conditions in treatment areas permitting valid Sentinel-2 observation. … Before model fitting, D1.2 will specify how these complementary sources define the stress reference.",
      "description": "The experimental and statistical design is not dimensioned: number and size of treatment areas and replicates, observations per campaign, campaigns per season and target sample sizes are absent; the physiological stress-reference rule and the acceptance thresholds are deferred to D1.2; crop growth stage is not considered; no pre-registration is committed.",
      "score_impact_estimate": -0.3,
      "watchlist_ref": "W13"
    },
    {
      "finding_id": "F-03",
      "criterion": "excellence",
      "aspect_id": "exc-method",
      "severity": "minor",
      "location": {
        "part": "B1",
        "section": "1.2",
        "pdf_page": 25,
        "anchor": "B1 §1.2 ¶\"Stage 1 (WP1) harmonises the\" s5 (p. 25)"
      },
      "evidence": "Blocked, leakage-safe unseen-year validation tests temporal transfer; a parsimonious uncertainty-aware model is compared with a nonlinear benchmark.",
      "description": "The model family and the uncertainty-quantification and calibration methods are not named; no proximal spectral measurement is planned in the prospective seasons, so sensing-scale and environmental transfer cannot be separated as the transfer specification (D1.5) intends.",
      "score_impact_estimate": -0.05,
      "watchlist_ref": null
    },
    {
      "finding_id": "F-04",
      "criterion": "excellence",
      "aspect_id": "exc-method",
      "severity": "minor",
      "location": {
        "part": "B1",
        "section": "1.2",
        "pdf_page": 26,
        "anchor": "B1 §1.2 ¶\"Open science practices. FIELDWISE follows\" s8 (p. 26)"
      },
      "evidence": "Analysis code, metadata and non-sensitive derived outputs will be shared where institutional, commercial and IP rights permit; potentially protectable results will be assessed before public disclosure",
      "description": "Open-science practices stop at principles: no repository, licence, preprint or public pre-registration is named, and code sharing is conditional on institutional, commercial and IP rights.",
      "score_impact_estimate": -0.1,
      "watchlist_ref": "W15"
    },
    {
      "finding_id": "F-05",
      "criterion": "excellence",
      "aspect_id": "exc-obj",
      "severity": "minor",
      "location": {
        "part": "B1",
        "section": "1.1",
        "pdf_page": 24,
        "anchor": "B1 §1.1 ¶\"Problem and overarching aim. European\" s1 and footnotes 1-4 (p. 24)"
      },
      "evidence": "approximately 30% of EU territory experiences seasonal water scarcity in an average year, while climate change is expected to intensify drought frequency, severity and seasonal freshwater fluctuations1.",
      "description": "The state of the art rests on four references, one of them a bare institutional web address, and does not engage with existing crop water-stress indicators or scheduling approaches for tomato (thermal or CWSI-type indices, sensor- or ET-based scheduling).",
      "score_impact_estimate": -0.1,
      "watchlist_ref": "W14"
    },
    {
      "finding_id": "F-06",
      "criterion": "excellence",
      "aspect_id": "exc-supervision",
      "severity": "major",
      "location": {
        "part": "B1",
        "section": "1.3",
        "pdf_page": 26,
        "anchor": "B1 §1.3 ¶\"Supervisory architecture and qualifications. FIELDWISE\" s3-s4 (pp. 26-27); B2 §5.2 table row \"Role and profile of supervisor\" (p. 36)"
      },
      "evidence": "His expertise in plant physiology, abiotic stress, including drought, and stress metabolomics anchors interpretation of plant water-stress responses, the physiological-validation framework and the measurement programme.",
      "description": "The supervisors' qualifications are asserted rather than evidenced: no record of PhD or postdoctoral supervision and no named international collaborations are given; supporting outputs are one cited paper each for the modelling and Earth-observation supervisors, and the primary supervisor's outputs appear only in Part A.",
      "score_impact_estimate": -0.3,
      "watchlist_ref": "W16"
    },
    {
      "finding_id": "F-07",
      "criterion": "excellence",
      "aspect_id": "exc-supervision",
      "severity": "minor",
      "location": {
        "part": "B1",
        "section": "1.3",
        "pdf_page": 27,
        "anchor": "B1 §1.3 ¶\"Planned training activities and ELTE secondment.\" s6 (p. 27)"
      },
      "evidence": "Guest lectures and practical activities at MATE and, where feasible, Agricultural University–Plovdiv build on previous university teaching experience.",
      "description": "Training is described by topic only, without named courses, providers or timing; teaching in Plovdiv is conditional; the arrangements for primary supervision during the first secondment block (M1-M3), which coincides with the protocol lock and model freeze, are not described.",
      "score_impact_estimate": -0.05,
      "watchlist_ref": "W17"
    },
    {
      "finding_id": "F-08",
      "criterion": "excellence",
      "aspect_id": "exc-researcher",
      "severity": "minor",
      "location": {
        "part": "B1",
        "section": "1.4",
        "pdf_page": 28,
        "anchor": "B1 §1.4 ¶\"A profile matched to the\" s7 (p. 28); B2 §4 \"Selected relevant research outputs\" (pp. 34-35)"
      },
      "evidence": "Her experience includes agricultural data work at Kleffmann Group Bulgaria, formal upskill training in Artificial Intelligence, Data Science, Machine Learning and Python, and practical use of R, QGIS, Google Earth Engine, SNAP and satellite/UAV data.",
      "description": "The researcher's water-stress and Earth-observation outputs are limited to one 2025 proceedings paper (watermelon) and two manuscripts under review; the data-science training is unnamed, the Kleffmann employment is undated and the existing DrR prototype is not documented (repository, version, implemented functions).",
      "score_impact_estimate": -0.15,
      "watchlist_ref": "W18"
    },
    {
      "finding_id": "F-09",
      "criterion": "excellence",
      "aspect_id": "exc-researcher",
      "severity": "minor",
      "location": {
        "part": "B2",
        "section": "4",
        "pdf_page": 34,
        "anchor": "B2 §4 list \"Professional experience\" bullets 1-3 (p. 34); ¶\"Career break\" (p. 35)"
      },
      "evidence": "Chief Assistant Professor, MVCRI, Plovdiv: abiotic-stress physiology, vegetable-crop phenotyping, field experimentation and non-destructive stress assessment. … Full-time parenting career break: 34 months (2021–2024).",
      "description": "The CV omits the template's minimum content: no dd/mm/yyyy dates for professional experience, education or the career break; the current position and the Kleffmann employment are undated; outputs carry no significance or open-access notes; invited presentations, funding and supervision/mentoring are not listed (or marked 'none').",
      "score_impact_estimate": -0.05,
      "watchlist_ref": "W2"
    },
    {
      "finding_id": "F-10",
      "criterion": "excellence",
      "aspect_id": "exc-researcher",
      "severity": "minor",
      "location": {
        "part": "B1",
        "section": "1.4",
        "pdf_page": 28,
        "anchor": "B1 §1.4 ¶\"A profile matched to the\" s9 (p. 28); B2 §4 list \"Education and research qualifications\" bullet 4 (p. 34)"
      },
      "evidence": "She holds an EU A1/A3 drone-pilot qualification, is holding Environmental Engineering Master’s degree, and has independently developed the pre-existing DrR – Digital Agronomist desktop research prototype. … Second MSc studies in Environmental Engineering (2025–2026), strengthening environmental-systems and geospatial competences.",
      "description": "Section 1.4 states that the researcher holds an Environmental Engineering Master's degree, whereas the CV lists it as ongoing studies (2025-2026); held or in progress is undetermined. Scored within F-09.",
      "score_impact_estimate": 0.0,
      "watchlist_ref": "W4"
    },
    {
      "finding_id": "F-11",
      "criterion": "impact",
      "aspect_id": "imp-magnitude",
      "severity": "major",
      "location": {
        "part": "B1",
        "section": "2.3",
        "pdf_page": 30,
        "anchor": "B1 §2.3 table \"Dimension\" row \"European & societal\" (p. 30); ¶\"Impact is measured through project-controlled\" s5 (p. 30)"
      },
      "evidence": "The funded magnitude is intentionally realistic: one development crop, one large commercial validation environment across two seasons, one validated web MVP and one external industrial evaluation.",
      "description": "The magnitude of the contribution is not quantified: no irrigated processing-tomato or horticultural area, no number of growers or FMIS users, no size of the software partner's farmer network, no link to European water or agricultural policy frames or to the work programme's expected impacts; the 'European & societal' row is generic.",
      "score_impact_estimate": -0.5,
      "watchlist_ref": "W21"
    },
    {
      "finding_id": "F-12",
      "criterion": "impact",
      "aspect_id": "imp-dissemination",
      "severity": "major",
      "location": {
        "part": "B1",
        "section": "2.2",
        "pdf_page": 29,
        "anchor": "B1 §2.2 table \"Strand\" row \"Communication\" (p. 29)"
      },
      "evidence": "Practitioner demonstrations of stress probability, uncertainty and irrigation-attention outputs; public-facing articles; farmer/end-user workshop; institutional and public-engagement activities.",
      "description": "The communication strategy lacks the main messages, tools, channels and timing per target group that the template requires; 'public-facing articles', a workshop and 'institutional and public-engagement activities' are listed without specification and 'reach indicators' are undefined.",
      "score_impact_estimate": -0.35,
      "watchlist_ref": "W20"
    },
    {
      "finding_id": "F-13",
      "criterion": "impact",
      "aspect_id": "imp-career",
      "severity": "minor",
      "location": {
        "part": "B1",
        "section": "2.1",
        "pdf_page": 28,
        "anchor": "B1 §2.1 table \"Measure\" row \"Transferable-skills portfolio\" (p. 28) and row \"Scientific visibility and leadership\" (p. 29)"
      },
      "evidence": "Research integrity, FAIR/open science, responsible AI use, grant writing, IP/exploitation, project management and science communication, exercised directly through FIELDWISE.",
      "description": "Leadership, grant writing and network building are listed as skills but not converted into measures (no planned grant application, network membership or mentoring role); teaching in Plovdiv is conditional ('where feasible', Section 1.3).",
      "score_impact_estimate": -0.2,
      "watchlist_ref": "W19"
    },
    {
      "finding_id": "F-14",
      "criterion": "impact",
      "aspect_id": "imp-career",
      "severity": "minor",
      "location": {
        "part": "B1",
        "section": "1.3",
        "pdf_page": 27,
        "anchor": "B1 §1.3 ¶\"Structured supervision and governance. Supervision\" s1 (p. 27); §2.1 table \"Measure\" row \"Career Development Plan\" cell Evidence (p. 28); §3.1 ¶\"Lead: fellow/ATK; supervisors and host\" T5.1 (p. 31)"
      },
      "evidence": "…monthly written progress monitoring and quarterly Career Development Plan reviews. … D5.1 (M3); reviews M3/M12/M21/M24/M27; K11",
      "description": "The Career Development Plan review cadence is inconsistent: quarterly reviews in Sections 1.3 and 3.1 against reviews at months 3, 12, 21, 24 and 27 in the Section 2.1 table.",
      "score_impact_estimate": -0.1,
      "watchlist_ref": null
    },
    {
      "finding_id": "F-15",
      "criterion": "impact",
      "aspect_id": "imp-dissemination",
      "severity": "minor",
      "location": {
        "part": "B1",
        "section": "2.2",
        "pdf_page": 30,
        "anchor": "B1 §2.2 ¶\"Reach and uptake are tracked\" s1 (p. 30); table \"Strand\" row \"Dissemination\" (p. 29)"
      },
      "evidence": "…AgroVIR operational assessment and monitoring of repository use after release.",
      "description": "Data and software as impact vehicles are unspecific: 'monitoring of repository use after release' names no repository, and no release plan (licence, identifier) exists for the harmonised archive or the prospective dataset D2.1, whose reuse rights depend on undetermined archive terms; dissemination venues are Earth-observation and precision-agriculture forums only (EGU/ECPA), with no horticultural or irrigation-science forum.",
      "score_impact_estimate": -0.15,
      "watchlist_ref": null
    },
    {
      "finding_id": "F-16",
      "criterion": "implementation",
      "aspect_id": "impl-host",
      "severity": "major",
      "location": {
        "part": "B1",
        "section": "3.2",
        "pdf_page": 33,
        "anchor": "B1 §3.2 table \"Organisation\" rows \"MATE\", \"Krumatic EOOD\", \"Commercial farmer/producer\" (p. 33); B2 §5.1 ¶\"Only formal MSCA participating organisations\" (p. 35)"
      },
      "evidence": "Data access and permitted reuse are documented before analysis and exploitation. … Only formal MSCA participating organisations are listed.",
      "description": "Four of the seven organisations in the capacity table (archive owner MATE, contractor Krumatic, the unnamed commercial farmer and MVCRI) hold no formal role although O1-O3 depend on the archive and the commercial field; access is 'documented before analysis', which describes a procedure; no existing agreement, letter or commitment is stated; field size, irrigation system and treatment layout are not described.",
      "score_impact_estimate": -0.4,
      "watchlist_ref": "W24"
    },
    {
      "finding_id": "F-17",
      "criterion": "implementation",
      "aspect_id": "impl-workplan",
      "severity": "major",
      "location": {
        "part": "B1",
        "section": "3.1",
        "pdf_page": 31,
        "anchor": "B1 §3.1 ¶\"Lead: fellow/ATK; MATE and ELTE\" T1.1-T1.3 (p. 31); Gantt rows \"WP1 model / synthesis\" and \"ELTE secondment\" (p. 32)"
      },
      "evidence": "T1.2 (M1–M3): harmonise predictors and lock the physiological reference, folds, metrics, sampling and recalibration rules before fitting. T1.3 (M2–M3): build the pipeline; after protocol lock, fit and freeze the model/benchmark.",
      "description": "Months 1-3 concentrate the audit and harmonisation of five archive seasons, protocol lock, pipeline construction, fitting and freeze, field-access agreements (T2.1), the IP/architecture agreement (T3.1), the CDP and the initial dissemination strategy, all during the first ELTE block; the feasibility of this concurrency and the 5.0 PM assigned to WP1 (about 3 PM before the freeze, 2 PM of synthesis after it) are not justified.",
      "score_impact_estimate": -0.4,
      "watchlist_ref": "W10"
    },
    {
      "finding_id": "F-18",
      "criterion": "implementation",
      "aspect_id": "impl-workplan",
      "severity": "major",
      "location": {
        "part": "B1",
        "section": "3.1",
        "pdf_page": 32,
        "anchor": "B1 §3.1 ¶\"Critical path: MS1 model freeze\" s3 (p. 32); table \"Risk; likelihood/impact\" row \"R2\" (p. 32)"
      },
      "evidence": "The crop calendar must place MS1 before season 1 and the second harvest by M20.",
      "description": "Season 1 (T2.2, M4-M12) and season 2 (T2.3, M13-M20, second harvest by M20) fit the Hungarian processing-tomato calendar only for a start in a narrow window; the proposal states the constraint but gives no assumed start month and no contingency for a start outside the transplanting window; R2 presupposes a calendar-compatible start.",
      "score_impact_estimate": -0.3,
      "watchlist_ref": "W9"
    },
    {
      "finding_id": "F-19",
      "criterion": "implementation",
      "aspect_id": "impl-host",
      "severity": "minor",
      "location": {
        "part": "A",
        "section": "2",
        "pdf_page": 4,
        "anchor": "A p.4 2 - Participants > List of participating organisations (p. 4); B2 §5.1 table \"Organisation role\" row \"Associated partner for secondment\" (p. 35)"
      },
      "evidence": "1 HUN-REN Agrartudomanyi Kutatokozpont Hungary Coordinator; 2 AGROVIR Uzletviteli Tanacsado Korlatolt Felelossegu Tarsasag Hungary Associated … Associated partner for secondment 999896468 ELTE Y Hungary Prof. András Jung",
      "description": "Part A lists two participating organisations while Part B-2 table 5.1 lists ELTE, which hosts twelve of the twenty-four months, as a formal participant with a PIC; the secondment arrangement is not anchored in the administrative forms.",
      "score_impact_estimate": -0.1,
      "watchlist_ref": "W1"
    },
    {
      "finding_id": "F-20",
      "criterion": "implementation",
      "aspect_id": "impl-host",
      "severity": "minor",
      "location": {
        "part": "B1",
        "section": "3.2",
        "pdf_page": 33,
        "anchor": "B1 §3.2 table \"Organisation\" row \"HUN-REN ATK\" s5 (p. 33); B2 §5.2 row \"Key research facilities\" (p. 36)"
      },
      "evidence": "ATK provides the scientific environment, infrastructure, workspace, administration and project support required throughout the action.",
      "description": "Hosting arrangements are generic: no description of team integration, onboarding, contractual, HR or relocation support, and no computing or Earth-observation data infrastructure described at the beneficiary.",
      "score_impact_estimate": -0.1,
      "watchlist_ref": "W23"
    },
    {
      "finding_id": "F-21",
      "criterion": "implementation",
      "aspect_id": "impl-workplan",
      "severity": "minor",
      "location": {
        "part": "B1",
        "section": "3.1",
        "pdf_page": 32,
        "anchor": "B1 §3.1 table \"Risk; likelihood/impact\" rows R1-R6 (p. 32)"
      },
      "evidence": "R1 | WP1 | M/H … R2 | WP2 | M/H … R3 | WP2 | M/H … R4 | WP1–2 | M/H … R5 | WP2–3 | M/H … R6 | WP3–5 | M/M",
      "description": "The risk register rates five of six risks identically (M/H) and omits farm commitment, archive reuse rights, AgroVIR withdrawal and supervisor or secondment availability.",
      "score_impact_estimate": -0.1,
      "watchlist_ref": "W22"
    },
    {
      "finding_id": "F-22",
      "criterion": "implementation",
      "aspect_id": "impl-workplan",
      "severity": "minor",
      "location": {
        "part": "B1",
        "section": "3.1",
        "pdf_page": 31,
        "anchor": "B1 §3.1 ¶\"The fellow leads the scientific work\" s4 (p. 31); A p.16 3 - Budget > Research, training and networking costs (p. 16)"
      },
      "evidence": "MATE supplies archive/irrigation expertise; the producer hosts field trials; Krumatic supplies remunerated engineering.",
      "description": "No resource plan links remunerated software engineering, soil-water and meteorological monitoring, UAV acquisition, conferences and open-access fees to the requested contributions (research, training and networking contribution EUR 30,000 over 30 months) or to any other source.",
      "score_impact_estimate": -0.05,
      "watchlist_ref": "W8"
    },
    {
      "finding_id": "F-23",
      "criterion": "implementation",
      "aspect_id": "impl-workplan",
      "severity": "minor",
      "location": {
        "part": "B1",
        "section": "3.1",
        "pdf_page": 31,
        "anchor": "B1 §3.1 ¶\"D1.1 archive/QC map (M2)\" s1 (p. 31); §1.1 ¶\"archive and establish the water-stress reference\" (pp. 24-25); Gantt rows \"Deliverables A/B\" (p. 32)"
      },
      "evidence": "D1.1 archive/QC map (M2); D1.2 protocol and D1.4 model/card (M3); D1.5 transfer specification (M21).",
      "description": "Deliverable numbering has a gap: D1.1, D1.2, D1.4 and D1.5 exist; D1.3 appears nowhere in Sections 1.1, 3.1 or the Gantt.",
      "score_impact_estimate": -0.05,
      "watchlist_ref": "W5"
    },
    {
      "finding_id": "F-24",
      "criterion": "formal",
      "aspect_id": "impl-host",
      "severity": "minor",
      "location": {
        "part": "A",
        "section": "4",
        "pdf_page": 17,
        "anchor": "A p.17 4 - Ethics & security > Ethics Issues Table > 2. Humans / 4. Personal data (p. 17)"
      },
      "evidence": "Does this activity involve human participants? No … Does this activity involve processing of personal data? No",
      "description": "The ethics table answers 'No' to human participants and to personal-data processing, while the self-assessment (pp. 19-20) and Part B-2 Section 6 describe voluntary grower and user feedback under informed consent and personal data processed under GDPR with pseudonymisation. Not scored by the panel; ethics-screening consistency.",
      "score_impact_estimate": 0.0,
      "watchlist_ref": "W7"
    },
    {
      "finding_id": "F-25",
      "criterion": "formal",
      "aspect_id": "impl-host",
      "severity": "minor",
      "location": {
        "part": "B2",
        "section": "4-8",
        "pdf_page": 34,
        "anchor": "B2 footer pp. 34-37"
      },
      "evidence": "Part B - Page 3 of [Page limit]",
      "description": "The Part B-2 footer carries an unreplaced template placeholder and its numbering starts at 3. Cosmetic.",
      "score_impact_estimate": 0.0,
      "watchlist_ref": "W3"
    },
    {
      "finding_id": "F-26",
      "criterion": "formal",
      "aspect_id": "impl-host",
      "severity": "minor",
      "location": {
        "part": "A",
        "section": "2",
        "pdf_page": 8,
        "anchor": "A p.8 Researcher > Current Department/Faculty/Institute/Laboratory name (p. 8); A p.15 AgroVIR achievements and infrastructure (p. 15); A p.13 AgroVIR Departments (p. 13)"
      },
      "evidence": "Plant physyology … Precision Decision Centre, SMART-GAZDA, Bonafarm G … satellite-map use, navigation and excha",
      "description": "Part A free-text fields contain a typo and two truncations at the field limit; the AgroVIR department block is empty. Cosmetic.",
      "score_impact_estimate": 0.0,
      "watchlist_ref": "W6"
    },
    {
      "finding_id": "F-27",
      "criterion": "formal",
      "aspect_id": "impl-host",
      "severity": "minor",
      "location": {
        "part": "B2",
        "section": "5.1",
        "pdf_page": 35,
        "anchor": "B2 §5.1 ¶\"Only formal MSCA participating organisations\" (p. 35)"
      },
      "evidence": "Only formal MSCA participating organisations are listed. MATE contributes the historical archive and scientific expertise; Krumatic provides remunerated software-engineering support; the commercial farmer/producer hosts and implements the agreed field-trial irrigation regimes; and MVCRI is a post-MSCA continuation route.",
      "description": "Part B-2 Section 5 contains no declaration of inter-relationships between participating organisations and individuals, although the CV shows co-authorship with MATE (Takács) and MVCRI (Ganeva) staff named in Section 3.2. Template item; not scored.",
      "score_impact_estimate": 0.0,
      "watchlist_ref": null
    },
    {
      "finding_id": "F-28",
      "criterion": "formal",
      "aspect_id": "impl-host",
      "severity": "minor",
      "location": {
        "part": "A",
        "section": "4",
        "pdf_page": 18,
        "anchor": "A p.18 Ethics Issues Table > 8. Artificial intelligence > Page (p. 18)"
      },
      "evidence": "Does this activity involve the development, deployment and/or use of Artificial Intelligence-based systems? Yes 6",
      "description": "The page pointer '6' for the AI item does not match where AI is discussed (Part A pp. 19-20; Part B-1 p. 26, i.e. Part B page 3); Part B-2 Section 6 does not mention AI. Not scored.",
      "score_impact_estimate": 0.0,
      "watchlist_ref": null
    },
    {
      "finding_id": "F-29",
      "criterion": "formal",
      "aspect_id": "exc-researcher",
      "severity": "minor",
      "location": {
        "part": "B2",
        "section": "4",
        "pdf_page": 35,
        "anchor": "B2 §4 ¶\"Career break\" (p. 35)"
      },
      "evidence": "Full-time parenting career break: 34 months (2021–2024).",
      "description": "The career break is stated in months and years only; eligibility on research experience holds even without the deduction (5.90 years elapsed since 14/10/2020), but the applicant is to double-check that the break can be documented if requested. Not scored (fair treatment of the break); the CV format aspect is scored in F-09.",
      "score_impact_estimate": 0.0,
      "watchlist_ref": null
    }
  ],
  "revision_actions": [
    {
      "action_id": "A-01",
      "finding_ids": [
        "F-19"
      ],
      "priority": "P0",
      "target_document": "PART_A_PORTAL",
      "anchor": "A p.4 2 - Participants > List of participating organisations (p. 4)",
      "action_class": "portal_admin",
      "instruction": "In the submission wizard add Eötvös Loránd University (ELTE, PIC 999896468) as an associated partner (associated partner for secondment), so that Part A lists the same three organisations as Part B-2 table 5.1. Do this only after the operator has confirmed with the Guide for Applicants / NCP that secondment hosts are registered in Part A for European Fellowships.",
      "proposed_text": null,
      "page_budget_delta_lines": 0,
      "compensating_cut": null,
      "owner": "operator",
      "fallback": "If the Guide does not require the secondment host in Part A, leave Part A unchanged; Part B-2 table 5.1 already states the role and PIC.",
      "ripple": [
        "Part A participant list and any participant-specific pages generated by the wizard",
        "Part B-2 §5.1 unchanged (already lists ELTE)"
      ],
      "verification": "Regenerated Part A p. 4 lists 3 organisations (ATK Coordinator, ELTE Associated, AgroVIR Associated); PIC 999896468 appears in Part A; Part B-2 §5.1 unchanged.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.1 on Implementation"
    },
    {
      "action_id": "A-02",
      "finding_ids": [
        "F-10"
      ],
      "priority": "P1",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §1.4 ¶\"A profile matched to the\" s9 (p. 28)",
      "action_class": "needs_fact",
      "instruction": "Replace the clause 'is holding Environmental Engineering Master’s degree' with the confirmed status, worded identically to the CV.",
      "proposed_text": "[OWNER-CONFIRM: holds an MSc in Environmental Engineering (awarded dd/mm/yyyy) | is completing an Environmental Engineering MSc (2025–2026)]",
      "page_budget_delta_lines": 0,
      "compensating_cut": null,
      "owner": "fellow",
      "fallback": "Use the CV wording (studies in progress, 2025–2026), the weaker of the two statements already in the PDF.",
      "ripple": [
        "B2 §4 list \"Education and research qualifications\" bullet 4 (p. 34): same status and dates (dd/mm/yyyy if awarded)"
      ],
      "verification": "grep 'Environmental Engineering' in B-1 and B-2 returns the same status in both; 'is holding' count = 0; §1.4 paragraph line count unchanged.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.0 (consistency; removes an inconsistency the panel reads as carelessness)"
    },
    {
      "action_id": "A-03",
      "finding_ids": [
        "F-23"
      ],
      "priority": "P1",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §3.1 ¶\"D1.1 archive/QC map (M2)\" s1 (p. 31)",
      "action_class": "editorial",
      "instruction": "Renumber D1.4 → D1.3 and D1.5 → D1.4 everywhere: §1.1 O2 '(D1.4)' (p. 24), §1.2 'D1.4 includes a model card' (p. 26), §2.1 table row 'ATK scientific and modelling training' cell Evidence 'D1.4' (p. 28), §2.2 table row 'Dissemination' cell Evidence 'D1.4 M3' (p. 29), §3.1 WP1 deliverable line (p. 31), Gantt labels '1.2/4' → '1.2/3' and '1.5' → '1.4' (p. 32).",
      "proposed_text": "D1.1 archive/QC map (M2); D1.2 protocol and D1.3 model/card (M3); D1.4 transfer specification (M21).",
      "page_budget_delta_lines": 0,
      "compensating_cut": null,
      "owner": "operator",
      "fallback": "If the Gantt image cannot be re-rendered, leave the numbering unchanged everywhere (a consistent gap is better than a text/Gantt mismatch).",
      "ripple": [
        "Gantt image p. 32 (re-render)",
        "§1.1 p. 24",
        "§1.2 p. 26",
        "§2.1 table p. 28",
        "§2.2 table p. 29"
      ],
      "verification": "grep -c 'D1.5' in B-1 = 0; grep -c 'D1.3' ≥ 4; Gantt row 'Deliverables B' shows '1.2/3; 5.1' at M3 and '1.4; 2.2' at M21; B-1 page count = 10.",
      "effort": "M",
      "regression_risk": "medium",
      "expected_gain": "+0.05 on Implementation"
    },
    {
      "action_id": "A-04",
      "finding_ids": [
        "F-14"
      ],
      "priority": "P1",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §2.1 table \"Measure\" row \"Career Development Plan\" cell Evidence (p. 28)",
      "action_class": "editorial",
      "instruction": "Harmonise the review cadence with §1.3 and T5.1 by stating both facts already in the PDF in the Evidence cell; leave §1.3 and §3.1 unchanged.",
      "proposed_text": "D5.1 (M3); quarterly reviews; gate reviews M12/M21/M24/M27; K11",
      "page_budget_delta_lines": 0,
      "compensating_cut": null,
      "owner": "operator",
      "fallback": "n/a (editorial)",
      "ripple": [],
      "verification": "grep 'quarterly' in B-1 returns §1.3, §2.1 table and T5.1; the row height is governed by the middle cell (4 lines), so the table does not grow; B-1 page count = 10.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.05 on Impact"
    },
    {
      "action_id": "A-05",
      "finding_ids": [
        "F-09",
        "F-29"
      ],
      "priority": "P1",
      "target_document": "PART_B2_DOCX",
      "anchor": "B2 §4 list \"Education and research qualifications\" and list \"Professional experience\" (p. 34); ¶\"Career break\" (p. 35)",
      "action_class": "needs_fact",
      "instruction": "Give every education and professional-experience entry full consecutive dates (dd/mm/yyyy–dd/mm/yyyy), consistent with Part A: PhD award 14/10/2020 (Part A p. 8); date the MVCRI position, the Kleffmann employment and the assistant professorship; date the career break; add a one-clause significance note and the open-access status to each listed output; add the template categories that are absent with an entry or 'none' (invited presentations, conference organisation, prizes/awards, funding, supervising/mentoring).",
      "proposed_text": "• PhD in Plant Physiology, Agricultural University of Plovdiv, awarded 14/10/2020. … • Chief Assistant Professor, MVCRI, Plovdiv, [OWNER-CONFIRM: dd/mm/yyyy]–present … • Assistant Professor …, Agricultural University of Plovdiv, [OWNER-CONFIRM: dd/mm/yyyy]–[OWNER-CONFIRM: dd/mm/yyyy] … • Agricultural data work, Kleffmann Group Bulgaria, [OWNER-CONFIRM: dd/mm/yyyy]–[OWNER-CONFIRM: dd/mm/yyyy] … Career break: full-time parenting, [OWNER-CONFIRM: dd/mm/yyyy]–[OWNER-CONFIRM: dd/mm/yyyy] (34 months). … Invited presentations: [OWNER-CONFIRM: list | none]. Funding: [OWNER-CONFIRM: list | none]. Supervising/mentoring: [OWNER-CONFIRM: list | none]. Each output: [OWNER-CONFIRM: one-clause significance]; open access: [OWNER-CONFIRM: yes/no].",
      "page_budget_delta_lines": 0,
      "compensating_cut": null,
      "owner": "fellow",
      "fallback": "Insert only the PhD award date from Part A (14/10/2020) and the fixed 34-month duration; leave the other entries as sealed.",
      "ripple": [
        "Part A p. 9 residence table must remain consistent with any dated stay abroad",
        "A-02 (MSc status)"
      ],
      "verification": "Every bullet under Education and Professional experience contains two dd/mm/yyyy dates (or one date and 'present'); the career-break line contains two dd/mm/yyyy dates; every publication entry ends with an open-access flag; the three added categories are present.",
      "effort": "M",
      "regression_risk": "low",
      "expected_gain": "+0.1 on Excellence"
    },
    {
      "action_id": "A-06",
      "finding_ids": [
        "F-24",
        "F-28"
      ],
      "priority": "P1",
      "target_document": "PART_A_PORTAL",
      "anchor": "A p.17 4 - Ethics & security > Ethics Issues Table > 2. Humans and 4. Personal data (p. 17); A p.18 > 8. Artificial intelligence > Page (p. 18)",
      "action_class": "needs_decision",
      "instruction": "Decide whether the voluntary grower/advisor/software-user feedback (self-assessment pp. 19–20, Part B-2 §6) constitutes involvement of human participants and processing of personal data. If yes, set both answers to Yes and enter the self-assessment page; if no, leave the table and keep the self-assessment. In both cases replace the AI page pointer '6' with the Part B-1 page where AI is discussed (Part B page 3) or with the self-assessment page.",
      "proposed_text": "[OWNER-CONFIRM: Humans = Yes/No; Personal data = Yes/No; AI page pointer = 3 (Part B-1) | self-assessment page]",
      "page_budget_delta_lines": 0,
      "compensating_cut": null,
      "owner": "operator",
      "fallback": "Leave the table as sealed; the self-assessment already describes consent, data minimisation and GDPR compliance, and the panel does not score the ethics table.",
      "ripple": [
        "Ethics self-assessment text unchanged",
        "Part B-2 §6 unchanged"
      ],
      "verification": "Ethics table answers match the self-assessment narrative; the AI page pointer resolves to a page that mentions AI.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.0 (not scored; ethics-screening consistency)"
    },
    {
      "action_id": "A-07",
      "finding_ids": [
        "F-06"
      ],
      "priority": "P2",
      "target_document": "PART_B2_DOCX",
      "anchor": "B2 §5.2 table (Beneficiary) row \"Role and profile of supervisor\" (p. 36)",
      "action_class": "editorial",
      "instruction": "Append to the supervisor-profile cell the supervisory team's outputs already listed in Part A p. 11, with the same descriptors.",
      "proposed_text": "Recent outputs of the supervisory team: Janda et al., 2025, Scientific Reports (water-deficit physiology; chlorophyll fluorescence, stomatal conductance, SPAD); Szalai et al., 2025, Plant Physiology and Biochemistry (whole-plant abiotic-stress physiology); Li et al., 2026, Nature Plants (plant signalling and stress-response physiology); Hollós et al., 2026, Geoscientific Model Development (machine learning, leave-one-year-out validation, independent testing, SHAP); Birinyi et al., 2024, Remote Sensing (EO-based maize condition mapping).",
      "page_budget_delta_lines": 0,
      "compensating_cut": null,
      "owner": "operator",
      "fallback": "n/a (editorial; facts in Part A p. 11)",
      "ripple": [
        "B1 §1.3 unchanged unless A-18 is applied"
      ],
      "verification": "grep 'Scientific Reports' and 'Geoscientific Model Development' in B-2 §5.2 each return 1; descriptors identical to Part A p. 11.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.1 on Excellence"
    },
    {
      "action_id": "A-08",
      "finding_ids": [
        "F-08"
      ],
      "priority": "P2",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §1.4 ¶\"A profile matched to the\" s7 (p. 28), after '…satellite/UAV data.'",
      "action_class": "editorial",
      "instruction": "Insert one sentence naming the two under-review tomato water-stress manuscripts and the MATE training stays already listed in Part B-2 §4 (+3 lines). Pay for it with CUT-1: delete §1.1 ¶\"Pertinence. Three linked scientific\" s4–s5 ('These objectives also advance the fellow … inter-sectoral profile.', −3 lines), which duplicates §2.1.",
      "proposed_text": "Two manuscripts under review document her recent water-stress and Earth-observation work: evapotranspiration estimation in tomato fields from multispectral and thermal UAV data, and proximal hyperspectral signatures of water stress in processing tomato validated against physiology and soil water, co-authored with the MATE and MVCRI colleagues named in Section 3.2 (Part B-2, Section 4).",
      "page_budget_delta_lines": 0,
      "compensating_cut": "B1 §1.1 ¶\"Pertinence. Three linked scientific\" s4–s5 (p. 24): 'These objectives also advance the fellow … inter-sectoral profile.' (−3 lines)",
      "owner": "operator",
      "fallback": "n/a (editorial; facts in Part B-2 pp. 34–35)",
      "ripple": [
        "§1.1 'Pertinence' paragraph shrinks from 9 to 6 lines; pages 24–28 reflow by −3/+3 lines"
      ],
      "verification": "grep 'Proximal Hyperspectral Signatures' in B-1 §1.4 (case-insensitive) = 1; grep 'These objectives also advance the fellow' = 0; Part B page 5 still starts with '…based stress assessment' or later; B-1 page count = 10.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.1 on Excellence"
    },
    {
      "action_id": "A-09",
      "finding_ids": [
        "F-17"
      ],
      "priority": "P2",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §1.1 ¶\"Realistically achievable. FIELDWISE combines\" s2 (p. 25), after '…support feasibility.'",
      "action_class": "editorial",
      "instruction": "Insert one sentence establishing that familiarity with the MATE archive predates the action (facts in Part B-2 §4), which addresses the credibility of the M1–M3 audit-to-freeze sequence (+3 lines). Pay for it with CUT-7: delete §2.3 ¶\"Impact is measured through project-controlled\" s3 ('Delivery is tracked through K1–K14, … implementation.', −3 lines), which duplicates §3.1.",
      "proposed_text": "Familiarity with the archive predates the action: the fellow completed a COST PANGEOS Short-Term Scientific Mission and Erasmus+ RGB/hyperspectral training at MATE in 2025 and co-authored, with Dr Takács, a manuscript under review on proximal hyperspectral signatures of water stress in processing tomato (Part B-2, Section 4).",
      "page_budget_delta_lines": 0,
      "compensating_cut": "B1 §2.3 ¶\"Impact is measured through project-controlled\" s3 (p. 30): 'Delivery is tracked through K1–K14, … implementation.' (−3 lines)",
      "owner": "operator",
      "fallback": "n/a (editorial; facts in Part B-2 pp. 34–35)",
      "ripple": [
        "§2.3 closing paragraph shrinks by 3 lines; Part B page 7 gains slack"
      ],
      "verification": "grep 'Familiarity with the archive predates' in B-1 = 1; grep 'Delivery is tracked through K1' = 0; §3 still starts at the top of Part B page 8; B-1 page count = 10.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.05 on Implementation"
    },
    {
      "action_id": "A-10",
      "finding_ids": [
        "F-21",
        "F-16"
      ],
      "priority": "P2",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §3.1 table \"Risk; likelihood/impact\" after row \"R6\" (p. 32)",
      "action_class": "editorial",
      "instruction": "Add a seventh risk row for partner and access failure, built only from mitigations already in the plan (R2 backup site by M3; T5.2 access rules from M1; T3.1 AgroVIR requirements M1–M3; MS4 placement-scope decision) (+3 lines). Pay for it with CUT-5 (delete 'Required administrative outputs: … two years later.' at the end of the WP5 paragraph, pp. 31–32, −2 lines) and CUT-14 (delete §3.1 ¶\"The fellow leads the scientific work\" s2 'Five WPs connect … career development.', −1 line). Do not touch the Gantt.",
      "proposed_text": "R7 | WP2–4 | M/H — Partner or access failure (producer field, MATE archive reuse, AgroVIR requirements/placement): backup site and access documentation agreed by M3 (T2.1, T5.2); AgroVIR requirements reviews from M1 (T3.1); placement scope re-confirmed at MS4. Owner: fellow/ATK.",
      "page_budget_delta_lines": 0,
      "compensating_cut": "B1 §3.1 ¶\"D5.1 CDP (M3); D5.2 DMP\" last sentence 'Required administrative outputs: … two years later.' (pp. 31–32, −2 lines) + B1 §3.1 ¶\"The fellow leads the scientific work\" s2 (p. 31, −1 line)",
      "owner": "operator",
      "fallback": "n/a (editorial; all mitigations already in the PDF)",
      "ripple": [
        "Part B page 9 must still end with the Gantt; if the Gantt moves to page 10, revert CUT-14 first, then the row"
      ],
      "verification": "Risk table has 7 rows; grep 'Required administrative outputs' = 0; the Gantt is still on Part B page 9; B-1 page count = 10.",
      "effort": "S",
      "regression_risk": "medium",
      "expected_gain": "+0.1 on Implementation"
    },
    {
      "action_id": "A-11",
      "finding_ids": [
        "F-18"
      ],
      "priority": "P3",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §3.1 ¶\"Critical path: MS1 model freeze\" s3 (p. 32)",
      "action_class": "needs_decision",
      "instruction": "Extend the crop-calendar sentence with the assumed start window and the slipped-start contingency decided by the fellow and the host (+2 lines). Pay for it with CUT-15 (condense the WP5 'Lead:' paragraph on p. 31 to three lines, −1) and CUT-16 (condense K5 in the WP2 deliverable paragraph on p. 31, −1).",
      "proposed_text": "The crop calendar must place MS1 before season 1 and the second harvest by M20; the plan assumes a start between [OWNER-CONFIRM: month] and [OWNER-CONFIRM: month], fixed at grant signature, and a start outside this window moves season 1 to the next transplanting window while T1.4 and T3.2 absorb the interval.",
      "page_budget_delta_lines": 0,
      "compensating_cut": "B1 §3.1 ¶\"Lead: fellow/ATK; supervisors and host\" (p. 31, condense to 3 lines, −1) + B1 §3.1 ¶\"D2.1 dataset/prediction log (M20)\" K5 clause 'all scheduled observation opportunities accounted for, with' (p. 31, −1)",
      "owner": "fellow",
      "fallback": "No change; the sealed sentence stands and the weakness remains.",
      "ripple": [
        "Risk row R2 wording ('Switch comparable site before the crop window') stays consistent",
        "Part B page 9 must still end with the Gantt"
      ],
      "verification": "grep 'the plan assumes a start between' in B-1 = 1 and contains no '[OWNER-CONFIRM' after the owner answers; the Gantt is still on Part B page 9; B-1 page count = 10.",
      "effort": "M",
      "regression_risk": "medium",
      "expected_gain": "+0.2 on Implementation"
    },
    {
      "action_id": "A-12",
      "finding_ids": [
        "F-11"
      ],
      "priority": "P2",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §2.3 table \"Dimension\" row \"European & societal\" (p. 30)",
      "action_class": "editorial",
      "instruction": "Rewrite the row so that it names the work-programme expected outcomes and impacts the action serves, using only facts in the PDF (Bulgarian fellow, Hungarian academic host, university secondment host, non-academic FMIS company placement, MVCRI return route, open-science outputs) (+1 line). Pay for it with CUT-8: delete §2.1 ¶\"By completion, the fellow will\" s3 ('The 12-month ELTE secondment adds … non-academic experience.', −1 line), which duplicates the table above it.",
      "proposed_text": "Contribution: a Bulgarian researcher trained in Hungary across an academic host, a university secondment host and a non-academic FMIS company, with a defined return route through MVCRI. Magnitude and importance: brain circulation and knowledge transfer across the ERA between two Member States; inter-sectoral mobility into the non-academic sector; open-science outputs (pre-specified protocol, model card, FAIR data, at least two open-access papers); a reusable transfer methodology applicable to further irrigated crops through MVCRI.",
      "page_budget_delta_lines": 0,
      "compensating_cut": "B1 §2.1 ¶\"By completion, the fellow will\" s3 (p. 29): 'The 12-month ELTE secondment adds … non-academic experience.' (−1 line)",
      "owner": "operator",
      "fallback": "n/a (editorial; work-programme terms and PDF facts only)",
      "ripple": [
        "§2.3 table row height grows by ~1 line; Part B page 7 has ~5 lines of slack"
      ],
      "verification": "grep 'brain circulation' in B-1 §2.3 = 1; grep 'The 12-month ELTE secondment adds' = 0; B-1 page count = 10.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.1 on Impact"
    },
    {
      "action_id": "A-13",
      "finding_ids": [
        "F-11"
      ],
      "priority": "P3",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §2.3 table \"Dimension\" row \"Agricultural & environmental\" cell \"Magnitude and importance\" (p. 30)",
      "action_class": "needs_fact",
      "instruction": "Append a quantified addressable target group to the cell (+2 lines). Pay for it with CUT-11 (delete §1.3 ¶\"Rationale and added value of the\" s6 'Commercially sensitive evaluation uses protected, coded or appropriately aggregated data.', −1) and CUT-12 (condense §1.2 ¶\"Stage 3 (WP3–WP4) operationalises only\" to one sentence, −1).",
      "proposed_text": "The addressable group comprises [OWNER-CONFIRM: n] farms and [OWNER-CONFIRM: ha] under AgroVIR farm-management software and [OWNER-CONFIRM: ha] of irrigated processing tomato in Hungary and Bulgaria [OWNER-CONFIRM: source]; the two validation seasons cover [OWNER-CONFIRM: ha] of it.",
      "page_budget_delta_lines": 0,
      "compensating_cut": "B1 §1.3 ¶\"Rationale and added value of the\" s6 (p. 27, −1) + B1 §1.2 ¶\"Stage 3 (WP3–WP4) operationalises only\" condensed to one sentence (p. 26, −1)",
      "owner": "partner:AgroVIR",
      "fallback": "Apply A-12 only; leave the cell as sealed (no invented figures).",
      "ripple": [
        "Part A abstract ('within its network of farmers') stays consistent",
        "A-14 communication reach figures use the same numbers"
      ],
      "verification": "The cell contains no '[OWNER-CONFIRM' after the owner answers and at least one numeral with a unit (farms or ha); B-1 page count = 10.",
      "effort": "M",
      "regression_risk": "low",
      "expected_gain": "+0.3 on Impact"
    },
    {
      "action_id": "A-14",
      "finding_ids": [
        "F-12"
      ],
      "priority": "P2",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §2.2 table \"Strand\" row \"Communication\" cell \"Measures and outputs\" (p. 29)",
      "action_class": "editorial",
      "instruction": "Restructure the cell by target group with main message, tool and timing, using only facts in the PDF (messages from §1.1–§2.3; the end-user workshop by M30 from K13; demonstrations during the M25–M30 placement; T5.3 strategy at M3) (+2 lines). Pay for it with CUT-13: delete §2.1 ¶\"FIELDWISE is designed to consolidate\" s2 ('The fellowship builds on competences … inter-sectoral exploitation.', −2 lines), which duplicates §1.4.",
      "proposed_text": "Growers and advisors (HU/BG) — message: when and where water stress needs attention, shown as stress probability with uncertainty, never beyond measured evidence; tools: practitioner demonstrations of the DrR outputs during the AgroVIR placement (M25–M30), one farmer/end-user workshop by M30 (K13), practitioner articles. Public — message: physiologically validated, open-science irrigation decision support; tools: institutional communication of HUN-REN ATK and ELTE, public-facing articles. Strategy documented at M3 (T5.3); reach indicators reported in D5.3.",
      "page_budget_delta_lines": 0,
      "compensating_cut": "B1 §2.1 ¶\"FIELDWISE is designed to consolidate\" s2 (p. 28): 'The fellowship builds on competences … inter-sectoral exploitation.' (−2 lines)",
      "owner": "operator",
      "fallback": "n/a (editorial; facts in the PDF)",
      "ripple": [
        "§2.1 opening paragraph shrinks from 6 to 4 lines; the §2.1 table may re-split across Part B pages 5–6 — check row integrity"
      ],
      "verification": "Communication cell contains 'M25–M30' and 'by M30 (K13)'; grep 'The fellowship builds on competences' = 0; §2.1 table rows intact; B-1 page count = 10.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.1 on Impact"
    },
    {
      "action_id": "A-15",
      "finding_ids": [
        "F-12"
      ],
      "priority": "P3",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §2.2 table \"Strand\" row \"Communication\" cell \"Evidence/timing\" (p. 29)",
      "action_class": "needs_fact",
      "instruction": "Replace 'Demonstrations, workshops, reach indicators' with named channels and reach targets supplied by the host and AgroVIR (+1 line). Pay for it with CUT-17: delete §2.2 ¶\"FIELDWISE uses a targeted strategy\" s2 ('Target groups are research communities, … wider public.', −2 lines), which the table repeats.",
      "proposed_text": "[OWNER-CONFIRM: n] demonstrations; workshop [OWNER-CONFIRM: month]; articles in [OWNER-CONFIRM: outlet]; channels [OWNER-CONFIRM: ATK/ELTE/AgroVIR channels]; reach ≥ [OWNER-CONFIRM: n] growers",
      "page_budget_delta_lines": -1,
      "compensating_cut": "B1 §2.2 ¶\"FIELDWISE uses a targeted strategy\" s2 (p. 29): 'Target groups are research communities, … wider public.' (−2 lines)",
      "owner": "host",
      "fallback": "Apply A-14 only; keep 'Demonstrations, workshops, reach indicators'.",
      "ripple": [
        "A-13 numbers, if any, reused for reach"
      ],
      "verification": "Evidence/timing cell contains at least one numeral and one named channel and no '[OWNER-CONFIRM'; B-1 page count = 10.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.1 on Impact"
    },
    {
      "action_id": "A-16",
      "finding_ids": [
        "F-13"
      ],
      "priority": "P2",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §2.1 table \"Measure\" row \"Scientific visibility and leadership\" cell \"Skills and employability mechanism\" (p. 29)",
      "action_class": "editorial",
      "instruction": "Name the network already in the PDF (COST Action CA22136 PANGEOS, Part B-2 §4) and the teaching venues (MATE; Agricultural University–Plovdiv) as the concrete network and teaching measures (+1 line). Pay for it with CUT-12 if not already used by A-13; otherwise with CUT-20 (delete §1.3 ¶\"Two-way transfer of knowledge. FIELDWISE\" s1, −1 line).",
      "proposed_text": "Co-authored publications, conference presentations, seminars and guest lectures at MATE and the Agricultural University–Plovdiv, and continued participation in COST Action CA22136 PANGEOS strengthen international visibility, communication, network building and future supervision capacity.",
      "page_budget_delta_lines": 0,
      "compensating_cut": "B1 §1.3 ¶\"Two-way transfer of knowledge. FIELDWISE\" s1 (p. 27): 'FIELDWISE connects internationally recognised … expertise.' (−1 line)",
      "owner": "operator",
      "fallback": "n/a (editorial; PANGEOS and the teaching venues are in the PDF)",
      "ripple": [
        "§1.3 'Two-way transfer' paragraph loses its opening sentence; the paragraph still names both directions of transfer"
      ],
      "verification": "grep 'PANGEOS' in B-1 §2.1 = 1; grep 'FIELDWISE connects internationally recognised' = 0; B-1 page count = 10.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.05 on Impact"
    },
    {
      "action_id": "A-17",
      "finding_ids": [
        "F-13"
      ],
      "priority": "P3",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §2.1 table \"Measure\" row \"Transferable-skills portfolio\" cell \"Evidence\" (p. 28)",
      "action_class": "needs_decision",
      "instruction": "Turn grant writing and mentoring into dated commitments if the fellow and supervisor agree (+1 line within the existing cell height; no cut needed if the middle cell remains the tallest).",
      "proposed_text": "CDP-tracked training and project outputs; [OWNER-CONFIRM: one grant application (scheme) submitted by M24]; [OWNER-CONFIRM: co-supervision of n MSc/BSc students at ATK or ELTE]",
      "page_budget_delta_lines": 0,
      "compensating_cut": null,
      "owner": "fellow",
      "fallback": "No change; the sealed cell stands.",
      "ripple": [
        "§1.3 training paragraph should mention the same commitments only if space allows (not required)"
      ],
      "verification": "The cell contains no '[OWNER-CONFIRM' after the owner answers; row height unchanged (Evidence cell ≤ 4 lines); B-1 page count = 10.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.1 on Impact"
    },
    {
      "action_id": "A-18",
      "finding_ids": [
        "F-06"
      ],
      "priority": "P3",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §1.3 ¶\"Supervisory architecture and qualifications. FIELDWISE\" s7 (p. 27): 'The host also provides demonstrated European-project experience: … TUdi.'",
      "action_class": "needs_fact",
      "instruction": "Replace the European-project sentence (duplicated in Part B-2 §5.2) in place with the supervisors' supervision record and named international collaborations (2 lines out, 2–3 lines in).",
      "proposed_text": "Prof. Janda has supervised [OWNER-CONFIRM: n] PhD and [OWNER-CONFIRM: m] postdoctoral researchers to completion and collaborates with [OWNER-CONFIRM: two named international groups]; Prof. Jung has supervised [OWNER-CONFIRM: n/m] and collaborates with [OWNER-CONFIRM: named group]. ATK's MSCA and Horizon Europe record is given in Part B-2, Section 5.2.",
      "page_budget_delta_lines": 0,
      "compensating_cut": "in place: B1 §1.3 ¶\"Supervisory architecture and qualifications. FIELDWISE\" s7 (p. 27): 'The host also provides demonstrated European-project experience: … TUdi.' (−2 lines)",
      "owner": "supervisor",
      "fallback": "Leave the sentence as sealed; apply A-07 (outputs in Part B-2) only.",
      "ripple": [
        "A-19 (same numbers in Part B-2 §5.2)",
        "Part B-2 §5.2 must keep the LANDRACES / AI4SoilHealth / COUSIN record (it does)"
      ],
      "verification": "grep 'has supervised' in B-1 §1.3 ≥ 1 with no '[OWNER-CONFIRM'; grep 'The host also provides demonstrated' = 0; §1.3 paragraph line count ≤ +1; B-1 page count = 10.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.2 on Excellence"
    },
    {
      "action_id": "A-19",
      "finding_ids": [
        "F-06"
      ],
      "priority": "P3",
      "target_document": "PART_B2_DOCX",
      "anchor": "B2 §5.2 table (Beneficiary) row \"Role and profile of supervisor\" (p. 36); table (Associated partner for secondment) row \"Role and profile of supervisor\" (p. 36)",
      "action_class": "needs_fact",
      "instruction": "Add to each supervisor-profile cell the supervision record (PhD / postdoctoral researchers supervised, completed) and two or three named international collaborations.",
      "proposed_text": "Supervision record: [OWNER-CONFIRM: n PhD, m postdoctoral researchers supervised; k completed]. Main international collaborations: [OWNER-CONFIRM: named institutions/groups].",
      "page_budget_delta_lines": 0,
      "compensating_cut": null,
      "owner": "supervisor",
      "fallback": "No change; A-07 stands alone.",
      "ripple": [
        "A-18 (Part B-1 sentence uses the same numbers)"
      ],
      "verification": "Both supervisor cells contain 'Supervision record:' with numerals and no '[OWNER-CONFIRM'.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.1 on Excellence (with A-18)"
    },
    {
      "action_id": "A-20",
      "finding_ids": [
        "F-01",
        "F-03"
      ],
      "priority": "P3",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §1.2 ¶\"Stage 1 (WP1) harmonises the\" s2–s3 and s5 (p. 25)",
      "action_class": "needs_fact",
      "instruction": "Replace the hedged harmonisation sentence with the method the fellow and Prof. Jung commit to, and name the model family, uncertainty and calibration method in s5 (+4 lines). Pay for it with CUT-18 (delete §1.1 ¶\"Realistically achievable. FIELDWISE combines\" s3 'Previous MATE research established … alone.', −2, already evidenced by footnotes 3–4), CUT-9 (compress the partner list in §1.2 ¶\"Integration of methods and disciplines.\" s2 to the four role assignments, −1) and CUT-22 (delete §1.2 ¶\"Overall methodology: concepts, models and\" s2 'Operational predictors comprise spectral, soil-water and meteorological variables.', −1).",
      "proposed_text": "Historical plots ([OWNER-CONFIRM: a × b m]) are too small for plot-level Sentinel-2 retrieval; handheld hyperspectral reflectance ([OWNER-CONFIRM: instrument, spectral range]) is therefore converted into Sentinel-2 band-equivalent reflectance and indices by [OWNER-CONFIRM: method, e.g. convolution with the Sentinel-2 MSI spectral response functions] after [OWNER-CONFIRM: correction applied], and a predictor is retained only where [OWNER-CONFIRM: acceptance test] holds, before model freeze. … Blocked, leakage-safe unseen-year validation tests temporal transfer; a [OWNER-CONFIRM: model family, e.g. regularised logistic model] with [OWNER-CONFIRM: uncertainty method] and [OWNER-CONFIRM: calibration method] is compared with a [OWNER-CONFIRM: nonlinear benchmark, e.g. gradient-boosted trees].",
      "page_budget_delta_lines": 0,
      "compensating_cut": "B1 §1.1 ¶\"Realistically achievable. FIELDWISE combines\" s3 (p. 25, −2) + B1 §1.2 ¶\"Integration of methods and disciplines.\" s2 compressed (p. 26, −1) + B1 §1.2 ¶\"Overall methodology: concepts, models and\" s2 (p. 25, −1)",
      "owner": "fellow",
      "fallback": "No change; the sealed sentences stand (no invented method).",
      "ripple": [
        "R4 (clouds/mixed pixels) and §3.2 ELTE row stay consistent with the named method",
        "D1.2 protocol description in §1.1 O1 unchanged"
      ],
      "verification": "grep 'where technically possible' in B-1 = 0; the two sentences contain no '[OWNER-CONFIRM' after the owner answers; grep 'Previous MATE research established' = 0; B-1 page count = 10.",
      "effort": "M",
      "regression_risk": "medium",
      "expected_gain": "+0.3 on Excellence"
    },
    {
      "action_id": "A-21",
      "finding_ids": [
        "F-02"
      ],
      "priority": "P3",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §1.2 ¶\"Stage 2 (WP2) prospectively tests\" s2 (p. 26); ¶\"Overall methodology: concepts, models and\" s5 (p. 25)",
      "action_class": "needs_fact",
      "instruction": "Dimension the prospective design in s2 and fix the stress-reference rule in the D1.2 sentence (+4 lines). Pay for it with CUT-19 (delete the two UAV sentences in §1.2 ¶\"Methodological challenges and mitigation.\" — 'If clouds or acquisition timing … transferability assessment.' — which R4 and the §3.2 ELTE row already state, −2), CUT-23 (delete §1.3 ¶\"Planned training activities and ELTE secondment.\" s5 'These activities advance the fellow … interface.', −1) and CUT-25 (delete §1.1 ¶\"Problem and overarching aim. European\" s2 'High-value horticultural irrigation often relies … unnecessary irrigation.', −2).",
      "proposed_text": "Controlled irrigation creates well-watered, deficit-irrigated and unirrigated conditions in [OWNER-CONFIRM: n] replicate treatment areas of at least [OWNER-CONFIRM: a × b m] each, so that [OWNER-CONFIRM: k] interior Sentinel-2 pixels per area are valid; [OWNER-CONFIRM: c] physiological campaigns per season sample [OWNER-CONFIRM: p] plants per area at [OWNER-CONFIRM: growth stages]. … Before model fitting, D1.2 fixes the stress reference as [OWNER-CONFIRM: rule, e.g. Fv/Fm and stomatal-conductance deviation from the well-watered control, stratified by growth stage] and the acceptance thresholds for K6.",
      "page_budget_delta_lines": -1,
      "compensating_cut": "B1 §1.2 ¶\"Methodological challenges and mitigation.\" UAV sentences (p. 26, −2) + B1 §1.3 ¶\"Planned training activities and ELTE secondment.\" s5 (p. 27, −1) + B1 §1.1 ¶\"Problem and overarching aim. European\" s2 (p. 24, −2)",
      "owner": "fellow",
      "fallback": "No change; the sealed sentences stand (no invented design numbers).",
      "ripple": [
        "K5 in §3.1 (biological sample size reported) stays consistent",
        "R2/R3 wording unchanged",
        "MATE (Dr Takács) to confirm the reference rule"
      ],
      "verification": "The Stage 2 sentence contains at least three numerals and no '[OWNER-CONFIRM'; grep 'If clouds or acquisition timing' = 0; B-1 page count = 10.",
      "effort": "M",
      "regression_risk": "medium",
      "expected_gain": "+0.2 on Excellence"
    },
    {
      "action_id": "A-22",
      "finding_ids": [
        "F-04",
        "F-15"
      ],
      "priority": "P3",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §1.2 ¶\"Open science practices. FIELDWISE follows\" s8 (p. 26)",
      "action_class": "needs_decision",
      "instruction": "Replace the conditional sharing sentence in place with named repository, licence and preprint commitments decided by the fellow and the host (same length ±1 line; trim the same sentence to fit).",
      "proposed_text": "Analysis code, the model card and non-sensitive derived outputs are deposited in [OWNER-CONFIRM: repository] under [OWNER-CONFIRM: licence] at each milestone release, each manuscript is posted as a preprint on [OWNER-CONFIRM: server], and commercially protectable results are assessed before disclosure.",
      "page_budget_delta_lines": 0,
      "compensating_cut": "in place: the replaced sentence (p. 26, 2 lines)",
      "owner": "fellow",
      "fallback": "No change; the sealed sentence stands.",
      "ripple": [
        "§2.2 ¶\"Reach and uptake are tracked\" 'monitoring of repository use after release' now refers to a named repository",
        "D5.2 DMP description unchanged"
      ],
      "verification": "grep 'where institutional, commercial and IP rights permit' in B-1 = 0; sentence contains no '[OWNER-CONFIRM'; B-1 page count = 10.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.1 on Excellence"
    },
    {
      "action_id": "A-23",
      "finding_ids": [
        "F-05"
      ],
      "priority": "P3",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §1.1 ¶\"Pertinence. Three linked scientific\" s3 (p. 24), after '…plant physiological responses2.'",
      "action_class": "needs_fact",
      "instruction": "Add one sentence positioning the approach against existing tomato water-stress indicators, with two references supplied by the fellow as footnotes (+1 text line, +2 footnote lines). No compensating cut remains in Part B pages 1–7 that does not touch a strength; use the ≈5 lines of slack on Part B page 7 and verify the page count. Lowest priority among the P3 items.",
      "proposed_text": "Existing tomato water-stress indicators — [OWNER-CONFIRM: e.g. crop water stress index / thermal, stem-water-potential and evapotranspiration-based scheduling][OWNER-CONFIRM: ref A],[OWNER-CONFIRM: ref B] — are calibrated locally and rarely tested prospectively across years or sensing scales.",
      "page_budget_delta_lines": 3,
      "compensating_cut": "none without touching a strength; consumes Part B page 7 slack (≈5 lines) — mandatory page-count check",
      "owner": "fellow",
      "fallback": "No change.",
      "ripple": [
        "Footnote numbering 3–6 shifts by two",
        "Part B page 7 slack reduced accordingly"
      ],
      "verification": "Footnote count in B-1 = 8; B-1 page count = 10; §3 still starts at the top of Part B page 8.",
      "effort": "M",
      "regression_risk": "medium",
      "expected_gain": "+0.1 on Excellence"
    },
    {
      "action_id": "A-24",
      "finding_ids": [
        "F-07"
      ],
      "priority": "P3",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §1.3 ¶\"Planned training activities and ELTE secondment.\" s6 (p. 27)",
      "action_class": "needs_fact",
      "instruction": "Replace 'Guest lectures and practical activities at MATE and, where feasible, Agricultural University–Plovdiv build on previous university teaching experience.' with named courses/providers with timing and firm teaching venues (+2 lines). Uses Part B page 7 slack (see A-23); apply only if A-23 is not applied or slack remains.",
      "proposed_text": "Formal training: [OWNER-CONFIRM: course, provider, month] (open science/FAIR), [OWNER-CONFIRM: course, provider, month] (responsible AI), [OWNER-CONFIRM: course, provider, month] (grant writing/IP). Teaching: guest lectures and practical activities at MATE [OWNER-CONFIRM: month] and at the Agricultural University–Plovdiv [OWNER-CONFIRM: month].",
      "page_budget_delta_lines": 2,
      "compensating_cut": "none remaining without touching a strength; Part B page 7 slack — mandatory page-count check",
      "owner": "supervisor",
      "fallback": "No change.",
      "ripple": [
        "§2.1 table row 'Transferable-skills portfolio' stays consistent",
        "CDP (D5.1) will list the same courses"
      ],
      "verification": "grep 'where feasible' in B-1 §1.3 = 0; sentence contains no '[OWNER-CONFIRM'; B-1 page count = 10.",
      "effort": "M",
      "regression_risk": "medium",
      "expected_gain": "+0.1 on Excellence"
    },
    {
      "action_id": "A-25",
      "finding_ids": [
        "F-20"
      ],
      "priority": "P3",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §3.2 table \"Organisation\" row \"HUN-REN ATK\" s5 (p. 33)",
      "action_class": "needs_fact",
      "instruction": "Replace the generic hosting sentence with concrete arrangements supplied by the host (+3 lines). Pay for it with CUT-2 (delete the ATK row sentence 'Where available and formally assigned early-stage female researchers … participation.', −2) and CUT-3 (delete the ELTE row sentence 'Where available, female students … participation.', −2); both describe team balance, which the panel does not score.",
      "proposed_text": "ATK employs the fellow under [OWNER-CONFIRM: full-time employment contract with full social security], integrates her in the Plant Physiology and Metabolomics Department with [OWNER-CONFIRM: office/laboratory and computing provision], provides [OWNER-CONFIRM: HR onboarding, relocation and family support, language support] and applies its gender equality plan (Part A); project administration is supported by [OWNER-CONFIRM: grants office].",
      "page_budget_delta_lines": -1,
      "compensating_cut": "B1 §3.2 table row \"HUN-REN ATK\" s4 (p. 33, −2) + B1 §3.2 table row \"ELTE\" s5 (p. 33, −2)",
      "owner": "host",
      "fallback": "Delete nothing and insert only 'ATK applies a gender equality plan (Part A)' if space allows; otherwise no change.",
      "ripple": [
        "Part A p. 5 'Gender equality plan: Yes' is the source for the GEP clause",
        "Part B-2 §5.2 'General description' cell may repeat the contract statement"
      ],
      "verification": "ATK row contains 'employs the fellow under' and no '[OWNER-CONFIRM'; grep 'female' in B-1 §3.2 = 0; Part B page 10 ends with the MVCRI row; B-1 page count = 10.",
      "effort": "M",
      "regression_risk": "low",
      "expected_gain": "+0.1 on Implementation"
    },
    {
      "action_id": "A-26",
      "finding_ids": [
        "F-16"
      ],
      "priority": "P3",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §3.2 table \"Organisation\" rows \"MATE\", \"Krumatic EOOD\", \"Commercial farmer/producer\" (p. 33)",
      "action_class": "needs_fact",
      "instruction": "State the status of each informal arrangement (agreement signed, letter held, producer identified) with dates (+3 lines). Pay for it with CUT-4 (condense the MVCRI row to three lines, −2) and the ≈4 lines of slack at the end of Part B page 10.",
      "proposed_text": "MATE: data-access and reuse agreement [OWNER-CONFIRM: signed dd/mm/yyyy | to be signed before M1]. Krumatic: development agreement [OWNER-CONFIRM: signed dd/mm/yyyy | draft agreed], covering deliverables, source-code delivery, ownership, licensing and access. Producer: [OWNER-CONFIRM: named farm/region, field of x ha with drip/sprinkler irrigation], commitment letter [OWNER-CONFIRM: held dd/mm/yyyy]; backup site [OWNER-CONFIRM: identified].",
      "page_budget_delta_lines": 1,
      "compensating_cut": "B1 §3.2 table row \"MVCRI, Plovdiv\" condensed to 3 lines (p. 33, −2) + Part B page 10 slack (≈4 lines) — mandatory page-count check",
      "owner": "host",
      "fallback": "Apply A-10 (risk row) only; leave the rows as sealed (no invented agreements).",
      "ripple": [
        "R7 (A-10) wording stays consistent",
        "Part B-2 §5.1 note on informal organisations may add the same status"
      ],
      "verification": "Each of the three rows contains 'agreement' or 'commitment' with a date or status and no '[OWNER-CONFIRM'; B-1 page count = 10.",
      "effort": "M",
      "regression_risk": "low",
      "expected_gain": "+0.3 on Implementation"
    },
    {
      "action_id": "A-27",
      "finding_ids": [
        "F-22"
      ],
      "priority": "P3",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §3.2 table \"Organisation\" row \"Krumatic EOOD\" s1 (p. 33)",
      "action_class": "needs_fact",
      "instruction": "Append the funding source of the remunerated services and of the field equipment (+1 line; Part B page 10 slack).",
      "proposed_text": "The services and the soil-water and meteorological monitoring equipment are funded from [OWNER-CONFIRM: the research, training and networking contribution (EUR 1 000 per month) | host co-funding | other source].",
      "page_budget_delta_lines": 1,
      "compensating_cut": "Part B page 10 slack (≈4 lines, shared with A-26) — mandatory page-count check",
      "owner": "host",
      "fallback": "No change.",
      "ripple": [
        "Part A budget unchanged (unit contributions are fixed)"
      ],
      "verification": "Krumatic row contains 'funded from' and no '[OWNER-CONFIRM'; B-1 page count = 10.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.05 on Implementation"
    },
    {
      "action_id": "A-28",
      "finding_ids": [
        "F-15"
      ],
      "priority": "P3",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §2.2 table \"Strand\" row \"Dissemination\" cell \"Measures and outputs\" (p. 29): 'EGU/ECPA presentations'",
      "action_class": "needs_decision",
      "instruction": "Add one horticultural or irrigation-science venue chosen by the fellow (in-cell, no line change expected).",
      "proposed_text": "EGU/ECPA and [OWNER-CONFIRM: horticultural or irrigation-science conference] presentations",
      "page_budget_delta_lines": 0,
      "compensating_cut": null,
      "owner": "fellow",
      "fallback": "No change.",
      "ripple": [
        "K13 (≥2 conference presentations) unchanged"
      ],
      "verification": "Dissemination cell names three venues and no '[OWNER-CONFIRM'; row height unchanged; B-1 page count = 10.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.05 on Impact"
    },
    {
      "action_id": "A-29",
      "finding_ids": [
        "F-08"
      ],
      "priority": "P3",
      "target_document": "PART_B2_DOCX",
      "anchor": "B2 §4 list \"Professional experience\" bullet 4 'Independent developer of the pre-existing DrR – Digital Agronomist desktop research prototype.' (p. 34)",
      "action_class": "needs_fact",
      "instruction": "Document the prototype: version, repository or dated declaration, implemented functions, and name the data-science training providers in the 'Methods and technical competences' paragraph.",
      "proposed_text": "Independent developer of the pre-existing DrR – Digital Agronomist desktop research prototype (version [OWNER-CONFIRM: x.y], [OWNER-CONFIRM: repository URL | dated declaration dd/mm/yyyy]; implements [OWNER-CONFIRM: functions, e.g. data ingestion, index computation, stress-status display]). … formal training in AI, Data Science, Machine Learning and Python ([OWNER-CONFIRM: provider, year]).",
      "page_budget_delta_lines": 0,
      "compensating_cut": null,
      "owner": "fellow",
      "fallback": "No change.",
      "ripple": [
        "Optional one-clause echo in B1 §1.4 only if Part B page 7 slack remains (not required)"
      ],
      "verification": "B-2 §4 DrR bullet contains a version and a repository or declaration date and no '[OWNER-CONFIRM'.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.05 on Excellence"
    },
    {
      "action_id": "A-30",
      "finding_ids": [
        "F-25"
      ],
      "priority": "P4",
      "target_document": "PART_B2_DOCX",
      "anchor": "B2 footer pp. 34–37",
      "action_class": "editorial",
      "instruction": "Replace the footer field '[Page limit]' with the actual page count and restart numbering at 1 for Part B-2 (or remove the 'of [Page limit]' fragment).",
      "proposed_text": "Part B – Page 1 of 4",
      "page_budget_delta_lines": 0,
      "compensating_cut": null,
      "owner": "operator",
      "fallback": "n/a (cosmetic)",
      "ripple": [],
      "verification": "grep '[Page limit]' in the exported PDF = 0.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.0 (cosmetic)"
    },
    {
      "action_id": "A-31",
      "finding_ids": [
        "F-27"
      ],
      "priority": "P4",
      "target_document": "PART_B2_DOCX",
      "anchor": "B2 §5.1 ¶\"Only formal MSCA participating organisations\" (p. 35), append",
      "action_class": "needs_fact",
      "instruction": "Add the inter-relationship declaration the template asks for, confirmed by the fellow and the host.",
      "proposed_text": "Inter-relationships: [OWNER-CONFIRM: none between the participating organisations and individuals beyond the co-authorships listed in Section 4 (MATE, MVCRI) | list].",
      "page_budget_delta_lines": 0,
      "compensating_cut": null,
      "owner": "fellow",
      "fallback": "No change.",
      "ripple": [],
      "verification": "grep 'Inter-relationships:' in B-2 §5.1 = 1 with no '[OWNER-CONFIRM'.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.0 (template completeness)"
    },
    {
      "action_id": "A-32",
      "finding_ids": [
        "F-26"
      ],
      "priority": "P4",
      "target_document": "PART_A_PORTAL",
      "anchor": "A p.8 Researcher > Current Department/Faculty/Institute/Laboratory name; A p.15 AgroVIR previous projects and infrastructure (500/300-character fields); A p.13 AgroVIR Departments",
      "action_class": "portal_admin",
      "instruction": "Correct 'Plant physyology' to 'Plant physiology'; shorten the two AgroVIR fields so that they end inside the character limit (e.g. end the infrastructure text at 'satellite-map use and navigation.' and the project-name field at 'SMART-GAZDA, Bonafarm'); fill the AgroVIR department block or mark it not applicable.",
      "proposed_text": "Plant physiology",
      "page_budget_delta_lines": 0,
      "compensating_cut": null,
      "owner": "operator",
      "fallback": "n/a (cosmetic)",
      "ripple": [],
      "verification": "Regenerated Part A pp. 8, 13, 15 show no truncated words and no typo.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.0 (cosmetic)"
    },
    {
      "action_id": "A-33",
      "finding_ids": [
        "F-14"
      ],
      "priority": "P2",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §3.1 ¶\"Lead: fellow/ATK; supervisors and host\" T5.1 (p. 31)",
      "action_class": "editorial",
      "instruction": "Keep 'quarterly reviews' in T5.1 (consistent with §1.3); no text change unless CUT-15 (A-11) condenses the paragraph, in which case retain the word 'quarterly'.",
      "proposed_text": "T5.1: CDP, quarterly reviews, technical/transferable skills, knowledge exchange.",
      "page_budget_delta_lines": 0,
      "compensating_cut": null,
      "owner": "operator",
      "fallback": "n/a",
      "ripple": [
        "A-04",
        "A-11 (CUT-15)"
      ],
      "verification": "grep 'quarterly' in B-1 §3.1 = 1.",
      "effort": "S",
      "regression_risk": "low",
      "expected_gain": "+0.0 (consistency guard)"
    },
    {
      "action_id": "A-34",
      "finding_ids": [
        "F-17"
      ],
      "priority": "P3",
      "target_document": "PART_B1_DOCX",
      "anchor": "B1 §3.1 ¶\"WP1 — Data harmonisation, stress definition\" header and ¶\"Lead: fellow/ATK; MATE and ELTE\" (p. 31)",
      "action_class": "needs_decision",
      "instruction": "If the fellow and supervisor decide to re-phase, move the model freeze from M3 to M4 (T1.3 M2–M4; MS1 M4; D1.2/D1.3 M4) and keep T2.2 at M4–M12 only if the start window (A-11) allows; otherwise leave as sealed. Any change must be propagated to the Gantt, MS1, D5.1 and §1.1.",
      "proposed_text": "[OWNER-CONFIRM: T1.3 (M2–M4): build the pipeline; after protocol lock, fit and freeze the model/benchmark. … D1.2 protocol and D1.3 model/card (M4) … MS1 (M4)]",
      "page_budget_delta_lines": 0,
      "compensating_cut": null,
      "owner": "fellow",
      "fallback": "No change (re-phasing without the start-window decision would create new inconsistencies).",
      "ripple": [
        "Gantt p. 32 (re-render)",
        "§1.1 O1/O2 deliverable months",
        "§3.1 milestone list and critical path",
        "§2.1 table (D5.1 M3 review) if D5.1 moves"
      ],
      "verification": "Every occurrence of 'M3' tied to MS1/D1.2/D1.3 reads 'M4'; Gantt milestone 1 at month 4; B-1 page count = 10.",
      "effort": "L",
      "regression_risk": "high",
      "expected_gain": "+0.1 on Implementation"
    }
  ],
  "do_not_touch": [
    {
      "location": "B1 §1.1 ¶\"Beyond the state of the art,\" (p. 25)",
      "reason": "The four challenged assumptions and the three citable advances are the clearest statement of ambition; every lens credited it."
    },
    {
      "location": "B1 §1.1 ¶\"Measurability and verifiability.Model development\" (p. 25)",
      "reason": "Metric set, M3 freeze and falsifiable hypothesis — the strongest sentences in the proposal (E1, E2, E3). Only the missing space after 'verifiability.' may be fixed."
    },
    {
      "location": "B1 §1.2 ¶\"Stage 2 (WP2) prospectively tests\" s1, s4–s6 (p. 26)",
      "reason": "Frozen-model, primary-before-recalibration logic; edit only s2 (A-21)."
    },
    {
      "location": "B1 §1.2 ¶\"Methodological challenges and mitigation.\" items (i)–(vi) (p. 26)",
      "reason": "Dense mitigation list valued by E1 and E2; only the two UAV sentences are a permitted cut (CUT-19)."
    },
    {
      "location": "B1 §1.2 ¶\"Gender dimension and other diversity aspects.\" (p. 26)",
      "reason": "Accepted by all lenses as an adequate justified non-relevance statement; rewording risks turning it into a team-balance claim."
    },
    {
      "location": "B1 §1.3 ¶\"Structured supervision and governance.\" (p. 27)",
      "reason": "Governance detail credited by E3; the only permitted change is none (cadence is harmonised in §2.1 by A-04)."
    },
    {
      "location": "B1 §1.3 ¶\"Two-way transfer of knowledge.\" s2–s4 (p. 27)",
      "reason": "Concrete two-directional transfer credited by all lenses; only the generic opening sentence is a permitted cut (CUT-20)."
    },
    {
      "location": "B1 §1.3 ¶\"Rationale and added value of the\" s1–s5 (p. 27)",
      "reason": "Compliance-critical placement wording ('integral', 'M25–M30', non-academic, added value for project and career); only s6 is a permitted cut (CUT-11)."
    },
    {
      "location": "B1 §2.2 table rows \"Exploitation\" and \"IP and knowledge management\" and ¶\"Exploitation pathway.\" (pp. 29–30)",
      "reason": "The strongest Impact strand (rights layers, dated DrR baseline, four result families); preserve verbatim."
    },
    {
      "location": "B1 §2.3 table row \"Agricultural & environmental\" sentence 'no numerical water-saving benefit is claimed in advance' (p. 30)",
      "reason": "Honest bounding credited by E1; keep it and add magnitude beside it (A-13) rather than replace it."
    },
    {
      "location": "B1 §3.1 WP headers, task months, PM figures, deliverable months, K1–K14, MS1–MS6 (pp. 31–32)",
      "reason": "Internally consistent set that reconciles with the Gantt; any change ripples into the Gantt image and Part A (duration)."
    },
    {
      "location": "B1 §3.1 ¶\"Decision gates and dependencies.\" and ¶\"Risk control.\" s2 (p. 32)",
      "reason": "Named approvers and the integrity rule ('Poor transfer is a reportable scientific result…') were quoted as strengths."
    },
    {
      "location": "B1 §3.1 Gantt (p. 32)",
      "reason": "Image; Part B page 9 is full — any text pushed from page 8 moves the Gantt to page 10 and overflows the limit. Re-render only for A-03 labels."
    },
    {
      "location": "Part A pp. 8–9 (researcher data, residence table), p. 16 (budget, 24 + 6 months, countries)",
      "reason": "Eligibility- and budget-critical; consistent with Part B; do not edit."
    },
    {
      "location": "B2 §5.1 table (PICs, roles) and §5.2 EU-project record (pp. 35–36)",
      "reason": "Consistent with Part A after A-01; the LANDRACES/AI4SoilHealth/COUSIN record is the host's MSCA evidence."
    },
    {
      "location": "B1 §2.1 table split across Part B pages 5–6 (pp. 28–29)",
      "reason": "Row-break sensitive: any reflow above it can move a row and change the page fill unpredictably; check row integrity after every edit in §1.x–§2.1."
    },
    {
      "location": "B1 footnotes 1–6 (pp. 24, 27)",
      "reason": "9-pt footnotes change page fill non-linearly; add footnotes (A-23) only with a page-count check."
    }
  ],
  "open_decisions": [
    {
      "id": "OD-E1",
      "question": "Does the Guide for Applicants require the secondment host (ELTE) to be registered as an associated partner in Part A for a European Fellowship? (A-01)",
      "owner": "operator",
      "needed_by": "2026-09-09T10:00+02:00",
      "fallback": "Leave Part A unchanged; Part B-2 table 5.1 already states role and PIC."
    },
    {
      "id": "OD-E2",
      "question": "Is the Environmental Engineering MSc held (award date dd/mm/yyyy) or in progress (2025–2026)? (A-02)",
      "owner": "fellow",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "Use the CV wording (in progress) in both Part B-1 and Part B-2."
    },
    {
      "id": "OD-E3",
      "question": "Full dd/mm/yyyy dates for every position, degree and the career break; one-clause significance and open-access status per output; entries or 'none' for invited presentations, funding, supervision/mentoring. (A-05)",
      "owner": "fellow",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "Insert only the PhD award date 14/10/2020 from Part A."
    },
    {
      "id": "OD-E4",
      "question": "Supervision record (PhD / postdoctoral researchers supervised and completed) and two or three named international collaborations for Prof. Janda and Prof. Jung (and Dr Hollós). (A-18, A-19)",
      "owner": "supervisor",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "Apply A-07 (outputs from Part A into Part B-2) only."
    },
    {
      "id": "OD-E5",
      "question": "Hyperspectral-to-Sentinel-2 harmonisation: instrument and spectral range, plot dimensions, conversion method, correction applied, acceptance test; model family, uncertainty and calibration method; benchmark. (A-20)",
      "owner": "fellow",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "No change to the sealed sentences."
    },
    {
      "id": "OD-E6",
      "question": "Prospective design: number and size of replicate treatment areas, valid interior pixels per area, campaigns per season, plants per area, growth stages sampled; the stress-reference rule to be fixed in D1.2. (A-21)",
      "owner": "fellow",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "No change to the sealed sentences."
    },
    {
      "id": "OD-E7",
      "question": "Assumed start window (months) compatible with the tomato calendar, and the slipped-start contingency; whether to re-phase MS1 to M4. (A-11, A-34)",
      "owner": "fellow",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "No change; the calendar dependency stays as sealed."
    },
    {
      "id": "OD-E8",
      "question": "Addressable magnitude: farms and hectares under AgroVIR software, irrigated processing-tomato area in Hungary and Bulgaria (with source), hectares covered by the validation field. (A-13)",
      "owner": "partner:AgroVIR",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "Apply A-12 (editorial European row) only."
    },
    {
      "id": "OD-E9",
      "question": "Communication channels (ATK/ELTE/AgroVIR), number and timing of demonstrations, workshop month, article outlets, reach target. (A-15)",
      "owner": "host",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "Apply A-14 (editorial restructuring) only."
    },
    {
      "id": "OD-E10",
      "question": "Open-science commitments: repository, licence, preprint server, milestone release schedule. (A-22)",
      "owner": "fellow",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "No change."
    },
    {
      "id": "OD-E11",
      "question": "Status of the MATE data-access/reuse agreement, the ATK–Krumatic development agreement, the producer's identity, field and commitment letter, and the backup site. (A-26)",
      "owner": "host",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "Apply A-10 (risk row R7) only."
    },
    {
      "id": "OD-E12",
      "question": "Hosting arrangements: contract type, office/laboratory/computing provision, HR onboarding, relocation and family support, language support, grants-office support. (A-25)",
      "owner": "host",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "Insert only the gender-equality-plan clause (Part A p. 5) if space allows."
    },
    {
      "id": "OD-E13",
      "question": "Funding source of Krumatic's remunerated services, monitoring equipment, UAV flights and open-access fees. (A-27)",
      "owner": "host",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "No change."
    },
    {
      "id": "OD-E14",
      "question": "Ethics table: do grower/user feedback activities count as human participants and personal-data processing? Which page pointer for the AI item? (A-06)",
      "owner": "operator",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "Leave the table as sealed."
    },
    {
      "id": "OD-E15",
      "question": "Named training courses, providers and months; firm teaching venues and months. (A-24)",
      "owner": "supervisor",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "No change."
    },
    {
      "id": "OD-E16",
      "question": "Career commitments: one grant application (scheme, month) and a co-supervision/mentoring role; a horticultural or irrigation-science conference venue. (A-17, A-28)",
      "owner": "fellow",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "Apply A-16 (PANGEOS, teaching venues) only."
    },
    {
      "id": "OD-E17",
      "question": "Two references on existing tomato water-stress indicators (CWSI/thermal, stem-water potential, ET-based scheduling) and the one-sentence positioning. (A-23)",
      "owner": "fellow",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "No change."
    },
    {
      "id": "OD-E18",
      "question": "DrR prototype: version, repository or dated declaration, implemented functions; data-science training providers and years. (A-29)",
      "owner": "fellow",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "No change."
    },
    {
      "id": "OD-E19",
      "question": "Inter-relationship declaration for Part B-2 §5 (none beyond listed co-authorships, or list). (A-31)",
      "owner": "fellow",
      "needed_by": "2026-09-09T12:00+02:00",
      "fallback": "No change."
    },
    {
      "id": "OD-E20",
      "question": "Can the Gantt image be re-rendered from its source with the renumbered deliverable labels? (A-03)",
      "owner": "operator",
      "needed_by": "2026-09-09T10:00+02:00",
      "fallback": "Keep the sealed deliverable numbering everywhere."
    }
  ],
  "reupload_recommendation": {
    "recommend": true,
    "minimum_set": [
      "A-01",
      "A-02",
      "A-03",
      "A-04",
      "A-05",
      "A-06",
      "A-07",
      "A-08"
    ],
    "projected_total_after_minimum_set": 76.6,
    "projected_total_after_all_P0_P2": 78.2,
    "rationale": "Re-upload is warranted: one P0 (secondment host absent from Part A) and five P1 defects (held/in-progress degree inconsistency, deliverable numbering gap, CDP cadence inconsistency, CV template content, ethics-table consistency) exist, and the P2 set is editorial, uses facts already in the PDF and nets ≤ 0 lines in Part B-1. Projections use one-decimal criterion scores: minimum set → Excellence 3.9 / Impact 3.8 / Implementation 3.7 = 76.60; all P0–P2 → 3.9 / 4.0 / 3.8 = 78.20. Both remain in the 'above threshold, not competitive' zone. Only the P3 items in II.4 (design numbers, harmonisation method, supervision record, magnitude figures, agreement status, start window) move the proposal towards Seal-of-Excellence territory (about 87–88 if every owner answers by 12:00 on 2026-09-09); the fundable zone (≥ 92) is not reachable within the day. Sequence: (1) portal edits A-01, A-06, A-32 as soon as OD-E1/OD-E14 are answered; (2) Part B-2 edits A-05, A-07, A-19, A-29, A-30, A-31 (no page limit); (3) Part B-1 P1 then P2 (A-02, A-03, A-04, A-08, A-09, A-10, A-12, A-14, A-16, A-33) with a page-count check after Part B pages 1–7, after pages 8–9 and after page 10; (4) P3 items in order of expected gain as answers arrive, respecting the region budgets (pages 1–7 net ≤ +4 against ≈5 lines of slack on page 7; pages 8–9 net ≤ 0; page 10 net ≤ +2 against ≈4 lines of slack); (5) export, run the II.5 checklist, upload. Point of no return: start the final upload no later than 15:30 Brussels time on 2026-09-09 and hold the new acknowledgement of receipt by 16:00; answers arriving after 13:00 are not integrated."
  }
}
```

# Annex A — Individual evaluations E1, E2, E3 (and the Step 1 fact sheet)

The three evaluations were produced independently and in parallel (Step 2); none read another's output before scoring. Each lens scored every criterion. Divergences and their resolution are recorded in Part I-bis (Consensus notes).

## A.0 Step 1 — Fact sheet (working notes)

**Objectives (B-1 §1.1 pp. 24–25).** O1 harmonise the 2022–2026 MATE processing-tomato archive; stress reference + validation protocol (D1.1 M2, D1.2 M3). O2 interpretable, uncertainty-aware probabilistic water-stress model; frozen at M3 with benchmark, predictor definitions and model card (D1.4). O3 prospective validation of the frozen model over two commercial-field processing-tomato seasons with actual Sentinel-2 (D2.1 M20, D2.2 M21). O4 translate validated outputs into the DrR web MVP and assess operational relevance (D3.1–D3.2 M24; D4.1–D4.2 M30).
**Metrics named (p. 25):** balanced accuracy, F1, ROC-AUC; reliability, Brier; lead time, false-alarm rate; regression only if a continuous severity reference is defensible. Acceptance criteria deferred to D1.2.

**Work packages (B-1 §3.1 p. 31).** WP1 Data harmonisation/stress definition/model development M1–M21, 5.0 PM: T1.1 M1–M2 audit; T1.2 M1–M3 harmonise predictors, lock protocol; T1.3 M2–M3 pipeline, fit, freeze; T1.4 M10–M12 + M16–M21 synthesise transfer diagnostics. D1.1 (M2), D1.2 (M3), D1.4 (M3), D1.5 (M21). K1–K4. WP2 Prospective field validation M1–M21, 9.0 PM: T2.1 M1–M4 access/backup, replication, irrigation contrasts, valid Sentinel-pixel geometry, sensor tests; T2.2 M4–M12 season 1; T2.3 M13–M20 season 2; T2.4 M20–M21 report. D2.1 (M20), D2.2 (M21). K5–K6. WP3 DrR web MVP M1–M24, 6.0 PM: T3.1 M1–M3 IP/workflows/interfaces/acceptance tests; T3.2 M4–M20 build; T3.3 M21–M24 integrate MS3-supported functions; T3.4 M22–M24 package. D3.1, D3.2 (M24). K7–K8. WP4 AgroVIR placement M25–M30, 5.4 PM: T4.1 M25–M27; T4.2 M28–M30; T4.3 M27–M30. D4.1, D4.2 (M30). K9–K10. WP5 Training/open science/dissemination/management M1–M30, 4.6 PM (4.0 in M1–M24, 0.6 in M25–M30): T5.1–T5.4. D5.1 CDP (M3), D5.2 DMP (M6; reviews M21/M30), D5.3 (M30; update M24). K11–K14. Total 30.0 PM (24.0 + 6.0). No D1.3 anywhere (D1.1, D1.2, D1.4, D1.5 only).

**Milestones (p. 32):** MS1 M3 protocol lock/model freeze/field plan/CDP; MS2 M12 season-1 QC; MS3 M21 two-season evidence, permitted MVP functions; MS4 M24 critical tests/placement scope; MS5 M27 midpoint; MS6 M30 external assessment/roadmaps. Critical path MS1 → WP2 → MS3 → MS4 → WP4. "The crop calendar must place MS1 before season 1 and the second harvest by M20." No start-month assumption anywhere.
**KPIs:** K1–K4 (WP1), K5–K6 (WP2), K7–K8 (WP3), K9–K10 (WP4), K11 (CDP reviews, four competence strands, 12 secondment months), K12 (metadata/access decisions), K13 (≥2 manuscripts submitted, ≥2 conference presentations, ≥1 end-user workshop by M30), K14 (result-family owners/routes).
**Risks (p. 32):** R1 archive/M3 freeze (M/H); R2 field/calendar (M/H); R3 sensors/weak contrast (M/H); R4 clouds/mixed pixels/EO access (M/H); R5 poor transfer (M/H); R6 engineering/IP/workload (M/M). No risk for farm commitment, MATE archive access/reuse rights, AgroVIR withdrawal, supervisor/secondment availability, start-date slippage.
**Gantt (p. 32):** rows WP1 (M1–3, 10–12, 16–21), WP2 (M1–21), WP3 (M1–24), WP4 (M25–30), WP5 (M1–30), ELTE secondment (M1–3, 10–12, 16–21), milestones 1–6 at M3/12/21/24/27/30, deliverables A/B rows; elapsed months, no dates. Consistent with the text.
**Secondment:** ELTE, Institute of Cartography and Geoinformatics, Prof. András Jung; 12 months in three blocks; "locations of work within the allocated effort". **Placement:** AgroVIR Kft., Budaörs, M25–M30, supervisor Miklós Maróti (MD).
**Participants — formal:** HUN-REN ATK (beneficiary, HU, PIC 866599553); AgroVIR (AP placement, HU, PIC 891807622); ELTE (AP secondment per B-2 only, PIC 999896468). **Informal (B-1 §3.2 p. 33; B-2 p. 35):** MATE (archive owner; Dr Sándor Takács, Prof. Gábor Milics); Krumatic EOOD (remunerated software engineering); unnamed Hungarian commercial farmer/producer (two-season field host); MVCRI Plovdiv (Prof. Ganeva; post-MSCA route, "no core in-action validation role").
**Named people:** Prof. Tibor Janda (primary supervisor, DSc, Head of Plant Physiology and Metabolomics); Dr Roland Hollós (ML/modelling mentoring); Prof. András Jung (co-supervisor, ELTE); Dr Zsófia Varga (ELTE UAV); Takács, Milics (MATE); Miklós Maróti (AgroVIR); Prof. Ganeva (MVCRI); Dr Rositsa Cholakova (fellow, b. 07/06/1989, BG, Chief Assistant Professor MVCRI).
**Supervisor evidence in the PDF:** Janda — Part A p. 11 lists "Janda et al., 2025 – Scientific Reports" and "Szalai et al., 2025"; B-1 §1.3 and B-2 §5.2 assert expertise; no supervision record, no named collaborations. Hollós — footnote 5 (Hollós et al. 2026, GMD) and Part A p. 11. Jung — footnote 6 (Jung et al. 2010, PFG); B-2: Professor and Deputy Director; COST experience; ELTE coordinates QUEST Twinning (GA 101156088). ATK EU record: LANDRACES (MSCA IF 752453), AI4SoilHealth (101086179), COUSIN (101135314), TUdi (B-1/Part A only).
**Budget (A p. 16):** coefficient 0.787; 24 + 6 months; living 149 923.5; mobility 21 300; family 19 800; research/training/networking 30 000; management/indirect 19 500 (displayed total 0); total 240 523.5. B-1 contains no resource plan (Krumatic paid services, sensors, UAV, conferences, OA fees unassigned).
**Researcher (B-2 §4 pp. 34–35; B-1 §1.4 pp. 27–28):** PhD 2020 (maize chilling stress); MSc 2014, BSc 2012 Plant Protection; "Second MSc studies in Environmental Engineering (2025–2026)"; Chief Assistant Professor MVCRI (undated); Assistant Professor AU Plovdiv 2015–2020; Kleffmann Group Bulgaria (undated); DrR prototype developer. 8 publications (2015–2026: 5 on maize chilling/wheat, 1 SES 2025 proceedings on watermelon water regimes and RS, 2 durum-wheat co-authorships) + 2 manuscripts under review (tomato ET from UAV; proximal hyperspectral signatures of water stress in processing tomato). Mobility: COST STSM MATE 10 d (2025); Erasmus+ MATE 14 d (2025); ELTE traineeship 3 months (2026); Novi Sad 7 d (2026). Career break 34 months (2021–2024). No dd/mm/yyyy dates, no significance/OA notes, no invited talks/funding/supervision entries.
**Open science (§1.2 p. 26):** "as open as possible, as closed as necessary"; pre-specification in D1.2; model card in D1.4; FAIR; Copernicus; both positive and negative results reported; ≥2 OA papers; DMP within 6 months; code/metadata/derived outputs "where institutional, commercial and IP rights permit". No repository, licence, preprint or public pre-registration named.
**Gender/diversity (§1.2 p. 26):** sex/gender dimension declared not relevant to the biological content with justification; diversity relevant in end-user interaction (farm context, digital literacy). §3.2 statements on female researchers/students = team balance (neutral).

## A.0b Step 1 — Internal-consistency scan

| Id | Finding | Where | Carry to |
|---|---|---|---|
| C-1 | Two participants in Part A vs three "formal MSCA participating organisations" in B-2 table 5.1 (ELTE) | A p. 4 / B-2 p. 35 | impl-host; formal (W1) |
| C-2 | "is holding Environmental Engineering Master's degree" vs "Second MSc studies in Environmental Engineering (2025–2026)" | B-1 p. 28 / B-2 p. 34 | exc-researcher (W4) |
| C-3 | Deliverable numbering gap: D1.1, D1.2, D1.4, D1.5; no D1.3 | B-1 pp. 24, 31, 32 | impl-workplan (W5) |
| C-4 | Ethics table "human participants: No", "personal data: No" vs self-assessment (consent, GDPR, pseudonymisation) | A p. 17 vs pp. 19–20, B-2 p. 37 | formal only (W7) |
| C-5 | CDP reviews "quarterly" (B-1 §1.3 p. 27; T5.1 p. 31) vs "reviews M3/M12/M21/M24/M27" (§2.1 table p. 28) | B-1 pp. 27, 28, 31 | imp-career / exc-supervision (minor) |
| C-6 | ATK Horizon Europe projects: TUdi listed in B-1 §1.3 and Part A p. 11, absent from B-2 §5.2 | pp. 11, 27, 36 | none (trivial) |
| C-7 | Part A "Public body: No" vs B-2 "public agricultural research organisation" | pp. 5, 36 | none (registry field) |
| C-8 | B-2 footers "Page 3…6 of [Page limit]" | pp. 34–37 | formal (W3) |
| C-9 | Part A typos/truncations; empty AgroVIR department block | pp. 8, 13, 15 | formal (W6) |
| C-10 | Ethics table AI "page 6" pointer: AI is discussed at A pp. 19–20 and B-1 p. 26; B-2 §6 does not mention AI | pp. 18, 37 | formal (Check) |
| C-11 | Krumatic "development agreement defines…" (present tense) vs §1.3 "will be defined in advance" and §3.2 MATE "documented before analysis" — status of agreements unstated | pp. 27, 29, 33 | impl-host (W24) |
| C-12 | Effort, months, KPIs, milestones, Gantt: all consistent; secondment 3 + 3 + 6 = 12 | pp. 31–32 | strength |

## Lens E1 — plant physiology / agronomy / irrigation science

### Criterion 1 — Excellence

**Strengths:**
- The stress construct is physiologically anchored: irrigation treatments and AquaCrop-based crop-water demand define the imposed deficit, while chlorophyll fluorescence and stomatal conductance provide "independent evidence of whether that deficit produced an actual plant stress response" (Section 1.1, p. 24; Section 1.2, p. 25).
- The five-season processing-tomato archive (2022–2026) with contrasting irrigation treatments and physiological, soil-water, meteorological and proximal-spectral observations is an unusually deep basis for a fellowship-scale model and supports unseen-year blocking (Section 1.1, pp. 24–25).
- The validation logic is agronomically sound: the model is frozen at M3 before any prospective outcome, tested over two seasons in a commercial field with well-watered, deficit-irrigated and unirrigated treatment areas, and primary performance is reported before recalibration (Section 1.2, pp. 25–26).
- Operational metrics of direct agronomic value are pre-named: warning lead time, false-alarm rate, calibration, with irrigation, yield and quality recorded in both seasons (Section 1.1, p. 25; Section 3.1, p. 31).
- The researcher's measurement toolkit (Fv/Fm, stomatal conductance, relative water content, canopy temperature, gas exchange) matches the physiological programme, and MATE's processing-tomato irrigation and AquaCrop expertise is documented in cited primary work (Section 1.4, pp. 27–28; footnotes 3–4, p. 24).

**Weaknesses:**
- The physiological stress reference is not defined in the proposal: which variables, thresholds and combination rules classify a plant as stressed is deferred to D1.2 ("Before model fitting, D1.2 will specify how these complementary sources define the stress reference"), and crop phenology is absent, although water-deficit sensitivity and deliberate deficit irrigation in processing tomato depend on growth stage (Section 1.2, p. 25). [major]
- The prospective experiment has no stated design: number of replicate treatment areas, their size, number of plants sampled per campaign, campaign frequency per season and target sample sizes are not given; K5 only promises that "biological sample size" is reported (Section 1.2, p. 26; Section 3.1, p. 31). [major]
- Historical hyperspectral spectra come from plots described as "too small for defensible plot-level Sentinel-2 retrieval" and are converted to Sentinel-2-compatible predictors only "where technically possible"; plot dimensions, canopy-cover conditions and the conversion method are not stated (Section 1.2, p. 25). [major]
- The state of the art does not engage with existing crop water-stress indicators for tomato (thermal or CWSI-type indices, stem-water potential, sensor- or ET-based scheduling); the problem statement rests on four references, one of them a bare EEA homepage link (Section 1.1, p. 24). [minor]
- The supervisory team's crop and irrigation-science expertise sits with MATE staff who hold no formal role, while the primary supervisor's drought-physiology record is asserted rather than evidenced by supervision history or named collaborations (Section 1.3, pp. 26–27; Part B-2, Section 5.2, p. 36). [major]
- The researcher's water-stress and irrigation outputs consist of one 2025 proceedings paper on watermelon and two manuscripts under review; the doctoral and publication record concerns maize chilling stress and wheat (Part B-2, Section 4, pp. 34–35). [minor]

**Score:** 3.7 — The design logic is strong and physiologically grounded, but the stress reference, the field experimental design and the spectral-conversion method are deferred, and supervision evidence is thin (three major and several minor shortcomings; cap 4.4 applies).

### Criterion 2 — Impact

**Strengths:**
- Impact claims are bounded to measurable agronomic quantities: "no numerical water-saving benefit is claimed in advance", and lead time, false alarms and water–yield–quality relationships are measured prospectively (Section 2.3, p. 30).
- The crop-transfer specification separating reusable from crop-specific components, plus the MVCRI route to other irrigated vegetable crops, gives the results a plausible agronomic afterlife (Section 1.1, p. 25; Section 2.3, p. 30).
- The exploitation pathway through a farm-management software company and an end-of-project placement is a realistic channel to growers, with IP layers defined (Section 2.2, pp. 29–30).
- The career measures are coherent with a plant physiologist's transition to agricultural data science, with a CDP, four competence strands and a career KPI (Section 2.1, pp. 28–29).

**Weaknesses:**
- The magnitude of the agricultural contribution is not quantified: no irrigated processing-tomato or horticultural area, no number of growers or hectares reachable through the FMIS network, no yield- or water-related target even as a hypothesis; the "European & societal" row is generic (Section 2.3, p. 30). [major]
- Communication to growers and advisors is unspecified: demonstrations, "public-facing articles" and one end-user workshop carry no timing, channel, key message or reach target beyond "≥1 end-user workshop" (Section 2.2, p. 29; K13, p. 31). [minor]
- Dissemination venues are EO and precision-agriculture forums (EGU/ECPA); no horticultural or irrigation-science forum is named for the physiological results (Section 2.2, p. 29). [minor]
- Career measures list grant writing, leadership and networking as skills without a planned application, named network or supervision role; teaching in Plovdiv is "where feasible" (Section 1.3, p. 27; Section 2.1, pp. 28–29). [minor]

**Score:** 3.8 — The plan is credible and honest, but the unquantified magnitude is a major gap and the communication and career measures lack specificity (one major, three minor).

### Criterion 3 — Quality and efficiency of the implementation

**Strengths:**
- The work plan mirrors the science: freeze → prospective seasons → permitted functions → release → external evaluation, with six gates and explicit decision responsibilities (Section 3.1, pp. 31–32).
- Two consecutive seasons on the same field with an unchanged model constitute replication in time, with a season-1 QC review at MS2 (Section 3.1, p. 32).
- The largest effort share (9.0 PM) goes to field validation, where the agronomic evidence is produced; effort, milestones, deliverables and the Gantt are mutually consistent (Section 3.1, pp. 31–32).
- Field-specific risks (calendar, sensors, weak stress contrast) have concrete trigger responses and named owners (Section 3.1, p. 32).

**Weaknesses:**
- Season 1 (T2.2, M4–M12) and season 2 (T2.3, M13–M20, harvest by M20) fit the Hungarian processing-tomato calendar only for a start in roughly February–March; the proposal states the constraint but gives no assumed start month and no contingency for a start outside the transplanting window; R2 presupposes a compatible start (Section 3.1, pp. 31–32). [major]
- Months 1–3 carry the audit and harmonisation of five heterogeneous seasons, protocol lock, pipeline, model fitting and freeze, field-access agreements, IP/architecture agreement and the CDP, while the fellow is on the first ELTE block; about 3 PM is available for the entire model-building phase (Section 3.1, p. 31; Gantt, p. 32). [major]
- The commercial field host is unnamed, no commitment is stated, and the field size, irrigation system, treatment-area layout and any compensation for deficit and unirrigated areas are not described, although the validation depends on them (Section 1.2, p. 26; Section 3.2, p. 33). [major]
- The archive owner (MATE), the software engineer (Krumatic) and the farmer have no formal role; data access is "documented before analysis", which describes a procedure rather than an existing agreement (Section 3.2, p. 33; Part B-2, Section 5.1, p. 35). [major]
- Five of six risks are rated M/H without differentiation; farm withdrawal, archive-reuse rights and AgroVIR withdrawal are absent (Section 3.1, p. 32). [minor]
- No resource plan links sensors, soil-water monitoring, UAV flights and paid engineering to available funds (Section 3.1, pp. 31–32). [minor]
- Deliverable D1.3 does not exist (D1.1, D1.2, D1.4, D1.5 only) (Sections 1.1 and 3.1, pp. 24, 31–32). [minor]

**Score:** 3.6 — A coherent and well-gated plan whose feasibility rests on an unstated start date, a compressed first quarter and field and data partners without formal commitments (four major, three minor; cap 4.4 applies).

### Diagnostic aspect sub-scores (E1)

| aspect_id | sub-score | reason |
|---|---|---|
| exc-obj | 4.2 | Measurable, falsifiable objectives on a rich archive; state of the art thin on existing tomato water-stress indicators |
| exc-method | 3.3 | Sound freeze/prospective logic; stress reference, phenology, replication and spectral conversion undefined |
| exc-supervision | 3.5 | Complementary expertise asserted; no supervision record; crop/irrigation expertise outside the formal team |
| exc-researcher | 3.8 | Strong physiological toolkit; thin water-stress/irrigation output; undated CV entries |
| imp-career | 4.0 | Coherent transition with CDP and KPI; leadership, grants, networks unspecified |
| imp-dissemination | 3.8 | Quantified papers/conferences and strong IP strand; grower communication unspecified; no horticultural forum |
| imp-magnitude | 3.3 | Honest bounding but no quantified target group, area or agronomic target |
| impl-workplan | 3.5 | Consistent gates and effort; start-date/calendar dependency and first-quarter compression unaddressed |
| impl-host | 3.5 | Adequate host infrastructure; field host, archive owner and engineer informal; hosting arrangements generic |

### Watch-list verdicts (E1)

- W1 — confirmed at minor–major in impl-host (Part A p. 4 vs B-2 p. 35); E1 defers weighting to the generalist lens.
- W2 — confirmed at minor in exc-researcher (undated positions and break, no significance notes).
- W3 — outside this lens (cosmetic).
- W4 — confirmed at minor in exc-researcher (held vs in progress, p. 28 vs p. 34).
- W5 — confirmed at minor in impl-workplan (no D1.3).
- W6 — outside this lens (cosmetic).
- W7 — outside this lens (not scored).
- W8 — confirmed at minor in impl-workplan (no resource plan for sensors, UAV, paid engineering).
- W9 — confirmed at major in impl-workplan (calendar dependency; no start-month assumption or slipped-start contingency).
- W10 — confirmed at major in impl-workplan (M1–M3 concurrency; ~3 PM for model building).
- W11 — merged into W10 (effort profile is a symptom of the same compression); not scored separately.
- W12 — confirmed at major in exc-method (small historical plots, conversion "where technically possible", no plot sizes or method).
- W13 — confirmed at major in exc-method (no replication, sample sizes, campaign frequency; thresholds deferred to D1.2).
- W14 — confirmed at minor in exc-obj (no engagement with CWSI/thermal/sensor-based scheduling; bare EEA link).
- W15 — confirmed at minor in exc-method (open-science specificity); gender justification accepted as adequate for plant-only content.
- W16 — confirmed at major in exc-supervision (no supervision record, no named collaborations; crop expertise informal).
- W17 — confirmed at minor in exc-supervision (unnamed courses; first block away from host).
- W18 — confirmed at minor in exc-researcher (water-stress outputs limited to one proceedings paper and two manuscripts under review; DrR undocumented).
- W19 — confirmed at minor in imp-career.
- W20 — confirmed at minor in imp-dissemination.
- W21 — confirmed at major in imp-magnitude.
- W22 — confirmed at minor in impl-workplan (undifferentiated likelihoods; farm/archive/AgroVIR risks absent).
- W23 — confirmed at minor in impl-host (generic hosting statement).
- W24 — confirmed at major in impl-host (four informal organisations; procedures described, no agreements stated).
- W25 — confirmed OK (placement and secondment compliant; nothing contradicts).
- E1-own-1 — [major] Stress reference and phenology undefined: no growth-stage stratification of the stress signal although deficit sensitivity in processing tomato is stage-dependent (Section 1.2, p. 25; no occurrence of phenology, growth stage, flowering or ripening anywhere in Part B).
- E1-own-2 — [minor] No horticultural or irrigation-science dissemination venue named; EGU/ECPA only (Section 2.2, p. 29).
- E1-own-3 — [major, folded into W24/W10] Field logistics unspecified: irrigation system, treatment-area layout and compensation for yield loss in deficit/unirrigated areas absent (Section 1.2, p. 26; Section 3.2, p. 33).
- E1-own-4 — [note, not scored] The archive is described as five seasons (2022–2026) while the 2026 season was still in progress at submission; the completeness of the fifth season is not stated (Section 1.1, p. 24).

## Lens E2 — Earth observation / remote sensing / machine learning

### Criterion 1 — Excellence

**Strengths:**
- Blocked unseen-year validation, a model and predictor set frozen at M3 before any prospective outcome, and primary performance reported before recalibration make the central hypothesis falsifiable (Section 1.1, p. 25; Section 1.2, pp. 25–26).
- The metric set covers discrimination, calibration and operational value (balanced accuracy, F1, ROC-AUC, reliability, Brier, lead time, false-alarm rate), with regression metrics conditional on a defensible continuous reference (Section 1.1, p. 25).
- Proximal and satellite observations are treated as non-interchangeable; cloud gaps and mixed pixels are recognised; UAV data are confined to a supplementary role (Section 1.2, p. 26).
- Open science is built into the method: pre-specified protocol (D1.2), model card (D1.4), FAIR management, reporting of unsuccessful transfer results, DMP within six months (Section 1.2, p. 26).
- The ELTE co-supervision covers field spectroscopy and multisensor fusion, and the fellow already uses Sentinel-1/2, SNAP, QGIS, Google Earth Engine, Python and R (Section 1.3, p. 27; Part B-2, Section 4, p. 34).

**Weaknesses:**
- The hyperspectral-to-Sentinel-2 harmonisation is unspecified (no spectral-response convolution, atmospheric or BRDF treatment, leaf-to-canopy scaling or acceptance test) and is committed only "where technically possible"; because the historical plots are "too small for defensible plot-level Sentinel-2 retrieval", the frozen model never sees a real Sentinel-2 predictor before deployment, and the resulting domain shift is neither bounded nor estimated (Section 1.1, p. 24; Section 1.2, p. 25). [major]
- The archive and the experiment are not dimensioned: plots, treatments and replicates per season, observations per campaign, hyperspectral instrument and spectral range, and target sample sizes are absent, so the power of unseen-year blocking over five seasons and of two prospective seasons cannot be assessed; acceptance thresholds are deferred to D1.2 (Section 1.1, p. 25; Section 1.2, pp. 25–26; Section 3.1, p. 31). [major]
- The model is unnamed: "a parsimonious uncertainty-aware model is compared with a nonlinear benchmark" gives no model family, uncertainty-quantification or calibration method (Section 1.2, p. 25). [minor]
- No proximal spectral measurement is planned in the commercial field, so sensing-scale shift cannot be separated from environmental shift, although D1.5 claims a specification separating "sensing-scale and crop-specific elements" (Section 1.1, p. 25; Section 1.2, p. 26; Section 3.1, p. 31). [minor]
- Sentinel-2 pixel validity is stated as a principle ("sufficiently large treatment areas and valid interior observations") without treatment areas, pixel-purity criteria or handling of the 10 m/20 m band mix (Section 1.2, p. 26). [minor]
- Open-science commitments name no repository, licence, versioning or preprint, and code sharing is conditional on "institutional, commercial and IP rights"; the fellow's machine-learning competence rests on unnamed courses and a prototype with no repository, version or function list (Section 1.2, p. 26; Section 1.4, p. 28; Part B-2, Section 4, p. 34). [minor]

**Score:** 3.5 — The validation logic is excellent, but two major gaps in the EO/ML methodology (unspecified harmonisation; undimensioned data and design) and several minor specificity gaps place the criterion at "good".

### Criterion 2 — Impact

**Strengths:**
- The exploitation pathway is auditable: pre-existing prototype → validated web MVP → independent AgroVIR evaluation → roadmap, with four named result families and separate rights layers anchored by a dated DrR declaration (Section 2.2, pp. 29–30).
- Dissemination is quantified (≥2 open-access manuscripts, EGU/ECPA presentations, model card, publication of prospective transfer performance; K13) (Section 2.2, p. 29; Section 3.1, p. 31).
- Impact claims are evidence-bounded and measured through pre-specified metrics; the transfer methodology and the D1.5 specification are positioned as reusable assets beyond tomato (Section 2.3, p. 30).

**Weaknesses:**
- Magnitude is unquantified: no irrigated area, grower or FMIS-user numbers, no size for AgroVIR's network, no link to EU water policy or to the work programme's expected impacts; the "European & societal" row is generic (Section 2.3, p. 30). [major]
- Data and software as impact vehicles are unspecific: "monitoring of repository use after release" names no repository; no licence, DOI or release plan exists for the harmonised archive or the prospective dataset D2.1, whose reuse rights depend on undetermined MATE terms (Section 2.2, pp. 29–30; Section 1.2, p. 26; Section 3.2, p. 33). [minor]
- Communication measures carry "reach indicators" without values, messages, channels or timing (Section 2.2, p. 29). [minor]
- Career measures name EO/ML skills but no courses, certifications or open-source contributions; CDP reviews are "quarterly" in Section 1.3 (p. 27) and at five listed months in Section 2.1 (p. 28). [minor]

**Score:** 3.8 — Strong exploitation and dissemination strands; one major gap (unquantified magnitude) and three minor ones.

### Criterion 3 — Quality and efficiency of the implementation

**Strengths:**
- Months, effort (30.0 PM), deliverables, milestones, secondment blocks and the Gantt chart reconcile exactly (Section 3.1, pp. 31–32).
- Gates enforce the scientific logic: MS1 freeze precedes season 1, MS3 decides permitted MVP functions, and T3.3 integrates only MS3-supported functions (Section 3.1, pp. 31–32).
- EO risks are recognised (R4: clouds, mixed pixels, access; inadequate coverage restricts satellite-transfer claims) and software readiness is testable (K7 acceptance tests, K8 rights documentation, D3.2) (Section 3.1, pp. 31–32).
- ELTE offers a geoinformatics laboratory, remote-sensing computing, field spectroscopy and UAV capacity (Part B-2, Section 5.2, p. 36).

**Weaknesses:**
- Months 1–3 bundle archive audit, spectral harmonisation, protocol lock, pipeline construction, fitting and freeze (T1.1–T1.3, within WP1's 5.0 PM) with T2.1, T3.1, the CDP and the first ELTE block; the feasibility of a validated freeze at M3 is not justified, and WP1's remaining 2 PM contain no model work (Section 3.1, pp. 31–32). [major]
- Four of seven organisations in the capacity table are informal (MATE archive, Krumatic, unnamed farmer, MVCRI) with no evidence of existing agreements, and the secondment host ELTE is absent from Part A (Section 3.2, p. 33; Part B-2, Section 5.1, p. 35; Part A, p. 4). [major]
- The crop-calendar dependency is stated but no start-month assumption or slipped-start contingency is given (Section 3.1, p. 32). [minor]
- No compute, storage or EO-processing infrastructure is described at the beneficiary, and resources for paid engineering, sensors, UAV flights and open-access fees are unassigned (Section 3.2, p. 33; Part B-2, Section 5.2, p. 36; Part A, p. 16). [minor]
- Deliverable D1.3 is missing; risk ratings are undifferentiated (five of six "M/H") and omit archive-reuse clearance, farm commitment and partner withdrawal (Section 3.1, pp. 31–32). [minor]

**Score:** 3.5 — A coherent, well-gated plan carrying two major credibility gaps (front-loaded months 1–3; informal partners) and several minor omissions.

### Diagnostic aspect sub-scores (E2)

| aspect_id | sub-score | reason |
|---|---|---|
| exc-obj | 4.2 | Clear, measurable, falsifiable objectives; state of the art thin (four references, no comparison with existing water-stress indices or models). |
| exc-method | 3.2 | Validation architecture excellent; harmonisation, data dimensions, statistical design and model family unspecified. |
| exc-supervision | 3.6 | Complementary physiology/ML/EO supervision; EO/ML supervisors evidenced by one paper each; no supervision record. |
| exc-researcher | 3.5 | Physiology and field competences documented; ML/EO evidence limited to unnamed courses, one proceedings paper and an undocumented prototype. |
| imp-career | 3.9 | Credible two-trajectory plan and CDP; EO/ML measures generic; review cadence inconsistent. |
| imp-dissemination | 4.0 | Exploitation and IP strands strong; communication and data/software release unspecific. |
| imp-magnitude | 3.3 | No quantification of reach, no policy or work-programme impact link. |
| impl-workplan | 3.4 | Internally consistent and gated; front-loaded M1–M3, calendar-sensitive, resources unassigned, D1.3 gap. |
| impl-host | 3.4 | ELTE EO capacity documented but not in Part A; four informal partners; beneficiary's EO computing not described. |

### Watch-list verdicts (E2)

- W1 — confirmed at major in impl-host (Part A p. 4 lists two participants; Part B-2 table 5.1, p. 35, lists ELTE with PIC 999896468 as a formal participating organisation).
- W2 — outside this lens (CV format); noted as minor.
- W3 — outside this lens; cosmetic.
- W4 — confirmed at minor in exc-researcher (p. 28 "is holding" vs p. 34 "Second MSc studies … (2025–2026)").
- W5 — confirmed at minor in impl-workplan (D1.1, D1.2, D1.4, D1.5 on pp. 24, 31, 32; no D1.3).
- W6 — outside this lens; cosmetic.
- W7 — outside this lens; not scored.
- W8 — confirmed at minor in impl-workplan (no resource plan for paid engineering, sensors, UAV, OA fees; Part A p. 16 EUR 30 000 research/training/networking).
- W9 — confirmed at minor in impl-workplan from this lens (dependency stated on p. 32; no start-month assumption; the applicant selects the start date, so the omission is a credibility gap rather than a design flaw).
- W10 — confirmed at major in impl-workplan (T1.1–T1.3, T2.1, T3.1, D5.1 and the first ELTE block all in M1–M3, p. 31; Gantt p. 32).
- W11 — confirmed, folded into W10 (WP1 5.0 PM with 2 PM after the freeze; no separate score effect).
- W12 — confirmed at major in exc-method ("where technically possible", pp. 24–25; no harmonisation method, plot sizes, pixel-purity or BRDF/atmospheric handling).
- W13 — confirmed at major in exc-method (no replicates, observations per campaign, sample sizes; thresholds deferred to D1.2, p. 25; no pre-registration).
- W14 — confirmed at minor in exc-obj (footnotes 1–4, p. 24; no engagement with existing tomato water-stress indices or thermal/S-2 approaches beyond one review).
- W15 — confirmed at minor in exc-method for open-science specificity; the gender-dimension justification (p. 26) is adequate and the team-balance statements (p. 33) are neutral.
- W16 — outside this lens except the EO/ML supervisors' evidence base (footnotes 5–6, p. 27: one paper each), noted as minor.
- W17 — outside this lens; from an EO viewpoint the early ELTE block is aligned with the harmonisation need and is not penalised.
- W18 — confirmed at minor in exc-researcher (unnamed "formal upskill training", p. 28; DrR prototype without repository, version or function list, pp. 28, 34; one SES 2025 proceedings paper; two manuscripts under review).
- W19 — outside this lens; noted as minor.
- W20 — confirmed at minor in imp-dissemination (p. 29: no channels, messages, timing or reach values).
- W21 — confirmed at major in imp-magnitude (p. 30: no addressable area, grower or user numbers; generic European row; no work-programme impact mapping).
- W22 — confirmed at minor in impl-workplan (p. 32: five of six risks "M/H"; no archive-reuse, farm-commitment or partner-withdrawal risk).
- W23 — outside this lens; E2 adds that the beneficiary's EO computing and data infrastructure are not described (p. 33; Part B-2 p. 36), minor in impl-host.
- W24 — confirmed at major in impl-host (p. 33: "Data access and permitted reuse are documented before analysis and exploitation" describes a procedure; unnamed farmer; Krumatic agreement status unstated).
- W25 — expected OK, confirmed: placement (M25–M30, AgroVIR, Hungary, rationale on p. 27) and secondment (12 of 24 months, p. 31) contradict nothing in the text.

Own findings (E2), not on the watch-list:
- E2-a — Model family, uncertainty-quantification and calibration method unnamed (Section 1.2, p. 25: "a parsimonious uncertainty-aware model is compared with a nonlinear benchmark"); minor, exc-method.
- E2-b — Archive not dimensioned: no instrument, spectral range, plot count, observations per season or Sentinel-2 revisit alignment (Sections 1.1–1.2, pp. 24–26); absorbed into W13.
- E2-c — No proximal spectral measurement in the prospective seasons, so scale shift and environment shift are confounded while D1.5 claims to separate "sensing-scale" elements (Section 1.1, p. 25; Section 1.2, p. 26; Section 3.1, p. 31); minor, exc-method.
- E2-d — No release plan (repository, licence, DOI) for the harmonised archive or D2.1; "monitoring of repository use after release" (Section 2.2, p. 30) names no repository; minor, imp-dissemination.
- E2-e — No compute or storage plan and no EO-processing capacity described at HUN-REN ATK (Section 3.2, p. 33; Part B-2, Section 5.2, p. 36); minor, impl-host.
- E2-f — Sentinel-2 10 m/20 m band mix and pixel-purity criteria unstated (Section 1.2, p. 26); absorbed into W12.

## Lens E3 — MSCA generalist

### Criterion 1 — Excellence

**Strengths:**
- The four objectives are each bound to dated deliverables (D1.1 M2, D1.2 M3, D1.4 M3, D2.1 M20, D2.2 M21, D3.1–D3.2 M24, D4.1–D4.2 M30) and to pre-specified metrics, so they are measurable and verifiable (Section 1.1, pp. 24–25).
- Freezing the model at M3 before any prospective outcome is observed, and reporting primary performance before recalibration, makes the central hypothesis falsifiable (Section 1.1, p. 25; Section 1.2, p. 26).
- The integration of disciplines is explicit and role-assigned: physiology at HUN-REN ATK, the archive at MATE, Earth observation at ELTE, software and farm-management perspectives at Krumatic/AgroVIR, with the fellow as integrator (Section 1.2, p. 26).
- Supervision is structured: one-to-one meetings, specialist technical sessions, "monthly written progress monitoring", a Project Steering Group with pre-defined decision responsibilities and a two-step conflict-resolution route (Section 1.3, p. 27).
- The two-way transfer is concrete in both directions, and the six-month non-academic placement is integral, end-positioned, non-academic and justified for both project and career (Section 1.3, p. 27). The gender dimension is addressed with a justified non-relevance statement (Section 1.2, p. 26).

**Weaknesses:**
- The supervisors' qualifications are asserted, not evidenced: no supervision record at PhD or postdoctoral level, no named international collaborations, and one cited paper each for Dr Hollós and Prof. Jung (Section 1.3, pp. 26–27, footnotes 5–6; Part B-2, Section 5.2, p. 36). [major]
- The CV omits the template's minimum content: no full dates for professional experience or education, the current MVCRI position and the Kleffmann employment are undated, the 34-month career break is undated within "2021–2024", outputs carry no significance or open-access notes, and invited talks, funding and supervision are not listed (Part B-2, Section 4, pp. 34–35). [major]
- Section 1.4 (p. 28) states the fellow "is holding Environmental Engineering Master's degree", whereas the CV lists "Second MSc studies in Environmental Engineering (2025–2026)" (p. 34). [minor]
- Training is described by topic only, without named courses, providers or timing; teaching is limited to "Guest lectures and practical activities at MATE and, where feasible, Agricultural University–Plovdiv" (Section 1.3, p. 27). [minor]
- The first secondment block (M1–M3) coincides with the protocol lock and model freeze; how primary supervision at HUN-REN ATK operates while the fellow is at ELTE is not described (Section 1.3, p. 27; Section 3.1, p. 31). [minor]
- Open-science commitments stop at principles: analysis code and derived outputs are shared "where institutional, commercial and IP rights permit", with no repository, licence, preprint or public pre-registration named; replication and sample sizes for the prospective validation are not stated (Section 1.2, p. 26). [minor]

**Score:** 3.7 — The objectives and staged design are very good, but two of the four aspects (supervision evidence; the researcher's CV) fall short of the template's minimum content, and training remains generic: several shortcomings, two of them major.

### Criterion 2 — Impact

**Strengths:**
- Career measures are concrete and evidenced: two named post-fellowship trajectories, a Career Development Plan (D5.1, M3), a measures table that ties each measure to a deliverable or KPI (K11), and a placement with its own deliverables (Section 2.1, pp. 28–29).
- The exploitation and IP strand is unusually mature for a fellowship: four exploitable result families, separate rights layers, a dated DrR baseline declaration and a defined ATK–Krumatic agreement (Section 2.2, pp. 29–30).
- Dissemination targets are quantified and dated (≥2 peer-reviewed manuscripts, EGU/ECPA presentations, ≥1 end-user workshop; K13 by M30) (Section 2.2, p. 29; Section 3.1, p. 31).
- End-users are involved in requirements and evaluation, in line with the action's call for end-user co-creation (Section 1.2, p. 26; Section 3.2, p. 33).

**Weaknesses:**
- The communication strategy lacks the main messages, tools, channels and timing per target group that the template requires; "public-facing articles; farmer/end-user workshop; institutional and public-engagement activities" are listed without specification, and "reach indicators" are undefined (Section 2.2, p. 29). [major]
- Magnitude is not quantified: no estimate of the irrigated area, grower base or FMIS user network addressed, no link to EU water or agricultural policy frames, and a generic European row; "no numerical water-saving benefit is claimed in advance" leaves the aspect largely unaddressed (Section 2.3, p. 30). [major]
- Leadership, grant writing and network building are named as skills but not converted into measures (no planned grant application, network membership or mentoring role) (Section 2.1, p. 28). [minor]
- The CDP review cadence is inconsistent: "quarterly Career Development Plan reviews" (Section 1.3, p. 27; Task 5.1, p. 31) against "reviews M3/M12/M21/M24/M27" (Section 2.1, p. 28). [minor]

**Score:** 3.6 — Career and exploitation measures are credible and specific, but the magnitude of the contribution is unquantified and the communication plan is generic: several shortcomings including two major ones.

### Criterion 3 — Quality and efficiency of the implementation

**Strengths:**
- The work plan is complete and internally consistent: five WPs with monthly task windows, thirteen dated deliverables, six milestones, K1–K14, effort summing to 30.0 PM, and a Gantt in elapsed months showing secondment blocks and placement (Section 3.1, pp. 31–32).
- Milestones operate as decision gates with named approvers ("The fellow and ATK approve scientific gates with specialist input; AgroVIR co-reviews MS4–MS6") and an explicit critical path (Section 3.1, p. 32).
- Each risk has an owner and a trigger response, monitoring is monthly, and an integrity rule is stated: "Poor transfer is a reportable scientific result; it does not authorise unsupported advice" (Section 3.1, p. 32).
- Host capacity is documented: phenotyping and Fitotron facilities, MSCA IF coordination (LANDRACES) and Horizon Europe participation at ATK; EO laboratory and QUEST coordination at ELTE; FMIS infrastructure and a national R&D project at AgroVIR (Part A, p. 11; Part B-2, Section 5.2, pp. 36–37).

**Weaknesses:**
- Four of the seven organisations in the capacity table have no formal role (MATE, Krumatic, the unnamed farmer/producer, MVCRI), yet the archive (O1–O2) and the two-season commercial field (O3) depend on them; "Data access and permitted reuse are documented before analysis and exploitation" describes a procedure, and no existing commitment or agreement is stated (Section 3.2, p. 33; Part B-2, p. 35). [major]
- Months 1–3 concentrate archive audit and harmonisation, protocol lock, pipeline build, model fitting and freeze, field-access agreements, IP/architecture agreement, the CDP and the initial dissemination strategy, all during the first ELTE block; the feasibility of this concurrency and the 5.0 PM assigned to WP1 are not justified (Section 3.1, pp. 31–32). [major]
- Hosting arrangements are generic: "ATK provides the scientific environment, infrastructure, workspace, administration and project support required throughout the action", with no description of team integration, onboarding, administrative or relocation support (Section 3.2, p. 33). [minor]
- Part A lists two participating organisations while Part B-2 table 5.1 lists ELTE as a formal participant hosting 12 of 24 months, so the secondment host is not anchored in the administrative forms (Part A, p. 4; Part B-2, p. 35). [minor]
- "The crop calendar must place MS1 before season 1 and the second harvest by M20", but no assumed start month or slipped-start contingency is given (Section 3.1, p. 32). [minor]
- The risk register grades five of six risks identically (M/H) and omits farm commitment, archive reuse rights, AgroVIR withdrawal and supervisor availability; resources for remunerated engineering, sensors, UAV flights and open-access fees are not indicated; deliverable D1.3 is missing from the numbering (Section 3.1, pp. 31–32; Part A, p. 16). [minor]

**Score:** 3.5 — A coherent, gated and consistent plan is offset by two major credibility gaps (informal critical partners; a front-loaded first quarter) and several minor omissions.

### Diagnostic aspect sub-scores (E3)

| aspect_id | sub-score | reason |
|---|---|---|
| exc-obj | 4.4 | Measurable, deliverable-bound, falsifiable objectives; state-of-the-art review rests on four references (Section 1.1, p. 24). |
| exc-method | 4.2 | Sound staged design with justified gender statement; open-science and replication details unspecified (Section 1.2, p. 26). |
| exc-supervision | 3.5 | Structured governance and concrete two-way transfer; supervision track record and named collaborations absent, training generic. |
| exc-researcher | 3.5 | Appropriate physiological profile and documented transition; CV lacks template minimum content; MSc status inconsistent. |
| imp-career | 4.3 | Concrete CDP, trajectories and evidence chain; leadership/grant/network measures unspecified; review cadence inconsistent. |
| imp-dissemination | 3.8 | Strong exploitation/IP and quantified dissemination; communication messages, channels and reach undefined. |
| imp-magnitude | 3.3 | Honest bounding but no quantified reach, policy link or European-level argument. |
| impl-workplan | 3.6 | Complete, consistent, gated plan; front-loaded M1–M3, no start-month assumption, undifferentiated risks, no resource plan, D1.3 gap. |
| impl-host | 3.4 | Capacity documented; hosting arrangements generic; critical dependencies on informal organisations; ELTE absent from Part A. |

### Watch-list verdicts (E3)

- W1 — confirmed at minor in impl-host (formal Risk for Part A completeness; operator to confirm the requirement with the Guide for Applicants / NCP).
- W2 — confirmed at major in exc-researcher (template-explicit: full dates, significance notes, missing categories).
- W3 — confirmed; cosmetic, not scored.
- W4 — confirmed at minor in exc-researcher.
- W5 — confirmed at minor in impl-workplan.
- W6 — confirmed; cosmetic, not scored.
- W7 — confirmed as a Part A ↔ self-assessment consistency Check; not scored by the panel.
- W8 — confirmed at minor in impl-workplan (resources not indicated).
- W9 — confirmed at minor in impl-workplan (generalist reading: dependency acknowledged, assumption absent; agronomic consequence left to E1).
- W10 — confirmed at major in impl-workplan (W11 folded in: WP1 effort not justified).
- W11 — folded into W10.
- W12 — outside this lens; the absence of stated treatment areas and replication is counted once, as minor, under exc-method.
- W13 — confirmed at minor in exc-method (generalist reading).
- W14 — confirmed at minor in exc-obj.
- W15 — confirmed at minor in exc-method (open-science specificity; gender statement acceptable).
- W16 — confirmed at major in exc-supervision.
- W17 — confirmed at minor in exc-supervision (training specificity; first-block supervision continuity undescribed). Same-country 50 % secondment is permitted and justified by EO capacity absent at ATK; not scored.
- W18 — confirmed at minor in exc-researcher (career break treated fairly; transition evidenced by named stays and trainings; DrR prototype undocumented).
- W19 — confirmed at minor in imp-career.
- W20 — confirmed at major in imp-dissemination (template-explicit messages/tools/channels absent); the IP/exploitation strand is a strength to preserve.
- W21 — confirmed at major in imp-magnitude.
- W22 — confirmed at minor in impl-workplan.
- W23 — confirmed at minor in impl-host.
- W24 — confirmed at major in impl-host.
- W25 — confirmed OK: placement and secondment comply with WP pp. 26–27 and 83; nothing contradicts.

Own findings (not on the watch-list):
- CDP review cadence "quarterly" (Section 1.3, p. 27; Task 5.1, p. 31) vs "M3/M12/M21/M24/M27" (Section 2.1 table, p. 28) — minor, imp-career.
- Part B-2 Section 5 contains no inter-relationship declaration although the CV shows co-authorship with MATE (Takács) and MVCRI (Ganeva) staff named in Section 3.2 (pp. 33–35) — formal Check, not scored.
- Ethics table AI page pointer "6" (Part A, p. 18) does not match where AI is discussed (Part A pp. 19–20; Part B-1 p. 26); Part B-2 Section 6 (p. 37) does not mention AI — formal Check, not scored.
- End-user involvement in requirements and evaluation (Sections 1.2, 3.2) matches the action's co-creation expectation — strength under Impact.

# Annex B — Machine-readable findings and revision actions

Identical to the fenced block in II.6 and to `plans/reports/FIELDWISE_ESR_2026-09-08.json` (schema `orch.tier5.esr_review_packet.v1`).
