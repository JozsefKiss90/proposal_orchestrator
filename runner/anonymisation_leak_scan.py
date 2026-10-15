"""The deterministic leak scan, the first half of stage A5 (AN8a).

AN8a of ``.scratch/msca-dn-anonymisation/tickets.md``, stage A5 of
``plans/msca_dn_anonymisation_handoff_2026-10-14.md``. Pure code, with no
model: :func:`leak_scan` reads a derivative and reports every place where an
entity dictionary entry or an identifier pattern of
:mod:`runner.anonymisation_matching` still matches. Any hit fails the
derivative. The model attack (AN8b) is the second half.

What it reads
-------------
:data:`LAYERS`, each scanned with every normalisation on:

``page_text``
    every character PyMuPDF extracts, headers, footers, tables and figure
    text layers included. Text outside the page box is read too, although the
    default extraction (and so A2) clips it.
``information_field``
    every string in the document information dictionary, custom keys included.
``xmp``
    the XMP packet, with XML character references decoded.
``embedded_file``
    each embedded file's name, file names and description.
``outline``, ``annotation``, ``link``, ``form_field``
    bookmark titles, annotation text, link targets and form field names and
    values. A2 declares that it does not edit these, so the scan is where a
    name left in them shows.

What it does not read, and says so in the report (:data:`NOT_SCANNED`): image
pixels and line art, embedded file contents, page labels, and identifying
numbers that no dictionary entry names.

Independence from A2
--------------------
The scan shares A2's matcher, because both must answer the same question, but
not A2's extraction or its result. It extracts the text again, in its own
order and without clipping, reads metadata from the information dictionary
rather than from A2's field list, and imports the matcher by module, so a
weakened A2 does not weaken the scan. The mutation test in
``tests/runner/test_anonymisation_leak_scan.py`` shows it: an A2 run with one
normalisation off passes its own self-check and fails this scan.

Hits and review
---------------
A **hit** is an edited entry or a pattern, and fails the derivative. Two
kinds of finding do not fail, and are listed for **review**:

``flagged_category``
    an entry whose category the policy flags rather than edits (a niche
    topic). A3 and the model attack decide it.
``case_variant``
    an entry the operator declared ``match_case``, such as an acronym that is
    also a word, found only when case is folded. The scan honours the
    declaration, because ignoring it would fail every document that uses the
    word, and lists the occurrence so the operator reads it.

Countries the policy keeps are not matched.

What is private
---------------
The derivative, the dictionary and the report. Every path inside this
repository is refused (the V17/V18 pattern). The report records layers,
pages, rectangles, field names, categories, entry ids and form kinds. It
quotes no text and names no file.

Constitutional standing: an authoring tool, not a runtime component. It
evaluates no gate, invokes no model and writes no Tier 5 artifact
(CLAUDE.md §13.3). No manifest node binds it.
"""

from __future__ import annotations

import dataclasses
import hashlib
import html
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional

from runner import anonymisation_intake as intake
from runner import anonymisation_matching as matching
from runner.anonymisation_policy import LoadedPolicy, require_hash
from runner.atomic_write import atomic_write_text, canonical_json_bytes

SCHEMA = "anonymisation_leak_scan/1"
RECORD_TYPE = "anonymisation_leak_scan"

REPORT_FILE = "leak_scan.json"

#: Every layer the scan reads, in report order.
LAYERS: tuple[str, ...] = (
    "page_text",
    "information_field",
    "xmp",
    "embedded_file",
    "outline",
    "annotation",
    "link",
    "form_field",
)

#: What the scan cannot read, and who reads it instead.
NOT_SCANNED: tuple[dict[str, str], ...] = (
    {"layer": "image_pixels_and_line_art", "read_by": "A6 figure review and the AN8b attack"},
    {"layer": "embedded_file_contents", "read_by": "the operator (A7)"},
    {"layer": "page_labels", "read_by": "the operator (A7)"},
    {"layer": "identifying_numbers_without_a_dictionary_entry", "read_by": "A3, A4 and AN8b"},
)

_EMBEDDED_FIELDS = ("name", "filename", "ufilename", "description")
_ANNOTATION_FIELDS = ("content", "title", "subject")

#: Information dictionary keys reported by name. Any other key is the
#: document's own, and its name may itself identify, so it is reported by
#: position as ``custom_<n>``.
_STANDARD_INFO_KEYS = frozenset(
    {"Title", "Author", "Subject", "Keywords", "Creator", "Producer", "CreationDate", "ModDate",
     "Trapped"}
)
_METADATA_FIELDS = {"title": "Title", "author": "Author", "subject": "Subject",
                    "keywords": "Keywords", "creator": "Creator", "producer": "Producer"}


class LeakScanRefused(RuntimeError):
    """The scan cannot run as asked. Nothing was written."""


@dataclass(frozen=True)
class LeakScanResult:
    report: Path
    passed: bool
    counts: dict[str, dict[str, int]]


# --------------------------------------------------------------------------- #
# Matching
# --------------------------------------------------------------------------- #


