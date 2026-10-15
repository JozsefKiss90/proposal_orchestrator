"""Deterministic redaction, stage A2 of the anonymisation pipeline (AN5).

AN5 of ``.scratch/msca-dn-anonymisation/tickets.md``, stage A2 of
``plans/msca_dn_anonymisation_handoff_2026-10-14.md``. Pure code, with no
model: :func:`redact` applies the operator's entity dictionary and the
identifier patterns of :mod:`runner.anonymisation_matching` to the document
that AN4's intake pinned, and writes the derivative and its edit log.

What it edits
-------------
* **Page text**, through AN4's PDF-route harness
  (:func:`runner.anonymisation_intake.apply_span_edits`), so only a document
  whose intake chose the submitted PDF can be redacted. A match broken across
  lines becomes one span per line: the first takes the replacement and the
  rest are removed. The replacement is the entry's first one that fits the
  first span's box at the span's point size. The box ends at the span's last
  character, except at a line end, where it runs to the right margin, taken
  as the page's left text margin mirrored. If no replacement fits, the run is
  refused, naming the entry id and the page: the operator adds a shorter
  replacement, or an empty one to declare a removal.
* **Information fields.** Author, creator and producer are cleared, because
  they name people and organisations and carry nothing an evaluator reads.
  Title, subject and keywords are matched like page text and take each
  entry's first replacement, with no width limit.
* **XMP** is removed whole. It repeats the information fields and can carry an
  editing history.
* **Embedded files** are renamed ``embedded_file_<n>`` with their extension
  kept, and their descriptions cleared. Their contents are kept and are not
  inspected here; the log says so.

What it does not edit: flagged entries (niche topics, figures), which are
located in the log for A3 and A5; countries, which the policy keeps; images
and line art; identifying numbers that no replacement in the dictionary fits;
and outlines, annotations, form fields and page labels. Stage A5's leak scan
(AN8a) is the independent check of what remains.

Replay
------
Same input, same policy hash and same dictionary hash give byte-equal output.
Every step is deterministic, the file identifier is not regenerated, and the
embedded files keep their recorded dates. After the derivative is built, it is
matched again, and any remaining edited entry or pattern refuses the run
before anything is written. That is a self-check by the same code, not A5.

What is private
---------------
Everything this module reads and writes: the original, the dictionary, the
derivative and the edit log. Every path inside this repository is refused
(the V17/V18 pattern). The edit log records span locations, categories, entry
ids and form kinds. It quotes no text, original or replacement, and names no
file.

Constitutional standing: an authoring tool, not a runtime component. It
evaluates no gate, invokes no model and writes no Tier 5 artifact
(CLAUDE.md §13.3). It is not a §17.5.3 deterministic component: no manifest
node binds it.
"""

from __future__ import annotations

import hashlib
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple, Optional

from runner import anonymisation_intake as intake
from runner.anonymisation_matching import (
    NORMALISATIONS,
    REGEX_PATTERNS,
    EntityDictionary,
    Match,
    find_matches,
    load_dictionary,
)
from runner.anonymisation_policy import LoadedPolicy, require_hash
from runner.atomic_write import atomic_write_text, atomic_write_via, canonical_json_bytes

SCHEMA = "anonymisation_redaction/1"
RECORD_TYPE = "anonymisation_redaction"

DERIVATIVE_FILE = "redacted.pdf"
EDIT_LOG_FILE = "redaction_log.json"

#: Information fields that are cleared, and those that are matched.
CLEARED_FIELDS: tuple[str, ...] = ("author", "creator", "producer")
MATCHED_FIELDS: tuple[str, ...] = ("title", "subject", "keywords")
_KEPT_FIELDS: tuple[str, ...] = ("creationDate", "modDate", "trapped")

_EXTENSION = re.compile(r"^\.[A-Za-z0-9]{1,5}$")


class RedactionRefused(RuntimeError):
    """The redaction cannot be applied as asked. Nothing was written."""


@dataclass(frozen=True)
class RedactionResult:
    derivative: Path
    edit_log: Path
    derivative_sha256: str


class _Char(NamedTuple):
    c: str
    bbox: tuple[float, float, float, float]
    size: float
    line: tuple[int, int]


# --------------------------------------------------------------------------- #
# Page text
# --------------------------------------------------------------------------- #


