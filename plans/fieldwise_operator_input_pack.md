# FIELDWISE operator input pack

Fourteen items block the FIELDWISE run. This form collects all of them in one pass. Fill in each
answer block in place and return the file. Ticket 6 folds your answers into Tier 3, and ticket 7
builds the authorisation packet from the result.

Source: `plans/fieldwise_reinstantiation_plan.md` §4. Draft: `FIELDWISE_MSCA_Master_Draft.docx` in
`docs/tier3_project_instantiation/source_materials/part_b_draft_v0/`.

## How to answer

Each item has four parts. "Draft basis" states what the draft already confirms, so you do not have to
repeat it. "Missing" names exactly what has no source. "Candidate" is a drafted answer for the eight
decision items, which you accept, edit, or replace. "Answer" is the block you fill.

Accept a candidate by writing `ACCEPT` on the first line of the answer block. Replace it by writing
your own text. Defer an item by writing `DEFER` and a reason. A deferred item stays Unresolved in
Tier 3 and appears in the authorisation packet with the gate it will fail.

Nothing you leave blank is guessed. A blank item becomes an Unresolved record under §13.3.

## The fourteen items

| # | Item | Severity | Gate it blocks | Candidate offered |
|---|------|----------|----------------|-------------------|
| 1 | Legal identity of MATE, MVCRI, AgroVIR | Blocks Phase 3 | `phase_03_gate` predicate `g04_p07` | No — you supply |
| 2 | Participation mode of the same three | Blocks Phase 3 | `phase_03_gate` predicate `g04_p07` | No — you supply |
| 3 | Ethics self-assessment | Blocks Phase 6 | `phase_06_gate` predicate `g07_p06` | Yes |
| 4 | Governance and supervision arrangements | Blocks Phase 6 | `phase_06_gate` predicates `g07_p07`, `g07_p08` | Yes |
| 5 | KPI set per impact claim | Blocks Phase 5 | `phase_05_gate` predicates `g06_p04`, `g06_p05` | Yes |
| 6 | Career Development Plan | Blocks Phase 6 | `phase_06_gate` predicate `g07_p09` | Yes |
| 7 | Identity-spine confirmation | Blocks authorisation | No runner gate — ticket 7 | No — you supply |
| 8 | Person-months per work package | High | None — Implementation criterion §3.1 | Yes |
| 9 | Optional unit-cost lines | High | `gate_09_budget_consistency` predicate `g08_uc03` | Yes |
| 10 | References and citations | High | None — Excellence criterion §1.1 | No — you supply |
| 11 | Researcher CV | High | None — Part B-2 §4 | No — you supply |
| 12 | Host and participant capacity | High | None — Part B-1 §3.2 and Part B-2 §5 | No — you supply |
| 13 | Security screening and Green Charter | Medium | None — Part B-2 §7 and §8 | Yes |
| 14 | Page-limit decision | Medium | None — Part B-1 10-page cap | Yes |

Three notes on that table, each a correction to plan §4.

Item 8 blocks no gate. `phase_04_gate` checks task months, milestone criteria and the critical path.
It does not check person-months. `gate_09` for a unit-cost instrument reads
`project_duration_months` from `selected_call.json`, not per-work-package effort. Person-months
therefore affect the Implementation score and the §3.1 narrative, not gate passage.

Item 5 blocks `phase_05_gate` through two predicates with different force. `g06_p04` is hard.
Every call expected impact must carry at least one mapped project output. `g06_p05` is soft.
It passes vacuously when the KPI list is present but empty, so the gate alone will not stop a
KPI-free proposal.

Items 11 and 13 feed Part B-2, which this run does not draft. `section_schema_registry.json` marks
sections 4 to 8 as out of scope. Your answers are still needed for a real submission, and item 11
also strengthens the in-scope §1.4.

---

## Item 1 — Legal identity of MATE, MVCRI and AgroVIR

Severity: Blocks Phase 3. Gate: `phase_03_gate` predicate `g04_p07` requires every work-package
assigned partner to exist in `consortium/partners.json`. Lands in: `consortium/partners.json`.

### Draft basis

The draft names all three by short name, country and function, and assigns work-package leadership
to two of them.

| Short name | Draft text | Function | Work plan role |
|------------|-----------|----------|----------------|
| MATE | "MATE, Hungary" as primary experimental and data environment | Five-year archive, tomato experiments, hyperspectral and soil and weather data, prospective validation | WP1 and WP2 co-lead, WP3 support, WP4 source domain |
| MVCRI | "Agricultural Academy / Maritsa Vegetable Crops Research Institute (MVCRI), Bulgaria" | Independent Bulgarian environment for cross-country transfer | WP4 target domain |
| AgroVIR | "AgroVIR" as operational and farmer-field evaluator | Commercial farmer-field testing, MVP requirements evaluation, FMIS pathway | WP5 co-lead |

### Missing

Seven fields per organisation. None appears anywhere in the draft.

- Full registered legal name, in the national language and in English.
- PIC, the nine-digit Participant Identification Code from the EU Participant Register.
- Entity type: public or private, non-profit status, and whether it is a higher education
  institution, a research organisation, or a company.
- Registered address: street, city, postcode, country, country code.
- Contact person: name, role, institutional email.
- Whether the organisation is already registered in the Participant Register.
- Whether a letter of commitment or support exists or is planned.

### Answer

```
ITEM 1 — LEGAL IDENTITY

MATE
  legal_name_national:
  legal_name_english:
  pic: 891269563
  entity_type:
  address_city:
  address_country_code:
  contact_person: Dr. Sándor Takács
  contact_email: tak5533@uni-mate.hu
  already_registered_in_participant_register: yes / no
  letter_of_commitment: planned 

MVCRI
  legal_name_national:
  legal_name_english:
  pic: 999533009
  entity_type:
  address_city:
  address_country_code:
  contact_person: Dr. Rositsa Cholakova
  contact_email: rositsa.cho@abv.bg
  already_registered_in_participant_register: yes 
  letter_of_commitment: planned 

AgroVIR
  legal_name_national:
  legal_name_english:
  pic: none
  entity_type:
  address_city: Budapest
  address_country_code:
  contact_person: Balázs Zsuzsanna
  contact_email:  balazs.zsuzsanna@agrovir.hu
  already_registered_in_participant_register:  no
  letter_of_commitment: none
```

---

## Item 2 — Participation mode of MATE, MVCRI and AgroVIR

Severity: Blocks Phase 3. Gate: `phase_03_gate` predicate `g04_p07`. Lands in:
`consortium/roles.json` and `consortium/partners.json`.

### Draft basis

The draft describes what each organisation contributes. It never states the legal relationship to
the action. ELTE is the sole beneficiary, so all three are non-beneficiaries in every scenario.

### Missing

One mode per organisation, from four options. Each carries a different consequence.

| Mode | What it means | Consequence |
|------|---------------|-------------|
| Associated partner | Contributes to the action without EU funding, listed in Part A and Part B-2 §5 | Simplest. Needs a partnership agreement and a capacity table |
| Secondment host | The fellow spends part of the fellowship there | Constraint CC-04 caps European Fellowship secondments at half the action, so at most 12 of the 24 months. The secondment must appear in the work plan and serve the objectives |
| Non-academic placement host | An added period at the end at a non-academic organisation | Constraint CC-07 allows up to 6 extra months, so the action would run 30 months. CC-09 requires the request to be integral to the proposal and it is evaluated. Only AgroVIR qualifies, since MATE and MVCRI are academic |
| Informal collaborator | No formal status in the action | The work plan cannot name it as a work-package lead. A `partners.json` record is still written, and the draft's "WP1 lead: MATE + ELTE" assignment would have to change |

Two facts you should weigh before answering.

The fellow's current affiliation is MVCRI, Plovdiv, per the superseded confirmation checklist.
The draft names her current employer as the independent site for the cross-country test. That is
defensible, and it needs an explicit statement in §1.2 that the Bulgarian evaluation stays
independent of the model development. The mobility rule is unaffected, because mobility is assessed against the host ELTE.

A non-academic placement at AgroVIR changes the duration from 24 to 30 months. That changes the
unit-cost budget by six months on every line, and it changes `project_duration_months` in
`selected_call.json`. Answer item 9 consistently with whatever you choose here.

### Answer

```
ITEM 2 — PARTICIPATION MODE

MATE:     associated_partner 
MVCRI:    associated_partner 
AgroVIR:  secondment_host / non_academic_placement 
  if non_academic_placement, months added at the end: 6

Total action duration after this decision (months):
Statement on MVCRI independence given the fellow's current affiliation:
```

---

## Item 3 — Ethics self-assessment

