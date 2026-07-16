# CONTEXT

Domain context and ubiquitous language for this project. Skills (`/domain-modeling`, `/diagnosing-bugs`, `/tdd`, `/improve-codebase-architecture`) read this before exploring, and should use the terms defined here rather than drifting to synonyms.

## What this project is

An **MSCA-style research proposal** on **crop water-stress monitoring and irrigation decision support**. The deliverable is the proposal (and a standalone research demonstrator / MVP), not a production product.

This repo is not source code — it is an **Obsidian LLM-wiki**: a structured, interlinked markdown knowledge graph (`methodology_graph/`) that compiles the proposal's methodology from a small set of immutable sources (`sources/`, mirrored as `01_sources/`). The LLM maintains the wiki; the human curates sources and asks questions. See `llm_wiki.md` for the governing method.

## The methodology in one line

> Satellite + soil sensors + weather + field observations → probabilistic field-state diagnosis → uncertainty-aware AquaCrop calibration → counterfactual irrigation simulations → profit/risk-based recommendation.

The problem decomposes into **two branches** joined by **one uncertainty chain**:

- **Diagnostic branch** — *what is the actual state of the field, plant, soil, and water now?* Estimates the **latent field state** — its committed target is two variables, **root-zone soil water** and **canopy cover** (ADR-0002; crop water stress is a *derived* AquaCrop output, not part of the estimated state) — from multiple uncertain streams.
- **Prognostic branch** — *given that state, what happens under each irrigation decision, so the best can be chosen?* Runs counterfactuals and selects the best expected economic outcome.

**Two routes, one shared decision engine** — with **asymmetric commitment**: Route A is the built/validated primary (the headline contribution); Route B is implemented in scoped form as a *result-generating* comparison, not just a fallback (ADR-0005). The diagnostic branch can be realised by either of two interchangeable routes; **from the diagnosed state onward the path is the same for both**:

- **Route A — Direct Probabilistic Fusion** — the rigorous one-step route: feed satellite as one more input into a probabilistic ML model (Bayesian hierarchical model / Gaussian process) that goes straight to field state with uncertainty, avoiding the two-step downscaling critique of the sub-pixel problem.
- **Route B — Homogeneous Patch Proxy** — the lighter route that sidesteps the resolution problem by reading a nearby homogeneous covarying patch the coarse pixel can read cleanly. It splits into a **software half** (find & read a *naturally-occurring* covarying patch — in scope, drives the A-vs-B comparison) and a **physical half**, the **Control Stand Variant** (deliberately plant a covarying proxy stand — a conditional stretch pending a field site). See ADR-0005.

Both feed the **AquaCrop Decision Interface**, which "stands for the plant," running counterfactual irrigation scenarios over weather ensembles toward the best **expected profit**.

## The red thread: uncertainty

The defining commitment: the two branches are tied by **one chain that carries uncertainty from end to end** — "keeping that uncertainty honest is the heart of the whole thing." Every model output must report not just the state but how sure it is, and that uncertainty must travel into the irrigation decision (**uncertainty propagation**).

## Novelty claim

Multimodal data fusion is mature, but **probabilistic, row-crop drought/irrigation decision frameworks remain underdeveloped**. Short form: *"From multi-sensor observation to probabilistic diagnosis to economically optimized irrigation decision."* The headline is deliberately **sensor-agnostic** (S1+S2 backbone); the PlanetScope-fusion GAP is claimed only *conditionally*, if research access lands (ADR-0004).

## Glossary (ubiquitous language)

Use these terms exactly. Canonical definitions and full pages live in `methodology_graph/09_terminology/` (and `Sub Pixel Problem` in `04_methodological_routes/`).

