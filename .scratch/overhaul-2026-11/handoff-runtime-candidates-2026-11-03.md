# Handoff — implement the runtime deepening candidates

Written 2026-11-03 (Europe/Budapest) at the end of a planning session on the November overhaul.
Repo: `C:\Code\proposal_demo\proposal_orchestrator` · branch `harness_overhaul` · HEAD `5ba39e2d`
("created harness candidates tickets"). The working tree is clean apart from `docs/infrastructure_security/` (AWS work, not ours).

## 1. What the next session is for

Turn the five **runtime** deepening candidates (`runner/{skill_runtime,agent_runtime,claude_transport,semantic_dispatch,transport/}`)
into tickets, then implement them one at a time.

**There are no runtime tickets yet.** Only the six harness tickets (01–06) exist. Step 1 below is writing
the runtime tickets. Do not start coding before they exist and the operator has admitted them.

## 2. Read these first (do not re-derive them)

| What | Where |
|------|-------|
| Constitution — §17 runtime architecture is binding; §14.5 bars agent-made amendments | `CLAUDE.md` |
| The overhaul plan: schedule, **§3 admission rules**, **§5 session brief template**, §6 open decisions | `plans/overhaul_2026-11_plan.md` |
| **Runtime discovery report** (candidates A–E with evidence, diagrams and a recommendation) | `.scratch/overhaul-2026-11/discovery/architecture-review-runtime-2026-11-03.html` |
| Harness report and the confirmed grill record (the decision style to imitate) | `.scratch/overhaul-2026-11/discovery/architecture-review-harness-2026-11-03.html`, `.../discovery/grill-A-judge-call.md` |
| Existing tickets (format, numbering, session-brief block to copy) | `.scratch/overhaul-2026-11/issues/01…06-*.md` |
| Tracker conventions (local markdown, `Status:` line, numbering) | `docs/agents/issue-tracker.md`, `docs/agents/triage-labels.md` |
| Domain vocabulary — runtime glossary, harness glossary, module map | `CONTEXT-MAP.md` → `runner/CONTEXT.md`, `harness/CONTEXT.md`; `plans/reports/RUNTIME_MAP.md` |

Claude project memory, if your session can read it: `caller-context-bindings.md` (relevant to runtime C),
`transport-continuation-splice.md`, `transport-cli-pin.md` and `runner-model-pin.md` (relevant to runtime A).

## 3. State of the overhaul (as of this handoff)

