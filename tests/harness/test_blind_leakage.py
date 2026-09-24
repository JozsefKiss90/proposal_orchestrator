"""
ESR intake and the leakage guard on the blind assessment lane.

The blind command builds its evidence through the dev-graph package builder
under the blind pre-evaluation view policy and asserts, before any assessor
call, that nothing tagged as historical feedback is in the package. The
world is the synthetic dev-graph fixture with its candidate and a planted
ESR-shaped document; the profile is a call-neutral three-criterion profile
mapped onto the candidate's three sections. Everything runs offline.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

import harness.blind_assessment as ba
import harness.commands.blind_assessment as cmd
from harness.judge import Judge, JudgeConfig
from harness.provenance import ProvenanceLog
from harness.rubrics import load_profile_bundle
from runner.dev_graph import (
    PERMITTED_PURPOSES,
    POLICY_VERSION,
    build_snapshot,
    import_document,
    record_esr_intake,
)
from runner.dev_graph.policies import HISTORICAL_FEEDBACK_TAGS
from runner.paths import find_repo_root

FIXTURE = find_repo_root() / "tests" / "fixtures" / "dev_graph_synthetic"
CANDIDATE = Path("docs/tier5_deliverables/candidates/synthetic_candidate.json")
ESR_DOC = Path("docs/tier5_deliverables/candidates/synthetic_esr.json")
FROZEN = "2026-09-24T12:00:00+00:00"
PASS_JSON = '{"passed": true, "score": 0.9, "rationale": "scripted pass"}'


def _write_json(path: Path, data) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _graph_profile(root: Path) -> Path:
    """A call-neutral profile whose three criteria map onto the fixture
    candidate's sections S1, S2 and S3."""
    criteria = [
        ("aims", "Aims", "S1", "aims-objectives", "Clarity of the objectives", ["objective"]),
        ("plan", "Plan", "S2", "plan-tasks", "Credibility of the task plan", ["task"]),
        ("outputs", "Outputs", "S3", "outputs-deliverables", "Definition of the deliverables", ["deliverable"]),
    ]
    registry = {
        "instruments": [
            {
                "instrument_type": "SYN-GRAPH",
                "criteria": [
                    {"criterion_id": rid, "evaluator_expectations": [text]}
                    for _c, rid, _s, _k, text, _t in criteria
                ],
            }
        ]
    }
    scorecard = {
        "scorecard_id": "syn_graph_scorecard",
        "provenance": {"version": "0.1"},
        "scoring": {"scale": "0-5", "levels": {"0": "none", "5": "full"}, "overall_threshold": 10, "overall_max": 15},
        "criteria": [
            {
                "id": cid,
                "name": rid,
                "weight_pct": 34 if cid == "aims" else 33,
                "aspects": [{"id": key, "text": text, "option_tag": "Track one", "source_page": 1}],
            }
            for cid, rid, _s, key, text, _t in criteria
        ],
        "excluded_aspects": [],
    }
    rubrics = {
        "rubric_set_id": "syn_graph_rubrics",
        "version": "0.1.0",
        "scorecard_id": "syn_graph_scorecard",
        "scorecard_version": "0.1",
        "rubrics": [
            {
                "expectation_key": key,
                "criterion_id": cid,
                "expectation_text": text,
                "rubric": "Integrity-framed: addressed AND grounded.",
                "evaluation_steps": ["Check the spans.", "Check the claims."],
                "pass_threshold": 0.7,
                "selection_terms": terms,
                "anchor_sub_section_ids": [sid],
            }
            for cid, _rid, sid, key, text, terms in criteria
        ],
    }
    profile = {
        "profile_id": "syn_graph",
        "label": "Synthetic graph-mapped profile",
        "instrument": {
            "registry_instrument_type": "SYN-GRAPH",
            "name": "Synthetic Graph Track",
            "form_name": "Synthetic Graph Assessment Form",
        },
        "option_tag_grammar": {
            "applicable_variant": "Track one",
            "known_variants": ["Track one", "Track two"],
            "variant_prefix": "",
            "all_except_prefix": "all tracks except ",
        },
        "criteria": [
            {"id": cid, "registry_criterion_id": rid, "section_ids": [sid]}
            for cid, rid, sid, _k, _t, _terms in criteria
        ],
        "registry_path": "syn/registry.json",
        "scorecard": {"path": "syn/scorecard.json", "scorecard_id": "syn_graph_scorecard", "version": "0.1"},
        "rubric_set": {"path": "syn/rubrics.json", "rubric_set_id": "syn_graph_rubrics", "version": "0.1.0"},
    }
    _write_json(root / "syn/registry.json", registry)
    _write_json(root / "syn/scorecard.json", scorecard)
    _write_json(root / "syn/rubrics.json", rubrics)
    return _write_json(root / "syn/profile.json", profile)


