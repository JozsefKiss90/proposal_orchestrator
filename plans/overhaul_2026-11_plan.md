# Surgical overhaul plan — 2026-11-02 → 2026-11-10

**Window:** the 8 days before the DC/WP structure is final (10 Nov). AWS R11+ is paused, so no
infrastructure tickets run in this window.
**Goal:** clean, refactor and complete the **harness / evaluation** modules and the runtime seams
they depend on, with surgical, well-scoped edits. This is not a rewrite.
**Hard constraint:** MSCA DN pre-evaluation (blind assessment, branch `msca-dn-pre-eval`) has to be *more* reliable on
10 Nov than it is today, because the DN proposal (deadline 23 Nov) will be assessed with it.
After 10 Nov, only bug fixes go in.

---

## 0. What the survey found (2026-11-02, branch `msca-dn-pre-eval` @ `d1e8527f`)

Scale: `runner/` 117 files / 59k lines · `harness/` 57 / 35k · `tools/` 35 / 23k · `tests/` 281 / 145k.

The items below are **hypotheses for the discovery pass to confirm or reject**. They are not decisions.

| # | Area | Evidence | Kind |
|---|------|----------|------|
| F1 | **Tracker drift** | Checkbox state doesn't match the work that was done. `plans/milestones/tickets.md` shows 53 open / 20 done, yet `MILESTONE1_CLOSURE.md` exists and `unit_cost_budget.py` and `docx_exporter.py` are built. `msca_dn_historical_validation_tickets.md` shows V01 with 6 boxes open, yet commit "Pin the extraction environment…" landed 2026-10-08. | Hygiene · it misleads every agent session |
| F2 | **Agent-context drift** | `AGENTS.md` is a hand-kept mirror of `CLAUDE.md`. It has 19 lines of non-mechanical drift, including an extra "Imported Claude Cowork project instructions" section. Root `CONTEXT.md` says "No project is instantiated". `plans/reports/CONTEXT.md` was last touched 2026-07-28 and lists August "current residuals". | Hygiene · high leverage for Fable |
| F3 | **Secret in git** | `.env.harness` is still tracked and holds a live transport key (in history since `fa5b1eb`). | Security quick win |
| F4 | **Runtime god-modules** | `skill_runtime.py` 2739 lines · `dag_scheduler.py` 2538 · `agent_runtime.py` 2206 · `claude_transport.py` 1141. These are protected by the constitution (§17 call graph). The §17 TAPM migration banner has said "IN PROGRESS" since 2026-04-15. | Deepening candidate · high risk |
| F5 | **Judge/backend fan-out** | `harness/judge.py` (Groq / OpenAI-compatible), `harness/commands/_converse_judge.py`, `_subscription_judge.py`, and `runner/transport/{openai_compatible,bedrock_converse,tool_loop,config}.py`. Drafter-refusal / independence checks may live in more than one place. Groq JSON is still salvaged after the fact (no `response_format`). | Deepening candidate |
| F6 | **Bind-by-hash logic spread** | `record_binding`, `record_pointer`, `execution_receipt`, `blind_baseline`, `candidate_provenance`, `runner/fingerprints.py`. Known defect: the E5 rubric checkpoint meta has **no per-section content sha256**, so resume doesn't catch a replaced section. | Deepening candidate + known bug |
| F7 | **Unfinished harness logic** | Eval harness: E5f, E5.1, E6, E7a/b, E8, E9 open (22 boxes). DN validation: X01 imported-source grounding, X02, X03 human DN calibration, X04 cross-baseline comparison, V02c, V14–V16 (V14/V15 are operator steps). Known small gaps: `harness/calibration.py` has no None-guard on precision when there are zero negatives; the E1.5 gold set has ~5 suspected mislabels. | Missing logic |
| F8 | **CLI sprawl** | Entry points are spread across `harness/commands/` (14), `tools/` (35, mostly one-off `author_*` and `diag_*`), and `scripts/`. | Classify only; don't refactor one-offs |
| F9 | **Branch / worktree sprawl** | 30+ local branches. `harness` is stale (pre-E5). There are stale worktree registrations. | Hygiene |

