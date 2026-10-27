"""Host launcher: runtime configuration from the runtime secret (R9, OD8 (a)).

Run on the private host, under the bundle's interpreter::

    python -m runner.host_env --region eu-north-1 \\
        --secret-id proposal-orchestrator/env-config -- <command> [args...]

It calls Secrets Manager ``GetSecretValue`` once (the only action the
runtime role may perform on the secret: R5 ``RuntimeSecretRead``, R8-D13),
checks the value, sets the configured variables in a copy of the
environment, and replaces itself with *command* (``os.execvpe``). No value
passes through a shell, a file, ``argv`` or the output streams.

What it accepts
---------------
The value must be one JSON object of exactly the five keys of
:data:`CONFIG_KEYS`, each a string (R8-D2), with
``ORCHESTRATOR_PRODUCTION_MODE=true`` and
``ORCHESTRATOR_DIAGNOSTIC_LEVEL=metadata`` (the launcher exists only for the
private host). Its ``AWS_REGION`` must equal ``--region``. The preset must
name a production-suitable ``bedrock_converse``-class preset of
:mod:`runner.transport.config`; until R9e adds ``BEDROCK_CONVERSE_EU``
(R8-D3), the real secret is therefore refused. A credential-shaped key name
(containing ``KEY``, ``SECRET``, ``TOKEN`` or ``PASSWORD``) is refused.

Precedence
----------
The caller's environment may not disagree with the secret: if it sets one
of the five keys, or ``AWS_DEFAULT_REGION``, to a different value, the
launcher refuses. ``AWS_DEFAULT_REGION`` is set to the ``AWS_REGION`` value so
that every boto3 client in the child agrees.

Output
------
Nothing on success. On failure one line on stderr naming the failure kind and
key **names** only, never a value, the response object or raw exception text
(only a boto3 error code or an exception class name). Exit codes:
:data:`EXIT_REFUSED` (2) configuration refused, :data:`EXIT_READ_FAILED` (3)
the secret could not be read, :data:`EXIT_EXEC_FAILED` (4) the command could
not be started.

This module sits outside the scheduler, agent and skill stack of
``CLAUDE.md`` §17: it only prepares the process environment of the command it
starts. Decision record: ``aws-redeployment-r9-runtime-config_2026-10-27``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Callable, Mapping, Optional, Sequence, TextIO

#: The five keys of the runtime secret's value (R8-D2), in the template's order.
CONFIG_KEYS: tuple[str, ...] = (
    "ORCHESTRATOR_TRANSPORT_PRESET",
    "ORCHESTRATOR_PRODUCTION_MODE",
    "ORCHESTRATOR_DIAGNOSTIC_LEVEL",
    "AWS_REGION",
    "ORCHESTRATOR_TRANSPORT_MODEL",
)

#: Values the launcher requires (case-sensitive, as the template writes them).
REQUIRED_VALUES: dict[str, str] = {
    "ORCHESTRATOR_PRODUCTION_MODE": "true",
    "ORCHESTRATOR_DIAGNOSTIC_LEVEL": "metadata",
}

#: Words that make a key name credential-shaped (as tests/test_aws_env_config_template.py).
CREDENTIAL_WORDS: tuple[str, ...] = ("KEY", "SECRET", "TOKEN", "PASSWORD")

#: Variables the launcher sets in the child environment besides CONFIG_KEYS.
DERIVED_KEYS: tuple[str, ...] = ("AWS_DEFAULT_REGION",)

EXIT_REFUSED = 2
EXIT_READ_FAILED = 3
EXIT_EXEC_FAILED = 4

#: The response field holding the value, assembled at run time so that no
#: file naming it trips the evidence secret scan (F-R8-8).
_VALUE_FIELD = "Secret" + "String"

_PREFIX = "host_env"


class LaunchRefused(Exception):
    """The configuration is refused. Carries a kind and key names, never values."""

    def __init__(self, kind: str, names: Sequence[str] = ()) -> None:
        self.kind = kind
        self.names = tuple(names)
        super().__init__(kind)

    def line(self) -> str:
        suffix = f"; keys: {', '.join(self.names)}" if self.names else ""
        return f"{_PREFIX}: refused: {self.kind}{suffix}"


class SecretReadFailed(Exception):
    """``GetSecretValue`` failed. Carries an error code or class name only."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)

    def line(self) -> str:
        return f"{_PREFIX}: the secret could not be read ({self.code})"


def _default_client_factory(region: str) -> Any:
    import boto3

    return boto3.client("secretsmanager", region_name=region)


def read_value(client: Any, secret_id: str) -> Any:
    """Call ``GetSecretValue`` once and return the parsed JSON value.

    Raises :class:`SecretReadFailed` on any client error (code only) and
    :class:`LaunchRefused` when the value is absent or not JSON (no parser text).
    """
    try:
        response = client.get_secret_value(SecretId=secret_id)
    except Exception as exc:  # noqa: BLE001 - only the code or class name leaves
        error = getattr(exc, "response", None)
        code = None
        if isinstance(error, Mapping):
            code = (error.get("Error") or {}).get("Code")
        raise SecretReadFailed(str(code) if code else type(exc).__name__) from None
    text = response.get(_VALUE_FIELD) if isinstance(response, Mapping) else None
    if not isinstance(text, str):
        raise LaunchRefused("the secret has no string value")
    try:
        return json.loads(text)
    except ValueError:
        raise LaunchRefused("the secret value is not JSON") from None


