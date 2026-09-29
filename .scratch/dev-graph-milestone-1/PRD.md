# Dev Graph milestone 1 — operational graph index, bounded evidence packages, shadow impact planner, blind pre-evaluation

Status: complete (2026-09-29, branch `dev_graph`; closure test `tests/harness/test_dev_graph_t03_end_to_end.py`; one follow-up ticket open, blind view and superseded versions)
Source: `plans/Dev_Graph_Orchestrator_Implementation_Handoff.md` (23 September 2026), sections 11 and 12, stages 1 to 6
Branch: `engine-base` at `69b62d9`
Written: 2026-09-23

## Problem Statement

The operator prepares Horizon Europe proposals with a gated eight-phase pipeline. When one project fact changes, the operator cannot answer five questions without reading the whole repository by hand:

1. What supports this claim?
2. What depends on this change?
3. What work must be reconsidered?
4. What evidence may this agent see?
5. Which results no longer apply, and why?

Today the Phase 8 reuse check fingerprints the whole Tier 3 directory. Any byte change anywhere invalidates every drafted section. That is safe but blind. It cannot say which sub-sections a change actually touches, so the operator either redrafts everything or trusts memory.

The drafter does not record what it consumed. The graph substrate records nodes but no typed relationships, no record versions and no snapshot identity. The harness can judge a section with a fake assessor, but a verdict is not bound to a content hash of what it judged, and nothing stops historical feedback from leaking into a blind assessment.

The operator also wants to pre-evaluate a draft on its own. Today that requires a full production run. An imported draft, a partial draft, or a draft with no submission history has no assessment path.

## Solution

Add a small, rebuildable operational graph over existing authoritative records. It indexes stable identities, record versions and typed relationships for project facts, proposal passages and execution records. It never owns content and never touches a gate.

Three consumers sit on the graph:

- **Bounded evidence packages.** A task-specific, immutable package built from a validated snapshot under an explicit evidence policy. The package manifest lists what was included, what was excluded and why, and whether the package is complete.
- **Shadow impact planner.** Given an approved change to a source record, it reports which artifacts, passages and checks are affected, with a reason path for every entry. It runs offline over durable run records. The existing whole-directory invalidation stays authoritative.
- **Blind pre-evaluation.** The harness assesses a specified candidate against a versioned profile with an injectable assessor. The report binds to the candidate's content hash and the profile version. Historical feedback is excluded by policy, and the exclusion is recorded.

The milestone closes on one synthetic scenario: responsibility for Task T03 moves from Participant B to Participant C on an unsubmitted candidate without an Evaluation Summary Report (ESR). Every acceptance item in the handoff's section 11 is a test.

## User Stories

### Graph index and snapshots

1. As an operator, I want every project fact, passage and execution record to carry a stable identity separate from its file path and display name, so that renaming a file does not break links or history.
2. As an operator, I want each record to carry a version, so that an assessment or a package can name the exact version it used.
3. As an operator, I want a graph snapshot to carry a content-derived identity, so that two builds from the same inputs produce the same snapshot and I can detect a stale one.
4. As an operator, I want the graph rebuilt from authoritative records on demand, so that I can discard and recreate it without losing anything.
5. As an operator, I want the builder to reject dangling or ill-typed relationships, so that a traversal always has a defined meaning.
6. As an operator, I want each relationship type to declare its endpoint types and its operational effect, so that a domain link such as "assigned to" is never mistaken for an execution dependency.
7. As an operator, I want a declared status, a verified source span and a current approval kept as three separate fields, so that a label never masquerades as proof.
8. As an operator, I want an imported draft or submitted text stored as an immutable document snapshot with a lifecycle state, so that historical wording is never mistaken for a current commitment.
9. As an operator, I want one authoritative owner per fact, so that the graph and Tier 3 JSON never drift into conflicting copies.
10. As an operator, I want the builder to run with an empty Tier 3, so that I get an explicit empty result rather than a crash or a fabricated node.
11. As an engineer, I want the builder to accept a synthetic fixture repository, so that tests never depend on a real project.
12. As an engineer, I want the existing graph compiler, projector and vault reader to keep working unchanged, so that the staging and promote path is not broken.

### Bounded evidence packages

