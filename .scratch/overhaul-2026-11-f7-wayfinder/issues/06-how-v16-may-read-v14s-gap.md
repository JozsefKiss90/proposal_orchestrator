# 06 — What may the V16 report say about V14's measured gap?

Type: grilling
Status: resolved
Blocked by: 05
Map: ../map.md

## Question

V14 measures the original-vs-ESR gap for the 2025 candidate under the historical profile. V16 assesses a
different candidate under a different profile, and the ledger forbids reusing any freeze, preflight or
scoring result across candidate/profile pairs. AN15 also says a delta is "never a correction factor".
Decide with the operator what the V16 report and the operator's reading may say about V14's gap:

- nothing;
- a qualitative caveat;
- a side-by-side with explicit non-comparability;
- something else.

Also decide whether that needs harness support (a report field, a successor record linking the two
freezes) or is prose in the operator's review. Without X04 (out of scope), any cross-run link must not
weaken a binding check.

## Answer (2026-11-06, grilled with the operator)

**A qualitative caveat, in prose only.** The operator's review of V16 may say how far the harness's scoring
stood from the 2025 evaluators on the 2025 text (V14), with an explicit statement that this is not a
correction factor (AN15) and not comparable across candidate/profile pairs (ledger). **No harness support:**
no report field and no record linking the two freezes, so no binding check is weakened and nothing new has to
land. X04 stays out of scope.
