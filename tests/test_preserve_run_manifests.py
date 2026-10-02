"""``tools/preserve_run_manifests.py``: the Tier 4 copy of a run manifest.

The copy is what the shadow comparison reads when a run's id is not a plain
identifier, so three things about it are pinned here. It is named by the one
slug rule ``runner.run_context`` owns. It keeps the distinction between a
manifest that records no ``reuse_decisions`` key and one that records an
empty map, because the comparison reads that distinction. And the note it
writes about the decisions describes the run it is copying, not the Phase 1
to 6 run the tool was first written for.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.phase8_reuse import REUSE_ELIGIBLE_NODES
from runner.run_context import (
    PRESERVED_RUN_RECORD_SCHEMA_ID,
    PRESERVED_RUN_RECORDS_REL,
    RUNS_DIR_REL,
    run_id_slug,
)
from tools.preserve_run_manifests import QUALIFYING_NODES, collect, main

MISPASTED = "import uuid; print(uuid.uuid4())"
PHASE8_NODES = tuple(sorted(REUSE_ELIGIBLE_NODES))


def _seed_run(root: Path, run_id: str, *, nodes: tuple[str, ...], manifest_extra: dict | None = None) -> None:
    directory = root / RUNS_DIR_REL / run_id
    directory.mkdir(parents=True)
    manifest = {
        "run_id": run_id,
        "manifest_version": "1.1",
        "created_at": "2026-09-30T22:23:10+00:00",
        "node_states": {n: "released" for n in nodes},
        "node_failure_details": {},
    }
    manifest.update(manifest_extra or {})
    (directory / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


@pytest.fixture
def world(tmp_path: Path) -> Path:
    return tmp_path


class TestNaming:
    def test_the_file_is_named_by_the_shared_slug(self, world: Path) -> None:
        _seed_run(world, MISPASTED, nodes=QUALIFYING_NODES + PHASE8_NODES)

        assert main(["--repo-root", str(world)]) == 0
        target = world / PRESERVED_RUN_RECORDS_REL / f"{run_id_slug(MISPASTED)}.json"
        assert target.is_file()
        doc = json.loads(target.read_text(encoding="utf-8"))
        assert doc["schema_id"] == PRESERVED_RUN_RECORD_SCHEMA_ID
        assert doc["run_id"] == MISPASTED
        assert doc["run_id_is_a_uuid"] is False
        assert doc["run_id_is_a_plain_identifier"] is False

    def test_a_plain_run_id_is_marked_as_one(self, world: Path) -> None:
        _seed_run(world, "d68acaef-e9b2-412e-bc09-4b34c386d5fd", nodes=QUALIFYING_NODES)

        [record] = collect(world)
        assert record["run_id_is_a_uuid"] is True
        assert record["run_id_is_a_plain_identifier"] is True


class TestReuseDecisions:
    def test_an_absent_key_is_preserved_as_null_not_coerced_to_empty(self, world: Path) -> None:
        _seed_run(world, "run-a", nodes=QUALIFYING_NODES + PHASE8_NODES)

        [record] = collect(world)
        assert record["reuse_decisions"] is None

    def test_a_recorded_map_is_copied_as_is(self, world: Path) -> None:
        decisions = {PHASE8_NODES[0]: {"status": "reused", "artifact_path": "x"}}
        _seed_run(world, "run-b", nodes=QUALIFYING_NODES + PHASE8_NODES, manifest_extra={"reuse_decisions": decisions})

        [record] = collect(world)
        assert record["reuse_decisions"] == decisions

    def test_the_note_for_a_phases_1_to_6_run_says_no_node_could_decide(self, world: Path) -> None:
        _seed_run(world, "run-c", nodes=QUALIFYING_NODES)

        [record] = collect(world)
        note = record["reuse_decisions_note"]
        assert "no node dispatched here can produce a reuse decision" in note

    def test_the_note_for_a_run_that_dispatched_phase_8_names_the_eligible_nodes_and_why_nothing_persisted(
        self, world: Path
    ) -> None:
        _seed_run(world, "run-d", nodes=QUALIFYING_NODES + PHASE8_NODES)

        [record] = collect(world)
        note = record["reuse_decisions_note"]
        for node in PHASE8_NODES:
            assert node in note
        assert "not_reused" in note and "run_summary.json" in note
        assert "Phases 1 to 6" not in note

    def test_the_caveat_counts_every_node_the_manifest_holds(self, world: Path) -> None:
        _seed_run(world, "run-e", nodes=QUALIFYING_NODES + PHASE8_NODES)

        [record] = collect(world)
        assert f"dispatched {len(QUALIFYING_NODES) + len(PHASE8_NODES)} nodes" in record["run_summary_caveat"]


class TestTheLiveRecords:
    """The two records this world preserves are current, not stale copies."""

    REPO_ROOT = Path(__file__).resolve().parents[1]

    def test_check_mode_reports_the_preserved_records_unchanged(self) -> None:
        if not (self.REPO_ROOT / RUNS_DIR_REL).is_dir():
            pytest.skip("runtime run state is gitignored under §9.2")
        assert main(["--repo-root", str(self.REPO_ROOT), "--check"]) == 0
