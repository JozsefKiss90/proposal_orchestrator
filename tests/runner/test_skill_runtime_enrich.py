"""
Tests for the ``enrich_artifact`` output contract in ``runner.skill_runtime``.

Covers:
  - Happy path: enrichment patch merged into base artifact, all fields present
  - Base artifact field preservation (impact_pathways, kpis untouched)
  - Patch schema_id / run_id mismatch → rejected
  - Patch containing artifact_status → rejected
  - Merged result failing full-schema validation → rejected
  - Missing base artifact → MISSING_INPUT
  - Missing enrichment_base_artifact config → MALFORMED_ARTIFACT
  - Wrapped/contaminated response → rejected (not valid JSON)
  - Gate sees non-null DEC fields after successful enrichment

All tests use synthetic skill catalogs and mock the Claude runtime transport.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from runner.runtime_models import SkillResult
from runner.skill_runtime import (
    _extract_json_response,
    run_skill,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic enrichment environment
# ---------------------------------------------------------------------------

_TRANSPORT_TARGET = "runner.skill_runtime.invoke_claude_text"

_BASE_ARTIFACT_REL = (
    "docs/tier4/phase5/impact_architecture.json"
)

_IMPACT_SCHEMA_ID = "orch.phase5.impact_architecture.v1"


def _write_skill_catalog(repo_root: Path, entries: list[dict]) -> None:
    catalog_path = (
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "skill_catalog.yaml"
    )
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        yaml.dump({"skill_catalog": entries}), encoding="utf-8"
    )


def _write_artifact_schema(repo_root: Path) -> None:
    spec_path = (
        repo_root / ".claude" / "workflows" / "system_orchestration"
        / "artifact_schema_specification.yaml"
    )
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    schemas = {
        "tier4_phase_output_schemas": {
            "impact_architecture": {
                "canonical_path": _BASE_ARTIFACT_REL,
                "schema_id_value": _IMPACT_SCHEMA_ID,
                "fields": {
                    "schema_id": {"required": True},
                    "run_id": {"required": True},
                    "impact_pathways": {"required": True},
                    "kpis": {"required": True},
                    "dissemination_plan": {"required": True},
                    "exploitation_plan": {"required": True},
                    "sustainability_mechanism": {"required": True},
                },
            }
        }
    }
    spec_path.write_text(yaml.dump(schemas), encoding="utf-8")


def _write_skill_spec(repo_root: Path, skill_id: str) -> None:
    spec_path = repo_root / ".claude" / "skills" / f"{skill_id}.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(f"# {skill_id}\nTest skill spec.", encoding="utf-8")


def _base_artifact(run_id: str = "run-enrich-001") -> dict:
    """A valid partial impact_architecture.json (core-builder output)."""
    return {
        "schema_id": _IMPACT_SCHEMA_ID,
        "run_id": run_id,
        "impact_pathways": [
            {
                "pathway_id": "PATH-01",
                "expected_impact_id": "EI-01",
                "project_outputs": ["D1-01"],
                "outcomes": ["OUT-1"],
                "impact_narrative": "Test pathway narrative.",
                "tier2b_source_ref": "expected_impacts.json:EI-01",
            }
        ],
        "kpis": [
            {
                "kpi_id": "KPI-01",
                "description": "Test KPI",
                "target": ">=1",
                "measurement_method": "Count",
                "traceable_to_deliverable": "D1-01",
            }
        ],
        "dissemination_plan": None,
        "exploitation_plan": None,
        "sustainability_mechanism": None,
    }


def _enrichment_patch(run_id: str = "run-enrich-001") -> dict:
    """A valid enrichment patch with only the 3 DEC fields + metadata."""
    return {
        "schema_id": _IMPACT_SCHEMA_ID,
        "run_id": run_id,
        "dissemination_plan": {
            "activities": [
                {
                    "activity_type": "conference_presentation",
                    "target_audience": "AI researchers at NeurIPS",
                    "responsible_partner": "ATU",
                    "timing": "M24",
                }
            ],
            "open_access_policy": "All publications deposited in Zenodo.",
        },
        "exploitation_plan": {
            "activities": [
                {
                    "activity_type": "technology_transfer",
                    "expected_result": "3 SMEs adopting framework",
                    "responsible_partner": "BAL",
                    "timing": "M48",
                }
            ],
            "ipr_strategy": "Apache 2.0 open-source for core components.",
        },
        "sustainability_mechanism": {
            "description": "Open-source governance charter maintained by ATU.",
            "responsible_partners": ["ATU", "BAL"],
        },
    }


def _make_enrich_env(
    tmp_path: Path,
    *,
    run_id: str = "run-enrich-001",
    write_base: bool = True,
    base_content: dict | None = None,
    extra_catalog_entries: list[dict] | None = None,
) -> Path:
    """Create a synthetic environment for enrich_artifact tests."""
    repo_root = tmp_path

    entries = [
        {
            "id": "test-enricher",
            "execution_mode": "tapm",
            "output_contract": "enrich_artifact",
            "enrichment_base_artifact": _BASE_ARTIFACT_REL,
            "reads_from": [
                "docs/tier4/phase5/",
                "docs/tier3/impacts.json",
            ],
            "writes_to": [
                "docs/tier4/phase5/",
            ],
            "constitutional_constraints": [
                "DEC plans must be project-specific",
            ],
        },
    ]
    if extra_catalog_entries:
        entries.extend(extra_catalog_entries)

    _write_skill_catalog(repo_root, entries)
    _write_artifact_schema(repo_root)
    _write_skill_spec(repo_root, "test-enricher")

    # Base artifact (partial — core-builder output)
    if write_base:
        content = base_content if base_content is not None else _base_artifact(run_id)
        base_path = repo_root / _BASE_ARTIFACT_REL
        base_path.parent.mkdir(parents=True, exist_ok=True)
        base_path.write_text(json.dumps(content, indent=2), encoding="utf-8")

    # Required reads_from input
    impacts_path = repo_root / "docs" / "tier3" / "impacts.json"
    impacts_path.parent.mkdir(parents=True, exist_ok=True)
    impacts_path.write_text(json.dumps({"impacts": []}), encoding="utf-8")

    return repo_root


@pytest.fixture()
def enrich_env(tmp_path: Path) -> Path:
    """Fresh synthetic enrichment environment."""
    import runner.skill_runtime as _sr
    _sr._catalog_cache.clear()
    _sr._schema_spec_cache.clear()
    return _make_enrich_env(tmp_path)


def _claude_returns(response_dict: dict):
    return patch(_TRANSPORT_TARGET, return_value=json.dumps(response_dict))


def _claude_returns_text(text: str):
    return patch(_TRANSPORT_TARGET, return_value=text)


# ---------------------------------------------------------------------------
# Happy path — enrichment merge succeeds
# ---------------------------------------------------------------------------


class TestEnrichArtifactSuccess:
    def test_enrichment_merges_patch_into_base(self, enrich_env: Path) -> None:
        """Enrichment patch fields are merged into the base artifact."""
        patch_data = _enrichment_patch()
        with _claude_returns(patch_data):
            result = run_skill("test-enricher", "run-enrich-001", enrich_env)

        assert result.status == "success"
        assert _BASE_ARTIFACT_REL in result.outputs_written

        # Read the written artifact
        written = json.loads(
            (enrich_env / _BASE_ARTIFACT_REL).read_text(encoding="utf-8")
        )

        # DEC fields populated
        assert written["dissemination_plan"] is not None
        assert written["exploitation_plan"] is not None
        assert written["sustainability_mechanism"] is not None
        assert len(written["dissemination_plan"]["activities"]) == 1
        assert written["dissemination_plan"]["open_access_policy"] != ""

    def test_base_fields_preserved(self, enrich_env: Path) -> None:
        """impact_pathways and kpis from the base artifact are preserved."""
        original_base = _base_artifact()
        patch_data = _enrichment_patch()

        with _claude_returns(patch_data):
            result = run_skill("test-enricher", "run-enrich-001", enrich_env)

        assert result.status == "success"
        written = json.loads(
            (enrich_env / _BASE_ARTIFACT_REL).read_text(encoding="utf-8")
        )

        # Pathways and KPIs preserved verbatim from base
        assert written["impact_pathways"] == original_base["impact_pathways"]
        assert written["kpis"] == original_base["kpis"]
        assert written["schema_id"] == _IMPACT_SCHEMA_ID
        assert written["run_id"] == "run-enrich-001"

    def test_all_seven_fields_present_in_merged(self, enrich_env: Path) -> None:
        """Merged artifact has all 7 required fields."""
        with _claude_returns(_enrichment_patch()):
            result = run_skill("test-enricher", "run-enrich-001", enrich_env)

        assert result.status == "success"
        written = json.loads(
            (enrich_env / _BASE_ARTIFACT_REL).read_text(encoding="utf-8")
        )

        required_fields = [
            "schema_id", "run_id", "impact_pathways", "kpis",
            "dissemination_plan", "exploitation_plan", "sustainability_mechanism",
        ]
        for field in required_fields:
            assert field in written, f"Missing field: {field}"
            assert written[field] is not None, f"Field is null: {field}"

    def test_gate_sees_nonnull_dec_fields(self, enrich_env: Path) -> None:
        """After enrichment, all three DEC fields are non-null (gate predicates pass)."""
        with _claude_returns(_enrichment_patch()):
            run_skill("test-enricher", "run-enrich-001", enrich_env)

        written = json.loads(
            (enrich_env / _BASE_ARTIFACT_REL).read_text(encoding="utf-8")
        )

        # These are the exact gate predicates that failed in the c4d3d0a6 run
        assert written["dissemination_plan"] is not None
        assert written["exploitation_plan"] is not None
        assert written["sustainability_mechanism"] is not None


# ---------------------------------------------------------------------------
# Validation failures — patch rejected
# ---------------------------------------------------------------------------


class TestEnrichArtifactValidation:
    def test_schema_id_mismatch_rejected(self, enrich_env: Path) -> None:
        """Patch with wrong schema_id is rejected."""
        patch_data = _enrichment_patch()
        patch_data["schema_id"] = "wrong_schema_v1"

        with _claude_returns(patch_data):
            result = run_skill("test-enricher", "run-enrich-001", enrich_env)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"
        assert "schema_id mismatch" in result.failure_reason

    def test_run_id_mismatch_rejected(self, enrich_env: Path) -> None:
        """Patch with wrong run_id is rejected."""
        patch_data = _enrichment_patch()
        patch_data["run_id"] = "wrong-run-id"

        with _claude_returns(patch_data):
            result = run_skill("test-enricher", "run-enrich-001", enrich_env)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"
        assert "run_id mismatch" in result.failure_reason

    def test_artifact_status_in_patch_rejected(self, enrich_env: Path) -> None:
        """Patch containing artifact_status is rejected."""
        patch_data = _enrichment_patch()
        patch_data["artifact_status"] = "validated"

        with _claude_returns(patch_data):
            result = run_skill("test-enricher", "run-enrich-001", enrich_env)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"
        assert "artifact_status" in result.failure_reason

    def test_merged_result_missing_required_field_rejected(
        self, tmp_path: Path
    ) -> None:
        """If base artifact is missing a required field, merged validation fails."""
        import runner.skill_runtime as _sr
        _sr._catalog_cache.clear()
        _sr._schema_spec_cache.clear()

        # Base artifact missing kpis entirely
        broken_base = _base_artifact()
        del broken_base["kpis"]

        repo_root = _make_enrich_env(
            tmp_path, base_content=broken_base
        )

        with _claude_returns(_enrichment_patch()):
            result = run_skill("test-enricher", "run-enrich-001", repo_root)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"
        assert "kpis" in result.failure_reason


# ---------------------------------------------------------------------------
# Missing inputs — base artifact absent or unreadable
# ---------------------------------------------------------------------------


class TestEnrichArtifactMissingInputs:
    def test_missing_base_artifact(self, tmp_path: Path) -> None:
        """Missing base artifact returns MISSING_INPUT."""
        import runner.skill_runtime as _sr
        _sr._catalog_cache.clear()
        _sr._schema_spec_cache.clear()

        repo_root = _make_enrich_env(tmp_path, write_base=False)

        with _claude_returns(_enrichment_patch()):
            result = run_skill("test-enricher", "run-enrich-001", repo_root)

        assert result.status == "failure"
        assert result.failure_category == "MISSING_INPUT"
        assert "not found" in result.failure_reason

    def test_missing_catalog_config(self, tmp_path: Path) -> None:
        """Missing enrichment_base_artifact config returns MALFORMED_ARTIFACT."""
        import runner.skill_runtime as _sr
        _sr._catalog_cache.clear()
        _sr._schema_spec_cache.clear()

        repo_root = tmp_path

        # Catalog entry WITHOUT enrichment_base_artifact
        _write_skill_catalog(repo_root, [
            {
                "id": "test-enricher",
                "execution_mode": "tapm",
                "output_contract": "enrich_artifact",
                # no enrichment_base_artifact
                "reads_from": ["docs/tier4/phase5/"],
                "writes_to": ["docs/tier4/phase5/"],
                "constitutional_constraints": [],
            },
        ])
        _write_artifact_schema(repo_root)
        _write_skill_spec(repo_root, "test-enricher")

        # Create directory so TAPM reads_from doesn't cause issues
        (repo_root / "docs" / "tier4" / "phase5").mkdir(parents=True, exist_ok=True)

        with _claude_returns(_enrichment_patch()):
            result = run_skill("test-enricher", "run-enrich-001", repo_root)

        assert result.status == "failure"
        assert result.failure_category == "MALFORMED_ARTIFACT"
        assert "enrichment_base_artifact" in result.failure_reason


# ---------------------------------------------------------------------------
# Response format robustness — wrapped/contaminated responses
# ---------------------------------------------------------------------------


class TestEnrichArtifactResponseFormat:
    def test_non_json_response_rejected(self, enrich_env: Path) -> None:
        """Non-JSON response is rejected before enrichment merge."""
        with _claude_returns_text("Here is the enrichment plan..."):
            result = run_skill("test-enricher", "run-enrich-001", enrich_env)

        assert result.status == "failure"
        assert result.failure_category == "INCOMPLETE_OUTPUT"
        assert "non-JSON" in result.failure_reason

    def test_compact_valid_json_accepted(self, enrich_env: Path) -> None:
        """Compact (non-pretty-printed) valid JSON is accepted."""
        compact_json = json.dumps(_enrichment_patch(), separators=(",", ":"))
        with _claude_returns_text(compact_json):
            result = run_skill("test-enricher", "run-enrich-001", enrich_env)

        assert result.status == "success"

    def test_model_signaled_failure_intercepted(self, enrich_env: Path) -> None:
        """Claude returning a SkillResult-shaped failure is intercepted."""
        failure_envelope = {
            "status": "failure",
            "failure_reason": "MISSING_INPUT: impacts.json not found",
            "failure_category": "MISSING_INPUT",
        }
        with _claude_returns(failure_envelope):
            result = run_skill("test-enricher", "run-enrich-001", enrich_env)

        assert result.status == "failure"
        assert "model-signaled failure" in result.failure_reason


# ---------------------------------------------------------------------------
# Parser behavior for large JSON (regression test for the original bug)
# ---------------------------------------------------------------------------


class TestExtractJsonLargeResponse:
    def test_valid_large_json_parsed(self) -> None:
        """A large but valid JSON object is successfully parsed."""
        large_obj = {
            "schema_id": "test_v1",
            "run_id": "run-001",
            "data": "x" * 20000,
        }
        text = json.dumps(large_obj)
        result = _extract_json_response(text)
        assert result is not None
        assert result["schema_id"] == "test_v1"

    def test_structurally_invalid_json_rejected(self) -> None:
        """The exact failure pattern from run c4d3d0a6 is correctly rejected.

        Claude emitted '},{"exploitation_plan":' instead of ',"exploitation_plan":',
        creating an object value without a key in the parent object.
        """
        # Simulate the malformation: valid start, then },{ in middle
        malformed = (
            '{"schema_id":"test_v1","dissemination_plan":{"a":1}'
            ',{"exploitation_plan":{"b":2},"sustainability":{"c":3}}'
        )
        result = _extract_json_response(malformed)
        # This MUST return None — the JSON is structurally invalid
        assert result is None

    def test_valid_enrichment_patch_parsed(self) -> None:
        """A well-formed enrichment patch (smaller output) is parsed successfully."""
        patch = _enrichment_patch()
        text = json.dumps(patch)
        result = _extract_json_response(text)
        assert result is not None
        assert result["dissemination_plan"] is not None
        assert result["exploitation_plan"] is not None
        assert result["sustainability_mechanism"] is not None
