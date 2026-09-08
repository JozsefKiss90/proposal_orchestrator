# FIELDWISE Part B-1 refactoring report

**Date:** 2026-09-08  
**Plan:** `plans/FIELDWISE_Part_B1_Scoring_Improvement_Plan_2026-09-08`  
**Build tool:** `tools/build_partb1_refactored.py` (edits, cut ledger, checks and this report come from one data set)  
**Scope:** Part B-1 Sections 1–3 only. No source file was modified.

## 1. Sources used

- CLAUDE.md
- plans/reports/FIELDWISE_Part_B1_Scoring_Improvement_Brief_2026-09-08.md
- plans/reports/FIELDWISE_ESR_2026-09-08.md
- plans/reports/FIELDWISE_ESR_2026-09-08.json
- docs/tier5_deliverables/submitted/FIELDWISE_101373105_submitted_2026-09-07.pdf (sealed baseline)
- docs/tier5_deliverables/submitted/FIELDWISE_Part_B1_10_pages.docx (editable baseline)
- docs/tier2a_instrument_schemas/application_forms/msca/Tpl_Application Form (Part B) (HE MSCA PF).rtf
- docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_en.pdf
- docs/tier2b_topic_and_call_sources/work_programmes/msca/wp-2-marie-sklodowska-curie-actions_horizon-2026-2027_en.pdf (expected outcomes, pp. 25–28)
- docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_manual-condensed_2026-09-06.docx (checked, superseded by the submitted DOCX)
- docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_gantt_2026-09-06.png (checked, superseded by the embedded Gantt of the submitted DOCX)
- EEA indicator 'Water scarcity conditions in Europe' (28 November 2025) for footnote 1; the Alordzinu (2021), Martelli (2025) and FAO-56 references supplied by the brief, authorship confirmed against the publishers' records

## 2. Editable baseline versus the sealed PDF

The plan expected `FIELDWISE_Part_B1_manual-condensed_2026-09-06.docx` to be the editable source. It is not: it lacks the official header and footer, has a different reference apparatus and a different Section 3. The DOCX stored beside the sealed PDF, `docs/tier5_deliverables/submitted/FIELDWISE_Part_B1_10_pages.docx`, carries the official header and footer, the same six footnotes and the same embedded Gantt image.

Word-sequence match of that DOCX against sealed PDF pp. 24–33: **0.9775** (6149 DOCX words, 6168 PDF words). Every residual difference is a PDF extraction artefact: inline superscript footnote numbers, hyphenation of 'UAV' and 'validation', the repeated table header on Part B page 6, and footnote text position. Exporting that DOCX through Word reproduces the sealed pagination exactly (10 pages, identical page starts). It is therefore the baseline.

## 3. Accepted-answer coverage matrix

| Answer | Edits | Target passages | Status |
|---|---|---|---|
| R01 | E03, E07, E08, E11 | §1.1 ¶The four objectives (O1–O4); §1.2 ¶Integration of methods; §1.2 ¶Stage 1 (WP1); §1.2 ¶Stage 2 (WP2) s2 | implemented at scoring-critical core |
| R02 | E06, E08, E10, E43 | §1.2 ¶Methodological challenges; §1.2 ¶Overall methodology; §1.2 ¶Stage 2 (WP2) s2; §3.2 table, Commercial farmer row | implemented at scoring-critical core |
| R03 | E03, E07 | §1.1 ¶The four objectives (O1–O4); §1.2 ¶Stage 1 (WP1) | implemented at scoring-critical core |
| R04 | E01, E02 | §1.1 ¶Pertinence; §1.1 ¶Problem and overarching aim | implemented at scoring-critical core |
| R05 | E11, E13 | §1.2 ¶Integration of methods; §1.3 ¶Supervisory architecture | implemented at scoring-critical core |
| R06 | E14, E15, E20, E40 | §1.3 ¶Planned training activities and ELTE secondment; §1.3 ¶Two-way transfer; §2.1 table, ATK training and ELTE secondment rows; §3.2 table, ELTE row | implemented at scoring-critical core |
| R07 | E05, E17 | §1.1 ¶Realistically achievable; §1.4 ¶A profile matched | implemented at scoring-critical core |
| R08 | E09, E09a, E16, E23, E27, E28a, E28, E29, E30, E44 | §1.1 ¶Problem (scope sentence); §1.2 ¶Stage 3 (WP3–WP4); §1.3 ¶Rationale and added value; §2.1 ¶By completion; §2.2 ¶Reach and uptake; §2.3 intro; §2.3 table, Agricultural & environmental row; §2.3 table, European & societal row; §2.3 ¶Impact is measured; §3.2 table, MVCRI row | implemented at scoring-critical core |
| R09 | E18, E24, E26, E27 | §2.1 ¶FIELDWISE is designed; §2.2 table, Communication row; §2.2 ¶FIELDWISE uses a targeted strategy; §2.2 ¶Reach and uptake | implemented at scoring-critical core |
| R10 | E14, E15, E19, E21, E22, E34 | §1.3 ¶Planned training activities and ELTE secondment; §1.3 ¶Two-way transfer; §2.1 table, Career Development Plan row; §2.1 table, Scientific visibility row; §2.1 table, Transferable-skills row; §3.1 WP5 task line | implemented at scoring-critical core |
| R11 | E12, E25 | §1.2 ¶Open science practices; §2.2 table, Dissemination row | implemented at scoring-critical core |
| R12 | E37, E38, E40, E41, E42, E43, E44 | §3.1 risk table; §3.2 intro; §3.2 table, Commercial farmer row; §3.2 table, ELTE row; §3.2 table, Krumatic row; §3.2 table, MATE row; §3.2 table, MVCRI row | implemented at scoring-critical core |
| R13 | E05, E33, E34, E36 | §1.1 ¶Realistically achievable; §3.1 WP2 deliverable line (K5); §3.1 WP5 task line; §3.1 ¶Critical path | implemented at scoring-critical core |
| R14 | E39 | §3.2 table, HUN-REN ATK row | implemented at scoring-critical core |
| R15 | E38, E42 | §3.2 intro; §3.2 table, Krumatic row | implemented at scoring-critical core |
| R16 | E03, E20, E25, E32 | §1.1 ¶The four objectives (O1–O4); §2.1 table, ATK training and ELTE secondment rows; §2.2 table, Dissemination row; §3.1 WP1 deliverable line | implemented at scoring-critical core |
| R17 | E31, E35, E37 | §3.1 WP5 deliverable line; §3.1 risk table; §3.1 ¶The fellow leads | implemented at scoring-critical core |

