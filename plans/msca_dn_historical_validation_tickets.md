# MSCA-DN historical-validation tickets

Date: 2026-10-08  
Repository: `JozsefKiss90/proposal_orchestrator`  
Branch: `msca-dn-pre-eval`  
Source: `plans/reports/MSCA_DN_Readiness_Audit_2026-10-08.md` (audit of `ca0a443`)  
Predecessor ledger: `plans/pe08_review_and_pe09_handoff_tickets.md`

## Purpose and milestone boundary

These tickets prepare the branch to import, assess, verify and freeze the official 2025 MSCA-DN
proposal as a validated historical baseline. **V01 to V15 are the historical-validation milestone.**
They close the audit's seven acceptance gates G1 to G7 and its twelve findings F01 to F12.

Two boundaries are deliberate:

- **V16 is downstream.** The Stage B resubmission lane sits in a separate backlog section below.
  Preparing it is not a precondition for accepting the frozen 2025 baseline through V15.
- **X01 to X04 are conditional enhancements** that block no gate. X01 becomes mandatory only under a
  source-grounded scope, selected at V06 and declared at V15.

The audit's decision stands: NO-GO on running and freezing the official assessment at `ca0a443`. This
ledger proposes implementation work. It confers no authority to mark a gate closed.

## Starting state

PE-08 is approved at `ca0a443`, with 26 of 26 path and hash bindings matching the checkout and the
comparison replaying successfully. That package is accepted with its recorded deferrals.

Four defects were reproduced in the audit and are not yet closed. The importer does not reproduce its committed
document snapshot in a fresh environment. The freeze accepts incomplete and inconsistent reports. No
sourced historical 2025 profile exists. The integrity audit hard-codes sanitisation assumptions. The
focused suite is not green: 1,864 passed, 44 failed, 48 errors, 8 skipped.

## Shared inputs

- Audit: `plans/reports/MSCA_DN_Readiness_Audit_2026-10-08.md`.
- Specification: `plans/msca_dn_pre_evaluation_spec.md`.
- Runbook: `plans/msca_dn_pe09_runbook.md`.
- Approval: `docs/tier4_orchestration_state/decision_log/msca-dn-operator-approval_2026-10-08.json`
  and `docs/tier4_orchestration_state/msca_dn/reviews/operator_approval_2026-10-08.md`.
- Import and workspace tools: `tools/import_external_proposal.py`, `tools/author_msca_dn_workspace.py`.
- Generic extraction: `runner/external_proposal.py`; dependency declarations in `requirements.txt`.
- Freeze and report binding: `harness/blind_baseline.py`, `harness/blind_assessment.py`.
- Integrity audit: `harness/integrity_audit.py`.
- Profile and rubrics: `harness/profiles/msca_dn_2026_default.json`, `harness/rubrics_msca_dn.json`,
  `harness/evaluator_scorecard_msca_dn.json`, `harness/rubrics.py`.
- Preflight and pack selection: `harness/evidence_preflight.py`, `harness/evidence_pack.py`.
- Frozen baseline: `docs/tier4_orchestration_state/msca_dn/baselines/resolved_fixes_2026-10-06/`.
- Approved dispositions and comparison: `docs/tier4_orchestration_state/msca_dn/esr/` and
  `docs/tier4_orchestration_state/msca_dn/comparisons/`.
- Graph root: `workspaces/msca_dn`. Candidate node `MSCA-DN-2025_sanitised_part_b@b51a103520b58ded`,
  candidate hash prefix `sha256:242f1afb02c8`, snapshot `sha256:a5176eef3a01`.

Resolve materialised candidate, audit and register paths from current records. Do not guess a path or
reconstruct an identifier from a hash prefix.

## Execution order

| Ticket | Work | Gate | Closes | Blocked by |
|---|---|---|---|---|
| V01 | Pin the extraction environment and reproduce both sanitised imports | G1 | F01 | None |
| V02a | Restore the document-identity-dependent fixtures | G1 | F08 part | V01, V05 |
| V02b | Pair the claim-ledger and evidence-pack real-data fixtures | G1 | F08 part | V01 |
| V02c | Update the stale synthetic test contracts | G1 | F08 part | None |
| V02d | Dispose of the missing calibration and regression datasets | G1 | F08 part | None |
| V03 | Name and green the PE-09 acceptance lane | G1 | F08 | V01, V02a (criterion 2 → V05), V02b, V02c (criterion 1 excluded), V02d |
| V04 | Make the freeze refuse incomplete and inconsistent reports | G4 | F03 | None |
| V05 | Derive audit grounding and identity wording from candidate provenance | G4 | F06 | None |
| V06 | Declare the grounding scope in preflight, report and freeze | G4 | F07 required half | V04 |
| V07 | Externalise the document configuration | G2 | F02 code | V01 |
| V08 | Dry-import inventory and original-provenance records | G2 | F02 review | V07 |
| V09 | Pin the 2025 authority documents and build the equivalence matrix | G3 | F05 sources | None |
| V10 | Author the historical 2025 profile from the matrix | G3 | F05 | V09 |
| V11 | Open-deferral register | G7 prereq | F11 | None |
| V12 | Correct the PE-09 runbook | G2, G4, G5 | F04, F12 | V04, V06, V07, V10 |
| V13 | Private execution readiness receipt and its validator | G5 | F04 evidence | V08, V10, V12 |
| V14 | Operator: Stage A historical experiment, frozen before ESR | G6 | — | V03, V05, V06, V11, V13 |
| V15 | Milestone acceptance record | G7 | — | V14 |

Seven tickets can start immediately: V01, V02c, V02d, V04, V05, V09 and V11 have no blockers. The
audit's dependency shape is preserved: G1 precedes G2; G3 and G4 proceed independently; G2, G3, G4 and
G5 all precede G6; G7 follows G6.

### Finding to ticket map

| Finding | Severity | Closed by |
|---|---|---|
| F01 | High; import reliability | V01 |
| F02 | High; original applicability | V07, V08 |
| F03 | High; baseline integrity | V04 |
| F04 | Medium; operational assurance | V12, V13 |
| F05 | High; historical validity | V09, V10 |
| F06 | High for truthful reporting | V05 |
| F07 | Conditional capability blocker | V06 required half; X01 if grounded claims are made |
| F08 | High; release confidence | V02a, V02b, V02c, V02d, V03 |
| F09 | Medium; later automation | X02 |
| F10 | Medium; evaluator claims | X03 |
| F11 | Governance clarification | V11 |
| F12 | Medium; runbook execution | V12 |

## Shared constraints

- **Immutable artifacts.** The committed sanitised PDFs, document records, page sources, import
  manifests, both fidelity registers, the ESR record, the frozen baseline and its freeze record, the
  approval records, the approved dispositions, comparison and revision plan, and the committed
  integrity audits are historical evidence. Do not edit them. New decisions go into successor records.
- **The 74.60 baseline stays.** Its recorded total, criterion medians and spreads, and all its
  bindings remain reproducible. V04 proves this: the committed report must still pass the hardened gate.
- **No quota while gates are open.** Do not run a new assessor during V01 to V13, and do not tune any
  component toward 85.80 or any other target score.
- **No auto-checking a deferral.** An agent-authored draft never impersonates operator approval. A box
  is checked only when its closure evidence exists, and V14 and V15 additionally require the operator's
  own decision.
- **Scoped exceptions are not passes.** A test excluded by scope is recorded as excluded, with its
  reason and its replacement evidence. Never report an excluded check, a missing dataset or an
  unassessable axis as a passing test or a successful calibration.
- **Hashes are reproduced, not regenerated.** Do not renormalise line endings in bulk and do not
  rewrite a recorded hash to make a check pass. Retain existing line-ending protections.
- **Honest status vocabulary.** Use Confirmed, Inferred, Assumed and Unresolved as the repository
  defines them. Every new artifact identifies its inputs, review state, uncertainties and relationship
  to earlier versions.
- **Read before writing.** Inspect current command help and tests before documenting a command. Do not
  invent a flag.
- Tests run with `py -3.10` under the environment pin established by V01.

## V01 — Pin the extraction environment and reproduce both sanitised imports

**Gate:** G1. **Closes:** F01. **Blocked by:** None — can start immediately.

**Problem.** In a fresh environment `tools.import_external_proposal --check` exits 1, deriving
`MSCA-DN-2025_sanitised_part_b@842a80dea6920270` against committed versions ending
`@bdb8670f6987e4db` and `@b51a103520b58ded`. `tools.author_msca_dn_workspace --check` also exits 1:
subsection 1.1 recomputes 307 paragraphs and 19,606 characters against a committed 302 and 19,601, and
subsection 1.3 recomputes 69 and 10,013 against 66 and 10,010. The manifests record the project's own
four version strings but pin neither Python, PyMuPDF nor MuPDF. `pymupdf>=1.24.0` is too broad for
byte-identical provenance replay.

**What to build.** An engineer in a named, pinned environment runs the two check commands and both
exit 0, with no committed artifact changing. The cause of the divergence is identified rather than
assumed, and the supported extraction environment is recorded where a future replay can reconstruct it.

### Acceptance criteria

- [ ] Both `tools.import_external_proposal --check` and `tools.author_msca_dn_workspace --check` pass
      in the pinned environment.
- [ ] Both committed document versions, `@bdb8670f6987e4db` and `@b51a103520b58ded`, are reproduced
      from the PDFs — not regenerated to match a new extraction.
- [ ] The cause of the paragraph and character divergence is diagnosed and recorded in the decision
      log, with the four measured register differences stated. An undiagnosed cause is recorded as
      Unresolved, not as extraction-library variation presumed.
- [ ] The exact Python, PyMuPDF and MuPDF versions are pinned in the repository and recorded in the
      import manifest alongside the existing extractor, normalisation, table-rendering and
      claim-extraction version strings.
