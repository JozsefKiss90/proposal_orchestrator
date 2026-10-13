"""The PE-09 runbook describes only what the code does (ticket V12).

The runbook is the only artifact of this milestone a human executes. Its
command lines are run by an operator in a private network, against a build
nobody here can watch, so a flag that no longer exists is discovered by the
operator at the cost of a step. That happened once already: V06 made
``--grounding-scope`` required and every documented ``preflight`` and
``assess`` line was silently wrong until V06 corrected them.

So the runbook's operational claims are measured here rather than reviewed:

* every long flag in every documented command line is a flag that command's
  parser accepts, read from its own ``--help``;
* every required choice the parser's usage states is documented, so a new
  required flag breaks this test rather than the operator's run;
* the enumerated freeze conditions are exactly :data:`BASELINE_CHECKS`, and
  the stated count is its length;
* every repository path, test module and test class the runbook cites exists;
* the claims the ticket corrected stay corrected — the planted-marker test is
  cited as a test and not as a freeze step, the cross-baseline ``diff`` is out
  of the command path, Stage B excludes the ESR comparison, and PE-09 is still
  labelled unexecuted here.

The flags are read from each command's own ``--help`` rather than from its
parser object. That is the surface the operator reads, and it is the only
surface all these commands share: ``harness.commands.blind_assessment`` exposes
a parser builder, while the ``tools`` entry points build theirs inside
``main()``.

What this module does not do: run a command. Nothing here spends assessor
quota, and ``--help`` is the only invocation.

Constitutional standing: a test over a plan document. It evaluates no gate and
invokes no Claude.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from harness.blind_baseline import BASELINE_CHECKS
from runner.paths import find_repo_root

REPO = find_repo_root()
RUNBOOK = REPO / "plans" / "msca_dn_pe09_runbook.md"

#: The launcher the runbook documents. Here it is this interpreter, which the
#: suite already runs under.
_LAUNCHER = "py -3.10 -m "

#: Top-level directories a backticked path may name. A token outside them is
#: prose, not a path.
_PATH_ROOTS = (
    "docs/",
    "harness/",
    "plans/",
    "runner/",
    "tests/",
    "tools/",
    "workspaces/",
)

_FLAG = re.compile(r"--[a-z][a-z0-9-]*")
_OPTION_ROW = re.compile(r"^  (-{1,2}[^\s].*)$")
_BACKTICKED = re.compile(r"`([^`]+)`")
_TEST_REF = re.compile(r"(tests/[\w/]+\.py)(?:::(\w+))?")


# --------------------------------------------------------------------------- #
# Reading the runbook
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def runbook() -> str:
    return RUNBOOK.read_text(encoding="utf-8")


def _fenced_blocks(text: str) -> list[str]:
    """Every fenced block's body, line continuations joined."""
    blocks: list[str] = []
    current: list[str] = []
    inside = False
    for line in text.splitlines():
        if line.startswith("```"):
            if inside:
                blocks.append("\n".join(current))
                current = []
            inside = not inside
            continue
        if inside:
            current.append(line)
    assert not inside, "the runbook has an unclosed fenced block"
    return [b.replace("\\\n", " ") for b in blocks]


def _command_lines(text: str) -> list[str]:
    """Every documented command line, one string each."""
    found: list[str] = []
    for block in _fenced_blocks(text):
        for raw in block.splitlines():
            line = raw.strip()
            if line.startswith(_LAUNCHER):
                found.append(" ".join(line.split()))
    return found


def _invocation(line: str) -> tuple[str, str | None]:
    """The module and sub-command a documented line invokes."""
    tokens = line.split()
    at = len(_LAUNCHER.split())
    module = tokens[at]
    sub = None
    if len(tokens) > at + 1 and not tokens[at + 1].startswith("-"):
        sub = tokens[at + 1]
    return module, sub


def _section(text: str, heading: str) -> str:
    """One section's body, found by the start of its heading line.

    Local on purpose, and not the same contract as the reader in
    ``tests/harness/test_acceptance_lane.py``: this one takes a heading at any
    level, excludes the heading line, and stops at the next heading of the same
    level or shallower, so a ``##`` section carries its ``###`` subsections.
    """
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith(heading):
            level = len(line) - len(line.lstrip("#"))
            body: list[str] = []
            for nxt in lines[i + 1 :]:
                if nxt.startswith("#") and (len(nxt) - len(nxt.lstrip("#"))) <= level:
                    break
                body.append(nxt)
            return "\n".join(body)
    raise AssertionError(f"the runbook carries no section {heading!r}")


# --------------------------------------------------------------------------- #
# Reading the parsers
# --------------------------------------------------------------------------- #


_HELP_CACHE: dict[tuple[str, str | None], str] = {}


