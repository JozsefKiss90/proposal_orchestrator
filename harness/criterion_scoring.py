"""
Criterion scoring — the holistic 0–5 score per evaluation criterion (spec PE-04).

The blind lane's cells answer, per aspect, whether a section *addresses* the
aspect.  Evaluation scores, however, are awarded **for the criteria, and not
for the different aspects** (General Annexes Part 15, Tier 1).  This module is
the separate criterion-grading stage that produces those scores, and it is
built so that no shortcut from the cells to a score exists:

* **The scorer reads the complete criterion section verbatim**, never a
  selected pack.  Whole sections fit the uncapped assessor budget; there is no
  selection, no ``not_relevant`` exclusion and no budget filler in this lane.
  An input that does not fit is reported incomplete and **not scored** —
  nothing is truncated to make it fit.
* **Cross-section evidence is a declared appendix.**  The profile's criterion
  appendix mapping (:mod:`harness.appendix_mapping`) names which sub-sections'
  rows a criterion receives beyond its own section.  They are appended whole,
  at sub-section granularity, and every declared row must resolve or the input
  is incomplete.
* **Every score names its complete input by hash** — section bytes and
  appendix rows together (``input_hash``), beside the section alone
  (``section_hash``) — and records the mapping version it was assembled under.
* **Aspect findings may accompany the section and may never replace it.**  A
  grader fed only the ten findings would grade the harness's own summaries;
  :func:`grade_criterion` refuses an input without section text.
* **N samples, median and spread.**  The spread is labelled
  :data:`SPREAD_LABEL` — within-assessor repeatability — because five samples
  from one pinned assessor over an identical prompt measure that and nothing
  else.  They cannot say how far a human panel would land.
* **The total is the form's arithmetic.**  ``S = Σ score × factor`` with the
  factor derived from the scorecard's weights, scale and maximum
  (:func:`score_factor`): ``10E + 6I + 4Q`` for a 50/30/20-weighted form, a plain
  sum for an unweighted one.  Both thresholds — per criterion and overall —
  are checked and reported, never inferred.

No code path here derives a criterion score from cell arithmetic: the module
imports neither the cell grader nor its grade type, and
:func:`combine_criterion_scores` takes criterion scores only.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA; reads candidate artifacts
    read-only and writes only through the judge's provenance log.  Never a
    runtime gate.  A criterion score is ``Inferred`` (§12.2), never Confirmed.
    See ``harness/HARNESS.md``.
"""

from __future__ import annotations

import dataclasses
import statistics
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

from runner.json_extract import extract_first_json_object
from harness.appendix_mapping import AppendixRow
from harness.evidence_pack import UNCAPPED_DEFAULT_PACK_TOKEN_BUDGET, estimate_tokens
from harness.judge import Judge, JudgeResponseError
from harness.profile import Scoring, canonical_hash
from harness.provenance import ProvenanceRecord, prompt_hash
from harness.routing import RoutingDecision, assert_judgeable
from harness.rubrics import RUBRIC_INDEPENDENCE_PREAMBLE, ProfileBundle
from harness.verdict import MIN_MAJORITY_SAMPLES, Verdict

__all__ = [
    "CRITERION_SCORING_METRIC",
    "DEFAULT_CRITERION_SAMPLES",
    "SPREAD_LABEL",
    "SCORED",
    "NOT_SCORED",
    "APPENDIX_APPENDED",
    "APPENDIX_OWN_SECTION",
    "APPENDIX_UNRESOLVED",
    "CriterionScoringError",
    "ResolvedAppendixRow",
    "CriterionInput",
    "CriterionSample",
    "CriterionScore",
    "CriterionScoring",
    "build_criterion_input",
    "build_criterion_prompts",
    "grade_criterion",
    "score_factor",
    "weighted_total",
    "total_formula",
    "combine_criterion_scores",
]

#: The metric name on every criterion-score verdict and provenance record.
CRITERION_SCORING_METRIC: str = "criterion_score"

#: Samples per criterion (spec decisions 5 and 11).  The quoted number gets the
#: most evidence; the cells get :data:`~harness.verdict.MIN_MAJORITY_SAMPLES`.
DEFAULT_CRITERION_SAMPLES: int = 5

