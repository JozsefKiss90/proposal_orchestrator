"""
Status-aware faithfulness — the "gap masked as confirmed" detector (E2).

Headline integrity signal #1.  The pipeline stamps every Tier-5 claim with a
``status`` (``confirmed`` / ``inferred`` / ``assumed``) and a ``source_ref``, and
a deterministic predicate can check that a ``source_ref`` field is *non-blank*.
No predicate can check the thing that actually matters: whether the cited source
genuinely **supports** the sentence it is cited for.  A ``confirmed`` claim whose
own source does not support it is a *gap masked as confirmed* — the exact threat
the strategy (§1/§2) says the same-model-family in-run reviewer cannot be trusted
to catch alone.  This module is that missing check, run by the independent,
out-of-band judge.

It is not one metric but three, partitioned by the engine's own ``status`` —
because the standard of faithfulness differs by what the status *claims*:

* ``confirmed`` → judged **strictly** against its ``source_ref``.  A confirmed
  claim must be directly evidenced (faithfulness ≈ 1.0); an unsupported one is a
  **hard integrity finding** (:data:`SEVERITY_INTEGRITY`).
* ``assumed`` → judged against the **operator-declared value** in
  ``working_assumptions.json``, *not* the source (an assumption has no source to
  cite — it was consciously declared).  This complements the W1 predicate, which
  checks the declaration *exists*: E2 checks the claim faithfully represents its
  *content*.  A mismatch is content drift (:data:`SEVERITY_CONTENT_DRIFT`).
* ``inferred`` → judged as **framing / synthesis** against its source under a
  **softer** bar: a faithful inference need not be verbatim, but it must be
  grounded in and not contradicted by the source.  A failure is a soft concern
  (:data:`SEVERITY_SOFT`), not a hard finding.

Everything here stands on the E1/E1.5 substrate and adds no framework
dependency: it reuses :class:`~harness.judge.Judge` (pinned, non-drafter,
provenance-logged), :func:`~harness.routing.assert_judgeable` (a green judge
never overrides a red predicate), :class:`~harness.verdict.Verdict` (typed
``Inferred``, never ``Confirmed``), and :func:`~harness.report.build_report`
(``advisory=True, blocking=False`` by construction).  It extends E1.5's atomic
faithfulness question with the status partitioning E1.5 deliberately left to E2.

**M3 reuse.**  The Milestone-3 composition pass rewrites each section's prose
while carrying ``claim_statuses`` / ``source_ref`` forward verbatim.  Its risk is
not a wrong token (structural detectors catch that) but a composer that keeps
every canonical token while subtly *weakening the grounding* of a ``confirmed``
claim.  :func:`freeze_baseline` snapshots the per-claim grounding verdict on the
pre-composition ledger; :func:`compare_to_baseline` re-runs on the composed
output and flags any claim whose grounding **weakened** — *form may change,
grounding may not.*

Reporting-only; zero DAG runs.  Built against the current
``docs/tier5_deliverables/proposal_sections/*_section.json`` and re-points at
M2-T10's graph-sourced artifacts unchanged (the claim schema is identical).

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate; reads Tier-5 sections
    and the Tier-3 declaration file only to *judge* them, and writes only
    harness-owned report/baseline files.  Never a runtime gate.  See
    ``harness/HARNESS.md``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from runner.atomic_write import atomic_write_json
from runner.paths import resolve_repo_path
from runner.working_assumptions import (
    WorkingAssumptions,
    declared_claim_summary,
)
from harness.faithfulness import INDEPENDENCE_PREAMBLE, build_claim_user_prompt
from harness.judge import Judge, MajorityJudgeResult
from harness.report import HarnessReport, build_report
from harness.routing import RoutingDecision, assert_judgeable
from harness.verdict import (
    MIN_MAJORITY_SAMPLES,
    MajorityVerdict,
    Verdict,
    validate_sample_count,
)

__all__ = [
    "STATUS_AWARE_FAITHFULNESS_METRIC",
    "STATUS_CONFIRMED",
    "STATUS_INFERRED",
    "STATUS_ASSUMED",
    "COMPARISON_SOURCE",
    "COMPARISON_DECLARED_VALUE",
    "SEVERITY_NONE",
    "SEVERITY_SOFT",
    "SEVERITY_CONTENT_DRIFT",
    "SEVERITY_INTEGRITY",
    "SEVERITY_UNRESOLVED",
    "SEVERITY_UNKNOWN_STATUS",
    "DEFAULT_MAX_SOURCE_CHARS",
    "StatusFaithfulnessError",
    "SourceResolutionError",
    "entry_key_for",
    "SectionClaim",
    "StatusPolicy",
    "DEFAULT_POLICIES",
    "ClaimFaithfulness",
    "StatusFaithfulnessResult",
    "load_section_claims",
    "resolve_claim_source_text",
    "resolve_assumed_declared_text",
    "build_faithfulness_prompt_for_status",
    "meets_bar",
    "classify_severity",
    "evaluate_claim",
    "evaluate_status_aware_faithfulness",
    # M3 reuse — per-claim grounding baseline + invariance
    "FaithfulnessBaseline",
    "ClaimGroundingSnapshot",
    "InvarianceViolation",
    "InvarianceReport",
    "DEFAULT_SCORE_DROP_TOLERANCE",
    "VIOLATION_DROPPED",
    "VIOLATION_STATUS_CHANGED",
    "VIOLATION_BAR_REGRESSION",
    "VIOLATION_SCORE_DROP",
    "freeze_baseline",
    "compare_to_baseline",
    "write_baseline",
    "load_baseline",
]

#: The metric name stamped on every status-aware-faithfulness verdict.
STATUS_AWARE_FAITHFULNESS_METRIC: str = "status_aware_faithfulness"

# --------------------------------------------------------------------------- #
# Status + comparison + severity vocabulary
# --------------------------------------------------------------------------- #

#: Engine claim statuses (CLAUDE.md §12.2, lowercased as they appear in
#: ``claim_statuses``).  ``unresolved`` is deliberately absent — an unresolved
#: claim never reaches a finalized Tier-5 section (it blocks), so E2 partitions
#: only the three statuses that *do* appear in drafted prose.
STATUS_CONFIRMED: str = "confirmed"
STATUS_INFERRED: str = "inferred"
STATUS_ASSUMED: str = "assumed"

#: What a claim's faithfulness is judged *against*.
COMPARISON_SOURCE: str = "source"
COMPARISON_DECLARED_VALUE: str = "declared_value"

#: Per-claim severity — ``none`` means the claim met its status bar.
SEVERITY_NONE: str = "none"
#: An ``inferred`` claim below the soft grounding bar (a soft concern).
SEVERITY_SOFT: str = "soft"
#: An ``assumed`` claim that does not match its operator-declared value.
SEVERITY_CONTENT_DRIFT: str = "content_drift"
#: A ``confirmed`` claim its own ``source_ref`` does not support — the headline
#: "gap masked as confirmed" (a hard integrity finding).
SEVERITY_INTEGRITY: str = "integrity"
#: The comparison target could not be resolved (source file missing, or an
#: ``assumed`` claim with no matching declaration) — cannot verify, so flag it.
SEVERITY_UNRESOLVED: str = "unresolved"
#: A claim carrying a status E2 does not partition (surfaced, not judged).
SEVERITY_UNKNOWN_STATUS: str = "unknown_status"

#: The severities that constitute a flag a human should review.
_FLAGGED_SEVERITIES: frozenset[str] = frozenset(
    {
        SEVERITY_SOFT,
        SEVERITY_CONTENT_DRIFT,
        SEVERITY_INTEGRITY,
        SEVERITY_UNRESOLVED,
        SEVERITY_UNKNOWN_STATUS,
    }
)

#: The hard-finding severities (grounding actually failed, not just unverifiable
#: or a soft concern) — used by the M3 invariance check and by
#: :meth:`StatusFaithfulnessResult.integrity_findings`.
_HARD_SEVERITIES: frozenset[str] = frozenset(
    {SEVERITY_INTEGRITY, SEVERITY_CONTENT_DRIFT}
)


class StatusFaithfulnessError(Exception):
    """A section artifact is malformed, or a metric input is inconsistent."""


class SourceResolutionError(StatusFaithfulnessError):
    """A claim's ``source_ref`` could not be resolved to a source passage."""


