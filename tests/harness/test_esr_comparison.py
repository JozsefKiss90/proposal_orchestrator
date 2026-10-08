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


# --------------------------------------------------------------------------- #
# What "sufficient preserved evidence" is actually checked against (ticket R05)
# --------------------------------------------------------------------------- #


def _rewrite_register(inputs, mutate) -> None:
    """Edit the fidelity register in place through *mutate(data)*."""
    path = inputs["register"]
    data = json.loads(path.read_text(encoding="utf-8"))
    mutate(data)
    _write_json(path, data)


class TestPreservationIsMeasuredNotAsserted:
    """A miss asserts the copy preserved what the evaluators read. The quote is
    measured against the candidate; the sufficiency of that evidence is a
    declaration, and a 'Confirmed' one needs the register's declared half."""

    def test_a_confirmed_preservation_status_needs_the_declared_half(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-2").update(evidence_preserved_status="Confirmed"))
        code, _ = _compare(inputs)
        assert code == 2
        err = capsys.readouterr().err
        assert "'evidence_preserved_status' is 'Confirmed'" in err
        assert "declared half" in err and "S2" in err

    def test_a_presence_only_entry_no_longer_carries_confirmed(self, inputs, capsys):
        """Before validation correction V01 this entry was enough. A presence
        is an extraction claim about this PDF; the submission is another step.
        The accepting case now lives in
        TestConfirmedPreservationNeedsTheOriginalFidelityClaim."""
        _rewrite(inputs, lambda d: _row(d, "OBS-2").update(
            evidence_preserved_status="Confirmed", evidence_basis=["declared/sub_sections/S2"]
        ))
        _rewrite_register(inputs, lambda d: d["declared"]["sub_sections"].append(
            {"sub_section_id": "S2", "presence": {"value": "present in the submission"},
             "transformation": {"value": "unchanged"}}
        ))
        code, _ = _compare(inputs)
        assert code == 2
        assert "does not unlock 'Confirmed' preservation" in capsys.readouterr().err

    def test_a_declared_entry_without_a_presence_value_does_not_carry_confirmed(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-2").update(evidence_preserved_status="Confirmed"))
        _rewrite_register(inputs, lambda d: d["declared"]["sub_sections"].append(
            {"sub_section_id": "S2", "transformation": {"value": "unchanged"}}
        ))
        code, _ = _compare(inputs)
        assert code == 2
        assert "declares no 'presence'" in capsys.readouterr().err

    def test_assumed_preservation_stands_on_its_own(self, inputs):
        """Today's declared halves are empty. 'Assumed' says so and is accepted."""
        code, out = _compare(inputs)
        assert code == 0
        row = _row(ec.load_comparison(next(out.glob("comparison_*.json"))), "OBS-2")
        assert row["evidence_preserved_status"] == "Assumed"


class TestDispositionsSchemaVersion:
    def test_an_unknown_schema_version_is_refused(self, inputs, capsys):
        _rewrite(inputs, lambda d: d.update(schema_version="2.0"))
        code, _ = _compare(inputs)
        assert code == 2
        assert "schema_version '2.0'" in capsys.readouterr().err

    def test_version_1_1_makes_a_miss_name_its_register_basis(self, inputs, capsys):
        _rewrite(inputs, lambda d: d.update(schema_version="1.1"))
        code, _ = _compare(inputs)
        assert code == 2
        err = capsys.readouterr().err
        assert "needs a fidelity-register entry" in err and "OBS-2" in err

    def test_version_1_0_leaves_that_row_as_it_was(self, inputs):
        """The committed PE-08 dispositions are 1.0 and must still compare."""
        code, _ = _compare(inputs)
        assert code == 0

    def test_version_1_1_accepts_the_miss_once_the_basis_is_named(self, inputs):
        def mutate(d):
            d["schema_version"] = "1.1"
            _row(d, "OBS-2")["evidence_basis"] = ["provenance/transformation/citations"]
        _rewrite(inputs, mutate)
        code, out = _compare(inputs)
        assert code == 0
        row = _row(ec.load_comparison(next(out.glob("comparison_*.json"))), "OBS-2")
        assert row["evidence_basis"][0]["pointer"] == "provenance/transformation/citations"


class TestRevisionPlan:
    """Ticket R05 item 6: a revision names its evidence, the human who owns it,
    what has to be confirmed, where it goes, and whether it is a commitment."""

    PLAN = {
        "evidence": ["the quoted passage in S2"],
        "responsible_role": {"role": "Project Coordinator", "source": "S2 of the candidate"},
        "requires_confirmation": ["that month four is feasible for task three"],
        "proposal_location": ["S2"],
        "commitment_kind": "requires_study_design",
    }

    def _plan(self, **over) -> dict:
        return {**copy.deepcopy(self.PLAN), **over}

    def test_a_plan_is_carried_into_both_artifacts(self, inputs):
        _rewrite(inputs, lambda d: _row(d, "OBS-2")["proposed_revision"].update(
            revision_plan=self._plan()))
        code, out = _compare(inputs)
        assert code == 0
        row = _row(ec.load_comparison(next(out.glob("comparison_*.json"))), "OBS-2")
        assert row["proposed_revision"]["revision_plan"]["commitment_kind"] == (
            "requires_study_design")
        rev = json.loads(next(out.glob("revisions_*.json")).read_text(encoding="utf-8"))
        entry = next(e for e in rev["open"] if e["observation_id"] == "OBS-2")
        assert entry["revision_plan"]["responsible_role"]["role"] == "Project Coordinator"

    def test_a_row_without_a_plan_carries_no_plan_key(self, inputs):
        """The 1.0 revisions artifact keeps its exact shape."""
        code, out = _compare(inputs)
        assert code == 0
        rev = json.loads(next(out.glob("revisions_*.json")).read_text(encoding="utf-8"))
        assert all("revision_plan" not in e for e in rev["open"])

    def test_a_plan_missing_a_field_is_refused(self, inputs, capsys):
        plan = self._plan()
        plan.pop("proposal_location")
        _rewrite(inputs, lambda d: _row(d, "OBS-2")["proposed_revision"].update(revision_plan=plan))
        code, _ = _compare(inputs)
        assert code == 2
        assert "revision_plan lacks 'proposal_location'" in capsys.readouterr().err

    def test_an_unknown_commitment_kind_is_refused(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-2")["proposed_revision"].update(
            revision_plan=self._plan(commitment_kind="nice_to_have")))
        code, _ = _compare(inputs)
        assert code == 2
        assert "commitment_kind 'nice_to_have'" in capsys.readouterr().err

    def test_a_commitment_must_name_what_has_to_be_confirmed(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-2")["proposed_revision"].update(
            revision_plan=self._plan(requires_confirmation=[])))
        code, _ = _compare(inputs)
        assert code == 2
        assert "names nothing to confirm" in capsys.readouterr().err

    def test_an_editorial_change_need_not(self, inputs):
        _rewrite(inputs, lambda d: _row(d, "OBS-2")["proposed_revision"].update(
            revision_plan=self._plan(commitment_kind="editorial_change", requires_confirmation=[])))
        code, _ = _compare(inputs)
        assert code == 0

    def test_a_role_without_a_source_is_refused(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-2")["proposed_revision"].update(
            revision_plan=self._plan(responsible_role={"role": "the Coordinator"})))
        code, _ = _compare(inputs)
        assert code == 2
        assert "responsible_role needs a 'role' and the 'source'" in capsys.readouterr().err


