"""Table 1.4.1 synthesis, stage A4 of the anonymisation pipeline (AN7).

AN7 of ``.scratch/msca-dn-anonymisation/tickets.md``, stage A4 of
``plans/msca_dn_anonymisation_handoff_2026-10-14.md``. Pure code, with no
model. :func:`synthesise` replaces the supervisor table's identifying cells
with synthetic ones and keeps the table. Removing the table would bias the
Implementation score, so its rows, columns and rules stay where they are.

The table specification
-----------------------
The operator authors a private ``anonymisation_table_spec/1`` record. It names
the table (page, index under :data:`TABLE_STRATEGY`, header rows) and declares
every column once, with the header the column must carry and one rule. The
header is checked against the last header row only:

* ``keep``: the cell is left as A2 left it. For degree level and DN role.
* ``pseudonym``: the cell must hold an A2 replacement of the declared category
  (``person_name`` or ``institution``). A4 keeps it and checks it. It never
  invents a pseudonym, so a supervisor carries the dictionary's code here and
  everywhere else A2 replaced them. A cell with no A2 edit is refused: the
  operator adds the entity to the dictionary and runs A2 again. Exactly one
  ``person_name`` pseudonym column is the row key: the row's supervisor.
* ``band``: the cell's whole number is replaced by the declared band holding
  it, written ``lo to hi`` or ``lo or more``, or ``lo-hi`` and ``lo+`` when
  the long form does not fit. Bands are sorted, do not overlap, and the only
  open one is last. A band of one value is refused, because it keeps the exact
  metric. The column header carries the measure, so the cell carries the band
  alone (the policy's ``{measure} {band}``).
* ``map``: the cell's text is replaced by the operator's mapped value, such as
  a kind of expertise for a named one. A value missing from the map is refused.

Why the operator maps and code does not: which career stage or kind of
expertise an evaluator reads is a judgment, and CLAUDE.md §10.6 forbids
supplying it from programme knowledge.

The pseudonym check
-------------------
Every ``person_name`` entry of the dictionary must carry one code in all its
replacements, and no two entries may share one (:func:`person_codes`). The
policy's ``{role} {code}`` pattern asks for both. A table cell must read its
entity's code. So one code stands for one supervisor in the table and in every
place A2 replaced them, and the row map records how many such places there are.

What it edits and what it writes
--------------------------------
The A2 derivative, pinned by the hash A2's log records, through AN4's edit
harness for stage outputs (:func:`runner.anonymisation_intake.apply_stage_edits`).
Each band or map cell is one span edit, from its first character to the cell's
right rule less :data:`CELL_INSET`. Only text changes: the rules stay. Before
anything is written, the output is measured again. The table must have the
same frame, row count, column count and cell boxes, and every cell must read
what the synthesis intended.

Three private files: the derivative, the synthesis log and the row map. The
log records locations, rules and counts and quotes no text. The **row map**
records, per row, the supervisor's entry id and pseudonym and each cell's
source and synthetic values. It is part of the mapping table, D4 forever.

What it does not do
-------------------
It edits no identifying number outside the table, such as an h-index in
prose. That is A3's (AN6). It applies no A3 plan. It does not re-run the leak
scan; AN8a does that on the derivative.

What is private
---------------
Everything this module reads and writes. Every path inside this repository is
refused (the V17/V18 pattern).

Constitutional standing: an authoring tool, not a runtime component. It
evaluates no gate, invokes no model and writes no Tier 5 artifact
(CLAUDE.md §11.4, §13.10). It is not a §17.5.3 deterministic component: no manifest
node binds it.
"""

from __future__ import annotations

import hashlib
import json
import re
import tempfile
from dataclasses import dataclass
from dataclasses import field as _default
from pathlib import Path
from typing import Any, Mapping, Optional

from runner import anonymisation_intake as intake
from runner.anonymisation_matching import EntityDictionary, Entry, load_dictionary
from runner.anonymisation_policy import LoadedPolicy, require_hash
from runner.anonymisation_policy import policy_sha256 as record_sha256
from runner.atomic_write import atomic_write_text, atomic_write_via, canonical_json_bytes
from runner.external_proposal import TABLE_STRATEGY

