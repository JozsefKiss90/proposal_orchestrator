"""
Judge-verdict provenance — the audit trail for every score (E1).

The guardrails require, for every judge verdict, a provenance record carrying
``{judge_model, judge_version, prompt_hash, score, rationale}`` — the same
discipline the pipeline already applies to ``reinstantiation_provenance.json``
and the decision log.  It exists so an ``Inferred`` score can be traced back to
*which* pinned judge said it, on *which* prompt, and why: without that, a
merge-advisory score is an unattributable opinion, and E1.5's judge-reliability
calibration (precision/recall vs a gold set) has nothing to calibrate against.

This module owns three things and nothing else:

* :func:`prompt_hash` — a stable content hash of the (system, user) prompt pair,
  so two verdicts on the same prompt are provably comparable and a prompt change
  is visible as a hash change.
* :class:`ProvenanceRecord` — the immutable five-field record (plus supplementary
  context), which cannot be constructed with a non-``Inferred`` evidence type.
* :class:`ProvenanceLog` — an append-only JSONL sink written atomically via the
  house ``atomic_write`` helper (Python owns every write, §9/§17.5.3).

It performs no judging and makes no network call; the judge
(:mod:`harness.judge`) builds records from its :class:`~harness.verdict.Verdict`
outputs and appends them here.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate; writes only to the
    harness's own report directory, never to a canonical Tier 1–5 artifact or a
    gate result.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runner.atomic_write import atomic_write_text
from harness.verdict import EVIDENCE_TYPE_INFERRED, Verdict

__all__ = [
    "REQUIRED_PROVENANCE_FIELDS",
    "prompt_hash",
    "ProvenanceRecord",
    "ProvenanceLog",
]

#: The five fields the guardrails require on every verdict's provenance.
#: :meth:`ProvenanceRecord.to_dict` is asserted to include exactly these.
REQUIRED_PROVENANCE_FIELDS: frozenset[str] = frozenset(
    {"judge_model", "judge_version", "prompt_hash", "score", "rationale"}
)


def prompt_hash(system_prompt: str, user_prompt: str) -> str:
    """Return a stable ``sha256:`` hash of the (system, user) prompt pair.

    Deterministic and order-sensitive: the two prompts are joined with a NUL
    delimiter (which cannot occur in either) so that moving text across the
    boundary changes the hash.  Two verdicts sharing a ``prompt_hash`` were
    produced from byte-identical prompts and are directly comparable; a changed
    hash is a changed question.
    """
    h = hashlib.sha256()
    h.update(system_prompt.encode("utf-8"))
    h.update(b"\x00")
    h.update(user_prompt.encode("utf-8"))
    return f"sha256:{h.hexdigest()}"


@dataclass(frozen=True)
class ProvenanceRecord:
    """One immutable provenance record for a single judge verdict.

    The five required fields (:data:`REQUIRED_PROVENANCE_FIELDS`) are the first
    five attributes; the rest are supplementary context that makes the record
    self-describing without changing the guarantee.

    Attributes
    ----------
    judge_model:
        The pinned judge model identifier (non-empty).  A *non-drafter* model —
        grader/generator independence is enforced in :mod:`harness.judge`, not
        here, but the recorded value is what makes that auditable after the fact.
    judge_version:
        The pinned judge version tag (non-empty).  A repin re-opens E1.5's
        advisory-only state, so the version must be recorded on every verdict.
    prompt_hash:
        Output of :func:`prompt_hash` for the exact prompts judged.
    score:
        The verdict's numeric score, or ``None`` for a boolean-only verdict.
    rationale:
        The judge's stated reason.
    metric, property_key, passed, sample_index:
        Supplementary context copied from the verdict.
    evidence_type:
        Always :data:`EVIDENCE_TYPE_INFERRED`; rejected otherwise.
    timestamp:
        Optional ISO-8601 string.  Injected by the caller (kept out of the
        required set and defaulting to ``None`` so records stay reproducible in
        tests); the judge stamps it from an injectable clock.
    """

    judge_model: str
    judge_version: str
    prompt_hash: str
    score: float | None
    rationale: str
    metric: str | None = None
    property_key: str | None = None
    passed: bool | None = None
    sample_index: int | None = None
    evidence_type: str = EVIDENCE_TYPE_INFERRED
    timestamp: str | None = None

    def __post_init__(self) -> None:
        if self.evidence_type != EVIDENCE_TYPE_INFERRED:
            raise ValueError(
                f"ProvenanceRecord.evidence_type must be "
                f"{EVIDENCE_TYPE_INFERRED!r} (a judge verdict is Inferred, never "
                f"Confirmed); got {self.evidence_type!r}."
            )
        if not str(self.judge_model).strip():
            raise ValueError(
                "ProvenanceRecord.judge_model must be non-empty — an "
                "unattributable score cannot be calibrated (E1.5)."
            )
        if not str(self.judge_version).strip():
            raise ValueError(
                "ProvenanceRecord.judge_version must be non-empty — a repin "
                "re-opens the advisory-only state, so the version is required."
            )

    @classmethod
    def from_verdict(
        cls,
        verdict: Verdict,
        *,
        judge_model: str,
        judge_version: str,
        prompt_hash: str,
        timestamp: str | None = None,
    ) -> "ProvenanceRecord":
        """Build a record from a :class:`~harness.verdict.Verdict` + judge identity.

        The judge's score/rationale/status come from the verdict; the pinned
        model+version and the prompt hash come from the invocation.  This is the
        one path the judge uses, guaranteeing every verdict yields a record.
        """
        return cls(
            judge_model=judge_model,
            judge_version=judge_version,
            prompt_hash=prompt_hash,
            score=verdict.score,
            rationale=verdict.rationale,
            metric=verdict.metric,
            property_key=verdict.property_key,
            passed=verdict.passed,
            sample_index=verdict.sample_index,
            evidence_type=verdict.evidence_type,
            timestamp=timestamp,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable record.

        The five :data:`REQUIRED_PROVENANCE_FIELDS` are always present.
        """
        return {
            "judge_model": self.judge_model,
            "judge_version": self.judge_version,
            "prompt_hash": self.prompt_hash,
            "score": self.score,
            "rationale": self.rationale,
            "metric": self.metric,
            "property_key": self.property_key,
            "passed": self.passed,
            "sample_index": self.sample_index,
            "evidence_type": self.evidence_type,
            "timestamp": self.timestamp,
        }


