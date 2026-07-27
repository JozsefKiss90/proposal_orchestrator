"""
Real-process tests for the transport's process-tree kill (TR-1).

Unlike ``test_claude_transport.py`` (which mocks the subprocess boundary),
these tests spawn a *real* parent -> grandchild process tree and prove that
:func:`runner.claude_transport._kill_process_tree` terminates the **whole**
tree, not just the direct child.

Why this is the right regression for TR-1
-----------------------------------------
The bug: ``subprocess.run(timeout=...)`` (and a naive ``proc.kill()``) only
terminate the *direct* child.  On Windows the ``claude`` CLI is a thin wrapper
that spawns a long-lived Node child; when the direct child is killed, that Node
grandchild is orphaned (reparented) and keeps running — the ~2h "stalled" hang.

These tests are **red-capable**: run them against the old direct-child-only
kill (``proc.kill()``) and the grandchild survives -> the orphaned-PID
assertion fails.  Against the tree-kill they pass.

The child tree is spawned with the *same* platform-specific Popen kwargs the
transport uses (:func:`_tree_killable_popen_kwargs`), so on POSIX the child
leads its own session/process-group and ``killpg`` can never reach the test
runner.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from runner.claude_transport import (
    _kill_process_tree,
    _tree_killable_popen_kwargs,
)


# ---------------------------------------------------------------------------
# Cross-platform process-liveness helpers
# ---------------------------------------------------------------------------


def _pid_alive(pid: int) -> bool:
    """Return True if a process with *pid* currently exists.

    Windows uses a ctypes ``OpenProcess`` probe (fast, no subprocess) rather
    than polling ``tasklist`` — the latter costs ~1s/call and made this test
    a multi-second drag.
    """
    if os.name == "nt":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if not handle:
            return False  # no such PID (our own children, so not access-denied)
        try:
            exit_code = ctypes.c_ulong()
            if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                # Our sleepers are force-killed (exit 1), never 259, so
                # STILL_ACTIVE is an unambiguous "running" signal here.
                return exit_code.value == STILL_ACTIVE
            return False
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Exists but owned by another user — still "alive".
        return True
    return True


def _wait_until_dead(pid: int, timeout: float = 15.0) -> bool:
    """Poll until *pid* is gone; return True if it died within *timeout*."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return True
        time.sleep(0.1)
    return not _pid_alive(pid)


def _wait_for_file(path: Path, timeout: float = 15.0) -> str:
    """Poll until *path* has non-empty content and return it."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            text = path.read_text(encoding="utf-8").strip()
        except (FileNotFoundError, OSError):
            text = ""
        if text:
            return text
        time.sleep(0.05)
    raise AssertionError(f"timed out waiting for {path} to be written")


def _force_cleanup(*pids: int) -> None:
    """Best-effort teardown so a failed assertion never leaks a sleeper."""
    for pid in pids:
        if pid <= 0:
            continue
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    timeout=10,
                )
            else:
                os.kill(pid, 9)
        except Exception:
            pass


# A parent that spawns a grandchild, records the grandchild PID to a file,
# then blocks.  Both sleepers are long-lived so they cannot self-exit during
# the test window.
_PARENT_TEMPLATE = (
    "import subprocess, sys, time\n"
    "gc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
    "open(r'{pid_file}', 'w').write(str(gc.pid))\n"
    "time.sleep(120)\n"
)


def _spawn_tree(pid_file: Path) -> tuple[subprocess.Popen, int]:
    """Spawn parent -> grandchild; return (parent_proc, grandchild_pid)."""
    parent_code = _PARENT_TEMPLATE.format(pid_file=str(pid_file))
    proc = subprocess.Popen(
        [sys.executable, "-c", parent_code],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **_tree_killable_popen_kwargs(),
    )
    grandchild_pid = int(_wait_for_file(pid_file))
    return proc, grandchild_pid


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestKillProcessTree:
    def test_kills_direct_child_and_grandchild(self, tmp_path: Path) -> None:
        """The whole tree dies — the orphaned-PID assertion the bug fails."""
        pid_file = tmp_path / "grandchild.pid"
        proc, grandchild_pid = _spawn_tree(pid_file)
        parent_pid = proc.pid
        try:
            # Sanity: the tree is genuinely up before we kill it.
            assert _pid_alive(parent_pid)
            assert _pid_alive(grandchild_pid)

            _kill_process_tree(proc)
            # Reap the direct child / drain pipes, mirroring the transport.
            try:
                proc.communicate(timeout=10)
            except Exception:
                pass

            assert _wait_until_dead(parent_pid), "direct child survived the kill"
            assert _wait_until_dead(grandchild_pid), (
                "grandchild orphaned — tree kill did not reach the descendant"
            )
        finally:
            _force_cleanup(grandchild_pid, parent_pid)

    def test_already_exited_process_is_noop(self, tmp_path: Path) -> None:
        """Killing an already-dead process must not raise."""
        proc = subprocess.Popen(
            [sys.executable, "-c", "pass"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            **_tree_killable_popen_kwargs(),
        )
        proc.communicate(timeout=10)
        assert proc.poll() is not None
        # Must be a safe no-op, never an exception.
        _kill_process_tree(proc)


class TestTreeKillablePopenKwargs:
    def test_posix_starts_new_session(self) -> None:
        kwargs = _tree_killable_popen_kwargs()
        if os.name == "nt":
            # No POSIX-only kwargs leak onto Windows.
            assert "start_new_session" not in kwargs
        else:
            assert kwargs.get("start_new_session") is True
