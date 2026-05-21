Which agents and skills rely on or use the 'tier1_normative_framework' files the most?                                                                                                        

● Let me search for references to tier1_normative_framework across agents, skills, and related configuration files.

  Searched for 5 patterns (ctrl+o to expand)

● Now let me read the top referencing files in detail.

  Searched for 2 patterns (ctrl+o to expand)

● Here's a summary of which agents and skills rely on tier1_normative_framework, ranked by usage intensity:

  Skills (heaviest to lightest)

  ┌─────────────────────────────────────┬────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │                Skill                │ References │                                                          How it uses Tier 1                                                           │
  ├─────────────────────────────────────┼────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ governance-model-builder            │ 12         │ Heaviest consumer. Reads governance_principles.json and implementation_constraints.json as mandatory inputs. Fails if either is       │
  │                                     │            │ missing. Sources every programme-rule claim back to Tier 1 files.                                                                     │
  ├─────────────────────────────────────┼────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ proposal-section-traceability-check │ 4          │ Uses Tier 1 extracted files as the reference set for verifying "Confirmed" traceability status on claims attributed to                │
  │                                     │            │ legislation/programme guidance.                                                                                                       │
  ├─────────────────────────────────────┼────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ constitutional-compliance-check     │ 1          │ References Tier 1 for compliance verification against normative rules.                                                                │
  └─────────────────────────────────────┴────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  Agents (heaviest to lightest)

  ┌──────────────────────┬──────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │        Agent         │      References      │                                                            How it uses Tier 1                                                             │
  ├──────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ compliance_validator │ 2 (+ 3 in its prompt │ Declares tier1_normative_framework/extracted/ as an input. Its prompt spec instructs it to read Tier 1 files when present and never       │
  │                      │  spec)               │ substitute agent knowledge for file contents (§13.9).                                                                                     │
  ├──────────────────────┼──────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ traceability_auditor │ 2 (+ 1 in its prompt │ Declares tier1_normative_framework/extracted/ as an input for verifying "Confirmed" status checks against normative sources.              │
  │                      │  spec)               │                                                                                                                                           │
  └──────────────────────┴──────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  Workflow bindings

  The system_orchestration.yaml manifest references Tier 1 in 5 places — binding it as a tier source, listing it as an input for nodes n10c (traceability check), n10d (constitutional
  compliance), and the n06 implementation architecture phase. The agent_catalog.yaml binds it to the compliance_validator and traceability_auditor agents.

  Key takeaway

  governance-model-builder is by far the most dependent skill — it has hard input requirements on two specific Tier 1 extracted files and will fail without them. The compliance_validator agent
   (with its prompt spec) and the proposal-section-traceability-check skill are the next most significant consumers, using Tier 1 as a reference authority for compliance and traceability
  verification.

✻ Cooked for 32s

❯ Which workflow elements process or use the 'general_fpa' and 'general_mga' pdf coments and what are the next upstream elements?                                                               

  Searched for 10 patterns (ctrl+o to expand)

● Now let me check what extracted files exist and how the extraction pipeline references them.

  Searched for 5 patterns, read 4 files (ctrl+o to expand)