# --------------------------------------------------------------------------- #
# Section claim model
# --------------------------------------------------------------------------- #


def entry_key_for(claim_id: str, entry_index: int | None) -> str:
    """The one rendering of a claim's disambiguated identity (``C01#171``).

    Real ledgers repeat ``claim_id`` across independently-numbered drafting
    blocks, so the bare id is a display label, not a key; the entry index is
    what makes a claim addressable.  ``None`` (a claim built outside a ledger)
    falls back to the bare id.  Every ``entry_key`` property across the
    harness (:class:`SectionClaim`, :class:`ClaimFaithfulness`,
    :class:`ClaimGroundingSnapshot`, E3's drift rows) delegates here so the
    format cannot drift.
    """
    if entry_index is None:
        return claim_id
    return f"{claim_id}#{entry_index}"


@dataclass(frozen=True)
class SectionClaim:
    """One entry of a section's ``validation_status.claim_statuses`` array.

    Attributes
    ----------
    claim_id:
        Stable claim identifier (e.g. ``C01``, ``FELLOW``, ``IMP-1``).
    claim_summary:
        The engine's own one-line statement of the claim — the text E2 judges
        for faithfulness against the claim's comparison target.
    status:
        The engine status (:data:`STATUS_CONFIRMED` / :data:`STATUS_INFERRED` /
        :data:`STATUS_ASSUMED`), lowercased.
    source_ref:
        The path (optionally ``…#fragment``, optionally with a trailing
        parenthetical annotation) the engine cited as the claim's provenance.
    entry_index:
        Position of this entry within the section's ``claim_statuses`` array.
        Real ledgers concatenate independently-numbered drafting blocks, so
        ``claim_id`` is **not unique** (excellence: 191 entries / 128 unique
        ids; three unrelated ``C01``\\ s) — the entry index is what makes a
        claim addressable.  ``None`` for a claim constructed outside a ledger.
    """

    claim_id: str
    claim_summary: str
    status: str
    source_ref: str
    entry_index: int | None = None

    def __post_init__(self) -> None:
        if not str(self.claim_id).strip():
            raise StatusFaithfulnessError("SectionClaim.claim_id must be non-empty.")
        if not str(self.claim_summary).strip():
            raise StatusFaithfulnessError(
                f"SectionClaim {self.claim_id!r}: claim_summary must be non-empty."
            )

    @property
    def entry_key(self) -> str:
        """The disambiguated identity: ``claim_id`` alone, or ``C01#7`` with an index.

        Used as the judge ``property_key``, in ``hard_finding_ids``, and as the
        baseline key — so a finding on one of several same-id claims names
        exactly which entry it concerns.
        """
        return entry_key_for(self.claim_id, self.entry_index)

    @classmethod
    def from_dict(
        cls, d: Mapping[str, Any], *, entry_index: int | None = None
    ) -> "SectionClaim":
        if not isinstance(d, Mapping):
            raise StatusFaithfulnessError(
                f"claim entry must be an object; got {type(d).__name__}"
            )
        return cls(
            claim_id=str(d.get("claim_id", "")),
            claim_summary=str(d.get("claim_summary", "")),
            status=str(d.get("status", "")).strip().lower(),
            source_ref=str(d.get("source_ref", "")),
            entry_index=entry_index,
        )