# --------------------------------------------------------------------------- #
# Whose declarations these are, and which of them are unresolved (ticket R05)
# --------------------------------------------------------------------------- #


class TestReviewState:
    def test_a_record_that_declares_none_is_read_as_before(self, inputs):
        """The PE-08 record declares no review state and must keep its shape."""
        code, out = _compare(inputs)
        assert code == 0
        data = ec.load_comparison(next(out.glob("comparison_*.json")))
        assert "review_state" not in data
        assert "review_state" not in data["dispositions"]
        assert all("review_status" not in r for r in data["rows"])

    def test_an_unknown_record_review_state_is_refused(self, inputs, capsys):
        _rewrite(inputs, lambda d: d.update(review_state="approved"))
        code, _ = _compare(inputs)
        assert code == 2
        assert "review_state 'approved'" in capsys.readouterr().err

    def test_a_declared_state_is_carried_and_qualifies_the_general_note(self, inputs):
        _rewrite(inputs, lambda d: d.update(review_state=ec.REVIEW_STATE_AGENT_DRAFTED))
        code, out = _compare(inputs)
        assert code == 0
        data = ec.load_comparison(next(out.glob("comparison_*.json")))
        assert data["dispositions"]["review_state"] == ec.REVIEW_STATE_AGENT_DRAFTED
        state = data["review_state"]
        assert state["state"] == ec.REVIEW_STATE_AGENT_DRAFTED
        assert "nothing here records an operator decision" in state["statement"]
        assert "this field governs" in state["statement"]
        assert ec.REVIEW_STATE_AGENT_DRAFTED in ec.render_comparison(data)

    def test_an_unknown_row_review_status_is_refused(self, inputs, capsys):
        _rewrite(inputs, lambda d: _row(d, "OBS-1").update(review_status="fine"))
        code, _ = _compare(inputs)
        assert code == 2
        assert "review_status 'fine'" in capsys.readouterr().err

    def test_a_row_status_is_carried_and_the_questions_are_listed(self, inputs):
        def mutate(d):
            d["review_state"] = ec.REVIEW_STATE_AGENT_DRAFTED
            _row(d, "OBS-1")["review_status"] = "operator_decision_required"
            _row(d, "OBS-2")["review_status"] = "agent_recommended_pending_operator_review"
        _rewrite(inputs, mutate)
        code, out = _compare(inputs)
        assert code == 0
        data = ec.load_comparison(next(out.glob("comparison_*.json")))
        assert _row(data, "OBS-1")["review_status"] == "operator_decision_required"
        assert data["review_state"]["rows_needing_an_operator_decision"] == ["OBS-1"]