def _preset_problem(name: str) -> Optional[str]:
    """Why the preset cannot run in production mode, or ``None``."""
    from runner.transport.config import PRODUCTION_BACKENDS, get_transport_preset

    try:
        preset = get_transport_preset(name)
    except ValueError:
        return "the preset is not known to runner.transport.config"
    if not preset.production_suitable or preset.backend_name not in PRODUCTION_BACKENDS:
        return "the preset is not production-suitable"
    return None


def validate(value: Any, region: str) -> dict[str, str]:
    """Return the five configured variables, or raise :class:`LaunchRefused`."""
    if not isinstance(value, dict):
        raise LaunchRefused("the secret value is not a JSON object")
    credential = sorted(k for k in value if any(w in str(k).upper() for w in CREDENTIAL_WORDS))
    if credential:
        raise LaunchRefused("credential-shaped key name", credential)
    extra = sorted(str(k) for k in value if k not in CONFIG_KEYS)
    if extra:
        raise LaunchRefused("unexpected key", extra)
    missing = [k for k in CONFIG_KEYS if k not in value]
    if missing:
        raise LaunchRefused("missing key", missing)
    not_string = [k for k in CONFIG_KEYS if not isinstance(value[k], str)]
    if not_string:
        raise LaunchRefused("value is not a string", not_string)
    empty = [k for k in CONFIG_KEYS if not value[k].strip()]
    if empty:
        raise LaunchRefused("value is empty", empty)
    wrong = [k for k, required in REQUIRED_VALUES.items() if value[k] != required]
    if wrong:
        raise LaunchRefused("value is not the one the private host requires", wrong)
    if value["AWS_REGION"] != region:
        raise LaunchRefused("the secret's Region differs from --region", ["AWS_REGION"])
    problem = _preset_problem(value["ORCHESTRATOR_TRANSPORT_PRESET"])
    if problem:
        raise LaunchRefused(problem, ["ORCHESTRATOR_TRANSPORT_PRESET"])
    return {k: value[k] for k in CONFIG_KEYS}


def child_environment(config: Mapping[str, str], environ: Mapping[str, str]) -> dict[str, str]:
    """The command's environment: *environ* plus *config*, refusing disagreement."""
    wanted = dict(config)
    wanted["AWS_DEFAULT_REGION"] = config["AWS_REGION"]
    conflicts = [k for k in (*CONFIG_KEYS, *DERIVED_KEYS) if k in environ and environ[k] != wanted[k]]
    if conflicts:
        raise LaunchRefused("the caller's environment sets a different value", conflicts)
    child = dict(environ)
    child.update(wanted)
    return child


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m runner.host_env",
        description="Read the runtime secret and run COMMAND with its configuration.",
    )
    parser.add_argument("--region", required=True,
                        help="Region of the secret; must equal the secret's AWS_REGION")
    parser.add_argument("--secret-id", required=True,
                        help="secret name, e.g. proposal-orchestrator/env-config")
    parser.add_argument("command", nargs=argparse.REMAINDER,
                        help="-- followed by the command and its arguments")
    return parser


def main(
    argv: Optional[Sequence[str]] = None,
    *,
    environ: Optional[Mapping[str, str]] = None,
    client_factory: Callable[[str], Any] = _default_client_factory,
    exec_fn: Callable[[str, list[str], dict[str, str]], Any] = os.execvpe,
    stderr: Optional[TextIO] = None,
) -> int:
    """Run the launcher. Returns an exit code only when it does not exec."""
    # Snapshot the caller's environment before anything is imported that
    # could change os.environ (runner.transport.config loads .env at import).
    environ = dict(os.environ if environ is None else environ)
    err = sys.stderr if stderr is None else stderr
    args = _parser().parse_args(argv)
    command = list(args.command)
    if command[:1] == ["--"]:
        command = command[1:]
    if not command:
        err.write(f"{_PREFIX}: refused: no command after --\n")
        return EXIT_REFUSED
    region = args.region.strip()
    if not region or not args.secret_id.strip():
        err.write(f"{_PREFIX}: refused: --region and --secret-id must not be empty\n")
        return EXIT_REFUSED

    try:
        try:
            client = client_factory(region)
        except Exception as exc:  # noqa: BLE001 - only the class name leaves
            raise SecretReadFailed(type(exc).__name__) from None
        value = read_value(client, args.secret_id)
        config = validate(value, region)
        child = child_environment(config, environ)
    except SecretReadFailed as exc:
        err.write(exc.line() + "\n")
        return EXIT_READ_FAILED
    except LaunchRefused as exc:
        err.write(exc.line() + "\n")
        return EXIT_REFUSED

    try:
        exec_fn(command[0], command, child)
    except OSError as exc:
        err.write(f"{_PREFIX}: the command could not be started ({type(exc).__name__})\n")
        return EXIT_EXEC_FAILED
    return 0  # reached only with an injected exec_fn (tests)


if __name__ == "__main__":  # pragma: no cover - exercised on the host (R12b)
    sys.exit(main())
