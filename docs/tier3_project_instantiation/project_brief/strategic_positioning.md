---
record_type: tier3_strategic_positioning
authority: "CLAUDE.md §5 Tier 3, §12.2 status categories, §13.3 no fabricated project facts"
source: docs/tier3_project_instantiation/source_materials/consolidated_pack_2026-08-28/FIELDWISE_Consolidated_Partner_Review_Pack_2026-08-28.docx
baseline_record: docs/tier4_orchestration_state/decision_log/fieldwise-run-02-baseline_2026-08-28.json
spine_status: confirmed_real
validation_status: Confirmed
source_ref: "Pack B, §1.1.9, §2.3, Pack E, 'Core message'"
note: >
  Prose lifted from the Consolidated Partner Review Pack of 2026-08-28 with no substantive
  rewriting (§10.5 traceability). Supersedes the Master Draft positioning of
  fieldwise-run-01 (six transitions, validation ladder). The resubmission-positioning
  section replaces the prior-evaluation quotes of the superseded draft: the governing prior
  fact is now the resubmission bar and the host switch, recorded with declared statuses in
  call_binding/confirmation_checklist.json.
---

# FIELDWISE — Strategic positioning

<!-- source_ref: Pack §1.1.9 -->
## Ambition beyond the state of the art

FIELDWISE is ambitious because it connects biological truth, rigorous transferability
testing, sensing scale and operational decision support within one validation chain, while
deliberately designing the resulting digital framework for reuse beyond the development
crop. It does not assume that a vegetation index is equivalent to water stress, that
proximal and satellite indices are interchangeable, that internal cross-validation proves
field transferability, or that one tomato-trained model can be transferred unchanged to
another horticultural crop.

1. Stress proxy -> physiologically defined stress target
2. Heterogeneous five-season archive -> explicit common-variable/missingness design
3. Internal fit -> blocked unseen-year validation -> independent commercial-field validation
4. Leaf/proximal sensing -> ELTE hyperspectral/UAV bridge -> Sentinel-2 field-scale operational inputs
5. Standalone model -> continuously developed DrR web MVP -> AgroVIR industrial evaluation
6. Academic-only validation -> farmer-facing real-world test plus a defined post-MSCA Bulgarian replication route through MVCRI
7. Tomato-specific prototype -> crop-configurable high-value-horticulture framework with explicit crop-specific validation/calibration gates

<!-- source_ref: Pack B -->
## The project logic in one chain

MATE longitudinal evidence -> physiological stress definition -> HUN-REN modelling and
uncertainty -> ELTE proximal/UAV/Sentinel scale bridging -> independent commercial-farmer
validation -> validated crop module -> Krumatic software implementation -> DrR web MVP ->
AgroVIR operational/FMIS evaluation -> post-MSCA Bulgarian replication and additional crop
modules.

The scientific objective is not to build an app. The objective is to establish and validate
a physiologically grounded water-stress decision framework. DrR is the pre-existing
research-to-application vehicle through which validated outputs become usable decision
support.

<!-- source_ref: Pack §2.3, Pack E -->
## Magnitude and importance of expected impacts

### Scientific impact

FIELDWISE provides a validation framework in which operationally obtainable data streams
are judged against independent plant-level ground truth and challenged under both
unseen-year and new commercial-field conditions. It clarifies which stress relationships
survive the transition from proximal measurements toward UAV and Sentinel-2 field
monitoring and which components of the modelling/decision workflow are genuinely reusable
beyond the development crop.

### Agricultural and environmental impact

FIELDWISE will not promise a fixed percentage reduction in irrigation water. Published
processing-tomato evidence provides bounded magnitude context: a two-year plant-plus-soil
monitoring study reported about 30% less irrigation water than empirical farmer management
and about 7.5% less than evapotranspiration-based scheduling, with yield differences that
underline the need to quantify water-yield trade-offs; a 2026 study reported 25% water
saving from early-timed controlled deficit without statistically significant yield loss,
while poorly timed or prolonged deficits reduced yield. FIELDWISE uses an external benchmark
range of roughly 8-30% only as bounded literature context, never as a project promise. The
project's claimed decision value is correct stress detection, lead time, uncertainty
honesty, usability and irrigation-attention relevance; prospective water-saving
quantification is claimed only to the extent the farmer-field irrigation-treatment
arrangement actually supports it (working assumption farmer_field_access), and otherwise
detection, lead-time and uncertainty outcomes are reported together with yield and quality
from the prospective validation data.

### Technological and economic impact

The web-based DrR MVP provides a tangible route from validated research to external testing,
preserving the distinction between the fellow's pre-existing DrR background and FIELDWISE
foreground. The architecture is crop-configurable; AgroVIR identifies the requirements for
future FMIS integration and Krumatic supports implementation and Bulgarian uptake. Within
the action, validation is limited to processing tomato; the crop-transfer specification
(T2.6) defines the components, parameters, minimum datasets and recalibration gates any
later crop addition must pass. The named follow-on route is concrete: MVCRI — with its
established vegetable-crop variety-trial design infrastructure — is the post-MSCA channel
through which the validated outcomes are transferred to and validated on additional tomato
cultivars under Bulgarian production conditions, as knowledge transfer outside the
24-month work plan (no in-action MVCRI effort is claimed). Economic
value is not expressed as an invented EUR/ha promise; FIELDWISE quantifies the measured
quantities from which later economic value can be assessed.

### European and societal relevance

Fresh vegetables were cultivated over approximately 2.0 million hectares in the EU in 2023,
by about 0.7 million EU farms (2020 census) — the scale of the domain, not an immediate
market. Bulgaria provides concrete downstream context: 35.6 thousand hectares of main
vegetable area and about 128 thousand tonnes of tomato in harvest 2024. FIELDWISE
contributes particularly to SDG 2, SDG 6, SDG 12 and SDG 13.

<!-- source_ref: call_binding/confirmation_checklist.json RESUBMISSION_BAR, PLANTDIGISENSE_SCORE -->
## Resubmission positioning

The 2026 call conditions bar resubmission of proposals involving the same recruiting
organisation and individual researcher that scored below 80% in 2025. The 2025 submission
PLANTDIGISENSE (host ELTE, the same researcher) scored 70.40% per the researcher's CV.
FIELDWISE is therefore submitted from a new recruiting organisation — HUN-REN ATK — with the
supervision restructured around it; ELTE continues as an associated partner. The score of
record (ESR) and the NCP/REA answer to the prepared eligibility query are operator-declared
assumptions until the documents arrive; the proposal text does not argue the bar.

<!-- source_ref: Pack 'Core message' -->
## Core message

FIELDWISE moves crop-stress modelling beyond retrospective accuracy by asking whether a
physiologically meaningful water-stress signal survives unseen years, a new real production
environment and a change of sensing scale — and whether the validated workflow can be
separated into a reusable decision-support core and crop-specific biological/calibration
components. Processing tomato is the evidence-rich starting crop because five years of
scientific data and strong collaborations already exist; the ambition is a scientifically
controlled pathway toward additional irrigated high-value horticultural crops, not a
universal tomato model imposed on all crops.