class _Scanner:
    """The dictionary, and the same dictionary with every case declaration folded."""

    def __init__(self, dictionary: matching.EntityDictionary) -> None:
        self.dictionary = dictionary
        self.case_ids = {e.id for e in dictionary.entries if e.match_case}
        self.folded = dataclasses.replace(
            dictionary,
            entries=tuple(dataclasses.replace(e, match_case=False) for e in dictionary.entries),
        )

    def __call__(self, text: str) -> Iterator[tuple[matching.Match, Optional[str]]]:
        """Each match in *text*, with ``None`` for a hit or the reason it is for review."""
        strict = matching.find_matches(text, self.dictionary)
        for match in strict:
            yield match, (None if match.action == "edit" else "flagged_category")
        if not self.case_ids:
            return
        for match in matching.find_matches(text, self.folded):
            # Text already reported, as a hit or for review, is not listed twice.
            if match.entry_id in self.case_ids and not any(
                m.start < match.end and match.start < m.end for m in strict
            ):
                yield match, "case_variant"


def _finding(match: matching.Match, reason: Optional[str], **where: Any) -> dict[str, Any]:
    finding = {
        **where,
        "category": match.category,
        "entry_id": match.entry_id,
        "regex_class": match.regex_class,
        "form": match.form,
    }
    if reason is not None:
        finding["reason"] = reason
    return finding


def _scan_string(scanner: _Scanner, text: Any, **where: Any) -> Iterator[dict[str, Any]]:
    if isinstance(text, str) and text:
        for match, reason in scanner(text):
            yield _finding(match, reason, **where)


# --------------------------------------------------------------------------- #
# Layers
# --------------------------------------------------------------------------- #


def _page_text(doc: Any, scanner: _Scanner) -> Iterator[dict[str, Any]]:
    import pymupdf

    # The default extraction clips text to the page box; a leak outside it
    # still leaks. Both the flag and an unbounded clip are needed.
    flags = pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_MEDIABOX_CLIP
    for number, page in enumerate(doc, start=1):
        text: list[str] = []
        boxes: list[Optional[tuple[tuple[int, int], tuple[float, ...]]]] = []
        raw = page.get_text("rawdict", flags=flags, clip=pymupdf.INFINITE_RECT(), sort=True)
        for b, block in enumerate(raw["blocks"]):
            for n, line in enumerate(block.get("lines", ())):
                for span in line["spans"]:
                    for char in span["chars"]:
                        text.append(char["c"])
                        boxes.append(((b, n), tuple(char["bbox"])))
                text.append("\n")
                boxes.append(None)
        for match, reason in scanner("".join(text)):
            by_line: dict[tuple[int, int], list[tuple[float, ...]]] = {}
            for i in range(match.start, match.end):
                box = boxes[i]
                if box is not None and not text[i].isspace():
                    by_line.setdefault(box[0], []).append(box[1])
            rects = [
                [round(min(r[0] for r in rs), 3), round(min(r[1] for r in rs), 3),
                 round(max(r[2] for r in rs), 3), round(max(r[3] for r in rs), 3)]
                for rs in by_line.values()
            ]
            yield _finding(match, reason, layer="page_text", page=number, rects=rects)


def _information_fields(doc: Any, scanner: _Scanner) -> Iterator[dict[str, Any]]:
    kind, value = doc.xref_get_key(-1, "Info")
    if kind != "xref":
        # An inline dictionary: PyMuPDF still decodes its standard fields.
        for name, field in _METADATA_FIELDS.items():
            yield from _scan_string(scanner, (doc.metadata or {}).get(name),
                                    layer="information_field", field=field)
        return
    xref = int(value.split()[0])
    custom = 0
    for key in doc.xref_get_keys(xref):
        if key not in _STANDARD_INFO_KEYS:
            custom += 1
        field = key if key in _STANDARD_INFO_KEYS else f"custom_{custom}"
        kind, text = doc.xref_get_key(xref, key)
        if kind == "string":
            yield from _scan_string(scanner, text, layer="information_field", field=field)


def _xmp(doc: Any, scanner: _Scanner) -> Iterator[dict[str, Any]]:
    yield from _scan_string(scanner, html.unescape(doc.get_xml_metadata() or ""), layer="xmp")


def _embedded_files(doc: Any, scanner: _Scanner) -> Iterator[dict[str, Any]]:
    for index in range(doc.embfile_count()):
        info = doc.embfile_info(index)
        for field in _EMBEDDED_FIELDS:
            yield from _scan_string(scanner, info.get(field), layer="embedded_file",
                                    index=index + 1, field=field)


def _outline(doc: Any, scanner: _Scanner) -> Iterator[dict[str, Any]]:
    for index, item in enumerate(doc.get_toc(simple=True), start=1):
        yield from _scan_string(scanner, item[1], layer="outline", index=index, field="title")


def _annotations(doc: Any, scanner: _Scanner) -> Iterator[dict[str, Any]]:
    for number, page in enumerate(doc, start=1):
        for index, annot in enumerate(page.annots(), start=1):
            info = annot.info
            for field in _ANNOTATION_FIELDS:
                yield from _scan_string(scanner, info.get(field), layer="annotation", page=number,
                                        index=index, field=field)


