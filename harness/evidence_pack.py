"""
Deterministic evidence-pack builder — the judge-budget contract (E5b).

The E5 rubric grader judges each MSCA-PF evaluator expectation against a
Tier-5 section, but the judge budget (Groq free tier: **6k tokens/minute**,
100k/day) makes "send the section" impossible by construction — Excellence
alone is ~120KB of prose plus a 146-entry claim ledger.  This module owns the
contract that keeps E5 inside that ceiling: per ``(expectation, section)`` it
deterministically selects the prose spans and ``claim_statuses`` entries that
*bear on* the expectation, caps the pack to a token budget that provably fits
one judge call under the TPM ceiling, and records **everything it excluded and
why** — a silent cap would read as "the section says nothing more", which is
exactly the false negative an integrity harness must not manufacture.

Selection is deterministic and versioned, no judge involved:

* **Term matching.**  Each expectation carries an authored ``selection_terms``
  list (versioned data in ``harness/rubrics_msca_pf.json``, E5b).  A paragraph
  or claim is a candidate iff it matches at least one term (case-insensitive,
  word-boundary, phrases allowed).
* **Anchor sub-sections.**  The MSCA-PF Part B mirrors the evaluation form:
  each aspect has a dedicated sub-section (``1.1``…``3.2``).  A rubric may
  declare its anchor sub-section(s); their paragraphs get a fixed score bonus
  (:data:`ANCHOR_SCORE_BONUS`) so the section's *dedicated answer* to the
  expectation dominates the pack.  A declared anchor absent from the section
  raises — the mapping fails closed, never silently stops matching.
* **Budget fill.**  Candidates are ranked ``(-score, document order)`` and
  greedily packed into the token budget (prose first, then claims).  Anything
  relevant that did not fit is recorded with reason ``over_budget`` and flips
  the pack status to :data:`PACK_INSUFFICIENT_CONTEXT` — an **explicit
  outcome** the grader must not read as a clean pass
  (:func:`pack_forbids_clean_pass`).

Token estimates use a fixed ``chars/4`` heuristic — approximate, but
deterministic and uniform, which is what a reproducible budget needs.

Measured reality (2026-08-07, the committed sections): the material bearing on
each expectation is ~5-18k estimated tokens against a 3k default budget, so on
real sections :data:`PACK_INSUFFICIENT_CONTEXT` is the **honest common
outcome**, not an edge case — the dedicated sub-section answering an
expectation simply does not fit the free-tier ceiling.  That is the ticket's
design: the truncation is explicit, the exclusions are recorded, and a
truncated pack forbids a clean pass; E5f may raise the effective budget by
switching to the uncapped local judge, never by silently shrinking the pack.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate; reads Tier-5 section
    artifacts read-only and writes nothing.  Never a runtime gate.  See
    ``harness/HARNESS.md``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from harness.judge import DEFAULT_JUDGE_MAX_TOKENS
from harness.status_faithfulness import SectionClaim, load_section_claims

__all__ = [
    "GROQ_TPM_LIMIT",
    "APPROX_CHARS_PER_TOKEN",
    "RUBRIC_PROMPT_ALLOWANCE",
    "MAX_PACK_TOKEN_BUDGET",
    "DEFAULT_PACK_TOKEN_BUDGET",
    "DEFAULT_SPAN_BUDGET_FRACTION",
    "ANCHOR_SCORE_BONUS",
    "PACK_COMPLETE",
    "PACK_INSUFFICIENT_CONTEXT",
    "EXCLUDED_NOT_RELEVANT",
    "EXCLUDED_OVER_BUDGET",
    "KIND_PROSE_SPAN",
    "KIND_CLAIM",
    "SPAN_DIVIDER",
    "CLAIM_DIVIDER",
    "EvidencePackError",
    "estimate_tokens",
    "normalize_terms",
    "ProseSpan",
    "PackClaim",
    "ExcludedItem",
    "EvidencePack",
    "build_evidence_pack",
    "pack_forbids_clean_pass",
    "clean_pass",
]

#: The Groq free-tier per-minute token ceiling the whole contract is sized to.
GROQ_TPM_LIMIT: int = 6000

#: Deterministic token estimate: ``ceil(len(text) / 4)`` characters per token.
APPROX_CHARS_PER_TOKEN: int = 4

#: Headroom reserved for the rubric system prompt + closing question around
#: the pack.  The committed E5b rubrics render to ~650 estimated tokens of
#: overhead; a test pins every rubric's actual overhead under this allowance,
#: so a rubric growing past it breaks a test instead of silently blowing the
#: TPM ceiling.
RUBRIC_PROMPT_ALLOWANCE: int = 900

#: Hard cap on any pack budget: one judge call (pack + rubric prompt +
#: completion budget) must fit under the TPM ceiling *by construction*.  With
#: the judge's default completion budget this is 6000 − 2048 − 900 = 3052.
MAX_PACK_TOKEN_BUDGET: int = (
    GROQ_TPM_LIMIT - DEFAULT_JUDGE_MAX_TOKENS - RUBRIC_PROMPT_ALLOWANCE
)

#: Default pack budget — under the hard cap with margin.  "Headroom for N≥3"
#: means each of the N≥3 majority samples individually clears the ceiling:
#: three samples *within one minute* are arithmetically impossible regardless
#: of pack size (3 × the 2048-token completion reserve alone exceeds 6k TPM),
#: so the N is paced across minute windows by E5f, one clean-fitting call per
#: window.
DEFAULT_PACK_TOKEN_BUDGET: int = 3000

#: Fraction of the usable budget offered to prose spans before claims fill the
#: remainder (a pack needs both: prose answers "addressed?", claims answer
#: "grounded?").
DEFAULT_SPAN_BUDGET_FRACTION: float = 0.6

#: Score bonus for paragraphs inside a declared anchor sub-section — the Part B
#: sub-section dedicated to the expectation outranks a stray term match
#: elsewhere, term-free anchor paragraphs stay candidates (score ≥ 1).
ANCHOR_SCORE_BONUS: int = 2

#: Pack status: every relevant candidate fit the budget.
PACK_COMPLETE: str = "complete"
#: Pack status: at least one relevant candidate was excluded for budget — an
#: explicit outcome; a rubric graded on this pack must not read as a clean pass.
PACK_INSUFFICIENT_CONTEXT: str = "insufficient_context"

#: Exclusion reason: matched no selection term (and no anchor bonus).
EXCLUDED_NOT_RELEVANT: str = "not_relevant"
#: Exclusion reason: relevant, but did not fit the token budget.
EXCLUDED_OVER_BUDGET: str = "over_budget"

#: Item kinds (``ProseSpan`` / ``PackClaim``) as recorded on :class:`ExcludedItem`.
KIND_PROSE_SPAN: str = "prose_span"
KIND_CLAIM: str = "claim"


class EvidencePackError(Exception):
    """The section artifact, anchors, or budget parameters are unusable (fail-closed)."""


def estimate_tokens(text: str) -> int:
    """Deterministic token estimate: ``ceil(len/4)``, minimum 1.

    A heuristic, not a tokenizer — uniform and reproducible is what the budget
    contract needs; the generous :data:`RUBRIC_PROMPT_ALLOWANCE` and the gap
    between the default budget and :data:`MAX_PACK_TOKEN_BUDGET` absorb the
    approximation error.
    """
    return max(1, (len(text) + APPROX_CHARS_PER_TOKEN - 1) // APPROX_CHARS_PER_TOKEN)


def normalize_terms(terms: Sequence[str]) -> tuple[str, ...]:
    """Normalize selection terms: collapse whitespace, lowercase, dedup (order kept).

    An empty term list — before or after normalization — raises: a pack built
    with no selection basis would silently select nothing.
    """
    seen: dict[str, None] = {}
    for term in terms:
        t = " ".join(str(term).split()).strip().lower()
        if t:
            seen.setdefault(t, None)
    if not seen:
        raise EvidencePackError("selection_terms must contain at least one non-empty term.")
    return tuple(seen)


def _term_patterns(terms: tuple[str, ...]) -> tuple[tuple[str, re.Pattern[str]], ...]:
    """Compile one word-boundary, case-insensitive pattern per term (phrases allowed)."""
    return tuple(
        (term, re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)", re.IGNORECASE))
        for term in terms
    )


def _matched_terms(
    text: str, patterns: tuple[tuple[str, re.Pattern[str]], ...]
) -> tuple[str, ...]:
    return tuple(term for term, pattern in patterns if pattern.search(text))


# --------------------------------------------------------------------------- #
# Pack items
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ProseSpan:
    """One paragraph of a section's prose, addressable as ``<sub_section>¶<index>``.

    ``matched_terms`` records the deterministic basis on which the span was
    selected (may be empty for a term-free anchor paragraph); ``in_anchor``
    whether the span sits in a declared anchor sub-section.
    """

    sub_section_id: str
    sub_section_index: int
    paragraph_index: int
    text: str
    matched_terms: tuple[str, ...]
    in_anchor: bool

    @property
    def key(self) -> str:
        """The span's stable identity within its section (``1.2¶7``)."""
        return f"{self.sub_section_id}¶{self.paragraph_index}"

    def render(self) -> str:
        """The span's deterministic rendered form — what the budget counts."""
        return f"[span {self.key}]\n{self.text}\n\n"

    @property
    def token_estimate(self) -> int:
        """The span's budget cost: the token estimate of its rendered form."""
        return estimate_tokens(self.render())


