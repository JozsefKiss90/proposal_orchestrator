# Rule-equivalence matrix — every scoring-relevant rule of the 2025 MSCA Doctoral Networks evaluation, read against the 2026 profile

Authored 2026-10-13. Matrix `msca_dn_2025_to_2026_equivalence_2026-10-13`, schema `authority_equivalence_matrix/1`,
written by `tools/author_msca_dn_authority_matrix.py`.

Review state: **agent drafted pending operator review**.
The matrix's own reading of its sources is declared **Inferred**.
Relationship to earlier versions: the equivalence matrix authored on 2026-10-12, `docs/tier4_orchestration_state/msca_dn/authority/equivalence_matrix_2025_2026-10-12.json` (sha256 115949d3fe4858340128a6ce1fc3afe83f28a085347714752ccf1ca9d9453bcd). That matrix carried six defaulted rows and two unresolved, every one of them resting on a 2025 document this repository did not hold. Three of those documents have since been obtained, so the six defaultings are re-derived here against the sources themselves and one new row records a difference they revealed. The superseded matrix stays in the tree unedited: a correction to a matrix is a successor matrix, and what was believed on 2026-10-12 is part of the evidence. The specification's decision 3, which pinned one 2026 profile because the 2025 sources were absent, stands as written.
Source index: `docs/tier4_orchestration_state/msca_dn/authority/authority_source_index_2026-10-13.json`, bound at `sha256:cfb935b0e0e9`.

The runbook proposes preparing a historical profile as a copy of the 2026 one, leaving a rule
unchanged where no source states a difference. That is a defaulting policy, not evidence that the
rule applied in 2025. This matrix replaces it: each rule is sourced to a 2025 document, or
recorded as defaulted with the rule its defaulting affects, or recorded as an unresolved
limitation. No verdict means that no difference was found.

## What the rows conclude

| Verdict | Rows | What it means |
|---|---|---|
| equivalent | 18 | a historical source states the rule, and it is the rule the current profile holds |
| differs | 2 | a historical source states a different rule |
| defaulted | 0 | the current rule is carried forward because no historical source states it — **not** equivalence |
| unresolved | 2 | no source states the rule, and the limitation is recorded |
| era_neutral | 5 | the rule is the assessing harness's own and no call document states it |
| **total** | **27** | |

No verdict means *no difference was found*. A row with no historical citation is `defaulted` and
names the rule its defaulting affects. `harness.authority_matrix.check` reports a row marked
equivalent or differs with no citation into an obtained historical source.

## Coverage

| Area | Rows | Verdicts |
|---|---|---|
| criteria | 2 | equivalent |
| weights | 2 | equivalent |
| thresholds | 6 | differs, equivalent |
| evaluator instructions | 4 | equivalent, unresolved |
| variant | 2 | equivalent |
| section mapping | 3 | differs, equivalent |
| appendix mapping | 1 | equivalent |
| scoring assumption | 6 | equivalent, era_neutral |
| call identity (beyond the required set) | 1 | unresolved |

## The rows

### Criteria

#### CR-01 — equivalent

The three criteria the proposal is scored on, and their order: Excellence, Impact, Implementation.

- Affects: both
- Settles: as applied to this submission
- 2025: Criterion 1 - Excellence Score: 4.20 (Threshold: 3 / 5.00 , Weight: 50.00% ); Criterion 2 - Impact Score: 4.50 (Threshold: 3 / 5.00 , Weight: 30.00%; Criterion 3 - implementation Score: 4.20 (Threshold: 3 / 5.00 , Weight: 20.00% )
- 2026: Excellence, Impact, Implementation
- Status: **Inferred** — The 2025 side is stated twice: by the evaluation's own recorded wording, which is evidence of what was applied to this submission, and by the work programme the call was opened under, which names the three criteria as the call's. It is Inferred rather than Confirmed because no hash from the issuing body vouches for either document's bytes.
- For the historical profile: The historical profile declares the same three criteria in the same order, sourced to this row rather than copied.

| Source | Era | Locator | States |
|---|---|---|---|
| `msca-dn-2025-esr.json` | historical | `evaluation_result/criteria/#0/wording` | the 2025 evaluation's recorded wording for criterion 1 |
| `msca-dn-2025-esr.json` | historical | `evaluation_result/criteria/#1/wording` | the 2025 evaluation's recorded wording for criterion 2 |
| `msca-dn-2025-esr.json` | historical | `evaluation_result/criteria/#2/wording` | the 2025 evaluation's recorded wording for criterion 3 |
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | historical | `page 123` | the work programme names the three award criteria of the 2025 call |
| `msca_dn_2026_default.json` | current | `criteria` | the 2026 profile's three criteria, in order |

> Criterion 1 - Excellence Score: 4.20 (Threshold: 3 / 5.00 , Weight: 50.00% )

> Criterion 2 - Impact Score: 4.50 (Threshold: 3 / 5.00 , Weight: 30.00%

> Criterion 3 - implementation Score: 4.20 (Threshold: 3 / 5.00 , Weight: 20.00% )

> the award criteria 'excellence', 'impact' and 'quality and efficiency of the implementation'

- Measured: the 2025 evaluation awarded three criterion scores — `evaluation_result/criteria` is length 3
- Measured: the 2026 profile declares three criteria — `criteria` is length 3
- Measured: the 2025 evaluation's criterion 1 is Excellence — `evaluation_result/criteria/#0/registry_criterion_id` is 'Excellence'
- Measured: the 2026 profile's criterion 1 is Excellence — `criteria/#0/registry_criterion_id` is 'Excellence'
- Measured: the 2025 evaluation's criterion 2 is Impact — `evaluation_result/criteria/#1/registry_criterion_id` is 'Impact'
- Measured: the 2026 profile's criterion 2 is Impact — `criteria/#1/registry_criterion_id` is 'Impact'
- Measured: the 2025 evaluation's criterion 3 is Implementation — `evaluation_result/criteria/#2/registry_criterion_id` is 'Implementation'
- Measured: the 2026 profile's criterion 3 is Implementation — `criteria/#2/registry_criterion_id` is 'Implementation'

#### CR-02 — equivalent

Which criterion each of the ten aspects is graded under: four under Excellence, four under Impact,
two under Implementation.

- Affects: a number
- Settles: call wide
- 2025: the evaluation form served through the 2025 call window carries all ten aspect texts, each inside the section of the criterion the scorecard grades it under
- 2026: excellence: exc-obj, exc-method, exc-training, exc-supervision; impact: imp-structuring, imp-career, imp-dissemination, imp-magnitude; implementation: impl-workplan, impl-participants
- Status: **Inferred** — Measured, not read off a list. The 2025 form is walked once, its three criterion section headings locate three boundaries, and every one of the ten aspect texts is required to fall inside its own criterion's section. An aspect present but grouped elsewhere refuses here. Inferred, not Confirmed, because that form's place in the call is bracketed and not closed, which row EI-02 keeps open.
- For the historical profile: The historical profile keeps the criterion-to-aspect assignment, sourced to the 2025 form's own grouping rather than carried over from 2026.

| Source | Era | Locator | States |
|---|---|---|---|
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 4` | aspect 1.1 under 1. Excellence |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 4` | aspect 1.2 under 1. Excellence |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 4` | aspect 1.3 under 1. Excellence |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 4` | aspect 1.4 under 1. Excellence |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 5` | aspect 2.1 under 2. Impact |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 5` | aspect 2.2 under 2. Impact |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 5` | aspect 2.3 under 2. Impact |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 5` | aspect 2.4 under 2. Impact |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 6` | aspect 3.1 under 3. Quality and efficiency of the implementation |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 6` | aspect 3.2 under 3. Quality and efficiency of the implementation |
| `evaluator_scorecard_msca_dn.json` | current | `criteria` | the 2026 evaluation form's aspects, grouped by criterion |

> Quality and pertinence of the project’s research and innovation objectives (and the extent to which they are ambitious, and go beyond the state of the art).

> Soundness of the proposed methodology (including interdisciplinary approaches, consideration of the gender dimension and other diversity aspects if relevant for the research project, and the quality and appropriateness of open science practices).

> Quality and credibility of the training programme (including transferable skills, inter/multidisciplinary, inter-sectoral and gender as well as other diversity aspects).

> Quality of the supervision (including mandatory joint supervision for industrial and joint doctorate projects).

> Contribution to structuring doctoral training at the European level and to strengthening European innovation capacity, including the potential for: a) meaningful contribution of the non-academic sector to the doctoral training, as appropriate to the implementation mode and research field b) developing sustainable elements of doctoral programmes.

