# Prompt for Claude Code — FIELDWISE project purge / clean-slate branch

> Paste everything below the line into Claude Code, running in
> `C:\Code\proposal_demo\proposal_orchestrator`.

---

## Task

Purge every FIELDWISE-instance artefact from this repository and leave me a clean,
reusable engine on a fresh branch, ready to instantiate a **new** proposal project.

This is a **project-scoped** purge, not a call-scoped one. Read the two definitions
below before touching anything — they decide every borderline file.

**PROJECT-SPECIFIC (delete)** — anything that exists only because FIELDWISE exists:
the project instantiation (concept, objectives, WPs, budget, consortium, fellow,
references, CV, source materials), all orchestration state produced by running the
engine on it (phase outputs, checkpoints, decision log, validation reports, reuse
caches, run logs), all deliverables (drafts, sections, exports, submitted PDF, ESR
evaluations, review packets), all FIELDWISE plans/tickets/reports/prompts, and the
instance-#1 Obsidian vault content under `MSCA/methodology_graph/`.

**CALL-/INSTRUMENT-SPECIFIC (keep)** — anything reusable by the next MSCA-PF (or
other Horizon) proposal: Tier 0–Tier 2B in `docs/` (external retrieval, normative
framework, instrument schemas, topic/call extracts, work programmes), the engine
itself (`runner/`, `tools/`, `scripts/`, `tests/`, `harness/`), the constitutional
config (`CLAUDE.md`, `AGENTS.md`, `.claude/agents|skills|workflows|output-styles`,
`.mcp.json`, `prose.config.json`, `skills-lock.json`), the generic vault template
`templates/obsidian_graph_vault/`, registries/schemas, and the directory skeletons
(`.gitkeep`) plus `*.example.json` files that define the empty-state contract.

Note the asymmetry that bit us before: `docs/tier2b_topic_and_call_sources/**` is
call-level and **stays**, but `docs/tier3_project_instantiation/call_binding/**`
(including `selected_call.json`, `topic_mapping.json`, `compliance_profile.json`,
`confirmation_checklist.json`) is the *project's binding to* a call and **goes** —
a new project re-derives it. Do not let "it mentions the call" keep a Tier 3 file.

## Ground rules

1. **Nothing is deleted before I approve a manifest.** Work in phases; stop where
   the phase says stop.
2. Delete with `git rm` for tracked files (so the removal is reviewable in the
   diff) and plain deletion for untracked/ignored runtime state.
3. Never edit engine logic to make a check pass. If code or a test depends on a
   purged artefact, surface it as a decision, do not silently patch it.
4. Preserve every directory skeleton: after deletion each emptied directory must
   still exist with its `.gitkeep`. The tier tree is a contract, not a by-product.
5. Precedent: `plans/fieldwise_tickets.md` ticket 1 and
   `plans/fieldwise_reinstantiation_plan.md` §2.1 already performed a partial purge
   of this kind (delete / archive / retain three-way split), and
   `tests/runner/test_fieldwise_purge.py` pins parts of it. Read all three first
   and reuse the method and vocabulary. This purge supersedes that one — it is the
   full version, so the earlier split's "retained" group is now in scope too.

## Phase 0 — Safety and branching

- Confirm the working tree state. There are currently many modified files under
  `.agents/skills/` and `.claude/agents/` on branch `ESR`; report them and ask me
  whether to commit, stash, or leave them before you branch.
- Preserve the FIELDWISE record before destroying it: create an annotated tag
  (e.g. `fieldwise-final-2026-09-22`) on the current HEAD **and** write a git
  bundle of the FIELDWISE branches (`ESR`, `fieldwise-run-01/02/03`) to
  `../fieldwise-archive.bundle` — outside the repo. Verify the bundle with
  `git bundle verify` and tell me the path and size.
- Create the clean branch from the base we agree on. Propose a base (`main` vs.
  current `ESR`) with a one-line reason for each, and a branch name such as
  `clean-slate` or `engine-base`; ask me to pick. Do the work there.
- Do **not** delete the FIELDWISE branches yet — that is a separate, final step I
  will authorise once I have seen the clean branch build.

## Phase 1 — Inventory (no deletions)

Produce `plans/purge/PURGE_MANIFEST_<date>.md` listing every candidate, each with
path, tracked/untracked, size, and a one-line reason, grouped as:

- **A. Tier 3 project instantiation** — everything under
  `docs/tier3_project_instantiation/` except `.gitkeep` and
  `working_assumptions.example.json` (that includes `architecture_inputs/*.json`,
  `call_binding/*`, `consortium/*`, `project_brief/*`, all of `source_materials/`
  incl. the CV, references `.bib`, consolidated pack, Part B draft v0 and the
  `submitted_2025` material, plus `hand_lift_provenance.json` and
  `working_assumptions.json`).
- **B. Tier 4 orchestration state** — `checkpoints/`, `phase_outputs/phase1..8`,
  `reuse/`, `validation_reports/` (52 constitutional-compliance files),
  the whole `decision_log/` including `archive/`, and
  `reinstantiation_provenance.json`.
- **C. Tier 5 deliverables** — `assembled_drafts/`, `proposal_sections/`,
  `review_packets/`, `final_exports/` (14 files), `submitted/`.
- **D. Plans, prompts, reports** — `plans/FIELDWISE_*`, `plans/fieldwise_*`,
  `plans/proposal_issues.md`, `plans/tickets_proposal_issues_2026-09.md`,
  `plans/decision_inputs.md` (check contents first), `plans/prompts/FIELDWISE_*`,
  and every FIELDWISE file in `plans/reports/`. Keep engine-development history
  (`plans/milestones/`, `plans/harness_plan/`, phase-refactor/ticket files that are
  about the engine rather than the proposal) — list any you are unsure about in a
  separate **Ambiguous** section rather than guessing.
