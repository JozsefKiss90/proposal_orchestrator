"""AN12 — the offline bundle that carries the pipeline to the private host.

Acceptance, from ``.scratch/msca-dn-anonymisation/tickets.md`` AN12:

1. The updated bundle installs on the private host without an internet route.

The install itself is the operator's act on the host. What is tested here is
everything the install depends on that can be decided before the bundle
leaves: the wheel set matches the hash-pinned requirements both ways and runs
on the host's interpreter and glibc, the bundle carries the committed bytes
and nothing else, the build is byte-reproducible, and the host verification
refuses each way the installed tree can be wrong.

Builds run in a throwaway git repository with fake wheels and a fake
interpreter archive. No test reaches a network.
"""

from __future__ import annotations

import hashlib
import os
import socket
import io
import json
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any

import pytest

from runner import extraction_environment as ee
from runner import offline_bundle as ob

REPO = Path(__file__).resolve().parents[2]


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
# Requirements
# --------------------------------------------------------------------------- #


H = "a" * 64


class TestRequirements:
    def test_a_pinned_hashed_line_parses(self):
        (req,) = ob.parse_requirements(f"# a comment\nPyYAML==6.0.2 --hash=sha256:{H}\n")
        assert (req.name, req.version, req.sha256) == ("pyyaml", "6.0.2", H)

    @pytest.mark.parametrize("line", [
        f"pyyaml>=6.0 --hash=sha256:{H}",
        "pyyaml==6.0.2",
        f"pyyaml==6.0.2 --hash=md5:{H[:32]}",
        f"pyyaml==6.0.2 --hash=sha256:{H} ; python_version < '3.10'",
        "-r other.txt",
    ])
    def test_anything_but_an_exact_pin_with_one_sha256_is_refused(self, line):
        with pytest.raises(ob.BundleRefused):
            ob.parse_requirements(line)

    def test_a_project_named_twice_is_refused(self):
        with pytest.raises(ob.BundleRefused, match="twice"):
            ob.parse_requirements(f"six==1.17.0 --hash=sha256:{H}\nSix==1.17.0 --hash=sha256:{H}")


# --------------------------------------------------------------------------- #
# Wheels against the target
# --------------------------------------------------------------------------- #


TARGET = ob.Target(python_tag="cp311", machine="x86_64", glibc="2.34")


class TestWheelCompatibility:
    @pytest.mark.parametrize("name", [
        "six-1.17.0-py2.py3-none-any.whl",
        "PyYAML-6.0.2-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
        "pymupdf-1.28.2-cp310-abi3-manylinux_2_28_x86_64.whl",
        "rpds_py-0.22.3-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
    ])
    def test_a_wheel_the_host_can_run_has_no_problem(self, name):
        assert ob.wheel_problem(ob.parse_wheel(name), TARGET) is None

    @pytest.mark.parametrize("name, why", [
        ("x-1.0-cp312-abi3-manylinux_2_28_x86_64.whl", "interpreter"),
        ("x-1.0-cp39-cp39-manylinux2014_x86_64.whl", "interpreter"),
        ("x-1.0-cp311-cp311-manylinux_2_35_x86_64.whl", "glibc"),
        ("x-1.0-cp311-cp311-manylinux2014_aarch64.whl", "platform"),
        ("x-1.0-cp311-cp311-win_amd64.whl", "platform"),
        ("x-1.0-cp311-cp311-musllinux_1_2_x86_64.whl", "platform"),
    ])
    def test_a_wheel_the_host_cannot_run_is_named(self, name, why):
        problem = ob.wheel_problem(ob.parse_wheel(name), TARGET)
        assert problem is not None and why in problem

    def test_a_cp39_abi3_wheel_runs_on_311_by_tag(self):
        """abi3 from 3.9 upward runs on 3.11: the tag rule itself, not a pin choice."""
        assert ob.wheel_problem(ob.parse_wheel("x-1.0-cp39-abi3-manylinux_2_28_x86_64.whl"),
                                TARGET) is None

    def test_a_malformed_name_is_refused(self):
        with pytest.raises(ob.BundleRefused):
            ob.parse_wheel("not-a-wheel.tar.gz")

    def test_the_glibc_a_wheel_needs(self):
        assert ob.parse_wheel("six-1.17.0-py3-none-any.whl").glibc_needed(TARGET) is None
        assert ob.parse_wheel("x-1-cp311-cp311-manylinux2014_x86_64.whl").glibc_needed(TARGET) == (2, 17)
        assert ob.parse_wheel("x-1-cp310-abi3-manylinux_2_28_x86_64.whl").glibc_needed(TARGET) == (2, 28)


