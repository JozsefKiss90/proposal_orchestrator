# PE-09 private-network runbook (ticket R06, corrected by V12)

Date: 2026-10-08. Corrected 2026-10-13 under ticket V12.
Branch: `msca-dn-pre-eval`
Status: **preparation only. PE-09 is not executed in this repository.** Every step below runs
inside the approved private environment, by its operator, under its rules.
Authority: `plans/msca_dn_pre_evaluation_spec.md` (PE-09, "declared, not built"); the operator
approval of 2026-10-08,
`docs/tier4_orchestration_state/msca_dn/reviews/operator_approval_2026-10-08.md` (D15 permits
this preparation; D09, D10, D12, D13 and the deferred table bound it).

Two kinds of line appear below. A line in a code block with a `py -3.10 -m` prefix is a command
whose flags exist on this build. A line marked **[future]** names work no tool does yet. Nothing
here is a result.

The command lines are measured rather than reviewed. `tests/test_msca_dn_pe09_runbook.py` reads
every one of them and asks each command for its own `--help`. It fails when a documented flag is
not one the parser accepts, and when a required flag is missing from the line. It also checks that
the freeze conditions listed in §5 are the ones the code runs, and that every path cited here
exists.
V06 is why: it made `--grounding-scope` required, and every documented command line was wrong
until it was corrected.

## 0. What this runbook separates

| Stage | Candidate | Profile | What it establishes |
|---|---|---|---|
| A. Historical validation | the submitted original, imported privately | the 2025 historical profile (§3) | whether a blind assessment of the original reproduces the ESR's findings and scores |
| B. Final resubmission | the revised proposal, imported as a new candidate | the profile of the call being submitted to | an advisory pre-evaluation of what will be submitted |

The two never share a candidate, a preflight, a baseline or a report. The ESR enters stage A only
after its baseline is frozen, and never enters stage B at all.

## 1. Private-environment prerequisites

Before any command runs, the private environment must hold:

- The submitted original (Part B, the PDF as submitted) and its sha256, taken from the
  authoritative source rather than from the copy to be measured.
- A private clone of this repository at the revision the decision log names
  (`docs/tier4_orchestration_state/decision_log/msca-dn-operator-approval_2026-10-08.json`).
- The environment's own rules on what may leave it (§10). This runbook invents none.
- The operator's own evidence about the assessor: which `claude` CLI, which version, which
  configuration, and which processing route the environment permits. A readiness receipt records it,
  and §1.1 validates that receipt before the run.
- The deferrals and validation cases in §2, each read before the stage it belongs to.

Nothing from the private environment is written back into this public workspace except what §10
permits.

### 1.1 The readiness receipt

The receipt is the operator's pre-run evidence. `harness/execution_receipt_template.json` is the
form to fill in, in the private environment. It covers eight things:

- the permitted processing and export route;
- the `claude` CLI version, as the CLI printed it;
- the model pin;
- every configured setting, with whether the transport sends it;
- the rendered argv;
- the isolation verification;
- the checkpoint path;
- the preflight the run is bound to.

```
py -3.10 -m harness.commands.execution_receipt --receipt <private receipt path> --expect-candidate <original document id> --expect-profile harness/profiles/msca_dn_2025_historical.json
```

It exits 0 when the receipt is complete and bound to the intended Stage A pair. It exits 1 on a
finding, and 2 when it refuses to read the receipt at all. What it refuses:

- A receipt stored inside this repository. The receipt holds private paths and the operator's own
  verification acts, so it stays in the private environment. The committed template is refused on
  this rule, which is the rule working.
- An unfilled placeholder, a missing section, a missing field and an empty one. An absent answer is
  never read as a negative answer. The template leaves `review_state` and `declared_status`
  unfilled too, because both are the operator's own declaration.

What it reports as a finding, at exit 1:

- A receipt bound to another candidate or another profile than the pair named on the command line.
  The profile is pinned by the bytes in this tree.
- A setting recorded as transmitted that the transport does not send, and the reverse.
  `harness/execution_receipt.py` holds that table, derived from `runner/claude_transport.py`: the
  pinned temperature and the judge's token limit reach no provider on this transport.
- A claimed operating-system sandbox. There is none (§5).
- A freeze condition or a freeze record cited as the isolation evidence. The freeze reads what a
  report declares about its invocation; verifying the invocation is this receipt's own act, and the
  two are separate records.