SCHEMA = "anonymisation_table_synthesis/1"
RECORD_TYPE = "anonymisation_table_synthesis"
ROW_MAP_SCHEMA = "anonymisation_table_row_map/1"
ROW_MAP_RECORD_TYPE = "anonymisation_table_row_map"
SPEC_SCHEMA = "anonymisation_table_spec/1"
SPEC_RECORD_TYPE = "anonymisation_table_spec"
REDACTION_SCHEMA = "anonymisation_redaction/1"

DERIVATIVE_FILE = "synthesised.pdf"
LOG_FILE = "table_synthesis_log.json"
ROW_MAP_FILE = "table_row_map.json"

RULES: tuple[str, ...] = ("keep", "pseudonym", "band", "map")
#: The categories a pseudonym column may hold, each replaced under the policy.
PSEUDONYM_CATEGORIES: tuple[str, ...] = ("person_name", "institution")
#: Points kept clear of a cell's right rule.
CELL_INSET = 1.0

#: A pseudonym code: a letter and a number, as the policy's patterns ask.
_CODE = re.compile(r"\b[A-Z][0-9]+\b")
_NUMBER = re.compile(r"^(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)$")


class TableRefused(RuntimeError):
    """The table cannot be synthesised as asked. Nothing was written."""


@dataclass(frozen=True)
class SynthesisResult:
    derivative: Path
    log: Path
    row_map: Path
    derivative_sha256: str


@dataclass(frozen=True)
class Column:
    index: int
    header: str
    field: str
    rule: str
    category: Optional[str] = None
    row_key: bool = False
    bands: tuple[tuple[int, Optional[int]], ...] = ()
    mapping: Mapping[str, str] = _default(default_factory=dict)


@dataclass(frozen=True)
class TableSpec:
    sha256: str
    page: int
    index: int
    header_rows: int
    columns: tuple[Column, ...]


# --------------------------------------------------------------------------- #
# The specification
# --------------------------------------------------------------------------- #


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _bands(raw: Any, where: str, problems: list[str]) -> tuple[tuple[int, Optional[int]], ...]:
    if not isinstance(raw, list) or not raw:
        problems.append(f"{where}: a band column declares a non-empty list of bands")
        return ()
    out: list[tuple[int, Optional[int]]] = []
    for n, band in enumerate(raw):
        ok = (isinstance(band, list) and len(band) == 2 and _is_int(band[0]) and band[0] >= 0
              and (band[1] is None or _is_int(band[1])))
        if not ok:
            problems.append(f"{where}: band {n} is not [low, high] with whole numbers, "
                            f"high null for an open band")
            return ()
        low, high = band
        if high is None and n != len(raw) - 1:
            problems.append(f"{where}: band {n} is open, and only the last band may be open")
        if high is not None and high <= low:
            problems.append(f"{where}: band {n} holds one value or none, so it keeps the exact "
                            f"metric; a band spans at least two values")
        previous = out[-1][1] if out else -1
        if previous is None or low <= previous:
            problems.append(f"{where}: bands {n - 1} and {n} overlap or are out of order")
        out.append((low, high))
    return tuple(out)


def _column(raw: Any, n: int, policy: LoadedPolicy, problems: list[str]) -> Optional[Column]:
    where = f"column entry {n}"
    if not isinstance(raw, dict):
        problems.append(f"{where} is not an object")
        return None
    index = raw.get("index")
    if _is_int(index):
        where = f"column {index}"
    rule = raw.get("rule")
    if not (isinstance(index, int) and not isinstance(index, bool) and index >= 0):
        problems.append(f"{where}: index is a whole number from 0")
    for key in ("header", "field"):
        if not (isinstance(raw.get(key), str) and raw[key].strip()):
            problems.append(f"{where}: {key} is a non-empty string")
    if rule not in RULES:
        problems.append(f"{where}: the rule is one of {', '.join(RULES)}")
        return None
    rules = {c.id: c.rule for c in policy.categories}
    category = raw.get("category")
    bands: tuple[tuple[int, Optional[int]], ...] = ()
    mapping: dict[str, str] = {}
    if rule == "pseudonym":
        if category not in PSEUDONYM_CATEGORIES:
            problems.append(f"{where}: a pseudonym column's category is one of "
                            f"{', '.join(PSEUDONYM_CATEGORIES)}")
        elif rules.get(category) != "replace":
            problems.append(f"{where}: the policy does not replace {category}")
    elif category is not None:
        problems.append(f"{where}: only a pseudonym column declares a category")
    if rule == "band":
        if rules.get("identifying_number") != "band":
            problems.append(f"{where}: the policy does not band identifying numbers")
        bands = _bands(raw.get("bands"), where, problems)
    if rule == "map":
        raw_map = raw.get("map")
        ok = isinstance(raw_map, dict) and raw_map and all(
            isinstance(v, str) and v.strip() and "\n" not in v for v in raw_map.values())
        if not ok:
            problems.append(f"{where}: a map column declares a non-empty map of one-line values")
        else:
            assert isinstance(raw_map, dict)
            mapping = {" ".join(str(k).split()): v for k, v in raw_map.items()}
    row_key = raw.get("row_key", False)
    if not isinstance(row_key, bool):
        problems.append(f"{where}: row_key is true or false")
        row_key = False
    if problems or not isinstance(index, int):
        return None
    return Column(index=index, header=raw["header"], field=raw["field"], rule=rule,
                  category=category, row_key=row_key, bands=bands, mapping=mapping)


