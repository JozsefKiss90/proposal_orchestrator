"""
Tests for runner.manifest_reader.ManifestReader (Approach B).

Covers:
  - load from explicit path: valid manifest with predicate_refs
  - load from repo_root auto-discovery
  - load with missing file: raises ManifestReaderError
  - load with invalid YAML: raises ManifestReaderError
  - load with missing gate_registry key: raises ManifestReaderError
  - load with non-list gate_registry: raises ManifestReaderError
  - get_predicate_refs: returns correct ordered list for a gate with refs
  - get_predicate_refs: returns None for gate with plain-string conditions
  - get_predicate_refs: returns None for gate not in manifest
  - get_predicate_refs: returns None for gate with no conditions field
  - get_predicate_refs: skips plain-string conditions, collects object conditions
  - has_predicate_refs: True / False variants
  - gate_ids: returns gate IDs in insertion order
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from runner.manifest_reader import (
    MANIFEST_REL_PATH,
    ManifestGateNotFoundError,
    ManifestReader,
    ManifestReaderError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_manifest(tmp_path: Path, content: str) -> Path:
    """Write a manifest YAML to the canonical manifest path under tmp_path."""
    manifest_path = tmp_path / MANIFEST_REL_PATH
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(textwrap.dedent(content), encoding="utf-8")
    return manifest_path


def _minimal_manifest(extra_gates: str = "") -> str:
    return textwrap.dedent(f"""\
        name: system_orchestration
        version: "1.1"
        gate_registry:
          - gate_id: gate_01_source_integrity
            name: "Source Integrity"
            evaluated_at: n01 entry
            conditions:
              - prose: "selected_call.json must be present and non-empty"
                predicate_refs: [g01_p01, g01_p02]
              - prose: "At least one work programme document must be present"
                predicate_refs: [g01_p03]
          - gate_id: phase_01_gate
            name: "Phase 1 Gate"
            evaluated_at: n01 exit
            conditions:
              - prose: "All six Tier 2B extracted JSON files are non-empty"
                predicate_refs: [g02_p01, g02_p02, g02_p03]
              - prose: "Instrument type resolved"
                predicate_refs: [g02_p13]
        {extra_gates}
    """)


# ---------------------------------------------------------------------------
# Load tests
# ---------------------------------------------------------------------------


class TestManifestReaderLoad:
    def test_load_from_explicit_path(self, tmp_path):
        path = _write_manifest(tmp_path, _minimal_manifest())
        rdr = ManifestReader.load(path)
        assert isinstance(rdr, ManifestReader)

    def test_load_from_repo_root(self, tmp_path):
        _write_manifest(tmp_path, _minimal_manifest())
        rdr = ManifestReader.load(repo_root=tmp_path)
        assert isinstance(rdr, ManifestReader)

    def test_load_missing_file_raises(self, tmp_path):
        missing = tmp_path / "nonexistent.yaml"
        with pytest.raises(ManifestReaderError, match="not found"):
            ManifestReader.load(missing)

    def test_load_invalid_yaml_raises(self, tmp_path):
        bad = tmp_path / "manifest.yaml"
        bad.write_text(": invalid: yaml: [\n", encoding="utf-8")
        with pytest.raises(ManifestReaderError, match="[Ii]nvalid YAML"):
            ManifestReader.load(bad)

    def test_load_non_mapping_root_raises(self, tmp_path):
        bad = tmp_path / "manifest.yaml"
        bad.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ManifestReaderError, match="mapping"):
            ManifestReader.load(bad)

    def test_load_missing_gate_registry_raises(self, tmp_path):
        content = "name: system_orchestration\nversion: '1.1'\n"
        path = tmp_path / "manifest.yaml"
        path.write_text(content, encoding="utf-8")
        with pytest.raises(ManifestReaderError, match="gate_registry"):
            ManifestReader.load(path)

    def test_load_non_list_gate_registry_raises(self, tmp_path):
        content = "name: system_orchestration\ngate_registry: not_a_list\n"
        path = tmp_path / "manifest.yaml"
        path.write_text(content, encoding="utf-8")
        with pytest.raises(ManifestReaderError, match="sequence"):
            ManifestReader.load(path)


# ---------------------------------------------------------------------------
# get_predicate_refs tests
# ---------------------------------------------------------------------------


class TestGetPredicateRefs:
    def _load(self, tmp_path, content=None) -> ManifestReader:
        path = _write_manifest(tmp_path, content or _minimal_manifest())
        return ManifestReader.load(path)

    def test_returns_ordered_pred_ids_for_gate_with_refs(self, tmp_path):
        rdr = self._load(tmp_path)
        refs = rdr.get_predicate_refs("gate_01_source_integrity")
        assert refs == ["g01_p01", "g01_p02", "g01_p03"]

    def test_flattens_multiple_conditions(self, tmp_path):
        rdr = self._load(tmp_path)
        refs = rdr.get_predicate_refs("phase_01_gate")
        assert refs == ["g02_p01", "g02_p02", "g02_p03", "g02_p13"]

    def test_returns_none_for_unknown_gate(self, tmp_path):
        rdr = self._load(tmp_path)
        assert rdr.get_predicate_refs("nonexistent_gate") is None

    def test_returns_none_for_gate_with_no_conditions(self, tmp_path):
        content = textwrap.dedent("""\
            name: test
            gate_registry:
              - gate_id: gate_no_conditions
                name: "No Conditions"
        """)
        path = tmp_path / "manifest.yaml"
        path.write_text(content, encoding="utf-8")
        rdr = ManifestReader.load(path)
        assert rdr.get_predicate_refs("gate_no_conditions") is None

    def test_returns_none_for_gate_with_plain_string_conditions(self, tmp_path):
        content = textwrap.dedent("""\
            name: test
            gate_registry:
              - gate_id: gate_prose_only
                name: "Prose Only"
                conditions:
                  - "All six Tier 2B files are non-empty"
                  - "Instrument type resolved"
        """)
        path = tmp_path / "manifest.yaml"
        path.write_text(content, encoding="utf-8")
        rdr = ManifestReader.load(path)
        assert rdr.get_predicate_refs("gate_prose_only") is None

    def test_skips_plain_strings_collects_objects(self, tmp_path):
        content = textwrap.dedent("""\
            name: test
            gate_registry:
              - gate_id: gate_mixed
                name: "Mixed"
                conditions:
                  - "plain prose string — skipped"
                  - prose: "object condition"
                    predicate_refs: [g01_p01, g01_p02]
        """)
        path = tmp_path / "manifest.yaml"
        path.write_text(content, encoding="utf-8")
        rdr = ManifestReader.load(path)
        refs = rdr.get_predicate_refs("gate_mixed")
        assert refs == ["g01_p01", "g01_p02"]

    def test_returns_none_for_gate_with_empty_predicate_refs(self, tmp_path):
        content = textwrap.dedent("""\
            name: test
            gate_registry:
              - gate_id: gate_empty_refs
                name: "Empty Refs"
                conditions:
                  - prose: "a condition with no refs"
                    predicate_refs: []
        """)
        path = tmp_path / "manifest.yaml"
        path.write_text(content, encoding="utf-8")
        rdr = ManifestReader.load(path)
        assert rdr.get_predicate_refs("gate_empty_refs") is None


# ---------------------------------------------------------------------------
# has_predicate_refs and gate_ids tests
# ---------------------------------------------------------------------------


class TestIntrospection:
    def test_has_predicate_refs_true(self, tmp_path):
        path = _write_manifest(tmp_path, _minimal_manifest())
        rdr = ManifestReader.load(path)
        assert rdr.has_predicate_refs("gate_01_source_integrity") is True

    def test_has_predicate_refs_false_for_unknown(self, tmp_path):
        path = _write_manifest(tmp_path, _minimal_manifest())
        rdr = ManifestReader.load(path)
        assert rdr.has_predicate_refs("no_such_gate") is False

    def test_gate_ids_insertion_order(self, tmp_path):
        path = _write_manifest(tmp_path, _minimal_manifest())
        rdr = ManifestReader.load(path)
        assert rdr.gate_ids() == ["gate_01_source_integrity", "phase_01_gate"]


# ---------------------------------------------------------------------------
# Approach B integration: evaluate_gate uses manifest when present
# ---------------------------------------------------------------------------


class TestApproachBIntegration:
    """
    Confirm that evaluate_gate() uses manifest predicate_refs (Approach B)
    when a manifest with predicate_refs is present, and produces an identical
    GateResult to Approach A (library-only path).
    """

    def test_evaluate_gate_uses_manifest_predicate_refs(self, tmp_path):
        """
        Build a minimal synthetic repo with both a synthetic library and a
        manifest that carries predicate_refs.  Evaluate gate_01 via Approach B
        and confirm all six predicate IDs appear in the passed list.
        """
        from tests.runner.fixtures.repo_builders import (
            make_repo_root,
            make_run_id,
            init_run,
            write_library,
            pred,
            gate_entry,
        )
        from tests.runner.fixtures.artifact_writers import (
            write_selected_call,
            write_source_dirs,
        )
        from runner.gate_evaluator import evaluate_gate

        repo = make_repo_root(tmp_path)
        run_id = make_run_id()
        init_run(repo, run_id)

        # Populate the artifacts that gate_01_source_integrity checks
        write_selected_call(repo)
        write_source_dirs(repo)

        # Build a synthetic library that has all six gate_01 predicate defs
        call_path = "docs/tier3_project_instantiation/call_binding/selected_call.json"
        predicates_01 = [
            pred("g01_p01", "file", "non_empty_json", path=call_path),
            pred("g01_p02", "schema", "json_fields_present",
                 path=call_path,
                 fields=["call_id", "topic_code", "instrument_type", "work_programme_area"]),
            pred("g01_p03", "file", "dir_non_empty",
                 path="docs/tier2b_topic_and_call_sources/work_programmes/"),
            pred("g01_p04", "file", "dir_non_empty",
                 path="docs/tier2b_topic_and_call_sources/call_extracts/"),
            pred("g01_p05", "file", "dir_non_empty",
                 path="docs/tier2a_instrument_schemas/application_forms/"),
            pred("g01_p06", "file", "dir_non_empty",
                 path="docs/tier2a_instrument_schemas/evaluation_forms/"),
        ]
        lib_gate = gate_entry(
            "gate_01_source_integrity",
            "entry",
            "n01",
            predicates_01,
        )
        lib_path = write_library(repo, [lib_gate])

        # Write a manifest with predicate_refs pointing at those predicate IDs
        manifest_dir = repo / ".claude" / "workflows" / "system_orchestration"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_content = textwrap.dedent("""\
            name: system_orchestration
            version: "1.1"
            gate_registry:
              - gate_id: gate_01_source_integrity
                name: "Source Integrity"
                evaluated_at: n01 entry
                conditions:
                  - prose: "selected_call.json must be present and non-empty"
                    predicate_refs: [g01_p01, g01_p02]
                  - prose: "At least one work programme document must be present"
                    predicate_refs: [g01_p03]
                  - prose: "At least one call extract matching the topic code must be present"
                    predicate_refs: [g01_p04]
                  - prose: "An application form template must be present"
                    predicate_refs: [g01_p05]
                  - prose: "An evaluation form must be present"
                    predicate_refs: [g01_p06]
        """)
        manifest_path = manifest_dir / "manifest.compile.yaml"
        manifest_path.write_text(manifest_content, encoding="utf-8")

        result = evaluate_gate(
            "gate_01_source_integrity",
            run_id,
            repo,
            library_path=lib_path,
            manifest_path=manifest_path,
        )

        assert result["gate_id"] == "gate_01_source_integrity"
        assert result["status"] == "pass"
        passed = result["deterministic_predicates"]["passed"]
        for pid in ["g01_p01", "g01_p02", "g01_p03", "g01_p04", "g01_p05", "g01_p06"]:
            assert pid in passed, f"{pid} not in passed: {passed}"

    def test_evaluate_gate_falls_back_to_library_without_manifest(self, tmp_path):
        """
        When no manifest exists in the repo root, evaluate_gate() falls back
        to Approach A (library gate entry predicates).  The result should still
        pass with the same predicate IDs.
        """
        from tests.runner.fixtures.repo_builders import (
            make_repo_root,
            make_run_id,
            init_run,
            write_library,
            pred,
            gate_entry,
        )
        from tests.runner.fixtures.artifact_writers import (
            write_selected_call,
            write_source_dirs,
        )
        from runner.gate_evaluator import evaluate_gate

        repo = make_repo_root(tmp_path)
        run_id = make_run_id()
        init_run(repo, run_id)
        write_selected_call(repo)
        write_source_dirs(repo)

        call_path = "docs/tier3_project_instantiation/call_binding/selected_call.json"
        predicates_01 = [
            pred("g01_p01", "file", "non_empty_json", path=call_path),
            pred("g01_p02", "schema", "json_fields_present",
                 path=call_path,
                 fields=["call_id", "topic_code", "instrument_type", "work_programme_area"]),
            pred("g01_p03", "file", "dir_non_empty",
                 path="docs/tier2b_topic_and_call_sources/work_programmes/"),
            pred("g01_p04", "file", "dir_non_empty",
                 path="docs/tier2b_topic_and_call_sources/call_extracts/"),
            pred("g01_p05", "file", "dir_non_empty",
                 path="docs/tier2a_instrument_schemas/application_forms/"),
            pred("g01_p06", "file", "dir_non_empty",
                 path="docs/tier2a_instrument_schemas/evaluation_forms/"),
        ]
        lib_gate = gate_entry(
            "gate_01_source_integrity",
            "entry",
            "n01",
            predicates_01,
        )
        lib_path = write_library(repo, [lib_gate])

        # No manifest written — evaluate_gate must fall back to Approach A
        result = evaluate_gate(
            "gate_01_source_integrity",
            run_id,
            repo,
            library_path=lib_path,
        )

        assert result["gate_id"] == "gate_01_source_integrity"
        assert result["status"] == "pass"
        passed = result["deterministic_predicates"]["passed"]
        for pid in ["g01_p01", "g01_p02", "g01_p03", "g01_p04", "g01_p05", "g01_p06"]:
            assert pid in passed, f"{pid} not in passed: {passed}"
