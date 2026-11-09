# W03 findings — the V14/V16 run path, and which tickets sit on it

Ticket: `issues/03-v14-v16-run-path-and-on-route-tickets.md` · researched 2026-11-06 on `harness_overhaul`
@ `1bfe147e` (code identical to `msca-dn-pre-eval` @ `de226401` apart from CONTEXT docs) · read only.

## 1. The path, module by module

Commands from `plans/msca_dn_pe09_runbook.md` (§1.1, §3, §4, §5, §6 `audit`; stage B §8 reuses §4, §5 and
`audit`). Static import closure computed from the six entry points; only modules the commands execute are
listed.

| Step | Command (runbook line) | Modules executed |
|------|------------------------|------------------|
| Receipt | `harness.commands.execution_receipt` (:66) | `harness/execution_receipt.py` (claude-cli and bedrock-converse tables, `:96-97`, `_check_converse_isolation` `:810`) |
| Profile check | `tools.author_msca_dn_historical_profile --check`, `harness.commands.historical_profile --check` (:177, :181) | `harness/historical_profile.py`, `harness/profile.py` · stage B loads `harness/profiles/msca_dn_2026_default.json` instead (W02) |
| Import | `tools.import_external_proposal`, `tools.dry_import_original`, `tools.author_original_workspace` (:206–289) | `runner/external_proposal.py`, `runner/dry_import.py`, `runner/original_configuration.py`, `runner/extraction_environment.py`, `runner/dev_graph/*`, `tools/fidelity_declarations.py` (W01) |
| Preflight | `blind_assessment preflight` (:334) | `harness/evidence_preflight.py`, `harness/evidence_pack.py`, `harness/grounding_scope.py`, `harness/record_binding.py` |
| Assess / resume | `blind_assessment assess [--resume]` (:347, :359) | `harness/blind_assessment.py`, `harness/judge.py`, `harness/response_cache.py`, `harness/criterion_scoring.py`, `harness/verdict.py`, judge builder by `--transport` (`harness/commands/blind_assessment.py:252-293`): **`_converse_judge.py` → `runner/transport/{config,bedrock_converse}.py`** or **`_subscription_judge.py` → `runner/claude_transport.py`** |
| Salvage | `blind_assessment salvage` (:378) | as assess, plus the transcript reader (`commands/blind_assessment.py` ~1002–1150) |
| Freeze (V04) | `blind_assessment freeze` (:434) | `harness/blind_baseline.py` (22 `BASELINE_CHECKS`; Converse isolation entry `:175`) |
| Audit | `blind_assessment audit --candidate-provenance` (:467) | `harness/integrity_audit.py`, `harness/candidate_provenance.py` |
| Stage A only | `compare`, `review`, `diff` (:474–511) | `harness/esr_comparison.py`, `harness/operator_review.py`, `harness/comparison_diff.py` (ultrareview slice 3, not run) |

The runtime god-modules are **not executed**: `harness/judge.py:133-134` imports only the model constants
`AGENT_MODEL` / `SKILL_MODEL` from `runner/semantic_dispatch.py` / `runner/skill_runtime.py`, for the
drafter-model guard.

## 2. The transport: what the evidence settles, and what it does not

- **The code supports both routes end to end.** `--transport` takes `openai-compatible` (default),
  `claude-cli` or `bedrock-converse` (`commands/blind_assessment.py:296-375`). Converse has its own builder
  that refuses an environment not resolving to `bedrock_converse` and a version tag not naming the
  transport (`_converse_judge.py:150-170`), a freeze isolation entry (AN1b) and a receipt table (AN1b).
- **The runbook prescribes `claude-cli` only** (:334, :347, :378, :392, :400). It is V12 (2026-10-13) and
  predates AN1a/AN1b (2026-10-14/15); it has no Converse command lines.
- **The map prescribes Converse on the private host** (decision 3), and the AN12 runbook defines that host:
  eu-north-1, assessor `eu.anthropic.claude-sonnet-4-6`, drafter `eu.anthropic.claude-opus-4-6-v1`,
  version tag `bedrock-converse-eu-north-1@<date>` (`plans/msca_dn_an12_host_runbook.md:108-117`).
- **That host does not exist yet.** R11 (endpoints + host) is held by the operator until the DC/WP
  structure is final (~10 Nov; `docs/infrastructure_security/aws_hardening_worklog_v2.md`, R12a/R16
  entries), and AN12's three host criteria are unchecked
  (`.scratch/msca-dn-anonymisation/tickets.md:180-182`).

**Conclusion: the code cannot settle the transport; it is an operator decision with a calendar cost, and
it belongs at the top of W05.** Converse means: R11 (+ the AN12 host steps: bundle install, synthetic
pipeline, synthetic Converse freeze) between 10 Nov and V14, then V14 and V16 on the host, plus a runbook
delta with Converse command lines. `claude-cli` means: runnable now from the workstation exactly as the
runbook says, with transport and vendor independence traded away (model guard and blindness kept,
`commands/blind_assessment.py:253-260`), and only if the private environment's own rules permit that
processing route for the original and the 2026 candidate (runbook §1, §10).

## 3. Ticket 03's misroute does not reach the blind assessment

The misroute is in `build_paced_judge` (`harness/commands/freeze_grounding_baselines.py:211-233`): it
refuses `claude_cli` and otherwise always builds an OpenAI-compatible backend. The blind assessment calls
it only for `--transport openai-compatible` (`commands/blind_assessment.py:284-292`). With
`--transport bedrock-converse` it calls `build_converse_judge`, which refuses a mismatched environment; with
`claude-cli` it calls `build_subscription_judge`. The only way in is omitting `--transport` on the host
(default `openai-compatible`, or `HARNESS_ASSESSOR_TRANSPORT`). Even then `build_openai_backend` raises
`ValueError("base_url is required …")` (`runner/transport/config.py:833-834`) before any call: a
traceback, not a wrong backend. That is ultrareview finding 4's class (UR-A), not ticket 03's.
The live defect does hit rubric grading, the grounding freeze and faithfulness calibration, none on this path.