class TestUnresolvedDeclarations:
    def test_no_unresolved_row_means_no_block(self, inputs):
        code, out = _compare(inputs)
        assert code == 0
        summary = ec.load_comparison(next(out.glob("comparison_*.json")))["summary"]
        assert "declarations_unresolved" not in summary

    def test_an_unresolved_row_is_counted_and_named(self, inputs, capsys):
        """A count must count something; the summary says which rows are provisional."""
        _rewrite(inputs, lambda d: _row(d, "OBS-1").update(declared_status="Unresolved"))
        code, out = _compare(inputs)
        assert code == 0
        data = ec.load_comparison(next(out.glob("comparison_*.json")))
        block = data["summary"]["declarations_unresolved"]
        assert block["rows"] == ["OBS-1"]
        assert "§12.2" in block["statement"]
        # still counted under the disposition it declares
        assert data["summary"]["by_disposition"]["independently_detected"] == 2
        assert "provisional: 1 row(s)" in ec.render_comparison(data)


# --------------------------------------------------------------------------- #
# V02 — a register pointer into a keyed list names an identity, not a position
# --------------------------------------------------------------------------- #


def _keyed_register() -> dict:
    """A derived half whose sub-section ids are digits that are not their positions."""
    return {
        "derived": {
            "sub_sections": [
                {"sub_section_id": "1.1", "characters": 10},
                {"sub_section_id": "1.2", "characters": 20},
                {"sub_section_id": "4", "characters": 40},
                {"sub_section_id": "5", "characters": 50},
                {"sub_section_id": "6", "characters": 60},
                {"sub_section_id": "7", "characters": 70},
                {"sub_section_id": "8", "characters": 80},
            ],
            "plain": [100, 200, 300],
        }
    }