def load_section_claims(path: Path | str) -> tuple[SectionClaim, ...]:
    """Load the ``claim_statuses`` of a Phase-8 section JSON into claim objects.

    Reads ``validation_status.claim_statuses`` and returns one
    :class:`SectionClaim` per entry, preserving order.  Raises
    :class:`StatusFaithfulnessError` on a missing file or an absent /
    non-array ``claim_statuses`` — E2 has nothing to judge without it.
    """
    p = Path(path)
    if not p.is_file():
        raise StatusFaithfulnessError(f"section file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise StatusFaithfulnessError(f"section {p} is not valid JSON: {exc}") from exc
    vs = data.get("validation_status") if isinstance(data, Mapping) else None
    claim_statuses = vs.get("claim_statuses") if isinstance(vs, Mapping) else None
    if not isinstance(claim_statuses, list):
        raise StatusFaithfulnessError(
            f"section {p} has no validation_status.claim_statuses array to judge."
        )
    return tuple(
        SectionClaim.from_dict(c, entry_index=i) for i, c in enumerate(claim_statuses)
    )


# --------------------------------------------------------------------------- #
# Status policy — the per-status bar
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class StatusPolicy:
    """The faithfulness bar and comparison target for one claim status.

    Attributes
    ----------
    status:
        The status this policy governs.
    comparison:
        :data:`COMPARISON_SOURCE` (judge against ``source_ref``) or
        :data:`COMPARISON_DECLARED_VALUE` (judge against the operator-declared
        value in ``working_assumptions.json``).
    min_score:
        Advisory score bar in ``[0, 1]``.  Only consulted when the judge returns
        a numeric ``score``; the primary signal is always the boolean ``passed``.
    strict:
        ``True`` (``confirmed`` / ``assumed``) — the claim must be *solidly*
        supported: ``passed`` must be ``True`` **and** any score must clear
        ``min_score``.  ``False`` (``inferred``) — the softer bar: ``passed``
        ``True`` **or** a score clearing ``min_score`` suffices.
    fail_severity:
        The severity assigned when the bar is not met
        (:data:`SEVERITY_INTEGRITY` / :data:`SEVERITY_CONTENT_DRIFT` /
        :data:`SEVERITY_SOFT`).
    """

    status: str
    comparison: str
    min_score: float
    strict: bool
    fail_severity: str

    def __post_init__(self) -> None:
        if not (0.0 <= float(self.min_score) <= 1.0):
            raise ValueError(
                f"StatusPolicy.min_score must lie in [0.0, 1.0]; got {self.min_score!r}."
            )


#: The default per-status bars.  These are **operator policy**, not physics: the
#: ``confirmed`` bar is deliberately strict (a confirmed claim carries the
#: strongest evidential promise), the ``inferred`` bar deliberately soft (framing
#: is legitimate), and ``assumed`` is judged against the declared value.  Tune
#: ``min_score`` to your own cost of a blessed gap vs an over-flag.
DEFAULT_POLICIES: dict[str, StatusPolicy] = {
    STATUS_CONFIRMED: StatusPolicy(
        status=STATUS_CONFIRMED,
        comparison=COMPARISON_SOURCE,
        min_score=0.90,
        strict=True,
        fail_severity=SEVERITY_INTEGRITY,
    ),
    STATUS_INFERRED: StatusPolicy(
        status=STATUS_INFERRED,
        comparison=COMPARISON_SOURCE,
        min_score=0.50,
        strict=False,
        fail_severity=SEVERITY_SOFT,
    ),
    STATUS_ASSUMED: StatusPolicy(
        status=STATUS_ASSUMED,
        comparison=COMPARISON_DECLARED_VALUE,
        min_score=0.90,
        strict=True,
        fail_severity=SEVERITY_CONTENT_DRIFT,
    ),
}


# --------------------------------------------------------------------------- #
# Prompts — status-specific standards, one independent judge
# --------------------------------------------------------------------------- #

_JSON_INSTRUCTION: str = (
    "\n\nReturn ONLY a JSON object, no prose before or after:\n"
    '{"passed": <true if the claim meets the standard above, false otherwise>, '
    '"score": <0.0–1.0 strength of grounding>, '
    '"rationale": "<one sentence citing the decisive part of the material>"}'
)

_CONFIRMED_STANDARD: str = (
    "The engine stamped this claim CONFIRMED — it asserts the claim is directly "
    "evidenced by the SOURCE it cites. Judge STRICTLY: the source supports the "
    "claim only if it states the claim or clearly entails it. Do not give a "
    'confirmed claim the benefit of the doubt. If the source is silent, '
    "contradicts the claim, or only loosely relates to it, the claim is NOT "
    "supported — a confirmed-but-unsupported claim is an integrity defect. When "
    'in doubt, answer "passed": false.'
)

_INFERRED_STANDARD: str = (
    "The engine stamped this claim INFERRED — derived by reasoning, synthesis, or "
    "framing from confirmed evidence, and NOT necessarily stated verbatim in the "
    "SOURCE. Judge with a SOFTER standard: the claim is faithful if it is a "
    "reasonable synthesis or framing that is grounded in and not contradicted by "
    "the source. A faithful inference need not appear word-for-word, but it must "
    "not introduce facts the source cannot support, nor contradict the source. "
    'Answer "passed": true if it is a faithful inference/framing; set score to '
    "the strength of its grounding."
)

_ASSUMED_STANDARD: str = (
    "The engine stamped this claim ASSUMED — it was adopted from an explicit "
    "operator DECLARATION, not from a source document. You are given the DECLARED "
    "VALUE. Judge whether the CLAIM faithfully represents that declared value: "
    "the same fact, neither exaggerated, narrowed, nor altered. (A separate "
    "deterministic check already confirmed the declaration EXISTS; your job is "
    'only whether the claim matches its CONTENT.) Answer "passed": true iff the '
    "claim faithfully represents the declared value."
)

_STANDARD_BY_STATUS: dict[str, str] = {
    STATUS_CONFIRMED: _CONFIRMED_STANDARD,
    STATUS_INFERRED: _INFERRED_STANDARD,
    STATUS_ASSUMED: _ASSUMED_STANDARD,
}


def build_faithfulness_prompt_for_status(
    status: str,
    claim: str,
    comparison_text: str,
    *,
    comparison: str,
    source_ref: str | None = None,
) -> tuple[str, str]:
    """Return the ``(system_prompt, user_prompt)`` for a status-specific judgment.

    The system prompt carries the independence framing, the status-specific
    standard, and the JSON-only instruction; the user prompt carries the claim
    and the material to judge it against — labelled ``SOURCE PASSAGE`` for a
    source comparison or ``DECLARED VALUE`` for an assumed-claim comparison.
    """
    standard = _STANDARD_BY_STATUS.get(status)
    if standard is None:
        raise StatusFaithfulnessError(
            f"no faithfulness standard for status {status!r}; "
            f"expected one of {sorted(_STANDARD_BY_STATUS)}."
        )
    system_prompt = INDEPENDENCE_PREAMBLE + standard + _JSON_INSTRUCTION

    is_declared = comparison == COMPARISON_DECLARED_VALUE
    user_prompt = build_claim_user_prompt(
        claim,
        comparison_text,
        question="Does the CLAIM meet the standard? Return the JSON verdict.",
        material_label="DECLARED VALUE" if is_declared else "SOURCE PASSAGE",
        # A declared value has no source-ref line — the ref labels a source only.
        source_ref=None if is_declared else source_ref,
    )
    return system_prompt, user_prompt


# --------------------------------------------------------------------------- #
# Comparison-target resolution
# --------------------------------------------------------------------------- #

#: Default cap on resolved source text, so a whole-file fallback cannot blow the
#: judge prompt.  Set well above the largest real Tier-3 source (the whole
#: ``confirmation_checklist.json`` renders to ~6.5 KB) so the common
#: no-fragment, whole-file cite is *not* truncated — silent truncation could drop
#: the very sentence that grounds a ``confirmed`` claim and manufacture a false
#: ``SEVERITY_INTEGRITY`` finding on the headline signal.  When a source genuinely
#: exceeds the cap, truncation is made **loud** (:data:`_TRUNCATION_MARKER`), never
#: silent — so a downstream finding on a truncated source is legible as such.
DEFAULT_MAX_SOURCE_CHARS: int = 40000

#: Appended when resolved source text is truncated, so the cut is visible to the
#: judge and in provenance (never a silent evidence drop).
_TRUNCATION_MARKER: str = "\n\n[…SOURCE TRUNCATED at {cap} chars; {omitted} char(s) omitted…]"

_ANNOTATION_RE = re.compile(r"\s*\([^()]*\)\s*$")


def _bounded(text: str, max_chars: int) -> str:
    """Return *text* capped at *max_chars*, appending a loud marker if it was cut."""
    if len(text) <= max_chars:
        return text
    omitted = len(text) - max_chars
    return text[:max_chars] + _TRUNCATION_MARKER.format(cap=max_chars, omitted=omitted)


#: A repo-relative source path: ``docs/…`` up to an extension, with an optional
#: ``#fragment``.  Extracting the path by shape is more robust than stripping a
#: trailing annotation, because real refs trail freeform prose after the path
#: (``… (hint) — a paragraph of explanation``) and carry nested-paren hints.
_PATH_RE = re.compile(r"(docs/[^\s()#]+\.[A-Za-z0-9]+)(?:#(\S+))?")


def _leading_parenthetical(text: str) -> str | None:
    """Return the content of a leading ``(…)`` in *text* (one level of nesting), else ``None``."""
    rest = text.lstrip()
    if not rest.startswith("("):
        return None
    depth = 0
    for i, ch in enumerate(rest):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return rest[1:i].strip() or None
    return None  # unbalanced — no clean hint


def _parse_segment(segment: str) -> tuple[str, str | None, str | None]:
    """Parse one ref segment into ``(path, fragment_or_None, hint_or_None)``.

    A segment names a ``docs/…`` path, optionally a ``#fragment``, and optionally a
    following ``(…)`` hint that in the real data names the relevant sub-part (e.g.
    ``(spine_identity FELLOW)``); any prose after that is ignored.  The path is
    *extracted by shape* (:data:`_PATH_RE`) so trailing explanations and
    nested-paren hints do not corrupt it.  A segment with no ``docs/…`` path falls
    back to stripping a trailing annotation (keeps simple non-``docs`` refs working).
    """
    seg = segment.strip()
    m = _PATH_RE.search(seg)
    if m:
        hint = _leading_parenthetical(seg[m.end():])
        return m.group(1), m.group(2), hint
    # Fallback: no docs/-shaped path — strip a trailing annotation and split '#'.
    hint = None
    am = _ANNOTATION_RE.search(seg)
    if am:
        hint = am.group(0).strip().lstrip("(").rstrip(")").strip() or None
        seg = seg[: am.start()].strip()
    if "#" in seg:
        path, frag = seg.split("#", 1)
        return path.strip(), (frag.strip() or None), hint
    return seg, None, hint


def _split_source_ref(source_ref: str) -> tuple[str, str | None]:
    """Split a single-segment ``source_ref`` into ``(path, fragment_or_None)``.

    Thin wrapper over :func:`_parse_segment` (drops the hint) — the single-source
    shape.  Compound refs are handled by :func:`_parse_source_segments`.
    """
    path, fragment, _hint = _parse_segment(source_ref)
    return path, fragment


#: Top-level separators that join several sources in one ``source_ref``.  A
#: separator only splits at paren-depth 0 — the same tokens (``" and "``, ``;``)
#: appear *inside* hints (e.g. ``(FELLOWSHIP_TYPE: Confirmed; spine_identity
#: FELLOW)``) and must not split there.
_SEGMENT_SEPARATORS: tuple[str, ...] = (" and ", ";")


def _split_top_level(text: str, seps: tuple[str, ...]) -> list[str]:
    """Split *text* on any of *seps*, but only where one occurs at paren-depth 0.

    A compound ``source_ref`` joins several ``path (hint)`` segments; those same
    separator tokens can appear *inside* a hint, so the split must respect
    parentheses.
    """
    out: list[str] = []
    depth = 0
    start = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            for sep in seps:
                if text[i : i + len(sep)] == sep:
                    out.append(text[start:i])
                    start = i + len(sep)
                    i += len(sep)
                    break
            else:
                i += 1
            continue
        i += 1
    out.append(text[start:])
    return out


def _parse_source_segments(source_ref: str) -> list[tuple[str, str | None, str | None]]:
    """Parse a (possibly compound) ``source_ref`` into ``(path, fragment, hint)`` segments.

    Real claim refs cite one *or several* sources joined by ``" and "`` or ``;`` —
    e.g. ``…/confirmation_checklist.json (spine_identity FELLOW) and
    …/project_summary.json (researcher)``, or ``concept_note.md;
    …/scope_requirements.json#SR-04`` — each optionally with a ``#fragment`` and/or
    a parenthetical hint.  Splitting respects parentheses so a separator inside a
    hint is not mis-split.  Empty segments (no path) are dropped.
    """
    segments: list[tuple[str, str | None, str | None]] = []
    for piece in _split_top_level(source_ref.strip(), _SEGMENT_SEPARATORS):
        # A ref can trail freeform prose ("… — the contrast between …") that a
        # separator inside it may have split off; a piece with no docs/-path is
        # explanation, not a citation, so it is dropped rather than treated as a
        # missing source.
        if not _PATH_RE.search(piece):
            continue
        path, fragment, hint = _parse_segment(piece)
        if path:
            segments.append((path, fragment, hint))
    return segments


def _hint_tokens(hint: str) -> list[str]:
    """Return candidate id tokens from a hint, in order (e.g. ``FELLOW`` from ``spine_identity FELLOW``)."""
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]*", hint)


