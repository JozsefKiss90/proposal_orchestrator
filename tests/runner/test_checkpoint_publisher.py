"""
Tests for the ``checkpoint_publisher`` deterministic component (CHK-1).

This replaces the retired ``checkpoint-publish`` skill spec tests
(``test_checkpoint_publish_spec.py``).  The component
(``runner/checkpoint_publisher.py``) writes the whole Phase-8 checkpoint —
including the authorized cross-run provenance quad — as a pure-Python,
Claude-free node-body pass (CLAUDE.md §17.5.3 / C2).

Coverage (handoff §7):
  * all-current-run → checkpoint written, no quad, valid.
  * bootstrapped gate_09 with an accepted_upstream_gates entry → quad
    recorded correctly (verbatim copy of the durable gate result's fields).
  * cross-run gate NOT in accepted_upstream_gates → raises (fail closed).
  * cross-run gate with a MISMATCHED acceptance record → raises (fail closed).
  * write-once guard: existing published checkpoint → raises.
  * missing / non-pass / wrong-schema gate → raises.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.checkpoint_publisher import (
    CHECKPOINT_REL,
    CHECKPOINT_SCHEMA_ID,
    CONFIRMED_GATE_IDS,
    CheckpointPublishError,
    publish_checkpoint,
)
from runner.gate_result_registry import GATE_RESULT_PATHS, GATE_RESULT_SCHEMA_ID
from runner.predicates.schema_predicates import checkpoint_published
from runner.run_context import RunContext

_TIER4_ROOT_REL = "docs/tier4_orchestration_state"
_CURRENT = "current-run-id"
_PRIOR = "prior-run-id"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_gate(
    repo_root: Path,
    gate_id: str,
    run_id: str = _CURRENT,
    *,
    status: str = "pass",
    schema_id: str = GATE_RESULT_SCHEMA_ID,
    input_fingerprint: str = "sha256:deadbeef",
    manifest_version: str = "1.1",
    library_version: str = "1.0",
    constitution_version: str = "21430b0",
) -> Path:
    """Write a canonical gate result artifact to Tier 4."""
    rel = GATE_RESULT_PATHS[gate_id]
    abs_path = repo_root / _TIER4_ROOT_REL / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "schema_id": schema_id,
        "gate_id": gate_id,
        "run_id": run_id,
        "manifest_version": manifest_version,
        "library_version": library_version,
        "constitution_version": constitution_version,
        "input_fingerprint": input_fingerprint,
        "evaluated_at": "2026-07-16T22:36:25+00:00",
        "status": status,
    }
    abs_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return abs_path


def _write_all_gates(repo_root: Path, run_id: str = _CURRENT) -> None:
    """Write all six confirmed gate results with the same run_id (all-current)."""
    for gate_id in CONFIRMED_GATE_IDS:
        _write_gate(repo_root, gate_id, run_id)


def _record_acceptance(
    repo_root: Path,
    run_id: str,
    gate_id: str,
    original_run_id: str,
) -> None:
    """Seed an accepted_upstream_gates record in the run manifest."""
    ctx = RunContext.initialize(repo_root, run_id)
    evidence_path = f"{_TIER4_ROOT_REL}/{GATE_RESULT_PATHS[gate_id]}"
    ctx.record_accepted_upstream_gate(
        gate_id=gate_id,
        original_run_id=original_run_id,
        evidence_path=evidence_path,
    )
    ctx.save()


def _read_checkpoint(repo_root: Path) -> dict:
    return json.loads((repo_root / CHECKPOINT_REL).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. All-current-run happy path (no quad)
# ---------------------------------------------------------------------------


class TestAllCurrentRun:
    def test_checkpoint_written_no_quad(self, tmp_path: Path):
        _write_all_gates(tmp_path, _CURRENT)

        out = publish_checkpoint(_CURRENT, tmp_path)

        assert out == tmp_path / CHECKPOINT_REL
        cp = _read_checkpoint(tmp_path)
        assert cp["schema_id"] == CHECKPOINT_SCHEMA_ID
        assert cp["run_id"] == _CURRENT
        assert cp["status"] == "published"
        assert cp["gate_results_confirmed"] == list(CONFIRMED_GATE_IDS)
        assert "published_at" in cp
        # Additive field omitted entirely for the all-current-run case.
        assert "inherited_gate_provenance" not in cp

    def test_no_run_manifest_needed_for_all_current(self, tmp_path: Path):
        """All-current-run must not require a run manifest on disk."""
        _write_all_gates(tmp_path, _CURRENT)
        # No RunContext initialized — there is no .claude/runs/<run_id>/.
        publish_checkpoint(_CURRENT, tmp_path)
        assert (tmp_path / CHECKPOINT_REL).is_file()

    def test_tier3_snapshot_present(self, tmp_path: Path):
        _write_all_gates(tmp_path, _CURRENT)
        # selected_call.json + partners.json present → snapshot populated.
        call_dir = tmp_path / "docs/tier3_project_instantiation/call_binding"
        call_dir.mkdir(parents=True, exist_ok=True)
        (call_dir / "selected_call.json").write_text(
            json.dumps({"call_id": "CALL-1", "topic_code": "TOPIC-1"}),
            encoding="utf-8",
        )
        cons_dir = tmp_path / "docs/tier3_project_instantiation/consortium"
        cons_dir.mkdir(parents=True, exist_ok=True)
        (cons_dir / "partners.json").write_text(
            json.dumps({"partners": [{"partner_id": "P1"}, {"partner_id": "P2"}]}),
            encoding="utf-8",
        )

        publish_checkpoint(_CURRENT, tmp_path)

        snap = _read_checkpoint(tmp_path)["tier3_snapshot"]
        assert snap["call_id"] == "CALL-1"
        assert snap["topic_id"] == "TOPIC-1"
        assert snap["partner_ids"] == ["P1", "P2"]

    def test_tier3_snapshot_absent_is_null(self, tmp_path: Path):
        _write_all_gates(tmp_path, _CURRENT)
        publish_checkpoint(_CURRENT, tmp_path)
        snap = _read_checkpoint(tmp_path)["tier3_snapshot"]
        assert snap["call_id"] is None
        assert snap["topic_id"] is None
        assert snap["partner_ids"] == []


# ---------------------------------------------------------------------------
# 2. Bootstrapped cross-run gate with an acceptance record → quad recorded
# ---------------------------------------------------------------------------


class TestBootstrappedQuad:
    def test_quad_recorded_for_bootstrapped_gate_09(self, tmp_path: Path):
        # gate_09 bootstrapped from a prior run; the phase-8 gates are current.
        gate09 = _write_gate(
            tmp_path,
            "gate_09_budget_consistency",
            _PRIOR,
            input_fingerprint="sha256:budgetfp",
            constitution_version="21430b0",
        )
        for gate_id in CONFIRMED_GATE_IDS[1:]:
            _write_gate(tmp_path, gate_id, _CURRENT)
        _record_acceptance(
            tmp_path, _CURRENT, "gate_09_budget_consistency", _PRIOR
        )

        publish_checkpoint(_CURRENT, tmp_path)

        cp = _read_checkpoint(tmp_path)
        assert cp["run_id"] == _CURRENT
        quad = cp["inherited_gate_provenance"]
        assert len(quad) == 1
        entry = quad[0]
        assert entry["gate_id"] == "gate_09_budget_consistency"
        assert entry["original_run_id"] == _PRIOR
        assert entry["evidence_path"] == (
            f"{_TIER4_ROOT_REL}/{GATE_RESULT_PATHS['gate_09_budget_consistency']}"
        )
        # Fields copied VERBATIM from the durable gate result.
        durable = json.loads(gate09.read_text(encoding="utf-8"))
        assert entry["input_fingerprint"] == durable["input_fingerprint"]
        assert entry["versions"] == {
            "manifest_version": durable["manifest_version"],
            "library_version": durable["library_version"],
            "constitution_version": durable["constitution_version"],
        }

    def test_only_cross_run_gates_get_a_quad_entry(self, tmp_path: Path):
        """A gate whose run_id matches the current run gets no quad entry."""
        _write_gate(tmp_path, "gate_09_budget_consistency", _PRIOR)
        for gate_id in CONFIRMED_GATE_IDS[1:]:
            _write_gate(tmp_path, gate_id, _CURRENT)
        _record_acceptance(
            tmp_path, _CURRENT, "gate_09_budget_consistency", _PRIOR
        )

        publish_checkpoint(_CURRENT, tmp_path)

        quad = _read_checkpoint(tmp_path)["inherited_gate_provenance"]
        assert [e["gate_id"] for e in quad] == ["gate_09_budget_consistency"]


# ---------------------------------------------------------------------------
# 3. Fail-closed on an unauthorized / mismatched cross-run gate
# ---------------------------------------------------------------------------


class TestFailClosedCrossRun:
    def test_cross_run_gate_without_acceptance_raises(self, tmp_path: Path):
        _write_gate(tmp_path, "gate_09_budget_consistency", _PRIOR)
        for gate_id in CONFIRMED_GATE_IDS[1:]:
            _write_gate(tmp_path, gate_id, _CURRENT)
        # A run manifest exists but records NO acceptance for gate_09.
        RunContext.initialize(tmp_path, _CURRENT).save()

        with pytest.raises(CheckpointPublishError):
            publish_checkpoint(_CURRENT, tmp_path)
        assert not (tmp_path / CHECKPOINT_REL).is_file()

    def test_cross_run_gate_no_run_manifest_raises(self, tmp_path: Path):
        _write_gate(tmp_path, "gate_09_budget_consistency", _PRIOR)
        for gate_id in CONFIRMED_GATE_IDS[1:]:
            _write_gate(tmp_path, gate_id, _CURRENT)
        # No run manifest at all → nothing can authorize the mismatch.
        with pytest.raises(CheckpointPublishError):
            publish_checkpoint(_CURRENT, tmp_path)
        assert not (tmp_path / CHECKPOINT_REL).is_file()

    def test_cross_run_gate_wrong_original_run_id_raises(self, tmp_path: Path):
        _write_gate(tmp_path, "gate_09_budget_consistency", _PRIOR)
        for gate_id in CONFIRMED_GATE_IDS[1:]:
            _write_gate(tmp_path, gate_id, _CURRENT)
        # Acceptance record names a DIFFERENT original run id.
        _record_acceptance(
            tmp_path, _CURRENT, "gate_09_budget_consistency", "some-other-run"
        )

        with pytest.raises(CheckpointPublishError):
            publish_checkpoint(_CURRENT, tmp_path)
        assert not (tmp_path / CHECKPOINT_REL).is_file()


# ---------------------------------------------------------------------------
# 4. Write-once guard
# ---------------------------------------------------------------------------


class TestWriteOnceGuard:
    def test_existing_published_checkpoint_raises(self, tmp_path: Path):
        _write_all_gates(tmp_path, _CURRENT)
        cp_path = tmp_path / CHECKPOINT_REL
        cp_path.parent.mkdir(parents=True, exist_ok=True)
        cp_path.write_text(
            json.dumps({"schema_id": CHECKPOINT_SCHEMA_ID, "status": "published"}),
            encoding="utf-8",
        )
        original = cp_path.read_text(encoding="utf-8")

        with pytest.raises(CheckpointPublishError):
            publish_checkpoint(_CURRENT, tmp_path)
        # The immutable checkpoint is untouched.
        assert cp_path.read_text(encoding="utf-8") == original

    def test_existing_non_published_checkpoint_is_overwritten(self, tmp_path: Path):
        """A stale non-published checkpoint does not block a fresh publish."""
        _write_all_gates(tmp_path, _CURRENT)
        cp_path = tmp_path / CHECKPOINT_REL
        cp_path.parent.mkdir(parents=True, exist_ok=True)
        cp_path.write_text(
            json.dumps({"status": "pending"}), encoding="utf-8"
        )

        publish_checkpoint(_CURRENT, tmp_path)
        assert _read_checkpoint(tmp_path)["status"] == "published"


# ---------------------------------------------------------------------------
# 5. Missing / non-pass / wrong-schema gate results
# ---------------------------------------------------------------------------


class TestGateValidation:
    def test_missing_gate_raises(self, tmp_path: Path):
        # Write only five of the six required gates.
        for gate_id in CONFIRMED_GATE_IDS[:-1]:
            _write_gate(tmp_path, gate_id, _CURRENT)
        with pytest.raises(CheckpointPublishError):
            publish_checkpoint(_CURRENT, tmp_path)
        assert not (tmp_path / CHECKPOINT_REL).is_file()

    def test_non_pass_gate_raises(self, tmp_path: Path):
        _write_all_gates(tmp_path, _CURRENT)
        _write_gate(tmp_path, "gate_11_review_closure", _CURRENT, status="fail")
        with pytest.raises(CheckpointPublishError):
            publish_checkpoint(_CURRENT, tmp_path)
        assert not (tmp_path / CHECKPOINT_REL).is_file()

    def test_wrong_schema_id_raises(self, tmp_path: Path):
        _write_all_gates(tmp_path, _CURRENT)
        _write_gate(
            tmp_path,
            "gate_10a_excellence_completeness",
            _CURRENT,
            schema_id="orch.gate_result.WRONG",
        )
        with pytest.raises(CheckpointPublishError):
            publish_checkpoint(_CURRENT, tmp_path)
        assert not (tmp_path / CHECKPOINT_REL).is_file()

    def test_malformed_gate_json_raises(self, tmp_path: Path):
        _write_all_gates(tmp_path, _CURRENT)
        bad = (
            tmp_path / _TIER4_ROOT_REL
            / GATE_RESULT_PATHS["gate_10b_impact_completeness"]
        )
        bad.write_text("{not json", encoding="utf-8")
        with pytest.raises(CheckpointPublishError):
            publish_checkpoint(_CURRENT, tmp_path)
        assert not (tmp_path / CHECKPOINT_REL).is_file()


# ---------------------------------------------------------------------------
# 6. End-to-end: component publishes → gate_12's checkpoint_published passes
#    (ticket CHK-1 acceptance criterion 5)
# ---------------------------------------------------------------------------


class TestComponentPredicateIntegration:
    def test_bootstrapped_under_fresh_run_id_e2e(self, tmp_path: Path):
        """The full CHK-1 loop: a fresh phase-8 run_id with a bootstrapped
        gate_09 → the component publishes a checkpoint with a provenance quad →
        the gate_12 checkpoint_published predicate accepts it."""
        # Bootstrap scenario: gate_09 from a prior run, phase-8 gates current.
        _write_gate(tmp_path, "gate_09_budget_consistency", _PRIOR)
        for gate_id in CONFIRMED_GATE_IDS[1:]:
            _write_gate(tmp_path, gate_id, _CURRENT)
        _record_acceptance(
            tmp_path, _CURRENT, "gate_09_budget_consistency", _PRIOR
        )

        # Component writes the checkpoint (node-body pass).
        publish_checkpoint(_CURRENT, tmp_path)

        # Predicate (gate_12) accepts the produced checkpoint + quad.
        result = checkpoint_published(
            tmp_path / CHECKPOINT_REL, repo_root=tmp_path
        )
        assert result.passed
        cp = _read_checkpoint(tmp_path)
        assert [e["gate_id"] for e in cp["inherited_gate_provenance"]] == [
            "gate_09_budget_consistency"
        ]

    def test_all_current_run_e2e(self, tmp_path: Path):
        """All-current-run: component writes no quad → predicate passes."""
        _write_all_gates(tmp_path, _CURRENT)
        publish_checkpoint(_CURRENT, tmp_path)
        result = checkpoint_published(
            tmp_path / CHECKPOINT_REL, repo_root=tmp_path
        )
        assert result.passed
        assert "inherited_gate_provenance" not in _read_checkpoint(tmp_path)
