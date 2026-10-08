# PE-08 review and PE-09 handoff tickets

Date: 2026-10-07  
Repository: `JozsefKiss90/proposal_orchestrator`  
Branch: `msca-dn-pre-eval`  
Suggested repository location: `plans/msca_dn_pe08_review_tickets.md`

## Reconciliation (2026-10-08)

The checkboxes below were reconciled against the implementation on 2026-10-08, after the
operator approved the PE-08 decision package
(`docs/tier4_orchestration_state/msca_dn/reviews/operator_approval_2026-10-08.md`). A box is
checked where a committed artifact or test evidences the criterion: R01 at `5159e5a`, R02 at
`0943b1d`, R03 at `1eddc81`, R04 at `76a794e`, R05 at `047f64d`, R06 by
`plans/msca_dn_pe09_runbook.md`. A note beside a box says what the approval changed about it.
Two things stay open by the approval's own terms and are not boxes here: active-register
adoption of the R04 drafts (D13) and every original-dependent question in the approval
record's deferred table. PE-09 remains unexecuted in this repository.

## Starting state

PE-08 was implemented at `67a3174`. The operator reports that line-ending protection is complete at `5b57f09`, with verification recorded at `015d9c0`: a fresh checkout passes all eight binding checks and reproduces the comparison. Treat that work as completed; verify the current checkout before continuing.

The remaining work is to preserve operator declarations, review semantic interpretations, prepare fidelity declarations, produce reviewed successor artifacts, and prepare private-network validation.

These are follow-up ticket IDs, not replacements for the specification's PE-01–PE-09 numbering. This document proposes implementation work; it does not confer authority on draft judgments.

## Shared inputs

- Specification: `plans/msca_dn_pre_evaluation_spec.md`.
- Implementation guidance: `harness/HARNESS.md` and applicable repository instructions.
- Authoring tools: `tools/author_msca_dn_workspace.py`, `tools/import_external_proposal.py`.
- Comparison implementation: `harness/esr_comparison.py` and `harness/commands/blind_assessment.py`.
- Integrity audit: `harness/integrity_audit.py`.
- Baseline: `docs/tier4_orchestration_state/msca_dn/baselines/resolved_fixes_2026-10-06/`.
- Candidate node: `MSCA-DN-2025_sanitised_part_b@b51a103520b58ded`.
- Candidate hash prefix: `sha256:242f1afb02c8`.
- Graph root: `workspaces/msca_dn`.
- Original dispositions: `docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1.json`.
- ESR record: `docs/tier4_orchestration_state/msca_dn/esr/msca-dn-2025-esr.json`.
- Original outputs: `docs/tier4_orchestration_state/msca_dn/comparisons/comparison_f60ae6e0a2a1_0001.json` and `revisions_f60ae6e0a2a1_0001.json`.
- Registers: `docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register.json` and `fidelity_register_resolved_fixes.json`.
- Revised import manifest: `workspaces/msca_dn/docs/tier4_orchestration_state/dev_graph/imports/MSCA-DN-2025_sanitised_part_b.resolved_fixes.json`.

Resolve materialised candidate, audit and historical-copy paths from current records; do not guess paths or reconstruct identifiers from hash prefixes.

## Execution order

| Ticket | Work | Depends on | Completion type |
|---|---|---|---|
| R01 | Preserve fidelity declarations during regeneration | Completed line-ending fix | Code and tests |
| R02 | Produce the 29-observation review table | Current PE-08 artifacts | Review artifact |
| R03 | Adjudicate possible semantic false positives | R02 | Evidence review; code only if justified |
| R04 | Prepare fidelity declarations and record operator decisions | R01, R02, R03 | Draft now; human verification where required |
| R05 | Generate successor dispositions and comparison artifacts | R03, R04 | Draft or reviewed outputs, explicitly labelled |
| R06 | Prepare PE-09 private-network runbook | R05 | Runbook; execution remains private |

R01 and R02 can be worked on independently. Continue all preparation supported by available evidence before requesting the operator's decisions.

## Shared constraints

- Preserve existing PDFs, document records, page sources, ESR record, frozen baseline, dispositions and generated reports as historical evidence.
- Do not modify proposal text, dates, partner assignments or scientific commitments in these tickets.
- Do not run a new assessor during R01–R06 or tune the framework toward 85.80.
- Separate reference resolution, semantic interpretation and operator confirmation.
- Use the repository's existing status vocabulary. Agent-authored drafts must not impersonate operator approval.
- Retain existing line-ending protections. Do not perform blanket renormalisation or silently replace recorded hashes.
- New artifacts must identify their inputs, review state, uncertainties and relationship to earlier versions.
- Inspect current command help and tests before documenting commands. Do not invent flags.

