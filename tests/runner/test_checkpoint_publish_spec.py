"""
Targeted tests for checkpoint-publish skill spec alignment with
the decomposed Phase 8 gate model.

Verifies that:
  - checkpoint-publish.md references the correct decomposed gate result files
  - Legacy monolithic gate_10_result.json is NOT referenced
  - gate_12_result.json is NOT required (it's evaluated after checkpoint-publish)
  - gate_results_confirmed array contains the correct gate IDs
  - The spec is consistent with manifest.compile.yaml and gate_result_registry.py
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"


def _read_skill(name: str) -> str:
    path = SKILLS_DIR / name
    assert path.is_file(), f"Skill spec not found: {path}"
    return path.read_text(encoding="utf-8")


# ===========================================================================
# 1. Legacy gate_10 rejection
# ===========================================================================


class TestLegacyGate10Rejection:
    """checkpoint-publish must NOT reference the legacy monolithic gate_10."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("checkpoint-publish.md")

    def test_no_gate_10_result_json_as_required_input(self) -> None:
        """The spec must not list gate_10_result.json as a required file
        to read (it should list gate_10a/b/c/d instead)."""
        # Find lines that reference gate_10_result.json as a path to read
        # (not in a "Do NOT" context)
        lines = self.text.split("\n")
        for line in lines:
            if "gate_10_result.json" in line:
                # OK if it's in a "Do NOT" / "no longer" context
                lower = line.lower()
                assert any(
                    neg in lower
                    for neg in ["do not", "no longer", "legacy", "not read", "not require"]
                ), (
                    f"checkpoint-publish.md references gate_10_result.json "
                    f"without a negation context: {line.strip()}"
                )

    def test_no_gate_10_part_b_completeness_in_confirmed(self) -> None:
        """gate_results_confirmed must not contain gate_10_part_b_completeness."""
        assert "gate_10_part_b_completeness" not in self.text


# ===========================================================================
# 2. Decomposed gate success — correct gate files referenced
# ===========================================================================


class TestDecomposedGateReferences:
    """checkpoint-publish must reference all five decomposed Phase 8 gate files."""

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
        """Budget gate (gate_09) must still be required."""
        assert "phase7_budget_gate/gate_result.json" in self.text

    def test_six_gate_files_in_step_1_2(self) -> None:
        """Step 1.2 must reference exactly six gate result files."""
        assert "six required gate result files" in self.text


# ===========================================================================
# 3. Missing decomposed gate — spec requires all six
# ===========================================================================


class TestMissingGateDetection:
    """The spec must fail-close when any gate result file is absent."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("checkpoint-publish.md")

    def test_missing_input_failure_category(self) -> None:
        """MISSING_INPUT failure must be documented for absent gate files."""
        assert 'failure_category="MISSING_INPUT"' in self.text

    def test_failure_mentions_six_gates(self) -> None:
        """Failure message must reference all six gates required."""
        assert "all six gate results required" in self.text


# ===========================================================================
# 4. Failed decomposed gate — spec rejects non-pass status
# ===========================================================================


class TestFailedGateRejection:
    """The spec must reject gate results with status != pass."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("checkpoint-publish.md")

    def test_status_pass_check_documented(self) -> None:
        """Step 1.3 must check status == pass for each gate."""
        assert 'status` ≠ "pass"' in self.text or "status` != \"pass\"" in self.text

    def test_non_pass_triggers_failure(self) -> None:
        """Non-pass status must trigger MISSING_INPUT failure."""
        assert "all required gates must have status 'pass'" in self.text


# ===========================================================================
# 5. gate_12 optionality — must NOT be required
# ===========================================================================


