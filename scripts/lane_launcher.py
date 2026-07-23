"""
lane_launcher.py — operator harness for the Phase-8 debug/calibration lanes.
 
Purpose: make session startup DETERMINISTIC instead of "paste the brief and hope". Uses the Claude
Agent SDK to (1) always load brief + handoff + CONTEXT.md into context, (2) expose .claude/skills/
(incl. diagnosing-bugs), (3) launch one lane at a time with lane-appropriate tools, and (4) run the
two Lane-B judgment items as a deterministic N-skeptic majority vote orchestrated in Python.
 
Operator tool — deliberately SEPARATE from the constitutionally-governed runtime (runner/, §17).
Do not wire it into the DAG scheduler.
 
--------------------------------------------------------------------------------------------------
VERIFY BEFORE RUN — SDK option names/enums drift between versions. Pin the version, check the ref:
  https://code.claude.com/docs/en/agent-sdk/python  and  .../agent-sdk/skills
Re-confirm: `permission_mode` values, the `system_prompt` preset/append shape, the `skills=` form,
your model id, and — see the EFFORT note below — how reasoning effort is set in YOUR installed version.
Check your actual surface:
  python -c "from claude_agent_sdk import ClaudeAgentOptions; import inspect; print(inspect.signature(ClaudeAgentOptions))"
  claude --help    # exact CLI flags that extra_args forwards
--------------------------------------------------------------------------------------------------
 
WHAT THE SDK FIXES vs WHAT IT DOESN'T:
  * Context pickup      -> SOLVED via system_prompt append (always present).
  * Skill availability  -> SOLVED via setting_sources=["project"] + skills.
  * Firing a SPECIFIC skill -> NOT forceable (model-driven by description); biased via opener wording.
  * Reasoning effort    -> NOT a stable first-class field across claude-agent-sdk versions (see below).
"""
 
import asyncio
import inspect
import json
import re
import sys
from pathlib import Path
 
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage  # verify surface vs your version
 
REPO = Path(r"C:\Code\proposal_demo\proposal_orchestrator")
BRIEF = REPO / "plans" / "DEBUG_KICKOFF_phase8_calibration.md"
HANDOFF = REPO / "HANDOFF_phase8_m2t10_2026-07-22.md"
CONTEXT = REPO / "CONTEXT.md"
 
OPUS_MODEL = "<your-opus-4.8-model-id>"   # depth lever that IS stable across versions — prefer this
DEFAULT_MODEL = None                       # None -> inherit default
 
# ============================ REASONING EFFORT (honest state) =====================================
# Short answer to "can we set effort in the script?": yes, but NOT via a reliable first-class field.
# The claude-agent-sdk dataclass (per its source) exposes only an `extra_args` passthrough; some
# CHANGELOGs claim a first-class `thinking`/`effort` field, and there's an open feature request — the
# signals conflict, so we DETECT support at runtime and fall back to extra_args. On current models
# (Opus 4.8 / Fable 5) the underlying concept is adaptive thinking + effort; older models used a
# thinking token budget (deprecated). The dependable depth lever remains MODEL choice (Opus).
_OPT_PARAMS = set(inspect.signature(ClaudeAgentOptions).parameters)
 
 
def _effort_kwargs(effort: str | None) -> dict:
    """Map effort ('low'|'medium'|'high'|None) to kwargs, adapting to the installed SDK surface."""
    if not effort:
        return {}
    if "effort" in _OPT_PARAMS:                 # first-class, if your version added it
        return {"effort": effort}
    if "thinking" in _OPT_PARAMS:               # adaptive-thinking shape, if present
        return {"thinking": {"type": "adaptive"}}
    # Fallback: forward to the underlying CLI/API. CONFIRM the flag name via `claude --help`.
    return {"extra_args": {"output-config": json.dumps({"effort": effort})}}
 
 
