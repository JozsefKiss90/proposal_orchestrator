---
record_type: tier3_training_and_career_development
authority: "CLAUDE.md §5 Tier 3, §12.2 status categories, §13.3 no fabricated project facts, §10.5 traceability"
source:
  - docs/tier3_project_instantiation/source_materials/part_b_draft_v0/FIELDWISE_MSCA_Master_Draft.docx
  - docs/tier3_project_instantiation/source_materials/operator_input_pack/fieldwise_operator_input_pack.md
lift_record: docs/tier4_orchestration_state/decision_log/fieldwise-training-career-lift_2026-08-13.json
provenance_manifest: docs/tier3_project_instantiation/hand_lift_provenance.json
spine_status: confirmed_real
validation_status: Confirmed
source_ref: "Draft ¶181 (Open Science); §1.3 ¶183-211; §1.4 ¶213-216; §2.1 ¶219-222; §2.2 ¶224-238; §3.2 ¶425-432. Operator input pack items 4, 5, 6, 12 and the placement decision (item 2)."
note: >
  This record carries two source classes and labels every statement with which one it came from.
  DRAFT-LIFTED prose is reproduced verbatim from the master draft with no rewriting (§10.5);
  paragraph numbers ¶N follow the numbering scheme defined in hand_lift_provenance.json.
  OPERATOR-DECIDED content is folded from the returned input pack, where the operator recorded
  an explicit ACCEPT (or a raised/amended variant) against a candidate; the decision-log record
  for each item is cited inline. No sentence states a project fact that is absent from both
  sources. Facts that neither source settles are carried here as Unresolved and named as such,
  not silently omitted and not assumed covered.
lift_reason: >
  Phase 2 run d00fc75d recorded four unresolved scope conflicts (CF-01 training activities,
  CF-02 Career Development Plan, CF-03 EO-03/04/05/06/08 framing, CF-04 placement added value)
  and failed phase_02_gate predicate g03_p06. The material answering all four was already
  decided, but lived in source_materials/, working_assumptions.json and the decision log —
  none of which concept-alignment-check reads. Its reads_from is project_brief/ only. This
  record moves the decided material into the directory the skill can see. Nothing was invented
  to close a conflict.
---

# FIELDWISE — Training, career development and institutional framing

<!-- OPERATOR-DECIDED | input pack item 6 (ACCEPT, 2026-08-11) | decision_log/fieldwise-item6-career-development-plan_2026-08-12.json -->
## Career Development Plan

A Career Development Plan is established jointly by the supervisors and the researcher and
submitted as an early project deliverable, **D1.3 Career Development Plan, due M3, owned by
FELLOW and SUPERVISOR**. The plan is agreed by M3 and reviewed at M6, M12, M16 and M20,
alongside the steering points of the governance model below.

The plan comprises six components:

| Component | Content |
|-----------|---------|
| Research objectives | O1 to O6 (draft §1.1.8) |
| Training and career needs | The eleven ELTE-to-fellow competences below, delivered as supervised practice plus named ELTE courses |
| Transferable skills | Research integrity; open science and FAIR practice; generative-AI literacy; grant writing; IP and exploitation; project management; science communication |
| Teaching | See "Teaching and education" below |
| Publications planning | Outputs P1 to P4, with at least two peer-reviewed submissions during or shortly after the fellowship |
| Open science engagement | Open-access publication, code and model cards where IP permits, FAIR metadata, validation split manifests |

<!-- OPERATOR-DECIDED | input pack item 4, amended C6/co-supervisor note (2026-08-11) | decision_log/fieldwise-item4-governance_2026-08-12.json -->
The plan is signed by both supervisors and the fellow. The call requires it to be
"established jointly by supervisor and researcher"; with a co-supervisor in place, joint
establishment means both.

<!-- DRAFT-LIFTED ¶181 -->
## Open Science

FIELDWISE will follow "as open as possible, as closed as necessary". Expected open outputs
include harmonisation protocols, validation split manifests, hyperspectral-to-Sentinel
methodology, analysis/model code where IP permits, model cards, FAIR metadata, selected
derived/anonymised datasets and open-access publications.

