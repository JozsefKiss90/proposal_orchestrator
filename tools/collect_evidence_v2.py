"""Parameterised evidence collector for the AWS redeployment (ticket R12a).

Ticket R12a of ``plans/aws_redeployment_tickets.md``; decision record
``aws-redeployment-r12a-collector_2026-10-28``. It replaces the first
hardening's ``collect_evidence.ps1`` (kept unchanged in the v1 tree as
history), which hard-coded the old account, its resource ids and its Region
and wrote into the v1 tree.

What it reads (point 2 of the decision record)
----------------------------------------------
Nothing in this module names an account, a Region, a resource id or a model.
Every such value comes from one of these files:

- ``deploy/aws/outputs_contract.json``: the stacks, their tickets, their
  parameter files and their output keys;
- ``<outputs root>/<ticket>/<ticket>_outputs.json`` for each base stack (the
  files the contract's ``outputs_file_rule`` names), and the per-session host
  stack's outputs file only when ``--host-outputs`` names it;
- the stacks' parameter files (``ExpectedAccountId``, ``ExpectedRegion``, the
  OD7 profile and model ARNs, the routed Regions, the transport model);
- ``deploy/aws/collector_inputs.json``: the few values no stack holds (the
  unapproved Region of the negative tests, the deny-probe model ids, the
  egress probe hosts, the fixed test string, the host paths of the DC-15
  tests), each with its source.

Before any collection it compares the caller's account with
``ExpectedAccountId`` and every stack's live outputs with its outputs file,
and refuses on any difference (a stale outputs file, a recreated host stack).

What it writes (points 6 and 20)
--------------------------------
One new folder per run, ``evidence_v2/<ticket>/<ticket>_<NN>_collector/``,
which must not exist yet. A path inside the v1 tree, or anywhere outside
``evidence_v2/``, is refused before any AWS call. The folder holds one file
per check (``<control>_<check>.json`` with the CLI's own JSON, or ``.txt`` with
the exit code and the error text), ``summary.json`` and, written last,
``MANIFEST.sha256``. The secret scan and the old-ID guard then run over the
folder; a finding makes the run fail and nothing is edited.

How it calls AWS (points 1, 4 and 8)
------------------------------------
Through the AWS CLI, one injected runner, always with ``--profile`` and
``--output json`` and, except for the global IAM and Organizations APIs, the
parameters' Region. Workstation commands use read verbs only. Host checks are
fixed scripts in ``tools/collector_host_checks/`` sent with SSM Run Command;
the evidence is the ``get-command-invocation`` answer and each script's
SHA-256. No command reads the runtime secret's value from the workstation.

Usage::

    py -3.10 -m tools.collect_evidence_v2 --ticket R12b --step 03 --profile po-r1 --plan
    py -3.10 -m tools.collect_evidence_v2 --ticket R12b --step 03 --profile po-r1 --host-outputs

``--host-outputs`` without a path reads the contract's file for the host stack
(``evidence_v2/R11/R11_outputs.json``); a path names another (a later session's).
``--host-bundle-dir`` (DC-33 to DC-35) and ``--f7-url-file`` (F7) add the two host
checks that need them; without them those checks are recorded "not collected".

Exit status: 0 when every check was collected, gave a declared expected error
or was not collected for a stated reason; 1 when a check failed or the scans
refused the folder; 2 when the run was refused before collecting anything.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]

EVIDENCE_V2 = Path("docs/infrastructure_security/evidence_v2")
#: The first hardening's evidence and records: never written (E0, point 6).
V1_PATHS: tuple[Path, ...] = (
    Path("docs/infrastructure_security/evidence"),
    Path("docs/infrastructure_security/audit_package"),
    Path("docs/infrastructure_security/aws_hardening_control_register.md"),
    Path("docs/infrastructure_security/aws_hardening_worklog.md"),
)
CONTRACT = Path("deploy/aws/outputs_contract.json")
INPUTS = Path("deploy/aws/collector_inputs.json")
HOST_CHECKS_DIR = Path(__file__).resolve().parent / "collector_host_checks"

#: ``--host-outputs`` given without a path: the contract's own outputs file of the host stack.
CONTRACT_DEFAULT = Path("<contract>")

SUMMARY_NAME = "summary.json"
MANIFEST_NAME = "MANIFEST.sha256"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_REFUSED = 2

_TICKET = re.compile(r"^R\d{1,2}[a-z]?$")
_STEP = re.compile(r"^\d{2}$")
_PROFILE = re.compile(r"^[A-Za-z0-9_.-]+$")
_ACCOUNT = re.compile(r"^\d{12}$")
_REGION = re.compile(r"^[a-z]{2}-[a-z]+-\d$")
_AWS_ERROR = re.compile(r"An error occurred \(([A-Za-z0-9.]+)\)")
_HOST_PATH = re.compile(r"^/[A-Za-z0-9._/-]*$")
_F7_URL = re.compile(r"^https://[A-Za-z0-9.-]+\.amazonaws\.com/\S+$")

#: Terminal statuses of an SSM command invocation.
_SSM_TERMINAL = frozenset({"Success", "Failed", "Cancelled", "TimedOut"})
_SSM_PENDING_ERRORS = frozenset({"InvocationDoesNotExist"})

#: Workstation verbs (point 8). ``send-command`` and ``get-command-invocation``
#: are the host-check transport.
READ_PREFIXES: tuple[str, ...] = ("describe-", "get-", "list-", "lookup-")
READ_EXACT: frozenset[str] = frozenset({"simulate-principal-policy"})
HOST_TRANSPORT_OPERATIONS: frozenset[str] = frozenset({"send-command", "get-command-invocation"})

#: Services whose API is global: no ``--region`` (as R5's step sheet).
GLOBAL_SERVICES: frozenset[str] = frozenset({"iam", "organizations"})


class CollectorRefused(Exception):
    """The run is refused before anything is collected."""


# ---------------------------------------------------------------------------
# Loading the inputs (point 2)
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        raise CollectorRefused(f"input file not found: {path.as_posix()}") from None
    except json.JSONDecodeError as exc:
        raise CollectorRefused(f"input file is not JSON: {path.as_posix()} ({exc.msg})") from None


def _outputs_map(path: Path, expected_keys: Iterable[str]) -> dict[str, str]:
    data = _read_json(path)
    if not isinstance(data, list) or not all(isinstance(e, dict) for e in data):
        raise CollectorRefused(f"not a describe-stacks Outputs list: {path.as_posix()}")
    values = {str(e.get("OutputKey")): str(e.get("OutputValue")) for e in data}
    expected = set(expected_keys)
    if set(values) != expected:
        missing = sorted(expected - set(values))
        extra = sorted(set(values) - expected)
        raise CollectorRefused(
            f"{path.as_posix()} does not hold the contract's outputs (missing {missing}, unexpected {extra})"
        )
    return values


def _parameters_map(path: Path) -> dict[str, str]:
    data = _read_json(path)
    if not isinstance(data, list):
        raise CollectorRefused(f"not a parameter file: {path.as_posix()}")
    return {str(e["ParameterKey"]): str(e["ParameterValue"]) for e in data}


@dataclass(frozen=True)
class Sources:
    """Where the inputs are read from. Defaults are the repository's files."""

    repo_root: Path = REPO_ROOT
    source_root: Path = REPO_ROOT
    contract: Optional[Path] = None
    parameters_dir: Optional[Path] = None
    outputs_root: Optional[Path] = None
    inputs: Optional[Path] = None
    host_outputs: Optional[Path] = None

    def contract_path(self) -> Path:
        return self.contract or self.source_root / CONTRACT

    def inputs_path(self) -> Path:
        return self.inputs or self.source_root / INPUTS

    def parameters_path(self, contract_relative: str) -> Path:
        if self.parameters_dir is not None:
            return self.parameters_dir / Path(contract_relative).name
        return self.source_root / contract_relative

    def outputs_path(self, ticket: str) -> Path:
        root = self.outputs_root or self.repo_root / EVIDENCE_V2
        return root / ticket / f"{ticket}_outputs.json"


