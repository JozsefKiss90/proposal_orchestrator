---
id: TPL-META-001
title: "Graph Meta Node"
node_type: meta
evidence_strength: source_grounded
status: template
tags:
  - graph-node
  - meta
aliases:
  - "Meta"
---

# Graph Meta Node

The hub of a graph vault scaffolded from the generic `obsidian_graph_vault`
template. This node exists so a freshly scaffolded vault is non-empty and the
[[Graph Overview]] dashboard renders immediately.

Every node in this vault carries the generic front-matter contract enforced by
`runner/graph_schema.py`:

- **Required core:** `id`, `title`, `node_type`, `evidence_strength`.
- **Additive-optional binding fields:** `tier`, `phase`, `artifact_path`,
  `sub_section_id` — set these on the Tier-3/4/5 binding nodes (folders `11…18`)
  so the compiler and projector route them.

`evidence_strength` carries provenance end-to-end (Appendix-B): `source_grounded`
→ Confirmed, `synthesis`/`inference` → Inferred, `unconfirmed` → Unresolved. Author
each node's `evidence_strength` **honestly** — an unconfirmed node yields a claim
the drafting gates correctly block. Tag every node `#graph-node` so the dashboards
find it.
