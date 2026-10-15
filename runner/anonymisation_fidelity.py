"""Structural fidelity comparison, stage A6 of the anonymisation pipeline (AN9).

AN9 of ``.scratch/msca-dn-anonymisation/tickets.md``, stage A6 of
``plans/msca_dn_anonymisation_handoff_2026-10-14.md``. Pure code, with no
model: :func:`fidelity` measures the derivative with the V08 dry import and
compares that inventory with the A0 reference inventory, category by category
(:data:`CATEGORIES`).

Explained or a finding
----------------------
Every measured difference is one of two things. It is **explained** when an
edit the policy authorises accounts for it: a logged A2 edit in a category the
policy edits, or a logged A4 table edit. It is a **finding** otherwise, and a
finding fails the derivative until a stage is fixed and re-run. There is no
third state. In particular:

* A heading or a table header whose text changed is explained only by an edit
  logged on its page. A changed page count, a heading on another page, or a
  table of another shape is never explained: no policy rule moves layout.
* A DOI or URL that disappeared is explained by as many logged edits of that
  identifier class on its page. A citation marker is explained only when a
  neutral marker (``[R12]``) replaced it on the same page, under a policy
  category that keeps the count and position of markers.
* A point size the reference does not carry is a finding: no policy rule
  changes the size of text.

Zero is not proof
-----------------
A figure is looked at, not counted. Every page that carries an image or a
vector drawing, in either document, needs an operator's entry in the figure
review (:data:`REVIEW_SCHEMA`), even when its counts did not change. The entry's
basis follows V08's closed vocabulary (:data:`runner.dry_import.ACCEPTANCE_BASES`);
its verdicts are A6's own (:data:`FIGURE_VERDICTS`).
A ``preserved`` verdict that rests on a measurement is refused, as
:func:`runner.dry_import.check_acceptance` refuses it. A ``masked`` or
``redrawn`` figure is explained when the policy's per-figure review category
permits that action. A ``lost`` figure is a finding, because the policy drops
no figure silently.

Declared limits
---------------
* **Page-level explanation.** The inventory locates a heading or a table
  header by page only, so an A2 edit anywhere on that page explains a text
  change in it. The operator's read in A7 is what ties the two together.
* **No A3 log yet.** A3 (AN6) writes a rewrite plan and applies no edit, so the
  stage chain reads A2 and A4 logs only. A derivative carrying applied A3
  edits is refused until A3 logs them and this module reads that log.
* **Point sizes beyond the body size.** The ticket names the body size. Every
  size the derivative carries and the reference does not is reported too,
  because replacement text set smaller than its span is a visible change.
* **Figure counts.** ``differences`` counts graphical pages whose counts
  changed. ``findings`` also counts unchanged pages nobody looked at, so it can
  exceed ``differences``.
* **Inventories before AN9.** The dry import gained per-page citation counts
  and the ``bracketed_labels`` class here. A reference inventory measured
  before that is refused, and the source needs a new intake.

The census counts per page, so the review is per page. A page with two figures
gets one verdict; the operator's note says which figure it covers.

What is private
---------------
The derivative, both inventories, the stage logs, the figure review and this
report. Every path inside this repository is refused (the V17/V18 pattern).
The report records categories, pages, counts, marker classes, point sizes,
codes and edit ids. It quotes no heading, no table header and no other text.

Constitutional standing: an authoring tool, not a runtime component. It
evaluates no gate, invokes no model and writes no Tier 5 artifact
(CLAUDE.md §13.10). No manifest node binds it.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple, Optional, Sequence

from runner import anonymisation_intake as intake
from runner import dry_import as di
from runner.anonymisation_policy import LoadedPolicy, require_hash
from runner.atomic_write import atomic_write_text, canonical_json_bytes

SCHEMA = "anonymisation_structural_fidelity/1"
RECORD_TYPE = "anonymisation_structural_fidelity"

REVIEW_SCHEMA = "anonymisation_figure_review/1"
REVIEW_RECORD_TYPE = "anonymisation_figure_review"

REPORT_FILE = "structural_fidelity.json"
DERIVATIVE_INVENTORY_FILE = "derivative_inventory.json"

#: The compared categories, in report order.
CATEGORIES: tuple[str, ...] = (
    "page_count",
    "headings",
    "tables",
    "figures",
    "point_sizes",
    "citation_markers",
)

#: What the comparison does not compare, and why.
NOT_COMPARED: tuple[dict[str, str], ...] = (
    {"measure": "metadata", "reason": "A2 scrubs it by design; the A5 leak scan reads it."},
    {"measure": "character_counts",
     "reason": "A replacement has another length than the text it replaces, by design."},
    {"measure": "point_size_counts_at_shared_sizes",
     "reason": "Replacement text moves characters between counts at a size both documents carry."},
    {"measure": "fonts",
     "reason": "The edit harness sets replacements in Helvetica; the stage logs record each "
               "span's original fonts."},
    {"measure": "table_cell_text", "reason": "A4 checks every cell it writes."},
)

#: The verdicts a figure review entry may carry.
FIGURE_VERDICTS: frozenset[str] = frozenset({"preserved", "masked", "redrawn", "lost"})

#: The policy action each altering verdict names.
_ACTIONS: dict[str, str] = {"masked": "mask", "redrawn": "redraw"}

#: Citation classes an edit removes, by the A2 regex class of the same name.
IDENTIFIER_CLASSES: frozenset[str] = frozenset({"doi", "url"})
#: Citation classes whose count the policy keeps.
MARKER_CLASSES: frozenset[str] = frozenset({"bracketed_numbers", "author_year"})
#: The neutral marker class that takes a self-citation's place.
NEUTRAL_CLASS = "bracketed_labels"

_FIGURE_TOTALS: tuple[str, ...] = ("annotations", "links", "embedded_files")

_STAGE_SCHEMAS: dict[str, str] = {
    "anonymisation_redaction/1": "A2",
    "anonymisation_table_synthesis/1": "A4",
}


class FidelityRefused(RuntimeError):
    """The comparison cannot run as asked. Nothing was written."""


@dataclass(frozen=True)
class FidelityResult:
    report: Path
    derivative_inventory: Path
    passed: bool
    counts: dict[str, dict[str, int]]


class LoggedEdit(NamedTuple):
    """One edit a stage logged: where it is and what authorised it."""

    stage: str
    edit: int
    page: int
    category: Optional[str]
    regex_class: Optional[str]


# --------------------------------------------------------------------------- #
# Explanations
# --------------------------------------------------------------------------- #


class _Policy:
    """What the comparison reads from the policy."""

    def __init__(self, policy: LoadedPolicy) -> None:
        self.edited = {c.id for c in policy.categories if c.auto_edit}
        self.neutral = {c.id for c in policy.categories if {"count", "position"} <= set(c.retain)}
        self.figure_actions = {
            c.id: set(c.permitted_actions)
            for c in policy.categories
            if c.review_unit == "per_figure"
        }

    def authorised(self, edit: LoggedEdit) -> bool:
        # A4 edits only cells its table spec declares, and A4 validated that
        # spec against the policy before writing a cell.
        return edit.stage == "A4" or edit.category in self.edited


def _explanation(edits: Sequence[LoggedEdit]) -> dict[str, Any]:
    return {
        "categories": sorted({e.category for e in edits if e.category}),
        "stages": sorted({e.stage for e in edits}),
        "edits": [f"{e.stage}:{e.edit}" for e in edits],
    }


class _Report:
    def __init__(self, edits: Sequence[LoggedEdit], policy: _Policy) -> None:
        self.policy = policy
        self.edits = [e for e in edits if policy.authorised(e)]
        self.differences: list[dict[str, Any]] = []

    def on_page(self, page: int, regex_class: Optional[str] = None,
                categories: Optional[set[str]] = None,
                stage: Optional[str] = None) -> list[LoggedEdit]:
        return [
            e for e in self.edits
            if e.page == page
            and (stage is None or e.stage == stage)
            and (regex_class is None or e.regex_class == regex_class)
            and (categories is None or e.category in categories)
        ]

    def finding(self, category: str, code: str, **detail: Any) -> None:
        self.differences.append({"category": category, **detail, "status": "finding",
                                 "code": code})

    def explained(self, category: str, code: str, edits: Sequence[LoggedEdit],
                  **detail: Any) -> None:
        self.differences.append({"category": category, **detail, "status": "explained",
                                 "code": code, "explanation": _explanation(edits)})

    def by_edit_on_page(self, category: str, code: str, page: int, **detail: Any) -> None:
        """Explained by an authorised A2 edit on *page*, else a finding.

        A2 only, because A4 writes data cells and never a heading or a header
        row. The page is the finest location the inventory gives a heading or
        a header, so the explanation is page-level (see the module docstring).
        """
        edits = self.on_page(page, stage="A2")
        if edits:
            self.explained(category, code, edits, page=page, **detail)
        else:
            self.finding(category, f"{code}_without_edit", page=page, **detail)


# --------------------------------------------------------------------------- #
# The categories
# --------------------------------------------------------------------------- #


def _page_count(ref: dict[str, Any], der: dict[str, Any], out: _Report) -> None:
    if ref["pages"] != der["pages"]:
        out.finding("page_count", "page_count_changed", reference=ref["pages"],
                    derivative=der["pages"])


def _headings(ref: dict[str, Any], der: dict[str, Any], out: _Report) -> None:
    mine, theirs = ref["heading_candidates"], der["heading_candidates"]
    if len(mine) != len(theirs):
        out.finding("headings", "heading_count_changed", reference=len(mine),
                    derivative=len(theirs))
    for index, (a, b) in enumerate(zip(mine, theirs)):
        where = {"index": index,
                 "reference": {"marker": a["marker"], "page": a["page"]},
                 "derivative": {"marker": b["marker"], "page": b["page"]}}
        if (a["marker"], a["page"]) != (b["marker"], b["page"]):
            out.finding("headings", "heading_moved", **where)
        elif a["text"] != b["text"]:
            out.by_edit_on_page("headings", "heading_text_changed", int(a["page"]), **where)


_SHAPE = ("page", "rows", "cols", "rows_parsed")


def _tables(ref: dict[str, Any], der: dict[str, Any], out: _Report) -> None:
    mine, theirs = ref["tables"]["per_table"], der["tables"]["per_table"]
    if len(mine) != len(theirs):
        out.finding("tables", "table_count_changed", reference=len(mine),
                    derivative=len(theirs))
    for index, (a, b) in enumerate(zip(mine, theirs)):
        shape_a = {k: a[k] for k in _SHAPE}
        shape_b = {k: b[k] for k in _SHAPE}
        if shape_a != shape_b:
            out.finding("tables", "table_shape_changed", index=index, reference=shape_a,
                        derivative=shape_b)
        elif a["header"] != b["header"]:
            out.by_edit_on_page("tables", "table_header_changed", int(a["page"]), index=index)


def _point_sizes(ref: dict[str, Any], der: dict[str, Any], out: _Report) -> None:
    body_a = (ref["point_sizes"]["largest_share"] or {}).get("size")
    body_b = (der["point_sizes"]["largest_share"] or {}).get("size")
    if body_a != body_b:
        out.finding("point_sizes", "body_size_changed", reference=body_a, derivative=body_b)
    sizes_a = ref["point_sizes"]["distribution"]
    sizes_b = der["point_sizes"]["distribution"]
    for size in sorted(set(sizes_b) - set(sizes_a), key=float):
        out.finding("point_sizes", "size_absent_from_reference", size=size, reference=0,
                    derivative=sizes_b[size])
    for size in sorted(set(sizes_a) - set(sizes_b), key=float):
        out.finding("point_sizes", "size_absent_from_derivative", size=size,
                    reference=sizes_a[size], derivative=0)


def _citation_pages(inventory: dict[str, Any], which: str) -> dict[int, dict[str, int]]:
    rows = inventory["citation_markers"].get("per_page")
    if rows is None:
        raise FidelityRefused(
            f"the {which} inventory carries no per-page citation counts, so marker positions "
            f"cannot be compared. Re-measure it with the current dry import."
        )
    return {int(row["page"]): dict(row["counts"]) for row in rows}


def _citations(ref: dict[str, Any], der: dict[str, Any], out: _Report) -> None:
    mine = _citation_pages(ref, "reference")
    theirs = _citation_pages(der, "derivative")
    classes = [name for name, _ in di.CITATION_PATTERNS]
    for page in sorted(set(mine) | set(theirs)):
        a, b = mine.get(page, {}), theirs.get(page, {})
        delta = {c: b.get(c, 0) - a.get(c, 0) for c in classes}
        neutral_edits = out.on_page(page, categories=out.policy.neutral)
        lost = sum(-delta[c] for c in MARKER_CLASSES if delta.get(c, 0) < 0)
        gain = delta.get(NEUTRAL_CLASS, 0)
        # The policy keeps the count: each lost marker has exactly one neutral
        # marker in its place on the same page.
        markers_replaced = 0 < lost == gain and lost <= len(neutral_edits)
        for cls in classes:
            if not delta[cls]:
                continue
            where = {"page": page, "marker_class": cls, "reference": a.get(cls, 0),
                     "derivative": b.get(cls, 0)}
            if cls in IDENTIFIER_CLASSES and delta[cls] < 0:
                edits = out.on_page(page, regex_class=cls)
                if len(edits) >= -delta[cls]:
                    out.explained("citation_markers", "identifier_removed", edits, **where)
                else:
                    out.finding("citation_markers", "citation_removed_without_edit", **where)
            elif cls in MARKER_CLASSES and delta[cls] < 0:
                if markers_replaced:
                    out.explained("citation_markers", "marker_replaced_by_neutral_marker",
                                  neutral_edits, **where)
                else:
                    out.finding("citation_markers", "citation_marker_lost", **where)
            elif cls == NEUTRAL_CLASS and lost and markers_replaced:
                out.explained("citation_markers", "marker_replaced_by_neutral_marker",
                              neutral_edits, **where)
            elif cls == NEUTRAL_CLASS and not lost and 0 < gain <= len(neutral_edits):
                out.explained("citation_markers", "neutral_marker_added", neutral_edits, **where)
            elif cls == NEUTRAL_CLASS and gain > 0:
                out.finding("citation_markers", "neutral_marker_without_edit", **where)
            elif delta[cls] > 0:
                out.finding("citation_markers", "citation_added", **where)
            else:
                out.finding("citation_markers", "citation_marker_lost", **where)


# --------------------------------------------------------------------------- #
# Figures
# --------------------------------------------------------------------------- #


def review_entries(review: Optional[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """The figure review's entries by page. Refuses a structurally malformed review."""
    if review is None:
        return {}
    pages = review.get("pages")
    if not isinstance(pages, list):
        raise FidelityRefused("the figure review carries no 'pages' list")
    entries: dict[int, dict[str, Any]] = {}
    for entry in pages:
        page = entry.get("page") if isinstance(entry, dict) else None
        if not isinstance(page, int) or isinstance(page, bool) or page < 1:
            raise FidelityRefused("a figure review entry does not name a page number")
        if page in entries:
            raise FidelityRefused(f"the figure review names page {page} twice")
        entries[page] = entry
    return entries


