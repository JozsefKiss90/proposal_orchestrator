"""
Ticket B: a document section declares its sub-sections, so the blind lane can grade it.

Ticket B in ``plans/tickets_budget_and_blind_lane.md``, closing finding F1 of
``docs/tier4_orchestration_state/validation_reports/demo-candidate-blind-baseline_2026-10-01.json``.

**The defect.** ``materialise_candidate`` wrote one sub-section per passage and named it
for its section, so ``excellence_section.json`` held one sub-section called
``excellence_section``.  The RIA rubrics anchor on ``B.1.1`` to ``B.3.2`` and the MSCA-PF
rubrics on ``1.1`` to ``3.2``.  ``build_evidence_pack`` raises on the first absent anchor,
nothing on the ``assess_candidate`` path catches it, and no report was written.  The
dev-graph *document* route could therefore feed no shipped profile at all.

**The fix.** A section carries an optional ``sub_sections`` list.  The builder copies it
onto the passage node, and the materialiser emits it instead of synthesising one.  Phase 8
already drafts at this granularity under
``phase_outputs/phase8_drafting_review/section_drafts/``, so the structure is preserved
rather than invented.

Two properties matter as much as the fix:

* **Optional means hash-stable.**  A section without ``sub_sections`` normalises to exactly
  the bytes it did before, so no stored record's ``content_version`` moves and no snapshot
  id shifts.  ``TestTheOldShapeIsUntouched`` pins that.
* **The anchor map still fails closed.**  The anchor is a score bonus of 2, not a content
  requirement: its purpose is that a section's dedicated answer to an expectation outranks
  a stray term match elsewhere.  A declared anchor absent from the candidate must still
  raise, or the check becomes a vacuous pass.  ``TestTheAnchorMapStillFailsClosed`` pins
  that.

Nothing here writes into ``docs/``.  Every import runs in a copy of the synthetic fixture
under ``tmp_path``, because a real import adds an ``artifact_version`` node and would move
the demo snapshot id that three Tier 4 records cite.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import harness.blind_assessment as ba
from harness.evidence_pack import (
    ANCHOR_SCORE_BONUS,
    EXCLUDED_NOT_RELEVANT,
    EvidencePackError,
    build_evidence_pack,
)
from harness.judge import Judge, JudgeConfig
from harness.provenance import ProvenanceLog
from harness.rubrics import load_profile_bundle
from runner.dev_graph import build_snapshot, import_document, read_esr_intake
from runner.dev_graph.documents import normalise_candidate, render_document
from runner.dev_graph.schema import DevGraphError
from runner.dev_graph.identity import content_hash

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixtures" / "dev_graph_synthetic"

RIA_PROFILE_REL = "harness/profiles/ria_default.json"
MSCA_PROFILE_REL = "harness/profiles/msca_pf_default.json"

#: The demo's ESR intake, written by the blind-baseline ticket.  F2 said an intake could
#: be stamped only through the document route, which F1 made ungradeable.  Both close here.
INTAKE_ID = "demo-biodiv-2027-part-b-v1"

FROZEN = "2026-10-01T00:00:00+00:00"
PASS_JSON = '{"passed": true, "score": 0.9, "rationale": "scripted pass"}'

SECTION_TEXT = "Participant B holds the capability that Task three requires."
SUB_TEXT = "Objective one is met by Task three, which Participant B leads."


@pytest.fixture
def world(tmp_path: Path) -> Path:
    """A copy of the synthetic fixture.  Nothing here touches ``docs/``."""
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    return root


@pytest.fixture(scope="module")
def ria_bundle():
    return load_profile_bundle(RIA_PROFILE_REL, repo_root=REPO)


@pytest.fixture(scope="module")
def msca_bundle():
    return load_profile_bundle(MSCA_PROFILE_REL, repo_root=REPO)


def _anchors_by_section(bundle) -> dict[str, list[str]]:
    """Each profile section id -> the anchor sub-section ids its rubrics declare.

    The profile maps a criterion to a section, and each rubric carries that criterion's
    anchors, so the grouping is the profile's own rather than a guess from the id shape.
    """
    by_criterion: dict[str, list[str]] = {}
    for rubric in bundle.rubric_set.rubrics:
        by_criterion.setdefault(rubric.criterion_id, []).extend(
            rubric.anchor_sub_section_ids
        )
    out: dict[str, list[str]] = {}
    for criterion, section_id in ba.required_sections(bundle.profile):
        out[section_id] = sorted(set(by_criterion.get(criterion, ())))
    return out


def _document(bundle, *, document_id: str = "SUBSECTIONED_PART_B", drop: str = "") -> dict:
    """A candidate whose sections declare the profile's own anchor ids.

    *drop* omits one anchor sub-section, which is how the fail-closed test builds a
    candidate that is structurally valid and still missing a declared anchor.
    """
    anchors = _anchors_by_section(bundle)
    sections = []
    for section_id, anchor_ids in anchors.items():
        sections.append(
            {
                "section_id": section_id,
                "title": section_id,
                "content": SECTION_TEXT,
                "addresses": ["OBJ-1"],
                "sub_sections": [
                    {
                        "sub_section_id": anchor_id,
                        "title": f"Answer to {anchor_id}",
                        "content": SUB_TEXT,
                    }
                    for anchor_id in anchor_ids
                    if anchor_id != drop
                ],
            }
        )
    first = next(iter(anchors))
    return {
        "document_id": document_id,
        "title": "A document whose sections declare their sub-sections",
        "sections": sections,
        "claims": [
            {
                "claim_id": "CL-1",
                "section_id": first,
                "text": SECTION_TEXT,
                "evidence_strength": "source_grounded",
                "verified_span": {"source_id": "SRC-1", "start": 0, "end": 58},
                "approval": "approved",
            }
        ],
        "commitments": [],
    }


def _import(world: Path, payload: dict) -> str:
    rel = Path("docs/tier5_deliverables/candidates/subsectioned.json")
    target = world / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    import_document(world, rel)
    return payload["document_id"]


def _evidence(world: Path, bundle, out_dir: Path, *, drop: str = ""):
    document = _import(world, _document(bundle, drop=drop))
    return ba.build_blind_evidence(
        world, document, profile_version=bundle.version, out_dir=out_dir
    )


def _judge(tmp_path: Path) -> Judge:
    return Judge(
        JudgeConfig(model="fake-assessor", version="pin-ticket-b"),
        backend=lambda messages: {"content": PASS_JSON},
        provenance_log=ProvenanceLog(tmp_path / "provenance.jsonl"),
        clock=lambda: FROZEN,
    )


# ---------------------------------------------------------------------------
# 1. Optional means optional: the old shape normalises and renders unchanged
# ---------------------------------------------------------------------------


class TestTheOldShapeIsUntouched:
    """Checkbox 1.  No stored record's ``content_version`` may move.

    There is no document record in ``docs/`` on any branch, so nothing stored is at
    risk today.  The fixtures are: ``synthetic_candidate.json`` is imported by the
    harness tests, and a changed hash would move every node id derived from it.
    """

    def _plain(self) -> dict:
        return {
            "document_id": "PLAIN_DOC",
            "title": "A section with no sub_sections key",
            "sections": [
                {
                    "section_id": "excellence_section",
                    "title": "Excellence",
                    "content": SECTION_TEXT,
                    "addresses": [],
                }
            ],
            "claims": [],
            "commitments": [],
        }

    def test_a_section_without_sub_sections_carries_no_such_key(self):
        content = normalise_candidate(self._plain(), "plain")
        assert "sub_sections" not in content["sections"][0]

    def test_an_empty_sub_sections_list_is_dropped_rather_than_stored(self):
        """Otherwise ``[]`` and absent would hash differently for the same document."""
        with_empty = self._plain()
        with_empty["sections"][0]["sub_sections"] = []
        assert content_hash(normalise_candidate(with_empty, "empty")) == content_hash(
            normalise_candidate(self._plain(), "plain")
        )

    def test_the_rendered_text_is_unchanged_when_no_sub_section_is_declared(self):
        content = normalise_candidate(self._plain(), "plain")
        text, spans = render_document(content["sections"])
        assert text == f"## excellence_section Excellence\n\n{SECTION_TEXT}\n\n"
        assert spans["excellence_section"] == {"start": 0, "end": len(text)}

    def test_the_synthetic_fixture_still_imports_and_builds(self, world):
        """The fixture declares no sub-section, so its snapshot must be reachable."""
        snapshot = build_snapshot(world)
        assert snapshot.snapshot_id.startswith("sha256:")

    def test_a_candidate_with_no_sub_sections_still_materialises_one(
        self, world, ria_bundle, tmp_path
    ):
        """The old fallback stays, so a record predating this ticket still grades."""
        plain = self._plain()
        plain["sections"] = [
            {"section_id": sid, "title": sid, "content": SECTION_TEXT, "addresses": []}
            for _c, sid in ba.required_sections(ria_bundle.profile)
        ]
        evidence = ba.build_blind_evidence(
            world,
            _import(world, plain),
            profile_version=ria_bundle.version,
            out_dir=tmp_path / "out",
        )
        for path in sorted(evidence.candidate_dir.glob("*.json")):
            artifact = json.loads(path.read_text(encoding="utf-8"))
            ids = [s["sub_section_id"] for s in artifact["sub_sections"]]
            assert ids == [artifact["section_id"]]


# ---------------------------------------------------------------------------
# 2. The declared sub-sections survive the record, the graph and the materialiser
# ---------------------------------------------------------------------------


class TestTheDeclaredSubSectionsSurvive:
    def test_the_record_keeps_them_in_declaration_order(self, ria_bundle):
        content = normalise_candidate(_document(ria_bundle), "doc")
        section = next(
            s for s in content["sections"] if s["section_id"] == "excellence_section"
        )
        assert [s["sub_section_id"] for s in section["sub_sections"]] == [
            "B.1.1",
            "B.1.2",
        ]

    def test_an_anchor_id_carrying_dots_is_a_valid_identifier(self, ria_bundle):
        """``B.1.1`` and ``1.1`` must both pass the record's id rule."""
        content = normalise_candidate(_document(ria_bundle), "doc")
        every = [
            sub["sub_section_id"]
            for section in content["sections"]
            for sub in section.get("sub_sections", ())
        ]
        assert "B.1.1" in every

    def test_the_rendered_span_covers_the_sub_section_text(self, ria_bundle):
        """A span that stopped at the section content would exclude the answer."""
        content = normalise_candidate(_document(ria_bundle), "doc")
        text, spans = render_document(content["sections"])
        span = spans["excellence_section"]
        assert SUB_TEXT in text[span["start"] : span["end"]]
        assert text.count(SUB_TEXT) == len(
            [s for s in content["sections"] for _ in s.get("sub_sections", ())]
        )

    def test_the_passage_node_carries_them(self, world, ria_bundle):
        document = _import(world, _document(ria_bundle))
        snapshot = build_snapshot(world)
        passages = [
            n
            for n in snapshot.nodes
            if n["type"] == "passage" and n["content"].get("document", "").startswith(
                f"{document}@"
            )
        ]
        assert passages, "no passage of the imported document is in the snapshot"
        excellence = next(
            n for n in passages if n["content"]["section_id"] == "excellence_section"
        )
        assert [s["sub_section_id"] for s in excellence["content"]["sub_sections"]] == [
            "B.1.1",
            "B.1.2",
        ]

    def test_the_materialised_candidate_carries_the_anchor_ids(
        self, world, ria_bundle, tmp_path
    ):
        """This is the assertion F1 inverts: the ids are the anchors, not the section."""
        evidence = _evidence(world, ria_bundle, tmp_path / "out")
        found: dict[str, list[str]] = {}
        for path in sorted(evidence.candidate_dir.glob("*.json")):
            artifact = json.loads(path.read_text(encoding="utf-8"))
            found[artifact["section_id"]] = [
                s["sub_section_id"] for s in artifact["sub_sections"]
            ]
        assert found == _anchors_by_section(ria_bundle)

    def test_the_materialisation_is_byte_equal_on_a_second_build(
        self, world, ria_bundle, tmp_path
    ):
        first = _evidence(world, ria_bundle, tmp_path / "one")
        second = _evidence(world, ria_bundle, tmp_path / "two")
        for path in sorted(first.candidate_dir.glob("*.json")):
            twin = second.candidate_dir / path.name
            assert twin.read_bytes() == path.read_bytes()