def _wheel_dir(tmp: Path, names: dict[str, bytes]) -> Path:
    d = tmp / "wheels"
    d.mkdir(parents=True, exist_ok=True)
    for name, data in names.items():
        (d / name).write_bytes(data)
    return d


WHEELS = {
    "six-1.17.0-py2.py3-none-any.whl": b"six wheel",
    f"pymupdf-{ee.PINNED_PYMUPDF}-cp310-abi3-manylinux_2_28_x86_64.whl": b"pymupdf wheel",
}


def _requirements_for(wheels: dict[str, bytes]) -> str:
    lines = []
    for name, data in wheels.items():
        project, version = name.split("-")[:2]
        lines.append(f"{project}=={version} --hash=sha256:{_sha(data)}")
    return "\n".join(lines) + "\n"


class TestTheWheelSet:
    def test_a_matching_set_is_accepted_with_its_hashes(self, tmp_path):
        reqs = ob.parse_requirements(_requirements_for(WHEELS))
        records = ob.check_wheels(reqs, _wheel_dir(tmp_path, WHEELS), TARGET)
        assert {r["file"]: r["sha256"] for r in records} == {n: _sha(d) for n, d in WHEELS.items()}

    def test_a_missing_wheel_is_refused(self, tmp_path):
        reqs = ob.parse_requirements(_requirements_for(WHEELS))
        only = dict(list(WHEELS.items())[:1])
        with pytest.raises(ob.BundleRefused, match="no wheel"):
            ob.check_wheels(reqs, _wheel_dir(tmp_path, only), TARGET)

    def test_an_extra_wheel_is_refused(self, tmp_path):
        reqs = ob.parse_requirements(_requirements_for(WHEELS))
        extra = {**WHEELS, "attrs-24.3.0-py3-none-any.whl": b"attrs"}
        with pytest.raises(ob.BundleRefused, match="not pinned"):
            ob.check_wheels(reqs, _wheel_dir(tmp_path, extra), TARGET)

    def test_an_altered_wheel_is_refused(self, tmp_path):
        reqs = ob.parse_requirements(_requirements_for(WHEELS))
        altered = {name: data + b"!" for name, data in WHEELS.items()}
        with pytest.raises(ob.BundleRefused, match="hash"):
            ob.check_wheels(reqs, _wheel_dir(tmp_path, altered), TARGET)

    def test_a_wheel_the_host_cannot_run_is_refused(self, tmp_path):
        wheels = {"six-1.17.0-cp311-cp311-win_amd64.whl": b"six"}
        reqs = ob.parse_requirements(_requirements_for(wheels))
        with pytest.raises(ob.BundleRefused, match="platform"):
            ob.check_wheels(reqs, _wheel_dir(tmp_path, wheels), TARGET)

    def test_every_problem_is_named_at_once(self, tmp_path):
        reqs = ob.parse_requirements(_requirements_for(WHEELS))
        altered = {name: data + b"!" for name, data in WHEELS.items()}
        with pytest.raises(ob.BundleRefused) as caught:
            ob.check_wheels(reqs, _wheel_dir(tmp_path, altered), TARGET)
        assert all(name in str(caught.value) for name in WHEELS)


# --------------------------------------------------------------------------- #
# The build
# --------------------------------------------------------------------------- #


INTERPRETER = b"a fake interpreter archive"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True).stdout