| Term | Meaning |
|---|---|
| **Crop water stress** | The plant condition when water supply is insufficient for demand — the central *concern*, but a **derived AquaCrop output**, not a directly-estimated state. The estimated latent state is root-zone soil water + canopy cover. |
| **Lead crop** | Processing tomato — the one crop AquaCrop is calibrated to and the pilot runs on. The method is *framed* as transferable to horticultural row crops, but only tomato is a calibration/validation commitment. See ADR-0001. |
| **Latent field state** | The real-but-unobserved *condition* of the crop/soil system that the model infers (the territory). The committed **diagnostic target** is two state variables: **root-zone soil water** and **canopy cover** (ADR-0002). Distinct from the latent-state interface, which is the model's *estimate* of it. |
| **Latent-state interface** | The calibrated *posterior* over {root-zone soil water, canopy cover} that **both** routes must emit — the interchangeable contract feeding the one shared decision engine, the A-vs-B plug-in point, and the input to the AquaCrop Decision Interface (ADR-0002, ADR-0005). The deliverable *estimate* of the latent field state. Aliases: shared latent-state posterior/seam. |
| **Data fusion** | Combining different data sources into one model rather than analysing each in isolation. |
| **Multimodal fusion** | Fusion across distinct sensing modalities (radar, optical, soil, weather). |
| **Uncertainty propagation** | Carrying uncertainty from inputs through every model step into the final decision — the "red thread." |
| **AquaCrop** | The FAO crop-growth model simulating yield response to water; used as the decision interface that "stands for the plant." Plays **two roles kept as distinct artifacts** — see the next two entries. |
| **AquaCrop Decision Interface** | AquaCrop in its *prognostic/decision* role: consumes the latent-state posterior, runs counterfactual simulations over the weather ensemble, and emits uncertain stress/yield/profit to be scored by the objective. The plug-in point shared by both routes. |
| **AquaCrop scoring model** | AquaCrop in its *outcome-scoring* role: the ruler that scores realised outcomes in the validated hindcast, validated against observed yield/Brix and kept a **distinct artifact** from the decision model. This separation (plus real-time information asymmetry) is what makes the hindcast non-circular (ADR-0009). Aliases: outcome model. *Avoid* conflating with the AquaCrop Decision Interface. |
| **Counterfactual simulation** | A "what would happen if…" run — how the system responds under a decision not (yet) taken. |
| **Weather ensemble** | Multiple plausible future weather paths used to evaluate a decision under uncertainty, not a single forecast. |
| **Expected profit** | Average net economic value of a decision across uncertain futures — crop value minus costs. |
| **Expected utility** | The **operative objective**: *risk-adjusted expected profit* (a concave utility of net profit / mean−λ·risk). The curvature (λ) is **not** a free knob — it is elicited from the tomato **contract economics**. See ADR-0003. |
| **Decision regret** | How much worse a chosen decision was than the best possible, judged after the fact. |
| **Contract-penalty asymmetry** | The asymmetric payoff of processing-tomato delivery contracts — shortfalls below contracted tonnage/quality are penalised more than good years reward. The substantive source of the decision-maker's (rational) loss-aversion, hence the objective's risk-adjustment. See ADR-0003. |
| **Decision-level (economic) calibration** | The **primary** evaluation of the red thread: does propagated uncertainty *improve decisions* — measured by decision regret and a cost–loss / value-of-information check (probabilistic vs point estimate) — not merely calibrate the state estimate. See ADR-0007. |
| **Current-practice baseline** | What growers actually do now (calendar / soil-feel / standard scheduling). The impact-relevant benchmark the method must beat; shared by RQ5 (evaluation) and RQ7 (pilot success). See ADR-0007. |
| **Pre-committed metric hierarchy** | Evaluation ranking fixed *before* seeing results to avoid metric-shopping: decision-level economic calibration **rules** (primary); per-operator calibration **localises** (secondary/diagnostic). See ADR-0007. |
| **Incremental information** | The sharp covariation test for Route B: the proxy patch must reduce the target's predictive uncertainty *beyond* the model's existing inputs (S1/S2, weather, soil) — not merely correlate. If existing inputs already explain the covariation, the patch adds nothing. See ADR-0008. |
| **Publishable null** | A pre-committed stance: a negative covariation / decision-parity result is a reportable, publishable outcome — not buried. Makes Route B's test genuinely falsifiable and guards against publication bias. See ADR-0008. |
| **Validated hindcast counterfactual** | The **primary** pilot-efficacy method: replay historical seasons, scoring the method vs current practice on risk-adjusted profit/regret. Non-circular because the AquaCrop *scoring* model is validated against observed yield/Brix and decisions respect real-time information asymmetry. See ADR-0009. |
| **Real-time information asymmetry** | The fairness constraint that makes the hindcast non-circular: both method and baseline decide using only information available *at decision time*, but are scored on *realised* outcomes — so the edge comes from better information use, not hindsight. See ADR-0009. |
| **User-acceptance endpoint** | A light usability / trust / actionability assessment with pilot users — a pilot-success item that also feeds the TRL judgement (RQ10). See ADR-0009. |
| **Sub-pixel problem** | Coarse satellite pixels mix multiple surfaces, so a field's signal is not cleanly readable — the resolution problem both routes confront. |
| **Natural patch proxy** | The *software/analytical half* of Route B (in scope): use existing high-resolution soil/climate data to find a *naturally-occurring* homogeneous covarying patch the coarse pixel reads cleanly, then infer the target crop's state. The half that actually drives the A-vs-B comparison. Its claim is reported *separately* from the Control Stand Variant's, never pooled (ADR-0005, ADR-0008). |
| **Control Stand Variant** | The *physical half* of Route B: a deliberately planted covarying species acting as a designed proxy sensor, so patch covariation is *measured*, not assumed. Conditional stretch, pending a secured field site (ADR-0005). |
| **Downscaling** | Inferring fine-resolution state from coarse pixels; the two-step approach Route A's critique avoids. |
| **Cokriging** | Geostatistical interpolation using correlated auxiliary variables, carrying its own uncertainty. |
| **Gaussian process / Bayesian hierarchical model** | The probabilistic ML model families behind Route A (aliases: GP, BHM). |
| **Root-zone soil water** | Latent target variable: water in the crop's root zone. *Not* observed directly — inferred from surface soil moisture through a temporal water balance (AquaCrop's balance, or an exponential-filter / Soil Water Index step), carrying that inference's uncertainty. |
| **Surface soil moisture** | What Sentinel-1 SAR actually observes — moisture in roughly the top ~5 cm. An *observation*, not the latent root-zone state; the two must never be conflated. |
| **Canopy cover (CC)** | AquaCrop's canopy state variable. Sentinel-2 optical indices (NDVI/NDWI/NDMI) track it through an **observation operator** (a conversion with its own error term), not as a direct identity. |
| **Observation operator** | The error-carrying map from a sensor observation to a latent state variable — here, surface SM → root-zone water (water balance) and optical index → canopy cover. Keeping each operator's error explicit is how the uncertainty chain stays honest. |
| **Supersite** | An intensively-instrumented pilot field carrying the full operator-aligned ground-truth stack (profile probes, canopy, IRT, yield+Brix, applied water). The project runs a *few* of these — depth over breadth — not a sparse regional network (ADR-0006). |
| **Extensive tier** | The light ground-truth tier paired with the supersites: yield + irrigation logs from cooperating farms, buying external validity without dense instrumentation. The "breadth" half of depth-over-breadth (ADR-0006). |
| **Within-pixel replication** | Multiple ground probes inside one satellite pixel — quantifies point-vs-pixel representativeness error *and* provides an empirical covariation test, so it doubles as RQ9 evidence (ADR-0006). |
| **Canopy IRT** | Fixed infrared thermometry (canopy temperature) used to *independently validate* the AquaCrop-derived crop water stress. A ground-truth check, **not** a model input — the sensor stack stays S1+S2 (ADR-0002, ADR-0006). |
| **Evapotranspiration / IWR** | Demand quantities AquaCrop tracks downstream (IWR = irrigation water requirement). |
| **Sentinel-1 / Sentinel-2 / PlanetScope / SAR / NDVI / NDWI / NDMI** | Earth-observation sources and indices (S1 radar, S2 optical; SAR = synthetic aperture radar). **S1+S2 are the guaranteed backbone; PlanetScope is an optional, when-available spatial enhancement, never a dependency (ADR-0004).** |

