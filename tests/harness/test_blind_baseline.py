"""
The frozen blind baseline (spec PE-06) and the tests that make blindness a
measured property rather than an asserted one.

Six groups:

* ``run_baseline_checks`` over report dicts: every condition the freeze
  requires, each refused by name when absent.
* The identity sets (V04): the cells are the profile's grid and the criterion
  scores its criteria — a report missing one, or carrying one twice, is
  refused. This is the group that notices a *deleted* record, which the
  per-entry checks cannot.
* The arithmetic (V04): the panel mean, agreement and majority call, each
  criterion's median and spread, and the weighted total all recompute from
  the draws the report carries, or the freeze refuses the report.
* The invocation and isolation evidence (V04): what the report's transport
  owes, and what it is recorded as not owing.
* The ``freeze`` command end to end on the synthetic dev-graph world: the
  record binds candidate hash, profile version, assessor pin, snapshot id,
  package id and the preflight pack-set hash; the pin names the transport;
  cells and criterion scores are present with spreads; a second freeze into
  the same directory is refused; an edited copy is refused on load.
* Condition 2 of the ticket: a unique marker planted in the historical
  evaluation artifact and in a Tier 5 draft reaches no rendered prompt.

A seventh group runs the real ``freeze_baseline`` path over the committed
MSCA-DN baseline: the control still freezes at 74.6 and reproduces the
committed bindings, and each of the readiness audit's four reproduced probes
is refused by name with nothing written.

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
import harness.grounding_scope as gs
from harness.judge import Judge, JudgeConfig
from harness.provenance import ProvenanceLog
from harness.rubrics import load_profile_bundle
from runner.dev_graph import build_snapshot, import_document
from runner.paths import find_repo_root
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


def _assess(
    world: Path,
    bundle,
    backend,
    *extra: str,
    version: str = VERSION,
    replace: dict[str, str] | None = None,
) -> tuple[int, Path]:
    argv = [
        "assess", "--document", "CAND-1", "--graph-root", str(world), "--out-dir", str(out := world / "reports"),
        "--repo-root", str(world), "--profile", str(bundle.profile.source_path),
        "--transport", TRANSPORT, "--grounding-scope", gs.SCOPE_CONTENT_FOCUSED, *extra,
    ]
    for flag, value in (replace or {}).items():
        argv[argv.index(flag) + 1] = value
    code = cmd.main(
        preflighted(argv),
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


class _BackendWithoutInvocation(RecordingBackend):
    """A backend that keeps no account of its invocation, as the API one does not."""

    invocation_record = None


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

    def test_the_transports_the_freeze_knows_are_the_transports_the_command_offers(self):
        """``blind_baseline`` cannot import the command it is called by, so the
        transport vocabulary is kept in step here."""
        assert set(bb.TRANSPORT_ISOLATION_EVIDENCE) == {
            cmd.TRANSPORT_CLAUDE_CLI,
            cmd.TRANSPORT_OPENAI,
        }

    def test_the_isolation_the_freeze_requires_is_what_the_backend_declares(self, tmp_path):
        """The required declarations must be ones the subscription backend
        actually makes, or no real baseline could satisfy the check."""
        from harness.commands import _subscription_judge as sj

        _judge, backend = sj.build_subscription_judge(
            JudgeConfig(model="claude-sonnet-5", version=VERSION),
            prov_path=tmp_path / "prov.jsonl",
            repo_root=find_repo_root(),
            log=lambda _m: None,
        )
        record = backend.invocation_record()
        required = bb.TRANSPORT_ISOLATION_EVIDENCE[cmd.TRANSPORT_CLAUDE_CLI]
        assert {key: record[key] for key in required} == dict(required)

    def test_the_command_stamps_the_backends_invocation_record(self, world, bundle):
        """Condition 1 is then recorded by the run, not only proven by tests."""
        _code, path = _assess(world, bundle, RecordingBackend())
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["assessor_invocation"]["tools"] == ""
        assert data["assessor_invocation"]["strict_mcp_config"] is True

    def test_a_backend_without_a_record_leaves_the_invocation_empty(self, world, bundle):
        _code, path = _assess(world, bundle, _BackendWithoutInvocation())
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["assessor_invocation"] == {}


# --------------------------------------------------------------------------- #
# The conditions, one by one
# --------------------------------------------------------------------------- #


def _frozen_ready(world: Path, bundle) -> dict:
    _code, path = _assess(world, bundle, RecordingBackend())
    return json.loads(path.read_text(encoding="utf-8"))


def _failures(report: dict, bundle, **kwargs) -> tuple[tuple[str, str], ...]:
    """The failures of a check run, which is what most of these cases assert on."""
    return bb.run_baseline_checks(report, bundle, **kwargs).failures


def _names(report: dict, bundle, **kwargs) -> set[str]:
    return {name for name, _ in _failures(report, bundle, **kwargs)}


class TestTheConditions:
    def test_a_complete_dev_graph_report_passes_every_check(self, world, bundle):
        assert _failures(_frozen_ready(world, bundle), bundle) == ()

    def test_every_name_a_check_can_emit_is_enumerated(self, world, bundle):
        """``checks_passed`` is derived from this tuple, so a check the function
        runs under a name the tuple lacks would be an unrecorded check."""
        report = _frozen_ready(world, bundle)
        report.update(snapshot_id="", preflight_report="", assessor_transport="", scope="partial",
                      cells=[], criterion_scoring=None, evidence_source="directory")
        names = {name for name, _ in _failures(report, bundle)}
        assert names <= set(bb.BASELINE_CHECKS)

    def test_a_preflight_file_that_is_gone_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        Path(report["preflight_report"]).unlink()
        names = {name for name, _ in _failures(report, bundle, repo_root=world)}
        assert "preflight_rebound" in names

    def test_a_preflight_file_whose_hash_moved_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        pre = Path(report["preflight_report"])
        data = json.loads(pre.read_text(encoding="utf-8"))
        data["pack_set_hash"] = "sha256:" + "0" * 64
        _write_json(pre, data)
        names = {name for name, _ in _failures(report, bundle, repo_root=world)}
        assert "preflight_rebound" in names

    def test_a_criterion_panel_below_five_is_refused(self, world, bundle):
        """Spec decision 11: N=5 for the three criterion scores."""
        _code, path = _assess(world, bundle, RecordingBackend(), "--criterion-n", "3")
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["criterion_scoring"]["samples_per_criterion"] == 3
        names = {name for name, _ in _failures(data, bundle)}
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
        names = {name for name, _reason in _failures(report, bundle)}
        assert check in names

    def test_a_cell_without_a_panel_spread_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["cells"][0]["coverage"]["verdict"]["agreement"] = None
        names = {name for name, _ in _failures(report, bundle)}
        assert "cell_spreads" in names

    def test_a_cell_with_a_panel_below_three_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["cells"][0]["coverage"]["verdict"]["n"] = 2
        names = {name for name, _ in _failures(report, bundle)}
        assert "cell_spreads" in names

    def test_an_unscored_criterion_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        score = report["criterion_scoring"]["scores"][0]
        score["score"] = None
        score["spread"] = None
        report["criterion_scoring"]["unscored_criteria"] = [score["criterion_id"]]
        report["criterion_scoring"]["total"] = None
        names = {name for name, _ in _failures(report, bundle)}
        assert {"criterion_spreads", "criterion_scores_present", "criterion_total"} <= names

    def test_the_cells_only_run_cannot_be_frozen(self, world, bundle):
        code, path = _assess(world, bundle, RecordingBackend(), "--skip-criterion-scores")
        assert code == 0
        data = json.loads(path.read_text(encoding="utf-8"))
        names = {name for name, _ in _failures(data, bundle)}
        assert "criterion_scores_present" in names


# --------------------------------------------------------------------------- #
# What is absent: the identity sets the profile declares (V04)
# --------------------------------------------------------------------------- #


class TestTheIdentitySets:
    """Removing records is the failure mode the per-entry checks cannot see:
    the loops that bind and range-check entries run over what is left, so a
    report with one of its cells kept satisfies all of them.  The identity
    sets are what notices."""

    def test_the_grid_is_the_rubric_set_crossed_with_the_profiles_sections(self, bundle):
        assert ba.expected_cells(bundle) == tuple(
            (r.criterion_id, r.expectation_key, s)
            for r in bundle.rubric_set.rubrics
            for s in bundle.profile.section_ids_for(r.criterion_id)
        )

    def test_a_report_missing_a_cell_is_refused(self, world, bundle):
        """Two independent witnesses to a deleted cell: the identity set, and
        the recorded grounding scope, whose counts no longer describe the
        cells that remain (V06)."""
        report = _frozen_ready(world, bundle)
        dropped = report["cells"].pop()
        failures = _failures(report, bundle)
        assert {name for name, _ in failures} == {"cell_identity", "grounding_scope"}
        reason = dict(failures)["cell_identity"]
        assert dropped["expectation_key"] in reason
        assert "total: report 3, cells 2" in dict(failures)["grounding_scope"]

    def test_a_report_with_one_cell_of_the_grid_is_refused(self, world, bundle):
        """The audit's second probe, in the shape it was reproduced."""
        report = _frozen_ready(world, bundle)
        report["cells"] = report["cells"][:1]
        assert "cell_identity" in _names(report, bundle)

    def test_a_duplicated_cell_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["cells"].append(copy.deepcopy(report["cells"][0]))
        failures = dict(_failures(report, bundle))
        assert "more than once" in failures["cell_identity"]
        # The duplicate is a fourth cell the recorded scope counted three of.
        assert "total: report 3, cells 4" in failures["grounding_scope"]

    def test_a_cell_the_profile_does_not_grade_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["cells"][0]["expectation_key"] = "invented-expectation"
        ((name, reason),) = _failures(report, bundle)
        assert name == "cell_identity"
        assert "invented-expectation" in reason

    def test_a_report_missing_a_criterion_score_is_refused(self, world, bundle):
        """The audit's third probe: one of three criterion scores kept."""
        report = _frozen_ready(world, bundle)
        report["criterion_scoring"]["scores"] = report["criterion_scoring"]["scores"][:1]
        names = _names(report, bundle)
        assert "criterion_identity" in names
        # And the total cannot be recomputed from one score of three.
        assert "total_recomputed" in names

    def test_a_duplicated_criterion_score_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        scores = report["criterion_scoring"]["scores"]
        scores.append(copy.deepcopy(scores[0]))
        ((name, reason),) = _failures(report, bundle)
        assert name == "criterion_identity"
        assert "more than once" in reason


