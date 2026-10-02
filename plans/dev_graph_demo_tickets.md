# Tickets: Dev Graph demo (instance two)

Initialises a second, separate project on the `dev_graph_demo` branch and populates every tier with authoritative records for topic `HORIZON-CL6-2027-01-BIODIV-01` ("Integrating Remote Sensing and in-situ observations of Biodiversity, towards a fully interoperable observation and data framework"). The project is a demonstration, not a submission. Its purpose is to run the Milestone 1 dev graph (snapshot builder, evidence packages, shadow impact planner, revision contracts, blind pre-evaluation lane) on a full-size, real-call world instead of the synthetic fixture. This is handoff stage 7 (real-document integration), which the Milestone 1 PRD left out of scope.

The consortium is derived from the instance-one consortium's expertise and then fully anonymised. The project concept needs explicit operator approval before any architecture seed is authored.

Work the **frontier**: any ticket whose blockers are all done. Tickets 1, 2, 3 and 4 can start immediately. Clear context between tickets.

Constraints that apply to every ticket:

- `CLAUDE.md` governs. No call constraint is invented outside Tier 2B (§13.2). No project fact is invented outside Tier 3 (§13.3). A gap is flagged, declared in `working_assumptions.json`, or left as an honest gate failure.
- The DAG scheduler, gate evaluator, gate library, budget-before-Phase-8 block and whole-Tier-3 reuse fingerprint are not modified. The impact planner stays in shadow mode.
- No real organisation name, person name, place, web address, grant or project identifier from instance one appears anywhere on this branch. That includes Tier 3–5, Tier 4 logs, vault notes, commit messages and this file. The instance-one Part B-1 stays outside the repository.
- The internal-docs style profile governs decision log entries and plans. The proposal-prose profile governs Tier 5 text.
- Tests run with `py -3.10`. Runner phases are dispatched only by the tickets that say so.

## Branch baseline and demo scope record

**What to build:** A recorded starting point for instance two. Confirm `dev_graph_demo` branches from the Milestone 1 closure commit, that Tier 3 and Tier 5 are still empty from the 22 September purge, and that the full test suite matches the recorded baseline. Write one decision log entry that fixes the demo's scope: instance two, demonstration only, never submitted, anonymised consortium, the selected topic, and the dev-graph questions the demo must answer (does the snapshot build on real records, do packages stay within budget, does the planner agree with real reruns, does the blind lane stay leak-free).

**Blocked by:** None — can start immediately.

- [x] The decision log entry records the branch, the base commit SHA and the Milestone 1 closure SHA.
- [x] Tier 3 holds only `.gitkeep` and `working_assumptions.example.json`. Tier 5 is empty.
- [x] The full test suite shows no new failures against the Milestone 1 baseline.
- [x] Unrelated working-tree changes (for example under `.agents/skills/`) are committed or stashed separately, not mixed into demo commits.

## Tier 2B intake for the selected topic

**What to build:** The topic's authoritative Tier 2B sources, so Phase 1 has something real to analyse. Add a call extract and its slice for `HORIZON-CL6-2027-01-BIODIV-01` in the same shape as the existing extracts (topic code, instrument type, dates, budget, expected outcomes, scope, eligibility restrictions, source document and pages). The work programme source is Horizon Europe 2026–2027 Part 9 (Cluster 6). Only the grouped JSON is in the repository today, so the operator downloads the Part 9 PDF and the portal topic JSON. The workspace shell cannot reach the portal. Then write `selected_call.json`.

Three facts need resolving against the downloaded sources, not against memory:

- **Dates.** The grouped JSON gives opening 20 April 2027 and deadline 22 September 2027. Two automated reads of the portal returned different dates. Record the value in the downloaded source and log the contradiction per §12.3.
- **Grant type.** One portal read says lump sum. `legal_and_financial_setup` is empty in the grouped JSON. This decides the budget-gate route (see the budget ticket).
- **Cross-cutting requirements.** The scope names GBIF, OBIS and LUCAS cooperation, optional JRC participation, EMBAL and LUCAS grassland data, EUNIS and Global Ecosystem Typology interoperability, EOSC and Common Data Spaces, and coordination with ESA FuturEO projects. Each needs a traceable source span.

**Blocked by:** None — can start immediately.

- [x] `call_extracts/HORIZON-CL6-2027-01-BIODIV-01.json` and `.slice.json` exist and cite the Part 9 PDF by page.
- [x] The Part 9 PDF and the portal topic JSON are stored under Tier 2B `work_programmes/` and registered in `docs/index/document_registry.json`.
- [x] `selected_call.json` names the topic, the action type (RIA), the per-project contribution (EUR 5,000,000) and the confirmed dates. It is marked Confirmed only for fields traced to a source.
- [x] The date contradiction and the grant-type finding each have a decision log entry naming the prevailing source.
- [x] Tier 2B `extracted/` is **not** hand-written. Phase 1 writes it.

## Tier 1 and Tier 2A coverage check for an RIA

**What to build:** A read-only check that the call-neutral tiers already cover this instrument, with a gap list if they do not. Tier 1 holds the 2026–2027 General Annexes, both model grant agreements and the lump-sum MGA. Tier 2A holds the RIA/IA application and evaluation forms. Confirm that the extracted registries (`instrument_registry.json`, `section_schema_registry.json`, `evaluator_expectation_registry.json`, `template_adapter_map.json`) have an RIA entry with sections, page limits and award criteria taken from the forms. Tier 1 `extracted/participation_rules.json` is empty on this branch (checked 29 September). Populate it from the General Annexes 2026–2027 (Part 15), at minimum the consortium-composition condition on pages 12–13 and the eligible-country and China-restriction rules for RIAs on pages 5–6. The consortium ticket depends on the composition condition.

**Blocked by:** None — can start immediately.

- [x] A validation report lists each registry and states Confirmed, Unresolved or missing for the RIA entry.
- [ ] Any missing RIA entry is filled from the Tier 2A PDF with page references. No entry is written from programme knowledge (§10.6).
- [x] `participation_rules.json` carries the consortium-composition condition with its source span: at least three independent legal entities as beneficiaries, each established in a different country, at least one in a Member State and at least two others in different Member States or Associated Countries. Affiliated entities do not count. The JRC and international European research organisations are deemed established in a Member State other than the other participants'.
- [x] No Tier 1 or Tier 2 source document is modified (§13.11).

**Why one box is unticked.** Two artifacts were filled: the RIA entry of `evaluator_expectation_registry.json`, and Tier 1 `participation_rules.json`. `template_adapter_map.json` was left empty, because it has no schema and no consumer, so any shape written into it would be invented (§16.3). The evaluator entry also carries no page references, because its declared schema has no field for one. Both gaps are recorded as findings F1 and F10 and decision D3.

**Findings carried forward.** The China restriction does not bind this project. Cluster 6's "Biodiversity and ecosystem services" is on the exempt-destination list (F5). The stored RIA Part B page limit is 40, and this lump-sum topic is allowed 45 (F2). The composition condition is on pages 13 and 14, not 12 and 13 as this ticket said (F4). `g02_p15` would have passed for an RIA run while the evaluator registry held only an MSCA-PF entry (F3).

**One more for the consortium ticket.** The agnosticism-lint denylist cannot be reused as it stands. It contains Member State names that the General Annexes enumerate verbatim (F9). The award criteria, scale and thresholds have no registry field, so the report carries them for the profile ticket (F7).

## Anonymised consortium with fictional gap partners

