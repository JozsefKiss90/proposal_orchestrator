"""
The assessor response checkpoint — every raw response, written as it arrives.

Why this module exists
----------------------
A blind assessment is a long sequence of assessor calls — 30 cells plus 15
criterion samples on the profile this lane last ran — and it writes nothing
until the last one is graded.  One malformed response at call 44 therefore discarded
43 good ones, every one of them paid for out of a daily quota (observed
2026-10-06: a criterion sample that ended ``..."rationale": "...", }``, a
trailing comma, which :func:`~runner.json_extract.extract_first_json_object`
refuses as it must).

The checkpoint removes the loss without touching what the loss protects.  Every
raw response is written to a JSONL file the moment the transport returns it,
keyed by the hash of the prompt that drew it.  A later run opened in resume mode
replays those bytes through the same parsers, the same provenance builders and
the same verdict arithmetic, then goes live from the first call the checkpoint
does not cover.

What a replay is, and is not
----------------------------
A replayed response is the response the assessor actually gave — the same bytes,
parsed by the same code.  It is not a fresh draw, and a report built partly from
replayed calls must say so: :func:`~harness.blind_assessment.assess_candidate`
reads :meth:`ResponseCache.stats` and stamps ``replayed_calls`` and
``live_calls`` on the report.  Nothing here repairs, edits or synthesises a
response; a malformed one is checkpointed verbatim and fails again on replay,
exactly as it failed live.

Refusals, all fail-closed
-------------------------
* A checkpoint is never silently reused: opening an existing file without
  ``resume=True`` is refused, and resuming a missing one is refused.
* A checkpoint carries the binding it was drawn under — candidate hash, profile
  version, assessor pin, preflight pack-set hash and the sampling parameters.
  Resuming into a different binding is refused, naming every field that moved.
  Replaying one candidate's responses into another candidate's report would be
  fabrication, and the binding check is what makes that impossible.
* A malformed checkpoint record is refused, never skipped.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate; never a runtime gate.
    See ``harness/HARNESS.md``.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from harness.jsonl_log import JsonlLog

__all__ = [
    "CHECKPOINT_FORMAT_VERSION",
    "CHECKPOINT_HEADER_RECORD_TYPE",
    "CHECKPOINT_DISCARD_RECORD_TYPE",
    "CHECKPOINT_RESPONSE_RECORD_TYPE",
    "CacheBinding",
    "ResponseCache",
    "ResponseCacheError",
    "next_checkpoint_path",
]

#: Record types written into the checkpoint file.
CHECKPOINT_HEADER_RECORD_TYPE: str = "harness.assessor_response_checkpoint"
CHECKPOINT_RESPONSE_RECORD_TYPE: str = "harness.assessor_response"
CHECKPOINT_DISCARD_RECORD_TYPE: str = "harness.assessor_response_discarded"

#: Bumped when the on-disk shape changes; a resume refuses another version.
CHECKPOINT_FORMAT_VERSION: int = 1

_CHECKPOINT_NAME_RE = re.compile(
    r"^checkpoint_(?P<hash>[0-9a-f]{12})_(?P<seq>\d{4})\.jsonl$"
)


class ResponseCacheError(Exception):
    """A checkpoint could not be opened, read or resumed as asked."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def next_checkpoint_path(reports_dir: Path | str, digest: str) -> Path:
    """The next free ``checkpoint_<hash12>_<NNNN>.jsonl`` under *reports_dir*.

    Mirrors :func:`~harness.blind_assessment.next_report_path` so a run's
    checkpoint sits beside its report under the same candidate-hash stem, and so
    a checkpoint is never overwritten by the next run.
    """
    directory = Path(reports_dir)
    short = digest.split(":", 1)[1][:12] if ":" in digest else digest[:12]
    taken = 0
    if directory.is_dir():
        for existing in directory.iterdir():
            m = _CHECKPOINT_NAME_RE.match(existing.name)
            if m and m.group("hash") == short:
                taken = max(taken, int(m.group("seq")))
    return directory / f"checkpoint_{short}_{taken + 1:04d}.jsonl"