# --------------------------------------------------------------------------- #
# What does not reproduce: the arithmetic the report declares (V04)
# --------------------------------------------------------------------------- #


class TestTheArithmeticReproduces:
    def test_a_panel_short_of_its_declared_members_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["cells"][0]["coverage"]["verdict"]["members"].pop()
        reasons = [r for n, r in _failures(report, bundle) if n == "cell_members"]
        assert any("carries 2 member(s)" in r for r in reasons)

    def test_a_member_score_off_the_unit_interval_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["cells"][0]["coverage"]["verdict"]["members"][0]["score"] = 1.5
        assert "cell_members" in _names(report, bundle)

    def test_a_panel_mean_that_does_not_reproduce_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["cells"][0]["coverage"]["verdict"]["score"] = 0.42
        assert "cell_members" in _names(report, bundle)

    def test_an_agreement_that_does_not_reproduce_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["cells"][0]["coverage"]["verdict"]["agreement"] = 0.5
        assert "cell_members" in _names(report, bundle)

    def test_a_majority_call_the_members_do_not_support_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["cells"][0]["coverage"]["verdict"]["passed"] = False
        assert "cell_members" in _names(report, bundle)

    def test_a_panel_of_members_about_different_properties_is_refused(self, world, bundle):
        """The vote is the producer's own ``majority_vote``, so the panel has
        to satisfy it: members of one vote concern one property."""
        report = _frozen_ready(world, bundle)
        report["cells"][0]["coverage"]["verdict"]["members"][0]["property_key"] = "elsewhere"
        reasons = [r for n, r in _failures(report, bundle) if n == "cell_members"]
        assert any("will not re-vote" in r for r in reasons)

    def test_a_criterion_the_scorecard_does_not_weight_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["criterion_scoring"]["scores"][0]["criterion_id"] = "invented"
        names = _names(report, bundle)
        assert "criterion_identity" in names
        assert "criterion_arithmetic" in names

    def test_a_criterion_median_that_does_not_reproduce_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["criterion_scoring"]["scores"][0]["score"] = 4.9
        names = _names(report, bundle)
        assert "criterion_arithmetic" in names
        assert "total_recomputed" in names

    def test_a_criterion_spread_that_does_not_reproduce_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["criterion_scoring"]["scores"][0]["spread"] = 2.5
        assert "criterion_arithmetic" in _names(report, bundle)

    def test_a_sample_off_the_scorecards_scale_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["criterion_scoring"]["scores"][0]["samples"][0]["score"] = 9.0
        assert "criterion_arithmetic" in _names(report, bundle)

    def test_a_declared_sample_count_the_samples_do_not_match_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["criterion_scoring"]["samples_per_criterion"] = 7
        assert "criterion_arithmetic" in _names(report, bundle)

    def test_a_criterion_scored_with_no_samples_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["criterion_scoring"]["scores"][0]["samples"] = []
        assert "criterion_arithmetic" in _names(report, bundle)

    def test_weighted_points_that_do_not_reproduce_are_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["criterion_scoring"]["scores"][0]["weighted_points"] = 99.0
        assert "criterion_arithmetic" in _names(report, bundle)

    def test_a_total_the_criterion_scores_do_not_give_is_refused(self, world, bundle):
        """The audit's fifth probe: the total replaced with another number."""
        report = _frozen_ready(world, bundle)
        report["criterion_scoring"]["total"] = 99.9
        ((name, reason),) = _failures(report, bundle)
        assert name == "total_recomputed"
        assert "99.9" in reason

    def test_a_threshold_verdict_the_total_does_not_support_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        met = report["criterion_scoring"]["overall_threshold_met"]
        report["criterion_scoring"]["overall_threshold_met"] = not met
        assert "total_recomputed" in _names(report, bundle)

    def test_an_overall_maximum_the_scorecard_does_not_declare_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["criterion_scoring"]["overall_max"] = 1000.0
        assert "total_recomputed" in _names(report, bundle)


