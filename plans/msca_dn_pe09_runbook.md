# PE-09 private-network runbook (ticket R06)

Date: 2026-10-08  
Branch: `msca-dn-pre-eval`  
Status: **preparation only. PE-09 is not executed in this repository.** Every step below runs
inside the approved private environment, by its operator, under its rules.  
Authority: `plans/msca_dn_pre_evaluation_spec.md` (PE-09, "declared, not built"); the operator
approval of 2026-10-08,
`docs/tier4_orchestration_state/msca_dn/reviews/operator_approval_2026-10-08.md` (D15 permits
this preparation; D09, D10, D12, D13 and the deferred table bound it).

Two kinds of line appear below. A line in a code block with a `py -3.10 -m ...` prefix is a
command whose flags exist on this build; each was checked against `--help` on 2026-10-08. A line
marked **[future]** names work no tool does yet. Nothing here is a result.

## 0. What this runbook separates

| Stage | Candidate | Profile | What it establishes |
|---|---|---|---|
| A. Historical validation | the submitted original, imported privately | the historical profile (see §3) | whether a blind assessment of the original reproduces the ESR's findings and scores |
| B. Final resubmission | the revised proposal, imported as a new candidate | the resubmission profile | an advisory pre-evaluation of what will be submitted |

The two never share a candidate, a preflight, a baseline or a report. The ESR enters stage A only
after its baseline is frozen, and never enters stage B's assessor inputs at all.

## 1. Private-environment prerequisites

Before any command runs, the private environment must hold:

- The submitted original (Part B, the PDF as submitted) and its sha256, recorded by the operator.
- A private clone of this repository at the revision the decision log names
  (`docs/tier4_orchestration_state/decision_log/msca-dn-operator-approval_2026-10-08.json`).
- The environment's own rules on what may leave it (§10). This runbook invents none.
- The deferrals and validation cases in §2, each read before the stage it belongs to.

Nothing from the private environment is written back into this public workspace except what §10
permits.

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

### 2.2 Register adoption and provenance (D13, D14)

- The R04 declaration drafts are not adopted. Adoption rewrites the register bytes and every
  binding on them; the drafts' adoption block lists each. If adoption is decided privately, follow
  the seven steps in `docs/tier4_orchestration_state/msca_dn/declarations/review_checklist.md`
  and record the new hash in a successor provenance record.
- The body-point-size qualification for the `resolved_fixes` revision is prepared in
  `draft_resolved_fixes.json` and not applied, for the same reason.

### 2.3 Assessor validation cases (D04, D05)

Both are recorded on `dispositions_f60ae6e0a2a1_approved.json` under
`assessor_validation_cases` and are to be checked against the stage-A assessor's own output:

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

The only Doctoral Network profile on this build is `harness/profiles/msca_dn_2026_default.json`.
It was written for the 2026 call. The 2025 call text and work programme are not stored in this
repository (`plans/msca_dn_pre_evaluation_spec.md` §8), and the application form was measured
unchanged between V5.0 and V6.0 for this call.

Stage A therefore needs a declared **historical profile**. Prepare it as a copy of the 2026
profile with every difference from the 2025 rules listed, each with its source in the 2025
call documents the private environment holds. Where no source states a difference, the rule
stays as the 2026 profile has it and the profile says so. Do not improvise a 2025 rule.

**[future]** No tool derives a profile from call documents. The historical profile is authored
by hand and checked by `tests/harness/test_msca_dn_profile.py`-style tests once it exists.

Stage B uses the resubmission profile applicable to the call being submitted to. The two
profiles stay separate files with separate versions wherever their rules differ.

## 4. Controlled import of the original (stage A, step 1)

The import tooling exists and is deterministic, but it is configured for the two sanitised
revisions only. `tools/import_external_proposal.py` reads a fixed revision table, `REVISIONS`.
Each `Revision` names the PDF path, the expected page count, the import manifest name, the
fidelity register path and the predecessor revision. The tool takes only `--check` and
`--repo-root`.

**[future]** Configuration work before the original can be imported, as a separate ticket:

1. A private workspace root beside `workspaces/msca_dn/` (never inside the public one),
   authored by the same pattern as `tools/author_msca_dn_workspace.py`.
2. A `Revision` entry for the original: its PDF under the private source-materials directory,
   its measured page count, a new manifest name, a new register path, no predecessor
   (the original is not a revision of the sanitised copy; the comparison between them is a
   separate record).
