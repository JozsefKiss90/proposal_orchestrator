"""
Expectation substrate — registry loader + applicability filter + criterion↔section map (E5a).

The E5 rubric grader grades the Tier-5 sections against the evaluator
expectations of the instrument a pre-evaluation profile names
(:mod:`harness.profile`).  Those expectations live in two places with two roles:

* the **raw upstream extraction** — the Tier-2A evaluator expectation registry
  the profile points at, which may hold rows for instrument variants that
  must **not** be graded for the profile's instrument; and
* the **binding, human-verified subset** — the profile's scorecard file, the
  verbatim freeze of the official evaluation form, whose aspects are the
  applicable set.

This module derives the applicability filter **deterministically from the
``[OPTION for …]`` applicability tags** under the profile's tag grammar, and
then requires the result to *reproduce* the scorecard exactly — the scorecard
is the anchor the filter reproduces, never a second hand-maintained copy, and
the filter is never a hand-copied constant.  Any divergence (a registry row
added/dropped/reworded, an unrecognised tag, an unmapped criterion, a stale
scorecard against a newer form version) **fails closed**: the loader raises
rather than silently grading a subset.  A scorecard-excluded aspect the
registry no longer carries is recorded as absent — it is not graded either
way, so the scorecard is still reproduced.

Each expectation is addressable by a stable ``expectation_key`` — the scorecard
aspect ``id`` — because the verbatim text is long and will be re-worded
upstream: the E3 *"claim_id is not a key"* lesson applied to expectations.
Each criterion is mapped to the frozen section artifact(s) it is graded
against by the profile, so the grader never guesses which prose answers which
expectation.

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
from typing import Any

from harness.profile import OptionTagGrammar, PreEvaluationProfile, ProfileError, default_profile
from harness.regression import DEFAULT_GOLDEN_DIR, DEFAULT_SECTIONS_DIR, GOLDEN_SUFFIX

__all__ = [
    "ExpectationError",
    "TAG_KIND_INCLUSION",
    "TAG_KIND_ALL_EXCEPT",
    "OptionTag",
    "parse_option_tag",
    "Expectation",
    "ExcludedExpectation",
    "ExpectationSubstrate",
    "load_expectation_substrate",
    "section_ids_for",
    "section_paths_for",
    "golden_paths_for",
]

#: Tag grammar: an explicit list of applicable variants …
TAG_KIND_INCLUSION: str = "inclusion"
#: … or the ``all <family> except <variants>`` exception form.
TAG_KIND_ALL_EXCEPT: str = "all_except"

#: Matches the inline applicability tag inside a registry expectation row.
_OPTION_TAG_RE = re.compile(r"\[OPTION for ([^\[\]]+)\]")


class ExpectationError(Exception):
    """The registry/scorecard is missing, malformed, or has drifted (fail-closed)."""


def _resolve_profile(profile: PreEvaluationProfile | None) -> PreEvaluationProfile:
    if profile is not None:
        return profile
    try:
        return default_profile()
    except ProfileError as exc:
        raise ExpectationError(str(exc)) from exc


# --------------------------------------------------------------------------- #
# Option-tag grammar
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class OptionTag:
    """One parsed ``[OPTION for …]`` applicability tag.

    ``variants`` is the normalized variant list (the grammar's variant prefix
    stripped) — the applicable instruments for :data:`TAG_KIND_INCLUSION`,
    the *excluded* instruments for :data:`TAG_KIND_ALL_EXCEPT`.  ``source``
    records where the tag came from: ``"registry"`` (inline in the row) or
    ``"scorecard"`` (the verified form, for the registry rows that carry no
    inline tag).  ``applicable`` is whether the tag applies to the profile's
    instrument variant, decided at parse time under the grammar.
    """

    raw: str
    kind: str
    variants: tuple[str, ...]
    source: str
    applicable: bool


def _split_variants(text: str, grammar: OptionTagGrammar) -> tuple[str, ...]:
    parts: list[str] = []
    prefix = grammar.variant_prefix.lower()
    for chunk in text.split(","):
        for piece in chunk.split(" and "):
            piece = " ".join(piece.split()).strip()
            if prefix and piece.lower().startswith(prefix):
                piece = piece[len(prefix):]
            if piece:
                parts.append(piece)
    return tuple(parts)


def parse_option_tag(raw: str, *, source: str, grammar: OptionTagGrammar) -> OptionTag:
    """Parse the inner text of an ``[OPTION for …]`` tag, fail-closed.

    Grammar (from the profile): either a comma/``and``-separated inclusion
    list of variants, or the exception form opened by the grammar's
    ``all_except_prefix``.  Every named variant must be in the grammar's
    ``known_variants``; anything else raises — an unrecognised tag must break
    the load, not silently grade (or skip) a row.
    """
    g = grammar
    text = " ".join(raw.split()).strip()
    if not text:
        raise ExpectationError("empty [OPTION ...] tag.")
    all_except = " ".join(g.all_except_prefix.split()).lower() + " "
    if text.lower().startswith(all_except):
        kind = TAG_KIND_ALL_EXCEPT
        variants = _split_variants(text[len(all_except):], g)
    else:
        kind = TAG_KIND_INCLUSION
        variants = _split_variants(text, g)
    if not variants:
        raise ExpectationError(f"[OPTION ...] tag names no variants: {text!r}")
    unknown = [v for v in variants if v not in g.known_variants]
    if unknown:
        raise ExpectationError(
            f"unrecognised [OPTION ...] tag {text!r}: unknown variant(s) "
            f"{unknown} (known: {sorted(g.known_variants)})."
        )
    if kind == TAG_KIND_ALL_EXCEPT:
        applicable = g.applicable_variant not in variants
    else:
        applicable = g.applicable_variant in variants
    return OptionTag(raw=text, kind=kind, variants=variants, source=source, applicable=applicable)


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
    parenthetical with ``...``; ``...`` is treated as a wildcard.  Without a
    wildcard the normalized texts must be equal — a rewording upstream must
    *not* match (fail-closed drift).
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
    """One applicable evaluator expectation, addressable by a stable key.

    ``expectation_key`` is the scorecard aspect ``id``, never a hash or index
    of the verbatim text — the text is long and will be re-worded upstream.
    ``text`` is the scorecard's verbatim form text (the E5b rubric wording
    source, auditable to a page of the official form); ``registry_text`` is
    the matched registry row with its inline tag stripped.
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
    """A scorecard-excluded aspect (kept for the record).

    ``present_in_registry`` is ``False`` when the registry no longer carries
    the row: the aspect is then absent rather than filtered, and the
    ``registry_text`` is the scorecard's own text.
    """

    criterion_id: str
    registry_text: str
    option_tag: OptionTag
    reason: str
    present_in_registry: bool = True


