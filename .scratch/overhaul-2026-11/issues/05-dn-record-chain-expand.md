# 05 — DN record chain (expand): one way to load a record against its predecessors

Status: needs-triage
Type: task
Blocked by: 04
Source: `discovery/architecture-review-harness-2026-11-03.html`, candidate D. Not grilled; written on
operator request 2026-11-03, with recommendations taken as decisions.
Findings: F6 deepening · DN record chain (Stage A/B evidence trail)

> `needs-triage` until the Step 3 scope cut admits it; then `ready-for-agent`.
> Candidate D is split expand → contract because it exceeds one session (admission rule 3).
> This ticket adds the module and moves the **two weakest links** onto it; 06 moves the rest and deletes the copies.

## What to build

The DN pre-evaluation records form a chain:

    evidence preflight → blind report → blind baseline → integrity audit → ESR comparison (+ revisions) → operator review / comparison diff

Each record names its predecessors by hash. Today every record module re-implements loading:
record-type check, advisory/blocking check, and whether to re-hash its predecessors. They differ in
strictness:

- the operator review re-hashes everything the comparison names;
- the comparison diff only compares fields between the two comparisons, and never re-reads either
  one's predecessors from disk;
- loading an ESR comparison checks its shape only.

After this ticket there is one record-chain module. A record kind declares its record type, its
predecessor references and its own error class, once. Loading a record of that kind checks its type
and flags and re-hashes every predecessor it names. A predecessor whose bytes moved is refused, naming
the record, the predecessor, and both hashes. The ESR comparison and the comparison diff load through it.

## Decisions (operator accepted recommendations, 2026-11-03)

- **The chain is shared; the readers are not.** This reopens `record_binding.py`'s documented decision
  only for the chain. Each record keeps its own vocabulary, field readers and error class. The error
  class is declared once on the kind, not threaded through every call site, which answers the
  objection recorded in `record_binding.py`'s docstring.
- **The interface is two operations:**
  - load a record of a kind, verified against its predecessors on disk;
  - write a record of a kind to the next numbered path, atomically, returning its path and file hash.
  Hashing and short forms come from ticket 04's module.
- **The behaviour change is the point.** The comparison diff now refuses a pair if either comparison's
  baseline report, ESR record, dispositions or revisions artifact has moved on disk. Loading an ESR
  comparison now re-hashes the baseline report and ESR record it names. Before, both passed silently.
- **Predecessor references are read from the fields records already carry** (`report_sha256`,
  `esr_record` / `sha256`, `dispositions_sha256`, `comparison_sha256`, …). No record format changes, and
  records written before this ticket load if their predecessors are unchanged.
- **Path resolution follows today's rules.** A predecessor recorded as an absolute path from another
  run resolves the way each module resolves it now (for example, the revisions artifact beside its
  comparison). Path rules are not unified in this ticket.

## Acceptance criteria

Failing tests first:

- [ ] Comparison diff over two comparisons whose shared baseline report was edited after they were written: refused, naming the baseline report and both hashes.
- [ ] Comparison diff where one member's revisions artifact was edited: refused in the same way.
- [ ] Loading an ESR comparison whose ESR record was edited: refused, naming it.
- [ ] Loading a record whose `record_type` or advisory/blocking flags are wrong: refused with the record kind's own error class.

Then:

- [ ] An untouched fixture chain (preflight → report → baseline → audit → comparison → review → diff) loads end to end.
- [ ] Records written before this ticket load when their predecessors are unchanged.
- [ ] The ESR comparison and comparison diff no longer carry their own type/flag/re-hash code for the links moved here.
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md`.
- [ ] **PE-09 acceptance lane green** (admission rule 5).
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/05-dn-record-chain-expand.md   Base commit: <sha at start>
Read first: CLAUDE.md §16–17, CONTEXT-MAP.md (+ harness/CONTEXT.md), docs/agents/*.md,
            plans/overhaul/BASELINE.md, harness/record_binding.py docstring, issue 04 (landed)
Seam: a new record-chain module — two operations (load verified, write numbered); record kinds declared once
Do not touch: record formats on disk, per-record field readers and vocabularies, blind-baseline freeze
      conditions, the PE-09 runbook, §17 call graph, Tier 1–3 docs
Tests first: the four failing tests above (tdd)
Size: ~250–350 changed non-test lines
```
