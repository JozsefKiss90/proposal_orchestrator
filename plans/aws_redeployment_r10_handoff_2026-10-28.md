# AWS redeployment: handoff for R10 (Phase 8 drafter through the transport layer, F5)

| Field | Value |
|---|---|
| Date | 2026-10-28 |
| Branch at writing | `msca-dn-pre-eval`; R9e committed as `47a32d4` (`close r9e`). The R9e tick (four files: `plans/aws_redeployment_tickets.md`, `evidence_v2/R9e/VERIFICATION.md`, `evidence_v2/R9e/RUNLOG.md`, `aws_hardening_worklog_v2.md`) was made after that commit and is the operator's to commit (`tick R9e`) before R10 starts. This file is the operator's to commit too (`starting R10`). |
| For | The agent that runs ticket R10 with the operator in a new session |
| Read first | `CLAUDE.md` (§13, §17 above all: `runner/` is governed by §17; R10 changes provider resolution inside a node body, not the call graph); `plans/aws_redeployment_tickets.md` (inherited constraints; R10; R9 note F-R9-1; R16); `plans/aws_redeployment_handoff_2026-10-21.md` §4 F5, §5 OD12, §6 R10, §7, §7a; §2 of this file and of the R4–R9e handoffs; decision records `aws-redeployment-operator-decisions_2026-10-21` (OD12), `aws-redeployment-od7-model-set_2026-10-21` (OD7-orchestrator, F-R2-2 quotas), `aws-redeployment-r9-runtime-config_2026-10-27` (R9-D6, R9-D7, R9-D12, R9-D21–D23, F-R9-1, F-R9-4, F-R9-5), `aws-redeployment-r9e-eu-region_2026-10-27` (R9e-D1, R9e-D8, R9e-D10, R9e-D18, F-R9e-1); `docs/infrastructure_security/evidence_v2/R9e/` (`STEPS.md` format, `VERIFICATION.md` baseline set, `RUNLOG.md`); code: `runner/decomposed_drafting.py` (`_default_claude_drafter`, `_capture_raw_response`, `_DRAFTER_*` constants, `_GROUNDING_INPUTS`, `draft_section_decomposed`), `runner/agent_runtime.py` (~line 1298, the only caller), `runner/skill_runtime.py` (`_resolve_transport_backend` ~136, the TAPM branches ~1530–1800, `_write_transport_failure_diagnostics` ~962, the response capture ~2030), `runner/semantic_dispatch.py` (its resolution, ~373 persistence), `runner/claude_transport.py`, `runner/transport/config.py`, `runner/transport/tool_loop.py`, `runner/transport/tool_executor.py`, `runner/transport/bedrock_converse.py`, `runner/persistence_policy.py`; tests: `tests/runner/test_excellence_decomposed_drafting.py` (esp. `TestProductionDrafterPromptHardening`, which monkeypatches `runner.claude_transport.invoke_claude_text`), `tests/runner/test_impact_implementation_decomposed_drafting.py`, `tests/runner/test_agent_runtime.py`, `tests/runner/test_e2e_msca_pf_run.py`, `tests/runner/test_section_extra_fields.py`, `tests/runner/test_preseed_suppression_scheduler.py`, `tests/test_production_mode.py`, `tests/test_persistence_policy.py`, `tests/harness/test_converse_judge.py` (the fake boto3 client pattern) |
| Decision records in force | as listed in the R9e handoff, plus `aws-redeployment-r9e-eu-region_2026-10-27` |
| Status | E0, R0–R9, R9e done. Frontier: **R10**, R12a. R11 is unblocked and needs the operator's explicit go (first hourly cost). R15 needs R11 and R12b. R16 stays deferred (OD12). |

## 1. Facts that govern R10

