# 11 — Declare the 2026 resubmission as its own document in the importer (W-1)

Status: ready-for-agent
Type: task
Blocked by: None — can start immediately
Source: `../overhaul-2026-11-f7-wayfinder/W01-findings.md` (must-land for V16); W02 confirms the Part B structure
Admitted: Step 3 scope cut, 2026-11-06 (`discovery/scope-cut-2026-11-06.md`) · lands before the 10 Nov freeze
Findings: F7 · must-land for V16

## What to build

The revised 2026 MSCA-DN Part B can be dry-imported, configured and imported on the private host as a
document of its own, with its own intake, revisions, manifest, register and declarations, exactly as the
2025 original is. Today the importer's document set is closed (`DOCUMENTS`: sanitised derivative, 2025
original, anonymised derivative) and every entry point refuses another document id, so V16 cannot import
its candidate. The 2026 candidate cannot be a revision of the 2025 original, whose identity is the 2025
submission.

After this ticket a fourth document of the existing **submitted-document** kind exists. Every value about
the PDF stays undeclared in the repository and comes from the operator's private configuration input (V17),
as for the original.

## Decisions (scope cut, 2026-11-06)

- **Same kind as the 2025 original.** Submitted document, no graph root in the repository, nothing
  inherited from any other document, refuses until the private input completes it, `declared_status`
  Assumed, same declaration fields.
- **Sections:** the three MSCA-DN Part B sections; the V5/V6 template equivalence measured in the scorecard
  confirms the 2026 Part B keeps them (W02).
- **Identity:** names are the operator's to confirm in the session's first step; proposal
  `resubmission_2026` / `msca-dn-2026-resubmission` / `MSCA-DN-2026_part_b_resubmission`, title naming the
  2026 call (HORIZON-MSCA-2026-DN-01).
- **No private content** in the repository; no change to V17/V18 code.

## Acceptance criteria

Failing tests first:

- [ ] `--document <new id>` is accepted by the importer and the dry import (today refused as unknown).
- [ ] The new document refuses an import until a configuration input completes it, naming the missing fields.
- [ ] A configuration input for the new document completes it; one naming the 2025 original does not.
- [ ] A 2026 revision cannot supersede a 2025 revision, and a revision id cannot belong to both documents.
- [ ] The existing original-route, dry-import and import tests pass parametrised over both submitted documents.

Then:

- [ ] The dry import, the V18 register renderer and the receipt validator work for the new document on synthetic config.
- [ ] Targeted tests and the full suite are at or above `plans/overhaul/BASELINE.md` (no new failure by node id against §4's 43).
- [ ] `code-review` run since the base commit, with no gaps on the spec axis.
- [ ] Acceptance lane stays green (the import tests are lane modules); rule 5 does not apply.

## Session brief

```
Ticket: .scratch/overhaul-2026-11/issues/11-declare-the-2026-resubmission.md   Base commit: <sha of the scope-cut commit>
Read first: CLAUDE.md §16–17, CONTEXT-MAP.md (+ harness/CONTEXT.md), docs/agents/*.md,
            plans/overhaul/BASELINE.md, .scratch/overhaul-2026-11/discovery/scope-cut-2026-11-06.md,
            .scratch/overhaul-2026-11-f7-wayfinder/W01-findings.md
Seam: the importer's document registry — no interface change; one new declared document
First step: confirm the four identity names with the operator
Do not touch: V17/V18 code paths, the three existing documents' values, harness/, Tier 1–3 docs
Skills: tdd
Size: ~60–80 changed non-test lines
Record: decision-log entry for the new document's identity (§9.4), as AN10 did for the derivative
```

## Out of scope

- The runbook's stage-B section (written with the Converse delta on Mon 9).
- The Stage B profile-applicability record (W02; operator authoring).
