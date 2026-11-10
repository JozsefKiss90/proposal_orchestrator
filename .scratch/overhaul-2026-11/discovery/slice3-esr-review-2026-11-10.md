# Slice 3 review (ESR side) — 2026-11-10

Review only, at `1ab64dc2` (`harness_overhaul`, wave 1 merged). Bar from the handoff (§5): a finding
gets a ticket only if it would make V14's ESR comparison wrong or crash it.

Scope read: the `compare`, `review` and `diff` command glue in `harness/commands/blind_assessment.py`;
`harness/esr_comparison.py` (loading, binding, `run_comparison`, row rules, the preservation rule,
`_summarise`, `_compare_scores`, `_prioritise`); `harness/operator_review.py` (`resolve_inputs`,
`recount`, `cross_check_counts`, row rendering); the V18 register's declared half
(`tools/author_original_workspace.py`, `tools/fidelity_declarations.py`). Not read in depth:
`comparison_diff.py` (V14 uses it only between two private comparisons over one baseline, which it
binds), `deferral_register.py` and `authority_matrix.py` (they feed `historical_profile --check`,
not the comparison; ticket 16 fixed that command).

## Verdict

**No ticket.** Nothing on V14's path crashes or miscounts. Every input is bound by hash and
fail-closed with a named reason; the ESR record's criteria must equal the baseline's; counts are
recomputed by the review and cross-checked against the comparison. The score scales agree (ESR total
85.8 on 100; blind total from `S = 10*excellence + 6*impact + 4*implementation`).

## Findings below the bar

**F1 — fixed prose assumes the candidate is the sanitised copy (wrong for V14; numbers unaffected).**
- `esr_comparison._SCORE_STATEMENT`: "The candidate is a sanitised derivative of the assessed
  document, so a difference … may equally be changed wording, removed evidence or assessor variance."
  For V14 the candidate is the submission: only assessor variance, the profile and the extraction remain.
- Each row's `historical_proposal_evidence.note`: "The submitted document is not available in this
  environment …".
- `operator_review` inventory notes ("the materialised sanitised copy every quote below is checked
  against", "the earlier sanitised copy") and the row heading "The same passages in the earlier
  sanitised copy".
Same class as ticket 11's register sentences. Proposed handling: a caveat in V14's (and V16's)
operator review notes; fix after V16 in one wave-2 ticket keyed on the register's
`is_submitted_document`, which `compare` already loads.

**F2 — a Confirmed miss needs `fidelity_to_submitted_original` in the original's declared half.**
`check_preservation_claim` refuses `evidence_preserved_status: Confirmed` unless the register's
declared row for the quoted sub-section carries `fidelity_to_submitted_original` (scope
`fidelity_against_the_submitted_original`, status Confirmed, a basis, an evidence item naming the
observation with source and statement), and the row's `evidence_basis` points at it. The original's
register note says that question "does not arise here", and its contract requires only `presence`
and `extraction_fidelity`; extra fields are carried through unchanged, so the operator can and must
add the block to the original's declaration input (runbook §5, "against the original and only
there"). Failure mode is a named refusal at `compare`, re-runnable with no assessor cost; an
`Inferred` status passes but understates. Runbook should state where the block goes.

**F3 — audit references match by path spelling.** `--audit` paths outside the repository are keyed
as given (`as_posix()`), and each disposition's `audit_findings[].report` must use the same
spelling. A mismatch is a refusal that lists the loaded keys. Runbook note.