- A rendered argv without the empty tool list or without `--strict-mcp-config`.
- A checkpoint path that already exists, or one outside the private clone.
- A preflight whose bytes, candidate, profile, pack set, import manifest or grounding scope are not
  the ones the receipt records. The validator reads that report rather than trusting the copy.
- A preflight that realised no pack or no criterion input. Identifiers that line up are not
  completeness. An `insufficient_context` pack is not among these: the pack set records it as an
  explicit outcome.

The receipt is readiness evidence, not authorisation. §10 governs what may leave the environment,
and this runbook states none of those rules.

## 2. Deferrals and validation cases carried from the approval

### 2.1 Original-dependent questions (approval record, deferred table)

Each row is answered only by reading the original. Until then its current review disposition
stands, and nothing in this repository changes it.

| Rows | Required private evidence | Disposition until answered |
|---|---|---|
| ESR-E-02, ESR-E-04, ESR-E-08 | Original security, hospital/operator diversity and entrepreneurship mechanisms; compare with the sanitised text. | Preservation unconfirmed. E-04's cohort-size citation is withdrawn; miss versus not-assessable is not settled from this copy. |
| ESR-E-05 | Original registry/database and contributing-clinician passages. | Not assessable, pending evidence. |
| ESR-E-S03, ESR-E-S05 | Original repository/preprint commitments, supervisor mapping, track-record evidence. | Blind criticisms are not adopted as established weaknesses. |
| ESR-I-S01 | Original secondment rows, host-sector classifications, the denominator of the 80% claim. | Recompute privately before any correction; identify the actual source subsection. |
| ESR-I-S04 | Original target-group/indicator tables, figures, prose. | Do not attribute the disagreement to sanitisation as a confirmed cause. |
| ESR-Q-01 | Original dependencies, Gantt, sequencing evidence. | Partial classification stays qualified; zero embedded images does not prove every figure was lost. |
| ESR-Q-S02, ESR-Q-S03 | Original capacity and hosting evidence. | Identity references corrected (V02); adequacy unresolved. |
| M7.3 and the appointments (ESR-Q-03, A01) | Actual project duration, WP scope, funding/activity windows, follow-up intent. | No date or participation change is approved (D09, D12). |

Every open row is registered, with its owner and the evidence that would close it, in
`docs/tier4_orchestration_state/msca_dn/deferrals/open_deferral_register_2026-10-12.json`. Read the
register, not this table alone: it is the artifact a check can refuse.

### 2.2 Register adoption and provenance (D13, D14)

- The R04 declaration drafts are not adopted. Adoption rewrites the register bytes and every
  binding on them; the drafts' adoption block lists each. If adoption is decided privately, follow
  the seven steps in `docs/tier4_orchestration_state/msca_dn/declarations/review_checklist.md`
  and record the new hash in a successor provenance record.
- The body-point-size qualification for the `resolved_fixes` revision is prepared in
  `docs/tier4_orchestration_state/msca_dn/declarations/draft_resolved_fixes.json` and not applied,
  for the same reason.

### 2.3 Assessor validation cases (D04, D05)

Both are recorded on
`docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json` under
`assessor_validation_cases`, and are checked against the stage-A assessor's own output:

- **AVC-01** — one implementation sample stated that no intermediate milestones are shown, while
  the input it received carried the full milestones table. Check whether the stage-A assessor
  repeats the claim against the original. Never edit a milestone to satisfy it.
- **AVC-02** — four of five implementation samples credited the deliverables table with the
  milestones table's verification column. Check whether the stage-A assessor conflates the two
  tables against the original.

### 2.4 The audit's retired rule (D10, D11)

The integrity audit no longer reports a milestone that names no deliverable; it inventories it
as drafting advice. DC participation is compared by containment in one direction only. Both are
assumptions the audit documents, and neither is restored as a defect finding privately.

## 3. Profile authority

Two Doctoral Networks profiles exist on this build.

| Profile | Written for | Used by |
|---|---|---|
| `harness/profiles/msca_dn_2025_historical.json` | the 2025 call the proposal was submitted to | stage A |
| `harness/profiles/msca_dn_2026_default.json` | the 2026 call | stage B, if the resubmission goes to that call |

