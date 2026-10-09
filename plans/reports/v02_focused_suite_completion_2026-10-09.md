# V02a–V02d completion report — the focused suite, reconciled

Date: 2026-10-09.
Branch: `msca-dn-pre-eval`.
Tickets: V02a, V02b, V02c, V02d of `plans/msca_dn_historical_validation_tickets.md`.
Closes: V02b, V02c and V02d in full.
Partial: V02a, whose second criterion needs V05.
Does not close: F08, which closes at V03. No gate closes here.

## Environment

Python 3.10.6 and PyMuPDF 1.28.2 over MuPDF 1.28.2, the pin established by V01
(`docs/tier4_orchestration_state/decision_log/msca-dn-extraction-environment-pin_2026-10-08.json`).
Tests run as `py -3.10 -m pytest`.

## The measured starting point

The audit's focused command reported 1,864 passed, 44 failed, 48 errors and 8 skipped at `ca0a443`.
Re-running it at the head of this branch, under the V01 pin and before any change here:

| Result | Audit at `ca0a443` | Head of branch, before V02 | After V02a–V02d |
|---|---:|---:|---:|
| Passed | 1,864 | 1,938 | 1,965 |
| Failed | 44 | 13 | 0 |
| Errors | 48 | 5 | 0 |
| Skipped | 8 | 8 | 17 |
| Collected | 1,964 | 1,964 | 1,982 |

V01 accounts for the fall from 44/48 to 13/5. The audit's instruction was to resolve F01 first and then
reclassify what remained; that reclassification is the table below. The audit's own figure of 1,864
passed is not comparable case-for-case, because V01 and the work here both added cases.

### The whole repository, and how the comparison was made

A whole-run count is not a stable number in this repository: the same invocation returns different
counts on consecutive runs, because some modules depend on execution order. Failing **identifier sets**
are compared instead, as the R02 and R04 records established.

The baseline is the whole suite on a fresh worktree at the pre-change commit `3b4cde8`. The comparison
run is the whole suite on the working tree with this work applied:

| | Failing ids |
|---|---:|
| Baseline, worktree at `3b4cde8` | 220 |
| After V02a–V02d | 194 |
| New failures introduced | **0** |
| Baseline failures now resolved | 26 |

The 194 remaining are concentrated in `tests/runner/test_skill_runtime*.py`, the phase artifact-production
modules and `tests/test_transport_*.py`. None is in a module this work touched, and none was introduced
here. Eight of the 26 resolved are demo checks that fail only on a fresh worktree, which lacks the
untracked run records they read. Those were never defects of this work, and are not claimed as its
result. The other 18 are the checks the tickets name.

This comparison caught one regression this work did introduce. The V02d decision record named the
instance-one project in Tier 4, which the anonymity scan forbids, and seven leakage and anonymity checks
failed. The noun was replaced with `instance-one`, the sanctioned term in the decision log, and all
seven pass.

## Family-by-family reclassification

The audit named eight principal failure families. Each one's current state:

| Audit family | At `ca0a443` | Now | Ticket |
|---|---|---|---|
| MSCA-DN import, workspace, fidelity, adoption fixtures | 29 failures, 43 errors | 317 pass, 0 fail | V02a |
| Integrity-audit integration | 2 failures on regenerated identity | 95 pass, 0 fail; wording still pre-V05 | V02a part |
| Claim-ledger real-data checks | 4 failures on stale counts | Pass against a declared pin | V02b |
| Evidence-pack real-data checks | 3 failures on a section/profile mismatch | Pass against a declared pairing | V02b |
| Rubric-report fixture | 1 failure | Excluded: the data is not in the tree | V02c |
| T03 harness integration | 1 failure, no criterion `shortcomings` | Pass; the refusal has its own test | V02c |
| Subscription-judge cwd refusal | 1 failure on a fresh checkout | Pass; the test builds its fixture | V02c |
| Ledger-granularity and regression goldens | 3 failures, 5 errors | Excluded, with a written disposition | V02d |

## V02a — document-identity-dependent fixtures

**The count, reconciled against the audit's figures.** The audit measured its MSCA-DN integration
group — `tests/test_msca_dn*.py` — at 242 passed, 29 failed and 43 errors over 314 cases. That group now
collects 317 cases, 317 of them passing: the six modules are green, and the three added cases are this
work's own. The integrity-audit integration lives in `tests/harness/test_integrity_audit.py`, not in
that group; it is 95 passed, 0 failed. V01's extraction pin, not any change here, closed the import,
workspace, fidelity-register and adoption families.

