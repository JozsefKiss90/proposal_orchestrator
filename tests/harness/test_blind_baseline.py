"""
The frozen blind baseline (spec PE-06) and the tests that make blindness a
measured property rather than an asserted one.

Three groups:

* ``check_baseline_report`` over report dicts: every condition the freeze
  requires, each refused by name when absent.
* The ``freeze`` command end to end on the synthetic dev-graph world: the
  record binds candidate hash, profile version, assessor pin, snapshot id,
  package id and the preflight pack-set hash; the pin names the transport;
  cells and criterion scores are present with spreads; a second freeze into
  the same directory is refused; an edited copy is refused on load.
* Condition 2 of the ticket: a unique marker planted in the historical
  evaluation artifact and in a Tier 5 draft reaches no rendered prompt.

Conditions 1 and 3 (the argv-level empty tool list and the external working
directory) live in ``tests/harness/test_subscription_judge.py``.
"""
from __future__ import annotations

import copy
import json
import shutil
import uuid
from pathlib import Path

import pytest

import harness.blind_assessment as ba
import harness.blind_baseline as bb
import harness.commands.blind_assessment as cmd
from harness.judge import Judge, JudgeConfig
from harness.provenance import ProvenanceLog
from harness.rubrics import load_profile_bundle
from runner.dev_graph import build_snapshot, import_document
from tests.harness._preflight import preflighted
from tests.harness.test_blind_leakage import (
    CANDIDATE,
    ESR_DOC,
    FIXTURE,
    FROZEN,
    RecordingBackend,
    _graph_profile,
)

TRANSPORT = cmd.TRANSPORT_CLAUDE_CLI
VERSION = f"{TRANSPORT}-test@2026-10-05"


def _write_json(path: Path, data) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _judge(root: Path, backend, *, version: str = VERSION) -> Judge:
    return Judge(
        JudgeConfig(model="fake-assessor", version=version),
        backend=backend,
        provenance_log=ProvenanceLog(root / "provenance.jsonl"),
        clock=lambda: FROZEN,
    )


def _assess(world: Path, bundle, backend, *extra: str, version: str = VERSION) -> tuple[int, Path]:
    out = world / "reports"
    code = cmd.main(
        preflighted([
            "assess", "--document", "CAND-1", "--graph-root", str(world), "--out-dir", str(out),
            "--repo-root", str(world), "--profile", str(bundle.profile.source_path),
            "--transport", TRANSPORT, *extra,
        ]),
        judge=_judge(world, backend, version=version),
        clock=lambda: FROZEN,
    )
    (path,) = [p for p in out.iterdir() if p.is_file()]
    return code, path


def _candidate_dir(world: Path) -> Path:
    (candidate,) = (world / "reports" / "candidates").iterdir()
    return candidate


