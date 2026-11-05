#!/usr/bin/env python3
"""
Check an open-deferral register, and render its reading beside it.

    py -3.10 -m harness.commands.deferral_register --register PATH

The register is a JSON declaration written by a deterministic authoring tool.
This command is the reader: it loads the declaration, reads it against the
records it binds, writes the Markdown reading next to it, and exits 0 only when
every finding is empty.

The check is separate from the authoring on purpose. A tool that both wrote a
record and certified it would be judging its own output, and the authoring side
sits outside this package for the one-way boundary
``tests/harness/test_boundary.py`` enforces.

What makes it fail
------------------
* a row marked ``closed`` with no closure evidence, or with no closure date;
* closure evidence filed against a row still marked open;
* a row with an empty owner, subject, closure evidence or source;
* a duplicate row id;
* a row or a measurement citing a record the register has not bound, or a
  pointer that no longer resolves;
* a bound record that is absent, a historical record whose bytes moved, or a
  tracked input whose bytes moved (the register is then stale);
* a statement with no measurement, or a measurement the records contradict.

Flags
-----
``--register PATH``   the declaration to read. Required: nothing here guesses
                      which register an operator meant.
``--check``           write nothing; exit 1 if the reading would change.
``--no-render``       check only, leaving any existing reading alone.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from harness import deferral_register as dr
from harness.commands._common import REPO_ROOT
from runner.atomic_write import atomic_write_text


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harness.commands.deferral_register",
        description="check an open-deferral register and render its reading",
    )
    parser.add_argument(
        "--register", type=Path, required=True, help="the JSON declaration to read"
    )
    parser.add_argument(
        "--check", action="store_true", help="write nothing; exit 1 if the reading would change"
    )
    parser.add_argument(
        "--no-render", action="store_true", help="check only, leaving any reading alone"
    )
    parser.add_argument("--repo-root", type=Path, default=None)
    return parser


def reading_path(register_path: Path) -> Path:
    """Where the Markdown reading of *register_path* lives."""
    return register_path.with_suffix(".md")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = args.repo_root or REPO_ROOT
    path = args.register if args.register.is_absolute() else repo_root / args.register

    try:
        register = dr.load_register(path, repo_root=repo_root)
    except (OSError, dr.DeferralRegisterError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1

    result = dr.check(register, repo_root)
    target = reading_path(path)

    # --no-render takes the reading out of the result entirely, so the exit code
    # is the register's check alone. Without it, a stale reading is a finding
    # under --check and a write otherwise.
    stale = False
    if not args.no_render:
        rendered = dr.render_report(register).encode("utf-8")
        stale = not target.is_file() or target.read_bytes() != rendered
        if args.check and stale:
            print(f"would change: {target.relative_to(repo_root).as_posix()}")
        elif stale:
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(rendered.decode("utf-8"), target)
            print(f"wrote: {target.relative_to(repo_root).as_posix()}")

    print(f"{register.name}: {len(register.open_rows())} open, {len(register.closed_rows())} closed")
    print(
        f"{len(register.rows_requiring_the_original())} of them need the submitted original, "
        "which this repository does not hold"
    )
    for line in result.lines():
        print(line)
    print("register check: green" if result.green else "register check: FAILED")
    if not result.green:
        return 1
    return 1 if (args.check and stale) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