| Fact | Record / evidence |
|---|---|
| **R10 is code only.** No AWS step, no resource, no cost. Evidence is test output and the repository diff, as in R9 and R9e. | ticket R10; R9/R9e precedent |
| **F5:** `runner/decomposed_drafting.py::_default_claude_drafter` imports `runner.claude_transport.invoke_claude_text` (line ~304) and calls it (line ~444) with `model=_DRAFTER_MODEL` (`claude-opus-4-8`), `max_tokens=8000`, `timeout_seconds=1800`, `tools=["Read", "Glob"]` (TAPM). No call to `resolve_provider_config`. `runner/claude_transport.py` has no production-mode guard. | code read 2026-10-28; handoff 2026-10-21 §4 F5 |
| **The one caller** is `runner/agent_runtime.py` (~1298): `draft_section_decomposed(run_id, repo_root, _slug)` with no drafter, so the production drafter is used; any exception becomes an `AgentResult` failure (§17.5.4). Tests inject a fake drafter, so the live path is never exercised in CI except the prompt-hardening tests, which monkeypatch `invoke_claude_text`. | code read |
| **How the skill runtime does it (the pattern to follow):** `_resolve_transport_backend()` (process-cached `resolve_provider_config()`); `claude_cli` → CLI; `bedrock_converse` → `build_converse_backend(config, tools=[READ_TOOL_SCHEMA, GLOB_TOOL_SCHEMA], temperature=0.0, max_tokens=…)` wrapped in `InstrumentedBackend`, then `run_tool_loop(backend, system_prompt, user_prompt, repo_root, allowed_prefixes=…, timeout_seconds=…)`; other tool-calling backends → `build_openai_backend` + the same loop; a backend without tool calling is refused for TAPM. The model is `provider_config.model` (on the host: the secret's `ORCHESTRATOR_TRANSPORT_MODEL`, OD7-orchestrator), not the CLI constant. | `runner/skill_runtime.py` ~1530–1800 |
| **Production mode already refuses** a non-production backend at resolution on both paths, and a missing `AWS_REGION` (R9-D6, R9-D7); `PRODUCTION_BACKENDS = {"bedrock_converse"}`. So routing the drafter through `resolve_provider_config()` makes it refuse `claude_cli` under production mode with a production-mode error. | R9 record |
| **The workstation path:** `.env` sets `ORCHESTRATOR_TRANSPORT_PRESET=CLAUDE_REFERENCE` (backend `claude_cli`), loaded at import of `runner.transport.config` with `override=False` (F-R9-4). So the non-production drafter stays on the CLI once it resolves through the transport layer. **Trap (F-R9-1):** a harness test can leak `.env.harness` (an OpenAI-compatible endpoint) into `os.environ`; a drafter test that does not pin its environment would then route to that provider. Tests must use `clear=True` or set the backend explicitly. | R9 record F-R9-1, F-R9-4; `.env` key and preset name only |
| **A DC-35 gap in the same function (found 2026-10-28):** `_capture_raw_response` writes the drafter's full raw response (`{sub_id}.response.txt`) and, on a transport failure, the transport's stdout/stderr, to `.claude/logs/decomposed_drafting/<run>/<slug>/`, whatever the diagnostic level. Under production mode the level is always `metadata` (`runner/persistence_policy.py`), which DC-35 says prevents prompt and response content being written to disk. The skill runtime and semantic dispatch gate their content files with `allows_content_persistence()`. | code read; register v2 DC-35 |
| **AN1c on the host already covers the drafter:** under production mode `harness.judge.drafter_models()` counts `ORCHESTRATOR_TRANSPORT_MODEL` (R9e-D8), which is the model the drafter will use once it resolves through the transport. | R9e record |
| **Quotas:** Opus 4.6 has 5 requests per minute in this account (F-R2-2); a TAPM drafting call is many Converse rounds. Sequential Phase 8 drafting fits but will be slow; throttling surfaces as a transport error. | OD7 record |
| **R10 does not make DC-38 pass** and does not dispatch Phase 8 on the host; DC-38 stays deferred (OD12; R16). It closes the production-mode bypass. | OD12 |
| **Full suite.** The R9e baseline (202 failed on `d1e767b`) and after-run (200 failed) are by id in `evidence_v2/R9e/`; the suite is order-dependent and makes outbound HTTP requests (F-R9-1; the `.env.harness` key is invalid, R9e-D13); one test can hit a Windows file lock (F-R9e-1). "No new failures" is judged by id (R9-D23). A new baseline on the R10 start commit is still the clean reference. Many Phase 8 runner tests are in the baseline set (F-R9-1), so the drafting tests R10 touches must be read by id. | R9e evidence |
| `CLAUDE.md` §17: the drafter is node-body code reached from `run_agent()`; R10 changes which transport a node body's Claude call goes through (§17.5.2's "configured runtime transport"), not the call graph (§17.1), the result contracts (§17.4) or the failure semantics (§17.3: a transport or resolution failure still surfaces as an agent-body failure). No ticket amends `CLAUDE.md`. | tickets inherited constraints |

## 2. How the operator works

Everything in the R4–R9e handoffs' §2 holds. Added in R9e:

