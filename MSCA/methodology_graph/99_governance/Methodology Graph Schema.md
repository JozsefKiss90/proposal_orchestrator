---
id: METH-GOV-001
title: "Methodology Graph Schema"
node_type: governance
status: draft
version: 0.1
created: 2026-06-19
updated: 2026-06-19
domain:
  - crop_water_stress
  - irrigation_decision_support
project_scope:
  - methodology
  - proposal_development
source_refs:
  - "[[Source - LLM Wiki Method]]"
evidence_basis:
  - "Build brief §C.1 (YAML schema), §C.2 (node_type vocab), §C.3 (evidence tags), §C.4 (linking)"
evidence_strength: synthesis
confidence: high
maturity: candidate_method
owner_role: "[[PI Role]]"
stakeholders: []
upstream_nodes:
  - "[[Methodology Graph - Meta Node]]"
downstream_nodes: []
related_nodes:
  - "[[Graph Maintenance Rules]]"
  - "[[Source Traceability Register]]"
  - "[[Source - LLM Wiki Method]]"
key_terms: []
risks: []
open_questions: []
validation_needs: []
aliases:
  - "Graph Schema"
  - "YAML Schema"
tags:
  - methodology-graph
  - governance
---

# Methodology Graph Schema

The canonical schema for every node in the methodology knowledge graph: required YAML front matter, the node-type vocabulary, evidence tags, the ID scheme, and linking conventions. It exists so the graph stays consistent, source-grounded and machine-queryable (see [[Methodology Graph Dashboard]]). Governed by the Karpathy LLM-wiki method ([[Source - LLM Wiki Method]]); maintenance procedures live in [[Graph Maintenance Rules]].

## 1. Required YAML front matter

Every canonical node begins with a `---` YAML block using exactly these field names:

```yaml
---
id: METH-XXX-000
title: ""
node_type: ""
status: draft
version: 0.1
created: 2026-06-19
updated: 2026-06-19
domain:
  - crop_water_stress
  - irrigation_decision_support
project_scope:
  - methodology
  - proposal_development
source_refs: []          # wikilinks to [[Source - ...]] notes
evidence_basis: []       # specific anchors: "prompt.txt §3", "litreview Report A Fig.6", DOIs
evidence_strength: ""    # ONE of: source_grounded | synthesis | inference | unconfirmed
confidence: ""           # high | medium | low
maturity: ""             # concept | candidate_method | validated_in_literature | project_decision_needed
owner_role: ""           # e.g. "[[PI Role]]" or "" if unknown
stakeholders: []
upstream_nodes: []       # wikilinks
downstream_nodes: []     # wikilinks
related_nodes: []        # wikilinks
key_terms: []            # wikilinks to [[09_terminology]] concepts
risks: []                # wikilinks
open_questions: []       # free text or "[[Ten Research Questions]]" refs
validation_needs: []
aliases: []              # OPTIONAL — acronyms/synonyms to aid link resolution
tags:
  - methodology-graph
---
```

Lists are written as block sequences (`- item`). `created`/`updated` for the initial build are `2026-06-19`. Each node always carries `tags: [methodology-graph]` plus one category tag (e.g. `terminology`, `state-of-the-art`, `risk`, `partner`, `infrastructure`, `decision`, `route`, `core`, `source`, `governance`, `meta`, `dashboard`, `research-questions`).

## 2. node_type controlled vocabulary

`meta`, `governance`, `dashboard`, `source`, `architecture`, `state_of_the_art`, `methodology_route`, `methodology_problem`, `decision_method`, `infrastructure_layer`, `risk`, `swot`, `partner`, `concept`, `research_questions`.

## 3. Evidence tagging rules

`evidence_strength` takes exactly **one** value:

| Value | Meaning |
|---|---|
| `source_grounded` | Directly supported by a source (cite it in `evidence_basis`). |
| `synthesis` | A new framing combining sources (state it is synthesis in-body). |
| `inference` | A logical extrapolation (label it in-body, e.g. *(inference)*). |
| `unconfirmed` | Not firmly established; use `confidence: low`, add to `open_questions`, and flag with a `> [!warning]` callout. |

Inference and unconfirmed material must **never** be presented as fact. Use inline tags such as `*(inference)*`, `*(proposal synthesis)*`, and warning callouts. The current distribution of nodes across these values is tracked in [[Source Traceability Register]] and [[Methodology Graph Dashboard]].

## 4. ID scheme

IDs follow `METH-<CAT>-<NNN>`, where `<CAT>` is a short category code (`META`, `GOV`, `DASH`, `SRC`, `CORE`, `SOTA`, `ROUTE`, `DEC`, `INFRA`, `RISK`, `PART`, `RQ`, `TERM`) and `<NNN>` is a zero-padded sequence within that category. IDs are stable and unique; they are the registry key.

## 5. Linking conventions

- Obsidian wikilinks resolve by **file basename** (no folder, no `.md`). Always use the exact registry basename, e.g. `[[Route A - Direct Probabilistic Fusion]]`, `[[AquaCrop Decision Interface]]`, `[[NDVI]]`.
- Populate `upstream_nodes` / `downstream_nodes` / `related_nodes` / `key_terms` in YAML **and** weave the same wikilinks into prose. Minimum ~4–8 outgoing links per content node; terminology nodes ≥3.
- Every node links **up** to its category hub and/or the [[Methodology Graph - Meta Node]], and cites ≥1 `source_refs`.
- Use `aliases` for acronyms/synonyms (e.g. `BHM`, `S1`) so links and search resolve cleanly.

## 6. Sub-pixel dedup decision

There is **one** canonical [[Sub Pixel Problem]] node, in `04_methodological_routes/`. It carries a Definition callout plus `aliases: ["Sub-pixel problem","Mixed pixel problem"]` and doubles as the glossary entry. No duplicate is created in `09_terminology/`; the Terminology MOC links to the canonical node.

## Source grounding

This schema is a **synthesis** of the build-brief governance rules, expressed under the Karpathy LLM-wiki philosophy ([[Source - LLM Wiki Method]]). For how to apply it when adding or updating nodes, see [[Graph Maintenance Rules]].
