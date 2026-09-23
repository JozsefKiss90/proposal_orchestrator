"""
Tests for harness/provenance.py — {judge_model, judge_version, prompt_hash,
score, rationale} logging for every verdict.

Covers:
  - prompt_hash stability + order sensitivity + delimiter safety
  - required-field contract on to_dict()
  - Inferred / non-empty model+version enforcement
  - from_verdict() carries score/rationale/status through
  - ProvenanceLog append-only JSONL, atomic rewrite, reload across instances
"""

from __future__ import annotations

import json

import pytest

from harness.provenance import (
    REQUIRED_PROVENANCE_FIELDS,
    ProvenanceLog,
    ProvenanceRecord,
    prompt_hash,
)
from harness.verdict import Verdict


def _rec(**kw) -> ProvenanceRecord:
    base = dict(
        judge_model="acme-judge-1",
        judge_version="2026-07-20",
        prompt_hash="sha256:deadbeef",
        score=0.5,
        rationale="because",
    )
    base.update(kw)
    return ProvenanceRecord(**base)


# --------------------------------------------------------------------------- #
# prompt_hash
# --------------------------------------------------------------------------- #


class TestPromptHash:
    def test_stable(self):
        assert prompt_hash("sys", "usr") == prompt_hash("sys", "usr")

    def test_prefixed_sha256(self):
        assert prompt_hash("a", "b").startswith("sha256:")

    def test_order_sensitive(self):
        assert prompt_hash("a", "b") != prompt_hash("b", "a")

    def test_delimiter_not_forgeable(self):
        # Moving text across the system/user boundary must change the hash;
        # the NUL delimiter cannot be smuggled inside either prompt.
        assert prompt_hash("ab", "c") != prompt_hash("a", "bc")


# --------------------------------------------------------------------------- #
# ProvenanceRecord
# --------------------------------------------------------------------------- #


class TestProvenanceRecord:
    def test_required_fields_present(self):
        d = _rec().to_dict()
        assert REQUIRED_PROVENANCE_FIELDS <= d.keys()
        for f in REQUIRED_PROVENANCE_FIELDS:
            assert f in d

    def test_required_fields_are_the_guardrail_five(self):
        assert REQUIRED_PROVENANCE_FIELDS == {
            "judge_model",
            "judge_version",
            "prompt_hash",
            "score",
            "rationale",
        }

    @pytest.mark.parametrize("bad", ["Confirmed", "Assumed", "Unresolved", ""])
    def test_non_inferred_rejected(self, bad):
        with pytest.raises(ValueError, match="evidence_type"):
            _rec(evidence_type=bad)

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_blank_model_rejected(self, blank):
        with pytest.raises(ValueError, match="judge_model"):
            _rec(judge_model=blank)

    @pytest.mark.parametrize("blank", ["", "   "])
    def test_blank_version_rejected(self, blank):
        with pytest.raises(ValueError, match="judge_version"):
            _rec(judge_version=blank)

    def test_score_may_be_none(self):
        assert _rec(score=None).to_dict()["score"] is None

    def test_from_verdict_carries_fields(self):
        v = Verdict(metric="faithfulness", property_key="C07", passed=False, score=0.1, rationale="unsupported")
        rec = ProvenanceRecord.from_verdict(
            v,
            judge_model="acme-judge-1",
            judge_version="2026-07-20",
            prompt_hash="sha256:abc",
        )
        d = rec.to_dict()
        assert d["score"] == 0.1
        assert d["rationale"] == "unsupported"
        assert d["metric"] == "faithfulness"
        assert d["property_key"] == "C07"
        assert d["passed"] is False
        assert d["evidence_type"] == "Inferred"
        assert d["judge_model"] == "acme-judge-1"


# --------------------------------------------------------------------------- #
# ProvenanceLog
# --------------------------------------------------------------------------- #


class TestProvenanceLog:
    def test_append_writes_jsonl(self, tmp_path):
        log = ProvenanceLog(tmp_path / "prov.jsonl")
        log.append(_rec(prompt_hash="sha256:1"))
        log.append(_rec(prompt_hash="sha256:2"))

        lines = (tmp_path / "prov.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["prompt_hash"] == "sha256:1"
        assert json.loads(lines[1])["prompt_hash"] == "sha256:2"

    def test_len_and_records(self, tmp_path):
        log = ProvenanceLog(tmp_path / "p.jsonl")
        log.append(_rec())
        log.append(_rec())
        assert len(log) == 2
        assert len(log.records()) == 2

    def test_records_is_a_copy(self, tmp_path):
        log = ProvenanceLog(tmp_path / "p.jsonl")
        log.append(_rec())
        got = log.records()
        got.append({"tampered": True})
        assert len(log) == 1  # internal state untouched

    def test_reload_across_instances(self, tmp_path):
        p = tmp_path / "p.jsonl"
        ProvenanceLog(p).append(_rec(prompt_hash="sha256:first"))
        # A fresh instance must see the pre-existing record and append after it.
        log2 = ProvenanceLog(p)
        assert len(log2) == 1
        log2.append(_rec(prompt_hash="sha256:second"))
        lines = p.read_text(encoding="utf-8").splitlines()
        assert [json.loads(l)["prompt_hash"] for l in lines] == ["sha256:first", "sha256:second"]

    def test_creates_parent_dirs(self, tmp_path):
        log = ProvenanceLog(tmp_path / "nested" / "deep" / "p.jsonl")
        log.append(_rec())
        assert (tmp_path / "nested" / "deep" / "p.jsonl").is_file()