# ---------------------------------------------------------------------------
# 3. The document route now grades under both shipped profiles
# ---------------------------------------------------------------------------


class TestItGradesUnderTheShippedProfiles:
    """Checkboxes 2 and 4.  F1's failing case, inverted."""

    def test_it_grades_under_the_real_ria_profile(self, world, ria_bundle, tmp_path):
        evidence = _evidence(world, ria_bundle, tmp_path / "out")
        report = ba.assess_candidate(
            _judge(tmp_path), ria_bundle, evidence=evidence, clock=lambda: FROZEN
        )
        assert report.scope in {"complete", "partial"}

    def test_the_ria_report_carries_the_three_pins(self, world, ria_bundle, tmp_path):
        evidence = _evidence(world, ria_bundle, tmp_path / "out")
        report = ba.assess_candidate(
            _judge(tmp_path), ria_bundle, evidence=evidence, clock=lambda: FROZEN
        )
        assert report.candidate_hash == ba.candidate_hash(
            ba.load_candidate(evidence.candidate_dir, ria_bundle.profile)
        )
        assert report.profile_version == ria_bundle.version
        assert report.assessor_pin
        assert report.candidate_hash.startswith("sha256:")
        for cell in report.cells:
            assert cell.candidate_hash == report.candidate_hash
            assert cell.profile_version == report.profile_version
            assert cell.assessor_pin == report.assessor_pin

    def test_the_same_shape_grades_under_the_msca_pf_profile(
        self, world, msca_bundle, tmp_path
    ):
        evidence = _evidence(world, msca_bundle, tmp_path / "out")
        report = ba.assess_candidate(
            _judge(tmp_path), msca_bundle, evidence=evidence, clock=lambda: FROZEN
        )
        assert report.scope in {"complete", "partial"}

    def test_the_anchor_bonus_is_still_what_ranks_a_dedicated_answer(
        self, world, ria_bundle, tmp_path
    ):
        """The fix must keep the anchor's purpose, not merely stop the exception.

        The bonus is observable without reading a score.  ``SUB_TEXT`` carries none of
        the selection terms, so a term-free paragraph that survives selection can only
        have survived on :data:`ANCHOR_SCORE_BONUS`.  The same paragraph, with the
        anchor moved elsewhere, is excluded as not relevant — and that contrast is what
        makes the first half mean anything.
        """
        assert "capability" not in SUB_TEXT, "the anchor text must be term-free here"
        evidence = _evidence(world, ria_bundle, tmp_path / "out")
        section = evidence.candidate_dir / "excellence_section.json"

        anchored = build_evidence_pack(
            expectation_key="exp",
            section_path=section,
            selection_terms=["capability"],
            anchor_sub_section_ids=["B.1.1"],
        )
        kept = [s for s in anchored.spans if s.sub_section_id == "B.1.1"]
        assert kept, "the declared anchor's paragraph was not selected"
        assert all(s.in_anchor and s.matched_terms == () for s in kept)
        assert ANCHOR_SCORE_BONUS == 2

        moved = build_evidence_pack(
            expectation_key="exp",
            section_path=section,
            selection_terms=["capability"],
            anchor_sub_section_ids=["B.1.2"],
        )
        assert [s for s in moved.spans if s.sub_section_id == "B.1.1"] == []
        dropped = [e for e in moved.excluded if e.key.startswith("B.1.1")]
        assert dropped, "the same paragraph outside the anchor was not even recorded"
        assert all(e.reason == EXCLUDED_NOT_RELEVANT for e in dropped)


