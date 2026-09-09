# FIELDWISE — Part B1 Scoring Improvement Brief, round two

Prepared: 9 September 2026. Scope: scoring-improvement answers and revision support only; no proposal text or source file has been edited.

**Revision baseline:** `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_refactored_2026-09-08.pdf`, physical pages 1–10, SHA-256 `6fb56e517df9eef5bd5de3258d414b67e0781f44c90a095aad4d0fefcc643371`. The hash matches both attached round-two ESR files. Repository snapshot used for this artefact: `e8e8d23895d0f223a70cccbf986d62ba86b8ad1a`, branch `ESR`.

**Assessment sources:** the user-supplied `FIELDWISE_ESR_round2_2026-09-08.md` and `.json`, including Part I, the findings/action registers, owner decisions, closure matrix and Annex A. The earlier improvement brief and the user's latest edited refactoring instructions remain context and constraints; they are not evidence that a missing fact exists.

This is a new round-two brief, not a replacement of the first brief or another ESR. All page anchors below refer to the refactored PDF, not the sealed full submission. Part A and Part B2 issues are excluded. This document supplies preferred answers, alternatives, fallbacks, necessary consistency changes and a current cut pool for the subsequent editor.

## 1. What offers the highest leverage

The round-two B1-only diagnostic is **Excellence 4.1, Impact 4.1, Implementation 3.7: 80.40/100**. It is 4.60 points below the 85-point Seal score condition, not an estimate of an actual award or a guaranteed improvement requirement. The arithmetic difference from round one's full-application score is not like-for-like. Criterion scores must not be reconstructed by adding estimated gains from individual edits. [ESR: Part I; I-bis.1–3; II.7.3]

| Priority package | Answers in this brief | Why it matters | What it cannot establish |
|---|---|---|---|
| Formal repair, planned before any additions | B18, B20; Section 5 | Tables below 11 pt, Gantt text below 8 pt, protruding table borders | No automatic numerical score uplift; no ten-page-fit guarantee |
| Coherent, testable methodology | B01–B06, B10 | Archive adequacy, spectral screen, sampling, comparator, precision and fallback logic | Actual archive contents, measured performance or achieved power |
| Deliverable field experiment and M3 freeze | B15–B19 | All three evaluators identify the field dependency and early workload as major | Secured land, allocated staff/instruments, funding or schedule slack |
| Supervision and fellow development | B07–B09, B11 | Resolve secondment clashes, make transfer distinctive, specify supervision delivery | Missing supervision totals or proven software/ML capability |
| Impact, engagement and exploitation | B12–B14 | Concrete channels, earlier feedback, decision ownership and defensible magnitude | A national market denominator, adoption or causal water savings |

### 1.1 How to use the answer bank

- **Preferred answer** means the recommended round-two response, not a claim that it has already been adopted or implemented. Earlier accepted decisions are retained unless a correction is explicitly identified.
- **Design proposal** means a prospective FIELDWISE commitment that can be chosen without inventing an existing fact. New numerical tolerances, protocols and activities in this brief are proposals, not measured results or universal standards.
- **Owner fact** means information that the sources do not establish. Use the safe wording now; never turn it into an existing allocation, agreement, qualification or result.
- **Alternative** is a mutually exclusive route, not an extra option to leave beside the preferred route in the final proposal. A scientific contingency can remain in B1 if its trigger and consequences are explicit.
- **Fallback** is the honest floor. It can reduce a claim or stop an activity; it must not relabel failed or unavailable evidence as successful validation.
- Short answer clauses are supplied for the later editor. They are not complete replacement sections. Integrate only their scoring-critical core, preserving prose style and the protected content in Section 5.

No new owner facts are assumed available. The brief therefore distinguishes **answerable now**, **partly answerable**, and **owner-evidence-limited** concerns. A response can make an arrangement credible without fully resolving the ESR weakness.

### 1.2 Corrections to the ESR handout that the next editor must observe

The ESR is the issue inventory; its proposed fixes still need scientific and editorial judgement.

1. **R2-A-05/W2:** differences between unpaired archive seasons are not sensor calibration error. Also, reference-defined physiological classes do not change when spectral processing changes. Define a like-for-like comparison; do not retain the vague “cross-instrument and cross-season consistency” remedy as a complete answer. See B02.
2. **R2-A-06/W3:** a continuous outcome needs a regression model and compatible validation criteria. Classification KPIs cannot simply become secondary if no defensible binary label exists. See B05.
3. **R2-A-08/W4:** distinguish the agronomic comparator, no-spectral ablation model and Brier reference. A baseline cannot be required to outperform itself when it becomes the fallback primary model. See B04–B05.
4. **R2-A-09/W5:** compensation must be negotiated and funded if needed; it is not a universal submission requirement or an available payment. Do not promise compensation without host-approved provision. See B15.
5. **R2-A-10:** do not add “February–March” without remapping the schedule. Under a March start, M3 is May rather than April and the freeze/planting relationship changes. Keep February as the preferred assumption. See B16.
6. **R2-A-16:** the PDF describes ELTE expertise and planned access; it does not prove ATK lacks every equivalent instrument or facility. Explain complementarity without asserting an unsupported institutional absence. See B08.
7. **R2-A-20:** renaming a clinic does not establish entrepreneurship training. Specify provider role, competence and assessed output. See B11.
8. **Formatting:** the ESR corrected its own right-margin measurement. Body-text ink margins pass; table borders remain the issue. Table narrative must be at least 11 pt, overriding the earlier edited prompt's categorisation of all tables as “other text”.
9. **Cut accounting:** R2-CUT-08 and R2-CUT-12 overlap in the same §1.4 sentence. Merge them; do not count the claimed savings twice. R2-CUT-11 was explicitly not offered. See Section 5.

## 2. Answer bank

### B01. Characterise the archive through an auditable adequacy gate

**Covers:** R2-F-01, R2-F-23; R2-A-11/22; R2-OD-01. **Anchors:** p.1 §1.1 O1; p.2 §1.2 “Stage 1”; p.9 R1; p.10 MATE row. **Status:** partly answerable; major evidence gap remains.

**Preferred answer.** Separate the asserted five-season archive from the subset that is legally and scientifically usable. Specify a year-by-variable inventory recording unique treatment areas, area/footprint, cultivar, treatments and irrigation records, control availability, physiological endpoints, dates/stages, spectral instrument/range/calibration and permitted uses. Distinguish records that exist from records with compatible paired variables. Explicitly check whether the 2026 season is complete and quality-controlled; do not infer completeness from the year label.

The M1 gate asks whether the accessible subset supports the *chosen* outcome, common predictors and year/group-aware validation. D1.1 at M2 reports the inventory, exclusions and independent groups; D1.2 fixes the permitted analysis before fitting. Audit all five nominated seasons, but train only on eligible records. At least three eligible years are a proposed minimum for any nested year-based train/validation/test separation; this is a structural floor, not evidence of adequate sample size or precision. Two years do not support the advertised nested leave-one-year-out design. Every held-out fold must have the outcome support needed for its metrics.

**Compact safe answer:** “The M1 access/adequacy gate checks per-season experimental units, controls, paired physiological/predictor coverage, instrument range and calibration. D1.1 distinguishes the five seasons audited from those eligible for modelling; D1.2 locks the admissible subset and validation design before fitting.”

**Alternative.** A smaller multi-year common subset may support a narrower model. Keep K1's audit count distinct from the actual number of eligible training years; update O1/O2, fold count, D1.1–D1.3 and the claim together. Do not keep “five-season validation” if fewer seasons enter it.

**Fallback.** If the physiological outcome or legal access is inadequate, do not promise that “redesign O1–O2” solves the problem. Record a no-go for the historical-to-prospective primary experiment and seek an authorised re-scope. Prospective data cannot become training data while retaining the unchanged-model validation claim.

**Still missing:** actual counts, instruments, variables, dates, controls and rights. No sentence can replace these facts. **Check:** inventory, outcome and validation branches use the same eligible subset; no invented SWIR coverage or archive size.

### B02. Replace the ambiguous spectral screen with two distinct tests

**Covers:** R2-F-02; E2-W01/W07 and processing-baseline note; R2-A-05. **Anchor:** p.2 §1.2 “A predictor is retained only if…”. **Status:** answerable as a clarified design, with an explicit adjustment to the previously accepted screen.

**Preferred answer.** Distinguish **pre-freeze numerical/spectral reconstructability** from **prospective sensing-scale transfer**.