Stage A loads the historical profile. Nothing in it is improvised. V10 authored it from the
equivalence matrix V09 built, and every element either names the matrix rows that establish its
2025 rule, or declares the row the matrix left open.

The 2025 authority documents are in this repository and pinned by sha256 in
`docs/tier4_orchestration_state/msca_dn/authority/authority_source_index_2026-10-13.json`. The
matrix over them is
`docs/tier4_orchestration_state/msca_dn/authority/equivalence_matrix_2025_2026-10-13.json`, and the
profile pins both by hash. A new 2025 rule enters through the matrix and then the profile. It never
enters through this runbook.

Check both before the profile is loaded. The first replays the profile from the matrix and compares
bytes. The second reads the written profile against the matrix and reports where its sourcing claim
fails:

```
py -3.10 -m tools.author_msca_dn_historical_profile --check
```

```
py -3.10 -m harness.commands.historical_profile --check
```

Measured on 2026-10-13: `up to date`, then `profile check: green` over 13 sourced elements, 2
declared limitations and 27 matrix rows. The rendered reading is
`harness/profiles/msca_dn_2025_historical.md`.

Two elements carry a declared limitation, each naming its open row. The submission's binding to a
call identifier is declared and not evidenced (`CI-01`). Which version of the evaluation form the
2025 evaluators were given is not established (`EI-02`). No element is Confirmed, because no matrix
row is: no document carries a hash published by its issuing body.

The 2026 profile's own applicability to the resubmission's call is a separate question, and it is
open. Stage B settles it before it loads that profile.

## 4. Controlled import of the original (stage A, step 1)

The importer selects a document configuration (V07). `tools/import_external_proposal.py` declares
two, `SANITISED_DERIVATIVE` and `OFFICIAL_ORIGINAL`, and `--document` chooses one. A configuration
is selected, never merged: the original inherits no page map, no page count and no body point size
from the sanitised copy. A missing required field refuses the import and names the field.

Ask the tool what the original still needs. It writes nothing:

```
py -3.10 -m tools.import_external_proposal --document official_original --describe
```

On this build it answers `importable: false` and names five undeclared required fields:
`workspace_rel`, `sub_sections`, `expected_pages`, `body_point_size` and `revisions`. It answers
`measurable: true` for the same configuration, because a dry import needs the identity fields
alone. Its declared status is `Assumed`: every value in it is an operator declaration about a
document this repository does not hold.

### Step 1a — measure the original before importing it

`plans/msca_dn_v08_original_dry_import_procedure.md` is the procedure, and it is the operator's.
Five steps in outline:

1. Hash the PDF at the authoritative source.
2. Check the extraction environment against the V01 pin.
3. Run the dry import, outside this repository.
4. Reconcile the worksheet page by page against the PDF.
5. Fill in the fidelity acceptance record, then validate it.

```
py -3.10 -m tools.import_external_proposal --environment
```

```
py -3.10 -m tools.dry_import_original --pdf <private>/part_b_as_submitted.pdf --expect-sha256 <hash from the authoritative source> --out <private>/v08_dry_import --submission-id <the proposal number> --call-id <the 2025 call id>
```

```
py -3.10 -m tools.dry_import_original --check-acceptance <private>/v08_dry_import/extraction_fidelity_acceptance.json
```

The dry import refuses a hash the bytes do not match, and refuses any path inside this repository
for the submitted text. It writes no graph state, so nothing it produces can be read as an imported
document. The page map it establishes is what the import then needs declared.

### Step 1b — configure the original, privately (V17)

The five fields `--describe` names are facts about a document this repository does not hold, so they
are declared in a file the operator authors in the private network. Nothing about them is declared
here. Copy `tools/original_configuration_template.json` to the private root and answer every
angle-bracketed value: the page map, the page count, the body point size, the work-package layout,
the graph root, and where the V08 records sit.

Three rules the form enforces rather than states:

- Every path in it is relative to the private root, and that root may not be inside this
  repository. The committed template is refused on both counts.
- A placeholder is not a declaration. An unanswered field refuses and names itself.
- Null is an answer and silence is not. A document with no work-package table says so, and one
  whose network type nothing here checks says that too.

Then declare each sub-section's own number, section, page range and opening marker. A page no
sub-section covers has to be listed under `pages_outside_the_map` with a basis: a cover page is a
legitimate answer and silence is not.

