"""Bounded model rewrite, stage A3 of the anonymisation pipeline (AN6).

AN6 of ``.scratch/msca-dn-anonymisation/tickets.md``, stage A3 of
``plans/msca_dn_anonymisation_handoff_2026-10-14.md``. A Bedrock model
proposes span edits for what A2 cannot handle, such as a niche topic
combination. Code decides which of them stand.

What the model sees
-------------------
One passage at a time: a run of visual lines of the A2 derivative, at most
:data:`MAX_PASSAGE_CHARS` characters, and the policy rules of the categories
flagged for that passage. Never the whole document. Lines are read in visual
order, so A2's replacement text, which PyMuPDF returns as separate blocks,
reads in place.

Which passages go
-----------------
Only those the caller flags, with the categories it flags them for. The policy
rewrites a niche topic only where stage A5 shows it identifies, so the
dictionary's flagged entries are not sent on their own: :func:`candidate_flags`
lists them for the operator, and the operator, or later AN8b, passes the flags.
``identifying_figure`` cannot be flagged: the policy reserves figures for the
operator.

What the model returns
----------------------
A JSON object of span edits and proposed new entities, nothing else. Each
edit names ``start``, ``end``, ``original``, ``replacement``, ``category`` and
``reason``. ``original`` must equal the passage's text at the offsets, which
catches an offset the model miscounted. :func:`validate_edits` refuses an edit
outside a flagged category, over its length budget, overlapping an earlier one,
spanning a line break in its replacement, matching a dictionary entry in its
replacement, or removing text without the operator's approval. The length
budget is AN5's: the first line's box, run to the mirrored margin at a line
end, measured in the replacement font at the span's point size. Later lines of
a span are removed. A malformed reply is recorded as malformed, never repaired
(CLAUDE.md §17.5.4).

New entities go to the operator queue, :data:`QUEUE_FILE`. They change no text
and no dictionary: the operator adds approved ones to the dictionary, and A2
runs again.

Checkpoints and the token budget
--------------------------------
Each reply is written to its passage's checkpoint before it is validated. A
re-run reads the checkpoint instead of calling the model, and refuses a
checkpoint whose request differs, so changed inputs never mix with old
replies. The plan and the queue are derived from the checkpoints and the
operator's removal approvals, so a re-run with a new approval rewrites them
without a call. The budget counts every recorded call of the stage,
checkpointed ones included. Before each call the stage reserves the request's
UTF-8 byte count plus :data:`REQUEST_OVERHEAD_TOKENS` plus
``max_output_tokens``, an upper bound on what the call can spend, and stops if
the reservation does not fit. A call charged above its reservation refuses the
run, now and on every resume, because the bound no longer holds. A call that
reports no usage is charged its reservation. A stopped run writes no plan. A
larger budget resumes it.

What it does not do
-------------------
It does not apply the plan. The plan locates edits on the A2 derivative, so
applying it needs the stage-output harness AN7 added
(:func:`runner.anonymisation_intake.apply_stage_edits`) and a stage that calls
it. Nor can code check that an edit keeps the
sentence's meaning: the operator reads the plan.

What is private
---------------
Everything: the derivative, the checkpoints (they hold the model's replies),
the plan (it holds replacements and reasons) and the queue (it holds the
proposed entities' text). Every path inside this repository is refused. The
module logs nothing.

Constitutional standing: an authoring tool, not a runtime component. It
evaluates no gate and writes no Tier 5 artifact. Its model calls go through the
runner's Bedrock Converse transport, with no tools.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, NamedTuple, Optional, Protocol, Sequence

from runner import anonymisation_intake as intake
from runner.anonymisation_matching import EntityDictionary, find_matches, load_dictionary
from runner.anonymisation_policy import LoadedPolicy, require_hash
from runner.atomic_write import atomic_write_text, canonical_json_bytes

SCHEMA = "anonymisation_rewrite/1"
RECORD_TYPE = "anonymisation_rewrite"
CHECKPOINT_SCHEMA = "anonymisation_rewrite_checkpoint/1"
QUEUE_SCHEMA = "anonymisation_entity_proposals/1"
REDACTION_SCHEMA = "anonymisation_redaction/1"

PLAN_FILE = "rewrite_plan.json"
QUEUE_FILE = "entity_proposals.json"
CHECKPOINT_DIR = "checkpoints"

MAX_PASSAGE_CHARS = 3000
#: Tokens a Converse request may add to its message bytes (roles, framing).
REQUEST_OVERHEAD_TOKENS = 64
#: ADR-001: Bedrock only in these regions. eu-north-1 is the host's Region
#: under OD1-r1 (decision record aws-redeployment-od1-region-r1_2026-10-21);
#: the code runs ahead of ADR-001's text on that record's authority until
#: amendment A2 (ticket R13) states the Region and decides whether to narrow
#: this list (decision record aws-redeployment-r9e-eu-region_2026-10-27).
ALLOWED_REGIONS: tuple[str, ...] = ("eu-north-1", "eu-west-1", "us-east-1")
#: The policy reserves these categories for the operator.
UNFLAGGABLE: frozenset[str] = frozenset({"identifying_figure"})

_EDIT_KEYS = frozenset({"start", "end", "original", "replacement", "category", "reason"})
_ENTITY_KEYS = frozenset({"text", "category", "reason"})
_CHECKPOINT_KEYS = ("passage_id", "request_sha256", "model_id", "content", "tool_calls",
                    "usage", "tokens_charged", "reservation")

SYSTEM_PROMPT = """\
You anonymise one passage of a research proposal under a published policy.
The user message is a JSON object with the passage and the policy rules of the
categories flagged for it. Propose span edits only in those categories.

