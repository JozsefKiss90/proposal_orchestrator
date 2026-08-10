"""
Regression golden-set — frozen baselines for the Tier-5 sections (E4).

The safety net the length-lift work lacks: a prompt change, a drafting soft-cap
lift (D2/D3), or a model swap regenerates the Phase-8 sections, and nothing
today would notice if the redraft silently *lost* a claim, weakened a
``confirmed`` to an ``inferred``, swapped a claim's evidential basis
(``source_ref``), or dropped a sub-section.  E4 freezes the current section
JSONs as golden baselines and diffs any future artifact against them, so a
regression of integrity or quality is *surfaced to a human* instead of sliding
through.

Two lanes, mirroring the harness's deterministic-first routing:

* **Deterministic fingerprint lane (zero judge, runs offline in CI).**
  :func:`freeze_section_fingerprint` snapshots a section's claim ledger
  (matched by *meaning* — ``(claim_summary, status, source_ref)`` — never by
  bare ``claim_id``, the E3 lesson), its per-sub-section prose hashes, and a
  canonical whole-artifact hash.  :func:`compare_section` diffs a current
  artifact against the frozen fingerprint and classifies every drift:
  a removed claim, a status change, or a source-ref change is a **breaking**
  regression finding; an added claim, prose growth, or a confirmed-share drop
  is advisory context.  Prose that changed while the ledger did not is called
  out explicitly — that is the escaped-claim risk zone (re-run E2/E3 on it).
* **Judge lane (E2 reuse, pending a live judge).**
  :func:`freeze_section_grounding` / :func:`compare_section_grounding` are thin
  wrappers over E2's :func:`~harness.status_faithfulness.freeze_baseline` /
  :func:`~harness.status_faithfulness.compare_to_baseline` — the per-claim
  grounding-invariance check (*form may change, grounding may not*), run under
  the pinned, non-drafter judge.
* **Rubric lane (E5f handoff).**  :func:`freeze_rubric_baseline` /
  :func:`compare_rubric_baseline` freeze the graded E5 coverage×grounding
  grid (``harness.rubric``) and diff a future re-grade against it — so a
  prompt or model change cannot silently regress an expectation's coverage or
  grounding outcome.  The comparison itself is deterministic dict arithmetic
  (the judge spend happened when the reports were graded); it fail-closes on
  a judge repin or a rubric-set fingerprint change, where grades stop being
  comparable and the baseline must be refrozen instead.

**Merge-advisory, never run-blocking.**  The comparison output is a
:class:`RegressionReport` with ``advisory=True, blocking=False`` enforced
structurally (a report cannot be constructed otherwise), and nothing in
``runner`` reads it.  The CLI's non-zero exit and the standing pytest lane
(``-m harness_regression``) advise a *merge decision by a human* — refreeze the
golden set if the change is intentional, investigate if it is not.  No DAG run
consumes any of this (the 138 deterministic predicates remain the only blocking
runtime gates).

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA; reads Tier-5 sections only to
    fingerprint/judge them and writes only harness-owned baseline/report files.
    Never a runtime gate.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from runner.atomic_write import atomic_write_json
from harness.claim_ledger import SubSectionProse, load_section_prose
from harness.judge import Judge
from harness.status_faithfulness import (
    FaithfulnessBaseline,
    InvarianceReport,
    SectionClaim,
    SourceTextResolver,
    StatusPolicy,
    compare_to_baseline,
    entry_key_for,
    evaluate_status_aware_faithfulness,
    freeze_baseline,
    load_section_claims,
)
from runner.working_assumptions import WorkingAssumptions

__all__ = [
    "REGRESSION_GOLDEN_METRIC",
    "RegressionError",
    # finding kinds
    "REGRESSION_CLAIM_REMOVED",
    "REGRESSION_STATUS_CHANGED",
    "REGRESSION_SOURCE_REF_CHANGED",
    "REGRESSION_CLAIM_ADDED",
    "REGRESSION_SUBSECTION_REMOVED",
    "REGRESSION_SUBSECTION_ADDED",
    "REGRESSION_PROSE_CHANGED",
    "REGRESSION_PROSE_CHANGED_LEDGER_UNCHANGED",
    "REGRESSION_CONFIRMED_SHARE_DROP",
    "REGRESSION_SECTION_MISSING",
    "REGRESSION_SECTION_ADDED",
    "DEFAULT_CONFIRMED_SHARE_TOLERANCE",
    "CURRENT_SNAPSHOT",
    # fingerprint model
    "LedgerEntry",
    "SubSectionFingerprint",
    "SectionFingerprint",
    "freeze_section_fingerprint",
    "write_fingerprint",
    "load_fingerprint",
    "GOLDEN_SUFFIX",
    "freeze_golden_set",
    "load_golden_set",
    "DEFAULT_SECTIONS_DIR",
    "DEFAULT_GOLDEN_DIR",
    # comparison
    "RegressionFinding",
    "SectionRegressionResult",
    "RegressionReport",
    "compare_section",
    "compare_to_golden_set",
    # judge lane (E2 reuse)
    "freeze_section_grounding",
    "compare_section_grounding",
    # rubric lane (E5f handoff)
    "RUBRIC_BASELINE_RECORD_TYPE",
    "DEFAULT_RUBRIC_BASELINE_PATH",
    "REGRESSION_RUBRIC_CELL_MISSING",
    "REGRESSION_RUBRIC_CELL_ADDED",
    "REGRESSION_RUBRIC_CELL_REGRESSED",
    "REGRESSION_RUBRIC_CONTRADICTION_APPEARED",
    "REGRESSION_RUBRIC_CELL_IMPROVED",
    "freeze_rubric_baseline",
    "load_rubric_baseline",
    "compare_rubric_baseline",
    # CLI
    "main",
]

#: The metric name stamped on every regression-golden artifact.
REGRESSION_GOLDEN_METRIC: str = "regression_golden_set"

#: Suffix of a per-section golden baseline file in the golden directory.
GOLDEN_SUFFIX: str = ".golden.json"

#: Where the live Phase-8 sections live (CLI default).
DEFAULT_SECTIONS_DIR: Path = Path("docs/tier5_deliverables/proposal_sections")

#: Where the committed golden baselines live (CLI default; harness-owned).
DEFAULT_GOLDEN_DIR: Path = Path("harness/regression_baselines")

# --------------------------------------------------------------------------- #
# Finding kinds
# --------------------------------------------------------------------------- #

#: A claim frozen in the baseline is absent from the current ledger — the
#: redraft *lost* a claim (breaking: integrity content vanished).
REGRESSION_CLAIM_REMOVED: str = "claim_removed"
#: A claim's ``status`` changed (e.g. ``confirmed`` → ``inferred``) — the
#: evidential promise moved (breaking either direction; a human decides).
REGRESSION_STATUS_CHANGED: str = "status_changed"
#: A claim's ``source_ref`` changed — same claim, different evidential basis
#: (breaking: grounding must be re-established, not silently swapped).
REGRESSION_SOURCE_REF_CHANGED: str = "source_ref_changed"
#: A claim present now but not in the baseline (advisory: new content).
REGRESSION_CLAIM_ADDED: str = "claim_added"
#: A baseline sub-section is gone (breaking: structure lost).
REGRESSION_SUBSECTION_REMOVED: str = "subsection_removed"
#: A new sub-section appeared (advisory).
REGRESSION_SUBSECTION_ADDED: str = "subsection_added"
#: A sub-section's prose changed (advisory; char delta in the detail).
REGRESSION_PROSE_CHANGED: str = "prose_changed"
#: Prose changed while the claim ledger did not — the escaped-claim risk zone;
#: re-run E2 grounding + E3 completeness on the new prose (advisory pointer).
REGRESSION_PROSE_CHANGED_LEDGER_UNCHANGED: str = "prose_changed_ledger_unchanged"
#: The share of ``confirmed`` claims fell beyond tolerance (advisory: the
#: quality axis — grounding density weakened even if no single claim broke).
REGRESSION_CONFIRMED_SHARE_DROP: str = "confirmed_share_drop"
#: A whole baseline section has no current artifact (breaking).
REGRESSION_SECTION_MISSING: str = "section_missing"
#: A current section has no baseline yet (advisory: freeze it).
REGRESSION_SECTION_ADDED: str = "section_added"

# Rubric-lane kinds (the E5f grid vs its frozen baseline; see the rubric-lane
# section below for the freeze/compare machinery).

#: A baseline cell has no counterpart in the current report (breaking: an
#: expectation silently fell out of the grid).
REGRESSION_RUBRIC_CELL_MISSING: str = "rubric_cell_missing"
#: A current cell has no baseline yet (advisory: refreeze to cover it).
REGRESSION_RUBRIC_CELL_ADDED: str = "rubric_cell_added"
#: A cell's coverage or grounding outcome degraded (breaking: the axis the
#: baseline vouched for no longer holds).
REGRESSION_RUBRIC_CELL_REGRESSED: str = "rubric_cell_regressed"
#: A contradiction kind absent from the baseline cell appeared (breaking).
REGRESSION_RUBRIC_CONTRADICTION_APPEARED: str = "rubric_contradiction_appeared"
#: A cell improved or a contradiction disappeared (advisory: refreeze to keep
#: the tighter baseline).
REGRESSION_RUBRIC_CELL_IMPROVED: str = "rubric_cell_improved"

#: Kinds that constitute a regression a human must decide on (refreeze or fix).
_BREAKING_KINDS: frozenset[str] = frozenset(
    {
        REGRESSION_CLAIM_REMOVED,
        REGRESSION_STATUS_CHANGED,
        REGRESSION_SOURCE_REF_CHANGED,
        REGRESSION_SUBSECTION_REMOVED,
        REGRESSION_SECTION_MISSING,
        REGRESSION_RUBRIC_CELL_MISSING,
        REGRESSION_RUBRIC_CELL_REGRESSED,
        REGRESSION_RUBRIC_CONTRADICTION_APPEARED,
    }
)

#: A ``confirmed``-share fall larger than this (absolute share, 0–1) is flagged
#: as an advisory quality drop.  Operator policy, not physics.
DEFAULT_CONFIRMED_SHARE_TOLERANCE: float = 0.05

#: The ``frozen_at`` stamp of an in-memory *current* snapshot built only to be
#: compared — it is not a frozen golden and is never written to disk.
CURRENT_SNAPSHOT: str = ""


class RegressionError(Exception):
    """A fingerprint/baseline is missing or malformed, or an input is invalid."""


def _default_clock() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(text: str) -> str:
    """Whitespace-normalize *text* for meaning comparison."""
    return " ".join(str(text).split())


# --------------------------------------------------------------------------- #
# Fingerprint model
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class LedgerEntry:
    """One frozen ``claim_statuses`` entry.

    ``identity`` is the claim's *meaning* — ``(claim_summary, status,
    source_ref)``, whitespace-normalized — never the bare ``claim_id``: real
    ledgers repeat ids across independently-numbered drafting blocks (three
    unrelated ``C01``\\ s in the excellence section), so an id-keyed diff would
    be broken by construction.  The id + entry index serve only as the display
    label (:attr:`entry_key`, e.g. ``C01#171``).
    """

    claim_id: str
    claim_summary: str
    status: str
    source_ref: str
    entry_index: int | None = None

    @property
    def entry_key(self) -> str:
        """Disambiguated display label (``C01#171``); see E2's ``entry_key_for``."""
        return entry_key_for(self.claim_id, self.entry_index)

    @property
    def identity(self) -> tuple[str, str, str]:
        """The claim's meaning — what the regression diff matches on."""
        return (_norm(self.claim_summary), _norm(self.status), _norm(self.source_ref))

    @property
    def summary_key(self) -> str:
        """The normalized summary alone — pairs status/source drift on one claim."""
        return _norm(self.claim_summary)

    @classmethod
    def from_claim(cls, claim: SectionClaim) -> "LedgerEntry":
        return cls(
            claim_id=claim.claim_id,
            claim_summary=claim.claim_summary,
            status=claim.status,
            source_ref=claim.source_ref,
            entry_index=claim.entry_index,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "entry_index": self.entry_index,
            "entry_key": self.entry_key,
            "claim_summary": self.claim_summary,
            "status": self.status,
            "source_ref": self.source_ref,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "LedgerEntry":
        return cls(
            claim_id=str(d.get("claim_id", "")),
            claim_summary=str(d.get("claim_summary", "")),
            status=str(d.get("status", "")),
            source_ref=str(d.get("source_ref", "")),
            entry_index=d.get("entry_index"),
        )


@dataclass(frozen=True)
class SubSectionFingerprint:
    """The frozen shape of one sub-section's prose (hash + size, not the text).

    The golden file stays reviewable and the git history already holds the full
    text; a hash is enough to *detect* a prose change, and the E2/E3 judge lanes
    are what evaluate its content.
    """

    sub_section_id: str
    title: str
    content_sha256: str
    char_count: int

    @classmethod
    def from_prose(cls, sub: SubSectionProse) -> "SubSectionFingerprint":
        return cls(
            sub_section_id=sub.sub_section_id,
            title=sub.title,
            content_sha256=hashlib.sha256(sub.content.encode("utf-8")).hexdigest(),
            char_count=len(sub.content),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "sub_section_id": self.sub_section_id,
            "title": self.title,
            "content_sha256": self.content_sha256,
            "char_count": self.char_count,
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "SubSectionFingerprint":
        return cls(
            sub_section_id=str(d.get("sub_section_id", "")),
            title=str(d.get("title", "")),
            content_sha256=str(d.get("content_sha256", "")),
            char_count=int(d.get("char_count", 0)),
        )


@dataclass(frozen=True)
class SectionFingerprint:
    """The frozen golden baseline of one Phase-8 section artifact."""

    section_id: str
    artifact_path: str
    artifact_sha256: str
    frozen_at: str
    claims: tuple[LedgerEntry, ...]
    sub_sections: tuple[SubSectionFingerprint, ...]

    @property
    def status_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for c in self.claims:
            counts[c.status] = counts.get(c.status, 0) + 1
        return counts

    @property
    def confirmed_share(self) -> float | None:
        """Share of ``confirmed`` claims, or ``None`` on an empty ledger."""
        if not self.claims:
            return None
        confirmed = sum(1 for c in self.claims if c.status == "confirmed")
        return confirmed / len(self.claims)

    def identity_entries(self) -> dict[tuple[str, str, str], LedgerEntry]:
        """Deduped ledger keyed by claim meaning (first occurrence wins).

        Duplicate identical records are drafting noise (E3 dedups them the same
        way); the diff compares unique meanings, not copy counts.
        """
        out: dict[tuple[str, str, str], LedgerEntry] = {}
        for entry in self.claims:
            out.setdefault(entry.identity, entry)
        return out

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "regression_section_fingerprint",
            "metric": REGRESSION_GOLDEN_METRIC,
            "section_id": self.section_id,
            "artifact_path": self.artifact_path,
            "artifact_sha256": self.artifact_sha256,
            "frozen_at": self.frozen_at,
            "status_counts": self.status_counts,
            "claims": [c.to_dict() for c in self.claims],
            "sub_sections": [s.to_dict() for s in self.sub_sections],
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "SectionFingerprint":
        claims = d.get("claims", [])
        subs = d.get("sub_sections", [])
        if not isinstance(claims, list) or not isinstance(subs, list):
            raise RegressionError(
                "fingerprint 'claims' and 'sub_sections' must be arrays."
            )
        return cls(
            section_id=str(d.get("section_id", "")),
            artifact_path=str(d.get("artifact_path", "")),
            artifact_sha256=str(d.get("artifact_sha256", "")),
            frozen_at=str(d.get("frozen_at", "")),
            claims=tuple(LedgerEntry.from_dict(c) for c in claims),
            sub_sections=tuple(SubSectionFingerprint.from_dict(s) for s in subs),
        )


def _canonical_artifact_sha256(data: Any) -> str:
    """Hash the *parsed* artifact canonically, so formatting/BOM churn is inert."""
    canonical = json.dumps(
        data, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def freeze_section_fingerprint(
    path: Path | str,
    *,
    section_id: str | None = None,
    frozen_at: str | None = None,
) -> SectionFingerprint:
    """Freeze one section JSON into a :class:`SectionFingerprint`.

    Fail-closed like every harness loader: a missing file, invalid JSON, or an
    absent ``claim_statuses``/``sub_sections`` raises rather than freezing an
    empty golden that would bless anything.  ``frozen_at`` is injectable for
    deterministic tests; the CLI stamps the UTC time of the freeze.
    """
    p = Path(path)
    if not p.is_file():
        raise RegressionError(f"section file not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise RegressionError(f"section {p} is not valid JSON: {exc}") from exc
    claims = load_section_claims(p)
    subs = load_section_prose(p)
    return SectionFingerprint(
        section_id=section_id or p.stem,
        artifact_path=p.as_posix(),
        artifact_sha256=_canonical_artifact_sha256(data),
        frozen_at=frozen_at if frozen_at is not None else _default_clock(),
        claims=tuple(LedgerEntry.from_claim(c) for c in claims),
        sub_sections=tuple(SubSectionFingerprint.from_prose(s) for s in subs),
    )


def write_fingerprint(fingerprint: SectionFingerprint, path: Path | str) -> None:
    """Write *fingerprint* as canonical JSON, atomically (harness-owned)."""
    atomic_write_json(fingerprint.to_dict(), Path(path), prefix="regression_golden_")


def load_fingerprint(path: Path | str) -> SectionFingerprint:
    """Load a :class:`SectionFingerprint` written by :func:`write_fingerprint`."""
    p = Path(path)
    if not p.is_file():
        raise RegressionError(f"golden fingerprint not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise RegressionError(f"golden {p} is not valid JSON: {exc}") from exc
    return SectionFingerprint.from_dict(data)


def freeze_golden_set(
    section_paths: Iterable[Path | str],
    out_dir: Path | str,
    *,
    frozen_at: str | None = None,
) -> tuple[SectionFingerprint, ...]:
    """Freeze each section and write ``<section_id>.golden.json`` files."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = frozen_at if frozen_at is not None else _default_clock()
    frozen: list[SectionFingerprint] = []
    for sp in section_paths:
        fp = freeze_section_fingerprint(sp, frozen_at=stamp)
        write_fingerprint(fp, out / f"{fp.section_id}{GOLDEN_SUFFIX}")
        frozen.append(fp)
    return tuple(frozen)


def load_golden_set(golden_dir: Path | str) -> dict[str, SectionFingerprint]:
    """Load every ``*.golden.json`` in *golden_dir*, keyed by ``section_id``.

    Fail-closed on an empty/missing directory — a regression check against no
    baselines would vacuously pass, which is exactly the silence E4 exists to
    prevent.
    """
    d = Path(golden_dir)
    files = sorted(d.glob(f"*{GOLDEN_SUFFIX}")) if d.is_dir() else []
    if not files:
        raise RegressionError(
            f"no {GOLDEN_SUFFIX} baselines found in {d} — freeze a golden set "
            "first (python -m harness.regression freeze)."
        )
    out: dict[str, SectionFingerprint] = {}
    for f in files:
        fp = load_fingerprint(f)
        out[fp.section_id] = fp
    return out


# --------------------------------------------------------------------------- #
# Comparison — the deterministic regression lane
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RegressionFinding:
    """One drift between a golden baseline and the current artifact."""

    kind: str
    section_id: str
    detail: str
    baseline: dict[str, Any] | None = None
    current: dict[str, Any] | None = None

    @property
    def breaking(self) -> bool:
        """Whether this finding is a regression a human must decide on."""
        return self.kind in _BREAKING_KINDS

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "breaking": self.breaking,
            "section_id": self.section_id,
            "detail": self.detail,
            "baseline": self.baseline,
            "current": self.current,
        }


@dataclass(frozen=True)
class SectionRegressionResult:
    """The deterministic regression outcome for one section."""

    section_id: str
    artifact_changed: bool
    findings: tuple[RegressionFinding, ...]

    @property
    def regressed(self) -> bool:
        return any(f.breaking for f in self.findings)

    @property
    def breaking_findings(self) -> tuple[RegressionFinding, ...]:
        return tuple(f for f in self.findings if f.breaking)

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "artifact_changed": self.artifact_changed,
            "regressed": self.regressed,
            "findings": [f.to_dict() for f in self.findings],
        }


_LEDGER_KINDS: frozenset[str] = frozenset(
    {
        REGRESSION_CLAIM_REMOVED,
        REGRESSION_STATUS_CHANGED,
        REGRESSION_SOURCE_REF_CHANGED,
        REGRESSION_CLAIM_ADDED,
    }
)


def _diff_ledger(
    golden: SectionFingerprint, current: SectionFingerprint
) -> list[RegressionFinding]:
    """Diff the two deduped ledgers by claim meaning.

    Exact-identity matches are unchanged.  The remainders are then paired by
    ``summary_key`` (same claim text) to distinguish a status/source-ref *drift
    on one claim* from a removed+added pair; pairing is in sorted order so the
    diff is deterministic.  Whatever cannot be paired is removed (breaking) or
    added (advisory).  A semantic rephrase of a summary shows as removed+added
    — surfaced for the human; the judge lane covers semantic equivalence.
    """
    sid = golden.section_id
    base_ids = golden.identity_entries()
    cur_ids = current.identity_entries()
    base_rest = [e for k, e in sorted(base_ids.items()) if k not in cur_ids]
    cur_rest = [e for k, e in sorted(cur_ids.items()) if k not in base_ids]

    by_summary_base: dict[str, list[LedgerEntry]] = {}
    for e in base_rest:
        by_summary_base.setdefault(e.summary_key, []).append(e)
    by_summary_cur: dict[str, list[LedgerEntry]] = {}
    for e in cur_rest:
        by_summary_cur.setdefault(e.summary_key, []).append(e)

    findings: list[RegressionFinding] = []
    for summary in sorted(set(by_summary_base) | set(by_summary_cur)):
        bases = by_summary_base.get(summary, [])
        curs = by_summary_cur.get(summary, [])
        for b, c in zip(bases, curs):
            if _norm(b.status) != _norm(c.status):
                findings.append(
                    RegressionFinding(
                        kind=REGRESSION_STATUS_CHANGED,
                        section_id=sid,
                        detail=(
                            f"{b.entry_key}: status {b.status!r} → {c.status!r} "
                            f"({b.claim_summary[:80]!r})"
                        ),
                        baseline=b.to_dict(),
                        current=c.to_dict(),
                    )
                )
            if _norm(b.source_ref) != _norm(c.source_ref):
                findings.append(
                    RegressionFinding(
                        kind=REGRESSION_SOURCE_REF_CHANGED,
                        section_id=sid,
                        detail=(
                            f"{b.entry_key}: source_ref changed "
                            f"({b.claim_summary[:80]!r})"
                        ),
                        baseline=b.to_dict(),
                        current=c.to_dict(),
                    )
                )
        for b in bases[len(curs):]:
            findings.append(
                RegressionFinding(
                    kind=REGRESSION_CLAIM_REMOVED,
                    section_id=sid,
                    detail=f"{b.entry_key}: baseline claim absent from the current ledger.",
                    baseline=b.to_dict(),
                )
            )
        for c in curs[len(bases):]:
            findings.append(
                RegressionFinding(
                    kind=REGRESSION_CLAIM_ADDED,
                    section_id=sid,
                    detail=f"{c.entry_key}: claim not present in the golden baseline.",
                    current=c.to_dict(),
                )
            )
    return findings


def _diff_prose(
    golden: SectionFingerprint, current: SectionFingerprint
) -> list[RegressionFinding]:
    """Diff sub-section structure and prose hashes."""
    sid = golden.section_id
    base_subs = {s.sub_section_id: s for s in golden.sub_sections}
    cur_subs = {s.sub_section_id: s for s in current.sub_sections}
    findings: list[RegressionFinding] = []
    for sub_id, b in base_subs.items():
        c = cur_subs.get(sub_id)
        if c is None:
            findings.append(
                RegressionFinding(
                    kind=REGRESSION_SUBSECTION_REMOVED,
                    section_id=sid,
                    detail=f"sub-section {sub_id!r} ({b.title!r}) is gone.",
                    baseline=b.to_dict(),
                )
            )
        elif c.content_sha256 != b.content_sha256:
            delta = c.char_count - b.char_count
            findings.append(
                RegressionFinding(
                    kind=REGRESSION_PROSE_CHANGED,
                    section_id=sid,
                    detail=(
                        f"sub-section {sub_id!r} prose changed "
                        f"({b.char_count} → {c.char_count} chars, {delta:+d})."
                    ),
                    baseline=b.to_dict(),
                    current=c.to_dict(),
                )
            )
    for sub_id, c in cur_subs.items():
        if sub_id not in base_subs:
            findings.append(
                RegressionFinding(
                    kind=REGRESSION_SUBSECTION_ADDED,
                    section_id=sid,
                    detail=f"new sub-section {sub_id!r} ({c.title!r}).",
                    current=c.to_dict(),
                )
            )
    return findings


def compare_section(
    golden: SectionFingerprint,
    current: SectionFingerprint,
    *,
    confirmed_share_tolerance: float = DEFAULT_CONFIRMED_SHARE_TOLERANCE,
) -> SectionRegressionResult:
    """Diff a current section fingerprint against its golden baseline.

    An identical artifact hash short-circuits to a clean result.  Otherwise the
    ledger is diffed by meaning, the prose by structure + hash, and two
    advisory quality signals are added: prose that changed while the ledger did
    not (the escaped-claim risk zone — re-run E2/E3 there), and a
    ``confirmed``-share fall beyond *confirmed_share_tolerance*.
    """
    if golden.artifact_sha256 == current.artifact_sha256:
        return SectionRegressionResult(
            section_id=golden.section_id, artifact_changed=False, findings=()
        )

    findings = _diff_ledger(golden, current)
    ledger_changed = any(f.kind in _LEDGER_KINDS for f in findings)
    prose_findings = _diff_prose(golden, current)
    findings.extend(prose_findings)

    if not ledger_changed and any(
        f.kind == REGRESSION_PROSE_CHANGED for f in prose_findings
    ):
        findings.append(
            RegressionFinding(
                kind=REGRESSION_PROSE_CHANGED_LEDGER_UNCHANGED,
                section_id=golden.section_id,
                detail=(
                    "prose changed but the claim ledger did not — the "
                    "escaped-claim risk zone; re-run E2 grounding and E3 "
                    "completeness on the new prose."
                ),
            )
        )

    base_share = golden.confirmed_share
    cur_share = current.confirmed_share
    if (
        base_share is not None
        and cur_share is not None
        and cur_share < base_share - confirmed_share_tolerance
    ):
        findings.append(
            RegressionFinding(
                kind=REGRESSION_CONFIRMED_SHARE_DROP,
                section_id=golden.section_id,
                detail=(
                    f"confirmed-claim share fell {base_share:.2f} → {cur_share:.2f} "
                    f"(tolerance {confirmed_share_tolerance}); grounding density "
                    "weakened."
                ),
            )
        )

    return SectionRegressionResult(
        section_id=golden.section_id,
        artifact_changed=True,
        findings=tuple(findings),
    )


# --------------------------------------------------------------------------- #
# Report — advisory by construction
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RegressionReport:
    """The whole golden-set comparison — merge-advisory, never run-blocking.

    ``advisory``/``blocking`` are enforced exactly like
    :class:`~harness.report.HarnessReport`: a report that could block a run
    cannot be constructed.  ``golden_set_findings`` carries the
    golden-set-level drifts (missing/new sections); per-section drifts live in
    ``results``.
    """

    results: tuple[SectionRegressionResult, ...]
    golden_set_findings: tuple[RegressionFinding, ...] = ()
    notes: str = ""
    advisory: bool = True
    blocking: bool = False

    def __post_init__(self) -> None:
        if self.advisory is not True:
            raise ValueError(
                "RegressionReport.advisory must be True — the golden-set is "
                "merge-advisory to a human, never authoritative over a run."
            )
        if self.blocking is not False:
            raise ValueError(
                "RegressionReport.blocking must be False — no eval metric may "
                "wire into the runtime DAG as a fail-closed gate."
            )

    @property
    def regressed(self) -> bool:
        return any(r.regressed for r in self.results) or any(
            f.breaking for f in self.golden_set_findings
        )

    @property
    def summary(self) -> dict[str, int]:
        all_findings = [f for r in self.results for f in r.findings]
        all_findings.extend(self.golden_set_findings)
        return {
            "sections_compared": len(self.results),
            "sections_changed": sum(1 for r in self.results if r.artifact_changed),
            "findings": len(all_findings),
            "breaking": sum(1 for f in all_findings if f.breaking),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "regression_golden_report",
            "metric": REGRESSION_GOLDEN_METRIC,
            "advisory": self.advisory,
            "blocking": self.blocking,
            "regressed": self.regressed,
            "summary": self.summary,
            "notes": self.notes,
            "golden_set_findings": [f.to_dict() for f in self.golden_set_findings],
            "sections": [r.to_dict() for r in self.results],
        }


#: The advisory boundary sentence stamped on every report.
_ADVISORY_NOTE: str = (
    "Merge-advisory to a human, never run-blocking: refreeze the golden set if "
    "the change is intentional, investigate if not (see harness/HARNESS.md)."
)


def compare_to_golden_set(
    golden: Mapping[str, SectionFingerprint],
    current_paths: Sequence[Path | str],
    *,
    confirmed_share_tolerance: float = DEFAULT_CONFIRMED_SHARE_TOLERANCE,
) -> RegressionReport:
    """Compare the current section artifacts against a loaded golden set.

    Sections are matched by ``section_id`` (the file stem).  A baseline with no
    current artifact is a breaking :data:`REGRESSION_SECTION_MISSING`; a current
    artifact with no baseline is an advisory :data:`REGRESSION_SECTION_ADDED`.
    """
    current: dict[str, SectionFingerprint] = {}
    for p in current_paths:
        fp = freeze_section_fingerprint(p, frozen_at=CURRENT_SNAPSHOT)
        current[fp.section_id] = fp

    set_findings: list[RegressionFinding] = []
    results: list[SectionRegressionResult] = []
    for section_id in sorted(golden):
        cur = current.get(section_id)
        if cur is None:
            set_findings.append(
                RegressionFinding(
                    kind=REGRESSION_SECTION_MISSING,
                    section_id=section_id,
                    detail=f"golden section {section_id!r} has no current artifact.",
                    baseline={"artifact_path": golden[section_id].artifact_path},
                )
            )
            continue
        results.append(
            compare_section(
                golden[section_id],
                cur,
                confirmed_share_tolerance=confirmed_share_tolerance,
            )
        )
    for section_id in sorted(set(current) - set(golden)):
        set_findings.append(
            RegressionFinding(
                kind=REGRESSION_SECTION_ADDED,
                section_id=section_id,
                detail=(
                    f"section {section_id!r} has no golden baseline yet — "
                    "freeze it to bring it under regression cover."
                ),
                current={"artifact_path": current[section_id].artifact_path},
            )
        )
    return RegressionReport(
        results=tuple(results),
        golden_set_findings=tuple(set_findings),
        notes=_ADVISORY_NOTE,
    )


# --------------------------------------------------------------------------- #
# Judge lane — E2 grounding-baseline reuse (pending a live judge)
# --------------------------------------------------------------------------- #


def _judge_section(
    section_path: Path | str,
    judge: Judge,
    *,
    repo_root: Path,
    working_assumptions: WorkingAssumptions,
    policies: Mapping[str, StatusPolicy] | None,
    n: int,
    source_text_resolver: SourceTextResolver | None,
):
    """Run E2's status-aware faithfulness over one section file."""
    p = Path(section_path)
    claims = load_section_claims(p)
    return evaluate_status_aware_faithfulness(
        claims,
        judge,
        repo_root=repo_root,
        working_assumptions=working_assumptions,
        section_id=p.stem,
        policies=policies,
        n=n,
        source_text_resolver=source_text_resolver,
    )


def freeze_section_grounding(
    section_path: Path | str,
    judge: Judge,
    *,
    repo_root: Path,
    working_assumptions: WorkingAssumptions,
    baseline_id: str = "",
    policies: Mapping[str, StatusPolicy] | None = None,
    n: int = 1,
    source_text_resolver: SourceTextResolver | None = None,
) -> FaithfulnessBaseline:
    """Freeze the per-claim grounding baseline for one section (E2 reuse).

    Runs E2's status-aware faithfulness over the section and freezes the
    verdicts — the judge half of the golden set, complementing the
    deterministic fingerprint.  Requires the pinned live judge (or an injected
    backend in tests); the fingerprint lane needs neither.
    """
    result = _judge_section(
        section_path,
        judge,
        repo_root=repo_root,
        working_assumptions=working_assumptions,
        policies=policies,
        n=n,
        source_text_resolver=source_text_resolver,
    )
    return freeze_baseline(result, baseline_id=baseline_id)


def compare_section_grounding(
    section_path: Path | str,
    baseline: FaithfulnessBaseline,
    judge: Judge,
    *,
    repo_root: Path,
    working_assumptions: WorkingAssumptions,
    policies: Mapping[str, StatusPolicy] | None = None,
    n: int = 1,
    source_text_resolver: SourceTextResolver | None = None,
) -> InvarianceReport:
    """Re-judge a section and compare its grounding against a frozen baseline.

    E2's grounding-invariance check applied as the E4 regression assertion:
    after a soft-cap lift or model swap, *form may change, grounding may not* —
    a ``bar_regression``, ``status_changed``, or ``dropped`` claim breaks
    invariance and is surfaced for the human merge decision.
    """
    result = _judge_section(
        section_path,
        judge,
        repo_root=repo_root,
        working_assumptions=working_assumptions,
        policies=policies,
        n=n,
        source_text_resolver=source_text_resolver,
    )
    return compare_to_baseline(baseline, result)


# --------------------------------------------------------------------------- #
# Rubric lane — the frozen E5f grid as a regression baseline (E5 handoff)
# --------------------------------------------------------------------------- #

#: The ``record_type`` of a frozen rubric-grid baseline file.
RUBRIC_BASELINE_RECORD_TYPE: str = "rubric_grid_baseline"

#: Where the frozen rubric-grid baseline lives (harness-owned; the suffix is
#: distinct from ``.golden.json`` so ``load_golden_set`` never reads it).
DEFAULT_RUBRIC_BASELINE_PATH: Path = DEFAULT_GOLDEN_DIR / "rubric_grid.rubric.json"

#: The ``record_type`` a rubric report must carry (mirrored from
#: ``harness.rubric`` without importing it — the rubric module already imports
#: nothing from here, and the string is a stable data contract).
_RUBRIC_REPORT_RECORD_TYPE: str = "rubric_grade_report"


def _require_report(report: Mapping[str, Any], label: str) -> None:
    """Fail closed unless *report* is a well-formed advisory rubric report."""
    if not isinstance(report, Mapping):
        raise RegressionError(f"{label} is not a JSON object.")
    if report.get("record_type") != _RUBRIC_REPORT_RECORD_TYPE:
        raise RegressionError(
            f"{label} is not a {_RUBRIC_REPORT_RECORD_TYPE!r} record "
            f"(got {report.get('record_type')!r})."
        )
    if report.get("advisory") is not True or report.get("blocking") is not False:
        raise RegressionError(
            f"{label} does not carry advisory=True/blocking=False — refusing "
            "a report that claims authority over a run."
        )
    cells = report.get("cells")
    if not isinstance(cells, list) or not cells:
        raise RegressionError(
            f"{label} has no cells — an empty grid cannot serve as a baseline."
        )
    if not report.get("judge_model") or not report.get("judge_version"):
        raise RegressionError(
            f"{label} carries no judge pin — a baseline without a pin cannot "
            "enforce the repin discipline."
        )


def freeze_rubric_baseline(
    report: Mapping[str, Any],
    *,
    baseline_id: str = "rubric_grid",
    frozen_at: str | None = None,
    budget_record: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze a graded rubric report as the E4 rubric-lane baseline.

    The full report travels inside the baseline (the audit trail), pinned to
    the judge and rubric set it was graded under.  *budget_record* is the E5f
    budget accounting — recorded with the freeze so the baseline documents
    what the run cost and what it planned.
    """
    _require_report(report, "rubric report")
    return {
        "record_type": RUBRIC_BASELINE_RECORD_TYPE,
        "metric": str(report.get("metric", "")),
        "baseline_id": baseline_id,
        "frozen_at": frozen_at if frozen_at is not None else _default_clock(),
        "judge_model": report["judge_model"],
        "judge_version": report["judge_version"],
        "rubric_set_id": str(report.get("rubric_set_id", "")),
        "rubric_set_version": str(report.get("rubric_set_version", "")),
        "rubric_set_fingerprint": str(report.get("rubric_set_fingerprint", "")),
        "budget_record": dict(budget_record) if budget_record is not None else None,
        "report": dict(report),
    }


def _read_json(path: Path, label: str) -> Any:
    """Read one JSON file fail-closed (missing/invalid raise, never default)."""
    if not path.is_file():
        raise RegressionError(f"{label} not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise RegressionError(f"{label} {path} is not valid JSON: {exc}") from exc


def load_rubric_baseline(path: Path | str) -> dict[str, Any]:
    """Load a frozen rubric-grid baseline, fail-closed."""
    p = Path(path)
    data = _read_json(p, "rubric baseline")
    if not isinstance(data, Mapping) or data.get("record_type") != RUBRIC_BASELINE_RECORD_TYPE:
        raise RegressionError(f"{p} is not a {RUBRIC_BASELINE_RECORD_TYPE!r} record.")
    _require_report(data.get("report", {}), f"rubric baseline {p} report")
    return dict(data)


def _cell_index(report: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    out: dict[tuple[str, str], Mapping[str, Any]] = {}
    for cell in report.get("cells", []):
        out[(str(cell.get("expectation_key", "")), str(cell.get("section_id", "")))] = cell
    return out


#: The boolean axes a baseline cell vouches for, with the record path each
#: reads: the cell-level covered/grounded outcomes plus coverage's clean pass
#: (the truncation-override bit E5b makes visible).
_RUBRIC_AXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("covered", ("covered",)),
    ("grounded", ("grounded",)),
    ("coverage clean pass", ("coverage", "passed")),
)


def _axis_value(cell: Mapping[str, Any], path: tuple[str, ...]) -> Any:
    node: Any = cell
    for key in path:
        if not isinstance(node, Mapping):
            return None
        node = node.get(key)
    return node


def _contradiction_kinds(cell: Mapping[str, Any]) -> set[str]:
    return {
        str(c.get("kind", ""))
        for c in cell.get("contradictions", [])
        if isinstance(c, Mapping)
    }


def compare_rubric_baseline(
    baseline: Mapping[str, Any],
    current_report: Mapping[str, Any],
) -> RegressionReport:
    """Diff a fresh rubric report against the frozen baseline, deterministically.

    Fail-closed on a judge repin or a rubric-set fingerprint change — grades
    under a different judge or different rubric text are not comparable; the
    E1.5 discipline says refreeze under the new pin instead.  Otherwise every
    baseline cell's boolean axes (covered, grounded, coverage clean pass) must
    hold and no new contradiction kind may appear; degradations are breaking
    findings, improvements are advisory context for a refreeze decision.
    """
    _require_report(current_report, "current rubric report")
    base_report = baseline.get("report")
    _require_report(base_report if isinstance(base_report, Mapping) else {}, "baseline report")

    base_pin = (baseline.get("judge_model"), baseline.get("judge_version"))
    cur_pin = (current_report.get("judge_model"), current_report.get("judge_version"))
    if base_pin != cur_pin:
        raise RegressionError(
            f"judge repin: baseline was frozen under {base_pin[0]}@{base_pin[1]}, "
            f"the current report is graded under {cur_pin[0]}@{cur_pin[1]} — "
            "not comparable; refreeze the rubric baseline under the new pin."
        )
    base_fp = str(baseline.get("rubric_set_fingerprint", ""))
    cur_fp = str(current_report.get("rubric_set_fingerprint", ""))
    if base_fp != cur_fp:
        raise RegressionError(
            "rubric-set fingerprint changed since the baseline was frozen — "
            "the rubric text is different, so the grades are not comparable; "
            "refreeze the rubric baseline for the new rubric set."
        )

    base_cells = _cell_index(base_report)  # type: ignore[arg-type]
    cur_cells = _cell_index(current_report)

    findings: list[RegressionFinding] = []
    for key in sorted(base_cells):
        expectation_key, section_id = key
        base_cell = base_cells[key]
        cur_cell = cur_cells.get(key)
        if cur_cell is None:
            findings.append(
                RegressionFinding(
                    kind=REGRESSION_RUBRIC_CELL_MISSING,
                    section_id=section_id,
                    detail=(
                        f"{expectation_key} / {section_id}: baseline cell has "
                        "no counterpart in the current report."
                    ),
                    baseline={"cell": base_cell.get("cell")},
                )
            )
            continue
        for axis, path in _RUBRIC_AXES:
            was, now = _axis_value(base_cell, path), _axis_value(cur_cell, path)
            if was is True and now is not True:
                findings.append(
                    RegressionFinding(
                        kind=REGRESSION_RUBRIC_CELL_REGRESSED,
                        section_id=section_id,
                        detail=(
                            f"{expectation_key} / {section_id}: {axis} "
                            f"degraded {was!r} -> {now!r}."
                        ),
                        baseline={axis: was},
                        current={axis: now},
                    )
                )
            elif was is not True and now is True:
                findings.append(
                    RegressionFinding(
                        kind=REGRESSION_RUBRIC_CELL_IMPROVED,
                        section_id=section_id,
                        detail=(
                            f"{expectation_key} / {section_id}: {axis} "
                            f"improved {was!r} -> {now!r} (refreeze to keep it)."
                        ),
                        baseline={axis: was},
                        current={axis: now},
                    )
                )
        base_kinds = _contradiction_kinds(base_cell)
        cur_kinds = _contradiction_kinds(cur_cell)
        for kind in sorted(cur_kinds - base_kinds):
            findings.append(
                RegressionFinding(
                    kind=REGRESSION_RUBRIC_CONTRADICTION_APPEARED,
                    section_id=section_id,
                    detail=(
                        f"{expectation_key} / {section_id}: contradiction "
                        f"{kind!r} appeared (absent from the baseline)."
                    ),
                    current={"contradiction_kind": kind},
                )
            )
        for kind in sorted(base_kinds - cur_kinds):
            findings.append(
                RegressionFinding(
                    kind=REGRESSION_RUBRIC_CELL_IMPROVED,
                    section_id=section_id,
                    detail=(
                        f"{expectation_key} / {section_id}: baseline "
                        f"contradiction {kind!r} is gone (refreeze to keep it)."
                    ),
                    baseline={"contradiction_kind": kind},
                )
            )
    for key in sorted(set(cur_cells) - set(base_cells)):
        expectation_key, section_id = key
        findings.append(
            RegressionFinding(
                kind=REGRESSION_RUBRIC_CELL_ADDED,
                section_id=section_id,
                detail=(
                    f"{expectation_key} / {section_id}: cell has no rubric "
                    "baseline yet — refreeze to bring it under cover."
                ),
                current={"cell": cur_cells[key].get("cell")},
            )
        )
    return RegressionReport(
        results=(),
        golden_set_findings=tuple(findings),
        notes=(
            "Rubric-lane comparison (coverage x grounding grid vs the frozen "
            "baseline). " + _ADVISORY_NOTE
        ),
    )


# --------------------------------------------------------------------------- #
# CLI — freeze / check (merge-advisory)
# --------------------------------------------------------------------------- #


def _section_files(sections_dir: Path) -> list[Path]:
    files = sorted(Path(sections_dir).glob("*.json"))
    if not files:
        raise RegressionError(f"no section JSONs found in {sections_dir}.")
    return files


def main(argv: Sequence[str] | None = None) -> int:
    """``python -m harness.regression`` — freeze or check the golden set.

    Exit codes: ``0`` clean; ``1`` drift detected (**merge-advisory** — a human
    decides to refreeze or fix; nothing run-blocking consumes this); ``2`` the
    check itself could not run (missing baselines/sections — fail-closed).
    """
    parser = argparse.ArgumentParser(
        prog="harness.regression",
        description=(
            "E4 regression golden-set: freeze the Tier-5 section JSONs as "
            "golden baselines, or check the current artifacts against them. "
            "Merge-advisory to a human; never a runtime gate."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_freeze = sub.add_parser("freeze", help="freeze current sections as the golden set")
    p_freeze.add_argument("--sections", default=str(DEFAULT_SECTIONS_DIR))
    p_freeze.add_argument("--out", default=str(DEFAULT_GOLDEN_DIR))
    p_freeze.add_argument("--frozen-at", default=None, help="freeze label (default: UTC now)")

    p_check = sub.add_parser("check", help="compare current sections to the golden set")
    p_check.add_argument("--sections", default=str(DEFAULT_SECTIONS_DIR))
    p_check.add_argument("--golden", default=str(DEFAULT_GOLDEN_DIR))
    p_check.add_argument("--report", default=None, help="also write the report JSON here")

    p_rfreeze = sub.add_parser(
        "rubric-freeze", help="freeze a graded rubric report as the rubric-lane baseline"
    )
    p_rfreeze.add_argument("--report", required=True, help="graded rubric report JSON")
    p_rfreeze.add_argument("--out", default=str(DEFAULT_RUBRIC_BASELINE_PATH))
    p_rfreeze.add_argument("--frozen-at", default=None, help="freeze label (default: UTC now)")

    p_rcheck = sub.add_parser(
        "rubric-check", help="compare a graded rubric report to the frozen baseline"
    )
    p_rcheck.add_argument("--report", required=True, help="graded rubric report JSON")
    p_rcheck.add_argument("--baseline", default=str(DEFAULT_RUBRIC_BASELINE_PATH))
    p_rcheck.add_argument("--out", default=None, help="also write the comparison JSON here")

    args = parser.parse_args(argv)
    try:
        if args.command == "freeze":
            frozen = freeze_golden_set(
                _section_files(Path(args.sections)),
                Path(args.out),
                frozen_at=args.frozen_at,
            )
            for fp in frozen:
                # ASCII-only: the Windows console commonly runs a cp125x codepage.
                print(
                    f"frozen {fp.section_id}: {len(fp.claims)} claims, "
                    f"{len(fp.sub_sections)} sub-sections -> "
                    f"{Path(args.out) / (fp.section_id + GOLDEN_SUFFIX)}"
                )
            return 0

        if args.command in ("rubric-freeze", "rubric-check"):
            graded = _read_json(Path(args.report), "rubric report")

            if args.command == "rubric-freeze":
                baseline = freeze_rubric_baseline(graded, frozen_at=args.frozen_at)
                atomic_write_json(baseline, Path(args.out), prefix="rubric_baseline_")
                print(
                    f"frozen rubric baseline: {len(baseline['report']['cells'])} cells "
                    f"under {baseline['judge_model']}@{baseline['judge_version']} "
                    f"-> {args.out}"
                )
                return 0

            comparison = compare_rubric_baseline(
                load_rubric_baseline(Path(args.baseline)), graded
            )
            print(json.dumps(comparison.to_dict(), indent=2, ensure_ascii=True))
            if args.out:
                atomic_write_json(
                    comparison.to_dict(), Path(args.out), prefix="rubric_regression_"
                )
            return 1 if comparison.regressed else 0

        golden = load_golden_set(Path(args.golden))
        report = compare_to_golden_set(golden, _section_files(Path(args.sections)))
        # ensure_ascii=True: console output must survive a cp125x codepage; the
        # --report file (below) keeps the readable UTF-8 serialisation.
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=True))
        if args.report:
            atomic_write_json(
                report.to_dict(), Path(args.report), prefix="regression_report_"
            )
        return 1 if report.regressed else 0
    except RegressionError as exc:
        print(f"regression check could not run (fail-closed): {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