@dataclass
class Context:
    """Every value a check may use, by reference name."""

    account: str
    region: str
    refs: dict[str, Any]
    stacks: list[dict[str, Any]]
    host_present: bool
    files_read: dict[str, Path]

    def get(self, ref: str) -> Any:
        try:
            return self.refs[ref]
        except KeyError:
            raise CollectorRefused(f"no value for {ref}") from None


def load_context(sources: Sources, runtime: Mapping[str, Any]) -> Context:
    """Read the contract, outputs, parameters and inputs, or refuse."""
    files: dict[str, Path] = {}
    contract_path = sources.contract_path()
    contract = _read_json(contract_path)
    files["contract"] = contract_path
    refs: dict[str, Any] = {}
    stacks = list(contract.get("stacks") or [])
    if not stacks:
        raise CollectorRefused("the contract names no stacks")

    accounts: dict[str, str] = {}
    regions: dict[str, str] = {}
    host_present = False
    for stack in stacks:
        key = stack["key"]
        params_path = sources.parameters_path(stack["parameters"])
        params = _parameters_map(params_path)
        files[f"parameters:{key}"] = params_path
        for name, value in params.items():
            refs[f"param:{key}.{name}"] = value
        if "ExpectedAccountId" not in params or "ExpectedRegion" not in params:
            raise CollectorRefused(f"{params_path.as_posix()} lacks ExpectedAccountId or ExpectedRegion")
        accounts[key] = params["ExpectedAccountId"]
        regions[key] = params["ExpectedRegion"]

        if stack.get("lifecycle") == "per_session":
            if sources.host_outputs is None:
                continue
            outputs_path = sources.host_outputs
            if outputs_path == CONTRACT_DEFAULT:
                outputs_path = sources.outputs_path(stack["ticket"])
            host_present = True
        else:
            outputs_path = sources.outputs_path(stack["ticket"])
        outputs = _outputs_map(outputs_path, stack["outputs"].keys())
        files[f"outputs:{key}"] = outputs_path
        for name, value in outputs.items():
            refs[f"out:{key}.{name}"] = value

    if len(set(accounts.values())) != 1:
        raise CollectorRefused(f"the parameter files disagree on ExpectedAccountId: {sorted(set(accounts.values()))}")
    if len(set(regions.values())) != 1:
        raise CollectorRefused(f"the parameter files disagree on ExpectedRegion: {sorted(set(regions.values()))}")
    account = next(iter(accounts.values()))
    region = next(iter(regions.values()))
    if not _ACCOUNT.match(account):
        raise CollectorRefused("ExpectedAccountId is not a 12-digit account id")
    if not _REGION.match(region):
        raise CollectorRefused("ExpectedRegion is not a Region name")
    refs["account"] = account
    refs["region"] = region

    inputs_path = sources.inputs_path()
    inputs = _read_json(inputs_path)
    files["inputs"] = inputs_path
    for name in REQUIRED_INPUTS:
        entry = (inputs.get("inputs") or {}).get(name)
        if not isinstance(entry, dict) or "value" not in entry or not entry.get("source"):
            raise CollectorRefused(f"{inputs_path.as_posix()}: input {name} needs a value and a source")
        refs[f"input:{name}"] = entry["value"]
    if refs["input:negative_region"] in refs["param:iam.RoutedRegions"].split(","):
        raise CollectorRefused("the negative-test Region is one of the routed Regions")

    secret_stack = next(s for s in stacks if s["key"] == "secret")
    template = sources.source_root / secret_stack["template"]
    files["secret_template"] = template
    refs["derived:secret.expected_sha256"] = _expected_config_digest(
        template, sources.parameters_path(secret_stack["parameters"]), region
    )
    for name, value in runtime.items():
        refs[f"runtime:{name}"] = value
    return Context(account=account, region=region, refs=refs, stacks=stacks, host_present=host_present, files_read=files)


REQUIRED_INPUTS: tuple[str, ...] = (
    "negative_region",
    "deny_probe_global_profile_ids",
    "deny_probe_non_claude_model_ids",
    "deny_probe_other_profile_ids",
    "bundle_object_key",
    "bundle_prefix",
    "bedrock_log_group_prefix",
    "dns_services",
    "egress_probe_hosts",
    "converse_test_string",
    "dc15_home_dirs",
    "dc15_env_files",
)


def _expected_config_digest(template: Path, parameters: Path, region: str) -> str:
    """SHA-256 of the configuration object the secret template stores (R8-D7)."""
    from tools import env_config_digest

    try:
        return env_config_digest.digest(env_config_digest.expected_object(template, parameters, region))
    except (OSError, ValueError, KeyError) as exc:
        raise CollectorRefused(f"cannot derive the expected configuration digest: {exc}") from None


# ---------------------------------------------------------------------------
# The coverage map (point 7)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Command:
    """One concrete workstation command, without the profile and output flags."""

    file: str
    service: str
    operation: str
    args: tuple[str, ...]
    expected_errors: tuple[str, ...] = ()

    def argv(self, ctx: Context, profile: str) -> list[str]:
        argv = ["aws", self.service, self.operation, *self.args, "--profile", profile]
        if self.service not in GLOBAL_SERVICES:
            argv += ["--region", ctx.region]
        return argv + ["--output", "json"]


@dataclass(frozen=True)
class Check:
    """A row of the coverage map: controls, the values it uses, how it runs."""

    name: str
    controls: tuple[str, ...]
    scope: str  # "region", "global" or "host"
    uses: tuple[str, ...]
    build: Optional[Callable[["Refs"], list[Command]]] = None
    host_script: Optional[str] = None
    host_env: Optional[Callable[["Refs"], dict[str, str]]] = None
    needs_host: bool = False
    needs_runtime: tuple[str, ...] = ()
    after_host: bool = False
    expected_errors: tuple[str, ...] = ()


class Refs:
    """Read access to a context, limited to the references a check declares."""

    def __init__(self, ctx: Context, allowed: Sequence[str]) -> None:
        self._ctx = ctx
        self._allowed = frozenset(allowed)

    def __call__(self, ref: str) -> Any:
        if ref not in self._allowed:
            raise AssertionError(f"check uses {ref} without declaring it")
        return self._ctx.get(ref)

    def list(self, ref: str) -> list[str]:
        value = self(ref)
        if isinstance(value, str):
            return [v for v in value.split(",") if v]
        return [str(v) for v in value]


def _cmd(file: str, service: str, operation: str, *args: str, expected: tuple[str, ...] = ()) -> Command:
    return Command(file=file, service=service, operation=operation, args=tuple(args), expected_errors=expected)


