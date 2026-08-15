# Handoff — n08b results, open decisions, n08c readiness

**For:** the next session, which will (a) run `n08c_implementation_drafting` and (b) close the operator decisions in §3.
**Branch:** `fieldwise-run-01`. Last commit `381eda1`; only the n08b run outputs are dirty (§6).
**Run-ids in play:** four, one per chain step — `77eeb21d` (n05), `8167365d` (n06), `584ecd9f` (n07), `2649ff21` (n08b). All passed.

**Read first:** `plans/reports/HANDOFF_n08a_results_and_n08b_readiness_2026-08-15.md` and its predecessor. They remain accurate on the free-check recipes, the line-ending hazard, and the log-reading trap (drafting emits no `skill START` lines). This document records only what changed on 2026-08-15/16.

---

## 0. TL;DR

1. **n08b is green.** `gate_10b_impact_completeness` pass, **14/14** predicates, `skipped_semantic: false`, run `2649ff21`.
2. The n05→n06→n07 rerun chain behind it is green, and each step bootstrapped its predecessors cross-run from durable evidence — four separate run-ids worked where the plan assumed one.
3. **gate_10a is now stale** (its recorded `budget_gate_assessment.json` fingerprint moved with the n07 rerun). n08a must re-run before n08d assembly; n08c does not care (§3.2).
4. **n08c is immediately runnable** (§4). It depends only on `gate_09`, which is pass and fresh under `584ecd9f`.
5. Do **not** re-run n01–n07.

---

## 1. What the chain fixed, and what held

Run `5dd0e971` failed gate_10b on three predicates; all three fixes held on the next attempt.

| Predicate | Root cause | Fix that held |
|---|---|---|
| `g09b_p06` | Spec divergence: the phase_05 workflow spec mandates a communication strategy, but `impact-dec-enricher` and the artifact schema had dropped the C of DEC | `communication_plan` added to schema + enricher spec; n05 rerun produced it (2 activities); `dec_coverage` now all-true |
| `g09b_p07` | The drafter honestly surfaced the operator's open background-IP item as an Unresolved claim | Operator-approved declaration `placement_ip_ownership` (Option C: grant-default allocation, confirmatory agreement); applier flipped it to Assumed |
| `g09b_p13` | Drafter derived seniority from a declared title, called the derivation "inferred" under an invented claim_id | W2 instruction extended to declaration-*derived* facts; also replaced the withdrawn `mobility_eligibility` example key |

The p06 fix forced a rerun cascade by content staleness: n05 changed `impact_architecture.json` (staling `phase_06_gate`), n06 changed `implementation_architecture.json` (staling `gate_09`), n07 changed `budget_gate_assessment.json` (staling `gate_10a` and `gate_10b`). The operator accepted this cost; `decision_log/fieldwise-p06-communication-route_2026-08-15.json` records the route and the cascade.

The earlier quote-transcription hardening (run `30a60152`: `„Марица"` emitted with an unescaped ASCII closing quote, breaking the JSON reply) also held — all three impact sub-sections parsed. Same caveat as the n07 UUID fix: one clean run is risk reduction, not proof.

## 2. n08b — the numbers

Claim ledger across the three sub-section drafts: **75 confirmed / 3 inferred / 4 assumed / 0 unresolved** (82 claims). `overall_status: assumed` — by design, as with n08a.

- The four assumed claims are `placement_supervisor_title_AgroVIR`, `placement_ip_ownership`, and `agrovir_relevant_track_record` twice (two sub-sections make the claim; both matched the declaration, both passed W1).
- `placement_ip_ownership` surfacing as Assumed is the p07 resolution working end to end: drafter keyed it, applier rewrote it with the operator's declared wording.
- Section artifact: `docs/tier5_deliverables/proposal_sections/impact_section.json`, spine run-id `2649ff21`, `dec_coverage` all three true.

## 3. Open decisions — the operator's, deliberately not taken

### 3.1 The two "no assumed claims" snapshot tests — now stale for both sections

`tests/runner/test_phase8_gate_content.py::TestCurrentArtifactState::test_excellence_no_assumed_claims` and `::test_excellence_overall_status_not_assumed` still fail, as they have since n08a. The impact section now carries the same deliberate `overall_status: assumed`, so the question they pose covers both drafted sections. The defensible rewrite is unchanged: allow `assumed` provided every assumed claim is operator-declared — which W1 already enforces at gate time. Needs operator sign-off; state the invariant as a test first (`tdd`).

### 3.2 When to re-spend n08a