**What to build:** `consortium/partners.json` and `consortium/roles.json` for instance two, covering twelve partners. Each partner is a pseudonymous organisation (`P01`, `P02`, …) described only by type, sector and capability. People appear as roles (for example "senior plant physiologist, P01"), never as names. Country is a pseudonymous slot (`C1`, `C2`, …) that records only whether it is a Member State (MS) or an Associated Country (AC), because the composition rule needs that. The mapping from pseudonyms to real entities is not stored in the repository.

Partners come from two sources, and each record says which in a `capability_basis` field:

- **P01–P06, derived.** Anonymised from the instance-one consortium. Their capabilities trace to the instance-one Part B-1.
- **P07–P12, fictional.** Invented to close the gaps against the topic. They have no name, acronym, city or web address, and must not be modelled on a recognisable real organisation.

The six derived profiles, taken from the instance-one Part B-1 and generalised so they do not re-identify:

| Pseudonym | Type | Capability carried into the demo |
|---|---|---|
| P01 | Public research organisation, agricultural institute | Plant physiology and stress metabolomics; phenotyping; statistical design, calibration and leakage-safe predictive validation |
| P02 | University, geoinformatics institute | Hyperspectral imaging, field spectroscopy, sensor harmonisation, satellite EO, UAV support |
| P03 | University, agriculture | Multi-season controlled field-experiment archive (physiological, spectral, soil-water, weather); crop and water-balance modelling; precision agriculture |
| P04 | SME, software engineering | Web decision-support engineering, provenance, reproducible inference pipelines |
| P05 | SME, farm-management information systems | Requirements, usability and interoperability evaluation; multi-country user network as an uptake channel |
| P06 | Public research institute, vegetable crops | Crop-specific transfer and production-context data |

Instance one had one fellow. Instance two is a multi-partner RIA, so partner roles are redesigned rather than copied. Reuse capabilities, not the fellowship structure. P06 had no in-action role in instance one. Here it becomes a beneficiary, and it is the second country.

**The gaps.** Measured against the topic's scope, the derived six have:

- no freshwater or marine expertise, although the scope asks for capabilities "across terrestrial, freshwater and marine ecosystems";
- no genomic, transcriptomic or eDNA capability; P01's metabolomics is the only omics;
- no biodiversity data-infrastructure partner for GBIF and OBIS cooperation, Darwin Core and EUNIS work, or EOSC links;
- no socio-ecological or socio-economic analysis of the pressures the scope names;
- no partner that runs AI habitat mapping and trend prediction at European scale;
- only two countries, C1 and C2, both MS. That fails the composition condition, which needs three.

**The fictional gap partners** proposed to close them:

| Pseudonym | Country slot | Type | Capability that closes a gap |
|---|---|---|---|
| P07 | C3 (MS) | Public research organisation, freshwater ecology | River, lake and wetland ecology; eDNA sampling networks; freshwater monitoring aligned with water-policy reporting; in-situ data for floodplain and riparian ecotones next to farmland |
| P08 | C4 (AC) | University, marine and coastal science | Coastal and benthic habitat mapping (for example seagrass); Marine Strategy Framework Directive indicators; sub-orbital and ocean-colour EO for transitional waters; contributes occurrence data to OBIS |
| P09 | C5 (MS) | University, biodiversity genomics | Genomic, transcriptomic and eDNA metabarcoding; reference libraries; bioinformatics pipelines; standardised omics metadata |
| P10 | C3 (MS) | Non-profit research organisation, biodiversity data infrastructure | Runs a national species-occurrence data facility that publishes to GBIF; Darwin Core, EUNIS and Global Ecosystem Typology crosswalks; FAIR metadata; EOSC service integration |
| P11 | C6 (AC) | University institute, socio-ecological systems | Land- and sea-use pressure analysis; socio-economic drivers from agriculture and aquaculture; policy-reporting needs under the Habitats and Birds Directives and the Nature Restoration Regulation; stakeholder engagement |
| P12 | C5 (MS) | SME, EO analytics and AI | Deep-learning habitat and ecosystem classification from Copernicus Sentinel-1 and Sentinel-2; scalable cloud processing; predictive biodiversity trend modelling at European scale |

Together the twelve give a coherent storyline for the concept ticket to test: a catchment-to-coast chain from farmland and grassland (P01–P06) through freshwater ecotones (P07) to coastal transitional waters (P08). The same agricultural pressures run through all three realms. That covers terrestrial, freshwater and marine demonstration cases on one pressure gradient.

**Composition check.** The condition, read from Tier 1: at least three independent beneficiaries, each in a different country, one of them in an MS and the others in MS or AC. With P07–P12 the consortium spans six country slots (four MS, two AC). The design builds in redundancy: removing any single gap partner still leaves at least three countries. Honest status: the condition is **met only under assumption**. The derived partners alone span two countries, and every partner that adds a country is fictional and Assumed. The optional JRC participation the topic allows is not counted.

**Blocked by:** None — can start immediately. The composition check uses the Tier 1 and Tier 2A coverage check.

- [x] `partners.json` and `roles.json` hold P01–P12 with type, sector, country slot and MS or AC, capability list, role and `capability_basis` (derived or fictional). Every derived capability traces to a line of the instance-one Part B-1, recorded in an operator-held mapping outside the repository.
- [x] P07–P12 carry participation status Assumed and are declared in `working_assumptions.json` as fictional, unconfirmed partners, with the gap each one closes. P01–P06 carry the status the operator sets for the demo, recorded in the decision log.
- [x] No fictional partner has a name, acronym, city or web address, and none is described so that it matches a single real organisation.
- [x] Partners are recorded as independent legal entities. None is modelled as an affiliated entity of another, because affiliated entities do not count toward composition.
- [x] A leakage test scans Tier 3, Tier 4, Tier 5 and the vault for instance-one proper nouns. It reuses the agnosticism-lint denylist, extended with the instance-one organisation names, people and places, and it fails on any hit.
- [x] The gap analysis is written to Tier 4 as a validation report, one line per topic requirement, naming the partner that covers it and the Tier 2B span it answers. No requirement is left without a covering partner.
- [x] A composition test evaluates the condition three ways: all twelve partners (met, Assumed), derived partners only (not met), and with each gap partner removed in turn (met in every case). The result cites the Tier 1 span.


**Why the leakage test is not a verbatim denylist reuse.** The standing agnosticism-lint denylist cannot be reused as it stands. That is finding F9 of the Tier 1 coverage check and finding F2 of the scope record. The raw denylist returns 46 hits on the finished tree, across six files, and none of them is a leak. Eight nouns account for all of them. Four are Member State and nationality names the General Annexes enumerate, one is an instrument name, and three are generic domain words the derived profiles use.

`runner/leakage_scan.py` therefore derives its noun set: `PROJECT_NOUNS` minus the scoped-out nouns, plus the project identifiers that denylist never held. Derivation means a noun added to the standing denylist is scanned from that moment. A separate partition test classifies every noun as identity, re-identifying or scoped-out, so the reason each one is a leak is on the record.

**The branch is not anonymity-clean, and the scan now says so.** An adversarial review of this ticket's own output found the first version reporting clean while instance one's project acronym stood eleven times in the Tier 4 purge record, inside the scan's own scope. The standing denylist never held that acronym: it was built from instance one's Tier 3 identity spine, which names people and partners, not the project.

`LeakageReport` now separates `ok`, meaning no new leak, from `clean`, meaning no leak at all. The CLI prints `OK, NOT CLEAN` and exits 0 while the recorded leak stands. The purge record is not redacted, because rewriting a Tier 4 decision record to suit a later constraint is an operator decision (§9.1). Four files under `plans/purge/` carry the same acronym, outside the scan's declared scope. Findings F8 and F9, decision D8.