3. The revision table must be selectable, so that the public tool keeps rendering the two
   sanitised revisions byte for byte.

Once configured, the importer records what it measures, and each item is a check the operator
reads before going on:

| Measured | Where it lands | Check |
|---|---|---|
| input sha256 | `provenance.current_assessment_artifact.sha256` | equals the sha256 recorded at intake |
| page count | `provenance.current_assessment_artifact.pages` | equals the expected count in the revision entry |
| headings and section boundaries | `derived.sub_sections[*]` (`declared_pages`, `derived_pages`, `heading`) | fifteen sub-sections anchored `1.1`–`3.2`, `4`–`8`; page-map discrepancies listed |
| tables | `derived.tables`, `derived.table_3_1a` | the work-package header layout the audit parser reads |
| extraction accounting | `derived.per_page_extraction_losses` | zero pages with loss, or each loss explained |
| import manifest | `<private graph root>/docs/tier4_orchestration_state/dev_graph/imports/<manifest name>` | written once; its path is the one every later command names |
| fidelity register | the new register path | the declared half comes from the operator's declaration input (R01), one file per revision |
| document node and version | the dev-graph import | one current version; its node id is the candidate id |
| materialised candidate | the audit's `candidates/<node id>/` directory | the content hash the preflight binds |

Then, against the original and only there, the operator records the per-sub-section
`fidelity_to_submitted_original` declarations the R04 drafts left Unresolved. Those are the
declarations V01 now requires before any miss can claim Confirmed preservation.

## 5. Fresh preflight and isolated blind assessment (stage A, steps 2–3)

The import manifest is named explicitly. The resolver's predecessor-manifest default is never
relied on (R05 item 9).

```
py -3.10 -m harness.commands.blind_assessment preflight --document <original document id> --graph-root <private graph root> --profile <historical profile> --transport claude-cli --no-claims --import-manifest <private manifest path> --out-dir <private reports dir>
```

Read the preflight report: the pack-set hash, the seven sections, the manifest pin. Then:

```
py -3.10 -m harness.commands.blind_assessment assess --document <original document id> --graph-root <private graph root> --profile <historical profile> --transport claude-cli --no-claims --import-manifest <private manifest path> --preflight <preflight report> --intake <intake id> --assessor-model <pin> --assessor-version <claude-cli version tag> --out-dir <private reports dir>
```

Isolation, enforced by the transport and verified before the run:

- `--transport claude-cli` renders the assessor's tool list as `--tools "" --strict-mcp-config`.
  `--tools ""` alone leaves the operator's MCP servers reachable (measured 2026-10-05).
- The assessor child runs from a working directory outside every repository clone; the
  subscription judge refuses one inside.
- `HARNESS_JUDGE_VERSION` names the transport, or the pin check refuses.
- The ESR is not in the graph root, not in the package, not in any file the assessor can open.
  The intake's permitted purpose is `blind_pre_evaluation`.
- `--no-claims`: the claim ledger is withheld, so every cell's grounding reads unassessable
  rather than passed (spec decision 14).

Record every call's response through the checkpoint (`--checkpoint`, `--resume`); a run that
spends quota before writing is salvaged, never redrawn, with `salvage`.

Freeze the report before the ESR is introduced:

```
py -3.10 -m harness.commands.blind_assessment freeze --report <blind report> --candidate <materialised candidate dir> --profile <historical profile> --baseline-dir <private baseline dir>
```

The freeze checks the fifteen baseline conditions, including the planted-marker test and the
preflight re-bind. One freeze per directory; a second is refused.

## 6. ESR comparison after the freeze (stage A, step 3)

Only now does the ESR enter. In order:

```
py -3.10 -m harness.commands.blind_assessment audit --document <original document id> --graph-root <private graph root> --profile <historical profile> --baseline-dir <private baseline dir> --out-dir <private audit dir>
```

```
py -3.10 -m harness.commands.blind_assessment compare --baseline-dir <private baseline dir> --esr docs/tier4_orchestration_state/msca_dn/esr/msca-dn-2025-esr.json --dispositions <private dispositions, schema 1.2> --candidate <materialised candidate dir> --register <private register> --audit <private audit report> --profile <historical profile> --out-dir <private comparisons dir>
```

