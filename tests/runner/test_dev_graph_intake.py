"""
Dev-graph ESR intake record and the tagged ESR-shaped document.

Every test copies ``tests/fixtures/dev_graph_synthetic`` into a temporary root.
The intake record is exercised through the public ``runner.dev_graph`` entry
points; the planted ESR-shaped candidate is imported next to the real one and
the blind view is asked for a package around the candidate document. Nothing
here touches a real project, the scheduler, or a gate.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from runner.dev_graph import (
    ESR_AVAILABILITY,
    INTAKE_REL,
    INTAKE_SCHEMA_ID,
    PERMITTED_PURPOSES,
    POLICY_VERSION,
    DevGraphError,
    EsrIntake,
    build_package,
    build_snapshot,
    import_document,
    read_esr_intake,
    record_esr_intake,
)
from runner.dev_graph.policies import HISTORICAL_FEEDBACK_TAGS
from runner.paths import find_repo_root

FIXTURE = find_repo_root() / "tests" / "fixtures" / "dev_graph_synthetic"
CANDIDATE = Path("docs/tier5_deliverables/candidates/synthetic_candidate.json")
ESR_DOC = Path("docs/tier5_deliverables/candidates/synthetic_esr.json")

BIG = 100_000


@pytest.fixture
def world(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    return root


def _intake(root: Path, **kw) -> EsrIntake:
    args = dict(
        intake_id="INTAKE-1",
        document_id="CAND-1",
        submission_id="SUB-1",
        call_id="SYN-CALL-01",
        permitted_purpose="blind_pre_evaluation",
    )
    args.update(kw)
    return record_esr_intake(root, **args)


# --------------------------------------------------------------------------- #
# The intake record
# --------------------------------------------------------------------------- #


class TestIntakeRecord:
    def test_closed_vocabularies(self):
        assert ESR_AVAILABILITY == {"unknown", "unavailable", "not_applicable", "available"}
        assert PERMITTED_PURPOSES == {"blind_pre_evaluation", "esr_informed_review"}

    def test_prior_submission_without_an_esr_stores_unknown_never_available(self, world: Path):
        rec = _intake(world, prior_submission=True)
        assert rec.prior_submission is True
        assert rec.esr_availability == "unknown"
        stored = json.loads((world / INTAKE_REL / "INTAKE-1.json").read_text(encoding="utf-8"))
        assert stored["schema_id"] == INTAKE_SCHEMA_ID
        assert stored["esr_availability"] == "unknown"
        assert stored["submission_id"] == "SUB-1"
        assert stored["call_id"] == "SYN-CALL-01"
        assert stored["permitted_purpose"] == "blind_pre_evaluation"
        assert "available" not in json.dumps(stored).replace("unavailable", "")

    def test_available_needs_a_declared_reference(self, world: Path):
        with pytest.raises(DevGraphError) as exc:
            _intake(world, esr_availability="available")
        assert "esr_reference" in str(exc.value)
        rec = _intake(world, esr_availability="available", esr_reference="ESR-1", prior_submission=True)
        assert rec.esr_availability == "available"
        assert rec.esr_reference == "ESR-1"

    def test_a_reference_without_a_declaration_is_refused(self, world: Path):
        with pytest.raises(DevGraphError, match="esr_availability"):
            _intake(world, esr_reference="ESR-1")

    @pytest.mark.parametrize("field,value", [
        ("esr_availability", "maybe"),
        ("permitted_purpose", "anything"),
        ("intake_id", "bad id"),
        ("submission_id", ""),
        ("call_id", ""),
        ("document_id", ""),
    ])
    def test_bad_values_are_refused_naming_the_field(self, world: Path, field, value):
        with pytest.raises(DevGraphError) as exc:
            _intake(world, **{field: value})
        assert field in str(exc.value)

    def test_record_is_immutable_and_rereadable(self, world: Path):
        first = _intake(world, prior_submission=True)
        path = world / INTAKE_REL / "INTAKE-1.json"
        before = path.read_bytes()
        again = _intake(world, prior_submission=True)
        assert again == first
        assert path.read_bytes() == before
        with pytest.raises(DevGraphError, match="immutable"):
            _intake(world, prior_submission=True, esr_availability="unavailable")
        assert path.read_bytes() == before
        assert read_esr_intake(world, "INTAKE-1") == first
        assert "recorded_at" not in json.loads(before)

    def test_missing_record_is_refused(self, world: Path):
        with pytest.raises(DevGraphError, match="INTAKE-9"):
            read_esr_intake(world, "INTAKE-9")


# --------------------------------------------------------------------------- #
# The planted ESR-shaped document
# --------------------------------------------------------------------------- #


def _blind_package(root: Path, seed: str):
    snap = build_snapshot(root)
    return snap, build_package(
        snap,
        task=seed,
        view="blind_pre_evaluation",
        budget=BIG,
        policy_version=POLICY_VERSION,
        expected_snapshot_id=snap.snapshot_id,
        project="SYN-PROJECT",
        profile_version="profile-0",
    )


class TestEsrShapedDocument:
    def test_fixture_esr_is_tagged_and_carries_esr_tokens(self):
        raw = json.loads((FIXTURE / ESR_DOC).read_text(encoding="utf-8"))
        assert set(raw["tags"]) <= HISTORICAL_FEEDBACK_TAGS
        assert "historical_feedback" in raw["tags"]
        assert "ESR" in json.dumps(raw)

    def test_tags_land_on_the_document_and_every_derived_node(self, world: Path):
        ref = import_document(world, ESR_DOC, state="submitted")
        snap = build_snapshot(world)
        derived = [n for n in snap.nodes if n["id"] == ref.id or n["content"].get("document") == ref.id]
        assert len(derived) >= 3
        for n in derived:
            assert set(n["content"]["tags"]) >= {"historical_feedback"}, n["id"]

    def test_untagged_candidate_content_is_unchanged(self, world: Path):
        import_document(world, CANDIDATE)
        snap = build_snapshot(world)
        assert not any("tags" in n["content"] for n in snap.nodes if n["type"] in ("passage", "claim", "commitment", "artifact_version"))

    def test_blind_package_around_the_candidate_excludes_the_esr_by_path(self, world: Path):
        cand = import_document(world, CANDIDATE)
        esr = import_document(world, ESR_DOC, state="submitted")
        snap, pkg = _blind_package(world, cand.id)
        rendered = json.dumps(pkg.to_dict())
        assert "ESR" not in rendered
        assert esr.id not in rendered
        excluded = [e for e in pkg.manifest["exclusions"] if e["reason"] == "policy_forbidden"]
        assert any(e["path"] == esr.path for e in excluded)
        assert all(e["detail"].startswith("tag_forbidden:") for e in excluded if e["path"] == esr.path)
        # The candidate's own passages and claims are in.
        included = {i["id"] for i in pkg.manifest["included"]}
        assert {f"{cand.id}#S1", f"{cand.id}#S2", f"{cand.id}#S3", f"{cand.id}#CL-1"} <= included

    def test_audit_view_sees_the_esr(self, world: Path):
        cand = import_document(world, CANDIDATE)
        esr = import_document(world, ESR_DOC, state="submitted")
        snap = build_snapshot(world)
        pkg = build_package(
            snap, task=cand.id, view="integrity_audit", budget=BIG,
            policy_version=POLICY_VERSION, expected_snapshot_id=snap.snapshot_id,
            project="SYN-PROJECT", profile_version="profile-0",
        )
        assert any(i["id"].startswith(esr.id) for i in pkg.manifest["included"])
