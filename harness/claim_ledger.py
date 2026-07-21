"""
Claim-ledger completeness — the "escaped claim" detector (E3, headline signal #2).

The pipeline's anti-fabrication predicates all watch the **ledger side**: every
logged claim has a status, a ``source_ref``, a declaration where assumed.  None
of them read the *prose*.  A drafter that asserts a fact in a section's
``content`` without ever emitting a ``claim_id`` for it has fabricated **around**
the ledger — the threat the W1 predicate cannot reach, and the output-side gap
in CLAUDE.md §10.5: *"Unattributed claims must be flagged, not asserted."*

This module closes that gap with a three-stage, judge-assisted diff:

1. **Decompose** — prose is chunked deterministically (whole paragraphs) and an
   independent judge decomposes each chunk into **atomic assertions**,
   *exhaustively* ("do not filter for importance" — materiality is a separate
   classifier, which also removes the incentive for the decomposer to silently
   drop borderline content).
2. **Classify materiality** — each assertion runs through the deployed §10.5
   classifier (:func:`harness.materiality.classify_materiality`).  Non-material
   prose (transitions, framing, definitional description) is excluded from the
   diff but *counted and visible*, never silently dropped.
3. **Match against the ledger** — each material assertion is matched **by
   meaning** against the section's claim records.  ``claim_id`` is *not* a key
   (real ledgers repeat ids across drafting blocks — three unrelated ``C01``\\ s
   in excellence), so the ledger is treated as a set of
   ``(claim_summary, status, source_ref)`` records, de-duplicated, and every
   surfaced match names the disambiguated ``entry_key``.  Matching is a
   deterministic lexical shortlist followed by one **batched** judge call over
   the numbered candidates (the judge answers with a candidate *number*, never
   an ambiguous claim id); a passed-but-unattributable batched verdict
   escalates to the stricter per-candidate boolean question — a bounded
   re-ask, not a silent repair.

A **material assertion no ledger record covers is an ESCAPED claim — the hard
finding** this metric exists to surface.  An escape's *basis* is always
recorded (``no_lexical_candidates`` vs ``judged_uncovered`` vs
``escalation_unconfirmed``) so a zero-overlap paraphrase false-escape is
legible rather than mistaken for proven fabrication.

Two batch-metric divergences from E2's per-claim posture, both deliberate:
a per-assertion :class:`~harness.judge.JudgeResponseError` is caught and
surfaced as an ``unjudgeable`` finding rather than propagated (an E3 run makes
thousands of judge calls; aborting at call 900 would produce *no* report,
which serves integrity worse than a report with the failure visible), and a
malformed decomposition response fails only its own chunk
(:class:`ChunkFailure`, surfaced in the result and report notes).

Reporting-only; zero DAG runs.  The report notes stamp the materiality
calibration state (uncalibrated / no labeled negatives / repinned judge), so a
reader knows how much to trust the non-material exclusions — the E1.5
"advisory until characterized" posture applied to the classifier.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate; reads Tier-5 sections
    read-only and writes only harness-owned artifacts.  Never a runtime gate.
    See ``harness/HARNESS.md``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from runner.json_extract import extract_first_json_object
from harness.faithfulness import INDEPENDENCE_PREAMBLE
from harness.judge import (
    Judge,
    JudgeResponseError,
    JudgeResult,
    MajorityJudgeResult,
)
from harness.materiality import (
    MaterialityCalibration,
    classify_materiality,
    normalize_text,
)
from harness.provenance import ProvenanceLog, ProvenanceRecord, prompt_hash
from harness.report import HarnessReport, build_report
from harness.routing import RoutingDecision, assert_judgeable
from harness.verdict import MajorityVerdict, Verdict, validate_sample_count

__all__ = [
    "CLAIM_LEDGER_METRIC",
    "DECOMPOSITION_METRIC",
    "COVERAGE_METRIC",
    "DEFAULT_MAX_CHUNK_CHARS",
    "DEFAULT_SHORTLIST_K",
    "ZERO_ASSERTION_FLOOR_CHARS",
    "OUTCOME_COVERED",
    "OUTCOME_ESCAPED",
    "OUTCOME_NON_MATERIAL",
    "OUTCOME_UNJUDGEABLE",
    "ESCAPE_NO_LEXICAL_CANDIDATES",
    "ESCAPE_JUDGED_UNCOVERED",
    "ESCAPE_ESCALATION_UNCONFIRMED",
    "ClaimLedgerError",
    "SubSectionProse",
    "load_section_prose",
    "ProseChunk",
    "chunk_prose",
    "build_decomposition_prompt",
    "parse_assertions_payload",
    "decompose_chunk",
    "Assertion",
    "dedup_assertions",
    "LedgerRecord",
    "dedup_ledger_claims",
    "lexical_shortlist",
    "build_coverage_prompt",
    "extract_covered_by",
    "judge_assertion_covered_by",
    "CoverageOutcome",
    "match_assertion",
    "AssertionFinding",
    "ChunkFailure",
    "LedgerCompletenessResult",
    "evaluate_ledger_completeness",
]

#: Metric names.  The headline metric is the completeness diff; decomposition
#: and coverage stamp their own metric names on provenance so every judge call
#: in the chain is attributable to its stage.
CLAIM_LEDGER_METRIC: str = "claim_ledger_completeness"
DECOMPOSITION_METRIC: str = "claim_ledger_decomposition"
COVERAGE_METRIC: str = "claim_ledger_coverage"

#: Paragraphs are grouped into chunks of at most this many characters (the
#: largest real paragraph is ~1.4 KB, so no paragraph is ever split).
DEFAULT_MAX_CHUNK_CHARS: int = 4000

#: How many lexically-nearest ledger records the batched coverage question
#: presents.  Small enough to keep the judge prompt bounded, large enough that
#: a genuinely-ledgered assertion's record is practically always present.
DEFAULT_SHORTLIST_K: int = 8

#: A chunk at least this long that decomposes to *zero* assertions is
#: surfaced as a density anomaly (possible silent under-extraction) — real
#: pure-transition chunks are short.
ZERO_ASSERTION_FLOOR_CHARS: int = 600

#: Assertion outcomes.
OUTCOME_COVERED: str = "covered"
OUTCOME_ESCAPED: str = "escaped"
OUTCOME_NON_MATERIAL: str = "non_material"
OUTCOME_UNJUDGEABLE: str = "unjudgeable"

#: Why an escaped assertion escaped — kept distinct so a reader can tell a
#: judged non-coverage from a shortlist miss (possible paraphrase false-escape).
ESCAPE_NO_LEXICAL_CANDIDATES: str = "no_lexical_candidates"
ESCAPE_JUDGED_UNCOVERED: str = "judged_uncovered"
ESCAPE_ESCALATION_UNCONFIRMED: str = "escalation_unconfirmed"


class ClaimLedgerError(Exception):
    """A section artifact, judge response, or metric input is malformed."""


def _default_clock() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Prose loading + chunking (pure)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SubSectionProse:
    """One entry of a section's ``sub_sections`` array — the prose under audit."""

    sub_section_id: str
    title: str
    content: str

    def __post_init__(self) -> None:
        if not str(self.sub_section_id).strip():
            raise ClaimLedgerError("SubSectionProse.sub_section_id must be non-empty.")


