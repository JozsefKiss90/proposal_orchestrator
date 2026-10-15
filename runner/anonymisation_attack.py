"""The closed-book model attack, the second half of stage A5 (AN8b).

AN8b of ``.scratch/msca-dn-anonymisation/tickets.md``, stage A5 of
``plans/msca_dn_anonymisation_handoff_2026-10-14.md``. A Bedrock model tries to
re-identify the derivative. Code scores its guesses against the entity
dictionary, privately, under the policy's re-identification thresholds (O3).
The deterministic leak scan (AN8a) is the first half.

Who attacks
-----------
A Claude model other than A3's, so the rewriter does not grade itself (O2).
The attack refuses a model outside the Claude family, and one whose canonical id (:func:`runner.model_ids.canonical_model_id`)
equals the A3 model's, so no Bedrock wrapping of the rewriter passes. Its
prompt, :data:`SYSTEM_PROMPT`, is its own. It runs closed book: the backend
carries no tools, and the request holds only the derivative's text.

What the model sees
-------------------
The derivative's passages, as :func:`runner.anonymisation_rewrite.passages`
cuts them. Re-identification works
across passages, so the passages are sent in windows of up to
:data:`MAX_WINDOW_CHARS` characters, the whole document when it fits. The
model is asked about every target the policy's threshold names, and answers
each with a guess or an abstention. A guess carries a confidence, the passage
that gave it away, and a quote from it.

How a guess is scored
---------------------
Against the dictionary, by the matcher A2 and the leak scan use, with every
normalisation on:

``correct``
    the guess matches an edited entry of the target's category.
``review``
    the guess matches an edited entry of another category, or an identifier
    pattern, or shares a word of four or more letters with an entry of the
    target's category that the derivative no longer contains. The last case
    catches a partial name such as a city without its university. A word the
    derivative still holds, such as "University", is not evidence. Review does
    not fail the derivative; the operator reads it, as for the leak scan.
``wrong``
    none of these.
``abstained``
    no guess, or no answer for the target in a window.
``admissible``
    any guess at a target the policy keeps, such as the country set. It is not
    scored.

The verdict is ``failed`` if any target fails, else ``incomplete`` if a reply
or a guess was malformed, else ``passed``. A malformed reply is recorded, never
repaired (CLAUDE.md §17.5.4).

A target fails when the entities its correct guesses name outnumber its
``max_correct_guesses``; a guess repeated across windows counts once. A target
abstains when no window drew a guess at it.

A correct guess sends its passage back to A3. Passage ids are positional, so
an id of the attacked derivative may name other text in A3's input once a later
stage has changed the page. The passage sent back is therefore the one passage
of A3's input that holds the guess's quote. The flags file maps it to the
target's category plus every category the policy flags rather than edits (the
niche topics, which the policy rewrites only where A5 shows they identify). It
is the ``flags`` argument of :func:`runner.anonymisation_rewrite.rewrite`. A
correct guess whose quote is missing from the passage it cites, or from A3's
input, or found there in several passages, still fails the derivative but
cannot be flagged. The report counts it, and the operator locates it.

The policy must be resolved
---------------------------
A threshold declared ``Unresolved`` refuses the run before any call. The
committed policy leaves the research group's threshold Unresolved (AN0 known
gap), so the attack cannot run on it until the operator sets one.

Checkpoints and the token budget
--------------------------------
As in A3. Each reply is checkpointed per window before it is scored; a re-run
reads the checkpoint, and refuses one whose request differs. The report, the
details and the flags are derived from the checkpoints, so a re-run rewrites
them byte-equal. Each call reserves its request bytes plus
:data:`runner.anonymisation_rewrite.REQUEST_OVERHEAD_TOKENS` plus
``max_output_tokens`` before it is made. A run that cannot reserve its next
call stops and writes nothing but checkpoints.

What is private
---------------
The checkpoints, the details (guesses, quotes, passage ids, matched entry ids)
and the flags (passage ids). The report holds counts, hashes and model ids,
and no text or passage id, so its counts can reach the public acceptance
record (A7). It is still written beside the others: every path inside this
repository is refused. The module logs nothing.

What it does not show
---------------------
A closed-book model is not a motivated human expert in the field. A pass says
only that this model, with this prompt, named no one. The operator's own read
in A7 is the last line. The report says so.

Constitutional standing: an authoring tool, not a runtime component. It
evaluates no gate and writes no Tier 5 artifact. Its model calls go through the
runner's Bedrock Converse transport, with no tools.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional, Sequence

from runner import anonymisation_intake as intake
from runner import anonymisation_rewrite as rw
from runner.anonymisation_matching import EntityDictionary, find_matches
from runner.anonymisation_policy import LoadedPolicy, require_hash
from runner.atomic_write import atomic_write_text, canonical_json_bytes
from runner.model_ids import canonical_model_id

SCHEMA = "reidentification_report/1"
RECORD_TYPE = "reidentification_report"
DETAILS_SCHEMA = "reidentification_details/1"
FLAGS_SCHEMA = "anonymisation_a3_flags/1"
CHECKPOINT_SCHEMA = "reidentification_checkpoint/1"

REPORT_FILE = "reidentification_report.json"
DETAILS_FILE = "reidentification_details.json"
FLAGS_FILE = "a3_flags.json"
CHECKPOINT_DIR = "checkpoints"

#: The most characters of passage text one request carries.
MAX_WINDOW_CHARS = 60_000
#: A word shorter than this is never evidence of a partial guess.
MIN_PARTIAL_WORD = 4

#: What the model is asked for each target the policy's threshold may name.
TARGET_QUESTIONS: dict[str, str] = {
    "coordinating_institution": "the institution that coordinates the network",
    "partner": "any other institution or company taking part in the network",
    "supervisor": "any supervisor or other named researcher",
    "country_set": "the countries the network spans",
    "project_acronym": "the project's acronym or title",
    "research_group": "the research group, department or laboratory behind the proposal",
}

LIMIT = (
    "A closed-book model is not a motivated human expert in the field. A pass shows only that "
    "this model, with this prompt and no tools or retrieval, named no protected target. The "
    "operator's own read at A7 is the last line."
)

SCORING_RULE = (
    "A guess is correct when the dictionary matcher finds an edited entry of the target's "
    "category in it. It is review when it matches another category's entry or an identifier "
    "pattern, or shares a word of four or more letters with an entry of the target's category "
    "that the derivative no longer contains. Review does not fail. A guess at a target the "
    "policy keeps is admissible and not scored. A target fails when the entities its correct "
    "guesses name outnumber max_correct_guesses."
)

_GUESS_KEYS = frozenset({"target", "guess", "confidence", "passage_id", "evidence"})
_CHECKPOINT_KEYS = ("window_id", "request_sha256", "model_id", "content", "tool_calls",
                    "usage", "tokens_charged", "reservation")
_OUTCOMES = ("correct", "review", "wrong", "admissible", "abstained")
_WORD = re.compile(r"\w+")

SYSTEM_PROMPT = """\
You are testing whether an anonymised research proposal can be traced back to
the real network behind it. Use only what you already know. You have no tools
and no search.

