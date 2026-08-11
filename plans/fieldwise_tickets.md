# Tickets: FIELDWISE re-instantiation

Replace the superseded Tier 3 project with FIELDWISE data lifted from the master draft, then run
Phases 1–8. Source plan: `plans/fieldwise_reinstantiation_plan.md`. On `fieldwise-run-01`, plan steps
B1 and B2 are already done: the branch exists and the draft lives in Tier 3 source materials.

Work the **frontier**: any ticket whose blockers are all done. Tickets 1 and 2 can start now, in
parallel.

The operator approved the §2.1 decision-log split on 2026-08-10. No §14.5 amendment question is
raised; the 29 engine rulings stay in Tier 4.

## 1. Complete the purge and the decision-log split

**What to build:** A committed clean skeleton on `fieldwise-run-01`. Run-scoped Tier 4 state and all
of Tier 5 are gone, and runtime memory is cleared. The decision log is split three ways per the
plan's §2.1: 18 auto-generated run files deleted, 5 project-scoped decisions archived to
`decision_log/archive/demo-run/`, 29 engine rulings untouched. The purge also writes two log
entries: the §13.11 correction for the draft's move out of Tier 2A, and the vault
quarantine/supersession record per plan §6.

**Blocked by:** None — can start immediately.

- [x] Tier 4 `phase_outputs/`, `checkpoints/`, `validation_reports/`, and `alpha_honest_block/` contain no run artifacts.
- [x] Tier 5 contains no files under its four subdirectories.
- [x] Tier 3 contains only `source_materials/` (plus any placeholder needed to keep directories tracked).
- [x] Runtime memory directories under `.claude/` (runs, benchmark, skill_diag, cache, logs, agent-memory) are cleared.
- [x] The `synthetic-spine*` entry sits in `archive/demo-run/`, and the docx exporter's stamp glob matches nothing.
- [x] The 29 engine-governing rulings remain in `decision_log/` unchanged.
- [x] The §13.11 correction and the vault supersession are logged in the decision log.
- [x] The purge is committed on `fieldwise-run-01`.

Three deviations, all recorded in the purge decision-log entry.

- `preseed/phase8/` and `reuse/phase8/` are deleted alongside the four named directories. They hold the
  superseded run's Part B sections, which would otherwise supersede a FIELDWISE draft at ticket 10.
- `graph_compile/` is deleted. Its `pre_promote_backup/` held a restorable copy of the purged Tier 3.
  The directory is gitignored, so this deletion appears in no diff and is not recoverable from git.
  The purged Tier 3 itself remains recoverable from commit `6d96a60`.
- `working_assumptions.example.json` is kept. It is a project-neutral template the operator manual tells
  you to copy, and it carries no superseded project data.

`.claude/runs/` refills with a `test-00000000-...` fixture directory whenever the test suite runs.
"Cleared" means no demo-run contexts remain, not that the directory stays absent.

## 2. Operator input pack

**What to build:** One fill-in form covering the 14 open items of plan §4, issued to the operator
and returned complete. It covers partner legal identities and participation modes, the identity-spine
confirmation, ethics, governance, KPIs, and the career development plan. It also covers
person-months, optional unit-cost lines, citations, the researcher CV, capacity descriptions,
screening and Green Charter statements, and the page-limit decision. For each decision item, the form offers a drafted candidate
the operator can accept or replace.

**Blocked by:** None — can start immediately.

- [x] The form lists all 14 items with severity and the gate each one blocks.
- [x] Items 3, 4, 5, 6, 8, 9, 13, and 14 each carry a drafted candidate answer.
- [ ] The operator has returned answers for every item, or explicitly deferred named items.

The form is `plans/fieldwise_operator_input_pack.md`. Fill it in place and return it. Ticket 6 copies
the completed pack to `docs/tier3_project_instantiation/source_materials/operator_input_pack/` as the
lift source.

Four corrections to plan §4 are recorded in the form itself.

- Item 8 blocks no gate. `phase_04_gate` checks task months and the critical path, not effort, and
  the unit-cost `gate_09` reads `project_duration_months`, not per-WP person-months.
- Item 5's `g06_p05` passes vacuously on an empty KPI list. The hard predicate is `g06_p04`, which
  needs all six Tier 2B expected impacts mapped. The draft covers only EI-01, EI-02 and EI-05.