def load_section_prose(path: Path | str) -> tuple[SubSectionProse, ...]:
    """Load a Phase-8 section JSON's ``sub_sections`` prose, in order.

    Fail-closed like :func:`~harness.status_faithfulness.load_section_claims`:
    a missing file or an absent/non-array ``sub_sections`` raises — E3 has no
    prose to audit without it.
    """
    p = Path(path)
    if not p.is_file():
        raise ClaimLedgerError(f"section file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ClaimLedgerError(f"section {p} is not valid JSON: {exc}") from exc
    subs = data.get("sub_sections") if isinstance(data, Mapping) else None
    if not isinstance(subs, list):
        raise ClaimLedgerError(f"section {p} has no sub_sections array to audit.")
    out: list[SubSectionProse] = []
    for s in subs:
        if not isinstance(s, Mapping):
            raise ClaimLedgerError(f"section {p}: sub_sections entries must be objects.")
        out.append(
            SubSectionProse(
                sub_section_id=str(s.get("sub_section_id", "")),
                title=str(s.get("title", "")),
                content=str(s.get("content", "")),
            )
        )
    return tuple(out)


@dataclass(frozen=True)
class ProseChunk:
    """A bounded group of whole paragraphs from one sub-section."""

    sub_section_id: str
    chunk_index: int
    text: str

    @property
    def chunk_id(self) -> str:
        return f"{self.sub_section_id}:c{self.chunk_index:02d}"


def chunk_prose(
    sub: SubSectionProse,
    *,
    max_chars: int = DEFAULT_MAX_CHUNK_CHARS,
) -> tuple[ProseChunk, ...]:
    """Group *sub*'s paragraphs into chunks of at most *max_chars*.

    Deterministic and paragraph-atomic: paragraphs (blank-line separated) are
    never split — an oversized paragraph becomes its own (over-cap) chunk
    rather than being cut mid-sentence, so no assertion can straddle a chunk
    boundary.  No overlap is added (overlap would double-decompose text; exact
    duplicates are handled by :func:`dedup_assertions`).
    """
    paragraphs = [p.strip() for p in sub.content.split("\n\n") if p.strip()]
    chunks: list[ProseChunk] = []
    current: list[str] = []
    size = 0
    for para in paragraphs:
        para_len = len(para) + (2 if current else 0)
        if current and size + para_len > max_chars:
            chunks.append(
                ProseChunk(sub.sub_section_id, len(chunks), "\n\n".join(current))
            )
            current, size = [], 0
            para_len = len(para)
        current.append(para)
        size += para_len
    if current:
        chunks.append(ProseChunk(sub.sub_section_id, len(chunks), "\n\n".join(current)))
    return tuple(chunks)


# --------------------------------------------------------------------------- #
# Decomposition (generative — raw judge invocation, strict parse)
# --------------------------------------------------------------------------- #

_DECOMPOSITION_SYSTEM: str = (
    INDEPENDENCE_PREAMBLE
    + "Your single task: decompose the PASSAGE below into ATOMIC ASSERTIONS — "
    "every declarative factual statement the passage asserts, each restated as "
    "one short, self-contained sentence.\n\n"
    "Be EXHAUSTIVE: extract every assertion, however minor. Do NOT filter for "
    "importance or materiality — a separate classifier does that. Do NOT add "
    "facts the passage does not assert, and do not merge distinct facts into "
    "one assertion. Pure transitions, headings, and rhetorical framing assert "
    "nothing and yield no assertions.\n\n"
    "Return ONLY a JSON object, no prose before or after:\n"
    '{"assertions": ["<assertion 1>", "<assertion 2>", ...]}\n\n'
    "An empty list is valid when the passage asserts nothing."
)


def build_decomposition_prompt(chunk: ProseChunk) -> tuple[str, str]:
    """Return the ``(system_prompt, user_prompt)`` for decomposing one chunk."""
    user_prompt = (
        f"PASSAGE (from sub-section {chunk.sub_section_id}):\n{chunk.text}\n\n"
        "Decompose the PASSAGE into atomic assertions. Return the JSON object."
    )
    return _DECOMPOSITION_SYSTEM, user_prompt


def parse_assertions_payload(raw: str) -> tuple[str, ...]:
    """Parse a decomposition response strictly — no silent repair (§17.6.5 spirit).

    The response must contain a JSON *object* with an ``assertions`` array of
    non-blank strings.  An empty array is **valid** (a pure-transition chunk
    asserts nothing); anything malformed — no object, a bare top-level array,
    a missing/non-array key, a non-string or blank member — raises
    :class:`ClaimLedgerError` so the chunk fails loudly instead of yielding a
    quietly wrong assertion set.
    """
    payload = extract_first_json_object(raw)
    if payload is None:
        raise ClaimLedgerError(
            f"decomposition response carried no parseable JSON object: {raw[:200]!r}"
        )
    assertions = payload.get("assertions")
    if not isinstance(assertions, list):
        raise ClaimLedgerError(
            "decomposition response has no 'assertions' array "
            f"(got {type(assertions).__name__})."
        )
    out: list[str] = []
    for i, a in enumerate(assertions):
        if not isinstance(a, str) or not a.strip():
            raise ClaimLedgerError(
                f"decomposition assertion [{i}] must be a non-blank string; got {a!r}."
            )
        out.append(a.strip())
    return tuple(out)


def decompose_chunk(
    judge: Judge,
    chunk: ProseChunk,
    *,
    provenance_log: ProvenanceLog | None = None,
    clock: Callable[[], str] | None = None,
) -> tuple[str, ...]:
    """Decompose one chunk into assertion texts via the independent judge.

    Uses :meth:`~harness.judge.Judge.raw_invoke` — decomposition is generative,
    not a boolean verdict, so it does not flow through ``evaluate()``.  Its
    provenance is therefore hand-built here.  It lands in the explicit
    *provenance_log* when one is passed (the
    :func:`~harness.calibration.calibrate_with_judge` precedent), **falling
    back to the judge's own attached log** — so a caller using the standard
    attach-a-log-to-the-Judge pattern still gets decomposition provenance
    rather than a silent gap; only a judge with no log anywhere logs nothing.
    A malformed response raises :class:`ClaimLedgerError`; the pipeline surfaces
    it as a :class:`ChunkFailure`.
    """
    system_prompt, user_prompt = build_decomposition_prompt(chunk)
    raw = judge.raw_invoke(system_prompt, user_prompt)
    texts = parse_assertions_payload(raw)
    log = provenance_log if provenance_log is not None else judge.provenance_log
    if log is not None:
        log.append(
            ProvenanceRecord(
                judge_model=judge.config.model,
                judge_version=judge.config.version,
                prompt_hash=prompt_hash(system_prompt, user_prompt),
                score=None,
                rationale=f"decomposed {len(texts)} assertion(s) from {chunk.chunk_id}",
                metric=DECOMPOSITION_METRIC,
                property_key=chunk.chunk_id,
                passed=None,
                timestamp=(clock or _default_clock)(),
            )
        )
    return texts


#: Decomposer shape — injectable so tests (and future non-judge decomposers)
#: supply assertion texts without a backend.  ``(chunk) -> assertion texts``.
Decomposer = Callable[[ProseChunk], "tuple[str, ...] | Sequence[str]"]

#: Materiality-classifier shape — ``(text, property_key) -> Verdict``.
#: Defaults to the deployed :func:`~harness.materiality.classify_materiality`.
MaterialityClassifier = Callable[[str, str], "Verdict | MajorityVerdict"]


# --------------------------------------------------------------------------- #
# Assertions
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Assertion:
    """One atomic assertion extracted from prose.

    ``assertion_id`` is synthetic (``excellence:1.2:c03:a05``) — unique within
    a run and never colliding with a deterministic predicate name, so it routes
    cleanly.  ``also_in`` lists further chunk ids where the same (normalized)
    assertion re-occurred; duplicates are judged once but never lose their
    origins.
    """

    assertion_id: str
    text: str
    sub_section_id: str
    chunk_id: str
    also_in: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not str(self.text).strip():
            raise ClaimLedgerError(f"Assertion {self.assertion_id!r}: text must be non-empty.")


def dedup_assertions(assertions: Sequence[Assertion]) -> tuple[Assertion, ...]:
    """Collapse assertions with identical normalized text, keeping all origins.

    First occurrence wins the id and text; later occurrences contribute their
    ``chunk_id`` to ``also_in``.  Order is first-occurrence order.
    """
    by_key: dict[str, Assertion] = {}
    extra: dict[str, list[str]] = {}
    for a in assertions:
        key = normalize_text(a.text)
        if key in by_key:
            extra.setdefault(key, []).append(a.chunk_id)
        else:
            by_key[key] = a
    out: list[Assertion] = []
    for key, a in by_key.items():
        dups = tuple(extra.get(key, ()))
        out.append(
            Assertion(
                assertion_id=a.assertion_id,
                text=a.text,
                sub_section_id=a.sub_section_id,
                chunk_id=a.chunk_id,
                also_in=a.also_in + dups,
            )
        )
    return tuple(out)


# --------------------------------------------------------------------------- #
# Ledger records (claims deduped for matching — id is a label, not a key)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LedgerRecord:
    """One de-duplicated ledger claim record the diff matches against.

    Real ledgers repeat both ids (unrelated claims sharing ``C01``) and whole
    entries (9 true duplicates in excellence).  Matching therefore treats the
    ledger as a set of ``(claim_summary, status, source_ref)`` records; every
    member entry's disambiguated ``entry_key`` stays attached so no entry is
    lost from reverse-diff accounting.
    """

    claim_summary: str
    status: str
    source_ref: str
    entry_keys: tuple[str, ...]

    @property
    def label(self) -> str:
        """The record's display label — its first member ``entry_key``."""
        return self.entry_keys[0]


def dedup_ledger_claims(claims: Sequence[Any]) -> tuple[LedgerRecord, ...]:
    """Collapse a section's claims into unique records for matching.

    *claims* are :class:`~harness.status_faithfulness.SectionClaim` objects.
    Key: ``(normalized summary, source_ref, status)``.  Order is
    first-occurrence order; all member ``entry_key``\\ s are kept.
    """
    order: list[tuple[str, str, str]] = []
    members: dict[tuple[str, str, str], list[Any]] = {}
    for c in claims:
        key = (normalize_text(c.claim_summary), str(c.source_ref), str(c.status))
        if key not in members:
            members[key] = []
            order.append(key)
        members[key].append(c)
    out: list[LedgerRecord] = []
    for key in order:
        group = members[key]
        out.append(
            LedgerRecord(
                claim_summary=group[0].claim_summary,
                status=group[0].status,
                source_ref=group[0].source_ref,
                entry_keys=tuple(c.entry_key for c in group),
            )
        )
    return tuple(out)


# --------------------------------------------------------------------------- #
# Lexical shortlist (pure, deterministic)
# --------------------------------------------------------------------------- #

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9-]{2,}")