#: What the spread of the N samples measures, and all it measures.
SPREAD_LABEL: str = (
    "within-assessor repeatability: the spread of N samples from one pinned "
    "assessor over an identical prompt. It measures that assessor's run-to-run "
    "variability and nothing else; it cannot decompose the distance from a human "
    "evaluation, which would need a second assessor."
)

#: Score status.
SCORED: str = "scored"
NOT_SCORED: str = "not_scored"

#: Appendix row dispositions.
APPENDIX_APPENDED: str = "appended"
APPENDIX_OWN_SECTION: str = "in_own_section"
APPENDIX_UNRESOLVED: str = "unresolved"


class CriterionScoringError(Exception):
    """The grader was invoked outside its contract (fail-closed)."""


class HasContents(Protocol):
    """What the input builder needs of a candidate: parsed sections by id."""

    @property
    def contents(self) -> Mapping[str, Any]: ...


# --------------------------------------------------------------------------- #
# The input — complete section + declared appendix, hashed whole
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ResolvedAppendixRow:
    """One declared appendix entry after resolution against the candidate."""

    row: AppendixRow
    disposition: str
    section_id: str = ""
    sub_section_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.row.to_dict(),
            "disposition": self.disposition,
            "section_id": self.section_id,
            "sub_section_id": self.sub_section_id,
        }


@dataclass(frozen=True)
class CriterionInput:
    """Everything one criterion score is produced from, and its accounting.

    ``text`` is what the scorer reads: every present section of the criterion,
    sub-section by sub-section, verbatim, then the appended sub-sections the
    mapping declares.  ``section_hash`` covers the criterion's own sections;
    ``input_hash`` covers sections and appended rows together.  ``complete``
    is ``False`` when a section is missing, a declared row did not resolve, or
    the assembled input exceeds the budget — with the reasons in
    ``incompleteness``.  Nothing is ever cut to restore completeness.
    """

    criterion_id: str
    registry_criterion_id: str
    section_ids: tuple[str, ...]
    present_section_ids: tuple[str, ...]
    text: str
    section_hash: str
    input_hash: str
    appendix: tuple[ResolvedAppendixRow, ...]
    mapping_version: Mapping[str, str] | None
    token_estimate: int
    token_budget: int
    complete: bool
    incompleteness: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """The accounting record (the text itself is identified by hash, not copied)."""
        return {
            "criterion_id": self.criterion_id,
            "registry_criterion_id": self.registry_criterion_id,
            "section_ids": list(self.section_ids),
            "present_section_ids": list(self.present_section_ids),
            "characters": len(self.text),
            "section_hash": self.section_hash,
            "input_hash": self.input_hash,
            "appendix": [r.to_dict() for r in self.appendix],
            "mapping_version": dict(self.mapping_version) if self.mapping_version else None,
            "token_estimate": self.token_estimate,
            "token_budget": self.token_budget,
            "complete": self.complete,
            "incompleteness": list(self.incompleteness),
        }


def _sub_sections(section: Any) -> list[dict[str, Any]]:
    subs = section.get("sub_sections") if isinstance(section, Mapping) else None
    if not isinstance(subs, list):
        return []
    return [dict(s) for s in subs if isinstance(s, Mapping) and str(s.get("sub_section_id", "")).strip()]


def _render_section(section_id: str, section: Any) -> str:
    parts = [f"=== CRITERION SECTION: {section_id} ===\n\n"]
    for sub in _sub_sections(section):
        title = str(sub.get("title", "")).strip()
        head = f"--- {sub['sub_section_id']}" + (f" | {title}" if title else "") + " ---\n"
        parts.append(head + str(sub.get("content", "")).rstrip() + "\n\n")
    return "".join(parts)


def _find_sub_section(
    contents: Mapping[str, Any], sub_section_id: str
) -> list[tuple[str, dict[str, Any]]]:
    hits: list[tuple[str, dict[str, Any]]] = []
    for section_id in sorted(contents):
        for sub in _sub_sections(contents[section_id]):
            if str(sub["sub_section_id"]) == sub_section_id:
                hits.append((section_id, dict(sub)))
    return hits


