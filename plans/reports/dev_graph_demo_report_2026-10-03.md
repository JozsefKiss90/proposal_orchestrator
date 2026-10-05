# Dev Graph demo report: instance two on HORIZON-CL6-2027-01-BIODIV-01

Branch `dev_graph_demo`, written 2026-10-03 at commit `c23666e`, 41 commits after the base commit
`f40753d`. The demo ran the Milestone 1 dev graph on a full-size real call instead of the synthetic
fixture. It was never submitted and its consortium is anonymised. Every number below is read from a
Tier 4 artifact named in the same section, and `tests/test_demo_report.py` re-derives the load-bearing
ones from those artifacts.

## The four scope questions, answered

The scope record `decision_log/dev-graph-demo-scope_2026-09-29.json` fixed four questions.

| Question | Answer | Evidence |
|---|---|---|
| Does the snapshot build on real Tier 2B and Tier 3 records, and twice to the same id? | Yes. 116 nodes and 305 edges from five Tier 3 records on 30 September, 267 nodes and 455 edges once the Part B candidate was imported. Two builds agree byte for byte, and the check mode reproduces all 38 artifacts. | `validation_reports/demo-dev-graph-snapshot_2026-09-30.json`; `dev_graph/demo_snapshot_summary.json` |
| Do evidence packages stay within the default budget, and which go incomplete and why? | No. All 18 packages are incomplete at the default budget of 3000 estimated tokens. The mandatory set alone costs 5,411 to 21,885. The budget, not the view policy, decides what is left out: 1,224 over-budget exclusions against 38 not-relevant and 5 policy-forbidden. | `validation_reports/demo-dev-graph-snapshot_2026-09-30.json`, its packages field; `dev_graph/demo_snapshot_summary.json`; §3 below |
| Does the shadow planner agree with real reruns, and is every narrower case investigated? | Not measurable on a real rerun. All 18 comparisons against the two real runs refused, because the scheduler never persists a `not_reused` decision. On a declared synthetic run the planner was narrower on 3 of 6 rows; the cause is recorded as a granularity disagreement, not an error of fact. | `decision_log/demo-change-scenarios_2026-10-02.json`; `decision_log/demo-change-scenarios-synthetic-rerun_2026-10-02.json` |
| Does the blind lane stay leak-free when the candidate and its history are real? | Yes, over the one candidate that exists. The 151-item package around candidate version 1 passes the leakage guard. The blind report binds candidate hash, profile version and assessor pin on every cell. The branch-wide scan reports no new leak over 336 files (re-derived 2026-10-05 after PE-01 to PE-07 added fourteen Tier 3/4 records; the 2026-10-03 scan saw 322). | `validation_reports/demo-candidate-blind-baseline_2026-10-01.json`; `harness/blind_reports/blind_e518c50023ee_0001.json` |

The demo closes with three of its four questions answered on real records and the third answered
on a declared synthetic run. What blocks the real answer is one dispatch and subticket D, both
operator acts.

## 1 · What was built

| Layer | State at `c23666e` | Record |
|---|---|---|
| Tier 2B | Part 9 PDF, portal topic JSON, call extract and slice for BIODIV-01; `extracted/` written by Phase 1 | `validation_reports/tier2b-biodiv-intake_2026-09-29.json` |
| Tier 1 and 2A | RIA participation rule and evaluator entry filled from the forms with page references | `validation_reports/tier1-tier2a-ria-coverage_2026-09-29.json` |
| Tier 3 | 12 pseudonymous partners, 6 objectives, 7 work packages, 35 tasks, 24 deliverables, 8 milestones, 24 sources; every partner Assumed; frozen and refrozen four times | `decision_log/demo-architecture-seeds_2026-09-30.json` and the four freeze records |
| Runner | Two full Phase 1 to 6 runs; Phase 7 and all six Phase 8 nodes released under the second run; 14 gate results, all pass, 143 predicates passed | `run_records/`, `phase_outputs/*/gate*_result.json` |
| Tier 5 | Three proposal sections, one assembled draft, one final export, one review packet, one candidate | `docs/tier5_deliverables/` |
| Dev graph | 4 snapshot generations, 72 package directories for 18 live packages, 7 change scenarios, 2 shadow comparisons, 1 enacted change, 1 declared synthetic rerun | `docs/tier4_orchestration_state/dev_graph/` |
| Harness | RIA pre-evaluation profile; one blind report over candidate version 1 | `validation_reports/ria-pre-evaluation-profile_2026-10-01.json` |

