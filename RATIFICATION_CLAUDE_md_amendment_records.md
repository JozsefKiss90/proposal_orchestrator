# Ratification Package — Insert-Ready `CLAUDE.md` §14 Amendment Records (C1–C3)

> **DRAFT FOR YOUR REVIEW. NOT APPLIED TO `CLAUDE.md`.**
> These are the literal amendment records that would be written into `CLAUDE.md`, formatted like the existing Section 17 records. Per §14.5, ratification is *your* explicit instruction; I will not transcribe any of these into `CLAUDE.md` until you say **"apply"** (naming which of C1/C2/C3).
>
> **How to ratify:** review the three records below → tell me which you adopt (all, a subset, or with edits) → I transcribe the adopted records into `CLAUDE.md` at the noted locations, run the §14.3 review (affected workflows/skills/agents) and the §14.4 consistency check, and report back. Only **C1–C3** need this; **W1** (the `assumed_claims_are_operator_declared` predicate) is workflow-level and needs building, not ratifying.
>
> **§14.4 consistency check (pre-checked):** none of C1–C3 contradicts another section. C1 preserves the §8.2/§8.3/§13.4 categorical block verbatim and only conditionalises the budget *source*; C2/C3 preserve §17.6 prohibitions (Python owns writes, scheduler owns gates) and §16.6 (agents are not authorities). No new contradiction is introduced; each change is additive or strengthening (§13.7-clean).

---

### Constitutional Amendment Record — Section 8 / Section 7 (C1: instrument-conditional budget gate)

*Placement: append after Section 8; add a cross-reference note at the Phase 7 gate condition in Section 7.*

| Field | Value |
|-------|-------|
| Section amended | §8.1; §8.4 (source/representation clauses); §7 Phase 7 gate condition (with a consequential cross-reference in §13.4). |
| Prior rule | §8.1: "This repository does not compute, estimate, or generate lump-sum budgets. Budget computation is exclusively the responsibility of the external Lump Sum Budget Planner system." §8.4/§7: the budget gate presumes a single validated **lump-sum response** present in `docs/integrations/lump_sum_budget_planner/received/`; Phase 7 "cannot be bypassed, deferred, or substituted with internally generated budget estimates"; Phase 8 is "fully blocked … until the budget gate passes … a blocking gate failure, not a hold state." |
| New rule | The budget gate is **instrument-conditional**. For **lump-sum instruments**, §8.1/§8.4/§7 stand unchanged (external planner, response in `received/`, categorical block). For **unit-cost instruments** (e.g. MSCA), the budget is **computed internally by deterministic derivation** from published unit costs — `confirmed_months(Phase 4) × published_rates(Tier 2B) × host_country_coefficient` — validated by a **byte-equal replay check**. §8.1's "does not compute" is scoped to lump-sum; §7's prohibition on "internally generated budget **estimates**" is preserved for lump-sum and clarified **not** to cover deterministic unit-cost **derivation** (which carries no judgment). The **categorical block is preserved verbatim**: `gate_09` passes only when **every** budget component — including host-dependent lines — resolves to Confirmed or operator-declared Assumed, and Phase 8 remains fully blocked until `gate_09` passes (§8.4/§13.4 unchanged). |
| Reason for change | §8 externalises lump-sum budgeting because lump-sum figures require **judgment** and are not replayable — externalisation is the anti-fabrication guarantee. Unit-cost budgets require no judgment (fixed arithmetic on published constants) and are verified by a byte-equal replay check, so **determinism supplies the equivalent anti-fabrication guarantee** and externalisation adds none, while blocking the §2 programme-agnostic mission. The change conditionalises the budget *source* to realise §2 agnosticism without weakening the categorical block (which would be a §13.7 violation and is unnecessary — a single operator host declaration resolves the one host-dependent line). |
| Impacted components | `runner/gate_evaluator.py` (`gate_09` instrument-conditional); a new deterministic **unit-cost budget deriver** (§17.5.3-class, per C2) + its byte-equal CI check; the `instrument_profile` resolver; `docs/integrations/lump_sum_budget_planner/**` (retained, lump-sum only); Tier 2B rate extraction (Stage 2, subject to §10.6); cross-references in §7, §8, §13.4. No change to the DAG scheduler, node-state machine, or gate-evaluation authority. |

