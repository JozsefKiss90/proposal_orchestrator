# Tickets: internal budget derivation, and the blind lane's document route

Two independent tickets. Both were raised as findings by the demo ticket "Candidate Part B and
the blind baseline", recorded in
`docs/tier4_orchestration_state/validation_reports/demo-candidate-blind-baseline_2026-10-01.json`.

They have no shared code and no shared artifact. Ticket B does not wait for ticket A.

Constraints that apply to both:

- `CLAUDE.md` governs. Ticket A changes it, by the §14 amendment route and no other.
- The DAG scheduler, the node state machine and gate-evaluation authority are not modified.
- The categorical Phase 8 block (§8.4, §13.4) is preserved verbatim. Neither ticket weakens it.
- Tests run with `py -3.10`. Neither ticket dispatches a runner phase.

---

## Ticket A — Internal budget derivation for a call with no external planner

**Why this is an amendment.** There is no external Lump Sum Budget Planner. The repository has
never held a transport for one: no subprocess call, no HTTP client, no URL, no script. §8.1,
§8.3 and §17.6.7 nonetheless reserve lump-sum computation to that system, and §13.3 forbids an
agent inventing a budget figure. An agent computing the budget is therefore inadmissible under
`CLAUDE.md` as written. §14.1 makes a change of constitutional meaning through code alone
invalid. So the amendment is the first deliverable, not a footnote to the code.

**The precedent to follow.** The C1 amendment already did this once, for unit-cost instruments.
Its argument is the one to reuse: §8 externalises lump-sum budgeting because lump-sum figures
carry un-replayable judgment, and externalisation is the anti-fabrication guarantee. Where that
guarantee can be supplied another way, externalisation adds nothing. `runner/unit_cost_budget.py`
is the shape of the answer: a pure arithmetic core that is the byte-equal CI target, plus a
deterministic component the agent runtime invokes in the n07 node body (§17.5.3).

**Why unit-cost's guarantee is not enough on its own.** A unit-cost budget is fixed arithmetic
on published constants, so determinism closes it completely. A lump sum has no published
constants. Two inputs carry real judgment: the effort in person-months per task and partner,
and the cost model that turns effort into euros. Determinism cannot launder either. So the
guarantee has to be split.

**What to build:** A third budget regime, `derived_lump_sum`, whose figures come from two
operator-approved judgment inputs and one deterministic transform.

1. **The judgment layer.** A skill estimates effort person-months per task, per partner, from
   the Phase 3 work package structure and the Phase 4 Gantt. It writes a proposal, never a
   budget. Every line carries its §12.2 status and its reasoning. The artifact is inert until
   the operator approves it, on the pattern the concept approval already uses.
2. **The cost model.** Personnel rates, overhead treatment and other direct cost categories are
   declared by the operator in Tier 3, each with a §12.2 status. No agent writes a rate. An
   absent rate is `Unresolved` and blocks, exactly as the host coefficient does today.
3. **The deterministic layer.** A new component multiplies approved effort by declared rates and
   writes the budget. It performs no reasoning, invokes no Claude, and is closed by a byte-equal
   replay check. It is bound in the manifest per §16.5, as C3 requires.

The existing `lump_sum` regime stays exactly as it is, for a project that does have a planner.
The amendment adds a route and removes none. Say so if you want the external route retired
instead — that is a larger change and a different ticket.

**Blocked by:** nothing.

- [ ] The amendment record is written into `CLAUDE.md` §8, naming every section it touches:
  §8.1, §8.3, §8.4, §17.6.7, §7 Phase 7, §5's integration constraints. §14.2 lists the five
  fields each amendment must carry.
- [ ] §14.4 is satisfied. No section of the amended constitution contradicts another, and the
  §13.3 prohibition on invented project facts still reads true.
- [ ] `VALID_BUDGET_REGIMES` carries `derived_lump_sum`, and `resolve_budget_regime` returns it
  from the Tier 3 call binding.
- [ ] `gate_09` gains an `applies_when: {budget_regime: derived_lump_sum}` predicate set. The
  lump-sum and unit-cost sets are untouched and their tests still pass.