The configuration is checked against the dry import's own inventory before anything is written.
`runner/original_configuration.py` compares the page count, the body point size, every numbered
marker and the coverage of the map against that measurement. What it cannot reach it reports as
unchecked rather than as agreeing. It refuses a configuration whose inventory measured other bytes.
It refuses one naming a PDF the operator did not authenticate.

Author the private graph root with it. The tool writes the same skeleton the public one writes —
README, intake record, the dev-graph directories the importer needs — and refuses a root inside this
repository:

```
py -3.10 -m tools.author_original_workspace --root <private root> --config-input <configuration input relative to that root>
```

The intake record is not re-declared. The dry import already authored one against the schema, and
this records that file into the graph root, so the submission id is declared once.

The original is not a revision of the sanitised copy. Its intake id differs
(`msca-dn-2025-original`), and a revision of one document may not supersede a revision of another.
A comparison between the two documents is a record of its own.

### Step 1c — what the import records, and what to read

The import reads the same configuration input, completes the document from it, and writes under the
private root:

```
py -3.10 -m tools.import_external_proposal --document official_original --config-input <configuration input> --repo-root <private root>
```

A configuration that disagrees with the measurement is reported and nothing is written. The import
also refuses to redeclare a document that is already complete, so the committed sanitised page map
stays the one its hash-bound manifests were measured under.

The importer records what it measures. Each line is a check the operator reads before going on:

| Measured | Where it lands | Check |
|---|---|---|
| input sha256 | `provenance.current_assessment_artifact.sha256` | equals the authenticated hash recorded at intake |
| page count | `provenance.current_assessment_artifact.pages` | equals the declared `expected_pages` |
| headings and section boundaries | `derived.sub_sections[*]` | every declared sub-section anchored; page-map discrepancies listed |
| tables | `derived.tables`, `derived.table_3_1a` | the work-package header layout the audit parser reads |
| extraction accounting | `derived.per_page_extraction_losses` | zero pages with loss, or each loss explained |
| import manifest | the workspace's `dev_graph/imports/<manifest name>` | written once; its path is the one every later command names |
| fidelity register | the declared register path | written by the submitted document's own renderer (V18), not the copy's; its declared half comes from the revision's declaration input, one file per revision |
| document node and version | the dev-graph import | one current version; its node id is the candidate id |
| materialised candidate | the audit's `candidates/<node id>/` directory | the content hash the preflight binds |

Then, against the original and only there, the operator records the per-sub-section
`fidelity_to_submitted_original` declarations the R04 drafts left Unresolved. V01 requires those
declarations before any miss can claim Confirmed preservation.

The original's own register asks a different question, and its renderer is a different one (V18).
The copy's header declares a sanitisation, a transformation and a reflow, which are the copy's
facts, so `tools/author_msca_dn_workspace.py` refuses the submitted text. The submitted document's
register declares that nothing stands between the submission and the text assessed, and says in so
many words that this is not a claim the extraction preserved everything.

What the extraction loses is the V08 reconciliation, and the register will not be written over an
open one. An item still `unreconciled`, or a `preserved` verdict resting on a measurement equally
true of a document whose figures are gone, refuses the write and names the class. Its declared half
asks for a `presence` and an `extraction_fidelity` per sub-section, under a record type of its own:
a transformation declared about the submitted text would read as a sanitisation of it.

## 5. Fresh preflight and isolated blind assessment (stage A, steps 2–3)

### The preflight

Name the import manifest explicitly. The resolver's predecessor-manifest default is never relied on
(R05 item 9).

```
py -3.10 -m harness.commands.blind_assessment preflight --document <original document id> --graph-root <private graph root> --profile harness/profiles/msca_dn_2025_historical.json --transport claude-cli --no-claims --grounding-scope content_focused --import-manifest <private manifest path> --out-dir <private reports dir>
```

This lane declares `--grounding-scope content_focused`. `--no-claims` withholds the claim ledger, so
grounding is unassessable, and all three records say so. A `source_grounded` declaration is refused
until ticket X01 lands (§9).

Read the preflight report before going on: the pack-set hash, the sections it realised, the manifest
pin and the declared grounding scope.

### The assessment

```
py -3.10 -m harness.commands.blind_assessment assess --document <original document id> --graph-root <private graph root> --profile harness/profiles/msca_dn_2025_historical.json --transport claude-cli --no-claims --grounding-scope content_focused --import-manifest <private manifest path> --preflight <preflight report> --intake msca-dn-2025-original --assessor-model <pin> --assessor-version <tag naming claude-cli> --out-dir <private reports dir>
```