# --------------------------------------------------------------------------- #
# The invocation and isolation evidence the transport owes (V04)
# --------------------------------------------------------------------------- #


class TestTheInvocationEvidence:
    def test_a_report_without_an_invocation_record_is_refused(self, world, bundle):
        """The audit's fourth probe: ``assessor_invocation`` removed."""
        report = _frozen_ready(world, bundle)
        report.pop("assessor_invocation")
        ((name, reason),) = _failures(report, bundle)
        assert name == "invocation_evidence"
        assert TRANSPORT in reason

    def test_an_empty_invocation_record_is_refused(self, world, bundle):
        _code, path = _assess(world, bundle, _BackendWithoutInvocation())
        report = json.loads(path.read_text(encoding="utf-8"))
        assert "invocation_evidence" in _names(report, bundle)

    def test_an_assessor_that_ran_inside_the_repository_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["assessor_invocation"]["working_directory_outside_repository"] = False
        ((name, reason),) = _failures(report, bundle)
        assert name == "invocation_evidence"
        assert "working_directory_outside_repository" in reason

    def test_an_assessor_that_could_reach_tools_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["assessor_invocation"]["tools"] = "Read,Glob"
        assert "invocation_evidence" in _names(report, bundle)

    def test_a_missing_declaration_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["assessor_invocation"].pop("strict_mcp_config")
        ((name, reason),) = _failures(report, bundle)
        assert name == "invocation_evidence"
        assert "strict_mcp_config" in reason

    def test_a_working_directory_inside_the_repository_is_refused(self, world, bundle):
        """The declaration is measured, not read: a record claiming its
        assessor ran outside the repository while naming a directory inside it
        is refused on the path, whatever it declares."""
        report = _frozen_ready(world, bundle)
        report["assessor_invocation"]["working_directory"] = str(world / "harness")
        assert report["assessor_invocation"]["working_directory_outside_repository"] is True
        ((name, reason),) = _failures(report, bundle, repo_root=world)
        assert name == "invocation_evidence"
        assert "lies under the repository root" in reason

    def test_an_unnamed_working_directory_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report["assessor_invocation"].pop("working_directory")
        ((name, reason),) = _failures(report, bundle, repo_root=world)
        assert name == "invocation_evidence"
        assert "cannot be measured" in reason

    def test_a_transport_the_freeze_does_not_know_is_refused(self, world, bundle):
        report = _frozen_ready(world, bundle)
        report.update(assessor_transport="carrier-pigeon", assessor_version="carrier-pigeon-1")
        assert "invocation_evidence" in _names(report, bundle)

    def test_a_transport_with_no_child_process_is_recorded_not_applicable(self, world, bundle):
        """An API transport declares no isolation of its own.  The check is
        then not claimed as passed — which is what ``checks_passed`` means."""
        report = _frozen_ready(world, bundle)
        report.update(
            assessor_transport=cmd.TRANSPORT_OPENAI,
            assessor_version=f"{cmd.TRANSPORT_OPENAI}-test@2026-10-05",
            assessor_invocation={},
        )
        run = bb.run_baseline_checks(report, bundle)
        assert run.failures == ()
        assert [name for name, _ in run.not_applicable] == ["invocation_evidence"]
        assert "invocation_evidence" not in run.passed
        assert set(run.passed) == set(bb.BASELINE_CHECKS) - {"invocation_evidence"}


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
        assert f"{len(bb.BASELINE_CHECKS)} of {len(bb.BASELINE_CHECKS)} passed" in printed

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

    def test_a_check_that_did_not_apply_is_not_recorded_as_passed(self, world, bundle):
        """``checks_passed`` lists what ran and held.  An API-transport report
        owes no child-process isolation, so the record says the check did not
        apply rather than listing it among the passes."""
        version = f"{cmd.TRANSPORT_OPENAI}-test@2026-10-05"
        _code, report = _assess(
            world, bundle, RecordingBackend(), "--transport", cmd.TRANSPORT_OPENAI,
            version=version,
        )
        baseline = world / "baseline"
        assert _freeze(world, bundle, report, baseline) == 0
        record = bb.load_frozen_baseline(baseline).record
        assert "invocation_evidence" not in record["checks_passed"]
        assert [row["check"] for row in record["checks_not_applicable"]] == [
            "invocation_evidence"
        ]
        assert record["checks_not_applicable"][0]["reason"]

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