def _help(module: str, sub: str | None) -> str:
    """The command's own ``--help``, from this interpreter."""
    key = (module, sub)
    if key not in _HELP_CACHE:
        argv = [sys.executable, "-m", module]
        if sub:
            argv.append(sub)
        argv.append("--help")
        done = subprocess.run(
            argv, cwd=REPO, capture_output=True, text=True, timeout=300
        )
        assert done.returncode == 0, f"{' '.join(argv)} exited {done.returncode}: {done.stderr}"
        _HELP_CACHE[key] = done.stdout
    return _HELP_CACHE[key]


def _accepted_flags(help_text: str) -> set[str]:
    """The long flags the parser accepts, from its option rows.

    Read from the rows argparse writes for each option, never from a
    description, so a flag merely discussed in help prose is not mistaken for
    one the parser takes.
    """
    flags: set[str] = set()
    for line in help_text.splitlines():
        m = _OPTION_ROW.match(line)
        if not m:
            continue
        invocation = re.split(r"\s{2,}", m.group(1))[0]
        flags.update(_FLAG.findall(invocation))
    return flags


def _usage(help_text: str) -> str:
    """The usage block, as one line."""
    out: list[str] = []
    for line in help_text.splitlines():
        if line.startswith("usage:"):
            out.append(line[len("usage:") :])
            continue
        if out:
            if not line.strip():
                break
            out.append(line)
    assert out, "the help output carries no usage block"
    return " ".join(" ".join(out).split())


def _required_choices(help_text: str) -> tuple[tuple[str, ...], ...]:
    """Every required choice in the usage block, as its alternatives.

    One choice per tuple, and a documented line satisfies a choice by carrying
    any one of its members. A flag outside every bracket is a choice of one. A
    parenthesised group outside every bracket, which argparse writes for a
    required mutually exclusive group, is a choice of its alternatives.
    """
    usage = _usage(help_text)
    groups: list[tuple[str, ...]] = []
    depth_optional = 0
    depth_group = 0
    buffer: list[str] = []
    token = ""

    def flush() -> None:
        nonlocal token
        if token.startswith("--"):
            if depth_group:
                buffer.append(token)
            else:
                groups.append((token,))
        token = ""

    for ch in usage:
        if ch in "[]()":
            flush()
            if ch == "[":
                depth_optional += 1
            elif ch == "]":
                depth_optional = max(0, depth_optional - 1)
            elif ch == "(":
                depth_group += 1
            else:
                depth_group = max(0, depth_group - 1)
                if depth_group == 0 and buffer:
                    groups.append(tuple(buffer))
                    buffer = []
            continue
        if ch.isspace() or ch == "|":
            flush()
            continue
        if depth_optional:
            continue
        token += ch
    flush()
    return tuple(groups)


# --------------------------------------------------------------------------- #
# The commands
# --------------------------------------------------------------------------- #


class TestTheDocumentedCommands:
    def test_the_runbook_documents_commands_at_all(self, runbook: str) -> None:
        """A runbook with no command line would pass every check below."""
        assert len(_command_lines(runbook)) >= 6

    def test_every_documented_flag_is_one_its_parser_accepts(self, runbook: str) -> None:
        for line in _command_lines(runbook):
            module, sub = _invocation(line)
            accepted = _accepted_flags(_help(module, sub))
            for flag in sorted(set(_FLAG.findall(line))):
                assert flag in accepted, (
                    f"{module} {sub or ''} does not accept {flag}: {line}"
                )

    def test_every_required_flag_is_documented(self, runbook: str) -> None:
        """The V06 failure mode: a flag the parser requires and no command
        line carries, so every documented invocation refuses."""
        for line in _command_lines(runbook):
            module, sub = _invocation(line)
            documented = set(_FLAG.findall(line))
            for alternatives in _required_choices(_help(module, sub)):
                assert documented & set(alternatives), (
                    f"{module} {sub or ''} requires one of {alternatives}, and "
                    f"this line carries none: {line}"
                )

    def test_no_command_line_names_the_public_comparison(self, runbook: str) -> None:
        """Criterion 5. A diff whose before-side is the sanitised copy's
        comparison and whose after-side is the original's is refused by
        design, so it is not a step anyone is told to run."""
        public = "docs/tier4_orchestration_state/msca_dn/comparisons/comparison_f60ae6e0a2a1_0003.json"
        for line in _command_lines(runbook):
            assert public not in line, f"the refused pair is still a command: {line}"
        assert public in runbook, "the refusal is not explained anywhere"


# --------------------------------------------------------------------------- #
# The freeze
# --------------------------------------------------------------------------- #