class RecordingBackend:
    """Scripted pass; keeps every prompt it was shown and counts calls."""

    def __init__(self):
        self.calls = 0
        self.prompts: list[str] = []

    def __call__(self, messages):
        self.calls += 1
        self.prompts.extend(str(m.get("content", "")) for m in messages)
        return {"content": PASS_JSON}


@pytest.fixture
def world(tmp_path: Path) -> Path:
    """The fixture with the candidate imported and the ESR planted as a
    submitted historical document."""
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    import_document(root, CANDIDATE)
    import_document(root, ESR_DOC, state="submitted")
    return root


@pytest.fixture
def bundle(world: Path):
    return load_profile_bundle(_graph_profile(world), repo_root=world)


def _judge(tmp_path: Path, backend) -> Judge:
    return Judge(
        JudgeConfig(model="fake-assessor", version="pin-7"),
        backend=backend,
        provenance_log=ProvenanceLog(tmp_path / "provenance.jsonl"),
        clock=lambda: FROZEN,
    )


def _run(world: Path, bundle, backend, *extra: str, out: Path | None = None) -> tuple[int, Path]:
    out = out or (world / "reports")
    code = cmd.main(
        ["assess", "--document", "CAND-1", "--graph-root", str(world), "--out-dir", str(out),
         "--repo-root", str(world), "--profile", str(bundle.profile.source_path), *extra],
        judge=_judge(world, backend),
        clock=lambda: FROZEN,
    )
    return code, out


# --------------------------------------------------------------------------- #
# The document route: evidence through the package builder, blind view
# --------------------------------------------------------------------------- #


