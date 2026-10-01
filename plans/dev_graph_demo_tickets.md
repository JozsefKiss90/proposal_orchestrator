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

**Nothing in the repository validated a budget request or a budget response.** `g08_p04` read the
interface contract as a JSON Schema. That document has no JSON-Schema keyword at its root, so the
predicate accepted every payload. Ten findings and nine decisions, three of them from the code review,
are in `demo-budget-request-phase7_2026-10-01.json`.

## RIA pre-evaluation profile in the harness

**What to build:** A versioned pre-evaluation profile for RIA, built with the Milestone 1 profile mechanism from the Tier 2A RIA evaluation form: criteria (Excellence, Impact, Quality and efficiency of the implementation), scale, weights, thresholds and the criteria-to-sub-section mapping. No harness Python changes are needed. If one is, that is a Milestone 1 defect to record.

**Blocked by:** Tier 1 and Tier 2A coverage check for an RIA.

- [ ] The profile loads, has its own version, and every field traces to the evaluation form or the General Annexes award criteria.
- [ ] The existing MSCA-default profile tests still pass.
- [ ] A dry run on a synthetic RIA-shaped candidate produces a report with the RIA criteria.

## Candidate Part B and the blind baseline

**What to build:** Phase 8 drafts Part B for the demo and the draft is imported as candidate version 1. The ESR intake record is written with availability not applicable (never submitted). The blind assessment runs on version 1 under the RIA profile through the blind pre-evaluation view.

**Blocked by:** Budget request and the Phase 7 gate; RIA pre-evaluation profile in the harness.

- [ ] Phase 8 reaches released, or its blocking gate is recorded.
- [ ] Candidate version 1 is a document snapshot with state imported, with passages linked by span.
- [ ] The blind report carries the candidate hash, profile version and assessor pin, and is labelled complete or partial.
- [ ] The leakage guard confirms no historical-feedback item entered the package.

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

- [ ] Each scenario has an advisory with non-empty reason paths, a rerun and a shadow comparison result.
- [ ] Every planner-narrower result is investigated and recorded, because it is the unsafe direction.
- [ ] No reuse metadata is written by the planner, and the scheduler's reuse decisions are identical with and without an advisory present.
- [ ] Revision contracts reject a change that touches a protected objective, with the node named.
- [ ] The blind lane never includes a superseded candidate version.

## Demo report

**What to build:** A report under `plans/` that answers the questions fixed in the scope record, with numbers: snapshot size and build time, packages that went incomplete and why, planner agreement per scenario, fail-closed errors found on real records, run cost, and the defects that need Milestone 2 tickets. It ends with the evidence for and against enabling fine-grained reuse.

**Blocked by:** Change scenarios and shadow comparison.

- [ ] Every scope question has an answer backed by a Tier 4 artifact.
- [ ] Defects found are listed as candidate Milestone 2 tickets.
- [ ] The leakage test passes on the whole branch.