# ---------------------------------------------------------------------------
# 4. Fail-closed is preserved
# ---------------------------------------------------------------------------


class TestTheAnchorMapStillFailsClosed:
    """Checkbox 3.  A declared anchor absent from the candidate still raises."""

    def test_a_missing_declared_anchor_still_raises(self, world, ria_bundle, tmp_path):
        with pytest.raises(EvidencePackError) as exc:
            evidence = _evidence(world, ria_bundle, tmp_path / "out", drop="B.1.2")
            ba.assess_candidate(
                _judge(tmp_path), ria_bundle, evidence=evidence, clock=lambda: FROZEN
            )
        message = str(exc.value)
        assert "B.1.2" in message
        assert "fail closed" in message

    def test_a_duplicate_sub_section_id_is_refused_by_the_record(self, ria_bundle):
        """Two sub-sections under one id would make the anchor map ambiguous."""
        payload = _document(ria_bundle)
        section = payload["sections"][0]
        section["sub_sections"].append(dict(section["sub_sections"][0]))
        with pytest.raises(DevGraphError, match="duplicate"):
            normalise_candidate(payload, "duplicate")

    def test_a_sub_section_without_an_id_is_refused(self, ria_bundle):
        payload = _document(ria_bundle)
        del payload["sections"][0]["sub_sections"][0]["sub_section_id"]
        with pytest.raises(DevGraphError):
            normalise_candidate(payload, "no id")

    def test_a_sub_section_id_that_is_not_an_identifier_is_refused(self, ria_bundle):
        payload = _document(ria_bundle)
        payload["sections"][0]["sub_sections"][0]["sub_section_id"] = "not an id"
        with pytest.raises(DevGraphError, match="identifier"):
            normalise_candidate(payload, "bad id")

    def test_sub_sections_must_be_a_list_of_objects(self, ria_bundle):
        payload = _document(ria_bundle)
        payload["sections"][0]["sub_sections"] = "B.1.1"
        with pytest.raises(DevGraphError):
            normalise_candidate(payload, "not a list")


