"""Demonstrate the frozen-console hang mechanism (TR-2 root cause).

A QuickEdit text selection (or Ctrl+S) freezes a console window's host
process. A child process that attaches to a frozen console blocks before
``main()``. It never reads stdin, so a parent writing a large prompt into
the pipe blocks forever — and ``communicate(input=...)`` writes stdin
synchronously before any deadline check, so its timeout never fires.

This script proves the mechanism on the local machine:

1. Spawn a helper in a new console window.
2. Suspend that console's host process (``NtSuspendProcess``) — the same
   freeze a QuickEdit selection causes.
3. The helper spawns a piped child and reports whether stdin drains.
4. Resume the console host and observe recovery.

Run modes::

    python tools/diag_console_freeze.py             # child shares console: BLOCKS while frozen
    python tools/diag_console_freeze.py --detached  # child CREATE_NO_WINDOW: immune

Observed 2026-08-13: shared-console child blocked 24.9 s (the full freeze),
then drained instantly on resume. Detached child drained in 0.11 s while
frozen. The transport fix (``runner/claude_transport.py``) applies both
guards: stdin is written from a daemon thread (deadline unconditional) and
the child is spawned with ``CREATE_NO_WINDOW`` (trigger removed).
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import tempfile
import time

WORK = os.path.join(tempfile.gettempdir(), "diag_console_freeze")
STATUS = os.path.join(WORK, "status.log")
FLAG = os.path.join(WORK, "frozen.flag")
DRAIN = os.path.join(WORK, "drain_done.txt")
PAYLOAD_LEN = 35714

PROCESS_SUSPEND_RESUME = 0x0800


def _log(msg: str) -> None:
    with open(STATUS, "a", encoding="utf-8") as f:
        f.write(f"{time.time():.3f} {msg}\n")


def host_main() -> int:
    """Runs inside the fresh console. Writes only to files after the freeze."""
    _log("host_up")
    print("diag host up; waiting for frozen.flag", flush=True)
    t0 = time.monotonic()
    while not os.path.exists(FLAG):
        if time.monotonic() - t0 > 60:
            _log("flag_timeout")
            return 1
        time.sleep(0.2)

    flags = subprocess.CREATE_NO_WINDOW if "--detached" in sys.argv else 0
    _log(f"flag_seen; spawning child creationflags={flags:#x}")
    child_code = (
        "import sys;"
        "d = sys.stdin.read();"
        f"open(r'{DRAIN}','w').write(str(len(d)))"
    )
    t1 = time.monotonic()
    p = subprocess.Popen([sys.executable, "-c", child_code],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True,
                         creationflags=flags)
    _log(f"popen_returned dt={time.monotonic()-t1:.2f}s pid={p.pid}")

    t2 = time.monotonic()
    try:
        p.stdin.write("x" * PAYLOAD_LEN)
        p.stdin.close()
        _log(f"stdin_write_done dt={time.monotonic()-t2:.2f}s")
    except Exception as exc:  # noqa: BLE001 — diagnostic record
        _log(f"stdin_write_failed {exc!r}")
    try:
        rc = p.wait(timeout=30)
        _log(f"child_exit rc={rc} dt={time.monotonic()-t2:.2f}s")
    except subprocess.TimeoutExpired:
        _log("child_wait_timeout_30s")
        p.kill()
    return 0


def _console_host_pids() -> set[int]:
    pids: set[int] = set()
    for image in ("conhost.exe", "OpenConsole.exe"):
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True).stdout
        for line in out.splitlines():
            parts = line.split('","')
            if len(parts) > 1:
                try:
                    pids.add(int(parts[1].strip('"')))
                except ValueError:
                    pass
    return pids


def _show_status(label: str) -> None:
    print(f"--- status ({label}) ---")
    if os.path.exists(STATUS):
        print(open(STATUS, encoding="utf-8").read().rstrip())
    drained = os.path.exists(DRAIN)
    print(f"drain_done exists: {drained}"
          + (f" content={open(DRAIN).read()}" if drained else ""))


def orchestrator_main() -> int:
    if os.name != "nt":
        print("Windows-only diagnostic.")
        return 1
    ntdll = ctypes.WinDLL("ntdll")
    kernel32 = ctypes.WinDLL("kernel32")

    os.makedirs(WORK, exist_ok=True)
    for p in (STATUS, FLAG, DRAIN):
        if os.path.exists(p):
            os.remove(p)

    detached = "--detached" in sys.argv
    before = _console_host_pids()
    host_args = [sys.executable, os.path.abspath(__file__), "--host"]
    if detached:
        host_args.append("--detached")
    host = subprocess.Popen(host_args,
                            creationflags=subprocess.CREATE_NEW_CONSOLE)
    print(f"host spawned pid={host.pid} (detached child: {detached})")

    time.sleep(3.0)
    new_hosts = _console_host_pids() - before
    print(f"new console host pid(s): {sorted(new_hosts)}")
    if not new_hosts:
        print("FAIL: no new console host found; aborting")
        host.kill()
        return 1

    handles = []
    for pid in new_hosts:
        h = kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, pid)
        if h:
            ntdll.NtSuspendProcess(h)
            print(f"suspended console host {pid}")
            handles.append((pid, h))

    open(FLAG, "w").write("1")
    time.sleep(25.0)
    _show_status("console FROZEN, t=25s")
    frozen_drained = os.path.exists(DRAIN)

    for pid, h in handles:
        ntdll.NtResumeProcess(h)
        kernel32.CloseHandle(h)
    print("console hosts resumed")

    time.sleep(8.0)
    _show_status("console RESUMED, +8s")

    print()
    if detached:
        print("PASS: detached child immune to the freeze."
              if frozen_drained else
              "UNEXPECTED: detached child was still blocked by the freeze.")
    else:
        if not frozen_drained and os.path.exists(DRAIN):
            print("MECHANISM CONFIRMED: frozen console blocked the piped "
                  "child (stdin never drained); resume unblocked it.")
        elif frozen_drained:
            print("MECHANISM NOT REPRODUCED: child drained stdin while "
                  "frozen.")
        else:
            print("INCONCLUSIVE: child still blocked after resume; inspect "
                  f"{STATUS}")

    try:
        host.wait(timeout=10)
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(host.pid)],
                       capture_output=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(host_main() if "--host" in sys.argv
                     else orchestrator_main())