@pytest.fixture
def world(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    import_document(root, CANDIDATE)
    import_document(root, ESR_DOC, state="submitted")
    return root


@pytest.fixture
def bundle(world: Path):
    return load_profile_bundle(_graph_profile(world), repo_root=world)


# --------------------------------------------------------------------------- #
# The report carries the transport
# --------------------------------------------------------------------------- #


class _RecordingBackendWithInvocation(RecordingBackend):
    """A backend that, like the subscription one, says what its child could reach."""

    def invocation_record(self):
        return {"tools": "", "strict_mcp_config": True, "working_directory_outside_repository": True}


class TestTheReportNamesItsTransport:
    def test_the_command_stamps_the_transport_it_chose(self, world, bundle):
        code, path = _assess(world, bundle, RecordingBackend())
        assert code == 0
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["assessor_transport"] == TRANSPORT
        assert TRANSPORT in data["assessor_version"]

    def test_the_transport_tag_the_builder_enforces_is_the_command_choice(self):
        """The builder cannot import the command, so the two literals are kept
        in step by this test rather than by a shared import."""
        from harness.commands._subscription_judge import TRANSPORT_TAG

        assert TRANSPORT_TAG == cmd.TRANSPORT_CLAUDE_CLI

    def test_the_command_stamps_the_backends_invocation_record(self, world, bundle):
        """Condition 1 is then recorded by the run, not only proven by tests."""
        _code, path = _assess(world, bundle, _RecordingBackendWithInvocation())
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["assessor_invocation"]["tools"] == ""
        assert data["assessor_invocation"]["strict_mcp_config"] is True

    def test_a_backend_without_a_record_leaves_the_invocation_empty(self, world, bundle):
        _code, path = _assess(world, bundle, RecordingBackend())
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["assessor_invocation"] == {}


# --------------------------------------------------------------------------- #
# The conditions, one by one
# --------------------------------------------------------------------------- #


def _frozen_ready(world: Path, bundle) -> dict:
    _code, path = _assess(world, bundle, RecordingBackend())
    return json.loads(path.read_text(encoding="utf-8"))


class TestTheConditions:
    def test_a_complete_dev_graph_report_passes_every_check(self, world, bundle):
        assert bb.check_baseline_report(_frozen_ready(world, bundle)) == ()

    def test_every_name_a_check_can_emit_is_enumerated(self, world, bundle):
        """``checks_passed`` is derived from this tuple, so a check the function
        runs under a name the tuple lacks would be an unrecorded check."""
        report = _frozen_ready(world, bundle)
        report.update(snapshot_id="", preflight_report="", assessor_transport="", scope="partial",
                      cells=[], criterion_scoring=None, evidence_source="directory")
        names = {name for name, _ in bb.check_baseline_report(report)}
        assert names <= set(bb.BASELINE_CHECKS)

    def test_a_preflight_file_that_is_gone_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        Path(report["preflight_report"]).unlink()
        names = {name for name, _ in bb.check_baseline_report(report, repo_root=world)}
        assert "preflight_rebound" in names

    def test_a_preflight_file_whose_hash_moved_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        pre = Path(report["preflight_report"])
        data = json.loads(pre.read_text(encoding="utf-8"))
        data["pack_set_hash"] = "sha256:" + "0" * 64
        _write_json(pre, data)
        names = {name for name, _ in bb.check_baseline_report(report, repo_root=world)}
        assert "preflight_rebound" in names

    def test_a_criterion_panel_below_five_is_refused(self, world, bundle):
        """Spec decision 11: N=5 for the three criterion scores."""
        _code, path = _assess(world, bundle, RecordingBackend(), "--criterion-n", "3")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["criterion_scoring"]["samples_per_criterion"] == 3
        names = {name for name, _ in bb.check_baseline_report(data)}
        assert "criterion_samples" in names

    @pytest.mark.parametrize(
        "mutate, check",
        [
            (lambda r: r.update(snapshot_id=""), "evidence_bindings"),
            (lambda r: r.update(package_id=""), "evidence_bindings"),
            (lambda r: r.update(preflight_pack_set_hash=""), "preflight_binding"),
            (lambda r: r.update(preflight_report=""), "preflight_binding"),
            (lambda r: r.update(assessor_transport=""), "assessor_transport"),
            (lambda r: r.update(assessor_version="pin-7"), "pin_names_transport"),
            (lambda r: r.update(evidence_source=ba.EVIDENCE_SOURCE_DIRECTORY), "evidence_source"),
            (lambda r: r.update(scope="partial"), "scope"),
            (lambda r: r.update(cells=[]), "cells_present"),
            (lambda r: r.update(criterion_scoring=None), "criterion_scores_present"),
        ],
    )
    def test_each_missing_binding_is_refused_by_name(self, world, bundle, mutate, check):
        report = _frozen_ready(world, bundle)
        mutate(report)
        names = {name for name, _reason in bb.check_baseline_report(report)}
        assert check in names

    def test_a_cell_without_a_panel_spread_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["cells"][0]["coverage"]["verdict"]["agreement"] = None
        names = {name for name, _ in bb.check_baseline_report(report)}
        assert "cell_spreads" in names

    def test_a_cell_with_a_panel_below_three_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["cells"][0]["coverage"]["verdict"]["n"] = 2
        names = {name for name, _ in bb.check_baseline_report(report)}
        assert "cell_spreads" in names

    def test_an_unscored_criterion_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        score = report["criterion_scoring"]["scores"][0]
        score["score"] = None
        score["spread"] = None
        report["criterion_scoring"]["unscored_criteria"] = [score["criterion_id"]]
        report["criterion_scoring"]["total"] = None
        names = {name for name, _ in bb.check_baseline_report(report)}
        assert {"criterion_spreads", "criterion_scores_present", "criterion_total"} <= names

    def test_the_cells_only_run_cannot_be_frozen(self, world, bundle):
        code, path = _assess(world, bundle, RecordingBackend(), "--skip-criterion-scores")
        assert code == 0
        data = json.loads(path.read_text(encoding="utf-8"))
        names = {name for name, _ in bb.check_baseline_report(data)}
        assert "criterion_scores_present" in names


# --------------------------------------------------------------------------- #
# The freeze command
# --------------------------------------------------------------------------- #


def _freeze(world: Path, bundle, report: Path, baseline: Path) -> int:
    return cmd.main(
        [
            "freeze", "--report", str(report), "--candidate", str(_candidate_dir(world)),
            "--baseline-dir", str(baseline), "--repo-root", str(world),
            "--profile", str(bundle.profile.source_path),
        ],
        clock=lambda: FROZEN,
    )


class TestFreeze:
    def test_the_record_binds_everything_the_ticket_names(self, world, bundle, capsys):
        code, report = _assess(world, bundle, RecordingBackend())
        assert code == 0
        baseline = world / "docs" / "tier4_orchestration_state" / "baseline"
        assert _freeze(world, bundle, report, baseline) == 0
        frozen = bb.load_frozen_baseline(baseline)
        data = json.loads(report.read_text(encoding="utf-8"))
        b = frozen.record["bindings"]
        assert b["candidate_hash"] == data["candidate_hash"]
        assert b["profile_version"] == bundle.version
        assert b["assessor_pin"] == f"fake-assessor@{VERSION}"
        assert b["assessor_transport"] == TRANSPORT
        assert b["snapshot_id"] == build_snapshot(world).snapshot_id
        assert b["package_id"] == data["package_id"]
        assert b["preflight_pack_set_hash"] == data["preflight_pack_set_hash"]
        assert frozen.record["preflight_report_sha256"]
        assert frozen.record["frozen_at"] == FROZEN
        assert frozen.record["advisory"] is True and frozen.record["blocking"] is False
        assert frozen.record["checks_passed"] == list(bb.BASELINE_CHECKS)
        # repo-relative, portable: the report lives under the world root
        assert frozen.record["report_path"] == "reports/" + report.name
        printed = capsys.readouterr().out
        assert "FROZEN BLIND BASELINE" in printed
        assert TRANSPORT in printed

    def test_cells_and_criterion_scores_are_present_with_spreads(self, world, bundle):
        _code, report = _assess(world, bundle, RecordingBackend())
        baseline = world / "baseline"
        assert _freeze(world, bundle, report, baseline) == 0
        record = bb.load_frozen_baseline(baseline).record
        assert len(record["cells"]) == 3
        assert all(c["n"] >= 3 and c["agreement"] is not None for c in record["cells"])
        assert len(record["criterion_scores"]) == 3
        assert all(s["score"] is not None and s["spread"] is not None for s in record["criterion_scores"])
        assert record["criterion_total"]["total"] is not None
        assert "repeatability" in record["spread_label"]

    def test_the_copy_is_byte_identical_and_named_by_its_hash(self, world, bundle):
        _code, report = _assess(world, bundle, RecordingBackend())
        baseline = world / "baseline"
        _freeze(world, bundle, report, baseline)
        frozen = bb.load_frozen_baseline(baseline)
        assert frozen.copy_path.read_bytes() == report.read_bytes()
        assert frozen.record["report_sha256"][:12] in frozen.copy_path.name
        assert frozen.freeze_path.name.endswith(".freeze.json")

    def test_a_second_freeze_into_the_same_directory_is_refused(self, world, bundle, capsys):
        _code, report = _assess(world, bundle, RecordingBackend())
        baseline = world / "baseline"
        assert _freeze(world, bundle, report, baseline) == 0
        before = {p.name: p.read_bytes() for p in baseline.iterdir()}
        assert _freeze(world, bundle, report, baseline) == 2
        assert "never replaced" in capsys.readouterr().err
        assert {p.name: p.read_bytes() for p in baseline.iterdir()} == before

    def test_a_report_that_fails_a_condition_writes_nothing(self, world, bundle, capsys):
        _code, report = _assess(world, bundle, RecordingBackend(), version="pin-7")
        baseline = world / "baseline"
        assert _freeze(world, bundle, report, baseline) == 2
        assert "pin_names_transport" in capsys.readouterr().err
        assert not baseline.exists()

    def test_a_report_bound_to_another_candidate_is_refused(self, world, bundle, capsys):
        _code, report = _assess(world, bundle, RecordingBackend())
        section = next(_candidate_dir(world).glob("*.json"))
        data = json.loads(section.read_text(encoding="utf-8"))
        data["sub_sections"][0]["content"] += " Edited."
        _write_json(section, data)
        assert _freeze(world, bundle, report, world / "baseline") == 2
        assert "hash" in capsys.readouterr().err

    def test_an_edited_frozen_copy_is_refused_on_load(self, world, bundle):
        _code, report = _assess(world, bundle, RecordingBackend())
        baseline = world / "baseline"
        _freeze(world, bundle, report, baseline)
        frozen = bb.load_frozen_baseline(baseline)
        frozen.copy_path.write_text(
            frozen.copy_path.read_text(encoding="utf-8").replace("fake-assessor", "other"),
            encoding="utf-8",
        )
        with pytest.raises(bb.BlindBaselineError, match="edited after"):
            bb.load_frozen_baseline(baseline)

    def test_an_empty_directory_holds_no_baseline(self, tmp_path):
        with pytest.raises(bb.BlindBaselineError, match="no frozen baseline"):
            bb.load_frozen_baseline(tmp_path)


# --------------------------------------------------------------------------- #
# Condition 2: planted markers reach no rendered prompt
# --------------------------------------------------------------------------- #


class TestPlantedMarkers:
    """A marker string that exists nowhere else is written into the historical
    evaluation (both as the ESR document record and as a Tier 4 ``esr/``
    artifact) and into a Tier 5 draft.  The assessor's prompts, the
    materialised candidate and the report must all be free of both.  The
    on-disk presence is asserted first, so a passing test is not vacuous."""

    def _planted_world(self, tmp_path: Path) -> tuple[Path, str, str]:
        esr_marker = f"ESRMARK-{uuid.uuid4().hex}"
        draft_marker = f"T5MARK-{uuid.uuid4().hex}"
        root = tmp_path / "repo"
        shutil.copytree(FIXTURE, root)
        esr = json.loads((root / ESR_DOC).read_text(encoding="utf-8"))
        esr = copy.deepcopy(esr)
        esr["sections"][0]["content"] += f" {esr_marker}"
        esr["claims"][0]["text"] += f" {esr_marker}"
        _write_json(root / ESR_DOC, esr)
        import_document(root, CANDIDATE)
        import_document(root, ESR_DOC, state="submitted")
        # Both the generic esr/ segment the preflight scans for and the path
        # spec §6 gives the milestone's artifact.
        for esr_dir in ("esr", "msca_dn/esr"):
            _write_json(
                root / "docs" / "tier4_orchestration_state" / esr_dir / "historical-esr.json",
                {"record_type": "historical_evaluation", "score": 85.8, "text": esr_marker},
            )
        _write_json(
            root / "docs" / "tier5_deliverables" / "proposal_sections" / "excellence_section.json",
            {"section_id": "excellence_section", "content": f"A draft paragraph. {draft_marker}"},
        )
        return root, esr_marker, draft_marker

    def test_markers_are_on_disk_and_absent_from_every_prompt(self, tmp_path):
        root, esr_marker, draft_marker = self._planted_world(tmp_path)
        bundle = load_profile_bundle(_graph_profile(root), repo_root=root)
        on_disk = "\n".join(
            p.read_text(encoding="utf-8", errors="ignore")
            for p in (root / "docs").rglob("*.json")
        )
        assert esr_marker in on_disk and draft_marker in on_disk
        documents = root / "docs" / "tier4_orchestration_state" / "dev_graph" / "documents"
        assert any(esr_marker in p.read_text(encoding="utf-8") for p in documents.rglob("*.json"))

        backend = RecordingBackend()
        code, report = _assess(root, bundle, backend)
        assert code == 0
        assert backend.prompts
        for prompt in backend.prompts:
            assert esr_marker not in prompt
            assert draft_marker not in prompt
        report_text = report.read_text(encoding="utf-8")
        assert esr_marker not in report_text and draft_marker not in report_text
        for section in _candidate_dir(root).glob("*.json"):
            text = section.read_text(encoding="utf-8")
            assert esr_marker not in text and draft_marker not in text

    def test_the_candidate_itself_still_reaches_the_prompts(self, tmp_path):
        """The check above would pass trivially over an empty prompt."""
        root, _esr_marker, _draft_marker = self._planted_world(tmp_path)
        bundle = load_profile_bundle(_graph_profile(root), repo_root=root)
        backend = RecordingBackend()
        _assess(root, bundle, backend)
        candidate = json.loads((root / CANDIDATE).read_text(encoding="utf-8"))
        first_words = candidate["sections"][0]["content"].split(".")[0]
        assert any(first_words in p for p in backend.prompts)
