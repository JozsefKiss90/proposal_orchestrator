# FIELDWISE authorisation packet

**Branch:** `fieldwise-run-01` · **Date:** 2026-08-12 · **Ticket:** `plans/fieldwise_tickets.md` ticket 7 ·
**Plan step:** `plans/fieldwise_reinstantiation_plan.md` §7 S6 · **Revision:** 3, after the second authorisation review

> **AUTHORISED 2026-08-12.** You authorised the seeded state on revision 3, having held authorisation on
> revisions 1 and 2 the same day. The record is
> `docs/tier4_orchestration_state/decision_log/fieldwise-authorisation_2026-08-12.json`, and
> `selected_call.json` now points `action_confirmation_ref` at it. Section 12 states what that record
> holds. The stamp, the section 12 rewrite and the one count it moved are the only edits made after you
> authorised; sections 1 to 11 are the text you read.

This is the document you authorise the run on. It lists every record tickets 3 to 7 seeded into Tier 3,
with its status and its source reference. It lists every residual open item under the gate it affects.
It states which gates the seeded state can pass and which depend on what the run itself produces.

Nothing here is new project data. Every line traces to a Tier 3 artifact, and every Tier 3 artifact
traces to the master draft, to the operator input pack, or to a decision-log record.

**Where this file lives.** Tier 4, as orchestration state, under CLAUDE.md §12.1 and §12.2. The
neighbouring files in `validation_reports/` are run-scoped skill output named
`<check>_<run_id>.json`. This one is a hand-authored operator review document and is named for what it
is, which is why it carries a date rather than a run id.

## 1. What you are authorising

You are authorising the execution of Phases 1 to 8 against the Tier 3 state described below.

Authorisation does not assert that the state is complete. Twelve items are open and thirty-four
records are Assumed. Sections 5 and 6 list all of them. Authorisation asserts that you have seen them
and accept the run proceeding with them open.

The run halts at the first gate whose inputs are incomplete. A gate failure is a correct output under
CLAUDE.md §12.4, not a fault to work around.

## 2. What changed since revision 1

You held authorisation twice and answered ten items across two reviews. All ten are folded into Tier 3.
Three decision-log records hold them: `decision_log/fieldwise-placement-hosting_2026-08-12.json`,
`decision_log/fieldwise-ticket7-open-items_2026-08-12.json` and
`decision_log/fieldwise-ticket7-review-round2_2026-08-12.json`.

| Id | Item | Outcome |
|----|------|---------|
| AR-1 | AgroVIR on-site placement supervisor | Miklós Maróti, Assumed and declared. Title Unresolved |
| AR-2 | AgroVIR placement workspace and system access | Still Unresolved. Your answer described field access, which is a different fact |
| AR-3 | AgroVIR six-month work content | Four items, Confirmed, reframed from the answer you first gave |
| AR-4 | D5.1 sequencing against the placement | Inferred, and already satisfied by MS5 at M23 |
| AR-5 | K11 | Added and Confirmed. Every accepted deliverable now carries a KPI |
| AR-6 | Co-supervisor person-months | 2.0 confirmed. Value unchanged, contradiction closed |
| AR-7 | M23-M30 monitoring gap | M27 steering point added |
| AR-8 | Invited talks | Deferred by name. Still Unresolved |
| AR-9 | Verification of the placement window | MS6 at M30 seeded as Inferred, and D5.4 and D5.5 named as what carries it. Reverses half of AR-7 |
| AR-10 | An M27 Career Development Plan review | Five review points, not four. Closes the contradiction AR-7 created |

Two verifications you asked for, both done before the fold.

**The input pack on disk is not current.** `plans/fieldwise_operator_input_pack.md` and its Tier 3 copy
are byte-identical at 183,385 bytes with an empty `diff`. The on-disk pack still carries both
co-supervisor figures, 2.0 at line 1210 and 1.5 at line 1314, so no revision resolving them ever
reached the repository. It contains no occurrence of "Maróti", and its item 12 lines at 2300 and 2685
hold the placement question rather than an answer. Revisions delivered as files outside the repository
are not repository state. Your answers therefore enter Tier 3 citing the two decision-log records, not
an input pack item.

**`g04_p07` tests record existence.** `all_partners_in_tier3` at
`runner/predicates/coverage_predicates.py:720` reads `partner_id` from `partners.json` and tests subset
membership of the work-package lead and contributor set. It reads no other field. The finding in §6.5
stands.

## 3. Status vocabulary

The four categories are CLAUDE.md §12.2, used without extension.

| Status | Meaning here |
|--------|--------------|
| Confirmed | Directly evidenced by a named source: a draft paragraph, an operator decision in the input pack, or an operator decision in the decision log |
| Inferred | Derived by reasoning from Confirmed evidence, with the derivation stated in the record's `note` |
| Assumed | Adopted with no direct evidence, declared by you in `working_assumptions.json` |
| Unresolved | Missing or contradicted, named rather than guessed, and blocking whatever needs it |

`¶N` is the Nth non-empty paragraph of `FIELDWISE_MSCA_Master_Draft.docx` in body order, table cells
included. The scheme is defined in `docs/tier3_project_instantiation/hand_lift_provenance.json`.

## 4. Record inventory

Every seeded record appears below with its status and source reference. A record is any object carrying
a `validation_status` or `*_status` field, plus the checklist records, the working-assumption
declarations, and the two narrative front matters.

### 4.1 Call binding — `call_binding/selected_call.json`