def _links(doc: Any, scanner: _Scanner) -> Iterator[dict[str, Any]]:
    for number, page in enumerate(doc, start=1):
        for index, link in enumerate(page.get_links(), start=1):
            for field in ("uri", "file"):
                yield from _scan_string(scanner, link.get(field), layer="link", page=number,
                                        index=index, field=field)


def _form_fields(doc: Any, scanner: _Scanner) -> Iterator[dict[str, Any]]:
    for number, page in enumerate(doc, start=1):
        for index, widget in enumerate(page.widgets(), start=1):
            for field in ("field_name", "field_label", "field_value"):
                yield from _scan_string(scanner, getattr(widget, field, None), layer="form_field",
                                        page=number, index=index, field=field)


_READERS = {
    "page_text": _page_text,
    "information_field": _information_fields,
    "xmp": _xmp,
    "embedded_file": _embedded_files,
    "outline": _outline,
    "annotation": _annotations,
    "link": _links,
    "form_field": _form_fields,
}


def scan(data: bytes, dictionary: matching.EntityDictionary) -> tuple[list[dict], list[dict]]:
    """``(hits, review)`` for the PDF *data*, every layer in :data:`LAYERS` order."""
    import pymupdf

    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as exc:  # PyMuPDF raises several types for a bad file.
        raise LeakScanRefused(
            f"the derivative cannot be opened as a PDF: {type(exc).__name__}. Nothing was written."
        ) from exc
    scanner = _Scanner(dictionary)
    hits: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    try:
        for layer in LAYERS:
            for finding in _READERS[layer](doc, scanner):
                (review if "reason" in finding else hits).append(finding)
    finally:
        doc.close()
    return hits, review


# --------------------------------------------------------------------------- #
# The scan
# --------------------------------------------------------------------------- #


def _counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(f["category"] for f in findings).items()))


def leak_scan(
    *,
    derivative: Path,
    policy: LoadedPolicy,
    policy_sha256: str,
    dictionary: Path,
    dictionary_sha256: str,
    out_dir: Path,
) -> LeakScanResult:
    """Scan *derivative* with the pinned dictionary and write the report into *out_dir*.

    *policy* must hash to *policy_sha256*, and the dictionary to
    *dictionary_sha256*. A failing scan is a result, not a refusal: the report
    is written and :attr:`LeakScanResult.passed` is false. A re-run that would
    write the same report is a no-op; one that would write a different report
    is refused, because a written report is never overwritten.
    """
    import pymupdf

    derivative = intake.require_private(derivative, "the derivative to scan")
    dictionary_path = intake.require_private(dictionary, "the entity dictionary")
    out_dir = intake.require_private(out_dir, "the leak scan directory")
    require_hash(policy, policy_sha256)
    entities = matching.load_dictionary(dictionary_path, policy)
    if entities.sha256 != dictionary_sha256:
        raise LeakScanRefused(
            f"the entity dictionary hashes to {entities.sha256}, not the declared "
            f"{dictionary_sha256}: this is not the pinned dictionary. Nothing was written."
        )
    try:
        data = derivative.read_bytes()
    except OSError as exc:
        raise LeakScanRefused(
            f"the derivative cannot be opened: {type(exc).__name__}. Nothing was written."
        ) from exc
    hits, review = scan(data, entities)
    counts = {"hits": _counts(hits), "review": _counts(review)}

    record = {
        "schema": SCHEMA,
        "record_type": RECORD_TYPE,
        "stage": "A5",
        "purpose": (
            "The deterministic leak scan of a derivative: every place where an entity "
            "dictionary entry or an identifier pattern still matches. Any hit fails the "
            "derivative."
        ),
        "input": {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)},
        "policy_sha256": policy.sha256,
        "dictionary_sha256": entities.sha256,
        "normalisations": list(matching.NORMALISATIONS),
        "regex_classes": list(matching.REGEX_PATTERNS),
        "coverage": {"scanned": list(LAYERS), "not_scanned": list(NOT_SCANNED)},
        "verdict": "fail" if hits else "pass",
        "counts": counts,
        "hits": hits,
        "review": review,
        "replay": {
            "rule": "Same derivative, same policy hash and same dictionary hash give a "
                    "byte-equal report.",
            "environment": {"pymupdf": pymupdf.VersionBind},
        },
        "privacy": {
            "declared_status": "Confirmed",
            "claim": (
                "This report records layers, pages, rectangles, field names, categories, entry "
                "ids and form kinds. It quotes no text and names no file."
            ),
            "basis": "Every path this scan read or wrote was refused if it resolved inside the "
                     "repository.",
        },
    }
    content = canonical_json_bytes(record)
    target = out_dir / REPORT_FILE
    if target.exists():
        if target.read_bytes() != content:
            raise LeakScanRefused(
                f"{out_dir.name} already holds a leak scan report that differs from this one. "
                f"The derivative, the policy, the dictionary or the PyMuPDF build differs. A "
                f"written report is never overwritten; scan into a new directory."
            )
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(content.decode("utf-8"), target)
    return LeakScanResult(report=target, passed=not hits, counts=counts)
