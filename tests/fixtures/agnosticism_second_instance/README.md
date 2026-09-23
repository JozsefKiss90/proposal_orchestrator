# Agnosticism proof — throwaway second instance

This is the **recorded test-of-done for agnosticism** (milestone 2, ticket 9;
`PHASE8_FULLSCALE_AND_OBSIDIAN_GRILL_BRIEF.md` §2.7 / D15).

It is a second, deliberately **unrelated toy project** — *BorrowBrella*, a
community umbrella-lending network — that compiles to valid `docs/**` artifacts
through the **same** `runner.graph_compiler` used by the MSCA-PF reference
instance. The per-project layer here is **only** `graph.config.yaml` and the
authored `vault/` nodes. **No runner code is edited** to support it: the schema,
reader, compiler, and pack deriver are byte-identical to what instance #1 uses.

If any instance-#1 noun (MSCA / crop / irrigation / a partner name) had leaked
into the generic layer, this instance could not stand on its own terms. The
companion **"no project nouns" lint** (`runner/agnosticism_lint.py`) proves the
negative half; this fixture proves the positive half.

## Contents

```
graph.config.yaml                    # the ONLY project-specific binding layer
vault/
  objectives/
    OBJ-1 Expand station coverage.md  # objective  -> Tier 3 objectives.json
    OBJ-2 Improve return rate.md      # objective  -> Tier 3 objectives.json
  sections/
    EXC-1 Objectives.md               # proposal_section (Excellence) -> Part B
    EXC-2 Concept and approach.md     # proposal_section (Excellence) -> Part B
```

Compiling it yields:

- `docs/tier3_project_instantiation/architecture_inputs/objectives.json` — 2
  objectives, `source_grounded` → **Confirmed** (Appendix-B lookup).
- `docs/tier5_deliverables/proposal_sections/excellence_section.json` — one
  Excellence section, 2 sub-sections, `synthesis` → **inferred** (never
  Confirmed), validating against the *real* retained Tier-5 schema.

## The config diff vs. the generic template

The generic template (`templates/obsidian_graph_vault/graph.config.yaml`) and this
instance differ **only** in the per-project binding layer — never in code:

| | generic template | this instance |
|---|---|---|
| `project_id` | `template-instance` | `borrowbrella-toy-instance` |
| binding folders | numbered `11_objectives … 18_phase_gate_state` | `objectives/` (+ node-type-only `proposal_section`) |
| scope | full Tier-3/4/5 skeleton | minimal (objectives + one Part B section) |

Crucially, this instance uses **different folder names** (`objectives/`,
`sections/`) than the reference instance's numbered folders. The compiler learns
the vault's shape from *this config*, not from hard-coded folder names — so a
differently-shaped vault compiles with no code change, which is the whole point.

## Re-run the proof

```bash
# 1. The lint: the generic layer carries no project noun.
py -3.10 -m runner.agnosticism_lint --repo-root .

# 2. This instance compiles through the same compiler (staging is non-destructive;
#    the residual reported by the CLI is only the diff vs instance #1's oracle).
py -3.10 -m runner.graph_compiler \
  --config tests/fixtures/agnosticism_second_instance/graph.config.yaml \
  --repo-root . --staging-root "$TEMP/bb_scratch"

# 3. The re-runnable assertions.
py -3.10 -m pytest tests/runner/test_agnosticism_lint.py \
  tests/runner/test_agnosticism_second_instance.py -q
```

Durable record: `docs/tier4_orchestration_state/decision_log/ms2-ticket9-agnosticism-proof_2026-07-20.json`.
