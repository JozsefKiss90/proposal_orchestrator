"""The extraction environment the committed import artifacts reproduce under.

``runner.external_proposal`` versions what the importer does to a page — the
extractor, the normalisation, the table rendering and the claim extraction. It
cannot version what PyMuPDF does to the page before the importer sees it. The
page text, the text blocks and the found tables are MuPDF's, and a MuPDF build
that groups glyphs into blocks differently produces a different paragraph
stream from the same bytes, hence a different document content version.

That is not hypothetical. PyMuPDF 1.26.6 through 1.27.2 split the first wrapped
line of eight numbered list items in the sanitised candidate into a block of
their own; 1.28.x keep each list item whole. The committed artifacts reproduce
under 1.28.x and refuse under the earlier builds, which derive
``MSCA-DN-2025_sanitised_part_b@842a80dea6920270`` instead. The measurement and
the arithmetic are in :data:`DECISION_REL`.

Two questions, kept apart
-------------------------
*Does this build reproduce the committed artifacts?* is
:func:`cannot_reproduce_reason`, answered against :data:`REPRODUCING_BUILDS`,
every member of which was measured. It is what the test suite asserts, because
a build outside that set makes every import test fail for one cause.

*Is this the declared environment?* is :func:`off_pin_reason`, answered against
the exact pin and the measured interpreters. It is informational. PyMuPDF
1.28.0 reproduces every committed artifact and is still off pin, because it
carries a MuPDF build the pin does not name.

Nothing here refuses. An off-pin environment is reported; ``--check`` still
answers the question it was asked, and its exit status still follows the
staleness alone. The point is that an engineer whose check fails reads which
version they are running, not only that a hash they have never seen was
expected.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

#: The PyMuPDF distribution version the committed MSCA-DN import artifacts were
#: reproduced under for V01. Exact, not a lower bound: ``pymupdf>=1.24.0``
#: admitted 1.24.0, which carries no ``pymupdf`` module at all, and four builds
#: that extract the candidate into a different paragraph stream.
PINNED_PYMUPDF = "1.28.2"
#: The MuPDF library version that PyMuPDF build carries. Named separately
#: because the two move independently, and the extraction behaviour is MuPDF's.
PINNED_MUPDF = "1.28.2"
#: Interpreter minor versions the reproduction was measured on, both of which
#: reproduce both committed document versions at the pinned library. The
#: interpreter is not the variable; the extraction library is. Versions outside
#: this tuple are unmeasured rather than known bad, so they are reported and
#: never treated as a failure to reproduce.
MEASURED_PYTHON: tuple[str, ...] = ("3.10", "3.11")
#: Every ``(pymupdf, mupdf)`` build measured to reproduce both committed
#: document versions byte-equal. The pin is the first. 1.28.0 reproduces them
#: too and ships MuPDF 1.29.0, so a range over the two would pin two MuPDF
#: builds; it is recorded here rather than widening the pin.
REPRODUCING_BUILDS: tuple[tuple[str, str], ...] = (
    (PINNED_PYMUPDF, PINNED_MUPDF),
    ("1.28.0", "1.29.0"),
)

#: The diagnosis, the measured version matrix and the four register
#: differences. Repository-relative.
DECISION_REL = "docs/tier4_orchestration_state/decision_log/msca-dn-extraction-environment-pin_2026-10-08.json"


@dataclass(frozen=True)
class Environment:
    """One measurement of an extraction environment."""

    pymupdf: str
    mupdf: str
    python: str

    @property
    def python_minor(self) -> str:
        """The interpreter's major.minor, which is what the pin ranges over."""
        return ".".join(self.python.split(".")[:2])

    @property
    def build(self) -> tuple[str, str]:
        """The extraction library pair the reproduction depends on."""
        return self.pymupdf, self.mupdf


def measure() -> Environment:
    """The running environment."""
    import pymupdf

    return Environment(
        pymupdf=pymupdf.__version__,
        mupdf=pymupdf.mupdf_version,
        python=".".join(str(n) for n in sys.version_info[:3]),
    )