- [ ] If an extraction upgrade proves necessary, it lands as a new document version with explained
      differences and successor bindings. The existing versions, their hashes and the frozen 74.60
      baseline remain untouched.
- [ ] A second run in the pinned environment reproduces the same identifiers byte-equal.

**Verification.** Run both check commands twice in the pinned environment, then the importer and
workspace test modules. Record the environment and both outputs in the completion report.

## V02a — Restore the document-identity-dependent fixtures

**Gate:** G1. **Closes:** part of F08. **Blocked by:** V01, V05.

**Problem.** The MSCA-DN integration modules show 29 failures and 43 errors, many sharing one failed
import fixture. Two integrity-audit integration failures depend on regenerated document identity. The
audit's instruction is to resolve F01 first, then reclassify what remains.

**What to build.** With import reproduction restored and the audit wording derived from provenance,
these modules go green or each residual failure is explained as a real defect with its own fix.

### Acceptance criteria

- [x] The import, workspace, fidelity-register and adoption fixture failures and setup errors are
      resolved, and the count is compared against the audit's 29 failures and 43 errors.
- [x] The two integrity-audit integration failures pass against the reproduced document identity and
      the V05 provenance-derived wording. **Closed by V05 on 2026-10-12.** The first half held from
      2026-10-09. V05 carried the second half as its own sixth criterion and closed it; evidence
      `plans/reports/v05_audit_grounding_provenance_2026-10-12.md` section 4.
- [x] Any residual failure is classified as a real defect with a named cause, not carried as
      pre-existing without evidence.
- [x] No fixture is edited to encode a hash the importer no longer produces.

**Verification.** Run the MSCA-DN integration modules and the integrity-audit tests under the V01 pin.


**Status 2026-10-09.** Three of four criteria closed. Criterion 2 stays open: both integrity-audit checks pass against the reproduced document identity, but under the existing wording, because V05 is open and no wording was derived from candidate provenance. It closes with V05. Evidence: `plans/reports/v02_focused_suite_completion_2026-10-09.md`.

**Status 2026-10-12.** Four of four criteria closed. V05 landed and criterion 2 closed with it, so V02a
is complete. Evidence: `plans/reports/v05_audit_grounding_provenance_2026-10-12.md`.

## V02b — Pair the claim-ledger and evidence-pack real-data fixtures

**Gate:** G1. **Closes:** part of F08. **Blocked by:** V01.

**Problem.** Claim-ledger real-data checks expect counts and fixtures that differ from current data.
Evidence-pack real-data checks carry a section and profile fixture mismatch. The audit warns against
forcing the code to reproduce stale counts blindly.

**What to build.** Each real-data check names the profile and data pair it intends, so a reader can see
which candidate and which profile the expectation belongs to.

### Acceptance criteria

- [x] The authoritative claim-ledger fixture is reconciled against current data, and the expected
      counts are derived from a named candidate version rather than hard-coded from memory.
- [x] Each evidence-pack real-data check declares its intended profile and section pairing explicitly.
- [x] No production register or committed ledger is mutated to satisfy a test.
- [x] Where a count changed legitimately, the completion report states the old value, the new value and
      the reason.

**Verification.** Run the claim-ledger and evidence-pack test modules under the V01 pin.


**Status 2026-10-09.** Closed, four of four. Evidence: `plans/reports/v02_focused_suite_completion_2026-10-09.md`.

## V02c — Update the stale synthetic test contracts

**Gate:** G1. **Closes:** part of F08. **Blocked by:** None — can start immediately.

**Problem.** Three failures come from synthetic test scaffolding, not from product data. The
rubric-report fixture lacks the current `confirmation_checklist` shape. The T03 end-to-end scripted
assessor returns no criterion `shortcomings` list, so the command correctly refuses the response and
checkpoints it. The subscription-judge cwd refusal test fails because a fresh checkout lacks the
expected `.claude/runs` fixture, so refusal happens earlier than the test intends.

**What to build.** Each of the three tests exercises the path it was written to exercise, with
fail-closed behaviour preserved rather than relaxed.

### Acceptance criteria

- [ ] The rubric-report fixture and the `confirmation_checklist` contract agree, and the change is made
      in one direction with a stated reason. **Excluded, not passed.** The direction and the reason are
      recorded. The two sides cannot agree while no Tier 3 checklist exists, so the real-file half is a
      scoped exclusion in `harness/DATASET_DISPOSITIONS.md` and in the V03 lane declaration.
- [x] The T03 scripted backend returns a criterion response that satisfies the current scorer contract,
      and a separate test still asserts that a response missing `shortcomings` is refused and
      checkpointed.
- [x] The subscription-judge test constructs its own `.claude/runs` fixture and asserts the intended
      path rule portably, on a fresh checkout and on Windows.
- [x] No refusal, isolation or fail-closed behaviour is weakened to make a test pass.

**Verification.** Run the three modules on a fresh checkout and confirm the fail-closed assertions
still fail when the guard is removed.


**Status 2026-10-09.** Three of four criteria closed. Criterion 1 stays open: the rubric-report lane's change was made in one direction with a stated reason, but the two sides cannot be made to agree while no Tier 3 confirmation checklist exists. The real-file half is recorded as an exclusion in `harness/DATASET_DISPOSITIONS.md`. Evidence: `plans/reports/v02_focused_suite_completion_2026-10-09.md`.

## V02d — Dispose of the missing calibration and regression datasets

**Gate:** G1. **Closes:** part of F08. **Blocked by:** None — can start immediately.

**Problem.** Ledger-granularity and regression golden checks fail because the datasets are absent:
`harness/gold_sets/` and `harness/regression_baselines/` contain only READMEs. The audit is explicit
that missing gold data must stay visible and must not become a claim of successful calibration.

**What to build.** A written disposition for each dataset-dependent check: restored from a maintained
source, or scoped out with its reason and its replacement evidence recorded.

### Acceptance criteria

- [x] Every dataset-dependent failing check is listed with its disposition, restored or scoped out.
- [x] A scoped-out check is recorded as excluded with a reason and replacement evidence. It is never
      reported as passing, skipped silently, or counted toward suite health.
- [x] The absence of expert-labelled DN validation data is stated where a reader of the harness status
      would otherwise infer calibration.
- [x] The disposition names X03 as the work that would lift the exclusion.

**Verification.** Run the affected modules and confirm the recorded disposition matches the observed
result. No new dataset is fabricated.


**Status 2026-10-09.** Closed, four of four. Evidence: `plans/reports/v02_focused_suite_completion_2026-10-09.md`.

## V03 — Name and green the PE-09 acceptance lane

**Gate:** G1 closure. **Closes:** F08. **Blocked by:** V01, V02a, V02b, V02c, V02d — the dependency
gate as amended below.

### Dependency gate, amended 2026-10-09

V02b and V02d closed in full. V02a and V02c each left one box open, and V03 cannot close a gate that
rests on an unexplained open box. Neither box is checked. Each one's disposition:

| Open box | Disposition | Owner |
|---|---|---|
| **V02a criterion 2** — the integrity-audit checks pass against the V05 provenance-derived wording | **Transferred.** Its first half holds: both checks pass against the reproduced document identity. Its second half needs wording V05 has not yet derived, and the ledger's own dependency table already records V02a as blocked by V05. | V05, which now carries it as its own sixth criterion |
| **V02c criterion 1** — the rubric-report fixture and the `confirmation_checklist` contract agree | **Excluded, not passed.** The change went in one direction with a stated reason. The two sides cannot agree while the engine stands at its project-agnostic default, because no Tier 3 confirmation checklist exists to agree with. The real-file half is one of the lane's 17 declared exclusions. | No owner; a project instantiation lifts it |

The amendment is to the gate, not to the criteria. V03's gate reads: V02a and V02c are closed for G1
once their open halves are **owned elsewhere or declared as exclusions**, and V03's own criteria carry
the evidence. An exclusion is never reported as a pass. `harness/ACCEPTANCE_LANE.md` and
`harness/DATASET_DISPOSITIONS.md` list the V02c exclusion by node id. The lane command refuses to run
when its declaration and the disposition table disagree, and `tests/harness/test_acceptance_lane.py`
fails if the row leaves either document.

**Problem.** The focused audit command completed with 1,864 passed, 44 failed, 48 errors and 8 skipped
across 1,964 collected cases. No hosted CI configuration supplies an independent result. Test counts
are not coverage of acceptance invariants: the passing baseline tests did not catch the defects the
freeze probes reproduced.

**What to build.** One documented command reproduces the acceptance suite from pinned dependencies,
with zero unexplained failures and every exception enumerated.

### Acceptance criteria

- [x] A named lane covers importer, profile, preflight, freeze, comparison, provenance and isolation
      checks, and runs under the V01 environment pin. Those seven areas plus seven more cover 66
      modules; the lane refuses to certify a result on a build not measured to reproduce the imports.
      (Recounted 2026-10-12: the figures read five more areas and 62 modules when V03 was accepted.
      V06 added `test_grounding_scope.py` and V11 added a `deferrals` area with two modules. The seven
      depended-on areas this criterion names are unchanged, and the recount re-accepts nothing.)
      `harness/acceptance_lanes/msca_dn_historical.json`, `harness/acceptance_lane.py`,
      `harness/commands/acceptance_lane.py`.
- [x] The lane reports zero unexplained failures. Each exception names its module, its reason and its
      replacement evidence, and no exception covers a check the historical run depends on. All 17 skips
      are declared exclusions, listed in the completion report and in `harness/DATASET_DISPOSITIONS.md`.
      The lane fails on an undeclared skip and on a stale exclusion, which is how it found one.
- [x] The result is recorded against the audit's 1,864 / 44 / 48 / 8 baseline so every item is resolved
      or explicitly scoped. `plans/reports/v03_acceptance_lane_completion_2026-10-09.md` section 3.
