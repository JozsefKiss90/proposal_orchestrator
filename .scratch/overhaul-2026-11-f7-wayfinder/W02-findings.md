# W02 findings — is `msca_dn_2026_default` an applicable, sourced profile for Stage B?

Ticket: `issues/02-profile-applicability-for-stage-b.md` · researched 2026-11-06 on `harness_overhaul`
@ `1bfe147e` · read only.

## Answer

**The sourcing exists, but it is not in the profile, and nobody has confirmed applicability yet.** The
profile file itself (`harness/profiles/msca_dn_2026_default.json`, PE-02, `1f8336c9`, 2026-10-04) is a thin
pointer file: criteria, scorecard, rubric set, appendix mapping, structural authority, target call. It
carries no hashes, no `advisory`/`blocking` flags, no `review_state`, no `declared_status` (except on the
target call) and no sourcing block, unlike the V10 historical profile. But its inputs are sourced elsewhere:

- the **scorecard** (criteria, weights, thresholds, aspects, levels) is derived from the stored forms by
  `tools/author_msca_dn_bundle.py` and re-derived by `tests/harness/test_msca_dn_profile.py`
  (`harness/evaluator_scorecard_msca_dn.json` → `provenance`);
- the **2026 ("current") documents are pinned by sha256** in the V09 source index
  (`docs/tier4_orchestration_state/msca_dn/authority/authority_source_index_2026-10-13.json`), and **every
  pinned hash still matches the file today** (checked 2026-11-06): the V6.0 Part B template, the
  evaluation form, the 2026–2027 MSCA work programme, the 2026–2027 General Annexes, the scorecard, the
  2026 profile itself (`308a955d…`) and the appendix mapping;
- the V09 matrix's 27 rows read every scoring-relevant rule against this profile, with 26 citations to
  those current-era sources.

**No harness code is needed.** The smallest action is an operator-reviewed **applicability record**
(a Tier 4 decision-log entry) that cites what already exists, settles two open points, and states the
profile's status. It is authoring work, not a ticket for the cut.

## Provenance per profile field

| Field | Value | Provenance found | Gap |
|-------|-------|------------------|-----|
| `criteria` (3, sections) | Excellence / Impact / Implementation → the three Part B sections | scorecard derived from the evaluation form pp. 4–6; matrix CR-01 (equivalent) | none |
| weights, thresholds, total | via the scorecard: 50 / 30 / 20, threshold 3 each, 70/100 overall | scorecard `scoring` and `criteria[*].weight_pct` (form pp. 5–7, General Annexes); matrix WT-01, SA-01; TH-06 records that the *2025* form printed /15, and the 2026 rule is the weighted /100 | none for 2026 |
| `scorecard` v2.2 | `harness/evaluator_scorecard_msca_dn.json` | pinned (`f0e16bf2…`); source `ef_he-msca_en.pdf` v2.2 dated 2025-12-17, pinned (`f7478ef7…`) | **which evaluation-form version the 2026 evaluators use is not established**. v2.2 is the current one held; the 2025 analogue is the matrix's open row EI-02 |
| `rubric_set` 1.0.0 | `harness/rubrics_msca_dn.json` | the harness's own instrument; the matrix records rubrics as "not a rule of either call" (SA-02/03/05/06) | none (declared as the harness's own) |
| `criterion_appendix_mapping` | `harness/criterion_appendix_mapping_msca_dn.json` | pinned (`36530cb0…`); SM-03 records that Part B2 §11 (RAISE DN) exists only in 2026 and is excluded | none |
| `structural_authority` | Part B template V6.0, 2026-04-04 | pinned (`f1904269…`); the scorecard records a **measured V5/V6 equivalence**: same ten aspect headings §1.1–3.2, same Tables 3.1 a–e, same 34-page Part B1 cap; V6 only adds Part B2 §11 | the footer/history-table date discrepancy (04.04 vs 26.03.2026) is recorded, not resolved; harmless |
| `target_call` | HORIZON-MSCA-2026-DN-01 / -01-01, deadline 2026-11-24, `declared_status: Confirmed` | cited to the portal JSON (`…/work_programmes/msca/HORIZON-MSCA.json`); the **pinned WP 2026–2027 PDF states the same call and "24 Nov 2026" (p. 12)** (`8577ee9c…`) | the citation should be the pinned WP page, not the unpinned portal JSON; and **the binding of this resubmission to that call is the operator's declaration** (the 2025 analogue is matrix row CI-01, unresolved) |
| `implementation_mode` | standard DN (not DN-ID, not DN-JD) | none; it is a fact about the proposal | operator declaration |
| `instrument`, `option_tag_grammar`, `registry_path` | MSCA-DN, "Doctoral networks" variant | scorecard `dn_scope_rule`; registry (Tier 2A extracted) | none |
| `advisory` / `blocking` / `review_state` / `declared_status` | absent | — | the profile does not say it is advisory and unreviewed, as the historical one does |

## The smallest action that lets the operator confirm applicability

Write one decision record, e.g. `docs/tier4_orchestration_state/decision_log/msca-dn-stage-b-profile-applicability_<date>.json`,
that:

1. **pins the profile** by its current sha256 (`308a955d…`, matching the V09 index) and names the V09
   source index as the provenance of every current-era input (all hashes match today);
2. **binds the call**: the resubmission goes to HORIZON-MSCA-2026-DN-01-01 as a standard DN, cited to WP
   2026–2027 p. 12 (call id and the 24 Nov 2026 deadline). This is the operator's declaration (`Assumed`),
   as CI-01 is for 2025;
3. **declares the evaluation-form version** as v2.2 (`Inferred`: the current form held; the version the
   2026 evaluators are given is not published in advance);
4. **records the Part B structure** as equivalent to V5 per the scorecard's measured `v5_equivalence`
   (this also answers W01's open assumption: the 2026 Part B keeps the three MSCA-DN sections);
5. states the profile **advisory, non-blocking**, and the operator's review outcome.

Optional and not needed for V16: re-author the 2026 profile through a tool so the file itself carries
these fields, as `tools/author_msca_dn_historical_profile.py` does for 2025. That would be new harness
authoring work and does not pass the "no DN value before 23 Nov" bar.

## Side findings

- **Deadline.** The work programme states **24 Nov 2026** for HORIZON-MSCA-2026-DN-01 (p. 12); the profile
  agrees. The overhaul plan and the wayfinder map say "23 Nov". If 23 Nov is an internal deadline, keep it;
  otherwise the window has one more day.
- The V09 matrix and the V10 historical profile are both still `agent_drafted_pending_operator_review`. That
  is a V14 (stage A) matter, not V16's, but the operator's review of the matrix also covers the rows the
  Stage B record would cite.
- W01's "same three sections" assumption is **confirmed** by the measured V5/V6 equivalence.