def _single(name: str, controls: tuple[str, ...], uses: tuple[str, ...], service: str, operation: str,
            args: Callable[[Refs], Sequence[str]], *, after_host: bool = False, needs_host: bool = False,
            expected: tuple[str, ...] = ()) -> Check:
    scope = "global" if service in GLOBAL_SERVICES else "region"
    file = f"{controls[0]}_{name}.json"
    return Check(
        name=name,
        controls=controls,
        scope=scope,
        uses=uses,
        build=lambda r: [_cmd(file, service, operation, *args(r), expected=expected)],
        after_host=after_host,
        needs_host=needs_host,
        expected_errors=expected,
    )


def _ctx_entry(key: str, value: str) -> str:
    return f"ContextKeyName={key},ContextKeyValues={value},ContextKeyType=string"


_INVOKE = ("bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream")


def _simulation(file: str, role_arn: str, actions: Sequence[str], resources: Sequence[str],
                context: Sequence[str] = ()) -> Command:
    args = ["--policy-source-arn", role_arn, "--action-names", *actions, "--resource-arns", *resources]
    if context:
        args += ["--context-entries", *context]
    return _cmd(file, "iam", "simulate-principal-policy", *args)


def _arn_region(arn: str) -> str:
    return arn.split(":")[3]


def _arn_name(arn: str) -> str:
    return arn.split("/")[-1]


def _simulations(r: Refs) -> list[Command]:
    """The R5 step 09 cases (allowed and denied), rebuilt from the parameters."""
    role = r("out:iam.RuntimeRoleArn")
    region = r("region")
    account = r("account")
    profiles = r.list("param:iam.InferenceProfileArns")
    models = r.list("param:iam.FoundationModelArns")
    deploy = r("out:audit.DeployBucketName")
    trail_bucket = r("out:audit.TrailBucketName")
    bundle_key = r("input:bundle_object_key")
    in_region = _ctx_entry("aws:RequestedRegion", region)
    commands = [_simulation("DC-10_sim-allow-profiles.json", role, _INVOKE, profiles, [in_region])]
    for model_arn in models:
        model = _arn_name(model_arn)
        model_region = _arn_region(model_arn)
        profile = next((p for p in profiles if _arn_name(p).split(".", 1)[-1] == model), None)
        if profile is None:
            raise CollectorRefused(f"no inference profile routes to {model}")
        commands.append(_simulation(
            f"DC-10_sim-allow-fm-{model_region}-{model}.json", role, _INVOKE, [model_arn],
            [_ctx_entry("aws:RequestedRegion", model_region), _ctx_entry("bedrock:InferenceProfileArn", profile)],
        ))
    commands += [
        _simulation("DC-12_sim-allow-s3-get-bundle.json", role, ["s3:GetObject"],
                    [f"arn:aws:s3:::{deploy}/{bundle_key}"]),
        _simulation("DC-12_sim-allow-s3-list-bundles.json", role, ["s3:ListBucket"], [f"arn:aws:s3:::{deploy}"],
                    [_ctx_entry("s3:prefix", r("input:bundle_prefix"))]),
        _simulation("DC-12_sim-allow-secret.json", role, ["secretsmanager:GetSecretValue"],
                    [r("out:secret.SecretArn")]),
        _simulation("DC-12_sim-allow-sts-ssm.json", role,
                    ["sts:GetCallerIdentity", "ssm:UpdateInstanceInformation", "ssmmessages:OpenControlChannel",
                     "ec2messages:GetMessages"], ["*"]),
        _simulation("DC-11_sim-deny-admin-logging.json", role,
                    ["bedrock:PutModelInvocationLoggingConfiguration", "bedrock:CreateProvisionedModelThroughput"],
                    ["*"], [in_region]),
    ]
    for probe in r.list("input:deny_probe_global_profile_ids"):
        commands.append(_simulation(f"DC-11_sim-deny-global-profile-{probe}.json", role, _INVOKE,
                                    [f"arn:aws:bedrock:{region}:{account}:inference-profile/{probe}"], [in_region]))
    for probe in r.list("input:deny_probe_non_claude_model_ids"):
        commands.append(_simulation(f"DC-11_sim-deny-non-claude-model-{probe}.json", role, _INVOKE,
                                    [f"arn:aws:bedrock:{region}::foundation-model/{probe}"], [in_region]))
    for probe in r.list("input:deny_probe_other_profile_ids"):
        commands.append(_simulation(f"DC-11_sim-deny-other-profile-{probe}.json", role, _INVOKE,
                                    [f"arn:aws:bedrock:{region}:{account}:inference-profile/{probe}"], [in_region]))
    negative = r("input:negative_region")
    commands += [
        _simulation("DC-16_sim-deny-unapproved-region.json", role, _INVOKE, [profiles[0]],
                    [_ctx_entry("aws:RequestedRegion", negative)]),
        _simulation("DC-11_sim-deny-fm-without-profile.json", role, _INVOKE, [models[1 % len(models)]],
                    [_ctx_entry("aws:RequestedRegion", _arn_region(models[1 % len(models)]))]),
        _simulation("DC-11_sim-deny-s3-put-bundle.json", role, ["s3:PutObject", "s3:DeleteObject"],
                    [f"arn:aws:s3:::{deploy}/{bundle_key}"]),
        _simulation("DC-11_sim-deny-s3-other-bucket.json", role, ["s3:GetObject", "s3:PutObject"],
                    [f"arn:aws:s3:::{trail_bucket}/x"]),
        _simulation("DC-11_sim-deny-ec2.json", role, ["ec2:DescribeInstances", "ec2:RunInstances"], ["*"]),
        _simulation("DC-11_sim-deny-iam.json", role, ["iam:ListRoles", "iam:PassRole"], ["*"]),
        _simulation("DC-19_sim-deny-kms-identity-grant.json", role, ["kms:Decrypt"], [r("out:kms.KeyArn")]),
    ]
    return commands


def _bucket_checks(prefix: str, control_of: Mapping[str, str], bucket_ref: str) -> list[Check]:
    operations = {
        "encryption": "get-bucket-encryption",
        "public-access-block": "get-public-access-block",
        "versioning": "get-bucket-versioning",
        "ownership": "get-bucket-ownership-controls",
        "policy": "get-bucket-policy",
        "lifecycle": "get-bucket-lifecycle-configuration",
    }
    checks = []
    for short, operation in operations.items():
        control = control_of.get(short)
        if control is None:
            continue
        checks.append(_single(f"{prefix}-{short}", (control,), (bucket_ref,), "s3api", operation,
                              lambda r, ref=bucket_ref: ["--bucket", r(ref)]))
    return checks


_HOST_ENDPOINTS = (
    "BedrockRuntimeEndpointId",
    "StsEndpointId",
    "SecretsManagerEndpointId",
    "SsmEndpointId",
    "SsmMessagesEndpointId",
    "Ec2MessagesEndpointId",
)


def _host(name: str, controls: tuple[str, ...], script: str, uses: tuple[str, ...],
          env: Callable[[Refs], dict[str, str]], needs_runtime: tuple[str, ...] = ()) -> Check:
    return Check(
        name=name,
        controls=controls,
        scope="host",
        uses=("out:host.InstanceId", *uses),
        host_script=script,
        host_env=env,
        needs_host=True,
        needs_runtime=needs_runtime,
    )


def _words(values: Sequence[str]) -> str:
    return " ".join(values)