@dataclass(frozen=True)
class PackClaim:
    """One selected ``claim_statuses`` entry, with its selection basis and cost."""

    claim: SectionClaim
    matched_terms: tuple[str, ...]

    @property
    def key(self) -> str:
        """The claim's disambiguated ``entry_key`` (the E3a identity discipline)."""
        return self.claim.entry_key

    def render(self) -> str:
        """The claim's deterministic rendered form (status + source_ref verbatim)."""
        c = self.claim
        return (
            f"[claim {c.entry_key} | status={c.status} | source_ref={c.source_ref}]\n"
            f"{c.claim_summary}\n\n"
        )

    @property
    def token_estimate(self) -> int:
        """The claim's budget cost: the token estimate of its rendered form."""
        return estimate_tokens(self.render())


@dataclass(frozen=True)
class ExcludedItem:
    """One candidate that is **not** in the pack — the no-silent-caps record.

    For an excluded **claim**, ``status`` and ``source_ref`` carry the ledger
    entry's identity (additive fields, empty for prose spans) — so a
    downstream consumer (E5e's spine cross-reference) can still see *what* was
    excluded, not merely that something was.  An exclusion record that hid the
    claim's identity would itself be a silent cap.
    """

    kind: str  # "prose_span" | "claim"
    key: str
    reason: str  # EXCLUDED_NOT_RELEVANT | EXCLUDED_OVER_BUDGET
    matched_terms: tuple[str, ...]
    token_estimate: int
    status: str = ""
    source_ref: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "key": self.key,
            "reason": self.reason,
            "matched_terms": list(self.matched_terms),
            "token_estimate": self.token_estimate,
            "status": self.status,
            "source_ref": self.source_ref,
        }


