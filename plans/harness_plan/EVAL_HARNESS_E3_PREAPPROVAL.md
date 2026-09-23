# Pre-approval review — E3 (Claim-ledger completeness + status calibration)

> **Reviewed 2026-07-21**, grounded against code + data on branch `harness`: the current `tickets_eval_harness.md` E3 spec, the committed substrate (`harness/**`; E1 `4d0a73e`, E1.5 `1f9df59`, E2 `f75d9e0`), the deterministic predicate registry (`runner/predicates/**`), `CLAUDE.md` §10.5, and the three real Part B sections (`docs/tier5_deliverables/proposal_sections/*.json` — 406 claim entries). Confidence **Confirmed** unless marked. Companion to `EVAL_HARNESS_TICKETS_REVIEW.md`.

## Verdict

**Approve and proceed — the substrate is ready and the plan is faithful — but settle three design questions before writing the modules, not one.** The ticket already names materiality as "the design task to settle first"; the real data adds a second, arguably larger one the plan is currently silent on: **`claim_id` is not a usable key**, so the "diff prose against logged `claim_id`s" mechanic must match on claim *meaning*, not id. None of this changes E3's shape or its native / offline / advisory framing.

## What the data confirms (premises hold)

- **Materiality is genuinely unspecified by the system.** `CLAUDE.md` §10.5 (line 291) mandates attribution "for each material claim" and "Unattributed claims must be flagged, not asserted," but never defines *which* sentences count; "material" appears nowhere else as a definition, and claim records carry only `{claim_id, claim_summary, source_ref, status}` — **no `material` flag**. The ticket's "settle materiality first" is right.
- **Routing boundary is clean.** The only material-named predicate, `no_unresolved_material_claims` (`criterion_predicates.py:189`), checks the `validation_status` roll-up, not the prose. No deterministic check does E3's job — E3 occupies empty territory; deterministic-first intact.
- **Substrate is reusable as claimed.** Verdicts are typed `Inferred` and cannot be constructed otherwise (`verdict.py`); N≥3 majority with tie→`False` is built; E2 ships `freeze_baseline` / `compare_to_baseline`. Native E3 is well-supported.
- **Headline data checks out.** 406 entries; excellence 191 / 128 unique; 0 `claim_id`s appear inline in prose (all three sections).

## Settle before building

### D1 — `claim_id` is not a usable key ⟐ *the one the plan is silent on*

The plan's mechanic is "diff prose assertions against logged `claim_id`s." But an id identifies nothing on its own:

- Excellence's 191 entries are a concatenation of **~34 independently-numbered blocks** — `C01..C43`, then `C01..C56`, then `C01..C20` — plus mixed schemes (`C-001`, `C-13-07`, `HOST`, `FELLOW`, `DURATION`). **`C01` alone maps to three unrelated claims** (tomato crop selection; the fellow's identity; route scope). No sub-section tag on entries re-scopes them.
- **Fix:** match prose → claims by **meaning** (`claim_summary` content), treating the ledger as a set of `(summary, status, source_ref)` records; use the id only as a *label*, disambiguated (block index or summary hash). "Does this assertion map to a logged `claim_id`" becomes "…to a logged claim."
- **Latent in shipped E2 (`f75d9e0`):** it keys `property_key` / `hard_finding_ids` on `claim_id` (`status_faithfulness.py:1037,1147`). Judging is correct (E2 iterates all 406 entries, each vs its own `source_ref`), but a finding surfaced as "C01" is ambiguous across three claims. Worth a disambiguation pass while in here. *(Confirmed the collision; the ambiguity is labeling / traceability, not a faithfulness-verdict bug.)*

### D2 — Ground materiality on §10.5 + a human-labeled slice, not the ledger alone

The empirical anchor ("positives = real `claim_summary` values") calibrates the materiality classifier on the very ledger E3 audits for completeness. "Material = looks like a logged claim" can **define away the escaped claims you most want to catch** — an escaped claim is by definition absent from the ledger and may not resemble what is in it. **Fix:** apply the E1.5 discipline (human ground truth, fail-closed on unlabeled) — let §10.5's *concept* govern, validate against a small human-labeled materiality set, and measure **recall on held-out / synthetic escaped cases**, not just precision on the existing ledger.

