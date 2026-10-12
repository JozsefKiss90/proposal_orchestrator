#!/usr/bin/env python3
"""
Check a rule-equivalence matrix against its source index, and render both readings.

    py -3.10 -m harness.commands.authority_matrix --matrix PATH

The matrix and the index are JSON declarations written by a deterministic
authoring tool. This command is the reader: it loads both, reads the matrix
against the index and the records they bind, writes the Markdown reading beside
each, and exits 0 only when every finding is empty.

The check is separate from the authoring on purpose. A tool that both wrote a
record and certified it would be judging its own output, and the authoring side
sits outside this package for the one-way boundary
``tests/harness/test_boundary.py`` enforces.

What makes it fail
------------------
* a row marked ``equivalent`` or ``differs`` with no citation into an obtained
  historical source — defaulting wearing the word equivalent;
* a ``defaulted`` row that does not name the rule its defaulting affects;
* a ``differs`` row with no difference, an ``unresolved`` row with no
  limitation, an ``era_neutral`` row with no justification;
* a required area no row covers;
* a citation of a source the index does not declare, of one it records as not
  obtained, or one whose page or field does not resolve;
* a page citation with no verbatim quote;
* a citation of a passage outside the areas its record measured;
* a row naming a document that would settle it which the index does not declare;
* a ``call_wide`` conclusion resting only on evidence about one submission;
* a ``Confirmed`` row with no authenticated source behind it;
* a bound record that is absent, a historical record whose bytes moved, a
  tracked input whose bytes moved, or a source index whose bytes moved;
* a measurement the records contradict.

Flags
-----
``--matrix PATH``   the matrix declaration to read. Required: nothing here
                    guesses which matrix an operator meant. The index comes
                    from the matrix's own ``source_index`` binding.
``--check``         write nothing; exit 1 if either reading would change.
``--no-render``     check only, leaving any existing readings alone.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional, Sequence

from harness import authority_matrix as am
from harness.commands._common import REPO_ROOT
from runner.atomic_write import atomic_write_text


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="harness.commands.authority_matrix",
        description="check a rule-equivalence matrix and render its reading",
    )
    parser.add_argument("--matrix", type=Path, required=True, help="the matrix declaration")
    parser.add_argument(
        "--check", action="store_true", help="write nothing; exit 1 if a reading would change"
    )
    parser.add_argument(
        "--no-render", action="store_true", help="check only, leaving any reading alone"
    )
    parser.add_argument("--repo-root", type=Path, default=None)
    return parser


def reading_path(declaration: Path) -> Path:
    """Where the Markdown reading of *declaration* lives."""
    return declaration.with_suffix(".md")


def _render(target: Path, body: str, repo_root: Path, check_only: bool) -> bool:
    """Write *body* to *target* unless *check_only*. True when it would change."""
    rendered = body.encode("utf-8")
    stale = not target.is_file() or target.read_bytes() != rendered
    if not stale:
        return False
    rel = (
        target.relative_to(repo_root).as_posix()
        if target.is_relative_to(repo_root)
        else target.as_posix()
    )
    if check_only:
        print(f"would change: {rel}")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(body, target)
        print(f"wrote: {rel}")
    return True


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = args.repo_root or REPO_ROOT
    matrix_path = args.matrix if args.matrix.is_absolute() else repo_root / args.matrix

    try:
        matrix = am.load_matrix(matrix_path, repo_root=repo_root)
        index_path = repo_root / matrix.index_path
        index = am.load_source_index(index_path, repo_root=repo_root)
    except (OSError, am.AuthorityMatrixError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1

    result = am.check(matrix, index, repo_root)

    stale = False
    if not args.no_render:
        stale |= _render(
            reading_path(index_path), am.render_index(index), repo_root, args.check
        )
        stale |= _render(
            reading_path(matrix_path), am.render_matrix(matrix, index), repo_root, args.check
        )

    counts = ", ".join(
        f"{len(rows)} {verdict}" for verdict, rows in matrix.rows_by_verdict().items()
    )
    print(f"{matrix.name}: {len(matrix.rows)} rows — {counts}")
    print(
        f"{index.name}: {len(index.obtained())} of {len(index.sources)} documents obtained, "
        f"{len(index.missing_required())} required ones absent"
    )
    for line in result.lines():
        print(line)
    print(
        "matrix check: green"
        if result.green
        else f"matrix check: FAILED ({result.findings_total} finding(s))"
    )
    if not result.green:
        return 1
    return 1 if (args.check and stale) else 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
