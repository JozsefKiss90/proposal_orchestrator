"""
Test helper: bind an ``assess`` command line to a fresh evidence preflight.

``assess`` requires ``--preflight <file>`` (spec PE-05).  Tests that drive the
command build their argv for ``assess``; this helper derives the ``preflight``
argv from it (dropping the assessor-only flags), runs the preflight into a
sibling of ``--out-dir`` so the report directory under test still holds only
the blind report, and returns the argv with ``--preflight`` appended.

A preflight that could not run (exit 2, nothing written) hands back a path to
a file that does not exist, so the assess call fails closed in the same way.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Sequence

import harness.commands.blind_assessment as cmd

#: Flags only ``assess`` takes, with a value.
ASSESS_ONLY_VALUE_FLAGS: frozenset[str] = frozenset(
    {
        "--intake", "--provenance", "--n", "--criterion-n", "--tpm", "--rpm", "--max-retries",
        "--assessor-model", "--assessor-version", "--cli-timeout", "--preflight",
        "--checkpoint", "--resume", "--transcripts",
    }
)

#: Flags only ``assess`` takes, without a value.
ASSESS_ONLY_SWITCHES: frozenset[str] = frozenset(
    {"--skip-criterion-scores", "--no-checkpoint"}
)


def preflighted(argv: Sequence[str], *, clock: Callable[[], str] | None = None) -> list[str]:
    """Return *argv* (an ``assess`` command line) with ``--preflight <file>`` appended."""
    args = list(argv)
    assert args and args[0] == "assess", args
    pre: list[str] = ["preflight"]
    out: Path | None = None
    tokens = iter(args[1:])
    for tok in tokens:
        if tok in ASSESS_ONLY_VALUE_FLAGS:
            next(tokens, None)
            continue
        if tok in ASSESS_ONLY_SWITCHES:
            continue
        if tok == "--out-dir":
            out = Path(next(tokens))
            continue
        pre.append(tok)
    base = out if out is not None else Path("harness/blind_reports")
    pre_out = base.parent / f"{base.name}_preflight"
    before = {p.name for p in pre_out.iterdir()} if pre_out.is_dir() else set()
    code = cmd.main([*pre, "--out-dir", str(pre_out)], clock=clock)
    if code == 2:
        return [*args, "--preflight", str(pre_out / "preflight_could_not_run.json")]
    # The document route also materialises candidates under the out dir; only the report counts.
    (new,) = [p for p in pre_out.glob("preflight_*.json") if p.name not in before]
    return [*args, "--preflight", str(new)]
