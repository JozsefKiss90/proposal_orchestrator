"""Secret scan for an AWS redeployment evidence folder (ticket E0).

Ticket E0 of ``plans/aws_redeployment_tickets.md``, implementing the refusal
step of the handoff's §7a evidence protocol
(``plans/aws_redeployment_handoff_2026-10-21.md``). Before the agent accepts
the evidence an operator saved for a ticket, it runs this check over the
ticket's folder under ``docs/infrastructure_security/evidence_v2/``. A folder
with any finding is refused, and the operator re-collects the evidence. A
finding is never fixed by editing the evidence file.

The four patterns are the ones the protocol names. ``AKIA`` (the prefix of a
long-term access key id) is matched case-sensitively, so that ordinary words
such as "Slovakia" are not refused. The other three are matched without
regard to case, so that ``AWS_SECRET_ACCESS_KEY`` and ``sessiontoken`` are
caught as well.

Every file under the folder is read as bytes, whatever its extension, so a
pasted ``.txt`` or a ``.md`` run log is scanned like a ``.json`` export. A
file that starts with a UTF-16 byte-order mark is decoded first: Windows
PowerShell 5.1 writes UTF-16 when output is redirected with ``>``, and a byte
match would miss a pattern whose characters are interleaved with zero bytes.
Screenshots are scanned too; they are expected to be clean as bytes, and the
operator still checks them by eye.

A finding reports the file, the line number and the pattern name, never the
matching text, so that running the check does not copy a leaked value into a
console, a log or a session transcript.

Usage::

    py -3.10 -m tools.evidence_secret_scan docs/infrastructure_security/evidence_v2/R4

Exit status: 0 when the folder is clean, 1 when it is refused, 2 when the
folder does not exist.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

# Name -> compiled pattern. The names are what a finding reports.
FORBIDDEN_PATTERNS: dict[str, re.Pattern[bytes]] = {
    "AKIA": re.compile(rb"AKIA"),
    "aws_secret": re.compile(rb"aws_secret", re.IGNORECASE),
    "SecretString": re.compile(rb"SecretString", re.IGNORECASE),
    "SessionToken": re.compile(rb"SessionToken", re.IGNORECASE),
}


@dataclass(frozen=True)
class Finding:
    """One forbidden pattern on one line of one file."""

    path: Path
    line: int
    pattern: str

    def describe(self, root: Path) -> str:
        try:
            shown = self.path.relative_to(root)
        except ValueError:
            shown = self.path
        return f"{shown.as_posix()}:{self.line}: forbidden pattern {self.pattern}"


_UTF16_BOMS = (b"\xff\xfe", b"\xfe\xff")


def _normalised_bytes(path: Path) -> bytes:
    """The file's bytes, with UTF-16 text (detected by its BOM) re-encoded as UTF-8."""
    data = path.read_bytes()
    if data.startswith(_UTF16_BOMS):
        return data.decode("utf-16", errors="replace").encode("utf-8")
    return data


def scan_file(path: Path) -> list[Finding]:
    """Return every finding in *path*, in line order."""
    findings: list[Finding] = []
    data = _normalised_bytes(path)
    for number, line in enumerate(data.splitlines(), start=1):
        for name, pattern in FORBIDDEN_PATTERNS.items():
            if pattern.search(line):
                findings.append(Finding(path=path, line=number, pattern=name))
    return findings


def scan_folder(folder: Path) -> list[Finding]:
    """Return every finding in every file under *folder*, sorted by path.

    Raises ``FileNotFoundError`` if *folder* is not an existing directory, so
    that a mistyped path is never reported as a clean folder.
    """
    if not folder.is_dir():
        raise FileNotFoundError(f"evidence folder not found: {folder}")
    findings: list[Finding] = []
    for path in sorted(p for p in folder.rglob("*") if p.is_file()):
        findings.extend(scan_file(path))
    return findings


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="evidence_secret_scan",
        description="Refuse an evidence folder that contains a forbidden secret pattern.",
    )
    parser.add_argument("folder", type=Path, help="ticket evidence folder to scan")
    args = parser.parse_args(argv)

    try:
        findings = scan_folder(args.folder)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if not findings:
        print(f"CLEAN: {args.folder.as_posix()}")
        return 0

    for finding in findings:
        print(finding.describe(args.folder))
    print(
        f"REFUSED: {len(findings)} finding(s) in {args.folder.as_posix()}. "
        "Re-collect the evidence; do not edit the files.",
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
