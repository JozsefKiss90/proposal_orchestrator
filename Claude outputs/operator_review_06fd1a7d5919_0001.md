# Operator review — the 29 ESR observations of msca-dn-2025-original

Generated: 2026-11-13T16:11:31.450004+00:00  
Review state: **agent_drafted_pending_operator_review**  
Drafted by: Jozsef Kiss (operator). All 29 classifications read and confirmed by the operator.  
Ticket: R02 of `plans/pe08_review_and_pe09_handoff_tickets.md`

Every recommendation, uncertainty and proposed revision in this report is agent-drafted and provisional. None of it is an operator decision, and nothing here records one.

This report reads the committed PE-08 comparison. It changes no disposition, writes no revision and calls no assessor. Every reference below was resolved again, against the artifact the comparison names, before this file was written.

Advisory to a human, never run-blocking (`harness/HARNESS.md`): this report evaluates no gate and blocks no phase. Its inputs carry `advisory: true` and `blocking: false`, and so do the review notes it rests on.

## 1. Inputs

| Role | Path | sha256 (or content hash) | Note |
|---|---|---|---|
| comparison report | `comparisons/comparison_f5c99a91adc9_0002.json` | `06fd1a7d59193ab6…` | the PE-08 output this review reads; not modified |
| ESR record | `docs/tier4_orchestration_state/msca_dn/esr/msca-dn-2025-original-esr.json` | `5c9b9c8e9f89f501…` | the historical evaluation summary, verbatim; the observation id set is its own |
| dispositions | `private/msca_dn_original/esr_work/dispositions_second.json` | `ed3237567fcc8aa9…` | the declared half of the comparison, drafted by Claude and under review here |
| frozen blind baseline | `baseline/blind_baseline_f5c99a91adc9.json` | `f5c99a91adc938f7…` | assessor eu.anthropic.claude-sonnet-4-6@bedrock-converse-eu-north-1@2026-11-13; no new assessor call was made |
| candidate | `reports/candidates/MSCA-DN-2025_part_b_as_submitted@0b168e1c40f6a093` | sha256:96a09b983831249ac17a80cde59714c887e4c9ca4d5c77be86d0fb1167700329 | the submitted document, which every quote below must match |
| fidelity register | `private/msca_dn_original/fidelity_register_as_submitted.json` | `bc7c237b2e0697dd…` | the register this comparison binds; the derived half is measured and the declared half is the operator's (ticket R01). Another revision's register, where one exists, is not an input of this report |
| integrity audit | `audit/first/integrity_96a09b983831_0001.json` | `fa24f1e140bfa254…` | over candidate sha256:96a09b983831 |
| review notes | `private/msca_dn_original/esr_work/notes_second.json` | `6b50ed4088fec603…` | the declared half of this report |

Each hash above was recomputed from the file on disk. A mismatch refuses the report. The assessor pin is `eu.anthropic.claude-sonnet-4-6@bedrock-converse-eu-north-1@2026-11-13`; no assessor ran for this review.

## 2. Counts

Of the 16 rows the comparison calls `independently_detected`, 11 are strengths the blind lane praised as the evaluators did and 5 are criticisms it caught. The two are counted apart below.

The ESR records **29 observations**: **15 criticisms** (8 shortcomings, 7 minor shortcomings) and **14 strengths**.

### Criticisms

| Disposition | Shortcomings | Minor | All criticisms | What it means here |
|---|---|---|---|---|
| `independently_detected` | 2 | 3 | 5 | a blind or audit finding names the same point |
| `partially_observable` | 0 | 0 | 0 | part of the point was found, or the copy preserves part of the evidence |
| `not_assessable_from_this_copy` | 0 | 0 | 0 | sanitisation removed the evidence; never counted as a failure |
| `not_detected_despite_sufficient_preserved_evidence` | 6 | 4 | 10 | the evidence is preserved and no finding names it |
| `addressed` | 0 | 0 | 0 | the assessed revision no longer exhibits the point |

### Strengths

| Disposition | Count |
|---|---|
| `independently_detected` | 11 |
| `not_detected_despite_sufficient_preserved_evidence` | 3 |

**0** of the 14 strengths carry a blind finding that contests the praised point.

### Lane attribution

These buckets are exclusive: a row both lanes found is counted once, under `both lanes`. The comparison's own `summary.detection.by_lane` counts membership instead, so its integrity-audit figure includes that row.

| Lane | Criticisms | Strengths |
|---|---|---|
| blind lane only | 5 | 11 |
| integrity audit only | 0 | 0 |
| both lanes | 0 | 0 |
| neither lane | 10 | 3 |

Criterion scores are compared in the comparison artifact and are not re-interpreted here. No deduction is attributed to any individual criticism.

## 3. Decisions required

13 of 29 rows need an operator decision. The full question is repeated in each row below, and alone in the companion decisions file.

| # | Observation | Agreement | Recommendation | Decision |
|---|---|---|---|---|
| 1 | `ESR-E-S02` | not_applicable | retain | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| 2 | `ESR-E-03` | not_applicable | retain | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| 3 | `ESR-E-04` | not_applicable | retain | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| 4 | `ESR-E-05` | not_applicable | retain | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| 5 | `ESR-E-07` | not_applicable | retain | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| 6 | `ESR-E-08` | not_applicable | retain | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| 7 | `ESR-E-09` | not_applicable | retain | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| 8 | `ESR-I-01` | not_applicable | retain | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| 9 | `ESR-Q-01` | not_applicable | retain | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| 10 | `ESR-Q-02` | not_applicable | retain | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| 11 | `ESR-Q-03` | not_applicable | retain | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| 12 | `ESR-Q-S03` | not_applicable | retain | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| 13 | `ESR-Q-S04` | not_applicable | retain | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |

## 4. The rows at a glance

`Refs` is how many references the row rests on; each one was resolved against the artifact it names, or this report would not have been written. The ESR closes each group of related points with one severity sentence, so rows in one cluster share a severity and none is invented per row.

