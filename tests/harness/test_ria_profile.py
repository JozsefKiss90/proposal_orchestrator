"""
The RIA pre-evaluation profile, held to the Tier 2A RIA/IA evaluation form.

Three things are checked here, in this order:

1. **The scorecard is a transcription, not a paraphrase.** Every aspect text,
   every scoring level and every threshold in
   ``harness/evaluator_scorecard_ria.json`` is re-read from the stored
   ``ef_he-ria-ia_en.pdf`` and compared. Changing one word of one aspect turns
   this file red, which is the point: the scorecard is the anchor the
   deterministic applicability filter reproduces (``harness/expectations.py``),
   so a drifted scorecard would silently redefine what is graded.
2. **The profile bundles.** The profile document, the scorecard and the rubric
   set load together, the six expectations come out applicable, and the profile
   carries its own version — distinct from the MSCA-PF default's, which must
   keep loading unchanged.
3. **A dry run produces an RIA report.** A synthetic RIA-shaped candidate is
   graded by a scripted assessor, and the report's criteria are the RIA
   criteria.

No Claude call, no DAG run, no network: the assessor is a scripted backend and
the candidate is built under ``tmp_path``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import harness.blind_assessment as ba
import harness.commands.blind_assessment as command
from harness.expectations import ExpectationError, load_expectation_substrate
from harness.judge import Judge, JudgeConfig
from harness.profile import DEFAULT_PROFILE_PATH, ProfileError, load_profile, parse_profile
from harness.provenance import ProvenanceLog
from harness.rubrics import RubricError, load_profile_bundle
from tests._tier_sources import read_pdf_pages

REPO_ROOT = Path(__file__).resolve().parents[2]

PROFILE_PATH = REPO_ROOT / "harness/profiles/ria_default.json"
SCORECARD_PATH = REPO_ROOT / "harness/evaluator_scorecard_ria.json"
RUBRIC_PATH = REPO_ROOT / "harness/rubrics_ria.json"
MSCA_PROFILE_PATH = REPO_ROOT / "harness/profiles/msca_pf_default.json"
FORM_PATH = REPO_ROOT / "docs/tier2a_instrument_schemas/evaluation_forms/ria_ia/ef_he-ria-ia_en.pdf"
SECTION_REGISTRY_PATH = (
    REPO_ROOT / "docs/tier2a_instrument_schemas/extracted/section_schema_registry.json"
)

#: The form's own bullet glyph. The two evaluator notes under "1. EVALUATION"
#: use a different character, so splitting on this yields the aspects alone.
BULLET = "•"

FROZEN = "2026-10-01T12:00:00+00:00"
PASS_JSON = '{"passed": true, "score": 0.9, "rationale": "scripted pass"}'

#: Prose carrying the RIA selection terms, so a pack is never empty of matches.
TEXT = (
    "The project objectives are measurable and go beyond the state of the art "
    "in interoperable biodiversity observation.\n\n"
    "The methodology, the pathways to the expected outcomes, the dissemination "
    "and exploitation plan, the work plan and the consortium capacity are each "
    "described with named partners and quantified effort."
)


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _mirror_profile_world(root: Path, document: dict) -> None:
    """Copy the profile's three declared files under *root*, keeping their paths.

    Lets a test mutate one bundled file and reload the bundle against a
    throwaway repo root, without touching the committed profile.
    """
    for relative in (
        document["registry_path"],
        document["scorecard"]["path"],
        document["rubric_set"]["path"],
    ):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            (REPO_ROOT / relative).read_text(encoding="utf-8-sig"), encoding="utf-8"
        )
    (root / "profile.json").write_text(
        json.dumps(document, ensure_ascii=False), encoding="utf-8"
    )


@pytest.fixture(scope="module")
def scorecard():
    return _read_json(SCORECARD_PATH)


@pytest.fixture(scope="module")
def bundle():
    return load_profile_bundle(PROFILE_PATH, repo_root=REPO_ROOT)


@pytest.fixture(scope="module")
def form_aspects(scorecard) -> tuple[str, ...]:
    """The six aspect bullets, re-read from the stored evaluation form.

    The Impact criterion's first aspect breaks across pages 4 and 5, so the two
    pages are joined with page 5's running header removed. The header must
    carry the version the scorecard's provenance claims — a form reissued under
    a new version stops matching here rather than being graded silently.
    """
    version = scorecard["provenance"]["version"]
    pages = read_pdf_pages(FORM_PATH, (4, 5))
    header, _, rest = pages[5].partition(" 5 ")
    assert f"V{version}" in header, f"page 5 header {header!r} does not carry V{version}"
    segments = (pages[4] + " " + rest).split(BULLET)
    aspects = tuple(" ".join(s.split("Comments:")[0].split()) for s in segments[1:])
    assert len(aspects) == 6, f"expected 6 aspect bullets, read {len(aspects)}"
    return aspects


# --------------------------------------------------------------------------- #
# 1. The scorecard transcribes the form
# --------------------------------------------------------------------------- #


class TestScorecardTracesToTheForm:
    def test_the_aspect_texts_are_the_form_bullets_in_order(self, scorecard, form_aspects):
        authored = tuple(
            a["text"] for c in scorecard["criteria"] for a in c["aspects"]
        )
        assert authored == form_aspects

    def test_every_aspect_names_the_page_it_is_read_from(self, scorecard, form_aspects):
        pages = read_pdf_pages(FORM_PATH, (4, 5))
        for criterion in scorecard["criteria"]:
            for aspect in criterion["aspects"]:
                page = aspect["source_page"]
                assert page in (4, 5, "4-5"), f"{aspect['id']}: unexpected page {page!r}"
                if page == "4-5":
                    # The one aspect that breaks across the boundary. Its head
                    # must be on page 4, its tail on page 5, and neither page
                    # may hold it whole — otherwise "4-5" is the wrong label.
                    head, tail = aspect["text"].rsplit(" ", 1)
                    assert head in pages[4], aspect["id"]
                    assert pages[5].startswith(tail) or f" {tail}" in pages[5], aspect["id"]
                    assert aspect["text"] not in pages[4]
                    assert aspect["text"] not in pages[5]
                    # And whole, in the header-stripped join the fixture builds.
                    assert aspect["text"] in form_aspects
                else:
                    assert aspect["text"] in pages[page], aspect["id"]

    def test_the_scoring_levels_are_verbatim_from_page_two(self, scorecard):
        page = read_pdf_pages(FORM_PATH, (2,))[2]
        levels = scorecard["scoring"]["levels"]
        assert sorted(levels) == ["0", "1", "2", "3", "4", "5"]
        for mark, text in levels.items():
            assert f"{mark} — {text}" in page, mark

    def test_the_scale_and_thresholds_are_the_form_s(self, scorecard):
        page = read_pdf_pages(FORM_PATH, (2,))[2]
        scoring = scorecard["scoring"]
        assert scoring["scale_source_quote"] in page
        assert scoring["threshold_source_quote"] in page
        assert scoring["weighting_source_quote"] in page
        # Page 2 states both thresholds in one sentence, which the stored quote
        # reproduces; the numbers are read back out of it rather than asserted
        # against a literal the form never prints on its own.
        assert f"individual criteria is {scoring['individual_threshold']}." in page
        assert f"is {scoring['overall_threshold']:g} points." in page

    def test_the_overall_maximum_is_the_total_the_form_prints(self, scorecard):
        """15 is on page 5, not page 2: the form prints it beside 'Total score'."""
        page = read_pdf_pages(FORM_PATH, (5,))[5]
        assert f"Total score Overall threshold /{scorecard['scoring']['overall_max']:g}" in page

    def test_each_criterion_carries_the_form_s_individual_threshold(self, scorecard):
        page = read_pdf_pages(FORM_PATH, (4, 5))
        both = page[4] + " " + page[5]
        for criterion in scorecard["criteria"]:
            score_field = criterion["score_field"]
            assert f"{score_field} (0-5): Threshold: {criterion['threshold_score']}/5" in both

    def test_the_criterion_names_are_the_form_headings(self, scorecard):
        pages = read_pdf_pages(FORM_PATH, (4, 5))
        both = pages[4] + " " + pages[5]
        for i, criterion in enumerate(scorecard["criteria"], 1):
            assert f"{i}. {criterion['name']}" in both, criterion["id"]

    def test_an_ria_carries_no_weighting_and_says_so(self, scorecard):
        """The form's own rule is that RIA scores are not weighted.

        ``weight_pct`` is the only key the scorecard loader accepts, so the
        unweighted ranking multiplier of 1 is recorded there and the mismatch
        is named in the note rather than hidden behind a fabricated percentage.
        The rule the value rests on is checked against page 2 here, so the
        test is not satisfied by the value alone.
        """
        page = read_pdf_pages(FORM_PATH, (2,))[2]
        assert "Scores are normally NOT weighted." in page
        note = scorecard["scoring"]["weighting_note"]
        assert "unweighted ranking multiplier of 1" in note
        assert "rather than a percentage" in note
        for criterion in scorecard["criteria"]:
            assert criterion["weight_pct"] == 1
            assert "weight_note" not in criterion, (
                f"{criterion['id']}: the weighting rule has one home, scoring.weighting_note"
            )

    def test_the_provenance_names_the_stored_form(self, scorecard):
        prov = scorecard["provenance"]
        assert prov["source_path"] == (
            "docs/tier2a_instrument_schemas/evaluation_forms/ria_ia/ef_he-ria-ia_en.pdf"
        )
        assert (REPO_ROOT / prov["source_path"]).is_file()
        assert prov["version"] == "4.0"

    def test_the_criteria_pages_carry_no_option_tag_at_all(self):
        """The ground of the empty exclusion list, checked against the form.

        Asserting ``excluded_aspects == []`` on its own only checks what the
        author typed. What makes the empty list correct is that pages 4 and 5
        annotate nothing: every ``OPTION`` in this form is on pages 6 to 8 and
        concerns an evaluator role (IER, CR, ESR) or a lump-sum assessment,
        never a type of action. So no aspect can be variant-scoped, and nothing
        is filtered for an RIA.
        """
        pages = read_pdf_pages(FORM_PATH, (4, 5))
        assert "OPTION" not in pages[4]
        assert "OPTION" not in pages[5]

    def test_no_aspect_is_excluded_for_an_ria(self, scorecard, bundle):
        assert scorecard["excluded_aspects"] == []
        assert bundle.substrate.excluded == ()


# --------------------------------------------------------------------------- #
# 2. The profile bundles
# --------------------------------------------------------------------------- #


class TestProfileLoads:
    def test_the_bundle_loads_with_its_own_version(self, bundle):
        assert bundle.profile_id == "ria_default"
        assert bundle.profile.instrument.registry_instrument_type == "RIA"
        assert bundle.version.startswith("sha256:")
        assert bundle.rubric_set.rubric_set_id == "ria_ia_rubrics"
        assert bundle.substrate.scorecard_id == "ria_ia_evaluation_scorecard"

    def test_the_six_expectations_cover_the_three_criteria(self, bundle):
        assert bundle.profile.criterion_ids == ("excellence", "impact", "implementation")
        assert len(bundle.substrate.expectations) == 6
        by_criterion: dict[str, int] = {}
        for expectation in bundle.substrate.expectations:
            by_criterion[expectation.criterion_id] = by_criterion.get(expectation.criterion_id, 0) + 1
        assert by_criterion == {"excellence": 2, "impact": 2, "implementation": 2}
        assert bundle.substrate.excluded == ()

    def test_each_criterion_maps_to_its_tier5_section_artifact(self, bundle):
        assert bundle.profile.section_ids_for("excellence") == ("excellence_section",)
        assert bundle.profile.section_ids_for("impact") == ("impact_section",)
        assert bundle.profile.section_ids_for("implementation") == ("implementation_section",)

    def test_one_rubric_per_expectation_with_the_verbatim_text(self, bundle):
        rubrics = bundle.rubric_set.by_key()
        assert len(rubrics) == 6
        for expectation in bundle.substrate.expectations:
            rubric = rubrics[expectation.expectation_key]
            assert rubric.expectation_text == expectation.text
            assert rubric.criterion_id == expectation.criterion_id
            assert rubric.form_name == "HE RIA and IA Evaluation Form"

    def test_every_anchor_is_a_registry_declared_ria_sub_section(self, bundle):
        """The anchors are the Part B sub-section ids Phase 8 writes for an RIA.

        They come from the Tier 2A section_schema_registry, which is what
        ``InstrumentProfile.drafting_sub_sections`` reads, so an anchor that is
        not a declared RIA sub-section would fail closed on the first real
        candidate instead of here.
        """
        registry = _read_json(SECTION_REGISTRY_PATH)
        ria = next(i for i in registry["instruments"] if i["instrument_type"] == "RIA")
        declared = {
            s["section_id"]
            for s in ria["sections"]
            if s.get("section_type") in ("proposal_section", "implementation_section")
        }
        for rubric in bundle.rubric_set.rubrics:
            assert rubric.anchor_sub_section_ids, rubric.expectation_key
            for anchor in rubric.anchor_sub_section_ids:
                assert anchor in declared, f"{rubric.expectation_key}: {anchor}"

    def test_only_the_optional_impact_canvas_is_left_unanchored(self, bundle):
        """Every mandatory RIA sub-section is anchored; B.2.3 deliberately is not.

        B.2.3 is the optional impact canvas the form tells applicants to remove
        if unused. Anchoring it would make every Impact pack raise whenever a
        candidate omits it, because ``build_evidence_pack`` fails closed on an
        absent anchor. Its prose is still selected on term match when present.
        """
        registry = _read_json(SECTION_REGISTRY_PATH)
        ria = next(i for i in registry["instruments"] if i["instrument_type"] == "RIA")
        drafted = [
            s
            for s in ria["sections"]
            if s.get("section_type") in ("proposal_section", "implementation_section")
        ]
        anchored = {
            a for r in bundle.rubric_set.rubrics for a in r.anchor_sub_section_ids
        }
        unanchored = {s["section_id"] for s in drafted} - anchored
        assert unanchored == {"B.2.3"}
        canvas = next(s for s in drafted if s["section_id"] == "B.2.3")
        assert canvas["mandatory"] is False
        assert all(s["mandatory"] for s in drafted if s["section_id"] in anchored)
        # The omission is a recorded choice, not an oversight.
        assert "B.2.3" in _read_json(RUBRIC_PATH)["framing"]

    def test_the_scoring_block_reaches_the_bundle(self, bundle):
        assert bundle.scoring.overall_threshold == 10
        assert bundle.scoring.overall_max == 15
        assert bundle.scoring.weights == {"excellence": 1, "impact": 1, "implementation": 1}

    def test_the_option_tag_admits_an_ria(self, bundle):
        for expectation in bundle.substrate.expectations:
            tag = expectation.option_tag
            assert tag.applicable is True
            assert set(tag.variants) == {"RIA", "IA"}
            assert tag.source == "scorecard"

    def test_a_variant_outside_the_tag_fails_closed(self):
        """Repointing the profile at a variant the aspects do not name must raise.

        The filter reproduces the scorecard or it fails; it never grades a
        subset. ``CSA`` is a known variant here only to make the negative case
        expressible.
        """
        document = _read_json(PROFILE_PATH)
        document["option_tag_grammar"]["known_variants"].append("CSA")
        document["option_tag_grammar"]["applicable_variant"] = "CSA"
        profile = parse_profile(document, source_path=PROFILE_PATH)
        with pytest.raises(ExpectationError) as excinfo:
            load_expectation_substrate(profile=profile, repo_root=REPO_ROOT)
        assert "not applicable" in str(excinfo.value)

    def test_a_reworded_aspect_breaks_the_load(self, tmp_path):
        """Paraphrasing one aspect must raise, not grade a five-aspect subset."""
        document = _read_json(PROFILE_PATH)
        _mirror_profile_world(tmp_path, document)
        mirrored = tmp_path / document["scorecard"]["path"]
        scorecard = _read_json(mirrored)
        scorecard["criteria"][0]["aspects"][0]["text"] = "Clarity of the objectives."
        mirrored.write_text(json.dumps(scorecard, ensure_ascii=False), encoding="utf-8")
        with pytest.raises((RubricError, ProfileError)) as excinfo:
            load_profile_bundle(tmp_path / "profile.json", repo_root=tmp_path)
        message = str(excinfo.value)
        assert "registry drift" in message or "stale scorecard" in message


# --------------------------------------------------------------------------- #
# 3. The MSCA-PF default is untouched
# --------------------------------------------------------------------------- #


class TestMscaDefaultIsUntouched:
    def test_the_msca_default_profile_still_bundles(self):
        msca = load_profile_bundle(MSCA_PROFILE_PATH, repo_root=REPO_ROOT)
        assert msca.profile_id == "msca_pf_default"
        assert len(msca.substrate.expectations) == 9
        assert msca.scoring.overall_max == 100

    def test_the_two_profiles_carry_different_versions(self, bundle):
        msca = load_profile_bundle(MSCA_PROFILE_PATH, repo_root=REPO_ROOT)
        assert bundle.version != msca.version
        assert bundle.rubric_set.fingerprint != msca.rubric_set.fingerprint

    def test_the_default_profile_path_is_still_the_msca_one(self):
        assert DEFAULT_PROFILE_PATH.as_posix() == "harness/profiles/msca_pf_default.json"
        assert load_profile(REPO_ROOT / DEFAULT_PROFILE_PATH).profile_id == "msca_pf_default"


# --------------------------------------------------------------------------- #
# 4. The dry run
# --------------------------------------------------------------------------- #


class ScriptedBackend:
    """Returns one scripted response for every call."""

    def __init__(self, content: str = PASS_JSON):
        self.content = content

    def __call__(self, messages):
        return {"content": self.content}


def _section(sub_section_ids) -> dict:
    return {
        "sub_sections": [
            {"sub_section_id": sid, "title": f"Section {sid}", "content": TEXT}
            for sid in sub_section_ids
        ],
        "validation_status": {
            "claim_statuses": [
                {
                    "claim_id": "C01",
                    "claim_summary": "The objectives go beyond the state of the art.",
                    "status": "confirmed",
                    "source_ref": "docs/tier3_project_instantiation/architecture_inputs/objectives.json",
                }
            ]
        },
    }


def _candidate(root: Path, bundle, *, drop: str | None = None) -> Path:
    """A candidate holding each profile-required section with its own anchors."""
    anchors: dict[str, set[str]] = {}
    for rubric in bundle.rubric_set.rubrics:
        for section_id in bundle.profile.section_ids_for(rubric.criterion_id):
            anchors.setdefault(section_id, set()).update(rubric.anchor_sub_section_ids)
    root.mkdir(parents=True, exist_ok=True)
    for section_id, ids in anchors.items():
        if section_id == drop:
            continue
        (root / f"{section_id}.json").write_text(
            json.dumps(_section(sorted(ids)), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return root


def _judge(tmp_path: Path, backend) -> Judge:
    return Judge(
        JudgeConfig(model="fake-assessor", version="pin-ria"),
        backend=backend,
        provenance_log=ProvenanceLog(tmp_path / "provenance.jsonl"),
        clock=lambda: FROZEN,
    )


class TestDryRun:
    def test_a_synthetic_candidate_yields_a_report_with_the_ria_criteria(
        self, tmp_path, bundle
    ):
        candidate = _candidate(tmp_path / "candidate", bundle)
        report = ba.assess_candidate(
            _judge(tmp_path, ScriptedBackend()), bundle, candidate, clock=lambda: FROZEN
        )
        assert report.scope == ba.SCOPE_COMPLETE
        assert report.profile_id == "ria_default"
        assert report.profile_version == bundle.version
        assert report.scorecard_id == "ria_ia_evaluation_scorecard"
        assert report.scorecard_version == "4.0"
        assert len(report.cells) == 6
        summary = report.summary
        assert set(summary["criteria"]) == {"excellence", "impact", "implementation"}
        assert all(e["cells"] == 2 for e in summary["criteria"].values())
        assert {c.expectation_key for c in report.cells} == set(
            bundle.rubric_set.by_key()
        )

    def test_the_report_is_advisory_and_never_blocking(self, tmp_path, bundle):
        candidate = _candidate(tmp_path / "candidate", bundle)
        report = ba.assess_candidate(
            _judge(tmp_path, ScriptedBackend()), bundle, candidate, clock=lambda: FROZEN
        )
        data = report.to_dict()
        assert data["advisory"] is True
        assert data["blocking"] is False

    def test_the_command_writes_a_report_file_naming_the_ria_criteria(
        self, tmp_path, bundle, capsys
    ):
        """The dry run through the module command, end to end.

        Exercises what the operator will run for a real candidate: profile
        resolution, assessment, the written report file and the rendered
        summary. The assessor is scripted, so no Claude call is made.
        """
        candidate = _candidate(tmp_path / "candidate", bundle)
        out_dir = tmp_path / "reports"
        code = command.main(
            [
                "assess",
                "--candidate",
                str(candidate),
                "--profile",
                str(PROFILE_PATH),
                "--repo-root",
                str(REPO_ROOT),
                "--out-dir",
                str(out_dir),
                "--provenance",
                str(tmp_path / "provenance.jsonl"),
            ],
            judge=_judge(tmp_path, ScriptedBackend()),
            clock=lambda: FROZEN,
        )
        assert code == 0
        written = sorted(out_dir.glob("blind_*.json"))
        assert len(written) == 1
        data = json.loads(written[0].read_text(encoding="utf-8"))
        assert data["profile_id"] == "ria_default"
        assert set(data["summary"]["criteria"]) == {
            "excellence",
            "impact",
            "implementation",
        }
        assert data["scope"] == "complete"
        rendered = capsys.readouterr().out
        assert "ria_default" in rendered

    def test_a_missing_section_is_reported_partial_not_passed_over(self, tmp_path, bundle):
        candidate = _candidate(tmp_path / "candidate", bundle, drop="impact_section")
        report = ba.assess_candidate(
            _judge(tmp_path, ScriptedBackend()), bundle, candidate, clock=lambda: FROZEN
        )
        assert report.scope == ba.SCOPE_PARTIAL
        assert [m.section_id for m in report.partial_coverage] == ["impact_section"]
        assert len(report.cells) == 4
        assert "impact" not in report.summary["criteria"]
