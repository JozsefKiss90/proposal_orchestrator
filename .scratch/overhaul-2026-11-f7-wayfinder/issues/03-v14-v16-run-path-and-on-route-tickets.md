# 03 — Which code does a V14/V16 private-host run execute, and which tickets and defects sit on it?

Type: research
Status: open
Blocked by: None
Map: ../map.md

## Question

Trace the private-host run path the PE-09 runbook prescribes (import → preflight → blind assessment over
the Converse backend with response checkpointing and `--resume` → freeze (V04) → integrity audit →
execution receipt), module by module. For each overhaul ticket, say whether it changes code on that path
and what it would buy V16:

- harness 01–06 (judge call, rubric resume, judge factory, content hash, record chain ×2);
- runtime 07a/07b/08/09.

Note: ticket 03 reports a live defect where a paced builder ignores a Converse environment. Is the blind
assessment's Converse route affected? Also record:

- any defect on the path that no ticket covers;
- whether V02c (stale synthetic test contracts) is really still open, and whether the PE-09 acceptance
  lane is green at HEAD.

Answer with: the path as a module list, plus a table of ticket → on/off path → V16 value → risk if it
lands after V14.