13. As a drafting agent, I want a package that names its project, profile version, snapshot, task and policy, so that every input I use is traceable.
14. As a drafting agent, I want mandatory constraints and cross-section dependencies included regardless of similarity ranking, so that I never draft against a partial rulebook.
15. As an operator, I want the package manifest to list every included record version and span with a selection reason, so that I can audit what the model saw.
16. As an operator, I want the manifest to list every exclusion with a reason, so that I can see what the model was not allowed to see.
17. As an operator, I want a package that would exceed its budget to return an explicit incomplete status rather than silently dropping required evidence, so that a truncated context never passes as complete.
18. As an operator, I want the package to be immutable once built and to carry its own hash, so that a later execution can prove which package it consumed.
19. As an operator, I want a task or view policy to define permitted content per view, so that revision, integrity audit, blind pre-evaluation and change-impact planning each see only what they may.
20. As an operator, I want the evidence policy enforced before retrieval, including graph expansion, so that a forbidden record cannot enter through a side path.
21. As an operator, I want unresolved items and contradictions listed in the manifest, so that a package built on conflicting evidence says so.
22. As an operator, I want a package built from a stale snapshot to be refused, so that obsolete evidence never enters context.

### Shadow impact planner

23. As an operator, I want to record an approved new version of a source record while keeping the old version, so that history is preserved.
24. As an operator, I want the planner to compute the change set between two versions, including changed relationships and removals, so that a removed link is treated as a change.
25. As an operator, I want the planner to list affected task descriptions, responsibility tables, proposal passages and schedule or resource checks after a task responsibility change, so that I know what to reconsider.
26. As an operator, I want every proposed rerun or reuse entry to carry a reproducible reason path through the graph, so that I can inspect why it was flagged.
27. As an operator, I want the planner to report "unknown dependency coverage" as conservative invalidation, so that a missing edge never justifies skipping work.
28. As an operator, I want a newly relevant source that was absent from the old package to be flagged, so that selection-scope changes are not missed.
29. As an operator, I want the planner to run in shadow mode only, so that the existing fail-closed reuse decision remains the sole authority over what executes.
30. As an operator, I want the planner's advisory report written to a durable Tier 4 location, so that the decision trail is auditable across runs.
31. As an operator, I want the planner to compare its advisory against the actual reuse decision recorded by the scheduler, so that I can measure how often the conservative path over-invalidates.
32. As an operator, I want an unchanged check result to be retained only when an explicit policy says it may be, so that "reconsidered" never silently becomes "unchanged".
33. As an operator, I want a malformed or missing graph snapshot to make the planner refuse, so that a broken index never produces a narrower plan.

### Revision contracts

34. As an operator, I want a revision contract that names permitted change classes and protected facts, so that a task responsibility change cannot also alter the objective, output or timing.
35. As an operator, I want a proposed change that touches a protected fact to be rejected or flagged for review, so that scope creep is caught before drafting.
36. As an operator, I want an unresolved participant capacity to stay explicit in the contract, so that a finding never approves a partner commitment.
37. As an operator, I want a new candidate version created after an approved change, with provenance linking it to the change and its evidence, so that the old candidate stays intact.
38. As an operator, I want an earlier candidate assessment to be marked no longer applicable once the candidate content changes, so that a stale score cannot justify the new candidate.

### Blind pre-evaluation

39. As an operator, I want to assess a specified candidate against a versioned profile without running the production pipeline, so that imported and partial drafts can be scored.
40. As an operator, I want the assessment report bound to the candidate's content hash, profile version and assessor pin, so that a report cannot be reattached to a different draft.
41. As an operator, I want a partial draft assessed with explicit coverage limitations, so that it is never presented as a complete-proposal assessment.
42. As an operator, I want the blind assessor to receive no ESR text, historical scores, target scores, repair plans or internal commitments absent from the candidate, so that the score is not contaminated.
43. As an operator, I want ESR availability recorded at intake as unknown, unavailable, not applicable or available, so that prior submission never implies an available ESR.
44. As an operator, I want an ESR-informed review to be a separately labelled task, so that it is never confused with a blind assessment.
45. As an operator, I want a fake assessor injected in tests, so that no external model is required to exercise scoring, malformed responses, disagreement and failure.
46. As an operator, I want a second synthetic profile to change criteria, scales and thresholds through configuration only, so that call-specific rules never enter core logic.
47. As an operator, I want the assessment report to remain advisory and never a gate result, so that the harness boundary is preserved.
48. As an operator, I want a malformed assessor response to fail the assessment rather than be silently repaired, so that the report is honest.
49. As an operator, I want historical assessments kept immutable, so that a rerun never rewrites a past result.