class TestPointerResolution:
    @pytest.mark.parametrize("sub", ["4", "5", "6", "7", "8"])
    def test_a_digit_segment_resolves_by_identity(self, sub):
        value = ec.resolve_pointer(_keyed_register(), f"derived/sub_sections/{sub}/characters")
        assert value == int(sub) * 10

    def test_a_dotted_id_resolves_by_identity(self):
        assert ec.resolve_pointer(_keyed_register(), "derived/sub_sections/1.2/characters") == 20

    def test_identity_survives_a_reordered_list(self):
        data = _keyed_register()
        data["derived"]["sub_sections"].reverse()
        assert ec.resolve_pointer(data, "derived/sub_sections/8/characters") == 80
        assert ec.resolve_pointer(data, "derived/sub_sections/1.1/characters") == 10

    def test_a_missing_id_is_refused_not_read_positionally(self):
        data = _keyed_register()
        with pytest.raises(ec.EsrComparisonError, match="no element '3'"):
            ec.resolve_pointer(data, "derived/sub_sections/3/characters")

    def test_an_explicit_position_is_typed(self):
        assert ec.resolve_pointer(_keyed_register(), "derived/sub_sections/#2/characters") == 40
        assert ec.resolve_pointer(_keyed_register(), "derived/sub_sections/#6/characters") == 80

    def test_an_explicit_position_past_the_end_is_refused(self):
        with pytest.raises(ec.EsrComparisonError, match="#9"):
            ec.resolve_pointer(_keyed_register(), "derived/sub_sections/#9")

    def test_a_plain_list_is_still_indexed_by_a_bare_digit(self):
        assert ec.resolve_pointer(_keyed_register(), "derived/plain/1") == 200
        assert ec.resolve_pointer(_keyed_register(), "derived/plain/#2") == 300

    def test_the_legacy_rule_reads_a_bare_digit_positionally_first(self):
        """Dispositions schema 1.0 and 1.1 recorded pointers under the old rule,
        and their comparisons replay only under it. The rule is named, opt-in,
        and never the default."""
        data = _keyed_register()
        # position 4 is sub-section "6", position 5 is sub-section "7"
        assert ec.resolve_pointer(data, "derived/sub_sections/4/characters", legacy_positional=True) == 60
        assert ec.resolve_pointer(data, "derived/sub_sections/5/characters", legacy_positional=True) == 70
        assert ec.resolve_pointer(data, "derived/sub_sections/1.2/characters", legacy_positional=True) == 20

    def test_the_legacy_rule_falls_back_to_identity_past_the_end(self):
        data = _keyed_register()
        del data["derived"]["sub_sections"][1:]
        data["derived"]["sub_sections"].append({"sub_section_id": "8", "characters": 80})
        assert ec.resolve_pointer(data, "derived/sub_sections/8/characters", legacy_positional=True) == 80

    def test_the_comparison_records_which_rule_resolved_its_pointers(self, inputs):
        """A 1.2 record resolves by identity and says so; an older record is
        resolved under the legacy rule and its artifact keeps its old shape."""
        _rewrite_register(inputs, lambda d: d["derived"]["sub_sections"].append(
            {"sub_section_id": "4", "characters": 44}
        ))

        def to_1_2(d):
            d["schema_version"] = "1.2"
            _row(d, "OBS-2")["evidence_basis"] = ["derived/sub_sections/4/characters"]
            _row(d, "OBS-2")["failure_mode"] = "absent_from_recorded_output"
            _row(d, "OBS-2")["failure_mode_basis"] = "no sample names the start month"
        _rewrite(inputs, to_1_2)
        code, out = _compare(inputs)
        assert code == 0
        data = ec.load_comparison(next(out.glob("comparison_*.json")))
        assert data["fidelity_register"]["pointer_resolution"] == ec.POINTER_RESOLUTION_IDENTITY
        row = _row(data, "OBS-2")
        assert row["evidence_basis"][0]["value"] == 44

    def test_a_1_0_record_keeps_the_legacy_rule_and_its_artifact_shape(self, inputs):
        _rewrite_register(inputs, lambda d: d["derived"]["sub_sections"].append(
            {"sub_section_id": "1", "characters": 11}
        ))
        _rewrite(inputs, lambda d: _row(d, "OBS-4").update(
            evidence_basis=["derived/sub_sections/1/characters"]
        ))
        code, out = _compare(inputs)
        assert code == 0
        data = ec.load_comparison(next(out.glob("comparison_*.json")))
        assert "pointer_resolution" not in data["fidelity_register"]
        # position 1 is S3 (60 characters), not the sub-section whose id is "1"
        assert _row(data, "OBS-4")["evidence_basis"][0]["value"] == 60

    def test_a_reader_of_a_written_comparison_reads_the_rule_back(self):
        """One reader of the recorded field, so one polarity: a comparison that
        does not say 'identity' was written under the legacy rule."""
        identity = {"fidelity_register": {"pointer_resolution": ec.POINTER_RESOLUTION_IDENTITY}}
        assert ec.pointer_rule_of(identity) == ec.POINTER_RESOLUTION_IDENTITY
        for older in ({"fidelity_register": {}}, {}, {"fidelity_register": None}):
            assert ec.pointer_rule_of(older) == ec.POINTER_RESOLUTION_LEGACY


