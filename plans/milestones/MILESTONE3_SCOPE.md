# Milestone 3 — Scope

**Working title:** Evaluator-ready narrative composition
**Status:** Draft scope for review. No code yet.
**Origin:** Operator observation on the milestone-1 engine-integration proof (`msca-pf-syn-01`, 2026-07-15): the drafted Excellence section is *structurally and semantically valid but not yet composed into a coherent, evaluator-ready narrative*, and it leaks internal identifiers into the prose.

In one line: **M1** made the drafting engine produce grounded, full-length, honest content; **M2** moves the authoring surface to the graph and generalises to many projects; **M3** turns *correct-and-grounded* into *readable-and-evaluator-ready*.

---

## 1. The problem M3 exists to fix

The milestone-1 proof produced a 20,780-word Excellence section that is grounded and honest but reads like an internal engineering artifact. Measured on that section's prose:

| Internal token class | count | examples |
|---|---:|---|
| `METH-*` graph-node IDs | 136 | `METH-SOTA-001`, `METH-CORE-004`, `METH-DEC-002` |
| `OBJ-/WP#/RQ#` IDs | 274 | `OBJ-4`, `WP3`, `RQ1`, `RQ10` |
| Task IDs (`T#-##`) | 114 | `T1-01`, `T3-02`, `T4-01` |
| `SR-/CC-` scope IDs | 74 | `SR-07`, `CC-04`, `CC-11` |
| Provenance tags | 164 | `source_grounded`, `synthesis`, `inference`, `unconfirmed` |
| `[SYNTHETIC]` markers | 7 | `[SYNTHETIC — SYN-SPINE-01 …]` |

That is **~760 internal tokens in ~20,800 words — roughly one every 27 words.** An evaluator should never see any of them. Two distinct defects hide here:

1. **Identifier leakage** — internal traceability tokens (`METH-*`, `SR-/CC-`, `T#-##`, `OBJ-/WP#/RQ#`), provenance vocabulary (`source_grounded`, `synthesis`), and demo markers (`[SYNTHETIC]`) appear *in the prose* rather than only in the artifact's metadata.
2. **Assembled, not composed** — the section is an array-append of five independently-drafted sub-sections. It has no cross-sub-section flow, no transitions, and repeats context; it stitches rather than weaves.

## 2. Why this is a milestone, not a prompt tweak — the load-bearing constraint

The Phase-8 pipeline deliberately separates **drafting** (Claude, per sub-section) from **assembly** (deterministic, byte-equal, `runner/section_assembler.py`). The assembler carries claim and validation status up **verbatim** and is closed by the replay check `assembler(drafts) == section_json`. That determinism is the assembly step's anti-fabrication guarantee (D3) — and it is precisely why the assembler **cannot** de-identify or compose: stripping tokens or rewriting for flow *is synthesis*, which the deterministic component is forbidden to do.

So evaluator-ready prose cannot be produced in the assembler. It requires a **separate, Claude-driven composition pass** — and introducing synthesis back into the Tier-5 path is a real architectural change that needs constitutional care (see §7).

## 3. Goal

Add a **gated narrative-composition layer** that transforms the grounded sub-section drafts into an evaluator-ready section (and, at assembly, an evaluator-ready Part B) that:

1. contains **no internal identifiers or provenance vocabulary** in the prose (they remain in `source_refs` / `claim_statuses` metadata for traceability);
2. reads as a **coherent, evaluator-oriented narrative** — transitions, no redundancy, framed against the evaluation criteria;
3. **fits the instrument's page limit** (the M1 proof overshot the MSCA-PF ~10-page target ~8×; an over-long section is not evaluator-ready); and
4. **preserves every canonical fact and every claim verbatim** — partner legal names, objective/WP titles, measurable targets, deliverable identities, and the full claim ledger (status + source_ref) — introducing, dropping, or restatusing nothing.

## 4. Design sketch — the gated composition layer

**Placement (a design decision to settle):** a per-section composer in `n08a/b/c` (de-identify + intra-section flow) **and** a cross-section narrative integrator in `n08d` (Part-B-level coherence). The per-section pass fixes identifier leakage and local flow; the assembly pass weaves sections into one narrative.

**Contract.** Input: the assembled section (grounded prose + `claim_statuses` + `source_refs` + the canonical reference pack). Output: a section of the **same schema** whose `content` is rewritten for readability and de-identified, with the **claim ledger carried forward unchanged**.

**The anti-fabrication guarantee shifts — and this is the crux.** The composer is Claude (synthesis), so it cannot carry the assembler's *byte-equal* guarantee. Its guarantee instead comes from the **existing Phase-8 gates**, re-run on the composed output:

