"""
E5c — coverage-axis grader: routing, N≥3 majority + provenance, clean-pass
derivation, and the structural grader/generator-independence assertion.

Everything runs offline against the injectable fake backend — no network.  The
independence tests are structural (same shape as ``test_boundary.py``): they
assert facts about models, transports, and source imports, not prose promises.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import harness.expectation_coverage as ec
from harness.evidence_pack import (
    PACK_COMPLETE,
    PACK_INSUFFICIENT_CONTEXT,
    _render_frame,
    estimate_tokens,
)
from harness.judge import Judge, JudgeConfig, JudgeIndependenceError, drafter_models
from harness.provenance import ProvenanceLog
from harness.routing import (
    DeterministicCoverageError,
    RoutingAuthority,
    assert_judgeable,
    deterministic_predicate_names,
    route,
)
from harness.rubrics import build_pack_for, load_rubric_set, rubric_prompt_hash
from harness.verdict import EVIDENCE_TYPE_INFERRED

from harness.profile import default_profile

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE = default_profile(REPO_ROOT)
RUBRIC_PATH = REPO_ROOT / PROFILE.rubric_set.path
REGISTRY_PATH = REPO_ROOT / PROFILE.registry_path
SCORECARD_PATH = REPO_ROOT / PROFILE.scorecard.path

#: The in-run reviewer skill the E5c ticket names — the thing the grader must
#: provably NOT be a second hat of.
INRUN_REVIEWER_SKILL = REPO_ROOT / ".claude/skills/evaluator-criteria-review.md"


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
    return (
        load_rubric_set(
            RUBRIC_PATH,
            registry_path=REGISTRY_PATH,
            scorecard_path=SCORECARD_PATH,
            profile=PROFILE,
        )
        .by_key()["exc-obj"]
    )


@pytest.fixture()
def fixture_pack(tmp_path, exc_obj_rubric):
    return build_pack_for(exc_obj_rubric, _fixture_section(tmp_path))


def _judge(tmp_path, responses, *, with_log=True):
    calls = []

    def backend(messages):
        calls.append(messages)
        return {"content": responses[min(len(calls) - 1, len(responses) - 1)]}

    judge = Judge(
        JudgeConfig(model="fake-judge", version="pin-1"),
        backend=backend,
        provenance_log=(
            ProvenanceLog(tmp_path / "provenance.jsonl") if with_log else None
        ),
        clock=lambda: "2026-08-07T00:00:00+00:00",
    )
    return judge, calls


MAJORITY_2_OF_3 = [
    '{"passed": true, "score": 0.8, "rationale": "1.1 grounds the objectives"}',
    '{"passed": true, "score": 0.7, "rationale": "addressed in 1.1"}',
    '{"passed": false, "score": 0.4, "rationale": "weak grounding"}',
]


# --------------------------------------------------------------------------- #
# Routing — a distinct key, checked on every grade
# --------------------------------------------------------------------------- #


class TestRouting:
    def test_metric_key_is_not_a_deterministic_predicate(self):
        preds = deterministic_predicate_names()
        assert "instrument_sections_addressed" in preds  # the neighbour exists
        assert ec.EXPECTATION_COVERAGE_METRIC not in preds
        key = ec.coverage_property_key("exc-obj", "excellence_section")
        assert key not in preds
        assert route(key).judge_permitted is True
        assert route(key).authority == RoutingAuthority.SEMANTIC_GAP

    def test_the_covered_neighbour_key_is_refused(self):
        # The predicate proves a section exists/is non-empty; judging under its
        # key would double-check a proof with an opinion — routing refuses it.
        assert route("instrument_sections_addressed").judge_permitted is False
        with pytest.raises(DeterministicCoverageError):
            assert_judgeable("instrument_sections_addressed")

    def test_grade_records_the_routing_decision(
        self, tmp_path, exc_obj_rubric, fixture_pack
    ):
        judge, _ = _judge(tmp_path, MAJORITY_2_OF_3)
        grade = ec.grade_coverage(judge, exc_obj_rubric, fixture_pack)
        assert grade.routing.judge_permitted is True
        assert grade.routing.property_key == grade.property_key
        assert grade.routing.authority == RoutingAuthority.SEMANTIC_GAP

    def test_grade_actually_routes_and_fails_closed_on_coverage(
        self, tmp_path, exc_obj_rubric, fixture_pack, monkeypatch
    ):
        # Prove grade_coverage() consults routing (not just the test above):
        # if the property key ever became deterministically covered, grading
        # raises instead of judging.
        key = ec.coverage_property_key(
            fixture_pack.expectation_key, fixture_pack.section_id
        )
        monkeypatch.setattr(
            "harness.routing.deterministic_predicate_names",
            lambda: frozenset({key}),
        )
        judge, calls = _judge(tmp_path, MAJORITY_2_OF_3)
        with pytest.raises(DeterministicCoverageError):
            ec.grade_coverage(judge, exc_obj_rubric, fixture_pack)
        assert calls == []  # the judge was never invoked


# --------------------------------------------------------------------------- #
# The grade — N≥3 majority, provenance, clean-pass derivation
# --------------------------------------------------------------------------- #


class TestGradeCoverage:
    def test_majority_grade_roundtrip(self, tmp_path, exc_obj_rubric, fixture_pack):
        judge, calls = _judge(tmp_path, MAJORITY_2_OF_3)
        grade = ec.grade_coverage(judge, exc_obj_rubric, fixture_pack)

        assert len(calls) == 3  # N≥3 panel, never a single sample
        assert grade.judge_passed is True  # 2 of 3
        assert grade.passed is True  # pack complete -> clean pass
        assert grade.score == pytest.approx((0.8 + 0.7 + 0.4) / 3)
        assert grade.rationale  # the vote synthesis
        assert grade.verdict.n == 3
        assert grade.verdict.evidence_type == EVIDENCE_TYPE_INFERRED
        assert all(
            m.evidence_type == EVIDENCE_TYPE_INFERRED for m in grade.verdict.members
        )
        assert grade.expectation_key == "exc-obj"
        assert grade.criterion_id == exc_obj_rubric.criterion_id
        assert grade.section_id == fixture_pack.section_id
        assert grade.pack_status == PACK_COMPLETE

    def test_full_provenance_record(self, tmp_path, exc_obj_rubric, fixture_pack):
        judge, _ = _judge(tmp_path, MAJORITY_2_OF_3)
        grade = ec.grade_coverage(judge, exc_obj_rubric, fixture_pack)

        # Every sample carries the five required fields, pinned to the judge...
        assert len(grade.provenance) == 3
        expected_hash = rubric_prompt_hash(exc_obj_rubric, fixture_pack)
        for i, rec in enumerate(grade.provenance):
            assert rec.judge_model == "fake-judge"
            assert rec.judge_version == "pin-1"
            assert rec.prompt_hash == expected_hash
            assert rec.metric == ec.EXPECTATION_COVERAGE_METRIC
            assert rec.property_key == grade.property_key
            assert rec.sample_index == i
        assert grade.prompt_hash == expected_hash
        # ...and every sample landed in the durable JSONL trail.
        lines = (tmp_path / "provenance.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3

    def test_judge_without_provenance_log_is_refused(
        self, tmp_path, exc_obj_rubric, fixture_pack
    ):
        judge, calls = _judge(tmp_path, MAJORITY_2_OF_3, with_log=False)
        with pytest.raises(ec.CoverageError, match="ProvenanceLog"):
            ec.grade_coverage(judge, exc_obj_rubric, fixture_pack)
        assert calls == []

    def test_n_below_three_rejected(self, tmp_path, exc_obj_rubric, fixture_pack):
        judge, _ = _judge(tmp_path, MAJORITY_2_OF_3)
        with pytest.raises(ValueError, match="n≥3"):
            ec.grade_coverage(judge, exc_obj_rubric, fixture_pack, n=2)

    def test_mismatched_pack_is_refused(self, tmp_path, exc_obj_rubric):
        from harness.evidence_pack import build_evidence_pack
        from harness.rubrics import RubricError

        other = build_evidence_pack(
            expectation_key="impl-host",
            section_path=_fixture_section(tmp_path),
            selection_terms=("objectives",),
        )
        judge, _ = _judge(tmp_path, MAJORITY_2_OF_3)
        with pytest.raises(RubricError, match="mismatched"):
            ec.grade_coverage(judge, exc_obj_rubric, other)

    def test_truncated_pack_never_yields_a_clean_pass(self, tmp_path, exc_obj_rubric):
        """The E5b contract consumed: a unanimous fooled judge over an
        insufficient_context pack still cannot produce passed=True."""
        frame_tokens = estimate_tokens(
            _render_frame("exc-obj", "excellence_section", PACK_INSUFFICIENT_CONTEXT)
        )
        truncated = build_pack_for(
            exc_obj_rubric, _fixture_section(tmp_path), token_budget=frame_tokens + 5
        )
        assert truncated.status == PACK_INSUFFICIENT_CONTEXT
        judge, _ = _judge(
            tmp_path, ['{"passed": true, "score": 0.95, "rationale": "looks fine"}'] * 3
        )
        grade = ec.grade_coverage(judge, exc_obj_rubric, truncated)
        assert grade.judge_passed is True  # the raw majority was fooled...
        assert grade.passed is False  # ...the derived pass field is not
        assert grade.pack_status == PACK_INSUFFICIENT_CONTEXT

    def test_to_dict_is_json_serializable_and_complete(
        self, tmp_path, exc_obj_rubric, fixture_pack
    ):
        judge, _ = _judge(tmp_path, MAJORITY_2_OF_3)
        grade = ec.grade_coverage(judge, exc_obj_rubric, fixture_pack)
        d = grade.to_dict()
        json.dumps(d)  # round-trippable
        assert d["metric"] == ec.EXPECTATION_COVERAGE_METRIC
        assert d["passed"] is True
        assert d["verdict"]["n"] == 3
        assert len(d["provenance"]) == 3
        assert d["routing"]["judge_permitted"] is True
        # The no-silent-caps selection record travels with the score.
        assert "excluded" in d["pack_record"]
        assert d["rubric_fingerprint"].startswith("sha256:")

    def test_grade_expectation_builds_pack_from_rubric_basis(
        self, tmp_path, exc_obj_rubric
    ):
        judge, _ = _judge(tmp_path, MAJORITY_2_OF_3)
        grade = ec.grade_expectation(
            judge, exc_obj_rubric, _fixture_section(tmp_path)
        )
        assert grade.expectation_key == "exc-obj"
        assert grade.pack_record["selection_terms"] == list(
            exc_obj_rubric.selection_terms
        )
        assert grade.pack_record["anchor_sub_section_ids"] == list(
            exc_obj_rubric.anchor_sub_section_ids
        )


# --------------------------------------------------------------------------- #
# Independence — structural, not prose (test_boundary.py shape)
# --------------------------------------------------------------------------- #


class TestIndependence:
    """The grader is provably not the in-run reviewer wearing a second hat.

    The in-run reviewer is the ``evaluator-criteria-review`` skill: it runs on
    ``SKILL_MODEL`` over the ``claude_cli`` drafter transport with the in-run
    drafting context.  Each test pins one axis of separation.
    """

    def test_inrun_reviewer_skill_exists(self):
        # The thing we claim independence FROM must actually exist in-run.
        assert INRUN_REVIEWER_SKILL.is_file()
        assert "evaluator-criteria-review" in INRUN_REVIEWER_SKILL.read_text(
            encoding="utf-8"
        )

    def test_judge_model_pin_cannot_be_the_inrun_reviewer_model(self):
        # Model axis: the models the in-run pipeline drafts/reviews with are
        # exactly what JudgeConfig refuses.
        from runner.semantic_dispatch import AGENT_MODEL
        from runner.skill_runtime import SKILL_MODEL

        assert SKILL_MODEL in drafter_models()
        assert AGENT_MODEL in drafter_models()
        with pytest.raises(JudgeIndependenceError):
            JudgeConfig(model=SKILL_MODEL, version="pin-x")
        with pytest.raises(JudgeIndependenceError):
            JudgeConfig(model=AGENT_MODEL, version="pin-x")

    def test_judge_default_transport_rejects_the_drafter_transport(self, monkeypatch):
        # Transport axis: the in-run skill speaks claude_cli; the judge's
        # default backend refuses to.
        from runner.transport.capabilities import CAPABILITIES_REGISTRY
        from runner.transport.config import ProviderConfig

        claude_cfg = ProviderConfig(
            backend_name="claude_cli",
            base_url=None,
            api_key_set=False,
            model=None,
            capabilities=CAPABILITIES_REGISTRY["claude_cli"],
        )
        monkeypatch.setattr(
            "runner.transport.config.resolve_provider_config", lambda: claude_cfg
        )
        judge = Judge(JudgeConfig(model="fake-judge", version="pin-1"))
        with pytest.raises(JudgeIndependenceError, match="OpenAI-compatible"):
            judge.raw_invoke("s", "u")

    def test_coverage_module_never_imports_the_drafter_stack(self):
        # Static source check (same mechanism as test_boundary.py): the grader
        # module must not import the transport/runtime the drafter and in-run
        # reviewer execute on.
        forbidden = re.compile(
            r"^\s*(?:from|import)\s+runner\.(?:claude_transport|skill_runtime|"
            r"semantic_dispatch|agent_runtime)\b",
            re.MULTILINE,
        )
        text = (REPO_ROOT / "harness" / "expectation_coverage.py").read_text(
            encoding="utf-8"
        )
        assert not forbidden.search(text), (
            "harness/expectation_coverage.py must not import the drafter "
            "transport/runtime stack"
        )

    def test_grader_context_is_the_frozen_pack_not_the_drafting_context(
        self, tmp_path, exc_obj_rubric, fixture_pack
    ):
        # Context axis: the judge sees exactly the rubric prompts over the
        # frozen artifact's evidence pack — nothing from the in-run drafting
        # context (assembled draft, phase outputs, evaluation forms on disk).
        judge, calls = _judge(tmp_path, MAJORITY_2_OF_3)
        ec.grade_coverage(judge, exc_obj_rubric, fixture_pack)
        from harness.rubrics import build_rubric_prompts

        system, user = build_rubric_prompts(exc_obj_rubric, fixture_pack)
        for call in calls:
            assert call[0]["content"] == system
            assert call[1]["content"] == user
        assert fixture_pack.render() in user
        for inrun_input in (
            "part_b_assembled_draft",
            "phase1_call_analysis",
            "evaluation_forms",
        ):
            assert inrun_input not in system + user
