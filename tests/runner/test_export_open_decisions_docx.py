"""
Stage-2 OD round-3 handout — regression seam for
``tools/export_open_decisions_docx.py`` and the handout's consistency with the
Stage-1 anchor map (plans/partb_final_drafting_strategy_2026-09-03.md §4).

Pins the load-bearing Stage-2 guarantees:

  * **handout ↔ anchor map consistency:** every needs-input / split action of
    the Stage-1 anchor map has exactly one ``## A-x`` entry, each entry cites
    at least one anchor that exists in the map (same sub-section and ¶), and
    each entry states a fallback and the answer deadline;
  * **resolved items are listed for veto, not authoring:** the
    resolved-in-draft table names A-11, the A-5 table half and the A-8 KPI
    half;
  * **faithful docx circulation copy:** the export renders every entry
    heading and the resolved table, and two renders are XML-identical
    (determinism at the document-part level, as in Stage 1).

Tests read the committed handout and anchor map read-only; docx output goes
to tmp_path.
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

import pytest

from tools.annotate_part_b_draft import ANCHOR_MAP_REL
from tools.export_open_decisions_docx import (
    DEFAULT_HANDOUT_REL,
    export_handout_docx,
    parse_inline_runs,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
HANDOUT_PATH = REPO_ROOT / DEFAULT_HANDOUT_REL

pytestmark = pytest.mark.skipif(
    not HANDOUT_PATH.is_file(), reason="round-3 handout not present"
)


@pytest.fixture(scope="module")
def handout_text() -> str:
    return HANDOUT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def anchor_map() -> dict:
    return json.loads(
        (REPO_ROOT / ANCHOR_MAP_REL).read_text(encoding="utf-8")
    )


@pytest.fixture(scope="module")
def entries(handout_text) -> dict[str, str]:
    """Map each ``## A-x — …`` entry heading to its body text."""
    parts = re.split(r"^## (A-\d+) — ", handout_text, flags=re.M)
    return {
        parts[i]: parts[i + 1] for i in range(1, len(parts) - 1, 2)
    }


class TestHandoutAnchorMapConsistency:
    def test_every_needs_input_action_has_exactly_one_entry(
        self, entries, anchor_map
    ):
        needs_input = {
            a["action_id"]
            for a in anchor_map["actions"]
            if a["kind"] in ("needs_input", "split")
        }
        assert set(entries) == needs_input

    def test_resolved_in_draft_actions_have_no_entry(self, entries, anchor_map):
        resolved = {
            a["action_id"]
            for a in anchor_map["actions"]
            if a["kind"] == "resolved_in_draft"
        }
        assert not (resolved & set(entries))

    def test_each_entry_cites_a_mapped_anchor(self, entries, anchor_map):
        anchors_by_action = {
            a["action_id"]: a["anchors"] for a in anchor_map["actions"]
        }
        for action_id, body in entries.items():
            cited = re.findall(r"section (\d\.\d) ¶(\d+)", body)
            assert cited, f"{action_id}: no anchor citation"
            mapped = {
                (an["sub_section_id"], str(an["paragraph"]))
                for an in anchors_by_action[action_id]
            }
            assert set(cited) <= mapped, (
                f"{action_id}: cites {cited} not in map {mapped}"
            )
            assert f"[{action_id}]" in body

    def test_each_entry_states_fallback_owner_and_deadline(self, entries):
        for action_id, body in entries.items():
            assert "**Fallback if unanswered:**" in body, action_id
            assert "**Owner:" in body, action_id
            assert "2026-09-05" in body, action_id

    def test_resolved_verify_table_lists_the_three_draft_resolutions(
        self, handout_text
    ):
        table_section = handout_text.split(
            "## Resolved in the annotated draft"
        )[1]
        for needle in ("A-11", "A-5 table half", "A-8 KPI half", "K11"):
            assert needle in table_section, needle

    def test_split_actions_reference_their_resolved_half(self, entries):
        assert "resolved in the annotated draft" in entries["A-5"]
        assert "resolved in the draft" in entries["A-8"]


class TestInlineRuns:
    def test_bold_and_plain_segments(self):
        runs = parse_inline_runs("plain **bold** tail")
        assert runs == [("plain ", False), ("bold", True), (" tail", False)]

    def test_unterminated_bold_is_literal(self):
        assert parse_inline_runs("a ** b") == [("a ** b", False)]

    def test_single_asterisk_emphasis_is_stripped_verbatim(self):
        assert parse_inline_runs("a *word* b") == [("a word b", False)]


class TestDocxExport:
    @pytest.fixture(scope="class")
    def exported(self, tmp_path_factory):
        out = tmp_path_factory.mktemp("stage2") / "round3.docx"
        return export_handout_docx(REPO_ROOT, output_path=out)

    @staticmethod
    def _text(path: Path) -> str:
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", xml))

    def test_all_entries_rendered(self, exported, entries):
        text = self._text(exported)
        for action_id in entries:
            assert f"{action_id} — " in text, action_id

    def test_quoted_list_items_keep_their_continuation_lines(self, exported):
        """A hard-wrapped list item inside a blockquote renders as ONE quote
        paragraph, not an item plus an orphan continuation paragraph."""
        from docx import Document

        doc = Document(str(exported))
        quotes = [
            p.text for p in doc.paragraphs if p.style.name == "Quote"
        ]
        joined = [q for q in quotes if "blocked unseen-year performance" in q]
        assert any(q.startswith("1. A released") for q in joined)
        assert not any(
            q.startswith("uncertainty and blocked") for q in quotes
        )

    def test_tables_rendered(self, exported):
        with zipfile.ZipFile(exported) as z:
            xml = z.read("word/document.xml").decode("utf-8")
        assert xml.count("<w:tbl>") >= 2  # resolved table + dates table

    def test_bold_markers_not_leaked(self, exported):
        assert "**" not in self._text(exported)

    def test_two_renders_are_xml_identical(self, exported, tmp_path):
        again = export_handout_docx(
            REPO_ROOT, output_path=tmp_path / "again.docx"
        )
        with zipfile.ZipFile(exported) as z1, zipfile.ZipFile(again) as z2:
            assert z1.read("word/document.xml") == z2.read("word/document.xml")