- [x] The lane's own documentation states that passing it is not evidence of calibration, forecast
      accuracy or grounded evaluation. `harness/ACCEPTANCE_LANE.md`, asserted by
      `tests/harness/test_acceptance_lane.py::TestLaneDocumentation`.

**Verification.** Run the lane twice from a clean checkout in the pinned environment. Record both
results and the exception list.

**Status 2026-10-09.** Closed, four of four, with the dependency gate amended above. F08 closes here.
V02a criterion 2 is owned by V05 and V02c criterion 1 stays an exclusion; neither is a pass. Evidence:
`plans/reports/v03_acceptance_lane_completion_2026-10-09.md` and
`docs/tier4_orchestration_state/decision_log/msca-dn-acceptance-lane_2026-10-09.json`. G1 closure is the
operator's to accept.

## V04 — Make the freeze refuse incomplete and inconsistent reports

**Gate:** G4. **Closes:** F03. **Blocked by:** None — can start immediately.

**Problem.** The complete `freeze_baseline` path accepted all four invalid variants the audit built
from copies of the committed report. One kept one of ten cells, one kept one of three criterion
scores, one removed `assessor_invocation`, and one replaced the total with 99.9. Each was accepted
with 15 checks passed. The checks verify non-empty lists, selected fields, bindings on entries that remain, a declared
sample count and a non-null total. Removing records leaves nothing for the per-entry binding loop to
reject. `BASELINE_CHECKS` names 16 conditions; none enforces the profile's identity sets or recomputes
the aggregate.

**What to build.** The freeze refuses a report that is incomplete, duplicated, out of range or
internally inconsistent, while the committed baseline still freezes unchanged.

### Acceptance criteria

- [x] Freeze enforces the profile's exact expected cell and criterion identity sets and their
      cardinalities, and rejects duplicate cell or criterion entries. `cell_identity` compares the
      report's cells with `harness.blind_assessment.expected_cells` — the rubric set crossed with the
      profile's criterion-to-section map — and `criterion_identity` compares its scores with
      `profile.criterion_ids`. Both compare multisets, so a repeated entry is refused by name.
      `assess_candidate` was additionally pointed at the same grid so the expected set and the
      produced set cannot drift; that refactor is a declared deviation, not a requirement of this
      criterion.
- [x] Freeze verifies member counts, score ranges, medians, spreads and the declared sample count
      against the entries actually present. `cell_members`: as many members as the panel declares,
      member scores on the unit interval, and the mean, agreement and majority call that
      `verdict.majority_vote` gives when the members are put back through it. `criterion_arithmetic`:
      as many samples as the report declares, every sample on the scorecard's scale, and the median,
      spread, weight, factor and weighted points from the grader's own
      `median_score` / `score_spread` / `weighted_points_for`.
- [x] Freeze recomputes the weighted total from the criterion scores under the profile's
      `10E + 6I + 4Q` and refuses an inconsistent aggregate. `total_recomputed` calls
      `harness.criterion_scoring.weighted_total` over the scores the report carries — the same
      function that formed the total — and also re-derives the declared maximum, threshold and
      threshold verdict.
- [x] Freeze requires transport-appropriate invocation and isolation evidence; a report with
      `assessor_invocation` removed is refused. `TRANSPORT_ISOLATION_EVIDENCE` names what each
      transport owes: the subscription transport must declare `tools: ""`, `strict_mcp_config: true`
      and a working directory outside the repository, and must name that directory. The last
      declaration is measured rather than read — a path under `--repo-root` is refused whatever the
      record claims — while the first two remain the backend's word (see the report's uncertainties).
      An unknown transport is refused. An API transport runs no child process and is recorded not
      applicable, never passed.
- [x] All four reproduced negative probes are refused with a check name and a reason, and focused
      negative tests cover each. `tests/harness/test_blind_baseline.py::TestTheCommittedMscaDnBaseline`
      runs all four through the real `freeze_baseline` on copies of the committed report under
      `tmp_path`; `TestTheIdentitySets`, `TestTheArithmeticReproduces` and `TestTheInvocationEvidence`
      add 32 focused cases on the synthetic world.
- [x] The unmodified control still passes, and the committed `blind_baseline_f60ae6e0a2a1.json` still
      validates with its recorded total of 74.6. The control freezes with 21 of 21 checks passed and
      reproduces the committed freeze's `report_sha256`, copy name and every binding.
- [x] `checks_passed` remains derived from checks that actually ran. Immutable report copies and
      one-freeze-per-directory behaviour are preserved. `BaselineCheckRun.passed` is the checks that
      ran minus the failures, and a check that did not apply is listed in the new
      `checks_not_applicable` with its reason (freeze schema 1.0.0 → 1.1.0). `render_freeze` prints
      the count and names any exception, so the screen and the record agree; that line and the
      removal of the redundant `profile_version` parameter are declared deviations.

**Verification.** Exercise the real `freeze_baseline` path on isolated copies with the real candidate
and loaded profile bundle, as the audit did. Write only to a temporary directory. Do not rerun the whole
repository in place of focused negative tests.

**Status 2026-10-12.** Closed, seven of seven. F03 closes here. G4 did not close on this ticket:
V06 was still open. The operator accepted V04 with V05 and V06 on 2026-10-12 — see the G4 acceptance
section below.

`freeze_baseline` now takes the loaded `ProfileBundle` rather than the profile, because the rubric set
and scorecard are what say whether a report is complete. Three changes outside the seven criteria are
declared in section 8 of the completion report rather than presented as required. The acceptance lane
is green: 2,244 passed, 0 failed, 0 errors, 17 declared exclusions. No assessor ran and the 74.60
baseline is untouched. Evidence: `plans/reports/v04_freeze_refuses_incomplete_reports_2026-10-12.md`
and `docs/tier4_orchestration_state/decision_log/msca-dn-freeze-completeness_2026-10-12.json`.

## V05 — Derive audit grounding and identity wording from candidate provenance

**Gate:** G4. **Closes:** F06. **Blocked by:** None — can start immediately.

**Problem.** `harness/integrity_audit.py` sets the grounding reason to the module constant
`"supporting sources removed by sanitisation"` and expects imported ledger claims to stay `unresolved`.
It also carries sanitisation-specific explanations for host-identity limitations. Applied unchanged to
the official original, that wording would misstate why corroboration is missing, even where the
original carries references and real identities.

**What to build.** The audit states the true reason for whichever candidate it reads.

### Acceptance criteria

- [x] The grounding reason and the host-identity explanations derive from the imported candidate's
      recorded provenance and capabilities, not from a constant applied to every document.
- [x] Expected claim status comes from the candidate's own ledger rather than a hard-coded `unresolved`
      assumption. **Source substitution, declared.** The expectation is read from the candidate's own
      import manifest (`claims.declared_status`), which is the import's declaration *about* that
      ledger, not from the ledger array itself. Reading the ledger as its own expectation is circular:
      every entry would then agree with itself and no contradiction could ever be reported. Without a
      manifest there is no expectation and the audit says so. Report section 3.
- [x] Table schema and identity comparisons are revalidated for a document carrying references and real
      identities. An anonymised-host assumption is never applied as an original-document rule.
- [x] **Amended and closed 2026-10-12 on operator instruction.** The amendment requires four
      conditions in place of whole-file reproduction, and all four are verified against the committed
      evidence:
      (1) both committed sanitised audits, `integrity_242f1afb02c8_0003.json` and
      `integrity_13ad3ad81d7e_0001.json`, are byte-unchanged and verify against their recorded
      sha256;
      (2) the grounding axis and all nine identity findings reproduce for both sanitised revisions;
      (3) the current revision's whole five-check payload reproduces, 13 findings for 13;
      (4) the older revision's differences are exactly the twenty-seven findings that operator
      decision D11 and ticket R03 retired — sixteen `undeclared_dependency`, nine `out_of_window`
      appointments, and the two whole-cohort package sets WP6 and WP7 — leaving 15 findings where the
      committed file carries 42, with nothing new.
      **The older revision's audit still does not reproduce in full under the current rules.** The
      amendment does not say otherwise. That file predates D11 and R03, which changed what the checks
      emit, and a successor audit over that candidate remains unwritten and remains the operator's to
      commission.
      Evidence: `tests/harness/test_integrity_audit.py::TestTheCommittedAudits`, eight cases passing,
      including `test_the_first_copys_payload_differs_only_by_the_retired_rules`, which enumerates the
      twenty-seven by name, and V05's report section 5. Acceptance record
      `docs/tier4_orchestration_state/msca_dn/reviews/operator_acceptance_g4_2026-10-12.md`; amendment
      record `docs/tier4_orchestration_state/decision_log/msca-dn-g4-acceptance_2026-10-12.json`.
      **Original wording, superseded and kept for the record.** "Both committed sanitised audits,
      `integrity_242f1afb02c8_0003.json` and `integrity_13ad3ad81d7e_0001.json`, reproduce
      byte-equal." That box stood open, annotated "Open, and not V05's to close", because whole-file
      reproduction could not hold for the older copy without a successor audit over it. The operator
      chose the amendment over that audit. V05's implementation did not change; what changed is what
      this criterion asks of it.
- [x] A candidate whose provenance does not state a grounding cause yields an explicit Unresolved
      reason, not a borrowed one.
- [x] **Inherited from V02a criterion 2.** The two integrity-audit integration checks pass against the
      provenance-derived wording, not only against the reproduced document identity. V02a closed its
      first half on 2026-10-09 and left this half open; V03 transferred it here rather than closing it
      as a pass. Evidence: `plans/reports/v02_focused_suite_completion_2026-10-09.md` and
      `plans/reports/v03_acceptance_lane_completion_2026-10-09.md`. **Closed 2026-10-12.** No earlier
      record resolves "the two checks" to test identifiers, so report section 4 names the two
      integration checks that depend on both the identity and the wording, and binds both committed
      audits byte-equal besides.

