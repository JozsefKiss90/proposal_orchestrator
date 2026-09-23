"""
Tests for runner/json_extract.py — shared JSON-object extraction helper.

This helper consolidates the extractor previously duplicated in
runner/semantic_dispatch.py and harness/judge.py; these tests pin the
extraction order and the never-repair contract both callers rely on.
"""

from __future__ import annotations

import pytest

from runner.json_extract import extract_first_json_object


class TestExtractFirstJsonObject:
    def test_bare_object(self):
        assert extract_first_json_object('{"a": 1}') == {"a": 1}

    def test_object_with_surrounding_whitespace(self):
        assert extract_first_json_object('\n  {"a": 1}\n') == {"a": 1}

    def test_fenced_json(self):
        assert extract_first_json_object('```json\n{"a": 1}\n```') == {"a": 1}

    def test_fenced_bare(self):
        assert extract_first_json_object('```\n{"a": 1}\n```') == {"a": 1}

    def test_embedded_in_prose(self):
        assert extract_first_json_object('Here is the verdict: {"a": 1}. Done.') == {"a": 1}

    def test_top_level_list_is_not_mined(self):
        # A top-level array must NOT have a nested dict pulled out of it.
        assert extract_first_json_object('[{"a": 1}]') is None

    @pytest.mark.parametrize("bad", ["", "   ", None, "no json here", "{not valid}", "{"])
    def test_unparseable_returns_none(self, bad):
        assert extract_first_json_object(bad) is None

    def test_never_raises(self):
        # Malformed input yields None, never an exception.
        for s in ["{", "}", "{'single': 'quotes'}", "{,}", "```json\n{oops}\n```"]:
            assert extract_first_json_object(s) is None

    def test_matches_legacy_semantic_dispatch_wrapper(self):
        # The retained module-local wrapper must delegate identically.
        from runner.semantic_dispatch import _extract_json

        for s in ['{"x": 1}', '```json\n{"y": 2}\n```', "prose {\"z\": 3} more", "[1,2]", ""]:
            assert _extract_json(s) == extract_first_json_object(s)
