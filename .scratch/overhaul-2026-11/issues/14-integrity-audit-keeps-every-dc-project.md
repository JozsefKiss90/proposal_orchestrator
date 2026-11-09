# 14 — The integrity audit never loses or overwrites a DC project (UR-E)

Status: ready-for-agent
Type: task
Blocked by: 10
Source: `discovery/ultrareview-records-2026-11-06.md` findings 5, 6
Admitted: Step 3 scope cut, 2026-11-06 (`discovery/scope-cut-2026-11-06.md`) · lands before the 10 Nov freeze
Findings: F7 · DN run path (audit step of V14 and V16)

## What to build

The integrity audit of an imported DN candidate accounts for every doctoral-candidate (DC) project the
Part B states, or reports why it cannot. Today two parsing defects lose one silently:

- DC projects are keyed by number, so when two prose blocks carry the same DC number the later one
  replaces the earlier with no finding; the parser also scans every section, not just §1.1, so a later
  paragraph can replace the real §1.1 project (finding 5);
- two parse loops consume the paragraph after a match ("Contribution to the Network" and one more site)
  without their own stop checks, so when that heading is not followed by exactly one same-sub-section
  paragraph, the next `DC<n> – title` heading is skipped and that project disappears (finding 6).

## Decisions (scope cut, 2026-11-06)

- **A duplicate DC number is a finding**, naming both locations; neither block silently wins.
- **The consumed paragraph must belong to the block:** same sub-section, not a DC heading, WP opener or
  table caption. Otherwise the loop advances by one and its own stop conditions end the block (both sites).
- Whether DC parsing should be limited to §1.1 is decided in the session: characterise first, and
  restrict only if a test shows a non-§1.1 block being taken as a project.
- The audit report format is unchanged apart from the new finding.

## Acceptance criteria

Failing tests first (synthetic Part B prose, no private content):

- [ ] Two blocks with the same DC number: a duplicate finding naming both; no silent replacement.
- [ ] A "Contribution to the Network" heading followed by zero or two paragraphs: the next DC project is still parsed.
- [ ] The same for the second consume-next site.
- [ ] A well-formed Part B audits exactly as today (existing integrity-audit tests unchanged).

Then:
- [ ] **PE-09 acceptance lane green**, run with ticket 10's lane (admission rule 5).
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md` (no new failure by node id against §4's 43).
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/14-integrity-audit-keeps-every-dc-project.md   Base commit: <sha after 10 merged>
Read first: CLAUDE.md §16–17, CONTEXT-MAP.md (+ harness/CONTEXT.md), docs/agents/*.md,
            plans/overhaul/BASELINE.md, .scratch/overhaul-2026-11/discovery/scope-cut-2026-11-06.md,
            .scratch/overhaul-2026-11/discovery/ultrareview-records-2026-11-06.md
Seam: the audit's Part B parser — no interface change
Do not touch: candidate provenance (ticket 16), audit report schema beyond the new finding, freeze, Tier 1–3 docs
Skills: diagnosing-bugs, then tdd
Size: ~60–120 changed non-test lines
Record: none
```
