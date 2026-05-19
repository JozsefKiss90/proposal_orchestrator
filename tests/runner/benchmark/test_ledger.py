"""Tests for runner.benchmark.ledger — append-only JSONL ledger."""

import json
import threading

import pytest

from runner.benchmark.ledger import BenchmarkLedger, _record_to_dict
from runner.benchmark.models import BenchmarkInvocationRecord


def _make_record(**overrides) -> BenchmarkInvocationRecord:
    defaults = dict(
        invocation_id="inv-001",
        run_id="run-001",
        node_id="n01",
        skill_id="s01",
        predicate_id=None,
        invocation_type="skill_tapm",
        execution_mode="tapm",
        model="claude-sonnet-4-6",
        timeout_seconds=1200,
        tools_enabled=["Read", "Glob"],
        system_prompt_chars=5000,
        user_prompt_chars=3000,
        response_chars=2000,
        response_status="success",
        wall_clock_start=100.0,
        wall_clock_end=110.0,
        wall_clock_seconds=10.0,
        timestamp_utc="2026-05-19T00:00:00+00:00",
        estimated_input_tokens=2285,
        estimated_output_tokens=571,
        error_class=None,
        error_message=None,
    )
    defaults.update(overrides)
    return BenchmarkInvocationRecord(**defaults)


class TestBenchmarkLedgerInMemory:
    """Test in-memory ledger behavior (no file)."""

    def test_empty_ledger(self):
        ledger = BenchmarkLedger()
        assert ledger.records == []

    def test_append_single(self):
        ledger = BenchmarkLedger()
        record = _make_record()
        ledger.append(record)
        assert len(ledger.records) == 1
        assert ledger.records[0].invocation_id == "inv-001"

    def test_append_multiple(self):
        ledger = BenchmarkLedger()
        for i in range(5):
            ledger.append(_make_record(invocation_id=f"inv-{i}"))
        assert len(ledger.records) == 5

    def test_records_returns_copy(self):
        """records property returns a copy, not the internal list."""
        ledger = BenchmarkLedger()
        ledger.append(_make_record())
        copy = ledger.records
        copy.append(_make_record(invocation_id="extra"))
        assert len(ledger.records) == 1  # Internal list unchanged

    def test_close_no_file(self):
        """close() on in-memory ledger does not raise."""
        ledger = BenchmarkLedger()
        ledger.close()


class TestBenchmarkLedgerFile:
    """Test JSONL file persistence."""

    def test_writes_jsonl(self, tmp_path):
        path = tmp_path / "ledger.jsonl"
        ledger = BenchmarkLedger(ledger_path=path)
        ledger.append(_make_record(invocation_id="a1"))
        ledger.append(_make_record(invocation_id="a2"))
        ledger.close()

        lines = path.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        obj1 = json.loads(lines[0])
        assert obj1["invocation_id"] == "a1"
        obj2 = json.loads(lines[1])
        assert obj2["invocation_id"] == "a2"

    def test_append_flushes(self, tmp_path):
        """Each append is flushed to disk immediately."""
        path = tmp_path / "ledger.jsonl"
        ledger = BenchmarkLedger(ledger_path=path)
        ledger.append(_make_record(invocation_id="f1"))
        # Read without closing — data should be flushed
        content = path.read_text(encoding="utf-8")
        assert "f1" in content
        ledger.close()

    def test_close_is_idempotent(self, tmp_path):
        path = tmp_path / "ledger.jsonl"
        ledger = BenchmarkLedger(ledger_path=path)
        ledger.close()
        ledger.close()  # Should not raise

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "ledger.jsonl"
        ledger = BenchmarkLedger(ledger_path=path)
        ledger.append(_make_record())
        ledger.close()
        assert path.exists()

    def test_invalid_path_swallowed(self, tmp_path):
        """Invalid path causes no exception — ledger works in-memory only."""
        # On Windows, NUL is reserved; on Unix, use a path with null bytes
        # to ensure FileNotFoundError. Use a read-only directory approach.
        ledger = BenchmarkLedger(ledger_path=tmp_path / "\x00invalid")
        # Should not raise — just works in memory
        ledger.append(_make_record())
        assert len(ledger.records) == 1
        ledger.close()


class TestBenchmarkLedgerThreadSafety:
    """Test thread-safe append."""

    def test_concurrent_appends(self):
        ledger = BenchmarkLedger()
        errors = []

        def append_records(start_id: int):
            try:
                for i in range(50):
                    ledger.append(
                        _make_record(invocation_id=f"t{start_id}-{i}")
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=append_records, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(ledger.records) == 200  # 4 threads x 50 records


class TestRecordToDict:
    """Test _record_to_dict serialization helper."""

    def test_serializes_all_fields(self):
        record = _make_record()
        d = _record_to_dict(record)
        assert d["invocation_id"] == "inv-001"
        assert d["model"] == "claude-sonnet-4-6"
        assert d["tools_enabled"] == ["Read", "Glob"]
        assert d["error_class"] is None

    def test_json_serializable(self):
        record = _make_record()
        d = _record_to_dict(record)
        # Should not raise
        text = json.dumps(d)
        assert isinstance(text, str)
