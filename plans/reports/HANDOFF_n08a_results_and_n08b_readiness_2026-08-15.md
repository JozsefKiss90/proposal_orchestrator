# Handoff — n08a results, open decisions, n08b readiness

**For:** the next session, which will (a) close two operator decisions left open from n08a and (b) run `n08b_impact_drafting`.
**Branch:** `fieldwise-run-01`. Working tree dirty (see §6).
**Run-id in play:** `7612dbaf-9d7d-428b-a5f0-7b4c1288b775` — n07 and n08a both released under it.

**Read first:** `plans/reports/HANDOFF_n08a_readiness_2026-08-14.md`. It remains accurate on the three defects (§1), the operator decisions of 2026-08-14 (§4), the free-check recipes (§5) and the line-ending hazard (§5). This document does **not** repeat any of it — it records only what changed on 2026-08-14/15 and what is still open.

---

## 0. TL;DR

1. **n07 is green.** `gate_09_budget_consistency` pass + fresh under `7612dbaf`.
2. **n08a is green.** `gate_10a_excellence_completeness` pass, **13/13** predicates, `skipped_semantic: false`.
3. **Two operator decisions are open** (§3). Neither blocks n08b.
4. **n08b is immediately runnable** (§4). It depends on n07, *not* on n08a.
5. Do **not** re-run n01–n07.

---

## 1. n07 — root cause was a UUID transcription error, not a logic defect

The prior handoff's §2 called n07 "stale, re-run it". That was right, but the re-run (`9e27694f`) then failed for an unrelated reason worth recording, because it can recur on any node.

Every skill in n07 succeeded, **including the budget evaluation itself**, which returned `overall_status: "pass"` with a correct §8.1 unit-cost rationale. The node died at the final step because Claude mis-transcribed the run UUID — in two places, differently each time:

| Where | Value |
|---|---|
| correct | `9e27694f-`**`e13b-4449`**`-9436-93623b7873bf` |
| envelope | `9e27694f-`**`4936-4436`**`-9436-93623b7873bf` |
| payload | `9e27694f-`**`9443-4436`**`-9436-93623b7873bf` |

The runtime refused it correctly per §17.6.5. The envelope copy is harmless (Phase D.6 normalization discards it); the **payload** copy is what failed, at `skill_runtime.py` `output_contract == "payload"` validation.

Evidence is preserved at `.claude/skill_diag/gate-enforcement_9e27694f_{response,parsed}.txt` — worth reading if this class recurs.

### The fix applied

`runner/skill_runtime.py`: new `_run_id_echo_directive()`, wired into **both** prompt builders (`_assemble_skill_prompt` cli-prompt, `_assemble_tapm_prompt` TAPM), plus a payload-contract-specific block in the TAPM user prompt. Payload skills return an in-memory payload, so the system prompt's "output artifact" framing did not visibly cover the field that actually failed.

**This hardens the request, never the acceptance.** A mismatched `run_id` remains a hard failure and is never auto-corrected. Changing what we *ask for* is prompt assembly (§17.5.2); changing what we *accept* would be the silent repair §17.6.5 forbids. No constitutional amendment needed or made.

**Attribution caveat — do not overstate this.** One success does not separate the fix from ordinary run-to-run variation. The change is sound regardless; treat it as risk reduction, not a proven cure.

144 skill-runtime tests pass (`test_skill_runtime{,_tapm,_enrich,_tool_loop}.py`).

---

## 2. n08a — green, and verified substantively

`gate_10a` **13/13**, `skipped_semantic: false`, gate result run-id `7612dbaf`.

Drafts genuinely regenerated (not reused): spine re-stamped `ec01fb84` → `7612dbaf`, sub-section drafts rewritten 23:41→23:54, ~16 min drafting + ~7 min audit.