Sixteen tickets carried the work: fourteen in `plans/dev_graph_demo_tickets.md` and two in
`plans/tickets_budget_and_blind_lane.md`. Before this report, 58 acceptance boxes were ticked and 22
open. Fourteen of the open boxes sit in the five subtickets of the change-scenarios ticket, and the
rest are recorded gaps named in §8.

## 2 · Snapshot on real records

| Measure | Value | Source |
|---|---|---|
| First snapshot (30 Sep) | 116 nodes, 305 edges, 7 node types, from 5 Tier 3 records | `decision_log/demo-dev-graph-snapshot_2026-09-30.json` |
| Current snapshot (2 Oct) | 267 nodes, 455 edges, 10 node types; 147 claims, 3 passages and 1 artifact version arrived with the candidate | `dev_graph/demo_snapshot_summary.json` |
| Generations | 4: first build; sources index refreeze after Phase 1; candidate import; the enacted month move | package manifests, dated by `git log` |
| Determinism | Two builds give one id; `tools.build_demo_dev_graph --check` finds 38 of 38 artifacts up to date | the check, run 2026-10-03 |
| Build time | 0.02 s for the snapshot in process; 5.1 s for the full check including 18 packages and interpreter start | measured 2026-10-03, three runs |
| Fail-closed errors on first build | None. The one defect was a fail-open: manifests rolled up Confirmed over all-Assumed records until each node type's own status field was read | snapshot report F1 |

Three of the six architecture seeds are not indexed, because no node type exists for an outcome,
an impact or a risk (snapshot report F3). The builder reads neither the uncertainty ledger nor the
roles registry (F5, F6).

## 3 · Packages within budget

Eighteen packages: six view policies over three seed tasks, at the default budget of 3000. All
eighteen are incomplete and every one reports Assumed as its worst declared status. 248
not-confirmed items are listed across them.

| Task | View | Included | Mandatory | Over budget | Of which required | First item that did not fit |
|---|---|---|---|---|---|---|
| T3.1 | blind_pre_evaluation | 16 | 54 | 77 | 39 | D1.1 |
| T3.1 | change_impact_planning | 16 | 68 | 91 | 53 | D1.1 |
| T3.1 | controlled_revision | 16 | 34 | 46 | 19 | D1.1 |
| T3.1 | engineering | 16 | 54 | 83 | 39 | D1.1 |
| T3.1 | historical_feedback_analysis | 16 | 34 | 47 | 19 | D1.1 |
| T3.1 | integrity_audit | 16 | 54 | 83 | 39 | D1.1 |
| T4.1 | blind_pre_evaluation | 17 | 58 | 79 | 43 | D1.1 |
| T4.1 | change_impact_planning | 17 | 67 | 90 | 51 | D1.1 |
| T4.1 | controlled_revision | 17 | 29 | 42 | 14 | D2.3 |
| T4.1 | engineering | 17 | 58 | 84 | 43 | D1.1 |
| T4.1 | historical_feedback_analysis | 17 | 29 | 43 | 14 | D2.3 |
| T4.1 | integrity_audit | 17 | 58 | 84 | 43 | D1.1 |
| T1.1 | blind_pre_evaluation | 9 | 16 | 72 | 8 | D1.1 |
| T1.1 | change_impact_planning | 9 | 45 | 98 | 37 | D1.1 |
| T1.1 | controlled_revision | 10 | 7 | 26 | 1 | O2 |
| T1.1 | engineering | 9 | 16 | 76 | 8 | D1.1 |
| T1.1 | historical_feedback_analysis | 10 | 7 | 27 | 1 | MS8 |
| T1.1 | integrity_audit | 9 | 16 | 76 | 8 | D1.1 |