The run re-derives the pack set under these flags and refuses before any assessor call if it does
not match the preflight's hash.

Checkpointing is on by default. Every raw response is written as it arrives to
`.harness/checkpoints/checkpoint_<hash12>_<NNNN>.jsonl` under `--repo-root`, never under
`--out-dir`. Record the exact path the run prints: a resume needs it.

- `--checkpoint <path>` names the file instead. An existing file is never appended to.
- `--no-checkpoint` writes none. A failed run is then redrawn in full, at the cost of the quota.
- `--resume <path>` replays every call the file covers and goes live from the first it does not.
  The report declares `replayed_calls` beside `live_calls`, so a partly replayed report says so.
  The checkpoint's binding — candidate, profile, assessor pin, preflight pack set, sample counts —
  must equal the resuming run's.

A malformed response stays in the checkpoint verbatim, with its hash and the parser's own message,
marked discarded. Nothing repairs it, and it is never replayed. A malformed criterion draw is asked
again over the identical prompt, at most twice, and every discarded draw is recorded on the score.

Recovery is not permission to replace an inconvenient valid sample. A parseable sample stands,
whatever it says. Only the parsers discard a response, and a sample the operator dislikes is
evidence rather than an accident.

If a run spent its quota before a checkpoint existed, rebuild one from the CLI's own session
transcripts and then resume. Every flag below must be the one the lost run used, because the sample
counts bind the checkpoint as much as the candidate does. Add `--skip-criterion-scores` if that run
set it:

```
py -3.10 -m harness.commands.blind_assessment salvage --document <original document id> --graph-root <private graph root> --profile harness/profiles/msca_dn_2025_historical.json --transport claude-cli --no-claims --grounding-scope content_focused --preflight <preflight report> --transcripts <private transcripts directory> --checkpoint <new checkpoint path> --n <the lost run's --n> --criterion-n <the lost run's --criterion-n> --assessor-model <pin> --assessor-version <tag naming claude-cli> --out-dir <private reports dir>
```

Record the salvage in the private handoff: which transcripts, which checkpoint file, and what it
recovered. A salvaged run is a replay of what the assessor said, not a fresh draw.

### What the recorded pins are, and are not

- `--assessor-model` and `--assessor-version` are **declared identifiers**. The report records
  `model@version` and nothing else about the assessor. Neither string is an attestation from the
  provider that this model answered.
- The pinned temperature is 0. `JudgeConfig` declares it and refuses any other value, but the
  `claude` CLI takes no temperature argument, so the value is not transmitted. Robustness comes from
  majority voting over N samples instead.
- `--assessor-version` must contain `claude-cli`, or the builder refuses. That rule stops a report
  carrying this transport under another name. It does not verify the transport.
- `JudgeConfig` refuses every drafter model, so the assessor can never be the model that drafted the
  text. Transport, vendor and model family are not independent on this path, and the pin is where
  the report says so.

### Isolation, and what it does not authorise

`--transport claude-cli` renders the assessor's tool list as `--tools "" --strict-mcp-config`
(`runner/claude_transport.py`). Three controls keep the assessor blind, and each has a test that
would fail if it broke:

- The explicit empty tool list, never `None`. `tools=None` omits the flag and leaves the CLI's
  built-in tools live. `--tools ""` alone still exposes the operator's MCP servers, measured
  2026-10-05. The argv is pinned at the level handed to the operating system:
  `tests/harness/test_subscription_judge.py::TestBlindnessAtTheArgvLevel`.
- A fresh working directory outside every repository clone. The subscription judge refuses one
  inside.
- The ESR sits outside the graph root, outside the package and outside every file the assessor can
  open. The intake's permitted purpose is `blind_pre_evaluation`. Leakage is tested in
  `tests/harness/test_blind_leakage.py`, and
  `tests/harness/test_blind_baseline.py::TestPlantedMarkers` writes a unique string into the
  historical evaluation and a Tier 5 draft, then shows it reaches no rendered prompt, no
  materialised candidate and no report. A non-vacuity check shows the candidate text does reach the
  prompts.

That planted-marker test is a transport and isolation test. It is not a step of the freeze, which
runs the conditions listed below and no marker check.

