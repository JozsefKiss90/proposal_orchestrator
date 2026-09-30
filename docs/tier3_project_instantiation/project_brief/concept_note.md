# Concept note

**Topic:** HORIZON-CL6-2027-01-BIODIV-01, Integrating Remote Sensing and in-situ observations of
Biodiversity, towards a fully interoperable observation and data framework.
**Instrument:** RIA, lump sum. **Call deadline:** 22 September 2027.

**Status: approved and frozen, 30 September 2026.** The operator approved the concept, chose gap
option 1 (all twelve partners) and set the duration at 48 months. No acronym is coined. The record is
`docs/tier4_orchestration_state/decision_log/demo-concept_2026-09-30.json`, which also carries this
file's fingerprint. The operator manual's freeze rule now applies: this note is immutable for the run,
and refinement happens through the graph rather than by re-editing it. The decisions and the options
put to the operator stay below, because a decision without its rejected alternatives cannot be
reviewed.

**Reading convention.** Every phrase in double quotes is a verbatim slice of the Tier 2B call extract
at `docs/tier2b_topic_and_call_sources/call_extracts/HORIZON-CL6-2027-01-BIODIV-01.json`. Partners are
pseudonyms, `P01` to `P12`, and their capabilities live in
`docs/tier3_project_instantiation/consortium/partners.json`. The claim table in `project_summary.json`
carries the span reference behind each phrase. `tests/test_demo_concept.py` checks both.

---

## The gap the topic names

Biodiversity data exists in large quantities and integrates badly. The topic says why. Many in-situ
collections "were not designed with Satellite Remote Sensing integration in mind" and "lack the
structure, interface and metadata required to support advanced analytics, including AI".

The consequence is practical. An assessment that needs molecular, plot, airborne and satellite evidence
together has to reconcile four measurement cultures first. That reconciliation is done once per project
and thrown away. The topic asks for it to be done once and kept.

## What this project does

The project builds one observation chain and runs it along one pressure gradient. The chain carries
measurement from molecules to satellites. The gradient runs from farmland, through the freshwater
ecotones that receive its runoff, to the coastal waters downstream.

Anchoring on farmland and grassland is a deliberate choice. The topic names agriculture twice: as a
pressure on ecosystems, and as a sector where "biodiversity preservation is a mainstream feature of
other sectors, such as agriculture". `P01`, `P02`, `P03`, `P05` and `P06` carry a deep agricultural
measurement base into the project. The gradient then supplies the three ecosystem realms without
inventing three unconnected sites.

## The chain, from genome to space

Five layers, each held by a named partner.

| Layer | Partner | What it contributes |
|---|---|---|
| Molecular | `P01`, `P09` | Stress metabolomics, and the genomic, transcriptomic and environmental DNA layers the second expected outcome names as "omics-based data (genomic, transcriptomic, metabolomic)" |
| Plot | `P01`, `P03`, `P06`, `P07`, `P08` | In-situ measurement in farmland, grassland, freshwater ecotones and coastal habitats |
| Airborne | `P02` | Field spectroscopy and uncrewed aerial survey, which bridge plot and satellite scales |
| Satellite | `P02`, `P12` | European radar and optical missions, as the eligibility condition on "Copernicus and/or Galileo/EGNOS" requires |
| Integration | `P04`, `P09`, `P10`, `P12` | Harmonisation workflows, provenance, standard crosswalks and the classification models |

`P10` owns interoperability. Every habitat label the project publishes carries a crosswalk to the
"Global Ecosystem Typology as well as EUNIS". That crosswalk is what makes the outputs usable outside
the project, and it is the interface an optional Joint Research Centre contribution would attach to.

## Three demonstration cases on one gradient

The second scope requirement asks for capabilities "across terrestrial, freshwater and marine
ecosystems". One gradient answers all three.

| Case | Lead | Habitats | Pressure studied |
|---|---|---|---|
| Terrestrial | `P03` | Arable land, grassland and field margins | Cultivation intensity, nutrient and water management |
| Freshwater | `P07` | Rivers, floodplains and riparian ecotones next to farmland | Runoff and nutrient load from the terrestrial case |
| Marine | `P08` | Coastal and benthic habitats in transitional waters | The same load, arriving at the coast |

`P11` analyses the pressures as "socio-economic pressures and activities impacting ecosystems", so case
selection rests on evidence rather than on data availability. Cases target habitats the topic marks as
"under pressure or as restoration priorities".

The three cases share one pressure and one measurement protocol. A harmonisation decision taken for
farmland is therefore tested twice more, in realms that did not design it. That is the test the topic's
integration claim needs, and three unconnected sites would not provide it.

## Training and validation data

The third expected outcome asks for in-situ data usable as "training and validation resources". `P03`
holds a multi-season field archive of physiological, spectral, soil-water and weather measurements.
The project reworks it into documented training and validation sets.

