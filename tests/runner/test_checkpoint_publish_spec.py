"""
Targeted tests for checkpoint-publish skill spec alignment with
the decomposed Phase 8 gate model and TAPM execution mode.

Verifies that:
  - checkpoint-publish is registered as TAPM in skill_catalog.yaml
  - The spec contains the TAPM input access header (no inlined gate JSONs)
  - Legacy monolithic gate_10_result.json is NOT referenced as required
  - gate_12_result.json is NOT required (evaluated after checkpoint-publish)
  - All six decomposed gate result files are still required
  - gate_results_confirmed array contains the correct gate IDs
  - The spec is consistent with manifest.compile.yaml and gate_result_registry.py
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"
CATALOG_PATH = (
    REPO_ROOT / ".claude" / "workflows" / "system_orchestration"
    / "skill_catalog.yaml"
)


def _read_skill(name: str) -> str:
    path = SKILLS_DIR / name
    assert path.is_file(), f"Skill spec not found: {path}"
    return path.read_text(encoding="utf-8")


def _load_catalog() -> list[dict]:
    with open(CATALOG_PATH, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("skill_catalog", [])


def _find_catalog_entry(skill_id: str) -> dict:
    for entry in _load_catalog():
        if entry.get("id") == skill_id:
            return entry
    pytest.fail(f"Skill {skill_id!r} not found in skill_catalog.yaml")


# ===========================================================================
# 1. TAPM mode — catalog registration
# ===========================================================================


class TestTAPMCatalogRegistration:
    """checkpoint-publish must be registered as TAPM in skill_catalog.yaml."""

    def test_execution_mode_is_tapm(self) -> None:
        entry = _find_catalog_entry("checkpoint-publish")
        assert entry.get("execution_mode") == "tapm", (
            f"checkpoint-publish execution_mode is {entry.get('execution_mode')!r}, "
            f"expected 'tapm'"
        )


# ===========================================================================
# 2. TAPM mode — spec header
# ===========================================================================


class TestTAPMSpecHeader:
    """The spec must contain the TAPM input access section."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("checkpoint-publish.md")

    def test_tapm_header_present(self) -> None:
        assert "TAPM" in self.text

    def test_input_access_section_present(self) -> None:
        assert "Input Access (TAPM Mode)" in self.text

    def test_declared_input_files_listed(self) -> None:
        """Declared inputs must list paths, not inline JSON content."""
        assert "Declared input files to read" in self.text

    def test_no_inlined_gate_json_content(self) -> None:
        """The spec must NOT contain serialized gate result JSON content.
        It should list paths for Claude to read via the Read tool."""
        # A serialized gate result would contain these patterns together
        # in a JSON block — the spec should only have path references
        lines = self.text.split("\n")
        for i, line in enumerate(lines):
            # Skip the output schema example block
            if '"schema_id": "orch.gate_result.v1"' in line:
                # This would indicate inlined gate result content
                # But we allow it in prose descriptions
                context = "\n".join(lines[max(0, i - 3):i + 4])
                assert "```" in context or "must equal" in context or "verify" in context.lower(), (
                    f"Possible inlined gate result JSON at line {i + 1}: {line.strip()}"
                )


# ===========================================================================
# 3. Legacy gate_10 rejection
# ===========================================================================


class TestLegacyGate10Rejection:
    """checkpoint-publish must NOT reference the legacy monolithic gate_10."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("checkpoint-publish.md")

    def test_no_gate_10_result_json_as_required_input(self) -> None:
        """gate_10_result.json must not appear as a required file
        (only in a "Do NOT" context)."""
        lines = self.text.split("\n")
        for line in lines:
            if "gate_10_result.json" in line:
                lower = line.lower()
                assert any(
                    neg in lower
                    for neg in ["do not", "no longer", "legacy", "not read", "not require"]
                ), (
                    f"checkpoint-publish.md references gate_10_result.json "
                    f"without a negation context: {line.strip()}"
                )

    def test_no_gate_10_part_b_completeness_in_confirmed(self) -> None:
        assert "gate_10_part_b_completeness" not in self.text


# ===========================================================================
# 4. Decomposed gate references — all six required
# ===========================================================================


class TestDecomposedGateReferences:
    """checkpoint-publish must reference all six required gate result files."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("checkpoint-publish.md")

    def test_gate_10a_result_referenced(self) -> None:
        assert "gate_10a_result.json" in self.text

    def test_gate_10b_result_referenced(self) -> None:
        assert "gate_10b_result.json" in self.text

    def test_gate_10c_result_referenced(self) -> None:
        assert "gate_10c_result.json" in self.text

    def test_gate_10d_result_referenced(self) -> None:
        assert "gate_10d_result.json" in self.text

    def test_gate_11_result_referenced(self) -> None:
        assert "gate_11_result.json" in self.text

    def test_gate_09_budget_gate_referenced(self) -> None:
        assert "phase7_budget_gate/gate_result.json" in self.text

    def test_six_gate_files_required(self) -> None:
        """The spec must state that six gate result files are required."""
        assert "six" in self.text.lower()


# ===========================================================================
# 5. gate_12 optionality — must NOT be required
# ===========================================================================


