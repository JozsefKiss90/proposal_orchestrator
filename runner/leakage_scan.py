"""The instance-one leakage scan — the anonymity proof for the demo branch.

The ``dev_graph_demo`` branch runs a *second* project instance. Its consortium is
derived from instance one's expertise and then fully anonymised, so the branch
carries one standing constraint: no real organisation name, person name, place,
web address, grant or project identifier from instance one appears in Tier 3,
Tier 4, Tier 5 or the vault.

This module makes that constraint checkable. It is the anonymity counterpart to
``runner/agnosticism_lint.py``: the lint keeps instance-one nouns out of the
*generic engine layer*, this scan keeps them out of *instance two's records*.

Two mechanisms, because a word scan alone cannot do the job
----------------------------------------------------------
**1. The word scan.** The scanned set is *derived* from the standing agnosticism
denylist, not re-typed from it: :data:`LEAKAGE_NOUNS` is ``PROJECT_NOUNS`` minus
the scoped-out set, plus the project identifiers that denylist never held. A noun
added to ``PROJECT_NOUNS`` later is therefore scanned from that moment with no
edit here. Every noun on the standing denylist is classified into exactly one of
three sets, and only the first two are leaks:

``IDENTITY_NOUNS``
    People, organisations and place names. An identifying fact of instance one,
    always a leak.
``REIDENTIFYING_NOUNS``
    Named tools and materials distinctive enough that together they re-identify
    instance one. Nothing in instance two needs them.
``SCOPED_OUT``
    Carried with a stated reason and *not* scanned.

The third set exists because of finding F9 of the Tier 1 coverage report: the
denylist cannot be reused as it stands. It contains Member State and nationality
names that the General Annexes enumerate verbatim, so a Tier 4 report that
discusses the eligibility rules must reproduce them. Scanning them would fail on
artifacts this constraint was never about. It also contains generic domain words
("crop", "hyperspectral") and one instrument name ("MSCA") — none of which is an
organisation, person, place, address or identifier, which is what the constraint
names. The demo scope record reached the same conclusion in its finding F2: the
leakage test scopes proper nouns, not domain nouns.

Two guarantees, and they do different work. Derivation means a new noun on the
standing denylist is *scanned* at once, because it is not in ``SCOPED_OUT``. The
partition check in ``tests/runner/test_leakage_scan.py`` means it is also
*classified*, so the reason it is a leak is on the record rather than implied.
Neither guarantee says the denylist is complete: completeness is a claim about
instance one's name set, which lives outside this repository.

**2. The pseudonymity check.** A country name is the one leak a word scan cannot
catch, because it is instance one's countries that matter and those are also
ordinary Member State names. The structural rule is stronger than a word list:
*no Tier 3 self-description may carry a real country name at all*. Country is a
pseudonymous slot (``C1``, ``C2``, …) recording only Member State or Associated
Country, which is all the composition condition needs. So the check reads the
real country lists out of Tier 1 ``participation_rules.json`` — Member States,
Associated Countries and Overseas Countries and Territories — and fails on any of
them in any artifact matched by :data:`PSEUDONYMITY_JSON_GLOBS`, together with any web
address or email. It covers every Tier 3 artifact that describes the project, not
the partner registry alone, because this is the only mechanism that catches a
country at all.

Pre-existing leaks
------------------
The branch already carries one. Instance one's project acronym appears in the
22 September purge record under Tier 4, because that record documents the purge of
that project. :data:`KNOWN_PRE_EXISTING_LEAKS` pins it to its path with the
reason, so :attr:`LeakageReport.ok` stays useful as a regression guard while
:attr:`LeakageReport.clean` reports the honest answer: the branch is **not**
clean. A hit at any other path fails the scan.

The operator extension
----------------------
The ticket asks for the denylist to be extended with instance-one organisation
names, people and places. Reuse supplies most of it: the standing denylist's
proper nouns are instance one's identity spine. It is not the whole set — the
project acronym was missing, which is why :data:`PROJECT_IDENTIFIERS` exists — so
reuse is a starting point, never a proof of completeness. Any further name is
supplied through :func:`leakage_denylist`'s ``extra_nouns``, or the CLI's
``--extra-nouns`` file, which the operator keeps **outside** the repository. That
keeps a name the branch does not already carry off the branch, which is the same
reason the pseudonym-to-entity mapping is operator-held. A name the branch
*already* carries is named here instead: a denylist cannot forbid what it cannot
say.

Constitutional standing
-----------------------
Subordinate to CLAUDE.md. Pure, deterministic and Claude-free: it reads files and
reports. It writes nothing, evaluates no gate (§17.6.2) and invents no fact.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

from runner.agnosticism_lint import PROJECT_NOUNS
from runner.consortium_composition import (
    PARTICIPATION_RULES_REL as _PARTICIPATION_RULES_REL,
)
from runner.consortium_composition import PARTNERS_REL as _PARTNERS_REL

# ---------------------------------------------------------------------------
# The partition of the standing denylist
# ---------------------------------------------------------------------------

#: Instance one's people, organisations and places. Always a leak: each names a
#: real entity or a real location tied to the reference project.
IDENTITY_NOUNS: frozenset[str] = frozenset(
    {
        # People
        "Cholakova",
        "Rositsa",
        "Jung",
        # Organisations, and the spellings the same organisation appears under
        "ELTE",
        "Eötvös",
        "Eotvos",
        "Loránd",
        "Lorand",
        "Cubert",
        "Brightic",
        "AgroVIR",
        # Places: cities and a named institute site
        "Plovdiv",
        "Budapest",
        "Maritsa",
    }
)

#: Named tools and materials distinctive to instance one. None is an
#: organisation, but the set re-identifies the reference project, and instance
#: two has no use for any of them.
REIDENTIFYING_NOUNS: frozenset[str] = frozenset(
    {
        "AquaCrop",
        "PlanetScope",
        "tomato",
        "biostimulant",
    }
)

#: Denylisted nouns deliberately **not** scanned, each with the reason. See the
#: module docstring: the constraint names organisations, people, places,
#: addresses and identifiers, and none of these is one.
SCOPED_OUT: dict[str, str] = {
    "Hungary": (
        "A Member State name the General Annexes enumerate verbatim (page 12) "
        "and the rule-of-law measure names (page 11). A Tier 4 report that "
        "records the eligibility rules must reproduce it. Finding F9."
    ),
    "Hungarian": (
        "A nationality the General Annexes use in the rule-of-law measure "
        "(page 11), quoted in the Tier 1 coverage report. Finding F9."
    ),
    "Bulgaria": (
        "A Member State name the General Annexes enumerate verbatim (page 12). "
        "Finding F9."
    ),
    "Bulgarian": (
        "The nationality of a Member State the General Annexes enumerate. "
        "Finding F9."
    ),
    "MSCA": (
        "A Tier 2A instrument name, and the name of engine artifacts that exist "
        "under it (harness/profiles/msca_pf_default.json). An instrument is not "
        "an organisation, person, place or identifier. Finding F2 of the demo "
        "scope record."
    ),
    "crop": (
        "A generic agricultural word the topic's own scope uses. Finding F2 of "
        "the demo scope record: this scan covers proper nouns, not domain nouns."
    ),
    "irrigation": (
        "A generic word for a farming practice. Not distinctive to one project."
    ),
    "hyperspectral": (
        "A generic remote-sensing term, and one of the derived capabilities the "
        "consortium ticket carries into instance two by name. Finding F2."
    ),
}

#: Instance one's own project identifier. The standing agnosticism denylist never
#: held it: that denylist was built from instance one's Tier 3 identity spine
#: (``roles.json``, ``project_summary.json``), which names the fellow, the host
#: and the partners, not the project. The acronym is a project identifier, which
#: the branch constraint names outright, and it is already present on the branch,
#: so naming it here adds nothing that is not already recorded and is the only way
#: to stop the next one.
PROJECT_IDENTIFIERS: frozenset[str] = frozenset({"FIELDWISE"})

#: The nouns this scan matches, **derived** rather than re-typed: everything on
#: the standing denylist except the scoped-out set, plus the project identifiers
#: that denylist never held. Derivation is the point — a noun added to
#: ``PROJECT_NOUNS`` later is scanned from that moment, with no edit here. The two
#: category constants above document *why* each retained noun is a leak; this is
#: what the scan actually matches.
LEAKAGE_NOUNS: frozenset[str] = (
    PROJECT_NOUNS - frozenset(SCOPED_OUT)
) | PROJECT_IDENTIFIERS


# ---------------------------------------------------------------------------
# Scope — what the scan reads
# ---------------------------------------------------------------------------

#: Repo-relative globs covering Tier 3, Tier 4, Tier 5 and the conventional vault
#: locations. Tier 1 and Tier 2 are deliberately out of scope: they are source
#: documents and their extracts, and §13.11 forbids editing them to suit a
#: project anyway. A vault placed somewhere else is still covered, because
#: :func:`iter_vault_roots` discovers it from its ``graph.config.yaml``.
SCAN_GLOBS: tuple[str, ...] = (
    "docs/tier3_project_instantiation/**/*",
    "docs/tier4_orchestration_state/**/*",
    "docs/tier5_deliverables/**/*",
    "vault/**/*",
    "docs/vault/**/*",
)

#: Every per-project graph binding. Each one names its vault in ``vault_path``,
#: so a vault is found where it is rather than where a glob guessed it would be.
VAULT_CONFIG_GLOB: str = "**/graph.config.yaml"

#: Path prefixes whose ``graph.config.yaml`` is not a project vault: the generic
#: template (which is instance-agnostic by construction and covered by the
#: agnosticism lint instead) and test fixtures.
_NON_PROJECT_CONFIG_PREFIXES: tuple[str, ...] = (
    "templates/",
    "tests/",
    ".git/",
)

#: File suffixes the scan reads. Anything else under a matched glob is skipped.
_TEXT_SUFFIXES: frozenset[str] = frozenset(
    {".json", ".md", ".yaml", ".yml", ".txt", ".csv"}
)

#: Path segments never scanned: the Obsidian app directory is vendored state.
_EXCLUDED_SEGMENTS: frozenset[str] = frozenset({".obsidian"})

#: Repo-relative Tier 1 source of the real country lists, and the Tier 3 partner
#: registry. Both are re-exported from :mod:`runner.consortium_composition`, which
#: owns them, so the two checks can never disagree about where a tier artifact is.
PARTICIPATION_RULES_REL = _PARTICIPATION_RULES_REL
PARTNERS_REL = _PARTNERS_REL

#: The Tier 3 *JSON* artifacts the pseudonymity check reads, as repo-relative
#: globs. The prose leg is :data:`PSEUDONYMITY_TEXT_GLOBS`. A real
#: country name matters wherever the project describes itself, not only in the
#: partner registry: a country written into a role, a declaration or the brief
#: re-identifies a derived partner just as effectively. Country and nationality
#: names are :data:`SCOPED_OUT` of the word scan, so this is the *only* mechanism
#: that catches them, and it has to reach every artifact that can carry one.
PSEUDONYMITY_JSON_GLOBS: tuple[str, ...] = (
    "docs/tier3_project_instantiation/consortium/*.json",
    "docs/tier3_project_instantiation/working_assumptions.json",
    "docs/tier3_project_instantiation/project_brief/*.json",
    "docs/tier3_project_instantiation/architecture_inputs/*.json",
    "docs/tier3_project_instantiation/call_binding/compliance_profile.json",
)

#: Tier 3 *prose* the pseudonymity check reads, as repo-relative globs. The
#: brief is the project describing itself in sentences, and a real country name
#: in a sentence re-identifies a derived partner exactly as one in a field does.
#: The word scan already reads these files, but country and nationality names are
#: :data:`SCOPED_OUT` of it, so without this leg no mechanism looked at them.
PSEUDONYMITY_TEXT_GLOBS: tuple[str, ...] = (
    "docs/tier3_project_instantiation/project_brief/*.md",
)

#: Paths excluded from the pseudonymity check, with the reason. ``selected_call``
#: is a Tier 2B-derived record, not a self-description of the project: it carries
#: the call's own text, which may name a country the work programme names.
PSEUDONYMITY_EXEMPT: dict[str, str] = {
    "docs/tier3_project_instantiation/working_assumptions.example.json": (
        "An inert template shipped with the engine, not this project's data. It "
        "declares a host country by design, to show the file's shape."
    ),
}

#: Leaks that predate this branch, each pinned to its path with the reason it is
#: recorded rather than removed. A hit at one of these paths is reported as
#: ``pre_existing`` and does not fail the scan; a hit anywhere else does. The
#: point is a check that stays useful: it cannot be green while the branch holds
#: a known leak, and it still fails loudly on a new one.
KNOWN_PRE_EXISTING_LEAKS: dict[str, str] = {
    "docs/tier4_orchestration_state/decision_log/"
    "project-purge-clean-engine-base_2026-09-22.json": (
        "The 22 September purge record, written before this branch opened. It "
        "names the purged project because that is what it records. Redacting it "
        "would rewrite a Tier 4 decision record to suit a later constraint, "
        "which CLAUDE.md §9.1 does not permit an implementing ticket to do. "
        "Whether to rewrite or retire it is an operator decision."
    ),
}

#: A web address inside a partner record. Deliberately anchored on a scheme or a
#: ``www.`` prefix rather than on a top-level domain: the records cite file paths
#: like ``partners.json``, and a bare-domain pattern would flag every one of them.
#: A bare domain with no scheme therefore passes, which the gap-analysis report
#: records rather than papering over.
_URL_RE: re.Pattern[str] = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)

#: An email address inside a partner record.
_EMAIL_RE: re.Pattern[str] = re.compile(
    r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.IGNORECASE
)


class LeakageError(Exception):
    """Raised when the scan cannot read a source it needs.

    Fail-closed: an unreadable Tier 1 country list means the pseudonymity check
    cannot run, and a check that cannot run must not report clean.
    """


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LeakageViolation:
    """One instance-one noun found where the branch forbids it."""

    path: str
    """Repo-relative POSIX path, or a JSON path for a record-level hit."""
    line: int
    """1-based line number, or ``0`` when the hit is located structurally."""
    noun: str
    """The matched text, verbatim."""
    snippet: str
    """The offending line or field, for an actionable report."""
    kind: str = "identity_noun"
    """``identity_noun``, ``country_name``, ``web_address`` or ``email``."""
    pre_existing: bool = False
    """True when the path is in :data:`KNOWN_PRE_EXISTING_LEAKS`."""


@dataclass(frozen=True)
class LeakageReport:
    """The outcome of a scan.

    Three outcomes, not two. ``ok`` means no new leak, which is what a regression
    guard has to answer. ``clean`` means no leak at all, new or pre-existing,
    which is what the anonymity constraint actually asks. Collapsing the two
    would let a recorded pre-existing leak be reported as clean.
    """

    scanned_files: tuple[str, ...]
    violations: tuple[LeakageViolation, ...]

    @property
    def new_violations(self) -> tuple[LeakageViolation, ...]:
        """Violations at paths not recorded as pre-existing."""
        return tuple(v for v in self.violations if not v.pre_existing)

    @property
    def pre_existing_violations(self) -> tuple[LeakageViolation, ...]:
        """Violations at paths :data:`KNOWN_PRE_EXISTING_LEAKS` records."""
        return tuple(v for v in self.violations if v.pre_existing)

    @property
    def ok(self) -> bool:
        """True when the scan found no *new* leak. The regression guard."""
        return not self.new_violations

    @property
    def clean(self) -> bool:
        """True when the scan found no leak at all. The constraint itself."""
        return not self.violations

    def format(self) -> str:
        """Render a human-readable summary."""
        head = f"{len(self.scanned_files)} file(s) scanned in Tier 3, Tier 4, Tier 5 and the vault"
        if self.clean:
            return f"[leakage-scan] OK — {head}, no instance-one noun found."
        lines: list[str] = []
        if self.ok:
            lines.append(
                f"[leakage-scan] OK, NOT CLEAN — {head}. No new leak. "
                f"{len(self.pre_existing_violations)} recorded pre-existing "
                f"leak(s) remain:"
            )
        else:
            lines.append(
                f"[leakage-scan] FAIL — {len(self.new_violations)} new "
                f"instance-one leak(s) ({head}):"
            )
        for v in self.violations:
            where = f"{v.path}:{v.line}" if v.line else v.path
            tag = "pre-existing" if v.pre_existing else v.kind
            lines.append(f"  {where}: [{tag}] {v.noun!r} — {v.snippet}")
        if self.ok:
            for path, reason in sorted(KNOWN_PRE_EXISTING_LEAKS.items()):
                lines.append(f"  recorded: {path} — {reason}")
        else:
            lines.append(
                "Instance two is anonymised: no organisation name, person name, "
                "place, web address, grant or project identifier from instance "
                "one may appear in Tier 3, Tier 4, Tier 5 or the vault. Replace "
                "the noun with its pseudonym."
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# The denylist and the word scan (pure)
# ---------------------------------------------------------------------------


def leakage_denylist(extra_nouns: Iterable[str] = ()) -> re.Pattern[str]:
    """Compile the scan pattern: :data:`LEAKAGE_NOUNS` plus operator additions.

    Word-boundary and case-insensitive, so ``ELTE`` never hits ``Svelte``.
    Sorted longest-first, so an overlapping longer noun wins the report.
    """
    nouns = set(LEAKAGE_NOUNS) | {n.strip() for n in extra_nouns if n.strip()}
    return re.compile(
        r"\b(?:"
        + "|".join(re.escape(n) for n in sorted(nouns, key=len, reverse=True))
        + r")\b",
        re.IGNORECASE | re.UNICODE,
    )


def scan_text(text: str, pattern: re.Pattern[str]) -> list[tuple[int, str, str]]:
    """Find every denylisted noun in *text*.

    Returns ``(line_number, matched_noun, stripped_line)`` in document order —
    the pure seam the file scan and the tests both drive.
    """
    out: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in pattern.finditer(line):
            out.append((lineno, match.group(0), line.strip()))
    return out


# ---------------------------------------------------------------------------
# File enumeration
# ---------------------------------------------------------------------------


def iter_vault_roots(repo_root: Path) -> list[Path]:
    """Find every project vault, by the ``vault_path`` of its graph binding.

    A vault holds authored project notes, so it is exactly where a real name
    would end up if one slipped in. Discovery beats a guessed path: the ticket
    that scaffolds a vault chooses where it goes, and this scan has to cover it
    wherever that is.

    Conservative on failure. If a ``graph.config.yaml`` exists but its
    ``vault_path`` cannot be read, the directory holding the config is scanned
    instead. Scanning too much is the safe direction for a leakage check.
    """
    roots: dict[str, Path] = {}
    for config in repo_root.glob(VAULT_CONFIG_GLOB):
        rel = config.relative_to(repo_root).as_posix()
        if rel.startswith(_NON_PROJECT_CONFIG_PREFIXES):
            continue
        target = config.parent
        try:
            # Imported here, not at module scope, so the scan still runs in an
            # environment without PyYAML. An import failure lands in the except
            # below and widens the scan, which is the safe direction.
            import yaml

            declared = yaml.safe_load(config.read_text(encoding="utf-8-sig")) or {}
            vault_path = declared.get("vault_path")
            if isinstance(vault_path, str) and vault_path.strip():
                candidate = (config.parent / vault_path.strip()).resolve()
                if candidate.is_dir() and repo_root.resolve() in candidate.parents:
                    target = candidate
        except Exception:  # noqa: BLE001 — an unreadable config widens the scan
            pass
        roots[target.resolve().as_posix()] = target
    return [roots[key] for key in sorted(roots)]


def iter_scanned_files(repo_root: Path) -> list[Path]:
    """Resolve the scan scope to the text files to read, deterministically.

    :data:`SCAN_GLOBS` plus every discovered vault root.
    """
    seen: dict[str, Path] = {}
    patterns = list(SCAN_GLOBS)
    for vault in iter_vault_roots(repo_root):
        patterns.append(
            vault.relative_to(repo_root.resolve()).as_posix() + "/**/*"
        )
    for pattern in patterns:
        for path in repo_root.glob(pattern):
            if not path.is_file() or path.suffix.lower() not in _TEXT_SUFFIXES:
                continue
            rel = path.relative_to(repo_root)
            if any(part in _EXCLUDED_SEGMENTS for part in rel.parts):
                continue
            seen[rel.as_posix()] = path
    return [seen[key] for key in sorted(seen)]


def scan_tree(
    repo_root: Path, *, extra_nouns: Iterable[str] = ()
) -> LeakageReport:
    """Scan Tier 3, Tier 4, Tier 5 and the vault for instance-one nouns."""
    pattern = leakage_denylist(extra_nouns)
    violations: list[LeakageViolation] = []
    scanned: list[str] = []
    for path in iter_scanned_files(repo_root):
        rel = path.relative_to(repo_root).as_posix()
        scanned.append(rel)
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        known = rel in KNOWN_PRE_EXISTING_LEAKS
        for lineno, noun, snippet in scan_text(text, pattern):
            violations.append(
                LeakageViolation(
                    path=rel,
                    line=lineno,
                    noun=noun,
                    snippet=snippet,
                    pre_existing=known,
                )
            )
    return LeakageReport(scanned_files=tuple(scanned), violations=tuple(violations))


# ---------------------------------------------------------------------------
# The pseudonymity check over the partner records
# ---------------------------------------------------------------------------


def _read_json_object(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise LeakageError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise LeakageError(f"{path} must hold a JSON object")
    return data


def real_country_names(rules_root: Path) -> frozenset[str]:
    """Read the real country names out of Tier 1 ``participation_rules.json``.

    Member States, Associated Countries and the Overseas Countries and
    Territories. Read rather than listed, so the check cannot drift from the
    General Annexes (CLAUDE.md §10.6). Fails closed when Tier 1 is unreadable.
    """
    path = rules_root / PARTICIPATION_RULES_REL
    if not path.is_file():
        raise LeakageError(
            f"Tier 1 country lists are absent ({PARTICIPATION_RULES_REL}). The "
            "pseudonymity check cannot run, so it must not report clean."
        )
    funding = _read_json_object(path).get("entities_eligible_for_funding")
    if not isinstance(funding, dict):
        raise LeakageError(
            f"{PARTICIPATION_RULES_REL} carries no "
            "'entities_eligible_for_funding' block."
        )
    names: set[str] = set()
    for block_key in (
        "member_states",
        "associated_countries",
        "overseas_countries_and_territories",
    ):
        block = funding.get(block_key)
        if not isinstance(block, dict):
            raise LeakageError(
                f"{PARTICIPATION_RULES_REL} carries no '{block_key}' block."
            )
        for entry in block.get("countries") or ():
            if not isinstance(entry, str):
                continue
            # "Aruba (NL)" — the territory name is the part before the bracket.
            name = entry.split("(")[0].strip()
            if len(name) > 2:
                names.add(name)
    if not names:
        raise LeakageError(
            f"{PARTICIPATION_RULES_REL} yielded no country name. The "
            "pseudonymity check would pass vacuously."
        )
    return frozenset(names)


def _iter_strings(node: object, where: str) -> Iterable[tuple[str, str]]:
    """Yield ``(json_path, string)`` for every string in the tree."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield from _iter_strings(value, f"{where}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _iter_strings(value, f"{where}[{index}]")
    elif isinstance(node, str):
        yield where, node


