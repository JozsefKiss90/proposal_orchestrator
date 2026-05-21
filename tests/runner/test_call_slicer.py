"""
Tests for runner.call_slicer — deterministic input bounding (Step 0).

Covers the 10 required test cases from backend_migration_plan.md §0.10:

  1.  Happy path: valid inputs → correct output
  2.  Output size < 20 KB
  3.  Only target call in output
  4.  Missing selected_call.json → CallSlicerError
  5.  Missing grouped JSON → CallSlicerError
  6.  topic_code not found → CallSlicerError
  7.  Unknown work_programme → CallSlicerError
  8.  Idempotency (modulo timestamp)
  9.  Grouped JSON unmodified after slicing
  10. Output path correctness

Additional tests:
  11. Schema B (CL1/CL2) matching via identifier field
  12. Target in second destination → correct source_destination
  13. Malformed selected_call.json → CallSlicerError
  14. Missing topic_code key → CallSlicerError
  15. Missing work_programme key → CallSlicerError

All tests use tmp_path for isolation — no real repository files are read.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from runner.call_slicer import (
    CALL_EXTRACTS_DIR,
    GROUPED_JSON_MAP,
    MAX_SLICE_BYTES,
    SELECTED_CALL_PATH,
    CallSlicerError,
    generate_call_slice,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: Any) -> None:
    """Write *data* as JSON to *path*, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _call_entry_a(call_id: str, **overrides: Any) -> dict[str, Any]:
    """Minimal Schema-A call entry (CL3-6 style: call_id / original_call_id)."""
    entry: dict[str, Any] = {
        "call_id": call_id,
        "call_title": f"Title for {call_id}",
        "scope": "Test scope text.",
        "expected_outcome": "Test expected outcome.",
        "original_call_id": call_id,
    }
    entry.update(overrides)
    return entry


def _call_entry_b(identifier: str, **overrides: Any) -> dict[str, Any]:
    """Minimal Schema-B call entry (CL1-2 style: identifier / topic_id)."""
    entry: dict[str, Any] = {
        "identifier": identifier,
        "topic_title": f"Title for {identifier}",
        "call_title": "Cluster call",
        "call_identifier": identifier.rsplit("-", 1)[0],
        "topic_id": identifier,
        "scope": "Test scope text.",
        "expected_outcome": "Test expected outcome.",
    }
    entry.update(overrides)
    return entry


def _minimal_grouped(
    calls: list[dict[str, Any]],
    destination_title: str = "Test Destination",
) -> dict[str, Any]:
    """Grouped JSON with a single destination containing *calls*."""
    return {
        "destinations": [
            {
                "destination_title": destination_title,
                "calls": calls,
            }
        ]
    }


def _multi_destination_grouped(
    destinations: list[tuple[str, list[dict[str, Any]]]],
) -> dict[str, Any]:
    """Grouped JSON with multiple destinations."""
    return {
        "destinations": [
            {"destination_title": title, "calls": calls}
            for title, calls in destinations
        ]
    }


# The work_programme used in most tests; must be a key in GROUPED_JSON_MAP.
_WP = "cluster_digital"
_TOPIC = "HORIZON-CL4-2026-TEST-01"


def _make_env(
    tmp_path: Path,
    *,
    topic_code: str = _TOPIC,
    work_programme: str = _WP,
    grouped: dict[str, Any] | None = None,
    selected_overrides: dict[str, Any] | None = None,
    skip_selected: bool = False,
    skip_grouped: bool = False,
) -> Path:
    """Set up a minimal slicer environment under *tmp_path* and return it as repo_root."""

    # selected_call.json
    if not skip_selected:
        selected: dict[str, Any] = {
            "topic_code": topic_code,
            "work_programme": work_programme,
        }
        if selected_overrides:
            selected.update(selected_overrides)
        _write_json(tmp_path / SELECTED_CALL_PATH, selected)

    # grouped JSON at the path that GROUPED_JSON_MAP expects
    if not skip_grouped and work_programme in GROUPED_JSON_MAP:
        grouped_rel = GROUPED_JSON_MAP[work_programme]
        if grouped is None:
            grouped = _minimal_grouped([_call_entry_a(topic_code)])
        _write_json(tmp_path / grouped_rel, grouped)

    return tmp_path