#: High-frequency tokens that carry no matching signal.
_STOPWORDS: frozenset[str] = frozenset(
    """the and for with that this from are was has have will not but its their
    which than then also each between within into over under more most other
    such per via due own two one all any been being does was were""".split()
)


def _tokens(text: str) -> frozenset[str]:
    return frozenset(t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS)


def lexical_shortlist(
    assertion_text: str,
    records: Sequence[LedgerRecord],
    *,
    k: int = DEFAULT_SHORTLIST_K,
) -> tuple[LedgerRecord, ...]:
    """Return the ≤ *k* records lexically nearest to *assertion_text*.

    Pure and deterministic: cosine-style token overlap
    (``|A∩B| / sqrt(|A|·|B|)``), zero-score records dropped, ties broken by
    ledger order.  This is a *recall* device that bounds the judge prompt — the
    semantic call is the judge's; an empty shortlist is recorded as its own
    escape basis precisely because it is the one case where a paraphrase could
    slip past the lexical net.
    """
    a = _tokens(assertion_text)
    if not a or k <= 0:
        return ()
    scored: list[tuple[float, int]] = []
    for i, r in enumerate(records):
        b = _tokens(r.claim_summary)
        if not b:
            continue
        overlap = len(a & b)
        if overlap == 0:
            continue
        scored.append((overlap / (len(a) * len(b)) ** 0.5, i))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return tuple(records[i] for _, i in scored[:k])