class ProvenanceLog:
    """Append-only JSONL log of :class:`ProvenanceRecord` — one record per line.

    Writes are atomic (temp file + rename via :func:`runner.atomic_write`): the
    whole log is re-serialized and swapped over on every append, so a reader
    never observes a torn line.  Volume is low (verdicts per QA run), so the
    read-all/rewrite cost is immaterial and buys torn-write safety plus trivial
    testability.  The log is an out-of-band artifact — it is *not* a Tier 4 gate
    result and nothing in :mod:`runner` reads it.

    Parameters
    ----------
    path:
        Destination ``.jsonl`` file.  Parent directories are created on first
        append.
    """

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        # In-memory mirror seeded from any pre-existing log so appends are
        # order-preserving across process restarts without re-reading per call.
        self._records: list[dict[str, Any]] = self._load_existing()

    @property
    def path(self) -> Path:
        return self._path

    def _load_existing(self) -> list[dict[str, Any]]:
        if not self._path.is_file():
            return []
        out: list[dict[str, Any]] = []
        text = self._path.read_text(encoding="utf-8")
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
        return out

    def append(self, record: ProvenanceRecord) -> None:
        """Append one record and atomically rewrite the log."""
        self._records.append(record.to_dict())
        self._flush()

    def _flush(self) -> None:
        body = "".join(
            json.dumps(rec, ensure_ascii=False) + "\n" for rec in self._records
        )
        atomic_write_text(body, self._path, prefix="provenance_")

    def records(self) -> list[dict[str, Any]]:
        """Return a copy of every logged record, in append order."""
        return list(self._records)

    def __len__(self) -> int:
        return len(self._records)