- [ ] The effort estimate is a Tier 3 artifact with a §12.2 status per line. An unapproved
  estimate fails the gate. A test proves the gate blocks on it.
- [ ] The cost model is operator-declared. A test proves no agent can write a rate, and that an
  absent rate is `Unresolved` rather than defaulted.
- [ ] The deterministic component replays byte-equal from its inputs, under a CI check that
  names the figure.
- [ ] The categorical Phase 8 block still holds. Every budget component must resolve to
  Confirmed or operator-declared Assumed before `gate_09` passes.
- [ ] `budget_request.json` carries a real run identifier. It currently holds the literal string
  `import uuid; print(uuid.uuid4())`, and the same string names two decision log files.

---

## Ticket B — Make the blind lane's document route usable by a shipped profile

**What to build:** The blind pre-evaluation lane's dev-graph document route, so that it can
grade a candidate under the RIA or MSCA-PF profile. It cannot today, for either.

**The defect, F1.** `harness.blind_assessment.materialise_candidate` writes one sub-section per
passage and names it for its section, so `excellence_section.json` holds one sub-section called
`excellence_section`. The RIA rubrics anchor on `B.1.1` to `B.3.2` and the MSCA-PF rubrics on
`1.1` to `3.2`. `build_evidence_pack` raises on the first absent anchor, nothing on the
`assess_candidate` path catches it, and no report is written. The `partial` label covers a
missing section only. There is no partial mode for a missing anchor.

**Why no test caught it.** The document route's own tests use a synthetic profile whose anchors
are its section ids. The profile tests use the directory route, with a candidate built from the
rubric anchors. No test crossed the two. The failing case now exists, at
`tests/test_demo_candidate_blind_baseline.py::TestTheDocumentRouteCannotFeedTheRiaProfile`.

**What the anchor is for.** It is a score bonus of 2, not a content requirement. Its purpose is
that the sub-section dedicated to an expectation outranks a stray term match elsewhere in the
section. It fails closed when absent so the mapping can never silently stop ranking. A fix must
keep that purpose, not just stop the exception.

**The chosen shape: the document record declares its sub-sections.** A section carries an
optional `sub_sections` list. The builder derives a passage per sub-section. The materialiser
preserves them instead of synthesising one. Phase 8 already drafts at this granularity, under
`phase_outputs/phase8_drafting_review/section_drafts/`, so the structure is preserved rather
than invented.

The rejected alternative was a profile-declared passage-to-anchor map. It changes no document
schema, which is cheaper. It also makes every paragraph in a section an anchor, which destroys
the ranking signal and converts a fail-closed check into a vacuous pass.

**Blocked by:** nothing.

- [ ] `sub_sections` is optional on a document section, so an existing record keeps its current
  behaviour. Check the `milestone_2` and `graph` branches for records before relying on that.
- [ ] A document whose sections declare sub-sections grades under the real RIA profile, through
  the document route, and the report carries the candidate hash, profile version and assessor
  pin.
- [ ] The anchor map still fails closed. A declared anchor absent from the candidate still
  raises, and a test proves it.
- [ ] The same candidate grades under the MSCA-PF profile.
- [ ] F2 closes with it. An ESR intake can be stamped on the resulting report, and
  `demo-biodiv-2027-part-b-v1` is the record to try it with.
- [ ] The existing document-route and profile tests pass unchanged.
- [ ] The demo's F1 reproduction test is inverted, from a recorded defect into a passing case.

---

## Also recorded, and not ticketed here

Two findings from the same report need no ticket of their own yet.

- **F3.** `record_esr_intake` demands a `submission_id` for a document that was never submitted,
  with no way to declare the absence. The demo records the sentinel `NOT_SUBMITTED`. Fold this
  into ticket B if the intake is touched there anyway.
- **F6.** A clean leakage-guard pass can be vacuous. The demo's six blind packages hold no
  passage, claim or commitment item, which are the three types a historical-feedback tag rides
  on. Ticket B gives the guard something real to check.