**Verification.** Regenerate both committed audits and diff the bytes. Add a test that a non-sanitised
candidate configuration produces a different, provenance-derived reason.

**Status 2026-10-12, as implemented.** Five of six criteria closed. `harness/candidate_provenance.py`
derives the grounding cause, the identity scope and the expected ledger status from each candidate's own
import manifest and fidelity register. The persisted report gained no key, which is what keeps the
committed audits reproducible. Criterion 4 stayed open for the reason written in its own box, and it was
not read as a pass anywhere. F06 closes: the wording no longer comes from a constant. G4 did not close
on this ticket — V06 was still open. Evidence:
`plans/reports/v05_audit_grounding_provenance_2026-10-12.md`; decision record
`docs/tier4_orchestration_state/decision_log/msca-dn-audit-grounding-provenance_2026-10-12.json`.

**Status 2026-10-12, after the amendment.** Six of six. The operator amended criterion 4 to four
enumerated reproduction conditions and they verify against the committed evidence. No code moved, no
committed audit was edited, and the older revision's audit still does not reproduce in full. V05 is
accepted as part of the G4 acceptance below. Amendment evidence:
`plans/reports/g4_acceptance_and_v05_criterion4_amendment_2026-10-12.md`.

## V06 — Declare the grounding scope in preflight, report and freeze

**Gate:** G4. **Closes:** the required half of F07. **Blocked by:** V04.

**Problem.** The sanitised ledger holds 45 unresolved claims per revision and the blind lane runs
`--no-claims`, which makes every cell's grounding unassessable by design. Nothing in the report records
that choice, so a later reader cannot tell an unassessable run from an assessed one.
Proposal-internal coherence, plausibility, fidelity to the submitted text and independent factual
support are four different claims.

**What to build.** Every preflight, report and freeze carries a declared grounding scope, and an
unassessable run says so where a reader cannot miss it.

### Acceptance criteria

- [x] Preflight, report and freeze each record a declared grounding scope. `--grounding-scope` is
      **required** on `preflight`, `assess` and `salvage`, and each of the three records carries a
      `grounding_scope` block holding the declaration, its source, the measurement, the counts and a
      derived reason.
- [x] A `--no-claims` run reports grounding as **unassessable** prominently, rather than as absent or as
      zero findings. All three renderers print the same derived headline and reason, and the report
      prints it above the cell table. A record carrying no block still gets one, measured from its own
      cells, so the line is never absent.
- [x] The freeze binds the declared scope, so a later stage cannot present an unassessable run as
      source-grounded. `BASELINE_CHECKS` gained `grounding_scope` (21 names → 22) and the freeze record
      gained a top-level block (schema 1.1.0 → 1.2.0). **One non-applicability, declared.** A report
      that declares nothing and whose cells are unanimously unassessable records the check *not
      applicable* with its reason, and the freeze records the measurement instead. The committed 74.60
      report is that case: it predates the declaration, and derivation can only ever read
      `unassessable`, never `source_grounded`. An undeclared report that grounded a cell is refused, so
      omitting the declaration is not a route past the check. Report section 5.
- [x] The acceptance-record template states which of the audit's two scope choices was performed:
      content-focused with grounding unassessable, or source-grounded.
      `docs/tier4_orchestration_state/msca_dn/reviews/acceptance_record_template.md`, unsigned and
      every value blank. It carries the audit's whole decision-text field set so V15 fills one record
      rather than two; V15 owns signing it.
- [x] A source-grounded declaration is refused unless the X01 imported-claim route is implemented and
      validated. One flag, `IMPORTED_CLAIM_ROUTE_IMPLEMENTED`, read by the command (at parse time,
      before any evidence or quota), the preflight, the report and the freeze. A second rule outlives
      X01: `source_grounded` over a run that did not assess every unit is refused on the measurement.
      Report section 4.

**Verification.** Freeze an unassessable run and a scope-mismatched run on copies; confirm the first
carries the declaration and the second is refused.

**Status 2026-10-12.** Five of five criteria closed. The required half of F07 closes; its conditional
half is X01 and is not implemented. The committed 74.60 report still freezes, 21 of 22 checks passed
with `grounding_scope` not applicable, and its 25 bindings and `report_sha256` reproduce. Two V04
assertions were widened rather than satisfied, and both are named in report section 6. No assessor ran
and no quota was spent, and G4 was then the operator's call over V04, V05 and V06 together. The
operator accepted all three on 2026-10-12 — see the G4 acceptance section below.

Evidence: `plans/reports/v06_grounding_scope_declared_2026-10-12.md`; decision record
`docs/tier4_orchestration_state/decision_log/msca-dn-grounding-scope_2026-10-12.json`.

## G4 — operator acceptance, 2026-10-12

**Status: closed for infrastructure readiness.** The operator accepted V04, V05 and V06 together, in
session, on 2026-10-12. That instruction is the authority for this section. The ledger itself confers
no authority to close a gate.

### What the acceptance covers

| Ticket | Commit | Completion record | Decision record |
|---|---|---|---|
| V04 — the freeze refuses incomplete and inconsistent reports | `82fa9b4` | `plans/reports/v04_freeze_refuses_incomplete_reports_2026-10-12.md` | `docs/tier4_orchestration_state/decision_log/msca-dn-freeze-completeness_2026-10-12.json` |
| V05 — provenance-derived audit grounding and identity wording | `437ca89` | `plans/reports/v05_audit_grounding_provenance_2026-10-12.md` | `docs/tier4_orchestration_state/decision_log/msca-dn-audit-grounding-provenance_2026-10-12.json` |
| V06 — declared grounding scope in preflight, report and freeze | `aa0d464` | `plans/reports/v06_grounding_scope_declared_2026-10-12.md` | `docs/tier4_orchestration_state/decision_log/msca-dn-grounding-scope_2026-10-12.json` |

The acceptance also carries the amendment to V05 criterion 4 and its verification. Evidence:
`plans/reports/g4_acceptance_and_v05_criterion4_amendment_2026-10-12.md`, acceptance record
`docs/tier4_orchestration_state/msca_dn/reviews/operator_acceptance_g4_2026-10-12.md`, decision record
`docs/tier4_orchestration_state/decision_log/msca-dn-g4-acceptance_2026-10-12.json`.

F03, F06 and the required half of F07 close with their tickets.

### What stays open

- **V12 — the PE-09 runbook.** Its substantive corrections stay open, and this acceptance closes none
  of them. V12 is blocked by V07 and V10 besides. G4's documentation share therefore remains to be
  done, and the gate's closure here is read as infrastructure readiness only.
- **X01 — the imported-source grounding route.** Mandatory for any source-grounded assessment. Until
  X01 is implemented and validated, a `source_grounded` declaration stays refused at V06 and V15.
- **The legacy 74.60 baseline keeps its undeclared grounding scope.** Its `grounding_scope` freeze
  check stays recorded not applicable, with the reason V06 declared. That outcome is retained
  deliberately. It is not a defect to repair and the committed report is not to be re-declared.

### What the acceptance does not authorise

It does not authorise the private assessment, and the audit's NO-GO on running and freezing the
official assessment stands. It does not validate the official 2025 baseline. It adopts no fidelity
declaration — D13 stays open. It approves no proposal change. G1, G2, G3, G5, G6 and G7 are untouched.

## V07 — Externalise the document configuration

**Gate:** G2. **Closes:** the code half of F02. **Blocked by:** V01.

**Problem.** The import wrapper's generic extraction machinery is sound, but its application layer is
configured for two sanitised revisions. It fixes `DOCUMENT_TITLE`, `EXPECTED_PAGES = 84`, the workspace
location, `SECTIONS`, `SUB_SECTIONS`, `CRITERION_HEADING_MARKERS`, `SOURCE_ID_FORMAT`, the beneficiary
marker, the intake id and `is_submitted_document: false`. The original must establish its own identity,
role, page count, section boundaries, table interpretation, source identifiers and figure coverage.

**What to build.** A selectable document configuration above the existing `Revision` record, carrying
every assumption the wrapper now hard-codes.

### Acceptance criteria

- [x] Workspace location, title, expected page count, section and subsection maps, criterion heading
      and page anchors, beneficiary marker, source-id format, intake id and the submitted-document flag
      all move into a selectable document configuration. `DocumentConfig` carries 26 fields, 15 of them
      required, one being a four-field `WorkPackageLayout`. The nine module constants are retired, and
      so are the six aliases that bound one document's workspace, intake, register, scorecard and
      revisions to module scope. A test asserts the module carries none of the fifteen names. Four
      assumptions beyond this list moved too: the body point size, the work-package table layout, the
      three labels the register's provenance header declares, and the two sentences a source record
      uses to describe the document and its pages.
- [x] A configuration for the official original exists with its own identity and role, renders
      `is_submitted_document: true`, and inherits no sanitised page map, 84-page assumption or
      derivative description. `official_original` declares its own config id, title, role, intake id,
      short name, page statement, reader caveat and manifest key vocabulary. A test asserts that
      *sanitised*, *derivative* and *84* appear in none of its identity or description fields. No
      required field defaults to the copy's value. Its graph root is deliberately undeclared: the
      original and its extracted text stay in the private network.
- [x] The original is not made a descendant of the sanitised version to reuse its version chain. Its
      intake id and graph root differ, and `__post_init__` refuses a revision whose `supersedes` names a
      revision of another document. The registry refuses any shared config id, intake id, graph root or
      revision id.
- [x] Both existing sanitised configurations reproduce byte-equal under the V01 pin, and both `--check`
      commands still pass. Both exit 0, every rendered file equals the committed bytes, and neither
      hash-bound manifest gained a field.
- [x] A configuration missing a required field fails closed, naming the field. `require_complete()` names
      every missing field; selecting the original names `workspace_rel`, `sub_sections`,
      `expected_pages`, `body_point_size` and `revisions`. One predicate decides which sub-sections need
      a scorecard, so no shape passes the check and refuses later. `require_provenance()` refuses
      separately and names the intake record rather than the undeclared path field.

