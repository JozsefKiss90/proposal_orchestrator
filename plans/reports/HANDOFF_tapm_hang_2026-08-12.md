# Handoff — Phase 1 hangs forever at `skill INVOKE`; the 1200 s timeout never fires

**Status:** MECHANISM RESOLVED 2026-08-13; trigger unattributed. The child stalls pre-`main()` and the timeout was structurally unreachable. Fixes landed in `runner/claude_transport.py` make any recurrence a diagnosable 1200 s failure. See §0.
**Date:** 2026-08-12 · **Branch:** `fieldwise-run-01` · **Blocks:** ticket 8 (Run Phases 1–2) — unblocked; Phase 1 passed its gate on run `11d4fcae`.

---

## 0. Resolution — 2026-08-13

### 0.1 H5 is dead

The §5 test ran the exact runner invocation: `--tools Read,Glob`, `--system-prompt`, 35 KB stdin. It completed in 44 s. The CLI denies unapproved tool calls non-interactively (`is_error: true` tool result) and exits cleanly. stdin drained at 6 s.

The full command also reproduced green. `python -m runner --phase 1 --verbose` completed all four Phase 1 skills (484 s, 223 s, 349 s, 232 s) and passed `phase_01_gate`.

### 0.2 What is proven — the child stalls pre-`main()`, in its first seconds

Forensics. Neither hung run left a CLI session transcript in `~/.claude/projects/`, wrote any `~/.claude` state, or spawned a single MCP server (no `claude-cli-nodejs` log stamps at 19:31Z or 22:06–22:27Z). A healthy child drains stdin at ~3–6 s and stamps MCP logs within ~10 s. Both hung children therefore froze within their first seconds and stayed frozen for hours. Diag trials completed at 23:01 local while run `f3a12cac` hung concurrently, which excludes global conditions (network, rate limit).

That early stall explains both §1 anomalies. A child that never reads stdin leaves the 35 KB prompt write blocked, and CPython's `communicate(input=...)` writes stdin synchronously before any deadline check, so the 1200 s timeout is structurally unreachable.

### 0.2a Trigger — unattributed; two candidate classes

The operator confirms the terminal was untouched for at least the first hour of each hang. The initial stall was therefore not caused by console interaction. The candidate classes that fit "frozen at process start, twice, user-terminal only, no traces":

- **Unserviced console at spawn.** `tools/diag_console_freeze.py` proves the mechanism: a child attaching to a frozen console blocks pre-`main()` (blocked 24.9 s under freeze; drained in 0.11 s with `CREATE_NO_WINDOW`). A console can be unserviced without user input (e.g. a stalled ConPTY consumer), but no such state was observed.
- **Startup deadlock in the stale CLI binary.** The runner resolves `AppData\Roaming\npm\claude.EXE` — a 242 MB self-contained build dated 2026-03-23 (v2.1.81), not the 2.1.224 the shell runs. An internal early-startup deadlock fits the evidence equally well.

Two samples, both unreproducible after the fact; the classes cannot be distinguished post-hoc. The fixes below cover both, and the new tree snapshot makes the next occurrence self-identifying.

### 0.3 Fixes landed (`runner/claude_transport.py`)

1. **Unconditional deadline** (§6 fix 1). A daemon thread now writes stdin; `communicate(timeout=...)` always holds the deadline. A never-draining child becomes `ClaudeCLITimeoutError` + tree kill, not an infinite hang.
2. **Console detach** (§6 fix 2 class). `_tree_killable_popen_kwargs()` adds `CREATE_NO_WINDOW` on Windows. The operator's terminal can never freeze the child, closing the unserviced-console trigger class.
3. **Diagnosable timeout.** The timeout error states when stdin was never fully written (the pre-`main()`-stall signature) and embeds a pre-kill snapshot of the child's process tree, so the next occurrence identifies where the child was stuck.

Regression locks: `tests/runner/test_claude_transport_treekill.py::TestStdinWriteDeadline` (red against the old code) and `TestTreeKillablePopenKwargs::test_windows_detaches_child_console`. Transport suites 57/57; transport-hook 27/27; TAPM skill-runtime 35/35. Live smoke through the fixed transport returned in 52 s.

### 0.4 Still open (operator decisions, from §6)

