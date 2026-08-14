# FIELDWISE — placeholder correction sheet

**Written 2026-08-14. Three items. Correct these by hand in the final draft.**

Nine records were closed today so n08a could complete. Six of them are real closures and need
nothing from you. **Three are stand-ins.** They are listed first, because they are the only part of
this sheet that is work.

---

## The three placeholders

Each one is a declaration in `docs/tier3_project_instantiation/working_assumptions.json` and is
registered there under `_operator_placeholders`. Removing a key returns its field to `Unresolved`
and re-blocks whatever it unblocked — that is deliberate, not a regression.

### 1. The team she joins at AgroVIR — **correct this one first**

| | |
|---|---|
| **Written** | "The AgroVIR product development team responsible for the FMIS platform." |
| **Declaration key** | `placement_team_AgroVIR` |
| **Records** | `consortium/capabilities.json` → `hosting_capacity_for_the_placement.workspace_and_system_access.team_she_joins` |
| **Reaches** | Part B-1 §1.3 (the placement argument), Part B-2 §5 |
| **Ask AgroVIR** | What team does she sit with during M25–M30, and who else is on it? |

This is the field an evaluator uses to test whether the placement is real, which is why it is first.
The placeholder is not a guess at a name — it identifies the team by function, derived from the
access and work content already on the record (FMIS dev/staging, customer-data environment,
operational hardening of the pipeline, the integration roadmap). AgroVIR may well call it something
else, split it across two teams, or seat her with an agronomy or customer-facing group instead.

### 2. Zsuzsanna Balázs's title

| | |
|---|---|
| **Written** | "Project manager" |
| **Declaration key** | `contact_person_title_AgroVIR` |
| **Records** | `consortium/partners.json` → `VALIDATION_PARTNER.contact_person_title`; `consortium/capabilities.json` → AgroVIR `key_people` |
| **Reaches** | Part B-2 §5 |
| **Ask AgroVIR** | What is her actual job title? |

Chosen to be the least specific title consistent with what the record already establishes — that she
is the company's project contact and holds its Steering Group seat — so being wrong costs a job
title, not a claim.

**One thing to watch in drafting.** Miklós Maróti's "senior research officer" is *not* a placeholder —
it is your answer of 2026-08-14 about a real person, and §1.3 leans on that seniority for the
placement's training rationale. Ms. Balázs's title carries no argument. If a draft starts resting an
argument on her seniority, that is the placeholder leaking.

### 3. MVCRI signatory authority

| | |
|---|---|
| **Written** | "The Director of the institute signs, with the Agricultural Academy countersigning where its statutes reserve the signature to the Academy. The post is held by Prof. Dr. Daniela Ganeva." |
| **Declaration key** | `signatory_authority_MVCRI` |
| **Records** | `consortium/partners.json` → `TRANSFER_PARTNER.signatory_authority` |
| **Reaches** | Nothing in Part B. Binds at partnership-agreement time. |
| **Ask MVCRI** | Does the institute sign a partnership agreement, or must the Agricultural Academy? |

Lowest urgency of the three — it reaches no proposal section, so this placeholder buys a phase pass
and nothing an evaluator reads. The unsettled part is a question of Bulgarian law and of the
Academy's statutes; institutes of the Academy are structural units, so it can go either way. The
placeholder takes the institute-signs reading because that is wrong in the smallest way if the
Academy turns out to hold the signature alone.

**Keep the name when you correct the rest.** Prof. Dr. Daniela Ganeva is named as director of the
institute in the Agricultural Academy's own press record — that half is sourced, not invented. It is
a 2024-era source, so re-check before anything is actually signed.

---

## The six that are not placeholders — do not "correct" these

| Record | Status | What happened |
|---|---|---|
| ELTE recent publications | **Confirmed** | Your four ORCID items. Each DOI checked against the publisher's own record — title, journal, date and author list matched every time, and Prof. Jung is an author on all four. |
| MATE recent projects & publications | **Confirmed** | Your three ORCID items, likewise all four fields verified per DOI, plus AGRIGEP (101094158) which was already CORDIS-verified. |
| AgroVIR company registration number | **Confirmed** | **You did not need a placeholder.** See below. |
| AgroVIR relevant track record | Assumed | A stated absence — no EU-funded research participation, plus the commercial footprint. This is the form input pack item 12 prescribed for exactly this case. Turning it into a positive research claim would be a downgrade. |
| Mobility eligibility | Assumed | Restated unconditionally. See below. |
| `part_b2_capacity_detail` | Assumed | Derived roll-up. It holds no fact of its own and moved because the fields under it moved. |

### AgroVIR's registration number resolved to a fact: **13-09-200433**