# --------------------------------------------------------------------------- #
# The committed MSCA-DN baseline: the control still freezes, the audit's four
# reproduced probes do not (V04)
# --------------------------------------------------------------------------- #

REPO = find_repo_root()
DN_BASELINE_DIR = REPO / "docs/tier4_orchestration_state/msca_dn/baselines/resolved_fixes_2026-10-06"
DN_REPORT = DN_BASELINE_DIR / "blind_baseline_f60ae6e0a2a1.json"
DN_FREEZE = DN_BASELINE_DIR / "blind_baseline_f60ae6e0a2a1.freeze.json"
DN_CANDIDATE = (
    REPO / "harness/blind_reports/candidates/MSCA-DN-2025_sanitised_part_b@b51a103520b58ded"
)
DN_PROFILE = REPO / "harness/profiles/msca_dn_2026_default.json"

#: The audit's probes, each built from a copy of the committed report by
#: changing only what the row names (readiness audit F03, section 8).
AUDIT_PROBES = [
    pytest.param(
        lambda r: r.__setitem__("cells", r["cells"][:1]),
        "cell_identity",
        id="one-of-ten-cells",
    ),
    pytest.param(
        lambda r: r["criterion_scoring"].__setitem__(
            "scores", r["criterion_scoring"]["scores"][:1]
        ),
        "criterion_identity",
        id="one-of-three-criterion-scores",
    ),
    pytest.param(
        lambda r: r.pop("assessor_invocation"),
        "invocation_evidence",
        id="assessor-invocation-removed",
    ),
    pytest.param(
        lambda r: r["criterion_scoring"].__setitem__("total", 99.9),
        "total_recomputed",
        id="total-replaced-with-99.9",
    ),
]


