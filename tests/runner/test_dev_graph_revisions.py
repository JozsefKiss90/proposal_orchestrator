"""
Dev-graph revision contracts, candidate versioning and assessment
applicability.

Every test copies ``tests/fixtures/dev_graph_synthetic`` into a temporary
root, imports the fixture candidate, and drives the public
``runner.dev_graph`` entry points. Nothing here dispatches a phase, evaluates
a gate or invokes Claude.
"""

from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest

from runner.deterministic_components import COMPONENT_REGISTRY, invoke_component
from runner.dev_graph import (
    APPLICABILITY_REASONS,
    CHANGE_CLASSES,
    CONTRACT_VERDICTS,
    DOCUMENTS_REL,
    POLICY_VERSION,
    REVISION_REQUEST_REL,
    REVISION_SCHEMA_ID,
    REVISIONS_REL,
    Applicability,
    ContractCheck,
    DevGraphError,
    RevisionContract,
    bind_assessment,
    build_snapshot,
    change_set,
    check_applicability,
    check_revision,
    create_candidate_version,
    current_commitments,
    import_document,
    load_snapshot,
    normalise_contract,
    read_revision_record,
    record_change,
    write_revision_record,
)
from runner.dev_graph.builder import OBJECTIVES_REL, WP_SEED_REL
from runner.paths import find_repo_root

FIXTURE = find_repo_root() / "tests" / "fixtures" / "dev_graph_synthetic"
CANDIDATE = Path("docs/tier5_deliverables/candidates/synthetic_candidate.json")
CANDIDATE_V2 = Path("docs/tier5_deliverables/candidates/synthetic_candidate_v2.json")

RESPONSIBILITY_CONTRACT = {
    "contract_id": "RC-1",
    "permitted_change_classes": ["responsibility"],
    "protected_node_ids": ["OBJ-1", "D1.1"],
    "unresolved_items": [],
}


@pytest.fixture
def world(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    import_document(root, CANDIDATE)
    return root


def _load(root: Path, rel: Path | str) -> dict:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def _dump(root: Path, rel: Path | str, obj: dict) -> None:
    (root / rel).parent.mkdir(parents=True, exist_ok=True)
    (root / rel).write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _tree_bytes(root: Path, rel: Path | str) -> dict[str, bytes]:
    base = root / rel
    if not base.exists():
        return {}
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in base.rglob("*") if p.is_file()}


def _t03_to_c(seed: dict) -> dict:
    t03 = next(t for t in seed["work_packages"][0]["tasks"] if t["task_id"] == "T03")
    t03["responsible_partner"] = "P-C"
    return seed


def _record_t03_change(root: Path, change_id: str = "CR-1"):
    return record_change(root, WP_SEED_REL, _t03_to_c(_load(root, WP_SEED_REL)), change_id=change_id)


def _t03_change_set(root: Path) -> dict:
    change = _record_t03_change(root)
    return change.change_set


def _write_candidate_v2(root: Path) -> None:
    doc = _load(root, CANDIDATE)
    s2 = next(s for s in doc["sections"] if s["section_id"] == "S2")
    s2["content"] = "Task three is led by Participant C with Participant B contributing. It starts in month ten."
    doc["commitments"][0]["text"] = "Participant C leads Task three."
    _dump(root, CANDIDATE_V2, doc)


def _document_nodes(snap) -> dict[str, dict]:
    return {n["id"]: n for n in snap.nodes if n["type"] == "artifact_version"}


# --------------------------------------------------------------------------- #
# The revision contract checker (pure)
# --------------------------------------------------------------------------- #


class TestVocabularies:
    def test_vocabularies_are_closed(self):
        assert CONTRACT_VERDICTS == {"accepted", "rejected", "flagged_for_review"}
        assert APPLICABILITY_REASONS == {
            "candidate_version_changed",
            "profile_version_changed",
            "policy_version_changed",
        }
        assert "responsibility" in CHANGE_CLASSES and "objective" in CHANGE_CLASSES


