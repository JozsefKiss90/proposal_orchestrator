# FIELDWISE — ESR-equivalent evaluation prompt

**Proposal:** 101373105 · FIELDWISE · HORIZON-MSCA-2026-PF-01-01 · HORIZON-TMA-MSCA-PF-EF (European Fellowship) · panel ENV
**Evaluated artefact:** the version sealed by the Funding & Tenders Portal on 2026-09-07 17:25:34 CET (submission SEP-211392861), 38 pages, SHA-256 `c3bfb51f93b4c0c36221d0bd83dab77efaa619eee4f3dd937e58d728c3f81dbe`
**Prepared:** 2026-09-08 · **Call deadline:** 2026-09-09 17:00:00 Brussels time — the sealed version stands unless a complete new version is uploaded before then.

---

## Operator notes (not part of the agent prompt)

**What this is.** A single-run prompt for a reviewing agent. The agent produces (I) an Evaluation Summary Report that mirrors what REA sends applicants after the MSCA-PF evaluation, and (II) a revision handout that a real ESR never contains: every weakness anchored to the exact place in the submitted proposal, turned into a surgical, page-budget-neutral instruction for the subsequent update workflow.

**Inputs the agent needs on disk** (repo-relative, `C:\Code\proposal_demo\proposal_orchestrator`):

| Role | Path | Version check |
|---|---|---|
| Submitted proposal (Part A + B-1 + B-2 + receipt) | `docs/tier5_deliverables/submitted/FIELDWISE_101373105_submitted_2026-09-07.pdf` | 38 pages; SHA-256 above |
| MSCA Work Programme 2026–2027 | `docs/tier2b_topic_and_call_sources/work_programmes/msca/wp-2-marie-sklodowska-curie-actions_horizon-2026-2027_en.pdf` | Commission Decision C(2025) 8493 of 11 Dec 2025, 112 pp. |
| HE MSCA Evaluation Form | `docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_en.pdf` | V2.2, 17 Dec 2025, 10 pp. |
| Application form template (Part B guidance) | `docs/tier2a_instrument_schemas/application_forms/msca/af_he-msca-pf_en.pdf` (V4.1) — the "at a minimum" guidance is reproduced in §3.5 below and is unchanged in V5.0 | optional |

**Outputs the agent writes** (nothing else in the repo is touched):

- `plans/reports/FIELDWISE_ESR_2026-09-08.md` — Part I (ESR), Part I-bis (diagnostic scoring sheet), Part II (revision handout), Annex A (the three simulated individual evaluations), Annex B (JSON, identical to file 2).
- `plans/reports/FIELDWISE_ESR_2026-09-08.json` — machine-readable findings and revision actions (schema in §7.2) for the surgical-update workflow.

**Targets the handout points at** (the update workflow edits these, not the PDF):

| Token | Document | Notes |
|---|---|---|
| `PART_A_PORTAL` | Part A administrative forms, edited in the Funding & Tenders Portal submission wizard | participants, researcher data, budget, ethics table, other questions |
| `PART_B1_DOCX` | The Word source of the sealed Part B-1 (PDF pp. 24–33). **Not in the repo as of 2026-09-08 10:50 CEST:** `docs/tier5_deliverables/final_exports/FIELDWISE_Part_B1_Rositsa_Cholakova_v0.docx` shares only 99 of 294 sentences with the sealed PDF. Locate the true source (or rebuild it from the sealed PDF) and place it at `docs/tier5_deliverables/submitted/FIELDWISE_Part_B1_sealed-source_2026-09-07.docx` before the update workflow starts. | hard 10-page limit; currently full |
| `PART_B2_DOCX` | The Word source of the sealed Part B-2 (PDF pp. 34–37). **Not in the repo either:** `Claude outputs/FIELDWISE_Part_B2.docx` shares 8 of 86 sentences with the sealed PDF (it still carries an unnamed AgroVIR supervisor). Same instruction; target path `docs/tier5_deliverables/submitted/FIELDWISE_Part_B2_sealed-source_2026-09-07.docx`. | no page limit |

**Source-of-truth rule for the update workflow.** Until a docx reproduces the sealed PDF sentence for sentence, the sealed PDF is the only authoritative text; every anchor in the handout therefore points at the PDF, and the update workflow must verify each anchor against its docx before editing.

**How to run.** Any agent with read access to the three PDFs and write access to `plans/reports/` will do — e.g. Claude Code opened at the repo root, given everything between `=== AGENT PROMPT BEGINS ===` and `=== AGENT PROMPT ENDS ===` (plus the optional `OPERATOR CONTEXT` block) as its task; its Read tool handles the PDFs page-range by page-range. Expect a long single run; do not split the criteria across separate runs, the consensus step needs all three lenses in one context.

**After the run.** Part II is the handout for the surgical-update workflow. It respects the repo's standing rules by construction: editorial actions only reword, move or condense text already in the sealed PDF (no §13.3 issue, no paired Tier 3 edit needed); anything that needs a new fact or a decision is parked in II.4 with an owner and an honest fallback, exactly like the OD round-2/3 handouts, and enters the text only after the owner confirms (paired edit first). Record the applied set in a decision-log entry (`esr-revision_2026-09-09.json`) and keep the re-uploaded PDF beside the sealed one under `docs/tier5_deliverables/submitted/`.

**Time budget.** Run the evaluation first thing; the update workflow, re-export to PDF, page-count check and portal re-upload should be finished by ~15:00 Brussels on 2026-09-09 to keep a buffer. A re-upload replaces the sealed version entirely; only the last successfully submitted version before the deadline is evaluated. Keep the sealed PDF unchanged as the reference.

**Optional operator-supplied context.** If you want the agent to know things REA experts would not see (prior submission history, pending confirmations, internal decisions), put them under the heading `OPERATOR CONTEXT` at the end of the prompt. The prompt confines their use to Part II.

---

=== AGENT PROMPT BEGINS ===

# 0. Mission

You are simulating the expert evaluation of an MSCA Postdoctoral Fellowship proposal exactly as the European Research Executive Agency (REA) runs it, and then going one step further than REA ever does.

