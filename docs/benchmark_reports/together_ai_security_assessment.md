# Together AI Security Assessment

Provider security qualification matrix for Together AI, assessed against Proposal Orchestrator backend requirements.

Sources:
- Together AI documentation (`together.txt`)
- Together AI Privacy Policy (updated December 17, 2025)

---

## Security Matrix

| Requirement | Required by Proposal Orchestrator | Pass/Gap | Together AI Evidence |
|---|---:|---|---|
| Zero data retention | Mandatory | PASS | Privacy Policy S2.6: ZDR available via Settings > Privacy & Security. Under ZDR, prompts, inputs, and outputs are not stored, retained, or used for training, product improvement, or any secondary purpose. ZDR applies from the moment it is enabled; data is removed as soon as processing concludes. |
| Training opt-out default | Mandatory | PASS | Privacy Policy S1 and S2.2: "We do not use any data collected from you to train our models without your explicit opt-in and consent." Training is opt-in only; no customer action is required to prevent training use. |
| Data residency controls | Preferred/Institutional | GAP | No data residency, region selection, or geographic data-placement controls are documented in the API docs or the Privacy Policy. S2.5 states data may be transferred to and maintained on computers outside your jurisdiction. Requires enterprise contract inquiry. |
| Private networking / VPC / PrivateLink | Preferred | GAP | Not documented. Dedicated endpoints provide reserved hardware but are accessed via the public `api.together.ai` endpoint. No VPC peering, PrivateLink, or private networking options are described in the available documentation. Requires enterprise/sales inquiry. |
| API key scope isolation | Mandatory | PARTIAL | API keys are scoped per project (`settings/projects/~current/api-keys`). Rate limits are per organization per model. However, no evidence of fine-grained permission scoping (e.g., read-only keys, model-restricted keys, or endpoint-restricted keys) in available documentation. |
| Auditability | Mandatory | PARTIAL | Per-project cost analytics page available (`settings/projects/~current/cost-analytics`). API responses include `prompt_tokens`, `completion_tokens`, `total_tokens` in the `usage` field. Helicone observability integration documented for request-level logging. No dedicated audit log or compliance audit trail feature documented. |
| OpenAI-compatible API | Mandatory | PASS | Explicitly documented as drop-in OpenAI replacement. Requires only `base_url` and `api_key` change. Full endpoint compatibility matrix provided: `chat.completions.create`, tools, structured outputs, embeddings, vision all supported. OpenAI-shaped error objects returned. |
| Structured outputs/function support | Mandatory | PASS | Function calling (`tools` + `tool_choice`) and structured outputs (`response_format`) are both supported via `chat.completions.create`. Confirmed in the OpenAI compatibility matrix. Multiple serverless chat models show "Function calling: Yes" and "Structured outputs: Yes" in the model catalog (e.g., Llama 3.3 70B, Qwen3.5, DeepSeek-V4-Pro). |
| Model routing transparency | Preferred | PASS | Model IDs are explicit and namespaced (`<provider>/<model_name>`). Caller selects the exact model per request. Dedicated endpoints serve a single model on reserved hardware. No opaque model routing or silent model substitution described. |
| Contractual DPA availability | Mandatory institutional requirement | GAP | No Data Processing Agreement (DPA) or DPA availability is mentioned in the Privacy Policy or the API documentation. Privacy Policy S2.3 describes sharing with service providers, third-party vendors, and business partners. DPA availability must be confirmed via sales/legal contact. |
| GDPR posture | Mandatory institutional requirement | PARTIAL | Privacy Policy S6 provides supplemental terms for the EEA, Switzerland, and the UK. Legal bases for processing are described (consent, contractual necessity, legitimate interest). However, no explicit GDPR compliance certification, no named EU representative, and no subprocessor list are published in the available documentation. |
| Data outflow prevention compatibility | Mandatory | PARTIAL | ZDR (S2.6) prevents server-side storage of prompts and responses after processing. However, all API traffic transits the public internet to `api.together.ai`. No VPC or private networking is documented, so data-in-transit crosses organizational network boundaries. Dedicated endpoints reduce shared-infrastructure risk but do not eliminate public-internet exposure. |

---

## Summary

| Verdict | Count | Requirements |
|---------|------:|---|
| PASS | 5 | Zero data retention, Training opt-out default, OpenAI-compatible API, Structured outputs/function support, Model routing transparency |
| PARTIAL | 4 | API key scope isolation, Auditability, GDPR posture, Data outflow prevention compatibility |
| GAP | 3 | Data residency controls, Private networking / VPC / PrivateLink, Contractual DPA availability |

### Key Findings

- Together AI's core technical requirements (OpenAI compatibility, function calling, structured outputs, ZDR, training opt-out) are well-documented and pass cleanly.
- The institutional/security requirements (DPA, GDPR certification, data residency, private networking) have gaps that require enterprise/sales engagement to resolve. These are not necessarily blockers -- they may be available under enterprise contracts but are not publicly documented.
- The PARTIAL verdicts on API key scope isolation and auditability reflect missing fine-grained features (permission-scoped keys, dedicated audit logs) rather than fundamental architectural gaps.

### Actions Required Before Production Use

1. Contact Together AI sales to confirm DPA availability and terms.
2. Confirm GDPR posture details: EU representative, subprocessor list, data processing records.
3. Inquire about private networking / VPC options for dedicated endpoints.
4. Inquire about data residency controls (EU region placement).
5. Confirm API key permission scoping capabilities beyond per-project isolation.
6. Enable ZDR in account settings before any orchestration workload is routed to Together AI.
