"""
Tests for the ``final_export_writer`` deterministic component.

The component (``runner/final_export_writer.py``) closes the gap found in run
5952b165: ``final_export.json`` was schema-bound and gate-checked (gate_12
``g11_p05``/``g11_p05b``) but had no producer, so ``n08f_revision`` could never
satisfy its §17.6.6 disk check.

Coverage:
  * happy path — bundle + manifest written; manifest schema-conformant
    (schema_id, run_id, export_format, export_path, section_index sorted by
    the assembled draft's explicit ``order``, exported_at); no artifact_status.
  * bundle is self-contained: assembled draft + section artifacts verbatim.
  * determinism — byte-equal replay of the bundle; manifest byte-equal modulo
    ``exported_at``.
  * overwrite semantics — a second run rewrites (no write-once guard;
    g11_p05b requires current-run ownership).
  * fail-closed — missing/malformed/empty/wrong-schema assembled draft,
    foreign-run assembled draft, empty/duplicate/malformed section list,
    missing or invalid referenced section artifact.  Nothing is written on
    any failure path.
  * registry — component registered, not draft-consuming, adapter returns
    both written paths through ``invoke_component``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.final_export_writer import (
    ASSEMBLED_DRAFT_REL,
    ASSEMBLED_DRAFT_SCHEMA_ID,
    FINAL_EXPORT_REL,
    FINAL_EXPORT_SCHEMA_ID,
    JSON_BUNDLE_REL,
    FinalExportError,
    write_final_export,
)

_RUN = "current-run-id"

_SECTION_FILES = {
    "excellence": "docs/tier5_deliverables/proposal_sections/excellence_section.json",
    "impact": "docs/tier5_deliverables/proposal_sections/impact_section.json",
    "implementation": (
        "docs/tier5_deliverables/proposal_sections/implementation_section.json"
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(repo_root: Path, rel: str, obj) -> Path:
    path = repo_root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    return path


def _seed_sections(repo_root: Path) -> None:
    for section_id, rel in _SECTION_FILES.items():
        _write_json(
            repo_root,
            rel,
            {
                "schema_id": "orch.tier5.proposal_section.v1",
                "section_id": section_id,
                "content": f"{section_id} prose",
            },
        )


def _assembled_draft(run_id: str = _RUN) -> dict:
    # Sections deliberately listed OUT of rendering order to prove the writer
    # sorts by the explicit ``order`` field rather than list position.
    return {
        "schema_id": ASSEMBLED_DRAFT_SCHEMA_ID,
        "run_id": run_id,
        "sections": [
            {
                "section_id": "implementation",
                "criterion": "Quality and efficiency of the implementation",
                "order": 3,
                "artifact_path": _SECTION_FILES["implementation"],
                "word_count": 7273,
            },
            {
                "section_id": "excellence",
                "criterion": "Excellence",
                "order": 1,
                "artifact_path": _SECTION_FILES["excellence"],
                "word_count": 16248,
            },
            {
                "section_id": "impact",
                "criterion": "Impact",
                "order": 2,
                "artifact_path": _SECTION_FILES["impact"],
                "word_count": 11058,
            },
        ],
        "consistency_log": [],
    }


def _seed_all(repo_root: Path, run_id: str = _RUN) -> dict:
    draft = _assembled_draft(run_id)
    _write_json(repo_root, ASSEMBLED_DRAFT_REL, draft)
    _seed_sections(repo_root)
    return draft


def _read(repo_root: Path, rel: str) -> dict:
    return json.loads((repo_root / rel).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1. Happy path
# ---------------------------------------------------------------------------


class TestHappyPath:
    def test_writes_bundle_and_manifest(self, tmp_path: Path):
        _seed_all(tmp_path)

        written = write_final_export(_RUN, tmp_path)

        assert written == [
            tmp_path / JSON_BUNDLE_REL,
            tmp_path / FINAL_EXPORT_REL,
        ]
        assert (tmp_path / JSON_BUNDLE_REL).is_file()
        assert (tmp_path / FINAL_EXPORT_REL).is_file()

    def test_manifest_is_schema_conformant(self, tmp_path: Path):
        _seed_all(tmp_path)
        write_final_export(_RUN, tmp_path)

        manifest = _read(tmp_path, FINAL_EXPORT_REL)
        assert manifest["schema_id"] == FINAL_EXPORT_SCHEMA_ID
        assert manifest["run_id"] == _RUN
        assert manifest["export_format"] == "json_bundle"
        assert manifest["export_path"] == JSON_BUNDLE_REL
        assert isinstance(manifest["exported_at"], str)
        # artifact_status is optional and must be ABSENT at write time
        # (mirrors the skill-response rule; validity is the gate's judgment).
        assert "artifact_status" not in manifest

    def test_section_index_sorted_by_order_with_criterion_as_name(
        self, tmp_path: Path
    ):
        _seed_all(tmp_path)
        write_final_export(_RUN, tmp_path)

        index = _read(tmp_path, FINAL_EXPORT_REL)["section_index"]
        assert [e["section_id"] for e in index] == [
            "excellence", "impact", "implementation",
        ]
        assert index[0]["section_name"] == "Excellence"
        assert index[2]["section_name"] == (
            "Quality and efficiency of the implementation"
        )
        for entry in index:
            assert entry["artifact_path"] == _SECTION_FILES[entry["section_id"]]

    def test_bundle_is_self_contained_and_verbatim(self, tmp_path: Path):
        draft = _seed_all(tmp_path)
        write_final_export(_RUN, tmp_path)

        bundle = _read(tmp_path, JSON_BUNDLE_REL)
        assert bundle["bundle_format"] == "part_b_json_bundle"
        assert bundle["run_id"] == _RUN
        assert bundle["assembled_draft"] == draft
        assert set(bundle["sections_content"]) == set(_SECTION_FILES)
        for section_id, rel in _SECTION_FILES.items():
            assert bundle["sections_content"][section_id] == _read(tmp_path, rel)

    def test_manifest_satisfies_gate_disk_shape(self, tmp_path: Path):
        """The §17.6.6 disk check needs >=1 non-empty .json in final_exports/;
        g11_p05b needs manifest run_id == current run."""
        _seed_all(tmp_path)
        write_final_export(_RUN, tmp_path)

        export_dir = tmp_path / "docs/tier5_deliverables/final_exports"
        json_files = [p for p in export_dir.iterdir() if p.suffix == ".json"]
        assert len(json_files) == 2
        assert _read(tmp_path, FINAL_EXPORT_REL)["run_id"] == _RUN


# ---------------------------------------------------------------------------
# 2. Determinism and overwrite semantics
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_bundle_byte_equal_on_replay(self, tmp_path: Path):
        _seed_all(tmp_path)
        write_final_export(_RUN, tmp_path)
        first = (tmp_path / JSON_BUNDLE_REL).read_bytes()

        write_final_export(_RUN, tmp_path)
        assert (tmp_path / JSON_BUNDLE_REL).read_bytes() == first

    def test_manifest_byte_equal_modulo_exported_at(self, tmp_path: Path):
        _seed_all(tmp_path)
        write_final_export(_RUN, tmp_path)
        first = _read(tmp_path, FINAL_EXPORT_REL)

        write_final_export(_RUN, tmp_path)
        second = _read(tmp_path, FINAL_EXPORT_REL)

        first.pop("exported_at")
        second.pop("exported_at")
        assert first == second

    def test_second_run_overwrites_with_new_ownership(self, tmp_path: Path):
        """No write-once guard: g11_p05b requires the CURRENT run's run_id, so
        a later run's export replaces the earlier one."""
        _seed_all(tmp_path, run_id="run-A")
        write_final_export("run-A", tmp_path)
        assert _read(tmp_path, FINAL_EXPORT_REL)["run_id"] == "run-A"

        _write_json(tmp_path, ASSEMBLED_DRAFT_REL, _assembled_draft("run-B"))
        write_final_export("run-B", tmp_path)
        assert _read(tmp_path, FINAL_EXPORT_REL)["run_id"] == "run-B"
        assert _read(tmp_path, JSON_BUNDLE_REL)["run_id"] == "run-B"


