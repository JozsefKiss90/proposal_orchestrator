# FIELDWISE re-instantiation plan

Target call: HORIZON-MSCA-2026-PF-01. Source of truth: `FIELDWISE_MSCA_Master_Draft.docx` (Part B Draft v0).
Goal: a clean branch carrying fresh Tier 3 data lifted from the draft, then a full Phase 1–8 run.

---

## 1. What I found

I read the draft (436 paragraphs), the current Tier 3, the compiled manifest, all 14 gate conditions,
and the MSCA vault. Five findings drive the plan.

**The draft and the current Tier 3 describe two different projects.** The identity spine matches:
fellow Dr. Rositsa Cholakova, host ELTE Budapest, supervisor Dr. András Jung, 24-month European
Fellowship, Hungary. The research content does not match. Current Tier 3 carries PlanetScope, Sentinel-1
SAR, ERA5, Route A/B latent-field-state fusion, ten decision questions and five objectives about
probabilistic diagnosis. The draft carries a five-year MATE hyperspectral archive, hyperspectral-to-
Sentinel-2 transfer, MVCRI Bulgaria cross-country transfer, AgroVIR farmer-field transfer, the DrR web
MVP, six objectives, seven research questions and Field Decision Value. Tier 3 must be replaced, not
edited.

**The draft sits in the wrong tier.** `docs/tier2a_instrument_schemas/part_b_draft_v0/` is instrument-
schema space. A project draft placed there violates §13.11. Its canonical home is
`docs/tier3_project_instantiation/source_materials/`.

**The call-level layers survive the purge.** Tier 1, Tier 2A and Tier 2B are call-specific and
project-agnostic. All six Tier 2B extracted files are populated for this call, `unit_cost_rates.json`
is present, and the MSCA-PF application and evaluation forms resolve. `gate_01_source_integrity` and
most of `phase_01_gate` therefore pass without new input from the draft.

**Two new participants have no Tier 3 identity.** The work plan assigns MATE and MVCRI as work-package
leads. `phase_03_gate` requires every assigned partner to exist in `partners.json`. Neither exists today.

**The vault is off the runner's critical path.** The manifest binds `canonical_pack_deriver` to
`runner/phase8_canonical_pack.py`, which reads Tier 3 docs. The graph-sourced variant
(`runner/graph_canonical_pack.py`) is not bound to any node. Section 5 answers the vault question.

---

## 2. Branch and purge

Do not purge on `eval_mock`. The E5f rubric grading run is in progress there.

| Step | Action |
|------|--------|
| B1 | Branch `fieldwise-run-01` from `eval_mock`, which carries the graph substrate, the runtime and the harness. |
| B2 | Move the draft to `docs/tier3_project_instantiation/source_materials/part_b_draft_v0/` and delete the Tier 2A copy. |
| B3 | Delete run-scoped Tier 4 state: `phase_outputs/**`, `checkpoints/**`, `validation_reports/**`, `alpha_honest_block/**`. |
| B4 | Delete all of Tier 5: `proposal_sections/`, `assembled_drafts/`, `final_exports/`, `review_packets/`. |
| B5 | Delete all of `docs/tier3_project_instantiation/**` except the new `source_materials/`. |
| B6 | Clear runtime memory under §9.2: `.claude/runs/`, `.claude/benchmark/`, `.claude/skill_diag/`, `.claude/cache/`, `.claude/logs/`, `.claude/agent-memory/`. |
| B7 | Split `docs/tier4_orchestration_state/decision_log/` three ways. See §2.1. |

### 2.1 The decision log split

The decision log is not one thing. Its 52 files fall into three groups with three different dispositions.
A blanket archive would remove rulings the next run depends on. A blanket delete would remove more.

| Group | Files | What it is | Disposition |
|-------|-------|------------|-------------|
| Auto-generated run state | 18: `decision-log-update_*`, `topic-scope-check_*`, `gate_failure_*` | Written by the runner during the demo run. References artifacts that B3–B5 delete. Regenerable | **Delete** |
| Project-scoped human decisions | 5: `13b-real-data-consolidation`, `action-confirmation-msca-pf`, `tier3-hand-lift-msca-pf`, `synthetic-spine-demo-override`, `synthetic-concept-override-extension` | Records about the superseded project. FIELDWISE replaces all five | **Archive** to `decision_log/archive/demo-run/` |
| Engine-governing rulings | 29: DOD-1×4, CHK-1, ST-1, `transport-stream-json-reassembly`, `runtime-truncation-fix`, `section-type-taxonomy-drift-correction`, `gate-result-schema-id-fix-and-backfill`, `ms2-ticket9-agnosticism-proof`, the E2–E5 and LG-1 harness frameworks, and the rest | Governs the engine regardless of which call is written. Not demo output | **Keep in place** |

