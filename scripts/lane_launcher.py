"""
lane_launcher.py — operator harness for the Phase-8 debug/calibration lanes.

Uses the Claude Agent SDK to (1) always load brief + handoff + CONTEXT.md into context, (2) expose
.claude/skills/ (incl. diagnosing-bugs), (3) launch one lane at a time with lane-appropriate tools,
(4) run the Lane-B judgment items as a deterministic N-skeptic majority vote (Python-orchestrated),
(5) PERSIST each vote's verdicts to scripts/vote_results/ so later steps consume them, and
(6) fail SOFT — a session that hits its turn ceiling reports cleanly instead of crashing.

Operator tool — deliberately SEPARATE from the constitutionally-governed runtime (runner/, §17).

--------------------------------------------------------------------------------------------------
VERIFY BEFORE RUN — SDK option names/enums drift. Pin the version, check the ref:
  https://code.claude.com/docs/en/agent-sdk/python  and  .../agent-sdk/skills
Confirm your surface:
  python -c "from claude_agent_sdk import ClaudeAgentOptions; import inspect; print(inspect.signature(ClaudeAgentOptions))"
BILLING: the SDK spawns your local `claude` CLI, so it uses your Max subscription — UNLESS
ANTHROPIC_API_KEY (or CLAUDE_CODE_USE_BEDROCK/VERTEX, ANTHROPIC_AUTH_TOKEN) is set, which silently
diverts to API billing. In PowerShell: `echo $env:ANTHROPIC_API_KEY` (should be empty).
--------------------------------------------------------------------------------------------------
"""

import asyncio
import inspect
import json
import os
import re
import sys
from pathlib import Path

from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage  # verify surface vs your version

REPO = Path(r"C:\Code\proposal_demo\proposal_orchestrator")
BRIEF = REPO / "plans" / "DEBUG_KICKOFF_phase8_calibration.md"
HANDOFF = REPO / "HANDOFF_phase8_m2t10_2026-07-22.md"
CONTEXT = REPO / "CONTEXT.md"
VOTE_DIR = REPO / "scripts" / "vote_results"   # persisted verdicts live here
VERBOSE = os.environ.get("LANE_VERBOSE") == "1"  # set LANE_VERBOSE=1 to print the raw SDK message stream

OPUS_MODEL = None    # None -> inherit your CLI default (already Opus 4.8). Set a literal id only to pin.
DEFAULT_MODEL = None

# ---- reasoning effort (version-adaptive; see prior notes) ----------------------------------------
_OPT_PARAMS = set(inspect.signature(ClaudeAgentOptions).parameters)


def _effort_kwargs(effort: str | None) -> dict:
    if not effort:
        return {}
    if "effort" in _OPT_PARAMS:
        return {"effort": effort}
    if "thinking" in _OPT_PARAMS:
        return {"thinking": {"type": "adaptive"}}
    return {"extra_args": {"output-config": json.dumps({"effort": effort})}}  # verify flag via `claude --help`


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else f"[missing: {p}]"


def _always_on_context(lane_note: str, extra: str = "") -> str:
    return (
        f"You are running an operator debug/calibration lane on {REPO}.\n\n"
        f"=== LANE ===\n{lane_note}\n\n"
        f"{extra}"
        f"=== CONTEXT.md (runtime module map) ===\n{_read(CONTEXT)}\n\n"
        f"=== DEBUG KICKOFF BRIEF ===\n{_read(BRIEF)}\n\n"
        f"=== HANDOFF (thread state) ===\n{_read(HANDOFF)}\n"
    )


def _make_options(*, allowed_tools, model, effort, system_append, max_turns=40) -> ClaudeAgentOptions:
    if isinstance(model, str) and model.startswith("<"):
        raise ValueError(f"model is still a placeholder ({model!r}) — set a real id or use None.")
    base = dict(
        cwd=str(REPO),
        setting_sources=["project"],
        skills="all",
        allowed_tools=allowed_tools,
        model=model,
        system_prompt={"type": "preset", "preset": "claude_code", "append": system_append},
        max_turns=max_turns,
    )
    return ClaudeAgentOptions(**base, **_effort_kwargs(effort))


