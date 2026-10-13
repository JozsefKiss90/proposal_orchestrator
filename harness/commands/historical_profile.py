"""Check a historical pre-evaluation profile and write its reading.

The declaration is JSON a tool writes. This command reads it against the matrix
it was authored from, writes the Markdown a human checks it by, and exits
non-zero when a finding stands.

Advisory. It closes no gate and runs no assessment.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from harness import historical_profile as hp

#: Where profile declarations live. The command finds the historical one by its
#: schema rather than by its filename, because a filename would name an
#: instrument and this package may not.
PROFILE_DIR = Path("harness/profiles")


def _reading_path(profile_path: Path) -> Path:
    return profile_path.with_suffix(".md")


def _discover(repo_root: Path) -> list[Path]:
    """Every profile declaration carrying the historical schema."""
    found: list[Path] = []
    for path in sorted((repo_root / PROFILE_DIR).glob("*.json")):
        try:
            head = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue
        if f'"{hp.SCHEMA}"' in head:
            found.append(path)
    return found


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--profile",
        default="",
        help=(
            "the historical profile declaration. Omit it and the one declaration carrying the "
            "historical schema is found and used."
        ),
    )
    parser.add_argument("--repo-root", default=".", help="repository root (default: .)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the committed reading is not what this run renders",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root)
    if args.profile:
        profile_path = repo_root / args.profile
    else:
        found = _discover(repo_root)
        if len(found) != 1:
            where = ", ".join(p.as_posix() for p in found) or "none"
            print(
                f"refused: {len(found)} declaration(s) carry the historical schema ({where}); "
                "name one with --profile"
            )
            return 2
        profile_path = found[0]

    try:
        profile = hp.load_historical_profile(profile_path)
    except hp.HistoricalProfileError as exc:
        print(f"refused: {exc}")
        return 2

    matrix_pin = next((p for p in profile.inputs if p.name == "matrix"), None)
    if matrix_pin is None:
        print("refused: the profile pins no matrix, so nothing can be read against it")
        return 2
    try:
        rows = hp.load_matrix_rows(repo_root / matrix_pin.path)
    except hp.HistoricalProfileError as exc:
        print(f"refused: {exc}")
        return 2

    # Compared and written as bytes, with one newline convention. Reading the
    # file as text would translate line endings on one platform and not on
    # another, so the same committed reading would be fresh here and stale
    # there, over bytes nobody changed.
    reading = hp.render(profile, rows).encode("utf-8")
    reading_path = _reading_path(profile_path)
    current = reading_path.read_bytes() if reading_path.is_file() else b""
    if args.check:
        if current != reading:
            print(f"stale: {reading_path.as_posix()}")
            return 1
    elif current != reading:
        reading_path.write_bytes(reading)
        print(f"wrote: {reading_path.as_posix()}")

    report = hp.check(profile, rows, repo_root)
    print(
        f"{profile.profile_id}: {len(profile.sourced)} sourced element(s), "
        f"{len(profile.limitations)} declared limitation(s), "
        f"{len(rows)} matrix row(s)"
    )
    if report.green:
        print("profile check: green")
        return 0
    for line in report.lines():
        print(line)
    print(f"profile check: {report.findings_total} finding(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
