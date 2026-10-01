# Tickets: the demo's Phase 7 gate, and the blind lane's document route

Two independent tickets. Both unblock the demo ticket "Candidate Part B and the blind baseline",
whose findings are recorded in
`docs/tier4_orchestration_state/validation_reports/demo-candidate-blind-baseline_2026-10-01.json`.

They have no shared code and no shared artifact. Ticket B does not wait for ticket A.

Constraints that apply to both:

- `CLAUDE.md` governs. Ticket A runs under an operator override of three named rules, by the §1
  route. Neither ticket amends the constitution, so §14 is not engaged.
- The DAG scheduler, the node state machine and gate-evaluation authority are not modified.
- Tests run with `py -3.10`. Neither ticket dispatches a runner phase. The operator does.

---

## Ticket A — Make the Phase 7 gate pass on a fictional demo budget

**What to build:** One fictional budget response in
`docs/integrations/lump_sum_budget_planner/received/`, so `gate_09` passes and Phase 8 unblocks.
No code, no new budget regime, no constitutional amendment.

**The override.** The operator has instructed, in session, that `CLAUDE.md` is overridden for
this task. The rules overridden are §8.1 and §17.6.7, which reserve lump-sum computation to the
external planner, and §8.3, which forbids substituting an internally generated figure for an
absent response. §1 permits this: an explicit in-session instruction scoped to the instruction
that invokes it. It is not an amendment, so §14 is not engaged, and the override expires with
this ticket.

**Why it is this small.** `gate_09`'s lump-sum branch reads the response from `received/` through
four predicates: `g08_p02` directory non-empty, `g08_p04` contract conformance, `g08_p05` work
package coverage and `g08_p06` partner coverage. All four pass on a single file covering the 7
work packages and 12 partners. The remaining predicates read artifacts the Phase 7 node writes
itself, so nothing else is authored by hand.

**What the file must contain.** The four `response_schema` required fields, a `lump_sum` per work
package and a `total_effort_pm` per partner. Figures are fictional and declared so in the file.
Summing the work package figures to the 5,000,000 euro expected contribution in
`selected_call.json` keeps the fiction traceable to a Tier 2B number rather than arbitrary.

**What this costs.** Every Phase 8 figure then traces to fiction. §13.8 still binds, so a Tier 5
deliverable resting on one must say so. That is a label, not a gate.

**Blocked by:** nothing.

- [ ] A response in `received/` conforms to the interface contract, covers all 7 work packages
  and all 12 partners, and declares itself fictional in its own content.
- [ ] `g08_p02`, `g08_p04`, `g08_p05` and `g08_p06` pass on it. A test proves each.
- [ ] A Tier 4 decision record names the override, the three rules it suspends, who authorised
  it, and that it expires with this ticket.
- [ ] The records that pin an empty `received/` are updated, not left contradicting the branch:
  the demo ticket's validation report, its decision record, its Outcome, and the four tests in
  `tests/test_demo_candidate_blind_baseline.py` that assert the blocking state.
- [ ] Tier 5 content derived from this budget carries the fictional label.
- [ ] After the operator dispatches Phase 7, the node writes `validation/` and
  `budget_gate_assessment.json`, and `gate_09` reaches pass. Recorded, not assumed.

**Not in this ticket.** A real internal budget route needs a §14 amendment, an operator-approved
effort estimate, a declared cost model and a deterministic component under byte-equal replay.
That was the earlier draft of this ticket. It is the right shape for a live proposal and the
wrong shape for a demo, so it is dropped rather than carried as scope.
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