## 4. Ticket → path → V16 value → risk if it lands after V14

"Changes assessment output" = V14 and V16 reports would come from different scoring/draw logic, which
weakens their comparability (W05/W06).

| Ticket | On path? | What it buys V16 | Changes assessment output? | Risk if it lands after V14 |
|--------|----------|------------------|----------------------------|----------------------------|
| 01 judge call | **yes** — every draw (`judge.py`, `criterion_scoring.py`, `blind_assessment.py`, salvage) | uniform redraw, fail-closed budget, discarded draws visible in the report (audited); finding 5's replay double-count fixed | **yes** (malformed-draw handling, provenance, additive report field) | high: V14 and V16 drawn under different rules |
| 02 rubric resume | no (rubric lane); touches the shared `response_cache` contract | none | no, if its "old blind checkpoint still opens and resumes" box holds | low; regression risk only |
| 03 judge factory | construction only; **its defect is off path** (§3) | an up-front refusal on an omitted `--transport`, which UR-A can also give | no | low |
| 04 content hash | yes (preflight, baseline hashing) | none functionally; groundwork | no (byte-identical by its own acceptance) | low–medium (touches freeze inputs) |
| 05 / 06 record chain | yes (preflight → report → baseline → audit loading) | stricter re-hash of predecessors | no (refusals only) | medium (refactor across the whole chain) |
| 07a / 07b / 08 | **no** (runner skill/agent runtime) | none | no | none |
| 09 model invocation | no (runner side only; must not touch `harness/` or model pins) | none | no | low, if it leaves `SKILL_MODEL`/`AGENT_MODEL` where `judge.py:133-134` imports them |
| UR-A (findings 2, 3, 4) | yes | bad configuration refused before the first paid call; finding 4 only matters on Converse | no (refusals only) | low |
| UR-B (finding 6) | yes (V14 requires `--resume`) | a resume after a sampling change is refused, not mixed | no for a clean run; old checkpoints may no longer resume | low; land before V14 or not at all mid-run |
| UR-C (finding 7) | yes (receipt) | the private-content guard actually guards | no | low |
| UR-D (slice 2: 3, 4, 7, 8) | gate, not run | a lane GREEN that can be trusted (rule 5) | no | none for V16; it guards every other ticket |
| UR-E (slice 2: 5, 6) | yes (audit) | no DC project lost or overwritten in the audit | audit output only (not the score) | low–medium |
| Slice 2 finding 2 | V16, when provenance is resolved from the graph root | no borrowed manifest from another revision | no | low |
| Slice 2 finding 1 | V14 only (profile check) | the sixth profile check runs | no | low |

## 5. Defects on the path that no ticket covers

1. **The PE-09 acceptance lane is RED at HEAD.** One lane module fails on the binding Windows baseline:
   `tests/test_msca_dn_declaration_drafts.py::TestDeterminismAndTheCommittedArtifacts::test_the_committed_artifacts_are_reproducible`
   (`plans/overhaul/BASELINE.md` §4; also fails on Linux). It is a lane module
   (`harness/acceptance_lanes/msca_dn_historical.json:150`) with no exclusion row, so the lane reconciles
   it as an unexplained failure (`harness/acceptance_lane.py:443-448`). Cause: drift, not a code defect.
   A re-render adds `plans/msca_dn_anonymisation_handoff_2026-10-14.md` (which names the sanitised
   register) to `draft_sanitised_v1.json`'s dependents and changes one line of `review_checklist.md`.
   **Every rule-5 ticket's "lane green" box is unreachable until this is re-rendered**
   (`py -3.10 -m tools.draft_fidelity_declarations`, then `--check`), with a successor to
   `msca-dn-declaration-draft-rerender_2026-10-09` if the operator wants the re-render recorded (§9.4).
2. **The runbook has no Converse route** (§2). If W05 picks Converse, the V14/V16 command lines, the
   version-tag rule and the receipt section need a runbook delta (map "Not yet specified": the V16 runbook delta).
3. **`tests/test_transport_openai_compatible.py` makes real network calls on Windows** (10 failures,
   `BASELINE.md` §4). Off the blind path, but any ticket touching `runner/transport/` cannot read those
   tests as its own regressions.

## 6. V02c and the acceptance lane

- **V02c is done in code**: commit `7195681f` ("Reconcile the focused acceptance suite (V02a-V02d)") and the
  decision record `docs/tier4_orchestration_state/decision_log/msca-dn-stale-test-contracts_2026-10-09.json`;
  V03 then named and greened the lane (`4f2c2755`). Any open V02c checkbox is ledger drift (F1). V02c
  leaves the must-land list.
- **The lane is red at HEAD** because of item 5.1, which is new drift since V03, not a V02c leftover.

## 7. Inputs this hands to W05 and the scope cut

- W05 Q0 (new, first): **Converse on the host after R11, or `claude-cli` per the runbook?** Everything else
  in W05's calendar follows from it.
- Ticket 03: **off route either way**; recommend deferring it, not "keep if Converse".
- Before any rule-5 ticket: re-render the declaration drafts (item 5.1). This is a five-minute operator
  step, not a ticket.
- Only ticket 01 changes assessment output among the keeps, so the locked-revision rule (W05 Q1) is mainly
  a rule about 01: land it before V14, or after V16.
