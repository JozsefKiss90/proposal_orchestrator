# 06 — DN record chain (contract): every link loads through the chain module

Status: needs-triage
Type: task
Blocked by: 05
Source: `discovery/architecture-review-harness-2026-11-03.html`, candidate D (contract half). Not
grilled; written on operator request 2026-11-03.
Findings: F6 deepening

> `needs-triage` until the Step 3 scope cut admits it; then `ready-for-agent`.

## What to build

The remaining DN records move onto the record-chain module from 05: evidence preflight, blind report,
blind baseline freeze, integrity audit and operator review (Markdown pair included). Each module's own
type/flag/predecessor-re-hash code and numbered-path writing is deleted. After this ticket, there is one
place that decides whether any DN record still describes the evidence it names, and every link is
equally strict.

## Decisions (operator accepted recommendations, 2026-11-03)

- **Same rules as 05:** kinds declared once with their own error class; no record format changes;
  existing path-resolution rules kept.
- **Records with their own checks keep them.** The blind report's candidate-hash recomputation from
  the candidate directory, and the baseline's freeze conditions (`BASELINE_CHECKS`), stay in their own
  modules. Only the generic chain checks move. The freeze schema version does not change, and the
  PE-09 runbook test stays green unedited.
- **Contract, then confirm.** When no module keeps its own copy of the chain checks, a boundary test
  asserts that DN record modules load predecessors only through the chain module.

## Acceptance criteria

Failing tests first:

- [ ] An integrity audit over a blind baseline whose frozen report bytes were edited: refused by the chain, naming the report and both hashes. (Characterise today's behaviour first; if it already refuses, this becomes a characterisation test.)
- [ ] An operator review over a comparison whose candidate artifacts moved: refused with the operator-review error class (characterisation of today's `_expect_sha` behaviour).

Then:

- [ ] Preflight, blind report, baseline, audit and operator review load and write through the chain module; their private copies are deleted.
- [ ] The boundary test above is in place.
- [ ] The full fixture chain loads end to end, and records written before 05 still load when unchanged.
- [ ] Blind-baseline freeze conditions, freeze schema version and the PE-09 runbook test are unchanged and green.
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md`.
- [ ] **PE-09 acceptance lane green** (admission rule 5).
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/06-dn-record-chain-contract.md   Base commit: <sha at start>
Read first: CLAUDE.md §16–17, CONTEXT-MAP.md (+ harness/CONTEXT.md), docs/agents/*.md,
            plans/overhaul/BASELINE.md, issues 04 and 05 (landed)
Seam: the record-chain module from 05 — call sites migrate; no interface change to the module
Do not touch: freeze conditions / BASELINE_CHECKS, record formats, per-record readers, the PE-09 runbook,
      §17 call graph, Tier 1–3 docs
Tests first: characterise each link's current refusal behaviour before migrating it
Size: ~250–350 changed non-test lines, net negative
```