def validate_spec(record: Any, policy: LoadedPolicy) -> TableSpec:
    """The specification *record* validated against *policy*. Refuses with every problem."""
    problems: list[str] = []
    if not isinstance(record, dict):
        raise TableRefused("the table specification is not a JSON object")
    if record.get("schema") != SPEC_SCHEMA or record.get("record_type") != SPEC_RECORD_TYPE:
        problems.append(f"the table specification is not an {SPEC_SCHEMA} record")
    table = record.get("table")
    if not isinstance(table, dict):
        table = {}
        problems.append("table is an object naming page, index and header_rows")
    for key, low in (("page", 1), ("index", 0), ("header_rows", 1)):
        if not (_is_int(table.get(key)) and table[key] >= low):
            problems.append(f"table.{key} is a whole number from {low}")
    raw_columns = record.get("columns")
    if not isinstance(raw_columns, list) or not raw_columns:
        raise TableRefused("; ".join(problems + ["columns is a non-empty list"]))
    columns: list[Column] = []
    for n, raw in enumerate(raw_columns):
        own: list[str] = []
        column = _column(raw, n, policy, own)
        problems += own
        if column is not None:
            columns.append(column)
    columns.sort(key=lambda c: c.index)
    if not problems and [c.index for c in columns] != list(range(len(columns))):
        problems.append("the columns are declared once each, indexed from 0 without a gap")
    keys = [c for c in columns if c.row_key]
    if not problems and (len(keys) != 1 or keys[0].rule != "pseudonym"
                         or keys[0].category != "person_name"):
        problems.append("exactly one column is the row key, and it is a person_name pseudonym "
                        "column: the row's supervisor")
    if problems:
        raise TableRefused("the table specification is refused: " + "; ".join(problems))
    return TableSpec(sha256=record_sha256(record), page=table["page"], index=table["index"],
                     header_rows=table["header_rows"], columns=tuple(columns))


def load_spec(path: Path, policy: LoadedPolicy, expected_sha256: str) -> TableSpec:
    """The specification at *path*, refused unless it hashes to *expected_sha256*."""
    path = intake.require_private(path, "the table specification")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TableRefused(f"the table specification cannot be read: {exc}") from exc
    spec = validate_spec(record, policy)
    if spec.sha256 != expected_sha256:
        raise TableRefused(
            f"the table specification hashes to {spec.sha256}, not the declared "
            f"{expected_sha256}: this is not the pinned table specification."
        )
    return spec


# --------------------------------------------------------------------------- #
# Pseudonym codes
# --------------------------------------------------------------------------- #


def pseudonym_code(entry: Entry) -> str:
    """The one code every replacement of *entry* carries, such as ``S03``."""
    codes = set()
    for replacement in entry.replacements:
        if not replacement:
            continue
        found = _CODE.findall(replacement)
        if len(found) != 1:
            raise TableRefused(
                f"entry {entry.id}: replacement {entry.replacements.index(replacement)} carries "
                f"{len(found)} codes; each carries exactly one"
            )
        codes.add(found[0])
    if len(codes) != 1:
        raise TableRefused(
            f"entry {entry.id}: its replacements carry {len(codes)} different codes; one entity "
            f"carries one pseudonym"
        )
    return codes.pop()


