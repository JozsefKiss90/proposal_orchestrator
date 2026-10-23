"""Old-account id guard for the AWS redeployment (ticket R3).

Ticket R3 of ``plans/aws_redeployment_tickets.md``. The constraint every ticket
inherits is that no id from the old account appears in a resource name or
policy (``plans/aws_redeployment_handoff_2026-10-21.md`` §7). This check greps
the new infrastructure and the new evidence for the dead ids listed in that
handoff's §9 old-to-new map, plus the old security-group rule its F7 names.

It matches each old id **exactly**, never by prefix: the v2 evidence
legitimately holds new-account ids of the same shape (for example the
eu-north-1 default VPC and a deleted security group recorded in R1).

The default scope is the v2 side of the work only:

- ``deploy/aws/`` (templates, parameters, contract, README);
- ``docs/infrastructure_security/evidence_v2/``;
- control register v2 and worklog v2;
- the ``aws-redeployment-*`` records in the Tier 4 decision log.

The v1 tree (``evidence/``, ``audit_package/``, register and worklog v1), the
old deployment guide (rewritten in R13) and ``plans/`` (whose handoffs list
the old ids on purpose) are out of scope. Other paths can be passed
explicitly; R12a runs the guard over its evidence collector that way, and R13
over the amended documents.

The old ids are assembled at import time from fragments, so that this file is
never itself a finding when it is passed to the guard. A finding reports the
file, the line and the label of the old id, never the id itself, so that a
guard run saved as evidence does not plant the id in the evidence tree.

Usage::

    py -3.10 -m tools.old_id_guard                 # the default scope
    py -3.10 -m tools.old_id_guard deploy/aws tools/collect_evidence_v2.py

Exit status: 0 when every path is clean, 1 when an old id is found, 2 when a
path (or a default-scope entry) does not exist.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

from tools.evidence_secret_scan import _normalised_bytes


def _j(*parts: str) -> str:
    return "".join(parts)


# Label -> old id. The labels are what a finding reports.
OLD_IDS: dict[str, str] = {
    "old account": _j("2325", "3855", "1827"),
    "old VPC": _j("vpc-", "050a0977", "4560fd774"),
    "old subnet 1": _j("subnet-", "023c6e3e", "a5451ea47"),
    "old subnet 2": _j("subnet-", "01d969bb", "1421a3042"),
    "old route table": _j("rtb-", "085481996", "de5e3ed9"),
    "old host security group": _j("sg-", "076f724a", "ed2429771"),
    "old endpoint security group": _j("sg-", "013d5e4d", "4eb55dfd9"),
    "old host SG rule (F7)": _j("sgr-", "0cc4c711", "2cd8277c2"),
    "old us-east-1 S3 prefix list": _j("pl-", "63a5", "400a"),
    "old bedrock-runtime endpoint": _j("vpce-", "0843d225", "c5b1ef6d5"),
    "old secretsmanager endpoint": _j("vpce-", "08ba482a", "3b11f7d64"),
    "old sts endpoint": _j("vpce-", "067abd50", "0c89e2bc4"),
    "old s3 endpoint": _j("vpce-", "0ee5648c", "e182bf85a"),
    "old ssm endpoint": _j("vpce-", "06a268f5", "4ecc1f754"),
    "old ssmmessages endpoint": _j("vpce-", "0824e9fb", "b2f099e37"),
    "old ec2messages endpoint": _j("vpce-", "0ec79b44", "974bfd85b"),
    "old flow log 1": _j("fl-", "03c1ed4c", "967c50073"),
    "old flow log 2": _j("fl-", "0948b876", "901308e70"),
    "old KMS key": _j("887638e8", "-358b-4664-", "9270-368aec0ea1f1"),
    "old host": _j("i-", "0045af36", "dbf5f1272"),
}

_OLD_ID_BYTES: dict[str, bytes] = {label: value.encode("ascii") for label, value in OLD_IDS.items()}

# Repository-relative default scope. A glob entry must match at least one file.
DEFAULT_SCOPE: tuple[str, ...] = (
    "deploy/aws",
    "docs/infrastructure_security/evidence_v2",
    "docs/infrastructure_security/aws_hardening_control_register_v2.md",
    "docs/infrastructure_security/aws_hardening_worklog_v2.md",
    "docs/tier4_orchestration_state/decision_log/aws-redeployment-*.json",
)


@dataclass(frozen=True)
class Finding:
    """One old id on one line of one file."""

    path: Path
    line: int
    label: str

    def describe(self, root: Optional[Path] = None) -> str:
        shown = self.path
        if root is not None:
            try:
                shown = self.path.relative_to(root)
            except ValueError:
                pass
        return f"{shown.as_posix()}:{self.line}: {self.label}"


def scan_file(path: Path) -> list[Finding]:
    """Return every old id in *path*, in line order."""
    findings: list[Finding] = []
    data = _normalised_bytes(path)
    for number, line in enumerate(data.splitlines(), start=1):
        for label, needle in _OLD_ID_BYTES.items():
            if needle in line:
                findings.append(Finding(path=path, line=number, label=label))
    return findings


def _files_under(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return sorted(p for p in path.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    raise FileNotFoundError(f"path not found: {path}")


def scan_paths(paths: Iterable[Path]) -> list[Finding]:
    """Return every finding under *paths* (files or folders), sorted by path.

    Raises ``FileNotFoundError`` for a path that does not exist, so that a
    mistyped path is never reported as clean.
    """
    findings: list[Finding] = []
    for path in paths:
        for file in _files_under(path):
            findings.extend(scan_file(file))
    return sorted(findings, key=lambda f: (f.path.as_posix(), f.line, f.label))


def default_scope(root: Path) -> list[Path]:
    """Resolve :data:`DEFAULT_SCOPE` against *root* (the repository root)."""
    resolved: list[Path] = []
    for entry in DEFAULT_SCOPE:
        if any(ch in entry for ch in "*?["):
            matches = sorted(root.glob(entry))
            if not matches:
                raise FileNotFoundError(f"default-scope glob matched nothing: {entry}")
            resolved.extend(matches)
        else:
            path = root / entry
            if not path.exists():
                raise FileNotFoundError(f"default-scope path not found: {entry}")
            resolved.append(path)
    return resolved


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="old_id_guard",
        description="Refuse files that contain an id of the old AWS account.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="files or folders to scan (default: the v2 scope, relative to the current directory)",
    )
    args = parser.parse_args(argv)

    root = Path.cwd()
    try:
        paths = list(args.paths) if args.paths else default_scope(root)
        findings = scan_paths(paths)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    shown = ", ".join(p.as_posix() for p in args.paths) if args.paths else "default v2 scope"
    if not findings:
        print(f"CLEAN: no old-account id in {shown} ({len(OLD_IDS)} ids checked)")
        return 0
    for finding in findings:
        print(finding.describe(root))
    print(f"REFUSED: {len(findings)} old-account id(s) in {shown}.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
