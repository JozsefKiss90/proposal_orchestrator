# Dev Graph integration into the Proposal Orchestrator

Implementation-planning handoff · 23 September 2026 · Revised scope

## 1. Mandate and status

Prepare an incremental implementation plan for an ontology-governed, operational graph supporting the Proposal Orchestrator. The Orchestrator is call-agnostic by default; this integration must support all Horizon Europe calls through versioned profiles. The user wants the long-term benefits of graph-based architecture without recreating a costly, unused copy of phase outputs.

This document consolidates the discussion. It is not an implementation report or permission to replace existing repository governance. Read the applicable repository instructions and inspect actual code before planning changes. No repository code was changed for this handoff.

Repositories:

- **Pattern source:** [JozsefKiss90/el_nino, alpaca_paper_trading, dev_graph](https://github.com/JozsefKiss90/el_nino/tree/alpaca_paper_trading/dev_graph).
- **Implementation target:** [JozsefKiss90/proposal_orchestrator, engine-base](https://github.com/JozsefKiss90/proposal_orchestrator/tree/engine-base).

Evidence status: the supplied conversation is the source for accepted direction and earlier inspection findings. For this handoff, the source Dev Graph manual and the target compiler, projector and reuse-module excerpts were checked again. Other repository observations below are inspection leads carried forward from that discussion, not newly verified runtime behaviour. Branches may move; record both commit SHAs at the beginning of implementation planning.

## 2. Scope and independent processes

The integration supports proposal creation, pre-evaluation, controlled revision and, where applicable, resubmission across Horizon Europe calls. No particular project, action type, previous score, target score, deployment environment or prior submission is a prerequisite.

| Layer | Responsibility |
| --- | --- |
| Call-agnostic core | Identities, provenance, graph validation/traversal, evidence policies, dependencies, execution records and revision contracts |
| Versioned call/instrument profile | Applicable entity extensions, proposal structure, criteria, scoring scales/weights/thresholds, constraints and governing sources |
| Project instance | Facts, commitments, candidate versions, selected profile, approvals and any historical material |

Do not hard-code one action's entities, scoring formula, criteria or lifecycle into the core. Validate profile binding explicitly; report unsupported requirements instead of substituting another call's defaults.

**Pre-evaluation/scoring and resubmission are separate processes.** They exchange versioned artifacts through explicit contracts; neither is an inseparable stage of the other.

| Process | Purpose and inputs | Output and relationship |
| --- | --- | --- |
| Pre-evaluation/scoring | Assess a specified draft or candidate against its profile, regardless of submission history or ESR availability | Findings and, where applicable, justified scores bound to candidate and profile; may inform revision |
| Controlled revision | Apply approved changes under preservation and evidence constraints | New candidate and provenance; may follow findings, new facts or other requirements |
| Resubmission | Prepare a new submission after a prior submission, considering current requirements, approved updates and relevant historical feedback if available | Revision plan and candidate; may invoke pre-evaluation independently |
| Historical comparison/calibration | Compare an assessment with suitable historical feedback or independently labelled evidence when available | Diagnostic records; not a prerequisite for pre-evaluation |

Pre-evaluation must be callable on imported or newly drafted candidates without replaying production, performing resubmission or supplying an ESR. Partial drafts may be assessed with explicit coverage limitations; do not represent them as complete-proposal assessments. Findings do not automatically authorise rewriting.

### Determine ESR availability and role per case

An Evaluation Summary Report (ESR) is optional historical evidence. At intake record whether it exists, whether it is accessible, which exact submission and call it concerns, and its permitted purpose. Distinguish unknown availability, unavailable, not applicable and available. Prior submission does not imply an available ESR.

| Situation | Handling |
| --- | --- |
| New proposal without submission history | Pre-evaluate normally; no ESR dependency |
| Prior submission, ESR unavailable or existence unknown | Allow pre-evaluation and governed revision; record limitation and omit ESR-dependent comparison |
| Available ESR correctly bound to historical candidate | Use for explicitly scoped feedback analysis, revision planning or historical comparison |
| ESR binding/version/call applicability uncertain | Resolve applicability before using it as a reference outcome |
| Independent blind assessment | Exclude ESR and historical/target scores even when available; compare only after freezing the assessment |

ESR-informed review is a separate, labelled task, not a blind assessment. Historical comparison uses historical rules; a new candidate uses its selected profile. Never force a scorer to reproduce an ESR score.

The graph supports evidence handling, revision scope and provenance. It cannot guarantee a panel score or prove a semantic rewrite lossless. Synthetic fixtures test infrastructure, not scoring accuracy. Build contracts, retrieval boundaries, offline assessment, change tracking and dependency diagnostics with synthetic inputs. Validate real-document fidelity, model quality and deployment separately when suitable inputs and access exist.

## 3. Architectural direction and invariants

Use a small operational graph whose first jobs are evidence traceability, bounded retrieval and change-impact analysis. Every initial node or relationship should support a concrete query, validation rule or execution decision.

The graph is initially a **rebuildable index over authoritative records**. “Graph-first” means relationships and their consumers are explicit in the design; it does not require graph storage to become the owner of all content.

Preserve these boundaries:

- The Runner owns scheduling and gate enforcement. Graph traversal proposes work; it cannot release gates or create an alternative execution path.
- The harness owns assessment records and diagnostics, separate from production scheduler authority.
- A finding may recommend a change; it cannot approve a partner commitment.
- Draft and submitted statements, current confirmed facts, approved changes, unresolved items and proposed improvements remain distinct.
- Each fact has one authoritative owner. Avoid unrestricted editing of equivalent facts in both JSON and graph notes.
- Absence of a dependency edge is not proof of independence. Unknown dependency coverage retains conservative invalidation.
- Keep historical assessments immutable and bound to their exact candidate. A stale assessment remains a historical result but cannot justify the new candidate.

## 4. Transfer from el_nino: principles and adaptations

The [Dev Graph Operations Manual](https://github.com/JozsefKiss90/el_nino/blob/alpaca_paper_trading/dev_graph/CLAUDE.md) describes an engineering digital twin, canonical ownership, typed relationships, intent-routed context packs, grounding against code and a derived Neo4j projection. Transfer the useful contracts selectively.

| Transfer | Adaptation for the Orchestrator | Concrete benefit |
| --- | --- | --- |
| Stable canonical IDs | Separate entity identity from record version, display name and path; namespace across projects/models | Renames preserve links and history |
| One canonical owner | Define field/record ownership and permitted writers | Avoid conflicting copies |
| Closed types and relationship semantics | Validate endpoint types, direction, required fields and applicable cardinalities | Traversal has a defined meaning |
| Intent-aware routing | Different entry points and policies for engineering, drafting, integrity audit, assessment and impact planning | Task-appropriate context |
| Bounded context packs | Explicit sources, mandatory dependencies, constraints, exclusions and versions | Smaller, inspectable model inputs |
| Admissibility and freshness checks | Check source existence, snapshot membership, supersession, contradictions and task permission | Prevent obsolete or inadmissible evidence from entering context |
| Code/source grounding | Verify engineering records against code; proposal claims against actual source spans | Metadata does not masquerade as proof |
| Decision/constraint/test traceability | Link an architectural decision to contracts, implementation and meaningful tests | Easier maintenance and extension |
| Derived read-only query store | Rebuild from canonical records; validate snapshot before publication | Recoverable index with clear authority |
| Disciplined writeback | Update affected engineering records, provenance and tests when implementation changes | Reduce documentation drift |
| Explicit lifecycle states | Keep planned, implemented, tested, validated and superseded states distinct | Do not present design intent as a working feature |

Do not copy all 24 engineering types into the proposal model. Do not require Neo4j, Obsidian, Smart Connections, Dataview or embeddings for the first working milestone. Retain domain-neutral principles while choosing the simplest store that satisfies the operational queries.

The source manual explicitly distinguishes proactive graph-query habits from mechanical enforcement. Convert correctness-critical requirements into executable checks. Its confidence conventions are also not universal evidence rules: a source count or a `confirmed` label does not establish current institutional approval or semantic support.

Use the source repository's authoring and writeback rules when working there. Do not transplant its project-specific paths, mutation policies, trading concepts or every formatting constraint into the target without an explicit design decision.

## 5. Three connected models

These are separate semantic responsibilities, not necessarily separate databases.

| Model | Main records | Operational responsibility | Authority limit |
| --- | --- | --- | --- |
| **Engineering** | Components, capabilities, interfaces, schemas, prompts, skills, workflow definitions, tests, constraints, decisions | Locate implementation impact; connect features to contracts and verification | Documentation cannot establish that code works |
| **Proposal and Evidence** | Participants, objectives, WPs, tasks, deliverables, milestones, claims, commitments, requirements, sources and source spans; profile-specific extensions as needed | Preserve meaning and assemble relevant evidence | Historical wording is not automatically a current commitment |
| **Execution and Assessment** | Runs, workflow-node executions, artifact versions, consumed inputs, context manifests, gate outcomes, assessments, findings, change requests and revision contracts | Explain production, changes, freshness and rerun/reuse decisions | Assessment and graph state cannot override scheduler gates |

Suggested relationship vocabulary includes `implements`, `validated_by`, `constrained_by`, `assigned_to`, `contributes_to`, `supported_by`, `expressed_in`, `consumes`, `produces`, `addresses` and `supersedes`. The final names and contracts are planning decisions.

Define each relationship's endpoints and operational effect. `related_to` may help browsing, but is inadequate for execution planning. Domain relationships such as `assigned_to` must not automatically behave as execution dependencies. Explicit rules must connect a domain change to affected records, passages and checks.

Example cross-model chain:

> A task-responsibility schema is implemented by a validator and covered by tests (Engineering). Task T03 connects its participant, objective, output and supporting commitment (Proposal and Evidence). A drafting execution consumed T03 version 2 and produced subsection version 5, referenced by a candidate assessment (Execution and Assessment).

Changing task responsibility identifies implementation contracts, meaning to protect and outputs requiring reconsideration.

## 6. Initial ownership arrangement

| Information | Initial authority | Graph treatment |
| --- | --- | --- |
| Approved project facts | Existing Tier 3 records, extended where necessary | Index stable identities, versions and relationships |
| Imported draft or submitted wording | Immutable document snapshot with explicit lifecycle state | Link claims/passages to exact locations without implying prior submission |
| Current generated wording | Versioned proposal artifacts | Index passages and production dependencies |
| Governing requirements and assessment configuration | Versioned profile, applicable source documents and requirement records | Preserve authority, applicability and source location |
| ESR or other feedback, if available | Historical document bound to its actual candidate and call | Optional, purpose-restricted evidence |
| Run and gate outcomes | Existing Runner records | Derived execution view; no gate authority |
| Findings and revision decisions | Versioned assessment/change records | Link findings, approvals and permitted changes |
| Engineering implementation | Code, schemas, tests and versioned decisions/instructions | Ground engineering nodes against those sources |
| Search/traversal graph | No independent factual authority | Rebuildable query index |
| Obsidian views | Inspection and optional controlled editing interface | No unrestricted parallel source of truth |

Resolve ownership per project and per field before connecting writers. If graph-authored project records later become canonical, use a deliberate migration with staging, diffs, validation and rollback. Do not run both ownership arrangements implicitly.

## 7. Existing Orchestrator graph work to retain

Inspect these files and their tests before proposing replacement components. Paths are relative to `proposal_orchestrator` on `engine-base`.

| Existing component | What to retain or verify |
| --- | --- |
| `runner/graph_schema.py` | Controlled types and validation; inspect evidence-status mappings |
| `runner/graph_config.py` and `templates/obsidian_graph_vault/graph.config.yaml` | Project-specific bindings and generic configuration separation |
| `runner/vault_reader.py` | Existing graph-note ingestion contract |
| `runner/graph_compiler.py` | Deterministic, non-inferential extraction; staging and compile-and-diff; Tier 3 and Part B extraction slices |
| `runner/graph_projector.py` | Tier 4 gate-state mirror, scoped writes and enforced non-overlap of sync ownership |
| `runner/phase8_reuse.py` | Conservative fail-closed reuse, existing eligibility checks and audit execution |
| `runner/decomposed_drafting.py` | Subsection drafting integration and prior-subsection context dependencies |
| `harness/HARNESS.md`, `harness/judge.py`, `harness/rubric.py` | Assessment boundary, injectable backend, existing coverage/grounding machinery |
| `AGENTS.md`, `CLAUDE.md`, `.claude/workflows/system_orchestration/manifest.compile.yaml` | Current constitutional, DAG and gate contracts |

**Important direction correction:** the compiler reads vault content and stages document artifacts; it is not a generic Tier 3-to-graph exporter. Its header describes canonical-source cutover as deferred and existing Tier 3 artifacts as the comparison oracle. Preserve this staging capability while implementing the initial Tier 3-authoritative index. Inspect actual entry points and configuration before deciding whether an adapter is needed.

The projector reads durable Tier 4 outcomes and writes only its owned gate-mirror area. Its no-overlap checks and prohibition on influencing gate evaluation must survive integration.

The existing reuse module fingerprints the whole Tier 3 directory for each eligible drafting section, alongside other sources and instructions. It skips expensive drafting only when eligible; audit skills still execute. Do not discard these safeguards to obtain narrower reuse.

Earlier inspection identified a `source_grounded` to `Confirmed` mapping. Preserve compatibility where required, but keep declared status separate from verified source support and current approval. Store supporting span, source version and verification decision explicitly.

## 8. Bounded evidence packages

A context builder should produce an immutable, task-specific package from a validated snapshot.

1. Bind project, call/instrument profile version, source snapshot, task identity and evidence policy.
2. Enforce permitted evidence scope before retrieval, including graph expansion and caches.
3. Select initial candidates by stable IDs and text search.
4. Expand only the relevant typed relationships within defined limits.
5. Include mandatory constraints, dependencies and required cross-section evidence independently of similarity ranking.
6. Verify source versions, admissibility, contradictions and unresolved items.
7. Apply a context budget without silently dropping required evidence; return an explicit incomplete-package result if necessary.
8. Persist the package and manifest, then record exactly what the execution consumed.

| Task/view | Permitted content |
| --- | --- |
| Engineering implementation | Relevant code, contracts, tests, constraints and decisions |
| Controlled revision | Current passage, approved change, protected meaning, connected entities and supporting evidence |
| Integrity audit | Candidate wording plus authoritative internal records, provenance and revision contract |
| Blind pre-evaluation/mock panel | Specified draft or candidate and applicable guidance; no prior submission required |
| Historical feedback analysis, if applicable | Correctly bound ESR/feedback, historical candidate and governing sources under an explicit policy |
| Change-impact planning | Changed versions, domain-to-artifact rules, execution dependencies and consumption records |

The blind assessor must not receive ESR text (if one exists), historical/target scores, repair plans or internal commitments absent from the assessed candidate. Prevent leakage through summaries, metadata, cached packages and tool access. ESR availability must not change the blind policy. A separate labelled feedback-analysis task may use historical feedback after establishing applicability.

Suggested manifest fields: package ID, project/task/view, profile version, source and graph snapshot IDs, policy version, included record versions/hashes and spans, selection reasons, mandatory dependencies, exclusions, unresolved issues, truncation/completeness status and package hash. These are proposed fields, not existing APIs.

Keep sufficient global context for cross-section consistency and complete-candidate assessment. “Bounded” must not mean that a local passage is scored in isolation when the criterion requires the complete candidate. Add embeddings only when measured retrieval shortcomings justify them.

## 9. Safe change propagation and reuse

Separate three questions: what may be affected, what is stale for the current task, and what must execute. Their answers need not be identical.

1. Record an approved new source version while retaining history.
2. Compute the change set, including changed relationships and removals.
3. Traverse explicit impact rules and dependency edges to identify affected artifacts/checks.
4. Reconcile the proposed closure with recorded input consumption, workflow dependencies and global constraints.
5. Explain every proposed invalidation or reuse decision.
6. Submit the plan to existing Runner prerequisites and gates.
7. Execute, validate and record new provenance; reassess the complete candidate when required.

Fingerprint relevant source records, upstream artifacts, prior subsection text, prompts, schemas, implementation/configuration versions, retrieval policies, model configuration and governing constraints. A record absent from the old package may become newly relevant after a change; therefore include selection-policy/scope dependencies, not only previously selected item hashes.

Initially run the planner in **shadow mode**. It reports selective work while the current conservative invalidation remains authoritative. Enable fine-grained reuse only where dependency capture has demonstrated adequate completeness. Missing records, uncertain capture, stale graph snapshots or malformed metadata must never justify skipping work.

Distinguish graph failure from evidence failure: an unavailable optional index may permit the existing conservative path; missing mandatory evidence must block the affected operation or yield an explicit unresolved result. Do not silently fall back to unrestricted model access.

Old gate outcomes and assessments remain immutable. Their applicability to a new input/candidate must be established by current policy. Freshness means compatibility with the current dependency state; it does not establish scientific correctness.

## 10. Runner behaviour and workflow integration

The fixed production DAG remains the execution framework. Introduce narrowly scoped services around it: snapshot validation, context assembly, impact planning, dependency recording and freshness checks. Names and module placement remain to be decided after inspection.

| Execution moment | Proposed addition |
| --- | --- |
| Before planning | Bind validated authoritative and graph snapshots |
| Before a node | Obtain an allowed context package; check completeness and freshness |
| Before reuse | Compare dependencies using a versioned policy; keep existing eligibility/audits |
| After execution | Record consumed versions, package hash, output hashes and provenance |
| After source change | Produce an explained impact plan and downstream freshness updates |
| Before release | Bind assessment to the actual final rendered candidate |

Do not allow an LLM to invent scheduler paths. Deterministic rules govern dependency traversal and execution eligibility. Models can propose findings, extraction mappings or revisions for validation and approval.

The earlier discussion identified scoped `--node` execution and `--preseed-phase8-sections` as possible integration points; verify their current contracts. Imported prose cannot fabricate valid predecessor phases. Independent pre-evaluation must remain callable outside the production DAG for new and previously submitted candidates. This must not bypass production prerequisites, including any currently required budget-before-Phase-8 gate. Verify the gate contract and distinguish it from assessment-service eligibility.

## 11. First operational milestone

Demonstrate one complete synthetic change: **responsibility for Task T03 changes from Participant B to Participant C**.

Use an unsubmitted synthetic candidate without an ESR. Connect the task to its participant, objective, output, timing, evidence, passages and checks. Pre-evaluate the candidate independently, then record the responsibility change and supporting commitment as approved inputs. The revision contract permits responsibility-related changes while protecting objective, output and timing; unresolved participant capacity remains explicit.

Acceptance evidence:

- The planner finds affected task descriptions, responsibility tables, proposal passages and applicable schedule/resource checks.
- An unchanged check result can be retained only under an explicit valid policy; being reconsidered does not automatically imply changed output.
- Revision and blind-assessment packages contain the correct evidence views.
- Protected factual/relational changes are rejected or flagged for review.
- The earlier candidate assessment is no longer applicable after candidate content changes.
- A missing dependency or newly relevant source produces conservative handling.
- Every proposed rerun/reuse decision has a reproducible reason path.
- Gate authority and baseline conservative behaviour remain intact.
- Pre-evaluation succeeds without submission history or an ESR; resubmission is not invoked.
- Additional cases exercise available, unavailable and inapplicable feedback without blind-assessment leakage.
- A second synthetic profile changes criteria/constraints through configuration without changing core logic.

This milestone demonstrates operational value before ontology expansion or a full proposal migration.

## 12. Recommended implementation order

| Stage | Deliverable | Acceptance evidence |
| --- | --- | --- |
| 0. Reconnaissance | Pin both commits; read instructions; map existing graph/harness/Runner code and tests; document ownership conflicts | Evidence-backed component map and explicit gaps |
| 1. Contracts and fixtures | Ownership rules, versioned identities, source states, relationship contracts and call-neutral synthetic fixture and contrasting profile configurations | One owner per fact; historical/proposed/approved states remain distinct |
| 2. Minimal graph builder | Validated, rebuildable snapshot from authoritative inputs | Reject dangling/invalid edges; deterministic graph content from identical inputs |
| 3. Context packages | Task/view policies, bounded traversal, manifests and evidence-boundary enforcement | Mandatory evidence present; prohibited information excluded across retrieval paths |
| 4. Shadow impact planner | Change sets, dependency capture, reason paths and freshness diagnostics | Seeded mutations yield explained scope; uncertain cases preserve broad invalidation |
| 5. Offline assessment plumbing | Fake/injectable assessors, profile-driven criteria/scoring, configured consensus, optional feedback handling and immutable report binding | Exercise no-ESR pre-evaluation, profile variation, malformed responses, disagreement and failure without external models |
| 6. Controlled revision | Revision contracts, protected-content checks, staged patches and provenance updates | Permitted change succeeds; prohibited change is detected; candidate reassessed |
| 7. Real-document integration | Authorised proposal fixtures and mutation copies across differing profiles | Real structure, extraction fidelity, context size, preservation and profile isolation measured |
| 8. Deployment and assessment validation | Target-environment tests, profile-specific datasets and human labels; ESR comparison only if available and applicable | Infrastructure and assessment quality validated separately; no mandatory ESR or deployment topology |

Introduce Engineering records alongside the components actually touched; do not postpone traceability, but avoid a complete codebase catalog before the first milestone. Fine-grained reuse activation is a separate decision after shadow evidence, not an automatic consequence of building the planner.

A real proposal fixture tests document handling, not scoring quality across calls. Use multiple profiles to test call-agnostic behaviour. Inspect harness assumptions and isolate action-specific rules in profiles. Each supported profile needs suitable assessment validation; graph integration does not supply it automatically.

Jev remains a prospective typed-decision adapter inside the harness, not a replacement for it. Keep generative explanations separate from typed decisions; benchmark bounded checks in shadow mode and validate deployment approval before using sensitive material. Neither Jev nor live external-model access is a prerequisite for the initial graph milestone.

## 13. Required output from the planning agent

Produce an implementation plan before changing architecture. It should include:

1. Verified repository state and a table separating existing, partial and proposed capabilities.
2. A transfer map from the source pattern to target components, including deliberate omissions.
3. Ownership and migration decisions, especially the existing graph-to-docs compiler versus the proposed Tier 3-authoritative index.
4. Minimal entity/relationship and versioning contracts, with consumer queries and validation rules.
5. Concrete Runner/harness integration points and contracts that remain unchanged.
6. Ordered work packages with affected files, dependencies, acceptance checks and fallback/rollback behaviour.
7. The synthetic task-responsibility scenario, expected impact closure and evidence packages, including pre-evaluation without an ESR.
8. Evidence needed before activating narrower reuse, plus measures of context size, avoided model work, missed dependencies and maintenance effort.
9. Separation of pre-evaluation, revision, resubmission and optional historical comparison, with case-specific ESR contracts.
10. Profile extension points and tests preventing call-specific rules from entering core logic.
11. Unresolved choices: storage, ID strategy, version granularity, snapshot publication, removal/supersession semantics, dependency capture and approval-state representation.

Prefer a small vertical implementation that answers the five operational questions: **What supports this claim? What depends on this change? What work must be reconsidered? What evidence may this agent see? Which results no longer apply, and why?**

## 14. Rechecked source anchors

These are file/blob identifiers returned during handoff preparation, not branch commit SHAs or proof of runtime validation:

| Source | File/blob SHA |
| --- | --- |
| `el_nino:dev_graph/CLAUDE.md` | `ce4dc39f48116900dd8f8cdf981f5e8b26d7b28c` |
| `proposal_orchestrator:runner/graph_compiler.py` | `69d697bc29c2e3b9f41175df9f34844649b18336` |
| `proposal_orchestrator:runner/graph_projector.py` | `aa5d41dd4440bbf1dd4c670e43852c23b45a0ad5` |
| `proposal_orchestrator:runner/phase8_reuse.py` | `eed55cb0a6d6460a32b54173310826de07993f58` |

The compiler, projector and reuse checks were limited to their relevant opening excerpts. The planning agent must inspect implementations, callers and tests before treating documented guarantees as verified behaviour.
