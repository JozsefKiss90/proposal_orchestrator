---
record_type: tier3_concept_note
authority: "CLAUDE.md §5 Tier 3, §12.2 status categories, §13.3 no fabricated project facts"
source: docs/tier3_project_instantiation/source_materials/consolidated_pack_2026-08-28/FIELDWISE_Consolidated_Partner_Review_Pack_2026-08-28.docx
baseline_record: docs/tier4_orchestration_state/decision_log/fieldwise-run-02-baseline_2026-08-28.json
spine_status: confirmed_real
validation_status: Confirmed
source_ref: "Pack §1.1.1-§1.1.7"
note: >
  Prose lifted from the Consolidated Partner Review Pack of 2026-08-28 with no substantive
  rewriting (§10.5 traceability). Section markers cite the Pack's own section numbers.
  Supersedes the Master Draft concept note of fieldwise-run-01 (gaps G1-G6, RQ1-RQ7, H1-H6);
  the Pack carries gaps G1-G3, RQ1-RQ5 and H1-H4.
---

# FIELDWISE — Concept note

<!-- source_ref: Pack §1.1.1 -->
## European challenge and scientific rationale

Water scarcity and increasing climatic variability are intensifying the need for more
efficient irrigation management in European high-value horticulture. Processing tomato is
used in FIELDWISE as the model crop because water availability strongly influences plant
functioning, yield formation, water-use efficiency and fruit quality, while the consortium
already has a uniquely strong combination of longitudinal scientific evidence, experimental
expertise and established working relationships around this crop. Yet irrigation decisions
in horticulture are still frequently based on delayed visual symptoms, isolated sensor
thresholds or retrospective crop-performance information.

Processing tomato is therefore the scientifically justified starting point, not the intended
limit of the technology. FIELDWISE will distinguish between (i) a transferable core
consisting of the data architecture, physiology-to-prediction workflow, uncertainty logic,
sensing-scale integration and irrigation-attention interface, and (ii) crop-specific
components such as physiological reference ranges, phenological interpretation, stress
thresholds and calibration parameters. The long-term objective is a crop-configurable DrR
framework that can be extended to other irrigated high-value horticultural crops once
appropriate crop-specific validation data are available. FIELDWISE will not claim that a
tomato-trained model can be applied unchanged to every crop; it will build and document the
methodology required for scientifically controlled transfer.

**Central challenge:** Can a water-stress signal discovered in a data-rich processing-tomato
system remain biologically meaningful across seasons and sensing scales, survive prospective
validation under real farmer conditions, and be encoded in a crop-configurable
decision-support framework that can later be adapted to other irrigated high-value
horticultural crops?

<!-- source_ref: Pack §1.1.2 -->
## Why prediction accuracy alone is insufficient

Agricultural sensing and modelling studies increasingly combine proximal spectroscopy, soil
and weather sensing, UAV observations, satellite Earth Observation (EO) and machine
learning. However, strong retrospective accuracy does not guarantee operational usefulness.
Models may exploit year-, treatment- or site-specific correlations; random train-test
splitting may overestimate generalisation; and a diagnosis of established stress may arrive
too late to alter irrigation.

FIELDWISE therefore evaluates success through four linked criteria: physiological validity,
predictive performance, transferability to unseen conditions and management relevance. The
aim is not to develop novel AI algorithms or maximise the number of models tested, but to
identify a parsimonious, interpretable and uncertainty-aware modelling strategy that remains
robust under leakage-safe temporal validation and prospective commercial-field testing.

<!-- source_ref: Pack §1.1.3 -->
## Preliminary basis: DrR - Digital Agronomist

DrR - Digital Agronomist is a pre-existing research tool initiated and developed
independently by the fellow, Rositsa Cholakova, using her own time and personal financial
resources. It was not commissioned or financed as an institutional software-development
project by the Maritsa Vegetable Crops Research Institute (MVCRI). The fellow currently uses
DrR in the conduct of her own research activities at MVCRI as a data-collection, monitoring
and integration tool for field sensors, environmental observations and Sentinel-2-derived
information. At this stage DrR is not a validated irrigation advisory product and should not
be described as an institutional MVCRI software platform. It constitutes pre-existing
project background whose ownership, version and access conditions will be documented before
the MSCA action starts.

