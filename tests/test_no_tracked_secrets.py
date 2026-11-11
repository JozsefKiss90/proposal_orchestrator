"""No credential is tracked in this repository (F3 recurrence guard).

The transport key that ``.env.harness`` carried from 2026-08-04 to 2026-11-04 was
public in git history and had to be revoked
(``docs/tier4_orchestration_state/decision_log/transport-key-revoked_2026-11-11.json``).
These checks fail the suite before that can happen again:

* no ``.env`` file is tracked (``.env.example``-style templates are allowed);
* no tracked file contains a provider API-key pattern.

A finding names the file, the line and the pattern, never the matching text, so
running the check does not copy a leaked value into a console or a log. The
patterns are assembled from fragments so this file never matches itself.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

_ALNUM = "[A-Za-z0-9]"
KEY_PATTERNS: dict[str, re.Pattern[str]] = {
    "groq": re.compile("gs" + "k_" + _ALNUM + "{20,}"),
    "anthropic": re.compile("sk" + "-ant-" + "[A-Za-z0-9_-]{20,}"),
    "openai": re.compile("s" + "k-(?:proj-)?" + _ALNUM + "{32,}"),
    "github": re.compile("gh" + "p_" + _ALNUM + "{30,}|github" + "_pat_" + "[A-Za-z0-9_]{30,}"),
    "slack": re.compile("xo" + "x[baprs]-" + "[A-Za-z0-9-]{10,}"),
    "google": re.compile("AI" + "za" + "[0-9A-Za-z_-]{35}"),
    "aws_secret": re.compile("aws_" + "secret_access_key" + r"\s*[=:]\s*['\"]?[A-Za-z0-9/+]{40}", re.I),
}


def _tracked_files() -> list[str]:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "-z"],
            capture_output=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout (e.g. the offline bundle): nothing is tracked here")
    return [p for p in out.decode("utf-8", "replace").split("\0") if p]


def _text(path: Path) -> str:
    data = path.read_bytes()
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", "replace")
    return data.decode("utf-8", "replace")


def test_no_env_file_is_tracked():
    tracked = [
        p for p in _tracked_files()
        if re.search(r"(^|/)\.env(\.[^/]+)?$", p) and not p.endswith(".example")
    ]
    assert not tracked, f"environment files must never be tracked: {tracked}"


def test_no_tracked_file_holds_a_provider_key():
    findings: list[str] = []
    for rel in _tracked_files():
        path = REPO / rel
        if not path.is_file():
            continue
        for lineno, line in enumerate(_text(path).splitlines(), 1):
            for name, pattern in KEY_PATTERNS.items():
                if pattern.search(line):
                    findings.append(f"{rel}:{lineno}: {name} key pattern")
    assert not findings, (
        "a credential is tracked; remove it, revoke it at the provider, and never "
        "print it:\n" + "\n".join(findings)
    )