| Record | Value | Status | Source reference |
|--------|-------|--------|------------------|
| Call-scoped block: call id, topic, instrument, deadline, opening, work programme, call extract, type of action, indicative budget, `max_project_duration_months` 36, `budget_regime` unit_cost | HORIZON-MSCA-2026-PF-01 | Carried forward | Pre-purge binding at commit `6d96a60`, unchanged |
| `host_country` | HU | Confirmed | Input pack item 7, 2026-08-11 |
| `project_duration_months` | 30 | Confirmed | Input pack items 2 and 7, 2026-08-11 |
| `action_confirmation_ref` | `decision_log/fieldwise-authorisation_2026-08-12.json` | Confirmed | Your authorisation of 2026-08-12. Section 12 records it |

### 4.2 Confirmation checklist — `call_binding/confirmation_checklist.json`

Thirty-four records: eleven spine, two supersessions, eleven operator decisions, ten
authorisation-review decisions.

| Record | Status | Source reference |
|--------|--------|------------------|
| FELLOW — Dr. Rositsa Cholakova, publishing before 2020 as Cholakova-Bimbalova | Confirmed | Input pack items 7 and 11 |
| HOST — Eötvös Loránd University, Faculty of Informatics, Budapest, HU | Confirmed | Cover block ¶7-8; §3.2 ¶425-426; item 7 |
| SUPERVISOR — Prof. András Jung, ELTE | Confirmed | Input pack item 7, corroborated against the ELTE staff listing |
| CO_SUPERVISOR — Dr. Roland Hollós, ELTE Department of Meteorology | Confirmed | Input pack item 7, new record 2026-08-11 |
| DATA_PARTNER — MATE, PIC 891269563 | Confirmed | Input pack items 1 and 2; CORDIS grant 101094158 |
| TRANSFER_PARTNER — MVCRI, PIC 999533009 | Confirmed | Input pack items 1 and 2; CORDIS FP7 grant 205941 |
| VALIDATION_PARTNER — AGROVIR Kft., tax number 14000838-2-13 | Confirmed | Input pack items 1 and 2; Hungarian company register |
| FELLOWSHIP_TYPE — European Fellowship with a CC-07 placement extension | Confirmed | Input pack item 7; draft cover block |
| DURATION — 30 months, 24 at ELTE plus 6 at AgroVIR | Confirmed | Operator decision 2026-08-11 |
| CALL_BINDING — HORIZON-MSCA-2026-PF-01, deadline 2026-09-09 | Confirmed | Input pack item 7 |
| MOBILITY_ELIGIBILITY — 7.05 months against a 12-month cap | **Assumed** | Operator override of C5, 2026-08-11. Section 5 states the basis |
| DATA_PROVIDERS superseded — PlanetScope, Sentinel-1, ERA5 are out | Confirmed | Input pack item 7 |
| RQ1-RQ10 superseded — the draft carries RQ1-RQ7 and H1-H6 | Confirmed | Input pack item 7 |
| Item 3 — ethics self-assessment, nine answers, issues identified | Confirmed | Input pack item 3, C2 amendment |
| Item 4 — governance, Steering Group, six decision rights, five meeting points | Confirmed | Input pack item 4, C6 correction, AR-7 amendment |
| Item 5 — eleven KPIs and six expected-impact mappings | Confirmed | Input pack item 5, C7 and C8; K11 by AR-5 |
| Item 6 — Career Development Plan, D1.3 at M3, reviewed at five points | Confirmed | Input pack item 6, AR-10 amendment |
| Item 8 — person-months, fellow 30.0 and partners 11.4 | Confirmed | Input pack item 8, C4 correction, AR-6 confirmation |
| Item 9 — no optional unit-cost line applies | **Assumed** | Input pack item 9, C3 resolved |
| Item 10 — 35-entry reference list | Confirmed | Input pack item 10 |
| Item 11 — researcher CV | Confirmed | Input pack item 11 |
| Item 12 — capacity descriptions, answered in part | **Unresolved** | Input pack item 12, partial deferral, AR-1 amendment |
| Item 13 — security screening and Green Charter | Confirmed | Input pack item 13 |
| Item 14 — page budget over nine sections, 10.0 pages | Confirmed | Input pack item 14, revised table |
| AR-1 to AR-10 — the authorisation-review decisions | 5 Confirmed, 1 Inferred, 2 Assumed, 2 Unresolved | The three decision-log records of 2026-08-12. Section 2 tabulates them |

### 4.3 Project brief

| Record | Status | Source reference |
|--------|--------|------------------|
| `project_summary.json` — 12 fields: acronym, title, instrument type, target crop, host, data environment, transfer environment, prototype, planned MVP, field evaluator, one-sentence summary, core message | Confirmed (12) | Cover block ¶1-18; ¶433-434; ¶435-436 |
| `concept_note.md` — verbatim lift, seven subsections including G1-G6, RQ1-RQ7, H1-H6 | Confirmed | §1.1.1-§1.1.7, ¶21-79 |
| `strategic_positioning.md` — verbatim lift, six transitions, validation ladder, five impact blocks, three prior-evaluation responses | Confirmed | §1.1.9 ¶102-110; §2.3 ¶239-249; ¶114, ¶233, ¶379 |

### 4.4 Objectives — `architecture_inputs/objectives.json`

Six records, all Confirmed. `title` is the draft table's Purpose column, `measurable_output` its
Verification column.