---

## 1. Skill → stage mapping

| Stage | Skill | Used for | Output |
|-------|-------|----------|--------|
| Prep | `/setup-matt-pocock-skills` | **Done 2026-11-03.** Tracker = local markdown under `.scratch/overhaul-2026-11/`; default triage labels; multi-context domain docs (`CONTEXT-MAP.md`). | `docs/agents/*.md`, `CONTEXT-MAP.md`, `AGENTS.md` block |
| Prep | `domain-modeling` | **Done 2026-11-03.** Root `CONTEXT.md` refreshed; new glossaries `runner/CONTEXT.md` and `harness/CONTEXT.md`; module map moved to `plans/reports/RUNTIME_MAP.md`. Pinned: judge = model / assessor = blind-assessment role; *lane* = test suite only. | CONTEXT files + `CONTEXT-MAP.md` |
| Discover | `improve-codebase-architecture` (uses `codebase-design` vocabulary) | One pass each over `harness/` and `runner/{transport,skill_runtime,agent_runtime}`. | HTML report of deepening candidates |
| Discover | `wayfinder` | **Only for F7** (unfinished harness logic). It spans more than one session and the route to "DN pre-eval is trustworthy" isn't clear yet. | map of investigation tickets |
| Review | `/ultrareview` (Claude Code command) | One run on the large, unreviewed October diff: `main...msca-dn-pre-eval` restricted to `harness/ runner/anonymisation_* runner/transport/`. Check its cost/quota in Claude Code before you start it. | finding list |
| Review | `code-review` | Per ticket, since the ticket's base commit. Standards axis = `CLAUDE.md` §16–17. Spec axis = the ticket text. | two-axis review |
| Fix | `diagnosing-bugs` | Only for reproducible defects: F6 checkpoint fingerprint, Groq malformed JSON, anything ultrareview confirms. | failing test → fix |
| Decide | `grilling` | 30 minutes at the scope cut (step 3) to kill weak candidates. | final ticket list |
| Build | `to-tickets` → Fable + Ultracode with `implement` / `tdd` | Execution. | commits |

The `codebase-design` "design it twice" step is only for candidates that change an interface.
Don't run it on hygiene work.

---

## 2. Schedule

| Day | Step | Who |
|-----|------|-----|
| **Mon 2 – Tue 3** | **Step 0, baseline.** (a) Cut `overhaul/2026-11` from `msca-dn-pre-eval`. (b) Run the full pytest suite on Windows and record pass/fail/skip counts and wall time in `plans/overhaul/BASELINE.md`. This is the red line nothing may cross. (c) F3: rotate the key, `git rm --cached .env.harness`, add it to `.gitignore`. (d) F9: `git worktree prune`, and list branches to archive (tag, then delete later). | You, ~2 h |
| Tue 3 | **Step 1, ground truth.** F1: reconcile ticket checkboxes against `git log` (Fable can do this from the commit-subject ↔ ticket-ID mapping; you approve). F2: regenerate `AGENTS.md` from `CLAUDE.md` with a tiny script plus a test that fails on drift, and run `domain-modeling` on both CONTEXT files. | Fable, 1 session |
| Wed 4 | **Step 2, discovery (read-only, parallel).** `improve-codebase-architecture` on `harness/`; the same on the runtime/transport slice; `/ultrareview` on the October diff; `wayfinder` on F7 with the destination "DN pre-evaluation trustworthy for the 2026 DN imported candidate". | Fable, 3–4 sessions in parallel |
| Thu 5 | **Step 3, scope cut.** Merge the findings into one candidate list, then grill it. Keep 5–8 tickets, each passing the §3 admission rules. Run `to-tickets`. | You + Claude |
| Thu 5 – Sun 8 | **Step 4, execution.** One ticket per Fable+Ultracode session, in dependency order. `code-review` after each ticket. Full suite at the end of each day. | Fable |
| Mon 9 | **Step 5, integration.** Full suite vs baseline. One PE-09 acceptance lane run (V03). Merge to `msca-dn-pre-eval`. | You |
| Tue 10 | **Freeze.** Only bug fixes after this. | — |