> Credibility of the measures to enhance the career perspectives and employability of researchers and contribution to their skills development.

> Suitability and quality of the measures to maximise expected outcomes and impacts, as set out in the dissemination and exploitation plan, including communication activities.

> The magnitude and importance of the project’s contribution to the expected scientific, societal and economic impacts.

> Quality and effectiveness of the work plan, assessment of risks and appropriateness of the effort assigned to work packages.

> Quality, capacity and role of each participant, including hosting arrangements and extent to which the consortium as a whole brings together the necessary expertise.

### Weights

#### WT-01 — equivalent

The criterion weights used to compute the weighted total.

- Affects: a number
- Settles: as applied to this submission
- 2025: excellence 50%, impact 30%, implementation 20%
- 2026: excellence 50%, impact 30%, implementation 20%
- Status: **Inferred** — Each weight is recorded three times: in the 2025 evaluation's own per-criterion wording, in the work programme's weighting row for that call, and in the 2026 scorecard derived from the evaluation form. The call document and the result agree, so the weights are the call's rule and not only what this submission was given. Inferred for the reason CR-01 gives.
- For the historical profile: The historical profile keeps these weights, sourced to the 2025 evaluation's own record rather than carried over.

| Source | Era | Locator | States |
|---|---|---|---|
| `msca-dn-2025-esr.json` | historical | `evaluation_result/criteria/#0/wording` | the weight the 2025 evaluation applied to criterion 1 |
| `msca-dn-2025-esr.json` | historical | `evaluation_result/criteria/#1/wording` | the weight the 2025 evaluation applied to criterion 2 |
| `msca-dn-2025-esr.json` | historical | `evaluation_result/criteria/#2/wording` | the weight the 2025 evaluation applied to criterion 3 |
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | historical | `page 124` | the work programme's weighting row for the 2025 call |
| `evaluator_scorecard_msca_dn.json` | current | `criteria` | the 2026 scorecard's weights, derived from the evaluation form |

> Criterion 1 - Excellence Score: 4.20 (Threshold: 3 / 5.00 , Weight: 50.00% )