def _graphics(inventory: dict[str, Any]) -> dict[int, dict[str, int]]:
    return {
        int(row["page"]): {"images": int(row["images"]), "drawings": int(row["drawings"])}
        for row in inventory["per_page"]
    }


def _figure_verdict(entry: Optional[dict[str, Any]], counts_equal: bool,
                    policy: _Policy) -> dict[str, Any]:
    """The status of one graphical page under its review entry."""
    if entry is None:
        return {"status": "finding", "code": "figure_not_looked_at"}
    verdict, basis = entry.get("verdict"), entry.get("basis")
    if verdict not in FIGURE_VERDICTS:
        return {"status": "finding", "code": "unknown_verdict"}
    if not basis or not entry.get("reviewed_by") or not entry.get("reviewed_on"):
        return {"status": "finding", "code": "verdict_without_attestation"}
    if basis not in di.ACCEPTANCE_BASES:
        return {"status": "finding", "code": "unknown_basis"}
    if verdict == "lost":
        return {"status": "finding", "code": "figure_lost"}
    if basis in di.MEASUREMENT_ONLY_BASES:
        return {"status": "finding", "code": "measurement_basis_not_proof"}
    if verdict == "preserved":
        if counts_equal:
            return {"status": "preserved"}
        return {"status": "finding", "code": "preserved_but_counts_changed"}
    action = _ACTIONS[verdict]
    permitting = sorted(c for c, actions in policy.figure_actions.items() if action in actions)
    if not permitting:
        return {"status": "finding", "code": "action_not_permitted"}
    return {"status": "explained", "explanation": {"categories": permitting, "action": action}}