`gate_10a` is stale on exactly one input, `budget_gate_assessment.json`, moved by the n07 rerun. n08d's transitive durable-evidence verification will refuse until n08a re-runs, but n08b and n08c are siblings and do not check it. Decision: re-run n08a immediately after n08c, or batch it just before n08d. Either works; it must precede n08d. Note the excellence drafts on disk predate every fix from 2026-08-15, so the re-run also picks up the quote directive and the derived-fact instruction.

### 3.3 Placeholders and Assumed wording in evaluator-facing prose — carried

The five n08a placeholders still need hand correction at assembly. The impact section adds the placement-IP sentence (Assumed until the written agreement exists) and the AgroVIR track-record absence. §3.2 of the *implementation* section will surface the same AgroVIR material — see §4.

## 4. n08c readiness

**Dependencies are green.** Manifest edge `e07_to_08c`: `n07_budget_gate → n08c_implementation_drafting`, gate condition `gate_09_budget_consistency` — pass and content-fresh under `584ecd9f`. Exit gate is `gate_10c_implementation_completeness`.

**Structure:** two drafting sub-sections, `3.1` (work plan, risks, effort) and `3.2` (host capacity and hosting arrangements). `source_section_extra_fields` derives cleanly right now: 5 `wp_table_refs`, 6 `milestone_refs`, gantt and risk-register refs present. All of these were regenerated fresh by the chain. `section_drafts/` holds only `excellence/` and `impact/`; there is no implementation spine, so the dead-draft-reuse hazard does not exist.

**Every shared fix applies unchanged** — n08c uses the same `_default_claude_drafter` (quote directive, derived-fact W2 rule) and the same applier/assembler machinery with `implementation_*` variants.

**§3.2-specific traps, written down before they bite:**

- `agrovir_relevant_track_record` prescribes its own form: §3.2 must state the absence of EU-funded research participation plainly and lean on the commercial footprint. Converting it into a positive research claim is the failure the declaration exists to prevent.
- The hosting-arrangement declarations (`placement_workspace_AgroVIR`, `placement_supervisor_AgroVIR`, `placement_supervisor_title_AgroVIR`, and the `placement_team_AgroVIR` placeholder) all land in §3.2 — expect several Assumed claims, all of which must be keyed to their declaration.
- The checklist open item "capacity descriptions item 12 never asked the organisations for" is still open: §3.2 drafts thin there, and thin is correct — do not fabricate depth.

**Suggested command** (reusing `2649ff21` keeps the Phase 8 sub-steps in one manifest for n08d later; a fresh run-id also works — cross-run bootstrap is now validated four times over):

```bash
py -3.10 -u -m runner --run-id 2649ff21-c9fa-4488-b802-a4b215d769b8 --node n08c_implementation_drafting --verbose
```

Background it; expect ~20 min for two sub-sections. Never launch a second runner invocation against a live run-id. If gate_10c fails, exhaust the free diagnostics first (raw responses under `.claude/logs/decomposed_drafting/<run>/implementation/`, direct predicate evaluation via `PREDICATE_REGISTRY`) and classify the blocker: real fact needing a Tier 3 answer or declaration, versus a drafting-instruction escape.

## 5. Test-suite state

Current known reds are all pre-existing and understood: the two §3.1 snapshot tests, plus four in `test_fieldwise_ticket7_authorisation.py`. Those four are `test_the_status_totals_match_the_artifacts`, `test_the_open_items_in_the_checklist_are_all_in_the_packet`, `test_the_record_carries_every_open_item`, and `test_the_workspace_answer_was_not_adopted_as_workspace`. They are the stale-packet class from the 2026-08-14 checklist rewrite, untouched by this session's syncs — verified 0 new before and after every edit.

## 6. Uncommitted state

Commit `381eda1` already carries the session's source fixes, the Tier 3 syncs, the spec amendments, and the n05/n06/n07 artifacts. Dirty now, all from the n08b run: `gate_10b_result.json`, `canonical_reference_pack.json`, the three impact drafts plus `section_spine.json`, `impact_section.json`, and the Step-0 call slice. Untracked: `reuse/phase8/n08b_impact_drafting.reuse.json` and the two `*_2649ff21.json` validation reports.

## 7. Rules carried forward

- Gate failure is a valid and correct output; never hand-edit claim statuses to force a green (§15).
- Verify drafting by draft-file mtimes and the spine run-id, never by the skill log.
- A drafter claim `unresolved` keyed on a declaration key is by design — the applier flips it; the drafter never self-declares `assumed`.
- After any checkout or stash touching Tier 3, re-run the freshness check: CRLF rewrites change fingerprints with zero content change.
- Do not spend a run to learn something establishable for free — the appliers, assemblers, pack deriver and every `gate_10*` predicate are deterministic and Claude-free.