# --------------------------------------------------------------------------- #
# Coverage — batched primary, per-candidate escalation
# --------------------------------------------------------------------------- #

_COVERAGE_SYSTEM: str = (
    INDEPENDENCE_PREAMBLE
    + "You are given one ASSERTION extracted from proposal prose, and a "
    "numbered list of CANDIDATE LEDGER CLAIMS from the proposal's own claim "
    "ledger. Decide whether ANY candidate claim COVERS the assertion: a claim "
    "covers the assertion if it states, entails, or clearly subsumes the "
    "assertion's factual content. A claim about a different fact, or one that "
    "only shares vocabulary, does NOT cover it.\n\n"
    "Return ONLY a JSON object, no prose before or after:\n"
    '{"passed": <true if ANY candidate covers the assertion, false otherwise>, '
    '"covered_by": <the covering candidate NUMBER (integer), or null>, '
    '"rationale": "<one sentence>"}\n\n'
    "Identify the candidate by its NUMBER only. When in doubt, answer "
    '"passed": false — an unledgered material assertion must be surfaced.'
)

_PAIR_COVERAGE_SYSTEM: str = (
    INDEPENDENCE_PREAMBLE
    + "You are given one ASSERTION extracted from proposal prose and ONE "
    "LEDGER CLAIM. Decide whether the ledger claim COVERS the assertion: it "
    "covers it if it states, entails, or clearly subsumes the assertion's "
    "factual content. Shared vocabulary alone is not coverage.\n\n"
    "Return ONLY a JSON object, no prose before or after:\n"
    '{"passed": <true if the claim covers the assertion, false otherwise>, '
    '"score": <0.0-1.0 confidence>, "rationale": "<one sentence>"}\n\n'
    'When in doubt, answer "passed": false.'
)