1. Before fitting, apply the wavelength, calibration and footprint requirements. Name a small candidate predictor dictionary: for example NDVI using B8/B4; NDRE using B8A/B5 only if covered; NDMI using B8A/B11 only if SWIR coverage is proven. These are candidates, not assertions of available archive bands. Avoid retaining highly redundant indices merely to fill the dictionary.
2. For numerical stability, compare synthetic indices derived from the **same calibrated spectrum** using a declared reference integration and the proposed resampling/integration pipeline. If genuinely paired common-target observations exist across instruments, test those separately. Do not compare arbitrary seasons and call their biological differences sensor error.
3. Retain the 0.25 historical-SD discrepancy tolerance only as a proposed engineering screen: median absolute candidate-versus-reference index difference, normalised by the appropriate historical training-partition SD. Handle a zero/near-zero SD by exclusion, not division by an unstable value. Archive-dependent acceptance and feature selection remain inside training folds; final fitting uses historical data only.
4. Reclassify the existing ≤10% stress-class-change figure as a **post-fit sensitivity diagnostic**, not proof of pre-model physiological class consistency. Compare the same fitted fold model's predictions under declared processing perturbations. It must not tune the model using outer-test or prospective labels. Physiological labels themselves remain unchanged. The decision threshold is historically selected as in B04.
5. Prospectively compare paired canopy-derived synthetic indices with actual Sentinel-2 values for the same treatment-area support and accepted time window. Report bias, dispersion and prediction sensitivity by stage/season and canopy cover. This measures combined radiometric, footprint and environmental discrepancy unless the design genuinely separates them. Never reselect predictors or alter the primary mapping after M3.

The retained numerical tolerances are conservative **project engineering choices**, not published equivalence standards or demonstrated performance. Document their sensitivity in D1.2. Official Sentinel documentation supports sensor-specific response functions and distinct spatial resolutions; it does not supply FIELDWISE's thresholds. [Copernicus Sentinel-2 mission](https://sentiwiki.copernicus.eu/web/s2-mission), [SRF document library](https://sentiwiki.copernicus.eu/web/document-library).

**Compact answer:** “Pre-freeze QC tests reconstructability and like-for-like integration stability, not satellite equivalence. The physiological reference is independent of spectral processing. Paired prospective canopy–Sentinel observations quantify transfer and canopy-cover sensitivity without changing the M3 predictor mapping.”

**Alternative.** Drop the unsupported numerical screen from feature-retention decisions and use documented coverage/calibration/QC requirements, retaining both numbers only as explicitly exploratory sensitivity flags. This is cleaner if no meaningful numerical reference is available; record the change to the earlier preferred answer.

**Fallback.** Exclude unsupported bands before freeze, retain the no-spectral baseline, and distinguish “transfer not testable” from measured poor transfer. A VNIR-only archive cannot support invented SWIR predictors. Pin satellite unit, SRF file/version, Level-2A processing baseline and any offsets; a later processor update is not permission to change the frozen pipeline silently.

### B03. Make pixel eligibility and observation matching executable

**Covers:** R2-F-03; R2-A-07; R2-OD-08. **Anchors:** pp.2–3 §1.2 pixel rules/Stage 2; p.9 R3; p.10 farmer row. **Status:** answerable design; field geometry remains an owner fact.

**Preferred answer.** Treat 80 × 80 m areas and 40 × 40 m interior cores as nominal design targets. At field readiness, overlay the actual Sentinel-2 20 m grid and retain at least four **whole, eligible** interior pixels per treatment area, in addition to the existing ≥90% treatment-cover requirement. Align or enlarge the candidate areas before randomisation if necessary; do not admit boundary/buffer pixels simply because they meet treatment cover. No interpolation or super-resolution creates additional independent native pixels. The 7.68 ha remains nominal, not a guaranteed footprint after alignment, isolation and access requirements.

Adopt a proposed primary matching rule: physiology and Sentinel acquisition on the same date, with physiological measurements within ±2 hours of the actual overpass time, subject to a no-intervening-irrigation/rainfall/disturbance check. Record the actual lag. This is a protocol target to test in the logistics dry run, not a universal physiological tolerance. Broader ±1-day matches, if scientifically justified, belong in a separately labelled sensitivity analysis, not the primary pool. An archive timestamp too coarse for this matching is a recorded limitation.

Keep the 30% loss scenario, but add 10% and 50% sensitivity cases: approximately 259, 202 and 144 retained area-date records out of 288. These are arithmetic planning scenarios, not forecast availability. Whole cloudy campaigns can remove many correlated records; class balance and independent units matter as much as the total. Report scheduled, attempted, matched, label-valid and model-usable denominators separately.

**Alternative.** Use a same-date-only pairing rule without a claimed hour limit if timestamps do not support finer matching; quantify the resulting temporal uncertainty. This relaxes the preferred within-day control, so the proposal must acknowledge that reference synchronisation remains less controlled.

**Fallback.** A date with fewer than four eligible pixels has no primary spectral prediction. Retain physiology and valid no-spectral observations for their pre-specified analyses; do not relax purity or inflate n. A site that cannot support the spatial rule fails field readiness.

**Check:** distinguish treatment cover from canopy cover, native pixels from resampled cells, and scheduled campaigns from valid matches. Grid alignment cannot be confirmed without polygons.

### B04. Define comparators, precision and lead time without claiming achieved power

**Covers:** R2-F-04; E1-W02/W08; E2-W04/W05; R2-A-08/30. **Anchors:** p.3 §1.2 decision criteria; p.8 K6. **Status:** design answer now; achieved precision remains unproven.

**Preferred answer: three distinct references.**

| Role | Proposed definition | What it tests |
|---|---|---|
| Agronomic alert comparator | A pre-specified root-zone soil-water/depletion rule, informed by the documented AquaCrop/irrigation protocol; parameters fixed from historical/agronomic information, never prospective physiology | Advantage over an operational agronomic rule |
| No-spectral ablation | Same regularised model family and outcome, using the locked soil-water/meteorological predictor subset without spectral inputs | Incremental information supplied by spectra |
| Brier reference | A constant historical training-prevalence probability, estimated within each training fold; final reference frozen from the eligible historical data | Probabilistic skill against a simple, independent reference |

Do not call the generic phrase “AquaCrop/soil-water rule” a complete executable comparator. D1.2 must identify the variable, threshold source, aggregation and alert rule. Where that agronomic rule cannot be justified, name the ablation as the available comparator and narrow the claim accordingly.

Retain balanced accuracy ≥0.70, sensitivity ≥0.80, FPR ≤0.20 and positive Brier skill as project targets. Select alert thresholds on **inner out-of-fold** historical predictions within outer training sets. Outer held-out years assess the entire selection pipeline; choose the final threshold under the same declared rule using historical data only. Separate continuous model output from the resulting alert.

**Precision answer:** pre-specify 95% uncertainty intervals and a proposed design target of balanced-accuracy interval half-width ≤0.10. Assess paired model-minus-comparator differences on the same eligible observations. A positive lower interval bound supports an advantage claim; an interval spanning zero does not. Meeting a point target with inadequate precision is not a deployment pass. With few blocks/areas, report sensitivity of intervals to the dependence model and non-estimability honestly; do not bootstrap individual plants or dates as independent replicates.

At protocol lock, simulate the *actual* block/area/time structure once archive information is available, exploring loss of 10/30/50%, varying event prevalence and plausible within-area dependence. Carry both years of the same area together and preserve block/control relationships. Pre-specify what precision permits a supported claim. **No simulation result or power percentage is asserted here.** If precision is inadequate, report the planned test as estimation/feasibility evidence and restrict operational claims; adding plants does not fix too few independent units.

**Lead-time answer:** define onset as the interval between the last determinate non-stress physiological observation and the first determinate stress observation under the locked reference. Relative to a prior alert at time t, report the onset interval minus t. Retain negative or indeterminate values where appropriate; do not convert coarse campaign spacing into exact advance-warning days. At alert time use only inputs already available; same-day data acquired later would be look-ahead. First-observation stress is left-censored, and indeterminate measurements do not establish onset.

**Alternative.** A precision-led test without the ±0.10 target can report full interval widths and a pre-registered decision rule. It is less specific but preferable to invented power. **Fallback:** non-estimable classification/lead-time metrics are marked not estimable, with denominators; no accuracy or advisory claim is manufactured. **Residual:** F-04 is only partly resolved until information supports the design's precision.

### B05. Lock a complete fallback hierarchy, not incompatible promises

**Covers:** R2-F-05 and fallback parts of F-02/04/18/23; R2-A-06. **Anchors:** p.2 reference fallback; pp.6–7 result families; pp.8–9 K5/K6/MS3. **Status:** scientific consistency correction; explicit model/metric choices below are new proposals.

**Preferred answer.** Select the scientifically admissible branch using historical adequacy information before fitting, register it in D1.2, and freeze it at M3. Do not wait for prospective performance to select the most favourable branch.