# ---------------------------------------------------------------------------
# Required tests (1–10)
# ---------------------------------------------------------------------------


class TestCallSlicer:
    """Required test cases from backend_migration_plan.md §0.10."""

    # 1. Happy path
    def test_happy_path(self, tmp_path: Path) -> None:
        repo = _make_env(tmp_path)
        result = generate_call_slice(repo)

        assert result.exists()
        data = json.loads(result.read_text(encoding="utf-8"))

        assert data["topic_code"] == _TOPIC
        assert data["call_entry"]["call_id"] == _TOPIC
        assert data["source_destination"] == "Test Destination"
        assert data["sliced_by"] == "runner/call_slicer.py"
        assert "slice_timestamp" in data
        assert data["source_grouped_json"] == GROUPED_JSON_MAP[_WP]

    # 2. Output size bound
    def test_output_size_bound(self, tmp_path: Path) -> None:
        repo = _make_env(tmp_path)
        result = generate_call_slice(repo)
        assert result.stat().st_size < MAX_SLICE_BYTES

    def test_oversized_output_raises(self, tmp_path: Path) -> None:
        big_scope = "x" * 25_000  # push output well over 20 KB
        grouped = _minimal_grouped([_call_entry_a(_TOPIC, scope=big_scope)])
        repo = _make_env(tmp_path, grouped=grouped)

        with pytest.raises(CallSlicerError, match="exceeds"):
            generate_call_slice(repo)

    # 3. Only target call in output
    def test_only_target_call_in_output(self, tmp_path: Path) -> None:
        calls = [
            _call_entry_a("OTHER-CALL-01"),
            _call_entry_a(_TOPIC),
            _call_entry_a("OTHER-CALL-02"),
        ]
        grouped = _minimal_grouped(calls)
        repo = _make_env(tmp_path, grouped=grouped)
        result = generate_call_slice(repo)

        data = json.loads(result.read_text(encoding="utf-8"))
        assert data["call_entry"]["call_id"] == _TOPIC
        # Ensure no other call_ids leaked into the output
        raw = result.read_text(encoding="utf-8")
        assert "OTHER-CALL-01" not in raw
        assert "OTHER-CALL-02" not in raw

    # 4. Missing selected_call.json
    def test_missing_selected_call(self, tmp_path: Path) -> None:
        _make_env(tmp_path, skip_selected=True)
        with pytest.raises(CallSlicerError, match="not found"):
            generate_call_slice(tmp_path)

    # 5. Missing grouped JSON
    def test_missing_grouped_json(self, tmp_path: Path) -> None:
        repo = _make_env(tmp_path, skip_grouped=True)
        with pytest.raises(CallSlicerError, match="not found"):
            generate_call_slice(repo)

    # 6. topic_code not found in grouped JSON
    def test_topic_code_not_found(self, tmp_path: Path) -> None:
        grouped = _minimal_grouped([_call_entry_a("COMPLETELY-DIFFERENT-ID")])
        repo = _make_env(tmp_path, grouped=grouped)
        with pytest.raises(CallSlicerError, match="not found"):
            generate_call_slice(repo)

    # 7. Unknown work_programme
    def test_unknown_work_programme(self, tmp_path: Path) -> None:
        repo = _make_env(tmp_path, work_programme="cluster_unknown", skip_grouped=True)
        # Manually write selected_call.json with the unknown programme
        _write_json(
            tmp_path / SELECTED_CALL_PATH,
            {"topic_code": _TOPIC, "work_programme": "cluster_unknown"},
        )
        with pytest.raises(CallSlicerError, match="Unknown work_programme"):
            generate_call_slice(repo)

    # 8. Idempotency (modulo timestamp)
    def test_idempotency(self, tmp_path: Path) -> None:
        repo = _make_env(tmp_path)

        generate_call_slice(repo)
        data1 = json.loads(
            (repo / CALL_EXTRACTS_DIR / f"{_TOPIC}.slice.json").read_text(
                encoding="utf-8"
            )
        )

        generate_call_slice(repo)
        data2 = json.loads(
            (repo / CALL_EXTRACTS_DIR / f"{_TOPIC}.slice.json").read_text(
                encoding="utf-8"
            )
        )

        # Zero out timestamps before comparison
        data1.pop("slice_timestamp")
        data2.pop("slice_timestamp")
        assert data1 == data2

    # 9. Grouped JSON unmodified
    def test_grouped_json_unmodified(self, tmp_path: Path) -> None:
        repo = _make_env(tmp_path)
        grouped_path = repo / GROUPED_JSON_MAP[_WP]
        before = grouped_path.read_bytes()

        generate_call_slice(repo)

        after = grouped_path.read_bytes()
        assert before == after

    # 10. Output path correctness
    def test_output_path_correctness(self, tmp_path: Path) -> None:
        repo = _make_env(tmp_path)
        result = generate_call_slice(repo)

        expected = repo / CALL_EXTRACTS_DIR / f"{_TOPIC}.slice.json"
        assert result == expected