### Governance and engineering

50. As an engineer, I want the graph-related generic modules covered by the agnosticism lint, so that instance nouns cannot leak in.
51. As an engineer, I want a decision log entry for every ownership decision the milestone makes, so that the authority hierarchy is respected.
52. As an engineer, I want gate authority, the budget-before-Phase-8 block and the whole-directory reuse fingerprint proven unchanged by tests, so that the milestone cannot weaken any gate.
53. As an engineer, I want the new components registered as deterministic components where they write canonical artifacts, so that they are bound in the manifest and recorded in the run result.
54. As an engineer, I want the harness boundary test to pass again, so that the new pre-evaluation lane does not inherit an existing violation.

## Implementation Decisions

### Scope and ownership

- The graph is a **rebuildable index over authoritative records**. Tier 3 JSON stays the owner of approved project facts. Tier 5 section artifacts stay the owner of current generated wording. Tier 4 stays the owner of run and gate outcomes. The graph owns nothing and is always derivable.
- The existing vault-to-docs compiler, the Tier 4 to vault projector, the vault reader and the promote tool are **retained unchanged**. The new builder reads the same authoritative inputs the compiler compares against. Whether the builder also ingests vault nodes is decided per binding in configuration, never by default.
- Ownership per field is written to the decision log before any writer is connected. No field has two writers.

### New package: runner dev-graph

One new package under the runner with a single public API. This is the first test seam.

- **Snapshot builder.** Input: repository root, an optional graph configuration, and an optional candidate document. Output: an immutable snapshot with a content-derived snapshot ID, or a fail-closed error naming the first invalid node or edge. Identical inputs produce byte-identical snapshots. The snapshot ID is computed over canonical JSON of nodes and edges, excluding any wall-clock field.
- **Identity model.** Every node has a canonical ID that is independent of file path and title. Tier 3 records derive their ID from the record's own declared key. Passages derive their ID from section and sub-section identifiers. Execution records derive their ID from run ID and node ID. A version is a content hash of the record's canonical form. A node reference is always `(id, version)`.
- **Closed type set.** Node types for this milestone are limited to what the T03 scenario needs: participant, objective, work package, task, deliverable, milestone, claim, commitment, passage, source, source span, artifact version, execution, assessment, finding, change request, revision contract. Adding a type is a schema change with a test.
- **Closed relationship set** with declared endpoint types, direction and cardinality, and an operational-effect flag distinguishing domain links from execution dependencies. Initial set: `assigned_to`, `contributes_to`, `produces`, `supported_by`, `expressed_in`, `consumes`, `addresses`, `supersedes`, `constrained_by`, `validated_by`. Any other predicate is rejected. `related_to` is not in the set.
- **Evidence fields.** A claim node carries three separate fields: declared status (the existing Confirmed, Inferred, Assumed, Unresolved vocabulary), verified source span (ID, version, offsets, or absent), and current approval (approved, pending, not applicable). The existing evidence-strength to status mapping remains a pure lookup and feeds only the declared status field.
- **Document snapshots.** An imported candidate is stored as an immutable document snapshot node with a lifecycle state from the closed set: imported, draft, submitted, superseded. Passages link to it by span.
- **Package builder.** Input: snapshot, task or view identifier, evidence policy version, budget. Output: an immutable package plus a manifest with package ID, project, task, view, profile version, snapshot ID, policy version, included record versions and spans with selection reasons, mandatory dependencies, exclusions with reasons, unresolved issues, completeness status and package hash. Policy enforcement happens before graph expansion. Over-budget required evidence yields `incomplete`, never a silent drop.
- **View policies** are configuration data, one per view: engineering, controlled revision, integrity audit, blind pre-evaluation, historical feedback analysis, change-impact planning. Each names permitted node types, permitted relationship traversals, maximum expansion depth and forbidden node types. The blind pre-evaluation policy forbids assessment, finding, change request and any node tagged as historical feedback.
- **Impact planner.** Input: two snapshots (before and after an approved change) and the durable run records. Output: a plan listing affected artifacts, passages and checks, each with a reason path (the sequence of edges traversed) and a proposed action from the closed set: rerun, reuse-under-policy, reconsider. Unknown dependency coverage for any affected artifact produces `rerun`. The plan is written as a durable Tier 4 advisory artifact. The planner never writes reuse metadata and never touches the scheduler.
- **Shadow comparison.** A comparison function reads the planner's advisory and the scheduler's recorded reuse decision and emits a diagnostic: agreed, planner narrower, planner broader. Nothing consumes it at runtime.
- **Revision contract checker.** Input: a revision contract (permitted change classes, protected node IDs, unresolved items) and a proposed change set. Output: accepted, rejected with the protected node named, or flagged for review. Pure function, no I/O.
- **Applicability check.** Given an assessment node and a current candidate version, returns applicable or not applicable with the reason (candidate version changed, profile version changed, policy version changed). Assessments are never mutated.
- The four writers that emit canonical artifacts (snapshot, package manifest, impact plan, revision record) are implemented as deterministic components in the existing registry pattern. They are Claude-free and each is closed by a byte-equal replay test.