class TestDocumentRoute:
    def test_report_carries_snapshot_package_policy_and_blind_label(self, world, bundle):
        backend = RecordingBackend()
        code, out = _run(world, bundle, backend)
        assert code == 0
        (path,) = [p for p in out.iterdir() if p.is_file()]
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["task_label"] == ba.BLIND_TASK_LABEL
        assert data["esr_availability"] == "unknown"
        assert data["intake_id"] == ""
        assert data["snapshot_id"] == build_snapshot(world).snapshot_id
        assert data["policy_version"] == POLICY_VERSION
        assert data["package_id"].startswith("sha256:")
        assert data["evidence_view"] == "blind_pre_evaluation"
        assert data["scope"] == "complete"
        assert {c["section_id"] for c in data["cells"]} == {"S1", "S2", "S3"}
        assert backend.calls == 3 * 3

    def test_rendered_package_prompts_and_report_hold_no_esr_text(self, world, bundle):
        backend = RecordingBackend()
        evidence = ba.build_blind_evidence(
            world, "CAND-1", profile_version=bundle.version, out_dir=world / "reports"
        )
        rendered = json.dumps(evidence.package.to_dict())
        assert "ESR" not in rendered
        for tag in HISTORICAL_FEEDBACK_TAGS:
            assert tag not in rendered
        esr_path = next(
            e["path"] for e in evidence.package.manifest["exclusions"]
            if e["reason"] == "policy_forbidden" and e["id"].startswith("ESR-1@")
        )
        assert esr_path.startswith("docs/tier4_orchestration_state/dev_graph/documents/ESR-1/")
        code, out = _run(world, bundle, backend)
        assert code == 0
        assert backend.prompts and all("ESR" not in p for p in backend.prompts)
        (path,) = [p for p in out.iterdir() if p.is_file()]
        assert "ESR" not in path.read_text(encoding="utf-8")
        # The materialised candidate the cells were graded over is ESR-free too.
        for section in evidence.candidate_dir.glob("*.json"):
            assert "ESR" not in section.read_text(encoding="utf-8")

    def test_materialised_candidate_is_deterministic_and_verifiable(self, world, bundle):
        a = ba.build_blind_evidence(world, "CAND-1", profile_version=bundle.version, out_dir=world / "r")
        b = ba.build_blind_evidence(world, "CAND-1", profile_version=bundle.version, out_dir=world / "r")
        assert a.package.package_id == b.package.package_id
        assert a.candidate_dir == b.candidate_dir
        assert {p.name: p.read_bytes() for p in a.candidate_dir.iterdir()} == {
            p.name: p.read_bytes() for p in b.candidate_dir.iterdir()
        }
        code, out = _run(world, bundle, RecordingBackend(), out=world / "r")
        assert code == 0
        (path,) = [p for p in out.iterdir() if p.is_file()]
        assert cmd.main(
            ["verify", "--report", str(path), "--candidate", str(a.candidate_dir),
             "--repo-root", str(world), "--profile", str(bundle.profile.source_path)]
        ) == 0

    def test_unknown_document_is_refused(self, world, bundle):
        with pytest.raises(ba.BlindAssessmentError, match="NOPE"):
            ba.build_blind_evidence(world, "NOPE", profile_version=bundle.version, out_dir=world / "r")

    def test_a_submitted_document_is_not_a_current_candidate(self, world, bundle):
        with pytest.raises(ba.BlindAssessmentError, match="ESR-1"):
            ba.build_blind_evidence(world, "ESR-1", profile_version=bundle.version, out_dir=world / "r")


# --------------------------------------------------------------------------- #
# The leakage guard: hard failure before any assessor call
# --------------------------------------------------------------------------- #


def _forced(package, *, tags=("historical_feedback",), ntype="passage"):
    item = {
        "id": "FORCED-1",
        "type": ntype,
        "version": "sha256:" + "f" * 64,
        "content": {"text": "historical score 2.5", "tags": list(tags)},
    }
    manifest = dict(package.manifest)
    manifest["included"] = list(manifest["included"]) + [
        {"id": "FORCED-1", "type": ntype, "version": item["version"], "reason": "expansion", "path": [], "depth": 1, "cost": 1}
    ]
    return type(package)(manifest=manifest, items=tuple(package.items) + (item,))


class TestLeakageGuard:
    @pytest.mark.parametrize("tag", sorted(HISTORICAL_FEEDBACK_TAGS))
    def test_each_forbidden_tag_is_a_hard_failure(self, world, bundle, monkeypatch, tag):
        real = ba.build_package
        monkeypatch.setattr(ba, "build_package", lambda *a, **k: _forced(real(*a, **k), tags=(tag,)))
        with pytest.raises(ba.LeakageError) as exc:
            ba.build_blind_evidence(world, "CAND-1", profile_version=bundle.version, out_dir=world / "r")
        assert "FORCED-1" in str(exc.value) and tag in str(exc.value)

    def test_a_forbidden_type_is_a_hard_failure(self, world, bundle, monkeypatch):
        real = ba.build_package
        monkeypatch.setattr(ba, "build_package", lambda *a, **k: _forced(real(*a, **k), tags=(), ntype="assessment"))
        with pytest.raises(ba.LeakageError, match="assessment"):
            ba.build_blind_evidence(world, "CAND-1", profile_version=bundle.version, out_dir=world / "r")

    def test_forced_item_fails_the_command_before_any_assessor_call(self, world, bundle, monkeypatch, capsys):
        real = ba.build_package
        monkeypatch.setattr(ba, "build_package", lambda *a, **k: _forced(real(*a, **k)))
        backend = RecordingBackend()
        code, out = _run(world, bundle, backend)
        assert code == 2
        assert backend.calls == 0
        assert not out.exists() or not [p for p in out.iterdir() if p.is_file()]
        assert "leak" in capsys.readouterr().err.lower()

    def test_a_package_under_another_view_is_refused(self, world, bundle):
        evidence = ba.build_blind_evidence(world, "CAND-1", profile_version=bundle.version, out_dir=world / "r")
        manifest = {**evidence.package.manifest, "view": "engineering"}
        with pytest.raises(ba.LeakageError, match="engineering"):
            ba.assert_no_leakage(type(evidence.package)(manifest=manifest, items=evidence.package.items))


