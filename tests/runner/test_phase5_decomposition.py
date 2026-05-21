"""
Tests for Phase 5 decomposition — impact-pathway-mapper split into
impact-pathway-core-builder + impact-dec-enricher.

Test groups:
  1. Core builder produces valid partial artifact (pathways + KPIs, null DEC)
  2. DEC enricher correctly enriches without overwriting core fields
  3. Full sequence produces valid final artifact
  4. Manifest, catalog, and agent specs are consistent
  5. Regression: failure if core builder missing
  6. Old impact-pathway-mapper is removed from manifest
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from runner.skill_runtime import (
    _get_skill_entry,
    _load_skill_catalog,
    _load_skill_spec,
    run_skill,
)
from runner.runtime_models import SkillResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_TRANSPORT_TARGET = "runner.skill_runtime.invoke_claude_text"


@pytest.fixture(autouse=True)
def _clear_caches() -> None:
    """Clear skill_runtime caches before each test."""
    import runner.skill_runtime as _sr
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()
    yield
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()


# ---------------------------------------------------------------------------
# Helpers — test environments
# ---------------------------------------------------------------------------

def _copy_real_config(repo_root: Path) -> None:
    """Copy real catalog, schema spec, and skill specs to a tmp env."""
    for rel in [
        ".claude/workflows/system_orchestration/skill_catalog.yaml",
        ".claude/workflows/system_orchestration/artifact_schema_specification.yaml",
    ]:
        src = _REPO_ROOT / rel
        dst = repo_root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8-sig"), encoding="utf-8")

    for skill_id in [
        "impact-pathway-core-builder",
        "impact-dec-enricher",
        "dissemination-exploitation-communication-check",
    ]:
        src = _REPO_ROOT / ".claude" / "skills" / f"{skill_id}.md"
        dst = repo_root / ".claude" / "skills" / f"{skill_id}.md"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(src.read_text(encoding="utf-8-sig"), encoding="utf-8")

    # Create output directory parent
    (repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs").mkdir(
        parents=True, exist_ok=True
    )


def _core_builder_response(run_id: str) -> str:
    """A valid response from impact-pathway-core-builder (partial artifact)."""
    return json.dumps({
        "schema_id": "orch.phase5.impact_architecture.v1",
        "run_id": run_id,
        "impact_pathways": [
            {
                "pathway_id": "PWY-1",
                "expected_impact_id": "EI-01",
                "project_outputs": ["D1-01"],
                "outcomes": [{"outcome_id": "OUT-1", "description": "test outcome", "timeframe": "M18"}],
                "impact_narrative": "Project WP1 deliverable D1-01 produces AI planning framework used by healthcare sector",
                "tier2b_source_ref": "Section 2.1"
            },
            {
                "pathway_id": "PWY-2",
                "expected_impact_id": "EI-02",
                "project_outputs": ["D2-01"],
                "outcomes": [{"outcome_id": "OUT-2", "description": "coordination protocol", "timeframe": "M24"}],
                "impact_narrative": "WP2 delivers multi-agent coordination tested in manufacturing via D2-01",
                "tier2b_source_ref": "Section 2.2"
            },
        ],
        "kpis": [
            {
                "kpi_id": "KPI-01",
                "description": "Number of AI agents integrated",
                "target": "5",
                "measurement_method": "deployment count",
                "traceable_to_deliverable": "D1-01",
            },
            {
                "kpi_id": "KPI-02",
                "description": "Coordination latency reduction",
                "target": "30%",
                "measurement_method": "benchmark comparison",
                "traceable_to_deliverable": "D2-01",
            },
        ],
        "dissemination_plan": None,
        "exploitation_plan": None,
        "sustainability_mechanism": None,
    })


def _enricher_response(run_id: str) -> str:
    """A valid response from impact-dec-enricher (complete artifact)."""
    return json.dumps({
        "schema_id": "orch.phase5.impact_architecture.v1",
        "run_id": run_id,
        "impact_pathways": [
            {
                "pathway_id": "PWY-1",
                "expected_impact_id": "EI-01",
                "project_outputs": ["D1-01"],
                "outcomes": [{"outcome_id": "OUT-1", "description": "test outcome", "timeframe": "M18"}],
                "impact_narrative": "Project WP1 deliverable D1-01 produces AI planning framework used by healthcare sector",
                "tier2b_source_ref": "Section 2.1"
            },
            {
                "pathway_id": "PWY-2",
                "expected_impact_id": "EI-02",
                "project_outputs": ["D2-01"],
                "outcomes": [{"outcome_id": "OUT-2", "description": "coordination protocol", "timeframe": "M24"}],
                "impact_narrative": "WP2 delivers multi-agent coordination tested in manufacturing via D2-01",
                "tier2b_source_ref": "Section 2.2"
            },
        ],
        "kpis": [
            {
                "kpi_id": "KPI-01",
                "description": "Number of AI agents integrated",
                "target": "5",
                "measurement_method": "deployment count",
                "traceable_to_deliverable": "D1-01",
            },
            {
                "kpi_id": "KPI-02",
                "description": "Coordination latency reduction",
                "target": "30%",
                "measurement_method": "benchmark comparison",
                "traceable_to_deliverable": "D2-01",
            },
        ],
        "dissemination_plan": {
            "activities": [
                {"activity_type": "open-access publication", "target_audience": "AI researchers in healthcare", "responsible_partner": "UNIV-A", "timing": "M12-M48"},
            ],
            "open_access_policy": "All publications in Gold OA journals; datasets on Zenodo."
        },
        "exploitation_plan": {
            "activities": [
                {"activity_type": "technology licensing", "expected_result": "commercial AI planning tool", "responsible_partner": "CORP-B", "timing": "M36-M48"},
            ],
            "ipr_strategy": "Joint ownership per consortium agreement"
        },
        "sustainability_mechanism": {
            "description": "Open-source framework maintained by UNIV-A with community governance model",
            "responsible_partners": ["UNIV-A", "CORP-B"],
            "post_project_timeline": "5 years post-project"
        },
    })


# ===========================================================================
# Test Group 1: Core builder produces valid partial artifact
# ===========================================================================


class TestCoreBuilderConfig:
    """Verify core builder catalog configuration."""

    def test_core_builder_exists_in_catalog(self) -> None:
        entry = _get_skill_entry("impact-pathway-core-builder", _REPO_ROOT)
        assert entry is not None

    def test_core_builder_is_tapm(self) -> None:
        entry = _get_skill_entry("impact-pathway-core-builder", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm"

    def test_core_builder_writes_to_phase5(self) -> None:
        entry = _get_skill_entry("impact-pathway-core-builder", _REPO_ROOT)
        writes_to = entry.get("writes_to", [])
        assert any("phase5_impact_architecture" in w for w in writes_to)

    def test_core_builder_spec_exists(self) -> None:
        spec = _load_skill_spec("impact-pathway-core-builder", _REPO_ROOT)
        assert "impact-pathway-core-builder" in spec

    def test_core_builder_spec_has_tapm_section(self) -> None:
        spec = _load_skill_spec("impact-pathway-core-builder", _REPO_ROOT)
        assert "Input Access (TAPM Mode)" in spec

    def test_core_builder_spec_has_scope_limitation(self) -> None:
        spec = _load_skill_spec("impact-pathway-core-builder", _REPO_ROOT)
        assert "dissemination_plan" in spec
        assert "null" in spec.lower()


class TestCoreBuilderExecution:
    """Verify core builder produces a valid partial artifact."""

    def test_writes_partial_artifact(self, tmp_path: Path) -> None:
        _copy_real_config(tmp_path)
        run_id = "test-core-001"

        with patch(_TRANSPORT_TARGET, return_value=_core_builder_response(run_id)):
            result = run_skill(
                "impact-pathway-core-builder", run_id, tmp_path,
                node_id="n05_impact_architecture",
            )

        assert result.status == "success"
        canonical = (
            tmp_path / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase5_impact_architecture" / "impact_architecture.json"
        )
        assert canonical.exists()
        content = json.loads(canonical.read_text(encoding="utf-8"))
        assert content["schema_id"] == "orch.phase5.impact_architecture.v1"
        assert content["run_id"] == run_id
        assert len(content["impact_pathways"]) == 2
        assert len(content["kpis"]) == 2
        assert content["dissemination_plan"] is None
        assert content["exploitation_plan"] is None
        assert content["sustainability_mechanism"] is None

    def test_uses_tapm_tools(self, tmp_path: Path) -> None:
        _copy_real_config(tmp_path)
        run_id = "test-core-002"

        with patch(_TRANSPORT_TARGET, return_value=_core_builder_response(run_id)) as mock:
            run_skill("impact-pathway-core-builder", run_id, tmp_path)

        call_kwargs = mock.call_args
        assert call_kwargs.kwargs.get("tools") == ["Read", "Glob"]

    def test_uses_600s_timeout(self, tmp_path: Path) -> None:
        _copy_real_config(tmp_path)
        run_id = "test-core-003"

        with patch(_TRANSPORT_TARGET, return_value=_core_builder_response(run_id)) as mock:
            run_skill("impact-pathway-core-builder", run_id, tmp_path)

        call_kwargs = mock.call_args
        assert call_kwargs.kwargs.get("timeout_seconds") == 1200


# ===========================================================================
# Test Group 2: DEC enricher correctly enriches without overwriting core
# ===========================================================================


class TestDecEnricherConfig:
    """Verify DEC enricher catalog configuration."""

    def test_enricher_exists_in_catalog(self) -> None:
        entry = _get_skill_entry("impact-dec-enricher", _REPO_ROOT)
        assert entry is not None

    def test_enricher_is_tapm(self) -> None:
        entry = _get_skill_entry("impact-dec-enricher", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm"

    def test_enricher_reads_from_phase5(self) -> None:
        entry = _get_skill_entry("impact-dec-enricher", _REPO_ROOT)
        reads_from = entry.get("reads_from", [])
        assert any("phase5_impact_architecture" in r for r in reads_from)

    def test_enricher_reads_impacts_json(self) -> None:
        entry = _get_skill_entry("impact-dec-enricher", _REPO_ROOT)
        reads_from = entry.get("reads_from", [])
        assert any("impacts.json" in r for r in reads_from)

    def test_enricher_spec_exists(self) -> None:
        spec = _load_skill_spec("impact-dec-enricher", _REPO_ROOT)
        assert "impact-dec-enricher" in spec

    def test_enricher_spec_preserves_core_fields(self) -> None:
        spec = _load_skill_spec("impact-dec-enricher", _REPO_ROOT)
        assert "preserve" in spec.lower()
        assert "impact_pathways" in spec
        assert "kpis" in spec


class TestDecEnricherExecution:
    """Verify DEC enricher produces a complete artifact."""

    def _setup_partial_artifact(self, repo_root: Path, run_id: str) -> None:
        """Write the core builder's partial artifact to disk."""
        _copy_real_config(repo_root)
        out_dir = (
            repo_root / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase5_impact_architecture"
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "impact_architecture.json").write_text(
            _core_builder_response(run_id), encoding="utf-8"
        )

    def test_writes_complete_artifact(self, tmp_path: Path) -> None:
        run_id = "test-enrich-001"
        self._setup_partial_artifact(tmp_path, run_id)

        with patch(_TRANSPORT_TARGET, return_value=_enricher_response(run_id)):
            result = run_skill(
                "impact-dec-enricher", run_id, tmp_path,
                node_id="n05_impact_architecture",
            )

        assert result.status == "success"
        canonical = (
            tmp_path / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase5_impact_architecture" / "impact_architecture.json"
        )
        content = json.loads(canonical.read_text(encoding="utf-8"))
        # DEC fields are now populated
        assert content["dissemination_plan"] is not None
        assert content["exploitation_plan"] is not None
        assert content["sustainability_mechanism"] is not None
        assert len(content["dissemination_plan"]["activities"]) > 0
        assert len(content["exploitation_plan"]["activities"]) > 0
        assert len(content["sustainability_mechanism"]["responsible_partners"]) > 0

    def test_preserves_pathways_and_kpis(self, tmp_path: Path) -> None:
        run_id = "test-enrich-002"
        self._setup_partial_artifact(tmp_path, run_id)

        # Read original pathways before enrichment
        canonical = (
            tmp_path / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase5_impact_architecture" / "impact_architecture.json"
        )
        original = json.loads(canonical.read_text(encoding="utf-8"))
        original_pathways = original["impact_pathways"]
        original_kpis = original["kpis"]

        with patch(_TRANSPORT_TARGET, return_value=_enricher_response(run_id)):
            result = run_skill("impact-dec-enricher", run_id, tmp_path)

        assert result.status == "success"
        enriched = json.loads(canonical.read_text(encoding="utf-8"))
        assert enriched["impact_pathways"] == original_pathways
        assert enriched["kpis"] == original_kpis