One archive move is load-bearing rather than tidy. `runner/docx_exporter.py:83` globs
`decision_log/synthetic-spine*.json`, and when the file matches, the exported Part B carries a visible
`SYNTHETIC DEMO — NOT FOR SUBMISSION` stamp. The glob is non-recursive, so moving the file into
`archive/demo-run/` clears the stamp from the FIELDWISE export while preserving the record. Leaving it
in place would mark a real submission as a demo.

### 2.2 What the purge cannot touch

The constitutional amendment history is not in the decision log. It sits in `CLAUDE.md` as six
`Constitutional Amendment Record` tables: §8/§7 (C1) at line 253, §16.5 (C3) at 429, §17 at 554, the
transport migration at 564, the pending backend migration at 574, and §17.5.3 (C2) at 585. C1, C2 and C3
live there and no Tier 4 operation reaches them. Decision-log entries only cite them.

### 2.3 Why the 29 stay

Two modules cite decision-log entries directly. `runner/graph_determinism_check.py:95` cites `dod-1c` for
retaining `compiled_at`. `runner/checkpoint_publisher.py:9` cites `chk-1` for the provenance quad. The
code records what was done. The entry records why, and what was rejected.

`dod-1d` is the clearest case, because §6 of this plan relies on it. It rules that the graph becomes
authoritative only through a fail-closed human promote, never a silent compiler overwrite. Neither
`CLAUDE.md` nor the manifest states this. Without the entry, `--from-graph` and
`tools/promote_graph_staging.py` read as an unfinished feature rather than a deliberate constraint.

### 2.4 A tension worth naming

The 29 are project-agnostic in rule. They are project-scoped only in evidence. Entry `dod-1e` proves
checkpoint publication by driving run `msca-pf-graph-01`, yet the rule binds any run. Entry
`ms2-ticket9-agnosticism-proof` records the proof that the graph layer carries no project nouns.

They therefore sit in the wrong tier. §5 defines Tier 4 as run-scoped orchestration state, and an engine
ruling is not that. But §9.4 mandates this location: durable decisions must go to the decision log or a
phase output. Moving engine rulings to a separate register outside Tier 4 would resolve the category
error and would require a §14.5 amendment, which only you can make. This plan does not assume that
amendment. It leaves the 29 in place and flags the question.

Two consequences to accept before starting. The E4 golden-set regression lane pins the current Tier 5
content and will go red once Tier 5 is regenerated. Re-freeze those baselines after the run, or mark the
lane expected-red on this branch. Separately, `runner/graph_claim_verifier.py` audits Tier 5 claims
against the vault and will fail while the vault still describes the old project.

---

## 3. What the draft yields, file by file

Every Tier 3 file the runner reads, and where its content comes from.

