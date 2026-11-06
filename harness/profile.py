"""
Pre-evaluation profile — the versioned configuration bundle the harness grades under.

A profile names everything that used to be a call-specific literal in harness
Python: the registry instrument type the expectation loader filters on, the
option-tag grammar (applicable variant, known variants, the prefix vocabulary),
the criterion-to-section mapping, the scorecard (scale, weights, thresholds)
and rubric-set files, and the form name the assessor system prompt cites.  The
profile *document* is pure configuration; this module parses it fail-closed and
owns the version arithmetic.  Loading the bundled components (substrate, rubric
set, scoring) lives in :func:`harness.rubrics.load_profile_bundle`, which sits
on top of the expectation and rubric loaders.

Versioning follows the rubric-set pattern: the profile document, the scorecard
file and the rubric set are each content-hashed, and the profile version is a
hash over those three pins — so any bundled component change moves the
version, and the profile document must carry the scorecard ID + version and
the rubric-set ID + version that the loaded files actually hold (a bijection
check, never a silent re-bind).

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA; reads harness-owned
    configuration read-only and writes nothing.  Never a runtime gate.  See
    ``harness/HARNESS.md``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

__all__ = [
    "ProfileError",
    "DEFAULT_PROFILE_PATH",
    "OptionTagGrammar",
    "CriterionSpec",
    "InstrumentSpec",
    "ComponentPin",
    "Scoring",
    "PreEvaluationProfile",
    "canonical_hash",
    "parse_profile",
    "load_profile",
    "default_profile",
    "parse_scoring",
    "score_resolution_for_scale",
    "profile_version",
]

#: The profile that reproduces the harness's original defaults (repo-relative).
DEFAULT_PROFILE_PATH: Path = Path("harness/profiles/msca_pf_default.json")


class ProfileError(Exception):
    """The profile document is missing, malformed, or inconsistent (fail-closed)."""


def canonical_hash(data: Any) -> str:
    """A ``sha256:`` hash of *data*'s canonical JSON (sorted keys, compact).

    Formatting-invariant: two files holding the same JSON value hash alike
    whatever their whitespace or key order.
    """
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class OptionTagGrammar:
    """The vocabulary an ``[OPTION for …]`` applicability tag may use.

    ``applicable_variant`` is the instrument variant that makes a tag apply to
    the profile's instrument; ``known_variants`` is the closed vocabulary (an
    unknown variant fails the load); ``variant_prefix`` is stripped from each
    named variant; ``all_except_prefix`` opens the exception form.
    """

    applicable_variant: str
    known_variants: frozenset[str]
    variant_prefix: str
    all_except_prefix: str


@dataclass(frozen=True)
class CriterionSpec:
    """One evaluation criterion: its scorecard id, its registry id, its sections."""

    id: str
    registry_criterion_id: str
    section_ids: tuple[str, ...]


@dataclass(frozen=True)
class InstrumentSpec:
    """The instrument the profile grades: registry type, display name, form name."""

    registry_instrument_type: str
    name: str
    form_name: str


@dataclass(frozen=True)
class ComponentPin:
    """A bundled data file plus the identity it must carry (the bijection pin)."""

    path: Path
    component_id: str
    version: str


@dataclass(frozen=True)
class Scoring:
    """The scorecard's scale, levels, weights and thresholds.

    ``scale_max`` is the top level key (the per-criterion maximum score);
    ``score_resolution`` the step a criterion score is awarded in when the
    scale wording declares one (:func:`score_resolution_for_scale`), else
    ``None`` — a criterion score is then bounded but not step-checked, and
    the record says so; ``individual_threshold`` the per-criterion threshold
    when the scorecard carries one, else ``None`` — a report then says the
    per-criterion threshold was not checked, never that it was met.
    """

    scale: str
    levels: Mapping[str, str]
    overall_threshold: float
    overall_max: float
    weights: Mapping[str, float]
    scale_max: float = 5.0
    score_resolution: float | None = None
    individual_threshold: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scale": self.scale,
            "levels": dict(self.levels),
            "overall_threshold": self.overall_threshold,
            "overall_max": self.overall_max,
            "weights": dict(self.weights),
            "scale_max": self.scale_max,
            "score_resolution": self.score_resolution,
            "individual_threshold": self.individual_threshold,
        }


@dataclass(frozen=True)
class PreEvaluationProfile:
    """The parsed profile document (configuration only; no files loaded yet)."""

    profile_id: str
    label: str
    instrument: InstrumentSpec
    grammar: OptionTagGrammar
    criteria: tuple[CriterionSpec, ...]
    registry_path: Path
    scorecard: ComponentPin
    rubric_set: ComponentPin
    document_hash: str
    source_path: Path | None = None
    #: The criterion appendix mapping file (repo-relative) when the profile
    #: declares one; the criterion-scoring stage then appends its declared rows
    #: to each criterion's own section.  ``None`` means every criterion is
    #: scored over its own section alone.
    criterion_appendix_mapping: Path | None = None

    @property
    def criterion_ids(self) -> tuple[str, ...]:
        return tuple(c.id for c in self.criteria)

    def criterion(self, criterion_id: str) -> CriterionSpec:
        """The criterion spec for *criterion_id*; unknown criterion fails closed."""
        for spec in self.criteria:
            if spec.id == criterion_id:
                return spec
        raise ProfileError(
            f"unmapped criterion {criterion_id!r} (known: {sorted(self.criterion_ids)})."
        )

    def section_ids_for(self, criterion_id: str) -> tuple[str, ...]:
        return self.criterion(criterion_id).section_ids

    def criterion_id_for_registry(self, registry_criterion_id: str) -> str | None:
        for spec in self.criteria:
            if spec.registry_criterion_id == registry_criterion_id:
                return spec.id
        return None

    def resolve(self, path: Path, repo_root: Path | str | None = None) -> Path:
        """A profile-declared repo-relative path, anchored on *repo_root* if given."""
        return Path(repo_root) / path if repo_root is not None else path


# --------------------------------------------------------------------------- #
# Parsing — fail-closed
# --------------------------------------------------------------------------- #


def _require_str(obj: Mapping[str, Any], key: str, where: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProfileError(f"{where}: {key!r} must be a non-empty string.")
    return value


def _require_obj(obj: Mapping[str, Any], key: str, where: str) -> Mapping[str, Any]:
    value = obj.get(key)
    if not isinstance(value, Mapping):
        raise ProfileError(f"{where}: {key!r} must be an object.")
    return value


def _parse_pin(raw: Mapping[str, Any], where: str, id_key: str) -> ComponentPin:
    return ComponentPin(
        path=Path(_require_str(raw, "path", where)),
        component_id=_require_str(raw, id_key, where),
        version=_require_str(raw, "version", where),
    )


def _parse_grammar(raw: Mapping[str, Any]) -> OptionTagGrammar:
    where = "profile option_tag_grammar"
    variants_raw = raw.get("known_variants")
    if not isinstance(variants_raw, list) or not variants_raw:
        raise ProfileError(f"{where}: known_variants must be a non-empty list.")
    variants = tuple(str(v) for v in variants_raw)
    if any(not v.strip() for v in variants):
        raise ProfileError(f"{where}: known_variants holds an empty variant.")
    if len(set(variants)) != len(variants):
        raise ProfileError(f"{where}: known_variants holds a duplicate variant.")
    applicable = _require_str(raw, "applicable_variant", where)
    if applicable not in variants:
        raise ProfileError(
            f"{where}: applicable_variant {applicable!r} is not in known_variants."
        )
    prefix = raw.get("variant_prefix", "")
    all_except = _require_str(raw, "all_except_prefix", where)
    if not isinstance(prefix, str):
        raise ProfileError(f"{where}: variant_prefix must be a string.")
    return OptionTagGrammar(
        applicable_variant=applicable,
        known_variants=frozenset(variants),
        variant_prefix=prefix,
        all_except_prefix=all_except,
    )


def _parse_criteria(raw: Any) -> tuple[CriterionSpec, ...]:
    if not isinstance(raw, list) or not raw:
        raise ProfileError("profile criteria must be a non-empty list.")
    specs: list[CriterionSpec] = []
    seen_ids: set[str] = set()
    seen_registry: set[str] = set()
    for i, item in enumerate(raw):
        if not isinstance(item, Mapping):
            raise ProfileError(f"profile criteria[{i}] is not an object.")
        where = f"profile criteria[{i}]"
        cid = _require_str(item, "id", where)
        rid = _require_str(item, "registry_criterion_id", where)
        sections_raw = item.get("section_ids")
        if not isinstance(sections_raw, list) or not sections_raw:
            raise ProfileError(f"{where}: section_ids must be a non-empty list.")
        sections = tuple(str(s) for s in sections_raw)
        if any(not s.strip() for s in sections):
            raise ProfileError(f"{where}: section_ids holds an empty id.")
        if cid in seen_ids or rid in seen_registry:
            raise ProfileError(f"{where}: duplicate criterion id {cid!r}/{rid!r}.")
        seen_ids.add(cid)
        seen_registry.add(rid)
        specs.append(CriterionSpec(id=cid, registry_criterion_id=rid, section_ids=sections))
    return tuple(specs)


def parse_profile(data: Any, *, source_path: Path | None = None) -> PreEvaluationProfile:
    """Parse a profile document (already decoded JSON), fail-closed."""
    if not isinstance(data, Mapping):
        raise ProfileError("profile document is not a JSON object.")
    profile_id = _require_str(data, "profile_id", "profile")
    label = str(data.get("label", ""))
    inst_raw = _require_obj(data, "instrument", "profile")
    instrument = InstrumentSpec(
        registry_instrument_type=_require_str(
            inst_raw, "registry_instrument_type", "profile instrument"
        ),
        name=_require_str(inst_raw, "name", "profile instrument"),
        form_name=_require_str(inst_raw, "form_name", "profile instrument"),
    )
    grammar = _parse_grammar(_require_obj(data, "option_tag_grammar", "profile"))
    criteria = _parse_criteria(data.get("criteria"))
    registry_path = Path(_require_str(data, "registry_path", "profile"))
    scorecard = _parse_pin(_require_obj(data, "scorecard", "profile"), "profile scorecard", "scorecard_id")
    rubric_set = _parse_pin(_require_obj(data, "rubric_set", "profile"), "profile rubric_set", "rubric_set_id")
    mapping_raw = data.get("criterion_appendix_mapping")
    mapping_path: Path | None = None
    if mapping_raw is not None:
        if not isinstance(mapping_raw, Mapping):
            raise ProfileError("profile criterion_appendix_mapping must be an object.")
        mapping_path = Path(_require_str(mapping_raw, "path", "profile criterion_appendix_mapping"))
    return PreEvaluationProfile(
        profile_id=profile_id,
        label=label,
        instrument=instrument,
        grammar=grammar,
        criteria=criteria,
        registry_path=registry_path,
        scorecard=scorecard,
        rubric_set=rubric_set,
        document_hash=canonical_hash(data),
        source_path=source_path,
        criterion_appendix_mapping=mapping_path,
    )


def load_profile(path: Path | str = DEFAULT_PROFILE_PATH) -> PreEvaluationProfile:
    """Load and parse one profile document from disk, fail-closed."""
    p = Path(path)
    if not p.is_file():
        raise ProfileError(f"pre-evaluation profile not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ProfileError(f"profile {p} is not valid JSON: {exc}") from exc
    return parse_profile(data, source_path=p)


def default_profile(repo_root: Path | str | None = None) -> PreEvaluationProfile:
    """The profile that reproduces the harness's original defaults."""
    path = DEFAULT_PROFILE_PATH if repo_root is None else Path(repo_root) / DEFAULT_PROFILE_PATH
    return load_profile(path)


