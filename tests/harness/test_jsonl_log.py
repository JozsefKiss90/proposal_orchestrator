"""
Tests for harness/jsonl_log.py — the shared append-only JSONL base.

ProvenanceLog and CalibrationLog both subclass this; here we pin the base
behaviour (atomic append, reload, parent-dir creation, records copy) directly.
"""

from __future__ import annotations

import json

from harness.jsonl_log import JsonlLog


class TestJsonlLog:
    def test_append_writes_one_line_each(self, tmp_path):
        log = JsonlLog(tmp_path / "l.jsonl", prefix="t_")
        log.append_dict({"a": 1})
        log.append_dict({"a": 2})
        lines = (tmp_path / "l.jsonl").read_text(encoding="utf-8").splitlines()
        assert [json.loads(x)["a"] for x in lines] == [1, 2]

    def test_len_and_records_copy(self, tmp_path):
        log = JsonlLog(tmp_path / "l.jsonl")
        log.append_dict({"a": 1})
        got = log.records()
        got.append({"tampered": True})
        assert len(log) == 1  # internal mirror untouched

    def test_reload_across_instances(self, tmp_path):
        p = tmp_path / "l.jsonl"
        JsonlLog(p).append_dict({"a": 1})
        log2 = JsonlLog(p)
        assert len(log2) == 1
        log2.append_dict({"a": 2})
        assert len(JsonlLog(p)) == 2

    def test_creates_parent_dirs(self, tmp_path):
        log = JsonlLog(tmp_path / "deep" / "nested" / "l.jsonl")
        log.append_dict({"a": 1})
        assert (tmp_path / "deep" / "nested" / "l.jsonl").is_file()

    def test_path_property(self, tmp_path):
        p = tmp_path / "l.jsonl"
        assert JsonlLog(p).path == p