# --------------------------------------------------------------------------- #
# V01 — Confirmed preservation needs the original-fidelity claim, not presence
# --------------------------------------------------------------------------- #


def _supported_entry(sub: str, observation_id: str = "OBS-2") -> dict:
    """A declared-half row that carries a Confirmed original-fidelity claim for *sub*."""
    return {
        "sub_section_id": sub,
        "presence": {
            "value": "present in this revision's extraction",
            "claim_scope": "extraction_fidelity_against_the_sanitised_pdf",
            "declared_status": "Confirmed",
        },
        "transformation": {"value": "unchanged", "declared_status": "Assumed"},
        "fidelity_to_submitted_original": {
            "value": "the passage the ESR rested on is carried unchanged",
            "claim_scope": "fidelity_against_the_submitted_original",
            "declared_status": "Confirmed",
            "basis": "operator reading of S2 against the submitted original, 2026-10-20",
            "evidence": [
                {
                    "observation_ids": [observation_id],
                    "source": "the submitted original, S2, paragraph 3, read inside the private network",
                    "statement": "the start-month sentence is the submission's own, word for word",
                }
            ],
        },
    }


def _confirm_obs_2(inputs, *, entry: dict | None, basis: list[str] | None = None) -> None:
    def mutate(d):
        row = _row(d, "OBS-2")
        row["evidence_preserved_status"] = "Confirmed"
        if basis is not None:
            row["evidence_basis"] = basis
    _rewrite(inputs, mutate)
    if entry is not None:
        _rewrite_register(inputs, lambda d: d["declared"]["sub_sections"].append(entry))


