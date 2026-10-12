# Claude handoff — token efficiency and output-quality tooling

Date: 2026-10-09
Repository: [JozsefKiss90/proposal_orchestrator](https://github.com/JozsefKiss90/proposal_orchestrator)
Branch: `msca-dn-pre-eval`
Repository snapshot inspected: `0b281a4819876de46a0c239c75e6d10747f09120`
Session purpose: assess candidate tooling and define tickets for its potential use and implementation.
Status: planning input; no candidate has been installed or tested through this handoff.

## 1. Instruction to the incoming Claude session

Use this note to prepare a bounded specification and dependency-ordered tickets for improving Claude workflow efficiency and output quality in Proposal Orchestrator.

First establish the current environment, repository state, existing integrations, and actual sources of waste. Then decide which candidates merit a pilot, which duplicate existing capabilities, and which should be deferred or rejected. Produce concrete, reviewable tickets with evidence-based acceptance criteria, cost constraints, and rollback.

The user requested a ticket-definition session. This session may research and author planning artifacts; it does not authorize installing plugins, changing global settings, starting paid services, running new proposal assessments, or implementing the proposed tickets. Use the existing ticketing skill's review workflow to agree the breakdown. Do not impose further approval steps on already authorized research and document preparation.

Treat the inventory below as hypotheses for assessment. Do not assume adoption, promise a savings percentage, or create one installation ticket per tool automatically.

## 2. What has already been done

The preceding research session reviewed the five user-supplied repositories and additional primary documentation. It distinguished:
- usage measurement from mechanisms that reduce usage;
- compression from selective retrieval;
- persistent knowledge from active execution state;
- engineering quality improvements from direct token savings;
- Claude Code extensions from standalone CLI/MCP/API tooling.

Documentation was inspected; no integration, compatibility, privacy, performance, or savings claim was independently runtime-tested. Re-check candidate releases, installation instructions, licenses, dependencies, and authentication before writing implementation steps.

This handoff subsequently inspected repository files on the snapshot above. Installed user-level plugins, local service availability, subscription entitlements, and current workstation configuration remain unknown.

## 3. Complete candidate inventory

IDs below identify candidates in this note only. They are not repository ticket IDs. Priority is an initial research recommendation, not an adoption decision. Every linked source is upstream; pin an exact release/commit for any pilot.

| ID | Candidate and upstream source | Kind and intended function | Initial disposition / question |
|---|---|---|---|
| C01 | [Headroom](https://github.com/headroomlabs-ai/headroom) | Library, proxy, wrapper and MCP; context compression with retrieval of originals; optional output shaping and memory. | Pilot candidate. Compare against Context Mode separately. Verify subscription transport, cache behavior, exact-data exclusions, and optional features. Its documented wrapper can install Serena: avoid duplicate registration. |
| C02 | [Ponytail](https://github.com/dietrichgebert/ponytail) | Skill/plugin; favors reuse, standard features, smaller correct implementations, and focused review. | Pilot candidate for reducing unnecessary implementation and prose. Reconcile with project architecture, required validation, and existing review/TDD skills. |
| C03 | [Anthropic code-review](https://github.com/anthropics/claude-code/tree/main/plugins/code-review) | Multi-agent PR review with confidence filtering. | Selective quality tool. Additional agents add usage; compare with existing review and a targeted reviewer before broad adoption. |
| C04 | [CodeBurn](https://github.com/getagentseal/codeburn) | Local usage analytics CLI/UI, diagnostics and optional MCP. | Baseline measurement candidate. Confirm transcript compatibility, subscription-vs-estimated-cost interpretation, network behavior and reporting fidelity. CLI use may suffice. |
| C05 | [Claude-Mem](https://github.com/thedotmack/claude-mem) | Automatic observations, model-generated summaries, and later retrieval. | Conditional memory pilot. Account for observer calls, hosted options, injection overhead, source staleness, and blind-assessment leakage. |
| C06 | [RTK](https://github.com/rtk-ai/rtk) | CLI and hooks; filters repetitive shell-command output. | Early pilot. Verify native Windows/Powershell or WSL setup, command coverage, exit codes, retained failures and raw-output bypass. Native Read/Grep/Glob are outside its Bash auto-rewrite path. |
| C07 | [pyright-lsp](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/pyright-lsp) | Official Claude Code Python code-intelligence/type-checking plugin. | Early pilot for the Python repository. Verify language-server setup and usefulness alongside the existing IDE. |
| C08 | [typescript-lsp](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/typescript-lsp) | Official Claude Code TypeScript/JavaScript navigation and diagnostics plugin. | Conditional on actual TS/JS work. More relevant to Hermes; do not add it to every Python session without a use case. |
| C09 | [Serena](https://github.com/oraios/serena) | MCP toolkit; symbol-level retrieval, references, editing/refactoring and project memory. | Early navigation pilot or alternative to native LSP support. Compare actual navigation tasks; inspect enabled tool footprint and Headroom overlap. Follow maintained upstream setup guidance. |
| C10 | [Context Mode](https://github.com/mksglu/context-mode) | MCP + hooks; execute/process/index large outputs outside model context, retrieve relevant results, preserve session continuity. | Compression/retrieval pilot alternative to Headroom. Verify routing, permitted execution, raw retrieval, hook overlap, local/hosted features and current ELv2 license. |
| C11 | [Planning with Files](https://github.com/OthmanAdi/planning-with-files) | Skill/plugin; durable task plans, findings and progress with session recovery and reinjection. | Conditional continuity pilot. Integrate with existing tickets and Dev Graph; avoid a second authority for task status. Measure recurring plan overhead. |
| C12 | [Context7](https://github.com/upstash/context7) | MCP or CLI/skills; retrieves library documentation and examples. | On-demand engineering documentation. Hosted retrieval receives queries even when the MCP process runs locally; exclude confidential proposal/ESR content. Verify documented versions and rate limits. |
| C13 | [CLAUDE.md Management](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-md-management) | Official skills/commands; audit project instructions and capture session learning. | Conditional maintenance tool. In this repository CLAUDE.md is constitutional text, not a freely editable learning notebook. No automatic rewriting; assess a separately governed operational note/skill instead. |
| C14 | [PR Review Toolkit](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/pr-review-toolkit) | Official specialized review agents for tests, silent failures, comments, types, correctness and simplification. | Targeted quality pilot. Select reviewer by changed behavior; compare against C03 and the existing code-review skill. Check proactive triggers and invocation-name collisions. |
| C15 | [Basic Memory](https://github.com/basicmachines-co/basic-memory) | Local-first Markdown knowledge graph, search, links and MCP; optional hosted service. | Conditional knowledge-management candidate. Compare with mcpvault, smart-connections, existing Obsidian files and Claude-Mem. Local storage and cloud sync are separate decisions. |
| C16 | [Superpowers](https://github.com/obra/superpowers) | Development methodology plugin/skills; requirements, plans, testing, debugging and review. | Defer broad adoption until overlap assessment. Existing Matt Pocock skills already cover much of this. Evaluate one bounded use case and count questions, agents and extra turns. |
| C17 | [Repomix](https://github.com/yamadashy/repomix) | CLI/MCP context packaging; inclusion/exclusion, token counts and optional structural code compression. | On-demand architecture/handoff tool. Use scoped file selections, not recurring whole-repository dumps. Compressed outlines cannot replace exact source required for editing or evidence. |
| C18 | [ccusage](https://github.com/ccusage/ccusage) | Local transcript usage reporting with scriptable/JSON outputs. | Alternative or cross-check to C04. Prefer external CLI reporting where sufficient; verify pricing/caching assumptions and offline behavior. |
| C19 | [Promptfoo](https://github.com/promptfoo/promptfoo) | Evaluation CLI/library for prompts, models and agent workflows; supports Anthropic and other providers. | Conditional evaluation infrastructure, not a passive optimizer. First examine existing harness coverage and the deferred E10 framework track. No separately metered provider dependency or same-drafter judge substitution. |

These are 19 individual candidates, including two language-server plugins. They are not all installable Claude marketplace plugins.

Built-in Claude Code context inspection, usage reporting, model/effort selection, compaction, deferred MCP tool discovery and CLI use are the baseline comparison. See [Anthropic cost guidance](https://code.claude.com/docs/en/costs). Product behavior depends on the installed version.

## 4. Repository facts that change the assessment

### Authority and source fidelity

Read `AGENTS.md` and `CLAUDE.md` before planning. Both are substantial constitutional documents on the inspected snapshot. In particular:
- §9 makes documented source/state authoritative over agent memory.
- §10 makes skills bounded execution aids, not authorities.
- §13 prohibits silent gate weakening and durable decisions stored only in memory.
- §14 requires explicit human instruction for constitutional amendments.
- §17 defines runtime contracts, layering and failure semantics.

Do not use C13, Headroom learning, Ponytail, or a memory tool to silently modify or reinterpret those rules. If an instruction cleanup would alter constitutional meaning, identify the specific amendment as a separate proposal. Reducing apparent duplication does not itself authorize deletion.

Keep proposal PDFs, verbatim ESR extracts, page sources, document identities, fidelity registers, evidence-pack anchors, hashes, schemas, approved reports, baselines and freeze records intact. Any compressed representation is a derivative view with access to the original; it is not source truth.

### Cost policy and evaluation independence

Read `plans/harness_plan/HARNESS_COST_POLICY.md`. It states that no separately metered paid service may be required to build, test or run the harness. Its native track uses subscription-covered Claude calls and an independent, no-added-cost judge over an OpenAI-compatible transport; metered external-framework work is deferred to E10.

Apply this policy to proposed integrations where they touch the harness. For developer-only tools, identify any separate spend explicitly rather than presuming the policy authorizes it. A free plugin can still generate additional subscription usage or paid observer/API calls.

The harness is advisory, not a new runtime gate. Quality graders must not inherit drafter identity as a substitute for the required independent judge. Do not assume current transport from historical wording: inspect the live configuration and implementation.

### Existing skills and integrations

The snapshot contains `skills-lock.json` entries from `mattpocock/skills`, including code-review, tdd, diagnosing-bugs, research, codebase-design, domain-modeling, handoff, to-spec, to-tickets, grilling and implementation. Related files exist under both `.claude/skills/` and `.agents/skills/`. Their presence does not prove both copies load in every session; inspect discovery and hashes before declaring duplicate overhead.

The project MCP configuration declares `mcpvault`, `smart-connections` and `filesystem`. `.claude/settings.json` enables all project MCP servers. Do not reproduce credentials or personal paths from local configuration in reports. User-level plugins/MCP servers and local overrides were not audited.

Compare memory and knowledge tools against these existing integrations. Compare review and methodology tools against the existing skills. A candidate must address a demonstrated gap.

### Current historical-validation boundary

Read the current ledger and successor reports rather than relying on this snapshot's status indefinitely:
- `plans/msca_dn_historical_validation_tickets.md`
- `plans/msca_dn_v04_v11_preparation_2026-10-09.md`
- `plans/reports/v03_acceptance_lane_completion_2026-10-09.md`
- `harness/ACCEPTANCE_LANE.md`
- `harness/acceptance_lanes/msca_dn_historical.json`

At the inspected snapshot, the V03 report records two clean-worktree runs at 4f2c275: 2,121 passed, zero failed/errors, and 17 declared exclusions over 2,138 collected. It expressly does not validate the official 2025 baseline. The preparation note identifies V04, V05, V07, V09 and V11 as the startable frontier.

These are reported historical results, not checks rerun by this handoff. Do not close V tickets, create additional dependencies for them, or turn tooling adoption into a requirement for historical-baseline acceptance.

V01–V13 constraints prohibit a new assessor run. Benchmark efficiency using bounded engineering tasks, existing outputs, fixtures and isolated copies. No official scoring, freeze, ESR comparison or assessor invocation is implied by this session.

The documented acceptance command is:
```powershell
py -3.10 -m harness.commands.acceptance_lane
```
Inspect current help and test contracts before specifying new flags or a wrapper. Retain full raw evidence and exclusion reconciliation even if Claude sees a compact presentation.

## 5. Separate the proposed integration surfaces

For every candidate declare which surface it touches:

| Surface | Planning question |
|---|---|
| Human-facing Claude Code development session | Can it help engineering without changing production execution? |
| Repository-local skills, hooks and MCP configuration | What is loaded, triggered, changed and versioned? |
| Proposal Orchestrator runtime transport/tool loop | Is a runtime change genuinely needed, and are contracts, cache behavior and declared inputs preserved? |
| Harness, judge and acceptance reporting | Does it preserve independence, evidence, deterministic checks and advisory semantics? |
| Private historical-assessment environment | Can it run within the permitted boundary without retrieving ESR feedback or sending restricted content elsewhere? |

Developer-session success does not establish production-runtime suitability.

Persistent memory and automatic injection need particular scrutiny: an assessor must not receive the ESR, prior scores, comparisons, revision advice, or memories derived from them. Analyze direct tool access, search indexes, startup hooks, shared stores, prompts and observer services. Keep development recall separate from blind-assessment execution; do not claim isolation from directory separation alone.

Local compression/indexing does not make a cloud Claude endpoint private. Document every endpoint, optional cloud feature, model download, observer and telemetry setting. For private-network deployment specify the permitted model endpoint and how dependencies are provisioned.

## 6. Work to perform in the ticket-definition session

1. **Inspect the current environment.** Record OS, native Windows vs WSL, Claude Code version/authentication mode, project/user plugin discovery, installed runtimes, MCP/hook configuration and observed context footprint. Use scoped summaries; never copy secrets into planning artifacts.
2. **Map waste to mechanisms.** Identify repeated reads, oversized terminal outputs, session reconstruction, unnecessary generated code/prose, incorrect API assumptions and expensive review fan-out. Separate measured evidence from inferred causes.
3. **Compare existing capabilities.** Produce a candidate decision matrix: adopt for pilot, defer, reject, or already covered. State evidence, intended surface, overlap, incremental dependencies, recurring overhead and uncertainty.
4. **Define a small baseline and benchmark protocol.** Prefer existing test/report fixtures and reproducible engineering tasks. Pin repository revision, task inputs, candidate version and model/effort settings; isolate variants so caches/memory from one arm do not contaminate another.
5. **Draft bounded tickets.** Define complete, independently verifiable outcomes with genuine blocking edges. Initial research clusters may cover measurement, navigation, terminal output, compression comparison, continuity, selective review and optional evaluation tooling. They are not a mandated ticket count or installation order.
6. **Review the breakdown with the operator using the existing ticket workflow.** Produce the agreed specification, candidate matrix and tickets. End with the ready frontier and unresolved decisions. Do not start implementation in this session.

Assess cheap or built-in alternatives explicitly: scoped `rg`, selective file reads, deterministic log/report extraction, reusable repository maps, and existing skills. For proposal import, compare deterministic scripts and compact machine-readable receipts with asking an LLM to inspect and narrate the entire import.

## 7. Benchmark and adoption criteria to encode in tickets

Measure the whole task, including main agent, subagents, observer/summary calls, retries and original-content retrieval:
- uncached input, cache-write, cache-read and output tokens, with the source and limits of measurement;
- subscription usage where observable, and separately metered charges where applicable;
- wall-clock time, model/tool calls, repeated reads and context resets;
- task correctness, required test results, evidence completeness and operator rework;
- hook/MCP overhead and latency, startup behavior and cache invalidation.

API-equivalent dollar estimates are not the subscription invoice or a reliable reconstruction of the provider's allowance formula. Compression ratio is not end-to-end cost reduction.

Set numerical acceptance targets only after establishing the baseline. No tool is adopted solely because its dashboard reports tokens saved. A cheaper run that loses required evidence, misreads exclusions, changes exact source values or introduces review errors fails the quality requirement.

For small local pilots, state that results establish feasibility rather than a universal savings percentage. Repeat where variability warrants it.

Test relevant failure behavior: missing plugin/service, unsupported command, empty retrieval, compression losing a needed detail, stale memory, malformed output, reviewer false positives, hook collision and endpoint failure. Provide original-output access and an explicit rollback. Preserve the existing fail-closed contracts; do not claim every tool must have the same fallback behavior.

## 8. Required ticket fields and planning outputs

Each ticket should state:
- problem and observed evidence;
- end-to-end outcome and candidate(s);
- intended integration surface and allowed scope;
- blockers and what specifically satisfies them;
- inputs, deliverables and evidence location;
- acceptance criteria and meaningful verification;
- cost/provider constraints and data boundaries;
- overlap/collision handling;
- disable/uninstall/rollback behavior;
- non-goals and completion evidence.

Do not mark installation as sufficient completion. A pilot closes with a measured comparison and an adoption/defer/reject decision.

Use the configured local tracker. The repository's `.claude/skills/setup-matt-pocock-skills/issue-tracker-local.md` specifies:
- `.scratch/<feature-slug>/PRD.md`
- `.scratch/<feature-slug>/issues/<NN>-<slug>.md`
- explicit status and blocker relationships.

A possible new effort slug is `claude-workflow-efficiency`; confirm it does not collide with existing work. The generic to-tickets skill's root-`tickets.md` template must not overwrite the existing ledger when the configured tracker says to use feature-local files. If a durable plan/report is needed under `plans/`, link it to the configured tracker; do not create incompatible status authorities.

Outputs should include a candidate matrix, a bounded specification, a benchmark protocol, dependency-ordered draft tickets, and a short session conclusion identifying the ready frontier. Only create Dev Graph records if the current graph contract requires and supports this effort; resolve actual nodes and schemas rather than fabricating identifiers.

## 9. Suggested skills for Claude

Inspect and invoke the repository's current skill versions as appropriate:
- `/research` for unresolved technical compatibility and upstream behavior.
- `/grill-with-docs` or `/grill-me` for consequential choices not settled by evidence.
- `/to-spec` for the bounded adoption/pilot specification.
- `/to-tickets` for vertical slices, blocker edges and operator review.
- `/handoff` for the next-session summary after ticket planning.

Read the configured domain/tracker guidance first. These suggestions do not authorize implementation or arbitrary agent fan-out. Use `/implement` only in a later session whose task authorizes ticket execution.

## 10. Repository references and opening prompt

Repository references were inspected at the snapshot stated above. Resolve paths against the current checkout and record its HEAD before proceeding. Candidate references remain unpinned upstream sources.

Key read-first references:
- [AGENTS.md](https://github.com/JozsefKiss90/proposal_orchestrator/blob/0b281a4819876de46a0c239c75e6d10747f09120/AGENTS.md)
- [CLAUDE.md](https://github.com/JozsefKiss90/proposal_orchestrator/blob/0b281a4819876de46a0c239c75e6d10747f09120/CLAUDE.md)
- [Harness cost policy](https://github.com/JozsefKiss90/proposal_orchestrator/blob/0b281a4819876de46a0c239c75e6d10747f09120/plans/harness_plan/HARNESS_COST_POLICY.md)
- [Historical-validation tickets](https://github.com/JozsefKiss90/proposal_orchestrator/blob/0b281a4819876de46a0c239c75e6d10747f09120/plans/msca_dn_historical_validation_tickets.md)
- [Current frontier preparation](https://github.com/JozsefKiss90/proposal_orchestrator/blob/0b281a4819876de46a0c239c75e6d10747f09120/plans/msca_dn_v04_v11_preparation_2026-10-09.md)
- [Acceptance lane](https://github.com/JozsefKiss90/proposal_orchestrator/blob/0b281a4819876de46a0c239c75e6d10747f09120/harness/ACCEPTANCE_LANE.md)
- [Existing skill lock](https://github.com/JozsefKiss90/proposal_orchestrator/blob/0b281a4819876de46a0c239c75e6d10747f09120/skills-lock.json)
- [Configured local tracker](https://github.com/JozsefKiss90/proposal_orchestrator/blob/0b281a4819876de46a0c239c75e6d10747f09120/.claude/skills/setup-matt-pocock-skills/issue-tracker-local.md)

Copyable opening prompt:

> Read this handoff and the current repository instructions on msca-dn-pre-eval. This session is for assessing candidate Claude workflow tools and defining potential-use, pilot and implementation tickets. Inspect existing integrations and the cost policy, identify overlaps and uncertainties, and prepare a small measured-adoption plan using our existing specification and ticket workflow. Keep historical-validation work, exact evidence, blind-assessment isolation and runtime gates intact. Produce the candidate decision matrix, benchmark protocol and dependency-ordered tickets for review; do not install tools or execute the tickets in this session.