`P01` sets the split protocol. Site, season and treatment travel together into one fold, so a model
cannot learn a site and score as though it had learned the biology. `P12` then trains the habitat and
ecosystem classification and scales it to European coverage.

## Reaching agriculture

Biodiversity indicators that stay in a research portal change no farming decision. `P04` engineers the
decision-support surface. `P05` carries the indicators into farm-management tools through a
multi-country user network of agricultural holdings, and evaluates whether practitioners can act on
them. `P06` tests whether the measurement protocols transfer to a second production context.

## Coordination the topic requires

The topic sets five coordination duties. The project accepts each one and names the partner that holds
it.

| Duty | Held by |
|---|---|
| Earmark resources for cooperation with "GBIF, OBIS, LUCAS" | `P10`, `P08` |
| Ingest Commission-steered monitoring data: "LUCAS, specifically LUCAS grassland, and EMBAL" | `P03`, `P10` |
| Leave a place for the Joint Research Centre, as a "beneficiary with zero funding, or as an associated partner" | `P10` |
| Link outputs to the "European Open Science Cloud (EOSC) and the European Common Data Spaces" | `P10`, `P04` |
| Coordinate with the space-agency projects of the "FuturEO programme" | `P02`, `P12` |

The Joint Research Centre place is held open and counted towards nothing. It takes no part in preparing
the proposal, so the consortium cannot rely on it for any eligibility condition.

---

## Decisions the operator owns

### Decision 1 — how the capability gaps are closed

**Decided: option 1, all twelve partners.**

The derived six cover farmland well. Measured against the topic they have no freshwater or marine
expertise, no genomics beyond metabolomics, no biodiversity data infrastructure, no socio-ecological
analysis and no European-scale AI. They also span two country slots, and the Tier 1 composition
condition needs three.

| Option | What it does | What it costs |
|---|---|---|
| **1. Add the gap partners** (recommended) | All twelve partners. Every requirement class in the gap analysis gains a covering partner, and the consortium reaches six country slots | Half the consortium is fictional and Assumed. The composition condition is met only under assumption, because every partner adding a third country is invented |
| **2. Narrow to terrestrial** | The derived six only. No invented entity enters Tier 3 | The second scope requirement is unanswered, and the composition condition fails outright. Phase 2 would have to record an unresolved scope conflict, which its gate forbids |
| **3. Mixed** | Add `P07`, `P08` and `P09`. Three realms, omics, five country slots | Four cross-cutting duties lose their holder: framework cooperation, typology crosswalks, the open science cloud link and policy-reporting alignment |

Option 1 is recommended because the scope requirement is not severable. It asks for capabilities across
all three realms, and option 2 drops two of them.

### Decision 2 — project duration

Tier 2B sets no duration for this topic. Pages 73 to 76 carry no duration condition and the portal
record carries none, so the choice is the operator's and will be recorded as Assumed.

**Decided: 48 months.** The terrestrial case needs the archive reworked and two further
seasons measured under the harmonised protocol. The freshwater and marine cases start only once that
protocol exists, and each needs a full annual cycle. European scaling and validation need a year after
that. At 36 months the cross-realm cycle collapses to one season. At 60 months the same EUR 5,000,000
covers a longer burn.

### Decision 3 — approve, approve with changes, or reject

**Decided: approved.** The source materials ticket and the architecture seeds ticket are unblocked.

The duration decision was written to `selected_call.json` as `project_duration_months`, because that is
where `runner/dependency_normalizer.py` and the timeline predicates read it. It carries Assumed there,
so no reader mistakes an operator choice for a call constraint.

---

## What this draft does not claim

Four things, stated rather than buried.

1. **No partner participation is confirmed.** All twelve carry Assumed and are declared in
   `working_assumptions.json`. The derived capabilities trace to a document held outside this
   repository, so no reader of this branch can check the trace.
2. **Each of the freshwater and marine realms rests on one partner.** Losing `P07` or `P08` leaves the
   second scope requirement unanswered, even though the composition condition survives. Finding F4 of
   the consortium gap analysis.
3. **The geography is thin.** Ten of twelve partners sit in three country slots, five of them in `C1`.
   The scope asks for use cases in "Member States and Associated Countries". Finding F5.
4. **No methodology vault backs this note.** The operator manual expects the concept to be lifted from
   an authored methodology graph. Instance two has none yet, so the mechanisms here are design intent
   at Assumed, not `source_grounded` claims.

## Traceability

`project_summary.json` carries 23 concept claims. Each names the call phrase it answers, the span that
phrase sits in, and the exact partner capability that carries it. Between them the claims reach every
expected outcome, every scope requirement, all three realms and all nine cross-cutting requirements the
call extract records.

No source literature is cited yet. The source materials ticket is blocked on this approval, so every
claim here is design intent rather than evidence.