# ---------------------------------------------------------------------------
# 3. Fail-closed paths
# ---------------------------------------------------------------------------


class TestFailClosed:
    def _assert_nothing_written(self, tmp_path: Path) -> None:
        assert not (tmp_path / JSON_BUNDLE_REL).exists()
        assert not (tmp_path / FINAL_EXPORT_REL).exists()

    def test_missing_assembled_draft(self, tmp_path: Path):
        _seed_sections(tmp_path)
        with pytest.raises(FinalExportError, match="not found"):
            write_final_export(_RUN, tmp_path)
        self._assert_nothing_written(tmp_path)

    def test_malformed_assembled_draft(self, tmp_path: Path):
        path = tmp_path / ASSEMBLED_DRAFT_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(FinalExportError, match="not valid JSON"):
            write_final_export(_RUN, tmp_path)
        self._assert_nothing_written(tmp_path)

    def test_empty_assembled_draft(self, tmp_path: Path):
        _write_json(tmp_path, ASSEMBLED_DRAFT_REL, {})
        with pytest.raises(FinalExportError, match="empty"):
            write_final_export(_RUN, tmp_path)
        self._assert_nothing_written(tmp_path)

    def test_wrong_schema_id(self, tmp_path: Path):
        draft = _assembled_draft()
        draft["schema_id"] = "orch.tier5.something_else.v1"
        _write_json(tmp_path, ASSEMBLED_DRAFT_REL, draft)
        _seed_sections(tmp_path)
        with pytest.raises(FinalExportError, match="unexpected schema_id"):
            write_final_export(_RUN, tmp_path)
        self._assert_nothing_written(tmp_path)

    def test_foreign_run_assembled_draft(self, tmp_path: Path):
        _seed_all(tmp_path, run_id="some-prior-run")
        with pytest.raises(FinalExportError, match="owned by run"):
            write_final_export(_RUN, tmp_path)
        self._assert_nothing_written(tmp_path)

    def test_empty_sections(self, tmp_path: Path):
        draft = _assembled_draft()
        draft["sections"] = []
        _write_json(tmp_path, ASSEMBLED_DRAFT_REL, draft)
        with pytest.raises(FinalExportError, match="no sections"):
            write_final_export(_RUN, tmp_path)
        self._assert_nothing_written(tmp_path)

    def test_section_entry_missing_fields(self, tmp_path: Path):
        draft = _assembled_draft()
        del draft["sections"][0]["artifact_path"]
        _write_json(tmp_path, ASSEMBLED_DRAFT_REL, draft)
        _seed_sections(tmp_path)
        with pytest.raises(FinalExportError, match="missing artifact_path"):
            write_final_export(_RUN, tmp_path)
        self._assert_nothing_written(tmp_path)

    def test_duplicate_section_id(self, tmp_path: Path):
        draft = _assembled_draft()
        dup = dict(draft["sections"][0])
        dup["order"] = 9
        draft["sections"].append(dup)
        _write_json(tmp_path, ASSEMBLED_DRAFT_REL, draft)
        _seed_sections(tmp_path)
        with pytest.raises(FinalExportError, match="Duplicate section_id"):
            write_final_export(_RUN, tmp_path)
        self._assert_nothing_written(tmp_path)

    def test_duplicate_order(self, tmp_path: Path):
        draft = _assembled_draft()
        draft["sections"][1]["order"] = draft["sections"][0]["order"]
        _write_json(tmp_path, ASSEMBLED_DRAFT_REL, draft)
        _seed_sections(tmp_path)
        with pytest.raises(FinalExportError, match="Duplicate section order"):
            write_final_export(_RUN, tmp_path)
        self._assert_nothing_written(tmp_path)

    def test_non_integer_order(self, tmp_path: Path):
        draft = _assembled_draft()
        draft["sections"][0]["order"] = "first"
        _write_json(tmp_path, ASSEMBLED_DRAFT_REL, draft)
        _seed_sections(tmp_path)
        with pytest.raises(FinalExportError, match="non-integer order"):
            write_final_export(_RUN, tmp_path)
        self._assert_nothing_written(tmp_path)

    def test_missing_section_artifact(self, tmp_path: Path):
        _seed_all(tmp_path)
        (tmp_path / _SECTION_FILES["impact"]).unlink()
        with pytest.raises(FinalExportError, match="'impact' not found"):
            write_final_export(_RUN, tmp_path)
        self._assert_nothing_written(tmp_path)

    def test_malformed_section_artifact(self, tmp_path: Path):
        _seed_all(tmp_path)
        (tmp_path / _SECTION_FILES["impact"]).write_text(
            "{broken", encoding="utf-8"
        )
        with pytest.raises(FinalExportError, match="not valid JSON"):
            write_final_export(_RUN, tmp_path)
        self._assert_nothing_written(tmp_path)