# --------------------------------------------------------------------------- #
# Scoring — scale, weights, thresholds from the scorecard file
# --------------------------------------------------------------------------- #


def _number(value: Any, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProfileError(f"scorecard scoring: {what} must be a number.")
    return float(value)


#: The closed rule from a scorecard's ``scale`` wording to the step a score is
#: awarded in.  The stored forms say "one decimal place" (MSCA) or "half-marks"
#: (RIA/IA); a synthetic scorecard may name integers.  Any other wording
#: declares no resolution: the step is then ``None`` and never guessed.
_SCALE_RESOLUTIONS: tuple[tuple[str, float], ...] = (
    ("one decimal", 0.1),
    ("half", 0.5),
    ("integer", 1.0),
)


def score_resolution_for_scale(scale: str) -> float | None:
    """The score step the scorecard's ``scale`` wording declares, or ``None``."""
    lowered = scale.lower()
    for marker, step in _SCALE_RESOLUTIONS:
        if marker in lowered:
            return step
    return None


def parse_scoring(scorecard: Mapping[str, Any], criterion_ids: tuple[str, ...]) -> Scoring:
    """Extract the scale, levels, weights and thresholds of a scorecard, fail-closed.

    Every profile criterion must carry a ``weight_pct`` in the scorecard; the
    overall threshold and maximum must be numbers with the threshold within
    the maximum.  The level keys must be integers (the top one is the
    per-criterion maximum), the scale wording may name a resolution, and an
    ``individual_threshold``, when present, must lie within the scale.
    """
    scoring = scorecard.get("scoring")
    if not isinstance(scoring, Mapping):
        raise ProfileError("scorecard has no 'scoring' object.")
    scale = scoring.get("scale")
    if not isinstance(scale, str) or not scale.strip():
        raise ProfileError("scorecard scoring: scale must be a non-empty string.")
    levels_raw = scoring.get("levels", {})
    if not isinstance(levels_raw, Mapping):
        raise ProfileError("scorecard scoring: levels must be an object.")
    threshold = _number(scoring.get("overall_threshold"), "overall_threshold")
    maximum = _number(scoring.get("overall_max"), "overall_max")
    if not 0 < threshold <= maximum:
        raise ProfileError(
            f"scorecard scoring: overall_threshold {threshold} must lie in "
            f"(0, overall_max={maximum}]."
        )
    criteria = scorecard.get("criteria")
    if not isinstance(criteria, list):
        raise ProfileError("scorecard has no 'criteria' array.")
    weights: dict[str, float] = {}
    for i, criterion in enumerate(criteria):
        if not isinstance(criterion, Mapping):
            raise ProfileError(f"scorecard criteria[{i}] is not an object.")
        cid = str(criterion.get("id", ""))
        if cid in criterion_ids:
            weights[cid] = _number(criterion.get("weight_pct"), f"weight_pct of {cid!r}")
    missing = [c for c in criterion_ids if c not in weights]
    if missing:
        raise ProfileError(f"scorecard carries no weight_pct for criteria {missing}.")
    try:
        level_keys = [int(str(k)) for k in levels_raw]
    except ValueError as exc:
        raise ProfileError(
            f"scorecard scoring: level keys must be integers; got {sorted(levels_raw)}."
        ) from exc
    if not level_keys or max(level_keys) <= 0:
        raise ProfileError("scorecard scoring: levels must name a positive top level.")
    scale_max = float(max(level_keys))
    resolution = score_resolution_for_scale(scale)
    individual_raw = scoring.get("individual_threshold")
    individual: float | None = None
    if individual_raw is not None:
        individual = _number(individual_raw, "individual_threshold")
        if not 0 < individual <= scale_max:
            raise ProfileError(
                f"scorecard scoring: individual_threshold {individual} must lie in "
                f"(0, {scale_max}]."
            )
    return Scoring(
        scale=scale,
        levels={str(k): str(v) for k, v in levels_raw.items()},
        overall_threshold=threshold,
        overall_max=maximum,
        weights=weights,
        scale_max=scale_max,
        score_resolution=resolution,
        individual_threshold=individual,
    )


# --------------------------------------------------------------------------- #
# Version arithmetic
# --------------------------------------------------------------------------- #


def profile_version(
    profile: PreEvaluationProfile, *, scorecard_hash: str, rubric_set_fingerprint: str
) -> str:
    """The profile version: a hash over the three component pins.

    Moves when the profile document, the scorecard file, or the rubric set
    changes — the profile-level counterpart of
    :func:`harness.rubrics.rubric_fingerprint`.
    """
    return canonical_hash(
        {
            "profile_id": profile.profile_id,
            "document_hash": profile.document_hash,
            "scorecard_hash": scorecard_hash,
            "rubric_set_fingerprint": rubric_set_fingerprint,
        }
    )