> **Log-reading trap that cost this session a false alarm.** The run log shows only **two** `skill START` lines (`proposal-section-traceability-check`, `constitutional-compliance-check`). `excellence-section-drafting` never appears, and the benchmark reports `invocations=2`. **Drafting still ran.** The decomposed drafter (`runner/decomposed_drafting.py`) supersedes the monolithic drafting skill and emits no `skill START` lines, and its per-sub-section calls are not counted in that benchmark total. Verify drafting by draft-file mtimes and the spine `run_id`, never by the skill log.

### The §1.3 honesty layer is working, and provably non-vacuously

Claim ledger across the four sub-section drafts: **82 confirmed / 9 inferred / 5 assumed / 0 unresolved**.

- **W1 (`g09a_p11`)** — all 5 `assumed` claims cite `working_assumptions.json` with `assumption_declared: true`. Previously **zero** assumed claims existed, so W1 passed vacuously. It now audits real declarations.
- **W2 (`g09a_p12`)** — 9 `inferred` claims, **none** citing `working_assumptions.json`; they cite genuine Tier 2B / Tier 3 / canonical-pack sources. This is exactly the defect that previously presented three operator-declared facts to the evaluator as derived from confirmed evidence.
- **Zero unresolved** is what clears `p06`.

The five assumed claims: `elte_previous_msca_hosting`, `placement_supervisor_AgroVIR`, `placement_supervisor_title_AgroVIR`, `placement_workspace_AgroVIR`, `placement_team_AgroVIR`.

---

## 3. Open decisions — both are the operator's, deliberately not taken

### 3.1 Two tests now fail, and the prior handoff's prediction about them was wrong

```
tests/runner/test_phase8_gate_content.py::TestCurrentArtifactState
  ::test_excellence_no_assumed_claims          expects 0 assumed, got 5
  ::test_excellence_overall_status_not_assumed expects confirmed|inferred, got assumed
```

Prior handoff §7 listed `test_excellence_overall_status_not_assumed` as an "honest red" that would "clear when n08a goes green". **It did not clear, and nothing is broken.** The operator's §4 decision to keep the AgroVIR placeholders Assumed *predetermined* `overall_status: "assumed"`. Both tests predate that decision and now assert a world the operator consciously overrode.

The gate is unaffected: `p06` rejects only `unresolved`; `p11` accepts *declared* `assumed`.

**Not rewritten deliberately.** Updating a guard to match a result the same session just produced needs operator sign-off, even though §7's own rule ("update a snapshot test to the new truth — do not delete it") points that way. The defensible rewrite: allow `assumed` **provided every assumed claim is operator-declared** — which W1 already enforces at gate time. Ask before applying.

### 3.2 Placeholders are in the evaluator-facing prose

The five assumed claims appear in the drafted text and need hand correction before submission. Tracked in `working_assumptions.json` `_operator_placeholders`. Expected per §4 of the prior handoff — flagged here only so it is not forgotten at assembly.

---

## 4. n08b readiness

**n08b does not depend on n08a.** Manifest edge `e07_to_08b`: `n07_budget_gate → n08b_impact_drafting`, gate condition `gate_09_budget_consistency` (passed, fresh). n08a and n08b are siblings that both fan into `n08d_assembly`. n08c is likewise independent.

**Structurally identical to n08a**, so every fix from this session and the last applies unchanged:

| | n08a | n08b |
|---|---|---|
| agent | `excellence_writer` | `impact_writer` |
| components | `canonical_pack_deriver`, `excellence_assumption_applier`, `excellence_section_assembler` | same three, `impact_*` variants |
| skills | `excellence-section-drafting` + 2 audits | `impact-section-drafting` + same 2 audits |
| exit gate | `gate_10a` (12 predicates + W2 = 13) | `gate_10b` (12 + W2 `g09b_p13` = 13) |

**Favourable starting conditions vs. n08a:** `section_drafts/` contains only `excellence/`. There is **no pre-existing impact spine**, so the dead-draft-reuse hazard that dominated the last two n08a attempts does not exist for n08b. Any fresh run drafts from scratch.