## R01 — Preserve fidelity declarations during regeneration

**Priority:** First implementation task.  
**Problem:** The workspace authoring tool generates an empty declared half, and the importer uses that output to rewrite both registers. Operator declarations would be lost.

### Implementation

1. Trace both generation paths, including normal writes, `--check`, missing-file rebuilds and historical/revised register selection.
2. Define one explicit ownership boundary: the tools own measured/derived fields; operator-authored declarations are retained without reinterpretation.
3. Choose a deterministic persistence mechanism compatible with repository rules. Either preserve and validate declarations from the existing register, or use a durable declaration input that supports reconstruction. Document the choice and its missing-input behaviour.
4. Keep declarations revision-specific. Never copy the current revision's declarations into the historical revision implicitly.
5. Fail clearly on malformed declaration data. Do not silently replace invalid data with an empty list. An existing empty declared half remains valid pending review.
6. Make `--check` read-only and ensure it detects stale derived fields while accepting retained declarations.
7. Preserve the current empty-register output bytes when no declaration is supplied, unless a separately documented format change is necessary.
8. Document how an operator adds declarations and how subsequent regeneration preserves them.

### Acceptance criteria

- [x] Both tools retain valid operator declarations across repeated regeneration.
- [x] Historical and revised declarations remain distinct.
- [x] Regeneration is deterministic, and `--check` succeeds immediately afterward.
- [x] Malformed declaration input fails without overwriting the register.
- [x] Changes to PDF-derived facts are still detected and regenerated.
- [x] Rebuild behaviour is documented honestly: if declarations require a durable input, it is included in the documented inputs.
- [x] Existing baseline bindings and historical artifact bytes remain intact.

### Verification

Add focused tests covering populated declarations, differing declarations in both revisions, malformed inputs, repeated generation, read-only checks and the chosen missing-file reconstruction behaviour. Run the importer/workspace suites and relevant binding checks. Use temporary fixtures rather than populating production registers with test declarations.

### Deliverables

Focused tool changes, tests, usage documentation and a decision record explaining declaration ownership and reconstruction.

## R02 — Produce a complete operator-review table

**Priority:** High.  
**Problem:** PE-08 resolves references, but its dispositions and proposed revisions were drafted by Claude and require semantic review.

### Implementation

1. Generate a readable Markdown review artifact from the committed ESR record, dispositions, comparison, candidate, registers and cited audits.
2. Cover each of the 29 observations exactly once. Preserve ESR wording and cluster severity; do not invent severity per split observation.
3. Include these fields per observation:
   - ID, criterion, aspect, strength/shortcoming kind and severity cluster.
   - Verbatim ESR text.
   - Existing disposition and its status.
   - Exact blind and audit findings, with lane and reference identifiers.
   - Candidate quotes and relevant register entries.
   - Whether the reference resolves and whether it supports the same proposition.
   - Uncertainty, recommended disposition, proposed revision and required operator decision.
4. Highlight the six alleged misses and eight contested strengths. Distinguish an absent detail from an inadequately explained detail.
5. Show separate counts for strengths, shortcomings, full detections, partial detections, misses and unassessable observations. Attribute detection to the blind lane and/or audit lane explicitly.
6. Include an input inventory and review status. Label agent-authored recommendations as provisional.

### Acceptance criteria

- [x] The observation ID set matches the ESR record, with no duplicates or omissions.
- [x] Every quoted reference resolves against its named artifact.
- [x] Reference validity and semantic agreement are separate fields.
- [x] Counts distinguish strengths from shortcomings; “15 detected” is not presented as 15 criticisms detected.
- [x] Every disputed row has a concrete review question.
- [x] No existing comparison artifact or ESR record is overwritten.

### Verification

Check ID coverage, counts and references using existing resolvers where practical. No new test suite is required for a standalone Markdown report; if a reusable generator is added, test coverage and reference failures meaningfully.

### Deliverables

A new Tier 4 Markdown review report and a concise list of operator decisions needed.

## R03 — Review semantic false positives and ESR matching

**Priority:** High.  
**Problem:** A deterministic comparison can be syntactically correct while comparing different relationships or interpreting an intentional schedule as a contradiction.

### Implementation