**Why the noun extension is a parameter, not a literal.** Hard-coding further instance-one names into the scan would write onto the branch nouns the constraint forbids. The extension is `leakage_denylist(extra_nouns=...)` and the CLI's `--extra-nouns` file, which the operator keeps outside the repository, as with the pseudonym mapping. A name the branch already carries is named in the module instead: a denylist cannot forbid what it cannot say. Reuse is a starting point, never a proof of completeness. Recorded as findings F2 and F8 rather than claimed as exhaustive.

**Operator decisions recorded.** All twelve partners carry participation status Assumed, not only the fictional six: nobody has confirmed any partner's participation in instance two, and the derived six collaborated on a different project. P01 is the coordinator, declared rather than Confirmed. Both are in `docs/tier4_orchestration_state/decision_log/demo-consortium_2026-09-30.json`.

**Findings carried forward.** The freshwater and marine realms rest on one fictional partner each (F4). The composition condition survives losing either, but the second scope requirement does not. Ten of the twelve partners sit in three country slots and five of them in C1, which is geographically thin for a topic asking for use cases across Member States and Associated Countries (F5). Both go to the concept ticket. `roles.json` has no declared schema in `artifact_schema_specification.yaml`, so its shape is authored and says so.

## Project concept for operator approval

**What to build:** `project_brief/concept_note.md`, `project_summary.json` and `strategic_positioning.md`, drafted for the operator to approve or send back. This ticket has a human gate. No architecture seed is authored until the operator records approval.

The draft proposes a concept that uses the consortium's real strengths and answers all three expected outcomes. A starting direction to test, not a decision:

- **Anchor ecosystems:** agricultural landscapes, grasslands and their ecotones, which the scope names as under pressure from agriculture. This links to LUCAS grassland and EMBAL.
- **Genome to space chain:** plant stress metabolomics (P01) and in-situ plots → field and UAV hyperspectral (P02) → Sentinel-2 and other Copernicus data, with harmonised FAIR workflows and AI habitat and ecosystem mapping against EUNIS.
- **Training data:** long-term field archives (P03) reworked as documented training and validation sets, which is the topic's third expected outcome.
- **Mainstreaming into agriculture:** the FMIS channel (P05) and decision-support engineering (P04) carry biodiversity indicators into farm-management tools. The scope names agriculture as a target sector.

The operator decides how the gaps are closed. The options to set out:

1. **Add gap-filling partners** (P07 onward) for freshwater and marine demonstration cases, genomics or eDNA, a biodiversity data infrastructure, socio-ecological analysis and a third country. Each is declared in `working_assumptions.json` as not yet confirmed, following the operator manual's rule for unconfirmed members. This is the recommended option, because the scope asks for capabilities "across terrestrial, freshwater and marine ecosystems".
2. **Narrow to terrestrial ecosystems** with the current six. Faster, but the concept must state it as a scope risk, and Phase 2 will probably fail on it.
3. **Mixed:** add only the partners needed to cover the three ecosystem realms and omics, and declare the rest out of scope.

The draft also records the coordination commitments the scope requires: resources earmarked for GBIF, OBIS and LUCAS, a place for JRC, and ESA FuturEO coordination. It proposes a project duration and says it is an operator choice, because Tier 2B sets no duration.

**Blocked by:** Tier 2B intake for the selected topic; Anonymised consortium profile from the instance-one expertise.

- [x] Every call phrase in the concept traces to a Tier 2B span. Every capability claim traces to `partners.json`.
- [x] The gap options are presented with the consequences of each. The draft does not choose silently.
- [x] The operator's decision (approved, approved with changes, or rejected) is written to the decision log with the chosen gap option and duration.
- [x] After approval, `concept_note.md`, `project_summary.json` and `strategic_positioning.md` are frozen per the operator manual's freeze rule.
- [x] The leakage test passes on the brief.

**Outcome.** Approved 30 September 2026. Gap option 1 (all twelve partners), duration 48 months, no
acronym. The reasoning, the seven design decisions, the eight findings and the freeze fingerprints are
in `docs/tier4_orchestration_state/decision_log/demo-concept_2026-09-30.json`.

Three things later tickets need from it. The duration lives in `selected_call.json` as
`project_duration_months`, Assumed, because the runner reads it nowhere else (D5). The freeze rule is
now a fingerprint test, not a convention (D6). An operator act carries a lifecycle `state`, never a
§12.2 status (D8).

## Source materials and the sources index

**What to build:** `source_materials/` for instance two plus `sources.json`, which the dev-graph builder reads. Sources are real, public literature and datasets relevant to the approved concept, such as the policy frameworks named in the scope and public datasets like LUCAS and EUNIS. Each source carries an ID, a citation, a location and the spans the concept relies on. No instance-one unpublished material or manuscripts are included.

**Blocked by:** Project concept for operator approval.

- [x] `sources.json` validates against the builder's schema, and the builder reads it without error.
- [ ] Each source cited in the concept has an entry. Each entry resolves to a stored file or a public persistent identifier.
- [x] No source is described as supporting a claim it does not contain. Claims without a verified span keep declared status and verified span as separate fields.

**Outcome.** Twenty-two sources. Six are transcribed pages of the stored Part 9 PDF, carrying 45
resolved spans. Sixteen are external references carrying no text. All 23 concept claims have a span
holding their call phrase verbatim. The report and the ten decisions are in
`demo-source-materials_2026-09-30.json`, under `validation_reports/` and `decision_log/`.

**The rule the index is built on.** A source carries verbatim text only when that text replays
byte-equal from a stored file. A source record is the one place in Tier 3 where an invented quotation
plus a span makes the builder report a grounded claim no document supports. The builder cannot catch
that. Byte-equal replay can.

**Why one box is unticked.** `SRC-EMBAL` resolves to no identifier, only to the call page naming it.
Nine other identifiers are homepages rather than persistent identifiers. Both are recorded honestly.
Neither meets the box as written (F3). No identifier was resolved at all: this workspace has no usable
egress, and the fetch tool returns a written answer rather than bytes (F1, F2).

**Carried forward.** The call names SAGE, the 2030 biodiversity strategy and the Kunming-Montreal
framework. The concept names none (F4). Nothing names a Sentinel mission or Darwin Core (F10). The name
sweep cannot derive single capitalised words (F5).

## Architecture seeds and the uncertainty ledger

**What to build:** The Tier 3 seeds Phases 3–6 read: `objectives.json`, `outcomes.json`, `impacts.json`, `workpackage_seed.json`, `milestones_seed.json`, `risks.json`, and then `working_assumptions.json`. They are authored through the vault per the operator manual (scaffold with the `obsidian-graph` skill, author folders 11–17, compile, promote), or directly as JSON if the operator prefers. The decision is recorded either way. Seeds are a real consortium design, with enough tasks and cross-partner assignments to exercise the planner: at least six work packages, tasks split across partners, and deliverables and milestones that depend on each other across work packages.

`working_assumptions.json` declares every open fact: unconfirmed gap partners, country slots, the duration, and effort shares. Declared facts become Assumed, not Confirmed.

**Blocked by:** Project concept for operator approval.

- [x] Every objective maps to at least one expected outcome span in Tier 2B.
- [x] Every task names a lead partner pseudonym and at least one task per work package involves two or more partners.
- [x] `working_assumptions.json` lists each unconfirmed partner and each Assumed value, with the reason.
- [x] The leakage test passes on all Tier 3 files and the vault.
- [x] Tier 3 is frozen and its fingerprint is recorded in the decision log.

