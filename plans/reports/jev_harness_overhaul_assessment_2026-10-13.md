# Jev and the harness: assessment and target architecture

| Field | Value |
|---|---|
| Date | 2026-10-13 |
| Branch / commit inspected | `msca-dn-pre-eval` at `0f2fa8b1233a88090238528b7fdf8d2159b1f08a` |
| Vendor model and docs | `jev-1.13.0` (the only release listed); TypeSafe docs read 2026-10-13 |
| SDKs checked | `typesafe-sdk` 0.7.4 (Python ≥3.10), `@typesafe-ai/sdk` 0.6.0 (Node ≥20) |
| Status | Decision input. Nothing was installed, run, transmitted or implemented. No historical record was edited. |
| Authority | Execution aid under `CLAUDE.md` §10.2. Adopting any part of it is an operator decision. |

The two attached PDFs were used for orientation only. Every vendor fact below was re-read from the primary page named in Appendix A, and the discrepancies with the attachments are listed in §4.5.

---

## 1. Decision

**Adopt Design 1 in a bounded form: Jev augments the harness as an optional, injectable typed-decision provider. It replaces nothing, it never enters the blind lane, and it stays out of the private network until a processing route exists.**

Six facts decide this.

1. **Jev cannot reach the data that matters.** The production host has no internet route and its Bedrock endpoint policy admits only Claude model ARNs (`docs/infrastructure_security/audit_package/ADR-001-security-decisions.md`, Decisions 1–2). TypeSafe documents no VPC, on-premises, Bedrock or private-endpoint option, and hosts in the United States only (§4.4). The V14 Stage A experiment on the submitted original therefore proceeds without Jev under current terms and architecture.
2. **Jev cannot produce the output the scoring contract consumes.** The criterion scorer requires `shortcomings`, `strengths` and `rationale`, and the ESR comparison resolves its `criterion_shortcoming` and `criterion_strength` references against those texts. Jev returns distributions and no text ("do not ... generate explanations of their reasoning", `docs.typesafe.ai/concepts/system-one`).
3. **Independent evidence points away from rubric scoring.** The University of Bonn evaluation of jev-1.13.0 found rubric scoring of generated text its weakest task (correlations 0.275–0.558) and calibration that changes direction by task (§4.6). Design 3 would place Jev on exactly that task.
4. **The harness cost policy forbids a required metered service** (`plans/harness_plan/HARNESS_COST_POLICY.md`, set 2026-07-21). Jev bills per input token. It can exist only as an optional backend behind the existing injected-backend seam, with the lane green and the tests passing without a key.
5. **No calibration data exists** (`harness/DATASET_DISPOSITIONS.md`, ticket X03). Every Jev threshold would be set against nothing. Agreement with the Claude panel is not ground truth, and the vendor's own evals use LLM-consensus labels.
6. **Four bounded tasks fit Jev's documented strengths** and are currently either hand-declared or unimplemented: ESR-observation agreement drafting, assessor false-absence screening, claim–evidence support once X01 lands, and a cell-addressal second opinion in shadow. Each is a short-text classification over supplied evidence, which is what the vendor documents and the Bonn evaluation support.

What the recommendation does not do: it does not change the advisory-versus-runtime boundary, it adds no runtime gate, it needs no `CLAUDE.md` amendment, and it adds one new Python module family and one data-schema family. Everything else is retained.

---

## 2. Repository state at `0f2fa8b`

### 2.1 Classification of what exists

| Class | Items |
|---|---|
| Implemented and tested | E1 substrate (`judge`, `verdict`, `routing`, `provenance`, `report`, `response_cache`); E2 status-aware faithfulness; E3 ledger completeness, materiality, status calibration; E4 regression machinery; E5a–e rubric lane; PE-01..PE-08; V01–V13, V17, V18; R01–R03, R05. Acceptance lane green: 2,121 passed, 0 failed, 17 declared exclusions (`harness/ACCEPTANCE_LANE.md`). |
| Tested contracts that carry the lane | 7 of 17 lane areas are `depended_on: true`: importer, profile, preflight, freeze, comparison, provenance, isolation. |
| Missing datasets | `harness/gold_sets/`, `harness/materiality_sets/`, `harness/regression_baselines/` hold READMEs only; `harness/rubric_reports/` holds a `.gitkeep`. The E1.5 and E3.1 calibration records cited in the plan are absent from the decision log. X03 names the lift. |
| Unresolved limitations | V01 criterion 4 open (runtime-environment block reaches no committed manifest). V02c criterion 1 excluded. V05 older audit does not reproduce in full. No authority-matrix row is `Confirmed`. Two 2025 authorities disagree on score resolution. 34 open deferral rows, 22 needing the original. AVC-01 and AVC-02 assessor-error cases open. |
| Planned, no code | E5.1, E6, E7a, E7b, E8, E9, E10; X01–X04; V14, V15, V16; PE-09 declared, not built; R04 criterion 5. |
| Not green at HEAD | Whole suite 7,985 passed / 37 failed / 86 skipped of 8,108 (V17/V18 status note). The named lane is the acceptance surface, not the whole suite. |

### 2.2 The 74.60 baseline

`docs/tier4_orchestration_state/msca_dn/baselines/resolved_fixes_2026-10-06/blind_baseline_f60ae6e0a2a1.freeze.json` freezes one blind pass of the sanitised derivative under the 2026 profile: excellence 4.0, impact 3.3, implementation 3.7, total 74.6, assessor `claude-sonnet-5` over `claude-cli`. The ledger states it is evidence, not a target: "Prompts and rubrics will not be tuned toward 85.80" (spec §1), "the −11.2 sanitised delta is not carried forward as a predictor" (V14 criterion 10). This report tunes nothing toward it and proposes no comparator role for it.

### 2.3 Prior position on Jev

The repository already records the intended stance in one sentence: "Jev remains a prospective typed-decision adapter inside the harness, not a replacement for it. Keep generative explanations separate from typed decisions; benchmark bounded checks in shadow mode and validate deployment approval before using sensitive material" (`plans/Dev_Graph_Orchestrator_Implementation_Handoff.md:263`). No code, seam, schema or test references Jev or TypeSafe. This report is consistent with that sentence and makes it concrete.

---

## 3. The evaluation path today

### 3.1 Stage map