**Verification.** Reproduce both sanitised configurations byte-equal, then select the original
configuration and confirm it refuses to run without its own page map and provenance.

**Status 2026-10-12.** Five of five criteria closed. The code half of F02 closes; its review half is
V08 and is open. No original PDF is stored here, no page map for it is declared and its intake record
does not exist, so the original is declared and not imported. No assessor ran and no quota was spent.

**V01's criterion 4 stays open.** Its carry is answered in code and not in an artifact. The
runtime-environment block is a configuration flag, empty for the two hash-bound manifests. It is true
only for a configuration `require_complete()` refuses, so the block reaches no file and V08 may still
change its shape. Five residual items are recorded in report section *What is unresolved*, and five declared
deviations in the section after it. The full suite is not green on this branch and was not green before:
HEAD measures 205 failed and 7,153 passed in a worktree, and no test fails here that passes at HEAD.

Evidence: `plans/reports/v07_document_configuration_2026-10-12.md`; decision record
`docs/tier4_orchestration_state/decision_log/msca-dn-document-configuration_2026-10-12.json`.

## V08 — Dry-import inventory and original-provenance records

**Gate:** G2. **Closes:** the review half of F02. **Blocked by:** V07.

**Problem.** Extraction accounting is not semantic fidelity. Normalised character counts and row
accounting prove neither reading order, cell association, mathematical meaning, image content nor
figure completeness, and character deficits and surpluses can offset inside an aggregate. The original
needs a manual reconciliation against the PDF before it is assessed.

**What to build.** A dry import the operator can run privately, producing an inventory to reconcile
against the PDF, plus the records that hold the result.

### Acceptance criteria

- [x] A dry-import mode reports measured section, table and figure inventory, page count and extraction
      limitations without writing graph state. `runner.dry_import.measure` takes a PDF and nothing
      else: no page map, no page count, no graph root, no declared body size. It reports the per-page
      accounting, every table with its header row, the graphical census, the candidate section headings
      and the limitations, and it writes no file. `tools/dry_import_original.py` writes six flat files
      into a directory the operator names — no document record, no source index, no snapshot and no
      intake directory. A weaker precondition than an import: `DRY_IMPORT_REQUIRED_FIELDS` asks for the
      ten identity fields alone, so `official_original` is measurable while still refusing an import.
- [x] Separate intake and original-document provenance records exist, including the authenticated input
      hash of the original PDF. Two records, and the provenance record names the separation: the intake
      holds what is known about the submission, the provenance record holds which file, which bytes and
      which environment. The intake is built through `normalise_intake`, so it keeps its schema. The
      hash is authenticated and not merely computed: `--expect-sha256` is the operator's hash from the
      authoritative source, and the run refuses and writes nothing unless the file matches it. The
      provenance record binds the other three records by the hash of their canonical bytes.
      **Not committed here.** The hash is the operator's, from a document this repository does not
      hold, so authoring either record now would mean inventing it. What is committed is the
      deterministic builder of each record, exercised against a fixture, plus the procedure. The
      ticket's own verification assigns the real run to the operator.
- [x] A fidelity acceptance record covers Gantt, diagrams, embedded images, footnotes, table headers,
      bibliographic references and any supporting Part B material explicitly. Seven items, each with
      what must be reconciled, the measurement that bears on it and why that measurement does not
      settle it. Every item starts `unreconciled`, and `check_acceptance` reports `item_missing` for a
      class the record does not name.
- [x] Neither zero character loss nor zero embedded images is accepted as proof that graphical evidence
      was preserved. Enforced, not stated: `MEASUREMENT_ONLY_BASES` names five measurement bases and
      `check_acceptance` reports `measurement_basis_not_proof` when one stands behind a `preserved` or
      `partly_lost` verdict. A measurement may stand behind `lost`, because an absence can be measured.
      The basis vocabulary is closed, so a measurement cannot enter as free text under a wording of its
      own; a basis outside it is an `unknown_basis` finding. The fixture makes the case concrete — a vector Gantt figure, zero embedded images and zero
      character loss on every page.
- [x] Unresolved extraction limitations are recorded before assessment, and the record states that a
      page or source span locates an assertion without corroborating it. Six rows, every one
      `Unresolved`, in a record of their own written by the dry import, which precedes the import and
      therefore every result. `SPAN_LOCATES_STATEMENT` is carried verbatim in the record.
- [x] The private original PDF and its derived text are not committed to this repository. The tool
      refuses a PDF path or an output path that resolves inside the repository for a document declared
      as the submitted text, and writes nothing. What counts as inside is resolved from the module's own
      location and no argument moves it. `official_original.workspace_rel` stays undeclared. Tests
      assert that no intake record and no document record for the original is committed, and that the
      operator procedure carries no hash and no private path.

**Verification.** Run the dry import on a non-sensitive fixture document in the test suite, and document
the operator procedure for the real original. The operator performs the real dry import.

**Status 2026-10-12.** Six of six criteria closed. F02 closes with V07's code half. The dry import ran
against a two-page fixture this test suite writes, in a temporary directory outside the repository. It
has not been run against the real original: no original PDF is stored here, no page map for it is
declared, and its intake record does not exist. No assessor ran and no quota was spent.

Seven residual items are recorded in report section *What is unresolved*, and seven declared deviations
in the section after it. The largest deviation is where the records live. The real original's records
cannot be authored here, because the document they describe is not here and its authenticated hash is
the operator's. What is committed is the deterministic builder of each record, plus the procedure.

**V01's criterion 4 stays open.** The runtime-environment block still reaches no committed manifest.
V08 did not change its shape.

Evidence: `plans/reports/v08_dry_import_and_original_provenance_2026-10-12.md`; procedure
`plans/msca_dn_v08_original_dry_import_procedure.md`; decision record
`docs/tier4_orchestration_state/decision_log/msca-dn-dry-import-and-original-provenance_2026-10-12.json`.

## V09 — Pin the 2025 authority documents and build the equivalence matrix

**Gate:** G3. **Closes:** the source half of F05. **Blocked by:** None — can start immediately.

**Problem.** The audit did not obtain or authenticate the 2025 call documents, and their absence is
itself a readiness finding. The runbook proposes copying the 2026 profile and leaving a rule unchanged
where no source states a difference. That is a defaulting policy, not evidence that the rule applied in
2025.

**What to build.** The 2025 authority sources pinned by hash, and a matrix in which every
scoring-relevant rule is either sourced or declared unresolved.

### Acceptance criteria

- [x] The 2025 call and work-programme documents are obtained, authenticated and pinned by hash in a
      source index. **Closed on 2026-10-13, under the operator's instruction amending the verification
      sentence below.** The index pins 15 documents by sha256. The work programme part of the 2025
      call, its General Annexes and the evaluation form served through the call window were retrieved
      from the issuing body and stored. No separate call document is held: the work programme carries
      the call's own conditions and topic text, and the rows cite its pages. The one remaining entry
      with `authentication: not_obtained` is the record that would bind this submission to a call
      identifier, which is CI-01's gap and not an authority document. **Authenticated is recorded
      precisely, not loosely.** One field was answering three questions, so the index now answers them
      separately: byte integrity, source authenticity and historical applicability. A retrieval settles
      the second and cannot settle the third. No entry carries a hash published by its issuing body, so
      every retrieval stays `computed_only` and no row is Confirmed.
- [x] A matrix covers criteria, weights, thresholds, evaluator instructions, DN variant, section and
      appendix mapping, and every scoring assumption that affects interpretation or a number. All eight
      areas are `required_areas` in the declaration, asserted against this ticket by test, and
      `areas_required_but_not_covered` reports any the rows leave empty. 23 rows, and a ninth area the
      ticket does not name: `call_identity`, because which call the 2025 submission was evaluated under
      is the prerequisite for addressing the index at all. Three rows carry the harness's own scoring
      assumptions — the sample count and statistic, the unassessable grounding axis, and the assessed
      text being a sanitised derivative — as `era_neutral`, each declaring why no call document of
      either year states it.
- [x] Each row cites a pinned source for equivalence or difference, or is marked an explicit unresolved
      limitation. 67 citations, each declaring exactly one locator: a pointer into a JSON source, or a
      page of a pinned document with the verbatim quote found there. A page number alone locates
      nothing a reader can check, so `document_citations_without_a_quote` reports one. All 34 document
      quotes are re-derived from their pages by test, through the extraction route the evaluation
      bundle used. The two unresolved rows carry their limitation, and an unresolved row without one
      fails.
- [x] No row is marked equivalent because no difference was found. Defaulting is recorded as defaulting,
      with the rule it affects named. Enforced, not stated: the verdict vocabulary has no term meaning
      *no difference was found*, and `equivalence_without_historical_evidence` reports a row marked
      equivalent or differs with no citation into an **obtained historical** source. A `defaulted` row
      names the source it is carried from, the rule its defaulting affects and the risk, and
      `defaulting_without_an_affected_rule` reports one that does not. Five rows are defaulted and two
      unresolved; six of the seven trace to the 2025 evaluation form alone.
- [x] Form-equivalence records are not treated as equivalence of every historical call rule. The index
      entry for the record carries a `scope_restrictions` block: the passage
      `provenance/v5_equivalence`, the one area it settles (`section_mapping`), and what it measured.
      A citation of it from any other area is `citations_outside_their_declared_scope`. It is cited
      once, from inside that area, over a row the 2025 form's own two sentences settle anyway. The
      appendix-mapping row, which could have leaned on it, carries eleven located passages of its own
      instead. A second species of the same overreach is enforced too: an evaluation output or a record
      over the submission evidences what was applied to *that* submission, so
      `call_wide_claims_on_submission_evidence` reports a call-wide conclusion resting only on one.

