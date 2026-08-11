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

Completed 2026-08-11 from public registers and CORDIS. Operator-supplied values are kept and
marked. [V] verified against a source named below. [O] operator-supplied, not independently
verified. [!] needs your action. [!!] blocks something.

MATE
  legal_name_national:  Magyar Agrár- és Élettudományi Egyetem                              [V]
  legal_name_english:   Hungarian University of Agriculture and Life Sciences                [V]
    EU grant spelling as recorded in CORDIS: MAGYAR AGRAR- ES ELETTUDOMANYI EGYETEM
  pic: 891269563                                                                             [V]
    Confirmed: MATE coordinates AGRIGEP, grant 101094158, recorded under this PIC.
  entity_type:  Higher education institution. Public-benefit (közhasznú) private non-profit
    since the 2021 model change, maintained by Magyar Agrár- és Élettudományi Egyetemért
    Alapítvány. Legal successor of Szent István Egyetem from 2021-02-01. In Horizon terms:
    Higher or Secondary Education Establishment, non-profit.                                 [V]
    [!] The public/private flag is the one field to check with MATE's grants office. The
        foundation model makes Hungarian universities private in form and public in function;
        the Part A entry must match how MATE already self-declares in the Register.
  address_street:   Páter Károly utca 1                                                      [V]
  address_city:     Gödöllő                                                                  [V]
  address_postcode: 2100                                                                     [V]
  address_country_code: HU                                                                   [V]
  contact_person: Dr. Sándor Takács                                                          [O]
  contact_email:  tak5533@uni-mate.hu                                                        [O]
    [!] Role and institute not verified. Item 12 places him in the Institute of Horticultural
        Sciences. Supply his exact title: Part B-2 §5 needs it and g07_p08 reads the name.
  already_registered_in_participant_register: yes — the PIC proves it                        [V]
  letter_of_commitment: planned                                                              [O]

MVCRI
  legal_name_national:  Институт по зеленчукови култури „Марица“ – Пловдив                   [V]
  legal_name_english:   Maritsa Vegetable Crops Research Institute                           [V]
    EU grant spelling as recorded in CORDIS: MARITSA VEGETABLE CROPS RESEARCH INSTITUTE
  pic: 999533009                                                                             [V]
    Confirmed, and it belongs to the institute itself rather than to the Agricultural Academy.
    MVCRI coordinated FP7 project 205941 under this PIC, in its own name.
  entity_type:  Public research organisation, non-profit, not a higher education institution.
    A scientific institute of Селскостопанска академия, the Agricultural Academy, which sits
    under the Minister of Agriculture.                                                       [V]
    [!] Holding its own PIC and having coordinated an EU project in its own name settles this
        for Register purposes. It does not settle who signs. Ask MVCRI whether the institute
        director signs a partnership agreement or whether the Academy must. Institutes of the
        Academy are structural units, so this can go either way, and it is far cheaper to ask
        now than at grant preparation.
  address_street:   32 Brezovsko shose St. (ул. „Брезовско шосе“ 32)                         [V]
  address_city:     Plovdiv                                                                  [V]
  address_postcode: 4003                                                                     [V]
  address_country_code: BG                                                                   [V]
  contact_person: Prof. Vinelina Yankova, PhD                                                    [!!]
  contact_email:  vinelina@abv.bg                                              [!!]
    C1 RESOLVED IN STRUCTURE, 2026-08-11 — operator chose "name another MVCRI colleague".
    Dr. Rositsa Cholakova is REMOVED from this field. She is the FELLOW, and naming her as
    the transfer partner's contact made the independent cross-country test answerable to the
    person whose model it tests.
    ONE NAME STILL NEEDED. Supply it once and it fills both this field and item 4's
    TRANSFER_PARTNER seat — the same token `<<MVCRI_COLLEAGUE>>` marks both.
    Candidates visible from her co-authorships, roles unconfirmed: Stanislava Grozeva,
    Ivanka Tringovska, Daniela Ganeva, Elena Topalova. The institute director would be the
    conventional choice for a partner contact; a head of department is equally acceptable.
    [!] Use an institutional address if one exists. Worth knowing: MVCRI appears to have no
        institutional mail domain — its own published addresses are izk_maritsa@abv.bg and
        seme_izk@abv.bg, both on the free provider abv.bg. So a free-provider address is
        normal here and is not a problem in itself. The problem was only whose it was.
  already_registered_in_participant_register: yes — the PIC proves it                        [V]
  letter_of_commitment: planned                                                              [O]

AgroVIR
  legal_name_national:  AGROVIR Üzletviteli Tanácsadó Korlátolt Felelősségű Társaság         [V]
    short form: AGROVIR Kft.
  legal_name_english:   AgroVIR Business Consulting Ltd.                                     [V]
  pic: none                                                                                  [!!]
    MUST BE CREATED BEFORE SUBMISSION. See "What item 1 still blocks" below.
  entity_type:  Private for-profit company, limited liability (Kft.). SME. Founded 2007.
    Main activity NACE 7020, business and management consulting.                             [V]
    [!] SME status is inferred from the published revenue band, not from a self-assessment.
        Run the official SME self-assessment before Part A.
  address_street:   Kinizsi utca 30                                                          [V]
  address_city:     Budaörs                                                                  [V]
  address_postcode: 2040                                                                     [V]
  address_country_code: HU                                                                   [V]
    [!!] CORRECTION. The form said Budapest. The registered seat is 2040 Budaörs, Kinizsi utca
         30 — a separate town in Pest county, not a Budapest district. The tax number ends in
         the Pest county code, which corroborates it. Budaörs is about 15 km from central
         Budapest, so nothing in the work plan changes; only the address in Part A and
         Part B-2 §5 does.
  tax_number (adószám): 14000838-2-13                                                        [V]
  company_registration_number (cégjegyzékszám):  NOT VERIFIED                                [!]
    One source implies 01-09-884056, but the tax number's county code points to Pest, which
    would give a 13- prefix. Do not use either until the company confirms it.
  contact_person: Balázs Zsuzsanna                                                           [O]
  contact_email:  balazs.zsuzsanna@agrovir.hu                                                [O]
    [!] Role not verified — the company website names no staff. Supply her title.
  already_registered_in_participant_register: no                                             [O]
  letter_of_commitment: none                                                                 [!!]
    "None" is a problem here, not a neutral answer. See below.
