"""
E5a — expectation substrate: registry loader + PF filter + criterion↔section map.

Deterministic, zero judge, zero DAG runs.  The tests pin the expected counts
(**10 raw / 9 PF-filtered**) against the *real* committed registry and
scorecard, so a registry edit breaks a test instead of quietly changing the
metric; drift fixtures (a dropped/added/reworded row, an unrecognised
``[OPTION …]`` tag, an unmapped criterion, a stale scorecard) assert the loader
fails closed rather than silently grading a subset.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import harness.expectations as exp

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / exp.DEFAULT_REGISTRY_PATH
SCORECARD_PATH = REPO_ROOT / exp.DEFAULT_SCORECARD_PATH

#: The pinned counts (the ticket's fail-closed drift bar): the committed
#: registry holds 10 raw MSCA-PF expectation rows; the PF-applicable set is 9.
EXPECTED_RAW_COUNT = 10
EXPECTED_PF_COUNT = 9

#: The 9 scorecard aspect ids, in scorecard order — the stable expectation keys.
EXPECTED_KEYS = (
    "exc-obj",
    "exc-method",
    "exc-supervision",
    "exc-researcher",
    "imp-career",
    "imp-dissemination",
    "imp-magnitude",
    "impl-workplan",
    "impl-host",
)


def _real_registry() -> dict:
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8-sig"))


def _real_scorecard() -> dict:
    return json.loads(SCORECARD_PATH.read_text(encoding="utf-8-sig"))


def _write(tmp_path: Path, name: str, data: dict) -> Path:
    p = tmp_path / name
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def _load(registry_path: Path | None = None, scorecard_path: Path | None = None):
    return exp.load_expectation_substrate(
        registry_path=registry_path or REGISTRY_PATH,
        scorecard_path=scorecard_path or SCORECARD_PATH,
    )


def _pf_criteria(registry: dict) -> list[dict]:
    """The mutable criterion dicts of the MSCA-PF instrument, in registry order."""
    (instrument,) = [
        i for i in registry["instruments"] if i["instrument_type"] == "MSCA-PF"
    ]
    return instrument["criteria"]


# --------------------------------------------------------------------------- #
# Option-tag parsing
# --------------------------------------------------------------------------- #


class TestOptionTagParsing:
    def test_inclusion_list(self):
        tag = exp.parse_option_tag(
            "MSCA Doctoral networks, Postdoctoral fellowships", source="registry"
        )
        assert tag.kind == exp.TAG_KIND_INCLUSION
        assert tag.variants == ("Doctoral networks", "Postdoctoral fellowships")
        assert tag.pf_applicable is True

    def test_inclusion_with_and(self):
        tag = exp.parse_option_tag(
            "MSCA Doctoral networks, Postdoctoral fellowships and Staff exchanges",
            source="registry",
        )
        assert tag.variants == (
            "Doctoral networks",
            "Postdoctoral fellowships",
            "Staff exchanges",
        )
        assert tag.pf_applicable is True

    def test_single_variant_pf(self):
        tag = exp.parse_option_tag("MSCA Postdoctoral fellowships", source="registry")
        assert tag.variants == ("Postdoctoral fellowships",)
        assert tag.pf_applicable is True

    def test_single_variant_non_pf(self):
        tag = exp.parse_option_tag("MSCA COFUND Choose Europe", source="scorecard")
        assert tag.variants == ("COFUND Choose Europe",)
        assert tag.pf_applicable is False

    def test_all_msca_except_pf_included(self):
        tag = exp.parse_option_tag(
            "all MSCA except Special needs allowances and COFUND Choose Europe",
            source="registry",
        )
        assert tag.kind == exp.TAG_KIND_ALL_EXCEPT
        assert tag.variants == ("Special needs allowances", "COFUND Choose Europe")
        assert tag.pf_applicable is True

    def test_all_msca_except_pf_excluded(self):
        tag = exp.parse_option_tag(
            "all MSCA except Postdoctoral fellowships", source="registry"
        )
        assert tag.pf_applicable is False

    def test_unknown_variant_raises(self):
        with pytest.raises(exp.ExpectationError, match="[Uu]nrecognised"):
            exp.parse_option_tag("MSCA Lunar fellowships", source="registry")

    def test_empty_tag_raises(self):
        with pytest.raises(exp.ExpectationError):
            exp.parse_option_tag("   ", source="registry")


# --------------------------------------------------------------------------- #
# The real committed registry + scorecard — the pinned substrate
# --------------------------------------------------------------------------- #


class TestRealSubstrate:
    def test_counts_pinned(self):
        substrate = _load()
        assert substrate.raw_count == EXPECTED_RAW_COUNT
        assert len(substrate.expectations) == EXPECTED_PF_COUNT
        assert len(substrate.excluded) == EXPECTED_RAW_COUNT - EXPECTED_PF_COUNT

    def test_keys_are_scorecard_aspect_ids_in_order(self):
        substrate = _load()
        assert tuple(e.expectation_key for e in substrate.expectations) == EXPECTED_KEYS

    def test_criterion_breakdown(self):
        substrate = _load()
        assert len(substrate.for_criterion("excellence")) == 4
        assert len(substrate.for_criterion("impact")) == 3
        assert len(substrate.for_criterion("implementation")) == 2

    def test_by_key_lookup(self):
        substrate = _load()
        e = substrate.by_key()["impl-host"]
        assert e.criterion_id == "implementation"
        assert "host institutions" in e.text

    def test_excluded_is_the_cofund_recruiting_item(self):
        substrate = _load()
        (excluded,) = substrate.excluded
        assert excluded.criterion_id == "implementation"
        assert "recruiting institutions" in excluded.registry_text
        assert excluded.option_tag.pf_applicable is False

    def test_text_is_scorecard_verbatim(self):
        substrate = _load()
        scorecard = _real_scorecard()
        aspect_texts = {
            a["id"]: a["text"]
            for c in scorecard["criteria"]
            for a in c["aspects"]
        }
        for e in substrate.expectations:
            assert e.text == aspect_texts[e.expectation_key]

    def test_tag_source_recorded(self):
        substrate = _load()
        by_key = substrate.by_key()
        # exc-obj carries an inline [OPTION …] tag in the registry.
        assert by_key["exc-obj"].option_tag.source == "registry"
        # exc-method is untagged in the registry; the scorecard supplies the tag.
        assert by_key["exc-method"].option_tag.source == "scorecard"

    def test_every_expectation_is_pf_applicable(self):
        substrate = _load()
        assert all(e.option_tag.pf_applicable for e in substrate.expectations)

    def test_section_ids_assigned_per_criterion(self):
        substrate = _load()
        for e in substrate.expectations:
            assert e.section_ids == exp.section_ids_for(e.criterion_id)

    def test_provenance_carried(self):
        substrate = _load()
        assert substrate.instrument_type == "MSCA-PF"
        assert substrate.scorecard_version == "2.2"


# --------------------------------------------------------------------------- #
# Fail-closed drift — a registry/scorecard edit breaks the load, not the metric
# --------------------------------------------------------------------------- #


class TestFailClosedDrift:
    def test_removed_row_raises(self, tmp_path):
        registry = _real_registry()
        _pf_criteria(registry)[0]["evaluator_expectations"].pop(0)
        path = _write(tmp_path, "registry.json", registry)
        with pytest.raises(exp.ExpectationError):
            _load(registry_path=path)

    def test_added_row_raises(self, tmp_path):
        registry = _real_registry()
        _pf_criteria(registry)[0]["evaluator_expectations"].append(
            "Novelty of the coffee machine [OPTION for MSCA Postdoctoral fellowships]"
        )
        path = _write(tmp_path, "registry.json", registry)
        with pytest.raises(exp.ExpectationError):
            _load(registry_path=path)

    def test_reworded_row_raises(self, tmp_path):
        registry = _real_registry()
        rows = _pf_criteria(registry)[0]["evaluator_expectations"]
        rows[0] = rows[0].replace("research and innovation", "R&I")
        path = _write(tmp_path, "registry.json", registry)
        with pytest.raises(exp.ExpectationError):
            _load(registry_path=path)

    def test_unrecognised_option_tag_raises(self, tmp_path):
        registry = _real_registry()
        rows = _pf_criteria(registry)[0]["evaluator_expectations"]
        rows[0] = rows[0].replace(
            "[OPTION for MSCA Doctoral networks, Postdoctoral fellowships]",
            "[OPTION for MSCA Lunar fellowships]",
        )
        path = _write(tmp_path, "registry.json", registry)
        with pytest.raises(exp.ExpectationError):
            _load(registry_path=path)

    def test_inline_tag_diverging_from_scorecard_raises(self, tmp_path):
        registry = _real_registry()
        rows = _pf_criteria(registry)[0]["evaluator_expectations"]
        rows[0] = rows[0].replace(
            "[OPTION for MSCA Doctoral networks, Postdoctoral fellowships]",
            "[OPTION for MSCA Doctoral networks]",
        )
        path = _write(tmp_path, "registry.json", registry)
        with pytest.raises(exp.ExpectationError, match="diverg"):
            _load(registry_path=path)

    def test_unmapped_criterion_raises(self, tmp_path):
        registry = _real_registry()
        _pf_criteria(registry)[0]["criterion_id"] = "Brilliance"
        path = _write(tmp_path, "registry.json", registry)
        with pytest.raises(exp.ExpectationError, match="criterion"):
            _load(registry_path=path)

    def test_missing_instrument_raises(self, tmp_path):
        registry = _real_registry()
        registry["instruments"][0]["instrument_type"] = "MSCA-DN"
        path = _write(tmp_path, "registry.json", registry)
        with pytest.raises(exp.ExpectationError, match="MSCA-PF"):
            _load(registry_path=path)

    def test_missing_registry_file_raises(self, tmp_path):
        with pytest.raises(exp.ExpectationError):
            _load(registry_path=tmp_path / "nope.json")

    def test_invalid_registry_json_raises(self, tmp_path):
        p = tmp_path / "registry.json"
        p.write_text("{not json", encoding="utf-8")
        with pytest.raises(exp.ExpectationError):
            _load(registry_path=p)

    def test_missing_scorecard_file_raises(self, tmp_path):
        with pytest.raises(exp.ExpectationError):
            _load(scorecard_path=tmp_path / "nope.json")

    def test_stale_scorecard_aspect_not_pf_raises(self, tmp_path):
        # exc-method is untagged in the registry, so the scorecard's tag governs;
        # a scorecard tag that excludes PF must fail the load, not shrink the 9.
        scorecard = _real_scorecard()
        for c in scorecard["criteria"]:
            for a in c["aspects"]:
                if a["id"] == "exc-method":
                    a["option_tag"] = "MSCA Doctoral networks"
        path = _write(tmp_path, "scorecard.json", scorecard)
        with pytest.raises(exp.ExpectationError):
            _load(scorecard_path=path)

    def test_excluded_item_becoming_pf_applicable_raises(self, tmp_path):
        scorecard = _real_scorecard()
        scorecard["excluded_for_pf"][0]["option_tag"] = "MSCA Postdoctoral fellowships"
        path = _write(tmp_path, "scorecard.json", scorecard)
        with pytest.raises(exp.ExpectationError):
            _load(scorecard_path=path)

    def test_drifted_fixture_copy_full_round(self, tmp_path):
        # A verbatim copy of both files loads identically (the fixture-registry
        # sanity check); the drifted copy — one row silently dropped — fails.
        reg_path = _write(tmp_path, "registry.json", _real_registry())
        sc_path = _write(tmp_path, "scorecard.json", _real_scorecard())
        substrate = _load(registry_path=reg_path, scorecard_path=sc_path)
        assert len(substrate.expectations) == EXPECTED_PF_COUNT

        drifted = _real_registry()
        _pf_criteria(drifted)[2]["evaluator_expectations"].pop()
        drifted_path = _write(tmp_path, "drifted.json", drifted)
        with pytest.raises(exp.ExpectationError):
            _load(registry_path=drifted_path, scorecard_path=sc_path)


# --------------------------------------------------------------------------- #
# Criterion ↔ section artifact map
# --------------------------------------------------------------------------- #


class TestCriterionSectionMap:
    def test_section_ids(self):
        assert exp.section_ids_for("excellence") == ("excellence_section",)
        assert exp.section_ids_for("impact") == ("impact_section",)
        assert exp.section_ids_for("implementation") == ("implementation_section",)

    def test_unmapped_criterion_raises(self):
        with pytest.raises(exp.ExpectationError, match="criterion"):
            exp.section_ids_for("brilliance")

    def test_live_section_paths_resolve(self):
        if not any((REPO_ROOT / "docs" / "tier5_deliverables" / "proposal_sections").glob("*.json")):
            pytest.skip("no live Tier 5 sections in this checkout (empty project instantiation)")
        for criterion in ("excellence", "impact", "implementation"):
            paths = exp.section_paths_for(criterion, repo_root=REPO_ROOT)
            assert all(p.is_file() for p in paths)

    def test_golden_paths_resolve(self):
        if not any((REPO_ROOT / "harness" / "regression_baselines").glob("*.golden.json")):
            pytest.skip("no committed E4 goldens in this checkout; refreeze after the next run")
        for criterion in ("excellence", "impact", "implementation"):
            paths = exp.golden_paths_for(criterion, repo_root=REPO_ROOT)
            assert all(p.is_file() for p in paths)
            assert all(p.name.endswith(".golden.json") for p in paths)

    def test_missing_artifact_fails_closed(self, tmp_path):
        with pytest.raises(exp.ExpectationError, match="not found"):
            exp.section_paths_for("excellence", repo_root=tmp_path)