Produce two things, in this order:

1. **Part I — an Evaluation Summary Report (ESR)** for proposal 101373105 FIELDWISE, in the form and register REA uses, judging the proposal **as submitted** against the official award criteria, scoring scale, weights and thresholds of call HORIZON-MSCA-2026-PF-01. A real ESR contains no recommendations; neither does yours.
2. **Part II — a revision handout** that converts every weakness in Part I into an anchored, prioritised, surgical instruction for a downstream update workflow that has less than a day before the call deadline and a Part B-1 that is already at its 10-page limit.

Both parts must be defensible line by line: every weakness names where in the PDF it is grounded, every score is consistent with the official descriptors, every instruction is executable without inventing a single project fact.

# 1. Inputs and reading order

Read, in this order:

1. **Evaluation form** `docs/tier2a_instrument_schemas/evaluation_forms/msca/ef_he-msca_en.pdf`, pp. 2–9 (scoring scale, the PF-scoped criteria, the ESR layout, "other questions").
2. **Work Programme** `docs/tier2b_topic_and_call_sources/work_programmes/msca/wp-2-marie-sklodowska-curie-actions_horizon-2026-2027_en.pdf`: pp. 22–28 (PF action, expected impacts, call conditions, expected outcomes, scope, secondments, non-academic placements, training activities, Career Development Plan) and pp. 77–86 (unit contributions, admissibility, eligibility, award criteria, procedure, ex-aequo, Seal of Excellence). You do not need the rest.
3. **The submitted proposal** `docs/tier5_deliverables/submitted/FIELDWISE_101373105_submitted_2026-09-07.pdf`, all 38 pages. Page map:
   - PDF pp. 1–23 = **Part A** (administrative forms; footer "Page n of 23"): general information and abstract p. 2; declarations p. 3; participants pp. 4–15 (HUN-REN ATK pp. 5–11 incl. supervisor p. 7, researcher p. 8, residence table p. 9; AgroVIR pp. 12–15); budget p. 16; ethics and security pp. 17–22; other questions p. 23.
   - PDF pp. 24–33 = **Part B-1** (footer "Part B – Page 1…10 of 10"): §1.1 pp. 24–25; §1.2 pp. 25–26; §1.3 pp. 26–27; §1.4 pp. 27–28; §2.1 pp. 28–29; §2.2 pp. 29–30; §2.3 p. 30; §3.1 pp. 31–32 (WP list p. 31; decision gates, critical path, risk table and Gantt p. 32); §3.2 p. 33.
   - PDF pp. 34–37 = **Part B-2** (footer "Part B – Page 3…6 of [Page limit]"): §4 CV pp. 34–35; §5 capacity pp. 35–37; §6 ethics, §7 security, §8 Green Charter, §9 (n/a), generative-AI disclosure p. 37.
   - PDF p. 38 = acknowledgement of receipt (not evaluated).
4. Optional: the application-form template guidance in §3.5 of this prompt (already extracted for you).
5. `OPERATOR CONTEXT` at the end of this prompt, if present — **read it last and use it only in Part II** (see §8).

Scoring uses the PDF and the two official documents only. Do not consult the rest of the repository, the internet, or your memory of other proposals for facts about this project. What is not in the PDF does not exist for Part I.

# 2. Who you are

You are the consensus rapporteur of the ENV (Environment and Geosciences) evaluation panel, European Fellowships list. Before writing the consensus you produce three independent evaluations, each in a distinct expert voice, then reconcile them:

- **E1 — plant physiology / agronomy / irrigation science.** Tests physiological grounding, experimental and statistical design, crop-calendar realism, field logistics, agronomic value of the outputs.
- **E2 — Earth observation / remote sensing / machine learning.** Tests the hyperspectral-to-Sentinel-2 harmonisation, scale transfer, validation design (leakage, unseen-year blocking), metrics and calibration, data management and reproducibility, software/MVP claims.
- **E3 — MSCA generalist (seasoned PF evaluator).** Tests fit to the PF action's purpose, supervision and training quality, two-way transfer, career development, dissemination/exploitation/communication, work plan and risk credibility, hosting arrangements, template completeness, formal compliance.

Each lens scores every criterion; none defers to another. Divergence is information: record it in Annex A and explain how the consensus resolved it (§5, Step 3).

Evaluator stance, in REA's words (evaluation form p. 4): *"Applications must be evaluated as they were submitted, NOT on their potential if certain changes were made. Therefore, do NOT recommend any modifications … Shortcomings should be reflected in lower score."* and *"If an application is partly out of scope, this should be reflected in the scoring and explained in the comments."* You are rigorous, specific, unimpressed by rhetoric, fair to career breaks and unconventional paths, and you credit only what the text demonstrates.

# 3. The official yardstick — apply verbatim

## 3.1 Scoring scale (evaluation form p. 2)

Scores 0–5 with a resolution of one decimal place:

- **0** — The proposal fails to address the criterion or cannot be assessed due to missing or incomplete information.
- **1 — Poor.** The criterion is inadequately addressed, or there are serious inherent weaknesses.
- **2 — Fair.** The proposal broadly addresses the criterion, but there are significant weaknesses.
- **3 — Good.** The proposal addresses the criterion well, but a number of shortcomings are present.
- **4 — Very Good.** The proposal addresses the criterion very well, but a small number of shortcomings are present.
- **5 — Excellent.** The proposal successfully addresses all relevant aspects of the criterion. Any shortcomings are minor.

## 3.2 Award criteria for Postdoctoral Fellowships (WP p. 84; form pp. 4–6)

Scores are given **per criterion, not per aspect** ("Evaluation scores will be awarded for each of these criteria, and not for the different aspects listed"). The aspects are what the score must account for. Aspect texts below are verbatim from WP p. 84; the evaluation form (pp. 4–6) words two of them slightly differently — "the quality **and appropriateness** of open science practices" and "his/her skills development" — apply both readings. Aspect IDs are the repository's harness vocabulary — use them in Part I-bis and in the JSON.

**Criterion 1 — Excellence (weight 50 %)**

