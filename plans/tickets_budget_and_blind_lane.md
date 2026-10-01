# Tickets: the demo's Phase 7 gate, and the blind lane's document route

Two independent tickets. Both unblock the demo ticket "Candidate Part B and the blind baseline",
whose findings are recorded in
`docs/tier4_orchestration_state/validation_reports/demo-candidate-blind-baseline_2026-10-01.json`.

They have no shared code and no shared artifact. Ticket B does not wait for ticket A.

Constraints that apply to both:

- `CLAUDE.md` governs. Ticket A runs under an operator override of six named clauses, by the §1
  route. Neither ticket amends the constitution, so §14 is not engaged.
- The DAG scheduler, the node state machine and gate-evaluation authority are not modified.
- Tests run with `py -3.10`. Neither ticket dispatches a runner phase. The operator does.

---

## Ticket A — Make the Phase 7 gate pass on a fictional demo budget

**What to build:** One fictional budget response in
`docs/integrations/lump_sum_budget_planner/received/`, so `gate_09` passes and Phase 8 unblocks.
No code, no new budget regime, no constitutional amendment.

**The override.** The operator has instructed, in session, that `CLAUDE.md` is overridden for
this task. §1 permits this: an explicit in-session instruction scoped to the instruction that
invokes it. It is not an amendment, so §14 is not engaged, and the override expires with this
ticket.

**Six clauses, not three.** This ticket first named §8.1 and §17.6.7, which reserve lump-sum
computation to the external planner, and §8.3, which forbids an internally generated substitute.
The code review found that understated. A hand-authored response also breaches §5's integration
constraint, §8.4's lump-sum *source* clause with §7's restatement of it, and §13.3's
budget-figure item. §8.4's *categorical Phase 8 block* is a different sentence and is not
suspended. Nor is §13.3's list of every other project fact.

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

- [x] A response in `received/` conforms to the interface contract, covers all 7 work packages
  and all 12 partners, and declares itself fictional in its own content.
- [x] `g08_p02`, `g08_p04`, `g08_p05` and `g08_p06` pass on it. A test proves each.
- [x] A Tier 4 decision record names the override, every clause it suspends, who authorised it,
  and that it expires with this ticket.
- [x] Nothing on the branch is left contradicting it. That reached further than this box first
  said: both demo tickets' validation reports, both decision records, both Outcomes, and the
  two test modules that assert the blocking state.
- [ ] Tier 5 content derived from this budget carries the fictional label.
- [ ] After the operator dispatches Phase 7, the node writes `validation/` and
  `budget_gate_assessment.json`, and `gate_09` reaches pass. Recorded, not assumed.
  The operator dispatched on 2026-10-01. The node failed at `agent_body`, the gate was
  never evaluated, and the cause was an engine defect rather than the budget. Fixed
  below; the box stays open until a gate result exists.

**Not in this ticket.** A real internal budget route needs a §14 amendment, an operator-approved
effort estimate, a declared cost model and a deterministic component under byte-equal replay.
That was the earlier draft of this ticket. It is the right shape for a live proposal and the
wrong shape for a demo, so it is dropped rather than carried as scope.

**Outcome: four of six, and the last two are not mine to close.** One file was written,
`budget_response_FICTIONAL_demo_2026-10-01.json`, and no code changed. The four predicates that
read `received/` pass on it, each proved by its own test. The override is recorded in
`demo-fictional-budget-override_2026-10-01.json`. Tier 5 is still empty, so no §13.8 label is
due yet, and a test fails the moment Phase 8 writes a section. The gate passes only after the
operator dispatches Phase 7. No runner phase was dispatched and no gate result was written.

**What the gate cannot see.** `g08_p05` and `g08_p06` count identifiers, so they passed the
moment a file covering 7 work packages and 12 partners appeared. `g08_p04` cannot reject a
non-numeric figure, because the contract declares no type for `lump_sum` (G3). None of the three
can tell a fictional figure from a planner's. That is what §8.1 was carrying, and why suspending
it took a human instruction rather than a code change. G1 and G2 are also recorded unfixed: the
leakage scan does not reach `docs/integrations/`, and `budget_request.json` holds a Python
snippet where its `run_id` belongs. Forty-five new tests.