Severity: Blocks Phase 6. Gate: `phase_06_gate` predicate `g07_p06` requires a non-empty
`ethics_assessment.self_assessment_statement` in the Phase 6 output. An omission fails the gate, and
so does an unexplained "N/A". Lands in: `call_binding/confirmation_checklist.json`, then Phase 2
writes `compliance_profile.json` and Phase 6 writes the statement.

### Draft basis

Nothing. The draft contains no ethics section. It does commit to "as open as possible, as closed as
necessary" and to protecting farmer-specific and commercially sensitive information.

### Candidate

Five categories, with a proposed answer and the reasoning.

| Category | Candidate | Reasoning |
|----------|-----------|-----------|
| Personal data under GDPR | Yes, limited | The DrR web MVP holds user accounts and farm contact details. Field boundaries tied to a named holding are personal data for a natural-person farmer. ELTE's Data Protection Officer reviews the processing, and data minimisation applies |
| Farmer commercial data | Yes | Yields, irrigation records and field geometries from AgroVIR farms are commercially sensitive. A data-sharing agreement governs them, and results are published only in aggregated or anonymised form |
| Human participants | Yes, low risk | Task T5.6 assesses MVP usability and interoperability, which requires structured feedback from AgroVIR staff and participating farmers. That is research involving human participants. Informed consent forms and a right of withdrawal apply. No health, biometric or special-category data is collected |
| Animal subjects | No | The project studies processing tomato. No animal work occurs |
| Dual use and misuse | No | The application is civil agricultural decision support. Sentinel-2 is open Copernicus data. No export-controlled goods or technology are involved |

Two supporting positions. All data stays within the EU, since Hungary and Bulgaria are Member
States, so no third-country transfer arises. The candidate identifies ethics issues, which means
`ethics_issues_identified` is true and the proposal completes the Part A ethics self-assessment
table and Part B-2 §6.

### Answer

```
ITEM 3 — ETHICS

personal_data_gdpr:      ACCEPT 
farmer_commercial_data:  ACCEPT 
human_participants:      ACCEPT 
animal_subjects:         ACCEPT 
dual_use:                ACCEPT 
non_eu_data_transfer:    no
ethics_committee_approval_required: no
ELTE data protection officer consulted: no
```

---

## Item 4 — Governance and supervision arrangements

Severity: Blocks Phase 6. Gates: `phase_06_gate` predicate `g07_p07` requires at least one
governance body with composition and decision scope, and `g07_p08` requires every management role to
name a partner that exists in `partners.json`. Lands in:
`call_binding/confirmation_checklist.json`, consumed by the Phase 6 governance builder.

### Draft basis

The draft names four corrective decision points at M6, M12, M16 and M20, and it states that these
answer a previous evaluator criticism about late milestones. It describes the two-way transfer
between the fellow and ELTE. It defines no bodies, no meeting cadence and no decision rights.

### Candidate

Supervision. Weekly one-to-one meeting between FELLOW and SUPERVISOR. Monthly written progress
record held by the fellow. Quarterly review against the Career Development Plan of item 6.

Governance body. A Project Steering Group chaired by SUPERVISOR, with FELLOW and one named contact
each from DATA_PARTNER, TRANSFER_PARTNER and VALIDATION_PARTNER. It meets at M6, M12, M16 and M20,
which are the four decision points the draft already names, and it issues a go or no-go verdict on
milestones MS1 to MS5.

Decision rights.

| Decision | Owner | Escalation |
|----------|-------|-----------|
| Scientific method, day-to-day research choices | FELLOW | SUPERVISOR |
| Training plan, resources, milestone go/no-go recommendation | SUPERVISOR | Steering Group |
| Contract, finance, IP, open-access policy | HOST | ELTE research office |
| Access to partner data and field sites | The owning partner | Steering Group |
| Milestone go/no-go | Steering Group | HOST |

Conflict resolution. Two steps. FELLOW and SUPERVISOR resolve disagreements directly and record the
outcome in the monthly progress record. Anything unresolved after one cycle goes to the ELTE
Institute of Cartography and Geoinformatics head, and then to the ELTE research integrity route.
Data access disputes follow the dispute clause of the relevant data-sharing agreement.

### Answer

```
ITEM 4 — GOVERNANCE

supervision_cadence:        ACCEPT 
steering_group_composition: ACCEPT 
steering_group_meetings:    ACCEPT 
decision_rights_table:      ACCEPT 
conflict_resolution:        ACCEPT 
named contacts per partner (needed for g07_p08):
  DATA_PARTNER (MATE): Dr. Sándor Takács
  TRANSFER_PARTNER (MVCRI): Dr. Rositsa Cholakova
  VALIDATION_PARTNER (AgroVIR): Zsuzsanna Balázs
```

---

## Item 5 — KPI set per impact claim

Severity: Blocks Phase 5. Gates: `g06_p04` requires every Tier 2B expected impact to carry at least
one mapped project output. `g06_p05` requires every KPI to name a `traceable_to_deliverable` that
matches a deliverable in the Phase 3 work-package structure. Lands in:
`architecture_inputs/impacts.json`.

### Draft basis

The draft states five impact claims in §2.3: scientific, environmental, agricultural, technological
and European. It declines advance numeric targets for water saving and says impact will be
quantified from project evidence. The candidate respects that refusal. Every KPI below measures
something the project controls and delivers.

### Candidate

Ten KPIs, each tied to a draft deliverable.

| KPI | Target | Deliverable |
|-----|--------|-------------|
| K1 Harmonised archive coverage | Five seasons integrated with documented QC flags and metadata | D1.1 |
| K2 Sentinel-2 transferability verdicts | Every candidate hyperspectral feature carries an explicit transferable or hyperspectral-only verdict | D2.2 |
| K3 Forecast horizons evaluated | Horizons t+1, t+3 and t+5 each reported with calibration and prediction-interval coverage | D3.1 |
| K4 Released model documented | One model card published for the released predictive engine | D3.2 |
| K5 Cross-country gap quantified | Zero-shot and locally calibrated Hungary to Bulgaria performance both reported | D4.2 |
| K6 Adaptation cost stated | Adaptation protocol states the minimum local calibration volume needed | D4.3 |
| K7 MVP delivered | Web MVP reachable and serving stress probability, uncertainty, spatial risk, irrigation priority and temporal evolution | D5.1 |
| K8 Decision value measured | Field Decision Value computed for at least two competing models, with lead time, false action rate and missed stress rate reported | D5.3 |
| K9 External evaluation completed | AgroVIR report covers all nine assessment dimensions listed in §1.2 | D5.4 |
| K10 Integration path defined | FMIS roadmap names the required interfaces and the post-fellowship steps | D5.5 |

Two gaps the candidate cannot close from the draft.

`g06_p04` requires all six Tier 2B expected impacts to map to a project output. The draft's §2.3
covers EI-02 and EI-05. Sections 2.1 and 2.2 cover EI-01. Nothing in the draft addresses EI-03
public engagement, EI-04 alignment with the European Charter for Researchers, or EI-06 feeding
results into teaching. Phase 5 will fail this gate unless you decide those three.

Proposed additions, which need your decision rather than a lift.

- EI-03: one public field demonstration with AgroVIR farmers, and one public-facing article per
  year.
- EI-04: ELTE's HR Excellence in Research status and its Charter alignment stated in §3.2, plus
  the Career Development Plan as the instrument-level Charter measure.
- EI-06: one guest module in an ELTE MSc course on Earth observation for agriculture, and
  co-supervision of one MSc thesis.

### Answer

```
ITEM 5 — KPIs

K1 to K10 as drafted:  ACCEPT / edit below
edits:

EI-03 public engagement measure:  ACCEPT candidate 
EI-04 Charter alignment measure:  ACCEPT candidate 
  does ELTE hold HR Excellence in Research? unknown
EI-06 teaching measure:           ACCEPT candidate 
```

---

## Item 6 — Career Development Plan

Severity: Blocks Phase 6. Gate: `phase_06_gate` predicate `g07_p09` requires every
instrument-mandated implementation section to be addressed. Constraint CC-13 makes the plan
mandatory. Lands in: `call_binding/confirmation_checklist.json` and
`architecture_inputs/workpackage_seed.json`.

### Draft basis

Section 1.3 lists eleven competences ELTE transfers to the fellow and nine the fellow brings to
ELTE. Section 1.4 states the intended progression from plant physiologist to Earth-observation crop
scientist to independent researcher. Section 2.1 lists the competences the fellowship adds. None of
this is assembled as a plan, and no deliverable carries it.

### Candidate

CC-13 requires six components, established jointly by supervisor and researcher, and submitted as a
deliverable at the start of the action.