## Conventions specific to this vault

- **Wikilinks resolve by file basename**, no folder or `.md`: `[[AquaCrop Decision Interface]]`, `[[NDVI]]`. Use the exact registry basename.
- Every methodology node carries YAML front matter per `methodology_graph/99_governance/Methodology Graph Schema.md` (`id: METH-<CAT>-<NNN>`, `evidence_strength`, `confidence`, `maturity`, link fields, `tags`).
- **Evidence honesty is mandatory.** `evidence_strength` is one of `source_grounded | synthesis | inference | unconfirmed`. Inference and unconfirmed material must never be presented as fact — tag inline (`*(inference)*`, `*(proposal synthesis)*`) and flag unconfirmed items with a `> [!warning]` callout, `confidence: low`, and an entry in open questions.
- Sources in `methodology_graph/01_sources/` are **immutable** — read, never rewrite.

## Flagged / unconfirmed (do not assert as settled)

Tracked in `methodology_graph/10_research_questions/Ten Research Questions.md`:

- **Partners** — ELTE is absent from the sources; AgroVIR appears only as "AgroVIR-like." Partners assist with feedback/validation, not ownership.
- **PlanetScope access** — genuinely unsecured (a fact), but the *posture* is decided: optional non-dependency enhancement via a named research-access route, GAP novelty claimed conditionally (ADR-0004).

## ADRs

Architectural decisions live in `docs/adr/` (single-context layout). Recorded so far: **ADR-0001** (processing tomato as lead crop), **ADR-0002** (diagnostic target = minimal AquaCrop-ingestible state), **ADR-0003** (risk-adjusted expected-profit objective), **ADR-0004** (S1+S2 backbone; PlanetScope optional non-dependency), **ADR-0005** (asymmetric two-route commitment; Route B split into software patch-proxy + physical control-stand), **ADR-0006** (operator-aligned, depth-over-breadth ground-truth campaign), **ADR-0007** (four-level uncertainty evaluation; decision-primary, pre-committed), **ADR-0008** (covariation validation: incremental-information, claims-separated, publishable null), **ADR-0009** (pilot success: validated hindcast counterfactual, feasibility latency, user-acceptance), **ADR-0010** (TRL target: validated research demonstrator, TRL 5). `/domain-modeling` creates them lazily as decisions get resolved. The methodology graph's `99_governance/` and `05_decision_framework/` hold the proposal's design decisions in wiki form.