class TestGate12Optionality:
    """gate_12 is evaluated AFTER checkpoint-publish; must NOT be required."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("checkpoint-publish.md")

    def test_gate_12_not_in_required_file_list(self) -> None:
        lines = self.text.split("\n")
        for line in lines:
            if "gate_12_result.json" in line:
                lower = line.lower()
                assert any(
                    neg in lower
                    for neg in ["do not", "not require", "not read", "not included"]
                ), (
                    f"checkpoint-publish.md references gate_12_result.json "
                    f"as a requirement: {line.strip()}"
                )

    def test_gate_12_not_in_confirmed_array(self) -> None:
        matches = re.findall(
            r'gate_results_confirmed.*?\[([^\]]+)\]',
            self.text,
            re.DOTALL,
        )
        for match in matches:
            assert "gate_12" not in match, (
                f"gate_results_confirmed array contains gate_12: {match}"
            )


# ===========================================================================
# 6. Fail-closed semantics preserved
# ===========================================================================


class TestFailClosedSemantics:
    """The spec must document failure for absent/non-pass gates."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("checkpoint-publish.md")

    def test_missing_input_failure(self) -> None:
        assert "MISSING_INPUT" in self.text

    def test_constraint_violation_failure(self) -> None:
        assert "CONSTRAINT_VIOLATION" in self.text

    def test_malformed_artifact_failure(self) -> None:
        assert "MALFORMED_ARTIFACT" in self.text

    def test_status_pass_check(self) -> None:
        assert '"pass"' in self.text

    def test_run_id_match_check(self) -> None:
        assert "run_id" in self.text


# ===========================================================================
# 7. Consistency with gate_result_registry.py
# ===========================================================================


class TestRegistryConsistency:
    """Gate result files in checkpoint-publish must match gate_result_registry."""

    def test_phase8_gate_paths_match_registry(self) -> None:
        from runner.gate_result_registry import GATE_RESULT_PATHS

        spec_text = _read_skill("checkpoint-publish.md")

        required_gates = [
            "gate_09_budget_consistency",
            "gate_10a_excellence_completeness",
            "gate_10b_impact_completeness",
            "gate_10c_implementation_completeness",
            "gate_10d_cross_section_consistency",
            "gate_11_review_closure",
        ]

        for gate_id in required_gates:
            assert gate_id in GATE_RESULT_PATHS
            # The gate_id must appear in the spec text
            assert gate_id in spec_text, (
                f"{gate_id} missing from checkpoint-publish.md"
            )

    def test_legacy_gate_10_absent_from_registry(self) -> None:
        from runner.gate_result_registry import GATE_RESULT_PATHS

        assert "gate_10_part_b_completeness" not in GATE_RESULT_PATHS


# ===========================================================================
# 8. Consistency with manifest.compile.yaml
# ===========================================================================


class TestManifestConsistency:
    """Gate expectations must match the manifest's Phase 8 gate definitions."""

    @pytest.fixture(autouse=True)
    def load_manifest(self) -> None:
        manifest_path = (
            REPO_ROOT / ".claude" / "workflows" / "system_orchestration"
            / "manifest.compile.yaml"
        )
        with open(manifest_path, encoding="utf-8") as f:
            self.manifest = yaml.safe_load(f)

    def _get_phase8_exit_gates(self) -> list[str]:
        gates = []
        for node in self.manifest.get("node_registry", []):
            if node.get("phase_number") == 8 and "exit_gate" in node:
                gates.append(node["exit_gate"])
        return gates

    def test_all_non_terminal_phase8_gates_in_spec(self) -> None:
        spec_text = _read_skill("checkpoint-publish.md")
        phase8_gates = self._get_phase8_exit_gates()
        non_terminal_gates = [
            g for g in phase8_gates
            if g != "gate_12_constitutional_compliance"
        ]
        for gate in non_terminal_gates:
            assert gate in spec_text, (
                f"Phase 8 gate {gate} from manifest not found in checkpoint-publish.md"
            )

    def test_n08f_exit_gate_is_gate_12(self) -> None:
        for node in self.manifest.get("node_registry", []):
            if node["node_id"] == "n08f_revision":
                assert node["exit_gate"] == "gate_12_constitutional_compliance"
                return
        pytest.fail("n08f_revision not found in manifest")

    def test_checkpoint_publish_is_skill_of_n08f(self) -> None:
        for node in self.manifest.get("node_registry", []):
            if node["node_id"] == "n08f_revision":
                assert "checkpoint-publish" in node.get("skills", [])
                return
        pytest.fail("n08f_revision not found in manifest")


# ===========================================================================
# 9. gate_results_confirmed content
# ===========================================================================


class TestGateResultsConfirmedContent:
    """The gate_results_confirmed array must contain the correct gate IDs."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("checkpoint-publish.md")

    def test_confirmed_contains_gate_09(self) -> None:
        assert "gate_09_budget_consistency" in self.text

    def test_confirmed_contains_all_decomposed_gates(self) -> None:
        for gate_id in [
            "gate_10a_excellence_completeness",
            "gate_10b_impact_completeness",
            "gate_10c_implementation_completeness",
            "gate_10d_cross_section_consistency",
        ]:
            assert gate_id in self.text

    def test_confirmed_contains_gate_11(self) -> None:
        assert "gate_11_review_closure" in self.text


# ===========================================================================
# 10. Output schema correctness
# ===========================================================================


class TestOutputSchema:
    """The spec must define the correct output schema for phase8_checkpoint.json."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("checkpoint-publish.md")

    def test_schema_id_defined(self) -> None:
        assert "orch.checkpoints.phase8_checkpoint.v1" in self.text

    def test_artifact_status_excluded(self) -> None:
        assert "artifact_status" in self.text
        # Must say it should NOT be added
        lower = self.text.lower()
        idx = lower.find("artifact_status")
        context = lower[max(0, idx - 40):idx + 80]
        assert "not" in context or "must not" in context