You asked for a placeholder and one was not needed. The Hungarian company register carries an entity
matching **every** discriminating field already in your Tier 3 record:

- legal name — AGROVIR Üzletviteli Tanácsadó Korlátolt Felelősségű Társaság
- seat — 2040 Budaörs, Kinizsi utca 30
- tax number — 14000838-2-13
- main activity — TEÁOR 70.20

Its cégjegyzékszám is **13-09-200433**. The `01-09-884056` reading is a Budapest-court record and
matches none of the four. The prediction in your own input pack note — that the tax number's county
code points to Pest and therefore to a 13- prefix — is what carried the identification. Recorded
`Confirmed`, no declaration behind it.

*Residual:* if the company was registered elsewhere before moving to Budaörs, the older number may
still appear on old documents. Part A takes the current one.

### Mobility eligibility — conditionality lifted, status still `Assumed`

Your confirmation was applied everywhere the condition appeared: `working_assumptions.json`,
`capabilities.json`, `confirmation_checklist.json` (including the `MOBILITY_ELIGIBILITY`, `HOST` and
`FELLOWSHIP_TYPE` records), `selected_call.json` and `project_summary.json`. HOST and FELLOWSHIP_TYPE
are no longer `CONFIRM — CONDITIONAL`, and nothing anywhere now waits on a rectified CV.

**It stays `Assumed`, and that is not a demurral.** `runner/working_assumptions.py` stamps
`DECLARED_STATUS = "Assumed"` on every declaration wherever it surfaces. Promoting it would make a
green bought by declaration indistinguishable from one bought by evidence, which is the one thing
that substrate exists to prevent. The record now reads as a settled operator position rather than an
open question with a deadline, which is the substantive change you asked for.

Two things stay true regardless: Part A's residence declaration is the binding statement and must say
what this record says; and the two periods documented outside the CV — KPMG Global Hungary (4.03
months) and the ELTE Erasmus mobility (3.02 months) — are fixed points that any later residence
evidence must remain consistent with. Eligibility is verified at grant agreement preparation, so the
exposure scales with success.

---

## What is still genuinely open — and was not closed today

None of these was on your list. They are the thin capacity descriptions *underneath* the fields that
were deferred, and closing the deferrals did not touch them.

1. **MATE's five-year hyperspectral archive.** Years covered, instrument make and model, number of
   campaigns and plots, accompanying soil and meteorological data. Gap G2 and hypothesis H2 rest on
   an asset the proposal describes in a single clause. The three new MATE publications evidence the
   group's competence; they describe no archive. **This is worth more to the score than all three
   placeholders combined.**
2. MVCRI's WP4 experimental capacity — trial area, tomato germplasm held, measurement instruments.
3. ELTE Department of Meteorology capacity — the co-supervisor is named with no institutional
   capacity behind him.
4. The ELTE equipment inventory's currency check (it is a 2025 snapshot), and what ELTE's hosting
   arrangements are during M25–M30 while she is on placement.
5. The background-IP question on the DrR components — a §2.2 drafting matter, not a Tier 3 fact.
6. Which point in the timeline D5.4 belongs to — MS5 at M23 versus the M25–M30 placement window.
   Phase 4 owns it.

---

## Files changed

| File | What changed |
|---|---|
| `consortium/capabilities.json` | ELTE + MATE publications; AgroVIR track record; Balázs title; the placement team; mobility position; `part_b2_capacity_detail` rewritten |
| `consortium/partners.json` | MVCRI signatory authority; AgroVIR registration number; Balázs title |
| `working_assumptions.json` | 4 declarations added (17 → 21); `mobility_eligibility` restated; `_operator_placeholders` register added |
| `call_binding/confirmation_checklist.json` | Item 12 closed; AR-1, AR-2, AR-8 closed; `open_for_authorisation` rewritten; HOST/FELLOWSHIP_TYPE conditionality lifted; summary counts corrected |
| `call_binding/selected_call.json` | Mobility conditionality lifted from `notes` |
| `project_brief/project_summary.json` | Mobility conditionality lifted from `spine_note` |
| `docs/tier4_orchestration_state/decision_log/fieldwise-placeholder-fold_2026-08-14.json` | New — the fold record for all of the above |

**Verified:** `runner.working_assumptions.load_working_assumptions` parses the edited file and returns
21 declarations, no duplicate keys, all four required fields present on every entry, every entry
rendering at `Assumed` in both `as_surface()` and `as_canonical_pack_entries()`. All six edited files
parse. No record in `capabilities.json` or `partners.json` carries an `Unresolved` status.

**Not verified:** no phase was run. This says the Tier 3 inputs to n08a are complete and well-formed.
It does not say n08a passes.