def _spec(**changes: Any) -> dict[str, Any]:
    spec = {
        "schema": ob.SPEC_SCHEMA,
        "record_type": "offline_bundle_spec",
        "bundle_name": "test-bundle",
        "purpose": "a test",
        "interpreter": {
            "distribution": "python-build-standalone",
            "python_version": "3.11.16",
            "release": "20260929",
            "archive": "cpython-test.tar.gz",
            "url": "https://example.org/cpython-test.tar.gz",
            "sha256": _sha(INTERPRETER),
            "sha256_source": "a test",
            "why": "a test",
        },
        "target": {"python_tag": "cp311", "machine": "x86_64", "glibc": "2.34",
                   "glibc_status": "Assumed", "glibc_basis": "a test"},
        "requirements": "deploy/requirements-host.txt",
        "roots": ["CLAUDE.md", "deploy", "runner"],
    }
    spec.update(changes)
    return spec


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    (root / "runner").mkdir(parents=True)
    (root / "deploy").mkdir()
    (root / "elsewhere").mkdir()
    (root / "CLAUDE.md").write_bytes(b"constitution\n")
    (root / "runner" / "a.py").write_bytes(b"print('a')\n")
    (root / "runner" / "data.json").write_bytes(b'{"k": 1}\n')
    (root / "elsewhere" / "private.txt").write_bytes(b"never bundled\n")
    (root / "deploy" / "requirements-host.txt").write_text(_requirements_for(WHEELS),
                                                            encoding="utf-8", newline="\n")
    (root / "deploy" / "offline_bundle.json").write_text(json.dumps(_spec()), encoding="utf-8",
                                                          newline="\n")
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.org")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "core.autocrlf", "false")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


@pytest.fixture
def inputs(tmp_path: Path) -> dict[str, Path]:
    interpreter = tmp_path / "inputs" / "cpython-test.tar.gz"
    interpreter.parent.mkdir()
    interpreter.write_bytes(INTERPRETER)
    return {"wheels": _wheel_dir(tmp_path / "inputs", WHEELS), "interpreter": interpreter}


def _build(repo: Path, inputs: dict[str, Path], out: Path, spec: str = "deploy/offline_bundle.json"):
    return ob.build(repo_root=repo, spec_path=repo / spec, wheel_dir=inputs["wheels"],
                    interpreter=inputs["interpreter"], out_dir=out)


def _members(tarball: Path) -> dict[str, tarfile.TarInfo]:
    with tarfile.open(tarball, "r:gz") as tar:
        return {m.name: m for m in tar.getmembers()}


def _read_member(tarball: Path, name: str) -> bytes:
    with tarfile.open(tarball, "r:gz") as tar:
        return tar.extractfile(name).read()


