"""
Versioned pre-evaluation profile — the configuration bundle the harness grades under.

Four bars from the ticket:

1. the default profile reproduces the harness's original defaults (instrument
   type, tag grammar, criterion-to-section map, bundled file paths) — the
   existing harness tests run against it;
2. a second, synthetic profile with different criteria names, a different
   scale and a different threshold drives the rubric grading path with **no
   Python change** and yields different verdicts on the same candidate;
3. the harness package carries no instrument-name literal outside the profile
   loader and the default profile file;
4. the profile version moves when any bundled component changes.

Everything runs offline; the grading path uses the injectable fake backend.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import harness.rubric as hr
from harness import profile as pf
from harness.judge import Judge, JudgeConfig
from harness.provenance import ProvenanceLog
from harness.rubrics import RubricError, load_profile_bundle, rubric_fingerprint
from runner.working_assumptions import WorkingAssumptions

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROFILE_PATH = REPO_ROOT / pf.DEFAULT_PROFILE_PATH

EMPTY_WA = WorkingAssumptions(present=True)
EMPTY_SPINE = hr.SpineRegistry(facts=())


def _write_json(path: Path, data) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _default_document() -> dict:
    return _read_json(DEFAULT_PROFILE_PATH)


def _absolute_copy(document: dict) -> dict:
    """The default profile document with every bundled path made absolute, so
    a copy written under a temporary directory still binds the real files."""
    doc = json.loads(json.dumps(document))
    doc["registry_path"] = str(REPO_ROOT / doc["registry_path"])
    doc["scorecard"]["path"] = str(REPO_ROOT / doc["scorecard"]["path"])
    doc["rubric_set"]["path"] = str(REPO_ROOT / doc["rubric_set"]["path"])
    return doc


# --------------------------------------------------------------------------- #
# 1. The default profile reproduces the original defaults
# --------------------------------------------------------------------------- #


class TestDefaultProfile:
    def test_parses_and_names_the_original_defaults(self):
        profile = pf.default_profile(REPO_ROOT)
        assert profile.profile_id == "msca_pf_default"
        assert profile.instrument.registry_instrument_type == "MSCA-PF"
        assert profile.grammar.applicable_variant == "Postdoctoral fellowships"
        assert profile.grammar.known_variants == frozenset(
            {
                "Doctoral networks",
                "Postdoctoral fellowships",
                "Staff exchanges",
                "COFUND Choose Europe",
                "Special needs allowances",
            }
        )
        assert profile.grammar.variant_prefix == "MSCA "
        assert profile.criterion_ids == ("excellence", "impact", "implementation")
        assert profile.section_ids_for("excellence") == ("excellence_section",)
        assert profile.section_ids_for("impact") == ("impact_section",)
        assert profile.section_ids_for("implementation") == ("implementation_section",)
        assert profile.criterion_id_for_registry("Excellence") == "excellence"
        assert profile.registry_path == Path(
            "docs/tier2a_instrument_schemas/extracted/evaluator_expectation_registry.json"
        )
        assert profile.scorecard.path == Path("harness/evaluator_scorecard_msca_pf.json")
        assert profile.rubric_set.path == Path("harness/rubrics_msca_pf.json")

    def test_bundle_loads_every_component_and_pins_them(self):
        bundle = load_profile_bundle(repo_root=REPO_ROOT)
        assert bundle.profile_id == "msca_pf_default"
        assert len(bundle.rubric_set.rubrics) == 9
        assert bundle.substrate.scorecard_id == bundle.profile.scorecard.component_id
        assert bundle.substrate.scorecard_version == bundle.profile.scorecard.version
        assert bundle.rubric_set.rubric_set_id == bundle.profile.rubric_set.component_id
        assert bundle.rubric_set.version == bundle.profile.rubric_set.version
        assert bundle.scoring.scale == "0-5, one decimal place"
        assert bundle.scoring.overall_threshold == 70
        assert bundle.scoring.overall_max == 100
        assert bundle.scoring.weights == {"excellence": 50, "impact": 30, "implementation": 20}
        assert bundle.version.startswith("sha256:")
        assert bundle.scorecard_hash.startswith("sha256:")

    def test_rubrics_carry_the_profile_form_name(self):
        bundle = load_profile_bundle(repo_root=REPO_ROOT)
        for rubric in bundle.rubric_set.rubrics:
            assert rubric.form_name == bundle.profile.instrument.form_name

    def test_report_carries_the_profile_pin(self):
        bundle = load_profile_bundle(repo_root=REPO_ROOT)
        report = hr.build_rubric_report((), rubric_set=bundle.rubric_set, profile=bundle)
        data = report.to_dict()
        assert data["profile_id"] == "msca_pf_default"
        assert data["profile_version"] == bundle.version
        assert "profile: msca_pf_default" in hr.render_report(data)


# --------------------------------------------------------------------------- #
# 4. The profile version moves with any bundled component
# --------------------------------------------------------------------------- #


class TestProfileVersion:
    def test_stable_across_loads(self):
        a = load_profile_bundle(repo_root=REPO_ROOT)
        b = load_profile_bundle(repo_root=REPO_ROOT)
        assert a.version == b.version

    def test_absolute_copy_reproduces_a_different_document_hash_only(self, tmp_path):
        # A copy with absolute paths is a different document (the paths are
        # part of it), so its version differs — the pins still bind.
        copy = _write_json(tmp_path / "profile.json", _absolute_copy(_default_document()))
        bundle = load_profile_bundle(copy)
        original = load_profile_bundle(repo_root=REPO_ROOT)
        assert bundle.rubric_set.fingerprint == original.rubric_set.fingerprint
        assert bundle.scorecard_hash == original.scorecard_hash
        assert bundle.version != original.version

    def test_profile_document_change_moves_the_version(self, tmp_path):
        doc = _absolute_copy(_default_document())
        before = load_profile_bundle(_write_json(tmp_path / "a.json", doc)).version
        doc["label"] = doc["label"] + " (edited)"
        after = load_profile_bundle(_write_json(tmp_path / "b.json", doc)).version
        assert before != after

    def test_rubric_set_change_moves_the_version(self, tmp_path):
        doc = _absolute_copy(_default_document())
        before = load_profile_bundle(_write_json(tmp_path / "a.json", doc)).version
        rubrics = _read_json(Path(doc["rubric_set"]["path"]))
        rubrics["rubrics"][0]["rubric"] += " Tightened wording."
        doc["rubric_set"]["path"] = str(_write_json(tmp_path / "rubrics.json", rubrics))
        after = load_profile_bundle(_write_json(tmp_path / "b.json", doc)).version
        assert before != after

    def test_scorecard_change_moves_the_version(self, tmp_path):
        doc = _absolute_copy(_default_document())
        before = load_profile_bundle(_write_json(tmp_path / "a.json", doc)).version
        scorecard = _read_json(Path(doc["scorecard"]["path"]))
        scorecard["scoring"]["overall_threshold"] = 75
        doc["scorecard"]["path"] = str(_write_json(tmp_path / "scorecard.json", scorecard))
        bundle = load_profile_bundle(_write_json(tmp_path / "b.json", doc))
        assert bundle.version != before
        assert bundle.scoring.overall_threshold == 75

    def test_scorecard_formatting_does_not_move_the_scorecard_hash(self, tmp_path):
        doc = _absolute_copy(_default_document())
        before = load_profile_bundle(_write_json(tmp_path / "a.json", doc)).scorecard_hash
        scorecard = _read_json(Path(doc["scorecard"]["path"]))
        reflowed = tmp_path / "scorecard.json"
        reflowed.write_text(json.dumps(scorecard, sort_keys=True), encoding="utf-8")
        doc["scorecard"]["path"] = str(reflowed)
        after = load_profile_bundle(_write_json(tmp_path / "b.json", doc)).scorecard_hash
        assert before == after


# --------------------------------------------------------------------------- #
# Fail-closed: the pins are a bijection, the document is validated
# --------------------------------------------------------------------------- #


class TestFailClosed:
    def test_scorecard_pin_mismatch_refuses(self, tmp_path):
        doc = _absolute_copy(_default_document())
        doc["scorecard"]["version"] = "1.9"
        with pytest.raises(RubricError, match="pins scorecard"):
            load_profile_bundle(_write_json(tmp_path / "p.json", doc))

    def test_rubric_set_pin_mismatch_refuses(self, tmp_path):
        doc = _absolute_copy(_default_document())
        doc["rubric_set"]["rubric_set_id"] = "someone_elses_rubrics"
        with pytest.raises(RubricError, match="pins rubric set"):
            load_profile_bundle(_write_json(tmp_path / "p.json", doc))

    def test_missing_profile_refuses(self, tmp_path):
        with pytest.raises(pf.ProfileError, match="not found"):
            pf.load_profile(tmp_path / "absent.json")
        with pytest.raises(RubricError, match="not found"):
            load_profile_bundle(tmp_path / "absent.json")

    def test_applicable_variant_outside_vocabulary_refuses(self, tmp_path):
        doc = _default_document()
        doc["option_tag_grammar"]["applicable_variant"] = "Lunar fellowships"
        with pytest.raises(pf.ProfileError, match="applicable_variant"):
            pf.load_profile(_write_json(tmp_path / "p.json", doc))

    def test_criteria_required(self, tmp_path):
        doc = _default_document()
        doc["criteria"] = []
        with pytest.raises(pf.ProfileError, match="criteria"):
            pf.load_profile(_write_json(tmp_path / "p.json", doc))

    def test_duplicate_criterion_refuses(self, tmp_path):
        doc = _default_document()
        doc["criteria"].append(dict(doc["criteria"][0]))
        with pytest.raises(pf.ProfileError, match="duplicate"):
            pf.load_profile(_write_json(tmp_path / "p.json", doc))

    def test_scoring_without_weights_refuses(self):
        with pytest.raises(pf.ProfileError, match="weight_pct"):
            pf.parse_scoring(
                {
                    "scoring": {"scale": "0-5", "overall_threshold": 70, "overall_max": 100},
                    "criteria": [{"id": "excellence"}],
                },
                ("excellence",),
            )

    def test_threshold_outside_maximum_refuses(self):
        with pytest.raises(pf.ProfileError, match="overall_threshold"):
            pf.parse_scoring(
                {
                    "scoring": {"scale": "0-5", "overall_threshold": 120, "overall_max": 100},
                    "criteria": [{"id": "excellence", "weight_pct": 100}],
                },
                ("excellence",),
            )


# --------------------------------------------------------------------------- #
# 3. No instrument-name literal outside the loader and the default profile
# --------------------------------------------------------------------------- #

_INSTRUMENT_LITERAL = re.compile(r"msca|postdoctoral|cofund|european fellowship", re.IGNORECASE)


class TestNoInstrumentLiterals:
    def test_harness_python_carries_no_instrument_name(self):
        offenders: list[str] = []
        for py in (REPO_ROOT / "harness").rglob("*.py"):
            if py.name == "profile.py":
                continue
            for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
                if _INSTRUMENT_LITERAL.search(line):
                    offenders.append(f"{py.relative_to(REPO_ROOT)}:{lineno}: {line.strip()}")
        assert not offenders, "instrument literals outside the profile loader:\n" + "\n".join(
            offenders
        )


# --------------------------------------------------------------------------- #
# 2. A synthetic second profile drives the grading path with no Python change
# --------------------------------------------------------------------------- #

CANDIDATE_TEXT = (
    "The modelling objectives are original and go beyond current practice.\n\n"
    "The modelling method reuses partner tooling across the consortium."
)

LEDGER = [
    ("C01", "The modelling objective is beyond current practice.", "confirmed", "docs/t3/a.json"),
]


def _section(sub_section_ids: list[str]) -> dict:
    return {
        "sub_sections": [
            {"sub_section_id": sid, "title": f"Part {sid}", "content": CANDIDATE_TEXT}
            for sid in sub_section_ids
        ],
        "validation_status": {
            "claim_statuses": [
                {"claim_id": cid, "claim_summary": s, "status": st, "source_ref": ref}
                for cid, s, st, ref in LEDGER
            ]
        },
    }


def _synthetic_world(root: Path) -> Path:
    """A call-neutral instrument ``SYN-ALPHA`` with two criteria (Novelty,
    Reach), a 0-10 scale, a 60/100 threshold, a distinct tag grammar, and a
    rubric pass threshold of 0.9 (the default profile's rubrics use 0.6)."""
    registry = {
        "instruments": [
            {
                "instrument_type": "SYN-ALPHA",
                "criteria": [
                    {
                        "criterion_id": "Novelty",
                        "evaluator_expectations": [
                            "Originality of the modelling objectives "
                            "[OPTION for Track alpha, Track beta]",
                            "Fit of the modelling method",
                        ],
                    },
                    {
                        "criterion_id": "Reach",
                        "evaluator_expectations": [
                            "Breadth of the modelling uptake "
                            "[OPTION for all tracks except Track gamma]",
                            "Cost of the recruiting desk [OPTION for Track gamma]",
                        ],
                    },
                ],
            }
        ]
    }
    scorecard = {
        "scorecard_id": "syn_alpha_scorecard",
        "provenance": {"version": "0.1"},
        "scoring": {
            "scale": "0-10, integers",
            "levels": {"0": "none", "10": "full"},
            "overall_threshold": 60,
            "overall_max": 100,
        },
        "criteria": [
            {
                "id": "novelty",
                "name": "Novelty",
                "weight_pct": 70,
                "aspects": [
                    {
                        "id": "nov-obj",
                        "text": "Originality of the modelling objectives",
                        "option_tag": "Track alpha, Track beta",
                        "source_page": 1,
                    },
                    {
                        "id": "nov-method",
                        "text": "Fit of the modelling method",
                        "option_tag": "Track alpha",
                        "source_page": 1,
                    },
                ],
            },
            {
                "id": "reach",
                "name": "Reach",
                "weight_pct": 30,
                "aspects": [
                    {
                        "id": "reach-uptake",
                        "text": "Breadth of the modelling uptake",
                        "option_tag": "all tracks except Track gamma",
                        "source_page": 2,
                    }
                ],
            },
        ],
        "excluded_aspects": [
            {
                "criterion": "reach",
                "text": "Cost of the recruiting desk",
                "option_tag": "Track gamma",
                "reason": "gamma track only",
            }
        ],
    }

    def rubric(key: str, criterion: str, text: str) -> dict:
        return {
            "expectation_key": key,
            "criterion_id": criterion,
            "expectation_text": text,
            "rubric": "Integrity-framed: addressed AND grounded.",
            "evaluation_steps": ["Check the spans.", "Check the claims."],
            "pass_threshold": 0.9,
            "selection_terms": ["modelling"],
            "anchor_sub_section_ids": ["A"],
        }

    rubrics = {
        "rubric_set_id": "syn_alpha_rubrics",
        "version": "0.1.0",
        "scorecard_id": "syn_alpha_scorecard",
        "scorecard_version": "0.1",
        "rubrics": [
            rubric("nov-obj", "novelty", "Originality of the modelling objectives"),
            rubric("nov-method", "novelty", "Fit of the modelling method"),
            rubric("reach-uptake", "reach", "Breadth of the modelling uptake"),
        ],
    }
    profile = {
        "profile_id": "syn_alpha",
        "label": "Synthetic alpha-track profile",
        "instrument": {
            "registry_instrument_type": "SYN-ALPHA",
            "name": "Synthetic Alpha Track",
            "form_name": "Synthetic Alpha Assessment Form",
        },
        "option_tag_grammar": {
            "applicable_variant": "Track alpha",
            "known_variants": ["Track alpha", "Track beta", "Track gamma"],
            "variant_prefix": "",
            "all_except_prefix": "all tracks except ",
        },
        "criteria": [
            {"id": "novelty", "registry_criterion_id": "Novelty", "section_ids": ["novelty_section"]},
            {"id": "reach", "registry_criterion_id": "Reach", "section_ids": ["reach_section"]},
        ],
        "registry_path": "syn/registry.json",
        "scorecard": {"path": "syn/scorecard.json", "scorecard_id": "syn_alpha_scorecard", "version": "0.1"},
        "rubric_set": {"path": "syn/rubrics.json", "rubric_set_id": "syn_alpha_rubrics", "version": "0.1.0"},
    }
    _write_json(root / "syn/registry.json", registry)
    _write_json(root / "syn/scorecard.json", scorecard)
    _write_json(root / "syn/rubrics.json", rubrics)
    return _write_json(root / "syn/profile.json", profile)


def _candidate_repo(tmp_path: Path) -> Path:
    """One candidate under both section layouts, plus the claim sources."""
    root = tmp_path / "repo"
    sections = root / "docs/tier5_deliverables/proposal_sections"
    default = load_profile_bundle(repo_root=REPO_ROOT)
    anchors: dict[str, list[str]] = {}
    for rubric in default.rubric_set.rubrics:
        for sid in default.profile.section_ids_for(rubric.criterion_id):
            anchors.setdefault(sid, []).extend(rubric.anchor_sub_section_ids)
    for sid, ids in anchors.items():
        _write_json(sections / f"{sid}.json", _section(sorted(set(ids))))
    for sid in ("novelty_section", "reach_section"):
        _write_json(sections / f"{sid}.json", _section(["A"]))
    _write_json(root / "docs/t3/a.json", {"text": "The modelling objective is beyond current practice."})
    return root


_THRESHOLD_RE = re.compile(r"at or above ([0-9.]+) corresponds to a pass")


class ThresholdAwareBackend:
    """A fake assessor that honours the threshold the system prompt states:
    the same candidate scores 0.75 everywhere, so the verdict is decided by
    the profile's rubric threshold, never by Python."""

    SCORE = 0.75

    def __init__(self) -> None:
        self.calls = 0
        self.thresholds: set[float] = set()

    def __call__(self, messages):
        self.calls += 1
        system = messages[0]["content"]
        match = _THRESHOLD_RE.search(system)
        if match:
            threshold = float(match.group(1))
            self.thresholds.add(threshold)
            passed = self.SCORE >= threshold
        else:  # a grounding (faithfulness) call
            passed = True
        return {
            "content": json.dumps(
                {"passed": passed, "score": self.SCORE, "rationale": "scripted"}
            )
        }


def _judge(tmp_path: Path, backend) -> Judge:
    return Judge(
        JudgeConfig(model="fake-judge", version="pin-1"),
        backend=backend,
        provenance_log=ProvenanceLog(tmp_path / "provenance.jsonl"),
        clock=lambda: "2026-09-24T00:00:00+00:00",
    )


def _grade(tmp_path: Path, root: Path, bundle):
    backend = ThresholdAwareBackend()
    cells = hr.grade_all(
        _judge(tmp_path, backend),
        bundle.rubric_set,
        EMPTY_SPINE,
        repo_root=root,
        working_assumptions=EMPTY_WA,
        profile=bundle.profile,
    )
    return cells, backend


class TestSyntheticProfile:
    def test_loads_with_its_own_grammar_criteria_scale_and_threshold(self, tmp_path):
        root = _candidate_repo(tmp_path)
        bundle = load_profile_bundle(_synthetic_world(root), repo_root=root)
        assert bundle.profile_id == "syn_alpha"
        assert tuple(r.expectation_key for r in bundle.rubric_set.rubrics) == (
            "nov-obj",
            "nov-method",
            "reach-uptake",
        )
        assert bundle.substrate.raw_count == 4
        (excluded,) = bundle.substrate.excluded
        assert excluded.present_in_registry is True
        assert excluded.option_tag.applicable is False
        assert bundle.scoring.scale == "0-10, integers"
        assert bundle.scoring.overall_threshold == 60
        assert bundle.scoring.weights == {"novelty": 70, "reach": 30}
        assert all(r.pass_threshold == 0.9 for r in bundle.rubric_set.rubrics)
        assert all(
            r.form_name == "Synthetic Alpha Assessment Form" for r in bundle.rubric_set.rubrics
        )

    def test_grading_path_yields_different_verdicts_on_the_same_candidate(self, tmp_path):
        root = _candidate_repo(tmp_path)
        default = load_profile_bundle(repo_root=REPO_ROOT)
        synthetic = load_profile_bundle(_synthetic_world(root), repo_root=root)

        default_cells, default_backend = _grade(tmp_path / "d", root, default)
        synthetic_cells, synthetic_backend = _grade(tmp_path / "s", root, synthetic)

        # The default profile grades its 9 expectations; the synthetic its 3.
        assert len(default_cells) == 9
        assert len(synthetic_cells) == 3
        assert {c.criterion_id for c in synthetic_cells} == {"novelty", "reach"}
        assert {c.coverage.section_id for c in synthetic_cells} == {
            "novelty_section",
            "reach_section",
        }
        # The assessor saw each profile's own threshold in the prompt…
        assert default_backend.thresholds == {0.6}
        assert synthetic_backend.thresholds == {0.9}
        # …and the same 0.75 candidate passes under one and fails under the other.
        assert all(c.coverage.judge_passed is True for c in default_cells)
        assert all(c.coverage.judge_passed is False for c in synthetic_cells)
        assert all(c.covered for c in default_cells)
        assert not any(c.covered for c in synthetic_cells)

    def test_synthetic_report_pins_the_synthetic_profile(self, tmp_path):
        root = _candidate_repo(tmp_path)
        synthetic = load_profile_bundle(_synthetic_world(root), repo_root=root)
        cells, _ = _grade(tmp_path, root, synthetic)
        report = hr.build_rubric_report(cells, rubric_set=synthetic.rubric_set, profile=synthetic)
        data = report.to_dict()
        assert data["profile_id"] == "syn_alpha"
        assert data["profile_version"] == synthetic.version
        assert data["rubric_set_id"] == "syn_alpha_rubrics"
        assert data["advisory"] is True and data["blocking"] is False

    def test_cells_record_the_synthetic_rubric_fingerprints(self, tmp_path):
        root = _candidate_repo(tmp_path)
        synthetic = load_profile_bundle(_synthetic_world(root), repo_root=root)
        cells, _ = _grade(tmp_path, root, synthetic)
        recorded = {c.coverage.rubric_fingerprint for c in cells}
        assert recorded == {rubric_fingerprint(r) for r in synthetic.rubric_set.rubrics}