| Component | Content | Source |
|-----------|---------|--------|
| Research objectives | O1 to O6 | Draft §1.1.8 |
| Training and career needs | The eleven ELTE-to-fellow competences, delivered as supervised practice plus named ELTE courses | Draft §1.3 |
| Transferable skills | Research integrity, open science and FAIR practice, generative-AI literacy, grant writing, IP and exploitation, project management, science communication | Constraint CC-11 |
| Teaching | One guest module in an ELTE MSc course, co-supervision of one MSc thesis | New, see item 5 |
| Publications planning | Outputs P1 to P4, with at least two peer-reviewed submissions during or shortly after the fellowship | Draft §2.2 |
| Open science engagement | Open-access publication, code and model cards where IP permits, FAIR metadata, validation split manifests | Draft §1.2 |

The plan is agreed by M3 and reviewed at M6, M12, M16 and M20, alongside the steering points of item
4.

One structural consequence. CC-13 requires the plan as a project deliverable, and the draft's
deliverable list D1.1 to D5.5 has no entry for it. Ticket 4 must therefore seed a new deliverable,
proposed as D1.3 Career Development Plan, due M3, owned by FELLOW and SUPERVISOR. Without it, no
KPI can trace to the plan and §3.1 will not show it.

### Answer

```
ITEM 6 — CAREER DEVELOPMENT PLAN

six components as drafted:  ACCEPT 
edits:

agreed by month:            M3 :
review points:              M6, M12, M16, M20 
add deliverable D1.3 Career Development Plan at M3:  yes
```

---

## Item 7 — Identity-spine confirmation

Severity: Blocks authorisation. No runner gate checks this. Ticket 7 will not issue the
authorisation packet without it. Lands in: `call_binding/confirmation_checklist.json`.

### Draft basis

The draft confirms ELTE as host, Hungary as host country, and a 24-month European Fellowship. It
never names the fellow or the supervisor. Those names come from the superseded Tier 3, which the
purge removed. A reassertion without your confirmation would violate §13.3.

### What to confirm

Seven records carry forward from the pre-purge checklist. Confirm or correct each.

| Record | Pre-purge value |
|--------|-----------------|
| FELLOW | Dr. Rositsa Cholakova, plant physiologist. Current affiliation MVCRI, Bulgarian Agricultural Academy, Plovdiv. PhD 2020 |
| HOST | Eötvös Loránd University, Faculty of Informatics, Institute of Cartography and Geoinformatics, Budapest, Hungary |
| SUPERVISOR | Dr. András Jung, Deputy Head, Institute of Cartography and Geoinformatics, ELTE |
| VALIDATION_PARTNER | AgroVIR, Hungary, associated partner for farmer access and field validation |
| FELLOWSHIP_TYPE | European Fellowship, from the Bulgaria to Hungary intra-EU move |
| DURATION | 24 months, carried in `selected_call.json` as `project_duration_months` |
| CALL_BINDING | HORIZON-MSCA-2026-PF-01, deadline 2026-09-09 |

Two pre-purge records are superseded by the draft and should not carry forward. Confirm that
reading.

The DATA_PROVIDERS record named PlanetScope, Sentinel-1 SAR and ERA5 reanalysis. FIELDWISE uses the
five-year MATE hyperspectral archive, MATE soil and meteorological stations, and Sentinel-2. The ten
project decisions RQ1 to RQ10 described Route B latent-field-state fusion. FIELDWISE carries its own
RQ1 to RQ7 and H1 to H6, which ticket 3 lifts from §1.1.6 and §1.1.7.

### Answer

```
ITEM 7 — IDENTITY SPINE

FELLOW:               CONFIRM 
HOST:                 CONFIRM 
SUPERVISOR:           CONFIRM 
VALIDATION_PARTNER:   CONFIRM 
FELLOWSHIP_TYPE:      CONFIRM 
DURATION:             CONFIRM 
CALL_BINDING:         CONFIRM 

DATA_PROVIDERS record is superseded by the draft:  CONFIRM 
RQ1 to RQ10 decisions are superseded by the draft: CONFIRM 
```

---

## Item 8 — Person-months per work package

Severity: High. No gate. Part B-1 §3.1 is scored on "appropriateness of the effort assigned to work
packages", so this affects the Implementation criterion. Lands in:
`architecture_inputs/workpackage_seed.json`.

### Draft basis

The draft gives a month range per work package and nothing else. There are no task months, no effort
figures and no cross-cutting allocation.

### Candidate

The fellow's 24 months are the only MSCA-funded effort. Partner effort is in kind and is not costed
by the unit-cost derivation.

| Work package | Month range | Fellow person-months | Share |
|--------------|-------------|----------------------|-------|
| WP1 Historical data and target design | M1 to M6 | 3.0 | 12.5% |
| WP2 Physiological early warning and sensor transfer | M3 to M14 | 5.5 | 22.9% |
| WP3 Prospective and uncertainty-aware prediction | M6 to M18 | 5.5 | 22.9% |
| WP4 Temporal and cross-country transferability | M12 to M21 | 4.0 | 16.7% |
| WP5 Operational transfer, decision value and web MVP | M16 to M24 | 4.0 | 16.7% |
| Cross-cutting: management, training, dissemination | M1 to M24 | 2.0 | 8.3% |
| Total | | 24.0 | 100% |

The cross-cutting row matches the three continuous rows in the draft's Gantt table. Phase 4 will
check that concurrent work packages never demand more than one full-time equivalent in any month.
The ranges overlap at M6 and M16, so the schedule assigns partial effort in those months.

Partner effort is left as an indicative in-kind figure. Give one per organisation if you have it,
or accept the candidate and it is recorded as Assumed with a matching declaration in
`working_assumptions.json`.

### Answer

```
ITEM 8 — PERSON-MONTHS

fellow allocation as drafted:  ACCEPT / replace with:
  WP1:   WP2:   WP3:   WP4:   WP5:   cross-cutting:    (must total the action duration)

person-months, optional:
  MATE: 0.24 
  MVCRI: -
  AgroVIR: -
  ELTE supervisor: -
```

---

## Item 9 — Optional unit-cost lines

Severity: High. Gate: `gate_09_budget_consistency` predicate `g08_uc03` requires every budget
component to resolve to Confirmed or to an operator-declared Assumed value. Lands in:
`working_assumptions.json`.

### Draft basis

None. The budget is not a draft matter. The rates come from Tier 2B `unit_cost_rates.json`, and the
duration and host country come from `selected_call.json`.

### Candidate

Declare that none of the three optional lines applies. The reasoning is that all three are marked
"if applicable" or situational in the rate table. Family circumstances are established at
recruitment, and leave and special-needs events cannot be foreseen at proposal stage.

With none applying, the derivation is fully determined.

| Line | Rate | Basis | Amount |
|------|------|-------|--------|
| Living allowance | €6,350 per month × 78.7% Hungary coefficient | 24 months | €119,938.80 |
| Mobility allowance | €710 per month | 24 months | €17,040.00 |
| Research, training and networking | €1,000 per month | 24 months | €24,000.00 |
| Management and indirect costs | €650 per month | 24 months | €15,600.00 |
| Total | | | €176,578.80 |

Two things to know before you answer differently.

A yes on family allowance cannot currently be reflected in the derived artifact. The deterministic
deriver accepts an `include_family` flag, and the component bound to node n07 never sets it. See
`runner/unit_cost_budget.py:159` and the call at line 507. A yes answer therefore needs an engine
change before `gate_09` reports the right total, and I will raise that as a separate ticket rather
than hand-edit the artifact.

Long-term leave and special-needs allowances have no representation in the deriver at all. If either
applies, it is recorded in `working_assumptions.json` and stated in the proposal narrative, and it
stays outside the derived figure.

If item 2 adds a non-academic placement, every figure above changes by six months and the total
becomes €220,723.50.

### Answer

```
ITEM 9 — OPTIONAL UNIT-COST LINES

none of the three applies:  ACCEPT / correct below

family_allowance:            applies unknown at proposal stage
long_term_leave_allowance:   unknown at proposal stage
special_needs_allowance:     does not apply 

duration used for the derivation:  24 months 
```

---

## Item 10 — References and citations

Severity: High. No gate. Part B-1 §1.1 is scored on going beyond the state of the art, which an
uncited narrative cannot demonstrate. Lands in: `project_brief/concept_note.md`.

### Draft basis

The draft carries a full argument and zero citations. Several claims name specific figures that need
a source, most visibly the statement that around 30% of EU territory is affected by seasonal water
scarcity.

### What is needed

A reference list covering eight areas, with DOIs where they exist. The page budget of item 14 allows
roughly 25 to 35 references, because references count toward the 10-page cap.

