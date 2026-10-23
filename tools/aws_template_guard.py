"""Parsed-template guard for the CloudFormation templates (ticket R3).

Ticket R3 of ``plans/aws_redeployment_tickets.md``. ``cfn-lint`` checks that a
template is valid CloudFormation; this guard checks that it keeps the
redeployment's own rules (``plans/aws_redeployment_handoff_2026-10-21.md`` §7,
F3, F9; tickets R4 and R5). It runs with ``py -3.10`` and only ``pyyaml``, so
the test suite does not depend on the lint virtual environment.

Checks, each reported under its name:

``forbidden-type``
    No Internet Gateway, egress-only Internet Gateway, NAT Gateway, Elastic
    IP or gateway attachment (ADR-001 D2, D7, D8).
``open-cidr``
    No ``0.0.0.0/0`` or ``::/0`` anywhere in the template: no such route and
    no such security-group rule, not even temporarily.
``project-tag``
    Every resource whose type takes tags carries ``project`` =
    ``proposal-orchestrator`` (literally or as ``!Ref ProjectName``). The
    types that take no tags are listed in :data:`UNTAGGABLE_TYPES`; a type is
    added there only after checking its CloudFormation reference page.
``forbidden-word``
    No logical id, name or description contains "temporary" or "validation"
    (ticket R5; the old programme left ``validation-*`` policies behind).
    Property *keys* such as ``EnableLogFileValidation`` are not names and are
    not checked.
``region-literal``
    No Region name except as a parameter default (F9).
``account-literal``
    No 12-digit account id anywhere; account ids come from
    ``AWS::AccountId`` or a parameter value.
``size``
    The template fits ``--template-body`` (51,200 bytes), since no staging
    bucket exists before R7.

Usage::

    py -3.10 -m tools.aws_template_guard deploy/aws/templates

Exit status: 0 when every template is clean, 1 when a check fails, 2 when a
path does not exist, holds no template, or a template does not parse.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional, Sequence

import yaml

TEMPLATE_BODY_LIMIT = 51_200
PROJECT_TAG_KEY = "project"
PROJECT_TAG_VALUE = "proposal-orchestrator"

FORBIDDEN_RESOURCE_TYPES = frozenset(
    {
        "AWS::EC2::InternetGateway",
        "AWS::EC2::EgressOnlyInternetGateway",
        "AWS::EC2::NatGateway",
        "AWS::EC2::EIP",
        "AWS::EC2::VPCGatewayAttachment",
    }
)

# Resource types that have no Tags property in CloudFormation.
UNTAGGABLE_TYPES = frozenset(
    {
        "AWS::CloudFormation::WaitConditionHandle",
        "AWS::EC2::SecurityGroupEgress",
        "AWS::EC2::SecurityGroupIngress",
        "AWS::EC2::SubnetRouteTableAssociation",
        "AWS::KMS::Alias",
        "AWS::S3::BucketPolicy",
        "AWS::SecretsManager::ResourcePolicy",
    }
)

_OPEN_CIDRS = ("0.0.0.0/0", "::/0")
_FORBIDDEN_WORD = re.compile(r"temporar|validation", re.IGNORECASE)
_REGION = re.compile(
    r"(?<![a-z0-9-])(?:af|ap|ca|cn|eu|il|me|mx|sa|us)(?:-gov)?-"
    r"(?:north|south|east|west|central|northeast|northwest|southeast|southwest)-[0-9](?![0-9])"
)
_ACCOUNT = re.compile(r"(?<![0-9])[0-9]{12}(?![0-9])")


# --- loading ------------------------------------------------------------------


class CfnLoader(yaml.SafeLoader):
    """A safe YAML loader that understands CloudFormation short-form intrinsics."""


def _construct_intrinsic(loader: CfnLoader, suffix: str, node: yaml.Node) -> dict[str, Any]:
    if isinstance(node, yaml.ScalarNode):
        value: Any = loader.construct_scalar(node)
    elif isinstance(node, yaml.SequenceNode):
        value = loader.construct_sequence(node, deep=True)
    else:
        value = loader.construct_mapping(node, deep=True)
    if suffix in ("Ref", "Condition"):
        return {suffix: value}
    if suffix == "GetAtt" and isinstance(value, str):
        value = value.split(".", 1)
    return {f"Fn::{suffix}": value}


CfnLoader.add_multi_constructor("!", _construct_intrinsic)


def load_template(path: Path) -> dict[str, Any]:
    """Parse a YAML or JSON template, short-form intrinsics included."""
    data = yaml.load(path.read_text(encoding="utf-8"), Loader=CfnLoader)  # noqa: S506 - SafeLoader subclass
    if not isinstance(data, dict):
        raise ValueError(f"not a CloudFormation template: {path}")
    return data


# --- findings -----------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """One failed check at one place in one template."""

    path: Path
    check: str
    where: str

    def describe(self) -> str:
        return f"{self.path.as_posix()}: {self.check} at {self.where}"


def _walk(node: Any, trail: tuple[str, ...] = ()) -> Iterator[tuple[tuple[str, ...], Any]]:
    """Yield (trail, value) for every key (as itself) and every scalar."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield trail + (str(key),), str(key)
            yield from _walk(value, trail + (str(key),))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk(value, trail + (f"[{index}]",))
    elif node is not None:
        yield trail, node


