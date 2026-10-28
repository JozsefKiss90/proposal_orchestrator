"""AN12 — the host runbook describes only what the code does.

Every ``python -m`` line of ``plans/msca_dn_an12_host_runbook.md`` for
the three AN12 commands is parsed by that command's own parser, every
required flag of each command appears in it, and every repository path it
cites exists. The V12 pattern: a runbook that drifts from its parser fails
here, not on the host.

R9e (decision record ``aws-redeployment-r9e-eu-region_2026-10-27``): every
host command runs through the launcher ``runner.host_env``, whose own parser
reads the prefix; no line exports the secret's keys; the Regions of a line
agree with the Region the deployment parameters name; no ``us-east-1``,
``us.`` or ``global.`` id is left.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
from pathlib import Path

import pytest

from harness.commands import converse_smoke as cs
from runner import host_env
from runner import offline_bundle as ob
from tools import anonymisation_host_smoke as smoke

REPO = Path(__file__).resolve().parents[1]
RUNBOOK = REPO / "plans" / "msca_dn_an12_host_runbook.md"

PARSERS: dict[str, argparse.ArgumentParser] = {
    "runner.offline_bundle": ob._parser(),
    "tools.anonymisation_host_smoke": smoke._parser(),
    "harness.commands.converse_smoke": cs._parser(),
}


LAUNCHER = "runner.host_env"
SECRET_ID = "proposal-orchestrator/env-config"
PARAMETERS = REPO / "deploy" / "aws" / "parameters" / "secret.json"


def _invocations() -> list[tuple[int, str, list[str], list[str] | None]]:
    """Each documented invocation of an AN12 command.

    As ``(part, module, argv, launcher_argv)``: the runbook part it is in, the
    command's module and arguments, and the launcher's own arguments when the
    line starts with ``python -m runner.host_env ... --`` (else ``None``).
    """
    text = RUNBOOK.read_text(encoding="utf-8")
    found: list[tuple[int, str, list[str], list[str] | None]] = []
    for part_match in re.finditer(r"^## Part (\d+)\b(.*?)(?=^## |\Z)", text, re.S | re.M):
        part = int(part_match[1])
        for block in re.findall(r"```bash\n(.*?)```", part_match[2], re.S):
            joined = re.sub(r"\\\n\s*", " ", block)
            for line in joined.splitlines():
                launcher_argv = None
                launched = re.search(rf"-m {re.escape(LAUNCHER)} (.*?) -- (.*)$", line)
                if launched:
                    launcher_argv = shlex.split(launched[1])
                    line = launched[2]
                match = re.search(r"-m (\S+) (.*)$", line)
                if match and match[1] in PARSERS:
                    argv = shlex.split(re.sub(r"<[^>]*>", "x", match[2]))
                    found.append((part, match[1], argv, launcher_argv))
    return found


INVOCATIONS = _invocations()
COMMANDS = [(module, argv) for _part, module, argv, _launcher in INVOCATIONS]


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


# --------------------------------------------------------------------------- #
# R9e: the launcher, the Region and the id rule
# --------------------------------------------------------------------------- #


def _region() -> str:
    """The Region the deployment parameters name (OD1-r1), not a literal here."""
    entries = json.loads(PARAMETERS.read_text(encoding="utf-8-sig"))
    return {e["ParameterKey"]: e["ParameterValue"] for e in entries}["ExpectedRegion"]


def _flag(argv: list[str], name: str) -> str | None:
    return argv[argv.index(name) + 1] if name in argv else None


def test_the_runbook_has_host_and_workstation_commands():
    parts = {part for part, *_rest in INVOCATIONS}
    assert 1 in parts and parts & {2, 3, 4}


@pytest.mark.parametrize("part, module, argv, launcher", INVOCATIONS,
                         ids=[f"part{p}-{m}-{a[0]}" for p, m, a, _l in INVOCATIONS])
def test_every_host_command_runs_through_the_launcher(part, module, argv, launcher):
    if part == 1:
        assert launcher is None, "the workstation reads no runtime secret"
        return
    assert launcher is not None, (module, argv)
    args = host_env._parser().parse_args([*launcher, "--", "x"])
    assert args.secret_id == SECRET_ID
    assert args.region == _region()


@pytest.mark.parametrize("part, module, argv, launcher", INVOCATIONS,
                         ids=[f"part{p}-{m}-{a[0]}" for p, m, a, _l in INVOCATIONS])
def test_the_regions_of_a_line_agree(part, module, argv, launcher):
    if launcher is None:
        return
    region = _flag(launcher, "--region")
    if "--region" in argv:
        assert _flag(argv, "--region") == region
    version = _flag(argv, "--assessor-version")
    if version is not None:
        assert version.startswith(f"bedrock-converse-{region}@"), version


def test_no_line_exports_the_secrets_keys():
    text = RUNBOOK.read_text(encoding="utf-8")
    keys = (*host_env.CONFIG_KEYS, *host_env.DERIVED_KEYS, "ORCHESTRATOR_TRANSPORT_BACKEND")
    exported = re.findall(r"^\s*export\s+(\w+)=", text, re.M)
    assert [k for k in exported if k in keys] == []


def test_no_us_east_1_and_only_eu_profiles():
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "us-east-1" not in text
    assert re.findall(r"`(?:us|global)\.anthropic\.[^`]*`", text) == []
    assert re.findall(r"`eu\.anthropic\.claude-[^`]+`", text)
    assert "global." in text, "the id rule names what is excluded"