| Tier 3 file | Draft source | Completeness |
|-------------|--------------|--------------|
| `call_binding/selected_call.json` | No draft input needed. Carry forward unchanged. Draft confirms 24 months and HU host. | Complete |
| `call_binding/confirmation_checklist.json` | Re-author. Spine survives, participants and decisions change. | Needs your input (§4) |
| `call_binding/topic_mapping.json` | Phase 2 writes this. Do not seed. | n/a |
| `call_binding/compliance_profile.json` | Phase 2 writes this. Do not seed. | n/a |
| `project_brief/project_summary.json` | Cover block, "The project in one sentence", "Core message". Acronym is FIELDWISE. | Complete |
| `project_brief/concept_note.md` | §1.1.1 to §1.1.7: challenge, accuracy critique, DrR prior work, gaps G1–G6, central question, RQ1–RQ7, H1–H6. | Complete |
| `project_brief/strategic_positioning.md` | §1.1.9 six transitions and validation ladder, §2.3 European impact, the two prior-evaluation responses. | Complete |
| `consortium/roles.json` | §1.3 and §3.2. Six role tokens: FELLOW, HOST, SUPERVISOR, DATA_PARTNER (MATE), TRANSFER_PARTNER (MVCRI), VALIDATION_PARTNER (AgroVIR). | Needs your input (§4) |
| `consortium/partners.json` | Derived from `roles.json`. Adds legal identity fields. | Needs your input (§4) |
| `consortium/capabilities.json` | §1.3 knowledge-transfer lists and §3.2 capacity statements. Optional input to Phase 6, recommended. | Complete |
| `architecture_inputs/objectives.json` | §1.1.8 table: O1–O6 with purpose and verification. | Complete |
| `architecture_inputs/outcomes.json` | Deliverables D1.1–D5.5 and the six transitions of §1.1.9. | Partial |
| `architecture_inputs/impacts.json` | §2.3 scientific, environmental, agricultural, technological and European impact. | Needs KPIs (§4) |
| `architecture_inputs/workpackage_seed.json` | §3.1: WP1–WP5 with month ranges, leads, tasks T1.1–T5.7, deliverables D1.1–D5.5. | Partial |
| `architecture_inputs/milestones_seed.json` | MS1 M6, MS2 M12, MS3 M16, MS4 M20, MS5 M23. | Complete |
| `architecture_inputs/risks.json` | §3.1 risk table: 13 risks with likelihood, impact and mitigation. | Complete |
| `working_assumptions.json` | Not from the draft. You declare each residual Assumed fact. | Needs your input (§4) |
| `hand_lift_provenance.json` | Written during the lift. Records draft paragraph ranges per claim. | Produced in §5 |
| `integration/` | Unused. MSCA-PF is a unit-cost instrument, so §8.1 derives the budget internally. | n/a |

Two entries need explanation.

`outcomes.json` is partial because the draft names deliverables but never separates a project output from
the outcome it produces. Phase 5 needs that separation to map outputs onto the call's expected outcomes.
I can derive a first pass from the deliverable list, marked Inferred.

`workpackage_seed.json` is partial because the draft gives month ranges per work package but no task-level
months, no person-months and no explicit inter-WP dependency edges. Phase 3 and Phase 4 can derive
schedule and dependencies from the WP ranges, and I will mark them Inferred. Person-months have no source.

---

## 4. What blocks the run

Fourteen items. Severity says what happens if the item stays open.

| # | Item | Severity | Why |
|---|------|----------|-----|
| 1 | Legal identity of MATE, MVCRI and AgroVIR: full legal name, city, country, PIC, entity type, contact person | **Blocks Phase 3** | `phase_03_gate` requires every WP-assigned partner in `partners.json` |
| 2 | Participation mode of MATE, MVCRI and AgroVIR: associated partner, secondment host, or informal collaborator | **Blocks Phase 3** | Determines role tokens, eligibility statements and whether a secondment appears in the work plan |
| 3 | Ethics self-assessment: personal data under GDPR, farmer commercial data, any human or animal subjects, dual use | **Blocks Phase 6** | `phase_06_gate` requires ethics to be explicitly present, never omitted. The draft contains nothing on ethics |
| 4 | Governance and supervision arrangements: supervision frequency, decision rights, conflict resolution | **Blocks Phase 6** | `phase_06_gate` requires a defined governance matrix |
| 5 | KPI set per impact claim, traceable to WP deliverables | **Blocks Phase 5** | `phase_05_gate` requires it. The draft explicitly declines advance numeric targets |
| 6 | Career development plan | **Blocks Phase 6** | Instrument-mandated for MSCA-PF. Feeds Impact 2.1 |
| 7 | Confirmation that the fellow, host and supervisor identities are unchanged | **Blocks authorisation** | Current Tier 3 asserts them as Confirmed. The draft never names them |
| 8 | Person-months per work package | High | No source anywhere. Needed for a credible work plan and for effort consistency at Phase 7 |
| 9 | Optional unit-cost lines: family allowance, special-needs allowance, long-term leave | High | `gate_09` requires every budget component Confirmed or operator-declared Assumed |
| 10 | State-of-the-art references and citations | High | The draft has a full SOTA narrative and zero citations. Excellence 1.1 is weak without them |
| 11 | Researcher CV: publication list, ORCID, PhD date and institution, prior projects | High | Part B-2 §4 requires a CV. Draft §1.4 is qualitative only |
| 12 | Host and participant capacity descriptions | High | Part B-2 §5 requires capacity of participating organisations |
| 13 | Security screening statement and MSCA Green Charter statement | Medium | Part B-2 §7 and §8 |
| 14 | Page-limit decision | Medium | Part B-1 sections 1–3 are capped at 10 pages including tables, figures and references. The draft exceeds this |