# ---------------------------------------------------------------------------
# Additional tests (11–15)
# ---------------------------------------------------------------------------


class TestCallSlicerSchemaVariants:
    """Schema-B (CL1/CL2) matching and multi-destination tests."""

    # 11. Schema B matching via identifier field
    def test_schema_b_identifier_field(self, tmp_path: Path) -> None:
        topic = "HORIZON-HLTH-2026-01-TEST-01"
        wp = "cluster_health"
        calls = [_call_entry_b(topic)]
        grouped = _minimal_grouped(calls)
        repo = _make_env(tmp_path, topic_code=topic, work_programme=wp, grouped=grouped)

        result = generate_call_slice(repo)
        data = json.loads(result.read_text(encoding="utf-8"))

        assert data["topic_code"] == topic
        assert data["call_entry"]["identifier"] == topic

    # 12. Target in second destination
    def test_multiple_destinations(self, tmp_path: Path) -> None:
        grouped = _multi_destination_grouped([
            ("First Destination", [_call_entry_a("OTHER-CALL-99")]),
            ("Second Destination", [_call_entry_a(_TOPIC)]),
        ])
        repo = _make_env(tmp_path, grouped=grouped)
        result = generate_call_slice(repo)

        data = json.loads(result.read_text(encoding="utf-8"))
        assert data["source_destination"] == "Second Destination"
        assert data["call_entry"]["call_id"] == _TOPIC


class TestCallSlicerInputValidation:
    """Malformed or incomplete selected_call.json."""

    # 13. Malformed JSON
    def test_malformed_selected_call_json(self, tmp_path: Path) -> None:
        path = tmp_path / SELECTED_CALL_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not valid json", encoding="utf-8")

        with pytest.raises(CallSlicerError, match="not valid JSON"):
            generate_call_slice(tmp_path)

    # 14. Missing topic_code key
    def test_missing_topic_code_key(self, tmp_path: Path) -> None:
        _write_json(
            tmp_path / SELECTED_CALL_PATH,
            {"work_programme": _WP},  # no topic_code
        )
        with pytest.raises(CallSlicerError, match="topic_code"):
            generate_call_slice(tmp_path)

    # 15. Missing work_programme key
    def test_missing_work_programme_key(self, tmp_path: Path) -> None:
        _write_json(
            tmp_path / SELECTED_CALL_PATH,
            {"topic_code": _TOPIC},  # no work_programme
        )
        with pytest.raises(CallSlicerError, match="work_programme"):
            generate_call_slice(tmp_path)