Why they go incomplete: the mandatory walk of a real work plan costs three to eight times what the
synthetic fixture's did. The minimum budget for the mandatory set is 5,411 to 21,885 and for full
completeness 9,597 to 25,495. The two depth-2 views need about half the budget of the depth-3 and
depth-4 views on the same seed, so the policies do bite. At 3000 the budget hides them: only 5
exclusions are policy-forbidden, in three packages, and none on the densest seed. The budget of 3000
was adopted from the harness for want of a second value and is recorded as Assumed. Source:
`validation_reports/demo-dev-graph-snapshot_2026-09-30.json`, fields `packages` and `findings` F2, F7,
F8; current figures from `dev_graph/demo_snapshot_summary.json`.

## 4 · Planner agreement with reruns

Seven scenarios were scripted, the six the ticket names and one probe for a protected objective.
They hold twelve arms, one more than the parent record counted, because the enactment split the
month move into two. Nine recorded a change and produced an advisory whose every entry carries a
reason path. Three are refusal probes that refused as expected.

| Scenario | Arms | Contract verdict | Advisory | Comparison against the two real runs |
|---|---|---|---|---|
| task_lead_moves | 1 change | flagged_for_review (no partner capacity confirmed) | yes | 2 refused, `no_reuse_decision` |
| gap_partner_withdraws | 1 probe, 2 changes | probe refused `dangling_edge`; both changes accepted | yes, 2 | 4 refused |
| gap_partner_confirmed | 1 change, 1 probe | accepted; probe refused `malformed_request` (ledger not covered) | yes, 1 | 2 refused |
| claim_loses_its_span | 1 change | accepted; advisory has no origin to walk from (F5) | yes | 2 refused |
| tier2b_fact_changes | 1 probe, 1 change | probe refused `malformed_request` (call binding not covered); proxy arm accepted | yes, 1 | 2 refused |
| deliverable_month_moves | 2 changes, enacted on the world | accepted, both | yes, 2 | 4 refused; see the synthetic run below |
| protected_objective_probe | 1 change | rejected, names O1 | yes | 2 refused |

Eighteen comparisons, eighteen refusals. Half name the Phase 8 run, whose id is a pasted shell
command. Before subticket A the reader rejected that id outright (F1); it now reads the preserved
copy by slug and refuses on the same ground as the other half. All eighteen refuse because no run
manifest in this world holds a reuse decision: the scheduler persists one only on the reuse branch
(F2). Source:
`decision_log/demo-change-scenarios_2026-10-02.json`, `dev_graph/change_scenarios/*/scenario.json`.

One scenario was enacted on the live world through the change recorder: D3.2 and MS4 moved from
month 28 to month 29 as two arms, because the work plan's own timing rule rejects moving the
deliverable alone. The snapshot moved from `706fe54f` to `68c0a8b7`, the prior record versions are
archived and the replay reproduces both. Source:
`decision_log/demo-change-scenarios-subticket-b_2026-10-02.json`.

The rerun half was then demonstrated on a declared synthetic run, `synthetic-rerun-2026-10-02`. Its
manifest says it was never dispatched. Its reuse decisions were derived by the reuse layer over the
live world, not typed: `not_reused`, `fingerprint_mismatch`, for all three drafting nodes.

| Arm | n08a excellence | n08b impact | n08c implementation | Arm diagnostic |
|---|---|---|---|---|
| a1 move D3.2 | planner reuse, scheduler rerun: **planner_narrower** | agreed (rerun) | agreed (rerun) | planner_narrower |
| a2 move MS4 | **planner_narrower** | **planner_narrower** | agreed (rerun) | planner_narrower |

Three narrower rows of six, no broader row. The investigation finds a granularity disagreement. The
scheduler fingerprints the whole Tier 3 directory, so any due-month change invalidates every
section. The planner traces record-level inputs and reaches the excellence and impact sections
only transitively, through T3.2, P08, D6.1, T6.1, P03 and the MS4 validation edge. No reuse policy
exists for this world, so the scheduler's rerun stays operative. Subticket D would persist this
verdict, not change it. Source: `dev_graph/change_scenarios/deliverable_month_moves/reruns/synthetic-rerun-2026-10-02.json`;
`decision_log/demo-change-scenarios-synthetic-rerun_2026-10-02.json`.

