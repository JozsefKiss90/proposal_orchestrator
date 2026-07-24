"""Tests for runner.deterministic_components — manifest-bound component substrate.

Covers the C2/C3 substrate (CLAUDE.md §17.5.3, §16.5):
  - invoke_component success / unknown-id / raised-exception → records
  - output path normalization to repo-relative POSIX strings
  - the n04 dependency_normalizer is registered and runs through the
    generic path with byte-identical output (migration regression)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.deterministic_components import (
    COMPONENT_REGISTRY,
    invoke_component,
    _to_repo_relative,
)
from runner.dependency_normalizer import (
    normalize_dependencies,
    OUTPUT_REL,
    WP_STRUCTURE_REL,
    WP_SEED_REL,
    SELECTED_CALL_REL,
)
from runner.runtime_models import ComponentInvocationRecord


# ---------------------------------------------------------------------------
# invoke_component — generic behavior
# ---------------------------------------------------------------------------


class TestInvokeComponentSuccess:
    def test_success_record_with_repo_relative_outputs(self, tmp_path: Path) -> None:
        """A registered component that writes an artifact → success record."""

        def _fake(run_id: str, repo_root: Path) -> list[Path]:
            out = repo_root / "docs" / "tier4" / "out.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"run_id": run_id}), encoding="utf-8")
            return [out]

        with pytest.MonkeyPatch.context() as mp:
            mp.setitem(COMPONENT_REGISTRY, "fake", _fake)
            record = invoke_component("fake", "run-x", tmp_path)

        assert isinstance(record, ComponentInvocationRecord)
        assert record.component_id == "fake"
        assert record.status == "success"
        assert record.failure_reason is None
        # Absolute path returned by the component is normalized to repo-relative
        assert record.outputs_written == ["docs/tier4/out.json"]

    def test_empty_outputs_still_success(self, tmp_path: Path) -> None:
        """A component that writes nothing still yields a success record."""

        def _noop(run_id: str, repo_root: Path) -> list[Path]:
            return []

        with pytest.MonkeyPatch.context() as mp:
            mp.setitem(COMPONENT_REGISTRY, "noop", _noop)
            record = invoke_component("noop", "run-x", tmp_path)

        assert record.status == "success"
        assert record.outputs_written == []


class TestInvokeComponentFailure:
    def test_unknown_component_is_failure_record(self, tmp_path: Path) -> None:
        """An unbound component id → failure record naming the unknown id."""
        record = invoke_component("does_not_exist", "run-x", tmp_path)
        assert record.status == "failure"
        assert record.component_id == "does_not_exist"
        assert "Unknown deterministic component" in (record.failure_reason or "")
        assert "does_not_exist" in (record.failure_reason or "")

    def test_raised_exception_becomes_failure_record(self, tmp_path: Path) -> None:
        """A component that raises → failure record (never propagates)."""

        def _boom(run_id: str, repo_root: Path):
            raise ValueError("kaboom")

        with pytest.MonkeyPatch.context() as mp:
            mp.setitem(COMPONENT_REGISTRY, "boom", _boom)
            record = invoke_component("boom", "run-x", tmp_path)

        assert record.status == "failure"
        assert "kaboom" in (record.failure_reason or "")
        assert "ValueError" in (record.failure_reason or "")


class TestPathNormalization:
    def test_absolute_path_normalized(self, tmp_path: Path) -> None:
        p = tmp_path / "docs" / "a" / "b.json"
        assert _to_repo_relative(p, tmp_path) == "docs/a/b.json"

    def test_relative_path_preserved_with_forward_slashes(self, tmp_path: Path) -> None:
        assert _to_repo_relative("docs\\a\\b.json", tmp_path) == "docs/a/b.json"


# ---------------------------------------------------------------------------
# n04 dependency_normalizer migration regression (byte-identical output)
# ---------------------------------------------------------------------------


def _write_dep_fixtures(tmp_path: Path) -> None:
    """Minimal fixtures for the Phase-4 dependency normalizer."""
    wp = tmp_path / WP_STRUCTURE_REL
    wp.parent.mkdir(parents=True, exist_ok=True)
    wp.write_text(json.dumps({
        "schema_id": "orch.phase3.wp_structure.v1",
        "run_id": "run-phase3",
        "work_packages": [
            {"wp_id": "WP1", "title": "Mgmt", "lead_partner": "P1",
             "tasks": [{"task_id": "T1-01", "title": "t"}], "deliverables": [],
             "dependencies": []},
            {"wp_id": "WP2", "title": "Res", "lead_partner": "P2",
             "tasks": [{"task_id": "T2-01", "title": "t"}], "deliverables": [],
             "dependencies": []},
        ],
        "dependency_map": {
            "nodes": ["WP1", "WP2", "T1-01", "T2-01"],
            "edges": [
                {"from": "WP2", "to": "WP1", "edge_type": "finish_to_start"},
                {"from": "T1-01", "to": "T2-01", "edge_type": "data_input"},
            ],
        },
    }), encoding="utf-8")

    seed = tmp_path / WP_SEED_REL
    seed.parent.mkdir(parents=True, exist_ok=True)
    seed.write_text(json.dumps({"work_packages": [
        {"id": "WP1", "start_month": 12, "end_month": 48},
        {"id": "WP2", "start_month": 1, "end_month": 36},
    ]}), encoding="utf-8")

    call = tmp_path / SELECTED_CALL_REL
    call.parent.mkdir(parents=True, exist_ok=True)
    call.write_text(json.dumps({
        "call_id": "T", "topic_code": "T", "instrument_type": "RIA",
        "max_project_duration_months": 48,
    }), encoding="utf-8")


class TestDependencyNormalizerMigration:
    def test_dependency_normalizer_registered(self) -> None:
        assert "dependency_normalizer" in COMPONENT_REGISTRY

    def test_component_output_matches_direct_call(self, tmp_path: Path) -> None:
        """Invoking via the component path yields output identical (modulo the
        wall-clock timestamp) to calling normalize_dependencies directly."""
        _write_dep_fixtures(tmp_path)

        # Direct (legacy) path
        direct_path = normalize_dependencies("run-1", tmp_path)
        direct = json.loads(direct_path.read_text(encoding="utf-8"))

        # Generic component path (same run_id → same content modulo timestamp)
        record = invoke_component("dependency_normalizer", "run-1", tmp_path)
        assert record.status == "success"
        assert record.outputs_written == [OUTPUT_REL]

        via_component = json.loads(
            (tmp_path / OUTPUT_REL).read_text(encoding="utf-8")
        )

        direct.pop("normalization_timestamp", None)
        via_component.pop("normalization_timestamp", None)
        assert via_component == direct

    def test_component_failure_on_missing_inputs(self, tmp_path: Path) -> None:
        """No fixtures on disk → the normalizer raises → failure record."""
        record = invoke_component("dependency_normalizer", "run-1", tmp_path)
        assert record.status == "failure"
        assert record.failure_reason


# ---------------------------------------------------------------------------
# canonical_pack_deriver registration (ticket 10)
# ---------------------------------------------------------------------------


def _write_pack_fixtures(tmp_path: Path) -> None:
    """Minimal Tier 3/4 fixtures for the canonical pack deriver."""
    base = tmp_path / "docs"
    obj = base / "tier3_project_instantiation" / "architecture_inputs" / "objectives.json"
    obj.parent.mkdir(parents=True, exist_ok=True)
    obj.write_text(json.dumps({
        "objectives": [{"id": "OBJ-1", "title": "T", "measurable_target": "x"}],
    }), encoding="utf-8")
    wp = base / "tier4_orchestration_state" / "phase_outputs" / "phase3_wp_design" / "wp_structure.json"
    wp.parent.mkdir(parents=True, exist_ok=True)
    wp.write_text(json.dumps({
        "work_packages": [{"wp_id": "WP1", "title": "Mgmt", "lead_partner": "P1",
                           "deliverables": [{"deliverable_id": "D1-01", "title": "d", "due_month": 3}]}],
    }), encoding="utf-8")
    partners = base / "tier3_project_instantiation" / "consortium" / "partners.json"
    partners.parent.mkdir(parents=True, exist_ok=True)
    partners.write_text(json.dumps({
        "partners": [{"short_name": "P1", "legal_name": "Partner One"}],
    }), encoding="utf-8")


class TestCanonicalPackDeriverComponent:
    def test_canonical_pack_deriver_registered(self) -> None:
        assert "canonical_pack_deriver" in COMPONENT_REGISTRY

    def test_component_writes_pack_via_generic_path(self, tmp_path: Path) -> None:
        """Invoking via the component path writes the canonical pack and
        records its repo-relative output."""
        from runner.phase8_canonical_pack import CANONICAL_PACK_REL

        _write_pack_fixtures(tmp_path)
        record = invoke_component("canonical_pack_deriver", "run-1", tmp_path)
        assert record.status == "success"
        assert record.outputs_written == [CANONICAL_PACK_REL]
        assert (tmp_path / CANONICAL_PACK_REL).is_file()

    def test_component_fails_closed_on_malformed_assumptions(
        self, tmp_path: Path
    ) -> None:
        """A malformed working_assumptions.json → the deriver raises → failure
        record (never propagates)."""
        from runner.working_assumptions import WORKING_ASSUMPTIONS_REL

        _write_pack_fixtures(tmp_path)
        wa = tmp_path / WORKING_ASSUMPTIONS_REL
        wa.parent.mkdir(parents=True, exist_ok=True)
        # Real declarations but missing the mandatory provenance_class.
        wa.write_text(json.dumps({
            "declarations": [{"key": "k", "value": "v", "declared_by": "o",
                              "declared_on": "2026-07-14"}],
        }), encoding="utf-8")
        record = invoke_component("canonical_pack_deriver", "run-1", tmp_path)
        assert record.status == "failure"
        assert "provenance_class" in (record.failure_reason or "")


# ---------------------------------------------------------------------------
# checkpoint_publisher registration (CHK-1)
# ---------------------------------------------------------------------------


def _write_checkpoint_gate_fixtures(tmp_path: Path, run_id: str) -> None:
    """Write the six confirmed gate results with a uniform run_id."""
    from runner.checkpoint_publisher import CONFIRMED_GATE_IDS
    from runner.gate_result_registry import (
        GATE_RESULT_PATHS,
        GATE_RESULT_SCHEMA_ID,
    )

    for gate_id in CONFIRMED_GATE_IDS:
        path = (
            tmp_path / "docs" / "tier4_orchestration_state"
            / GATE_RESULT_PATHS[gate_id]
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "schema_id": GATE_RESULT_SCHEMA_ID,
            "gate_id": gate_id,
            "run_id": run_id,
            "status": "pass",
            "manifest_version": "1.1",
            "library_version": "1.0",
            "constitution_version": "21430b0",
            "input_fingerprint": "sha256:abc",
            "evaluated_at": "2026-07-16T00:00:00+00:00",
        }), encoding="utf-8")


class TestCheckpointPublisherComponent:
    def test_checkpoint_publisher_registered(self) -> None:
        assert "checkpoint_publisher" in COMPONENT_REGISTRY

    def test_not_a_draft_consuming_component(self) -> None:
        """checkpoint_publisher does not read section_drafts/ — must not be
        suppressed when the drafting skill is skipped."""
        from runner.deterministic_components import DRAFT_CONSUMING_COMPONENTS

        assert "checkpoint_publisher" not in DRAFT_CONSUMING_COMPONENTS

    def test_component_writes_checkpoint_via_generic_path(
        self, tmp_path: Path
    ) -> None:
        from runner.checkpoint_publisher import CHECKPOINT_REL

        _write_checkpoint_gate_fixtures(tmp_path, "run-1")
        record = invoke_component("checkpoint_publisher", "run-1", tmp_path)
        assert record.status == "success"
        assert record.outputs_written == [CHECKPOINT_REL]
        assert (tmp_path / CHECKPOINT_REL).is_file()

    def test_component_fails_closed_on_unauthorized_cross_run(
        self, tmp_path: Path
    ) -> None:
        """A cross-run gate with no acceptance record → the publisher raises →
        failure record (never propagates)."""
        from runner.checkpoint_publisher import CHECKPOINT_REL

        _write_checkpoint_gate_fixtures(tmp_path, "run-1")
        # Rewrite gate_09 to carry a prior run_id with no acceptance record.
        from runner.gate_result_registry import (
            GATE_RESULT_PATHS,
            GATE_RESULT_SCHEMA_ID,
        )

        g09 = (
            tmp_path / "docs" / "tier4_orchestration_state"
            / GATE_RESULT_PATHS["gate_09_budget_consistency"]
        )
        g09.write_text(json.dumps({
            "schema_id": GATE_RESULT_SCHEMA_ID,
            "gate_id": "gate_09_budget_consistency",
            "run_id": "prior-run",
            "status": "pass",
            "manifest_version": "1.1",
            "library_version": "1.0",
            "constitution_version": "21430b0",
            "input_fingerprint": "sha256:abc",
            "evaluated_at": "2026-07-16T00:00:00+00:00",
        }), encoding="utf-8")

        record = invoke_component("checkpoint_publisher", "run-1", tmp_path)
        assert record.status == "failure"
        assert record.failure_reason
        assert not (tmp_path / CHECKPOINT_REL).is_file()