| Id | Title | Target month | Source reference |
|----|-------|--------------|------------------|
| O1 | Harmonised five-year MATE soil-plant-atmosphere dataset | 6 | §1.1.8 ¶84-86; WP1 ¶252-262 |
| O2 | Hyperspectral early-warning signatures and Sentinel-2 transferability | 12 | §1.1.8 ¶87-89; WP2 ¶263-274 |
| O3 | Prospective uncertainty-aware water-stress forecasts | 16 | §1.1.8 ¶90-92; WP3 ¶275-287 |
| O4 | Temporal and Hungary-to-Bulgaria transferability | 20 | §1.1.8 ¶93-95; WP4 ¶288-301 |
| O5 | Research-to-commercial-field operational transferability | 23 | §1.1.8 ¶96-98; WP5 ¶302-317 |
| O6 | Irrigation priority and a functional web MVP | 23 | §1.1.8 ¶99-101; WP5 ¶302-317 |

### 4.5 Outcomes — `architecture_inputs/outcomes.json`

Twenty-eight records: fifteen outputs, seven transitions, six outcomes.

| Group | Records | Status | Source reference |
|-------|---------|--------|------------------|
| Outputs | D1.1 ¶260, D1.2 ¶261, D2.1 ¶272, D2.2 ¶273, D3.1 ¶285, D3.2 ¶286, D4.1 ¶298, D4.2 ¶299, D4.3 ¶300, D5.1 ¶312, D5.2 ¶313, D5.3 ¶314, D5.4 ¶315, D5.5 ¶316 | Confirmed (14) | §3.1 deliverable lines |
| Output D1.3 — Career Development Plan, M3 | 1 | Confirmed | Input pack item 6, not in the draft |
| Transitions | TR1 ¶104, TR2 ¶105, TR3 ¶106, TR4 ¶107, TR5 ¶108, TR6 ¶109, VL ¶110 | Confirmed (7) | §1.1.9 |
| Outcomes | OC1 to OC6 | **Inferred (6)** | Derived from the transitions and the outputs. Each `note` states the derivation |

The draft never separates an output from the outcome it produces. OC1 to OC6 are that separation, made
here for the first time. Phase 5 refines it against the Tier 2B expected outcomes.

### 4.6 Impacts — `architecture_inputs/impacts.json`

Twenty-four records, all Confirmed after AR-5: five impact claims, eleven KPIs, six expected-impact
mappings, and two collection records.

| Group | Records | Source reference |
|-------|---------|------------------|
| Impact claims | IMP-SCI ¶240-241, IMP-ENV ¶242-243, IMP-AGRI ¶244-245, IMP-TECH ¶246-247, IMP-EU ¶248-249 | §2.3, verbatim |
| KPIs | K1 D1.1, K2 D2.2, K3 D3.1, K4 D3.2, K5 D4.2, K6 D4.3, K7 D5.1, K8 D5.3, K9 D5.4, K10 D5.5 | Input pack item 5, accepted 2026-08-11 |
| KPI K11 | Career Development Plan agreed by M3 and reviewed at all five steering points, D1.3 | AR-5, decided 2026-08-12; count amended by AR-10 |
| Expected impacts | EI-01 D1.3, EI-02 D4.2 and D5.4, EI-05 D2.2, D3.2 and D4.3 | Draft content: §2.1, §1.3, §2.3, §3.1 |
| Expected impacts | EI-03 public engagement, EI-04 Charter convergence, EI-06 teaching integration | Input pack item 5. The draft addresses none of the three |

EI-03 and EI-06 map to activities, not deliverables, so their `mapped_project_outputs` lists are empty
by design. EI-04 carries no HRS4R claim: you confirmed on 2026-08-11 that ELTE does not hold the award,
and the claim is removed permanently.

### 4.7 Work packages — `architecture_inputs/workpackage_seed.json`

Sixty-nine status-bearing records.

| Group | Records | Status | Source reference |
|-------|---------|--------|------------------|
| Work packages | WP1 M1-M6, WP2 M3-M14, WP3 M6-M18, WP4 M12-M21, WP5 M16-M30 | Confirmed (5) | §3.1 ¶252-317 |
| WP5 end month | M30, with the draft's M24 kept as `draft_end_month` | Confirmed | Input pack items 2 and 8 |
| Tasks | T1.1-T1.5 ¶254-258, T2.1-T2.6 ¶265-270, T3.1-T3.7 ¶277-283, T4.1-T4.7 ¶290-296, T5.1-T5.7 ¶304-310 | Confirmed (32) | §3.1, one paragraph per task in id order |
| Deliverables | D1.1, D1.2, D2.1, D2.2, D3.1, D3.2, D4.1, D4.2, D4.3, D5.1-D5.5 | Confirmed (14) | §3.1 deliverable lines |
| Deliverable D1.3 | 1 | Confirmed | Input pack item 6 |
| Task month allocation | 32 rows, each task inheriting its work package's range | **Inferred (1)** | The draft gives no task-level months |
| Dependencies | WP1→WP2, WP1→WP3, WP2→WP3, WP3→WP4, WP4→WP5, WP3→WP5 | **Inferred (6)** | Derived from task content and milestone lines |
| WP5 deliverable sequencing check | D5.1 lands before M25 | **Inferred (1)** | AR-4. MS5 at M23 already forces it |
| Fellow effort | WP1 3.0, WP2 5.5, WP3 5.5, WP4 4.0, WP5 9.0, cross-cutting 3.0, total 30.0 | Confirmed (1) | Input pack item 8 |
| Partner in-kind effort | MATE 2.4, MVCRI 1.5, AgroVIR 3.0, ELTE supervisor 2.5, ELTE co-supervisor 2.0, total 11.4 | **Assumed (6)** | Input pack item 8, co-supervisor figure confirmed by AR-6 |