def person_codes(dictionary: EntityDictionary) -> dict[str, str]:
    """Each person entry's code, refused if one is inconsistent or two entries share one."""
    codes: dict[str, str] = {}
    owner: dict[str, str] = {}
    for entry in dictionary.entries:
        if entry.category != "person_name":
            continue
        code = pseudonym_code(entry)
        if code in owner:
            raise TableRefused(
                f"{code} is the pseudonym of both {owner[code]} and {entry.id}; one code stands "
                f"for one person"
            )
        owner[code] = entry.id
        codes[entry.id] = code
    return codes


# --------------------------------------------------------------------------- #
# Reading the table
# --------------------------------------------------------------------------- #

_Rect = tuple[float, float, float, float]


@dataclass(frozen=True)
class _Cell:
    row: int  # data row, from 1
    col: int
    bbox: _Rect
    text: str


def _norm(text: Optional[str]) -> str:
    return " ".join((text or "").split())


def _measure(doc: Any, spec: TableSpec) -> tuple[_Rect, int, int, list[list[Optional[_Rect]]],
                                                  list[list[str]]]:
    page = doc[spec.page - 1] if 1 <= spec.page <= doc.page_count else None
    tables = page.find_tables(strategy=TABLE_STRATEGY).tables if page is not None else []
    if spec.index >= len(tables):
        raise TableRefused(f"page {spec.page} holds no table at index {spec.index} under the "
                           f"{TABLE_STRATEGY} strategy")
    table = tables[spec.index]
    boxes = [[tuple(c) if c else None for c in row.cells] for row in table.rows]
    texts = [[_norm(t) for t in row] for row in table.extract()]
    return tuple(table.bbox), table.row_count, table.col_count, boxes, texts


def _cells(doc: Any, spec: TableSpec) -> tuple[_Rect, list[_Cell]]:
    bbox, rows, cols, boxes, texts = _measure(doc, spec)
    if cols != len(spec.columns):
        missing = ", ".join(str(n) for n in range(len(spec.columns), cols))
        raise TableRefused(
            f"the table has {cols} columns and the specification declares {len(spec.columns)}"
            + (f"; column {missing} is not declared" if missing else "")
        )
    if rows <= spec.header_rows:
        raise TableRefused("the table has no data row below its header rows")
    for column in spec.columns:
        if texts[spec.header_rows - 1][column.index] != _norm(column.header):
            raise TableRefused(f"column {column.index}: the table's header is not the one the "
                               f"specification declares")
    cells: list[_Cell] = []
    for r in range(spec.header_rows, rows):
        for c in range(cols):
            box = boxes[r][c]
            if box is None:
                raise TableRefused(f"row {r - spec.header_rows + 1}, column {c} is a merged "
                                   f"cell; a synthetic row keeps one cell per column")
            cells.append(_Cell(r - spec.header_rows + 1, c, box, texts[r][c]))
    return bbox, cells


def _chars(page: Any, box: _Rect) -> list[tuple[_Rect, float]]:
    out = []
    for block in page.get_text("rawdict")["blocks"]:
        for line in block.get("lines", ()):
            for span in line["spans"]:
                for char in span["chars"]:
                    x0, y0, x1, y1 = char["bbox"]
                    if char["c"].isspace():
                        continue
                    if box[0] <= (x0 + x1) / 2 <= box[2] and box[1] <= (y0 + y1) / 2 <= box[3]:
                        out.append(((x0, y0, x1, y1), round(float(span["size"]), 2)))
    return out


def _starts_in(rect: list[float], box: _Rect) -> bool:
    """A2 runs a line-end box to the margin, so its left edge locates it, not its centre."""
    middle = (rect[1] + rect[3]) / 2
    return box[0] <= rect[0] + 0.5 <= box[2] and box[1] <= middle <= box[3]


# --------------------------------------------------------------------------- #
# Synthesis
# --------------------------------------------------------------------------- #


def _band_forms(low: int, high: Optional[int]) -> tuple[str, str]:
    if high is None:
        return f"{low} or more", f"{low}+"
    return f"{low} to {high}", f"{low}-{high}"


def _where(cell: _Cell) -> str:
    return f"row {cell.row}, column {cell.col}"