def _find_by_id(obj: Any, fragment: str) -> Any | None:
    """Recursively find the first dict whose ``id`` equals *fragment*."""
    if isinstance(obj, Mapping):
        if str(obj.get("id")) == fragment:
            return obj
        for v in obj.values():
            found = _find_by_id(v, fragment)
            if found is not None:
                return found
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            found = _find_by_id(item, fragment)
            if found is not None:
                return found
    return None


def _render_text(obj: Any, max_chars: int) -> str:
    """Render a JSON value as a bounded, judge-readable passage of its string leaves."""
    if isinstance(obj, str):
        return _bounded(obj, max_chars)
    parts: list[str] = []

    def walk(o: Any) -> None:
        if isinstance(o, str):
            if o.strip():
                parts.append(o)
        elif isinstance(o, Mapping):
            for v in o.values():
                walk(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                walk(v)
        elif isinstance(o, bool):
            parts.append(str(o))
        elif o is not None:
            parts.append(str(o))

    walk(obj)
    return _bounded("\n".join(parts), max_chars)


def resolve_claim_source_text(
    source_ref: str,
    repo_root: Path,
    *,
    max_chars: int = DEFAULT_MAX_SOURCE_CHARS,
) -> str:
    """Resolve a claim ``source_ref`` to the source passage the judge reads.

    Handles every shape a real claim ref takes: a bare path; a ``path#fragment``
    (the fragment names an object by its ``id`` — e.g. ``…#FELLOW`` in the
    checklist's ``spine_identity``, ``…#IMP-1`` in ``impacts.json``); a trailing
    ``(…)`` annotation that names the relevant sub-part (e.g. ``(spine_identity
    FELLOW)``); and a **compound** ref citing several sources joined by ``" and "``
    (``…checklist.json (spine_identity FELLOW) and …project_summary.json
    (researcher)``).  Each segment is resolved and the passages concatenated.

    **Narrowing.**  A segment is narrowed to one object when it carries an explicit
    ``#fragment`` *or* a hint token that matches an object ``id`` (so a whole-file
    checklist cite hinted ``spine_identity FELLOW`` is judged against just the
    FELLOW entry, not the ~6.5 KB blob).  With neither, the whole JSON (or raw
    non-JSON text) is used — the strict bar is only as sharp as the citation, and
    this metric does not *invent* a narrowing the ref does not provide; sharper
    grounding comes from the source citing a fragment/hint or from M2-T10's
    graph-sourced ``source_ref``s.

    Truncation is never silent (:func:`_bounded`): the cap sits above the largest
    real source, and any overflow is marked, so a finding on a truncated source is
    legible as such rather than a fabricated gap.

    Raises :class:`SourceResolutionError` only when **no** cited segment resolves
    to an existing file — a claim whose every cited source is missing cannot be
    verified and must be surfaced, not silently skipped.  If some segments resolve
    and others do not, the resolved passages are returned with the missing paths
    noted inline (visible, not silently dropped).
    """
    segments = _parse_source_segments(source_ref)
    if not segments:
        raise SourceResolutionError(
            f"source_ref {source_ref!r} has no resolvable path component."
        )
    rendered: list[str] = []
    missing: list[str] = []
    multi = len(segments) > 1
    for path, fragment, hint in segments:
        resolved = resolve_repo_path(path, repo_root)
        if not resolved.is_file():
            missing.append(path)
            continue
        rendered.append(_render_segment(resolved, fragment, hint, max_chars, label=path if multi else None))
    if not rendered:
        raise SourceResolutionError(
            f"source_ref {source_ref!r}: none of the cited paths exist "
            f"({', '.join(missing)})."
        )
    body = "\n\n".join(rendered)
    if missing:
        body += f"\n\n[…{len(missing)} cited source(s) not found: {', '.join(missing)}…]"
    return _bounded(body, max_chars)


def _render_segment(
    resolved: Path,
    fragment: str | None,
    hint: str | None,
    max_chars: int,
    *,
    label: str | None,
) -> str:
    """Render one resolved source segment, narrowed by fragment/hint where possible."""
    raw = resolved.read_text(encoding="utf-8-sig")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        text = _bounded(raw, max_chars)  # non-JSON source (e.g. a markdown document)
        return f"[source: {label}]\n{text}" if label else text

    obj: Any | None = None
    if fragment is not None:
        obj = _find_by_id(data, fragment)
    if obj is None and hint:
        for token in _hint_tokens(hint):
            obj = _find_by_id(data, token)
            if obj is not None:
                break
    text = _render_text(obj if obj is not None else data, max_chars)
    return f"[source: {label}]\n{text}" if label else text


def resolve_assumed_declared_text(
    claim: SectionClaim,
    working_assumptions: WorkingAssumptions,
) -> str | None:
    """Return the operator-declared value an ``assumed`` claim is judged against.

    Looks the declaration up two ways, matching the shared W1 substrate
    (:mod:`runner.working_assumptions`): first by ``claim_id`` as the declaration
    ``key`` (the W1 ``key``-vs-``claim_id`` match), then by ``claim_id`` as a
    ``checklist_ref`` (the D11/D12 bridge — one host declaration backs several
    spine claims).  Returns the value rendered exactly as a claim carries it
    (:func:`~runner.working_assumptions.declared_claim_summary`), or ``None`` when
    no declaration backs the claim — the caller flags that as unverifiable
    content (W1 would have blocked it, so E2 surfaces it as a finding).
    """
    decl = working_assumptions.declaration(claim.claim_id)
    if decl is None:
        by_ref = working_assumptions.by_checklist_ref(claim.claim_id)
        decl = by_ref[0] if by_ref else None
    if decl is None:
        return None
    return declared_claim_summary(decl.value)


# --------------------------------------------------------------------------- #
# Bar evaluation + severity
# --------------------------------------------------------------------------- #


def meets_bar(
    policy: StatusPolicy,
    verdict: Verdict | MajorityVerdict,
    *,
    score_informs_decision: bool = False,
) -> bool:
    """Whether *verdict* clears *policy*'s bar.

    The boolean ``passed`` is the **primary** signal and governs at every panel
    size.  The numeric ``score`` only refines the bar when *score_informs_decision*
    is ``True`` — which callers set **only** for an N≥3 majority panel, honouring
    the guardrail "N≥3 majority where a score will inform a decision."  At a single
    sample a score never drives the decision (a lone sample's confidence is not
    trustworthy enough to manufacture a hard integrity finding).

    With *score_informs_decision*:

    * strict (``confirmed`` / ``assumed``) — ``passed is True`` **and**, when a
      score is present, ``score >= min_score`` (the ≈1.0 floor);
    * soft (``inferred``) — ``passed is True`` **or** a present score clearing
      ``min_score``.

    A verdict carrying no boolean and no usable score never meets the bar.
    """
    passed = verdict.passed
    score = verdict.score
    if policy.strict:
        if passed is not True:
            return False
        if not score_informs_decision:
            return True
        return score is None or score >= policy.min_score
    # Soft: the boolean carries it at any n; a score may additionally rescue it,
    # but only when a majority panel lets the score inform the decision.
    if passed is True:
        return True
    return score_informs_decision and score is not None and score >= policy.min_score


def classify_severity(
    policy: StatusPolicy,
    verdict: Verdict | MajorityVerdict,
    *,
    score_informs_decision: bool = False,
) -> str:
    """Return :data:`SEVERITY_NONE` if *verdict* meets the bar, else the fail severity."""
    return (
        SEVERITY_NONE
        if meets_bar(policy, verdict, score_informs_decision=score_informs_decision)
        else policy.fail_severity
    )


# --------------------------------------------------------------------------- #
# Per-claim finding
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ClaimFaithfulness:
    """The status-aware faithfulness outcome for one claim.

    Attributes
    ----------
    claim_id, status:
        Identity and engine status of the judged claim.
    comparison:
        What the claim was judged against
        (:data:`COMPARISON_SOURCE` / :data:`COMPARISON_DECLARED_VALUE`).
    comparison_ref:
        The concrete target — the ``source_ref`` for a source comparison, or the
        declaration key for a declared-value comparison.
    severity:
        One of the ``SEVERITY_*`` constants; :data:`SEVERITY_NONE` means the
        claim met its status bar.
    verdict:
        The judge's :class:`~harness.verdict.Verdict` /
        :class:`~harness.verdict.MajorityVerdict`, or ``None`` when the claim was
        *not* judged (comparison target unresolved, or an unknown status).
    reason:
        Human-readable explanation, especially for the un-judged cases.
    entry_index:
        The judged claim's position in ``claim_statuses`` (see
        :attr:`SectionClaim.entry_index`); ``None`` when unknown.
    claim_summary:
        The judged claim's text, carried so a *reuser* of this finding (E5d's
        grounding aggregation) can detect that the ledger's wording drifted
        since the claim was judged — id/status/ref alone cannot see a reworded
        claim.  Empty on findings built before the field existed.
    """

    claim_id: str
    status: str
    comparison: str
    comparison_ref: str
    severity: str
    verdict: Verdict | MajorityVerdict | None = None
    reason: str = ""
    entry_index: int | None = None
    claim_summary: str = ""

    @property
    def entry_key(self) -> str:
        """Disambiguated identity (``C01#171``); bare ``claim_id`` without an index."""
        return entry_key_for(self.claim_id, self.entry_index)

    @property
    def flagged(self) -> bool:
        """``True`` when this claim warrants human review."""
        return self.severity in _FLAGGED_SEVERITIES

    @property
    def is_hard_finding(self) -> bool:
        """``True`` for a grounding failure (integrity or assumed content drift).

        Distinguished from a soft/unresolved/unknown flag: a hard finding is a
        claim whose grounding *actually failed*, not one that is merely
        unverifiable or a soft concern.
        """
        return self.severity in _HARD_SEVERITIES

    @property
    def passed(self) -> bool | None:
        """The underlying judge boolean, or ``None`` when not judged."""
        return self.verdict.passed if self.verdict is not None else None

    @property
    def score(self) -> float | None:
        """The underlying judge score, or ``None`` when not judged/scoreless."""
        return self.verdict.score if self.verdict is not None else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "entry_index": self.entry_index,
            "entry_key": self.entry_key,
            "claim_summary": self.claim_summary,
            "status": self.status,
            "comparison": self.comparison,
            "comparison_ref": self.comparison_ref,
            "severity": self.severity,
            "flagged": self.flagged,
            "is_hard_finding": self.is_hard_finding,
            "reason": self.reason,
            "verdict": self.verdict.to_dict() if self.verdict is not None else None,
        }