---

## 3. Admission rules for a ticket (the "surgical" test)

A candidate becomes a ticket only if **all** of these hold:

1. **One seam.** It changes one module's interface, or none. No change to the §17 call graph (scheduler → agent → skill → transport; gates are scheduler-only).
2. **Behaviour-preserving, or the behaviour change is the point.** A refactor ticket ships with characterisation tests written *before* the move. A logic ticket ships with failing tests first (`tdd`).
3. **Fits one session.** Roughly ≤ 400 changed non-test lines. Bigger means split, or route it through wayfinder.
4. **No constitutional amendment.** If it needs one (e.g. closing the §17 TAPM banner), it becomes a separate decision for you, not a Fable ticket (§14.5).
5. **Doesn't touch DN pre-evaluation without an acceptance lane run.** Any change under `harness/blind_*`, `evidence_*`, `execution_receipt`, `anonymisation_*` or `transport/` also needs the PE-09 acceptance lane green.

---

## 4. Likely ticket shortlist (to be confirmed in step 3)

Priority order, given the 23 Nov DN use:

1. **Content fingerprint in run checkpoints (F6, bug).** Per-artifact sha256 in the rubric checkpoint meta; resume refuses on mismatch. Small, high integrity value.
2. **One bind-by-hash module (F6, deepening).** Only if discovery confirms duplicated hashing/canonicalisation. A deep `binding` module that the receipt, baseline, pointer and provenance code call.
3. **One judge-backend seam (F5, deepening).** A single place that builds judge backends and enforces drafter refusal / non-Claude independence; `response_format=json_object` where the provider supports it; salvage kept only as fallback.
4. **Small harness gaps (F7).** Calibration None-guard; V02c stale synthetic contracts.
5. **Whatever wayfinder marks as on the DN critical path.** Most likely X01 (imported-source grounding) and the Stage B (V16) machinery, *not* the operator-run parts (V14/V15).
6. **Runtime extraction (F4).** At most **one** internal extraction (e.g. TAPM prompt assembly or response validation out of `skill_runtime.py`), and only if discovery shows it blocks testability. Otherwise defer past 23 Nov.

Explicitly **out of scope** this window: E7b/E8 (behind M2-T10), E9 Ragas, Milestone 2 graph tickets, AWS R11+, refactoring `tools/author_*` one-offs (F8 is classification only: live / one-off / archive).

---

## 5. Briefing template for each Fable + Ultracode session

```
Ticket: .scratch/overhaul-2026-11/issues/<NN>-<slug>.md   Base commit: <sha>
Read first: CLAUDE.md §16–17, CONTEXT-MAP.md (+ both CONTEXT files), docs/agents/*.md, plans/overhaul/BASELINE.md
Seam: <module> — interface before/after: <...>
Do not touch: §17 call graph, gate_evaluator authority, Tier 1–3 docs, any file outside <paths>
Tests first: <characterisation | failing test names>
Done when: ticket acceptance boxes ticked, targeted tests + full suite ≥ baseline,
           PE-09 acceptance lane green if rule 5 applies, `code-review` run since base with no Spec-axis gaps.
Record: decision-log entry if the change affects interpretation (§9.4).
```

---

## 6. Open decisions for you

- **§17 TAPM banner.** Is the migration actually done? If so, the amendment record should be closed (your instruction is required). If not, say what's left. Either way the stale banner misleads every runtime session.
- **Trunk.** Which branch becomes the long-lived base after 10 Nov (`main` is far behind)? Proposed: merge `msca-dn-pre-eval` → `main` after the freeze and archive the rest by tag.
- **Ultrareview scope.** One run on the October harness/anonymisation diff is proposed. More runs only if the first yields confirmed defects.