def _edit_box(page: Any, cell: _Cell) -> tuple[_Rect, float]:
    chars = _chars(page, cell.bbox)
    sizes = {size for _, size in chars}
    if not chars:
        raise TableRefused(f"{_where(cell)}: the cell holds no text to synthesise")
    if len(sizes) > 1:
        raise TableRefused(f"{_where(cell)}: the cell holds text in more than one point size")
    rect = (min(b[0] for b, _ in chars), min(b[1] for b, _ in chars),
            cell.bbox[2] - CELL_INSET, max(b[3] for b, _ in chars))
    return rect, sizes.pop()


def _fits(text: str, size: float, rect: _Rect) -> bool:
    import pymupdf

    used = pymupdf.get_text_length(text, fontname=intake.REPLACEMENT_FONT, fontsize=size)
    return used <= rect[2] - rect[0] + 1e-6


def _synthetic(page: Any, cell: _Cell, column: Column) -> tuple[str, intake.SpanEdit, dict]:
    rect, size = _edit_box(page, cell)
    detail: dict[str, Any] = {}
    if column.rule == "band":
        if not _NUMBER.match(cell.text):
            raise TableRefused(f"{_where(cell)}: the cell holds no whole number to band")
        value = int(cell.text.replace(",", ""))
        held = [n for n, (low, high) in enumerate(column.bands)
                if low <= value and (high is None or value <= high)]
        if not held:
            raise TableRefused(f"{_where(cell)}: no band of the column holds the cell's value")
        low, high = column.bands[held[0]]
        candidates: tuple[str, ...] = _band_forms(low, high)
        detail = {"band": [low, high]}
    else:
        if cell.text not in column.mapping:
            raise TableRefused(f"{_where(cell)}: the cell's value is not in the column's map")
        candidates = (column.mapping[cell.text],)
    for text in candidates:
        if _fits(text, size, rect):
            return text, intake.SpanEdit(page=page.number + 1, rect=rect, replacement=text), detail
    raise TableRefused(f"{_where(cell)}: the synthetic value is too wide for the cell at "
                       f"{size} pt; declare a shorter one")