Items 1, 2, 7, 10, 11 and 12 are the ones you said you would supply manually. Items 3, 4, 5, 6, 8, 9,
13 and 14 need a decision from you, and I can draft a candidate for each once you confirm the direction.

Item 14 deserves a note now. Compressing prose at the current scope is how sentences get long and
evaluators get lost. The right response is to cut content, and the cut is a proposal decision, not a
runner decision.

---

## 5. Tier 3 seed template

Every seeded file uses one envelope. This is the contract the seeds follow, so your review is a check on
status and source, not a read of free prose.

```jsonc
{
  "_provenance": {
    "record_type": "<tier3 record type>",
    "authority": ["CLAUDE.md §5 Tier 3, §12.2 status categories, §13.3 no fabricated project facts"],
    "source": "docs/tier3_project_instantiation/source_materials/part_b_draft_v0/FIELDWISE_MSCA_Master_Draft.docx",
    "lift_record": "docs/tier4_orchestration_state/decision_log/fieldwise-tier3-lift_<date>.json",
    "provenance_manifest": "docs/tier3_project_instantiation/hand_lift_provenance.json"
  },
  "spine_status": "confirmed_real",
  "<collection_key>": [ /* records */ ]
}
```

Every record carries four fields beyond its own content.

| Field | Meaning |
|-------|---------|
| `validation_status` | Exactly one of Confirmed, Inferred, Assumed, Unresolved (§12.2) |
| `source_ref` | Draft heading and paragraph range, for example `§1.1.8, ¶80–101` |
| `note` | Why the status is what it is. Required on anything not Confirmed |
| `checklist_ref` | Token linking to `confirmation_checklist.json`, on identity and decision records only |

Status assignment follows one rule. Text present in the draft is **Confirmed**. Content derived by
reasoning from draft text is **Inferred**, and the note states the derivation. Content adopted with no
draft basis is **Assumed**, and it must have a matching declaration in `working_assumptions.json`, which
the W1 predicate enforces at Phase 8. Content that is missing or contradicted is **Unresolved**, which
blocks the gate that needs it. No seed invents a project fact.

### Worked example: `architecture_inputs/objectives.json`

```jsonc
{
  "_provenance": { "record_type": "tier3_objectives", "...": "as above" },
  "objectives": [
    {
      "objective_id": "O2",
      "title": "Identify physiologically meaningful hyperspectral early-warning signatures and establish their Sentinel-2 transferability",
      "measurable_target": "Validated hyperspectral/Sentinel-compatible feature library",
      "verification": "Feature library documented with per-feature Sentinel-2 transferability verdict",
      "addressed_by_work_packages": ["WP2"],
      "linked_research_questions": ["RQ1", "RQ2"],
      "linked_hypotheses": ["H1", "H2"],
      "target_month": 12,
      "responsible_partner": "DATA_PARTNER",
      "contributing_partners": ["FELLOW", "HOST"],
      "validation_status": "Confirmed",
      "source_ref": "§1.1.8 ¶87-89; WP2 §3.1 ¶263-274; MS2 ¶274"
    }
  ]
}
```

`objective_id`, `title`, `measurable_target` and `verification` come straight from the draft table.
`addressed_by_work_packages`, `linked_research_questions` and `target_month` come from the WP2 block and
the MS2 milestone, so they stay Confirmed. Had I inferred the WP link, the record would read `Inferred`
with the derivation in `note`.

### Worked example: an unresolved record

```jsonc
{
  "partner_id": "TRANSFER_PARTNER",
  "short_name": "MVCRI",
  "legal_name": null,
  "entity_type": "legal_entity",
  "role_in_action": "Associated partner - cross-country transferability environment",
  "country": "Bulgaria",
  "country_code": "BG",
  "beneficiary": false,
  "validation_status": "Unresolved",
  "source_ref": "§3.2 ¶429-430; §1.3 ¶208-209",
  "note": "Role, country and function are draft-confirmed. Full legal name, city, PIC and contact person are absent from the draft and await operator input (blocking item 1). Participation mode is likewise open (blocking item 2)."
}
```

This is the shape every gap takes. The record exists, states what the draft confirms, names what is
missing, and fails the gate that depends on it. It never guesses a legal name.