def build_criterion_input(
    bundle: ProfileBundle,
    candidate: HasContents,
    criterion_id: str,
    *,
    token_budget: int = UNCAPPED_DEFAULT_PACK_TOKEN_BUDGET,
) -> CriterionInput:
    """Assemble the complete input for one criterion, with its accounting.

    Deterministic and judgment-free: the criterion's sections come from the
    profile, the appendix rows from the bundle's mapping, the content from the
    candidate.  A missing section, an unresolved row or an over-budget input
    makes the result incomplete; the text is still assembled and reported so
    the gap is visible, but :func:`grade_criterion` will not score it.
    """
    profile = bundle.profile
    spec = profile.criterion(criterion_id)
    contents = candidate.contents
    reasons: list[str] = []
    present = tuple(sid for sid in spec.section_ids if sid in contents)
    for sid in spec.section_ids:
        if sid not in contents:
            reasons.append(f"section {sid} is missing from the candidate")
        elif not any(str(sub.get("content", "")).strip() for sub in _sub_sections(contents[sid])):
            # A section artifact with no sub-section text would still render a
            # header; scoring it would be scoring the findings alone.
            reasons.append(f"section {sid} carries no sub-section text to score")

    text_parts = [_render_section(sid, contents[sid]) for sid in present]
    section_record = {sid: _sub_sections(contents[sid]) for sid in present}

    resolved: list[ResolvedAppendixRow] = []
    appended: dict[tuple[str, str], dict[str, Any]] = {}
    appended_rows: dict[tuple[str, str], list[AppendixRow]] = {}
    mapping = bundle.appendix_mapping
    if mapping is not None:
        for row in mapping.rows_for(criterion_id):
            hits = _find_sub_section(contents, row.candidate_sub_section)
            own = [h for h in hits if h[0] in spec.section_ids]
            if own:
                resolved.append(
                    ResolvedAppendixRow(row, APPENDIX_OWN_SECTION, own[0][0], row.candidate_sub_section)
                )
                continue
            if len(hits) == 1:
                section_id, sub = hits[0]
                key = (section_id, row.candidate_sub_section)
                appended.setdefault(key, sub)
                appended_rows.setdefault(key, []).append(row)
                resolved.append(
                    ResolvedAppendixRow(row, APPENDIX_APPENDED, section_id, row.candidate_sub_section)
                )
                continue
            resolved.append(ResolvedAppendixRow(row, APPENDIX_UNRESOLVED))
            if hits:
                reasons.append(
                    f"appendix row {row.table!r} -> sub-section {row.candidate_sub_section} "
                    f"is ambiguous: held by {', '.join(h[0] for h in hits)}"
                )
            else:
                reasons.append(
                    f"appendix row {row.table!r} -> sub-section {row.candidate_sub_section} "
                    "is not present in any candidate section"
                )

    appendix_record: list[dict[str, Any]] = []
    if appended:
        text_parts.append(
            "=== DECLARED APPENDIX (rows this criterion receives beyond its own section) ===\n\n"
        )
        for key in sorted(appended):
            section_id, sub_id = key
            sub = appended[key]
            declared = "; ".join(
                f"{r.table}: {r.rows} ({r.status})" for r in appended_rows[key]
            )
            title = str(sub.get("title", "")).strip()
            text_parts.append(
                f"--- appendix | section {section_id} | sub-section {sub_id}"
                + (f" | {title}" if title else "")
                + f" | declared: {declared} ---\n"
                + str(sub.get("content", "")).rstrip()
                + "\n\n"
            )
            appendix_record.append(
                {"section_id": section_id, "sub_section_id": sub_id, "content": sub.get("content", "")}
            )

    text = "".join(text_parts)
    tokens = estimate_tokens(text)
    if tokens > token_budget:
        reasons.append(
            f"the assembled input estimates {tokens} tokens against a budget of "
            f"{token_budget}; nothing was truncated, so the criterion is not scored"
        )
    return CriterionInput(
        criterion_id=criterion_id,
        registry_criterion_id=spec.registry_criterion_id,
        section_ids=tuple(spec.section_ids),
        present_section_ids=present,
        text=text,
        section_hash=canonical_hash(section_record),
        input_hash=canonical_hash({"sections": section_record, "appendix": appendix_record}),
        appendix=tuple(resolved),
        mapping_version=mapping.version if mapping is not None else None,
        token_estimate=tokens,
        token_budget=token_budget,
        complete=not reasons,
        incompleteness=tuple(reasons),
    )


# --------------------------------------------------------------------------- #
# Prompts
# --------------------------------------------------------------------------- #


_FINDINGS_HEADER: str = (
    "=== HARNESS FINDINGS (advisory machine pre-check per aspect; grade the "
    "section text above, never these) ===\n\n"
)


