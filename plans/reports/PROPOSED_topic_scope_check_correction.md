# PROPOSED CORRECTION — `.claude/skills/topic-scope-check.md`

**Status:** NOT APPLIED. Requires your hand.
**Blocking?** **No.** This skill writes a decision-log entry and gates nothing. Gate `g03_p06` reads `concept_refinement_summary.json` (from `concept-alignment-check`). You can defer this to milestone 2 without affecting Phase 2.
**Why I didn't apply it:** the repo's `.claude/` is write-protected in the assisting session — and that's the right outcome. A skill spec is an agent instruction; a change to scope-evaluation *semantics* should pass through you explicitly, not be applied silently by an agent.

---

## The defect

The skill's anti-fabrication guard (≈ line 108) is **correct in intent**:

> Any claim evaluated as `in_scope` without a matching `scope_element_ref` from the loaded Tier 2B data must instead be assigned `status: "flagged"` … "No Tier 2B scope element found to confirm this claim is in-scope; scope boundary is defined by Tier 2B only"

This stops the skill declaring things in-scope from prior programme knowledge (§13.2 / §13.9). Keep it.

But it **conflates two different situations**:

| | Situation | Correct disposition |
|---|---|---|
| (a) | The call **has** thematic boundaries; this claim matches none | `flagged` / `out_of_scope` — a real conflict |
| (b) | The instrument defines **no thematic boundary at all** | *not a conflict* — there is nothing to match, and there never will be |

MSCA-PF is **researcher-driven and topic-agnostic**. It constrains eligibility, mobility, supervision, training, CDP and duration — but imposes **no research-domain scope**. So every research-content claim fails to match, is flagged, and `resolution_status` is forced to `unresolved`.

**This is unfixable by editing the concept.** The only way to satisfy it would be to invent Tier 2B scope elements — which is exactly what §13.2 forbids. On the live run it produced 5 spurious flags (research domain, two-route methodology, AquaCrop decision engine, TRL target, the ten open RQs), each reading *"MSCA-PF is research-topic-agnostic; `scope_requirements.json` contains no entries addressing this."*

## The secondary defect — scope vs. provenance

Two further flags objected that SR-01/SR-02/CC-01 require an *excellent researcher* and a *real joint application*, while the concept "explicitly declares… SYNTHETIC — not real facts, not submittable."

That is **provenance policing, not scope checking.** Whether a claim is real, assumed or synthetic is governed by the §12.2 `validation_status`, the `no_unresolved_material_claims` predicate, W1, and any logged §3 override. A scope checker that downgrades honestly-marked content makes transparency self-defeating: *any* data carrying its own honesty markers becomes unable to pass.

---

## The three edits

### 1. Insert new **Step 2.3a** (before Step 2.4)

```
- Step 2.3a: **Determine the instrument's thematic jurisdiction.** From the loaded
  `scope_requirements.json`, determine whether the call defines ANY *thematic* scope
  boundary — i.e. any entry constraining the research domain, topic, technology,
  methodology, or expected research content. Set `thematic_jurisdiction` = true if at
  least one such entry exists, false if none does. This is read from Tier 2B ONLY and is
  NEVER inferred from prior programme knowledge. Some instruments (notably MSCA-PF and
  ERC, which are researcher-driven and topic-agnostic) define eligibility, mobility,
  supervision, training and duration requirements but deliberately impose NO thematic
  boundary: the researcher proposes any subject. For such instruments
  `thematic_jurisdiction` is false, and no thematic boundary exists against which to
  evaluate research-content claims — not because data is missing, but because the call
  defines none.
```

### 2. Add a fourth disposition to **Step 2.4**, and a jurisdictional limit as **Step 2.4a**

```
  - **no_applicable_boundary**: `thematic_jurisdiction` is false AND the claim asserts
    research content (domain, methodology, model choice, output type, TRL, or an open
    research decision) AND no SR-xx or CC-xx entry in the loaded Tier 2B addresses that
    claim's subject matter. The call defines no boundary governing this claim, so the
    claim is OUTSIDE THIS SKILL'S JURISDICTION — neither confirmed in-scope nor in
    conflict. Status = no_applicable_boundary. Must record `flag_reason` naming the
    Tier 2B file consulted and stating that it contains no entry governing the claim's
    subject.
    - **This disposition is NOT a fallback and NOT a way to dispose of an inconvenient
      finding.** It is available ONLY when `thematic_jurisdiction` is false. If ANY
      SR-xx or CC-xx addresses the claim's subject — eligibility, mobility, supervision,
      training, career development, secondment, duration, ethics, open science — the
      claim MUST be evaluated against that element and MUST NOT be assigned
      no_applicable_boundary. A claim that touches a real requirement and fails it is
      `out_of_scope` or `flagged`, never no_applicable_boundary.

- Step 2.4a: **Scope, not provenance — jurisdictional limit.** This skill evaluates WHAT
  THE PROJECT ASSERTS against the Tier 2B scope boundaries. It does NOT evaluate whether
  the asserted facts are true, real, confirmed, assumed, or synthetic. Provenance is
  governed elsewhere and is fully checked there: by the §12.2 `validation_status` on each
  claim, by the `no_unresolved_material_claims` gate predicate, by the W1
  `assumed_claims_are_operator_declared` predicate, and by any logged §3 operator
  override. A claim MUST NOT be downgraded to `flagged` or `out_of_scope` on the ground
  that it is marked synthetic, assumed, unconfirmed, or "not submittable", or that it
  originates in an operator override. Where a proposal asserts a fact that satisfies a
  scope element, that element is satisfied *for scope purposes*, and the claim's
  provenance travels with it in its own metadata.
```

### 3. Update **Step 2.6** and **Step 2.7**

- **2.6** — extend the status enum: `(in_scope / out_of_scope / flagged / no_applicable_boundary)`, and require `flag_reason` non-empty for `no_applicable_boundary` too.
- **2.7** — replace with:

```
- Step 2.7: Determine `resolution_status`: if any finding has status out_of_scope or
  flagged → "unresolved". If every finding has status in_scope or no_applicable_boundary
  → "resolved". `no_applicable_boundary` findings do NOT make the invocation unresolved —
  a claim the call does not govern cannot be a scope conflict — but they MUST still be
  listed in `scope_findings` with their `flag_reason`, so the absence of a governing
  boundary is visible and auditable rather than silently dropped.
```

Also update the enum in the two documentation tables (≈ lines 41 and 220) and the `resolution_status` row (≈ line 223).

---

## Is this a §13.7 gate weakening?

**No — but it deserves the scrutiny.** It removes a check the scope gate has no *jurisdiction* over (provenance), and adds a disposition for constraints that **do not exist** (topic-agnostic instruments). Nothing goes unchecked: every provenance check stays with the authority that owns it. It is not silent (this document + a decision-log entry), and it does not let the workflow proceed on incomplete inputs — incompleteness is still caught by `validation_status` / `no_unresolved_material_claims` / W1.

## The consequence to hold consciously

After the provenance/scope separation, **nothing in the gate stack blocks synthetic data.** `no_unresolved_material_claims` fails only on `unresolved`; the SYN-SPINE-01 spine is `Confirmed` + `synthetic: true`. W1 governs only `assumed`. The synthetic nature of this run is then carried by exactly three things: the `synthetic: true` metadata, the logged override records, and the `SYNTHETIC DEMO — NOT FOR SUBMISSION` watermark on the `.docx`.

That is **by design** — SYN-SPINE-01 accepted precisely this trade. But hold it deliberately rather than discover it later.