class TestTheBuild:
    def test_the_bundle_carries_the_roots_the_wheels_and_the_interpreter(self, repo, inputs, tmp_path):
        result = _build(repo, inputs, tmp_path / "out")
        names = set(_members(result.tarball))
        top = "test-bundle"
        assert {f"{top}/app/CLAUDE.md", f"{top}/app/runner/a.py", f"{top}/app/runner/data.json",
                f"{top}/app/deploy/requirements-host.txt", f"{top}/app/bundle_manifest.json",
                f"{top}/app/.git", f"{top}/python/cpython-test.tar.gz",
                f"{top}/SHA256SUMS"} <= names
        assert {f"{top}/wheels/{n}" for n in WHEELS} <= names
        assert not any("elsewhere" in n for n in names)

    def test_the_bundle_carries_the_committed_bytes_not_the_working_tree(self, repo, inputs, tmp_path):
        (repo / "runner" / "a.py").write_bytes(b"print('edited, never committed')\r\n")
        (repo / "runner" / "untracked.py").write_bytes(b"x = 1\n")
        result = _build(repo, inputs, tmp_path / "out")
        assert _read_member(result.tarball, "test-bundle/app/runner/a.py") == b"print('a')\n"
        assert "test-bundle/app/runner/untracked.py" not in _members(result.tarball)

    def test_the_manifest_binds_every_file_wheel_and_the_revision(self, repo, inputs, tmp_path):
        result = _build(repo, inputs, tmp_path / "out")
        manifest = json.loads(_read_member(result.tarball, "test-bundle/app/bundle_manifest.json"))
        assert manifest == result.manifest
        assert manifest["schema"] == ob.MANIFEST_SCHEMA
        assert manifest["repository_revision"] == _git(repo, "rev-parse", "HEAD").strip()
        files = {f["path"]: f["sha256"] for f in manifest["files"]}
        assert files["runner/a.py"] == _sha(b"print('a')\n")
        assert {w["file"] for w in manifest["wheels"]} == set(WHEELS)
        assert manifest["interpreter"]["sha256"] == _sha(INTERPRETER)
        assert manifest["glibc_required"] == "2.28"
        assert manifest["extraction_pin"] == {"pymupdf": ee.PINNED_PYMUPDF, "mupdf": ee.PINNED_MUPDF}

    def test_the_checksum_file_covers_the_interpreter_and_every_wheel(self, repo, inputs, tmp_path):
        result = _build(repo, inputs, tmp_path / "out")
        sums = _read_member(result.tarball, "test-bundle/SHA256SUMS").decode()
        lines = dict(reversed(line.split("  ", 1)) for line in sums.splitlines())
        assert lines["python/cpython-test.tar.gz"] == _sha(INTERPRETER)
        for name, data in WHEELS.items():
            assert lines[f"wheels/{name}"] == _sha(data)

    def test_two_builds_are_byte_equal(self, repo, inputs, tmp_path):
        a = _build(repo, inputs, tmp_path / "a")
        b = _build(repo, inputs, tmp_path / "b")
        assert a.tarball.read_bytes() == b.tarball.read_bytes()
        assert a.tarball_sha256 == b.tarball_sha256 == _sha(a.tarball.read_bytes())
        assert (a.tarball.parent / (a.tarball.name + ".sha256")).read_text().startswith(a.tarball_sha256)

    def test_an_interpreter_that_is_not_the_pinned_one_is_refused(self, repo, inputs, tmp_path):
        inputs["interpreter"].write_bytes(b"another interpreter")
        with pytest.raises(ob.BundleRefused, match="interpreter"):
            _build(repo, inputs, tmp_path / "out")

    def test_a_root_that_matches_no_committed_file_is_refused(self, repo, inputs, tmp_path):
        spec = _spec(roots=["CLAUDE.md", "deploy", "runner", "tools/missing.py"])
        (repo / "deploy" / "offline_bundle.json").write_text(json.dumps(spec), encoding="utf-8")
        _git(repo, "commit", "-qam", "spec")
        with pytest.raises(ob.BundleRefused, match="tools/missing.py"):
            _build(repo, inputs, tmp_path / "out")

    def test_a_spec_that_does_not_bundle_its_own_requirements_is_refused(self, repo, inputs, tmp_path):
        spec = _spec(roots=["CLAUDE.md", "runner"])
        (repo / "deploy" / "offline_bundle.json").write_text(json.dumps(spec), encoding="utf-8")
        _git(repo, "commit", "-qam", "spec")
        with pytest.raises(ob.BundleRefused, match="requirements"):
            _build(repo, inputs, tmp_path / "out")

    def test_requirements_that_drop_the_extraction_pin_are_refused(self, repo, inputs, tmp_path):
        wheels = {"six-1.17.0-py2.py3-none-any.whl": b"six wheel",
                  "pymupdf-1.26.5-cp39-abi3-manylinux_2_28_x86_64.whl": b"old"}
        (repo / "deploy" / "requirements-host.txt").write_text(_requirements_for(wheels),
                                                                encoding="utf-8")
        _git(repo, "commit", "-qam", "reqs")
        inputs["wheels"] = _wheel_dir(tmp_path / "other", wheels)
        with pytest.raises(ob.BundleRefused, match="extraction pin"):
            _build(repo, inputs, tmp_path / "out")

    def test_an_interpreter_outside_the_measured_versions_is_refused(self, repo, inputs, tmp_path):
        spec = _spec()
        spec["interpreter"]["python_version"] = "3.12.9"
        spec["target"]["python_tag"] = "cp312"
        (repo / "deploy" / "offline_bundle.json").write_text(json.dumps(spec), encoding="utf-8")
        _git(repo, "commit", "-qam", "spec")
        with pytest.raises(ob.BundleRefused, match="measured"):
            _build(repo, inputs, tmp_path / "out")

    def test_an_output_directory_inside_the_repository_is_refused(self, repo, inputs):
        with pytest.raises(ob.BundleRefused, match="inside"):
            _build(repo, inputs, repo / "out")

    def test_a_spec_outside_the_repository_is_refused(self, repo, inputs, tmp_path):
        outside = tmp_path / "offline_bundle.json"
        outside.write_text(json.dumps(_spec()), encoding="utf-8")
        with pytest.raises(ob.BundleRefused, match="not inside"):
            ob.build(repo_root=repo, spec_path=outside, wheel_dir=inputs["wheels"],
                     interpreter=inputs["interpreter"], out_dir=tmp_path / "out")

    def test_the_spec_is_read_from_the_commit(self, repo, inputs, tmp_path):
        """An uncommitted spec edit does not reach the bundle or its manifest."""
        (repo / "deploy" / "offline_bundle.json").write_text(
            json.dumps(_spec(roots=["CLAUDE.md"])), encoding="utf-8")
        result = _build(repo, inputs, tmp_path / "out")
        assert "test-bundle/app/runner/a.py" in _members(result.tarball)