Rules:
- Keep the sentence's meaning and everything an evaluator scores. Change only
  what identifies the network, its people, its places or the project.
- Keep each replacement about as long as the text it replaces. It is set in the
  same space on the page.
- Never remove text without a replacement.
- Offsets are 0-based character indices into passage.text, end exclusive.
  "original" must equal passage.text[start:end] exactly.
- If you notice an identifying entity the edits do not cover, list it under
  new_entities. Do not edit it.

Reply with one JSON object and nothing else, no code fence:
{"edits": [{"start": 0, "end": 0, "original": "", "replacement": "",
            "category": "", "reason": ""}],
 "new_entities": [{"text": "", "category": "", "reason": ""}]}
"""


class RewriteRefused(RuntimeError):
    """The rewrite cannot run as asked. No model call was made for the refused step."""


class RewriteBackend(Protocol):
    """What the stage needs of a backend: ``BedrockConverseBackend`` satisfies it."""

    @property
    def model(self) -> str: ...

    @property
    def last_usage(self) -> Optional[dict[str, int]]: ...

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class RemovalApproval:
    """The operator approves removing ``text[start:end]`` of passage *passage_id*."""

    passage_id: str
    start: int
    end: int


@dataclass(frozen=True)
class RewriteResult:
    status: str
    """``complete`` or ``stopped_at_token_budget``."""
    plan: Optional[Path]
    queue: Optional[Path]
    tokens_used: int
    calls_made: int
    passages_from_checkpoint: int
    passages_pending: int


class _Char(NamedTuple):
    c: str
    bbox: tuple[float, float, float, float]
    size: float
    row: int


@dataclass(frozen=True)
class Passage:
    """A run of visual lines on one page. ``chars[i]`` locates ``text[i]``, or is None."""

    id: str
    page: int
    text: str
    chars: tuple[Optional[_Char], ...]
    right_limit: float
    """Where a box at a line end may run to: the left text margin, mirrored."""


# --------------------------------------------------------------------------- #
# Passages
# --------------------------------------------------------------------------- #


def _rows(page: Any) -> list[list[tuple[str, tuple[float, float, float, float], float]]]:
    """The page's characters grouped into visual lines, top to bottom, left to right."""
    lines = []
    for block in page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", ()):
            chars = [(ch["c"], tuple(ch["bbox"]), round(float(span["size"]), 2))
                     for span in line["spans"] for ch in span["chars"]]
            if chars:
                x0, y0, x1, y1 = line["bbox"]
                lines.append(((y0 + y1) / 2, y1 - y0, chars))
    lines.sort(key=lambda item: (item[0], item[2][0][1][0]))
    rows: list[tuple[float, float, list]] = []
    for middle, height, chars in lines:
        if rows and abs(middle - rows[-1][0]) <= min(height, rows[-1][1]) / 2:
            rows[-1][2].extend(chars)
        else:
            rows.append((middle, height, list(chars)))
    return [sorted(chars, key=lambda ch: ch[1][0]) for _, _, chars in rows]


