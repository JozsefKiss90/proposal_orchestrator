# Historical pre-evaluation profile — MSCA Doctoral Networks — 2025 historical pre-evaluation profile, authored from the equivalence matrix

Authored 2026-10-13. Profile `msca_dn_2025_historical`, schema `pre_evaluation_profile/historical/1`,
written by `tools/author_msca_dn_historical_profile.py`.

Review state: **agent drafted pending operator review**.
The profile's own reading of its sources is declared **Inferred**.

Score the submitted 2025 original under the rules of its own call. Every element below either
names the matrix rows that establish the 2025 rule, or declares what the matrix left open. An
element that did neither would be the 2026 profile under another name.

## What the matrix sources

| Element | Matrix rows | Verdicts |
|---|---|---|
| criteria | `CR-01`, `CR-02` | equivalent, equivalent |
| criterion_appendix_mapping | `AM-01` | equivalent |
| implementation_mode | `VA-01`, `VA-02` | equivalent, equivalent |
| individual_threshold | `TH-01` | equivalent |
| option_tag_grammar | `EI-04` | equivalent |
| overall_threshold | `TH-02`, `TH-03`, `TH-06` | equivalent, equivalent, differs |
| score_levels | `EI-01` | equivalent |
| score_maximum | `TH-04` | equivalent |
| score_resolution | `TH-05` | equivalent |
| scores_are_per_criterion | `EI-03` | equivalent |
| structural_authority | `SM-01`, `SM-02`, `SM-03` | equivalent, equivalent, differs |
| weighting_is_for_ranking | `WT-02` | equivalent |
| weights | `WT-01`, `SA-01` | equivalent, equivalent |

## What the matrix leaves open

**target_call** — row `CI-01` (unresolved)

The call's own identifier, opening and deadline are stated by the work programme the call was
opened under. That this submission was entered into that call is declared by two records and
evidenced by neither, so the binding is Assumed.

**scorecard** — row `EI-02` (unresolved)

The scorecard is derived from the 2026 evaluation form, and every scoring rule it carries is
sourced to a 2025 document by the rows above. Which version of the evaluation form the 2025
evaluators were given is not established: captures of the published address bracket the call
window without closing it.

## What neither call states

These are this harness's own instruments, not rules of either call. The matrix carries their rows
as era neutral, so reusing them is a reuse of an instrument and not a finding that a call
prescribed it.

| Element | Matrix rows |
|---|---|
| rubric_set | `SA-02`, `SA-03`, `SA-05`, `SA-06` |
| assessed_text | `SA-04` |

## What it was derived from

| Record | Path | sha256 |
|---|---|---|
| matrix | `docs/tier4_orchestration_state/msca_dn/authority/equivalence_matrix_2025_2026-10-13.json` | `2e1fba3b3bf5bc8609911250d66e04b70e791af091402f8cf78cb87c2da9a273` |
| source_index | `docs/tier4_orchestration_state/msca_dn/authority/authority_source_index_2026-10-13.json` | `cfb935b0e0e9c42e3e14701d870645017a89822a3792d1a58441e64b1c853575` |
| counterpart, not edited | `harness/profiles/msca_dn_2026_default.json` | `308a955dada102e92212f87c43cdf28576b49f1cb2a6894acb64c2ac87a3fee2` |

Every one is pinned by the sha256 of its bytes. A profile read beside a record that has moved is
stale, and the check reports it rather than scoring under it.