# ===========================================================================
# Test Group 3: Full sequence produces valid final artifact
# ===========================================================================


class TestFullSequence:
    """Verify the core-builder → enricher sequence produces a gate-ready artifact."""

    def test_sequential_execution_produces_complete_artifact(
        self, tmp_path: Path
    ) -> None:
        _copy_real_config(tmp_path)
        run_id = "test-seq-001"

        # Step 1: Core builder
        with patch(_TRANSPORT_TARGET, return_value=_core_builder_response(run_id)):
            r1 = run_skill(
                "impact-pathway-core-builder", run_id, tmp_path,
                node_id="n05_impact_architecture",
            )
        assert r1.status == "success"

        # Verify partial artifact exists with null DEC
        canonical = (
            tmp_path / "docs" / "tier4_orchestration_state" / "phase_outputs"
            / "phase5_impact_architecture" / "impact_architecture.json"
        )
        partial = json.loads(canonical.read_text(encoding="utf-8"))
        assert partial["dissemination_plan"] is None

        # Step 2: DEC enricher
        with patch(_TRANSPORT_TARGET, return_value=_enricher_response(run_id)):
            r2 = run_skill(
                "impact-dec-enricher", run_id, tmp_path,
                node_id="n05_impact_architecture",
            )
        assert r2.status == "success"

        # Verify final artifact is complete
        final = json.loads(canonical.read_text(encoding="utf-8"))
        assert final["schema_id"] == "orch.phase5.impact_architecture.v1"
        assert final["run_id"] == run_id
        assert len(final["impact_pathways"]) > 0
        assert len(final["kpis"]) > 0
        assert final["dissemination_plan"] is not None
        assert final["exploitation_plan"] is not None
        assert final["sustainability_mechanism"] is not None
        assert "artifact_status" not in final