# --------------------------------------------------------------------------- #
# Per-claim evaluation
# --------------------------------------------------------------------------- #

#: A resolver ``(source_ref, repo_root) -> passage`` — injectable so tests supply
#: deterministic source text without touching disk (mirrors the injectable-judge
#: philosophy of the substrate).  Defaults to :func:`resolve_claim_source_text`.
SourceTextResolver = Callable[[str, Path], str]


def _judge_claim(
    judge: Judge,
    *,
    status: str,
    claim_text: str,
    comparison_text: str,
    comparison: str,
    property_key: str,
    source_ref: str | None,
    n: int,
) -> Verdict | MajorityVerdict:
    """Invoke the judge once (n==1) or as an N≥3 majority; return the verdict."""
    system_prompt, user_prompt = build_faithfulness_prompt_for_status(
        status,
        claim_text,
        comparison_text,
        comparison=comparison,
        source_ref=source_ref,
    )
    if n == 1:
        return judge.evaluate(
            system_prompt,
            user_prompt,
            metric=STATUS_AWARE_FAITHFULNESS_METRIC,
            property_key=property_key,
        ).verdict
    result: MajorityJudgeResult = judge.evaluate_majority(
        system_prompt,
        user_prompt,
        metric=STATUS_AWARE_FAITHFULNESS_METRIC,
        property_key=property_key,
        n=n,
    )
    return result.majority