@pytest.mark.skipif(
    not DN_REPORT.is_file() or not DN_CANDIDATE.is_dir(),
    reason="MSCA-DN baseline or candidate absent",
)
class TestTheDeclaredGroundingScope:
    """V06, on the synthetic world: a run that declares its scope has it
    checked rather than skipped, the freeze binds it, and the two refusals
    criterion 5 asks for hold at the command and at the freeze."""

    def test_a_declared_run_has_the_check_run_and_passed(self, world, bundle):
        run = bb.run_baseline_checks(_frozen_ready(world, bundle), bundle)
        assert run.failures == ()
        assert run.not_applicable == ()
        assert "grounding_scope" in run.passed

    def test_the_report_records_the_declaration_beside_the_measurement(self, world, bundle):
        report = _frozen_ready(world, bundle)
        scope = report["grounding_scope"]
        assert scope["declared"] == gs.SCOPE_CONTENT_FOCUSED
        assert scope["declaration_source"] == gs.DECLARED_BY_THE_RUN
        assert scope["measured"] == gs.GROUNDING_ASSESSED
        assert (scope["with_claims"], scope["total"]) == (3, 3)

    def test_the_freeze_binds_the_declaration_the_report_made(self, world, bundle, tmp_path):
        _code, path = _assess(world, bundle, RecordingBackend())
        frozen = bb.freeze_baseline(
            path, _candidate_dir(world), bundle,
            baseline_dir=tmp_path / "baseline", repo_root=world, clock=lambda: FROZEN,
        )
        assert frozen.record["grounding_scope"]["declared"] == gs.SCOPE_CONTENT_FOCUSED
        assert frozen.record["schema_version"] == "1.2.0"
        assert gs.SCOPE_CONTENT_FOCUSED in bb.render_freeze(frozen.record)

    def test_the_command_refuses_a_source_grounded_run_before_any_assessor_call(
        self, world, bundle
    ):
        """Criterion 5 at the command: refused while X01 is open, with no
        quota spent — the backend is never called."""
        backend = RecordingBackend()
        out = world / "reports"
        code = cmd.main(
            [
                "preflight", "--document", "CAND-1", "--graph-root", str(world),
                "--out-dir", str(out), "--repo-root", str(world),
                "--profile", str(bundle.profile.source_path),
                "--transport", TRANSPORT,
                "--grounding-scope", gs.SCOPE_SOURCE_GROUNDED,
            ],
            judge=_judge(world, backend),
            clock=lambda: FROZEN,
        )
        assert code == 2
        assert backend.calls == 0

    def test_with_the_route_implemented_a_fully_grounded_run_may_declare_it(
        self, world, bundle, monkeypatch
    ):
        """The refusal is the capability flag, not a hardcoded no: the same
        world declares the scope once X01 would have landed."""
        monkeypatch.setattr(gs, "IMPORTED_CLAIM_ROUTE_IMPLEMENTED", True)
        _code, path = _assess(
            world, bundle, RecordingBackend(),
            replace={"--grounding-scope": gs.SCOPE_SOURCE_GROUNDED},
        )
        report = json.loads(path.read_text(encoding="utf-8"))
        assert report["grounding_scope"]["declared"] == gs.SCOPE_SOURCE_GROUNDED
        assert bb.run_baseline_checks(report, bundle).failures == ()