- The operator answers "1–N a"; new points get new numbers, including points found after the baseline.
- **The operator may skip a commit or run a step out of order** (R9e: the baseline ran before `starting R9e`; `close r9e` was committed before the tick). Check `git log` and `git status` at every hand-back and record a deviation rather than asking for a rerun when the tree is the same.
- The device can disconnect mid-call. Before retrying any write, check whether it took effect; never re-append.
- **Agent-side lessons (R9, R9e):**
  - Never run a git command that writes in the connected folder (R9 `RUNLOG.md`). Compare on `git archive HEAD | tar -x -C $HOME/<dir>` copies; run `git init -q` in each copy, because `runner` looks for a `.git` beside `CLAUDE.md`.
  - A device VM venv: `uv venv $HOME/r9venv --python 3.10`; `uv pip install python-dotenv==1.2.2 boto3==1.42.68 pytest httpx pyyaml jsonschema pymupdf==1.28.2` (PyMuPDF installs; python-docx is absent, so leave `tests/runner/test_docx_exporter.py` out of both sides). The session's `$HOME` may be new; re-create it.
  - A device call is capped at ~180 s and background processes die with it. Run the suite in chunks (`tests/harness`; `tests/runner/test_*.py` and `tests/test_*.py` split in eight; `tests/tools` and `tests/runner/*/`), HEAD copy and change copy in parallel, and compare failure sets by id. Tests that depend on `.claude/runs` fail in both copies (environment-specific).
  - Edit with an exact-match, all-or-nothing read-modify-write that keeps each file's line endings (R9e-D18); `runner/decomposed_drafting.py` is LF in the working copy today (check). git prints `LF will be replaced by CRLF` for files already LF; say so in the step sheet.
  - Run the secret scan on every evidence draft; the decision record holds no scan pattern either (F-R9-5).

## 3. R10 as it reads

1. **A test that fails on today's code:** under `ORCHESTRATOR_PRODUCTION_MODE=true`, the drafter never calls the Claude CLI transport.
2. **The existing Phase 8 drafting tests still pass on the workstation's non-production path.**
3. **Phase 8 dispatch is untouched apart from provider resolution.** The gates, scheduler and node states are unchanged.

## 4. Points to settle with the operator before writing code

1. **Where the routing lives.** (a) In `runner/decomposed_drafting.py` only: the production drafter resolves `resolve_provider_config()`; `claude_cli` keeps `invoke_claude_text`; otherwise it builds the backend (`build_converse_backend` / `build_openai_backend` with the Read/Glob schemas) and runs `run_tool_loop`, mirroring the skill runtime; (b) extract a shared TAPM helper used by both the skill runtime and the drafter (one code path, but touches `run_skill`); (c) refuse every non-CLI backend in the drafter and only add the production guard. Proposal: (a) — the ticket's "as the skill runtime does", with `run_skill` untouched (criterion 3).
2. **Which backends.** (a) The skill runtime's set: `claude_cli`, `bedrock_converse`, and tool-calling OpenAI-compatible backends; a backend without tool calling refused (TAPM needs tools); (b) `claude_cli` and `bedrock_converse` only. Proposal: (a), for parity; production mode narrows to Converse anyway.
3. **Model, limits, timeout.** Non-CLI backends use `provider_config.model` (refuse when it is missing, as `build_converse_backend` does); the CLI path keeps `_DRAFTER_MODEL`. `max_tokens` 8000 and the 1800 s timeout carry over to the loop; `max_rounds` stays the loop's default (25) unless the operator wants more for long sub-sections. Proposal: so.
4. **TAPM boundary.** `allowed_prefixes` = `_GROUNDING_INPUTS` (the tool executor then refuses reads outside the declared inputs; the CLI path has no such sandbox). Proposal: so, with a test that a read outside them is refused.
5. **Resolution caching.** (a) Resolve once per `_default_claude_drafter(...)` call (per section), no new process cache; (b) reuse `skill_runtime._resolve_transport_backend()` (process cache, the F-R9-1 trap). Proposal: (a).
6. **Defence in depth in the CLI transport.** (a) `runner/claude_transport.invoke_claude_text` (and its siblings, if any) refuses under production mode with a production-mode error, so any future bypass fails closed; (b) leave the transport as is; R10 fixes the caller only. Proposal: (a), with a test; check first that no production-mode test path calls the CLI legitimately (semantic dispatch and the skill runtime refuse earlier at resolution).
7. **The DC-35 gap (new, §1).** (a) In R10: `_capture_raw_response` writes content (`*.response.txt`, transport stdout/stderr) only when `allows_content_persistence()`; under `metadata` it writes a metadata-only record (sub-section id, sizes, exception class, `sanitize_error_message` text) or nothing; tests for both levels; (b) a separate ticket. Proposal: (a) — the same function, the same production path, and DC-35 is evidenced in R12b on this host.
8. **The failing test (criterion 1).** Proposal: in `tests/runner/test_excellence_decomposed_drafting.py` (or a new `tests/runner/test_decomposed_drafting_transport.py`): with production mode, the `BEDROCK_CONVERSE_EU` preset, a sentinel `AWS_REGION` and model, and `boto3.client` replaced by a fake Converse client, the default drafter drafts one sub-section through Converse while `runner.claude_transport.invoke_claude_text` is patched to fail the test if called; with production mode and a `claude_cli` configuration, it refuses with a production-mode error before any CLI call; one test through `draft_section_decomposed` with the default drafter. Confirm it fails on HEAD (the CLI is called) on the device copy before the change.
9. **Existing tests amended on purpose (criterion 2).** The two `TestProductionDrafterPromptHardening` tests patch `invoke_claude_text` and rely on the drafter reaching it; they get an explicit non-production `claude_cli` environment (`clear=True`), so the F-R9-1 leak cannot reroute them. The decision record names each amended id, as R9-D15.
10. **Criterion 3 as evidence.** The diff touches `runner/decomposed_drafting.py` (and, under point 6 (a), `runner/claude_transport.py`) and tests only; `runner/agent_runtime.py`, `runner/dag_scheduler.py`, `runner/gate_evaluator.py`, the manifest and node states unchanged; step 03 records the diff stat. Proposal: so.
11. **Evidence.** As R9e: `evidence_v2/R10/` with `STEPS.md`, `RUNLOG.md`, `R10_<NN>_*`, `VERIFICATION.md`; baseline on the `starting R10` commit; the R10 tests and the touched modules; full suite after, by id (R9-D23); old-ID guard; secret scan last. Register v2: a note on DC-35 (the drafter honours the diagnostic level) and on DC-38 (F5 closed; still deferred, OD12), statuses unchanged. Proposal: so.
12. **Scope.** R10 does not run Phase 8 on the host (R16, deferred), change the drafter's prompts, quotas or retry behaviour (§17.5.4: no retry), or fix F-R9-1. Proposal: confirm.