<!-- DRAFT-LIFTED §1.3 ¶183-194 (ELTE to Fellow), ¶195-204 (Fellow to ELTE), ¶205 (bidirectionality), ¶206-211 (partner contributions) -->
## Supervision, training and two-way transfer of knowledge

ELTE -> Fellow: geoinformatics; EO time-series analysis; optical/SAR integration;
hyperspectral-to-multispectral transfer; spatio-temporal modelling; Bayesian hierarchical
modelling; uncertainty quantification; transfer learning/domain adaptation; reproducible
geospatial computation; research software/web deployment; IP and research exploitation.

Fellow -> ELTE: plant physiology; horticultural crop science; plant protection/agronomy;
water-stress experimentation; physiological phenotyping; hyperspectral field measurements;
biological interpretation of EO; DrR - Digital Agronomist preliminary development; access to
complementary agricultural research collaborations.

The transfer is genuinely bidirectional: crop physiology/agronomy <-> geospatial/data science.

MATE provides the long-term experimental knowledge and source-domain dataset necessary for
model development and validation. MVCRI provides the independent Bulgarian research
environment required for cross-country scientific transferability; its role is specifically
Hungary -> Bulgaria rather than simply increasing sample size. AgroVIR provides the bridge
from research field to farmer field and from research prototype to operational requirements.
This produces a genuine academic-research-industry knowledge chain.

<!-- OPERATOR-DECIDED | input pack item 4 (ACCEPT with amendment, 2026-08-11) | decision_log/fieldwise-item4-governance_2026-08-12.json -->
## Supervision cadence and governance

Weekly one-to-one meeting between the fellow and the supervisor. A weekly technical session
with the co-supervisor through WP3 and WP4 (M6-M21), tapering to monthly outside that window.
A monthly written progress record held by the fellow. A quarterly review against the Career
Development Plan, attended by both supervisors.

A Project Steering Group chaired by the supervisor, with the fellow, the co-supervisor and one
named contact each from MATE, MVCRI and AgroVIR. It meets at M6, M12, M16 and M20 — the four
decision points the draft already names — and issues a go/no-go verdict on milestones MS1 to
MS5.

Decision rights: scientific method and day-to-day research choices rest with the fellow,
escalating to the supervisor; model development and testing methodological lead and quality
assurance rest with the co-supervisor, escalating to the supervisor; training plan, resources
and milestone go/no-go recommendation rest with the supervisor, escalating to the Steering
Group; contract, finance, IP and open-access policy rest with the host; access to partner data
and field sites rests with the owning partner, escalating to the Steering Group.

Conflict resolution has two steps: the fellow and supervisor resolve disagreements directly and
record the outcome in the monthly progress record; anything unresolved after one cycle escalates
within ELTE and then to the ELTE research integrity route. Data-access disputes follow the
dispute clause of the relevant data-sharing agreement.

> **Unresolved (§12.2).** The input pack's C6 note records that the accepted escalation route
> ran partly through a post the supervisor himself holds, and that the defect is real and still
> open. The escalation target above is therefore stated without naming that post. See
> decision_log/fieldwise-item4-governance_2026-08-12.json.

<!-- OPERATOR-DECIDED | input pack item 5, C7 raised (2026-08-11) | decision_log/fieldwise-item5-kpis_2026-08-12.json -->
## Teaching and education

Research results feed back into teaching at the host through three measures:

- Co-design and deliver a full module unit within an ELTE MSc course on Earth observation for
  agriculture, rather than a single guest lecture.
- Co-supervise the field-experiment component of one PhD student's work.

In the Career Development Plan the teaching component is framed as an existing strength
transferred into a new discipline, a new institution and a new language of instruction, not as
a competence to be acquired: the researcher taught for five years at Agricultural University
Plovdiv (2015-2020), including syllabus design, lecturing and examining in Bulgarian and
English, and Bachelor's thesis supervision. The developmental content is the move from plant
protection teaching in Bulgarian at a Bulgarian agricultural university to Earth-observation
teaching in English at a Hungarian informatics faculty, and the step from Bachelor's to
doctoral supervision.

