"""The host launcher ``runner.host_env`` (ticket R9, OD8 (a)).

Exit condition 2 of R9: the launcher exports the configured values without
logging any of them. Every test drives :func:`runner.host_env.main` with an
injected Secrets Manager client, an injected ``exec`` and an explicit
environment mapping: no AWS call, no real exec, and ``os.environ`` (into which
``runner.transport.config`` loads the workstation's ``.env`` at import) is
never read.

Distinctive sentinel values stand in for the configuration; the tests assert
that none of them reaches stdout, stderr, a ``logging`` record or the exec'd
command's argv. The response field holding the value is named at run time
(F-R8-8), never written out in this file.

Decision record: ``aws-redeployment-r9-runtime-config_2026-10-27``.
"""

from __future__ import annotations

import io
import json
import logging
from pathlib import Path
from typing import Any

import pytest

import runner.host_env as host_env
from runner.transport.config import PRESET_REGISTRY, PRODUCTION_BACKENDS

REPO_ROOT = Path(__file__).resolve().parent.parent

VALUE_FIELD = "Secret" + "String"
SECRET_ID = "proposal-orchestrator/env-config"

#: A production-suitable Converse preset (the first by name). The real
#: secret's preset, BEDROCK_CONVERSE_EU (R8-D3), is tested by name in
#: TestTheRealSecretsPreset.
PRESET = next(
    name for name, p in sorted(PRESET_REGISTRY.items())
    if p.production_suitable and p.backend_name in PRODUCTION_BACKENDS
)

REGION = "zz-sentinel-7"
MODEL = "zz.sentinel.model-4f9c2e"
COMMAND = ["python", "-m", "runner", "--help"]

#: Values that must never be printed or logged. "true" and "metadata" are fixed
#: by contract (REQUIRED_VALUES) and are too common to search for.
SENTINELS = (REGION, MODEL, PRESET)


def _value(**changes: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "ORCHESTRATOR_TRANSPORT_PRESET": PRESET,
        "ORCHESTRATOR_PRODUCTION_MODE": "true",
        "ORCHESTRATOR_DIAGNOSTIC_LEVEL": "metadata",
        "AWS_REGION": REGION,
        "ORCHESTRATOR_TRANSPORT_MODEL": MODEL,
    }
    for key, new in changes.items():
        if new is None:
            value.pop(key, None)
        else:
            value[key] = new
    return value


class FakeClient:
    """Records every call; answers GetSecretValue with *text* or raises *error*."""

    def __init__(self, text: Any = None, error: Exception | None = None,
                 response: Any = None) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._text = text
        self._error = error
        self._response = response

    def get_secret_value(self, **kwargs: Any) -> Any:
        self.calls.append(("get_secret_value", kwargs))
        if self._error is not None:
            raise self._error
        if self._response is not None:
            return self._response
        return {"ARN": "arn:example", "Name": SECRET_ID, VALUE_FIELD: self._text,
                "VersionStages": ["AWSCURRENT"]}

    def __getattr__(self, name: str) -> Any:  # any other API call is recorded and refused
        def call(**kwargs: Any) -> Any:
            self.calls.append((name, kwargs))
            raise AssertionError(f"unexpected call {name}")
        return call


class Run:
    """One launcher run with everything captured."""

    def __init__(self, client: FakeClient, *, environ: dict[str, str] | None = None,
                 argv: list[str] | None = None, exec_error: Exception | None = None) -> None:
        self.client = client
        self.factory_regions: list[str] = []
        self.execs: list[tuple[str, list[str], dict[str, str]]] = []
        self.stderr = io.StringIO()
        self._exec_error = exec_error
        self.argv = argv if argv is not None else [
            "--region", REGION, "--secret-id", SECRET_ID, "--", *COMMAND]
        self.environ = {"PATH": "/usr/bin", "HOME": "/home/ssm-user"} if environ is None else environ

    def factory(self, region: str) -> FakeClient:
        self.factory_regions.append(region)
        return self.client

    def exec_fn(self, file: str, args: list[str], env: dict[str, str]) -> None:
        self.execs.append((file, list(args), dict(env)))
        if self._exec_error is not None:
            raise self._exec_error

    def __call__(self) -> int:
        return host_env.main(self.argv, environ=self.environ, client_factory=self.factory,
                             exec_fn=self.exec_fn, stderr=self.stderr)


def _run(text: Any = None, **kwargs: Any) -> tuple[Run, int]:
    client_kwargs = {k: kwargs.pop(k) for k in ("error", "response") if k in kwargs}
    run = Run(FakeClient(text=text, **client_kwargs), **kwargs)
    return run, run()