### 4.8 Milestones — `architecture_inputs/milestones_seed.json`

Sixteen records after AR-9: fifteen Confirmed, one Inferred, plus one Unresolved sub-record.

| Id | Month | Criterion statement | Status | Source reference |
|----|-------|---------------------|--------|------------------|
| MS1 | 6 | Data and target readiness | Confirmed | §3.1 ¶262 |
| MS2 | 12 | Sentinel-observable physiologically meaningful early-warning signature established | Confirmed | §3.1 ¶274 |
| MS3 | 16 | Predictor ready for independent transferability testing | Confirmed | §3.1 ¶287 |
| MS4 | 20 | Independent cross-country transferability quantified | Confirmed | §3.1 ¶301 |
| MS5 | 23 | Web MVP externally evaluated under farmer conditions | Confirmed | §3.1 ¶317 |
| MS6 | 30 | Non-academic placement completed: the operational assessment and the FMIS integration roadmap are delivered from inside the host company | **Inferred** | AR-9. Month from WP5's end, criterion from the AR-3 work content |
| Steering points | 6, 12, 16, 20 | The draft's corrective decision points, adopted as the Steering Group schedule | Confirmed | §3.1 ¶379; input pack item 4 |
| Steering point | 27 | Mid-placement review of the M25-M30 placement | Confirmed | AR-7 |
| `placement_verification` | — | D5.4 and D5.5 carry the placement's verification, and MS6 attaches to both | Confirmed | AR-9 |
| `placement_verification.open_sequencing_question` | — | D5.4 is claimed by both MS5 at M23 and the placement window | **Unresolved** | AR-9 |
| `placement_period_monitoring` | — | Both candidates input pack item 8 raised are now adopted | Confirmed | AR-7 and AR-9 |

MS1 to MS5 carry the draft's own criterion statements verbatim. MS6 has no draft source, because the
draft's action ran to M24, so it is Inferred with its derivation stated: the month is WP5's Confirmed
end month, and the criterion restates two AR-3 work-content items that already produce D5.4 and D5.5.
No deliverable, task or month is invented. Turning any criterion statement into a verifiable
achievement criterion with a responsible party is Phase 4's output, not a seeded fact.

### 4.9 Risks — `architecture_inputs/risks.json`

Fourteen records, all Confirmed. R01 to R13 lift the draft's risk table at ¶384-422, three paragraphs
each in id order. Likelihood and impact split the draft's single L/I column.

| Id | Title | L/I |
|----|-------|-----|
| R01 | Historical MATE information incomplete | M/H |
| R02 | Hyperspectral index has no Sentinel equivalent | M/M |
| R03 | Spectral domain mismatch | M/H |
| R04 | Proximal/satellite spatial mismatch | M/H |
| R05 | Insufficient physiological stress events | M/H |
| R06 | Cloud gaps | M/M |
| R07 | Unseen-year performance drops | M/H |
| R08 | Hungary-to-Bulgaria performance drops | M/H |
| R09 | Farmer-field performance drops | M/H |
| R10 | Bayesian approach does not outperform ML | M/L |
| R11 | Prediction is accurate but too late | M/H |
| R12 | Web development delayed | L/M |
| R13 | Full AgroVIR integration not feasible | M/M |
| `risk_philosophy` | Failed zero-shot transfer is a scientific finding, not project failure | ¶423 |

Categories, owners and affected work packages are absent from the draft. Phase 6 populates them.

### 4.10 Consortium — `consortium/roles.json` and `consortium/partners.json`

Seven role tokens, each with one record in each file. All fourteen records are Confirmed.

| Token | Identity | Source reference |
|-------|----------|------------------|
| FELLOW | Dr. Rositsa Cholakova, natural person, BG | Input pack item 7; §1.4 ¶212-216 |
| HOST | ELTE, sole beneficiary, HU | Cover block ¶7-8; §3.2 ¶425-426; item 7 |
| SUPERVISOR | Prof. András Jung, natural person, HU | Input pack item 7; §1.3 ¶182-194 |
| CO_SUPERVISOR | Dr. Roland Hollós, natural person, HU | Input pack item 7, added 2026-08-11 |
| DATA_PARTNER | MATE, associated partner, HU | Cover block ¶9-10; §1.3 ¶206-207; items 1 and 2 |
| TRANSFER_PARTNER | MVCRI, associated partner, BG | Cover block ¶11-12; §1.3 ¶208-209; items 1 and 2 |
| VALIDATION_PARTNER | AgroVIR, non-academic placement host, M25-M30, HU | Cover block ¶17-18; §1.3 ¶210-211; items 1 and 2 |

CO_SUPERVISOR is a seventh token beyond the six the ticket named. Input pack item 7 instructed ticket 5
to add it, because a co-supervisor is a management role at the beneficiary that `g07_p08` reads.

Six fields inside those records carry their own status.

| Field | Value | Status |
|-------|-------|--------|
| MATE `contact_person` | Dr. Sándor Takács | Assumed |
| AgroVIR `contact_person` | Zsuzsanna Balázs | Assumed |
| MVCRI `contact_email` | vinelina@abv.bg | Assumed |
| MVCRI `signatory_authority` | null | Unresolved |
| AgroVIR `company_registration_number` | null | Unresolved |
| AgroVIR `pic` | null | **Confirmed absent** |