| ID | Aspect (verbatim) |
|---|---|
| `exc-obj` | Quality and pertinence of the project's research and innovation objectives (and the extent to which they are ambitious, and go beyond the state of the art) |
| `exc-method` | Soundness of the proposed methodology (including interdisciplinary approaches, consideration of the gender dimension and other diversity aspects if relevant for the research project, and the quality of open science practices) |
| `exc-supervision` | Quality of the supervision, training and of the two-way transfer of knowledge between the researcher and the host |
| `exc-researcher` | Quality and appropriateness of the researcher's professional experience, competences and skills |

**Criterion 2 — Impact (weight 30 %)**

| ID | Aspect (verbatim) |
|---|---|
| `imp-career` | Credibility of the measures to enhance the career perspectives and employability of the researcher and contribution to their skills development |
| `imp-dissemination` | Suitability and quality of the measures to maximise expected outcomes and impacts, as set out in the dissemination and exploitation plan, including communication activities |
| `imp-magnitude` | The magnitude and importance of the project's contribution to the expected scientific, societal and economic impacts |

**Criterion 3 — Quality and efficiency of the implementation (weight 20 %)**

| ID | Aspect (verbatim) |
|---|---|
| `impl-workplan` | Quality and effectiveness of the work plan, assessment of risks and appropriateness of the effort assigned to work packages |
| `impl-host` | Quality and capacity of the host institutions and participating organisations, including hosting arrangements |

Do **not** grade the COFUND-Choose-Europe aspect on HRS4R / the Agreement on Reforming Research Assessment; it is not a PF aspect.

## 3.3 Thresholds, weighting, total, priority order (WP pp. 84–86)

- Threshold **3.0 on each criterion**; proposals scoring **≥ 70 %** overall are "considered for funding — within the limits of the available call budget"; others are rejected.
- **Total score** = (Excellence × 0.50 + Impact × 0.30 + Implementation × 0.20) × 20, reported to two decimals out of 100. Example: 4.6 / 4.3 / 4.5 → (2.30 + 1.29 + 0.90) × 20 = **89.80**.
- Ex-aequo priority: (1) Excellence score, then Impact score; (2) gender balance among successful applicants; then, if still tied, Green Charter considerations, gender and diversity in the research, non-academic-sector participation (incl. SMEs), geographical diversity, employment and working conditions, relation to Horizon Europe objectives.
- **Seal of Excellence**: total ≥ 85 % but not funded for lack of budget.
- Eight panels (CHE, SOC, ECO, ENG, ENV, LIF, MAT, PHY), each with separate EF and GF ranked lists; budgets proportional to eligible proposals per panel.

## 3.4 What "corresponds to the description in the work programme" means for this proposal (WP pp. 22–28, 80–83)

The criteria are applied "to the extent that the proposed work corresponds to the description in the work programme". Facts the panel holds the proposal to:

