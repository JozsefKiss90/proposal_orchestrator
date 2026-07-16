---
id: TPL-DASH-001
title: "Graph Overview"
node_type: dashboard
evidence_strength: synthesis
status: template
tags:
  - graph-node
  - dashboard
aliases:
  - "Overview"
---

# Graph Overview

Live, queryable overview of this graph vault. The tables below need the **Dataview**
plugin (shipped enabled with this template). If Dataview is disabled, enable it in
*Settings → Community plugins*.

> [!note] Reading the evidence legend
> `evidence_strength` tells you how solid each node's claims are: **source_grounded**
> = directly backed by a source; **synthesis** = a new framing combining sources;
> **inference** = a logical extrapolation; **unconfirmed** = not firmly established.
> Triage the *unconfirmed* table first — those are the graph's weak spots.

## All nodes

```dataview
TABLE node_type, evidence_strength, status
FROM #graph-node
WHERE node_type != "dashboard"
SORT id ASC
```

## Weak spots — unconfirmed evidence

```dataview
TABLE title, node_type
FROM #graph-node
WHERE evidence_strength = "unconfirmed"
SORT id ASC
```

## Per-type counts

```dataview
TABLE length(rows) AS count
FROM #graph-node
GROUP BY node_type
```

## By evidence strength

```dataview
TABLE length(rows) AS count
FROM #graph-node
GROUP BY evidence_strength
```
