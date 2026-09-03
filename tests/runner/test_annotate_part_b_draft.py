"""
Stage-1 annotated Part B draft — regression seam for ``tools/annotate_part_b_draft.py``
(plans/partb_final_drafting_strategy_2026-09-03.md §3).

Pins the load-bearing Stage-1 guarantees:

  * **fail-closed anchoring:** every anchor's ``match`` substring must be found in
    the mapped paragraph of the *current* section artifacts — a regenerated draft
    can never be silently mis-annotated (AnnotationError, no output written);
  * **coverage:** every unresolved revision action of ``drafting_review_status.json``
    is mapped, and every one appears in the rendered document as a highlighted
    ``[A-x]`` marker carrying a native Word comment (plan §3 step 6);
  * **no new facts:** the three draft-resolvable insertions are exactly the mapped
    ones (A-11 note, A-8 KPI naming from the Tier 4 KPI set, A-5 task-loading
    table derived strictly from gantt.json) — the table asserts task *activity*,
    never an invented per-month person-month split (§13.3);
  * **spine safety:** the rendered text names the run-03 supervisor spine from
    Tier 3 ``roles.json`` and never attributes hosting elsewhere; A-7/A-12
    resolved-content spot-checks pass;
  * **determinism (§17.5.3-class):** two renders from the same inputs produce
    identical document and comment XML (comment timestamps come from the map,
    not the wall clock).

These tests read the real repo artifacts read-only and write only under tmp_path.
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pytest

from tools.annotate_part_b_draft import (
    ANCHOR_MAP_REL,
    AnnotationError,
    DEFAULT_OUTPUT_NAME,
    REVIEW_STATUS_REL,
    build_annotated_draft,
    derive_task_loading,
    load_inputs,
    validate_anchors,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.skipif(
    not (REPO_ROOT / REVIEW_STATUS_REL).is_file(),
    reason="run-03 drafting_review_status.json not present",
)


@pytest.fixture(scope="module")
def inputs():
    return load_inputs(REPO_ROOT)


@pytest.fixture(scope="module")
def rendered(tmp_path_factory, inputs):
    tmp = tmp_path_factory.mktemp("stage1")
    return build_annotated_draft(
        REPO_ROOT,
        output_path=tmp / DEFAULT_OUTPUT_NAME,
        verification_report_path=tmp / "verification.json",
    )


def _docx_xml(path: Path, member: str) -> bytes:
    with zipfile.ZipFile(path) as z:
        return z.read(member)


def _document_text(path: Path) -> str:
    xml = _docx_xml(path, "word/document.xml").decode("utf-8")
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml))


# ---------------------------------------------------------------------------
# Anchor map ↔ review status coverage
# ---------------------------------------------------------------------------


class TestAnchorMapCoverage:
    def test_every_unresolved_action_is_mapped(self, inputs):
        unresolved = {
            a["action_id"]
            for a in inputs.review_status["revision_actions"]
            if a.get("status") == "unresolved"
        }
        mapped = {a["action_id"] for a in inputs.anchor_map["actions"]}
        assert unresolved == mapped

    def test_resolved_actions_are_not_annotated(self, inputs):
        resolved = {
            a["action_id"]
            for a in inputs.review_status["revision_actions"]
            if a.get("status") == "resolved"
        }
        mapped = {a["action_id"] for a in inputs.anchor_map["actions"]}
        assert not (resolved & mapped)

    def test_needs_input_actions_carry_question_and_fallback(self, inputs):
        for action in inputs.anchor_map["actions"]:
            if action["kind"] in ("needs_input", "split"):
                assert action["question"], action["action_id"]
                assert action["fallback"], action["action_id"]

    def test_a1_touches_both_sub_sections(self, inputs):
        a1 = next(
            a for a in inputs.anchor_map["actions"] if a["action_id"] == "A-1"
        )
        assert {an["sub_section_id"] for an in a1["anchors"]} == {"1.1", "1.2"}


# ---------------------------------------------------------------------------
# Fail-closed anchor validation
# ---------------------------------------------------------------------------


class TestValidateAnchors:
    def test_current_anchors_all_resolve(self, inputs):
        validate_anchors(inputs)  # must not raise

    def test_match_absent_from_paragraph_fails_closed(self, inputs):
        bad = json.loads(json.dumps(inputs.anchor_map))
        bad["actions"][0]["anchors"][0]["match"] = "NOT IN THE DRAFT 12345"
        with pytest.raises(AnnotationError):
            validate_anchors(inputs._replace(anchor_map=bad))

    def test_paragraph_index_out_of_range_fails_closed(self, inputs):
        bad = json.loads(json.dumps(inputs.anchor_map))
        bad["actions"][0]["anchors"][0]["paragraph"] = 999
        with pytest.raises(AnnotationError):
            validate_anchors(inputs._replace(anchor_map=bad))

    def test_unknown_sub_section_fails_closed(self, inputs):
        bad = json.loads(json.dumps(inputs.anchor_map))
        bad["actions"][0]["anchors"][0]["sub_section_id"] = "9.9"
        with pytest.raises(AnnotationError):
            validate_anchors(inputs._replace(anchor_map=bad))

    def test_unknown_insertion_type_fails_closed(self, inputs):
        """An insertion type the renderer does not implement must be rejected
        at validation, never silently skipped at render time."""
        bad = json.loads(json.dumps(inputs.anchor_map))
        bad["insertions"][0]["type"] = "not_a_renderer_type"
        with pytest.raises(AnnotationError, match="unknown insertion type"):
            validate_anchors(inputs._replace(anchor_map=bad))

    def test_a8_kpi_claim_reverified_against_tier4(self, inputs):
        """The A-8 insertion's KPI claim is re-verified against the Tier 4
        KPI set at render time — a map edit citing a nonexistent KPI or
        dropping a target month fails closed (§11.4, §13.10)."""
        bad = json.loads(json.dumps(inputs.anchor_map))
        for ins in bad["insertions"]:
            if ins["action_id"] == "A-8":
                ins["text"] = ins["text"].replace("K11", "K99")
        with pytest.raises(AnnotationError, match="K99"):
            validate_anchors(inputs._replace(anchor_map=bad))

        bad = json.loads(json.dumps(inputs.anchor_map))
        for ins in bad["insertions"]:
            if ins["action_id"] == "A-8":
                ins["text"] = ins["text"].replace("M18, ", "")
        with pytest.raises(AnnotationError, match="M18"):
            validate_anchors(inputs._replace(anchor_map=bad))


# ---------------------------------------------------------------------------
# A-5 effort-loading derivation (strictly from gantt.json)
# ---------------------------------------------------------------------------


class TestEffortLoading:
    def test_overlap_window_is_m4_to_m14(self, inputs):
        months, rows = derive_task_loading(inputs.gantt)
        assert months == list(range(4, 15))
        assert [r[0] for r in rows] == ["WP1", "WP3", "WP4"]

    def test_every_cell_counts_at_least_one_active_task(self, inputs):
        months, rows = derive_task_loading(inputs.gantt)
        for wp, counts in rows:
            assert len(counts) == len(months)
            assert all(c >= 1 for c in counts), wp

    def test_counts_match_gantt_recomputation(self, inputs):
        months, rows = derive_task_loading(inputs.gantt)
        for wp, counts in rows:
            for month, count in zip(months, counts):
                expected = sum(
                    1
                    for t in inputs.gantt["tasks"]
                    if t["wp_id"] == wp
                    and t["start_month"] <= month <= t["end_month"]
                )
                assert count == expected, (wp, month)


# ---------------------------------------------------------------------------
# Rendered document
# ---------------------------------------------------------------------------


class TestRenderedDraft:
    def test_output_written_at_requested_path(self, rendered):
        assert rendered.output_path.is_file()

    def test_all_unresolved_action_markers_present(self, rendered, inputs):
        text = _document_text(rendered.output_path)
        for action in inputs.anchor_map["actions"]:
            assert f"[{action['action_id']}]" in text, action["action_id"]

    def test_paragraph_anchors_present(self, rendered):
        text = _document_text(rendered.output_path)
        for anchor in ("[1.1-¶4]", "[1.2-¶6]", "[3.1-¶16]", "[2.1-¶2]"):
            assert anchor in text, anchor

    def test_one_comment_per_anchor(self, rendered, inputs):
        n_anchors = sum(len(a["anchors"]) for a in inputs.anchor_map["actions"])
        assert len(rendered.comments) == n_anchors

    def test_comment_carries_description_question_fallback(
        self, rendered, inputs
    ):
        by_action = {
            a["action_id"]: a
            for a in inputs.review_status["revision_actions"]
        }
        for comment in rendered.comments:
            action_id = comment.action_id
            assert by_action[action_id]["description"] in comment.text
            mapped = next(
                a
                for a in inputs.anchor_map["actions"]
                if a["action_id"] == action_id
            )
            if mapped["kind"] in ("needs_input", "split"):
                assert mapped["question"] in comment.text
                assert mapped["fallback"] in comment.text
            if mapped.get("resolution_note"):
                assert mapped["resolution_note"] in comment.text

    def test_a11_note_inserted(self, rendered):
        text = _document_text(rendered.output_path)
        assert "the former WP2 (model development) was merged into WP1" in text
        assert "deliberate, not an omission" in text

    def test_a8_kpi_named_from_tier4(self, rendered, inputs):
        text = _document_text(rendered.output_path)
        assert "That career KPI is K11" in text
        k11 = next(
            k for k in inputs.impact_architecture["kpis"] if k["kpi_id"] == "K11"
        )
        assert "M6, M14, M18, M24, M27" in k11["target"]

    def test_a5_table_present_with_derivation_flag(self, rendered):
        text = _document_text(rendered.output_path)
        assert "derived from Tier 4, no new fact" in text
        assert "No per-month person-month split is asserted" in text
        xml = _docx_xml(rendered.output_path, "word/document.xml").decode("utf-8")
        assert "<w:tbl>" in xml

    def test_no_person_month_numbers_in_table_cells(self, rendered):
        """The A-5 table asserts task activity only — integer counts, never
        person-month figures (which would be an invented fact, §13.3)."""
        xml = _docx_xml(rendered.output_path, "word/document.xml").decode("utf-8")
        tbl = xml[xml.index("<w:tbl>") : xml.index("</w:tbl>")]
        cells = re.findall(r"<w:t[^>]*>([^<]*)</w:t>", tbl)
        for cell in cells:
            if cell.startswith(("WP", "M", "Work")):
                continue
            assert re.fullmatch(r"\d+", cell), cell


# ---------------------------------------------------------------------------
# Stage-1 verification (plan §3 step 6)
# ---------------------------------------------------------------------------


class TestVerification:
    def test_verification_report_passes(self, rendered):
        assert rendered.verification["passed"] is True
        assert rendered.verification["failures"] == []

    def test_all_ten_action_ids_verified(self, rendered):
        assert sorted(rendered.verification["annotated_actions"]) == [
            "A-1",
            "A-10",
            "A-11",
            "A-2",
            "A-3",
            "A-4",
            "A-5",
            "A-6",
            "A-8",
            "A-9",
        ]

    def test_spine_names_from_tier3_roles(self, rendered, inputs):
        """The supervision names asserted in the draft are the Tier 3
        roles.json identities (run-03 spine), not hardcoded expectations."""
        import re as _re

        text = _document_text(rendered.output_path)
        by_token = {
            r["role_token"]: _re.sub(r"^(Prof\.|Dr\.)\s+", "", r["identity"])
            for r in inputs.roles["roles"]
            if r.get("role_token") in ("SUPERVISOR", "CO_SUPERVISOR")
        }
        assert by_token["SUPERVISOR"] in text
        assert by_token["CO_SUPERVISOR"] in text

    def test_verification_report_persisted(self, rendered, inputs):
        report = json.loads(
            rendered.verification_report_path.read_text(encoding="utf-8")
        )
        assert report["passed"] is True
        assert report["run_id"] == inputs.anchor_map["run_id"]
        assert report["spine_checks"]["NO_SUPERSEDED_SUPERVISOR"] is True

    def test_a7_a12_spot_checks_recorded(self, rendered):
        checks = rendered.verification["spot_checks"]
        assert checks["A-7"] is True
        assert checks["A-12"] is True


# ---------------------------------------------------------------------------
# Determinism — same inputs, identical document + comment XML
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_two_renders_are_xml_identical(self, tmp_path, rendered):
        again = build_annotated_draft(
            REPO_ROOT,
            output_path=tmp_path / "again.docx",
            verification_report_path=tmp_path / "verification.json",
        )
        for member in ("word/document.xml", "word/comments.xml"):
            assert _docx_xml(rendered.output_path, member) == _docx_xml(
                again.output_path, member
            ), member

    def test_comment_dates_come_from_map_not_wall_clock(self, rendered, inputs):
        xml = _docx_xml(rendered.output_path, "word/comments.xml").decode("utf-8")
        stamp = inputs.anchor_map["comment_timestamp"]
        dates = re.findall(r'w:date="([^"]+)"', xml)
        assert dates
        assert set(dates) == {stamp}
