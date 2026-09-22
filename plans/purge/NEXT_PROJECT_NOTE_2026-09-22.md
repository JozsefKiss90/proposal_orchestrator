# Next project — what you must supply on `engine-base`

Derived from what the 2026-09-22 purge emptied. The engine, Tier 0 to Tier 2B, the
constitution and the vault template are in place. Everything below is yours to author.
Order follows the operator manual §3.1 (`Proposal_Engine_Operator_Manual.md`).

## 1. Tier 3 — `docs/tier3_project_instantiation/`

| Step | File | Read by | Note |
|---|---|---|---|
| 1 | `call_binding/selected_call.json` | Phase 1 entry gate, Phase 4 | Must be Confirmed. `call_id` and `topic_code` are gate predicates `g01_p01`/`g01_p02`. Without it the run stops at Phase 1 entry. |
| 2 | `project_brief/concept_note.md` | Phase 2 | Prose. |
| 2 | `project_brief/project_summary.json` | Phase 2 | Structured one-page summary. |
| 2 | `project_brief/strategic_positioning.md` | Phase 2 | Fit to the call, why this team, now. |
| 2 | `project_brief/training_and_career_development.md` | Phase 2, Phase 8 | MSCA-PF only. |
| 3 | `source_materials/**` | Phase 2 | Real sources only: literature, prior results, host data, CV, references `.bib`. |
| 4 | `consortium/partners.json` | Phases 3, 4, 6, 7 | Host, supervisors, secondment and associated partners. |
| 4 | `consortium/roles.json` | Phases 3, 4, 6, 7 | Seat tokens (HOST, SUPERVISOR, …) with status per seat. |
| 4 | `consortium/capabilities.json` | Phase 6 | Evidence of competence per partner. |
| 5 | `architecture_inputs/objectives.json` | Phases 3, 5 | Seeds, not sections. |
| 5 | `architecture_inputs/outcomes.json`, `impacts.json` | Phase 5 | |
| 5 | `architecture_inputs/workpackage_seed.json` | Phase 3 | Intended WP shape. |
| 5 | `architecture_inputs/risks.json` | Phase 6 | Headline risks. |
| 5 | `architecture_inputs/milestones_seed.json` | Phase 4 | Phase 4 populates it; seed optional. |
| 6 | `working_assumptions.json` | Phases 7, 8 | Copy `working_assumptions.example.json`. Optional: the loader treats absence as an empty ledger. Never declare a call-binding fact here as Confirmed. |

Phase 2 derives `call_binding/topic_mapping.json`, `compliance_profile.json` and
`confirmation_checklist.json`. Do not hand-author them unless you are re-instantiating.

## 2. Vault — `<vault>/` (your choice of folder name)

Scaffold with the `obsidian-graph` skill from `templates/obsidian_graph_vault/`. It drops
folders `00`–`18`, `90_dashboards`, `99_governance` and a `graph.config.yaml`. Set
`project_id` and `vault_path` in that config. Author folders `00`–`10` (methodology) before
the project brief; folders `11`–`17` compile into the architecture seeds. Do not name the
vault `MSCA/`: the agnosticism lint treats that noun as an instance leak.

## 3. Tier 2B — check, do not assume

`docs/tier2b_topic_and_call_sources/` still holds the MSCA-PF 2025/2026 work programme and
extracts. If the new project targets a different call, add its work programme and call
extract there and let Phase 1 repopulate `extracted/`. Tier 2B is call-level and stays across
projects; only `call_binding/` is project-level.

## 4. Project vocabulary

`CONTEXT.md` is a project-neutral template. Add the new project's terms below its marker line.

## 5. Run

```
py -3.10 -m runner --run-id <fresh-uuid> --dry-run     # confirms n01 is ready
py -3.10 -m runner --run-id <fresh-uuid>               # Phase 1 onward, gate by gate
```

Use a fresh run id per project. The first gate (`gate_01_source_integrity`) checks step 1
above and nothing else, so it is the cheapest way to confirm the instantiation is wired.

## 6. Housekeeping the purge left to you

- Delete the FIELDWISE branches after you have seen this branch build (`ESR`,
  `fieldwise-run-01/02/03`, local and remote). The archive is tag
  `fieldwise-final-2026-09-22` and `../fieldwise-archive.bundle`.
- Decide about the dirty git worktree under `.claude/worktrees/`.
- Re-freeze the E4 goldens and re-seed the gold sets after the first full run of the new
  project (`py -3.10 -m harness.regression freeze`); the skipped harness tests re-arm then.
