---
id: TPL-DASH-002
title: "Phase-Gate State"
node_type: dashboard
evidence_strength: synthesis
status: template
tags:
  - graph-node
  - dashboard
aliases:
  - "Gate State"
---

# Phase-Gate State

Mirror of the orchestration run's phase/gate state. The `phase_gate_state` nodes in
`18_phase_gate_state/` are written by the **docs→graph projector**
(`runner/graph_projector.py`) from durable Tier-4 gate results — they are derived,
read-only, and are **regenerated**, so edit the run, not these nodes.

> [!info] Empty until a run projects state
> This table is empty in a freshly scaffolded vault. Run
> `python -m runner.graph_projector --config graph.config.yaml` after an
> orchestration run to populate it.

## Gate results by phase

```dataview
TABLE phase, gate_status, run_id, evaluated_at
FROM #phase-gate-mirror
SORT phase ASC, gate_id ASC
```

## Failing gates

```dataview
TABLE gate_id, phase, run_id
FROM #phase-gate-mirror
WHERE gate_status != "pass"
SORT phase ASC
```
