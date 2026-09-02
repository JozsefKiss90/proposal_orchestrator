# FIELDWISE — Open Decisions, Round 2 (2026-08-31)

**Submission deadline: Tuesday 2026-09-09** (HORIZON-MSCA-2026-PF-01-01, MSCA-PF 2026).
**Answers needed by: Thursday 2026-09-03, end of day.**
Anything unanswered at that point takes its stated fallback so the proposal can be frozen
on 2026-09-06 and uploaded with buffer. A fallback is always the honest, currently
confirmed position — never a strengthened claim.

This round arises from the external review comments collected in
`plans/proposal_issues.md`. Review items that needed no partner input (KPI list, research
questions, claim rewordings, contingency framing) are already being applied and are NOT
listed here; this document contains only the four decisions we cannot make alone.

Status vocabulary is the project's standard: **Confirmed** (written evidence) /
**Assumed** (declared working assumption) / **Unresolved**. Draft answers below are
**Assumed-pending-confirmation**: they are grounded strictly in the partner-reviewed Pack
and are offered so the owner only needs to confirm or correct, not author from scratch.
Nothing enters the submitted text until the owner confirms it.

---

## OD-1 — Work-plan timing: when can the model be frozen? (review issue 1)

**Owner: Dr. Roland Hollós (ATK), with Dr. Rositsa Cholakova.**
**Needed by 2026-09-03 EOD.**

The reviewer's point: a model still being developed during the validation field season is
not prospectively validated. They propose: WP1 (harmonisation + stress-target definition)
done by ~M2; WP2 model built, validated and **frozen by M3**; WP3 genuinely prospective
commercial-field validation from M4.

Current partner-reviewed timing: WP1 M1–M6, WP2 M3–M14, WP3 M4–M18.

**The underlying question we need answered, rather than a yes/no on the reviewer's
months:**

1. Relative to the expected fellowship start, in which project month does the first
   prospective commercial field season begin?
2. Can an initial primary model realistically be frozen (fixed parameters, registered
   model card) before that season starts — and if so, by which month?

**Two candidate schemes (pick, adapt, or replace):**

- **Scheme A — reviewer's compression:** WP1 → M1–M2, WP2 freeze → M3, WP3 prospective
  from M4. Question of feasibility: five-season archive harmonised in two months.
- **Scheme B — freeze-milestone variant (minimal change):** keep the current WP spans,
  insert an explicit milestone "primary model frozen and registered" scheduled before the
  first prospective measurement campaign (T3.3), and re-scope T3.5 so only the frozen
  model is applied prospectively in season 1; any recalibration happens after the season
  and is reported as such. WP2's remaining months (post-freeze) carry the scale-
  harmonisation and crop-transfer specification work (T2.4–T2.6), not target-model
  changes.

**If adopted, this ripples into:** work-package table, Gantt, milestones, the closure
narrative ("freezing it before the new field season"), and the KPI/deliverable month
anchors. We will apply the ripple on 2026-09-04/05.

**Fallback if unanswered:** the submitted proposal keeps the current confirmed timing
unchanged and makes no pre-season freeze commitment.

---

## OD-2 — Pre-specified physiological stress-target hierarchy (review issue 4)

**Owner: Dr. Rositsa Cholakova, with Dr. Hollós.**
**Needed by 2026-09-03 EOD.**

The reviewer asks that the proposal state, at proposal level, how the primary
physiological stress target is chosen — as a pre-specified hierarchy, so it cannot look
like cherry-picking after seeing the data.

**Draft answer for confirmation (Assumed-pending-confirmation; built only from the
instrument set and archive variables the Pack names — please correct freely):**

> The primary physiological water-stress target and its corroborating endpoints follow a
> pre-specified hierarchy, fixed in the stress-target and validation protocol (D1.2)
> before any model fitting:
> 1. **Primary target:** the stomatal conductance/resistance-based stress state,
>    evaluated against phenology-adjusted reference ranges — the physiological variable
>    with the most consistent coverage across the 2022–2026 archive.
> 2. **First corroborating endpoint:** leaf-surface temperature / CWSI (the thermal
>    expression of stomatal closure; available in the later archive years).
> 3. **Second corroborating endpoint:** VIS-NIR (and, where available, SWIR) spectral
>    water- and pigment-related indices.
> 4. **Slow-response corroborator:** SPAD chlorophyll status.

> Selection rule: if the T1.1 archive audit shows the primary target's coverage is
> insufficient for a given season or site, the next level of the hierarchy becomes the
> primary target for that stratum. Every such substitution is made and documented before
> model training, never after inspecting model results.

**Questions to the owner:** Is stomatal conductance/resistance the right apex? Should
CWSI outrank the spectral indices? Is the substitution rule how you would defend it?

