"""
ESR comparison over a frozen blind baseline (spec PE-08).

Three groups:

* Unit rules over the synthetic world: every declared reference is resolved or
  the comparison is refused by name; each disposition needs the basis the
  ticket gives it; nothing is written on refusal.
* The ``compare`` command end to end: bindings, the summary that counts
  "not assessable" separately and never as a failure, the score table kept
  apart from the rows, and the revisions artifact in derived priority order.
* The committed MSCA-DN artifacts: the operator's ESR record and dispositions
  resolve against the committed frozen baseline, so every historical
  observation has a traceable disposition (the ticket's acceptance).
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import harness.blind_baseline as bb
import harness.commands.blind_assessment as cmd
import harness.esr_comparison as ec
from harness.blind_assessment import candidate_hash, load_candidate
from harness.integrity_audit import AUDIT_RECORD_TYPE
from harness.rubrics import load_profile_bundle
from runner.dev_graph import record_esr_intake
from runner.paths import find_repo_root
from tests.harness.test_blind_baseline import (
    TRANSPORT,
    VERSION,
    _assess,
    _candidate_dir,
    _freeze,
    _write_json,
    bundle,  # noqa: F401 - fixture
    world,  # noqa: F401 - fixture
)
from tests.harness.test_blind_leakage import FROZEN, RecordingBackend

REPO = find_repo_root()
DN_BASELINE = REPO / "docs/tier4_orchestration_state/msca_dn/baselines/resolved_fixes_2026-10-06"
DN_ESR = REPO / "docs/tier4_orchestration_state/msca_dn/esr/msca-dn-2025-esr.json"
DN_DISPOSITIONS = REPO / "docs/tier4_orchestration_state/msca_dn/esr/dispositions_f60ae6e0a2a1.json"
DN_CANDIDATES = REPO / "docs/tier4_orchestration_state/msca_dn/audit/candidates"
DN_REGISTER = REPO / "docs/tier3_project_instantiation/source_materials/msca_dn/fidelity_register_resolved_fixes.json"
DN_AUDITS = [
    "docs/tier4_orchestration_state/msca_dn/audit/integrity_242f1afb02c8_0001.json",
    "docs/tier4_orchestration_state/msca_dn/audit/integrity_13ad3ad81d7e_0001.json",
]
DN_PROFILE = REPO / "harness/profiles/msca_dn_2026_default.json"


# --------------------------------------------------------------------------- #
# Fixtures: a frozen synthetic baseline, an ESR record and dispositions for it
# --------------------------------------------------------------------------- #


@pytest.fixture
def frozen_world(world, bundle):
    """The synthetic world with a report assessed under an intake and frozen as the baseline."""
    record_esr_intake(
        world, intake_id="INTAKE-1", document_id="CAND-1", submission_id="SUB-1",
        call_id="SYN-CALL-01", permitted_purpose="blind_pre_evaluation", prior_submission=True,
    )
    code, report = _assess(world, bundle, RecordingBackend(), "--intake", "INTAKE-1")
    assert code == 0
    baseline = world / "docs" / "tier4_orchestration_state" / "baseline"
    assert _freeze(world, bundle, report, baseline) == 0
    frozen = bb.load_frozen_baseline(baseline)
    return world, bundle, baseline, frozen


def _esr(intake_id: str = "INTAKE-1") -> dict:
    return {
        "record_type": ec.ESR_RECORD_TYPE,
        "schema_version": "1.0",
        "intake_id": intake_id,
        "source": {"path": "docs/tier5_deliverables/candidates/synthetic_esr.json", "sha256": "0" * 64},
        "evaluation_result": {
            "total": 80.0,
            "overall_threshold": 70,
            "criteria": [
                {"criterion_id": "aims", "score": 4.0, "threshold": 3, "weight_pct": 50},
                {"criterion_id": "plan", "score": 4.5, "threshold": 3, "weight_pct": 30},
                {"criterion_id": "outputs", "score": 3.5, "threshold": 3, "weight_pct": 20},
            ],
        },
        "observations": [
            {"id": "OBS-1", "criterion_id": "aims", "aspect_id": "aims-objectives",
             "kind": "shortcoming", "severity_wording": "This is a shortcoming.",
             "text": "Objective two is not measurable.", "esr_location": {"page": 1},
             "proposal_location": ["S1"]},
            {"id": "OBS-2", "criterion_id": "plan", "aspect_id": "plan-tasks",
             "kind": "minor_shortcoming", "severity_wording": "This is a minor shortcoming.",
             "text": "Task three starts late.", "esr_location": {"page": 2},
             "proposal_location": ["S2"]},
            {"id": "OBS-3", "criterion_id": "outputs", "aspect_id": "outputs-deliverables",
             "kind": "strength", "severity_wording": None,
             "text": "Deliverables are well defined.", "esr_location": {"page": 2},
             "proposal_location": ["S3"]},
            {"id": "OBS-4", "criterion_id": "outputs", "aspect_id": "outputs-deliverables",
             "kind": "minor_shortcoming", "severity_wording": "This is a minor shortcoming.",
             "text": "The validation of deliverable one is unclear.", "esr_location": {"page": 2},
             "proposal_location": ["S3"]},
        ],
    }


def _register() -> dict:
    return {
        "record_type": "fidelity_register",
        "derived": {"figures": {"images_on_any_page": 0}, "sub_sections": [
            {"sub_section_id": "S1", "characters": 70}, {"sub_section_id": "S3", "characters": 60},
        ]},
        "declared": {"sub_sections": []},
        "provenance": {"transformation": {"citations": "all removed"}},
    }


def _rows(frozen_sha: str, esr_sha: str) -> dict:
    return {
        "record_type": ec.DISPOSITIONS_RECORD_TYPE,
        "schema_version": "1.0",
        "baseline_report_sha256": frozen_sha,
        "esr_record_sha256": esr_sha,
        "declared_by": "test operator",
        "declared_on": "2026-10-07",
        "rows": [
            {
                "observation_id": "OBS-1",
                "disposition": "independently_detected",
                "declared_status": "Inferred",
                "blind_findings": [{"kind": "criterion_shortcoming", "criterion_id": "aims",
                                    "sample_index": 0, "index": 0}],
                "current_evidence": [{"section_id": "S1", "sub_section_id": "S1",
                                      "quote": "objective one and objective two"}],
                "explanation": "The blind lane names it.",
                "proposed_revision": {"text": "Give objective two a target.", "declared_status": "Assumed"},
            },
            {
                "observation_id": "OBS-2",
                "disposition": "not_detected_despite_sufficient_preserved_evidence",
                "declared_status": "Inferred",
                "evidence_preserved_status": "Assumed",
                "current_evidence": [{"section_id": "S2", "sub_section_id": "S2",
                                      "quote": "It starts in month ten."}],
                "explanation": "The sentence survives and no finding names it.",
                "proposed_revision": {"text": "Start task three in month four.", "declared_status": "Assumed"},
            },
            {
                "observation_id": "OBS-3",
                "disposition": "independently_detected",
                "declared_status": "Inferred",
                "blind_findings": [{"kind": "criterion_strength", "criterion_id": "outputs",
                                    "sample_index": 1, "index": 0},
                                   {"kind": "cell", "expectation_key": "outputs-deliverables"}],
                "explanation": "A blind strength agrees.",
            },
            {
                "observation_id": "OBS-4",
                "disposition": "not_assessable_from_this_copy",
                "declared_status": "Assumed",
                "evidence_basis": ["derived/figures/images_on_any_page",
                                   "provenance/transformation/citations"],
                "explanation": "The validation figure was removed.",
                "proposed_revision": {"text": "Restore the validation figure.", "declared_status": "Assumed"},
            },
        ],
    }


@pytest.fixture
def inputs(frozen_world, tmp_path: Path):
    """ESR record, dispositions and register written for the frozen world."""
    world, bundle_, baseline, frozen = frozen_world
    esr_path = _write_json(world / "docs" / "esr" / "esr.json", _esr())
    esr = ec.load_esr_record(esr_path)
    disp_path = _write_json(
        world / "docs" / "esr" / "dispositions.json",
        _rows(frozen.record["report_sha256"], esr.sha256),
    )
    reg_path = _write_json(world / "docs" / "register.json", _register())
    return {
        "world": world, "bundle": bundle_, "baseline": baseline, "frozen": frozen,
        "esr": esr_path, "dispositions": disp_path, "register": reg_path,
        "candidate": _candidate_dir(world),
    }


def _compare(inputs, *extra: str, out: Path | None = None) -> tuple[int, Path]:
    world = inputs["world"]
    out = out or (world / "comparisons")
    code = cmd.main(
        [
            "compare", "--baseline-dir", str(inputs["baseline"]), "--esr", str(inputs["esr"]),
            "--dispositions", str(inputs["dispositions"]), "--candidate", str(inputs["candidate"]),
            "--register", str(inputs["register"]), "--repo-root", str(world),
            "--profile", str(inputs["bundle"].profile.source_path), "--out-dir", str(out), *extra,
        ],
        clock=lambda: FROZEN,
    )
    return code, out


def _rewrite(inputs, mutate) -> None:
    """Edit the dispositions in place through *mutate(data)*."""
    path = inputs["dispositions"]
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    _write_json(path, data)


def _row(data: dict, oid: str) -> dict:
    return next(r for r in data["rows"] if r["observation_id"] == oid)


# --------------------------------------------------------------------------- #
# Loading and binding
# --------------------------------------------------------------------------- #


class TestLoading:
    def test_esr_record_refuses_unknown_kind(self, tmp_path):
        data = _esr()
        data["observations"][0]["kind"] = "nitpick"
        with pytest.raises(ec.EsrComparisonError, match="kind 'nitpick'"):
            ec.load_esr_record(_write_json(tmp_path / "esr.json", data))

    def test_esr_record_refuses_repeated_id(self, tmp_path):
        data = _esr()
        data["observations"][1]["id"] = "OBS-1"
        with pytest.raises(ec.EsrComparisonError, match="repeated"):
            ec.load_esr_record(_write_json(tmp_path / "esr.json", data))

    def test_esr_record_refuses_empty_text(self, tmp_path):
        data = _esr()
        data["observations"][0]["text"] = "  "
        with pytest.raises(ec.EsrComparisonError, match="empty text"):
            ec.load_esr_record(_write_json(tmp_path / "esr.json", data))

    def test_dispositions_refuse_a_row_disposed_twice(self, tmp_path):
        data = _rows("a" * 64, "b" * 64)
        data["rows"].append(dict(data["rows"][0]))
        with pytest.raises(ec.EsrComparisonError, match="disposed twice"):
            ec.load_dispositions(_write_json(tmp_path / "d.json", data))

    def test_dispositions_bound_to_another_baseline_are_refused(self, inputs, capsys):
        _rewrite(inputs, lambda d: d.update(baseline_report_sha256="f" * 64))
        code, out = _compare(inputs)
        assert code == 2
        assert "bound to baseline report ffffffffffff" in capsys.readouterr().err
        assert not out.exists()

    def test_dispositions_bound_to_another_esr_record_are_refused(self, inputs, capsys):
        _rewrite(inputs, lambda d: d.update(esr_record_sha256="e" * 64))
        code, _ = _compare(inputs)
        assert code == 2
        assert "another ESR record" in capsys.readouterr().err

    def test_candidate_that_is_not_the_baselines_is_refused(self, inputs, capsys):
        other = inputs["world"] / "other_candidate"
        other.mkdir()
        for p in inputs["candidate"].iterdir():
            data = json.loads(p.read_text(encoding="utf-8"))
            data["sub_sections"][0]["content"] += " (edited)"
            _write_json(other / p.name, data)
        inputs = dict(inputs, candidate=other)
        code, _ = _compare(inputs)
        assert code == 2
        assert "frozen baseline is bound to" in capsys.readouterr().err

    def test_esr_for_another_intake_is_refused(self, inputs, capsys):
        esr = _write_json(inputs["world"] / "docs" / "esr" / "other.json", _esr("INTAKE-9"))
        sha = ec.load_esr_record(esr).sha256
        _rewrite(inputs, lambda d: d.update(esr_record_sha256=sha))
        code, _ = _compare(dict(inputs, esr=esr))
        assert code == 2
        assert "intake 'INTAKE-9'" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# Every observation disposed; every reference resolved
# --------------------------------------------------------------------------- #


class TestTraceability:
    def test_an_observation_without_a_disposition_is_refused(self, inputs, capsys):
        _rewrite(inputs, lambda d: d["rows"].pop())
        code, out = _compare(inputs)
        assert code == 2
        assert "have no disposition: OBS-4" in capsys.readouterr().err
        assert not out.exists()

    def test_a_disposition_for_an_unknown_observation_is_refused(self, inputs, capsys):
        _rewrite(inputs, lambda d: d["rows"].append(dict(d["rows"][0], observation_id="OBS-9")))
        code, _ = _compare(inputs)
        assert code == 2
        assert "the ESR record does not: OBS-9" in capsys.readouterr().err

    def test_an_unknown_disposition_is_refused(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-1").update(disposition="probably_fine"))
        code, _ = _compare(inputs)
        assert code == 2
        assert "disposition 'probably_fine'" in capsys.readouterr().err

    def test_a_blind_reference_that_does_not_resolve_is_refused(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-1")["blind_findings"][0].update(index=7))
        code, _ = _compare(inputs)
        assert code == 2
        assert "has no shortcoming 7" in capsys.readouterr().err

    def test_a_quote_not_in_the_candidate_is_refused(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-1")["current_evidence"][0].update(quote="objective nine"))
        code, out = _compare(inputs)
        assert code == 2
        assert "is not found in S1/S1" in capsys.readouterr().err
        assert not out.exists()

    def test_a_quote_is_matched_with_whitespace_and_ligatures_folded(self, inputs):
        _rewrite(inputs, lambda d: _row(d, "OBS-1")["current_evidence"][0].update(
            quote="objective   one and\nobjective two"))
        code, _ = _compare(inputs)
        assert code == 0

    def test_a_register_pointer_that_does_not_resolve_is_refused(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-4").update(evidence_basis=["derived/figures/nope"]))
        code, _ = _compare(inputs)
        assert code == 2
        assert "no key 'nope'" in capsys.readouterr().err

    def test_an_audit_reference_needs_the_audit_on_the_command_line(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-1").update(
            audit_findings=[{"report": "audits/a.json", "check": "x", "index": 0}]))
        code, _ = _compare(inputs)
        assert code == 2
        assert "was not given to the command" in capsys.readouterr().err

    def test_an_audit_over_another_candidate_is_refused(self, inputs, capsys):
        audit = _write_json(inputs["world"] / "audits" / "a.json", {
            "record_type": AUDIT_RECORD_TYPE, "advisory": True, "blocking": False,
            "candidate_hash": "sha256:" + "1" * 64, "profile_version": "x",
            "checks": [{"check_id": "x", "findings": [{"kind": "k", "subject": "s", "detail": "d"}]}],
            "grounding": {}, "baseline": {},
        })
        code, _ = _compare(inputs, "--audit", str(audit))
        assert code == 2
        assert "neither the current nor the historical candidate" in capsys.readouterr().err

    def test_an_audit_finding_is_quoted_and_the_lane_recorded(self, inputs):
        digest = candidate_hash(load_candidate(inputs["candidate"], inputs["bundle"].profile))
        audit = _write_json(inputs["world"] / "audits" / "a.json", {
            "record_type": AUDIT_RECORD_TYPE, "advisory": True, "blocking": False,
            "candidate_hash": digest, "profile_version": "x",
            "checks": [{"check_id": "x", "findings": [{"kind": "k", "subject": "s", "detail": "the detail"}]}],
            "grounding": {}, "baseline": {},
        })
        _rewrite(inputs, lambda d: _row(d, "OBS-1").update(
            audit_findings=[{"report": "audits/a.json", "check": "x", "index": 0}]))
        code, out = _compare(inputs, "--audit", "audits/a.json")
        assert code == 0
        data = ec.load_comparison(next(out.glob("comparison_*.json")))
        row = _row(data, "OBS-1")
        assert row["audit_findings"][0]["text"] == "the detail"
        assert row["detected_by"] == sorted([ec.LANE_AUDIT, ec.LANE_BLIND])
        assert data["audits"][0]["path"] == "audits/a.json"


# --------------------------------------------------------------------------- #
# Disposition rules
# --------------------------------------------------------------------------- #


class TestDispositionRules:
    def test_independently_detected_needs_a_finding(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-1").update(blind_findings=[]))
        code, _ = _compare(inputs)
        assert code == 2
        assert "'independently_detected' needs at least one" in capsys.readouterr().err

    def test_not_detected_cannot_cite_a_finding(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-2").update(
            blind_findings=[{"kind": "criterion_shortcoming", "criterion_id": "plan",
                             "sample_index": 0, "index": 0}]))
        code, _ = _compare(inputs)
        assert code == 2
        assert "cannot cite a finding" in capsys.readouterr().err

    def test_not_detected_needs_the_preserved_passage(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-2").update(current_evidence=[]))
        code, _ = _compare(inputs)
        assert code == 2
        assert "needs the preserved passage" in capsys.readouterr().err

    def test_not_detected_needs_a_declared_preservation_status(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-2").pop("evidence_preserved_status"))
        code, _ = _compare(inputs)
        assert code == 2
        assert "'evidence_preserved_status' is required" in capsys.readouterr().err

    def test_not_assessable_needs_a_register_entry(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-4").update(evidence_basis=[]))
        code, _ = _compare(inputs)
        assert code == 2
        assert "needs a fidelity-register entry" in capsys.readouterr().err

    def test_partially_observable_needs_a_finding_and_a_register_entry(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-1").update(disposition="partially_observable"))
        code, _ = _compare(inputs)
        assert code == 2
        assert "'partially_observable' needs a fidelity-register entry" in capsys.readouterr().err
        _rewrite(inputs, lambda d: _row(d, "OBS-1").update(evidence_basis=["derived/figures"]))
        code, out = _compare(inputs)
        assert code == 0
        det = ec.load_comparison(next(out.glob("comparison_*.json")))["summary"]["detection"]
        assert det["partially_observable"] == 1 and det["independently_detected"] == 0
        assert det["rate_detected"] == 0.0 and det["rate_detected_or_partial"] == 0.5

    def test_addressed_needs_both_copies(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-1").update(disposition="addressed"))
        code, _ = _compare(inputs)
        assert code == 2
        assert "'addressed' needs a verified quote from the historical copy" in capsys.readouterr().err

    def test_addressed_resolves_against_the_historical_candidate(self, inputs):
        historical = inputs["world"] / "historical_candidate"
        historical.mkdir()
        for p in inputs["candidate"].iterdir():
            data = json.loads(p.read_text(encoding="utf-8"))
            if data["section_id"] == "S1":
                data["sub_sections"][0]["content"] = "The project pursues objective one only."
            _write_json(historical / p.name, data)

        def mutate(d):
            _row(d, "OBS-1").update(
                disposition="addressed", blind_findings=[],
                historical_evidence=[{"section_id": "S1", "sub_section_id": "S1",
                                      "quote": "objective one only"}],
            )
        _rewrite(inputs, mutate)
        code, out = _compare(inputs, "--historical-candidate", str(historical))
        assert code == 0
        data = ec.load_comparison(next(out.glob("comparison_*.json")))
        row = _row(data, "OBS-1")
        assert row["historical_proposal_evidence"]["quotes"][0]["verified"] is True
        assert row["counted_in_detection_rate"] is False
        assert data["historical_candidate"]["candidate_hash"] != data["candidate"]["candidate_hash"]

    def test_current_quotes_stand_for_the_historical_copy_when_they_occur_there(self, inputs):
        historical = inputs["world"] / "historical_candidate"
        historical.mkdir()
        for p in inputs["candidate"].iterdir():
            data = json.loads(p.read_text(encoding="utf-8"))
            if data["section_id"] == "S2":
                data["sub_sections"][0]["content"] = "Task three is led by Participant B. It starts in month nine."
            _write_json(historical / p.name, data)
        code, out = _compare(inputs, "--historical-candidate", str(historical))
        assert code == 0
        data = ec.load_comparison(next(out.glob("comparison_*.json")))
        # OBS-1 quotes S1, unchanged in the historical copy: re-verified there
        q = _row(data, "OBS-1")["historical_proposal_evidence"]["quotes"]
        assert q and q[0]["same_as_current"] is True and q[0]["verified"] is True
        # OBS-2 quotes a sentence the historical copy does not carry: no quote
        assert _row(data, "OBS-2")["historical_proposal_evidence"]["quotes"] == []

    def test_a_strength_cannot_be_addressed(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-3").update(disposition="addressed"))
        code, _ = _compare(inputs)
        assert code == 2
        assert "a strength cannot be 'addressed'" in capsys.readouterr().err

    def test_a_declared_status_outside_the_four_categories_is_refused(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-1").update(declared_status="Probable"))
        code, _ = _compare(inputs)
        assert code == 2
        assert "'declared_status' is 'Probable'" in capsys.readouterr().err

    def test_a_proposed_revision_needs_a_declared_status_in_the_four_categories(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-1")["proposed_revision"].update(declared_status="Likely"))
        code, _ = _compare(inputs)
        assert code == 2
        assert "(proposed_revision): 'declared_status' is 'Likely'" in capsys.readouterr().err

    def test_an_evidence_preserved_status_outside_the_categories_is_refused_on_any_row(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-1").update(evidence_preserved_status="yes"))
        code, _ = _compare(inputs)
        assert code == 2
        assert "'evidence_preserved_status' is 'yes'" in capsys.readouterr().err

    def test_a_register_that_is_not_a_register_is_refused(self, inputs, capsys):
        bad = _write_json(inputs["world"] / "docs" / "not_register.json", {"record_type": "other"})
        code, _ = _compare(dict(inputs, register=bad))
        assert code == 2
        assert "is not a 'fidelity_register' record" in capsys.readouterr().err

    def test_an_esr_score_that_is_not_a_number_is_refused(self, tmp_path):
        data = _esr()
        data["evaluation_result"]["criteria"][0]["score"] = "4.0"
        with pytest.raises(ec.EsrComparisonError, match="non-numeric 'score'"):
            ec.load_esr_record(_write_json(tmp_path / "esr.json", data))

    def test_an_explanation_is_required(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-1").update(explanation=""))
        code, _ = _compare(inputs)
        assert code == 2
        assert "an explanation is required" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# The report: bindings, summary, scores, revisions, immutability
# --------------------------------------------------------------------------- #


class TestReport:
    def test_bindings_and_row_shape(self, inputs):
        code, out = _compare(inputs)
        assert code == 0
        data = ec.load_comparison(next(out.glob("comparison_*.json")))
        frozen = inputs["frozen"]
        assert data["advisory"] is True and data["blocking"] is False
        assert data["baseline"]["report_sha256"] == frozen.record["report_sha256"]
        assert data["baseline"]["candidate_hash"] == frozen.record["bindings"]["candidate_hash"]
        assert data["baseline"]["assessor_pin"] == f"fake-assessor@{VERSION}"
        assert data["baseline"]["assessor_transport"] == TRANSPORT
        assert data["candidate"]["candidate_hash"] == data["baseline"]["candidate_hash"]
        assert data["esr_record"]["sha256"] and data["dispositions"]["sha256"]
        assert data["fidelity_register"]["sha256"]
        assert data["dispositions_vocabulary"] == list(ec.DISPOSITIONS)
        assert len(data["rows"]) == 4
        row = _row(data, "OBS-1")
        for key in ("historical_finding", "historical_location", "criterion_id", "aspect_id",
                    "historical_proposal_evidence", "current_proposal_evidence", "blind_findings",
                    "disposition", "explanation"):
            assert key in row
        assert row["blind_findings"][0]["text"] == "one named shortcoming"
        assert row["blind_findings"][0]["polarity"] == "shortcoming"
        assert row["current_proposal_evidence"][0]["verified"] is True
        assert row["detected_by"] == [ec.LANE_BLIND]
        assert row["blind_cell"]["covered"] is True

    def test_not_assessable_is_counted_separately_and_never_as_failure(self, inputs):
        _code, out = _compare(inputs)
        s = ec.load_comparison(next(out.glob("comparison_*.json")))["summary"]
        assert s["observations"] == 4
        assert s["not_assessable"] == 1
        assert s["assessable"] == 3
        assert s["assessable_fraction"] == 0.75
        assert s["not_assessable_counted_as_failure"] is False
        assert s["not_assessable_dropped"] is False
        assert s["by_disposition"]["not_assessable_from_this_copy"] == 1
        det = s["detection"]
        # OBS-1 detected, OBS-2 missed; OBS-3 is a strength, OBS-4 not assessable
        assert det["rated"] == 2
        assert det["independently_detected"] == 1 and det["not_detected"] == 1
        assert det["rate_detected"] == 0.5 and det["rate_detected_or_partial"] == 0.5
        assert det["by_lane"] == {ec.LANE_BLIND: 1, ec.LANE_AUDIT: 0}
        assert s["by_criterion"]["outputs"]["not_assessable"] == 1
        assert s["by_criterion"]["outputs"]["detection"]["rated"] == 0
        assert s["by_criterion"]["outputs"]["detection"]["rate_detected"] is None

    def test_a_blind_shortcoming_on_a_praised_point_is_flagged_as_contested(self, inputs):
        _rewrite(inputs, lambda d: _row(d, "OBS-3")["blind_findings"].append(
            {"kind": "criterion_shortcoming", "criterion_id": "outputs", "sample_index": 2, "index": 0}))
        _code, out = _compare(inputs)
        data = ec.load_comparison(next(out.glob("comparison_*.json")))
        assert _row(data, "OBS-3")["contests_historical_strength"] is True
        assert data["summary"]["strengths_contested_by_blind_findings"] == 1
        revisions = json.loads(next(out.glob("revisions_*.json")).read_text(encoding="utf-8"))
        assert [e["observation_id"] for e in revisions["contested_strengths"]] == ["OBS-3"]

    def test_scores_are_compared_apart_from_the_rows(self, inputs):
        _code, out = _compare(inputs)
        data = ec.load_comparison(next(out.glob("comparison_*.json")))
        sc = data["score_comparison"]
        by_id = {c["criterion_id"]: c for c in sc["criteria"]}
        assert by_id["aims"]["historical_score"] == 4.0
        assert by_id["aims"]["blind_median"] == 4.0 and by_id["aims"]["difference"] == 0.0
        assert by_id["plan"]["historical_score"] == 4.5 and by_id["plan"]["difference"] == -0.5
        assert by_id["aims"]["blind_spread"] is not None and by_id["aims"]["blind_samples"] >= 5
        assert sc["total"]["historical"] == 80.0
        assert sc["total"]["blind"] == data["score_comparison"]["total"]["blind"]
        assert sc["no_deduction_attributed_to_individual_criticism"] is True
        assert "not interpretable as model error" in sc["statement"]
        assert "repeatability" in sc["spread_label"]
        # no row carries a score delta
        assert all("score_delta" not in r and "deduction" not in r for r in data["rows"])

    def test_revisions_are_a_separate_artifact_in_derived_priority_order(self, inputs):
        _code, out = _compare(inputs)
        data = ec.load_comparison(next(out.glob("comparison_*.json")))
        rev_path = next(out.glob("revisions_*.json"))
        assert data["revisions_artifact"].endswith(rev_path.name)
        rev = json.loads(rev_path.read_text(encoding="utf-8"))
        assert rev["record_type"] == ec.REVISIONS_RECORD_TYPE
        assert rev["baseline_report_sha256"] == data["baseline"]["report_sha256"]
        # severity first: the shortcoming (OBS-1) before the two minor ones; among the
        # minor ones the heavier criterion (plan, 30%) before outputs (20%)
        assert [e["observation_id"] for e in rev["open"]] == ["OBS-1", "OBS-2", "OBS-4"]
        assert [e["priority"] for e in rev["open"]] == [1, 2, 3]
        assert rev["open"][2]["needs_private_network"] is True
        assert rev["open"][0]["proposed_revision"] == "Give objective two a target."
        assert rev["closed"] == []
        assert "OBS-3" not in {e["observation_id"] for e in rev["open"]}

    def test_an_open_shortcoming_without_a_revision_is_flagged(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-2").pop("proposed_revision"))
        code, out = _compare(inputs)
        assert code == 1
        data = ec.load_comparison(next(out.glob("comparison_*.json")))
        assert data["flags"] == ["open shortcoming(s) without a proposed revision: OBS-2"]
        assert "FLAG:" in capsys.readouterr().out

    def test_a_baseline_without_an_intake_is_flagged_not_silently_accepted(self, world, bundle):
        code, report = _assess(world, bundle, RecordingBackend())
        assert code == 0
        baseline = world / "baseline"
        assert _freeze(world, bundle, report, baseline) == 0
        frozen = bb.load_frozen_baseline(baseline)
        esr_path = _write_json(world / "docs" / "esr" / "esr.json", _esr())
        esr = ec.load_esr_record(esr_path)
        disp = _write_json(world / "docs" / "esr" / "d.json", _rows(frozen.record["report_sha256"], esr.sha256))
        reg = _write_json(world / "docs" / "register.json", _register())
        inputs = {"world": world, "bundle": bundle, "baseline": baseline, "frozen": frozen,
                  "esr": esr_path, "dispositions": disp, "register": reg, "candidate": _candidate_dir(world)}
        code, out = _compare(inputs)
        assert code == 1
        data = ec.load_comparison(next(out.glob("comparison_*.json")))
        assert any("carries no intake id" in f for f in data["flags"])

    def test_reports_are_never_overwritten(self, inputs):
        _compare(inputs)
        _compare(inputs)
        out = inputs["world"] / "comparisons"
        names = sorted(p.name for p in out.iterdir())
        short = inputs["frozen"].record["report_sha256"][:12]
        assert names == [
            f"comparison_{short}_0001.json", f"comparison_{short}_0002.json",
            f"revisions_{short}_0001.json", f"revisions_{short}_0002.json",
        ]

    def test_render_names_the_bindings_and_the_counts(self, inputs, capsys):
        _compare(inputs)
        printed = capsys.readouterr().out
        assert "ESR COMPARISON" in printed
        assert "not assessable never counted" in printed
        assert "no deduction is attributed" in printed
        assert TRANSPORT in printed


# --------------------------------------------------------------------------- #
# The committed MSCA-DN artifacts resolve against the committed baseline
# --------------------------------------------------------------------------- #


@pytest.mark.skipif(not DN_BASELINE.is_dir() or not DN_ESR.is_file(), reason="MSCA-DN artifacts absent")
class TestCommittedMscaDn:
    def _run(self, tmp_path: Path) -> tuple[int, dict, dict, bb.FrozenBaseline]:
        frozen = bb.load_frozen_baseline(DN_BASELINE)
        current = DN_CANDIDATES / "MSCA-DN-2025_sanitised_part_b@b51a103520b58ded"
        historical = DN_CANDIDATES / "MSCA-DN-2025_sanitised_part_b@bdb8670f6987e4db"
        out = tmp_path / "comparisons"
        argv = [
            "compare", "--baseline-dir", str(DN_BASELINE), "--esr", str(DN_ESR),
            "--dispositions", str(DN_DISPOSITIONS), "--candidate", str(current),
            "--historical-candidate", str(historical), "--register", str(DN_REGISTER),
            "--repo-root", str(REPO), "--profile", str(DN_PROFILE), "--out-dir", str(out),
        ]
        for a in DN_AUDITS:
            argv += ["--audit", a]
        code = cmd.main(argv, clock=lambda: FROZEN)
        data = ec.load_comparison(next(out.glob("comparison_*.json")))
        rev = json.loads(next(out.glob("revisions_*.json")).read_text(encoding="utf-8"))
        return code, data, rev, frozen

    def test_every_historical_observation_has_a_traceable_disposition(self, tmp_path):
        code, data, _rev, frozen = self._run(tmp_path)
        assert code == 0, data["flags"]
        esr = ec.load_esr_record(DN_ESR)
        assert {r["observation_id"] for r in data["rows"]} == {o["id"] for o in esr.observations}
        assert data["baseline"]["report_sha256"] == frozen.record["report_sha256"]
        for row in data["rows"]:
            assert row["disposition"] in ec.DISPOSITIONS
            assert row["explanation"]
            assert row["disposition_status"] in ec.DECLARED_STATUSES
            if row["disposition"] == "independently_detected":
                assert row["blind_findings"] or row["audit_findings"]
            if row["disposition"] == "not_detected_despite_sufficient_preserved_evidence":
                assert row["current_proposal_evidence"] and not row["blind_findings"]
            if row["disposition"] == "not_assessable_from_this_copy":
                assert row["evidence_basis"]

    def test_the_esr_record_is_the_historical_result(self, tmp_path):
        _code, data, _rev, _frozen = self._run(tmp_path)
        sc = data["score_comparison"]
        assert sc["total"]["historical"] == 85.8
        by_id = {c["criterion_id"]: c["historical_score"] for c in sc["criteria"]}
        assert by_id == {"excellence": 4.2, "impact": 4.5, "implementation": 4.2}
        assert sc["no_deduction_attributed_to_individual_criticism"] is True

    def test_the_comparison_states_how_much_was_assessable(self, tmp_path):
        _code, data, rev, _frozen = self._run(tmp_path)
        s = data["summary"]
        assert s["assessable_fraction"] is not None
        assert s["assessable"] + s["not_assessable"] == s["observations"]
        assert s["not_assessable_counted_as_failure"] is False
        assert all(e["proposed_revision"] for e in rev["open"])