CHECKS: tuple[Check, ...] = (
    # --- Group 1: network (R4) and endpoints (R11) ---
    _single("route-table", ("DC-06",), ("out:network.PrivateRouteTableId",), "ec2", "describe-route-tables",
            lambda r: ["--route-table-ids", r("out:network.PrivateRouteTableId")]),
    _single("internet-gateways", ("DC-06", "DC-32"), ("out:network.VpcId",), "ec2", "describe-internet-gateways",
            lambda r: ["--filters", f"Name=attachment.vpc-id,Values={r('out:network.VpcId')}"]),
    _single("nat-gateways", ("DC-06", "DC-32"), ("out:network.VpcId",), "ec2", "describe-nat-gateways",
            lambda r: ["--filter", f"Name=vpc-id,Values={r('out:network.VpcId')}"]),
    _single("vpc", ("PL-8",), ("out:network.VpcId",), "ec2", "describe-vpcs",
            lambda r: ["--vpc-ids", r("out:network.VpcId")]),
    _single("vpc-dns-support", ("PL-8",), ("out:network.VpcId",), "ec2", "describe-vpc-attribute",
            lambda r: ["--vpc-id", r("out:network.VpcId"), "--attribute", "enableDnsSupport"]),
    _single("vpc-dns-hostnames", ("PL-8",), ("out:network.VpcId",), "ec2", "describe-vpc-attribute",
            lambda r: ["--vpc-id", r("out:network.VpcId"), "--attribute", "enableDnsHostnames"]),
    _single("security-groups", ("DC-03", "DC-07"),
            ("out:network.HostSecurityGroupId", "out:network.EndpointSecurityGroupId"), "ec2",
            "describe-security-groups",
            lambda r: ["--group-ids", r("out:network.HostSecurityGroupId"), r("out:network.EndpointSecurityGroupId")]),
    _single("security-group-rules", ("DC-03", "DC-07"),
            ("out:network.HostSecurityGroupId", "out:network.EndpointSecurityGroupId"), "ec2",
            "describe-security-group-rules",
            lambda r: ["--filters", "Name=group-id,Values="
                       f"{r('out:network.HostSecurityGroupId')},{r('out:network.EndpointSecurityGroupId')}"]),
    _single("s3-gateway-endpoint", ("DC-05",), ("out:network.S3GatewayEndpointId",), "ec2",
            "describe-vpc-endpoints", lambda r: ["--vpc-endpoint-ids", r("out:network.S3GatewayEndpointId")]),
    _single("subnet", ("DC-08",), ("out:network.PrivateSubnetId",), "ec2", "describe-subnets",
            lambda r: ["--subnet-ids", r("out:network.PrivateSubnetId")]),
    _single("vpc-subnets", ("DC-08",), ("out:network.VpcId",), "ec2", "describe-subnets",
            lambda r: ["--filters", f"Name=vpc-id,Values={r('out:network.VpcId')}"]),
    _single("interface-endpoints", ("DC-01", "DC-02", "DC-03", "DC-04", "DC-05"),
            tuple(f"out:host.{k}" for k in _HOST_ENDPOINTS), "ec2", "describe-vpc-endpoints",
            lambda r: ["--vpc-endpoint-ids", *(r(f"out:host.{k}") for k in _HOST_ENDPOINTS)], needs_host=True),
    _single("host-instance", ("DC-07", "DC-14"), ("out:host.InstanceId",), "ec2", "describe-instances",
            lambda r: ["--instance-ids", r("out:host.InstanceId")], needs_host=True),
    _single("instance-profile-association", ("DC-14",), ("out:host.InstanceId",), "ec2",
            "describe-iam-instance-profile-associations",
            lambda r: ["--filters", f"Name=instance-id,Values={r('out:host.InstanceId')}"], needs_host=True),
    _single("ssm-instance", ("DC-14",), ("out:host.InstanceId",), "ssm", "describe-instance-information",
            lambda r: ["--filters", f"Key=InstanceIds,Values={r('out:host.InstanceId')}"], needs_host=True),
    # --- Group 2: IAM (R5) ---
    _single("runtime-role", ("DC-09", "DC-12", "DC-13"), ("out:iam.RuntimeRoleName",), "iam", "get-role",
            lambda r: ["--role-name", r("out:iam.RuntimeRoleName")]),
    _single("runtime-role-attached", ("DC-09", "DC-11"), ("out:iam.RuntimeRoleName",), "iam",
            "list-attached-role-policies", lambda r: ["--role-name", r("out:iam.RuntimeRoleName")]),
    _single("runtime-role-inline", ("DC-09",), ("out:iam.RuntimeRoleName",), "iam", "list-role-policies",
            lambda r: ["--role-name", r("out:iam.RuntimeRoleName")]),
    _single("instance-profile", ("DC-09", "DC-14"), ("out:iam.InstanceProfileName",), "iam",
            "get-instance-profile", lambda r: ["--instance-profile-name", r("out:iam.InstanceProfileName")]),
    _single("local-policies", ("DC-10", "DC-11", "DC-12"), (), "iam", "get-account-authorization-details",
            lambda r: ["--filter", "LocalManagedPolicy"]),
    _single("boundary-policy", ("DC-12",), ("out:iam.PermissionBoundaryArn",), "iam", "get-policy",
            lambda r: ["--policy-arn", r("out:iam.PermissionBoundaryArn")]),
    _single("explicit-deny-policy", ("DC-11",), ("out:iam.ExplicitDenyPolicyArn",), "iam", "get-policy",
            lambda r: ["--policy-arn", r("out:iam.ExplicitDenyPolicyArn")]),
    _single("flow-logs-role", ("DC-08",), ("out:iam.FlowLogsRoleArn",), "iam", "get-role",
            lambda r: ["--role-name", _arn_name(r("out:iam.FlowLogsRoleArn"))]),
    _single("account-summary", ("DC-15",), (), "iam", "get-account-summary", lambda r: []),
    _single("users", ("DC-15",), (), "iam", "list-users", lambda r: []),
    Check(
        name="simulations",
        controls=("DC-10", "DC-11", "DC-12", "DC-16", "DC-17", "DC-19"),
        scope="global",
        uses=("out:iam.RuntimeRoleArn", "region", "account", "param:iam.InferenceProfileArns",
              "param:iam.FoundationModelArns", "out:audit.DeployBucketName", "out:audit.TrailBucketName",
              "out:secret.SecretArn", "out:kms.KeyArn", "input:bundle_object_key", "input:bundle_prefix",
              "input:deny_probe_global_profile_ids", "input:deny_probe_non_claude_model_ids",
              "input:deny_probe_other_profile_ids", "input:negative_region"),
        build=_simulations,
    ),
    # --- Group 3: Region (DC-40) ---
    _single("organization", ("DC-40",), (), "organizations", "describe-organization",
            lambda r: ["--query", "Organization.{Id:Id,Arn:Arn,FeatureSet:FeatureSet,"
                                  "MasterAccountId:MasterAccountId,AvailablePolicyTypes:AvailablePolicyTypes}"]),
    _single("scp-list", ("DC-40",), (), "organizations", "list-policies",
            lambda r: ["--filter", "SERVICE_CONTROL_POLICY"], expected=("AccessDeniedException",)),
    # --- Group 4: KMS (R6) ---
    _single("describe-key", ("DC-18",), ("out:kms.KeyArn",), "kms", "describe-key",
            lambda r: ["--key-id", r("out:kms.KeyArn")]),
    _single("rotation-status", ("DC-18",), ("out:kms.KeyArn",), "kms", "get-key-rotation-status",
            lambda r: ["--key-id", r("out:kms.KeyArn")]),
    _single("describe-by-alias", ("DC-18",), ("out:kms.KeyAliasName",), "kms", "describe-key",
            lambda r: ["--key-id", r("out:kms.KeyAliasName")]),
    _single("aliases-of-key", ("DC-18",), ("out:kms.KeyId",), "kms", "list-aliases",
            lambda r: ["--key-id", r("out:kms.KeyId")]),
    _single("key-policy", ("DC-19",), ("out:kms.KeyArn",), "kms", "get-key-policy",
            lambda r: ["--key-id", r("out:kms.KeyArn"), "--policy-name", "default"]),
    _single("key-grants", ("DC-19",), ("out:kms.KeyArn",), "kms", "list-grants",
            lambda r: ["--key-id", r("out:kms.KeyArn")]),
    # --- Group 5: Secrets Manager (R8) ---
    _single("describe-secret", ("DC-20", "DC-33", "DC-34", "DC-35"), ("out:secret.SecretArn",), "secretsmanager",
            "describe-secret", lambda r: ["--secret-id", r("out:secret.SecretArn")]),
    _single("version-ids", ("DC-20",), ("out:secret.SecretArn",), "secretsmanager", "list-secret-version-ids",
            lambda r: ["--secret-id", r("out:secret.SecretArn")]),
    _single("resource-policy", ("DC-21",), ("out:secret.SecretArn",), "secretsmanager", "get-resource-policy",
            lambda r: ["--secret-id", r("out:secret.SecretArn")]),
    # --- Group 6: CloudTrail (R7) ---
    _single("trail", ("DC-23", "DC-24"), ("out:audit.TrailArn",), "cloudtrail", "describe-trails",
            lambda r: ["--trail-name-list", r("out:audit.TrailArn")]),
    _single("trail-status", ("DC-23",), ("out:audit.TrailArn",), "cloudtrail", "get-trail-status",
            lambda r: ["--name", r("out:audit.TrailArn")]),
    _single("trail-event-selectors", ("DC-26",), ("out:audit.TrailArn",), "cloudtrail", "get-event-selectors",
            lambda r: ["--trail-name", r("out:audit.TrailArn")]),
    *_bucket_checks("trail-bucket", {"encryption": "DC-25", "public-access-block": "DC-25", "versioning": "DC-25",
                                     "ownership": "DC-25", "policy": "DC-25", "lifecycle": "DC-27"},
                    "out:audit.TrailBucketName"),
    *_bucket_checks("deploy-bucket", {"encryption": "DC-05", "public-access-block": "DC-05", "versioning": "DC-05",
                                      "ownership": "DC-05", "policy": "DC-05"},
                    "out:audit.DeployBucketName"),
    # --- Group 7: CloudWatch (R7) ---
    _single("invocation-logging", ("DC-28",), (), "bedrock", "get-model-invocation-logging-configuration",
            lambda r: []),
    _single("log-groups-bedrock", ("DC-29",), ("input:bedrock_log_group_prefix",), "logs", "describe-log-groups",
            lambda r: ["--log-group-name-prefix", r("input:bedrock_log_group_prefix")]),
    _single("log-groups", ("DC-30",), (), "logs", "describe-log-groups", lambda r: []),
    # --- Group 8: egress (R7) ---
    _single("flow-log", ("DC-08",), ("out:audit.FlowLogId",), "ec2", "describe-flow-logs",
            lambda r: ["--flow-log-ids", r("out:audit.FlowLogId")]),
    _single("flow-log-streams", ("DC-08",), ("out:audit.FlowLogGroupName",), "logs", "describe-log-streams",
            lambda r: ["--log-group-name", r("out:audit.FlowLogGroupName"), "--order-by", "LastEventTime",
                       "--descending", "--max-items", "10"]),
    # --- Group 9: models (R2) ---
    Check(
        name="inference-profiles",
        controls=("DC-36",),
        scope="region",
        uses=("param:iam.InferenceProfileArns",),
        build=lambda r: [
            _cmd(f"DC-36_inference-profile-{_arn_name(arn)}.json", "bedrock", "get-inference-profile",
                 "--inference-profile-identifier", arn)
            for arn in r.list("param:iam.InferenceProfileArns")
        ],
    ),
    # --- Host checks through SSM Run Command (points 4, 5, 16, 17, 19) ---
    _host("private-dns", ("DC-02",), "dc02_private_dns.sh", ("region", "input:dns_services"),
          lambda r: {"PO_REGION": r("region"), "PO_DNS_SERVICES": _words(r.list("input:dns_services"))}),
    _host("caller-identity", ("DC-14", "DC-09"), "dc14_caller_identity.sh", ("region", "out:iam.RuntimeRoleName",
          "out:iam.InstanceProfileArn"),
          lambda r: {"PO_REGION": r("region"), "PO_RUNTIME_ROLE_NAME": r("out:iam.RuntimeRoleName"),
                     "PO_INSTANCE_PROFILE_ARN": r("out:iam.InstanceProfileArn")}),
    _host("no-long-term-keys", ("DC-15",), "dc15_no_long_term_keys.sh",
          ("input:dc15_home_dirs", "input:dc15_env_files"),
          lambda r: {"PO_HOME_DIRS": _words(r.list("input:dc15_home_dirs")),
                     "PO_ENV_FILES": _words(r.list("input:dc15_env_files"))}),
    _host("negative-region", ("DC-17",), "dc17_negative_region.sh",
          ("input:negative_region", "param:secret.TransportModelId", "input:converse_test_string"),
          lambda r: {"PO_NEGATIVE_REGION": r("input:negative_region"),
                     "PO_MODEL_ID": r("param:secret.TransportModelId"),
                     "PO_TEST_STRING": r("input:converse_test_string")}),
    _host("no-claude-cli", ("DC-31",), "dc31_no_claude_cli.sh", ("input:dc15_home_dirs",),
          lambda r: {"PO_HOME_DIRS": _words(r.list("input:dc15_home_dirs"))}),
    _host("egress-blocked", ("DC-32",), "dc32_egress_blocked.sh", ("input:egress_probe_hosts",),
          lambda r: {"PO_EGRESS_HOSTS": _words(r.list("input:egress_probe_hosts"))}),
    _host("converse", ("DC-37", "DC-36"), "dc37_converse.sh",
          ("region", "param:secret.TransportModelId", "input:converse_test_string", "out:iam.RuntimeRoleName"),
          lambda r: {"PO_REGION": r("region"), "PO_MODEL_ID": r("param:secret.TransportModelId"),
                     "PO_TEST_STRING": r("input:converse_test_string"),
                     "PO_RUNTIME_ROLE_NAME": r("out:iam.RuntimeRoleName")}),
    _host("launcher-config", ("DC-33", "DC-34", "DC-35", "DC-21"), "dc33_35_launcher_config.sh",
          ("region", "out:secret.SecretName", "derived:secret.expected_sha256", "runtime:bundle_dir",
           "runtime:bundle_python", "runtime:config_keys"),
          lambda r: {"PO_REGION": r("region"), "PO_SECRET_ID": r("out:secret.SecretName"),
                     "PO_EXPECTED_SHA256": r("derived:secret.expected_sha256"),
                     "PO_BUNDLE_DIR": r("runtime:bundle_dir"), "PO_BUNDLE_PYTHON": r("runtime:bundle_python"),
                     "PO_CONFIG_KEYS": _words(r.list("runtime:config_keys"))},
          needs_runtime=("bundle_dir",)),
    _host("f7-presigned-put", ("DC-05", "DC-07"), "f7_presigned_put.sh", ("runtime:f7_url",),
          lambda r: {"PO_F7_URL": r("runtime:f7_url")}, needs_runtime=("f7_url",)),
    # --- After the host checks ---
    _single("converse-events", ("DC-26",), ("runtime:started_utc",), "cloudtrail", "lookup-events",
            lambda r: ["--lookup-attributes", "AttributeKey=EventName,AttributeValue=Converse",
                       "--start-time", r("runtime:started_utc"), "--max-results", "20"], after_host=True),
)