### Harness: blind pre-evaluation lane

The second test seam is the existing injectable assessor in the harness, used exactly as the current rubric grading run uses it.

- **Candidate binding.** Every assessment report and every cell gains a candidate hash computed with the harness's existing formatting-invariant artifact hash. A report whose candidate hash does not match the candidate on disk is rejected on load.
- **Profile.** A pre-evaluation profile is a versioned configuration bundle: rubric set, scorecard (scale, weights, thresholds), criteria to sub-section mapping, and the instrument type it applies to. The existing rubric-set fingerprint and scorecard ID plus version bijection check is the pattern. A second synthetic profile with different criteria and thresholds must run through the same code with no Python change.
- **Call-specific literals move to configuration.** The instrument type filter, the variant vocabulary, the option-tag grammar, the criterion to section mapping, the default rubric and scorecard paths, and the instrument name in the assessor system prompt become profile fields. The generic lane reads them from the profile.
- **ESR intake record.** A small typed record with availability from the closed set unknown, unavailable, not applicable, available; the bound submission and call identifiers; and the permitted purpose. It is written at intake and read by the policy layer only.
- **Leakage guard.** The blind pre-evaluation view policy is enforced by the package builder. The harness additionally asserts, before invoking the assessor, that no included item is tagged historical feedback, historical score, target score or repair plan. Violation is a hard failure, not a warning. A new exclusion reason, policy-forbidden, joins the existing not-relevant and over-budget reasons.
- **Coverage limitation.** When the candidate lacks sub-sections the profile requires, the report carries an explicit partial-coverage list and is labelled a partial assessment.
- **Advisory only.** The report keeps the existing advisory-true, blocking-false invariant. No gate reads it.
- **Driver placement.** The lane is invoked as a harness module command, not a script, so the one-way harness-to-runner import boundary holds. The existing boundary test must pass.

### Runner integration points that stay unchanged

- The DAG scheduler, node state machine, gate evaluator, gate library, gate result schema and the budget-before-Phase-8 hard block are not modified.
- The whole-Tier-3 reuse fingerprint, the fail-closed reuse conditions and the required audit skills are not modified. The planner's advisory never appears in the reuse decision, the skip binding or the written reuse metadata.
- The scoped node execution and preseed flags are not modified. Imported prose still cannot fabricate predecessor phases.

### Fixtures

- One call-neutral synthetic fixture repository: a minimal Tier 2A registry entry for a synthetic instrument, a Tier 3 set with three participants, two objectives, one work package, tasks T01 to T03, one deliverable, one milestone, and a synthetic candidate with three sections. No real proposal text. No instance-one nouns.
- A second synthetic profile with different criteria names, a different scale and a different threshold.
- A planted ESR-shaped document for leakage tests.

### Decision log

One entry per: field ownership table, retained compiler staging path versus new index, type and relationship set, view policies, shadow-mode rule, ESR intake contract.

## Testing Decisions

A good test exercises a public entry point on a synthetic repository under a temporary directory and asserts on outputs, written artifacts and raised errors. It never asserts on private helpers, call order or internal data structures. A test that can only go red by deleting a feature is preferred to one that inspects how the feature is built.

### Seam 1: runner dev-graph public API