| Observation | Criterion | Aspect | Kind | ESR cluster | Disposition | Lane | Refs | Agreement | Decision? |
|---|---|---|---|---|---|---|---|---|---|
| `ESR-E-S01` | excellence | exc-obj | strength | — | independently_detected | blind lane only | 1 | agreed | no |
| `ESR-E-S02` | excellence | exc-method | strength | — | not_detected_despite_sufficient_preserved_evidence | neither lane | 2 | not_applicable | yes |
| `ESR-E-01` | excellence | exc-method | shortcoming | ESR-C1 (shortcoming, 5 observations) | independently_detected | blind lane only | 2 | agreed | no |
| `ESR-E-02` | excellence | exc-method | shortcoming | ESR-C1 (shortcoming, 5 observations) | independently_detected | blind lane only | 2 | agreed | no |
| `ESR-E-03` | excellence | exc-method | shortcoming | ESR-C1 (shortcoming, 5 observations) | not_detected_despite_sufficient_preserved_evidence | neither lane | 2 | not_applicable | yes |
| `ESR-E-04` | excellence | exc-method | shortcoming | ESR-C1 (shortcoming, 5 observations) | not_detected_despite_sufficient_preserved_evidence | neither lane | 2 | not_applicable | yes |
| `ESR-E-05` | excellence | exc-method | shortcoming | ESR-C1 (shortcoming, 5 observations) | not_detected_despite_sufficient_preserved_evidence | neither lane | 2 | not_applicable | yes |
| `ESR-E-06` | excellence | exc-method | minor_shortcoming | ESR-C2 (minor_shortcoming) | independently_detected | blind lane only | 2 | agreed | no |
| `ESR-E-S03` | excellence | exc-method | strength | — | independently_detected | blind lane only | 1 | agreed | no |
| `ESR-E-S04` | excellence | exc-training | strength | — | independently_detected | blind lane only | 1 | agreed | no |
| `ESR-E-07` | excellence | exc-training | minor_shortcoming | ESR-C3 (minor_shortcoming, 2 observations) | not_detected_despite_sufficient_preserved_evidence | neither lane | 2 | not_applicable | yes |
| `ESR-E-08` | excellence | exc-training | minor_shortcoming | ESR-C3 (minor_shortcoming, 2 observations) | not_detected_despite_sufficient_preserved_evidence | neither lane | 2 | not_applicable | yes |
| `ESR-E-S05` | excellence | exc-supervision | strength | — | independently_detected | blind lane only | 1 | agreed | no |
| `ESR-E-09` | excellence | exc-supervision | minor_shortcoming | ESR-C4 (minor_shortcoming) | not_detected_despite_sufficient_preserved_evidence | neither lane | 2 | not_applicable | yes |
| `ESR-I-S01` | impact | imp-structuring | strength | — | independently_detected | blind lane only | 1 | agreed | no |
| `ESR-I-S02` | impact | imp-structuring | strength | — | independently_detected | blind lane only | 1 | agreed | no |
| `ESR-I-S03` | impact | imp-career | strength | — | independently_detected | blind lane only | 1 | agreed | no |
| `ESR-I-S04` | impact | imp-dissemination | strength | — | independently_detected | blind lane only | 1 | agreed | no |
| `ESR-I-01` | impact | imp-dissemination | minor_shortcoming | ESR-C5 (minor_shortcoming) | not_detected_despite_sufficient_preserved_evidence | neither lane | 2 | not_applicable | yes |
| `ESR-I-S05` | impact | imp-magnitude | strength | — | independently_detected | blind lane only | 1 | agreed | no |
| `ESR-I-02` | impact | imp-magnitude | minor_shortcoming | ESR-C6 (minor_shortcoming) | independently_detected | blind lane only | 2 | agreed | no |
| `ESR-Q-S01` | implementation | impl-workplan | strength | — | independently_detected | blind lane only | 1 | agreed | no |
| `ESR-Q-01` | implementation | impl-workplan | shortcoming | ESR-C7 (shortcoming, 3 observations) | not_detected_despite_sufficient_preserved_evidence | neither lane | 2 | not_applicable | yes |
| `ESR-Q-02` | implementation | impl-workplan | shortcoming | ESR-C7 (shortcoming, 3 observations) | not_detected_despite_sufficient_preserved_evidence | neither lane | 2 | not_applicable | yes |
| `ESR-Q-03` | implementation | impl-workplan | shortcoming | ESR-C7 (shortcoming, 3 observations) | not_detected_despite_sufficient_preserved_evidence | neither lane | 2 | not_applicable | yes |
| `ESR-Q-04` | implementation | impl-workplan | minor_shortcoming | ESR-C8 (minor_shortcoming) | independently_detected | blind lane only | 2 | agreed | no |
| `ESR-Q-S02` | implementation | impl-participants | strength | — | independently_detected | blind lane only | 1 | agreed | no |
| `ESR-Q-S03` | implementation | impl-participants | strength | — | not_detected_despite_sufficient_preserved_evidence | neither lane | 2 | not_applicable | yes |
| `ESR-Q-S04` | implementation | impl-participants | strength | — | not_detected_despite_sufficient_preserved_evidence | neither lane | 2 | not_applicable | yes |

## 5. The two groups the ticket asks to highlight

### The alleged misses (13)

A miss is counted against the lane only where the copy preserves the evidence. The preservation of that evidence is a declaration, not a measurement, which is why each row names the status it rests on.

| Observation | ESR complains of | Preservation status | Agreement | Decision |
|---|---|---|---|---|
| `ESR-E-S02` | not_applicable | Assumed | not_applicable | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| `ESR-E-03` | both | Assumed | not_applicable | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| `ESR-E-04` | absent_detail | Assumed | not_applicable | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| `ESR-E-05` | absent_detail | Assumed | not_applicable | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| `ESR-E-07` | inadequately_explained | Assumed | not_applicable | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| `ESR-E-08` | absent_detail | Assumed | not_applicable | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| `ESR-E-09` | inadequately_explained | Assumed | not_applicable | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| `ESR-I-01` | inadequately_explained | Assumed | not_applicable | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| `ESR-Q-01` | both | Assumed | not_applicable | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| `ESR-Q-02` | absent_detail | Assumed | not_applicable | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| `ESR-Q-03` | other | Assumed | not_applicable | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| `ESR-Q-S03` | not_applicable | Assumed | not_applicable | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |
| `ESR-Q-S04` | not_applicable | Assumed | not_applicable | Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency. |

### The contested strengths (0)

The evaluators praised the point and the blind lane faulted it. Either the blind lane is right and the evaluators were generous, or the evidence that earned the praise did not survive sanitisation. The register says which is possible; only the original says which is true.

| Observation | Disposition | Agreement | Decision |
|---|---|---|---|

## 6. The observations

### ESR-E-S01 — excellence / exc-obj

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 1.1

**ESR text (verbatim):**

