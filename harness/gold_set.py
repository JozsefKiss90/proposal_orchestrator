"""
The human-labeled faithfulness gold set (E1.5).

Judge-reliability calibration needs a small set of ``(claim, source_ref,
supported?)`` triples where ``supported?`` is a **human** ground-truth label —
not the engine's own ``status``.  The distinction is the whole point: the engine
may stamp a claim ``confirmed`` while its cited source does not actually support
it ("a gap masked as confirmed"), so the engine's ``status`` is a *prior/candidate*,
never the gold label.  A human reads the claim against its source and records
whether the source genuinely supports it; the calibration
(:mod:`harness.calibration`) then measures whether the pinned judge agrees.

This module owns the gold-set data model, a **fail-closed** loader (an unlabeled
pair cannot be used for calibration — you cannot characterize a judge against
labels that don't exist), and a deterministic seeder that draws candidate pairs
from the real ``validation_status.claim_statuses`` of a Phase-8 section.  The
seeder emits *unlabeled templates*; it never fabricates the human label (an AI
labeling the gold set for an AI judge would reintroduce exactly the
grader–generator correlation the harness exists to avoid).

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate; reads a Tier-5 section
    only to seed candidates and writes only harness-owned gold-set files.  See
    ``harness/HARNESS.md``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from runner.atomic_write import atomic_write_text

__all__ = [
    "RECOMMENDED_MIN_PAIRS",
    "RECOMMENDED_MAX_PAIRS",
    "TO_BE_LABELED",
    "GoldSetError",
    "GoldPair",
    "GoldSet",
    "load_gold_set",
    "gold_set_hash",
    "seed_pairs_from_claim_statuses",
    "write_gold_set_template",
]

#: The ticket's recommended gold-set size band (~20–30 pairs).  Advisory — the
#: loader warns outside it but does not fail (a human curates the final set).
RECOMMENDED_MIN_PAIRS: int = 20
RECOMMENDED_MAX_PAIRS: int = 30

#: Human-facing marker written on a seeded, not-yet-labeled pair.
TO_BE_LABELED: str = "TO_BE_LABELED_BY_HUMAN"


class GoldSetError(Exception):
    """A gold set is malformed, or unlabeled where a label is required."""


@dataclass(frozen=True)
class GoldPair:
    """One ``(claim, source_ref, supported?)`` gold triple.

    Attributes
    ----------
    pair_id:
        Stable identifier within the gold set.
    claim:
        The claim text under test (typically a ``claim_summary``).
    source_ref:
        The path the engine cited as the claim's source (provenance).
    supported:
        The **human** ground-truth label — ``True`` if the source genuinely
        supports the claim, ``False`` if not.  ``None`` means *unlabeled* (a
        seeded template awaiting a human); calibration rejects it.
    claim_id:
        The originating ``claim_id`` (e.g. ``C07``), when seeded from a section.
    source_excerpt:
        The specific passage the human judged against.  Recommended on a labeled
        pair so calibration is self-contained and reproducible (the judge sees a
        bounded excerpt, not a drifting file).
    engine_status:
        The engine's stamped ``status`` (``confirmed`` / ``inferred`` /
        ``assumed``).  Informational prior only — **not** the gold label.
    labeler:
        Optional human labeler identity, for provenance.
    note:
        Optional free-form human note.
    """

    pair_id: str
    claim: str
    source_ref: str
    supported: bool | None = None
    claim_id: str | None = None
    source_excerpt: str | None = None
    engine_status: str | None = None
    labeler: str | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if not str(self.pair_id).strip():
            raise GoldSetError("GoldPair.pair_id must be non-empty.")
        if not str(self.claim).strip():
            raise GoldSetError(f"GoldPair {self.pair_id!r}: claim must be non-empty.")
        if not str(self.source_ref).strip():
            raise GoldSetError(f"GoldPair {self.pair_id!r}: source_ref must be non-empty.")
        if self.supported is not None and not isinstance(self.supported, bool):
            raise GoldSetError(
                f"GoldPair {self.pair_id!r}: supported must be a bool or None "
                f"(unlabeled); got {self.supported!r}."
            )

    @property
    def is_labeled(self) -> bool:
        """``True`` iff a human has set :attr:`supported`."""
        return self.supported is not None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "pair_id": self.pair_id,
            "claim_id": self.claim_id,
            "claim": self.claim,
            "source_ref": self.source_ref,
            "source_excerpt": self.source_excerpt,
            "engine_status": self.engine_status,
            "supported": self.supported,
            "labeler": self.labeler,
            "note": self.note,
        }
        if not self.is_labeled:
            d["labeling_status"] = TO_BE_LABELED
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "GoldPair":
        if not isinstance(d, dict):
            raise GoldSetError(f"gold pair must be an object; got {type(d).__name__}")
        return cls(
            pair_id=str(d.get("pair_id", "")),
            claim=str(d.get("claim", "")),
            source_ref=str(d.get("source_ref", "")),
            supported=d.get("supported"),
            claim_id=d.get("claim_id"),
            source_excerpt=d.get("source_excerpt"),
            engine_status=d.get("engine_status"),
            labeler=d.get("labeler"),
            note=str(d.get("note", "")),
        )


@dataclass(frozen=True)
class GoldSet:
    """An ordered collection of :class:`GoldPair` with a stable id."""

    pairs: tuple[GoldPair, ...]
    gold_set_id: str = ""

    def __len__(self) -> int:
        return len(self.pairs)

    def __iter__(self):
        return iter(self.pairs)

    def labeled(self) -> tuple[GoldPair, ...]:
        """The human-labeled pairs, in order."""
        return tuple(p for p in self.pairs if p.is_labeled)

    def unlabeled(self) -> tuple[GoldPair, ...]:
        """The pairs still awaiting a human label."""
        return tuple(p for p in self.pairs if not p.is_labeled)

    def require_fully_labeled(self) -> None:
        """Raise :class:`GoldSetError` if any pair is unlabeled.

        The fail-closed gate calibration calls before measuring a judge: a set
        with unlabeled pairs cannot characterize reliability.
        """
        missing = [p.pair_id for p in self.unlabeled()]
        if missing:
            raise GoldSetError(
                f"gold set {self.gold_set_id!r} has {len(missing)} unlabeled pair(s) "
                f"({missing[:5]}{'…' if len(missing) > 5 else ''}); a human must set "
                f"'supported' on every pair before calibration."
            )


def _iter_raw_pairs(text: str) -> Iterable[dict]:
    """Yield raw pair dicts from either a JSON list/`{pairs:[…]}` or JSONL body."""
    stripped = text.strip()
    if not stripped:
        return []
    # Whole-file JSON (a list, or an object with a "pairs" array).
    try:
        whole = json.loads(stripped)
    except json.JSONDecodeError:
        whole = None
    if isinstance(whole, list):
        return whole
    if isinstance(whole, dict) and isinstance(whole.get("pairs"), list):
        return whole["pairs"]
    # Otherwise treat as JSONL (one object per non-blank line).
    out: list[dict] = []
    for line in stripped.splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def load_gold_set(
    path: Path | str,
    *,
    require_labeled: bool = True,
    gold_set_id: str | None = None,
) -> GoldSet:
    """Load a gold set from a ``.jsonl`` (one pair per line) or ``.json`` file.

    Parameters
    ----------
    path:
        The gold-set file.
    require_labeled:
        When ``True`` (the default — calibration mode), every pair must carry a
        human ``supported`` label; an unlabeled pair raises
        :class:`GoldSetError`.  Pass ``False`` to load a seeded template for
        editing.
    gold_set_id:
        Overrides the derived id (default: the file stem).

    Raises
    ------
    GoldSetError
        On a missing file, malformed content, duplicate ``pair_id``, or — when
        *require_labeled* — any unlabeled pair.
    """
    p = Path(path)
    if not p.is_file():
        raise GoldSetError(f"gold set file not found: {p}")
    try:
        raw = _iter_raw_pairs(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise GoldSetError(f"gold set {p} is not valid JSON/JSONL: {exc}") from exc

    pairs = tuple(GoldPair.from_dict(d) for d in raw)
    seen: set[str] = set()
    for pair in pairs:
        if pair.pair_id in seen:
            raise GoldSetError(f"duplicate pair_id in gold set: {pair.pair_id!r}")
        seen.add(pair.pair_id)

    gold_set = GoldSet(pairs=pairs, gold_set_id=gold_set_id or p.stem)
    if require_labeled:
        gold_set.require_fully_labeled()
    return gold_set


def gold_set_hash(gold_set: GoldSet) -> str:
    """Return a stable ``sha256:`` hash over the gold set's labeled content.

    Hashes ``(pair_id, claim, source_ref, source_excerpt, supported)`` per pair,
    so a re-label or a claim edit changes the hash (a calibration recorded
    against an old hash is visibly stale), but a cosmetic note edit does not.
    """
    h = hashlib.sha256()
    for p in gold_set.pairs:
        h.update(
            json.dumps(
                [p.pair_id, p.claim, p.source_ref, p.source_excerpt, p.supported],
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        )
        h.update(b"\x00")
    return f"sha256:{h.hexdigest()}"


def _even_spaced_indices(n: int, k: int) -> list[int]:
    """Return *k* evenly-spaced, deterministic, de-duplicated indices in ``[0, n)``."""
    if n <= 0 or k <= 0:
        return []
    if k >= n:
        return list(range(n))
    if k == 1:
        return [0]
    picks = [round(j * (n - 1) / (k - 1)) for j in range(k)]
    # De-dupe while preserving order (rounding can collide for small n).
    seen: set[int] = set()
    out: list[int] = []
    for i in picks:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def seed_pairs_from_claim_statuses(
    claim_statuses: list[dict],
    *,
    limit: int = RECOMMENDED_MAX_PAIRS,
    prefix: str = "gold",
) -> list[GoldPair]:
    """Draw a deterministic candidate sample of *unlabeled* pairs from ``claim_statuses``.

    Each emitted :class:`GoldPair` carries the real ``claim_id``,
    ``claim_summary`` (as ``claim``), ``source_ref`` and engine ``status`` — but
    ``supported`` is ``None``: the human label is deliberately **not** fabricated.
    Candidates are first de-duplicated by ``(claim, source_ref)`` (a section's
    ``claim_statuses`` can repeat a claim, and labeling the same faithfulness
    question twice is wasted human effort).  Sampling is then deterministic
    (evenly-spaced indices) and stratified across the present statuses
    proportionally, so both grounded and less-grounded claims are represented — a
    ``confirmed`` claim that is actually unsupported is the integrity-critical
    case the gold set must be able to contain.
    """
    valid = [
        c for c in claim_statuses
        if isinstance(c, dict) and str(c.get("claim_summary", "")).strip()
        and str(c.get("source_ref", "")).strip()
    ]
    # De-duplicate identical (claim, source_ref) questions, keeping first occurrence.
    seen_keys: set[tuple[str, str]] = set()
    deduped: list[dict] = []
    for c in valid:
        key = (str(c.get("claim_summary", "")), str(c.get("source_ref", "")))
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped.append(c)
    if not deduped:
        return []
    limit = max(1, min(limit, len(deduped)))

    # Group by status (first-seen order), allocate limit proportionally, and pick
    # evenly-spaced members within each group.
    groups: dict[str, list[dict]] = {}
    for c in deduped:
        groups.setdefault(str(c.get("status", "unknown")), []).append(c)
    alloc = _allocate(limit, {k: len(v) for k, v in groups.items()})
    chosen: list[dict] = []
    for status, k in alloc.items():
        grp = groups[status]
        chosen.extend(grp[i] for i in _even_spaced_indices(len(grp), k))

    pairs: list[GoldPair] = []
    for i, c in enumerate(chosen):
        pairs.append(
            GoldPair(
                pair_id=f"{prefix}-{i + 1:02d}",
                claim=str(c.get("claim_summary", "")),
                source_ref=str(c.get("source_ref", "")),
                supported=None,  # human label pending — never fabricated
                claim_id=c.get("claim_id"),
                engine_status=c.get("status"),
            )
        )
    return pairs


def _allocate(total: int, sizes: dict[str, int]) -> dict[str, int]:
    """Split *total* across groups proportionally to *sizes*, ≥1 each, deterministic."""
    present = {k: v for k, v in sizes.items() if v > 0}
    if not present:
        return {}
    grand = sum(present.values())
    # Largest-remainder method for a stable, exact split.
    base: dict[str, int] = {}
    remainders: list[tuple[float, str]] = []
    for k, v in present.items():
        exact = total * v / grand
        base[k] = max(1, int(exact))
        remainders.append((exact - int(exact), k))
    # Adjust to hit *total* exactly.
    diff = total - sum(base.values())
    if diff > 0:
        for _, k in sorted(remainders, reverse=True):
            if diff == 0:
                break
            base[k] += 1
            diff -= 1
    elif diff < 0:
        # Trim from the largest allocations first, never below 1.
        for k in sorted(base, key=base.get, reverse=True):
            while diff < 0 and base[k] > 1:
                base[k] -= 1
                diff += 1
            if diff == 0:
                break
    return base


def write_gold_set_template(pairs: list[GoldPair], path: Path | str) -> None:
    """Write *pairs* as a JSONL gold-set template (atomic, one pair per line).

    Intended for seeded, unlabeled candidates — the file a human then edits to
    set ``supported`` on each pair.
    """
    body = "".join(json.dumps(p.to_dict(), ensure_ascii=False) + "\n" for p in pairs)
    atomic_write_text(body, Path(path), prefix="goldset_")
