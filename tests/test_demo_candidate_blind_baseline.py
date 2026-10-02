"""
The demo's candidate Part B and blind baseline: what is recorded, and what is left.

Ticket "Candidate Part B and the blind baseline" in ``plans/dev_graph_demo_tickets.md``.
All four criteria are met and these tests pin how, so none can later be quietly un-met.

**Criterion 1 — met.** The operator dispatched n08a to n08f one node at a time and every
Phase 8 node released. ``gate_12_constitutional_compliance`` passed 8 of 8 deterministic
predicates and 6 of 6 semantic ones, the first gate on this branch with semantic
predicates bound.

**Criterion 2 — met.** ``tools/build_part_b_candidate.py`` converted the three section
artifacts and ``import_document`` wrote candidate version 1. Two rules had to be found
first, because no fixture had exercised them (F7, F8): ``assumed`` has no
``evidence_strength``, so such a claim carries ``unconfirmed`` plus a declared status;
and a Tier 5 ``claim_id`` is a declaration key, not an occurrence id, so a claim's
identity is ``(section_id, claim_id)``.

**Criterion 4 — met, over the package the criterion names.** F6 observed that a clean
leakage pass over the task-seeded packages is uninformative, because a historical
feedback tag rides on passages, claims and commitments and those packages hold none.
The candidate package holds 3 passages and 147 claims, so it could carry the leak. It
does not.

**Criterion 3 — met.** The operator ran the assessor over the Max subscription and the
report binds the candidate hash, the profile version and the pin on its header and on
each of its six cells, labelled scope ``complete``. The criterion asks what the report
binds and how it is labelled; it never asked the candidate to grade well, and four of
the six cells fail. The single systematic reason they fail is F12, which is the thing
this lane exists to find: every claim reaches the assessor with an empty ``source_ref``,
because the converter does not carry the Tier 5 field and ``materialise_candidate``
reads only the ``verified_span`` the converter deliberately omits. No deterministic gate
caught it — each component passes its own contract — and the blind assessor named it in
all six cells unprompted. ``TestTheAssessorsReport`` pins both halves: the bindings that
close the criterion, and the blank field that F12 is open against, so the day F12 is
fixed these tests fail and say so.

Two earlier blocks are now history, kept because each was a finding rather than a wait.
``gate_09`` froze every Phase 8 node until ticket A placed a fictional budget response
under an operator override and the Phase 7 dispatch passed it 9 of 9. And F1: the
document route could feed neither shipped profile, because ``materialise_candidate``
synthesised one sub-section named for its section while the RIA rubrics anchor on
``B.1.1`` to ``B.3.2`` and the MSCA-PF rubrics on ``1.1`` to ``3.2``. Ticket B closed it
— a section declares its sub-sections and the materialiser emits them — and
``tests/harness/test_blind_document_subsections.py`` owns the fix. What remains here is
the half that was never a defect: a document declaring no sub-sections still fails
closed.

F9 is pinned here too, and it is the newest: the evidence pack's budget ceiling was
derived from one provider's free-tier rate limit, which truncated all six cells and so
predetermined every grade. The ceiling now belongs to the assessor's transport.

No runner phase is dispatched and no gate result is written: gate evaluation belongs to
the scheduler and gate results to the gate evaluator (§17.1.4, §17.6.3). What runs is
the gate's own predicate functions, which are pure, and the harness lane, which is
out-of-band QA and never a runtime gate. The F1 reproduction still imports its document
into a copy of the synthetic fixture under ``tmp_path``; the one record under ``docs/``
is the real Part B, imported deliberately, and it moved the demo snapshot id that three
Tier 4 records cite — so those records were rewritten with it.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

import harness.blind_assessment as ba
from harness.evidence_pack import EvidencePackError, pack_forbids_clean_pass
from harness.judge import Judge, JudgeConfig
from harness.provenance import ProvenanceLog
from harness.rubrics import load_profile_bundle
from runner.dag_scheduler import _HARD_BLOCK_GATE
from runner.dev_graph import build_snapshot, import_document, read_esr_intake
from runner.dev_graph.changes import load_snapshot
from runner.dev_graph.documents import DOCUMENTS_REL, read_document_records
from runner.dev_graph.packages import PACKAGES_REL, Package
from runner.dev_graph.policies import HISTORICAL_FEEDBACK_TAGS
from runner.dev_graph.scenarios import materialise_sandbox, read_enactment, versions_before
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
RUN_MANIFEST_REL = ".claude/runs/import uuid; print(uuid.uuid4())/run_manifest.json"
SUMMARY_REL = "docs/tier4_orchestration_state/dev_graph/demo_snapshot_summary.json"
MSCA_PROFILE_REL = "harness/profiles/msca_pf_default.json"

#: The demo snapshot after candidate version 1 was imported.  Ticket 8 pinned
#: the Tier-3-only snapshot at 116 nodes; importing Part B added one
#: artifact_version, three passages and 147 claims and moved the id.  Writing
#: the intake still must not move it, which is what the intake test checks.
#: Subticket B then enacted a change through the change recorder and moved the
#: live id once more. This is the snapshot the blind baseline bound; it is
#: archived under dev_graph/snapshots by that enactment and read from there.
DEMO_SNAPSHOT_ID = "sha256:706fe54fd85ebda600d70b02c80ce6ca1e12e2697b373a45cf730ef03504e389"

#: The scenario whose enactment moved the live snapshot off DEMO_SNAPSHOT_ID.
ENACTED_SCENARIO = "deliverable_month_moves"

#: The document node candidate version 1 landed as.
DOCUMENT_NODE_ID = "DEMO-BIODIV-2027_part_b@1101b2a653c543a4"

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
    """The snapshot the blind baseline bound, read from the archive.

    The live build has moved on by one enacted change; what this report's
    numbers must match is the snapshot they were taken over.
    """
    return load_snapshot(REPO, DEMO_SNAPSHOT_ID)


def _baseline_world(out: Path) -> Path:
    """A sandbox at DEMO_SNAPSHOT_ID: the live inputs with the enacted records
    put back to the versions the change recorder archived."""
    enactment = read_enactment(REPO, ENACTED_SCENARIO)
    if enactment is None:
        return REPO
    return materialise_sandbox(
        REPO,
        out / "world",
        record_versions=versions_before(enactment),
        expected_snapshot_id=DEMO_SNAPSHOT_ID,
    ).root


@pytest.fixture(scope="module")
def ria_bundle():
    return load_profile_bundle(RIA_PROFILE_REL, repo_root=REPO)


# ---------------------------------------------------------------------------
# 1. The Phase 8 block, from the gate's own predicates
# ---------------------------------------------------------------------------


class TestThePhase8BlockIsLifted:
    """Criterion 1, now on its first branch rather than its second.

    The ticket's criterion reads "Phase 8 reaches released, or its blocking gate
    is recorded".  It was satisfied by the second branch twice over: first with
    ``received/`` empty, then with the node failing at ``agent_body``.  On
    1 October the re-dispatch released n07 and ``gate_09`` recorded a pass, so
    the six Phase 8 nodes sit at ``pending`` and three of them dispatch.

    Phase 8 has still written nothing, which is why criteria 2 to 4 stay open.
    What changed is that nothing constitutional now blocks them.
    """

    def test_the_topic_is_lump_sum_so_the_response_is_the_operators_step(self):
        call = _json("docs/tier3_project_instantiation/call_binding/selected_call.json")
        assert call["budget_regime"] == "lump_sum"

    def test_the_only_response_is_the_fictional_one_authored_under_override(self):
        """Ticket A placed it there. No planner produced it, and none exists.

        When this ticket ran, ``received/`` was empty and that was the whole of the
        block.  Ticket A in ``plans/tickets_budget_and_blind_lane.md`` then authored
        one fictional response under an operator override of six constitutional clauses.
        The block below is unchanged, because the gate reads more than this directory.
        """
        assert dir_non_empty(RECEIVED_REL, repo_root=REPO).passed
        responses = sorted(
            p.name
            for p in (REPO / RECEIVED_REL).iterdir()
            if p.is_file() and p.name != ".gitkeep"
        )
        assert responses == ["budget_response_FICTIONAL_demo_2026-10-01.json"]
        response = _json(RECEIVED_REL + responses[0])
        assert response["figures_are_fictional"] is True
        assert response["produced_by_external_planner"] is False

    def test_the_validation_artifact_exists(self):
        assert dir_non_empty(VALIDATION_REL, repo_root=REPO).passed

    def test_the_dispatched_phase_7_released(self):
        """Second dispatch, after commit ``67794f3`` fixed the output contract.

        The first dispatch blocked at exit: the skill never wrote the validation
        artifact it declared, so the exit gate was never evaluated and every
        Phase 8 node took ``hard_block_upstream``.  Both artifacts now exist and
        the gate evaluated.
        """
        assessment = _json(
            "docs/tier4_orchestration_state/phase_outputs/phase7_budget_gate/"
            "budget_gate_assessment.json"
        )
        assert assessment["gate_pass_declaration"] == "pass"
        assert dir_non_empty(VALIDATION_REL, repo_root=REPO).passed

    def test_every_phase_through_7_now_has_a_gate_result(self):
        """Seven, where this ticket recorded six and a frozen node."""
        assert (REPO / PHASE_7_REL / "gate_result.json").exists()
        results = sorted(
            p.parent.name
            for p in (REPO / "docs/tier4_orchestration_state/phase_outputs").rglob(
                "gate_result.json"
            )
        )
        assert len(results) == 7, results
        assert "phase7_budget_gate" in results

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

    def test_every_phase_8_node_released(self):
        """The operator dispatched n08a to n08f one at a time, fixing each
        exit gate offline before the next."""
        states = _json(RUN_MANIFEST_REL)["node_states"]
        assert {states[node] for node in PHASE_8_NODE_IDS} == {"released"}

    def test_the_terminal_gate_passed_on_both_halves(self):
        """gate_12 is the first gate on this branch with semantic predicates
        bound, so its six Claude judges ran where no earlier gate had any."""
        gate = _json(f"{PHASE_8_REL}/gate_12_result.json")
        assert gate["status"] == "pass"
        assert gate["deterministic_predicates"]["failed"] == []
        assert gate["semantic_predicates"]["failed"] == []
        assert gate["skipped_semantic"] is False
        assert len(gate["deterministic_predicates"]["passed"]) == 8
        assert len(gate["semantic_predicates"]["passed"]) == 6

    def test_tier_5_holds_the_part_b_phase_8_wrote(self):
        names = {path.name for path in _files(TIER_5_REL)}
        assert {
            "excellence_section.json",
            "impact_section.json",
            "implementation_section.json",
        } <= names


# ---------------------------------------------------------------------------
# 2. Criterion 2: candidate version 1, imported with its passages spanned
# ---------------------------------------------------------------------------


class TestCandidateVersionOneExists:
    def test_one_document_record_exists_and_its_state_is_imported(self):
        records = read_document_records(REPO)
        assert len(records) == 1
        _rel, record = records[0]
        assert record["document_id"] == DOCUMENT_ID
        assert record["state"] == "imported"

    def test_the_demo_snapshot_holds_the_document_node(self, demo_snapshot):
        assert demo_snapshot.snapshot_id == DEMO_SNAPSHOT_ID
        versions = [
            n for n in demo_snapshot.nodes if n["type"] == "artifact_version"
        ]
        assert [n["id"] for n in versions] == [DOCUMENT_NODE_ID]

    def test_resolving_the_part_b_document_succeeds(self, demo_snapshot):
        node = ba.resolve_document(demo_snapshot, DOCUMENT_ID)
        assert node["id"] == DOCUMENT_NODE_ID

    def test_every_passage_is_linked_by_span(self, demo_snapshot):
        """Criterion 2's own words. A passage without a span would be linked
        by title, and a title is not a position in the rendered document."""
        passages = [n for n in demo_snapshot.nodes if n["type"] == "passage"]
        assert len(passages) == 3
        for passage in passages:
            span = passage["content"]["span"]
            assert span["end"] > span["start"] >= 0

    def test_the_declared_sub_sections_are_the_rubrics_anchors(
        self, demo_snapshot, ria_bundle
    ):
        """Carried verbatim from Phase 8. A renumbered one would break grading
        silently, because the anchor map fails closed on an absent anchor."""
        declared = {
            str(sub["sub_section_id"])
            for n in demo_snapshot.nodes
            if n["type"] == "passage"
            for sub in n["content"].get("sub_sections") or []
        }
        anchors = {
            anchor
            for rubric in ria_bundle.rubric_set.rubrics
            for anchor in rubric.anchor_sub_section_ids
        }
        assert anchors
        assert anchors <= declared


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
        """An intake is not a graph record. The snapshot id did move since
        ticket 8, and candidate version 1 moved it, not this record."""
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
        package = Package(manifest=pkg_manifest, items=tuple(items))
        object.__setattr__(package, "directory_name", directory.name)
        out.append(package)
    return out


@pytest.fixture(scope="module")
def live_packages(stored_packages) -> list[Package]:
    """The packages the current snapshot's build wrote.

    ``tools/build_demo_dev_graph.py`` writes content-addressed packages and
    never removes the previous generation, so the directory listing holds more
    than one snapshot's worth (F8). The builder's own summary names the live
    set, so that is what is read here rather than the listing.
    """
    summary = _json(SUMMARY_REL)
    live = {Path(entry["path"]).name for entry in summary["packages"]}
    return [p for p in stored_packages if p.directory_name in live]


@pytest.fixture(scope="module")
def blind_packages(live_packages) -> list[Package]:
    return [p for p in live_packages if p.manifest.get("view") == ba.BLIND_VIEW]


@pytest.fixture(scope="module")
def candidate_sections(tmp_path_factory):
    """The materialised candidate's section artifacts, kept on disk.

    ``candidate_package`` discards its temporary directory; the pack-ceiling
    tests need the files themselves, so this fixture holds them for the module.
    """
    out = tmp_path_factory.mktemp("candidate_v1")
    evidence = ba.build_blind_evidence(
        _baseline_world(out),
        DOCUMENT_ID,
        profile_version=load_profile_bundle(RIA_PROFILE_REL, repo_root=REPO).version,
        out_dir=out / "evidence",
    )
    candidate = ba.load_candidate(
        evidence.candidate_dir,
        load_profile_bundle(RIA_PROFILE_REL, repo_root=REPO).profile,
    )
    return candidate


class TestThePackCeilingBelongsToTheTransport:
    """F9: a Groq rate limit was deciding how much of the Part B is assessable.

    ``MAX_PACK_TOKEN_BUDGET`` is ``GROQ_TPM_LIMIT - 2048 - 900``.  Under it every
    one of the six cells is truncated, and the rubric system prompt instructs the
    assessor not to return ``passed: true`` on a truncated pack — so the whole
    report would have been a predetermined fail describing the cap rather than
    the proposal.  The ceiling is now the assessor transport's to declare, and a
    transport with no per-minute token cap declares none.
    """

    @staticmethod
    def _cells(bundle, candidate):
        return [
            (rubric, candidate.sections[section_id])
            for rubric in bundle.rubric_set.rubrics
            for section_id in bundle.profile.section_ids_for(rubric.criterion_id)
            if section_id in candidate.sections
        ]

    def test_every_cell_is_truncated_under_the_providers_cap(
        self, ria_bundle, candidate_sections
    ):
        from harness.evidence_pack import DEFAULT_PACK_TOKEN_BUDGET, PACK_COMPLETE
        from harness.rubrics import build_pack_for

        cells = self._cells(ria_bundle, candidate_sections)
        assert len(cells) == 6
        for rubric, path in cells:
            pack = build_pack_for(rubric, path, token_budget=DEFAULT_PACK_TOKEN_BUDGET)
            assert pack.status != PACK_COMPLETE, rubric.expectation_key

    def test_every_cell_completes_once_the_ceiling_is_the_transports(
        self, ria_bundle, candidate_sections
    ):
        from harness.evidence_pack import (
            PACK_COMPLETE,
            UNCAPPED_DEFAULT_PACK_TOKEN_BUDGET,
        )
        from harness.rubrics import build_pack_for

        for rubric, path in self._cells(ria_bundle, candidate_sections):
            pack = build_pack_for(
                rubric,
                path,
                token_budget=UNCAPPED_DEFAULT_PACK_TOKEN_BUDGET,
                max_token_budget=None,
            )
            assert pack.status == PACK_COMPLETE, rubric.expectation_key
            assert not pack_forbids_clean_pass(pack)

    def test_the_capped_transport_is_still_capped(self, ria_bundle, candidate_sections):
        """Lifting it for one transport must not lift it for the other: the Groq
        lane still cannot be handed a budget its TPM ceiling cannot carry."""
        from harness.evidence_pack import MAX_PACK_TOKEN_BUDGET
        from harness.rubrics import build_pack_for

        rubric, path = self._cells(ria_bundle, candidate_sections)[0]
        with pytest.raises(EvidencePackError, match="TPM"):
            build_pack_for(rubric, path, token_budget=MAX_PACK_TOKEN_BUDGET + 1)


@pytest.fixture(scope="module")
def candidate_package():
    """The package criterion 4 names: the one built around candidate v1."""
    import tempfile

    with tempfile.TemporaryDirectory() as out:
        evidence = ba.build_blind_evidence(
            _baseline_world(Path(out)),
            DOCUMENT_ID,
            profile_version=load_profile_bundle(
                RIA_PROFILE_REL, repo_root=REPO
            ).version,
            out_dir=Path(out) / "evidence",
        )
        return evidence.package


class TestTheLeakageGuardIsCleanOnTheDemoWorld:
    def test_the_live_packages_are_the_summarys_and_the_rest_are_history(
        self, stored_packages, live_packages, blind_packages
    ):
        """F8: the directory listing holds more than one generation.

        The 1 October evidence counted 36 directories and 6 blind packages.
        18 of those directories, 3 of them blind, belonged to a snapshot that
        no longer exists.
        """
        assert len(live_packages) == 18
        assert len(blind_packages) == 3
        assert {p.manifest["task"] for p in blind_packages} == {"T1.1", "T3.1", "T4.1"}
        assert len(stored_packages) > len(live_packages)
        # The live set binds the live snapshot, which subticket B's enactment
        # moved off the baseline's; the baseline's own generation is history.
        live = build_snapshot(REPO).snapshot_id
        for package in live_packages:
            assert package.manifest["snapshot_id"] == live
        assert any(p.manifest["snapshot_id"] == DEMO_SNAPSHOT_ID for p in stored_packages)

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

    def test_the_task_packages_still_cannot_carry_the_leak(self, blind_packages):
        """F6, for the task-seeded packages: the clean pass is uninformative.

        A historical-feedback tag rides on a document's passages, claims and
        commitments.  These packages are seeded on a task, so they hold none
        of those three types and no item in them could carry a tag.  Criterion
        4 is answered by the candidate package below, not by these.
        """
        counts: dict[str, int] = {}
        for package in blind_packages:
            for item in package.items:
                counts[item["type"]] = counts.get(item["type"], 0) + 1
        assert counts
        for kind in ("passage", "claim", "commitment"):
            assert kind not in counts

    def test_the_candidate_package_can_carry_it_and_does_not(self, candidate_package):
        """Criterion 4, over the package it names. This is the pass F6 said
        the earlier one was not."""
        counts: dict[str, int] = {}
        for item in candidate_package.items:
            counts[item["type"]] = counts.get(item["type"], 0) + 1
        assert counts["passage"] == 3
        assert counts["claim"] == 147
        assert sum(counts.values()) == 151
        ba.assert_no_leakage(candidate_package)
        for item in candidate_package.items:
            tags = (item.get("content") or {}).get("tags") or []
            assert not set(tags) & HISTORICAL_FEEDBACK_TAGS, item.get("id")

    def test_the_one_document_carries_no_tag_to_leak(self):
        """An untagged candidate carries no ``tags`` key anywhere, so nothing
        derived from it can carry one either."""
        records = read_document_records(REPO)
        assert len(records) == 1
        assert "tags" not in records[0][1]

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
    """F1, now **fixed** by ticket B — and these tests say what is left.

    When this ticket ran, the dev-graph document route could feed no shipped profile:
    ``materialise_candidate`` synthesised one sub-section named for its section, and the
    anchor map refused it.  Ticket B gave a section an optional ``sub_sections`` list,
    which the builder carries onto the passage and the materialiser emits.

    What this class still pins is the half of F1 that was never a defect.  A document
    that declares **no** sub-section still cannot feed an anchored profile, and must
    still fail closed rather than grade on a vacuous anchor.  The RIA-shaped document
    below declares none, so it is exactly that case.  The positive case — a document
    that does declare them, grading under the real RIA and MSCA-PF profiles — lives in
    ``tests/harness/test_blind_document_subsections.py``.
    """

    def test_a_declaring_document_now_grades_under_the_real_ria_profile(
        self, world, ria_bundle, tmp_path
    ):
        """F1 inverted: the case that raised ``EvidencePackError`` now returns a report."""
        anchors = sorted(
            a for r in ria_bundle.rubric_set.rubrics for a in r.anchor_sub_section_ids
        )
        document = _ria_shaped_document(
            [sid for _c, sid in ba.required_sections(ria_bundle.profile)]
        )
        for section in document["sections"]:
            section["sub_sections"] = [
                {"sub_section_id": a, "title": a, "content": RIA_SECTION_TEXT}
                for a in anchors
            ]
        rel = Path("docs/tier5_deliverables/candidates/declaring.json")
        (world / rel).parent.mkdir(parents=True, exist_ok=True)
        (world / rel).write_text(json.dumps(document, indent=2), encoding="utf-8")
        import_document(world, rel)
        evidence = ba.build_blind_evidence(
            world,
            document["document_id"],
            profile_version=ria_bundle.version,
            out_dir=tmp_path / "out",
        )
        report = ba.assess_candidate(
            _stub_judge(tmp_path), ria_bundle, evidence=evidence, clock=lambda: FROZEN
        )
        assert report.scope in {"complete", "partial"}
        assert report.candidate_hash.startswith("sha256:")

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

    def test_a_document_declaring_none_falls_back_to_one_named_for_its_section(
        self, world, ria_bundle, tmp_path
    ):
        evidence = _evidence(world, ria_bundle, tmp_path / "out")
        for path in sorted(evidence.candidate_dir.glob("*.json")):
            artifact = json.loads(path.read_text(encoding="utf-8"))
            ids = [s["sub_section_id"] for s in artifact["sub_sections"]]
            assert ids == [artifact["section_id"]]

    def test_a_document_declaring_none_still_fails_closed_on_the_anchor(
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

    def test_the_only_document_in_the_repository_is_candidate_version_1(self):
        """The F1 reproduction still imports into ``tmp_path``. The one record
        under ``docs/`` is the real Part B, imported deliberately."""
        records = read_document_records(REPO)
        assert [rec["document_id"] for _rel, rec in records] == [DOCUMENT_ID]


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

    def test_every_criterion_is_recorded_as_met(self, report):
        """All four closed on 2 October, the last of them when the operator ran
        the assessor over the subscription transport.  Four of the six graded
        cells fail, which this criterion never asked about: it asks what the
        report binds and how it is labelled."""
        not_met = [
            c for c in report["acceptance_criteria"] if c["disposition"].startswith("not met")
        ]
        assert not_met == []
        assert len(report["acceptance_criteria"]) == 4

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
        self, report, candidate_package
    ):
        evidence = _criterion_4_evidence(report)
        assert candidate_package.package_id in evidence
        assert f"{len(candidate_package.items)} items" in evidence

    def test_f8_states_the_directory_count_on_disk_today(
        self, report, stored_packages, live_packages
    ):
        """Criterion 4's evidence states the 1 October counts, because that is
        the reading it corrects. F8 states today's, and both are re-derived
        rather than carried forward."""
        f8 = next(f for f in report["findings"] if f["id"] == "F8")
        assert (
            f"{len(stored_packages)} directories now hold "
            f"{len(live_packages)} current packages" in f8["finding"]
        )

    def test_the_intake_block_matches_the_record_on_disk(self, report):
        intake = read_esr_intake(REPO, INTAKE_ID)
        block = report["the_esr_intake"]
        assert block["intake_id"] == intake.intake_id
        assert block["document_id"] == intake.document_id
        assert block["esr_availability"] == intake.esr_availability
        assert block["permitted_purpose"] == intake.permitted_purpose

    def test_no_human_step_is_outstanding_for_this_ticket(self, decision):
        """It was the planner run, then the Phase 7 dispatch, then Phase 8,
        then the assessor run.  All four are done.  The field must say so
        rather than be deleted, so a reader of the record can tell a closed
        ticket from one whose outstanding step was never written down."""
        outstanding = decision["what_is_outstanding_for_the_operator"]
        assert outstanding.startswith("Nothing for this ticket")
        assert "harness.commands.blind_assessment assess" not in outstanding

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
            if c["criterion"].startswith("Candidate version 1")
        )
        types = {n["type"] for n in demo_snapshot.nodes}
        assert f"{len(demo_snapshot.nodes)} nodes of {len(types)} types" in evidence
        assert demo_snapshot.snapshot_id in evidence

    def test_the_candidate_packages_snapshot_is_the_one_on_disk(
        self, report, candidate_package, demo_snapshot
    ):
        evidence = _criterion_4_evidence(report)
        assert candidate_package.manifest["snapshot_id"] == demo_snapshot.snapshot_id
        assert demo_snapshot.snapshot_id in evidence
        assert str(ba.DEFAULT_PACKAGE_BUDGET) in evidence

    def test_the_policy_forbidden_exclusion_is_still_the_packages_own(
        self, blind_packages
    ):
        """No longer a number the report states, and still worth pinning: the
        blind view refuses the ``validated_by`` traversal to MS6."""
        forbidden = {
            (e["id"], e["detail"])
            for p in blind_packages
            for e in p.manifest.get("exclusions", [])
            if e.get("reason") == "policy_forbidden"
        }
        assert forbidden == {("MS6", "traversal_not_permitted:validated_by")}

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


class TestTheAssessorsReport:
    """Criterion 3 against the report the operator's run produced.

    Two things are pinned, and they pull in opposite directions on purpose.
    The bindings are what closes the criterion.  The blank ``source_ref`` is
    what F12 is open against, so the day the converter carries the Tier 5
    field these tests fail and name the finding that has been resolved.
    """

    ASSESSOR_PIN = "claude-sonnet-5@claude-cli-subscription@2026-10-02"

    @pytest.fixture(scope="class")
    def blind_report(self) -> dict:
        path = REPO / "harness/blind_reports/blind_e518c50023ee_0001.json"
        assert path.exists(), (
            f"{path.relative_to(REPO)} is absent; criterion 3 is recorded as met "
            "on a report that is not on disk"
        )
        return json.loads(path.read_text(encoding="utf-8"))

    def test_it_binds_the_candidate_profile_and_assessor(self, blind_report, report):
        """The criterion names three bindings and a label.  All four, and the
        hash and profile version must be the ones the Tier 4 record states."""
        evidence = next(
            c["evidence"] for c in report["acceptance_criteria"]
            if c["criterion"].startswith("The blind report carries")
        )
        for field in ("candidate_hash", "profile_version", "assessor_pin"):
            value = blind_report[field]
            assert value, f"{field} is empty"
            assert value in evidence, (
                f"the record states a {field} the report does not carry"
            )
        assert blind_report["scope"] in {"complete", "partial"}

    def test_every_cell_carries_the_bindings_too(self, blind_report):
        """A cell lifted out of the report must still name what produced it."""
        for cell in blind_report["cells"]:
            assert cell["candidate_hash"] == blind_report["candidate_hash"]
            assert cell["profile_version"] == blind_report["profile_version"]
            assert cell["assessor_pin"] == blind_report["assessor_pin"]

    def test_the_assessor_was_not_the_drafter(self, blind_report):
        """The one independence axis the subscription transport preserves."""
        from runner.semantic_dispatch import AGENT_MODEL
        from runner.skill_runtime import SKILL_MODEL

        assert blind_report["assessor_model"] not in {SKILL_MODEL, AGENT_MODEL}
        assert blind_report["assessor_pin"] == self.ASSESSOR_PIN

    def test_no_pack_was_truncated(self, blind_report):
        """F9 fixed: the ceiling is the transport's, so no cell is graded on a
        pack the rubric forbids passing."""
        for cell in blind_report["cells"]:
            record = cell["coverage"]["pack_record"]
            assert record["status"] == "complete", (
                f"{cell['expectation_key']} was graded on a truncated pack"
            )
            assert record["token_estimate"] <= record["token_budget"]

    def test_the_grades_discriminate(self, blind_report):
        """A lane that returns one verdict for every cell measures nothing.
        These are advisory and never run-blocking."""
        assert blind_report["advisory"] is True
        assert blind_report["blocking"] is False
        scores = [c["score"] for c in blind_report["cells"]]
        assert len(set(scores)) > 1
        assert all(0.0 <= s <= 1.0 for s in scores)

    def test_f12_every_candidate_claim_still_has_no_source(self):
        """The finding, measured rather than quoted from the assessor."""
        directory = (
            REPO / "harness/blind_reports/candidates" / DOCUMENT_NODE_ID
        )
        blank = total = confirmed_blank = 0
        for path in sorted(directory.glob("*_section.json")):
            claims = json.loads(path.read_text(encoding="utf-8"))
            for claim in claims["validation_status"]["claim_statuses"]:
                total += 1
                if not str(claim.get("source_ref") or "").strip():
                    blank += 1
                    if claim.get("status") == "confirmed":
                        confirmed_blank += 1
        assert total == blank == 147, (
            "F12 is recorded as every claim carrying an empty source_ref; "
            f"{total - blank} of {total} now carry one. If the converter was "
            "fixed, close F12 and re-grade."
        )
        assert confirmed_blank == 90

    def test_f12_the_tier_5_sections_it_was_built_from_do_have_sources(self):
        """Which is what makes F12 a loss in the seam rather than an absence
        at the origin."""
        directory = REPO / "docs/tier5_deliverables/proposal_sections"
        total = blank = 0
        for path in sorted(directory.glob("*_section.json")):
            section = json.loads(path.read_text(encoding="utf-8"))
            for claim in section["validation_status"]["claim_statuses"]:
                total += 1
                if not str(claim.get("source_ref") or "").strip():
                    blank += 1
        assert total == 180
        assert blank == 0, f"{blank} Tier 5 claims lost their source_ref upstream"