What these controls are not:

- **Not an operating-system sandbox.** The child process runs from a directory, with the operator's
  own privileges, filesystem rights and network access.
- **Not authorisation** to send private proposal content to a provider. An empty tool list stops the
  assessor reading this repository. It says nothing about what the private environment permits to
  leave it. §10 governs that, and §1 requires it settled first.

### The freeze

Freeze the report before the ESR is introduced:

```
py -3.10 -m harness.commands.blind_assessment freeze --report <blind report> --candidate <materialised candidate dir> --profile harness/profiles/msca_dn_2025_historical.json --baseline-dir <private baseline dir>
```

One freeze per directory. A second is refused, because a frozen baseline is never replaced.

The freeze loads the profile bundle and compares the report with what a complete report holds (V04).
It refuses a report whose cells are not the profile's grid, whose criterion scores are not the
profile's criteria, and whose total its own scores do not produce. A condition the report's transport
cannot answer is recorded not applicable rather than passed: `invocation_evidence` applies to
`claude-cli` and not to an API transport.

### The conditions the freeze checks

22 baseline conditions, in the order the freeze runs them:

```
record_type, binding_fields, evidence_source, evidence_bindings,
preflight_binding, preflight_rebound, assessor_transport, pin_names_transport,
invocation_evidence, scope, grounding_scope, cells_present, cell_identity,
cell_spreads, cell_members, criterion_scores_present, criterion_identity,
criterion_spreads, criterion_arithmetic, criterion_samples, criterion_total,
total_recomputed
```

`harness/blind_baseline.py` holds that list as `BASELINE_CHECKS`. The freeze record's
`checks_passed` is derived from the conditions that ran, so it cannot claim one the freeze did not
make. `tests/test_msca_dn_pe09_runbook.py` fails if this block and that tuple disagree.

## 6. ESR comparison after the freeze (stage A, step 4)

Only now does the ESR enter. In order:

```
py -3.10 -m harness.commands.blind_assessment audit --document <original document id> --graph-root <private graph root> --profile harness/profiles/msca_dn_2025_historical.json --candidate-provenance <private manifest path> --baseline-dir <private baseline dir> --out-dir <private audit dir>
```

The audit names the import manifest explicitly, for the same reason the preflight does. Without one
the report states that the grounding cause is Unresolved and borrows no other document's reason.

```
py -3.10 -m harness.commands.blind_assessment compare --baseline-dir <private baseline dir> --esr docs/tier4_orchestration_state/msca_dn/esr/msca-dn-2025-esr.json --dispositions <private dispositions, schema 1.2> --candidate <materialised candidate dir> --register <private register> --audit <private audit report> --profile harness/profiles/msca_dn_2025_historical.json --out-dir <private comparisons dir>
```

The dispositions are written privately, one row per ESR observation, under schema `1.2`. Register
pointers resolve by identity, and every miss declares its failure mode. A Confirmed preservation
claim rests on the register's `fidelity_to_submitted_original` declaration for the quoted
sub-section (V01). The approved public file
`docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1_approved.json` is the
template, and its deferred rows are the questions §2.1 answers.

```
py -3.10 -m harness.commands.blind_assessment review --comparison <private comparison> --notes <private review notes> --profile harness/profiles/msca_dn_2025_historical.json --out-dir <private reviews dir>
```

The review reads every other input from the comparison, re-resolves each reference and recomputes
the counts. The notes are declarations, and a disposition stays the operator's decision.

### The two readings are compared row by row, and the reading is labelled

`diff` compares a comparison with its successor over the same baseline, ESR record and candidate.
The public comparison
`docs/tier4_orchestration_state/msca_dn/comparisons/comparison_f60ae6e0a2a1_0003.json` is over the
sanitised copy's baseline. Pairing it with the original's comparison is refused by design, so it is
not a step here and no command line above names it.

**[future]** No tool compares two comparisons over different baselines. Until one exists, read the
two by observation id, by hand, and label the reading for what it is: two assessments, of two
documents, under two baselines and two profiles. A row that moved may have moved because the
document differs, because the rules differ, or because the assessor differs. The reading says which
it cannot distinguish.

