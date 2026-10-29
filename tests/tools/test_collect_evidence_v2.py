"""R12a — the parameterised evidence collector (``tools/collect_evidence_v2.py``).

Ticket R12a of ``plans/aws_redeployment_tickets.md``; decision record
``aws-redeployment-r12a-collector_2026-10-28``. The ticket's criteria:

1. a test runs the collector against fixture stack outputs and confirms that
   every id it uses comes from them (``TestCriterion1``);
2. a test confirms that the collector refuses an output path inside the v1
   tree (``TestCriterion2``);
3. the R3 old-ID test passes over the collector (``test_old_id_guard_is_clean_over_the_collector``
   here, and the guard's default scope in ``tests/test_old_id_guard.py``).

Nothing here calls AWS: a fake runner answers every command and records it.
The fixtures (``tests/tools/fixtures/collector/``) are synthetic.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Sequence

import pytest

from runner import host_env
from tools import collect_evidence_v2 as collector
from tools import env_config_digest, evidence_secret_scan, old_id_guard
from tools.collect_evidence_v2 import RunResult

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "tests" / "tools" / "fixtures" / "collector"
HOST_CHECKS = REPO / "tools" / "collector_host_checks"
MODULE = REPO / "tools" / "collect_evidence_v2.py"
CONTRACT = REPO / "deploy" / "aws" / "outputs_contract.json"
REGISTER_V2 = REPO / "docs" / "infrastructure_security" / "aws_hardening_control_register_v2.md"
REAL_OUTPUTS = [REPO / "docs" / "infrastructure_security" / "evidence_v2" / t / f"{t}_outputs.json"
                for t in ("R4", "R5", "R6", "R7", "R8")]
REAL_PARAMETERS = sorted((REPO / "deploy" / "aws" / "parameters").glob("*.json"))

FIXED_NOW = datetime(2026, 10, 28, 12, 0, 0, tzinfo=timezone.utc)
FAKE_COMMAND_IDS = [f"0c0c0c0c-0000-4000-8000-{n:012d}" for n in range(1, 40)]

# Id-shaped tokens (criterion 1). ARNs are covered through the atoms they hold.
ID_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?<![\w-])\d{12}(?![\w])"),
    re.compile(r"\b[a-z]{2}-(?:north|south|east|west|central|northeast|southeast|northwest|southwest)-\d\b"),
    re.compile(r"\b(?:vpc|subnet|sg|vpce|rtb|i|fl|pl|eni|igw|nat|sgr)-[0-9a-f]{8,17}\b"),
    re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"),
    re.compile(r"\b(?:(?:eu|us|apac|global)\.)?(?:anthropic|amazon|meta|mistral|cohere|ai21)\.[a-z0-9][a-z0-9.:-]*"),
)
NAME_PATTERN = re.compile(r"[a-z0-9-]*fx-orch[a-z0-9._-]*")
PROJECT_PATTERN = re.compile(r"proposal-orchestrator[a-z0-9-]*")


def _atoms(text: str) -> set[str]:
    found: set[str] = set()
    for pattern in (*ID_PATTERNS, NAME_PATTERN):
        found.update(m.group(0) for m in pattern.finditer(text))
    return found


def _texts(root: Path) -> str:
    return "\n".join(p.read_text(encoding="utf-8-sig") for p in sorted(root.rglob("*.json")))


# ---------------------------------------------------------------------------
# The fake AWS CLI
# ---------------------------------------------------------------------------


class FakeAws:
    """Answers like the AWS CLI and records every argv."""

    def __init__(self, fixtures: Path, account: str = "111122223333") -> None:
        self.calls: list[list[str]] = []
        self.account = account
        self.overrides: dict[tuple[str, str], Callable[[Sequence[str]], RunResult]] = {}
        self.stacks: dict[str, Any] = {}
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        for stack in contract["stacks"]:
            path = fixtures / "outputs" / stack["ticket"] / f"{stack['ticket']}_outputs.json"
            self.stacks[stack["stack_name"]] = json.loads(path.read_text(encoding="utf-8-sig"))
        self._ids = iter(FAKE_COMMAND_IDS)

    def __call__(self, argv: Sequence[str]) -> RunResult:
        self.calls.append(list(argv))
        key = (argv[1], argv[2])
        if key in self.overrides:
            return self.overrides[key](argv)
        if key == ("sts", "get-caller-identity"):
            return RunResult(0, json.dumps({"Account": self.account, "Arn": "arn:aws:sts::%s:assumed-role/fx-admin/s"
                                            % self.account}), "")
        if key == ("cloudformation", "describe-stacks"):
            name = argv[argv.index("--stack-name") + 1]
            return RunResult(0, json.dumps(self.stacks[name]), "")
        if key == ("ssm", "send-command"):
            return RunResult(0, json.dumps(next(self._ids)), "")
        if key == ("ssm", "get-command-invocation"):
            return RunResult(0, json.dumps({"Status": "Success", "ResponseCode": 0,
                                            "StandardOutputContent": "CHECK=x\nRESULT=expected\n",
                                            "StandardErrorContent": ""}), "")
        return RunResult(0, json.dumps({"fake": argv[2]}), "")

    def commands(self) -> list[str]:
        return [" ".join(c) for c in self.calls]


def _error(code: str, rc: int = 254) -> Callable[[Sequence[str]], RunResult]:
    return lambda argv: RunResult(rc, "", f"\nAn error occurred ({code}) when calling the X operation: no\n")


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A minimal repository tree: the v1 and v2 evidence trees and a ticket folder."""
    infra = tmp_path / "docs" / "infrastructure_security"
    (infra / "evidence" / "11_audit_package").mkdir(parents=True)
    (infra / "audit_package").mkdir()
    (infra / "aws_hardening_control_register.md").write_text("v1\n", encoding="utf-8")
    (infra / "evidence_v2" / "R12b").mkdir(parents=True)
    return tmp_path