def _tool_arg(inp) -> str:
    if isinstance(inp, dict):
        for key in ("file_path", "path", "command", "pattern", "skill", "query", "url", "prompt"):
            if key in inp:
                val = str(inp[key]).replace(str(REPO) + "\\", "").replace(str(REPO) + "/", "").replace("\n", " ")
                return (val[:100] + "…") if len(val) > 100 else val
    return ""


def _render(message) -> None:
    """Concise, human-readable progress: tool calls as one-liners, Claude's narration, and a compact
    final summary. Skips SDK bookkeeping (system/task/usage/tool-results). LANE_VERBOSE=1 = raw stream."""
    if VERBOSE:
        print(message)
        return
    kind = type(message).__name__
    if kind == "ResultMessage" or hasattr(message, "total_cost_usd"):
        bits = []
        st = getattr(message, "subtype", None)
        if st:
            bits.append(str(st))
        nt = getattr(message, "num_turns", None)
        if isinstance(nt, int):
            bits.append(f"{nt} turns")
        dur = getattr(message, "duration_ms", None)
        if isinstance(dur, (int, float)):
            bits.append(f"{round(dur / 1000)}s")
        cost = getattr(message, "total_cost_usd", None)
        if isinstance(cost, (int, float)):
            bits.append(f"~${cost:.2f} est")
        print("  · " + (", ".join(bits) if bits else "result"))
        return
    content = getattr(message, "content", None)
    if kind == "AssistantMessage" and isinstance(content, list):
        for block in content:
            bkind = type(block).__name__
            if bkind == "ThinkingBlock":
                continue
            if bkind == "ToolUseBlock" or (hasattr(block, "name") and hasattr(block, "input")):
                arg = _tool_arg(getattr(block, "input", {}) or {})
                print(f"  → {getattr(block, 'name', 'tool')}{(' ' + arg) if arg else ''}")
            elif bkind == "TextBlock" or hasattr(block, "text"):
                txt = (getattr(block, "text", "") or "").strip()
                if txt:
                    print(txt)
        return
    # SystemMessage / Task*Message / UserMessage(tool results) / StreamEvent -> skipped as noise


async def _drive(opener: str, options: ClaudeAgentOptions, label: str) -> str | None:
    """Run one session with concise output (LANE_VERBOSE=1 for the raw stream). Never crashes on a
    turn-ceiling/error result — reports and returns."""
    print(f"\n▶ {label} — running (Ctrl-C to abort)…")
    result, stopped = None, None
    try:
        async for message in query(prompt=opener, options=options):
            if isinstance(message, ResultMessage):
                result = getattr(message, "result", None)
                if getattr(message, "is_error", False):
                    stopped = getattr(message, "terminal_reason", None) or "error"
            _render(message)
    except Exception as e:  # SDK raises on error_max_turns etc. — swallow into a clean report
        stopped = stopped or str(e)
    if stopped:
        print(f"\n[!] {label} STOPPED EARLY: {stopped}")
        print("    Any edits it made are on disk — review `git diff` before trusting them.")
        print("    If it ran out of turns, raise this lane's max_turns or split the task smaller.")
    else:
        print(f"✓ {label} — done.")
    return result