- EU water scarcity and irrigation demand statistics, for §1.1.1.
- The critique of accuracy-centred evaluation in agricultural machine learning, for §1.1.2.
- Hyperspectral indicators of crop water stress, for gap G1 and hypothesis H1.
- Spectral resampling to Sentinel-2 response functions, for gap G2 and hypothesis H2.
- Transfer learning and domain adaptation in agricultural remote sensing, for gaps G4 and G5.
- Bayesian hierarchical modelling of crop processes, for methodology layer 6.
- Decision-value and lead-time evaluation of forecasts, for gap G6 and Field Decision Value.
- The fellow's own prior work, including the DrR prototype and the PhD thesis.

### Answer

```
ITEM 10 — REFERENCES

bib_file: docs/tier3_project_instantiation/source_materials/references/fieldwise_references.bib
reference_count: 35  (at the ceiling of the 25–35 budget item 14 allows)
list_below: yes — see "Reference list as supplied", grouped by the eight areas

"30% of EU territory" figure is supported by:  R01  European Environment Agency (2025),
  indicator WAT001. Exact sentence: "On average, about 30% of EU territory and 33% of
  the population are affected each year."

areas_covered: 8 of 8, one partially
AMENDED 2026-08-11 on receipt of the researcher's CV and ORCID 0009-0008-3761-3106.
  Area 8 was previously flagged as wholly uncitable. Two of its three strands now
  resolve: the PhD thesis is identified and citable (R34), and the fellow's own
  peer-reviewed stress-physiology work is citable (R35). The DrR prototype alone
  remains uncitable. See "Flag: area 8" below for what is left.
```

### Provenance and verification

Twenty-two of the 33 entries were taken from the operator-supplied literature review
`crop_water_stress_articles_review.pdf`, which is the primary source for this item, or were found
by search to fill areas that review does not cover. Every DOI listed was checked against Crossref,
a publisher record or the DOI resolver. Nothing here is quoted from memory.

Two entries carry a weaker check and are marked `[dc]` in the list. R24 Tarraf et al. resolved
through `doi.org` to a valid Elsevier record but Crossref rate-limited the metadata read, and R31
Wilks (2001) has a DOI, volume and start page confirmed from three sources but an end page taken
from a secondary listing. Confirm both before the list goes into a submitted Part B.

The review PDF covers areas 3 and 4 well and areas 5, 6 and 7 barely, so most of the search effort
went there. Its 28 references were not adopted wholesale: entries that only restate the same review
ground were left out to protect the page budget.

### Reference list as supplied

**Area 1 — EU water scarcity and irrigation demand, for §1.1.1** (3)

- **R01** European Environment Agency (2025). *Water scarcity conditions in Europe.* Indicator
  WAT001, published 28 November 2025.
  https://www.eea.europa.eu/en/analysis/indicators/use-of-freshwater-resources-in-europe-1
  — **supports the "30% of EU territory" figure**, and the southern-Europe permanent and seasonal
  stress shares.
- **R02** Hristov, J., Toreti, A., Pérez Domínguez, I., Dentener, F., Fellmann, T., Elleby, C.,
  Ceglar, A., Fumagalli, D., Niemeyer, S., Cerrani, I., Panarello, L., & Bratu, M. (2020).
  *Analysis of climate change impacts on EU agriculture by 2050.* JRC PESETA IV project, Task 3.
  EUR 30078 EN, Publications Office of the European Union, Luxembourg. JRC119632.
  https://doi.org/10.2760/121115 — climate-change exposure of EU agriculture and the water
  constraint on expanding irrigation in the Mediterranean.
- **R03** Lu, J., Shao, G., Cui, J., Wang, X., & Keabetswe, L. (2019). Yield, fruit quality and
  water use efficiency of tomato for processing under regulated deficit irrigation: A meta-analysis.
  *Agricultural Water Management*, 222, 301–312. https://doi.org/10.1016/j.agwat.2019.06.008
  — processing tomato specifically, for the claim that irrigation timing drives productivity, fruit
  quality and water-use efficiency.

**Area 2 — the critique of accuracy-centred evaluation, for §1.1.2** (4)

- **R04** Roberts, D. R., Bahn, V., Ciuti, S., Boyce, M. S., Elith, J., Guillera-Arroita, G.,
  Hauenstein, S., Lahoz-Monfort, J. J., Schröder, B., Thuiller, W., Warton, D. I., Wintle, B. A.,
  Hartig, F., & Dormann, C. F. (2017). Cross-validation strategies for data with temporal, spatial,
  hierarchical, or phylogenetic structure. *Ecography*, 40(8), 913–929.
  https://doi.org/10.1111/ecog.02881 — the canonical statement of why random splits leak across
  season, plot and field. Directly supports the §1.1.2 bullet on observations from related seasons
  appearing in both training and testing.
- **R05** Meyer, H., Reudenbach, C., Hengl, T., Katurji, M., & Nauss, T. (2018). Improving
  performance of spatio-temporal machine learning models using forward feature selection and
  target-oriented validation. *Environmental Modelling & Software*, 101, 1–9.
  https://doi.org/10.1016/j.envsoft.2017.12.001 — target-oriented validation, the method behind the
  year-blocked and country-blocked designs of methodology layer 7.
- **R06** Ploton, P., Mortier, F., Réjou-Méchain, M., Barbier, N., Picard, N., Rossi, V., Dormann,
  C., Cornu, G., Viennois, G., Bayol, N., Lyapustin, A., Gourlet-Fleury, S., & Pélissier, R. (2020).
  Spatial validation reveals poor predictive performance of large-scale ecological mapping models.
  *Nature Communications*, 11, 4540. https://doi.org/10.1038/s41467-020-18321-y — quantifies the
  optimism that random validation produces. Supports the claim that a model may learn
  environment-specific relationships rather than transferable ones.
- **R07** Meyer, H., & Pebesma, E. (2022). Machine learning-based global maps of ecological
  variables and the challenge of assessing them. *Nature Communications*, 13, 2208.
  https://doi.org/10.1038/s41467-022-29838-9 — the area-of-applicability argument, which is the
  formal version of FIELDWISE's transferability position.

**Area 3 — hyperspectral and physiological indicators of crop water stress, for G1 and H1** (4)

- **R08** Ahmad, U., Alvino, A., & Marino, S. (2021). A review of crop water stress assessment using
  remote sensing. *Remote Sensing*, 13(20), 4155. https://doi.org/10.3390/rs13204155
- **R09** Sharma, H., Sidhu, H., & Bhowmik, A. (2025). Remote sensing using unmanned aerial vehicles
  for water stress detection: A review focusing on specialty crops. *Drones*, 9(4), 241.
  https://doi.org/10.3390/drones9040241
- **R10** Velazquez-Chavez, L. J., Daccache, A., Mohamed, A. Z., & Centritto, M. (2024). Plant-based
  and remote sensing for water status monitoring of orchard crops: Systematic review and
  meta-analysis. *Agricultural Water Management*, 298, 109051.
  https://doi.org/10.1016/j.agwat.2024.109051 — the plant-based-versus-remote comparison that
  underpins G1's move from spectral proxy to physiological target.
- **R11** Zeyliger, A., & Ermolaeva, O. (2021). Water stress regime of irrigated crops based on
  remote sensing and ground-based data. *Agronomy*, 11(6), 1117.
  https://doi.org/10.3390/agronomy11061117 — ground-sensor and remote-sensing combination, for
  methodology layers 1 and 2.

**Area 4 — spectral resampling to Sentinel-2 response functions, for G2 and H2** (5)

- **R12** Perich, G., Aasen, H., Verrelst, J., Argento, F., Walter, A., & Liebisch, F. (2021). Crop
  nitrogen retrieval methods for simulated Sentinel-2 data using in-field spectrometer data.
  *Remote Sensing*, 13(12), 2404. https://doi.org/10.3390/rs13122404 — the closest published
  analogue to layer 3: field spectrometer reflectance convolved with the Sentinel-2 spectral
  response functions, then evaluated. The trait is nitrogen rather than water, which is worth
  stating when cited.
- **R13** Frampton, W. J., Dash, J., Watmough, G., & Milton, E. J. (2013). Evaluating the
  capabilities of Sentinel-2 for quantitative estimation of biophysical variables in vegetation.
  *ISPRS Journal of Photogrammetry and Remote Sensing*, 82, 83–92.
  https://doi.org/10.1016/j.isprsjprs.2013.04.007
- **R14** Delegido, J., Verrelst, J., Alonso, L., & Moreno, J. (2011). Evaluation of Sentinel-2
  red-edge bands for empirical estimation of green LAI and chlorophyll content. *Sensors*, 11(7),
  7063–7081. https://doi.org/10.3390/s110707063 — red-edge band capability, the specific spectral
  region H2 depends on.
