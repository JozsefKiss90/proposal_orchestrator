"""
Stage-1 annotated Part B draft renderer — deterministic, Claude-free
(plans/partb_final_drafting_strategy_2026-09-03.md §3).

Reads the run-03 Tier 5 section artifacts, the run's
``drafting_review_status.json`` and the hand-authored anchor map
(``plans/reports/partb_draft_anchor_map_2026-09.json``), and renders the
unbounded annotated draft ``.docx``:

  * every content paragraph carries its ``[<sub-section>-¶<n>]`` anchor prefix
    (the established draft ¶-numbering scheme; sentences are referenced
    positionally as s1, s2, … in the handout — they are not stamped in-text);
  * the three draft-resolvable items are resolved in place — the A-11
    numbering-gap note, the A-8 career-KPI naming (both texts fixed in the
    anchor map, grounded in Tier 4), and the A-5 task-loading table derived
    strictly from ``gantt.json`` (task activity counts only; the Gantt carries
    no per-task effort, so a per-month person-month split would be an invented
    fact, §13.3);
  * every unresolved revision action gets a highlighted ``[A-x]`` marker run at
    each mapped anchor plus a native Word comment carrying the action
    description, the question for the researcher and the proposed fallback —
    one comment per anchor (plan §3 step 4).

Fail-closed anchoring: every anchor and insertion carries a ``match``
substring that must be present in the mapped paragraph of the *current*
section artifacts; any mismatch raises ``AnnotationError`` before anything is
written, so a regenerated draft can never be silently mis-annotated.

Stage-1 verification (plan §3 step 6) runs before the file is written: all
unresolved action ids annotated, the A-7/A-12 resolved-content spot-checks,
and the run-03 supervisor-spine check against Tier 3 ``roles.json``.

Determinism: the output is a pure function of its declared inputs — comment
timestamps come from the anchor map, never the wall clock — so two renders
from the same inputs produce identical document and comment XML (the .docx
zip container itself carries entry mtimes; determinism is at the XML-part
level, as in ``runner/graph_determinism_check.py``).

This is a plans-layer drafting utility, not a manifest-bound runtime
component: it writes only the dated annotated deliverable under
``final_exports/`` and never touches Tier 1–4 state.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, NamedTuple, Optional

_REPO_ROOT_FOR_IMPORT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT_FOR_IMPORT))

from runner.atomic_write import atomic_write_via  # noqa: E402
from runner.docx_exporter import (  # noqa: E402  (needs repo root on sys.path)
    FINAL_EXPORTS_REL,
    _read_optional_json,
    _resolve_section_paths,
    split_content_blocks,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ANCHOR_MAP_REL: str = "plans/reports/partb_draft_anchor_map_2026-09.json"
REVIEW_STATUS_REL: str = (
    "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/"
    "drafting_review_status.json"
)
GANTT_REL: str = (
    "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/"
    "gantt.json"
)
WP_STRUCTURE_REL: str = (
    "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/"
    "wp_structure.json"
)
IMPACT_ARCHITECTURE_REL: str = (
    "docs/tier4_orchestration_state/phase_outputs/phase5_impact_architecture/"
    "impact_architecture.json"
)
ROLES_REL: str = "docs/tier3_project_instantiation/consortium/roles.json"

DEFAULT_OUTPUT_NAME: str = (
    "FIELDWISE_Part_B_draft_run-03_2026-09-04_annotated.docx"
)
VERIFICATION_REPORT_REL: str = (
    "plans/reports/partb_stage1_verification_2026-09.json"
)

#: Work packages whose concurrency the A-5 view demonstrates (the review
#: finding names the WP1/WP3/WP4 overlap).
_OVERLAP_WPS: tuple[str, ...] = ("WP1", "WP3", "WP4")

#: The closed set of insertion types the renderer implements.  Validation
#: rejects anything else fail-closed — an unknown type must never be
#: silently skipped at render time.
_INSERTION_TYPES: frozenset[str] = frozenset(
    {"paragraph_after", "sentence_after_match", "effort_loading_table_after"}
)

_COMMENT_AUTHOR: str = "Stage-1 annotator"
_COMMENT_INITIALS: str = "S1"

_DOCUMENT_TITLE: str = "Proposal Part B — Stage-1 annotated draft (run-03)"

#: A-7 / A-12 are resolved actions whose resolving content the draft must
#: PRESERVE (plan §2); these substrings pin that content in the current
#: section artifacts (wording verified against revision_log L-7 / L-12).
_SPOT_CHECKS: dict[str, tuple[str, str]] = {
    "A-7": ("1.4", "DrR - Digital Agronomist"),
    "A-12": ("3.2", "registration is a submission-time action"),
}


class AnnotationError(Exception):
    """Raised fail-closed when anchoring, inputs, or verification fail."""


# ---------------------------------------------------------------------------
# Inputs
# ---------------------------------------------------------------------------


class Inputs(NamedTuple):
    """All declared inputs, resolved from disk."""

    sections: list[dict[str, Any]]  # ordered section artifacts (Part B order)
    blocks: dict[str, list[str]]  # sub_section_id -> ¶ blocks
    anchor_map: dict[str, Any]
    review_status: dict[str, Any]
    gantt: dict[str, Any]
    wp_structure: dict[str, Any]
    impact_architecture: dict[str, Any]
    roles: dict[str, Any]


class CommentRecord(NamedTuple):
    action_id: str
    text: str


class RenderResult(NamedTuple):
    output_path: Path
    comments: list[CommentRecord]
    verification: dict[str, Any]
    verification_report_path: Optional[Path] = None


def _read_required_json(repo_root: Path, rel: str) -> dict[str, Any]:
    data = _read_optional_json(repo_root / rel)
    if data is None:
        raise AnnotationError(f"required input missing or unreadable: {rel}")
    return data


def load_inputs(repo_root: Path) -> Inputs:
    """Resolve every declared input from disk, fail-closed."""
    section_paths = _resolve_section_paths(repo_root)
    if not section_paths:
        raise AnnotationError("no section artifacts found to annotate")
    sections: list[dict[str, Any]] = []
    blocks: dict[str, list[str]] = {}
    for path in section_paths:
        section = _read_optional_json(path)
        if section is None:
            raise AnnotationError(f"unreadable section artifact: {path}")
        sections.append(section)
        for sub in section.get("sub_sections", []):
            sid = sub.get("sub_section_id")
            content = sub.get("content")
            if isinstance(sid, str) and isinstance(content, str):
                blocks[sid] = split_content_blocks(content)
    return Inputs(
        sections=sections,
        blocks=blocks,
        anchor_map=_read_required_json(repo_root, ANCHOR_MAP_REL),
        review_status=_read_required_json(repo_root, REVIEW_STATUS_REL),
        gantt=_read_required_json(repo_root, GANTT_REL),
        wp_structure=_read_required_json(repo_root, WP_STRUCTURE_REL),
        impact_architecture=_read_required_json(
            repo_root, IMPACT_ARCHITECTURE_REL
        ),
        roles=_read_required_json(repo_root, ROLES_REL),
    )


# ---------------------------------------------------------------------------
# Fail-closed anchor validation
# ---------------------------------------------------------------------------


def _resolve_anchor_block(
    inputs: Inputs, where: str, sub_section_id: str, paragraph: Any, match: str
) -> str:
    """Return the anchored block text, raising ``AnnotationError`` on any
    mismatch between the map and the current section artifacts."""
    section_blocks = inputs.blocks.get(sub_section_id)
    if section_blocks is None:
        raise AnnotationError(
            f"{where}: unknown sub-section {sub_section_id!r}"
        )
    if not isinstance(paragraph, int) or not (
        1 <= paragraph <= len(section_blocks)
    ):
        raise AnnotationError(
            f"{where}: paragraph {paragraph!r} out of range for "
            f"{sub_section_id} (1..{len(section_blocks)})"
        )
    block = section_blocks[paragraph - 1]
    if match not in block:
        raise AnnotationError(
            f"{where}: match not found in {sub_section_id}-¶{paragraph}: "
            f"{match!r}"
        )
    return block


def validate_anchors(inputs: Inputs) -> None:
    """Validate the anchor map against the current section artifacts and the
    run's review status.  Raises ``AnnotationError`` on the first violation."""
    unresolved = {
        a["action_id"]
        for a in inputs.review_status.get("revision_actions", [])
        if a.get("status") == "unresolved"
    }
    mapped = {a["action_id"] for a in inputs.anchor_map.get("actions", [])}
    if mapped != unresolved:
        raise AnnotationError(
            "anchor map does not cover exactly the unresolved actions: "
            f"missing={sorted(unresolved - mapped)}, "
            f"extra={sorted(mapped - unresolved)}"
        )
    for action in inputs.anchor_map["actions"]:
        action_id = action["action_id"]
        if not action.get("anchors"):
            raise AnnotationError(f"{action_id}: no anchors")
        for anchor in action["anchors"]:
            _resolve_anchor_block(
                inputs,
                f"{action_id} anchor",
                anchor.get("sub_section_id"),
                anchor.get("paragraph"),
                anchor.get("match", ""),
            )
    splice_paragraphs: set[tuple[str, int]] = set()
    for ins in inputs.anchor_map.get("insertions", []):
        where = f"{ins.get('action_id')} insertion"
        if ins.get("type") not in _INSERTION_TYPES:
            raise AnnotationError(
                f"{where}: unknown insertion type {ins.get('type')!r} "
                f"(renderer implements {sorted(_INSERTION_TYPES)})"
            )
        block = _resolve_anchor_block(
            inputs,
            where,
            ins.get("sub_section_id"),
            ins.get("paragraph"),
            ins.get("match", "") or "",
        )
        if ins["type"] == "sentence_after_match":
            match = ins.get("match", "")
            if not match:
                raise AnnotationError(f"{where}: sentence_after_match "
                                      "requires a match")
            if _sentence_end(block, match) is None:
                raise AnnotationError(
                    f"{where}: match is not at a sentence boundary"
                )
            key = (ins["sub_section_id"], ins["paragraph"])
            if key in splice_paragraphs:
                raise AnnotationError(
                    f"{where}: more than one sentence_after_match insertion "
                    f"targets {key[0]}-¶{key[1]}"
                )
            splice_paragraphs.add(key)
    _validate_a8_grounding(inputs)