## 4. Finding-to-edit matrix (F-01–F-23)

| Finding | Edits | Target passages | Status |
|---|---|---|---|
| F-01 | E03, E07 | §1.1 ¶The four objectives (O1–O4); §1.2 ¶Stage 1 (WP1) | addressed |
| F-02 | E06, E08, E10, E43 | §1.2 ¶Methodological challenges; §1.2 ¶Overall methodology; §1.2 ¶Stage 2 (WP2) s2; §3.2 table, Commercial farmer row | addressed |
| F-03 | E03, E07, E08 | §1.1 ¶The four objectives (O1–O4); §1.2 ¶Stage 1 (WP1); §1.2 ¶Stage 2 (WP2) s2 | addressed |
| F-04 | E12 | §1.2 ¶Open science practices | addressed |
| F-05 | E01, E02 | §1.1 ¶Pertinence; §1.1 ¶Problem and overarching aim | addressed |
| F-06 | E11, E13 | §1.2 ¶Integration of methods; §1.3 ¶Supervisory architecture | addressed |
| F-07 | E14 | §1.3 ¶Planned training activities and ELTE secondment | addressed |
| F-08 | E17 | §1.4 ¶A profile matched | addressed |
| F-09 | — | — | excluded: Part B-2 CV-format issue; out of scope for B-1 |
| F-10 | E17 | §1.4 ¶A profile matched | addressed |
| F-11 | E09, E09a, E16, E23, E27, E28a, E28, E29, E30 | §1.1 ¶Problem (scope sentence); §1.2 ¶Stage 3 (WP3–WP4); §1.3 ¶Rationale and added value; §2.1 ¶By completion; §2.2 ¶Reach and uptake; §2.3 intro; §2.3 table, Agricultural & environmental row; §2.3 table, European & societal row; §2.3 ¶Impact is measured | addressed |
| F-12 | E18, E24, E26, E27 | §2.1 ¶FIELDWISE is designed; §2.2 table, Communication row; §2.2 ¶FIELDWISE uses a targeted strategy; §2.2 ¶Reach and uptake | addressed |
| F-13 | E14, E15, E21, E22 | §1.3 ¶Planned training activities and ELTE secondment; §1.3 ¶Two-way transfer; §2.1 table, Scientific visibility row; §2.1 table, Transferable-skills row | addressed |
| F-14 | E14, E19, E34 | §1.3 ¶Planned training activities and ELTE secondment; §2.1 table, Career Development Plan row; §3.1 WP5 task line | addressed |
| F-15 | E12, E25 | §1.2 ¶Open science practices; §2.2 table, Dissemination row | addressed |
| F-16 | E37, E38, E40, E41, E42, E43, E44 | §3.1 risk table; §3.2 intro; §3.2 table, Commercial farmer row; §3.2 table, ELTE row; §3.2 table, Krumatic row; §3.2 table, MATE row; §3.2 table, MVCRI row | addressed |
| F-17 | E05, E36 | §1.1 ¶Realistically achievable; §3.1 ¶Critical path | addressed |
| F-18 | E33, E34, E36 | §3.1 WP2 deliverable line (K5); §3.1 WP5 task line; §3.1 ¶Critical path | addressed |
| F-19 | — | — | excluded: Part A participant registration; out of scope for B-1 |
| F-20 | E39 | §3.2 table, HUN-REN ATK row | addressed |
| F-21 | E31, E35, E37 | §3.1 WP5 deliverable line; §3.1 risk table; §3.1 ¶The fellow leads | addressed |
| F-22 | E38, E42 | §3.2 intro; §3.2 table, Krumatic row | addressed |
| F-23 | E03, E20, E25, E32 | §1.1 ¶The four objectives (O1–O4); §2.1 table, ATK training and ELTE secondment rows; §2.2 table, Dissemination row; §3.1 WP1 deliverable line | addressed |

## 5. Edit register