def build_coverage_prompt(
    assertion_text: str, candidates: Sequence[LedgerRecord]
) -> tuple[str, str]:
    """Return the ``(system, user)`` prompts for one batched coverage question.

    Candidates are presented **numbered**; the judge answers with the number.
    The ``entry_key`` label rides along for the human reading provenance, but
    the answer channel is the index — bare claim ids are ambiguous in real
    ledgers (three unrelated ``C01``\\ s) and a model echoing ids is a fragile
    contract.
    """
    if not candidates:
        raise ClaimLedgerError("build_coverage_prompt requires at least one candidate.")
    lines = [
        f"{i + 1}. [{r.label}] ({r.status}) {r.claim_summary}"
        for i, r in enumerate(candidates)
    ]
    user_prompt = (
        f"ASSERTION:\n{assertion_text}\n\n"
        "CANDIDATE LEDGER CLAIMS:\n" + "\n".join(lines) + "\n\n"
        "Does any candidate cover the ASSERTION? Return the JSON verdict."
    )
    return _COVERAGE_SYSTEM, user_prompt


def extract_covered_by(raw: str, n_candidates: int) -> int | None:
    """Extract a valid 1-based ``covered_by`` candidate number from *raw*.

    Returns ``None`` for anything missing, non-integer, or out of range — the
    caller treats that as "coverage asserted but not attributable" and
    escalates; it never guesses a candidate (no silent repair).
    """
    payload = extract_first_json_object(raw)
    if payload is None:
        return None
    value = payload.get("covered_by")
    if isinstance(value, bool):
        return None
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value.strip())
    if isinstance(value, int) and 1 <= value <= n_candidates:
        return value
    return None


def judge_assertion_covered_by(
    judge: Judge,
    assertion: Assertion,
    record: LedgerRecord,
    *,
    n: int = 1,
) -> Verdict | MajorityVerdict:
    """The per-candidate boolean coverage question (the escalation fallback).

    Asks whether one specific ledger record covers the assertion.
    ``passed=True`` = covered.  Also the most unit-testable coverage seam.
    """
    validate_sample_count(n)
    user_prompt = (
        f"ASSERTION:\n{assertion.text}\n\n"
        f"LEDGER CLAIM [{record.label}] ({record.status}):\n{record.claim_summary}\n\n"
        "Does the LEDGER CLAIM cover the ASSERTION? Return the JSON verdict."
    )
    property_key = f"{assertion.assertion_id}~{record.label}"
    if n == 1:
        return judge.evaluate(
            _PAIR_COVERAGE_SYSTEM,
            user_prompt,
            metric=COVERAGE_METRIC,
            property_key=property_key,
        ).verdict
    return judge.evaluate_majority(
        _PAIR_COVERAGE_SYSTEM,
        user_prompt,
        metric=COVERAGE_METRIC,
        property_key=property_key,
        n=n,
    ).majority



@dataclass(frozen=True)
class CoverageOutcome:
    """The matching outcome for one material assertion.

    ``covered`` is the boolean-primary answer.  ``matched`` is the covering
    :class:`LedgerRecord` when attributable.  ``basis`` is one of the
    ``ESCAPE_*`` constants when not covered (``None`` when covered).
    ``escalated`` marks that the per-candidate fallback ran.
    """

    covered: bool
    matched: LedgerRecord | None
    verdict: Verdict | MajorityVerdict | None
    basis: str | None
    escalated: bool = False


def _covered_by_from_result(
    result: JudgeResult | MajorityJudgeResult, n: int, n_candidates: int
) -> int | None:
    """Pull the modal valid ``covered_by`` out of a single or majority result."""
    if n == 1:
        return extract_covered_by(result.raw_response, n_candidates)
    counts: dict[int, int] = {}
    for member, raw in zip(result.majority.members, result.raw_responses):
        if member.passed is not True:
            continue
        idx = extract_covered_by(raw, n_candidates)
        if idx is not None:
            counts[idx] = counts.get(idx, 0) + 1
    if not counts:
        return None
    # Modal value; ties break to the smallest candidate number (deterministic).
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def match_assertion(
    judge: Judge,
    assertion: Assertion,
    records: Sequence[LedgerRecord],
    *,
    shortlist_k: int = DEFAULT_SHORTLIST_K,
    n: int = 1,
) -> CoverageOutcome:
    """Match one material assertion against the ledger records.

    Deterministic shortlist → one batched judge call → (only if the judge says
    "covered" but names no valid candidate) per-candidate escalation.  If the
    escalation confirms no candidate either, the stricter question governs and
    the assertion is treated as uncovered — with the disagreement recorded in
    the basis (:data:`ESCAPE_ESCALATION_UNCONFIRMED`), never silently resolved.
    """
    validate_sample_count(n)
    candidates = lexical_shortlist(assertion.text, records, k=shortlist_k)
    if not candidates:
        return CoverageOutcome(
            covered=False,
            matched=None,
            verdict=None,
            basis=ESCAPE_NO_LEXICAL_CANDIDATES,
        )

    system_prompt, user_prompt = build_coverage_prompt(assertion.text, candidates)
    if n == 1:
        result: JudgeResult | MajorityJudgeResult = judge.evaluate(
            system_prompt,
            user_prompt,
            metric=COVERAGE_METRIC,
            property_key=assertion.assertion_id,
        )
        verdict: Verdict | MajorityVerdict = result.verdict
    else:
        result = judge.evaluate_majority(
            system_prompt,
            user_prompt,
            metric=COVERAGE_METRIC,
            property_key=assertion.assertion_id,
            n=n,
        )
        verdict = result.majority

    if verdict.passed is not True:
        return CoverageOutcome(
            covered=False,
            matched=None,
            verdict=verdict,
            basis=ESCAPE_JUDGED_UNCOVERED,
        )

    idx = _covered_by_from_result(result, n, len(candidates))
    if idx is not None:
        return CoverageOutcome(
            covered=True, matched=candidates[idx - 1], verdict=verdict, basis=None
        )

    # Covered-but-unattributable: escalate to the stricter per-candidate
    # question. First candidate to pass wins; none passing means the batched
    # "covered" cannot be substantiated — treated as uncovered, loudly.
    for cand in candidates:
        cand_verdict = judge_assertion_covered_by(judge, assertion, cand, n=n)
        if cand_verdict.passed is True:
            return CoverageOutcome(
                covered=True,
                matched=cand,
                verdict=cand_verdict,
                basis=None,
                escalated=True,
            )
    return CoverageOutcome(
        covered=False,
        matched=None,
        verdict=verdict,
        basis=ESCAPE_ESCALATION_UNCONFIRMED,
        escalated=True,
    )


