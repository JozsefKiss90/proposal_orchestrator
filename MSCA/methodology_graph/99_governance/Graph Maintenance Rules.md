---
id: METH-GOV-002
title: "Graph Maintenance Rules"
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
  - "Build brief §A (Karpathy LLM-wiki rules 1-4), §C.3, §F.4 (anti-fabrication checklist)"
evidence_strength: synthesis
confidence: high
maturity: candidate_method
owner_role: "[[PI Role]]"
stakeholders: []
upstream_nodes:
  - "[[Methodology Graph - Meta Node]]"
downstream_nodes: []
related_nodes:
  - "[[Methodology Graph Schema]]"
  - "[[Source - LLM Wiki Method]]"
  - "[[log]]"
key_terms: []
risks: []
open_questions: []
validation_needs: []
aliases:
  - "Maintenance Rules"
  - "Wiki Rules"
tags:
  - methodology-graph
  - governance
---

# Graph Maintenance Rules

How to keep the methodology knowledge graph healthy, consistent and source-grounded over time, under the Karpathy LLM-wiki method ([[Source - LLM Wiki Method]]). For the field-level schema this enforces, see [[Methodology Graph Schema]]; all changes are recorded in [[log]].

## 1. The Karpathy LLM-wiki principles

1. **Raw sources are immutable.** Never edit `sources/*` or restate them as fact without attribution. The source notes ([[Source - Literature Review]], [[Source - Methodology Idea]], [[Source - Methodology Synthesis Prompt]], [[Source - LLM Wiki Method]]) are the only allowed factual basis.
2. **The wiki is a persistent, compounding markdown layer.** Each node is canonical and reusable; knowledge accumulates rather than being re-derived in chat.
3. **Every synthesis is filed back** into a node (not left in conversation).
4. **Every canonical page is interlinked, source-grounded, and governed by YAML front matter.**

## 2. Adding a new node

1. Assign a unique `METH-<CAT>-<NNN>` ID (see [[Methodology Graph Schema]] §4) and place the file in the correct category folder.
2. Write full YAML front matter with all required fields; set `created`/`updated`, choose **one** `evidence_strength`, set `confidence` and `maturity`.
3. Ground every claim in a source and cite it in `evidence_basis`; populate `source_refs` with ≥1 source note.
4. Link **up** to the category hub and/or [[Methodology Graph - Meta Node]]; weave 4–8 outgoing wikilinks into prose (≥3 for terminology). Add the node to [[index]].
5. Append a dated entry to [[log]].

## 3. Updating an existing node

- Edit the body, then **bump `version`** (e.g. 0.1 → 0.2) and set `updated` to the edit date.
- Keep claims traceable; do not silently introduce unsourced statements.
- Record the change in [[log]] (append-only; corrections are new entries, never deletions).

## 4. Promoting evidence strength (`unconfirmed → source_grounded`)

When a currently unconfirmed fact is confirmed by an admissible source:

1. Update `evidence_strength` (e.g. `unconfirmed → source_grounded`, or `inference → source_grounded`).
2. Raise `confidence` accordingly and add the confirming anchor to `evidence_basis`.
3. Remove or down-grade the `> [!warning]` callout and resolve the matching item in `open_questions` / [[Ten Research Questions]].
4. Log the promotion in [[log]] with the confirming source.

This path applies directly to the §B.6 unconfirmed items: the first crop (tomato), partner identities ([[ELTE Role]], [[AgroVIR Validation Partner Role]]), [[PlanetScope Usage Gap]] access, and the TRL target ([[Web MVP and User Interface Layer]]).

## 5. Anti-fabrication checklist (apply on every write)

- [ ] Every factual claim traces to a source in the digest (cited in `evidence_basis`).
- [ ] Inference/synthesis explicitly labelled; unconfirmed items flagged with `confidence: low` and a warning callout.
- [ ] No invented citations, partner commitments, datasets, crops, numbers, or TRLs.
- [ ] All wikilinks use exact registry basenames; ≥1 `source_refs`; links up to a hub.

## 6. Review cadence

- Review the graph whenever a source changes, a research question is answered, or a project decision is taken.
- Use [[Methodology Graph Dashboard]] to surface weak spots: nodes with `evidence_strength = unconfirmed`, `maturity = project_decision_needed`, and outstanding `open_questions`.
- Resolve broken or non-registry wikilinks promptly to preserve graph connectivity.

## Source grounding

These rules are a **synthesis** of the Karpathy LLM-wiki principles ([[Source - LLM Wiki Method]]) and the build-brief governance and anti-fabrication requirements, paired with the [[Methodology Graph Schema]].
