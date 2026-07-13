# Strategic Positioning — MSCA Postdoctoral Fellowship

> **Tier 3 hand-lift (ticket 14).** Positioning against the MSCA-PF evaluation frame (Excellence 50% / Impact 30% / Implementation 20%; source: `section_schema_registry.json` MSCA-PF, HE MSCA evaluation form V.2.2) and the Part B-1 sub-section structure. Research positioning is vault-grounded; **career, training and host positioning are spine-dependent and Unresolved** (see `call_binding/confirmation_checklist.json`).

## Differentiation within the MSCA-PF frame

MSCA-PF is a **single-researcher, single-beneficiary** action assessed on the researcher's development through an excellent, well-hosted research project — not a consortium research programme. This positioning note therefore separates the **research merit** (confirmable now from the methodology vault) from the **researcher-and-host merit** (1.3, 1.4, 2.1, 3.2 — spine-dependent, deferred until the fellow, supervisor and host are confirmed).

## Excellence (50%) — research and methodology *(vault-grounded)*

**1.1 Quality and pertinence of the R&I objectives; going beyond the state of the art.** The project targets the single empty cell of the reviewed literature's research-gap matrix — *Real-Time Decision Support × PlanetScope* (`[[Research Gap Matrix]]`, `source_grounded`) — and the underdeveloped combination of *learned multimodal fusion + explicit probabilistic crop-water-state + irrigation optimisation* (`[[Probabilistic Fusion Novelty Claim]]`). The defensible edge is the end-to-end coupling, argued narrowly and honestly, not "using satellites for irrigation." Objectives are measurable against a validation protocol (uncertainty calibration, decision quality) rather than asserted.

**1.2 Soundness of the methodology.** The distinctive methodological commitment is the **honest uncertainty chain** carried from observation to decision (`[[Uncertainty Chain]]`, `[[Uncertainty Aware AquaCrop Calibration]]`). The design is **risk-managed by construction**: two interchangeable diagnostic routes share one decision engine, so a rigorous-but-demanding route (Route A, `[[Route A - Direct Probabilistic Fusion]]`) is hedged by a lighter route that sidesteps the sub-pixel problem (Route B, `[[Route B - Homogeneous Patch Proxy]]`) — the analyst's own framing of "a two-route methodology with one shared decision engine" (RQ2). Open-science practices (open data/models, a DMP by month 6) and the gender/diversity dimension are required by sub-section 1.2 and are addressed at the methodology level; the concrete open-science and EDI plan is refined once the host's practices are known.

## Excellence (50%) — researcher & supervision *(Unresolved — spine-dependent)*

**1.3 Supervision, training, two-way transfer of knowledge** and **1.4 the researcher's professional experience** cannot be drafted as confirmed content: no fellow, supervisor or host is named in any source (`[[Partner Roles Overview]]`, `[[PI Role]]`). The vault supplies only a role-inferred design owner and the fellow-attributed prior method (doi:10.1016/j.envsoft.2022.105556). These sub-sections are enumerated as blocked in the confirmation checklist and are the first to green once the spine is confirmed or β-declared.

## Impact (30%)

**2.3 Scientific, societal and economic impact** *(vault-grounded).* Scientifically, the project would establish a defensible probabilistic-fusion decision framework where the literature is thin. Societally and economically, uncertainty-aware, profit-based irrigation recommendation targets **water-use efficiency and farm economic resilience** for row-crop horticulture, with an ecological co-benefit in Route B's reliance on semi-natural covarying patches (`[[Route B - Homogeneous Patch Proxy]]`). Magnitude claims are kept proportionate and are contingent on the (open) decision objective (RQ6) and TRL target (RQ10). Call-specific expected outcomes/impacts are governed by Tier 2B (Phase 1) and are not restated here.

**2.1 Career perspectives / employability** and **2.2 dissemination, exploitation and communication** *(Unresolved / partially grounded).* 2.1 is entirely spine-dependent (the fellow's career trajectory) and is blocked. 2.2 is partially grounded — the demonstrator-and-open-science posture supports a dissemination/exploitation logic — but the target groups, IP arrangements and communication plan depend on the host and any validation partner, so the concrete plan is deferred.

## Implementation (20%)

**3.1 Work plan, risk assessment, effort per WP** *(vault-grounded research content; effort/timeline Assumed).* The work plan seed (`architecture_inputs/workpackage_seed.json`) organises the confirmed methodology into research work packages (diagnostic block, prognostic/decision engine, validation) plus the MSCA-structural training, communication and management packages. The risk assessment is lifted directly from the vault `[[Risk Register]]` (data access, validation, model complexity, operationalisation). Effort months and the 24-month timeline are an **Assumed European-Fellowship working scaffold**, not confirmed — the EF/GF choice and duration are unresolved.

**3.2 Host capacity and hosting arrangements** *(Unresolved — spine-dependent).* No host, infrastructure, or hosting arrangement is named in any source; this sub-section is blocked pending host confirmation.

## Honest gaps and open decisions

This positioning is **strategically honest** in the MSCA sense: it claims research novelty it can defend against the literature, and it does **not** claim a fellow, supervisor, host, partner, crop, site, data-access guarantee, duration or TRL that no source supports. Every such gap is a named item in `call_binding/confirmation_checklist.json` with a confirmation action, and the ten open scientific decisions are tracked in `[[Ten Research Questions]]`. A green bought by operator β-declaration (`working_assumptions.json`, ticket 15) remains legible as *declared*, not confirmed.

## Source grounding

Research positioning traces to the pinned methodology vault (`MSCA/methodology_graph/`, SHA `b4d9e57`); evaluation-frame facts trace to `docs/tier2a_instrument_schemas/extracted/section_schema_registry.json` (MSCA-PF). Consolidated per-fact provenance: `docs/tier3_project_instantiation/hand_lift_provenance.json`.