# --------------------------------------------------------------------------- #
# Findings + result
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class AssertionFinding:
    """The completeness outcome for one (deduped) prose assertion.

    Attributes
    ----------
    assertion:
        The judged :class:`Assertion` (id, text, origin chunk(s)).
    outcome:
        One of the ``OUTCOME_*`` constants; ``escaped`` is the hard finding.
    material:
        The materiality boolean, or ``None`` when the assertion never reached
        (or could not complete) classification.
    materiality_verdict, coverage_verdict:
        The underlying judge verdicts for each stage, where that stage ran.
    matched_entry_key:
        The covering ledger record's disambiguated label, when covered.
    escape_basis:
        For an escaped assertion, one of the ``ESCAPE_*`` constants — why no
        cover was found (shortlist miss vs judged vs unconfirmed escalation).
    escalated:
        ``True`` when the per-candidate fallback ran after a batched
        covered-but-unattributable verdict.
    reason:
        Human-readable explanation, especially for the un-judged cases.
    """

    assertion: Assertion
    outcome: str
    material: bool | None = None
    materiality_verdict: Verdict | MajorityVerdict | None = None
    coverage_verdict: Verdict | MajorityVerdict | None = None
    matched_entry_key: str | None = None
    escape_basis: str | None = None
    escalated: bool = False
    reason: str = ""

    @property
    def is_hard_finding(self) -> bool:
        """``True`` for an escaped claim — a material assertion with no ledger cover."""
        return self.outcome == OUTCOME_ESCAPED

    @property
    def flagged(self) -> bool:
        """``True`` when a human should look (escaped or unjudgeable)."""
        return self.outcome in (OUTCOME_ESCAPED, OUTCOME_UNJUDGEABLE)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assertion_id": self.assertion.assertion_id,
            "text": self.assertion.text,
            "sub_section_id": self.assertion.sub_section_id,
            "chunk_id": self.assertion.chunk_id,
            "also_in": list(self.assertion.also_in),
            "outcome": self.outcome,
            "material": self.material,
            "matched_entry_key": self.matched_entry_key,
            "escape_basis": self.escape_basis,
            "escalated": self.escalated,
            "is_hard_finding": self.is_hard_finding,
            "flagged": self.flagged,
            "reason": self.reason,
            "materiality_verdict": (
                self.materiality_verdict.to_dict() if self.materiality_verdict else None
            ),
            "coverage_verdict": (
                self.coverage_verdict.to_dict() if self.coverage_verdict else None
            ),
        }


@dataclass(frozen=True)
class ChunkFailure:
    """A chunk whose decomposition failed — surfaced, never dropped."""

    chunk_id: str
    error: str

    def to_dict(self) -> dict[str, Any]:
        return {"chunk_id": self.chunk_id, "error": self.error}