def _sentence_end(block: str, match: str) -> Optional[int]:
    """Index just past the closing period of the sentence containing *match*,
    or ``None`` when the match is not at a sentence boundary.  Single source
    of the boundary rule for validation and rendering."""
    end = block.index(match) + len(match)
    tail = block[end : end + 2]
    if "." not in tail:
        return None
    return end + tail.index(".") + 1


def _validate_a8_grounding(inputs: Inputs) -> None:
    """The A-8 insertion names the Tier 4 career KPI — re-verify that claim
    against ``impact_architecture.json`` at render time (plan §2: 'verify
    first'), so a hand-edited map can never push an ungrounded KPI claim into
    a Tier 5 export (§11.4, §13.10)."""
    a8 = [
        i
        for i in inputs.anchor_map.get("insertions", [])
        if i.get("action_id") == "A-8"
    ]
    if not a8:
        return
    text = a8[0].get("text", "")
    kpi_ids = re.findall(r"\bK\d+\b", text)
    if not kpi_ids:
        raise AnnotationError("A-8 insertion names no KPI id")
    kpis = {k.get("kpi_id"): k for k in inputs.impact_architecture.get("kpis", [])}
    for kpi_id in kpi_ids:
        kpi = kpis.get(kpi_id)
        if kpi is None:
            raise AnnotationError(
                f"A-8 insertion cites {kpi_id}, absent from the Tier 4 KPI set"
            )
        deliverable = kpi.get("traceable_to_deliverable", "")
        if deliverable and deliverable not in text:
            raise AnnotationError(
                f"A-8 insertion omits {kpi_id}'s deliverable {deliverable!r}"
            )
        review_months = re.findall(r"M\d+", kpi.get("target", ""))
        for month in review_months:
            if month not in text:
                raise AnnotationError(
                    f"A-8 insertion omits {kpi_id} target month {month}"
                )