def _redaction_log(path: Path) -> dict[str, Any]:
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise TableRefused(f"the redaction log cannot be read: {exc}") from exc
    if not isinstance(record, dict) or record.get("schema") != REDACTION_SCHEMA:
        raise TableRefused(f"the redaction log is not an {REDACTION_SCHEMA} record")
    edits = (record.get("page_text") or {}).get("edits") if isinstance(
        record.get("page_text"), dict) else None
    well_formed = (
        isinstance(record.get("input"), dict) and isinstance(record.get("output"), dict)
        and isinstance(record["output"].get("sha256"), str) and isinstance(edits, list)
        and all(isinstance(e, dict) and {"page", "rect", "category", "entry_id", "removed"} <= e.keys()
                for e in edits)
    )
    if not well_formed:
        raise TableRefused("the redaction log lacks its input, output or page-text edits")
    return record


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def synthesise(
    *,
    derivative: Path,
    redaction_log: Path,
    intake_record: Path,
    policy: LoadedPolicy,
    policy_sha256: str,
    dictionary: Path,
    dictionary_sha256: str,
    spec: Path,
    spec_sha256: str,
    out_dir: Path,
) -> SynthesisResult:
    """Synthesise the table *spec* names in the A2 *derivative*; write it, its log and row map.

    *derivative* must be the file *redaction_log* records as A2's output, and
    the policy, the dictionary and the intake record must be the ones A2 used.
    Every refusal runs before the first write. A re-run that would write the
    same bytes is a no-op; one that would write different bytes is refused.
    """
    import pymupdf

    derivative = intake.require_private(derivative, "the A2 derivative")
    redaction_log = intake.require_private(redaction_log, "the redaction log")
    intake_record = intake.require_private(intake_record, "the intake record")
    dictionary = intake.require_private(dictionary, "the entity dictionary")
    spec_path = intake.require_private(spec, "the table specification")
    out_dir = intake.require_private(out_dir, "the synthesis directory")
    require_hash(policy, policy_sha256)

    a2 = _redaction_log(redaction_log)
    if a2.get("policy_sha256") != policy.sha256:
        raise TableRefused("the policy is not the one A2 applied")
    if a2.get("dictionary_sha256") != dictionary_sha256:
        raise TableRefused("the entity dictionary is not the one A2 applied")
    if a2["input"].get("intake_record_sha256") != _sha(intake_record.read_bytes()):
        raise TableRefused("the intake record is not the one A2 read")
    entities = load_dictionary(dictionary, policy)
    if entities.sha256 != dictionary_sha256:
        raise TableRefused(
            f"the entity dictionary hashes to {entities.sha256}, not the declared "
            f"{dictionary_sha256}: this is not the pinned dictionary."
        )
    table_spec = load_spec(spec_path, policy, spec_sha256)
    intake.require_pdf_route(intake_record)
    derivative_sha = intake.pin(derivative, str(a2["output"]["sha256"]), "the A2 derivative")
    codes = person_codes(entities)
    by_id = {e.id: e for e in entities.entries}
    a2_edits = [e for e in a2["page_text"]["edits"] if not e["removed"] and e.get("entry_id")]

    doc = pymupdf.open(derivative)
    try:
        frame, cells = _cells(doc, table_spec)
        page = doc[table_spec.page - 1]
        span_edits: list[intake.SpanEdit] = []
        rows: dict[int, dict[str, Any]] = {}
        logged: list[dict[str, Any]] = []
        expected: dict[tuple[int, int], str] = {}
        for cell in cells:
            column = table_spec.columns[cell.col]
            row = rows.setdefault(cell.row, {"row": cell.row, "cells": []})
            entry: dict[str, Any] = {"col": cell.col, "field": column.field, "rule": column.rule}
            expected[(cell.row, cell.col)] = cell.text
            if column.rule == "keep":
                entry.update(source=cell.text, synthetic=cell.text)
            elif column.rule == "pseudonym":
                ids = sorted({e["entry_id"] for e in a2_edits
                              if e["page"] == table_spec.page and e["category"] == column.category
                              and _starts_in(e["rect"], cell.bbox)})
                if len(ids) != 1:
                    raise TableRefused(
                        f"{_where(cell)}: {len(ids)} A2 replacements of {column.category} lie in "
                        f"the cell, and a pseudonym cell holds exactly one. Add the entity to the "
                        f"dictionary and run A2 again"
                    )
                code = codes[ids[0]] if column.category == "person_name" else \
                    pseudonym_code(by_id[ids[0]])
                if code not in _CODE.findall(cell.text):
                    raise TableRefused(f"{_where(cell)}: the cell does not read the pseudonym "
                                       f"of entry {ids[0]}")
                entry.update(category=column.category, entry_id=ids[0], pseudonym=code)
                if column.row_key:
                    elsewhere = [e for e in a2_edits if e["entry_id"] == ids[0]
                                 and not (e["page"] == table_spec.page
                                          and _starts_in(e["rect"], frame))]
                    row["supervisor"] = {
                        "entry_id": ids[0], "pseudonym": code,
                        "occurrences_outside_table": len(elsewhere),
                        "pages": sorted({e["page"] for e in elsewhere}),
                    }
            else:
                text, span_edit, detail = _synthetic(page, cell, column)
                span_edits.append(span_edit)
                expected[(cell.row, cell.col)] = text
                entry.update(source=cell.text, synthetic=text, **detail)
                logged.append({"row": cell.row, "col": cell.col, "rule": column.rule})
            row["cells"].append(entry)
    finally:
        doc.close()

    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out_dir) as scratch:
        staged = Path(scratch) / DERIVATIVE_FILE
        try:
            harness_log = intake.apply_stage_edits(derivative, intake_record, derivative_sha,
                                                   span_edits, staged)
        except intake.ReplacementOverflow as exc:
            raise TableRefused(f"a synthetic value did not fit its cell: {exc}") from exc
        data = staged.read_bytes()

    _self_check(data, table_spec, frame, cells, expected)

    inputs = {
        "derivative_sha256": derivative_sha,
        "redaction_log_sha256": _sha(redaction_log.read_bytes()),
        "intake_record_sha256": _sha(intake_record.read_bytes()),
        "policy_sha256": policy.sha256,
        "dictionary_sha256": entities.sha256,
        "table_spec_sha256": table_spec.sha256,
    }
    output = {"file": DERIVATIVE_FILE, "sha256": _sha(data), "bytes": len(data)}
    counts: dict[str, int] = {rule: 0 for rule in RULES}
    for cell in cells:
        counts[table_spec.columns[cell.col].rule] += 1
    log = {
        "schema": SCHEMA,
        "record_type": RECORD_TYPE,
        "stage": "A4",
        "purpose": (
            "The log of the Table 1.4.1 synthesis: which cells were banded or mapped, where, "
            "and what was checked. The row map holds the values."
        ),
        "input": inputs,
        "output": output,
        "table": {"page": table_spec.page, "index": table_spec.index,
                  "strategy": TABLE_STRATEGY, "header_rows": table_spec.header_rows,
                  "data_rows": len(rows), "columns": len(table_spec.columns),
                  "frame": [round(v, 3) for v in frame]},
        "cells_by_rule": counts,
        "supervisors": len(rows),
        "edits": [{**entry, **h} for entry, h in zip(logged, harness_log)],
        "checks": [
            "the output table has the source table's frame, row count, column count and "
            "cell boxes",
            "every cell reads the value the synthesis intended",
            "every band holds the source value it replaces",
            "every pseudonym cell reads the code of the one entity A2 replaced there, and one "
            "code stands for one person across the dictionary",
        ],
        "not_in_scope": [
            "identifying numbers outside the table, which are A3's",
            "the A3 rewrite plan, which this stage does not apply",
            "the leak scan of the derivative, which is A5's",
        ],
        "replay": {
            "rule": "Same inputs, same hashes and same PyMuPDF build give byte-equal output.",
            "environment": {"pymupdf": pymupdf.VersionBind},
        },
        "privacy": {
            "declared_status": "Confirmed",
            "claim": "This log records locations, rules and counts. It quotes no text, source "
                     "or synthetic, and names no entity.",
            "basis": "The log is built from cell positions, rule names and the edit harness's "
                     "geometry only; tests/runner/test_anonymisation_table.py asserts that no "
                     "table text appears in it.",
        },
    }
    row_map = {
        "schema": ROW_MAP_SCHEMA,
        "record_type": ROW_MAP_RECORD_TYPE,
        "stage": "A4",
        "purpose": (
            "The real-to-synthetic correspondence of Table 1.4.1, row by row. Part of the "
            "mapping table: private, D4 forever."
        ),
        "input": inputs,
        "output": output,
        "table": {"page": table_spec.page, "index": table_spec.index},
        "rows": [rows[n] for n in sorted(rows)],
    }
    files = {DERIVATIVE_FILE: data, LOG_FILE: canonical_json_bytes(log),
             ROW_MAP_FILE: canonical_json_bytes(row_map)}
    for name, content in files.items():
        existing = out_dir / name
        if existing.exists() and existing.read_bytes() != content:
            raise TableRefused(
                f"{out_dir.name} already holds a synthesis that differs from this one ({name}). "
                f"A written derivative is never overwritten; synthesise into a new directory."
            )

    def write_derivative(tmp: str) -> None:
        Path(tmp).write_bytes(data)

    if not (out_dir / DERIVATIVE_FILE).exists():
        atomic_write_via(out_dir / DERIVATIVE_FILE, write_derivative)
    for name in (LOG_FILE, ROW_MAP_FILE):
        if not (out_dir / name).exists():
            atomic_write_text(files[name].decode("utf-8"), out_dir / name)
    return SynthesisResult(derivative=out_dir / DERIVATIVE_FILE, log=out_dir / LOG_FILE,
                           row_map=out_dir / ROW_MAP_FILE, derivative_sha256=_sha(data))


def _self_check(data: bytes, spec: TableSpec, frame: _Rect, cells: list[_Cell],
                expected: Mapping[tuple[int, int], str]) -> None:
    import pymupdf

    doc = pymupdf.open(stream=data, filetype="pdf")
    try:
        after_frame, after = _cells(doc, spec)
    finally:
        doc.close()
    same = (len(after) == len(cells) and all(a.bbox == b.bbox for a, b in zip(after, cells))
            and tuple(round(v, 3) for v in after_frame) == tuple(round(v, 3) for v in frame))
    if not same:
        raise TableRefused("the synthesised table's layout differs from the source table's. "
                           "Nothing was written.")
    wrong = [_where(c) for c in after if c.text != expected[(c.row, c.col)]]
    if wrong:
        raise TableRefused(f"{', '.join(wrong)}: the synthesised cell does not read the "
                           f"intended value. Nothing was written.")