# --------------------------------------------------------------------------- #
# The pack
# --------------------------------------------------------------------------- #


#: The two divider lines the frame wraps the pack's items in.
SPAN_DIVIDER: str = "=== PROSE SPANS (verbatim from the section under assessment) ===\n\n"
CLAIM_DIVIDER: str = "=== CLAIM-LEDGER ENTRIES (status and source_ref as recorded) ===\n\n"


def _render_header(expectation_key: str, section_id: str, status: str) -> str:
    return (
        "EVIDENCE PACK\n"
        f"expectation_key: {expectation_key}\n"
        f"section: {section_id}\n"
        f"pack_status: {status}\n"
        "\n"
    )


def _render_frame(expectation_key: str, section_id: str, status: str) -> str:
    """The pack's fixed wrapper text (header + the two dividers)."""
    return _render_header(expectation_key, section_id, status) + SPAN_DIVIDER + CLAIM_DIVIDER


@dataclass(frozen=True)
class EvidencePack:
    """A reproducible, budget-bounded evidence pack for one ``(expectation, section)``.

    ``spans`` and ``claims`` are in document order (the readable form; rank
    only decided *selection*).  ``excluded`` holds every non-included candidate
    with its reason — what was excluded is part of the record.  ``status`` is
    :data:`PACK_COMPLETE` unless a relevant candidate was excluded for budget,
    in which case it is :data:`PACK_INSUFFICIENT_CONTEXT` and
    :func:`pack_forbids_clean_pass` returns ``True``.
    """

    expectation_key: str
    section_id: str
    section_path: str
    status: str
    token_budget: int
    spans: tuple[ProseSpan, ...]
    claims: tuple[PackClaim, ...]
    excluded: tuple[ExcludedItem, ...]
    selection_terms: tuple[str, ...]
    anchor_sub_section_ids: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        """No relevant content existed at all — legitimate "not addressed" evidence."""
        return not self.spans and not self.claims

    def render(self) -> str:
        """The deterministic text the judge sees (and the budget counted).

        The frame's two dividers wrap the spans and claims respectively; items
        appear in document order.
        """
        parts = [
            _render_header(self.expectation_key, self.section_id, self.status),
            SPAN_DIVIDER,
        ]
        parts.extend(s.render() for s in self.spans)
        parts.append(CLAIM_DIVIDER)
        parts.extend(c.render() for c in self.claims)
        return "".join(parts)

    @property
    def token_estimate(self) -> int:
        """The token estimate of the full rendered pack (≤ ``token_budget``;
        per-character estimates sub-add, so the sum of the parts bounds it)."""
        return estimate_tokens(self.render())

    def to_dict(self) -> dict[str, Any]:
        """The full selection record — inclusions, exclusions, basis, budget."""
        return {
            "expectation_key": self.expectation_key,
            "section_id": self.section_id,
            "section_path": self.section_path,
            "status": self.status,
            "token_budget": self.token_budget,
            "token_estimate": self.token_estimate,
            "selection_terms": list(self.selection_terms),
            "anchor_sub_section_ids": list(self.anchor_sub_section_ids),
            "spans": [
                {
                    "key": s.key,
                    "matched_terms": list(s.matched_terms),
                    "in_anchor": s.in_anchor,
                    "token_estimate": s.token_estimate,
                }
                for s in self.spans
            ],
            "claims": [
                {
                    "key": c.key,
                    "status": c.claim.status,
                    "source_ref": c.claim.source_ref,
                    "matched_terms": list(c.matched_terms),
                    "token_estimate": c.token_estimate,
                }
                for c in self.claims
            ],
            "excluded": [e.to_dict() for e in self.excluded],
        }


