"""An acceptance lane: named coverage areas, declared exclusions, and a measured baseline.

A lane is read from a JSON declaration under ``harness/acceptance_lanes/``. This
module is the reader and the reconciler. It carries no instrument name, no call
name and no module list of its own — those are the declaration's, exactly as a
profile's criteria are the profile's and not the loader's.

Why a declaration and not a pytest invocation
---------------------------------------------
Test counts are not coverage of acceptance invariants. A suite can pass 1,864
cases and still miss four reproduced defects, which is what the readiness audit
measured. A count answers "did anything break". It does not answer "is the thing
we are about to accept actually checked".

So a lane declares :class:`Area` records, not paths. Each area names one
acceptance invariant and the modules that check it, and
:meth:`Lane.unassigned_focused_modules` refuses to let a module inside the
audit's own command belong to no area. A reader can then ask which invariant
covers the importer and get a named answer.

Two reconciliations a lane performs, and a third it does not
------------------------------------------------------------
:func:`reconcile` compares a run against the declaration in both directions. A
skip no :class:`Exclusion` declares is an *invisible* exclusion. An exclusion
the run never reported is a *stale* claim — which is how the first run of this
lane found a disposition row naming a class that had been renamed. Either fails
the lane; so does any failure or error. :class:`Baseline` carries the audit's
measured figures, so a result is recorded against a measured number rather than
a remembered one.

What a lane cannot reconcile is coverage against *value*. Passing it says the
code behaves as its fixtures specify. It says nothing about calibration,
forecast accuracy or grounded evaluation, and :attr:`Lane.not_evidence_of`
carries that sentence for a human reader.

Nothing here runs pytest. ``harness.commands.acceptance_lane`` does that, and
this module stays importable and offline so a declaration is testable on its
own.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from xml.etree import ElementTree

from runner.paths import find_repo_root

#: Where lane declarations live, repository-relative. One JSON file per lane.
LANES_DIR_REL = "harness/acceptance_lanes"


#: The declaration schema this reader understands.
SCHEMA = "acceptance_lane/1"


# --------------------------------------------------------------------------- #
# The declaration
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Area:
    """One acceptance invariant, and the modules that check it."""

    #: A short name. Lower case, one word where one word will do.
    name: str
    #: The invariant in a sentence: what would be untrue if these checks failed.
    invariant: str
    #: Repository-relative test module paths, POSIX separators.
    modules: tuple[str, ...]
    #: Whether the run this lane gates depends on this invariant. Declared per
    #: area rather than per exclusion, because it is the invariant that is
    #: depended on and an exclusion inherits the answer from where it sits.
    #: :meth:`Lane.exclusions_in_depended_on_areas` is what turns the
    #: acceptance criterion into a measurement.
    depended_on: bool = False


@dataclass(frozen=True)
class Baseline:
    """One measured suite result, with the commit it was measured at."""

    commit: str
    passed: int
    failed: int
    errors: int
    skipped: int
    collected: int


@dataclass(frozen=True)
class Exclusion:
    """One check the lane cannot run, with its reason and its replacement.

    ``check`` is a module-relative node id and may name a class rather than a
    test, because one disposition row can stand for several checks.
    """

    check: str
    substrate: str
    reason: str
    #: What covers the invariant instead. Required: an exception without one
    #: is an uncovered invariant, not an accounted-for absence.
    replacement_evidence: str
    lifted_by: str
    #: How many individual cases the row stands for.
    checks: int = 1
    #: Whether the historical run depends on the invariant this check covered.
    #: A lane whose acceptance criteria forbid it refuses to close while set.
    historical_run_depends_on: bool = False


@dataclass(frozen=True)
class Lane:
    """A lane declaration, as read from its JSON file."""

    name: str
    command: str
    areas: tuple[Area, ...]
    exclusions: tuple[Exclusion, ...]
    audit_baseline: Baseline
    #: The audit command the lane must cover, as glob patterns.
    audit_focused_globs: tuple[str, ...]
    #: What the lane adds beyond that command, mapped to why each belongs.
    modules_added: Mapping[str, str]
    #: Modules considered and left out, mapped to why. Read and printed, so a
    #: module kept out of the lane is a stated decision rather than an absence.
    modules_left_out: Mapping[str, str]
    #: How many individual skips a complete run reports.
    declared_skips: int
    #: What a green result is not evidence of.
    not_evidence_of: tuple[str, ...]
    #: Where the prose declaration and the exclusion document live.
    documentation: str
    exclusion_document: str
    #: Where this declaration was read from, repository-relative.
    source: str

    # -- the modules -------------------------------------------------------- #

    def modules(self) -> tuple[str, ...]:
        """Every module the lane runs, in area order."""
        return tuple(module for area in self.areas for module in area.modules)

    def modules_missing_from_disk(self, repo_root: Path) -> tuple[str, ...]:
        """Declared modules that are not files. A stale area names a check
        nobody runs."""
        return tuple(m for m in self.modules() if not (repo_root / m).is_file())

    def audit_focused_modules(self, repo_root: Path) -> tuple[str, ...]:
        """The audit's focused command, expanded against the tree."""
        found: set[str] = set()
        for pattern in self.audit_focused_globs:
            parent, _, name = pattern.rpartition("/")
            for path in sorted((repo_root / parent).glob(name)):
                found.add(path.relative_to(repo_root).as_posix())
        return tuple(sorted(found))

    def unassigned_focused_modules(self, repo_root: Path) -> tuple[str, ...]:
        """Modules inside the audit's command that belong to no area.

        The lane is a superset of that command by construction, so a module
        here is a check the lane would drop while reporting a green result.
        """
        assigned = set(self.modules())
        return tuple(m for m in self.audit_focused_modules(repo_root) if m not in assigned)

    # -- the exclusions ----------------------------------------------------- #

    def declared_check_count(self) -> int:
        """The number of individual cases the exclusion rows account for.

        Compared against the declared :attr:`declared_skips` by the lane's
        tests. The duplication is deliberate double entry: a mistyped
        ``checks`` on one row changes this sum and the stated total catches it.
        """
        return sum(e.checks for e in self.exclusions)

    def area_of_module(self, module: str) -> Area | None:
        """The area a repository-relative test module belongs to."""
        for area in self.areas:
            if module in area.modules:
                return area
        return None

    def area_of_exclusion(self, exclusion: Exclusion) -> Area | None:
        """The area the excluded check's module belongs to.

        An exclusion names a module-relative node id, so the module is matched
        by basename against every declared path.
        """
        basename = exclusion.check.split("::")[0]
        for area in self.areas:
            for module in area.modules:
                if module.rsplit("/", 1)[-1] == basename:
                    return area
        return None

    def exclusions_in_depended_on_areas(self) -> tuple[tuple[str, str], ...]:
        """Every ``(check, area)`` pair where an exclusion sits in an area the
        run depends on.

        This is the measurement behind "no exception covers a check the
        historical run depends on". A row that self-declares
        ``historical_run_depends_on`` counts too, so an exclusion can still be
        flagged by hand when its area is not the whole story.
        """
        found = []
        for exclusion in self.exclusions:
            area = self.area_of_exclusion(exclusion)
            if exclusion.historical_run_depends_on:
                found.append((exclusion.check, area.name if area else "unassigned"))
            elif area is not None and area.depended_on:
                found.append((exclusion.check, area.name))
        return tuple(found)

    def exclusions_missing_from_their_document(self, repo_root: Path) -> tuple[str, ...]:
        """Declared exclusions the exclusion document does not name.

        The lane's claim is that the declaration and the document cannot drift
        apart. The command checks it before running anything, so the claim is
        true of the command and not only of the lane's tests.
        """
        path = repo_root / self.exclusion_document
        if not path.is_file():
            return tuple(e.check for e in self.exclusions)
        text = path.read_text(encoding="utf-8")
        return tuple(e.check for e in self.exclusions if e.check not in text)