1. Examine `ESR-Q-03`, including M7.3 at M48 and WP7 at M1–M36. Establish what the candidate actually says about project duration, WP duration and follow-up commitments. If context is insufficient, record uncertainty rather than choosing an interpretation.
2. Examine DC appointments beginning at M5 for 36 months against WP windows. Do not assume employment and WP participation must have identical durations.
3. Examine “DCs involved” versus DC project/host lines, especially training, dissemination and management WPs. Establish whether the compared sets represent the same relation.
4. Review undeclared milestone dependencies. Identify whether an explicit deliverable link is a sourced requirement, an inferred relationship or a drafting recommendation.
5. Inspect whether quoted blind findings actually match the ESR criticism. For example, a statement that no intermediate milestones are shown must be assessed against the materialised milestone table and the assessor's actual input.
6. Record each adjudication with finding ID, rule, compared relation, exact evidence, interpretation and status. Distinguish actual inconsistency, ambiguous relationship, extraction issue, sanitisation limitation and unsupported checker assumption in prose without silently changing existing report enums.
7. If a general audit defect is established, implement a narrowly scoped, instrument-neutral correction with representative positive and negative cases. Do not add WP4-, M7.3- or page-specific exceptions.
8. Generate a new audit artifact if code changes affect findings. Preserve the original audit and baseline, identify changed findings, and bind the successor audit to its actual candidate and snapshot.
9. Propagate justified disposition recommendations into the R02 review report.

### Acceptance criteria

- [x] Every disputed relationship has an explicit interpretation or unresolved status.
- [x] No timing/assignment value is changed to satisfy the checker.
- [x] An audit finding is counted as ESR detection only when the semantic match is supported. (D06 narrows ESR-Q-03 to provisional partial credit on the timing finding alone)
- [x] Any rule change applies generally and retains meaningful true-positive checks. (D11 retires the undeclared-dependency finding generally; explicit references are still checked)
- [x] Old audit findings remain available; changed outputs are written as successors. (`integrity_242f1afb02c8_0001`, `_0002` and `_0003` all on disk)
- [x] Claims requiring the original are identified for private-network review, without importing it here.

### Verification

For code changes, test legitimate post-WP follow-up or employment relationships alongside genuine conflicts, and run the integrity-audit suite. Compare old/new findings by kind, subject and explanation; justify differences instead of pinning disputed totals as correctness.

### Deliverables

A semantic adjudication record, updated review recommendations, and optional focused audit correction with successor audit and tests.

## R04 — Prepare revision-specific fidelity declarations

**Priority:** High.  
**Problem:** The declared halves are empty, so sufficient preservation is assumed on every alleged miss.

### Implementation

1. After R01, prepare a declaration draft for each revision using the existing register format. Cover each subsection in that revision's derived inventory exactly once.
2. For each subsection, provide independent `presence` and `transformation` fields, evidence/basis, author/reviewer information and status as supported by the existing format.
3. Separate three claims: extraction fidelity against the sanitised PDF; differences between sanitised revisions; fidelity against the submitted original.
4. Populate only supported facts. A present passage or zero extraction loss does not prove complete preservation from the original.
5. Use existing permitted values; if the format cannot represent a necessary uncertainty, document and implement the smallest justified format change rather than inventing undeclared enums.
6. Leave original-dependent judgments pending approved private-network verification. Preserve the operator's prior declarations without upgrading their status silently.
7. Review known declarations that measurements contradict, such as uniform 12-point body text. Prepare a proposed correction with evidence and reviewer status.
8. Identify which ESR dispositions depend on each declaration and what confirmation would change their interpretation.
9. Store drafts separately from active registers until review is recorded. Apply only operator-confirmed judgments as operator declarations.

### Acceptance criteria

