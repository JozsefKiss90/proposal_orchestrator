"""
Milestone closure: the T03 scenario end to end.

One test walks the handoff's first operational milestone in order on the
synthetic fixture (``plans/Dev_Graph_Orchestrator_Implementation_Handoff.md``
section 11). Responsibility for Task T03 moves from Participant B to
Participant C on an unsubmitted candidate without an ESR. The walk is:

1. import the candidate and record the ESR intake (availability unknown);
2. pre-evaluate the candidate blind and bind the assessment to that version;
3. record the change request as an approved Tier 3 change;
4. check the revision contract (accepted; the protected variant is rejected);
5. plan the impact and write the advisory;
6. compare the advisory with a seeded scheduler decision in shadow mode;
7. create the new candidate version with provenance;
8. assess the new version blind, with the intake, and check the earlier
   assessment is no longer applicable;
9. the additional cases: a planted ESR under available, unavailable and
   not-applicable intakes, and a second profile changing verdicts through
   configuration alone.

Every acceptance item of handoff section 11 is referenced by exactly one
``# handoff §11 item N`` comment above the assertion block that proves it.
Nothing here dispatches a phase, evaluates a gate, writes reuse metadata or
invokes Claude: the assessor is a scripted fake.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest

import harness.blind_assessment as ba
import harness.commands.blind_assessment as cmd
from tests.harness._preflight import preflighted
from harness.judge import Judge, JudgeConfig
from harness.provenance import ProvenanceLog
from harness.rubrics import load_profile_bundle
from runner.dev_graph import (
    ACTIONS,
    HITS,
    IMPACT_REQUEST_REL,
    POLICY_VERSION,
    REVISION_REQUEST_REL,
    SHADOW_REQUEST_REL,
    bind_assessment,
    build_package,
    build_snapshot,
    check_applicability,
    check_revision,
    compare_shadow,
    import_document,
    load_snapshot,
    normalise_contract,
    plan_impact,
    read_esr_intake,
    read_revision_record,
    read_run_records,
    record_change,
    record_esr_intake,
    write_impact_plan,
    write_revision_record,
    write_shadow_comparison,
)
from runner.dev_graph.builder import OBJECTIVES_REL, WP_SEED_REL
from runner.dev_graph.identity import HASH_PREFIX
from runner.dev_graph.policies import HISTORICAL_FEEDBACK_TAGS
from runner.paths import find_repo_root
from tests.runner.test_dev_graph_gate_invariants import _evaluate_gate_call_sites

REPO = find_repo_root()
FIXTURE = REPO / "tests" / "fixtures" / "dev_graph_synthetic"
CANDIDATE = Path("docs/tier5_deliverables/candidates/synthetic_candidate.json")
CANDIDATE_V2 = Path("docs/tier5_deliverables/candidates/synthetic_candidate_v2.json")
ESR_DOC = Path("docs/tier5_deliverables/candidates/synthetic_esr.json")
REUSE_DIR = Path("docs/tier4_orchestration_state/reuse/phase8")
RUNS_DIR = Path(".claude/runs")
NODE = "n08a_excellence_drafting"
SECTION_PATH = "docs/tier5_deliverables/proposal_sections/synthetic_section_two.json"
DELIVERABLE_NODE = "n08b_impact_drafting"
DELIVERABLE_CHECK_PATH = "docs/tier4_orchestration_state/validation_reports/synthetic_deliverable_check.json"
NOT_REUSED = {"status": "not_reused", "reason": "fingerprint_mismatch"}
FROZEN = "2026-09-29T12:00:00+00:00"
BIG = 100_000

#: Responsibility changes are permitted; objective and deliverable are
#: protected; the capacity of an untouched participant stays an open item.
CONTRACT = {
    "contract_id": "RC-T03",
    "permitted_change_classes": ["responsibility"],
    "protected_node_ids": ["OBJ-1", "D1.1"],
    "unresolved_items": [
        {"item_id": "U-CAP-A", "description": "Capacity of Participant A", "node_ids": ["P-A"]}
    ],
}

_THRESHOLD_RE = re.compile(r"at or above ([0-9.]+) corresponds to a pass")


# --------------------------------------------------------------------------- #
# Helpers: world, profiles, fake assessors
# --------------------------------------------------------------------------- #


def _load(root: Path, rel: Path | str) -> dict:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def _dump(root: Path, rel: Path | str, obj) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _tree_bytes(root: Path, rel: Path | str) -> dict[str, bytes]:
    base = root / rel
    if not base.exists():
        return {}
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in base.rglob("*") if p.is_file()}


def _graph_profile(root: Path, *, name: str, criteria: list[tuple], scale: str, threshold: int,
                   maximum: int, pass_threshold: float) -> Path:
    """A call-neutral profile mapped onto the fixture candidate's sections.

    *criteria* rows are ``(criterion_id, registry_id, section_id, key, text, terms)``.
    Everything that differs between the two profiles of the closure test is a
    parameter here; the harness code they drive is the same.
    """
    registry = {
        "instruments": [
            {
                "instrument_type": f"SYN-{name.upper()}",
                "criteria": [
                    {"criterion_id": rid, "evaluator_expectations": [text]}
                    for _c, rid, _s, _k, text, _t in criteria
                ],
            }
        ]
    }
    scorecard = {
        "scorecard_id": f"{name}_scorecard",
        "provenance": {"version": "0.1"},
        "scoring": {
            "scale": scale,
            "levels": {"0": "none", scale.split("-")[1].split(",")[0]: "full"},
            "overall_threshold": threshold,
            "overall_max": maximum,
        },
        "criteria": [
            {
                "id": cid,
                "name": rid,
                "weight_pct": 34 if i == 0 else 33,
                "aspects": [{"id": key, "text": text, "option_tag": "Track one", "source_page": 1}],
            }
            for i, (cid, rid, _s, key, text, _t) in enumerate(criteria)
        ],
        "excluded_aspects": [],
    }
    rubrics = {
        "rubric_set_id": f"{name}_rubrics",
        "version": "0.1.0",
        "scorecard_id": f"{name}_scorecard",
        "scorecard_version": "0.1",
        "rubrics": [
            {
                "expectation_key": key,
                "criterion_id": cid,
                "expectation_text": text,
                "rubric": "Integrity-framed: addressed AND grounded.",
                "evaluation_steps": ["Check the spans.", "Check the claims."],
                "pass_threshold": pass_threshold,
                "selection_terms": terms,
                "anchor_sub_section_ids": [sid],
            }
            for cid, _rid, sid, key, text, terms in criteria
        ],
    }
    profile = {
        "profile_id": name,
        "label": f"Synthetic profile {name}",
        "instrument": {
            "registry_instrument_type": f"SYN-{name.upper()}",
            "name": f"Synthetic {name} track",
            "form_name": f"Synthetic {name} assessment form",
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
        "registry_path": f"{name}/registry.json",
        "scorecard": {"path": f"{name}/scorecard.json", "scorecard_id": f"{name}_scorecard", "version": "0.1"},
        "rubric_set": {"path": f"{name}/rubrics.json", "rubric_set_id": f"{name}_rubrics", "version": "0.1.0"},
    }
    _dump(root, f"{name}/registry.json", registry)
    _dump(root, f"{name}/scorecard.json", scorecard)
    _dump(root, f"{name}/rubrics.json", rubrics)
    return _dump(root, f"{name}/profile.json", profile)


def _profile_a(root: Path) -> Path:
    return _graph_profile(
        root,
        name="syn_a",
        criteria=[
            ("aims", "Aims", "S1", "aims-objectives", "Clarity of the objectives", ["objective"]),
            ("plan", "Plan", "S2", "plan-tasks", "Credibility of the task plan", ["task"]),
            ("outputs", "Outputs", "S3", "outputs-deliverables", "Definition of the deliverables", ["deliverable"]),
        ],
        scale="0-5",
        threshold=10,
        maximum=15,
        pass_threshold=0.7,
    )


def _profile_b(root: Path) -> Path:
    """Different criteria names, a different scale, a stricter threshold."""
    return _graph_profile(
        root,
        name="syn_b",
        criteria=[
            ("novelty", "Novelty", "S1", "nov-objectives", "Novelty of the objectives", ["objective"]),
            ("feasibility", "Feasibility", "S2", "feas-tasks", "Feasibility of the task plan", ["task"]),
            ("reach", "Reach", "S3", "reach-deliverables", "Reach of the deliverables", ["deliverable"]),
        ],
        scale="0-10, integers",
        threshold=60,
        maximum=100,
        pass_threshold=0.9,
    )


class ScriptedBackend:
    """One fixed score; the verdict is decided by the threshold the prompt
    states, never by Python. Keeps every prompt it was shown."""

    def __init__(self, score: float = 0.75):
        self.score = score
        self.calls = 0
        self.prompts: list[str] = []
        self.thresholds: set[float] = set()

    def __call__(self, messages):
        self.calls += 1
        self.prompts.extend(str(m.get("content", "")) for m in messages)
        match = _THRESHOLD_RE.search(str(messages[0].get("content", "")))
        if match:
            threshold = float(match.group(1))
            self.thresholds.add(threshold)
            passed = self.score >= threshold
        else:
            passed = True
        return {"content": json.dumps({"passed": passed, "score": self.score, "rationale": "scripted"})}


def _judge(root: Path, backend, tag: str) -> Judge:
    return Judge(
        JudgeConfig(model="fake-assessor", version="pin-7"),
        backend=backend,
        provenance_log=ProvenanceLog(root / f"provenance_{tag}.jsonl"),
        clock=lambda: FROZEN,
    )


def _assess(root: Path, profile: Path, backend, out: Path, *extra: str) -> tuple[int, dict]:
    """Run the blind command on document CAND-1 and return (exit code, report)."""
    before = {p.name for p in out.iterdir() if p.is_file()} if out.exists() else set()
    code = cmd.main(
        preflighted(["assess", "--document", "CAND-1", "--graph-root", str(root), "--out-dir", str(out),
         "--repo-root", str(root), "--profile", str(profile), *extra]),
        judge=_judge(root, backend, out.name),
        clock=lambda: FROZEN,
    )
    new = [p for p in out.iterdir() if p.is_file() and p.name not in before] if out.exists() else []
    if code == 2:
        assert new == []
        return code, {}
    (path,) = new
    return code, json.loads(path.read_text(encoding="utf-8"))


def _document_nodes(snap) -> dict[str, dict]:
    return {n["id"]: n for n in snap.nodes if n["type"] == "artifact_version"}


def _entry(plan, entry_id: str) -> dict:
    matches = [e for e in plan.entries if e["id"] == entry_id]
    assert len(matches) == 1, f"{entry_id}: {matches}"
    return matches[0]


def _passage_id(snap, section: str) -> str:
    return next(n["id"] for n in snap.nodes if n["type"] == "passage" and n["id"].endswith("#" + section))


def _t03_to_c(seed: dict) -> dict:
    t03 = next(t for t in seed["work_packages"][0]["tasks"] if t["task_id"] == "T03")
    t03["responsible_partner"] = "P-C"
    return seed


# --------------------------------------------------------------------------- #
# The walk
# --------------------------------------------------------------------------- #


def test_t03_scenario_end_to_end(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    # Sentinels the walk must never touch: reuse metadata and the run manifest
    # that carries the scheduler's recorded decision.
    (root / REUSE_DIR).mkdir(parents=True)
    (root / REUSE_DIR / f"{NODE}.reuse.json").write_text('{"sentinel": "reuse metadata"}', encoding="utf-8")
    manifest_path = root / RUNS_DIR / "run-a" / "run_manifest.json"
    manifest_path.parent.mkdir(parents=True)
    decisions = {NODE: NOT_REUSED, DELIVERABLE_NODE: NOT_REUSED}
    manifest_path.write_text(json.dumps({"run_id": "run-a", "reuse_decisions": decisions}), encoding="utf-8")
    reuse_before = _tree_bytes(root, REUSE_DIR)
    runs_before = _tree_bytes(root, RUNS_DIR)

    profile_a = _profile_a(root)
    bundle_a = load_profile_bundle(profile_a, repo_root=root)

    # ---- 1. The candidate and its intake -----------------------------------
    first = import_document(root, CANDIDATE)
    intake = record_esr_intake(
        root, intake_id="INTAKE-1", document_id="CAND-1", submission_id="SUB-1",
        call_id="SYN-CALL-01", permitted_purpose="blind_pre_evaluation",
    )
    assert intake.prior_submission is False and intake.esr_availability == "unknown"
    assert read_esr_intake(root, "INTAKE-1") == intake

    # ---- 2. Independent pre-evaluation of version one ----------------------
    # handoff §11 item 9: pre-evaluation succeeds without submission history
    # or an ESR; resubmission is not invoked. No submitted document exists,
    # the intake declares no prior submission and no ESR, the report is
    # bound to the candidate, and the walk dispatched nothing (the runs
    # directory is unchanged, so no run was started or resumed).
    backend_v1 = ScriptedBackend()
    code_v1, report_v1 = _assess(root, profile_a, backend_v1, root / "reports_v1", "--intake", "INTAKE-1")
    assert code_v1 in (0, 1) and report_v1["scope"] in ("complete", "partial")
    assert report_v1["task_label"] == ba.BLIND_TASK_LABEL
    assert report_v1["esr_availability"] == "unknown" and report_v1["intake_id"] == "INTAKE-1"
    assert report_v1["evidence_source"] == ba.EVIDENCE_SOURCE_DEV_GRAPH
    assert not any(n["content"].get("state") == "submitted" for n in _document_nodes(build_snapshot(root)).values())
    assert _tree_bytes(root, RUNS_DIR) == runs_before
    snap_v1 = build_snapshot(root)
    assert report_v1["snapshot_id"] == snap_v1.snapshot_id
    v1_node = _document_nodes(snap_v1)[first.id]
    assessment_v1 = bind_assessment("ASSESS-1", v1_node, profile_version=bundle_a.version, policy_version=POLICY_VERSION)
    assert check_applicability(assessment_v1, v1_node, profile_version=bundle_a.version).applicable is True

    # ---- 3. The change request: T03 from Participant B to Participant C ----
    change = record_change(root, WP_SEED_REL, _t03_to_c(_load(root, WP_SEED_REL)), change_id="CR-T03")
    assert {e["label"] for e in change.change_set["edges"]["removed"]} == {"T03 -assigned_to-> P-B"}
    assert {e["label"] for e in change.change_set["edges"]["added"]} == {"T03 -assigned_to-> P-C"}
    before = load_snapshot(root, change.before_snapshot_id)
    after = load_snapshot(root, change.after_snapshot_id)
    assert before.snapshot_id == snap_v1.snapshot_id

    # ---- 4. The revision contract ------------------------------------------
    contract = normalise_contract(CONTRACT)
    check = check_revision(contract, change.change_set)
    assert check.verdict == "accepted" and check.change_classes == ("responsibility",)
    assert check.protected_hits == () and check.unpermitted_classes == ()
    # Unresolved participant capacity remains explicit: carried as
    # unresolved, never approved by the accepted change.
    (capacity,) = check.unresolved
    assert capacity["item_id"] == "U-CAP-A" and capacity["status"] == "unresolved"
    assert "approved" not in json.dumps(check.to_dict())

    # handoff §11 item 4: protected factual/relational changes are rejected or
    # flagged for review. The same contract rejects a change that also alters
    # the protected objective, naming it, and flags a timing change the
    # contract does not permit.
    scratch = tmp_path / "protected"
    shutil.copytree(root, scratch)
    objectives = _load(scratch, OBJECTIVES_REL)
    objectives["objectives"][0]["measurable_target"] = "Target one, revised"
    protected = record_change(scratch, OBJECTIVES_REL, objectives, change_id="CR-OBJ")
    rejected = check_revision(contract, protected.change_set)
    assert rejected.verdict == "rejected"
    assert [h["node_id"] for h in rejected.protected_hits] == ["OBJ-1"]
    timing_seed = _load(scratch, WP_SEED_REL)
    next(t for t in timing_seed["work_packages"][0]["tasks"] if t["task_id"] == "T03")["end_month"] = 20
    timing = record_change(scratch, WP_SEED_REL, timing_seed, change_id="CR-TIME")
    flagged = check_revision(contract, timing.change_set)
    assert flagged.verdict == "flagged_for_review" and flagged.unpermitted_classes == ("timing",)

    # ---- 5. The impact plan and its advisory -------------------------------
    plan = plan_impact(before, after, read_run_records(root), change_id="CR-T03")
    assert plan.origins == ["T03"] and not plan.nothing_changed

    # handoff §11 item 1: the planner finds affected task descriptions,
    # responsibility tables, proposal passages and applicable schedule and
    # resource checks.
    s2 = _passage_id(after, "S2")
    assert _entry(plan, "T03")["kind"] == "record" and _entry(plan, "T03")["hit"] == "origin"
    responsibility_table = _entry(plan, s2)
    assert responsibility_table["kind"] == "passage" and responsibility_table["action"] == "reconsider"
    for section in ("S1", "S3"):
        assert _entry(plan, _passage_id(after, section))["kind"] == "passage"
    assert _entry(plan, "CHK-SCHEDULE")["action"] == "rerun" and _entry(plan, "CHK-SCHEDULE")["hit"] == "direct"
    assert _entry(plan, "CHK-RESOURCE")["action"] == "rerun" and _entry(plan, "CHK-RESOURCE")["hit"] == "direct"

    # handoff §11 item 2: an unchanged check result can be retained only under
    # an explicit valid policy; being reconsidered does not automatically
    # imply changed output. The deliverable check is reached over unchanged
    # edges only and is retained under policy, not silently kept; the
    # responsibility passage is reconsidered, not marked as changed output.
    deliverable = _entry(plan, "CHK-DELIVERABLE")
    assert deliverable["hit"] == "transitive" and deliverable["action"] == "reuse-under-policy"
    assert responsibility_table["action"] == "reconsider" and responsibility_table["action"] != "rerun"
    assert "reuse" not in ACTIONS and "unchanged" not in ACTIONS
    # The policy that may retain it is the scheduler's, not the planner's:
    # the shadow comparison below shows the recorded not-reused decision
    # standing against the planner's narrower advisory (see step 6).

    # handoff §11 item 6: a missing dependency or newly relevant source
    # produces conservative handling. The artifact with no declared inputs is
    # rerun, and the source behind the responsibility claim is flagged.
    unknown = _entry(plan, "ART-SECTION-2")
    assert unknown["hit"] == "coverage_unknown" and unknown["action"] == "rerun"
    newly_relevant = {s["id"]: s for s in plan.newly_relevant_sources}
    assert "SRC-1" in newly_relevant and newly_relevant["SRC-1"]["reason_path"][0] == "changed:T03"

    # handoff §11 item 7: every proposed rerun/reuse decision has a
    # reproducible reason path. Every entry starts at the change or at the
    # unknown coverage, ends at the entry, and the plan id is content-derived.
    for e in plan.entries:
        assert e["reason_path"], e["id"]
        head = "coverage_unknown:" if e["hit"] == "coverage_unknown" else "changed:"
        assert e["reason_path"][0].startswith(head)
        assert e["action"] in ACTIONS and e["hit"] in HITS
    assert deliverable["reason_path"] == ["changed:T03", "T03 -produces-> D1.1", "input_of:CHK-DELIVERABLE"]
    assert plan.plan_id == plan_impact(before, after, read_run_records(root), change_id="CR-T03").plan_id
    _dump(root, IMPACT_REQUEST_REL, {"change_id": "CR-T03"})
    (plan_path,) = write_impact_plan(root)
    written_plan = json.loads(plan_path.read_text(encoding="utf-8"))
    assert written_plan["plan_id"] == plan.plan_id and written_plan["advisory"] is True
    assert written_plan["mode"] == "shadow"

    # ---- 6. Shadow comparison against the seeded scheduler decision --------
    comparison = compare_shadow(
        plan, decisions, run_id="run-a",
        artifact_paths={NODE: SECTION_PATH, DELIVERABLE_NODE: DELIVERABLE_CHECK_PATH},
    )
    rows = {r["node_id"]: r for r in comparison.rows}
    section_row = rows[NODE]
    assert section_row["scheduler"] == "rerun" and section_row["planner"] == "rerun"
    assert section_row["record_ids"] == ["ART-SECTION-2"] and section_row["diagnostic"] == "agreed"
    # Item 2, continued: the deliverable check the planner would retain under
    # policy is one the scheduler decided to rerun. The comparison records
    # the disagreement as advisory; the scheduler's decision stands and the
    # planner's label changes no output.
    retained = rows[DELIVERABLE_NODE]
    assert retained["planner_actions"] == ["reuse-under-policy"] and retained["record_ids"] == ["CHK-DELIVERABLE"]
    assert retained["scheduler"] == "rerun" and retained["planner"] == "reuse"
    assert retained["diagnostic"] == "planner_narrower" and comparison.diagnostic == "planner_narrower"
    _dump(root, SHADOW_REQUEST_REL, {"plan_id": plan.plan_id, "run_id": "run-a"})
    (comparison_path,) = write_shadow_comparison(root)
    written_comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    assert written_comparison["consumed_at_runtime"] is False and written_comparison["mode"] == "shadow"

    # handoff §11 item 8: gate authority and baseline conservative behaviour
    # remain intact. The advisory and the comparison wrote no reuse metadata
    # and touched no run manifest, and the dev-graph package names no gate
    # evaluation, scheduler or transport.
    assert _tree_bytes(root, REUSE_DIR) == reuse_before
    assert _tree_bytes(root, RUNS_DIR) == runs_before
    package_text = "\n".join(p.read_text(encoding="utf-8") for p in (REPO / "runner" / "dev_graph").glob("*.py"))
    for forbidden in ("evaluate_gate", "dag_scheduler", "claude_transport", "write_reuse_metadata"):
        assert forbidden not in package_text, forbidden
    call_sites = _evaluate_gate_call_sites()
    assert len(call_sites) == 2 and {path for path, _ in call_sites} == {"runner/dag_scheduler.py"}, call_sites

    # ---- 7. The new candidate version with provenance ----------------------
    doc = _load(root, CANDIDATE)
    s2_section = next(s for s in doc["sections"] if s["section_id"] == "S2")
    s2_section["content"] = "Task three is led by Participant C with Participant B contributing. It starts in month ten."
    doc["commitments"][0]["text"] = "Participant C leads Task three."
    _dump(root, CANDIDATE_V2, doc)
    _dump(root, REVISION_REQUEST_REL, {
        "revision_id": "REV-T03",
        "change_id": "CR-T03",
        "contract": CONTRACT,
        "candidate": CANDIDATE_V2.as_posix(),
        "supersedes": first.id,
        "evidence": ["T03", "P-C"],
    })
    (revision_path,) = write_revision_record(root)
    revision = read_revision_record(root, "REV-T03").to_dict()
    assert revision["check"]["verdict"] == "accepted"
    created = revision["candidate_version"]["created"]
    assert revision["candidate_version"]["previous"]["id"] == first.id and created["id"] != first.id
    snap_v2 = build_snapshot(root)
    docs = _document_nodes(snap_v2)
    v2_node = docs[created["id"]]
    provenance = v2_node["content"]["provenance"]
    assert provenance["change_id"] == "CR-T03"
    assert provenance["supersedes"] == {"id": first.id, "version": v1_node["version"]}
    assert [e["id"] for e in provenance["evidence"]] == ["P-C", "T03"]
    assert any(e["predicate"] == "supersedes" and e["source"]["id"] == created["id"] for e in snap_v2.edges)

    # handoff §11 item 3: revision and blind-assessment packages contain the
    # correct evidence views. The controlled-revision package around T03 is
    # built under its own view and lists the change and the new participant;
    # the blind package around the new candidate is built under the blind view
    # and admits no assessment, finding or change-request node.
    revision_package = build_package(
        snap_v2, task="T03", view="controlled_revision", budget=BIG, policy_version=POLICY_VERSION,
        expected_snapshot_id=snap_v2.snapshot_id, project="SYN-PROJECT", profile_version=bundle_a.version,
    )
    assert revision_package.manifest["view"] == "controlled_revision"
    revision_included = {i["id"] for i in revision_package.manifest["included"]}
    assert {"T03", "P-C"} <= revision_included
    assert not any(i["type"] in ("assessment", "finding") for i in revision_package.items)
    blind_evidence = ba.build_blind_evidence(root, "CAND-1", profile_version=bundle_a.version, out_dir=root / "reports_v2")
    assert blind_evidence.document == created["id"]
    assert blind_evidence.package.manifest["view"] == "blind_pre_evaluation"
    assert not any(i["type"] in ("assessment", "finding", "change_request") for i in blind_evidence.package.items)
    blind_included = {i["id"] for i in blind_evidence.package.manifest["included"]}
    assert {f"{created['id']}#S1", f"{created['id']}#S2", f"{created['id']}#S3"} <= blind_included
    # What the assessor grades is the new version alone, and so is what the
    # package carries: the blind view hides every node derived from the
    # superseded version, so nothing of it re-enters through the shared
    # objective node. Pinned by
    # ``test_blind_package_around_a_new_version_excludes_the_superseded_version``.
    materialised = {p.name: p.read_text(encoding="utf-8") for p in blind_evidence.candidate_dir.glob("*.json")}
    assert set(materialised) == {"S1.json", "S2.json", "S3.json"}
    assert "Participant C leads" in materialised["S2.json"] or "led by Participant C" in materialised["S2.json"]
    assert first.id not in json.dumps(materialised)

    # ---- 8. Blind assessment of the new version; the old one lapses --------
    backend_v2 = ScriptedBackend()
    code_v2, report_v2 = _assess(root, profile_a, backend_v2, root / "reports_v2", "--intake", "INTAKE-1")
    assert code_v2 in (0, 1) and report_v2["scope"] in ("complete", "partial")
    assert report_v2["task_label"] == ba.BLIND_TASK_LABEL
    assert report_v2["esr_availability"] == "unknown" and report_v2["intake_id"] == "INTAKE-1"
    assert report_v2["snapshot_id"] == snap_v2.snapshot_id
    assert report_v2["package_id"] == blind_evidence.package.package_id
    assert report_v2["candidate_hash"] != report_v1["candidate_hash"]
    assert all(c["candidate_hash"] == report_v2["candidate_hash"] for c in report_v2["cells"])
    assert backend_v2.calls > 0 and all("ESR" not in p for p in backend_v2.prompts)

    # handoff §11 item 5: the earlier candidate assessment is no longer
    # applicable after candidate content changes.
    lapsed = check_applicability(assessment_v1, v2_node, profile_version=bundle_a.version)
    assert lapsed.applicable is False and lapsed.reasons == ("candidate_version_changed",)
    assert lapsed.bound["candidate"] == {"id": first.id, "version": v1_node["version"]}
    assert lapsed.current["candidate"] == {"id": created["id"], "version": v2_node["version"]}
    with pytest.raises(ba.BlindAssessmentError):
        ba.build_blind_evidence(root, first.id, profile_version=bundle_a.version, out_dir=root / "reports_old")

    # ---- 9a. Additional cases: feedback available, unavailable, inapplicable
    # handoff §11 item 10: additional cases exercise available, unavailable
    # and inapplicable feedback without blind-assessment leakage. A planted
    # ESR is imported as a submitted document; each intake stamps its
    # declared availability on the report; the package excludes the ESR by
    # policy and no prompt or report carries an ESR token.
    esr = import_document(root, ESR_DOC, state="submitted")
    intakes: dict[str, dict[str, Any]] = {
        "INTAKE-AV": dict(esr_availability="available", esr_reference=esr.id.split("@")[0], prior_submission=True),
        "INTAKE-UN": dict(esr_availability="unavailable", prior_submission=True),
        "INTAKE-NA": dict(esr_availability="not_applicable"),
    }
    for intake_id, extra in intakes.items():
        record_esr_intake(
            root, intake_id=intake_id, document_id="CAND-1", submission_id="SUB-1",
            call_id="SYN-CALL-01", permitted_purpose="blind_pre_evaluation", **extra,
        )
        backend = ScriptedBackend()
        code, report = _assess(root, profile_a, backend, root / f"reports_{intake_id}", "--intake", intake_id)
        assert code in (0, 1), intake_id
        assert report["esr_availability"] == extra["esr_availability"] and report["intake_id"] == intake_id
        assert report["task_label"] == ba.BLIND_TASK_LABEL
        assert "ESR" not in json.dumps(report)
        assert backend.calls > 0 and all("ESR" not in p for p in backend.prompts)
        evidence = ba.build_blind_evidence(root, "CAND-1", profile_version=bundle_a.version, out_dir=root / "pkg")
        assert report["package_id"] == evidence.package.package_id
        rendered = json.dumps(evidence.package.to_dict())
        assert "ESR" not in rendered and not (HISTORICAL_FEEDBACK_TAGS & set(re.findall(r"[a-z_]+", rendered)))
        assert any(
            e["reason"] == "policy_forbidden" and e["path"] == esr.path
            for e in evidence.package.manifest["exclusions"]
        )
    # The ESR-informed purpose is a separately labelled task: the blind lane
    # refuses it before any assessor call.
    record_esr_intake(
        root, intake_id="INTAKE-ESR", document_id="CAND-1", submission_id="SUB-1", call_id="SYN-CALL-01",
        permitted_purpose="esr_informed_review", prior_submission=True, esr_availability="available",
        esr_reference=esr.id.split("@")[0],
    )
    refused_backend = ScriptedBackend()
    code_refused, _ = _assess(root, profile_a, refused_backend, root / "reports_refused", "--intake", "INTAKE-ESR")
    assert code_refused == 2 and refused_backend.calls == 0

    # ---- 9b. Additional case: a second profile through configuration -------
    # handoff §11 item 11: a second synthetic profile changes criteria and
    # constraints through configuration without changing core logic. The same
    # candidate, the same fixed assessor score and the same command: profile A
    # passes every cell at its threshold, profile B fails every cell at its
    # stricter one, and the two reports pin different profiles.
    profile_b = _profile_b(root)
    bundle_b = load_profile_bundle(profile_b, repo_root=root)
    assert bundle_b.profile_id != bundle_a.profile_id and bundle_b.version != bundle_a.version
    assert bundle_b.scoring.scale != bundle_a.scoring.scale
    assert bundle_b.scoring.overall_threshold != bundle_a.scoring.overall_threshold
    backend_a, backend_b = ScriptedBackend(), ScriptedBackend()
    code_a, report_a = _assess(root, profile_a, backend_a, root / "reports_prof_a", "--intake", "INTAKE-1")
    code_b, report_b = _assess(root, profile_b, backend_b, root / "reports_prof_b", "--intake", "INTAKE-1")
    assert code_a in (0, 1) and code_b in (0, 1)
    assert backend_a.thresholds == {0.7} and backend_b.thresholds == {0.9}
    assert report_a["candidate_hash"] == report_b["candidate_hash"]
    assert {c["criterion_id"] for c in report_a["cells"]} == {"aims", "plan", "outputs"}
    assert {c["criterion_id"] for c in report_b["cells"]} == {"novelty", "feasibility", "reach"}
    assert all(c["covered"] for c in report_a["cells"])
    assert not any(c["covered"] for c in report_b["cells"])
    assert report_a["profile_id"] == "syn_a" and report_b["profile_id"] == "syn_b"
    assert report_a["profile_version"] == bundle_a.version and report_b["profile_version"] == bundle_b.version

    # The walk left the scheduler's world exactly as it found it.
    assert _tree_bytes(root, REUSE_DIR) == reuse_before
    assert _tree_bytes(root, RUNS_DIR) == runs_before
    assert revision_path.is_file() and comparison_path.is_file() and plan_path.is_file()
    assert plan.plan_id.startswith(HASH_PREFIX)


# --------------------------------------------------------------------------- #
# The gap the walk surfaced, now closed: the blind view hides superseded versions
# --------------------------------------------------------------------------- #


def test_blind_package_around_a_new_version_excludes_the_superseded_version(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    first = import_document(root, CANDIDATE)
    record_change(root, WP_SEED_REL, _t03_to_c(_load(root, WP_SEED_REL)), change_id="CR-T03")
    doc = _load(root, CANDIDATE)
    doc["commitments"][0]["text"] = "Participant C leads Task three."
    _dump(root, CANDIDATE_V2, doc)
    _dump(root, REVISION_REQUEST_REL, {
        "revision_id": "REV-T03", "change_id": "CR-T03", "contract": CONTRACT,
        "candidate": CANDIDATE_V2.as_posix(), "supersedes": first.id, "evidence": ["T03", "P-C"],
    })
    write_revision_record(root)
    evidence = ba.build_blind_evidence(root, "CAND-1", profile_version="profile-0", out_dir=root / "r")
    assert evidence.document != first.id
    stale = sorted(i["id"] for i in evidence.package.manifest["included"] if i["id"].startswith(first.id))
    assert stale == [], stale


# --------------------------------------------------------------------------- #
# Closure evidence: decision log and PRD status
# --------------------------------------------------------------------------- #

#: The six entries the spec names (PRD "Decision log" section).
DECISION_LOG_ENTRIES = (
    "dev-graph-field-ownership",
    "dev-graph-staging-versus-index",
    "dev-graph-type-and-relationship-set",
    "dev-graph-view-policies",
    "dev-graph-shadow-mode-rule",
    "dev-graph-esr-intake-contract",
)


class TestClosureEvidence:
    @pytest.mark.parametrize("stem", DECISION_LOG_ENTRIES)
    def test_each_named_decision_log_entry_exists_once(self, stem: str):
        log = REPO / "docs/tier4_orchestration_state/decision_log"
        entries = list(log.glob(f"{stem}_*.json"))
        assert len(entries) == 1, stem
        rec = json.loads(entries[0].read_text(encoding="utf-8"))
        assert rec["record_type"] == "decision" and rec["id"] == stem

    def test_the_handoff_names_eleven_acceptance_items_and_each_is_referenced_once(self):
        handoff = (REPO / "plans/Dev_Graph_Orchestrator_Implementation_Handoff.md").read_text(encoding="utf-8")
        section = handoff.split("## 11. First operational milestone", 1)[1].split("## 12.", 1)[0]
        items = [line for line in section.splitlines() if line.startswith("- ")]
        assert len(items) == 11
        test_text = Path(__file__).read_text(encoding="utf-8")
        refs = re.findall(r"# handoff §11 item (\d+):", test_text)
        assert sorted(int(r) for r in refs) == list(range(1, len(items) + 1))

    def test_the_prd_status_line_reports_completion(self):
        prd = (REPO / ".scratch/dev-graph-milestone-1/PRD.md").read_text(encoding="utf-8")
        status = next(line for line in prd.splitlines() if line.startswith("Status:"))
        assert "complete" in status.lower()
        assert "ready-for-agent" not in status
