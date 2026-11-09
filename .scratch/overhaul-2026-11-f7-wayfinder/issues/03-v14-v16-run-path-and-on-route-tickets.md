# 03 — Which code does a V14/V16 private-host run execute, and which tickets and defects sit on it?

Type: research
Status: resolved
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

## Answer (2026-11-06)

Full findings: [../W03-findings.md](../W03-findings.md).

- **Transport is not settled by the code.** Both routes are built and freezable. The runbook says `claude-cli`
  (V12 predates the Converse assessor); the map says Converse on the private host, which does not exist yet
  (R11 held until ~10 Nov; AN12 host criteria open). This becomes W05's first question.
- **Ticket 03's misroute does not reach the blind assessment**, on either transport: an omitted `--transport`
  ends in a `ValueError` before any call. 03 is off route; recommend deferring it.
- **On path:** 01 (the only keep that changes assessment output), UR-A, UR-B, UR-C, UR-E, slice-2 findings 1–2;
  04–06 touch the record chain without changing output. **Off path:** 02, 07a, 07b, 08, 09.
- **The PE-09 acceptance lane is RED at HEAD** because the declaration drafts are stale (one lane test fails
  on Windows). Re-render them before any rule-5 ticket.
- **V02c is done** (`7195681f`); any open checkbox is ledger drift.