> The proposal presents clear objectives to develop AI-technologies for cardiovascular healthcare, with concrete measures that make them overall verifiable and achievable within the project's timeframe. The individual projects of the recruited researchers are appropriately articulated and convincingly integrated to support and strengthen the coherent outcomes of the research programme. The project goes beyond the state of the art in cardiovascular care and it is ambitious.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Operator reading: the cited blind finding(s) make the same point as the ESR observation. Findings: [strength sample 2 index 0] "Objectives O1–O4 and CO are clearly articulated with specific, measurable KPIs and directly mapped to EU policy drivers (EU AI Act, EHDS, MDR/IVDR), demonstrating strong pertinence and ambition beyond the state of the art"

**Findings, as resolved:**

- blind lane · criterion_strength · excellence sample 2 #0
  > Objectives O1–O4 and CO are clearly articulated with specific, measurable KPIs and directly mapped to EU policy drivers (EU AI Act, EHDS, MDR/IVDR), demonstrating strong pertinence and ambition beyond the state of the art

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 1 of 1 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** The operator read the cited finding against the ESR observation and judged that they make the same point.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-E-S02 — excellence / exc-method

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 1.2

**ESR text (verbatim):**

> Overall, the methodology is clearly described, including the underlying concepts and models are mostly detailed. Several aspects of interdisciplinary approaches are coherent, and well-integrated to carry out the objectives of the proposal.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. No blind finding makes this point. The failure mode is left undetermined, and the quote was chosen by word overlap with the ESR sentence; its sufficiency was not separately checked.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `excellence_section` / `1.2`
  > Overall methodology We will adopt a highly interdisciplinary and strongly collaborative approach that prioritizes

**Fidelity register entries the row rests on:**

- `derived/sub_sections/1.2` = {"sub_section_id": "1.2", "section_id": "excellence_section", "declared_pages": [13, 15], "derived_pages": [13, 15], "heading": "1.2. Soundness of the proposed methodology", "title": "Soundness of the proposed methodology", "title_source": "candidate heading", "paragraphs": 28, "table_rows": 0, "characters": 8672, "claims": 15}

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 1 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Inferred)
- **Basis:** No blind finding makes this point, so there is no finding to compare. The operator read the candidate findings and confirmed the row as a miss.
- **Recommendation:** `retain`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency.

---

### ESR-E-01 — excellence / exc-method

**Kind:** shortcoming · **ESR severity cluster:** ESR-C1 (shortcoming, 5 observations) · **Proposal location:** 1.2

**ESR text (verbatim):**

> However, AI/ML plans- specifically conceptual paradigms, methods, and validation metrics, as well as critical security aspects for handling clinical data with AI are insufficiently detailed.
>
> Together, these constitute a shortcoming.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. Matched finding (score 8.6): "DC4 is recruited at TRDF (a technology-transfer entity, not a university), yet the PhD-awarding mechanism via Technion is only briefly noted; the pathway to degree conferral and doctoral-school enrolment is insufficiently detailed compared with other DCs" The quoted passage was chosen by word overlap and not separately checked.

**Findings, as resolved:**

- blind lane · criterion_shortcoming · excellence sample 2 #3
  > DC4 is recruited at TRDF (a technology-transfer entity, not a university), yet the PhD-awarding mechanism via Technion is only briefly noted; the pathway to degree conferral and doctoral-school enrolment is insufficiently detailed compared with other DCs

**Candidate passages (quote verified in the named sub-section):**

- `excellence_section` / `1.1`
  > It connects DC2-3-4-6-8 via WP1’s causal and XAI methods and WP3’s HITL paradigms with

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** The operator read the cited finding against the ESR observation and judged that they make the same point.
- **The ESR complains of:** `inadequately_explained`
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-E-02 — excellence / exc-method

**Kind:** shortcoming · **ESR severity cluster:** ESR-C1 (shortcoming, 5 observations) · **Proposal location:** 1.2

**ESR text (verbatim):**

> However, AI/ML plans- specifically conceptual paradigms, methods, and validation metrics, as well as critical security aspects for handling clinical data with AI are insufficiently detailed.
>
> Together, these constitute a shortcoming.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. Matched finding (score 8.6): "DC4 is recruited at TRDF (a technology-transfer entity, not a university), yet the PhD-awarding mechanism via Technion is only briefly noted; the pathway to degree conferral and doctoral-school enrolment is insufficiently detailed compared with other DCs" The quoted passage was chosen by word overlap and not separately checked.

**Findings, as resolved:**

- blind lane · criterion_shortcoming · excellence sample 2 #3
  > DC4 is recruited at TRDF (a technology-transfer entity, not a university), yet the PhD-awarding mechanism via Technion is only briefly noted; the pathway to degree conferral and doctoral-school enrolment is insufficiently detailed compared with other DCs

**Candidate passages (quote verified in the named sub-section):**

- `excellence_section` / `1.1`
  > It connects DC2-3-4-6-8 via WP1’s causal and XAI methods and WP3’s HITL paradigms with

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** The operator read the cited finding against the ESR observation and judged that they make the same point.
- **The ESR complains of:** `both`
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-E-03 — excellence / exc-method

**Kind:** shortcoming · **ESR severity cluster:** ESR-C1 (shortcoming, 5 observations) · **Proposal location:** 1.2, 1.1, 3.1

**ESR text (verbatim):**

> It is also not fully clear how some of the chosen methods will deliver key objectives: cardiovascular AI models are evaluated only retrospectively with limited plans for prospective validation;
>
> Together, these constitute a shortcoming.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. No blind finding makes this point. The failure mode is left undetermined, and the quote was chosen by word overlap with the ESR sentence; its sufficiency was not separately checked.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `excellence_section` / `1.1`
  > Systematic reviews confirm that adoption is slowed by fragmented data environments, limited explainability and

**Fidelity register entries the row rests on:**

- `derived/sub_sections/1.1` = {"sub_section_id": "1.1", "section_id": "excellence_section", "declared_pages": [5, 13], "derived_pages": [5, 13], "heading": "1.1. Quality and pertinence of the project’s research and innovation objectives", "title": "Quality and pertinence of the project’s research and innovation objectives", "title_source": "candidate heading", "paragraphs": 61, "table_rows": 0, "characters": 29049, "claims": 35}

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 1 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Inferred)
- **Basis:** No blind finding makes this point, so there is no finding to compare. The operator read the candidate findings and confirmed the row as a miss.
- **The ESR complains of:** `both`
- **Recommendation:** `retain`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency.

