# Tickets: Dev Graph milestone 1

Builds the operational graph index, bounded evidence packages, shadow impact planner and blind pre-evaluation lane described in `.scratch/dev-graph-milestone-1/PRD.md`, closing on the synthetic scenario "responsibility for Task T03 moves from Participant B to Participant C" on an unsubmitted candidate without an ESR. Handoff stages 1 to 6 only.

Work the **frontier**: any ticket whose blockers are all done. Tickets 1, 2 and 8 can start immediately. Clear context between tickets.

Constraints that apply to every ticket: the DAG scheduler, gate evaluator, gate library, budget-before-Phase-8 block and whole-Tier-3 reuse fingerprint are not modified. Tests run with `py -3.10` and build their own synthetic world under a temporary directory. Never dispatch runner phases. The internal-docs style profile governs prose in decision log entries.

## Fix the harness import boundary

**What to build:** The existing harness boundary test goes green. Three scripts currently import the harness package at runtime and violate the one-way harness-to-runner rule. Move the harness-dependent behaviour of each script behind a harness module command, or drop the import, so runtime tools and scripts no longer depend on the harness. This is a prefactor: the new pre-evaluation lane must not inherit the violation.

**Blocked by:** None — can start immediately.

- [x] The boundary test that checks tools and scripts do not import the harness passes.
- [x] Each of the three scripts still performs its documented job, verified by its existing tests or a new one.
- [x] No new script or tool imports the harness.

## Dev-graph schema and snapshot builder on a synthetic fixture

**What to build:** A new runner package with one public entry point that builds an immutable graph snapshot from a repository root. An engineer points it at a call-neutral synthetic fixture repository and gets back a snapshot with a content-derived ID, or a fail-closed error naming the first invalid node or edge. The fixture holds a minimal synthetic instrument registry entry, three participants, two objectives, one work package, tasks T01 to T03, one deliverable and one milestone. No real proposal text, no instance-one nouns.

The snapshot uses the closed node type set (participant, objective, work package, task, deliverable, milestone, claim, commitment, passage, source, source span, artifact version, execution, assessment, finding, change request, revision contract) and the closed relationship set (`assigned_to`, `contributes_to`, `produces`, `supported_by`, `expressed_in`, `consumes`, `addresses`, `supersedes`, `constrained_by`, `validated_by`). Each relationship declares endpoint types, direction, cardinality and whether it is a domain link or an execution dependency. Node identity is separate from path and title. A node reference is always an ID plus a content-hash version. The snapshot ID hashes canonical JSON of nodes and edges recursively and excludes any wall-clock field. Do not reuse the existing directory fingerprint helper, which hashes direct child names only.

The snapshot writer is registered as a deterministic component in the existing registry and is Claude-free. The existing compiler, projector, vault reader and promote tool stay unchanged.

**Blocked by:** None — can start immediately.

- [x] Two builds of the fixture with maximally different wall-clock stamps produce byte-identical snapshots and the same snapshot ID.
- [x] A dangling edge, a wrong endpoint type, an unknown predicate (including `related_to`) and a duplicate ID each fail closed with an error naming the offending node or edge.
- [x] An empty Tier 3 returns an explicit empty snapshot, not an error and not fabricated nodes.
- [x] Byte-equal replay test for the snapshot writer passes through the component registry.
- [x] The agnosticism lint covers the new package and passes.
- [x] The existing graph compiler, projector, vault reader and determinism check tests still pass.
- [x] Decision log entries exist for field ownership (one writer per field), the retained compiler staging path versus the new index, and the type and relationship set. The first entry records the engine-base commit SHA.

## Document snapshots and separated claim evidence fields

**What to build:** An operator imports a candidate proposal document and the builder stores it as an immutable document snapshot node with a lifecycle state from the closed set imported, draft, submitted, superseded. Passages link to the document snapshot by span. Claim nodes carry three separate fields: declared status (Confirmed, Inferred, Assumed, Unresolved), verified source span (ID, version, offsets, or absent) and current approval (approved, pending, not applicable). The existing evidence-strength to status lookup feeds only the declared status field. The synthetic fixture gains a three-section candidate.

**Blocked by:** Dev-graph schema and snapshot builder on a synthetic fixture.

- [x] Building the fixture with the candidate yields one document snapshot node with state imported and passage nodes linked to it by span.
- [x] Importing the same candidate twice yields the same document snapshot version. A changed candidate yields a new version and the old one remains.
- [x] A claim with declared status Confirmed and no verified span is representable and the two fields are reported separately.
- [x] A submitted document snapshot is never returned as a current commitment.
- [x] Snapshot ID stability and rejection tests from the previous ticket still pass with the extended fixture.