`diff` does apply inside the private environment, between two comparisons over the same private
baseline. That pair exists as soon as the operator revises the dispositions and runs `compare` again,
which is what the public lineage did three times over one baseline
(`docs/tier4_orchestration_state/msca_dn/comparisons/comparison_f60ae6e0a2a1_0001.json` to `0003`):

```
py -3.10 -m harness.commands.blind_assessment diff --before <private comparison> --after <private successor comparison> --out-dir <private comparisons dir>
```

### What to investigate, in this order

Record each as a Tier 4 note in the private environment:

1. Missed findings: the seven preservation-qualified misses, each re-read against the original's
   declaration. A miss stays a miss only where the original carries the evidence.
2. False positives: AVC-01 and AVC-02 against the stage-A assessor's own samples.
3. Contested strengths: the eight rows where a blind shortcoming sits on a praised point. §2.1 says
   which need the original.
4. Score differences: the historical 85.80 against the stage-A blind total, per criterion. No
   deduction is attributed to any individual criticism. The sanitised copy's frozen 74.60 is not a
   comparator for the original, and it stays untouched.

## 7. Human-approved revisions (stage A → B)

Revisions are implemented in the authoritative proposal, privately, by the humans the revision
plans name. Every plan in
`docs/tier4_orchestration_state/msca_dn/comparisons/revisions_f60ae6e0a2a1_0003.json` lists what has
to be confirmed first. A numerical target, a study design, data access or a partner commitment is
written only after its named human confirms it. The two beyond-ESR items (ESR-I-S02's sustainability
improvement, ESR-I-02's societal subtask) stay labelled as beyond the ESR.

Record each change with its source in the private environment. No private material, no original
passage and no partner identity is carried into this public workspace.

## 8. Final resubmission as a distinct candidate (stage B)

The resubmission is imported as its own document, with its own revision entry, manifest, register,
declaration input, preflight, assessment, audit and reports. None of stage A's artifacts is reused
as an input.

Stage B reuses the commands of §4 and §5, and the `audit` command of §6, with the stage-B document
id, manifest, profile and output directories. It reuses the profile of the call being submitted to,
after that profile's applicability is settled (§3).

The rest of §6 is excluded. `compare`, `review` and `diff` do not apply, because the resubmission has
no evaluation summary report of its own. The 2025 ESR is not a stage-B input, and an observation
about the 2025 submission does not become a row about a different document. Stage A's comparison,
its review and its diff stay in stage A.

## 9. Grounding prerequisites

The sanitised audit marks all 45 ledger claims Unresolved with one declared reason, and every blind
cell reports grounding unassessable under `--no-claims`. Restoring the sources in the private
environment does not by itself validate the grounding axis. Three pieces are needed first, none of
which exists for an imported proposal:

- **[future]** a claim loader for the imported document's sections that yields a ledger with
  resolvable `source_ref` spans;
- **[future]** a ledger status other than `unresolved` that the import contract permits, with the
  evidence each status rests on;
- **[future]** the E2 grounding integration over that ledger, so a cell's grounding can read passed
  or failed and not only unassessable.

Until then stage A and stage B report grounding unassessable, and say so. `--grounding-scope
source_grounded` is refused until ticket X01 implements and validates that route.

## 10. What may leave the private environment

The approved environment's rules decide this, and this runbook does not state them. What the public
workspace can hold without them is the metadata already here: hashes, counts, dates, decision ids,
review statuses and the command lines above. A score, a finding text, a quoted passage or a register
declaration about the original leaves only if those rules say it may.

## 11. Implementation gaps needing separate tickets

| Gap | Blocks |
|---|---|
| Claim loader, ledger statuses and E2 integration for imported documents (§9) | the grounding axis in both stages |
| A labelled row-by-observation reading of two comparisons over different baselines (§6) | the stage-A reading against the public comparison |
| The D14 successor provenance update and the D13 adoption, if decided (§2.2) | nothing in the harness; the register bindings |

Four rows have closed. V10 authored the historical profile from V09's matrix (§3), V13 built the readiness receipt and its validator (§1.1), V17 built the original's configuration route (§4 step 1b) and V18 its register renderer (§4 step 1c). The original's own values stay the operator's: the route is here and the declarations are theirs.

## 12. Handoff statement

PE-09 is not executed in this repository. No original, no private passage and no new assessor call
exists here. The frozen baseline stays 74.60, the ESR record stays as transcribed, and the
comparisons on disk are over the sanitised copy only.
