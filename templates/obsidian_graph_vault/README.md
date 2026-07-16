# Generic graph-vault template (`obsidian_graph_vault`)

The **fixed home** for the generic, project-agnostic Obsidian graph-vault template
— decided by the milestone-2 topology resolution (ticket 2 / D8) and populated by
**ticket 5** (`obsidian-graph` scaffolding skill + Dataview). It carries **zero
project nouns** — no instrument, domain, or partner names from any single instance
(the "no project nouns" lint, ticket 9, runs over this template).

## Layout

```
obsidian_graph_vault/
├── README.md                     ← this file (outside the node root)
├── graph.config.yaml             ← generic binding contract (project_id: template-instance)
├── .obsidian/                    ← Dataview enabled + vendored (dashboards render live)
│   ├── community-plugins.json    ← ["dataview"]
│   └── plugins/dataview/         ← the vendored plugin (main.js, manifest.json, styles.css)
└── vault/                        ← the NODE ROOT (graph.config.yaml vault_path: vault)
    ├── 00_meta/ … 10_research_questions/   ← methodology folders (skeleton)
    ├── 11_objectives/ … 17_budget/          ← Tier-3 binding folders (compiler source)
    ├── 18_phase_gate_state/                 ← Tier-4 mirror (docs→graph projector target)
    ├── 90_dashboards/                       ← Graph Overview + Phase-Gate State (Dataview)
    └── 99_governance/
```

The node root is the `vault/` subfolder (per `graph.config.yaml`'s `vault_path`), so
`README.md` and `graph.config.yaml` at the template root are **not** parsed as
nodes. Empty folders carry a `.gitkeep`; only real nodes are `.md` with valid
front-matter.

## Instantiate a new instance

Use the `obsidian-graph` skill, or drive the deterministic scaffolder directly:

```python
from pathlib import Path
from runner.vault_scaffold import scaffold_vault, validate_scaffold

result = scaffold_vault(
    Path("templates/obsidian_graph_vault"),
    Path("path/to/new_vault"),
    project_id="acme-ria-2027",
)
validate_scaffold(result)   # confirms the reader/compiler accept it
```

The scaffolder copies this template and swaps in the `project_id` (preserving the
config's comments) — **the whole agnosticism story (D15): one generic layer here,
one per-project `graph.config.yaml` per instance.** It authors no content; a fresh
vault is empty of project facts until a human authors nodes.

## The generic contract

- **Schema:** `runner/graph_schema.py` (node-type vocabulary, required-core vs
  additive-optional front-matter, Appendix-B `evidence_strength` → status).
- **Config:** `runner/graph_config.py` (the `graph.config.yaml` binding contract).
- **Reader:** `runner/vault_reader.py` (deterministic parse).
- **Compiler:** `runner/graph_compiler.py` (graph→docs Tier-3 extraction).
- **Projector:** `runner/graph_projector.py` (docs→graph phase/gate mirror).

The reference instance (instance #1) and its absorbed in-tree location are recorded
in `docs/tier4_orchestration_state/decision_log/graph-topology-d8-absorb_2026-07-16.json`.