**What actually blocked the gate, and it was not the budget.** The operator dispatched
Phase 7 on 2026-10-01. n07 ended `blocked_at_exit` with `failure_origin: "agent_body"`,
`exit_gate_evaluated: false`, and all six Phase 8 nodes on `hard_block_upstream`.
`gate_09` was never evaluated. The `budget-interface-validation` skill declared
`gate_pass_declaration: "pass"` and named a validation artifact it never wrote, so
`_determine_can_evaluate_exit_gate` found `validation/` holding only `.gitkeep` and
§17.3.2 skipped the gate. The skill could not write it: its catalog entry carried no
`output_contract`, the artifact had no schema, the sections the runtime searched stopped
at Tier 2A, and the multi-artifact prompt directive existed only in the TAPM assembler.
All four are fixed, recorded in
`decision_log/demo-n07-validation-artifact-contract_2026-10-01.json`, with 20 tests. The
validation artifact was **not** hand-authored: that would have passed `g08_p03` on a file
no skill produced, which is the fabricated completion §15 forbids and the thing §17.6.6
exists to catch.

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

- [x] `sub_sections` is optional on a document section, so an existing record keeps its current
  behaviour. Check the `milestone_2` and `graph` branches for records before relying on that.
- [x] A document whose sections declare sub-sections grades under the real RIA profile, through
  the document route, and the report carries the candidate hash, profile version and assessor
  pin.
- [x] The anchor map still fails closed. A declared anchor absent from the candidate still
  raises, and a test proves it.
- [x] The same candidate grades under the MSCA-PF profile.
- [x] F2 closes with it. An ESR intake can be stamped on the resulting report, and
  `demo-biodiv-2027-part-b-v1` is the record to try it with.
- [x] The existing document-route and profile tests pass unchanged.
- [x] The demo's F1 reproduction test is inverted, from a recorded defect into a passing case.

**Outcome: seven of seven.** Two functions changed and nothing else. `_section` in
`runner/dev_graph/documents.py` normalises an optional `sub_sections` list, and
`materialise_candidate` emits it when present. The builder needed no edit: it already copies
every section field onto the passage node. 22 new tests in
`tests/harness/test_blind_document_subsections.py`.

**Optional had to mean hash-stable.** A section declaring none normalises without the key, and
an empty list normalises to absent too. Otherwise one document would hash two ways depending on
how its author spelled "none", and every stored `content_version` would move. No document record
exists on any branch, so nothing stored was at risk, but the synthetic fixture's node ids were.

**The span had to grow with it.** `render_document` now renders each sub-section as a
third-level block inside its section's span. A span that stopped at the section's own content
would point at text omitting the section's dedicated answers, which is what the anchor ranks.

**One departure from this ticket as written.** It said the builder derives a passage per
sub-section. That would break the materialiser, which writes one artifact per passage named for
its section, so two sub-sections of one section would collide on a filename. It would also
re-point every claim-to-passage edge. The passage stays per section and carries its
sub-sections, which is what the evidence pack reads anyway.

**The agnosticism lint earned its keep.** A first draft of the `materialise_candidate` docstring
named RIA and MSCA-PF, and `test_harness_python_carries_no_instrument_name` failed. Which ids a
profile anchors on is the profile's business, never the harness's.

---

## Also recorded, and not ticketed here

Two findings from the same report need no ticket of their own yet.

- **F3.** `record_esr_intake` demands a `submission_id` for a document that was never submitted,
  with no way to declare the absence. The demo records the sentinel `NOT_SUBMITTED`. Fold this
  into ticket B if the intake is touched there anyway.
- **F6.** A clean leakage-guard pass can be vacuous. The demo's six blind packages hold no
  passage, claim or commitment item, which are the three types a historical-feedback tag rides
  on. Ticket B gives the guard something real to check.