- **Pin the CLI to an absolute path — now strongly recommended.** Python subprocess resolves the stale March build (2.1.81, a trigger suspect per §0.2a) while the shell runs 2.1.224. Removing or replacing `AppData\Roaming\npm\claude.EXE` also removes that suspect. **Mechanism landed (TR-3); the version choice is yours — see §0.5.**
- Isolate the runner's CLI environment (`--strict-mcp-config` or a dedicated settings dir) to cut the 20–30 s / ~$0.10+ startup floor.

### 0.5 CLI pin — TR-3

Why the two layers disagreed: the runner spawns with `shell=False`, so the OS
resolves `claude` through PATH × PATHEXT — not the resolution PowerShell
performs. Neither layer was wrong; they answer different questions, and
nothing in the run record said which build had served an invocation.

Landed:

1. `runner/claude_transport.py` — `resolve_claude_cli()`. `cmd[0]` is now the
   *resolved* executable, never the bare name. `ORCHESTRATOR_CLAUDE_CLI_PATH`
   pins it; unset keeps the old behaviour but resolves to an absolute path.
   Fail-closed: a pin naming a missing file, an unresolvable bare name, or
   (on Windows) a `.ps1` raises `ClaudeCLIUnavailableError` before any spawn.
   It never falls back to a path search — a typo must stop the run, not
   quietly restore the ambiguity being closed.
2. The resolved path is logged once per run under `--verbose`
   (`runner/__main__.py` wires the transport logger), so every future run
   states which build it used. Combined with §0.3's tree snapshot, a
   recurrence names both the build and where its child was stuck — which is
   what would distinguish §0.2a's two trigger classes.
3. `tools/diag_cli_resolution.py` — enumerates every `claude*` on PATH and in
   the known install locations, probes each with `--version` **through the
   production spawn path**, reports what `shutil.which` and `Get-Command`
   each pick, and prints a ready-to-paste `.env` line.

Regression lock: `tests/runner/test_claude_transport.py::TestCliPathResolution`
(15 cases — precedence, quote/`~`/`%VAR%` handling, every fail-closed branch,
and the `.ps1` rejection as a Windows-only spawn rule).

Operator action — decide the version, then pin it:

```powershell
python tools/diag_cli_resolution.py
# then add the recommended line to .env
```

The two candidates pull in opposite directions. §3 measures 2.1.81 at
≈$0.099/invocation against 2.1.224 at ≈$0.29 sonnet / $0.50 opus — but 2.1.81
is the March build that §0.2a names as a trigger suspect, and cost is the
cheaper problem of the two. Pinning 2.1.224 retires the suspect; the price
gap is then worth re-measuring after `--strict-mcp-config` lands, since most
of that spread is MCP, plugin and skill context the runner never uses.

**Windows caveat:** pin the `.exe` or `.cmd`, never the `.ps1`.
`Get-Command claude` reports the `.ps1` shim, and `CreateProcess` cannot start
a PowerShell script — which is why the transport rejects that value at
resolution rather than letting it fail as an opaque `WinError 193` mid-run.

Sections below are the pre-resolution record, kept verbatim.

---

## 1. Symptom

`python -m runner --run-id <uuid> --phase 1 --verbose` prints through to:

```
[INFO]   skill START  id=call-requirements-extraction  mode=tapm  node=-  run=<id>
[INFO]   skill INVOKE id=call-requirements-extraction  sys=1155  user=35714  timeout=1200s  backend=claude_cli
```

and then produces nothing, indefinitely.

Two observed runs:

| Run | Started (UTC) | Observed | Wrote after start? |
|-----|---------------|----------|--------------------|
| `f3a12cac-484e-48d2-a7d2-bef642d6c9d3` | 19:31:12 | ~93 min, still hung | No. `invocation_ledger.jsonl` created, 0 bytes. No `skill_diag/`, no `logs/` |
| `a5827388-7a40-4530-b46a-b54f3514cc30` | ~22:0x | same | same |

**Two anomalies, not one.** (a) The call never returns. (b) `TAPM_TIMEOUT_SECONDS = 1200`
never fires — at 93 minutes it should have raised `ClaudeCLITimeoutError`, tree-killed the
child, and written a transport-failure diagnostic bundle. It wrote nothing. Any proposed
cause must explain **both**.