---

### ESR-E-04 — excellence / exc-method

**Kind:** shortcoming · **ESR severity cluster:** ESR-C1 (shortcoming, 5 observations) · **Proposal location:** 3.1, 1.2

**ESR text (verbatim):**

> the cohort is not sufficient concerning the multihospital, multi-operator design needed to reflect contemporary European TAVI practice to capture the diversity;
>
> Together, these constitute a shortcoming.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. No blind finding makes this point. The failure mode is left undetermined, and the quote was chosen by word overlap with the ESR sentence; its sufficiency was not separately checked.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `excellence_section` / `1.1`
  > TRANSMIT will produce a cohort of specialists who can design, evaluate and implement trustworthy,

**Fidelity register entries the row rests on:**

- `derived/sub_sections/1.1` = {"sub_section_id": "1.1", "section_id": "excellence_section", "declared_pages": [5, 13], "derived_pages": [5, 13], "heading": "1.1. Quality and pertinence of the project’s research and innovation objectives", "title": "Quality and pertinence of the project’s research and innovation objectives", "title_source": "candidate heading", "paragraphs": 61, "table_rows": 0, "characters": 29049, "claims": 35}

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 1 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Inferred)
- **Basis:** No blind finding makes this point, so there is no finding to compare. The operator read the candidate findings and confirmed the row as a miss.
- **The ESR complains of:** `absent_detail`
- **Recommendation:** `retain`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency.

---

### ESR-E-05 — excellence / exc-method

**Kind:** shortcoming · **ESR severity cluster:** ESR-C1 (shortcoming, 5 observations) · **Proposal location:** 1.2, 1.1

**ESR text (verbatim):**

> and the number of contributing clinicians to the database is not well-specified.
>
> Together, these constitute a shortcoming.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. No blind finding makes this point. The failure mode is left undetermined, and the quote was chosen by word overlap with the ESR sentence; its sufficiency was not separately checked.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `excellence_section` / `1.1`
  > The TRANSMIT (TRAnsparent and Safe Medical Intelligence and Trustworthiness) Doctoral Network directly responds to

**Fidelity register entries the row rests on:**

- `derived/sub_sections/1.1` = {"sub_section_id": "1.1", "section_id": "excellence_section", "declared_pages": [5, 13], "derived_pages": [5, 13], "heading": "1.1. Quality and pertinence of the project’s research and innovation objectives", "title": "Quality and pertinence of the project’s research and innovation objectives", "title_source": "candidate heading", "paragraphs": 61, "table_rows": 0, "characters": 29049, "claims": 35}

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 1 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Inferred)
- **Basis:** No blind finding makes this point, so there is no finding to compare. The operator read the candidate findings and confirmed the row as a miss.
- **The ESR complains of:** `absent_detail`
- **Recommendation:** `retain`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency.

---

### ESR-E-06 — excellence / exc-method

**Kind:** minor_shortcoming · **ESR severity cluster:** ESR-C2 (minor_shortcoming) · **Proposal location:** 1.2

**ESR text (verbatim):**

> Gender and other diversity characteristics relevant to this research are mostly appropriately considered in the research methodology as scientific variables (disaggregated data, subgroup calibration, bias mitigation), however, they are not detailed enough regarding their essential role in clinical issues in cardiology.
>
> This is a minor shortcoming.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. Matched finding (score 15.0): "The gender dimension treatment is largely declarative ('sex and gender as scientific variables') without specifying concrete operationalisation steps such as minimum disaggregation thresholds, power calculations for subgroup analyses, or protocols for handling datasets where sex/gender metadata is absent" The quoted passage was chosen by word overlap and not separately checked.

**Findings, as resolved:**

- blind lane · criterion_shortcoming · excellence sample 2 #2
  > The gender dimension treatment is largely declarative ('sex and gender as scientific variables') without specifying concrete operationalisation steps such as minimum disaggregation thresholds, power calculations for subgroup analyses, or protocols for handling datasets where sex/gender metadata is absent

**Candidate passages (quote verified in the named sub-section):**

- `excellence_section` / `1.2`
  > Gender dimension and other diversity aspects In TRANSMIT, sex, gender and other diversity characteristics

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** The operator read the cited finding against the ESR observation and judged that they make the same point.
- **The ESR complains of:** `inadequately_explained`
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-E-S03 — excellence / exc-method

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 1.2

**ESR text (verbatim):**

> Open science practices, such as preprints, and repositories, are included and adequately described in the proposed methodology.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> The blind strength states that open science commitments are appropriately contextualised, with the open-as-possible principle and a FAIR data management plan. That is the ESR's point that open science practices are included and adequately described; the ESR names preprints and repositories, the finding names the principle and the plan. Found in one sample, ranked below the 8.5 triage cut-off, kept on reading.

**Findings, as resolved:**

- blind lane · criterion_strength · excellence sample 2 #6
  > Open science commitments are contextualised appropriately for high-risk medical AI, with the 'as open as possible, as closed as necessary' principle and FAIR data management plan explicitly stated

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 1 of 1 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** The operator read the cited finding against the ESR observation and judged that they make the same point.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-E-S04 — excellence / exc-training

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 1.3

**ESR text (verbatim):**

> In general, a solid training framework with meaningful network-wide events - supporting well-structured scientific and transferable training - is described in the proposal. The training programme effectively integrates intersectoral and transferable skills through training schools, courses, conferences and secondments.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Operator reading: the blind strength at excellence sample 0 index 5 makes the same point as the ESR observation. Finding: "The training programme is well-structured with six explicit training goals (TG1–TG6), a Personal Career Development Plan mechanism, an Individual Training Panel per DC, and a named sequence of seven network-wide events with indicative ECTS"

**Findings, as resolved:**

- blind lane · criterion_strength · excellence sample 0 #5
  > The training programme is well-structured with six explicit training goals (TG1–TG6), a Personal Career Development Plan mechanism, an Individual Training Panel per DC, and a named sequence of seven network-wide events with indicative ECTS

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 1 of 1 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** The operator read the cited finding against the ESR observation and judged that they make the same point.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-E-07 — excellence / exc-training

**Kind:** minor_shortcoming · **ESR severity cluster:** ESR-C3 (minor_shortcoming, 2 observations) · **Proposal location:** 1.3

**ESR text (verbatim):**