The user message is a JSON object with passages of the proposal, each with an
id, and the targets to identify. Names, institutions and places were replaced
with codes such as "Supervisor S01" or "Beneficiary B1". A code is not an
answer: name the real entity, or abstain.

For each target, give your best real-world guess, or null if you cannot tell.
A target may take several guesses, one entry each. For each guess give:
- confidence: a number from 0 to 1;
- passage_id: the passage that gave it away;
- evidence: a short exact quote from that passage.

Reply with one JSON object and nothing else, no code fence:
{"guesses": [{"target": "", "guess": "", "confidence": 0.0,
              "passage_id": "", "evidence": ""}]}
"""


class AttackRefused(RuntimeError):
    """The attack cannot run as asked. No model call was made for the refused step."""


@dataclass(frozen=True)
class AttackResult:
    status: str
    """``complete`` or ``stopped_at_token_budget``."""
    verdict: Optional[str]
    """``passed``, ``failed`` or ``incomplete``; None when the run stopped."""
    report: Optional[Path]
    details: Optional[Path]
    flags: Optional[Path]
    tokens_used: int
    calls_made: int
    windows_from_checkpoint: int
    windows_pending: int


@dataclass(frozen=True)
class _Target:
    name: str
    category: str
    max_correct: Optional[int]
    admissible: bool


# --------------------------------------------------------------------------- #
# Targets and windows
# --------------------------------------------------------------------------- #


def targets(policy: LoadedPolicy) -> list[_Target]:
    """The policy's re-identification targets, refused if any is Unresolved or unknown."""
    out: list[_Target] = []
    for raw in policy.record["reidentification_threshold"]["targets"]:
        name = raw["target"]
        if raw["declared_status"] == "Unresolved":
            raise AttackRefused(
                f"the policy's threshold for {name} is Unresolved; the attack does not run "
                f"until the operator sets it (O3)"
            )
        if name not in TARGET_QUESTIONS:
            raise AttackRefused(f"the policy names target {name!r}, which the attack cannot ask")
        out.append(_Target(name, raw["category"], raw["max_correct_guesses"],
                           raw["guess_admissible"]))
    return out