- **R15** Cundill, S. L., van der Werff, H. M. A., & van der Meijde, M. (2015). Adjusting spectral
  indices for spectral response function differences of very high spatial resolution sensors
  simulated from field spectra. *Sensors*, 15(3), 6221–6240. https://doi.org/10.3390/s150306221
  — cross-sensor bias in resampled indices, which is exactly the quantity layer 3 sets out to
  measure.
- **R16** Jamshidi, S., Zand-Parsa, S., & Niyogi, D. (2020). Assessing crop water stress index of
  citrus using in-situ measurements, Landsat, and Sentinel-2 data. *International Journal of Remote
  Sensing*, 42(5), 1893–1916. https://doi.org/10.1080/01431161.2020.1846224 — in-situ to
  Sentinel-2 water-stress scaling in a high-value crop.

**Area 5 — transfer learning and domain adaptation, for G4 and G5** (5)

- **R17** Priyatikanto, R., Lu, Y., Dash, J., & Sheffield, J. (2023). Improving generalisability and
  transferability of machine-learning-based maize yield prediction model through domain adaptation.
  *Agricultural and Forest Meteorology*, 341, 109652.
  https://doi.org/10.1016/j.agrformet.2023.109652 — quantifies the out-of-region performance drop
  and what adaptation recovers. Supports H4.
- **R18** Ma, Y., Yang, Z., Huang, Q., & Zhang, Z. (2023). Improving the transferability of deep
  learning models for crop yield prediction: A partial domain adaptation approach. *Remote Sensing*,
  15(18), 4562. https://doi.org/10.3390/rs15184562
- **R19** Yang, J., Guo, X., Li, Y., Marinello, F., Ercisli, S., & Zhang, Z. (2022). A survey of
  few-shot learning in smart agriculture: developments, applications, and challenges. *Plant
  Methods*, 18, 28. https://doi.org/10.1186/s13007-022-00866-2 — how little local data adaptation
  needs. Supports RQ5 and the item-6 adaptation-cost KPI.
- **R20** Reuss, J., Macdonald, J., Becker, S., Richter, L., & Körner, M. (2025). The EuroCropsML
  time series benchmark dataset for few-shot crop type classification in Europe. *Scientific Data*,
  12, 664. https://doi.org/10.1038/s41597-025-04952-7 — a European cross-country few-shot benchmark,
  the closest published parallel to the Hungary-to-Bulgaria design.
- **R21** Colaço, A. F., Bramley, R. G. V., Richetti, J., & Lawes, R. A. (2025). What makes on-farm
  experimental data suitable for data-driven decision-making? Implications of trial design and
  spatial distribution of field data for machine learning models. *Precision Agriculture*, 26(5),
  85. https://doi.org/10.1007/s11119-025-10280-y — the research-plot to commercial-field gap. This
  is the strongest available support for G5 and H5.

**Area 6 — process-based and Bayesian hierarchical modelling, for methodology layer 6** (6)

- **R22** Tolomio, M., & Casa, R. (2020). Dynamic crop models and remote sensing irrigation decision
  support systems: A review of water stress concepts for improved estimation of water requirements.
  *Remote Sensing*, 12(23), 3945. https://doi.org/10.3390/rs12233945 — the process-based branch of
  the layer-6 model comparison.
- **R23** Gao, Y., Wallach, D., Hasegawa, T., Tang, L., Zhang, R., Asseng, S., Kahveci, T., Liu, L.,
  He, J., & Hoogenboom, G. (2021). Evaluation of crop model prediction and uncertainty using
  Bayesian parameter estimation and Bayesian model averaging. *Agricultural and Forest Meteorology*,
  311, 108686. https://doi.org/10.1016/j.agrformet.2021.108686
- **R24** `[dc]` Tarraf, B., Brun, F., Raynaud, L., Roux, S., Zhang, Y., Davadan, L., & Deudon, O.
  (2024). Assessing the impact of weather forecast uncertainties in crop water stress model
  predictions. *Agricultural and Forest Meteorology*, 349, 109934.
  https://doi.org/10.1016/j.agrformet.2024.109934 — uncertainty propagation in crop water-stress
  forecasting, the nearest match to FIELDWISE's own application.
- **R25** Poudel, P., Alderman, P. D., Ochsner, T. E., & Lollato, R. P. (2024). A parsimonious
  Bayesian crop growth model for water-limited winter wheat. *Computers and Electronics in
  Agriculture*, 217, 108618. https://doi.org/10.1016/j.compag.2024.108618 — supports the layer-6
  preference for the simplest adequate model, and the item-13 Green Charter commitment that rests on
  it.
- **R26** Bukombe, B., Csenki, S., Szlatenyi, D., Czakó, I., & Láng, V. (2023). Integrating remote
  sensing, proximal sensing, and probabilistic modeling to support agricultural project planning and
  decision-making for waterlogged fields. *Water*, 15(7), 1340. https://doi.org/10.3390/w15071340
  — probabilistic agricultural decision support in a Hungarian setting.
- **R27** Gneiting, T., Balabdaoui, F., & Raftery, A. E. (2007). Probabilistic forecasts, calibration
  and sharpness. *Journal of the Royal Statistical Society: Series B*, 69(2), 243–268.
  https://doi.org/10.1111/j.1467-9868.2007.00587.x — the definition of calibration and
  prediction-interval coverage that KPI K3 reports against.

**Area 7 — decision value and lead time, for G6 and Field Decision Value** (6)

- **R28** Murphy, A. H. (1993). What is a good forecast? An essay on the nature of goodness in
  weather forecasting. *Weather and Forecasting*, 8(2), 281–293.
  https://doi.org/10.1175/1520-0434(1993)008<0281:WIAGFA>2.0.CO;2 — the quality-versus-value
  distinction. This is the single reference that most directly grounds H6 and the FDV framework.
- **R29** Murphy, A. H. (1973). A new vector partition of the probability score. *Journal of Applied
  Meteorology*, 12(4), 595–600.
  https://doi.org/10.1175/1520-0450(1973)012<0595:ANVPOT>2.0.CO;2 — the reliability, resolution and
  uncertainty decomposition, the reliability term of FDV.
- **R30** Katz, R. W., Brown, B. G., & Murphy, A. H. (1987). Decision-analytic assessment of the
  economic value of weather forecasts: The fallowing/planting problem. *Journal of Forecasting*,
  6(2), 77–89. https://doi.org/10.1002/for.3980060202 — the cost-loss structure behind the false
  action and missed stress terms.
- **R31** `[dc]` Wilks, D. S. (2001). A skill score based on economic value for probability
  forecasts. *Meteorological Applications*, 8(2), 209–219.
  https://doi.org/10.1017/S1350482701002092 — a worked skill score built from decision value rather
  than accuracy, the closest formal precedent for FDV.
- **R32** Wilks, D. S., & Wolfe, D. W. (1998). Optimal use and economic value of weather forecasts
  for lettuce irrigation in a humid climate. *Agricultural and Forest Meteorology*, 89(2), 115–129.
  https://doi.org/10.1016/S0168-1923(97)00066-X — decision value applied to irrigation timing in a
  high-value vegetable crop. The nearest agricultural precedent FIELDWISE has.
- **R33** Giuliani, M., Crochemore, L., Pechlivanidis, I., & Castelletti, A. (2020). From skill to
  value: isolating the influence of end user behavior on seasonal forecast assessment. *Hydrology
  and Earth System Sciences*, 24(12), 5891–5902. https://doi.org/10.5194/hess-24-5891-2020
  — demonstrates in an irrigation case study that better skill does not translate proportionally
  into decision benefit. This is H6 stated by someone else, which is the useful kind of citation
  here.

### Area 8 — the fellow's own prior work (amended 2026-08-11)

The original flag said no citation could be provided for any of area 8. The CV and ORCID
0009-0008-3761-3106 close most of it. What follows replaces that flag.

**Now citable, added to the list as R34 and R35.**

- **R34** Cholakova-Bimbalova, R. (2020). *Response of maize (Zea mays L.) to low temperatures and
  the effectiveness of subsequent foliar fertilisation* [PhD thesis]. Agricultural University –
  Plovdiv, Faculty of Agronomy, Department of Plant Physiology and Biochemistry. Supervisor
  Prof. Dr. Andon Vassilev. Doctoral programme Plant Physiology, professional field 6.1 Agronomy.
  Abstract at https://www.au-plovdiv.bg/docs/Razvitie_AS/PhD/2020/R_Cholakova/Abstract-Rositsa-Cholakova.pdf
  — the thesis strand of area 8. **One caveat:** the English title above is my rendering of the
  Bulgarian original, and the copy of the title I could read was truncated mid-phrase. Confirm the
  exact wording, in Bulgarian and in English, before it goes into a submitted Part B.