# ---------------------------------------------------------------------------
# A-5 derivation — strictly from gantt.json
# ---------------------------------------------------------------------------


def derive_task_loading(
    gantt: dict[str, Any]
) -> tuple[list[int], list[tuple[str, list[int]]]]:
    """Derive the WP1/WP3/WP4 overlap task-loading view from the Tier 4 Gantt.

    Returns ``(months, rows)`` where *months* are the months in which all
    three work packages have at least one active task, and each row is
    ``(wp_id, [active-task count per month])``.  Pure lookup over
    ``tasks[].start_month..end_month`` — deliberately *not* an effort
    derivation: the Gantt carries no per-task effort, so a per-month
    person-month split would be an invented fact (§13.3).
    """
    tasks = [
        t
        for t in gantt.get("tasks", [])
        if t.get("wp_id") in _OVERLAP_WPS
    ]
    if not tasks:
        raise AnnotationError("gantt.json has no tasks for the A-5 view")

    def active(wp: str, month: int) -> int:
        return sum(
            1
            for t in tasks
            if t["wp_id"] == wp and t["start_month"] <= month <= t["end_month"]
        )

    horizon = max(t["end_month"] for t in tasks)
    months = [
        m
        for m in range(1, horizon + 1)
        if all(active(wp, m) >= 1 for wp in _OVERLAP_WPS)
    ]
    if not months:
        raise AnnotationError("no WP1/WP3/WP4 overlap months in gantt.json")
    rows = [(wp, [active(wp, m) for m in months]) for wp in _OVERLAP_WPS]
    return months, rows