**Ctrl+C does not interrupt.** The terminal must be closed. This is expected rather than a
third symptom: CPython on Windows does not deliver `KeyboardInterrupt` while the main thread
is blocked in `Thread.join()`, which is where `communicate()` waits.

---

## 2. What is NOT the cause — do not re-investigate

| # | Hypothesis | Killed by |
|---|-----------|-----------|
| H1 | Invalid/unavailable model id after the sonnet→opus change | `claude -p "say OK" --model claude-opus-4-6` returns in 3 s. Hangs identically on **both** models. Constants reverted to `claude-sonnet-4-6` |
| H2 | `.claude/settings.local.json` permission allowlist pins the model string | `python -m runner` spawns `claude` via `subprocess`, not through Claude Code's permission layer. That allowlist is irrelevant to a direct run |
| H3 | Windows stdin-write deadlock: 35,714 chars into a ~4 KB pipe | Trial C below wrote 35,721 chars through a pipe and completed in 19.9 s |
| H4 | Piped stdout prevents the CLI terminating | Trial C used piped stdout and completed |

**Note:** an earlier version of `tools/diag_stdin_deadlock.py` printed
"PIPED STDOUT IS THE BUG". That verdict was wrong — its reading logic returned on trials A
and B without weighing C. Ignore any transcript quoting it.

---

## 3. Evidence

`tools/diag_stdin_deadlock.py`, three trials, `claude-sonnet-4-6`:

| Trial | stdin | stdout | Result |
|-------|-------|--------|--------|
| A | 6 chars | pipe | TIMEOUT at 34.4 s (30 s limit) |
| B | 6 chars | console | completed 24.3 s |
| C | **35,721 chars** | **pipe** | **completed 19.9 s, 7,737 chars out** |

**Read A as jitter, not a distinct failure.** All three sit in a 20–30 s band. Every
invocation pays ~20–30 s of CLI startup, so a 30 s limit is a coin flip.

**Two different CLI versions are on PATH.** PowerShell resolves **2.1.224** (MCP servers
report `pending`). Python `subprocess` resolves **2.1.81**, which fully connects five local
MCP servers — `context7`, `serena`, `mcpvault`, `smart-connections`, `filesystem` — and that
is where the 20–30 s goes. The runner is not exercising the CLI you get at the prompt.

**Cost floor per invocation** (trivial prompt, whole session context cached):
2.1.81 ≈ **$0.099**; 2.1.224 ≈ **$0.29** sonnet / **$0.50** opus. Mostly MCP, plugin and
skill context the runner never uses.

---

## 4. Live hypothesis — H5, and it explains both anomalies

Trial C omitted two flags the runner actually passes (`runner/skill_runtime.py:1403-1414`):

```python
invoke_claude_text(
    system_prompt=system_prompt,   # 1,155 chars -> --system-prompt
    user_prompt=user_prompt,       # 35,714 chars -> stdin
    tools=["Read", "Glob"],        # -> --tools Read,Glob     <-- UNTESTED
    timeout_seconds=TAPM_TIMEOUT_SECONDS,   # 1200
)
```

**The chain:**

1. `--tools Read,Glob` under `permissionMode: "default"` makes the CLI want approval for a
   tool call. `communicate()` has already written and **closed** stdin, so the answer can
   never arrive. The CLI stalls and never exits.
2. Because it stalls **before draining stdin**, the 35,714-char write cannot complete.
3. CPython's Windows `Popen._communicate()` calls `self._stdin_write(input)` **synchronously
   on the calling thread, before any deadline check**. Blocked there, the code never reaches
   `stdout_thread.join(remaining_time)` — so `TimeoutExpired` is structurally unreachable.

That is why trial C passed (no `--tools` → CLI drains stdin promptly → 35 KB is harmless)
and why the real run hangs with the timeout inert. **It is the only hypothesis so far that
accounts for the silent 1200 s as well as the hang.**

**Confidence: moderate.** The `--tools` half is untested. The `_stdin_write` half is read
from CPython 3.11 source, not observed.

---

## 5. Next step — one test, already written

```powershell
Get-Process claude,node -EA SilentlyContinue | Stop-Process -Force
python tools/diag_stdin_deadlock.py
```