def evaluate_claim(
    judge: Judge,
    claim: SectionClaim,
    *,
    repo_root: Path,
    working_assumptions: WorkingAssumptions,
    policies: Mapping[str, StatusPolicy] | None = None,
    n: int = 1,
    source_text_resolver: SourceTextResolver | None = None,
) -> ClaimFaithfulness:
    """Judge one claim's faithfulness under its status policy.

    Routes on the claim's ``entry_key`` (a green judge never overrides a red
    predicate), resolves the status-appropriate comparison target, invokes the
    judge (single or N≥3 majority), and classifies the severity.  A claim with
    an unknown status, an unresolvable source, or an ``assumed`` claim with no
    backing declaration is *surfaced un-judged* with the matching severity —
    never silently dropped.
    """
    # Routing enforcement is the public entry point's job; the section runner
    # (:func:`evaluate_status_aware_faithfulness`) routes once itself and calls
    # the already-routed body directly, so the check is not duplicated per claim.
    assert_judgeable(claim.entry_key)
    return _evaluate_claim_routed(
        judge,
        claim,
        repo_root=repo_root,
        working_assumptions=working_assumptions,
        policies=policies,
        n=n,
        source_text_resolver=source_text_resolver,
    )


def _evaluate_claim_routed(
    judge: Judge,
    claim: SectionClaim,
    *,
    repo_root: Path,
    working_assumptions: WorkingAssumptions,
    policies: Mapping[str, StatusPolicy] | None = None,
    n: int = 1,
    source_text_resolver: SourceTextResolver | None = None,
) -> ClaimFaithfulness:
    """Body of :func:`evaluate_claim`, assuming the claim id is already routed."""
    validate_sample_count(n)
    resolved_policies = policies if policies is not None else DEFAULT_POLICIES
    resolver = source_text_resolver or resolve_claim_source_text
    # A single sample's score never drives a hard decision; the ≈1.0 / soft-score
    # floor applies only with an N≥3 panel behind it (the guardrail's N≥3 rule).
    score_informs = n >= MIN_MAJORITY_SAMPLES

    def finding(
        severity: str,
        *,
        comparison: str,
        comparison_ref: str,
        verdict: Verdict | MajorityVerdict | None = None,
        reason: str = "",
    ) -> ClaimFaithfulness:
        return ClaimFaithfulness(
            claim_id=claim.claim_id,
            status=claim.status,
            comparison=comparison,
            comparison_ref=comparison_ref,
            severity=severity,
            verdict=verdict,
            reason=reason,
            entry_index=claim.entry_index,
            claim_summary=claim.claim_summary,
        )

    policy = resolved_policies.get(claim.status)
    if policy is None:
        return finding(
            SEVERITY_UNKNOWN_STATUS,
            comparison="",
            comparison_ref=claim.source_ref,
            reason=(
                f"status {claim.status!r} is not partitioned by E2 "
                f"(expected one of {sorted(resolved_policies)})."
            ),
        )

    # Resolve the status-appropriate comparison target; a missing target is a
    # surfaced-but-unjudged finding (the judge is never asked to rule on nothing).
    if policy.comparison == COMPARISON_DECLARED_VALUE:
        material = resolve_assumed_declared_text(claim, working_assumptions)
        comparison_ref = claim.claim_id
        source_ref = None
        if material is None:
            return finding(
                SEVERITY_UNRESOLVED,
                comparison=policy.comparison,
                comparison_ref=comparison_ref,
                reason=(
                    "no operator declaration backs this assumed claim "
                    "(by key or checklist_ref); its content cannot be verified."
                ),
            )
        reason = "judged against the operator-declared value"
    else:
        comparison_ref = claim.source_ref
        source_ref = claim.source_ref
        try:
            material = resolver(claim.source_ref, repo_root)
        except SourceResolutionError as exc:
            return finding(
                SEVERITY_UNRESOLVED,
                comparison=policy.comparison,
                comparison_ref=comparison_ref,
                reason=f"source unresolved: {exc}",
            )
        reason = "judged against the cited source"

    verdict = _judge_claim(
        judge,
        status=claim.status,
        claim_text=claim.claim_summary,
        comparison_text=material,
        comparison=policy.comparison,
        property_key=claim.entry_key,
        source_ref=source_ref,
        n=n,
    )
    return finding(
        classify_severity(policy, verdict, score_informs_decision=score_informs),
        comparison=policy.comparison,
        comparison_ref=comparison_ref,
        verdict=verdict,
        reason=reason,
    )


# --------------------------------------------------------------------------- #
# Whole-section result
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class StatusFaithfulnessResult:
    """The status-aware faithfulness outcome for a whole section.

    Carries every :class:`ClaimFaithfulness` in claim order plus the routing
    decisions and pinned judge identity, and builds the advisory
    :class:`~harness.report.HarnessReport` on demand.  It is *reporting-only*:
    nothing here is a gate result.
    """

    section_id: str
    findings: tuple[ClaimFaithfulness, ...]
    routing: tuple[RoutingDecision, ...] = ()
    judge_model: str | None = None
    judge_version: str | None = None

    def by_status(self) -> dict[str, tuple[ClaimFaithfulness, ...]]:
        """Group findings by engine status, preserving order."""
        out: dict[str, list[ClaimFaithfulness]] = {}
        for f in self.findings:
            out.setdefault(f.status, []).append(f)
        return {k: tuple(v) for k, v in out.items()}

    def flagged(self) -> tuple[ClaimFaithfulness, ...]:
        """Every finding a human should review (any non-``none`` severity)."""
        return tuple(f for f in self.findings if f.flagged)

    def integrity_findings(self) -> tuple[ClaimFaithfulness, ...]:
        """The hard findings — grounding that actually failed.

        A ``confirmed`` claim unsupported by its own source, or an ``assumed``
        claim that does not match its declared value.  These are the headline
        "gap masked as confirmed" (and content-drift) findings E2 exists to
        surface; soft/unresolved/unknown flags are excluded.
        """
        return tuple(f for f in self.findings if f.is_hard_finding)

    @property
    def severity_counts(self) -> dict[str, int]:
        """Count of findings by severity (all ``SEVERITY_*`` keys present)."""
        counts = {
            s: 0
            for s in (
                SEVERITY_NONE,
                SEVERITY_SOFT,
                SEVERITY_CONTENT_DRIFT,
                SEVERITY_INTEGRITY,
                SEVERITY_UNRESOLVED,
                SEVERITY_UNKNOWN_STATUS,
            )
        }
        for f in self.findings:
            counts[f.severity] = counts.get(f.severity, 0) + 1
        return counts

    def build_report(self) -> HarnessReport:
        """Assemble the advisory :class:`~harness.report.HarnessReport`.

        ``findings`` are the actual judge verdicts (so the report's pass/fail
        summary is over real verdicts); un-judged claims are summarized in the
        notes.  ``advisory=True, blocking=False`` is structural — the harness
        never gates a run.
        """
        verdicts = [f.verdict for f in self.findings if f.verdict is not None]
        integrity = self.integrity_findings()
        counts = self.severity_counts
        notes = (
            f"section={self.section_id}; claims={len(self.findings)}; "
            f"hard_findings={len(integrity)} "
            f"(integrity={counts[SEVERITY_INTEGRITY]}, "
            f"content_drift={counts[SEVERITY_CONTENT_DRIFT]}); "
            f"soft={counts[SEVERITY_SOFT]}; unresolved={counts[SEVERITY_UNRESOLVED]}; "
            f"unknown_status={counts[SEVERITY_UNKNOWN_STATUS]}. "
            "Advisory only — never a runtime gate (see harness/HARNESS.md)."
        )
        return build_report(
            STATUS_AWARE_FAITHFULNESS_METRIC,
            verdicts,
            routing=self.routing,
            notes=notes,
            judge_model=self.judge_model,
            judge_version=self.judge_version,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "status_aware_faithfulness_result",
            "metric": STATUS_AWARE_FAITHFULNESS_METRIC,
            "section_id": self.section_id,
            "judge_model": self.judge_model,
            "judge_version": self.judge_version,
            "severity_counts": self.severity_counts,
            "hard_finding_ids": [f.entry_key for f in self.integrity_findings()],
            "findings": [f.to_dict() for f in self.findings],
        }


