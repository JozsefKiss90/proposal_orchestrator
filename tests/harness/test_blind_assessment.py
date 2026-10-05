"""
Candidate-bound blind assessment (``harness.blind_assessment`` +
``harness.commands.blind_assessment``).

Everything runs offline: a fake backend, a frozen clock and a temporary
provenance log.  The candidate is a directory of section artifacts built under
``tmp_path`` against a call-neutral synthetic three-criterion profile, so the
tests never read a real proposal or the default profile.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import harness.blind_assessment as ba
import harness.commands.blind_assessment as cmd
from tests.harness._preflight import preflighted
from harness.judge import Judge, JudgeConfig, JudgeResponseError
from harness.provenance import ProvenanceLog
from harness.rubrics import load_profile_bundle

REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN = "2026-09-24T12:00:00+00:00"
PASS_JSON = '{"passed": true, "score": 0.9, "rationale": "scripted pass"}'
FAIL_JSON = '{"passed": false, "score": 0.2, "rationale": "scripted fail"}'

TEXT = (
    "The modelling objectives are original and go beyond current practice.\n\n"
    "The modelling method reuses partner tooling across the consortium."
)


def _write_json(path: Path, data) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _section(sub_section_ids) -> dict:
    return {
        "sub_sections": [
            {"sub_section_id": sid, "title": f"Part {sid}", "content": TEXT}
            for sid in sub_section_ids
        ],
        "validation_status": {
            "claim_statuses": [
                {
                    "claim_id": "C01",
                    "claim_summary": "The modelling objective is beyond current practice.",
                    "status": "confirmed",
                    "source_ref": "docs/t3/a.json",
                }
            ]
        },
    }


def _synthetic_world(root: Path) -> Path:
    """A call-neutral instrument ``SYN-TRI`` with three criteria (Novelty,
    Reach, Feasibility), each mapped to one section of the candidate."""
    criteria = [
        ("novelty", "Novelty", "nov-obj", "Originality of the modelling objectives", 60),
        ("reach", "Reach", "reach-uptake", "Breadth of the modelling uptake", 25),
        ("feasibility", "Feasibility", "feas-plan", "Credibility of the modelling plan", 15),
    ]
    registry = {
        "instruments": [
            {
                "instrument_type": "SYN-TRI",
                "criteria": [
                    {"criterion_id": rid, "evaluator_expectations": [text]}
                    for _cid, rid, _key, text, _w in criteria
                ],
            }
        ]
    }
    scorecard = {
        "scorecard_id": "syn_tri_scorecard",
        "provenance": {"version": "0.1"},
        "scoring": {
            "scale": "0-10, integers",
            "levels": {"0": "none", "10": "full"},
            "overall_threshold": 60,
            "overall_max": 100,
        },
        "criteria": [
            {
                "id": cid,
                "name": rid,
                "weight_pct": weight,
                "aspects": [{"id": key, "text": text, "option_tag": "Track one", "source_page": 1}],
            }
            for cid, rid, key, text, weight in criteria
        ],
        "excluded_aspects": [],
    }
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
                "anchor_sub_section_ids": ["A"],
            }
            for cid, _rid, key, text, _w in criteria
        ],
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
            for cid, rid, _key, _text, _w in criteria
        ],
        "registry_path": "syn/registry.json",
        "scorecard": {"path": "syn/scorecard.json", "scorecard_id": "syn_tri_scorecard", "version": "0.1"},
        "rubric_set": {"path": "syn/rubrics.json", "rubric_set_id": "syn_tri_rubrics", "version": "0.1.0"},
    }
    _write_json(root / "syn/registry.json", registry)
    _write_json(root / "syn/scorecard.json", scorecard)
    _write_json(root / "syn/rubrics.json", rubrics)
    return _write_json(root / "syn/profile.json", profile)


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    root = tmp_path_factory.mktemp("world")
    return load_profile_bundle(_synthetic_world(root), repo_root=root)


def _candidate(tmp_path: Path, bundle, *, drop: str | None = None) -> Path:
    """A candidate directory holding every profile-required section (minus *drop*),
    each with the anchor sub-sections its rubrics declare."""
    anchors: dict[str, list[str]] = {}
    for rubric in bundle.rubric_set.rubrics:
        for sid in bundle.profile.section_ids_for(rubric.criterion_id):
            anchors.setdefault(sid, []).extend(rubric.anchor_sub_section_ids)
    root = tmp_path / "candidate"
    for sid, ids in anchors.items():
        if sid == drop:
            continue
        _write_json(root / f"{sid}.json", _section(sorted(set(ids)) or ["1"]))
    return root


class ScriptedBackend:
    """Returns the scripted contents in a cycle and counts calls."""

    def __init__(self, *contents: str):
        self.contents = list(contents) or [PASS_JSON]
        self.calls = 0

    def __call__(self, messages):
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


def _assess(tmp_path, bundle, candidate, backend=None):
    return ba.assess_candidate(
        _judge(tmp_path, backend or ScriptedBackend()),
        bundle,
        candidate,
        clock=lambda: FROZEN,
    )


# --------------------------------------------------------------------------- #
# Binding: candidate hash, profile version, assessor pin
# --------------------------------------------------------------------------- #


class TestBinding:
    def test_report_and_every_cell_carry_the_three_pins(self, tmp_path, bundle):
        candidate = _candidate(tmp_path, bundle)
        report = _assess(tmp_path, bundle, candidate)
        expected_hash = ba.candidate_hash(ba.load_candidate(candidate, bundle.profile))
        assert report.candidate_hash == expected_hash
        assert report.candidate_hash.startswith("sha256:")
        assert report.profile_version == bundle.version
        assert report.assessor_pin == "fake-assessor@pin-7"
        assert report.assessed_at == FROZEN
        assert len(report.cells) == len(bundle.rubric_set.rubrics)
        for cell in report.cells:
            assert cell.candidate_hash == expected_hash
            assert cell.profile_version == bundle.version
            assert cell.assessor_pin == "fake-assessor@pin-7"
        data = report.to_dict()
        assert data["record_type"] == ba.BLIND_REPORT_RECORD_TYPE
        assert data["candidate_hash"] == expected_hash
        assert all(c["candidate_hash"] == expected_hash for c in data["cells"])
        assert all(c["profile_version"] == bundle.version for c in data["cells"])
        assert all(c["assessor_pin"] == "fake-assessor@pin-7" for c in data["cells"])

    def test_candidate_hash_is_formatting_invariant(self, tmp_path, bundle):
        candidate = _candidate(tmp_path, bundle)
        before = ba.candidate_hash(ba.load_candidate(candidate, bundle.profile))
        for path in candidate.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
        after = ba.candidate_hash(ba.load_candidate(candidate, bundle.profile))
        assert before == after

    def test_edited_candidate_rejects_the_report_naming_both_hashes(self, tmp_path, bundle):
        candidate = _candidate(tmp_path, bundle)
        report = _assess(tmp_path, bundle, candidate)
        path = ba.write_report(report, tmp_path / "reports")
        loaded = ba.load_report(path, candidate, bundle.profile)
        assert loaded["candidate_hash"] == report.candidate_hash

        section = next(candidate.glob("*.json"))
        data = json.loads(section.read_text(encoding="utf-8"))
        data["sub_sections"][0]["content"] += " An extra sentence."
        _write_json(section, data)
        current = ba.candidate_hash(ba.load_candidate(candidate, bundle.profile))
        with pytest.raises(ba.CandidateHashMismatch) as exc:
            ba.load_report(path, candidate, bundle.profile)
        assert report.candidate_hash in str(exc.value)
        assert current in str(exc.value)

    def test_report_loaded_against_a_different_profile_is_rejected(self, tmp_path, bundle):
        candidate = _candidate(tmp_path, bundle)
        report = _assess(tmp_path, bundle, candidate)
        path = ba.write_report(report, tmp_path / "reports")
        with pytest.raises(ba.BlindAssessmentError, match="profile"):
            ba.load_report(path, candidate, bundle.profile, profile_version="sha256:other")


# --------------------------------------------------------------------------- #
# Coverage scope
# --------------------------------------------------------------------------- #


class TestCoverageScope:
    def test_complete_candidate_is_labelled_complete(self, tmp_path, bundle):
        report = _assess(tmp_path, bundle, _candidate(tmp_path, bundle))
        assert report.scope == ba.SCOPE_COMPLETE
        assert report.partial_coverage == ()

    def test_missing_required_section_yields_partial_label_and_names_it(self, tmp_path, bundle):
        candidate = _candidate(tmp_path, bundle, drop="reach_section")
        report = _assess(tmp_path, bundle, candidate)
        assert report.scope == ba.SCOPE_PARTIAL
        assert [m.section_id for m in report.partial_coverage] == ["reach_section"]
        assert report.partial_coverage[0].criterion_id == "reach"
        assert all(c.section_id != "reach_section" for c in report.cells)
        assert {c.criterion_id for c in report.cells} == {"novelty", "feasibility"}
        data = report.to_dict()
        assert data["scope"] == "partial"
        assert data["partial_coverage"] == [
            {"criterion_id": "reach", "section_id": "reach_section", "reason": "missing"}
        ]
        assert "PARTIAL" in ba.render_report(data)

    def test_candidate_with_no_required_section_is_refused(self, tmp_path, bundle):
        empty = tmp_path / "empty"
        empty.mkdir()
        with pytest.raises(ba.BlindAssessmentError, match="none of the"):
            ba.load_candidate(empty, bundle.profile)

    def test_missing_candidate_directory_is_refused(self, tmp_path, bundle):
        with pytest.raises(ba.BlindAssessmentError, match="not a directory"):
            ba.load_candidate(tmp_path / "absent", bundle.profile)


# --------------------------------------------------------------------------- #
# Assessor behaviour: malformed responses fail, majority rule resolves
# --------------------------------------------------------------------------- #


class TestAssessor:
    def test_malformed_response_fails_the_run_and_writes_no_report(self, tmp_path, bundle):
        candidate = _candidate(tmp_path, bundle)
        judge = _judge(tmp_path, ScriptedBackend("not json at all"))
        with pytest.raises(JudgeResponseError):
            ba.assess_candidate(judge, bundle, candidate, clock=lambda: FROZEN)

    def test_panel_below_the_majority_minimum_is_refused(self, tmp_path, bundle):
        judge = _judge(tmp_path, ScriptedBackend())
        with pytest.raises(ba.BlindAssessmentError, match="majority"):
            ba.assess_candidate(judge, bundle, _candidate(tmp_path, bundle), n=2)

    def test_malformed_response_via_the_command_exits_2_and_writes_nothing(self, tmp_path, bundle):
        candidate = _candidate(tmp_path, bundle)
        out = tmp_path / "reports"
        judge = _judge(tmp_path, ScriptedBackend(PASS_JSON, '{"rationale": "no verdict"}'))
        code = cmd.main(
            preflighted(["assess", "--candidate", str(candidate), "--out-dir", str(out),
             "--repo-root", str(bundle.profile.source_path.parents[1]),
             "--profile", str(bundle.profile.source_path)]),
            judge=judge,
            clock=lambda: FROZEN,
        )
        assert code == 2
        assert not out.exists() or not list(out.iterdir())

    def test_disagreement_resolves_by_majority(self, tmp_path, bundle):
        candidate = _candidate(tmp_path, bundle)
        report = _assess(tmp_path, bundle, candidate, ScriptedBackend(PASS_JSON, FAIL_JSON, PASS_JSON))
        for cell in report.cells:
            assert cell.coverage.verdict.n == 3
            assert cell.coverage.judge_passed is True
            assert cell.coverage.verdict.agreement == pytest.approx(2 / 3)

    def test_tie_free_all_fail_is_not_covered(self, tmp_path, bundle):
        report = _assess(tmp_path, bundle, _candidate(tmp_path, bundle), ScriptedBackend(FAIL_JSON))
        assert all(c.coverage.judge_passed is False for c in report.cells)
        assert report.summary["covered"] == 0


# --------------------------------------------------------------------------- #
# Immutability and the advisory invariant
# --------------------------------------------------------------------------- #


class TestImmutability:
    def test_rerun_writes_a_new_report_and_leaves_the_first_byte_identical(self, tmp_path, bundle):
        candidate = _candidate(tmp_path, bundle)
        out = tmp_path / "reports"
        first = ba.write_report(_assess(tmp_path / "a", bundle, candidate), out)
        first_bytes = first.read_bytes()
        second = ba.write_report(_assess(tmp_path / "b", bundle, candidate), out)
        assert second != first
        assert second.is_file()
        assert first.read_bytes() == first_bytes
        assert sorted(p.name for p in out.iterdir()) == sorted([first.name, second.name])

    def test_writer_never_overwrites_an_existing_path(self, tmp_path, bundle):
        report = _assess(tmp_path, bundle, _candidate(tmp_path, bundle))
        out = tmp_path / "reports"
        path = ba.write_report(report, out)
        with pytest.raises(ba.BlindAssessmentError, match="exists"):
            ba.write_report(report, out, path=path)

    def test_report_cannot_be_constructed_blocking(self, tmp_path, bundle):
        report = _assess(tmp_path, bundle, _candidate(tmp_path, bundle))
        kwargs = {k: getattr(report, k) for k in report.__dataclass_fields__}
        with pytest.raises(ValueError, match="blocking"):
            ba.BlindAssessmentReport(**{**kwargs, "blocking": True})
        with pytest.raises(ValueError, match="advisory"):
            ba.BlindAssessmentReport(**{**kwargs, "advisory": False})
        assert report.advisory is True and report.blocking is False

    def test_report_refuses_a_cell_bound_to_another_candidate(self, tmp_path, bundle):
        report = _assess(tmp_path, bundle, _candidate(tmp_path, bundle))
        kwargs = {k: getattr(report, k) for k in report.__dataclass_fields__}
        foreign = ba.BlindCell(
            **{**report.cells[0].__dict__, "candidate_hash": "sha256:" + "0" * 64}
        )
        with pytest.raises(ValueError, match="candidate_hash"):
            ba.BlindAssessmentReport(**{**kwargs, "cells": (foreign,) + report.cells[1:]})

    def test_loaded_report_must_keep_the_invariant(self, tmp_path, bundle):
        candidate = _candidate(tmp_path, bundle)
        path = ba.write_report(_assess(tmp_path, bundle, candidate), tmp_path / "reports")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["blocking"] = True
        tampered = _write_json(tmp_path / "tampered.json", data)
        with pytest.raises(ba.BlindAssessmentError, match="blocking"):
            ba.load_report(tampered, candidate, bundle.profile)

    def test_loaded_report_rejects_a_cell_with_a_foreign_assessor_pin(self, tmp_path, bundle):
        candidate = _candidate(tmp_path, bundle)
        path = ba.write_report(_assess(tmp_path, bundle, candidate), tmp_path / "reports")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["cells"][0]["assessor_pin"] = "other@pin"
        tampered = _write_json(tmp_path / "tampered.json", data)
        with pytest.raises(ba.BlindAssessmentError, match="assessor_pin"):
            ba.load_report(tampered, candidate, bundle.profile)


# --------------------------------------------------------------------------- #
# The module command
# --------------------------------------------------------------------------- #


class TestCommand:
    def test_assess_writes_a_report_and_verify_accepts_it(self, tmp_path, bundle, capsys):
        candidate = _candidate(tmp_path, bundle)
        out = tmp_path / "reports"
        code = cmd.main(
            preflighted(["assess", "--candidate", str(candidate), "--out-dir", str(out),
             "--repo-root", str(bundle.profile.source_path.parents[1]),
             "--profile", str(bundle.profile.source_path)]),
            judge=_judge(tmp_path, DualBackend()),
            clock=lambda: FROZEN,
        )
        assert code == 0
        (path,) = list(out.iterdir())
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["assessor_pin"] == "fake-assessor@pin-7"
        assert data["profile_version"] == bundle.version
        printed = capsys.readouterr().out
        assert "BLIND ASSESSMENT" in printed
        assert data["candidate_hash"][:19] in printed

        code = cmd.main(
            ["verify", "--report", str(path), "--candidate", str(candidate),
             "--repo-root", str(bundle.profile.source_path.parents[1]),
             "--profile", str(bundle.profile.source_path)]
        )
        assert code == 0

    def test_verify_rejects_an_edited_candidate(self, tmp_path, bundle, capsys):
        candidate = _candidate(tmp_path, bundle)
        out = tmp_path / "reports"
        cmd.main(
            preflighted(["assess", "--candidate", str(candidate), "--out-dir", str(out),
             "--repo-root", str(bundle.profile.source_path.parents[1]),
             "--profile", str(bundle.profile.source_path)]),
            judge=_judge(tmp_path, DualBackend()),
            clock=lambda: FROZEN,
        )
        (path,) = list(out.iterdir())
        section = next(candidate.glob("*.json"))
        data = json.loads(section.read_text(encoding="utf-8"))
        data["sub_sections"][0]["content"] += " Edited."
        _write_json(section, data)
        code = cmd.main(
            ["verify", "--report", str(path), "--candidate", str(candidate),
             "--repo-root", str(bundle.profile.source_path.parents[1]),
             "--profile", str(bundle.profile.source_path)]
        )
        assert code == 2
        assert "hash" in capsys.readouterr().err

    def test_partial_candidate_exits_1(self, tmp_path, bundle):
        candidate = _candidate(tmp_path, bundle, drop="feasibility_section")
        code = cmd.main(
            preflighted(["assess", "--candidate", str(candidate), "--out-dir", str(tmp_path / "r"),
             "--repo-root", str(bundle.profile.source_path.parents[1]),
             "--profile", str(bundle.profile.source_path)]),
            judge=_judge(tmp_path, DualBackend()),
            clock=lambda: FROZEN,
        )
        assert code == 1

    def test_command_is_registered(self):
        from harness.commands import __all__ as commands

        assert "blind_assessment" in commands
        assert not (REPO_ROOT / "scripts" / "blind_assessment.py").exists()


# --------------------------------------------------------------------------- #
# PE-04: include_claims, the two-value cell, and the criterion-scoring stage
# --------------------------------------------------------------------------- #

CRITERION_JSON = json.dumps(
    {"score": 4.0, "shortcomings": ["one named shortcoming"], "strengths": ["s"],
     "rationale": "scripted criterion score"}
)


class DualBackend:
    """Cell JSON for rubric prompts, criterion JSON for criterion prompts; counts both."""

    def __init__(self, cell: str = PASS_JSON, criterion: str = CRITERION_JSON):
        self.cell, self.criterion = cell, criterion
        self.calls = self.cell_calls = self.criterion_calls = 0
        self.prompts: list[tuple[str, str]] = []

    def __call__(self, messages):
        system = "\n".join(m["content"] for m in messages if m["role"] == "system")
        user = "\n".join(m["content"] for m in messages if m["role"] == "user")
        self.prompts.append((system, user))
        self.calls += 1
        if "CRITERION UNDER ASSESSMENT" in system:
            self.criterion_calls += 1
            return {"content": self.criterion}
        self.cell_calls += 1
        return {"content": self.cell}


class TestCriterionScoringInReport:
    def test_the_library_default_scores_no_criteria_and_includes_claims(self, tmp_path, bundle):
        report = _assess(tmp_path, bundle, _candidate(tmp_path, bundle))
        assert report.criterion_scoring is None
        assert report.include_claims is True
        data = report.to_dict()
        assert data["criterion_scoring"] is None
        assert data["include_claims"] is True
        for cell in data["cells"]:
            assert cell["addressal"] == cell["covered"]
            assert cell["grounding"] == ba.GROUNDING_IN_VERDICT

    def test_criterion_scores_are_bound_and_total_follows_the_scorecard(self, tmp_path, bundle):
        backend = DualBackend()
        candidate = _candidate(tmp_path, bundle)
        report = ba.assess_candidate(
            _judge(tmp_path, backend), bundle, candidate, clock=lambda: FROZEN, criterion_samples=5
        )
        assert backend.cell_calls == 3 * len(bundle.rubric_set.rubrics)
        assert backend.criterion_calls == 5 * len(bundle.profile.criteria)
        cs = report.criterion_scoring
        assert cs is not None
        assert cs.samples_per_criterion == 5
        # weights 60/25/15 over 0-10 to 100 -> factors 6, 2.5, 1.5; every score 4.0
        assert cs.total == pytest.approx(4.0 * (6 + 2.5 + 1.5))
        assert cs.formula == "S = 6*novelty + 2.5*reach + 1.5*feasibility"
        assert cs.overall_threshold_met is False  # 40 < 60
        assert cs.individual_threshold is None and cs.individual_thresholds_met is None
        for score in cs.scores:
            assert score.candidate_hash == report.candidate_hash
            assert score.profile_version == report.profile_version
            assert score.assessor_pin == report.assessor_pin
            assert score.aspect_findings_attached is True
            assert score.input_hash.startswith("sha256:")
        data = report.to_dict()
        assert data["criterion_scoring"]["total"] == pytest.approx(40.0)
        assert all(s["candidate_hash"] == report.candidate_hash for s in data["criterion_scoring"]["scores"])
        rendered = ba.render_report(data)
        assert "CRITERION SCORES" in rendered and "40.00" in rendered

    def test_the_criterion_scorer_reads_the_section_and_the_findings_follow_it(self, tmp_path, bundle):
        backend = DualBackend()
        ba.assess_candidate(
            _judge(tmp_path, backend), bundle, _candidate(tmp_path, bundle),
            clock=lambda: FROZEN, criterion_samples=3,
        )
        criterion_prompts = [(s, u) for s, u in backend.prompts if "CRITERION UNDER ASSESSMENT" in s]
        assert criterion_prompts
        for _system, user in criterion_prompts:
            assert TEXT.split("\n\n")[0] in user          # the section, verbatim
            assert "EVIDENCE PACK" not in user            # never a pack
            assert "HARNESS FINDINGS" in user             # the cells accompany it
            assert user.index("CRITERION SECTION") < user.index("HARNESS FINDINGS")

    def test_a_partial_candidate_leaves_the_total_undetermined(self, tmp_path, bundle):
        report = ba.assess_candidate(
            _judge(tmp_path, DualBackend()), bundle, _candidate(tmp_path, bundle, drop="reach_section"),
            clock=lambda: FROZEN, criterion_samples=3,
        )
        cs = report.criterion_scoring
        assert cs.total is None and cs.overall_threshold_met is None
        assert cs.unscored_criteria == ("reach",)
        reach = next(s for s in cs.scores if s.criterion_id == "reach")
        assert reach.status == "not_scored" and reach.samples == ()

    def test_report_refuses_a_criterion_score_bound_to_another_candidate(self, tmp_path, bundle):
        import dataclasses

        report = ba.assess_candidate(
            _judge(tmp_path, DualBackend()), bundle, _candidate(tmp_path, bundle),
            clock=lambda: FROZEN, criterion_samples=3,
        )
        cs = report.criterion_scoring
        foreign = dataclasses.replace(cs.scores[0], candidate_hash="sha256:" + "0" * 64)
        tampered = dataclasses.replace(cs, scores=(foreign,) + cs.scores[1:])
        kwargs = {k: getattr(report, k) for k in report.__dataclass_fields__}
        with pytest.raises(ValueError, match="criterion score"):
            ba.BlindAssessmentReport(**{**kwargs, "criterion_scoring": tampered})

    def test_loaded_report_rejects_a_criterion_score_with_a_foreign_pin(self, tmp_path, bundle):
        candidate = _candidate(tmp_path, bundle)
        report = ba.assess_candidate(
            _judge(tmp_path, DualBackend()), bundle, candidate, clock=lambda: FROZEN, criterion_samples=3
        )
        path = ba.write_report(report, tmp_path / "reports")
        data = json.loads(path.read_text(encoding="utf-8"))
        data["criterion_scoring"]["scores"][0]["assessor_pin"] = "other@pin"
        tampered = _write_json(tmp_path / "tampered.json", data)
        with pytest.raises(ba.BlindAssessmentError, match="assessor_pin"):
            ba.load_report(tampered, candidate, bundle.profile)
        assert ba.load_report(path, candidate, bundle.profile)["criterion_scoring"]["total"] is not None

    def test_no_claims_withholds_the_ledger_and_marks_grounding_unassessable(self, tmp_path, bundle):
        report = ba.assess_candidate(
            _judge(tmp_path, ScriptedBackend()), bundle, _candidate(tmp_path, bundle),
            clock=lambda: FROZEN, include_claims=False,
        )
        assert report.include_claims is False
        for cell in report.cells:
            assert cell.coverage.pack_record["include_claims"] is False
            assert cell.coverage.pack_record["claims"] == []
            assert cell.to_dict()["grounding"] == ba.GROUNDING_UNASSESSABLE
        assert report.to_dict()["include_claims"] is False


class TestCommandCriterionScoring:
    def _args(self, bundle, candidate, out):
        return ["assess", "--candidate", str(candidate), "--out-dir", str(out),
                "--repo-root", str(bundle.profile.source_path.parents[1]),
                "--profile", str(bundle.profile.source_path)]

    def test_assess_scores_criteria_by_default_with_five_samples(self, tmp_path, bundle):
        backend = DualBackend()
        out = tmp_path / "reports"
        code = cmd.main(preflighted(self._args(bundle, _candidate(tmp_path, bundle), out)),
                        judge=_judge(tmp_path, backend), clock=lambda: FROZEN)
        assert code == 0
        (path,) = list(out.iterdir())
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["criterion_scoring"]["samples_per_criterion"] == 5
        assert backend.criterion_calls == 5 * len(bundle.profile.criteria)
        assert data["include_claims"] is True

    def test_skip_and_no_claims_flags(self, tmp_path, bundle):
        out = tmp_path / "reports"
        code = cmd.main(
            preflighted(self._args(bundle, _candidate(tmp_path, bundle), out) + ["--skip-criterion-scores", "--no-claims"]),
            judge=_judge(tmp_path, ScriptedBackend()), clock=lambda: FROZEN,
        )
        assert code == 0
        (path,) = list(out.iterdir())
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["criterion_scoring"] is None
        assert data["include_claims"] is False

    def test_criterion_n_below_the_minimum_exits_2(self, tmp_path, bundle):
        out = tmp_path / "reports"
        code = cmd.main(preflighted(self._args(bundle, _candidate(tmp_path, bundle), out) + ["--criterion-n", "2"]),
                        judge=_judge(tmp_path, DualBackend()), clock=lambda: FROZEN)
        assert code == 2
        assert not out.exists() or not list(out.iterdir())