**Fallback if unanswered:** the proposal states that a pre-specified target hierarchy is
fixed in D1.2 before any model fitting, without naming the order at proposal level.
(Weaker than the reviewer wants, but honest.)

---

## OD-3 — Named performance, uncertainty and calibration metrics (review issue 5)

**Owner: Dr. Rositsa Cholakova.**
**Needed by 2026-09-03 EOD.**

The reviewer asks for the actual metrics — "thresholds fixed in advance" is not enough.
T2.3 already commits to calibration, uncertainty, interpretability and blocked
unseen-year performance; this decision names the metrics inside those families.

**Draft answer for confirmation (Assumed-pending-confirmation — trim to what you would
actually defend; fewer, named metrics beat a long list):**

> Model evaluation uses pre-registered metrics under blocked unseen-year validation.
> 1. **Stress detection (classified state):** balanced accuracy and F1 against the
>    pre-specified physiological stress state; ROC-AUC for threshold-free comparison.
> 2. **Continuous prediction (where the target is continuous):** RMSE and MAE, with R²
>    reported for context.
> 3. **Calibration:** reliability diagrams with Brier score for probabilistic stress
>    classification; prediction-interval coverage probability (PICP) and mean interval
>    width for continuous predictions.
> 4. **Operational value:** stress-detection lead time (days ahead of the reference
>    physiological expression) and per-season false-alarm rate.

> All acceptance thresholds are fixed in D1.2 before the prospective season.

**Questions to the owner:** classification, regression, or both, as the primary framing?
Are lead time and false-alarm rate the right operational pair? Any metric here you would
not defend in an interview?

**Fallback if unanswered:** the proposal names the metric families (detection accuracy,
calibration, uncertainty coverage, lead time) and states that exact metrics and
thresholds are pre-registered in D1.2 before model fitting.

---

## OD-4 — MATE written data-use confirmation (review issue 8a)

**Owner: operator → MATE (contact: Dr. Sándor Takács, to be confirmed as contact).**
**Needed by 2026-09-03 EOD.**

Working assumption `mate_data_rights` currently declares (Assumed): MATE grants rights
and access to the 2022–2026 processing-tomato archive under institutional data-use
conditions to be documented before the action starts.

**Ask:** a short written confirmation (e-mail suffices) of (a) archive access for
FIELDWISE's scientific purposes, and (b) Dr. Takács as contact person.
**On confirmation:** `mate_data_rights` flips Assumed→Confirmed; the confirmation source
is recorded in the confirmation checklist.
**Fallback if unanswered:** the current Assumed formulation stands, with the proposal's
existing "to be documented before the action starts" flag left in place.

---

## OD-5 — Commercial farmer field access in writing (review issue 8b)

**Owner: operator → the collaborating commercial farmer (via MATE/ATK channel).**
**Needed by 2026-09-03 EOD.**

Working assumption `farmer_field_access` currently declares (Assumed): written field
access covering site availability within M4–M18, sensor installation, measurement and
UAV campaigns, agreed irrigation-treatment implementation, and routine crop management.

**Ask:** written confirmation of the above, even in short letter form.
**On confirmation:** Assumed→Confirmed; strengthens the WP3 independence claim, which the
review identifies as the proposal's central evidence step.
**Fallback if unanswered:** the Assumed declaration stands; T3.1 (secure written access)
remains the M1 task; the Skanzen contingency remains framed as measurement backup only
(never transferability proof — applied under review issue 7).

---

## OD-6 — AgroVIR written confirmation of involvement and supervision (review issue 8c)

**Owner: operator → AgroVIR (Miklós Maróti, Managing Director).**
**Needed by 2026-09-03 EOD.**

The Pack already asks AgroVIR to confirm the supervision arrangement in writing. Needed:
(a) the placement supervision arrangement (named supervisor, monthly face-to-face
technical reviews), and (b) the M1-onward structured consultation role (T4.4).

Note: separately from this confirmation, the placement passage is being rewritten to
lead with what the placement delivers (structured monthly reviews, protected-data
interoperability work, named MD-level supervisor) rather than the phrase "mainly remote"
(review issue 9). That rewrite changes no facts and does not wait on this OD.

**On confirmation:** the AgroVIR-keyed working assumptions flip to Confirmed.
**Fallback if unanswered:** Assumed declarations stand as written.

---

## What happens on each date

| Date | Action |
|------|--------|
| 2026-09-03 EOD | Answer cut-off; unanswered ODs take their fallbacks |
| 2026-09-04/05 | Confirmed answers applied to the proposal and the project records (paired edits) |
| 2026-09-06 | Submission master frozen (hash recorded) |
| 2026-09-07/08 | Buffer; portal upload |
| 2026-09-09 | Call deadline |