def cannot_reproduce_reason(environment: Environment | None = None) -> str | None:
    """Why *environment* cannot reproduce the committed import artifacts, or
    ``None`` when its build was measured to reproduce them.

    The interpreter is not consulted: it was measured not to matter, so an
    unmeasured one is unknown rather than broken, and refusing on it would
    report a problem that has not been shown to exist.
    """
    env = environment if environment is not None else measure()
    if env.build in REPRODUCING_BUILDS:
        return None
    measured = ", ".join(f"PyMuPDF {b} with MuPDF {m}" for b, m in REPRODUCING_BUILDS)
    return (
        f"PyMuPDF {env.pymupdf} with MuPDF {env.mupdf} is not a build measured to reproduce "
        f"the committed import artifacts; those are {measured}"
    )


def off_pin_reason(environment: Environment | None = None) -> str | None:
    """Why *environment* is off the declared pin, or ``None`` when it is on it.

    One reason, the extraction library first: a wrong library explains a failed
    replay on its own, and an unmeasured interpreter underneath it is then
    beside the point.
    """
    env = environment if environment is not None else measure()
    if env.pymupdf != PINNED_PYMUPDF:
        return f"PyMuPDF {env.pymupdf} is not the pinned {PINNED_PYMUPDF}"
    if env.mupdf != PINNED_MUPDF:
        return (
            f"MuPDF {env.mupdf} is not the pinned {PINNED_MUPDF}; "
            f"this PyMuPDF build carries a different library"
        )
    if env.python_minor not in MEASURED_PYTHON:
        return (
            f"Python {env.python_minor} is outside the measured "
            f"{' and '.join(MEASURED_PYTHON)}; the reproduction is unmeasured here, not known broken"
        )
    return None


def staleness_notice(environment: Environment | None = None) -> str:
    """What the extraction environment contributes to a stale rendering.

    Said either way round. A build that cannot reproduce the artifacts is the
    explanation; one that can rules the library out, which is the more useful
    half of the message because it sends the reader to the diff rather than to
    pip.
    """
    env = environment if environment is not None else measure()
    cannot = cannot_reproduce_reason(env)
    if cannot is not None:
        return f"extraction environment: {cannot}; see {DECISION_REL}"
    return (
        f"extraction environment: PyMuPDF {env.pymupdf} with MuPDF {env.mupdf} reproduces the "
        f"committed import artifacts, so the staleness is not a library difference"
    )


def describe_environment(environment: Environment | None = None) -> str:
    """The pin, the measurement and where the diagnosis lives, for an operator."""
    env = environment if environment is not None else measure()
    off_pin = off_pin_reason(env)
    cannot = cannot_reproduce_reason(env)
    return "\n".join(
        [
            f"pinned extraction environment: PyMuPDF {PINNED_PYMUPDF}, MuPDF {PINNED_MUPDF}, "
            f"Python {' or '.join(MEASURED_PYTHON)}",
            f"running: PyMuPDF {env.pymupdf}, MuPDF {env.mupdf}, Python {env.python}",
            "on pin" if off_pin is None else f"OFF PIN: {off_pin}",
            "reproduces the committed import artifacts"
            if cannot is None
            else f"CANNOT REPRODUCE: {cannot}",
            f"diagnosis: {DECISION_REL}",
        ]
    )


# --------------------------------------------------------------------------- #
# The flag the authoring tools share
# --------------------------------------------------------------------------- #


def add_environment_flag(parser: argparse.ArgumentParser) -> None:
    """Declare ``--environment`` on an authoring tool's parser.

    Shared so the two importers cannot word the flag, or answer it,
    differently.
    """
    parser.add_argument(
        "--environment",
        action="store_true",
        help="print the pinned extraction environment against the running one and exit",
    )


def environment_exit_code(args: argparse.Namespace) -> int | None:
    """``0`` once ``--environment`` has been answered, else ``None``.

    Answered before any repository root is resolved, so the flag works from
    anywhere.
    """
    if not args.environment:
        return None
    print(describe_environment())
    return 0