| Stage | Module(s) | Command | Model calls | Jev role proposed |
|---|---|---|---|---|
| 0 Extraction and fidelity | `runner/external_proposal.py`, `runner/extraction_environment.py`, `tools/import_external_proposal.py`, `runner/dry_import.py` (V08), `runner/original_configuration.py` (V17) | `py -3.10 -m tools.import_external_proposal` | none; PyMuPDF 1.28.2 pinned | none |
| 1 Graph and evidence selection | `runner/dev_graph/*`, `harness/evidence_pack.py`, `harness/appendix_mapping.py` | inside preflight and assess | none; deterministic `selection_terms` + anchors | none on selection; shadow omission annotation deferred (J6) |
| 2 Preflight | `harness/evidence_preflight.py`, `harness/grounding_scope.py` | `blind_assessment preflight` | none | none |
| 3a Cell assessment | `harness/expectation_coverage.py` via `harness/blind_assessment.py` | `blind_assessment assess` | N=3 majority, `claude-cli` or OpenAI-compatible | shadow second opinion (J5), never in V14 |
| 3b Criterion scoring | `harness/criterion_scoring.py` | same | N=5, median, spread; `S = 10E + 6I + 4Q` | benchmark-only Score shadow (J7); no production role |
| 4 Validation and freeze | `harness/blind_baseline.py` (22 checks) | `blind_assessment freeze` | none | none |
| 5 Integrity audit | `harness/integrity_audit.py`, `harness/candidate_provenance.py` | `blind_assessment audit` | none | consumer of the audit's table inventory for the false-absence screen (J4) |
| 6 ESR comparison | `harness/esr_comparison.py`, `harness/comparison_diff.py` | `blind_assessment compare`, `diff` | none | none on resolution; agreement draft feeds stage 7 (J3) |
| 7 Operator review | `harness/operator_review.py` | `blind_assessment review` | none | Jev drafts the declared `Agreement` column, labelled as a draft (J3) |

### 3.2 E1–E9 responsibilities and what is real

| Ticket | Scope | Status in code | Jev relevance |
|---|---|---|---|
| E1 | Independent judge substrate | done | Jev is a second provider kind beside it, not a judge subclass |
| E1.5 | Faithfulness calibration | mechanism done; data absent | same labels would serve a Jev support classifier |
| E2 | Status-aware faithfulness | done | candidate for a Jev second opinion per claim (J8) |
| E3 | Ledger completeness, materiality, status drift | done; E3c recall unmeasured; `assumed` path unexercised | decomposition stays generative; materiality Noul possible after E3.1 data returns |
| E3.1 | Materiality calibration | runner done; dataset and record absent | prerequisite for any Jev materiality use |
| E4 | Regression goldens | machinery done; no goldens | none |
| E5a–e | Rubric lane, two axes | done | cell second opinion (J5) |
| E5f | First real rubric run | partial; no frozen artifact | none |
| E5.1 | Rubric calibration | not implemented | shares labelling with X03 |
| E6, E7a, E7b | Prompt boundary, α-block, β run | not implemented | none |
| E8 | Adversarial suite | not implemented | Jev adversarial-content weakness makes E8-style fixtures mandatory in the benchmark (J2) |
| E9 | Context precision/recall | not implemented; native path is set arithmetic | none |
| E10 | Paid framework integration | deferred by policy | Jev is the first metered external; fold its governance into J0 and retire the framework list (§8) |

---

## 4. Jev as documented

### 4.1 Interface

Endpoint `POST https://api.typesafe.ai/v1/systemone` with `state` (string, object or array), `model`, and a map of named questions (`docs.typesafe.ai/api`). Three primitives:

| Primitive | Request | Response | Documented bound |
|---|---|---|---|
| Choice | `instructions`, `criteria` map option → description | `choice` (argmax), `probabilities` (sum 1), `confidence` | up to 255 options |
| Score | `instructions`, ordered `criteria` levels | `score` = Σ level × probability, `legend`, `probabilities`, `confidence` | 2–10 levels |
| Noul | `instructions`, optional `criteria.true/false` | `noul` = P(yes) in 0–1 | no confidence field |

Every question in a request sees the same state and is evaluated independently; "One question's answer is not hidden context for another" (`docs.typesafe.ai/primitives`). The response carries `model` and `usage.input_tokens/output_tokens`. There is no explanation field, no batch endpoint, and no documented maximum number of questions per request beyond the token budget.

### 4.2 Confidence

`docs.typesafe.ai/confidence` defines Choice confidence as `(p_max − 1/n) / (1 − 1/n)` and Score confidence as a distance-weighted concentration statistic around the modal level. Both are distribution summaries. The page says thresholds "depend on your domain and the performance of the model for your use case." Confidence is not an empirical probability of correctness and this report never treats it as one.

### 4.3 Limits, pricing, versioning, determinism

| Item | Documented value | Source |
|---|---|---|
| Context | 64k tokens per request; 32k for `state` plus the longest question | `docs.typesafe.ai/models` |
| Price | $0.042 per million input tokens; output free | same |
| Rate limits | 100k tokens/s and **80 requests/s**, "adjusting dynamically" | same |
| Versions | `jev-1.13.0` only; aliases `jev-latest`, `jev-preview` both resolve to it; "pin that version's ID instead of the alias" | same |
| Customisation | none; "not fine-tuned or LoRA-adapted with customer data" | same |
| Inputs | text only; English primary | same; `concepts/state` |
| Determinism | no temperature, seed or determinism parameter; vendor consistency cookbooks measure variance across repeats and use a fresh `uid` field to force independent draws | `api`; `cookbooks/consistency_*` |
| SLA | none in the Master Customer Agreement; status page reports 99.837% API uptime with incidents on 20, 21, 23 and 28–29 September 2026 | `typesafe.ai/legal/mca`; `status.typesafe.ai` |

Determinism consequence: a live Jev call is not reproducible. The harness's existing position applies unchanged. Reproducibility comes from byte-faithful replay of recorded responses, not from the provider.

### 4.4 Data processing and deployment

| Question | Documented answer | Status |
|---|---|---|
| Training on inputs | No. Privacy Policy, MCA and models page agree. | documented |
| Retention period | "for as long as reasonably necessary"; no number anywhere | not established |
| Zero data retention | "available for enterprise customers. Ask about the setup" | enterprise only, on request |
| Hosting region | United States; endpoints `api.us.typesafe.ai`, `api.us-west-2.typesafe.ai` | documented; no EU region |
| VPC, on-prem, dedicated endpoint | not documented; the enterprise FAQ poses the question but no answer was retrievable | not established |
| Bedrock, Vertex, Azure, AWS Marketplace listing | none found on any vendor page | not established |
| GDPR | DPA with EU SCCs Module 2, UK addendum, 72-hour breach notice | documented |
| SOC 2 | Type II claimed; report gated behind the Trust Center | claimed, report not read |
| Sub-processors | Trust Center page is JavaScript-rendered and was not retrieved in this session | **not retrieved** |