def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else f"[missing: {p}]"
 
 
def _always_on_context(lane_note: str) -> str:
    """Everything a lane must ALWAYS see, injected into the system prompt (not left to a Read)."""
    return (
        f"You are running an operator debug/calibration lane on {REPO}.\n\n"
        f"=== LANE ===\n{lane_note}\n\n"
        f"=== CONTEXT.md (runtime module map) ===\n{_read(CONTEXT)}\n\n"
        f"=== DEBUG KICKOFF BRIEF ===\n{_read(BRIEF)}\n\n"
        f"=== HANDOFF (thread state) ===\n{_read(HANDOFF)}\n"
    )
 
 
def _make_options(*, allowed_tools, model, effort, lane_note) -> ClaudeAgentOptions:
    base = dict(
        cwd=str(REPO),
        setting_sources=["project"],            # loads CLAUDE.md + discovers .claude/skills/
        skills="all",                            # available; model still chooses when to fire
        allowed_tools=allowed_tools,
        model=model,
        system_prompt={"type": "preset", "preset": "claude_code",
                       "append": _always_on_context(lane_note)},
        max_turns=40,
    )
    return ClaudeAgentOptions(**base, **_effort_kwargs(effort))
 
 
# ============================ SINGLE-SESSION LANES ================================================
LANES = {
    "C-calibration": dict(
        model=DEFAULT_MODEL, effort="medium",
        allowed_tools=["Read", "Grep", "Glob", "Bash"],
        lane_note="Lane C. Measurement, NOT debugging — do not invoke diagnosing-bugs.",
        opener=(
            "Lane C only: run eval-harness E2 (status-aware faithfulness) + E3 (ledger completeness) "
            "offline on the current artifacts to quantify the coarse claim ledger (handoff §4.4). "
            "Report the numbers; make no code changes."
        ),
    ),
    # Run AFTER the B-review-* votes: write seams only for fixes the vote judged safe.
    "B-write-seams": dict(
        model=OPUS_MODEL, effort="high",
        allowed_tools=["Read", "Grep", "Glob", "Write", "Edit", "Bash"],
        lane_note="Lane B write-up. Only write seams for fixes the vote cleared. Do not commit.",
        opener=(
            "The adversarial review votes are done. For each fix the vote judged safe, write the missing "
            "regression seam from the brief: assert-AT-THE-WRITER that every emitted gate_result carries "
            "schema_id; and a scheduler-in-preseed-mode fixture asserting preseeded prose survives "
            "un-recomposed. Do not commit."
        ),
    ),
    "A-transport": dict(
        model=OPUS_MODEL, effort="high",
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
 
 
async def run_lane(name: str) -> str | None:
    lane = LANES[name]
    options = _make_options(allowed_tools=lane["allowed_tools"], model=lane["model"],
                            effort=lane["effort"], lane_note=lane["lane_note"])
    result = None
    async for message in query(prompt=lane["opener"], options=options):
        if isinstance(message, ResultMessage):
            result = getattr(message, "result", None)
        print(message)
    return result
 
 
# ============================ OPTION (b): DETERMINISTIC N-VOTE ====================================
# Read-only skeptics (safe to parallelize — no writers), each with a DISTINCT lens (perspective-
# diverse verify), each ending in a machine-parseable verdict. Python does the majority tally, so the
# result never depends on in-session subagent scheduling.
 
_VERDICT_INSTRUCTION = (
    "End with EXACTLY one line and nothing after it:\n"
    'VERDICT_JSON: {{"holds_up": true|false, "confidence": "low|medium|high", '
    '"top_defect": "<one line>", "lens": "<your lens>"}}\n'
    "holds_up=false means you found a real defect that should block {block}."
)
 
VOTE_LANES = {
    "B-checkpoint-decision": dict(
        model=OPUS_MODEL, effort="high",
        block="adopting option 1 as the checkpoint-publish contract",
        lane_note="Lane B decision. CONTRACT decision, not a bug. Do NOT build a repro loop. Reasoning only.",
        lenses=["provenance-integrity", "operational-what-breaks", "cost-vs-option-2-full-fresh-run"],
        opener=(
            "Lane B, checkpoint-publish run_id (§2). Adversarially REFUTE option 1 (accept bootstrapped "
            "gate results, validated against original_run_id). Treat option 3 (re-stamp) as provenance "
            "falsification. If option 1 survives, say what one-line contract to write into checkpoint-publish."
        ),
    ),
    "B-review-preseed": dict(
        model=OPUS_MODEL, effort="high",
        block="committing the preseed-suppression fix as-is",
        lane_note="Lane B review. Read-only; refute the fix. Do not modify files.",
        lenses=["correctness-and-missed-code-paths", "canonical_pack-vs-unapplied-assumptions", "brittle-name-suffix-match"],
        opener=(
            "Refute the preseed-suppression fix in runner/dag_scheduler.py (drops *_section_assembler + "
            "*_assumption_applier, keeps canonical_pack_deriver in preseed mode). Find a scenario where "
            "it is wrong or inconsistent; quote the code."
        ),
    ),
    "B-review-schemaid": dict(
        model=OPUS_MODEL, effort="high",
        block="committing the schema_id emit/backfill as-is",
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
    async for message in query(prompt=opener, options=options):
        if isinstance(message, ResultMessage):
            result = getattr(message, "result", None)
    return result
 
 
async def run_vote(name: str, n: int = 3) -> dict:
    lane = VOTE_LANES[name]
    lenses = lane["lenses"]
 
    async def one(idx: int) -> dict:
        lens = lenses[idx % len(lenses)]
        opener = (f"{lane['opener']}\n\nApply this lens specifically: {lens}.\n"
                  + _VERDICT_INSTRUCTION.format(block=lane["block"]))
        options = _make_options(
            allowed_tools=["Read", "Grep", "Glob"],       # read-only -> parallel-safe
            model=lane["model"], effort=lane["effort"], lane_note=lane["lane_note"],
        )
        text = await _run_capture(opener, options)
        return {"idx": idx, "lens": lens, "verdict": parse_verdict(text), "raw": text}
 
    runs = await asyncio.gather(*[one(i) for i in range(n)], return_exceptions=True)
    runs = [r for r in runs if isinstance(r, dict)]  # drop crashed skeptics
    parsed = [r for r in runs if r.get("verdict")]
    holds = [r for r in parsed if r["verdict"].get("holds_up") is True]
    refute = [r for r in parsed if r["verdict"].get("holds_up") is False]
    unparsed = [r for r in runs if not r.get("verdict")]
 
    if len(refute) > len(holds):
        decision = "REFUTED — majority found blocking defects"
    elif len(holds) > len(refute):
        decision = "HOLDS UP — majority"
    else:
        decision = "TIE / inconclusive — escalate to a human or raise n"
 
    print(f"\n=== VOTE {name}  (n={len(runs)}) ===")
    print(f"decision: {decision}   [holds={len(holds)} refute={len(refute)} unparsed={len(unparsed)}]")
    for r in parsed:
        v = r["verdict"]
        print(f"  [{r['lens']}] holds_up={v.get('holds_up')} conf={v.get('confidence')} :: {v.get('top_defect')}")
    return {"lane": name, "decision": decision, "holds": len(holds),
            "refute": len(refute), "unparsed": len(unparsed), "runs": runs}
 
 
# ============================ CLI ================================================================
def _usage() -> None:
    print("Usage:")
    print("  python lane_launcher.py <lane>            lanes: " + ", ".join(LANES))
    print("  python lane_launcher.py vote <lane> [n]   vote lanes: " + ", ".join(VOTE_LANES) + "  (n default 3)")
 
 
def main() -> None:
    args = sys.argv[1:]
    if args[:1] == ["vote"] and len(args) >= 2 and args[1] in VOTE_LANES:
        n = int(args[2]) if len(args) >= 3 else 3
        asyncio.run(run_vote(args[1], n))
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