def _page_stream(page: Any) -> tuple[str, list[Optional[_Char]]]:
    """The page's text with a line break after each line, and each character's record."""
    text: list[str] = []
    chars: list[Optional[_Char]] = []
    for b, block in enumerate(page.get_text("rawdict")["blocks"]):
        for n, line in enumerate(block.get("lines", ())):
            for span in line["spans"]:
                for char in span["chars"]:
                    text.append(char["c"])
                    chars.append(_Char(char["c"], tuple(char["bbox"]),
                                       round(float(span["size"]), 2), (b, n)))
            text.append("\n")
            chars.append(None)
    return "".join(text), chars


_Rect = tuple[float, float, float, float]


def _union(chars: list[_Char]) -> _Rect:
    return (
        min(c.bbox[0] for c in chars),
        min(c.bbox[1] for c in chars),
        max(c.bbox[2] for c in chars),
        max(c.bbox[3] for c in chars),
    )


def _pieces(match: Match, chars: list[Optional[_Char]]) -> list[list[_Char]]:
    """The match's visible characters, one list per text line, in reading order."""
    by_line: dict[tuple[int, int], list[_Char]] = {}
    for char in chars[match.start:match.end]:
        if char is not None and not char.c.isspace():
            by_line.setdefault(char.line, []).append(char)
    return list(by_line.values())


def _extend_at_line_end(rect: _Rect, piece: list[_Char], page_chars: list[_Char],
                        page_x1: float) -> _Rect:
    """*rect* run to the right margin when nothing follows it on its line."""
    own = {id(c) for c in piece}
    for c in page_chars:
        if id(c) in own:
            continue
        middle = (c.bbox[1] + c.bbox[3]) / 2
        if rect[1] <= middle <= rect[3] and c.bbox[0] >= rect[2] - 0.5:
            return rect
    margin = min(c.bbox[0] for c in page_chars)
    return (rect[0], rect[1], max(rect[2], page_x1 - margin), rect[3])


def _choose(match: Match, size: float, budget: float, page: int) -> int:
    import pymupdf

    for index, replacement in enumerate(match.replacements):
        used = pymupdf.get_text_length(replacement, fontname=intake.REPLACEMENT_FONT, fontsize=size)
        if used <= budget + 1e-6:
            return index
    who = f"entry {match.entry_id}" if match.entry_id else f"regex class {match.regex_class}"
    raise RedactionRefused(
        f"{who} on page {page}: no replacement fits the span's {budget:.1f} pt box at {size} pt. "
        f"Add a shorter replacement to the dictionary, or an empty one to declare a removal."
    )


def _who(match: Match) -> dict[str, Any]:
    return {
        "category": match.category,
        "entry_id": match.entry_id,
        "regex_class": match.regex_class,
        "form": match.form,
    }


def _plan_page(doc: Any, number: int, dictionary: EntityDictionary
               ) -> tuple[list[intake.SpanEdit], list[dict[str, Any]], list[dict[str, Any]]]:
    page = doc[number - 1]
    text, chars = _page_stream(page)
    page_chars = [c for c in chars if c is not None and not c.c.isspace()]
    edits: list[intake.SpanEdit] = []
    entries: list[dict[str, Any]] = []
    flags: list[dict[str, Any]] = []
    for match in find_matches(text, dictionary):
        pieces = _pieces(match, chars)
        if not pieces:
            continue
        if match.action == "flag":
            flags.append({**_who(match), "page": number,
                          "rects": [[round(v, 3) for v in _union(p)] for p in pieces]})
            continue
        for k, piece in enumerate(pieces):
            rect = _union(piece)
            chosen: Optional[int] = None
            replacement = ""
            if k == 0:
                rect = _extend_at_line_end(rect, piece, page_chars, page.rect.x1)
                sizes = {c.size for c in piece}
                size = max(sizes)
                chosen = _choose(match, size, rect[2] - rect[0], number)
                replacement = match.replacements[chosen]
            edits.append(intake.SpanEdit(page=number, rect=rect, replacement=replacement))
            entries.append({
                **_who(match),
                "piece": k,
                "pieces": len(pieces),
                "replacement_index": chosen,
                "removed": replacement == "",
            })
    return edits, entries, flags


# --------------------------------------------------------------------------- #
# Metadata, XMP and embedded files
# --------------------------------------------------------------------------- #


