# Evaluation & Integrity Harness

Out-of-band evaluation of proposal text and the evidence behind it, by a model independent of the
one that drafted it. Every output here is advisory to a human; nothing here is a runtime gate.

## Language

### Roles

**Judge**:
The pinned, independent model that returns verdicts and scores. It is never the drafter's model
family, and its verdicts are at most Inferred, never Confirmed.
_Avoid_: grader, reviewer, LLM-as-judge

**Assessor**:
The judge in the role of scoring a candidate during a blind assessment, identified by its assessor
pin (model at version).
_Avoid_: evaluator, judge (when the blind-assessment role is meant)

**Drafter**:
The model family that wrote the text under evaluation. It may never judge or assess that text.
_Avoid_: generator, writer

**Evaluator**:
The external expert who scored a submitted proposal for the funding body; the author of an ESR.
_Avoid_: assessor, judge, reviewer

**Operator**:
The human who declares, approves and runs the private steps, and to whom every harness output is
advisory.
_Avoid_: user, reviewer

### What is assessed

**Candidate**:
One proposal text presented for assessment, as a set of section artifacts, identified by its
candidate hash.
_Avoid_: draft, submission (unless it was actually submitted)

**Imported candidate**:
A candidate that did not come out of the pipeline (e.g. the 2026 MSCA DN proposal), so its own claim
statuses are not trusted for grounding.
_Avoid_: external draft

**Candidate hash**:
The formatting-invariant content hash of a candidate. Every report and every scored cell is bound to
exactly one.

**Pre-evaluation profile**:
The versioned configuration a candidate is graded under: instrument, criterion-to-section map,
scorecard and rubric set. Any change to a component changes its version.
_Avoid_: config, scheme

**Historical profile**:
A pre-evaluation profile written for a past call, authored from a rule-equivalence matrix.

**Rule-equivalence matrix**:
The rule-by-rule mapping from a historical call's scoring rules to the call a profile serves; each
rule is sourced, defaulted or unresolved.
_Avoid_: authority matrix (outside file and command names)

**Scorecard**:
The scale, weights and thresholds of one evaluation form's criteria.

**Rubric set**:
The versioned rubrics the judge applies, each traceable to a scorecard criterion.

**Expectation**:
One thing an evaluator expects a section to address, taken from the evaluation form.
_Avoid_: requirement

**Coverage**:
Whether a section substantively addresses an expectation.
_Avoid_: addressal, completeness

**Grounding**:
Whether what a section claims is supported by its sources. Coverage and grounding are always reported
as two separate values, never blended into one score.
_Avoid_: faithfulness (that is the per-claim question)

**Criterion score**:
The holistic 0–5 score for one evaluation criterion.

**Evidence pack**:
The deterministic, size-bounded set of passages the judge is shown for one question.
_Avoid_: context, prompt input

**Grounding scope**:
What a blind assessment declares it assessed for grounding, stated beside what was actually measured.

**Draw**:
One response from the judge to one prompt, live or replayed from the response checkpoint.
_Avoid_: call, sample (a sample is one accepted draw in a majority vote)

**Discarded draw**:
A draw the parser rejected as malformed. It is recorded with its reason, never repaired, and asked
again over the identical prompt within a bounded budget.
_Avoid_: retry, failed call

**Leakage**:
Any historical feedback (ESR findings, scores, target scores, repair plans) reaching the assessor.
It is refused before any assessor call.

### Integrity signals

**Claim ledger**:
The record of every material claim a section makes, each with its evidence status (Confirmed,
Inferred, Assumed, Unresolved).
_Avoid_: claim list

**Escaped claim**:
A material claim present in the text but missing from the claim ledger.

**Materiality**:
Whether a claim bears on how an evaluator would score the proposal.

**Faithfulness**:
The atomic question "does this source support this claim?".
_Avoid_: grounding (that is the section-level axis)

**Status-aware faithfulness**:
Whether a claim's declared status matches what its source supports — the detector for a gap masked as
Confirmed.

**Gold set**:
Human-labelled faithfulness examples against which the judge is calibrated.

**Calibration**:
Measuring the judge's reliability against a gold set; only a calibrated check may move from advisory
toward gating a decision about the pipeline.

**Advisory**:
The standing of every harness output: a human decides what to do with it.
_Avoid_: gate, blocking, pass/fail

### Blind assessment and DN pre-evaluation

**Blind assessment**:
Scoring one candidate under one pre-evaluation profile with one pinned assessor, without the
pipeline and without any historical feedback.
_Avoid_: blind lane, blind run, pre-eval lane

**Blind report**:
The bound output of one blind assessment. It is partial when the candidate lacks required sections.

**Blind baseline**:
A blind report that has been checked, copied and frozen before any ESR is read.
_Avoid_: baseline (on its own)

**Integrity audit**:
The consistency checks run over a blind report's parsed rows.

**ESR**:
The Evaluation Summary Report: the funding body's scores and comments on a submitted proposal.

**ESR intake**:
The recorded availability of an ESR (unknown, unavailable, not applicable, available). It is
declared, never derived.

**ESR comparison**:
A blind baseline set against an ESR, one row per ESR observation, with scores compared separately.

**Operator review**:
An ESR comparison rendered for the operator, with the operator's agreement declared.

**Stage A**:
Historical validation: a blind assessment of the submitted original under its historical profile,
frozen before the ESR is read, to test whether the harness reproduces the ESR.
_Avoid_: historical run

**Stage B**:
Final resubmission: an advisory pre-evaluation of the revised proposal under the profile of the call
it will be submitted to.

**PE-09**:
The operator's execution of Stage A and Stage B in the approved private environment. It is never
executed in this repository.

**Execution receipt**:
The operator's readiness statement before a private run, read and checked but never trusted on its
own say-so.
_Avoid_: readiness checklist

**Deferral register**:
Every item an approval left open, and what closes it.

**Record binding**:
Tying a successor record to the records it reads, by the hash of their bytes.

### Assurance

**Acceptance lane**:
A named test suite reconciled against its own declaration of coverage areas and exclusions. Green
says the code behaves as its fixtures specify; it says nothing about calibration.
_Avoid_: lane (for any assessment flow), test run

**Declared exclusion**:
A check an acceptance lane deliberately does not run, named with its reason and the work that would
lift it.

**Regression golden-set**:
Frozen baselines of the current sections, so a prompt or model change cannot silently regress them.

## Relationships

- A **blind assessment** grades one **candidate** under one **pre-evaluation profile** with one **assessor**.
- A **blind baseline** is frozen from a **blind report**; an **ESR comparison** reads one blind baseline and one **ESR**.
- **Stage A** and **Stage B** are both run by the **operator** as **PE-09**; the **PE-09 acceptance lane** is the test suite that must be green before it.
- **Coverage** and **grounding** are the two axes of an **expectation**; **faithfulness** is the per-claim question beneath grounding.
