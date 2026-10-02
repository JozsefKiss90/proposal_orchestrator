"""The dev-graph run records the impact planner reads, and how they are derived.

The planner refuses without ``run_records.json``, and the schema specification
places that file by hand. Hand-typing it would type a node list the artifacts
already carry, so ``tools/derive_dev_graph_run_records.py`` derives it: one
artifact record per Tier 5 proposal section, whose inputs are the snapshot node
ids the section's own text names, and one check record per gate result, whose
inputs are null because no gate result in this world names a graph node.

Every expected value here is read back off the snapshot, the sections and the
gate results. A test that typed the node count would be a second copy of the
measurement, free to drift from what it claims to describe.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from runner.atomic_write import canonical_json_bytes
from runner.dev_graph.builder import build_snapshot
from runner.dev_graph.impact import (
    RUN_RECORDS_REL,
    RUN_RECORDS_SCHEMA_ID,
    normalise_run_records,
)
from tools.derive_dev_graph_run_records import (
    GATE_RESULT_GLOBS,
    SECTION_DIR_REL,
    build_document,
    derive_run_records,
    named_node_ids,
    record_id_for,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def _sections() -> list[Path]:
    return sorted((REPO_ROOT / SECTION_DIR_REL).glob("*.json"))


def _gate_results() -> list[Path]:
    return sorted(
        p for pattern in GATE_RESULT_GLOBS for p in REPO_ROOT.glob(pattern)
    )


@pytest.fixture(scope="module")
def records() -> list[dict]:
    return derive_run_records(REPO_ROOT)


class TestNamedNodeIds:
    """The one derivation rule: the ids the text itself names."""

    def test_matches_an_id_on_a_word_boundary(self) -> None:
        assert named_node_ids('the lead is "P01" here', {"P01", "P0"}) == ["P01"]

    def test_does_not_match_an_id_inside_a_longer_identifier(self) -> None:
        # D3.2 must not be found inside D3.21, or a section would declare a
        # dependency on a deliverable it never mentions.
        assert named_node_ids("see D3.21", {"D3.2"}) == []

    def test_matches_a_task_id_that_ends_in_a_digit_after_a_dot(self) -> None:
        assert named_node_ids("task T3.1 runs", {"T3.1"}) == ["T3.1"]

    def test_returns_the_ids_sorted_and_deduplicated(self) -> None:
        assert named_node_ids("WP2 WP1 WP2", {"WP1", "WP2"}) == ["WP1", "WP2"]


class TestDerivedRecords:
    """What the demo world's records say, checked against the demo world."""

    def test_one_record_per_section_and_one_per_gate_result(
        self, records: list[dict]
    ) -> None:
        kinds = [r["kind"] for r in records]
        assert kinds.count("artifact") == len(_sections())
        assert kinds.count("check") == len(_gate_results())

    def test_the_records_pass_the_planner_s_own_validation(
        self, records: list[dict]
    ) -> None:
        assert normalise_run_records(records, "derived") == sorted(
            normalise_run_records(records, "derived"), key=lambda r: r["record_id"]
        )

    def test_each_section_declares_the_node_ids_its_text_names(
        self, records: list[dict]
    ) -> None:
        ids = {n["id"] for n in build_snapshot(REPO_ROOT).nodes}
        for section in _sections():
            record = next(r for r in records if r["path"].endswith(section.name))
            expected = named_node_ids(section.read_text(encoding="utf-8-sig"), ids)
            assert record["inputs"] == (expected or None)

    def test_every_section_in_this_world_names_at_least_one_node(
        self, records: list[dict]
    ) -> None:
        # The null branch is the fail-closed one. If it ever fires here, the
        # section stopped naming the project and that is the finding.
        artifacts = [r for r in records if r["kind"] == "artifact"]
        assert artifacts
        assert all(r["inputs"] for r in artifacts)

    def test_the_sections_differ_in_what_they_name(self, records: list[dict]) -> None:
        # A derivation that gave every section the same inputs would make the
        # planner unable to tell them apart, and would be a bug in the scan.
        counts = {len(r["inputs"]) for r in records if r["kind"] == "artifact"}
        assert len(counts) > 1

    def test_every_check_declares_unknown_coverage(self, records: list[dict]) -> None:
        # No gate result in this world names a graph node, so the only honest
        # value is null, which the planner reads as rerun.
        checks = [r for r in records if r["kind"] == "check"]
        assert checks
        assert all(r["inputs"] is None for r in checks)

    def test_no_gate_result_names_a_graph_node(self) -> None:
        # The premise of the rule above, checked rather than assumed.
        ids = {n["id"] for n in build_snapshot(REPO_ROOT).nodes}
        for gate in _gate_results():
            assert named_node_ids(gate.read_text(encoding="utf-8-sig"), ids) == []

    def test_every_declared_input_is_a_node_of_the_current_snapshot(
        self, records: list[dict]
    ) -> None:
        ids = {n["id"] for n in build_snapshot(REPO_ROOT).nodes}
        for record in records:
            assert set(record["inputs"] or []) <= ids

    def test_no_record_declares_a_package(self, records: list[dict]) -> None:
        # The evidence packages this world holds are per-task integrity views,
        # not the view a section was drafted from. Citing one would misdescribe
        # the artifact's provenance.
        assert all(r.get("package") is None for r in records)


class TestDocument:
    """The artifact the tool writes."""

    def test_carries_the_schema_the_planner_requires(self) -> None:
        assert build_document(REPO_ROOT)["schema_id"] == RUN_RECORDS_SCHEMA_ID

    def test_states_the_derivation_rule_it_applied(self) -> None:
        doc = build_document(REPO_ROOT)
        assert doc["derivation_rule"]
        assert doc["unknown_coverage_rule"]

    def test_a_second_derivation_is_byte_equal(self) -> None:
        assert canonical_json_bytes(build_document(REPO_ROOT)) == canonical_json_bytes(
            build_document(REPO_ROOT)
        )

    def test_the_written_artifact_is_current(self) -> None:
        path = REPO_ROOT / RUN_RECORDS_REL
        if not path.is_file():
            pytest.skip("run records not written yet")
        assert path.read_bytes() == canonical_json_bytes(build_document(REPO_ROOT))


class TestDerivationOverAnotherWorld:
    """The rules hold where the demo's numbers do not."""

    def test_a_world_with_no_section_and_no_gate_yields_no_record(
        self, tmp_path: Path
    ) -> None:
        assert derive_run_records(tmp_path) == []

    def test_a_section_naming_no_node_declares_unknown_coverage(
        self, tmp_path: Path
    ) -> None:
        sections = tmp_path / SECTION_DIR_REL
        sections.mkdir(parents=True)
        (sections / "empty_section.json").write_text(
            json.dumps({"schema_id": "x", "text": "no identifier here"}), encoding="utf-8"
        )

        records = derive_run_records(tmp_path)

        assert [r["record_id"] for r in records] == ["proposal_sections.empty_section"]
        assert records[0]["inputs"] is None

    def test_every_record_id_is_a_plain_identifier(self, records: list[dict]) -> None:
        plain = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
        assert all(plain.match(r["record_id"]) for r in records)

    def test_the_record_id_names_the_parent_directory_and_the_stem(self) -> None:
        # Seven phase directories each hold a gate_result.json, so the stem
        # alone would collide and the planner would refuse the document.
        assert record_id_for(Path("a/phase1_call_analysis/gate_result.json")) == (
            "phase1_call_analysis.gate_result"
        )