# --------------------------------------------------------------------------- #
# The host verification
# --------------------------------------------------------------------------- #


def _facts(**changes: Any) -> ob.HostFacts:
    values = {
        "python_version": "3.11.16",
        "machine": "x86_64",
        "libc": ("glibc", "2.34"),
        "extraction": ee.Environment(pymupdf=ee.PINNED_PYMUPDF, mupdf=ee.PINNED_MUPDF,
                                     python="3.11.16"),
        "distributions": {"six": "1.17.0", "pymupdf": ee.PINNED_PYMUPDF},
    }
    values.update(changes)
    return ob.HostFacts(**values)


HOST_ENV = {
    "ORCHESTRATOR_PRODUCTION_MODE": "true",
    "ORCHESTRATOR_DIAGNOSTIC_LEVEL": "metadata",
    "ORCHESTRATOR_TRANSPORT_BACKEND": "bedrock_converse",
    "ORCHESTRATOR_TRANSPORT_MODEL": "eu.anthropic.claude-sonnet-4-6",
    "AWS_REGION": "eu-west-1",
}


def _refused(host: str, port: int, timeout: float):
    raise OSError("no route to host")


def _unresolved(host: str, port: int, timeout: float):
    raise socket.gaierror(-2, "Name or service not known")


def _resolves_to(*addresses: str):
    def resolve(host: str) -> list[str]:
        if not addresses:
            raise socket.gaierror(-2, "Name or service not known")
        return list(addresses)
    return resolve


@pytest.fixture(autouse=True)
def _private_dns(monkeypatch):
    """Bedrock resolves to the VPC endpoint unless a test says otherwise; no test resolves."""
    monkeypatch.setattr(ob, "_resolve", _resolves_to("172.31.27.207", "172.31.80.15"))


@pytest.fixture
def installed(repo, inputs, tmp_path) -> Path:
    result = _build(repo, inputs, tmp_path / "out")
    with tarfile.open(result.tarball, "r:gz") as tar:
        tar.extractall(tmp_path / "host")
    return tmp_path / "host" / "test-bundle" / "app"


def _failed(record: dict[str, Any]) -> set[str]:
    return {c["check"] for c in record["checks"] if c["passed"] is False}


