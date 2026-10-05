"""
Integrity audit — internal consistency over the parsed table rows (spec PE-07).

What this is
------------
A Claude-free, deterministic audit of one candidate. It reads the same
materialised section artifacts the blind lane reads, parses the rendered
pipe-delimited table rows (spec decision 8: the rendering *is* the structure)
and the label-value work-package blocks, and runs five consistency checks:

1. **Work-package table against work-package prose** — lead, start and end
   month, DCs involved; every field present, every task numbered under its
   own package, and the DCs a package declares against the packages each DC
   project in section 1.1 declares.
2. **Each deliverable's work package exists, and its month fits that
   package's window.**
3. **Each milestone's month against the months of the deliverables it depends
   on.** A dependency is a deliverable the milestone row names. A milestone
   naming none is reported as *undeclared*, with the related packages'
   deliverable months beside it as context, never as a failure.
4. **DC table against the individual DC research projects described in
   1.1** — the DC set, each DC's packages against the package windows, and
   the recruiting participant against the project's host line, which the
   sanitisation made *not comparable* and which is reported as such.
5. **Risk table against the mitigations named in prose, and whether any
   threshold is stated.**

Every finding is a fact about two places in the proposal that do not agree,
or one place that says less than the check needs. No finding is a score, a
grade or a pass: the report carries counts of findings by kind and nothing
that ranks the proposal. A reader who wants a quality judgment reads the blind
baseline, not this.

The grounding axis
------------------
Per spec decision 15 the audit enumerates the import's claim ledger
(``validation_status.claim_statuses`` of each section artifact, the same file
the pack builder reads) and reports **every claim Unresolved** with the reason
:data:`GROUNDING_REASON`. A claim extracted from the proposal is trivially
entailed by the proposal, so no judge runs here and none could say more. The
axis is wired to the E2 vocabulary (:data:`~harness.status_faithfulness.SEVERITY_UNRESOLVED`)
so a later stage with sources can replace the rows without changing the
shape. An empty ledger makes the axis vacuous and is flagged, never silently
reported as zero findings. A claim whose ledger entry declares a status other
than ``unresolved`` contradicts the import contract (spec PE-03) and is flagged
with its declaration visible; it is still reported Unresolved, because a
declaration is not evidence. The ledger's ``source_ref`` is the claim's own
verified span into the proposal's page sources: a location, carried as
``assertion_location``, never a source.

The baseline
------------
The audit writes nothing under the graph root, so the snapshot id the frozen
blind baseline stamped cannot move. When a baseline directory is given the
audit loads the freeze through :func:`~harness.blind_baseline.load_frozen_baseline`
and compares its candidate hash and snapshot id with its own. Equal ids: the
audit is *bound* to the baseline. A moved snapshot id over the same candidate:
the report says the baseline was *re-derived*. A different candidate hash: the
audit does not describe the frozen candidate and says so. No directory: the
report says no baseline was consulted. Nothing here refuses to run; the
statement is the acceptance.

Constitutional authority:
    Subordinate to CLAUDE.md. Out-of-band QA; reads candidate artifacts and
    dev-graph records read-only and writes only harness-owned report files.
    Never a runtime gate. See ``harness/HARNESS.md``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

from runner.atomic_write import atomic_write_json
from runner.external_proposal import ExtractionError, is_row, parse_row
from harness.blind_assessment import (
    EVIDENCE_SOURCE_DEV_GRAPH,
    EVIDENCE_SOURCE_DIRECTORY,
    BlindAssessmentError,
    BlindEvidence,
    Candidate,
    candidate_hash,
    next_report_path,
)
from harness.blind_baseline import BlindBaselineError, FrozenBaseline, load_frozen_baseline
from harness.evidence_pack import split_paragraphs
from harness.status_faithfulness import (
    SEVERITY_UNRESOLVED,
    SectionClaim,
    StatusFaithfulnessError,
    load_section_claims,
)

__all__ = [
    "AUDIT_RECORD_TYPE",
    "AUDIT_METRIC",
    "AUDIT_SCHEMA_VERSION",
    "GROUNDING_REASON",
    "GROUNDING_STATUS",
    "CHECKS",
    "FINDING_KINDS",
    "BASELINE_STATUSES",
    "IntegrityAuditError",
    "Where",
    "Finding",
    "CheckResult",
    "ParsedTables",
    "parse_candidate",
    "run_checks",
    "enumerate_grounding",
    "bind_baseline",
    "IntegrityAuditReport",
    "run_audit",
    "write_audit",
    "load_audit",
    "render_audit",
]

AUDIT_RECORD_TYPE: str = "integrity_audit_report"
AUDIT_METRIC: str = "integrity_audit"
AUDIT_SCHEMA_VERSION: str = "1.0.0"

#: Spec decision 15, verbatim: the one reason every ledger claim carries.
GROUNDING_REASON: str = "supporting sources removed by sanitisation"
#: CLAUDE.md §12.2 status the grounding axis reports for every claim.
GROUNDING_STATUS: str = "Unresolved"
#: The ledger status the import contract fixes (spec PE-03); anything else is flagged.
_LEDGER_EXPECTED_STATUS: str = "unresolved"

#: The five checks, in the order the spec lists them and the report runs them.
CHECKS: tuple[tuple[str, str], ...] = (
    ("wp_table_vs_prose", "Work-package table against work-package prose"),
    ("deliverable_wp_window", "Each deliverable's work package exists and its month fits the window"),
    ("milestone_dependencies", "Each milestone's month against the deliverables it depends on"),
    ("dc_table_vs_projects", "DC table against the individual DC research projects in 1.1"),
    ("risk_table_vs_prose", "Risk table against the mitigations named in prose; thresholds"),
)

#: What a finding can be. None is a score.
KIND_INCONSISTENCY: str = "inconsistency"
KIND_MISSING_FIELD: str = "missing_field"
KIND_UNPARSED: str = "unparsed_cell"
KIND_UNDECLARED: str = "undeclared_dependency"
KIND_OUT_OF_WINDOW: str = "out_of_window"
KIND_NOT_COMPARABLE: str = "not_comparable"
KIND_UNLINKED_PROSE: str = "unlinked_prose"
FINDING_KINDS: tuple[str, ...] = (
    KIND_INCONSISTENCY,
    KIND_MISSING_FIELD,
    KIND_UNPARSED,
    KIND_UNDECLARED,
    KIND_OUT_OF_WINDOW,
    KIND_NOT_COMPARABLE,
    KIND_UNLINKED_PROSE,
)

BASELINE_NONE: str = "no_baseline"
BASELINE_BOUND: str = "bound"
BASELINE_REDERIVED: str = "re-derived"
BASELINE_OTHER_CANDIDATE: str = "candidate_differs"
BASELINE_UNKNOWN_SNAPSHOT: str = "snapshot_unknown"
BASELINE_STATUSES: tuple[str, ...] = (
    BASELINE_NONE,
    BASELINE_BOUND,
    BASELINE_REDERIVED,
    BASELINE_OTHER_CANDIDATE,
    BASELINE_UNKNOWN_SNAPSHOT,
)

_REPORT_PREFIX: str = "integrity"

_ADVISORY_NOTE: str = (
    "Advisory to a human, never run-blocking. Every finding names two places in "
    "the proposal that do not agree, or one that says less than the check needs; "
    "no finding is a proposal-quality score and the counts rank nothing. The "
    "grounding axis reports every claim Unresolved for one declared reason and "
    "runs no judge (spec decision 15)."
)

Clock = Callable[[], str]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class IntegrityAuditError(BlindAssessmentError):
    """The audit was invoked outside its contract (fail-closed)."""


# --------------------------------------------------------------------------- #
# Locations and findings
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Where:
    """One paragraph of one sub-section of one section artifact."""

    section_id: str
    sub_section_id: str
    paragraph_index: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "sub_section_id": self.sub_section_id,
            "paragraph_index": self.paragraph_index,
        }


@dataclass(frozen=True)
class Finding:
    """One fact the check could not reconcile. Never a score."""

    check: str
    kind: str
    subject: str
    detail: str
    where: tuple[Where, ...] = ()
    evidence: tuple[str, ...] = ()
    context: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.kind not in FINDING_KINDS:
            raise ValueError(f"unknown finding kind {self.kind!r}; one of {FINDING_KINDS}.")

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "check": self.check,
            "kind": self.kind,
            "subject": self.subject,
            "detail": self.detail,
            "where": [w.to_dict() for w in self.where],
            "evidence": list(self.evidence),
        }
        if self.context is not None:
            d["context"] = dict(self.context)
        return d


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    title: str
    compared: int
    findings: tuple[Finding, ...]
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        by_kind = {k: sum(1 for f in self.findings if f.kind == k) for k in FINDING_KINDS}
        return {
            "check_id": self.check_id,
            "title": self.title,
            "compared": self.compared,
            "findings_total": len(self.findings),
            "findings_by_kind": {k: v for k, v in by_kind.items() if v},
            "findings": [f.to_dict() for f in self.findings],
            "notes": list(self.notes),
        }


# --------------------------------------------------------------------------- #
# Parsing: rows, work-package blocks, DC projects, risk prose
# --------------------------------------------------------------------------- #


def _norm(cell: str) -> str:
    """Whitespace removed, lowercased: ``"Numbe r"`` and ``"Number"`` agree."""
    return re.sub(r"\s+", "", cell).lower()


_DASH = r"[–—\-]"
_RE_MONTH = re.compile(r"\bM\s?0*(\d+)\b")
_RE_RANGE = re.compile(rf"(\d+)\s*{_DASH}\s*(\d+)")
_RE_INT = re.compile(r"\b(\d+)\b")
_RE_DELIV_ID = re.compile(r"D(\d+)\.(\d+)")
_RE_WP_BLOCK = re.compile(r"^WP\s*Number:?\s*(\d+)\s*$", re.IGNORECASE)
_RE_WP_TITLE = re.compile(
    rf"^WP\s*title:?\s*(?P<title>.*?)\s*Start\s*month\s*{_DASH}\s*End\s*month:?\s*"
    rf"M\s?0*(?P<start>\d+)\s*{_DASH}\s*M\s?0*(?P<end>\d+)\s*$",
    re.IGNORECASE,
)
_RE_WP_TITLE_ONLY = re.compile(r"^WP\s*title:?\s*(?P<title>.*)$", re.IGNORECASE)
_RE_LEAD = re.compile(r"^Lead\s+(?:participant|beneficiary):?\s*(?P<value>.*)$", re.IGNORECASE)
_RE_PARTICIPANTS = re.compile(r"^Participants:?\s*(?P<value>.*)$", re.IGNORECASE)
_RE_DCS = re.compile(r"^DCs?\s+involved:?\s*(?P<value>.*)$", re.IGNORECASE)
_RE_TASK = re.compile(r"^Task\s+(\d+)\.(\d+)\b", re.IGNORECASE)
_RE_TABLE_CAPTION = re.compile(r"^Table\s+\d", re.IGNORECASE)
_RE_DC_HEADING = re.compile(rf"^DC\s?(\d+)\s*{_DASH}\s*(?P<title>.+)$")
_RE_HOST = re.compile(r"^Host:?\s*(?P<value>.*)$", re.IGNORECASE)
_RE_HOST_WPS = re.compile(r"\(([^)]*\bWP\s?\d[^)]*)\)")
_RE_CONTRIBUTION = re.compile(r"^Contribution to the Network", re.IGNORECASE)
_RE_SECONDMENTS = re.compile(r"^Key Secondments", re.IGNORECASE)
_RE_BULLET = re.compile(r"^[•‣◦⁃\-\*]\s*")
_RE_MITIGATION_PROSE = re.compile(
    r"\brisks?\s+(?:will\s+be\s+|are\s+|is\s+|can\s+be\s+|would\s+be\s+)?mitigated\b|"
    r"\bmitigat\w*\s+(?:of\s+|the\s+|this\s+|these\s+|those\s+|such\s+|any\s+)?risks?\b|"
    r"\bcontingenc\w*\b|\breserve pool\b|\brisk[- ]management\s+(?:procedure|process|plan|measure)s?\b|"
    r"\brisk register\b|\bfallback\b|\bback-?up plan\b",
    re.IGNORECASE,
)
_RE_THRESHOLD = re.compile(
    r"\bthreshold\b|\d+\s*%|\bper cent\b|\bat least\s+\d|\bmore than\s+\d|\bno later than\b|"
    r"\bwithin\s+\d+\s*(?:months?|weeks?|days?)\b|\btrigger\w*\b|\bexceed\w*\s+\d",
    re.IGNORECASE,
)
_STOPWORDS = frozenset(
    "that this with from will into than then they them their there these those which while "
    "where when what have been being were also such each other more most some same both "
    "through between within without across under over after before during until against "
    "early later stage stages work package packages project risk risks measures measure "
    "mitigation proposed involved ensure ensuring support supporting strong".split()
)


def _tokens(text: str) -> frozenset[str]:
    return frozenset(
        t for t in re.findall(r"[a-z][a-z\-]{3,}", text.lower()) if t not in _STOPWORDS
    )


def _months(text: str) -> tuple[tuple[int, ...], str | None]:
    """``"M12, M24, M36"`` → ``((12, 24, 36), None)``; nothing parsed → ``((), text)``."""
    found = tuple(int(m) for m in _RE_MONTH.findall(text))
    if not found:
        return (), text.strip()
    return found, None


def _refs(text: str, *, prefix: str = "") -> tuple[tuple[int, ...] | None, str | None]:
    """Numbers, ranges and ``all`` out of a reference cell.

    Returns ``(numbers, unparsed)``. ``numbers`` is ``None`` for an explicit
    *all*; an empty tuple for an explicit none (``–``) or an empty cell;
    ``unparsed`` holds the text when it carried something unreadable.
    """
    raw = text.strip()
    if not raw:
        return (), None
    lowered = raw.lower()
    if re.search(r"\ball\b", lowered):
        return None, None
    if re.fullmatch(rf"{_DASH}|n/?a|none", lowered):
        return (), None
    body = re.sub(rf"\b{re.escape(prefix)}", "", raw, flags=re.IGNORECASE) if prefix else raw
    numbers: set[int] = set()
    for a, b in _RE_RANGE.findall(body):
        lo, hi = int(a), int(b)
        if lo <= hi:
            numbers.update(range(lo, hi + 1))
    rest = _RE_RANGE.sub(" ", body)
    numbers.update(int(n) for n in _RE_INT.findall(rest))
    if not numbers:
        return (), raw
    return tuple(sorted(numbers)), None


@dataclass(frozen=True)
class Row:
    """One data row of one rendered table, continuation rows merged in."""

    table: str
    cells: tuple[str, ...]
    where: tuple[Where, ...]
    columns: tuple[str, ...]

    @property
    def text(self) -> str:
        return "| " + " | ".join(self.cells) + " |"

    def to_dict(self) -> dict[str, Any]:
        return {
            "table": self.table,
            "cells": list(self.cells),
            "where": [w.to_dict() for w in self.where],
        }


TABLE_DELIVERABLES: str = "deliverables"
TABLE_MILESTONES: str = "milestones"
TABLE_DCS: str = "dcs"
TABLE_RISKS: str = "risks"
TABLES: tuple[str, ...] = (TABLE_DELIVERABLES, TABLE_MILESTONES, TABLE_DCS, TABLE_RISKS)


def _table_kind(cells: Sequence[str]) -> str | None:
    """Which table a header row opens, by the headings the form fixes."""
    first = _norm(cells[0]) if cells else ""
    rest = {_norm(c) for c in cells[1:]}
    if first == "number" and "deliverabletitle" in rest:
        return TABLE_DELIVERABLES
    if first == "number" and "meansofverification" in rest:
        return TABLE_MILESTONES
    if first in {"dcno.", "dcno", "dcnumber"}:
        return TABLE_DCS
    if first == "descriptionofrisk":
        return TABLE_RISKS
    return None


def _opens_row(table: str, cells: Sequence[str]) -> bool:
    """Whether *cells* start a new data row of *table* (else a continuation)."""
    first = _norm(cells[0]) if cells else ""
    if table == TABLE_DELIVERABLES:
        return re.fullmatch(r"d\d+\.\d+", first) is not None
    if table == TABLE_MILESTONES:
        return re.fullmatch(r"m\d+\.\d+", first) is not None
    if table == TABLE_DCS:
        return re.fullmatch(r"dc\d+", first) is not None
    if table == TABLE_RISKS:
        return any(c.strip() for c in cells[1:4])
    return False


@dataclass(frozen=True)
class WpBlock:
    number: int
    title: str | None
    start: int | None
    end: int | None
    lead: str | None
    participants: str | None
    dcs: tuple[int, ...] | None   # None = all; () = explicitly none
    dcs_text: str | None
    tasks: tuple[tuple[int, int], ...]
    where: Where
    unparsed: tuple[str, ...] = ()

    @property
    def window(self) -> tuple[int, int] | None:
        return (self.start, self.end) if self.start is not None and self.end is not None else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "start": self.start,
            "end": self.end,
            "lead": self.lead,
            "participants": self.participants,
            "dcs": "all" if self.dcs is None else list(self.dcs),
            "dcs_text": self.dcs_text,
            "tasks": [f"{a}.{b}" for a, b in self.tasks],
            "where": self.where.to_dict(),
        }


@dataclass(frozen=True)
class DcProject:
    number: int
    title: str
    host: str | None
    host_wps: tuple[int, ...]
    secondment_bullets: int
    where: Where

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "host": self.host,
            "host_wps": list(self.host_wps),
            "secondment_bullets": self.secondment_bullets,
            "where": self.where.to_dict(),
        }


@dataclass(frozen=True)
class Paragraph:
    where: Where
    text: str


@dataclass(frozen=True)
class ParsedTables:
    """Everything the checks read, parsed once."""

    rows: tuple[Row, ...]
    headers: Mapping[str, tuple[str, ...]]
    wp_blocks: tuple[WpBlock, ...]
    dc_projects: tuple[DcProject, ...]
    prose: tuple[Paragraph, ...]
    rows_rendered: int
    rows_parsed: int
    rows_merged: int
    unparsed: tuple[Finding, ...]

    def table(self, kind: str) -> tuple[Row, ...]:
        return tuple(r for r in self.rows if r.table == kind)

    def wp(self, number: int) -> WpBlock | None:
        for b in self.wp_blocks:
            if b.number == number:
                return b
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows_rendered": self.rows_rendered,
            "rows_parsed": self.rows_parsed,
            "rows_merged": self.rows_merged,
            "tables": {
                k: {"columns": list(self.headers.get(k, ())), "rows": len(self.table(k))}
                for k in TABLES
            },
            "wp_blocks": [b.to_dict() for b in self.wp_blocks],
            "dc_projects": [p.to_dict() for p in self.dc_projects],
            "prose_paragraphs": len(self.prose),
            "unparsed": [f.to_dict() for f in self.unparsed],
        }


def _paragraphs(candidate: Candidate) -> Iterator[Paragraph]:
    for sid in sorted(candidate.contents):
        section = candidate.contents[sid]
        subs = section.get("sub_sections") if isinstance(section, Mapping) else None
        for sub in subs if isinstance(subs, list) else []:
            if not isinstance(sub, Mapping):
                continue
            ssid = str(sub.get("sub_section_id", ""))
            for i, text in enumerate(split_paragraphs(str(sub.get("content", "")))):
                yield Paragraph(Where(sid, ssid, i), text)


def parse_candidate(candidate: Candidate) -> ParsedTables:
    """Parse the rendered rows, the work-package blocks and the DC projects.

    Pure over the candidate's contents: the same artifacts parse to the same
    objects. Rows are attributed to a table by the header that precedes them;
    a header repeated at a page break re-opens the same table; a row that
    does not open a new entry is merged into the previous entry cell by cell.
    """
    rows: list[Row] = []
    headers: dict[str, tuple[str, ...]] = {}
    unparsed: list[Finding] = []
    prose: list[Paragraph] = []
    rendered = parsed = merged = 0
    current: str | None = None

    for para in _paragraphs(candidate):
        if not is_row(para.text):
            prose.append(para)
            continue
        rendered += 1
        try:
            cells = tuple(c.strip() for c in parse_row(para.text))
        except ExtractionError as exc:
            unparsed.append(Finding("parse", KIND_UNPARSED, "row", str(exc), (para.where,), (para.text[:120],)))
            continue
        parsed += 1
        kind = _table_kind(cells)
        if kind is not None:
            current = kind
            headers.setdefault(kind, cells)
            if len(cells) != len(headers[kind]):
                unparsed.append(
                    Finding("parse", KIND_UNPARSED, kind,
                            f"a repeated {kind} header has {len(cells)} columns, the first had {len(headers[kind])}",
                            (para.where,), (para.text[:120],))
                )
            continue
        if current is None:
            unparsed.append(
                Finding("parse", KIND_UNPARSED, "row", "a data row precedes any recognised table header",
                        (para.where,), (para.text[:120],))
            )
            continue
        columns = headers[current]
        if len(cells) != len(columns):
            unparsed.append(
                Finding("parse", KIND_UNPARSED, current,
                        f"row has {len(cells)} cells, the {current} header has {len(columns)}",
                        (para.where,), (para.text[:120],))
            )
            continue
        if _opens_row(current, cells):
            rows.append(Row(current, cells, (para.where,), columns))
            continue
        # A continuation: the previous entry of the same table wrapped over a page break.
        prev_index = next((i for i in range(len(rows) - 1, -1, -1) if rows[i].table == current), None)
        if prev_index is None:
            unparsed.append(
                Finding("parse", KIND_UNPARSED, current, "a continuation row has no entry to continue",
                        (para.where,), (para.text[:120],))
            )
            continue
        prev = rows[prev_index]
        joined = tuple(
            (a + " " + b).strip() if b else a for a, b in zip(prev.cells, cells)
        )
        rows[prev_index] = Row(current, joined, prev.where + (para.where,), columns)
        merged += 1

    wp_blocks = _parse_wp_blocks(prose)
    dc_projects = _parse_dc_projects(prose)
    return ParsedTables(
        rows=tuple(rows),
        headers=headers,
        wp_blocks=wp_blocks,
        dc_projects=dc_projects,
        prose=tuple(prose),
        rows_rendered=rendered,
        rows_parsed=parsed,
        rows_merged=merged,
        unparsed=tuple(unparsed),
    )


def _parse_wp_blocks(prose: Sequence[Paragraph]) -> tuple[WpBlock, ...]:
    """The label-value work-package blocks (Table 3.1 a flattened to prose, spec §2.11)."""
    blocks: list[WpBlock] = []
    i = 0
    n = len(prose)
    while i < n:
        m = _RE_WP_BLOCK.match(prose[i].text)
        if not m:
            i += 1
            continue
        number = int(m.group(1))
        where = prose[i].where
        title = start = end = lead = participants = dcs_text = None
        dcs: tuple[int, ...] | None = ()
        dcs_seen = False
        tasks: list[tuple[int, int]] = []
        bad: list[str] = []
        j = i + 1
        while j < n:
            t = prose[j].text
            if _RE_WP_BLOCK.match(t) or _RE_TABLE_CAPTION.match(t) or _RE_DC_HEADING.match(t):
                break
            if prose[j].where.section_id != where.section_id or prose[j].where.sub_section_id != where.sub_section_id:
                break
            mt = _RE_WP_TITLE.match(t)
            if mt:
                title, start, end = mt.group("title").strip(), int(mt.group("start")), int(mt.group("end"))
            elif _RE_WP_TITLE_ONLY.match(t) and title is None:
                title = _RE_WP_TITLE_ONLY.match(t).group("title").strip()  # type: ignore[union-attr]
                bad.append(f"WP title line carries no parsable start/end month: {t[:80]!r}")
            elif _RE_LEAD.match(t):
                lead = _RE_LEAD.match(t).group("value").strip() or None  # type: ignore[union-attr]
                if lead is None and j + 1 < n and not _looks_like_label(prose[j + 1].text):
                    lead = prose[j + 1].text.strip()
                    j += 1
            elif _RE_PARTICIPANTS.match(t):
                participants = _RE_PARTICIPANTS.match(t).group("value").strip() or None  # type: ignore[union-attr]
                if participants is None and j + 1 < n and not _looks_like_label(prose[j + 1].text):
                    participants = prose[j + 1].text.strip()
                    j += 1
            elif _RE_DCS.match(t):
                dcs_seen = True
                dcs_text = _RE_DCS.match(t).group("value").strip()  # type: ignore[union-attr]
                if not dcs_text and j + 1 < n and not _looks_like_label(prose[j + 1].text):
                    dcs_text = prose[j + 1].text.strip()
                    j += 1
                dcs, unread = _refs(dcs_text, prefix="DC")
                if unread:
                    bad.append(f"DCs involved not parsable: {unread!r}")
            else:
                mk = _RE_TASK.match(t)
                if mk:
                    tasks.append((int(mk.group(1)), int(mk.group(2))))
            j += 1
        blocks.append(
            WpBlock(
                number=number, title=title, start=start, end=end, lead=lead,
                participants=participants, dcs=dcs if dcs_seen else (),
                dcs_text=dcs_text if dcs_seen else None, tasks=tuple(tasks), where=where,
                unparsed=tuple(bad),
            )
        )
        i = j
    return tuple(blocks)


def _looks_like_label(text: str) -> bool:
    return bool(
        _RE_WP_BLOCK.match(text) or _RE_WP_TITLE_ONLY.match(text) or _RE_LEAD.match(text)
        or _RE_PARTICIPANTS.match(text) or _RE_DCS.match(text) or _RE_TASK.match(text)
        or _RE_TABLE_CAPTION.match(text) or re.match(r"^Objectives?:?\s*$", text, re.IGNORECASE)
    )


def _parse_dc_projects(prose: Sequence[Paragraph]) -> tuple[DcProject, ...]:
    """The per-DC research projects of section 1.1: ``DC<n> – <title>``, a Host line, secondment bullets."""
    projects: list[DcProject] = []
    i = 0
    n = len(prose)
    while i < n:
        m = _RE_DC_HEADING.match(prose[i].text)
        if not m:
            i += 1
            continue
        number = int(m.group(1))
        where = prose[i].where
        host: str | None = None
        host_wps: tuple[int, ...] = ()
        bullets = 0
        in_secondments = False
        j = i + 1
        while j < n:
            t = prose[j].text
            if _RE_DC_HEADING.match(t) or _RE_WP_BLOCK.match(t) or _RE_TABLE_CAPTION.match(t):
                break
            if prose[j].where.section_id != where.section_id or prose[j].where.sub_section_id != where.sub_section_id:
                break
            if _RE_HOST.match(t) and host is None:
                host = _RE_HOST.match(t).group("value").strip()  # type: ignore[union-attr]
                found: set[int] = set()
                for inner in _RE_HOST_WPS.findall(host):
                    nums, _ = _refs(inner, prefix="WP")
                    found.update(nums or ())
                host_wps = tuple(sorted(found))
            elif _RE_SECONDMENTS.match(t):
                in_secondments = True
            elif in_secondments and _RE_BULLET.match(t):
                bullets += 1
            elif in_secondments and not _RE_BULLET.match(t):
                in_secondments = False
            if _RE_CONTRIBUTION.match(t):
                j += 2  # the heading and its one paragraph close the project
                break
            j += 1
        projects.append(
            DcProject(number=number, title=m.group("title").strip(), host=host, host_wps=host_wps,
                      secondment_bullets=bullets, where=where)
        )
        i = j
    return tuple(projects)


# --------------------------------------------------------------------------- #
# Typed views over the rows
# --------------------------------------------------------------------------- #


def _col(row: Row, *names: str) -> str:
    """The cell under the first header whose normalised name matches one of *names*."""
    wanted = {_norm(n) for n in names}
    for name, cell in zip(row.columns, row.cells):
        if _norm(name) in wanted:
            return cell
    return ""


def _deliverables(parsed: ParsedTables) -> list[dict[str, Any]]:
    out = []
    for r in parsed.table(TABLE_DELIVERABLES):
        wps, wp_bad = _refs(_col(r, "WP", "W P", "Work package"), prefix="WP")
        months, m_bad = _months(_col(r, "Due", "Due date", "Delivery date", "Due month"))
        out.append({
            "id": r.cells[0], "title": _col(r, "Deliverable Title", "Title"),
            "wps": wps, "wp_text": _col(r, "WP", "W P", "Work package"), "wp_unparsed": wp_bad,
            "lead": _col(r, "Lead Beneficiary", "Lead participant", "Lead"),
            "months": months, "months_unparsed": m_bad, "row": r,
        })
    return out


def _milestones(parsed: ParsedTables) -> list[dict[str, Any]]:
    out = []
    for r in parsed.table(TABLE_MILESTONES):
        wps, wp_bad = _refs(_col(r, "Related WP", "Related WP(s)", "WP", "W P"), prefix="WP")
        months, m_bad = _months(_col(r, "Due Date", "Due", "Due month"))
        text = " ".join((r.cells[1], _col(r, "Means of Verification")))
        deps = tuple(sorted({f"D{a}.{b}" for a, b in _RE_DELIV_ID.findall(text)}))
        out.append({
            "id": r.cells[0], "title": r.cells[1], "wps": wps,
            "wp_text": _col(r, "Related WP", "Related WP(s)", "WP", "W P"), "wp_unparsed": wp_bad,
            "lead": _col(r, "Lead Beneficiary", "Lead participant", "Lead"),
            "months": months, "months_unparsed": m_bad, "depends_on": deps, "row": r,
        })
    return out


def _dcs(parsed: ParsedTables) -> list[dict[str, Any]]:
    out = []
    for r in parsed.table(TABLE_DCS):
        num = int(re.sub(r"\D", "", r.cells[0]) or 0)
        start, s_bad = _months(_col(r, "Planned Start Month", "Start month", "Start"))

        def _int(cell: str) -> int | None:
            m = _RE_INT.search(cell)
            return int(m.group(1)) if m else None

        out.append({
            "number": num, "id": r.cells[0],
            "recruiting": _col(r, "Recruiting Participant", "Recruiting participant"),
            "awarding": _col(r, "PhD Awarding Entity", "PhD awarding entity"),
            "start": start[0] if start else None, "start_unparsed": s_bad,
            "duration": _int(_col(r, "Duration (months)", "Duration")),
            "secondments": _int(_col(r, "Total Duration of Secondments (months)", "Secondments")),
            "non_academic": _int(_col(r, "Total Duration in Non- academic Sector (months)",
                                      "Total Duration in Non-academic Sector (months)", "Non-academic")),
            "row": r,
        })
    return out


def _risks(parsed: ParsedTables) -> list[dict[str, Any]]:
    out = []
    for i, r in enumerate(parsed.table(TABLE_RISKS)):
        wps, wp_bad = _refs(_col(r, "WPs involved", "WP involved", "WPs", "WP"), prefix="WP")
        mitigation = _col(r, "Proposed risk-mitigation measures", "Mitigation measures", "Mitigation")
        threshold = _RE_THRESHOLD.search(mitigation) or _RE_THRESHOLD.search(r.cells[0])
        out.append({
            "index": i, "description": r.cells[0], "wps": wps,
            "wp_text": _col(r, "WPs involved", "WP involved", "WPs", "WP"), "wp_unparsed": wp_bad,
            "likelihood": _col(r, "Likelihood"), "severity": _col(r, "Severity"),
            "mitigation": mitigation, "threshold": threshold.group(0) if threshold else None, "row": r,
        })
    return out


# --------------------------------------------------------------------------- #
# The five checks
# --------------------------------------------------------------------------- #


def _in_window(month: int, window: tuple[int, int]) -> bool:
    return window[0] <= month <= window[1]


def _check_wp(parsed: ParsedTables) -> CheckResult:
    cid, title = CHECKS[0]
    findings: list[Finding] = []
    compared = 0
    numbers = {b.number for b in parsed.wp_blocks}
    for b in parsed.wp_blocks:
        subject = f"WP{b.number}"
        for name, value in (("lead participant", b.lead), ("start/end month", b.window),
                            ("DCs involved", b.dcs_text), ("participants", b.participants)):
            compared += 1
            if value is None:
                findings.append(Finding(cid, KIND_MISSING_FIELD, subject,
                                        f"{subject} declares no {name}", (b.where,),
                                        (f"WP Number: {b.number}",)))
        for text in b.unparsed:
            findings.append(Finding(cid, KIND_UNPARSED, subject, text, (b.where,)))
        for a, k in b.tasks:
            compared += 1
            if a != b.number:
                findings.append(Finding(cid, KIND_INCONSISTENCY, subject,
                                        f"Task {a}.{k} is described under {subject}", (b.where,),
                                        (f"Task {a}.{k}",)))
        # DCs involved against the DC projects naming this package.
        if b.dcs_text is not None and parsed.dc_projects:
            compared += 1
            from_projects = tuple(sorted(p.number for p in parsed.dc_projects if b.number in p.host_wps))
            declared = tuple(sorted(p.number for p in parsed.dc_projects)) if b.dcs is None else b.dcs
            if declared != from_projects:
                findings.append(Finding(
                    cid, KIND_INCONSISTENCY, subject,
                    f"{subject} declares DCs involved {list(declared)}; the DC projects in 1.1 that "
                    f"name {subject} on their host line are {list(from_projects)}",
                    (b.where,) + tuple(p.where for p in parsed.dc_projects if b.number in p.host_wps),
                    (f"DCs involved {b.dcs_text}",),
                    {"declared": list(declared), "from_dc_projects": list(from_projects)},
                ))
    referenced: dict[int, list[Where]] = {}
    for d in _deliverables(parsed):
        for w in d["wps"] or ():
            referenced.setdefault(w, []).append(d["row"].where[0])
    for m in _milestones(parsed):
        for w in m["wps"] or ():
            referenced.setdefault(w, []).append(m["row"].where[0])
    for p in parsed.dc_projects:
        for w in p.host_wps:
            referenced.setdefault(w, []).append(p.where)
    for w in sorted(referenced):
        compared += 1
        if w not in numbers:
            findings.append(Finding(cid, KIND_MISSING_FIELD, f"WP{w}",
                                    f"WP{w} is referenced but no work-package block describes it",
                                    tuple(referenced[w][:3])))
    notes = () if parsed.wp_blocks else ("no work-package block found; the check compared nothing",)
    return CheckResult(cid, title, compared, tuple(findings), notes)


def _check_deliverables(parsed: ParsedTables) -> CheckResult:
    cid, title = CHECKS[1]
    findings: list[Finding] = []
    compared = 0
    seen: dict[str, Row] = {}
    for d in _deliverables(parsed):
        subject, row = d["id"], d["row"]
        compared += 1
        if subject in seen:
            findings.append(Finding(cid, KIND_INCONSISTENCY, subject, f"{subject} appears twice",
                                    (seen[subject].where[0], row.where[0])))
        seen[subject] = row
        if d["wp_unparsed"] is not None or d["wps"] is None or not d["wps"]:
            findings.append(Finding(cid, KIND_UNPARSED, subject,
                                    f"{subject}: work package cell not parsable: {d['wp_text']!r}",
                                    row.where, (row.text[:160],)))
            continue
        if d["months_unparsed"] is not None:
            findings.append(Finding(cid, KIND_UNPARSED, subject,
                                    f"{subject}: due cell not parsable: {d['months_unparsed']!r}",
                                    row.where, (row.text[:160],)))
            continue
        for w in d["wps"]:
            block = parsed.wp(w)
            if block is None:
                findings.append(Finding(cid, KIND_INCONSISTENCY, subject,
                                        f"{subject} belongs to WP{w}, which no work-package block describes",
                                        row.where, (row.text[:160],)))
                continue
            if block.window is None:
                findings.append(Finding(cid, KIND_MISSING_FIELD, subject,
                                        f"{subject}: WP{w} declares no start/end month to check against",
                                        row.where + (block.where,)))
                continue
            for month in d["months"]:
                if not _in_window(month, block.window):
                    findings.append(Finding(
                        cid, KIND_OUT_OF_WINDOW, subject,
                        f"{subject} is due M{month}; WP{w} runs M{block.start}-M{block.end}",
                        row.where + (block.where,), (row.text[:160],),
                        {"month": month, "window": list(block.window)},
                    ))
    notes = () if seen else ("no deliverables table found; the check compared nothing",)
    return CheckResult(cid, title, compared, tuple(findings), notes)


def _check_milestones(parsed: ParsedTables) -> CheckResult:
    cid, title = CHECKS[2]
    findings: list[Finding] = []
    compared = 0
    deliverables = {d["id"]: d for d in _deliverables(parsed)}
    milestones = _milestones(parsed)
    for m in milestones:
        subject, row = m["id"], m["row"]
        compared += 1
        if m["months_unparsed"] is not None or not m["months"]:
            findings.append(Finding(cid, KIND_UNPARSED, subject,
                                    f"{subject}: due cell not parsable: {m['months_unparsed']!r}",
                                    row.where, (row.text[:160],)))
            continue
        month = m["months"][0]
        if m["wp_unparsed"] is not None:
            findings.append(Finding(cid, KIND_UNPARSED, subject,
                                    f"{subject}: related WP cell not parsable: {m['wp_text']!r}",
                                    row.where, (row.text[:160],)))
        related = (tuple(b.number for b in parsed.wp_blocks) if m["wps"] is None else m["wps"]) or ()
        for w in related:
            block = parsed.wp(w)
            if block is None:
                findings.append(Finding(cid, KIND_INCONSISTENCY, subject,
                                        f"{subject} relates to WP{w}, which no work-package block describes",
                                        row.where, (row.text[:160],)))
            elif block.window is not None and not _in_window(month, block.window):
                findings.append(Finding(
                    cid, KIND_OUT_OF_WINDOW, subject,
                    f"{subject} is due M{month}; its related WP{w} runs M{block.start}-M{block.end}",
                    row.where + (block.where,), (row.text[:160],),
                    {"month": month, "window": list(block.window)},
                ))
        if m["depends_on"]:
            for dep in m["depends_on"]:
                compared += 1
                d = deliverables.get(dep)
                if d is None:
                    findings.append(Finding(cid, KIND_INCONSISTENCY, subject,
                                            f"{subject} names {dep}, which the deliverables table does not list",
                                            row.where, (row.text[:160],)))
                    continue
                late = [x for x in d["months"] if x > month]
                if late:
                    findings.append(Finding(
                        cid, KIND_INCONSISTENCY, subject,
                        f"{subject} is due M{month} but depends on {dep}, due M{max(late)}",
                        row.where + d["row"].where, (row.text[:160], d["row"].text[:160]),
                        {"milestone_month": month, "deliverable_months": list(d["months"])},
                    ))
            continue
        context = {
            "related_wps": list(related),
            "deliverables_of_related_wps": [
                {"id": d["id"], "months": list(d["months"])}
                for d in deliverables.values()
                if d["wps"] and any(w in related for w in d["wps"])
            ],
        }
        findings.append(Finding(
            cid, KIND_UNDECLARED, subject,
            f"{subject} names no deliverable it depends on; the deliverables of its related "
            f"package(s) and their months are listed as context, not judged",
            row.where, (row.text[:160],), context,
        ))
    notes = () if milestones else ("no milestones table found; the check compared nothing",)
    return CheckResult(cid, title, compared, tuple(findings), notes)


def _check_dcs(parsed: ParsedTables) -> CheckResult:
    cid, title = CHECKS[3]
    findings: list[Finding] = []
    compared = 0
    table = _dcs(parsed)
    projects = {p.number: p for p in parsed.dc_projects}
    in_table = {d["number"] for d in table}
    if table or projects:
        compared += 1
        if in_table != set(projects):
            findings.append(Finding(
                cid, KIND_INCONSISTENCY, "DC set",
                f"the DC table lists {sorted(in_table)}; section 1.1 describes projects for {sorted(projects)}",
                tuple(d["row"].where[0] for d in table[:1]) + tuple(p.where for p in list(projects.values())[:1]),
                (), {"table": sorted(in_table), "projects": sorted(projects)},
            ))
    for d in table:
        subject, row = d["id"], d["row"]
        p = projects.get(d["number"])
        if p is None:
            continue
        compared += 1
        if p.host is None:
            findings.append(Finding(cid, KIND_MISSING_FIELD, subject, f"{subject}: the 1.1 project has no Host line",
                                    (p.where,)))
        else:
            findings.append(Finding(
                cid, KIND_NOT_COMPARABLE, subject,
                f"{subject}: the table names recruiting participant {d['recruiting']!r}; the 1.1 project "
                f"describes its host as {p.host!r}. The identifiers were removed by sanitisation, so the "
                f"two cannot be compared",
                row.where + (p.where,), (row.text[:160],),
                {"recruiting_participant": d["recruiting"], "host_line": p.host},
            ))
        if d["start"] is None or d["duration"] is None:
            findings.append(Finding(cid, KIND_UNPARSED, subject,
                                    f"{subject}: start month or duration not parsable", row.where, (row.text[:160],)))
        else:
            last = d["start"] + d["duration"] - 1
            ended_early: list[tuple[int, int]] = []
            for w in p.host_wps:
                compared += 1
                block = parsed.wp(w)
                if block is None:
                    findings.append(Finding(cid, KIND_INCONSISTENCY, subject,
                                            f"{subject}'s project names WP{w}, which no work-package block describes",
                                            (p.where,)))
                elif block.window is not None and last > block.end:
                    ended_early.append((w, block.end))
            if ended_early:
                wps = ", ".join(f"WP{w} ends M{e}" for w, e in ended_early)
                where = row.where + (p.where,) + tuple(
                    b.where for w, _ in ended_early for b in parsed.wp_blocks if b.number == w
                )
                findings.append(Finding(
                    cid, KIND_OUT_OF_WINDOW, subject,
                    f"{subject} runs M{d['start']}-M{last} ({d['duration']} months); {wps}",
                    where, (row.text[:160],),
                    {"dc_window": [d["start"], last], "wps_ending_before": [list(x) for x in ended_early]},
                ))
        if d["duration"] is not None and d["secondments"] is not None and d["secondments"] > d["duration"]:
            compared += 1
            findings.append(Finding(cid, KIND_INCONSISTENCY, subject,
                                    f"{subject}: {d['secondments']} secondment months exceed the {d['duration']}-month contract",
                                    row.where, (row.text[:160],)))
    notes = ()
    if not table:
        notes += ("no DC table found; the check compared nothing",)
    if not projects:
        notes += ("no DC project blocks found in prose; the check compared nothing",)
    return CheckResult(cid, title, compared, tuple(findings), notes)


def _check_risks(parsed: ParsedTables) -> CheckResult:
    cid, title = CHECKS[4]
    findings: list[Finding] = []
    compared = 0
    risks = _risks(parsed)
    numbers = {b.number for b in parsed.wp_blocks}
    any_threshold = False
    thresholds: list[str] = []
    for r in risks:
        subject = f"risk {r['index'] + 1}"
        row = r["row"]
        compared += 1
        if r["wp_unparsed"] is not None:
            findings.append(Finding(cid, KIND_UNPARSED, subject,
                                    f"{subject}: WPs involved not parsable: {r['wp_text']!r}", row.where, (row.text[:160],)))
        for w in r["wps"] or ():
            if numbers and w not in numbers:
                findings.append(Finding(cid, KIND_INCONSISTENCY, subject,
                                        f"{subject} involves WP{w}, which no work-package block describes",
                                        row.where, (row.text[:160],)))
        if not r["mitigation"].strip():
            findings.append(Finding(cid, KIND_MISSING_FIELD, subject, f"{subject} states no mitigation measure",
                                    row.where, (row.text[:160],)))
        if r["threshold"]:
            any_threshold = True
            thresholds.append(f"{subject}: {r['threshold']!r}")
    # Mitigations named in prose, linked to a row by shared vocabulary. A hit
    # that ends in a colon introduces a list; its bullets are read with it.
    prose_hits: list[tuple[Paragraph, str]] = []
    for i, p in enumerate(parsed.prose):
        if not _RE_MITIGATION_PROSE.search(p.text):
            continue
        text = p.text
        if text.rstrip().endswith(":"):
            j = i + 1
            while (
                j < len(parsed.prose)
                and _RE_BULLET.match(parsed.prose[j].text)
                and parsed.prose[j].where.sub_section_id == p.where.sub_section_id
            ):
                text += " " + parsed.prose[j].text
                j += 1
        prose_hits.append((p, text))
    row_tokens = [(r, _tokens(r["description"] + " " + r["mitigation"])) for r in risks]
    linked_rows: set[int] = set()
    for p, text in prose_hits:
        compared += 1
        pt = _tokens(text)
        matches = [r["index"] for r, toks in row_tokens if len(pt & toks) >= 3]
        linked_rows.update(matches)
        if not matches:
            findings.append(Finding(
                cid, KIND_UNLINKED_PROSE, f"{p.where.sub_section_id}#{p.where.paragraph_index}",
                "prose names a mitigation that shares no vocabulary with any risk-table row",
                (p.where,), (text[:200],),
            ))
    notes: tuple[str, ...] = (
        f"threshold stated in any risk row: {'yes' if any_threshold else 'no'}"
        + (f" ({'; '.join(thresholds)})" if thresholds else ""),
        f"prose paragraphs naming a mitigation: {len(prose_hits)}; risk rows they link to: {sorted(linked_rows)}",
    )
    if not risks:
        notes += ("no risk table found; the check compared nothing",)
    return CheckResult(cid, title, compared, tuple(findings), notes)


def run_checks(parsed: ParsedTables) -> tuple[CheckResult, ...]:
    """The five checks, in spec order, over one parse."""
    return (
        _check_wp(parsed),
        _check_deliverables(parsed),
        _check_milestones(parsed),
        _check_dcs(parsed),
        _check_risks(parsed),
    )


# --------------------------------------------------------------------------- #
# The grounding axis
# --------------------------------------------------------------------------- #


def enumerate_grounding(candidate: Candidate) -> dict[str, Any]:
    """Every ledger claim, reported Unresolved with :data:`GROUNDING_REASON`.

    Reads each section artifact's ``validation_status.claim_statuses`` through
    the same loader the pack builder uses. No judge runs. Flags a vacuous
    ledger and any entry whose declaration contradicts the import contract.
    """
    rows: list[dict[str, Any]] = []
    flags: list[str] = []
    for sid in sorted(candidate.sections):
        try:
            claims: tuple[SectionClaim, ...] = load_section_claims(candidate.sections[sid])
        except StatusFaithfulnessError as exc:
            flags.append(f"{sid}: {exc}")
            continue
        for c in claims:
            declared = c.status
            if declared != _LEDGER_EXPECTED_STATUS:
                flags.append(
                    f"{sid}/{c.entry_key} declares status {declared!r}, not {_LEDGER_EXPECTED_STATUS!r}; "
                    "the declaration is not evidence and the claim is still reported Unresolved"
                )
            rows.append({
                "section_id": sid,
                "entry_key": c.entry_key,
                "claim_id": c.claim_id,
                "claim_summary": c.claim_summary,
                "declared_status": declared,
                # The import writes the claim's own verified span here: where the
                # assertion sits in the proposal's page sources. A location, not a source.
                "assertion_location": c.source_ref,
                "status": GROUNDING_STATUS,
                "severity": SEVERITY_UNRESOLVED,
                "reason": GROUNDING_REASON,
            })
    vacuous = not rows
    if vacuous:
        flags.append("grounding axis is vacuous: the ledger holds no claims to enumerate (spec PE-07)")
    return {
        "axis": "grounding",
        "judge": None,
        "reason": GROUNDING_REASON,
        "assertion_location_note": (
            "assertion_location is the claim's verified span into the proposal's own page "
            "sources (spec PE-03): it locates the assertion and is not evidence for it"
        ),
        "claims_total": len(rows),
        "unresolved": len(rows),
        "vacuous": vacuous,
        "flags": flags,
        "rows": rows,
    }


# --------------------------------------------------------------------------- #
# The baseline binding
# --------------------------------------------------------------------------- #


def bind_baseline(
    baseline_dir: Path | str | None,
    *,
    candidate_digest: str,
    snapshot_id: str,
) -> dict[str, Any]:
    """Compare this audit's candidate hash and snapshot id with the frozen baseline's.

    Returns a statement the report carries verbatim; raises
    :class:`IntegrityAuditError` only when a directory was given and holds no
    readable freeze, because an audit that claims a baseline it could not read
    would be the fabricated completion CLAUDE.md §15 forbids.
    """
    if baseline_dir is None:
        return {
            "status": BASELINE_NONE,
            "baseline_dir": None,
            "statement": "no frozen baseline was consulted; rerun with --baseline-dir after the freeze",
        }
    try:
        frozen: FrozenBaseline = load_frozen_baseline(baseline_dir)
    except BlindBaselineError as exc:
        raise IntegrityAuditError(f"baseline directory given but no baseline could be read: {exc}") from exc
    b = frozen.record.get("bindings") or {}
    frozen_hash = b.get("candidate_hash")
    frozen_snapshot = b.get("snapshot_id")
    common = {
        "baseline_dir": Path(baseline_dir).as_posix(),
        "report_copy": frozen.record.get("report_copy"),
        "report_sha256": frozen.record.get("report_sha256"),
        "candidate_hash_frozen": frozen_hash,
        "candidate_hash_audited": candidate_digest,
        "snapshot_id_frozen": frozen_snapshot,
        "snapshot_id_audited": snapshot_id or None,
    }
    if frozen_hash != candidate_digest:
        return {**common, "status": BASELINE_OTHER_CANDIDATE,
                "statement": "the frozen baseline binds a different candidate hash; this audit does not describe the frozen candidate"}
    if not snapshot_id:
        return {**common, "status": BASELINE_UNKNOWN_SNAPSHOT,
                "statement": "candidate hash equals the baseline's; the directory route carries no snapshot id, so the baseline's snapshot id was not re-derived"}
    if frozen_snapshot == snapshot_id:
        return {**common, "status": BASELINE_BOUND,
                "statement": "candidate hash and snapshot id equal the frozen baseline's; the audit is bound to the baseline"}
    return {**common, "status": BASELINE_REDERIVED,
            "statement": f"the baseline was re-derived: the snapshot id moved from {frozen_snapshot} to {snapshot_id} over the same candidate"}


# --------------------------------------------------------------------------- #
# The report
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class IntegrityAuditReport:
    candidate_hash: str
    candidate_path: str
    evidence_source: str
    profile_id: str
    profile_version: str
    audited_at: str
    parse: Mapping[str, Any]
    checks: tuple[CheckResult, ...]
    grounding: Mapping[str, Any]
    baseline: Mapping[str, Any]
    flags: tuple[str, ...]
    document: str = ""
    document_id: str = ""
    snapshot_id: str = ""
    package_id: str = ""
    policy_version: str = ""
    writes: tuple[str, ...] = ()
    notes: str = _ADVISORY_NOTE
    advisory: bool = True
    blocking: bool = False

    def __post_init__(self) -> None:
        if self.advisory is not True or self.blocking is not False:
            raise ValueError("IntegrityAuditReport must carry advisory=True and blocking=False.")
        if not str(self.candidate_hash).startswith("sha256:"):
            raise ValueError("IntegrityAuditReport.candidate_hash must be a sha256: hash.")
        if self.evidence_source not in (EVIDENCE_SOURCE_DEV_GRAPH, EVIDENCE_SOURCE_DIRECTORY):
            raise ValueError(f"unknown evidence_source {self.evidence_source!r}.")
        if self.baseline.get("status") not in BASELINE_STATUSES:
            raise ValueError(f"unknown baseline status {self.baseline.get('status')!r}.")

    @property
    def findings(self) -> tuple[Finding, ...]:
        return tuple(f for c in self.checks for f in c.findings)

    def to_dict(self) -> dict[str, Any]:
        by_kind = {k: sum(1 for f in self.findings if f.kind == k) for k in FINDING_KINDS}
        return {
            "record_type": AUDIT_RECORD_TYPE,
            "metric": AUDIT_METRIC,
            "schema_version": AUDIT_SCHEMA_VERSION,
            "advisory": self.advisory,
            "blocking": self.blocking,
            "audited_at": self.audited_at,
            "candidate_hash": self.candidate_hash,
            "candidate_path": self.candidate_path,
            "evidence_source": self.evidence_source,
            "document": self.document,
            "document_id": self.document_id,
            "snapshot_id": self.snapshot_id,
            "package_id": self.package_id,
            "policy_version": self.policy_version,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "parse": dict(self.parse),
            "checks": [c.to_dict() for c in self.checks],
            "findings_total": len(self.findings),
            "findings_by_kind": {k: v for k, v in by_kind.items() if v},
            "grounding": dict(self.grounding),
            "baseline": dict(self.baseline),
            "writes": list(self.writes),
            "flags": list(self.flags),
            "notes": self.notes,
        }


def run_audit(
    candidate: Candidate,
    *,
    profile_id: str,
    profile_version: str,
    candidate_path: str,
    evidence: BlindEvidence | None = None,
    baseline_dir: Path | str | None = None,
    out_dir: Path | str | None = None,
    graph_root: Path | str | None = None,
    clock: Clock | None = None,
) -> IntegrityAuditReport:
    """Parse, check, enumerate and bind — one report, nothing written."""
    parsed = parse_candidate(candidate)
    checks = run_checks(parsed)
    grounding = enumerate_grounding(candidate)
    digest = candidate_hash(candidate)
    snapshot_id = evidence.snapshot_id if evidence is not None else ""
    baseline = bind_baseline(baseline_dir, candidate_digest=digest, snapshot_id=snapshot_id)
    flags: list[str] = list(grounding["flags"])
    if baseline["status"] in (BASELINE_REDERIVED, BASELINE_OTHER_CANDIDATE):
        flags.append(f"baseline: {baseline['statement']}")
    writes: list[str] = []
    if out_dir is not None and graph_root is not None:
        try:
            Path(out_dir).resolve().relative_to(Path(graph_root).resolve())
            flags.append(
                f"out-dir {Path(out_dir).as_posix()} lies under the graph root; the audit writes only "
                "there and nothing under the dev-graph record directories, but keep the report outside "
                "the graph root so the snapshot cannot be touched by a later tool reading it"
            )
        except ValueError:
            pass
    for f in parsed.unparsed:
        flags.append(f"parse: {f.detail}")
    return IntegrityAuditReport(
        candidate_hash=digest,
        candidate_path=candidate_path,
        evidence_source=EVIDENCE_SOURCE_DEV_GRAPH if evidence is not None else EVIDENCE_SOURCE_DIRECTORY,
        document=evidence.document if evidence is not None else "",
        document_id=evidence.document_id if evidence is not None else "",
        snapshot_id=snapshot_id,
        package_id=evidence.package.package_id if evidence is not None else "",
        policy_version=str(evidence.package.manifest.get("policy_version", "")) if evidence is not None else "",
        profile_id=profile_id,
        profile_version=profile_version,
        audited_at=(clock or _utc_now)(),
        parse=parsed.to_dict(),
        checks=checks,
        grounding=grounding,
        baseline=baseline,
        writes=tuple(writes),
        flags=tuple(flags),
    )


def write_audit(report: IntegrityAuditReport, reports_dir: Path | str) -> Path:
    """Write *report* as ``integrity_<hash12>_<NNNN>.json``; never overwrite."""
    out_dir = Path(reports_dir)
    target = next_report_path(out_dir, report.candidate_hash, prefix=_REPORT_PREFIX)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = report.to_dict()
    # The path as the operator gave it, so a committed report stays portable.
    data["writes"] = [(Path(reports_dir) / target.name).as_posix()]
    atomic_write_json(data, target, prefix="integrity_audit_")
    return target


def load_audit(path: Path | str) -> dict[str, Any]:
    """Load a persisted audit report, fail-closed on shape and flags."""
    import json

    p = Path(path)
    if not p.is_file():
        raise IntegrityAuditError(f"audit report not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise IntegrityAuditError(f"audit {p} is not valid JSON: {exc}") from exc
    if not isinstance(data, Mapping) or data.get("record_type") != AUDIT_RECORD_TYPE:
        raise IntegrityAuditError(f"{p} is not an {AUDIT_RECORD_TYPE!r} record.")
    if data.get("advisory") is not True or data.get("blocking") is not False:
        raise IntegrityAuditError(f"audit {p} must carry advisory=true and blocking=false.")
    for key in ("candidate_hash", "profile_version", "checks", "grounding", "baseline"):
        if key not in data:
            raise IntegrityAuditError(f"audit {p} lacks {key!r}.")
    return dict(data)


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #


def _ascii(text: str) -> str:
    return text.encode("ascii", "replace").decode("ascii")


def render_audit(report: Mapping[str, Any]) -> str:
    """One screen of text: counts by check and by kind, the grounding axis, the baseline."""
    lines = [
        f"INTEGRITY AUDIT  candidate {report.get('candidate_hash')}",
        f"profile {report.get('profile_id')}@{report.get('profile_version')}  "
        f"evidence {report.get('evidence_source')}  snapshot {report.get('snapshot_id') or '-'}",
        "",
    ]
    parse = report.get("parse") or {}
    tables = parse.get("tables") or {}
    lines.append(
        f"rows rendered {parse.get('rows_rendered')}, parsed {parse.get('rows_parsed')}, "
        f"merged {parse.get('rows_merged')}; "
        + ", ".join(f"{k} {v.get('rows')}" for k, v in tables.items())
        + f"; WP blocks {len(parse.get('wp_blocks') or [])}; DC projects {len(parse.get('dc_projects') or [])}"
    )
    lines.append("")
    for c in report.get("checks") or []:
        kinds = ", ".join(f"{k} {v}" for k, v in (c.get("findings_by_kind") or {}).items()) or "none"
        lines.append(f"[{c.get('check_id')}] compared {c.get('compared')}; findings {c.get('findings_total')}: {kinds}")
        for note in c.get("notes") or []:
            lines.append(f"    note: {_ascii(note)}")
        for f in (c.get("findings") or [])[:12]:
            lines.append(f"    - {f.get('kind')} {f.get('subject')}: {_ascii(f.get('detail', ''))}")
        more = len(c.get("findings") or []) - 12
        if more > 0:
            lines.append(f"    ... {more} more in the report")
    lines.append("")
    g = report.get("grounding") or {}
    lines.append(
        f"grounding: {g.get('claims_total')} claims, {g.get('unresolved')} Unresolved, "
        f"reason: {g.get('reason')}{'  (VACUOUS)' if g.get('vacuous') else ''}"
    )
    b = report.get("baseline") or {}
    lines.append(f"baseline: {b.get('status')} - {_ascii(str(b.get('statement', '')))}")
    for flag in report.get("flags") or []:
        lines.append(f"flag: {_ascii(flag)}")
    lines.append("")
    lines.append("No finding above is a score. " + _ascii(str(report.get("notes", ""))))
    return "\n".join(lines)