class TestTheFreezeConditions:
    """Criterion 1. The runbook claimed fifteen conditions including a
    planted-marker test. There are now twenty-two, and none of them is that
    test."""

    @pytest.fixture(scope="class")
    def enumerated(self, runbook: str) -> tuple[str, ...]:
        section = _section(runbook, "### The conditions the freeze checks")
        blocks = _fenced_blocks(section)
        assert len(blocks) == 1, "the conditions are not in one fenced block"
        return tuple(
            name.strip() for name in blocks[0].replace("\n", ",").split(",") if name.strip()
        )

    def test_the_enumeration_is_the_codes_own(self, enumerated: tuple[str, ...]) -> None:
        assert set(enumerated) == set(BASELINE_CHECKS), (
            f"documented but not checked: {sorted(set(enumerated) - set(BASELINE_CHECKS))}; "
            f"checked but not documented: {sorted(set(BASELINE_CHECKS) - set(enumerated))}"
        )

    def test_each_condition_is_named_once(self, enumerated: tuple[str, ...]) -> None:
        assert len(enumerated) == len(set(enumerated))

    def test_the_stated_count_is_the_codes_own(self, runbook: str) -> None:
        assert f"{len(BASELINE_CHECKS)} baseline conditions" in runbook

    def test_the_freeze_step_claims_no_planted_marker(self, runbook: str) -> None:
        for heading in ("### The freeze", "### The conditions the freeze checks"):
            section = _section(runbook, heading)
            assert "planted" not in section.lower(), (
                f"{heading} still claims the planted-marker test"
            )

    def test_the_planted_marker_test_is_cited_as_a_test(self, runbook: str) -> None:
        """Where it belongs: among the transport and isolation controls."""
        isolation = _section(runbook, "### Isolation, and what it does not authorise")
        assert "tests/harness/test_blind_baseline.py::TestPlantedMarkers" in isolation


# --------------------------------------------------------------------------- #
# What the runbook points at
# --------------------------------------------------------------------------- #


class TestEveryCitationResolves:
    def _paths(self, runbook: str) -> set[str]:
        found: set[str] = set()
        for token in _BACKTICKED.findall(runbook):
            token = token.strip()
            if "<" in token or " " in token or token.startswith("."):
                continue
            if token.startswith(_PATH_ROOTS):
                found.add(token.split("::", 1)[0])
        return found

    def test_the_scan_finds_paths(self, runbook: str) -> None:
        assert len(self._paths(runbook)) >= 10

    def test_every_cited_path_exists(self, runbook: str) -> None:
        missing = sorted(p for p in self._paths(runbook) if not (REPO / p).exists())
        assert missing == [], f"the runbook cites what is not here: {missing}"

    def test_every_cited_test_class_exists(self, runbook: str) -> None:
        for module, cls in _TEST_REF.findall(runbook):
            path = REPO / module
            assert path.is_file(), module
            if cls:
                body = path.read_text(encoding="utf-8")
                assert f"class {cls}" in body, f"{module} carries no {cls}"


# --------------------------------------------------------------------------- #
# The corrections the ticket asked for
# --------------------------------------------------------------------------- #


class TestTheCorrectionsHold:
    def test_the_historical_profile_is_the_one_on_this_build(self, runbook: str) -> None:
        """Criterion 3. The profile is authored from V09's matrix, not
        defaulted from the 2026 rules."""
        section = _section(runbook, "## 3.")
        assert "harness/profiles/msca_dn_2025_historical.json" in section
        assert "equivalence_matrix_2025_2026-10-13.json" in section

    def test_the_import_route_is_v07s_with_v08s_measurement(self, runbook: str) -> None:
        """Criterion 4."""
        section = _section(runbook, "## 4.")
        assert "--document official_original" in section
        assert "plans/msca_dn_v08_original_dry_import_procedure.md" in section

    def test_checkpointing_is_described_as_the_default(self, runbook: str) -> None:
        """Criterion 2."""
        section = _section(runbook, "## 5.")
        assert "--no-checkpoint" in section
        assert ".harness/checkpoints/" in section

    def test_stage_b_excludes_the_esr_comparison(self, runbook: str) -> None:
        """Criterion 6."""
        section = _section(runbook, "## 8.")
        for excluded in ("compare", "review", "diff"):
            assert f"`{excluded}`" in section, excluded
        assert "do not apply" in section

    def test_the_declared_identifiers_are_called_declared(self, runbook: str) -> None:
        """Criterion 7."""
        section = _section(runbook, "## 5.")
        assert "declared identifier" in section
        assert "temperature" in section

    def test_isolation_is_distinguished_from_authorisation(self, runbook: str) -> None:
        """Criterion 7. An empty tool list is not permission to send private
        content to a provider, and a working directory is not a sandbox."""
        section = _section(runbook, "## 5.")
        lowered = section.lower()
        assert "not an operating-system sandbox" in lowered
        assert "not authorisation" in lowered

    def test_pe09_is_still_unexecuted_here(self, runbook: str) -> None:
        assert "not executed in this repository" in runbook
        assert "74.60" in runbook