def _row_text(row: list, number: int) -> tuple[str, list[Optional[_Char]]]:
    text: list[str] = []
    chars: list[Optional[_Char]] = []
    for c, bbox, size in row:
        if chars and not c.isspace() and text[-1] != " ":
            previous = chars[-1]
            if previous is not None and bbox[0] - previous.bbox[2] > 0.2 * size:
                text.append(" ")
                chars.append(None)
        text.append(c)
        chars.append(_Char(c, bbox, size, number))
    return "".join(text), chars


def passages(pdf: Path) -> list[Passage]:
    """The derivative's passages: visual lines split at paragraph gaps and at the size cap."""
    import pymupdf

    pdf = intake.require_private(pdf, "the derivative")
    out: list[Passage] = []
    doc = pymupdf.open(pdf)
    try:
        for number in range(1, doc.page_count + 1):
            page = doc[number - 1]
            rows = _rows(page)
            if not rows:
                continue
            margin = min(ch[1][0] for row in rows for ch in row)
            right_limit = page.rect.x1 - margin
            groups: list[list[int]] = []
            for r, row in enumerate(rows):
                top = min(ch[1][1] for ch in row)
                if groups:
                    previous = rows[groups[-1][-1]]
                    bottom = max(ch[1][3] for ch in previous)
                    height = bottom - min(ch[1][1] for ch in previous)
                    if top - bottom <= 0.8 * height:
                        groups[-1].append(r)
                        continue
                groups.append([r])
            k = 0
            for group in groups:
                text = ""
                chars: list[Optional[_Char]] = []
                segments = []
                for r in group:
                    line, line_chars = _row_text(rows[r], r)
                    # A line longer than the cap is cut into pieces, never dropped.
                    for at in range(0, len(line), MAX_PASSAGE_CHARS):
                        segments.append((line[at:at + MAX_PASSAGE_CHARS],
                                         line_chars[at:at + MAX_PASSAGE_CHARS]))
                for line, line_chars in segments:
                    joined = len(text) + (1 if text else 0) + len(line)
                    if text and joined > MAX_PASSAGE_CHARS:
                        k += 1
                        out.append(Passage(f"p{number}-{k}", number, text, tuple(chars),
                                           right_limit))
                        text, chars = "", []
                    if text:
                        text += "\n"
                        chars.append(None)
                    text += line
                    chars += line_chars
                k += 1
                out.append(Passage(f"p{number}-{k}", number, text, tuple(chars), right_limit))
    finally:
        doc.close()
    return out


def candidate_flags(found: Sequence[Passage], dictionary: EntityDictionary) -> dict[str, list[str]]:
    """Passages holding a flagged dictionary entry, for the operator to consider."""
    out: dict[str, list[str]] = {}
    for passage in found:
        categories = sorted({m.category for m in find_matches(passage.text, dictionary)
                             if m.action == "flag"})
        if categories:
            out[passage.id] = categories
    return out


def load_pinned_dictionary(path: Path, policy: LoadedPolicy, expected_sha256: str
                           ) -> EntityDictionary:
    """The entity dictionary at *path*, refused unless it hashes to *expected_sha256*."""
    entities = load_dictionary(intake.require_private(path, "the entity dictionary"), policy)
    if entities.sha256 != expected_sha256:
        raise RewriteRefused(
            f"the entity dictionary hashes to {entities.sha256}, not the declared "
            f"{expected_sha256}: this is not the pinned dictionary."
        )
    return entities


# --------------------------------------------------------------------------- #
# The validator
# --------------------------------------------------------------------------- #


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _well_formed(edit: Any) -> bool:
    return (isinstance(edit, dict) and set(edit) == _EDIT_KEYS
            and _is_int(edit["start"]) and _is_int(edit["end"])
            and all(isinstance(edit[k], str) for k in _EDIT_KEYS - {"start", "end"}))