| Branch and trigger | Model and primary evidence | Metrics and claims | Required consequences |
|---|---|---|---|
| Binary physiological reference and defensible spectra available | Regularised logistic model; constrained tree benchmark; independent physiological labels | Existing discrimination/calibration/alert criteria plus B04 comparators | Normal O1–O4 pathway, conditional on validation |
| Only a valid continuous physiological reference is available | Regularised linear regression on a pre-specified scale/transformation of the control-relative endpoint; restricted nonlinear regression benchmark only if feasible | MAE/RMSE, bias, prediction-interval coverage and error skill against a historical-mean and no-spectral regression baseline; acceptable error derived before fitting from reference repeatability and intended interpretation | Amend O2, D1.2/D1.3, K3/K6, model card, outputs and MVP labels. No stress probability, Brier score or classification KPI unless an independently justified binary reference also exists |
| Spectral conversion unavailable before freeze, but physiological and no-spectral data adequate | Frozen soil-water/meteorological model in the admissible outcome family | Skill versus the appropriate independent simple reference; no incremental-spectral claim | Deliver an archive/reconstructability limitation report, not demonstrated poor satellite transfer; restrict the sensing-scale result family and MVP scope |
| Frozen spectral model transfers poorly prospectively | Report that model's unchanged primary performance first; separately report the already locked no-spectral baseline and any pre-specified secondary recalibration | Measured negative transfer is valid evidence | Research-only display; no irrigation advice from failed functions; D2.2/D1.4 retain the negative result |
| One season lost, or reference/control support inadequate | Analyse only the genuinely observed, admissible evidence | K5 target not met; K6 restricted; no fictitious second season or replacement primary dataset | D2.1/D2.2, MS3 and exploitation claims state the limitation; substantive redesign/rephasing requires the appropriate approval |

A continuous branch does not guarantee probabilities or calibrated alerts. “Classification KPIs secondary” is permissible only if the branch has a separately justified label definition; otherwise they are not applicable. The regression branch's acceptable-error number cannot be fabricated without endpoint/repeatability information.

**Alternative.** Keep a binary primary reference with one validated physiological marker and independent corroboration only if historical controls support a defensible pre-fixed dichotomisation. Do not invent a cut-off to preserve logistic regression. This changes the earlier two-marker preference and requires a recorded scientific decision.

**Fallback.** If no defensible reference exists, the core predictive-validation objective is not executable. Preserve the evidence package and seek a re-scope; do not present a technically working MVP as a scientifically validated substitute.

**Protected-text exception:** update unconditional “validated MVP/workflow” result-family language only where required by this accepted evidence-gating logic; retain the four result families as intended outputs, conditional on admissible evidence. Do not remove the rights-layer or poor-transfer integrity statements.

### B06. Make the physiological campaign operationally credible

**Covers:** R2-F-10, staffing parts of F-24; E1 logistics and sensor-density notes; R2-A-18/26. **Anchor:** p.3 Stage 2; p.10 farmer/ELTE rows. **Status:** protocol answer; staff/equipment allocations unavailable.

**Preferred answer.** Budget and plan for 60 plant measurements per campaign (12 areas × five plants), 24 campaigns and approximately 1,440 plant visits. These are repeated measurements, not independent n. Use the B03 overpass-centred window; rotate block order, interleave each block's control with deficit treatments, standardise leaf/stage selection and log time, temperature/VPD, irrigation, genotype and competing stress. Balance operators across treatments and use a shared repeatability check. Aggregate plants to the treatment-area/date reference using a locked rule; matched control normalisation and any validity filters must not be inferred from model success.

Specify a **planned minimum delivery arrangement** to be tested before launch: two trained measurement operators, one of whom may be the fellow, plus a field/logging coordinator role that may be combined only if the dry run demonstrates throughput. This is a staffing requirement, not a statement of allocated personnel. A timed full-circuit dry run checks that physiology and corroborating measurements for all areas fit the pairing window; any proposed reallocation of roles needs a successful rerun.

For soil-water monitoring, require a representative root-zone measurement profile in each independently managed treatment area, with depths and placement fixed from the site's rooting/soil conditions. Log irrigation separately for each treatment area and weather at a representative site location. A single farm-average moisture reading cannot substantiate twelve independently imposed regimes. Equipment type, calibration, maintenance, instrument sharing and data ownership belong in the readiness record; do not invent procurement quantities as existing assets.

**Alternative.** Two synchronised sub-campaigns with matched controls and timestamped strata can be analysed separately if the physiology/EO pairing and area coverage remain valid. Do not call different-day measurements one simultaneous campaign.

**Fallback.** If staffing or instruments cannot deliver the design, reduce optional measurements first, not independent areas or the primary physiological reference. Missing windows remain missing. If the essential reference cannot be delivered, do not launch that test.

**Residual:** the proposal can specify the resource requirement; it cannot establish who or what has been allocated. The current 30% loss scenario is not a staffing plan.

### B07. Strengthen supervision delivery without inventing its track record

**Covers:** R2-F-06; E3-W04; R2-A-23; R2-OD-03. **Anchor:** p.4 §1.3. **Status:** partly answerable; evidence-limited.

**Preferred answer.** Preserve Janda's documented doctoral-school/teaching record and the named 2023 co-supervision example. Distinguish that example from a completed-PhD total. Retain Jung's documented spectroscopy/EO role, doctoral-programme and teaching experience, and the relevance of his 2010 white-reference method to this project. Retain Hollós' **2026** modelling publication already cited in footnote 8; the ESR's old-publication concern about Jung must not be generalised to all specialists.

Make the already declared two-step conflict route executable: first a recorded fellow/supervisor discussion with agreed action; if unresolved, or the supervisor is implicated, referral to a designated host contact outside the dispute through the host's applicable procedure. Describe this as the proposed escalation arrangement, not an invented institutional policy. Retain weekly M1–M3 meetings and propose at least fortnightly primary-supervisor contact thereafter, with monthly written monitoring and quarterly CDP reviews. Integrate this with existing sessions rather than adding several duplicate meeting series.

Before a prolonged absence, require ATK to designate a suitably qualified alternate for the relevant competence and record authority at the next gate. A deputy's name is unavailable; do not invent one or assert that one has already been appointed. A scientific gate is not passed without competent review.

**Alternative.** One additional verified topic-relevant output or documented supervision outcome can replace generic seniority text if a source is supplied. Do not search for a flattering aggregate number and treat it as current capacity.

**Fallback.** Keep the existing evidence and the proposed governance routine; label the track-record finding only partly answered. No public CV or promised meeting cadence proves allocated time, current collaborations or postdoctoral supervision outcomes.

**Check:** historical expertise, proposed supervision and current availability remain three distinct claims; no phantom institutional complaint route or named deputy appears.

### B08. Explain twelve ELTE months and remove the location clash

**Covers:** R2-F-07; R2-A-04/16/32; R2-OD-06. **Anchors:** p.4 training; pp.5–6 §2.1; p.8 K11; p.10 ELTE row. **Status:** answerable in design; access/staff facts remain open.

**Preferred answer.** Retain M1–M3, M10–M12 and M16–M21, twelve months total. Describe ATK-led practicals in overlapping months as **ATK-led through the joint sessions while the fellow is based at ELTE**, not “at ATK”. Do not claim remote delivery can replace laboratory work requiring physical access; schedule any essential visit explicitly without double-counting residence or secondment effort.

Give each block a research purpose beyond attendance: M1–M3 builds the reproducible harmonisation and QC pipeline; M10–M12 analyses first-season transfer and prepares the unchanged second-season workflow; M16–M21 combines paired sensing with prospective acquisition/QC and synthesis. The middle block does not change the primary model. Explain the difference from the prior traineeship: independent responsibility for a frozen cross-scale validation pipeline and its assessed outputs, rather than introductory EO exposure.

The added value is sustained specialist supervision and working integration of spectroscopy, geoinformatics and satellite processing across successive evidence stages, complementing ATK's physiology/modelling accountabilities. Do not assert that ATK lacks particular equipment without evidence. Second-season field days are WP2 work conducted during the relevant ELTE block, not a second full-time allocation; travel, access and measurement staffing must pass B06/B15 readiness.

**Alternative.** Consolidate ATK instruction into the existing joint sessions and move non-critical classroom material outside peak field windows. Keep all twelve secondment months and their substantive tasks, rather than using a course label as justification for residence.

**Fallback.** Require access before each block and withhold activities needing unavailable facilities. Reducing or relocating the secondment is a substantive alternative requiring an approved schedule and K11/Gantt update, not a silent editorial fix.

### B09. Make the fellow's contribution distinctive, not overstated

**Covers:** R2-F-08, R2-F-11; R2-A-17/25; R2-OD-05. **Anchors:** p.4 “Two-way transfer”; p.5 §1.4. **Status:** current evidence supports better linkage, not a stronger invented record.

**Preferred answer.** Link the documented physiology/vegetable-crop experience to independent reference design and production-context interpretation; the MATE stays and ELTE traineeship to archive familiarity and EO workflows; and the pre-existing DrR prototype to translating a physiological question into a software specification. State that advanced predictive modelling is an assessed development objective, supervised by Hollós, rather than already proven expertise. Do not promise that brief training guarantees the M3 freeze.