def _apply_to_string(value: str, dictionary: EntityDictionary) -> tuple[str, list[dict[str, Any]]]:
    out: list[str] = []
    applied: list[dict[str, Any]] = []
    last = 0
    for match in find_matches(value, dictionary):
        if match.action != "edit":
            continue
        out.append(value[last:match.start])
        out.append(match.replacements[0])
        applied.append(_who(match))
        last = match.end
    out.append(value[last:])
    return "".join(out), applied


def _scrub_information(doc: Any, dictionary: EntityDictionary) -> list[dict[str, Any]]:
    metadata = doc.metadata or {}
    new: dict[str, str] = {key: metadata.get(key) or "" for key in _KEPT_FIELDS}
    log: list[dict[str, Any]] = []
    for field in CLEARED_FIELDS:
        new[field] = ""
        log.append({"field": field, "action": "cleared" if metadata.get(field) else "empty"})
    for field in MATCHED_FIELDS:
        value, applied = _apply_to_string(metadata.get(field) or "", dictionary)
        new[field] = value
        log.append({"field": field, "action": "redacted" if applied else "unchanged",
                    "edits": applied})
    doc.set_metadata(new)
    return log


def _scrub_xmp(doc: Any) -> str:
    if not doc.get_xml_metadata():
        return "absent"
    doc.del_xml_metadata()
    return "removed"


def _scrub_embedded_files(doc: Any) -> list[dict[str, Any]]:
    files = []
    for index in range(doc.embfile_count()):
        files.append((doc.embfile_info(index), doc.embfile_get(index)))
    for _ in files:
        doc.embfile_del(0)
    log = []
    for n, (info, data) in enumerate(files, start=1):
        suffix = Path(info.get("name") or "").suffix
        name = f"embedded_file_{n}{suffix if _EXTENSION.match(suffix) else ''}"
        xref = doc.embfile_add(name, data, filename=name, ufilename=name, desc="")
        # The dates the original recorded, not today's: replay is byte-equal.
        for key, field in (("Params/CreationDate", "creationDate"), ("Params/ModDate", "modDate")):
            value = info.get(field)
            doc.xref_set_key(xref, key, f"({value})" if value else "null")
        log.append({"index": n, "action": "renamed", "description": "cleared",
                    "content": "kept, not inspected by A2"})
    return log


# --------------------------------------------------------------------------- #
# The self-check
# --------------------------------------------------------------------------- #


def _residual(data: bytes, dictionary: EntityDictionary) -> list[dict[str, Any]]:
    """Every edited entry or pattern still found in the derivative, by location."""
    import pymupdf

    found: list[dict[str, Any]] = []
    doc = pymupdf.open(stream=data, filetype="pdf")
    try:
        for number in range(1, doc.page_count + 1):
            text, _ = _page_stream(doc[number - 1])
            found += [{**_who(m), "page": number} for m in find_matches(text, dictionary)
                      if m.action == "edit"]
        for field in (*CLEARED_FIELDS, *MATCHED_FIELDS):
            found += [{**_who(m), "field": field}
                      for m in find_matches((doc.metadata or {}).get(field) or "", dictionary)
                      if m.action == "edit"]
        if doc.get_xml_metadata():
            found.append({"layer": "xmp"})
        for name in doc.embfile_names():
            found += [{**_who(m), "layer": "embedded_file_name"}
                      for m in find_matches(name, dictionary) if m.action == "edit"]
    finally:
        doc.close()
    return found