The dispositions are written privately, one row per ESR observation, under schema `1.2`.
Register pointers resolve by identity and every miss declares its failure mode. A Confirmed
preservation claim rests on the register's `fidelity_to_submitted_original` declaration for the
quoted sub-section (V01). The public `dispositions_f60ae6e0a2a1_approved.json` is the template.
Its deferred rows are the questions §2.1 answers.

Then render and diff:

```
py -3.10 -m harness.commands.blind_assessment review --comparison <private comparison> --notes <private review notes> --profile <historical profile> --out-dir <private reviews dir>
```

```
py -3.10 -m harness.commands.blind_assessment diff --before docs/tier4_orchestration_state/msca_dn/comparisons/comparison_f60ae6e0a2a1_0003.json --after <private comparison> --out-dir <private comparisons dir>
```

The diff refuses a pair over different baselines. The public comparison is over the sanitised
copy's baseline, so this diff will be refused as written; it is listed so the refusal is expected
and not worked around. Compare the two readings row by row instead, by observation id.

Investigate, in this order, and record each as a Tier 4 note in the private environment:

1. Missed findings: the seven preservation-qualified misses, each re-read against the original's
   declaration; a miss stays a miss only where the original carries the evidence.
2. False positives: AVC-01 and AVC-02 against the stage-A assessor's own samples.
3. Contested strengths: the eight rows where a blind shortcoming sits on a praised point; §2.1
   says which need the original.
4. Score differences: the historical 85.80 against the stage-A blind total, per criterion. No
   deduction is attributed to any individual criticism. The sanitised copy's frozen 74.60 is
   not a comparator for the original and stays untouched.

## 7. Human-approved revisions (stage A → B)

Revisions are implemented in the authoritative proposal, privately, by the humans the revision
plans name. Every plan in `revisions_f60ae6e0a2a1_0003.json` lists what has to be confirmed
first; a numerical target, a study design, data access or a partner commitment is written only
after its named human confirms it. The two beyond-ESR items (ESR-I-S02's sustainability
improvement, ESR-I-02's societal subtask) stay labelled as beyond the ESR.

Record each change with its source in the private environment. No private material, no
original passage and no partner identity is carried into this public workspace.

## 8. Final resubmission as a distinct candidate (stage B)

The resubmission is imported as its own document, with its own revision entry, manifest,
register, declaration input, preflight, assessment, audit and reports, under the resubmission
profile. None of stage A's artifacts is reused as an input. The ESR is not an assessor input
here either.

Commands are those of §4–§6 with the stage-B document id, manifest, profile and output
directories. The `compare` step does not apply: there is no ESR for the resubmission.

## 9. Grounding prerequisites

The sanitised audit marks all 45 ledger claims Unresolved with one declared reason, and every
blind cell reports grounding unassessable under `--no-claims`. Restoring the sources in the
private environment does not by itself validate the grounding axis. Before that axis can be
claimed, three pieces are needed, none of which exists for an imported proposal:

- **[future]** a claim loader for the imported document's sections that yields a ledger with
  resolvable `source_ref` spans;
- **[future]** a ledger status other than `unresolved` that the import contract permits, with
  the evidence each status rests on;
- **[future]** the E2 grounding integration over that ledger, so a cell's grounding can read
  passed or failed and not only unassessable.

Until then stage A and stage B report grounding unassessable, and say so.

## 10. What may leave the private environment

The approved environment's rules decide this, and this runbook does not state them. What the
public workspace can hold without them is the metadata already here: hashes, counts, dates,
decision ids, review statuses and the command lines above. A score, a finding text, a quoted
passage or a register declaration about the original leaves only if those rules say it may.

## 11. Implementation gaps needing separate tickets

| Gap | Blocks |
|---|---|
| Selectable revision table and a private workspace root for the importer (§4) | stage A step 1 |
| A declared historical profile with sourced 2025 differences (§3) | stage A steps 2–6 |
| Claim loader, ledger statuses and E2 integration for imported documents (§9) | the grounding axis in both stages |
| A cross-baseline comparison of two readings by observation id (§6) | the stage-A diff against the public comparison |
| The D14 successor provenance update and the D13 adoption, if decided (§2.2) | nothing in the harness; the register bindings |

## 12. Handoff statement

PE-09 is not executed in this repository. No original, no private passage and no new
assessor call exists here. The frozen baseline stays 74.60, the ESR record stays as
transcribed, and the comparisons on disk are over the sanitised copy only.
