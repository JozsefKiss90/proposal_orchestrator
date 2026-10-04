"""
Criterion appendix mapping — the rows a criterion receives beyond its own section.

At the criterion-grading stage a criterion is scored over its complete section
verbatim.  Some aspects rest on rows another criterion's section owns (a
deliverables table under Implementation that an Impact aspect cites), and a
single-section pack cannot express that.  The mapping names those rows as a
**declared appendix**: one entry per ``(criterion, table, candidate sub-section)``,
each with the status rule of CLAUDE.md §12.2 and its sources.

The mapping is **versioned with the rubric set and never assembled at scoring
time**: the rubric-set file pins the mapping file's sha256, the mapping carries
the rubric set's id and version, and a byte that drifts from the pin refuses to
load.  A silent change to the mapping would change scores; this is what makes
it loud.

Resolution granularity is the **candidate sub-section**.  The ``rows`` field is
the authored description an evaluator reads; the import renders tables one
pipe-delimited row per paragraph, but a table the source copy flattened to
prose has no row boundaries left, so a finer locator would fail on exactly the
rows that matter.  The criterion input therefore appends the whole declared
sub-section, which carries the declared rows and never less than them.

Constitutional authority:
    Subordinate to CLAUDE.md.  Out-of-band QA configuration; read-only.  Never
    a runtime gate.  See ``harness/HARNESS.md``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

__all__ = [
    "AppendixMappingError",
    "AppendixRow",
    "CriterionAppendixMapping",
    "load_criterion_appendix_mapping",
]


class AppendixMappingError(Exception):
    """The mapping file is missing, malformed, or has drifted from its pin (fail-closed)."""


@dataclass(frozen=True)
class AppendixRow:
    """One declared appendix entry: which sub-section's rows a criterion receives."""

    criterion_id: str
    aspect_id: str
    table: str
    candidate_sub_section: str
    rows: str
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion_id": self.criterion_id,
            "aspect_id": self.aspect_id,
            "table": self.table,
            "candidate_sub_section": self.candidate_sub_section,
            "rows": self.rows,
            "status": self.status,
        }


@dataclass(frozen=True)
class CriterionAppendixMapping:
    """The loaded, pin-checked mapping."""

    mapping_id: str
    rubric_set_id: str
    rubric_set_version: str
    sha256: str
    path: str
    rows: tuple[AppendixRow, ...]

    @property
    def version(self) -> dict[str, str]:
        """What a score records as the mapping version: identity, rubric-set pin, bytes."""
        return {
            "mapping_id": self.mapping_id,
            "rubric_set_id": self.rubric_set_id,
            "rubric_set_version": self.rubric_set_version,
            "sha256": self.sha256,
        }

    def rows_for(self, criterion_id: str) -> tuple[AppendixRow, ...]:
        return tuple(r for r in self.rows if r.criterion_id == criterion_id)


def _require_str(obj: Mapping[str, Any], key: str, where: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AppendixMappingError(f"{where}: {key!r} must be a non-empty string.")
    return value


def load_criterion_appendix_mapping(
    path: Path | str,
    *,
    expected_sha256: str | None,
    rubric_set_id: str,
    rubric_set_version: str,
) -> CriterionAppendixMapping:
    """Load the mapping at *path* and check it against the rubric set's pin.

    Refuses: a missing or malformed file; a file whose sha256 differs from
    *expected_sha256* (``None`` means the rubric set carries no pin, which is
    itself a refusal — an unpinned mapping could change scores silently); a
    mapping authored for another rubric set or version; a row without its
    required fields.
    """
    p = Path(path)
    if not p.is_file():
        raise AppendixMappingError(f"criterion appendix mapping not found: {p}")
    raw = p.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if not expected_sha256:
        raise AppendixMappingError(
            f"the rubric set carries no sha256 pin for the criterion appendix mapping "
            f"{p}; an unpinned mapping could change scores silently, so it is refused."
        )
    if digest != expected_sha256:
        raise AppendixMappingError(
            f"criterion appendix mapping {p} hashes to sha256 {digest}, but the rubric "
            f"set pins {expected_sha256} — the mapping changed without a rubric-set "
            "version change."
        )
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AppendixMappingError(f"criterion appendix mapping {p} is not valid JSON: {exc}") from exc
    if not isinstance(data, Mapping):
        raise AppendixMappingError(f"criterion appendix mapping {p} is not a JSON object.")
    where = f"criterion appendix mapping {p}"
    mapping_id = _require_str(data, "mapping_id", where)
    set_id = _require_str(data, "rubric_set_id", where)
    set_version = _require_str(data, "rubric_set_version", where)
    if (set_id, set_version) != (rubric_set_id, rubric_set_version):
        raise AppendixMappingError(
            f"{where} was authored for rubric set {set_id!r} v{set_version!r}, but the "
            f"loaded rubric set is {rubric_set_id!r} v{rubric_set_version!r}."
        )
    rows_raw = data.get("rows")
    if not isinstance(rows_raw, list):
        raise AppendixMappingError(f"{where} has no rows array.")
    rows: list[AppendixRow] = []
    for i, row in enumerate(rows_raw):
        if not isinstance(row, Mapping):
            raise AppendixMappingError(f"{where}: rows[{i}] is not an object.")
        here = f"{where} rows[{i}]"
        rows.append(
            AppendixRow(
                criterion_id=_require_str(row, "criterion_id", here),
                aspect_id=str(row.get("aspect_id", "")),
                table=_require_str(row, "table", here),
                candidate_sub_section=_require_str(row, "candidate_sub_section", here),
                rows=_require_str(row, "rows", here),
                status=_require_str(row, "status", here),
            )
        )
    return CriterionAppendixMapping(
        mapping_id=mapping_id,
        rubric_set_id=set_id,
        rubric_set_version=set_version,
        sha256=digest,
        path=p.as_posix(),
        rows=tuple(rows),
    )
