---
id: METH-DEC-006
title: "Decision Recommendation Logic"
node_type: decision_method
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
  - "[[Source - Methodology Idea]]"
  - "[[Source - Methodology Synthesis Prompt]]"
evidence_basis:
  - "methodology_idea.txt ('steer toward the one with the best expected outcome at the end of the season')"
  - "prompt.txt §6 ('compares expected outcomes'); §8 (Decision layer: irrigation recommendation engine, risk thresholds)"
  - "prompt.txt §7 (decision regret definition)"
evidence_strength: source_grounded
confidence: medium
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes:
  - "[[Profit Based Objective Function]]"
  - "[[Prognostic Branch]]"
  - "[[Weather Ensemble Scenario Evaluation]]"
downstream_nodes: []
related_nodes:
  - "[[Decision Engine Layer]]"
  - "[[Uncertainty Chain]]"
key_terms:
  - "[[Expected Profit]]"
  - "[[Expected Utility]]"
  - "[[Decision Regret]]"
risks: []
open_questions:
  - "RQ7: What counts as pilot success (better timing, water savings, profit increase, reduced stress-detection error)?"
validation_needs:
  - "Define decision-performance metrics and success criteria for the pilot"
aliases:
  - "Irrigation recommendation logic"
tags:
  - methodology-graph
  - decision
---

# Decision Recommendation Logic

The final step that **selects** the irrigation decision — steering toward the option with the **best expected end-of-season outcome**, subject to risk thresholds.

## What it is

After every candidate decision has been simulated over weather futures and scored economically, the system **chooses**. The PI's instruction is to *"steer toward the one with the best expected outcome at the end of the season"* (methodology_idea.txt); the analyst synthesis frames the same step as *"compares expected outcomes"* and then recommends (prompt.txt §6). The selection acts on the **[[Expected Profit]]** scores from the **[[Profit Based Objective Function]]**, i.e. it maximises **[[Expected Utility]]** over the **[[Weather Ensemble Scenario Evaluation]]** results, closing the **[[Prognostic Branch]]**.

## Role in this methodology

This is the recommendation end of the pipeline — what the analyst's infrastructure map calls the **irrigation recommendation engine** with associated **risk thresholds** (prompt.txt §8). It is realised operationally in the **[[Decision Engine Layer]]**. Two qualifications keep it honest:

- **Risk thresholds.** prompt.txt §8 lists "risk thresholds" alongside the recommendation engine. Choosing purely by mean expected value can be reckless under wide uncertainty, so the recommendation logic is the natural place to apply risk constraints. *(inference: the sources name risk thresholds but do not specify their exact form.)*
- **Decision regret.** The choice can be assessed by **[[Decision Regret]]** — *"how much worse a chosen decision was compared with the best possible decision after the fact"* (prompt.txt §7) — which is a way to evaluate whether the logic chose well once outcomes are known.

Because uncertainty must travel *all the way into the irrigation decision* (prompt.txt §3), this node is the terminus of the **[[Uncertainty Chain]]**: the recommendation is meaningful only if the spread carried from observation through diagnosis and simulation is still present here.

## Open question

> [!warning] Decision needed — what counts as success
> The criteria for a "good" recommendation — **pilot success** — are **RQ7** in the [[Ten Research Questions]]: better irrigation timing, water savings, profit increase, or reduced stress-detection error (prompt.txt §10). These are not yet decided, and the exact form of the risk thresholds is likewise open. This is why the node carries `confidence: medium`: the *principle* (choose best expected end-of-season outcome) is source-grounded, but the operational decision rule and success metrics are still to be specified.

## Source grounding

- "steer toward the one with the best expected outcome at the end of the season": `methodology_idea.txt`.
- "compares expected outcomes"; irrigation recommendation engine + risk thresholds: `prompt.txt §6`, `§8`.
- Decision regret definition: `prompt.txt §7`. Uncertainty must reach the decision: `prompt.txt §3`.

## Links & relationships

Upstream: [[Profit Based Objective Function]], [[Prognostic Branch]], [[Weather Ensemble Scenario Evaluation]]. Related: [[Decision Engine Layer]], [[Uncertainty Chain]]. Key terms: [[Expected Profit]], [[Expected Utility]], [[Decision Regret]]. Hub: [[Methodology Graph - Meta Node]].
