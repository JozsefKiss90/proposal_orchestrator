"""
The §10.5 materiality classifier + its ledger-anchored calibration (E3).

The escaped-claim detector (:mod:`harness.claim_ledger`) is self-defeating
without a materiality threshold: prose is full of transitions, framing, and
definitional/method description that legitimately carries no ``claim_id``, and
flagging all of it floods the "unledgered assertion" set until the check is
ignored.  This module owns the bar that separates a **material claim** — one
CLAUDE.md §10.5 requires to be attributed or flagged — from non-material prose.

Two anchors, per the ticket:

* **Constitutional (what).**  §10.5, quoted verbatim in the classifier prompt
  (:data:`SECTION_10_5`): *"Unattributed claims must be flagged, not asserted."*
  The constitution never defines *which* sentences count, so §10.5 alone cannot
  drive a classifier.
* **Empirical (which).**  The engine's own 406-entry claim ledger is its
  enumeration of what it treats as material-and-attributable.
  :func:`seed_materiality_positives` turns real ``claim_summary`` values into
  auto-labeled positive examples (this is the *engine's* enumeration, not an AI
  fabricating gold labels); negative examples (framing / transition /
  definitional spans) are seeded as **unlabeled candidates**
  (:func:`seed_negative_candidates`) for a *human* to label — the E1.5
  discipline: an AI labeling gold for an AI judge would reintroduce the
  grader–generator correlation the harness exists to avoid.

:func:`calibrate_materiality` measures the deployed classifier (the same
:func:`classify_materiality` path the pipeline runs) against the labeled set,
reusing the E1.5 :class:`~harness.calibration.ConfusionMatrix`.  One guard is
load-bearing: with **zero labeled negatives** the matrix's precision is a
spurious ``tp/(tp+0) = 1.0``, so :class:`MaterialityCalibration` forces
``precision`` to ``None`` until real negatives exist — recall over the
auto-positives is computable day one (it bounds the missed-escape risk), but
precision must wait for human-labeled negatives.  A judge repin re-opens the
uncalibrated state (:meth:`MaterialityCalibration.applies_to`), mirroring E1.5.

Like E1.5's :func:`~harness.calibration.calibrate_with_judge`, the classifier
helpers here do not route property keys; the pipeline entry points that judge
*artifacts* (:mod:`harness.claim_ledger`) route each assertion id through
:func:`~harness.routing.assert_judgeable` themselves.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA substrate; reads Tier-5 claim
    ledgers only to seed examples and writes only harness-owned materiality-set
    files.  Never a runtime gate.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from runner.atomic_write import atomic_write_text
from harness.calibration import ConfusionMatrix, confusion_from_labels
from harness.faithfulness import INDEPENDENCE_PREAMBLE, build_claim_user_prompt
from harness.gold_set import TO_BE_LABELED
from harness.judge import Judge, JudgeConfig, MajorityJudgeResult
from harness.verdict import MajorityVerdict, Verdict, validate_sample_count

__all__ = [
    "MATERIALITY_METRIC",
    "SECTION_10_5",
    "ORIGIN_LEDGER",
    "ORIGIN_PROSE",
    "MaterialityError",
    "MaterialityExample",
    "normalize_text",
    "seed_materiality_positives",
    "seed_negative_candidates",
    "write_materiality_template",
    "load_materiality_set",
    "materiality_set_hash",
    "build_materiality_prompt",
    "classify_materiality",
    "MaterialityCalibration",
    "calibrate_materiality",
]

#: The metric name stamped on every materiality verdict and its provenance.
MATERIALITY_METRIC: str = "claim_materiality"

#: CLAUDE.md §10.5, verbatim — the constitutional mandate the classifier
#: operationalizes.  Quoted in the prompt so the judge applies the repo's own
#: bar, not a generic notion of importance.
SECTION_10_5: str = (
    "All major outputs produced by agents must be traceable to their tiered "
    "inputs. An agent must be able to identify, for each material claim in its "
    "output, the Tier 1-4 source from which the claim derives. Unattributed "
    "claims must be flagged, not asserted."
)

#: Example origins.  ``ledger`` positives carry the engine's own enumeration;
#: ``prose`` candidates are spans drawn from section prose for human labeling.
ORIGIN_LEDGER: str = "ledger"
ORIGIN_PROSE: str = "prose"


class MaterialityError(Exception):
    """A materiality set is malformed, unlabeled where required, or inconsistent."""


_WHITESPACE_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Lowercase and whitespace-collapse *text* for dedup comparisons.

    Shared by the positive seeder here and the assertion dedup in
    :mod:`harness.claim_ledger` — one notion of "the same sentence."
    """
    return _WHITESPACE_RE.sub(" ", str(text)).strip().lower()