# ============================ SINGLE-SESSION LANES ================================================
LANES = {
    "C-calibration": dict(
        model=DEFAULT_MODEL, effort="medium", max_turns=40,
        allowed_tools=["Read", "Grep", "Glob", "Bash"],
        lane_note="Lane C. Measurement, NOT debugging — do not invoke diagnosing-bugs.",
        opener=(
            "Lane C only: run eval-harness E2 (status-aware faithfulness) + E3 (ledger completeness) "
            "offline on the current artifacts to quantify the coarse claim ledger (handoff §4.4). "
            "Report the numbers; make no code changes."
        ),
    ),
    "A-transport": dict(
        model=OPUS_MODEL, effort="high", max_turns=80,
        allowed_tools=["Read", "Grep", "Glob", "Write", "Edit", "Bash"],
        lane_note="Lane A. Runs LOCALLY (needs the Windows `claude` CLI). Loop before hypothesis.",
        opener=(
            "Use the diagnosing-bugs skill to debug the transport 2-hour hang (§4.2). Build the Phase-1 "
            "red-capable loop from the brief (fake unkillable child + orphaned-PID assertion) and show it "
            "going RED before proposing any hypothesis. Only then propose the Popen + tree-kill fix, and "
            "stress its known risks (killpg/setsid, taskkill, PID-reuse race, PIPE deadlock)."
        ),
    ),
}
# NOTE: post-vote work is verdict-driven, so nothing runs into a wall like the old monolithic
# B-write-seams did (it assumed a fix had cleared and tried two at once):
#   * apply <item>  — per-item: reads the verdict and does what it warrants
#                     (apply the prescribed fix + its test if REFUTED; write the seam if it HELD UP).
#   * seams [item]  — B-write-seams, RESTORED and made safe: writes the seam ONLY for items whose
#                     latest verdict HELD UP; on a refuted/absent verdict it reports and skips.


async def run_lane(name: str) -> str | None:
    lane = LANES[name]
    options = _make_options(allowed_tools=lane["allowed_tools"], model=lane["model"], effort=lane["effort"],
                            system_append=_always_on_context(lane["lane_note"]), max_turns=lane["max_turns"])
    return await _drive(lane["opener"], options, f"lane {name}")


# ============================ OPTION (b): DETERMINISTIC N-VOTE ====================================
_VERDICT_INSTRUCTION = (
    "End with EXACTLY one line and nothing after it:\n"
    'VERDICT_JSON: {{"holds_up": true|false, "confidence": "low|medium|high", '
    '"top_defect": "<one line>", "lens": "<your lens>"}}\n'
    "holds_up=false means you found a real defect that should block {block}."
)

VOTE_LANES = {
    "B-checkpoint-decision": dict(
        model=OPUS_MODEL, effort="high", block="adopting option 1 as the checkpoint-publish contract",
        lane_note="Lane B decision. CONTRACT decision, not a bug. Do NOT build a repro loop. Reasoning only.",
        lenses=["provenance-integrity", "operational-what-breaks", "cost-vs-option-2-full-fresh-run"],
        opener=(
            "Lane B, checkpoint-publish run_id (§2). Adversarially REFUTE option 1 (accept bootstrapped "
            "gate results, validated against original_run_id). Treat option 3 (re-stamp) as provenance "
            "falsification. If option 1 survives, say what one-line contract to write into checkpoint-publish."
        ),
    ),
    "B-review-preseed": dict(
        model=OPUS_MODEL, effort="high", block="committing the preseed-suppression fix as-is",
        lane_note="Lane B review. Read-only; refute the fix. Do not modify files.",
        lenses=["correctness-and-missed-code-paths", "canonical_pack-vs-unapplied-assumptions", "brittle-name-suffix-match"],
        opener=(
            "Refute the preseed-suppression fix in runner/dag_scheduler.py (drops *_section_assembler + "
            "*_assumption_applier, keeps canonical_pack_deriver in preseed mode). Find a scenario where "
            "it is wrong or inconsistent; quote the code."
        ),
    ),
    "B-review-schemaid": dict(
        model=OPUS_MODEL, effort="high", block="committing the schema_id emit/backfill as-is",
        lane_note="Lane B review. Read-only; refute the fix. Do not modify files.",
        lenses=["every-write-path-covered", "backfill-idempotency-and-safety", "schema-contract-match"],
        opener=(
            "Refute the gate-result schema_id fix (runner/gate_evaluator.py emits schema_id; "
            "tools/backfill_gate_result_schema_id.py backfilled 13 legacy results). Does the emit cover "
            "EVERY gate_result write path? Is the backfill safe to re-run? Quote the code."
        ),
    ),
}


def parse_verdict(text: str | None) -> dict | None:
    if not text:
        return None
    lines = [ln for ln in text.splitlines() if "VERDICT_JSON:" in ln]
    if not lines:
        return None
    raw = lines[-1].split("VERDICT_JSON:", 1)[1].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw)
        try:
            return json.loads(m.group(0)) if m else None
        except json.JSONDecodeError:
            return None


