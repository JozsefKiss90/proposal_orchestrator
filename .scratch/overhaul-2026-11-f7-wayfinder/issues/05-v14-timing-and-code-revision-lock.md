# 05 — When does V14 run, and on which locked code revision?

Type: grilling
Status: open
Blocked by: 03, 04
Map: ../map.md

## Question

V14 must lock its code revision before any ESR material is read. V16 must use "the same model and sample
plan" (decision 3), so the 2026 score can be read against V14's gap. Harness changes landing between the
two runs would weaken that. Decide with the operator:

1. Does V14 run **after** the 10 Nov freeze, on the same locked revision V16 will use? Or before it, on
   HEAD-of-today, accepting that on-path tickets landing afterwards make the two runs non-comparable?
2. The AN12 host steps (bundle install, synthetic pipeline run, synthetic Converse freeze): on which date,
   and are they re-run after the freeze, since the offline bundle carries the code?
3. Does the V14 → V16 calendar (incl. AN15 if 04 says so) fit before 23 Nov at the declared sample plan?

The answer is a dated operator schedule plus the locked-revision rule, which feeds the must-land list.
