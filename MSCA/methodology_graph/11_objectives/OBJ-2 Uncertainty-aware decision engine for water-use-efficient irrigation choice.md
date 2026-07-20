---
id: OBJ-2
title: Uncertainty-aware decision engine for water-use-efficient irrigation choice
node_type: objective
evidence_strength: source_grounded
tier: tier3
aliases:
- OBJ-2
description: 'Develop the prognostic decision engine that turns the diagnosed field state into an irrigation recommendation: calibrate the FAO AquaCrop model in an uncertainty-aware way that retains an honest parameter posterior, run counterfactual irrigation simulations over weather ensembles, and select the option that best improves water-use efficiency.'
measurable_target: An integrated decision engine that scores candidate irrigation decisions by water-use efficiency (WUE) under weather and model uncertainty, propagating uncertainty from diagnosis into the recommendation. The decision objective is water-use efficiency (RQ6, operator-confirmed).
target_month: 15
pillar: Prognostic branch
responsible_partner: FELLOW
contributing_partners:
- SUPERVISOR
source_vault_nodes:
- AquaCrop Decision Interface (METH-DEC-001)
- Uncertainty Aware AquaCrop Calibration (METH-DEC-002)
- Counterfactual Irrigation Simulation (METH-DEC-003)
- Weather Ensemble Scenario Evaluation (METH-DEC-004)
- Profit Based Objective Function (METH-DEC-005)
- Decision Recommendation Logic (METH-DEC-006)
resolved_decisions:
- RQ6 = water-use efficiency (WUE)
note: The vault's objective-function machinery (Profit Based Objective Function METH-DEC-005) is the mechanism for scoring irrigation decisions by an expected-value criterion; RQ6 instantiates that mechanism with water-use efficiency as the chosen criterion. The uncertainty-aware AquaCrop calibration is the project's (vault-grounded) methodology; it is not attributed to the fellow.
provenance_detail: source_grounded (objective-function machinery) + operator_confirmed (RQ6 objective)
---

Develop the prognostic decision engine that turns the diagnosed field state into an irrigation recommendation: calibrate the FAO AquaCrop model in an uncertainty-aware way that retains an honest parameter posterior, run counterfactual irrigation simulations over weather ensembles, and select the option that best improves water-use efficiency.

## Related

**Grounded in methodology nodes:** [[AquaCrop Decision Interface]], [[Uncertainty Aware AquaCrop Calibration]], [[Counterfactual Irrigation Simulation]], [[Weather Ensemble Scenario Evaluation]], [[Profit Based Objective Function]], [[Decision Recommendation Logic]]
