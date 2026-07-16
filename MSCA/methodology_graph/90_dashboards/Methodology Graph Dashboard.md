---
id: METH-DASH-001
title: "Methodology Graph Dashboard"
node_type: dashboard
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
  - "Build brief §F.1 (dashboard Dataview queries)"
evidence_strength: synthesis
confidence: high
maturity: candidate_method
owner_role: "[[PI Role]]"
stakeholders: []
upstream_nodes:
  - "[[Methodology Graph - Meta Node]]"
downstream_nodes: []
related_nodes:
  - "[[index]]"
  - "[[Source Traceability Register]]"
  - "[[Ten Research Questions]]"
key_terms: []
risks: []
open_questions: []
validation_needs: []
aliases:
  - "Dashboard"
tags:
  - methodology-graph
  - dashboard
---

# Methodology Graph Dashboard

Live, queryable overview of the methodology knowledge graph. Up to the [[Methodology Graph - Meta Node]]; for the static map see [[index]] and for source health see [[Source Traceability Register]].

> [!note] Reading the evidence legend
> `evidence_strength` tells you how solid each node's claims are: **source_grounded** = directly backed by a source; **synthesis** = a new framing combining sources; **inference** = a logical extrapolation; **unconfirmed** = not firmly established (treat with care, `confidence: low`). When triaging, start with the *unconfirmed* and *project_decision_needed* tables below — those are the graph's weak spots and decision points.

> [!info] Dataview required
> The tables below need the Dataview plugin. If it is disabled, use [[index]] for the static node list and [[Source Traceability Register]] for the source mapping.

## All graph nodes

```dataview
TABLE node_type, status, evidence_strength, confidence, maturity
FROM #methodology-graph
WHERE node_type != "dashboard"
SORT id ASC
```

## Weak spots — unconfirmed evidence

```dataview
TABLE title, evidence_strength, confidence
FROM #methodology-graph
WHERE evidence_strength = "unconfirmed"
SORT id ASC
```

## Decisions needed

```dataview
TABLE title, open_questions
FROM #methodology-graph
WHERE maturity = "project_decision_needed"
SORT id ASC
```

## Open questions surface

```dataview
TABLE open_questions
FROM #methodology-graph
WHERE open_questions
SORT id ASC
```

## Per-category counts

```dataview
TABLE length(rows) AS count
FROM #methodology-graph
GROUP BY node_type
```

## By evidence strength

```dataview
TABLE length(rows) AS count
FROM #methodology-graph
GROUP BY evidence_strength
```

## Recently updated

```dataview
TABLE updated, version
FROM #methodology-graph
SORT updated DESC
LIMIT 15
```

## How to use this dashboard

- **Triage credibility:** the *unconfirmed evidence* table lists nodes whose claims are not yet source-grounded (e.g. partner identities, tomato, PlanetScope access, TRL — see [[Ten Research Questions]]). These should be confirmed or down-scoped before the proposal hardens.
- **Track decisions:** the *decisions needed* table lists `project_decision_needed` nodes (e.g. [[Route Comparison]], [[Profit Based Objective Function]], [[Web MVP and User Interface Layer]]).
- **Maintain quality:** promotions and edits follow [[Graph Maintenance Rules]]; the schema behind every field is in [[Methodology Graph Schema]].