def windows(found: Sequence[rw.Passage]) -> list[list[rw.Passage]]:
    """Consecutive passages, at most :data:`MAX_WINDOW_CHARS` characters per window.

    A passage never splits; one longer than the cap is a window on its own.
    """
    out: list[list[rw.Passage]] = []
    size = 0
    for passage in found:
        if out and size + len(passage.text) <= MAX_WINDOW_CHARS:
            out[-1].append(passage)
            size += len(passage.text)
        else:
            out.append([passage])
            size = len(passage.text)
    return out


def _messages(window: Sequence[rw.Passage], asked: Sequence[_Target]) -> list[dict[str, Any]]:
    user = {
        "passages": [{"id": p.id, "page": p.page, "text": p.text} for p in window],
        "targets": [{"target": t.name, "identify": TARGET_QUESTIONS[t.name]} for t in asked],
    }
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False, sort_keys=True)}]


def reservation_of(window: Sequence[rw.Passage], policy: LoadedPolicy, *,
                   max_output_tokens: int) -> int:
    """What the call for *window* reserves against the token budget."""
    return rw.reservation(_messages(window, targets(policy)), max_output_tokens=max_output_tokens)


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #


def _words(text: str) -> set[str]:
    folded = "".join(c for c in unicodedata.normalize("NFKD", text)
                     if not unicodedata.combining(c)).casefold()
    return {w for w in _WORD.findall(folded) if len(w) >= MIN_PARTIAL_WORD and not w.isdigit()}


def _removed_words(entities: EntityDictionary, kept: set[str]) -> dict[str, set[str]]:
    """Per category, the words of its edited entries that the derivative no longer holds."""
    out: dict[str, set[str]] = {}
    for entry in entities.entries:
        if entry.action != "edit":
            continue
        forms = [entry.surface, *entry.variants]
        if entry.person is not None:
            forms += [entry.person.given, entry.person.family]
        out.setdefault(entry.category, set()).update(*(_words(f) for f in forms))
    return {category: words - kept for category, words in out.items()}


def _score(guess: str, target: _Target, entities: EntityDictionary,
           removed: Mapping[str, set[str]]) -> tuple[str, Optional[str], list[str]]:
    """The outcome, the review reason and the matched entry ids."""
    matches = find_matches(guess, entities)
    entries = [(m.entry_id, m.category) for m in matches
               if m.entry_id is not None and m.action == "edit"]
    own = sorted({eid for eid, category in entries if category == target.category})
    if own:
        return "correct", None, own
    if entries:
        return "review", "other_category", sorted({eid for eid, _ in entries})
    if any(m.regex_class is not None for m in matches):
        return "review", "identifier_pattern", []
    if _words(guess) & removed.get(target.category, set()):
        return "review", "partial_name", []
    return "wrong", None, []


def _collapse(text: str) -> str:
    return " ".join(text.split())


def _is_confidence(value: Any) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and 0 <= value <= 1)


def _well_formed(item: Any, asked: Mapping[str, _Target]) -> bool:
    if not (isinstance(item, dict) and set(item) == _GUESS_KEYS and item["target"] in asked):
        return False
    guess = item["guess"]
    if guess is None or (isinstance(guess, str) and not guess.strip()):
        return True
    return (isinstance(guess, str) and _is_confidence(item["confidence"])
            and isinstance(item["passage_id"], str) and isinstance(item["evidence"], str)
            and bool(item["evidence"].strip()))


def _parse(content: Any) -> Optional[list[Any]]:
    if not isinstance(content, str):
        return None
    try:
        reply = json.loads(content)
    except ValueError:
        return None
    if not (isinstance(reply, dict) and set(reply) == {"guesses"}
            and isinstance(reply["guesses"], list)):
        return None
    return reply["guesses"]


# --------------------------------------------------------------------------- #
# Checkpoints
# --------------------------------------------------------------------------- #


def _request_sha256(messages: list[dict[str, Any]], model_id: str, max_output_tokens: int) -> str:
    request = {"messages": messages, "model_id": model_id, "max_output_tokens": max_output_tokens}
    return hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False)
                          .encode("utf-8")).hexdigest()


