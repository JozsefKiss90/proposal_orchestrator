# Handoff — Phase 1 hangs forever at `skill INVOKE`; the 1200 s timeout never fires

**Status:** RESOLVED 2026-08-13. Root cause: frozen console. Fixes landed in `runner/claude_transport.py`. See §0.
**Date:** 2026-08-12 · **Branch:** `fieldwise-run-01` · **Blocks:** ticket 8 (Run Phases 1–2) — unblocked; Phase 1 passed its gate on run `11d4fcae`.

---

## 0. Resolution — 2026-08-13

### 0.1 H5 is dead

The §5 test ran the exact runner invocation: `--tools Read,Glob`, `--system-prompt`, 35 KB stdin. It completed in 44 s. The CLI denies unapproved tool calls non-interactively (`is_error: true` tool result) and exits cleanly. stdin drained at 6 s.

The full command also reproduced green. `python -m runner --phase 1 --verbose` completed all four Phase 1 skills (484 s, 223 s, 349 s, 232 s) and passed `phase_01_gate`.

### 0.2 Root cause — a frozen console blocks the child before `main()`

Forensics first. Neither hung run left a CLI session transcript in `~/.claude/projects/`, and neither wrote any `~/.claude` state. The child stalled before creating a session and before draining stdin. Diag trials completed at 23:01 local while run `f3a12cac` hung concurrently, which excludes global conditions (network, rate limit).

The mechanism, demonstrated on this machine by `tools/diag_console_freeze.py`:

- A QuickEdit text selection (enabled here: `HKCU\Console` `QuickEdit=1`) or Ctrl+S freezes the console host process.
- A child process attaching to a frozen console blocks before `main()`. It never reads stdin.
- The 35 KB prompt write then blocks forever: CPython's `communicate(input=...)` writes stdin synchronously before any deadline check, so the 1200 s timeout is structurally unreachable.
- Ctrl+C is swallowed by selection mode. Closing the terminal is the only exit. Both §1 anomalies follow from one stall.

Measured: a console-attached piped child blocked 24.9 s — the full freeze window — and drained instantly on resume. A `CREATE_NO_WINDOW` child drained the same payload in 0.11 s while the console stayed frozen.

This also explains the immunity pattern. Every completed trial was agent-spawned into a console nobody clicks. Both hangs ran in the operator's interactive terminal.

Attribution caveat: the past hangs cannot be rerun. Console freeze is the only hypothesis consistent with every observed fact, and the fixes below remove the entire failure class regardless of the exact freeze trigger.

### 0.3 Fixes landed (`runner/claude_transport.py`)

1. **Unconditional deadline** (§6 fix 1). A daemon thread now writes stdin; `communicate(timeout=...)` always holds the deadline. A never-draining child becomes `ClaudeCLITimeoutError` + tree kill, not an infinite hang.
2. **Console detach** (§6 fix 2 class). `_tree_killable_popen_kwargs()` adds `CREATE_NO_WINDOW` on Windows. The operator's terminal can never freeze the child.
3. **Diagnosable timeout.** The timeout error now states when stdin was never fully written — the frozen-console signature.

Regression locks: `tests/runner/test_claude_transport_treekill.py::TestStdinWriteDeadline` (red against the old code) and `TestTreeKillablePopenKwargs::test_windows_detaches_child_console`. Transport suites 57/57; transport-hook 27/27; TAPM skill-runtime 35/35. Live smoke through the fixed transport returned in 52 s.

### 0.4 Still open (operator decisions, from §6)

- Pin the CLI to an absolute path. Python subprocess resolves 2.1.81 (`claude.EXE`) while the shell runs 2.1.224 (`claude.ps1`).
- Isolate the runner's CLI environment (`--strict-mcp-config` or a dedicated settings dir) to cut the 20–30 s / ~$0.10+ startup floor.

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

## 9. Falbe sessions output 

Diagnosed and fixed. The hang was never the CLI flags — it was a frozen console. Full story:

Root cause

When you click (QuickEdit selection) or press Ctrl+S in the terminal running python -m runner, Windows freezes that console's host process. A child process that spawns attached to a frozen console blocks before main() — the claude CLI never started working and never read stdin. The 35 KB prompt write then blocked forever, and because CPython's communicate(input=…) writes stdin synchronously before any deadline check, the 1200 s timeout was structurally unreachable. Ctrl+C was swallowed by selection mode. One stall, both anomalies.

How it was pinned down

- H5 died first: the handoff's own next-step test completed in 44 s — the CLI denies unapproved tools non-interactively and exits; stdin drained at 6 s.
- The real command reproduced green: python -m runner --phase 1 completed all four skills and passed phase_01_gate (run 11d4fcae) — so the bug was environmental, not deterministic. Side effect worth knowing: that run wrote real Phase 1 artifacts (Tier 2B extracted + Tier 4 phase output), which is your ticket 8 evidence.
- Forensics: neither hung run left a CLI transcript or any ~/.claude write — theiag trials succeeded at 23:01 while run 1 was concurrently hung, excludingnetwork/rate-limit causes. Every completed invocation was agent-spawned (headless console); both hangs ran in your interactive terminal. Your registry has QuickEdit=1.
- Mechanism proven on your machine: with the console host suspended, a piped child blocked 24.9 s (the whole freeze) and drained instantly on resume — tools/diag_console_freeze.py reproduces this on demand.

Fixes (in runner/claude_transport.py)

1. Unconditional deadline — stdin is written from a daemon thread, so communicate(timeout=…) always fires; a wedged child now becomes ClaudeCLITimeoutError + tree-kill + diagnostics instead
of a 93-minute silent hang.
2. CREATE_NO_WINDOW on Windows — the CLI child gets its own invisible console, so clicking in your terminal can never freeze it again (verified: detached child drained in 0.11 s while the console was frozen).
3. The timeout error now says when stdin never drained — the frozen-console sign

Regression tests added at the real-process seam (TestStdinWriteDeadline, red against the old code, plus the console-detach assertion). Transport suite 57/57, transport-hook 27/27, TAPM skill-runtime 35/35, and a live CLI smoke through the fixed transport passed. The handoff report is updated to RESOLVED with the full record.

Left for you (from the handoff's §6, deliberate non-changes)

- Pin the CLI path: python resolves claude.EXE = 2.1.81 while your shell runs 2.1.224 — pick one deliberately (2.1.224 costs ~3–5× per invocation per the handoff's measurements).
- --strict-mcp-config for the runner would cut the ~20–30 s / ~$0.10 startup flo
- The tree has uncommitted work (this fix, the diag tools, the ticket 7 fold items) — I've left committing to you.