"""
Dev-graph snapshot builder — public-API tests on the synthetic fixture.

Every test copies ``tests/fixtures/dev_graph_synthetic`` into a temporary root
and calls the one public entry point, ``runner.dev_graph.build_snapshot``.
Rejection cases mutate the copy. Nothing here touches a real project, the
scheduler, or a gate.
"""

from __future__ import annotations

import json
import os
import shutil
import time as _time
from pathlib import Path

import pytest

from runner.deterministic_components import COMPONENT_REGISTRY, invoke_component
from runner.dev_graph import (
    NODE_TYPES,
    RELATIONSHIPS,
    SNAPSHOT_REL,
    DevGraphError,
    build_snapshot,
    validate_graph,
    write_snapshot,
)
from runner.paths import find_repo_root

FIXTURE = find_repo_root() / "tests" / "fixtures" / "dev_graph_synthetic"
T3 = Path("docs/tier3_project_instantiation")
WP_SEED = T3 / "architecture_inputs" / "workpackage_seed.json"
OBJECTIVES = T3 / "architecture_inputs" / "objectives.json"
PARTNERS = T3 / "consortium" / "partners.json"
MILESTONES = T3 / "architecture_inputs" / "milestones_seed.json"


@pytest.fixture
def world(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    return root


def _load(root: Path, rel: Path) -> dict:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def _dump(root: Path, rel: Path, obj: dict) -> None:
    (root / rel).write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _stamp_tree(root: Path, epoch: float) -> None:
    for p in root.rglob("*"):
        os.utime(p, (epoch, epoch))


def _triples(snap) -> set[tuple[str, str, str]]:
    return {(e["source"]["id"], e["predicate"], e["target"]["id"]) for e in snap.edges}


# --------------------------------------------------------------------------- #
# Closed vocabularies
# --------------------------------------------------------------------------- #


class TestClosedSets:
    def test_node_type_set_is_the_milestone_seventeen(self):
        assert NODE_TYPES == frozenset(
            {
                "participant", "objective", "work_package", "task", "deliverable",
                "milestone", "claim", "commitment", "passage", "source", "source_span",
                "artifact_version", "execution", "assessment", "finding",
                "change_request", "revision_contract",
            }
        )

    def test_relationship_set_is_closed_and_related_to_is_absent(self):
        assert set(RELATIONSHIPS) == {
            "assigned_to", "contributes_to", "produces", "supported_by", "expressed_in",
            "consumes", "addresses", "supersedes", "constrained_by", "validated_by",
        }
        assert "related_to" not in RELATIONSHIPS

    def test_every_relationship_declares_endpoints_direction_cardinality_effect(self):
        for predicate, spec in RELATIONSHIPS.items():
            assert spec.predicate == predicate
            assert spec.endpoints, predicate
            for src, dst in spec.endpoints:
                assert src in NODE_TYPES and dst in NODE_TYPES, predicate
            assert spec.direction == "source_to_target"
            assert spec.cardinality in {"one_to_one", "many_to_one", "many_to_many"}
            assert spec.effect in {"domain_link", "execution_dependency"}

    def test_assigned_to_is_a_domain_link_not_an_execution_dependency(self):
        assert RELATIONSHIPS["assigned_to"].effect == "domain_link"
        assert RELATIONSHIPS["consumes"].effect == "execution_dependency"


# --------------------------------------------------------------------------- #
# Building the fixture
# --------------------------------------------------------------------------- #


class TestFixtureBuild:
    def test_fixture_builds_the_expected_nodes(self, world: Path):
        snap = build_snapshot(world)
        by_type: dict[str, set[str]] = {}
        for n in snap.nodes:
            by_type.setdefault(n["type"], set()).add(n["id"])
        assert by_type["participant"] == {"P-A", "P-B", "P-C"}
        assert by_type["objective"] == {"OBJ-1", "OBJ-2"}
        assert by_type["work_package"] == {"WP1"}
        assert by_type["task"] == {"T01", "T02", "T03"}
        assert by_type["deliverable"] == {"D1.1"}
        assert by_type["milestone"] == {"MS1"}
        assert by_type["source"] == {"SRC-1", "SRC-2"}  # Tier 3 source materials
        assert "SYN-A" not in {n["id"] for n in snap.nodes}  # Tier 2A is not indexed
        assert not snap.empty

    def test_identity_is_separate_from_path_and_title(self, world: Path):
        snap = build_snapshot(world)
        t03 = next(n for n in snap.nodes if n["id"] == "T03")
        assert t03["title"] == "Task three"
        assert t03["path"] == WP_SEED.as_posix()
        assert t03["version"].startswith("sha256:")
        # Renaming the title changes the version, never the id.
        seed = _load(world, WP_SEED)
        seed["work_packages"][0]["tasks"][2]["title"] = "Task three, renamed"
        _dump(world, WP_SEED, seed)
        t03b = next(n for n in build_snapshot(world).nodes if n["id"] == "T03")
        assert t03b["id"] == "T03" and t03b["version"] != t03["version"]

    def test_edges_reference_id_plus_version(self, world: Path):
        snap = build_snapshot(world)
        versions = {n["id"]: n["version"] for n in snap.nodes}
        assigned = [
            e for e in snap.edges
            if e["predicate"] == "assigned_to" and e["source"]["id"] == "T03"
        ]
        assert len(assigned) == 1
        e = assigned[0]
        assert e["target"] == {"id": "P-B", "version": versions["P-B"]}
        assert e["source"] == {"id": "T03", "version": versions["T03"]}

    def test_derived_relationships_cover_the_t03_scenario(self, world: Path):
        triples = _triples(build_snapshot(world))
        assert ("T03", "assigned_to", "P-B") in triples
        assert ("P-C", "contributes_to", "T03") in triples
        assert ("T03", "consumes", "T02") in triples
        assert ("T03", "contributes_to", "WP1") in triples
        assert ("WP1", "contributes_to", "OBJ-1") in triples
        assert ("WP1", "produces", "D1.1") in triples
        assert ("T03", "produces", "D1.1") in triples
        assert ("D1.1", "validated_by", "MS1") in triples
        assert ("WP1", "assigned_to", "P-A") in triples

    def test_participant_title_is_the_legal_name(self, world: Path):
        pb = next(n for n in build_snapshot(world).nodes if n["id"] == "P-B")
        assert pb["title"] == "Participant B"

    def test_snapshot_lists_the_inputs_it_read(self, world: Path):
        snap = build_snapshot(world)
        assert WP_SEED.as_posix() in snap.inputs
        assert PARTNERS.as_posix() in snap.inputs


# --------------------------------------------------------------------------- #
# Determinism
# --------------------------------------------------------------------------- #


class TestDeterminism:
    def test_two_builds_with_opposite_wall_clocks_are_byte_identical(
        self, tmp_path: Path, monkeypatch
    ):
        a = tmp_path / "a"
        b = tmp_path / "b"
        shutil.copytree(FIXTURE, a)
        shutil.copytree(FIXTURE, b)
        _stamp_tree(a, 0.0)
        _stamp_tree(b, 4_102_444_800.0)  # 2100-01-01
        monkeypatch.setattr(_time, "time", lambda: 0.0)
        sa = build_snapshot(a)
        monkeypatch.setattr(_time, "time", lambda: 4_102_444_800.0)
        sb = build_snapshot(b)
        assert sa.to_json_bytes() == sb.to_json_bytes()
        assert sa.snapshot_id == sb.snapshot_id
        assert sa.snapshot_id.startswith("sha256:")

    def test_snapshot_carries_no_wall_clock_field(self, world: Path):
        text = build_snapshot(world).to_json_bytes().decode("utf-8")
        for key in ("compiled_at", "built_at", "generated_at", "timestamp"):
            assert key not in text

    def test_content_change_changes_snapshot_id(self, world: Path):
        before = build_snapshot(world).snapshot_id
        seed = _load(world, WP_SEED)
        seed["work_packages"][0]["tasks"][2]["responsible_partner"] = "P-C"
        _dump(world, WP_SEED, seed)
        assert build_snapshot(world).snapshot_id != before

    def test_key_order_in_source_does_not_change_snapshot_id(self, world: Path):
        before = build_snapshot(world).snapshot_id
        raw = _load(world, PARTNERS)
        reordered = {"partners": [dict(reversed(list(p.items()))) for p in raw["partners"]]}
        _dump(world, PARTNERS, reordered)
        assert build_snapshot(world).snapshot_id == before


# --------------------------------------------------------------------------- #
# Fail-closed rejection, naming the offender
# --------------------------------------------------------------------------- #


class TestRejection:
    def test_dangling_edge_names_the_edge(self, world: Path):
        seed = _load(world, WP_SEED)
        seed["work_packages"][0]["tasks"][2]["responsible_partner"] = "P-Z"
        _dump(world, WP_SEED, seed)
        with pytest.raises(DevGraphError) as ei:
            build_snapshot(world)
        assert ei.value.kind == "dangling_edge"
        assert "T03" in ei.value.offender and "P-Z" in ei.value.offender
        assert "assigned_to" in str(ei.value)

    def test_wrong_endpoint_type_names_the_edge(self, world: Path):
        seed = _load(world, WP_SEED)
        # A deliverable id where a task id belongs.
        seed["work_packages"][0]["tasks"][2]["dependencies"] = ["D1.1"]
        _dump(world, WP_SEED, seed)
        with pytest.raises(DevGraphError) as ei:
            build_snapshot(world)
        assert ei.value.kind == "endpoint_type"
        assert "T03" in ei.value.offender and "D1.1" in ei.value.offender
        assert "deliverable" in str(ei.value)

    @pytest.mark.parametrize("predicate", ["related_to", "depends_on", ""])
    def test_unknown_predicate_is_rejected(self, world: Path, predicate: str):
        # Tier 3 declares no predicates, so the closed-set check is exercised
        # on the pure validator the builder applies to every derived edge.
        nodes = [n for n in build_snapshot(world).nodes]
        edge = {
            "predicate": predicate,
            "source": {"id": "T01", "version": "sha256:x"},
            "target": {"id": "T02", "version": "sha256:y"},
        }
        with pytest.raises(DevGraphError) as ei:
            validate_graph(nodes, [edge])
        assert ei.value.kind == "unknown_predicate"
        assert "T01" in ei.value.offender and "T02" in ei.value.offender

    def test_single_target_cardinality_is_enforced(self, world: Path):
        nodes = [n for n in build_snapshot(world).nodes]
        edges = [
            {"predicate": "assigned_to", "source": {"id": "T01", "version": ""}, "target": {"id": "P-A", "version": ""}},
            {"predicate": "assigned_to", "source": {"id": "T01", "version": ""}, "target": {"id": "P-B", "version": ""}},
        ]
        with pytest.raises(DevGraphError) as ei:
            validate_graph(nodes, edges)
        assert ei.value.kind == "cardinality"
        assert "T01" in ei.value.offender and "P-B" in ei.value.offender

    def test_duplicate_id_within_a_file_names_the_node(self, world: Path):
        seed = _load(world, WP_SEED)
        seed["work_packages"][0]["tasks"][1]["task_id"] = "T01"
        _dump(world, WP_SEED, seed)
        with pytest.raises(DevGraphError) as ei:
            build_snapshot(world)
        assert ei.value.kind == "duplicate_id" and ei.value.offender == "T01"

    def test_duplicate_id_across_files_names_the_node(self, world: Path):
        objs = _load(world, OBJECTIVES)
        objs["objectives"][0]["objective_id"] = "P-A"
        _dump(world, OBJECTIVES, objs)
        with pytest.raises(DevGraphError) as ei:
            build_snapshot(world)
        assert ei.value.kind == "duplicate_id" and ei.value.offender == "P-A"

    def test_record_without_its_declared_key_is_rejected(self, world: Path):
        objs = _load(world, OBJECTIVES)
        del objs["objectives"][1]["objective_id"]
        _dump(world, OBJECTIVES, objs)
        with pytest.raises(DevGraphError) as ei:
            build_snapshot(world)
        assert ei.value.kind == "malformed_record"
        assert OBJECTIVES.as_posix() in ei.value.offender

    def test_malformed_json_is_rejected_naming_the_file(self, world: Path):
        (world / MILESTONES).write_text("{not json", encoding="utf-8")
        with pytest.raises(DevGraphError) as ei:
            build_snapshot(world)
        assert ei.value.kind == "malformed_record"
        assert MILESTONES.as_posix() in ei.value.offender


# --------------------------------------------------------------------------- #
# Empty Tier 3
# --------------------------------------------------------------------------- #


class TestEmptyTier3:
    def test_empty_tier3_is_an_explicit_empty_snapshot(self, tmp_path: Path):
        root = tmp_path / "repo"
        (root / T3).mkdir(parents=True)
        snap = build_snapshot(root)
        assert snap.empty is True
        assert snap.nodes == () and snap.edges == ()
        assert snap.snapshot_id.startswith("sha256:")

    def test_missing_tier3_directory_is_also_explicitly_empty(self, tmp_path: Path):
        root = tmp_path / "repo"
        root.mkdir()
        snap = build_snapshot(root)
        assert snap.empty is True and snap.nodes == ()

    def test_two_empty_builds_share_an_id(self, tmp_path: Path):
        a = tmp_path / "a"
        b = tmp_path / "b"
        a.mkdir()
        b.mkdir()
        assert build_snapshot(a).snapshot_id == build_snapshot(b).snapshot_id


# --------------------------------------------------------------------------- #
# Deterministic component: snapshot writer
# --------------------------------------------------------------------------- #


class TestSnapshotWriterComponent:
    def test_registered_and_claude_free(self):
        assert "dev_graph_snapshot_writer" in COMPONENT_REGISTRY
        import runner.dev_graph as pkg

        src = Path(pkg.__file__).parent
        for py in src.glob("*.py"):
            text = py.read_text(encoding="utf-8")
            assert "invoke_claude" not in text and "claude_transport" not in text, py.name

    def test_byte_equal_replay_through_the_registry(self, world: Path):
        rec = invoke_component("dev_graph_snapshot_writer", "run-1", world)
        assert rec.status == "success", rec.failure_reason
        assert rec.outputs_written == [SNAPSHOT_REL]
        first = (world / SNAPSHOT_REL).read_bytes()
        direct = write_snapshot(world)
        assert direct == world / SNAPSHOT_REL
        assert (world / SNAPSHOT_REL).read_bytes() == first
        rec2 = invoke_component("dev_graph_snapshot_writer", "run-2", world)
        assert rec2.status == "success"
        assert (world / SNAPSHOT_REL).read_bytes() == first
        assert first == build_snapshot(world).to_json_bytes()

    def test_component_fails_closed_on_an_invalid_graph(self, world: Path):
        seed = _load(world, WP_SEED)
        seed["work_packages"][0]["tasks"][2]["responsible_partner"] = "P-Z"
        _dump(world, WP_SEED, seed)
        rec = invoke_component("dev_graph_snapshot_writer", "run-1", world)
        assert rec.status == "failure"
        assert "P-Z" in (rec.failure_reason or "")
        assert not (world / SNAPSHOT_REL).exists()


# --------------------------------------------------------------------------- #
# Agnosticism lint covers the package
# --------------------------------------------------------------------------- #


class TestAgnosticism:
    def test_lint_scans_the_dev_graph_package_and_passes(self):
        from runner.agnosticism_lint import lint_generic_layer

        report = lint_generic_layer(find_repo_root())
        scanned = [p for p in report.scanned_files if p.startswith("runner/dev_graph/")]
        assert "runner/dev_graph/__init__.py" in scanned
        assert not [v for v in report.violations if v.path.startswith("runner/dev_graph/")]