- **Prep stage done:** tracker setup (`docs/agents/`, `CONTEXT-MAP.md`) and domain modelling (three glossaries).
- **Discovery:** both `improve-codebase-architecture` passes are done. Still open: `wayfinder` on F7 and `/ultrareview` on the October diff (Claude Code only).
- **Tickets:** harness 01–06 are written and all `Status: needs-triage`. **Step 3, the scope cut, has not happened**, so no ticket is `ready-for-agent` yet. The plan targets 5–8 tickets in total, and the harness alone already has six. The operator's suggested harness priority is 01 → 03 → 02, with 04–06 deferred first.
- **Step 0 prerequisites are still open, and they block implementation:**
  - `plans/overhaul/BASELINE.md` does not exist (the folder doesn't either). The baseline must be the operator's **Windows workstation** run, `py -3.10 -m pytest -q`: pass, fail and skip counts plus wall time. The device VM lacks `dotenv` and `boto3`, so its numbers are not a baseline.
  - `.env.harness` is still tracked in git and holds a live transport key. The operator still has to rotate it and untrack it. **Never print, copy or commit its contents.**
  - `git worktree prune`: three prunable worktree registrations remain.

## 4. The runtime candidates: what to ticket, and how

Evidence for each candidate is in the runtime report; this section adds only the decisions and order.
The operator has accepted every recommendation in the harness tickets. Present these recommendations
for confirmation, using `grilling` only if the operator wants it.

| Report candidate | Proposed ticket | Recommendation |
|------------------|-----------------|----------------|
| **B · Skill response contract** | `07` — first | Strong. Plan §4 item 6 exactly. No transport change, no change to DN pre-evaluation code, **no PE-09 run needed**. |
| **C · Caller context in one module** | `08` | Worth doing. Pure, in-process. Characterise all five special-cased skills before moving anything. |
| **A · One model-invocation module** | `09` | Strong, but it touches `transport/` → **admission rule 5, PE-09 acceptance lane must be green**. It is much smaller if E is decided first. |
| **D · Node-body plan as a pure function** | none | Defer past 23 Nov unless discovery shows a sequencing bug. |
| **E · Retire cli-prompt mode** | **not a ticket** | Needs the operator to amend `CLAUDE.md` §17 (§14.5) and close the TAPM banner (plan §6). Bring him the evidence: all 24 catalog entries that declare a mode declare `tapm`. Do not edit `CLAUDE.md`. |

Proposed decisions to put in the tickets (confirm with the operator):

**07 · Skill response contract (runtime B)**
- One module owns everything after the transport returns text:
  - JSON extraction (the skill runtime's current policy: the largest object wins, and front-truncation fails closed — made public);
  - envelope unwrapping, and the `run_id` / `artifact_status` no-silent-repair rules (§17.5.4, §17.6.5);
  - the three output-contract write modes (canonical single, `enrich_artifact`, multi-artifact), with atomic writes.
- It returns a `SkillResult`. `run_skill` keeps mode selection, prompt assembly and invocation, and delegates the rest.
- `decomposed_drafting` stops importing the private `_extract_json_response` and uses the public extractor.
- **Size risk:** this moves about 700 lines. A pure move may still break the ≤400 *changed* non-test line rule (§3.3). If it does, split it: 07a parse and validate (Phases D/D.5), then 07b the write modes (Phase E).
- **Out of scope:** making the two JSON-extraction policies consistent. The shared `runner/json_extract.py` (used by `semantic_dispatch` and the harness judge) has no front-truncation guard. Unifying them changes behaviour and is a separate decision for the operator.

**08 · Caller context (runtime C)**
- One module answers "what context does this skill get here?" with three outcomes: context, not applicable, or missing.
- It absorbs the `_build_caller_context` registry, the fail-closed "no context at all" guard, and the four inline special cases in `run_agent`'s skill loop:
  - `invocation_mode` (budget-interface-validation);
  - `gate_id` (gate-enforcement);
  - `resolved_instrument_type` (instrument-schema-normalization);
  - `artifact_path` plus the Tier-5 applicability skip (constitutional-compliance-check, proposal-section-traceability-check).
- The fail-closed rule then covers every binding. Characterisation tests come first: this is the area of the 2026-08-13 guard and the g04_p07 missing-binding failure.

**09 · Model invocation (runtime A)**
- One request in (system, user, optional tools and allowed prefixes, timeout, benchmark tags), one response out (text, files read, rounds exhausted), and a single failure type.
- Adapters: Claude CLI, Bedrock Converse (+ tool loop), OpenAI-compatible (+ tool loop), and an in-memory adapter for tests.
- `run_skill` (both modes) and `semantic_dispatch._invoke_via_backend` call it, and keep mapping the failure to their own categories.
- This **is** the configured transport, so the §17.1.3 call graph is unchanged. Use `codebase-design` "design it twice" here, because it is an interface change.
- Keep it on the runner side. The harness may later adopt it as an adapter (harness ticket 03 is its counterpart), but runner code must never import harness code.

Blocking edges: 07 → none. 08 → none (it touches `agent_runtime.py` only). 09 → 07, because both
restructure `run_skill`; land the contract first, so 09 only replaces the invoke block. Harness and
runtime tickets touch different files except `runner/json_extract.py`: no ticket changes it, so keep it that way.

## 5. Rules every runtime ticket inherits

- `CLAUDE.md` §17 is the contract. Keep the stack scheduler → agent runtime → skill runtime → transport. Gates are evaluated by the scheduler only. Skills don't call skills. No retry or silent repair in the skill runtime (§17.5.4). Python owns the writes, through `_atomic_write`.
- Plan §3 admission rules:
  - one seam;
  - characterisation tests before any move, and failing tests first for any behaviour change;
  - ≤ ~400 changed non-test lines;
  - no constitutional amendment;
  - rule 5 (PE-09 acceptance lane) for anything under `transport/`.
- Plan §5 session brief, per ticket, with base commit, "Read first", seam, do-not-touch and done-when.
  - Done when: targeted tests and the full suite are at or above `BASELINE.md`, `code-review` has run since the base commit with no spec-axis gaps, and there is a decision-log entry if interpretation changed (§9.4).
- One ticket per session. Clear context between tickets. Commit to the current branch.
- Existing test style: most runtime tests patch `runner.claude_transport.invoke_claude_text` and drive `run_skill` end to end. Relevant files: `tests/runner/test_skill_runtime*.py`, `test_agent_runtime.py`, `test_claude_transport*.py`, `test_semantic_dispatch.py`, `test_decomposed_drafting_transport.py`. Keep them green, and add tests at the new interface. Replace, don't layer: delete a test that only exercised a removed internal, once an interface test covers the same behaviour.
- New terms go into `runner/CONTEXT.md` (glossary only, no file paths).

## 6. Suggested order for the session

1. Confirm Step 0 with the operator: `BASELINE.md` exists, or the operator runs the baseline. Don't implement without it.
2. Use `to-tickets` to write `07`, `08`, `09` as `.scratch/overhaul-2026-11/issues/NN-<slug>.md`, `Status: needs-triage`, with each one's decisions, acceptance criteria (failing or characterisation tests first) and session brief, in the same shape as 01–06.
3. Hand back for the operator's Step 3 scope cut. The operator sets `Status: ready-for-agent`.
4. Implement the first admitted runtime ticket (expected: 07) with `implement` + `tdd`, then run `code-review`. One ticket per session.
5. Raise E (the TAPM banner) with the operator as a decision, with evidence; don't implement it.

## 7. Suggested skills

- **`to-tickets`** — write 07–09 in the tracker format above.
- **`grilling`** — only if the operator wants to stress-test a decision rather than accept the recommendations.
- **`codebase-design`** — vocabulary throughout; its **design-it-twice** step for ticket 09 (interface change).
- **`tdd`** — characterisation tests before moves; failing tests first for behaviour changes.
- **`implement`** — executes one ticket (uses `tdd`, then `code-review`, then commits).
- **`code-review`** — after each ticket, since the base commit. Standards axis = `CLAUDE.md` §16–17; spec axis = the ticket.
- **`domain-modeling`** — when a new runtime term crystallises (`runner/CONTEXT.md`).
- **`diagnosing-bugs`** — only for a defect reproduced during the work.