Consequence for this repository. The production environment is a private VPC with no internet gateway, no NAT, and an endpoint policy restricted to `anthropic.claude-*` (ADR-001 Decisions 1–2). Reaching `api.typesafe.ai` from it would reopen the egress path the architecture exists to close. A private network does not make a US-hosted public API private. No supported processing route exists today for the submitted original or for the Stage B candidate.

The only material Jev can process without a new governance decision is synthetic (the `SYN-ALPHA` world, the BIODIV-01 demo candidate). Whether the sanitised derivative, the ESR text, or harness outputs quoting them may go to a US processor is an operator decision that this report does not make.

### 4.5 Discrepancies with the attached PDFs

| Attachment statement | Finding |
|---|---|
| Rate limit 40 requests/s | Docs say **80 requests/s**. |
| Nine failure modes | Confirmed as nine table rows; "Math and Numbers" has three sub-headings, so heading counts give 11–12. |
| Everything else checked (64k/32k, $0.042/M, 255 options, 2–10 levels, text-only, isolation, no Noul confidence, SDK names, Node 20+) | Confirmed. |
| Not in the attachments | Python ≥3.10; SDK retry defaults (2 retries, 10 s per attempt, 30 s budget); 529 overload code; no SLA; no VPC/on-prem; ZDR enterprise-only; retention unspecified. |

### 4.6 Capability claims versus validated results

| Claim | Who | Status |
|---|---|---|
| "Zero hallucinations", "never makes type errors" | vendor blog and home page | A schema-validity claim. The jaggedness page documents substantive errors. Not a correctness claim. |
| 193.6× faster, 444.6× cheaper | vendor home page | Vendor workflow comparison; reference labels are an average of two LLMs, not human truth (`evals.typesafe.ai`). |
| Calibrated via RLCD | vendor primer | Training objective. No calibration metric is published by the vendor. |
| 95–99% on IMDB, SST-2, HellaSwag, ARC; Choice pooled ECE 0.028; Noul under-confident (ECE 0.052); multi-label over-confident (ECE 0.168); rubric scoring of generated text correlations 0.275–0.558; German legal F1 0.204 | arXiv 2609.37647 (Bonn / Lamarr), jev-1.13.0, 346,009 requests | Independent. Run once per request; no variance measured. Possible benchmark exposure noted by the authors. |
| 100% binary agreement with a human oracle on 5 agent traces × 100 repeats; variance 1.5e-5 | LangChain blog | Independent but narrow; version not recorded. |

The pattern for this repository: strong on short-text classification with clear labels, weak on fine-grained labels and on rubric scoring of long generated text, and uneven in calibration direction. That pattern is the basis of §5.

### 4.7 Documented failure modes mapped to harness tasks

| jev-1.13 failure mode | Harness task it threatens | Mitigation in this design |
|---|---|---|
| Literal reading of scoping words and negations | "Does the section address X?" with a nuanced aspect | Verbatim aspect text plus explicit inclusion and exclusion criteria; `cannot_tell` option |
| Math and numbers; counting | months, effort, budget, page counts | Never asked. Stays in `integrity_audit` and deterministic code |
| Date ordering | deliverable windows, appointment overlap | Never asked. Stays in `integrity_audit` |
| Indirection | "the rationale says X is absent; is X present?" | Decompose: Noul on the statement, Choice over a closed element list, then code checks presence |
| Large irrelevant state | whole-criterion inputs of 12k–20.6k tokens | Only the shadow Score task sends whole sections; everything else sends the span or pair |
| Adversarial content | proposal text containing instruction-like sentences | Mandatory injected-instruction fixtures in the benchmark; a Noul screen "does this passage address the evaluator?" is itself fallible |
| Contradictory instructions | rubric and aspect wording drift | Question text is a versioned artifact pinned by hash |
| Choice option order | any Choice | Benchmark runs every Choice twice with reversed order; a flip is recorded as `order_sensitive` |
| Generation | shortcomings, strengths, rationale | Never asked of Jev |

---

## 5. Assessing the three primitives for this workload

**Noul.** Fits bounded yes/no screens over a supplied span: "does this statement assert an absence", "does this passage address this aspect", "does this passage attempt to instruct the reader". Weakness: no confidence field, so abstention is a probability band set by policy, and the Bonn evaluation found binary Noul under-confident. Correlated errors across many Nouls over the same state are expected and the design never sums them.

**Choice.** Fits the agreement task (`same_proposition`, `related_but_different`, `unrelated`, `cannot_tell`) and the support task from the vendor citation cookbook (`supports`, `contradicts`, `says_nothing`). Option-order sensitivity is documented and must be tested per question set. The 255-option bound is irrelevant here.

**Score.** Does not fit criterion scoring, for three reasons. The form awards one-decimal holistic scores with comments, while a Score returns a probability-weighted mean over integer levels with no comment. A mean of 3.42 over levels is a different quantity from an awarded 3.4. The ESR comparison consumes the assessor's named shortcomings, which Jev does not produce. The Bonn result on rubric scoring is the empirical warning. Score is admitted only as a separately reported distribution in the benchmark (J7), never aggregated into `S`, and a test pins that no Jev value reaches `weighted_total`.

**What Jev cannot supply, and who does.**