**Outcome.** Six seeds authored directly as JSON, not through the vault (D1), because instance two has
no methodology vault and folders 11 to 17 would have stood on an empty 00 to 10. Six objectives, seven
work packages, 35 tasks, 24 deliverables, eight milestones, seven outcomes, six impact pathways with
twelve indicators, thirteen risks, over 48 months. Ten more ledger declarations, twenty-two in all.
Tier 3 frozen: ten artifacts fingerprinted here, the three brief artifacts left to the concept record,
the ledger exempt. The thirteen findings and the nine decisions are in
`docs/tier4_orchestration_state/decision_log/demo-architecture-seeds_2026-09-30.json`.

**The number that was wrong.** The first draft said the destination sets seven expected impacts. It
sets six. The fourth bullet straddles a page break and its tail carries no bullet marker, so counting
it separately invented a call constraint the source does not make (§13.2). The wrong number reached
eight records before the two-axis review caught it, on both axes independently. The fix is a check:
`tests/test_demo_architecture_seeds.py` counts the bullet markers in the replayed page text and holds
every record to that count (D9, F13).

**Two seams the next tickets inherit.** `workpackage_seed.json` has two readers that disagree on the
key: the dev-graph builder reads `wp_id`, the dependency normaliser reads `id` and silently skips a
work package carrying neither. Every work package carries both and a test pins them equal (D4, F1).
And the topic's call extract carries no expected impacts at all — they are set at destination level, so
pages 47 and 48 were transcribed into `sources.json` and Phase 1 must extract them (D3, F2).

**What is deliberately not settled.** Effort is Unresolved and declared, never seeded: nobody has
agreed a split for a consortium whose every member is Assumed (D5). The twelve indicators carry no
target numbers for the same reason (D6). `roles.json` still records the work package leads as
Unresolved, because it is frozen and was honest when written; the leads are in the ledger instead (D8).
A deliverable cannot depend on another deliverable — the relationship set has no such predicate, so
deliverables couple across work packages through milestones (F12).

## First dev-graph snapshot on the demo world

**What to build:** Run `build_snapshot` on the populated repository root, before any runner phase. This is the first build on real records. A fail-closed error is a finding to record and fix at its source record, not by loosening the builder. Then build one evidence package per view policy for three named tasks and check the manifests.

**Blocked by:** Source materials and the sources index; Architecture seeds and the uncertainty ledger.

- [x] The snapshot builds, and two builds give the same snapshot ID.
- [x] Every fail-closed error hit on the way is listed with its cause and the record fix, in a Tier 4 validation report.
- [x] Each package manifest reports completeness. Any package marked incomplete under the default budget is listed with the item that did not fit.
- [x] Assumed partners and Unresolved claims appear in the manifests' unresolved lists.
- [x] Node and edge counts are recorded so later scenarios can be compared against them.

**Outcome.** The snapshot builds at the first attempt: 116 nodes and 305 edges from five Tier 3
records, deterministic across two builds and across a full replay of all 38 artifacts. Eighteen packages,
one per view policy for T3.1, T4.1 and T1.1, all incomplete under a default budget of 3,000. The eight
findings and the eight decisions are in this ticket's validation report,
`demo-dev-graph-snapshot_2026-09-30.json`.

**The builder raised no error, so nothing was fixed at a record.** The defect was in the index instead.
A manifest rolled up a declared status from document claims alone, and Tier 5 is empty. All eighteen
packages reported Confirmed over records that every one declared Assumed (F1).

**Three numbers the next tickets need.** A real work plan's mandatory set costs 5,411 to 21,885 estimated
tokens, so the default budget is three to eight times too small (F2). Under it the manifests are dominated
by the budget rather than by the view: 1,224 over-budget exclusions against 5 policy exclusions, and none
at all on the densest seed (F8). And the blind lane cannot be shown leak-free here, because the world holds
nothing the policy would hide (F4).

**The number that was wrong, again.** The first draft of F8 said no manifest records a policy exclusion.
It was generalised from T3.1, which records none, and three of the eighteen do.

The seeds ticket recorded this same lesson as its D9. Repeating it means the rule was not yet mechanical
here. Every exclusion count is now derived into the run summary and read back by
`TestWhatThePolicyKeptOut` (D8).

## Runner Phases 1 to 6 on the demo

**What to build:** Dispatch Phases 1–6 through the runner on the frozen Tier 3. Phase 1 writes Tier 2B `extracted/`. Phase 2 writes `topic_mapping.json` and `compliance_profile.json`. Phases 3–6 write their Tier 4 outputs. A gate failure is a valid result. It is recorded, the cause is fixed at the right tier, and the phase is rerun. Each rerun's scheduler reuse decisions are kept, because the shadow comparison needs them.

**Blocked by:** Architecture seeds and the uncertainty ledger; Tier 1 and Tier 2A coverage check for an RIA.

- [x] Phases 1–6 each reach released, or the blocking gate and reason are recorded in Tier 4.
- [x] Tier 2B `extracted/` holds the six files for this topic, traceable to the Part 9 source.
- [x] Run manifests with reuse decisions are preserved for every run.
- [x] Run cost and duration per phase are recorded.

## Budget request and the Phase 7 gate

**What to build:** The Phase 7 budget route chosen by the grant-type finding. If the topic is lump sum, prepare a budget request from the request template and the Phase 3, 4 and 6 outputs. The operator runs it through the external Lump Sum Budget Planner and places the response in `received/`. The response is validated against the interface contract. The repository never computes a lump-sum figure (§8.1). This ticket has a human step. Until the response exists, Phase 8 stays hard-blocked, and the demo continues with the scenarios that do not need Phase 8.

**Blocked by:** Runner Phases 1 to 6 on the demo; Tier 2B intake for the selected topic.

- [x] The budget request conforms to `interface_contract.json` and names pseudonymous partners only.
- [x] A received response is validated, or the missing response is recorded as a blocking gate failure.
- [x] Phase 7 reaches released, or its hard block on Phase 8 is shown intact.

**Outcome.** The request is composed and conforms: 7 work packages, 12 pseudonymous partners, and 38
effort and cost fields left to the planner as a non-numeric sentinel. No euro amount appears in it, the
call's own indicative figures included. The operator has not run the planner, so criteria 2 and 3 are met
on their second branch. `received/` is empty, which is `g08_p02`, and the hard block on Phase 8 is intact.
Phase 7 is not dispatched and no gate result is written.

**Amended 1 October 2026 by ticket A in `plans/tickets_budget_and_blind_lane.md`.** No planner exists
for this repository, so the operator overrode six constitutional clauses for that task alone. One fictional
response now sits in `received/`, which lifts `g08_p02`, `g08_p04`, `g08_p05` and `g08_p06`. The gate
still fails on `g08_p03` and `g08_p08`, and the Phase 8 block stands. The override is recorded in
`demo-fictional-budget-override_2026-10-01.json`.

**Nothing in the repository validated a budget request or a budget response.** `g08_p04` read the
interface contract as a JSON Schema. That document has no JSON-Schema keyword at its root, so the
predicate accepted every payload. Ten findings and nine decisions, three of them from the code review,
are in `demo-budget-request-phase7_2026-10-01.json`.

## RIA pre-evaluation profile in the harness

**What to build:** A versioned pre-evaluation profile for RIA, built with the Milestone 1 profile mechanism from the Tier 2A RIA evaluation form: criteria (Excellence, Impact, Quality and efficiency of the implementation), scale, weights, thresholds and the criteria-to-sub-section mapping. No harness Python changes are needed. If one is, that is a Milestone 1 defect to record.

**Blocked by:** Tier 1 and Tier 2A coverage check for an RIA.

- [x] The profile loads and has its own version. Every field the form or the General Annexes can
  supply traces to them. The three classes that cannot are declared with their §12.2 status (F7).