---

### Constitutional Amendment Record — Section 17.5.3 (C2: deterministic node-body components)

*Placement: append after Section 17; it clarifies §17.5.3 and adds a field to §17.4.2.*

| Field | Value |
|-------|-------|
| Section amended | §17.5.3 (agent runtime role); consequential additive field in §17.4.2 (`AgentResult`). |
| Prior rule | §17.5.3: "The agent runtime (`run_agent()`) is an orchestration adapter that … sequences skill invocations through `run_skill()`, manages context passing between invocations, handles failure propagation, and determines `can_evaluate_exit_gate` from disk state. It does not perform domain reasoning itself." (The agent runtime does not invoke components that write canonical artifacts.) |
| New rule | The agent runtime may additionally invoke **deterministic, Claude-free composition components** within the node body — analogous to the Step-0 Call Slicer precedent but node-body-scoped — which read declared input artifacts and write canonical artifacts via `_atomic_write`. Such components perform **no domain reasoning and no inference**; each is closed by a determinism guarantee (byte-equal replay or pure lookup). Skill semantics (§17.5.1–.2) are **unchanged** — these are **not** skills (a skill is defined by Claude invocation). Artifact writes remain in Python; gate evaluation remains exclusively the scheduler's (§17.6.2); skills still may not invoke other skills (§17.6.4, unaffected). Each invocation is recorded in `AgentResult.invoked_components`. |
| Reason for change | Decomposed drafting composes bounded per-sub-section drafts into one section artifact, and unit-cost budgeting, canonical-pack generation, and assumption-application are deterministic transforms that must write canonical artifacts. Modelling these as "skills" would redefine the skill contract (§17.5.2 — `run_skill` has only Claude-invoking modes) and ripple through `SkillResult` and all skills. The Call Slicer already establishes deterministic non-Claude passes as §17-legitimate; this extends the pattern from Step 0 to the node body while preserving every runtime contract. |
| Impacted components | `runner/agent_runtime.py` (invokes components; new additive `AgentResult.invoked_components`); the four milestone-1 deterministic components — section assembler, assumption-applier, canonical-pack deriver, unit-cost budget deriver. No change to `run_skill()`, the DAG scheduler, or gate-evaluation authority. Requires §16.5 (C3) to bind these components in the manifest. |

---

### Constitutional Amendment Record — Section 16.5 (C3: bindable vocabulary)

*Placement: append after Section 16 (Agent Derivation and Execution Binding).*

| Field | Value |
|-------|-------|
| Section amended | §16.5. |
| Prior rule | §16.5: "The compiled workflow manifest defines the binding between: phases (nodes), agents, skills, gate conditions. This binding must not be overridden by agent implementations." |
| New rule | The bindable vocabulary is extended to include **deterministic components** (per §17.5.3, C2). A node body may declare a deterministic component in the manifest node spec; such a binding is a first-class, enumerated binding and does **not** constitute a non-enumerated-element inconsistency under §14.4. The rule that bindings must not be overridden by agent implementations is unchanged and now also governs deterministic-component bindings. |
| Reason for change | The deterministic components introduced by C2 must be declared in the manifest for §16.5 auditability ("binding must not be overridden by agent implementations"). The enumerated bindable set must therefore admit them, or declaring one would itself be an internal inconsistency (§14.4). |
| Impacted components | The compiled workflow manifest (node specs declaring deterministic components); §16.5 text; kept consistent with §17.5.3 (C2). |

---

## After you ratify

On your explicit "apply C1/C2/C3":

1. I transcribe the adopted records into `CLAUDE.md` at the placements noted (and add the cross-reference notes in §7/§13.4 for C1).
2. I run the **§14.3 review** — confirm `gate_09`, the affected skills/agents, and the manifest still comply with the amended text — and re-confirm the **§14.4** consistency check against the applied text.
3. I report the applied diff and the review result for your final look.
4. Only then does Stage 1 (purge) begin — and per your earlier steer, the first build increment is the **Excellence-only vertical slice**, not the full path.

*Nothing above is applied. Awaiting your explicit ratification instruction per §14.5.*