For fellow-to-host transfer, identify tangible new outputs the host teams receive: a documented control-relative phenotyping workflow, annotated crop/production-context cases, and a teaching practical that links stress physiology to uncertainty-qualified decision support. These are planned outputs derived from her experience, not claims that the hosts lack physiology expertise. The Bulgarian production perspective and prototype-development experience differentiate the contribution without claiming exclusive knowledge.

**Compact answer:** “The fellow contributes vegetable-crop phenotyping and Bulgarian production-context experience through a documented reference protocol, annotated cases and a joint teaching practical; specialist supervision develops the modelling competence required to test those observations reproducibly.”

**Alternative.** Add a dated DrR version, implemented function and reproducible demonstration only if the fellow supplies evidence. Treat any new demonstration as current work with its actual date, not retrospective proof of past maturity.

**Fallback.** Retain “pre-existing desktop research prototype”; no function list, validated release, repository or individual manuscript contribution is invented. Preserve the 2025 proceedings and two 2026 manuscripts as described, with “under review”; no MSc award or training certificate is added. Do not add publication counts merely to satisfy a quantitative-looking response.

### B10. Replace the universal novelty claim with an evidenced comparison

**Covers:** R2-F-09; R2-A-27; satellite-literature component of R2-OD-08. **Anchor:** p.1 §1.1 “Pertinence”. **Status:** answerable now from public research, not an owner-only question.

**Preferred answer.** Keep the existing thermal/CWSI, FAO-56/AquaCrop and processing-tomato ML comparators. Add one directly relevant satellite-scale example: Dalla Marta et al. (2019), *Integrating Sentinel-2 Imagery with AquaCrop for Dynamic Assessment of Tomato Water Requirements in Southern Italy*, Agronomy 9, 404, DOI `10.3390/agronomy9070404`. It examines Sentinel-2 canopy information and irrigation-water-requirement assessment, including integration with AquaCrop. FIELDWISE's distinct claim is the prospective test of an independently physiological, historically frozen predictor pipeline—not that satellite-based tomato irrigation research does not exist. [Dalla Marta et al.](https://doi.org/10.3390/agronomy9070404)

**Proposed local replacement for the categorical clause:** “Satellite-informed tomato irrigation approaches already estimate canopy development and water requirements. FIELDWISE tests a distinct evidential step: whether a historically frozen, independently physiology-referenced model retains calibration and discrimination when deployed through actual Sentinel-2 observations in an independent commercial environment.”

This expresses the intended contribution without claiming a comprehensive proof that no predecessor used any part of it. Preserve the four challenged assumptions and three advances in the following protected paragraph.