## 5 · The blind lane on a real candidate

| Measure | Value |
|---|---|
| Candidate | `DEMO-BIODIV-2027_part_b@1101b2a6`, imported from the three Phase 8 sections, 147 claims, 3 passages linked by span |
| Package | 151 items, passes the leakage guard; the earlier 6 demo-world packages held 0 passages and so proved nothing (F6) |
| Report | `blind_e518c50023ee_0001.json`, profile `ria_default`, scope complete, pin `claude-sonnet-5@claude-cli-subscription@2026-10-02`, bindings repeated on all six cells |
| Cells | excellence 0.350 and 0.547, impact 0.780 and 0.797, implementation 0.323 and 0.283; two of six pass; grades are advisory |
| Why four fail | every one of the 147 claims reaches the assessor with an empty `source_ref` (F12), and every person-month in the implementation tables reads not agreed or TBD over an all-Assumed Tier 3 (F13, not a defect) |
| Branch scan | `runner.leakage_scan` over 326 files (re-derived 2026-10-04 after PE-01 and PE-02 added four Tier 3/4 records; the 2026-10-03 scan saw 322): no new leak; 11 pre-existing hits, all in the 22 September purge record, which names the project it purged |

Source: `validation_reports/demo-candidate-blind-baseline_2026-10-01.json`, criteria 2 to 4 and
findings F6, F12, F13.

## 6 · Fail-closed and fail-open on real records

What refused correctly, and what accepted something it should not have.

| Kind | What happened | Status | Record |
|---|---|---|---|
| Fail-closed | Candidate builder refused the real Part B: no mapping for an `assumed` claim, then duplicate claim ids across sub-sections | fixed | blind baseline F7, F8 |
| Fail-closed | Document route raised on the RIA profile's first anchor: one sub-section per section against `B.1.1` anchors | fixed by `sub_sections` | blind baseline F1, F2 |
| Fail-closed | Change recorder refused a partner withdrawal while the work plan still named the partner (`dangling_edge`), and refused the call binding and the ledger (`malformed_request`) | by design, recorded | change scenarios D3, F3, F7 |
| Fail-closed | Shadow comparison refused all 16 real comparisons; CLI exits 3 on a non-plain run id | by design; D pending | change scenarios F1, F2; subticket A |
| Fail-closed | Assessor rejected key printed a traceback instead of exit 2 | fixed | blind baseline F10 |
| Fail-open | Package manifests rolled up Confirmed over all-Assumed records | fixed | snapshot F1 |
| Fail-open | `g08_p04` read the interface contract as a JSON Schema and accepted every payload, including a non-budget | fixed | budget request F1 |
| Fail-open | Both Phase 7 budget components wrote on a call whose budget regime did not resolve | fixed | budget request F9 |
| Fail-open | `phase_01_gate` passed 17 of 17 while Phase 1 destroyed the MSCA-PF entry in a shared Tier 2A registry | repaired by restore, not fixed | phases 1 to 6 F13 |
| Fail-open | Phase 1 wrote five paraphrased expected impacts and marked four Confirmed | rerun; Tier 2B extract corrected | phases 1 to 6 F3, F4 |
| Fail-open | `phase_01_gate`'s twelve Tier 2B predicates passed on another call's `extracted/` before Phase 1 ran | unresolved (I1) | Tier 2B intake |
| Fail-open | `g02_p15` cannot detect a missing RIA evaluator entry; `g08_p04` cannot reject a non-numeric figure | unfixed | coverage F3; override G3 |
| Fail-open | First leakage scan reported the branch clean while the purged project's acronym stood in Tier 4 eleven times | fixed; the hits are now listed as pre-existing | consortium F8 |
| Fail-open | A provider's free-tier rate limit set the evidence-pack ceiling and predetermined every grade | fixed | blind baseline F9 |
| Fail-open | Nothing validated `--run-id`; the pasted command text became a run id in 18 Tier 4 artifacts | run id rule added at the comparison; dispatch still unvalidated (M2) | phases 1 to 6 F11 |