```

### Sources for the verified fields

- MATE legal name, address and PIC 891269563 — CORDIS grant 101094158 (AGRIGEP), MATE as
  coordinator: https://cordis.europa.eu/project/id/101094158
- MATE seat, foundation maintenance, successor status — the university's own published economic
  information: https://uni-mate.hu/gazd%C3%A1lkod%C3%A1si-inform%C3%A1ci%C3%B3k
- MVCRI legal name, address and PIC 999533009 — CORDIS FP7 grant 205941, MVCRI as coordinator:
  https://cordis.europa.eu/project/id/205941 and http://izk-maritsa.org/en/contact-us/
- AgroVIR legal name, seat, tax number, activity code, founding year — Hungarian company register
  extract via OPTEN: https://webshop.opten.hu/agrovir-kft-c0109884056.html ; scale and product:
  https://www.agrovir.com/HU/rolunk.html

### What item 1 still blocks

`phase_03_gate` predicate `g04_p07` requires every work-package-assigned partner to exist in
`consortium/partners.json`. MATE and MVCRI now resolve completely — verified legal name, verified
PIC, verified address. They will pass.

**AgroVIR will not.** It has no PIC and no letter of commitment, and the draft makes it WP5 co-lead.
Three consequences, in the order they bite.

The PIC is the easy one. Registering in the Participant Register is free, takes minutes, and needs
only the legal name, address and tax number — all three of which are now filled in above. Nothing
blocks doing it today. Until it exists, `partners.json` carries an Unresolved record for a partner
the work plan assigns a work package to, and `g04_p07` fails on it.

The letter is harder, and it interacts with item 2. If AgroVIR becomes a **non-academic placement
host**, constraint CC-09 requires the placement to be integral to the proposal, and it is
*evaluated*. A placement host that has given no letter of commitment is the weakest possible version
of that, and evaluators read it as an arrangement that may not exist. As an **associated partner**
or **secondment host** a letter is still expected, but the exposure is smaller. Decide item 2 and
you will know how hard to push.

The third is quieter, and it is contradiction C9.

**C9 RESOLVED 2026-08-11 — by narrative, since the fact itself is not wrong.** AgroVIR's registered
activity code is 7020, business and management consulting, and its registered name is AGROVIR
Üzletviteli Tanácsadó Kft. — literally "business consulting Ltd". The company plainly does build and
operate a farm management information system. Both things are true: Hungarian companies commonly
keep a founding NACE code that no longer describes what they do, and nothing needs correcting at the
registry. The contradiction is only in what an evaluator infers.

The exposure grew when the placement was approved. An evaluator now reads Part A, sees a business
consultancy, and turns to a Part B-1 that asks them to accept it as both the operational technology
partner and a six-month non-academic placement host. Left unaddressed, the registered activity is
the first thing that contradicts the narrative.

Adopted approach — state it, do not let the code speak first. Wherever AgroVIR is introduced, in
§3.2 and Part B-2 §5, lead with what it operates rather than how it is registered:

  "AgroVIR (AGROVIR Üzletviteli Tanácsadó Kft., founded 2007, Budaörs, Hungary) develops and
  operates a cloud-based farm management information system in production use across more than
  745,000 hectares in eight countries — Hungary (500,000+ ha), Romania (120,000+), Azerbaijan
  (50,000+), Slovakia (40,000+), Bulgaria (15,000+), Serbia (10,000+), Ukraine (7,000+) and
  Argentina (3,000+). Its Hungarian and Bulgarian footprints correspond to the two countries in
  which FIELDWISE operates. The company is registered under NACE 7020 (business and management
  consulting), reflecting its founding activity; its current business is agricultural software."

That last sentence is the whole fix: name the discrepancy in one clause instead of leaving the
evaluator to find it. The hectare figures come from the company's own published material.

[!] Two things this wording depends on, both still open: a letter of commitment (which the
    placement decision made load-bearing), and a named on-site supervisor for M25–M30. The
    narrative above describes a substantial company; it does not yet evidence a hosting
    arrangement.

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
AgroVIR:  non_academic_placement          <-- DECIDED by the operator, 2026-08-11
  if non_academic_placement, months added at the end: 6

Total action duration after this decision (months):  30

Statement on MVCRI independence given the fellow's current affiliation:

--- DECISION RECORDED 2026-08-11 -------------------------------------------------
RESOLVED. AgroVIR is the non-academic placement host. Six months are added at the end
of the action. The action runs 30 months: M1–M24 at ELTE, M25–M30 on placement at
AgroVIR. My earlier recommendation of a 24-month secondment is superseded; it is struck
through below and kept only so the reasoning is on the record.

This is now the settled duration everywhere in the pack. Items 7, 8, 9, 12 and 14 have
been consolidated to 30 months. The contradiction with item 9 is closed.

WHAT THE DECISION BUYS. The placement is the operational-transfer half of the proposal
made structural rather than asserted. G5 and H5 both claim that research-to-farm transfer
is where models break; a six-month period embedded in the company that runs the farms is
the strongest available evidence that the proposal takes its own gap seriously. It also
answers the previous evaluation's criticism, recorded in §2.2, that the economic and
technological route to users was insufficiently substantiated. A resubmission that moved
from 70.40% needs exactly this kind of structural answer.

WHAT IT COSTS, and all of it is now live work.

  1. The placement is EVALUATED. Confirmed against the 2026 Guide for Applicants: the
     non-academic placement "should be described in part B-1 and the evaluators will
     assess their relevance and quality in the respective criterion". It is no longer
     enough for AgroVIR to appear in the work plan — Part B-1 must argue the placement:
     what the fellow does in M25–M30, why it needs six months, why it needs to be inside
     the company, and what the fellow gains that ELTE cannot give her. Nothing in the
     current draft does this. It is new §1.2/§1.3/§3.1 content for Phase 8.
  2. Part A needs a separate budget line. The Guide is explicit: add the number of months
     requested for the non-academic placement as a separate line in Part A Section 3.
  3. AgroVIR's letter of commitment moves from "nice to have" to load-bearing. An
     evaluated placement resting on a host that has provided no letter is the weakest
     version of this decision. See item 1 — this is now the most urgent open action in
     the pack after the mobility flag.
  4. Location is fine. The placement organisation must be in an EU Member State or
     Associated Country; the Guide does not prohibit the same country as the beneficiary.
     AgroVIR in Budaörs, Hungary, is eligible. Confirmed, no action needed.
  5. CC-07's six-month ceiling is used in full. There is no headroom left if the plan
     later needs a seventh month.

  ~~Recommendation: secondment_host, 24 months total.~~ SUPERSEDED 2026-08-11.
  ~~Reasons were: CC-09 makes a placement evaluated while AgroVIR has no letter; the +6
  months churns every downstream number; the draft did not argue for the extra months;
  CC-04 already allows up to 12 secondment months.~~ The operator has weighed these and
  accepted the placement. Reasons 1 and 3 above are the residual work those objections
  point at, and they are now tracked rather than avoided.
----------------------------------------------------------------------------------

Statement on MVCRI independence — DRAFTED, accept or replace:
  "MVCRI is the fellow's employer of record at the time of application. The Bulgarian
  evaluation is nonetheless independent of model development in the sense that matters
  scientifically: the Hungary-to-Bulgaria transfer test in WP4 is a zero-shot evaluation
  against data MVCRI holds and the fellow does not use in training, executed against a
  frozen model and a pre-registered evaluation protocol agreed before the Bulgarian data
  are opened. Model development occurs entirely at ELTE on MATE source-domain data. To
  keep the separation visible rather than asserted, MVCRI's project contact and steering
  group seat are held by a named MVCRI colleague other than the fellow, and the WP4
  evaluation split manifest is published under the open-science commitments of §1.2."
  [✓] C1 RESOLVED 2026-08-11. That last sentence is now true in structure: the fellow has
      been removed from item 1's MVCRI contact field and item 4's TRANSFER_PARTNER seat,
      both of which now carry `<<MVCRI_COLLEAGUE>>`. It becomes true in fact when you supply
      the name. The statement above can be adopted as drafted.
  [!] One addition the placement decision forces: WP4's Bulgarian transfer test must
      complete before the placement begins at M25, or the fellow is evaluating the
      Hungary-to-Bulgaria transfer from inside a Hungarian commercial software company.
      WP4 currently runs M12–M21, so this holds — but state it, because the sequencing
      is now part of the independence argument rather than an accident of the Gantt.
----------------------------------------------------------------------------------
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
ethics_committee_approval_required: not_yet_determined     <-- C2, amended 2026-08-11
ELTE data protection officer consulted: planned            <-- C2, amended 2026-08-11

--- C2 RESOLVED 2026-08-11 -------------------------------------------------------
Operator chose "soften both answers". `g07_p06` passes and the internal contradiction is
gone. The two amended lines carry the following reasons, which Phase 6 should write into
`ethics_assessment.self_assessment_statement` rather than leaving as bare tokens.

  ethics_committee_approval_required: not_yet_determined
    "ELTE's research ethics committee will be consulted on task T5.6 before any fieldwork
    begins. The expectation is that structured usability feedback from AgroVIR staff and
    participating farmers, collected under informed consent with a right of withdrawal and
    with no health, biometric or special-category data, falls below the committee's review
    threshold. This will be confirmed in writing by M12."

  ELTE data protection officer consulted: planned
    "ELTE's Data Protection Officer will be consulted before the first DrR Web MVP user
    account is created, covering the lawful basis for holding farm contact details and
    field boundaries, the retention period, and data minimisation across the MVP."

What this fixed. You had accepted `personal_data_gdpr: yes, limited` and
`human_participants: yes, low risk`, and the GDPR candidate's own text says "ELTE's Data
Protection Officer reviews the processing" — so answering "no DPO consulted" made the form
contradict the text it had adopted. An evaluator reads that as an ethics section written
without reference to its own commitments. Both amendments cost nothing at gate.

[!] One consequence to carry: `ethics_issues_identified` remains true, so Part A's ethics
    self-assessment table and Part B-2 §6 must both be completed. Unchanged by this edit,
    but it follows from the candidates you accepted rather than from these two lines.
----------------------------------------------------------------------------------
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
  TRANSFER_PARTNER (MVCRI): Vinelina Yankova         
  VALIDATION_PARTNER (AgroVIR): Zsuzsanna Balázs

--- sweep 2026-08-11 -------------------------------------------------------------
Complete. `g07_p07` passes on the accepted Steering Group. `g07_p08` will pass once the
three names resolve to partners in `partners.json`, which item 1 now makes possible for
MATE and MVCRI and not yet for AgroVIR.

[✓] C1 RESOLVED IN STRUCTURE, 2026-08-11. The fellow is removed from the TRANSFER_PARTNER
    seat. She previously sat on the Steering Group twice — once as FELLOW and once as the
    transfer partner's representative — on a body that issues go/no-go verdicts on MS1–MS5.
    The same `<<MVCRI_COLLEAGUE>>` name fills item 1's contact field; supply it once.

[✓] The knock-on is fixed by the same change. The accepted decision-rights table routes
    "access to partner data and field sites" to "the owning partner", escalating to the
    Steering Group. With the fellow holding MVCRI's seat she owned, escalated and voted.
    With a colleague in the seat, the escalation is genuine.

[✓] C6 RESOLVED 2026-08-11. The accepted conflict-resolution route escalates past the
    SUPERVISOR to "the ELTE Institute of Cartography and Geoinformatics head" — but the
    supervisor IS the deputy head of that institute, so the route partly looped back on the
    person being escalated past. The head is a different person and the route is sound once
    named.

      Head of Institute: Dr. Mátyás Gede, habil. associate professor, Director of the
      Institute of Cartography and Geoinformatics, ELTE Faculty of Informatics,
      H-1117 Budapest, Pázmány Péter sétány 1/C.
      Verified: https://www.inf.elte.hu/en/units/institute-of-cartography-science-and-geoinformatics

    Corrected escalation, replacing the accepted text's second step:
      "FELLOW and SUPERVISOR resolve disagreements directly and record the outcome in the
      monthly progress record. Anything unresolved after one cycle goes to the Director of
      the Institute of Cartography and Geoinformatics (Dr. Mátyás Gede), and then to the
      ELTE research integrity route. Data access disputes follow the dispute clause of the
      relevant data-sharing agreement."

    [!] One caveat worth carrying. ELTE lists Dr. Jung's deputy directorship as *temporary*.
        If he ceases to be deputy director during a 30-month action the escalation route is
        unaffected — it names the Director by office — but item 12's §3.2 text should
        describe him by his professorship rather than by a temporary administrative post.
----------------------------------------------------------------------------------
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
EI-04 Charter alignment measure:  ACCEPT, WITH THE HRS4R CLAIM REMOVED  <-- C8, 2026-08-11
  does ELTE hold HR Excellence in Research? unknown — claim dropped, see C8 below
EI-06 teaching measure:           RAISED, see C7 below                  <-- C7, 2026-08-11

--- sweep 2026-08-11 -------------------------------------------------------------
Complete enough for `g06_p04` — all six expected impacts now map to an output. `g06_p05`
passes on the ten KPIs, each of which names a deliverable.

[✓] C8 RESOLVED 2026-08-11 by removing the claim rather than by verifying it. Two rounds of
    checking failed: the EURAXESS acknowledged-institutions list is robots-blocked to
    automated access, targeted searches of elte.hu and euraxess.ec.europa.eu returned
    nothing either way, and https://www.elte.hu/en/hrs4r returns 404. That last point is
    weak evidence rather than proof — institutions holding the award usually publish a page
    — but it is not evidence of absence and I am not asserting ELTE lacks it.

    The contradiction was internal: the accepted EI-04 candidate asserts "ELTE's HR
    Excellence in Research status ... stated in §3.2" while the answer line to its immediate
    right says "unknown". A proposal cannot both claim the status and record not knowing it.

    ADOPTED EI-04 WORDING, which does not depend on the answer:
      "Charter alignment is evidenced at instrument level by the Career Development Plan
      (D1.3), by ELTE's open recruitment and researcher-development policies, and by the
      supervision and training arrangements set out in §1.3."

    The asymmetry decides it: if ELTE does hold the award, adding one sentence later costs
    nothing; if it does not, the original wording puts a false institutional claim into a
    submitted proposal. One email to ELTE's HR or research office settles it — restore the
    stronger claim the moment they confirm, and not before.

[✓] C1 knock-on RESOLVED 2026-08-11. K5 "cross-country gap quantified" and K6 "adaptation
    cost stated" both trace to D4.2/D4.3 in WP4, whose target domain is MVCRI. While the
    fellow held MVCRI's contact and steering seat, these two KPIs were measured by her
    against her own employer's data with no third party in the loop. With
    `<<MVCRI_COLLEAGUE>>` in both seats, K5 and K6 are reported to someone at MVCRI who is
    not their author. No change to the KPI wording is needed — only to who receives it.

[!] Item 6's D1.3 Career Development Plan carries no KPI. Item 6 accepted it as a
    deliverable, so the KPI list is now one short of covering every deliverable it claims
    traceability to. Consider K11: "Career Development Plan agreed by M3 and reviewed at all
    four steering points" → D1.3.

--- C7 RESOLVED 2026-08-11: teaching ambition raised -------------------------------
Operator chose "raise the ambition". The contradiction was that items 5 and 6 treated
teaching as a competence the fellowship would build, while the CV shows five years of it at
Agricultural University Plovdiv, 2015–2020: syllabus design, lecturing and examining in
Bulgarian and English including for Erasmus students, and Bachelor's thesis supervision.

REPLACES the EI-06 candidate ("one guest module in an ELTE MSc course, and co-supervision
of one MSc thesis"):

  EI-06 teaching measure — raised:
    • Co-design and deliver a full module unit within an ELTE MSc course on Earth
      observation for agriculture, rather than a single guest lecture.
    • PRIMARY-supervise one ELTE MSc thesis to completion.
    • Co-supervise the field-experiment component of one PhD student's work.

  Corresponding change to item 6's Career Development Plan, "Teaching" component: it is
  reframed from a competence to acquire into an existing strength transferred into a new
  discipline, a new institution and a new language of instruction. The developmental content
  is real but different — moving from plant protection teaching in Bulgarian at a Bulgarian
  agricultural university to Earth-observation teaching in English at a Hungarian
  informatics faculty, and stepping up from Bachelor's to Master's and doctoral supervision.

Why this is worth the extra commitment. §1.4 states the intended progression ending at
"independent researcher". Primary supervision and module ownership are the standard
evidence of that step; guest lecturing is not. The raised version turns EI-06 from the
weakest of the three added impact measures into support for the career argument §2.1 is
scored on.

[!] Two consequences to carry.
    • The workload lands in a 30-month plan whose cross-cutting allocation is 3.0
      person-months. Supervising a thesis to completion and co-designing a module unit will
      not fit inside that comfortably. Either raise cross-cutting, or state in §3.1 that
      teaching sits within the training allocation rather than the research WPs.
    • Primary supervision of an ELTE MSc thesis may require a formal ELTE affiliation or
      status the fellow will not automatically hold. Confirm with the Faculty of Informatics
      that an MSCA fellow can act as primary supervisor; if not, the measure drops back to
      co-supervision and the module unit carries the ambition instead.
----------------------------------------------------------------------------------
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
HOST:                 CONFIRM — CONDITIONAL on C5        <-- amended 2026-08-11
SUPERVISOR:           CONFIRM — corroborated, see below  <-- amended 2026-08-11
VALIDATION_PARTNER:   CONFIRM 
FELLOWSHIP_TYPE:      CONFIRM — CONDITIONAL on C5        <-- amended 2026-08-11
DURATION:             CONFIRM   <-- AMENDED, see below
CALL_BINDING:         CONFIRM 

DATA_PROVIDERS record is superseded by the draft:  CONFIRM 
RQ1 to RQ10 decisions are superseded by the draft: CONFIRM 

--- consolidated 2026-08-11 ------------------------------------------------------
[!!] DURATION IS NO LONGER 24 MONTHS. The pre-purge record you confirmed reads
     "24 months, carried in `selected_call.json` as `project_duration_months`". Item 2's
     placement decision makes the action 30 months. The confirmation stands on the
     principle — the duration record does carry forward and does live in
     `selected_call.json` — but the value is now wrong.

     Corrected record:
       DURATION: 30 months. 24 months of European Fellowship at ELTE (M1–M24) plus a
       6-month non-academic placement at AgroVIR (M25–M30) under CC-07.
       `selected_call.json` `project_duration_months` = 30.

[✓] TICKET 3 RESOLVED, 2026-08-11. An earlier version of this note called this a collision
    with ticket 3's "matches its pre-purge content" criterion and asked you to choose
    between amending the criterion and moving the field. That framing was wrong, and it is
    withdrawn. Reading `runner/unit_cost_budget.py` and the pre-purge file settled it.

    What the runner actually does. `_resolve_confirmed_months` (line 305) resolves the
    duration in priority order: a positive `project_duration_months` in the call binding
    (→ Confirmed); then an operator declaration in `working_assumptions.json` or the
    `DURATION` checklist token (→ Assumed); else Unresolved. Its docstring is explicit that
    `max_project_duration_months` is a call-level maximum and is "deliberately not used as
    the figure (§13.3: no fabricated project facts)". The two fields are different things
    and the engine already knows it.

    What the pre-purge file actually contains, at commit `6d96a60`:
      "max_project_duration_months": 36            <- genuine call fact
      "project_duration_months": 24                <- Confirmed
      "project_duration_months_note": "Operator-confirmed (13B consolidation, 2026-07-16)..."
    The 13B consolidation is the SUPERSEDED demo run's. So the 24 was never a call fact —
    it is the purged project's decision, sitting inside a call-binding artifact and stamped
    Confirmed. `host_country` is in the same position; it survives only because FIELDWISE
    also hosts in Hungary.

    Worse, two of the file's internal references now dangle. `action_confirmation_ref`
    points at `decision_log/action-confirmation-msca-pf_2026-07-13.json`, and `notes` cites
    `decision_log/13b-real-data-consolidation_2026-07-16.json`. Ticket 1 moved both to
    `decision_log/archive/demo-run/`. Verified: neither path resolves. And `notes` asserts
    RQ1–RQ10 are "operator-confirmed real data" — the opposite of what you confirmed three
    lines above in this very item.

    So this is not a criterion collision. It is a purge miss. Ticket 3's criterion is right
    in intent; the pre-purge file is what is wrong. Ticket 3 has been given a deviation
    block in `plans/fieldwise_tickets.md` listing the six fields to correct, in the same
    form as ticket 1's three deviations. No amendment to the runner is needed and none is
    proposed.

[!] Why the value is SET here rather than declared in `working_assumptions.json`. Both
    routes satisfy `gate_09` — `g08_uc03` accepts Confirmed or operator-declared Assumed.
    But `phase_04_gate`'s `timeline_within_duration` reads `project_duration_months` from
    `selected_call.json` by name, and the gate-enforcement rules record a predicate whose
    value is unavailable as a special case rather than passing it. Removing the field would
    serve one gate and risk stalling the other. Setting it to 30 satisfies both, and
    "Confirmed" is honest now that you have decided it — the runner's caution about
    confirming into the call binding was aimed at a duration nobody had chosen.

[!] FELLOWSHIP_TYPE is unchanged in kind — it remains a European Fellowship. The
    placement is an extension of it, not a different instrument. No amendment needed
    beyond the duration.

--- C5 DEFERRED BY THE OPERATOR, 2026-08-11 --------------------------------------
Status: DEFER — "I will consult with the fellow." Under this pack's own rules a deferred
item stays Unresolved and goes into the authorisation packet. No runner gate reads it, so
the run can proceed; ticket 7 must not issue authorisation while it is open.

HOST and FELLOWSHIP_TYPE are therefore marked CONFIRM — CONDITIONAL rather than plain
CONFIRM. The records themselves are right: ELTE is the intended host and a European
Fellowship is the intended instrument. What is unresolved is whether that combination is
*available* to this fellow at this deadline.

THE RULE IS NOT AMBIGUOUS. I checked the 2026 Guide for Applicants directly. The mobility
rule reads: "The researcher cannot have resided or carried out their main activity (work,
studies, etc.) in the country of the beneficiary for more than 12 months in the 36 months
immediately before the call deadline." The exception list is closed and exhaustive:

  a) compulsory national service;
  b) time spent in a procedure for obtaining refugee status under the Geneva Convention,
     and time spent obtaining EU temporary protection;
  c) short stays (such as holidays), "i.e. the researcher did not reside or did not have
     their main activity (work, studies, etc.) in the country during that period".

Career breaks, parental leave and time outside research are NOT on that list. They extend
the *research experience* window, which is a different criterion. And exception (c) is
defined by not having resided — so a career break spent living in Budapest is expressly not
a short stay.

THE ARITHMETIC, against a deadline of 2026-09-09, so a window opening 2023-09-09:

| Period | Basis | Months in window |
|--------|-------|------------------|
| 2023-09-09 to 2024-05-31 | Career break, residing in Budapest | ≈ 8.7 |
| 2024-06-01 to 2024-10-01 | Data Analyst, KPMG Global Hungary | 4.0 |
| 2026, 3 months, dates not given | Erasmus master's mobility at ELTE | ≈ 3.0 |
| | **Total** | **≈ 15.7** |

Even discounting the ELTE internship entirely, the first two rows come to ≈ 12.7 months
against a 12-month cap. The Erasmus is a three-month study mobility, which is main activity
rather than a holiday, so discounting it is generous rather than correct.

WHAT WOULD ACTUALLY CHANGE THE ANSWER. Only one thing: the CV's location lines are not
residence records. It says "BUDAPEST, HUNGARY" against the career break, but if her
registered residence remained in Bulgaria and the Budapest time was intermittent, the count
falls. That is the question to put to the fellow. Ask for documented residence — registration,
tax residence, lease or address history — across 2023-09-09 to 2026-09-09, not a recollection.

THE FOUR OPTIONS, preserved for when you have the answer.

  1. Verify residence and submit in 2026 as planned. Only viable if the documented record
     is materially different from the CV.
  2. Defer to the 2027 call. The arithmetic clears on its own: a ~September 2027 deadline
     puts the window at 2024-09 to 2027-09, containing roughly 0.8 months of KPMG plus the
     3-month Erasmus — about 3.8 months against a 12-month cap, with eight months of
     headroom. It also buys time for the AgroVIR letter, the PIC, and the placement
     narrative, all of which are currently thin. This was my recommendation.
  3. Restructure as a Global Fellowship. The mobility rule then applies to the outgoing
     third-country host rather than the return host, so ELTE could remain. FIELDWISE has no
     third-country partner — Bulgaria is a Member State — so this means finding one and
     redesigning the work plan.
  4. Change the host country. Clean on eligibility, but it removes ELTE, the supervisor
     relationship, the MATE archive and the PLANTDIGISENSE continuity. A different proposal.

[✓] SUPERVISOR record independently corroborated, 2026-08-11. ELTE's Faculty of Informatics
    lists Dr. András Jung as Professor and Deputy Director of the Institute of Cartography
    and Geoinformatics, H-1117 Budapest, Pázmány Péter sétány 1/C. The pre-purge record said
    "Deputy Head" and is accurate. The listing marks the deputy role as temporary, which is
    worth knowing for a 30-month action but does not affect the confirmation.

[!] The placement decision does not touch C5. The placement runs after the deadline and has
    no bearing on the 36-month look-back.
----------------------------------------------------------------------------------
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
  MATE: 2.4                <-- C4, corrected from 0.24 by the operator, 2026-08-11
  MVCRI: -
  AgroVIR: -
  ELTE supervisor: -

--- consolidated 2026-08-11 ------------------------------------------------------
You answered `fellow allocation as drafted: ACCEPT`. Taken as accepting the drafted
*shape*, extended to the approved 30 months — WP1 to WP4 are exactly as drafted and
untouched, and the six placement months are added where the placement actually happens.

  fellow allocation:  ACCEPT as drafted for WP1–WP4, extended for WP5 and cross-cutting
    WP1: 3.0   WP2: 5.5   WP3: 5.5   WP4: 4.0   WP5: 9.0   cross-cutting: 3.0   = 30.0

  [!] If you meant "accept" literally — the drafted table as written, totalling 24.0 —
      say so, because it would leave six months of the action unallocated and the line
      itself requires the total to equal the action duration. I have read it the other way
      because a 24-month allocation against a 30-month action cannot be what you intended.

| Work package | Month range | Person-months | Share | Change from the 24-month draft |
|--------------|-------------|---------------|-------|--------------------------------|
| WP1 Historical data and target design | M1–M6 | 3.0 | 10.0% | unchanged |
| WP2 Physiological early warning and sensor transfer | M3–M14 | 5.5 | 18.3% | unchanged |
| WP3 Prospective and uncertainty-aware prediction | M6–M18 | 5.5 | 18.3% | unchanged |
| WP4 Temporal and cross-country transferability | M12–M21 | 4.0 | 13.3% | unchanged |
| WP5 Operational transfer, decision value and web MVP | M16–**M30** | **9.0** | 30.0% | **+5.0**, range extended |
| Cross-cutting: management, training, dissemination | M1–**M30** | **3.0** | 10.0% | **+1.0**, range extended |
| Total | | **30.0** | 100% | +6.0 |

Why the six months land where they do. The placement is at AgroVIR, and AgroVIR is the
WP5 partner — so the added effort belongs to WP5 by construction, not by allocation
choice. Five of the six go there and one goes to cross-cutting, because management,
training and dissemination are continuous rows in the draft's Gantt and have to cover the
longer action. WP1–WP4 are untouched: none of them runs past M21 and the placement adds
nothing to them.

WP5 becoming the largest work package at 30% is the intended, visible consequence of the
decision. It is also the honest one — an evaluated placement that did not show up as the
largest effort block would look like a budget device rather than a research plan.

[!!] MONTH RANGES ARE NOT JUST THIS TABLE. `phase_04_gate` checks task months and the
     critical path, and ticket 4 seeds `workpackage_seed.json` and `milestones_seed.json`
     with Inferred task months derived from the WP month ranges. Those seeds must now be
     derived against M1–M30, not M1–M24. In particular:
       - WP5's range extends from M16–M24 to M16–M30, and its internal tasks need
         re-spreading. T5.6, the AgroVIR MVP assessment, is the natural occupant of the
         M25–M30 placement window.
       - MS5, if it sat at M24, has to move or be joined by a placement-completion
         milestone. The draft's four corrective decision points at M6, M12, M16 and M20
         now leave a ten-month unmonitored tail. Item 4's Steering Group meets at those
         four points; consider adding M27.
     None of this can be inferred safely from the draft. Ticket 4 should seed it Inferred
     with the derivation stated, and the authorisation packet should surface it.

[!] `phase_04_gate` also checks that concurrent work packages never demand more than one
    FTE in any month. M16–M21 now carries WP4 and a heavier WP5 concurrently. The totals
    still fit inside 30 person-months over 30 months, but the monthly profile is tighter
    than it was. Phase 4 will tell you if it breaks.

[✓] C4 RESOLVED 2026-08-11. MATE corrected from 0.24 to 2.4 person-months — the misplaced
    decimal. 2.4 PM across 30 months is roughly ten working days a year: plausible for
    supervision, data preparation and experiment access, and no longer at odds with item
    12's capacity claim for the same partner. It is in-kind and not costed by the unit-cost
    derivation, so it changes no budget figure. It is recorded as Assumed, not Confirmed —
    the number is the operator's estimate, not MATE's own statement, and it needs a matching
    declaration in `working_assumptions.json`.

[!] STILL OPEN, and it is the residue of C4 rather than a new problem. MVCRI, AgroVIR and
    the ELTE supervisor are all "-". A literal zero for the supervisor contradicts item 4's
    accepted weekly one-to-ones and quarterly reviews, and a literal zero for AgroVIR is now
    plainly wrong — it hosts the fellow for six months. Two ways to close it:
      (a) Give each a nominal indicative figure, declared Assumed like MATE's 2.4.
      (b) State in §3.1 that partner contributions are in kind and deliberately not
          quantified, and drop the per-partner lines entirely — including MATE's.
    (b) is the more honest option if none of these figures comes from the partners
    themselves. What is not defensible is a table where one partner carries a number and
    three carry dashes, because the dashes then read as zero.
----------------------------------------------------------------------------------
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

family_allowance:            does not apply — DECLARED ASSUMED   <-- C3, resolved 2026-08-11
long_term_leave_allowance:   does not apply — DECLARED ASSUMED   <-- C3, resolved 2026-08-11
special_needs_allowance:     does not apply 

duration used for the derivation:  30 months     <-- RESOLVED by the operator, 2026-08-11

--- consolidated 2026-08-11 ------------------------------------------------------
DURATION RESOLVED. 30 months, consistent with item 2's placement decision and item 7's
amended DURATION record. The contradiction that stood here is closed.

The derivation at 30 months, replacing the 24-month table above:

| Line | Rate | Basis | Amount |
|------|------|-------|--------|
| Living allowance | €6,350/month × 78.7% Hungary coefficient = €4,997.45 | 30 months | €149,923.50 |
| Mobility allowance | €710/month | 30 months | €21,300.00 |
| Research, training and networking | €1,000/month | 30 months | €30,000.00 |
| Management and indirect costs | €650/month | 30 months | €19,500.00 |
| **Total** | | | **€220,723.50** |

That is €44,144.70 more than the 24-month figure, and it matches the €220,723.50 the
candidate text already predicted for this scenario. Arithmetic checks out on all four
lines.

[!] Part A needs the placement months as a SEPARATE budget line — the 2026 Guide for
    Applicants is explicit about this. The derived total above is the whole 30 months in
    one block; Part A wants 24 + 6 shown separately. That is a Part A presentation matter,
    not a change to the total, but it has to happen.

[✓] C3 RESOLVED 2026-08-11 — THE ITEM IS NOW CLOSED. Operator chose to declare both
    remaining lines "does not apply" as Assumed. All three components of `g08_uc03` now
    resolve: duration Confirmed at 30, family allowance and long-term leave
    operator-declared Assumed, special needs does not apply. **`gate_09` passes.**

    The two declarations to write into `working_assumptions.json`, verbatim:

      project_duration_months: 30 — Confirmed. Operator decision 2026-08-11, input pack
        item 2: 24-month European Fellowship plus a 6-month non-academic placement at
        AgroVIR under CC-07. Also carried in selected_call.json per ticket 3's deviation.

      family_allowance: does not apply — ASSUMED, operator-declared 2026-08-11. Family
        status is established at recruitment, not at proposal stage. The unit-cost
        derivation is built without the family rate. If the fellow's circumstances at
        recruitment trigger the allowance, it is added at grant preparation, which is the
        normal route and does not affect the proposal budget.

      long_term_leave_allowance: does not apply — ASSUMED, operator-declared 2026-08-11.
        Not foreseeable at proposal stage. The deriver has no representation for this line,
        so it would be handled by amendment if it arose.

    This is the §13.3 pattern working as intended: a stated assumption, owned and dated,
    rather than a guess or a blank. Ticket 6 folds these; ticket 7 lists them as Assumed
    facts in the authorisation packet.

[!] The engine gap recorded in ticket 2 is now dormant rather than blocking.
    `derive_unit_cost_budget` still never sets `include_family`
    (`runner/unit_cost_budget.py:159`, call at line 507). With family allowance declared
    "does not apply", nothing needs the flag and the derived total is correct. Keep the
    engine ticket open — the bug is real and would bite on any future run that answers
    "applies" — but it no longer blocks this one.

[!!] family_allowance reads "applies unknown at proposal stage" — two answers at once. It
     has to be one. This one also carries the engine gap already recorded in ticket 2:
     `derive_unit_cost_budget` never sets `include_family`, so even a clean "applies" cannot
     reach the derived artifact without a code change (`runner/unit_cost_budget.py:159`, call
     at line 507).

     How to make the gate pass without pretending to know the answer. The predicate accepts
     an operator-declared Assumed value — it does not require certainty, it requires a
     declaration. So:
       family_allowance: does not apply — DECLARED ASSUMED. Family status is established at
         recruitment, not at proposal stage. The derivation is built without the family rate.
         If the fellow's circumstances at recruitment trigger it, the allowance is added at
         grant preparation, which is the normal route and does not affect the proposal budget.
       long_term_leave_allowance: does not apply — DECLARED ASSUMED. Not foreseeable at
         proposal stage; the deriver has no representation for it, and it would be handled by
         amendment if it arose.
     Both declarations go into `working_assumptions.json`. That is exactly what §13.3 wants:
     a stated assumption rather than a guess or a blank.

     If you would rather keep "unknown", that is a legitimate answer — but then accept that
     `gate_09` fails honestly and say so in the authorisation packet. Do not leave it
     ambiguous.

[✓] special_needs_allowance: does not apply. Clean.

[!] `selected_call.json` `project_duration_months` must now read 30. `gate_09` reads it
    from there, not from this form. Item 7's note records the collision this creates with
    ticket 3's acceptance criterion — settle that before ticket 3 runs.

[!] One knock-on the placement creates for the family allowance question specifically. A
    30-month action makes a change in family circumstances during the fellowship more
    likely than a 24-month one, simply by being longer. That does not change the answer at
    proposal stage — family status is still established at recruitment — but it slightly
    strengthens the case for declaring the assumption explicitly rather than leaving it
    open, since an amendment mid-action is the fallback either way.
----------------------------------------------------------------------------------
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

--- sweep 2026-08-11: what I could fill from sources already in hand ---------------
Blocks no gate. Feeds Part B-1 §3.2, which IS in scope for this run, so the blanks below
will show up in the drafted proposal.

AgroVIR — organisation_profile, DRAFTED from the company's own published figures:
  "AgroVIR Kft., founded 2007 and seated in Budaörs, Hungary, develops and operates a
  cloud-based farm management information system built on twenty years of practice in
  Hungarian commercial agriculture. The platform is in production use across more than
  745,000 hectares in eight countries: Hungary (500,000+ ha), Romania (120,000+),
  Azerbaijan (50,000+), Slovakia (40,000+), Bulgaria (15,000+), Serbia (10,000+), Ukraine
  (7,000+) and Argentina (3,000+). This is the commercial-scale operating environment
  against which WP5 tests research-to-farm transferability, and the Bulgarian and Hungarian
  footprints match the two countries FIELDWISE works in."
  Source: https://www.agrovir.com/HU/rolunk.html   [V]
  [!!] THE PLACEMENT DECISION RAISES THE BAR HERE. AgroVIR is no longer just a validation
       partner — it hosts the fellow for M25–M30, and the placement is evaluated. Part B-1
       must now show AgroVIR can *host a researcher*, not merely provide data access. That
       means, on top of the profile above: who supervises her on site and with what
       seniority, what workspace and system access she gets, what she works on for six
       months, and what she learns there that ELTE cannot teach. None of this exists yet in
       any source. It is the largest single content gap the placement decision opens.
  [!] relevant_track_record: no EU-funded research participation found for AgroVIR. If
      there is none, say so plainly and lean on the commercial footprint instead — an
      unevidenced claim of research experience is worse than an honest absence. With the
      placement now evaluated, the 745,000-hectare figure is doing more work than before:
      it is the main evidence that the host is substantial enough to place someone in.
  [!] key_people: only Zsuzsanna Balázs is named, role unknown. §3.2 needs a role — and
      the placement needs a named on-site supervisor, who may or may not be her.
  [!] "MCP validation via the agrovir software" — I could not tell what MCP stands for
      here. If it means the model/prediction pipeline validating through the AgroVIR API,
      write it out; the acronym will not survive an evaluator.

MVCRI — DRAFTED from the item 11 CV and the institute's own pages:
  department_and_team: Maritsa Vegetable Crops Research Institute, Plovdiv — a vegetable
    breeding and crop science institute of the Agricultural Academy, with tomato breeding
    and abiotic-stress physiology groups relevant to FIELDWISE.   [partly V]
  key_people: Dr. Rositsa Cholakova (Chief Assistant Professor) is MVCRI staff — but she is
    the fellow, so §3.2 needs OTHER MVCRI people to demonstrate capacity. Candidates visible
    from her co-authorships: Stanislava Grozeva, Ivanka Tringovska, Daniela Ganeva,
    Elena Topalova.   [!] confirm roles with MVCRI.
  recent_projects_and_publications: two funded projects run there now and both are strong
    §3.2 material —
      • ZEMDKT 17, Agricultural Academy, 2024–2026, Task 7: "Resistance to abiotic stress —
        drought and salinity in Solanum lycopersicum." Same crop and same stress as FIELDWISE.
      • KP-06-COST/2, National Science Fund, 2025–ongoing: "Monitoring of vegetable crops in
        support of precision agriculture using satellite and unmanned aerial systems", with
        the Space Research and Technology Institute, Bulgarian Academy of Sciences.
    Both come from the CV supplied for item 11, so they are as reliable as that document.
  [!] infrastructure: "secondary access to field trials" understates it and reads as an
      afterthought. WP4 depends on MVCRI having real experimental capacity. Ask for the trial
      area, the tomato germplasm held, and what measurement instruments are available.

MATE — key_people is Dr. Sándor Takács with no role, and recent_projects_and_publications is
  blank. MATE is a verified Horizon coordinator (AGRIGEP, grant 101094158), which is
  citable §3.2 evidence of EU project capability. Its PIC and legal identity are now
  confirmed in item 1.
  [!] The five-year hyperspectral archive is the single most important asset in the whole
      proposal and §3.2 currently describes it in one clause. Ask MATE for: years covered,
      instrument make and model, number of measurement campaigns and plots, and what soil and
      meteorological station data accompany it. Without this, G2 and H2 rest on an asset the
      proposal has not described.

ELTE — recent_projects_and_publications, previous_msca_hosting and
  hosting_arrangements_and_support_services are all blank, and §3.2 is scored.
  previous_msca_hosting: PARTIAL ANSWER AVAILABLE. Item 11 establishes that ELTE hosted the
    PLANTDIGISENSE MSCA-PF application (HORIZON-MSCA-2025-PF, proposal 101284764) with the
    same fellow and supervisor, scoring 70.40% against a 70.00 threshold. That evidences MSCA
    application experience, not MSCA *hosting*. [!] Ask ELTE's research office whether it has
    hosted funded MSCA fellows before, and how many.
  [!] hosting_arrangements_and_support_services is the field §3.2 is most explicitly scored
      on — integration into the team, office and lab access, administrative and career support,
      mentoring structure. None of it can be invented. This needs one email to ELTE.
  [!] "claude storage" in the infrastructure line is presumably "cloud storage". Fix before
      it reaches a drafted section.
------------------------------------------------------------------------------------
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

--- sweep 2026-08-11 -------------------------------------------------------------
[✓] Complete. Both statements accepted, no gate involved, nothing outstanding.
[!] One consistency note only: the accepted security statement says the project "involves no
    entity established outside the EU". True of the consortium as it stands — ELTE and MATE
    in Hungary, MVCRI in Bulgaria, AgroVIR in Hungary. It stays true regardless of how item 2
    is decided. No action needed; recorded so ticket 6 does not re-derive it.
----------------------------------------------------------------------------------
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

--- sweep 2026-08-11 -------------------------------------------------------------
[!] Unanswered. Blocks no gate, but the Phase 8 drafting skills read this, so leaving it
    blank means Phase 8 drafts to no budget at all.

Recommended answer, which is simply the drafted table:
  page budget as drafted:  ACCEPT

Three things that have changed since the candidate table was written, none of which
require altering it:

  • Item 10 landed at 35 references, the top of the 25–35 range the table assumed. They must
    fit inside the 1.1 + 1.2 allocation of 4.50 pages. At MSCA formatting a 35-entry list runs
    roughly 0.8–1.0 of a page, so §1.1 and §1.2 have about 3.5 pages of prose between them.
    That is tight but workable. If it proves not to be, drop R20 first (noted in item 10).
  • Item 6 added deliverable D1.3, and item 5 may add a K11 KPI for it. Both land in §3.1's
    1.50 pages alongside the 13-row risk table and the Gantt. §3.1 is the section most likely
    to overflow; the risk table compressing to a grouped form is the intended release valve.
  • Item 12's §3.2 allocation is 0.50 pages and four organisations must fit in it, one of
    which (ELTE) needs hosting arrangements as well as capacity. If the item 12 blanks get
    filled generously, 0.50 will not hold. Consider moving 0.25 from §1.3 to §3.2.

--- consolidated 2026-08-11 -------------------------------------------------------
The placement is approved, so the fourth pressure is now real rather than conditional.
§3.1's Gantt gains six months of columns, WP5 and the cross-cutting rows extend to M30,
and a placement-completion milestone probably joins MS1–MS5. All of that lands inside
§3.1's 1.50 pages, which was already the tightest allocation in the table.

More importantly, the placement is **evaluated**, and the Guide says it is described in
Part B-1. That is new prose with nowhere currently budgeted to go. It belongs across §1.2
(what happens in M25–M30 methodologically), §1.3 (what the fellow gains from a
non-academic environment — this is the training argument) and §3.1 (the work plan). None
of those three has slack.

Revised page budget, replacing the drafted table. The total still comes to 10.00:

| Section | Drafted | **Revised** | Why |
|---------|---------|-------------|-----|
| 1.1 Objectives, gaps, questions, ambition, references | 2.25 | 2.25 | unchanged; holds the 35-reference list |
| 1.2 Methodology, incl. the method figure | 2.25 | 2.25 | unchanged; absorbs the placement method text by compressing layer descriptions |
| 1.3 Supervision, training, two-way transfer | 0.75 | **1.00** | +0.25 — the placement's training argument lives here and is scored |
| 1.4 Researcher experience | 0.50 | 0.50 | unchanged |
| 2.1 Career perspectives | 0.75 | 0.75 | unchanged |
| 2.2 Dissemination, exploitation, communication | 0.75 | **0.50** | −0.25; the exploitation pathway overlaps the placement text in 1.3 and 3.1 |
| 2.3 Expected impacts | 0.75 | 0.75 | unchanged |
| 3.1 Work plan, Gantt, risks, effort | 1.50 | **1.75** | +0.25 — 30-month Gantt, extended WP5, placement in the work plan |
| 3.2 Capacity and hosting arrangements | 0.50 | **0.25** | −0.25, under protest; see the warning below |
| **Total** | 10.00 | **10.00** | |

  page budget as drafted:  REPLACE with the revised column above

[!!] §3.2 at 0.25 pages is the weakest part of this proposal. Four organisations, plus
     ELTE's hosting arrangements, plus — now — AgroVIR's ability to host a six-month
     placement, in a quarter page. It does not fit. I have taken the quarter page from it
     because §3.1 and §1.3 are scored harder and the placement content has to go
     somewhere, but this is a real loss, not a tidy reallocation.
     Two ways out, both yours to pick:
       (a) Compress the 13-row risk table to a grouped form in §3.1 and give the recovered
           space back to §3.2. The draft's risk table is the most compressible object in
           Part B-1.
       (b) Accept a thin §3.2 and carry the capacity detail in Part B-2 §5, which is not
           page-capped the same way. Legitimate, but §3.2 is scored under Implementation
           and Part B-2 is not, so this trades a scored section for an unscored one.
     (a) is better if the risk table survives compression legibly.

[!] The 35-reference list is unchanged by this decision and still fits §1.1 + §1.2 at
    roughly 0.8–1.0 page. If §1.2 turns out to need more room for the placement method
    text, dropping R20 remains the first release valve (item 10 records this).
----------------------------------------------------------------------------------
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

---

# Completion sweep — 2026-08-11

All fourteen items were reviewed in one pass after item 1 was completed. This section is the
register: what is done, what still blocks a runner gate, and what has no source. Ticket 6 folds
answers; ticket 7 carries whatever is still open into the authorisation packet.

## Status of the fourteen items

> **Consolidated 2026-08-11 (second pass).** The operator approved the six-month non-academic
> placement at AgroVIR and set the duration to 30 months. Items 2, 7, 8, 9, 12 and 14 have been
> updated to match. The table below reflects the post-decision state.

| # | Item | State | Gate | Verdict |
|---|------|-------|------|---------|
| 1 | Legal identity | **Complete** | `g04_p07` | MATE and MVCRI pass. AgroVIR fails: no PIC |
| 2 | Participation mode | **DECIDED** | `g04_p07` | Non-academic placement, 30 months. New Part B-1 content owed |
| 3 | Ethics | **Complete** | `g07_p06` | **C2 resolved.** Passes, contradiction gone |
| 4 | Governance | Complete | `g07_p07`, `g07_p08` | **C1 resolved in structure.** Needs one MVCRI name |
| 5 | KPIs | Complete | `g06_p04`, `g06_p05` | Passes. **C7 and C8 resolved** — EI-06 raised, HRS4R claim removed |
| 6 | Career Development Plan | Complete | `g07_p09` | Passes. **C7 resolved** — teaching component reframed |
| 7 | Identity spine | **Amended** | none | DURATION now 30; ticket 3 deviation written. **C5 DEFERRED** — HOST and FELLOWSHIP_TYPE conditional |
| 8 | Person-months | **Proposed** | none | 30-month split drafted; accept or replace. **C4 resolved** (MATE 2.4) |
| 9 | Unit-cost lines | **CLOSED** | `gate_09` `g08_uc03` | **C3 resolved.** All components resolve → **gate passes** |
| 10 | References | Complete | none | 35 refs. DrR alone uncited |
| 11 | Researcher CV | Complete | none | **Carries an eligibility risk that outranks everything** |
| 12 | Capacity | **Partial** | none | ELTE hosting blank; AgroVIR must now show it can host a placement |
| 13 | Security / Green Charter | Complete | none | Nothing outstanding |
| 14 | Page budget | **Proposed** | none | Revised 30-month budget drafted; §3.2 squeezed to 0.25 |

## Blocking a runner gate

Two remain. Item 2 is off this list.

**AgroVIR has no PIC — `phase_03_gate` `g04_p07`.** The draft assigns it WP5 co-lead, and the
placement decision now also makes it the host for M25–M30, so `partners.json` must contain it.
Registration is free and takes minutes, and item 1 supplies every field it needs: AGROVIR
Üzletviteli Tanácsadó Kft., 2040 Budaörs, Kinizsi utca 30, tax number 14000838-2-13. This is the
cheapest blocker on the list, and the placement decision made it more urgent, not less.

**~~Item 9's two "unknown" answers~~ — CLOSED 2026-08-11 (C3).** Both lines are now declared
"does not apply" as operator-declared Assumed. With duration Confirmed at 30, all three components
of `g08_uc03` resolve and **`gate_09` passes**. The declaration text for
`working_assumptions.json` is in item 9.

### Contradiction register

Nine contradictions were flagged in the sweep. Four are resolved.

| # | Contradiction | State |
|---|---------------|-------|
| C1 | Fellow held every MVCRI seat | **Resolved in structure** — needs one name |
| C2 | Ethics answers contradicted the accepted candidates | **Resolved** |
| C3 | Family allowance held two answers; both unknowns failed the gate | **Resolved — gate now passes** |
| C4 | MATE at 0.24 PM against its own capacity claim | **Resolved** — 2.4. Residue: three dashes still read as zero |
| C5 | Item 7 confirms HOST/FELLOWSHIP_TYPE; item 11 says they may be unavailable | **DEFERRED** — operator consulting the fellow. Rule text confirmed; records marked conditional |
| C6 | Escalation routes past the supervisor to a post the supervisor deputises | **Resolved** — Director is Dr. Mátyás Gede, a different person |
| C7 | Teaching treated as a competence to build; the CV shows five years of it | **Resolved** — EI-06 raised, CDP component reframed |
| C8 | EI-04 asserts ELTE holds HRS4R while the same item answers "unknown" | **Resolved** — claim removed; restore only if ELTE confirms |
| C9 | AgroVIR registered as a consultancy, named as technology partner and placement host | **Resolved** — named explicitly in the §3.2 / Part B-2 §5 wording |

Eight of nine resolved. C5 is deferred, not closed: no runner gate reads it, so the run proceeds,
but **ticket 7 must not issue authorisation while it is open** — it is the one item that can
invalidate the identity spine rather than merely weaken a score.

Open actions carried out of the contradiction pass, none of which I can close:

| Action | For | Blocks |
|--------|-----|--------|
| The fellow's documented residence across 2023-09-09 to 2026-09-09 | C5 | Authorisation |
| One MVCRI colleague's name and email | C1 | `g07_p08` resolution, item 1, item 4 |
| Confirm whether ELTE holds HRS4R | C8 | Nothing — restores a stronger EI-04 claim |
| Confirm an MSCA fellow may primary-supervise an ELTE MSc thesis | C7 | Nothing — else EI-06 drops to co-supervision |
| AgroVIR letter of commitment and named on-site placement supervisor | C9, item 12 | Nothing at gate; scored |
| Decide the three dashes in item 8's partner effort table | C4 residue | Nothing at gate; scored |

**~~Item 2's undecided mode~~ — CLOSED 2026-08-11.** The placement is approved. `roles.json` and
`partners.json` can now record `non_academic_placement` for AgroVIR, the duration is 30 months,
item 8's allocation totals 30, item 9's derivation runs at 30, and `selected_call.json`
`project_duration_months` is set to 30 — subject to the ticket 3 collision recorded in item 7.

## What the placement decision opened

Closing item 2 settled four items and opened five pieces of work. None blocks a gate; all of them
are scored.

| Owed | Where it lands | Why it is new |
|------|----------------|---------------|
| Part B-1 must argue the placement | §1.2, §1.3, §3.1 | The Guide says the placement is described in Part B-1 and evaluators assess its relevance and quality. The draft says nothing about M25–M30 |
| AgroVIR letter of commitment | Item 1 | An *evaluated* placement resting on a host with no letter is the weakest form of this decision. Now the most urgent open action after the mobility flag |
| AgroVIR must show it can host a researcher | Item 12, §3.2 and Part B-2 §5 | On-site supervisor, workspace, system access, six months of work. Nothing on this exists in any source yet |
| Part A separate budget line | Part A §3 | The Guide requires the placement months as their own line, even though the derived total is one block |
| 30-month WP and milestone ranges | Ticket 4 seeds | WP5 extends to M30, MS5 moves or gains a companion, and the M6/M12/M16/M20 decision points leave a ten-month unmonitored tail |

## A purge miss found on the way, 2026-08-11

Chasing the duration through the runner turned up something that has nothing to do with the
placement and would have surfaced at ticket 3 regardless.

The pre-purge `selected_call.json` carries the superseded demo run's project facts inside a
call-binding artifact — `project_duration_months: 24` stamped Confirmed and provenanced to the 13B
consolidation of 2026-07-16, `host_country` provenanced the same way, and a `notes` field asserting
that RQ1–RQ10 are "operator-confirmed real data" when item 7 confirms they are superseded. Two of
its internal references also dangle: `action_confirmation_ref` and the `notes` citation both point
at decision-log files that ticket 1 moved to `archive/demo-run/`. Verified — neither path resolves.

Ticket 1's purge was scoped to directories and to the decision log. It did not re-read the contents
of files that survived, and this one survived with purged data inside it.

`plans/fieldwise_tickets.md` now carries a deviation block on ticket 3 listing the six fields to
correct. Two consequences worth carrying further.

Ticket 3's acceptance criterion has been reworded from "matches its pre-purge content" to
"targets HORIZON-MSCA-2026-PF-01 and its call-scoped fields match its pre-purge content", with a
second criterion covering the corrections. The old wording could not be met honestly.

**I checked whether anything else survived with demo-run content in it.** `selected_call.json` was
found because `gate_09` reads it, so it was worth asking what else had not been re-read. A
`git grep` for `13b-real-data`, `13B consolidation`, `synthetic-spine`, `synthetic-concept` and
`demo-run` across `docs/`, `plans/` and `runner/`, excluding `archive/demo-run/`, returns seven
files. **None is a Tier 3 data file, and none needs action.**

| File | Verdict |
|------|---------|
| `decision_log/fieldwise-purge-and-decision-log-split_2026-08-11.json` | The purge record itself, describing what it moved. Correct |
| `plans/fieldwise_reinstantiation_plan.md`, `plans/fieldwise_tickets.md` | Plans describing the purge. Correct |
| `plans/milestones/WAVE6_STATE_HANDOFF.md`, `plans/reports/HANDOFF_phase8_m2t10_2026-07-22.md` | Historical planning documents, not project data. Correct |
| `runner/docx_exporter.py` | The `synthetic-spine*.json` glob at line 69 — exactly the mechanism ticket 1 relies on, and it now matches nothing. Correct |
| `decision_log/milestone1-engine-integration-proof_2026-07-15.json` | Borderline but defensible — see below |

The last one is the only judgement call. It was classified as an engine ruling and left in
`decision_log/`, which is right on content — it records engine bugs found and fixed, the length fix,
the live pipeline proof and a `gate_10a` honest block, all of which are reusable findings about the
engine rather than facts about the superseded project. But it also carries `run_id` and
`final_run_states` fields tied to the demo run, and a `what_remains_for_a_real_finalization_13B` key.
Nothing reads those fields, so it is inert. Flagging it only so the classification is on the record
rather than rediscovered later.

Conclusion: `selected_call.json` was the only real survivor with purged data inside it. Ticket 1's
purge was sound; it was scoped to directories and to the decision log, and this one file slipped
through because it survives by design and nobody re-read its contents.

## No source — flagged, not guessed

| What | Where | Status |
|------|-------|--------|
| DrR - Digital Agronomist | Item 10, area 8 | No publication, preprint, release or repository. Deposit on Zenodo or accept §1.1.3 uncited |
| ELTE HR Excellence in Research (HRS4R) | Item 5, EI-04 | Could not confirm either way. EURAXESS list robots-blocked; elte.hu search found nothing. One email to ELTE settles it. Fallback wording supplied in item 5 |
| ELTE hosting arrangements and support services | Item 12 | Cannot be invented and §3.2 is scored on it |
| ELTE previous MSCA hosting | Item 12 | PLANTDIGISENSE evidences application, not hosting |
| AgroVIR EU-project track record | Item 12 | None found. May genuinely be none — say so rather than imply otherwise |
| AgroVIR company registration number | Item 1 | Two conflicting readings. Ask the company |
| Roles of Takács, Balázs; MVCRI senior contact | Items 1, 4, 12 | Names known, roles not |
| MATE archive specification | Item 12 | Years, instrument, campaigns, plots. The proposal's most important asset is described in one clause |
| Invited talks | Item 11 | Not in the CV. Supply or confirm none |
| PhD thesis exact title | Item 11, R34 | Read truncated; English rendering is mine |
| AgroVIR on-site placement supervisor | Item 12 | Added 2026-08-11. The placement is evaluated and currently has no named supervisor |
| What the fellow does at AgroVIR in M25–M30 | Item 2, §1.2/§1.3 | Added 2026-08-11. Cannot be inferred from the draft; only AgroVIR and the fellow can supply it |

## The one that is not a gate problem

Item 11 raises a **mobility-rule risk** that no gate checks and no seeding can work around. On the
CV's face the fellow spent roughly 12.7 months in Hungary inside the 36-month window before the
deadline, against a 12-month cap — and about 15.7 months if the 2026 Erasmus internship at ELTE
counts. If that holds, the European Fellowship with ELTE as host is not available and item 7's
`FELLOWSHIP_TYPE` and `HOST` confirmations are wrong.

Everything else in this pack is downstream of that being true. Settle it first.

**Updated 2026-08-11.** The rule text has since been checked directly against the 2026 Guide for
Applicants and it is not ambiguous: the exception list is closed at compulsory national service,
refugee and temporary-protection procedures, and short stays defined as periods where the researcher
*did not reside* in the country. Career breaks and parental leave are excluded from the
research-experience criterion, not from this one. So the arithmetic above stands unless the fellow's
documented residence differs from what her CV states.

The operator has deferred pending consultation with the fellow. Item 7 now carries HOST and
FELLOWSHIP_TYPE as CONFIRM — CONDITIONAL, and the four available routes, including deferring to the
2027 call where the window clears to about 3.8 months, are recorded in item 7.

## One thread running through four items

The fellow is named as MVCRI's contact (item 1), as MVCRI's steering-group representative (item 4),
and is the person whose model WP4 tests against MVCRI data (item 2). She is also the author of the
KPIs that measure that test (item 5, K5 and K6). Item 2 already asks for a statement on MVCRI
independence; a statement will not carry it while the same person holds every seat.

Naming one MVCRI colleague other than the fellow fixes all four at once. It is a single edit in two
places and it is the highest-leverage small change available in this pack.
