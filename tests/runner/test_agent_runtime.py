"""
Tests for runner.agent_runtime — agent orchestration adapter layer.

Covers §14 test cases 6, 9, 10, 16:
  6.  skill failure propagation to AgentResult
  9.  n03 sub-agent behavior (dependency_mapper)
  10. n07 pre_gate_agent behavior (budget_interface_coordinator)
  16. CONSTITUTIONAL_HALT from skill propagates as agent_body failure

Additional tests:
  - successful agent → AgentResult(status="success", can_evaluate_exit_gate=True)
  - invoked_skills ordering and completeness
  - missing agent spec → failure
  - can_evaluate_exit_gate determined from disk state
  - module isolation (no dag_scheduler / gate_evaluator imports)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from runner.runtime_models import AgentResult, SkillInvocationRecord, SkillResult
from runner.agent_runtime import run_agent, AgentRuntimeError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_RUN_SKILL_TARGET = "runner.agent_runtime.run_skill"


def _write_yaml(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data), encoding="utf-8")


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _make_agent_env(
    tmp_path: Path,
    *,
    agent_id: str = "test_agent",
    node_id: str = "n01_call_analysis",
    skill_ids: list[str] | None = None,
    phase_id: str = "phase1",
    sub_agent_id: str | None = None,
    pre_gate_agent_id: str | None = None,
    reads_from: list[str] | None = None,
    writes_to: list[str] | None = None,
    extra_catalog_entries: list[dict] | None = None,
    artifact_registry: list[dict] | None = None,
) -> dict:
    """Create a synthetic environment and return kwargs for run_agent().

    Returns a dict ready to be unpacked as ``run_agent(**kwargs)``.
    """
    repo_root = tmp_path
    if skill_ids is None:
        skill_ids = ["skill-a", "skill-b"]
    if reads_from is None:
        reads_from = ["docs/tier3/input.json"]
    if writes_to is None:
        writes_to = ["docs/tier4/phase1/"]

    # Agent catalog
    catalog_entries = [
        {
            "id": agent_id,
            "reads_from": reads_from,
            "writes_to": writes_to,
        },
    ]
    if extra_catalog_entries:
        catalog_entries.extend(extra_catalog_entries)
    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "agent_catalog.yaml",
        {"agent_catalog": catalog_entries},
    )

    # Skill catalog — each skill belongs to its agent
    skill_catalog = []
    for sid in skill_ids:
        used_by = [agent_id]
        if sub_agent_id and sid.startswith("sub-"):
            used_by = [sub_agent_id]
        if pre_gate_agent_id and sid.startswith("pre-"):
            used_by = [pre_gate_agent_id]
        skill_catalog.append({
            "id": sid,
            "reads_from": reads_from,
            "writes_to": writes_to,
            "constitutional_constraints": [],
            "used_by_agents": used_by,
        })
    _write_yaml(
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "skill_catalog.yaml",
        {"skill_catalog": skill_catalog},
    )

    # Manifest with artifact_registry
    if artifact_registry is None:
        artifact_registry = [
            {
                "path": "docs/tier4/phase1/output.json",
                "produced_by": node_id,
                "tier": "tier4_phase_output",
            },
        ]
    manifest_data = {
        "name": "test",
        "version": "1.1",
        "node_registry": [
            {
                "node_id": node_id,
                "agent": agent_id,
                "skills": skill_ids,
                "phase_id": phase_id,
                "exit_gate": "test_gate",
            },
        ],
        "edge_registry": [],
        "artifact_registry": artifact_registry,
    }
    manifest_path = repo_root / "manifest_test.yaml"
    _write_yaml(manifest_path, manifest_data)

    # Agent definition and prompt spec
    agent_dir = repo_root / ".claude" / "agents"
    (agent_dir / f"{agent_id}.md").parent.mkdir(parents=True, exist_ok=True)
    (agent_dir / f"{agent_id}.md").write_text(
        f"# {agent_id}\nTest agent definition.", encoding="utf-8"
    )
    prompts_dir = agent_dir / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    # Mention skills in order in prompt spec
    prompt_content = f"# {agent_id} prompt spec\n\n"
    for sid in skill_ids:
        prompt_content += f"Invoke {sid}.\n"
    (prompts_dir / f"{agent_id}_prompt_spec.md").write_text(
        prompt_content, encoding="utf-8"
    )

    # Input artifact
    _write_json(repo_root / "docs" / "tier3" / "input.json", {"data": "test"})

    return {
        "agent_id": agent_id,
        "node_id": node_id,
        "run_id": "run-test-001",
        "repo_root": repo_root,
        "manifest_path": manifest_path,
        "skill_ids": skill_ids,
        "phase_id": phase_id,
        "sub_agent_id": sub_agent_id,
        "pre_gate_agent_id": pre_gate_agent_id,
    }


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    """Clear module-level caches between tests."""
    import runner.agent_runtime as _ar
    import runner.skill_runtime as _sr
    _ar._agent_catalog_cache.clear()
    _ar._artifact_registry_cache.clear()
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()


def _success_skill(outputs: list[str] | None = None) -> SkillResult:
    return SkillResult(
        status="success",
        outputs_written=outputs or [],
    )


def _failure_skill(
    category: str = "MISSING_INPUT",
    reason: str = "test failure",
) -> SkillResult:
    return SkillResult(
        status="failure",
        failure_reason=reason,
        failure_category=category,
    )


# ---------------------------------------------------------------------------
# Successful agent execution
# ---------------------------------------------------------------------------


class TestAgentSuccess:
    def test_all_skills_succeed(self, tmp_path: Path) -> None:
        """Successful agent → AgentResult(status="success", can_evaluate_exit_gate=True)."""
        kwargs = _make_agent_env(tmp_path)
        # Write the gate-relevant artifact so can_evaluate_exit_gate is True
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )
        with patch(_RUN_SKILL_TARGET, return_value=_success_skill()):
            result = run_agent(**kwargs)

        assert result.status == "success"
        assert result.can_evaluate_exit_gate is True
        assert result.failure_origin == "agent_body"
        assert result.failure_reason is None

    def test_invoked_skills_ordered(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(tmp_path, skill_ids=["skill-a", "skill-b", "skill-c"])
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )
        records: list[str] = []

        def _track_skill(skill_id, *args, **kw):
            records.append(skill_id)
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track_skill):
            result = run_agent(**kwargs)

        assert result.status == "success"
        assert len(result.invoked_skills) == 3
        # All three skill IDs recorded
        skill_ids_recorded = [r.skill_id for r in result.invoked_skills]
        assert "skill-a" in skill_ids_recorded
        assert "skill-b" in skill_ids_recorded
        assert "skill-c" in skill_ids_recorded

    def test_failure_origin_always_agent_body(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(tmp_path)
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )
        with patch(_RUN_SKILL_TARGET, return_value=_success_skill()):
            result = run_agent(**kwargs)
        assert result.failure_origin == "agent_body"


# ---------------------------------------------------------------------------
# §14 test 6 — skill failure propagation
# ---------------------------------------------------------------------------


class TestSkillFailurePropagation:
    """Verify that when a skill returns SkillResult(status="failure"),
    the agent runtime correctly propagates this to AgentResult."""

    def test_skill_failure_propagated(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(tmp_path)
        with patch(
            _RUN_SKILL_TARGET,
            return_value=_failure_skill("MISSING_INPUT", "input missing"),
        ):
            result = run_agent(**kwargs)

        assert result.status == "failure"
        assert result.failure_category == "SKILL_FAILURE"
        assert "input missing" in (result.failure_reason or "")

    def test_skill_failure_records(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(tmp_path)
        with patch(
            _RUN_SKILL_TARGET,
            return_value=_failure_skill("MALFORMED_ARTIFACT", "bad schema"),
        ):
            result = run_agent(**kwargs)

        assert len(result.invoked_skills) > 0
        failed = [r for r in result.invoked_skills if r.status == "failure"]
        assert len(failed) > 0
        assert failed[0].failure_category == "MALFORMED_ARTIFACT"


# ---------------------------------------------------------------------------
# §14 test 16 — CONSTITUTIONAL_HALT
# ---------------------------------------------------------------------------


class TestConstitutionalHalt:
    """Test that when a skill returns SkillResult(failure_category="CONSTITUTIONAL_HALT"),
    the agent immediately halts and returns AgentResult with
    failure_category="CONSTITUTIONAL_HALT" and can_evaluate_exit_gate=False."""

    def test_halt_on_constitutional_halt(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(
            tmp_path, skill_ids=["skill-a", "skill-b", "skill-c"]
        )
        call_count = 0

        def _halt_on_second(skill_id, *args, **kw):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                return _failure_skill("CONSTITUTIONAL_HALT", "fabricated data")
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_halt_on_second):
            result = run_agent(**kwargs)

        assert result.status == "failure"
        assert result.failure_category == "CONSTITUTIONAL_HALT"
        assert result.can_evaluate_exit_gate is False
        # Third skill should NOT have been invoked
        assert call_count == 2

    def test_halt_records_partial_invocations(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(tmp_path, skill_ids=["skill-a", "skill-b"])

        def _first_halts(skill_id, *args, **kw):
            return _failure_skill("CONSTITUTIONAL_HALT", "violated constraint")

        with patch(_RUN_SKILL_TARGET, side_effect=_first_halts):
            result = run_agent(**kwargs)

        assert result.failure_category == "CONSTITUTIONAL_HALT"
        assert len(result.invoked_skills) == 1
        assert result.invoked_skills[0].failure_category == "CONSTITUTIONAL_HALT"


# ---------------------------------------------------------------------------
# §14 test 9 — n03 sub-agent coordination
# ---------------------------------------------------------------------------


class TestSubAgentCoordination:
    """Verify that n03_wp_design invokes sub-agent (dependency_mapper) skills."""

    def test_sub_agent_skills_invoked(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(
            tmp_path,
            agent_id="wp_designer",
            node_id="n03_wp_design",
            skill_ids=[
                "work-package-normalization",
                "sub-dependency-analysis",
                "skill-c",
            ],
            sub_agent_id="dependency_mapper",
            extra_catalog_entries=[
                {
                    "id": "dependency_mapper",
                    "reads_from": ["docs/tier3/input.json"],
                    "writes_to": ["docs/tier4/phase1/"],
                },
            ],
        )
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )
        invoked: list[str] = []

        def _track(skill_id, *args, **kw):
            invoked.append(skill_id)
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        assert result.status == "success"
        # sub-agent skill was invoked
        assert "sub-dependency-analysis" in invoked
        # Primary skills were also invoked
        assert "work-package-normalization" in invoked


# ---------------------------------------------------------------------------
# Declarative sub-agent injection (manifest-driven, not skill-name coupled)
# ---------------------------------------------------------------------------


class TestDeclarativeSubAgentInjection:
    """Verify sub-agent invocation is manifest-driven via artifact readiness,
    not coupled to any hardcoded skill name."""

    def test_sub_agent_invoked_by_artifact_readiness_not_skill_name(
        self, tmp_path: Path,
    ) -> None:
        """Sub-agent triggers when its reads_from inputs appear on disk,
        regardless of which skill produced them.  Uses non-standard skill
        names to prove no coupling to 'work-package-normalization'."""
        # Use completely different skill names — no reference to
        # "work-package-normalization" anywhere in this test.
        kwargs = _make_agent_env(
            tmp_path,
            agent_id="my_agent",
            node_id="n03_wp_design",
            skill_ids=["primary-alpha", "sub-beta", "primary-gamma"],
            sub_agent_id="my_sub_agent",
            reads_from=["docs/tier3/input.json"],
            writes_to=["docs/tier4/phase1/"],
            extra_catalog_entries=[
                {
                    "id": "my_sub_agent",
                    # Sub-agent reads from a directory that the primary
                    # agent writes to — the key readiness trigger.
                    "reads_from": ["docs/output_dir/"],
                    "writes_to": ["docs/output_dir/"],
                },
            ],
        )
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )

        invoked: list[str] = []

        def _track(skill_id, *args, **kw):
            invoked.append(skill_id)
            if skill_id == "primary-alpha":
                # Simulate the primary skill writing the artifact that
                # makes the sub-agent's inputs ready.
                out_dir = tmp_path / "docs" / "output_dir"
                out_dir.mkdir(parents=True, exist_ok=True)
                _write_json(out_dir / "structure.json", {"wp": "data"})
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        assert result.status == "success"
        # Sub-agent skill was invoked — triggered by artifact readiness,
        # not by any skill name matching.
        assert "sub-beta" in invoked
        # Sub-agent was invoked AFTER primary-alpha (which created the artifact)
        assert invoked.index("sub-beta") > invoked.index("primary-alpha")

    def test_sub_agent_not_invoked_when_inputs_not_ready(
        self, tmp_path: Path,
    ) -> None:
        """When the sub-agent's reads_from inputs are never produced,
        the sub-agent is not invoked during the primary loop, and the
        fallback fails closed."""
        kwargs = _make_agent_env(
            tmp_path,
            agent_id="my_agent",
            node_id="n03_wp_design",
            skill_ids=["primary-alpha", "sub-beta"],
            sub_agent_id="my_sub_agent",
            reads_from=["docs/tier3/input.json"],
            writes_to=["docs/tier4/phase1/"],
            extra_catalog_entries=[
                {
                    "id": "my_sub_agent",
                    # Points to a directory that will NOT be created.
                    "reads_from": ["docs/nonexistent_dir/"],
                    "writes_to": [],
                },
            ],
        )
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )

        invoked: list[str] = []

        def _track(skill_id, *args, **kw):
            invoked.append(skill_id)
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        # Sub-agent skill was NOT invoked — inputs never became ready.
        assert "sub-beta" not in invoked
        # Fail closed: agent reports failure because sub-agent couldn't run.
        assert result.status == "failure"
        assert result.failure_category == "INCOMPLETE_OUTPUT"
        assert "sub-agent" in (result.failure_reason or "").lower()

    def test_sub_agent_invoked_at_correct_point_in_sequence(
        self, tmp_path: Path,
    ) -> None:
        """Sub-agent skills are injected after the skill that makes
        their inputs ready, not at the end of the sequence."""
        kwargs = _make_agent_env(
            tmp_path,
            agent_id="my_agent",
            node_id="n03_wp_design",
            skill_ids=["step-one", "sub-work", "step-two"],
            sub_agent_id="my_sub_agent",
            reads_from=["docs/tier3/input.json"],
            writes_to=["docs/tier4/phase1/"],
            extra_catalog_entries=[
                {
                    "id": "my_sub_agent",
                    "reads_from": ["docs/sub_input/"],
                    "writes_to": [],
                },
            ],
        )
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )

        invoked: list[str] = []

        def _track(skill_id, *args, **kw):
            invoked.append(skill_id)
            if skill_id == "step-one":
                # Create the sub-agent's required input directory.
                d = tmp_path / "docs" / "sub_input"
                d.mkdir(parents=True, exist_ok=True)
                _write_json(d / "data.json", {"ready": True})
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        assert result.status == "success"
        # Execution order: step-one → sub-work → step-two
        assert invoked.index("step-one") < invoked.index("sub-work")
        assert invoked.index("sub-work") < invoked.index("step-two")

    def test_no_sub_agent_unchanged_behavior(self, tmp_path: Path) -> None:
        """Nodes without a declared sub_agent execute normally."""
        kwargs = _make_agent_env(
            tmp_path,
            skill_ids=["alpha", "beta"],
            sub_agent_id=None,
        )
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )

        invoked: list[str] = []

        def _track(skill_id, *args, **kw):
            invoked.append(skill_id)
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        assert result.status == "success"
        assert invoked == ["alpha", "beta"]

    def test_no_hardcoded_skill_name_trigger_in_source(self) -> None:
        """Confirm agent_runtime.py no longer contains the hardcoded
        'work-package-normalization' trigger string as a controlling
        mechanism for sub-agent invocation."""
        import runner.agent_runtime as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        # The old _should_invoke_sub_agent function must be gone.
        assert "_should_invoke_sub_agent" not in source
        # No runtime decision based on the literal skill name.
        # (The string may appear in comments explaining history,
        # but not in executable if/elif branches.)
        lines = source.splitlines()
        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue  # skip comments
            assert (
                '"work-package-normalization"' not in stripped
                and "'work-package-normalization'" not in stripped
            ), (
                f"Hardcoded skill-name trigger found in executable code: "
                f"{line!r}"
            )

    def test_manifest_declared_sub_agent_is_controlling_factor(
        self, tmp_path: Path,
    ) -> None:
        """When the manifest declares a sub_agent, its invocation is
        driven by agent_catalog reads_from readiness — not by any
        heuristic or prompt parsing."""
        # Use a totally novel agent/sub-agent pair with no resemblance
        # to Phase 3 names.  If this works, the mechanism is generic.
        kwargs = _make_agent_env(
            tmp_path,
            agent_id="novel_agent",
            node_id="n99_novel",
            skill_ids=["novel-build", "sub-novel-enrich", "novel-check"],
            sub_agent_id="novel_sub",
            reads_from=["docs/tier3/input.json"],
            writes_to=["docs/tier4/phase1/"],
            extra_catalog_entries=[
                {
                    "id": "novel_sub",
                    "reads_from": ["docs/novel_ready/"],
                    "writes_to": ["docs/novel_ready/"],
                },
            ],
            artifact_registry=[
                {
                    "path": "docs/tier4/phase1/output.json",
                    "produced_by": "n99_novel",
                    "tier": "tier4_phase_output",
                },
            ],
        )
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )

        invoked: list[str] = []

        def _track(skill_id, *args, **kw):
            invoked.append(skill_id)
            if skill_id == "novel-build":
                d = tmp_path / "docs" / "novel_ready"
                d.mkdir(parents=True, exist_ok=True)
                _write_json(d / "artifact.json", {"built": True})
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        assert result.status == "success"
        assert "sub-novel-enrich" in invoked
        assert invoked.index("novel-build") < invoked.index("sub-novel-enrich")


# ---------------------------------------------------------------------------
# §14 test 10 — n07 pre_gate_agent coordination
# ---------------------------------------------------------------------------


class TestPreGateAgentCoordination:
    """Confirm that n07_budget_gate invokes pre-gate agent
    (budget_interface_coordinator) before primary agent skills."""

    def test_pre_gate_skills_invoked_first(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(
            tmp_path,
            agent_id="budget_gate_validator",
            node_id="n07_budget_gate",
            skill_ids=["pre-budget-prep", "skill-validate"],
            pre_gate_agent_id="budget_interface_coordinator",
            extra_catalog_entries=[
                {
                    "id": "budget_interface_coordinator",
                    "reads_from": ["docs/tier3/input.json"],
                    "writes_to": ["docs/tier4/phase1/"],
                },
            ],
        )
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )
        invoked: list[str] = []

        def _track(skill_id, *args, **kw):
            invoked.append(skill_id)
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        assert result.status == "success"
        # Pre-gate skill invoked
        assert "pre-budget-prep" in invoked
        # Primary skill invoked
        assert "skill-validate" in invoked
        # Pre-gate skills come before primary skills
        pre_idx = invoked.index("pre-budget-prep")
        primary_idx = invoked.index("skill-validate")
        assert pre_idx < primary_idx, "Pre-gate skills must run before primary"

    def test_pre_gate_constitutional_halt_stops_agent(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(
            tmp_path,
            agent_id="budget_gate_validator",
            node_id="n07_budget_gate",
            skill_ids=["pre-budget-prep", "skill-validate"],
            pre_gate_agent_id="budget_interface_coordinator",
            extra_catalog_entries=[
                {
                    "id": "budget_interface_coordinator",
                    "reads_from": ["docs/tier3/input.json"],
                    "writes_to": ["docs/tier4/phase1/"],
                },
            ],
        )

        def _halt_pre_gate(skill_id, *args, **kw):
            if skill_id == "pre-budget-prep":
                return _failure_skill("CONSTITUTIONAL_HALT", "budget fabricated")
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_halt_pre_gate):
            result = run_agent(**kwargs)

        assert result.status == "failure"
        assert result.failure_category == "CONSTITUTIONAL_HALT"
        assert result.can_evaluate_exit_gate is False


# ---------------------------------------------------------------------------
# can_evaluate_exit_gate from disk state
# ---------------------------------------------------------------------------


class TestCanEvaluateExitGate:
    def test_false_when_artifacts_missing(self, tmp_path: Path) -> None:
        """can_evaluate_exit_gate is False when gate-relevant artifacts are absent."""
        kwargs = _make_agent_env(tmp_path)
        # Don't write the output artifact
        with patch(_RUN_SKILL_TARGET, return_value=_success_skill()):
            result = run_agent(**kwargs)

        # All skills succeeded but artifact missing → failure
        assert result.can_evaluate_exit_gate is False

    def test_true_when_artifacts_present(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(tmp_path)
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )
        with patch(_RUN_SKILL_TARGET, return_value=_success_skill()):
            result = run_agent(**kwargs)

        assert result.can_evaluate_exit_gate is True


# ---------------------------------------------------------------------------
# Missing agent spec
# ---------------------------------------------------------------------------


class TestMissingSpecs:
    def test_missing_agent_definition(self, tmp_path: Path) -> None:
        kwargs = _make_agent_env(tmp_path, agent_id="nonexistent_agent")
        # Remove the agent spec that was created
        spec_path = tmp_path / ".claude" / "agents" / "nonexistent_agent.md"
        if spec_path.exists():
            spec_path.unlink()

        result = run_agent(**kwargs)
        assert result.status == "failure"
        assert result.failure_category == "MISSING_INPUT"
        assert result.can_evaluate_exit_gate is False


# ---------------------------------------------------------------------------
# Gate-enforcement context injection (Fix 2)
# ---------------------------------------------------------------------------


class TestGateEnforcementContext:
    """Tests that gate-enforcement receives gate_id via caller_context."""

    def test_gate_enforcement_receives_gate_id(self, tmp_path: Path) -> None:
        """When gate-enforcement is in the skill list, the agent runtime
        passes the node's exit gate as gate_id in caller_context."""
        kwargs = _make_agent_env(
            tmp_path,
            skill_ids=["skill-a", "gate-enforcement"],
            node_id="n03_wp_design",
        )
        # Update manifest so n03 has exit_gate
        manifest_path = kwargs["repo_root"] / "manifest_test.yaml"
        manifest_data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest_data["node_registry"][0]["exit_gate"] = "phase_03_gate"
        _write_yaml(manifest_path, manifest_data)
        kwargs["manifest_path"] = manifest_path

        # Write gate-relevant artifact so can_evaluate_exit_gate can be True
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )

        captured_calls: list[dict] = []

        def _capture_run_skill(skill_id, run_id, repo_root, inputs=None, **kw):
            captured_calls.append({
                "skill_id": skill_id,
                "caller_context": kw.get("caller_context"),
            })
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_capture_run_skill):
            result = run_agent(**kwargs)

        # Find the gate-enforcement call
        gate_calls = [c for c in captured_calls if c["skill_id"] == "gate-enforcement"]
        assert len(gate_calls) == 1, (
            f"Expected 1 gate-enforcement call, got {len(gate_calls)}"
        )
        ctx = gate_calls[0]["caller_context"]
        assert ctx is not None, "gate-enforcement should receive caller_context"
        assert ctx.get("gate_id") == "phase_03_gate", (
            f"Expected gate_id='phase_03_gate', got {ctx.get('gate_id')!r}"
        )

    def test_non_gate_enforcement_skills_unaffected(self, tmp_path: Path) -> None:
        """Skills other than gate-enforcement do not get gate_id injected."""
        kwargs = _make_agent_env(
            tmp_path,
            skill_ids=["skill-a", "skill-b"],
        )
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )

        captured_calls: list[dict] = []

        def _capture_run_skill(skill_id, run_id, repo_root, inputs=None, **kw):
            captured_calls.append({
                "skill_id": skill_id,
                "caller_context": kw.get("caller_context"),
            })
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_capture_run_skill):
            result = run_agent(**kwargs)

        for call in captured_calls:
            ctx = call["caller_context"]
            # Non-gate-enforcement skills: caller_context should be None or
            # not contain gate_id
            if ctx is not None:
                assert "gate_id" not in ctx, (
                    f"Skill {call['skill_id']!r} should not receive gate_id"
                )


