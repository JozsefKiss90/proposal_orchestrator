# 04 — Does AN15 (score fidelity of the derivative) ride in the V14 session?

Type: grilling
Status: resolved
Blocked by: None
Map: ../map.md

## Question

The AN chain is in scope. AN15 runs inside the V14 private session, after the original's blind run is
frozen, and needs AN14 → AN13 → AN12a first. AN12a is **code** (applying the A3 rewrite plan) and
isn't built yet. AN13 and AN14 are operator runs. Is AN15 part of the V14 session before 23 Nov? If so:

- AN12a joins the must-land-by-10-Nov list;
- AN13 and AN14 join the operator schedule ahead of V14.

If not, the AN chain is deferred past 23 Nov, and the map records why it stays in scope but not on the
critical path. Decide with the operator, one question at a time.

## Answer (2026-11-06)

**Skipped by the operator; taken as the "if not" branch.** AN15 does not ride in the V14 session before
23 Nov. Consequences:

- AN12a is **not** on the must-land-by-10-Nov list; AN13 and AN14 are not on the operator schedule ahead of V14.
- The AN chain (AN12a–AN15) stays in the map's scope but **off the critical path**, deferred past 23 Nov.
  Why: the operator chose not to spend the window on it; V14 and V16 do not depend on the derivative's
  score fidelity (V16 is not anonymised, map decision 3).
- W05 no longer has to fit AN15 into the V14 → V16 calendar; it is now blocked only by W03.