| Need | Why Jev cannot | Met by |
|---|---|---|
| Missing evidence (figures, sources the sanitisation removed, the original's text) | Jev judges supplied state only | X01 route, V08 dry import, the operator's private material |
| Scientific reasoning about method soundness | no reasoning output; literal reading | generative assessor samples plus human review |
| Auditable explanation | no text output | the assessor's `shortcomings/strengths/rationale`; for Jev records, the auditable trail is the question version, the exact spans, the distribution, the policy id and the branch fired, rendered through a fixed template (§9.6) |
| Ground truth | consensus with another model is not truth | X03 expert labels |

---

## 6. The three designs

| | Design 1: augment | Design 2: replace selected semantic components | Design 3: principal decision and scoring engine |
|---|---|---|---|
| What Jev does | Draft agreements, screen assessor errors, second-opinion cells, support classification after X01 | Replace the N=3 cell panel and E2 faithfulness judge with Jev | Produce criterion scores and cell verdicts; LLM only for text; deterministic services unchanged |
| Output contract | All current schemas unchanged; Jev records additive | `CoverageGrade.rationale` disappears or must come from a second call | `shortcomings/strengths/rationale` cannot be produced; ESR comparison loses its references |
| Evidence base | vendor cookbooks (citation check, RAG classification) plus Bonn classification results | Bonn classification results only; no domain labels | Bonn rubric result argues against it |
| Blind lane | untouched | changed; `TRANSPORT_ISOLATION_EVIDENCE` needs a new transport entry and the V13 receipt a new section | same, plus the freeze arithmetic changes |
| Private network | not needed for shadow and comparison-stage tasks | needed for the lane; no route exists | needed; no route exists |
| Cost policy | compatible if optional | requires amending "no metered service required" | same |
| Complexity | one provider module, one record type, one shadow runner | removes one judge path, adds a provider, changes freeze checks | rewrites scoring, freeze, comparison and receipt |
| Reversibility | unset one env var | re-enable the judge path | full rollback of four modules |

**Design 2 is rejected** for three reasons. The cell verdict carries a rationale the operator reads. No labelled data exists to show Jev is at least as accurate as the panel on this domain. The lane the change would alter is the one that must run in a network Jev cannot reach.

**Design 3 is rejected** on the output-contract mismatch alone, and independently on the Bonn rubric result and the processing route.

**Design 1 is recommended.** Every task it assigns to Jev is a short-text classification over supplied evidence. Each is currently hand-declared or unimplemented. Each runs outside the blind lane or in shadow, and each can be switched off without touching a committed artifact.

---

## 7. Architecture

### 7.1 Current

```
                         deterministic                     advisory (harness, out-of-band)
runner/ ──► 138 predicates + byte-equal gates        harness/judge.py ──► claude-cli (subscription)  ─┐
   │        (the only blocking gates)                                 └─► OpenAI-compatible (Groq/local)
   │                                                                                                  │
   ▼                                                      routing.assert_judgeable ◄──────────────────┘
import (PyMuPDF 1.28.2) ─► dev_graph ─► evidence_pack ─► preflight ─► assess (cells N=3, criteria N=5)
                                                                           │ response_cache (replay)
                                                                           ▼
                                                   freeze (22 checks) ─► audit (deterministic) ─► compare (ESR enters here)
                                                                                                        │
                                                                                                        ▼
                                                                                              operator review
                                                                                       measured half │ declared half (by hand)
```

### 7.2 Target

```
runner/ (unchanged) ───────────────────────────────────────────────────────── no Jev anywhere in runner/

harness/
  judge.py (unchanged)            decision_provider.py  (NEW, sibling of judge, not a subclass)
      │                               │   TypeSafeBackend (httpx, one POST)  │  FakeDecisionBackend (tests)
      │                               │   question sets: harness/decision_questions/*.json (versioned, hashed)
      │                               │   records: TypedJudgment{distribution, policy, branch}  evidence_type=Inferred
      │                               │   checkpoint: ResponseCache binding provider=typesafe model=jev-1.13.0
      ▼                               ▼
  blind lane (unchanged, no Jev) ─► freeze ─► audit ─► compare ─► review ◄── agreement_draft.py (J3, reads comparison + ESR text)
                                                 │
                                                 └─► absence_screen.py (J4, reads frozen samples + audit table inventory)
  shadow/                                                                 ◄── cell_shadow.py (J5, same packs, writes beside report)
  benchmark/                                                              ◄── score_shadow.py (J7, benchmark fixtures only)
  calibration/ (gold_set extended for new task labels, X03)
```

Rules the target keeps. The import direction stays `harness → runner` only, and `tools/` and `scripts/` never import `harness`. `HarnessReport(advisory=True, blocking=False)` stays the only constructible report. `Verdict` stays `Inferred`-only and unchanged. The freeze checks, the receipt and `TRANSPORT_ISOLATION_EVIDENCE` are untouched, because Jev never produces a cell or a criterion score that a freeze reads.

---

## 8. Component replacement matrix

| Component | Decision | Reason |
|---|---|---|
| `judge.py`, `verdict.py`, `provenance.py`, `routing.py`, `report.py`, `jsonl_log.py` | Retain | Substrate is sound; Jev records reuse `prompt_hash`-style hashing and `Inferred` typing |
| `response_cache.py` | Retain, extend binding | Add `provider` and `question_set_hash` to `CacheBinding`; replay stays byte-faithful |
| `expectation_coverage.py` (cells) | Retain; augment in shadow (J5) | Panel rationale is read by humans; no labels yet to justify replacement |
| `criterion_scoring.py` | Retain unchanged | Output contract and Bonn evidence; Jev Score benchmark-only (J7) |
| `evidence_pack.py`, `appendix_mapping.py`, `evidence_preflight.py` | Retain | Pack-set hash binding requires deterministic selection; a Jev relevance score would move the hash on every call |
| `blind_assessment.py`, `blind_baseline.py`, `grounding_scope.py`, `candidate_provenance.py`, `execution_receipt.py` | Retain unchanged | Blind lane carries no Jev |
| `integrity_audit.py` | Retain; expose table inventory | The false-absence screen (J4) needs the parsed table list as an input |
| `esr_comparison.py`, `comparison_diff.py` | Retain | Reference resolution is deterministic and must stay so |
| `operator_review.py` | Retain; accept a draft `Agreement` column (J3) | The declared half gains a labelled draft; `review_state` stays `agent_drafted_pending_operator_review` |
| `faithfulness.py`, `status_faithfulness.py` | Retain; augment later (J8) | Citation-check pattern fits; needs E1.5 labels first |
| `claim_ledger.py` | Retain | Decomposition is generation |
| `materiality.py`, `status_calibration.py` | Retain; defer Jev | E3.1 dataset absent from tree |
| `calibration.py`, `gold_set.py` | Retain; extend schema | Hold labels for the three new tasks (X03) |
| `regression.py`, `rubric.py`, `rubrics.py`, `expectations.py`, `expectation_grounding.py` | Retain | No Jev role |
| `authority_matrix.py`, `historical_profile.py`, `deferral_register.py`, `record_*`, `acceptance_lane.py` | Retain | Declaration readers; no model |
| `commands/_subscription_judge.py` | Retain | Jev is not a judge transport and must not be registered as one |
| `commands/blind_assessment.py salvage` | Retain for V14; review for retirement after | Checkpointing is default; transcript salvage is a recovery path with cells-only coverage |
| Double-entry schema strings (`tools/` vs `harness/`) | Simplify, independent of Jev | A leaf package neither side owns (for example `schemas/`) removes the double entry without breaking the boundary test |
| E10 framework list (DeepEval, Ragas, PromptFoo, DeepTeam) | Retire as a list; keep one policy line | The native track already extracted their substance; Jev is the first concrete metered external, so one "optional metered provider" rule replaces four framework placeholders |
| E8 (adversarial) | Keep as deterministic fixtures; make them a Jev benchmark input (J2) | Adversarial content is a documented Jev weakness |

New abstractions and their justification:

| New thing | Why it earns its place |
|---|---|
| `decision_provider.py` | Jev is not a chat completion; forcing it through `Judge` would fake a `rationale` or break the `Verdict` contract. One module, one protocol, two backends. |
| `TypedJudgment` record | Carries a distribution and a policy branch, which `Verdict` must not (its `Inferred`-only, passed/score shape is test-pinned). |
| Versioned question sets as data | Question text is workflow configuration; hashing it is what makes a threshold reproducible and a regression attributable. |
| Three task modules (J3, J4, J5) | Each is a bounded read-only transform with one input artifact and one output file; none shares code worth a framework. |

Nothing else is added. No TypeScript service, no gateway, no dashboard.

---

## 9. Integration contracts

### 9.1 Language and placement

Python, inside `harness/`. Reasons: the injected-backend seam, `ResponseCache`, provenance and the acceptance lane are Python; `httpx` is already an optional runtime dependency in `runner/transport/openai_compatible.py`; the Jev API is one POST. A TypeScript service would add a process boundary, a second runtime and a second secret path for no capability. The official Python SDK is not required: a 150-line adapter mirroring `OpenAICompatBackend` keeps raw response bytes for replay and avoids a pydantic dependency. If the SDK is preferred later, wrap it behind the same protocol.

### 9.2 Provider protocol

```python
class DecisionBackend(Protocol):
    def __call__(self, request: DecisionRequest) -> RawDecisionResponse: ...
    # RawDecisionResponse carries the exact response bytes, the HTTP status, the
    # returned `model`, `usage`, and wall-clock latency. Parsing happens above the seam.

@dataclass(frozen=True)
class DecisionRequest:
    state: str | dict | list           # the exact evidence; never a path
    questions: Mapping[str, Question]  # loaded from a versioned question set
    model: str                         # pinned id, never an alias ("jev-1.13.0")
    uid: str                           # request nonce so repeats are independent draws
```

`TypeSafeBackend(api_key_env="TYPESAFE_API_KEY", base_url, timeout=10.0, max_retries=2)` retries 408, 429, 5xx and 529 with jittered backoff and a total budget, honours `Retry-After`, and never retries a 4xx validation error. `FakeDecisionBackend` serves canned responses for every test. A missing key constructs nothing and the lane runs without it.

### 9.3 Question sets

`harness/decision_questions/<task>.json`:

```json
{
  "schema_id": "decision_question_set/1",
  "task": "esr_agreement",
  "version": "1.0.0",
  "model": "jev-1.13.0",
  "questions": { "...": "exact Jev question objects" },
  "policy": {
    "policy_id": "esr_agreement_policy/1",
    "abstain": {"choice_confidence_below": 0.6},
    "branches": {"same_proposition": "draft_agree", "related_but_different": "draft_partial",
                 "unrelated": "draft_disagree", "cannot_tell": "undetermined"}
  }
}
```

`question_set_hash` is the canonical hash of the file. It is recorded on every judgment, in the cache binding and in every output report. Changing a word re-opens the task's calibration state, mirroring `CalibrationReport.applies_to`.

### 9.4 Judgment record

```json
{
  "record_type": "harness.typed_judgment",
  "task": "esr_agreement",
  "question_set_hash": "sha256:...",
  "provider": "typesafe", "model_requested": "jev-1.13.0", "model_returned": "jev-1.13.0",
  "state_hash": "sha256:...", "evidence_ids": ["ESR-E-02", "criterion_shortcoming#excellence/3"],
  "answers": {"relation": {"type": "choice", "choice": "same_proposition",
               "probabilities": {"same_proposition": 0.81, "related_but_different": 0.14,
                                 "unrelated": 0.03, "cannot_tell": 0.02}, "confidence": 0.75}},
  "policy_id": "esr_agreement_policy/1", "branch": "draft_agree",
  "usage": {"input_tokens": 612, "output_tokens": 4}, "latency_ms": 310,
  "replayed": false, "evidence_type": "Inferred",
  "review_state": "agent_drafted_pending_operator_review"
}
```

Exactly one evidence type is admissible, as in `verdict.py`. No field named `score` on a 0–5 scale ever appears in a typed judgment; a test pins it.

### 9.5 Batching, ordering, isolation

Batch only questions that share one state (one ESR observation against one blind reference is one request; the vendor documents this fan-out). Never place a question whose answer depends on another in the same request. One request per record, bounded worker pool, token and request budgets both enforced, and a run stops issuing new work after a sustained error rate while retaining the pending ids. Dependency order is the harness's own: J3 reads a written comparison; J4 reads a frozen report and a written audit; J5 reads the same realised packs preflight wrote.

### 9.6 Uncertainty, abstention, fallback, explanation

| Situation | Handling |
|---|---|
| Noul in the abstention band (default 0.35–0.65, per task, set from labels) | `undetermined`; counted as abstention coverage, never as "no" |
| Choice `confidence` below the task floor, or `cannot_tell` chosen | `undetermined` |
| API error, timeout, malformed body, wrong `model_returned` | `unavailable`; the record is written with the error class; nothing is inferred |
| Provider unreachable at start | the task module exits 2 and writes nothing; the lane is unaffected |
| Explanation | rendered deterministically from a template: question version, evidence ids, the distribution, the branch. No generated prose. The operator reads the spans themselves. |

### 9.7 Caching, retries, checkpoints, provenance

Reuse `ResponseCache` with a binding extended by `provider`, `model`, `question_set_hash` and `task`. The cache key is the canonical hash of `(state, questions, model)`; the `uid` is excluded from the key so a replay reproduces the recorded draw. A replayed record is marked `replayed: true` and the report counts `replayed_calls` and `live_calls`, as `blind_assessment` does today. Every judgment appends to a `harness/provenance/typed_judgments.jsonl` log with the same append-only discipline as `ProvenanceLog`.

### 9.8 Representative questions

**J3 ESR agreement** (state = `{"esr_observation": "...", "blind_statement": "...", "sub_section": "1.2"}`):

```json
"relation": {"type": "choice",
  "instructions": "Decide whether BLIND_STATEMENT makes the same point about the proposal as ESR_OBSERVATION. Judge the proposition, not the wording or the severity.",
  "criteria": {
    "same_proposition": "Both texts assert the same strength or the same shortcoming about the same element of the proposal.",
    "related_but_different": "Both texts concern the same element but assert different things about it.",
    "unrelated": "The texts concern different elements of the proposal.",
    "cannot_tell": "One text is too vague or too short to decide."}}
```

**J4 false-absence screen** (state = one assessor shortcoming sentence):

```json
"asserts_absence": {"type": "noul",
  "instructions": "Does STATEMENT assert that a specific table, plan or section is missing from the proposal?",
  "criteria": {"true": "It says something is absent, not provided, or not included.",
               "false": "It criticises content that is present, or says nothing about absence."}},
"element": {"type": "choice",
  "instructions": "Which element does STATEMENT say is missing? Choose none_of_these if it names something not listed.",
  "criteria": {"milestones_table": "...", "deliverables_table": "...", "gantt_chart": "...",
               "risk_table": "...", "data_management_plan": "...", "recruitment_table": "...",
               "secondment_table": "...", "none_of_these": "The statement names an element not listed here."}}
```

Code then checks the audit's parsed table inventory for the chosen element and flags `possible_false_absence` only when the element exists. Jev never answers "is it present".

**J5 cell second opinion** (state = the exact rendered evidence pack):

```json
"addresses": {"type": "noul",
  "instructions": "Does the PACK text substantively address this aspect of the evaluation form: <verbatim aspect text>? Addressing means stating what the project does about it, not mentioning the words.",
  "criteria": {"true": "The text explains what is done, by whom or how.",
               "false": "The aspect is absent, or named without substance."}}
```

**J8 claim support** (after X01; state = `{"claim": "...", "source_span": "..."}`): the vendor citation-check Choice `supports / contradicts / says_nothing`, with the exact-quote string match done in code first.

---

## 10. Scoring, evidence and explanation design

**Criterion scores are unchanged.** Five draws from the pinned generative assessor, median to two decimals, spread labelled as within-assessor repeatability, `S = 10E + 6I + 4Q`, both thresholds reported. Jev contributes nothing to any of these numbers, and a test asserts that `weighted_total` and `combine_criterion_scores` receive no value originating in a typed judgment.

**Why no conversion.** A Jev Score over six verbatim level descriptors returns an expected level with a distribution. The form awards a one-decimal holistic placement with comments. Mapping 3.42 to 3.4 would present a mean over integer categories as an award at one-decimal resolution, which the form does not define. Mapping confidence to anything would present a concentration statistic as correctness. Neither is done.

**What Jev Score may do (benchmark only, J7).** Over the same whole-criterion input the assessor saw (12k–20.6k tokens today, within the 32k state budget), report the level distribution and the modal level beside the frozen median. The measurement is agreement of the modal level with the floor of the median, and Spearman correlation across fixtures. It is reported in the benchmark record and nowhere else. If the Bonn pattern holds, this closes the question of Design 3 with local evidence.

**Evidence design.** Every typed judgment names its evidence by stable id: ESR observation id, `criterion_shortcoming#<criterion>/<index>` or `criterion_strength#...` from the frozen report, cell `expectation_key::section`, claim id, or the audit's table id. The state sent is the exact text those ids resolve to, hashed. The same resolvers `esr_comparison` and `operator_review` use today re-resolve them, so a judgment on text the artifacts no longer contain is refused.

**Explanation design.** Jev records carry no generated explanation. The rendered Markdown line is a template: "Jev `jev-1.13.0`, question set `esr_agreement/1.0.0`: P(same_proposition)=0.81, confidence 0.75, branch `draft_agree`." The operator's decision column stays empty until a person fills it. The generative assessor's `shortcomings`, `strengths` and `rationale` remain the only explanations of a score.

---

## 11. Benchmark protocol, adoption criteria, cost

### 11.1 Fixtures

| Set | Source | Confidential | Use |
|---|---|---|---|
| Synthetic world | `SYN-ALPHA` instrument in `tests/harness/test_profile.py`; hand-authored cells with planted presence and absence | no | functional and option-order tests |
| Pseudonymous demo candidate | BIODIV-01 dev-graph demo (`dev_graph_demo` branch artifacts in `docs/`) and the MSCA-PF graph candidate | no | shadow runs for J4, J5, J7 |
| Adversarial fixtures | E8 substance: injected instructions inside a passage, numeric traps, double negatives, reversed option order | no | mandatory per release of a question set |
| Sanitised derivative and ESR | `docs/tier3_project_instantiation/source_materials/msca_dn/` | operator decides | J3 agreement labels, J5 shadow against the 74.60 report |
| Expert-labelled held-out | X03; does not exist | n/a | the only basis for an accuracy claim |

Public Horizon Europe Part B proposals are not assumed to exist; if the operator locates openly licensed ones, they join the second row.

### 11.2 Labelling protocol (addresses X03)

Two labellers, blind to every model output, label each item; disagreements are adjudicated by a third and the pre-adjudication Cohen's κ is recorded. Items: every cell (aspect × section) on each fixture candidate; every ESR observation × blind reference pair from the approved comparison; every assessor shortcoming sentence from frozen samples, labelled `asserts_absence` and `element present?`. The operator's recorded decisions in `operator_decisions_14508ee2def5_0001.md` seed the J3 set but are not a test set, because they were made with the comparison in view. A random split is fixed before any model output is seen; a dev set may use uncertainty sampling, the held-out set never does. The `LABELLING_GUIDE.md` rule stands: no model writes a label.

### 11.3 Measurements

| Measure | Definition |
|---|---|
| Decision quality | per-task precision and recall against held-out labels, with the costly error named first (J4: a missed false-absence; J3: a wrong `same_proposition`) |
| Panel agreement | agreement with the N=3 or N=5 Claude panel, reported as agreement, never as accuracy |
| Bias | per-criterion and per-section error rates; option-order flip rate |
| Calibration | reliability bins with n per bin and ECE for Noul tasks; confidence-band error rate for Choice |
| Abstention coverage | fraction `undetermined`; quality of the automatic fraction reported separately |
| Stability | five repeats per item with fresh `uid`; label flip rate and probability standard deviation |
| Latency | p50 and p95 per request and per full run, measured at the adapter |
| Cost | API-reported input tokens × posted rate, plus preprocessing, repeated state across requests, retries, and the Claude panel calls the task still needs |

Expected gains are stated before the run and kept in a separate column from measured results. Nothing is tuned toward the ESR total or any resubmission target.

### 11.4 Adoption criteria (set before results)

| Task | Promote from shadow to draft when | Rollback |
|---|---|---|
| J3 agreement draft | ≥0.90 agreement with adjudicated labels on held-out, abstention ≤25%, no criterion with error rate above twice the mean, option-order flip rate ≤2% | unset `TYPESAFE_API_KEY`; the `Agreement` column returns to blank |
| J4 false-absence screen | recall ≥0.90 on seeded absences; ≤3 false alarms per full report; zero flags on the synthetic clean candidate | same |
| J5 cell second opinion | stays shadow until X03 labels exist and E5.1 defines the per-axis thresholds; promotion means "shown beside the panel", never "replaces the panel" | same |
| J7 Score shadow | never promoted; benchmark record only | n/a |

A shadow pilot is two complete passes over a fixture candidate with every typed judgment written beside, not into, the committed artifacts. Regression tests pin: no Jev value in any freeze check, no `score` key in a typed judgment, lane green without a key, replay byte-faithful, and `review_state` immutable. Historical artifacts and baseline bindings are never rewritten; a new report version is a new file with the next sequence number.

### 11.5 Cost model

| Item | Basis | Estimate |
|---|---|---|
| J5 shadow, one full pass on the sanitised candidate | 10 cells × ~4k tokens + overhead | ~0.05M tokens → ~$0.002 |
| J7 Score shadow, one pass | 3 criteria × ~16k tokens × 5 repeats | ~0.24M tokens → ~$0.01 |
| J3 agreement, one comparison | 29 observations × ~15 references × ~0.6k tokens | ~0.26M tokens → ~$0.011 |
| J4 screen, one frozen report | 3 criteria × 5 samples × ~6 shortcomings × ~0.3k | ~0.03M tokens → ~$0.001 |
| Benchmark, five repeats of everything over three fixtures | sum × 15 | ~$0.4 |
| Engineering | adapter, fake backend, three task modules, question sets, tests, benchmark harness | the actual cost; order of weeks, not dollars |
| Governance | cost-policy amendment, data-processing decision, DPA and ZDR request if proposal text is ever sent | operator time; possibly an enterprise agreement |

Token cost is immaterial at this volume. The decision turns on engineering time, governance and the processing route, not on price.

---

## 12. Migration backlog

Dependency order is top to bottom. "Before private setup" means the work needs no confidential material. The last row is the only one that touches the private environment, and it is blocked indefinitely.

| Id | Ticket | Depends on | Material | Exit condition |
|---|---|---|---|---|
| J0 | Governance. Record the operator decision in `docs/tier4_orchestration_state/decision_log/`. Amend `HARNESS_COST_POLICY.md` to permit an optional metered provider behind an injected backend, never required. Decide which artifact classes may be sent to a US processor. Fold E10 into this policy. | none | none | signed decision record; policy text; a data-class table |
| J1 | `decision_provider.py` with `TypeSafeBackend`, `FakeDecisionBackend`, `TypedJudgment`, extended `CacheBinding`, question-set loader and hashing; boundary and no-score tests | J0 | none | lane green with and without a key; replay byte-faithful; 0 Jev references in `runner/` |
| J2 | Benchmark harness and adversarial fixtures (E8 substance): option-order reversal, injected instructions, numeric traps; stability and latency measurement | J1 | synthetic | benchmark record schema; first run on `SYN-ALPHA` |
| J3 | `agreement_draft.py`: Jev draft for the operator review's `Agreement` column, labelled `agent_drafted_pending_operator_review` | J1, J2, J0 data decision for the ESR and sanitised texts | sanitised derivative + ESR, if permitted | drafts written beside the review; labelling set assembled |
| J4 | `absence_screen.py`: false-absence screen over frozen samples and the audit's table inventory; closes the tooling half of AVC-01/AVC-02 | J1, J2 | BIODIV demo first; sanitised report if permitted | seeded recall measured; flags rendered for the operator |
| J5 | `cell_shadow.py`: Noul second opinion over the realised packs, written beside the report | J1, J2 | demo candidates; sanitised if permitted | shadow agreement with the N=3 panel reported, labelled as agreement |
| J6 | X03 labelling: protocol, two labellers, adjudication, held-out split; `gold_set` schema extended | J3–J5 produce the item lists | labellers see proposal text | κ recorded; held-out frozen by hash |
| J7 | `score_shadow.py`: Score distribution over whole-criterion inputs, benchmark only | J1, J2 | demo candidates | modal-level agreement and correlation recorded; the Design 3 question closed with local evidence |
| J8 | Claim-support classifier for X01 using the citation-check pattern | X01 route (deterministic, outside this backlog), J6 labels | depends on X01's sources | precision/recall on E1.5-style labels; advisory |
| J9 | Adoption review: compare measured results with §11.4; promote, hold or retire each task; version the question sets | J6, J7 | none | decision record per task |
| J10 | Private-network route (blocked): requires a TypeSafe deployment option that does not exist today, or an operator decision to open egress and sign a DPA with ZDR. Not scheduled. | J9 and a vendor capability | the original | none until the route exists |

The deliverables of J1–J9 are reviewable as implementation tickets in the configured local tracker (`.scratch/<slug>/issues/`), one per row, each with the acceptance test named in its exit condition.

---

## 13. Mapping to X01–X04

| Ticket | Still necessary | Jev could support | Could be simplified |
|---|---|---|---|
| X01 imported-source grounding | Yes. Loading claims with resolvable sources and evidenced statuses is deterministic route work Jev cannot do. | The per-pair support judgment (J8) as an advisory second opinion beside E2. | No. The `IMPORTED_CLAIM_ROUTE_IMPLEMENTED` flag and the refusal of `source_grounded` stay. |
| X02 engineering-graph population | Yes, if trace-driven engineering is claimed. Entity extraction is generative or deterministic work. | Marginally: Choice over a closed candidate set of entity types for a parsed row. Not worth a ticket. | No change. |
| X03 calibration data | Yes. It is the prerequisite for every accuracy claim, including any claim about Jev. | Jev adds a second thing to calibrate, not a substitute. Uncertainty sampling may order the dev set; the held-out set stays random. | The labelling protocol (J6) serves E1.5, E5.1 and the Jev tasks at once. One protocol, three consumers. |
| X04 cross-baseline comparison | Convenience only, deterministic. | None. | Unchanged. |

---

## 14. Unresolved questions and work deferred to V14–V16

**Unresolved by the vendor documentation**

- Retention period and deletion-on-termination timeline (DPA gives none).
- Whether any VPC, dedicated or on-premises deployment exists; the enterprise FAQ poses the question without a retrievable answer.
- Sub-processor list and SOC 2 report scope (Trust Center not retrievable in this session; verify in a browser before citing).
- Model deprecation notice period; a pinned `jev-1.13.0` has no documented lifetime.
- Run-to-run variance on identical inputs without a `uid`; the cookbooks imply caching but do not state it.

**Unresolved for the operator**

- Whether the sanitised derivative, the ESR text and harness outputs quoting them may be sent to a US-hosted processor at all. Without that decision J3, J4 on the sanitised report, and J5 on the sanitised candidate stay on synthetic fixtures.
- Whether to request an enterprise ZDR arrangement before any proposal text leaves the repository.
- The cost-policy amendment wording (J0).

**Deferred to V14** (operator act, no Jev): the Stage A experiment runs in the private network under the V13 receipt and the V17/V18 configuration route with the pinned generative assessor. Nothing in this report changes its inputs, its freeze checks or its comparison.

**Deferred to V15**: the acceptance record states the grounding scope and residual uncertainties. If any Jev shadow output exists by then, the record names it as advisory draft evidence that influenced no score and no freeze.

**Deferred to V16**: the Stage B candidate is confidential and has no processing route; Jev stays out unless J10 unblocks. Any question set validated on the 2025 material is re-validated on the 2026 profile before use, because the profile, the call and the candidate all change.

---

## Appendix A. Access record

All vendor pages read 2026-10-13 through a fetch tool; figures that matter were re-fetched with verbatim prompts and agreed across fetches.

| Source | URL | Retrieved |
|---|---|---|
| Introduction, quickstart, primitives (choice, score, noul, advanced), API, models, confidence, state, system-one, use-case map, fan-out, composite scoring, confidence routing | `https://docs.typesafe.ai/...` as named in §4 | yes |
| jev-1.13 jaggedness | `https://docs.typesafe.ai/model-jaggedness/jev-1.13` | yes (three fetches) |
| SDK pages, Python API (clients, retries, constants, exceptions, changelog), JavaScript API (client config, retry policy, version) | `https://docs.typesafe.ai/sdk/...` | yes |
| PyPI `typesafe-sdk` 0.7.4 | `https://pypi.org/project/typesafe-sdk` | yes |
| npm `@typesafe-ai/sdk` 0.6.0 | `https://registry.npmjs.org/@typesafe-ai/sdk/latest` (npmjs.com returned 403) | yes via registry |
| Cookbooks: citation check, RAG passages, guardrails, function calling, parallel questions, consistency (noul, choice) | `https://docs.typesafe.ai/cookbooks/...` | yes |
| Legal index, DPA, MCA (Sep 23 2026), privacy policy (Nov 19 2025), acceptable use, enterprise page | `https://docs.typesafe.ai/legal`, `https://typesafe.ai/legal/...`, `https://typesafe.ai/enterprise` | yes |
| Trust Center and sub-processors | `https://trust.typesafe.ai/`, `/subprocessors` | **not retrieved** (JavaScript-rendered; browser extension unavailable) |
| Status page | `https://status.typesafe.ai` | yes |
| Vendor evals | `https://evals.typesafe.ai/` | yes |
| Launch blog, home page | `https://typesafe.ai/blog/introducing-system-one-models-and-jev`, `https://typesafe.ai` | yes |
| Agent skill, skills repo, adapter repo, coding-agents page | `https://docs.typesafe.ai/agent-skill`, `https://github.com/typesafe-ai/skills`, `https://github.com/typesafe-ai/system-one-adapter-python`, `https://docs.typesafe.ai/introduction/coding-agents` | yes |
| Independent evaluation | `https://arxiv.org/abs/2609.37647` (Deußer, Sparrenberg, Sifa; 29 Sep 2026) | yes |
| LangChain agent-eval report | `https://www.langchain.com/blog/jev-agent-evals-langsmith` | yes |
| Repository sources | `CLAUDE.md`; `harness/HARNESS.md`; `harness/ACCEPTANCE_LANE.md`; `harness/DATASET_DISPOSITIONS.md`; `plans/harness_plan/HARNESS_COST_POLICY.md`; `plans/harness_plan/EVALUATION_HARNESS_STRATEGY.md`; `plans/harness_plan/tickets_eval_harness.md`; `plans/msca_dn_historical_validation_tickets.md`; `plans/msca_dn_pre_evaluation_spec.md`; `plans/msca_dn_pe09_runbook.md`; `plans/claude_plugin_assessment_handoff_2026-10-09.md`; `plans/Dev_Graph_Orchestrator_Implementation_Handoff.md`; `docs/infrastructure_security/audit_package/ADR-001-security-decisions.md`; `docs/infrastructure_security/audit_package/security_architecture_diagram.md`; `harness/*.py` and `harness/commands/*.py` as cited | at `0f2fa8b` |

## Appendix B. Sizes that bound the design

| Quantity | Value | Source |
|---|---|---|
| Criterion input tokens (excellence / impact / implementation) | 20,599 / 12,007 / 14,392 | frozen report `blind_baseline_f60ae6e0a2a1.json`, `criterion_scoring.scores[].input.token_estimate` |
| Jev state budget | 32,768 tokens (state plus longest question) | `docs.typesafe.ai/models` |
| Live assessor calls per blind pass | 45 (10 cells × 3 + 3 criteria × 5) | same report |
| Harness tests | 1,878 in `tests/harness/` (51 modules); 598 in `tests/test_msca_dn*.py` (12 modules) | `grep -c "def test_"` |
| Harness size | ~83k lines; largest modules `integrity_audit.py` 1,989, `esr_comparison.py` 1,950 | file counts at `0f2fa8b` |