FIELDWISE will use this existing prototype as a research-to-application vehicle rather than
making software development the scientific objective of the fellowship. Only validated
scientific components will be progressively incorporated into DrR. The intended pathway is:
existing monitoring/data-integration tool -> FIELDWISE physiological and modelling research
-> scientifically validated stress-prediction component -> crop-configurable
decision-support architecture -> web MVP -> operational farmer-oriented evaluation. Krumatic
will support software engineering, while AgroVIR will provide requirements-oriented
consultation from project start and later operational/FMIS evaluation. The software follows
the science, not the other way around.

<!-- source_ref: Pack §1.1.4 -->
## Three focused scientific gaps

**G1 - Physiological grounding of plant water-stress indicators**

Spectral and environmental variables are often treated as stress proxies without
demonstrating that they correspond to actual plant responses. FIELDWISE will define a
physiologically meaningful stress target and identify a restricted set of proximal spectral,
soil-water and meteorological indicators that track that target.

**G2 - Transferability across unseen conditions, sensing scales and horticultural crops**

The MATE archive provides valuable multi-year processing-tomato information, but
relationships learned from controlled research plots may not survive a new production
environment and cannot automatically be assumed to hold for other crops. FIELDWISE therefore
separates three levels of transferability: temporal transfer across unseen years;
environmental transfer from research experiments to an independent commercial field; and
methodological/crop transfer, in which the stable data architecture and decision workflow
are separated from crop-specific physiological targets and calibration parameters. UAV
observations bridge plant/plot measurements toward field-scale Sentinel-2 monitoring where
pixel support is physically meaningful.

**G3 - Irrigation decision relevance**

A model may be statistically accurate yet provide little management value if warnings are
unstable, uncertain or too late. FIELDWISE will translate validated stress predictions into
interpretable irrigation-attention information and evaluate usability and interoperability
through AgroVIR.

<!-- source_ref: Pack §1.1.5 -->
## Central research question

Can physiologically grounded water-stress signatures derived from heterogeneous multi-year
processing-tomato observations be converted into a parsimonious predictive framework that
remains reliable under unseen-year and prospective commercial-field validation, and can the
validated architecture be made crop-configurable so that the same physiology-to-decision
workflow can later be transferred to other irrigated high-value horticultural crops through
explicit crop-specific validation and calibration?

<!-- source_ref: Pack §1.1.6 -->
## Research questions

- RQ1. Which soil-water, meteorological, physiological and proximal spectral variables
  provide the most robust indication of developing water stress in processing tomato across
  the heterogeneous 2022-2026 MATE archive?
- RQ2. Can a parsimonious process-informed/AI-supported model predict the defined
  physiological stress state from operationally obtainable data streams that can be
  integrated through DrR?
- RQ3. Which relationships remain stable under blocked unseen-year validation and when
  transferred prospectively to an independent commercial farmer field, and what limited
  recalibration is required if transfer is incomplete?
- RQ4. Which physiological and proximal signals can be translated across sensing scales
  through ELTE UAV/hyperspectral expertise toward Sentinel-2 field monitoring without
  assuming equivalence between leaf-, plot- and satellite-scale measurements?
- RQ5. Can the validated framework be implemented incrementally in a crop-configurable web
  MVP that meets scientifically defined performance gates and practical AgroVIR
  usability/interoperability requirements while clearly separating reusable system
  components from crop-specific calibration parameters?

<!-- source_ref: Pack §1.1.7 -->
## Hypotheses

- **H1 - Physiological signature hypothesis.** Declining soil-water availability and
  increasing atmospheric demand produce coordinated plant responses that can be captured by
  a parsimonious subset of proximal spectral and environmental indicators.
- **H2 - Transferability hypothesis.** Performance will decrease when moving from internal
  fitting to unseen-year and independent commercial-field validation, but a stable core of
  the physiology-to-prediction workflow can be identified. That transferable core will form
  the basis for later extension to other irrigated high-value horticultural crops, while
  crop-specific physiological targets, phenological interpretation and calibration will be
  treated explicitly rather than assumed universal.
- **H3 - Scale-transition hypothesis.** Physiologically meaningful proximal signatures will
  not map one-to-one to satellite bands, but a subset of relationships can be retained
  through explicit hyperspectral/UAV-to-Sentinel harmonisation at spatial scales where field
  geometry supports valid EO interpretation.
- **H4 - Operational relevance hypothesis.** A model selected for physiological validity,
  calibration, uncertainty and stability will provide more useful irrigation-attention
  information than one selected solely for retrospective predictive accuracy.