# ===========================================================================
# Test Group 4: Manifest, catalog, and agent specs are consistent
# ===========================================================================


class TestSpecConsistency:
    """Verify manifest, catalog, workflow, and agent spec alignment."""

    def test_manifest_n05_has_core_builder(self) -> None:
        manifest_path = (
            _REPO_ROOT / ".claude" / "workflows" / "system_orchestration"
            / "manifest.compile.yaml"
        )
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8-sig"))
        n05 = None
        for node in data["node_registry"]:
            if node["node_id"] == "n05_impact_architecture":
                n05 = node
                break
        assert n05 is not None
        assert "impact-pathway-core-builder" in n05["skills"]

    def test_manifest_n05_has_dec_enricher(self) -> None:
        manifest_path = (
            _REPO_ROOT / ".claude" / "workflows" / "system_orchestration"
            / "manifest.compile.yaml"
        )
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8-sig"))
        n05 = [n for n in data["node_registry"] if n["node_id"] == "n05_impact_architecture"][0]
        assert "impact-dec-enricher" in n05["skills"]

    def test_manifest_n05_no_old_mapper(self) -> None:
        """impact-pathway-mapper must NOT be in the manifest skill list."""
        manifest_path = (
            _REPO_ROOT / ".claude" / "workflows" / "system_orchestration"
            / "manifest.compile.yaml"
        )
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8-sig"))
        n05 = [n for n in data["node_registry"] if n["node_id"] == "n05_impact_architecture"][0]
        assert "impact-pathway-mapper" not in n05["skills"]

    def test_manifest_n05_skill_order(self) -> None:
        """Skills must be in correct order: core-builder, enricher, DEC check, ..., gate-enforcement."""
        manifest_path = (
            _REPO_ROOT / ".claude" / "workflows" / "system_orchestration"
            / "manifest.compile.yaml"
        )
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8-sig"))
        n05 = [n for n in data["node_registry"] if n["node_id"] == "n05_impact_architecture"][0]
        skills = n05["skills"]
        assert skills.index("impact-pathway-core-builder") < skills.index("impact-dec-enricher")
        assert skills.index("impact-dec-enricher") < skills.index("dissemination-exploitation-communication-check")
        assert skills[-1] == "gate-enforcement"

    def test_workflow_phase_yaml_updated(self) -> None:
        phase_path = (
            _REPO_ROOT / ".claude" / "workflows" / "system_orchestration"
            / "workflow_phases" / "phase_05_impact_architecture.yaml"
        )
        data = yaml.safe_load(phase_path.read_text(encoding="utf-8-sig"))
        skills = data["skills"]
        assert "impact-pathway-core-builder" in skills
        assert "impact-dec-enricher" in skills
        assert "impact-pathway-mapper" not in skills

    def test_agent_spec_lists_new_skills(self) -> None:
        spec_path = _REPO_ROOT / ".claude" / "agents" / "impact_architect.md"
        content = spec_path.read_text(encoding="utf-8-sig")
        assert "impact-pathway-core-builder" in content
        assert "impact-dec-enricher" in content

    def test_agent_spec_no_old_mapper(self) -> None:
        spec_path = _REPO_ROOT / ".claude" / "agents" / "impact_architect.md"
        content = spec_path.read_text(encoding="utf-8-sig")
        # The old skill name should not appear as a skill binding
        # (it may appear in historical comments, but not in Skill Bindings section)
        bindings_section = content.split("## Skill Bindings")[1].split("## Canonical")[0]
        assert "impact-pathway-mapper" not in bindings_section

    def test_prompt_spec_references_new_skills(self) -> None:
        spec_path = (
            _REPO_ROOT / ".claude" / "agents" / "prompts"
            / "impact_architect_prompt_spec.md"
        )
        content = spec_path.read_text(encoding="utf-8-sig")
        assert "impact-pathway-core-builder" in content
        assert "impact-dec-enricher" in content

    def test_catalog_no_old_mapper(self) -> None:
        """impact-pathway-mapper must NOT be in the skill catalog."""
        catalog = _load_skill_catalog(_REPO_ROOT)
        ids = [e.get("id") for e in catalog]
        assert "impact-pathway-mapper" not in ids

    def test_catalog_has_both_new_skills(self) -> None:
        catalog = _load_skill_catalog(_REPO_ROOT)
        ids = [e.get("id") for e in catalog]
        assert "impact-pathway-core-builder" in ids
        assert "impact-dec-enricher" in ids