# ---------------------------------------------------------------------------
# 4. Registry and adapter integration (C2/C3 substrate)
# ---------------------------------------------------------------------------


class TestRegistryIntegration:
    def test_registered_in_component_registry(self):
        from runner.deterministic_components import COMPONENT_REGISTRY

        assert "final_export_writer" in COMPONENT_REGISTRY

    def test_not_draft_consuming(self):
        """The export writer reads the assembled draft, not section_drafts/ —
        it must survive Phase-8 reuse suppression."""
        from runner.deterministic_components import DRAFT_CONSUMING_COMPONENTS

        assert "final_export_writer" not in DRAFT_CONSUMING_COMPONENTS

    def test_invoke_component_success_records_both_outputs(self, tmp_path: Path):
        from runner.deterministic_components import invoke_component

        _seed_all(tmp_path)
        record = invoke_component("final_export_writer", _RUN, tmp_path)

        assert record.status == "success"
        assert record.component_id == "final_export_writer"
        written = [str(p) for p in record.outputs_written]
        assert any(s.endswith("part_b_json_bundle.json") for s in written)
        assert any(s.endswith("final_export.json") for s in written)

    def test_invoke_component_failure_is_recorded_not_raised(
        self, tmp_path: Path
    ):
        from runner.deterministic_components import invoke_component

        record = invoke_component("final_export_writer", _RUN, tmp_path)

        assert record.status == "failure"
        assert "not found" in (record.failure_reason or "")
        self_check = tmp_path / FINAL_EXPORT_REL
        assert not self_check.exists()