- [x] Both revision drafts cover their actual subsection inventories.
- [x] Presence and transformation are independent.
- [x] Measured extraction facts do not masquerade as fidelity to the original. (V01 now enforces it: a presence declaration unlocks no Confirmed preservation)
- [x] Unverified original-dependent claims remain explicitly uncertain.
- [ ] Draft declarations survive the supported generation workflow after adoption. (open: the R01 retention tests and the R04 temporary-checkout exercise show the workflow survives a drafted declaration, but adoption into an active register is deferred by D13, so the criterion's own precondition is unmet and the box stays unchecked)
- [x] Dependencies on register/manifest hashes are enumerated before adopting changes.

### Verification

Validate the draft format and identifiers. Exercise regeneration in a temporary checkout after applying representative declarations. If adoption changes a register, record the new hash and affected bindings; preserve historical copies so the original comparison remains replayable. Reuse the frozen baseline rather than altering its evidence or pins.

### Deliverables

Two revision-specific declaration drafts, a review checklist and an adoption/provenance record when operator review occurs.

## R05 — Generate successor dispositions, comparison and revision plan

**Priority:** After evidence review.  
**Problem:** The original PE-08 outputs are a provisional interpretation and must remain available while reviewed conclusions are recorded.

### Implementation

1. Create an identifiable successor dispositions file bound to the unchanged baseline and ESR record. Cite the R02/R03 adjudications and the applicable register version.
2. Distinguish agent recommendations from operator-reviewed decisions. If decisions are still pending, produce a clearly labelled draft rather than claiming review completion.
3. Verify whether current code truly checks evidence preservation or merely validates a declared status. Do not describe it as stronger than its implementation; address any justified gap with focused validation and tests.
4. Run the supported `compare` command over the successor inputs. Write new comparison and revision artifacts without overwriting the originals.
5. Recompute counts from the successor rows. Keep strengths, shortcomings, lane attribution and partial detections separate. Preserve the score-comparison block without assigning point deductions to criticisms.
6. For each proposed revision, identify the evidence, responsible human role, required scientific/partner confirmation and intended proposal location. Treat numerical targets, study designs, data access and partner commitments as proposals until confirmed.
7. Retain all ESR shortcomings in the revision review even when the harness missed them. Explain any excluded or closed item with evidence.
8. Record a clear diff of dispositions, evidence, findings and priorities against the original comparison.
9. Where register updates affect the current import manifest or preflight, document those effects. The old preflight remains historical evidence; a future assessment requires fresh bindings to changed active inputs. Always use the explicit revised import manifest for that future run.

### Acceptance criteria

- [x] Old artifacts remain byte-unchanged and replayable from documented historical inputs. (the legacy pointer rule is kept, version-gated, for that replay)
- [x] Every successor observation has a traceable disposition and review status.
- [x] References resolve; unavailable confirmation is not presented as certainty.
- [x] Summary counts match the successor rows.
- [x] Revisions distinguish confirmed actions from proposals requiring human commitment.
- [x] The original baseline and criterion scores are preserved; no new assessor call occurs.
- [x] Pending review prevents a claim of final operator acceptance, but does not prevent preparation of a labelled draft. (the operator's review is now recorded; see the reconciliation note)

### Verification

Run ESR-comparison tests and resolve successor references end to end. Check fail-closed behaviour for invalid references and stale bindings. Compare regenerated substantive output with the recorded successor, allowing only documented run metadata differences.

### Deliverables

Successor dispositions, comparison and revision plan; original-to-successor review diff; exact replay command and input inventory.

## R06 — Prepare the PE-09 private-network runbook

**Priority:** Handoff.  
**Scope:** Preparation only. PE-09 execution occurs inside the approved private environment.

### Implementation

1. Write a step-by-step runbook based on the current CLI and importer capabilities. Mark proposed tooling separately from commands verified to exist.
2. Define a controlled import process: input hash, measured page count, headings, boundaries, tables, extraction accounting, import manifest, fidelity register, document node/version and materialised candidate. Reuse deterministic tooling; identify any required configuration work before running it on the original.
3. Include an explicit selection of the correct import manifest. Do not rely on the resolver's predecessor-manifest default.
4. Establish historical-profile authority and document differences from the resubmission profile. Do not improvise absent call rules.
5. Require a fresh preflight followed by an isolated blind historical assessment and verified freeze. Exclude the ESR from assessor inputs and access, including drafting context and process capabilities.
6. Introduce the ESR only after the historical freeze. Run the integrity audit and comparison, and investigate missed findings, false positives, contested strengths and score differences.
7. Implement human-approved revisions in the authoritative proposal. Record changes and supporting sources without carrying private material into this public workspace.
8. Import the final resubmission as a distinct candidate with its own provenance, profile, preflight, assessment, audit and reports.
9. Describe grounding prerequisites: the current sanitised audit deliberately marks 45 claims unresolved. Restoring sources alone does not implement evidence-backed grounding; identify the required loader, ledger and E2/grounding integration before claiming that axis is validated.
10. State which metadata may be exported and which artifacts must remain private according to the approved environment's rules. Do not invent those rules.

### Acceptance criteria

- [x] The runbook separates historical validation from final resubmission assessment.
- [x] Every documented command uses supported flags or is labelled as future implementation.
- [x] Original import has measurable fidelity checks and an explicit manifest binding. (as prerequisites: the importer's checks exist, the original's revision entry does not)
- [x] Historical blind assessment is frozen before ESR comparison.
- [x] Assessor isolation includes tool/MCP restrictions and an external working directory.
- [x] Missing profile authority, grounding integration or operator decisions are named prerequisites.
- [x] The handoff states that PE-09 remains unexecuted here.

### Verification

Check CLI syntax locally without assessor calls. Link commands to current help/documentation and list exact required private inputs. No private proposal or source upload is part of this ticket.

### Deliverables

PE-09 runbook, private-environment prerequisites, supported command templates and a list of any implementation gaps that need separate tickets.

## Completion report for each ticket

Record changed files, actual checks and results, preserved artifact bindings, remaining uncertainties and successor artifact paths. If broader failures are called pre-existing, provide a baseline comparison supporting that statement. Do not call a ticket fully accepted while its required operator judgment is still pending.