class TestContractChecker:
    def test_a_responsibility_change_under_a_permitting_contract_is_accepted(self, world: Path):
        cs = _t03_change_set(world)
        result = check_revision(normalise_contract(RESPONSIBILITY_CONTRACT), cs)
        assert isinstance(result, ContractCheck)
        assert result.verdict == "accepted"
        assert result.change_classes == ("responsibility",)
        assert result.protected_hits == ()
        assert result.unpermitted_classes == ()
        assert result.unresolved == ()

    def test_a_change_that_also_alters_the_protected_objective_is_rejected_naming_it(self, world: Path):
        before = build_snapshot(world)
        _dump(world, WP_SEED_REL, _t03_to_c(_load(world, WP_SEED_REL)))
        objectives = _load(world, OBJECTIVES_REL)
        objectives["objectives"][0]["measurable_target"] = "Target one, revised"
        _dump(world, OBJECTIVES_REL, objectives)
        cs = change_set(before, build_snapshot(world))

        result = check_revision(normalise_contract(RESPONSIBILITY_CONTRACT), cs)
        assert result.verdict == "rejected"
        assert [h["node_id"] for h in result.protected_hits] == ["OBJ-1"]
        assert result.protected_hits[0]["via"] == ["changed:OBJ-1"]
        assert "objective" in result.change_classes

    def test_a_removed_edge_to_a_protected_node_is_a_hit(self, world: Path):
        seed = _load(world, WP_SEED_REL)
        seed["work_packages"][0]["deliverables"][0]["produced_by"] = []
        before = build_snapshot(world)
        _dump(world, WP_SEED_REL, seed)
        cs = change_set(before, build_snapshot(world))

        result = check_revision(normalise_contract(RESPONSIBILITY_CONTRACT), cs)
        assert result.verdict == "rejected"
        hit = next(h for h in result.protected_hits if h["node_id"] == "D1.1")
        assert "T03 -produces-> D1.1" in hit["via"]

    def test_an_unpermitted_change_class_is_flagged_for_review(self, world: Path):
        seed = _load(world, WP_SEED_REL)
        t03 = next(t for t in seed["work_packages"][0]["tasks"] if t["task_id"] == "T03")
        t03["end_month"] = 20
        before = build_snapshot(world)
        _dump(world, WP_SEED_REL, seed)
        cs = change_set(before, build_snapshot(world))

        result = check_revision(normalise_contract(RESPONSIBILITY_CONTRACT), cs)
        assert result.verdict == "flagged_for_review"
        assert result.change_classes == ("timing",)
        assert result.unpermitted_classes == ("timing",)

    def test_an_unresolved_capacity_the_change_bears_on_stays_flagged(self, world: Path):
        contract = normalise_contract(
            {
                **RESPONSIBILITY_CONTRACT,
                "unresolved_items": [
                    {"item_id": "U-1", "description": "Capacity of Participant C for Task three", "node_ids": ["P-C"]}
                ],
            }
        )
        result = check_revision(contract, _t03_change_set(world))
        assert result.verdict == "flagged_for_review"
        assert len(result.unresolved) == 1
        item = result.unresolved[0]
        assert item["item_id"] == "U-1" and item["status"] == "unresolved" and item["bears_on_change"] is True
        assert "T03 -assigned_to-> P-C" in item["via"]
        assert "approved" not in json.dumps(result.to_dict())

    def test_an_unresolved_item_the_change_does_not_touch_is_carried_not_approved(self, world: Path):
        contract = normalise_contract(
            {
                **RESPONSIBILITY_CONTRACT,
                "unresolved_items": [{"item_id": "U-2", "description": "Capacity of Participant A", "node_ids": ["P-A"]}],
            }
        )
        result = check_revision(contract, _t03_change_set(world))
        assert result.verdict == "accepted"
        assert result.unresolved[0]["status"] == "unresolved" and result.unresolved[0]["bears_on_change"] is False

    def test_an_unresolved_item_naming_no_node_bears_on_every_change(self, world: Path):
        contract = normalise_contract(
            {**RESPONSIBILITY_CONTRACT, "unresolved_items": [{"item_id": "U-3", "description": "Whole contract open"}]}
        )
        result = check_revision(contract, _t03_change_set(world))
        assert result.verdict == "flagged_for_review" and result.unresolved[0]["bears_on_change"] is True

    def test_rejection_outranks_review(self, world: Path):
        before = build_snapshot(world)
        objectives = _load(world, OBJECTIVES_REL)
        objectives["objectives"][0]["title"] = "Objective one, renamed"
        _dump(world, OBJECTIVES_REL, objectives)
        cs = change_set(before, build_snapshot(world))
        contract = normalise_contract(
            {**RESPONSIBILITY_CONTRACT, "unresolved_items": [{"item_id": "U-3", "description": "open"}]}
        )
        result = check_revision(contract, cs)
        assert result.verdict == "rejected" and result.unpermitted_classes == ("objective",)

    def test_an_empty_change_set_is_accepted_with_no_classes(self, world: Path):
        snap = build_snapshot(world)
        result = check_revision(normalise_contract(RESPONSIBILITY_CONTRACT), change_set(snap, snap))
        assert result.verdict == "accepted" and result.change_classes == ()

    def test_the_checker_is_pure(self, world: Path):
        cs = _t03_change_set(world)
        contract = normalise_contract(RESPONSIBILITY_CONTRACT)
        frozen_cs, frozen_contract = copy.deepcopy(cs), copy.deepcopy(contract)
        first = check_revision(contract, cs)
        second = check_revision(contract, cs)
        assert first == second and first.to_dict() == second.to_dict()
        assert cs == frozen_cs and contract == frozen_contract

    @pytest.mark.parametrize(
        "mutation, needle",
        [
            (lambda c: c.update(permitted_change_classes=["related_to"]), "related_to"),
            (lambda c: c.update(protected_node_ids=["bad id"]), "bad id"),
            (lambda c: c.update(contract_id=""), "contract_id"),
            (lambda c: c.update(unresolved_items=[{"description": "no id"}]), "item_id"),
            (lambda c: c.update(unresolved_items=[{"item_id": "U", "status": "approved"}]), "approved"),
        ],
    )
    def test_a_malformed_contract_is_refused(self, mutation, needle):
        raw = copy.deepcopy(RESPONSIBILITY_CONTRACT)
        mutation(raw)
        with pytest.raises(DevGraphError) as exc:
            normalise_contract(raw)
        assert exc.value.kind == "malformed_request" and needle in str(exc.value)

    def test_a_malformed_change_set_is_refused(self, world: Path):
        with pytest.raises(DevGraphError) as exc:
            check_revision(normalise_contract(RESPONSIBILITY_CONTRACT), {"nodes": {}})
        assert exc.value.kind == "malformed_request"