> While network-wide training overall complements the local training programmes, there is a slight limitation in clarity and depth in systematic description of complementation of local training.
>
> These constitute a minor shortcoming.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. No blind finding makes this point. The failure mode is left undetermined, and the quote was chosen by word overlap with the ESR sentence; its sufficiency was not separately checked.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `excellence_section` / `1.3`
  > each DC’s Personal Career Development Plan (PCDP) maps how local and network-wide activities, including

**Fidelity register entries the row rests on:**

- `derived/sub_sections/1.3` = {"sub_section_id": "1.3", "section_id": "excellence_section", "declared_pages": [15, 18], "derived_pages": [15, 18], "heading": "1.3. Quality and credibility of the training programme", "title": "Quality and credibility of the training programme", "title_source": "candidate heading", "paragraphs": 34, "table_rows": 8, "characters": 11245, "claims": 3}

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 1 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Inferred)
- **Basis:** No blind finding makes this point, so there is no finding to compare. The operator read the candidate findings and confirmed the row as a miss.
- **The ESR complains of:** `inadequately_explained`
- **Recommendation:** `retain`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency.

---

### ESR-E-08 — excellence / exc-training

**Kind:** minor_shortcoming · **ESR severity cluster:** ESR-C3 (minor_shortcoming, 2 observations) · **Proposal location:** 1.3, 2.2

**ESR text (verbatim):**

> In addition, some details for training are not properly described, for example, the integration of entrepreneurship training lacks clear mechanisms for practical application.
>
> These constitute a minor shortcoming.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. No blind finding makes this point. The failure mode is left undetermined, and the quote was chosen by word overlap with the ESR sentence; its sufficiency was not separately checked.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `excellence_section` / `1.1`
  > Integration into TRANSMIT DC3 operationalises the interoperability and clinical adaptation objectives (O2-4) by translating

**Fidelity register entries the row rests on:**

- `derived/sub_sections/1.1` = {"sub_section_id": "1.1", "section_id": "excellence_section", "declared_pages": [5, 13], "derived_pages": [5, 13], "heading": "1.1. Quality and pertinence of the project’s research and innovation objectives", "title": "Quality and pertinence of the project’s research and innovation objectives", "title_source": "candidate heading", "paragraphs": 61, "table_rows": 0, "characters": 29049, "claims": 35}

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 1 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Inferred)
- **Basis:** No blind finding makes this point, so there is no finding to compare. The operator read the candidate findings and confirmed the row as a miss.
- **The ESR complains of:** `absent_detail`
- **Recommendation:** `retain`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency.

---

### ESR-E-S05 — excellence / exc-supervision

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 1.4

**ESR text (verbatim):**

> The supervisors are experienced and highly qualified in their scientific roles. They demonstrate appropriate international and local experience across all relevant areas and facilitating the adequate and effective completion the individual research projects. The well-structured and multi-layered approach of supervision practices is solid and overall sound. It ensures effective progress monitoring, feedback and support for the fellows; for example, well-defined and reviewed Personal Career Development Plans ensure systematic tracking of training objectives.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Operator reading: the blind strength at excellence sample 0 index 5 makes the same point as the ESR observation. Finding: "The training programme is well-structured with six explicit training goals (TG1–TG6), a Personal Career Development Plan mechanism, an Individual Training Panel per DC, and a named sequence of seven network-wide events with indicative ECTS"

**Findings, as resolved:**

- blind lane · criterion_strength · excellence sample 0 #5
  > The training programme is well-structured with six explicit training goals (TG1–TG6), a Personal Career Development Plan mechanism, an Individual Training Panel per DC, and a named sequence of seven network-wide events with indicative ECTS

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 1 of 1 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** The operator read the cited finding against the ESR observation and judged that they make the same point.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-E-09 — excellence / exc-supervision

**Kind:** minor_shortcoming · **ESR severity cluster:** ESR-C4 (minor_shortcoming) · **Proposal location:** 1.4

**ESR text (verbatim):**

> However, the description remains slightly generic on how the quality of supervisory practices will be measured.
>
> This is minor shortcoming.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. No blind finding makes this point. The failure mode is left undetermined, and the quote was chosen by word overlap with the ESR sentence; its sufficiency was not separately checked.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `excellence_section` / `1.1`
  > Introduction, objectives and overview of the overall research programme Despite rapid advances, the current

**Fidelity register entries the row rests on:**

- `derived/sub_sections/1.1` = {"sub_section_id": "1.1", "section_id": "excellence_section", "declared_pages": [5, 13], "derived_pages": [5, 13], "heading": "1.1. Quality and pertinence of the project’s research and innovation objectives", "title": "Quality and pertinence of the project’s research and innovation objectives", "title_source": "candidate heading", "paragraphs": 61, "table_rows": 0, "characters": 29049, "claims": 35}

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 1 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Inferred)
- **Basis:** No blind finding makes this point, so there is no finding to compare. The operator read the candidate findings and confirmed the row as a miss.
- **The ESR complains of:** `inadequately_explained`
- **Recommendation:** `retain`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency.

---

### ESR-I-S01 — impact / imp-structuring

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 2.1

**ESR text (verbatim):**

> Non-academic sector contribution to doctoral training is well described and compelling; they have a meaningful and tangible role through structured secondments in hospitals, SMEs, and regulatory bodies, ensuring hands-on exposure to clinical workflows, compliance, and innovation. Industry and regulatory partners actively co-supervise doctoral candidates (DCs), participate the Individual Training Panels, and the Supervisory Board, and lead network-wide training sessions.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Operator reading: the cited blind finding(s) make the same point as the ESR observation. Findings: [strength sample 2 index 0] "Comprehensive and coherent structuring of doctoral training across academic, clinical, industrial and regulatory sectors with explicit governance bodies (ITP, Supervisory Board, Innovation and Sustainability Committee)"

**Findings, as resolved:**

- blind lane · criterion_strength · impact sample 2 #0
  > Comprehensive and coherent structuring of doctoral training across academic, clinical, industrial and regulatory sectors with explicit governance bodies (ITP, Supervisory Board, Innovation and Sustainability Committee)

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 1 of 1 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** The operator read the cited finding against the ESR observation and judged that they make the same point.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-I-S02 — impact / imp-structuring

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 2.1

**ESR text (verbatim):**