def _figures(ref: dict[str, Any], der: dict[str, Any], review: Optional[dict[str, Any]],
             out: _Report) -> list[dict[str, Any]]:
    for name in _FIGURE_TOTALS:
        if ref["figures"][name] != der["figures"][name]:
            out.finding("figures", f"{name}_changed", reference=ref["figures"][name],
                        derivative=der["figures"][name])
    mine, theirs = _graphics(ref), _graphics(der)
    none = {"images": 0, "drawings": 0}
    entries = review_entries(review)
    graphical = sorted(
        page for page in set(mine) | set(theirs)
        if any(mine.get(page, none).values()) or any(theirs.get(page, none).values())
    )
    figures: list[dict[str, Any]] = []
    for page in graphical:
        a, b = mine.get(page, none), theirs.get(page, none)
        entry = entries.get(page)
        figures.append({
            "page": page,
            "reference": a,
            "derivative": b,
            "counts_equal": a == b,
            "review": None if entry is None else
            {"verdict": entry.get("verdict"), "basis": entry.get("basis")},
            **_figure_verdict(entry, a == b, out.policy),
        })
    for page in sorted(set(entries) - set(graphical)):
        figures.append({"page": page, "reference": none, "derivative": none,
                        "counts_equal": True, "review": None, "status": "finding",
                        "code": "review_of_page_without_graphics"})
    return figures