# --------------------------------------------------------------------------- #
# Candidate versioning
# --------------------------------------------------------------------------- #


class TestCandidateVersioning:
    def test_a_new_version_supersedes_the_first_with_provenance(self, world: Path):
        first = import_document(world, CANDIDATE)
        first_bytes = (world / first.path).read_bytes()
        change = _record_t03_change(world)
        _write_candidate_v2(world)

        second = create_candidate_version(
            world, CANDIDATE_V2, supersedes=first.id, change_id=change.change_id, evidence=["T03", "P-C"]
        )
        assert second.id != first.id and second.path != first.path
        assert (world / first.path).read_bytes() == first_bytes

        snap = build_snapshot(world)
        docs = _document_nodes(snap)
        assert set(docs) == {first.id, second.id}
        edges = [e for e in snap.edges if e["predicate"] == "supersedes"]
        assert len(edges) == 1
        assert edges[0]["source"]["id"] == second.id and edges[0]["target"]["id"] == first.id
        assert edges[0]["target"]["version"] == docs[first.id]["version"]
        prov = docs[second.id]["content"]["provenance"]
        assert prov["change_id"] == change.change_id
        assert prov["supersedes"] == {"id": first.id, "version": docs[first.id]["version"]}
        assert [e["id"] for e in prov["evidence"]] == ["P-C", "T03"]
        assert all(e["version"].startswith("sha256:") for e in prov["evidence"])
        assert "provenance" not in docs[first.id]["content"]

    def test_the_superseded_snapshot_yields_no_current_commitment(self, world: Path):
        first = import_document(world, CANDIDATE)
        change = _record_t03_change(world)
        _write_candidate_v2(world)
        second = create_candidate_version(world, CANDIDATE_V2, supersedes=first.id, change_id=change.change_id)
        current = current_commitments(build_snapshot(world))
        assert {c["content"]["document"] for c in current} == {second.id}
        assert current[0]["content"]["text"] == "Participant C leads Task three."

    def test_the_new_version_is_immutable_and_reimport_is_a_no_op(self, world: Path):
        first = import_document(world, CANDIDATE)
        change = _record_t03_change(world)
        _write_candidate_v2(world)
        kwargs = dict(supersedes=first.id, change_id=change.change_id, evidence=["T03"])
        second = create_candidate_version(world, CANDIDATE_V2, **kwargs)
        second_bytes = (world / second.path).read_bytes()
        again = create_candidate_version(world, CANDIDATE_V2, **kwargs)
        assert again == second and (world / second.path).read_bytes() == second_bytes
        with pytest.raises(DevGraphError) as exc:
            create_candidate_version(world, CANDIDATE_V2, supersedes=first.id, change_id=change.change_id, evidence=[])
        assert exc.value.kind == "immutable_record"

    def test_unknown_predecessor_change_or_evidence_is_refused_before_writing(self, world: Path):
        first = import_document(world, CANDIDATE)
        change = _record_t03_change(world)
        _write_candidate_v2(world)
        before = _tree_bytes(world, DOCUMENTS_REL)
        for kwargs, needle in (
            (dict(supersedes="CAND-9@0000000000000000", change_id=change.change_id), "CAND-9"),
            (dict(supersedes=first.id, change_id="CR-absent"), "CR-absent"),
            (dict(supersedes=first.id, change_id=change.change_id, evidence=["T99"]), "T99"),
        ):
            with pytest.raises(DevGraphError) as exc:
                create_candidate_version(world, CANDIDATE_V2, **kwargs)
            assert exc.value.kind == "malformed_request" and needle in str(exc.value)
        assert _tree_bytes(world, DOCUMENTS_REL) == before

    def test_a_tampered_provenance_version_fails_the_build(self, world: Path):
        first = import_document(world, CANDIDATE)
        change = _record_t03_change(world)
        _write_candidate_v2(world)
        second = create_candidate_version(world, CANDIDATE_V2, supersedes=first.id, change_id=change.change_id)
        rec = _load(world, second.path)
        rec["provenance"]["supersedes"]["version"] = "sha256:" + "0" * 64
        (world / second.path).write_text(json.dumps(rec), encoding="utf-8")
        with pytest.raises(DevGraphError) as exc:
            build_snapshot(world)
        assert exc.value.kind == "malformed_record" and first.id in str(exc.value)

    def test_a_document_cannot_supersede_itself(self, world: Path):
        first = import_document(world, CANDIDATE)
        change = _record_t03_change(world)
        with pytest.raises(DevGraphError) as exc:
            create_candidate_version(world, CANDIDATE, supersedes=first.id, change_id=change.change_id)
        assert exc.value.kind == "malformed_request"


