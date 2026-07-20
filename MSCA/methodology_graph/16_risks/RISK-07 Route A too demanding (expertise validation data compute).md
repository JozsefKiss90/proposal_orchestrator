---
id: RISK-07
title: Route A too demanding (expertise / validation data / compute)
node_type: risk
evidence_strength: synthesis
tier: tier3
aliases:
- RISK-07
description: The rigorous one-step probabilistic fusion route may exceed available modelling expertise, validation data or compute within the fellowship.
category: model_complexity
probability: medium
impact: high
affected_objectives:
- OBJ-1
affected_work_packages:
- WP1
mitigation: Keep Route B as a credible fallback; stage the build; provision the probabilistic-modelling compute runtime.
contingency: Adopt Route B as the primary diagnostic route, with Route A as a comparison where resources allow (RQ2).
risk_owner: FELLOW
source_vault_nodes:
- Risk Register R7 (METH-RISK-002)
- Model Complexity Risks (METH-RISK-005)
- Route A - Direct Probabilistic Fusion (METH-ROUTE-001)
- Probabilistic Modelling Runtime (METH-INFRA-006)
provenance_detail: source_grounded (hazard) / synthesis (likelihood-impact estimate)
---

The rigorous one-step probabilistic fusion route may exceed available modelling expertise, validation data or compute within the fellowship.

## Related

**Grounded in methodology nodes:** Risk Register R7 (METH-RISK-002), [[Model Complexity Risks]], [[Route A - Direct Probabilistic Fusion]], [[Probabilistic Modelling Runtime]]

**Related architecture nodes:** [[OBJ-1]], [[WP1]]
