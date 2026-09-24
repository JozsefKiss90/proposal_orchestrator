"""
E5b — rubric set: versioned data, scorecard-verbatim wording, fail-closed drift,
prompt rendering, and the offline fake-backend end-to-end.

The real-file pins assert the committed ``harness/rubrics_msca_pf.json`` is in
bijection with the E5a substrate and byte-verbatim with the scorecard; drift
fixtures (paraphrase, missing/extra/duplicate rubric, stale scorecard version,
malformed fields) assert the loader fails closed.  The end-to-end test drives a
rubric + evidence pack through the E1 judge with an **injectable fake backend**
— no network anywhere in this module.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import harness.rubrics as rb
from harness.evidence_pack import PACK_INSUFFICIENT_CONTEXT, build_evidence_pack
from harness.judge import Judge, JudgeConfig
from harness.profile import default_profile
from harness.provenance import ProvenanceLog, prompt_hash
from harness.verdict import EVIDENCE_TYPE_INFERRED

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE = default_profile(REPO_ROOT)
RUBRIC_PATH = REPO_ROOT / PROFILE.rubric_set.path
REGISTRY_PATH = REPO_ROOT / PROFILE.registry_path
SCORECARD_PATH = REPO_ROOT / PROFILE.scorecard.path

#: The 9 scorecard aspect ids in scorecard order (the E5a pin, reused).
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


def _load(rubric_path: Path | None = None):
    return rb.load_rubric_set(
        rubric_path or RUBRIC_PATH,
        registry_path=REGISTRY_PATH,
        scorecard_path=SCORECARD_PATH,
        profile=PROFILE,
    )


def _real_rubric_data() -> dict:
    return json.loads(RUBRIC_PATH.read_text(encoding="utf-8-sig"))


def _write(tmp_path: Path, data: dict) -> Path:
    p = tmp_path / "rubrics.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


# --------------------------------------------------------------------------- #
# Real-file pins
# --------------------------------------------------------------------------- #


class TestRealRubricSet:
    def test_nine_rubrics_in_scorecard_order(self):
        rs = _load()
        assert tuple(r.expectation_key for r in rs.rubrics) == EXPECTED_KEYS

    def test_expectation_text_is_scorecard_verbatim(self):
        from harness.expectations import load_expectation_substrate

        substrate = load_expectation_substrate(
            registry_path=REGISTRY_PATH, scorecard_path=SCORECARD_PATH, profile=PROFILE
        )
        expected = substrate.by_key()
        for rubric in _load().rubrics:
            assert rubric.expectation_text == expected[rubric.expectation_key].text
            assert rubric.criterion_id == expected[rubric.expectation_key].criterion_id
            assert rubric.source_page == expected[rubric.expectation_key].source_page

    def test_every_rubric_carries_steps_threshold_and_selection_basis(self):
        for rubric in _load().rubrics:
            assert rubric.rubric
            assert len(rubric.evaluation_steps) >= 3
            assert 0.0 < rubric.pass_threshold <= 1.0
            assert rubric.selection_terms
            assert rubric.anchor_sub_section_ids

    def test_set_identity_and_fingerprints_are_stable(self):
        a, b = _load(), _load()
        assert a.rubric_set_id == "msca_pf_rubrics"
        assert a.version
        assert a.fingerprint == b.fingerprint
        for ra, rc in zip(a.rubrics, b.rubrics):
            assert rb.rubric_fingerprint(ra) == rb.rubric_fingerprint(rc)
            assert rb.rubric_fingerprint(ra).startswith("sha256:")

    def test_fingerprint_changes_when_rubric_data_changes(self, tmp_path):
        data = _real_rubric_data()
        data["rubrics"][0]["rubric"] += " Tightened wording."
        drifted = _load(_write(tmp_path, data))
        assert drifted.fingerprint != _load().fingerprint

    def test_fingerprint_ignores_substrate_stamped_source_page(self):
        import dataclasses

        rubric = _load().rubrics[0]
        restamped = dataclasses.replace(rubric, source_page="99", form_name="Other Form")
        assert rb.rubric_fingerprint(restamped) == rb.rubric_fingerprint(rubric)


# --------------------------------------------------------------------------- #
# Fail-closed drift
# --------------------------------------------------------------------------- #


class TestFailClosedDrift:
    def test_paraphrased_expectation_text_raises(self, tmp_path):
        data = _real_rubric_data()
        data["rubrics"][0]["expectation_text"] = (
            "Quality and pertinence of the research objectives."
        )
        with pytest.raises(rb.RubricError, match="verbatim"):
            _load(_write(tmp_path, data))

    def test_missing_rubric_raises(self, tmp_path):
        data = _real_rubric_data()
        del data["rubrics"][3]
        with pytest.raises(rb.RubricError, match="bijection"):
            _load(_write(tmp_path, data))

    def test_extra_rubric_raises(self, tmp_path):
        data = _real_rubric_data()
        extra = dict(data["rubrics"][0])
        extra["expectation_key"] = "exc-extra"
        data["rubrics"].append(extra)
        with pytest.raises(rb.RubricError, match="bijection"):
            _load(_write(tmp_path, data))

    def test_duplicate_rubric_raises(self, tmp_path):
        data = _real_rubric_data()
        data["rubrics"].append(dict(data["rubrics"][0]))
        with pytest.raises(rb.RubricError, match="duplicate"):
            _load(_write(tmp_path, data))

    def test_stale_scorecard_version_raises(self, tmp_path):
        data = _real_rubric_data()
        data["scorecard_version"] = "1.9"
        with pytest.raises(rb.RubricError, match="re-verify"):
            _load(_write(tmp_path, data))

    def test_criterion_mismatch_raises(self, tmp_path):
        data = _real_rubric_data()
        data["rubrics"][0]["criterion_id"] = "impact"
        with pytest.raises(rb.RubricError, match="criterion_id"):
            _load(_write(tmp_path, data))

    def test_empty_steps_raise(self, tmp_path):
        data = _real_rubric_data()
        data["rubrics"][0]["evaluation_steps"] = []
        with pytest.raises(rb.RubricError, match="evaluation_steps"):
            _load(_write(tmp_path, data))

    def test_threshold_out_of_range_raises(self, tmp_path):
        for bad in (0, 1.5, -0.1):
            data = _real_rubric_data()
            data["rubrics"][0]["pass_threshold"] = bad
            with pytest.raises(rb.RubricError, match="pass_threshold"):
                _load(_write(tmp_path, data))

    def test_empty_selection_terms_raise(self, tmp_path):
        data = _real_rubric_data()
        data["rubrics"][0]["selection_terms"] = []
        with pytest.raises(rb.RubricError):
            _load(_write(tmp_path, data))

    def test_unversioned_set_raises(self, tmp_path):
        data = _real_rubric_data()
        data["version"] = ""
        with pytest.raises(rb.RubricError, match="versioned"):
            _load(_write(tmp_path, data))

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(rb.RubricError, match="not found"):
            _load(tmp_path / "absent.json")

    def test_invalid_json_raises(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{oops", encoding="utf-8")
        with pytest.raises(rb.RubricError, match="valid JSON"):
            _load(p)


# --------------------------------------------------------------------------- #
# Prompt rendering + hashing (offline, over a fixture pack)
# --------------------------------------------------------------------------- #


def _fixture_section(tmp_path: Path) -> Path:
    data = {
        "sub_sections": [
            {
                "sub_section_id": "1.1",
                "title": "Objectives",
                "content": (
                    "The objectives are ambitious and go beyond the state of "
                    "the art in modelling."
                ),
            }
        ],
        "validation_status": {
            "claim_statuses": [
                {
                    "claim_id": "C01",
                    "claim_summary": "The objectives target modelling advances.",
                    "status": "confirmed",
                    "source_ref": "docs/tier3/a.json#x",
                }
            ]
        },
    }
    p = tmp_path / "excellence_section.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


@pytest.fixture()
def exc_obj_rubric():
    return _load().by_key()["exc-obj"]


@pytest.fixture()
def fixture_pack(tmp_path, exc_obj_rubric):
    return rb.build_pack_for(exc_obj_rubric, _fixture_section(tmp_path))


class TestPromptRendering:
    def test_system_prompt_carries_the_contract(self, exc_obj_rubric):
        system = rb.build_rubric_system_prompt(exc_obj_rubric)
        assert exc_obj_rubric.expectation_text in system
        assert exc_obj_rubric.rubric in system
        for i, step in enumerate(exc_obj_rubric.evaluation_steps, 1):
            assert f"{i}. {step}" in system
        assert PACK_INSUFFICIENT_CONTEXT in system
        assert str(exc_obj_rubric.pass_threshold) in system
        assert '"passed"' in system and '"score"' in system and '"rationale"' in system
        assert "ADDRESSES and GROUNDS" in system
        # The form the prompt cites comes from the profile, not from Python.
        assert PROFILE.instrument.form_name in system
        assert exc_obj_rubric.form_name == PROFILE.instrument.form_name

    def test_user_prompt_embeds_the_pack_verbatim(self, exc_obj_rubric, fixture_pack):
        user = rb.build_rubric_user_prompt(exc_obj_rubric, fixture_pack)
        assert user.startswith(fixture_pack.render())
        assert user.rstrip().endswith("return only the JSON object.")

    def test_mismatched_pack_is_refused(self, exc_obj_rubric, tmp_path):
        other = build_evidence_pack(
            expectation_key="impl-host",
            section_path=_fixture_section(tmp_path),
            selection_terms=("objectives",),
        )
        with pytest.raises(rb.RubricError, match="mismatched"):
            rb.build_rubric_user_prompt(exc_obj_rubric, other)

    def test_prompt_hash_matches_house_hash_and_is_stable(
        self, exc_obj_rubric, fixture_pack
    ):
        h1 = rb.rubric_prompt_hash(exc_obj_rubric, fixture_pack)
        h2 = rb.rubric_prompt_hash(exc_obj_rubric, fixture_pack)
        assert h1 == h2 == prompt_hash(*rb.build_rubric_prompts(exc_obj_rubric, fixture_pack))
        assert h1.startswith("sha256:")

    def test_build_pack_for_uses_the_rubric_selection_basis(
        self, exc_obj_rubric, fixture_pack
    ):
        assert fixture_pack.expectation_key == exc_obj_rubric.expectation_key
        assert fixture_pack.selection_terms == exc_obj_rubric.selection_terms
        assert (
            fixture_pack.anchor_sub_section_ids
            == exc_obj_rubric.anchor_sub_section_ids
        )


# --------------------------------------------------------------------------- #
# End-to-end with the injectable fake backend — no network
# --------------------------------------------------------------------------- #


class TestFakeBackendEndToEnd:
    def _judge(self, tmp_path, responses):
        calls = []

        def backend(messages):
            calls.append(messages)
            return {"content": responses[min(len(calls) - 1, len(responses) - 1)]}

        judge = Judge(
            JudgeConfig(model="fake-judge", version="pin-1"),
            backend=backend,
            provenance_log=ProvenanceLog(tmp_path / "provenance.jsonl"),
            clock=lambda: "2026-08-07T00:00:00+00:00",
        )
        return judge, calls

    def test_single_verdict_roundtrip(self, tmp_path, exc_obj_rubric, fixture_pack):
        judge, calls = self._judge(
            tmp_path,
            ['{"passed": true, "score": 0.85, "rationale": "spans 1.1 ground it"}'],
        )
        system, user = rb.build_rubric_prompts(exc_obj_rubric, fixture_pack)
        result = judge.evaluate(
            system,
            user,
            metric="rubric_coverage",
            property_key=f"rubric::{exc_obj_rubric.expectation_key}::{fixture_pack.section_id}",
        )
        assert result.verdict.passed is True
        assert result.verdict.score == 0.85
        assert result.verdict.evidence_type == EVIDENCE_TYPE_INFERRED
        # The provenance prompt_hash equals the offline-computable pin.
        assert result.provenance.prompt_hash == rb.rubric_prompt_hash(
            exc_obj_rubric, fixture_pack
        )
        # The backend really saw the rendered pack — end-to-end, not a stub.
        assert calls[0][0]["content"] == system
        assert fixture_pack.render() in calls[0][1]["content"]

    def test_majority_vote_roundtrip(self, tmp_path, exc_obj_rubric, fixture_pack):
        judge, calls = self._judge(
            tmp_path,
            [
                '{"passed": true, "score": 0.8, "rationale": "grounded"}',
                '{"passed": true, "score": 0.7, "rationale": "grounded"}',
                '{"passed": false, "score": 0.4, "rationale": "weak grounding"}',
            ],
        )
        system, user = rb.build_rubric_prompts(exc_obj_rubric, fixture_pack)
        result = judge.evaluate_majority(
            system,
            user,
            metric="rubric_coverage",
            property_key="rubric::exc-obj::excellence_section",
        )
        assert len(calls) == 3
        assert result.majority.passed is True  # 2 of 3
        assert result.majority.evidence_type == EVIDENCE_TYPE_INFERRED
        assert len(result.provenance) == 3

    def test_truncated_pack_never_yields_a_clean_pass(
        self, tmp_path, exc_obj_rubric
    ):
        """The mechanism, not just the prompt: even a judge that answers
        passed=true over an insufficient_context pack does not produce a clean
        pass through clean_pass()."""
        from harness.evidence_pack import (
            _render_frame,
            clean_pass,
            estimate_tokens,
            pack_forbids_clean_pass,
        )

        frame_tokens = estimate_tokens(
            _render_frame("exc-obj", "excellence_section", PACK_INSUFFICIENT_CONTEXT)
        )
        truncated = rb.build_pack_for(
            exc_obj_rubric, _fixture_section(tmp_path), token_budget=frame_tokens + 5
        )
        assert pack_forbids_clean_pass(truncated)
        judge, _calls = self._judge(
            tmp_path, ['{"passed": true, "score": 0.95, "rationale": "looks fine"}']
        )
        system, user = rb.build_rubric_prompts(exc_obj_rubric, truncated)
        result = judge.evaluate(
            system, user, metric="rubric_coverage", property_key="rubric::exc-obj::x"
        )
        assert result.verdict.passed is True  # the judge was fooled...
        assert clean_pass(truncated, result.verdict.passed) is False  # ...the contract is not
        # And the prompt did carry the truncation instruction.
        assert PACK_INSUFFICIENT_CONTEXT in system
        assert "pack_status: insufficient_context" in user