### Narrative files

`concept_note.md` and `strategic_positioning.md` are Markdown, so they carry a YAML front-matter block
holding the same `_provenance` fields, and each section header carries an HTML comment with its
`source_ref`. Their prose is lifted from the draft with no rewriting, because the draft is the source of
truth and rewriting would break traceability under §10.5.

---

## 6. The Obsidian vault: recreate, do not update

The vault at `MSCA/methodology_graph/` holds 140 nodes across 22 folders. Folders 11–19 hold the Tier 3
binding nodes and the Part B section nodes that `runner/graph_compiler.py` compiles.

Its content describes the superseded project. Folder 11 holds five objectives about probabilistic
multi-sensor diagnosis of a latent field state. Folder 14 holds five work packages built on Route B and
PlanetScope. Folder 16 holds ten risks, six of which are about PlanetScope access, SAR retrieval and
Route A cost. Folder 19 holds Part B sections written from that architecture. FIELDWISE replaces the
methodological architecture itself, not only its wording, so an incremental update would edit almost
every node and leave stale link structure behind.

**The vault does not block the run.** The manifest binds the Tier 3-sourced canonical pack deriver, and
`--from-graph` compilation is opt-in and non-destructive under the DOD-1d ruling. You can seed Tier 3
directly from the draft and run Phases 1–8 with the vault untouched.

**A stale vault does cause two problems.** `runner/graph_claim_verifier.py` audits Tier 5 claim IDs
against vault node IDs and will fail against FIELDWISE sections. A vault that contradicts Tier 3 is also
a §12.3 tier contradiction that must be logged rather than ignored.

My recommendation is to sequence the vault after the first run, not before it.

| Option | When | Trade-off |
|--------|------|-----------|
| Quarantine now, re-author later (recommended) | Log the supersession in the decision log, run Phases 1–8 from hand-lifted Tier 3, re-author the vault against the resulting Tier 3 | Fastest path to a running proposal. The claim verifier stays red until the vault is re-authored |
| Re-author first | Rewrite folders 02–08, 10–19 for FIELDWISE, then compile Tier 3 with `--from-graph` | Tier 3 becomes deterministically reproducible from the graph. Costs a full vault authoring pass before anything runs |

Under either option, folders `00_meta`, `01_sources`, `09_terminology`, `90_dashboards` and
`99_governance` are largely project-neutral and survive. `tools/author_msca_proposal_graph.py` is the
deterministic authoring path and should be rewritten for FIELDWISE rather than hand-edited.

---

## 7. Sequence

| Step | Work | Gate on you |
|------|------|-------------|
| S1 | Create `fieldwise-run-01`, execute the purge in §2, commit | Approve the §2.1 three-way decision-log split |
| S2 | Move the draft into Tier 3 source materials, log the §13.11 correction | — |
| S3 | Issue the operator input pack: the 14 items of §4 as a single fill-in form | You supply items 1, 2, 7, 10, 11, 12 |
| S4 | Seed the 12 authorable Tier 3 files from the draft using the §5 template, plus `hand_lift_provenance.json` | — |
| S5 | Fold your input into `roles.json`, `partners.json`, `confirmation_checklist.json` and `working_assumptions.json` | You decide items 3, 4, 5, 6, 8, 9, 13, 14 |
| S6 | Present the authorisation packet: every record, its status, its source reference, and every remaining Unresolved item | **You authorise** |
| S7 | Run Phase 1, inspect `phase_01_gate`, then run Phases 2–8 with a stop at each gate | You clear each gate failure |
| S8 | Re-author the vault against the resulting Tier 3, or defer | Your call per §6 |

The run halts honestly at the first gate whose inputs are incomplete. That is a correct output under
§12.4, not a fault to work around.

---

## 8. Open questions for you

1. Do you accept the §2.1 split, and do you want the §2.4 category error raised as a §14.5 amendment
   question, or left as it stands with the engine rulings inside Tier 4?
2. Are MATE, MVCRI and AgroVIR associated partners, secondment hosts, or informal collaborators?
3. Does the fellowship include a secondment or a non-academic placement? The draft implies AgroVIR
   involvement but never names a placement.
4. Do you want the vault re-authored before the run or after it?
5. Should the E4 harness golden baselines be re-frozen after the run, or should that lane be marked
   expected-red on this branch?