## 7 · Run cost

Two Phase 1 to 6 runs, one Phase 7 and Phase 8 run. Token counts are the benchmark layer's own
estimates. No provider rate was priced, so the monetary cost is Unresolved and no figure is
substituted. Attribution of invocations to phases is Inferred from gate times, because the ledger
carries no node id (phases 1 to 6 F1). Source: `run_cost/*.json`,
`decision_log/demo-n07-validation-artifact-contract_2026-10-01.json` G4.

| Run | Phases | Invocations | Estimated tokens | Wall-clock | First to last invocation |
|---|---|---|---|---|---|
| `d68acaef` (30 Sep, first run) | 1 to 6 | 27 | 575,107 | 3,108 s | 4,835 s |
| `import uuid; …` (30 Sep, rerun) | 1 to 6 | 27 | 585,786 | 3,043 s | 4,894 s |
| same run, 1 to 2 Oct | 7 and 8, unattributed by the tool | 41 | 994,968 | 5,707 s | 74,684 s across two days |
| of which Phase 7 (G4) | 7, two dispatches | 10 | 324,850 | 656 s | |
| of which Phase 8, by subtraction | 8, six nodes with offline gate fixes between dispatches | 31 | 670,118 | 5,051 s | |

Per phase on the rerun: Phase 1 took 618 s of wall-clock, Phase 2 500 s, Phase 3 684 s, Phase 4
290 s, Phase 5 450 s and Phase 6 502 s. Phase 3 is the costliest at 152,913 tokens, driven by
instrument-schema normalisation and the milestone-consistency check reading 76,378 tokens of input.

## 8 · Defects as candidate Milestone 2 tickets

Every row is open on the branch and recorded in the named Tier 4 record. The first six carry the
ids the change-scenarios record gave them.

| Id | Candidate ticket | From |
|---|---|---|
| M1 | Persist the `not_reused` decision to the run manifest, so `planner_narrower` is detectable on a real run | change scenarios F2; subticket D |
| M2 | Validate the run id at dispatch, so a pasted argument cannot become a run directory | phases 1 to 6 F11; change scenarios F1 |
| M3 | Widen the change vocabulary to the call binding, Tier 2B and the uncertainty ledger; define what a ledger declaration leaving means for a §12.2 status | change scenarios F3, F9; subticket E |
| M4 | Join the Part B to the graph: addresses on passages, verified spans carried through the candidate builder, so `source_ref` reaches the assessor | change scenarios F4, F6; blind baseline F12 |
| M5 | Decide what a change to a non-indexed nested list means; today it is contained, has no origin and reports nothing changed | change scenarios F5 |
| M6 | Let one approved revision span more than one record | change scenarios F7; subticket B F1 |
| M7 | Teach the revision contract cross-record invariants, starting with milestone-after-deliverable timing | subticket B F1 |
| M8 | Attribute each invocation to its node in the benchmark ledger, and map Phase 7's gate to its phase in the cost tool | phases 1 to 6 F1; n07 record G4 |
| M9 | Index outcomes, impacts and risks as node types, and read the uncertainty ledger and roles registry in the builder | snapshot F3, F5, F6 |
| M10 | Measure a default package budget from a real work plan instead of inheriting 3000 from the harness | snapshot F2, F7, F8; blind baseline F5 |
| M11 | Prune or index superseded package generations; 72 directories hold 18 live packages | blind baseline list; subticket B F5 |
| M12 | Stop Phase 1 overwriting another instrument's entry in a shared Tier 2A registry, and make the gate see it | phases 1 to 6 F13; profile F6 |
| M13 | Let `phase_01_gate` tell this call's `extracted/` from a stale one | Tier 2B intake I1 |
| M14 | Give the pre-evaluation profile schema an unweighted, single-variant form; anchor B.2.3 | profile F1, F2, F8 |
| M15 | Let an ESR intake declare that no submission exists | blind baseline F3 |
| M16 | Deduplicate the section assembler's claim ledger at the source | blind baseline list |
| M17 | Resolve the real-section probes' anchors from the matching profile | blind baseline F11 |
| M18 | Reach `docs/integrations/` with the leakage scan, and catch a bare domain | override G1; consortium F6 |
| M19 | Type the budget figures in the interface contract so `g08_p04` can reject a non-numeric price | override G3; budget request F8 |
| M20 | Label Tier 5 content derived from the fictional budget, as §13.8 requires; the box is open and its test is red | ticket A, `tickets_budget_and_blind_lane.md` |
| M21 | Record the RIA lump-sum page limit of 45 beside the stored 40, and fill `template_adapter_map.json` or retire it | coverage F1, F2 |
| M22 | Unify the work package seed's two readers on one key, and declare schemas for the five seeds that have none | seeds F1, F4, F5 |
| M23 | Decide whether the change recorder keeps bytes as well as content | subticket B F6 |
| M24 | Name the change recorder as a second refine route in the operator manual for instances with no vault | subticket B F3 |
| M25 | Move D7.4, the dissemination plan, off the final month of a 48-month project | gate 10c record F15 |
| M26 | Re-point three stale test pins: the Phase 8 hard block, Phase 1's ownership of `extracted/`, and the intake's stale-files finding | phases 1 to 6 F8; the suite |