def _fmt_step(resolution: float | None) -> str:
    if resolution is None:
        return "at the resolution the form allows (the scorecard declares none)"
    if resolution == 0.1:
        return "in steps of 0.1 (one decimal place)"
    if resolution == 0.5:
        return "in steps of 0.5 (half-marks)"
    if resolution == 1.0:
        return "in whole numbers"
    return f"in steps of {resolution}"


def _fmt_number(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def build_criterion_prompts(
    bundle: ProfileBundle,
    criterion_input: CriterionInput,
    *,
    aspect_findings: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[str, str]:
    """The (system, user) prompt pair for one criterion-score call.

    The system prompt carries the criterion name, every aspect the form lists
    under it (verbatim, with its form page), the official level descriptors,
    the scale and its resolution, the no-aspect-averaging rule and the JSON
    schema.  The user prompt is the complete input text, then — only when
    given — the aspect findings under a header that names them advisory.
    """
    scoring = bundle.scoring
    form = bundle.profile.instrument.form_name
    aspects = [r for r in bundle.rubric_set.rubrics if r.criterion_id == criterion_input.criterion_id]
    aspect_lines = "\n".join(
        f"- {r.expectation_text}" + (f" (form p.{r.source_page})" if r.source_page is not None else "")
        for r in aspects
    )
    level_lines = "\n".join(
        f"{k}: {scoring.levels[k]}" for k in sorted(scoring.levels, key=lambda x: int(x))
    )
    top = _fmt_number(scoring.scale_max)
    system = (
        RUBRIC_INDEPENDENCE_PREAMBLE
        + f"CRITERION UNDER ASSESSMENT: {criterion_input.registry_criterion_id} ({form})\n\n"
        f"ASPECTS the form lists under this criterion, verbatim:\n{aspect_lines}\n\n"
        f"SCORING, verbatim descriptors from the form (scale: {scoring.scale}):\n{level_lines}\n\n"
        f"Award ONE holistic score for the criterion as a whole, from 0 to {top}, "
        f"{_fmt_step(scoring.score_resolution)}. Scores are awarded for the criterion, "
        "not for the aspects: weigh every aspect, do not average them.\n"
        "Judge only the text you are given. Name every shortcoming you find as a "
        "separate short statement an applicant could act on; name the strengths "
        "that carry the score.\n"
        "If a block headed HARNESS FINDINGS follows the section, it is the advisory "
        "output of a machine pre-check: grade the section text, never the findings.\n\n"
        "Return ONLY a JSON object, no prose before or after:\n"
        '{"score": <number>, '
        '"shortcomings": ["<one named shortcoming>", ...], '
        '"strengths": ["<one named strength>", ...], '
        '"rationale": "<two to four sentences naming the decisive passages>"}'
    )
    user = criterion_input.text
    if aspect_findings:
        user += _FINDINGS_HEADER
        for f in aspect_findings:
            key = f.get("expectation_key", "?")
            covered = f.get("covered")
            score = f.get("score")
            rationale = str(f.get("rationale", "")).strip()
            user += (
                f"[finding {key} | addressed={covered} | score={score}]\n"
                + (rationale + "\n" if rationale else "")
                + "\n"
            )
    user += (
        f"Score the criterion {criterion_input.registry_criterion_id} over the complete "
        "section text above and return only the JSON object."
    )
    return system, user


# --------------------------------------------------------------------------- #
# Samples and scores
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class CriterionSample:
    """One assessor sample: the raw criterion score and what it named."""

    sample_index: int
    score: float
    shortcomings: tuple[str, ...]
    strengths: tuple[str, ...]
    rationale: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_index": self.sample_index,
            "score": self.score,
            "shortcomings": list(self.shortcomings),
            "strengths": list(self.strengths),
            "rationale": self.rationale,
        }


@dataclass(frozen=True)
class CriterionScore:
    """The criterion score: median and spread of N samples over one hashed input.

    ``status`` is :data:`NOT_SCORED` when the input was incomplete; then
    ``score``, ``spread`` and ``threshold_met`` are ``None`` and ``samples`` is
    empty, because the judge was never called.  The binding fields
    (``candidate_hash``, ``profile_version``, ``assessor_pin``) tie the score
    to a report the way a cell is tied.
    """

    criterion_id: str
    registry_criterion_id: str
    status: str
    score: float | None
    spread: float | None
    spread_label: str
    samples: tuple[CriterionSample, ...]
    provenance: tuple[ProvenanceRecord, ...]
    property_key: str
    routing: RoutingDecision | None
    prompt_hash: str
    input_hash: str
    section_hash: str
    mapping_version: Mapping[str, str] | None
    input_record: Mapping[str, Any]
    incompleteness: tuple[str, ...]
    threshold: float | None
    threshold_met: bool | None
    weight: float
    factor: float
    weighted_points: float | None
    aspect_findings_attached: bool
    profile_version: str = ""
    assessor_pin: str = ""
    candidate_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": CRITERION_SCORING_METRIC,
            "criterion_id": self.criterion_id,
            "registry_criterion_id": self.registry_criterion_id,
            "status": self.status,
            "score": self.score,
            "spread": self.spread,
            "spread_label": self.spread_label,
            "samples": [s.to_dict() for s in self.samples],
            "provenance": [p.to_dict() for p in self.provenance],
            "property_key": self.property_key,
            "routing": self.routing.to_dict() if self.routing is not None else None,
            "prompt_hash": self.prompt_hash,
            "input_hash": self.input_hash,
            "section_hash": self.section_hash,
            "mapping_version": dict(self.mapping_version) if self.mapping_version else None,
            "input": dict(self.input_record),
            "incompleteness": list(self.incompleteness),
            "threshold": self.threshold,
            "threshold_met": self.threshold_met,
            "weight": self.weight,
            "factor": self.factor,
            "weighted_points": self.weighted_points,
            "aspect_findings_attached": self.aspect_findings_attached,
            "candidate_hash": self.candidate_hash,
            "profile_version": self.profile_version,
            "assessor_pin": self.assessor_pin,
            "evidence_type": "Inferred",
        }


