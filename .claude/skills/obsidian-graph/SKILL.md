---
name: obsidian-graph
description: "Scaffold a fresh, project-agnostic Obsidian graph vault from the generic template so a new proposal instance can be authored in the graph and compiled to docs/**. Use when the user wants to start a new per-project vault, instantiate a second instance, or set up the authoring surface for a new call/project."
disable-model-invocation: true
---

# obsidian-graph — scaffold a per-project graph vault

Instantiate a fresh per-project graph vault from the generic template
(`templates/obsidian_graph_vault/`) so a new proposal instance can be authored in
the graph and compiled to `docs/**` by `runner/graph_compiler.py`. This is the
reusable, multi-project entry point (D15/D16): **one generic template, one
per-project `graph.config.yaml` per instance** — no code changes.

## What the template provides

- The **schema superset** (`runner/graph_schema.py`) — the node-type vocabulary
  and the required-core / additive-optional front-matter contract.
- The **folder skeleton** `00…18`, `90_dashboards`, `99_governance` under the
  node root (`vault/`).
- **Dataview enabled** (`.obsidian/community-plugins.json` lists `dataview` and
  the plugin is vendored under `.obsidian/plugins/dataview/`), so the template
  dashboards render live.
- A **generic `graph.config.yaml`** binding contract with the Tier-3/4/5 bindings
  and no project nouns.

## Steps

1. **Decide the target and id.** Pick the new vault directory and an opaque
   `project_id` (e.g. `acme-ria-2027`). The id is not interpreted as content.

2. **Scaffold (deterministic, no reasoning).** Run the scaffolder — it copies the
   template and swaps in the `project_id`, preserving config comments:

   ```bash
   python -c "from pathlib import Path; from runner.vault_scaffold import scaffold_vault; \
     r = scaffold_vault(Path('templates/obsidian_graph_vault'), Path('<TARGET_DIR>'), '<PROJECT_ID>'); \
     print('scaffolded', r.node_root)"
   ```

   Or drive `runner.vault_scaffold.scaffold_vault(template_dir, target_dir,
   project_id)` directly.

3. **Verify the vault is reader/compiler-acceptable.** Confirm the scaffolded
   vault parses and the no-overlap invariant holds by calling
   `validate_scaffold` on the `ScaffoldResult` from step 2:

   ```bash
   python -c "from pathlib import Path; from runner.vault_scaffold import scaffold_vault, validate_scaffold; \
     r = scaffold_vault(Path('templates/obsidian_graph_vault'), Path('<TARGET_DIR>'), '<PROJECT_ID>', force=True); \
     validate_scaffold(r); print('vault OK:', r.node_root)"
   ```

   `runner.vault_scaffold.validate_scaffold(result)` loads the config, reads the
   vault, and checks `runner/graph_projector.py::check_no_overlap`. It raises the
   fail-closed exception (naming the node/binding) on any problem.

4. **Author honestly.** Populate the binding folders (`11…18`) and
   `proposal_section` nodes. Set each node's `evidence_strength` **honestly**
   (`source_grounded` / `synthesis` / `inference` / `unconfirmed`) — provenance is
   carried end-to-end and an unconfirmed node yields a claim the drafting gates
   correctly block. Do not invent project facts (CLAUDE.md §13.3).

5. **Compile.** Preview the Tier-3 extraction against the hand-lift (non-destructive):

   ```bash
   python -m runner --run-id preview --from-graph <TARGET_DIR>/graph.config.yaml
   ```

## Constitutional notes

- The scaffolder authors **no** content — a scaffolded vault is empty of project
  facts until a human authors nodes. It performs a deterministic copy + a single
  `project_id` rewrite only.
- The template and everything the scaffolder emits carry **zero project nouns**
  (the "no project nouns" lint, ticket 9, runs over the generic layer).
- Scaffolding writes only into the target directory; it makes no tier, gate, or
  DAG change (subordinate to CLAUDE.md).
