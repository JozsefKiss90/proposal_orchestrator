"""
Unit tests for Step 10 — runner/gate_library.py.

All tests use synthetic temporary YAML files; no live repository artifacts are
read.  Every test builds a minimal valid library document and then mutates
specific fields to exercise each validation path.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from runner.gate_library import (
    GateLibrary,
    GateLibraryError,
    GateNotFoundError,
    ManifestVersionMismatchError,
)
from runner.versions import MANIFEST_VERSION


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_library_yaml(tmp_path: Path, content: dict) -> Path:
    """Serialise *content* to a YAML file in *tmp_path* and return its path."""
    lib_path = tmp_path / "gate_rules_library.yaml"
    lib_path.write_text(yaml.dump(content), encoding="utf-8")
    return lib_path


def _minimal_library(
    manifest_version: str = MANIFEST_VERSION,
    extra_gates: list | None = None,
) -> dict:
    """Return a minimal valid library document."""
    gates = [
        {
            "gate_id": "gate_test_alpha",
            "gate_kind": "entry",
            "evaluated_at": "n01 entry",
            "predicates": [],
        },
        {
            "gate_id": "gate_test_beta",
            "gate_kind": "exit",
            "evaluated_at": "n02 exit",
            "predicates": [],
        },
    ]
    if extra_gates:
        gates.extend(extra_gates)
    return {
        "library_version": "1.0",
        "manifest_version": manifest_version,
        "constitution_version": "abc1234",
        "gate_rules": gates,
    }


# ---------------------------------------------------------------------------
# Load — happy path
# ---------------------------------------------------------------------------


class TestGateLibraryLoad:
    def test_load_valid_library(self, tmp_path: Path) -> None:
        lib_path = _write_library_yaml(tmp_path, _minimal_library())
        lib = GateLibrary.load(lib_path)
        assert isinstance(lib, GateLibrary)

    def test_version_properties_match_yaml(self, tmp_path: Path) -> None:
        lib_path = _write_library_yaml(tmp_path, _minimal_library())
        lib = GateLibrary.load(lib_path)
        assert lib.library_version == "1.0"
        assert lib.manifest_version == MANIFEST_VERSION
        assert lib.constitution_version == "abc1234"

    def test_gate_ids_returns_all_in_order(self, tmp_path: Path) -> None:
        lib_path = _write_library_yaml(tmp_path, _minimal_library())
        lib = GateLibrary.load(lib_path)
        assert lib.gate_ids() == ["gate_test_alpha", "gate_test_beta"]

    # ------------------------------------------------------------------
    # via repo_root kwarg
    # ------------------------------------------------------------------

    def test_load_via_repo_root_kwarg(self, tmp_path: Path) -> None:
        """load() resolves library_path from repo_root when library_path is None."""
        from runner.gate_library import LIBRARY_REL_PATH

        lib_file = tmp_path / LIBRARY_REL_PATH
        lib_file.parent.mkdir(parents=True, exist_ok=True)
        lib_file.write_text(yaml.dump(_minimal_library()), encoding="utf-8")

        lib = GateLibrary.load(repo_root=tmp_path)
        assert isinstance(lib, GateLibrary)


# ---------------------------------------------------------------------------
# Load — validation failures
# ---------------------------------------------------------------------------


class TestGateLibraryLoadValidation:
    def test_missing_file_raises_GateLibraryError(self, tmp_path: Path) -> None:
        missing = tmp_path / "nonexistent.yaml"
        with pytest.raises(GateLibraryError, match="not found"):
            GateLibrary.load(missing)

    def test_invalid_yaml_raises_GateLibraryError(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text(":\n  - key: [broken", encoding="utf-8")
        with pytest.raises(GateLibraryError, match="Invalid YAML"):
            GateLibrary.load(bad)

    def test_root_not_mapping_raises_GateLibraryError(self, tmp_path: Path) -> None:
        lib_path = tmp_path / "bad.yaml"
        lib_path.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(GateLibraryError, match="mapping"):
            GateLibrary.load(lib_path)

    @pytest.mark.parametrize(
        "missing_key",
        ["library_version", "manifest_version", "constitution_version", "gate_rules"],
    )
    def test_missing_required_top_level_field_raises(
        self, tmp_path: Path, missing_key: str
    ) -> None:
        data = _minimal_library()
        del data[missing_key]
        lib_path = _write_library_yaml(tmp_path, data)
        with pytest.raises(GateLibraryError, match="missing required"):
            GateLibrary.load(lib_path)

    def test_manifest_version_mismatch_raises_ManifestVersionMismatchError(
        self, tmp_path: Path
    ) -> None:
        data = _minimal_library(manifest_version="0.0")
        lib_path = _write_library_yaml(tmp_path, data)
        with pytest.raises(ManifestVersionMismatchError, match="manifest_version"):
            GateLibrary.load(lib_path)

    def test_manifest_version_mismatch_is_subclass_of_GateLibraryError(
        self, tmp_path: Path
    ) -> None:
        data = _minimal_library(manifest_version="0.0")
        lib_path = _write_library_yaml(tmp_path, data)
        with pytest.raises(GateLibraryError):
            GateLibrary.load(lib_path)

    def test_gate_rules_not_list_raises(self, tmp_path: Path) -> None:
        data = _minimal_library()
        data["gate_rules"] = {"unexpected": "dict"}
        lib_path = _write_library_yaml(tmp_path, data)
        with pytest.raises(GateLibraryError, match="sequence"):
            GateLibrary.load(lib_path)

    def test_gate_entry_not_dict_raises(self, tmp_path: Path) -> None:
        data = _minimal_library()
        data["gate_rules"] = ["string_not_dict"]
        lib_path = _write_library_yaml(tmp_path, data)
        with pytest.raises(GateLibraryError, match="mapping"):
            GateLibrary.load(lib_path)

    def test_gate_missing_gate_id_raises(self, tmp_path: Path) -> None:
        data = _minimal_library()
        data["gate_rules"] = [{"gate_kind": "entry"}]
        lib_path = _write_library_yaml(tmp_path, data)
        with pytest.raises(GateLibraryError, match="gate_id"):
            GateLibrary.load(lib_path)

    def test_gate_missing_gate_kind_raises(self, tmp_path: Path) -> None:
        data = _minimal_library()
        data["gate_rules"] = [{"gate_id": "gate_x"}]
        lib_path = _write_library_yaml(tmp_path, data)
        with pytest.raises(GateLibraryError, match="gate_kind"):
            GateLibrary.load(lib_path)

    def test_expected_manifest_version_override(self, tmp_path: Path) -> None:
        """Caller can override the expected version for migration tests."""
        data = _minimal_library(manifest_version="9.9")
        lib_path = _write_library_yaml(tmp_path, data)
        lib = GateLibrary.load(lib_path, expected_manifest_version="9.9")
        assert lib.manifest_version == "9.9"


# ---------------------------------------------------------------------------
# get_gate
# ---------------------------------------------------------------------------


class TestGateLibraryGetGate:
    def test_get_gate_returns_correct_entry(self, tmp_path: Path) -> None:
        lib_path = _write_library_yaml(tmp_path, _minimal_library())
        lib = GateLibrary.load(lib_path)
        gate = lib.get_gate("gate_test_alpha")
        assert gate["gate_id"] == "gate_test_alpha"
        assert gate["gate_kind"] == "entry"

    def test_get_gate_not_found_raises_GateNotFoundError(
        self, tmp_path: Path
    ) -> None:
        lib_path = _write_library_yaml(tmp_path, _minimal_library())
        lib = GateLibrary.load(lib_path)
        with pytest.raises(GateNotFoundError, match="gate_x_not_there"):
            lib.get_gate("gate_x_not_there")

    def test_get_gate_not_found_is_subclass_of_GateLibraryError(
        self, tmp_path: Path
    ) -> None:
        lib_path = _write_library_yaml(tmp_path, _minimal_library())
        lib = GateLibrary.load(lib_path)
        with pytest.raises(GateLibraryError):
            lib.get_gate("nonexistent")

    def test_get_gate_error_message_lists_available_gates(
        self, tmp_path: Path
    ) -> None:
        lib_path = _write_library_yaml(tmp_path, _minimal_library())
        lib = GateLibrary.load(lib_path)
        with pytest.raises(GateNotFoundError, match="gate_test_alpha"):
            lib.get_gate("nonexistent")

    def test_gate_ids_empty_when_no_gates(self, tmp_path: Path) -> None:
        data = _minimal_library()
        data["gate_rules"] = []
        lib_path = _write_library_yaml(tmp_path, data)
        lib = GateLibrary.load(lib_path)
        assert lib.gate_ids() == []