## 9 · Fine-grained reuse: the evidence for and against

The question the demo was built to inform: should the scheduler's whole-Tier-3 fingerprint give way
to the planner's record-level trace?

For:

- On the one enacted change, the fingerprint forced a rerun of all three sections for a one-month
  move of one deliverable and one milestone. The planner would have reused two sections on arm 1 and
  one on arm 2. A Phase 8 redraft cost 31 invocations and about 670,000 estimated tokens here, so the
  saving per avoided section is real.
- The planner's narrower verdicts were investigated and are defensible: the changed field alters no
  record the two sections draw on directly, and the reached nodes are transitive hits.
- The planner wrote no reuse metadata and left every scheduler decision byte-identical with and
  without an advisory present, so it can run in shadow indefinitely at no risk.

Against:

- There is no evidence from a real rerun. Eighteen of eighteen real comparisons refused, and the only
  diagnostic comes from a run that never ran. M1 and one dispatch are needed before any real
  agreement rate exists.
- The planner's inputs rest on the operator's declared derivation rule, recorded as Assumed: a
  section's inputs are the node ids its text names, not what the drafter read.
- The planner cannot see two classes of change at all: a change inside a non-indexed nested list
  reports nothing changed (F5), and no Part B passage is reachable from any Tier 3 origin (F6). Both
  are the unsafe direction.
- No reuse policy exists for this world, so there is nothing to apply a narrower verdict under.
- The scheduler's conservative verdict costs quota, never correctness.

Recommendation: keep the fingerprint operative, land M1 and dispatch once to get a real agreement
rate, and treat M4 and M5 as prerequisites for any policy that lets the planner's verdict win.

## 10 · What stays open

- Subticket D, then one Phase 8 dispatch under a uuid, then `--record-rerun`. Both are operator acts.
- Subticket C: candidate version 2 and the superseded blind lane need the redrafted sections that
  dispatch produces.
- Subticket E, or its retirement to Milestone 2 as M3.
- The Tier 5 fictional-budget label (M20), the only open box outside the subtickets that is a
  live constitutional requirement.

The test suite at this report, `py -3.10 -m pytest -q` on 2026-10-03: 47 failed, 6060 passed, 77 skipped, 5 errors in 258 s, measured before this report's own placeholder check was filled, so the committed state is 46 failed.
Before this ticket the suite showed 47 failed and 5 errors. The one failure this ticket removes is the
blind-baseline scan count. The failures outside the demo's own tests are the pre-existing families the
scope record listed. The demo's own red tests are the three stale pins in M26 and the fictional-label
test of M20.