> **Confirmed (§12.2).** MSc thesis supervision was removed by the operator on 2026-08-14. The
> measure previously read "primary-supervise one ELTE MSc thesis to completion" and carried an
> Assumed note, because primary supervision may require a formal ELTE affiliation or status the
> fellow will not automatically hold. The operator has decided against MSc thesis supervision
> rather than resolving that status question, so the measure is withdrawn outright — the
> fallback to co-supervision is withdrawn with it, since the decision is about MSc thesis
> supervision as such and not about the grade of it. Two measures carry the teaching component:
> the module unit, which was always the one that carries the ambition, and the PhD
> field-experiment co-supervision, which is unaffected. This is an operator decision about the
> action's own design, so it is Confirmed rather than declared. See
> decision_log/fieldwise-open-items-fold_2026-08-14.json.

<!-- DRAFT-LIFTED §2.2 ¶224-230 | OPERATOR-DECIDED input pack item 5, EI-03 (ACCEPT, 2026-08-11) -->
## Networking, communication and public engagement

Scientific dissemination targets publications around four principal scientific outputs:
P1 physiological and hyperspectral early-warning signatures of processing-tomato water stress;
P2 hyperspectral-to-Sentinel scaling for water-stress prediction; P3 temporal and cross-country
transferability of agricultural water-stress models; P4 research-to-commercial transfer and
decision-oriented evaluation of agricultural AI. At least two high-quality peer-reviewed
submissions are targeted during or shortly following the fellowship.

Public engagement beyond scientific peers: one public field demonstration with AgroVIR farmers,
and one public-facing article per year.

Science communication is one of the seven transferable-skill strands of the Career Development
Plan.

<!-- OPERATOR-DECIDED | input pack item 5, EI-04 adopted wording, C8 closed (2026-08-11) | decision_log/fieldwise-item5-kpis_2026-08-12.json -->
## Alignment of working conditions with the European Charter for Researchers

Charter alignment is evidenced at instrument level by the Career Development Plan (D1.3), by
ELTE's open recruitment and researcher-development policies, and by the supervision and
training arrangements set out above.

> **ELTE does not hold the HR Excellence in Research (HRS4R) award.** The operator confirmed
> this on 2026-08-11 and the claim was removed permanently, not provisionally. It must not be
> restored unless ELTE actually obtains the award. The input pack records that an earlier
> candidate wording asserted the status while the answer beside it said "unknown"; carrying
> that forward would have put a false, one-click-checkable institutional claim into a submitted
> proposal.

> **Unresolved (§12.2).** This is the thinnest of the expected-impact mappings — it rests on
> D1.3, institutional policy and the supervision arrangements, with no external accreditation
> behind it. Naming an ELTE researcher-development or HR policy document, if one exists, would
> strengthen it.

<!-- DRAFT-LIFTED §1.4 ¶213, ¶215-216 and §2.1 ¶219-222 -->
## Career perspectives and employability

The researcher combines a foundation in agronomy, plant protection and plant physiology with
developing expertise in EO, GIS and agricultural data science. FIELDWISE will address the
remaining competence gap in Bayesian modelling, spatio-temporal AI, sensor transfer,
uncertainty, domain adaptation and decision evaluation. Intended career progression: Plant
Physiologist/Agronomist -> EO/Geospatial Crop Scientist -> Independent researcher in
transferable agricultural intelligence.

FIELDWISE will create a distinctive scientific profile combining biological understanding with
scalable geospatial prediction and operational agricultural decision support. The fellowship
will provide advanced competence in Bayesian/probabilistic modelling, uncertainty
quantification, spatio-temporal validation, sensor-domain transfer, cross-country adaptation,
operational AI evaluation, research-to-MVP translation and IP/exploitation. The researcher will
gain experience taking a scientific concept through experimental evidence -> validated model ->
cross-country testing -> commercial-field testing -> MVP. This profile is relevant to European
research institutes, universities, EU agricultural/environmental research, EO organisations,
precision-agriculture companies, irrigation technology and FMIS providers.

