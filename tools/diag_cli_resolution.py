"""Pin down which ``claude`` CLI this machine actually runs (TR-3).

The runner spawns ``claude`` through ``subprocess`` with ``shell=False``.  That
resolution is **not** the one your shell performs: PowerShell prefers a
``.ps1`` shim, ``CreateProcess`` walks ``PATH`` x ``PATHEXT`` and takes the
first *image* it finds.  On the reference machine the two disagreed —
Python got 2.1.81, the prompt got 2.1.224 — so the runner silently exercised a
different build, with a different MCP surface and a ~3-5x different
per-invocation cost, than the one being tested by hand.

This script answers four questions, in order:

1. **What is installed?**  Every ``claude*`` file in every ``PATH`` directory,
   plus the well-known install locations npm and the native installer use.
2. **What does each one report?**  ``<candidate> --version``, spawned exactly
   the way the transport spawns it (``shell=False``, detached console) — so a
   candidate that cannot be launched that way *fails here*, visibly, instead
   of at 3 a.m. inside a run.
3. **What would each layer pick?**  ``shutil.which`` (what the transport does
   unpinned), and ``Get-Command claude`` (what your prompt does).
4. **What should the pin be?**  A ready-to-paste ``.env`` line.

Usage::

    python tools/diag_cli_resolution.py            # human-readable report
    python tools/diag_cli_resolution.py --json     # machine-readable dump
    python tools/diag_cli_resolution.py --no-probe # skip --version spawns

Read-only: it launches ``--version`` and nothing else, starts no session, and
writes no files.

Companion to ``runner.claude_transport.resolve_claude_cli`` — the pin this
script recommends is the value that function consumes.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from typing import Any

#: Matches runner/claude_transport.py.
CLI_PATH_ENV_VAR = "ORCHESTRATOR_CLAUDE_CLI_PATH"
CLI_COMMAND_NAME = "claude"

IS_WINDOWS = os.name == "nt"

#: Seconds to wait for ``<candidate> --version``.  Generous: a cold CLI on
#: Windows can spend 20-30 s connecting MCP servers before printing anything,
#: and that latency is itself a finding worth measuring.
PROBE_TIMEOUT_SECONDS = 90

#: Extra directories worth checking even when they are not on PATH — a build
#: that is installed but unreachable explains a version you *thought* you had.
def _extra_search_dirs() -> list[str]:
    home = os.path.expanduser("~")
    dirs = [
        os.path.join(home, ".local", "bin"),          # native installer
        os.path.join(home, ".claude", "local"),       # legacy local install
        os.path.join(home, "bin"),
    ]
    if IS_WINDOWS:
        appdata = os.environ.get("APPDATA")
        if appdata:
            dirs.append(os.path.join(appdata, "npm"))  # npm -g shims
        localappdata = os.environ.get("LOCALAPPDATA")
        if localappdata:
            dirs.append(os.path.join(localappdata, "Programs", "claude"))
    else:
        dirs.extend(["/usr/local/bin", "/usr/bin", "/opt/homebrew/bin"])
    return dirs


def _popen_kwargs() -> dict:
    """Spawn kwargs identical to the transport's (detached console on Windows).

    Probing through a *different* spawn path than production would let a
    candidate pass here and fail in the runner, which is the whole point of
    this script.
    """
    if IS_WINDOWS:
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    return {"start_new_session": True}


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def _path_dirs() -> list[str]:
    raw = os.environ.get("PATH", "")
    seen: set[str] = set()
    out: list[str] = []
    for part in raw.split(os.pathsep):
        part = part.strip().strip('"')
        if not part:
            continue
        key = os.path.normcase(os.path.abspath(part))
        if key in seen:
            continue
        seen.add(key)
        out.append(part)
    return out


def discover_candidates() -> list[dict[str, Any]]:
    """Every file whose name starts with ``claude``, in PATH + known dirs.

    Ordered as the OS would search: PATH directories first, in PATH order,
    then the extra locations.  ``on_path`` records which group a hit came
    from — an install that is present but *not* on PATH cannot be what your
    shell runs, however plausible its version number looks.
    """
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    groups = [(d, True) for d in _path_dirs()]
    groups += [(d, False) for d in _extra_search_dirs()]

    for directory, on_path in groups:
        try:
            entries = sorted(os.listdir(directory))
        except OSError:
            continue
        for name in entries:
            if not name.lower().startswith(CLI_COMMAND_NAME):
                continue
            full = os.path.join(directory, name)
            if not os.path.isfile(full):
                continue
            key = os.path.normcase(os.path.abspath(full))
            if key in seen:
                continue
            seen.add(key)
            try:
                stat = os.stat(full)
                size, mtime = stat.st_size, stat.st_mtime
            except OSError:
                size, mtime = None, None
            candidates.append(
                {
                    "path": os.path.abspath(full),
                    "dir": directory,
                    "on_path": on_path,
                    "suffix": os.path.splitext(name)[1].lower(),
                    "size": size,
                    "mtime": (
                        time.strftime("%Y-%m-%d %H:%M", time.localtime(mtime))
                        if mtime
                        else None
                    ),
                }
            )
    return candidates


def find_node_entrypoints() -> list[str]:
    """Locate ``@anthropic-ai/claude-code/cli.js`` installs.

    The npm shims (``claude.cmd`` / ``claude.ps1``) are thin wrappers around
    this file.  ``node <cli.js>`` is the escape hatch when no directly
    spawnable image exists for the build you want to pin.
    """
    found: list[str] = []
    roots: list[str] = []
    for base in _extra_search_dirs() + _path_dirs():
        roots.append(os.path.join(base, "node_modules"))
        roots.append(os.path.join(os.path.dirname(base), "node_modules"))
    try:
        prefix = subprocess.run(
            ["npm", "prefix", "-g"],
            capture_output=True,
            text=True,
            timeout=30,
            shell=IS_WINDOWS,  # npm is itself a .cmd shim on Windows
        )
        if prefix.returncode == 0 and prefix.stdout.strip():
            roots.append(os.path.join(prefix.stdout.strip(), "node_modules"))
            roots.append(
                os.path.join(prefix.stdout.strip(), "lib", "node_modules")
            )
    except Exception:
        pass

    seen: set[str] = set()
    for root in roots:
        cli = os.path.join(root, "@anthropic-ai", "claude-code", "cli.js")
        key = os.path.normcase(os.path.abspath(cli))
        if key in seen:
            continue
        seen.add(key)
        if os.path.isfile(cli):
            found.append(os.path.abspath(cli))
    return found


# ---------------------------------------------------------------------------
# Probing
# ---------------------------------------------------------------------------


def probe_version(command: list[str]) -> dict[str, Any]:
    """Run ``<command> --version`` the way the transport spawns processes.

    Returns a record with the reported version, elapsed seconds, and — when
    the spawn itself fails — the OS error.  A ``.ps1`` shim is expected to
    fail here with WinError 193: that is the finding, not a bug in the probe.
    """
    t0 = time.monotonic()
    record: dict[str, Any] = {"command": command}
    try:
        proc = subprocess.run(
            command + ["--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=PROBE_TIMEOUT_SECONDS,
            shell=False,
            **_popen_kwargs(),
        )
    except subprocess.TimeoutExpired:
        record.update(
            spawnable=True,
            version=None,
            error=f"timed out after {PROBE_TIMEOUT_SECONDS}s",
        )
    except OSError as exc:
        record.update(
            spawnable=False,
            version=None,
            error=f"{type(exc).__name__}: {exc}",
        )
    except Exception as exc:  # pragma: no cover - defensive
        record.update(
            spawnable=False, version=None, error=f"{type(exc).__name__}: {exc}"
        )
    else:
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        record.update(
            spawnable=True,
            returncode=proc.returncode,
            version=out.splitlines()[0] if out else None,
            error=None if proc.returncode == 0 else (err[:300] or None),
        )
    record["elapsed_seconds"] = round(time.monotonic() - t0, 2)
    return record


def powershell_resolution() -> dict[str, Any] | None:
    """What the operator's own prompt resolves — the other half of the split.

    Windows only.  Uses ``-NoProfile`` so the answer reflects PATH, not a
    profile alias; if your profile *does* alias ``claude``, that is worth
    knowing separately.
    """
    if not IS_WINDOWS:
        return None
    script = (
        "$c = Get-Command claude -ErrorAction SilentlyContinue; "
        "if ($c) { $c.Source } else { '<not found>' }"
    )
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            timeout=60,
            shell=False,
        )
    except Exception as exc:
        return {"source": None, "error": f"{type(exc).__name__}: {exc}"}
    return {"source": (proc.stdout or "").strip() or None, "error": None}


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def _recommend(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the best pin: spawnable, on PATH, highest reported version.

    Deliberately conservative — it only ever recommends a candidate that
    *actually answered* ``--version`` through the production spawn path.
    """
    usable = [
        r
        for r in results
        if r.get("probe", {}).get("spawnable")
        and r.get("probe", {}).get("version")
    ]
    if not usable:
        return None

    def sort_key(r: dict[str, Any]) -> tuple:
        version = r["probe"]["version"] or ""
        digits = [int(p) for p in "".join(
            c if c.isdigit() else " " for c in version
        ).split()[:3]]
        digits += [0] * (3 - len(digits))
        return (1 if r["on_path"] else 0, tuple(digits))

    return sorted(usable, key=sort_key)[-1]