### 4.11 Capabilities — `consortium/capabilities.json`

Fifty-seven status-bearing records, up from forty-six: AR-1 to AR-4 decomposed the AgroVIR
placement-hosting record from one null field into five sub-records.

| Group | Records | Status | Source reference |
|-------|---------|--------|------------------|
| Knowledge transfer | KT1 ELTE to fellow (eleven competences), KT2 fellow to ELTE (nine), KT3 bidirectional | Confirmed (3) | §1.3 ¶183-205, verbatim |
| Partner contributions | PC1 MATE, PC2 MVCRI, PC3 AgroVIR | Confirmed (3) | §1.3 ¶206-211, verbatim |
| Capacity statements | CAP1 ELTE, CAP2 MATE, CAP3 MVCRI, CAP4 AgroVIR | Confirmed (4) | §3.2 ¶425-432, verbatim |
| Training and career | TR-COMP ¶220, TR-GAP ¶215, TR-PROGRESSION ¶216 | Confirmed (3) | §2.1 and §1.4 |
| Participant capacity | ELTE, MATE, MVCRI, AgroVIR, with per-field statuses | Confirmed (4 records) | Input pack item 12, answered in part |
| AgroVIR placement hosting | Supervisor Assumed, workspace Unresolved, work content Confirmed, ELTE comparison Inferred, field access Confirmed, D5.1 check Inferred | Unresolved overall | AR-1 to AR-4. Section 7 sets it out |
| Researcher profile | CV: positions, doctorate, teaching, publications, projects, mobilities, career break, previous submission | Confirmed (1 record) | Input pack item 11 |
| `part_b2_capacity_detail` | Roll-up of the residual capacity gaps | **Unresolved** | Input pack item 12 |

### 4.12 Working assumptions — `working_assumptions.json`

Fourteen declarations, Assumed by construction. Section 5 lists them.

`project_duration_months` and `host_country` are deliberately not declared. Both are Confirmed in
`selected_call.json`, which is where the unit-cost deriver resolves them first and where
`phase_04_gate` reads the duration by name. The shared reader stamps every declaration Assumed, so a
declaration would render an operator-Confirmed fact Assumed in the declared surface.

### 4.13 Not seeded

`topic_mapping.json` and `compliance_profile.json` do not exist. Phase 2 writes them. This is the plan's
design, not a gap.

## 5. Status totals

| Status | Count | Change since revision 1 | Change at the 2026-08-14 fold |
|--------|-------|--------------------------|-------------------------------|
| Confirmed | 232 | +17 | +1 |
| Inferred | 19 | +5 | 0 |
| Assumed | 42 | +7 | +8 |
| Unresolved | 11 | +3 | -6 |
| **Total** | **304** | **+32** | **+3** |

The count covers 254 `validation_status` and `*_status` fields across the Tier 3 JSON, plus 34
checklist records, 17 declarations, and the 2 narrative front matters.

**Amended 2026-08-14 (open-items fold).** The counts above are recomputed, not the ones tallied at
the 2026-08-12 review; the fourth column isolates what the fold moved. The operator answered six of
the twelve accepted open items and Tier 3 was updated accordingly, so six Unresolved records closed:
ELTE's previous MSCA hosting, the AgroVIR placement supervisor's title, the placement workspace and
system access, the two hosting-capacity roll-ups, and the researcher's invited talks. Five closed to
Assumed, backed by three new declarations, because they report facts about a third party that only
that third party can evidence; the sixth, invited talks, closed to a Confirmed absence on the CV plus
the operator's direct confirmation. The MSc thesis supervision withdrawal and the co-supervisor's
employment check moved records that were already Confirmed and so changed no total. One new named gap
was created rather than closed and is counted in the 11: the team the fellow joins during the
placement, which the workspace decomposition separated out. Record:
`decision_log/fieldwise-open-items-fold_2026-08-14.json`.

**Unresolved rose while the state improved.** That is the decomposition, not a regression. Revision 1
carried AgroVIR's hosting capacity as one opaque null field with all four counts missing. It is now
five named sub-records, of which one is Unresolved, and the two supervisor titles are named separately
rather than hidden inside a deferred field. The eighteenth is the D5.4 sequencing question, which AR-9
did not create but did make visible. Counting named gaps went up because fewer gaps are hidden.
Section 6 counts distinct open items instead, which stands at twelve against revision 1's twelve.

The table above reads seventeen Unresolved, not the eighteen you reviewed. Your authorisation moved
`action_confirmation` in `selected_call.json` from Unresolved to Confirmed. Nothing else moved, and the
twelve open items of section 6 are untouched.

## 6. Residual open items, by the gate they affect

Twelve distinct items are open. **None of them fails a runner gate in Phases 1 to 7.** They cost
proposal score, or they block submission, or they surface at Phase 8 only if the drafting carries them
into a section as a material claim.

A gate verdict is not a quality verdict, and the placement made the difference concrete. Five
milestones inside a 30-month timeline satisfy `phase_04_gate` whether or not any of them falls in the
placement window, so the gate never noticed that the action's last checkpoint sat at M23. AR-9 fixed
what the gate does not check.

### 6.1 Blocks no gate — costs Part B-1 §3.2, which is scored

