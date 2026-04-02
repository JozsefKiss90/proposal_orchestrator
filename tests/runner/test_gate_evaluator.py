"""
Unit tests for Step 10 — runner/gate_evaluator.py.

Tests cover:
    - Deterministic gate evaluation (pass / fail / multi-failure collection)
    - GateResult writing and mandatory-field presence
    - Canonical gate-result path resolution
    - Node-state transitions (entry / exit / pass)
    - Semantic-pending boundary (non-false-pass)
    - HARD_BLOCK for gate_09_budget_consistency
    - Input fingerprinting (stable / change-sensitive)
    - artifact_owned_by_run integration (via evaluate_gate and directly)

All tests use synthetic temporary directories as the repo root and a
synthetic gate_rules_library.yaml passed via the library_path kwarg.
No live repository artifacts are read or mutated.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

import pytest
import yaml

from runner.gate_evaluator import (
    PREDICATE_REGISTRY,
    _compute_fingerprints,
    _fingerprint_path,
    _substitute_runtime_args,
    evaluate_gate,
)
from runner.gate_result_registry import GATE_RESULT_PATHS
from runner.predicates.file_predicates import artifact_owned_by_run
from runner.predicates.types import MISSING_MANDATORY_INPUT, STALE_UPSTREAM_MISMATCH
from runner.run_context import PHASE_8_NODE_IDS, RunContext
from runner.versions import MANIFEST_VERSION


# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------

_LIB_VERSION = "1.0"
_CONST_VERSION = "abc1234"

# Synthetic gate IDs (not in GATE_RESULT_PATHS → fallback path)
_GATE_PASS = "gate_synth_pass"
_GATE_FAIL = "gate_synth_fail"
_GATE_MULTI = "gate_synth_multi_fail"
_GATE_ENTRY = "gate_synth_entry_fail"
_GATE_SEM = "gate_synth_semantic"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run_id() -> str:
    return str(uuid.uuid4())


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _write_library(tmp_path: Path, gates: list[dict]) -> Path:
    """Write a synthetic gate_rules_library.yaml and return its path."""
    lib_data = {
        "library_version": _LIB_VERSION,
        "manifest_version": MANIFEST_VERSION,
        "constitution_version": _CONST_VERSION,
        "gate_rules": gates,
    }
    lib_path = tmp_path / "gate_rules_library.yaml"
    lib_path.write_text(yaml.dump(lib_data), encoding="utf-8")
    return lib_path


def _exists_pred(path_str: str) -> dict:
    """Return a synthetic 'exists' file predicate targeting *path_str*."""
    return {
        "predicate_id": f"p_exists_{path_str.replace('/', '_')}",
        "type": "file",
        "function": "exists",
        "args": {"path": path_str},
        "prose_condition": "Path exists",
        "fail_message": "Required path is missing",
    }


def _semantic_pred() -> dict:
    """Return a synthetic semantic predicate stub."""
    return {
        "predicate_id": "p_sem_quality",
        "type": "semantic",
        "function": "agent_quality_check",
        "args": {},
        "prose_condition": "Quality meets bar",
        "fail_message": "Quality check failed",
    }


def _gate_entry(
    gate_id: str,
    gate_kind: str = "exit",
    evaluated_at: str | None = None,
    predicates: list | None = None,
    **extras,
) -> dict:
    gate: dict = {
        "gate_id": gate_id,
        "gate_kind": gate_kind,
        "evaluated_at": evaluated_at or f"n01 {gate_kind}",
        "predicates": predicates or [],
    }
    gate.update(extras)
    return gate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_root(tmp_path: Path) -> Path:
    """A temp directory acting as the repository root."""
    return tmp_path


@pytest.fixture
def run_id() -> str:
    return _make_run_id()


# ---------------------------------------------------------------------------
# Helpers to read a written GateResult
# ---------------------------------------------------------------------------


def _fallback_result_path(gate_id: str, repo_root: Path) -> Path:
    return (
        repo_root
        / "docs/tier4_orchestration_state/gate_results"
        / f"{gate_id}.json"
    )


def _canonical_result_path(gate_id: str, repo_root: Path) -> Path:
    return (
        repo_root / "docs/tier4_orchestration_state" / GATE_RESULT_PATHS[gate_id]
    )


# ---------------------------------------------------------------------------
# _substitute_runtime_args
# ---------------------------------------------------------------------------


class TestSubstituteRuntimeArgs:
    def test_replaces_run_id_in_string_value(self) -> None:
        args = {"path": "some/${run_id}/artifact.json"}
        result = _substitute_runtime_args(args, "my-run-42")
        assert result["path"] == "some/my-run-42/artifact.json"

    def test_replaces_run_id_in_list_values(self) -> None:
        args = {"paths": ["a/${run_id}", "b/${run_id}"]}
        result = _substitute_runtime_args(args, "X")
        assert result["paths"] == ["a/X", "b/X"]

    def test_non_string_values_passed_through(self) -> None:
        args = {"flag": True, "count": 42}
        result = _substitute_runtime_args(args, "irrelevant")
        assert result["flag"] is True
        assert result["count"] == 42

    def test_no_placeholder_unchanged(self) -> None:
        args = {"path": "some/static/path.json"}
        result = _substitute_runtime_args(args, "whatever")
        assert result["path"] == "some/static/path.json"


# ---------------------------------------------------------------------------
# Fingerprinting
# ---------------------------------------------------------------------------


class TestFingerprinting:
    def test_fingerprint_path_missing_file_returns_sentinel(
        self, tmp_path: Path
    ) -> None:
        fp = _fingerprint_path(tmp_path / "nonexistent.json")
        assert fp == "sha256:MISSING"

    def test_fingerprint_path_existing_file_returns_sha256(
        self, tmp_path: Path
    ) -> None:
        f = tmp_path / "artifact.json"
        f.write_text('{"key": "value"}', encoding="utf-8")
        fp = _fingerprint_path(f)
        expected = "sha256:" + hashlib.sha256(f.read_bytes()).hexdigest()
        assert fp == expected

    def test_fingerprint_path_directory_fingerprints_children(
        self, tmp_path: Path
    ) -> None:
        d = tmp_path / "dir"
        d.mkdir()
        (d / "a.txt").write_text("hello", encoding="utf-8")
        (d / "b.txt").write_text("world", encoding="utf-8")
        fp = _fingerprint_path(d)
        assert fp.startswith("sha256:")
        assert fp != "sha256:MISSING"

    def test_combined_fingerprint_stable_for_same_inputs(
        self, tmp_path: Path
    ) -> None:
        f = tmp_path / "art.json"
        f.write_text('{"x": 1}', encoding="utf-8")
        per1, combined1 = _compute_fingerprints(["art.json"], tmp_path)
        per2, combined2 = _compute_fingerprints(["art.json"], tmp_path)
        assert combined1 == combined2
        assert per1 == per2

    def test_combined_fingerprint_changes_when_input_changes(
        self, tmp_path: Path
    ) -> None:
        f = tmp_path / "art.json"
        f.write_text('{"x": 1}', encoding="utf-8")
        _, combined1 = _compute_fingerprints(["art.json"], tmp_path)
        f.write_text('{"x": 2}', encoding="utf-8")
        _, combined2 = _compute_fingerprints(["art.json"], tmp_path)
        assert combined1 != combined2

    def test_per_artifact_fingerprints_in_gate_result(
        self, tmp_path: Path, run_id: str
    ) -> None:
        """evaluate_gate writes input_artifact_fingerprints in the result."""
        # Create a file to fingerprint
        art = tmp_path / "docs/tier1_normative_framework/source.json"
        _write_json(art, {"x": 1})

        # Gate that passes (exists check on a file we create)
        marker = tmp_path / "marker.json"
        _write_json(marker, {"run_id": run_id})

        lib_path = _write_library(
            tmp_path,
            [
                _gate_entry(
                    _GATE_PASS,
                    gate_kind="exit",
                    evaluated_at="n01 exit",
                    predicates=[_exists_pred("marker.json")],
                )
            ],
        )
        result = evaluate_gate(_GATE_PASS, run_id, tmp_path, library_path=lib_path)
        # The result always contains these keys (may be empty dicts for unknown gates)
        assert "input_fingerprint" in result
        assert "input_artifact_fingerprints" in result
        assert isinstance(result["input_artifact_fingerprints"], dict)


# ---------------------------------------------------------------------------
# Deterministic gate evaluation — pass
# ---------------------------------------------------------------------------


class TestEvaluateGatePass:
    def test_pass_when_all_deterministic_predicates_pass(
        self, tmp_path: Path, run_id: str
    ) -> None:
        target = tmp_path / "myfile.json"
        _write_json(target, {"a": 1})
        lib_path = _write_library(
            tmp_path,
            [
                _gate_entry(
                    _GATE_PASS,
                    gate_kind="exit",
                    evaluated_at="n01 exit",
                    predicates=[_exists_pred("myfile.json")],
                )
            ],
        )
        result = evaluate_gate(_GATE_PASS, run_id, tmp_path, library_path=lib_path)
        assert result["status"] == "pass"

    def test_gate_result_written_to_disk(self, tmp_path: Path, run_id: str) -> None:
        target = tmp_path / "myfile.json"
        _write_json(target, {})
        lib_path = _write_library(
            tmp_path,
            [_gate_entry(_GATE_PASS, predicates=[_exists_pred("myfile.json")])],
        )
        evaluate_gate(_GATE_PASS, run_id, tmp_path, library_path=lib_path)
        written = _fallback_result_path(_GATE_PASS, tmp_path)
        assert written.exists()
        content = json.loads(written.read_text())
        assert content["status"] == "pass"

    def test_gate_result_contains_mandatory_fields(
        self, tmp_path: Path, run_id: str
    ) -> None:
        target = tmp_path / "f.json"
        _write_json(target, {})
        lib_path = _write_library(
            tmp_path,
            [_gate_entry(_GATE_PASS, predicates=[_exists_pred("f.json")])],
        )
        result = evaluate_gate(_GATE_PASS, run_id, tmp_path, library_path=lib_path)
        mandatory = [
            "gate_id",
            "gate_kind",
            "run_id",
            "manifest_version",
            "library_version",
            "constitution_version",
            "input_fingerprint",
            "input_artifact_fingerprints",
            "evaluated_at",
            "status",
            "deterministic_predicates",
            "semantic_predicates",
            "skipped_semantic",
            "report_written_to",
        ]
        for field in mandatory:
            assert field in result, f"Missing mandatory field: {field!r}"

    def test_gate_result_ids_match_input(self, tmp_path: Path, run_id: str) -> None:
        target = tmp_path / "f.json"
        _write_json(target, {})
        lib_path = _write_library(
            tmp_path,
            [_gate_entry(_GATE_PASS, predicates=[_exists_pred("f.json")])],
        )
        result = evaluate_gate(_GATE_PASS, run_id, tmp_path, library_path=lib_path)
        assert result["gate_id"] == _GATE_PASS
        assert result["run_id"] == run_id

    def test_result_path_uses_fallback_for_unknown_gate_id(
        self, tmp_path: Path, run_id: str
    ) -> None:
        target = tmp_path / "f.json"
        _write_json(target, {})
        lib_path = _write_library(
            tmp_path,
            [_gate_entry(_GATE_PASS, predicates=[_exists_pred("f.json")])],
        )
        result = evaluate_gate(_GATE_PASS, run_id, tmp_path, library_path=lib_path)
        expected = str(_fallback_result_path(_GATE_PASS, tmp_path))
        assert result["report_written_to"] == expected

    def test_result_path_uses_canonical_registry_path_for_known_gate(
        self, tmp_path: Path, run_id: str
    ) -> None:
        """For a gate_id in GATE_RESULT_PATHS, the canonical path is used."""
        known_gate_id = "phase_01_gate"
        lib_path = _write_library(
            tmp_path,
            [
                _gate_entry(
                    known_gate_id,
                    gate_kind="exit",
                    evaluated_at="n01 exit",
                    predicates=[],
                )
            ],
        )
        result = evaluate_gate(known_gate_id, run_id, tmp_path, library_path=lib_path)
        expected = str(_canonical_result_path(known_gate_id, tmp_path))
        assert result["report_written_to"] == expected


# ---------------------------------------------------------------------------
# Deterministic gate evaluation — fail
# ---------------------------------------------------------------------------


class TestEvaluateGateFail:
    def test_fail_when_deterministic_predicate_fails(
        self, tmp_path: Path, run_id: str
    ) -> None:
        # Do NOT create the target file → exists predicate will fail
        lib_path = _write_library(
            tmp_path,
            [_gate_entry(_GATE_FAIL, predicates=[_exists_pred("missing.json")])],
        )
        result = evaluate_gate(_GATE_FAIL, run_id, tmp_path, library_path=lib_path)
        assert result["status"] == "fail"

    def test_fail_gate_result_written_to_disk(self, tmp_path: Path, run_id: str) -> None:
        lib_path = _write_library(
            tmp_path,
            [_gate_entry(_GATE_FAIL, predicates=[_exists_pred("missing.json")])],
        )
        evaluate_gate(_GATE_FAIL, run_id, tmp_path, library_path=lib_path)
        written = _fallback_result_path(_GATE_FAIL, tmp_path)
        assert written.exists()

    def test_fail_records_failed_predicate_details(
        self, tmp_path: Path, run_id: str
    ) -> None:
        lib_path = _write_library(
            tmp_path,
            [_gate_entry(_GATE_FAIL, predicates=[_exists_pred("missing.json")])],
        )
        result = evaluate_gate(_GATE_FAIL, run_id, tmp_path, library_path=lib_path)
        failed = result["deterministic_predicates"]["failed"]
        assert len(failed) == 1
        assert failed[0]["failure_category"] == MISSING_MANDATORY_INPUT

    def test_all_deterministic_failures_collected(
        self, tmp_path: Path, run_id: str
    ) -> None:
        """Multiple failing predicates are ALL collected — no fast-fail."""
        preds = [
            _exists_pred("absent_a.json"),
            _exists_pred("absent_b.json"),
            _exists_pred("absent_c.json"),
        ]
        lib_path = _write_library(
            tmp_path, [_gate_entry(_GATE_MULTI, predicates=preds)]
        )
        result = evaluate_gate(_GATE_MULTI, run_id, tmp_path, library_path=lib_path)
        assert result["status"] == "fail"
        assert len(result["deterministic_predicates"]["failed"]) == 3

    def test_fail_skips_semantic_evaluation(self, tmp_path: Path, run_id: str) -> None:
        preds = [_exists_pred("missing.json"), _semantic_pred()]
        lib_path = _write_library(
            tmp_path, [_gate_entry(_GATE_FAIL, predicates=preds)]
        )
        result = evaluate_gate(_GATE_FAIL, run_id, tmp_path, library_path=lib_path)
        assert result["status"] == "fail"
        assert result["skipped_semantic"] is True


# ---------------------------------------------------------------------------
# Node-state transitions
# ---------------------------------------------------------------------------


class TestNodeStateTransitions:
    def test_entry_gate_failure_sets_blocked_at_entry(
        self, tmp_path: Path, run_id: str
    ) -> None:
        lib_path = _write_library(
            tmp_path,
            [
                _gate_entry(
                    _GATE_ENTRY,
                    gate_kind="entry",
                    evaluated_at="n05 entry",
                    predicates=[_exists_pred("missing.json")],
                )
            ],
        )
        evaluate_gate(_GATE_ENTRY, run_id, tmp_path, library_path=lib_path)
        ctx = RunContext.load(tmp_path, run_id)
        assert ctx.get_node_state("n05") == "blocked_at_entry"

    def test_exit_gate_failure_sets_blocked_at_exit(
        self, tmp_path: Path, run_id: str
    ) -> None:
        lib_path = _write_library(
            tmp_path,
            [
                _gate_entry(
                    _GATE_FAIL,
                    gate_kind="exit",
                    evaluated_at="n03 exit",
                    predicates=[_exists_pred("missing.json")],
                )
            ],
        )
        evaluate_gate(_GATE_FAIL, run_id, tmp_path, library_path=lib_path)
        ctx = RunContext.load(tmp_path, run_id)
        assert ctx.get_node_state("n03") == "blocked_at_exit"

    def test_deterministic_pass_sets_released(
        self, tmp_path: Path, run_id: str
    ) -> None:
        target = tmp_path / "present.json"
        _write_json(target, {})
        lib_path = _write_library(
            tmp_path,
            [
                _gate_entry(
                    _GATE_PASS,
                    gate_kind="exit",
                    evaluated_at="n02 exit",
                    predicates=[_exists_pred("present.json")],
                )
            ],
        )
        evaluate_gate(_GATE_PASS, run_id, tmp_path, library_path=lib_path)
        ctx = RunContext.load(tmp_path, run_id)
        assert ctx.get_node_state("n02") == "released"

    def test_node_state_persisted_to_manifest(
        self, tmp_path: Path, run_id: str
    ) -> None:
        lib_path = _write_library(
            tmp_path,
            [
                _gate_entry(
                    _GATE_FAIL,
                    gate_kind="exit",
                    evaluated_at="n04 exit",
                    predicates=[_exists_pred("missing.json")],
                )
            ],
        )
        evaluate_gate(_GATE_FAIL, run_id, tmp_path, library_path=lib_path)
        # Load context from disk (not in-memory)
        ctx = RunContext.load(tmp_path, run_id)
        assert ctx.get_node_state("n04") == "blocked_at_exit"


# ---------------------------------------------------------------------------
# Semantic-pending boundary
# ---------------------------------------------------------------------------


class TestSemanticPendingBoundary:
    def test_semantic_predicates_not_invoked_when_deterministic_passes(
        self, tmp_path: Path, run_id: str
    ) -> None:
        target = tmp_path / "f.json"
        _write_json(target, {})
        lib_path = _write_library(
            tmp_path,
            [
                _gate_entry(
                    _GATE_SEM,
                    gate_kind="exit",
                    evaluated_at="n01 exit",
                    predicates=[_exists_pred("f.json"), _semantic_pred()],
                )
            ],
        )
        result = evaluate_gate(_GATE_SEM, run_id, tmp_path, library_path=lib_path)
        # Status must NOT be "pass" — semantic predicates exist but aren't evaluated
        assert result["status"] == "semantic_evaluation_pending"

    def test_semantic_pending_status_is_not_false_pass(
        self, tmp_path: Path, run_id: str
    ) -> None:
        target = tmp_path / "f.json"
        _write_json(target, {})
        lib_path = _write_library(
            tmp_path,
            [
                _gate_entry(
                    _GATE_SEM,
                    predicates=[_exists_pred("f.json"), _semantic_pred()],
                )
            ],
        )
        result = evaluate_gate(_GATE_SEM, run_id, tmp_path, library_path=lib_path)
        assert result["status"] != "pass"

    def test_semantic_pending_node_state(self, tmp_path: Path, run_id: str) -> None:
        target = tmp_path / "f.json"
        _write_json(target, {})
        lib_path = _write_library(
            tmp_path,
            [
                _gate_entry(
                    _GATE_SEM,
                    gate_kind="exit",
                    evaluated_at="n06 exit",
                    predicates=[_exists_pred("f.json"), _semantic_pred()],
                )
            ],
        )
        evaluate_gate(_GATE_SEM, run_id, tmp_path, library_path=lib_path)
        ctx = RunContext.load(tmp_path, run_id)
        assert ctx.get_node_state("n06") == "deterministic_pass_semantic_pending"

    def test_semantic_pending_result_records_pending_predicate_ids(
        self, tmp_path: Path, run_id: str
    ) -> None:
        target = tmp_path / "f.json"
        _write_json(target, {})
        lib_path = _write_library(
            tmp_path,
            [
                _gate_entry(
                    _GATE_SEM,
                    predicates=[_exists_pred("f.json"), _semantic_pred()],
                )
            ],
        )
        result = evaluate_gate(_GATE_SEM, run_id, tmp_path, library_path=lib_path)
        sem_section = result["semantic_predicates"]
        assert "pending" in sem_section
        assert "p_sem_quality" in sem_section["pending"]


# ---------------------------------------------------------------------------
# HARD_BLOCK (gate_09_budget_consistency)
# ---------------------------------------------------------------------------


class TestHardBlock:
    def _make_gate09_gate(self, received_path: str) -> dict:
        return {
            "gate_id": "gate_09_budget_consistency",
            "gate_kind": "exit",
            "evaluated_at": "n07 exit",
            "hard_block_on_missing_received_dir": True,
            "predicates": [
                {
                    "predicate_id": "p_received_dir",
                    "type": "file",
                    "function": "dir_non_empty",
                    "args": {"path": received_path},
                    "prose_condition": "Budget received dir is non-empty",
                    "fail_message": "No budget received",
                }
            ],
        }

    def test_gate09_missing_received_dir_produces_hard_block_in_result(
        self, tmp_path: Path, run_id: str
    ) -> None:
        received_rel = "docs/integrations/lump_sum_budget_planner/received"
        # Deliberately do NOT create the received/ dir
        lib_path = _write_library(
            tmp_path, [self._make_gate09_gate(received_rel)]
        )
        result = evaluate_gate(
            "gate_09_budget_consistency", run_id, tmp_path, library_path=lib_path
        )
        assert result.get("hard_block") is True

    def test_gate09_hard_block_freezes_phase8_nodes(
        self, tmp_path: Path, run_id: str
    ) -> None:
        received_rel = "docs/integrations/lump_sum_budget_planner/received"
        lib_path = _write_library(
            tmp_path, [self._make_gate09_gate(received_rel)]
        )
        evaluate_gate(
            "gate_09_budget_consistency", run_id, tmp_path, library_path=lib_path
        )
        ctx = RunContext.load(tmp_path, run_id)
        for node_id in PHASE_8_NODE_IDS:
            assert ctx.get_node_state(node_id) == "hard_block_upstream", (
                f"Expected hard_block_upstream for {node_id}"
            )

    def test_gate09_hard_block_downstream_reason_in_manifest(
        self, tmp_path: Path, run_id: str
    ) -> None:
        received_rel = "docs/integrations/lump_sum_budget_planner/received"
        lib_path = _write_library(
            tmp_path, [self._make_gate09_gate(received_rel)]
        )
        evaluate_gate(
            "gate_09_budget_consistency", run_id, tmp_path, library_path=lib_path
        )
        ctx = RunContext.load(tmp_path, run_id)
        manifest = ctx.to_dict()
        assert "hard_block_reason" in manifest
        assert manifest["hard_block_gate"] == "gate_09_budget_consistency"

    def test_gate09_no_hard_block_when_received_dir_present(
        self, tmp_path: Path, run_id: str
    ) -> None:
        received_rel = "docs/integrations/lump_sum_budget_planner/received"
        received_abs = tmp_path / received_rel
        received_abs.mkdir(parents=True)
        (received_abs / "response.json").write_text('{"ok": true}', encoding="utf-8")

        lib_path = _write_library(
            tmp_path, [self._make_gate09_gate(received_rel)]
        )
        result = evaluate_gate(
            "gate_09_budget_consistency", run_id, tmp_path, library_path=lib_path
        )
        assert result.get("hard_block") is not True


# ---------------------------------------------------------------------------
# artifact_owned_by_run predicate (direct and via evaluate_gate)
# ---------------------------------------------------------------------------


class TestArtifactOwnedByRun:
    def test_current_run_artifact_passes(self, tmp_path: Path) -> None:
        run_id = _make_run_id()
        art = tmp_path / "artifact.json"
        _write_json(art, {"run_id": run_id, "data": "hello"})
        result = artifact_owned_by_run(art, run_id, repo_root=tmp_path)
        assert result.passed

    def test_mismatched_run_id_fails_stale(self, tmp_path: Path) -> None:
        art = tmp_path / "artifact.json"
        _write_json(art, {"run_id": "old-run-id", "data": "hello"})
        result = artifact_owned_by_run(art, "new-run-id", repo_root=tmp_path)
        assert not result.passed
        assert result.failure_category == STALE_UPSTREAM_MISMATCH

    def test_approved_inherited_artifact_passes(self, tmp_path: Path) -> None:
        art = tmp_path / "artifact.json"
        _write_json(art, {"run_id": "old-run-id", "data": "inherited"})

        policy = tmp_path / "reuse_policy.json"
        _write_json(policy, {"approved_artifacts": [str(art)]})

        result = artifact_owned_by_run(
            art, "new-run-id", reuse_policy_path=policy, repo_root=tmp_path
        )
        assert result.passed
        assert result.details.get("approved_via_reuse_policy") is True

    def test_missing_artifact_fails_missing_mandatory_input(
        self, tmp_path: Path
    ) -> None:
        art = tmp_path / "nonexistent.json"
        result = artifact_owned_by_run(art, "some-run", repo_root=tmp_path)
        assert not result.passed
        assert result.failure_category == MISSING_MANDATORY_INPUT

    def test_artifact_owned_by_run_via_evaluate_gate(
        self, tmp_path: Path
    ) -> None:
        """Smoke-test the predicate dispatched through evaluate_gate."""
        run_id = _make_run_id()
        art_rel = "docs/tier4_orchestration_state/phase_outputs/phase1/output.json"
        art_abs = tmp_path / art_rel
        _write_json(art_abs, {"run_id": run_id, "content": "ok"})

        gate_id = "gate_synth_ownership"
        lib_path = _write_library(
            tmp_path,
            [
                _gate_entry(
                    gate_id,
                    gate_kind="exit",
                    evaluated_at="n01 exit",
                    predicates=[
                        {
                            "predicate_id": "p_ownership",
                            "type": "file",
                            "function": "artifact_owned_by_run",
                            "args": {
                                "path": art_rel,
                                "run_id": "${run_id}",
                            },
                            "prose_condition": "Artifact belongs to current run",
                            "fail_message": "Stale artifact",
                        }
                    ],
                )
            ],
        )
        result = evaluate_gate(gate_id, run_id, tmp_path, library_path=lib_path)
        assert result["status"] == "pass"


# ---------------------------------------------------------------------------
# Predicate registry completeness
# ---------------------------------------------------------------------------


class TestPredicateRegistry:
    def test_registry_contains_expected_predicates(self) -> None:
        expected = [
            "exists",
            "non_empty",
            "non_empty_json",
            "dir_non_empty",
            "artifact_owned_by_run",
            "gate_pass_recorded",
            "json_field_present",
            "json_fields_present",
            "no_dependency_cycles",
            "timeline_within_duration",
            "all_milestones_have_criteria",
            "wp_count_within_limit",
            "critical_path_present",
        ]
        for name in expected:
            assert name in PREDICATE_REGISTRY, (
                f"Missing predicate in registry: {name!r}"
            )

    def test_unknown_predicate_returns_failing_result(
        self, tmp_path: Path, run_id: str
    ) -> None:
        lib_path = _write_library(
            tmp_path,
            [
                _gate_entry(
                    "gate_synth_unknown_pred",
                    predicates=[
                        {
                            "predicate_id": "p_bad",
                            "type": "file",
                            "function": "nonexistent_function_xyz",
                            "args": {},
                        }
                    ],
                )
            ],
        )
        result = evaluate_gate(
            "gate_synth_unknown_pred", run_id, tmp_path, library_path=lib_path
        )
        assert result["status"] == "fail"
        failed = result["deterministic_predicates"]["failed"]
        assert any(
            "nonexistent_function_xyz" in (f.get("function") or "")
            for f in failed
        )
