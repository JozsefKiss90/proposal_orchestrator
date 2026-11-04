# 06 — What may the V16 report say about V14's measured gap?

Type: grilling
Status: open
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