| Item | Why it is open |
|------|----------------|
| ELTE `recent_projects_and_publications` | Deferred 2026-08-11. Only the institute can supply its own project list. CORDIS indexes ELTE at university level |
| ELTE `previous_msca_hosting` | Deferred 2026-08-11. PLANTDIGISENSE evidences an application, not a funded hosting. §3.2 must not blur the two |
| MATE `recent_projects_and_publications` | Deferred 2026-08-11. AGRIGEP, grant 101094158, is one verified line and is not the list |
| AgroVIR `relevant_track_record` | Deferred 2026-08-11. No EU-funded research participation was found. If there is none, §3.2 says so plainly |
| Miklós Maróti's title and seniority | AR-1. The name is supplied and declared. Part B-2 §5 needs the role, and the placement argument leans on the seniority |

`phase_06_gate` predicate `g07_p09` requires every instrument-mandated implementation section to be
addressed. §3.2 will be thin, not empty, and "addressed" is a low bar. The gate passes. The score does
not follow the gate.

### 6.2 Blocks no gate — the remaining placement gap

| Item | Why it is open |
|------|----------------|
| AgroVIR workspace and system access for M25-M30 | AR-2. Desk or office location, FMIS development or staging access, customer-data environment access, and the team she joins. Only AgroVIR can supply them |

This is one count of four, down from four of four at revision 1. Section 7 sets out what closed.

### 6.3 Blocks no gate — quality and drafting

| Item | Why it is open |
|------|----------------|
| The background-IP question on the DrR components | Raised by you when reframing the placement content. §2.2 records the components as the fellow's background IP, and the proposal does not address ownership of work done on them inside a commercial partner |
| `invited_talks` in the researcher profile | AR-8. Not in the CV. "Not supplied" and "there are none" are different facts, and only the second can be written into §1.4 |
| Which point in the timeline D5.4 belongs to | AR-9. MS5 at M23 says the MVP is externally evaluated under farmer conditions, and the AR-3 placement content puts the assessment producing D5.4 inside M25-M30. One of the two must give. Phase 4 owns deliverable due months, and no source states which reading the draft intended |

### 6.4 Blocks no gate — binds later, outside the run

| Item | Why it is open |
|------|----------------|
| MVCRI `signatory_authority` | Whether the institute director signs or the Agricultural Academy must. It binds at partnership-agreement time |
| AgroVIR `company_registration_number` | Two conflicting readings. The company must confirm. No value is guessed |
| The co-supervisor's ELTE contract status | MSCA requires supervision at the beneficiary. It decides whether CO_SUPERVISOR is the right token |
| Roles and titles for Takács (MATE) and Balázs (AgroVIR) | Names are known, roles are not. Predicate `g07_p08` reads the name, and Part B-2 §5 needs the role |

### 6.5 Blocks submission, not a gate

| Item | Status | Why |
|------|--------|-----|
| AgroVIR PIC | Confirmed absent | AgroVIR hosts the placement, so it appears in Part A Section 2, where every participant needs a PIC |

This one is a settled fact rather than an open question, which is why it is Confirmed on the absence
and does not sit among the eleven. Predicate `g04_p07` at `phase_03_gate` compares work-package partner
ids against the ids in `partners.json` and reads no PIC, which I verified in the implementation at
`runner/predicates/coverage_predicates.py:720`. AgroVIR passes the gate. Only the EU Participant
Register can supply a PIC. Registration is free and needs the legal name, the address and the tax
number, all three of which Tier 3 records.

### 6.6 The one place an open item can fail a gate

Gates `gate_10a`, `gate_10b` and `gate_10c` each carry a `no_unresolved_material_claims` predicate
(`g09a_p06`, `g09b_p07`, `g09c_p07`). They read the drafted section, not Tier 3. An Unresolved Tier 3
record fails one of them only if Phase 8 drafts it into a section as a material claim.

The same three gates carry `assumed_claims_are_operator_declared` (`g09a_p11`, `g09b_p12`, `g09c_p11`).
That predicate is stricter than it reads. An assumed claim must carry a `claim_id` equal to a
declaration key in `working_assumptions.json`, and its `claim_summary` must equal the declared value
exactly. The fourteen keys in section 8 are therefore the only claim ids an assumed Phase 8 claim may
use.

## 7. The AgroVIR placement after the fold

Input pack item 12 sets four counts a placement must satisfy in Part B-1. Revision 1 had none of them.

| Count | State | Detail |
|-------|-------|--------|
| Who supervises her on site | Assumed | Miklós Maróti, declared as `placement_supervisor_AgroVIR`. Title Unresolved |
| What workspace and system access she gets | **Unresolved** | Four fields named in §6.2 |
| What she does for six months | Confirmed | Four items, below |
| What she gains that ELTE cannot give | Inferred | A production FMIS environment, a commercial engineering practice, and direct contact with paying growers |

The work content is your reframe, not your first answer. "Developing further the MVP prototype" was
set aside on three grounds you stated: an MSCA placement must serve the fellow's training rather than
the company's engineering; the draft itself calls the MVP the research-to-operation demonstrator and
not the primary scientific objective (¶158); and §2.2 records the DrR components as the fellow's
background IP.

The four items are operational hardening of the prediction pipeline in a production FMIS environment;
the nine-dimension operational assessment producing D5.4; the FMIS integration roadmap written from
inside the implementing company, producing D5.5; and requirements engineering and user testing with
commercial growers. All four map onto WP5 content the draft already carries, so the placement deepens
WP5 rather than adding a strand. No task and no deliverable was invented to hold it.