- **R35** Cholakova-Bimbalova, R., Petrov, V., & Vassilev, A. (2019). Photosynthetic performance of
  young maize (Zea mays L.) plants exposed to chilling stress can be improved by the application of
  protein hydrolysates. *Acta Agrobotanica*, 72(2), 1769. https://doi.org/10.5586/aa.1769
  — the strongest available evidence for the §1.4 claim that the researcher can measure plant stress
  physiologically rather than treat it as a spectral classification problem. It is the only one of
  her own works that is both peer-reviewed and carries a verified DOI. Abiotic stress in this paper
  is chilling rather than drought, which is worth stating plainly when §1.4 cites it.

Adding two entries takes the list from 33 to **35**, which is the ceiling of item 14's budget. If
you want headroom, R20 Reuss et al. (2025) is the weakest fit in the list and is the entry I would
drop first.

**Still not citable — DrR - Digital Agronomist.** This is now the whole of the residual flag. The
prototype is an unpublished desktop tool with no publication, preprint, software release, DOI or
repository. Neither the CV nor ORCID mentions it, and searches return nothing under that name.
§1.1.3 rests the project's preliminary-work claim entirely on it. Depositing it on Zenodo before
submission produces a citable DOI and converts §1.1.3 from an assertion into evidence; that remains
the recommendation. Otherwise §1.1.3 stands as an uncited first-person statement, which is legitimate
in a fellowship proposal but reads weaker.

**Two candidates worth adding once their status firms up.**

- Cholakova, R., Grozeva, S., Topalova, E., Ganeva, D., Tringovska, I., & Kamenova, I. (2025).
  Non-destructive evaluation of physiological status of drought-stressed tomato plants. Under
  review; no publication or preprint found. This is the single most on-point item in her record —
  the exact crop, the exact stress and non-destructive assessment — and it would strengthen §1.4
  more than anything else here. Add it the day it is accepted.
- Kamenova, I., Dimitrov, P., Ganeva, D., Cholakova, R., Filchev, L., Ivanov, I., Tringovska, I.,
  Ganeva, D., & Grozeva, S. (2026). UAV remote sensing of watermelon under different irrigation
  regimes: Non-parametric modelling of crop biophysical variables. Twelfth International Conference
  on Remote Sensing and Geoinformation of the Environment, Paphos. The title is confirmed as an
  accepted paper in the RSCy2026 abstract booklet, but the SPIE proceedings volume and page numbers
  are not published yet, so there is no complete citation to give. It evidences UAV remote sensing
  of irrigation treatments, which is the EO half of the §1.4 profile.

**Residual status.** Area 8 is Partially Resolved rather than Unresolved. Two of three strands are
cited; the DrR strand stays open pending your decision on depositing it. It blocks no gate. Ticket 7
should carry the DrR strand alone into the authorisation packet, not the whole item.

### Reserve, not counted in the 35

Six further entries from the review PDF are on-topic and were held back only to protect the page
budget. With the list now at 35, these are strictly swap-ins: bring one in only by dropping one out.

| Ref | Use |
|-----|-----|
| Fuentes-Peñailillo et al. (2025), *Agronomy*, https://doi.org/10.3390/agronomy15092122 | Remote sensing, agro-meteorology and wireless sensor networks combined for high-value fruit crops. Carries the up-to-30%-water-saving figure |
| Peeters et al. (2024), *Comput. Electron. Agric.*, 227, 109578, https://doi.org/10.1016/j.compag.2024.109578 | Spatial ML model predicting CWSI for precision irrigation of vineyards. Closest published parallel to the irrigation decision layer |
| Kapari et al. (2024), *Drones*, https://doi.org/10.3390/drones8020061 | ML algorithm comparison for CWSI from UAV data, with feature selection |
| Torres-Quezada et al. (2025), *Remote Sensing*, https://doi.org/10.3390/rs17040708 | Remote sensing plus soil-moisture sensors for orchard irrigation, for layer 1 |
| Katimbo et al. (2023), *Smart Agricultural Technology*, https://doi.org/10.1016/j.atech.2023.100176 | Sensor data assimilation for ET and CWSI estimation |
| Kamarudin et al. (2021), *Applied Sciences*, https://doi.org/10.3390/app11041403 | Deep-learning sensor fusion review, for the layer-6 note that deep architectures need justification |

---

## Item 11 — Researcher CV

Severity: High. No gate. Part B-2 §4 requires a CV of indicative length five pages, and the dates
must agree with Part A. This run does not draft Part B-2, so the CV feeds the in-scope §1.4 rather
than a drafted annexe. Lands in: `consortium/capabilities.json` and
`project_brief/strategic_positioning.md`.

### Draft basis

Section 1.4 describes the researcher's profile qualitatively. It names no publication, no date and
no institution.

### Answer

```
ITEM 11 — RESEARCHER CV

source: JRC_2026.pdf (Europass CV, supplied 2026-08-11) + ORCID 0009-0008-3761-3106
       + the PhD abstract published by Agricultural University – Plovdiv.

full_name: Rositsa Cholakova
  publishing name variant: Rositsa Cholakova-Bimbalova — used on every publication up to 2020,
  and on the PhD thesis. "Cholakova" is used from 2025. BOTH NAMES MUST APPEAR in Part A and in
  §1.4, or half her record looks like someone else's. See "Name variant" below.
orcid: 0009-0008-3761-3106
  ASSUMED, not confirmed. The record could not be read: pub.orcid.org blocks automated access,
  orcid.org needs JavaScript, and Crossref returns zero works carrying this ORCID. The iD came
  from your message, not from a source I could verify. Confirm it resolves to her.

phd_title: Response of maize (Zea mays L.) to low temperatures and the effectiveness of
  subsequent foliar fertilisation
  PARTIAL — English rendering of the Bulgarian original, and the copy I could read was
  truncated mid-phrase. Supply the exact Bulgarian title and its official English form.
phd_award_date: 2020-10-10   (doctoral studies 2014-11-15 to 2020-10-10)
phd_institution: Agricultural University – Plovdiv, Faculty of Agronomy,
  Department of Plant Physiology and Biochemistry. Doctoral programme: Plant Physiology.
  Professional field 6.1 Agronomy. EQF level 8, 291 ECTS.
phd_supervisor: Prof. Dr. Andon Vassilev

positions_held (role, organisation, from, to):
  Chief Assistant Professor, plant physiology researcher — Maritsa Vegetable Crops Research
    Institute (MVCRI), Agricultural Academy, Plovdiv, BG — 2024-10-15 to present
  Data Analyst — KPMG Global Hungary, Budapest, HU — 2024-06-01 to 2024-10-01
  Full-time parenting, career break — Budapest, HU — 2021-07-25 to 2024-05-31
  Assistant Professor in Plant Physiology and Plant Stress Physiology — Agricultural University,
    Plovdiv, BG — 2015-11-15 to 2020-10-20
  Agricultural Market Analyst — Kleffmann Group Bulgaria, Plovdiv, BG — 2013-06-03 to 2013-11-29

key_publications (at least five, with DOI):
  ONLY TWO OF NINE CARRY A DOI. The requirement is not met on DOIs, though it is met on count.
  See "Publications" below for the full list with per-item verification status.
  With DOI:
    Cholakova-Bimbalova, R., Petrov, V., & Vassilev, A. (2019). Acta Agrobotanica, 72(2), 1769.
      https://doi.org/10.5586/aa.1769
    Cholakova-Bimbalova, R., & Vassilev, A. (2017). CBU International Conference Proceedings, 5,
      1118–1123. https://doi.org/10.12955/cbup.v5.1081
  Without DOI, verified against the publisher: the two 2025 durum wheat papers and the 2015
    Scientific Works paper. Without DOI and unverified: four further items.

teaching_and_supervision:
  Agricultural University Plovdiv, 2015–2020: syllabus design, lectures and examinations in
  Bulgarian and English, including for Erasmus students. Supervised student research projects
  and Bachelor's theses. Specialist consultant to farmers on physiological monitoring and
  integrated plant protection.
  NOTE: this is a strong fit for the item-5 EI-06 teaching measure and the item-6 Career
  Development Plan teaching component. Both assumed she would need to build teaching experience;
  she already has five years of it. Consider raising the ambition of both.

projects_and_grants:
  MVCRI / Agricultural Academy (SAA), 2024–2026 — ZEMDKT 17, Task 7: resistance to abiotic
    stress, drought and salinity, in Solanum lycopersicum. DIRECTLY RELEVANT: this is the
    FIELDWISE crop and the FIELDWISE stress, already funded and running.
  National Science Fund (MES), 2025–ongoing — "Monitoring of vegetable crops in support of
    precision agriculture using satellite and unmanned aerial systems", contract KP-06-COST/2,
    with the Space Research and Technology Institute, Bulgarian Academy of Sciences.
  HORIZON-MSCA-2025-SE-01-01 Staff Exchanges, 2026–2030 — SolGenSys, tomato multi-stress
    tolerance.
  Agricultural University Plovdiv, 2016–2020 — project OA-17 (herbicide phytotoxicity,
    biostimulants) and project DN 16/8 (biostimulants for biocontrol under stress).

awards_and_fellowships:
  STSM awardee, COST Action CA22136 PANGEOS, at MATE, Hungary, 2025 — UAV multispectral and
    hyperspectral assessment of crop physiological status under abiotic stress.
  Erasmus+ staff mobility, three grants, MATE (HU) and University of Novi Sad (RS), 2025–2026 —
    UAV acquisition, hyperspectral imaging, field spectrometry, crop phenotyping.
  Erasmus PhD mobility, Russian State Agrarian University – Moscow Timiryazev Academy, 3 months,
    2018 — innovation in agriculture.
  Erasmus master's mobility internship, ELTE Budapest, 3 months, 2026 — remote sensing, precision
    agriculture, geoinformatics; satellite and UAV data analysis.
  UAV pilot licence A1/A3, Civil Aviation Administration Bulgaria, BGR-RP-t8drlyacolpq.
  COST Action member: CA22136 PANGEOS, CA22149 AI4Insect, CA22141 REcrop.
  Prior MSCA-PF submission: PLANTDIGISENSE, HORIZON-MSCA-2025-PF, proposal 101284764, host ELTE,
    scored 70.40% against a 70.00 threshold. See "The previous proposal" below.

invited_talks: NOT IN THE CV. Unresolved. Supply any, or confirm there are none.

career_breaks_or_gaps_to_explain:
  2021-07-25 to 2024-05-31, full-time parenting, in Budapest, Hungary. Just over 34 months.
  Declare it in Part A. It does not count against the research-experience ceiling.
  *** BUT IT MAY BREAK THE MOBILITY RULE. SEE "Eligibility flag" BELOW. READ THAT FIRST. ***

second_masters (not asked for, but it changes §1.4):
  MSc Environmental Engineering, Agricultural University Plovdiv, 2025-09-15 to 2026-05-31.
  Earlier: MSc Plant Protection (2013), BSc Plant Protection (2012), both AU Plovdiv.
```

