# Proposed Constitutional Changes — Milestone 1 (MSCA-PF Honest-Run)

> **STATUS: DRAFT FOR RATIFICATION. NOT APPLIED.**
> Output of the milestone-1 `/grilling` session, reconciled with the shared-understanding Stage-0 ledger. Per `CLAUDE.md` §14.5 a constitutional amendment *"requires explicit human instruction"* and *"may not be made by agents, skills, or workflows operating autonomously."* Nothing here is written into `CLAUDE.md`. To enact: instruct explicitly which items to adopt; §14.3 then requires reviewing every affected workflow/skill/agent; §14.1 makes a change enacted by editing a workflow/skill *without* amending `CLAUDE.md` invalid.
>
> **Three items require §14 ratification** — **C1** §8 (budget, substantive), **C2** §17.5.3 and **C3** §16.5 (both clarifications). The β operator-declared-`Assumed` guardrail (**W1**) needs **no** amendment: it enforces §12.2's existing "explicitly declared" at the workflow level by *strengthening* a gate (§13.7 permits adding, forbids only weakening).

---

## Constitutional sign-off set — requires explicit §14.5 ratification

### C1 — §8 budget: instrument-conditional gate [substantive] (D12)

**Sections amended.** §8.1; §8.4 (source/representation clauses only); §7 Phase 7 gate condition.

**Prior rule.**
- §8.1: "This repository does not compute, estimate, or generate lump-sum budgets. Budget computation is exclusively the responsibility of the external Lump Sum Budget Planner system."
- §8.4 / §7: the gate presumes a single external lump-sum response in `…/received/`; Phase 7 "cannot be bypassed, deferred, or substituted with internally generated budget estimates"; Phase 8 is "fully blocked… until the budget gate passes… a blocking gate failure, not a hold state."

**New rule.**
- §8.1 scoped to lump-sum (externalised because lump-sum carries un-replayable *judgment*). For **unit-cost instruments** (MSCA), the budget is **computed internally by deterministic derivation** — `confirmed_months(Phase 4) × published_rates(Tier 2B) × host_country_coefficient` — validated by a **byte-equal replay check**. A derivation, not an estimate: no judgment.
- §8.4 / §7 make the budget **source** instrument-conditional (lump-sum → external planner; unit-cost → internal componentised derivation). The **categorical block is preserved verbatim**: `gate_09` passes only when every component — including the host-dependent living-allowance line — resolves to Confirmed or operator-declared Assumed. §7's ban on internal *estimates* is preserved for lump-sum and clarified to not cover deterministic unit-cost *derivation*.

**Reason.** §8 externalises lump-sum because judgment is un-replayable and externalisation is the anti-fabrication guarantee. Unit-cost carries no judgment, so **determinism supplies the equivalent guarantee** (byte-equal check) and externalisation buys zero anti-fabrication value while blocking §2 agnosticism. Source-conditionalisation finishes agnosticism; softening the block is unnecessary (β resolves the one host-dependent line) and would be a §13.7 weakening.

**Impacted.** `gate_evaluator.py` (`gate_09` conditional); the §17.5.3 unit-cost deriver + CI; `instrument_profile` resolver; `…/lump_sum_budget_planner/**` (retained, lump-sum only); Tier 2B rate extraction (Stage 2, §10.6). No change to scheduler, node-state machine, or gate authority.

### C2 — §17.5.3: agent runtime may invoke deterministic components [clarification] (D3, D11, D12, D13-r)

**Prior rule.** §17.5.3 casts the agent runtime as an orchestration adapter (sequences skills, manages context, determines `can_evaluate_exit_gate` from disk). It does not invoke components that *write* canonical artifacts.

**New rule.** The agent runtime may invoke **deterministic, Claude-free components** in the node body that write canonical artifacts via `_atomic_write` — analogous to the Step-0 Call Slicer precedent, but node-body-scoped. Writes stay in Python; gate evaluation stays with the scheduler; skills are untouched (§17.5.1–.2 unchanged — these are **not** skills, which are defined by Claude invocation). Each component is closed by a determinism guarantee (byte-equal or pure lookup).

**Reason.** Decomposed drafting + deterministic composition need a runtime home that isn't "skill." Call Slicer already establishes deterministic non-Claude passes as §17-legitimate; this extends the pattern from Step 0 to node-body composition, preserving every runtime contract.