class TestTheHostVerification:
    def test_a_correct_install_passes_every_check(self, installed):
        record = ob.verify(installed, environ=HOST_ENV, facts=_facts(),
                           probe=("pypi.org", 443), connect=_refused)
        assert record["schema"] == ob.VERIFICATION_SCHEMA
        assert record["passed"], record["checks"]
        assert _failed(record) == set()
        assert {c["check"] for c in record["checks"]} == set(ob.CHECKS)

    def test_the_launchers_environment_passes_every_check(self, installed):
        """R9e: the five values the runtime secret stores, as the launcher
        exports them (with AWS_DEFAULT_REGION), satisfy every environment check:
        the preset BEDROCK_CONVERSE_EU resolves to the host backend and the
        secret's Region is in ALLOWED_REGIONS (decision record
        aws-redeployment-r9e-eu-region_2026-10-27)."""
        from tools import env_config_digest

        repo = Path(__file__).resolve().parents[2]
        parameters = repo / "deploy" / "aws" / "parameters" / "secret.json"
        region = {e["ParameterKey"]: e["ParameterValue"] for e in
                  json.loads(parameters.read_text(encoding="utf-8-sig"))}["ExpectedRegion"]
        secret = env_config_digest.expected_object(
            repo / "deploy" / "aws" / "templates" / "50-secret.yaml", parameters, region)
        environ = {**secret, "AWS_DEFAULT_REGION": secret["AWS_REGION"]}
        record = ob.verify(installed, environ=environ, facts=_facts(),
                           probe=("pypi.org", 443), connect=_refused)
        assert record["passed"], record["checks"]
        endpoint = next(c for c in record["checks"] if c["check"] == "private_endpoint")
        assert f"bedrock-runtime.{region}.amazonaws.com" in endpoint["detail"]

    def test_the_record_binds_the_manifest(self, installed):
        record = ob.verify(installed, environ=HOST_ENV, facts=_facts())
        manifest = (installed / ob.MANIFEST_FILE).read_bytes()
        assert record["manifest_sha256"] == _sha(manifest)
        assert record["repository_revision"] == json.loads(manifest)["repository_revision"]

    def test_an_altered_or_missing_file_fails(self, installed):
        (installed / "runner" / "a.py").write_bytes(b"tampered\n")
        (installed / "runner" / "data.json").unlink()
        record = ob.verify(installed, environ=HOST_ENV, facts=_facts())
        assert _failed(record) == {"files"}
        detail = next(c for c in record["checks"] if c["check"] == "files")["detail"]
        assert "runner/a.py" in detail and "runner/data.json" in detail

    @pytest.mark.parametrize("facts, check", [
        (dict(python_version="3.9.25"), "interpreter"),
        (dict(machine="aarch64"), "interpreter"),
        (dict(libc=("glibc", "2.26")), "glibc"),
        (dict(libc=("", "")), "glibc"),
        (dict(extraction=ee.Environment(pymupdf="1.26.5", mupdf="1.26.11", python="3.11.16")),
         "extraction_pin"),
        (dict(extraction=None), "extraction_pin"),
        (dict(distributions={"six": "1.16.0", "pymupdf": ee.PINNED_PYMUPDF}), "distributions"),
        (dict(distributions={"pymupdf": ee.PINNED_PYMUPDF}), "distributions"),
    ])
    def test_a_wrong_host_fact_fails_its_check(self, installed, facts, check):
        record = ob.verify(installed, environ=HOST_ENV, facts=_facts(**facts))
        assert _failed(record) == {check}
        assert not record["passed"]

    @pytest.mark.parametrize("change, check", [
        ({"ORCHESTRATOR_PRODUCTION_MODE": "false"}, "production_mode"),
        ({"ORCHESTRATOR_DIAGNOSTIC_LEVEL": "full"}, "diagnostic_level"),
        ({"ORCHESTRATOR_TRANSPORT_BACKEND": "openai_compatible"}, "transport"),
        ({"AWS_REGION": "eu-central-1"}, "region"),
    ])
    def test_a_wrong_environment_fails_its_check(self, installed, change, check):
        record = ob.verify(installed, environ={**HOST_ENV, **change}, facts=_facts())
        assert check in _failed(record)

    def test_a_reachable_internet_endpoint_fails(self, installed):
        record = ob.verify(installed, environ=HOST_ENV, facts=_facts(), probe=("pypi.org", 443),
                           connect=lambda host, port, timeout: io.BytesIO())
        assert _failed(record) == {"no_internet_route"}

    def test_without_a_probe_the_route_is_not_claimed(self, installed):
        record = ob.verify(installed, environ=HOST_ENV, facts=_facts())
        check = next(c for c in record["checks"] if c["check"] == "no_internet_route")
        assert check["passed"] is None
        assert record["passed"] is False, "an unprobed route is not a pass"

    def test_a_name_that_does_not_resolve_leaves_the_route_unmeasured(self, installed):
        record = ob.verify(installed, environ=HOST_ENV, facts=_facts(), probe=("pypi.org", 443),
                           connect=_unresolved)
        check = next(c for c in record["checks"] if c["check"] == "no_internet_route")
        assert check["passed"] is None
        assert "did not resolve" in check["detail"] and "IP address" in check["detail"]
        assert record["passed"] is False

    def test_an_ip_literal_that_times_out_passes(self, installed):
        def timed_out(host, port, timeout):
            raise socket.timeout("timed out")
        record = ob.verify(installed, environ=HOST_ENV, facts=_facts(), probe=("1.1.1.1", 443),
                           connect=timed_out)
        check = next(c for c in record["checks"] if c["check"] == "no_internet_route")
        assert check["passed"] is True
        assert "timed out" in check["detail"]

    def test_bedrock_resolving_to_the_vpc_endpoint_passes(self, installed):
        record = ob.verify(installed, environ=HOST_ENV, facts=_facts(), probe=("pypi.org", 443),
                           connect=_refused)
        check = next(c for c in record["checks"] if c["check"] == "private_endpoint")
        assert check["passed"] is True
        assert "bedrock-runtime.eu-west-1.amazonaws.com" in check["detail"]
        assert "172.31.27.207" in check["detail"]

    @pytest.mark.parametrize("addresses", [
        ("52.94.4.10",),
        ("172.31.27.207", "52.94.4.10"),
        (),
    ])
    def test_bedrock_resolving_anywhere_else_fails(self, installed, monkeypatch, addresses):
        monkeypatch.setattr(ob, "_resolve", _resolves_to(*addresses))
        record = ob.verify(installed, environ=HOST_ENV, facts=_facts(), probe=("pypi.org", 443),
                           connect=_refused)
        assert _failed(record) == {"private_endpoint"}

    def test_without_an_adr_001_region_the_endpoint_is_not_resolved(self, installed, monkeypatch):
        def never(host):
            raise AssertionError("resolved without a region")
        monkeypatch.setattr(ob, "_resolve", never)
        env = {k: v for k, v in HOST_ENV.items() if k != "AWS_REGION"}
        record = ob.verify(installed, environ=env, facts=_facts())
        assert {"region", "private_endpoint"} <= _failed(record)

    def test_aws_default_region_alone_does_not_satisfy_the_region_check(self, installed, monkeypatch):
        """R9 (F4): the Converse backend reads AWS_REGION, so verify requires it too."""
        monkeypatch.setattr(ob, "_resolve", lambda host: ["10.0.0.10"])
        env = {k: v for k, v in HOST_ENV.items() if k != "AWS_REGION"}
        env["AWS_DEFAULT_REGION"] = HOST_ENV["AWS_REGION"]
        record = ob.verify(installed, environ=env, facts=_facts())
        assert {"region", "private_endpoint"} <= _failed(record)
        region = next(c for c in record["checks"] if c["check"] == "region")
        assert "AWS_DEFAULT_REGION alone does not count" in region["detail"]

    def test_the_record_holds_no_environment_value_but_the_ones_it_checks(self, installed):
        env = {**HOST_ENV, "AWS_SECRET_ACCESS_KEY": "s3cr3t", "SOME_TOKEN": "t0k3n"}
        record = ob.verify(installed, environ=env, facts=_facts(), probe=("pypi.org", 443),
                           connect=_refused)
        text = json.dumps(record)
        assert "s3cr3t" not in text and "t0k3n" not in text


