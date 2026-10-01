"""
The demo's candidate Part B and blind baseline: what is recorded, and what is blocked.

Ticket "Candidate Part B and the blind baseline" in ``plans/dev_graph_demo_tickets.md``.
Three of its four criteria are not met, and these tests pin why so none can be quietly
reported as done later.  Two unrelated blocks account for the first two:

1. **Phase 8 is frozen.**  BIODIV-01 is a lump-sum RIA.  ``received/`` holds no
   planner response, so ``gate_09`` fails, and CLAUDE.md §8.4 and §13.4 freeze every
   Phase 8 node.  There is therefore no Part B, and drafting one here — by the runner
   or by hand — is the violation the gate exists to prevent.
2. **The blind lane's document route cannot feed either shipped profile.**
   ``materialise_candidate`` writes one sub-section per passage and names it for the
   section; the RIA rubrics anchor on ``B.1.1`` to ``B.3.2`` and the MSCA-PF rubrics on
   ``1.1`` to ``3.2``.  The anchor map fails closed.  This criterion would fail with
   Part B in hand, which is why it is a finding (F1) and not a wait.

The fourth criterion asks the leakage guard about the package built around candidate
version 1.  The guard runs clean over all 6 blind packages the demo world holds, but
those hold no passage, claim or commitment item, so they cannot carry the leak it looks
for (F6).  Its box stays open.

What this module does deliver: the ESR intake record with availability
``not_applicable``, and the recorded Phase 8 block.

No runner phase is dispatched and no gate result is written: gate evaluation belongs to
the scheduler and gate results to the gate evaluator (§17.1.4, §17.6.3).  What runs is
the gate's own predicate functions, which are pure, and the harness lane, which is
out-of-band QA and never a runtime gate.  The F1 reproduction imports its document into
a copy of the synthetic fixture under ``tmp_path``, never into ``docs/``: a real import
would move the demo snapshot id that three Tier 4 records cite.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

import harness.blind_assessment as ba
from harness.evidence_pack import EvidencePackError
from harness.judge import Judge, JudgeConfig
from harness.provenance import ProvenanceLog
from harness.rubrics import load_profile_bundle
from runner.dag_scheduler import _HARD_BLOCK_GATE
from runner.dev_graph import build_snapshot, import_document, read_esr_intake
from runner.dev_graph.documents import DOCUMENTS_REL, read_document_records
from runner.dev_graph.packages import PACKAGES_REL, Package
from runner.dev_graph.policies import HISTORICAL_FEEDBACK_TAGS
from runner.gate_evaluator import HARD_BLOCK_GATE
from runner.leakage_scan import iter_scanned_files
from runner.predicates.file_predicates import dir_non_empty
from runner.run_context import PHASE_8_NODE_IDS

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "dev_graph_synthetic"

RECEIVED_REL = "docs/integrations/lump_sum_budget_planner/received/"
VALIDATION_REL = "docs/integrations/lump_sum_budget_planner/validation/"
MANIFEST_REL = ".claude/workflows/system_orchestration/manifest.compile.yaml"
PHASE_7_REL = "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate"
PHASE_8_REL = "docs/tier4_orchestration_state/phase_outputs/phase8_drafting_review"
TIER_5_REL = "docs/tier5_deliverables"

INTAKE_ID = "demo-biodiv-2027-part-b-v1"
DOCUMENT_ID = "DEMO-BIODIV-2027_part_b"
RIA_PROFILE_REL = "harness/profiles/ria_default.json"
MSCA_PROFILE_REL = "harness/profiles/msca_pf_default.json"

#: Ticket 8 pinned the demo snapshot.  Writing the intake must not move it.
DEMO_SNAPSHOT_ID = "sha256:93b18297a8703157e77e08d1a3c97abd240f752b63b711ca0b3037f6141bd836"

REPORT_REL = (
    "docs/tier4_orchestration_state/validation_reports/"
    "demo-candidate-blind-baseline_2026-10-01.json"
)
DECISION_REL = (
    "docs/tier4_orchestration_state/decision_log/"
    "demo-candidate-blind-baseline_2026-10-01.json"
)

FROZEN = "2026-10-01T00:00:00+00:00"
PASS_JSON = '{"passed": true, "score": 0.9, "rationale": "scripted pass"}'


def _json(rel: str) -> dict:
    return json.loads((REPO / rel).read_text(encoding="utf-8-sig"))


def _files(rel: str) -> list[Path]:
    """Every real file under *rel*; ``.gitkeep`` placeholders are not output."""
    base = REPO / rel
    if not base.is_dir():
        return []
    return [p for p in base.rglob("*") if p.is_file() and p.name != ".gitkeep"]


@pytest.fixture(scope="module")
def manifest() -> dict:
    return yaml.safe_load((REPO / MANIFEST_REL).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def demo_snapshot():
    return build_snapshot(REPO)


@pytest.fixture(scope="module")
def ria_bundle():
    return load_profile_bundle(RIA_PROFILE_REL, repo_root=REPO)


# ---------------------------------------------------------------------------
# 1. The Phase 8 block, from the gate's own predicates
# ---------------------------------------------------------------------------


class TestThePhase8BlockIsRecorded:
    """Criterion 1, second branch: the blocking gate is recorded."""

    def test_the_topic_is_lump_sum_so_the_response_is_the_operators_step(self):
        call = _json("docs/tier3_project_instantiation/call_binding/selected_call.json")
        assert call["budget_regime"] == "lump_sum"

    def test_no_planner_response_has_been_received(self):
        assert not dir_non_empty(RECEIVED_REL, repo_root=REPO).passed, (
            "A response has appeared in received/. Re-run this ticket: these tests pin "
            "the recorded blocking state, not a wish."
        )

    def test_no_validation_artifact_exists(self):
        assert not dir_non_empty(VALIDATION_REL, repo_root=REPO).passed

    def test_no_budget_gate_assessment_was_written(self):
        assert not (REPO / PHASE_7_REL / "budget_gate_assessment.json").exists()

    def test_phase_7_has_no_gate_result_while_phases_1_to_6_each_have_one(self):
        assert not (REPO / PHASE_7_REL / "gate_result.json").exists()
        earlier = sorted(
            p.parent.name
            for p in (REPO / "docs/tier4_orchestration_state/phase_outputs").rglob(
                "gate_result.json"
            )
        )
        assert len(earlier) == 6, earlier

    def test_the_hard_block_gate_is_still_the_budget_gate(self):
        assert _HARD_BLOCK_GATE == "gate_09_budget_consistency"
        assert HARD_BLOCK_GATE == _HARD_BLOCK_GATE, (
            "the scheduler and the gate evaluator name different hard-block gates"
        )

    def test_the_frozen_set_covers_every_phase_8_node(self, manifest):
        in_manifest = {
            n["node_id"]
            for n in manifest["node_registry"]
            if n.get("phase_number") == 8
        }
        assert in_manifest == set(PHASE_8_NODE_IDS)
        assert len(in_manifest) == 6

    def test_the_budget_gate_blocks_the_edge_into_phase_8(self, manifest):
        gate = next(
            g
            for g in manifest["gate_registry"]
            if g["gate_id"] == _HARD_BLOCK_GATE
        )
        assert gate["mandatory"] is True
        assert gate["bypass_prohibited"] is True
        assert gate["absent_artifacts_behavior"] == "blocking_gate_failure"
        assert "e07_to_08a" in gate["blocking_edges"]

    def test_phase_8_has_produced_nothing(self):
        assert _files(PHASE_8_REL) == []

    def test_tier_5_holds_nothing_but_placeholders(self):
        assert _files(TIER_5_REL) == []
        assert (REPO / TIER_5_REL / "proposal_sections" / ".gitkeep").is_file()


# ---------------------------------------------------------------------------
# 2. Criterion 2: there is no candidate version 1, and why
# ---------------------------------------------------------------------------


class TestNoCandidateVersionExists:
    def test_no_document_record_exists(self):
        assert read_document_records(REPO) == []
        assert not (REPO / DOCUMENTS_REL).exists()

    def test_the_demo_snapshot_holds_no_document_node(self, demo_snapshot):
        assert demo_snapshot.snapshot_id == DEMO_SNAPSHOT_ID
        assert [n for n in demo_snapshot.nodes if n["type"] == "artifact_version"] == []

    def test_resolving_the_part_b_document_is_refused(self, demo_snapshot):
        with pytest.raises(ba.BlindAssessmentError) as exc:
            ba.resolve_document(demo_snapshot, DOCUMENT_ID)
        assert "no document snapshot named" in str(exc.value)


# ---------------------------------------------------------------------------
# 3. The ESR intake record — the part of the ticket neither block reaches
# ---------------------------------------------------------------------------


class TestTheEsrIntakeRecord:
    def test_it_declares_availability_not_applicable(self):
        intake = read_esr_intake(REPO, INTAKE_ID)
        assert intake.esr_availability == "not_applicable"
        assert intake.prior_submission is False
        assert intake.esr_reference is None

    def test_it_permits_only_a_blind_assessment(self):
        assert read_esr_intake(REPO, INTAKE_ID).permitted_purpose == ba.BLIND_TASK_LABEL

    def test_it_pins_the_document_identity_the_import_must_use(self):
        assert read_esr_intake(REPO, INTAKE_ID).document_id == DOCUMENT_ID

    def test_it_binds_the_tier_3_call_id(self):
        call = _json("docs/tier3_project_instantiation/call_binding/selected_call.json")
        assert read_esr_intake(REPO, INTAKE_ID).call_id == call["call_id"]

    def test_the_submission_id_declares_an_absence_rather_than_inventing_one(self):
        """F3: the schema requires a submission_id for a document never submitted."""
        assert read_esr_intake(REPO, INTAKE_ID).submission_id == "NOT_SUBMITTED"

    def test_writing_it_did_not_move_the_demo_snapshot(self, demo_snapshot):
        assert demo_snapshot.snapshot_id == DEMO_SNAPSHOT_ID

    def test_an_esr_informed_purpose_would_be_refused_by_the_blind_lane(self):
        assert ba.TASK_LABELS == {ba.BLIND_TASK_LABEL, ba.ESR_INFORMED_TASK_LABEL}
        assert read_esr_intake(REPO, INTAKE_ID).permitted_purpose != (
            ba.ESR_INFORMED_TASK_LABEL
        )


# ---------------------------------------------------------------------------
# 4. Criterion 4: the leakage guard over the demo world's blind packages
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def stored_packages() -> list[Package]:
    """Every stored package, rebuilt from its two records.

    ``runner.dev_graph.packages`` exposes no reader for a written package —
    only ``build_package``, ``write_package`` and ``read_package_request`` —
    so the pair is reassembled here.
    """
    out = []
    for directory in sorted((REPO / PACKAGES_REL).iterdir()):
        pkg_manifest = json.loads(
            (directory / "manifest.json").read_text(encoding="utf-8-sig")
        )
        items = json.loads(
            (directory / "package.json").read_text(encoding="utf-8-sig")
        )["items"]
        out.append(Package(manifest=pkg_manifest, items=tuple(items)))
    return out


@pytest.fixture(scope="module")
def blind_packages(stored_packages) -> list[Package]:
    return [p for p in stored_packages if p.manifest.get("view") == ba.BLIND_VIEW]


class TestTheLeakageGuardIsCleanOnTheDemoWorld:
    def test_the_demo_world_holds_the_blind_packages_the_report_counts(
        self, stored_packages, blind_packages
    ):
        assert len(stored_packages) == 36
        assert len(blind_packages) == 6
        assert {p.manifest["task"] for p in blind_packages} == {"T1.1", "T3.1", "T4.1"}

    def test_every_blind_package_passes_the_guard(self, blind_packages):
        for package in blind_packages:
            ba.assert_no_leakage(package)

    def test_no_blind_item_carries_a_historical_feedback_tag(self, blind_packages):
        for package in blind_packages:
            for item in package.items:
                tags = (item.get("content") or {}).get("tags") or []
                assert not set(tags) & HISTORICAL_FEEDBACK_TAGS, item.get("id")

    def test_no_blind_item_is_of_a_forbidden_type(self, blind_packages):
        kinds = {i.get("type") for p in blind_packages for i in p.items}
        assert not kinds & ba.LEAKAGE_FORBIDDEN_TYPES

    def test_the_packages_cannot_carry_the_leak_the_guard_looks_for(
        self, blind_packages
    ):
        """F6: the clean pass is correct, and it is uninformative.

        A historical-feedback tag rides on a document's passages, claims and
        commitments.  The demo world has no document, so the packages hold
        none of those three types and no item in them could carry a tag.
        """
        counts: dict[str, int] = {}
        for package in blind_packages:
            for item in package.items:
                counts[item["type"]] = counts.get(item["type"], 0) + 1
        assert counts == {
            "task": 50,
            "participant": 22,
            "work_package": 6,
            "source": 4,
            "deliverable": 2,
        }
        for kind in ("passage", "claim", "commitment"):
            assert kind not in counts

    def test_there_is_no_document_whose_tags_could_leak(self):
        assert read_document_records(REPO) == []

    def test_the_guard_refuses_a_planted_item_so_a_pass_is_not_vacuous(
        self, blind_packages
    ):
        clean = blind_packages[0]
        planted = Package(
            manifest=clean.manifest,
            items=clean.items
            + (
                {
                    "id": "PLANTED",
                    "type": "passage",
                    "content": {"tags": sorted(HISTORICAL_FEEDBACK_TAGS)[:1]},
                },
            ),
        )
        with pytest.raises(ba.LeakageError) as exc:
            ba.assert_no_leakage(planted)
        assert "PLANTED" in str(exc.value)

    def test_the_guard_refuses_a_package_built_under_another_view(self, stored_packages):
        other = next(
            p for p in stored_packages if p.manifest.get("view") != ba.BLIND_VIEW
        )
        with pytest.raises(ba.LeakageError):
            ba.assert_no_leakage(other)


# ---------------------------------------------------------------------------
# 5. F1: the document route cannot feed either shipped profile
# ---------------------------------------------------------------------------

RIA_SECTION_TEXT = (
    "Objectives go beyond the state of the art and are measurable. The methodology is "
    "interdisciplinary, addresses the gender dimension and is FAIR. Pathways to the "
    "expected outcomes are quantified for each target group. Dissemination, "
    "exploitation and communication measures name stakeholders and open access. Work "
    "packages, tasks, deliverables and milestones carry person-months, risks and a "
    "Gantt critical path. The consortium partners hold roles, capabilities and "
    "infrastructure that complement each other."
)


def _ria_shaped_document(sections) -> dict:
    return {
        "document_id": "RIA_SHAPED_PART_B",
        "title": "RIA-shaped document, for the anchor check only",
        "sections": [
            {
                "section_id": sid,
                "title": sid,
                "content": RIA_SECTION_TEXT,
                "addresses": ["OBJ-1"],
            }
            for sid in sections
        ],
        "claims": [
            {
                "claim_id": "CL-1",
                "section_id": sections[0],
                "text": "Participant B holds the capability that Task three requires.",
                "evidence_strength": "source_grounded",
                "verified_span": {"source_id": "SRC-1", "start": 0, "end": 58},
                "approval": "approved",
            }
        ],
        "commitments": [],
    }


@pytest.fixture
def world(tmp_path: Path) -> Path:
    """A copy of the synthetic fixture.  Nothing here touches ``docs/``."""
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    return root


def _import_ria_shaped(world: Path, ria_bundle) -> str:
    sections = [sid for _c, sid in ba.required_sections(ria_bundle.profile)]
    rel = Path("docs/tier5_deliverables/candidates/ria_shaped.json")
    target = world / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_ria_shaped_document(sections), indent=2), encoding="utf-8"
    )
    import_document(world, rel)
    return "RIA_SHAPED_PART_B"


def _evidence(world: Path, ria_bundle, out_dir: Path):
    """Import the RIA-shaped document into *world*, then build its blind evidence."""
    return ba.build_blind_evidence(
        world,
        _import_ria_shaped(world, ria_bundle),
        profile_version=ria_bundle.version,
        out_dir=out_dir,
    )


def _stub_judge(tmp_path: Path) -> Judge:
    return Judge(
        JudgeConfig(model="fake-assessor", version="pin-f1"),
        backend=lambda messages: {"content": PASS_JSON},
        provenance_log=ProvenanceLog(tmp_path / "provenance.jsonl"),
        clock=lambda: FROZEN,
    )


def _anchors_and_sections(bundle) -> tuple[set[str], set[str]]:
    """What the rubrics anchor on, and what the profile calls its sections."""
    anchors = {
        a for r in bundle.rubric_set.rubrics for a in r.anchor_sub_section_ids
    }
    sections = {sid for _c, sid in ba.required_sections(bundle.profile)}
    return anchors, sections


class TestTheDocumentRouteCannotFeedTheRiaProfile:
    """F1.  The guarded route builds its evidence, then the anchor map refuses it."""

    def test_the_ria_rubrics_anchor_below_the_section(self, ria_bundle):
        anchors, sections = _anchors_and_sections(ria_bundle)
        assert anchors == {"B.1.1", "B.1.2", "B.2.1", "B.2.2", "B.3.1", "B.3.2"}
        assert not anchors & sections

    def test_the_msca_pf_profile_has_the_same_mismatch(self):
        anchors, sections = _anchors_and_sections(
            load_profile_bundle(MSCA_PROFILE_REL, repo_root=REPO)
        )
        assert anchors == {"1.1", "1.2", "1.3", "1.4", "2.1", "2.2", "2.3", "3.1", "3.2"}
        assert not anchors & sections

    def test_the_route_materialises_one_sub_section_named_for_its_section(
        self, world, ria_bundle, tmp_path
    ):
        evidence = _evidence(world, ria_bundle, tmp_path / "out")
        for path in sorted(evidence.candidate_dir.glob("*.json")):
            artifact = json.loads(path.read_text(encoding="utf-8"))
            ids = [s["sub_section_id"] for s in artifact["sub_sections"]]
            assert ids == [artifact["section_id"]]

    def test_assessment_fails_closed_on_the_missing_anchor(
        self, world, ria_bundle, tmp_path
    ):
        evidence = _evidence(world, ria_bundle, tmp_path / "out")
        with pytest.raises(EvidencePackError) as exc:
            ba.assess_candidate(
                _stub_judge(tmp_path),
                ria_bundle,
                evidence=evidence,
                clock=lambda: FROZEN,
            )
        message = str(exc.value)
        assert "B.1.1" in message
        assert "fail closed" in message

    def test_the_directory_route_cannot_stamp_the_intake_f2(self, tmp_path, ria_bundle):
        """F2: the route that could grade is the route that refuses an intake."""
        intake = read_esr_intake(REPO, INTAKE_ID)
        with pytest.raises(ba.BlindAssessmentError) as exc:
            ba.assess_candidate(
                _stub_judge(tmp_path),
                ria_bundle,
                tmp_path / "nowhere",
                intake=intake,
                clock=lambda: FROZEN,
            )
        assert "assess through the document route to stamp an intake" in str(exc.value)

    def test_no_document_was_written_into_the_repository(self):
        assert read_document_records(REPO) == []


class TestTheImportRouteWorks:
    """The import machinery is sound; only the Part B it would import is missing."""

    def test_an_imported_document_lands_under_state_imported(self, world, ria_bundle):
        _import_ria_shaped(world, ria_bundle)
        records = read_document_records(world)
        assert [rec["state"] for _rel, rec in records] == ["imported"]

    def test_re_importing_the_same_content_is_a_no_op(self, world, ria_bundle):
        _import_ria_shaped(world, ria_bundle)
        before = {
            rel: json.dumps(rec, sort_keys=True) for rel, rec in read_document_records(world)
        }
        _import_ria_shaped(world, ria_bundle)
        after = {
            rel: json.dumps(rec, sort_keys=True) for rel, rec in read_document_records(world)
        }
        assert before == after

    def test_the_materialised_sections_carry_their_passage_and_span(
        self, world, ria_bundle, tmp_path
    ):
        evidence = _evidence(world, ria_bundle, tmp_path / "out")
        artifacts = {
            p.stem: json.loads(p.read_text(encoding="utf-8"))
            for p in evidence.candidate_dir.glob("*.json")
        }
        assert set(artifacts) == {
            sid for _c, sid in ba.required_sections(ria_bundle.profile)
        }
        for artifact in artifacts.values():
            assert artifact["passage"]["id"]
            assert artifact["passage"]["version"].startswith("sha256:")
        ledgers = [
            claim
            for artifact in artifacts.values()
            for claim in artifact["validation_status"]["claim_statuses"]
        ]
        assert [c["claim_id"] for c in ledgers] == ["CL-1"]
        assert ledgers[0]["source_ref"], "a verified span must reach the ledger"

    def test_the_materialisation_is_byte_equal_on_a_second_build(
        self, world, ria_bundle, tmp_path
    ):
        first = _evidence(world, ria_bundle, tmp_path / "a")
        bytes_first = {p.name: p.read_bytes() for p in first.candidate_dir.iterdir()}
        second = _evidence(world, ria_bundle, tmp_path / "b")
        assert first.package.package_id == second.package.package_id
        assert bytes_first == {p.name: p.read_bytes() for p in second.candidate_dir.iterdir()}


# ---------------------------------------------------------------------------
# 6. The record itself
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def report() -> dict:
    return _json(REPORT_REL)


@pytest.fixture(scope="module")
def decision() -> dict:
    return _json(DECISION_REL)


class TestTheRecord:
    def test_both_records_exist_and_point_at_each_other(self, report, decision):
        assert report["report_id"] == "demo-candidate-blind-baseline_2026-10-01"
        assert decision["validation_report"] == REPORT_REL

    def test_the_four_criteria_carry_the_same_disposition_in_both(self, report, decision):
        assert [c["criterion"] for c in report["acceptance_criteria"]] == [
            c["criterion"] for c in decision["acceptance_criteria"]
        ]
        assert [c["disposition"] for c in report["acceptance_criteria"]] == [
            c["disposition"] for c in decision["acceptance_criteria"]
        ]

    def test_three_criteria_are_recorded_as_not_met(self, report):
        not_met = [
            c for c in report["acceptance_criteria"] if c["disposition"].startswith("not met")
        ]
        assert len(not_met) == 3

    def test_the_open_ticket_boxes_are_the_criteria_recorded_as_not_met(self, report):
        """The ticket's checkboxes and the report's dispositions must agree."""
        lines = (REPO / "plans/dev_graph_demo_tickets.md").read_text(
            encoding="utf-8"
        ).splitlines()
        boxes = {
            line.split("] ", 1)[1].strip(): line.strip().startswith("- [x]")
            for line in lines
            if line.strip().startswith(("- [ ]", "- [x]")) and "] " in line
        }
        for criterion in report["acceptance_criteria"]:
            checked = boxes[criterion["criterion"]]
            assert checked is not criterion["disposition"].startswith("not met"), (
                f"ticket box and report disposition disagree on: {criterion['criterion']}"
            )

    def test_no_criterion_is_claimed_as_plain_met(self, report):
        assert all(
            c["disposition"] != "met" for c in report["acceptance_criteria"]
        ), "a qualified disposition must not be reported as a plain pass"

    def test_every_criterion_carries_its_evidence(self, report):
        assert all(c.get("evidence") for c in report["acceptance_criteria"])

    def test_every_finding_carries_a_disposition(self, report, decision):
        assert {f["id"] for f in report["findings"]} == {
            f["id"] for f in decision["findings"]
        }
        assert all(f.get("disposition") for f in report["findings"])

    def test_every_decision_carries_its_reasoning_and_where_it_landed(self, decision):
        for entry in decision["decisions"]:
            assert entry.get("reasoning")
            assert entry.get("recorded_in")

    def test_the_four_status_categories_are_all_answered(self, report):
        assert set(report["status_summary"]) == {
            "Confirmed",
            "Inferred",
            "Assumed",
            "Unresolved",
        }
        assert all(report["status_summary"][k] for k in report["status_summary"])

    def test_every_budget_figure_is_unresolved(self, report):
        assert any(
            "budget figure" in item for item in report["status_summary"]["Unresolved"]
        )

    def test_the_report_counts_match_the_artifacts(
        self, report, stored_packages, blind_packages
    ):
        evidence = _criterion_4_evidence(report)
        assert f"{len(stored_packages)} evidence packages" in evidence
        assert f"{len(blind_packages)} of them" in evidence

    def test_the_intake_block_matches_the_record_on_disk(self, report):
        intake = read_esr_intake(REPO, INTAKE_ID)
        block = report["the_esr_intake"]
        assert block["intake_id"] == intake.intake_id
        assert block["document_id"] == intake.document_id
        assert block["esr_availability"] == intake.esr_availability
        assert block["permitted_purpose"] == intake.permitted_purpose

    def test_the_outstanding_human_step_is_named(self, decision):
        assert "Lump Sum Budget Planner" in decision["what_is_outstanding_for_the_operator"]

    def test_the_defects_are_offered_as_milestone_2_candidates(self, decision):
        assert len(decision["milestone_2_candidates"]) >= 2


def _criterion_4_evidence(report) -> str:
    """The evidence the report gives for the leakage-guard criterion."""
    return next(
        c["evidence"]
        for c in report["acceptance_criteria"]
        if c["criterion"].startswith("The leakage guard")
    )


class TestTheReportsNumbersAreTheArtifactsOwn:
    """Every number the report states is re-derived here, so neither can drift."""

    def test_the_snapshot_id_it_cites_is_the_one_the_builder_produces(
        self, report, demo_snapshot
    ):
        cited = report["the_esr_intake"]["why_it_is_written_now"]
        assert demo_snapshot.snapshot_id in cited
        assert demo_snapshot.snapshot_id == DEMO_SNAPSHOT_ID

    def test_the_node_count_and_type_count_are_the_snapshots_own(
        self, report, demo_snapshot
    ):
        evidence = next(
            c["evidence"]
            for c in report["acceptance_criteria"]
            if c["disposition"] == "not met, blocked upstream"
        )
        types = {n["type"] for n in demo_snapshot.nodes}
        assert f"{len(demo_snapshot.nodes)} nodes of {len(types)} types" in evidence

    def test_the_blind_package_tasks_are_the_stored_packages_own(
        self, report, blind_packages
    ):
        evidence = _criterion_4_evidence(report)
        tasks = sorted({p.manifest["task"] for p in blind_packages})
        assert ", ".join(tasks[:-1]) + f" and {tasks[-1]}" in evidence

    def test_the_policy_forbidden_exclusion_it_names_is_the_packages_own(
        self, report, blind_packages
    ):
        evidence = _criterion_4_evidence(report)
        forbidden = {
            (e["id"], e["detail"])
            for p in blind_packages
            for e in p.manifest.get("exclusions", [])
            if e.get("reason") == "policy_forbidden"
        }
        assert forbidden == {("MS6", "traversal_not_permitted:validated_by")}
        for node_id, detail in forbidden:
            assert node_id in evidence
            assert detail in evidence

    def test_the_default_package_budget_it_names_is_the_lanes_own(self, report):
        f5 = next(f for f in report["findings"] if f["id"] == "F5")
        assert str(ba.DEFAULT_PACKAGE_BUDGET) in f5["finding"]

    def test_the_leakage_scan_file_count_is_re_derivable(self, report):
        scanned = len(iter_scanned_files(REPO))
        stated = next(
            line
            for line in report["what_was_checked_and_how"]
            if line.startswith("Anonymity:")
        )
        assert f"over {scanned} files" in stated, (
            f"the report states a file count the scan no longer produces ({scanned}); "
            "a Tier 4 file was added or removed after the report was written"
        )
