# Claude workflow efficiency — measured assessment of five candidate tools

Status: draft (planning only; no candidate installed, no benchmark run, no assessment run)
Source: `plans/claude_plugin_assessment_handoff_2026-10-09.md` (9 October 2026), sections 3 to 9
Scope: candidates C01 to C05 only
Branch: `msca-dn-pre-eval` at `0b281a4819876de46a0c239c75e6d10747f09120`
Written: 2026-10-11
Tracker: `.claude/skills/setup-matt-pocock-skills/issue-tracker-local.md`

## Problem Statement

Claude sessions in this repository spend usage on work that produces no evidence. The handoff names the
suspected sources: repeated file reads, oversized terminal output, session reconstruction after a reset,
generated code and prose beyond what the task required, and review fan-out across several agents.

None of that is measured here. The repository has no recorded baseline for the usage of a bounded
engineering task. It has no agreed instrument for reading usage, and no protocol that produces the same
number twice. Without those, a savings claim rests on a vendor dashboard.

Five candidate tools claim to address parts of the problem. Each also carries a risk this repository
cares about more than it cares about usage.

1. A compression proxy can sit in front of the same `claude -p` the orchestrator transport invokes.
2. An implementation-restraint skill can argue for dropping required validation.
3. A review plugin adds agents, and so adds the usage it is meant to save elsewhere.
4. A usage analytics tool can report API-equivalent dollars that bear no relation to a subscription.
5. A memory tool can inject assessment-derived content into a session that must stay blind.

The last risk is specific and checkable. The blind assessor is isolated by `--tools ""`,
`--strict-mcp-config`, and a working directory outside the repository. The transport source records that
operator MCP servers survive `--tools ""` on its own. Only `--strict-mcp-config` removes them. A
user-level memory server is therefore reachable by any assessor path that omits that flag.

## Solution

Measure before adopting. The effort runs in three stages.

**Stage one records the ground.** One ticket records what actually loads in a session, as opposed to what
is present on disk. One ticket pins a measurement protocol and establishes a baseline from it.

**Stage two pilots each candidate against that baseline.** Five tickets, one per candidate, each closing
with a measured comparison and a decision of adopt, defer or reject. Each pilot declares its surface and
fences the surfaces it must not touch. Each pilot tests the failure behaviour that would make a cheaper
run a worse run.

**Stage three verifies the combination.** One ticket records all five decisions, tests whatever was
adopted for interaction and duplicate context, and removes what was rejected.

Installation is never completion. A ticket closes on a measured comparison and a decision.

## Candidate matrix

The disposition in the handoff is a research recommendation, not a decision. The decision is the output of
the ticket named in the last column.

| ID | Candidate | Kind | Surface it may touch | What the pilot must prove | Decided by |
|---|---|---|---|---|---|
| C01 | Headroom | Compression and retrieval; library, proxy, wrapper, MCP | Development session only | Retrieval returns originals, no orchestrator interposition, no duplicate Serena registration | Ticket 04 |
| C02 | Ponytail | Skill or plugin; implementation restraint | Development session, repository-local skills | Smaller output preserves required tests, architecture and evidence | Ticket 05 |
| C03 | Anthropic code-review | Multi-agent review with confidence filtering | Development session, repository-local plugin | Finding quality against an adjudicated reference, at a counted fan-out cost | Ticket 06 |
| C04 | CodeBurn | Local usage analytics, CLI, UI, optional MCP | Development session | Its output agrees with built-in reporting and transcript evidence on Windows | Ticket 03 |
| C05 | Claude-Mem | Automatic observation, summary and retrieval | Development session only, never the assessor | Synthetic canaries for prohibited content never reach an assessor-shaped session | Ticket 07 |

Candidates C06 to C19 are out of scope for this effort. Context Mode (C10) is the named alternative to
Headroom, and ccusage (C18) the named alternative to CodeBurn. Neither is assessed here. Ticket 04 and
ticket 03 record whether their result justifies opening that comparison.

## Repository constraints that bind this effort

**The constitution governs.** `CLAUDE.md` and `AGENTS.md` are constitutional text. Section 9 makes
documented state authoritative over agent memory. Section 10.2 makes a skill a bounded execution aid.
Section 13.5 forbids durable decisions held only in memory. Section 13.7 forbids silent gate weakening.
Section 14.5 forbids an agent amending the constitution. No ticket in this effort amends constitutional
text, and no candidate may reinterpret it.

**No second status authority.** The configured tracker owns ticket status. This PRD and its issue files
are the status authority for this effort. No candidate may become a competing record of task state.

