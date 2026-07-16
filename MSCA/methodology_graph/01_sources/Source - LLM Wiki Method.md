---
id: METH-SRC-004
title: "Source - LLM Wiki Method"
node_type: source
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
  - "build request (Karpathy LLM-wiki method described in the build brief §A)"
evidence_strength: synthesis
confidence: medium
maturity: candidate_method
owner_role: ""
stakeholders: []
upstream_nodes: []
downstream_nodes:
  - "[[Methodology Graph - Meta Node]]"
  - "[[Graph Maintenance Rules]]"
  - "[[Methodology Graph Schema]]"
related_nodes:
  - "[[Methodology Graph - Meta Node]]"
  - "[[Graph Maintenance Rules]]"
  - "[[Methodology Graph Schema]]"
  - "[[Source Traceability Register]]"
key_terms: []
risks: []
open_questions: []
validation_needs: []
aliases:
  - "Karpathy LLM Wiki"
  - "LLM Wiki Method"
tags:
  - methodology-graph
  - source
---

# Source - LLM Wiki Method

> [!note] Governance source (not a vault file)
> Unlike the other three source notes, this one does **not** correspond to a file in `sources/`. It records the **Karpathy "LLM wiki" method** as described in the build request, which serves as the **governance philosophy** for this methodology graph. Because it summarises a method description rather than restating a primary research artefact, its `evidence_strength` is `synthesis` and `confidence` is `medium`.

One-line summary: the LLM-wiki method treats raw sources as immutable inputs and builds a **persistent, compounding, interlinked markdown layer** in which every synthesis is filed back into a canonical, source-grounded, YAML-governed node — the operating discipline behind this entire graph.

## The method (faithful to the build request §A)

The Karpathy LLM-wiki approach is captured in four governing rules:

1. **Raw sources are immutable.** Never edit `sources/*` or restate them as fact without attribution. The four source notes — [[Source - Literature Review]], [[Source - Methodology Idea]], [[Source - Methodology Synthesis Prompt]] and this note — are the only sanctioned factual basis; everything else must trace back to them.
2. **The wiki is a persistent, compounding markdown layer.** Each node is canonical and reusable, so knowledge accumulates over time rather than being re-derived in transient chats.
3. **Every synthesis is filed back** into a node, not left in conversation. A new framing or conclusion becomes a durable page, not an ephemeral answer.
4. **Every canonical page is interlinked, source-grounded, and governed by YAML front matter.** Wikilinks make the graph navigable; YAML carries evidence strength, confidence, maturity and relationships; citations keep every claim accountable.

## Role in this methodology

This method **governs how the methodology graph is authored and maintained**. It is the rationale behind the schema and the maintenance rules:

- The [[Methodology Graph Schema]] operationalises rule 4 — the required YAML fields, the `node_type` vocabulary, the evidence-tagging scheme (`source_grounded` / `synthesis` / `inference` / `unconfirmed`) and the `METH-<CAT>-<NNN>` ID convention.
- The [[Graph Maintenance Rules]] operationalise rules 1-3 — keeping sources immutable, filing syntheses back, interlinking, and the procedure to **promote an `unconfirmed` item to `source_grounded`** once a fact is confirmed.
- The [[Methodology Graph - Meta Node]] is the top hub the method's "interlink and link-up" principle requires every node to reach.
- The [[Source Traceability Register]] enforces rule 1's "with attribution" requirement by mapping each source to the nodes that cite it.

> [!note] Why this is `synthesis`, not `source_grounded`
> This note describes a *method/philosophy* conveyed in the build request rather than a primary research source with verifiable numbers or DOIs. It is therefore tagged `synthesis` with `confidence: medium`; the substantive scientific claims in the graph rest on the three file-backed sources instead.

## Links & relationships
- **Feeds (governs):** [[Methodology Graph - Meta Node]], [[Graph Maintenance Rules]], [[Methodology Graph Schema]]
- **Related:** [[Source Traceability Register]], [[Source - Literature Review]], [[Source - Methodology Idea]], [[Source - Methodology Synthesis Prompt]]