## 5. Step sheet outline (suggestion)

`evidence_v2/R10/STEPS.md`, workstation only.

1. Baseline: commit `tick R9e` and `starting R10` first (or record the deviation); `git log -2` and status; versions; full suite → `R10_01_baseline-pytest.txt`. Hand back.
2. The agent shows on the device that the criterion-1 test fails on HEAD, writes the change, the tests and the decision record `aws-redeployment-r10-drafter-transport_<date>`, and runs its subset and the chunked suite comparison in the VM copies.
3. Diff stat; the R10 tests and the drafting, agent-runtime, production-mode, persistence and transport modules → `R10_03_*`.
4. Full suite after → `R10_04_full-pytest.txt`, compared by id.
5. Old-ID guard; secret scan last. Commit; confirm.

## 6. Files (expected)

| Path | What |
|---|---|
| `runner/decomposed_drafting.py` | provider resolution in the production drafter; content capture gated by the diagnostic level |
| `runner/claude_transport.py` | production-mode refusal (point 6 (a) only) |
| `tests/runner/test_excellence_decomposed_drafting.py` (or a new `tests/runner/test_decomposed_drafting_transport.py`), `tests/runner/test_impact_implementation_decomposed_drafting.py`, `tests/test_production_mode.py` or `tests/runner/test_claude_transport.py` | tests |
| `docs/tier4_orchestration_state/decision_log/aws-redeployment-r10-drafter-transport_<date>.json` | the §4 answers |
| `docs/infrastructure_security/evidence_v2/R10/` | `STEPS.md`, `RUNLOG.md`, `R10_<NN>_*`, `VERIFICATION.md` |
| `docs/infrastructure_security/aws_hardening_control_register_v2.md` | notes on DC-35 and DC-38 |
| `docs/infrastructure_security/aws_hardening_worklog_v2.md` | entries |
| `plans/aws_redeployment_tickets.md` | R10 ticked |

## 7. Done for R10

Every `VERIFICATION.md` criterion PASS; the three ticket criteria PASS; the criterion-1 test shown failing on the start commit and passing after; the full suite shows no failure that is not in the R10 baseline (by id), the amended ids passing; old-ID guard and secret scan CLEAN (scan last); register notes and worklog entry; the operator commits and confirms. Then tick R10. R16 stays deferred (OD12); R12b, R15 and R13 are unaffected except that R12b's DC-35 evidence can now cite the drafter.