def _args(repo: Path, fixtures: Path = FIXTURES, *extra: str, host: bool = True) -> list[str]:
    args = ["--ticket", "R12b", "--step", "03", "--profile", "fx-profile", "--repo-root", str(repo),
            "--source-root", str(REPO), "--parameters-dir", str(fixtures / "parameters"),
            "--outputs-root", str(fixtures / "outputs"), "--inputs", str(fixtures / "collector_inputs.json")]
    if host:
        args += ["--host-outputs", str(fixtures / "outputs" / "R11" / "R11_outputs.json")]
    return args + list(extra)


def _run(repo: Path, fake: FakeAws, *extra: str, fixtures: Path = FIXTURES, host: bool = True,
         echo: Optional[list[str]] = None, sleeps: Optional[list[float]] = None) -> int:
    lines = echo if echo is not None else []
    slept = sleeps if sleeps is not None else []
    return collector.main(_args(repo, fixtures, *extra, host=host), runner=fake, clock=lambda: FIXED_NOW,
                          sleep=slept.append, echo=lines.append)


def _out(repo: Path) -> Path:
    return repo / "docs" / "infrastructure_security" / "evidence_v2" / "R12b" / "R12b_03_collector"


def _summary(repo: Path) -> dict[str, Any]:
    return json.loads((_out(repo) / "summary.json").read_text(encoding="utf-8"))


def _ssm_parameters(argv: Sequence[str]) -> dict[str, Any]:
    return json.loads(argv[argv.index("--parameters") + 1])


# ---------------------------------------------------------------------------
# Criterion 1: every id comes from the fixture outputs (point 9)
# ---------------------------------------------------------------------------


