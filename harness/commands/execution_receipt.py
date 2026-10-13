"""Validate a private execution readiness receipt before a run.

The receipt is the operator's pre-run evidence: which CLI answered, which
settings reach it, which directory the child runs in, and which preflight the
run is bound to. This command reads one, refuses an incomplete one, and refuses
one bound to a candidate or a profile other than the intended pair.

The receipt stays in the private environment. This command refuses one stored
inside the repository, and writes nothing anywhere.

Advisory. It closes no gate, runs no assessment and spends no quota.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from harness import execution_receipt as er
from harness import historical_profile as hp
from harness.record_binding import file_sha256

def _intended(
    repo_root: Path, candidate: str, profile: str
) -> tuple[er.IntendedPair | None, str]:
    """The Stage A pair, with the profile pinned by the bytes in this tree."""
    if profile:
        profile_path = repo_root / profile
        if not profile_path.is_file():
            return None, f"refused: no profile at {profile_path.as_posix()}"
    else:
        found = hp.discover_declarations(repo_root)
        if len(found) != 1:
            where = ", ".join(p.as_posix() for p in found) or "none"
            return None, (
                f"refused: {len(found)} declaration(s) carry the historical schema "
                f"({where}); name one with --expect-profile"
            )
        profile_path = found[0]
    try:
        declaration = hp.load_historical_profile(profile_path)
    except hp.HistoricalProfileError as exc:
        return None, f"refused: {exc}"
    return (
        er.IntendedPair(
            candidate_document_id=candidate,
            profile_id=declaration.profile_id,
            profile_path=profile_path.as_posix(),
            profile_sha256=file_sha256(profile_path),
        ),
        "",
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--receipt",
        required=True,
        help="the readiness receipt to validate. It must lie outside this repository.",
    )
    parser.add_argument(
        "--expect-candidate",
        required=True,
        help="the document id of the candidate the run is intended to assess",
    )
    parser.add_argument(
        "--expect-profile",
        default="",
        help=(
            "the profile declaration the run is intended to load. Omit it and the one "
            "declaration carrying the historical schema is found and used."
        ),
    )
    parser.add_argument("--repo-root", default=".", help="repository root (default: .)")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    intended, refusal = _intended(repo_root, args.expect_candidate, args.expect_profile)
    if intended is None:
        print(refusal)
        return 2

    try:
        receipt_path = er.receipt_path_outside(Path(args.receipt), repo_root)
        receipt = er.load_receipt(receipt_path)
    except er.ReceiptError as exc:
        print(f"refused: {exc}")
        return 2

    report = er.check(receipt, intended, receipt_dir=receipt_path.parent)
    for line in er.summary_lines(receipt, report):
        print(line)
    return 0 if report.green else 1


if __name__ == "__main__":
    raise SystemExit(main())
