---
id: METH-RQ-001
title: "Ten Research Questions"
node_type: research_questions
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
  - "[[Source - Methodology Synthesis Prompt]]"
  - "[[Source - Methodology Idea]]"
evidence_basis:
  - "prompt.txt §10 (ten clarification questions)"
  - "prompt.txt §2, §3, §4, §5, §6, §8, §9"
  - "methodology_idea.txt (tomato-first uncertainty; profit objective; control-stand)"
evidence_strength: source_grounded
confidence: high
maturity: project_decision_needed
owner_role: "[[PI Role]]"
stakeholders:
  - "[[PI Role]]"
  - "[[Methodology Contributor Role]]"
upstream_nodes:
  - "[[Methodology Graph - Meta Node]]"
  - "[[Source - Methodology Synthesis Prompt]]"
downstream_nodes: []
related_nodes:
  - "[[AquaCrop Decision Interface]]"
  - "[[Route Comparison]]"
  - "[[Route A - Direct Probabilistic Fusion]]"
  - "[[Route B - Homogeneous Patch Proxy]]"
  - "[[Latent Field State]]"
  - "[[Diagnostic Branch]]"
  - "[[Ground Truth]]"
  - "[[Validation and Field Trial Layer]]"
  - "[[Uncertainty Chain]]"
  - "[[Profit Based Objective Function]]"
  - "[[Decision Recommendation Logic]]"
  - "[[PlanetScope Usage Gap]]"
  - "[[Data Access Risks]]"
  - "[[Control Stand Variant]]"
  - "[[Validation Risks]]"
  - "[[Web MVP and User Interface Layer]]"
  - "[[Operationalisation Risks]]"
key_terms:
  - "[[Crop Water Stress]]"
  - "[[Root Zone Soil Moisture]]"
  - "[[Expected Profit]]"
  - "[[PlanetScope]]"
risks:
  - "[[Validation Risks]]"
  - "[[Data Access Risks]]"
  - "[[Operationalisation Risks]]"
open_questions:
  - "All ten questions below are themselves the open questions; each is tagged with its current status (unconfirmed / decision needed / open)."
validation_needs:
  - "Answers to RQ4, RQ5, RQ7 and RQ9 define the validation protocol that does not yet exist."
aliases:
  - "10 Research Questions"
  - "Clarification Questions"
tags:
  - methodology-graph
  - research-questions
---

# Ten Research Questions

The ten open questions that the scientific team must answer to fully specify this MSCA-style methodology proposal — each lightly refined for clarity, mapped to the node(s) it concerns, and tagged with its current status.

> [!note] Where these come from
> All ten questions are taken faithfully from the analyst synthesis (`[[Source - Methodology Synthesis Prompt]]`, prompt.txt §10), which closes with the instruction to "ask the scientific team to clarify" these points before proposal writing. Several map onto items the brief flags as unconfirmed or undecided; this node is therefore the central register of what the graph still does **not** know. It is the decision-needed counterpart to the [[Methodology Graph - Meta Node]] hub.

These questions trace the project's "red thread" of uncertainty (see [[Uncertainty Chain]]) from the choice of crop, through the two diagnostic routes, into the decision objective, and out to the validation and operational targets. Resolving them turns the current two-route concept into a committed methodology.

## The questions, mapped and status-tagged

| # | Question (refined for clarity) | Concerns | Status |
|---|---|---|---|
| RQ1 | Is the first crop definitely **tomato**, or more broadly **horticultural row crops**? | [[AquaCrop Decision Interface]] | unconfirmed (tomato tentative) |
| RQ2 | Will **Route A and Route B both** be implemented, or one as main method and the other as fallback/comparison? | [[Route Comparison]], [[Route A - Direct Probabilistic Fusion]], [[Route B - Homogeneous Patch Proxy]] | decision needed |
| RQ3 | What exactly is the target **"field state"** — soil moisture, crop water stress, yield risk, irrigation priority, or all of these? | [[Latent Field State]], [[Diagnostic Branch]], [[Crop Water Stress]], [[Root Zone Soil Moisture]] | decision needed |
| RQ4 | What **ground-truth measurements** will be collected? | [[Ground Truth]], [[Validation and Field Trial Layer]], [[Ground Sensing Layer]] | open |
| RQ5 | How will **uncertainty be evaluated** (e.g. do 90% prediction intervals contain the true value ~90% of the time)? | [[Uncertainty Chain]], [[Validation and Field Trial Layer]], [[Posterior Distribution]] | open |
| RQ6 | What is the **decision objective** — profit, water-use efficiency, yield stability, drought-risk reduction, or a weighted combination? | [[Profit Based Objective Function]], [[Expected Profit]] | decision needed |
| RQ7 | What counts as **pilot success** — better timing, water savings, profit increase, reduced stress-detection error? | [[Decision Recommendation Logic]], [[Validation and Field Trial Layer]] | decision needed |
| RQ8 | Is **PlanetScope access secured** or only optional? | [[PlanetScope Usage Gap]], [[Data Access Risks]] | unconfirmed |
| RQ9 | How will the **homogeneous-patch / control-stand covariation** be validated scientifically? | [[Route B - Homogeneous Patch Proxy]], [[Control Stand Variant]], [[Validation Risks]] | open |
| RQ10 | What is the **TRL target** — research prototype, validated MVP, or operational pilot? | [[Web MVP and User Interface Layer]], [[Operationalisation Risks]] | unconfirmed |

