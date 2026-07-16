---
id: METH-META-003
title: "log"
node_type: meta
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
  - "Build brief §A (Karpathy LLM-wiki rules), §C, §D"
evidence_strength: source_grounded
confidence: high
maturity: candidate_method
owner_role: "[[PI Role]]"
stakeholders: []
upstream_nodes:
  - "[[Methodology Graph - Meta Node]]"
downstream_nodes: []
related_nodes:
  - "[[Graph Maintenance Rules]]"
  - "[[Methodology Graph Schema]]"
key_terms: []
risks: []
open_questions: []
validation_needs: []
aliases:
  - "Changelog"
tags:
  - methodology-graph
  - meta
---

# log

Append-only changelog for the methodology knowledge graph. Newest entries go on top; **never edit or delete past entries** — corrections are added as new entries (per [[Graph Maintenance Rules]]). Each entry records the date, what changed, and the key decisions made. Up to the [[Methodology Graph - Meta Node]].

> [!note] Convention
> Append a new dated entry whenever nodes are added, updated, or promoted (e.g. `unconfirmed → source_grounded`). Bump the affected node's `version` and `updated` fields at the same time, as specified in [[Methodology Graph Schema]].

## 2026-06-19 — Verification & QA pass

- **Multi-agent authoring + adversarial audit:** the 87 graph nodes plus the `llm_wiki.md` root were authored by 14 parallel agents from a single build brief, then checked by 3 independent auditors. Result: **0 high / 0 medium issues, 0 fabrications**; auditors re-verified DOIs, the Fig.6 gap matrix (18/10/7/3 · 15/9/6/2 · 7/4/3/GAP), the Claims-table strengths and contributor names against the immutable PDF.
- **Deterministic link check:** all 90 unique `[[wikilink]]` targets resolve to existing notes (the only flags were two schema-template placeholders inside a code fence — not real links — and one case-variant alias, since normalised). Zero broken links.
- **Corrections applied against the immutable sources:** Bousbih 2018 DOI `rs10101953 → rs10121953` (matches `literature_review.pdf` p.6) in [[Source - Literature Review]], [[Source Traceability Register]] and [[Sentinel 1 and Sentinel 2 Integration]]; removed an `index` self-link; added [[Source - Literature Review]] to [[Uncertainty Chain]] `source_refs` (it cites Report B); added the "scales to extensive agriculture" opportunity to [[Methodology SWOT Matrix]]; dropped an unsourced "C-band" detail from [[Sentinel 1]].
- **Scaffolding removed:** the temporary `99_governance/_BUILD_BRIEF.md` build contract was deleted after the build.
- **Smart Connections caveat:** embeddings were not refreshed — the SC MCP server is read-only over `.smart-env` and currently holds only the pre-existing note. Open the vault in Obsidian once so the Smart Connections plugin re-indexes the new notes; semantic retrieval (and SC MCP search) will then surface the graph.

## 2026-06-19 — Initial graph creation

- Created the methodology knowledge graph as a Karpathy **LLM-wiki** layer over the proposal sources (see [[Source - LLM Wiki Method]]). All four source notes registered: [[Source - Literature Review]], [[Source - Methodology Idea]], [[Source - Methodology Synthesis Prompt]], [[Source - LLM Wiki Method]].
- Adopted the YAML schema, `node_type` controlled vocabulary, evidence-tagging rules, and the `METH-<CAT>-<NNN>` ID scheme documented in [[Methodology Graph Schema]].
- Established the governance triad: [[Methodology Graph Schema]], [[Graph Maintenance Rules]], [[Source Traceability Register]], with [[Methodology Graph Dashboard]] for live monitoring.

### Key decisions recorded

- **Sub-pixel dedup:** [[Sub Pixel Problem]] is the single canonical node, living in `04_methodological_routes/` and doubling as the glossary entry (carries a Definition callout and aliases). No duplicate is created in `09_terminology/`; the Terminology MOC links to it.
- **Two routes, one shared decision engine:** the methodology is framed as [[Route A - Direct Probabilistic Fusion]] and [[Route B - Homogeneous Patch Proxy]], both feeding the shared [[AquaCrop Decision Interface]] and [[Uncertainty Chain]] (synthesis framing from [[Source - Methodology Synthesis Prompt]] §10).
- **Partners flagged unconfirmed:** **ELTE** is absent from all primary sources ([[ELTE Role]]); **AgroVIR** appears only as "AgroVIR-like partners" ([[AgroVIR Validation Partner Role]]). Both carry `evidence_strength: unconfirmed` and `confidence: low`. See [[Partner Roles Overview]].
- **Other unconfirmed items** recorded in [[Ten Research Questions]]: first crop = tomato (tentative), PlanetScope access (RQ8), TRL target (RQ10), validation protocol and decision objective.
- **Wiki root:** `llm_wiki.md` (vault root) set as the wiki landing page, linking to [[Methodology Graph - Meta Node]], [[index]], and [[Methodology Graph Dashboard]].