- **E. Root-level strays** — `Claude outputs/` (three FIELDWISE .docx),
  `n08f_chat.md`, `runner_fieldwise-run-02.log`, `runner_run02_detached.*.log`,
  `MSCA-preabsorb-b4d9e57.bundle`, the loose `image.png` /
  `1786192761074 (1).jpeg`, `screenshots/`, `costs/` and `bedrock-*.json` if they
  are FIELDWISE run telemetry (check before proposing).
- **F. Ignored runtime state** — `.claude/runs/` (14 run dirs), `.claude/logs/`,
  `.claude/cache/`, `.claude/benchmark/`, `.claude/skill_diag/`,
  `.claude/semantic_diag/`, `.claude/worktrees/`, `__pycache__/`, `.pytest_cache/`,
  `.mypy_cache/`, and `harness/` report/checkpoint output that is FIELDWISE-run
  derived (keep the harness code and its rubric definitions).
- **G. Instance-#1 vault** — `MSCA/`. The authored nodes under
  `methodology_graph/00_meta … 99_governance`, `graph.config.yaml`, `sources/`,
  `MSCA/docs/`, `OBJ-1.md`, `llm_wiki.md`, `Untitled.canvas` are FIELDWISE content.
  Propose removing the instance while confirming that
  `templates/obsidian_graph_vault/` still contains a complete, noun-free skeleton
  the next project can be scaffolded from. If anything generic lives only in
  `MSCA/` and not in the template, say so — that is a migration, not a deletion.
- **H. References from surviving files** — do not delete these, list them: entries
  in `docs/index/*.json` registries, any manifest, `.claude/settings.json`, README
  / CLAUDE.md / AGENTS.md / CONTEXT.md sections, and the `runner/` + `tools/` +
  `tests/` modules that name FIELDWISE (`runner/agnosticism_lint.py` denylist,
  `runner/phase8_canonical_pack.py`, `tools/build_partb1_*`, `tools/annotate_*`,
  `tools/partb1_refactor_*`, `tools/export_open_decisions_docx.py`,
  `tests/runner/test_fieldwise_*`, `tests/harness/test_status_faithfulness.py`,
  `tests/runner/test_phase8_consistency_layer.py`).

**Stop here.** Give me the manifest plus a short summary (counts and total size per
group) and these three decisions stated as explicit questions:

1. **Tests and fixtures** — the `test_fieldwise_*` tests assert on artefacts this
   purge removes. Options: (a) delete them as project-specific, (b) convert their
   fixtures to a synthetic instance so the invariants stay enforced, (c) keep and
   let them fail. Recommend one.
2. **`runner/agnosticism_lint.py` denylist** — it hardcodes instance-#1 nouns
   (AgroVIR, MATE, MVCRI, MSCA, crop, irrigation…) as the proof that the generic
   layer is noun-free. If FIELDWISE is gone, does the denylist stay as the standing
   guard, get re-pointed at the new project's nouns, or move to config? Recommend.
3. **Purge record** — the decision log is being deleted, so where does the record
   of *this* purge live: a single seed record in a fresh `decision_log/`, or only in
   `plans/purge/` and the commit message? Recommend.

## Phase 2 — Execute (only after I approve)

- Delete exactly what the approved manifest lists; nothing extra, nothing skipped.
- Recreate every emptied directory with `.gitkeep`, and restore
  `working_assumptions.json` from `working_assumptions.example.json` if the engine
  requires the file to exist (check the loader before assuming either way).
- Reset, don't delete, anything that is a registry of a contract rather than a
  FIELDWISE artefact: empty the entry lists in `docs/index/*.json` while keeping
  schema/structure valid, and clear FIELDWISE from any manifest the runner reads at
  startup.
- Scrub project narrative out of surviving prose: `CONTEXT.md`, `README.md`,
  `CLAUDE.md`, `AGENTS.md`, `Proposal_Engine_Operator_Manual.md`,
  `.claude/agents/*.md`, `.agents/skills/**`. Replace FIELDWISE examples with
  instrument-level or placeholder wording — do not simply strip sentences and leave
  dangling references. Show me each prose diff separately from the deletions.
- Commit in reviewable slices, one per manifest group, message format
  `purge(<group>): <what and why>`. Do not squash.

## Phase 3 — Verification (report results, do not self-certify)

Run and paste the output of:

- `git status --porcelain` — expect clean.
- `git grep -inE "fieldwise|cholakova|agrovir|mvcri|101373105"` — the only hits
  allowed are ones I approved in Phase 1 decision 2 (and the purge record). List
  every remaining hit with its justification.
- The same grep over untracked/ignored paths (`grep -ri` excluding `.git`).
- `python -m pytest` — full suite, with a per-failure explanation of whether it is
  an expected consequence of the purge or a real regression.
- `python -m runner.agnosticism_lint` (or however it is invoked) — must pass.
- A dry-run instantiation smoke test: whatever the engine's entry point is for
  starting a *new* project (see `scripts/run_msca_pf_e2e.py` and the operator
  manual), prove it can reach at least phase 1 against the empty Tier 3 skeleton
  without a FIELDWISE artefact. If it cannot, that is the most important finding of
  the whole task — report it prominently rather than working around it.
- `du -sh` before/after and a file-count delta.

## Deliverables

1. The clean branch, committed.
2. `plans/purge/PURGE_MANIFEST_<date>.md` (as approved) and
   `plans/purge/PURGE_REPORT_<date>.md` — what was removed, what was intentionally
   kept and why, every residual FIELDWISE reference with its justification,
   verification output, and the archive tag + bundle location.
3. A short "next project" note: the exact list of files the operator must supply to
   instantiate a new proposal on this branch, derived from what you just emptied.