def criterion_property_key(criterion_id: str) -> str:
    return f"{CRITERION_SCORING_METRIC}::{criterion_id}"


def _str_list(payload: Mapping[str, Any], key: str, *, required: bool) -> tuple[str, ...]:
    value = payload.get(key)
    if value is None:
        if required:
            raise JudgeResponseError(f"criterion score response carries no {key!r} list.")
        return ()
    if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise JudgeResponseError(
            f"criterion score response: {key!r} must be a list of non-empty strings; got {value!r}."
        )
    return tuple(v.strip() for v in value)


def _parse_sample(raw: str, scoring: Scoring, index: int) -> CriterionSample:
    """Parse one response strictly; never repair (CLAUDE.md §17.5.4 in spirit).

    The score must be a number on the scale.  Its step is checked only when the
    scorecard declares a resolution; a scorecard that declares none gets a
    bounded, unstepped score and the aggregate records ``score_resolution:
    null`` so a reader knows the step was not validated.
    """
    payload = extract_first_json_object(raw)
    if payload is None:
        raise JudgeResponseError(
            f"criterion score response carried no parseable JSON object: {raw[:200]!r}"
        )
    score = payload.get("score")
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        raise JudgeResponseError(f"criterion score response: 'score' must be a number; got {score!r}.")
    value = float(score)
    if not 0.0 <= value <= scoring.scale_max:
        raise JudgeResponseError(
            f"criterion score {value} lies outside the scale 0-{_fmt_number(scoring.scale_max)}."
        )
    if scoring.score_resolution is not None:
        steps = value / scoring.score_resolution
        if abs(steps - round(steps)) > 1e-6:
            raise JudgeResponseError(
                f"criterion score {value} is not awarded {_fmt_step(scoring.score_resolution)}."
            )
    shortcomings = _str_list(payload, "shortcomings", required=True)
    strengths = _str_list(payload, "strengths", required=False)
    rationale = str(payload.get("rationale", "")).strip()
    if not rationale:
        raise JudgeResponseError("criterion score response carries no rationale.")
    return CriterionSample(
        sample_index=index,
        score=round(value, 2),
        shortcomings=shortcomings,
        strengths=strengths,
        rationale=rationale,
    )