#: Register rows no command evidences, with the reason (point 7).
NON_COMMAND: dict[str, str] = {
    "DC-22": "NOT_APPLICABLE since R8 (R8-D14): no API-key secret exists",
    "DC-38": "a full DAG run under production configuration: R16, deferred per OD12",
    "DC-39": "document review: the AWS data processing terms of the account (console, AWS Artifact)",
}

_RUNTIME_REASONS: dict[str, str] = {
    "bundle_dir": "no host bundle directory given (--host-bundle-dir)",
    "f7_url": "no F7 presigned URL file given (--f7-url-file)",
}


def coverage_map() -> dict[str, list[str]]:
    """Control id -> the checks (or the non-command reason) that cover it."""
    covered: dict[str, list[str]] = {}
    for check in CHECKS:
        for control in check.controls:
            covered.setdefault(control, []).append(check.name)
    for control, reason in NON_COMMAND.items():
        covered.setdefault(control, []).append(f"non-command: {reason}")
    return covered


# ---------------------------------------------------------------------------
# Host scripts (points 4 and 16)
# ---------------------------------------------------------------------------


def host_script_text(name: str) -> str:
    """A host script with LF line endings, whatever the checkout wrote."""
    return (HOST_CHECKS_DIR / name).read_bytes().decode("utf-8").replace("\r\n", "\n")