def _geometry(passage: Passage, start: int, end: int, replacement: str
              ) -> tuple[Optional[str], dict[str, Any]]:
    """The edit's pieces and budget, or the refusal code."""
    import pymupdf

    by_row: dict[int, list[_Char]] = {}
    for char in passage.chars[start:end]:
        if char is not None and not char.c.isspace():
            by_row.setdefault(char.row, []).append(char)
    pieces = list(by_row.values())
    if not pieces:
        return "empty_span", {}
    rects = [(min(c.bbox[0] for c in p), min(c.bbox[1] for c in p),
              max(c.bbox[2] for c in p), max(c.bbox[3] for c in p)) for p in pieces]
    first, row = rects[0], pieces[0][0].row
    own = {id(c) for c in pieces[0]}
    followed = any(
        c is not None and c.row == row and id(c) not in own and not c.c.isspace()
        and c.bbox[0] >= first[2] - 0.5
        for c in passage.chars
    )
    if not followed:
        first = (first[0], first[1], max(first[2], passage.right_limit), first[3])
        rects[0] = first
    sizes = {c.size for c in pieces[0]}
    if len(sizes) > 1:
        return "mixed_point_size", {}
    size = sizes.pop()
    used = pymupdf.get_text_length(replacement, fontname=intake.REPLACEMENT_FONT, fontsize=size)
    budget = first[2] - first[0]
    if used > budget + 1e-6:
        return "over_length_budget", {}
    return None, {
        "pieces": [{"rect": [round(v, 3) for v in rect], "replacement": replacement if k == 0 else ""}
                   for k, rect in enumerate(rects)],
        "point_size": size,
        "budget_points": round(budget, 3),
        "used_points": round(used, 3),
    }