- [x] The existing MSCA-default profile tests still pass.
- [x] A dry run on a synthetic RIA-shaped candidate produces a report with the RIA criteria.

**Outcome.** Three data files and no Python: `harness/profiles/ria_default.json`,
`harness/evaluator_scorecard_ria.json` and `harness/rubrics_ria.json`. Six expectations, two per
criterion, scored 0 to 5 and summed unweighted to 15 with a threshold of 10. The scorecard was
generated with the aspect and level texts extracted from `ef_he-ria-ia_en.pdf`, not retyped, and the
transcription checks re-read pages 2, 4 and 5 and compare, verbatim up to whitespace collapsing. One
aspect breaks across the page boundary, so the test strips page 5's running header and asserts it
carries the version the provenance claims. 28 tests in all. The MSCA-PF profile still loads, still
holds nine expectations, and is still the default.

**Two scorecard fields fit a multi-variant form, not this one.** The RIA/IA form annotates no aspect
with an `[OPTION for ...]` tag and the loader requires one, so every aspect carries `RIA and IA` as
an Inferred reading of the form's scope. An RIA is unweighted and `parse_scoring` requires a
`weight_pct`, so each criterion carries the ranking multiplier 1. Both are Milestone 1 defects,
recorded unfixed as F1 and F2. Ten findings and seven decisions are in
`ria-pre-evaluation-profile_2026-10-01.json`.

## Candidate Part B and the blind baseline

**What to build:** Phase 8 drafts Part B for the demo and the draft is imported as candidate version 1. The ESR intake record is written with availability not applicable (never submitted). The blind assessment runs on version 1 under the RIA profile through the blind pre-evaluation view.

**Blocked by:** Budget request and the Phase 7 gate; RIA pre-evaluation profile in the harness.

- [x] Phase 8 reaches released, or its blocking gate is recorded.
- [x] Candidate version 1 is a document snapshot with state imported, with passages linked by span.
- [x] The blind report carries the candidate hash, profile version and assessor pin, and is labelled complete or partial.
- [x] The leakage guard confirms no historical-feedback item entered the package.

**Outcome: one of four.** The blocking gate is recorded from the gate's own predicates. No node
was dispatched and no gate result was written. The planner response is absent, so `g08_p02`
fails and all six Phase 8 nodes stay frozen. Phase 8 has written nothing, and Tier 5 holds only
its placeholders. The ESR intake record carries availability `not_applicable`, which is the one
part of the ticket neither block reaches.

**Amended 1 October 2026 by ticket A in `plans/tickets_budget_and_blind_lane.md`.** A fictional
response now sits in `received/` under an operator override, so `g08_p02` passes. The gate still
fails on `g08_p03` and `g08_p08`, which the Phase 7 node writes, so the freeze is unchanged.
Criterion 2 now waits on the operator's dispatch rather than on an absent response.

**Amended again 1 October 2026: the freeze is lifted.** The operator's second Phase 7 dispatch
released n07 and `gate_09` passed 9 of 9 deterministic predicates, recorded in
`phase7_budget_gate/gate_result.json`. The six Phase 8 nodes moved from `hard_block_upstream` to
`pending`, and `--dry-run` reports n08a, n08b and n08c ready. Criterion 1 still stands on its
second branch, because Phase 8 has not reached released, but the gate it records is now a pass
rather than a block.

Criteria 2, 3 and 4 wait on a Phase 8 dispatch and on nothing else. No constitutional block
stands in front of them, and ticket B closed the F1 defect that would have failed criterion 3.
Phase 8 drafting is now permitted under §13.4 for the first time on this branch. Every figure it
draws on is fictional, so §13.8 applies to the first section written.

**Amended 2 October 2026: three of four are closed.** The operator dispatched n08a to n08f one
node at a time, and every Phase 8 node released. `gate_12_constitutional_compliance` passed 8 of
8 deterministic predicates and 6 of 6 semantic ones, the first gate on this branch with semantic
predicates bound. Criterion 1 therefore stands on its first branch, not its second.

Criterion 2 is closed. `tools/build_part_b_candidate.py` converted the three section artifacts
and `import_document` wrote `DEMO-BIODIV-2027_part_b@1101b2a653c543a4` with state `imported`.
The demo snapshot moved from 116 nodes of 7 types to 267 of 10: one `artifact_version`, three
passages and 147 claims arrived with it. Each passage carries its span over the rendered
document, and the seven declared sub-sections `B.1.1` to `B.3.2` are carried verbatim.

Criterion 4 is closed over the package the criterion actually names, not over the six the
1 October report could reach. `assert_no_leakage` ran over the blind-view package built around
candidate version 1: 151 items, three of them passages and 147 claims, clean. That is the pass
F6 said the earlier one was not, because a historical-feedback tag rides on exactly those types.
Commitments are still zero, so F6's commitment half stays open.

**Criterion 3 is the one box left, and no defect stands behind it.** Every input the blind
report binds was verified offline against the real candidate: `load_candidate` resolves all
three profile-required sections, so the scope is `complete`; the candidate hash and the profile
version are derived; and `build_pack_for` ran for all six rubric-and-section pairs with the
anchor map closing on every one. What remains is the call to the pinned assessor, which is the
operator's step:

```
py -3.10 -m harness.commands.blind_assessment assess --document DEMO-BIODIV-2027_part_b \
  --profile harness/profiles/ria_default.json --intake demo-biodiv-2027-part-b-v1
```

**Amended again, 2 October 2026: the assessor now speaks the Max subscription.** The operator
ran that command. Groq rejected the key with HTTP 401 on a well-formed 56-character `gsk_`
token, so the key is revoked, expired or belongs to a closed account. The run proved more than
the offline rehearsal did before it stopped: the snapshot resolved, the blind package built,
`assert_no_leakage` passed and the three section artifacts were materialised. Only the grades
are missing.

Rather than hold an API key, the operator chose the subscription. The harness refuses the
`claude_cli` transport in two places, and both refusals govern the *default-built* backend.
`Judge` names the injected backend as the seam for callers that wire their own transport, and
makes transport independence the caller's responsibility there.
`harness/commands/_subscription_judge.py` is that caller, and its docstring states the trade.
**Model independence survives** — `JudgeConfig` still refuses every model in `drafter_models()`,
so the assessor can never be the `claude-opus-4-8` that wrote these sections. **Context
independence survives, and the blind lane rests on it** — the transport is called with
`tools=None`, so the assessor has no `Read` and no `Glob` and cannot open the drafting context,
the assembled draft or the phase outputs. **Transport, vendor and family independence do not
survive.** A same-family assessor shares the drafter's priors and is a weaker check on phrasing
than a different-family one. The pin is where that is declared:
`claude-sonnet-5@claude-cli-subscription@2026-10-02`.

The outstanding command is now:

```
py -3.10 -m harness.commands.blind_assessment assess --document DEMO-BIODIV-2027_part_b \
  --profile harness/profiles/ria_default.json --intake demo-biodiv-2027-part-b-v1 \
  --transport claude-cli --assessor-model claude-sonnet-5 \
  --assessor-version claude-cli-subscription@2026-10-02
```

The two pin flags are not optional. `.env.harness` is loaded with `override=True` and still
holds the Groq pin, so an exported variable loses to the file and the CLI would be asked for
`llama-3.3-70b-versatile`. The file itself was not edited: it keeps its key and its pin, and the
E5f lane that shares it is untouched. The alternative also stays open — rotate the Groq key and
drop the four flags to run the same assessment over the independent transport.