def evaluate_status_aware_faithfulness(
    claims: Sequence[SectionClaim],
    judge: Judge,
    *,
    repo_root: Path,
    working_assumptions: WorkingAssumptions,
    section_id: str = "",
    policies: Mapping[str, StatusPolicy] | None = None,
    n: int = 1,
    source_text_resolver: SourceTextResolver | None = None,
    claim_filter: Callable[[SectionClaim], bool] | None = None,
) -> StatusFaithfulnessResult:
    """Run status-aware faithfulness over a section's claims.

    Partitions each claim by ``status`` and judges it under the matching
    :class:`StatusPolicy`, returning a :class:`StatusFaithfulnessResult` that
    surfaces the hard "gap masked as confirmed" findings, the soft concerns, and
    the un-judged (unresolved / unknown-status) claims.  *claim_filter* limits
    the run to a subset (e.g. only ``confirmed`` claims); *n* selects a single
    verdict (1) or an N≥3 majority.  Reporting-only; performs zero DAG runs.
    """
    validate_sample_count(n)
    selected = [c for c in claims if (claim_filter is None or claim_filter(c))]
    findings: list[ClaimFaithfulness] = []
    routing: list[RoutingDecision] = []
    for claim in selected:
        # Route once here (collecting the decision for the report) and call the
        # already-routed body, so routing is not re-evaluated per claim.
        routing.append(assert_judgeable(claim.entry_key))
        findings.append(
            _evaluate_claim_routed(
                judge,
                claim,
                repo_root=repo_root,
                working_assumptions=working_assumptions,
                policies=policies,
                n=n,
                source_text_resolver=source_text_resolver,
            )
        )
    return StatusFaithfulnessResult(
        section_id=section_id,
        findings=tuple(findings),
        routing=tuple(routing),
        judge_model=judge.config.model,
        judge_version=judge.config.version,
    )


# --------------------------------------------------------------------------- #
# M3 reuse — per-claim grounding baseline + invariance
# --------------------------------------------------------------------------- #
#
# The Milestone-3 composition pass rewrites each section's prose while carrying
# claim_statuses / source_ref forward verbatim.  The threat is a composer that
# keeps every canonical token but weakens the *grounding* of a confirmed claim.
# So the exit check is: freeze the per-claim grounding verdict on the
# pre-composition ledger, re-run on the composed output, and require that no
# claim's grounding weakened — *form may change, grounding may not.*

#: A score may drift slightly under residual judge non-determinism without being
#: a grounding regression; a drop beyond this (on a claim still meeting its bar)
#: is surfaced as a soft ``score_drop`` — informational, not an invariance break.
DEFAULT_SCORE_DROP_TOLERANCE: float = 0.15

#: Invariance-violation kinds.  The first three *break* invariance (grounding
#: weakened or the ledger mutated); ``score_drop`` is a soft, informational flag.
VIOLATION_DROPPED: str = "dropped"
VIOLATION_STATUS_CHANGED: str = "status_changed"
VIOLATION_BAR_REGRESSION: str = "bar_regression"
VIOLATION_SCORE_DROP: str = "score_drop"

#: Kinds that break per-claim grounding invariance.
_WEAKENING_KINDS: frozenset[str] = frozenset(
    {VIOLATION_DROPPED, VIOLATION_STATUS_CHANGED, VIOLATION_BAR_REGRESSION}
)