def pack_forbids_clean_pass(pack: EvidencePack) -> bool:
    """Whether a rubric graded on this pack must **not** be read as a clean pass.

    ``True`` for a truncated pack (:data:`PACK_INSUFFICIENT_CONTEXT`): the
    judge did not see everything relevant, so a pass verdict is not evidence
    the expectation is met.  The E5c grader consults this; the rubric system
    prompt additionally instructs the judge directly.
    """
    return pack.status == PACK_INSUFFICIENT_CONTEXT


def clean_pass(pack: EvidencePack, judge_passed: bool | None) -> bool:
    """The code-side enforcement of "a truncated pack is never a clean pass".

    ``True`` iff the judge passed the rubric **and** the pack does not forbid a
    clean pass.  The prompt instructs the judge about truncation, but a prompt
    is a request, not a guarantee — this function is the mechanism: whatever
    the judge answered over an :data:`PACK_INSUFFICIENT_CONTEXT` pack, the
    combined outcome is not a clean pass.  E5c derives its pass field through
    this, never from the raw verdict alone.
    """
    return bool(judge_passed) and not pack_forbids_clean_pass(pack)


# --------------------------------------------------------------------------- #
# Section loading
# --------------------------------------------------------------------------- #


def _load_sub_sections(path: Path) -> list[tuple[str, str]]:
    """Load ``(sub_section_id, content)`` pairs of a Phase-8 section JSON."""
    if not path.is_file():
        raise EvidencePackError(f"section file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise EvidencePackError(f"section {path} is not valid JSON: {exc}") from exc
    sub_sections = data.get("sub_sections") if isinstance(data, Mapping) else None
    if not isinstance(sub_sections, list) or not sub_sections:
        raise EvidencePackError(f"section {path} has no sub_sections array.")
    pairs: list[tuple[str, str]] = []
    for i, ss in enumerate(sub_sections):
        if not isinstance(ss, Mapping) or not str(ss.get("sub_section_id", "")).strip():
            raise EvidencePackError(
                f"section {path}: sub_sections[{i}] has no sub_section_id."
            )
        pairs.append((str(ss["sub_section_id"]), str(ss.get("content", ""))))
    return pairs


def _split_paragraphs(content: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", content) if p.strip()]


# --------------------------------------------------------------------------- #
# The builder
# --------------------------------------------------------------------------- #


def _fill_budget(
    candidates: list,
    budget: int,
    kind: str,
    excluded: list[ExcludedItem],
) -> tuple[list, int, bool]:
    """Greedily pack ranked ``(score, doc_order, item)`` candidates into *budget*.

    Returns ``(included as (doc_order, item), tokens used, truncated?)``; every
    candidate that did not fit is appended to *excluded* with reason
    :data:`EXCLUDED_OVER_BUDGET` — the shared no-silent-caps fill for spans and
    claims.
    """
    included: list = []
    used = 0
    truncated = False
    for _score, order, item in candidates:
        if used + item.token_estimate <= budget:
            included.append((order, item))
            used += item.token_estimate
        else:
            truncated = True
            claim = getattr(item, "claim", None)  # PackClaim carries identity
            excluded.append(
                ExcludedItem(
                    kind=kind,
                    key=item.key,
                    reason=EXCLUDED_OVER_BUDGET,
                    matched_terms=item.matched_terms,
                    token_estimate=item.token_estimate,
                    status=claim.status if claim is not None else "",
                    source_ref=claim.source_ref if claim is not None else "",
                )
            )
    return included, used, truncated


def build_evidence_pack(
    *,
    expectation_key: str,
    section_path: Path | str,
    selection_terms: Sequence[str],
    anchor_sub_section_ids: Sequence[str] = (),
    token_budget: int = DEFAULT_PACK_TOKEN_BUDGET,
    span_budget_fraction: float = DEFAULT_SPAN_BUDGET_FRACTION,
) -> EvidencePack:
    """Deterministically build the evidence pack for one ``(expectation, section)``.

    Selection pipeline (no judge, no randomness):

    1. Split every sub-section's prose into paragraphs; load the claim ledger.
    2. Score each paragraph/claim by matched ``selection_terms`` (paragraphs in
       a declared anchor sub-section get :data:`ANCHOR_SCORE_BONUS`).  Score 0
       → excluded ``not_relevant``.
    3. Rank candidates ``(-score, document order)`` and greedily fill the
       budget — prose spans into ``span_budget_fraction`` of the usable budget,
       claims into the remainder.  A relevant candidate that does not fit is
       excluded ``over_budget``.
    4. Status: :data:`PACK_COMPLETE` iff nothing relevant was excluded for
       budget, else :data:`PACK_INSUFFICIENT_CONTEXT` (explicit, never silent).

    Raises :class:`EvidencePackError` on an unusable section artifact, a
    declared anchor absent from the section, an empty term list, or a budget
    outside ``(0, MAX_PACK_TOKEN_BUDGET]`` — the hard cap is what guarantees a
    single judge call fits under the :data:`GROQ_TPM_LIMIT` ceiling.
    """
    if not str(expectation_key).strip():
        raise EvidencePackError("expectation_key must be non-empty.")
    if not 0 < token_budget <= MAX_PACK_TOKEN_BUDGET:
        raise EvidencePackError(
            f"token_budget must be in (0, {MAX_PACK_TOKEN_BUDGET}] so one judge "
            f"call (pack + rubric prompt allowance {RUBRIC_PROMPT_ALLOWANCE} + "
            f"completion budget {DEFAULT_JUDGE_MAX_TOKENS}) fits the "
            f"{GROQ_TPM_LIMIT}-TPM ceiling; got {token_budget}."
        )
    if not 0.0 < span_budget_fraction < 1.0:
        raise EvidencePackError(
            f"span_budget_fraction must be in (0, 1); got {span_budget_fraction!r}."
        )

    terms = normalize_terms(selection_terms)
    patterns = _term_patterns(terms)
    path = Path(section_path)
    section_id = path.stem

    sub_sections = _load_sub_sections(path)
    known_ids = {sid for sid, _ in sub_sections}
    anchors = tuple(str(a) for a in anchor_sub_section_ids)
    missing_anchors = [a for a in anchors if a not in known_ids]
    if missing_anchors:
        raise EvidencePackError(
            f"anchor sub-section(s) {missing_anchors} not present in {path} "
            f"(has: {sorted(known_ids)}) — the anchor map must fail closed, not "
            "silently stop matching."
        )
    claims = load_section_claims(path)

    # -- score every candidate ------------------------------------------- #
    span_candidates: list[tuple[int, int, ProseSpan]] = []  # (score, doc_order, span)
    excluded: list[ExcludedItem] = []
    doc_order = 0
    for ss_index, (sid, content) in enumerate(sub_sections):
        in_anchor = sid in anchors
        for p_index, text in enumerate(_split_paragraphs(content)):
            matched = _matched_terms(text, patterns)
            score = len(matched) + (ANCHOR_SCORE_BONUS if in_anchor else 0)
            span = ProseSpan(
                sub_section_id=sid,
                sub_section_index=ss_index,
                paragraph_index=p_index,
                text=text,
                matched_terms=matched,
                in_anchor=in_anchor,
            )
            if score >= 1:
                span_candidates.append((score, doc_order, span))
            else:
                excluded.append(
                    ExcludedItem(
                        kind=KIND_PROSE_SPAN,
                        key=span.key,
                        reason=EXCLUDED_NOT_RELEVANT,
                        matched_terms=matched,
                        token_estimate=span.token_estimate,
                    )
                )
            doc_order += 1

    claim_candidates: list[tuple[int, int, PackClaim]] = []
    for order, claim in enumerate(claims):
        matched = _matched_terms(claim.claim_summary, patterns)
        pc = PackClaim(claim=claim, matched_terms=matched)
        if matched:
            claim_candidates.append((len(matched), order, pc))
        else:
            excluded.append(
                ExcludedItem(
                    kind=KIND_CLAIM,
                    key=pc.key,
                    reason=EXCLUDED_NOT_RELEVANT,
                    matched_terms=(),
                    token_estimate=pc.token_estimate,
                    status=claim.status,
                    source_ref=claim.source_ref,
                )
            )

    # -- budget fill ------------------------------------------------------ #
    frame_tokens = estimate_tokens(
        _render_frame(expectation_key, section_id, PACK_INSUFFICIENT_CONTEXT)
    )
    usable = token_budget - frame_tokens
    if usable <= 0:
        raise EvidencePackError(
            f"token_budget {token_budget} cannot even carry the pack frame "
            f"({frame_tokens} tokens)."
        )

    span_candidates.sort(key=lambda t: (-t[0], t[1]))
    claim_candidates.sort(key=lambda t: (-t[0], t[1]))

    # Spans get their fraction first, claims the remainder.  Deliberately
    # conservative: a span excluded here is over the *span* budget even if
    # claim budget goes unused — the split biases toward declaring
    # insufficient_context rather than quietly re-balancing the pack shape.
    span_budget = int(usable * span_budget_fraction)
    included_spans, spans_used, spans_truncated = _fill_budget(
        span_candidates, span_budget, KIND_PROSE_SPAN, excluded
    )
    included_claims, _claims_used, claims_truncated = _fill_budget(
        claim_candidates, usable - spans_used, KIND_CLAIM, excluded
    )

    included_spans.sort(key=lambda t: t[0])
    included_claims.sort(key=lambda t: t[0])
    truncated = spans_truncated or claims_truncated
    status = PACK_INSUFFICIENT_CONTEXT if truncated else PACK_COMPLETE

    return EvidencePack(
        expectation_key=expectation_key,
        section_id=section_id,
        section_path=str(path),
        status=status,
        token_budget=token_budget,
        spans=tuple(s for _, s in included_spans),
        claims=tuple(c for _, c in included_claims),
        excluded=tuple(excluded),
        selection_terms=terms,
        anchor_sub_section_ids=anchors,
    )