# --------------------------------------------------------------------------- #
# The committed spec
# --------------------------------------------------------------------------- #


class TestTheCommittedSpec:
    @pytest.fixture(scope="class")
    def spec(self) -> ob.Spec:
        return ob.load_spec((REPO / ob.SPEC_REL).read_bytes())

    def test_it_pins_a_measured_interpreter(self, spec):
        minor = ".".join(spec.interpreter["python_version"].split(".")[:2])
        assert minor in ee.MEASURED_PYTHON
        assert spec.target.python_tag == "cp" + minor.replace(".", "")

    def test_its_requirements_pin_the_extraction_library(self, spec):
        reqs = ob.parse_requirements((REPO / spec.requirements).read_text(encoding="utf-8"))
        assert {r.name: r.version for r in reqs}["pymupdf"] == ee.PINNED_PYMUPDF

    def test_its_requirements_carry_what_the_pipeline_imports(self, spec):
        reqs = {r.name for r in ob.parse_requirements(
            (REPO / spec.requirements).read_text(encoding="utf-8"))}
        assert {"boto3", "botocore", "pyyaml", "jsonschema", "python-dotenv", "pymupdf"} <= reqs

    def test_every_root_exists(self, spec):
        missing = [root for root in spec.roots if not (REPO / root).exists()]
        assert missing == []

    def test_it_bundles_its_own_requirements_and_the_host_install(self, spec):
        assert ob.covered(spec.requirements, spec.roots)
        assert ob.covered("deploy/install_host.sh", spec.roots)


# --------------------------------------------------------------------------- #
# The bundle is self-sufficient
# --------------------------------------------------------------------------- #