# --------------------------------------------------------------------------- #
# Assessment applicability (pure)
# --------------------------------------------------------------------------- #


class TestApplicability:
    def _versions(self, world: Path) -> tuple[dict, dict]:
        first = import_document(world, CANDIDATE)
        change = _record_t03_change(world)
        _write_candidate_v2(world)
        second = create_candidate_version(world, CANDIDATE_V2, supersedes=first.id, change_id=change.change_id)
        docs = _document_nodes(build_snapshot(world))
        return docs[first.id], docs[second.id]

    def test_an_assessment_bound_to_version_one_is_applicable_to_version_one(self, world: Path):
        v1, _ = self._versions(world)
        node = bind_assessment("ASSESS-1", v1, profile_version="profile-a", policy_version=POLICY_VERSION)
        assert node["type"] == "assessment" and node["id"] == "ASSESS-1"
        result = check_applicability(node, v1, profile_version="profile-a")
        assert isinstance(result, Applicability)
        assert result.applicable is True and result.reasons == ()

    def test_candidate_version_changed(self, world: Path):
        v1, v2 = self._versions(world)
        node = bind_assessment("ASSESS-1", v1, profile_version="profile-a", policy_version=POLICY_VERSION)
        result = check_applicability(node, v2, profile_version="profile-a")
        assert result.applicable is False and result.reasons == ("candidate_version_changed",)
        assert result.bound["candidate"] == {"id": v1["id"], "version": v1["version"]}
        assert result.current["candidate"] == {"id": v2["id"], "version": v2["version"]}

    def test_profile_and_policy_versions_each_produce_their_own_reason(self, world: Path):
        v1, _ = self._versions(world)
        node = bind_assessment("ASSESS-1", v1, profile_version="profile-a", policy_version=POLICY_VERSION)
        by_profile = check_applicability(node, v1, profile_version="profile-b")
        assert by_profile.reasons == ("profile_version_changed",)
        by_policy = check_applicability(node, v1, profile_version="profile-a", policy_version="sha256:" + "0" * 64)
        assert by_policy.reasons == ("policy_version_changed",)
        all_three = check_applicability(node, {"id": "X", "version": "sha256:" + "1" * 64}, profile_version="p", policy_version="q")
        assert all_three.reasons == ("candidate_version_changed", "profile_version_changed", "policy_version_changed")

    def test_assessments_are_never_mutated(self, world: Path):
        v1, v2 = self._versions(world)
        node = bind_assessment("ASSESS-1", v1, profile_version="profile-a", policy_version=POLICY_VERSION)
        frozen = copy.deepcopy(node)
        check_applicability(node, v2, profile_version="profile-b", policy_version="other")
        assert node == frozen
        result = check_applicability(node, v2, profile_version="profile-a")
        assert "applicable" not in node and "applicable" not in node["content"]
        assert result.to_dict()["assessment"] == {"id": node["id"], "version": node["version"]}

    def test_an_assessment_without_a_binding_is_refused(self, world: Path):
        v1, _ = self._versions(world)
        with pytest.raises(DevGraphError) as exc:
            check_applicability({"id": "A", "type": "assessment", "version": "sha256:" + "0" * 64, "content": {}}, v1, profile_version="p")
        assert exc.value.kind == "malformed_record"
        with pytest.raises(DevGraphError):
            check_applicability({"id": "A", "type": "finding", "version": "x", "content": {}}, v1, profile_version="p")


