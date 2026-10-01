"""The bridge from Phase 8's Tier 5 sections to a blind-lane candidate.

The demo ticket "Candidate Part B and the blind baseline" asks that Phase 8
draft Part B and that the draft be "imported as candidate version 1".  Two
halves of that existed and nothing joined them.

Phase 8 writes three section artifacts under
``docs/tier5_deliverables/proposal_sections/``.  The blind lane imports a
*candidate*: one JSON object carrying ``document_id``, ``sections``, ``claims``
and ``commitments``, which ``import_document`` turns into an immutable record.
``import_document`` is called from exactly two places in the tree, the
revisions module and the tests, and every test hand-writes its candidate.  So
no route ran from a drafted Part B to a graded one, and the ticket's criteria 2
to 4 would have failed after a full Phase 8 dispatch for want of a converter.

These tests drive ``tools/build_part_b_candidate.py``.  The anchor chain is the
point: the Tier 2A ``section_schema_registry`` declares ``B.1.1`` to ``B.3.2``,
the Phase 8 drafting skills take ``sub_section_id`` from that registry, and the
RIA rubrics anchor on six of those seven.  A converter that drops or renames a
sub-section id breaks the chain silently, so the end-to-end test grades a built
candidate under the real RIA profile rather than a synthetic one.

Nothing here touches ``docs/``.  Each test builds Phase 8-shaped artifacts in a
copy of the synthetic dev-graph fixture, because a real import would move the
pinned demo snapshot id.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import harness.blind_assessment as ba
from harness.evidence_pack import EvidencePackError
from harness.judge import Judge, JudgeConfig
from harness.provenance import ProvenanceLog
from harness.rubrics import load_profile_bundle
from runner.dev_graph import import_document
from runner.dev_graph.documents import normalise_candidate
from runner.dev_graph.schema import DevGraphError

from tools.build_part_b_candidate import (
    CANDIDATES_REL,
    CLAIM_APPROVAL,
    EVIDENCE_STRENGTH_BY_STATUS,
    SECTION_SPECS,
    BuilderError,
    build_candidate,
    main,
    output_path,
    write_candidate,
)

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "dev_graph_synthetic"
RIA_PROFILE_REL = "harness/profiles/ria_default.json"

SECTIONS_REL = "docs/tier5_deliverables/proposal_sections"
DOCUMENT_ID = "DEMO-BIODIV-2027_part_b"
RUN_ID = "demo-run-candidate"

SUB_TEXT = "Objective one is met by Task three, which Participant B leads."

FROZEN = "2026-10-01T00:00:00+00:00"
PASS_JSON = '{"passed": true, "score": 0.9, "rationale": "scripted pass"}'


def _judge(tmp_path: Path) -> Judge:
    """A scripted assessor. The grade is not under test; the anchors are."""
    return Judge(
        JudgeConfig(model="fake-assessor", version="pin-part-b-builder"),
        backend=lambda messages: {"content": PASS_JSON},
        provenance_log=ProvenanceLog(tmp_path / "provenance.jsonl"),
        clock=lambda: FROZEN,
    )


@pytest.fixture
def world(tmp_path: Path) -> Path:
    """A copy of the synthetic dev-graph fixture. Never ``docs/``."""
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    return root


@pytest.fixture(scope="module")
def ria_bundle():
    return load_profile_bundle(RIA_PROFILE_REL, repo_root=REPO)


REGISTRY_REL = "docs/tier2a_instrument_schemas/extracted/section_schema_registry.json"


def _anchors_by_section(bundle) -> dict[str, list[str]]:
    """Profile section id -> the anchor sub-section ids its rubrics declare.

    Grouped through the profile's own criterion-to-section map rather than
    guessed from the shape of an id.
    """
    by_criterion: dict[str, list[str]] = {}
    for rubric in bundle.rubric_set.rubrics:
        by_criterion.setdefault(rubric.criterion_id, []).extend(
            rubric.anchor_sub_section_ids
        )
    return {
        section_id: sorted(set(by_criterion.get(criterion, ())))
        for criterion, section_id in ba.required_sections(bundle.profile)
    }


def _registry_sub_sections(bundle) -> dict[str, list[str]]:
    """Profile section id -> every RIA sub-section the Tier 2A registry declares.

    This is the shape Phase 8 actually drafts, and it is wider than the anchor
    set: the registry declares seven ``B.n.m`` sub-sections and the rubrics
    anchor on six, leaving ``B.2.3`` unanchored.

    Building a fixture from the anchors instead would make the anchor test
    true by construction, which is what a review caught it being. So the
    *set* comes from the registry and only the *prefix* comes from the
    profile's anchors — no hand-written criterion-number mapping either.
    """
    registry = json.loads((REPO / REGISTRY_REL).read_text(encoding="utf-8-sig"))
    declared = [
        str(s["section_id"])
        for inst in registry["instruments"]
        for s in inst.get("sections", [])
        if isinstance(s, dict) and "section_id" in s
    ]
    out: dict[str, list[str]] = {}
    for section_id, anchors in _anchors_by_section(bundle).items():
        assert anchors, f"{section_id} declares no anchor; the derivation needs one"
        prefix = anchors[0].rsplit(".", 1)[0] + "."
        ids = sorted(d for d in declared if d.startswith(prefix))
        assert ids, f"the registry declares no sub-section under {prefix!r}"
        out[section_id] = ids
    return out


#: Required fields each section's schema declares beyond the common set, so a
#: fixture artifact is schema-complete. The builder carries none of them: they
#: are id lists and refs with no text, not document content. They live here
#: rather than on ``SectionSpec`` because only the fixtures need them.
EXTRA_REQUIRED_BY_SECTION: dict[str, dict] = {
    "excellence_section": {},
    "impact_section": {"impact_pathway_refs": [], "dec_coverage": {}},
    "implementation_section": {
        "wp_table_refs": [],
        "gantt_ref": "",
        "milestone_refs": [],
        "risk_register_ref": "",
    },
}


def _artifact(spec, anchor_ids: list[str], *, claims: list[dict] | None = None) -> dict:
    """One Phase 8 section artifact, in the shape its schema declares."""
    artifact: dict = {
        "schema_id": spec.schema_id,
        "run_id": RUN_ID,
        "criterion": spec.criterion,
        "sub_sections": [
            {
                "sub_section_id": anchor_id,
                "title": f"Answer to {anchor_id}",
                "content": SUB_TEXT,
                "word_count": len(SUB_TEXT.split()),
            }
            for anchor_id in anchor_ids
        ],
        "validation_status": {
            "overall_status": "confirmed",
            "claim_statuses": claims if claims is not None else [],
        },
        "traceability_footer": {
            "primary_sources": [{"tier": 3, "source_path": "docs/tier3_x/y.json"}]
        },
    }
    for extra, value in EXTRA_REQUIRED_BY_SECTION[spec.section_id].items():
        artifact[extra] = value
    return artifact


def _write_phase_8(
    world: Path,
    bundle,
    *,
    drop_anchor: str = "",
    omit_section: str = "",
    mutate=None,
) -> None:
    """Write the three Phase 8 section artifacts into *world*.

    Sub-sections come from the Tier 2A registry, not from the profile's
    anchors, so the fixture is the shape Phase 8 drafts and the anchor test
    is not satisfied by its own fixture.
    """
    declared = _registry_sub_sections(bundle)
    base = world / SECTIONS_REL
    base.mkdir(parents=True, exist_ok=True)
    for spec in SECTION_SPECS:
        if spec.section_id == omit_section:
            continue
        ids = [a for a in declared[spec.section_id] if a != drop_anchor]
        artifact = _artifact(spec, ids)
        if mutate is not None:
            mutate(spec, artifact)
        (base / f"{spec.section_id}.json").write_text(
            json.dumps(artifact, indent=2), encoding="utf-8"
        )


def _build(world: Path, bundle, **kwargs) -> dict:
    _write_phase_8(world, bundle, **kwargs)
    return build_candidate(world, document_id=DOCUMENT_ID)


# ---------------------------------------------------------------------------
# 1. It bridges the two halves at all
# ---------------------------------------------------------------------------


class TestItBridgesPhase8ToTheBlindLane:
    def test_it_builds_one_section_per_phase_8_artifact(self, world, ria_bundle):
        candidate = _build(world, ria_bundle)
        assert [s["section_id"] for s in candidate["sections"]] == [
            spec.section_id for spec in SECTION_SPECS
        ]

    def test_section_ids_are_the_ones_the_profile_names(self, world, ria_bundle):
        """The profile maps each criterion to a section id; these must be those."""
        candidate = _build(world, ria_bundle)
        named = {section_id for _c, section_id in ba.required_sections(ria_bundle.profile)}
        assert {s["section_id"] for s in candidate["sections"]} == named

    def test_sub_sections_are_carried_verbatim(self, world, ria_bundle):
        """Copied, never re-titled or renumbered: the anchor is an exact match."""
        candidate = _build(world, ria_bundle)
        declared = _registry_sub_sections(ria_bundle)
        for section in candidate["sections"]:
            got = [s["sub_section_id"] for s in section["sub_sections"]]
            assert got == declared[section["section_id"]]
            for sub in section["sub_sections"]:
                assert sub["content"] == SUB_TEXT
                assert sub["title"] == f"Answer to {sub['sub_section_id']}"

    def test_the_candidate_passes_the_real_normaliser(self, world, ria_bundle):
        """Not a shape of this tool's own invention: the importer's validator."""
        candidate = _build(world, ria_bundle)
        assert normalise_candidate(candidate, "built") == candidate

    def test_the_title_comes_from_the_artifacts_own_criterion(self, world, ria_bundle):
        candidate = _build(world, ria_bundle)
        by_id = {s["section_id"]: s for s in candidate["sections"]}
        for spec in SECTION_SPECS:
            assert by_id[spec.section_id]["title"] == spec.criterion

    def test_it_addresses_nothing(self, world, ria_bundle):
        """``addresses`` stays empty on purpose.

        The *snapshot* builder checks that an addressed id exists as a node.
        A Tier 5 section's own references are work package and milestone ids,
        whose presence as graph nodes is not guaranteed, so addressing them
        would make the snapshot fail on a document that is otherwise sound.
        """
        candidate = _build(world, ria_bundle)
        assert all(s["addresses"] == [] for s in candidate["sections"])

    def test_the_schema_ids_are_the_ones_phase_8_writes(self):
        """Read from ``PRESEED_NODE_CONFIG`` rather than restated here.

        That module binds each Phase 8 node to its target path and schema id,
        and asserts at import time that its own copies do not drift. A third
        copy in the builder would be free to drift from both.
        """
        from runner.phase8_preseed import PRESEED_NODE_CONFIG

        owned = {
            Path(cfg["target_path"]).stem: cfg["schema_id"]
            for cfg in PRESEED_NODE_CONFIG.values()
        }
        for spec in SECTION_SPECS:
            assert owned[spec.section_id] == spec.schema_id


# ---------------------------------------------------------------------------
# 2. The anchor chain closes, which is the whole point
# ---------------------------------------------------------------------------


class TestTheAnchorChainCloses:
    def test_every_ria_rubric_anchor_is_a_sub_section(self, world, ria_bundle):
        """The registry's ids cover the profile's anchors, through the builder.

        The fixture is built from the Tier 2A registry and the anchors come
        from the profile, so the two sets have independent origins. An earlier
        version built the fixture from the anchors themselves and was true by
        construction; a review caught it.
        """
        candidate = _build(world, ria_bundle)
        present = {
            sub["sub_section_id"]
            for section in candidate["sections"]
            for sub in section["sub_sections"]
        }
        anchors = {
            anchor
            for rubric in ria_bundle.rubric_set.rubrics
            for anchor in rubric.anchor_sub_section_ids
        }
        assert anchors, "the RIA profile declares no anchors; the test proves nothing"
        assert anchors <= present, sorted(anchors - present)

    def test_the_candidate_is_wider_than_the_anchor_set(self, world, ria_bundle):
        """Phase 8 drafts seven RIA sub-sections and six are anchored.

        If these sets were equal the test above would prove nothing, because
        the fixture would be the anchor list under another name. B.2.3 is the
        unanchored one, and it must survive into the candidate: it is Part B
        content whether or not a rubric ranks it.
        """
        candidate = _build(world, ria_bundle)
        present = {
            sub["sub_section_id"]
            for section in candidate["sections"]
            for sub in section["sub_sections"]
        }
        anchors = {
            anchor
            for rubric in ria_bundle.rubric_set.rubrics
            for anchor in rubric.anchor_sub_section_ids
        }
        assert present - anchors, (
            "every drafted sub-section is an anchor, so the fixture is the "
            "anchor list and the chain is untested"
        )

    def _grade(self, world, bundle, tmp_path, **kwargs):
        """Phase 8 artifacts in, a blind report out. The route under test.

        The anchor map is read on the ``assess_candidate`` path, not when the
        package is built, so a test that stopped at ``build_blind_evidence``
        would pass with every anchor missing.
        """
        _write_phase_8(world, bundle, **kwargs)
        rel = write_candidate(world, document_id=DOCUMENT_ID)
        import_document(world, rel)
        evidence = ba.build_blind_evidence(
            world,
            DOCUMENT_ID,
            profile_version=bundle.version,
            out_dir=tmp_path / "out",
        )
        return ba.assess_candidate(
            _judge(tmp_path), bundle, evidence=evidence, clock=lambda: FROZEN
        )

    def test_a_built_candidate_grades_under_the_real_ria_profile(
        self, world, ria_bundle, tmp_path
    ):
        """End to end: this is the step that did not exist.

        Criterion 2's import and criterion 3's grading, on a Part B shape built
        from Phase 8's own artifacts rather than on a hand-written fixture.
        """
        report = self._grade(world, ria_bundle, tmp_path)
        assert report.scope in {"complete", "partial"}

    def test_the_report_carries_the_three_pins(self, world, ria_bundle, tmp_path):
        """Criterion 3 names exactly these: candidate hash, profile version,
        assessor pin."""
        report = self._grade(world, ria_bundle, tmp_path)
        assert report.candidate_hash.startswith("sha256:")
        assert report.profile_version == ria_bundle.version
        assert report.assessor_pin
        for cell in report.cells:
            assert cell.candidate_hash == report.candidate_hash
            assert cell.profile_version == report.profile_version
            assert cell.assessor_pin == report.assessor_pin

    def test_a_dropped_anchor_still_fails_closed(self, world, ria_bundle, tmp_path):
        """The converter must not rescue a Part B that omits a declared anchor.

        Ticket B's fix kept the anchor map fail-closed, and a bridge that
        quietly synthesised the missing sub-section would undo that.
        """
        anchors = _anchors_by_section(ria_bundle)
        victim = anchors["excellence_section"][0]
        with pytest.raises(EvidencePackError) as exc:
            self._grade(world, ria_bundle, tmp_path, drop_anchor=victim)
        assert victim in str(exc.value)


# ---------------------------------------------------------------------------
# 3. Fail closed rather than build half a document
# ---------------------------------------------------------------------------


class TestItFailsClosedRatherThanBuildingHalfADocument:
    def test_a_missing_section_artifact_refuses(self, world, ria_bundle):
        """Two sections out of three is not a Part B.

        §12.4: a missing mandatory input is a failure, not a partial output.
        """
        with pytest.raises(BuilderError, match="impact_section"):
            _build(world, ria_bundle, omit_section="impact_section")

    def test_a_wrong_schema_id_refuses(self, world, ria_bundle):
        def wrong(spec, artifact):
            if spec.section_id == "impact_section":
                artifact["schema_id"] = "orch.tier5.something_else.v1"

        with pytest.raises(BuilderError, match="schema_id"):
            _build(world, ria_bundle, mutate=wrong)

    def test_an_invalid_artifact_status_refuses(self, world, ria_bundle):
        """A section the runner marked invalid may not become a candidate."""

        def invalid(spec, artifact):
            if spec.section_id == "excellence_section":
                artifact["artifact_status"] = "invalid"

        with pytest.raises(BuilderError, match="artifact_status"):
            _build(world, ria_bundle, mutate=invalid)

    def test_a_section_with_no_sub_sections_refuses(self, world, ria_bundle):
        def empty(spec, artifact):
            if spec.section_id == "implementation_section":
                artifact["sub_sections"] = []

        with pytest.raises(BuilderError, match="sub_sections"):
            _build(world, ria_bundle, mutate=empty)

    def test_a_criterion_disagreeing_with_the_schema_refuses(self, world, ria_bundle):
        """The section title is copied from the artifact's ``criterion``.

        Each Tier 5 section schema fixes that string, so a disagreement means
        either the wrong artifact or a drifted skill, and the candidate would
        carry the wrong heading into the blind report.
        """

        def drift(spec, artifact):
            if spec.section_id == "excellence_section":
                artifact["criterion"] = "Excellence and other virtues"

        with pytest.raises(BuilderError, match="criterion"):
            _build(world, ria_bundle, mutate=drift)

    def test_a_sub_section_missing_its_title_refuses(self, world, ria_bundle):
        def gut(spec, artifact):
            if spec.section_id == "impact_section":
                artifact["sub_sections"][0].pop("title")

        with pytest.raises(BuilderError, match="title"):
            _build(world, ria_bundle, mutate=gut)

    def test_a_sub_section_missing_its_content_refuses(self, world, ria_bundle):
        def gut(spec, artifact):
            if spec.section_id == "impact_section":
                artifact["sub_sections"][0].pop("content")

        with pytest.raises(BuilderError, match="content"):
            _build(world, ria_bundle, mutate=gut)


# ---------------------------------------------------------------------------
# 4. Claims come from the artifact, with no invention
# ---------------------------------------------------------------------------


class TestClaimsComeFromTheArtifactsOwnValidationStatus:
    """F6 recorded that the demo's blind packages held 0 claims, which makes a
    clean leakage pass vacuous. Carrying the sections' own claim statuses is
    what gives the guard something real to read."""

    def _with_claims(self, world, ria_bundle, claims):
        def add(spec, artifact):
            if spec.section_id == "excellence_section":
                artifact["validation_status"]["claim_statuses"] = claims

        return _build(world, ria_bundle, mutate=add)

    def test_claims_are_mapped_through_the_evidence_lookup(self, world, ria_bundle):
        candidate = self._with_claims(
            world,
            ria_bundle,
            [
                {
                    "claim_id": "CL-1",
                    "claim_summary": "A confirmed thing.",
                    "status": "confirmed",
                    "source_ref": "docs/tier3_x/y.json#a",
                },
                {
                    "claim_id": "CL-2",
                    "claim_summary": "An inferred thing.",
                    "status": "inferred",
                    "source_ref": "docs/tier3_x/y.json#b",
                },
            ],
        )
        claims = {c["claim_id"]: c for c in candidate["claims"]}
        assert set(claims) == {"CL-1", "CL-2"}
        assert claims["CL-1"]["evidence_strength"] == (
            EVIDENCE_STRENGTH_BY_STATUS["confirmed"]
        )
        assert claims["CL-1"]["text"] == "A confirmed thing."
        assert all(c["section_id"] == "excellence_section" for c in claims.values())
        assert all(c["approval"] == CLAIM_APPROVAL for c in claims.values())

    def test_the_graph_derives_declared_status_not_the_builder(
        self, world, ria_bundle
    ):
        """The builder maps ``status`` to ``evidence_strength`` and stops.

        ``declared_status`` comes from the graph's own ``EVIDENCE_TO_STATUS``
        lookup inside ``normalise_candidate``. Emitting it here would be a
        second copy of that lookup, free to contradict it.
        """
        candidate = self._with_claims(
            world,
            ria_bundle,
            [
                {
                    "claim_id": "CL-1",
                    "claim_summary": "A confirmed thing.",
                    "status": "confirmed",
                    "source_ref": "docs/tier3_x/y.json#a",
                },
                {
                    "claim_id": "CL-2",
                    "claim_summary": "An inferred thing.",
                    "status": "inferred",
                    "source_ref": "docs/tier3_x/y.json#b",
                },
            ],
        )
        assert all("declared_status" not in c for c in candidate["claims"])
        normalised = normalise_candidate(candidate, "built")
        derived = {c["claim_id"]: c["declared_status"] for c in normalised["claims"]}
        assert derived == {"CL-1": "Confirmed", "CL-2": "Inferred"}

    def test_no_claim_carries_a_verified_span(self, world, ria_bundle):
        """A Tier 5 ``source_ref`` is a path plus an id, never an offset range.

        Deriving a span from it would be invention, and the span is what the
        claim verifier checks against real source text.
        """
        candidate = self._with_claims(
            world,
            ria_bundle,
            [
                {
                    "claim_id": "CL-1",
                    "claim_summary": "A thing.",
                    "status": "confirmed",
                    "source_ref": "docs/tier3_x/y.json#a",
                }
            ],
        )
        assert "verified_span" not in candidate["claims"][0]
        normalised = normalise_candidate(candidate, "built")
        assert normalised["claims"][0]["verified_span"] is None

    def test_an_unknown_claim_status_refuses(self, world, ria_bundle):
        with pytest.raises(BuilderError, match="status"):
            self._with_claims(
                world,
                ria_bundle,
                [
                    {
                        "claim_id": "CL-1",
                        "claim_summary": "A thing.",
                        "status": "probably_fine",
                        "source_ref": "docs/tier3_x/y.json#a",
                    }
                ],
            )

    def test_a_claim_id_that_is_not_an_identifier_refuses(self, world, ria_bundle):
        """Refused, not sanitised. Rewriting an id would break traceability."""
        with pytest.raises(BuilderError, match="claim_id"):
            self._with_claims(
                world,
                ria_bundle,
                [
                    {
                        "claim_id": "claim one!",
                        "claim_summary": "A thing.",
                        "status": "confirmed",
                        "source_ref": "docs/tier3_x/y.json#a",
                    }
                ],
            )

    def test_a_duplicate_claim_id_across_sections_refuses(self, world, ria_bundle):
        """``normalise_candidate`` rejects a duplicate, so catch it with a
        message naming the builder rather than letting the importer raise."""

        def dupe(spec, artifact):
            artifact["validation_status"]["claim_statuses"] = [
                {
                    "claim_id": "CL-SAME",
                    "claim_summary": "A thing.",
                    "status": "confirmed",
                    "source_ref": "docs/tier3_x/y.json#a",
                }
            ]

        with pytest.raises(BuilderError, match="CL-SAME"):
            _build(world, ria_bundle, mutate=dupe)

    def test_a_carried_claim_reaches_the_grader_without_a_source_ref(
        self, world, ria_bundle, tmp_path
    ):
        """Recorded, not hidden: a carried claim is ungrounded to the judge.

        The Tier 5 claim shape and the graph claim shape do not meet. Tier 5
        records ``source_ref``, a path plus an id. The graph has no such field:
        ``materialise_candidate`` derives ``source_ref`` from the span node id
        that ``_add_verified_span`` mints, and that function refuses a source
        which is not already a graph node with text at the declared offsets.
        A Tier 5 ``source_ref`` supplies neither offsets nor a source node, so
        no honest span can be built from it and ``source_ref`` stays empty.

        The claims are still worth carrying: the leakage guard reads claim
        text, which is F6's point. But a reader must not mistake this for
        grounded evidence, so the gap is asserted rather than left to be
        discovered by someone trusting a score.
        """

        def add(spec, artifact):
            if spec.section_id == "excellence_section":
                artifact["validation_status"]["claim_statuses"] = [
                    {
                        "claim_id": "CL-1",
                        "claim_summary": "A thing with a recorded source.",
                        "status": "confirmed",
                        "source_ref": "docs/tier3_x/y.json#a",
                    }
                ]

        _write_phase_8(world, ria_bundle, mutate=add)
        rel = write_candidate(world, document_id=DOCUMENT_ID)
        import_document(world, rel)
        evidence = ba.build_blind_evidence(
            world,
            DOCUMENT_ID,
            profile_version=ria_bundle.version,
            out_dir=tmp_path / "out",
        )
        assert "claim" in {i["type"] for i in evidence.package.items}, (
            "the blind package holds no claim item; F6's point was that the "
            "demo's six packages held zero, which makes the guard vacuous"
        )
        ledgers = [
            entry
            for path in sorted(Path(evidence.candidate_dir).glob("*.json"))
            for entry in json.loads(path.read_text(encoding="utf-8-sig"))
            .get("validation_status", {})
            .get("claim_statuses", [])
        ]
        carried = [e for e in ledgers if e.get("claim_id") == "CL-1"]
        assert carried, "the claim did not survive into the materialised candidate"
        assert carried[0]["claim_summary"] == "A thing with a recorded source."
        assert carried[0]["status"] == "confirmed"
        assert carried[0]["source_ref"] == "", (
            "a source_ref now survives the round trip; if the Tier 5 claim "
            "shape gained a span, revisit D9 and this limitation"
        )

    def test_commitments_are_empty_and_that_is_declared(self, world, ria_bundle):
        """No Tier 5 field carries a commitment in the shape the graph wants.

        ``milestone_refs`` and ``wp_table_refs`` are id lists with no text, so
        turning them into commitments would invent the commitment's content.
        F6 stays open on commitments; the claims above close its claim half.
        """
        candidate = _build(world, ria_bundle)
        assert candidate["commitments"] == []


# ---------------------------------------------------------------------------
# 5. Deterministic, per §6.4
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_two_builds_are_byte_equal(self, world, ria_bundle):
        _write_phase_8(world, ria_bundle)
        first = build_candidate(world, document_id=DOCUMENT_ID)
        second = build_candidate(world, document_id=DOCUMENT_ID)
        assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)

    def test_it_writes_no_wall_clock_of_its_own(self, world, ria_bundle):
        candidate = _build(world, ria_bundle)
        blob = json.dumps(candidate)
        for forbidden in ("built_at", "generated_at", "derived_at", "timestamp"):
            assert forbidden not in blob

    def test_the_run_id_is_not_carried_into_the_candidate(self, world, ria_bundle):
        """A candidate is content addressed. Carrying the run id would move its
        ``content_version`` on every rerun and make each one a new version."""
        candidate = _build(world, ria_bundle)
        assert RUN_ID not in json.dumps(candidate)

    def test_a_rebuild_imports_as_the_same_record(self, world, ria_bundle):
        """Same bytes in, same ``content_version`` out, so a rerun is not a
        re-import. ``import_document`` refuses a state change, not a repeat."""
        _write_phase_8(world, ria_bundle)
        rel = write_candidate(world, document_id=DOCUMENT_ID)
        first = import_document(world, rel)
        rel_again = write_candidate(world, document_id=DOCUMENT_ID)
        second = import_document(world, rel_again)
        assert first.id == second.id
        assert first.version == second.version


# ---------------------------------------------------------------------------
# 6. Where it writes
# ---------------------------------------------------------------------------


class TestWhereItWrites:
    def test_it_writes_under_the_established_candidates_directory(
        self, world, ria_bundle
    ):
        _write_phase_8(world, ria_bundle)
        rel = write_candidate(world, document_id=DOCUMENT_ID)
        assert Path(rel).as_posix().startswith(CANDIDATES_REL)
        assert (world / rel).is_file()

    def test_the_path_is_named_for_the_document(self, world):
        assert output_path(world, "SOME_DOC").name == "SOME_DOC.json"

    def test_it_writes_nothing_outside_the_candidate_file(self, world, ria_bundle):
        """No Tier 4 record, no gate result, no snapshot. One file."""
        _write_phase_8(world, ria_bundle)
        before = {p for p in (world / "docs").rglob("*") if p.is_file()}
        rel = write_candidate(world, document_id=DOCUMENT_ID)
        after = {p for p in (world / "docs").rglob("*") if p.is_file()}
        assert after - before == {world / rel}


class TestTheCommandLineIsTheSamePathTheTestsDrive:
    """The review caught ``main`` serialising its own copy instead of calling
    ``write_candidate``, so the shipped write path was not the tested one.
    These pin the two together and pin the exit-code contract."""

    def _argv(self, world: Path) -> list[str]:
        return ["--repo-root", str(world), "--document-id", DOCUMENT_ID]

    def test_the_cli_writes_what_write_candidate_writes(self, world, ria_bundle):
        _write_phase_8(world, ria_bundle)
        assert main(self._argv(world)) == 0
        from_cli = output_path(world, DOCUMENT_ID).read_bytes()
        output_path(world, DOCUMENT_ID).unlink()
        write_candidate(world, document_id=DOCUMENT_ID)
        assert output_path(world, DOCUMENT_ID).read_bytes() == from_cli

    def test_a_refusal_exits_2_and_a_check_diff_exits_1(self, world, ria_bundle):
        """Distinguishable, per ``tools/derive_run_phase_costs.py``.

        A structural refusal and a drifted artifact are different events, and
        a caller that cannot tell them apart will treat a missing Phase 8 as
        a stale file.
        """
        assert main(self._argv(world) + ["--check"]) == 2, (
            "no Phase 8 output at all must be a refusal, not drift"
        )
        _write_phase_8(world, ria_bundle)
        assert main(self._argv(world) + ["--check"]) == 1, (
            "nothing written yet, so --check must report drift"
        )
        assert main(self._argv(world)) == 0
        assert main(self._argv(world) + ["--check"]) == 0

    def test_check_writes_nothing(self, world, ria_bundle):
        _write_phase_8(world, ria_bundle)
        main(self._argv(world) + ["--check"])
        assert not output_path(world, DOCUMENT_ID).exists()

    def test_the_written_bytes_are_the_canonical_serialisation(
        self, world, ria_bundle
    ):
        """``--check`` compares against the serialiser that wrote the file,
        not a second copy of the dump options."""
        from runner.atomic_write import canonical_json_bytes

        _write_phase_8(world, ria_bundle)
        rel = write_candidate(world, document_id=DOCUMENT_ID)
        expected = canonical_json_bytes(
            build_candidate(world, document_id=DOCUMENT_ID)
        )
        assert (world / rel).read_bytes() == expected


class TestItRefusesToGuessTheDocumentId:
    def test_a_document_id_that_is_not_an_identifier_refuses(self, world, ria_bundle):
        _write_phase_8(world, ria_bundle)
        with pytest.raises(BuilderError, match="document_id"):
            build_candidate(world, document_id="not an id!")


class TestTheImporterStillOwnsItsOwnRules:
    def test_the_builder_does_not_import(self, world, ria_bundle):
        """Building is not importing. The tool writes a candidate and stops, so
        the operator decides when a document record is created (§9.4)."""
        _write_phase_8(world, ria_bundle)
        write_candidate(world, document_id=DOCUMENT_ID)
        records = world / "docs/tier4_orchestration_state/dev_graph/documents"
        assert not records.exists() or not list(records.rglob("*.json"))

    def test_an_unreadable_section_artifact_refuses(self, world, ria_bundle):
        _write_phase_8(world, ria_bundle)
        (world / SECTIONS_REL / "impact_section.json").write_text(
            "{not json", encoding="utf-8"
        )
        with pytest.raises(BuilderError):
            build_candidate(world, document_id=DOCUMENT_ID)

    def test_the_importer_rejects_what_the_builder_would_not_write(self):
        """A sanity check on the pairing: the validator the builder targets is
        the one the importer runs, and it does reject a bad section id."""
        with pytest.raises(DevGraphError):
            normalise_candidate(
                {
                    "document_id": "D",
                    "sections": [{"section_id": "not an id!"}],
                    "claims": [],
                    "commitments": [],
                },
                "handmade",
            )