@dataclass(frozen=True)
class CacheBinding:
    """What a checkpoint was drawn under; a resume must match it exactly.

    Every field changes which prompts the run issues or what the responses
    mean.  The candidate hash and profile version decide the text and the
    rubrics; the assessor pin decides who answered; the preflight pack-set hash
    decides what each cell was shown; the sample counts and ``include_claims``
    decide how many prompts there are and what they carry.
    """

    candidate_hash: str = ""
    profile_version: str = ""
    assessor_pin: str = ""
    preflight_pack_set_hash: str = ""
    include_claims: bool = True
    n: int = 0
    criterion_samples: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_hash": self.candidate_hash,
            "profile_version": self.profile_version,
            "assessor_pin": self.assessor_pin,
            "preflight_pack_set_hash": self.preflight_pack_set_hash,
            "include_claims": self.include_claims,
            "n": self.n,
            "criterion_samples": self.criterion_samples,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CacheBinding":
        if not isinstance(data, Mapping):
            raise ResponseCacheError("checkpoint header carries no binding object.")
        return cls(
            candidate_hash=str(data.get("candidate_hash", "")),
            profile_version=str(data.get("profile_version", "")),
            assessor_pin=str(data.get("assessor_pin", "")),
            preflight_pack_set_hash=str(data.get("preflight_pack_set_hash", "")),
            include_claims=bool(data.get("include_claims", True)),
            n=int(data.get("n", 0)),
            criterion_samples=(
                None if data.get("criterion_samples") is None else int(data["criterion_samples"])
            ),
        )

    def differences(self, other: "CacheBinding") -> list[str]:
        """Field-by-field account of how *other* differs from this binding."""
        mine, theirs = self.to_dict(), other.to_dict()
        return [
            f"{key}: checkpoint {mine[key]!r} != this run {theirs[key]!r}"
            for key in mine
            if mine[key] != theirs[key]
        ]


