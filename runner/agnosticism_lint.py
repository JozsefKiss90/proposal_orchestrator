"""
"No project nouns" lint — the agnosticism proof for the generic graph layer
(milestone 2, ticket 9; D15 test-of-done).

This is the capstone generality check for the whole milestone-2 graph track.  The
graph substrate is *designed* to be project-agnostic: one generic layer (schema,
config, reader, scaffolder, compiler, pack deriver, projector, and the vault
template), plus one per-project ``graph.config.yaml`` and its authored vault per
instance (D15).  Agnosticism is only *real* if the generic layer carries **no
instance-specific nouns** — if a partner name, the reference call/instrument, or
a domain noun of instance #1 (the MSCA-PF reference) had leaked into the schema,
the reader, or the compiler, a "second instance" would silently inherit instance
#1's specifics.

This module makes that property **checkable and enforced**.  It scans the
enumerated generic-layer sources for a denylist of instance-#1 project nouns and
fails (naming ``file:line:noun``) if any appears.  It is the executable form of
§2.7's "test of done for agnosticism"; the companion proof — a throwaway second
instance that compiles with only its ``graph.config.yaml`` changed — lives beside
it as a fixture (``tests/fixtures/agnosticism_second_instance/``) exercised by
``tests/runner/test_agnosticism_second_instance.py``.

What is (and is not) linted
---------------------------
* **In scope — the generic graph layer.**  The milestone-2 graph substrate and
  its template: ``runner/graph_*.py`` (schema, config, compiler, pack deriver,
  projector), ``runner/vault_*.py`` (reader, scaffolder), the generic vault
  template ``templates/obsidian_graph_vault/`` (authored ``.md``/``.yaml`` only),
  and the ``obsidian-graph`` scaffolding skill.  These are the reusable,
  multi-project components that must be noun-free.
* **Out of scope — the broader engine and instance #1.**  The rest of the runner
  (``call_slicer.py``, ``dag_scheduler.py``, ``unit_cost_budget.py``,
  ``instrument_profile.py`` …) is legitimately instrument-aware: MSCA-PF is
  instance #1's *active instrument*, a Tier-2A/2B fact the engine is entitled to
  name.  The reference vault ``MSCA/`` and its ``graph.config.yaml`` **are**
  instance #1 — the per-project layer — so they carry project nouns by design.
  Vendored assets (the Obsidian ``.obsidian/`` app dir, including the bundled
  Dataview plugin) are third-party, not authored generic-layer content, and are
  skipped — scanning minified Svelte would false-positive (``Sv``\\ **elte** would
  hit a bare ``ELTE``; word-boundary matching guards the authored layer, but
  vendored code is excluded outright as a matter of scope).

The denylist
------------
The nouns are instance #1's real proper nouns and distinctive domain terms, taken
from the confirmed Tier-3 project data (``consortium/roles.json``,
``project_brief/project_summary.json``) plus the three nouns the ticket names
outright (MSCA / crop / irrigation).  Matching is **word-boundary + case-
insensitive** so a generic word is never a false hit ("partner", "impact",
"objective", "outcome" are generic and deliberately **not** denylisted; only
partner *names* like ``AgroVIR`` are).  The list is instance #1's noun set: a new
instance need not extend it — the second-instance proof shows the mechanism is
generic regardless — but if a *second* reference instance were ever folded into
the generic layer, its proper nouns would be added here.

Constitutional authority
-------------------------
Subordinate to CLAUDE.md.  A pure, deterministic, Claude-free static check: it
reads source files and reports; it writes nothing, evaluates no gate (§17.6.2),
and invents no facts.  It enforces the §2 programme-/project-agnostic mission at
the source level.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

# ---------------------------------------------------------------------------
# Scope — the generic-layer sources the lint scans
# ---------------------------------------------------------------------------

#: Repo-relative globs enumerating the **generic graph layer**.  Deliberately
#: precise: ``runner/graph_*.py`` / ``runner/vault_*.py`` capture the substrate
#: and compiler family while excluding the instrument-aware engine (and this lint
#: module itself, which necessarily *contains* the denylisted nouns).  A new
#: generic ``graph_*``/``vault_*`` module is auto-covered — which is the intent:
#: the generic layer stays noun-free by construction.
GENERIC_LAYER_GLOBS: tuple[str, ...] = (
    "runner/graph_*.py",  # schema, config, compiler, pack deriver, projector
    "runner/vault_*.py",  # reader, scaffolder
    "runner/dev_graph/**/*.py",  # dev-graph index: schema, identity, builder, writer
    "templates/obsidian_graph_vault/graph.config.yaml",
    "templates/obsidian_graph_vault/README.md",
    "templates/obsidian_graph_vault/vault/**/*.md",
    ".claude/skills/obsidian-graph/SKILL.md",
)

#: File suffixes the lint reads (authored text).  Anything else under a matched
#: glob (binary/vendored assets) is skipped.
_TEXT_SUFFIXES: frozenset[str] = frozenset({".py", ".md", ".yaml", ".yml"})

#: Path segments that mark **vendored / app-config** content, never scanned even
#: when nested under a matched glob.  ``.obsidian`` is the Obsidian app directory
#: (app state + the bundled Dataview plugin) — third-party, not authored
#: generic-layer content.
_EXCLUDED_SEGMENTS: frozenset[str] = frozenset({".obsidian"})


# ---------------------------------------------------------------------------
# The denylist — instance #1's project nouns
# ---------------------------------------------------------------------------

#: Instance #1 is the MSCA-PF reference proposal.  Its *instrument* specificity —
#: the reference call/action type — must not appear in the generic layer.  ("RIA",
#: "IA", "CSA" etc. are *not* here: they are generic instrument names the engine
#: and templates may illustrate with; only instance #1's own ``MSCA`` is a leak.)
_INSTRUMENT_NOUNS: frozenset[str] = frozenset({"MSCA"})

#: The identity spine's proper nouns, from the confirmed Tier-3 spine
#: (``consortium/roles.json``): fellow, host, supervisor, associated partner, the
#: supervisor's companies, and the places tied to the mobility path.  A partner
#: **name** is denylisted; the generic word "partner" is not.
_PROPER_NOUNS: frozenset[str] = frozenset(
    {
        # Fellow (applicant researcher)
        "Cholakova",
        "Rositsa",
        # Host organisation
        "ELTE",
        "Eötvös",
        "Eotvos",
        "Loránd",
        "Lorand",
        # Supervisor + his companies
        "Jung",
        "Cubert",
        "Brightic",
        # Associated partner
        "AgroVIR",
        # Places / countries / nationalities on the mobility path + origin institute
        "Plovdiv",
        "Budapest",
        "Maritsa",
        "Hungary",
        "Hungarian",
        "Bulgaria",
        "Bulgarian",
    }
)

#: Domain nouns: the two the ticket names outright (crop, irrigation) plus the
#: distinctive instance-#1 domain terms.  Generic scientific words ("stress",
#: "monitoring", "sensor", "field") are **not** here — they would false-positive
#: on generic content; only unmistakably instance-#1 terms are.
_DOMAIN_NOUNS: frozenset[str] = frozenset(
    {
        "crop",
        "irrigation",
        "tomato",
        "hyperspectral",
        "AquaCrop",
        "PlanetScope",
        "biostimulant",
    }
)

#: The full denylist the lint matches (word-boundary, case-insensitive).
PROJECT_NOUNS: frozenset[str] = _INSTRUMENT_NOUNS | _PROPER_NOUNS | _DOMAIN_NOUNS

#: The three noun *categories* the ticket names explicitly — asserted covered by
#: the denylist (a guard so a future edit can't quietly drop one).
TICKET_NAMED_NOUNS: frozenset[str] = frozenset({"MSCA", "crop", "irrigation"})

#: One compiled, case-insensitive, word-boundary alternation over the denylist.
#: Sorted longest-first so an overlapping longer noun wins the report (cosmetic —
#: the boundary anchors already prevent substring hits).
_NOUN_RE: re.Pattern[str] = re.compile(
    r"\b(?:"
    + "|".join(re.escape(n) for n in sorted(PROJECT_NOUNS, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE | re.UNICODE,
)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LintViolation:
    """One denylisted noun found in a generic-layer source."""

    path: str
    """Repo-relative POSIX path of the offending file."""
    line: int
    """1-based line number of the match."""
    noun: str
    """The denylisted noun as it appears in the source (verbatim slice)."""
    snippet: str
    """The full offending line, stripped — for an actionable report."""


@dataclass(frozen=True)
class LintReport:
    """The outcome of a generic-layer scan."""

    scanned_files: tuple[str, ...]
    """Every file scanned, repo-relative POSIX, sorted."""
    violations: tuple[LintViolation, ...]
    """Every violation, in ``(path, line)`` order."""

    @property
    def ok(self) -> bool:
        """True when the generic layer carries no project noun."""
        return not self.violations


# ---------------------------------------------------------------------------
# Core matcher (pure)
# ---------------------------------------------------------------------------


def scan_text(text: str) -> list[tuple[int, str, str]]:
    """Find every denylisted noun in *text*.

    Returns ``(line_number, matched_noun, stripped_line)`` tuples in document
    order — the pure seam both the file scanner and the self-test drive.  Matching
    is word-boundary + case-insensitive, so ``ELTE`` never hits ``Svelte`` and
    ``crop`` never hits ``AquaCrop`` — only whole-word project nouns match.
    """
    out: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in _NOUN_RE.finditer(line):
            out.append((lineno, match.group(0), line.strip()))
    return out


# ---------------------------------------------------------------------------
# File enumeration
# ---------------------------------------------------------------------------


def _is_excluded(rel_parts: Iterable[str]) -> bool:
    """True if any path segment marks vendored/app-config content."""
    return any(part in _EXCLUDED_SEGMENTS for part in rel_parts)


def iter_generic_layer_files(repo_root: Path) -> list[Path]:
    """Resolve :data:`GENERIC_LAYER_GLOBS` to the authored text files to scan.

    Deterministic (sorted by repo-relative POSIX path), de-duplicated, restricted
    to :data:`_TEXT_SUFFIXES`, and excluding any path under an
    :data:`_EXCLUDED_SEGMENTS` segment (the vendored ``.obsidian`` app dir).
    """
    seen: dict[str, Path] = {}
    for pattern in GENERIC_LAYER_GLOBS:
        for path in repo_root.glob(pattern):
            if not path.is_file() or path.suffix not in _TEXT_SUFFIXES:
                continue
            rel = path.relative_to(repo_root)
            if _is_excluded(rel.parts):
                continue
            seen[rel.as_posix()] = path
    return [seen[key] for key in sorted(seen)]


# ---------------------------------------------------------------------------
# Scan
# ---------------------------------------------------------------------------


def lint_generic_layer(repo_root: Path) -> LintReport:
    """Scan the generic graph layer for project nouns and return a report.

    Reads each enumerated source (UTF-8, BOM-tolerant) and collects a
    :class:`LintViolation` for every denylisted-noun hit.  Pure and deterministic:
    the same tree yields the same report.  Never raises on a project noun — it
    *reports* one (the CLI turns a non-empty report into a non-zero exit).
    """
    files = iter_generic_layer_files(repo_root)
    violations: list[LintViolation] = []
    scanned: list[str] = []
    for path in files:
        rel = path.relative_to(repo_root).as_posix()
        scanned.append(rel)
        text = path.read_text(encoding="utf-8-sig")
        for lineno, noun, snippet in scan_text(text):
            violations.append(
                LintViolation(path=rel, line=lineno, noun=noun, snippet=snippet)
            )
    return LintReport(scanned_files=tuple(scanned), violations=tuple(violations))


def format_report(report: LintReport) -> str:
    """Render a human-readable summary of a :class:`LintReport`."""
    if report.ok:
        return (
            f"[agnosticism-lint] OK — {len(report.scanned_files)} generic-layer "
            f"file(s) scanned, no project nouns found."
        )
    lines = [
        f"[agnosticism-lint] FAIL — {len(report.violations)} project-noun "
        f"leak(s) in the generic layer ({len(report.scanned_files)} file(s) scanned):"
    ]
    for v in report.violations:
        lines.append(f"  {v.path}:{v.line}: {v.noun!r} — {v.snippet}")
    lines.append(
        "The generic graph layer must carry no instance-specific noun (D15). Move "
        "the project-specific fact into the per-project graph.config.yaml / vault, "
        "or reword the generic-layer text."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI  (python -m runner.agnosticism_lint)
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    """Run the lint from the command line.

    Exit codes: ``0`` clean; ``1`` one or more project nouns found (report printed
    to stderr); ``3`` an unexpected error.
    """
    parser = argparse.ArgumentParser(
        prog="python -m runner.agnosticism_lint",
        description=(
            'The "no project nouns" agnosticism lint (milestone 2, ticket 9): '
            "fails if an instance-#1 project noun appears in the generic graph layer."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root (default: auto-discovered via find_repo_root).",
    )
    args = parser.parse_args(argv)

    from runner.paths import find_repo_root

    try:
        repo_root = (
            Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
        )
        report = lint_generic_layer(repo_root)
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"[agnosticism-lint] ERROR: {exc}", file=sys.stderr, flush=True)
        return 3

    if report.ok:
        print(format_report(report), flush=True)
        return 0
    print(format_report(report), file=sys.stderr, flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