| Edit | Findings | Answers | Target | Change | Cuts | Dependencies |
|---|---|---|---|---|---|---|
| E01 | F-05 | R04 | §1.1 ¶Problem and overarching aim | Generic problem sentence removed (CUT-25, allocated to E08); footnote 1 re-sourced to the EEA indicator. | — | Footnote 1 text replaced in footnotes.xml. |
| E02 | F-05 | R04 | §1.1 ¶Pertinence | Position FIELDWISE against thermal/CWSI, soil-water/ET/AquaCrop scheduling and ML tomato irrigation work with three new footnotes; the FIELDWISE addition stated; career duplicate cut (CUT-1). | CUT-1 | Footnotes 7–9 added; Word renumbers the displayed footnotes in order. |
| E03 | F-01, F-03, F-23 | R01, R03, R16 | §1.1 ¶The four objectives (O1–O4) | O1 states the conditional spectral conversion; O2 names the model and benchmark and the renumbered D1.3; O3 names the replicated design; O2–O4 duplicates merged (IPC-2). | — | D1.4→D1.3 here, §1.2, §2.1, §2.2, §3.1 and Gantt. |
| E04 | — | — | §1.1 ¶Measurability and verifiability | Only the missing space after 'verifiability.' is restored (permitted by the do-not-touch list). | — | — |
| E05 | F-17 | R13, R07 | §1.1 ¶Realistically achievable | Archive familiarity pointer (A-09) added once; CUT-18 and two duplicates removed (IPC-1). | CUT-18 | Training stays are detailed once, in §1.4. |
| E06 | F-02 | R02 | §1.2 ¶Overall methodology | Physiological stress reference defined before fitting (primary axis, corroborating endpoint, fluorescence role, reference limits, indeterminate class, safe response); CUT-22 applied. | CUT-22 | — |
| E07 | F-01, F-03 | R01, R03 | §1.2 ¶Stage 1 (WP1) | Restricted common-predictor chain (M1 audit, band integration with versioned SRFs, band exclusion, separated corrections, Level-2A, 20 m grid, pixel rules, engineering screen, failed-transfer response), named model/benchmark, leave-one-year-out validation, group-aware uncertainty, abstention, freeze rule and project decision criteria. | — | ELTE secondment sentence compressed (IPC-3); D1.3 renumbering. |
| E08 | F-02, F-03 | R02, R01 | §1.2 ¶Stage 2 (WP2) s2 | Prospective design dimensioned (3 regimes × 4 blocks, 12 areas, 80 × 80 m, 20 m buffer, 7.68 ha, 12 campaigns, 5 plants, 288 records, 202 pairs, growth-stage stratification, experimental unit, temporal not environmental replication); paired proximal spectra sentence appended; s1 and s4–s6 verbatim. | CUT-19, CUT-23, CUT-25 | §3.2 farmer row and risk R3 use the same design and field-readiness gate. |
| E09 | F-11 | R08 | §1.2 ¶Stage 3 (WP3–WP4) | Condensed to one sentence (CUT-12) to fund the §2.3 magnitude statement. | CUT-12 | — |
| E09a | F-11 | R08 | §1.1 ¶Problem (scope sentence) | Crop-transfer scope sentence compressed to a pointer; the one-crop/two-season limit stays in 'Realistically achievable' and Stage 2 (IPC-8). | — | — |
| E10 | F-02 | R02 | §1.2 ¶Methodological challenges | Items (i)–(vi) verbatim; the two UAV sentences removed (CUT-19, allocated to E08); UAV's supplementary status stays in risk R4 and the §3.2 ELTE row. | — | — |
| E11 | F-06 | R05, R01 | §1.2 ¶Integration of methods | Discipline list and partner roles merged into accountabilities (Janda: physiology and scientific gates; Jung: sensor harmonisation; Hollós: statistical design, calibration, leakage checks; Takács: agronomic review of the irrigation protocol) (CUT-9, IPC-4). | CUT-9 | — |
| E12 | F-04, F-15 | R11 | §1.2 ¶Open science practices | Compact release plan: timestamped protocol registration, public protocol/metadata deposit, versioned model card, Zenodo or equivalent, BSD-3-Clause research code, metadata/synthetic examples where data are restricted, rights-cleared prospective dataset, preprints, negative results, layer separation, 30-day disclosure review subject to institutional clearance. | — | D1.3 renumbering. |
| E13 | F-06 | R05 | §1.3 ¶Supervisory architecture | Generic opener removed (IPC-5); host EU-project sentence replaced (CUT-10) by sourced supervision evidence (Janda: doctoral-school roles, 1997–2012 teaching, 2023 co-supervision example, research stays; Jung: doctoral-programme head, named courses, Halle-Wittenberg/Leipzig/Ulm experience) and accountabilities; no totals invented. | CUT-10 | — |
| E14 | F-07, F-13, F-14 | R06, R10 | §1.3 ¶Planned training activities and ELTE secondment | Timed, assessed training schedule with named providers and ELTE courses; M1–M3 primary-supervision continuity (weekly meetings, fortnightly joint sessions, shared records, joint sign-off, continuity/deputy arrangement without a named deputy); deliverable-backed teaching with host seminar otherwise; CDP cadence reconciled (CUT-23 removed here, allocated to E08). | — | §2.1 table cadence identical; §3.1 T5.1 keeps 'quarterly reviews'. |
| E15 | F-13 | R06, R10 | §1.3 ¶Two-way transfer | Generic opening sentence cut (CUT-20); s2–s4 verbatim. | CUT-20 | — |
| E16 | F-11 | R08 | §1.3 ¶Rationale and added value | s6 cut (CUT-11); s1–s5 and the final arrangements sentence verbatim. | CUT-11 | — |
| E17 | F-08, F-10 | R07 | §1.4 ¶A profile matched | Three competence-to-task links (physiology; EO/data science via the 2025 MATE stays and 2026 ELTE traineeship; recent crop work with the 2025 proceedings paper and two 2026 manuscripts labelled under review); DrR as a pre-existing desktop research prototype; disputed MSc omitted; undated/unnamed items and duplicated fit sentences removed (IPC-6). | — | Consumes CUT-1 (career duplicate in §1.1). |
| E18 | F-12 | R09 | §2.1 ¶FIELDWISE is designed | s2 cut (CUT-13); s1 verbatim. | CUT-13 | — |
| E18a | — | — | §2.1 ¶Two realistic trajectories | Record clause compressed (IPC-8); the two trajectories and K11 unchanged. | — | — |
| E19 | F-14 | R10 | §2.1 table, Career Development Plan row | Evidence cell reconciles quarterly reviews (M6–M30) with transition reviews M12/M21/M24/M27; D5.1 stays at M3. | — | — |
| E20 | F-23 | R16, R06 | §2.1 table, ATK training and ELTE secondment rows | The two training rows merged into one (ATK modelling training and the 12-month ELTE secondment); evidence cell D1.4 → D1.3 (IPC-9). | — | — |
| E21 | F-13 | R10 | §2.1 table, Transferable-skills row | Three dated independence measures added: methods clinic by M12; complete grant concept and mock-reviewed application by M21–M24 (submission only if an eligible call is open; no award promised); mentoring M10–M21 with peer-learning/teaching-practical fallback. | — | — |
| E22 | F-13 | R10 | §2.1 table, Scientific visibility row | Teaching venues and the COST Action CA22136 PANGEOS contact base named as the networking starting point (A-16). | — | — |
| E23 | F-11 | R08 | §2.1 ¶By completion | s3 cut (CUT-8); rest verbatim. | CUT-8 | — |
| E24 | F-12 | R09 | §2.2 ¶FIELDWISE uses a targeted strategy | s2 cut (CUT-17); the table's target-group column carries the audiences. | CUT-17 | — |
| E25 | F-15, F-23 | R11, R16 | §2.2 table, Dissemination row | Irrigation Science / ISHS venue added beside EGU/ECPA; release assets named; D1.4 → D1.3. | — | — |
| E26 | F-12 | R09 | §2.2 table, Communication row | Per audience: main message, tool, timing and evidence (practitioner brief M12, two demonstrations M25–M29, workshop of about 20 participants M29–M30, three explainers M3/M12/M24, one tutorial and HU/BG summaries M21–M24); evidence cell names attendance, feedback, views and downloads under project control. | — | — |
| E27 | F-11, F-12 | R08, R09 | §2.2 ¶Reach and uptake | Project-controlled reach indicators with the adopted targets (6–10 growers/advisors, 2–3 FMIS users, two demonstrations, one workshop, three explainers, one tutorial, two summaries); recruitment through AgroVIR stated as a target, attendance not equated with adoption. | — | — |
| E28a | F-11 | R08 | §2.3 intro | Duration sentence removed (stated in §1.3 and §3.1); the bounded-impact sentence kept. | — | — |
| E28 | F-11 | R08 | §2.3 table, Agricultural & environmental row | Water-saving boundary kept verbatim; added that irrigation, yield and quality are recorded by treatment and not used to estimate DrR-caused savings. | — | — |
| E29 | F-11 | R08 | §2.3 table, European & societal row | Row rewritten with the work-programme expected outcomes (skills and employability; international, inter-sectoral, interdisciplinary experience; knowledge exchange; research-to-teaching feedback) and the EU Water Resilience Strategy link without adopting its 10% ambition (A-12). | — | — |
| E30 | F-11 | R08 | §2.3 ¶Impact is measured | K1–K14 duplicate cut (CUT-7); three scales distinguished: direct delivery, AgroVIR's translation channel (over 700,000 ha, company-reported August 2025, attributed and bounded) and the narrower eligible-uptake group quantified during the placement and modelled only as a scenario. | CUT-7 | — |
| E31 | F-21 | R17 | §3.1 ¶The fellow leads | s2 cut (CUT-14); Section 3 starts on a new page (layout target kept explicit). | CUT-14 | — |
| E32 | F-23 | R16 | §3.1 WP1 deliverable line | D1.4 model/card → D1.3; D1.5 transfer specification → D1.4; K1–K4 verbatim. | — | — |
| E33 | F-18 | R13 | §3.1 WP2 deliverable line (K5) | K5 condensed (CUT-16) while keeping scheduled-versus-valid observation accounting. | CUT-16 | — |
| E34 | F-14, F-18 | R10, R13 | §3.1 WP5 task line | T5.1–T5.4 condensed (CUT-15) keeping 'quarterly reviews' (A-33). | CUT-15 | — |
| E35 | F-21 | R17 | §3.1 WP5 deliverable line | Administrative-outputs sentence cut (CUT-5); K11–K14 verbatim. | CUT-5 | — |
| E36 | F-17, F-18 | R13 | §3.1 ¶Critical path | Assumed February start with M3 freeze before first principal observations and second harvest by M20; honest slipped-start response; effort rationale from the accepted allocation (pre-freeze WP1 2.2 PM, later 2.8 PM diagnostics; period totals kept). | — | — |
| E37 | F-21, F-16 | R17, R12 | §3.1 risk table | Six decision-specific rows (archive rights/coverage and model freeze; field/irrigation/calendar; sensors/cloud/pixels; poor transfer; supervisor/ELTE access; engineering/IP/placement) with distinct ratings; no backup site, deputy or substitute provider claimed to exist (brief R17 alternative: six rows with added triggers). | — | — |
| E38 | F-16, F-22 | R12, R15 | §3.2 intro | Dependency statement (arrangements completed before the activity; nothing claimed as signed) and the resource-priority order (IPC-7). | — | — |
| E39 | F-20 | R14 | §3.2 table, HUN-REN ATK row | Team-balance sentence cut (CUT-2); hosting plan with provision deadlines (induction, workspace, instruments, workstation and secure storage, remote EO access, HR/data/IP/grants support) without inventing allocations. | CUT-2 | — |
| E40 | F-16 | R12, R06 | §3.2 table, ELTE row | Team-balance sentence cut (CUT-3); planned secondment tasks per block; access arranged before each block, no allocated instrument time claimed. | CUT-3 | — |
| E41 | F-16 | R12 | §3.2 table, MATE row | M1 archive and rights audit; only the legally accessible common subset used; no access terms or redistribution rights claimed. | — | — |
| E42 | F-16, F-22 | R12, R15 | §3.2 table, Krumatic row | Deliverable-based engineering scope contracted before paid development; lean-MVP fallback; no quotation, contract or funding allocation claimed. | — | — |
| E43 | F-16, F-02 | R12, R02 | §3.2 table, Commercial farmer row | Adopted field requirements and the field-readiness gate stated; no site named or described as secured. | — | — |
| E44 | F-16 | R12, R08 | §3.2 table, MVCRI row | Condensed (CUT-4) to a potential continuation route; not a guaranteed position, funded activity or multi-crop programme; protected sentence kept. | CUT-4 | — |