**Criterion 2 is partially satisfied, and the ticket's box stays open.** The criterion reads: *"The two
integrity-audit integration failures pass against the reproduced document identity and the V05
provenance-derived wording."* The first half holds — both pass against the reproduced identity. The
second half cannot: V05 is open, no wording was derived from candidate provenance, and nothing here
touched `harness/integrity_audit.py`, whose grounding reason is still a module constant. The failures
pass under the *existing* wording. That wording is wrong for the official original, which is V05's
subject and why V05 blocks V02a. Criterion 2 closes when V05 lands and these two checks are re-run
against provenance-derived wording, not now.

**One residual failure, diagnosed and fixed.** `tests/test_msca_dn_declaration_drafts.py::
TestDeterminismAndTheCommittedArtifacts::test_the_committed_artifacts_are_reproducible` failed because
the three committed declaration drafts were stale. Their adoption-cost scan is coupled to the
repository tree by design, so the three artifacts added since they were last rendered — V01's two and
the audit report itself — belong in their dependent lists. The drafts were re-rendered by their own
tool. Two sha256 values pinned by the 2026-10-08 approval record no longer describe those files; the
old and new values, the reason, and the scope of what the approval record still binds are in
`docs/tier4_orchestration_state/decision_log/msca-dn-declaration-draft-rerender_2026-10-09.json`. The
approval record is left exactly as written.

**For the operator: the approval record's bindings now measure 24 of 26.** The audit recorded 26 of 26.
The two that moved are the two draft hashes above, and nothing else in the record changed. Re-rendering
is the maintenance the R04 ticket prescribed for this exact staleness. The drafts are generated review
material, not historical evidence: they are absent from the shared constraints' immutable list, their
`review_state` is unchanged, and no test reads those two pins. The alternative was to leave
`--check` red.

Still, the approval package is the operator's. The change is named here rather than left in a decision
record alone, and it wants an acknowledgement.

No fixture was edited to encode a hash the importer no longer produces. No register changed, and the
remaining 24 bindings were re-verified against the files on disk.

## V02b — the real-data pairings

**Claim ledger.** The expectations were the FIELDWISE drafter-era numbers, and that data is not in the
repository: the purge removed those sections and the graph compiler wrote the BIODIV-01 sections now
committed. Reconciled against the committed artifacts:

| Expectation | Old (drafter-era) | New (measured 2026-10-09) |
|---|---|---|
| Sub-sections across the three sections | 12 | 7: `B.1.1`–`B.1.2`, `B.2.1`–`B.2.3`, `B.3.1`–`B.3.2` |
| Excellence ledger entries | 191 | 50, of which 49 distinct after dedup |
| Impact ledger entries | not pinned | 68, 59 distinct |
| Implementation ledger entries | not pinned | 62, 57 distinct |
| The ambiguous-id probe | three `C01` entries in excellence | `kpi_targets` in impact, three distinct claims |
| The lexical-shortlist probe | a claim naming the old project's crop | `copernicus_eligibility` |

The reason for every change is the same: these are different sections of a different project. The
ambiguous-id probe moved sections because the graph compiler writes semantic claim ids, so excellence
now carries no repeated id at all and the property is untestable there.

Every number lives in one `REAL_SECTIONS_PIN` constant that names its source and its measurement date,
and one test compares the pin against the files. A recompile fails that test with a message saying to
re-pin and state the old value, the new value and the reason — the discipline this section follows.
Counts and ids only, never a byte hash: `.gitattributes` protects the hashed trees deliberately, and
`docs/tier5_deliverables/` is not among them.

**Evidence packs.** The failure was a pairing the test never declared. `default_profile` resolves to
MSCA-PF, whose rubrics anchor at `1.1`–`3.2`; the committed sections are RIA, anchored `B.1.1`–`B.3.2`.
The anchor map failed closed on every pack build, which was correct behaviour on a wrong pairing. The
real-file class now declares `harness/profiles/ria_default.json`, and a new test asserts the pairing
itself: every rubric's anchors exist in the section its profile routes the criterion to. Pointing the
constant back at the PF profile makes that test fail first, with both sides named.

