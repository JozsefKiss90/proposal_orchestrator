"""
Expectation substrate — registry loader + PF filter + criterion↔section map (E5a).

The E5 rubric grader grades the Tier-5 sections against the MSCA-PF evaluator
expectations.  Those expectations live in two places with two roles:

* the **raw upstream extraction** —
  ``docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json``
  (Tier 2A), which holds **10** rows for MSCA-PF including the COFUND
  *recruiting-institutions* variant that must **not** be graded for a PF
  proposal; and
* the **binding, human-verified subset** —
  ``harness/evaluator_scorecard_msca_pf.json``, the verbatim freeze of the
  official *HE MSCA Evaluation Form V2.2* (pp.4-6, verified 2026-08-07), whose
  9 aspects are the PF-applicable set.

This module derives the 10→9 filter **deterministically from the ``[OPTION for
…]`` applicability tags** and then requires the result to *reproduce* the
scorecard exactly — the scorecard is the anchor the filter reproduces, never a
second hand-maintained copy, and the filter is never a hand-copied constant.
Any divergence (a registry row added/dropped/reworded, an unrecognised tag, an
unmapped criterion, a stale scorecard against a newer form version) **fails
closed**: the loader raises rather than silently grading a subset.

Each expectation is addressable by a stable ``expectation_key`` — the scorecard
aspect ``id`` (``exc-*`` / ``imp-*`` / ``impl-*``) — because the verbatim text
is long and will be re-worded upstream: the E3 *"claim_id is not a key"* lesson
applied to expectations.  Each criterion is mapped to the frozen section
artifact(s) it is graded against, so the grader never guesses which prose
answers which expectation.

Zero judge, zero DAG runs — pure deterministic loading; E5b builds the rubric
set and evidence packs on top of this substrate.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA; reads the Tier-2A registry and
    the harness-owned scorecard read-only and writes nothing.  Never a runtime
    gate.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from harness.regression import DEFAULT_GOLDEN_DIR, DEFAULT_SECTIONS_DIR, GOLDEN_SUFFIX

__all__ = [
    "ExpectationError",
    "DEFAULT_REGISTRY_PATH",
    "DEFAULT_SCORECARD_PATH",
    "REGISTRY_INSTRUMENT_TYPE",
    "PF_VARIANT",
    "KNOWN_VARIANTS",
    "TAG_KIND_INCLUSION",
    "TAG_KIND_ALL_EXCEPT",
    "OptionTag",
    "parse_option_tag",
    "Expectation",
    "ExcludedExpectation",
    "ExpectationSubstrate",
    "load_expectation_substrate",
    "CRITERION_SECTION_IDS",
    "section_ids_for",
    "section_paths_for",
    "golden_paths_for",
]

#: The Tier-2A raw extraction the filter runs over (repo-relative).
DEFAULT_REGISTRY_PATH: Path = Path(
    "docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json"
)

#: The human-verified verbatim freeze of the official evaluation form
#: (repo-relative; harness-owned) — the anchor the deterministic filter
#: must reproduce.
DEFAULT_SCORECARD_PATH: Path = Path("harness/evaluator_scorecard_msca_pf.json")

#: The registry ``instrument_type`` this substrate grades against.
REGISTRY_INSTRUMENT_TYPE: str = "MSCA-PF"

#: The MSCA instrument variant that makes a tag PF-applicable.
PF_VARIANT: str = "Postdoctoral fellowships"

#: The closed vocabulary of MSCA instrument variants an ``[OPTION …]`` tag may
#: name (normalized, leading ``MSCA `` stripped).  An unknown variant is a
#: fail-closed error, never a silent skip.
KNOWN_VARIANTS: frozenset[str] = frozenset(
    {
        "Doctoral networks",
        "Postdoctoral fellowships",
        "Staff exchanges",
        "COFUND Choose Europe",
        "Special needs allowances",
    }
)

#: Tag grammar: an explicit list of applicable variants …
TAG_KIND_INCLUSION: str = "inclusion"
#: … or the ``all MSCA except <variants>`` exception form.
TAG_KIND_ALL_EXCEPT: str = "all_msca_except"

#: Criterion → the frozen section artifact stem(s) it is graded against.
CRITERION_SECTION_IDS: Mapping[str, tuple[str, ...]] = {
    "excellence": ("excellence_section",),
    "impact": ("impact_section",),
    "implementation": ("implementation_section",),
}

#: Registry ``criterion_id`` → scorecard criterion id.
_CRITERION_MAP: Mapping[str, str] = {
    "Excellence": "excellence",
    "Impact": "impact",
    "Implementation": "implementation",
}

#: Matches the inline applicability tag inside a registry expectation row.
_OPTION_TAG_RE = re.compile(r"\[OPTION for ([^\[\]]+)\]")

_ALL_EXCEPT_PREFIX = "all msca except "


class ExpectationError(Exception):
    """The registry/scorecard is missing, malformed, or has drifted (fail-closed)."""


# --------------------------------------------------------------------------- #
# Option-tag grammar
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class OptionTag:
    """One parsed ``[OPTION for …]`` applicability tag.

    ``variants`` is the normalized variant list (leading ``MSCA `` stripped) —
    the applicable instruments for :data:`TAG_KIND_INCLUSION`, the *excluded*
    instruments for :data:`TAG_KIND_ALL_EXCEPT`.  ``source`` records where the
    tag came from: ``"registry"`` (inline in the row) or ``"scorecard"`` (the
    verified form, for the registry rows that carry no inline tag).
    """

    raw: str
    kind: str
    variants: tuple[str, ...]
    source: str

    @property
    def pf_applicable(self) -> bool:
        """Whether this tag applies to MSCA Postdoctoral Fellowships."""
        if self.kind == TAG_KIND_ALL_EXCEPT:
            return PF_VARIANT not in self.variants
        return PF_VARIANT in self.variants


def _split_variants(text: str) -> tuple[str, ...]:
    parts: list[str] = []
    for chunk in text.split(","):
        for piece in chunk.split(" and "):
            piece = " ".join(piece.split()).strip()
            if piece.lower().startswith("msca "):
                piece = piece[len("msca "):]
            if piece:
                parts.append(piece)
    return tuple(parts)


def parse_option_tag(raw: str, *, source: str) -> OptionTag:
    """Parse the inner text of an ``[OPTION for …]`` tag, fail-closed.

    Grammar: either a comma/``and``-separated inclusion list of variants, or
    ``all MSCA except <variants>``.  Every named variant must be in
    :data:`KNOWN_VARIANTS`; anything else raises — an unrecognised tag must
    break the load, not silently grade (or skip) a row.
    """
    text = " ".join(raw.split()).strip()
    if not text:
        raise ExpectationError("empty [OPTION ...] tag.")
    if text.lower().startswith(_ALL_EXCEPT_PREFIX):
        kind = TAG_KIND_ALL_EXCEPT
        variants = _split_variants(text[len(_ALL_EXCEPT_PREFIX):])
    else:
        kind = TAG_KIND_INCLUSION
        variants = _split_variants(text)
    if not variants:
        raise ExpectationError(f"[OPTION ...] tag names no variants: {text!r}")
    unknown = [v for v in variants if v not in KNOWN_VARIANTS]
    if unknown:
        raise ExpectationError(
            f"unrecognised [OPTION ...] tag {text!r}: unknown variant(s) "
            f"{unknown} (known: {sorted(KNOWN_VARIANTS)})."
        )
    return OptionTag(raw=text, kind=kind, variants=variants, source=source)


# --------------------------------------------------------------------------- #
# Text matching — registry row ↔ scorecard entry
# --------------------------------------------------------------------------- #


def _match_key(text: str) -> str:
    """Normalize for meaning comparison: collapse whitespace, lowercase, and
    strip a single trailing period (the scorecard keeps the form's punctuation,
    the registry drops it) — but never a trailing ``...`` wildcard."""
    s = " ".join(text.split()).strip().lower()
    if s.endswith(".") and not s.endswith("..."):
        s = s[:-1]
    return s


def _scorecard_text_matches(scorecard_text: str, registry_text: str) -> bool:
    """Whether a scorecard entry's text matches a registry row's text.

    The scorecard is verbatim except that it may abbreviate a long
    parenthetical with ``...`` (the excluded COFUND item does); ``...`` is
    treated as a wildcard.  Without a wildcard the normalized texts must be
    equal — a rewording upstream must *not* match (fail-closed drift).
    """
    sc = _match_key(scorecard_text)
    reg = _match_key(registry_text)
    if "..." not in sc:
        return sc == reg
    segments = sc.split("...")
    pos = 0
    for i, seg in enumerate(segments):
        seg = seg.strip()
        if not seg:
            continue
        idx = reg.find(seg, pos)
        if idx < 0:
            return False
        if i == 0 and idx != 0:
            return False
        pos = idx + len(seg)
    if segments[-1].strip() and pos != len(reg):
        return False
    return True


# --------------------------------------------------------------------------- #
# Substrate model
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Expectation:
    """One PF-applicable evaluator expectation, addressable by a stable key.

    ``expectation_key`` is the scorecard aspect ``id`` (``exc-obj`` …), never a
    hash or index of the verbatim text — the text is long and will be
    re-worded upstream.  ``text`` is the scorecard's verbatim form text (the
    E5b rubric wording source, auditable to a page of the official form);
    ``registry_text`` is the matched registry row with its inline tag stripped.
    """

    expectation_key: str
    criterion_id: str
    criterion_name: str
    registry_criterion_id: str
    text: str
    registry_text: str
    option_tag: OptionTag
    source_page: int | str | None
    section_ids: tuple[str, ...]


@dataclass(frozen=True)
class ExcludedExpectation:
    """A registry row filtered out as not PF-applicable (kept for the record)."""

    criterion_id: str
    registry_text: str
    option_tag: OptionTag
    reason: str


@dataclass(frozen=True)
class ExpectationSubstrate:
    """The loaded, cross-checked expectation set the E5 grader runs over."""

    instrument_type: str
    scorecard_id: str
    scorecard_version: str
    raw_count: int
    expectations: tuple[Expectation, ...]
    excluded: tuple[ExcludedExpectation, ...]

    def by_key(self) -> dict[str, Expectation]:
        """The PF expectations keyed by ``expectation_key``."""
        return {e.expectation_key: e for e in self.expectations}

    def for_criterion(self, criterion_id: str) -> tuple[Expectation, ...]:
        """The PF expectations of one criterion; unknown criterion fails closed."""
        _require_known_criterion(criterion_id)
        return tuple(e for e in self.expectations if e.criterion_id == criterion_id)


# --------------------------------------------------------------------------- #
# Loading — fail-closed on every drift
# --------------------------------------------------------------------------- #


def _load_json(path: Path, what: str) -> Any:
    if not path.is_file():
        raise ExpectationError(f"{what} not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ExpectationError(f"{what} {path} is not valid JSON: {exc}") from exc


def _registry_rows(registry: Any) -> list[tuple[str, str]]:
    """Extract the MSCA-PF rows as ``(registry_criterion_id, row_text)`` pairs."""
    instruments = registry.get("instruments") if isinstance(registry, dict) else None
    if not isinstance(instruments, list):
        raise ExpectationError("registry has no 'instruments' array.")
    matches = [
        i
        for i in instruments
        if isinstance(i, dict) and i.get("instrument_type") == REGISTRY_INSTRUMENT_TYPE
    ]
    if len(matches) != 1:
        raise ExpectationError(
            f"registry must hold exactly one {REGISTRY_INSTRUMENT_TYPE!r} instrument "
            f"(found {len(matches)})."
        )
    rows: list[tuple[str, str]] = []
    for criterion in matches[0].get("criteria", []):
        cid = str(criterion.get("criterion_id", ""))
        expectations = criterion.get("evaluator_expectations")
        if not isinstance(expectations, list) or not expectations:
            raise ExpectationError(
                f"registry criterion {cid!r} has no evaluator_expectations."
            )
        for row in expectations:
            rows.append((cid, str(row)))
    if not rows:
        raise ExpectationError("registry holds no expectation rows.")
    return rows


@dataclass(frozen=True)
class _ScorecardEntry:
    """One scorecard target a registry row must match: an aspect or an exclusion."""

    is_aspect: bool
    criterion_id: str
    criterion_name: str
    aspect_id: str  # "" for an excluded entry
    text: str
    option_tag_raw: str
    source_page: int | str | None
    reason: str  # "" for an aspect


def _scorecard_entries(
    scorecard: Any,
) -> tuple[list[_ScorecardEntry], str, str]:
    if not isinstance(scorecard, dict):
        raise ExpectationError("scorecard is not a JSON object.")
    criteria = scorecard.get("criteria")
    if not isinstance(criteria, list) or not criteria:
        raise ExpectationError("scorecard has no 'criteria' array.")
    entries: list[_ScorecardEntry] = []
    for criterion in criteria:
        cid = str(criterion.get("id", ""))
        cname = str(criterion.get("name", ""))
        _require_known_criterion(cid)
        aspects = criterion.get("aspects")
        if not isinstance(aspects, list) or not aspects:
            raise ExpectationError(f"scorecard criterion {cid!r} has no aspects.")
        for aspect in aspects:
            if not all(aspect.get(k) for k in ("id", "text", "option_tag")):
                raise ExpectationError(
                    f"scorecard aspect in {cid!r} is missing id/text/option_tag."
                )
            entries.append(
                _ScorecardEntry(
                    is_aspect=True,
                    criterion_id=cid,
                    criterion_name=cname,
                    aspect_id=str(aspect["id"]),
                    text=str(aspect["text"]),
                    option_tag_raw=str(aspect["option_tag"]),
                    source_page=aspect.get("source_page"),
                    reason="",
                )
            )
    for item in scorecard.get("excluded_for_pf", []):
        cid = str(item.get("criterion", ""))
        _require_known_criterion(cid)
        if not item.get("text") or not item.get("option_tag"):
            raise ExpectationError("scorecard excluded_for_pf entry is incomplete.")
        entries.append(
            _ScorecardEntry(
                is_aspect=False,
                criterion_id=cid,
                criterion_name="",
                aspect_id="",
                text=str(item["text"]),
                option_tag_raw=str(item["option_tag"]),
                source_page=item.get("source_page"),
                reason=str(item.get("reason", "")),
            )
        )
    version = str(scorecard.get("provenance", {}).get("version", ""))
    return entries, str(scorecard.get("scorecard_id", "")), version


def _require_known_criterion(criterion_id: str) -> None:
    if criterion_id not in CRITERION_SECTION_IDS:
        raise ExpectationError(
            f"unmapped criterion {criterion_id!r} (known: "
            f"{sorted(CRITERION_SECTION_IDS)})."
        )


def _resolve_tag(
    inline_raw: str | None, entry: _ScorecardEntry, registry_text: str
) -> OptionTag:
    """Resolve a row's applicability tag: inline if present, else the scorecard's.

    When both exist they must agree (same grammar form, same variant set) —
    a divergence means either the registry or the scorecard moved without the
    other, which is exactly the drift this loader exists to catch.
    """
    scorecard_tag = parse_option_tag(entry.option_tag_raw, source="scorecard")
    if inline_raw is None:
        return scorecard_tag
    inline_tag = parse_option_tag(inline_raw, source="registry")
    if (
        inline_tag.kind != scorecard_tag.kind
        or frozenset(inline_tag.variants) != frozenset(scorecard_tag.variants)
    ):
        raise ExpectationError(
            f"registry [OPTION ...] tag diverges from the verified scorecard for "
            f"row {registry_text[:60]!r}: registry {inline_tag.raw!r} vs "
            f"scorecard {scorecard_tag.raw!r}."
        )
    return inline_tag


def load_expectation_substrate(
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
    scorecard_path: Path | str = DEFAULT_SCORECARD_PATH,
) -> ExpectationSubstrate:
    """Load, filter, and cross-check the MSCA-PF expectation set.

    Deterministic pipeline, every step fail-closed:

    1. Load the Tier-2A registry rows for :data:`REGISTRY_INSTRUMENT_TYPE` and
       the verified scorecard entries (aspects + ``excluded_for_pf``).
    2. Match every registry row to exactly one scorecard entry of the same
       (mapped) criterion by verbatim text — a bijection.  An unmatched,
       ambiguous, or left-over entry on either side raises: registry drift
       *or* a stale scorecard against a newer form version.
    3. Resolve each row's ``[OPTION …]`` tag (inline, cross-checked against the
       scorecard's; scorecard-supplied where the registry row is untagged) and
       apply the PF-applicability rule.
    4. Require the filter to reproduce the scorecard exactly: every aspect must
       come out PF-applicable, every ``excluded_for_pf`` entry must not.

    Returns the 9 PF expectations in scorecard order, addressable by
    ``expectation_key``, each mapped to its frozen section artifact(s).
    """
    registry = _load_json(Path(registry_path), "expectation registry")
    scorecard = _load_json(Path(scorecard_path), "evaluator scorecard")
    rows = _registry_rows(registry)
    entries, scorecard_id, scorecard_version = _scorecard_entries(scorecard)

    matched: dict[int, tuple[str, str, OptionTag]] = {}  # entry idx -> row info
    for registry_criterion_id, row_text in rows:
        criterion_id = _CRITERION_MAP.get(registry_criterion_id)
        if criterion_id is None:
            raise ExpectationError(
                f"unmapped registry criterion {registry_criterion_id!r} "
                f"(known: {sorted(_CRITERION_MAP)})."
            )
        tag_match = _OPTION_TAG_RE.search(row_text)
        inline_raw = tag_match.group(1) if tag_match else None
        registry_text = " ".join(_OPTION_TAG_RE.sub(" ", row_text).split()).strip()

        candidates = [
            i
            for i, entry in enumerate(entries)
            if i not in matched
            and entry.criterion_id == criterion_id
            and _scorecard_text_matches(entry.text, registry_text)
        ]
        if len(candidates) != 1:
            kind = "no" if not candidates else "multiple"
            raise ExpectationError(
                f"registry row matches {kind} scorecard entries under criterion "
                f"{criterion_id!r}: {registry_text[:80]!r} — registry drift or a "
                "stale scorecard against a newer form version."
            )
        entry = entries[candidates[0]]
        tag = _resolve_tag(inline_raw, entry, registry_text)
        matched[candidates[0]] = (registry_criterion_id, registry_text, tag)

    unmatched = [entries[i].text for i in range(len(entries)) if i not in matched]
    if unmatched:
        raise ExpectationError(
            f"{len(unmatched)} scorecard entr(y/ies) matched no registry row "
            f"(first: {unmatched[0][:80]!r}) — registry drift or a stale scorecard."
        )

    expectations: list[Expectation] = []
    excluded: list[ExcludedExpectation] = []
    for i, entry in enumerate(entries):
        registry_criterion_id, registry_text, tag = matched[i]
        if entry.is_aspect:
            if not tag.pf_applicable:
                raise ExpectationError(
                    f"scorecard aspect {entry.aspect_id!r} is not PF-applicable by "
                    f"its [OPTION ...] tag {tag.raw!r} — the deterministic filter "
                    "no longer reproduces the verified scorecard."
                )
            expectations.append(
                Expectation(
                    expectation_key=entry.aspect_id,
                    criterion_id=entry.criterion_id,
                    criterion_name=entry.criterion_name,
                    registry_criterion_id=registry_criterion_id,
                    text=entry.text,
                    registry_text=registry_text,
                    option_tag=tag,
                    source_page=entry.source_page,
                    section_ids=section_ids_for(entry.criterion_id),
                )
            )
        else:
            if tag.pf_applicable:
                raise ExpectationError(
                    f"scorecard excluded_for_pf entry is PF-applicable by its "
                    f"[OPTION ...] tag {tag.raw!r} ({registry_text[:60]!r}) — the "
                    "deterministic filter no longer reproduces the verified "
                    "scorecard."
                )
            excluded.append(
                ExcludedExpectation(
                    criterion_id=entry.criterion_id,
                    registry_text=registry_text,
                    option_tag=tag,
                    reason=entry.reason,
                )
            )

    return ExpectationSubstrate(
        instrument_type=REGISTRY_INSTRUMENT_TYPE,
        scorecard_id=scorecard_id,
        scorecard_version=scorecard_version,
        raw_count=len(rows),
        expectations=tuple(expectations),
        excluded=tuple(excluded),
    )


# --------------------------------------------------------------------------- #
# Criterion ↔ section artifact map
# --------------------------------------------------------------------------- #


def section_ids_for(criterion_id: str) -> tuple[str, ...]:
    """The frozen section artifact stem(s) a criterion is graded against."""
    _require_known_criterion(criterion_id)
    return CRITERION_SECTION_IDS[criterion_id]


def _resolve_paths(
    criterion_id: str, base: Path, suffix: str, what: str
) -> tuple[Path, ...]:
    paths = tuple(base / f"{sid}{suffix}" for sid in section_ids_for(criterion_id))
    missing = [p for p in paths if not p.is_file()]
    if missing:
        raise ExpectationError(
            f"{what} for criterion {criterion_id!r} not found: {missing[0]}"
        )
    return paths


def section_paths_for(
    criterion_id: str,
    *,
    repo_root: Path | str = Path("."),
    sections_dir: Path | str = DEFAULT_SECTIONS_DIR,
) -> tuple[Path, ...]:
    """The live Tier-5 section artifact(s) a criterion is graded against.

    Fail-closed: a mapped artifact that is absent on disk raises — the grader
    must never silently grade a criterion against nothing.
    """
    base = Path(repo_root) / Path(sections_dir)
    return _resolve_paths(criterion_id, base, ".json", "section artifact")


def golden_paths_for(
    criterion_id: str,
    *,
    repo_root: Path | str = Path("."),
    golden_dir: Path | str = DEFAULT_GOLDEN_DIR,
) -> tuple[Path, ...]:
    """The frozen E4 golden fingerprint(s) for a criterion (same fail-closed rule)."""
    base = Path(repo_root) / Path(golden_dir)
    return _resolve_paths(criterion_id, base, GOLDEN_SUFFIX, "golden baseline")