## 6. Unresolved owner claims and the safe response used

| Owner | Missing fact | Safe response applied |
|---|---|---|
| MATE / Dr Takács | Archive instrument, spectral range, per-year units, common physiological variables, analysis and reuse permissions | M1 archive and rights audit committed; conversion conditional on wavelength coverage and calibration records; only the legally accessible common subset used; no confirmed access terms or redistribution rights claimed (§1.1 O1, §1.2 Stage 1, §3.2 MATE row, risk R1). |
| Farmer + ATK | Site identity, polygons, irrigation control, crop calendar, labour, compensation, genuine backup site | Design presented as adopted requirements subject to the field-readiness gate; 'no site is described as secured'; backup site used only if genuinely available (§1.2 Stage 2, §3.2 farmer row, §3.1 critical path, risk R2). |
| Prof. Jung / ELTE | Paired-spectrum access, instrument/operator time, course access, remote computing, continuity/deputy | Published expertise and course names used; secondment tasks per block with access 'arranged before each block'; no allocated instrument or operator time claimed (§1.3, §3.2 ELTE row). |
| Prof. Janda / ATK | Supervision totals, current collaborations, committed hours, irrigation adviser, named deputy | One sourced supervision example (2023 co-supervision), CV-documented roles and research stays; proposed routine without committed hours; deputy arrangement without identity (§1.3). |
| Dr Hollós / ATK | Available time, statistical support, supervision record | Documented technical role and accountability only; no supervision total (§1.2, §1.3). |
| ATK support services | Workspace, equipment, compute/storage, onboarding, HR contacts | Hosting plan with M1 induction and 'each in place before its first use'; no office, computing, welfare or equipment allocation invented (§3.2 ATK row). |
| Krumatic + ATK | Scope, quotation, commissioning source, source delivery, licences | Deliverable-based scope 'contracted before paid development' and lean-MVP contingency; no quotation, signed contract or funding allocation claimed (§3.2 Krumatic row, risk R6). |
| AgroVIR | Crop-specific network subset, participants, channels, staff time | Dated public footprint (over 700,000 ha, August 2025) used as context only; recruitment stated as an agreed target, not a guaranteed channel; eligible subset quantified during the placement (§2.2, §2.3). |
| MVCRI | Post-project opportunity and support | 'Potential post-MSCA continuation route'; not a guaranteed position, funded activity or multi-crop validation programme (§3.2 MVCRI row). |
| Fellow | MSc status, DrR version/functions, training certificates, manuscript contributions | Disputed Environmental Engineering MSc omitted from B-1; DrR described as a pre-existing desktop research prototype; manuscripts labelled 'under review'; no contribution statement invented (§1.4). |