# --------------------------------------------------------------------------- #
# Reading a declaration
# --------------------------------------------------------------------------- #


def _root(repo_root: Path | None) -> Path:
    """*repo_root*, or the root this file sits in.

    Anchored on the file rather than on the working directory, so a lane
    resolves the same from anywhere, and defined once so the library holds no
    second repo root beside ``harness.commands._common.REPO_ROOT``.
    """
    if repo_root is not None:
        return repo_root
    return find_repo_root(Path(__file__).resolve().parent)


def lane_paths(repo_root: Path | None = None) -> tuple[Path, ...]:
    """Every lane declaration in the tree, sorted by name."""
    root = _root(repo_root)
    directory = root / LANES_DIR_REL
    if not directory.is_dir():
        return ()
    return tuple(sorted(directory.glob("*.json")))


def default_lane_path(repo_root: Path | None = None) -> Path:
    """The only lane declaration in the tree.

    Fails closed on none and on several rather than picking one. A reader that
    guessed would silently accept a run against a lane nobody chose, and the
    name of the lane is the whole point of a named lane.
    """
    found = lane_paths(repo_root)
    if not found:
        raise FileNotFoundError(f"no lane declaration in {LANES_DIR_REL}/")
    if len(found) > 1:
        names = ", ".join(p.stem for p in found)
        raise ValueError(f"several lane declarations in {LANES_DIR_REL}/: {names}; name one")
    return found[0]