# --------------------------------------------------------------------------- #
# Example model
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MaterialityExample:
    """One labeled (or to-be-labeled) materiality example.

    Attributes
    ----------
    example_id:
        Stable identifier within the set.
    text:
        The assertion/span under classification.
    material:
        The ground-truth label — ``True`` (a material claim per §10.5),
        ``False`` (framing / transition / definitional prose), or ``None``
        (unlabeled candidate awaiting a human).  Ledger positives are the one
        sanctioned auto-label: they are the engine's own enumeration.
    origin:
        :data:`ORIGIN_LEDGER` or :data:`ORIGIN_PROSE`.
    section_id:
        The section the example was drawn from, when known.
    claim_id:
        For ledger positives, the originating claim's ``entry_key``.
    note:
        Free-form human note.
    """

    example_id: str
    text: str
    material: bool | None = None
    origin: str = ORIGIN_LEDGER
    section_id: str | None = None
    claim_id: str | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if not str(self.example_id).strip():
            raise MaterialityError("MaterialityExample.example_id must be non-empty.")
        if not str(self.text).strip():
            raise MaterialityError(
                f"MaterialityExample {self.example_id!r}: text must be non-empty."
            )
        if self.material is not None and not isinstance(self.material, bool):
            raise MaterialityError(
                f"MaterialityExample {self.example_id!r}: material must be a bool "
                f"or None (unlabeled); got {self.material!r}."
            )

    @property
    def is_labeled(self) -> bool:
        """``True`` iff :attr:`material` carries a ground-truth label."""
        return self.material is not None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "example_id": self.example_id,
            "text": self.text,
            "material": self.material,
            "origin": self.origin,
            "section_id": self.section_id,
            "claim_id": self.claim_id,
            "note": self.note,
        }
        if not self.is_labeled:
            d["labeling_status"] = TO_BE_LABELED
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MaterialityExample":
        if not isinstance(d, dict):
            raise MaterialityError(
                f"materiality example must be an object; got {type(d).__name__}"
            )
        return cls(
            example_id=str(d.get("example_id", "")),
            text=str(d.get("text", "")),
            material=d.get("material"),
            origin=str(d.get("origin", ORIGIN_LEDGER)),
            section_id=d.get("section_id"),
            claim_id=d.get("claim_id"),
            note=str(d.get("note", "")),
        )


# --------------------------------------------------------------------------- #
# Seeding — positives from the ledger, negative candidates from prose
# --------------------------------------------------------------------------- #