> Several elements are convincingly sustained after the project; these include e.g. the development of a virtual knowledge hub. The robust strategies and mechanisms described ensure a sustained long-term collaboration, and foster future international and intersectoral research and cooperation.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Operator reading: the cited blind finding(s) make the same point as the ESR observation. Findings: [strength sample 0 index 5] "The European Causal AI Academy as a virtual hub for post-project sustainability, combined with an alumni network and Innovation and Sustainability Committee, provides a plausible long-term impact mechanism beyond project funding."

**Findings, as resolved:**

- blind lane · criterion_strength · impact sample 0 #5
  > The European Causal AI Academy as a virtual hub for post-project sustainability, combined with an alumni network and Innovation and Sustainability Committee, provides a plausible long-term impact mechanism beyond project funding.

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 1 of 1 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** The operator read the cited finding against the ESR observation and judged that they make the same point.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-I-S03 — impact / imp-career

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 2.2

**ESR text (verbatim):**

> The project provides a robust and well-structured framework and environment to equip fellows with both technical and transferable skills, significantly enhancing and ensuring the future employability in both academia and industry. Specifically, the profile of fellows in trustworthy AI for clinical issues is highly relevant for hospitals, industry R&D departments, start-ups and research infrastructures. Transferable skills are integrated in the training, and intersectoral secondments and co-supervision expose fellows to hospitals, SMEs, and regulatory bodies, ensuring practical experience and networking. The measures to enhance the career perspectives of fellows are highly relevant and comprehensive and designed to prepare fellows for multidisciplinary careers.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Operator reading: the blind strength at impact sample 2 index 4 makes the same point as the ESR observation. Finding: "Triple-I exposure embedded structurally for most DCs with secondments in hospitals, SMEs and regulatory bodies, supporting diverse and credible career pathways"

**Findings, as resolved:**

- blind lane · criterion_strength · impact sample 2 #4
  > Triple-I exposure embedded structurally for most DCs with secondments in hospitals, SMEs and regulatory bodies, supporting diverse and credible career pathways

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 1 of 1 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** The operator read the cited finding against the ESR observation and judged that they make the same point.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-I-S04 — impact / imp-dissemination

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 2.3

**ESR text (verbatim):**

> The dissemination, exploitation, and communication measures are comprehensive, and well-structured, with clear objectives and monitoring through measurable indicators. The target groups for these measures are clearly identified. The outline of intellectual property management strategy is mostly appropriately addressed.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Operator reading: the blind strength at impact sample 3 index 6 makes the same point as the ESR observation. Finding: "WP7 with dedicated tasks for communication strategy, knowledge transfer and post-project exploitation, backed by annual DEC reports (D7.1) and R2I Canvas updates (D7.2), provides governance infrastructure for impact monitoring."

**Findings, as resolved:**

- blind lane · criterion_strength · impact sample 3 #6
  > WP7 with dedicated tasks for communication strategy, knowledge transfer and post-project exploitation, backed by annual DEC reports (D7.1) and R2I Canvas updates (D7.2), provides governance infrastructure for impact monitoring.

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 1 of 1 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** The operator read the cited finding against the ESR observation and judged that they make the same point.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-I-01 — impact / imp-dissemination

**Kind:** minor_shortcoming · **ESR severity cluster:** ESR-C5 (minor_shortcoming) · **Proposal location:** 2.3

**ESR text (verbatim):**

> However, suitable strategies to protect industrial and other relevant outcomes are not convincingly elaborated; this is a minor shortcoming.
>
> this is a minor shortcoming.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. No blind finding makes this point. The failure mode is left undetermined, and the quote was chosen by word overlap with the ESR sentence; its sufficiency was not separately checked.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `impact_section` / `2.3`
  > Beneficiaries will protect commercially relevant results through appropriate intellectual-property instruments, while other outputs (e.g.

**Fidelity register entries the row rests on:**

- `derived/sub_sections/2.3` = {"sub_section_id": "2.3", "section_id": "impact_section", "declared_pages": [22, 23], "derived_pages": [22, 23], "heading": "2.3. Suitability and quality of the measures to maximise expected outcomes and impacts, as set out in the dissemination and exploitation plan, including communication activities", "title": "Suitability and quality of the measures to maximise expected outcomes and impacts, as set out in the dissemination and exploitation plan, including communication activities", "title_source": "candidate heading", "paragraphs": 15, "table_rows": 0, "characters": 5242, "claims": 3}

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 1 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Inferred)
- **Basis:** No blind finding makes this point, so there is no finding to compare. The operator read the candidate findings and confirmed the row as a miss.
- **The ESR complains of:** `inadequately_explained`
- **Recommendation:** `retain`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency.

---

### ESR-I-S05 — impact / imp-magnitude

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 2.4

**ESR text (verbatim):**

> The expected scientific impact is highly credible with clear breakthroughs in causal modelling. For example, the integration of regulatory-grade pipelines aligned with regulatory frameworks adds robustness. Indicators, such as cross-site transportability, make the scientific outcomes measurable and realistic. Societal impact is well-justified: effective and safe integration of AI in healthcare and regulatory frameworks will largely affect the quality of the cardiovascular care provided to patients, and is addressing patient benefit, healthcare-system resilience, and policy uptake.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Operator reading: the cited blind finding(s) make the same point as the ESR observation. Findings: [strength sample 1 index 4] "Scientific impact is grounded in three concrete research pillars (causal modelling, resilient explainability, regulatory integration) with named deliverables and milestones providing traceability"

**Findings, as resolved:**

- blind lane · criterion_strength · impact sample 1 #4
  > Scientific impact is grounded in three concrete research pillars (causal modelling, resilient explainability, regulatory integration) with named deliverables and milestones providing traceability

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 1 of 1 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** The operator read the cited finding against the ESR observation and judged that they make the same point.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-I-02 — impact / imp-magnitude

**Kind:** minor_shortcoming · **ESR severity cluster:** ESR-C6 (minor_shortcoming) · **Proposal location:** 2.4

**ESR text (verbatim):**

> Economic and technological impacts, such as validated causal AI and interoperability with European Health Data Space/Fast Healthcare Interoperability Resources (EHDS/FHIR), and human capital development through multi-sector training, are overall valid, especially in a long-term, however, the magnitude in terms of specific measures is insufficiently presented in the proposal.
>
> This is a minor shortcoming.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. Matched finding (score 9.6): "The European Causal AI Academy sustainability mechanism is described only at a high level — concrete commitments from individual institutions to embed modules into their curricula (e.g., named ECTS credits, signed letters of intent) are absent, making long-term sustainability aspirational rather than evidenced." The quoted passage was chosen by word overlap and not separately checked.