@dataclass(frozen=True)
class LedgerCompletenessResult:
    """The whole-section claim-ledger completeness outcome (reporting-only)."""

    section_id: str
    findings: tuple[AssertionFinding, ...]
    chunk_failures: tuple[ChunkFailure, ...] = ()
    zero_assertion_chunk_ids: tuple[str, ...] = ()
    unreferenced_record_labels: tuple[str, ...] = ()
    routing: tuple[RoutingDecision, ...] = ()
    judge_model: str | None = None
    judge_version: str | None = None
    materiality_calibration: MaterialityCalibration | None = None

    def escaped(self) -> tuple[AssertionFinding, ...]:
        """The hard findings — material assertions no ledger record covers."""
        return tuple(f for f in self.findings if f.outcome == OUTCOME_ESCAPED)

    def covered(self) -> tuple[AssertionFinding, ...]:
        return tuple(f for f in self.findings if f.outcome == OUTCOME_COVERED)

    def non_material(self) -> tuple[AssertionFinding, ...]:
        return tuple(f for f in self.findings if f.outcome == OUTCOME_NON_MATERIAL)

    def unjudgeable(self) -> tuple[AssertionFinding, ...]:
        return tuple(f for f in self.findings if f.outcome == OUTCOME_UNJUDGEABLE)

    @property
    def outcome_counts(self) -> dict[str, int]:
        counts = {
            OUTCOME_COVERED: 0,
            OUTCOME_ESCAPED: 0,
            OUTCOME_NON_MATERIAL: 0,
            OUTCOME_UNJUDGEABLE: 0,
        }
        for f in self.findings:
            counts[f.outcome] = counts.get(f.outcome, 0) + 1
        return counts

    def _materiality_note(self) -> str:
        """One line stating how much the non-material exclusions can be trusted."""
        cal = self.materiality_calibration
        if cal is None:
            return "materiality classifier UNCALIBRATED (no calibration supplied)"
        if self.judge_model is not None and (
            cal.judge_model != self.judge_model
            or cal.judge_version != self.judge_version
        ):
            return (
                f"materiality calibration is for {cal.judge_model}@{cal.judge_version} "
                f"— repinned judge, treat as uncalibrated"
            )
        if not cal.has_negatives:
            return (
                f"materiality classifier partially calibrated: recall={cal.recall} "
                f"on ledger positives; precision unmeasured (0 labeled negatives)"
            )
        return (
            f"materiality classifier calibrated: recall={cal.recall}, "
            f"precision={cal.precision} ({cal.labeled_negatives} labeled negatives)"
        )

    def _outcome_verdict(self, f: AssertionFinding) -> Verdict:
        """One derived, per-assertion verdict for the report's tallies.

        Raw stage verdicts would misrepresent the headline signal in
        ``HarnessReport.summary``: a ``no_lexical_candidates`` escape has *no*
        coverage verdict at all, and an ``escalation_unconfirmed`` escape's
        batched verdict says ``passed=True`` — both would count a hard finding
        as absent or passed.  So the report carries one verdict per assertion
        stating the E3 *outcome*: ``passed=False`` iff the assertion escaped,
        ``True`` when covered, ``None`` (inconclusive) for non-material /
        unjudgeable.  Still typed ``Inferred`` — it is derived from judge
        opinions; the underlying stage verdicts stay on the finding and in
        provenance.
        """
        if f.outcome == OUTCOME_COVERED:
            passed: bool | None = True
            why = f"covered by {f.matched_entry_key}"
        elif f.outcome == OUTCOME_ESCAPED:
            passed = False
            why = f"ESCAPED ({f.escape_basis})"
        else:
            passed = None
            why = f"{f.outcome}: {f.reason}"
        return Verdict(
            metric=CLAIM_LEDGER_METRIC,
            property_key=f.assertion.assertion_id,
            passed=passed,
            rationale=why,
        )

    def build_report(self) -> HarnessReport:
        """Assemble the advisory report — ``blocking=False`` by construction.

        ``findings`` are the derived per-assertion outcome verdicts (see
        :meth:`_outcome_verdict`), so the report ``summary`` reads
        ``failed == escaped`` exactly.
        """
        verdicts = [self._outcome_verdict(f) for f in self.findings]
        counts = self.outcome_counts
        notes = (
            f"section={self.section_id}; assertions={len(self.findings)}; "
            f"ESCAPED={counts[OUTCOME_ESCAPED]} (hard: unledgered material "
            f"assertions, CLAUDE.md §10.5); covered={counts[OUTCOME_COVERED]}; "
            f"non_material={counts[OUTCOME_NON_MATERIAL]}; "
            f"unjudgeable={counts[OUTCOME_UNJUDGEABLE]}; "
            f"chunk_failures={len(self.chunk_failures)}; "
            f"zero_assertion_chunks={len(self.zero_assertion_chunk_ids)}; "
            f"unreferenced_ledger_records={len(self.unreferenced_record_labels)}. "
            f"{self._materiality_note()}. "
            "Advisory only — never a runtime gate (see harness/HARNESS.md)."
        )
        return build_report(
            CLAIM_LEDGER_METRIC,
            verdicts,
            routing=self.routing,
            notes=notes,
            judge_model=self.judge_model,
            judge_version=self.judge_version,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "claim_ledger_completeness_result",
            "metric": CLAIM_LEDGER_METRIC,
            "section_id": self.section_id,
            "judge_model": self.judge_model,
            "judge_version": self.judge_version,
            "outcome_counts": self.outcome_counts,
            "escaped_assertion_ids": [f.assertion.assertion_id for f in self.escaped()],
            "zero_assertion_chunk_ids": list(self.zero_assertion_chunk_ids),
            "unreferenced_record_labels": list(self.unreferenced_record_labels),
            "chunk_failures": [c.to_dict() for c in self.chunk_failures],
            "materiality_calibration": (
                self.materiality_calibration.to_dict()
                if self.materiality_calibration
                else None
            ),
            "findings": [f.to_dict() for f in self.findings],
        }


# --------------------------------------------------------------------------- #
# The pipeline
# --------------------------------------------------------------------------- #