> Criterion 2 - Impact Score: 4.50 (Threshold: 3 / 5.00 , Weight: 30.00%

> Criterion 3 - implementation Score: 4.20 (Threshold: 3 / 5.00 , Weight: 20.00% )

> 50% 30% 20% Weighting

- Measured: the 2025 evaluation weighted excellence at 50% — `evaluation_result/criteria/#0/weight_pct` is 50
- Measured: the 2026 scorecard weights excellence at 50% — `criteria/#0/weight_pct` is 50
- Measured: the 2025 evaluation weighted impact at 30% — `evaluation_result/criteria/#1/weight_pct` is 30
- Measured: the 2026 scorecard weights impact at 30% — `criteria/#1/weight_pct` is 30
- Measured: the 2025 evaluation weighted implementation at 20% — `evaluation_result/criteria/#2/weight_pct` is 20
- Measured: the 2026 scorecard weights implementation at 20% — `criteria/#2/weight_pct` is 20

#### WT-02 — equivalent

The evaluation form's statement that weighting serves the ranking and not the determination of
whether a proposal passed the thresholds.

- Affects: an interpretation
- Settles: call wide
- 2025: Weighting is only for the ranking (not to determine if the proposal passed the thresholds).
- 2026: Weighting is only for the ranking (not to determine if the proposal passed the thresholds).
- Status: **Inferred** — The two forms carry the sentence word for word. Inferred, not Confirmed, because the 2025 form's place in the call is bracketed, which row EI-02 keeps open.
- For the historical profile: The historical profile carries the sentence, sourced to the 2025 form. A pass or fail statement about the 2025 result rests on it and may cite this row.

| Source | Era | Locator | States |
|---|---|---|---|
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 2` | the 2025 evaluation form on what weighting is for |
| `ef_he-msca_en.pdf` | current | `page 2` | the 2026 evaluation form on what weighting is for |

> Weighting is only for the ranking (not to determine if the proposal passed the thresholds).

> Weighting is only for the ranking (not to determine if the proposal passed the thresholds).

### Thresholds

#### TH-01 — equivalent

The per-criterion threshold a criterion score must reach.

- Affects: a number
- Settles: as applied to this submission
- 2025: excellence threshold 3, impact threshold 3, implementation threshold 3
- 2026: 3
- Status: **Inferred** — The 2025 evaluation records the threshold beside each of its three criterion scores, and the evaluation form of that call window states the same figure as a rule. Result and rule agree. Inferred for the reason CR-01 gives.
- For the historical profile: The historical profile keeps the per-criterion threshold unchanged.

| Source | Era | Locator | States |
|---|---|---|---|
| `msca-dn-2025-esr.json` | historical | `evaluation_result/criteria/#0/wording` | the threshold recorded beside criterion 1 |
| `msca-dn-2025-esr.json` | historical | `evaluation_result/criteria/#1/wording` | the threshold recorded beside criterion 2 |
| `msca-dn-2025-esr.json` | historical | `evaluation_result/criteria/#2/wording` | the threshold recorded beside criterion 3 |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 2` | the 2025 evaluation form on the per-criterion threshold |
| `wp-15-general-annexes_horizon-2026-2027_en.pdf` | current | `page 27` | the 2026 General Annexes on the per-criterion threshold |

> Criterion 1 - Excellence Score: 4.20 (Threshold: 3 / 5.00 , Weight: 50.00% )

> Criterion 2 - Impact Score: 4.50 (Threshold: 3 / 5.00 , Weight: 30.00%

> Criterion 3 - implementation Score: 4.20 (Threshold: 3 / 5.00 , Weight: 20.00% )

> The threshold for the individual criteria is 3.

> The threshold for individual criteria will be 3.

- Measured: the 2025 evaluation applied a threshold of 3 to excellence — `evaluation_result/criteria/#0/threshold` is 3
- Measured: the 2025 evaluation applied a threshold of 3 to impact — `evaluation_result/criteria/#1/threshold` is 3
- Measured: the 2025 evaluation applied a threshold of 3 to implementation — `evaluation_result/criteria/#2/threshold` is 3
- Measured: the 2026 scorecard declares the same per-criterion threshold — `scoring/individual_threshold` is 3

#### TH-02 — equivalent

The overall threshold, and the total it applies to.

- Affects: a number
- Settles: as applied to this submission
- 2025: Evaluation Result Total score: 85.80 % (Threshold: 70 /100.00)
- 2026: 70 of 100
- Status: **Inferred** — The 2025 evaluation's recorded result wording carries the threshold and the maximum it is out of, and the work programme the call was opened under sets the same threshold as a percentage of the weighted total. Seventy per cent of a hundred is seventy points, so the two are the same rule stated in two units. Inferred for the reason CR-01 gives.
- For the historical profile: The historical profile keeps the overall threshold and maximum.

| Source | Era | Locator | States |
|---|---|---|---|
| `msca-dn-2025-esr.json` | historical | `evaluation_result/result_wording` | the 2025 evaluation's recorded overall threshold and maximum |
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | historical | `page 123` | the work programme sets the 2025 call's funding threshold |
| `ef_he-msca_en.pdf` | current | `page 2` | the 2026 evaluation form on the overall threshold |

> Evaluation Result Total score: 85.80 % (Threshold: 70 /100.00)

> Proposals scoring equal to or above 70% will be considered for funding

> The overall threshold, applying to the sum of the 3 individual scores, is 70 points.

- Measured: the 2025 evaluation records an overall threshold of 70 — `evaluation_result/overall_threshold` is 70
- Measured: out of 100 — `evaluation_result/overall_max` is 100
- Measured: the 2026 scorecard declares the same overall threshold — `scoring/overall_threshold` is 70
- Measured: and the same maximum — `scoring/overall_max` is 100

#### TH-03 — equivalent

Which authority sets the overall threshold where the General Annexes and the evaluation form
disagree. The annexes state a generic threshold on the unweighted sum; the form states one on the
weighted total.

- Affects: an interpretation
- Settles: call wide
- 2025: the call's own work programme part governs. Its General Annexes refer training and mobility actions to that part, the part itself takes the weighting and the thresholds into its specific conditions, and the evaluation form of the call window says a call may set different rules
- 2026: The MSCA evaluation form (Tier 2A) overrides the General Annexes' generic overall threshold of 10 on the unweighted sum with 70 on a weighted total out of 100; the General Annexes themselves allow it ('Specific calls or topics may have different rules'). The per-criterion threshold of 3 is unchanged. Tier interaction logged per CLAUDE.md §12.3 in docs/tier4_orchestration_state/decision_log/msca-dn-pe02-evaluation-bundle_2026-10-04.json.
- Status: **Inferred** — Three 2025 documents point the same way, and none of them is this repository's. The General Annexes hand training and mobility actions to the work programme part; that part states the weighting and thresholds are in its own specific conditions; and the evaluation form of the call window says a specific call may differ. So the call document outranked the generic one in 2025, which is the resolution the 2026 documents were given. Inferred, not Confirmed, because no issuing body's hash vouches for any of the three.
- For the historical profile: The historical profile reads the 2025 scores against the call's own threshold, citing this row. The resolution is no longer carried forward from 2026.

| Source | Era | Locator | States |
|---|---|---|---|
| `wp-14-general-annexes_horizon-2025_en.pdf` | historical | `page 24` | the 2025 General Annexes refer this action type to the work programme part |
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | historical | `page 24` | that part takes the weighting and the thresholds into its own conditions |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 2` | the 2025 evaluation form allows a call to set different rules |
| `evaluator_scorecard_msca_dn.json` | current | `scoring/annex_d_override/resolution` | the resolution taken on the 2026 documents |

> Training and mobility actions (TMA)

> For application of the general award criteria, including weighting and thresholds, see the specific conditions at the end of this Work Programme part.

> Specific calls or topics may have different rules

#### TH-04 — equivalent

The maximum a criterion score may reach.

- Affects: a number
- Settles: as applied to this submission
- 2025: the maximum recorded beside each criterion score is 5.00
- 2026: 5, the upper end of the scorecard's scale
- Status: **Inferred** — The 2025 evaluation prints the maximum beside every criterion score it records, and the work programme of that call states it as a rule. Inferred for the reason CR-01 gives. The claim is the maximum and nothing else: row TH-05 carries the resolution, which the two 2025 authorities state differently.
- For the historical profile: The historical profile keeps the maximum.

| Source | Era | Locator | States |
|---|---|---|---|
| `msca-dn-2025-esr.json` | historical | `evaluation_result/criteria/#0/wording` | the 2025 evaluation's recorded maximum for criterion 1 |
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | historical | `page 123` | the work programme states the maximum for the 2025 call |
| `ef_he-msca_en.pdf` | current | `page 2` | the 2026 evaluation form on the range and its resolution |

> Criterion 1 - Excellence Score: 4.20 (Threshold: 3 / 5.00 , Weight: 50.00% )

> Each criterion will be scored out of 5.

> Scoring must be in the range from 0-5. Scores will be awarded with a resolution of one decimal place.

- Measured: the 2026 scorecard declares the scale — `scoring/scale` is '0-5, one decimal place'

#### TH-05 — equivalent

The resolution a criterion score is awarded to.

- Affects: a number
- Settles: call wide
- 2025: one decimal place. The two 2025 authorities state different resolutions, and the recorded scores decide between them: excellence 4.2, implementation 4.2 is not a half mark
- 2026: one decimal place
- Status: **Inferred** — The two 2025 authorities disagree. The work programme of the call states one decimal place; the evaluation form of the call window states that half marks may be given. The recorded result settles which was applied, because a score of 4.2 is not a half mark and could not have been awarded under the form's rule. This module refuses to render if no recorded score is finer than a half mark, because then both rules would fit and the equivalence would be the absence of a visible difference again. Inferred, not Confirmed: the rule applied to this submission is evidenced, and the conflict between the two 2025 documents is recorded rather than resolved in general.
- For the historical profile: The historical profile keeps one decimal place and cites this row, not a defaulting. A statement about any other 2025 proposal must carry the conflict between the two authorities, which the matrix records as an uncertainty.

| Source | Era | Locator | States |
|---|---|---|---|
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | historical | `page 123` | the work programme states one decimal place for the 2025 call |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 2` | the evaluation form of the call window states half marks instead |
| `msca-dn-2025-esr.json` | historical | `evaluation_result/criteria/#0/score` | a recorded score that no half-mark rule could have awarded |
| `ef_he-msca_en.pdf` | current | `page 2` | the 2026 evaluation form on the range and its resolution |
| `evaluator_scorecard_msca_dn.json` | current | `scoring/scale` | the resolution as the scorecard carries it |

> Scores will be awarded with a resolution of one decimal place

> Scoring must be in the range from 0-5. Half-marks may be given.

> 4.2

> Scoring must be in the range from 0-5. Scores will be awarded with a resolution of one decimal place.

- Measured: the 2025 evaluation recorded 4.2 for excellence — `evaluation_result/criteria/#0/score` is 4.2
- Measured: the 2025 evaluation recorded 4.5 for impact — `evaluation_result/criteria/#1/score` is 4.5
- Measured: the 2025 evaluation recorded 4.2 for implementation — `evaluation_result/criteria/#2/score` is 4.2

#### TH-06 — differs

The total the three criterion scores are summed into, as the evaluation form itself prints it.

- Affects: a number
- Settles: call wide
- 2025: the 2025 evaluation form prints an unweighted total out of 15 and states an overall threshold of 10 points on the sum of the three scores
- 2026: 70 points on a weighted total out of 100
- Difference: The 2025 evaluation form's own total is the three criterion scores added up, out of 15, read against 10 points. The 2026 form instead states the threshold on the weighted total out of 100. The difference is in the form, and it is not the difference that governed: the work programme of the 2025 call sets the threshold at 70% of the weighted total, and the recorded result is a weighted total out of 100. So the 2025 form's generic total was superseded by the call's own rule, which is what TH-03 resolves and TH-02 measures.
- Status: **Inferred** — Both forms are read directly, and the recorded result shows which total was actually formed. Inferred, not Confirmed, for the reason CR-01 gives, and because the 2025 form's place in the call is bracketed.
- For the historical profile: The historical profile forms the weighted total out of 100 and cites the call document for it. It must not cite the 2025 evaluation form's /15 total, and a reader comparing the two eras is told why the form's own total does not apply.

| Source | Era | Locator | States |
|---|---|---|---|
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 2` | the 2025 evaluation form's generic overall threshold |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 6` | and the total it prints that threshold against |
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | historical | `page 123` | the work programme's threshold for the 2025 call instead |
| `msca-dn-2025-esr.json` | historical | `evaluation_result/result_wording` | the total the 2025 evaluation actually recorded |
| `ef_he-msca_en.pdf` | current | `page 2` | the 2026 evaluation form on the overall threshold |

> The overall threshold, applying to the sum of the 3 individual scores, is 10 points.

> Total score Overall threshold /15

> Proposals scoring equal to or above 70% will be considered for funding

> Evaluation Result Total score: 85.80 % (Threshold: 70 /100.00)

> The overall threshold, applying to the sum of the 3 individual scores, is 70 points.

- Measured: the 2025 evaluation recorded a maximum of 100, not the form's fifteen — `evaluation_result/overall_max` is 100

### Evaluator instructions

#### EI-01 — equivalent

The six score-level descriptions, 0 to 5, an evaluator grades against.

- Affects: both
- Settles: call wide
- 2025: all six sentences occur word for word in the evaluation form served through the 2025 call window
- 2026: 0: The proposal fails to address the criterion or cannot be assessed due to missing or incomplete information.; 1: Poor. The criterion is inadequately addressed, or there are serious inherent weaknesses.; 2: Fair. The proposal broadly addresses the criterion, but there are significant weaknesses.; 3: Good. The proposal addresses the criterion well, but a number of shortcomings are present.; 4: Very Good. The proposal addresses the criterion very well, but a small number of shortcomings are present.; 5: Excellent. The proposal successfully addresses all relevant aspects of the criterion. Any shortcomings are minor.
- Status: **Inferred** — Each of the six sentences is located in the 2025 form and in the 2026 form, and the citation below refuses if any one of them stops occurring on the page it cites. This was the largest unsourced input to a numerical comparison, and it is now sourced on both sides. Inferred, not Confirmed, because the 2025 form's place in the call is bracketed, which row EI-02 keeps open.
- For the historical profile: The historical profile keeps the level descriptions and cites this row. A grade awarded under them is no longer resting on a 2026 document alone.

| Source | Era | Locator | States |
|---|---|---|---|
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 2` | the 2025 evaluation form's level 0 description |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 2` | the 2025 evaluation form's level 1 description |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 2` | the 2025 evaluation form's level 2 description |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 2` | the 2025 evaluation form's level 3 description |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 2` | the 2025 evaluation form's level 4 description |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 2` | the 2025 evaluation form's level 5 description |
| `ef_he-msca_en.pdf` | current | `page 2` | the 2026 evaluation form's level 4 description, one of six |
| `evaluator_scorecard_msca_dn.json` | current | `scoring/levels` | all six descriptions, as the scorecard holds them |

> The proposal fails to address the criterion or cannot be assessed due to missing or incomplete information.

> Poor. The criterion is inadequately addressed, or there are serious inherent weaknesses.

> Fair. The proposal broadly addresses the criterion, but there are significant weaknesses.

> Good. The proposal addresses the criterion well, but a number of shortcomings are present.

> Very Good. The proposal addresses the criterion very well, but a small number of shortcomings are present.

> Excellent. The proposal successfully addresses all relevant aspects of the criterion. Any shortcomings are minor.

> Very Good. The proposal addresses the criterion very well, but a small number of shortcomings are present.

#### EI-02 — unresolved

Which version of the evaluation form was in force for the 2025 call.

- Affects: an interpretation
- Settles: call wide
- 2026: version 2.2 dated 2025-12-17
- Limitation: Three captures of the issuing body's template address carry one archive digest, dated inside the call window, the last of them twenty days before the deadline, and the next distinct digest is months after it. That brackets the window and does not close it: a version served between two captures and never captured would leave no trace, and nothing states which version the evaluators were given. The captures are also of one archive, so they are one witness observed three times rather than three independent witnesses. Every row citing the 2025 form is Inferred because of this, and none is Confirmed.
- Status: **Unresolved** — A version served at the issuing body's template address through the call window is now held, and its place in the call is bracketed rather than settled. Nothing states which version the 2025 evaluation used.
- For the historical profile: The historical profile records that the evaluation-form version the 2025 evaluators used is not established. It does not claim the held version applied, and every rule it takes from that form is declared Inferred.

| Source | Era | Locator | States |
|---|---|---|---|
| `evaluator_scorecard_msca_dn.json` | current | `provenance/version_date` | the version date the stored evaluation form declares |

> 2025-12-17

- Measured: the stored evaluation form's declared version — `provenance/version` is '2.2'
- Measured: and its declared date — `provenance/version_date` is '2025-12-17'

#### EI-03 — equivalent

Scores are awarded for the criteria and not for the individual aspects listed under them.

- Affects: a number
- Settles: as applied to this submission
- 2025: the 2025 evaluation records 3 criterion scores and 29 observations, none of which carries a score
- 2026: Evaluation scores will be awarded for the criteria, and not for the different aspects listed in the table.
- Status: **Inferred** — The 2025 side is stated and also measured. The work programme of the call carries the rule in words, and the recorded result bears it out: three criterion scores are recorded and no observation carries a score field. Inferred rather than Confirmed because no issuing body's hash vouches for either document.
- For the historical profile: The historical profile keeps the rule that the ten aspect cells inform a criterion score and are never averaged into one.

| Source | Era | Locator | States |
|---|---|---|---|
| `msca-dn-2025-esr.json` | historical | `evaluation_result/criteria` | three criterion scores, and no aspect score, in the 2025 evaluation |
| `msca-dn-2025-esr.json` | historical | `observations` | every recorded observation, none of which carries a score |
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | historical | `page 123` | the work programme of the 2025 call states the same rule |
| `wp-15-general-annexes_horizon-2026-2027_en.pdf` | current | `page 27` | the 2026 General Annexes on what a score is awarded for |

> Evaluation scores will be awarded for each of these criteria, and not for the different aspects listed in the table below.

> Evaluation scores will be awarded for the criteria, and not for the different aspects listed in the table.

- Measured: three criterion scores — `evaluation_result/criteria` is length 3
- Measured: 29 observations, none with a score — `observations` is length 29

#### EI-04 — equivalent

The applicability-tag grammar that selects which of the evaluation form's aspects a Doctoral
Network proposal is graded on.

- Affects: a number
- Settles: call wide
- 2025: the evaluation form of the 2025 call window carries the same tag grammar, and names this action type in the tags that select the ten aspects
- 2026: Keep every aspect whose [OPTION for ...] tag names MSCA Doctoral networks, plus the 'all MSCA except ...' aspects whose exception list does not name it. Exclude every Postdoctoral fellowships, Staff exchanges, COFUND, COFUND Choose Europe and Special needs allowances variant.
- Status: **Inferred** — The grammar is the evaluation form's alone: this module refuses to render if either application form carries an applicability tag, and neither does. The 2025 form carries it, and row CR-02 measures that the aspects it selects for this action type are the scorecard's ten, each under the same criterion. One tag's scope did move between the eras, and it does not move the selection: the 2025 tag names a third action type that the 2026 tag does not, and this action type is named in both. Inferred for the reason EI-02 gives.
- For the historical profile: The historical profile keeps the tag grammar and the scope rule, cited to the 2025 form. CR-02 carries the measured selection, so no row rests on the assumption that the two forms tagged alike.

| Source | Era | Locator | States |
|---|---|---|---|
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 4` | a 2025 tag naming this action type for one of the ten aspects |
| `ef_he-msca_v2.0_2025-02-28.pdf` | historical | `page 4` | the one tag whose scope moved, as the 2025 form states it |
| `ef_he-msca_en.pdf` | current | `page 4` | and as the 2026 form states it, with a third action type dropped |
| `evaluator_scorecard_msca_dn.json` | current | `provenance/dn_scope_rule` | the scope rule derived from the 2026 evaluation form's tags |
| `msca_dn_2026_default.json` | current | `option_tag_grammar` | the tag vocabulary the 2026 profile declares |

> [OPTION for MSCA Doctoral networks Quality and credibility of the training programme

> [OPTION for MSCA Doctoral networks, Postdoctoral fellowships and Staff exchanges:

> [OPTION for MSCA Doctoral networks, Postdoctoral fellowships:

### Variant

#### VA-01 — equivalent

Which Doctoral Network implementation mode the 2025 submission used.

- Affects: an interpretation
- Settles: as applied to this submission
- 2025: standard Doctoral Network, not an Industrial Doctorate and not a Joint Doctorate
- 2026: standard Doctoral Network (not DN-ID, not DN-JD)
- Status: **Inferred** — The fidelity register declares the mode Confirmed on a phrase its authoring tool checks on page 32 of the sanitised copy. This row is Inferred rather than Confirmed because no hash from an issuing body vouches for that copy's bytes.
- For the historical profile: The historical profile declares the same implementation mode, sourced to the submission's own text.

| Source | Era | Locator | States |
|---|---|---|---|
| `fidelity_register.json` | historical | `provenance/historical_submission/dn_type/basis` | the page of the submission the mode is checked on |
| `msca_dn_2026_default.json` | current | `implementation_mode` | the mode the 2026 profile declares |

> the sanitised copy states it on p. 32; the tool checks the phrase on that page

> standard Doctoral Network (not DN-ID, not DN-JD)

- Measured: the fidelity register declares the mode Confirmed — `provenance/historical_submission/dn_type/declared_status` is 'Confirmed'
- Measured: and the 2026 profile declares the same mode — `implementation_mode` is 'standard Doctoral Network (not DN-ID, not DN-JD)'

#### VA-02 — equivalent

The implementation modes the application form recognises, and which must be declared in the Part B
header.

- Affects: an interpretation
- Settles: call wide
- 2025: DN, DN-ID or DN-JD
- 2026: DN, DN-ID or DN-JD
- Status: **Inferred** — The same sentence is located in both application forms, verbatim, and the 2025 form is a 2025-call document rather than evidence about one submission.
- For the historical profile: The historical profile may declare the mode vocabulary as sourced to the 2025 form, not carried from the 2026 one.

| Source | Era | Locator | States |
|---|---|---|---|
| `af_he-msca-dn_en.pdf` | historical | `page 25` | the 2025 form on the modes a Part B header must declare |
| `Tpl_Application Form (Part B) (HE MSCA DN).pdf` | current | `page 5` | the same sentence in the 2026 form |

> the implementation mode applied to (i.e. DN, DN-ID or DN-JD)

> the implementation mode applied to (i.e. DN, DN-ID or DN-JD)

### Section mapping

#### SM-01 — equivalent

The ten numbered Part B aspect headings the criteria decompose into, sections 1.1 to 3.2.

- Affects: an interpretation
- Settles: call wide
- 2025: the same ten headings, all occurring verbatim in the 2025 form, and its criteria table carries no eleventh aspect anchor
- 2026: the ten headings the scorecard derives from the 2026 form
- Status: **Inferred** — Ten citations, one per heading, each located in the 2025 form and each quote verified to occur on the page it cites. That settles one direction. The other is measured: the anchors printed across each form's criteria table are read out and compared, with the page either side of the table required to carry none, and both sets are exactly 1.1 1.2 1.3 1.4 2.1 2.2 2.3 2.4 3.1 3.2. This module refuses to render if either set stops matching the scorecard's, or if the page rule stops matching the scorecard's own declared 2026 pages.
- For the historical profile: The historical profile reuses the criterion-to-section mapping unchanged, with this row as the source.

| Source | Era | Locator | States |
|---|---|---|---|
| `af_he-msca-dn_en.pdf` | historical | `page 49` | aspect exc-obj (1.1) is a Part B heading of the 2025 form, verbatim |
| `af_he-msca-dn_en.pdf` | historical | `page 49` | aspect exc-method (1.2) is a Part B heading of the 2025 form, verbatim |
| `af_he-msca-dn_en.pdf` | historical | `page 49` | aspect exc-training (1.3) is a Part B heading of the 2025 form, verbatim |
| `af_he-msca-dn_en.pdf` | historical | `page 50` | aspect exc-supervision (1.4) is a Part B heading of the 2025 form, verbatim |
| `af_he-msca-dn_en.pdf` | historical | `page 50` | aspect imp-structuring (2.1) is a Part B heading of the 2025 form, verbatim |
| `af_he-msca-dn_en.pdf` | historical | `page 50` | aspect imp-career (2.2) is a Part B heading of the 2025 form, verbatim |
| `af_he-msca-dn_en.pdf` | historical | `page 50` | aspect imp-dissemination (2.3) is a Part B heading of the 2025 form, verbatim |
| `af_he-msca-dn_en.pdf` | historical | `page 50` | aspect imp-magnitude (2.4) is a Part B heading of the 2025 form, verbatim |
| `af_he-msca-dn_en.pdf` | historical | `page 50` | aspect impl-workplan (3.1) is a Part B heading of the 2025 form, verbatim |
| `af_he-msca-dn_en.pdf` | historical | `page 52` | aspect impl-participants (3.2) is a Part B heading of the 2025 form, verbatim |

> Quality and pertinence of the project’s research and innovation objectives (and the extent to which they are ambitious, and go beyond the state of the art)

> Soundness of the proposed methodology (including interdisciplinary approaches, consideration of the gender dimension and other diversity aspects if relevant for the research project, and the quality and appropriateness of open science practices)

> Quality and credibility of the training programme (including transferable skills, inter/multidisciplinary, inter-sectoral and gender as well as other diversity aspects)

> Quality of the supervision (including mandatory joint supervision for industrial and joint doctorate projects)

> Contribution to structuring doctoral training at the European level and to strengthening European innovation capacity, including the potential for: a) Meaningful contribution of the non-academic sector to the doctoral training, as appropriate to the implementation mode and research field b) Developing sustainable (=lasting) elements of doctoral programmes after the end of the DN funding

> Credibility of the measures to enhance the career perspectives and employability of researchers and contribution to their skills development

> Suitability and quality of the measures to maximise expected outcomes and impacts, as set out in the dissemination and exploitation plan, including communication activities

> The magnitude and importance of the project’s contribution to the expected scientific, societal and economic impacts (project’s pathways towards impact)

> Quality and effectiveness of the work plan, assessment of risks and appropriateness of the effort assigned to work packages

> Quality, capacity and role of each participant, including hosting arrangements and extent to which the consortium as a whole brings together the necessary expertise

- Measured: criterion excellence carries the aspects this row enumerates — `criteria/#0/aspects` is length 4
- Measured: criterion impact carries the aspects this row enumerates — `criteria/#1/aspects` is length 4
- Measured: criterion implementation carries the aspects this row enumerates — `criteria/#2/aspects` is length 2

#### SM-02 — equivalent

The Part B1 length limits: 34 pages in total, of which 30 are available to sections 1 to 3.

- Affects: an interpretation
- Settles: call wide
- 2025: 34 pages in total, 30 for sections 1 to 3
- 2026: 34 pages in total, 30 for sections 1 to 3
- Status: **Inferred** — Both sentences are located in the 2025 form and in the 2026 form, verbatim. The form-equivalence record is cited as corroboration and is within the scope it measured; the 2025 form itself is what settles the row.
- For the historical profile: No page-based judgment is admissible over the sanitised copy at all, which the fidelity register declares. The limits are recorded because the historical profile's structural authority has to name them.

| Source | Era | Locator | States |
|---|---|---|---|
| `af_he-msca-dn_en.pdf` | historical | `page 24` | the 2025 form's total cap |
| `af_he-msca-dn_en.pdf` | historical | `page 24` | the 2025 form's cap on sections 1 to 3 |
| `Tpl_Application Form (Part B) (HE MSCA DN).pdf` | current | `page 4` | the 2026 form's total cap |
| `evaluator_scorecard_msca_dn.json` | current | `provenance/v5_equivalence/statement` | the form-equivalence record, within the section structure it measured |

> The maximum total length for this document is 34 pages.

> Of the maximum 30 pages applied to sections 1, 2 and 3, applicants are free to decide on the allocation of pages between the sections.

> The maximum total length for this document is 34 pages.

> For HORIZON-MSCA-2026-DN-01 the V5.0 (2025 call) and V6.0 (2026 call) Part B templates are structurally identical: the same ten numbered aspect headings §1.1 to §3.2, the same Tables 3.1 a to 3.1 e, the same 34-page Part B1 cap with sections 1-3 at 30, the same Part B2 sections 4 to 10. V6.0 adds Part B2 section 11 (RAISE DN) for a different call. Measured in spec §2.12.

#### SM-03 — differs

Which sections Part B2 contains.

- Affects: an interpretation
- Settles: call wide
- 2025: Part B2 ends at section 10, the declaration on the use of AI
- 2026: Part B2 adds section 11, RAISE DN, for a different call
- Difference: The 2026 form adds a Part B2 section 11 the 2025 form does not have. It is reserved for applicants of another call, so no 2025 submission could have had one.
- Status: **Inferred** — The 2025 form's section 10 is followed by its example block; the 2026 form's section 10 is followed by section 11. Both quotes are verified on the pages they cite.
- For the historical profile: The appendix mapping's rule excluding Part B2 section 11 has no subject under the 2025 form. The historical profile keeps the rule and records that it is vacuous rather than deleting it.

| Source | Era | Locator | States |
|---|---|---|---|
| `af_he-msca-dn_en.pdf` | historical | `page 44` | the 2025 form's last Part B2 section, followed by its example block |
| `Tpl_Application Form (Part B) (HE MSCA DN).pdf` | current | `page 23` | the section the 2026 form adds after section 10 |

> 10. Declaration on the use of AI Example, not to be completed

> 11. RAISE DN (Only for applicants of HORIZON-RAISE-2026-01-MSCA, 1 page)

### Appendix mapping

#### AM-01 — equivalent

The cross-references that route table rows to criteria at the criterion-grading stage.

- Affects: a number
- Settles: call wide
- 2025: all 11 distinct cross-reference sentences occur verbatim in the 2025 form
- 2026: 7 mapping rows, derived from the 2026 form
- Status: **Inferred** — One citation per distinct sentence, each located in the 2025 form and verified on the page it cites. This is the row the form-equivalence record could not settle: that record measured headings, tables, caps and section numbering, not the instructional sentences the mapping routes on. The claim is an inclusion and not a set equality. Every sentence the 2026 mapping routes on is in the 2025 form; whether the 2025 form carries a further cross-reference the mapping has no row for is unmeasured, and cannot be searched for without the 2025 mapping's own list. Row SM-01 settles the aspect anchors in both directions, which bounds what such a sentence could reroute.
- For the historical profile: The historical profile reuses the appendix mapping unchanged, sourced to the 2025 form rather than carried over on the form-equivalence record. The unmeasured direction stays an uncertainty of this matrix and is not closed by this row.

| Source | Era | Locator | States |
|---|---|---|---|
| `af_he-msca-dn_en.pdf` | historical | `page 31` | the cross-reference the appendix mapping routes on, in the 2025 form |
| `af_he-msca-dn_en.pdf` | historical | `page 31` | the cross-reference the appendix mapping routes on, in the 2025 form |
| `af_he-msca-dn_en.pdf` | historical | `page 38` | the cross-reference the appendix mapping routes on, in the 2025 form |
| `af_he-msca-dn_en.pdf` | historical | `page 33` | the cross-reference the appendix mapping routes on, in the 2025 form |
| `af_he-msca-dn_en.pdf` | historical | `page 35` | the cross-reference the appendix mapping routes on, in the 2025 form |
| `af_he-msca-dn_en.pdf` | historical | `page 50` | the cross-reference the appendix mapping routes on, in the 2025 form |
| `af_he-msca-dn_en.pdf` | historical | `page 37` | the cross-reference the appendix mapping routes on, in the 2025 form |
| `af_he-msca-dn_en.pdf` | historical | `page 34` | the cross-reference the appendix mapping routes on, in the 2025 form |
| `af_he-msca-dn_en.pdf` | historical | `page 38` | the cross-reference the appendix mapping routes on, in the 2025 form |
| `af_he-msca-dn_en.pdf` | historical | `page 39` | the cross-reference the appendix mapping routes on, in the 2025 form |
| `af_he-msca-dn_en.pdf` | historical | `page 39` | the cross-reference the appendix mapping routes on, in the 2025 form |
| `criterion_appendix_mapping_msca_dn.json` | current | `rows` | the mapping rows these sentences are the authority for |

> The action should be divided in Work Packages and described in the Table 3.1a under the Implementation section.

> Describe each DC’s individual research project, including for each a title, objectives, expected results, and planned secondments (purpose, timing, duration, host, sector).

> Total duration of secondments (months)

> To avoid duplication, the role and scientific profile of the supervisors should only be listed in the "Participating Organisations" tables (see section 8 below).

> Concrete plans for sections 2.3 must be included in the corresponding table 3.1 a Description of Work Packages.

> Concrete plans for sections 2.3 must be included in the corresponding implementation tables.

> PDE = dissemination and/or exploitation of results

> meaningful exposure of Doctoral Candidates to the non-academic sector through secondments

> Total duration in non- academic sector (months)

> Appropriateness of the infrastructure and capacity of each participating organisation, as outlined in Section 8 (Participating Organisations), in light of the tasks allocated to them in the action;

> Role of associated partners to the programme (please see also section 8).

### Scoring assumption

#### SA-01 — equivalent

The weighted total is each criterion score times its weight in percent over five, summed.

- Affects: a number
- Settles: as applied to this submission
- 2025: Evaluation Result Total score: 85.80 % (Threshold: 70 /100.00)
- 2026: S = 10·E + 6·I + 4·Q
- Status: **Inferred** — Arithmetic evidence, and now a rule to match it. The formula applied to the 2025 evaluation's own recorded criterion scores reproduces its own recorded total, and this module refuses to render if it stops doing so. The work programme of the call states the two inputs the formula is built from: a maximum of five per criterion and the weighting row. Inferred, not Confirmed, for the reason CR-01 gives.
- For the historical profile: The historical profile keeps the total formula. It is the one scoring rule whose 2025 application is evidenced by arithmetic rather than by wording.

| Source | Era | Locator | States |
|---|---|---|---|
| `msca-dn-2025-esr.json` | historical | `evaluation_result/total` | the total the formula has to reproduce |
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | historical | `page 123` | the work programme on the maximum each criterion is scored out of |
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | historical | `page 124` | and on the weights the total applies to those scores |
| `evaluator_scorecard_msca_dn.json` | current | `scoring/total_formula` | the formula, as the 2026 scorecard holds it |

> Each criterion will be scored out of 5.

> 50% 30% 20% Weighting

> S = 10·E + 6·I + 4·Q

- Measured: the recorded total the formula reproduces — `evaluation_result/total` is 85.8

#### SA-02 — era_neutral

Criterion grading draws five samples per criterion and reports the median with its spread,
labelled within-assessor repeatability.

- Affects: a number
- Settles: as applied to this submission
- 2026: N=5 per criterion score, median and spread reported
- Why no era states it: The sample count and the statistic belong to the assessing harness, not to either call. No call document states them, and neither can differ between the two calls.
- Status: **Inferred** — The specification's decisions 5 and 11 fix the sample count and the statistic. The citation resolves as text in the specification, so a reworded decision fails the check.
- For the historical profile: The historical profile inherits the method. The matrix records that it is not a 2025 rule and cannot be sourced to one, so a difference between the assessor's median and the 2025 total is not attributable to a rule change.

| Source | Era | Locator | States |
|---|---|---|---|
| `msca_dn_pre_evaluation_spec.md` | cross_era | `five samples per criterion` | the specification's decision on the criterion-grading stage |
| `msca_dn_pre_evaluation_spec.md` | cross_era | `N=5 for the three criterion scores` | the specification's decision on the sample count and the statistic |

#### SA-03 — era_neutral

Where the evidence pack carries no claim ledger, a cell reports grounding unassessable — never
failed and never passed.

- Affects: an interpretation
- Settles: as applied to this submission
- 2026: grounding unassessable where no ledger reaches the pack
- Why no era states it: The rule governs how this harness reports an axis it cannot assess over a damaged copy. No call document states it, in either year.
- Status: **Inferred** — The specification's decision 14 states the rule. The citation resolves as text in the specification.
- For the historical profile: The historical profile inherits the rule. A grounding result is reported as unassessable and is never read as a score the 2025 evaluators would recognise.

| Source | Era | Locator | States |
|---|---|---|---|
| `msca_dn_pre_evaluation_spec.md` | cross_era | `the cell reports grounding **unassessable**` | the specification's decision on an unassessable axis |

#### SA-04 — era_neutral

The assessed text is a sanitised derivative produced after the evaluation, not the text the 2025
evaluation read.

- Affects: both
- Settles: as applied to this submission
- 2025: This file is not the text the ESR evaluated. It is a derivative produced by sanitisation after evaluation, and no result over it is a result over the submission.
- Why no era states it: The candidate's fidelity is not a rule either call states. It is the condition of the document being assessed, and it bounds every row above regardless of which year's rules apply.
- Status: **Inferred** — The fidelity register states it over the file it pins by hash. This is a property of one derivative, measured on it.
- For the historical profile: No result over this copy is a result over the submission. The historical profile changes nothing about that, and a comparison with the 2025 total carries the statement.

| Source | Era | Locator | States |
|---|---|---|---|
| `fidelity_register.json` | historical | `provenance/current_assessment_artifact/statement` | the register's statement over the file it pins |

> This file is not the text the ESR evaluated. It is a derivative produced by sanitisation after evaluation, and no result over it is a result over the submission.

- Measured: the assessed file is declared not to be the submitted document — `provenance/current_assessment_artifact/is_submitted_document` is False

#### SA-05 — era_neutral

A blind cell reports addressal and grounding as two values, and never blends them into one.

- Affects: an interpretation
- Settles: as applied to this submission
- 2026: two values per cell, grounding never folded into addressal
- Why no era states it: What a cell reports is this harness's own output shape. Neither call states it, and neither could: no 2025 or 2026 document knows of a cell.
- Status: **Inferred** — The specification's decision 4 states the rule and its reason. The citation resolves as text in the specification, so a reworded decision fails the check.
- For the historical profile: The historical profile inherits the two-value cell. A reader comparing a cell with a 2025 criterion score is comparing an assessor's two axes with an evaluator's single grade, which this row records as a method difference rather than a rule difference.

| Source | Era | Locator | States |
|---|---|---|---|
| `msca_dn_pre_evaluation_spec.md` | cross_era | `reports addressal and grounding as two values` | the specification's decision on what a blind cell reports |

#### SA-06 — era_neutral

The criterion scorer reads the complete criterion section plus the declared appendix rows, with no
selection and no budget filler.

- Affects: a number
- Settles: as applied to this submission
- 2026: the whole section verbatim, within the 32,768-token pack budget, with every declared appendix row resolved
- Why no era states it: An evaluator reads the proposal. A pack budget and a selection rule are properties of the assessing harness, so no call document of either year states them.
- Status: **Inferred** — The specification states the input and its bound, and both citations resolve as text in it. What the scorer reads is a harness decision, not a call rule, which is why it is recorded here rather than compared across the two years.
- For the historical profile: The historical profile inherits the input rule. A truncated or selected input would change a criterion score without any 2025 rule changing, which is why the bound is recorded as a scoring assumption and not left implicit.

| Source | Era | Locator | States |
|---|---|---|---|
| `msca_dn_pre_evaluation_spec.md` | cross_era | `the criterion lane carries no selection at all` | the specification on selection in the criterion lane |
| `msca_dn_pre_evaluation_spec.md` | cross_era | `the assembled input fit the budget without truncation` | the specification's acceptance condition on the criterion input |

### Call identity

#### CI-01 — unresolved

Which call the 2025 submission was evaluated under. Every other row's 2025 side is addressed to
this call.

- Affects: an interpretation
- Settles: as applied to this submission
- Limitation: The call itself is now pinned. The work programme part states its identifier, its opening date and its deadline, so the call this submission is declared against exists and its conditions are held. What is still missing is the binding: the Evaluation Summary Report names no proposal number, and nothing in this repository shows this submission was entered into that call. Two records declare the binding, and a declaration is not evidence of it.
- Status: **Assumed** — Two records declare the identifier Assumed and give the same reason. The value is the operator's declaration, and this module refuses to render if either record stops declaring it Assumed. The work programme now evidences that a call with that identifier existed, with the dates it cites. It does not evidence that this submission was made to it, which is what the row is about, so the status stays Assumed.
- For the historical profile: The historical profile carries the operator's declared call identifier with declared_status Assumed, never Confirmed, and the matrix is cited as the reason.
- Would be settled by: `docs/tier3_project_instantiation/source_materials/msca_dn/submission_acknowledgement.pdf`

| Source | Era | Locator | States |
|---|---|---|---|
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | historical | `page 23` | the work programme states the identifier of the 2025 call |
| `wp-2-msca-actions_horizon-2023-2025_en.pdf` | historical | `page 23` | and that call's opening date and deadline |
| `msca-dn-pe01-workspace_2026-10-04.json` | cross_era | `declared_values/historical_call_id/reason` | the PE-01 decision records the call identifier as the operator's declaration |
| `fidelity_register.json` | historical | `provenance/historical_submission/call_id/basis` | the fidelity register records the same basis for the same identifier |

> Call - MSCA Doctoral Networks 2025 HORIZON-MSCA-2025-DN-01 Conditions for the Call

> Opening: 28 May 2025 Deadline(s): 25 Nov 2025

- Measured: the PE-01 decision declares the call identifier Assumed — `declared_values/historical_call_id/declared_status` is 'Assumed'
- Measured: the fidelity register declares the same identifier Assumed — `provenance/historical_submission/call_id/declared_status` is 'Assumed'

## What the author of this matrix is unsure of

- No row is defaulted. Two are unresolved, and each names what is missing: the binding of this submission to a call, and the evaluation form version the 2025 evaluators were given.
- Twenty-five rows are Inferred and none is Confirmed. Every 2025 document here is hashed in this tree and none carries a hash published by its issuing body, so no row may be Confirmed on byte integrity. Three documents are corroborated by a second independent copy, which raises what is known about their origin and not about what governed the call.
- Two 2025 authorities state different score resolutions. The work programme says one decimal place, the evaluation form says half marks. TH-05 shows which was applied to this submission, from a recorded score no half-mark rule could award. It does not resolve the conflict in general, and a statement about any other 2025 proposal must carry it.
- Every row citing the 2025 evaluation form inherits EI-02's bracket. Three captures of one archive are one witness observed three times, and a version served between two captures and never captured would leave no trace.
- The 2025 application form has no recorded origin, and nothing establishes it was the version in force. The five rows citing it are Inferred for that reason, and retrieving a corroborating copy of it is not attempted here.
- A sourced row claims what its citations measure and no more. SM-01 compares the aspect anchors in both directions; AM-01 claims an inclusion only, so a 2025 cross-reference the 2026 mapping has no row for would not have been seen.
- Whether an area's rows are all of its scoring-relevant rules is this author's judgement. The check reads what each row cites and refuses an unsourced relation; it cannot report a rule nobody wrote a row for.
- The rows sourced to the 2025 evaluation's own record settle what was applied to this submission. None of them settles a rule of the 2025 call, and the check refuses a call-wide claim resting only on them.
- EI-01, the six score-level descriptions, was the largest unsourced input to a numerical comparison. All six sentences are now located in the 2025 form, word for word, so the comparison no longer rests on a 2026 document alone.
- This matrix quotes the 2025 evaluation's recorded figures. It lives beside the ESR record, outside the dev-graph root, and is not snapshotted; the blind lane's isolation rests on that exclusion and on the assessor running with no tools from outside the repository, exactly as it does for the ESR record itself.
