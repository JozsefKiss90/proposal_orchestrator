"""
Rubric set — versioned, scorecard-traceable rubrics + prompt rendering (E5b).

The E5 grader asks, per MSCA-PF evaluator expectation, one integrity-framed
question: *does the section address AND ground this expectation* — never "is
this good prose".  This module owns the rubric side of that contract:

* **Rubrics are versioned data, not inline strings** —
  ``harness/rubrics_msca_pf.json`` carries, per expectation, the rubric text,
  evaluation steps, pass threshold, and the deterministic selection basis
  (``selection_terms`` + ``anchor_sub_section_ids``) the evidence-pack builder
  uses.  A rubric change is a data-file diff with a fingerprint change, not a
  silent prompt edit.
* **Rubric wording traces to the scorecard.**  Each rubric's
  ``expectation_text`` must be byte-identical to the matching aspect ``text``
  in ``harness/evaluator_scorecard_msca_pf.json`` (the human-verified verbatim
  freeze of the official *HE MSCA Evaluation Form V2.2*, pp.4-6), and
  ``expectation_key`` equals the scorecard aspect ``id`` — so any rubric is
  auditable to a page of the official form.  The loader cross-checks the
  rubric set against the E5a substrate and **fails closed** on any divergence:
  a missing/extra rubric, a paraphrased expectation text, a criterion
  mismatch, or a rubric set built against a different scorecard version.
* **Prompt pinning.**  The rendered (system, user) prompt pair is hashed with
  the house :func:`~harness.provenance.prompt_hash` (recorded on every judge
  verdict's provenance); :func:`rubric_fingerprint` additionally pins the
  rubric *data* so a report can state exactly which rubric version scored.

The pack side of the contract lives in :mod:`harness.evidence_pack`; this
module renders prompts *over* a pack and never selects evidence itself.
E5c (coverage grader) drives the judge with these prompts; E5b itself is
judge-free — everything here is exercised offline with the injectable fake
backend.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate; reads harness-owned
    data files read-only and writes nothing.  Never a runtime gate.  See
    ``harness/HARNESS.md``.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from harness.evidence_pack import (
    DEFAULT_PACK_TOKEN_BUDGET,
    DEFAULT_SPAN_BUDGET_FRACTION,
    EvidencePack,
    EvidencePackError,
    PACK_INSUFFICIENT_CONTEXT,
    build_evidence_pack,
    normalize_terms,
)
from harness.expectations import (
    DEFAULT_REGISTRY_PATH,
    DEFAULT_SCORECARD_PATH,
    ExpectationSubstrate,
    load_expectation_substrate,
)
from harness.provenance import prompt_hash

__all__ = [
    "DEFAULT_RUBRIC_SET_PATH",
    "RUBRIC_INDEPENDENCE_PREAMBLE",
    "RubricError",
    "Rubric",
    "RubricSet",
    "rubric_fingerprint",
    "load_rubric_set",
    "build_pack_for",
    "build_rubric_system_prompt",
    "build_rubric_user_prompt",
    "build_rubric_prompts",
    "rubric_prompt_hash",
]

#: The versioned rubric data file (repo-relative; harness-owned).
DEFAULT_RUBRIC_SET_PATH: Path = Path("harness/rubrics_msca_pf.json")

#: The grader/generator-independence framing every rubric system prompt opens
#: with — the expectation-judge sibling of E1.5's faithfulness preamble.
RUBRIC_INDEPENDENCE_PREAMBLE: str = (
    "You are an independent evaluator-expectation judge for a research-proposal "
    "integrity harness. You are deliberately a different model from the one "
    "that drafted the text, and you judge ONLY from the evidence pack provided "
    "— never from prior knowledge or plausibility.\n\n"
)


class RubricError(Exception):
    """The rubric set is missing, malformed, or has drifted from the substrate (fail-closed)."""


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Rubric:
    """One integrity-framed rubric for one PF evaluator expectation.

    ``expectation_key`` is the scorecard aspect ``id``; ``expectation_text`` is
    the scorecard's verbatim form text (loader-enforced, auditable to
    ``source_page`` of the official form).  ``selection_terms`` and
    ``anchor_sub_section_ids`` are the deterministic evidence-selection basis
    handed to :func:`~harness.evidence_pack.build_evidence_pack`.
    """

    expectation_key: str
    criterion_id: str
    expectation_text: str
    rubric: str
    evaluation_steps: tuple[str, ...]
    pass_threshold: float
    selection_terms: tuple[str, ...]
    anchor_sub_section_ids: tuple[str, ...]
    source_page: int | str | None

    def to_dict(self) -> dict[str, Any]:
        """The rubric's canonical JSON-serializable form (fingerprint input)."""
        return {
            "expectation_key": self.expectation_key,
            "criterion_id": self.criterion_id,
            "expectation_text": self.expectation_text,
            "rubric": self.rubric,
            "evaluation_steps": list(self.evaluation_steps),
            "pass_threshold": self.pass_threshold,
            "selection_terms": list(self.selection_terms),
            "anchor_sub_section_ids": list(self.anchor_sub_section_ids),
            "source_page": self.source_page,
        }