**Verification.** Every matrix row resolves to a pinned document and a located passage, or to a recorded
Unresolved status. ~~The operator supplies the source documents.~~

**Amended by the operator on 2026-10-13.** Retrieving, inspecting, storing and indexing the public
authority documents is authorised. Duplicate manual downloads are not required. A retrieval may not
be recorded as `operator_supplied` or `issuer_hash_confirmed`.

**Status 2026-10-13, second pass.** All five criteria closed. Three 2025 authority documents were
retrieved from the issuing body, stored, pinned and cited. A successor index and matrix carry the
result, and the 2026-10-12 pair stays in the tree unedited, which is what the superseded index says
must happen to it.

27 rows: 18 equivalent, 2 differs, 0 defaulted, 2 unresolved and 5 era_neutral. Twenty-five are
`Inferred`, one `Assumed` and one `Unresolved`. None is Confirmed. 74 document quotes are re-located
on the pages they cite.

**Every defaulting is gone, and none was relabelled.** Six rows were defaulted because a 2025 document
was missing. Each is now `equivalent` against a located passage of the document itself. The six are the
criterion-to-aspect grouping, the sentence that weighting serves the ranking, which authority sets the
overall threshold, the score resolution, the six score-level descriptions and the applicability-tag
grammar. Those level sentences occur verbatim in both forms.

**One row was added.** TH-06 records that the 2025 evaluation form prints an unweighted total out of
15, where the 2026 form states the threshold on the weighted total out of 100. The form's generic total
was superseded by the call's own rule, and the recorded result shows which was applied.

**Two 2025 authorities disagree about the score resolution.** The work programme says one decimal
place; the evaluation form of the call window says half marks may be given. Two recorded scores are
4.2, which no half-mark rule could award, so the work programme's rule was what was applied. The
deriver refuses to render the row if no recorded score is finer than a half mark. The conflict itself
is logged as a tier conflict and is not resolved in general.

**Four limitations are preserved.** No issuing body's hash vouches for any entry, so no row is
Confirmed. The evaluation form's place in the call is bracketed by three captures of one archive and
not closed, so EI-02 stays unresolved. The 2025 application form has no recorded origin. The
submission's binding to a call identifier is still declared rather than evidenced.

Report: `plans/reports/v09_authority_matrix_2026-10-13.md`. Decision record:
`docs/tier4_orchestration_state/decision_log/msca-dn-authority-matrix_2026-10-13.json`.

**Status 2026-10-12, first pass.** Four of five criteria closed; criterion 1 half closed, with the obtaining
assigned to the operator. The source half of F05 closes. V09 no longer blocks V10 on anything but the
four absent documents — V10 can author the historical profile from this matrix now, and its defaulted
rules will be defaulted in the profile too.

One 2025-era call document turned out to be in the tree already: the V5.0 application form, which the
form-equivalence record cited and nothing had read as an authority in its own right. It carries five
rows. The 2025 evaluation's own record carries seven more. One of those is evidenced by arithmetic:
the weighted-total formula applied to its recorded criterion scores reproduces its recorded total,
and the deriver refuses to render if it stops doing so.

The one difference found is SM-03. The 2026 form adds a Part B2 section 11 the 2025 form does not have,
so the appendix mapping's rule excluding it has no subject under the 2025 form. The historical profile
keeps the rule and records that it is vacuous.

26 rows: 12 equivalent, 1 differs, 6 defaulted, 2 unresolved and 5 era_neutral. Eighteen are
`Inferred`, seven `Assumed` and one `Unresolved`.

**Review changed five rows and added two.** The first draft carried the defect criterion 4 names. One
row called the score resolution equivalent on three recorded scores that happen to end in zero, which
is the absence of a visible difference read as agreement. The resolution is now TH-05, defaulted, with
the rule it affects and the document that would settle it; the maximum of 5.00, which the 2025 record
does print, stays TH-04.

SM-01's claim of a set equality is now measured in both directions and the deriver refuses if the
anchor sets part. AM-01 states that its claim is an inclusion, and the matrix carries the unmeasured
direction as an uncertainty. SA-05 and SA-06 were added for two harness assumptions that affect a
number. Both `operator_supplied` entries now name the field recording that provenance, and the check
reports a vouched rank with no basis.

No assessor ran, no quota was spent, and the 74.60 baseline is untouched. Both declarations are
`agent_drafted_pending_operator_review` and no row is Confirmed.

**The lane's own result is unmeasured.** The lane gains an `authority` area, declared not depended on.
Its declaration is reconciled and `tests/harness/` passes whole, but the lane was not run to completion
in this change and no lane figure is stated. The decision record declares it `Unresolved`.

**One side effect on another ticket's artifact.** The R04 declaration drafts carry an adoption-cost
scan coupled to the tree, so the authority index pinning the sanitised revision's register made the
sanitised draft and the shared checklist stale. Both were re-rendered, which is the response the scan's
own documentation states, and a successor re-render record states the hashes of the two files that
moved. The resolved-fixes draft is untouched and its older record is unedited. The re-render test now
reads the series of records rather than one named record; the invariant it enforces is unchanged.

The whole suite is 7,479 passed, 194 failed, 86 skipped. The baseline at `ab0fd35`, run in a separate
worktree, gives 205 failed. Every one of the 194 failing node ids appears in that 205, so this change
introduces no failure.

Evidence: `plans/reports/v09_authority_matrix_2026-10-12.md`; decision record
`docs/tier4_orchestration_state/decision_log/msca-dn-authority-matrix_2026-10-12.json`; artifacts
`docs/tier4_orchestration_state/msca_dn/authority/`.

## V10 — Author the historical 2025 profile from the matrix

**Gate:** G3. **Closes:** F05. **Blocked by:** V09.

**Problem.** The only DN profile at this revision is `msca_dn_2026_default.json`, labelled for 2026
resubmission-readiness. Assessing the 2025 original under it would score a historical submission by a
later year's configuration.

**What to build.** A distinct historical profile that loads, scores an example and traces every rule to
the V09 matrix.

### Acceptance criteria

- [x] A separate profile file exists with its own `profile_id`, label and `target_call`, bound to the
      matrix row by row. `harness/profiles/msca_dn_2025_historical.json`, profile id
      `msca_dn_2025_historical`, target call `HORIZON-MSCA-2025-DN-01` with the opening and deadline
      the work programme states. **Bound in both directions.** 13 elements name the matrix rows that
      establish their 2025 value, and every one of the matrix's 27 rows is read by some element: a row
      nobody reads refuses, because it would be a rule the profile ignores in silence.
- [x] Criteria, weights, thresholds, rubric set, scorecard, appendix mapping, structural authority and
      implementation mode are each sourced from the matrix or carry a declared unresolved limitation.
      Two carry one. `target_call` names CI-01, because the call exists and this submission's binding
      to it does not. `scorecard` names EI-02, because every scoring rule it carries is sourced and
      the form version the evaluators used is not established. **An element sourced to an open row
      refuses,** which is the defect the binding exists for: it would be the profile claiming the
      matrix settled what the matrix recorded as open. The rubrics are neither sourced nor limited.
      They are declared this harness's own instrument against the matrix's era-neutral rows, because
      no call document of either year states them, and an element declared that way whose row is a
      call's rule refuses.
- [x] Profile-loading and example-scoring tests pass, and the 2026 profile is unchanged. Both profiles
      load through one loader; a second loader would be a second contract. The historical profile pins
      the 2026 profile's sha256, so an edit to it fails the check and a test. 28 tests over the
      committed profile, 21 over a synthetic profile and matrix.
- [x] The 2026 profile's own applicability question stays open for Stage B; it is not closed by this
      ticket. Nothing here reads or edits it beyond pinning its bytes.
- [x] Reuse of a historical freeze, candidate, preflight or scoring result across a different candidate
      and profile pair is refused. The refusal is the existing machinery's: the preflight compares
      `profile_id` and `profile_version` against the loaded bundle, and the freeze binds both. The two
      profiles carry different document hashes, so a report made under one is a mismatch against the
      other rather than a figure silently reused.

**Verification.** Load the profile bundle, score the committed example, and confirm the refusal of a
mismatched candidate and profile pair.

**Status 2026-10-13.** Five of five criteria closed. F05 closes: V09 closed its source half by
obtaining and pinning the 2025 authorities, and this ticket closes the profile half by authoring the
configuration those sources support.

Four things differ from the 2026 profile, each traced to a matrix row. The target call and its dates
come from the work programme the call was opened under. The structural authority is the 2025
application form at version 5.0, not the 2026 template at 6.0. The appendix mapping's exclusion of a
Part B2 section the 2025 form does not have is kept and recorded as vacuous. And the 2025 evaluation
form's unweighted total out of 15 is recorded and not used, because the call's own work programme sets
the threshold on the weighted total.

**Two reasons for reuse, kept apart.** The scorecard is reused because every scoring rule it carries
is sourced to a 2025 document. The rubrics are reused because they are this harness's grading
instrument and no call document of either year states them. Collapsing those would be the error the
matrix's era-neutral verdict exists to prevent.

No assessment was run under the profile. Loading it is not evidence of a score, and no quota was
spent.

Report: `plans/reports/v10_historical_profile_2026-10-13.md`. Decision record:
`docs/tier4_orchestration_state/decision_log/msca-dn-historical-profile_2026-10-13.json`.

## V11 — Open-deferral register

**Gate:** G7 prerequisite. **Closes:** F11. **Blocked by:** None — can start immediately.

**Problem.** The approval's own terms leave matters open. The R04 criterion on draft declarations
surviving regeneration after adoption is unchecked because active adoption is deferred under D13. The
successor dispositions hold 9 `operator_confirmed`, 10 `operator_decision_required` and 10
`agent_recommended_pending_operator_review` rows. Q01 and Q03 carry qualified or deferred
interpretation. AVC-01 and AVC-02 await the original's blind output. A ticket checkbox closes none of
these.

