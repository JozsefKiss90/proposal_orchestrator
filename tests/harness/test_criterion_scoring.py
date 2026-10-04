"""
Criterion scoring (``harness.criterion_scoring``) — spec PE-04.

Everything runs offline against a call-neutral synthetic profile: three
criteria, three sections, and a criterion appendix mapping that hands one
criterion a sub-section another criterion's section owns.  The assessor is a
scripted backend; the clock is frozen; provenance lands in ``tmp_path``.

What is pinned, in the spec's words:

* the scorer reads the COMPLETE criterion section verbatim, never a pack;
* every score names its complete input (section bytes + appendix rows) by
  hash, and a completeness check covers that whole input;
* the appendix mapping version is recorded on every score;
* no criterion score is produced from aspect findings alone;
* N=5, median and spread labelled within-assessor repeatability;
* ``S = 10E + 6I + 4Q`` with both thresholds checked, and
  4.20 / 4.50 / 4.20 -> 85.80 on the shipped MSCA-DN scorecard;
* no code path derives a criterion score from cell arithmetic.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import harness.criterion_scoring as cs
from harness.judge import Judge, JudgeConfig, JudgeResponseError
from harness.provenance import ProvenanceLog
from harness.rubrics import RubricError, load_profile_bundle

REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN = "2026-10-04T12:00:00+00:00"


def _write_json(path: Path, data) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


CRITERIA = [
    ("novelty", "Novelty", "nov-obj", "Originality of the modelling objectives", 50),
    ("reach", "Reach", "reach-uptake", "Breadth of the modelling uptake", 30),
    ("feasibility", "Feasibility", "feas-plan", "Credibility of the modelling plan", 20),
]

MAPPING_ROWS = [
    {
        "criterion_id": "novelty",
        "aspect_id": "nov-obj",
        "table": "Table F.1 - Plan rows",
        "candidate_sub_section": "F.2",
        "rows": "every plan row",
        "status": "Confirmed",
    },
    {
        "criterion_id": "feasibility",
        "aspect_id": "feas-plan",
        "table": "Table F.1 - Plan rows",
        "candidate_sub_section": "F.2",
        "rows": "every plan row (own section)",
        "status": "Confirmed",
    },
]


def _synthetic_world(root: Path, *, with_mapping: bool = True, mapping_rows=None) -> Path:
    registry = {
        "instruments": [
            {
                "instrument_type": "SYN-TRI",
                "criteria": [
                    {"criterion_id": rid, "evaluator_expectations": [text]}
                    for _cid, rid, _key, text, _w in CRITERIA
                ],
            }
        ]
    }
    scorecard = {
        "scorecard_id": "syn_tri_scorecard",
        "provenance": {"version": "0.1"},
        "scoring": {
            "scale": "0-5, one decimal place",
            "levels": {str(i): f"level {i}" for i in range(6)},
            "overall_threshold": 70,
            "overall_max": 100,
            "individual_threshold": 3,
        },
        "criteria": [
            {
                "id": cid,
                "name": rid,
                "weight_pct": weight,
                "aspects": [{"id": key, "text": text, "option_tag": "Track one", "source_page": 1}],
            }
            for cid, rid, key, text, weight in CRITERIA
        ],
        "excluded_aspects": [],
    }
    mapping = {
        "mapping_id": "syn_tri_mapping",
        "rubric_set_id": "syn_tri_rubrics",
        "rubric_set_version": "0.1.0",
        "scorecard_id": "syn_tri_scorecard",
        "rows": MAPPING_ROWS if mapping_rows is None else mapping_rows,
    }
    mapping_bytes = json.dumps(mapping, ensure_ascii=False, indent=2).encode("utf-8")
    rubrics = {
        "rubric_set_id": "syn_tri_rubrics",
        "version": "0.1.0",
        "scorecard_id": "syn_tri_scorecard",
        "scorecard_version": "0.1",
        "rubrics": [
            {
                "expectation_key": key,
                "criterion_id": cid,
                "expectation_text": text,
                "rubric": "Integrity-framed: addressed AND grounded.",
                "evaluation_steps": ["Check the spans.", "Check the claims."],
                "pass_threshold": 0.7,
                "selection_terms": ["modelling"],
                "anchor_sub_section_ids": [f"{cid[0].upper()}.1"],
            }
            for cid, _rid, key, text, _w in CRITERIA
        ],
    }
    if with_mapping:
        rubrics["criterion_appendix_mapping"] = {
            "path": "syn/mapping.json",
            "sha256": hashlib.sha256(mapping_bytes).hexdigest(),
        }
    profile = {
        "profile_id": "syn_tri",
        "label": "Synthetic three-criterion profile",
        "instrument": {
            "registry_instrument_type": "SYN-TRI",
            "name": "Synthetic Tri Track",
            "form_name": "Synthetic Tri Assessment Form",
        },
        "option_tag_grammar": {
            "applicable_variant": "Track one",
            "known_variants": ["Track one", "Track two"],
            "variant_prefix": "",
            "all_except_prefix": "all tracks except ",
        },
        "criteria": [
            {"id": cid, "registry_criterion_id": rid, "section_ids": [f"{cid}_section"]}
            for cid, rid, _key, _text, _w in CRITERIA
        ],
        "registry_path": "syn/registry.json",
        "scorecard": {"path": "syn/scorecard.json", "scorecard_id": "syn_tri_scorecard", "version": "0.1"},
        "rubric_set": {"path": "syn/rubrics.json", "rubric_set_id": "syn_tri_rubrics", "version": "0.1.0"},
    }
    if with_mapping:
        profile["criterion_appendix_mapping"] = {"path": "syn/mapping.json"}
    _write_json(root / "syn/registry.json", registry)
    _write_json(root / "syn/scorecard.json", scorecard)
    _write_json(root / "syn/rubrics.json", rubrics)
    (root / "syn/mapping.json").write_bytes(mapping_bytes)
    return _write_json(root / "syn/profile.json", profile)


def _section(sub_sections: list[tuple[str, str]]) -> dict:
    return {
        "sub_sections": [
            {"sub_section_id": sid, "title": f"Part {sid}", "content": text}
            for sid, text in sub_sections
        ],
        "validation_status": {"claim_statuses": []},
    }


NOVELTY_TEXT = "The modelling objectives are original.\n\nMARKER-NOVELTY-BODY paragraph."
REACH_TEXT = "The modelling uptake spans three sectors.\n\nMARKER-REACH-BODY paragraph."
FEAS_TEXT = "The modelling plan is credible.\n\nMARKER-FEAS-BODY paragraph."
PLAN_ROWS = "| Task | Month |\n\n| T1 MARKER-PLAN-ROW | M3 |\n\n| T2 | M9 |"


def _candidate(tmp_path: Path, *, drop: str | None = None, without_f2: bool = False) -> Path:
    root = tmp_path / "candidate"
    sections = {
        "novelty_section": [("N.1", NOVELTY_TEXT)],
        "reach_section": [("R.1", REACH_TEXT)],
        "feasibility_section": [("F.1", FEAS_TEXT)] + ([] if without_f2 else [("F.2", PLAN_ROWS)]),
    }
    for sid, subs in sections.items():
        if sid == drop:
            continue
        _write_json(root / f"{sid}.json", _section(subs))
    return root


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    root = tmp_path_factory.mktemp("world")
    return load_profile_bundle(_synthetic_world(root), repo_root=root)


def _score_json(score, shortcomings=("one named shortcoming",), rationale="scripted"):
    return json.dumps(
        {
            "score": score,
            "shortcomings": list(shortcomings),
            "strengths": ["a strength"],
            "rationale": rationale,
        }
    )


class ScriptedBackend:
    def __init__(self, *contents: str):
        self.contents = list(contents) or [_score_json(4.0)]
        self.calls = 0
        self.prompts: list[tuple[str, str]] = []

    def __call__(self, messages):
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        user = "\n".join(m["content"] for m in messages if m["role"] == "user")
        self.prompts.append((system, user))
        out = self.contents[self.calls % len(self.contents)]
        self.calls += 1
        return {"content": out}


def _judge(tmp_path: Path, backend) -> Judge:
    return Judge(
        JudgeConfig(model="fake-assessor", version="pin-7"),
        backend=backend,
        provenance_log=ProvenanceLog(tmp_path / "provenance.jsonl"),
        clock=lambda: FROZEN,
    )


def _inputs(bundle, candidate_dir, **kw):
    import harness.blind_assessment as ba

    candidate = ba.load_candidate(candidate_dir, bundle.profile)
    return {
        cid: cs.build_criterion_input(bundle, candidate, cid, **kw)
        for cid in bundle.profile.criterion_ids
    }


# --------------------------------------------------------------------------- #
# 1. The mapping is loaded, pinned and versioned
# --------------------------------------------------------------------------- #


class TestMapping:
    def test_bundle_carries_the_mapping_and_its_version(self, bundle):
        mapping = bundle.appendix_mapping
        assert mapping is not None
        assert mapping.mapping_id == "syn_tri_mapping"
        assert len(mapping.rows) == 2
        assert mapping.version == {
            "mapping_id": "syn_tri_mapping",
            "rubric_set_id": "syn_tri_rubrics",
            "rubric_set_version": "0.1.0",
            "sha256": mapping.sha256,
        }
        assert len(mapping.sha256) == 64

    def test_a_mapping_whose_bytes_drift_from_the_pin_refuses_to_load(self, tmp_path):
        profile_path = _synthetic_world(tmp_path)
        mapping_path = tmp_path / "syn/mapping.json"
        data = json.loads(mapping_path.read_text(encoding="utf-8"))
        data["rows"][0]["rows"] = "a silently widened row set"
        mapping_path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(RubricError, match="sha256"):
            load_profile_bundle(profile_path, repo_root=tmp_path)

    def test_a_mapping_declared_by_the_profile_but_unpinned_by_the_rubric_set_refuses(self, tmp_path):
        profile_path = _synthetic_world(tmp_path)
        rubrics_path = tmp_path / "syn/rubrics.json"
        data = json.loads(rubrics_path.read_text(encoding="utf-8"))
        del data["criterion_appendix_mapping"]
        rubrics_path.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(RubricError, match="pin"):
            load_profile_bundle(profile_path, repo_root=tmp_path)

    def test_a_profile_without_a_mapping_loads_with_none(self, tmp_path):
        profile_path = _synthetic_world(tmp_path, with_mapping=False)
        b = load_profile_bundle(profile_path, repo_root=tmp_path)
        assert b.appendix_mapping is None

    def test_the_shipped_dn_profile_loads_its_mapping(self):
        b = load_profile_bundle(
            REPO_ROOT / "harness/profiles/msca_dn_2026_default.json", repo_root=REPO_ROOT
        )
        assert b.appendix_mapping is not None
        assert b.appendix_mapping.rubric_set_version == b.rubric_set.version
        assert {r.criterion_id for r in b.appendix_mapping.rows} == {
            "excellence", "impact", "implementation"
        }


# --------------------------------------------------------------------------- #
# 2. The criterion input: complete section + declared appendix, hashed whole
# --------------------------------------------------------------------------- #


class TestCriterionInput:
    def test_the_input_is_the_whole_section_verbatim_plus_the_appendix(self, tmp_path, bundle):
        inputs = _inputs(bundle, _candidate(tmp_path))
        novelty = inputs["novelty"]
        assert "MARKER-NOVELTY-BODY" in novelty.text
        assert "The modelling objectives are original." in novelty.text
        assert "MARKER-PLAN-ROW" in novelty.text, "the declared appendix row travels with the section"
        assert "MARKER-FEAS-BODY" not in novelty.text, "only the declared sub-section is appended"
        assert novelty.complete is True
        assert novelty.incompleteness == ()
        (row,) = novelty.appendix
        assert row.disposition == cs.APPENDIX_APPENDED
        assert row.section_id == "feasibility_section"
        assert row.sub_section_id == "F.2"

    def test_a_row_in_the_criterions_own_section_is_not_duplicated(self, tmp_path, bundle):
        inputs = _inputs(bundle, _candidate(tmp_path))
        feas = inputs["feasibility"]
        (row,) = feas.appendix
        assert row.disposition == cs.APPENDIX_OWN_SECTION
        assert feas.text.count("MARKER-PLAN-ROW") == 1
        assert feas.complete is True

    def test_the_hash_covers_section_and_appendix_together(self, tmp_path, bundle):
        a = _inputs(bundle, _candidate(tmp_path / "a"))["novelty"]
        # Edit the appendix sub-section only: the novelty section bytes are unchanged.
        cand = _candidate(tmp_path / "b")
        feas = cand / "feasibility_section.json"
        data = json.loads(feas.read_text(encoding="utf-8"))
        data["sub_sections"][1]["content"] += "\n\n| T3 | M12 |"
        _write_json(feas, data)
        b = _inputs(bundle, cand)["novelty"]
        assert a.input_hash.startswith("sha256:")
        assert a.input_hash != b.input_hash
        assert a.section_hash == b.section_hash, "the section alone did not change"

    def test_the_hash_is_formatting_invariant(self, tmp_path, bundle):
        cand = _candidate(tmp_path)
        a = _inputs(bundle, cand)["novelty"]
        for path in cand.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            path.write_text(json.dumps(data, sort_keys=True, indent=4), encoding="utf-8")
        b = _inputs(bundle, cand)["novelty"]
        assert a.input_hash == b.input_hash

    def test_an_unresolved_appendix_row_makes_the_input_incomplete(self, tmp_path, bundle):
        inputs = _inputs(bundle, _candidate(tmp_path, without_f2=True))
        novelty = inputs["novelty"]
        assert novelty.complete is False
        (row,) = novelty.appendix
        assert row.disposition == cs.APPENDIX_UNRESOLVED
        assert any("F.2" in reason for reason in novelty.incompleteness)
        assert "MARKER-NOVELTY-BODY" in novelty.text, "the section is still assembled and reported"

    def test_an_input_over_budget_is_incomplete_not_truncated(self, tmp_path, bundle):
        inputs = _inputs(bundle, _candidate(tmp_path), token_budget=20)
        novelty = inputs["novelty"]
        assert novelty.complete is False
        assert any("budget" in reason for reason in novelty.incompleteness)
        assert "MARKER-PLAN-ROW" in novelty.text, "nothing is cut to make it fit"

    def test_a_section_with_no_text_is_incomplete_not_scored_over_findings(self, tmp_path, bundle):
        cand = _candidate(tmp_path)
        _write_json(cand / "reach_section.json", _section([("R.1", "")]))
        reach = _inputs(bundle, cand)["reach"]
        assert reach.complete is False
        assert any("no sub-section text" in r for r in reach.incompleteness)
        backend = ScriptedBackend()
        findings = [{"expectation_key": "reach-uptake", "covered": True, "score": 0.9}]
        score = cs.grade_criterion(_judge(tmp_path, backend), bundle, reach, aspect_findings=findings)
        assert score.status == cs.NOT_SCORED and backend.calls == 0

    def test_a_missing_section_is_incomplete(self, tmp_path, bundle):
        inputs = _inputs(bundle, _candidate(tmp_path, drop="reach_section"))
        reach = inputs["reach"]
        assert reach.complete is False
        assert any("reach_section" in reason for reason in reach.incompleteness)

    def test_the_mapping_version_is_recorded_on_the_input(self, tmp_path, bundle):
        inputs = _inputs(bundle, _candidate(tmp_path))
        for inp in inputs.values():
            assert inp.mapping_version == bundle.appendix_mapping.version

    def test_without_a_mapping_the_input_is_the_section_alone(self, tmp_path):
        profile_path = _synthetic_world(tmp_path, with_mapping=False)
        b = load_profile_bundle(profile_path, repo_root=tmp_path)
        inputs = _inputs(b, _candidate(tmp_path))
        assert inputs["novelty"].appendix == ()
        assert inputs["novelty"].mapping_version is None
        assert inputs["novelty"].complete is True


# --------------------------------------------------------------------------- #
# 3. The grader: five samples, median and spread, provenance, no shortcuts
# --------------------------------------------------------------------------- #


class TestGrader:
    def test_five_samples_median_and_spread(self, tmp_path, bundle):
        backend = ScriptedBackend(*(_score_json(s) for s in (4.0, 4.5, 3.5, 4.0, 5.0)))
        judge = _judge(tmp_path, backend)
        novelty = _inputs(bundle, _candidate(tmp_path))["novelty"]
        score = cs.grade_criterion(judge, bundle, novelty, n=5)
        assert backend.calls == 5
        assert score.status == cs.SCORED
        assert score.score == 4.0
        assert score.spread == 1.5
        assert score.spread_label == cs.SPREAD_LABEL
        assert "within-assessor" in score.spread_label
        assert [s.score for s in score.samples] == [4.0, 4.5, 3.5, 4.0, 5.0]
        assert all(s.shortcomings == ("one named shortcoming",) for s in score.samples)
        assert len(score.provenance) == 5
        assert score.threshold == 3.0
        assert score.threshold_met is True
        assert score.input_hash == novelty.input_hash
        assert score.mapping_version == bundle.appendix_mapping.version

    def test_the_default_sample_count_is_five(self, tmp_path, bundle):
        backend = ScriptedBackend()
        novelty = _inputs(bundle, _candidate(tmp_path))["novelty"]
        cs.grade_criterion(_judge(tmp_path, backend), bundle, novelty)
        assert backend.calls == cs.DEFAULT_CRITERION_SAMPLES == 5

    def test_the_scorer_sees_the_complete_section_not_a_pack(self, tmp_path, bundle):
        backend = ScriptedBackend()
        novelty = _inputs(bundle, _candidate(tmp_path))["novelty"]
        cs.grade_criterion(_judge(tmp_path, backend), bundle, novelty, n=3)
        for system, user in backend.prompts:
            assert "MARKER-NOVELTY-BODY" in user
            assert "MARKER-PLAN-ROW" in user
            assert "EVIDENCE PACK" not in user
            assert "pack_status" not in user
            assert "Originality of the modelling objectives" in system  # the aspect, verbatim
            assert "level 3" in system  # the official descriptors
            assert "Novelty" in system

    def test_aspect_findings_accompany_the_section_and_never_replace_it(self, tmp_path, bundle):
        backend = ScriptedBackend()
        novelty = _inputs(bundle, _candidate(tmp_path))["novelty"]
        findings = [
            {"expectation_key": "nov-obj", "covered": True, "score": 0.9, "rationale": "FINDING-MARKER"}
        ]
        score = cs.grade_criterion(
            _judge(tmp_path, backend), bundle, novelty, aspect_findings=findings, n=3
        )
        for _system, user in backend.prompts:
            assert "FINDING-MARKER" in user
            assert "MARKER-NOVELTY-BODY" in user
            assert user.index("MARKER-NOVELTY-BODY") < user.index("FINDING-MARKER")
        assert score.aspect_findings_attached is True

    def test_no_criterion_score_from_findings_alone(self, tmp_path, bundle):
        novelty = _inputs(bundle, _candidate(tmp_path))["novelty"]
        empty = cs.CriterionInput(**{**novelty.__dict__, "text": "", "section_hash": novelty.section_hash})
        findings = [{"expectation_key": "nov-obj", "covered": True, "score": 0.9}]
        with pytest.raises(cs.CriterionScoringError, match="findings alone"):
            cs.grade_criterion(_judge(tmp_path, ScriptedBackend()), bundle, empty, aspect_findings=findings)
        with pytest.raises(cs.CriterionScoringError, match="findings alone"):
            cs.grade_criterion(_judge(tmp_path, ScriptedBackend()), bundle, empty)

    def test_an_incomplete_input_is_not_scored_and_the_judge_is_not_called(self, tmp_path, bundle):
        backend = ScriptedBackend()
        novelty = _inputs(bundle, _candidate(tmp_path, without_f2=True))["novelty"]
        score = cs.grade_criterion(_judge(tmp_path, backend), bundle, novelty)
        assert backend.calls == 0
        assert score.status == cs.NOT_SCORED
        assert score.score is None and score.spread is None
        assert score.samples == ()
        assert score.threshold_met is None
        assert score.incompleteness == novelty.incompleteness

    def test_a_malformed_response_fails_closed(self, tmp_path, bundle):
        novelty = _inputs(bundle, _candidate(tmp_path))["novelty"]
        for bad in (
            "not json",
            json.dumps({"shortcomings": [], "rationale": "no score"}),
            json.dumps({"score": 7, "shortcomings": [], "rationale": "out of scale"}),
            json.dumps({"score": 4.25, "shortcomings": [], "rationale": "two decimals"}),
            json.dumps({"score": 4.0, "rationale": "no shortcomings list"}),
            json.dumps({"score": 4.0, "shortcomings": "a string", "rationale": "wrong type"}),
            json.dumps({"score": 4.0, "shortcomings": [], "rationale": ""}),
        ):
            with pytest.raises(JudgeResponseError):
                cs.grade_criterion(_judge(tmp_path, ScriptedBackend(bad)), bundle, novelty, n=3)

    def test_a_judge_without_provenance_is_refused(self, tmp_path, bundle):
        judge = Judge(JudgeConfig(model="fake-assessor", version="pin-7"), backend=ScriptedBackend())
        novelty = _inputs(bundle, _candidate(tmp_path))["novelty"]
        with pytest.raises(cs.CriterionScoringError, match="ProvenanceLog"):
            cs.grade_criterion(judge, bundle, novelty)

    def test_fewer_than_three_samples_is_refused(self, tmp_path, bundle):
        novelty = _inputs(bundle, _candidate(tmp_path))["novelty"]
        with pytest.raises(cs.CriterionScoringError, match="n"):
            cs.grade_criterion(_judge(tmp_path, ScriptedBackend()), bundle, novelty, n=2)

    def test_the_provenance_trail_carries_the_normalised_score(self, tmp_path, bundle):
        backend = ScriptedBackend(_score_json(4.5))
        judge = _judge(tmp_path, backend)
        novelty = _inputs(bundle, _candidate(tmp_path))["novelty"]
        score = cs.grade_criterion(judge, bundle, novelty, n=3)
        lines = (tmp_path / "provenance.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3
        rec = json.loads(lines[0])
        assert rec["metric"] == cs.CRITERION_SCORING_METRIC
        assert rec["property_key"] == score.property_key
        assert rec["score"] == pytest.approx(0.9)  # 4.5 of 5
        assert rec["evidence_type"] == "Inferred"
        assert rec["judge_model"] == "fake-assessor"
        assert score.prompt_hash == rec["prompt_hash"]


# --------------------------------------------------------------------------- #
# 4. The total: weights, thresholds, the ESR arithmetic
# --------------------------------------------------------------------------- #


class TestTotal:
    def test_the_esr_arithmetic_on_the_shipped_dn_scorecard(self):
        b = load_profile_bundle(
            REPO_ROOT / "harness/profiles/msca_dn_2026_default.json", repo_root=REPO_ROOT
        )
        total = cs.weighted_total(
            {"excellence": 4.20, "impact": 4.50, "implementation": 4.20}, b.scoring
        )
        assert total == pytest.approx(85.80)
        assert cs.score_factor(b.scoring, "excellence") == pytest.approx(10.0)
        assert cs.score_factor(b.scoring, "impact") == pytest.approx(6.0)
        assert cs.score_factor(b.scoring, "implementation") == pytest.approx(4.0)
        assert cs.total_formula(b.scoring) == "S = 10*excellence + 6*impact + 4*implementation"

    def test_the_shipped_pf_and_ria_profiles_still_load_and_parse_their_scales(self):
        pf = load_profile_bundle(REPO_ROOT / "harness/profiles/msca_pf_default.json", repo_root=REPO_ROOT)
        ria = load_profile_bundle(REPO_ROOT / "harness/profiles/ria_default.json", repo_root=REPO_ROOT)
        assert (pf.scoring.scale_max, pf.scoring.score_resolution, pf.scoring.individual_threshold) == (5.0, 0.1, None)
        assert (ria.scoring.scale_max, ria.scoring.score_resolution, ria.scoring.individual_threshold) == (5.0, 0.5, 3.0)
        assert pf.appendix_mapping is None and ria.appendix_mapping is None
        assert cs.total_formula(pf.scoring) == "S = 10*excellence + 6*impact + 4*implementation"
        assert cs.total_formula(ria.scoring) == "S = 1*excellence + 1*impact + 1*implementation"

    def test_an_unweighted_scorecard_sums_the_scores(self):
        b = load_profile_bundle(REPO_ROOT / "harness/profiles/ria_default.json", repo_root=REPO_ROOT)
        assert cs.weighted_total({"excellence": 4, "impact": 3.5, "implementation": 3}, b.scoring) == pytest.approx(10.5)
        assert b.scoring.overall_max == 15

    def test_thresholds_both_checked(self, tmp_path, bundle):
        scripted = {
            "novelty": (4.0,) * 5,
            "reach": (2.5,) * 5,
            "feasibility": (4.0,) * 5,
        }
        inputs = _inputs(bundle, _candidate(tmp_path))
        scores = []
        for cid, values in scripted.items():
            judge = _judge(tmp_path / cid, ScriptedBackend(*(_score_json(v) for v in values)))
            scores.append(cs.grade_criterion(judge, bundle, inputs[cid]))
        result = cs.combine_criterion_scores(scores, bundle.scoring)
        # 10*4.0 + 6*2.5 + 4*4.0 = 71.0 -> overall passes, one criterion fails its own threshold
        assert result.total == pytest.approx(71.0)
        assert result.overall_threshold == 70
        assert result.overall_threshold_met is True
        assert result.individual_thresholds_met is False
        assert result.failing_criteria == ("reach",)
        assert result.formula == "S = 10*novelty + 6*reach + 4*feasibility"
        data = result.to_dict()
        assert data["spread_label"] == cs.SPREAD_LABEL
        assert data["samples_per_criterion"] == 5
        assert {s["criterion_id"] for s in data["scores"]} == {"novelty", "reach", "feasibility"}

    def test_an_unscored_criterion_leaves_the_total_undetermined(self, tmp_path, bundle):
        inputs = _inputs(bundle, _candidate(tmp_path, drop="reach_section"))
        scores = [
            cs.grade_criterion(_judge(tmp_path / cid, ScriptedBackend()), bundle, inputs[cid])
            for cid in ("novelty", "reach", "feasibility")
        ]
        result = cs.combine_criterion_scores(scores, bundle.scoring)
        assert result.total is None
        assert result.overall_threshold_met is None
        assert result.individual_thresholds_met is None
        assert result.unscored_criteria == ("reach",)

    def test_no_code_path_derives_a_criterion_score_from_cells(self):
        """The grader module never imports the cell grader or its grade type, and
        the aggregate takes criterion scores only."""
        source = (REPO_ROOT / "harness/criterion_scoring.py").read_text(encoding="utf-8")
        assert "grade_expectation" not in source
        assert "CoverageGrade" not in source
        assert "mean_score" not in source
        import inspect

        params = inspect.signature(cs.combine_criterion_scores).parameters
        assert list(params) == ["scores", "scoring"]


# --------------------------------------------------------------------------- #
# 5. The shipped MSCA-DN candidate: whole sections fit, every row resolves
# --------------------------------------------------------------------------- #


class TestShippedDnCandidate:
    """Spec PE-04's table: the criterion lane carries no selection because the
    complete sections plus their declared appendix fit the uncapped budget.
    Re-derived here from the imported record, Claude-free."""

    @pytest.fixture(scope="class")
    def dn_inputs(self, tmp_path_factory):
        import harness.blind_assessment as ba
        from harness.evidence_pack import UNCAPPED_DEFAULT_PACK_TOKEN_BUDGET

        bundle = load_profile_bundle(
            REPO_ROOT / "harness/profiles/msca_dn_2026_default.json", repo_root=REPO_ROOT
        )
        evidence = ba.build_blind_evidence(
            REPO_ROOT / "workspaces/msca_dn",
            "MSCA-DN-2025_sanitised_part_b",
            profile_version=bundle.version,
            out_dir=tmp_path_factory.mktemp("dn"),
        )
        candidate = ba.load_candidate(evidence.candidate_dir, bundle.profile)
        return bundle, {
            cid: cs.build_criterion_input(
                bundle, candidate, cid, token_budget=UNCAPPED_DEFAULT_PACK_TOKEN_BUDGET
            )
            for cid in bundle.profile.criterion_ids
        }

    def test_every_criterion_input_is_complete_under_the_uncapped_budget(self, dn_inputs):
        _bundle, inputs = dn_inputs
        for cid, inp in inputs.items():
            assert inp.complete, (cid, inp.incompleteness)
            assert inp.token_estimate <= inp.token_budget

    def test_every_declared_row_resolves_and_none_is_unresolved(self, dn_inputs):
        bundle, inputs = dn_inputs
        declared = {r.criterion_id for r in bundle.appendix_mapping.rows}
        assert declared == set(inputs)
        for inp in inputs.values():
            assert inp.appendix, inp.criterion_id
            assert all(r.disposition != cs.APPENDIX_UNRESOLVED for r in inp.appendix)

    def test_cross_section_rows_reach_the_criterion_that_declared_them(self, dn_inputs):
        _bundle, inputs = dn_inputs
        # Excellence and Impact receive Implementation's tables; Implementation
        # receives only its own section 8 and nothing twice.
        assert "Table 3.1 b Deliverables List" in inputs["impact"].text
        assert "Beneficiary A" in inputs["excellence"].text
        impl = inputs["implementation"]
        assert all(r.disposition == cs.APPENDIX_OWN_SECTION for r in impl.appendix)
        assert impl.text.count("=== DECLARED APPENDIX") == 0