def resolve_lane_path(name: str | None, repo_root: Path | None = None) -> Path:
    """The declaration for *name*, or the only one when *name* is ``None``."""
    if name is None:
        return default_lane_path(repo_root)
    root = _root(repo_root)
    path = root / LANES_DIR_REL / f"{name}.json"
    if not path.is_file():
        available = ", ".join(p.stem for p in lane_paths(root)) or "none"
        raise FileNotFoundError(f"no lane declaration {name!r}; available: {available}")
    return path


def _required(raw: Mapping[str, Any], key: str, source: str) -> Any:
    if key not in raw:
        raise ValueError(f"{source}: the declaration has no {key!r}")
    return raw[key]


def load_lane(path: Path, repo_root: Path | None = None) -> Lane:
    """Read a lane declaration.

    Fails closed on a missing field. A lane with half a declaration would
    reconcile a run against half a claim.
    """
    root = _root(repo_root)
    try:
        source = path.relative_to(root).as_posix()
    except ValueError:
        source = path.as_posix()
    raw = json.loads(path.read_text(encoding="utf-8"))
    schema = raw.get("schema")
    if schema != SCHEMA:
        raise ValueError(f"{source}: schema is {schema!r}, expected {SCHEMA!r}")

    areas = tuple(
        Area(
            name=_required(a, "name", source),
            invariant=_required(a, "invariant", source),
            modules=tuple(_required(a, "modules", source)),
            depended_on=bool(_required(a, "depended_on", source)),
        )
        for a in _required(raw, "areas", source)
    )
    exclusions = tuple(
        Exclusion(
            check=_required(e, "check", source),
            substrate=_required(e, "substrate", source),
            reason=_required(e, "reason", source),
            replacement_evidence=_required(e, "replacement_evidence", source),
            lifted_by=_required(e, "lifted_by", source),
            checks=int(e.get("checks", 1)),
            historical_run_depends_on=bool(e.get("historical_run_depends_on", False)),
        )
        for e in _required(raw, "exclusions", source)
    )
    b = _required(raw, "audit_baseline", source)
    baseline = Baseline(
        commit=_required(b, "commit", source),
        passed=int(_required(b, "passed", source)),
        failed=int(_required(b, "failed", source)),
        errors=int(_required(b, "errors", source)),
        skipped=int(_required(b, "skipped", source)),
        collected=int(_required(b, "collected", source)),
    )
    return Lane(
        name=_required(raw, "lane_name", source),
        command=_required(raw, "command", source),
        areas=areas,
        exclusions=exclusions,
        audit_baseline=baseline,
        audit_focused_globs=tuple(_required(raw, "audit_focused_globs", source)),
        modules_added=dict(_required(raw, "modules_added_beyond_the_focused_command", source)),
        modules_left_out=dict(_required(raw, "modules_considered_and_left_out", source)),
        declared_skips=int(_required(raw, "declared_skips", source)),
        not_evidence_of=tuple(_required(raw, "not_evidence_of", source)),
        documentation=_required(raw, "documentation", source),
        exclusion_document=_required(raw, "exclusion_document", source),
        source=source,
    )


# --------------------------------------------------------------------------- #
# Reading a run
# --------------------------------------------------------------------------- #


def node_id(classname: str, name: str) -> str:
    """A module-relative node id from a JUnit ``classname`` and ``name``.

    ``tests.harness.test_gold_set.TestSeededExcellenceTemplate`` with
    ``test_x`` becomes ``test_gold_set.py::TestSeededExcellenceTemplate::test_x``
    — the spelling the exclusion document uses, so one id serves the document,
    the lane and a reader.
    """
    parts = classname.split(".")
    for index, part in enumerate(parts):
        if part.startswith("test_"):
            return "::".join([part + ".py", *parts[index + 1 :], name])
    # No ``test_*`` component: not a shape pytest produces for a collected
    # module. Keep the ``<module>.py::`` prefix anyway, so every id the
    # reconciler compares has one shape and a surprise reads as a wrong name
    # rather than as a different format.
    head, *rest = parts or [""]
    return "::".join([head + ".py", *rest, name])


