"""Shared helpers for the checks that hold tier artifacts to their sources.

Two test files verify that an authored artifact quotes the document it cites:
`test_tier2b_biodiv_intake.py` for the Tier 2B call sources, and
`test_tier1_tier2a_ria_coverage.py` for the Tier 1 and Tier 2A ones. They ran
on copies of the same five helpers. The copies are here instead, so a fix to
the span sniffing or the digest basis reaches both.

Nothing here reads a tier artifact or asserts anything about one. It normalises
PDF text, digests a file on a declared basis, and walks a JSON tree for source
spans. The assertions stay in the test files, where the artifact they are about
is named.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Iterator

#: The four status categories of CLAUDE.md §12.2.
STATUSES = frozenset({"Confirmed", "Inferred", "Assumed", "Unresolved"})

#: The three keys that make a JSON object a source span.
SPAN_KEYS = frozenset({"quote", "source_document", "source_page"})

#: Line endings, named so a caller comparing bytes can apply the same rule
#: ``digest`` applies: core.autocrlf is true here, so a text file checks out
#: CRLF on Windows and LF elsewhere.
CRLF = b"\r\n"
LF = b"\n"


def norm(text: str) -> str:
    """Collapse a PDF's line breaks and runs of spaces to one space each."""
    return re.sub(r"\s+", " ", text).strip()


def digest(path: Path, basis: str) -> str:
    """A file's sha256 on the basis a registry entry declares.

    ``lf_normalised_bytes`` exists because core.autocrlf is true in this
    repository: a text file checks out CRLF on Windows and LF elsewhere, so a
    raw digest would identify the platform rather than the content.
    """
    raw = path.read_bytes()
    if basis == "lf_normalised_bytes":
        raw = raw.replace(b"\r\n", b"\n")
    elif basis != "raw_bytes":
        raise AssertionError("unknown digest_basis: " + basis)
    return hashlib.sha256(raw).hexdigest()


def iter_spans(node: object, where: str = "$") -> Iterator[tuple]:
    """Yield every source-span object in the tree, with the path that found it."""
    if isinstance(node, dict):
        if SPAN_KEYS <= set(node):
            yield where, node
            return
        for key, value in node.items():
            yield from iter_spans(value, where + "." + str(key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from iter_spans(value, where + "[" + str(index) + "]")


def iter_malformed_spans(node: object, where: str = "$") -> Iterator[tuple]:
    """Yield objects that look like a span but are missing one of its keys.

    ``iter_spans`` recognises a span only by holding all three keys, so a
    dropped or mistyped key does not fail a verbatim sweep: it removes the span
    from the sweep entirely and the sweep still reports green. This finds the
    near misses so that silence can be asserted against.
    """
    if isinstance(node, dict):
        present = SPAN_KEYS & set(node)
        if present and present != SPAN_KEYS:
            yield where, sorted(SPAN_KEYS - present)
            return
        if present == SPAN_KEYS:
            return
        for key, value in node.items():
            yield from iter_malformed_spans(value, where + "." + str(key))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from iter_malformed_spans(value, where + "[" + str(index) + "]")


def read_pdf_pages(pdf: Path, wanted: tuple) -> dict:
    """Normalised text of the wanted pages, keyed by printed page number.

    This deliberately does not skip when pymupdf is missing. Reading the source
    is the whole verification the callers exist to do, so an absent reader must
    turn the suite red rather than let it report green on checks that never ran
    (CLAUDE.md §15). pymupdf is declared in requirements.txt.
    """
    import pymupdf

    doc = pymupdf.open(pdf)
    try:
        return {n: norm(doc[n - 1].get_text()) for n in wanted}
    finally:
        doc.close()


def resolve_ref(node: object, ref: str):
    """Resolve a ``$.a.b[0]`` reference against a parsed JSON tree.

    Returns ``None`` when the reference does not resolve, which is what a
    span-reference check treats as a failure. Two test modules assert that an
    authored artifact's cross-references land somewhere real — the consortium
    gap analysis and the project concept — and both need the same walk.
    """
    assert ref.startswith("$"), ref
    current = node
    for part in ref[1:].split("."):
        if not part:
            continue
        name, _, rest = part.partition("[")
        if name:
            if not isinstance(current, dict) or name not in current:
                return None
            current = current[name]
        while rest:
            index_text, _, rest = rest.partition("]")
            if not isinstance(current, list):
                return None
            index = int(index_text)
            if index >= len(current):
                return None
            current = current[index]
            rest = rest.lstrip("[")
    return current


def iter_strings(node: object):
    """Yield every string in a parsed JSON tree, depth first."""
    if isinstance(node, dict):
        for value in node.values():
            yield from iter_strings(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_strings(value)
    elif isinstance(node, str):
        yield node