def validate_edits(
    passage: Passage,
    edits: Sequence[Any],
    *,
    flagged: Sequence[str],
    policy: LoadedPolicy,
    dictionary: EntityDictionary,
    approved_removals: Sequence[RemovalApproval] = (),
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The edits that stand, located on the page, and the refused ones by index and code.

    Edits are taken in order; an edit overlapping an earlier accepted one is
    refused.
    """
    categories = {c.id for c in policy.categories}
    approved = {(a.start, a.end) for a in approved_removals if a.passage_id == passage.id}
    accepted: list[dict[str, Any]] = []
    refused: list[dict[str, Any]] = []
    taken: list[tuple[int, int]] = []
    for index, edit in enumerate(edits):
        code: Optional[str] = None
        located: dict[str, Any] = {}
        if not _well_formed(edit):
            code = "malformed_edit"
        elif not 0 <= edit["start"] < edit["end"] <= len(passage.text):
            code = "span_out_of_bounds"
        elif passage.text[edit["start"]:edit["end"]] != edit["original"]:
            code = "span_mismatch"
        elif edit["category"] not in categories or edit["category"] not in flagged:
            code = "category_not_flagged"
        elif not edit["reason"].strip():
            code = "no_reason"
        elif "\n" in edit["replacement"] or "\r" in edit["replacement"]:
            code = "multiline_replacement"
        elif not edit["replacement"].strip() and (edit["start"], edit["end"]) not in approved:
            code = "removal_not_approved"
        elif any(edit["start"] < e and s < edit["end"] for s, e in taken):
            code = "overlap"
        elif any(m.action == "edit" for m in find_matches(edit["replacement"], dictionary)):
            code = "replacement_identifies"
        else:
            code, located = _geometry(passage, edit["start"], edit["end"],
                                      edit["replacement"].strip() and edit["replacement"])
        if code is not None:
            refused.append({"index": index, "code": code})
            continue
        taken.append((edit["start"], edit["end"]))
        accepted.append({
            "index": index,
            "start": edit["start"],
            "end": edit["end"],
            "category": edit["category"],
            "replacement": located["pieces"][0]["replacement"],
            "reason": edit["reason"],
            "removal": located["pieces"][0]["replacement"] == "",
            "page": passage.page,
            **located,
        })
    return accepted, refused


def _parse(content: Any) -> Optional[dict[str, Any]]:
    """The reply as an object with list-valued ``edits`` and ``new_entities``, or None."""
    if not isinstance(content, str):
        return None
    try:
        reply = json.loads(content)
    except ValueError:
        return None
    if (not isinstance(reply, dict) or set(reply) != {"edits", "new_entities"}
            or not isinstance(reply["edits"], list) or not isinstance(reply["new_entities"], list)):
        return None
    return reply


# --------------------------------------------------------------------------- #
# Requests, checkpoints and the budget
# --------------------------------------------------------------------------- #


def _policy_excerpt(policy: LoadedPolicy, flagged: Sequence[str]) -> dict[str, Any]:
    wanted = set(flagged)
    return {
        "policy_sha256": policy.sha256,
        "categories": [c for c in policy.record["categories"] if c["id"] in wanted],
        "kept_content": policy.record["kept_content"],
    }


def _messages(passage: Passage, flagged: Sequence[str], policy: LoadedPolicy
              ) -> list[dict[str, Any]]:
    user = {
        "passage": {"id": passage.id, "text": passage.text},
        "flagged_categories": list(flagged),
        "policy": _policy_excerpt(policy, flagged),
    }
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user, ensure_ascii=False, sort_keys=True)}]


def reservation(messages: Sequence[Mapping[str, Any]], *, max_output_tokens: int) -> int:
    """An upper bound on what one call can spend.

    A token covers at least one byte, so a request costs at most its UTF-8
    bytes in input tokens.
    """
    request = sum(len(str(m.get("content") or "").encode("utf-8")) for m in messages)
    return request + REQUEST_OVERHEAD_TOKENS + max_output_tokens


def _request_sha256(messages: list[dict[str, Any]], model_id: str, max_output_tokens: int) -> str:
    request = {"messages": messages, "model_id": model_id, "max_output_tokens": max_output_tokens}
    return hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False)
                          .encode("utf-8")).hexdigest()


def _read_checkpoint(path: Path, request_sha256: str) -> dict[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RewriteRefused(f"checkpoint {path.name} cannot be read: {exc}") from exc
    if not isinstance(record, dict) or record.get("schema") != CHECKPOINT_SCHEMA:
        raise RewriteRefused(f"checkpoint {path.name} is not an {CHECKPOINT_SCHEMA} record")
    if record.get("request_sha256") != request_sha256:
        raise RewriteRefused(
            f"checkpoint {path.name} answers a different request: the passage, the policy, "
            f"the flags, the model or the token limit changed. Its reply is not reused and no "
            f"call is made; rewrite into a new directory."
        )
    if not (set(_CHECKPOINT_KEYS) <= set(record) and _is_int(record["tokens_charged"])
            and _is_int(record["reservation"]) and isinstance(record["tool_calls"], bool)):
        raise RewriteRefused(f"checkpoint {path.name} lacks a field of {CHECKPOINT_SCHEMA}")
    return record


def _require_within_reservation(record: Mapping[str, Any], max_output_tokens: int) -> None:
    """Refuse a call that spent more than the reservation the budget was checked against."""
    usage = record["usage"]
    completion = usage.get("completion_tokens") if isinstance(usage, dict) else None
    if record["tokens_charged"] > record["reservation"] or (
            isinstance(completion, int) and completion > max_output_tokens):
        raise RewriteRefused(
            f"passage {record['passage_id']}: the call was charged {record['tokens_charged']} "
            f"tokens against a reservation of {record['reservation']} (max_output_tokens "
            f"{max_output_tokens}), so the reservation does not bound the backend and the "
            f"budget cannot be enforced. The reply is checkpointed; fix the backend."
        )


# --------------------------------------------------------------------------- #
# The stage
# --------------------------------------------------------------------------- #


def build_converse_backend(*, model_id: str, region: str, max_output_tokens: int) -> Any:
    """The runner's Converse backend for A3: pinned model, temperature 0, no tools."""
    if region not in ALLOWED_REGIONS:
        raise RewriteRefused(
            f"region {region!r} is outside ADR-001's {list(ALLOWED_REGIONS)}"
        )
    from runner.transport import bedrock_converse

    return bedrock_converse.BedrockConverseBackend(
        model_id=model_id, region_name=region, temperature=0.0, max_tokens=max_output_tokens
    )


def _pinned_derivative(derivative: Path, redaction_log: Path) -> tuple[str, str]:
    try:
        record = json.loads(redaction_log.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RewriteRefused(f"the redaction log cannot be read: {exc}") from exc
    if not isinstance(record, dict) or record.get("schema") != REDACTION_SCHEMA:
        raise RewriteRefused(f"the redaction log is not an {REDACTION_SCHEMA} record")
    sha = intake.pin(derivative, str(record["output"]["sha256"]), "the derivative")
    return sha, hashlib.sha256(redaction_log.read_bytes()).hexdigest()


def _check_flags(flags: Mapping[str, Sequence[str]], known: Mapping[str, Passage],
                 policy: LoadedPolicy) -> dict[str, list[str]]:
    if not flags:
        raise RewriteRefused("no passage is flagged, so there is nothing to rewrite")
    categories = {c.id for c in policy.categories}
    out: dict[str, list[str]] = {}
    for pid, flagged in flags.items():
        if pid not in known:
            raise RewriteRefused(f"flagged passage {pid!r} is not a passage of the derivative")
        wanted = sorted(set(flagged))
        if not wanted:
            raise RewriteRefused(f"passage {pid!r} is flagged with no category")
        for category in wanted:
            if category not in categories:
                raise RewriteRefused(f"passage {pid!r}: {category!r} is not a policy category")
            if category in UNFLAGGABLE:
                raise RewriteRefused(
                    f"passage {pid!r}: {category} is reviewed by the operator per figure "
                    f"and is never rewritten by a model"
                )
        out[pid] = wanted
    return out


def rewrite(
    *,
    derivative: Path,
    redaction_log: Path,
    policy: LoadedPolicy,
    policy_sha256: str,
    dictionary: Path,
    dictionary_sha256: str,
    flags: Mapping[str, Sequence[str]],
    backend: RewriteBackend,
    model_id: str,
    max_output_tokens: int,
    token_budget: int,
    out_dir: Path,
    approved_removals: Sequence[RemovalApproval] = (),
) -> RewriteResult:
    """Ask *backend* for span edits to each flagged passage of *derivative*; write the plan.

    *derivative* must be the file *redaction_log* records as A2's output.
    *model_id* is the A3 model the operator pinned, and *backend* must serve
    it. Every refusal of the inputs runs before the first call.
    """
    derivative = intake.require_private(derivative, "the derivative")
    redaction_log = intake.require_private(redaction_log, "the redaction log")
    out_dir = intake.require_private(out_dir, "the rewrite directory")
    require_hash(policy, policy_sha256)
    entities = load_pinned_dictionary(dictionary, policy, dictionary_sha256)
    derivative_sha, log_sha = _pinned_derivative(derivative, redaction_log)

    if not (isinstance(model_id, str) and model_id.strip()):
        raise RewriteRefused("the A3 model id is not declared; the operator pins it (O2)")
    if getattr(backend, "model", None) != model_id:
        raise RewriteRefused(
            f"the backend serves model {getattr(backend, 'model', None)!r}, not the pinned "
            f"A3 model {model_id!r}"
        )
    # BedrockConverseBackend keeps its tool schemas here; A3 sends none.
    if getattr(backend, "_tools", None):
        raise RewriteRefused("the backend carries tools; an A3 call carries no tools")
    if not (_is_int(token_budget) and token_budget > 0):
        raise RewriteRefused(f"the token budget must be a positive integer, not {token_budget!r}")
    if not (_is_int(max_output_tokens) and max_output_tokens > 0):
        raise RewriteRefused("max_output_tokens must be a positive integer")

    found = passages(derivative)
    known = {p.id: p for p in found}
    flagged = _check_flags(flags, known, policy)
    for approval in approved_removals:
        if approval.passage_id not in flagged:
            raise RewriteRefused(f"removal approved for unflagged passage {approval.passage_id!r}")
    order = [p for p in found if p.id in flagged]

    checkpoints = out_dir / CHECKPOINT_DIR
    requests: dict[str, tuple[list[dict[str, Any]], str]] = {}
    replies: dict[str, dict[str, Any]] = {}
    for passage in order:
        messages = _messages(passage, flagged[passage.id], policy)
        sha = _request_sha256(messages, model_id, max_output_tokens)
        requests[passage.id] = (messages, sha)
        path = checkpoints / f"{passage.id}.json"
        if path.exists():
            replies[passage.id] = _read_checkpoint(path, sha)
    for record in replies.values():
        _require_within_reservation(record, max_output_tokens)
    from_checkpoint = len(replies)
    used = sum(int(r["tokens_charged"]) for r in replies.values())
    calls = 0

    for passage in order:
        if passage.id in replies:
            continue
        messages, sha = requests[passage.id]
        reserve = reservation(messages, max_output_tokens=max_output_tokens)
        if used + reserve > token_budget:
            return RewriteResult("stopped_at_token_budget", None, None, used, calls,
                                 from_checkpoint, len(order) - len(replies))
        before = backend.last_usage
        response = backend(messages)
        calls += 1
        usage = backend.last_usage
        # BedrockConverseBackend keeps the previous call's usage when a reply reports none.
        reported = (usage is not before and isinstance(usage, dict)
                    and _is_int(usage.get("total_tokens")))
        charged = int(usage["total_tokens"]) if reported else reserve  # type: ignore[index]
        record = {
            "schema": CHECKPOINT_SCHEMA,
            "passage_id": passage.id,
            "request_sha256": sha,
            "model_id": model_id,
            "content": response.get("content"),
            "tool_calls": bool(response.get("tool_calls")),
            "usage": usage if reported else None,
            "tokens_charged": charged,
            "reservation": reserve,
        }
        checkpoints.mkdir(parents=True, exist_ok=True)
        atomic_write_text(canonical_json_bytes(record).decode("utf-8"),
                          checkpoints / f"{passage.id}.json")
        replies[passage.id] = record
        used += charged
        _require_within_reservation(record, max_output_tokens)

    known_categories = {c.id for c in policy.categories}
    plan_passages: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []
    for passage in order:
        record = replies[passage.id]
        reply = None if record["tool_calls"] else _parse(record["content"])
        entry: dict[str, Any] = {"id": passage.id, "page": passage.page,
                                 "flagged": flagged[passage.id],
                                 "tokens_charged": record["tokens_charged"]}
        if reply is None:
            plan_passages.append({**entry, "response_status": "malformed", "edits": [],
                                  "refused": [], "proposals": 0})
            continue
        accepted, refused = validate_edits(
            passage, reply["edits"], flagged=flagged[passage.id], policy=policy,
            dictionary=entities, approved_removals=approved_removals)
        queued = [
            {"passage_id": passage.id, "text": e["text"], "category": e["category"],
             "reason": e["reason"], "status": "awaiting_operator"}
            for e in reply["new_entities"]
            if isinstance(e, dict) and set(e) == _ENTITY_KEYS
            and all(isinstance(e[k], str) and e[k].strip() for k in _ENTITY_KEYS)
            and e["category"] in known_categories
        ]
        proposals += queued
        plan_passages.append({
            **entry, "response_status": "valid", "edits": accepted, "refused": refused,
            "proposals": len(queued),
            "malformed_proposals": len(reply["new_entities"]) - len(queued),
        })

    plan = {
        "schema": SCHEMA,
        "record_type": RECORD_TYPE,
        "stage": "A3",
        "purpose": "The validated span edits a model proposed for the flagged passages of the A2 "
                   "derivative, located on its pages.",
        "input": {"derivative_sha256": derivative_sha, "redaction_log_sha256": log_sha},
        "policy_sha256": policy.sha256,
        "dictionary_sha256": entities.sha256,
        "model": {"model_id": model_id, "max_output_tokens": max_output_tokens,
                  "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()},
        "token_budget": token_budget,
        "tokens_used": used,
        "flags": flagged,
        "approved_removals": [{"passage_id": a.passage_id, "start": a.start, "end": a.end}
                              for a in approved_removals],
        "passages": plan_passages,
        "applied": False,
        "not_applied_because": (
            "AN4's edit harness edits only the PDF its intake pinned. Applying this plan to the "
            "A2 derivative needs a harness that pins a stage output."
        ),
        "not_checked": "Whether an edit keeps the sentence's meaning. The operator reads the plan.",
        "privacy": "Private: this plan holds replacement text and the model's reasons.",
    }
    queue = {
        "schema": QUEUE_SCHEMA,
        "record_type": "anonymisation_entity_proposals",
        "stage": "A3",
        "applied": False,
        "rule": "A proposed entity changes no text and no dictionary. The operator adds approved "
                "entries to the dictionary, and A2 runs again.",
        "dictionary_sha256": entities.sha256,
        "proposals": proposals,
    }
    # Both are derived from the checkpoints and the approvals, so a re-run rewrites them
    # deterministically; the checkpoints are the record that is never redrawn.
    atomic_write_text(canonical_json_bytes(plan).decode("utf-8"), out_dir / PLAN_FILE)
    atomic_write_text(canonical_json_bytes(queue).decode("utf-8"), out_dir / QUEUE_FILE)
    return RewriteResult("complete", out_dir / PLAN_FILE, out_dir / QUEUE_FILE, used, calls,
                         from_checkpoint, 0)
