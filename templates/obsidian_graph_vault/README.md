# Generic graph-vault template home (reserved)

This directory is the **fixed home** for the generic, project-agnostic Obsidian
graph-vault template — decided by the milestone-2 topology resolution (ticket 2 /
D8) and populated by **ticket 5** (`obsidian-graph` scaffolding skill + Dataview).

It is intentionally empty apart from this note until ticket 5 authors the template
here. When populated it will carry, with **zero project nouns**:

- the additive-superset schema (ticket 1 — `runner/graph_schema.py`),
- the folder skeleton (`00…18`) and template dashboards,
- a starter `graph.config.yaml` binding contract (ticket 1 — `runner/graph_config.py`).

The `obsidian-graph` skill instantiates a fresh per-project vault by copying this
template and swapping in a project's `graph.config.yaml` — the whole agnosticism
story (D15): one generic layer here, one per-project config per instance.

The reference instance (instance #1) and its absorbed in-tree location are recorded in
`docs/tier4_orchestration_state/decision_log/graph-topology-d8-absorb_2026-07-16.json`.
The "no project nouns" lint (ticket 9) runs over this template — so this placeholder,
and the template ticket 5 authors here, carry no project nouns.