## Bounded evidence package builder with view policies

**What to build:** An operator or agent asks for an evidence package for a named task or view from a snapshot under a policy version and a budget. The builder returns an immutable package plus a manifest listing package ID, project, task, view, profile version, snapshot ID, policy version, included record versions and spans with selection reasons, mandatory dependencies, exclusions with reasons, unresolved issues, completeness status and package hash. View policies are configuration data, one per view: engineering, controlled revision, integrity audit, blind pre-evaluation, historical feedback analysis, change-impact planning. Each names permitted node types, permitted traversals, maximum depth and forbidden types. The blind pre-evaluation policy forbids assessment, finding, change request and anything tagged historical feedback. Policy is enforced before graph expansion. The manifest writer is a registered deterministic component. Import the shared claim status severity table rather than the compiler's private copy.

**Blocked by:** Document snapshots and separated claim evidence fields.

- [ ] Mandatory constraints and cross-section dependencies appear in the package regardless of ranking.
- [ ] A node of a forbidden type reachable only through graph expansion is excluded with reason policy-forbidden.
- [ ] A required item that exceeds the budget yields completeness status incomplete. Nothing required is silently dropped.
- [ ] A package requested from a snapshot whose ID does not match the current build is refused.
- [ ] Unresolved claims and contradictions in the snapshot appear in the manifest's unresolved list.
- [ ] Two builds with identical inputs produce the same package hash. Byte-equal replay passes through the registry.
- [ ] Decision log entry for the view policies exists.

## Approved change recording and the shadow impact planner

**What to build:** An operator records an approved new version of a source record while the old version is kept, then asks the planner what the change affects. The planner takes the before and after snapshots and the durable run records and returns a plan listing affected artifacts, passages and checks. Each entry carries a reason path (the edges traversed) and one action from the closed set rerun, reuse-under-policy, reconsider. Unknown dependency coverage for an artifact yields rerun. A source that is newly relevant after the change is flagged. The plan is written as a durable Tier 4 advisory artifact via a registered deterministic component. The planner never writes reuse metadata and never touches the scheduler.

**Blocked by:** Dev-graph schema and snapshot builder on a synthetic fixture.

- [ ] Recording a new version of T03 with assignment moved from B to C keeps the old version retrievable and the change set lists the changed `assigned_to` edge, including the removal.
- [ ] The plan for the T03 change lists the task description, the responsibility table passage, the affected proposal passages and the schedule and resource checks, each with a non-empty reason path.
- [ ] With one dependency edge removed from the fixture, the artifact whose coverage became unknown gets action rerun.
- [ ] A source absent from the old package but relevant to the new version is flagged.
- [ ] A malformed or missing snapshot makes the planner refuse rather than produce a narrower plan.
- [ ] The advisory artifact is written under Tier 4 and byte-equal replay passes.
- [ ] No file under the reuse metadata location and no run manifest reuse decision is touched.

## Shadow comparison and gate invariant pins

**What to build:** An operator compares the planner's advisory with the reuse decision the scheduler actually recorded and gets a diagnostic: agreed, planner narrower, planner broader. Nothing consumes the diagnostic at runtime. This ticket also adds the tests that prove the milestone does not weaken any gate.

**Blocked by:** Approved change recording and the shadow impact planner.

- [ ] Seeding a run manifest with a not-reused decision and an advisory that says nothing changed yields planner narrower, and no reuse metadata is written.
- [ ] Agreed and planner broader are each produced by their own seeded case.
- [ ] A test pins that the gate evaluator has exactly two call sites, both in the scheduler.
- [ ] A test proves the reuse decision is identical with and without a planner advisory present.
- [ ] A test proves the budget-before-Phase-8 hard block behaviour is unchanged.
- [ ] Decision log entry for the shadow-mode rule exists.

## Revision contracts, candidate versioning and assessment applicability

**What to build:** An operator proposes a change under a revision contract that names permitted change classes, protected node IDs and unresolved items. The checker is a pure function returning accepted, rejected with the protected node named, or flagged for review. After an accepted change the operator creates a new candidate version with provenance linking it to the change request and its evidence, leaving the old candidate intact. An applicability check takes an assessment node and a current candidate version and returns applicable or not applicable with the reason (candidate version changed, profile version changed, policy version changed). Assessments are never mutated. The revision record writer is a registered deterministic component.

**Blocked by:** Document snapshots and separated claim evidence fields.

