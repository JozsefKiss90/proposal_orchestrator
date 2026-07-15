# Milestone 2 — Scope

**Working title:** Extend the β declaration substrate to Phases 2–6
**Status:** Draft scope for review. No code yet.
**Precedent:** Milestone 1 handoff §7, finding 1.

---

## 1. The problem M2 exists to fix

Milestone 1 exposed a real gap by running the DAG. When the Phase-2 scope gate meets an **Unresolved** identity spine (fellow / host / supervisor), the operator has only two options today:

1. **Leave it Unresolved** → the engine honest-blocks at Phase 2 (this is α — correct, but the run stops).
2. **Fabricate under a §3 override** → SYN-SPINE-01: fill the spine with *synthetic* `Confirmed` data so the gates evaluate it.

There is **no honest middle path** — no way for the operator to say *"assume host = ELTE, pending real confirmation"* and have Phases 2–6 treat that as a first-class **Assumed** input: evaluated so the DAG proceeds, but transparently marked and guarded so the assumption can never pass itself off as a confirmed fact.

That middle path already exists — but only for Phases 7 and 8.

## 2. Evidence: the substrate stops at Phase 7

`working_assumptions.json` (the β declaration substrate) and its W1 guard `assumed_claims_are_operator_declared` are read by exactly these modules:

- `runner/unit_cost_budget.py` — Phase 7 (host coefficient)
- `runner/assumption_applier.py`, `runner/decomposed_drafting.py`, `runner/phase8_canonical_pack.py`, `runner/predicates/criterion_predicates.py` (W1) — Phase 8

**No Phase 2–6 skill or semantic predicate reads it.** So a β-declaration cannot unblock the Phase-2 scope gate — which is *why* SYN-SPINE-01 (fabrication) was needed instead of a clean declaration. SYN-SPINE-01 is the demo shortcut; extending the substrate is the honest fix.

## 3. Goal

Let an operator **declare** a working assumption once, in `working_assumptions.json`, and have every phase from 2 to 6 that would otherwise block on missing/Unresolved spine or scope data:

1. **consume** the declared value as status **`Assumed`** (never `Confirmed`, never a fifth status);
2. **proceed** through the gate on that basis; and
3. be **guarded** by a W1-equivalent provenance predicate on that phase's output, so every `Assumed` claim provably maps back to an operator declaration — the same guarantee W1 gives Phase 8.

The closed four-value status enum (`Confirmed / Inferred / Assumed / Unresolved`) is unchanged. `synthetic` / `declared` remain descriptive provenance flags, never status values.

## 4. Design sketch (per-phase, to be refined)

| Phase | Blocks on | M2 change | W1-equivalent guard |
|-------|-----------|-----------|---------------------|
| 2 Concept | `all_mandatory_scope_covered` / scope conflicts on Unresolved spine | concept-alignment + scope skills read declared assumptions; emit matched claims as `Assumed` | new predicate on `concept_refinement_summary.json`: every `Assumed` scope/mapping claim maps to a declaration |
| 3 WP design | partner/role coverage | WP skills may treat a declared partner as `Assumed` present | guard on `wp_structure.json` |
| 4 Gantt | duration/role assignment | consume declared duration/role assumptions | guard on gantt/milestones output |
| 5 Impact | outcome/impact mapping needing spine | consume declared assumptions | guard on impact pathway output |
| 6 Implementation | management/host-dependent roles | consume declared assumptions | guard on implementation output |

**Reusable pattern (the load-bearing part):** a single shared helper — *"resolve field X: Confirmed from Tier 3 if present, else Assumed from a matching `working_assumptions.json` declaration, else Unresolved"* — plus one W1-equivalent predicate generator applied at each phase gate. Build the pattern once; apply it six times. This avoids six divergent implementations of the same honesty rule.

## 5. Candidate tickets

1. **M2-T1** — Generalise the W1 predicate into a phase-parameterised `assumed_claims_are_operator_declared(path, claim_field)` usable by any phase artifact.
2. **M2-T2** — Shared `resolve_with_declaration()` helper (Confirmed → Assumed → Unresolved) + provenance stamping.
3. **M2-T3** — Wire Phase 2 (highest value: it's where α blocks) and add its guard predicate to `phase_02_gate`.
4. **M2-T4** — Wire Phases 3–6 and add guard predicates to each gate.
5. **M2-T5** — Manifest bindings (§16.5) for any new deterministic components; decision-log + `CLAUDE.md` amendment record if gate conditions change (§14).
6. **M2-T6** — E2E: replace SYN-SPINE-01 with a **declared** spine and prove Phases 2–6 pass with every spine claim marked `Assumed` and every guard green. This is the honest re-run of Option 0.

## 6. Constitutional guardrails (non-negotiable)

- **Not a gate weakening.** Consuming a declared `Assumed` value is *not* softening a gate — the guard predicate makes the honesty burden *stricter* (every Assumed claim must trace to a declaration, or the gate fails). This is the opposite of §13.7.
- **Enum stays closed.** No fifth status. `Assumed` is the vehicle; provenance flags carry the rest (per `status-vocabulary-correction_2026-07-13.json`).
- **Any change to a Phase 2–6 gate condition is a §14 amendment** — explicit, logged, with impact review. M2-T5 owns this.
- **The engine still never invents.** The operator *declares*; the substrate *records*; the guard *verifies*. §13.3 is untouched — indeed this is what §13.3 wants: declarations instead of fabrication.

## 7. Definition of done

An operator can take the honest Tier 3 (spine Unresolved), add spine declarations to `working_assumptions.json`, run Phases 1–6, and reach green with **every** spine-derived claim marked `Assumed` and **every** phase guard confirming operator-declaration — with **no synthetic data and no §3 override anywhere in the run.** At that point SYN-SPINE-01 is retired to a historical demo artifact, and the α honest-block and a *declared* full-green coexist as the two honest poles of the system.