# --------------------------------------------------------------------------- #
# The registered revision record writer
# --------------------------------------------------------------------------- #


def _request(world: Path, first_id: str, change_id: str = "CR-1", **overrides) -> dict:
    req = {
        "revision_id": "REV-1",
        "change_id": change_id,
        "contract": RESPONSIBILITY_CONTRACT,
        "candidate": CANDIDATE_V2.as_posix(),
        "supersedes": first_id,
        "evidence": ["T03", "P-C"],
        **overrides,
    }
    (world / REVISION_REQUEST_REL).parent.mkdir(parents=True, exist_ok=True)
    (world / REVISION_REQUEST_REL).write_text(json.dumps(req), encoding="utf-8")
    return req


class TestRevisionRecordWriter:
    def test_registered_and_claude_free(self):
        assert "dev_graph_revision_record_writer" in COMPONENT_REGISTRY
        text = (find_repo_root() / "runner" / "dev_graph" / "revisions.py").read_text(encoding="utf-8")
        for forbidden in ("dag_scheduler", "gate_evaluator", "claude_transport", "skill_runtime", "write_reuse_metadata"):
            assert forbidden not in text, f"revisions.py names {forbidden}"

    def test_byte_equal_replay_through_the_registry(self, world: Path):
        first = import_document(world, CANDIDATE)
        _record_t03_change(world)
        _write_candidate_v2(world)
        _request(world, first.id)

        rec = invoke_component("dev_graph_revision_record_writer", "run-1", world)
        assert rec.status == "success", rec.failure_reason
        [rel] = rec.outputs_written
        assert rel == f"{REVISIONS_REL}/REV-1.json"
        first_bytes = (world / rel).read_bytes()
        docs_after_first = _tree_bytes(world, DOCUMENTS_REL)

        direct = write_revision_record(world)
        assert [p.as_posix() for p in direct] == [(world / rel).as_posix()]
        rec2 = invoke_component("dev_graph_revision_record_writer", "run-2", world)
        assert rec2.status == "success"
        assert (world / rel).read_bytes() == first_bytes
        assert _tree_bytes(world, DOCUMENTS_REL) == docs_after_first

        doc = json.loads(first_bytes)
        assert doc["schema_id"] == REVISION_SCHEMA_ID and doc["revision_id"] == "REV-1"
        assert doc["check"]["verdict"] == "accepted" and doc["change_id"] == "CR-1"
        assert doc["contract"]["contract_id"] == "RC-1"
        created = doc["candidate_version"]["created"]
        assert created["id"] != first.id and doc["candidate_version"]["previous"]["id"] == first.id
        assert (world / created["path"]).is_file()
        assert "run_id" not in doc and "run-1" not in first_bytes.decode("utf-8")

        loaded = read_revision_record(world, "REV-1")
        assert loaded.to_dict() == doc
        snap = build_snapshot(world)
        assert any(e["predicate"] == "supersedes" and e["source"]["id"] == created["id"] for e in snap.edges)

    def test_a_rejected_check_records_the_verdict_and_creates_no_version(self, world: Path):
        first = import_document(world, CANDIDATE)
        _record_t03_change(world)
        _write_candidate_v2(world)
        _request(world, first.id, contract={**RESPONSIBILITY_CONTRACT, "protected_node_ids": ["T03"]})
        docs_before = _tree_bytes(world, DOCUMENTS_REL)

        rec = invoke_component("dev_graph_revision_record_writer", "run-1", world)
        assert rec.status == "success", rec.failure_reason
        doc = _load(world, rec.outputs_written[0])
        assert doc["check"]["verdict"] == "rejected"
        assert doc["check"]["protected_hits"][0]["node_id"] == "T03"
        assert doc["candidate_version"] is None
        assert _tree_bytes(world, DOCUMENTS_REL) == docs_before

    def test_a_revision_id_is_write_once(self, world: Path):
        first = import_document(world, CANDIDATE)
        _record_t03_change(world)
        _write_candidate_v2(world)
        _request(world, first.id)
        write_revision_record(world)
        _request(world, first.id, evidence=["T03"])
        with pytest.raises(DevGraphError) as exc:
            write_revision_record(world)
        assert exc.value.kind == "immutable_record"

    def test_a_rerequest_under_an_existing_id_writes_no_document_before_refusing(self, world: Path):
        first = import_document(world, CANDIDATE)
        _record_t03_change(world)
        _write_candidate_v2(world)
        _request(world, first.id)
        write_revision_record(world)
        docs_after = _tree_bytes(world, DOCUMENTS_REL)
        # A second recorded change and a third candidate under the same revision id.
        seed = _load(world, WP_SEED_REL)
        seed["work_packages"][0]["tasks"][0]["contributing_partners"] = []
        record_change(world, WP_SEED_REL, seed, change_id="CR-2")
        doc = _load(world, CANDIDATE_V2)
        doc["title"] = "Synthetic candidate, third"
        _dump(world, Path("docs/tier5_deliverables/candidates/synthetic_candidate_v3.json"), doc)
        _request(
            world, first.id, change_id="CR-2",
            candidate="docs/tier5_deliverables/candidates/synthetic_candidate_v3.json",
            contract={**RESPONSIBILITY_CONTRACT, "permitted_change_classes": ["responsibility", "contribution"]},
        )
        with pytest.raises(DevGraphError) as exc:
            write_revision_record(world)
        assert exc.value.kind == "immutable_record"
        assert _tree_bytes(world, DOCUMENTS_REL) == docs_after

    def test_a_missing_change_record_refuses_and_writes_nothing(self, world: Path):
        first = import_document(world, CANDIDATE)
        _write_candidate_v2(world)
        _request(world, first.id, change_id="CR-absent")
        docs_before = _tree_bytes(world, DOCUMENTS_REL)
        rec = invoke_component("dev_graph_revision_record_writer", "run-1", world)
        assert rec.status == "failure" and "CR-absent" in (rec.failure_reason or "")
        assert not (world / REVISIONS_REL).exists()
        assert _tree_bytes(world, DOCUMENTS_REL) == docs_before

    def test_a_malformed_request_is_refused(self, world: Path):
        (world / REVISION_REQUEST_REL).parent.mkdir(parents=True, exist_ok=True)
        (world / REVISION_REQUEST_REL).write_text('{"revision_id": "REV-1"}', encoding="utf-8")
        with pytest.raises(DevGraphError) as exc:
            write_revision_record(world)
        assert exc.value.kind == "malformed_request"
        assert not (world / REVISIONS_REL).exists()


class TestAgnosticism:
    def test_lint_covers_the_new_module(self):
        from runner.agnosticism_lint import lint_generic_layer

        report = lint_generic_layer(find_repo_root())
        assert "runner/dev_graph/revisions.py" in set(report.scanned_files)
        assert not [v for v in report.violations if v.path.startswith("runner/dev_graph/")]


class TestDecisionLog:
    def test_revision_contract_entry_exists(self):
        log = find_repo_root() / "docs/tier4_orchestration_state/decision_log"
        entries = list(log.glob("dev-graph-revision-contracts_*.json"))
        assert len(entries) == 1
        rec = json.loads(entries[0].read_text(encoding="utf-8"))
        assert rec["record_type"] == "decision"
        text = json.dumps(rec)
        for needle in ("flagged_for_review", "supersedes", "candidate_version_changed", "never mutated"):
            assert needle in text
