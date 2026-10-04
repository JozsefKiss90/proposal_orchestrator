"""
The MSCA-DN evaluation bundle (spec PE-02), held to the stored forms.

Five things are checked, in this order:

1. **The scorecard is a derivation, not a transcription from memory.** Every
   aspect text, level, weight and quote in ``harness/evaluator_scorecard_msca_dn.json``
   is re-read from ``ef_he-msca_en.pdf`` V2.2 and General Annexes Part 15, and
   the authoring tool replays byte-equal. The §3.2 bracket defect is checked
   against the form on each of its three grounds.
2. **The AF V6.0 headings confirm the ten anchors one-to-one**, after the
   ``#@...@#`` tags are stripped, under the recorded correspondence rule.
3. **Nothing foreign can enter a DN assessment**: the PF-only aspects, every
   other variant, and Part B2 section 11.
4. **The registry gained an entry and lost nothing**: the RIA and MSCA-PF
   entries hash to what they hashed before the DN entry was added, and all
   three bundles load.
5. **The criterion appendix mapping is pinned by the rubric set** and every
   Confirmed row quotes the application form.

No Claude call, no DAG run, no network.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from harness.expectations import parse_option_tag
from harness.rubrics import load_profile_bundle
from tests._tier_sources import read_pdf_pages
from tools import author_msca_dn_bundle as bundle_tool

REPO_ROOT = Path(__file__).resolve().parents[2]

PROFILE_PATH = REPO_ROOT / bundle_tool.PROFILE_REL
SCORECARD_PATH = REPO_ROOT / bundle_tool.SCORECARD_REL
RUBRIC_PATH = REPO_ROOT / bundle_tool.RUBRICS_REL
MAPPING_PATH = REPO_ROOT / bundle_tool.MAPPING_REL
REGISTRY_PATH = REPO_ROOT / bundle_tool.REGISTRY_REL
FORM_PATH = REPO_ROOT / bundle_tool.EVALUATION_FORM_REL
AF_V6_PATH = REPO_ROOT / bundle_tool.APPLICATION_FORM_V6_REL
GA_PATH = REPO_ROOT / bundle_tool.GENERAL_ANNEXES_REL
DECISION_PATH = (
    REPO_ROOT
    / "docs/tier4_orchestration_state/decision_log/msca-dn-pe02-evaluation-bundle_2026-10-04.json"
)

#: sha256 of each pre-existing registry instrument, canonical JSON, computed
#: from the committed registry before the DN entry was added (git HEAD
#: 0e7118b). Typed on purpose: the test must catch a rewritten entry, so it
#: cannot read the expected value from the file under test.
PRE_EXISTING_ENTRY_HASHES = {
    "RIA": "b36e47202521f2bb483988b073d8f30a1c413db81fc9eb63c1add760eb29eecb",
    "MSCA-PF": "eb40c8c6ceb8d380a33f9c3f18ff3541718aadc2072bb5ee97b93981647d52cc",
}

ANCHORS = ("1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "2.4", "3.1", "3.2")
PART_B2_SUB_SECTIONS = ("4", "5", "6", "7", "8")

#: The spec's §3.1 table: anchor -> (option tag, form page). Typed from the
#: spec on purpose, so a tag swapped between two aspects fails here.
SPEC_TABLE = {
    "1.1": ("MSCA Doctoral networks, Postdoctoral fellowships", 4),
    "1.2": ("MSCA Doctoral networks, Postdoctoral fellowships", 4),
    "1.3": ("MSCA Doctoral networks", 4),
    "1.4": ("MSCA Doctoral networks", 4),
    "2.1": ("MSCA Doctoral networks", 5),
    "2.2": ("MSCA Doctoral networks", 5),  # untagged in the form, resolved per §3.2
    "2.3": ("all MSCA except Special needs allowances and COFUND Choose Europe", 6),
    "2.4": ("MSCA Doctoral networks, Postdoctoral fellowships and Staff exchanges", 6),
    "3.1": ("all MSCA except Special needs allowances and COFUND Choose Europe", 6),
    "3.2": ("MSCA Doctoral networks and Staff exchanges", 6),
}
WORK_PROGRAMME_PATH = REPO_ROOT / bundle_tool.WORK_PROGRAMME_REL

PF_ONLY_TEXTS = (
    "Quality of the supervision, training and of the two-way transfer of knowledge between the researcher and the host.",
    "Quality and appropriateness of the researcher’s professional experience, competences and skills.",
)
RAISE_CALL = "HORIZON-RAISE-2026-01-MSCA"


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _canonical_hash(obj) -> str:
    data = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _strip_tags(text: str) -> str:
    return bundle_tool.strip_template_tags(text)


@pytest.fixture(scope="module")
def scorecard():
    return _read_json(SCORECARD_PATH)


@pytest.fixture(scope="module")
def rubric_set():
    return _read_json(RUBRIC_PATH)


@pytest.fixture(scope="module")
def mapping():
    return _read_json(MAPPING_PATH)


@pytest.fixture(scope="module")
def profile():
    return _read_json(PROFILE_PATH)


@pytest.fixture(scope="module")
def bundle():
    return load_profile_bundle(PROFILE_PATH, repo_root=REPO_ROOT)


@pytest.fixture(scope="module")
def form_pages() -> dict:
    """Criteria pages 4-7 with the running header checked for the claimed version."""
    pages = read_pdf_pages(FORM_PATH, (2, 4, 5, 6, 7))
    for n in (4, 5, 6, 7):
        assert pages[n].startswith(f"{bundle_tool.EVALUATION_FORM_HEADER} {n} "), n
    return pages


@pytest.fixture(scope="module")
def aspects(scorecard) -> list[dict]:
    return [a for c in scorecard["criteria"] for a in c["aspects"]]


@pytest.fixture(scope="module")
def walk():
    return bundle_tool.derive_form_aspects(REPO_ROOT)


# --------------------------------------------------------------------------- #
# 1. The scorecard derives from the forms
# --------------------------------------------------------------------------- #


class TestScorecardTracesToTheForm:
    def test_the_authored_bundle_replays_byte_equal(self):
        assert bundle_tool.check(REPO_ROOT) == []

    def test_there_are_ten_aspects_with_the_spec_ids_and_anchors(self, aspects):
        assert [(a["anchor"], a["id"]) for a in aspects] == [
            (anchor, aspect_id) for anchor, aspect_id, _c in bundle_tool.DN_ASPECTS
        ]
        assert tuple(a["anchor"] for a in aspects) == ANCHORS

    def test_each_aspect_carries_the_tag_and_page_of_the_spec_table(self, aspects):
        assert {a["anchor"]: (a["option_tag"], a["source_page"]) for a in aspects} == SPEC_TABLE

    def test_every_aspect_text_is_on_the_page_it_names(self, aspects, form_pages):
        for aspect in aspects:
            page = aspect["source_page"]
            assert page in (4, 5, 6), aspect["id"]
            assert aspect["text"] in form_pages[page], aspect["id"]

    def test_the_bracket_walk_yields_exactly_the_ten(self, walk, aspects):
        applicable = [a for a in walk if a.applicable_dn]
        untagged = [a for a in walk if a.untagged]
        assert len(applicable) == 9
        assert len(untagged) == 1
        texts = [a.text for a in walk if a.applicable_dn or a.untagged]
        assert texts == [a["text"] for a in aspects]

    def test_every_tagged_aspect_carries_the_bracket_the_form_prints(self, aspects, form_pages):
        joined = " ".join(form_pages[n] for n in (4, 5, 6))
        for aspect in aspects:
            if aspect["option_tag_status"] == "Confirmed":
                assert f"[OPTION for {aspect['option_tag']}" in joined, aspect["id"]
            else:
                assert aspect["id"] == "imp-career"

    def test_the_untagged_career_bullet_is_resolved_on_three_checkable_grounds(
        self, scorecard, aspects, walk, form_pages
    ):
        career = next(a for a in aspects if a["id"] == "imp-career")
        assert career["option_tag"] == "MSCA Doctoral networks"
        assert career["option_tag_status"] == "Inferred"
        resolution = scorecard["provenance"]["untagged_bullet_resolution"]
        assert resolution["aspect_id"] == "imp-career"
        assert len(resolution["grounds"]) == 3
        # Ground 1: plural DN text; singular PF variant printed immediately below.
        assert "researchers" in career["text"] and "their" in career["text"]
        pf_variant = (
            "[OPTION for MSCA Postdoctoral fellowships: Credibility of the measures to enhance "
            "the career perspectives and employability of the researcher and contribution to "
            "his/her skills development. ]"
        )
        page5 = form_pages[5]
        assert pf_variant in page5
        assert page5.index(career["text"]) < page5.index(pf_variant)
        # Ground 3: no bracket is open there. The walk shows the bullet closes a
        # bracket it did not open, and the bullet before it closed the DN one.
        index = next(i for i, a in enumerate(walk) if a.untagged)
        assert walk[index].closes and not walk[index].opens
        assert walk[index - 1].closes
        assert walk[index - 1].option_tag == "MSCA Doctoral networks"
        assert walk[index - 1].text.endswith("developing sustainable elements of doctoral programmes.")
        # Ground 2 is the ESR, read in session and never copied here.
        assert "ESR" in resolution["grounds"][1]
        assert "decision 12" in resolution["grounds"][1]

    def test_the_scoring_levels_are_the_form_s_full_sentences(self, scorecard, form_pages):
        page = form_pages[2]
        levels = scorecard["scoring"]["levels"]
        assert sorted(levels) == ["0", "1", "2", "3", "4", "5"]
        for mark, text in levels.items():
            assert f"{mark} — {text}" in page, mark
        assert levels["5"].endswith("Any shortcomings are minor.")

    def test_the_scale_threshold_and_weighting_quotes_are_on_page_two(self, scorecard, form_pages):
        scoring = scorecard["scoring"]
        page = form_pages[2]
        assert scoring["scale_source_quote"] in page
        assert scoring["threshold_source_quote"] in page
        assert scoring["weighting_source_quote"] in page
        assert f"is {scoring['overall_threshold']:g} points." in page
        assert scoring["overall_max"] == 100
        assert "Total score Overall threshold /100" in form_pages[7]

    def test_the_weights_are_the_form_s_and_the_formula_follows(self, scorecard, form_pages):
        multipliers = {"excellence": 10, "impact": 6, "implementation": 4}
        for criterion in scorecard["criteria"]:
            page = form_pages[criterion["weighting_page"]]
            assert f"{criterion['score_field']} (0-5): Weighting: {criterion['weight_pct']}%" in page
            assert criterion["weight_pct"] * 100 // 500 == multipliers[criterion["id"]]
        assert scorecard["scoring"]["total_formula"] == "S = 10·E + 6·I + 4·Q"
        assert sum(c["weight_pct"] for c in scorecard["criteria"]) == 100

    def test_the_criterion_names_are_the_form_headings(self, scorecard, form_pages):
        joined = " ".join(form_pages[n] for n in (4, 5, 6))
        for i, criterion in enumerate(scorecard["criteria"], 1):
            assert f"{i}. {criterion['name']}" in joined, criterion["id"]

    def test_the_per_criterion_threshold_and_no_aspect_scores_come_from_general_annexes(self, scorecard):
        page = read_pdf_pages(GA_PATH, (27,))[27]
        assert "General Annexes Part 15 - Page 27 of 46" in page
        scoring = scorecard["scoring"]
        assert scoring["individual_threshold"] == 3
        assert scoring["individual_threshold_source"]["page"] == 27
        assert scoring["individual_threshold_source"]["quote"] in page
        assert scoring["no_aspect_scores_rule"]["quote"] in page
        assert "not for the different aspects" in scoring["no_aspect_scores_rule"]["quote"]
        for criterion in scorecard["criteria"]:
            assert criterion["threshold_score"] == 3

    def test_the_annex_d_override_is_recorded_as_a_tier_interaction(self, scorecard):
        page = read_pdf_pages(GA_PATH, (27,))[27]
        override = scorecard["scoring"]["annex_d_override"]
        assert override["annex_d_rule"] in page
        assert "will be 10" in override["annex_d_rule"]
        assert "is 70 points" in override["form_rule"]
        assert "§12.3" in override["resolution"]
        assert DECISION_PATH.is_file(), "the §12.3 record the scorecard names must exist"
        record = _read_json(DECISION_PATH)
        assert "annex_d_override" in json.dumps(record)

    def test_the_provenance_names_both_forms_and_the_v5_equivalence(self, scorecard):
        prov = scorecard["provenance"]
        assert prov["source_path"] == bundle_tool.EVALUATION_FORM_REL
        assert (REPO_ROOT / prov["source_path"]).is_file()
        assert prov["version"] == "2.2"
        structural = prov["structural_authority"]
        assert structural["version"] == "6.0"
        assert (REPO_ROOT / structural["source_path"]).is_file()
        equivalence = prov["v5_equivalence"]
        assert equivalence["version"] == "5.0"
        assert (REPO_ROOT / equivalence["source_path"]).is_file()
        assert "section 11" in equivalence["statement"]
        register = _read_json(
            REPO_ROOT / "docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register.json"
        )
        declared = {
            row["path"]: row["version"] for row in register["provenance"]["inputs"]
        }
        assert declared[structural["source_path"]].startswith("V6.0")
        assert declared[equivalence["source_path"]].startswith("V5.0")

    def test_the_esr_cross_confirmation_copies_no_esr_text(self, scorecard):
        note = scorecard["provenance"]["esr_cross_confirmation"]
        assert "nine of the ten" in note
        assert "No ESR text is stored" in note
        assert "85.80" not in json.dumps(scorecard)


# --------------------------------------------------------------------------- #
# 2. The AF V6.0 headings confirm the anchors
# --------------------------------------------------------------------------- #


def _corresponds(aspect_text: str, heading: str, glosses: list[str]) -> bool:
    """The recorded rule, restated here independently of the tool."""
    h = " ".join(heading.split()).lower()
    for gloss in glosses:
        assert gloss in h, gloss
        h = h.replace(gloss, "")
    return h.rstrip(".") == " ".join(aspect_text.split()).lower().rstrip(".")


class TestApplicationFormHeadingsConfirmTheAnchors:
    @pytest.fixture(scope="class")
    def template(self) -> dict:
        raw = read_pdf_pages(AF_V6_PATH, (28, 29, 30, 31))
        assert "#@REL-EVA-RE@#" in raw[28], "the stripping rule must have something to strip"
        return {n: _strip_tags(t) for n, t in raw.items()}

    def test_each_heading_is_on_the_template_page_it_names_after_tag_stripping(self, aspects, template):
        for aspect in aspects:
            heading = aspect["af_v6_heading"]
            assert "#@" not in heading and "#§" not in heading, aspect["id"]
            page = template[aspect["af_v6_heading_page"]]
            assert f"{aspect['anchor']} {heading}" in page, aspect["id"]

    def test_the_ten_anchors_appear_in_order(self, template):
        joined = " ".join(template[n] for n in (28, 29, 30, 31))
        positions = [joined.index(f" {anchor} ") for anchor in ANCHORS]
        assert positions == sorted(positions)

    def test_each_heading_corresponds_to_its_aspect_under_the_recorded_rule(self, aspects):
        for aspect in aspects:
            assert _corresponds(aspect["text"], aspect["af_v6_heading"], aspect["af_v6_heading_glosses"]), aspect["id"]

    def test_only_two_headings_carry_glosses(self, aspects):
        glossed = {a["anchor"]: a["af_v6_heading_glosses"] for a in aspects if a["af_v6_heading_glosses"]}
        assert set(glossed) == {"2.1", "2.4"}
        assert "pathways towards impact" in glossed["2.4"][0]
        assert any("lasting" in g for g in glossed["2.1"])


# --------------------------------------------------------------------------- #
# 3. Nothing foreign enters a DN assessment
# --------------------------------------------------------------------------- #


class TestExclusions:
    def test_the_pf_only_aspects_cannot_enter(self, bundle, scorecard):
        graded = {e.text for e in bundle.substrate.expectations}
        excluded_texts = {e["text"]: e for e in scorecard["excluded_aspects"]}
        for text in PF_ONLY_TEXTS:
            assert text not in graded
            assert excluded_texts[text]["option_tag"] == "MSCA Postdoctoral fellowships"
            tag = parse_option_tag(excluded_texts[text]["option_tag"], source="test", grammar=bundle.profile.grammar)
            assert tag.applicable is False

    def test_every_excluded_entry_is_inapplicable_and_absent_from_the_registry(self, bundle, scorecard):
        assert len(bundle.substrate.excluded) == len(scorecard["excluded_aspects"])
        for excluded in bundle.substrate.excluded:
            assert excluded.option_tag.applicable is False
            assert excluded.present_in_registry is False

    def test_every_non_dn_family_of_the_form_is_excluded(self, scorecard):
        tags = {e["option_tag"] for e in scorecard["excluded_aspects"]}
        for family in ("Postdoctoral fellowships", "Staff exchanges", "COFUND", "COFUND Choose Europe", "Special needs allowances"):
            assert any(family in tag for tag in tags), family
        assert all("Doctoral networks" not in tag for tag in tags)

    def test_the_staff_exchanges_duplicate_of_exc_obj_is_recorded_not_graded_twice(self, scorecard, aspects):
        shared = scorecard["excluded_aspects_sharing_included_text"]
        assert len(shared) == 1
        assert shared[0]["option_tag"] == "MSCA Staff exchanges"
        assert shared[0]["text"] == next(a["text"] for a in aspects if a["id"] == "exc-obj")
        assert shared[0]["text"] not in {e["text"] for e in scorecard["excluded_aspects"]}

    def test_section_11_cannot_enter(self, scorecard, rubric_set, mapping, profile):
        sections = scorecard["excluded_sections"]
        assert [s["section"] for s in sections] == ["11"]
        eleven = sections[0]
        assert RAISE_CALL in eleven["heading"]
        page = _strip_tags(read_pdf_pages(AF_V6_PATH, (eleven["source_page"],))[eleven["source_page"]])
        assert f"11. {eleven['heading']}" in page
        assert all("11" not in r["anchor_sub_section_ids"] for r in rubric_set["rubrics"])
        assert all(row["candidate_sub_section"] != "11" for row in mapping["rows"])
        assert any("section 11" in item for item in mapping["never_received"])
        assert profile["target_call"]["call_id"] != RAISE_CALL
        assert RAISE_CALL not in json.dumps(profile)


# --------------------------------------------------------------------------- #
# 4. The registry gained an entry and lost nothing
# --------------------------------------------------------------------------- #


class TestRegistry:
    def test_ria_and_pf_entries_hash_to_their_pre_dn_values(self):
        registry = _read_json(REGISTRY_PATH)
        by_type = {i["instrument_type"]: i for i in registry["instruments"]}
        assert set(by_type) == {"RIA", "MSCA-PF", "MSCA-DN"}
        for instrument_type, expected in PRE_EXISTING_ENTRY_HASHES.items():
            assert _canonical_hash(by_type[instrument_type]) == expected, instrument_type

    def test_the_dn_rows_are_the_scorecard_texts_in_order(self, scorecard):
        registry = _read_json(REGISTRY_PATH)
        dn = next(i for i in registry["instruments"] if i["instrument_type"] == "MSCA-DN")
        rows = [row for c in dn["criteria"] for row in c["evaluator_expectations"]]
        assert rows == [a["text"] for c in scorecard["criteria"] for a in c["aspects"]]
        assert [c["criterion_id"] for c in dn["criteria"]] == ["Excellence", "Impact", "Implementation"]
        assert all(c["threshold_score"] == 3 for c in dn["criteria"])

    def test_all_three_profiles_still_load(self):
        counts = {}
        for rel in ("harness/profiles/msca_pf_default.json", "harness/profiles/ria_default.json", bundle_tool.PROFILE_REL):
            loaded = load_profile_bundle(REPO_ROOT / rel, repo_root=REPO_ROOT)
            counts[loaded.profile_id] = len(loaded.substrate.expectations)
        assert counts == {"msca_pf_default": 9, "ria_default": 6, "msca_dn_2026_default": 10}


# --------------------------------------------------------------------------- #
# 5. The profile bundles, and the mapping is pinned
# --------------------------------------------------------------------------- #


class TestProfileBundle:
    def test_the_bundle_loads_with_its_own_version(self, bundle):
        assert bundle.profile_id == "msca_dn_2026_default"
        assert bundle.profile.instrument.registry_instrument_type == "MSCA-DN"
        assert bundle.profile.grammar.applicable_variant == "Doctoral networks"
        assert bundle.version.startswith("sha256:")
        others = {
            load_profile_bundle(REPO_ROOT / rel, repo_root=REPO_ROOT).version
            for rel in ("harness/profiles/msca_pf_default.json", "harness/profiles/ria_default.json")
        }
        assert bundle.version not in others

    def test_the_ten_expectations_split_four_four_two(self, bundle):
        by_criterion: dict[str, int] = {}
        for expectation in bundle.substrate.expectations:
            by_criterion[expectation.criterion_id] = by_criterion.get(expectation.criterion_id, 0) + 1
        assert by_criterion == {"excellence": 4, "impact": 4, "implementation": 2}
        assert all(e.option_tag.applicable for e in bundle.substrate.expectations)

    def test_one_rubric_per_expectation_with_the_verbatim_text(self, bundle):
        rubrics = bundle.rubric_set.by_key()
        assert len(rubrics) == 10
        for expectation in bundle.substrate.expectations:
            rubric = rubrics[expectation.expectation_key]
            assert rubric.expectation_text == expectation.text
            assert rubric.criterion_id == expectation.criterion_id
            assert rubric.form_name == "HE MSCA Evaluation Form"

    def test_anchors_are_the_part_b1_sub_sections_and_part_b2_is_unanchored(self, bundle):
        anchors = [a for r in bundle.rubric_set.rubrics for a in r.anchor_sub_section_ids]
        assert tuple(anchors) == ANCHORS
        assert not set(anchors) & set(PART_B2_SUB_SECTIONS)

    def test_every_rubric_keeps_a_substantiation_step_that_can_report_unassessable(self, bundle):
        for rubric in bundle.rubric_set.rubrics:
            steps = " ".join(rubric.evaluation_steps)
            assert "UNASSESSABLE" in steps, rubric.expectation_key
            assert "never failed and never passed" in steps, rubric.expectation_key
            assert "SPECIFIC" in rubric.rubric, rubric.expectation_key

    def test_the_scoring_block_reaches_the_bundle(self, bundle):
        assert bundle.scoring.overall_threshold == 70
        assert bundle.scoring.overall_max == 100
        assert bundle.scoring.weights == {"excellence": 50, "impact": 30, "implementation": 20}

    def test_the_profile_owns_the_baseline_target_call_and_derives_it_from_tier_2b(self, profile):
        target = profile["target_call"]
        assert target["call_id"] == "HORIZON-MSCA-2026-DN-01"
        assert target["declared_status"] == "Confirmed"
        assert target["source_path"] == bundle_tool.WORK_PROGRAMME_REL
        work_programme = _read_json(WORK_PROGRAMME_PATH)
        calls = [
            c
            for d in work_programme["destinations"]
            for c in d.get("calls", [])
            if c.get("call_identifier") == target["call_id"]
        ]
        assert len(calls) == 1
        assert calls[0]["deadline"].startswith(target["deadline"] + "T")
        assert target["deadline"] == "2026-11-24", "the spec §1 deadline; the Tier 2B extract is the source"
        assert profile["structural_authority"]["version"] == "6.0"
        assert "standard Doctoral Network" in profile["implementation_mode"]


class TestCriterionAppendixMapping:
    def test_the_rubric_set_pins_the_mapping_by_hash_and_version(self, rubric_set, mapping):
        pin = rubric_set["criterion_appendix_mapping"]
        assert pin["path"] == bundle_tool.MAPPING_REL
        assert pin["sha256"] == hashlib.sha256(MAPPING_PATH.read_bytes()).hexdigest()
        assert mapping["rubric_set_id"] == rubric_set["rubric_set_id"]
        assert mapping["rubric_set_version"] == rubric_set["version"]
        assert mapping["scorecard_id"] == rubric_set["scorecard_id"]

    def test_every_row_names_a_scorecard_aspect_and_its_criterion(self, mapping, aspects):
        by_id = {a["id"]: a for a in aspects}
        criterion_of = {i: c for _a, i, c in bundle_tool.DN_ASPECTS}
        assert mapping["rows"], "an empty mapping would make the criterion stage silently section-only"
        for row in mapping["rows"]:
            assert row["aspect_id"] in by_id, row
            assert row["criterion_id"] == criterion_of[row["aspect_id"]], row
            assert row["status"] in ("Confirmed", "Inferred"), row
            if row["status"] == "Inferred":
                assert row["inference"], row

    def test_every_source_quote_is_on_the_application_form_page_it_names(self, mapping):
        pages = sorted({s["page"] for row in mapping["rows"] for s in row["sources"]})
        texts = {n: _strip_tags(t) for n, t in read_pdf_pages(AF_V6_PATH, tuple(pages)).items()}
        for row in mapping["rows"]:
            assert row["sources"], row["aspect_id"]
            for source in row["sources"]:
                assert source["source_path"] == bundle_tool.APPLICATION_FORM_V6_REL
                assert source["quote"] in texts[source["page"]], (row["aspect_id"], source["page"])

    def test_candidate_sub_sections_follow_the_spec_page_map(self, mapping):
        for row in mapping["rows"]:
            assert row["candidate_sub_section"] in ("3.1", "8"), row
            if row["table"].startswith("Table 3.1"):
                assert row["candidate_sub_section"] == "3.1"
            if row["table"].startswith("Section 8"):
                assert row["candidate_sub_section"] == "8"

    def test_each_criterion_receives_something_beyond_its_own_section(self, mapping):
        assert {row["criterion_id"] for row in mapping["rows"]} == {"excellence", "impact", "implementation"}