def _where(trail: tuple[str, ...]) -> str:
    return ".".join(trail) or "<root>"


def _is_parameter_default(trail: tuple[str, ...]) -> bool:
    return len(trail) == 3 and trail[0] == "Parameters" and trail[2] == "Default"


def _names_and_descriptions(template: dict[str, Any]) -> Iterator[tuple[tuple[str, ...], str]]:
    """Logical ids, and every value under a key that names or describes something."""
    if isinstance(template.get("Description"), str):
        yield ("Description",), template["Description"]
    for section in ("Parameters", "Resources", "Outputs"):
        entries = template.get(section) or {}
        for logical_id, body in entries.items():
            yield (section, str(logical_id)), str(logical_id)
            for trail, value in _walk(body, (section, str(logical_id))):
                key = trail[-1]
                is_key = value == key
                named = key.endswith("Name") or key == "Description"
                tag_value = len(trail) >= 2 and key == "Value" and "Tags" in trail
                if not is_key and isinstance(value, str) and (named or tag_value):
                    yield trail, value
                elif not is_key and isinstance(value, str) and len(trail) >= 2 and trail[-2].endswith("Name"):
                    yield trail, value  # e.g. RoleName: !Sub "..."


def _has_project_tag(tags: Any) -> bool:
    accepted = (PROJECT_TAG_VALUE, {"Ref": "ProjectName"})
    if isinstance(tags, list):
        return any(
            isinstance(tag, dict) and tag.get("Key") == PROJECT_TAG_KEY and tag.get("Value") in accepted
            for tag in tags
        )
    if isinstance(tags, dict):  # map-shaped Tags (some resource types)
        return tags.get(PROJECT_TAG_KEY) in accepted
    return False


def check_template(path: Path) -> list[Finding]:
    """Run every check on one template file."""
    findings: list[Finding] = []

    def add(check: str, trail: tuple[str, ...]) -> None:
        findings.append(Finding(path=path, check=check, where=_where(trail)))

    if path.stat().st_size > TEMPLATE_BODY_LIMIT:
        add("size", ())

    template = load_template(path)
    resources = template.get("Resources") or {}

    for logical_id, resource in resources.items():
        rtype = (resource or {}).get("Type", "")
        if rtype in FORBIDDEN_RESOURCE_TYPES:
            add("forbidden-type", ("Resources", str(logical_id), "Type"))
        if rtype not in UNTAGGABLE_TYPES:
            tags = ((resource or {}).get("Properties") or {}).get("Tags")
            if not _has_project_tag(tags):
                add("project-tag", ("Resources", str(logical_id)))

    for trail, value in _walk(template):
        if not isinstance(value, str):
            value = str(value)
        if any(cidr in value for cidr in _OPEN_CIDRS):
            add("open-cidr", trail)
        if _REGION.search(value) and not _is_parameter_default(trail):
            add("region-literal", trail)
        if _ACCOUNT.search(value):
            add("account-literal", trail)

    for trail, value in _names_and_descriptions(template):
        if _FORBIDDEN_WORD.search(value):
            add("forbidden-word", trail)

    # A value can be reached twice (as a key and as a scalar); report once.
    unique = {(f.check, f.where): f for f in findings}
    return sorted(unique.values(), key=lambda f: (f.check, f.where))


def template_files(paths: Sequence[Path]) -> list[Path]:
    """The ``.yaml``, ``.yml`` and ``.json`` files under *paths*."""
    files: list[Path] = []
    for path in paths:
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(p for p in path.rglob("*") if p.suffix in (".yaml", ".yml", ".json")))
        else:
            raise FileNotFoundError(f"path not found: {path}")
    if not files:
        raise FileNotFoundError("no template found under: " + ", ".join(p.as_posix() for p in paths))
    return files


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aws_template_guard",
        description="Check CloudFormation templates against the redeployment's own rules.",
    )
    parser.add_argument("paths", nargs="+", type=Path, help="template files or folders")
    args = parser.parse_args(argv)

    try:
        files = template_files(args.paths)
        findings = [finding for file in files for finding in check_template(file)]
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not findings:
        print(f"CLEAN: {len(files)} template(s): " + ", ".join(f.as_posix() for f in files))
        return 0
    for finding in findings:
        print(finding.describe())
    print(f"REFUSED: {len(findings)} finding(s) in {len(files)} template(s).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
