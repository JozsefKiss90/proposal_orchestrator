# MAESTRO — Strategic Positioning

## Differentiation within the Call Scope

### Call Scope Alignment

The topic HORIZON-CL4-2026-05-DIGITAL-EMERGING-02 calls for research on next-generation AI agents with advances in planning, reasoning, memory management, and multi-agent coordination. MAESTRO addresses all four areas as an integrated research programme rather than treating them as independent work streams. This integrated design is the project's primary differentiator.

### Positioning Against the Expected Outcomes

The call specifies two expected outcomes:

1. **Significant improvements in the autonomy, robustness and reliability of AI agents through advanced planning mechanisms, memory management, and reasoning capabilities.** — MAESTRO addresses this through Pillars 1 (neuro-symbolic planning and reasoning) and 2 (adaptive memory architecture), unified by the External Tool and API Orchestration Layer. The neuro-symbolic approach is distinctive because it provides formal guarantees (verifiable sub-task decomposition, plan monitoring with provable recovery) that pure LLM-based approaches cannot offer, while retaining the flexibility of neural methods. The tool orchestration layer directly enhances agent reliability by grounding reasoning in verified external data and providing principled fallback/recovery mechanisms for tool failures — addressing the call's essential requirement (SR-04) that integration of external tools and APIs is necessary to overcome limitations of large AI models and enhance agent performance in tasks requiring accuracy and reliability.

2. **Innovative multi-agent frameworks and protocols demonstrating effective decentralised coordination and collaboration among multiple AI agents beyond the capabilities of individual agents.** — MAESTRO addresses this through Pillar 3 (decentralised multi-agent coordination). The approach is distinctive because it develops formally specified delegation and negotiation protocols with convergence guarantees, rather than relying on ad-hoc LLM-based agent communication patterns. The External Tool and API Orchestration Layer extends multi-agent capability by governing shared tool access, delegated tool invocation, and conflict resolution when multiple agents require the same external resource.

### Positioning Against the State of the Art

Current AI agent research is concentrated in three largely disconnected communities:

- **LLM-based agents** (e.g., ReAct, AutoGPT-style systems): Strong on natural language task understanding but weak on long-horizon planning robustness and memory management. Plans degrade over extended task sequences.
- **Classical planning and multi-agent systems**: Strong on formal guarantees but weak on handling the ambiguity and open-endedness of real-world natural language tasks.
- **Memory-augmented neural systems**: Focused on retrieval augmentation for single-turn accuracy but lacking integration with planning and coordination.

MAESTRO's distinctive contribution is the co-design of these three capabilities into a unified architecture. The neuro-symbolic planning engine uses the memory architecture to maintain coherence over long horizons, while the multi-agent protocol uses both planning and memory to coordinate agents with heterogeneous capabilities. This integration is not achievable by combining off-the-shelf components from the three communities.

### Positioning Within the Apply AI Sectors

The call expects proposals to demonstrate application in at least one Apply AI sector, with three specifically identified portfolio-priority sectors: healthcare, advanced manufacturing, and in-vehicle autonomous driving (SR-07). The portfolio coverage mechanism (CC-10) is designed to ensure at least one funded proposal per sector.

MAESTRO validates directly in **two** of the three call-identified Apply AI sectors:

- **Healthcare** (call-identified sector): Clinical decision support requires agents that reason under uncertainty, integrate information from heterogeneous sources via the External Tool and API Orchestration Layer (HL7 FHIR connectors, diagnostic knowledge bases, imaging analysis APIs), and coordinate specialist reasoning — exercising all three MAESTRO pillars and the tool orchestration capability simultaneously.
- **Advanced manufacturing** (call-identified sector): Process optimisation requires real-time multi-agent coordination with shared state, exercising Pillars 2 and 3 under hard timing constraints, with the tool orchestration layer managing OPC-UA industrial connectors, digital twin APIs, and sensor data streams.

MAESTRO additionally validates in **logistics and supply chain operations** as a **cross-sector transfer demonstrator** that confirms the architecture's portability and generalisation capability beyond the minimum sector requirement:

- **Logistics** (cross-sector transfer): Supply chain planning requires long-horizon planning with multiple autonomous actors and disruption recovery, exercising Pillars 1 and 3 at scale with tool orchestration managing logistics tracking, customs clearance, and carrier scheduling APIs.

This positioning is strategically honest: MAESTRO does not claim to address in-vehicle autonomous driving as a demonstrator sector, as the current consortium does not include automotive sector partners. However, the MAESTRO architecture — with its real-time multi-agent coordination, verified planning under safety constraints, and external tool/API integration (including sensor APIs and V2X communication interfaces) — is architecturally transferable to autonomous driving settings, and the project includes a targeted architectural mapping analysis (WP8) assessing this transferability. The three-domain validation strategy (two call-identified sectors plus one transfer sector) demonstrates that MAESTRO's research advances are generalisable capabilities, not domain-specific artifacts, while providing strong coverage of the call's Apply AI portfolio logic through healthcare and advanced manufacturing.

### Positioning Against SR-04 — External Tools and APIs

The call mandates integration of external tools and APIs as an essential required element to overcome limitations of large AI models (SR-04). MAESTRO addresses this requirement through a dedicated **External Tool and API Orchestration Layer** that is architecturally central — not an afterthought. The layer provides: a typed tool registry with capability models; formal tool selection and invocation policies integrated with the neuro-symbolic planning engine; standardised API adapters abstracting heterogeneous protocols; post-invocation verification and grounding; execution monitoring with fallback/recovery; and auditable tool execution traces stored in the adaptive memory architecture. This cross-cutting capability is a genuine research-and-engineering contribution that distinguishes MAESTRO from agent architectures that treat tool use as a simple function-calling interface.

### Consortium Positioning

The MAESTRO consortium combines:
- Leading European AI research institutions with track records in neuro-symbolic AI, multi-agent systems, memory-augmented learning, and tool-augmented agent architectures.
- Sector-specific industry partners in healthcare, manufacturing, and logistics who will co-design demonstrators and provide real deployment environments with domain-specific tool and API ecosystems.
- A technology transfer partner to ensure framework adoption through the AI-on-demand platform and EDIHs.

This composition ensures that research outputs are validated against real industry needs and positioned for post-project exploitation. The consortium's sector coverage directly addresses healthcare and advanced manufacturing as call-identified Apply AI sectors, with logistics providing additional evidence of cross-sector transferability.

### Risks Addressed by the Positioning

- **Risk of producing yet another LLM wrapper framework**: Mitigated by the neuro-symbolic approach and the principled External Tool and API Orchestration Layer, which together produce architecturally distinct planning and tool-integration capabilities with formal properties that differentiate MAESTRO from prompt-engineering-based agent tools and simple function-calling wrappers.
- **Risk of research-only output without deployment pathway**: Mitigated by co-design with industry partners and validation in operational environments at TRL 5 across two call-identified Apply AI sectors plus a transfer sector.
- **Risk of fragmented research across pillars**: Mitigated by the co-design architecture, where all three pillars and the tool orchestration layer share common data representations, evaluation benchmarks, and integration interfaces from the start.
- **Risk of weak SR-04 compliance**: Mitigated by making external tool and API integration an explicit, named, architecturally central cross-cutting capability with dedicated research tasks — not a cosmetic addition.
