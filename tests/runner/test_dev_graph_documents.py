"""
Dev-graph document snapshots and separated claim evidence fields.

Every test copies ``tests/fixtures/dev_graph_synthetic`` into a temporary root,
imports the fixture's three-section candidate through the public
``runner.dev_graph.import_document`` entry point, and builds a snapshot with
``runner.dev_graph.build_snapshot``. Nothing here touches a real project, the
scheduler, or a gate.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from runner.deterministic_components import invoke_component
from runner.dev_graph import (
    APPROVALS,
    CURRENT_DOCUMENT_STATES,
    DECLARED_STATUSES,
    DOCUMENT_STATES,
    DOCUMENTS_REL,
    RELATIONSHIPS,
    SNAPSHOT_REL,
    DevGraphError,
    build_snapshot,
    current_commitments,
    import_document,
    write_snapshot,
)
from runner.graph_schema import EVIDENCE_TO_STATUS
from runner.paths import find_repo_root

FIXTURE = find_repo_root() / "tests" / "fixtures" / "dev_graph_synthetic"
CANDIDATE = Path("docs/tier5_deliverables/candidates/synthetic_candidate.json")
SOURCES = Path("docs/tier3_project_instantiation/source_materials/sources.json")
WP_SEED = Path("docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json")


@pytest.fixture
def world(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    return root


def _load(root: Path, rel: Path) -> dict:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def _dump(root: Path, rel: Path, obj: dict) -> None:
    (root / rel).write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _by_type(snap) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for n in snap.nodes:
        out.setdefault(n["type"], []).append(n)
    return out


def _node(snap, nid: str) -> dict:
    return next(n for n in snap.nodes if n["id"] == nid)


# --------------------------------------------------------------------------- #
# Closed vocabularies added by this ticket
# --------------------------------------------------------------------------- #


class TestVocabularies:
    def test_document_lifecycle_states_are_closed(self):
        assert DOCUMENT_STATES == frozenset({"imported", "draft", "submitted", "superseded"})
        assert CURRENT_DOCUMENT_STATES == frozenset({"imported", "draft"})

    def test_claim_field_vocabularies_are_closed(self):
        assert DECLARED_STATUSES == frozenset({"Confirmed", "Inferred", "Assumed", "Unresolved"})
        assert APPROVALS == frozenset({"approved", "pending", "not_applicable"})

    def test_passage_links_to_a_document_snapshot_through_expressed_in(self):
        assert RELATIONSHIPS["expressed_in"].permits("passage", "artifact_version")


# --------------------------------------------------------------------------- #
# Importing a candidate
# --------------------------------------------------------------------------- #


class TestImport:
    def test_import_yields_one_document_snapshot_node_with_state_imported(self, world: Path):
        ref = import_document(world, CANDIDATE)
        snap = build_snapshot(world)
        docs = _by_type(snap)["artifact_version"]
        assert len(docs) == 1
        doc = docs[0]
        assert doc["id"] == ref.id
        assert doc["version"] == ref.version
        assert doc["content"]["kind"] == "document_snapshot"
        assert doc["content"]["document_id"] == "CAND-1"
        assert doc["content"]["state"] == "imported"
        assert doc["title"] == "Synthetic candidate"

    def test_passages_link_to_the_document_by_span(self, world: Path):
        ref = import_document(world, CANDIDATE)
        snap = build_snapshot(world)
        passages = _by_type(snap)["passage"]
        assert {p["content"]["section_id"] for p in passages} == {"S1", "S2", "S3"}
        links = [
            e for e in snap.edges
            if e["predicate"] == "expressed_in" and e["target"]["id"] == ref.id
        ]
        assert len(links) == 3
        spans = []
        for e in links:
            assert e["target"]["version"] == ref.version
            assert set(e["span"]) == {"start", "end"}
            assert e["span"]["start"] < e["span"]["end"]
            spans.append((e["span"]["start"], e["span"]["end"]))
        spans.sort()
        # Spans tile the rendered document without overlap.
        for (_, end_a), (start_b, _) in zip(spans, spans[1:]):
            assert end_a <= start_b
        # A span recovers its passage from the rendered text.
        text = _node(snap, ref.id)["content"]["text"]
        s2 = next(p for p in passages if p["content"]["section_id"] == "S2")
        span = s2["content"]["span"]
        assert "Task three is led by Participant B" in text[span["start"]:span["end"]]

    def test_passages_address_the_records_the_section_names(self, world: Path):
        import_document(world, CANDIDATE)
        snap = build_snapshot(world)
        s2 = next(n for n in snap.nodes if n["type"] == "passage" and n["content"]["section_id"] == "S2")
        triples = {(e["source"]["id"], e["predicate"], e["target"]["id"]) for e in snap.edges}
        assert (s2["id"], "addresses", "T03") in triples

    def test_importing_twice_yields_the_same_version(self, world: Path):
        first = import_document(world, CANDIDATE)
        store_before = sorted(p.name for p in (world / DOCUMENTS_REL).rglob("*.json"))
        second = import_document(world, CANDIDATE)
        assert first == second
        assert sorted(p.name for p in (world / DOCUMENTS_REL).rglob("*.json")) == store_before
        assert len(_by_type(build_snapshot(world))["artifact_version"]) == 1

    def test_a_changed_candidate_yields_a_new_version_and_keeps_the_old(self, world: Path):
        first = import_document(world, CANDIDATE)
        cand = _load(world, CANDIDATE)
        cand["sections"][1]["content"] = "Task three is led by Participant C with Participant B contributing."
        _dump(world, CANDIDATE, cand)
        second = import_document(world, CANDIDATE)
        assert second.id != first.id and second.version != first.version
        snap = build_snapshot(world)
        docs = {n["id"]: n for n in _by_type(snap)["artifact_version"]}
        assert set(docs) == {first.id, second.id}
        assert docs[first.id]["version"] == first.version
        assert "Participant B with Participant C" in docs[first.id]["content"]["text"]
        # Each version keeps its own passages.
        assert len(_by_type(snap)["passage"]) == 6

    def test_import_with_another_state_of_the_same_content_is_refused(self, world: Path):
        import_document(world, CANDIDATE, state="draft")
        with pytest.raises(DevGraphError) as ei:
            import_document(world, CANDIDATE, state="submitted")
        assert ei.value.kind == "immutable_record"
        assert "draft" in str(ei.value)

    @pytest.mark.parametrize("state", ["", "final", "Imported"])
    def test_unknown_lifecycle_state_is_refused(self, world: Path, state: str):
        with pytest.raises(DevGraphError) as ei:
            import_document(world, CANDIDATE, state=state)
        assert ei.value.kind == "malformed_record"

    def test_missing_candidate_is_refused_naming_the_path(self, world: Path):
        with pytest.raises(DevGraphError) as ei:
            import_document(world, Path("docs/nowhere.json"))
        assert "docs/nowhere.json" in ei.value.offender

    def test_candidate_without_a_document_id_is_refused(self, world: Path):
        cand = _load(world, CANDIDATE)
        del cand["document_id"]
        _dump(world, CANDIDATE, cand)
        with pytest.raises(DevGraphError) as ei:
            import_document(world, CANDIDATE)
        assert ei.value.kind == "malformed_record"

    def test_snapshot_lists_the_document_record_it_read(self, world: Path):
        import_document(world, CANDIDATE)
        snap = build_snapshot(world)
        assert any(p.startswith(DOCUMENTS_REL) for p in snap.inputs)
        assert SOURCES.as_posix() in snap.inputs


# --------------------------------------------------------------------------- #
# Claim evidence fields
# --------------------------------------------------------------------------- #


class TestClaimFields:
    def _claims(self, world: Path) -> dict[str, dict]:
        import_document(world, CANDIDATE)
        snap = build_snapshot(world)
        return {n["content"]["claim_id"]: n for n in _by_type(snap)["claim"]}

    def test_every_claim_carries_the_three_fields_separately(self, world: Path):
        for claim in self._claims(world).values():
            c = claim["content"]
            assert set(c) >= {"declared_status", "verified_span", "approval"}
            assert c["declared_status"] in DECLARED_STATUSES
            assert c["approval"] in APPROVALS

    def test_declared_status_comes_from_the_evidence_strength_lookup_only(self, world: Path):
        claims = self._claims(world)
        for claim in claims.values():
            c = claim["content"]
            assert c["declared_status"] == EVIDENCE_TO_STATUS[c["evidence_strength"]]
        assert claims["CL-1"]["content"]["declared_status"] == "Confirmed"
        assert claims["CL-3"]["content"]["declared_status"] == "Inferred"
        assert claims["CL-4"]["content"]["declared_status"] == "Unresolved"

    def test_confirmed_with_no_verified_span_is_representable(self, world: Path):
        cl2 = self._claims(world)["CL-2"]["content"]
        assert cl2["declared_status"] == "Confirmed"
        assert cl2["verified_span"] is None
        assert cl2["approval"] == "pending"

    def test_verified_span_carries_id_version_and_offsets(self, world: Path):
        import_document(world, CANDIDATE)
        snap = build_snapshot(world)
        cl1 = next(n for n in snap.nodes if n["type"] == "claim" and n["content"]["claim_id"] == "CL-1")
        span = cl1["content"]["verified_span"]
        src1 = _node(snap, "SRC-1")
        assert span["source"] == {"id": "SRC-1", "version": src1["version"]}
        assert (span["start"], span["end"]) == (0, 60)
        assert span["id"].startswith("SRC-1")
        span_node = _node(snap, span["id"])
        assert span_node["type"] == "source_span"
        assert span_node["version"] == span["version"]
        triples = {(e["source"]["id"], e["predicate"], e["target"]["id"]) for e in snap.edges}
        assert (cl1["id"], "supported_by", span["id"]) in triples
        assert src1["content"]["text"][0:60].endswith("requires.")

    def test_approval_and_span_do_not_move_with_the_lookup(self, world: Path):
        cand = _load(world, CANDIDATE)
        # A span and an approval on an unconfirmed claim stay exactly as declared.
        cand["claims"][3]["verified_span"] = {"source_id": "SRC-2", "start": 0, "end": 13}
        cand["claims"][3]["approval"] = "approved"
        _dump(world, CANDIDATE, cand)
        cl4 = self._claims(world)["CL-4"]["content"]
        assert cl4["declared_status"] == "Unresolved"
        assert cl4["approval"] == "approved"
        assert cl4["verified_span"]["source"]["id"] == "SRC-2"

    def test_assumed_is_declared_only_over_an_unresolved_lookup(self, world: Path):
        cand = _load(world, CANDIDATE)
        cand["claims"][3]["declared_status"] = "Assumed"
        _dump(world, CANDIDATE, cand)
        assert self._claims(world)["CL-4"]["content"]["declared_status"] == "Assumed"
        cand["claims"][0]["declared_status"] = "Assumed"  # lookup says Confirmed
        _dump(world, CANDIDATE, cand)
        with pytest.raises(DevGraphError) as ei:
            import_document(world, CANDIDATE)
        assert ei.value.kind == "malformed_record" and "CL-1" in str(ei.value)

    def test_claims_are_expressed_in_their_passage(self, world: Path):
        import_document(world, CANDIDATE)
        snap = build_snapshot(world)
        cl1 = next(n for n in snap.nodes if n["type"] == "claim" and n["content"]["claim_id"] == "CL-1")
        s2 = next(n for n in snap.nodes if n["type"] == "passage" and n["content"]["section_id"] == "S2")
        triples = {(e["source"]["id"], e["predicate"], e["target"]["id"]) for e in snap.edges}
        assert (cl1["id"], "expressed_in", s2["id"]) in triples

    @pytest.mark.parametrize(
        "mutation, needle",
        [
            ({"approval": "maybe"}, "approval"),
            ({"evidence_strength": "strong"}, "evidence_strength"),
            ({"verified_span": {"source_id": "SRC-9", "start": 0, "end": 5}}, "SRC-9"),
            ({"verified_span": {"source_id": "SRC-1", "start": 50, "end": 500}}, "offset"),
            ({"section_id": "S9"}, "S9"),
        ],
    )
    def test_malformed_claim_fields_are_refused_naming_the_claim(self, world: Path, mutation, needle):
        cand = _load(world, CANDIDATE)
        cand["claims"][0].update(mutation)
        _dump(world, CANDIDATE, cand)
        with pytest.raises(DevGraphError) as ei:
            import_document(world, CANDIDATE)
            build_snapshot(world)
        assert "CL-1" in str(ei.value)
        assert needle in str(ei.value)

    def test_a_declared_source_version_must_match_the_source_record(self, world: Path):
        cand = _load(world, CANDIDATE)
        cand["claims"][0]["verified_span"]["version"] = "sha256:stale"
        _dump(world, CANDIDATE, cand)
        import_document(world, CANDIDATE)
        with pytest.raises(DevGraphError) as ei:
            build_snapshot(world)
        assert ei.value.kind == "malformed_record" and "CL-1" in str(ei.value)


# --------------------------------------------------------------------------- #
# Current commitments
# --------------------------------------------------------------------------- #


class TestCurrentCommitments:
    def test_an_imported_candidate_yields_a_current_commitment(self, world: Path):
        import_document(world, CANDIDATE)
        snap = build_snapshot(world)
        current = current_commitments(snap)
        assert [c["content"]["commitment_id"] for c in current] == ["CM-1"]
        assert current[0]["type"] == "commitment"

    @pytest.mark.parametrize("state", ["submitted", "superseded"])
    def test_a_historical_document_is_never_a_current_commitment(self, world: Path, state: str):
        import_document(world, CANDIDATE, state=state)
        snap = build_snapshot(world)
        assert _by_type(snap)["commitment"], "the commitment is still indexed"
        assert current_commitments(snap) == []

    def test_current_and_submitted_versions_coexist(self, world: Path):
        import_document(world, CANDIDATE, state="submitted")
        cand = _load(world, CANDIDATE)
        cand["commitments"][0]["commitment_id"] = "CM-2"
        _dump(world, CANDIDATE, cand)
        import_document(world, CANDIDATE, state="draft")
        current = current_commitments(build_snapshot(world))
        assert [c["content"]["commitment_id"] for c in current] == ["CM-2"]


# --------------------------------------------------------------------------- #
# Stability of the previous ticket's guarantees on the extended fixture
# --------------------------------------------------------------------------- #


class TestExtendedFixtureStability:
    def test_two_imports_and_builds_are_byte_identical(self, tmp_path: Path):
        a = tmp_path / "a"
        b = tmp_path / "b"
        shutil.copytree(FIXTURE, a)
        shutil.copytree(FIXTURE, b)
        import_document(a, CANDIDATE)
        import_document(b, CANDIDATE)
        sa, sb = build_snapshot(a), build_snapshot(b)
        assert sa.to_json_bytes() == sb.to_json_bytes()
        assert sa.snapshot_id == sb.snapshot_id
        assert "timestamp" not in sa.to_json_bytes().decode("utf-8")

    def test_document_record_carries_no_wall_clock_field(self, world: Path):
        ref = import_document(world, CANDIDATE)
        text = (world / ref.path).read_text(encoding="utf-8")
        for key in ("imported_at", "created_at", "timestamp"):
            assert key not in text

    def test_dangling_edge_from_a_passage_names_the_edge(self, world: Path):
        cand = _load(world, CANDIDATE)
        cand["sections"][1]["addresses"] = ["T99"]
        _dump(world, CANDIDATE, cand)
        import_document(world, CANDIDATE)
        with pytest.raises(DevGraphError) as ei:
            build_snapshot(world)
        assert ei.value.kind == "dangling_edge" and "T99" in ei.value.offender

    def test_passage_addressing_a_participant_is_an_endpoint_type_error(self, world: Path):
        cand = _load(world, CANDIDATE)
        cand["sections"][1]["addresses"] = ["P-B"]
        _dump(world, CANDIDATE, cand)
        import_document(world, CANDIDATE)
        with pytest.raises(DevGraphError) as ei:
            build_snapshot(world)
        assert ei.value.kind == "endpoint_type" and "P-B" in ei.value.offender

    def test_tier3_change_still_changes_the_snapshot_id(self, world: Path):
        import_document(world, CANDIDATE)
        before = build_snapshot(world).snapshot_id
        seed = _load(world, WP_SEED)
        seed["work_packages"][0]["tasks"][2]["responsible_partner"] = "P-C"
        _dump(world, WP_SEED, seed)
        assert build_snapshot(world).snapshot_id != before

    def test_writer_replay_is_byte_equal_with_documents(self, world: Path):
        import_document(world, CANDIDATE)
        rec = invoke_component("dev_graph_snapshot_writer", "run-1", world)
        assert rec.status == "success", rec.failure_reason
        first = (world / SNAPSHOT_REL).read_bytes()
        write_snapshot(world)
        assert (world / SNAPSHOT_REL).read_bytes() == first
        assert b'"document_snapshot"' in first


# --------------------------------------------------------------------------- #
# Schema v2 (spec decision 17): a source_grounded claim must carry a span
# --------------------------------------------------------------------------- #


class TestSchemaV2:
    """``orch.dev_graph.document_snapshot.v2`` requires a ``verified_span`` on
    every ``source_grounded`` claim. v1 is grandfathered: the fixture's CL-2
    (source_grounded, no span) still imports under v1 and is refused under v2.
    """

    def test_schema_ids_are_closed_and_v1_is_the_default(self):
        from runner.dev_graph.documents import (
            DOCUMENT_SCHEMA_ID,
            DOCUMENT_SCHEMA_ID_V2,
            DOCUMENT_SCHEMA_IDS,
        )

        assert DOCUMENT_SCHEMA_ID == "orch.dev_graph.document_snapshot.v1"
        assert DOCUMENT_SCHEMA_ID_V2 == "orch.dev_graph.document_snapshot.v2"
        assert DOCUMENT_SCHEMA_IDS == frozenset({DOCUMENT_SCHEMA_ID, DOCUMENT_SCHEMA_ID_V2})

    def test_v2_refuses_a_source_grounded_claim_without_a_span_naming_it(self, world: Path):
        from runner.dev_graph.documents import DOCUMENT_SCHEMA_ID_V2

        with pytest.raises(DevGraphError) as exc:
            import_document(world, CANDIDATE, schema_id=DOCUMENT_SCHEMA_ID_V2)
        assert exc.value.kind == "malformed_record"
        assert "CL-2" in str(exc.value)
        assert "verified_span" in str(exc.value)
        assert not (world / DOCUMENTS_REL).exists()

    def test_v1_still_imports_the_same_candidate(self, world: Path):
        ref = import_document(world, CANDIDATE)
        rec = _load(world, Path(ref.path))
        assert rec["schema_id"] == "orch.dev_graph.document_snapshot.v1"

    def test_v2_record_carries_the_v2_schema_id_and_builds(self, world: Path):
        from runner.dev_graph.documents import DOCUMENT_SCHEMA_ID_V2

        cand = _load(world, CANDIDATE)
        cand["claims"][1]["verified_span"] = {"source_id": "SRC-2", "start": 0, "end": 13}
        _dump(world, CANDIDATE, cand)
        ref = import_document(world, CANDIDATE, schema_id=DOCUMENT_SCHEMA_ID_V2)
        rec = _load(world, Path(ref.path))
        assert rec["schema_id"] == DOCUMENT_SCHEMA_ID_V2
        snap = build_snapshot(world)
        docs = [n for n in snap.nodes if n["type"] == "artifact_version"]
        assert [d["id"] for d in docs] == [ref.id]

    def test_the_builder_re_checks_a_v2_record_on_disk(self, world: Path):
        """A v2 record whose span was dropped by hand is refused at build time,
        so the rule cannot be bypassed by editing the record."""
        from runner.dev_graph.documents import DOCUMENT_SCHEMA_ID_V2

        cand = _load(world, CANDIDATE)
        cand["claims"][1]["verified_span"] = {"source_id": "SRC-2", "start": 0, "end": 13}
        _dump(world, CANDIDATE, cand)
        ref = import_document(world, CANDIDATE, schema_id=DOCUMENT_SCHEMA_ID_V2)
        rec = _load(world, Path(ref.path))
        rec["claims"][1]["verified_span"] = None
        _dump(world, Path(ref.path), rec)
        with pytest.raises(DevGraphError) as exc:
            build_snapshot(world)
        assert exc.value.kind == "malformed_record"

    def test_an_unknown_schema_id_is_refused(self, world: Path):
        with pytest.raises(DevGraphError) as exc:
            import_document(world, CANDIDATE, schema_id="orch.dev_graph.document_snapshot.v9")
        assert exc.value.kind == "malformed_record"

    def test_import_candidate_from_a_dict_lands_the_same_record_as_the_file(self, tmp_path: Path):
        from runner.dev_graph.documents import import_candidate

        a = tmp_path / "a"
        b = tmp_path / "b"
        shutil.copytree(FIXTURE, a)
        shutil.copytree(FIXTURE, b)
        raw = _load(a, CANDIDATE)
        ref_file = import_document(a, CANDIDATE)
        ref_dict = import_candidate(b, raw, where="in-memory candidate")
        assert ref_dict == ref_file
        assert (a / ref_file.path).read_bytes() == (b / ref_dict.path).read_bytes()

    def test_render_record_is_the_bytes_import_writes_without_writing(self, world: Path):
        from runner.atomic_write import canonical_json_bytes
        from runner.dev_graph.documents import render_record

        raw = _load(world, CANDIDATE)
        record, rel = render_record(raw, where="x")
        assert not (world / rel).exists()
        ref = import_document(world, CANDIDATE)
        assert rel == ref.path
        assert (world / ref.path).read_bytes() == canonical_json_bytes(record)