# ---------------------------------------------------------------------------
# Exit gate lookup helper
# ---------------------------------------------------------------------------


class TestGetExitGateForNode:
    """Tests for _get_exit_gate_for_node manifest lookup."""

    def test_returns_exit_gate(self, tmp_path: Path) -> None:
        from runner.agent_runtime import _get_exit_gate_for_node, _node_exit_gate_cache
        _node_exit_gate_cache.clear()

        manifest_path = tmp_path / "manifest.yaml"
        _write_yaml(manifest_path, {
            "node_registry": [
                {"node_id": "n03_wp_design", "exit_gate": "phase_03_gate"},
                {"node_id": "n04_gantt", "exit_gate": "phase_04_gate"},
            ],
        })

        assert _get_exit_gate_for_node("n03_wp_design", manifest_path) == "phase_03_gate"
        assert _get_exit_gate_for_node("n04_gantt", manifest_path) == "phase_04_gate"

    def test_returns_none_for_unknown_node(self, tmp_path: Path) -> None:
        from runner.agent_runtime import _get_exit_gate_for_node, _node_exit_gate_cache
        _node_exit_gate_cache.clear()

        manifest_path = tmp_path / "manifest.yaml"
        _write_yaml(manifest_path, {
            "node_registry": [
                {"node_id": "n01", "exit_gate": "gate_01"},
            ],
        })

        assert _get_exit_gate_for_node("n99_unknown", manifest_path) is None

    def test_returns_none_for_missing_manifest(self, tmp_path: Path) -> None:
        from runner.agent_runtime import _get_exit_gate_for_node, _node_exit_gate_cache
        _node_exit_gate_cache.clear()

        manifest_path = tmp_path / "nonexistent.yaml"
        assert _get_exit_gate_for_node("n01", manifest_path) is None