class TestCriterion1:
    def test_every_id_in_every_command_comes_from_the_fixtures(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        f7 = repo / "f7.txt"
        f7.write_text("https://fx-outside.s3.ap-east-9.amazonaws.com/o?X-Amz-Signature=fx\n", encoding="utf-8")
        assert _run(repo, fake, "--host-bundle-dir", "/opt/fx-bundle", "--f7-url-file", str(f7)) == 0

        allowed = _atoms(_texts(FIXTURES)) | set(FAKE_COMMAND_IDS) | _atoms(f7.read_text(encoding="utf-8"))
        stack_names = {s["stack_name"] for s in json.loads(CONTRACT.read_text(encoding="utf-8"))["stacks"]}
        used: set[str] = set()
        for command in fake.commands():
            tokens = _atoms(command)
            used |= tokens
            assert tokens <= allowed, (command[:200], sorted(tokens - allowed))
            assert set(PROJECT_PATTERN.findall(command)) <= stack_names, command[:200]
        # Every account, Region and resource id of the fixtures was actually used.
        for value in ("111122223333", "eu-west-9", "eu-south-9", "ap-east-9", "vpc-0f1f1f1f1f1f1f1f1",
                      "rtb-0f3f3f3f3f3f3f3f3", "sg-0f4f4f4f4f4f4f4f4", "sg-0f5f5f5f5f5f5f5f5",
                      "vpce-0f6f6f6f6f6f6f6f6", "fl-0f7f7f7f7f7f7f7f7", "i-0f8f8f8f8f8f8f8f8",
                      "vpce-0e1e1e1e1e1e1e1e1", "vpce-0e6e6e6e6e6e6e6e6", "0f0f0f0f-1111-4222-8333-444455556666",
                      "eu.anthropic.claude-fx-alpha-v1", "fx-orch-deploy-111122223333"):
            assert value in used, value

    def test_the_host_scripts_and_the_module_hold_no_id(self) -> None:
        texts = {p.name: p.read_text(encoding="utf-8") for p in HOST_CHECKS.iterdir() if p.is_file()}
        texts[MODULE.name] = MODULE.read_text(encoding="utf-8")
        for name, text in texts.items():
            found = set()
            for pattern in ID_PATTERNS:
                found.update(m.group(0) for m in pattern.finditer(text))
            assert found == set(), (name, sorted(found))

    def test_swapping_the_fixture_ids_swaps_the_commands(self, repo: Path, tmp_path: Path) -> None:
        swapped = tmp_path / "swapped"
        shutil.copytree(FIXTURES, swapped)
        mapping = {"111122223333": "444455556666", "eu-west-9": "eu-west-8", "eu-south-9": "eu-south-8",
                   "ap-east-9": "ap-east-8", "fx-orch": "fy-orch", "0f": "0d", "0e": "0c", "claude-fx": "claude-fz", "fx-other": "fz-other"}
        for path in swapped.rglob("*.json"):
            text = path.read_text(encoding="utf-8-sig")
            for old, new in mapping.items():
                text = text.replace(old, new)
            path.write_text(text, encoding="utf-8-sig")

        first, second = FakeAws(FIXTURES), FakeAws(swapped, account="444455556666")
        assert _run(repo, first) == 0
        shutil.rmtree(_out(repo))
        assert _run(repo, second, fixtures=swapped) == 0

        before = set().union(*(_atoms(c) for c in first.commands()))
        after = set().union(*(_atoms(c) for c in second.commands()))
        assert len(first.calls) == len(second.calls)
        assert before & after <= set(FAKE_COMMAND_IDS)
        assert {"444455556666", "eu-west-8", "vpc-0d1f1f1f1f1f1f1f1", "i-0d8f8f8f8f8f8f8f8"} <= after

    def test_no_fixture_value_is_a_real_value(self) -> None:
        real: set[str] = set()
        for path in REAL_OUTPUTS:
            for entry in json.loads(path.read_text(encoding="utf-8-sig")):
                real.add(entry["OutputValue"])
        for path in REAL_PARAMETERS:
            for entry in json.loads(path.read_text(encoding="utf-8-sig")):
                real.update(entry["ParameterValue"].split(","))
        real_atoms = real | set().union(*(_atoms(v) for v in real))
        fixture_text = _texts(FIXTURES)
        fixture_atoms = _atoms(fixture_text)
        assert fixture_atoms, "the fixtures hold ids"
        assert fixture_atoms & real_atoms == set()
        assert not any(value in fixture_text for value in real if len(value) > 6)

    def test_no_real_value_reaches_a_fixture_run(self, repo: Path) -> None:
        real: set[str] = set()
        for path in REAL_OUTPUTS:
            real.update(e["OutputValue"] for e in json.loads(path.read_text(encoding="utf-8-sig")))
        for path in REAL_PARAMETERS:
            for entry in json.loads(path.read_text(encoding="utf-8-sig")):
                real.update(entry["ParameterValue"].split(","))
        real_atoms = set().union(*(_atoms(v) for v in real))
        fake = FakeAws(FIXTURES)
        assert _run(repo, fake) == 0
        for command in fake.commands():
            assert _atoms(command) & real_atoms == set(), command[:200]


# ---------------------------------------------------------------------------
# Criterion 2: the v1 tree and every other wrong path are refused (point 6, 20)
# ---------------------------------------------------------------------------


class TestCriterion2:
    @pytest.mark.parametrize("target", [
        "docs/infrastructure_security/evidence",
        "docs/infrastructure_security/evidence/11_audit_package",
        "docs/infrastructure_security/evidence/R12b/R12b_03_collector",
        "docs/infrastructure_security/audit_package/R12b_03_collector",
        "docs/infrastructure_security/aws_hardening_control_register.md",
        "docs/infrastructure_security/evidence_v2/R12b/../../evidence/R12b_03_collector",
    ])
    def test_a_path_inside_the_v1_tree_is_refused_before_any_aws_call(self, repo: Path, target: str) -> None:
        fake = FakeAws(FIXTURES)
        echo: list[str] = []
        before = sorted(p.as_posix() for p in repo.rglob("*"))

        assert _run(repo, fake, "--out", target, echo=echo) == collector.EXIT_REFUSED

        assert fake.calls == []
        assert sorted(p.as_posix() for p in repo.rglob("*")) == before
        assert any("v1 evidence tree" in line for line in echo), echo

    def test_an_absolute_v1_path_is_refused(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        target = repo / "docs" / "infrastructure_security" / "evidence" / "x"
        assert _run(repo, fake, "--out", str(target)) == collector.EXIT_REFUSED
        assert fake.calls == [] and not target.exists()

    def test_a_symlink_into_the_v1_tree_is_refused(self, repo: Path) -> None:
        v2_ticket = repo / "docs" / "infrastructure_security" / "evidence_v2" / "R12c"
        try:
            os.symlink(repo / "docs" / "infrastructure_security" / "evidence", v2_ticket, target_is_directory=True)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks cannot be created here")
        fake = FakeAws(FIXTURES)
        echo: list[str] = []
        code = collector.main(_args(repo) [:1] + ["R12c"] + _args(repo)[2:], runner=fake, clock=lambda: FIXED_NOW,
                              sleep=lambda s: None, echo=echo.append)
        assert code == collector.EXIT_REFUSED
        assert fake.calls == []
        assert any("v1 evidence tree" in line for line in echo), echo
        assert not (repo / "docs" / "infrastructure_security" / "evidence" / "R12c_03_collector").exists()

    @pytest.mark.parametrize("target, message", [
        ("docs/other/R12b_03_collector", "outside"),
        ("docs/infrastructure_security/evidence_v2", "outside"),
        ("docs/infrastructure_security/evidence_v2/R12b", "must be"),
        ("docs/infrastructure_security/evidence_v2/R12b/custom", "must be"),
        ("docs/infrastructure_security/evidence_v2/R12a/R12b_03_collector", "must be"),
    ])
    def test_any_other_path_is_refused(self, repo: Path, target: str, message: str) -> None:
        fake = FakeAws(FIXTURES)
        echo: list[str] = []
        assert _run(repo, fake, "--out", target, echo=echo) == collector.EXIT_REFUSED
        assert fake.calls == []
        assert any(message in line for line in echo), echo

    def test_an_existing_run_folder_is_never_overwritten(self, repo: Path) -> None:
        _out(repo).mkdir()
        (_out(repo) / "keep.txt").write_text("x\n", encoding="utf-8")
        fake = FakeAws(FIXTURES)
        assert _run(repo, fake) == collector.EXIT_REFUSED
        assert fake.calls == []
        assert sorted(p.name for p in _out(repo).iterdir()) == ["keep.txt"]

    def test_a_missing_ticket_folder_is_refused(self, repo: Path) -> None:
        shutil.rmtree(repo / "docs" / "infrastructure_security" / "evidence_v2" / "R12b")
        fake = FakeAws(FIXTURES)
        assert _run(repo, fake) == collector.EXIT_REFUSED
        assert fake.calls == []

    @pytest.mark.parametrize("ticket, step", [("R12b/../x", "03"), ("evidence", "03"), ("R12b", "3"), ("R12b", "a1")])
    def test_ticket_and_step_must_be_well_formed(self, repo: Path, ticket: str, step: str) -> None:
        with pytest.raises(collector.CollectorRefused):
            collector.resolve_output_dir(repo, ticket, step)

    def test_the_derived_folder_is_the_only_one_accepted(self, repo: Path) -> None:
        resolved = collector.resolve_output_dir(repo, "R12b", "03")
        assert resolved == _out(repo).resolve()
        assert not resolved.exists()


# ---------------------------------------------------------------------------
# A whole run against the fixtures (points 3, 4, 7, 10, 16, 20)
# ---------------------------------------------------------------------------


def _register_controls() -> set[str]:
    rows = set()
    for line in REGISTER_V2.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 2 and re.fullmatch(r"DC-\d{2}|PL-8", cells[1]):
            rows.add(cells[1])
    return rows


class TestRun:
    def test_a_full_run_writes_one_file_per_check_a_summary_and_a_manifest(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        assert _run(repo, fake) == 0
        out = _out(repo)
        names = sorted(p.name for p in out.iterdir())
        assert "00_caller-identity.json" in names
        assert {f"00_stack-outputs-{k}.json" for k in ("network", "iam", "kms", "audit", "secret", "host")} <= set(names)
        assert "DC-06_route-table.json" in names and "DC-15_host-no-long-term-keys.json" in names
        manifest = (out / collector.MANIFEST_NAME).read_text(encoding="utf-8").splitlines()
        listed = {line.split("  ", 1)[1]: line.split("  ", 1)[0] for line in manifest}
        assert set(listed) == set(names) - {collector.MANIFEST_NAME}
        for name, digest in listed.items():
            assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest
        assert evidence_secret_scan.scan_folder(out) == []
        assert old_id_guard.scan_paths([out]) == []
        summary = _summary(repo)
        assert set(summary["controls"]) == _register_controls()
        assert summary["account"] == "111122223333" and summary["region"] == "eu-west-9"
        assert summary["host_stack"] == "present"
        assert {c["status"] for c in summary["checks"]} <= {"collected", "not_collected"}

    def test_the_preflight_comes_first_and_the_converse_events_last(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        assert _run(repo, fake) == 0
        operations = [c[2] for c in fake.calls]
        assert operations[0] == "get-caller-identity"
        assert operations[1:7] == ["describe-stacks"] * 6
        assert operations[-1] == "lookup-events"
        assert operations.index("lookup-events") > max(i for i, op in enumerate(operations) if op == "send-command")

    def test_without_host_outputs_the_host_checks_are_not_collected(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        assert _run(repo, fake, host=False) == 0
        summary = _summary(repo)
        host_checks = [c for c in summary["checks"] if c["scope"] == "host"]
        assert host_checks and all(c["status"] == "not_collected" for c in host_checks)
        assert all("host stack outputs absent" in c["reason"] for c in host_checks)
        assert not any(c[1] == "ssm" for c in fake.calls)
        assert not any("proposal-orchestrator-host" in " ".join(c) for c in fake.calls)
        assert summary["controls"]["DC-37"]["status"] == "not_collected"
        assert summary["controls"]["DC-06"]["status"] == "collected"
        assert summary["host_stack"] == "absent"

    def test_every_register_row_is_covered_or_has_a_reason(self) -> None:
        covered = collector.coverage_map()
        assert set(covered) == _register_controls()
        assert set(collector.NON_COMMAND) == {"DC-22", "DC-38", "DC-39"}
        for control, reason in collector.NON_COMMAND.items():
            assert reason, control
            assert not any(control in c.controls for c in collector.CHECKS), control

    def test_every_check_declares_what_it_uses(self, repo: Path) -> None:
        # Refs refuses an undeclared reference: building every command proves the declarations.
        echo: list[str] = []
        f7 = repo / "f7.txt"
        f7.write_text("https://fx.s3.amazonaws.com/o\n", encoding="utf-8")
        assert collector.main(_args(repo, FIXTURES, "--plan", "--host-bundle-dir", "/opt/fx", "--f7-url-file", str(f7)),
                              runner=FakeAws(FIXTURES), clock=lambda: FIXED_NOW, echo=echo.append) == 0
        assert not any("not collected" in line for line in echo)

    def test_the_file_names_are_unique(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        assert _run(repo, fake, "--host-bundle-dir", "/opt/fx") == 0
        files = [c["file"] for c in _summary(repo)["checks"] if c["file"]]
        assert len(files) == len(set(files))

    def test_plan_calls_nothing_and_writes_nothing(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        echo: list[str] = []
        assert _run(repo, fake, "--plan", echo=echo) == 0
        assert fake.calls == []
        assert not _out(repo).exists()
        assert any("describe-route-tables" in line for line in echo)


# ---------------------------------------------------------------------------
# Refusals before collecting (points 2 and 3)
# ---------------------------------------------------------------------------


class TestRefusals:
    def test_a_caller_in_another_account_is_refused(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES, account="999988887777")
        echo: list[str] = []
        assert _run(repo, fake, echo=echo) == collector.EXIT_REFUSED
        assert [c[2] for c in fake.calls] == ["get-caller-identity"]
        assert not _out(repo).exists()
        assert any("ExpectedAccountId" in line for line in echo)

    def test_stale_stack_outputs_are_refused(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        fake.stacks["proposal-orchestrator-host"] = [
            {**e, "OutputValue": "i-0a0a0a0a0a0a0a0a0"} if e["OutputKey"] == "InstanceId" else e
            for e in fake.stacks["proposal-orchestrator-host"]
        ]
        echo: list[str] = []
        assert _run(repo, fake, echo=echo) == collector.EXIT_REFUSED
        assert not _out(repo).exists()
        assert any("stale" in line for line in echo)

    def test_a_deleted_host_stack_is_refused(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        original = fake.overrides.get

        def describe(argv: Sequence[str]) -> RunResult:
            if "proposal-orchestrator-host" in argv:
                return _error("ValidationError")(argv)
            return RunResult(0, json.dumps(fake.stacks[argv[argv.index("--stack-name") + 1]]), "")

        fake.overrides[("cloudformation", "describe-stacks")] = describe
        assert original is not None
        assert _run(repo, fake) == collector.EXIT_REFUSED
        assert not _out(repo).exists()

    def _copy(self, tmp_path: Path) -> Path:
        copy = tmp_path / "fx"
        shutil.copytree(FIXTURES, copy)
        return copy

    def test_parameter_files_that_disagree_on_the_account_are_refused(self, repo: Path, tmp_path: Path) -> None:
        copy = self._copy(tmp_path)
        path = copy / "parameters" / "kms.json"
        path.write_text(path.read_text(encoding="utf-8").replace("111122223333", "999988887777"), encoding="utf-8")
        fake = FakeAws(copy)
        assert _run(repo, fake, fixtures=copy) == collector.EXIT_REFUSED
        assert fake.calls == []

    def test_an_outputs_file_missing_a_contract_key_is_refused(self, repo: Path, tmp_path: Path) -> None:
        copy = self._copy(tmp_path)
        path = copy / "outputs" / "R4" / "R4_outputs.json"
        data = [e for e in json.loads(path.read_text(encoding="utf-8-sig")) if e["OutputKey"] != "VpcId"]
        path.write_text(json.dumps(data), encoding="utf-8")
        fake = FakeAws(copy)
        assert _run(repo, fake, fixtures=copy) == collector.EXIT_REFUSED
        assert fake.calls == []

    def test_a_negative_region_among_the_routed_ones_is_refused(self, repo: Path, tmp_path: Path) -> None:
        copy = self._copy(tmp_path)
        path = copy / "collector_inputs.json"
        path.write_text(path.read_text(encoding="utf-8").replace('"ap-east-9"', '"eu-south-9"'), encoding="utf-8")
        fake = FakeAws(copy)
        assert _run(repo, fake, fixtures=copy) == collector.EXIT_REFUSED
        assert fake.calls == []

    def test_an_input_without_a_source_is_refused(self, repo: Path, tmp_path: Path) -> None:
        copy = self._copy(tmp_path)
        path = copy / "collector_inputs.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["inputs"]["negative_region"]["source"] = ""
        path.write_text(json.dumps(data), encoding="utf-8")
        assert _run(repo, FakeAws(copy), fixtures=copy) == collector.EXIT_REFUSED

    @pytest.mark.parametrize("flag, value", [("--host-bundle-dir", "relative/path"),
                                             ("--host-bundle-dir", "/opt/x; rm -rf /"),
                                             ("--host-bundle-python", "python3 -c x")])
    def test_host_runtime_values_are_checked(self, repo: Path, flag: str, value: str) -> None:
        fake = FakeAws(FIXTURES)
        assert _run(repo, fake, flag, value) == collector.EXIT_REFUSED
        assert fake.calls == []

    def test_an_f7_file_that_is_not_one_s3_url_is_refused(self, repo: Path) -> None:
        f7 = repo / "f7.txt"
        f7.write_text("http://example.org/x\n", encoding="utf-8")
        fake = FakeAws(FIXTURES)
        assert _run(repo, fake, "--f7-url-file", str(f7)) == collector.EXIT_REFUSED
        assert fake.calls == []


# ---------------------------------------------------------------------------
# After a run: errors, expected errors, scans (point 10, 18)
# ---------------------------------------------------------------------------


class TestAfterRun:
    def test_the_dc40_access_denied_is_an_expected_error(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        fake.overrides[("organizations", "list-policies")] = _error("AccessDeniedException")
        assert _run(repo, fake) == 0
        check = next(c for c in _summary(repo)["checks"] if c["check"] == "scp-list")
        assert check["status"] == "expected_error" and check["reason"] == "AccessDeniedException"
        assert check["file"] == "DC-40_scp-list.txt"
        assert (_out(repo) / "DC-40_scp-list.txt").read_text(encoding="utf-8").startswith("exit=254\n")

    def test_the_organization_query_leaves_out_the_management_email(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        assert _run(repo, fake) == 0
        argv = next(c for c in fake.calls if c[2] == "describe-organization")
        query = argv[argv.index("--query") + 1]
        assert "Email" not in query and "MasterAccountId" in query

    def test_an_unexpected_error_fails_the_run_but_the_rest_is_collected(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        fake.overrides[("kms", "get-key-policy")] = _error("AccessDeniedException")
        echo: list[str] = []
        assert _run(repo, fake, echo=echo) == collector.EXIT_FAILED
        summary = _summary(repo)
        assert summary["controls"]["DC-19"]["status"] == "error"
        assert summary["controls"]["DC-18"]["status"] == "collected"
        assert (_out(repo) / "DC-18_describe-key.json").exists()
        assert (_out(repo) / collector.MANIFEST_NAME).exists()

    def test_a_secret_pattern_in_collected_output_fails_the_run_and_is_not_edited(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        leaked = json.dumps({"Secret" + "String": "x"})
        fake.overrides[("secretsmanager", "describe-secret")] = lambda argv: RunResult(0, leaked, "")
        echo: list[str] = []
        assert _run(repo, fake, echo=echo) == collector.EXIT_FAILED
        assert any(line.startswith("SECRET SCAN:") for line in echo)
        assert (_out(repo) / "DC-20_describe-secret.json").read_text(encoding="utf-8") == leaked + "\n"

    def test_an_old_id_in_collected_output_fails_the_run(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        planted = json.dumps({"VpcId": old_id_guard.OLD_IDS["old VPC"]})
        fake.overrides[("ec2", "describe-vpcs")] = lambda argv: RunResult(0, planted, "")
        echo: list[str] = []
        assert _run(repo, fake, echo=echo) == collector.EXIT_FAILED
        assert any(line.startswith("OLD-ID GUARD:") for line in echo)


# ---------------------------------------------------------------------------
# Host checks through SSM (points 4, 5, 16, 17, 19)
# ---------------------------------------------------------------------------


class TestHostChecks:
    def test_each_host_check_sends_its_fixed_script_and_saves_the_invocation(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        assert _run(repo, fake) == 0
        sends = [c for c in fake.calls if c[2] == "send-command"]
        summary = _summary(repo)
        host = [c for c in summary["checks"] if c["scope"] == "host" and c["status"] == "collected"]
        assert len(sends) == len(host) == 7
        for argv in sends:
            assert argv[argv.index("--document-name") + 1] == "AWS-RunShellScript"
            assert argv[argv.index("--instance-ids") + 1] == "i-0f8f8f8f8f8f8f8f8"
            lines = _ssm_parameters(argv)["commands"]
            body = [line for line in lines if not line.startswith("export PO_")]
            assert any(collector.host_script_text(c.host_script).rstrip("\n").split("\n") == body
                       for c in collector.CHECKS if c.host_script)
        for check in host:
            script = next(c.host_script for c in collector.CHECKS if c.name == check["check"])
            assert check["script_sha256"] == collector.host_script_sha256(script)
            assert check["host_result"] == "expected"
            saved = json.loads((_out(repo) / check["file"]).read_text(encoding="utf-8"))
            assert saved["Status"] == "Success" and "StandardOutputContent" in saved
        assert not any(name.startswith("send") for name in os.listdir(_out(repo)))

    def test_a_pending_invocation_is_polled_until_it_ends(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        answers = iter([_error("InvocationDoesNotExist")(()),
                        RunResult(0, json.dumps({"Status": "InProgress"}), "")])

        def invocation(argv: Sequence[str]) -> RunResult:
            try:
                return next(answers)
            except StopIteration:
                return RunResult(0, json.dumps({"Status": "Success", "StandardOutputContent": "RESULT=expected\n"}), "")

        fake.overrides[("ssm", "get-command-invocation")] = invocation
        sleeps: list[float] = []
        assert _run(repo, fake, sleeps=sleeps) == 0
        assert sleeps == [5.0, 5.0]

    def test_a_failed_invocation_is_an_error(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        fake.overrides[("ssm", "get-command-invocation")] = lambda argv: RunResult(
            0, json.dumps({"Status": "Failed", "StandardOutputContent": ""}), "")
        assert _run(repo, fake) == collector.EXIT_FAILED
        assert _summary(repo)["controls"]["DC-31"]["status"] == "error"

    def test_a_host_check_that_never_ends_times_out_as_an_error(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        fake.overrides[("ssm", "get-command-invocation")] = lambda argv: RunResult(
            0, json.dumps({"Status": "InProgress"}), "")
        sleeps: list[float] = []
        assert _run(repo, fake, "--host-timeout", "10", sleeps=sleeps) == collector.EXIT_FAILED
        assert sleeps.count(5.0) == 2 * 7

    def test_the_launcher_check_uses_the_launchers_keys_and_the_templates_digest(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        assert _run(repo, fake, "--host-bundle-dir", "/opt/fx-bundle", "--host-bundle-python", "/opt/fx-bundle/py") == 0
        argv = next(c for c in fake.calls if c[2] == "send-command"
                    and "dc33-35-launcher-config" in " ".join(_ssm_parameters(c)["commands"]))
        exports = dict(line[len("export "):].split("=", 1) for line in _ssm_parameters(argv)["commands"]
                       if line.startswith("export PO_"))
        assert exports["PO_CONFIG_KEYS"].strip("'").split() == list(host_env.CONFIG_KEYS)
        template = REPO / "deploy" / "aws" / "templates" / "50-secret.yaml"
        expected = env_config_digest.digest(
            env_config_digest.expected_object(template, FIXTURES / "parameters" / "secret.json", "eu-west-9"))
        assert exports["PO_EXPECTED_SHA256"] == expected
        assert exports["PO_SECRET_ID"] == "fx-orch/env-config"
        assert exports["PO_BUNDLE_DIR"] == "/opt/fx-bundle"
        assert _summary(repo)["controls"]["DC-33"]["status"] == "collected"

    def test_without_a_bundle_the_launcher_check_is_not_collected(self, repo: Path) -> None:
        assert _run(repo, FakeAws(FIXTURES)) == 0
        check = next(c for c in _summary(repo)["checks"] if c["check"] == "launcher-config")
        assert check["status"] == "not_collected" and "--host-bundle-dir" in check["reason"]

    def test_the_f7_url_never_reaches_the_evidence_or_the_console(self, repo: Path) -> None:
        url = "https://fx-outside.s3.ap-east-9.amazonaws.com/obj?X-Amz-Signature=fxsignaturevalue"
        f7 = repo / "f7.txt"
        f7.write_text(url + "\n", encoding="utf-8")
        fake = FakeAws(FIXTURES)
        echo: list[str] = []
        assert _run(repo, fake, "--f7-url-file", str(f7), echo=echo) == 0
        for path in _out(repo).iterdir():
            assert "fxsignaturevalue" not in path.read_text(encoding="utf-8"), path.name
            assert "fx-outside" not in path.read_text(encoding="utf-8"), path.name
        assert not any("fxsignaturevalue" in line for line in echo)
        plan: list[str] = []
        shutil.rmtree(_out(repo))
        assert _run(repo, FakeAws(FIXTURES), "--f7-url-file", str(f7), "--plan", echo=plan) == 0
        assert not any("fxsignaturevalue" in line for line in plan)
        assert any("<f7-url>" in line for line in plan)


# ---------------------------------------------------------------------------
# Read-only by construction (point 8) and the scripts (point 16)
# ---------------------------------------------------------------------------


class TestReadOnly:
    def test_every_workstation_command_is_a_read(self, repo: Path) -> None:
        fake = FakeAws(FIXTURES)
        f7 = repo / "f7.txt"
        f7.write_text("https://fx.s3.amazonaws.com/o\n", encoding="utf-8")
        assert _run(repo, fake, "--host-bundle-dir", "/opt/fx", "--f7-url-file", str(f7)) == 0
        for argv in fake.calls:
            operation = argv[2]
            if operation in collector.HOST_TRANSPORT_OPERATIONS:
                assert argv[1] == "ssm"
                continue
            assert operation.startswith(collector.READ_PREFIXES) or operation in collector.READ_EXACT, operation
            assert operation != "get-secret-value"
            assert "--profile" in argv and argv[argv.index("--output") + 1] == "json"
            if argv[1] in collector.GLOBAL_SERVICES:
                assert "--region" not in argv
            else:
                assert argv[argv.index("--region") + 1] == "eu-west-9"

    def test_the_host_scripts_are_read_only_but_for_the_f7_put(self) -> None:
        write_verbs = re.compile(r"\baws\s+[a-z0-9-]+\s+(?!get-|describe-|list-|converse\b)[a-z]+-|"
                                 r"\baws\s+s3\s+(cp|mv|rm|sync)\b|--upload-file|\brm\s+-rf\b")
        for path in HOST_CHECKS.glob("*.sh"):
            text = path.read_text(encoding="utf-8")
            assert not write_verbs.search(text), path.name
            for line in text.splitlines():
                if "-X PUT" in line and path.name != "f7_presigned_put.sh":
                    # The only other PUT asks IMDSv2 for a session token (DC-14).
                    assert "169.254.169.254/latest/api/token" in line, (path.name, line)
            assert "get-secret-value" not in text, path.name

    def test_the_host_scripts_and_the_module_pass_the_secret_scan_and_the_guard(self) -> None:
        assert evidence_secret_scan.scan_folder(HOST_CHECKS) == []
        assert evidence_secret_scan.scan_file(MODULE) == []
        assert evidence_secret_scan.scan_folder(FIXTURES) == []

    def test_every_host_script_ends_with_a_result_and_exit_0(self) -> None:
        scripts = {c.host_script for c in collector.CHECKS if c.host_script}
        assert scripts == {p.name for p in HOST_CHECKS.glob("*.sh")}
        for name in scripts:
            text = collector.host_script_text(name)
            assert "\r" not in text
            assert 'echo "RESULT=' in text, name
            assert text.rstrip().endswith("exit 0"), name

    def test_the_script_digest_ignores_crlf_checkouts(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        name = "dc32_egress_blocked.sh"
        expected = collector.host_script_sha256(name)
        copy = tmp_path / "hc"
        copy.mkdir()
        (copy / name).write_bytes((HOST_CHECKS / name).read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        monkeypatch.setattr(collector, "HOST_CHECKS_DIR", copy)
        assert collector.host_script_sha256(name) == expected

    def test_the_real_inputs_file_is_complete_and_sourced(self) -> None:
        data = json.loads((REPO / "deploy" / "aws" / "collector_inputs.json").read_text(encoding="utf-8"))
        assert set(data["inputs"]) == set(collector.REQUIRED_INPUTS)
        for name, entry in data["inputs"].items():
            assert entry["source"], name
        routed = [p for p in json.loads((REPO / "deploy/aws/parameters/iam.json").read_text(encoding="utf-8"))
                  if p["ParameterKey"] == "RoutedRegions"][0]["ParameterValue"].split(",")
        assert data["inputs"]["negative_region"]["value"] not in routed


def test_old_id_guard_is_clean_over_the_collector() -> None:
    """Criterion 3: the R3 old-ID guard over the collector, its scripts, tests and fixtures."""
    paths = [MODULE, HOST_CHECKS, Path(__file__), FIXTURES, REPO / "deploy" / "aws" / "collector_inputs.json"]
    assert old_id_guard.scan_paths(paths) == []
    for entry in ("tools/collect_evidence_v2.py", "tools/collector_host_checks", "tests/tools/fixtures/collector"):
        assert entry in old_id_guard.DEFAULT_SCOPE


def test_the_real_files_load_and_plan(tmp_path: Path) -> None:
    """The repository's own contract, outputs and parameters load without a refusal (no AWS call)."""
    (tmp_path / "docs" / "infrastructure_security" / "evidence_v2" / "R12b").mkdir(parents=True)
    fake = FakeAws(FIXTURES)
    echo: list[str] = []
    code = collector.main(["--ticket", "R12b", "--step", "03", "--profile", "po-r1", "--plan",
                           "--repo-root", str(tmp_path), "--source-root", str(REPO),
                           "--outputs-root", str(REPO / "docs" / "infrastructure_security" / "evidence_v2")],
                          runner=fake, clock=lambda: FIXED_NOW, echo=echo.append)
    assert code == 0, echo
    assert fake.calls == []
    assert any("not collected: host stack outputs absent" in line for line in echo)


def test_host_outputs_without_a_path_reads_the_contracts_file(repo: Path) -> None:
    fake = FakeAws(FIXTURES)
    args = [a for a in _args(repo, host=False)] + ["--host-outputs"]
    assert collector.main(args, runner=fake, clock=lambda: FIXED_NOW, sleep=lambda s: None, echo=lambda s: None) == 0
    assert _summary(repo)["host_stack"] == "present"
    assert _summary(repo)["inputs_sha256"]["outputs:host"]["path"].endswith("R11/R11_outputs.json")


def test_a_send_command_error_text_is_masked(repo: Path) -> None:
    url = "https://fx-outside.s3.amazonaws.com/o?X-Amz-Signature=fxmaskme"
    f7 = repo / "f7.txt"
    f7.write_text(url, encoding="utf-8")
    fake = FakeAws(FIXTURES)
    fake.overrides[("ssm", "send-command")] = lambda argv: RunResult(
        252, "", f"Parameter validation failed: value: {argv[argv.index('--parameters') + 1]}")
    assert _run(repo, fake, "--f7-url-file", str(f7)) == collector.EXIT_FAILED
    for path in _out(repo).iterdir():
        assert "fxmaskme" not in path.read_text(encoding="utf-8"), path.name
