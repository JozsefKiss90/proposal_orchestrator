# 05 — When does V14 run, and on which locked code revision?

Type: grilling
Status: resolved
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

## Answer (2026-11-06, grilled with the operator)

Inputs: W01, W02, W03 findings (this folder); W04 skipped (AN15 does not ride).

| # | Question | Decision |
|---|----------|----------|
| Q0 | Transport for V14 and V16 | **Bedrock Converse on the private eu-north-1 host** (map decision 3 kept). `claude-cli` is not used for private content. The host does not exist yet, so R11 is on the critical path. |
| Q1 | Locked-revision rule | **One offline bundle, built from the 10 Nov freeze commit, serves both V14 and V16. Nothing lands between them.** A defect is fixed mid-way only if it blocks a run; if that fix changes assessment output, V14 is re-run on the new bundle, or the two reports are marked non-comparable. Consequence: ticket 01 (the only keep that changes assessment output) lands before 10 Nov or after V16. |
| Q2 | AN12 host steps | **Criteria 1 (offline install) and 3 (synthetic Converse blind pass frozen with a validated receipt) only**, on the freeze-commit bundle, right after R11. Criterion 2 (A0–A7 anonymisation pipeline) is not run; AN12 stays open. |
| Q3 | Calendar | Tue 10 Nov freeze commit + bundle build → Wed 11 R11 (host + endpoints) → Thu 12 AN12 criteria 1 + 3 → Fri 13–Sun 15 V14 (dry import, configuration, import, preflight, assess, freeze, then ESR compare) → **one V16 run on the near-final 2026 text, ~Thu 19–Fri 20 Nov** → deadline Tue 24 Nov (WP 2026–2027 p. 12). |

Risk: R11 is the calendar's single point of failure. With `claude-cli` ruled out there is no fallback route, so a slip on 11–12 Nov is taken out of V14's days.