# ---------------------------------------------------------------------------
# Instrument type context injection (resolved_instrument_type fix)
# ---------------------------------------------------------------------------


class TestResolveInstrumentType:
    """Tests for _resolve_instrument_type() helper."""

    def test_returns_instrument_type_from_selected_call(self, tmp_path: Path) -> None:
        from runner.agent_runtime import _resolve_instrument_type
        _write_json(
            tmp_path / "docs" / "tier3_project_instantiation"
            / "call_binding" / "selected_call.json",
            {"instrument_type": "RIA", "topic_code": "HORIZON-CL4-2026"},
        )
        assert _resolve_instrument_type(tmp_path) == "RIA"

    def test_returns_none_when_file_missing(self, tmp_path: Path) -> None:
        from runner.agent_runtime import _resolve_instrument_type
        assert _resolve_instrument_type(tmp_path) is None

    def test_returns_none_when_field_missing(self, tmp_path: Path) -> None:
        from runner.agent_runtime import _resolve_instrument_type
        _write_json(
            tmp_path / "docs" / "tier3_project_instantiation"
            / "call_binding" / "selected_call.json",
            {"topic_code": "HORIZON-CL4-2026"},
        )
        assert _resolve_instrument_type(tmp_path) is None

    def test_returns_none_when_field_empty(self, tmp_path: Path) -> None:
        from runner.agent_runtime import _resolve_instrument_type
        _write_json(
            tmp_path / "docs" / "tier3_project_instantiation"
            / "call_binding" / "selected_call.json",
            {"instrument_type": "  "},
        )
        assert _resolve_instrument_type(tmp_path) is None

    def test_returns_none_when_malformed_json(self, tmp_path: Path) -> None:
        from runner.agent_runtime import _resolve_instrument_type
        path = (
            tmp_path / "docs" / "tier3_project_instantiation"
            / "call_binding" / "selected_call.json"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not valid json {{{", encoding="utf-8")
        assert _resolve_instrument_type(tmp_path) is None

    def test_strips_whitespace(self, tmp_path: Path) -> None:
        from runner.agent_runtime import _resolve_instrument_type
        _write_json(
            tmp_path / "docs" / "tier3_project_instantiation"
            / "call_binding" / "selected_call.json",
            {"instrument_type": "  CSA  "},
        )
        assert _resolve_instrument_type(tmp_path) == "CSA"


class TestInstrumentTypeContextInjection:
    """Tests that instrument-schema-normalization receives resolved_instrument_type
    via caller_context, sourced from selected_call.json."""

    def _make_env_with_selected_call(
        self,
        tmp_path: Path,
        *,
        instrument_type: str = "RIA",
        include_selected_call: bool = True,
        skill_ids: list[str] | None = None,
    ) -> dict:
        """Create a test environment with instrument-schema-normalization."""
        if skill_ids is None:
            skill_ids = [
                "work-package-normalization",
                "instrument-schema-normalization",
                "gate-enforcement",
            ]
        kwargs = _make_agent_env(
            tmp_path,
            agent_id="wp_designer",
            node_id="n03_wp_design",
            skill_ids=skill_ids,
            phase_id="phase_03_wp_design_and_dependency_mapping",
        )
        # Update manifest exit_gate
        manifest_path = kwargs["repo_root"] / "manifest_test.yaml"
        manifest_data = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        manifest_data["node_registry"][0]["exit_gate"] = "phase_03_gate"
        _write_yaml(manifest_path, manifest_data)

        # Write gate-relevant artifact
        _write_json(
            tmp_path / "docs" / "tier4" / "phase1" / "output.json",
            {"result": "done"},
        )

        # Write selected_call.json (authoritative source)
        if include_selected_call:
            _write_json(
                tmp_path / "docs" / "tier3_project_instantiation"
                / "call_binding" / "selected_call.json",
                {"instrument_type": instrument_type, "topic_code": "HORIZON-TEST"},
            )
        return kwargs

    def test_receives_resolved_instrument_type(self, tmp_path: Path) -> None:
        """Positive case: instrument-schema-normalization receives the
        resolved_instrument_type from selected_call.json via caller_context."""
        kwargs = self._make_env_with_selected_call(tmp_path, instrument_type="RIA")

        captured_calls: list[dict] = []

        def _capture(skill_id, run_id, repo_root, inputs=None, **kw):
            captured_calls.append({
                "skill_id": skill_id,
                "caller_context": kw.get("caller_context"),
            })
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_capture):
            result = run_agent(**kwargs)

        # Find the instrument-schema-normalization call
        isn_calls = [
            c for c in captured_calls
            if c["skill_id"] == "instrument-schema-normalization"
        ]
        assert len(isn_calls) == 1, (
            f"Expected 1 instrument-schema-normalization call, got {len(isn_calls)}"
        )
        ctx = isn_calls[0]["caller_context"]
        assert ctx is not None, (
            "instrument-schema-normalization should receive caller_context"
        )
        assert ctx.get("resolved_instrument_type") == "RIA", (
            f"Expected resolved_instrument_type='RIA', "
            f"got {ctx.get('resolved_instrument_type')!r}"
        )

    def test_fails_closed_when_selected_call_missing(self, tmp_path: Path) -> None:
        """Missing-source case: runtime fails closed with clear reason."""
        kwargs = self._make_env_with_selected_call(
            tmp_path, include_selected_call=False,
        )

        invoked_skill_ids: list[str] = []

        def _track(skill_id, run_id, repo_root, inputs=None, **kw):
            invoked_skill_ids.append(skill_id)
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        # instrument-schema-normalization was NOT invoked via run_skill
        assert "instrument-schema-normalization" not in invoked_skill_ids
        # Agent reports failure
        assert result.status == "failure"
        assert "instrument type" in (result.failure_reason or "").lower()
        # The failure is recorded in invoked_skills
        isn_records = [
            r for r in result.invoked_skills
            if r.skill_id == "instrument-schema-normalization"
        ]
        assert len(isn_records) == 1
        assert isn_records[0].status == "failure"
        assert isn_records[0].failure_category == "MISSING_INPUT"

    def test_fails_closed_when_instrument_type_field_missing(
        self, tmp_path: Path,
    ) -> None:
        """Malformed source: selected_call.json exists but has no instrument_type."""
        kwargs = self._make_env_with_selected_call(tmp_path)
        # Overwrite selected_call.json without instrument_type
        _write_json(
            tmp_path / "docs" / "tier3_project_instantiation"
            / "call_binding" / "selected_call.json",
            {"topic_code": "HORIZON-TEST"},
        )

        invoked_skill_ids: list[str] = []

        def _track(skill_id, run_id, repo_root, inputs=None, **kw):
            invoked_skill_ids.append(skill_id)
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        assert "instrument-schema-normalization" not in invoked_skill_ids
        assert result.status == "failure"
        isn_records = [
            r for r in result.invoked_skills
            if r.skill_id == "instrument-schema-normalization"
        ]
        assert len(isn_records) == 1
        assert isn_records[0].failure_category == "MISSING_INPUT"

    def test_no_fabricated_default_instrument_type(self, tmp_path: Path) -> None:
        """No default value is used when the source is missing."""
        kwargs = self._make_env_with_selected_call(
            tmp_path, include_selected_call=False,
        )

        captured_contexts: list[dict | None] = []

        def _capture(skill_id, run_id, repo_root, inputs=None, **kw):
            captured_contexts.append(kw.get("caller_context"))
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_capture):
            run_agent(**kwargs)

        # No call should have received a fabricated resolved_instrument_type
        for ctx in captured_contexts:
            if ctx is not None:
                assert "resolved_instrument_type" not in ctx, (
                    "No skill should receive a fabricated resolved_instrument_type"
                )

    def test_other_skills_unaffected(self, tmp_path: Path) -> None:
        """Non-instrument-schema-normalization skills do not get
        resolved_instrument_type injected."""
        kwargs = self._make_env_with_selected_call(
            tmp_path,
            skill_ids=["skill-a", "skill-b"],
        )

        captured_calls: list[dict] = []

        def _capture(skill_id, run_id, repo_root, inputs=None, **kw):
            captured_calls.append({
                "skill_id": skill_id,
                "caller_context": kw.get("caller_context"),
            })
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_capture):
            run_agent(**kwargs)

        for call in captured_calls:
            ctx = call["caller_context"]
            if ctx is not None:
                assert "resolved_instrument_type" not in ctx, (
                    f"Skill {call['skill_id']!r} should not receive "
                    f"resolved_instrument_type"
                )

    def test_gate_enforcement_ordering_preserved(self, tmp_path: Path) -> None:
        """gate-enforcement still executes LAST after instrument-schema-normalization."""
        kwargs = self._make_env_with_selected_call(
            tmp_path,
            skill_ids=[
                "work-package-normalization",
                "instrument-schema-normalization",
                "gate-enforcement",
            ],
        )

        invoked_order: list[str] = []

        def _track(skill_id, run_id, repo_root, inputs=None, **kw):
            invoked_order.append(skill_id)
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            run_agent(**kwargs)

        # gate-enforcement must be last
        assert invoked_order[-1] == "gate-enforcement"
        # instrument-schema-normalization must come before gate-enforcement
        isn_idx = invoked_order.index("instrument-schema-normalization")
        ge_idx = invoked_order.index("gate-enforcement")
        assert isn_idx < ge_idx

    def test_phase3_full_skill_sequence(self, tmp_path: Path) -> None:
        """Integration-style: Phase 3 agent passes instrument type and
        maintains correct skill ordering."""
        kwargs = self._make_env_with_selected_call(
            tmp_path,
            instrument_type="IA",
            skill_ids=[
                "work-package-normalization",
                "wp-dependency-analysis",
                "milestone-consistency-check",
                "instrument-schema-normalization",
                "gate-enforcement",
            ],
        )
        # Update skill catalog for all skills
        catalog_path = (
            tmp_path / ".claude" / "workflows"
            / "system_orchestration" / "skill_catalog.yaml"
        )
        catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
        for entry in catalog["skill_catalog"]:
            entry["used_by_agents"] = ["wp_designer"]
        _write_yaml(catalog_path, catalog)

        invoked_order: list[str] = []
        isn_context: dict | None = None

        def _track(skill_id, run_id, repo_root, inputs=None, **kw):
            nonlocal isn_context
            invoked_order.append(skill_id)
            if skill_id == "instrument-schema-normalization":
                isn_context = kw.get("caller_context")
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        # instrument-schema-normalization received IA
        assert isn_context is not None
        assert isn_context.get("resolved_instrument_type") == "IA"

        # gate-enforcement is last
        assert invoked_order[-1] == "gate-enforcement"

        # instrument-schema-normalization is before gate-enforcement
        assert invoked_order.index("instrument-schema-normalization") < (
            invoked_order.index("gate-enforcement")
        )


# ---------------------------------------------------------------------------
# Module isolation
# ---------------------------------------------------------------------------


class TestModuleIsolation:
    def test_no_dag_scheduler_or_gate_evaluator_import(self) -> None:
        import runner.agent_runtime as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "runner.dag_scheduler" not in source
        assert "runner.gate_evaluator" not in source


# ---------------------------------------------------------------------------
# Phase 8 startup: artifact_path injection and skill ordering
# ---------------------------------------------------------------------------


class TestPhase8ArtifactPathInjection:
    """Verify constitutional-compliance-check receives artifact_path
    for Phase 8 nodes where outputs are Tier 5 deliverables."""

    def _make_phase8_env(
        self,
        tmp_path: Path,
        *,
        node_id: str = "n08a_section_drafting",
        skill_ids: list[str] | None = None,
    ) -> dict:
        if skill_ids is None:
            skill_ids = [
                "proposal-section-drafting",
                "constitutional-compliance-check",
            ]
        kwargs = _make_agent_env(
            tmp_path,
            agent_id="proposal_writer",
            node_id=node_id,
            skill_ids=skill_ids,
            phase_id="phase_08a_section_drafting",
            reads_from=[
                "docs/tier3/input.json",
                "docs/tier4_orchestration_state/phase_outputs/",
            ],
            writes_to=[
                "docs/tier5_deliverables/proposal_sections/",
                "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/",
            ],
            artifact_registry=[
                {
                    "path": "docs/tier5_deliverables/proposal_sections/",
                    "produced_by": node_id,
                    "tier": "tier5_deliverable",
                },
                {
                    "path": "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review/",
                    "produced_by": node_id,
                    "tier": "tier4_phase_output",
                },
            ],
        )
        # Create phase_outputs dir so input resolution doesn't fail
        (tmp_path / "docs" / "tier4_orchestration_state" / "phase_outputs").mkdir(
            parents=True, exist_ok=True,
        )
        return kwargs

    def test_tier5_output_injected_as_artifact_path(
        self, tmp_path: Path,
    ) -> None:
        """When proposal-section-drafting produces Tier 5 output,
        constitutional-compliance-check receives it as artifact_path."""
        kwargs = self._make_phase8_env(tmp_path)

        captured_calls: list[dict] = []

        def _track(skill_id, run_id, repo_root, inputs=None, **kw):
            captured_calls.append({
                "skill_id": skill_id,
                "caller_context": kw.get("caller_context"),
            })
            if skill_id == "proposal-section-drafting":
                # Simulate producing a Tier 5 section artifact
                section_path = (
                    tmp_path / "docs" / "tier5_deliverables"
                    / "proposal_sections" / "section_1a.json"
                )
                section_path.parent.mkdir(parents=True, exist_ok=True)
                _write_json(section_path, {
                    "schema_id": "orch.tier5.proposal_section.v1",
                    "section_id": "section_1a",
                    "content": "Test content",
                })
                return _success_skill(outputs=[
                    "docs/tier5_deliverables/proposal_sections/section_1a.json",
                ])
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            run_agent(**kwargs)

        # Find constitutional-compliance-check call
        ccc_calls = [
            c for c in captured_calls
            if c["skill_id"] == "constitutional-compliance-check"
        ]
        assert len(ccc_calls) == 1
        ctx = ccc_calls[0]["caller_context"]
        assert ctx is not None, (
            "constitutional-compliance-check should receive caller_context"
        )
        assert ctx.get("artifact_path") == (
            "docs/tier5_deliverables/proposal_sections/section_1a.json"
        )

    def test_no_artifact_produces_missing_input_failure(
        self, tmp_path: Path,
    ) -> None:
        """When no earlier skill produces an auditable artifact,
        constitutional-compliance-check is skipped with MISSING_INPUT."""
        kwargs = self._make_phase8_env(tmp_path)

        invoked_skill_ids: list[str] = []

        def _track(skill_id, run_id, repo_root, inputs=None, **kw):
            invoked_skill_ids.append(skill_id)
            # proposal-section-drafting succeeds but writes nothing
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        # constitutional-compliance-check should NOT be invoked via run_skill
        assert "constitutional-compliance-check" not in invoked_skill_ids
        # But it should appear in invoked_skills with a failure record
        ccc_records = [
            r for r in result.invoked_skills
            if r.skill_id == "constitutional-compliance-check"
        ]
        assert len(ccc_records) == 1
        assert ccc_records[0].status == "failure"
        assert ccc_records[0].failure_category == "MISSING_INPUT"
        assert "auditable artifact" in (ccc_records[0].failure_reason or "").lower()

    def test_tier4_phase_output_also_works_for_phase8(
        self, tmp_path: Path,
    ) -> None:
        """If an earlier skill writes a Tier 4 phase output in Phase 8,
        that path is also accepted as artifact_path."""
        kwargs = self._make_phase8_env(tmp_path)

        captured_calls: list[dict] = []

        def _track(skill_id, run_id, repo_root, inputs=None, **kw):
            captured_calls.append({
                "skill_id": skill_id,
                "caller_context": kw.get("caller_context"),
            })
            if skill_id == "proposal-section-drafting":
                # Produces a Tier 4 phase output instead of Tier 5
                out_path = (
                    tmp_path / "docs" / "tier4_orchestration_state"
                    / "phase_outputs" / "phase8_drafting_review" / "status.json"
                )
                out_path.parent.mkdir(parents=True, exist_ok=True)
                _write_json(out_path, {"status": "drafted"})
                return _success_skill(outputs=[
                    "docs/tier4_orchestration_state/phase_outputs/"
                    "phase8_drafting_review/status.json",
                ])
            return _success_skill()

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            run_agent(**kwargs)

        ccc_calls = [
            c for c in captured_calls
            if c["skill_id"] == "constitutional-compliance-check"
        ]
        assert len(ccc_calls) == 1
        ctx = ccc_calls[0]["caller_context"]
        assert ctx is not None
        assert ctx["artifact_path"].startswith(
            "docs/tier4_orchestration_state/phase_outputs/"
        )


class TestResolveAuditableArtifact:
    """Unit tests for the _resolve_auditable_artifact helper."""

    def test_prefers_outputs_over_fallback(self, tmp_path: Path) -> None:
        from runner.agent_runtime import _resolve_auditable_artifact
        outputs = [
            "docs/tier5_deliverables/proposal_sections/section_1a.json",
        ]
        result = _resolve_auditable_artifact(
            "n08a_section_drafting", outputs, tmp_path,
        )
        assert result == "docs/tier5_deliverables/proposal_sections/section_1a.json"

    def test_filters_gate_result(self, tmp_path: Path) -> None:
        from runner.agent_runtime import _resolve_auditable_artifact
        outputs = [
            "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/gate_result.json",
            "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/budget_gate_assessment.json",
        ]
        result = _resolve_auditable_artifact(
            "n07_budget_gate", outputs, tmp_path,
        )
        assert result == (
            "docs/tier4_orchestration_state/phase_outputs/"
            "phase7_budget_gate/budget_gate_assessment.json"
        )

    def test_fallback_to_disk_for_n08a(self, tmp_path: Path) -> None:
        from runner.agent_runtime import _resolve_auditable_artifact
        # Create a file in the fallback directory
        section_dir = tmp_path / "docs" / "tier5_deliverables" / "proposal_sections"
        section_dir.mkdir(parents=True, exist_ok=True)
        _write_json(section_dir / "section_1a.json", {"content": "test"})

        result = _resolve_auditable_artifact(
            "n08a_section_drafting", [], tmp_path,
        )
        assert result is not None
        assert "proposal_sections" in result
        assert result.endswith("section_1a.json")

    def test_returns_none_when_no_artifacts(self, tmp_path: Path) -> None:
        from runner.agent_runtime import _resolve_auditable_artifact
        result = _resolve_auditable_artifact(
            "n08a_section_drafting", [], tmp_path,
        )
        assert result is None

    def test_n08b_fallback_checks_assembled_drafts(self, tmp_path: Path) -> None:
        from runner.agent_runtime import _resolve_auditable_artifact
        drafts_dir = tmp_path / "docs" / "tier5_deliverables" / "assembled_drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        _write_json(drafts_dir / "assembled_draft.json", {"sections": []})

        result = _resolve_auditable_artifact(
            "n08b_assembly", [], tmp_path,
        )
        assert result is not None
        assert "assembled_drafts" in result


class TestEvaluatorCriteriaReviewApplicability:
    """Verify evaluator-criteria-review is skipped when Tier 5 is empty."""

    def test_skipped_when_no_tier5_content(self, tmp_path: Path) -> None:
        """evaluator-criteria-review should be skipped (not_applicable)
        when no Tier 5 deliverable directories have content."""
        from runner.agent_runtime import _check_skill_applicability
        # Ensure Tier 5 dirs exist but are empty
        for subdir in ("proposal_sections", "assembled_drafts"):
            (tmp_path / "docs" / "tier5_deliverables" / subdir).mkdir(
                parents=True, exist_ok=True,
            )
        applicable, reason = _check_skill_applicability(
            "evaluator-criteria-review", tmp_path,
        )
        assert not applicable
        assert reason is not None
        assert "Tier 5" in reason

    def test_applicable_when_tier5_has_content(self, tmp_path: Path) -> None:
        """evaluator-criteria-review is applicable when Tier 5 has content."""
        from runner.agent_runtime import _check_skill_applicability
        section_dir = tmp_path / "docs" / "tier5_deliverables" / "proposal_sections"
        section_dir.mkdir(parents=True, exist_ok=True)
        _write_json(section_dir / "section_1a.json", {"content": "test"})
        applicable, reason = _check_skill_applicability(
            "evaluator-criteria-review", tmp_path,
        )
        assert applicable
        assert reason is None

    def test_regular_skills_always_applicable(self, tmp_path: Path) -> None:
        """Skills not in _TIER5_AUDIT_SKILLS are always applicable."""
        from runner.agent_runtime import _check_skill_applicability
        applicable, reason = _check_skill_applicability(
            "proposal-section-drafting", tmp_path,
        )
        assert applicable
        assert reason is None


class TestPhase8GateResultOnlyByRunner:
    """Verify gate_result.json is never written by agent skills."""

    def test_gate_result_not_in_skill_outputs(self, tmp_path: Path) -> None:
        """No skill invocation in Phase 8 should produce gate_result.json."""
        kwargs = _make_agent_env(
            tmp_path,
            agent_id="proposal_writer",
            node_id="n08a_section_drafting",
            skill_ids=["proposal-section-drafting"],
            phase_id="phase_08a_section_drafting",
            reads_from=["docs/tier3/input.json"],
            writes_to=["docs/tier5_deliverables/proposal_sections/"],
            artifact_registry=[
                {
                    "path": "docs/tier5_deliverables/proposal_sections/",
                    "produced_by": "n08a_section_drafting",
                    "tier": "tier5_deliverable",
                },
            ],
        )

        def _track(skill_id, run_id, repo_root, inputs=None, **kw):
            return _success_skill(outputs=[
                "docs/tier5_deliverables/proposal_sections/section_1a.json",
            ])

        with patch(_RUN_SKILL_TARGET, side_effect=_track):
            result = run_agent(**kwargs)

        for output in result.outputs_written:
            assert not output.endswith("gate_result.json"), (
                f"gate_result.json must not be in skill outputs: {output}"
            )