## 7. Cut ledger (each cut used once)

| Cut | Location | Removed text (start) | Allocated to | Charged to edit | Lines |
|---|---|---|---|---|---|
| CUT-25 | §1.1 ¶Problem s2 (p. 1) | High-value horticultural irrigation often relies on delayed visual sym… | R02 design/reference/phenology | E08 | 2 |
| CUT-1 | §1.1 ¶Pertinence s4–s5 (p. 1) | These objectives also advance the fellow from plant physiologist and a… | R07 researcher evidence | E02 | 3 |
| CUT-18 | §1.1 ¶Realistically achievable s3 (p. 2) | Previous MATE research established AquaCrop-based full-to-deficit irri… | R01/R03 transfer chain and named model | E05 | 2 |
| CUT-22 | §1.2 ¶Overall methodology s2 (p. 2) | Operational predictors comprise spectral, soil-water and meteorologica… | R01/R03 transfer chain and named model | E06 | 1 |
| CUT-9 | §1.2 ¶Integration of methods s2 (p. 3) | HUN-REN ATK supplies plant-stress physiology/modelling; MATE the multi… | R01/R03 transfer chain and named model | E11 | 1 |
| CUT-19 | §1.2 ¶Methodological challenges, UAV sentences (p. 3) | If clouds or acquisition timing prevent usable Sentinel-2 observations… | R02 design/reference/phenology | E08 | 2 |
| CUT-23 | §1.3 ¶Planned training s5 (p. 4) | These activities advance the fellow toward an independent Agricultural… | R02 design/reference/phenology | E08 | 1 |
| CUT-12 | §1.2 ¶Stage 3 condensed to one sentence (p. 3) | DrR – Digital Agronomist enters FIELDWISE as the fellow’s pre-existing… | R08 magnitude | E09 | 1 |
| CUT-11 | §1.3 ¶Rationale and added value s6 (p. 4) | Commercially sensitive evaluation uses protected, coded or appropriate… | R08 magnitude | E16 | 1 |
| CUT-10 | §1.3 ¶Supervisory architecture s7 (p. 4) | The host also provides demonstrated European-project experience: ATK c… | R05 supervision evidence | E13 | 2 |
| CUT-20 | §1.3 ¶Two-way transfer s1 (p. 4) | FIELDWISE connects internationally recognised plant-stress physiology,… | R06/R10 training and career | E15 | 1 |
| CUT-13 | §2.1 ¶FIELDWISE is designed s2 (p. 5) | The fellowship builds on competences already established in physiology… | R09 communication | E18 | 2 |
| CUT-8 | §2.1 ¶By completion s3 (p. 6) | The 12-month ELTE secondment adds sustained inter-institutional experi… | R09 communication | E23 | 1 |
| CUT-17 | §2.2 ¶FIELDWISE uses a targeted strategy s2 (p. 6) | Target groups are research communities, growers and advisors, FMIS/agr… | R09/R11 reach and release | E24 | 2 |
| CUT-7 | §2.3 ¶Impact is measured s3 (p. 7) | Delivery is tracked through K1–K14, covering archive harmonisation and… | R01/R02 overflow (three-scale magnitude) | E30 | 3 |
| CUT-5 | §3.1 ¶D5.1 CDP last sentence (pp. 8–9) | Required administrative outputs: mobility declaration within 20 days o… | R17 risk triggers / R13 effort | E35 | 2 |
| CUT-14 | §3.1 ¶The fellow leads s2 (p. 8) | Five WPs connect a frozen historical-data model, two prospective tomat… | R17 risk triggers / R13 effort | E31 | 1 |
| CUT-15 | §3.1 ¶Lead: fellow/ATK; supervisors (WP5 verbs) (p. 8) | implement the CDP, quarterly reviews, technical/transferable skills an… | R13 start window and contingency | E34 | 1 |
| CUT-16 | §3.1 ¶D2.1 dataset K5 (p. 8) | all scheduled observation opportunities accounted for, with | R13 start window and contingency | E33 | 1 |
| CUT-2 | §3.2 ATK row s4 (p. 10) | Where available and formally assigned early-stage female researchers w… | R14 hosting provision | E39 | 2 |
| CUT-3 | §3.2 ELTE row s5 (p. 10) | Where available, female students will participate in EO/geospatial pro… | R14 hosting provision | E40 | 2 |
| CUT-4 | §3.2 MVCRI row condensed (p. 10) | The institute provides a realistic pathway for crop-specific recalibra… | R12 dependency status | E44 | 2 |