Your field-access answer is recorded, but not as workspace. AgroVIR provides field access as
VALIDATION_PARTNER from M16, and WP5 tasks T5.4 and T5.5 already depend on it. It would be true had the
placement never been decided, so it evidences nothing about hosting capacity. It sits on the record as
`supplementary_field_access`, Confirmed, with that distinction stated.

Your D5.1 check is satisfied by the seeded state. MS5 at M23 requires an externally evaluated web MVP,
which cannot precede D5.1, so the MVP lands before the placement window by construction. The check is
recorded on WP5 so Phase 4 does not schedule D5.1 into M25-M30.

### The placement's verification, after AR-9

The window now carries a milestone and a named evidence base. MS6 sits at M30 with the criterion
"non-academic placement completed: the operational assessment and the FMIS integration roadmap are
delivered from inside the host company", and `placement_verification` names D5.4 and D5.5 as what
carries it.

Seeding MS6 exposed a conflict that was already in the state. MS5 at M23 says the web MVP is
"externally evaluated under farmer/operational conditions", which is D5.4's content, and the AR-3
placement work content puts the nine-dimension operational assessment producing D5.4 inside M25-M30.
Input pack item 8 separately calls T5.6 the natural occupant of the placement window. D5.4 cannot be
in both places.

Either reading is defensible and neither is stated by a source. If D5.4 lands by M23, MS6 rests on
D5.5 alone and the placement deepens an evaluation already delivered. If D5.4 lands in the placement,
MS5 needs a different output, most likely D5.2 or D5.3. Deliverable due months are Phase 4's output, so
choosing here would fabricate a scheduling fact. It is listed in §6.3 and left to Phase 4.

## 8. Assumed facts you own

Every Assumed fact carries a declaration in `working_assumptions.json`, attributed to you and dated. A
declaration makes an assumption conscious and owned. It never makes a fact Confirmed.

| Key | Value | Declared | What it backs |
|-----|-------|----------|---------------|
| `family_allowance` | does not apply | 2026-08-11 | Unit-cost budget, gate_09 |
| `long_term_leave_allowance` | does not apply | 2026-08-11 | Unit-cost budget, gate_09 |
| `special_needs_allowance` | does not apply | 2026-08-11 | Unit-cost budget, gate_09 |
| `person_months_MATE` | 2.4 | 2026-08-11 | WP seed partner effort |
| `person_months_MVCRI` | 1.5 | 2026-08-11 | WP seed partner effort |
| `person_months_AgroVIR` | 3.0 | 2026-08-11 | WP seed partner effort |
| `person_months_ELTE_supervisor` | 2.5 | 2026-08-11 | WP seed partner effort |
| `person_months_ELTE_co_supervisor` | 2.0 | 2026-08-11, confirmed 2026-08-12 | WP seed partner effort |
| `contact_person_MATE` | Dr. Sándor Takács | 2026-08-11 | `partners.json`, `g07_p08` |
| `contact_person_AgroVIR` | Zsuzsanna Balázs | 2026-08-11 | `partners.json`, `g07_p08` |
| `placement_supervisor_AgroVIR` | Miklós Maróti | 2026-08-12 | AgroVIR placement hosting |
| `contact_email_MVCRI` | vinelina@abv.bg | 2026-08-11 | `partners.json` |
| `researcher_orcid` | 0009-0008-3761-3106 | 2026-08-11 | Researcher profile |
| `mobility_eligibility` | 7.05 months against a 12-month cap | 2026-08-11 | Eligibility. See below |

### The C5 mobility override

You overrode contradiction C5 on 2026-08-11. The declaration records the override as an operator
position, not as a confirmed fact, because the underlying facts did not change and no new evidence was
supplied.

The stated basis is that the CV's residence lines will be rectified, which removes 8.76 of the 15.81
months the CV counts on its face. Two periods survive any revision and are fixed points: KPMG Global
Hungary as employer of record, 4.03 months, and the ELTE-documented Erasmus mobility, 3.02 months.

The rectified CV must stay consistent with both, and with ELTE's own Erasmus records. Eligibility is
self-declared at submission and verified at grant agreement preparation, so the exposure grows with
success rather than shrinking. This packet carries the override, its basis and its date. It is not
promoted to Confirmed here or anywhere downstream.

## 9. Open checks that carry no status

These are named in Tier 3 record notes. They are not Unresolved records, because nothing is missing
from a field. Each one is an action against an external party.

| Check | Where it is recorded |
|-------|----------------------|
| MATE's public or private flag must match its EU Participant Register self-declaration | `partners.json` MATE `entity_type_open_check` |
| The ELTE equipment inventory is a 2025 snapshot and needs a currency check | `capabilities.json` ELTE `infrastructure_note` |
| The ELTE Department of Meteorology's own capacity is described nowhere, so the co-supervisor has no institutional capacity behind him | `capabilities.json` ELTE `infrastructure_note` |
| The five-year MATE hyperspectral archive is described in one clause, and it is the proposal's most important asset | `capabilities.json` MATE `infrastructure_note` |
| MVCRI's experimental capacity is understated as "secondary access to field trials" | `capabilities.json` MVCRI `infrastructure_note` |
| The AgroVIR line "MCP validaation via the agrovir software" was rendered readable at the fold and needs your confirmation | `capabilities.json` AgroVIR `infrastructure_and_farm_access_note` |
| §3.2 must state what ELTE's hosting arrangements are during M25-M30 | `capabilities.json` ELTE `hosting_arrangements_note` |
| The DrR prototype has no publication, preprint or repository, so §1.1.3 is either uncited or the prototype is deposited | Item 10 record in the checklist |
| The PLANTDIGISENSE Evaluation Summary Report is not in Tier 3 and is named the highest-value missing input to Phase 8 | `capabilities.json` researcher profile |
| Primary supervision of an ELTE MSc thesis may need a formal status the fellow will not hold | EI-06 mapping note in `impacts.json` |
| §3.2 holds 0.25 pages in the item 14 budget, and the remedy was left open | Item 14 record in the checklist |