**A third finding, and the largest, found by rehearsing that lane end to end.** F9: one
provider's free-tier rate limit was deciding how much of the Part B the assessor may read.
`MAX_PACK_TOKEN_BUDGET` was `GROQ_TPM_LIMIT - 2048 - 900 = 3052`, and the pack builder refused
anything larger. Over the six candidate packs that cap drops **111 of 266 relevant items** and
truncates every cell; the implementation workplan cell loses 32 of its 53. The rubric system
prompt then tells the assessor that a truncated pack means "you must not return `passed: true`".
Every grade was therefore predetermined before a model read anything, and the report would have
measured the rate limit rather than the proposal. The ceiling is now a parameter the transport
declares. It still defaults to the old value, so the Groq lane is unchanged and a test pins that
it still refuses an oversized budget. All six packs complete at 10501, bisected rather than
estimated; the uncapped default is 32768. Lifting the ceiling does not lift the floor: a budget
that is still too small reports `insufficient_context` exactly as before.

F10: the 401 printed a traceback rather than failing closed, because no transport error sat in
the command's fail-closed set. Fixed — both transports now print one line and exit 2. F11: three
real-data probes in `tests/harness/test_evidence_pack.py` fail on this branch and failed before
this act, because they read the RIA sections with the MSCA-PF anchor spelling `1.1`. Recorded so
they are not read as a regression from it, and offered as a Milestone 2 candidate.

**Closed 2 October 2026: four of four.** The operator ran the subscription command and the
assessor graded all six cells. `harness/blind_reports/blind_e518c50023ee_0001.json` carries the
candidate hash, the profile version and the pin
`claude-sonnet-5@claude-cli-subscription@2026-10-02`, labelled scope `complete`, with
`partial_coverage` empty and no missing section. The three bindings repeat on every cell, so no
cell can be read apart from the candidate and the assessor that produced it. The provenance log
holds 18 entries, six cells at n=3. Criterion 3 is met and the ticket closes.

The F9 fix held in the live run. All six packs report status `complete` at budget 32768, between
2430 and 6565 tokens, so the ceiling that would have truncated five of the six and forbidden
every pass is gone. The grades discriminate rather than flatten: impact passes both cells at
0.780 and 0.797, excellence fails at 0.350 and 0.547, implementation fails at 0.323 and 0.283.
Two clean passes of six. The report is advisory and never run-blocking.

**F12, and the lane earned its keep.** Four of the six cells fail for one systematic reason, and
the assessor named it in all six without being asked: every claim-ledger entry it was shown
carries an empty `source_ref`. That is true, and it was checked rather than taken on the
assessor's word. All 147 claims in the candidate are blank, including the 90 declared
`confirmed`; all 180 entries in the three Tier 5 sections carry a real source. The break is a
seam between two components that are each correct alone.
`tools/build_part_b_candidate.py::_claims` maps `claim_id`, `status` and `claim_summary` onto the
graph's claim shape and never carries `source_ref`, and its docstring explains, rightly, that it
leaves `verified_span` absent because inventing offsets would defeat the claim verifier.
`materialise_candidate` then derives `source_ref` from `verified_span["id"]` alone — the one
field the converter deliberately never writes — so it resolves to the empty string. The harness
is faithful throughout: the pack renders `source_ref=` verbatim and the assessor judged what it
was shown. Under §12.2 a `confirmed` claim is one directly evidenced by a named source, and in
the candidate the name is gone, so the candidate understates its own traceability. Open, and a
Milestone 2 candidate. **No deterministic gate caught this, because every component passed its
own contract. The blind assessor is the only thing on this branch that has found it.**

F13 is recorded so the scores are not misread. The two implementation cells score lowest because
the person-months read TBD, the resources defer to a future lump-sum response, and all twelve
partner participations are assumed. That is the demo's all-Assumed Tier 3 being priced honestly,
and the sections concede it in the prose the assessor quotes back. Not a defect.

**Two findings, both from converting a real Part B rather than a fixture.** F7: the builder had
no mapping for an `assumed` claim and refused the Part B outright. The graph has no
`evidence_strength` that yields Assumed, because Assumed is declared rather than evidenced, and
the importer admits exactly one override for it. Carrying such a claim on strength alone would
have landed 85 of the demo's 180 claims as Unresolved and discarded the operator declaration.
F8: a Tier 5 `claim_id` is a declaration key, not an occurrence id — all three sections assert
`project_duration`, and the assembler concatenates the per-sub-section ledgers without
deduplicating, so one declaration arrives up to six times with an identical status and summary.
The builder now scopes each claim id to its section, collapses an exact repeat and refuses a
repeat that disagrees. F8 also records that the demo dev-graph builder never prunes: 54 package
directories now hold 18 current packages, and the 1 October count of "36 evidence packages, 6 of
them blind" included a superseded snapshot's 18 and 3.

**F7: nothing converted a Phase 8 draft into a candidate, and it is now built.** Criterion 2
says the draft is "imported as candidate version 1". Phase 8 writes three section artifacts
under `proposal_sections/`; the document route imports a candidate carrying `document_id`,
`sections`, `claims` and `commitments`. Nothing joined the two. `import_document` is called from
exactly two places in the tree, the revisions module and the tests, and every test hand-writes
its candidate. Both halves were well tested and neither asked where a real candidate comes
from.

This blocks criteria 2 and 4, not criterion 3. The spec review caught a first draft of this
entry overstating it. `load_candidate` resolves a section artifact by name inside a candidate
directory, and `proposal_sections/` already is such a directory. Criterion 3's three pinned
fields were therefore reachable through the **directory** route with no conversion. The ticket
asks for the blind pre-evaluation view, which is the document route, and this report already
recorded that the directory route carries no package and refuses to stamp an intake.

`tools/build_part_b_candidate.py` is that converter, with 42 tests and a decision record at
`decision_log/demo-part-b-candidate-builder_2026-10-01.json`. It is an operator tool, not a
skill and not a manifest-bound component, and it writes the candidate without importing it. The
anchor chain is what forced exact copying. Tier 2A declares the RIA sub-sections `B.1.1` to
`B.3.2`, and the drafting skills take `sub_section_id` from that registry. The RIA rubrics anchor
on six of those seven, so a converter that renumbered one would break grading silently.

**The end-to-end test nearly proved nothing.** The anchor map is read on the `assess_candidate`
path, not when the evidence pack is built, so a first draft that stopped at
`build_blind_evidence` passed with every anchor missing. It now runs the judge and asserts the
three pins criterion 3 names. Claims are carried from each section's own `validation_status`,
which gives the leakage guard real items and closes the claim half of F6. Commitments stay
empty. `milestone_refs` and `wp_table_refs` are id lists with no text, so a commitment built
from one would have invented content.

**Criterion 4 is checked over the wrong package, so its box stays open.** `assert_no_leakage`
ran over all 6 blind packages the demo world holds, rebuilt from their stored manifests, and
all 6 are clean. The package the criterion means is the one built around candidate version 1,
and that package does not exist. Worse, those 6 hold 0 passage, 0 claim and 0 commitment
items, which are the three types a historical-feedback tag rides on (F6). The clean pass is
correct and tells a reader nothing about a real Part B package.

**There is no candidate version 1, and the blind lane could not have graded one.** The first gap
is the human step the ticket always depended on. Until the operator runs the external planner,
§13.4 forbids drafting the Part B this ticket would import, by the runner or by hand. The second
gap is a defect, F1, and it would have failed the criterion with Part B in hand.