# --------------------------------------------------------------------------- #
# The comparison
# --------------------------------------------------------------------------- #


def compare(
    reference: dict[str, Any],
    derivative: dict[str, Any],
    *,
    edits: Sequence[LoggedEdit],
    policy: LoadedPolicy,
    review: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """Every difference between two dry-import inventories, explained or a finding. Pure."""
    out = _Report(edits, _Policy(policy))
    _page_count(reference, derivative, out)
    _headings(reference, derivative, out)
    _tables(reference, derivative, out)
    figures = _figures(reference, derivative, review, out)
    _point_sizes(reference, derivative, out)
    _citations(reference, derivative, out)

    counts: dict[str, dict[str, int]] = {}
    for category in CATEGORIES:
        mine = [d for d in out.differences if d["category"] == category]
        items = mine + (figures if category == "figures" else [])
        changed = [f for f in figures if not f["counts_equal"]] if category == "figures" else []
        counts[category] = {
            "differences": len(mine) + len(changed),
            "explained": sum(1 for d in items if d["status"] == "explained"),
            "findings": sum(1 for d in items if d["status"] == "finding"),
        }
    failed = any(c["findings"] for c in counts.values())
    return {
        "verdict": "fail" if failed else "pass",
        "counts": counts,
        "differences": out.differences,
        "figures": figures,
    }


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #


class _Read(NamedTuple):
    """A JSON input, parsed from bytes that were hashed once."""

    record: dict[str, Any]
    sha256: str


def _parse(data: bytes, what: str) -> dict[str, Any]:
    try:
        record = json.loads(data)
    except ValueError as exc:
        raise FidelityRefused(f"{what} cannot be read as JSON: {type(exc).__name__}") from exc
    if not isinstance(record, dict):
        raise FidelityRefused(f"{what} is not a JSON object")
    return record


def _read(path: Path, what: str) -> _Read:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise FidelityRefused(f"{what} cannot be read: {type(exc).__name__}") from exc
    return _Read(_parse(data, what), _sha(data))


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class _Reference(NamedTuple):
    inventory: dict[str, Any]
    inventory_sha256: str
    source_sha256: str


def _reference(intake_record: Path, record: dict[str, Any]) -> _Reference:
    """The reference inventory the intake record bound, and the pinned input's hash."""
    if record.get("schema") != intake.SCHEMA:
        raise FidelityRefused(f"the intake record is not {intake.SCHEMA}")
    try:
        file, bound = str(record["reference_inventory"]["file"]), record["reference_inventory"]["sha256"]
        source = str(record["input"]["sha256"])
    except (KeyError, TypeError) as exc:
        raise FidelityRefused(f"the intake record is malformed: {exc!r}") from exc
    read = _read(intake_record.parent / file, "the reference inventory beside the intake record")
    if read.sha256 != bound:
        raise FidelityRefused(
            f"the reference inventory hashes to {read.sha256}, not the {bound} the intake record "
            f"bound. It is not the inventory A0 pinned."
        )
    return _Reference(read.record, read.sha256, source)


def _stage(log: dict[str, Any]) -> tuple[str, str, str, str, list[LoggedEdit]]:
    """``(stage, input sha, output sha, policy sha, edits)`` of one stage log."""
    stage = _STAGE_SCHEMAS.get(str(log.get("schema")))
    if stage is None:
        raise FidelityRefused(
            f"a stage log has schema {log.get('schema')!r}; A6 reads only "
            f"{sorted(_STAGE_SCHEMAS)}"
        )
    try:
        if stage == "A2":
            edits = [LoggedEdit("A2", int(e["edit"]), int(e["page"]), e["category"],
                                e["regex_class"]) for e in log["page_text"]["edits"]]
            return (stage, log["input"]["sha256"], log["output"]["sha256"],
                    log["policy_sha256"], edits)
        edits = [LoggedEdit("A4", int(e["edit"]), int(e["page"]), None, None)
                 for e in log["edits"]]
        return (stage, log["input"]["derivative_sha256"], log["output"]["sha256"],
                log["input"]["policy_sha256"], edits)
    except (KeyError, TypeError, ValueError) as exc:
        raise FidelityRefused(f"the {stage} stage log is malformed: {exc!r}") from exc


def _chain(logs: Sequence[dict[str, Any]], source_sha256: str, derivative_sha256: str,
           policy_sha256: str) -> tuple[list[LoggedEdit], list[dict[str, str]]]:
    """The edits of *logs*, refused unless they lead from the source to the derivative."""
    expected = source_sha256
    edits: list[LoggedEdit] = []
    bound: list[dict[str, str]] = []
    for log in logs:
        stage, given, made, policy, logged = _stage(log)
        if policy != policy_sha256:
            raise FidelityRefused(
                f"the {stage} log ran under policy {policy}, not the declared {policy_sha256}. "
                f"A change of policy re-opens acceptance; re-run the stages."
            )
        if given != expected:
            raise FidelityRefused(
                f"the stage chain breaks at {stage}: it edited {given}, but the previous link "
                f"produced {expected}"
            )
        expected = made
        edits += logged
        bound.append({"stage": stage, "output_sha256": made})
    if expected != derivative_sha256:
        raise FidelityRefused(
            f"the stage chain ends at {expected}, not at the derivative {derivative_sha256}. "
            f"Every edit that made the derivative must be logged."
        )
    return edits, bound


def _review(record: dict[str, Any], derivative_sha256: str) -> dict[str, Any]:
    if record.get("schema") != REVIEW_SCHEMA or record.get("record_type") != REVIEW_RECORD_TYPE:
        raise FidelityRefused(f"the figure review is not {REVIEW_SCHEMA}")
    if record.get("derivative_sha256") != derivative_sha256:
        raise FidelityRefused(
            "the figure review was made of another derivative. A figure is looked at in the "
            "document being accepted."
        )
    review_entries(record)
    return record


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #


def fidelity(
    *,
    derivative: Path,
    derivative_sha256: str,
    intake_record: Path,
    policy: LoadedPolicy,
    policy_sha256: str,
    stage_logs: Sequence[Path],
    figure_review: Optional[Path],
    out_dir: Path,
) -> FidelityResult:
    """Measure *derivative*, compare it with the A0 reference inventory and write the report.

    *derivative* must hash to *derivative_sha256*, taken from the last stage's
    record. *stage_logs* are the logs of every stage that edited the document,
    in order: the chain from the intake's pinned input to the derivative must
    be unbroken. A report with findings is a result, not a refusal. A re-run
    that would write the same files is a no-op; one that would write different
    files is refused.
    """
    import pymupdf

    derivative = intake.require_private(derivative, "the derivative to compare")
    intake_record = intake.require_private(intake_record, "the intake record")
    logs = [intake.require_private(p, "a stage log") for p in stage_logs]
    review_path = (None if figure_review is None
                   else intake.require_private(figure_review, "the figure review"))
    out_dir = intake.require_private(out_dir, "the fidelity directory")
    intake.pin(derivative, derivative_sha256, "the derivative")
    require_hash(policy, policy_sha256)

    intake_read = _read(intake_record, "the intake record")
    reference = _reference(intake_record, intake_read.record)
    log_reads = [_read(p, "a stage log") for p in logs]
    edits, bound = _chain([r.record for r in log_reads], reference.source_sha256,
                          derivative_sha256, policy.sha256)
    review_read = None if review_path is None else _read(review_path, "the figure review")
    review = None if review_read is None else _review(review_read.record, derivative_sha256)

    measured = di.measure(derivative)
    inventory_bytes = canonical_json_bytes(measured)
    result = compare(reference.inventory, measured, edits=edits, policy=policy, review=review)

    record = {
        "schema": SCHEMA,
        "record_type": RECORD_TYPE,
        "stage": "A6",
        "purpose": (
            "The structural fidelity of a derivative: every measured difference from the A0 "
            "reference inventory, each explained by an edit the policy authorises or reported "
            "as a finding. Any finding fails the derivative."
        ),
        "input": {
            "derivative_sha256": derivative_sha256,
            "derivative_inventory_sha256": _sha(inventory_bytes),
            "reference_inventory_sha256": reference.inventory_sha256,
            "intake_record_sha256": intake_read.sha256,
            "stage_logs": [
                {**link, "log_sha256": read.sha256} for link, read in zip(bound, log_reads)
            ],
            "figure_review_sha256": None if review_read is None else review_read.sha256,
        },
        "policy_sha256": policy.sha256,
        "compared": list(CATEGORIES),
        "not_compared": list(NOT_COMPARED),
        "rule": di.GRAPHICAL_PROOF_STATEMENT,
        **result,
        "replay": {
            "rule": "Same derivative, same reference inventory, same stage logs, same figure "
                    "review and same policy give a byte-equal report.",
            "environment": {"pymupdf": pymupdf.VersionBind},
        },
        "privacy": {
            "declared_status": "Confirmed",
            "claim": (
                "This report records categories, pages, counts, marker classes, point sizes, "
                "codes and edit ids. It quotes no heading, no table header and no other text. "
                "The derivative inventory beside it quotes headings and stays private."
            ),
            "basis": "Every path this comparison read or wrote was refused if it resolved "
                     "inside the repository.",
        },
    }
    files = {
        DERIVATIVE_INVENTORY_FILE: inventory_bytes,
        REPORT_FILE: canonical_json_bytes(record),
    }
    for name, data in files.items():
        target = out_dir / name
        if target.exists() and target.read_bytes() != data:
            raise FidelityRefused(
                f"{out_dir.name} already holds a fidelity report that differs from this one "
                f"({name}). A written report is never overwritten; compare into a new directory."
            )
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        if not (out_dir / name).exists():
            atomic_write_text(data.decode("utf-8"), out_dir / name)
    return FidelityResult(
        report=out_dir / REPORT_FILE,
        derivative_inventory=out_dir / DERIVATIVE_INVENTORY_FILE,
        passed=result["verdict"] == "pass",
        counts=result["counts"],
    )
