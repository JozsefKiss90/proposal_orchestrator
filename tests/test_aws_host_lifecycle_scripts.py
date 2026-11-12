"""The R14 host-lifecycle scripts: both forms run against a fake AWS CLI.

``deploy/aws/scripts/host-lifecycle.ps1`` (workstation) and ``host-lifecycle.sh`` (CloudShell) start,
stop and tear down the endpoints-and-host stack. These tests pin the decisions of
``docs/infrastructure_security/evidence_v2/R14/STEPS.md``: the change set is checked before anything
is created, the typed word gates creation, resumption and deletion, a failed execute is never waited
on, a prefix is never overwritten, and teardown proves that nothing of the stack remains.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "deploy" / "aws" / "scripts"
PS1 = SCRIPTS / "host-lifecycle.ps1"
SH = SCRIPTS / "host-lifecycle.sh"
HOST_JSON = REPO / "deploy" / "aws" / "parameters" / "host.json"
FAKE = REPO / "tests" / "fixtures" / "fake_aws_lifecycle.py"
ACCOUNT = "797661577394"
STACK = "proposal-orchestrator-host"
SEVEN = ["BedrockRuntimeEndpoint", "StsEndpoint", "SecretsManagerEndpoint", "SsmEndpoint",
         "SsmMessagesEndpoint", "Ec2MessagesEndpoint", "Host"]
Q_STATUS = "Stacks[0].StackStatus"
Q_INSTANCE = "Stacks[0].Outputs[?OutputKey=='InstanceId'].OutputValue | [0]"
Q_STATE = "Reservations[0].Instances[0].State.Name"
Q_PING = "InstanceInformationList[0].PingStatus"
Q_VPC = "Stacks[0].Outputs[?OutputKey=='VpcId'].OutputValue | [0]"
Q_RECORD = "Reservations[0].Instances[0].{id:InstanceId,state:State.Name,type:InstanceType,vpc:VpcId}"
Q_BASE = ("Stacks[?starts_with(StackName, 'proposal-orchestrator-') && StackName != "
          "'proposal-orchestrator-host'].{name:StackName,status:StackStatus}")
ABSENT = {"out": f"An error occurred (ValidationError) when calling the DescribeStacks operation: "
                 f"Stack with id {STACK} does not exist", "rc": 254}


def ok(out: Any) -> dict[str, Any]:
    return {"out": out if isinstance(out, str) else json.dumps(out), "rc": 0}


def change_set(adds: Optional[list[str]] = None, capabilities: Optional[list[str]] = None) -> dict[str, Any]:
    params = json.loads(HOST_JSON.read_text(encoding="utf-8-sig"))
    params += [{"ParameterKey": "InstanceType", "ParameterValue": "c7i-flex.large"},
               {"ParameterKey": "LatestAmiId", "ParameterValue": "/aws/service/ami",
                "ResolvedValue": "ami-0123456789abcdef0"}]
    return {"Status": "CREATE_COMPLETE", "ExecutionStatus": "AVAILABLE", "Capabilities": capabilities or [],
            "Tags": [{"Key": "project", "Value": "proposal-orchestrator"}], "Parameters": params,
            "Changes": [{"Type": "Resource", "ResourceChange": {"Action": "Add", "LogicalResourceId": a}}
                        for a in (adds if adds is not None else SEVEN)]}


def base_stacks(n: int = 5) -> list[dict[str, str]]:
    names = ["network", "iam", "kms", "audit", "secret"]
    return [{"name": f"proposal-orchestrator-{x}", "status": "CREATE_COMPLETE"} for x in names[:n]]


def scenario_create(**over: Any) -> dict[str, Any]:
    s = {
        "sts get-caller-identity": [ok({"Account": ACCOUNT, "Arn": "arn:aws:sts::%s:assumed-role/x/y" % ACCOUNT})],
        f"cloudformation describe-stacks|{Q_STATUS}": [ABSENT, ok("CREATE_COMPLETE")],
        "cloudformation create-change-set": [ok({"Id": "arn:cs", "StackId": "arn:stack"})],
        "cloudformation describe-change-set": [ok(change_set())],
        f"cloudformation describe-stacks|{Q_INSTANCE}": [ok("i-0abc")],
        "cloudformation describe-stacks|Stacks[0].Outputs": [ok([{"OutputKey": "InstanceId", "OutputValue": "i-0abc"}])],
        f"ssm describe-instance-information|{Q_PING}": [ok("ConnectionLost"), ok("Online")],
        "ssm describe-instance-information": [ok([{"id": "i-0abc", "ping": "Online"}])],
    }
    s.update(over)
    return s


def scenario_up(state: str, **over: Any) -> dict[str, Any]:
    s = scenario_create()
    s[f"cloudformation describe-stacks|{Q_STATUS}"] = [ok("CREATE_COMPLETE")]
    s[f"ec2 describe-instances|{Q_STATE}"] = [ok(state)]
    s.update(over)
    return s


def scenario_teardown(**over: Any) -> dict[str, Any]:
    s = scenario_up("running")
    s[f"cloudformation describe-stacks|{Q_VPC}"] = [ok("vpc-0abc")]
    s["cloudformation describe-stacks"] = [ABSENT]
    s["ec2 describe-vpc-endpoints"] = [ok([{"id": "vpce-1", "type": "Gateway", "state": "available"}])]
    for k in ("ec2 describe-network-interfaces", "ec2 describe-instances", "ec2 describe-volumes"):
        s[k] = [ok([])]
    s[f"cloudformation describe-stacks|{Q_BASE}"] = [ok(base_stacks())]
    s.update(over)
    return s


# ---------------------------------------------------------------------------
# Running the two forms
# ---------------------------------------------------------------------------


def _git_bash() -> Optional[str]:
    if os.name != "nt":
        return shutil.which("bash")
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"):
        if Path(candidate).exists():
            return candidate
    return None  # WSL's bash.exe would not see this Python


POWERSHELL = shutil.which("powershell") or shutil.which("pwsh")
BASH = _git_bash()


class Run:
    def __init__(self, tmp: Path, result: subprocess.CompletedProcess[str], out: Path, prefix: str) -> None:
        self.rc = result.returncode
        self.console = result.stdout + result.stderr
        self.out, self.prefix = out, prefix
        log = tmp / "fake.log"
        self.calls = [json.loads(x)["argv"] for x in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []

    def file(self, name: str) -> str:
        return (self.out / f"{self.prefix}_{name}").read_text(encoding="utf-8-sig")

    def log(self) -> list[str]:
        return [x for x in self.file("log.txt").splitlines() if x]

    def ops(self) -> list[str]:
        return [" ".join(c[:3] if len(c) > 2 and c[1] == "wait" else c[:2]) for c in self.calls]


def _shims(tmp: Path) -> Path:
    shims = tmp / "shims"
    shims.mkdir()
    py, fake = Path(sys.executable).as_posix(), FAKE.as_posix()
    (shims / "aws.cmd").write_text(f'@"{sys.executable}" "{FAKE}" %*\r\n', encoding="ascii")
    for name, body in (("aws", f'exec "{py}" "{fake}" "$@"'), ("python3", f'exec "{py}" "$@"')):
        path = shims / name
        path.write_bytes(f"#!/bin/sh\n{body}\n".encode("ascii"))
        path.chmod(0o755)
    return shims


def run_form(form: str, tmp: Path, action: str, scenario: dict[str, Any], typed: str = "",
             prefix: str = "T_01") -> Run:
    out = tmp / "out"
    out.mkdir(exist_ok=True)
    (tmp / "scenario.json").write_text(json.dumps(scenario), encoding="utf-8")
    env = dict(os.environ)
    env.update({"FAKE_AWS_SCENARIO": str(tmp / "scenario.json"), "FAKE_AWS_LOG": str(tmp / "fake.log"),
                "PO_POLL_SECONDS": "0", "PATH": str(_shims(tmp) if not (tmp / "shims").exists() else tmp / "shims")
                + os.pathsep + os.environ.get("PATH", "")})
    if form == "ps1":
        if not POWERSHELL:
            pytest.skip("no PowerShell")
        argv = [POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(PS1),
                "-Action", action, "-AwsProfile", "po-r1", "-OutDir", str(out), "-Prefix", prefix]
    else:
        if not BASH:
            pytest.skip("no Git Bash")
        argv = [BASH, SH.as_posix(), action, out.as_posix(), prefix]
    result = subprocess.run(argv, input=typed, capture_output=True, text=True, env=env, timeout=120, check=False)
    return Run(tmp, result, out, prefix)


FORMS = ["ps1", "sh"]


# ---------------------------------------------------------------------------
# Static rules
# ---------------------------------------------------------------------------


def test_cloudshell_form_has_lf_line_endings() -> None:
    assert b"\r" not in SH.read_bytes()


@pytest.mark.parametrize("path", [PS1, SH])
def test_scripts_keep_the_template_rules(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "0.0.0.0/0" not in text and "::/0" not in text
    for forbidden in ("create-route", "authorize-security-group", "create-internet-gateway", "create-nat-gateway",
                      "put-model-invocation-logging", "get-secret-value", "ExpectedAccountId\": \"7"):
        assert forbidden not in text
    assert ACCOUNT not in text  # the account comes from host.json


@pytest.mark.parametrize("path", [PS1, SH])
def test_scripts_delete_only_the_host_stack(path: Path) -> None:
    lines = [x for x in path.read_text(encoding="utf-8").splitlines() if "delete-stack" in x and not x.lstrip().startswith("#")]
    assert lines
    for line in lines:
        assert "$Stack" in line or '"$STACK"' in line


def test_powershell_form_is_ascii() -> None:
    assert all(b < 128 for b in PS1.read_bytes())  # Windows PowerShell 5.1 reads BOM-less files as ANSI


def test_powershell_plan_lists_every_call_with_profile_and_region(tmp_path: Path) -> None:
    if not POWERSHELL:
        pytest.skip("no PowerShell")
    result = subprocess.run([POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(PS1),
                             "-Action", "plan", "-AwsProfile", "po-r1", "-OutDir", str(tmp_path), "-Prefix", "P"],
                            capture_output=True, text=True, timeout=60, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    lines = [x for x in result.stdout.splitlines() if x.strip()]
    assert len(lines) >= 25
    for line in lines:
        assert " aws " in line and line.endswith("--region eu-north-1 --profile po-r1")
    deletes = [x for x in lines if "delete-stack" in x]
    assert deletes and all(f"--stack-name {STACK} " in x for x in deletes)
    assert not list(tmp_path.iterdir())


# ---------------------------------------------------------------------------
# start
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("form", FORMS)
def test_start_creates_after_the_typed_word(form: str, tmp_path: Path) -> None:
    run = run_form(form, tmp_path, "start", scenario_create(), typed="create\n")
    assert run.rc == 0, run.console
    log = run.log()
    assert log[-1] == "RESULT=started"
    assert "path=create" in log and "confirmed=create" in log
    assert any(x.startswith("change_set_ok=7 Add; instance_type=c7i-flex.large; image=ami-") for x in log)
    ops = run.ops()
    assert ops.index("cloudformation describe-change-set") < ops.index("cloudformation execute-change-set")
    assert ops.index("cloudformation execute-change-set") < ops.index("cloudformation wait stack-create-complete")
    for name in ("identity.json", "change-set.json", "execute-exit.txt", "stack-status.json", "stack-events.json",
                 "outputs.json", "instance-information.json"):
        assert run.file(name)
    assert "execute exit=0" in run.file("execute-exit.txt")
    for call in run.calls:
        assert call[call.index("--region") + 1] == "eu-north-1"
        assert ("--profile" in call) == (form == "ps1")
    cs_call = next(c for c in run.calls if c[1] == "create-change-set")
    assert cs_call[cs_call.index("--change-set-type") + 1] == "CREATE"
    assert cs_call[cs_call.index("--stack-name") + 1] == STACK


@pytest.mark.parametrize("form", FORMS)
def test_start_without_the_typed_word_creates_nothing(form: str, tmp_path: Path) -> None:
    run = run_form(form, tmp_path, "start", scenario_create(), typed="yes\n")
    assert run.rc == 3
    assert run.log()[-1] == "RESULT=not-confirmed"
    assert "confirmed=no" in run.log()
    ops = run.ops()
    assert "cloudformation execute-change-set" not in ops
    assert "cloudformation delete-stack" in ops  # the unexecuted change set leaves a stack in review


@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("bad", [SEVEN[:-1], SEVEN + ["Extra"], "capabilities"])
def test_start_refuses_a_change_set_other_than_the_seven_adds(form: str, bad: Any, tmp_path: Path) -> None:
    cs = change_set(capabilities=["CAPABILITY_IAM"]) if bad == "capabilities" else change_set(adds=bad)
    run = run_form(form, tmp_path, "start", scenario_create(**{"cloudformation describe-change-set": [ok(cs)]}),
                   typed="create\n")
    assert run.rc == 3
    assert run.log()[-1] == "RESULT=refused-change-set"
    assert any(x.startswith("change_set_problem=") for x in run.log())
    assert "cloudformation execute-change-set" not in run.ops()
    assert "cloudformation delete-stack" in run.ops()


@pytest.mark.parametrize("form", FORMS)
def test_start_refuses_a_parameter_other_than_host_json(form: str, tmp_path: Path) -> None:
    cs = change_set()
    cs["Parameters"][0]["ParameterValue"] = "111122223333"
    run = run_form(form, tmp_path, "start", scenario_create(**{"cloudformation describe-change-set": [ok(cs)]}),
                   typed="create\n")
    assert run.rc == 3
    assert "change_set_problem=parameter ExpectedAccountId differs from host.json" in run.log()


@pytest.mark.parametrize("form", FORMS)
def test_a_failed_execute_is_never_waited_on(form: str, tmp_path: Path) -> None:
    sc = scenario_create(**{"cloudformation execute-change-set": [{"out": "An error occurred (ChangeSetNotFound)", "rc": 254}]})
    run = run_form(form, tmp_path, "start", sc, typed="create\n")
    assert run.rc == 1
    assert run.log()[-1] == "RESULT=execute-failed"
    assert "cloudformation wait stack-create-complete" not in run.ops()
    assert "execute exit=254" in run.file("execute-exit.txt")


@pytest.mark.parametrize("form", FORMS)
def test_start_refuses_another_account_before_any_other_call(form: str, tmp_path: Path) -> None:
    sc = scenario_create(**{"sts get-caller-identity": [ok({"Account": "111122223333"})]})
    run = run_form(form, tmp_path, "start", sc, typed="create\n")
    assert run.rc == 2
    assert run.log()[-1] == "RESULT=refused-account"
    assert run.ops() == ["sts get-caller-identity"]


@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("status, advice", [
    ("REVIEW_IN_PROGRESS", "A stack in review holds no resource: run teardown to remove it"),
    ("DELETE_IN_PROGRESS", "Wait until it ends, then run again"),
    ("ROLLBACK_COMPLETE", "Run teardown, then start again"),
])
def test_start_refuses_a_stack_in_another_state_with_advice_for_that_state(
        form: str, status: str, advice: str, tmp_path: Path) -> None:
    # F-R14-1: the advice for DELETE_IN_PROGRESS named REVIEW_IN_PROGRESS and said to run teardown.
    sc = scenario_create(**{f"cloudformation describe-stacks|{Q_STATUS}": [ok(status)]})
    run = run_form(form, tmp_path, "start", sc, typed="create\n")
    assert run.rc == 2
    assert run.log()[-1] == "RESULT=refused-state"
    assert f"refused: stack is {status}. {advice}" in run.log()
    assert "cloudformation create-change-set" not in run.ops()


@pytest.mark.parametrize("path, guard", [
    (PS1, "if (-not [Console]::IsInputRedirected) { while ([Console]::KeyAvailable)"),
    (SH, "if [ -t 0 ]; then while read -r -t 0.1 _ahead; do :; done; fi"),
])
def test_prompt_discards_input_typed_before_it_only_at_a_terminal(path: Path, guard: str) -> None:
    # F-R14-2: an Enter pressed while the script ran was read as the answer. The discard runs before the
    # prompt, and only at a terminal: the tests above pipe the answer in, and it must still be read.
    text = path.read_text(encoding="utf-8")
    assert text.count(guard) == 1
    assert text.index(guard) < text.index("Type $")


@pytest.mark.parametrize("form", FORMS)
def test_start_resumes_a_stopped_host_after_the_typed_word(form: str, tmp_path: Path) -> None:
    run = run_form(form, tmp_path, "start", scenario_up("stopped"), typed="start\n")
    assert run.rc == 0, run.console
    log = run.log()
    assert "path=resume" in log and "confirmed=start" in log and log[-1] == "RESULT=started"
    start = next(c for c in run.calls if c[1] == "start-instances")
    assert start[start.index("--instance-ids") + 1] == "i-0abc"
    assert "cloudformation create-change-set" not in run.ops()
    assert run.file("instance-information.json")


@pytest.mark.parametrize("form", FORMS)
def test_start_on_a_running_host_changes_nothing(form: str, tmp_path: Path) -> None:
    run = run_form(form, tmp_path, "start", scenario_up("running"))
    assert run.rc == 0
    assert run.log()[-1] == "RESULT=already-running"
    assert not {"ec2 start-instances", "cloudformation create-change-set"} & set(run.ops())


@pytest.mark.parametrize("form", FORMS)
def test_start_reports_a_host_that_never_comes_online(form: str, tmp_path: Path) -> None:
    sc = scenario_create(**{f"ssm describe-instance-information|{Q_PING}": [ok("None")]})
    run = run_form(form, tmp_path, "start", sc, typed="create\n")
    assert run.rc == 1
    assert run.log()[-1] == "RESULT=not-online"
    assert run.ops().count("ssm describe-instance-information") == 31  # 30 tries, then the record


@pytest.mark.parametrize("form", FORMS)
def test_a_used_prefix_is_refused(form: str, tmp_path: Path) -> None:
    (tmp_path / "out").mkdir()
    (tmp_path / "out" / "T_01_log.txt").write_text("earlier\n", encoding="utf-8")
    run = run_form(form, tmp_path, "start", scenario_create(), typed="create\n")
    assert run.rc == 2
    assert run.calls == []
    assert (tmp_path / "out" / "T_01_log.txt").read_text(encoding="utf-8") == "earlier\n"


# ---------------------------------------------------------------------------
# stop
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("form", FORMS)
def test_stop_stops_the_host_and_records_what_still_costs(form: str, tmp_path: Path) -> None:
    sc = scenario_up("running", **{
        f"ec2 describe-instances|{Q_STATE}": [ok("running"), ok("stopped")],
        f"ec2 describe-instances|{Q_RECORD}": [ok({"id": "i-0abc", "state": "stopped", "vpc": "vpc-0abc"})],
        "ec2 describe-vpc-endpoints": [ok([{"id": "vpce-1", "type": "Interface", "state": "available"}])],
    })
    run = run_form(form, tmp_path, "stop", sc)
    assert run.rc == 0, run.console
    assert run.log()[-1] == "RESULT=stopped"
    ops = run.ops()
    assert "ec2 stop-instances" in ops and "ec2 wait instance-stopped" in ops
    assert not {"cloudformation delete-stack", "ec2 terminate-instances"} & set(ops)
    ep = next(c for c in run.calls if c[1] == "describe-vpc-endpoints")
    assert "Name=vpc-id,Values=vpc-0abc" in ep
    for name in ("instance.json", "volumes.json", "vpc-endpoints.json"):
        assert run.file(name)


# ---------------------------------------------------------------------------
# teardown
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("form", FORMS)
def test_teardown_deletes_after_the_typed_word_and_proves_nothing_remains(form: str, tmp_path: Path) -> None:
    run = run_form(form, tmp_path, "teardown", scenario_teardown(), typed="delete\n")
    assert run.rc == 0, run.console
    log = run.log()
    assert "confirmed=delete" in log and "base_stacks_complete=5" in log and log[-1] == "RESULT=deleted"
    deletes = [c for c in run.calls if c[1] == "delete-stack"]
    assert len(deletes) == 1 and deletes[0][deletes[0].index("--stack-name") + 1] == STACK
    assert "does not exist" in run.file("host-stack-after.txt")
    for name in ("after-vpc-endpoints.json", "after-network-interfaces.json", "after-instances.json",
                 "after-volumes.json", "after-base-stacks.json", "delete-exit.txt"):
        assert run.file(name)


@pytest.mark.parametrize("form", FORMS)
def test_teardown_without_the_typed_word_deletes_nothing(form: str, tmp_path: Path) -> None:
    run = run_form(form, tmp_path, "teardown", scenario_teardown(), typed="\n")
    assert run.rc == 3
    assert "cloudformation delete-stack" not in run.ops()


@pytest.mark.parametrize("form", FORMS)
@pytest.mark.parametrize("left", ["endpoint", "volume", "base", "lookup"])
def test_teardown_reports_leftovers(form: str, left: str, tmp_path: Path) -> None:
    over: dict[str, Any] = {}
    if left == "endpoint":
        over["ec2 describe-vpc-endpoints"] = [ok([{"id": "vpce-2", "type": "Interface", "state": "deleting"}])]
    elif left == "volume":
        over["ec2 describe-volumes"] = [ok([{"id": "vol-1", "state": "available"}])]
    elif left == "base":
        over[f"cloudformation describe-stacks|{Q_BASE}"] = [ok(base_stacks(4))]
    else:
        over["ec2 describe-network-interfaces"] = [{"out": "An error occurred (RequestExpired)", "rc": 255}]
    run = run_form(form, tmp_path, "teardown", scenario_teardown(**over), typed="delete\n")
    assert run.rc == 1, run.console
    assert run.log()[-1] == "RESULT=leftovers"
    assert any(x.startswith("leftover=") for x in run.log())


@pytest.mark.parametrize("form", FORMS)
def test_teardown_of_an_absent_stack_does_nothing(form: str, tmp_path: Path) -> None:
    sc = scenario_teardown(**{f"cloudformation describe-stacks|{Q_STATUS}": [ABSENT]})
    run = run_form(form, tmp_path, "teardown", sc, typed="delete\n")
    assert run.rc == 0
    assert run.log()[-1] == "RESULT=absent"
    assert "cloudformation delete-stack" not in run.ops()


def test_cloudshell_check_records_versions_and_hashes(tmp_path: Path) -> None:
    sc = scenario_create(**{"--version": [ok("aws-cli/2.0.0")]})
    run = run_form("sh", tmp_path, "check", sc, prefix="T_06")
    assert run.rc == 0, run.console
    check = run.file("check.txt").splitlines()
    assert check[-1] == "RESULT=ready"
    assert f"caller_account={ACCOUNT}" in check and "region=eu-north-1" in check
    assert sum(1 for x in check if x.startswith("sha256_") and len(x.split("=", 1)[1]) == 64) == 3