async def _run_capture(opener: str, options: ClaudeAgentOptions) -> str | None:
    result = None
    try:
        async for message in query(prompt=opener, options=options):
            if isinstance(message, ResultMessage):
                result = getattr(message, "result", None)
    except Exception as e:
        return f"[skeptic errored: {e}]"
    return result


async def run_vote(name: str, n: int = 3) -> dict:
    lane = VOTE_LANES[name]
    lenses = lane["lenses"]

    async def one(idx: int) -> dict:
        lens = lenses[idx % len(lenses)]
        opener = (f"{lane['opener']}\n\nApply this lens specifically: {lens}.\n"
                  + _VERDICT_INSTRUCTION.format(block=lane["block"]))
        options = _make_options(allowed_tools=["Read", "Grep", "Glob"], model=lane["model"],
                                effort=lane["effort"], system_append=_always_on_context(lane["lane_note"]),
                                max_turns=40)
        text = await _run_capture(opener, options)
        return {"idx": idx, "lens": lens, "verdict": parse_verdict(text), "raw": text}

    raw = await asyncio.gather(*[one(i) for i in range(n)], return_exceptions=True)
    errors = [r for r in raw if isinstance(r, Exception)]
    runs = [r for r in raw if isinstance(r, dict)]
    parsed = [r for r in runs if r.get("verdict")]
    holds = [r for r in parsed if r["verdict"].get("holds_up") is True]
    refute = [r for r in parsed if r["verdict"].get("holds_up") is False]
    unparsed = [r for r in runs if not r.get("verdict")]

    if errors:
        print(f"[!] {len(errors)}/{n} skeptics ERRORED — first: {type(errors[0]).__name__}: {errors[0]}")
    if not runs:
        decision = "ALL SKEPTICS ERRORED — fix the error above (usually the model id or an SDK option)"
    elif len(refute) > len(holds):
        decision = "REFUTED — majority found blocking defects"
    elif len(holds) > len(refute):
        decision = "HOLDS UP — majority"
    else:
        decision = "TIE / inconclusive — escalate to a human or raise n"

    print(f"\n=== VOTE {name}  (n={n}) ===")
    print(f"decision: {decision}   [holds={len(holds)} refute={len(refute)} unparsed={len(unparsed)} errored={len(errors)}]")
    for r in parsed:
        v = r["verdict"]
        print(f"  [{r['lens']}] holds_up={v.get('holds_up')} conf={v.get('confidence')} :: {v.get('top_defect')}")

    payload = {"lane": name, "decision": decision, "holds": len(holds), "refute": len(refute),
               "unparsed": len(unparsed), "errored": len(errors),
               "verdicts": [{"lens": r["lens"], "verdict": r["verdict"]} for r in runs]}
    VOTE_DIR.mkdir(parents=True, exist_ok=True)
    (VOTE_DIR / f"{name}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"  -> persisted to {VOTE_DIR / (name + '.json')}")
    return payload


# ============================ POST-VOTE: apply <item> ============================================
# Reads the persisted verdict and does what it warrants. Write-capable; higher turn budget; fails soft.
APPLY_ITEMS = {
    "preseed":    dict(vote="B-review-preseed",
                       targets="runner/dag_scheduler.py preseed-suppression + its regression test"),
    "schemaid":   dict(vote="B-review-schemaid",
                       targets="runner/gate_evaluator.py emit, tools/backfill_gate_result_schema_id.py, "
                               "gate_pass_predicates._MANDATORY_FIELDS + tests"),
    "checkpoint": dict(vote="B-checkpoint-decision",
                       targets="the phase8_checkpoint schema (add a bootstrapped_gates provenance field) "
                               "+ the checkpoint-publish skill"),
}


async def run_apply(item: str) -> str | None:
    spec = APPLY_ITEMS[item]
    vote_file = VOTE_DIR / f"{spec['vote']}.json"
    if not vote_file.exists():
        print(f"[!] No persisted verdict at {vote_file}. Run:  python lane_launcher.py vote {spec['vote']} 3")
        return None
    verdicts = vote_file.read_text(encoding="utf-8")
    opener = (
        f"Post-vote work for '{item}'. Targets: {spec['targets']}.\n"
        f"The adversarial vote verdicts are below — TREAT THEM AS HYPOTHESES: first confirm each cited "
        f"line against the real file, then act.\n\n{verdicts}\n\n"
        "If the decision was HOLDS UP: write the regression seam the brief specifies. "
        "If REFUTED: apply the specific fix each top_defect prescribes, then add the regression test that "
        "would catch it. Keep edits minimal and constitutional (§17). Do NOT commit; leave changes for review."
    )
    options = _make_options(
        allowed_tools=["Read", "Grep", "Glob", "Write", "Edit", "Bash"],
        model=OPUS_MODEL, effort="high",
        system_append=_always_on_context(f"Apply lane for '{item}'. Verify findings, then fix. No commit."),
        max_turns=80,
    )
    return await _drive(opener, options, f"apply {item}")


async def run_seams(item: str | None = None) -> None:
    """Verdict-gated seam writer (the restored B-write-seams). Writes the regression seam ONLY for
    items whose latest vote HELD UP; never touches logic; safe-skips refuted/absent verdicts."""
    for it in ([item] if item else list(APPLY_ITEMS)):
        spec = APPLY_ITEMS[it]
        vf = VOTE_DIR / f"{spec['vote']}.json"
        if not vf.exists():
            print(f"[skip] {it}: no verdict at {vf} — run `python lane_launcher.py vote {spec['vote']} 3` first.")
            continue
        data = json.loads(vf.read_text(encoding="utf-8"))
        if not str(data.get("decision", "")).startswith("HOLDS UP"):
            print(f"[skip] {it}: latest verdict is '{data.get('decision')}' — run `apply {it}` first, then re-vote.")
            continue
        opener = (
            f"Item '{it}' HELD UP under adversarial review (verdict below). Write ONLY the regression seam "
            f"the brief specifies for {spec['targets']} — the test that would catch the original defect if it "
            f"regressed. Do NOT change production logic. Do NOT commit.\n\n{vf.read_text(encoding='utf-8')}"
        )
        options = _make_options(
            allowed_tools=["Read", "Grep", "Glob", "Write", "Edit", "Bash"],
            model=OPUS_MODEL, effort="high",
            system_append=_always_on_context(f"Seam-lock lane for '{it}'. Test only; no logic change; no commit."),
            max_turns=50,
        )
        await _drive(opener, options, f"seams {it}")


# ============================ CLI ================================================================
def _usage() -> None:
    print("Usage:")
    print("  python lane_launcher.py <lane>            lanes: " + ", ".join(LANES))
    print("  python lane_launcher.py vote <lane> [n]   vote lanes: " + ", ".join(VOTE_LANES) + "  (n default 3)")
    print("  python lane_launcher.py apply <item>      items: " + ", ".join(APPLY_ITEMS) + "  (reads the persisted verdict)")
    print("  python lane_launcher.py seams [item]      write the seam for items that HELD UP (verdict-gated)")


def main() -> None:
    args = sys.argv[1:]
    if args[:1] == ["vote"] and len(args) >= 2 and args[1] in VOTE_LANES:
        asyncio.run(run_vote(args[1], int(args[2]) if len(args) >= 3 else 3))
        return
    if args[:1] == ["apply"] and len(args) == 2 and args[1] in APPLY_ITEMS:
        asyncio.run(run_apply(args[1]))
        return
    if args[:1] == ["seams"]:
        it = args[1] if len(args) >= 2 else None
        if it is not None and it not in APPLY_ITEMS:
            _usage()
            raise SystemExit(2)
        asyncio.run(run_seams(it))
        return
    if len(args) == 1 and args[0] in LANES:
        if args[0] == "A-transport":
            print("NOTE: Lane A must run on the machine with the local `claude` CLI; untestable in a cloud sandbox.")
        asyncio.run(run_lane(args[0]))
        return
    _usage()
    raise SystemExit(2)


if __name__ == "__main__":
    main()