@dataclass(frozen=True)
class ClaimGroundingSnapshot:
    """The frozen per-claim grounding a baseline records for one claim.

    Deliberately *not* the full verdict prose — only the grounding facts the
    invariance check compares: the status, the comparison kind, the severity,
    whether the bar was met, and the judge's boolean/score.
    """

    claim_id: str
    status: str
    comparison: str
    severity: str
    #: Whether the claim met its status bar at freeze time (``severity == none``).
    #: A field, distinct from the module-level :func:`meets_bar` predicate.
    met_bar: bool
    passed: bool | None
    score: float | None
    #: Position in ``claim_statuses`` — real ledgers repeat ``claim_id`` across
    #: drafting blocks, so without this a baseline of same-id claims collapses.
    entry_index: int | None = None

    @property
    def entry_key(self) -> str:
        """Disambiguated identity (``C01#171``); bare ``claim_id`` without an index."""
        return entry_key_for(self.claim_id, self.entry_index)

    @classmethod
    def from_finding(cls, finding: ClaimFaithfulness) -> "ClaimGroundingSnapshot":
        return cls(
            claim_id=finding.claim_id,
            status=finding.status,
            comparison=finding.comparison,
            severity=finding.severity,
            met_bar=finding.severity == SEVERITY_NONE,
            passed=finding.passed,
            score=finding.score,
            entry_index=finding.entry_index,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "entry_index": self.entry_index,
            "status": self.status,
            "comparison": self.comparison,
            "severity": self.severity,
            "met_bar": self.met_bar,
            "passed": self.passed,
            "score": self.score,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "ClaimGroundingSnapshot":
        return cls(
            claim_id=str(d.get("claim_id", "")),
            status=str(d.get("status", "")),
            comparison=str(d.get("comparison", "")),
            severity=str(d.get("severity", "")),
            met_bar=bool(d.get("met_bar", False)),
            passed=d.get("passed"),
            score=d.get("score"),
            # Absent in baselines frozen before entry_index existed — the key
            # then falls back to the bare claim_id, keeping old files loadable.
            entry_index=d.get("entry_index"),
        )


@dataclass(frozen=True)
class FaithfulnessBaseline:
    """A frozen per-claim grounding snapshot for a section (the M3 baseline).

    Keyed by ``claim_id``.  Carries the pinned judge identity it was measured
    under so a baseline frozen by one judge is not silently compared under a
    repinned one (:meth:`applies_to`, mirroring the E1.5 calibration discipline).
    """

    baseline_id: str
    section_id: str
    judge_model: str | None
    judge_version: str | None
    snapshots: tuple[ClaimGroundingSnapshot, ...]

    def by_id(self) -> dict[str, ClaimGroundingSnapshot]:
        """Snapshots keyed by ``entry_key`` (claim ids repeat across blocks).

        Keying on the bare ``claim_id`` would silently collapse a real ledger
        (excellence: 191 entries / 128 unique ids) and mis-compare the M3
        invariance check.  Baselines frozen before ``entry_index`` existed fall
        back to ``claim_id`` keys.
        """
        return {s.entry_key: s for s in self.snapshots}

    def applies_to(self, judge_model: str | None, judge_version: str | None) -> bool:
        """Whether this baseline was frozen under the given judge pin."""
        return (
            self.judge_model == judge_model
            and self.judge_version == judge_version
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "status_faithfulness_baseline",
            "metric": STATUS_AWARE_FAITHFULNESS_METRIC,
            "baseline_id": self.baseline_id,
            "section_id": self.section_id,
            "judge_model": self.judge_model,
            "judge_version": self.judge_version,
            "snapshots": [s.to_dict() for s in self.snapshots],
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "FaithfulnessBaseline":
        snaps = d.get("snapshots", [])
        if not isinstance(snaps, list):
            raise StatusFaithfulnessError("baseline 'snapshots' must be an array.")
        return cls(
            baseline_id=str(d.get("baseline_id", "")),
            section_id=str(d.get("section_id", "")),
            judge_model=d.get("judge_model"),
            judge_version=d.get("judge_version"),
            snapshots=tuple(ClaimGroundingSnapshot.from_dict(s) for s in snaps),
        )


def freeze_baseline(
    result: StatusFaithfulnessResult, *, baseline_id: str = ""
) -> FaithfulnessBaseline:
    """Freeze *result*'s per-claim grounding as a reusable M3 baseline."""
    return FaithfulnessBaseline(
        baseline_id=baseline_id or f"baseline:{result.section_id}",
        section_id=result.section_id,
        judge_model=result.judge_model,
        judge_version=result.judge_version,
        snapshots=tuple(
            ClaimGroundingSnapshot.from_finding(f) for f in result.findings
        ),
    )


def write_baseline(baseline: FaithfulnessBaseline, path: Path | str) -> None:
    """Write *baseline* as canonical JSON, atomically (harness-owned artifact)."""
    atomic_write_json(baseline.to_dict(), Path(path), prefix="faith_baseline_")


def load_baseline(path: Path | str) -> FaithfulnessBaseline:
    """Load a :class:`FaithfulnessBaseline` written by :func:`write_baseline`."""
    p = Path(path)
    if not p.is_file():
        raise StatusFaithfulnessError(f"baseline file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise StatusFaithfulnessError(f"baseline {p} is not valid JSON: {exc}") from exc
    return FaithfulnessBaseline.from_dict(data)


@dataclass(frozen=True)
class InvarianceViolation:
    """One per-claim grounding change between a baseline and a re-run.

    ``claim_id`` carries the *entry key* (``C01#171``) where the ledger
    supplied an entry index, so a violation names exactly which of several
    same-id claims changed.  ``kind`` is one of the ``VIOLATION_*`` constants.
    A ``breaking`` violation
    (:data:`VIOLATION_DROPPED` / :data:`VIOLATION_STATUS_CHANGED` /
    :data:`VIOLATION_BAR_REGRESSION`) means grounding weakened or the ledger
    mutated; :data:`VIOLATION_SCORE_DROP` is a soft, informational flag.
    """

    claim_id: str
    kind: str
    detail: str
    baseline: dict[str, Any] | None = None
    current: dict[str, Any] | None = None

    @property
    def breaking(self) -> bool:
        return self.kind in _WEAKENING_KINDS

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "kind": self.kind,
            "breaking": self.breaking,
            "detail": self.detail,
            "baseline": self.baseline,
            "current": self.current,
        }


@dataclass(frozen=True)
class InvarianceReport:
    """The result of comparing a re-run against a frozen baseline.

    ``invariant`` is ``True`` iff no *breaking* violation occurred — grounding
    held for every baseline claim.  Soft ``score_drop`` flags and ``added_claim_ids``
    (claims in the re-run but not the baseline) are surfaced without breaking
    invariance.  ``judge_repinned`` warns that the comparison spans a judge repin
    (the E1.5 discipline: a repin re-opens the advisory-only state).
    """

    baseline_id: str
    section_id: str
    compared: int
    violations: tuple[InvarianceViolation, ...]
    added_claim_ids: tuple[str, ...]
    judge_repinned: bool = False

    @property
    def invariant(self) -> bool:
        return not any(v.breaking for v in self.violations)

    @property
    def breaking_violations(self) -> tuple[InvarianceViolation, ...]:
        return tuple(v for v in self.violations if v.breaking)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "status_faithfulness_invariance",
            "metric": STATUS_AWARE_FAITHFULNESS_METRIC,
            "baseline_id": self.baseline_id,
            "section_id": self.section_id,
            "invariant": self.invariant,
            "compared": self.compared,
            "judge_repinned": self.judge_repinned,
            "breaking_count": len(self.breaking_violations),
            "added_claim_ids": list(self.added_claim_ids),
            "violations": [v.to_dict() for v in self.violations],
        }


def compare_to_baseline(
    baseline: FaithfulnessBaseline,
    result: StatusFaithfulnessResult,
    *,
    score_drop_tolerance: float = DEFAULT_SCORE_DROP_TOLERANCE,
) -> InvarianceReport:
    """Compare a re-run *result* against a frozen *baseline*, per claim.

    Emits an :class:`InvarianceViolation` for each grounding change:

    * :data:`VIOLATION_DROPPED` — a baseline claim absent from the re-run (the
      ledger lost a claim);
    * :data:`VIOLATION_STATUS_CHANGED` — the claim's status changed (composition
      is supposed to carry status forward verbatim);
    * :data:`VIOLATION_BAR_REGRESSION` — a claim that met its bar no longer does
      (grounding weakened — the headline M3 risk);
    * :data:`VIOLATION_SCORE_DROP` — a still-passing claim whose score fell more
      than *score_drop_tolerance* (soft, informational).

    ``invariant`` on the returned report is ``True`` iff none of the first three
    (breaking) kinds occurred.  Reporting-only; advisory to a human.
    """
    base_by_id = baseline.by_id()
    # Keyed by entry_key throughout — claim ids repeat across drafting blocks,
    # and a violation must name exactly which entry weakened.
    cur_by_id = {f.entry_key: f for f in result.findings}
    violations: list[InvarianceViolation] = []

    for claim_id, snap in base_by_id.items():
        cur = cur_by_id.get(claim_id)
        if cur is None:
            violations.append(
                InvarianceViolation(
                    claim_id=claim_id,
                    kind=VIOLATION_DROPPED,
                    detail="claim present in baseline is absent from the re-run.",
                    baseline=snap.to_dict(),
                    current=None,
                )
            )
            continue
        if snap.status != cur.status:
            violations.append(
                InvarianceViolation(
                    claim_id=claim_id,
                    kind=VIOLATION_STATUS_CHANGED,
                    detail=f"status changed {snap.status!r} → {cur.status!r}.",
                    baseline=snap.to_dict(),
                    current=cur.to_dict(),
                )
            )
        cur_meets = cur.severity == SEVERITY_NONE
        if snap.met_bar and not cur_meets:
            violations.append(
                InvarianceViolation(
                    claim_id=claim_id,
                    kind=VIOLATION_BAR_REGRESSION,
                    detail=(
                        f"grounding weakened: met the bar in the baseline, now "
                        f"severity {cur.severity!r}."
                    ),
                    baseline=snap.to_dict(),
                    current=cur.to_dict(),
                )
            )
        elif (
            snap.score is not None
            and cur.score is not None
            and cur.score < snap.score - score_drop_tolerance
        ):
            violations.append(
                InvarianceViolation(
                    claim_id=claim_id,
                    kind=VIOLATION_SCORE_DROP,
                    detail=(
                        f"score fell {snap.score:.3f} → {cur.score:.3f} "
                        f"(> {score_drop_tolerance} tolerance) but still meets the bar."
                    ),
                    baseline=snap.to_dict(),
                    current=cur.to_dict(),
                )
            )

    added = tuple(cid for cid in cur_by_id if cid not in base_by_id)
    return InvarianceReport(
        baseline_id=baseline.baseline_id,
        section_id=result.section_id,
        compared=len(base_by_id),
        violations=tuple(violations),
        added_claim_ids=added,
        judge_repinned=not baseline.applies_to(
            result.judge_model, result.judge_version
        ),
    )