- Item 14's premise is wrong. Sections 1–3 of the draft measure about 3,800 words, roughly five to
  six pages against a 10-page cap. The form asks for a page budget instead of a cut list.
- CC-13 requires the Career Development Plan as a deliverable, and the draft's D1.1–D5.5 list has
  none. Ticket 4 must seed D1.3 if the operator accepts item 6.

One engine gap surfaced by item 9. `derive_unit_cost_budget` never sets `include_family`, so a
"family allowance applies" answer cannot reach the derived artifact without a code change.

## 3. Seed call binding and project brief

**What to build:** The first Tier 3 seeding slice. `selected_call.json` is carried forward
unchanged, and `project_summary.json`, `concept_note.md`, and `strategic_positioning.md` are lifted
from the draft under the plan's §5 provenance envelope. This ticket also creates
`hand_lift_provenance.json` and the lift record in the decision log, which tickets 4 and 5 extend.
Narrative files carry YAML front matter and per-section source references; prose is lifted without
rewriting.

**Blocked by:** Complete the purge and the decision-log split.

- [ ] `selected_call.json` matches its pre-purge content and targets HORIZON-MSCA-2026-PF-01.
- [ ] The three project-brief files exist, use the §5 envelope, and cite draft paragraph ranges.
- [ ] Every record carries exactly one §12.2 status, and nothing not present in the draft is marked Confirmed.
- [ ] `hand_lift_provenance.json` and the lift decision-log entry exist and cover these files.
- [ ] `topic_mapping.json` and `compliance_profile.json` are not seeded (Phase 2 writes them).

## 4. Seed architecture inputs

**What to build:** The second seeding slice: `objectives.json`, `outcomes.json`, `impacts.json`,
`workpackage_seed.json`, `milestones_seed.json`, and `risks.json`, lifted from the draft under the
§5 envelope. Outcomes get an Inferred first pass separating outputs from outcomes. The WP seed
carries Inferred task months and dependency edges derived from the WP month ranges, with
person-months absent. Impact KPIs are Unresolved pending operator input.

**Blocked by:** Seed call binding and project brief.

- [ ] All six files exist with the §5 envelope and draft source references.
- [ ] Objectives O1–O6, milestones MS1–MS5, and the 13 risks are Confirmed against the draft.
- [ ] Derived content (outcome separation, task months, dependencies) is Inferred with the derivation stated in `note`.
- [ ] Person-months and KPIs appear as Unresolved records, not as invented values.
- [ ] `hand_lift_provenance.json` covers these files.

## 5. Seed consortium files

**What to build:** The third seeding slice: `roles.json` with the six role tokens, `partners.json`,
and `capabilities.json`. MATE, MVCRI, and AgroVIR get honest Unresolved records in the plan's
worked-example shape: draft-confirmed role, country, and function stated; legal name, PIC, contact,
and participation mode named as missing and tied to blocking items 1 and 2.

**Blocked by:** Seed call binding and project brief.

- [ ] `roles.json` defines FELLOW, HOST, SUPERVISOR, DATA_PARTNER, TRANSFER_PARTNER, VALIDATION_PARTNER.
- [ ] `partners.json` covers every role token referenced by the draft work plan.
- [ ] The three new participants are Unresolved with missing fields named, never guessed.
- [ ] `capabilities.json` is lifted from the draft's knowledge-transfer and capacity statements.
- [ ] `hand_lift_provenance.json` covers these files.

## 6. Fold operator answers into Tier 3

**What to build:** Tier 3 updated with the returned input pack. Partner identities and participation
modes resolve the Unresolved consortium records. `confirmation_checklist.json` is re-authored and
`working_assumptions.json` declares every residual Assumed fact. KPIs land in `impacts.json` and
person-months in `workpackage_seed.json`. Each decided item gets a decision-log record.

**Blocked by:** Operator input pack; Seed architecture inputs; Seed consortium files.

- [ ] No consortium record remains Unresolved for a reason the input pack answered.
- [ ] Every Assumed fact in Tier 3 has a matching declaration in `working_assumptions.json`.
- [ ] `confirmation_checklist.json` covers the identity spine and every operator decision.
- [ ] Items the operator deferred remain Unresolved and are listed for the authorisation packet.
- [ ] Each of the eight decision items has a decision-log record.