def evaluate_ledger_completeness(
    prose: Sequence[SubSectionProse],
    claims: Sequence[Any],
    judge: Judge,
    *,
    section_id: str = "",
    n: int = 1,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
    shortlist_k: int = DEFAULT_SHORTLIST_K,
    materiality_calibration: MaterialityCalibration | None = None,
    provenance_log: ProvenanceLog | None = None,
    clock: Callable[[], str] | None = None,
    decomposer: Decomposer | None = None,
    materiality_classifier: MaterialityClassifier | None = None,
    sub_section_filter: Callable[[SubSectionProse], bool] | None = None,
) -> LedgerCompletenessResult:
    """Run the escaped-claim diff over a section's prose and claim ledger.

    Chunks the prose, decomposes each chunk (default: the judge; injectable
    *decomposer* for tests), de-duplicates assertions, classifies materiality
    (default: :func:`~harness.materiality.classify_materiality`; injectable),
    and matches each material assertion against the de-duplicated ledger
    records.  Every assertion is routed through
    :func:`~harness.routing.assert_judgeable` once.

    Per-assertion/per-chunk judge failures are **surfaced as findings**, not
    propagated (see the module docstring for why this batch metric diverges
    from E2 there).  Reporting-only; performs zero DAG runs.
    """
    validate_sample_count(n)
    records = dedup_ledger_claims(claims)

    def default_decomposer(chunk: ProseChunk) -> tuple[str, ...]:
        return decompose_chunk(
            judge, chunk, provenance_log=provenance_log, clock=clock
        )

    def default_classifier(text: str, property_key: str) -> Verdict | MajorityVerdict:
        return classify_materiality(judge, text, property_key=property_key, n=n)

    decompose = decomposer or default_decomposer
    classify = materiality_classifier or default_classifier

    # 1. Chunk + decompose (chunk failures surfaced, never dropped).
    raw_assertions: list[Assertion] = []
    chunk_failures: list[ChunkFailure] = []
    zero_chunks: list[str] = []
    selected = [
        s for s in prose if (sub_section_filter is None or sub_section_filter(s))
    ]
    for sub in selected:
        for chunk in chunk_prose(sub, max_chars=max_chunk_chars):
            prefix = f"{section_id}:{chunk.chunk_id}" if section_id else chunk.chunk_id
            try:
                texts = tuple(decompose(chunk))
            except (ClaimLedgerError, JudgeResponseError) as exc:
                chunk_failures.append(ChunkFailure(chunk_id=prefix, error=str(exc)))
                continue
            if not texts and len(chunk.text) >= ZERO_ASSERTION_FLOOR_CHARS:
                zero_chunks.append(prefix)
            for j, text in enumerate(texts):
                raw_assertions.append(
                    Assertion(
                        assertion_id=f"{prefix}:a{j:02d}",
                        text=text,
                        sub_section_id=sub.sub_section_id,
                        chunk_id=prefix,
                    )
                )
    assertions = dedup_assertions(raw_assertions)

    # 2. Classify materiality + 3. match against the ledger.
    findings: list[AssertionFinding] = []
    routing: list[RoutingDecision] = []
    matched_labels: set[str] = set()
    for assertion in assertions:
        routing.append(assert_judgeable(assertion.assertion_id))

        try:
            m_verdict = classify(assertion.text, assertion.assertion_id)
        except JudgeResponseError as exc:
            findings.append(
                AssertionFinding(
                    assertion=assertion,
                    outcome=OUTCOME_UNJUDGEABLE,
                    reason=f"materiality classification failed: {exc}",
                )
            )
            continue
        if m_verdict.passed is None:
            findings.append(
                AssertionFinding(
                    assertion=assertion,
                    outcome=OUTCOME_UNJUDGEABLE,
                    materiality_verdict=m_verdict,
                    reason="materiality classifier returned no boolean verdict.",
                )
            )
            continue
        if m_verdict.passed is False:
            findings.append(
                AssertionFinding(
                    assertion=assertion,
                    outcome=OUTCOME_NON_MATERIAL,
                    material=False,
                    materiality_verdict=m_verdict,
                    reason="below the §10.5 materiality bar — excluded from the diff.",
                )
            )
            continue

        try:
            outcome = match_assertion(
                judge, assertion, records, shortlist_k=shortlist_k, n=n
            )
        except JudgeResponseError as exc:
            findings.append(
                AssertionFinding(
                    assertion=assertion,
                    outcome=OUTCOME_UNJUDGEABLE,
                    material=True,
                    materiality_verdict=m_verdict,
                    reason=f"coverage matching failed: {exc}",
                )
            )
            continue

        if outcome.covered and outcome.matched is not None:
            matched_labels.add(outcome.matched.label)
            findings.append(
                AssertionFinding(
                    assertion=assertion,
                    outcome=OUTCOME_COVERED,
                    material=True,
                    materiality_verdict=m_verdict,
                    coverage_verdict=outcome.verdict,
                    matched_entry_key=outcome.matched.label,
                    escalated=outcome.escalated,
                    reason="covered by a ledger claim.",
                )
            )
        else:
            findings.append(
                AssertionFinding(
                    assertion=assertion,
                    outcome=OUTCOME_ESCAPED,
                    material=True,
                    materiality_verdict=m_verdict,
                    coverage_verdict=outcome.verdict,
                    escape_basis=outcome.basis,
                    escalated=outcome.escalated,
                    reason=(
                        "material assertion with no covering ledger claim — an "
                        "unattributed claim per CLAUDE.md §10.5."
                    ),
                )
            )

    unreferenced = tuple(
        r.label for r in records if r.label not in matched_labels
    )
    return LedgerCompletenessResult(
        section_id=section_id,
        findings=tuple(findings),
        chunk_failures=tuple(chunk_failures),
        zero_assertion_chunk_ids=tuple(zero_chunks),
        unreferenced_record_labels=unreferenced,
        routing=tuple(routing),
        judge_model=judge.config.model,
        judge_version=judge.config.version,
        materiality_calibration=materiality_calibration,
    )
