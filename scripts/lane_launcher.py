"""
lane_launcher.py — operator harness for the Phase-8 debug/calibration lanes.
 
Purpose: make session startup DETERMINISTIC instead of "paste the brief and hope". It uses the
Claude Agent SDK to (1) always load the brief + handoff + CONTEXT.md into context, (2) make the
project's `.claude/skills/` (incl. diagnosing-bugs) available, and (3) launch one lane at a time
with lane-appropriate tools and an opener whose wording fires the right skill.
 
This is an OPERATOR TOOL, deliberately separate from the constitutionally-governed production runtime
(runner/, §17). Do not wire it into the DAG scheduler — it exists to drive debugging sessions, not to
execute the workflow.
 
--------------------------------------------------------------------------------------------------
VERIFY BEFORE RUN — SDK option names/enums drift between versions. Pin the version and check the ref:
  https://code.claude.com/docs/en/agent-sdk/python   and   .../agent-sdk/skills
Specifically re-confirm: `permission_mode` allowed values, the `system_prompt` preset/append shape,
the `skills=` form ("all" vs list), and your exact model id. `pip install claude-agent-sdk` (pin it).
--------------------------------------------------------------------------------------------------
 
WHAT THE SDK FIXES vs WHAT IT DOESN'T (the honest part):
  * Context pickup  -> SOLVED. Injected via system_prompt append, so it is ALWAYS present (more
    reliable than letting the model choose to Read the files).
  * Skill availability -> SOLVED. setting_sources=["project"] + skills discovers .claude/skills/.
  * Firing a SPECIFIC skill -> NOT forceable. Invocation stays model-driven by the skill's
    description. You bias it by matching description keywords in the opener (done below) or by
    registering a slash command. There is no "invoke skill X now" API.
"""
 
import asyncio
import sys
from pathlib import Path
 
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage  # verify import surface vs your version
 
REPO = Path(r"C:\Code\proposal_demo\proposal_orchestrator")
BRIEF = REPO / "plans" / "DEBUG_KICKOFF_phase8_calibration.md"
HANDOFF = REPO / "HANDOFF_phase8_m2t10_2026-07-22.md"
CONTEXT = REPO / "CONTEXT.md"
 
# Set to your chosen ids. Opus for adversarial judgment lanes; a cheaper tier is fine for Lane C.
OPUS_MODEL = "<your-opus-4.8-model-id>"       # e.g. the Opus 4.8 id from your model list
DEFAULT_MODEL = None                           # None -> inherit the SDK/CLI default
 
 
def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8") if p.exists() else f"[missing: {p}]"
 
 
def _always_on_context(lane_note: str) -> str:
    """Everything the lane must ALWAYS see, injected into the system prompt (not left to a Read)."""
    return (
        f"You are running an operator debug/calibration lane on {REPO}.\n\n"
        f"=== LANE ===\n{lane_note}\n\n"
        f"=== CONTEXT.md (runtime module map) ===\n{_read(CONTEXT)}\n\n"
        f"=== DEBUG KICKOFF BRIEF ===\n{_read(BRIEF)}\n\n"
        f"=== HANDOFF (thread state) ===\n{_read(HANDOFF)}\n"
    )
 
 
# Each lane = opener (fires the right behavior) + tool posture + model. Openers mirror the brief's runbook.
LANES = {
    # Lane C — offline calibration. No debugging skill. Read-only + Bash to run the eval harness.
    "C-calibration": dict(
        model=DEFAULT_MODEL,
        allowed_tools=["Read", "Grep", "Glob", "Bash"],
        lane_note="Lane C. Measurement, NOT debugging — do not invoke diagnosing-bugs.",
        opener=(
            "Lane C only: run eval-harness E2 (status-aware faithfulness) + E3 (ledger completeness) "
            "offline on the current artifacts to quantify the coarse claim ledger (handoff §4.4). "
            "Report the numbers; make no code changes."
        ),
    ),
    # Lane B — contract decision. Reasoning only: deny writes so it cannot 'fix' anything.
    "B-checkpoint-decision": dict(
        model=OPUS_MODEL,
        allowed_tools=["Read", "Grep", "Glob"],  # read-only by omission of Write/Edit/Bash
        lane_note="Lane B decision. This is a CONTRACT decision, not a bug. Do NOT build a repro loop.",
        opener=(
            "Lane B, checkpoint-publish run_id (§2). Adversarially refute option 1 (accept bootstrapped "
            "gate results, validated against original_run_id) per the brief's prompt. Treat option 3 "
            "(re-stamp) as provenance falsification. Output the one-line contract to write into "
            "checkpoint-publish and name what to grep in its source first. Reasoning only — no edits."
        ),
    ),
    # Lane B — adversarial review of the two untested fixes, then write the missing seams.
    "B-untested-fixes": dict(
        model=OPUS_MODEL,
        allowed_tools=["Read", "Grep", "Glob", "Write", "Edit", "Bash"],  # may write the regression tests
        lane_note="Lane B fixes. Refute first; only then write the missing regression seam.",
        opener=(
            "Lane B: adversarially review the preseed-suppression (dag_scheduler.py) and schema_id "
            "(gate_evaluator.py) fixes per the brief. For each: decide holds_up with code-cited evidence, "
            "then write the missing regression seam the brief specifies. Do not commit."
        ),
    ),
    # Lane A — the one true diagnosing-bugs target. MUST run where the local `claude` CLI is.
    "A-transport": dict(
        model=OPUS_MODEL,
        allowed_tools=["Read", "Grep", "Glob", "Write", "Edit", "Bash"],
        lane_note="Lane A. Runs LOCALLY (needs the Windows `claude` CLI). Loop before hypothesis.",
        # 'diagnose'/'debug' wording is what makes the diagnosing-bugs skill fire (description match).
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
    options = ClaudeAgentOptions(
        cwd=str(REPO),
        setting_sources=["project"],          # loads CLAUDE.md + discovers .claude/skills/
        skills="all",                          # make diagnosing-bugs (etc.) available; model still chooses
        allowed_tools=lane["allowed_tools"],
        model=lane["model"],                   # None -> default
        # Inject all lane context so it is guaranteed present (verify preset/append shape vs your version):
        system_prompt={"type": "preset", "preset": "claude_code",
                       "append": _always_on_context(lane["lane_note"])},
        # permission_mode=...  # set per your version's allowed values if you want auto-accept edits
        max_turns=40,
    )
    result = None
    async for message in query(prompt=lane["opener"], options=options):
        if isinstance(message, ResultMessage):
            result = getattr(message, "result", None)
        print(message)
    return result
 
 
def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in LANES:
        print("Usage: python lane_launcher.py <lane>\n  lanes: " + ", ".join(LANES))
        raise SystemExit(2)
    name = sys.argv[1]
    if name == "A-transport":
        print("NOTE: Lane A must run on the machine with the local `claude` CLI; its loop is untestable in a cloud sandbox.")
    asyncio.run(run_lane(name))
 
 
if __name__ == "__main__":
    main()
 
 
# ---------------------------------------------------------------------------------------------------
# ON THE "ADVERSARIAL AGENTS" (Ultracode): the openers above run ONE session per lane. To get the
# multi-skeptic majority-vote for the two Lane-B items, either (a) let the session spawn subagents if
# your setup exposes a Task/subagent tool, or (b) do it deterministically in Python — call run_lane on
# a refute-only variant N times (or N parallel query() calls), then majority-vote the verdicts here.
# Option (b) is the version that fits your orchestrator mindset and removes model-scheduling variance.
# ---------------------------------------------------------------------------------------------------
 