The current version replicates the exact runner invocation (`--system-prompt` + `--tools
Read,Glob` + 35 KB stdin), streams every line with an elapsed stamp, and self-kills at 90 s.

| Where the stream stops | Meaning |
|------------------------|---------|
| after `init` / system events | CLI never began work — startup blocker, look at MCP servers |
| after an assistant turn or `tool_use` | **H5 confirmed** — permission prompt on closed stdin |
| completes normally | H5 dead. Remaining delta is the `_env` the transport builds, or real prompt content |

---

## 6. Fixes to consider once the cause is known

1. **Make the deadline unconditional.** Write stdin from a daemon thread, or add a watchdog
   that hard-kills at `timeout_seconds` regardless of where `communicate()` is blocked. A run
   that hangs forever is worse than one that fails: it produced no diagnostics across 93
   minutes and cost a terminal each time. **Do this even if H5 is wrong.**
2. **Run non-interactively.** If H5 confirms, the CLI must not be able to prompt — a
   permission mode that cannot block, or a pre-approved tool set.
3. **Pin the CLI.** Resolve `claude` to an absolute path so the runner stops silently using
   2.1.81 while the operator tests 2.1.224.
4. **Isolate the runner's CLI environment.** A dedicated settings directory or
   `--strict-mcp-config` removes five MCP servers from the failure surface and cuts the
   20–30 s / ~$0.10–0.50 floor per invocation.

---

## 7. Map

| Path | Why it matters |
|------|----------------|
| `runner/skill_runtime.py:1396-1414` | TAPM invocation. Emits the INVOKE log; passes `tools`, `timeout_seconds` |
| `runner/skill_runtime.py:93` | `TAPM_TIMEOUT_SECONDS = 1200` |
| `runner/claude_transport.py:407-418` | Command construction (`--tools`, `--system-prompt`) |
| `runner/claude_transport.py:446-495` | `Popen` + `communicate(timeout=…)` + the timeout/tree-kill path |
| `runner/claude_transport.py:278` | `_kill_process_tree` |
| `runner/{semantic_dispatch.py:94, skill_runtime.py:75, decomposed_drafting.py:78}` | Model constants — **all `claude-sonnet-4-6`**, reverted |
| `tools/diag_stdin_deadlock.py` | The repro |

**Environment:** Windows, Python 3.11.9 win32, Claude Code 2.1.81 (subprocess) / 2.1.224
(shell), backend `claude_cli`, preset `CLAUDE_REFERENCE`, `production_mode=False`.
Rate limit: five-hour window, overage rejected (`org_level_disabled`) — not implicated, but
a run that exhausts it may stall rather than error, so rule it out before concluding.

**Housekeeping:** every hung attempt orphans `claude`/`node` processes. Some reached 1,285
CPU-seconds. Sweep before each repro or the machine degrades.

---

## 8. Uncommitted work in the tree

- three model constants: opus → **reverted to sonnet**
- docstrings in `semantic_dispatch.py`, `gate_evaluator.py` now reference `AGENT_MODEL`
  instead of naming a model — **keep**, they are model-agnostic and correct
- four `claude-opus-4-6` entries in `.claude/settings.local.json` — harmless, additive, and
  (per H2) never relevant to a direct runner invocation
- `tools/diag_stdin_deadlock.py` — new

`git diff` before committing alongside the ticket 7 fold.

## 9. Fable session output — 2026-08-13

An earlier version of this section recorded the session's first conclusion: a QuickEdit click froze the console and caused the hang. The operator refuted the trigger: the terminal was untouched for at least the first hour of each hang.

MCP log forensics confirmed the refutation. The hung children spawned no MCP servers, so they froze within their first seconds — long before any interaction. §0 holds the corrected record: mechanism proven and fixed, trigger unattributed (§0.2a).

Session deliverables:

- Transport fixes and regression tests per §0.3. Transport suites 57/57; live CLI smoke passed.
- Phase 1 passed `phase_01_gate` on run `11d4fcae`, writing real Tier 2B extracted files and Tier 4 phase outputs (ticket 8 evidence).
- `tools/diag_console_freeze.py` — frozen-console mechanism demo; `--detached` shows the `CREATE_NO_WINDOW` immunity.
- Committing is left to the operator, alongside the ticket 7 fold.