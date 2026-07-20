"""
Tests for harness/faithfulness.py — the atomic faithfulness question.

Covers:
  - prompt carries claim + source; independence framing; JSON-only instruction
  - resolve_source_text prefers inline excerpt; reads source_ref via repo_root;
    raises when neither is available
  - judge_pair_supported wires the judge, stamps the metric + pair_id
"""

from __future__ import annotations

from typing import Any

import pytest

from harness.faithfulness import (
    FAITHFULNESS_METRIC,
    build_faithfulness_prompt,
    judge_pair_supported,
    resolve_source_text,
)
from harness.gold_set import GoldPair
from harness.judge import Judge, JudgeConfig


class _Backend:
    def __init__(self, content: str) -> None:
        self._content = content
        self.calls: list[list[dict[str, Any]]] = []

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        self.calls.append(messages)
        return {"content": self._content, "tool_calls": None}


def _judge(content='{"passed": true, "rationale": "stated verbatim"}') -> tuple[Judge, _Backend]:
    b = _Backend(content)
    return Judge(JudgeConfig(model="acme-judge-1", version="v1"), backend=b), b


class TestPrompt:
    def test_contains_claim_and_source(self):
        sys, usr = build_faithfulness_prompt("tomato is the crop", "The crop is tomato.", source_ref="docs/x.json")
        assert "tomato is the crop" in usr
        assert "The crop is tomato." in usr
        assert "docs/x.json" in usr

    def test_independence_and_json_framing(self):
        sys, _ = build_faithfulness_prompt("c", "s")
        assert "different model" in sys
        assert "passed" in sys
        assert "false" in sys  # instructs conservative default

    def test_no_source_ref_line_when_absent(self):
        _, usr = build_faithfulness_prompt("c", "s")
        assert "SOURCE REF" not in usr


class TestResolveSourceText:
    def test_prefers_excerpt(self):
        p = GoldPair(pair_id="g", claim="c", source_ref="docs/x.json", source_excerpt="the passage")
        assert resolve_source_text(p) == "the passage"

    def test_reads_source_ref_via_repo_root(self, tmp_path):
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "x.json").write_text("file body", encoding="utf-8")
        p = GoldPair(pair_id="g", claim="c", source_ref="docs/x.json")
        assert resolve_source_text(p, repo_root=tmp_path) == "file body"

    def test_raises_without_excerpt_or_root(self):
        p = GoldPair(pair_id="g", claim="c", source_ref="docs/x.json")
        with pytest.raises(ValueError, match="cannot judge"):
            resolve_source_text(p)

    def test_raises_when_source_ref_missing_on_disk(self, tmp_path):
        p = GoldPair(pair_id="g", claim="c", source_ref="docs/nope.json")
        with pytest.raises(ValueError, match="not found"):
            resolve_source_text(p, repo_root=tmp_path)


class TestJudgePairSupported:
    def test_supported_true(self):
        judge, _ = _judge('{"passed": true, "rationale": "ok"}')
        p = GoldPair(pair_id="g5", claim="c", source_ref="docs/x.json", source_excerpt="c is stated")
        res = judge_pair_supported(judge, p)
        assert res.verdict.passed is True
        assert res.verdict.metric == FAITHFULNESS_METRIC
        assert res.verdict.property_key == "g5"

    def test_supported_false(self):
        judge, _ = _judge('{"passed": false, "rationale": "source silent"}')
        p = GoldPair(pair_id="g6", claim="c", source_ref="docs/x.json", source_excerpt="unrelated text")
        res = judge_pair_supported(judge, p)
        assert res.verdict.passed is False

    def test_source_excerpt_reaches_backend(self):
        judge, backend = _judge()
        p = GoldPair(pair_id="g", claim="the claim", source_ref="d", source_excerpt="EXCERPT-XYZ")
        judge_pair_supported(judge, p)
        user_msg = backend.calls[0][1]["content"]
        assert "EXCERPT-XYZ" in user_msg
        assert "the claim" in user_msg
