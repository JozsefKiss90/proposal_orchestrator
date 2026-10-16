"""AN12 — the host runbook describes only what the code does.

Every ``python -m`` line of ``plans/msca_dn_an12_host_runbook.md`` for
the three AN12 commands is parsed by that command's own parser, every
required flag of each command appears in it, and every repository path it
cites exists. The V12 pattern: a runbook that drifts from its parser fails
here, not on the host.
"""

from __future__ import annotations

import argparse
import re
import shlex
from pathlib import Path

import pytest

from harness.commands import converse_smoke as cs
from runner import offline_bundle as ob
from tools import anonymisation_host_smoke as smoke

REPO = Path(__file__).resolve().parents[1]
RUNBOOK = REPO / "plans" / "msca_dn_an12_host_runbook.md"

PARSERS: dict[str, argparse.ArgumentParser] = {
    "runner.offline_bundle": ob._parser(),
    "tools.anonymisation_host_smoke": smoke._parser(),
    "harness.commands.converse_smoke": cs._parser(),
}


def _commands() -> list[tuple[str, list[str]]]:
    """Each documented invocation of an AN12 command, as (module, argv)."""
    text = RUNBOOK.read_text(encoding="utf-8")
    blocks = re.findall(r"```bash\n(.*?)```", text, re.S)
    found: list[tuple[str, list[str]]] = []
    for block in blocks:
        joined = re.sub(r"\\\n\s*", " ", block)
        for line in joined.splitlines():
            match = re.search(r"-m (\S+) (.*)$", line)
            if match and match[1] in PARSERS:
                argv = shlex.split(re.sub(r"<[^>]*>", "x", match[2]))
                found.append((match[1], argv))
    return found


COMMANDS = _commands()


def test_the_runbook_runs_every_command():
    assert {module for module, _argv in COMMANDS} == set(PARSERS)


@pytest.mark.parametrize("module, argv", COMMANDS, ids=[" ".join(a[:1]) for _m, a in COMMANDS])
def test_each_documented_line_parses(module, argv):
    PARSERS[module].parse_args(argv)


def _required(parser: argparse.ArgumentParser) -> dict[str, set[str]]:
    """Required option strings, per sub-command ('' when there is none)."""
    out: dict[str, set[str]] = {}
    subs = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    targets = subs[0].choices.items() if subs else [("", parser)]
    for name, sub in targets:
        out[name] = {a.option_strings[0] for a in sub._actions if a.required and a.option_strings}
    return out


@pytest.mark.parametrize("module", sorted(PARSERS))
def test_every_required_flag_is_documented(module):
    used: dict[str, set[str]] = {}
    for mod, argv in COMMANDS:
        if mod == module:
            sub = argv[0] if not argv[0].startswith("-") else ""
            used.setdefault(sub, set()).update(a for a in argv if a.startswith("--"))
    for sub, flags in _required(PARSERS[module]).items():
        if sub in used:
            assert flags <= used[sub], (module, sub, flags - used[sub])


def test_every_cited_repository_path_exists():
    text = RUNBOOK.read_text(encoding="utf-8")
    cited = set(re.findall(r"`((?:runner|tools|harness|deploy|tests|plans|docs)/[^`\s]+)`", text))
    assert cited
    missing = sorted(p for p in cited if not (REPO / p).exists())
    assert missing == []
