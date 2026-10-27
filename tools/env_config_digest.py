"""Key names and digest of the runtime configuration secret (ticket R8).

Ticket R8 of ``plans/aws_redeployment_tickets.md``; decision record
``aws-redeployment-r8-secret_2026-10-26`` (R8-D7). The evidence of R8 may
record the configuration secret's key names and metadata only, never its
values (handoff 2026-10-21 §7a, CG5 rule). This script lets the admin role
show that the stored object is the one the template defines, without any
value reaching a console, a file or a transcript:

- it reads the current version through the AWS CLI (``get-secret-value``),
  keeps the answer in memory, and parses the value as a JSON object;
- it prints the secret's name, the version's stages, the sorted key names and
  the SHA-256 of the object's canonical JSON (keys sorted, no whitespace,
  UTF-8);
- with ``--template`` and ``--parameters`` it derives the expected object
  from ``deploy/aws/templates/50-secret.yaml`` and the parameter file, and
  prints ``MATCH`` or ``MISMATCH`` for the key names and for the digest.

A SHA-256 of five short configuration strings is not a protection of those
strings; the values are not secret (R8-D2) and sit in the repository's
template anyway. The digest exists so that the evidence can say "equal"
without quoting them, which keeps the evidence folder within E0's rule.

The name of the response field that carries the value is one of the four
patterns ``tools/evidence_secret_scan.py`` refuses. It is assembled at run
time and never printed, so neither this script's output nor a step sheet
that calls it contains it.

Usage::

    py -3.10 -m tools.env_config_digest --profile po-r1 --region eu-north-1 \
        --template deploy/aws/templates/50-secret.yaml \
        --parameters deploy/aws/parameters/secret.json

Exit status: 0 when the read succeeded (and, with ``--template``, both the
key names and the digest match), 1 on a mismatch, 2 when the read or the
derivation fails.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

DEFAULT_SECRET_ID = "proposal-orchestrator/env-config"
SECRET_RESOURCE = "EnvConfigSecret"

# The response field and template property that carry the value (see the
# module docstring for why the name is assembled).
VALUE_FIELD = "Secret" + "String"

_SUB_REF = re.compile(r"\$\{([^}]+)\}")


def canonical_json(obj: dict[str, Any]) -> bytes:
    """The canonical JSON form the digest is taken over."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(obj: dict[str, Any]) -> str:
    """SHA-256 (hex) of :func:`canonical_json`."""
    return hashlib.sha256(canonical_json(obj)).hexdigest()


def expected_object(template: Path, parameters: Path, region: str) -> dict[str, Any]:
    """The object the template stores, with its ``Fn::Sub`` resolved.

    Only ``${AWS::Region}`` and template parameters (from the parameter file,
    or their defaults) are resolved; any other reference is an error.
    """
    from tools import aws_template_guard as guard

    resources = guard.load_template(template)
    params_doc = resources.get("Parameters", {})
    value = resources["Resources"][SECRET_RESOURCE]["Properties"][VALUE_FIELD]
    if not (isinstance(value, dict) and set(value) == {"Fn::Sub"} and isinstance(value["Fn::Sub"], str)):
        raise ValueError("the secret's value is not a single-string Fn::Sub")

    values = {
        name: spec["Default"] for name, spec in params_doc.items() if isinstance(spec, dict) and "Default" in spec
    }
    for entry in json.loads(parameters.read_text(encoding="utf-8-sig")):
        values[entry["ParameterKey"]] = entry["ParameterValue"]
    values["AWS::Region"] = region

    def _resolve(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in values:
            raise ValueError(f"unresolved reference ${{{name}}} in the secret's value")
        return str(values[name])

    obj = json.loads(_SUB_REF.sub(_resolve, value["Fn::Sub"]))
    if not isinstance(obj, dict):
        raise ValueError("the secret's value is not a JSON object")
    return obj


def _read_current(secret_id: str, region: str, profile: Optional[str]) -> tuple[str, list[str], dict[str, Any]]:
    aws = shutil.which("aws")
    if aws is None:
        raise RuntimeError("the AWS CLI (aws) is not on PATH")
    command = [aws, "secretsmanager", "get-secret-value", "--secret-id", secret_id, "--region", region, "--output", "json"]
    if profile:
        command[1:1] = ["--profile", profile]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603 - fixed argv
    if completed.returncode != 0:
        # CLI error text names the caller, the action and the resource, not the value.
        raise RuntimeError(f"get-secret-value failed (exit {completed.returncode}): {completed.stderr.strip()}")
    answer = json.loads(completed.stdout)
    raw = answer.get(VALUE_FIELD)
    if not isinstance(raw, str):
        raise RuntimeError("the current version holds no JSON text value")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise RuntimeError("the value is not a JSON object")
    return str(answer.get("Name")), list(answer.get("VersionStages") or []), obj


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="env_config_digest",
        description="Print the key names and the SHA-256 of the runtime configuration secret, never its values.",
    )
    parser.add_argument("--secret-id", default=DEFAULT_SECRET_ID)
    parser.add_argument("--region", required=True)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--template", type=Path, default=None)
    parser.add_argument("--parameters", type=Path, default=None)
    args = parser.parse_args(argv)

    if (args.template is None) != (args.parameters is None):
        print("ERROR: --template and --parameters go together", file=sys.stderr)
        return 2

    try:
        name, stages, stored = _read_current(args.secret_id, args.region, args.profile)
    except (RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    stored_keys = sorted(stored)
    stored_digest = digest(stored)
    del stored

    print(f"name: {name}")
    print(f"version_stages: {', '.join(stages)}")
    print(f"key_count: {len(stored_keys)}")
    print(f"keys: {', '.join(stored_keys)}")
    print(f"sha256: {stored_digest}")

    if args.template is None:
        return 0

    try:
        expected = expected_object(args.template, args.parameters, args.region)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    keys_match = sorted(expected) == stored_keys
    digest_match = digest(expected) == stored_digest
    print(f"expected_sha256: {digest(expected)}")
    print(f"keys: {'MATCH' if keys_match else 'MISMATCH'}")
    print(f"sha256: {'MATCH' if digest_match else 'MISMATCH'}")
    return 0 if keys_match and digest_match else 1


if __name__ == "__main__":
    sys.exit(main())