<!-- OPERATOR-DECIDED | placement decision (input pack item 2, RESOLVED 2026-08-11) | decision_log/fieldwise-placement-hosting_2026-08-12.json -->
## Non-academic placement: added value for the project and for the researcher

AgroVIR is the non-academic placement host. Six months are added at the end of the action,
which runs 30 months: M1-M24 at ELTE, M25-M30 on placement at AgroVIR, in Budaörs, Hungary.

**Added value for the project.** The placement makes the operational-transfer half of the
proposal structural rather than asserted. Gap G5 and hypothesis H5 both claim that
research-to-farm transfer is where models break; a six-month period embedded in the company
that runs the farms is the strongest available evidence that the proposal takes its own gap
seriously. It also answers the criticism recorded in §2.2 of the previous evaluation, that the
economic and technological route to users was insufficiently substantiated.

**Added value for the researcher's career.** The placement supplies the inter-sectoral half of
the career progression above — operational AI evaluation, research-to-MVP translation and
exposure to commercial agricultural software requirements — none of which the academic host can
provide. It is the segment of the profile that makes the researcher employable in
precision-agriculture, irrigation-technology and FMIS companies as well as in academia.

**Why it must be inside the company and why it needs six months.** The nine-dimension MVP
assessment, farmer-field access and the FMIS integration roadmap all depend on the company's
own operational environment and customer-facing requirements. AgroVIR co-leads WP5 from M16 and
hosts the fellow from M25 to M30.

> The placement is evaluated. The 2026 Guide for Applicants states that the non-academic
> placement "should be described in part B-1 and the evaluators will assess their relevance and
> quality in the respective criterion", so this argument belongs in Part B-1 and not only in the
> work plan. No letter of commitment is to be included for a non-academic placement host;
> AgroVIR is instead encoded in Part A Section 2 as the placement host and requires a PIC, and
> the placement months are a separate line in Part A Section 3. The six-month ceiling is used in
> full, so there is no headroom if the plan later needs a seventh month.

<!-- DRAFT-LIFTED §3.2 ¶425-432 | OPERATOR-DECIDED input pack item 12 (PARTIAL, 2026-08-11) -->
## Host capacity, attractiveness and visibility

ELTE hosts at the Faculty of Informatics, Institute of Cartography and Geoinformatics; the
hosting team is the institute's remote-sensing group. Its GIS and Remote Sensing Laboratory
holds the institute's own hyperspectral capability — an Ultris S5 (VIS-NIR narrow bands) and a
Cubert CUVIS Lab Lite package — alongside DJI Matrice 350 RTK, Zenmuse L1, P1 and H20T payloads,
licensed ArcGIS, ENVI and MATLAB, and high-performance computing clusters with secure storage
for large remote-sensing datasets.

Hosting arrangements and support services: dedicated office and laboratory space; full
integration into the institute's research groups, weekly meetings and interdisciplinary
workshops; administrative and technical support for relocation, project management, procurement
and dissemination; access to short-term training courses; participation in international
networks (COST Actions, FAO/EU webinars).

MATE provides five-year data, the processing-tomato experimental environment,
hyperspectral/soil/weather information and primary scientific validation. MVCRI provides an
independent processing-tomato environment, a contrasting country and agro-climate, and
cross-country model validation and calibration. AgroVIR provides commercial farmer-field
testing, research-to-operation transferability, MVP requirements and interoperability
evaluation, and a prospective FMIS integration pathway.

> **Unresolved (§12.2).** Five capacity fields are deferred pending the organisations' own
> input and are not asserted here: ELTE recent projects and publications; ELTE previous MSCA
> hosting; MATE recent projects and publications; AgroVIR key people; AgroVIR relevant track
> record. The mentoring structure that Part B-1 §3.2 asks for is also not yet described. These
> block no runner gate; they thin §3.2 at drafting.