**Suggested command** (a new run-id is *not* required — no stale impact spine to invalidate; reusing `7612dbaf` keeps `gate_09` same-run and avoids a cross-run bootstrap):

```bash
py -3.10 -u -m runner --run-id 7612dbaf-9d7d-428b-a5f0-7b4c1288b775 --node n08b_impact_drafting --verbose
```

Background it — expect ~25 min. **Never launch a second `runner` invocation against a live run-id**; a concurrent `--phase 7` this session was caught by the guard (`dispatched=0`, zero quota) but only because it arrived after the node was already `running`.

**Free pre-flight** (both recipes in prior handoff §5): the seven-gate freshness check, and direct `gate_10b` predicate evaluation via `runner.gate_evaluator.PREDICATE_REGISTRY`.

**Residual risk, unchanged:** drafting is non-deterministic and the claim set varies per run. W2 now blocks the specific "declared fact laundered as `inferred`" class, but cannot guarantee the drafter avoids inventing meta-claims about repository state. If `gate_10b` fails, run the §6 diagnostic from the prior handoff (adapted to `section_drafts/impact/`) **before** spending another run, and classify the blocker as a real fact (needs Tier 3 answer or declaration) vs. a drafting-instruction escape (tighten the instruction; do not declare it away).

---

## 5. Quota

Roughly half the subscription session quota was already spent before this session. Added since: n07 ≈ 5 invocations / ~121k tokens; n08a ≈ 2 audit invocations / ~32k plus the uncounted decomposed-drafting calls. Prior handoff's rule still governs: **do not spend a run to learn something establishable for free** — the appliers, assemblers, canonical-pack deriver and every `gate_10*` predicate are deterministic and Claude-free.

---

## 6. Uncommitted state

Nothing from this session is committed. Beyond the prior handoff's §8 list:

- `runner/skill_runtime.py` — the only source change this session (§1).
- Regenerated by the runs: `phase7_budget_gate/{gate_result,budget_gate_assessment,unit_cost_budget}.json`, `phase8_drafting_review/{gate_10a_result,canonical_reference_pack}.json`, `section_drafts/excellence/*`, `tier5_deliverables/proposal_sections/excellence_section.json`.
- New untracked: `decision_log/decision-log-update_7612dbaf.json`, `validation_reports/{constitutional-compliance-check,proposal-section-traceability-check}_7612dbaf.json`, `docs/tier4_orchestration_state/reuse/phase8/`.
- **Junk to delete:** `docs/tier3_project_instantiation/source_materials/part_b_draft_v0/~$ELDWISE_MSCA_Master_Draft.docx` (Word lock file).
- Artifacts from the failed `9e27694f` run are still untracked; harmless, but they are dead evidence.

Still open and untouched from prior handoff §7: the 7 pre-fold snapshot tests and the missing `amendments` entries on the authorisation record. No quota needed.

---

## 7. Suggested skills

- **`tdd`** — for §3.1, if the operator approves rewriting the two guards. The rewrite is a behaviour change to a safety net; state the new invariant ("`assumed` permitted iff every assumed claim is operator-declared") as a test first.
- **`diagnosing-bugs`** — only if `gate_10b` fails. Exhaust the free diagnostics (prior handoff §5–6) before any re-run.
- **`code-review`** — before committing; `runner/skill_runtime.py` is the sole source change and touches every skill invocation.
- **`prose-review`** — for the evaluator-facing Tier 5 prose once §3.2's placeholders are hand-corrected. Not before.

**Do not** reach for `Workflow`/multi-agent orchestration here. This work is sequential, quota-bound, and gated; fan-out spends quota without shortening the critical path.

---

## 8. Rules carried forward

- Never hand-edit claim statuses in a draft to force a green — fabricated completion, §15.
- Gate failure is a valid and correct output.
- Verify drafting by artifact mtimes + spine `run_id`, not by the skill log (§2).
- After any checkout / stash pop / branch switch touching Tier 3, re-run the freshness check — CRLF rewrites change fingerprints with zero content change (prior handoff §5).