def grade_criterion(
    judge: Judge,
    bundle: ProfileBundle,
    criterion_input: CriterionInput,
    *,
    aspect_findings: Sequence[Mapping[str, Any]] | None = None,
    n: int = DEFAULT_CRITERION_SAMPLES,
) -> CriterionScore:
    """Score one criterion over its complete input with *n* assessor samples.

    Guards, each raising rather than degrading: the judge must carry a
    provenance log; ``n`` must be at least the majority minimum; an input that
    is complete yet holds no section text is refused — aspect findings alone
    never yield a score.  An incomplete input returns :data:`NOT_SCORED`
    without a judge call.  Each sample is
    parsed strictly (score on the scale and at its resolution, a shortcomings
    list, a rationale); a malformed one fails the run through
    :class:`~harness.judge.JudgeResponseError`.  Every sample's provenance is
    appended to the judge's log with the score normalised to ``[0, 1]`` so
    the trail stays comparable with every other harness verdict.
    """
    if judge.provenance_log is None:
        raise CriterionScoringError(
            "grade_criterion requires a Judge with an attached ProvenanceLog — every "
            "criterion score must land in a durable provenance trail."
        )
    if n < MIN_MAJORITY_SAMPLES:
        raise CriterionScoringError(
            f"n must be at least {MIN_MAJORITY_SAMPLES}; got {n}. The spec grades "
            f"criteria with {DEFAULT_CRITERION_SAMPLES} samples."
        )
    scoring = bundle.scoring
    cid = criterion_input.criterion_id
    weight = float(scoring.weights[cid])
    factor = score_factor(scoring, cid)
    pin = f"{judge.config.model}@{judge.config.version}"
    common: dict[str, Any] = dict(
        criterion_id=cid,
        registry_criterion_id=criterion_input.registry_criterion_id,
        spread_label=SPREAD_LABEL,
        property_key=criterion_property_key(cid),
        input_hash=criterion_input.input_hash,
        section_hash=criterion_input.section_hash,
        mapping_version=criterion_input.mapping_version,
        input_record=criterion_input.to_dict(),
        incompleteness=criterion_input.incompleteness,
        threshold=scoring.individual_threshold,
        weight=weight,
        factor=factor,
        aspect_findings_attached=bool(aspect_findings),
        profile_version=bundle.version,
        assessor_pin=pin,
    )
    if not criterion_input.complete:
        # Reported, never scored: the judge is not called over a gap.
        return CriterionScore(
            status=NOT_SCORED,
            score=None,
            spread=None,
            samples=(),
            provenance=(),
            routing=None,
            prompt_hash="",
            threshold_met=None,
            weighted_points=None,
            **common,
        )

    if not criterion_input.text.strip():
        raise CriterionScoringError(
            f"criterion {criterion_input.criterion_id!r} has no section text to score; a "
            "criterion score is never produced from aspect findings alone."
        )

    routing = assert_judgeable(common["property_key"])
    system, user = build_criterion_prompts(bundle, criterion_input, aspect_findings=aspect_findings)
    digest = prompt_hash(system, user)
    samples: list[CriterionSample] = []
    records: list[ProvenanceRecord] = []
    for i in range(n):
        raw = judge.raw_invoke(system, user)
        sample = _parse_sample(raw, scoring, i)
        verdict = Verdict(
            metric=CRITERION_SCORING_METRIC,
            property_key=common["property_key"],
            score=sample.score / scoring.scale_max,
            rationale=sample.rationale,
            sample_index=i,
        )
        record = ProvenanceRecord.from_verdict(
            verdict,
            judge_model=judge.config.model,
            judge_version=judge.config.version,
            prompt_hash=digest,
            timestamp=judge.clock(),
        )
        judge.provenance_log.append(record)
        samples.append(sample)
        records.append(record)
    values = [s.score for s in samples]
    median = round(float(statistics.median(values)), 2)
    spread = round(max(values) - min(values), 2)
    threshold = scoring.individual_threshold
    return CriterionScore(
        status=SCORED,
        score=median,
        spread=spread,
        samples=tuple(samples),
        provenance=tuple(records),
        routing=routing,
        prompt_hash=digest,
        threshold_met=(median >= threshold) if threshold is not None else None,
        weighted_points=round(median * factor, 4),
        **common,
    )


# --------------------------------------------------------------------------- #
# The total — the form's arithmetic, both thresholds
# --------------------------------------------------------------------------- #