- `partner_names_preserved`, `deliverable_identity_preserved`, `canonical_terms_preserved`, `measurable_targets_preserved` — every canonical fact still present, verbatim.
- `no_unsupported_tier5_claims` — no claim the composer invented.
- `no_unresolved_material_claims`, `assumed_claims_are_operator_declared` (W1) — the honesty ledger unchanged.
- `cross_section_consistency` (`gate_10d`) — the woven Part B is internally consistent.

These gates already enforce *"form may change, substance may not."* M3's composer is allowed to change **prose form**; the gates guarantee it changed no **substance**. This is the same move as C1's budget reasoning: where determinism can't supply the anti-fabrication guarantee, **gated verification** does.

**De-identification target (mechanical half).** Strip from `content` (never from metadata): `METH-[A-Z]+-\d+`, `\b(?:SR|CC|OBJ|WP|RQ)-?\d+`, `\bT\d+(?:-\d+)?\b`, the provenance lexicon (`source_grounded`/`synthesis`/`inference`/`unconfirmed`), and `[[wikilinks]]`. Demo markers (`[SYNTHETIC]`) are a special case: they must stay legible *as a demo watermark* somewhere (the docx already stamps "SYNTHETIC DEMO — NOT FOR SUBMISSION"), but should not litter the body prose.

## 5. The cheap partial (available before M3)

Tightening the drafter prompt to **keep internal IDs out of `content`** (they belong in `source_refs`) reduces leakage at the source and is a small change — the same kind as the recent tier-format prompt fix. It does **not** deliver cross-sub-section composition or page-limit fitting (the substantial M3 work), but it makes every future draft cleaner and lowers the composer's burden. Reasonable to land as an M1-remainder polish rather than waiting for M3.

## 6. Candidate tickets

1. **M3-T1** — Drafter-prompt de-identification (the cheap partial): IDs and provenance tags out of `content`, into `source_refs` only.
2. **M3-T2** — The per-section **narrative composer** (Claude pass, §17.5.2 skill-class): de-identify + intra-section flow; output same schema, claim ledger carried forward.
3. **M3-T3** — Re-run the canonical-preservation + W1 + `no_unsupported_tier5_claims` gates on the composed output; wire as the composer's exit condition (the anti-fabrication guarantee).
4. **M3-T4** — Cross-section **narrative integrator** at `n08d` + `gate_10d` coherence over the woven Part B.
5. **M3-T5** — **Page-limit fitting**: tune per-sub-section soft caps to the instrument profile's page limit, or a composition-time length budget, so the composed section lands within the profile limit.
6. **M3-T6** — Constitutional treatment (§7): a decision-record / amendment establishing the gated-synthesis composer as a sanctioned Tier-5 step, with its anti-fabrication guarantee defined as gated verification (not determinism).
7. **M3-T7** — E2E: recompose the milestone-1 Excellence drafts into evaluator-ready prose with **zero internal tokens** in the body and every canonical/claim gate green.

## 7. Constitutional guardrails (non-negotiable)

- **This introduces synthesis into the Tier-5 path.** The current design keeps the assembler deterministic precisely to avoid a "shadow author" (§9.4/§16). The composer *is* a Claude author, so its output must be gated by the contradiction-detectors above — the guarantee is verification, not trust. This shift should be logged and, if it changes the Phase-8 contract, amended per §14 (M3-T6).
- **The claim ledger is the substance.** Composition may rewrite the `content` string but must carry `claim_statuses` and `source_refs` forward unchanged. A composer that alters a claim's status or drops a source_ref is a violation the gates must catch.
- **Traceability is not lost, only relocated.** IDs leave the prose but remain in metadata, so every claim still traces to Tier 1–4. De-identification must never sever a claim from its source.
- **§13.3 unchanged.** The composer may reshape grounded prose; it may not invent a fact. `no_unsupported_tier5_claims` is its hard floor.

## 8. Relationship to M1 and M2

- **M1 (done, proven):** grounded, full-length, honest content; the engine refuses to finalize unconfirmed content. M3 sits directly on top — same honesty discipline, one layer up (prose form rather than claim substance).
- **M2 (graph track):** authoring surface and multi-project generalisation. Independent of M3; the two can proceed in either order, though M3's composer operates on whatever the drafting layer produces, graph-sourced or not.

## 9. Definition of done

Take the milestone-1 Excellence drafts (or a real confirmed-data run) through the composition layer and produce an Excellence section that: contains **zero internal identifiers or provenance tags** in the body prose; reads as a coherent evaluator-oriented narrative; **fits the MSCA-PF page limit**; and passes **every** canonical-preservation, W1, `no_unsupported_tier5_claims`, and `no_unresolved_material_claims` gate — proving the prose was made readable **without** fabricating or dropping a single canonical fact or claim. At that point the system produces not just a *correct* proposal section but a *submittable-quality* one.