**The cost policy applies.** `plans/harness_plan/HARNESS_COST_POLICY.md` forbids requiring a separately
metered paid service to build, test or run the harness. A free plugin can still generate subscription
usage or paid observer calls. Every ticket states its spend explicitly rather than presuming the policy
covers it.

**The harness stays advisory.** No candidate becomes a runtime gate. The deterministic predicates and the
byte-equal checks remain the only things that gate a run. The judge stays a non-drafter model.

**The historical-validation boundary holds.** V01 to V13 prohibit a new assessor run. No ticket here runs
an official scoring, a freeze, an Evaluation Summary Report comparison, or an assessor invocation.
Benchmarking uses bounded engineering tasks, existing fixtures and isolated copies. Tooling adoption is
never a dependency of a historical-validation ticket, and no ticket here closes one.

**Source evidence is immutable.** Proposal PDFs, verbatim extracts, page sources, fidelity registers,
evidence-pack anchors, hashes, schemas, approved reports, baselines and freeze records stay intact. A
compressed representation is a derivative view with access to the original. It is not source truth.

## Measurement requirements

Every pilot measures the whole task. That includes the main agent, subagents, observer and summary calls,
retries, recalls, and retrieval of original content.

Recorded per arm:

- uncached input, cache-write, cache-read and output tokens, with the source and limit of the measurement;
- subscription usage where observable, and separately metered charges where any apply;
- wall-clock time, model and tool calls, repeated reads, and context resets;
- task correctness, required test results, evidence completeness, and operator rework;
- hook and MCP overhead, startup behaviour, and cache invalidation.

Three rules close the common failure of this kind of measurement.

1. A missing measurement is recorded as unresolved. It is never recorded as zero.
2. An API-equivalent dollar estimate is not a subscription invoice, and not a reconstruction of the
   provider's allowance formula. A compression ratio is not an end-to-end cost reduction.
3. A small local pilot establishes feasibility. It does not establish a savings percentage.

Numerical acceptance targets are set after ticket 02 produces baseline evidence, not before.

## Ticket map and dependency order

| NN | Ticket | Blocked by | Status |
|---|---|---|---|
| 01 | Record the loaded environment and compatibility surface | none | ready-for-agent |
| 02 | Define the measurement protocol and establish the baseline | 01 | ready-for-human |
| 03 | Evaluate CodeBurn against the measurement evidence | 02 | ready-for-human |
| 04 | Pilot Headroom on the development-session surface | 02 | ready-for-human |
| 05 | Pilot Ponytail while preserving required validation | 02 | ready-for-human |
| 06 | Evaluate Anthropic code-review against the existing reviewer | 01 | ready-for-human |
| 07 | Evaluate Claude-Mem, with isolation as the first gate | 02 | ready-for-human |
| 08 | Close the decision matrix and verify the selected configuration | 03, 04, 05, 06, 07 | ready-for-human |

The graph is acyclic. Ticket 01 is the only root. Tickets 03, 04, 05 and 07 are siblings on ticket 02.
Ticket 06 depends on ticket 01 alone, so review assessment can run while the baseline is still forming.
Ticket 08 requires every pilot resolved, where adopt, defer and reject all count as resolved.

Ready frontier at creation: ticket 01.

## Out of scope

- Installing any candidate outside the scope its ticket names.
- Any change to the orchestrator runtime transport, gate logic, node state semantics, or artifact schemas.
- Any amendment to `CLAUDE.md` or `AGENTS.md`.
- A new proposal assessment, assessor invocation, official scoring, freeze, or report comparison.
- Closing, reopening or adding dependencies to any V ticket in the historical-validation ledger.
- Candidates C06 to C19.
- Adopting a candidate into user-level or global configuration without a recorded uninstall path.

## Unresolved questions

1. **Whether a usable measurement exists at all.** Built-in reporting may not separate cache-read from
   cache-write per task on this version. Ticket 02 either produces a usable recording method, or reports
   that the protocol cannot measure what the handoff requires.
2. **Whether the Headroom pilot can be fenced in practice.** The fence is asserted as a requirement in
   ticket 04. Whether a wrapper or proxy form stays confined to the development session, given inherited
   settings and environment variables, is the pilot's first finding.
3. **What an adjudicated review reference costs.** Ticket 06 needs a reference that previously reviewed
   diffs do not supply on their own. The adjudication effort is operator time, and it is not yet sized.
4. **Whether two runs expose the real variance.** Ticket 02 repeats twice. Model and cache variability may
   need more repeats before any pilot delta is readable.