### Eligibility flag — the mobility rule may not be satisfied

This is the most consequential thing in the CV and it is not a Part B-2 matter. **Raise it before
anything else in this pack is acted on.**

MSCA European Postdoctoral Fellowships require that the researcher *"must not have resided or
carried out their main activity (work, studies, or equivalent) in the country of the host
organisation for more than 12 months in the 36 months immediately before the call deadline."* The
host is ELTE, so the country is Hungary. Item 7 confirms the deadline as 2026-09-09, which makes the
reference window **2023-09-09 to 2026-09-09**.

What the CV places inside that window, all in Budapest:

| Period | Basis | Months in window |
|--------|-------|------------------|
| 2023-09-09 to 2024-05-31 | Full-time parenting, residing in Budapest | ≈ 8.7 |
| 2024-06-01 to 2024-10-01 | Data Analyst, KPMG Global Hungary | 4.0 |
| 2026, 3 months, exact dates not given | Erasmus master's mobility internship at ELTE | ≈ 3.0 |
| | **Total** | **≈ 15.7** |

Even discounting the ELTE internship entirely, the first two rows alone come to about **12.7
months**, which exceeds the cap by roughly three weeks.

Three things make this worth checking rather than assuming.

The exceptions are narrow. The work programme excludes compulsory national service, time spent in a
procedure for obtaining refugee status, and short stays such as holidays. Career breaks and parental
leave are excluded from the *eight-year research experience* ceiling — which is a different rule —
and I could not find them excluded from the *mobility* count. Confirm this against the 2026 work
programme text rather than against my reading of it.

Residence is what counts, not employment. The parenting period is not employment, but the rule says
"resided **or** carried out their main activity". If she was resident in Budapest throughout, it
counts. If her registered residence stayed in Bulgaria and the Budapest time was intermittent, the
arithmetic changes. Only she knows this.

The dates are the CV's, not a registry's. The KPMG end date of 2024-10-01 and the MVCRI start of
2024-10-15 are consistent with a move back to Plovdiv in October 2024, which is what puts the total
so close to the line. A few weeks either way decides it.

**What to do.** Establish her actual documented residence dates in Hungary across 2023-09-09 to
2026-09-09, then check the total against the 2026 work programme. If it exceeds 12 months, the
European Fellowship route with ELTE as host is not available and item 7's `FELLOWSHIP_TYPE`
confirmation is wrong. Options would then include a different host country, or a Global Fellowship
structure where the rule applies to the outgoing host. This is not something the run can seed
around — it invalidates the identity spine.

Until it is resolved, treat item 7's FELLOWSHIP_TYPE and HOST confirmations as provisional.

### Name variant

Every publication up to and including the 2020 thesis is under **Cholakova-Bimbalova**; everything
from 2025 is under **Cholakova**. Nothing in the record links the two names. Practical consequences:

- Part A must carry both, or the pre-2020 record does not attach to the applicant.
- §1.4 should state the change explicitly the first time it cites a pre-2020 work.
- ORCID 0009-0008-3761-3106 currently surfaces no Crossref-indexed works at all. Claiming her
  publications on the ORCID record before submission is cheap and makes the whole record findable
  under one identifier. Recommended.

### Publications, with verification status

Nine items, in date order. Verification means the title, authors, venue and pages were read from the
publisher or the institution, not from the CV.

| # | Publication | Status |
|---|-------------|--------|
| P1 | Cholakova-Bimbalova, R., & Vassilev, A. (2015). Influence of low temperatures on the growth and macronutrient content in young maize plants. *Scientific Works, Agricultural University – Plovdiv*, LIX(2), 87–94 | VERIFIED against the AU-Plovdiv PDF. No DOI |
| P2 | Cholakova-Bimbalova, R. (2017). Influence of foliar fertilizer and its components on the tolerance of young corn plants experienced low temperatures. *Scientific works of the Institute of Agriculture Karnobat*, 54–59 | UNVERIFIED. The institute's online archive stops at 2014. No DOI |
| P3 | Cholakova-Bimbalova, R., & Vassilev, A. (2017). Effect of chilling stress on the photosynthetic performance of young plants from two maize (Zea mays L.) hybrids. *CBU International Conference Proceedings*, 5, 1118–1123 | VERIFIED. **DOI 10.12955/cbup.v5.1081**. The CV omits this DOI |
| P4 | Cholakova-Bimbalova, R., Koleva, L., & Vassilev, A. (2018). Effects of a biostimulant and a mineral fertilizer on the antioxidative defence system of chilling-exposed maize plants. *Agricultural Sciences*, 33–39 | UNVERIFIED. Not locatable on the journal site or CABI. No DOI |
| P5 | Cholakova-Bimbalova, R., Petrov, V., & Vassilev, A. (2019). Photosynthetic performance of young maize (Zea mays L.) plants exposed to chilling stress can be improved by the application of protein hydrolysates. *Acta Agrobotanica*, 72(2), 1769 | VERIFIED. **DOI 10.5586/aa.1769**. Her strongest single publication and the only DOI-bearing journal article. Cited as R35 in item 10 |
| P6 | Cholakova-Bimbalova, R. (2020). Changes in the growth and antioxidant enzyme activity of seedlings originating from wheat seeds subjected to accelerated ageing test | UNVERIFIED. **The CV names no journal at all** and the entry reads "Write here the description...". Supply the venue |
| P7 | Dragov, R., Taneva, K., Hadzhiivanova, B., Videva, M., Todorova, B., & Cholakova, R. (2025). Genetic nature of quantitative traits in durum wheat. *Scientific Papers. Series A. Agronomy*, LXVIII(1), 320–326 | VERIFIED against the publisher PDF. No DOI. WOS:001598862000037 could not be checked |
| P8 | Dragov, R., Taneva, K., Hadzhiivanova, B., Videva, M., Todorova, B., & Cholakova, R. (2025). Graphical diallel analysis for quantitative traits in durum wheat. *Scientific Papers. Series A. Agronomy*, LXVIII(2), 382–391 | **CORRECTED: the CV dates this 2026. It is Vol. LXVIII No. 2, 2025.** Fix it before Part A, where dates must agree |
| P9 | Kamenova, I., Dimitrov, P., Ganeva, D., & Cholakova, R. (2025). Remote sensing monitoring of watermelon under different water regimes: methodology and preliminary results. *Proceedings of SES 2025*, Sofia | UNVERIFIED. The proceedings site is HTTP-only and could not be reached. No DOI |