#: Runs in a fresh interpreter whose only source tree is the copied bundle: both
#: host smokes, against fakes, to their first operator step.
_SELF_SUFFICIENCY = r'''
import json, os, sys
from pathlib import Path
app, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
sys.path.insert(0, str(app))
import runner, harness, tests
import tools.anonymisation_host_smoke as smoke
from harness.commands import converse_smoke as cs
for module in (runner, harness, tests, smoke, cs):
    assert Path(module.__file__).resolve().is_relative_to(app), module.__file__

USAGE = {"prompt_tokens": 900, "completion_tokens": 100, "total_tokens": 1000}
class Fake:
    def __init__(self, respond, model):
        self.model, self.last_usage, self.respond = model, None, respond
    def __call__(self, messages):
        self.last_usage = dict(USAGE)
        return {"content": json.dumps(self.respond(messages)), "tool_calls": None}
def wrong(messages):
    passage = json.loads(messages[-1]["content"])["passages"][0]
    return {"guesses": [{"target": "supervisor", "guess": None, "confidence": None,
                         "passage_id": None, "evidence": None}]}
a3, a5 = "eu.anthropic.claude-test-a3-v1:0", "eu.anthropic.claude-test-a5-v1:0"
result = smoke.run(out / "pipeline", a3_backend=Fake(lambda m: {"edits": [], "new_entities": []}, a3),
                   a5_backend=Fake(wrong, a5), a3_model=a3, a5_model=a5, max_output_tokens=1000,
                   a3_token_budget=10**6, a5_token_budget=10**6, pipeline_revision="0" * 40)
assert result.outcome == "awaiting_operator", result.status.read_text()

PASS = '{"passed": true, "score": 0.9, "rationale": "scripted pass"}'
CRITERION = json.dumps({"score": 4.0, "shortcomings": ["one"], "strengths": ["s"],
                        "rationale": "scripted criterion score"})
class Client:
    def converse(self, **kw):
        system = "".join(b["text"] for b in kw.get("system", []))
        text = CRITERION if "CRITERION UNDER ASSESSMENT" in system else PASS
        return {"output": {"message": {"role": "assistant", "content": [{"text": text}]}},
                "usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15}}
import runner.transport.bedrock_converse as bc
bc.boto3.client = lambda service, **kw: Client()
import harness.commands._common as common
common.load_harness_env = lambda: None
os.environ.pop("ORCHESTRATOR_TRANSPORT_PRESET", None)
os.environ.pop("ORCHESTRATOR_PRODUCTION_MODE", None)
os.environ.update(ORCHESTRATOR_TRANSPORT_BACKEND="bedrock_converse",
                  ORCHESTRATOR_TRANSPORT_MODEL="env-default-model", AWS_REGION="eu-west-1")
code = cs.main(["prepare", "--root", str(out / "converse"), "--assessor-model",
                "eu.anthropic.claude-sonnet-4-6", "--assessor-version",
                "bedrock-converse-eu-west-1@2026-10-16"])
assert code == 0, code
print("SELF_SUFFICIENT")
'''


class TestTheBundleIsSelfSufficient:
    def test_both_host_smokes_run_from_the_bundled_roots_alone(self, tmp_path):
        """The spec's roots, copied without the rest of the repository, carry
        everything both smokes import and read. Run in a fresh interpreter, so
        a module or data file missing from the roots fails here, not on the host."""
        spec = ob.load_spec((REPO / ob.SPEC_REL).read_bytes())
        listing = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "-z", "--cached", "--others",
             "--exclude-standard", "--", *spec.roots],
            check=True, capture_output=True).stdout
        app = tmp_path / "app"
        for rel in filter(None, listing.decode("utf-8").split("\0")):
            source = REPO / rel
            if source.is_file():
                (app / rel).parent.mkdir(parents=True, exist_ok=True)
                (app / rel).write_bytes(source.read_bytes())
        (app / ".git").mkdir()
        script = tmp_path / "self_sufficiency.py"
        script.write_text(_SELF_SUFFICIENCY, encoding="utf-8")
        env = {k: v for k, v in os.environ.items() if not k.startswith(("ORCHESTRATOR_", "PYTHON"))}
        done = subprocess.run([sys.executable, "-I", str(script), str(app), str(tmp_path / "out")],
                              cwd=tmp_path, env=env, capture_output=True, text=True, timeout=600)
        assert done.returncode == 0 and "SELF_SUFFICIENT" in done.stdout, \
            done.stdout[-3000:] + done.stderr[-3000:]