# ---------------------------------------------------------------------------
# 5. F2 closes with it: the graded report can carry the ESR intake
# ---------------------------------------------------------------------------


class TestTheEsrIntakeCanNowBeStamped:
    """Checkbox 5.  F2 was F1 wearing another hat.

    ``_check_intake`` refuses an intake on the directory route, so the only route that
    could stamp one was the route F1 made ungradeable.  With F1 fixed the demo's own
    intake record stamps onto a real report.
    """

    def test_the_demo_intake_stamps_onto_the_report(self, world, ria_bundle, tmp_path):
        intake = read_esr_intake(REPO, INTAKE_ID)
        document = _import(
            world, _document(ria_bundle, document_id=intake.document_id)
        )
        evidence = ba.build_blind_evidence(
            world,
            document,
            profile_version=ria_bundle.version,
            out_dir=tmp_path / "out",
        )
        report = ba.assess_candidate(
            _judge(tmp_path),
            ria_bundle,
            evidence=evidence,
            intake=intake,
            clock=lambda: FROZEN,
        )
        assert report.intake_id == INTAKE_ID

    def test_the_stamped_intake_keeps_its_not_applicable_availability(self):
        intake = read_esr_intake(REPO, INTAKE_ID)
        assert intake.esr_availability == "not_applicable"
        assert intake.permitted_purpose == "blind_pre_evaluation"