## Notes on individual questions

- **RQ1 (crop).** The methodology idea narrative names tomato only tentatively ("do I remember right, that it would be tomato first?"). The safe framing is "horticultural row crops" until confirmed; this flows directly into how the [[AquaCrop Decision Interface]] is parameterised.

> [!warning] Unconfirmed: tomato as the first crop
> The specific crop (tomato) is **not firmly established** — the PI is unsure in `[[Source - Methodology Idea]]`. Treat "horticultural row crops" as the default and confirm RQ1 before committing crop-specific calibration.

- **RQ2 (routes).** The analyst's own instinct (prompt.txt §10) is to frame the work as a **two-route methodology with one shared decision engine** — `[[Route A - Direct Probabilistic Fusion]]` as the rigorous main route and `[[Route B - Homogeneous Patch Proxy]]` as a creative fallback/comparison — but whether both are actually built is a project decision (see [[Route Comparison]]).
- **RQ3 (field state).** The diagnostic target — what the [[Diagnostic Branch]] estimates as the [[Latent Field State]] — could be any of [[Crop Water Stress]], [[Root Zone Soil Moisture]], yield risk or irrigation priority. Pinning this down scopes the whole diagnostic block.
- **RQ4–RQ5, RQ7, RQ9 (validation).** These four define a validation protocol that does not yet exist: what ground truth is collected, how uncertainty calibration is judged (e.g. 90% prediction-interval coverage), what pilot success means, and how patch covariation is proven. They feed [[Validation and Field Trial Layer]] and [[Validation Risks]].
- **RQ6 (objective).** The methodology idea is emphatic that the objective should be **profit, not yield** (`expected crop value − costs`); RQ6 asks whether that holds or whether a weighted multi-objective is preferred. See [[Profit Based Objective Function]] and [[Expected Profit]].
- **RQ8 (PlanetScope).** Whether higher-resolution PlanetScope imagery is secured or merely optional bears directly on the [[PlanetScope Usage Gap]] and on [[Data Access Risks]] (cost/access are known constraints in the literature).

> [!warning] Unconfirmed: PlanetScope access and TRL target
> RQ8 (PlanetScope access secured vs optional) and RQ10 (TRL target) are **not established in any source**. Do not assume secured access or a specific TRL; both remain open project decisions.

- **RQ10 (TRL).** The brief presents the web MVP as a **standalone research demonstrator**, not a product; the precise TRL target (research prototype vs validated MVP vs operational pilot) is open and shapes [[Web MVP and User Interface Layer]] and [[Operationalisation Risks]].

## Source grounding

- The ten questions verbatim: `[[Source - Methodology Synthesis Prompt]]` (prompt.txt §10).
- Profit-not-yield framing (RQ6) and the tentative tomato crop (RQ1): `[[Source - Methodology Idea]]`, also restated in prompt.txt §6 and §1.
- PlanetScope cost/access and the operational-DSS gap (RQ8, RQ10): consistent with `[[Source - Literature Review]]` Report A, surfaced via prompt.txt §8–§9.

## Links & relationships

This register sits under the [[Methodology Graph - Meta Node]] and connects outward to nearly every category hub: the routes ([[Route A - Direct Probabilistic Fusion]], [[Route B - Homogeneous Patch Proxy]], [[Control Stand Variant]], [[Route Comparison]]), the decision framework ([[Profit Based Objective Function]], [[Decision Recommendation Logic]]), the diagnostic core ([[Diagnostic Branch]], [[Latent Field State]], [[Uncertainty Chain]]), the infrastructure ([[Validation and Field Trial Layer]], [[Web MVP and User Interface Layer]]), and the risk register ([[Validation Risks]], [[Data Access Risks]], [[Operationalisation Risks]]).
