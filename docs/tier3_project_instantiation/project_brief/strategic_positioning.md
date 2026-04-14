# MAESTRO — Strategic Positioning

## Differentiation within the Call Scope

### Call Scope Alignment

The topic HORIZON-CL4-2026-05-DIGITAL-EMERGING-02 calls for research on next-generation AI agents with advances in planning, reasoning, memory management, and multi-agent coordination. MAESTRO addresses all four areas as an integrated research programme rather than treating them as independent work streams. This integrated design is the project's primary differentiator.

### Positioning Against the Expected Outcomes

The call specifies two expected outcomes:

1. **Significant improvements in the autonomy, robustness and reliability of AI agents through advanced planning mechanisms, memory management, and reasoning capabilities.** — MAESTRO addresses this through Pillars 1 (neuro-symbolic planning and reasoning) and 2 (adaptive memory architecture). The neuro-symbolic approach is distinctive because it provides formal guarantees (verifiable sub-task decomposition, plan monitoring with provable recovery) that pure LLM-based approaches cannot offer, while retaining the flexibility of neural methods.

2. **Innovative multi-agent frameworks and protocols demonstrating effective decentralised coordination and collaboration among multiple AI agents beyond the capabilities of individual agents.** — MAESTRO addresses this through Pillar 3 (decentralised multi-agent coordination). The approach is distinctive because it develops formally specified delegation and negotiation protocols with convergence guarantees, rather than relying on ad-hoc LLM-based agent communication patterns.

### Positioning Against the State of the Art

Current AI agent research is concentrated in three largely disconnected communities:

- **LLM-based agents** (e.g., ReAct, AutoGPT-style systems): Strong on natural language task understanding but weak on long-horizon planning robustness and memory management. Plans degrade over extended task sequences.
- **Classical planning and multi-agent systems**: Strong on formal guarantees but weak on handling the ambiguity and open-endedness of real-world natural language tasks.
- **Memory-augmented neural systems**: Focused on retrieval augmentation for single-turn accuracy but lacking integration with planning and coordination.

MAESTRO's distinctive contribution is the co-design of these three capabilities into a unified architecture. The neuro-symbolic planning engine uses the memory architecture to maintain coherence over long horizons, while the multi-agent protocol uses both planning and memory to coordinate agents with heterogeneous capabilities. This integration is not achievable by combining off-the-shelf components from the three communities.

### Positioning Within the Apply AI Sectors

The call expects proposals to validate AI agent capabilities in real-world application domains. MAESTRO validates across three of the Apply AI Strategy's priority sectors:

- **Healthcare**: Clinical decision support requires agents that reason under uncertainty, integrate information from heterogeneous sources, and coordinate specialist reasoning — exercising all three MAESTRO pillars simultaneously.
- **Advanced manufacturing**: Process optimisation requires real-time multi-agent coordination with shared state, exercising Pillars 2 and 3 under hard timing constraints.
- **Logistics**: Supply chain planning requires long-horizon planning with multiple autonomous actors and disruption recovery, exercising Pillars 1 and 3 at scale.

This three-sector validation strategy ensures that MAESTRO's research advances are not domain-specific artifacts but generalisable capabilities.

### Consortium Positioning

The MAESTRO consortium combines:
- Leading European AI research institutions with track records in neuro-symbolic AI, multi-agent systems, and memory-augmented learning.
- Sector-specific industry partners in healthcare, manufacturing, and logistics who will co-design demonstrators and provide real deployment environments.
- A technology transfer partner to ensure framework adoption through the AI-on-demand platform and EDIHs.

This composition ensures that research outputs are validated against real industry needs and positioned for post-project exploitation.

### Risks Addressed by the Positioning

- **Risk of producing yet another LLM wrapper framework**: Mitigated by the neuro-symbolic approach, which produces architecturally distinct planning capabilities with formal properties that differentiate MAESTRO from prompt-engineering-based agent tools.
- **Risk of research-only output without deployment pathway**: Mitigated by co-design with industry partners and validation in operational environments at TRL 5.
- **Risk of fragmented research across pillars**: Mitigated by the co-design architecture, where all three pillars share common data representations, evaluation benchmarks, and integration interfaces from the start.