**F1: the document route cannot feed either shipped profile.** `materialise_candidate` writes
one sub-section per passage and names it for its section. The RIA rubrics anchor on `B.1.1` to
`B.3.2`, and the MSCA-PF rubrics on `1.1` to `3.2`. The anchor map then fails closed with an
`EvidencePackError`. The route's own tests use a synthetic profile whose anchors are its section
ids. The profile tests use the directory route with a candidate built from the anchors. No test
crossed the two, which is what handoff stage 7 was for.

A second finding rides on the first. An ESR intake can be stamped only through the document
route, so criteria 3 and 4 cannot share one report while F1 stands. The intake writer also
requires a `submission_id` and offers no way to declare that none exists. So the record carries
the sentinel `NOT_SUBMITTED` (F3). F1 was reproduced in a temporary graph root, never in
`docs/`, because a real import would move the pinned demo snapshot id. Six findings and eight
decisions are in `demo-candidate-blind-baseline_2026-10-01.json`, with 58 tests.

## Change scenarios and shadow comparison

**What to build:** A scripted set of approved changes, each run as a pair: the planner's advisory first, then a real rerun, then the shadow comparison (agreed, planner narrower, planner broader). The scenarios:

1. A task's lead moves between two partners (the T03 scenario at full scale).
2. An Assumed gap partner withdraws before confirmation.
3. An Assumed gap partner is confirmed, and its declaration leaves `working_assumptions.json`.
4. A claim loses its verified source span.
5. A Tier 2B fact changes, such as the date correction from the intake ticket or a topic text amendment when the call opens.
6. A deliverable's month moves across a milestone.

Each change runs under a revision contract. Scenarios that alter Tier 3 follow the operator manual's refinement route and never edit frozen founding documents in place. Where Phase 8 is available, each scenario ends with a new candidate version and a new blind report. The previous report is shown as not applicable.

**Blocked by:** First dev-graph snapshot on the demo world; Runner Phases 1 to 6 on the demo. Phase 8 steps are also blocked by Candidate Part B and the blind baseline.

- [ ] Each scenario has an advisory with non-empty reason paths, a rerun and a shadow comparison result. — advisory yes; rerun and comparison no (subtickets A and B)
- [x] Every planner-narrower result is investigated and recorded, because it is the unsafe direction. — vacuous, and F2 is why
- [x] No reuse metadata is written by the planner, and the scheduler's reuse decisions are identical with and without an advisory present.
- [x] Revision contracts reject a change that touches a protected objective, with the node named.
- [ ] The blind lane never includes a superseded candidate version. — needs a candidate version 2, which needs the rerun (subticket C)

**Two of five met, one met vacuously, two not met.** Seven scenarios are scripted: the six the
ticket names and one probe for criterion 4. They hold eleven arms. Eight recorded a change and
produced an advisory, and every entry in all eight carries a reason path. Each advisory was
compared against both runs this world holds, and all sixteen comparisons refused.

A refusal is not one of the three diagnostics criterion 1 names, so its comparison half is not met
either. The first draft of the Tier 4 record called it "met as a refusal", which the code review
caught. The refusals are a durable result and are recorded. They are not the criterion.

The decision record is `demo-change-scenarios_2026-10-02.json`: 15 decisions, 9 findings and 6
Milestone 2 candidates, with 111 tests across three files.

**The frozen world is never edited.** `record_change` writes the approved content to the record's
own Tier 3 path. A scenario run against `docs/` would therefore edit the founding documents in
place and move the pinned demo snapshot id. Each scenario instead copies the six files the snapshot
declares as its inputs into a sandbox. It then checks that the copy builds the live snapshot id
before any arm runs. All seven records carry `before_snapshot_id` equal to `sha256:706fe54f…`, and a run
leaves `docs/tier3_project_instantiation` byte for byte unchanged.

**The advisory discriminates, and that is the result worth having.** On `task_lead_moves` the three
Part B sections receive three different verdicts from one change. The excellence section is
`transitive` and so `reuse-under-policy`. Impact and implementation are `direct` and `rerun`.
On `gap_partner_withdraws` arm 3 all three turn `coverage_unknown`: the removed partner is still
in their declared inputs and no longer in the after snapshot. On `tier2b_fact_changes` all three
are `transitive`.

That is the handoff's "an unchanged check result can be retained only under an explicit valid
policy", working on real records.

**Three of the six scenarios are only expressible as a refusal, and that is the finding.** A
partner withdrawal cannot be one change. Removing P07 while the work plan still names it in
eleven task roles breaks the graph. The builder refuses at the first dangling edge, and
`record_change` restores the record byte for byte (F7).

Two other arms refuse because the change recorder covers five Tier 3 records. Neither of their
files is one of the five (F3): the declaration leaving `working_assumptions.json`, and the date
correction in `selected_call.json` that is the whole of scenario 5. Each is probed in its own arm
with the refusal kind declared up front. The record says the engine refused, not that nobody
tried.

**Scenario 4 found the structural planner-narrower case, which no per-run comparison can see.**
Dropping the span a claim would rest on moves the source's version but leaves its own content
equal. The cause is that `change_set` excludes a list of objects from a node's own content. The change is
classified `contained`, there is no origin, and the advisory reports `nothing_changed` for a change
that withdrew evidence (F5). The rule is right where the nested list is indexed as nodes, as a work
package's tasks are. It is wrong where the list is not indexed, and nothing distinguishes the two.

**Criterion 3 is proved dynamically, not argued.** No path in any node's `FINGERPRINT_INPUTS`
covers `change_scenarios/` or `run_records.json`, asserted directly. Running all seven scenarios
and writing their records leaves every eligible node's input fingerprint and its full
`ReuseDecision` byte-identical, for all three nodes, and writes no reuse metadata. The writer
carries no clock, so a rewrite changes no byte and the before-and-after comparison is like with
like.

**Criterion 2 is met vacuously, and the vacuity is untested machinery.** Half the sixteen refusals
come from F1, where the reader rejects the run id before the manifest is opened, and half from F2.
The comparison path was therefore never exercised end to end on a real run here. Nothing in this
world shows it would classify a genuine pair of verdicts correctly. `test_dev_graph_shadow.py`
covers that over a seeded synthetic manifest. The demo adds nothing to it.

A `planner_narrower` row needs a scheduler verdict of `rerun`, which comes only from a decision
whose status is `not_reused`. The
scheduler records both outcomes in `self._reuse_decisions`, which reaches `run_summary.json`. It
calls `ctx.record_reuse_decision` only inside the reused branch. So a `not_reused` decision never
reaches the run manifest the comparison reads (F2), and the comparison is blind to the one
direction the ticket calls unsafe. `run_summary.json` is also rewritten by every dispatch. The demo
dispatched one node at a time ending on `n08f`, so the n08a-n08c decisions were produced and then
overwritten.

Three reasons not to fix it here, on operator instruction. It changes runtime persistence. Two
existing tests assert `get_reuse_decision` returns `None` on that path. And it would not help runs
that have already happened. It is Milestone 2 candidate M1.

**The second refusal cause is the run id.** The only run that carried Phase 8 is stored under
`import uuid; print(uuid.uuid4())` — a mis-pasted shell command. Nothing validates a run id at
dispatch, and `read_reuse_decisions` requires a plain identifier. That run can therefore never be
named to a comparison (F1). `tools/preserve_run_manifests.py` already slugifies the id for its own
file name. The defect is upstream.

**`run_records.json` did not exist, and the planner refuses without it.** The schema specification
places that file by hand. `tools/derive_dev_graph_run_records.py` derives it instead, under two
declared rules. An artifact's inputs are the snapshot node ids its own text names, matched on a word
boundary so `D3.2` is never found inside `D3.21`. A check's inputs are `null`, because no gate
result in this repository names a graph node. That premise is checked by test, not assumed. The
result is seventeen records: three artifacts declaring 3, 30 and 92 node ids, and fourteen checks.

