"""The R15 Run Command sender and the host scripts it sends.

``deploy/aws/scripts/host-run.ps1`` sends one fixed shell script to the host by ``AWS-RunShellScript`` and
waits for it. These tests pin the decisions of ``docs/infrastructure_security/evidence_v2/R15/STEPS.md``:
one ``send-command`` with the export lines first, the timeout passed, the parameters file removed, the
truncation flag set, and nothing sent when an input is refused. The host scripts under
``evidence_v2/R15/host`` are checked statically, and the receipt filler of step 12 runs against a real
draft made by ``harness.commands.converse_smoke prepare``.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import pytest

from harness.commands import converse_smoke as cs
from tests.harness.test_converse_smoke import _prepare
from tests.harness.test_converse_judge import client, converse_env  # noqa: F401
from tests.test_aws_host_lifecycle_scripts import BASH, POWERSHELL, _shims, ok

REPO = Path(__file__).resolve().parents[1]
SENDER = REPO / "deploy" / "aws" / "scripts" / "host-run.ps1"
V2 = REPO / "docs" / "infrastructure_security" / "evidence_v2"
HOST = V2 / "R15" / "host"
SCRIPTS = ["r15_07_fetch.sh", "r15_08_install.sh", "r15_09_verify.sh", "r15_11_prepare.sh",
           "r15_12_receipt.sh", "r15_13_assess.sh"]
DC33 = REPO / "tools" / "collector_host_checks" / "dc33_35_launcher_config.sh"
COMMAND_ID = "0b1c2d3e-4f50-6172-8394-a5b6c7d8e9f0"
OPERATOR_FIELDS = {
    "authored_on", "review_state", "declared_status", "purpose", "written_by",
    "processing_route.authority", "processing_route.processing", "processing_route.export",
    "processing_route.verified_on", "processing_route.verified_by",
    "isolation_check.evidence[0]", "isolation_check.verified_on", "isolation_check.verified_by",
}


def _outputs(path: Path, instance: Optional[str] = "i-0123456789abcdef0") -> Path:
    rows = [{"OutputKey": "VpcId", "OutputValue": "vpc-0abc"}]
    if instance:
        rows.append({"OutputKey": "InstanceId", "OutputValue": instance})
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path


def _invocation(status: str = "Success", stdout: str = "CHECK=x\nRESULT=expected\n", stderr: str = "") -> dict[str, Any]:
    return {"Status": status, "StatusDetails": status, "ResponseCode": 0 if status == "Success" else 1,
            "ExecutionStartDateTime": "2026-11-12T10:00:00Z", "ExecutionEndDateTime": "2026-11-12T10:01:00Z",
            "StandardOutputContent": stdout, "StandardErrorContent": stderr}


def scenario(**over: Any) -> dict[str, Any]:
    s = {
        "ssm send-command": [ok(COMMAND_ID)],
        "ssm get-command-invocation|Status": [ok("InProgress"), ok("Success")],
        "ssm get-command-invocation": [ok(_invocation())],
    }
    s.update(over)
    return s


class Sent:
    def __init__(self, tmp: Path, result: subprocess.CompletedProcess[str], out: Path) -> None:
        self.rc = result.returncode
        self.console = result.stdout + result.stderr
        self.out = out
        log = tmp / "fake.log"
        self.calls = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []

    def record(self) -> dict[str, Any]:
        return json.loads(self.out.read_text(encoding="utf-8-sig"))

    def sends(self) -> list[dict[str, Any]]:
        return [c for c in self.calls if c["argv"][:2] == ["ssm", "send-command"]]


def send(tmp: Path, scen: dict[str, Any], script_text: str = "echo CHECK=x\necho RESULT=expected\n",
         vars_obj: Optional[Any] = None, timeout: int = 900, instance: Optional[str] = "i-0123456789abcdef0",
         script_bytes: Optional[bytes] = None) -> Sent:
    if not POWERSHELL:
        pytest.skip("no PowerShell")
    script = tmp / "probe.sh"
    script.write_bytes(script_bytes if script_bytes is not None else script_text.encode("utf-8"))
    (tmp / "scenario.json").write_text(json.dumps(scen), encoding="utf-8")
    shims = tmp / "shims" if (tmp / "shims").exists() else _shims(tmp)
    env = dict(__import__("os").environ)
    env.update({"FAKE_AWS_SCENARIO": str(tmp / "scenario.json"), "FAKE_AWS_LOG": str(tmp / "fake.log"),
                "PO_POLL_SECONDS": "0", "PATH": str(shims) + ";" + env.get("PATH", "")})
    out = tmp / "result.json"
    argv = [POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(SENDER),
            "-AwsProfile", "po-r1", "-Outputs", str(_outputs(tmp / "outputs.json", instance)),
            "-Script", str(script), "-TimeoutSeconds", str(timeout), "-Out", str(out)]
    if vars_obj is not None:
        (tmp / "vars.json").write_text(json.dumps(vars_obj), encoding="utf-8")
        argv += ["-VarsFile", str(tmp / "vars.json")]
    result = subprocess.run(argv, capture_output=True, text=True, env=env, timeout=120, check=False)
    return Sent(tmp, result, out)


def _parameters(call: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    argv = call["argv"]
    ref = argv[argv.index("--parameters") + 1]
    assert ref.startswith("file://")
    return ref[7:], json.loads(call["files"][ref])


# ---------------------------------------------------------------------------
# The sender
# ---------------------------------------------------------------------------


def test_sender_is_ascii() -> None:
    assert all(b < 128 for b in SENDER.read_bytes())  # Windows PowerShell 5.1 reads BOM-less files as ANSI


def test_one_send_with_the_exports_first_and_the_timeout_passed(tmp_path: Path) -> None:
    run = send(tmp_path, scenario(), "echo CHECK=x\r\necho RESULT=expected\r\n",
               vars_obj={"PO_B": "two words", "PO_A": "it's"}, timeout=900)
    assert run.rc == 0, run.console
    (call,) = run.sends()
    argv = call["argv"]
    assert argv[argv.index("--instance-ids") + 1] == "i-0123456789abcdef0"
    assert argv[argv.index("--document-name") + 1] == "AWS-RunShellScript"
    assert argv[-4:] == ["--region", "eu-north-1", "--profile", "po-r1"]
    path, params = _parameters(call)
    assert params["commands"] == ["export PO_A='it'\\''s'", "export PO_B='two words'",
                                  "echo CHECK=x", "echo RESULT=expected"]
    assert params["executionTimeout"] == ["900"]
    assert not Path(path).exists(), "the parameters file must be removed after the send"
    assert not str(Path(path).resolve()).startswith(str(REPO))


def test_the_record_names_the_vars_and_never_their_values(tmp_path: Path) -> None:
    run = send(tmp_path, scenario(), vars_obj={"PO_SECRET_ID": "a-value-that-must-not-appear"})
    assert run.rc == 0, run.console
    rec = run.record()
    assert rec["vars_names"] == ["PO_SECRET_ID"]
    assert "a-value-that-must-not-appear" not in run.out.read_text(encoding="utf-8-sig")
    lf = b"echo CHECK=x\necho RESULT=expected\n"
    assert rec["script_sha256"] == hashlib.sha256(lf).hexdigest()
    assert rec["command_id"] == COMMAND_ID and rec["instance_id"] == "i-0123456789abcdef0"
    assert rec["status"] == "Success" and rec["responseCode"] == 0
    assert rec["stdout"].splitlines()[-1] == "RESULT=expected"
    assert rec["stdout_truncated"] is False
    assert rec["sent_utc"] and rec["finished_utc"] and rec["timeout_seconds"] == 900


def test_crlf_is_sent_and_hashed_as_lf(tmp_path: Path) -> None:
    crlf = send(tmp_path, scenario(), script_bytes=b"echo CHECK=x\r\necho RESULT=expected\r\n")
    assert crlf.rc == 0, crlf.console
    _, params = _parameters(crlf.sends()[0])
    assert not any("\r" in line for line in params["commands"])
    assert crlf.record()["script_sha256"] == hashlib.sha256(b"echo CHECK=x\necho RESULT=expected\n").hexdigest()


def test_a_full_stdout_sets_the_truncation_flag_and_a_failure_exits_1(tmp_path: Path) -> None:
    full = _invocation("Failed", stdout="x" * 24000)
    run = send(tmp_path, scenario(**{"ssm get-command-invocation|Status": [ok("Failed")],
                                     "ssm get-command-invocation": [ok(full)]}))
    assert run.rc == 1
    rec = run.record()
    assert rec["status"] == "Failed" and rec["stdout_truncated"] is True


def test_a_refused_send_is_recorded_and_the_file_still_removed(tmp_path: Path) -> None:
    denied = {"out": "An error occurred (AccessDeniedException) when calling the SendCommand operation", "rc": 254}
    run = send(tmp_path, scenario(**{"ssm send-command": [denied]}))
    assert run.rc == 1
    assert run.record()["status"] == "NotSent"
    path, _ = _parameters(run.sends()[0])
    assert not Path(path).exists()
    assert not [c for c in run.calls if c["argv"][:2] == ["ssm", "get-command-invocation"]]


@pytest.mark.parametrize("case", ["out_exists", "no_instance", "lowercase_var", "not_po_var", "number_value",
                                  "non_ascii_script", "vars_array"])
def test_bad_inputs_are_refused_before_any_aws_call(tmp_path: Path, case: str) -> None:
    kwargs: dict[str, Any] = {}
    if case == "out_exists":
        (tmp_path / "result.json").write_text("{}", encoding="utf-8")
    elif case == "no_instance":
        kwargs["instance"] = None
    elif case == "lowercase_var":
        kwargs["vars_obj"] = {"po_a": "x"}
    elif case == "not_po_var":
        kwargs["vars_obj"] = {"PATH": "/tmp"}
    elif case == "number_value":
        kwargs["vars_obj"] = {"PO_A": 3}
    elif case == "non_ascii_script":
        kwargs["script_text"] = "echo —\n"
    elif case == "vars_array":
        kwargs["vars_obj"] = ["PO_A"]
    run = send(tmp_path, scenario(), **kwargs)
    assert run.rc == 2, run.console
    assert "REFUSED" in run.console
    assert run.calls == []
    if case != "out_exists":
        assert not run.out.exists()


# ---------------------------------------------------------------------------
# The host scripts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", SCRIPTS)
def test_host_scripts_are_lf_ascii_and_end_with_a_result(name: str) -> None:
    data = (HOST / name).read_bytes()
    assert b"\r" not in data and all(b < 128 for b in data)
    text = data.decode("ascii")
    assert 'echo "RESULT=expected"' in text and 'echo "RESULT=unexpected"' in text
    assert text.rstrip().splitlines()[-1] == "exit 0"
    for forbidden in ("0.0.0.0/0", "get-secret-value", "s3 rm", "put-object", "set -x", "cat \"$REC\""):
        assert forbidden not in text
    # The host only reads the bucket: every s3 cp copies from it, never to it.
    for line in text.splitlines():
        if "aws s3 cp" in line:
            assert line.split("aws s3 cp", 1)[1].split()[0].startswith('"$SRC')


@pytest.mark.parametrize("path", [HOST / n for n in SCRIPTS] + [DC33], ids=lambda p: p.name)
def test_host_scripts_parse_in_bash(path: Path) -> None:
    if not BASH:
        pytest.skip("no Git Bash")
    result = subprocess.run([BASH, "-n", path.as_posix()], capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stderr


def test_the_fetch_script_reads_the_deploy_bucket_and_expects_the_o5_tarball() -> None:
    text = (HOST / "r15_07_fetch.sh").read_text(encoding="ascii")
    r7 = {o["OutputKey"]: o["OutputValue"]
          for o in json.loads((V2 / "R7" / "R7_outputs.json").read_text(encoding="utf-8-sig"))}
    assert f"SRC=s3://{r7['DeployBucketName']}/bundles/msca-dn-freeze-2026-11-12\n" in text
    o5 = json.loads((REPO / "docs" / "tier4_orchestration_state" / "decision_log"
                     / "msca-dn-refreeze-o5_2026-11-12.json").read_text(encoding="utf-8"))
    assert f"EXPECT_SHA={o5_sha(o5)}\n" in text
    assert "EXPECT_SIZE=92413570\n" in text


def o5_sha(record: Any) -> str:
    found = set(re.findall(r'"sha256": "([0-9a-f]{64})"', json.dumps(record)))
    tar = {h for h in found if h.startswith("9c5351ef")}
    assert len(tar) == 1
    return tar.pop()


def test_the_dc33_35_vars_match_r8_and_the_scripts_install_path() -> None:
    vars_obj = json.loads((HOST / "dc33_35.vars.json").read_text(encoding="utf-8"))
    declared = re.search(r"^# In: (.+)\.$", DC33.read_text(encoding="utf-8"), re.M).group(1)
    needed = set(declared.split(", "))
    assert set(vars_obj) == needed
    digest = (V2 / "R8" / "R8_09_key-names-digest.txt").read_text(encoding="utf-8-sig")
    assert f"expected_sha256: {vars_obj['PO_EXPECTED_SHA256']}" in digest
    keys = re.search(r"^keys: (.+)$", digest, re.M).group(1).split(", ")
    assert sorted(vars_obj["PO_CONFIG_KEYS"].split()) == sorted(keys)
    assert vars_obj["PO_SECRET_ID"] == "proposal-orchestrator/env-config" and vars_obj["PO_REGION"] == "eu-north-1"
    for name in SCRIPTS[2:]:
        text = (HOST / name).read_text(encoding="ascii")
        assert f"APP={vars_obj['PO_BUNDLE_DIR']}\n" in text and f"PY={vars_obj['PO_BUNDLE_PYTHON']}\n" in text


def test_the_assessor_is_point_10s_and_not_the_drafter() -> None:
    text = (HOST / "r15_11_prepare.sh").read_text(encoding="ascii")
    assert "MODEL=eu.anthropic.claude-sonnet-4-6\n" in text
    assert 'VERSION="bedrock-converse-eu-north-1@$(date -u +%F)"' in text
    assert "opus" not in text


def _block(name: str, marker: str) -> str:
    text = (HOST / name).read_text(encoding="ascii")
    return text.split(f"<<'{marker}'\n", 1)[1].split(f"\n{marker}\n", 1)[0] + "\n"


def test_prepare_and_receipt_scripts_expect_the_same_operator_fields() -> None:
    for name, marker in (("r15_11_prepare.sh", "PYEOF"), ("r15_12_receipt.sh", "FILL")):
        body = _block(name, marker)
        found = set(re.findall(r'"([a-z_.]+(?:\[0\])?)"', body.split("}", 1)[0]))
        assert found == OPERATOR_FIELDS, name


def test_the_filler_turns_a_real_draft_into_a_green_receipt(converse_env, client, tmp_path) -> None:  # noqa: F811
    root = tmp_path / "smoke"
    assert _prepare(root) == 0
    draft = root / cs.DRAFT_FILE
    doc = json.loads(draft.read_text(encoding="utf-8"))
    # Here no bundle is installed, so prepare found no manifest to read the revision from.
    doc["repository_revision"] = "17e32d54f2bd60c1d69d9a1b6caa8688c34f036e"
    draft.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    parser = tmp_path / "parse.py"
    parser.write_text(_block("r15_11_prepare.sh", "PYEOF"), encoding="utf-8")
    model = doc["rendered_request"]["model_id"]
    version = doc["model_identity"]["pin"].split("@", 1)[1]
    seen = subprocess.run([sys.executable, str(parser), str(draft), model, version],
                          capture_output=True, text=True, check=True).stdout
    assert f"placeholders={','.join(sorted(OPERATOR_FIELDS))}" in seen.splitlines()
    assert "rendered_request.tool_config_present=false" in seen.splitlines()

    filler = tmp_path / "fill.py"
    filler.write_text(_block("r15_12_receipt.sh", "FILL"), encoding="utf-8")
    receipt = tmp_path / "readiness_receipt.json"
    done = subprocess.run([sys.executable, str(filler), str(draft), str(receipt), "2026-11-12"],
                          capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
    assert done.stdout.strip() == "placeholders_left=none"
    filled = json.loads(receipt.read_text(encoding="utf-8"))
    assert filled["review_state"] == "operator_reviewed" and filled["declared_status"] == "Confirmed"
    assert filled["isolation_check"]["verified_on"] == "2026-11-12"
    assert len(filled["isolation_check"]["evidence"]) == 3
    result = cs.check_receipt(root, receipt)
    assert result.green, result.lines()

    again = subprocess.run([sys.executable, str(filler), str(receipt), str(tmp_path / "second.json"), "2026-11-12"],
                           capture_output=True, text=True, check=False)
    assert again.returncode == 1 and again.stdout.startswith("fill_refused=")
