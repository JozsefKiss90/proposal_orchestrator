"""FIELDWISE ticket 4 — architecture-inputs seed acceptance tests.

Pins the durable acceptance criteria of plans/fieldwise_tickets.md ticket 4:
the six architecture_inputs files exist with the plan §5 envelope, draft
content is Confirmed, derived content is Inferred with a stated derivation,
person-months and KPIs are Unresolved (never invented values), and
hand_lift_provenance.json covers the six files.

Read-only: these tests never write to docs/.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ARCH = REPO_ROOT / "docs" / "tier3_project_instantiation" / "architecture_inputs"
PROVENANCE = (
    REPO_ROOT / "docs" / "tier3_project_instantiation" / "hand_lift_provenance.json"
)

SIX_FILES = [
    "objectives.json",
    "outcomes.json",
    "impacts.json",
    "workpackage_seed.json",
    "milestones_seed.json",
    "risks.json",
]

VALID_STATUSES = {"Confirmed", "Inferred", "Assumed", "Unresolved"}

DRAFT_SOURCE = (
    "docs/tier3_project_instantiation/source_materials/part_b_draft_v0/"
    "FIELDWISE_MSCA_Master_Draft.docx"
)


def _load(name: str) -> dict:
    path = ARCH / name
    assert path.is_file(), f"{name} does not exist"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _iter_status_records(obj, path="$"):
    """Yield (json_path, record) for every dict carrying validation_status."""
    if isinstance(obj, dict):
        if "validation_status" in obj:
            yield path, obj
        for key, value in obj.items():
            yield from _iter_status_records(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from _iter_status_records(item, f"{path}[{i}]")


class TestEnvelope:
    @pytest.mark.parametrize("name", SIX_FILES)
    def test_file_exists_with_section5_envelope(self, name):
        data = _load(name)
        prov = data.get("_provenance")
        assert isinstance(prov, dict), f"{name} missing _provenance envelope"
        assert prov.get("source") == DRAFT_SOURCE
        assert "lift_record" in prov and "fieldwise-tier3-lift" in prov["lift_record"]
        assert prov.get("provenance_manifest") == (
            "docs/tier3_project_instantiation/hand_lift_provenance.json"
        )
        assert any("CLAUDE.md" in a for a in prov.get("authority", []))

    @pytest.mark.parametrize("name", SIX_FILES)
    def test_every_record_carries_exactly_one_valid_status(self, name):
        data = _load(name)
        records = list(_iter_status_records(data))
        assert records, f"{name} carries no status-bearing records"
        for path, record in records:
            status = record["validation_status"]
            assert status in VALID_STATUSES, f"{name} {path}: bad status {status!r}"

    @pytest.mark.parametrize("name", SIX_FILES)
    def test_non_confirmed_records_state_why(self, name):
        data = _load(name)
        for path, record in _iter_status_records(data):
            if record["validation_status"] != "Confirmed":
                note = record.get("note", "")
                assert note.strip(), (
                    f"{name} {path}: {record['validation_status']} record "
                    "has no note (plan §5 requires one on anything not Confirmed)"
                )

    @pytest.mark.parametrize("name", SIX_FILES)
    def test_confirmed_records_cite_a_source(self, name):
        data = _load(name)
        for path, record in _iter_status_records(data):
            if record["validation_status"] == "Confirmed":
                assert record.get("source_ref", "").strip(), (
                    f"{name} {path}: Confirmed record has no source_ref"
                )


class TestObjectives:
    def test_o1_to_o6_confirmed_with_draft_refs(self):
        data = _load("objectives.json")
        objectives = {o["objective_id"]: o for o in data["objectives"]}
        assert sorted(objectives) == ["O1", "O2", "O3", "O4", "O5", "O6"]
        for oid, record in objectives.items():
            assert record["validation_status"] == "Confirmed", oid
            assert "§1.1.8" in record["source_ref"], oid
            assert record.get("title", "").strip(), oid
            assert record.get("measurable_output", "").strip(), oid


class TestMilestones:
    def test_ms1_to_ms5_confirmed_with_draft_months(self):
        data = _load("milestones_seed.json")
        milestones = {m["milestone_id"]: m for m in data["milestones"]}
        assert sorted(milestones) == ["MS1", "MS2", "MS3", "MS4", "MS5"]
        expected_months = {"MS1": 6, "MS2": 12, "MS3": 16, "MS4": 20, "MS5": 23}
        for mid, record in milestones.items():
            assert record["validation_status"] == "Confirmed", mid
            assert record["due_month"] == expected_months[mid], mid


class TestRisks:
    def test_thirteen_risks_confirmed_with_likelihood_impact_mitigation(self):
        data = _load("risks.json")
        risks = data["risks"]
        assert len(risks) == 13
        for record in risks:
            assert record["validation_status"] == "Confirmed", record.get("risk_id")
            assert record["likelihood"] in {"L", "M", "H"}
            assert record["impact"] in {"L", "M", "H"}
            assert record.get("mitigation", "").strip()


class TestDerivedContentIsInferred:
    def test_outcome_separation_is_inferred_with_derivation(self):
        data = _load("outcomes.json")
        outcomes = data["outcomes"]
        assert outcomes, "outcomes.json carries no derived outcome records"
        for record in outcomes:
            assert record["validation_status"] == "Inferred", record.get("outcome_id")
            assert record.get("note", "").strip(), record.get("outcome_id")

    def test_outputs_are_confirmed_deliverables(self):
        data = _load("outcomes.json")
        outputs = {o["deliverable_id"]: o for o in data["outputs"]}
        for did in [
            "D1.1", "D1.2", "D2.1", "D2.2", "D3.1", "D3.2",
            "D4.1", "D4.2", "D4.3", "D5.1", "D5.2", "D5.3", "D5.4", "D5.5",
        ]:
            assert did in outputs, f"draft deliverable {did} missing"
            assert outputs[did]["validation_status"] == "Confirmed", did

    def test_task_month_allocation_is_inferred(self):
        data = _load("workpackage_seed.json")
        alloc = data["task_month_allocation"]
        assert alloc["validation_status"] == "Inferred"
        assert alloc.get("note", "").strip()
        task_ids = {a["task_id"] for a in alloc["allocations"]}
        assert len(task_ids) == 32  # T1.1-T1.5 + T2.1-T2.6 + T3.1-T3.7 + T4.1-T4.7 + T5.1-T5.7
        for allocation in alloc["allocations"]:
            assert isinstance(allocation["start_month"], int)
            assert isinstance(allocation["end_month"], int)

    def test_dependencies_are_inferred_with_rationale(self):
        data = _load("workpackage_seed.json")
        deps = data["dependencies"]
        assert deps, "no dependency edges seeded"
        for record in deps:
            assert record["validation_status"] == "Inferred"
            assert record.get("note", "").strip()
            assert record["from_wp"].startswith("WP")
            assert record["to_wp"].startswith("WP")


class TestNothingInvented:
    def test_person_months_unresolved_not_numeric(self):
        data = _load("workpackage_seed.json")
        pm = data["person_months"]
        assert pm["validation_status"] == "Unresolved"
        assert pm.get("note", "").strip()
        for wp in data["work_packages"]:
            assert "person_months" not in wp, (
                f"{wp['id']} carries a person_months value with no draft source"
            )

    def test_kpis_unresolved_not_invented(self):
        data = _load("impacts.json")
        kpis = data["kpis"]
        assert kpis["validation_status"] == "Unresolved"
        assert kpis.get("note", "").strip()
        assert "values" not in kpis and "targets" not in kpis


class TestWorkPackages:
    def test_five_wps_confirmed_with_draft_month_ranges(self):
        data = _load("workpackage_seed.json")
        wps = {wp["id"]: wp for wp in data["work_packages"]}
        expected = {
            "WP1": (1, 6),
            "WP2": (3, 14),
            "WP3": (6, 18),
            "WP4": (12, 21),
            "WP5": (16, 24),
        }
        assert sorted(wps) == sorted(expected)
        for wp_id, (start, end) in expected.items():
            record = wps[wp_id]
            assert record["validation_status"] == "Confirmed", wp_id
            assert record["start_month"] == start, wp_id
            assert record["end_month"] == end, wp_id

    def test_seed_satisfies_dependency_normalizer_bounds(self):
        from runner.dependency_normalizer import _build_wp_bounds

        bounds = _build_wp_bounds(_load("workpackage_seed.json"))
        assert set(bounds) == {"WP1", "WP2", "WP3", "WP4", "WP5"}

    def test_d13_career_development_plan_seeded(self):
        """Operator accepted input pack item 6: D1.3 CDP at M3 (CC-13)."""
        data = _load("workpackage_seed.json")
        wp1 = next(wp for wp in data["work_packages"] if wp["id"] == "WP1")
        d13 = next(
            d for d in wp1["deliverables"] if d["deliverable_id"] == "D1.3"
        )
        assert d13["due_month"] == 3
        assert "input pack item 6" in d13["source_ref"]


class TestProvenanceManifest:
    def test_manifest_covers_all_six_files(self):
        with PROVENANCE.open(encoding="utf-8") as fh:
            manifest = json.load(fh)
        covered = {
            entry["artifact"].split("/")[-1]
            for entry in manifest["lifted_artifacts"]
            if entry["artifact"].startswith("architecture_inputs/")
        }
        assert covered == set(SIX_FILES)
