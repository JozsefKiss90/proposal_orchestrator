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
- [ ] The two integrity-audit integration failures pass against the reproduced document identity and
      the V05 provenance-derived wording. **Open; owner V05.** The first half holds. The second half
      is V05's to close, and V05 carries it as its own sixth criterion.
- [x] Any residual failure is classified as a real defect with a named cause, not carried as
      pre-existing without evidence.
- [x] No fixture is edited to encode a hash the importer no longer produces.

**Verification.** Run the MSCA-DN integration modules and the integrity-audit tests under the V01 pin.


**Status 2026-10-09.** Three of four criteria closed. Criterion 2 stays open: both integrity-audit checks pass against the reproduced document identity, but under the existing wording, because V05 is open and no wording was derived from candidate provenance. It closes with V05. Evidence: `plans/reports/v02_focused_suite_completion_2026-10-09.md`.

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
      checks, and runs under the V01 environment pin. Those seven areas plus five more cover 62 modules;
      the lane refuses to certify a result on a build not measured to reproduce the imports.
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

- [ ] Freeze enforces the profile's exact expected cell and criterion identity sets and their
      cardinalities, and rejects duplicate cell or criterion entries.
- [ ] Freeze verifies member counts, score ranges, medians, spreads and the declared sample count
      against the entries actually present.
- [ ] Freeze recomputes the weighted total from the criterion scores under the profile's
      `10E + 6I + 4Q` and refuses an inconsistent aggregate.
- [ ] Freeze requires transport-appropriate invocation and isolation evidence; a report with
      `assessor_invocation` removed is refused.
- [ ] All four reproduced negative probes are refused with a check name and a reason, and focused
      negative tests cover each.
- [ ] The unmodified control still passes, and the committed `blind_baseline_f60ae6e0a2a1.json` still
      validates with its recorded total of 74.6.
- [ ] `checks_passed` remains derived from checks that actually ran. Immutable report copies and
      one-freeze-per-directory behaviour are preserved.

**Verification.** Exercise the real `freeze_baseline` path on isolated copies with the real candidate
and loaded profile bundle, as the audit did. Write only to a temporary directory. Do not rerun the whole
repository in place of focused negative tests.

## V05 — Derive audit grounding and identity wording from candidate provenance

**Gate:** G4. **Closes:** F06. **Blocked by:** None — can start immediately.

**Problem.** `harness/integrity_audit.py` sets the grounding reason to the module constant
`"supporting sources removed by sanitisation"` and expects imported ledger claims to stay `unresolved`.
It also carries sanitisation-specific explanations for host-identity limitations. Applied unchanged to
the official original, that wording would misstate why corroboration is missing, even where the
original carries references and real identities.

**What to build.** The audit states the true reason for whichever candidate it reads.

### Acceptance criteria

- [ ] The grounding reason and the host-identity explanations derive from the imported candidate's
      recorded provenance and capabilities, not from a constant applied to every document.
- [ ] Expected claim status comes from the candidate's own ledger rather than a hard-coded `unresolved`
      assumption.
- [ ] Table schema and identity comparisons are revalidated for a document carrying references and real
      identities. An anonymised-host assumption is never applied as an original-document rule.
- [ ] Both committed sanitised audits, `integrity_242f1afb02c8_0003.json` and
      `integrity_13ad3ad81d7e_0001.json`, reproduce byte-equal.
- [ ] A candidate whose provenance does not state a grounding cause yields an explicit Unresolved
      reason, not a borrowed one.
- [ ] **Inherited from V02a criterion 2.** The two integrity-audit integration checks pass against the
      provenance-derived wording, not only against the reproduced document identity. V02a closed its
      first half on 2026-10-09 and left this half open; V03 transferred it here rather than closing it
      as a pass. Evidence: `plans/reports/v02_focused_suite_completion_2026-10-09.md` and
      `plans/reports/v03_acceptance_lane_completion_2026-10-09.md`.

**Verification.** Regenerate both committed audits and diff the bytes. Add a test that a non-sanitised
candidate configuration produces a different, provenance-derived reason.

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