**Alternative.** Vanino et al. (2018), *Capability of Sentinel-2 data for estimating maximum evapotranspiration and irrigation requirements for tomato crop in Central Italy*, is another directly relevant comparator. Its title/publisher record was identified in this review; verify detailed methods before making a method-specific contrast. [Publisher record](https://www.sciencedirect.com/science/article/pii/S0034425718303134)

**Fallback.** Even without space for another footnote, remove “none has been tested…” and bound the claim to what FIELDWISE will test. This narrows overstatement but does not fully answer the literature gap. Count the footnote's actual wrapping cost; do not remove an existing unique source to create nominal reference space.

### B11. Specify transferable-skills training and post-fellowship positioning

**Covers:** R2-F-12, R2-F-16; R2-A-20/29. **Anchors:** p.4 training; pp.5–6 §2.1; p.10 MVCRI row. **Status:** proposed activities, not owner facts or promised appointments.

**Preferred answer.** Extend the existing M22–M30 ATK-support/AgroVIR activity into assessed grant-writing, valorisation and entrepreneurship learning: an IP/ownership map, user-value proposition, costed route-to-use options and a mock decision on licence/service/start-up/no-commercialisation. Provider roles are the already named supervision and research-support/placement roles; specialist delivery must be arranged before use, not claimed as an existing named course or guaranteed enrolment. Research-only results must allow a “no commercialisation yet” conclusion.

Make career positioning an action: by M24 the fellow prepares a portfolio linking the protocol, analysis, teaching and MVP evidence to agricultural-data-scientist/research roles; by M27 she compares two realistic position types or eligible funding routes; by M30 she prepares one tailored application or research-line pitch. No job, award or institutional continuation is guaranteed. The existing grant concept and mock-reviewed application by M21–M24 supply most of the work, avoiding a duplicate application requirement.

**Alternative.** A named, verified external course can substitute for part of the planned clinic if accessible and suitable, but do not introduce new course costs, places or eligibility assumptions here.

**Fallback.** Supervisor-assessed self-study using public training materials and a documented peer/mock review replaces unavailable external instruction. MVCRI remains one possible continuation route, not the condition for career success. A portfolio and role-specific pitch remain deliverable without an open vacancy.

**Check:** provider role, period, competence and assessed output all appear; D5.1 M3 and quarterly CDP reviews remain unchanged. A new title alone does not close F-12.

### B12. Quantify the achievable impact envelope, not an invented market

**Covers:** R2-F-13; R2-A-24; R2-OD-04. **Anchor:** p.7 §2.3. **Status:** partly answerable; wider agricultural/economic magnitude remains evidence-limited.

**Preferred answer.** Retain the three scales and state a quantified **direct evidence envelope**: one crop and one commercial environment, two planned seasons, twelve treatment areas per season, up to 288 area-date records, evaluation with 6–10 growers/advisors and 2–3 technical users, one approximately 20-person workshop. These are the project's intended evidence and engagement scale, not unique farm totals, adoption or a representative survey. Do not sum overlapping participants, treat every advisor as a farm, or multiply hectares by years and call it unique area.

Quantify *importance* through what the study can decide: paired model-versus-baseline performance and uncertainty; counts/fractions of valid, abstained and misleading outputs; correctly interpreted uncertainty; user task completion and critical usability problems. Report numerators/denominators, not just activity counts. B04's decision thresholds describe the planned value test, not benefits already achieved.

Move the **definition** of eligibility earlier: by M12 specify crop, irrigation, native-pixel geometry, reference/data availability and user capability requirements; by M24 assemble a source-labelled screening method; during placement apply it only to the genuinely accessible network and record the denominator/date. Do not claim that access to AgroVIR customer data has become necessary. Public land-use statistics or voluntary screening can describe a broader context but cannot establish AgroVIR's crop-specific subset.

**Alternative.** If a documented local/regional processing-tomato irrigation denominator becomes available, use one bounded number with geography, year, crop/use definition and source. Explain why only part is technically eligible. Do not use all tomato area or the reported 700,000 ha company footprint as eligible uptake.

**Fallback.** Use the direct envelope and measured decision value, with wider uptake unquantified. An illustrative formula `eligible area × uptake fraction × validated effect` may guide later scenario work but supplies no number now: each factor is unknown, and causal water-saving effect is not estimated by this design. Do not invent adoption percentages, euro benefits or water savings to remove a major finding.

**Residual:** this improves assessability and honesty but may not fully satisfy the ESR's requested wider magnitude. Preserve verbatim “no numerical water-saving benefit is claimed in advance.”

### B13. Name public channels and begin feedback before the placement

**Covers:** R2-F-14, R2-F-17; R2-A-14/28; R2-OD-08. **Anchors:** p.6 Communication row; p.7 reach; p.8 WP3/WP4. **Status:** new planned engagement procedure; no guaranteed recruitment.

**Preferred answer.** Use a fellow-maintained public project page for the already planned explainers, tutorial and Hungarian/Bulgarian summaries, linked to the persistent research outputs. Add an accessible question/feedback route and a brief “questions received and responses” record. Host, ELTE and AgroVIR channels amplify the material only where agreed. Avoid committing to a platform licence or host website access that is not established.

At M12, use the existing practitioner brief to open an early **requirements/interpretability** round, targeting a subset of approximately 3–4 of the planned 6–10 growers/advisors. Revisit provisional uncertainty displays at M21–M24; retain the M25–M30 placement for intensive operational/interoperability evaluation. Count repeat participants once in the total reach and separately as repeat contacts. These early sessions do not change the frozen scientific model or expose unvalidated output as irrigation advice.

Recruit through project-controlled invitations and professional contacts, with AgroVIR support where available; no recruitment success is guaranteed. Record response rate, farm context, digital literacy, task completion and misinterpretation themes, using the existing consent/minimisation safeguards. Public engagement is two-way through questions and responses; it need not become a new citizen-science experiment.

**Alternative.** One remote facilitated discussion linked to the M12 brief can replace a separate event; use existing communication effort and targets rather than adding travel.

**Fallback.** If recruitment fails, document attempts and use a clearly labelled expert walkthrough for interface refinement. It is not grower validation and does not meet the grower target. Publish the outputs and open feedback route regardless; placement recruitment stays an unresolved dependency rather than a guaranteed channel.

### B14. Assign exploitation decisions now, while keeping commercial commitments conditional

**Covers:** R2-F-15; R2-A-15; B05 result-family consequences. **Anchors:** pp.6–7 exploitation; p.8 K10. **Status:** answerable governance; rights/funding remain conditional.

**Preferred answer.** Tie the existing routes to current gates and accountable roles rather than defer all ownership to a future roadmap:

- **MS3/M21:** fellow and ATK decide which functions have sufficient scientific evidence; failed functions do not become advisory products.
- **MS4/M24:** ATK with the fellow checks release scope, rights, reproducibility and critical tests; engineering acceptance and placement scope are recorded.
- **MS5/M27:** AgroVIR supplies operational assessment; ATK/fellow compare integration, licensing/service and continued research routes using that evidence. Participation in the review is a proposed role, not a licence or investment commitment.
- **MS6/M30/D4.2:** the responsible rights holders decide the authorised next step, required resources and unresolved conditions. K10 already requires owners and decision gates: make that connection explicit in §2.2.

The decision can be “research-only release and further validation”; a start-up or licence is not a required successful outcome. MVCRI crop extension remains optional and separate from in-action delivery.

**Alternative.** A compact one-sentence gate chain can replace a new table in B1. Preserve the protected IP row and exploitation pathway; append or make only necessary conditionality corrections.

**Fallback.** Without cleared rights or a funded continuation route, release the rights-cleared evidence package and limit the roadmap to conditions for further work. No proprietary source-code access, partner agreement or commercial readiness is implied.

### B15. Define a field-readiness decision that protects producer and science

**Covers:** R2-F-18; E1-W14 rotation concern; R2-A-09/10/13; R2-OD-02. **Anchors:** p.3 Stage 2; p.9 MS1/R2; p.10 farmer row. **Status:** major owner-evidence-limited dependency.

**Preferred answer.** Make field readiness a named element of **MS1 at M3**, completed before irreversible planting/interventions, not merely a plan agreed at the same time as data collection. Require identified polygons passing B03, independent irrigation control, usable reference/control areas, site/soil/crop history and two-season agronomic suitability, access terms, sensor/staff provision, data handling, and a named producer contact. Check local crop-rotation/soil-health constraints with an agronomic adviser; do not dismiss the two-consecutive-tomato-seasons concern or assert a universal prohibition.

Identify the producer's burden explicitly: land occupied, management restrictions, irrigation labour and potential yield/quality loss in deficit/unirrigated areas. Proposed terms must document irrigation responsibilities, ownership/use of produce and data, withdrawal, and allocation of costs and crop-loss risk. If compensation or other consideration is necessary, its basis and funding must be approved before interventions; no amount, available fund or acceptance is asserted. Participation can also be on agreed non-cash terms if the producer accepts them and the host's rules permit; do not assume free land or risk-bearing.

**Compact safe answer:** “MS1 includes a pre-intervention field-readiness decision covering native-pixel geometry, irrigation isolation, two-season agronomic suitability, staffing and instruments, and host-approved producer terms including costs and crop-loss risk. No field, compensation budget or backup is claimed as secured.”

**Alternative.** Two matched fields in successive years may be more agronomically suitable if genuine access is available, but this is a substantive design change: site and year become confounded; do not call it two independent environmental replicates or the same-field experiment. Update O3, units, sampling, uncertainty, K5/K6 and MS3 together. This alternative is not silently authorised by the earlier preference.

**Fallback.** A genuine backup site must pass the same requirements before use. If none is ready, no experimental planting/irrigation intervention starts under the claimed protocol; seek an approved rephase/re-scope. One observed season is reported as one season. A procedure does not eliminate F-18 without evidence of an achievable site.

### B16. Protect the M3 freeze and justify effort through a minimum executable pipeline

**Covers:** R2-F-19, R2-F-20; R2-A-19 and calendar parts of A-10; R2-OD-01/02/06/07. **Anchors:** pp.8–9 WP1–WP3/critical path; p.4 training. **Status:** stronger planned prioritisation; feasibility remains conditional.

**Preferred answer.** Keep February as the preferred start assumption, M3/April freeze before M4/May principal observations, five WP totals and the accepted PM matrix. Describe the first quarter as sequential gates within existing tasks, not simultaneous completion of every ambition:

| Period | Critical output and decision | Work deliberately bounded |
|---|---|---|
| M1 | Legal access and archive adequacy; candidate field screen; reproducible data/QC scaffold | No speculative feature search; essential rights/scope work only |
| M2 | D1.1; reference definition and protocol registered before fitting; baseline pipeline and nested-fold dry run | Small predictor set, one primary family; training assessed through these same artefacts |
| M3 | Complete historical fitting/validation under the locked protocol; freeze D1.3; MS1 field readiness; D5.1 | No prospective tuning; no discretionary interface work competing with freeze |

Protocol definition precedes T1.3 fitting even though D1.2's formal delivery month is M3. T3.1 in M1–M3 supplies only indispensable background/IP boundaries, user-workflow scope and acceptance criteria; paid engineering and interface elaboration need not be completed in this quarter. Other agreements are completed before their respective activities, not all at M3, while legal archive access and field-intervention permissions cannot be deferred past use. Host support is a proposed dependency, not unbudgeted free staff.

Explain WP3's 6.0 fellow PM as scientific specification, data/provenance contracts, reference-versus-web inference tests, invalid-input/uncertainty checks and acceptance testing, distinct from Krumatic's paid implementation. WP4 includes six operational assessment dimensions; 38% on WP3+WP4 is not 38% writing interface code. This explains the existing allocation; it does not prove it adequate.

Protect the M20–M21 window by implementing and testing analysis/report code on historical or synthetic data beforehand; run versioned QC during both seasons without changing the model. Final outcome-dependent analysis begins only after the prospective lock. Do not claim rolling QC is early unblinded model optimisation.

**Alternative.** A scientific decision to rebalance WP1/WP3 effort could help, but would change the accepted PM model and all dependent tables; it is not the preferred editorial fix. No extra fellow time is created by moving a task label.

**Fallback.** If the planned pipeline cannot freeze by M3, use only the simpler historically specified and reproducibly validated branch if it is genuinely ready. Otherwise do not claim an unchanged primary test beginning M4. Any shifted start must be checked against the permitted window and the entire crop schedule; do not add “February–March” as a supposedly equivalent calendar.

### B17. Add the missing failure triggers without inventing ready-made substitutes

**Covers:** R2-F-21; E1/E2 risk notes; R2-A-12; R2-OD-07. **Anchor:** p.9 risk table. **Status:** answerable risk design; substitute capacity remains unavailable.

**Preferred answer.** Expand existing R1–R6 in place. Preserve scientific integrity and named accountabilities, remove repetition, and include these trigger-to-response links:

| Existing row | Add or clarify trigger | Response and limitation |
|---|---|---|
| R1 | Archive inadequate; M3 pipeline/approval delay threatens M4 | B01/B16 gate; simpler ready locked branch or no launch of claimed primary test, never fitting to future outcomes |
| R2 | Field not ready; rotation unsuited; mid-season producer withdrawal | B15 terms and agronomic review; only genuinely available qualified backup; preserve accessible data; separate any changed site/season and narrow claims |
| R3 | Clouds/failed instruments; weak stress contrast in wet weather; heat/pest confounding; excessive indeterminate labels | Log availability and confounders; maintain safe agronomy; report prevalence, indeterminate fraction and information loss; no forced drought or retrospectively relaxed labels |
| R4 | Low or imprecise transfer performance | Unchanged primary results first; B04/B05 decision rules; research-only scope. A wide interval is not evidence of successful transfer |
| R5 | Supervisor/fellow absence; essential operator/instrument access interrupted | Host-designated competent review/measurement cover before affected work; if none exists, suspend that task and assess seasonal loss; no fictitious deputy or facility |
| R6 | Engineering affordability/IP/provider failure; placement interruption; analysis backlog at M20 | Accepted scope/rights before paid work; pretested reporting pipeline; cut non-essential UI first; replacements only after actual qualification/access; any placement change handled through the applicable approval route |

Do not change likelihood ratings cosmetically to make 30% attrition seem likely. Wet weather can remove stress cases even when records are plentiful; report absent contrast/non-estimability rather than simply “reduced power under K6”. Heat, pests and irrigation effects must not be labelled water stress merely because a model flags them.

**Alternative.** One compact risk subclause can combine environmental loss and reference confounding; retain distinct responses for data absence and biological non-specificity.

**Fallback.** No substitute is named without evidence. Conclude that the affected objective or placement cannot proceed as designed, and specify the remaining valid reporting output. A web demonstration does not replace the non-academic placement's purpose.

### B18. Make the Gantt readable and the field gate explicit

**Covers:** R2-F-22, R2-F-26; R2-A-02/13. **Anchor:** p.9 Gantt and MS1. **Status:** actionable presentation/design clarification.

**Preferred answer.** Retain the existing five WPs, six milestone IDs, deliverable months, secondment blocks and placement. Add “field readiness” to MS1 and use legible short milestone labels or a directly adjacent key: freeze/readiness, season-1 review, evidence/MVP scope, release, placement review, final roadmap. Clarify abbreviated deliverable families in a compact legend tied to §3.1; do not invent new deliverables or renumber the now-correct D1.1–D1.4.

Re-render labels and axis text at an effective **at least 8 pt at final placement**, preferably with a small safety margin, and verify at print size. Preserve the same frame only if all labels remain readable; higher image resolution alone does not enlarge text. Prefer vector output where supported or a high-resolution raster with calibrated placement. Effective font size is determined by source typography and scaling; glyph-ink height is not the same as nominal point size. The ESR's raster-size estimates justify repair, not a new “9-point ascender height” rule.

**Alternative.** Add a concise field-season/critical-task overlay if it improves sequence comprehension at compliant size. The template requires the core work-plan elements, not automatically a row for every task. Do not crowd the figure merely to satisfy an evaluator's preference for task bars.

**Fallback.** Retain WP-level bars with clear full keys and MS1 readiness wording; disclose residual granularity rather than shrinking labels. If the frame must grow, charge the resulting space to region B. Gantt completion on p.9 is the user's layout target and remains the preferred constraint.

### B19. Describe required capacity and resource decisions, not invented provision

**Covers:** R2-F-24; R2-A-26/31; R2-OD-06/07. **Anchor:** p.10 §3.2 capacity rows; p.8 WP4. **Status:** owner-evidence-limited.

**Preferred answer.** Keep the concrete ATK onboarding/storage/support plan already credited. Add only critical missing accountabilities:

- **Field programme:** B06's measured throughput and instruments must be secured before launch; name a *role* responsible for organising them, not invented people or loans.
- **ELTE:** agree instrument/operator access and field-travel arrangements before each relevant block; no assumption of equipment availability or automatic remote access.
- **Krumatic:** state the already specified deliverable-based engineering scope, reproducible acceptance tests, source delivery and rights; ATK checks capability and affordability before paid work. This is not proof of a quotation, staffing level or current track record.
- **AgroVIR:** require an operational supervisor/contact role to be nominated and the supervision/evaluation plan agreed before placement; do not insert a name from memory or Part B2 without evidence in the authorised source set.
- **Resource approval:** host confirms which permitted resources cover the critical reference, monitoring, field operation and engineering before commitment. Preserve the priority order; do not assume the full research/training contribution is freely available for software or promise unverified co-funding.

**Alternative.** A lean, scientifically valid MVP may defer dashboards and production integration while retaining reproducible inference, provenance, uncertainty and invalid-input handling. It does not eliminate essential field costs or the need for a provider if the fellow lacks implementation capacity.

**Fallback.** If essential resource provision is unavailable, stop or narrow the corresponding activity through the stated gate; do not substitute generic partner reputation for capacity. Post-submission arrangements are acceptable to describe prospectively when permitted, but unsupported feasibility remains a scoring limitation.

### B20. Restore compliant typography without a broad margin rewrite

**Covers:** R2-F-25, R2-F-27; FC-06/FC-04b; R2-A-01/03. **Anchors:** substantive tables pp.5–7,9–10. **Status:** mandatory formatting repair; no scoring points claimed.

**Preferred answer.** Set all substantive table text to at least 11 pt, including overridden runs and table styles; retain standard character spacing and single-or-greater line spacing. Check captions/footnotes and other non-body text against their applicable ≥8 pt rule. Correct table widths/indents so the outer border, including stroke width, lies inside the 15 mm margins. Do not widen already compliant body margins merely because trailing spaces enlarge extracted span boxes.

The ESR reports about 29.5 equivalent lines of growth at 11 pt; treat this as a planning estimate, not a measured final layout. Font enlargement, changed table width, header repetition and row wrapping interact. Even border repairs may alter wrapping if the usable cell width changes; do not guarantee zero space cost.

**Alternative.** Compact or reorganise a table's duplicated content at 11 pt, with headings and evidence preserved. This changes presentation, not the underlying claims. The official full headings and tags take precedence over shorthand section titles in an earlier prompt.

**Fallback.** If all required content does not fit, use verified current cuts and targeted compression, then re-export. There is no compliant fallback involving 10 pt narrative tables, reduced margins, squashed text, hidden content or moving assessed B1 material into B2. If it still cannot fit, report the conflict rather than certify submission readiness.

**Check:** exact ten-page user target; A4; embedded fonts; unencrypted; correct headers/footers; no markup/placeholders; all pages inspected after final export. This brief performs none of those checks on a future revised file.

## 3. Owner facts still unavailable and the safe response to use

The missing facts below are **not** questions blocking preparation of this brief. They identify the limits of what the subsequent rewrite can truthfully say. “Before activity” is a proposed operational dependency; it is not a claim that the application requires a letter at submission.

| ESR owner ID | Unavailable fact | Safe response and relevant answer | Earliest relevant gate | Residual scoring limitation |
|---|---|---|---|---|
| R2-OD-01 | MATE counts, controls, variables, dates, spectral range, 2026 completeness and rights | B01/B02: conditional adequacy inventory and lawful common subset; no claimed instrument or dataset size | Access before analysis; M1 adequacy; M3 freeze | F-01/F-23 cannot be fully closed |
| R2-OD-02 | Field identity, polygons, irrigation, crop history, two-season availability, acceptable terms, backup | B03/B15: explicit readiness requirements and no claimed secured site/payment | MS1 before irreversible intervention | F-18 remains major without feasible-site evidence |
| R2-OD-03 | Personal supervision totals/outcomes, current collaborations, allocated time, deputy | B07: existing documented examples plus proposed routine and independent escalation | Before reliance on claimed capacity; competent cover before affected gate | F-06 remains partly answered |
| R2-OD-04 | Crop-specific reachable farms/hectares, qualifying denominator, recruitment success | B12/B13: direct evidence/engagement envelope; eligibility definition early; wider uptake unknown | Definition M12; accessible screening/assessment later | F-13 not cured by fabricated market numbers |
| R2-OD-05 | DrR demonstrated functions/version, individual manuscript contributions, certificates, changed publication status | B09: prototype and current documented competence-to-task links; retain “under review” | Before any stronger B1 claim | F-08 remains evidence-limited |
| R2-OD-06 | ELTE operators/instruments/time/travel arrangements per block | B08/B19: assigned block purposes and access-before-use plan | Before M1/M10/M16 access and field campaigns | Rationale can improve; capacity not proven |
| R2-OD-07 | Actual field staffing, instrumentation funding, engineering quotation/capacity, AgroVIR supervisor | B06/B19: explicit required roles and approval/acceptance gates | Before field launch, paid engineering and placement respectively | F-24 and resource risks remain |
| R2-OD-08 | Protocol decisions mixed with genuine evidence needs | B03/B04/B10/B11/B13 supply proposed matching, precision, literature, career and early-feedback responses now; actual power still needs data | D1.2 before fitting; later action milestones | Do not misclassify every new protocol choice as an unavailable owner fact |
| R2-OD-09 | Work-programme provenance check | Official Commission PDF is accessible and retains the DRAFT watermark; repository and previously downloaded official copy are byte-identical (Section 7) | Report provenance, not B1 content | No extra proposal paragraph or owner confirmation needed |

No Part A/B2 correction, ethics checkbox, CV date repair or portal registration action is included. No letter is added merely because the ESR mentions an agreement: the EF secondment/placement letter question was rejected as a weakness in round two. Genuine access, field-operation, service and placement arrangements may be concluded after submission when permitted, but **before their corresponding use/activity**. Do not describe them as already signed.

### 3.1 Decision substitutions to record in the next revision report

The earlier “all preferred answers accepted” instruction does not pre-approve newly invented facts or every new number in this brief. Record these new design choices if adopted:

- B02: distinguish reconstructability from transfer; move the 10% classification-change screen to a non-selective sensitivity diagnostic, or omit it as justified.
- B03: adopt the proposed same-day/±2-hour primary pairing rule and explicit grid eligibility; broader windows only as labelled sensitivity analyses.
- B04: select the separate agronomic, ablation and prevalence references and the proposed precision criterion.
- B05: use a genuinely compatible regression branch or a justified single-marker binary alternative; no classification claims without labels.
- B06: resource the stated planned campaign roles and dry-run requirement; do not claim allocation.
- B11/B13: adopt portfolio/positioning outputs and early feedback within existing effort, with fallback and no recruitment promise.
- B15: any change from one field over two seasons, any promised compensation or PM/schedule change requires a substantive decision and evidence; none is silently adopted here.

## 4. Complete ESR-to-answer coverage

### 4.1 Consensus findings, including formal defects

| Finding | Main answer(s) | Expected disposition from the recommended response |
|---|---|---|
| R2-F-01 | B01/B02 | Adequacy logic clarified; archive facts still missing |
| R2-F-02 | B02/B04 | Screen made interpretable; no invented calibration/transfer evidence |
| R2-F-03 | B03/B06 | Grid and matching protocol specified; attainability checked at readiness |
| R2-F-04 | B04 | Comparators/precision/lead-time decision defined; achieved power not established |
| R2-F-05 | B05 | Branch consequences propagated; no automatic classification fallback |
| R2-F-06 | B07 | Governance clarified; record still evidence-limited |
| R2-F-07 | B08/B06 | Location clash and rationale addressed; access remains conditional |
| R2-F-08 | B09/B16 | Existing fit better linked; no fabricated ML/software record |
| R2-F-09 | B10 | Satellite comparator supplied and universal negative removed |
| R2-F-10 | B06 | Time/order/reference protection specified; staffing not secured |
| R2-F-11 | B09 | Distinctive assets linked to planned host benefits |
| R2-F-12 | B11 | Learning outcomes and delivery clarified, not merely renamed |
| R2-F-13 | B12 | Direct magnitude and decision value quantified; wider impact conditional |
| R2-F-14 | B13 | Project-controlled channel and two-way feedback specified |
| R2-F-15 | B14/B05 | Owners/gates and outcome-dependent exploitation clarified |
| R2-F-16 | B11 | Concrete positioning activity without job/funding promise |
| R2-F-17 | B13 | Earlier feedback planned; failed recruitment reported honestly |
| R2-F-18 | B15/B03/B16 | Requirements and risk terms strengthened; actual field remains missing |
| R2-F-19 | B16/B01 | Critical path bounded; first-quarter feasibility still evidence-dependent |
| R2-F-20 | B16 | Scientific WP3/WP4 effort explained without PM inflation |
| R2-F-21 | B17/B04 | Missing risks and analysis compression addressed |
| R2-F-22 | B18/B15 | MS1 readiness and Gantt keys clarified; no new milestone IDs |
| R2-F-23 | B01/B19 | Replace open-ended redesign with explicit adequacy/no-go branches |
| R2-F-24 | B06/B19/B08 | Capacity requirements identified; unavailable provision remains flagged |
| R2-F-25 | B20 | Table-size repair required and separately verified downstream |
| R2-F-26 | B18 | Final-size figure text repair required |
| R2-F-27 | B20 | Table-border repair; body margins are not re-labelled a failure |

“Addressed” is not the same as “resolved by an evaluator”. These dispositions are revision intentions, not a new score.

### 4.2 ESR action and Annex A coverage

All 32 ESR actions are covered: A-01/03 → B20; A-02/13 → B18; A-04/16/32 → B08; A-05 → B02; A-06 → B05; A-07 → B03; A-08/30 → B04; A-09 → B15; A-10/19 → B16; A-11/22 → B01; A-12 → B17; A-14/28 → B13; A-15 → B14; A-17/25 → B09; A-18 → B06; A-20/29 → B11; A-21 → the zero-cost polish note below; A-23 → B07; A-24 → B12; A-26/31 → B19. These are `R2-A-` IDs; none refers to round-one actions.

Annex A's retained concerns map through its A.4 disposition table to all 24 scored findings above. Additional sub-points receive explicit treatment:

- E1: rotation/same-field suitability → B15; campaign duration, operator/sensor density, genotype, stage, indeterminate labels → B06/B17; optical warning versus actual onset → B04; early workload → B16.
- E2: canopy-cover versus treatment purity and shared spatial support → B02/B03; processing-baseline versioning → B02; inner-out-of-fold threshold choice and spectral increment → B04; M20/M21 compression → B16/B17; source/placement alternatives → B19/B17.
- E3: conflict escalation, competent alternate and post-M3 cadence → B07; past traineeship versus secondment added value → B08; publication status/qualitative evidence → B09; one-way engagement and positioning → B13/B11.
- E3-W13 (publication volume/timing) was rejected at consensus. Preserve the proportionate existing publication floor and schedule; do not spend page space manufacturing an extra paper commitment.
- The old 2026-season completeness note → B01, as a provenance check, not an invented new deduction.
- Paid engineering, same-country secondment, the permitted twelve-month duration, single-crop scope, justified gender treatment, the career break and absence of EF commitment letters are **not reopened as defects**.

**Zero-cost polish:** delete “irrespective of gender” from the p.10 farmer role only if already editing that row, as R2-A-21 suggests. Do not touch the accepted research gender-dimension justification. No score gain is attributed to this deletion.

## 5. Revision sequence, do-not-touch list and current cut pool

### 5.1 Recommended sequence

1. Preserve the identified PDF and exact editable counterpart. The current refactored PDF is the baseline; do not reconstruct or edit the old sealed proposal again.
2. Establish protected passages and a **compliant** regional space budget: 11 pt table narrative, ≥8 pt figure text, borders within margins. Record all run/style overrides and actual Gantt scaling.
3. Apply genuine duplicate cuts and local replacements, prioritising B02–B05 coherence and B08's location correction alongside formal repair. Do not leave scientifically inconsistent fallbacks because compliance alone fits.
4. Integrate B01/B06/B15–B17's scoring-critical gate/logistics clauses; keep owner-fact limits explicit. The ESR's minimum set does not close the major archive, field, precision and workload weaknesses.
5. Use verified savings for B07/B09–B14's compact evidence and impact improvements. Avoid re-expanding already credited open-science, governance and placement prose.
6. Propagate every chosen branch into objectives, tasks, deliverables, KPIs, risk rows, impact result families and Gantt; re-export, inspect all pages and iterate.

If only one short scoring-focused pass is feasible, prefer a coherent, accurate reduced package over a list of unimplemented promises. Do not declare the file ready if tables/figure text still fail or if a central scientific contradiction remains.

### 5.2 Binding protections

Preserve verbatim except for an explicitly authorised cut or strictly necessary consistency correction:

- p.2 §1.1 four assumptions and three advances; pp.1–2 measurable/falsifiable freeze logic.
- p.3 primary-before-recalibration statements, the independent physiological-reference principle, methodological challenge controls and gender justification.
- p.4 structured supervision/governance and substantive two-way transfer; new clarity is appended or locally integrated without deleting the strengths.
- p.5 placement rationale, timing and integral career/project value.
- pp.6–7 layered DrR background/result/data/contractor rights, dated background distinction, exploitation governance and no numerical water-saving claim.
- pp.8–9 five WPs, current deliverable numbering and months, effort totals, scientific gates and poor-transfer integrity rule.
- p.10 dependency-before-use statement, resource priorities, non-essential proprietary customer data and MVCRI's non-core conditional role.

Keep the accepted WP totals **5.0/9.0/6.0/5.4/4.6 = 30.0 PM**, 24 fellowship PM plus six placement PM; WP1 2.2 pre-freeze plus 2.8 later; ELTE blocks 1–3/10–12/16–21; placement 25–30; D5.1 M3; quarterly CDP reviews. Do not renumber D1 again. Milestone months remain 3/12/21/24/27/30; add readiness to MS1, not a seventh milestone by default.

Changes needed by B05 are narrowly defined consistency exceptions, not permission for general rewriting. Record each exception and its consequence. If an earlier protected phrase promises unconditional success, preserve the underlying evidence gate and correct the unconditional promise rather than retain a contradiction.

### 5.3 Corrected current cut pool

Round-one cuts are already consumed. The following are **candidates**, verified against current text; they are not applied cuts. Approximate line credits from the ESR are planning ceilings, not measurements after reflow. A row is spent only when its exact deleted/replaced span and actual rendered saving are recorded.

| Brief cut ID | Current anchor and exact scope | Relation to ESR cut | Conservative planning credit | Allocation/guardrail |
|---|---|---|---:|---|
| C2-01 | p.5 §2.1 training table, mechanism cell beginning “ATK: plant-stress interpretation…” | R2-CUT-01 | ≤3 lines, A | Formal repair; compact pointer to §1.3 but retain ATK/ELTE competence distinction and evidence cell |
| C2-02 | p.7 §2.3 Scientific row, contribution cell beginning “Leakage-safe modelling links…” | R2-CUT-02 | ≤2 lines, A | Formal repair; retain one evaluator-readable account of scientific contribution and the magnitude cell |
| C2-03 | p.10 ATK row, only the Janda/Hollós role sentence | R2-CUT-03 | ≤1.5 lines, C | Formal repair; roles stay in §1.3; do not remove unique hosting/induction provision |
| C2-04 | p.10 ELTE row, per-block task list only | R2-CUT-04 | ≤1 line, C | Conditional: only after B08 preserves block purposes in §1.3; keep instrument/operator access and supplementary UAV limits |
| C2-05 | p.6 §2.1 sentence beginning “By completion, the fellow will have taken…” | R2-CUT-05 | ≤2 lines, A | B05 consistency; compact the repeated development chain, preserving biological-to-industrial span |
| C2-06 | p.3 Integration paragraph's final sentence, “The fellow integrates these disciplines…” | R2-CUT-06 | ≤1 line, A | B02 clarification; retain reference → interpretation, protocol → development, predictor specification → input constraints |
| C2-07 | p.7 “Reach and uptake”, repeated counts for demos/workshop/explainers/tutorial/summaries only | R2-CUT-07 | ≤1.5 lines, A | Formal repair; retain 6–10/2–3 targets, task/interpretation/usability measures, evidence sources and attendance≠adoption |
| C2-08 | p.5 entire “The fellowship addresses the next step…” sentence, including “deepened through…” | **Merge R2-CUT-08 and R2-CUT-12** | ≤1.5 lines total, A | Formal repair; one replacement and one credit. Preserve development needs in §2.1; never allocate the embedded clause separately |
| C2-09 | p.8 opening ELTE-months sentence | R2-CUT-09 | ≤1 line, B | Formal repair; retain once nearby the distinction between work location and PM, and retain block months in §1.3/Gantt/K11 |
| C2-10 | p.8 WP5 lead line merged into T5.1, not deletion of lead | R2-CUT-10 | ≤0.5 line, B | Formal repair; check task readability and ownership |
| C2-11 | p.9 R4/R6 repeated response prose | R2-CUT-13 | **0 until verified** | Compression only; B17 adds distinct risks here. Never delete secondary-recalibration separation, qualified replacement or placement-change conditions merely because integrity is stated above |

**Not a cut:** R2-CUT-11/p.7 impact-bounding sentence remains protected. Do not interpret the ESR JSON's “apply all cuts … except none withheld” as authority to delete it.

For C2-08, a rewrite retaining the same scientific-development needs can save space, but the original sentence already contains C2-12's proposed deletion. The ESR's separate 1.5 + 1.5 line credits therefore cannot be assumed additive. This brief conservatively reserves 1.5 total until the editor measures the combined replacement.

### 5.4 Budget after removing unsafe credits

The ESR estimates 21.1 lines of total slack, but it is region-bound. Do not spend page-10 slack on a page-9 Gantt that must not move. Starting from the ESR's own estimated growth and minimum additions:

| Region | ESR estimated required space | ESR slack | Corrected provisional cut credits | Provisional margin, **before new brief additions** |
|---|---:|---:|---:|---:|
| A: pp.1–7 | 21.4 lines | 11.4 | 11.0 (C2-01/02/05/06/07/08) | +1.0 line |
| B: pp.8–9 | 4.7 lines | 3.3 | 1.5 (C2-09/10; no automatic C2-11 credit) | +0.1 line |
| C: p.10 | 8.5 lines | 6.4 | 2.5 (C2-03/04, latter conditional) | +0.4 line |

These figures **do not establish fit**. They reuse the ESR's 10→11 pt growth estimate; the revised answer clauses, footnotes, table-border changes and Gantt keys still need to be costed. In particular, the original two-line allowance for a screen correction may not accommodate a defensible B02 answer. Label honest partial coverage rather than silently omit its causal distinction.

Additional savings must be measured from **non-overlapping** in-place compression, not assumed:

- Shorten objective/task repetitions without removing each section's objective, method or delivery function. Exclude protected measurability and ambition paragraphs.
- Standardise short names of the registered protocol, model card and evidence package across §1.2/§2.2; keep timing, licence, rights limitations and negative-results release once clearly stated.
- Remove repeated career-target phrases outside C2-05/C2-08 only after defining disjoint spans; keep the explicit target role and trajectories.
- Integrate risk additions as replacements within R1–R6 rather than appending a second risk register. Distinct triggers and qualified fallbacks are not disposable duplication.

Do not claim that a cell fits “one line” by character count alone. Count **gross additions, gross deletions and net reflow** separately at compliant typography. A single cut cannot fund both formal repair and a scientific addition. C2-05 and C2-06 have dedicated consumers; all other measured formal credits are unavailable for reuse.

## 6. Handoff and validation for the later editor

The later implementation should create new versioned outputs, for example `FIELDWISE_Part_B1_round2_revised_2026-09-09.docx/.pdf` and a corresponding revision report; preserve the 8 September refactored source. This brief itself creates none of those files.

The revision matrix must record each R2-F ID, selected B-answer, actual paragraph/table/Gantt edit, retained owner limitation, cut ID and consistency dependencies. Include all new numerical choices and every departure from a formerly accepted preferred answer. No placeholders, “preferred answer” language, ESR references or alternative drafting options belong in B1.

Validation must establish:

1. **Scientific coherence:** same outcome, predictor eligibility, comparator/reference and performance rules throughout; regression branch genuinely regression-based; no Brier-to-self comparison or classification without labels.
2. **No leakage:** reference/rules registered before fitting; training-dependent operations within folds; M3 freeze; prospective measurements diagnostic/test-only; unchanged results first.
3. **Design denominators:** independent areas versus plants/pixels/dates; actual usable pixels, pairing windows, missingness, class availability, indeterminate fraction and uncertainty limits.
4. **Feasibility honesty:** no fabricated archive, field, compensation, staff, instrument, supervisor, software or market evidence; essential activity gates occur before use. No approved rephase or guaranteed replacement is invented.
5. **Cross-references:** five WP totals 30 PM, 24+6 split, twelve ELTE months, M25–M30 placement, M3 freeze/D5.1, D1.1–D1.4 and other deliverable months, K5/K6/MS3 fallback consequences, CDP cadence, Gantt keys.
6. **Protected content and cuts:** whitespace-normalised preservation or documented narrow exceptions; no reused old cut; C2-08 merged; unoffered impact-bounding cut untouched; actual rather than estimated savings.
7. **Formal readiness:** exactly ten A4 pages; body and table narrative ≥11 pt; other text including figure labels ≥8 pt at final placement; standard spacing; borders and content within margins; embedded fonts; correct official headings/header/footer; no markup, placeholder, clipping or unreadable row splits.
8. **Visual QA:** inspect all ten pages after the final export. Preserve Section 3 starting p.8, Gantt ending p.9 and §3.2 p.10 where required by the user's layout constraints. If a conflict remains, report it; do not silently declare compliance.

Report residual findings even after an edit has been made. The archive, field, supervision record and capacity limitations can persist after safe wording is correctly applied. No predicted score or funding outcome is attached to this brief.

## 7. Sources, verification and limitations

- **Attached round-two ESR Markdown and JSON:** authoritative sources for this task's 27 findings, 32 actions, nine owner decisions, consensus/individual concerns, technical-check corrections and cut inventory. The Markdown's Annex B duplicates the JSON packet; the standalone JSON is used for structured coverage. References such as “ESR II.5” refer to these attachments, not a newly run evaluation.
- **Current refactored PDF:** hash verified against the ESR; text of all ten pages read. Pages 5, 9 and 10 visually inspected for current table, cut-span, Gantt and capacity context. This brief relies on the ESR's full ten-page technical audit for reported font/border measurements; it does not claim a fresh full forensic compliance audit or a re-export.
- **Prior improvement brief:** `FIELDWISE_Part_B1_Scoring_Improvement_Brief_2026-09-08.md`, especially the accepted scientific package, safe responses, source boundaries and consumed cut pool. The user's latest edited refactoring prompt is the constraint reference, with the table-text rule corrected to the actual template as explicitly required by round two.
- **Actual Part B template V5.0:** `docs/tier2a_instrument_schemas/application_forms/msca/Tpl_Application Form (Part B) (HE MSCA PF).rtf`. It explicitly applies the 11-point body-text minimum to text in tables. The [official application-form source](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/temp-form/af/af_he-msca-pf_en.pdf) is the reference for current form guidance, not the shorthand wording in an earlier prompt.
- **Official work-programme provenance:** the [Commission's 2026–2027 MSCA PDF](https://ec.europa.eu/info/funding-tenders/opportunities/docs/2021-2027/horizon/wp-call/2026-2027/wp-2-marie-sklodowska-curie-actions_horizon-2026-2027_en.pdf) was accessible on 9 September and itself displays the DRAFT watermark and Commission Decision C(2025) 8493 of 11 December 2025. The repository copy and previously downloaded official copy have the same SHA-256, `8577ee9cd0bc506b28dbcb9b86bb2016745b75fbd6fb8a254b76597cbd3ef24b`. The watermark alone is therefore not evidence that the repository holds a different, unofficial version. No scoring points or B1 space are allocated to this provenance matter.
- **Technical sources:** Copernicus mission/SRF documentation and the directly relevant Dalla Marta research paper are linked at B02/B10. The paper text was available through its indexed author-shared copy; publisher direct retrieval was rate-limited. No claim of exhaustive literature review or external validation of FIELDWISE is made. The Vanino item is an optional title-level comparator, not a fully reviewed methods source here.

**Boundary:** proposed thresholds, matching windows, staffing requirements, model branches and milestones in this brief are reasoned project-design options. They are not verified owner facts, achieved experimental precision, accepted contractual terms or universal scientific standards. The document supports scoring improvement and a controlled rewrite; it does not secure resources, run an experiment, refactor the proposal, certify submission readiness or guarantee a Seal/funding result.
