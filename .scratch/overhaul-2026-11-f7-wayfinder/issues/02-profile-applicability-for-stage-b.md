# 02 — Is `msca_dn_2026_default` an applicable, sourced profile for Stage B?

Type: research
Status: resolved
Blocked by: None
Map: ../map.md

## Question

V16 requires "the resubmission profile's applicability is confirmed for Stage B". For 2025, the profile
was authored from an authority matrix (V09 → V10: pinned authority documents, equivalence matrix,
`msca_dn_2025_historical.json`). Does `harness/profiles/msca_dn_2026_default.json` have equivalent
sourcing: target call, WP 2026–2027 and evaluation-form version, scorecard and rubric provenance, with
hashes? If not, what exactly is missing for an applicability confirmation, and is closing it config or
authoring work, or harness code?

Answer with the provenance found for each profile field, the gaps, and the smallest action that would let
the operator confirm applicability.

## Answer (2026-11-06)

Full findings: [../W02-findings.md](../W02-findings.md).

- **Sourced, but not in the profile file, and not yet confirmed.** The 2026 profile is a thin PE-02 pointer
  file; its inputs are sourced elsewhere: the scorecard is derived from the stored forms and re-derived by a
  test, and every 2026 document (V6.0 template, evaluation form v2.2, WP 2026–2027, General Annexes
  2026–2027, scorecard, the profile, the appendix mapping) is pinned in the V09 source index. All hashes
  still match.
- **Gaps:** the call binding (the operator's declaration, as CI-01 is for 2025); the evaluation-form version
  the 2026 evaluators use (v2.2 Inferred); the target call is cited to the unpinned portal JSON, not the
  pinned WP (p. 12 states the call and 24 Nov 2026); no advisory/review status on the profile.
- **Smallest action: an operator-reviewed applicability decision record. No harness code, nothing for the cut.**
- Side: the WP deadline is **24 Nov 2026**, not 23 Nov; W01's three-section assumption is confirmed.