def rubric_fingerprint(rubric: Rubric) -> str:
    """A stable ``sha256:`` hash of the rubric's canonical *authored* data.

    Pins the rubric *content* the way :func:`~harness.provenance.prompt_hash`
    pins the rendered prompts: a report carrying this fingerprint states
    exactly which rubric version produced a score, and any edit to the data
    file is visible as a fingerprint change.  ``source_page`` is excluded — it
    is stamped from the substrate at load time, not authored in the rubric
    file, and must not shift the fingerprint without a data-file diff.
    """
    data = rubric.to_dict()
    del data["source_page"]
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RubricSet:
    """The loaded, substrate-cross-checked rubric set (one rubric per expectation)."""

    rubric_set_id: str
    version: str
    scorecard_id: str
    scorecard_version: str
    rubrics: tuple[Rubric, ...]

    def by_key(self) -> dict[str, Rubric]:
        """The rubrics keyed by ``expectation_key`` (substrate order preserved)."""
        return {r.expectation_key: r for r in self.rubrics}

    @property
    def fingerprint(self) -> str:
        """A stable ``sha256:`` hash over the set identity + every rubric fingerprint."""
        canonical = json.dumps(
            {
                "rubric_set_id": self.rubric_set_id,
                "version": self.version,
                "scorecard_id": self.scorecard_id,
                "scorecard_version": self.scorecard_version,
                "rubrics": [rubric_fingerprint(r) for r in self.rubrics],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Loading — fail-closed against the E5a substrate
# --------------------------------------------------------------------------- #


def _parse_rubric(raw: Any, index: int) -> Rubric:
    if not isinstance(raw, Mapping):
        raise RubricError(f"rubrics[{index}] is not an object.")
    key = str(raw.get("expectation_key", "")).strip()
    if not key:
        raise RubricError(f"rubrics[{index}] has no expectation_key.")
    rubric_text = str(raw.get("rubric", "")).strip()
    if not rubric_text:
        raise RubricError(f"rubric {key!r} has an empty rubric text.")
    steps_raw = raw.get("evaluation_steps")
    if not isinstance(steps_raw, list) or not steps_raw:
        raise RubricError(f"rubric {key!r} has no evaluation_steps.")
    steps = tuple(str(s).strip() for s in steps_raw)
    if any(not s for s in steps):
        raise RubricError(f"rubric {key!r} has an empty evaluation step.")
    threshold = raw.get("pass_threshold")
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
        raise RubricError(f"rubric {key!r}: pass_threshold must be a number.")
    threshold = float(threshold)
    if not 0.0 < threshold <= 1.0:
        raise RubricError(
            f"rubric {key!r}: pass_threshold must be in (0, 1]; got {threshold}."
        )
    terms_raw = raw.get("selection_terms")
    if not isinstance(terms_raw, list):
        raise RubricError(f"rubric {key!r} has no selection_terms list.")
    try:
        terms = normalize_terms(terms_raw)
    except EvidencePackError as exc:
        raise RubricError(f"rubric {key!r}: {exc}") from exc
    anchors_raw = raw.get("anchor_sub_section_ids", [])
    if not isinstance(anchors_raw, list):
        raise RubricError(f"rubric {key!r}: anchor_sub_section_ids must be a list.")
    anchors = tuple(str(a).strip() for a in anchors_raw)
    if any(not a for a in anchors):
        raise RubricError(f"rubric {key!r} has an empty anchor sub-section id.")
    return Rubric(
        expectation_key=key,
        criterion_id=str(raw.get("criterion_id", "")).strip(),
        expectation_text=str(raw.get("expectation_text", "")),
        rubric=rubric_text,
        evaluation_steps=steps,
        pass_threshold=threshold,
        selection_terms=terms,
        anchor_sub_section_ids=anchors,
        source_page=None,  # filled from the substrate during cross-check
    )


def load_rubric_set(
    rubric_path: Path | str = DEFAULT_RUBRIC_SET_PATH,
    *,
    substrate: ExpectationSubstrate | None = None,
    registry_path: Path | str = DEFAULT_REGISTRY_PATH,
    scorecard_path: Path | str = DEFAULT_SCORECARD_PATH,
) -> RubricSet:
    """Load the rubric set and cross-check it against the E5a substrate, fail-closed.

    Checks, in order — any failure raises :class:`RubricError`:

    1. The file exists, is valid JSON, and carries a non-empty
       ``rubric_set_id`` / ``version``.
    2. ``scorecard_id`` / ``scorecard_version`` match the substrate's — a
       rubric set authored against an older form version must not silently
       grade against a newer scorecard.
    3. The rubric keys are in **bijection** with the substrate's 9
       ``expectation_key``\\ s (no missing, no extra, no duplicate).
    4. Each rubric's ``expectation_text`` is **byte-identical** to the
       substrate expectation's scorecard text (verbatim, never paraphrased)
       and its ``criterion_id`` matches.

    Rubrics are returned in substrate (scorecard) order, each stamped with the
    substrate's ``source_page`` so a rendered prompt is auditable to a page of
    the official form.
    """
    sub = substrate or load_expectation_substrate(
        registry_path=registry_path, scorecard_path=scorecard_path
    )
    path = Path(rubric_path)
    if not path.is_file():
        raise RubricError(f"rubric set not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise RubricError(f"rubric set {path} is not valid JSON: {exc}") from exc
    if not isinstance(data, Mapping):
        raise RubricError(f"rubric set {path} is not a JSON object.")

    set_id = str(data.get("rubric_set_id", "")).strip()
    version = str(data.get("version", "")).strip()
    if not set_id or not version:
        raise RubricError(
            f"rubric set {path} must carry non-empty rubric_set_id and version "
            "(rubrics are versioned data)."
        )
    sc_id = str(data.get("scorecard_id", ""))
    sc_version = str(data.get("scorecard_version", ""))
    if sc_id != sub.scorecard_id or sc_version != sub.scorecard_version:
        raise RubricError(
            f"rubric set {path} was authored against scorecard "
            f"{sc_id!r} v{sc_version!r}, but the substrate carries "
            f"{sub.scorecard_id!r} v{sub.scorecard_version!r} — re-verify the "
            "rubrics against the current form before grading."
        )

    raw_rubrics = data.get("rubrics")
    if not isinstance(raw_rubrics, list) or not raw_rubrics:
        raise RubricError(f"rubric set {path} has no rubrics array.")
    parsed: dict[str, Rubric] = {}
    for i, raw in enumerate(raw_rubrics):
        rubric = _parse_rubric(raw, i)
        if rubric.expectation_key in parsed:
            raise RubricError(f"duplicate rubric for {rubric.expectation_key!r}.")
        parsed[rubric.expectation_key] = rubric

    expected = sub.by_key()
    missing = sorted(set(expected) - set(parsed))
    extra = sorted(set(parsed) - set(expected))
    if missing or extra:
        raise RubricError(
            f"rubric set {path} is not in bijection with the {len(expected)} PF "
            f"expectations: missing {missing or 'none'}, extra {extra or 'none'} "
            "— every expectation needs exactly one rubric."
        )

    ordered: list[Rubric] = []
    for key, expectation in expected.items():
        rubric = parsed[key]
        if rubric.expectation_text != expectation.text:
            raise RubricError(
                f"rubric {key!r}: expectation_text diverges from the verified "
                f"scorecard text — rubric wording must be verbatim, never "
                f"paraphrased.\n  rubric:    {rubric.expectation_text[:100]!r}\n"
                f"  scorecard: {expectation.text[:100]!r}"
            )
        if rubric.criterion_id != expectation.criterion_id:
            raise RubricError(
                f"rubric {key!r}: criterion_id {rubric.criterion_id!r} does not "
                f"match the expectation's {expectation.criterion_id!r}."
            )
        ordered.append(dataclasses.replace(rubric, source_page=expectation.source_page))

    return RubricSet(
        rubric_set_id=set_id,
        version=version,
        scorecard_id=sc_id,
        scorecard_version=sc_version,
        rubrics=tuple(ordered),
    )


# --------------------------------------------------------------------------- #
# Pack construction for a rubric
# --------------------------------------------------------------------------- #


def build_pack_for(
    rubric: Rubric,
    section_path: Path | str,
    *,
    token_budget: int = DEFAULT_PACK_TOKEN_BUDGET,
    span_budget_fraction: float = DEFAULT_SPAN_BUDGET_FRACTION,
) -> EvidencePack:
    """Build the evidence pack for *rubric* over one section artifact.

    A thin binding of the rubric's versioned selection basis
    (``selection_terms`` + ``anchor_sub_section_ids``) to
    :func:`~harness.evidence_pack.build_evidence_pack` — so E5c/E5f never
    hand-assemble the selection parameters and the pack provably used the
    rubric's recorded basis.
    """
    return build_evidence_pack(
        expectation_key=rubric.expectation_key,
        section_path=section_path,
        selection_terms=rubric.selection_terms,
        anchor_sub_section_ids=rubric.anchor_sub_section_ids,
        token_budget=token_budget,
        span_budget_fraction=span_budget_fraction,
    )


# --------------------------------------------------------------------------- #
# Prompt rendering
# --------------------------------------------------------------------------- #


def build_rubric_system_prompt(rubric: Rubric) -> str:
    """Render the rubric into the judge's system prompt.

    Carries the verbatim expectation text (labelled with its form page), the
    integrity-framed rubric, the numbered evaluation steps, the JSON output
    schema, and the truncation rule: a pack whose ``pack_status`` is
    ``insufficient_context`` must not yield a clean pass.
    """
    steps = "\n".join(f"{i}. {s}" for i, s in enumerate(rubric.evaluation_steps, 1))
    page = f" (form p.{rubric.source_page})" if rubric.source_page is not None else ""
    return (
        RUBRIC_INDEPENDENCE_PREAMBLE
        + "EXPECTATION UNDER ASSESSMENT — verbatim from the HE MSCA Evaluation "
        f"Form{page}:\n{rubric.expectation_text}\n\n"
        f"RUBRIC:\n{rubric.rubric}\n\n"
        f"EVALUATION STEPS:\n{steps}\n\n"
        "You are judging whether the section ADDRESSES and GROUNDS this "
        "expectation — never whether the prose is well written.\n"
        f"If the evidence pack's pack_status is '{PACK_INSUFFICIENT_CONTEXT}', "
        "the pack was truncated to fit a budget: you did not see everything "
        'relevant, so you must not return "passed": true.\n\n'
        "Return ONLY a JSON object, no prose before or after:\n"
        '{"passed": <true only if the expectation is both addressed and '
        "grounded>, "
        '"score": <0.0-1.0, the degree to which the expectation is addressed '
        "and grounded>, "
        '"rationale": "<one or two sentences naming the decisive spans/claims>"}\n\n'
        f"A score at or above {rubric.pass_threshold} corresponds to a pass. "
        'When in doubt, answer "passed": false.'
    )


def build_rubric_user_prompt(rubric: Rubric, pack: EvidencePack) -> str:
    """Render the evidence pack into the judge's user prompt.

    Fails closed on a pack built for a different expectation — a pack must
    never be graded against a rubric it was not selected for.
    """
    if pack.expectation_key != rubric.expectation_key:
        raise RubricError(
            f"evidence pack was built for {pack.expectation_key!r}, not for "
            f"rubric {rubric.expectation_key!r} — refusing to grade a mismatched "
            "pack."
        )
    return (
        pack.render()
        + "Does the section, as evidenced by this pack, substantively address "
        "and ground the expectation above? Apply the evaluation steps and "
        "return only the JSON object."
    )


def build_rubric_prompts(rubric: Rubric, pack: EvidencePack) -> tuple[str, str]:
    """The (system, user) prompt pair for one ``(rubric, pack)`` grading call."""
    return build_rubric_system_prompt(rubric), build_rubric_user_prompt(rubric, pack)


def rubric_prompt_hash(rubric: Rubric, pack: EvidencePack) -> str:
    """The house :func:`~harness.provenance.prompt_hash` of the rendered pair.

    Identical to what the judge records on the verdict's provenance — exposed
    so a report can pin the exact prompts without invoking the judge.
    """
    return prompt_hash(*build_rubric_prompts(rubric, pack))