def render(report: dict[str, Any]) -> str:
    lines: list[str] = []
    add = lines.append

    add("=" * 78)
    add("claude CLI resolution — " + report["platform"])
    add("=" * 78)
    add(f"python           : {report['python']}")
    add(f"{CLI_PATH_ENV_VAR:<17}: {report['pin'] or '<unset>'}")
    add(f"shutil.which     : {report['which'] or '<not found>'}")
    if report.get("powershell"):
        add(f"Get-Command claude: {report['powershell'].get('source') or '<error>'}")
    if IS_WINDOWS:
        add(f"PATHEXT          : {os.environ.get('PATHEXT', '<unset>')}")
    add("")

    add("-" * 78)
    add("Candidates (PATH order first, then known install locations)")
    add("-" * 78)
    if not report["candidates"]:
        add("  none found")
    for r in report["candidates"]:
        probe = r.get("probe")
        flag = "PATH" if r["on_path"] else "off-PATH"
        add(f"  {r['path']}")
        detail = f"    [{flag}]  {r['mtime'] or '?'}  {r['size'] or '?'} bytes"
        add(detail)
        if probe is None:
            add("    version: <not probed>")
        elif probe.get("version"):
            add(
                f"    version: {probe['version']}"
                f"   ({probe['elapsed_seconds']}s to answer)"
            )
        else:
            add(f"    version: FAILED — {probe.get('error')}")
            if not probe.get("spawnable"):
                add("             (cannot be spawned with shell=False — "
                    "unusable as a pin)")
        add("")

    if report["node_entrypoints"]:
        add("-" * 78)
        add("Node entry points (pin via a wrapper if no image is spawnable)")
        add("-" * 78)
        for p in report["node_entrypoints"]:
            add(f"  {p}")
        add("")

    add("-" * 78)
    add("Recommendation")
    add("-" * 78)
    rec = report.get("recommended")
    if not report.get("probed"):
        add("  Skipped: --no-probe. A pin is only recommended for a candidate")
        add("  that answered --version through the production spawn path.")
    elif rec is None:
        add("  No candidate answered --version through the production spawn")
        add("  path.  Nothing can be pinned safely until that is fixed.")
    else:
        add(f"  Pin        : {rec['path']}")
        add(f"  Version    : {rec['probe']['version']}")
        add(f"  Startup    : {rec['probe']['elapsed_seconds']}s to --version")
        add("")
        add("  Add to .env (git-ignored, machine-specific):")
        add("")
        add(f"      {CLI_PATH_ENV_VAR}={rec['path']}")
        add("")
        versions = {
            r["probe"]["version"]
            for r in report["candidates"]
            if r.get("probe", {}).get("version")
        }
        if len(versions) > 1:
            add(f"  NOTE: {len(versions)} distinct versions are installed "
                f"({', '.join(sorted(versions))}).")
            add("  Pinning is what makes the choice between them deliberate.")
    add("=" * 78)
    return "\n".join(lines)


def _load_dotenv_best_effort() -> None:
    """Mirror ``runner/__main__.py``: the pin normally lives in ``.env``.

    Without this the report would say ``<unset>`` for a pin the runner does in
    fact honour — the exact kind of mismatch this script exists to expose.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def build_report(*, probe: bool = True) -> dict[str, Any]:
    _load_dotenv_best_effort()
    candidates = discover_candidates()
    if probe:
        for candidate in candidates:
            candidate["probe"] = probe_version([candidate["path"]])
    report: dict[str, Any] = {
        "platform": f"{sys.platform} ({os.name})",
        "python": sys.version.split()[0],
        "pin": os.environ.get(CLI_PATH_ENV_VAR),
        "which": shutil.which(CLI_COMMAND_NAME),
        "powershell": powershell_resolution(),
        "candidates": candidates,
        "node_entrypoints": find_node_entrypoints(),
        "probed": probe,
    }
    report["recommended"] = _recommend(candidates) if probe else None
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--json", action="store_true", help="emit the raw report as JSON"
    )
    parser.add_argument(
        "--no-probe",
        action="store_true",
        help="skip the --version spawns (discovery only, instant)",
    )
    args = parser.parse_args(argv)

    report = build_report(probe=not args.no_probe)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