def host_script_sha256(name: str) -> str:
    return hashlib.sha256(host_script_text(name).encode("utf-8")).hexdigest()


def host_commands(check: Check, env: Mapping[str, str]) -> list[str]:
    """The ``commands`` lines sent to ``AWS-RunShellScript``: exports, then the fixed script."""
    lines = []
    for key in sorted(env):
        lines.append(f"export {key}={shlex.quote(str(env[key]))}")
    lines += host_script_text(check.host_script or "").rstrip("\n").split("\n")
    return lines


# ---------------------------------------------------------------------------
# The output folder (points 6 and 20)
# ---------------------------------------------------------------------------


def _norm(path: Path) -> str:
    return os.path.normcase(os.path.normpath(str(path)))


def _is_within(child: Path, parent: Path) -> bool:
    c, p = _norm(child), _norm(parent)
    return c == p or c.startswith(p.rstrip(os.sep) + os.sep)


def resolve_output_dir(repo_root: Path, ticket: str, step: str, out: Optional[Path] = None,
                       *, must_not_exist: bool = True) -> Path:
    """The run folder, or :class:`CollectorRefused`. Never creates anything."""
    if not _TICKET.match(ticket):
        raise CollectorRefused(f"not a ticket id: {ticket!r}")
    if not _STEP.match(step):
        raise CollectorRefused(f"not a two-digit step: {step!r}")
    root = repo_root.resolve()
    v2 = (root / EVIDENCE_V2).resolve()
    expected = v2 / ticket / f"{ticket}_{step}_collector"
    target = expected if out is None else (out if out.is_absolute() else root / out)
    resolved = target.resolve()
    for v1 in V1_PATHS:
        if _is_within(resolved, (root / v1).resolve()):
            raise CollectorRefused(f"refused: {target.as_posix()} is inside the v1 evidence tree ({v1.as_posix()})")
    if not _is_within(resolved, v2) or _norm(resolved) == _norm(v2):
        raise CollectorRefused(f"refused: {target.as_posix()} is outside {EVIDENCE_V2.as_posix()}/")
    if _norm(resolved) != _norm(expected):
        rel = expected.relative_to(root).as_posix()
        raise CollectorRefused(f"refused: the output folder must be {rel}")
    if not resolved.parent.is_dir():
        raise CollectorRefused(f"refused: the ticket folder {resolved.parent.relative_to(root).as_posix()} does not exist")
    if must_not_exist and (resolved.exists() or resolved.is_symlink()):
        raise CollectorRefused(f"refused: {resolved.relative_to(root).as_posix()} exists; a run never overwrites")
    return resolved


# ---------------------------------------------------------------------------
# Running (points 1, 3, 4 and 10)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RunResult:
    returncode: int
    stdout: str
    stderr: str


Runner = Callable[[Sequence[str]], RunResult]


def subprocess_runner(aws_executable: str = "aws") -> Runner:
    """The real runner: the AWS CLI, argv only, no shell."""
    resolved = shutil.which(aws_executable) or aws_executable

    def run(argv: Sequence[str]) -> RunResult:
        command = [resolved, *argv[1:]]
        completed = subprocess.run(  # noqa: S603 - argv built from checked values, no shell
            command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
        )
        return RunResult(completed.returncode, completed.stdout, completed.stderr)

    return run


def _error_code(result: RunResult) -> Optional[str]:
    match = _AWS_ERROR.search(result.stderr or "")
    return match.group(1) if match else None


@dataclass
class Outcome:
    check: str
    file: str
    controls: tuple[str, ...]
    scope: str
    status: str  # collected, expected_error, not_collected, error
    reason: str = ""
    script_sha256: str = ""
    host_result: str = ""
    command: str = ""


@dataclass
class Config:
    ticket: str
    step: str
    profile: str
    sources: Sources = field(default_factory=Sources)
    out: Optional[Path] = None
    bundle_dir: Optional[str] = None
    bundle_python: str = "python3"
    f7_url: Optional[str] = None
    host_timeout: float = 180.0
    poll_interval: float = 5.0
    plan: bool = False


def _runtime_values(cfg: Config, started_utc: str) -> dict[str, Any]:
    from runner import host_env

    values: dict[str, Any] = {
        "started_utc": started_utc,
        "bundle_python": cfg.bundle_python,
        "config_keys": list(host_env.CONFIG_KEYS),
    }
    if cfg.bundle_dir is not None:
        values["bundle_dir"] = cfg.bundle_dir
    if cfg.f7_url is not None:
        values["f7_url"] = cfg.f7_url
    return values


def _validate_runtime(cfg: Config) -> None:
    if not _PROFILE.match(cfg.profile):
        raise CollectorRefused("not a profile name")
    if cfg.bundle_dir is not None and not _HOST_PATH.match(cfg.bundle_dir):
        raise CollectorRefused("--host-bundle-dir must be an absolute host path")
    if not (_HOST_PATH.match(cfg.bundle_python) or re.fullmatch(r"python3(\.\d+)?", cfg.bundle_python)):
        raise CollectorRefused("--host-bundle-python must be python3 or an absolute host path")
    if cfg.f7_url is not None and not _F7_URL.match(cfg.f7_url):
        raise CollectorRefused("the F7 file does not hold one https S3 URL")


