---
id: METH-PART-001
title: "Partner Roles Overview"
node_type: partner
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
  - "prompt.txt §8 (AgroVIR-like partners assist, not own/operate)"
  - "methodology_idea.txt (PI design narrative authorship; the 'colleague' sub-pixel concern)"
  - "BUILD_BRIEF §B.6 (partner identities unconfirmed)"
evidence_strength: unconfirmed
confidence: low
maturity: project_decision_needed
owner_role: "[[PI Role]]"
stakeholders:
  - "[[PI Role]]"
  - "[[Methodology Contributor Role]]"
  - "[[AgroVIR Validation Partner Role]]"
upstream_nodes:
  - "[[Methodology Graph - Meta Node]]"
downstream_nodes:
  - "[[ELTE Role]]"
  - "[[PI Role]]"
  - "[[Methodology Contributor Role]]"
  - "[[AgroVIR Validation Partner Role]]"
  - "[[Unconfirmed Partner Placeholders]]"
related_nodes:
  - "[[ELTE Role]]"
  - "[[PI Role]]"
  - "[[Methodology Contributor Role]]"
  - "[[AgroVIR Validation Partner Role]]"
  - "[[Unconfirmed Partner Placeholders]]"
  - "[[Web MVP and User Interface Layer]]"
  - "[[Validation and Field Trial Layer]]"
key_terms: []
risks: []
open_questions:
  - "Who is the lead institution / named PI?"
  - "Is ELTE involved, and in what role?"
  - "Is there a committed AgroVIR (or AgroVIR-like) validation partnership?"
  - "Which validation farms, EO data providers and meteo providers are confirmed?"
validation_needs:
  - "Confirm each partner identity and role before proposal submission."
aliases:
  - "Partner Roles"
  - "Consortium Overview"
tags:
  - methodology-graph
  - partner
---

# Partner Roles Overview

A consolidated, caution-first map of the people and organisations implied by this methodology proposal — most of which are **not yet confirmed in any primary source**.

> [!warning] Partner identities are largely unconfirmed
> Across the three primary sources ([[Source - Methodology Idea]], [[Source - Methodology Synthesis Prompt]], [[Source - Literature Review]]), **no committed partner is named**. The only consortium-shaped statement is that an MSCA-style proposal could be supported by *"AgroVIR-like partners helping with feedback, farmer access, testing and validation rather than owning or operating the tool"* (prompt.txt §8). The PI and the methodology contributor are **inferred from authorship**, not named. **ELTE does not appear in any source.** Treat everything on this page as a scaffold to be confirmed, not as fact (`evidence_strength: unconfirmed`, `confidence: low`).

## What this page is

This overview indexes the partner/role nodes in the graph and records, for each, exactly how strongly (or weakly) it is grounded in the sources. It exists so that proposal authors can see at a glance which roles are evidenced, which are inferred, and which are pure placeholders awaiting confirmation. It is a `project_decision_needed` node: the consortium composition is an open decision, not a settled fact.

## Role inventory

| Role node | Grounding | Evidence strength | What the source actually says |
|---|---|---|---|
| [[PI Role]] | Inference from authorship | inference | Author of the design narrative; developer of the uncertainty-aware calibration method (doi:10.1016/j.envsoft.2022.105556). Name not stated. |
| [[Methodology Contributor Role]] | Inference | inference | The "colleague" who raised the sub-pixel concern and framed the two routes (prompt.txt §2–§4). Whether this is the same person as the PI is open. |
| [[AgroVIR Validation Partner Role]] | Single example mention | unconfirmed | Appears only as "AgroVIR-like partners" assisting with feedback/farmer access/testing/validation — *not* owning/operating (prompt.txt §8). No committed partnership stated. |
| [[ELTE Role]] | **Absent from sources** | unconfirmed | Not mentioned anywhere. Role to be confirmed; do not invent. |
| [[Unconfirmed Partner Placeholders]] | Placeholder set | unconfirmed | Lead institution/PI name, ELTE, AgroVIR, validation farms, EO data providers, meteo providers — all to be confirmed. |

## Role logic (synthesis)

*(Proposal synthesis — combines the source statements into a coherent role picture; the structure is the analyst's, the facts are the sources'.)* The methodology divides cleanly into who **designs/leads the science** (the [[PI Role]] and [[Methodology Contributor Role]]) and who **enables real-world testing** (an [[AgroVIR Validation Partner Role]]-type partner, plus validation farms and data providers). The brief's framing of the [[Web MVP and User Interface Layer]] as a *standalone research demonstrator* — with partners helping rather than operating — is the load-bearing constraint on the partner model: an MSCA-style proposal keeps ownership of the demonstrator with the research host while partners feed in feedback, farmer access and [[Validation and Field Trial Layer]] support.

## Source grounding

- PI / contributor inference: [[Source - Methodology Idea]] (first-person design narrative; "a method I developed … doi:10.1016/j.envsoft.2022.105556"; references to "your colleague").
- AgroVIR-like partner role: [[Source - Methodology Synthesis Prompt]] §8.
- Unconfirmed-status discipline: BUILD_BRIEF §B.6.

## Links & relationships

This page sits under [[Methodology Graph - Meta Node]] and fans out to the five role nodes above. It connects to the [[Web MVP and User Interface Layer]] (what partners help test) and the [[Validation and Field Trial Layer]] (where partner-enabled field access matters).

## Open questions

All consortium identities are open. See [[Unconfirmed Partner Placeholders]] for the working list and [[Ten Research Questions]] for the broader open-decisions context.