Additional in-place compressions outside the cut pool (plan: compress duplication before removing content):

| Id | Location | What was compressed |
|---|---|---|
| IPC-1 | §1.1 ¶Realistically achievable s1 and s4 | Duration sentence repeated in §2.3 and §3.1; 'links this imposed deficit context' repeated in §1.2 Overall methodology. |
| IPC-2 | §1.1 ¶Four objectives, O2–O4 | Deficit-context, Sentinel-input and partner-role sentences merged; each is stated once in §1.2. |
| IPC-3 | §1.2 ¶Stage 1 ELTE secondment sentence | Secondment description kept in §1.3, §2.1 and §3.2; Stage 1 keeps only ELTE's role in the sensor-transfer specification. |
| IPC-4 | §1.2 ¶Integration of methods s1–s2 merged | Discipline list and role assignments merged into one sentence with accountabilities. |
| IPC-5 | §1.3 ¶Supervisory architecture s1 | Generic opener ('complementary expertise') removed; the evidence sentences carry the content. |
| IPC-6 | §1.4 ¶A profile matched | Undated Kleffmann employment, unnamed AI/ML course list, Novi Sad mobility, the disputed MSc claim and two duplicated fit sentences removed; three competence-to-task links replace them. |
| IPC-7 | §3.2 intro s3 | 'Each participating organisation contributes a complementary capacity' replaced by the dependency and resource-priority statements. |
| IPC-8 | §1.1 ¶Problem s5, ¶Pertinence closer, §2.3 intro s1, §2.3 Scientific row, §2.1 ¶By completion s2 and closer, §2.1 ¶Two trajectories, §1.2 ¶Integration opener, §1.3 ¶Placement s7 | Restated scope, duration, novelty and closing sentences compressed; each fact remains stated once elsewhere (the placement's IP arrangements are carried by the §2.2 IP row). |
| IPC-9 | §2.1 table training rows | The 'ATK scientific and modelling training' and '12-month distributed ELTE secondment' rows merged into one row; both measures and their evidence retained. |

## 8. Protected passages (do-not-touch list)

Each passage below was asserted verbatim in the built document (whitespace-normalised).

- §1.1 Beyond the state of the art (four assumptions, three advances)
- §1.1 Measurability and verifiability (metrics, M3 freeze, falsifiable hypothesis)
- §1.2 Stage 2 s1 and s4–s6 (frozen model, primary before recalibration)
- §1.2 Methodological challenges (i)–(vi)
- §1.2 Gender dimension and other diversity aspects
- §1.3 Structured supervision and governance
- §1.3 Two-way transfer s2–s4
- §1.3 Rationale and added value of the placement s1–s5
- §2.2 Exploitation row
- §2.2 IP and knowledge management row
- §2.2 Exploitation pathway
- §2.3 water-saving boundary
- §3.1 Decision gates and dependencies
- §3.1 Risk control integrity rule
- §3.1 K1–K4
- §3.1 K6
- §3.1 K7–K8
- §3.1 K9–K10
- §3.1 K11–K14
- §3.1 WP headers
- §3.1 WP headers
- §3.1 WP headers
- §3.1 WP headers
- §3.1 WP headers

## 9. Cross-reference validation

| Check | How it was checked | Result |
|---|---|---|
| D1.1–D1.4 consistent; no D1.5 remains | D1.5 forbidden; D1.1–D1.4 required at their months | PASS |
| Model freeze M3 throughout | 'frozen with its model card at M3 (D1.3)', MS1 (M3) required | PASS |
| D5.1 at M3 | 'Career Development Plan (D5.1, M3)' and 'D5.1 CDP (M3)' required | PASS |
| CDP review wording consistent | 'quarterly reviews', 'M6–M30', 'M12/M21/M24/M27' required | PASS |
| Five WPs present | WP1–WP5 headers parsed; WP6 forbidden | PASS |
| WP totals = 30.0 PM | header PM 5.0 + 9.0 + 6.0 + 5.4 + 4.6 | PASS |
| Fellowship 24 PM, placement 6 PM | '30.0 fellow PM: 24.0 in M1–M24 and 6.0 in M25–M30' required | PASS |
| ELTE secondment 12 months | 'M1–M3, M10–M12 and M16–M21 (12 months)' required | PASS |
| AgroVIR placement M25–M30 | 'AgroVIR placement (M25–M30)' required | PASS |
| Gantt labels match prose and tables | Gantt built from DELIVERABLE_MONTHS/MILESTONE_MONTHS; §3.1 lines checked against the same data | PASS |
| Risks match the revised design | R1–R6 rows built from RISK_ROWS; no backup site, deputy or substitute provider asserted to exist | PASS |
| Placeholders and process vocabulary absent | 29 forbidden patterns | PASS |
| Required design content present | 67 required phrases | PASS |
| Cut ledger | 22 cuts, each present in the baseline and absent afterwards | PASS |

DOCX validation: **0 failures**.

## 10. WP and person-month arithmetic

| WP | M1–M3 | M4–M9 | M10–M12 | M13–M15 | M16–M21 | M22–M24 | M25–M30 | Total |
|---|---|---|---|---|---|---|---|---|
| WP1 | 2.2 | 0.0 | 0.6 | 0.0 | 2.2 | 0.0 | 0.0 | 5.0 |
| WP2 | 0.3 | 4.2 | 0.3 | 0.6 | 3.6 | 0.0 | 0.0 | 9.0 |
| WP3 | 0.2 | 1.2 | 1.4 | 1.3 | 0.1 | 1.8 | 0.0 | 6.0 |
| WP4 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 5.4 | 5.4 |
| WP5 | 0.3 | 0.6 | 0.7 | 1.1 | 0.1 | 1.2 | 0.6 | 4.6 |
| Period total | 3.0 | 6.0 | 3.0 | 3.0 | 6.0 | 3.0 | 6.0 | 30.0 |

Fellowship months M1–M24: 24.0 PM; placement M25–M30: 6.0 PM (WP4 5.4 + WP5 0.6). The matrix reproduces the sealed WP totals and the 3/6/3/3/6/3/6 period totals; B-1 states only the pre-freeze split and the later WP1 share (§3.1).

## 11. Page-by-page visual validation

| Page | Footer | Slack (lines) | Min body pt | Min other pt | Margins mm | Images | Visual inspection |
|---|---|---|---|---|---|---|---|
| 1 | Part B - Page 1 of 10 | 0.1 | 11.0 | 9.0 | L 15.0 / R 14.0 | 0 | Title, 1 Excellence, 1.1; footnotes 1–7 at 9 pt legible; no clipping; header/footer intact. |
| 2 | Part B - Page 2 of 10 | 0.5 | 11.0 | None | L 15.0 / R 14.0 | 0 | Measurability (verbatim), Realistically achievable, Beyond the state of the art (verbatim), 1.2 heading, Overall methodology, Stage 1 start; justified text clean. |
| 3 | Part B - Page 3 of 10 | 0.4 | 11.0 | None | L 15.0 / R 14.0 | 0 | Stage 1 end, Stage 2, Stage 3, challenges (i)–(vi), Integration, Gender (verbatim), Open science start; no orphan headings. |
| 4 | Part B - Page 4 of 10 | 0.1 | 11.0 | 9.0 | L 15.0 / R 13.9 | 0 | Open science end, 1.3 heading, Supervisory, Structured supervision (verbatim), Training, Two-way; footnotes 8–9 at 9 pt. |
| 5 | Part B - Page 5 of 10 | 1.6 | 11.0 | 10.0 | L 15.0 / R 14.0 | 0 | Placement rationale, 1.4, 2 Impact, 2.1, trajectories, §2.1 table header + first two rows; table rows intact, header row repeats on page 6. |
| 6 | Part B - Page 6 of 10 | 1.1 | 11.0 | 10.0 | L 15.0 / R 14.0 | 0 | §2.1 table rows 3–5, By completion, 2.2 heading, full §2.2 table at 10 pt; 'Communication' label on one line after the column re-balance; no split rows. |
| 7 | Part B - Page 7 of 10 | 6.7 | 11.0 | 10.0 | L 15.0 / R 14.1 | 0 | Exploitation pathway (verbatim), Reach, 2.3 heading, §2.3 table, Impact paragraph; about seven blank lines before the page break, as in the sealed version's page 7. |
| 8 | Part B - Page 8 of 10 | 1.9 | 11.0 | None | L 15.0 / R 14.1 | 0 | Section 3 starts at the top of the page; 3.1, WP1–WP5 blocks with D1.3/D1.4 renumbered; page full. |
| 9 | Part B - Page 9 of 10 | 2.5 | 11.0 | 10.0 | L 15.0 / R 15.0 | 1 | Decision gates (verbatim), Critical path with calendar and effort, Risk control, six-row risk table, regenerated Gantt (labels 1.2/3; 5.1 and 1.4; 2.2) ending above the footer; sharp. |
| 10 | Part B - Page 10 of 10 | 7.0 | 11.0 | 10.0 | L 15.0 / R 14.1 | 0 | 3.2 heading at the top (keep-with-next), intro, seven-row organisation table at 10 pt; about seven blank lines remain; no overflow. |

## 12. Formatting and PDF technical checks

| Check | Evidence | Result |
|---|---|---|
| Page count | 10 | PASS |
| Page size | 595.3x841.9 pt | PASS (A4) |
| Encryption | none | PASS |
| Fonts | BCDEEE+Calibri (embedded), BCDFEE+Calibri (embedded), BCDGEE+Aptos (embedded), BCDHEE+ArialMT (embedded), BCDIEE+TimesNewRomanPS-BoldMT (embedded), BCDJEE+TimesNewRomanPS-BoldItalicMT (embedded), BCDKEE+Arial-BoldItalicMT (embedded), BCDLEE+TimesNewRomanPS-BoldItalicMT (embedded), BCDMEE+TimesNewRomanPSMT (embedded), BCDNEE+TimesNewRomanPSMT (embedded), BCDOEE+TimesNewRomanPS-BoldMT (embedded) | PASS |
| Body text ≥ 11 pt / other ≥ 8 pt (header and footer excluded, superscripts excluded) | per page above | PASS |
| Margins ≥ 15 mm (excluding header/footer) | per page above | PASS |
| Footers 'Part B - Page n of 10' | all pages | PASS |
| Placeholders / comments / tracked changes | none in DOCX XML or PDF text | PASS |
| Layout targets (§3 on page 8, Gantt on page 9, §3.2 on page 10) | met | PASS |
| Table text size | FW Table style 10 pt (sealed: 11 pt); plan permits tables, captions and footnotes at ≥ 8 pt | PASS |
| Gantt | regenerated at 2125×760 px, same 17.99 cm width as the sealed image, height reduced from 8.26 cm to 6.43 cm; labels renumbered | PASS |

### Prose profile note

Sentences over 35 words: 18 in the sealed B-1, 45 in the revised B-1. The plan forbids general stylistic rewriting and the 10-page limit forced dense enumerations (design dimensions, decision criteria, training schedule). The prose profile's sentence-length rule therefore conflicts with the content; the long sentences are lists, each item one design element, and were left as lists rather than mangled into fragments. Reported, not silently broken.

## 13. Final file hashes (SHA-256)

- `docs\tier5_deliverables\final_exports\FIELDWISE_Part_B1_refactored_2026-09-08.docx`: `5d57b057dbbd993ce32b6ff804cb7c502fb4e6d856c7c1dcb73752e820696579`
- `docs\tier5_deliverables\final_exports\FIELDWISE_Part_B1_refactored_2026-09-08.pdf`: `6fb56e517df9eef5bd5de3258d414b67e0781f44c90a095aad4d0fefcc643371`
- `docs\tier5_deliverables\final_exports\FIELDWISE_Part_B1_gantt_refactored_2026-09-08.png`: `a9483481461699b11889c7460c370f733332075863e31e78591dddc37c15ec11`
- `docs\tier5_deliverables\submitted\FIELDWISE_Part_B1_10_pages.docx`: `79e23ee5357e36cf0051602048cc88d5fd1a8c5d325a5e9898852ec62829e18c`
- `docs\tier5_deliverables\submitted\FIELDWISE_101373105_submitted_2026-09-07.pdf`: `c3bfb51f93b4c0c36221d0bd83dab77efaa619eee4f3dd937e58d728c3f81dbe`

## 14. Accepted details that could not be included

| Detail | Reason |
|---|---|
| R01 view/illumination geometry recording and BRDF sensitivity test | Lower-value detail of the transfer chain; the chain's testable elements (SRF integration, band exclusion, corrections, Level-2A, 20 m grid, pixel rules, engineering screen) are in §1.2. |
| R01 reporting of paired bias, RMSE, slope and prediction disagreement by band/index, season, stage | Subsumed under 'diagnose sensing discrepancies' and the D2.2 report; metrics are fixed in D1.2. |
| R02 simulation of interval precision and detection performance from archive counts | Owner counts unavailable; the design is presented as targets with an attrition sensitivity scenario, not a power claim. |
| R02 '60–70% replacement' deficit level and the '1,440 plant visits' total | Cut for space in the final fitting round; the regimes are named (well-watered, deficit-irrigated, unirrigated) and the 288 area-date records and 202-pair attrition scenario carry the scale; the deficit level belongs to the D1.2 protocol. |
| R06 M1–M3 continuity items 'ATK laboratory visits around measurement needs' and the 'grant-writing/valorisation clinic' assessed output | Cut for space; the weekly meetings, fortnightly joint sessions, shared records, joint sign-off and deputy arrangement are stated, and the grant clinic is carried by the §2.1 independence measures. |
| R03 calibration method detail (sigmoid vs isotonic) and abstention under domain shift wording | Kept to 'calibration fitted only inside training folds' and 'abstention or a limited-evidence flag'; the method choice belongs to D1.2. |
| R06 full course-to-competence table and R09 audience table | Rendered as compact clauses in §1.3 and in the §2.2 Communication row; every provider, period, competence, assessed output, audience, message, channel, timing and evidence is stated. |
| R08 optional 300-view aggregate target | Marked optional in the brief; not adopted. |
| R13 seven-period effort matrix as a table | Plan allows the smallest wording; §3.1 states the pre-freeze split, the later WP1 diagnostics share and the unchanged period totals; the full matrix is reproduced in this report. |
| R14 planning specification of workstation RAM/storage figures | Not an ATK allocation; the hosting plan names the workstation, secure versioned storage and remote EO access without figures. |

## 15. Substitutions from the answer bank

- R02 physiological reference: the preferred two-marker rule is adopted, with the brief's alternative (one continuous endpoint) stated as the in-text condition if no common two-marker reference exists across the archive.
- R01 failed-conversion route: the fallback (defensible common predictors plus a soil-water/meteorological baseline, failed transfer reported) is stated as the in-text condition, not as the design.
- R05: the alternative (named documentary examples instead of totals) was used because supervision totals and current collaborations are owner facts that were unavailable.
- R06: assessed supervisor-led modules drawing on the named ELTE subjects replace promised course enrolment (owner timetable unavailable).
- R07 MSc: the safe response (omit the disputed credential) was used.
- R10: mentoring carries the peer-learning/teaching-practical alternative in text; grant submission only if an eligible call is open.
- R12/R14/R15: safe responses for MATE, farmer, ELTE, ATK, Krumatic, AgroVIR and MVCRI as listed in Section 6.
- R16: the Gantt was regenerated reliably, so the preferred renumbering was applied; the fallback (keep the gap) was not needed.