**What to build.** One register that holds every open item, so nothing closes by inheritance.

### Acceptance criteria

- [x] The register carries the unchecked R04 criterion with its D13 precondition, all 10
      `operator_decision_required` and 10 `agent_recommended_pending_operator_review` rows, Q01, Q03,
      AVC-01, AVC-02, the single unresolved disposition marker `ESR-E-04`, and the approval record's
      original-dependent deferred table. **34 rows in seven groups, each group derived from the
      record it comes from rather than typed.** Evidence:
      `tests/test_msca_dn_deferral_register.py::TestTheRows`.
- [x] Each row names its owner, the evidence that would close it, and whether the original is required.
      22 of the 34 need the submitted original. `original_required` is a required boolean the loader
      refuses to default, and the two validation-case rows read it off their own recorded limit.
- [x] A check fails when a row is marked closed without its closure evidence.
      `harness.deferral_register.check` reports `closed_without_evidence`, and also a closure with no
      date and evidence filed against an open row. Evidence:
      `tests/harness/test_deferral_register.py::TestTheClosureRule`.
- [x] The committed approval record and dispositions are not edited. The register is a successor
      artifact that points at them. Both are bound as `immutable_evidence`, so a later edit fails the
      check; the approval record still carries the sha256 the approved dispositions pinned on
      2026-10-08.
- [x] The register states that the recorded 40 to 29 to 13 finding sequence reflects changed
      interpretation and audit rules, not 27 repaired proposal defects, and that all 15 ESR criticisms
      still have open revision work. Both statements are measured: S1 against the three audits' own
      totals, candidate hashes and document ids; S2 against the approved revision plan's 15 open and
      0 closed rows. A statement with no measurement fails the check.

**Verification.** Add a test that a closed row without evidence fails the check. Confirm the register
row count against the approved dispositions and the approval record.

**Status 2026-10-12.** Five of five criteria closed. F11 closes. Evidence:
`plans/reports/v11_open_deferral_register_2026-10-12.md`; decision record
`docs/tier4_orchestration_state/decision_log/msca-dn-open-deferrals_2026-10-12.json`. The register is
`docs/tier4_orchestration_state/msca_dn/deferrals/open_deferral_register_2026-10-12.json` with its
rendered reading beside it. No row is closed, no quota was spent, and the frozen 74.60 baseline is
untouched. V11 no longer blocks V14.

One check did not run: the acceptance lane was killed by the host for low memory on four attempts, so
its single-process result is unmeasured and the decision record declares that `Unresolved`. The
declaration reconciles (`--list`, exit 0) and all five affected test modules pass individually; no lane
figure is stated anywhere in the change. An operator run of
`py -3.10 -m harness.commands.acceptance_lane` closes it.

## V12 — Correct the PE-09 runbook

**Gate:** G2, G4 and G5. **Closes:** F04 and F12. **Blocked by:** V04, V06, V07, V10.

**Problem.** The runbook overstates what the code does. It says the fifteen freeze checks include the
planted-marker test; they do not, and planted-marker protection is exercised by transport and isolation
tests instead. It proposes historical defaulting, and its original-import instructions assume the
sanitised wrapper. It includes a cross-baseline `diff` command that is guaranteed to refuse.

It also carries Sections 4 to 6 into Stage B including the ESR comparison. It presents declared model
and temperature strings as if they were transmitted and attested.

**What to build.** A runbook that describes only what the code does, with every operational claim
traceable to a check that actually runs.

**Still open after the G4 acceptance of 2026-10-12.** That acceptance closed G4 for infrastructure
readiness over V04, V05 and V06. It closed none of the corrections below, and F04 and F12 stay open.
V12 remains blocked by V07 and V10.

### Acceptance criteria

- [x] The planted-marker claim is corrected: it is a transport and isolation test, not a runtime freeze
      step. The documented freeze check list matches `BASELINE_CHECKS` after V04. Section 5 enumerates
      the 22 conditions in the order the freeze runs them, and cites the planted-marker test among the
      transport and isolation controls instead. Both halves are measured:
      `tests/test_msca_dn_pe09_runbook.py::TestTheFreezeConditions` fails when the enumeration and the
      tuple disagree, and when either freeze heading mentions a marker.
- [x] Checkpointing's automatic default is stated, and the private handoff records the exact checkpoint
      path and preserves malformed responses and any salvage decision. Recovery is stated as no
      permission to replace an inconvenient valid sample. Section 5 states the default path under
      `--repo-root`, the three flags that change it, the discard record a malformed response leaves
      behind, the two-redraw budget, and the `salvage` command with the flags that bind its checkpoint.
- [x] The historical defaulting instruction is replaced by the V09 and V10 sourcing requirement.
      Section 3 names both profiles, the pinned source index, the matrix, the two commands that check
      the profile against them, and the two elements whose matrix rows are still open.
- [x] Original-import instructions use the V07 configuration route and the V08 dry import. Section 4
      selects `--document official_original`, prints what that configuration still needs, and points at
      `plans/msca_dn_v08_original_dry_import_procedure.md`. The five undeclared fields and the missing
      register renderer stay declared gaps.
- [x] The guaranteed-refusal cross-baseline `diff` command leaves the operational success path, replaced
      by an explicitly labelled row-by-observation comparison of the two readings. No command line names
      the public comparison, which a test asserts. The refusal is explained where the command stood, and
      the manual reading states which cause of a moved row it cannot distinguish.
- [x] Stage B reuse of Sections 4 to 6 explicitly excludes the ESR comparison, its review and its diff.
      Section 8 reuses Sections 4 and 5 and the `audit` command alone, and says why `compare`, `review`
      and `diff` do not apply.
- [x] Declared model and temperature values are described as declared identifiers. An external working
      directory is distinguished from an operating-system sandbox, and tool disabling from authorisation
      to transmit private content. Section 5 carries all three, and records that the pinned temperature
      reaches no provider: the `claude` CLI takes no temperature argument.
- [x] Every command in the runbook is verified against current help output before it is documented.
      Verified by test rather than by reading. Every documented flag is read back from that command's
      own `--help`, and every flag its parser marks required must appear on the documented line.

**Verification.** Walk each documented command against its implementation and tests. The runbook keeps
labelling PE-09 as unexecuted in this repository.

**Status 2026-10-13.** Eight of eight criteria closed. F12 closes. V12's share of F04 closes, and the
evidence half of F04 stays with V13, which this ticket now unblocks. The blockers cleared: V04, V06 and
V07 are committed, and V10 is in the tree.

The corrections are measured rather than reviewed. `tests/test_msca_dn_pe09_runbook.py` reads every
documented command line and asks each command for its own `--help`. It fails on a flag the parser does
not accept, and on a required flag the line omits. A mutation run confirmed it is not vacuous: renaming
one flag and dropping one condition name failed three checks. The module is registered in the
acceptance lane's new `handoff` area, which the historical run does not depend on.

No quota was spent. No assessor ran. No command but `--help`, `--check`, `--describe` and
`--environment` was executed,
and the frozen 74.60 baseline is untouched. Report:
`plans/reports/v12_pe09_runbook_corrected_2026-10-13.md`. Decision record:
`docs/tier4_orchestration_state/decision_log/msca-dn-pe09-runbook_2026-10-13.json`.

One test contract changed. `tests/harness/test_acceptance_lane.py` held that no box in this section is
checked, which was right while the G4 acceptance was the only thing that could have checked one. It now
holds that the section still records the acceptance closing none of these corrections, and that the
closure above names its own date and work.

## V13 — Private execution readiness receipt and its validator

**Gate:** G5. **Closes:** the evidence half of F04. **Blocked by:** V08, V10, V12.

**Problem.** The subscription assessor's controls are real: a fresh working directory outside the
repository, an empty tool list and strict MCP configuration. They are not an operating-system sandbox,
and they are not authorisation to send private proposal content to a provider. The private operator must
verify the actual CLI, version and configuration, and record the permitted processing route, before a
private run. Model and version strings are declared identifiers, not runtime attestation.

**What to build.** A receipt record holding the operator's pre-run evidence, and a validator that
refuses an incomplete or mismatched one.

### Acceptance criteria

- [x] The receipt covers the permitted processing and export route, the actual CLI version, the model
      identity, the effective settings, the rendered invocation, the isolation check, the checkpoint
      path, and a complete preflight naming its import manifest. Eight sections, each refused when
      absent. The preflight half is read from the report rather than taken from the receipt's copy.
- [x] The validator refuses an incomplete receipt and refuses one whose candidate or profile bindings do
      not match the intended Stage A pair. The candidate is named on the command line, because the
      original's document id is private. The profile is pinned by the bytes in this tree.
- [x] The receipt distinguishes an external working directory from a sandbox, and records that a
      configured temperature or token limit is claimed as transmitted only where the transport enforces
      it. A claimed sandbox is refused. A settings table read off the transport refuses both an
      overstated and an understated claim.
- [x] The isolation verification is a separate receipt from the freeze record, and neither is described
      as a check the freeze performs. A receipt citing a freeze condition or a freeze record as its own
      isolation evidence is reported.
- [x] No private content enters this repository through the receipt. The command refuses a receipt
      stored inside the repository root, and the committed template is refused on that rule.

**Verification.** Validate a complete synthetic receipt and confirm refusal for each missing field and
for a mismatched binding. The real receipt is the operator's, produced privately.

**Status 2026-10-13.** Five of five criteria closed. The evidence half of F04 closes, which closes F04
with V12. G5 has its code. The blockers cleared: V08, V10 and V12 are all in the tree.

The validator is `harness/execution_receipt.py`, read by
`py -3.10 -m harness.commands.execution_receipt`. `harness/execution_receipt_template.json` is the
form the operator fills in privately. §1.1 of the runbook documents the command, what it refuses and
what it reports.