def score_factor(scoring: Scoring, criterion_id: str) -> float:
    """Points per score unit for *criterion_id*: ``weight × overall_max / (scale_max × Σ weights)``.

    Weighted 50/30/20 over a 0–5 scale to 100 gives 10, 6 and 4; an unweighted
    form (every weight 1, maximum 15) gives 1 each, a plain sum.
    """
    total_weight = sum(float(w) for w in scoring.weights.values())
    if total_weight <= 0:
        raise CriterionScoringError("the scorecard weights sum to nothing; no total can be formed.")
    return float(scoring.weights[criterion_id]) * scoring.overall_max / (scoring.scale_max * total_weight)


def weighted_total(scores: Mapping[str, float], scoring: Scoring) -> float:
    """``S = Σ score × factor`` over every criterion the scoring weights name.

    Fails closed on a missing criterion score; never fills one in.
    """
    missing = [c for c in scoring.weights if c not in scores]
    if missing:
        raise CriterionScoringError(f"no score for criteria {missing}; the total is undetermined.")
    return round(sum(float(scores[c]) * score_factor(scoring, c) for c in scoring.weights), 4)


def total_formula(scoring: Scoring) -> str:
    """The total as the form states it, e.g. ``S = 10*excellence + 6*impact + 4*implementation``."""
    return "S = " + " + ".join(
        f"{_fmt_number(round(score_factor(scoring, c), 6))}*{c}" for c in scoring.weights
    )


@dataclass(frozen=True)
class CriterionScoring:
    """The criterion scores of one candidate and their total under the form's rules."""

    scores: tuple[CriterionScore, ...]
    formula: str
    total: float | None
    overall_threshold: float
    overall_max: float
    overall_threshold_met: bool | None
    individual_threshold: float | None
    individual_thresholds_met: bool | None
    failing_criteria: tuple[str, ...]
    unscored_criteria: tuple[str, ...]
    samples_per_criterion: int | None
    scale_max: float = 5.0
    score_resolution: float | None = None
    spread_label: str = SPREAD_LABEL

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric": CRITERION_SCORING_METRIC,
            "formula": self.formula,
            "total": self.total,
            "overall_threshold": self.overall_threshold,
            "overall_max": self.overall_max,
            "overall_threshold_met": self.overall_threshold_met,
            "individual_threshold": self.individual_threshold,
            "individual_thresholds_met": self.individual_thresholds_met,
            "failing_criteria": list(self.failing_criteria),
            "unscored_criteria": list(self.unscored_criteria),
            "samples_per_criterion": self.samples_per_criterion,
            "scale_max": self.scale_max,
            "score_resolution": self.score_resolution,
            "spread_label": self.spread_label,
            "scores": [s.to_dict() for s in self.scores],
        }


def combine_criterion_scores(
    scores: Sequence[CriterionScore], scoring: Scoring
) -> CriterionScoring:
    """Form the total and check both thresholds from criterion scores alone.

    A criterion that was not scored leaves the total and both threshold
    verdicts ``None`` and is named in ``unscored_criteria``; nothing is
    estimated in its place.  Per-criterion thresholds are checked only when
    the scorecard carries one.
    """
    by_id = {s.criterion_id: s for s in scores}
    unscored = tuple(
        c for c in scoring.weights if c not in by_id or by_id[c].status != SCORED
    )
    scored = {c: s.score for c, s in by_id.items() if s.status == SCORED and s.score is not None}
    total = weighted_total(scored, scoring) if not unscored else None
    threshold = scoring.individual_threshold
    failing = tuple(
        c for c, s in by_id.items()
        if s.status == SCORED and s.threshold_met is False
    )
    individual_met: bool | None
    if threshold is None or unscored:
        individual_met = None
    else:
        individual_met = not failing
    counts = {len(s.samples) for s in scores if s.status == SCORED}
    if len(counts) > 1:
        raise CriterionScoringError(
            f"criterion scores carry different sample counts {sorted(counts)}; one "
            "assessment grades every criterion with the same N."
        )
    return CriterionScoring(
        scores=tuple(scores),
        formula=total_formula(scoring),
        total=total,
        overall_threshold=scoring.overall_threshold,
        overall_max=scoring.overall_max,
        overall_threshold_met=(total >= scoring.overall_threshold) if total is not None else None,
        individual_threshold=threshold,
        individual_thresholds_met=individual_met,
        failing_criteria=failing,
        unscored_criteria=unscored,
        samples_per_criterion=next(iter(counts)) if counts else None,
        scale_max=scoring.scale_max,
        score_resolution=scoring.score_resolution,
    )