**Findings, as resolved:**

- blind lane · criterion_shortcoming · impact sample 3 #2
  > The European Causal AI Academy sustainability mechanism is described only at a high level — concrete commitments from individual institutions to embed modules into their curricula (e.g., named ECTS credits, signed letters of intent) are absent, making long-term sustainability aspirational rather than evidenced.

**Candidate passages (quote verified in the named sub-section):**

- `impact_section` / `2.1`
  > Developing sustainable (=lasting) elements of doctoral programmes after the end of the DN funding

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** The operator read the cited finding against the ESR observation and judged that they make the same point.
- **The ESR complains of:** `absent_detail`
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-Q-S01 — implementation / impl-workplan

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 3.1

**ESR text (verbatim):**

> The work plan is overall of good quality. The work packages (WPs) are clearly aligned with the project objectives, and the allocation of WPs and tasks is coherent. Each WP includes generally well-defined and appropriate deliverables and milestones.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Operator reading: the blind strength at implementation sample 0 index 0 makes the same point as the ESR observation. Finding: "Seven scientifically coherent work packages with clear objectives, well-defined tasks, named lead participants, and explicit DC assignments provide a strong structural backbone."

**Findings, as resolved:**

- blind lane · criterion_strength · implementation sample 0 #0
  > Seven scientifically coherent work packages with clear objectives, well-defined tasks, named lead participants, and explicit DC assignments provide a strong structural backbone.

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 1 of 1 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** The operator read the cited finding against the ESR observation and judged that they make the same point.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-Q-01 — implementation / impl-workplan

**Kind:** shortcoming · **ESR severity cluster:** ESR-C7 (shortcoming, 3 observations) · **Proposal location:** 3.1

**ESR text (verbatim):**

> However, several aspects lack appropriate detail such as the description of dependencies between work packages.
>
> These issues together are a shortcoming.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. No blind finding makes this point. The failure mode is left undetermined, and the quote was chosen by word overlap with the ESR sentence; its sufficiency was not separately checked.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `implementation_section` / `3.1`
  > #§CON-SOR-CS§# #§PRJ-MGT-PM§# Table 3.1 a Description of Work Packages | WP Number:

**Fidelity register entries the row rests on:**

- `derived/sub_sections/3.1` = {"sub_section_id": "3.1", "section_id": "implementation_section", "declared_pages": [24, 32], "derived_pages": [24, 32], "heading": "3.1. Quality and effectiveness of the work plan, assessment of risks and appropriateness of the effort assigned to work packages", "title": "Quality and effectiveness of the work plan, assessment of risks and appropriateness of the effort assigned to work packages", "title_source": "candidate heading", "paragraphs": 33, "table_rows": 113, "characters": 27796, "claims": 8}

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 1 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Inferred)
- **Basis:** No blind finding makes this point, so there is no finding to compare. The operator read the candidate findings and confirmed the row as a miss.
- **The ESR complains of:** `both`
- **Recommendation:** `retain`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency.

---

### ESR-Q-02 — implementation / impl-workplan

**Kind:** shortcoming · **ESR severity cluster:** ESR-C7 (shortcoming, 3 observations) · **Proposal location:** 3.1

**ESR text (verbatim):**

> In addition, the validation strategy for certain deliverables is not fully specified
>
> These issues together are a shortcoming.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. No blind finding makes this point. The failure mode is left undetermined, and the quote was chosen by word overlap with the ESR sentence; its sufficiency was not separately checked.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `implementation_section` / `5`
  > Associated partners participate fully in the SB and related innovation/impact structures, reflecting their role

**Fidelity register entries the row rests on:**

- `derived/sub_sections/5` = {"sub_section_id": "5", "section_id": "implementation_section", "declared_pages": [34, 38], "derived_pages": [34, 38], "heading": "5. Network organisation", "title": "Network organisation", "title_source": "candidate heading", "paragraphs": 53, "table_rows": 0, "characters": 13717, "claims": 5}

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 1 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Inferred)
- **Basis:** No blind finding makes this point, so there is no finding to compare. The operator read the candidate findings and confirmed the row as a miss.
- **The ESR complains of:** `absent_detail`
- **Recommendation:** `retain`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency.

---

### ESR-Q-03 — implementation / impl-workplan

**Kind:** shortcoming · **ESR severity cluster:** ESR-C7 (shortcoming, 3 observations) · **Proposal location:** 3.1

**ESR text (verbatim):**

> and the definitions and timing of some milestones is not well aligned with the overall proposal.
>
> These issues together are a shortcoming.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. No blind finding makes this point. The failure mode is left undetermined, and the quote was chosen by word overlap with the ESR sentence; its sufficiency was not separately checked.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `implementation_section` / `3.1`
  > Monitor deliverables, milestones, risks, and ethics compliance.

**Fidelity register entries the row rests on:**

- `derived/sub_sections/3.1` = {"sub_section_id": "3.1", "section_id": "implementation_section", "declared_pages": [24, 32], "derived_pages": [24, 32], "heading": "3.1. Quality and effectiveness of the work plan, assessment of risks and appropriateness of the effort assigned to work packages", "title": "Quality and effectiveness of the work plan, assessment of risks and appropriateness of the effort assigned to work packages", "title_source": "candidate heading", "paragraphs": 33, "table_rows": 113, "characters": 27796, "claims": 8}

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 1 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Inferred)
- **Basis:** No blind finding makes this point, so there is no finding to compare. The operator read the candidate findings and confirmed the row as a miss.
- **The ESR complains of:** `other`
- **Recommendation:** `retain`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency.

---

### ESR-Q-04 — implementation / impl-workplan

**Kind:** minor_shortcoming · **ESR severity cluster:** ESR-C8 (minor_shortcoming) · **Proposal location:** 3.1

**ESR text (verbatim):**

> Risk management is present and generally credible, with several appropriate mitigation measures. However, certain descriptions of risks remain generic and oversimplified, without measurable thresholds for activation of the mitigation.
>
> This is a minor shortcoming.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. Matched finding (score 9.1): "The risk table rates several medium-likelihood/medium-severity risks (e.g., data-sharing delays, model generalisation failures) as 'low' severity, which appears inconsistent and may understate genuine threats to WP1–4 delivery." The quoted passage was chosen by word overlap and not separately checked.

**Findings, as resolved:**