### D3 — Spot-check the paragraph decomposition

Paragraphs run to **2,208 chars (excellence) / 4,556 (implementation)**, median ~600. Reliable atomic decomposition of long synthesis paragraphs is where false "escaped" findings will originate — more than from the materiality bar. Give the decomposition its own spot-check. This is also the one place a purpose-built tool (Ragas) could earn in later (per the ticket's own note); native is right for now given the API-currency guardrail — treat as "revisit if noisy."

## Note — no `assumed` claims in the fixtures

All three sections are **359 `confirmed` / 47 `inferred` / 0 `assumed`**. E3's status-calibration and E2's `assumed`-vs-declared branch are therefore **unexercised** by the current artifacts; they are first tested once the adversarial / undeclared fixtures (E8) exist. "Runs clean on the real sections" does not yet validate the `assumed` path.

## Evidence

| Finding | Evidence |
|---|---|
| §10.5 mandates, never defines, materiality; no `material` flag | `CLAUDE.md:291`; claim keys `{claim_id, claim_summary, source_ref, status}` |
| Routing boundary clean | `no_unresolved_material_claims` @ `criterion_predicates.py:189` = status roll-up |
| `claim_id` not a key | excellence 191 entries / 128 unique; ~34 numbering blocks (`C01..C43`, `C01..C56`, `C01..C20`); `C01`→3 claims; mixed id schemes |
| E2 labels ambiguous | `status_faithfulness.py:1037,1147` key on `claim_id` |
| Decomposition risk | max paragraph 2,208 / 4,556 chars; median ~600 |
| `assumed` path untested | 359 confirmed / 47 inferred / 0 assumed across 406 entries |
| 0 inline ids | prose match 0/128 (excellence), 0/114 (impact), 0/68 (implementation) |

## Bottom line

Approve. Before the modules: **(D1)** match on claim *meaning*, because `claim_id` isn't a key; **(D2)** ground materiality on §10.5 + a human-labeled slice; **(D3)** spot-check decomposition. D1 is cheap to fold in now and painful to retrofit, and it also warrants a small labeling / disambiguation pass over shipped E2.

---

## Resolution status (2026-07-21) — post-build (commit `b2b69b0`, Wave 0 complete)

Applied after E3 shipped; supersedes the "Before the modules" framing above where noted. *(2026-07-31: E3 has since been divided into subtickets **E3a–E3e** in `tickets_eval_harness.md` — D1 → E3a, D3 → E3b, D2 → E3c (+ residual → E3.1), status calibration → E3d, real-section run → E3e. Content unchanged; structure only.)*

- **D1 — claim-identity — ✅ resolved.** Nothing keys on bare `claim_id`; every surface uses `entry_key` (e.g. `C01#171`) and E3 never matches by id. The forced E2 disambiguation pass also caught a **real baseline bug** — a snapshot keyer silently collapsing 191→128 on duplicate ids in the grounding-invariance comparison (`compare_to_baseline`), which would have mis-paired claims; fixed backward-compatibly.
- **D3 — decomposition — ✅ addressed.** Exhaustive judge decomposition (filtering split out of the decomposer), paragraph chunking ≤4 KB, escalation to a stricter per-candidate question when coverage is claimed but unattributable, and the match basis recorded so a paraphrase false-escape stays legible.
- **D2 — materiality grounding — ◐ set up correctly, not closed.** The circularity trap is avoided: precision is honestly `None` until the non-material negatives are labeled (positives-only would report a spurious 1.0). **Residual:** recall on the real failure mode — material assertions *absent* from the ledger — is still unmeasured (shipped recall is against ledger-sourced positives only). **Tracked as → E3.1** (materiality calibration completeness: label negatives → precision; seed out-of-ledger escapes → miss-rate; record a graduation decision). **Does not block E4** — E4 reuses E2's now-fixed baseline machinery and may proceed in parallel, inheriting E3's advisory status for E3-derived metrics until E3.1 closes.

Wave-0 signals are **built but advisory**; the two open human-labeling tasks (E3.1 materiality sets + the E1.5 gold set) are the critical path to gating.