def seed_materiality_positives(
    claims: Sequence[Any],
    *,
    section_id: str = "",
    prefix: str = "mat-pos",
) -> list[MaterialityExample]:
    """Turn a section's claim summaries into auto-labeled positive examples.

    *claims* are :class:`~harness.status_faithfulness.SectionClaim` objects (or
    anything with ``claim_summary`` / ``entry_key``).  The ledger is the
    engine's own enumeration of material-and-attributable content, so labeling
    these ``material=True`` fabricates nothing.  Summaries are de-duplicated by
    normalized text (real ledgers repeat entries across drafting blocks —
    excellence carries 9 true duplicates) so the calibration set does not
    over-weight repeated claims.
    """
    out: list[MaterialityExample] = []
    seen: set[str] = set()
    for c in claims:
        summary = str(getattr(c, "claim_summary", "")).strip()
        if not summary:
            continue
        key = normalize_text(summary)
        if key in seen:
            continue
        seen.add(key)
        out.append(
            MaterialityExample(
                example_id=f"{prefix}-{len(out) + 1:03d}",
                text=summary,
                material=True,
                origin=ORIGIN_LEDGER,
                section_id=section_id or None,
                claim_id=getattr(c, "entry_key", None),
            )
        )
    return out


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _sentences(text: str) -> list[str]:
    """Split prose into rough sentences, dropping headings and empties."""
    out: list[str] = []
    for para in text.split("\n\n"):
        para = para.strip()
        if not para or para.lstrip().startswith("#"):
            continue
        for s in _SENTENCE_SPLIT_RE.split(para.replace("\n", " ")):
            s = s.strip()
            if len(s) >= 40:  # too-short fragments are not useful candidates
                out.append(s)
    return out


def seed_negative_candidates(
    prose_texts: Sequence[str],
    *,
    limit: int = 30,
    section_id: str = "",
    prefix: str = "mat-neg",
) -> list[MaterialityExample]:
    """Draw deterministic, **unlabeled** negative-candidate spans from prose.

    Emits evenly-spaced sentences from *prose_texts* with ``material=None`` — a
    human then keeps/labels the genuine framing/transition/definitional spans
    ``False`` (and re-labels any that are actually material ``True``).  The
    label is deliberately never fabricated here: unlike the ledger positives,
    "this sentence is non-material" is not something the engine ever asserted.
    """
    sentences: list[str] = []
    seen: set[str] = set()
    for text in prose_texts:
        for s in _sentences(str(text)):
            key = normalize_text(s)
            if key in seen:
                continue
            seen.add(key)
            sentences.append(s)
    if not sentences or limit <= 0:
        return []
    k = min(limit, len(sentences))
    if k == 1:
        picks = [0]
    else:
        picks = []
        seen_i: set[int] = set()
        for j in range(k):
            i = round(j * (len(sentences) - 1) / (k - 1))
            if i not in seen_i:
                seen_i.add(i)
                picks.append(i)
    return [
        MaterialityExample(
            example_id=f"{prefix}-{n + 1:03d}",
            text=sentences[i],
            material=None,  # human label pending — never fabricated
            origin=ORIGIN_PROSE,
            section_id=section_id or None,
        )
        for n, i in enumerate(picks)
    ]


# --------------------------------------------------------------------------- #
# Set I/O (JSONL, mirroring the E1.5 gold set)
# --------------------------------------------------------------------------- #


def write_materiality_template(
    examples: Sequence[MaterialityExample], path: Path | str
) -> None:
    """Write *examples* as a JSONL materiality set (atomic, one per line)."""
    body = "".join(
        json.dumps(e.to_dict(), ensure_ascii=False) + "\n" for e in examples
    )
    atomic_write_text(body, Path(path), prefix="matset_")


def load_materiality_set(
    path: Path | str,
    *,
    require_labeled: bool = False,
) -> tuple[MaterialityExample, ...]:
    """Load a materiality set from a ``.jsonl`` file.

    With *require_labeled* (calibration mode) every example must carry a
    ``material`` label; an unlabeled one raises :class:`MaterialityError` —
    the same fail-closed posture as the E1.5 gold set.
    """
    p = Path(path)
    if not p.is_file():
        raise MaterialityError(f"materiality set file not found: {p}")
    examples: list[MaterialityExample] = []
    seen: set[str] = set()
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise MaterialityError(f"materiality set {p} has a malformed line: {exc}") from exc
        ex = MaterialityExample.from_dict(raw)
        if ex.example_id in seen:
            raise MaterialityError(f"duplicate example_id in materiality set: {ex.example_id!r}")
        seen.add(ex.example_id)
        examples.append(ex)
    if require_labeled:
        missing = [e.example_id for e in examples if not e.is_labeled]
        if missing:
            raise MaterialityError(
                f"materiality set {p} has {len(missing)} unlabeled example(s) "
                f"({missing[:5]}{'…' if len(missing) > 5 else ''}); a human must "
                f"label 'material' on every example before calibration."
            )
    return tuple(examples)