# --------------------------------------------------------------------------- #
# Redaction
# --------------------------------------------------------------------------- #


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def redact(
    *,
    pdf: Path,
    intake_record: Path,
    policy: LoadedPolicy,
    policy_sha256: str,
    dictionary: Path,
    dictionary_sha256: str,
    out_dir: Path,
) -> RedactionResult:
    """Apply *dictionary* to the PDF *intake_record* pinned; write the derivative and its log.

    *policy* must hash to *policy_sha256*, and the dictionary to
    *dictionary_sha256*, taken over its parsed record like the policy's.
    Every refusal runs before the first
    write. A re-run that would write the same bytes is a no-op; one that would
    write different bytes is refused, because a written derivative is never
    overwritten.
    """
    import pymupdf

    pdf = intake.require_private(pdf, "the PDF to redact")
    intake_record = intake.require_private(intake_record, "the intake record")
    dictionary_path = intake.require_private(dictionary, "the entity dictionary")
    out_dir = intake.require_private(out_dir, "the redaction directory")
    require_hash(policy, policy_sha256)
    entities = load_dictionary(dictionary_path, policy)
    if entities.sha256 != dictionary_sha256:
        raise RedactionRefused(
            f"the entity dictionary hashes to {entities.sha256}, not the declared "
            f"{dictionary_sha256}: this is not the pinned dictionary. Nothing was written."
        )
    input_sha = intake.pin(pdf, intake.require_pdf_route(intake_record), "the PDF to redact")

    doc = pymupdf.open(pdf)
    try:
        edits: list[intake.SpanEdit] = []
        planned: list[dict[str, Any]] = []
        flags: list[dict[str, Any]] = []
        for number in range(1, doc.page_count + 1):
            page_edits, page_entries, page_flags = _plan_page(doc, number, entities)
            edits += page_edits
            planned += page_entries
            flags += page_flags
    finally:
        doc.close()

    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out_dir) as scratch:
        text_only = Path(scratch) / "text_redacted.pdf"
        harness_log = intake.apply_span_edits(pdf, intake_record, edits, text_only)
        doc = pymupdf.open(text_only)
        try:
            information = _scrub_information(doc, entities)
            xmp = _scrub_xmp(doc)
            embedded = _scrub_embedded_files(doc)
            data = doc.tobytes(garbage=4, deflate=True, no_new_id=True)
        finally:
            doc.close()

    residual = _residual(data, entities)
    if residual:
        raise RedactionRefused(
            f"the derivative still matches {len(residual)} edited entr(ies) or pattern(s) "
            f"after redaction: {residual}. Nothing was written."
        )

    record = {
        "schema": SCHEMA,
        "record_type": RECORD_TYPE,
        "stage": "A2",
        "purpose": (
            "The edit log of the deterministic redaction: where each dictionary entry and "
            "identifier pattern was replaced or removed, and what was scrubbed from the metadata."
        ),
        "input": {"sha256": input_sha, "intake_record_sha256": _sha(intake_record.read_bytes())},
        "policy_sha256": policy.sha256,
        "dictionary_sha256": entities.sha256,
        "output": {"file": DERIVATIVE_FILE, "sha256": _sha(data), "bytes": len(data)},
        "normalisations": list(NORMALISATIONS),
        "regex_classes": list(REGEX_PATTERNS),
        "page_text": {
            "edits": [{**entry, **logged} for entry, logged in zip(planned, harness_log)],
            "flags": flags,
        },
        "information_fields": information,
        "xmp": xmp,
        "embedded_files": embedded,
        "kept": [
            {"entry_id": e.id, "category": e.category, "reason": "the policy retains the country"}
            for e in entities.entries if e.action == "keep"
        ],
        "replay": {
            "rule": (
                "Same input, same policy hash and same dictionary hash give byte-equal output."
            ),
            "environment": {"pymupdf": pymupdf.VersionBind},
        },
        "privacy": {
            "declared_status": "Confirmed",
            "claim": (
                "This log records locations, categories, entry ids and form kinds. It quotes no "
                "text, original or replacement, and names no file."
            ),
            "basis": "Every path this redaction read or wrote was refused if it resolved inside "
                     "the repository.",
        },
    }
    files = {DERIVATIVE_FILE: data, EDIT_LOG_FILE: canonical_json_bytes(record)}
    for name, content in files.items():
        existing = out_dir / name
        if existing.exists() and existing.read_bytes() != content:
            raise RedactionRefused(
                f"{out_dir.name} already holds a derivative that differs from this one ({name}). "
                f"The input, the policy, the dictionary or the PyMuPDF build differs. A written "
                f"derivative is never overwritten; redact into a new directory."
            )
    def write_derivative(tmp: str) -> None:
        Path(tmp).write_bytes(data)

    if not (out_dir / DERIVATIVE_FILE).exists():
        atomic_write_via(out_dir / DERIVATIVE_FILE, write_derivative)
    if not (out_dir / EDIT_LOG_FILE).exists():
        atomic_write_text(files[EDIT_LOG_FILE].decode("utf-8"), out_dir / EDIT_LOG_FILE)
    return RedactionResult(
        derivative=out_dir / DERIVATIVE_FILE,
        edit_log=out_dir / EDIT_LOG_FILE,
        derivative_sha256=_sha(data),
    )