def _iter_globbed(repo_root: Path, globs: Iterable[str]) -> list[Path]:
    """Resolve *globs* to existing files, deterministically, minus exemptions.

    Both pseudonymity legs resolve their scope the same way and drop the same
    declared exemptions. One resolver means an exemption can never apply to one
    leg and not the other.
    """
    seen: dict[str, Path] = {}
    for pattern in globs:
        for path in repo_root.glob(pattern):
            if not path.is_file():
                continue
            rel = path.relative_to(repo_root).as_posix()
            if rel in PSEUDONYMITY_EXEMPT:
                continue
            seen[rel] = path
    return [seen[key] for key in sorted(seen)]


def iter_pseudonymity_files(repo_root: Path) -> list[Path]:
    """The JSON leg's scope: :data:`PSEUDONYMITY_JSON_GLOBS`."""
    return _iter_globbed(repo_root, PSEUDONYMITY_JSON_GLOBS)


def iter_pseudonymity_text_files(repo_root: Path) -> list[Path]:
    """The prose leg's scope: :data:`PSEUDONYMITY_TEXT_GLOBS`."""
    return _iter_globbed(repo_root, PSEUDONYMITY_TEXT_GLOBS)


def scan_partner_records(
    repo_root: Path, *, rules_root: Optional[Path] = None
) -> tuple[LeakageViolation, ...]:
    """Check that no Tier 3 self-description carries a real country or address.

    The structural half of the constraint, and the *only* mechanism that catches
    a country name: country and nationality names are :data:`SCOPED_OUT` of the
    word scan, because Tier 1 enumerates them and a Tier 4 report may discuss
    them. So this reads every artifact in :data:`PSEUDONYMITY_JSON_GLOBS`, not the
    partner registry alone — a country written into a role, a declaration or a
    seed re-identifies a derived partner just as effectively.

    It reads the Tier 3 *prose* in :data:`PSEUDONYMITY_TEXT_GLOBS` on the same
    grounds. The brief is the project describing itself in sentences, so it can
    carry a country the same way a field can. A JSON hit is located by field
    path and reports line ``0``; a prose hit reports its line number.

    An absent artifact yields no violation: an empty Tier 3 is a valid state, not
    a leak. An unreadable Tier 1 raises :class:`LeakageError`, because a check
    that cannot run must not report clean.
    """
    targets = iter_pseudonymity_files(repo_root)
    text_targets = iter_pseudonymity_text_files(repo_root)
    if not targets and not text_targets:
        return ()

    countries = real_country_names(rules_root if rules_root else repo_root)
    country_re = re.compile(
        r"\b(?:"
        + "|".join(re.escape(c) for c in sorted(countries, key=len, reverse=True))
        + r")\b"
    )
    patterns = (
        (country_re, "country_name"),
        (_URL_RE, "web_address"),
        (_EMAIL_RE, "email"),
    )

    violations: list[LeakageViolation] = []
    for path in targets:
        rel = path.relative_to(repo_root).as_posix()
        for json_path, value in _iter_strings(_read_json_object(path), "$"):
            for pattern, kind in patterns:
                for match in pattern.finditer(value):
                    violations.append(
                        LeakageViolation(
                            path=f"{rel} {json_path}",
                            line=0,
                            noun=match.group(0),
                            snippet=value,
                            kind=kind,
                        )
                    )
    for path in text_targets:
        rel = path.relative_to(repo_root).as_posix()
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for pattern, kind in patterns:
            for lineno, noun, snippet in scan_text(text, pattern):
                violations.append(
                    LeakageViolation(
                        path=rel,
                        line=lineno,
                        noun=noun,
                        snippet=snippet,
                        kind=kind,
                    )
                )
    return tuple(violations)