- blind lane · criterion_shortcoming · implementation sample 0 #3
  > The risk table rates several medium-likelihood/medium-severity risks (e.g., data-sharing delays, model generalisation failures) as 'low' severity, which appears inconsistent and may understate genuine threats to WP1–4 delivery.

**Candidate passages (quote verified in the named sub-section):**

- `implementation_section` / `3.1`
  > | Recruiting Participant (short name) | PhD awarding entities (short name) | Planned Start

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** The operator read the cited finding against the ESR observation and judged that they make the same point.
- **The ESR complains of:** `both`
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-Q-S02 — implementation / impl-participants

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 3.2, 8

**ESR text (verbatim):**

> The participating organisations have the required high-quality infrastructure and capacity to implement research of high quality and their tasks. The international consortium is well-structured, integrating academic and non-academic partners with expertise, complementary strengths, and interdisciplinary knowledge, matching with the project's objectives, and reinforcing the structural and functional capability of the Doctoral Network.

**Disposition:** `independently_detected` (declared Inferred) · **Lane:** blind lane only

**Why the disposition says so (from the dispositions):**

> Operator reading: the blind strength at implementation sample 4 index 3 makes the same point as the ESR observation. Finding: "The consortium combines complementary methodological (ELTE, DTU, NTUA, RWTH), clinical (UMG, KUH, UHEI), and digital-health (UOULU) expertise, with industrial associated partners (UNEEG, Weyer, Corpuls) covering the full innovation chain."

**Findings, as resolved:**

- blind lane · criterion_strength · implementation sample 4 #3
  > The consortium combines complementary methodological (ELTE, DTU, NTUA, RWTH), clinical (UMG, KUH, UHEI), and digital-health (UOULU) expertise, with industrial associated partners (UNEEG, Weyer, Corpuls) covering the full innovation chain.

**Reference check (measured):**

- resolved: 1 blind finding(s), 0 audit finding(s), 0 candidate quote(s), 0 historical quote(s), 0 register entr(ies) — 1 of 1 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `agreed` (declared Inferred)
- **Basis:** The operator read the cited finding against the ESR observation and judged that they make the same point.
- **Recommendation:** `retain`, disposition `independently_detected` (unchanged)
- **Operator decision required:** none.

---

### ESR-Q-S03 — implementation / impl-participants

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 3.2, 5

**ESR text (verbatim):**

> Hosting arrangements via accredited doctoral schools and international offices are credible and supportive.

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. No blind finding makes this point. The failure mode is left undetermined, and the quote was chosen by word overlap with the ESR sentence; its sufficiency was not separately checked.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `implementation_section` / `3.2`
  > All DCs are embedded in accredited doctoral schools and established research groups with clear

**Fidelity register entries the row rests on:**

- `derived/sub_sections/3.2` = {"sub_section_id": "3.2", "section_id": "implementation_section", "declared_pages": [32, 33], "derived_pages": [32, 34], "heading": "3.2. Quality, capacity and role of each participant, including hosting arrangements and extent to which the consortium as a whole brings together the necessary expertise", "title": "Quality, capacity and role of each participant, including hosting arrangements and extent to which the consortium as a whole brings together the necessary expertise", "title_source": "candidate heading", "paragraphs": 15, "table_rows": 0, "characters": 5034, "claims": 4}

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 1 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Inferred)
- **Basis:** No blind finding makes this point, so there is no finding to compare. The operator read the candidate findings and confirmed the row as a miss.
- **Recommendation:** `retain`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency.

---

### ESR-Q-S04 — implementation / impl-participants

**Kind:** strength · **ESR severity cluster:** — · **Proposal location:** 3.2, 8

**ESR text (verbatim):**

> The roles of all associated partners are described in detail

**Disposition:** `not_detected_despite_sufficient_preserved_evidence` (declared Inferred) · **Lane:** neither lane

**Why the disposition says so (from the dispositions):**

> Operator reading (2026-11-13): the operator read the candidate findings for this row against the ESR observation and confirmed this classification. No blind finding makes this point. The failure mode is left undetermined, and the quote was chosen by word overlap with the ESR sentence; its sufficiency was not separately checked.

**Findings, as resolved:** none. No blind sample and no audit check names this point.

**Candidate passages (quote verified in the named sub-section):**

- `implementation_section` / `3.1`
  > Establishment and implementation of a PhD committee (see Section 2.2) for all DCs comprising

**Fidelity register entries the row rests on:**

- `derived/sub_sections/3.1` = {"sub_section_id": "3.1", "section_id": "implementation_section", "declared_pages": [24, 32], "derived_pages": [24, 32], "heading": "3.1. Quality and effectiveness of the work plan, assessment of risks and appropriateness of the effort assigned to work packages", "title": "Quality and effectiveness of the work plan, assessment of risks and appropriateness of the effort assigned to work packages", "title_source": "candidate heading", "paragraphs": 33, "table_rows": 113, "characters": 27796, "claims": 8}

**Evidence preservation:** declared Assumed. Preservation of the evidence the evaluators read is not measurable from this copy.

**Reference check (measured):**

- resolved: 0 blind finding(s), 0 audit finding(s), 1 candidate quote(s), 0 historical quote(s), 1 register entr(ies) — 2 of 2 against the artifact each names.

**Semantic agreement (declared, provisional):**

- **Does the evidence support the ESR's proposition?** `not_applicable` (declared Inferred)
- **Basis:** No blind finding makes this point, so there is no finding to compare. The operator read the candidate findings and confirmed the row as a miss.
- **Recommendation:** `retain`, disposition `not_detected_despite_sufficient_preserved_evidence` (unchanged)
- **Operator decision required:** Classification confirmed by the operator. Still open on this row: the failure mode is undetermined, and the quoted passage was chosen by word overlap and not checked for sufficiency.

---

## 7. What this report does not settle

- Whether a resolved finding is about the ESR's proposition is a judgment, recorded above as `semantic_agreement` and adjudicated in R03.
- Whether the copy preserves the evidence an ESR observation rested on is an operator declaration, prepared in R04. Every alleged miss and every partially observable row depends on it.
- Whether a praised point survives sanitisation can be settled only against the submitted original, inside the private network (PE-09).
- No disposition, revision, count or score in the comparison artifact was changed by this report. Successor artifacts are R05's.
- Relationship to earlier versions: an earlier review of this comparison, if one exists, stays in this directory under a lower sequence number. Nothing here supersedes an artifact in place, and a review of a successor comparison is a new file, not an edit of this one.