The refusals are measured. `tests/harness/test_execution_receipt.py` builds a synthetic receipt and a
synthetic preflight report in a temporary directory, then removes or alters one thing per case. The
118 cases cover eight missing sections, every field of every section, every finding, the three
command exit codes and the committed template. The missing-field sweep is generated from the
receipt, so a field added to the schema and not to the reader fails there. Two mutation runs
confirmed the module is not vacuous: seven changes failed sixteen checks between them.

Two things the receipt does not do. It is not authorisation — §10 of the runbook governs what may
leave the private environment, and the receipt records which rule permits the processing rather than
granting it. It is not a gate: the harness is never run-blocking, and nothing here evaluates one.

No quota was spent. No assessor ran. The frozen 74.60 baseline is untouched. Report:
`plans/reports/v13_execution_readiness_receipt_2026-10-13.md`. Decision record:
`docs/tier4_orchestration_state/decision_log/msca-dn-execution-receipt_2026-10-13.json`.

One pre-existing defect was fixed to land this. The runbook guard's path scan paired backticks over
the whole document. A fenced block is three backticks, where the inline-code pattern can pair only
two, so each fence left one over and shifted the pairing of every inline span after it. Adding
§1.1's command block therefore dropped eight cited paths from the scan silently. The scan now removes
the fences before reading inline code, and reads the command lines separately, where a path is an
argument. Both floors are asserted.

## V14 — Operator: Stage A historical experiment, frozen before ESR

**Gate:** G6. **Blocked by:** V03, V05, V06, V11, V13.

**Execution boundary.** The operator performs this ticket. Claude does not run the private assessment,
does not transmit proposal content, and spends no model quota on it. Claude may prepare records and
verify deposited evidence afterwards.

**Problem.** The official original has never been evaluated here. The sanitised blind median of 74.6
against the historical ESR's 85.8 is a difference of candidate and profile, not a measured harness bias.
Stage A must establish what changes when the actual original is assessed under a justified historical
profile.

**What to build.** One controlled assessment of the official original, frozen before any ESR material
enters, then a post-freeze comparison and review.

### Acceptance criteria

- [ ] The input PDF, governing source documents, runtime and code revision are pinned privately, and
      proposal evidence is kept separate from ESR and review material.
- [ ] The original is imported as a distinct original document through V07 and V08, with fidelity
      reviewed against the actual submitted material including figures and the declared appendix
      mapping, and unresolved extraction limitations recorded before assessment.
- [ ] The V10 historical profile is loaded, and preflight runs with the actual transport, an explicit
      manifest and the declared grounding scope. Both expectation-pack selections and whole-criterion
      inputs are reviewed.
- [ ] One blind assessment runs under the declared sample plan with response checkpointing. A resume
      replays saved responses rather than redrawing a failed run, and no valid sample is silently
      replaced.
- [ ] The complete report validates and freezes under the V04 gate before any ESR material enters, with
      actual invocation and isolation evidence and the candidate and profile bindings recorded.
- [ ] Only then does the ESR enter comparison. Original dispositions and fidelity declarations are
      authored to schema, the integrity audit runs with V05 provenance, and every criticism and strength
      classification is reviewed.
- [ ] Missed findings, false positives, the 8 contested strengths and the criterion deltas are
      evaluated, with AVC-01 and AVC-02 investigated at sample level.
- [ ] Each divergence carries a recorded diagnosis — evidence omission, extraction, rubric
      interpretation, assessor error, historical subjectivity or unresolved cause — rather than pursuit
      of a target score.
- [ ] The sanitised 74.60 baseline, its freeze record, the approved dispositions and the approved
      comparison are preserved unchanged. The new result is a successor record.
- [ ] No numerical deduction is inferred for a criticism the ESR does not quantify, and the −11.2
      sanitised delta is not carried forward as a predictor.
- [ ] Within-assessor spreads are reported as repeatability only, never as an accuracy interval or a
      panel of independent reviewers.

**Verification.** The frozen original baseline, the post-freeze comparison, the integrity audit and the
diagnosis record are the evidence. Claude verifies the deposited bindings; it does not produce the
assessment.

## V15 — Milestone acceptance record

**Gate:** G7. **Blocked by:** V14.

**Execution boundary.** The operator decides and signs. Claude drafts the record and verifies its
bindings. An inherited approval, a generated report, a listed command or an empty placeholder is not
closure evidence.

**What to build.** A signed acceptance of V14's evidence and its residual limitations, scoping what 2026
work may begin.

### Acceptance criteria

- [ ] The record names the candidate hash, profile version, code revision and frozen report hash of the
      historical result.
- [ ] It states whether imported-source grounding was validated or explicitly unassessable, matching the
      V06 declared scope. A source-grounded acceptance requires X01; a content-focused acceptance states
      that scope plainly.
- [ ] Residual uncertainties, deferred matters and their owners are listed, and every V11 register row is
      resolved or explicitly carried forward with its owner.
- [ ] A prioritised revision backlog is attached, with the source and human-confirmation requirement for
      each item.
- [ ] The record carries an approval identity, date and reference, and references G1 to G6 closure
      evidence.
- [ ] Preparing the Stage B lane is **not** a precondition. The record names V16 as downstream work and
      may be signed with V16 unstarted.
- [ ] Advisory status is restated: the result is not a funding forecast, and one proposal establishes no
      population-level predictive accuracy.

**Verification.** Check every named hash and path against the checkout. Leave the record unsigned until
the operator signs it.

---

# Downstream backlog — Stage B resubmission

**Not part of the historical-validation milestone.** V16 is downstream of V15. Nothing here is required
to accept the frozen 2025 baseline, and no V15 criterion depends on it.

## V16 — Stage B lane: the 2026 candidate, profile and scoring process

**Blocked by:** V15.

**What to build.** The revised proposal is assessed as a new candidate under its own applicable profile,
never against the historical freeze.

### Acceptance criteria

- [ ] Human-approved scientific and programme changes land in authoritative inputs before drafting.
      Numerical targets, access claims, partner commitments, study design and timing each carry their
      required human confirmation.
- [ ] The revised proposal imports as a new candidate with its own manifest, register and declarations,
      preflight, assessment, audit and report bindings.
- [ ] The resubmission profile's applicability is confirmed for Stage B. No historical freeze, candidate,
      preflight or scoring result is reused across a different candidate and profile pair.
- [ ] The ESR informs the human revision plan and is excluded from the Stage B blind assessor's evidence.
      The two beyond-ESR improvements stay labelled as such.
- [ ] Scores are reported as advisory. No target score and no narrow repeatability spread is presented as
      a funding forecast, and there is no future ESR to compare at this stage.

---

# Conditional enhancements

These block no gate. Each is scheduled when the claim or workflow that needs it is actually made.

## X01 — Imported-source grounding route

**Condition:** mandatory only if the grounding scope selected at V06 and declared at V15 asserts
source-grounded evaluation. **Closes:** the conditional half of F07. **Blocked by:** V06, V08.

**What to build.** The three missing integrations the runbook identifies: imported-section claim loading
with resolvable sources, supported statuses backed by evidence, and E2 grounding over that ledger.

### Acceptance criteria

- [ ] Imported-section claims load with resolvable sources, replacing the 45 unresolved claims per
      revision with evidenced statuses where evidence exists.
- [ ] E2 grounding runs over that ledger, and grounding is reported as assessed rather than unassessable.
- [ ] A source span inside the proposal is not treated as independent proof of a partner commitment, an
      access entitlement or a scientific result.
- [ ] Until this ticket closes, any source-grounded declaration at V06 or V15 is refused.

## X02 — Populate DN project entities and `addresses` edges

**Condition:** required before claiming trace-driven engineering or graph-assisted drafting.
**Closes:** F09. **Blocked by:** V03.

**Problem.** The workspace holds 354 nodes — 2 artifact versions, 90 claims, 6 passages, 168 sources, 88
source spans — and 273 edges across `expressed_in`, `supported_by` and `supersedes`. It has no
participant, objective, work-package, task, deliverable or milestone nodes and no `addresses` edges.
Work-plan rows parsed from section content are not a populated engineering graph.

### Acceptance criteria

- [ ] The relevant authoritative Tier 3 entities, their provenance and passage-to-entity links are
      populated and tested for the selected workflow.
- [ ] Until then, no claim is made that the research plan can be revised, traced or invalidated
      automatically through graph relationships.

## X03 — Human DN calibration and gold datasets

**Condition:** required before any accuracy or comparative-performance claim. **Closes:** F10.
**Blocked by:** V03.

**Problem.** Calibration machinery exists and its tests pass, but `harness/gold_sets/` and
`harness/regression_baselines/` hold only READMEs. Historical E3 adjudication under a different judge is
not evidence that the current DN scorer is calibrated.

### Acceptance criteria

- [ ] Expert-labelled DN validation data exists and is maintained, lifting the V02d exclusions.
- [ ] A release-status table separates current code, usable datasets, live-model evidence and known
      failing fixtures.
- [ ] Five draws from one assessor are never described as five independent expert reviewers.

## X04 — Cross-baseline comparison tool

**Condition:** convenience only. **Blocked by:** V04.

**Problem.** The existing same-baseline `diff` correctly refuses comparisons across different frozen
baselines. V12 removes the guaranteed-refusal command from the success path.

### Acceptance criteria

- [ ] A cross-baseline comparison, if built, preserves every binding check and states which baselines it
      spans.
- [ ] Its absence never delays the historical experiment, and it is not a route around a binding check.

---

## Completion report for each ticket

Record the changed files, the actual checks run and their results, the preserved artifact bindings, the
remaining uncertainties and the successor artifact paths. If a broader failure is called pre-existing,
supply the baseline comparison that supports the statement. State scoped exceptions as exceptions. Do
not call a ticket fully accepted while its required operator judgment is still pending, and do not
report that a deliverable passed a check that did not run.