- [ ] Preflight, report and freeze each record a declared grounding scope.
- [ ] A `--no-claims` run reports grounding as **unassessable** prominently, rather than as absent or as
      zero findings.
- [ ] The freeze binds the declared scope, so a later stage cannot present an unassessable run as
      source-grounded.
- [ ] The acceptance-record template states which of the audit's two scope choices was performed:
      content-focused with grounding unassessable, or source-grounded.
- [ ] A source-grounded declaration is refused unless the X01 imported-claim route is implemented and
      validated.

**Verification.** Freeze an unassessable run and a scope-mismatched run on copies; confirm the first
carries the declaration and the second is refused.

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

- [ ] Workspace location, title, expected page count, section and subsection maps, criterion heading
      and page anchors, beneficiary marker, source-id format, intake id and the submitted-document flag
      all move into a selectable document configuration.
- [ ] A configuration for the official original exists with its own identity and role, renders
      `is_submitted_document: true`, and inherits no sanitised page map, 84-page assumption or
      derivative description.
- [ ] The original is not made a descendant of the sanitised version to reuse its version chain.
- [ ] Both existing sanitised configurations reproduce byte-equal under the V01 pin, and both `--check`
      commands still pass.
- [ ] A configuration missing a required field fails closed, naming the field.

**Verification.** Reproduce both sanitised configurations byte-equal, then select the original
configuration and confirm it refuses to run without its own page map and provenance.

## V08 — Dry-import inventory and original-provenance records

**Gate:** G2. **Closes:** the review half of F02. **Blocked by:** V07.

**Problem.** Extraction accounting is not semantic fidelity. Normalised character counts and row
accounting prove neither reading order, cell association, mathematical meaning, image content nor
figure completeness, and character deficits and surpluses can offset inside an aggregate. The original
needs a manual reconciliation against the PDF before it is assessed.

**What to build.** A dry import the operator can run privately, producing an inventory to reconcile
against the PDF, plus the records that hold the result.

### Acceptance criteria

- [ ] A dry-import mode reports measured section, table and figure inventory, page count and extraction
      limitations without writing graph state.
- [ ] Separate intake and original-document provenance records exist, including the authenticated input
      hash of the original PDF.
- [ ] A fidelity acceptance record covers Gantt, diagrams, embedded images, footnotes, table headers,
      bibliographic references and any supporting Part B material explicitly.
- [ ] Neither zero character loss nor zero embedded images is accepted as proof that graphical evidence
      was preserved.
- [ ] Unresolved extraction limitations are recorded before assessment, and the record states that a
      page or source span locates an assertion without corroborating it.
- [ ] The private original PDF and its derived text are not committed to this repository.

**Verification.** Run the dry import on a non-sensitive fixture document in the test suite, and document
the operator procedure for the real original. The operator performs the real dry import.

## V09 — Pin the 2025 authority documents and build the equivalence matrix

**Gate:** G3. **Closes:** the source half of F05. **Blocked by:** None — can start immediately.

**Problem.** The audit did not obtain or authenticate the 2025 call documents, and their absence is
itself a readiness finding. The runbook proposes copying the 2026 profile and leaving a rule unchanged
where no source states a difference. That is a defaulting policy, not evidence that the rule applied in
2025.

**What to build.** The 2025 authority sources pinned by hash, and a matrix in which every
scoring-relevant rule is either sourced or declared unresolved.

### Acceptance criteria

- [ ] The 2025 call and work-programme documents are obtained, authenticated and pinned by hash in a
      source index.
- [ ] A matrix covers criteria, weights, thresholds, evaluator instructions, DN variant, section and
      appendix mapping, and every scoring assumption that affects interpretation or a number.
- [ ] Each row cites a pinned source for equivalence or difference, or is marked an explicit unresolved
      limitation.
- [ ] No row is marked equivalent because no difference was found. Defaulting is recorded as defaulting,
      with the rule it affects named.
- [ ] Form-equivalence records are not treated as equivalence of every historical call rule.

**Verification.** Every matrix row resolves to a pinned document and a located passage, or to a recorded
Unresolved status. The operator supplies the source documents.