- Build the snapshot from the synthetic fixture. Assert snapshot ID is byte-stable across two builds with different wall-clock stamps. Prior art: the graph determinism check tests, which compile twice into two roots with maximally different timestamps and compare trees.
- Rejection cases: dangling edge, wrong endpoint type, unknown predicate, duplicate ID, empty Tier 3. Each names the offending node or edge. Prior art: vault reader and graph schema tests, which construct minimal front matter inline and parametrise over each vocabulary.
- Package builder: mandatory dependencies present regardless of ranking; forbidden types excluded with a reason; over-budget required item yields incomplete status; stale snapshot refused; manifest hash stable. Prior art: evidence pack tests, which build an in-memory section, write it to a temporary path and assert on the manifest including exclusions.
- Impact planner on the T03 scenario: after changing T03 assignment from B to C, the plan lists the task description, the responsibility table passage, the affected proposal passages and the schedule and resource checks, each with a reason path. A second run with an edge removed from the fixture yields `rerun` for the artifact whose coverage became unknown. A newly relevant source is flagged. Prior art: graph claim verifier tests, which use one red-capable fixture per finding kind.
- Shadow comparison: seed a run manifest with a not-reused decision and a planner advisory that says nothing changed. Assert the diagnostic reports planner-narrower and that no reuse metadata was written. Prior art: reuse tests, which build a full reuse environment in a temporary root and patch only at the scheduler boundary.
- Revision contract checker: permitted responsibility change accepted; change touching the protected objective rejected naming it; unresolved capacity stays flagged. Pure-function tests.
- Applicability: assessment bound to candidate version 1 is not applicable to candidate version 2, with reason.
- Byte-equal replay for each deterministic component. Prior art: deterministic component tests, which compare a registry invocation against a direct call.
- Agnosticism lint covers the new package. Prior art: the lint's real-repository lane.

### Seam 2: harness blind pre-evaluation

- Fake backend returning scripted responses; assert report carries candidate hash, profile version and assessor pin; assert a report loaded against a changed candidate is rejected. Prior art: the rubric grading run tests, which wire a counting fake backend, a frozen clock and a temporary provenance log.
- Same candidate, two profiles, different verdicts and thresholds with no Python change.
- Partial candidate yields a partial-coverage label.
- Planted ESR document: assert no ESR token in the rendered package, assert the ESR path appears in exclusions with reason policy-forbidden, assert the prompt hash inputs contain no ESR text.
- Malformed assessor response fails the assessment. Prior art: judge no-silent-repair tests.
- Disagreement across samples resolves per the existing majority rule. Prior art: verdict tests.
- Report remains advisory-true, blocking-false. Prior art: report tests.
- Boundary test passes with the new module command in place.

### Invariants pinned by tests

- Gate evaluator call sites unchanged: exactly two, both in the scheduler.
- Reuse decision unchanged under any planner advisory.
- Budget-before-Phase-8 hard block unchanged.

## Out of Scope

- Handoff stages 7 and 8: real-document integration, deployment validation, human labels and ESR comparison with real data.
- Enabling fine-grained reuse. The planner stays in shadow mode. Activation is a separate decision after measured evidence.
- A scheduler hook for the planner. The advisory is produced and compared offline.
- Embeddings, Neo4j, Obsidian, Smart Connections or Dataview dependencies.
- Migrating graph-authored records to canonical ownership. The compiler staging plus explicit promote path stays as is.
- Copying the source repository's 24 engineering node types or its mutation policies.
- The Jev typed-decision adapter and live external model access.
- Recording consumed inputs inside the drafter. The planner derives dependencies from declared inputs and durable artifacts; per-invocation consumption records are a later stage.
- A full engineering catalogue of the codebase. Engineering nodes are added only for components this milestone touches.
- Resubmission workflow and historical comparison workflow beyond the intake record and policy exclusion.

## Further Notes

- Tier 3, Tier 5 sections, harness gold sets and rubric reports are empty on this branch after the 22 September 2026 purge. Every test must build its own world. Tests that skip when the reference vault is absent are dormant and must not be relied on.
- The harness boundary test currently fails on this branch because three scripts import the harness. The new lane must not add a fourth. Fixing the three existing offenders is a separate ticket but blocks the "boundary test passes" acceptance item.
- The graph canonical pack deriver does not fail closed on an empty required array. The new package builder must, and the spec's incomplete-status rule covers it.
- The compiler carries a private copy of the claim status severity table. The new package should import the shared one.
- The existing fingerprint helper hashes only direct child names for directories. Snapshot IDs must hash content recursively and must not reuse that helper unchanged.
- The proposal-prose style profile does not govern this document or the code. The internal-docs profile does.
- Both repositories should have their commit SHAs recorded in the first decision log entry, per the handoff's reconnaissance stage. The target is `69b62d9` on `engine-base`. The source pattern repository SHA is not recorded here.