Two further items are in the pipeline rather than published, and are handled in the amended area 8
flag of item 10: the drought-stressed tomato paper (under review, no preprint found) and the
RSCy2026 watermelon UAV paper (title confirmed as accepted, proceedings volume not yet issued).

**The honest summary for §1.4.** Nine items, of which two carry a DOI, four are publisher-verified
without one, and three could not be verified at all. Only three touch remote sensing, and all three
are 2025 or later with her as a middle author. The EO half of the §1.4 profile rests on the STSM,
the Erasmus mobilities and the UAV licence rather than on publications — which is a defensible story
for a career-transition fellowship, but §1.4 should tell it that way rather than implying an
established EO publication record.

### The previous proposal — PLANTDIGISENSE

The CV names it: HORIZON-MSCA-2025-PF, proposal 101284764, acronym PLANTDIGISENSE, host ELTE, total
score **70.40%** against a 70.00 threshold. This is the proposal whose evaluator criticism the draft
answers in three separate places — §1.2.1 on heterogeneous data treatment, §2.2 on the route to
users and IP, and the §3.1 note on late milestones.

Two things follow.

The margin matters to the strategy. 70.40 against a 70.00 threshold means it passed the quality bar
and lost on ranking, not on substance. FIELDWISE is therefore a resubmission that needs to move a
score, not repair a failure. If the Evaluation Summary Report exists, it is the single most valuable
input to Phase 8 drafting that this pack has not asked for. Consider adding it to Tier 3 source
materials.

It also confirms a fact the pack had recorded only as draft-derived: the ELTE host relationship and
the supervisor arrangement predate FIELDWISE. Item 7's HOST and SUPERVISOR confirmations are on
firmer ground than the draft alone made them look — subject entirely to the eligibility flag above.

### Consistency checks against the rest of the pack

- Item 7 FELLOW record: **confirmed** on every field. Rositsa Cholakova, plant physiologist, MVCRI
  Plovdiv, PhD 2020. Her title is Chief Assistant Professor, which §1.4 and Part A should use.
- Item 1 MVCRI contact and item 4 TRANSFER_PARTNER contact are both given as Dr. Rositsa Cholakova —
  the fellow herself. That is the independence problem item 2 already raises, now concrete: the
  fellow would be the named contact for the partner that provides the independent cross-country
  test, and a member of its steering group seat. Name a different MVCRI contact, and state the
  separation explicitly in §1.2.
- Item 6 Career Development Plan and item 5 EI-06 both assume teaching is a competence to be built.
  Five years of university teaching and thesis supervision says otherwise. Revisit both.
- Item 12 will need her MVCRI department and the ZEMDKT 17 and KP-06-COST/2 projects; they are the
  strongest capacity evidence available for MVCRI and they come from this CV.

---

## Item 12 — Host and participant capacity descriptions

Severity: High. No gate. Part B-1 §3.2 is in scope for this run and needs hosting arrangements and
capacity. Part B-2 §5 needs one table per organisation, at most one page for the beneficiary and
half a page for each associated partner. Lands in: `consortium/capabilities.json`.

### Draft basis

Section 3.2 gives one function sentence per organisation. That is enough to state a role and not
enough to demonstrate capacity.

### What is needed

Per organisation, and additionally for ELTE the hosting arrangements that §3.2 requires.

- Department or institute, and the size and composition of the hosting team.
- Infrastructure and facilities relevant to the work packages, including instruments, field sites
  and computing.
- Key people, with role in the project.
- Relevant recent projects and publications.
- Previous MSCA hosting experience.
- For ELTE only: integration into the team, office and laboratory access, administrative and career
  support services, and the mentoring structure.

### Answer

```
ITEM 12 — CAPACITY

ELTE (beneficiary)
  department_and_team: Faculty of Informatics
  infrastructure: drones, satelite access (hyerpsetcral, multispectral), claude storage, computing infrastructure for machine learing   
  key_people: Dr. András Jung
  recent_projects_and_publications:
  previous_msca_hosting:
  hosting_arrangements_and_support_services:

MATE
  department_and_team:  Institute of Horticultural Sciences
  infrastructure: field trials, source-domain scientific dataset and primary model-development/validation environment
  key_people: Dr. Sándor Takács
  recent_projects_and_publications:

MVCRI
  department_and_team:
  infrastructure: secondary access to field trials
  key_people: 
  recent_projects_and_publications:

AgroVIR
  organisation_profile:
  infrastructure_and_farm_access: network access, MCP validaation via the agrovir software
  key_people: 
  relevant_track_record:
```

---

## Item 13 — Security screening and Green Charter statements

Severity: Medium. No gate. Part B-2 §7 and §8. This run does not draft Part B-2, so both statements
are held in Tier 3 for the submission rather than consumed by a phase. Lands in:
`call_binding/confirmation_checklist.json`.

### Draft basis

Nothing for §7. Section 1.2 supplies real material for §8 without naming the Green Charter.

### Candidate

Security screening, §7. No concerns arise. The project handles no classified or EU-restricted
information. It uses open Copernicus data and institutional field measurements. It involves no
dual-use goods or technology and no entity established outside the EU.

Green Charter, §8. Six commitments, four of which the draft already supports.

| Commitment | Basis |
|------------|-------|
| Reuse before regeneration: the five-year MATE archive is the primary data source rather than a new campaign | Draft §1.2 layer 1 |
| Prefer the simplest adequate model, and introduce deep architectures only where sample size and temporal density justify them | Draft §1.2 layer 6 |
| Run computation on shared ELTE infrastructure rather than provisioning dedicated hardware | New |
| Travel: default to remote collaboration, with at most one physical visit to MVCRI per growing season and shared transport for field campaigns | New |
| Conferences: hybrid attendance by default, at most one in-person conference per year | New |
| Purpose: the project targets better irrigation timing, which serves the Charter's environmental aim directly | Draft §2.3 |

### Answer

```
ITEM 13 — SECURITY SCREENING AND GREEN CHARTER

security_screening statement:  ACCEPT 
green_charter commitments:     ACCEPT 
edits:
```

---

## Item 14 — Page-limit decision

Severity: Medium. No gate. Part B-1 sections 1, 2 and 3 together are capped at 10 pages, and all
tables, figures and references count toward that cap. Lands in:
`call_binding/confirmation_checklist.json`, read by the Phase 8 drafting skills.

### A correction to the plan

Plan §4 states that the draft exceeds the 10-page limit. Measured, it does not. Sections 1 to 3 of
the draft total about 3,800 words including all four tables, which is roughly five to six pages at
normal MSCA formatting. The draft is under the cap, not over it.

The reason is that the draft is a skeleton. It carries no citations, no figures, an empty §1.1.8
body under its objectives table, and thin §1.4 and §3.2 sections. Phase 8 drafting expands it, item
10 adds references that count toward the cap, and item 12 fills §3.2. The real decision is how to
allocate the remaining space, not what to cut.

### Candidate

A page budget per section, weighted toward the criteria weights of 50%, 30% and 20%.

| Section | Pages | Criterion share |
|---------|-------|-----------------|
| 1.1 Objectives, gaps, questions, ambition, references | 2.25 | Excellence, 57.5% total |
| 1.2 Methodology, including the Gantt-independent method figure | 2.25 | |
| 1.3 Supervision, training, two-way transfer | 0.75 | |
| 1.4 Researcher experience | 0.50 | |
| 2.1 Career perspectives | 0.75 | Impact, 22.5% total |
| 2.2 Dissemination, exploitation, communication | 0.75 | |
| 2.3 Expected impacts | 0.75 | |
| 3.1 Work plan, Gantt, risks, effort | 1.50 | Implementation, 20% total |
| 3.2 Capacity and hosting arrangements | 0.50 | |
| Total | 10.00 | |

Two consequences of this budget. The reference list of item 10 must fit inside the 1.1 and 1.2
allocation, which caps it at roughly 25 to 35 entries. The 13-row risk table and the Gantt figure
must fit inside §3.1's 1.5 pages, so the risk table is likely to compress to a grouped form.

### Answer

```
ITEM 14 — PAGE BUDGET

page budget as drafted:  ACCEPT / replace with:
edits:

if you disagree that the draft is under the cap, state what you measured:
```

---

## What this pack does not cover

Three things sit outside the fourteen items and will surface later.

Ticket 4 seeds `outcomes.json` by separating project outputs from outcomes, marked Inferred. You
review that separation in the authorisation packet, not here.

Ticket 11 decides what happens to the E4 golden-set regression lane once FIELDWISE Tier 5 exists.
Ticket 12 decides when the Obsidian vault is re-authored. Both are recorded as open questions 4 and
5 of the plan.

The `graph_claim_verifier` audit stays red until ticket 12 completes. That is a known and logged
§12.3 contradiction, not a new gap.