def _skip_reason(check: Check, ctx: Context) -> Optional[str]:
    if check.needs_host and not ctx.host_present:
        return "host stack outputs absent (--host-outputs)"
    for name in check.needs_runtime:
        if f"runtime:{name}" not in ctx.refs:
            return _RUNTIME_REASONS[name]
    return None


def _mask(text: str, ctx: Context) -> str:
    url = ctx.refs.get("runtime:f7_url")
    return text.replace(url, "<f7-url>") if url else text


def _write(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text if text.endswith("\n") else text + "\n")


def _error_text(result: RunResult) -> str:
    return f"exit={result.returncode}\n{(result.stderr or '').strip()}\n"


class Collector:
    def __init__(self, cfg: Config, runner: Runner, clock: Callable[[], datetime], sleep: Callable[[float], None],
                 echo: Callable[[str], None]) -> None:
        self.cfg = cfg
        self.runner = runner
        self.clock = clock
        self.sleep = sleep
        self.echo = echo

    # -- helpers --

    def _aws(self, ctx: Context, command: Command) -> RunResult:
        return self.runner(command.argv(ctx, self.cfg.profile))

    def _preflight(self, ctx: Context) -> list[tuple[str, str]]:
        """Caller account and stack outputs, compared before collecting (points 2, 3)."""
        files: list[tuple[str, str]] = []
        caller = self._aws(ctx, _cmd("", "sts", "get-caller-identity"))
        if caller.returncode != 0:
            raise CollectorRefused(f"sts get-caller-identity failed: {_error_code(caller) or caller.returncode}")
        if str(json.loads(caller.stdout).get("Account")) != ctx.account:
            raise CollectorRefused("refused: the caller's account is not ExpectedAccountId")
        files.append(("00_caller-identity.json", caller.stdout))
        for stack in ctx.stacks:
            if stack.get("lifecycle") == "per_session" and not ctx.host_present:
                continue
            result = self._aws(ctx, _cmd("", "cloudformation", "describe-stacks", "--stack-name",
                                         stack["stack_name"], "--query", "Stacks[0].Outputs"))
            if result.returncode != 0:
                raise CollectorRefused(
                    f"refused: stack {stack['stack_name']} could not be read ({_error_code(result) or result.returncode});"
                    " its outputs file is stale"
                )
            live = {str(e["OutputKey"]): str(e["OutputValue"]) for e in json.loads(result.stdout) or []}
            saved = {name.split(".", 1)[1]: value for name, value in ctx.refs.items()
                     if name.startswith(f"out:{stack['key']}.")}
            if live != saved:
                raise CollectorRefused(
                    f"refused: the live outputs of {stack['stack_name']} differ from its outputs file (stale)"
                )
            files.append((f"00_stack-outputs-{stack['key']}.json", result.stdout))
        return files

    def _run_command(self, ctx: Context, check: Check, command: Command, folder: Path) -> Outcome:
        result = self._aws(ctx, command)
        shown = " ".join(command.argv(ctx, self.cfg.profile))
        if result.returncode == 0:
            _write(folder / command.file, result.stdout)
            return Outcome(check.name, command.file, check.controls, check.scope, "collected", command=shown)
        code = _error_code(result)
        file = command.file.rsplit(".", 1)[0] + ".txt"
        _write(folder / file, _error_text(result))
        if code is not None and code in command.expected_errors:
            return Outcome(check.name, file, check.controls, check.scope, "expected_error", reason=code, command=shown)
        return Outcome(check.name, file, check.controls, check.scope, "error",
                       reason=code or f"exit {result.returncode}", command=shown)

    def _run_host(self, ctx: Context, check: Check, folder: Path) -> Outcome:
        refs = Refs(ctx, check.uses)
        instance = refs("out:host.InstanceId")
        env = check.host_env(refs) if check.host_env else {}
        parameters = json.dumps({"commands": host_commands(check, env), "executionTimeout": ["120"]})
        file = f"{check.controls[0]}_host-{check.name}.json"
        sha = host_script_sha256(check.host_script or "")
        send = _cmd(file, "ssm", "send-command", "--instance-ids", instance, "--document-name", "AWS-RunShellScript",
                    "--comment", f"{self.cfg.ticket} collector {check.name}", "--timeout-seconds", "60",
                    "--parameters", parameters, "--query", "Command.CommandId")
        sent = self._aws(ctx, send)
        if sent.returncode != 0:
            text_file = file[:-5] + ".txt"
            _write(folder / text_file, _mask(_error_text(sent), ctx))
            return Outcome(check.name, text_file, check.controls, "host", "error",
                           reason=f"send-command: {_error_code(sent) or sent.returncode}", script_sha256=sha)
        command_id = str(json.loads(sent.stdout))
        poll = _cmd(file, "ssm", "get-command-invocation", "--command-id", command_id, "--instance-id", instance)
        waited = 0.0
        while True:
            result = self._aws(ctx, poll)
            if result.returncode == 0:
                status = str(json.loads(result.stdout).get("Status"))
                if status in _SSM_TERMINAL:
                    break
            elif _error_code(result) not in _SSM_PENDING_ERRORS:
                break
            if waited >= self.cfg.host_timeout:
                break
            self.sleep(self.cfg.poll_interval)
            waited += self.cfg.poll_interval
        if result.returncode != 0:
            text_file = file[:-5] + ".txt"
            _write(folder / text_file, _mask(_error_text(result), ctx))
            return Outcome(check.name, text_file, check.controls, "host", "error",
                           reason=f"get-command-invocation: {_error_code(result) or result.returncode}",
                           script_sha256=sha)
        _write(folder / file, result.stdout)
        answer = json.loads(result.stdout)
        status = str(answer.get("Status"))
        host_result = ""
        for line in str(answer.get("StandardOutputContent") or "").splitlines():
            if line.startswith("RESULT="):
                host_result = line.split("=", 1)[1].strip()
        if status != "Success":
            return Outcome(check.name, file, check.controls, "host", "error", reason=f"invocation {status}",
                           script_sha256=sha, host_result=host_result)
        return Outcome(check.name, file, check.controls, "host", "collected", script_sha256=sha,
                       host_result=host_result)

    # -- plan and run --

    def planned(self, ctx: Context) -> list[tuple[Check, Optional[list[Command]], Optional[str]]]:
        rows = []
        ordered = [c for c in CHECKS if c.scope != "host" and not c.after_host]
        ordered += [c for c in CHECKS if c.scope == "host"]
        ordered += [c for c in CHECKS if c.after_host]
        for check in ordered:
            reason = _skip_reason(check, ctx)
            if reason is not None:
                rows.append((check, None, reason))
            elif check.build is not None:
                rows.append((check, check.build(Refs(ctx, check.uses)), None))
            else:
                rows.append((check, [], None))
        return rows

    def plan(self, ctx: Context) -> int:
        for check, commands, reason in self.planned(ctx):
            if reason is not None:
                self.echo(f"[{check.name}] not collected: {reason}")
            elif check.scope == "host":
                env = check.host_env(Refs(ctx, check.uses)) if check.host_env else {}
                shown = " ".join(f"{k}={shlex.quote(v)}" for k, v in sorted(env.items()))
                self.echo(_mask(f"[{check.name}] host {check.host_script} "
                                f"sha256={host_script_sha256(check.host_script or '')} {shown}", ctx))
            else:
                for command in commands or []:
                    self.echo(_mask(f"[{check.name}] {command.file}: "
                                    + " ".join(command.argv(ctx, self.cfg.profile)), ctx))
        return EXIT_OK

    def run(self, ctx: Context, folder: Path) -> int:
        planned = self.planned(ctx)  # builds every command before any AWS call
        preflight = self._preflight(ctx)
        folder.mkdir()
        for name, text in preflight:
            _write(folder / name, text)
        outcomes: list[Outcome] = []
        for check, commands, reason in planned:
            if reason is not None:
                outcomes.append(Outcome(check.name, "", check.controls, check.scope, "not_collected", reason=reason))
            elif check.scope == "host":
                outcomes.append(self._run_host(ctx, check, folder))
            else:
                for command in commands or []:
                    outcomes.append(self._run_command(ctx, check, command, folder))
        for outcome in outcomes:
            detail = f" ({outcome.reason})" if outcome.reason else ""
            self.echo(f"{outcome.status:15} {outcome.check} {outcome.file}{detail}")
        _write(folder / SUMMARY_NAME, json.dumps(self._summary(ctx, outcomes), indent=2, ensure_ascii=False))
        _write_manifest(folder)
        failed = any(o.status == "error" for o in outcomes)
        if not _scans_clean(folder, self.echo):
            failed = True
        counts = {s: sum(1 for o in outcomes if o.status == s)
                  for s in ("collected", "expected_error", "not_collected", "error")}
        self.echo("summary: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
        return EXIT_FAILED if failed else EXIT_OK

    def _summary(self, ctx: Context, outcomes: list[Outcome]) -> dict[str, Any]:
        controls: dict[str, dict[str, Any]] = {}
        for control, covered in sorted(coverage_map().items()):
            mine = [o for o in outcomes if control in o.controls]
            if not mine:
                controls[control] = {"status": "non_command", "reason": NON_COMMAND.get(control, "")}
                continue
            statuses = {o.status for o in mine}
            if "error" in statuses:
                status = "error"
            elif statuses == {"not_collected"}:
                status = "not_collected"
            elif "not_collected" in statuses:
                status = "partial"
            else:
                status = "collected"
            controls[control] = {"status": status, "files": sorted({o.file for o in mine if o.file})}
        root = self.cfg.sources.repo_root.resolve()

        def shown(path: Path) -> str:
            resolved = path.resolve()
            return resolved.relative_to(root).as_posix() if _is_within(resolved, root) else path.as_posix()

        return {
            "schema": "proposal-orchestrator-collector-summary/1",
            "ticket": self.cfg.ticket,
            "step": self.cfg.step,
            "account": ctx.account,
            "region": ctx.region,
            "started_utc": ctx.refs["runtime:started_utc"],
            "finished_utc": _utc(self.clock()),
            "collector_sha256": _lf_sha256(Path(__file__)),
            "inputs_sha256": {name: {"path": shown(p), "sha256": _lf_sha256(p)}
                              for name, p in sorted(ctx.files_read.items())},
            "host_stack": "present" if ctx.host_present else "absent",
            "checks": [o.__dict__ | {"controls": list(o.controls), "command": _mask(o.command, ctx)}
                       for o in outcomes],
            "controls": controls,
        }


def _utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _lf_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _write_manifest(folder: Path) -> None:
    lines = []
    for path in sorted(p for p in folder.iterdir() if p.is_file() and p.name != MANIFEST_NAME):
        lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    _write(folder / MANIFEST_NAME, "\n".join(lines))


def _scans_clean(folder: Path, echo: Callable[[str], None]) -> bool:
    """The secret scan and the old-ID guard over the run folder (point 10). Nothing is edited."""
    from tools import evidence_secret_scan, old_id_guard

    secrets = evidence_secret_scan.scan_folder(folder)
    old_ids = old_id_guard.scan_paths([folder])
    for finding in secrets:
        echo("SECRET SCAN: " + finding.describe(folder))
    for finding in old_ids:
        echo("OLD-ID GUARD: " + finding.describe(folder))
    if secrets or old_ids:
        echo("REFUSED: the run folder has findings. Re-collect; do not edit the files.")
        return False
    return True


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None, *, runner: Optional[Runner] = None,
         clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
         sleep: Callable[[float], None] = time.sleep, echo: Callable[[str], None] = print) -> int:
    parser = argparse.ArgumentParser(prog="collect_evidence_v2", description=__doc__.split("\n\n")[0])
    parser.add_argument("--ticket", required=True, help="ticket id, e.g. R12b")
    parser.add_argument("--step", required=True, help="two-digit step number of the step sheet")
    parser.add_argument("--profile", required=True, help="AWS CLI profile")
    parser.add_argument("--out", type=Path, default=None, help="run folder (default: derived; any other is refused)")
    parser.add_argument("--host-outputs", type=Path, nargs="?", const=CONTRACT_DEFAULT, default=None,
                        help="the host stack's outputs file; without a path, the contract's (R11_outputs.json)")
    parser.add_argument("--host-bundle-dir", default=None, help="the orchestrator bundle on the host (DC-33 to DC-35)")
    parser.add_argument("--host-bundle-python", default="python3", help="the bundle's interpreter on the host")
    parser.add_argument("--f7-url-file", type=Path, default=None, help="file holding one presigned PUT URL (F7)")
    parser.add_argument("--host-timeout", type=float, default=180.0, help="seconds to wait for each host check")
    parser.add_argument("--plan", action="store_true", help="print the commands; call nothing, write nothing")
    parser.add_argument("--aws-executable", default="aws")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--source-root", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--contract", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--parameters-dir", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--outputs-root", type=Path, default=None, help=argparse.SUPPRESS)
    parser.add_argument("--inputs", type=Path, default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    sources = Sources(
        repo_root=args.repo_root,
        source_root=args.source_root or args.repo_root,
        contract=args.contract,
        parameters_dir=args.parameters_dir,
        outputs_root=args.outputs_root,
        inputs=args.inputs,
        host_outputs=args.host_outputs,
    )
    try:
        folder = resolve_output_dir(args.repo_root, args.ticket, args.step, args.out, must_not_exist=not args.plan)
        f7_url = None
        if args.f7_url_file is not None:
            try:
                f7_url = args.f7_url_file.read_text(encoding="utf-8-sig").strip()
            except OSError:
                raise CollectorRefused("the F7 URL file cannot be read") from None
        cfg = Config(ticket=args.ticket, step=args.step, profile=args.profile, sources=sources, out=args.out,
                     bundle_dir=args.host_bundle_dir, bundle_python=args.host_bundle_python, f7_url=f7_url,
                     host_timeout=args.host_timeout, plan=args.plan)
        _validate_runtime(cfg)
        ctx = load_context(sources, _runtime_values(cfg, _utc(clock())))
        collector = Collector(cfg, runner or subprocess_runner(args.aws_executable), clock, sleep, echo)
        if args.plan:
            return collector.plan(ctx)
        return collector.run(ctx, folder)
    except CollectorRefused as exc:
        echo(f"REFUSED: {exc}")
        return EXIT_REFUSED


if __name__ == "__main__":
    sys.exit(main())