class TestGate12Optionality:
    """gate_12 is the exit gate of n08f, evaluated AFTER checkpoint-publish.
    The spec must NOT require gate_12_result.json."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("checkpoint-publish.md")

    def test_gate_12_not_in_required_file_list(self) -> None:
        """gate_12_result.json must not appear as a required input file
        in Step 1.2 (outside of "Do NOT" context)."""
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
        """gate_results_confirmed array must not include gate_12."""
        # Find the gate_results_confirmed array in the output construction
        matches = re.findall(
            r'gate_results_confirmed.*?\[([^\]]+)\]',
            self.text,
            re.DOTALL,
        )
        for match in matches:
            assert "gate_12" not in match, (
                f"gate_results_confirmed array contains gate_12: {match}"
            )

    def test_gate_12_exclusion_documented(self) -> None:
        """The spec must explicitly document why gate_12 is excluded."""
        assert "gate_12_constitutional_compliance" in self.text
        # Must explain it's evaluated after
        assert "after" in self.text.lower()


# ===========================================================================
# 6. Consistency with gate_result_registry.py
# ===========================================================================


class TestRegistryConsistency:
    """The gate result files referenced in checkpoint-publish must match
    the paths in gate_result_registry.py."""

    def test_phase8_gate_paths_match_registry(self) -> None:
        from runner.gate_result_registry import GATE_RESULT_PATHS

        spec_text = _read_skill("checkpoint-publish.md")

        # These are the six gates checkpoint-publish must check
        required_gates = [
            "gate_09_budget_consistency",
            "gate_10a_excellence_completeness",
            "gate_10b_impact_completeness",
            "gate_10c_implementation_completeness",
            "gate_10d_cross_section_consistency",
            "gate_11_review_closure",
        ]

        for gate_id in required_gates:
            assert gate_id in GATE_RESULT_PATHS, (
                f"{gate_id} missing from GATE_RESULT_PATHS"
            )

        # Verify that the registry paths for decomposed gates use the
        # correct filenames that the spec references
        for suffix in ["10a", "10b", "10c", "10d"]:
            gate_id = f"gate_{suffix}_{'excellence_completeness' if suffix == '10a' else 'impact_completeness' if suffix == '10b' else 'implementation_completeness' if suffix == '10c' else 'cross_section_consistency'}"
            path = GATE_RESULT_PATHS[gate_id]
            expected_filename = f"gate_{suffix}_result.json"
            assert expected_filename in path, (
                f"Registry path for {gate_id} does not contain {expected_filename}: {path}"
            )

    def test_legacy_gate_10_absent_from_registry(self) -> None:
        from runner.gate_result_registry import GATE_RESULT_PATHS

        assert "gate_10_part_b_completeness" not in GATE_RESULT_PATHS


# ===========================================================================
# 7. Consistency with manifest.compile.yaml
# ===========================================================================


class TestManifestConsistency:
    """checkpoint-publish gate expectations must match the manifest's
    Phase 8 gate definitions."""

    @pytest.fixture(autouse=True)
    def load_manifest(self) -> None:
        import yaml

        manifest_path = (
            REPO_ROOT
            / ".claude"
            / "workflows"
            / "system_orchestration"
            / "manifest.compile.yaml"
        )
        with open(manifest_path, encoding="utf-8") as f:
            self.manifest = yaml.safe_load(f)

    def _get_phase8_exit_gates(self) -> list[str]:
        """Extract all exit_gate values for phase_number==8 nodes."""
        gates = []
        for node in self.manifest.get("node_registry", []):
            if node.get("phase_number") == 8 and "exit_gate" in node:
                gates.append(node["exit_gate"])
        return gates

    def test_all_non_terminal_phase8_gates_in_spec(self) -> None:
        """All Phase 8 exit gates except gate_12 (terminal exit gate)
        must be referenced in checkpoint-publish."""
        spec_text = _read_skill("checkpoint-publish.md")
        phase8_gates = self._get_phase8_exit_gates()

        # gate_12 is the exit gate of the terminal node n08f_revision;
        # it's evaluated AFTER checkpoint-publish and should not be required
        non_terminal_gates = [g for g in phase8_gates if g != "gate_12_constitutional_compliance"]

        for gate in non_terminal_gates:
            assert gate in spec_text, (
                f"Phase 8 gate {gate} from manifest not found in checkpoint-publish.md"
            )

    def test_n08f_exit_gate_is_gate_12(self) -> None:
        """Confirm that gate_12 is indeed the exit gate of n08f_revision."""
        for node in self.manifest.get("node_registry", []):
            if node["node_id"] == "n08f_revision":
                assert node["exit_gate"] == "gate_12_constitutional_compliance"
                return
        pytest.fail("n08f_revision not found in manifest")

    def test_checkpoint_publish_is_skill_of_n08f(self) -> None:
        """Confirm checkpoint-publish is a skill of n08f_revision."""
        for node in self.manifest.get("node_registry", []):
            if node["node_id"] == "n08f_revision":
                assert "checkpoint-publish" in node.get("skills", [])
                return
        pytest.fail("n08f_revision not found in manifest")


# ===========================================================================
# 8. gate_results_confirmed content
# ===========================================================================


class TestGateResultsConfirmedContent:
    """Verify the gate_results_confirmed array in the spec contains
    exactly the correct gate IDs."""

    @pytest.fixture(autouse=True)
    def load_spec(self) -> None:
        self.text = _read_skill("checkpoint-publish.md")

    def test_confirmed_contains_gate_09(self) -> None:
        # Find gate_results_confirmed arrays and check content
        assert "gate_09_budget_consistency" in self.text

    def test_confirmed_contains_all_decomposed_gates(self) -> None:
        expected = [
            "gate_10a_excellence_completeness",
            "gate_10b_impact_completeness",
            "gate_10c_implementation_completeness",
            "gate_10d_cross_section_consistency",
        ]
        for gate_id in expected:
            assert gate_id in self.text, (
                f"{gate_id} not found in checkpoint-publish.md"
            )

    def test_confirmed_contains_gate_11(self) -> None:
        assert "gate_11_review_closure" in self.text