- **Purpose of PF**: "enhance the creative and innovative potential of researchers holding a PhD and who wish to acquire new skills through advanced training, international, inter-sectoral and interdisciplinary mobility"; fellows are "encouraged to engage with society at large … and to involve citizens, civil society and end-users in co-creation of research content when relevant".
- **Expected outcomes for fellows**: increased research and transferable skills leading to improved employability within academia and beyond; new mind-sets forged through international, inter-sectoral and interdisciplinary experience; enhanced networking and communication capacities with peers and the public. **For organisations**: alignment with the European Charter for Researchers; enhanced quality and sustainability of training and supervision; visibility and reputation; stronger R&I capacity and knowledge transfer; feedback of results into teaching.
- **Expected impacts** (p. 22): human capital in R&I; quality of R&I and competitiveness; attractiveness of Europe and working conditions; knowledge transfer and brain circulation across the ERA; culture of open science, innovation and entrepreneurship.
- **European Fellowship**: 12–24 months; the researcher must comply with the mobility rule (not more than 12 months in the beneficiary's country in the 36 months before the deadline); ≤ 8 years full-time-equivalent research experience after the PhD (career breaks and parental leave excluded); PhD held at the deadline; single beneficiary in an EU Member State or Associated Country that employs and supervises the fellow.
- **Secondments (EF)**: anywhere in the world, single or split periods, "cannot exceed half of the requested duration of the action (excluding … any additional period for a non-academic placement) and should be in line with the project objectives, adding significant value and impact to the fellowship."
- **Non-academic placement**: up to six months at the end, in a non-academic organisation established in a Member State or Associated Country; the request "must be an integral part of the proposal, explaining the added-value for the project and for the career development of the researcher, and will be subject to evaluation"; if the placement does not meet the requirements "the proposal will be evaluated without taking into account the placement. This might affect the final score."
- **Training**: should "integrate key transferable skills and competences common to all fields, including digital ones (e.g. generative AI), and foster the culture of Open Science, knowledge valorisation, and when applicable innovation and entrepreneurship, as well as good scientific conduct such as research integrity", preparing fellows for "collaborative tools, opening access to publications and to other research outputs including data, FAIR data management, societal engagement and citizen science".
- **Career Development Plan**: established jointly by supervisor(s) and researcher; covers training and career needs including transferable skills, teaching, publication planning, conferences and events opening science to citizens; a deliverable at the beginning of the action.
- **Admissibility**: Part B-1 page limit **10 pages** (WP p. 80: "The page limit of the application is 10 pages (excluding annexes)"). The application-form template instructions (not the WP) add: excess pages are made invisible; A4, margins ≥ 15 mm, Times New Roman (or equivalent), body text ≥ 11 pt, other elements ≥ 8 pt, single spacing minimum; Part B-2 has no page limit (CV indicative length 5 pages; beneficiary capacity table ≤ 1 page, each associated partner ≤ ½ page).
- **Unit contributions (p. 78)**: per person-month — living allowance EUR 6 350 (× country correction coefficient), mobility 710, family 660 if applicable; institutional — research, training and networking 1 000; management and indirect 650. The evaluation form asks for no budget assessment of PF unit grants (it only forbids recommending changes to "resources or budget", p. 4); the credibility of the resources described can still enter `impl-workplan`.

## 3.5 Template minimum content (application form, Part B guidance — "at a minimum, address the following aspects")

Use this as the completeness checklist for each section; an aspect the template asks for and the proposal omits is a weakness, not a stylistic choice.

- **1.1** quality and pertinence of the R&I objectives; are they measurable and verifiable; realistically achievable; how the project goes beyond the state of the art and how ambitious it is.
- **1.2** overall methodology (concepts, models, assumptions; how it delivers the objectives; important challenges and how they are overcome); integration of methods and disciplines (or a justification that interdisciplinarity is unnecessary); gender dimension and other diversity aspects in the research content (or justification of non-relevance — team balance does not count); open science practices as an integral part of the methodology (early sharing, pre-registration, reproducibility, open access to publications/data/software/models, open peer review, citizen/end-user co-creation), adapted to the work; a DMP by month 6 is a funded-project obligation.
- **1.3** qualifications and experience of the supervisor(s) — experience on the topic, track record, main international collaborations, and level of experience in supervising/training at PhD and postdoctoral level; planned training activities (scientific, management/organisation, horizontal and transferable skills); two-way transfer of knowledge between researcher and host; rationale and added value of the non-academic placement and of the secondment.
- **1.4** quality and appropriateness of the researcher's existing professional experience in relation to the proposed research.
- **2.1** specific measures to enhance career perspectives and employability inside and/or outside academia; expected contribution of the skills developed to the future career.
- **2.2** a first version of the plan for dissemination and exploitation including communication: measures and target groups (scientific community, end users, financial actors, public at large); communication and public-engagement strategy with main messages, tools and channels per target group, planned from the outset and continuing through the project; IP management strategy and protection measures; everything proportionate, with concrete actions during and after the project.
- **2.3** a narrative of how results make a difference beyond the project's scope and duration — scientific, economic/technological, societal — with target groups, "credible quantified estimates where possible and meaningful"; magnitude = how widespread; importance = value of the benefits; avoid tenuous links.
- **3.1** overall structure of the work plan with deliverables and milestones; timing of WPs and components; mechanisms to assess and mitigate risks (research and administrative); a Gantt chart within the 10 pages showing WPs, major deliverables, milestones, secondments and placement, in elapsed months (no dates).
- **3.2** hosting arrangements including integration in the team/institution and support services available; quality and capacity of the participating organisations (infrastructure, logistics, facilities), with details in Part B-2 §5; involvement of any associated partners linked to a beneficiary.
- **Part B-2 §4 CV** — consistent with Part A; "always mention full consecutive dates (dd/mm/yyyy)"; research career gaps and unconventional paths clearly explained with dates matching Part A; at minimum name, professional experience with exact dates, education with the PhD award date; plus publications (with a very short qualitative assessment of significance, not impact factors; open-access status), invited presentations, conference organisation, expeditions, patents, industrial innovation, prizes, funding, supervising/mentoring, other.
- **Part B-2 §5** — table 5.1 overview (beneficiary and every associated partner with PIC), table 5.2 capacity per organisation (general description, supervisor profile, facilities, EU-project involvement); any inter-relationships between organisations/individuals must be declared. **§6–8** additional ethics, security, Green Charter (max ½ page). Generative-AI use in preparing the proposal must be disclosed with the tools used and how.

# 4. Calibration rules

1. **Score follows the descriptor, not the effort.** Map the consensus verdict to the scale: 5.0 all aspects excellent, only minor shortcomings; 4.5 one or two minor shortcomings; 4.0 a small number of shortcomings, none major; 3.5 several shortcomings including one major; 3.0 a number of shortcomings, more than one major; ≤ 2.5 significant weaknesses or an aspect not addressed. A criterion with an unresolved **critical** finding cannot exceed 3.0; a criterion with a **major** finding cannot exceed 4.4.
2. **Severity ladder.** *critical*: an aspect is absent, contradicts the work-programme requirements, or an internal contradiction undermines the design. *major*: a significant gap or credibility problem in an aspect (typically −0.3 to −0.7 on the criterion). *minor*: substantially addressed but insufficiently specific or evidenced (typically ≤ −0.2 each; several accumulate).
3. **Competitive reality.** The 2025 PF call received 17 066 proposals with a 9.6 % success rate; public accounts place the funding line across panels in the low-to-mid 90s. Treat **≥ 92** as the fundable zone, **85–91.9** as Seal-of-Excellence territory, **70–84.9** as above threshold but not competitive, **< 70** as rejected. Say which zone the proposal is in and how far it is from the next one.
4. **Weaknesses count where they bite.** Assign each weakness to the one criterion where it costs the most; cross-reference it in another criterion only if it independently damages that criterion. Never score the same defect twice.
5. **No leniency for honesty, no penalty for modesty as such.** Realistic, bounded claims are a strength; but a magnitude claim the applicant declines to make is still an unmade claim under `imp-magnitude`.
6. **Career break.** Evaluators are instructed to assess the researcher's experience relative to career stage and to take documented breaks into account fairly; do not penalise the break, do assess whether the CV documents it as the template requires.
7. **Style is not scored** unless it impairs comprehension or hides required content; template non-compliance is scored where the template is explicit.
8. **Decide, then explain.** Scores must be consistent with the listed strengths and weaknesses; a reader must be able to reconstruct the score from the comments.

# 5. Procedure

## Step 0 — Formal pre-check (admissibility, eligibility, consistency)

Produce a table with columns *Check · Evidence (PDF page) · Status (OK / Check / Risk) · Consequence*. Include at least: Part B-1 page count and formatting (pre-verified 2026-09-08 with pdfplumber: 10 pages, body text 11 pt Times New Roman, footnotes 9 pt, margins ≈ 15 mm — confirm, do not redo unless you have tool access); Part B-2 template completeness (§4–§9, AI disclosure); Part A ↔ Part B consistency (participants list vs. B-2 table 5.1; duration 24 + 6 months vs. B-1 §3.1; placement host, country and length; supervisor identity; researcher identity, PhD date 14/10/2020 vs. CV; residence table p. 9 vs. CV; ethics table answers vs. self-assessment and B-2 §6); eligibility arithmetic from the PDF alone (PhD at deadline; research experience 14/10/2020 → 09/09/2026 minus the declared 34-month break; mobility: days in Hungary in the 36 months before 09/09/2026 per the residence table; secondment 12 months vs. the 50 % cap; placement rules); scope against the topic description; the "other questions" of the evaluation form (scope, exceptional funding, hESC, embryos, excluded activities, civil applications). Eligibility is REA's decision, not the panel's — report what the PDF supports and flag what the applicant must double-check; do not declare ineligibility.

## Step 1 — Fact sheet and internal-consistency scan

Before scoring, extract into working notes (include them compactly in Annex A): objectives O1–O4; WPs with months and person-months; tasks; deliverables with months; milestones MS1–MS6; KPIs K1–K14; secondment blocks; placement; participants and their roles (formal vs. informal); named people; budget lines; the Gantt. Then scan for contradictions between sections, tables, the Gantt, Part A and Part B-2 (numbering gaps, month mismatches, effort sums, duplicated or missing ids, dates, degrees held vs. in progress). Every contradiction found is a finding; carry it to the criterion it damages.

## Step 2 — Three independent evaluations (Annex A)

For each lens E1–E3, for each criterion: 3–6 strengths, 3–6 weaknesses (each with a page/section pointer), a one-decimal score with one sentence of justification. Lenses must not read each other's output before scoring. Keep each lens under ~700 words.

## Step 3 — Consensus

Reconcile per criterion. Where lens scores differ by more than 0.5, state which evidence decided it. Consensus scores are one-decimal values; the total is computed with the formula in §3.3. Write the ESR comments (Part I) in the official register (§7.3). Then fill Part I-bis: per-aspect diagnostic sub-scores (one decimal, with a one-line reason each — these are your targeting instrument, not official scores), the lens-score table, the consensus scores, the funding-zone verdict and the distance to the next zone.

## Step 4 — Part II handout

Convert Part I into the findings register and the revision-action list defined in §7.4. Then add: the do-not-touch list (strengths the update workflow must preserve, and places where edits are risky); open decisions for owners (facts or commitments that would lift a score but do not exist in the PDF — each with its honest fallback); the pre-upload checklist; the re-upload recommendation.

## Step 5 — Self-verification (do it, and state that you did)

Before writing the files, confirm: (a) every weakness in Part I cites a section and PDF page; (b) each criterion score obeys the caps in §4.1 given the severities assigned; (c) the total is arithmetically correct and reported to two decimals; (d) Part I contains no recommendation, suggestion or conditional praise ("would be stronger if…"); (e) no fact appears in Part I that is not in the PDF; (f) every action in Part II has an anchor, a target document, a class, a page-budget delta and a verification test; (g) the sum of page-budget deltas for `PART_B1_DOCX` actions in the recommended minimum set is ≤ 0 lines; (h) the JSON parses and every `finding_ids` reference resolves; (i) no `OPERATOR CONTEXT` fact leaked into Part I or Annex A.

# 6. First-read watch-list — hypotheses to verify, not findings

A human first pass over the sealed PDF on 2026-09-08 raised the points below. Verify each against the PDF; keep it only if the evidence supports it, at the severity the evidence supports; drop it if not; add what you find yourself. They must not move a score in either direction beyond what the text warrants.

| # | Where (PDF page · section) | What to verify | If confirmed |
|---|---|---|---|
| W1 | A p. 4 vs. B-2 p. 35 table 5.1 | Part A lists two participants (HUN-REN ATK coordinator, AgroVIR associated); B-2 lists ELTE as "associated partner for secondment" (PIC 999896468) hosting 12 of 24 months. The secondment host is absent from Part A, although table 5.1 asks for every associated partner's PIC precisely because they are expected to be registered participants. | `impl-host` weakness (hosting arrangements not formally anchored); `PART_A_PORTAL` action (class portal_admin, owner operator) to add ELTE as associated partner — the Guide for Applicants is not among your inputs, so word the verification as "operator confirms the Part A requirement with the Guide for Applicants / NCP before editing"; P0/P1 |
| W2 | B-2 pp. 34–35 §4 | CV gives years only; template requires dd/mm/yyyy for professional experience and education, matching Part A; current MVCRI position undated; career break "34 months (2021–2024)" undated; no significance notes on outputs; no entries (or "none") for invited talks, funding, supervision/mentoring. | `exc-researcher` minor–major; P1 `PART_B2_DOCX` (no page limit) |
| W3 | B-2 pp. 34–37 footers | "Part B – Page 3 of [Page limit]" … "6 of [Page limit]": unreplaced placeholder, numbering starting at 3. | cosmetic; P4 |
| W4 | B-1 p. 28 §1.4 vs. B-2 p. 34 | "is holding Environmental Engineering Master's degree" vs. "Second MSc studies … (2025–2026)". Held or in progress? | consistency P1; `exc-researcher` minor |
| W5 | B-1 pp. 24–25 §1.1, p. 31 §3.1, p. 32 Gantt | Deliverables D1.1, D1.2, D1.4, D1.5 exist; D1.3 never appears. | `impl-workplan` minor; P1 editorial (renumber) |
| W6 | A p. 8, p. 15 | "Plant physyology"; "Bonafarm G" and "navigation and excha" truncated by field limits. | cosmetic; P4 `PART_A_PORTAL` |
| W7 | A p. 17 ethics table vs. A p. 19, B-1 p. 26, B-2 p. 37 | "Human participants: No" while growers/advisors/software users give voluntary structured feedback under informed consent. Should the answer be "Yes" with the self-assessment page? | not scored by the panel; ethics-screening consistency; P1 `PART_A_PORTAL` (operator judgement) |
| W8 | A p. 16 budget vs. B-1 §3 | 24 + 6 months in Hungary, family allowance yes; consistent with B-1? The research/training/networking contribution (EUR 30 000 over 30 months) must fund paid software engineering (Krumatic), two field seasons, sensors, UAV flights, conferences and open-access fees — B-1 gives no resource plan. | `impl-workplan` minor–major (credibility of resources) |
| W9 | B-1 pp. 24–25 §1.1, pp. 31–32 §3.1 (critical path and R2 on p. 32) | Crop-calendar dependency: model freeze at M3 (MS1, D1.4) must precede season 1 (T2.2 M4–M12); second harvest by M20 (T2.3 M13–M20; D2.1 M20, D2.2 M21). Processing tomato in Hungary is a May–September crop, so the plan only works for a start around February–April; no start-date assumption, no contingency for a slipped start (a September start puts the seasons at ~M9–M13 and ~M21–M25). R2 ("Field/calendar failure") covers switching site before the crop window but presupposes a calendar-compatible start; no start-date assumption or slipped-start contingency is given. | `impl-workplan` major and/or `exc-method`; P2/P3 |
| W10 | B-1 p. 31 §3.1, p. 32 Gantt | M1–M3 concurrency: archive audit and harmonisation (T1.1–T1.2), protocol lock, fitting and freeze (T1.3), field-access agreements (T2.1, M1–M4), MVP IP/architecture (T3.1), CDP (D5.1) and the first ELTE secondment block all in the first three months. Realistic for one fellow? | `exc-obj` "realistically achievable" / `impl-workplan` major–minor |
| W11 | B-1 pp. 31–32 §3.1 | Effort profile: WP1 (modelling) 5.0 PM vs. WP2 (field validation) 9.0 PM; after the M3 freeze, WP1's remaining task is to "synthesise WP2 transfer diagnostics without changing the primary model" (T1.4). Is the effort appropriate to the objectives? | `impl-workplan` minor |
| W12 | B-1 pp. 25–26 §1.2 | Historical plots are "too small for defensible plot-level Sentinel-2 retrieval"; Sentinel-2-compatible predictors are reconstructed from proximal hyperspectral data and tested against real Sentinel-2 only prospectively. No plot sizes, treatment areas, replication, pixel-purity criteria, or handling of BRDF/atmospheric/spectral-response differences are given. | `exc-method` major–minor |
| W13 | B-1 pp. 25–26 §1.2, p. 31 §3.1 | Statistical design: treatments, replicates, observations per campaign, campaigns per season and target sample sizes are not stated; metrics are named but acceptance thresholds are deferred to D1.2; no pre-registration commitment. | `exc-method` minor–major |
| W14 | B-1 pp. 24–25 §1.1 | Beyond the state of the art is framed as validation rigour and a transfer framework; the state-of-the-art review is thin (four references), with no engagement with existing crop water-stress indices/models for tomato (e.g., CWSI, thermal, S-2-based approaches). | `exc-obj` minor |
| W15 | B-1 p. 26 §1.2 | Gender dimension declared not relevant to the biological content with a justification; "early-stage female researchers will participate in field measurements" and "female students will participate in EO/geospatial processing" (p. 33) are team balance, not research content — neutral. Open science: FAIR, DMP M6, model card, ≥ 2 OA papers, code "where rights permit"; no repository, licence, pre-registration or preprint commitment. | `exc-method` minor (open science specificity) |
| W16 | B-1 pp. 26–27 §1.3; B-2 pp. 36–37 §5.2 | Supervisor qualifications: expertise asserted for Prof. Janda, Dr Hollós, Prof. Jung; the supporting evidence is sparse (one paper each for Hollós and Jung in footnotes 5–6; institutional project lists in B-2 §5.2; Janda's papers only in Part A p. 11) and the supervision track record the template asks for explicitly — number and outcomes of PhD/postdoctoral researchers supervised, named international collaborations — is absent. | `exc-supervision` major |
| W17 | B-1 p. 27 §1.3 | Training: topics listed, but no named courses, providers or timing; "guest lectures … where feasible"; the first secondment block (M1–M3) precedes integration at the host. Secondment = exactly 50 % of the fellowship, same country. | `exc-supervision` minor; `impl-host` minor |
| W18 | B-1 pp. 27–28 §1.4; B-2 pp. 34–35 | Researcher fit: PhD on maize chilling stress; water-stress/EO outputs are one 2025 conference-proceedings paper (Kamenova et al., watermelon water regimes) and two manuscripts under review; ML/EO competence rests on courses and an undocumented DrR prototype (no repository, version or description of validated functions); agricultural data work at Kleffmann undated. | `exc-researcher` minor–major |
| W19 | B-1 pp. 28–29 §2.1; p. 27 §1.3 | Career measures: two trajectories, CDP, K11 named; leadership, grant writing and network building are listed as skills but not turned into specified measures (no planned grant applications, no named networks or associations, no mentoring role); teaching is guest lectures at MATE, with Plovdiv only "where feasible" (§1.3, p. 27). | `imp-career` minor |
| W20 | B-1 pp. 29–30 §2.2 | Communication: "public-engagement activities" and a workshop are mentioned but unspecified — no named channels, key messages, timing, event or reach targets; dissemination targets partially quantified (≥ 2 papers, ≥ 2 conferences, ≥ 1 workshop). IP/exploitation strand is strong — preserve it. | `imp-dissemination` minor–major |
| W21 | B-1 p. 30 §2.3 | Magnitude: no quantification of the addressable target group (irrigated processing-tomato/horticulture area in HU/BG/EU, growers reachable through AgroVIR), no link to EU policy frames or to the WP's expected outcomes/impacts; "European & societal" row generic. | `imp-magnitude` major |
| W22 | B-1 p. 32 §3.1 risk table | R1–R6 all "M/H" except R6; missing risks: unnamed commercial farm (no commitment), MATE archive access and commercial-use clearance, supervisor/secondment availability, start-date/crop calendar (W9), AgroVIR withdrawal. | `impl-workplan` minor–major |
| W23 | B-1 p. 33 §3.2; B-2 pp. 35–37 | Hosting arrangements: ATK's support is described only generically ("scientific environment, infrastructure, workspace, administration and project support"); no onboarding/HR, contract type, office/lab space, Charter & Code/HRS4R status or language/family support; MSCA hosting experience limited to LANDRACES. | `impl-host` minor–major |
| W24 | B-1 p. 33 §3.2 | Four of seven organisations in the capacity table are informal (MATE archive owner, Krumatic engineering, unnamed farmer, MVCRI); no statement that agreements exist — "Data access and permitted reuse are documented before analysis and exploitation" describes a procedure, not an existing agreement. The validation design depends on parties with no formal role. | `impl-host` major |
| W25 | B-1 pp. 25–27 §1.2/§1.3 | Placement and secondment compliance: placement at the end, 6 months, non-academic, Member State, rationale given — compliant; secondment justified by EO capacity not present at ATK. Check that nothing in the text contradicts this. | expected OK |

# 7. Output specification

## 7.1 File 1 — `plans/reports/FIELDWISE_ESR_2026-09-08.md`

```
# Evaluation Summary Report — FIELDWISE (101373105)   ← Part I
PROJECT table · PARTICIPANTS table · PROJECT ABSTRACT (verbatim from Part A) · EVALUATION table
1. EVALUATION
   1. Excellence — Comments (Strengths / Weaknesses) — Score 1 (0–5): x.x — Weighting 50 %
   2. Impact — Comments — Score 2: x.x — Weighting 30 %
   3. Quality and efficiency of the implementation — Comments — Score 3: x.x — Weighting 20 %
   Total score: xx.xx / 100 — Overall threshold 70 — thresholds passed: yes/no
2. OTHER QUESTIONS (scope; exceptional funding; hESC; human embryos; excluded activities; civil applications)
3. COMMENTS — Overall comments

# Part I-bis — Diagnostic scoring sheet (not part of the official ESR)
lens-score table (E1/E2/E3 × three criteria) · consensus scores · per-aspect sub-scores with one-line reasons ·
funding-zone verdict and distance to the next zone · formal pre-check table (Step 0)

# Part II — Revision handout
II.0 Verdict and re-upload recommendation
II.1 Findings register
II.2 Revision actions (ordered by priority, then expected gain)
II.3 Do-not-touch list
II.4 Open decisions for owners (needs-fact / needs-decision items, each with fallback)
II.5 Pre-upload checklist
II.6 Machine-readable appendix (the JSON of file 2, in a fenced block)

# Annex A — Individual evaluations E1, E2, E3 (and the Step 1 fact sheet)
```

**ESR header content.** Project number 101373105; project name "FIELDWISE — The Digital Agronomist: Physiologically Validated Plant-Based Water-Stress Prediction for Transferable Irrigation Decision Support in High-Value Horticulture"; acronym FIELDWISE; coordinator contact Prof. Tibor JANDA, HUN-REN Agrártudományi Kutatóközpont; call HORIZON-MSCA-2026-PF-01; topic HORIZON-MSCA-2026-PF-01-01; type of action HORIZON-TMA-MSCA-PF-EF; responsible service "REA" (no unit stated in the proposal — do not invent one); project duration 30 months (24 + 6); participants exactly as Part A lists them (1 COO HUN-REN ATK, HU, PIC 866599553; 2 AP AgroVIR, HU, PIC 891807622), with a footnote that B-2 lists ELTE (PIC 999896468) as secondment host; evaluation model single; panel ENV; evaluators "E1, E2, E3 (simulated)".

## 7.2 File 2 — `plans/reports/FIELDWISE_ESR_2026-09-08.json`

```json
{
  "schema_id": "orch.tier5.esr_review_packet.v1",
  "proposal_id": "101373105",
  "acronym": "FIELDWISE",
  "evaluated_version": {"portal_submission_id": "SEP-211392861", "sealed_at": "2026-09-07 17:25:34 CET (portal stamp)",
                        "pdf_sha256": "c3bfb51f93b4c0c36221d0bd83dab77efaa619eee4f3dd937e58d728c3f81dbe"},
  "generated_at": "<ISO 8601>",
  "scores": {"excellence": 0.0, "impact": 0.0, "implementation": 0.0, "total": 0.0,
             "thresholds_passed": true, "funding_zone": "fundable | seal | above_threshold_not_competitive | below_threshold"},
  "lens_scores": {"E1": {"excellence": 0.0, "impact": 0.0, "implementation": 0.0}, "E2": {}, "E3": {}},
  "aspect_scores": {"exc-obj": 0.0, "exc-method": 0.0, "exc-supervision": 0.0, "exc-researcher": 0.0,
                    "imp-career": 0.0, "imp-dissemination": 0.0, "imp-magnitude": 0.0,
                    "impl-workplan": 0.0, "impl-host": 0.0},
  "formal_checks": [{"check": "", "evidence": "", "status": "OK | Check | Risk", "consequence": ""}],
  "findings": [{"finding_id": "F-01", "criterion": "excellence | impact | implementation | formal",
                "aspect_id": "exc-method", "severity": "critical | major | minor",
                "location": {"part": "A | B1 | B2", "section": "1.2", "pdf_page": 26,
                             "anchor": "¶ beginning \"Stage 2 (WP2) prospectively tests…\", s3"},
                "evidence": "≤ 2 sentences quoted from the PDF", "description": "the weakness, as an evaluator states it",
                "score_impact_estimate": -0.3, "watchlist_ref": "W12 | null"}],
  "revision_actions": [{"action_id": "A-01", "finding_ids": ["F-01"], "priority": "P0 | P1 | P2 | P3 | P4",
                        "target_document": "PART_A_PORTAL | PART_B1_DOCX | PART_B2_DOCX",
                        "anchor": "B1 §1.2 ¶\"Stage 2 (WP2)…\" s3", "action_class": "editorial | needs_fact | needs_decision | portal_admin",
                        "instruction": "imperative, surgical; what to delete/replace/insert and where",
                        "proposed_text": "exact replacement text with [OWNER-CONFIRM: …] placeholders for any fact not in the PDF, or null",
                        "page_budget_delta_lines": 0, "compensating_cut": "anchor of the text to remove to pay for an insertion, or null",
                        "owner": "operator | fellow | supervisor | host | partner:<name>",
                        "fallback": "the honest floor if the owner does not answer", "ripple": ["other places that must change in step"],
                        "verification": "a test the update workflow can run (grep, count, page check)",
                        "effort": "S | M | L", "regression_risk": "low | medium | high", "expected_gain": "+0.2 on Excellence"}],
  "do_not_touch": [{"location": "", "reason": ""}],
  "open_decisions": [{"id": "OD-E1", "question": "", "owner": "", "needed_by": "2026-09-09T12:00+02:00", "fallback": ""}],
  "reupload_recommendation": {"recommend": true, "minimum_set": ["A-01"], "projected_total_after_minimum_set": 0.0,
                              "projected_total_after_all_P0_P2": 0.0, "rationale": ""}
}
```

## 7.3 Register of the ESR comments (Part I)

- Third person, present tense, declarative: "The proposal …", "The applicant …", "The supervisor's …". No "we", no "you".
- For each criterion: **Strengths:** then **Weaknesses:**, each a bullet of one to three sentences making one specific, evidence-based point, referring to sections by number ("Section 1.2", "Part B-2, Section 4"). Strengths are as specific as weaknesses; no praise inflation.
- Weaknesses state what is missing, unclear, unsupported or inconsistent — never what should be done about it. Words that turn a weakness into a recommendation ("should", "could", "would benefit from", "it is recommended") are forbidden in Part I.
- Indicative length: Excellence 300–500 words, Impact 200–400, Implementation 200–350, Overall comments 120–200.
- Scores: criterion scores one decimal (display as x.x); total two decimals (xx.xx).
- Register exemplar (generic, not about this proposal — match the tone, not the content):

  > **Strengths:**
  > - The research objectives are clearly formulated, measurable through pre-specified metrics and logically linked to the gap identified in the state of the art (Section 1.1).
  > - The two-way transfer of knowledge is concrete: the researcher brings field phenotyping expertise that the host lacks, and the host provides modelling supervision documented in Section 1.3.
  >
  > **Weaknesses:**
  > - The proposal does not specify the sample sizes, replication or statistical power underlying the validation experiment, so the robustness of the planned tests cannot be assessed (Section 1.2).
  > - The supervisor's experience in supervising postdoctoral researchers is not described (Section 1.3; Part B-2, Section 5).

## 7.4 Handout conventions (Part II)

- **Anchor format.** `<Part> §<section> ¶"<first 4–6 words of the paragraph>" s<n>` for prose (e.g. `B1 §2.3 ¶"Impact is measured through" s2`); `<Part> §<section> table "<caption or first header>" row <label>` for tables; `B1 §3.1 Gantt row "<label>"`; `A p.<n> <form block> > <field>` for Part A. Always add the PDF page.
- **Priorities.** *P0* admissibility/eligibility/compliance defects; *P1* factual errors, internal inconsistencies, template minimum-content omissions; *P2* score-bearing weaknesses fixable editorially with facts already in the PDF, within the page budget; *P3* score-bearing weaknesses that need a new fact, commitment or decision from an owner (listed in II.4 with fallback); *P4* polish, only if a re-upload happens anyway.
- **Action classes.** *editorial* (rewording, re-ordering, condensing, re-numbering, moving content between B-1 and B-2); *needs_fact* (a number, name, date, document); *needs_decision* (a choice among options with different consequences); *portal_admin* (Part A wizard changes).
- **Page budget.** Part B-1 is at the 10-page limit. Every `PART_B1_DOCX` action states its line delta at the current typesetting (≈ 100 characters per line, 11 pt) and, for any insertion, the `compensating_cut` that pays for it. Part B-2 is unlimited but must stay concise. The recommended minimum set must net to ≤ 0 lines in B-1.
- **No new facts.** `proposed_text` may only contain facts present in the PDF or explicit `[OWNER-CONFIRM: …]` placeholders. Never invent names, numbers, dates, commitments, letters, courses, hectares, or results. Never strengthen a claim in a fallback; the fallback is the honest floor.
- **Expected gain** is an estimate per action in criterion points; the projected totals in II.0 assume the stated set is applied cleanly and nothing else changes.
- **Re-upload recommendation.** Recommend a re-upload only if at least one P0/P1 action exists or the P2 set is deliverable within the remaining time at low regression risk; otherwise recommend leaving the sealed version and say why. State the minimum set, the sequence, and the point of no return (last safe upload time).
- **Pre-upload checklist** must include: the sealed PDF is preserved unchanged; B-1 re-exported to PDF and page count = 10 with tables/figures/references inside; fonts embedded; no template placeholders or comment markup; Part A ↔ B ↔ B-2 cross-checks re-run; every applied action's verification test passed; both B-1 and B-2 attached; submission completed and a new acknowledgement of receipt obtained well before 17:00 Brussels.

# 8. Guardrails

1. **Part I is blind.** Nothing outside the PDF and the two official documents may inform Part I or Annex A. If `OPERATOR CONTEXT` is present, use it only to classify actions, set owners, fallbacks and feasibility in Part II, and mark every use with "(operator context)".
2. **Absence is a finding, not a gap to fill.** If the proposal does not state something, the evaluator's weakness is "the proposal does not state …"; the handout's action is either editorial (if the fact is elsewhere in the PDF) or needs_fact.
3. **No modification of any file except the two outputs.** Do not edit the docx sources, Part A, Tier 3 or the decision log; the update workflow owns those.
4. **Respect the instrument.** Apply PF criteria only; do not import Doctoral Networks, Staff Exchanges, COFUND or grant-agreement criteria; do not assess the budget beyond credibility of resources.
5. **Keep quotes short** (≤ 2 sentences) and exact; use "…" for elisions.
6. **Do not adjudicate eligibility.** Report what the PDF supports; phrase residual doubts as "to be double-checked by the applicant before the deadline".
7. **Language:** English; British or American spelling consistently (the proposal uses British).
8. If the sealed PDF's page count is not 38 or its SHA-256 differs from the one above, stop and report the mismatch instead of evaluating.

=== AGENT PROMPT ENDS ===

<!-- OPERATOR CONTEXT (optional). Add below this line anything the reviewing agent may use in Part II only. Leave empty for a fully blind run. -->