def materiality_set_hash(examples: Iterable[MaterialityExample]) -> str:
    """Stable ``sha256:`` hash over the set's labeled content.

    Hashes ``(example_id, text, material)`` per example — a re-label or a text
    edit changes the hash (a calibration recorded against an old hash is
    visibly stale); a note edit does not.
    """
    h = hashlib.sha256()
    for e in examples:
        h.update(
            json.dumps([e.example_id, e.text, e.material], ensure_ascii=False).encode("utf-8")
        )
        h.update(b"\x00")
    return f"sha256:{h.hexdigest()}"


# --------------------------------------------------------------------------- #
# The classifier — one path for pipeline and calibration
# --------------------------------------------------------------------------- #

_MATERIALITY_STANDARD: str = (
    "Your single task: decide whether the ASSERTION below is a MATERIAL CLAIM "
    "under this repository's constitution (CLAUDE.md §10.5):\n\n"
    f'"{SECTION_10_5}"\n\n'
    "A MATERIAL claim asserts a specific fact that would need a source: a "
    "project fact (who, where, what equipment, what prior work), a call or "
    "programme constraint, a quantitative value (duration, budget, KPI, "
    "percentage), a commitment (deliverable, milestone, activity), or a "
    "capability/qualification. Example of the form: a one-line factual claim "
    "such as 'the project is a 24-month action hosted at university X'.\n\n"
    "NOT material: transitions and framing ('the following sub-sections "
    "describe...'), definitional or method description that introduces a "
    "general concept without asserting a project-specific fact, restatements "
    "of the evaluation criteria themselves, and rhetorical connective tissue.\n\n"
    "Judge the assertion text alone — not whether it is true, and not whether "
    "a source exists for it. When genuinely in doubt, answer \"passed\": true "
    "(over-flagging is reviewable; a silently missed material claim is not)."
)

_JSON_INSTRUCTION: str = (
    "\n\nReturn ONLY a JSON object, no prose before or after:\n"
    '{"passed": <true if the assertion is a MATERIAL claim, false otherwise>, '
    '"score": <0.0-1.0 confidence>, '
    '"rationale": "<one sentence>"}'
)


def build_materiality_prompt(text: str) -> tuple[str, str]:
    """Return the ``(system_prompt, user_prompt)`` for one materiality question."""
    system_prompt = INDEPENDENCE_PREAMBLE + _MATERIALITY_STANDARD + _JSON_INSTRUCTION
    user_prompt = build_claim_user_prompt(
        text,
        "(classification of the claim text itself — no source material applies)",
        question="Is the CLAIM a MATERIAL claim under the standard? Return the JSON verdict.",
        material_label="CONTEXT",
    )
    return system_prompt, user_prompt



def classify_materiality(
    judge: Judge,
    text: str,
    *,
    property_key: str,
    n: int = 1,
) -> Verdict | MajorityVerdict:
    """Classify one assertion as material / non-material (boolean verdict).

    The single classifier path shared by the escaped-claim pipeline and
    :func:`calibrate_materiality`, so the calibration measures exactly the
    classifier that runs in production.  ``passed=True`` means *material*.
    Callers route *property_key* (:func:`~harness.routing.assert_judgeable`)
    before invoking, as the E1.5 calibration precedent does.
    """
    validate_sample_count(n)
    system_prompt, user_prompt = build_materiality_prompt(text)
    if n == 1:
        return judge.evaluate(
            system_prompt,
            user_prompt,
            metric=MATERIALITY_METRIC,
            property_key=property_key,
        ).verdict
    result: MajorityJudgeResult = judge.evaluate_majority(
        system_prompt,
        user_prompt,
        metric=MATERIALITY_METRIC,
        property_key=property_key,
        n=n,
    )
    return result.majority