class TestConfirmedPreservationNeedsTheOriginalFidelityClaim:
    """An extraction-only presence declaration says the PDF was read. It says
    nothing about the submission, so it must not unlock Confirmed preservation."""

    BASIS = ["declared/sub_sections/S2/fidelity_to_submitted_original"]

    def test_extraction_only_presence_is_refused(self, inputs, capsys):
        entry = _supported_entry("S2")
        del entry["fidelity_to_submitted_original"]
        _confirm_obs_2(inputs, entry=entry, basis=["declared/sub_sections/S2"])
        code, _ = _compare(inputs)
        assert code == 2
        err = capsys.readouterr().err
        assert "fidelity_to_submitted_original" in err and "S2" in err

    def test_an_unresolved_original_fidelity_is_refused(self, inputs, capsys):
        entry = _supported_entry("S2")
        entry["fidelity_to_submitted_original"]["declared_status"] = "Unresolved"
        _confirm_obs_2(inputs, entry=entry, basis=self.BASIS)
        code, _ = _compare(inputs)
        assert code == 2
        assert "'Unresolved'" in capsys.readouterr().err

    def test_a_claim_in_another_scope_is_refused(self, inputs, capsys):
        entry = _supported_entry("S2")
        entry["fidelity_to_submitted_original"]["claim_scope"] = "extraction_fidelity_against_the_sanitised_pdf"
        _confirm_obs_2(inputs, entry=entry, basis=self.BASIS)
        code, _ = _compare(inputs)
        assert code == 2
        assert "claim_scope" in capsys.readouterr().err

    def test_a_missing_basis_is_refused(self, inputs, capsys):
        entry = _supported_entry("S2")
        entry["fidelity_to_submitted_original"]["basis"] = ""
        _confirm_obs_2(inputs, entry=entry, basis=self.BASIS)
        code, _ = _compare(inputs)
        assert code == 2
        assert "basis" in capsys.readouterr().err

    def test_a_generic_basis_with_no_evidence_for_this_row_is_refused(self, inputs, capsys):
        entry = _supported_entry("S2", observation_id="OBS-9")
        _confirm_obs_2(inputs, entry=entry, basis=self.BASIS)
        code, _ = _compare(inputs)
        assert code == 2
        err = capsys.readouterr().err
        assert "OBS-2" in err and "evidence" in err

    def test_a_declaration_for_another_sub_section_is_refused(self, inputs, capsys):
        _confirm_obs_2(inputs, entry=_supported_entry("S1"), basis=["declared/sub_sections/S1"])
        code, _ = _compare(inputs)
        assert code == 2
        err = capsys.readouterr().err
        assert "no entry for sub-section S2" in err

    def test_the_row_must_name_the_declaration_it_rests_on(self, inputs, capsys):
        _confirm_obs_2(inputs, entry=_supported_entry("S2"), basis=["provenance/transformation/citations"])
        code, _ = _compare(inputs)
        assert code == 2
        assert "evidence_basis" in capsys.readouterr().err

    def test_a_supported_declaration_is_accepted(self, inputs):
        _confirm_obs_2(inputs, entry=_supported_entry("S2"), basis=self.BASIS)
        code, out = _compare(inputs)
        assert code == 0
        row = _row(ec.load_comparison(next(out.glob("comparison_*.json"))), "OBS-2")
        assert row["evidence_preserved_status"] == "Confirmed"
        assert row["evidence_basis"][0]["value"]["declared_status"] == "Confirmed"

    def test_the_rule_applies_to_every_schema_version(self, inputs, capsys):
        """No committed 1.0 or 1.1 row declares Confirmed, so the stricter rule
        changes nothing they replay; it is not version-gated."""
        entry = _supported_entry("S2")
        del entry["fidelity_to_submitted_original"]
        _confirm_obs_2(inputs, entry=entry, basis=["declared/sub_sections/S2"])
        code, _ = _compare(inputs)
        assert code == 2
        _rewrite(inputs, lambda d: d.update(schema_version="1.1"))
        code, _ = _compare(inputs)
        assert code == 2

    def test_no_committed_record_declares_confirmed_preservation(self):
        """The historical replay of the 1.0 and 1.1 records does not exercise the
        rule, and the records say so."""
        for name in ("dispositions_f60ae6e0a2a1.json", "dispositions_f60ae6e0a2a1_r05.json"):
            path = DN_DISPOSITIONS.parent / name
            if not path.is_file():
                continue
            rows = json.loads(path.read_text(encoding="utf-8-sig"))["rows"]
            assert not [r for r in rows if r.get("evidence_preserved_status") == "Confirmed"], name
