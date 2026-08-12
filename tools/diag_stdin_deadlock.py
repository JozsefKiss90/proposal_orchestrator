"""Replicate the runner's EXACT claude invocation and stream output live.

Trials A/B/C established:
  * piped stdout is fine (trial C: 35,721 chars in, 7,737 out, 19.9 s)
  * every invocation costs ~20-30 s of MCP startup, so trial A's 30 s
    timeout was jitter, not a distinct failure
The untested delta is what skill_runtime.py:1403 actually passes:
    --system-prompt <1155 chars>   and   --tools Read,Glob

This script sends exactly that, prints every line as it arrives with an
elapsed stamp, and kills at 90 s.  Where the stream stops is the answer.
"""
from __future__ import annotations

import subprocess, sys, threading, time

MODEL = "claude-sonnet-4-6"
SYSTEM_PROMPT = ("You are a JSON extractor for a proposal orchestrator. "
                 "Read the declared input files and return only JSON. ") * 12  # ~1150 chars
USER_PROMPT = ("Task: list the files you can see, then reply with the single "
               "word DONE.\n" + "context padding line\n" * 1200)              # ~35 KB
TIMEOUT = 90

CMD = ["claude", "-p", "--model", MODEL,
       "--output-format", "stream-json", "--verbose",
       "--tools", "Read,Glob",
       "--system-prompt", SYSTEM_PROMPT]


def pump(stream, tag, t0):
    for line in iter(stream.readline, ""):
        line = line.rstrip()
        if not line:
            continue
        print(f"[{time.monotonic()-t0:6.1f}s {tag}] {line[:220]}", flush=True)
    stream.close()


def main() -> int:
    print(f"python {sys.version.split()[0]} on {sys.platform}")
    print(f"sys={len(SYSTEM_PROMPT)} user={len(USER_PROMPT)} tools=Read,Glob timeout={TIMEOUT}s")
    print("Watch where the stream stops.\n", flush=True)

    t0 = time.monotonic()
    p = subprocess.Popen(CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, encoding="utf-8")
    threading.Thread(target=pump, args=(p.stdout, "out", t0), daemon=True).start()
    threading.Thread(target=pump, args=(p.stderr, "ERR", t0), daemon=True).start()

    try:
        p.stdin.write(USER_PROMPT); p.stdin.close()
        print(f"[{time.monotonic()-t0:6.1f}s ---] stdin written and closed", flush=True)
    except Exception as exc:
        print(f"stdin write FAILED: {exc!r}", flush=True)

    try:
        rc = p.wait(timeout=TIMEOUT)
        print(f"\n[{time.monotonic()-t0:6.1f}s ---] exited rc={rc}", flush=True)
    except subprocess.TimeoutExpired:
        print(f"\n[{time.monotonic()-t0:6.1f}s ---] STILL RUNNING at {TIMEOUT}s -- killing", flush=True)
        p.kill()
    print("\nIf the last line is an init/system event, the CLI never began work.")
    print("If it is an assistant turn or a tool_use, it stalled mid-task --")
    print("almost certainly a permission prompt on a stdin that is already closed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