**Impacted.** `agent_runtime.py` (invokes components; new `AgentResult.invoked_components`); the four deterministic components (below). `run_skill`, the scheduler, and gate-evaluation authority unchanged.

### C3 — §16.5: widen bindable vocabulary [clarification] (D11)

**Prior rule.** §16.5 binds `{phases (nodes), agents, skills, gate conditions}`.

**New rule.** Add **"deterministic components"** to the bindable set, so a node body may declare a deterministic component in the manifest without that binding being a non-enumerated-element inconsistency (§14.4).

**Reason.** The C2 components must be declared in the manifest node spec for §16.5 auditability ("binding must not be overridden by agent implementations"); the vocabulary must admit them.

**Impacted.** Manifest node specs; §16.5 text.

---

## Workflow-level — no CLAUDE.md amendment (strengthens / extends)

### W1 — Operator-declared `Assumed` guardrail (D11): §12.2 *enforced*, not amended

§12.2 already requires an Assumed claim be "explicitly declared." The operator-only rule is enforced **without amending §12.2**, by a new hard gate predicate **`assumed_claims_are_operator_declared`** on the Phase-8 drafting gates: every `status: assumed` claim maps by `claim_id` to a `manually_placed` `working_assumptions.json` entry **and** `claim_summary == declared value`; a `run_produced` artifact can never back an Assumed; any Assumed without a backing declaration fails the gate. Strengthens gates (§13.7-clean). **Boundary:** closes marked-`Assumed` laundering; prose that fabricates without emitting a claim stays the semantic gates' job (`no_unsupported_tier5_claims`, `no_gap_masked_as_confirmed`). *Optional:* record a one-line §12.2 clarification if you want the operator-only reading in the constitution's text — not required.

### W2 — Supporting build artifacts (no amendment)

- Tier 3 `working_assumptions.json` — `provenance_class: manually_placed`, user-authored, engine reads/never writes.
- Tier 4 `phase8_drafting_review/section_drafts/` — retained (§9.5 audit), freshness-excluded; the section JSON is the sole gate/freshness artifact.
- `AgentResult.invoked_components` — additive to §17.4.2.
- Canonical-pack deriver — same source as the prose (Tier 3 confirmed + `working_assumptions`), **per-entry provenance** so an assumed value never rides into the pack as a confirmed canonical fact.
- Instrument-profile resolver + MSCA Tier 2A/2B extraction (Stage 2).
- CI: `assembler(drafts) == section_json`; `unit_cost_budget(…) == figure`.

---

## Deterministic-component roster (C2 / §16.5)

| Component | Role | Determinism guarantee |
|---|---|---|
| Section assembler | Per-sub-section drafts → section JSON (array-append; never synthesises) | `assembler(drafts) == section_json` byte-equal |
| Assumption-applier | Flips enumerated Unresolved → Assumed from `working_assumptions.json`, pre-assembly | lookup only; self-declares nothing |
| Canonical-pack deriver | Builds `canonical_reference_pack.json` from Tier 3 confirmed + declared values | same-source ⇒ no drift; per-entry provenance |
| Unit-cost budget deriver | `months × rates × host_coeff` (unit-cost instruments) | `unit_cost_budget(…) == figure` byte-equal |

All four: agent-runtime-invoked (C2), manifest-bound (C3), logged in `AgentResult.invoked_components`.

---

## Ratification checklist (operator)

1. Instruct explicitly which of **C1 / C2 / C3** to enact (§14.5). C1 is required before Phase 7 runs on MSCA; W1's predicate is required before any operator-declared assumption may pass a Phase-8 gate (no amendment, but must be built + registered).
2. For **C1**: confirm the MSCA budget formula (living-allowance = base × host-country coefficient; other lines fixed) against the Work Programme / AGA before the rates are trusted (§10.6).
3. Run the §14.3 review: `gate_09`, affected skills/agents, tier definitions.
4. On enactment, write each amendment into `CLAUDE.md` §14 with the fields above. Do **not** enact by editing a workflow or skill alone — §14.1 makes that invalid.

*Reconciled with the milestone-1 shared-understanding ledger. Awaiting explicit human ratification per §14.5.*