- [ ] A responsibility change on T03 under a contract permitting responsibility changes is accepted.
- [ ] A change set that also alters the protected objective is rejected and the response names the objective node.
- [ ] A contract with unresolved participant capacity keeps that item flagged in the result. It never becomes approved.
- [ ] Creating a new candidate version yields a second document snapshot with a `supersedes` edge to the first and provenance to the change request. The first snapshot is unchanged.
- [ ] An assessment bound to candidate version 1 reports not applicable against version 2 with reason candidate version changed. Profile and policy version changes each produce their own reason.
- [ ] Byte-equal replay passes for the revision record writer.

## Versioned pre-evaluation profile in the harness

**What to build:** A harness user selects a pre-evaluation profile, a versioned configuration bundle holding the rubric set, the scorecard (scale, weights, thresholds), the criteria to sub-section mapping and the instrument type. The call-specific literals now in harness Python (instrument type filter, variant vocabulary, option-tag grammar, criterion to section mapping, default rubric and scorecard paths, instrument name in the assessor system prompt) become profile fields read from configuration. The profile version follows the existing rubric-set fingerprint and scorecard ID plus version bijection pattern. Existing harness tests keep passing against a profile that reproduces current defaults.

**Blocked by:** None — can start immediately.

- [ ] A profile that reproduces the current defaults leaves every existing harness test green.
- [ ] A second synthetic profile with different criteria names, a different scale and a different threshold runs the rubric grading path with no Python change and produces different verdicts on the same candidate.
- [ ] A grep of the harness package finds no instrument name literal outside the profile loader and the default profile file.
- [ ] Profile version changes when any bundled component changes.

## Candidate-bound blind assessment as a harness module command

**What to build:** An operator runs a harness module command to assess one specified candidate against a profile using an injectable assessor, without running the production pipeline. The report and every cell carry the candidate's content hash (using the harness's existing formatting-invariant artifact hash), the profile version and the assessor pin. A report loaded against a candidate whose hash differs is rejected. A candidate missing sub-sections the profile requires gets a partial-coverage list and is labelled a partial assessment. A malformed assessor response fails the assessment. Disagreement across samples resolves by the existing majority rule. The report keeps advisory true and blocking false. Historical reports are immutable.

**Blocked by:** Fix the harness import boundary; Versioned pre-evaluation profile in the harness.

- [ ] With a fake backend, a frozen clock and a temporary provenance log, the report carries candidate hash, profile version and assessor pin.
- [ ] Editing the candidate on disk and reloading the report raises a rejection naming the hash mismatch.
- [ ] A candidate with one of three required sub-sections missing yields a partial label and a coverage list naming the missing sub-section.
- [ ] A scripted malformed response fails the run and no report is written.
- [ ] A rerun over the same candidate writes a new report and leaves the earlier report byte-identical.
- [ ] The report cannot be constructed with blocking true.
- [ ] The boundary test passes with the module command in place.

## ESR intake record and leakage guard

**What to build:** At intake the operator records ESR availability as one of unknown, unavailable, not applicable, available, together with the bound submission and call identifiers and the permitted purpose. The blind assessment command builds its evidence package through the dev-graph package builder under the blind pre-evaluation view policy and, before invoking the assessor, asserts that no included item is tagged historical feedback, historical score, target score or repair plan. Violation is a hard failure. An ESR-informed review is a separately labelled task and never shares the blind label.

**Blocked by:** Bounded evidence package builder with view policies; Candidate-bound blind assessment as a harness module command.

- [ ] An intake record with a prior submission and no ESR stores availability unknown, never available.
- [ ] With a planted ESR-shaped document in the fixture, the rendered package contains no ESR token, the ESR path appears in exclusions with reason policy-forbidden, and the prompt hash inputs contain no ESR text.
- [ ] Forcing a historical-feedback item into the package makes the command fail before any assessor call.
- [ ] An ESR-informed task carries its own label and cannot be reported as blind.
- [ ] Decision log entry for the ESR intake contract exists.

## Milestone closure: the T03 scenario end to end

**What to build:** One test walks the handoff's first milestone in order on the synthetic fixture. A change request moves T03 from Participant B to Participant C. The revision contract checker accepts it. The planner reports the affected passages and checks with reason paths and writes its advisory. The shadow comparison runs against a seeded scheduler decision. A new candidate version is created with provenance. The blind assessment runs on the new candidate with ESR availability unknown and produces a candidate-bound, partial-or-complete report. The earlier assessment reports not applicable. Every acceptance item in the handoff's section 11 maps to one assertion.

**Blocked by:** Shadow comparison and gate invariant pins; Revision contracts, candidate versioning and assessment applicability; ESR intake record and leakage guard.

- [ ] The end-to-end test passes and each handoff section 11 item is referenced by an assertion comment.
- [ ] The full test suite shows no new failures against the recorded pre-existing baseline.
- [ ] The decision log holds all six entries named by the spec.
- [ ] The PRD status line is updated to reflect completion.