# --------------------------------------------------------------------------- #
# ESR intake and the task label
# --------------------------------------------------------------------------- #


class TestIntakeAndLabel:
    def test_task_labels_are_the_intake_purposes(self):
        assert ba.TASK_LABELS == PERMITTED_PURPOSES
        assert ba.BLIND_TASK_LABEL != ba.ESR_INFORMED_TASK_LABEL

    def test_esr_informed_task_carries_its_own_label_and_is_never_blind(self):
        task = ba.ReviewTask(label=ba.ESR_INFORMED_TASK_LABEL, document="CAND-1")
        assert task.label == "esr_informed_review"
        assert task.is_blind is False
        assert ba.ReviewTask(label=ba.BLIND_TASK_LABEL, document="CAND-1").is_blind is True
        with pytest.raises(ValueError, match="label"):
            ba.ReviewTask(label="something_else", document="CAND-1")

    def test_report_cannot_carry_the_esr_informed_label(self, world, bundle):
        code, out = _run(world, bundle, RecordingBackend())
        assert code == 0
        (path,) = [p for p in out.iterdir() if p.is_file()]
        data = json.loads(path.read_text(encoding="utf-8"))
        evidence = ba.build_blind_evidence(world, "CAND-1", profile_version=bundle.version, out_dir=out)
        report = ba.assess_candidate(
            _judge(world, RecordingBackend()), bundle, evidence=evidence, clock=lambda: FROZEN
        )
        kwargs = {k: getattr(report, k) for k in report.__dataclass_fields__}
        with pytest.raises(ValueError, match="separately labelled"):
            ba.BlindAssessmentReport(**{**kwargs, "task_label": ba.ESR_INFORMED_TASK_LABEL})
        data["task_label"] = ba.ESR_INFORMED_TASK_LABEL
        tampered = _write_json(world / "tampered.json", data)
        with pytest.raises(ba.BlindAssessmentError, match="task_label"):
            ba.load_report(tampered, evidence.candidate_dir, bundle.profile)

    def test_intake_with_prior_submission_stamps_unknown(self, world, bundle):
        rec = record_esr_intake(
            world, intake_id="INTAKE-1", document_id="CAND-1", submission_id="SUB-1",
            call_id="SYN-CALL-01", permitted_purpose="blind_pre_evaluation", prior_submission=True,
        )
        assert rec.esr_availability == "unknown"
        code, out = _run(world, bundle, RecordingBackend(), "--intake", "INTAKE-1")
        assert code == 0
        (path,) = [p for p in out.iterdir() if p.is_file()]
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["esr_availability"] == "unknown"
        assert data["intake_id"] == "INTAKE-1"

    def test_intake_for_an_esr_informed_review_refuses_the_blind_lane(self, world, bundle, capsys):
        record_esr_intake(
            world, intake_id="INTAKE-2", document_id="CAND-1", submission_id="SUB-1",
            call_id="SYN-CALL-01", permitted_purpose="esr_informed_review", prior_submission=True,
            esr_availability="available", esr_reference="ESR-1",
        )
        backend = RecordingBackend()
        code, out = _run(world, bundle, backend, "--intake", "INTAKE-2")
        assert code == 2
        assert backend.calls == 0
        assert "esr_informed_review" in capsys.readouterr().err

    def test_intake_for_another_document_is_refused(self, world, bundle, capsys):
        record_esr_intake(
            world, intake_id="INTAKE-3", document_id="OTHER-1", submission_id="SUB-1",
            call_id="SYN-CALL-01", permitted_purpose="blind_pre_evaluation",
        )
        code, _ = _run(world, bundle, RecordingBackend(), "--intake", "INTAKE-3")
        assert code == 2
        assert "OTHER-1" in capsys.readouterr().err

    def test_directory_route_cannot_stamp_an_intake(self, world, bundle, capsys):
        record_esr_intake(
            world, intake_id="INTAKE-5", document_id="CAND-1", submission_id="SUB-1",
            call_id="SYN-CALL-01", permitted_purpose="blind_pre_evaluation",
        )
        evidence = ba.build_blind_evidence(world, "CAND-1", profile_version=bundle.version, out_dir=world / "r")
        backend = RecordingBackend()
        code = cmd.main(
            ["assess", "--candidate", str(evidence.candidate_dir), "--graph-root", str(world),
             "--out-dir", str(world / "d"), "--repo-root", str(world),
             "--profile", str(bundle.profile.source_path), "--intake", "INTAKE-5"],
            judge=_judge(world, backend), clock=lambda: FROZEN,
        )
        assert code == 2
        assert backend.calls == 0
        assert "document route" in capsys.readouterr().err

    def test_report_names_its_evidence_source(self, world, bundle):
        evidence = ba.build_blind_evidence(world, "CAND-1", profile_version=bundle.version, out_dir=world / "r")
        graph = ba.assess_candidate(_judge(world, RecordingBackend()), bundle, evidence=evidence, clock=lambda: FROZEN)
        plain = ba.assess_candidate(_judge(world, RecordingBackend()), bundle, evidence.candidate_dir, clock=lambda: FROZEN)
        assert graph.evidence_source == ba.EVIDENCE_SOURCE_DEV_GRAPH and graph.package_id
        assert plain.evidence_source == ba.EVIDENCE_SOURCE_DIRECTORY and plain.package_id == ""
        assert "leakage guard did not run" in ba.render_report(plain.to_dict())
        kwargs = {k: getattr(plain, k) for k in plain.__dataclass_fields__}
        with pytest.raises(ValueError, match="package_id"):
            ba.BlindAssessmentReport(**{**kwargs, "evidence_source": ba.EVIDENCE_SOURCE_DEV_GRAPH})

    def test_esr_availability_does_not_change_the_blind_package(self, world, bundle):
        record_esr_intake(
            world, intake_id="INTAKE-4", document_id="CAND-1", submission_id="SUB-1",
            call_id="SYN-CALL-01", permitted_purpose="blind_pre_evaluation", prior_submission=True,
            esr_availability="available", esr_reference="ESR-1",
        )
        plain = ba.build_blind_evidence(world, "CAND-1", profile_version=bundle.version, out_dir=world / "r")
        backend = RecordingBackend()
        code, out = _run(world, bundle, backend, "--intake", "INTAKE-4", out=world / "r")
        assert code == 0
        (path,) = [p for p in out.iterdir() if p.is_file()]
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["esr_availability"] == "available"
        assert data["package_id"] == plain.package.package_id
        assert all("ESR" not in p for p in backend.prompts)


# --------------------------------------------------------------------------- #
# Decision log
# --------------------------------------------------------------------------- #


class TestDecisionLog:
    def test_esr_intake_contract_entry_exists(self):
        log = find_repo_root() / "docs/tier4_orchestration_state/decision_log"
        entries = list(log.glob("dev-graph-esr-intake-contract_*.json"))
        assert len(entries) == 1
        rec = json.loads(entries[0].read_text(encoding="utf-8"))
        assert rec["record_type"] == "decision"
        text = json.dumps(rec)
        for needle in ("unknown", "not_applicable", "never", "esr_informed_review", "policy_forbidden", "LeakageError"):
            assert needle in text