## V10 — Author the historical 2025 profile from the matrix

**Gate:** G3. **Closes:** F05. **Blocked by:** V09.

**Problem.** The only DN profile at this revision is `msca_dn_2026_default.json`, labelled for 2026
resubmission-readiness. Assessing the 2025 original under it would score a historical submission by a
later year's configuration.

**What to build.** A distinct historical profile that loads, scores an example and traces every rule to
the V09 matrix.

### Acceptance criteria

- [ ] A separate profile file exists with its own `profile_id`, label and `target_call`, bound to the
      matrix row by row.
- [ ] Criteria, weights, thresholds, rubric set, scorecard, appendix mapping, structural authority and
      implementation mode are each sourced from the matrix or carry a declared unresolved limitation.
- [ ] Profile-loading and example-scoring tests pass, and the 2026 profile is unchanged.
- [ ] The 2026 profile's own applicability question stays open for Stage B; it is not closed by this
      ticket.
- [ ] Reuse of a historical freeze, candidate, preflight or scoring result across a different candidate
      and profile pair is refused.

**Verification.** Load the profile bundle, score the committed example, and confirm the refusal of a
mismatched candidate and profile pair.

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

- [ ] The register carries the unchecked R04 criterion with its D13 precondition, all 10
      `operator_decision_required` and 10 `agent_recommended_pending_operator_review` rows, Q01, Q03,
      AVC-01, AVC-02, the single unresolved disposition marker `ESR-E-04`, and the approval record's
      original-dependent deferred table.
- [ ] Each row names its owner, the evidence that would close it, and whether the original is required.
- [ ] A check fails when a row is marked closed without its closure evidence.
- [ ] The committed approval record and dispositions are not edited. The register is a successor
      artifact that points at them.
- [ ] The register states that the recorded 40 to 29 to 13 finding sequence reflects changed
      interpretation and audit rules, not 27 repaired proposal defects, and that all 15 ESR criticisms
      still have open revision work.

**Verification.** Add a test that a closed row without evidence fails the check. Confirm the register
row count against the approved dispositions and the approval record.

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

### Acceptance criteria

- [ ] The planted-marker claim is corrected: it is a transport and isolation test, not a runtime freeze
      step. The documented freeze check list matches `BASELINE_CHECKS` after V04.
- [ ] Checkpointing's automatic default is stated, and the private handoff records the exact checkpoint
      path and preserves malformed responses and any salvage decision. Recovery is stated as no
      permission to replace an inconvenient valid sample.
- [ ] The historical defaulting instruction is replaced by the V09 and V10 sourcing requirement.
- [ ] Original-import instructions use the V07 configuration route and the V08 dry import.
- [ ] The guaranteed-refusal cross-baseline `diff` command leaves the operational success path, replaced
      by an explicitly labelled row-by-observation comparison of the two readings.
- [ ] Stage B reuse of Sections 4 to 6 explicitly excludes the ESR comparison, its review and its diff.
- [ ] Declared model and temperature values are described as declared identifiers. An external working
      directory is distinguished from an operating-system sandbox, and tool disabling from authorisation
      to transmit private content.
- [ ] Every command in the runbook is verified against current help output before it is documented.

**Verification.** Walk each documented command against its implementation and tests. The runbook keeps
labelling PE-09 as unexecuted in this repository.

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

- [ ] The receipt covers the permitted processing and export route, the actual CLI version, the model
      identity, the effective settings, the rendered invocation, the isolation check, the checkpoint
      path, and a complete preflight naming its import manifest.
- [ ] The validator refuses an incomplete receipt and refuses one whose candidate or profile bindings do
      not match the intended Stage A pair.
- [ ] The receipt distinguishes an external working directory from a sandbox, and records that a
      configured temperature or token limit is claimed as transmitted only where the transport enforces
      it.
- [ ] The isolation verification is a separate receipt from the freeze record, and neither is described
      as a check the freeze performs.
- [ ] No private content enters this repository through the receipt.

**Verification.** Validate a complete synthetic receipt and confirm refusal for each missing field and
for a mismatched binding. The real receipt is the operator's, produced privately.

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