class ResponseCache:
    """Raw assessor responses, written as they arrive and replayable in order.

    Consulted and fed by :meth:`harness.judge.Judge.raw_invoke`, which is the
    single seam every grader's assessor call passes through.  Responses are
    keyed by :func:`~harness.provenance.prompt_hash` of the ``(system, user)``
    pair and served first-in-first-out within a key, so the N samples of one
    prompt replay in the order they were drawn.

    Parameters
    ----------
    path:
        The JSONL checkpoint file.
    binding:
        The binding this run carries; written to a new file, checked against an
        existing one.
    resume:
        ``True`` replays the responses already in *path* before any live call.
        ``False`` (the default) requires *path* not to exist.
    clock:
        Timestamp source for the records (injectable for tests).
    """

    def __init__(
        self,
        path: Path | str,
        binding: CacheBinding,
        *,
        resume: bool = False,
        clock: Any = None,
    ) -> None:
        self._path = Path(path)
        self._binding = binding
        self._clock = clock or _utc_now
        self._pending: dict[str, deque[str]] = {}
        self._last: tuple[str, str] | None = None
        self.replayed = 0
        self.live = 0
        self.discarded = 0
        self._resumed = resume

        if resume:
            self._open_existing()
        else:
            if self._path.exists():
                raise ResponseCacheError(
                    f"checkpoint {self._path} already exists. A checkpoint is never "
                    f"appended to by accident: pass --resume to replay it, or name a "
                    f"different file."
                )
            self._log = JsonlLog(self._path, prefix="checkpoint_")
            self._log.append_dict(
                {
                    "record_type": CHECKPOINT_HEADER_RECORD_TYPE,
                    "format_version": CHECKPOINT_FORMAT_VERSION,
                    "opened_at": self._clock(),
                    "binding": binding.to_dict(),
                }
            )

    # -- state ------------------------------------------------------------ #

    @property
    def path(self) -> Path:
        return self._path

    @property
    def binding(self) -> CacheBinding:
        return self._binding

    @property
    def replayable(self) -> int:
        """Responses still queued for replay (0 once the checkpoint is spent)."""
        return sum(len(q) for q in self._pending.values())

    def stats(self) -> dict[str, Any]:
        """What a report records about this checkpoint."""
        return {
            "checkpoint_path": self._path.as_posix(),
            "resumed": self._resumed,
            "replayed_calls": self.replayed,
            "live_calls": self.live,
            "discarded_responses": self.discarded,
            "unreplayed_calls": self.replayable,
        }

    # -- the seam --------------------------------------------------------- #

    def take(self, prompt_hash: str) -> str | None:
        """The next replayable response for *prompt_hash*, or ``None``.

        ``None`` means the checkpoint does not cover this call and the caller
        must go live.  A served response is not re-recorded: it is already in
        the file, and recording it again would double it on the next resume.
        """
        queue = self._pending.get(prompt_hash)
        if not queue:
            return None
        self.replayed += 1
        response = queue.popleft()
        self._last = (prompt_hash, response)
        return response

    def record(self, prompt_hash: str, response: str) -> None:
        """Checkpoint one live response, verbatim, before the caller parses it.

        Verbatim and unconditional: a response that will fail to parse is
        written too, so a resume reproduces the run it is resuming — including
        its failure — rather than a tidied version of it.
        """
        self.live += 1
        self._last = (prompt_hash, response)
        self._log.append_dict(
            {
                "record_type": CHECKPOINT_RESPONSE_RECORD_TYPE,
                "prompt_hash": prompt_hash,
                "at": self._clock(),
                "chars": len(response),
                "sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
                "response": response,
            }
        )

    def discard_last(self, reason: str) -> None:
        """Mark the response just served or recorded as one the harness could not use.

        Called by the parsers, which are the only code that can tell.  A
        discarded response stays in the file verbatim — the checkpoint is a
        faithful record of what the assessor said — but it is never replayed,
        so a resume draws that call again instead of failing on it a second
        time.  Without this a run could never get past the response that
        killed it.
        """
        if self._last is None:
            return
        key, response = self._last
        self._last = None
        self.discarded += 1
        self._log.append_dict(
            {
                "record_type": CHECKPOINT_DISCARD_RECORD_TYPE,
                "prompt_hash": key,
                "at": self._clock(),
                "sha256": hashlib.sha256(response.encode("utf-8")).hexdigest(),
                "reason": reason,
            }
        )

    # -- resume ----------------------------------------------------------- #

    def _open_existing(self) -> None:
        if not self._path.is_file():
            raise ResponseCacheError(
                f"checkpoint {self._path} does not exist; there is nothing to resume."
            )
        try:
            self._log = JsonlLog(self._path, prefix="checkpoint_")
            records = list(self._log.records())
        except json.JSONDecodeError as exc:
            raise ResponseCacheError(
                f"checkpoint {self._path} holds a line that is not JSON: {exc}"
            ) from exc
        if not records:
            raise ResponseCacheError(f"checkpoint {self._path} is empty.")

        header = records[0]
        if header.get("record_type") != CHECKPOINT_HEADER_RECORD_TYPE:
            raise ResponseCacheError(
                f"{self._path} is not a {CHECKPOINT_HEADER_RECORD_TYPE!r} checkpoint."
            )
        if int(header.get("format_version", 0)) != CHECKPOINT_FORMAT_VERSION:
            raise ResponseCacheError(
                f"checkpoint {self._path} is format version "
                f"{header.get('format_version')!r}; this harness reads version "
                f"{CHECKPOINT_FORMAT_VERSION}."
            )
        recorded = CacheBinding.from_dict(header.get("binding", {}))
        moved = recorded.differences(self._binding)
        if moved:
            raise ResponseCacheError(
                f"checkpoint {self._path} was drawn under a different binding and "
                f"cannot be replayed into this run:\n  - " + "\n  - ".join(moved)
            )

        discarded = {
            (record.get("prompt_hash"), record.get("sha256"))
            for record in records[1:]
            if record.get("record_type") == CHECKPOINT_DISCARD_RECORD_TYPE
        }
        for index, record in enumerate(records[1:], start=1):
            if record.get("record_type") == CHECKPOINT_DISCARD_RECORD_TYPE:
                continue
            if record.get("record_type") != CHECKPOINT_RESPONSE_RECORD_TYPE:
                raise ResponseCacheError(
                    f"checkpoint {self._path} line {index + 1}: unknown record type "
                    f"{record.get('record_type')!r}."
                )
            key = record.get("prompt_hash")
            response = record.get("response")
            if not isinstance(key, str) or not key or not isinstance(response, str):
                raise ResponseCacheError(
                    f"checkpoint {self._path} line {index + 1}: a response record needs "
                    f"a 'prompt_hash' string and a 'response' string."
                )
            digest = record.get("sha256")
            if isinstance(digest, str) and digest:
                actual = hashlib.sha256(response.encode("utf-8")).hexdigest()
                if actual != digest:
                    raise ResponseCacheError(
                        f"checkpoint {self._path} line {index + 1}: the recorded "
                        f"response does not match its sha256 (recorded {digest[:12]}, "
                        f"actual {actual[:12]}) — the file has been edited."
                    )
            if (key, hashlib.sha256(response.encode("utf-8")).hexdigest()) in discarded:
                # Recorded, kept, and never served again: the parsers rejected
                # it in the run that drew it, and replaying it would only
                # reproduce that rejection.
                continue
            self._pending.setdefault(key, deque()).append(response)