@dataclass(frozen=True)
class ExpectationSubstrate:
    """The loaded, cross-checked expectation set the E5 grader runs over."""

    instrument_type: str
    scorecard_id: str
    scorecard_version: str
    raw_count: int
    expectations: tuple[Expectation, ...]
    excluded: tuple[ExcludedExpectation, ...]
    profile_id: str = ""
    criterion_ids: tuple[str, ...] = ()

    def by_key(self) -> dict[str, Expectation]:
        """The applicable expectations keyed by ``expectation_key``."""
        return {e.expectation_key: e for e in self.expectations}

    def for_criterion(self, criterion_id: str) -> tuple[Expectation, ...]:
        """The expectations of one criterion; unknown criterion fails closed."""
        known = self.criterion_ids
        if criterion_id not in known:
            raise ExpectationError(
                f"unmapped criterion {criterion_id!r} (known: {sorted(known)})."
            )
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


def _registry_rows(registry: Any, instrument_type: str) -> list[tuple[str, str]]:
    """Extract the instrument's rows as ``(registry_criterion_id, row_text)`` pairs."""
    instruments = registry.get("instruments") if isinstance(registry, dict) else None
    if not isinstance(instruments, list):
        raise ExpectationError("registry has no 'instruments' array.")
    matches = [
        i
        for i in instruments
        if isinstance(i, dict) and i.get("instrument_type") == instrument_type
    ]
    if len(matches) != 1:
        raise ExpectationError(
            f"registry must hold exactly one {instrument_type!r} instrument "
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


def _require_known_criterion(criterion_id: str, profile: PreEvaluationProfile) -> None:
    if criterion_id not in profile.criterion_ids:
        raise ExpectationError(
            f"unmapped criterion {criterion_id!r} (known: "
            f"{sorted(profile.criterion_ids)})."
        )


def _scorecard_entries(
    scorecard: Any, profile: PreEvaluationProfile
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
        _require_known_criterion(cid, profile)
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
    for item in scorecard.get("excluded_aspects", []):
        cid = str(item.get("criterion", ""))
        _require_known_criterion(cid, profile)
        if not item.get("text") or not item.get("option_tag"):
            raise ExpectationError("scorecard excluded_aspects entry is incomplete.")
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


def _resolve_tag(
    inline_raw: str | None,
    entry: _ScorecardEntry,
    registry_text: str,
    grammar: OptionTagGrammar,
) -> OptionTag:
    """Resolve a row's applicability tag: inline if present, else the scorecard's.

    When both exist they must agree (same grammar form, same variant set) —
    a divergence means either the registry or the scorecard moved without the
    other, which is exactly the drift this loader exists to catch.
    """
    scorecard_tag = parse_option_tag(entry.option_tag_raw, source="scorecard", grammar=grammar)
    if inline_raw is None:
        return scorecard_tag
    inline_tag = parse_option_tag(inline_raw, source="registry", grammar=grammar)
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
    registry_path: Path | str | None = None,
    scorecard_path: Path | str | None = None,
    *,
    profile: PreEvaluationProfile | None = None,
    repo_root: Path | str | None = None,
) -> ExpectationSubstrate:
    """Load, filter, and cross-check the profile's expectation set.

    Deterministic pipeline, every step fail-closed:

    1. Load the Tier-2A registry rows for the profile's instrument type and
       the verified scorecard entries (aspects + ``excluded_aspects``).
    2. Match every registry row to exactly one scorecard entry of the same
       (mapped) criterion by verbatim text — a bijection over the aspects.
       An unmatched, ambiguous, or left-over aspect on either side raises:
       registry drift *or* a stale scorecard against a newer form version.
       An excluded entry the registry no longer carries is recorded as absent.
    3. Resolve each row's ``[OPTION …]`` tag (inline, cross-checked against
       the scorecard's; scorecard-supplied where the registry row is untagged)
       and apply the profile's applicability rule.
    4. Require the filter to reproduce the scorecard exactly: every aspect
       must come out applicable, every excluded entry must not.

    Paths default to the profile's declared files; when *repo_root* is given
    the profile's repo-relative paths are anchored on it.  Returns the
    applicable expectations in scorecard order, addressable by
    ``expectation_key``, each mapped to its frozen section artifact(s).
    """
    prof = _resolve_profile(profile)
    reg_path = Path(registry_path) if registry_path is not None else prof.resolve(prof.registry_path, repo_root)
    sc_path = Path(scorecard_path) if scorecard_path is not None else prof.resolve(prof.scorecard.path, repo_root)
    registry = _load_json(reg_path, "expectation registry")
    scorecard = _load_json(sc_path, "evaluator scorecard")
    rows = _registry_rows(registry, prof.instrument.registry_instrument_type)
    entries, scorecard_id, scorecard_version = _scorecard_entries(scorecard, prof)

    matched: dict[int, tuple[str, str, OptionTag]] = {}  # entry idx -> row info
    for registry_criterion_id, row_text in rows:
        criterion_id = prof.criterion_id_for_registry(registry_criterion_id)
        if criterion_id is None:
            raise ExpectationError(
                f"unmapped registry criterion {registry_criterion_id!r} "
                f"(known: {sorted(c.registry_criterion_id for c in prof.criteria)})."
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
        tag = _resolve_tag(inline_raw, entry, registry_text, prof.grammar)
        matched[candidates[0]] = (registry_criterion_id, registry_text, tag)

    unmatched = [
        entries[i].text for i in range(len(entries)) if i not in matched and entries[i].is_aspect
    ]
    if unmatched:
        raise ExpectationError(
            f"{len(unmatched)} scorecard aspect(s) matched no registry row "
            f"(first: {unmatched[0][:80]!r}) — registry drift or a stale scorecard."
        )

    expectations: list[Expectation] = []
    excluded: list[ExcludedExpectation] = []
    for i, entry in enumerate(entries):
        if i in matched:
            registry_criterion_id, registry_text, tag = matched[i]
            present = True
        else:
            # An excluded aspect the registry no longer carries: not graded
            # either way, recorded as absent under the scorecard's own tag.
            registry_criterion_id, registry_text, present = "", entry.text, False
            tag = parse_option_tag(entry.option_tag_raw, source="scorecard", grammar=prof.grammar)
        if entry.is_aspect:
            if not tag.applicable:
                raise ExpectationError(
                    f"scorecard aspect {entry.aspect_id!r} is not applicable to "
                    f"{prof.grammar.applicable_variant!r} by its [OPTION ...] tag "
                    f"{tag.raw!r} — the deterministic filter no longer reproduces "
                    "the verified scorecard."
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
                    section_ids=prof.section_ids_for(entry.criterion_id),
                )
            )
        else:
            if tag.applicable:
                raise ExpectationError(
                    f"scorecard excluded_aspects entry is applicable to "
                    f"{prof.grammar.applicable_variant!r} by its [OPTION ...] tag "
                    f"{tag.raw!r} ({registry_text[:60]!r}) — the deterministic "
                    "filter no longer reproduces the verified scorecard."
                )
            excluded.append(
                ExcludedExpectation(
                    criterion_id=entry.criterion_id,
                    registry_text=registry_text,
                    option_tag=tag,
                    reason=entry.reason,
                    present_in_registry=present,
                )
            )

    return ExpectationSubstrate(
        instrument_type=prof.instrument.registry_instrument_type,
        scorecard_id=scorecard_id,
        scorecard_version=scorecard_version,
        raw_count=len(rows),
        expectations=tuple(expectations),
        excluded=tuple(excluded),
        profile_id=prof.profile_id,
        criterion_ids=prof.criterion_ids,
    )


# --------------------------------------------------------------------------- #
# Criterion ↔ section artifact map (from the profile)
# --------------------------------------------------------------------------- #


def section_ids_for(
    criterion_id: str, *, profile: PreEvaluationProfile | None = None
) -> tuple[str, ...]:
    """The frozen section artifact stem(s) a criterion is graded against."""
    prof = _resolve_profile(profile)
    _require_known_criterion(criterion_id, prof)
    return prof.section_ids_for(criterion_id)


def _resolve_paths(
    criterion_id: str, base: Path, suffix: str, what: str, profile: PreEvaluationProfile | None
) -> tuple[Path, ...]:
    paths = tuple(
        base / f"{sid}{suffix}" for sid in section_ids_for(criterion_id, profile=profile)
    )
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
    profile: PreEvaluationProfile | None = None,
) -> tuple[Path, ...]:
    """The live Tier-5 section artifact(s) a criterion is graded against.

    Fail-closed: a mapped artifact that is absent on disk raises — the grader
    must never silently grade a criterion against nothing.
    """
    base = Path(repo_root) / Path(sections_dir)
    return _resolve_paths(criterion_id, base, ".json", "section artifact", profile)


def golden_paths_for(
    criterion_id: str,
    *,
    repo_root: Path | str = Path("."),
    golden_dir: Path | str = DEFAULT_GOLDEN_DIR,
    profile: PreEvaluationProfile | None = None,
) -> tuple[Path, ...]:
    """The frozen E4 golden fingerprint(s) for a criterion (same fail-closed rule)."""
    base = Path(repo_root) / Path(golden_dir)
    return _resolve_paths(criterion_id, base, GOLDEN_SUFFIX, "golden baseline", profile)