## 10. Which gates the seeded state can pass

Tier 3 supplies gate inputs. Most predicates read the Tier 4 output the node produces, which no packet
can pre-judge. The table states what the seeded state supplies and what remains with the run.

| Gate | Seeded state supplies | Verdict |
|------|----------------------|---------|
| `gate_01_source_integrity` | `selected_call.json`, the MSCA work programme PDF, call extract HORIZON-MSCA-2026-PF-01-01, application form `af_he-msca-pf_en.pdf`, evaluation form `ef_he-msca_en.pdf` | Can pass |
| `phase_01_gate` | Six Tier 2B extracted files, all non-empty and surviving the purge. `g02_p13` compares `selected_call.json` against them | Can pass. The node must still write the evaluation matrix and compliance checklist |
| `phase_02_gate` | The concept note and strategic positioning the mapping is built from | Depends on the node. `topic_mapping.json` and `compliance_profile.json` do not yet exist by design |
| `phase_03_gate` | Seven partner ids for `g04_p07`. Five work packages, 32 tasks, 15 deliverables, six acyclic dependency edges | Can pass |
| `phase_04_gate` | Task months inside M1-M30 against `project_duration_months` 30. `milestones_seed.json` populated for `g05_p07`, now with six milestones | Can pass. Two things to watch: the one-FTE-per-month check over M16-M21, where WP4 and a heavier WP5 overlap, and the D5.4 sequencing question of §6.3 |
| `phase_05_gate` | All six Tier 2B expected impacts mapped for `g06_p04`. Eleven KPIs, each naming a deliverable, for `g06_p05` | Can pass |
| `phase_06_gate` | Thirteen risks, the item 3 ethics answers, the item 4 governance structure with five steering points, and management roles that all resolve in `partners.json` | Can pass. §3.2 will be thin under `g07_p09` |
| `gate_09_budget_consistency` | `project_duration_months` 30 Confirmed, `host_country` HU Confirmed, the HU coefficient 78.7 in Tier 2B `unit_cost_rates.json`, and all three optional lines declared | Can pass. Every budget component resolves to Confirmed or operator-declared Assumed, which is what `g08_uc03` requires |
| `gate_10a` / `gate_10b` / `gate_10c` | Fourteen declarations for the W1 predicate | Depends on the drafting. Section 6.6 states the two predicates at risk |
| `gate_10d`, `gate_11`, `gate_12` | Nothing from Tier 3 directly | Depends on Phase 8 |

Phases 1 and 2 are ticket 8. Phases 3 to 7 are ticket 9. Phase 8 and the export are ticket 10.

## 11. Corrections applied while building this packet

Three, all consistency corrections rather than new content.

`project_summary.json` described the C5 mobility question as deferred. You overrode it on 2026-08-11,
and the ticket 6 fold corrected the same sentence in `selected_call.json` and left this copy standing.
The line now records the override and points at the declaration.

The `placement_period_monitoring` record and the item 4 governance record disagreed about the Steering
Group schedule once AR-7 added M27. Both now carry five meeting points, and the schedule itself has one
home, `milestones_seed.json` under `steering_decision_points`.

Item 6's accepted text ties the Career Development Plan reviews to the item 4 steering points with the
word "alongside". AR-7 made that clause false by adding a fifth steering point against four reviews.
AR-10 resolved it by adding an M27 review rather than by dropping the clause. Five records carried the
old count and all five now read five: item 6's `review_points`, K11's target, the two D1.3 notes, and
the `steering_decision_points` consequence. The item 6 decision-log record keeps its 2026-08-11 text
and carries an `amended_by` block, because a decision record states what was decided, not what is
currently true.

## 12. What authorisation recorded

You authorised the seed on 2026-08-12. Two files carry the act.

`docs/tier4_orchestration_state/decision_log/fieldwise-authorisation_2026-08-12.json` holds the date,
your instruction, the scope, the twelve items accepted as open, the fourteen declarations that stand,
the C5 override carried without promotion, and what the authorisation does not do. It also fingerprints
the fifteen Tier 3 artifacts it authorised, so a later reader can tell whether what ran is what you
approved.

`selected_call.json` points `action_confirmation_ref` at that record and moves
`action_confirmation_status` to Confirmed. The field had dangled since ticket 1 archived the superseded
run's authorisation record. No runner predicate reads it, so neither the pending state nor this one
moves a gate. Ticket 7 blocked the run on it, and that block is released.

**What the authorisation does not do.** It changes no record status. The twelve open items of section 6
stay open, the C5 override stays Assumed, and the thirty-four Assumed records stay Assumed. It waives
no gate and grants no permission to fill a gap. A gate that fails on incomplete input still fails, which
is CLAUDE.md §12.4 working as intended.

**Ticket 8 is unblocked.** Phases 1 and 2 may run.