def _task_loading_legend(
    gantt: dict[str, Any], wp_structure: dict[str, Any], months: list[int]
) -> str:
    """One legend line per overlap WP — its Tier 4 title (wp_structure.json)
    and its window-active tasks with their Gantt month spans (file order)."""
    titles = {
        wp.get("wp_id"): wp.get("title", "")
        for wp in wp_structure.get("work_packages", [])
    }
    lo, hi = months[0], months[-1]
    parts: list[str] = []
    for wp in _OVERLAP_WPS:
        spans = [
            f"{t['task_id']} (M{t['start_month']}–M{t['end_month']})"
            for t in gantt.get("tasks", [])
            if t.get("wp_id") == wp
            and t["start_month"] <= hi
            and t["end_month"] >= lo
        ]
        label = f"{wp} ({titles[wp]})" if titles.get(wp) else wp
        parts.append(f"{label}: " + ", ".join(spans))
    return "Window-active tasks — " + "; ".join(parts) + "."


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _add_text_runs(paragraph: Any, text: str) -> None:
    """Add *text* verbatim, preserving intra-block line breaks (exporter
    convention)."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        run = paragraph.add_run(line)
        if i < len(lines) - 1:
            run.add_break()


def _comment_text(
    action: dict[str, Any], description: str
) -> str:
    parts = [f"{action['action_id']} ({action['kind']}): {description}"]
    resolution = action.get("resolution")
    if resolution:
        parts.insert(
            0,
            f"RESOLVED ({resolution['resolved_on']}, OD round-3 answer): "
            f"{resolution['answer_summary']}",
        )
        parts.insert(1, f"Applied: {resolution['applied']}")
    if action.get("resolution_note"):
        parts.append(f"Resolution note: {action['resolution_note']}")
    if action.get("question"):
        parts.append(f"Question: {action['question']}")
    if action.get("fallback"):
        parts.append(f"Fallback: {action['fallback']}")
    if action.get("owner"):
        parts.append(f"Owner of the answer: {action['owner']}")
    return "\n\n".join(parts)


def _normalize_comment_dates(doc: Any, timestamp: str) -> None:
    """Stamp every comment with the map's fixed timestamp (determinism —
    the python-docx API stamps the wall clock, which would break byte-equal
    replay of the comments part)."""
    from docx.oxml.ns import qn

    for comment in doc.comments:
        comment._comment_elm.set(qn("w:date"), timestamp)


def build_annotated_draft(
    repo_root: Path,
    *,
    output_path: Optional[Path] = None,
    verification_report_path: Optional[Path] = None,
) -> RenderResult:
    """Render the Stage-1 annotated draft.  Validates anchors and runs the
    Stage-1 verification before writing; raises ``AnnotationError`` (writing
    nothing) on any failure."""
    try:
        from docx import Document
        from docx.enum.text import WD_COLOR_INDEX
        from docx.shared import RGBColor
    except ImportError as exc:  # pragma: no cover - dependency guard
        raise AnnotationError(
            "python-docx >= 1.2.0 is required (native Word comments)"
        ) from exc

    inputs = load_inputs(repo_root)
    validate_anchors(inputs)

    if output_path is None:
        output_path = repo_root / FINAL_EXPORTS_REL / DEFAULT_OUTPUT_NAME

    descriptions = {
        a["action_id"]: a["description"]
        for a in inputs.review_status.get("revision_actions", [])
    }

    # anchor/insertion lookup tables keyed by (sub_section_id, paragraph)
    anchors_at: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for action in inputs.anchor_map["actions"]:
        for anchor in action["anchors"]:
            key = (anchor["sub_section_id"], anchor["paragraph"])
            anchors_at.setdefault(key, []).append(action)
    insertions_at: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for ins in inputs.anchor_map.get("insertions", []):
        key = (ins["sub_section_id"], ins["paragraph"])
        insertions_at.setdefault(key, []).append(ins)

    doc = Document()
    doc.add_heading(_DOCUMENT_TITLE, level=0)
    prov = doc.add_paragraph()
    prov_run = prov.add_run(
        "Annotated working draft (unbounded) generated per "
        "plans/partb_final_drafting_strategy_2026-09-03.md §3, "
        f"{inputs.anchor_map['date']}, from the run "
        f"{inputs.anchor_map['run_id']} section artifacts. Paragraphs carry "
        "[<sub-section>-¶<n>] anchors (sentences are referenced positionally "
        "as s1, s2, … within a ¶); highlighted [A-x] markers carry Word "
        "comments with the revision action, the question for the researcher "
        "and the proposed fallback; highlighted insertions are the "
        "draft-resolved items. All markup is stripped in the final "
        "submission form."
    )
    prov_run.italic = True

    comments: list[CommentRecord] = []

    def add_marker(paragraph: Any, action: dict[str, Any]) -> None:
        run = paragraph.add_run(f" [{action['action_id']}]")
        # a resolved action (Stage 3, OD round-3 answer applied) turns its
        # marker green; an open question stays yellow
        run.font.highlight_color = (
            WD_COLOR_INDEX.BRIGHT_GREEN
            if action.get("resolution")
            else WD_COLOR_INDEX.YELLOW
        )
        run.bold = True
        text = _comment_text(action, descriptions[action["action_id"]])
        doc.add_comment(
            runs=run,
            text=text,
            author=_COMMENT_AUTHOR,
            initials=_COMMENT_INITIALS,
        )
        comments.append(CommentRecord(action["action_id"], text))

    def add_insertion_paragraph(ins: dict[str, Any]) -> None:
        para = doc.add_paragraph()
        run = para.add_run(ins["text"])
        run.font.highlight_color = WD_COLOR_INDEX.BRIGHT_GREEN

    def add_effort_table(ins: dict[str, Any]) -> None:
        months, rows = derive_task_loading(inputs.gantt)
        caption = doc.add_paragraph()
        cap_run = caption.add_run(ins["caption"])
        cap_run.font.highlight_color = WD_COLOR_INDEX.BRIGHT_GREEN
        table = doc.add_table(rows=1 + len(rows), cols=1 + len(months))
        table.style = "Table Grid"
        header = table.rows[0].cells
        header[0].text = "Work package"
        for j, month in enumerate(months, start=1):
            header[j].text = f"M{month}"
        for i, (wp, counts) in enumerate(rows, start=1):
            cells = table.rows[i].cells
            cells[0].text = wp
            for j, count in enumerate(counts, start=1):
                cells[j].text = str(count)
        legend = doc.add_paragraph()
        leg_run = legend.add_run(
            _task_loading_legend(inputs.gantt, inputs.wp_structure, months)
        )
        leg_run.font.highlight_color = WD_COLOR_INDEX.BRIGHT_GREEN

    gray = RGBColor(0x80, 0x80, 0x80)

    for section in inputs.sections:
        criterion = section.get("criterion")
        if isinstance(criterion, str) and criterion.strip():
            doc.add_heading(criterion, level=1)
        for sub in section.get("sub_sections", []):
            sid = sub.get("sub_section_id")
            title = sub.get("title")
            heading_parts = [
                str(p) for p in (sid, title) if isinstance(p, str) and p.strip()
            ]
            if heading_parts:
                doc.add_heading(" ".join(heading_parts), level=2)
            if not isinstance(sid, str):
                continue
            for index, block in enumerate(inputs.blocks.get(sid, []), start=1):
                key = (sid, index)
                para = doc.add_paragraph()
                prefix = para.add_run(f"[{sid}-¶{index}] ")
                prefix.italic = True
                prefix.font.color.rgb = gray

                sentence_ins = [
                    i
                    for i in insertions_at.get(key, [])
                    if i["type"] == "sentence_after_match"
                ]
                # actions whose marker rides an in-paragraph insertion rather
                # than the paragraph end (one comment per anchor either way)
                inline_marked = {i["action_id"] for i in sentence_ins}

                if sentence_ins:
                    ins = sentence_ins[0]  # >1 per ¶ rejected in validation
                    end = _sentence_end(block, ins["match"])
                    assert end is not None  # guaranteed by validate_anchors
                    _add_text_runs(para, block[:end])
                    ins_run = para.add_run(ins["text"])
                    ins_run.font.highlight_color = WD_COLOR_INDEX.BRIGHT_GREEN
                    action = next(
                        a
                        for a in inputs.anchor_map["actions"]
                        if a["action_id"] == ins["action_id"]
                    )
                    add_marker(para, action)
                    _add_text_runs(para, block[end:])
                else:
                    _add_text_runs(para, block)

                for action in anchors_at.get(key, []):
                    if action["action_id"] in inline_marked:
                        continue
                    add_marker(para, action)

                for ins in insertions_at.get(key, []):
                    if ins["type"] == "paragraph_after":
                        add_insertion_paragraph(ins)
                    elif ins["type"] == "effort_loading_table_after":
                        add_effort_table(ins)

    _normalize_comment_dates(doc, inputs.anchor_map["comment_timestamp"])

    verification = _verify(inputs, comments)
    if not verification["passed"]:
        raise AnnotationError(
            "Stage-1 verification failed: "
            + "; ".join(verification["failures"])
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_via(output_path, doc.save, prefix="stage1_annotated_")

    # Persist the Stage-1 verification durably (§9.4 — a check that matters
    # for future interpretation must not live only in stdout).
    report_path = (
        verification_report_path
        if verification_report_path is not None
        else repo_root / VERIFICATION_REPORT_REL
    )
    report = {
        "schema_id": "plans.partb_stage1_verification.v1",
        "date": inputs.anchor_map["date"],
        "run_id": inputs.anchor_map["run_id"],
        "output": str(output_path.name),
        "comment_count": len(comments),
        **verification,
    }
    atomic_write_via(
        report_path,
        lambda p: Path(p).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        ),
        prefix="stage1_verification_",
    )
    return RenderResult(
        output_path=output_path,
        comments=comments,
        verification=verification,
        verification_report_path=report_path,
    )


# ---------------------------------------------------------------------------
# Stage-1 verification (plan §3 step 6)
# ---------------------------------------------------------------------------


def _role_identity(roles: dict[str, Any], token: str) -> str:
    for record in roles.get("roles", []):
        if record.get("role_token") == token:
            identity = record.get("identity", "")
            # strip the honorific so the check matches prose variants
            return re.sub(r"^(Prof\.|Dr\.)\s+", "", identity)
    raise AnnotationError(f"Tier 3 roles.json has no {token} record")


def _verify(
    inputs: Inputs, comments: list[CommentRecord]
) -> dict[str, Any]:
    failures: list[str] = []

    annotated = sorted({c.action_id for c in comments})
    expected = sorted(a["action_id"] for a in inputs.anchor_map["actions"])
    if annotated != expected:
        failures.append(
            f"annotated action ids {annotated} != mapped {expected}"
        )

    spot_checks: dict[str, bool] = {}
    for action_id, (sid, needle) in _SPOT_CHECKS.items():
        full = "\n\n".join(inputs.blocks.get(sid, []))
        ok = needle in full
        spot_checks[action_id] = ok
        if not ok:
            failures.append(
                f"{action_id} spot-check failed: {needle!r} not in {sid}"
            )

    # run-03 supervisor spine (Tier 3 roles.json is the authority, §9.3).
    # The supervision names must appear in 1.3 itself (not just anywhere),
    # every 'hosted by' clause must name the HUN-REN host and at least one
    # must exist (no vacuous pass), and no sentence may attribute
    # supervision to the superseded run-02 supervisor.
    all_text = "\n\n".join(
        "\n\n".join(blocks) for blocks in inputs.blocks.values()
    )
    supervision_text = "\n\n".join(inputs.blocks.get("1.3", []))
    spine_checks: dict[str, bool] = {}
    for token in ("SUPERVISOR", "CO_SUPERVISOR"):
        name = _role_identity(inputs.roles, token)
        spine_checks[token] = name in supervision_text
        if not spine_checks[token]:
            failures.append(f"spine: {token} identity {name!r} not in 1.3")
    hosted_by = re.findall(r"hosted by (?:the )?(\S+)", all_text)
    hosted_by_ok = bool(hosted_by) and all(
        h.startswith("HUN-REN") for h in hosted_by
    )
    spine_checks["HOSTED_BY_HUN_REN"] = hosted_by_ok
    if not hosted_by_ok:
        failures.append(
            "spine: no 'hosted by' clause, or one names a non-HUN-REN host"
        )
    superseded = re.search(
        r"supervis[a-z]*[^.]{0,160}Holl[oó]s|Holl[oó]s[^.]{0,160}supervis",
        all_text,
        re.IGNORECASE,
    )
    spine_checks["NO_SUPERSEDED_SUPERVISOR"] = superseded is None
    if superseded is not None:
        failures.append(
            "spine: a sentence attributes supervision to the superseded "
            f"run-02 supervisor: {superseded.group(0)[:120]!r}"
        )

    return {
        "passed": not failures,
        "failures": failures,
        "annotated_actions": annotated,
        "spot_checks": spot_checks,
        "spine_checks": spine_checks,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    import argparse

    from runner.paths import find_repo_root

    parser = argparse.ArgumentParser(
        prog="python tools/annotate_part_b_draft.py",
        description="Render the Stage-1 annotated Part B draft (.docx).",
    )
    parser.add_argument("--repo-root", default=None)
    parser.add_argument(
        "--output-name",
        default=DEFAULT_OUTPUT_NAME,
        help=f"File name under final_exports/ (default: {DEFAULT_OUTPUT_NAME})",
    )
    parser.add_argument(
        "--verification-report",
        default=None,
        help=(
            "Repo-relative path for the verification report (default: "
            f"{VERIFICATION_REPORT_REL})"
        ),
    )
    args = parser.parse_args(argv)

    repo_root = (
        Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
    )
    try:
        result = build_annotated_draft(
            repo_root,
            output_path=repo_root / FINAL_EXPORTS_REL / args.output_name,
            verification_report_path=(
                repo_root / args.verification_report
                if args.verification_report
                else None
            ),
        )
    except AnnotationError as exc:
        print(f"[ERROR] {exc}")
        return 1
    print(f"[stage1] Annotated draft written to {result.output_path}")
    print(
        f"[stage1] {len(result.comments)} comments across "
        f"{len(result.verification['annotated_actions'])} actions: "
        + ", ".join(result.verification["annotated_actions"])
    )
    print(
        "[stage1] verification passed: "
        f"spot_checks={result.verification['spot_checks']}, "
        f"spine_checks={result.verification['spine_checks']}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    sys.exit(main())