# ---------------------------------------------------------------------------
# CLI  (python -m runner.leakage_scan)
# ---------------------------------------------------------------------------


def _read_extra_nouns(path_text: Optional[str]) -> tuple[str, ...]:
    """Read the operator's noun extension, one noun per line, outside the repo."""
    if not path_text:
        return ()
    path = Path(path_text).expanduser()
    if not path.is_file():
        raise LeakageError(f"--extra-nouns file not found: {path}")
    return tuple(
        line.strip()
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Run the leakage scan from the command line.

    Exit codes: ``0`` clean; ``1`` one or more leaks found; ``3`` a source the
    scan needs could not be read.
    """
    parser = argparse.ArgumentParser(
        prog="python -m runner.leakage_scan",
        description=(
            "Scan Tier 3, Tier 4, Tier 5 and the vault for instance-one "
            "organisation names, people, places, web addresses and identifiers."
        ),
    )
    parser.add_argument("--repo-root", default=None)
    parser.add_argument(
        "--extra-nouns",
        default=None,
        help=(
            "Path to a newline-separated list of further instance-one nouns. "
            "Keep the file OUTSIDE the repository: writing those names into the "
            "branch is the leak this scan exists to prevent."
        ),
    )
    args = parser.parse_args(argv)

    from runner.paths import find_repo_root

    try:
        repo_root = (
            Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
        )
        report = scan_tree(repo_root, extra_nouns=_read_extra_nouns(args.extra_nouns))
        record_violations = scan_partner_records(repo_root)
    except LeakageError as exc:
        print(f"[leakage-scan] ERROR: {exc}", file=sys.stderr, flush=True)
        return 3
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"[leakage-scan] ERROR: {exc}", file=sys.stderr, flush=True)
        return 3

    combined = LeakageReport(
        scanned_files=report.scanned_files,
        violations=report.violations + record_violations,
    )
    if combined.ok:
        # Exit 0 on "no new leak", so the scan is usable as a regression guard
        # while a recorded pre-existing leak stands. The report still says NOT
        # CLEAN, so a reader is never told the branch is clean when it is not.
        print(combined.format(), flush=True)
        return 0
    print(combined.format(), file=sys.stderr, flush=True)
    return 1


if __name__ == "__main__":
    sys.exit(main())