# --------------------------------------------------------------------------- #
# Calibration — recall now, precision once negatives are labeled
# --------------------------------------------------------------------------- #


def _default_clock() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class MaterialityCalibration:
    """One calibration run of the materiality classifier, keyed to the judge pin.

    ``recall`` (of the material class) is meaningful as soon as the ledger
    positives exist.  ``precision`` is **forced to ``None`` when the labeled
    set contains no negatives** — with only positives the confusion matrix
    would report a spurious ``tp/(tp+0) = 1.0``, blessing a classifier that
    flags everything.  ``labeled_negatives`` makes the basis explicit.
    """

    judge_model: str
    judge_version: str
    recall: float | None
    precision: float | None
    confusion: ConfusionMatrix
    n_examples: int
    labeled_negatives: int
    set_hash: str
    timestamp: str | None = None

    def applies_to(self, config: JudgeConfig) -> bool:
        """Whether this calibration applies to *config*'s exact model+version."""
        return (
            self.judge_model == config.model
            and self.judge_version == config.version
        )

    @property
    def has_negatives(self) -> bool:
        return self.labeled_negatives > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_type": "materiality_calibration",
            "metric": MATERIALITY_METRIC,
            "judge_model": self.judge_model,
            "judge_version": self.judge_version,
            "recall": self.recall,
            "precision": self.precision,
            "labeled_negatives": self.labeled_negatives,
            "n_examples": self.n_examples,
            "set_hash": self.set_hash,
            "confusion": self.confusion.to_dict(),
            "timestamp": self.timestamp,
        }


def calibrate_materiality(
    examples: Sequence[MaterialityExample],
    judge: Judge,
    *,
    clock: Callable[[], str] | None = None,
) -> MaterialityCalibration:
    """Run the deployed classifier over a fully-labeled set and measure it.

    Fail-closed on any unlabeled example.  Every prediction is a real
    :func:`classify_materiality` call (single verdict; provenance logs via the
    judge's attached log).  A verdict with no boolean answer raises — the
    classifier must say material yes/no, never shrug.

    Returns a :class:`MaterialityCalibration` with recall from the confusion
    matrix and precision only when labeled negatives exist (see the class
    docstring for why positives-only precision would be spurious).
    """
    unlabeled = [e.example_id for e in examples if not e.is_labeled]
    if unlabeled:
        raise MaterialityError(
            f"{len(unlabeled)} example(s) are unlabeled "
            f"({unlabeled[:5]}{'…' if len(unlabeled) > 5 else ''}); calibration "
            f"requires a fully-labeled set (label or drop them first)."
        )
    if not examples:
        raise MaterialityError("cannot calibrate on an empty materiality set.")

    truth: list[bool] = []
    pred: list[bool] = []
    for e in examples:
        verdict = classify_materiality(
            judge, e.text, property_key=e.example_id, n=1
        )
        if verdict.passed is None:
            raise MaterialityError(
                f"example {e.example_id!r}: classifier returned no boolean "
                f"'material' verdict (passed is None); cannot calibrate."
            )
        truth.append(bool(e.material))
        pred.append(bool(verdict.passed))

    confusion = confusion_from_labels(truth, pred)
    labeled_negatives = sum(1 for t in truth if not t)
    return MaterialityCalibration(
        judge_model=judge.config.model,
        judge_version=judge.config.version,
        recall=confusion.recall,
        # Positives-only precision is spuriously 1.0 (tp/(tp+0)); withhold it
        # until human-labeled negatives exist.
        precision=confusion.precision if labeled_negatives > 0 else None,
        confusion=confusion,
        n_examples=len(examples),
        labeled_negatives=labeled_negatives,
        set_hash=materiality_set_hash(examples),
        timestamp=(clock or _default_clock)(),
    )