## V02c — the stale synthetic contracts

**Rubric-report standing lane.** The lane pinned the FIELDWISE 13B spine state by count and by fact id:
9 spine items, 10 project decisions, `HOST`/`FELLOW`/`SUPERVISOR`. The purge removed the Tier 3
instantiation that carried them, so `docs/tier3_project_instantiation/call_binding/confirmation_checklist.json`
does not exist and the loader failed closed. The change went in one direction, towards the engine: those
counts and ids are project data, not engine invariants, and `CLAUDE.md` §2 puts the engine at a
project-agnostic default. The lane now asserts what the engine owns — a present checklist loads, carries
both fact kinds, speaks the §12.2 vocabulary and leaves nothing unconfirmed — and records an absent
checklist as a skip naming the reason. The loader's own contract is unchanged and still covered by the
fixture tests in the same module.

**T03 end-to-end.** The scripted assessor returned only a pass/fail verdict, so the criterion scorer
refused every draw and the command exited 2. The walk was measuring a refusal rather than the path it
was written for. The scripted backend now answers the criterion prompt with the shape the scorer parses,
reading the score off the scale the prompt declares, so a profile may still change its scale through
configuration. The refusal kept its own test: `NoShortcomingsBackend` drops the `shortcomings` list, and
the test asserts exit 2, no report written, and the draws left on a checkpoint a resume can read.
Removing `required=True` from the scorer's `shortcomings` check makes that test fail — verified, then
reverted. No fail-closed behaviour was relaxed.

**Subscription-judge cwd refusal.** `_check_working_dir` tests existence before containment, so on a
fresh checkout — where `.claude/runs` is untracked and absent — the inside-the-repository test was
refused for the path being *missing* and asserted the wrong rule. A fixture now builds the directory and
removes only the levels it created. A second test asserts the distinction directly: the directory
exists, so `does not exist` cannot fire, and the message must name containment.

## V02d — the missing datasets

Both dataset directories hold only their READMEs. Every dependent check is **excluded**, not restored:

- `harness/gold_sets/`: a gold set is human ground truth, and this repository's own rule is that an AI
  labelling a gold set for an AI judge reintroduces the correlation the harness exists to detect. An
  agent cannot produce it. Ticket X03 lifts it.
- `harness/regression_baselines/`: a refreeze is deterministic and available, but the E4 lane is
  merge-advisory and human-decided by its own documented contract, so the choice is the operator's. A
  refreeze would also replace the drafter-era side of the LG-1 granularity measurement, which that
  suite's docstring names as work to budget alongside it.

`harness/DATASET_DISPOSITIONS.md` holds fourteen rows covering seventeen individual checks: one row
stands for four. Each row gives its substrate, its reason, its replacement evidence where any exists,
and the work that lifts it. Those seventeen are every skip the focused command reports: thirteen for the
two dataset directories, two for the absent Tier 3 confirmation checklist, and two for the unfrozen E5f
artifacts. The last four were added when the review of this work found them excluded on disk but
missing from the table.

Both dataset READMEs and `harness/HARNESS.md` point at that document, so a reader cannot reach a green
lane without meeting the absence. A test module, `tests/harness/test_dataset_dispositions.py`, keeps the
list honest in both directions. An exclusion missing from the table fails. So does a row naming a module
that does not exist, and so does an excluded module that omits the document from its own skip reason.
The decision is recorded at
`docs/tier4_orchestration_state/decision_log/msca-dn-dataset-dispositions_2026-10-09.json`.

The drafter-era numbers the granularity suite measured survive in the commit that recorded them,
`32b5606`; the record itself was removed from the working tree by `da9f846`.

## What this report does not claim

No refusal, isolation or fail-closed behaviour was weakened to make a check pass. One lane did lose
assertions: the rubric-report standing lane no longer pins nine spine items, ten project decisions and
three named fact ids, because that project's data is not in the repository. It pins the engine contract
instead, which is a narrower claim, and the V02c section above says so.

No dataset was created. No calibration ran, and the 17 skips are 17 absences, not 17 passes. The suite being green is not coverage of the acceptance
invariants: the audit's own observation stands that the passing baseline tests did not catch the defects
the freeze probes reproduced, which is V04's work. V03 is the ticket that names the acceptance lane and
publishes its exception list; this report is its input, not its substitute.