def _read_checkpoint(path: Path, request_sha256: str) -> dict[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AttackRefused(f"checkpoint {path.name} cannot be read: {exc}") from exc
    if not isinstance(record, dict) or record.get("schema") != CHECKPOINT_SCHEMA:
        raise AttackRefused(f"checkpoint {path.name} is not a {CHECKPOINT_SCHEMA} record")
    if record.get("request_sha256") != request_sha256:
        raise AttackRefused(
            f"checkpoint {path.name} answers a different request: the derivative, the policy, "
            f"the model or the token limit changed. Its reply is not reused and no call is "
            f"made; attack into a new directory."
        )
    if not (set(_CHECKPOINT_KEYS) <= set(record) and rw._is_int(record["tokens_charged"])
            and rw._is_int(record["reservation"]) and isinstance(record["tool_calls"], bool)):
        raise AttackRefused(f"checkpoint {path.name} lacks a field of {CHECKPOINT_SCHEMA}")
    return record


def _require_within_reservation(record: Mapping[str, Any], max_output_tokens: int) -> None:
    usage = record["usage"]
    completion = usage.get("completion_tokens") if isinstance(usage, dict) else None
    if record["tokens_charged"] > record["reservation"] or (
            isinstance(completion, int) and completion > max_output_tokens):
        raise AttackRefused(
            f"window {record['window_id']}: the call was charged {record['tokens_charged']} "
            f"tokens against a reservation of {record['reservation']}, so the budget cannot "
            f"be enforced. The reply is checkpointed; fix the backend."
        )


# --------------------------------------------------------------------------- #
# The stage
# --------------------------------------------------------------------------- #


def build_converse_backend(*, model_id: str, region: str, max_output_tokens: int) -> Any:
    """The runner's Converse backend for A5: pinned model, temperature 0, no tools."""
    if region not in rw.ALLOWED_REGIONS:
        raise AttackRefused(f"region {region!r} is outside ADR-001's {list(rw.ALLOWED_REGIONS)}")
    from runner.transport import bedrock_converse

    return bedrock_converse.BedrockConverseBackend(
        model_id=model_id, region_name=region, temperature=0.0, max_tokens=max_output_tokens
    )


def _check_models(backend: Any, model_id: str, a3_model_id: str) -> None:
    if not (isinstance(model_id, str) and model_id.strip()):
        raise AttackRefused("the A5 model id is not declared; the operator pins it (O2)")
    if not (isinstance(a3_model_id, str) and a3_model_id.strip()):
        raise AttackRefused("the A3 model id is not declared, so independence cannot be checked")
    if not canonical_model_id(model_id).startswith("claude"):
        raise AttackRefused(
            f"the A5 model {model_id!r} is not a Claude model; O2 asks for another member of "
            f"the Claude family"
        )
    if canonical_model_id(model_id) == canonical_model_id(a3_model_id):
        raise AttackRefused(
            f"the A5 model {model_id!r} is the A3 model {a3_model_id!r}: the rewriter may not "
            f"grade itself (O2)"
        )
    if getattr(backend, "model", None) != model_id:
        raise AttackRefused(
            f"the backend serves model {getattr(backend, 'model', None)!r}, not the pinned "
            f"A5 model {model_id!r}"
        )
    # BedrockConverseBackend keeps its tool schemas here.
    if getattr(backend, "_tools", None):
        raise AttackRefused("the backend carries tools; the attack runs closed book")


def attack(
    *,
    derivative: Path,
    derivative_sha256: str,
    policy: LoadedPolicy,
    policy_sha256: str,
    dictionary: Path,
    dictionary_sha256: str,
    backend: rw.RewriteBackend,
    model_id: str,
    a3_model_id: str,
    a3_input: Path,
    a3_input_sha256: str,
    max_output_tokens: int,
    token_budget: int,
    out_dir: Path,
) -> AttackResult:
    """Ask *backend* to re-identify *derivative*; score its guesses; write the report.

    *derivative* is any stage output, pinned by *derivative_sha256*.
    *a3_input* is the derivative A3 reads, pinned by *a3_input_sha256*; the
    flags name its passages. Every refusal of the inputs runs before the first
    call.
    """
    derivative = intake.require_private(derivative, "the derivative")
    out_dir = intake.require_private(out_dir, "the attack directory")
    require_hash(policy, policy_sha256)
    asked = targets(policy)
    try:
        entities = rw.load_pinned_dictionary(dictionary, policy, dictionary_sha256)
    except rw.RewriteRefused as exc:
        raise AttackRefused(str(exc)) from exc
    pinned = intake.pin(derivative, derivative_sha256, "the derivative")
    a3_input = intake.require_private(a3_input, "A3's input")
    a3_pinned = intake.pin(a3_input, a3_input_sha256, "A3's input")
    _check_models(backend, model_id, a3_model_id)
    if not (rw._is_int(token_budget) and token_budget > 0):
        raise AttackRefused(f"the token budget must be a positive integer, not {token_budget!r}")
    if not (rw._is_int(max_output_tokens) and max_output_tokens > 0):
        raise AttackRefused("max_output_tokens must be a positive integer")

    found = rw.passages(derivative)
    if not any(p.text.strip() for p in found):
        raise AttackRefused("the derivative has no extractable text, so there is nothing to attack")
    a3_texts = {p.id: _collapse(p.text) for p in rw.passages(a3_input)}
    grouped = windows(found)
    checkpoints = out_dir / CHECKPOINT_DIR
    requests: list[tuple[str, list[dict[str, Any]], str]] = []
    replies: dict[str, dict[str, Any]] = {}
    for number, window in enumerate(grouped, start=1):
        wid = f"w{number}"
        messages = _messages(window, asked)
        sha = _request_sha256(messages, model_id, max_output_tokens)
        requests.append((wid, messages, sha))
        path = checkpoints / f"{wid}.json"
        if path.exists():
            replies[wid] = _read_checkpoint(path, sha)
    for record in replies.values():
        _require_within_reservation(record, max_output_tokens)
    from_checkpoint = len(replies)
    used = sum(int(r["tokens_charged"]) for r in replies.values())
    calls = 0

    for wid, messages, sha in requests:
        if wid in replies:
            continue
        reserve = rw.reservation(messages, max_output_tokens=max_output_tokens)
        if used + reserve > token_budget:
            return AttackResult("stopped_at_token_budget", None, None, None, None, used, calls,
                                from_checkpoint, len(requests) - len(replies))
        before = backend.last_usage
        response = backend(messages)
        calls += 1
        usage = backend.last_usage
        # BedrockConverseBackend keeps the previous call's usage when a reply reports none.
        reported = (usage is not before and isinstance(usage, dict)
                    and rw._is_int(usage.get("total_tokens")))
        charged = int(usage["total_tokens"]) if reported else reserve  # type: ignore[index]
        record = {
            "schema": CHECKPOINT_SCHEMA,
            "window_id": wid,
            "request_sha256": sha,
            "model_id": model_id,
            "content": response.get("content"),
            "tool_calls": bool(response.get("tool_calls")),
            "usage": usage if reported else None,
            "tokens_charged": charged,
            "reservation": reserve,
        }
        checkpoints.mkdir(parents=True, exist_ok=True)
        atomic_write_text(canonical_json_bytes(record).decode("utf-8"), checkpoints / f"{wid}.json")
        replies[wid] = record
        used += charged
        _require_within_reservation(record, max_output_tokens)

    by_name = {t.name: t for t in asked}
    removed = _removed_words(entities, set().union(*(_words(p.text) for p in found)))
    flag_categories = {c.id for c in policy.categories if c.rule == "flag"} - rw.UNFLAGGABLE
    counts = {t.name: Counter({k: 0 for k in _OUTCOMES}) for t in asked}
    identified: dict[str, set[str]] = {t.name: set() for t in asked}
    flags: dict[str, set[str]] = {}
    malformed_windows = malformed_guesses = unlocated = 0
    detail_windows: list[dict[str, Any]] = []

    for (wid, _, _), window in zip(requests, grouped):
        record = replies[wid]
        texts = {p.id: _collapse(p.text) for p in window}
        entry: dict[str, Any] = {"id": wid, "passage_ids": [p.id for p in window],
                                 "tokens_charged": record["tokens_charged"]}
        items = None if record["tool_calls"] else _parse(record["content"])
        if items is None:
            malformed_windows += 1
            detail_windows.append({**entry, "response_status": "malformed", "guesses": []})
            continue
        scored: list[dict[str, Any]] = []
        for item in items:
            if not _well_formed(item, by_name):
                malformed_guesses += 1
                scored.append({"outcome": "malformed"})
                continue
            target = by_name[item["target"]]
            guess = item["guess"]
            if guess is None or not guess.strip():
                scored.append({"target": target.name, "outcome": "abstained"})
                continue
            reason: Optional[str] = None
            ids: list[str] = []
            if target.admissible:
                outcome = "admissible"
            else:
                outcome, reason, ids = _score(guess, target, entities, removed)
            counts[target.name][outcome] += 1
            quote = _collapse(item["evidence"])
            # The quote must be in the passage cited, and in exactly one passage of A3's
            # input: passage ids are positional, so a later stage's id may name other text.
            a3_ids = [pid for pid, text in a3_texts.items() if quote in text]
            located = (item["passage_id"] in texts and quote in texts[item["passage_id"]]
                       and len(a3_ids) == 1)
            if outcome == "correct":
                identified[target.name].update(ids)
                if located:
                    flags.setdefault(a3_ids[0], set()).update({target.category} | flag_categories)
                else:
                    unlocated += 1
            scored.append({**item, "outcome": outcome, "review_reason": reason,
                           "entry_ids": ids, "located": located,
                           "a3_passage_id": a3_ids[0] if located else None})
        detail_windows.append({**entry, "response_status": "valid", "guesses": scored})

    target_rows: list[dict[str, Any]] = []
    by_category: dict[str, Counter[str]] = {}
    for target in asked:
        tally = counts[target.name]
        # A target abstains when no window drew a guess at it.
        tally["abstained"] = int(not any(tally[k] for k in _OUTCOMES if k != "abstained"))
        # The threshold counts entities identified, not guesses repeated.
        failed = (not target.admissible and target.max_correct is not None
                  and len(identified[target.name]) > target.max_correct)
        target_rows.append({
            "target": target.name, "category": target.category,
            "max_correct_guesses": target.max_correct, "guess_admissible": target.admissible,
            "counts": dict(tally), "entities_identified": len(identified[target.name]),
            "failed": failed,
        })
        by_category.setdefault(target.category, Counter({k: 0 for k in _OUTCOMES})).update(tally)
    if any(row["failed"] for row in target_rows):
        verdict = "failed"
    elif malformed_windows or malformed_guesses:
        verdict = "incomplete"
    else:
        verdict = "passed"

    report = {
        "schema": SCHEMA,
        "record_type": RECORD_TYPE,
        "stage": "A5",
        "part": "closed-book model attack",
        "input": {"derivative_sha256": pinned, "a3_input_sha256": a3_pinned},
        "policy_sha256": policy.sha256,
        "dictionary_sha256": entities.sha256,
        "model": {
            "model_id": model_id, "canonical_model_id": canonical_model_id(model_id),
            "a3_model_id": a3_model_id, "a3_canonical_model_id": canonical_model_id(a3_model_id),
            "max_output_tokens": max_output_tokens, "tools": [],
            "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
        },
        "token_budget": token_budget,
        "tokens_used": used,
        "windows": {"total": len(requests), "malformed": malformed_windows,
                    "max_window_chars": MAX_WINDOW_CHARS},
        "targets": target_rows,
        "by_category": {k: dict(v) for k, v in sorted(by_category.items())},
        "malformed_guesses": malformed_guesses,
        "correct_unlocated": unlocated,
        "passages_sent_back": len(flags),
        "verdict": verdict,
        "scoring_rule": SCORING_RULE,
        "review_rule_status": "agent_drafted_pending_operator_confirmation",
        "limit": LIMIT,
        "privacy": "Counts, hashes and model ids only. Guesses, quotes and passage ids are in the "
                   "private details file.",
    }
    details = {
        "schema": DETAILS_SCHEMA,
        "record_type": "reidentification_details",
        "stage": "A5",
        "derivative_sha256": pinned,
        "windows": detail_windows,
        "privacy": "Private: guesses name real entities, and quotes are derivative text.",
    }
    flag_record = {
        "schema": FLAGS_SCHEMA,
        "record_type": "anonymisation_a3_flags",
        "stage": "A5",
        "derivative_sha256": pinned,
        "a3_input_sha256": a3_pinned,
        "policy_sha256": policy.sha256,
        "flags": {pid: sorted(categories) for pid, categories in sorted(flags.items())},
        "rule": "Each passage of A3's input that holds the quote of a correct guess, with the "
                "target's category and every category the policy flags. A quote found in no "
                "passage of A3's input, or in several, is counted as correct_unlocated instead.",
    }
    for name, record in ((REPORT_FILE, report), (DETAILS_FILE, details), (FLAGS_FILE, flag_record)):
        atomic_write_text(canonical_json_bytes(record).decode("utf-8"), out_dir / name)
    return AttackResult("complete", verdict, out_dir / REPORT_FILE, out_dir / DETAILS_FILE,
                        out_dir / FLAGS_FILE, used, calls, from_checkpoint, 0)
