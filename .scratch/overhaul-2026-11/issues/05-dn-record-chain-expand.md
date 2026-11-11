# 05 — DN record chain (expand): one way to load a record against its predecessors

Status: done
Type: task
Blocked by: 04
Source: `discovery/architecture-review-harness-2026-11-03.html`, candidate D. Not grilled; written on
operator request 2026-11-03, with recommendations taken as decisions.
Findings: F6 deepening · DN record chain (Stage A/B evidence trail)

> Admitted by operator decision D2 (`docs/tier4_orchestration_state/decision_log/plan-order-reliability_2026-11-11.json`).
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

- [x] Comparison diff over two comparisons whose shared baseline report was edited after they were written: refused, naming the baseline report and both hashes.
- [x] Comparison diff where one member's revisions artifact was edited: refused in the same way.
- [x] Loading an ESR comparison whose ESR record was edited: refused, naming it.
- [x] Loading a record whose `record_type` or advisory/blocking flags are wrong: refused with the record kind's own error class.

Then:

- [x] An untouched fixture chain (preflight → report → baseline → audit → comparison → review → diff) loads end to end.
- [x] Records written before this ticket load when their predecessors are unchanged.
- [x] The ESR comparison and comparison diff no longer carry their own type/flag/re-hash code for the links moved here.
- [x] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md`.
- [x] **PE-09 acceptance lane green** (admission rule 5).
- [x] `code-review` run since the base commit, with no gaps on the spec axis. Operator exception: the revisions-hash gap is accepted (decision `overhaul-05-revisions-hash-gap_2026-11-11`).

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

## Comments

- Deferred at Step 3 (2026-11-06): record-chain refactor, refusals only, no value for V14/V16 before the deadline. Blocked by 04.
- Wave 2b (2026-11-06): order in `discovery/scope-cut-2026-11-06.md`; brief reads "at or above BASELINE.md §5" once wave 1 has merged.
- 2026-11-11, base 6820395e: targeted 24 modules, 1 failed (on the BASELINE §5 red line: `test_demo_candidate_blind_baseline.py::...::test_the_leakage_scan_file_count_is_re_derivable`) / 1,272 passed. Code-review ran (spec + standards); fixed: comparison now also re-hashes the fidelity register and each audit, the diff command passes --repo-root through, unused `beside` rule removed, record_binding docstring notes the chain. Spec gap left open: a comparison records no hash of its revisions artifact, so a content edit to it is refused when a written diff is loaded (the diff holds its hash) but not when a new diff is run (only its bound hashes are checked); closing it needs a record-format change, which this ticket forbids. Code-review box open for the operator. Full suite and lane not run.
- 2026-11-11, operator decision: option 1. The revisions-hash gap is accepted for the O5 bundle; a revisions hash in the comparison record is a later format ticket after V16. The four behaviour changes (path lookup without a repo root, re-hashing dispositions/fidelity register/audits, required advisory/blocking flags on revisions, temp-file prefix `comparison_`) are accepted. Record: `overhaul-05-revisions-hash-gap_2026-11-11`. Suite and lane boxes wait for the operator's O2 run.
- 2026-11-11, closed: merged by the operator as `70fcb6b5` (with `8579d877`). Suite at `70fcb6b5`: 42 failed, 9,606 passed, 87 skipped; the 42 failed node ids equal BASELINE §5 exactly (none new, none gone; `suite-o2.txt`). Lane GREEN: 3,662 tests, 3,645 passed, 0 failed, 0 errors, 17 declared exclusions (`lane-o2.xml`). The revisions-hash gap stays open under `overhaul-05-revisions-hash-gap_2026-11-11` G1 until its format ticket lands after V16.