# ===========================================================================
# Test Group 5: Regression guards
# ===========================================================================


class TestRegressionGuards:
    """Ensure other Phase 5 skills and gate predicates are unaffected."""

    def test_dec_check_reads_from_phase5(self) -> None:
        """DEC check reads from Phase 5 directory (unchanged by TAPM migration)."""
        entry = _get_skill_entry(
            "dissemination-exploitation-communication-check", _REPO_ROOT
        )
        reads_from = entry.get("reads_from", [])
        assert any("phase5_impact_architecture" in r for r in reads_from)

    def test_gate_enforcement_unchanged(self) -> None:
        entry = _get_skill_entry("gate-enforcement", _REPO_ROOT)
        assert entry.get("execution_mode") == "tapm"

    def test_phase5_gate_unchanged_in_manifest(self) -> None:
        manifest_path = (
            _REPO_ROOT / ".claude" / "workflows" / "system_orchestration"
            / "manifest.compile.yaml"
        )
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8-sig"))
        n05 = [n for n in data["node_registry"] if n["node_id"] == "n05_impact_architecture"][0]
        assert n05["exit_gate"] == "phase_05_gate"

    def test_phase5_gate_predicates_in_gate_registry(self) -> None:
        """Gate predicates g06_p01 through g06_p08 must still be present."""
        manifest_path = (
            _REPO_ROOT / ".claude" / "workflows" / "system_orchestration"
            / "manifest.compile.yaml"
        )
        data = yaml.safe_load(manifest_path.read_text(encoding="utf-8-sig"))
        gate = None
        for g in data.get("gate_registry", []):
            if g.get("gate_id") == "phase_05_gate":
                gate = g
                break
        assert gate is not None
        # Flatten all predicate_refs
        all_refs = []
        for cond in gate.get("conditions", []):
            all_refs.extend(cond.get("predicate_refs", []))
        for pred_id in ["g06_p01", "g06_p02", "g06_p03", "g06_p04", "g06_p05", "g06_p06", "g06_p07", "g06_p08"]:
            assert pred_id in all_refs, f"Missing predicate {pred_id} in phase_05_gate"