@pytest.fixture
def captured(capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture):
    """Everything a value could leak into: both streams and every log record."""
    caplog.set_level(logging.DEBUG)

    def text(run: Run) -> str:
        out, err = capsys.readouterr()
        logs = "\n".join(f"{r.name} {r.getMessage()}" for r in caplog.records)
        argv = "\n".join(" ".join(args) for _, args, _ in run.execs)
        return "\n".join((out, err, run.stderr.getvalue(), logs, argv))

    return text


def _assert_no_value(text: str) -> None:
    for sentinel in SENTINELS:
        assert sentinel not in text, f"a configured value leaked: {sentinel!r}"


# --------------------------------------------------------------------------- #
# The configured values are exported, and nothing is printed or logged
# --------------------------------------------------------------------------- #


class TestExportsWithoutLogging:
    def test_valid_value_execs_the_command_with_the_five_variables(self, captured):
        run, code = _run(json.dumps(_value()))
        assert code == 0
        assert len(run.execs) == 1
        file, args, env = run.execs[0]
        assert (file, args) == (COMMAND[0], COMMAND)
        for key, expected in _value().items():
            assert env[key] == expected
        assert env["AWS_DEFAULT_REGION"] == REGION
        assert env["PATH"] == "/usr/bin" and env["HOME"] == "/home/ssm-user"

    def test_success_prints_and_logs_nothing(self, captured):
        run, code = _run(json.dumps(_value()))
        assert code == 0
        text = captured(run)
        assert text.strip() == " ".join(COMMAND)  # only the exec'd argv, which carries no value
        _assert_no_value(text)

    def test_get_secret_value_is_the_only_call_once_with_the_named_secret(self):
        run, _ = _run(json.dumps(_value()))
        assert run.client.calls == [("get_secret_value", {"SecretId": SECRET_ID})]
        assert run.factory_regions == [REGION]

    def test_the_callers_environment_is_not_modified(self):
        environ = {"PATH": "/usr/bin"}
        run, _ = _run(json.dumps(_value()), environ=environ)
        assert environ == {"PATH": "/usr/bin"}
        assert run.execs[0][2] is not environ

    def test_matching_caller_values_are_accepted(self):
        environ = {"PATH": "/usr/bin", **_value(), "AWS_DEFAULT_REGION": REGION}
        run, code = _run(json.dumps(_value()), environ=environ)
        assert code == 0 and len(run.execs) == 1

    def test_the_value_field_name_is_never_written_out_in_the_launcher(self):
        source = (REPO_ROOT / "runner" / "host_env.py").read_text(encoding="utf-8")
        assert VALUE_FIELD not in source  # F-R8-8: assembled at run time


# --------------------------------------------------------------------------- #
# Refusals: nothing exported, nothing exec'd, no value printed
# --------------------------------------------------------------------------- #


CREDENTIAL_SHAPED = "ORCHESTRATOR_TRANSPORT_API_" + "KEY"

REFUSED_VALUES = {
    "missing key": _value(ORCHESTRATOR_TRANSPORT_MODEL=None),
    "extra key": {**_value(), "ORCHESTRATOR_TRANSPORT_BACKEND": "bedrock_converse"},
    "credential-shaped key": {**_value(), CREDENTIAL_SHAPED: MODEL},
    "non-string value": _value(AWS_REGION=["zz", "sentinel"]),
    "empty value": _value(ORCHESTRATOR_TRANSPORT_MODEL="  "),
    "production mode not true": _value(ORCHESTRATOR_PRODUCTION_MODE="false"),
    "production mode wrong case": _value(ORCHESTRATOR_PRODUCTION_MODE="True"),
    "diagnostic level not metadata": _value(ORCHESTRATOR_DIAGNOSTIC_LEVEL="full"),
    "region differs from --region": _value(AWS_REGION="zz-other-sentinel-3"),
    "unknown preset": _value(ORCHESTRATOR_TRANSPORT_PRESET="ZZ_NO_SUCH_PRESET_SENTINEL"),
    "non-production preset": _value(ORCHESTRATOR_TRANSPORT_PRESET="CLAUDE_REFERENCE"),
    "mantle preset (F6)": _value(ORCHESTRATOR_TRANSPORT_PRESET="BEDROCK_EU_PRODUCTION"),
}