Two consequences are recorded
rather than smoothed. No section cites a source id, so fifteen of the twenty-four sources come back
flagged newly relevant on most scenarios (F4). That is the same root as the earlier ticket's F12.
And a record with `null` inputs yields an entry on every plan, so `claim_loses_its_span` reports
`nothing_changed` with fourteen entries (F8). Measured across the eight advisories: 112 of the 150
entries are those checks, and the substantive remainder is 38.

**No advisory in this world names a proposal passage.** The candidate's three passages carry an
empty `addresses` list, and none of its 147 claims carries a verified span. The document is
therefore joined to the project graph by no edge the planner can walk (F6). The handoff asks the planner to find
affected proposal passages. For this candidate it cannot, and the artifact half of every plan comes
entirely from the derived run records.

**The refinement route is not exercised, and scenario 5 has no representable form.** The ticket
asks that scenarios altering Tier 3 follow the operator manual's §5 route and never edit frozen
founding documents in place. No scenario alters Tier 3 at all: every arm runs in a sandbox, which
satisfies the second clause by never engaging the first. The route ends in a re-gate, which is the
dispatch the rerun half is blocked on.

Scenario 5 is the other gap. Its date correction and its topic amendment both land in
`selected_call.json` or Tier 2B, and F3 covers neither, so the refusal is the whole of what the
recorder can say. The second arm is a labelled proxy on the project's own confidence in the page,
not a Tier 2B change (F9).

**One verdict was left inconvenient on purpose.** `task_lead_moves` is `flagged_for_review`, not
`accepted`. The handoff asks that unresolved participant capacity stay explicit, and that item
names no node, so it bears on every change under its contract. Narrowing the item to nodes the
change misses would have bought an `accepted` verdict by choosing the convenient reading.
`deliverable_month_moves` carries no such item and is the accepted case.

### Subtickets: what closes the open boxes

The parent ticket stopped at two of five. Each open half is listed below as its own subticket,
with the finding that blocks it and the component it may touch. Subtickets A, D and E are engine
work. Subtickets B and C are operator acts that spend quota. F4, F5, F6, F7 and F8 stay
Milestone 2 candidates M4, M5 and M6 and are not subtickets of this demo.

#### A. Name the Phase 8 run to the comparison

**What to build:** Two things that together let a comparison name the only run that carried Phase
8. First, the CLI entry point rejects a `--run-id` that `read_reuse_decisions` would refuse, with
the same identifier rule, so a mis-pasted argument fails at dispatch and never becomes a run
directory. The DAG scheduler is not touched. Second, the comparison reader accepts the preserved
manifest that `tools/preserve_run_manifests.py` writes under its slug, with the true run id
recorded inside, so the existing run `import uuid; print(uuid.uuid4())` can be named without
renaming its directory. The eight advisories are then compared again against that run and the
diagnostics recorded in the scenario records.

**Blocked by:** nothing. Milestone 2 candidate M2, from F1.

- [ ] A run id that is not a plain identifier fails at the entry point, with the rule named.
- [ ] The comparison reads the preserved manifest by slug and reports the true run id.
- [ ] The eight advisories compared against the Phase 8 run return a diagnostic or a refusal whose kind is not `malformed_request`.

#### B. Enact one scenario through the refinement route and rerun

**What to build:** One scenario leaves the sandbox. `deliverable_month_moves` is the candidate:
its contract verdict is `accepted` and it touches one record. The change is recorded against
`docs/` through the operator manual's refine cycle (Part IV, §5.1), so the Tier 3 record gains a
new version and the founding document is not edited in place. The snapshot id moves, and the new
id is pinned in the scenario record as `after_snapshot_id`. The operator then dispatches the Phase
8 nodes the advisory marked `rerun` under a plain run id, and the comparison runs against that
run. The result is one of the three diagnostics, recorded next to the advisory.

**Blocked by:** Subticket A. Dispatch is an operator act (quota).

- [ ] The Tier 3 record carries a new version and the prior version is intact.
- [ ] The scenario record names the before and after snapshot ids.
- [ ] The rerun is dispatched under a plain run id and its manifest holds reuse decisions.
- [ ] The comparison for the enacted scenario reports `agreed`, `planner_narrower` or `planner_broader`.
- [ ] A `planner_narrower` result, if any, is investigated and the reason recorded.

#### C. Candidate version 2 and the superseded blind lane

**What to build:** After the rerun, the candidate builder produces a Part B version 2 from the
rerun's sections. `import_document` imports it with a `supersedes` reference to version 1. The
blind lane runs on version 2 only and its report marks the version 1 report as not applicable.

**Blocked by:** Subticket B.

- [ ] Version 2 is imported with a `supersedes` edge to version 1.
- [ ] The blind lane's package set contains no passage from version 1.
- [ ] The version 2 blind report names the version 1 report as not applicable.
- [ ] The leakage scan passes over the new version.

#### D. Persist the `not_reused` decision to the run manifest

**What to build:** The scheduler calls `ctx.record_reuse_decision` only on the reuse branch, so a
`not_reused` decision reaches `run_summary.json` and nothing durable. The fix records both
outcomes to the manifest and gives the per-dispatch decisions a home that a later dispatch does
not overwrite. Two tests assert that `get_reuse_decision` returns `None` on the not-reused path;
they change with it. This makes `planner_narrower` detectable and takes the vacuity out of
criterion 2.

**Blocked by:** explicit operator instruction. It changes runtime persistence, which the demo's
constraints exclude, and it was deferred on operator instruction in the parent ticket. Milestone 2
candidate M1, from F2.

- [ ] A `not_reused` decision is readable from the run manifest after the dispatch ends.
- [ ] A later dispatch in the same run does not overwrite an earlier node's decision.
- [ ] The two tests that pinned `None` are re-pointed, not deleted.
- [ ] A seeded `planner_narrower` pair is classified as such by the comparison.

#### E. Make scenario 5 and the ledger declaration recordable

**What to build:** The change recorder covers five Tier 3 records. Scenario 5 lands in
`selected_call.json` or Tier 2B, and scenario 3's second half lands in `working_assumptions.json`.
The recorder is widened to those two Tier 3 files, with a declared rule for what a change to a
ledger declaration means for the §12.2 status the deliverables quote. The two refusal-probe arms
(`tier2b_fact_changes/a1`, `gap_partner_confirmed/a2`) become change arms and are rerun through
the advisory. A Tier 2B text amendment stays out of scope until Tier 2B is a snapshot input.

**Blocked by:** nothing. Milestone 2 candidate M3, from F3 and F9. The operator decides whether it
lands in the demo or waits for Milestone 2.

- [ ] A date correction in `selected_call.json` is recorded, planned and compared.
- [ ] A declaration leaving `working_assumptions.json` is recorded, planned and compared.
- [ ] The rule for a status change caused by a ledger declaration is written down and tested.
- [ ] The F9 proxy arm is retired or relabelled as what it is.

## Demo report

**What to build:** A report under `plans/` that answers the questions fixed in the scope record, with numbers: snapshot size and build time, packages that went incomplete and why, planner agreement per scenario, fail-closed errors found on real records, run cost, and the defects that need Milestone 2 tickets. It ends with the evidence for and against enabling fine-grained reuse.

**Blocked by:** Change scenarios and shadow comparison. Subtickets B and C may stay open; the report then records them as pending.

- [ ] Every scope question has an answer backed by a Tier 4 artifact.
- [ ] Defects found are listed as candidate Milestone 2 tickets.
- [ ] The leakage test passes on the whole branch.