class TestTheCommittedMscaDnBaseline:
    """The real `freeze_baseline` path, on the real candidate and the loaded
    profile bundle, as the audit exercised it.  Every case works on its own
    copy under ``tmp_path`` and writes nowhere else."""

    @pytest.fixture
    def dn_bundle(self):
        return load_profile_bundle(DN_PROFILE, repo_root=REPO)

    def _copy(self, tmp_path: Path, mutate=None) -> Path:
        copy_path = tmp_path / "report.json"
        if mutate is None:
            shutil.copyfile(DN_REPORT, copy_path)
            return copy_path
        data = json.loads(DN_REPORT.read_text(encoding="utf-8"))
        mutate(data)
        return _write_json(copy_path, data)

    def _freeze_copy(self, tmp_path: Path, dn_bundle, report: Path) -> bb.FrozenBaseline:
        return bb.freeze_baseline(
            report,
            DN_CANDIDATE,
            dn_bundle,
            baseline_dir=tmp_path / "baseline",
            repo_root=REPO,
            clock=lambda: FROZEN,
        )

    def test_the_unmodified_control_still_freezes_at_74_6(self, tmp_path, dn_bundle):
        """V06 added `grounding_scope`, and this report predates the
        declaration.  Its cells are unanimously unassessable, so the check is
        recorded not applicable and the freeze records the measurement; every
        other check still passes and the total is still 74.6."""
        frozen = self._freeze_copy(tmp_path, dn_bundle, self._copy(tmp_path))
        assert frozen.record["criterion_total"]["total"] == 74.6
        assert frozen.record["checks_passed"] == [
            name for name in bb.BASELINE_CHECKS if name != "grounding_scope"
        ]
        ((check, _reason),) = [
            (row["check"], row["reason"]) for row in frozen.record["checks_not_applicable"]
        ]
        assert check == "grounding_scope"
        assert len(frozen.record["cells"]) == 10
        assert len(frozen.record["criterion_scores"]) == 3

    def test_the_freeze_records_the_measured_grounding_of_the_undeclared_run(
        self, tmp_path, dn_bundle
    ):
        """Criterion 3: a later stage reading this freeze cannot present the
        run as source-grounded, because the record says unassessable and
        carries no declaration to misread."""
        frozen = self._freeze_copy(tmp_path, dn_bundle, self._copy(tmp_path))
        scope = frozen.record["grounding_scope"]
        assert scope["declared"] is None
        assert scope["declaration_source"] == gs.MEASURED_HERE
        assert scope["measured"] == gs.GROUNDING_UNASSESSABLE
        assert (scope["with_claims"], scope["total"]) == (0, 10)
        assert scope["include_claims"] is False
        assert "withheld" in scope["reason"]
        assert gs.SCOPE_SOURCE_GROUNDED not in json.dumps(scope)

    def test_the_rendered_freeze_states_the_grounding_prominently(self, tmp_path, dn_bundle):
        frozen = self._freeze_copy(tmp_path, dn_bundle, self._copy(tmp_path))
        screen = bb.render_freeze(frozen.record)
        assert f"GROUNDING  [{gs.GROUNDING_UNASSESSABLE.upper()}]" in screen
        assert "none declared" in screen
        assert "withheld" in screen

    def test_the_three_renderers_print_the_same_derived_line(self, tmp_path, dn_bundle):
        """One statement of the headline and the reason, three readers."""
        report = json.loads(DN_REPORT.read_text(encoding="utf-8"))
        frozen = self._freeze_copy(tmp_path, dn_bundle, self._copy(tmp_path))
        scope = gs.measured_only(
            include_claims=False, with_claims=0, total=10, unit=gs.UNIT_CELL
        )
        for screen in (ba.render_report(report), bb.render_freeze(frozen.record)):
            assert scope.headline in screen
            assert scope.reason in screen

    def test_a_freeze_record_written_before_the_block_still_renders_grounding(
        self, tmp_path, dn_bundle
    ):
        """The committed 1.0.0 record carries no block; its cell summaries and
        its bindings are enough to measure one."""
        frozen = self._freeze_copy(tmp_path, dn_bundle, self._copy(tmp_path))
        legacy = {k: v for k, v in frozen.record.items() if k != "grounding_scope"}
        screen = bb.render_freeze(legacy)
        assert f"GROUNDING  [{gs.GROUNDING_UNASSESSABLE.upper()}]" in screen
        assert "none declared" in screen

    def test_a_freeze_record_whose_counts_cannot_be_measured_says_so(self, tmp_path, dn_bundle):
        frozen = self._freeze_copy(tmp_path, dn_bundle, self._copy(tmp_path))
        record = dict(frozen.record)
        record["grounding_scope"] = {**record["grounding_scope"], "with_claims": 11}
        assert "GROUNDING  [NOT MEASURABLE]" in bb.render_freeze(record)

    def test_a_source_grounded_declaration_on_the_committed_report_is_refused(
        self, tmp_path, dn_bundle
    ):
        """Criterion 5, at the freeze: the declaration is refused while X01 is
        open, and refused again on the measurement if the flag is ever set."""
        def declare(data):
            data["grounding_scope"] = {
                "declared": gs.SCOPE_SOURCE_GROUNDED,
                "declaration_source": gs.DECLARED_BY_THE_RUN,
                "measured": gs.GROUNDING_UNASSESSABLE,
                "include_claims": False,
                "unit": gs.UNIT_CELL,
                "with_claims": 0,
                "total": 10,
                "reason": "asserted",
            }

        report = self._copy(tmp_path, declare)
        with pytest.raises(bb.BlindBaselineError) as caught:
            self._freeze_copy(tmp_path, dn_bundle, report)
        assert "grounding_scope: " in str(caught.value)
        assert "X01" in str(caught.value)
        assert not (tmp_path / "baseline").exists()

    def test_a_declared_scope_the_cells_contradict_is_refused(self, tmp_path, dn_bundle):
        def overstate(data):
            data["grounding_scope"] = {
                "declared": gs.SCOPE_CONTENT_FOCUSED,
                "declaration_source": gs.DECLARED_BY_THE_RUN,
                "measured": gs.GROUNDING_ASSESSED,
                "include_claims": False,
                "unit": gs.UNIT_CELL,
                "with_claims": 10,
                "total": 10,
                "reason": "asserted",
            }

        report = self._copy(tmp_path, overstate)
        with pytest.raises(bb.BlindBaselineError) as caught:
            self._freeze_copy(tmp_path, dn_bundle, report)
        assert "grounding_scope: " in str(caught.value)

    def test_a_report_that_declares_nothing_and_grounded_a_cell_is_refused(
        self, tmp_path, dn_bundle
    ):
        """The one undeclared case that is not derivable: there is a grounding
        result, so the baseline must say which scope produced it."""
        def ground_one(data):
            data["include_claims"] = True
            data["cells"][0]["grounding"] = gs.GROUNDING_IN_VERDICT

        report = self._copy(tmp_path, ground_one)
        with pytest.raises(bb.BlindBaselineError) as caught:
            self._freeze_copy(tmp_path, dn_bundle, report)
        message = str(caught.value)
        assert "grounding_scope: " in message
        assert "must declare which scope produced it" in message

    def test_the_control_reproduces_the_committed_identity(self, tmp_path, dn_bundle):
        """The hardened gate re-derives the bindings the committed freeze
        recorded: same report bytes, same hash, same copy name."""
        frozen = self._freeze_copy(tmp_path, dn_bundle, self._copy(tmp_path))
        committed = json.loads(DN_FREEZE.read_text(encoding="utf-8"))
        assert frozen.record["report_sha256"] == committed["report_sha256"]
        assert frozen.copy_path.name == committed["report_copy"]
        assert frozen.copy_path.read_bytes() == DN_REPORT.read_bytes()
        assert frozen.record["bindings"] == committed["bindings"]

    def test_the_committed_report_passes_every_check_by_name(self, dn_bundle):
        run = bb.run_baseline_checks(
            json.loads(DN_REPORT.read_text(encoding="utf-8")), dn_bundle, repo_root=REPO
        )
        assert run.failures == ()
        assert [name for name, _ in run.not_applicable] == ["grounding_scope"]
        assert run.passed == tuple(
            name for name in bb.BASELINE_CHECKS if name != "grounding_scope"
        )

    @pytest.mark.parametrize("mutate, check", AUDIT_PROBES)
    def test_each_reproduced_probe_is_refused_with_a_check_and_a_reason(
        self, tmp_path, dn_bundle, mutate, check
    ):
        report = self._copy(tmp_path, mutate)
        with pytest.raises(bb.BlindBaselineError) as caught:
            self._freeze_copy(tmp_path, dn_bundle, report)
        message = str(caught.value)
        assert f"{check}: " in message
        assert not (tmp_path / "baseline").exists()