class TestRefusals:
    @pytest.mark.parametrize("case", sorted(REFUSED_VALUES))
    def test_refused_value(self, case, captured):
        run, code = _run(json.dumps(REFUSED_VALUES[case]))
        assert code == host_env.EXIT_REFUSED
        assert run.execs == []
        text = captured(run)
        assert "host_env: refused:" in text
        _assert_no_value(text)
        for other in ("zz-other-sentinel-3", "ZZ_NO_SUCH_PRESET_SENTINEL"):
            assert other not in text

    @pytest.mark.parametrize("text", [
        "[1, 2, 3]",
        '"zz.sentinel.model-4f9c2e"',
        '{"AWS_REGION": "zz-sentinel-7", ',  # truncated JSON: the parser's text names the value
    ])
    def test_value_that_is_not_a_json_object_is_refused(self, text, captured):
        run, code = _run(text)
        assert code == host_env.EXIT_REFUSED and run.execs == []
        _assert_no_value(captured(run))

    def test_response_without_a_string_value_is_refused(self, captured):
        run, code = _run(response={"ARN": "arn:example", "Name": SECRET_ID})
        assert code == host_env.EXIT_REFUSED and run.execs == []

    @pytest.mark.parametrize("key", [*host_env.CONFIG_KEYS, "AWS_DEFAULT_REGION"])
    def test_a_caller_value_that_disagrees_is_refused(self, key, captured):
        environ = {"PATH": "/usr/bin", key: "zz-caller-sentinel-5"}
        run, code = _run(json.dumps(_value()), environ=environ)
        assert code == host_env.EXIT_REFUSED and run.execs == []
        text = captured(run)
        assert key in text  # the name is reported
        _assert_no_value(text)
        assert "zz-caller-sentinel-5" not in text

    def test_refusal_names_keys_only(self, captured):
        run, code = _run(json.dumps(_value(ORCHESTRATOR_DIAGNOSTIC_LEVEL="full")))
        line = run.stderr.getvalue().strip()
        assert line == ("host_env: refused: value is not the one the private host requires; "
                        "keys: ORCHESTRATOR_DIAGNOSTIC_LEVEL")
        assert "full" not in line


class TestReadFailures:
    def test_client_error_reports_the_code_only(self, captured):
        from botocore.exceptions import ClientError

        error = ClientError(
            {"Error": {"Code": "AccessDeniedException",
                       "Message": f"not authorized on {MODEL} in {REGION}"}},
            "GetSecretValue",
        )
        run, code = _run(error=error)
        assert code == host_env.EXIT_READ_FAILED and run.execs == []
        text = captured(run)
        assert "host_env: the secret could not be read (AccessDeniedException)" in text
        _assert_no_value(text)

    def test_other_errors_report_the_class_name_only(self, captured):
        run, code = _run(error=RuntimeError(f"endpoint for {REGION} said {MODEL}"))
        assert code == host_env.EXIT_READ_FAILED and run.execs == []
        text = captured(run)
        assert "(RuntimeError)" in text
        _assert_no_value(text)

    def test_a_failing_client_factory_reports_the_class_name_only(self, captured):
        def factory(region: str) -> Any:
            raise ImportError(f"no module for {REGION}")

        stderr = io.StringIO()
        code = host_env.main(["--region", REGION, "--secret-id", SECRET_ID, "--", *COMMAND],
                             environ={}, client_factory=factory,
                             exec_fn=lambda *a: pytest.fail("exec"), stderr=stderr)
        assert code == host_env.EXIT_READ_FAILED
        assert stderr.getvalue().strip() == "host_env: the secret could not be read (ImportError)"

    def test_a_command_that_cannot_start_reports_the_class_name_only(self, captured):
        run, code = _run(json.dumps(_value()), exec_error=FileNotFoundError(MODEL))
        assert code == host_env.EXIT_EXEC_FAILED
        text = run.stderr.getvalue()
        assert "(FileNotFoundError)" in text
        _assert_no_value(text)


class TestArguments:
    @pytest.mark.parametrize("argv", [
        ["--secret-id", SECRET_ID, "--", *COMMAND],  # no --region: no default Region
        ["--region", REGION, "--", *COMMAND],  # no --secret-id
    ])
    def test_region_and_secret_id_are_required(self, argv):
        with pytest.raises(SystemExit) as exc:
            Run(FakeClient(text=json.dumps(_value())), argv=argv)()
        assert exc.value.code == 2

    def test_a_command_is_required(self):
        run, code = _run(json.dumps(_value()), argv=["--region", REGION, "--secret-id", SECRET_ID])
        assert code == host_env.EXIT_REFUSED and run.client.calls == []

    def test_an_empty_region_is_refused_before_any_read(self):
        run, code = _run(json.dumps(_value()),
                         argv=["--region", " ", "--secret-id", SECRET_ID, "--", *COMMAND])
        assert code == host_env.EXIT_REFUSED and run.client.calls == []


class TestTheRealSecretsPreset:
    def test_the_real_secrets_preset_is_accepted(self):
        """R8-D3: the secret stores BEDROCK_CONVERSE_EU, which R9e added.

        Unconditional since R9e (decision record
        ``aws-redeployment-r9e-eu-region_2026-10-27``, point 15): removing the
        preset, or making it unsuitable for production, fails here.
        """
        name = "BEDROCK_CONVERSE_EU"
        run, code = _run(json.dumps(_value(ORCHESTRATOR_TRANSPORT_PRESET=name)))
        assert code == 0 and len(run.execs) == 1
        assert run.execs[0][2]["ORCHESTRATOR_TRANSPORT_PRESET"] == name