@dataclass(frozen=True)
class Outcome:
    """One lane run, as its JUnit report records it."""

    collected: int
    failed: int
    errors: int
    skipped: int
    failures: tuple[str, ...]
    skips: tuple[tuple[str, str], ...]

    @property
    def passed(self) -> int:
        """Derived, because JUnit records no pass count."""
        return self.collected - self.failed - self.errors - self.skipped


def parse_junit(xml_text: str) -> Outcome:
    """Read a pytest JUnit XML report.

    Failures and errors are kept together in :attr:`Outcome.failures`. A lane
    asks for zero *unexplained failures*, and a setup error is not a lesser
    result — only, often, a shared cause.
    """
    root = ElementTree.fromstring(xml_text)
    suites = root.findall("testsuite") or ([root] if root.tag == "testsuite" else [])
    collected = failed = errors = skipped = 0
    for suite in suites:
        collected += int(suite.get("tests", 0))
        failed += int(suite.get("failures", 0))
        errors += int(suite.get("errors", 0))
        skipped += int(suite.get("skipped", 0))
    failures: list[str] = []
    skips: list[tuple[str, str]] = []
    for case in root.iter("testcase"):
        ident = node_id(case.get("classname", ""), case.get("name", ""))
        if case.find("failure") is not None or case.find("error") is not None:
            failures.append(ident)
        skip = case.find("skipped")
        if skip is not None:
            skips.append((ident, skip.get("message", "")))
    return Outcome(
        collected=collected,
        failed=failed,
        errors=errors,
        skipped=skipped,
        failures=tuple(failures),
        skips=tuple(skips),
    )


@dataclass(frozen=True)
class Reconciliation:
    """A run read against a declaration, in both directions."""

    unexplained_failures: tuple[str, ...] = ()
    undeclared_skips: tuple[str, ...] = ()
    declared_but_absent: tuple[str, ...] = ()

    @property
    def green(self) -> bool:
        """Zero unexplained failures, every exception enumerated, and no
        enumerated exception left unobserved."""
        return not (
            self.unexplained_failures or self.undeclared_skips or self.declared_but_absent
        )

    def lines(self, exclusion_document: str = "the exclusion document") -> tuple[str, ...]:
        """The reconciliation for a human, one finding per line."""
        out = []
        for ident in self.unexplained_failures:
            out.append(f"UNEXPLAINED FAILURE  {ident}")
        for ident in self.undeclared_skips:
            out.append(f"UNDECLARED SKIP      {ident}  (add it to {exclusion_document})")
        for ident in self.declared_but_absent:
            out.append(f"STALE EXCLUSION      {ident}  (declared, and the run did not report it)")
        return tuple(out)


def _declares(exclusion: Exclusion, ident: str) -> bool:
    """Whether *exclusion* covers the node id *ident*.

    Prefix match on node-id boundaries, so a row naming a class covers each of
    its tests and a row naming a test covers only itself.
    """
    return ident == exclusion.check or ident.startswith(exclusion.check + "::")


def reconcile(outcome: Outcome, exclusions: Sequence[Exclusion]) -> Reconciliation:
    """Read *outcome* against *exclusions*.

    A failure is never explained by an exclusion: an excluded check skips. So
    every failure is unexplained, which is what makes "zero unexplained
    failures" a check an operator can run rather than a sentence in a report.
    """
    observed = [ident for ident, _reason in outcome.skips]
    undeclared = tuple(
        ident for ident in observed if not any(_declares(e, ident) for e in exclusions)
    )
    absent = tuple(
        e.check for e in exclusions if not any(_declares(e, ident) for ident in observed)
    )
    return Reconciliation(
        unexplained_failures=tuple(outcome.failures),
        undeclared_skips=undeclared,
        declared_but_absent=absent,
    )


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #


def baseline_reconciliation(lane: Lane, outcome: Outcome) -> tuple[str, ...]:
    """The lane's result beside the audit's, line by line."""
    b = lane.audit_baseline
    rows = (
        ("passed", b.passed, outcome.passed),
        ("failed", b.failed, outcome.failed),
        ("errors", b.errors, outcome.errors),
        ("skipped (declared exclusions)", b.skipped, outcome.skipped),
        ("collected", b.collected, outcome.collected),
    )
    width = max(len(name) for name, _, _ in rows)
    head = f"{'':{width}}  {'audit ' + b.commit:>14}  {'this lane':>14}"
    return (head, *(f"{name:{width}}  {was:>14,}  {now:>14,}" for name, was, now in rows))


_WS = re.compile(r"\s+")


def one_line(text: str) -> str:
    """*text* with its newlines collapsed, for a table cell."""
    return _WS.sub(" ", text).strip()