## 7. Authorisation packet

**What to build:** The single review document the operator authorises the run on. It lists every
Tier 3 record with its status and source reference, groups the residual Unresolved items by the gate
they will fail, and states which phases can pass as seeded. Authorisation is recorded in the
decision log.

**Blocked by:** Seed call binding and project brief; Seed architecture inputs; Seed consortium
files; Fold operator answers into Tier 3.

- [ ] The packet enumerates every seeded record with status and source reference.
- [ ] Every remaining Unresolved item is listed with the gate it blocks.
- [ ] Operator authorisation is recorded in the decision log before any phase runs.

## 8. Run Phases 1–2

**What to build:** Call analysis and concept refinement executed through the runner, with a stop at
each gate. Phase 1 confirms the surviving Tier 2B extraction against `selected_call.json`. Phase 2
writes `topic_mapping.json` and `compliance_profile.json` and aligns the concept with the call. An
honest gate failure is a valid terminal state for this ticket, provided its cause is diagnosed and
reported.

**Blocked by:** Authorisation packet.

- [ ] `phase_01_gate` and `phase_02_gate` results are written to Tier 4 with pass or diagnosed-fail status.
- [ ] `topic_mapping.json` and `compliance_profile.json` exist after a Phase 2 pass.
- [ ] Any gate failure names the missing or contradicting input, not a generic error.

## 9. Run Phases 3–7

**What to build:** WP design, Gantt and milestones, impact architecture, implementation
architecture, and the budget gate, executed in order with a stop at each gate. Phase 7 runs the
internal unit-cost derivation per §8.1, with the HU host coefficient, and every budget component
resolves to Confirmed or operator-declared Assumed before `gate_09` can pass.

**Blocked by:** Run Phases 1–2.

- [ ] Phase 3–6 outputs and gate results are written to Tier 4 in phase order.
- [ ] Every WP-assigned partner resolves in `partners.json` at `phase_03_gate`.
- [ ] The unit-cost budget derivation passes its byte-equal replay check.
- [ ] `gate_09` result is written, and any failure names the unresolved budget component.

## 10. Run Phase 8 and export

**What to build:** The drafted FIELDWISE proposal. All sections required by the MSCA-PF application
form are drafted, assembled, and reviewed, and the final export is produced. The export must carry
no synthetic-demo stamp, which ticket 1's archive move makes possible.

**Blocked by:** Run Phases 3–7.

- [ ] All required sections exist in `proposal_sections/` and the assembled draft exists.
- [ ] The review packet distinguishes Confirmed facts from Inferred content.
- [ ] `gate_12` result is written with pass or diagnosed-fail status.
- [ ] The exported Part B contains no `SYNTHETIC DEMO` stamp.

## 11. Apply the E4 golden-lane decision

**What to build:** The E4 regression lane made honest again. The old goldens pin superseded Tier 5
content and go red once FIELDWISE Tier 5 exists. Decide with the operator: re-freeze the baselines
against the new Tier 5, or mark the lane expected-red on this branch. Apply the decision and log it.

**Blocked by:** Run Phase 8 and export.

- [ ] The lane either passes against re-frozen baselines or is marked expected-red with a stated reason.
- [ ] The decision and its rationale are in the decision log.
- [ ] The full-suite baseline count for the branch is recorded.

## 12. Re-author the vault for FIELDWISE

**What to build:** The Obsidian vault rebuilt to describe FIELDWISE, after the run, per the plan's
recommended sequencing. The deterministic authoring tool is rewritten for FIELDWISE rather than the
vault being hand-edited. The claim verifier then passes against the new Tier 5 sections, clearing
the §12.3 contradiction logged in ticket 1.

**Blocked by:** Run Phase 8 and export.

- [ ] The authoring tool regenerates the project-specific folders deterministically for FIELDWISE.
- [ ] Project-neutral folders (meta, sources, terminology, dashboards, governance) are preserved.
- [ ] `graph_claim_verifier` passes against the committed FIELDWISE Tier 5 sections.
- [ ] The vault supersession record is closed out or updated in the decision log.
