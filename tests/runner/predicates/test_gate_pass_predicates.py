"""
Unit tests for gate_pass_recorded.

Nine test cases covering the predicate's verification contract:
  1. Pass: valid gate result, matching run, fresh timestamp.
  2. Gate result file absent → MISSING_MANDATORY_INPUT.
  3. Unknown gate_id → MISSING_MANDATORY_INPUT.
  4. run_id mismatch → STALE_UPSTREAM_MISMATCH.
  5. Missing input_fingerprint field → MALFORMED_ARTIFACT.
  6. Missing evaluated_at field → MALFORMED_ARTIFACT.
  7. status != "pass" → POLICY_VIOLATION.
  8. Freshness violation (upstream input modified after evaluated_at) → STALE_UPSTREAM_MISMATCH.
  9. manifest_version mismatch → STALE_UPSTREAM_MISMATCH.

All tests use tmp_path for tier4_root so no live repository state is touched.
Upstream input files (for test 8) are written to a synthetic repo_root under
tmp_path to keep tests self-contained.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import pytest

from runner.predicates.gate_pass_predicates import gate_pass_recorded
from runner.predicates.types import (
    MALFORMED_ARTIFACT,
    MISSING_MANDATORY_INPUT,
    POLICY_VIOLATION,
    STALE_UPSTREAM_MISMATCH,
)
from runner.versions import CONSTITUTION_VERSION, LIBRARY_VERSION, MANIFEST_VERSION

# ---------------------------------------------------------------------------
# Constants shared across tests
# ---------------------------------------------------------------------------

SAMPLE_RUN_ID = "run-aaaa1111-bbbb-cccc-dddd-eeeeeeeeeeee"
SAMPLE_GATE_ID = "phase_01_gate"
# Relative path within tier4_root for SAMPLE_GATE_ID
SAMPLE_RESULT_SUBPATH = "phase_outputs/phase1_call_analysis/gate_result.json"

# A timestamp safely in the future — upstream mtimes will always be earlier.
_FUTURE_TS = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
# A timestamp safely in the past — any file written during tests will be newer.
_PAST_TS = "2000-01-01T00:00:00+00:00"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_gate_result(
    *,
    run_id: str = SAMPLE_RUN_ID,
    gate_id: str = SAMPLE_GATE_ID,
    status: str = "pass",
    manifest_version: str = MANIFEST_VERSION,
    library_version: str = LIBRARY_VERSION,
    constitution_version: str = CONSTITUTION_VERSION,
    input_fingerprint: str = "abc123def456",
    evaluated_at: str = _FUTURE_TS,
    **extra: Any,
) -> dict[str, Any]:
    """Return a minimal valid GateResult dict with optional field overrides."""
    return {
        "gate_id": gate_id,
        "run_id": run_id,
        "status": status,
        "manifest_version": manifest_version,
        "library_version": library_version,
        "constitution_version": constitution_version,
        "input_fingerprint": input_fingerprint,
        "evaluated_at": evaluated_at,
        **extra,
    }


def _write_gate_result(
    tier4_root: Path,
    subpath: str,
    data: dict[str, Any],
) -> Path:
    """Write data as JSON to tier4_root / subpath, creating parents."""
    target = tier4_root / subpath
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data), encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestGatePassRecorded:

    # 1 — Pass: valid gate result with matching run_id, fresh evaluated_at.
    def test_pass_valid_gate_result(self, tmp_path: Path) -> None:
        tier4 = tmp_path / "tier4"
        _write_gate_result(tier4, SAMPLE_RESULT_SUBPATH, _make_gate_result())

        result = gate_pass_recorded(SAMPLE_GATE_ID, SAMPLE_RUN_ID, tier4)

        assert result.passed is True
        assert result.failure_category is None
        assert result.reason is None
        assert result.details["gate_id"] == SAMPLE_GATE_ID
        assert result.details["run_id"] == SAMPLE_RUN_ID
        assert result.details["status"] == "pass"

    # 2 — Gate result file absent → MISSING_MANDATORY_INPUT.
    def test_gate_result_absent(self, tmp_path: Path) -> None:
        tier4 = tmp_path / "tier4"
        tier4.mkdir()  # exists but the result file is not written

        result = gate_pass_recorded(SAMPLE_GATE_ID, SAMPLE_RUN_ID, tier4)

        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT
        assert SAMPLE_GATE_ID in (result.reason or "")

    # 3 — Unknown gate_id → MISSING_MANDATORY_INPUT.
    def test_unknown_gate_id(self, tmp_path: Path) -> None:
        tier4 = tmp_path / "tier4"

        result = gate_pass_recorded("gate_99_nonexistent", SAMPLE_RUN_ID, tier4)

        assert result.passed is False
        assert result.failure_category == MISSING_MANDATORY_INPUT
        assert "gate_99_nonexistent" in (result.reason or "")

    # 4 — run_id mismatch → STALE_UPSTREAM_MISMATCH.
    def test_run_id_mismatch(self, tmp_path: Path) -> None:
        tier4 = tmp_path / "tier4"
        stale_data = _make_gate_result(run_id="run-old-00000000-0000-0000-0000")
        _write_gate_result(tier4, SAMPLE_RESULT_SUBPATH, stale_data)

        result = gate_pass_recorded(SAMPLE_GATE_ID, SAMPLE_RUN_ID, tier4)

        assert result.passed is False
        assert result.failure_category == STALE_UPSTREAM_MISMATCH
        assert result.details["expected_run_id"] == SAMPLE_RUN_ID
        assert result.details["recorded_run_id"] == "run-old-00000000-0000-0000-0000"

    # 5 — Missing input_fingerprint field → MALFORMED_ARTIFACT.
    def test_missing_input_fingerprint(self, tmp_path: Path) -> None:
        tier4 = tmp_path / "tier4"
        data = _make_gate_result()
        del data["input_fingerprint"]
        _write_gate_result(tier4, SAMPLE_RESULT_SUBPATH, data)

        result = gate_pass_recorded(SAMPLE_GATE_ID, SAMPLE_RUN_ID, tier4)

        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "input_fingerprint" in (result.reason or "")

    # 6 — Missing evaluated_at field → MALFORMED_ARTIFACT.
    def test_missing_evaluated_at(self, tmp_path: Path) -> None:
        tier4 = tmp_path / "tier4"
        data = _make_gate_result()
        del data["evaluated_at"]
        _write_gate_result(tier4, SAMPLE_RESULT_SUBPATH, data)

        result = gate_pass_recorded(SAMPLE_GATE_ID, SAMPLE_RUN_ID, tier4)

        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "evaluated_at" in (result.reason or "")

    # 7 — status != "pass" → POLICY_VIOLATION.
    def test_status_not_pass(self, tmp_path: Path) -> None:
        tier4 = tmp_path / "tier4"
        _write_gate_result(
            tier4, SAMPLE_RESULT_SUBPATH, _make_gate_result(status="fail")
        )

        result = gate_pass_recorded(SAMPLE_GATE_ID, SAMPLE_RUN_ID, tier4)

        assert result.passed is False
        assert result.failure_category == POLICY_VIOLATION
        assert result.details["recorded_status"] == "fail"

    # 8 — Freshness violation: upstream input modified after evaluated_at.
    def test_freshness_violation(self, tmp_path: Path) -> None:
        tier4 = tmp_path / "tier4"
        # Gate result was "evaluated" in the distant past.
        _write_gate_result(
            tier4,
            SAMPLE_RESULT_SUBPATH,
            _make_gate_result(evaluated_at=_PAST_TS),
        )

        # Create a synthetic repo root and plant an upstream input file.
        # The upstream inputs for phase_01_gate include selected_call.json.
        # Writing it NOW means its mtime > _PAST_TS → freshness violation.
        fake_repo = tmp_path / "repo"
        upstream_file = (
            fake_repo
            / "docs"
            / "tier3_project_instantiation"
            / "call_binding"
            / "selected_call.json"
        )
        upstream_file.parent.mkdir(parents=True)
        upstream_file.write_text('{"call_id": "test"}', encoding="utf-8")

        result = gate_pass_recorded(
            SAMPLE_GATE_ID, SAMPLE_RUN_ID, tier4, repo_root=fake_repo
        )

        assert result.passed is False
        assert result.failure_category == STALE_UPSTREAM_MISMATCH
        assert result.details.get("stale_inputs"), "stale_inputs list should be non-empty"
        assert any(
            "selected_call.json" in p for p in result.details["stale_inputs"]
        )

    # 9 — manifest_version mismatch → STALE_UPSTREAM_MISMATCH.
    def test_manifest_version_mismatch(self, tmp_path: Path) -> None:
        tier4 = tmp_path / "tier4"
        old_version_data = _make_gate_result(manifest_version="0.9")
        _write_gate_result(tier4, SAMPLE_RESULT_SUBPATH, old_version_data)

        result = gate_pass_recorded(SAMPLE_GATE_ID, SAMPLE_RUN_ID, tier4)

        assert result.passed is False
        assert result.failure_category == STALE_UPSTREAM_MISMATCH
        assert result.details["expected_manifest_version"] == MANIFEST_VERSION
        assert result.details["recorded_manifest_version"] == "0.9"