● Here's the full picture:

  general_fpa.pdf and general_mga.pdf — Current Usage

  No workflow element directly reads or processes these PDFs. Zero references to general_fpa or general_mga (by filename) exist anywhere in skills, agents, workflows, or runner code. The only
  mention is in project_structure.md as a directory listing.

  What does reference the grant architecture subdirectory

  The grant_architecture/ directory is acknowledged at the tier binding level:

  - tier_bindings.yaml and system_orchestration.yaml — describe Tier 1 as containing "model grant architectures" in their prose, but no node or skill declares a direct input path to
  grant_architecture/*.pdf.

  The anti-pattern guard (not consumption)

  Three skills reference MGA/FPA concepts, but only as prohibitions — detecting and rejecting their misuse:

  ┌─────────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
  │                Skill                │                                                             What it does with MGA/FPA                                                              │
  ├─────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ constitutional-compliance-check     │ Detects if a proposal section cites a "Grant Agreement Annex", "Model Grant Agreement", or "AGA" as a structural authority → flags as critical     │
  │                                     │ violation (CLAUDE.md §13.1)                                                                                                                        │
  ├─────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ instrument-schema-normalization     │ Guards against accidentally loading a Grant Agreement Annex as the application form template → fails if the identified application form contains   │
  │                                     │ "Grant Agreement" or "AGA" in its title                                                                                                            │
  ├─────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
  │ proposal-section-traceability-check │ Lists grant_architecture in the Tier 1 description prose, but only as part of the reference set for verifying Tier 1-attributed claims             │
  └─────────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

  Actual downstream consumption path

  The PDFs' content flows indirectly through the extracted JSON files:

  grant_architecture/*.pdf  ──(manual extraction)──►  tier1_normative_framework/extracted/
      general_fpa.pdf                                      governance_principles.json
      general_mga.pdf                                      implementation_constraints.json
      general-mga_horizon-euratom_en.pdf                   (compliance_principles.json — empty)
      mga_lump_sum.pdf                                     (participation_rules.json — empty)

  However, the two populated extracted files (governance_principles.json, implementation_constraints.json) source their content from the Programme Guide and General Annexes, not from the
  MGA/FPA PDFs. Their source_documents arrays list:
  - programme-guide_horizon_en.pdf
  - wp-15-general-annexes_horizon-2026-2027_en.pdf
  - ef_he-ria-ia_en.pdf (evaluation form)

  Upstream elements that would consume extracted Tier 1

  If content from the FPA/MGA were ever extracted into the JSON files, the upstream consumers would be (per my earlier analysis):

  1. governance-model-builder skill (Phase 6) — reads governance_principles.json and implementation_constraints.json
  2. compliance_validator agent — reads tier1_normative_framework/extracted/
  3. traceability_auditor agent — reads tier1_normative_framework/extracted/
  4. proposal-section-traceability-check skill — uses extracted files as reference set

  Bottom line

  The general_fpa.pdf and general_mga.pdf files are present but unused — no workflow element reads them, no extraction has been performed from them, and the constitution (§13.1) actively
  prohibits using Grant Agreement/FPA templates as structural schema sources for proposal writing. They exist as Tier 1 source materials available for future rule extraction, but the current
  extracted JSON files derive from the Programme Guide and General Annexes instead.

✻ Churned for 1m 7s

❯ Are the files used to a sufficent degree or should their integration into the workflow be more enhanced?                                                                                      

● Good question. Let me assess this properly by examining what these documents contain, what's currently extracted, and what gaps exist.

  Read 5 files (ctrl+o to expand)

● Let me read the substantive articles of these documents to assess what proposal-relevant content they contain.

  Read 2 files (ctrl+o to expand)

● Now I have a thorough picture of all three documents. Let me give you a clear assessment.

  Assessment: Are the MGA/FPA files used sufficiently?

  Short answer: The current level of integration is largely appropriate for the system's mission, but there are a few targeted gaps worth closing.

  Why the current light integration is mostly correct

  The constitution (CLAUDE.md §2) is explicit: "The optimisation target of this system is evaluation success under the applicable Horizon Europe evaluation criteria. It is not
  grant-preparation formatting, grant agreement annex compliance, or financial reporting readiness."

  The MGA and FPA are post-award documents. Their bulk content — payment schedules, reporting deadlines, cost eligibility conditions, audit procedures, certificate thresholds, financial
  statement models, recovery mechanisms — is irrelevant to proposal writing. The constitutional prohibition in §13.1 against using Grant Agreement Annex templates as structural schemas is
  well-founded, and the existing guard rails (constitutional-compliance-check, instrument-schema-normalization) correctly enforce this.

  The existing extracted files (governance_principles.json, implementation_constraints.json) correctly source their content from the Programme Guide and General Annexes — which are the
  proposal-facing distillation of MGA/FPA obligations. This is the right source hierarchy for proposal writing.

  Where targeted extraction would add value

  However, the HE MGA (specifically the general-mga_horizon-euratom_en.pdf, V1.2) contains a few article clusters that are directly relevant to proposal evaluation because evaluators assess
  whether the applicant demonstrates awareness of the post-award obligations their project will face:

  ┌─────────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────┐
  │             MGA Article             │                               Proposal relevance                               │                      Currently extracted?                       │
  ├─────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │                                     │ Evaluators check ethics awareness. The MGA's binding ethics obligations go     │ Partially — implementation_constraints.json covers ethics from  │
  │ Art. 14 — Ethics and Values         │ beyond the Programme Guide summary.                                            │ the Programme Guide but not the MGA's specific Article 14       │
  │                                     │                                                                                │ obligations                                                     │
  ├─────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Art. 16 — IPR, Background, and      │ Section 3.2 (Implementation) must describe IPR management. The MGA defines     │                                                                 │
  │ Access Rights                       │ "background", "results", "access rights", and "fair and reasonable conditions" │ No — not extracted anywhere                                     │
  │                                     │  — the exact vocabulary evaluators expect.                                     │                                                                 │
  ├─────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Art. 17 — Communication,            │ Section 2.2 (Impact) must describe dissemination/exploitation. Art. 17 defines │ Partially — implementation_constraints.json has a generic       │
  │ Dissemination, and Visibility       │  binding obligations (EU flag, funding statement, open access, disclaimer)     │ dissemination rule from the Programme Guide, but not the        │
  │                                     │ that a credible D&E plan should acknowledge.                                   │ MGA-specific obligations                                        │
  ├─────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Art. 11 — Proper Implementation     │ The "best effort" obligation and consequences of non-compliance inform how     │ No                                                              │
  │                                     │ evaluators judge implementation credibility.                                   │                                                                 │
  ├─────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │ Art. 9 — Other Participants         │ The MGA definitions of subcontracting vs. purchases vs. in-kind contributions  │                                                                 │
  │ (subcontracting, third parties,     │ directly affect how the implementation section must describe consortium        │ No                                                              │
  │ associated partners)                │ resource allocation.                                                           │                                                                 │
  ├─────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────┤
  │                                     │ Canonical definitions of "results", "background", "dissemination",             │                                                                 │
  │ Art. 2 — Definitions                │ "exploitation", "open access", "open science", "research and innovation        │ No                                                              │
  │                                     │ action", etc. These are the authoritative vocabulary.                          │                                                                 │
  └─────────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────┴─────────────────────────────────────────────────────────────────┘

  The FPA (general_fpa.pdf) is the generic corporate MGA template — it's a structural superset that the HE-specific MGA inherits from. It adds no proposal-relevant content beyond what the HE
  MGA already contains. No further extraction is needed from the FPA.

  The Regulation (general-mga_horizon-euratom_en.pdf pages contain Regulation (EU) 2021/695) — this is actually the primary legislation establishing Horizon Europe. Its Article 2 definitions,
  Article 3 programme objectives, and Article 14 (open science) are high-value sources that should arguably live in a dedicated legislation/ extracted file.

  Recommendation

  Don't enhance the integration broadly — enhance it surgically. Specifically:

  1. Extract an ipr_and_access_rights.json from HE MGA Art. 16 + Art. 2 definitions. This would give Phase 5 (Impact Architecture) and Phase 8 drafting grounded vocabulary for IPR management,
  background/results/access rights, and exploitation framing — terms evaluators expect to see used precisely.
  2. Extract a dissemination_visibility_obligations.json from HE MGA Art. 17. This would strengthen the dissemination-exploitation-communication-check skill and the Impact section drafting
  with binding MGA obligations that a credible D&E plan should acknowledge.
  3. Enrich implementation_constraints.json with MGA Art. 14 (ethics/values) specifics and Art. 9 (participant categories — subcontracting vs. associated partners vs. third-party
  contributions). These directly affect how the Implementation section must be framed.
  4. Extract a programme_definitions.json from Regulation 2021/695 Art. 2 (the definitions article). Having canonical legal definitions of "RIA", "IA", "results", "background", "open science",
   etc. would benefit vocabulary consistency across all drafting skills.
  5. Do not extract the FPA, the MGA's financial/reporting/audit articles (Ch. 3-5), or the budget-related Data Sheet content. These are post-award and constitutionally out of scope.

  This approach respects the constitutional boundary — no MGA content becomes a structural schema — while closing the real gap: proposal sections that discuss IPR, dissemination, ethics, and
  participant roles currently lack grounded MGA-sourced vocabulary, relying instead on the Programme Guide's higher-level summaries or worse, unattributed generic knowledge.

  
❯ How are the files in the 'Tier2B_Topic_and_Call_Sources' folder populated? What are the most important inputs and workflow elements?                                                          
                                                                                                                                       
  Searched for 2 patterns, read 4 files (ctrl+o to expand)                                                                                                                                      
                                                                                                                                                                                                
● Now I have a comprehensive picture. Here's the full population flow:                                                                                                                          
                                                             
  How Tier 2B is Populated                                                                                                                                                                      
                                                                                                                                                                                                
  Tier 2B has three layers, each populated differently:                                                                                                                                         
                                                                                                                                                                                                
  Layer 1: work_programmes/ — Manually placed source data

  These are pre-populated, manually placed files. They are not produced by any workflow element.

  ┌───────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────┬─────────────────┐
  │                   File                    │                                             Content                                             │      Size       │
  ├───────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────┤
  │ cluster_CL1–CL6.grouped.json              │ Full work programme content for each Horizon Europe cluster, structured as destinations → calls │ 338–794 KB each │
  ├───────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────┤
  │ HORIZON-ERC.json, HORIZON-MSCA.json, etc. │ Work programmes for non-cluster programmes                                                      │ Varies          │
  └───────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────┴─────────────────┘

  These are the raw source material — the largest and most important inputs to the entire system. They must be placed by the human operator before any workflow can begin.

  Layer 2: call_extracts/ — Two distinct sources

  a) Curated call extract (manually placed):
  - HORIZON-CL4-2026-05-DIGITAL-EMERGING-02.json — A structured, human-curated interpretation of the specific topic with fields like outcomes arrays, scope summaries, research areas, FSTP
  details.

  b) Call slice (deterministically generated):
  - HORIZON-CL4-2026-05-DIGITAL-EMERGING-02.slice.json — Produced by runner/call_slicer.py (Step 0), a pure-Python preprocessing layer that runs before any Claude invocation. It:
    a. Reads selected_call.json to get the topic_code and work_programme
    b. Loads the corresponding grouped JSON (e.g., cluster_CL4.grouped.json)
    c. Linear-scans for the matching call entry
    d. Extracts just that one call entry (~5–8 KB from a 338+ KB file)
    e. Writes it as a bounded slice to call_extracts/

  This is the critical input bounding step — it reduces the data Claude must process from hundreds of KB to single-digit KB.

  Layer 3: extracted/ — Six structured JSON files produced by Phase 1

  These are the workflow outputs — produced by the call_analyzer agent running the call-requirements-extraction skill during Phase 1:

  ┌──────────────────────────────────┬───────────────────────────────────────────────────────────────┬──────────────────────────────────┐
  │               File               │                            Content                            │             Join key             │
  ├──────────────────────────────────┼───────────────────────────────────────────────────────────────┼──────────────────────────────────┤
  │ call_constraints.json            │ Binding call constraints (eligibility, scope, methodological) │ —                                │
  ├──────────────────────────────────┼───────────────────────────────────────────────────────────────┼──────────────────────────────────┤
  │ expected_outcomes.json           │ Verbatim expected outcomes from work programme                │ outcome_id → Phase 2             │
  ├──────────────────────────────────┼───────────────────────────────────────────────────────────────┼──────────────────────────────────┤
  │ expected_impacts.json            │ Verbatim expected impacts                                     │ impact_id → Phase 5              │
  ├──────────────────────────────────┼───────────────────────────────────────────────────────────────┼──────────────────────────────────┤
  │ scope_requirements.json          │ Thematic scope boundaries                                     │ —                                │
  ├──────────────────────────────────┼───────────────────────────────────────────────────────────────┼──────────────────────────────────┤
  │ eligibility_conditions.json      │ Participation eligibility conditions                          │ —                                │
  ├──────────────────────────────────┼───────────────────────────────────────────────────────────────┼──────────────────────────────────┤
  │ evaluation_priority_weights.json │ Evaluation criterion weights                                  │ criterion_id → evaluation matrix │
  └──────────────────────────────────┴───────────────────────────────────────────────────────────────┴──────────────────────────────────┘

  Every entry in these files carries source_section, source_document, and a status (Confirmed/Inferred/Assumed/Unresolved). Missing source references on Confirmed entries trigger a
  CONSTITUTIONAL_HALT.

  The Full Pipeline

  MANUAL PLACEMENT                     STEP 0 (deterministic)           PHASE 1 (Claude)
  ─────────────────                     ─────────────────────           ────────────────

  work_programmes/
    cluster_CL4.grouped.json ──┐
         (338+ KB)             │
                               ├──► call_slicer.py ──► .slice.json ──┐
  selected_call.json ──────────┘     (topic_code      (~5-8 KB)     │
    (topic_code,                      + work_programme                │
     work_programme,                  lookup)                         │
     instrument_type)                                                 ├──► call_analyzer agent
                                                                     │      │
  call_extracts/                                                     │      ├─ call-requirements-extraction ──► extracted/ (6 files)
    <topic>.json (curated) ─────────────────────────────────────────┘      ├─ evaluation-matrix-builder ──► Tier 4 eval matrix
                                                                            ├─ instrument-schema-normalization ──► Tier 2A schemas
                                                                            ├─ topic-scope-check ──► decision log
                                                                            └─ gate-enforcement ──► gate_result.json

  Most Important Inputs (ranked)

  1. selected_call.json — The trigger for everything. Without the topic_code and work_programme, nothing can resolve.
  2. Grouped work programme JSON (e.g., cluster_CL4.grouped.json) — The authoritative source material. Contains all call entries with their scope, outcomes, impacts, and eligibility
  conditions.
  3. Curated call extract (<topic>.json) — Supplements the raw work programme with structured interpretation.

  Most Important Workflow Elements (ranked)

  1. call_slicer.py — Deterministic Step 0 input bounding. Reduces 338–794 KB to ~5–8 KB. Runs before any Claude call.
  2. call-requirements-extraction skill — The skill that actually reads the sources and produces all six extracted files. Most complex skill in Phase 1.
  3. call_analyzer agent — Orchestrates Phase 1, sequences all five skills, handles failures.
  4. gate_01_source_integrity (entry gate) — Validates that all source materials exist before Phase 1 begins.
  5. phase_01_gate (exit gate) — Validates all six extracted files are non-empty with source references before Phase 2 can start.

  Downstream Consumption

  The six extracted files are consumed by virtually every subsequent phase:
  - Phase 2 (concept refinement) — aligns concept with expected_outcomes.json and scope_requirements.json
  - Phase 5 (impact architecture) — maps project outputs to expected_impacts.json using impact_id join keys
  - Phase 6 (implementation architecture) — governance-model-builder reads scope_requirements.json and call constraints
  - Phase 8 (drafting) — all three section drafting skills read extracted files for evaluator-oriented vocabulary

 How are the files in the 'Tier2B_Topic_and_Call_Sources' folder populated? What are the most important inputs and workflow elements?                                                          
                                                                                                                                       
  Searched for 2 patterns, read 4 files (ctrl+o to expand)                                                                                                                                      
                                                                                                                                                                                                
● Now I have a comprehensive picture. Here's the full population flow:                                                                                                                          
                                                             
  How Tier 2B is Populated                                                                                                                                                                      
                                                                                                                                                                                                
  Tier 2B has three layers, each populated differently:                                                                                                                                         
                                                                                                                                                                                                
  Layer 1: work_programmes/ — Manually placed source data

  These are pre-populated, manually placed files. They are not produced by any workflow element.

  ┌───────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────┬─────────────────┐
  │                   File                    │                                             Content                                             │      Size       │
  ├───────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────┤
  │ cluster_CL1–CL6.grouped.json              │ Full work programme content for each Horizon Europe cluster, structured as destinations → calls │ 338–794 KB each │
  ├───────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────┤
  │ HORIZON-ERC.json, HORIZON-MSCA.json, etc. │ Work programmes for non-cluster programmes                                                      │ Varies          │
  └───────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────┴─────────────────┘

  These are the raw source material — the largest and most important inputs to the entire system. They must be placed by the human operator before any workflow can begin.

  Layer 2: call_extracts/ — Two distinct sources

  a) Curated call extract (manually placed):
  - HORIZON-CL4-2026-05-DIGITAL-EMERGING-02.json — A structured, human-curated interpretation of the specific topic with fields like outcomes arrays, scope summaries, research areas, FSTP
  details.

  b) Call slice (deterministically generated):
  - HORIZON-CL4-2026-05-DIGITAL-EMERGING-02.slice.json — Produced by runner/call_slicer.py (Step 0), a pure-Python preprocessing layer that runs before any Claude invocation. It:
    a. Reads selected_call.json to get the topic_code and work_programme
    b. Loads the corresponding grouped JSON (e.g., cluster_CL4.grouped.json)
    c. Linear-scans for the matching call entry
    d. Extracts just that one call entry (~5–8 KB from a 338+ KB file)
    e. Writes it as a bounded slice to call_extracts/

  This is the critical input bounding step — it reduces the data Claude must process from hundreds of KB to single-digit KB.

  Layer 3: extracted/ — Six structured JSON files produced by Phase 1

  These are the workflow outputs — produced by the call_analyzer agent running the call-requirements-extraction skill during Phase 1:

  ┌──────────────────────────────────┬───────────────────────────────────────────────────────────────┬──────────────────────────────────┐
  │               File               │                            Content                            │             Join key             │
  ├──────────────────────────────────┼───────────────────────────────────────────────────────────────┼──────────────────────────────────┤
  │ call_constraints.json            │ Binding call constraints (eligibility, scope, methodological) │ —                                │
  ├──────────────────────────────────┼───────────────────────────────────────────────────────────────┼──────────────────────────────────┤
  │ expected_outcomes.json           │ Verbatim expected outcomes from work programme                │ outcome_id → Phase 2             │
  ├──────────────────────────────────┼───────────────────────────────────────────────────────────────┼──────────────────────────────────┤
  │ expected_impacts.json            │ Verbatim expected impacts                                     │ impact_id → Phase 5              │
  ├──────────────────────────────────┼───────────────────────────────────────────────────────────────┼──────────────────────────────────┤
  │ scope_requirements.json          │ Thematic scope boundaries                                     │ —                                │
  ├──────────────────────────────────┼───────────────────────────────────────────────────────────────┼──────────────────────────────────┤
  │ eligibility_conditions.json      │ Participation eligibility conditions                          │ —                                │
  ├──────────────────────────────────┼───────────────────────────────────────────────────────────────┼──────────────────────────────────┤
  │ evaluation_priority_weights.json │ Evaluation criterion weights                                  │ criterion_id → evaluation matrix │
  └──────────────────────────────────┴───────────────────────────────────────────────────────────────┴──────────────────────────────────┘

  Every entry in these files carries source_section, source_document, and a status (Confirmed/Inferred/Assumed/Unresolved). Missing source references on Confirmed entries trigger a
  CONSTITUTIONAL_HALT.

  The Full Pipeline

  MANUAL PLACEMENT                     STEP 0 (deterministic)           PHASE 1 (Claude)
  ─────────────────                     ─────────────────────           ────────────────

  work_programmes/
    cluster_CL4.grouped.json ──┐
         (338+ KB)             │
                               ├──► call_slicer.py ──► .slice.json ──┐
  selected_call.json ──────────┘     (topic_code      (~5-8 KB)     │
    (topic_code,                      + work_programme                │
     work_programme,                  lookup)                         │
     instrument_type)                                                 ├──► call_analyzer agent
                                                                     │      │
  call_extracts/                                                     │      ├─ call-requirements-extraction ──► extracted/ (6 files)
    <topic>.json (curated) ─────────────────────────────────────────┘      ├─ evaluation-matrix-builder ──► Tier 4 eval matrix
                                                                            ├─ instrument-schema-normalization ──► Tier 2A schemas
                                                                            ├─ topic-scope-check ──► decision log
                                                                            └─ gate-enforcement ──► gate_result.json

  Most Important Inputs (ranked)

  1. selected_call.json — The trigger for everything. Without the topic_code and work_programme, nothing can resolve.
  2. Grouped work programme JSON (e.g., cluster_CL4.grouped.json) — The authoritative source material. Contains all call entries with their scope, outcomes, impacts, and eligibility
  conditions.
  3. Curated call extract (<topic>.json) — Supplements the raw work programme with structured interpretation.

  Most Important Workflow Elements (ranked)

  1. call_slicer.py — Deterministic Step 0 input bounding. Reduces 338–794 KB to ~5–8 KB. Runs before any Claude call.
  2. call-requirements-extraction skill — The skill that actually reads the sources and produces all six extracted files. Most complex skill in Phase 1.
  3. call_analyzer agent — Orchestrates Phase 1, sequences all five skills, handles failures.
  4. gate_01_source_integrity (entry gate) — Validates that all source materials exist before Phase 1 begins.
  5. phase_01_gate (exit gate) — Validates all six extracted files are non-empty with source references before Phase 2 can start.

  Downstream Consumption

  The six extracted files are consumed by virtually every subsequent phase:
  - Phase 2 (concept refinement) — aligns concept with expected_outcomes.json and scope_requirements.json
  - Phase 5 (impact architecture) — maps project outputs to expected_impacts.json using impact_id join keys
  - Phase 6 (implementation architecture) — governance-model-builder reads scope_requirements.json and call constraints
  - Phase 8 (drafting) — all three section drafting skills read extracted files for evaluator-oriented vocabulary

  
❯ In which phases and by which skill or agent are the metadata associated with the Tier 2B outputs produced by the Call Analyzer used?                                                          
                                                                                                                                       
  Searched for 2 patterns (ctrl+o to expand)                                                                                                                                                    
                                                                                                                                                                                                
● Explore(Trace Tier2B metadata consumption) Sonnet 4.6                                                                                                                                         
  ⎿  Done (18 tool uses · 133.2k tokens · 2m 24s)                          
  (ctrl+o to expand)                                                                                                                                                                            
                                                                                                                                                                                                
● Here is the complete trace of how each Tier 2B metadata field is consumed downstream:                                                                                                         
                                                                                                                                                                                                
  ---                                                                                                                                                                                           
  Phase 2 — Concept Refinement                                                                                                                                                                  
                                                                                                                                                                                                
  concept-alignment-check skill                                                                                                                                                                 
                                                                                                                                                                                                
  ┌─────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────────────┬────────────────────────────────────────────────┐   
  │        Tier 2B File         │                                               Fields Read                                                │                     Usage                      │   
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
  │ expected_outcomes.json      │ outcome_id — required coverage key: builds set A = {all outcome_ids}, enforces every one has a           │ Coverage completeness enforcement              │
  │                             │ topic_mapping_rationale entry; gaps → INCOMPLETE_OUTPUT                                                  │                                                │
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
  │                             │ description — parsed for key noun phrases; matched (exact or synonym) against concept corpus             │ Vocabulary alignment verification              │
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
  │                             │ source_section, source_document — copied into tier2b_source_ref on each rationale entry                  │ Traceability stamping                          │
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
  │                             │ status — if "Unresolved", forces the alignment judgment to "Unresolved"                                  │ Status propagation                             │
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
  │ scope_requirements.json     │ requirement_id — key in scope_coverage entries (prefixed SR-xx)                                          │ Scope boundary set construction                │
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
  │                             │ description — content checked for concept coverage                                                       │ Scope match evaluation                         │
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
  │                             │ mandatory — fail-closed: any mandatory element missing from coverage → "unresolved"                      │ Mandatory coverage gate                        │
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
  │                             │ source_section, source_document — into tier2b_source_ref                                                 │ Traceability                                   │
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
  │ call_constraints.json       │ constraint_id — key in scope_coverage entries (prefixed CC-xx)                                           │ Constraint tracking                            │
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
  │                             │ description — scanned for ethics, gender, open science signals                                           │ Compliance flag extraction                     │
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
  │                             │ constraint_type — "scope" type + ethics mentions → ethics_review_required: true                          │ Compliance profile seeding                     │
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
  │                             │ source_section — into tier2b_source_ref                                                                  │ Traceability                                   │
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
  │ eligibility_conditions.json │ condition_id, description, condition_type — checked for contradictions with project concept              │ Conservative default: absent →                 │
  │                             │                                                                                                          │ eligibility_confirmed = false                  │
  └─────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────────┴────────────────────────────────────────────────┘

  concept-call-binding-derivation skill

  ┌─────────────────────────────┬──────────────────────────────────────────────────────────────────────────────┬────────────────────────────────────────────────────────────────────────────┐
  │        Tier 2B File         │                                 Fields Read                                  │                                   Usage                                    │
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────┤
  │ expected_outcomes.json      │ outcome_id — completeness check: every outcome_id must appear in derived     │ Mechanical completeness verification                                       │
  │                             │ mappings array; gap → INCOMPLETE_OUTPUT                                      │                                                                            │
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────┤
  │ call_constraints.json       │ constraint_type, description — scanned for ethics/gender/open science        │ Derives ethics_review_required, gender_plan_required,                      │
  │                             │ signals                                                                      │ open_science_requirements in compliance_profile.json                       │
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────┤
  │ scope_requirements.json     │ description — scanned for gender equality, FAIR principles, open science     │ Supplements compliance profile derivation                                  │
  │                             │ mentions                                                                     │                                                                            │
  ├─────────────────────────────┼──────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────────────────────────────────┤
  │ eligibility_conditions.json │ condition_id, description — checked for explicit contradictions by the       │ Derives eligibility_confirmed boolean (true/false)                         │
  │                             │ concept                                                                      │                                                                            │
  └─────────────────────────────┴──────────────────────────────────────────────────────────────────────────────┴────────────────────────────────────────────────────────────────────────────┘

  topic-scope-check skill (also used in Phase 1)

  ┌─────────────────────────┬───────────────────────────────────────────────────────────────────────────┬──────────────────────────────────────────────────────────┐
  │      Tier 2B File       │                                Fields Read                                │                          Usage                           │
  ├─────────────────────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────┤
  │ scope_requirements.json │ requirement_id — stored as scope_element_ref in each scope_findings entry │ Scope boundary set authority                             │
  ├─────────────────────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────┤
  │                         │ description — builds scope boundary set                                   │ Match evaluation against submitted claims                │
  ├─────────────────────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────┤
  │                         │ mandatory/boundary_type — governs how each requirement is scored          │ excluded_topic → out-of-scope override                   │
  ├─────────────────────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────┤
  │                         │ source_section — into tier2b_source_refs and tier_authority_applied       │ Traceability                                             │
  ├─────────────────────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────┤
  │ call_constraints.json   │ constraint_id — stored as constraint_ref in each finding                  │ Constraint violation tracking                            │
  ├─────────────────────────┼───────────────────────────────────────────────────────────────────────────┼──────────────────────────────────────────────────────────┤
  │                         │ description — excluded-activity matching against submitted content        │ Out-of-scope override if claim matches excluded activity │
  └─────────────────────────┴───────────────────────────────────────────────────────────────────────────┴──────────────────────────────────────────────────────────┘

  ---
  Phase 5 — Impact Architecture

  impact-pathway-mapper skill

  ┌────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┬──────────────────────────────┐
  │      Tier 2B File      │                                                           Fields Read                                                           │            Usage             │
  ├────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────────────────────┤
  │ expected_impacts.json  │ impact_id — primary required coverage key: every impact_id must appear in at least one impact_pathways entry; uncovered →       │ Mandatory mapping set        │
  │                        │ INCOMPLETE_OUTPUT                                                                                                               │                              │
  ├────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────────────────────┤
  │                        │ description — subject-matter alignment matching to project impacts                                                              │ Pathway construction driver  │
  ├────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────────────────────┤
  │                        │ source_section, source_document — into tier2b_source_ref on each pathway entry                                                  │ Traceability                 │
  ├────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────────────────────┤
  │ expected_outcomes.json │ outcome_id — lookup map for intermediate pathway nodes                                                                          │ Pathway node enrichment      │
  ├────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼──────────────────────────────┤
  │                        │ description — narrative use                                                                                                     │ Intermediate outcome         │
  │                        │                                                                                                                                 │ placement                    │
  └────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┴──────────────────────────────┘

  impact-pathway-core-builder skill

  ┌────────────────────────┬────────────────────────────────────────────────────────────────────────────────┬────────────────────────────────────────────────┐
  │      Tier 2B File      │                                  Fields Read                                   │                     Usage                      │
  ├────────────────────────┼────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
  │ expected_impacts.json  │ impact_id — required coverage set (same as mapper)                             │ Every impact_id must appear in impact_pathways │
  ├────────────────────────┼────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
  │                        │ description, source_section — matching and traceability                        │ Pathway construction                           │
  ├────────────────────────┼────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────────────────┤
  │ expected_outcomes.json │ outcome_id, description — intermediate pathway nodes via linked_wp_ids overlap │ Pathway node enrichment                        │
  └────────────────────────┴────────────────────────────────────────────────────────────────────────────────┴────────────────────────────────────────────────┘

  dissemination-exploitation-communication-check skill

  ┌───────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────┬─────────────────────────────┐
  │     Tier 2B File      │                                               Fields Read                                               │            Usage            │
  ├───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │ expected_impacts.json │ impact_id — builds call_dec_requirements_list (those impacts whose description mentions DEC activities) │ DEC requirement enumeration │
  ├───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │                       │ description — identifies which impacts require specific DEC activities                                  │ Subject-matter matching     │
  ├───────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────────────┤
  │                       │ source_section — into tier2b_source_ref on flagged findings                                             │ Traceability                │
  └───────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────┴─────────────────────────────┘

  impact_architect agent

  ┌──────────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────────┬───────────────────────────────────────────────┐
  │           Tier 2B File           │                                             Fields Read                                              │                     Usage                     │
  ├──────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────┤
  │ expected_impacts.json            │ Passed to pathway skills; impact_id coverage enforced by all_impacts_mapped predicate                │ Agent-level coverage gate                     │
  ├──────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────┤
  │ expected_outcomes.json           │ Passed to pathway skills for intermediate node enrichment                                            │ Context passing                               │
  ├──────────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────┤
  │ evaluation_priority_weights.json │ criterion_id, weight — used to prioritise which expected impacts receive more prominent narrative    │ Narrative weighting signal (not structural    │
  │                                  │ treatment                                                                                            │ join)                                         │
  └──────────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────┴───────────────────────────────────────────────┘

  ---
  Phase 6 — Implementation Architecture

  governance-model-builder skill

  ┌─────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────┬───────────────────────────────────────────────────────────┐
  │      Tier 2B File       │                                        Fields Read                                        │                           Usage                           │
  ├─────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────┤
  │ call_constraints.json   │ constraint_id — cited in source_basis fields and traceability_footer.primary_sources      │ Tier 2B traceability guard                                │
  ├─────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────┤
  │                         │ description — consulted to confirm/deny call-specific mandate claims before sourcing them │ Evidence check before assertion                           │
  ├─────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────┤
  │                         │ constraint_type, source_section — classification and citation                             │ Attribution                                               │
  ├─────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────────────┤
  │ scope_requirements.json │ requirement_id, description, mandatory, source_section — same traceability guard pattern  │ Confirms scope mandates at tier 2 before attributing them │
  └─────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────┴───────────────────────────────────────────────────────────┘

  ---
  Phase 8 — Drafting and Review

  excellence-section-drafting skill

  ┌─────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┬───────────────────────┐
  │      Tier 2B File       │                                                          Fields Read                                                           │         Usage         │
  ├─────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────┤
  │ expected_outcomes.json  │ outcome_id, description — vocabulary sourcing; reinforces traceability claims in validation_status.claim_statuses[].source_ref │ Vocabulary grounding  │
  ├─────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────┤
  │ expected_impacts.json   │ impact_id, description — contextual grounding for excellence section language alignment                                        │ Supplementary context │
  ├─────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────┤
  │ scope_requirements.json │ requirement_id, description — Excellence section claims checked against call scope boundaries                                  │ Scope compliance      │
  └─────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┴───────────────────────┘

  impact-section-drafting skill

  ┌────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┬─────────────────────┐
  │      Tier 2B File      │                                                               Fields Read                                                                │        Usage        │
  ├────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────┤
  │ expected_impacts.json  │ impact_id — coverage verification: every call expected impact must have a corresponding pathway in impact_architecture.json; unmapped →  │ Coverage audit      │
  │                        │ recorded in validation_status                                                                                                            │                     │
  ├────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────┤
  │                        │ description — vocabulary for Impact section prose                                                                                        │ Vocabulary sourcing │
  ├────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────────┤
  │ expected_outcomes.json │ outcome_id, description — supporting context for pathway construction narrative                                                          │ Supplementary       │
  │                        │                                                                                                                                          │ context             │
  └────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┴─────────────────────┘

  implementation-section-drafting skill

  ┌─────────────────────────┬───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┬───────────────────────┐
  │      Tier 2B File       │                                                              Fields Read                                                              │         Usage         │
  ├─────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────┤
  │ call_constraints.json   │ constraint_id — when CC-* identifiers appear in drafted text, the source file must be cited in traceability_footer.primary_sources    │ Traceability          │
  │                         │ with tier: 2                                                                                                                          │ anchoring             │
  ├─────────────────────────┼───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────┤
  │ scope_requirements.json │ requirement_id — same pattern: SR-* identifiers require source file citation                                                          │ Traceability          │
  │                         │                                                                                                                                       │ anchoring             │
  └─────────────────────────┴───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┴───────────────────────┘

  ---
  Phase 1 — Evaluation Matrix (internal consumption)

  evaluation-matrix-builder skill

  ┌──────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┬────────────────────────────────────┐
  │           Tier 2B File           │                                                   Fields Read                                                   │               Usage                │
  ├──────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────┤
  │ evaluation_priority_weights.json │ criterion_id — join key against the evaluation form's criterion identifiers; each matched entry gets its weight │ Weight overlay onto evaluation     │
  │                                  │  overlaid                                                                                                       │ matrix                             │
  ├──────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────┤
  │                                  │ weight — overwrites the matrix entry's weight; weight_source stamped as                                         │ Authoritative weight source        │
  │                                  │ "tier2b_evaluation_priority_weights.json"                                                                       │                                    │
  ├──────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼────────────────────────────────────┤
  │                                  │ Non-null weights in the output matrix MUST originate from this file; prior-knowledge weights →                  │ Constitutional enforcement         │
  │                                  │ CONSTRAINT_VIOLATION                                                                                            │                                    │
  └──────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────────────────────────────┴────────────────────────────────────┘

  ---
  Summary: Metadata Field Usage Patterns

  ┌────────────────────────────────┬────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┬───────────────┐
  │             Field              │                                                             Usage Pattern                                                              │   Primary     │
  │                                │                                                                                                                                        │    Phases     │
  ├────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────┤
  │ outcome_id                     │ Required coverage key (Phase 2), intermediate pathway node key (Phase 5), vocabulary anchor (Phase 8)                                  │ 2, 5, 8       │
  ├────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────┤
  │ impact_id                      │ Required coverage key (Phase 5), DEC check key (Phase 5), coverage audit (Phase 8)                                                     │ 5, 8          │
  ├────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────┤
  │ constraint_id / requirement_id │ Scope boundary enforcement (Phase 1/2), compliance profile derivation (Phase 2), traceability guard (Phase 6), traceability anchoring  │ 1, 2, 6, 8    │
  │                                │ (Phase 8)                                                                                                                              │               │
  ├────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────┤
  │ condition_id                   │ Conservative eligibility gate (Phase 2 only)                                                                                           │ 2             │
  ├────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────┤
  │ criterion_id                   │ Evaluation matrix weight overlay (Phase 1), narrative prioritisation (Phase 5)                                                         │ 1, 5          │
  ├────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────┤
  │ description                    │ Vocabulary matching, subject-matter alignment, compliance signal extraction                                                            │ All phases    │
  ├────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────┤
  │ source_section +               │ tier2b_source_ref stamping, traceability_footer.primary_sources citation, source_basis population                                      │ All phases    │
  │ source_document                │                                                                                                                                        │               │
  ├────────────────────────────────┼────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────┤
  │ status                         │ Status propagation (Unresolved forces downstream Unresolved), conservative defaults (absent → false)                                   │ 2, 5          │
  └────────────────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┴───────────────┘

  The two most architecturally significant metadata fields are outcome_id and impact_id — they serve as cross-phase join keys that enforce end-to-end traceability from call requirements
  through to drafted proposal sections. The source_section/source_document pair is the most widely consumed metadata, appearing in every phase that reads any Tier 2B file.

  ❯ What is the purpose of using the Predicate Modules  (in runner/predicates/) for the DAG runner?                                                                                               
                                                                                                  
  Searched for 2 patterns, read 3 files (ctrl+o to expand)                                                                                                                                      
                                                                                                                                                                                                
● Now let me read a few representative predicate modules to show the range of what they do.                                                                                                     
                  
  Read 3 files (ctrl+o to expand)                                                                                                                                                               
                                                                                                                                                                                                
● Purpose of the Predicate Modules                                                                                                                                                              
                                                                                                                                                                                                
  The predicate modules serve as the deterministic verification layer of the gate evaluation system. Here's how they fit into the architecture:                                                 
                                                                                                                                                                                                
  Core Design Principle                                                                                                                                                                         
                                                                                                                                                                                                
  Gates control phase progression (CLAUDE.md §6: "Gates are mandatory"). Every gate is composed of predicates — atomic, stateless Python functions that inspect artifacts on disk and return a
  uniform PredicateResult(passed, failure_category, reason, details). Predicates are the mechanism by which gate conditions defined in the workflow specification become executable, testable,
  deterministic checks.

  The key architectural insight is the separation of concerns:

  ┌──────────────────────┬────────────────────────────────────┬──────────────────────────┐
  │       Concern        │           Responsibility           │         Location         │
  ├──────────────────────┼────────────────────────────────────┼──────────────────────────┤
  │ What must be checked │ Gate rules library YAML + manifest │ .claude/workflows/       │
  ├──────────────────────┼────────────────────────────────────┼──────────────────────────┤
  │ How to check it      │ Predicate functions                │ runner/predicates/       │
  ├──────────────────────┼────────────────────────────────────┼──────────────────────────┤
  │ When to check it     │ DAG scheduler dispatch             │ runner/dag_scheduler.py  │
  ├──────────────────────┼────────────────────────────────────┼──────────────────────────┤
  │ Recording the result │ Gate evaluator                     │ runner/gate_evaluator.py │
  └──────────────────────┴────────────────────────────────────┴──────────────────────────┘

  Evaluation Flow

  gate_rules_library.yaml         manifest.compile.yaml
          │                              │
          │  predicate definitions       │  predicate_refs per gate
          └──────────┬───────────────────┘
                     ▼
           gate_evaluator.evaluate_gate()
                     │
                     │  PREDICATE_REGISTRY lookup
                     ▼
           predicate function(path, ..., repo_root=...)
                     │
                     ▼
           PredicateResult(passed, failure_category, reason, details)
                     │
                     ▼
           GateResult JSON → Tier 4

  The gate evaluator collects all predicate failures (no fast-fail) and writes a complete GateResult to Tier 4.

  Predicate Type Hierarchy (Mandatory Evaluation Order)

  The modules are organized by type, and the gate evaluator enforces strict evaluation ordering:

  ┌───────┬────────────┬──────────────────────────┬───────────────────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────────┐
  │ Order │    Type    │          Module          │                      What it checks                       │                                   Example                                   │
  ├───────┼────────────┼──────────────────────────┼───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ 0     │ file       │ file_predicates.py       │ Does the artifact exist? Is it non-empty? Is it valid     │ exists, non_empty_json, artifact_owned_by_run                               │
  │       │            │                          │ JSON? Is the run_id current?                              │                                                                             │
  ├───────┼────────────┼──────────────────────────┼───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ 1     │ gate_pass  │ gate_pass_predicates.py  │ Has a prerequisite gate already passed?                   │ gate_pass_recorded — checks if an upstream gate result has status: "pass"   │
  ├───────┼────────────┼──────────────────────────┼───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ 2     │ schema     │ schema_predicates.py     │ Does the artifact contain required fields? Are            │ risk_register_populated, ethics_assessment_explicit,                        │
  │       │            │                          │ domain-specific structural requirements met?              │ budget_gate_confirmation_present                                            │
  ├───────┼────────────┼──────────────────────────┼───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ 3     │ source_ref │ source_ref_predicates.py │ Does every extracted item carry a traceable source        │ source_refs_present (Tier 2B files), all_mappings_have_source_refs (topic   │
  │       │            │                          │ reference?                                                │ mapping)                                                                    │
  ├───────┼────────────┼──────────────────────────┼───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ 4     │ coverage   │ coverage_predicates.py   │ Do cross-artifact join keys align? Are all required       │ all_impacts_mapped (every expected impact has a pathway),                   │
  │       │            │                          │ elements present across paired artifacts?                 │ all_partners_in_tier3 (WP partners exist in consortium)                     │
  ├───────┼────────────┼──────────────────────────┼───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ 5     │ cycle      │ cycle_predicates.py      │ Are there circular dependencies in the WP structure?      │ no_dependency_cycles                                                        │
  ├───────┼────────────┼──────────────────────────┼───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ 6     │ timeline   │ timeline_predicates.py   │ Does the timeline fit within duration limits? Do          │ timeline_within_duration, all_milestones_have_criteria                      │
  │       │            │                          │ milestones have verifiable criteria?                      │                                                                             │
  ├───────┼────────────┼──────────────────────────┼───────────────────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────────┤
  │ 7     │ semantic   │ (not in predicates/)     │ Claude-evaluated content quality checks                   │ Dispatched via semantic_dispatch.py — only runs if all deterministic        │
  │       │            │                          │                                                           │ predicates pass                                                             │
  └───────┴────────────┴──────────────────────────┴───────────────────────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────────┘

  This ordering is deliberate: cheaper/faster checks run first. If a file doesn't exist (type 0), there's no point checking its schema (type 2) or cross-artifact coverage (type 4). Semantic
  checks (type 7, which invoke Claude) are skipped entirely if any deterministic predicate fails — saving cost and latency.

  The Five Failure Categories

  Every failing predicate must classify its failure into exactly one category (enforced by PredicateResult.__post_init__):

  ┌──────────────────────────────┬──────────────────────────────────────────────────────────────────────────────────────────────────┬───────────────────────────────────────────────────┐
  │           Category           │                                             Meaning                                              │                  Operator Action                  │
  ├──────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────┤
  │ MISSING_MANDATORY_INPUT      │ Required artifact absent                                                                         │ Supply the artifact, re-run the producing phase   │
  ├──────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────┤
  │ MALFORMED_ARTIFACT           │ Artifact exists but structurally wrong (bad JSON, missing fields, wrong type)                    │ Regenerate the artifact                           │
  ├──────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────┤
  │ CROSS_ARTIFACT_INCONSISTENCY │ Content mismatch between two artifacts (e.g., WP references a partner not in Tier 3)             │ Identify which artifact is wrong, fix it          │
  ├──────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────┤
  │ POLICY_VIOLATION             │ Structurally valid but violates a constitutional/workflow rule (e.g., missing source references) │ Review agent behaviour, correct, re-run           │
  ├──────────────────────────────┼──────────────────────────────────────────────────────────────────────────────────────────────────┼───────────────────────────────────────────────────┤
  │ STALE_UPSTREAM_MISMATCH      │ Artifact's run_id doesn't match current run, and not approved in reuse policy                    │ Re-run upstream phase or register in reuse policy │
  └──────────────────────────────┴──────────────────────────────────────────────────────────────────────────────────────────────────┴───────────────────────────────────────────────────┘

  These categories are the primary triage signal for the human operator — they tell you not just that a gate failed, but why and what to do about it.

  Why Predicates Instead of Inline Checks

  1. Testability — Each predicate is a pure function: same inputs → same result. The test suite can verify predicates in isolation without needing a running scheduler or Claude invocations.
  2. Composability — Gate conditions are composed from predicates in YAML (gate_rules_library.yaml + manifest.compile.yaml), not in code. This means gate logic can be reviewed, modified, and
  audited without changing Python.
  3. Collect-all-failures — The gate evaluator runs every predicate and collects all failures rather than stopping at the first one. This gives the operator a complete diagnostic picture in a
  single gate evaluation.
  4. Determinism — Predicates read only from disk. They don't depend on agent memory, cached state, or prior run context (except artifact_owned_by_run which reads run_id from the artifact
  itself). This satisfies CLAUDE.md §6 rule 4: "Reruns are deterministic."
  5. Constitutional enforcement at the runtime layer — The predicates mechanically enforce constitutional rules that would otherwise depend on agent compliance. For example,
  source_refs_present enforces CLAUDE.md §10.5 (traceability) without relying on the skill to self-police. The gate will block regardless of what the agent produced.
  6. Separation from Claude — Deterministic predicates never invoke Claude. This means gate evaluation cost is near-zero for the 7 deterministic types, with Claude only called for semantic
  predicates and only when all deterministic checks pass.