"""
Dev-graph bounded evidence packages and view policies.

Every test copies ``tests/fixtures/dev_graph_synthetic`` into a temporary root,
imports the fixture candidate, builds a snapshot and asks for a package through
the public ``runner.dev_graph.build_package`` entry point. Nothing here touches
a real project, the scheduler, or a gate.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from runner.deterministic_components import COMPONENT_REGISTRY, invoke_component
from runner.dev_graph import (
    COMPLETENESS,
    DECLARED_STATUSES,
    DECLARED_STATUS_FIELDS,
    DEFAULT_PACKAGE_BUDGET,
    EXCLUSION_REASONS,
    NODE_TYPES,
    PACKAGE_REQUEST_REL,
    PACKAGES_REL,
    POLICY_VERSION,
    RELATIONSHIPS,
    SELECTION_REASONS,
    VIEW_POLICIES,
    VIEWS,
    DevGraphError,
    Package,
    Snapshot,
    build_package,
    build_snapshot,
    create_candidate_version,
    declared_status,
    import_document,
    record_change,
    write_package,
)
from runner.dev_graph.builder import PARTNERS_REL, WP_SEED_REL
from runner.dev_graph.identity import content_hash
from runner.paths import find_repo_root

FIXTURE = find_repo_root() / "tests" / "fixtures" / "dev_graph_synthetic"
CANDIDATE = Path("docs/tier5_deliverables/candidates/synthetic_candidate.json")
SOURCES = Path("docs/tier3_project_instantiation/source_materials/sources.json")
CANDIDATE_V2 = Path("docs/tier5_deliverables/candidates/synthetic_candidate_v2.json")

BIG = 100_000


@pytest.fixture
def world(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    import_document(root, CANDIDATE)
    return root


@pytest.fixture
def snap(world: Path) -> Snapshot:
    return build_snapshot(world)


def _load(root: Path, rel: Path) -> dict:
    return json.loads((root / rel).read_text(encoding="utf-8"))


def _dump(root: Path, rel: Path, obj: dict) -> None:
    (root / rel).write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _pkg(snap: Snapshot, **kw) -> Package:
    args = dict(
        task="T03",
        view="engineering",
        budget=BIG,
        policy_version=POLICY_VERSION,
        expected_snapshot_id=snap.snapshot_id,
        project="SYN-PROJECT",
        profile_version="profile-0",
    )
    args.update(kw)
    return build_package(snap, **args)


def _included_ids(pkg: Package) -> set[str]:
    return {i["id"] for i in pkg.manifest["included"]}


def _excluded(pkg: Package, reason: str) -> set[str]:
    return {e["id"] for e in pkg.manifest["exclusions"] if e["reason"] == reason}


def _with_extra(snap: Snapshot, nodes: list[dict], edges: list[dict]) -> Snapshot:
    """A snapshot with extra nodes and edges, validated and re-identified."""
    return Snapshot.from_graph(
        list(snap.nodes) + nodes, list(snap.edges) + edges, list(snap.inputs)
    )


def _node(nid: str, ntype: str, content: dict) -> dict:
    return {
        "id": nid,
        "type": ntype,
        "version": content_hash(content),
        "title": nid,
        "path": "synthetic",
        "content": content,
    }


def _edge(snap_nodes: list[dict], src: str, pred: str, dst: str) -> dict:
    versions = {n["id"]: n["version"] for n in snap_nodes}
    return {
        "predicate": pred,
        "source": {"id": src, "version": versions[src]},
        "target": {"id": dst, "version": versions[dst]},
    }


def _supersede(root: Path) -> tuple[str, str]:
    """Import the fixture candidate, then a second version that supersedes it.
    Returns ``(first_id, second_id)``."""
    first = import_document(root, CANDIDATE)
    seed = _load(root, WP_SEED_REL)
    t03 = next(t for t in seed["work_packages"][0]["tasks"] if t["task_id"] == "T03")
    t03["responsible_partner"] = "P-C"
    change = record_change(root, WP_SEED_REL, seed, change_id="CR-1")
    doc = _load(root, CANDIDATE)
    doc["commitments"][0]["text"] = "Participant C leads Task three."
    _dump(root, CANDIDATE_V2, doc)
    second = create_candidate_version(root, CANDIDATE_V2, supersedes=first.id, change_id=change.change_id)
    return first.id, second.id


# --------------------------------------------------------------------------- #
# View policies are closed configuration data
# --------------------------------------------------------------------------- #


class TestViewPolicies:
    def test_the_six_views_exist_once_each(self):
        assert VIEWS == frozenset(
            {
                "engineering",
                "controlled_revision",
                "integrity_audit",
                "blind_pre_evaluation",
                "historical_feedback_analysis",
                "change_impact_planning",
            }
        )
        assert set(VIEW_POLICIES) == VIEWS

    def test_every_policy_names_its_four_parts_over_closed_vocabularies(self):
        for view, p in VIEW_POLICIES.items():
            assert p.view == view
            assert p.permitted_types and p.permitted_types <= NODE_TYPES
            assert p.permitted_traversals and p.permitted_traversals <= set(RELATIONSHIPS)
            assert p.max_depth >= 1
            assert p.forbidden_types <= NODE_TYPES
            assert not (p.forbidden_types & p.permitted_types), view

    def test_blind_pre_evaluation_forbids_feedback_types_and_tag(self):
        p = VIEW_POLICIES["blind_pre_evaluation"]
        assert {"assessment", "finding", "change_request"} <= p.forbidden_types
        assert "historical_feedback" in p.forbidden_tags

    def test_only_the_blind_view_hides_superseded_versions(self):
        hidden = {v for v, p in VIEW_POLICIES.items() if p.hide_superseded_versions}
        assert hidden == {"blind_pre_evaluation"}
        assert all("hide_superseded_versions" in p.to_dict() for p in VIEW_POLICIES.values())

    def test_policy_version_is_a_content_hash_of_the_policies(self):
        assert POLICY_VERSION.startswith("sha256:")
        assert POLICY_VERSION == content_hash(
            {v: VIEW_POLICIES[v].to_dict() for v in sorted(VIEW_POLICIES)}
        )

    def test_closed_manifest_vocabularies(self):
        assert COMPLETENESS == frozenset({"complete", "incomplete"})
        assert {"policy_forbidden", "over_budget", "not_relevant"} <= EXCLUSION_REASONS
        assert {"seed", "mandatory", "expansion"} <= SELECTION_REASONS


# --------------------------------------------------------------------------- #
# Manifest shape
# --------------------------------------------------------------------------- #


class TestManifest:
    def test_manifest_names_every_field_the_ticket_lists(self, snap: Snapshot):
        m = _pkg(snap).manifest
        for key in (
            "package_id",
            "project",
            "task",
            "view",
            "profile_version",
            "snapshot_id",
            "policy_version",
            "budget",
            "included",
            "mandatory_dependencies",
            "exclusions",
            "unresolved",
            "completeness",
            "package_hash",
        ):
            assert key in m, key
        assert m["project"] == "SYN-PROJECT"
        assert m["task"] == "T03"
        assert m["view"] == "engineering"
        assert m["profile_version"] == "profile-0"
        assert m["snapshot_id"] == snap.snapshot_id
        assert m["policy_version"] == POLICY_VERSION
        assert m["completeness"] in COMPLETENESS

    def test_included_items_carry_version_reason_and_span(self, snap: Snapshot):
        pkg = _pkg(snap)
        versions = {n["id"]: n["version"] for n in snap.nodes}
        for item in pkg.manifest["included"]:
            assert item["version"] == versions[item["id"]]
            assert item["reason"] in SELECTION_REASONS
            assert isinstance(item["path"], list)
        passages = [i for i in pkg.manifest["included"] if i["type"] == "passage"]
        assert passages
        assert all({"start", "end"} <= set(i["span"]) for i in passages)

    def test_seed_is_included_with_reason_seed_and_empty_path(self, snap: Snapshot):
        pkg = _pkg(snap)
        seed = next(i for i in pkg.manifest["included"] if i["id"] == "T03")
        assert seed["reason"] == "seed"
        assert seed["path"] == []

    def test_package_content_hash_matches_the_manifest(self, snap: Snapshot):
        pkg = _pkg(snap)
        assert pkg.manifest["package_hash"] == content_hash(pkg.items)
        assert {i["id"] for i in pkg.items} == _included_ids(pkg)

    def test_unknown_task_is_refused_naming_it(self, snap: Snapshot):
        with pytest.raises(DevGraphError) as exc:
            _pkg(snap, task="T99")
        assert exc.value.kind == "malformed_request"
        assert "T99" in exc.value.offender

    def test_unknown_view_is_refused(self, snap: Snapshot):
        with pytest.raises(DevGraphError) as exc:
            _pkg(snap, view="marketing")
        assert exc.value.kind == "unknown_view"

    @pytest.mark.parametrize("budget", [0, -1, "big"])
    def test_a_non_positive_budget_is_refused(self, snap: Snapshot, budget):
        with pytest.raises(DevGraphError) as exc:
            _pkg(snap, budget=budget)
        assert exc.value.kind == "malformed_request"


# --------------------------------------------------------------------------- #
# Mandatory dependencies survive ranking
# --------------------------------------------------------------------------- #


class TestMandatory:
    def test_t03_mandatory_set_covers_constraints_and_cross_section_dependencies(
        self, snap: Snapshot
    ):
        pkg = _pkg(snap)
        mandatory = {m["id"] for m in pkg.manifest["mandatory_dependencies"]}
        # The responsible participant, the consumed task, the passage that
        # addresses T03 from the candidate (a cross-section dependency) and the
        # source that constrains T03's work package.
        assert {"P-B", "T02", "WP1", "SRC-2"} <= mandatory
        assert any(m.endswith("#S2") for m in mandatory)
        assert mandatory <= _included_ids(pkg)
        by_id = {m["id"]: m for m in pkg.manifest["mandatory_dependencies"]}
        assert by_id["SRC-2"]["path"] == [
            "T03 -contributes_to-> WP1",
            "WP1 -constrained_by-> SRC-2",
        ]
        for m in pkg.manifest["mandatory_dependencies"]:
            assert m["path"], m
        # The included entry of a required item carries the same path.
        included = {i["id"]: i for i in pkg.manifest["included"]}
        for m in pkg.manifest["mandatory_dependencies"]:
            assert included[m["id"]]["path"] == m["path"]

    def test_mandatory_walk_does_not_descend_from_the_work_package(self, snap: Snapshot):
        """contributes_to is followed from a task upward only, and addresses
        only towards the addressed node: the work package's objectives are
        ranked, not required. T01 is required through the consumes chain."""
        pkg = _pkg(snap)
        mandatory = {m["id"] for m in pkg.manifest["mandatory_dependencies"]}
        assert not ({"OBJ-1", "OBJ-2"} & mandatory)
        assert "T01" in mandatory
        assert "OBJ-1" in _included_ids(pkg)

    def test_mandatory_items_are_included_regardless_of_ranking(self, snap: Snapshot):
        full = _pkg(snap)
        mandatory = {m["id"] for m in full.manifest["mandatory_dependencies"]}
        required_cost = sum(
            i["cost"] for i in full.manifest["included"] if i["id"] in mandatory | {"T03"}
        )
        pkg = _pkg(snap, budget=required_cost)
        assert mandatory <= _included_ids(pkg)
        assert _excluded(pkg, "over_budget")
        assert not (_excluded(pkg, "over_budget") & mandatory)
        # Ranking order never puts an optional item ahead of a required one.
        reasons = [i["reason"] for i in pkg.manifest["included"]]
        first_optional = reasons.index("expansion") if "expansion" in reasons else len(reasons)
        assert "mandatory" not in reasons[first_optional:]


# --------------------------------------------------------------------------- #
# Policy is enforced before expansion
# --------------------------------------------------------------------------- #


class TestPolicy:
    def test_forbidden_type_reachable_only_by_expansion_is_excluded_policy_forbidden(
        self, snap: Snapshot
    ):
        claim_id = next(n["id"] for n in snap.nodes if n["id"].endswith("#CL-1"))
        nodes = list(snap.nodes)
        assessment = _node("ASSESS-1", "assessment", {"verdict": "synthetic", "score": 3})
        nodes.append(assessment)
        extended = _with_extra(
            snap, [assessment], [_edge(nodes, claim_id, "validated_by", "ASSESS-1")]
        )
        open_view = _pkg(extended, view="engineering", expected_snapshot_id=extended.snapshot_id)
        assert "ASSESS-1" in _included_ids(open_view)
        blind = _pkg(
            extended, view="blind_pre_evaluation", expected_snapshot_id=extended.snapshot_id
        )
        assert "ASSESS-1" not in _included_ids(blind)
        assert "ASSESS-1" in _excluded(blind, "policy_forbidden")
        assert "ASSESS-1" not in json.dumps(blind.items)

    def test_historical_feedback_tag_is_forbidden_for_blind_pre_evaluation(self, world: Path):
        sources = _load(world, SOURCES)
        sources["sources"][0]["tags"] = ["historical_feedback"]
        _dump(world, SOURCES, sources)
        snap = build_snapshot(world)
        blind = _pkg(snap, view="blind_pre_evaluation")
        assert "SRC-1" in _excluded(blind, "policy_forbidden")
        assert "SRC-1" not in _included_ids(blind)
        assert "historical_feedback" not in json.dumps(blind.items)
        audit = _pkg(snap, view="integrity_audit")
        assert "SRC-1" in _included_ids(audit)

    def test_expansion_never_crosses_a_forbidden_node(self, snap: Snapshot):
        """A node behind a forbidden node is not reached through it."""
        claim_id = next(n["id"] for n in snap.nodes if n["id"].endswith("#CL-1"))
        assessment = _node("ASSESS-1", "assessment", {"verdict": "synthetic"})
        # A permitted artifact version whose only link is through the assessment.
        behind = _node("ART-BEHIND", "artifact_version", {"kind": "synthetic", "text": "x"})
        nodes = list(snap.nodes) + [assessment, behind]
        extended = _with_extra(
            snap,
            [assessment, behind],
            [
                _edge(nodes, claim_id, "validated_by", "ASSESS-1"),
                _edge(nodes, "ART-BEHIND", "validated_by", "ASSESS-1"),
            ],
        )
        # The chain task <- passage <- claim -> assessment -> artifact is four
        # steps: the change-impact view (depth 4) reaches it, and proves the
        # node is reachable when the assessment is permitted.
        open_view = _pkg(
            extended, view="change_impact_planning", expected_snapshot_id=extended.snapshot_id
        )
        assert "ART-BEHIND" in _included_ids(open_view)
        blind = _pkg(
            extended, view="blind_pre_evaluation", expected_snapshot_id=extended.snapshot_id
        )
        assert {"ASSESS-1", "ART-BEHIND"} & _included_ids(blind) == set()
        assert "ASSESS-1" in _excluded(blind, "policy_forbidden")
        # The node behind the forbidden one was never reached, so it is not
        # even an exclusion: policy runs before expansion, not after.
        assert "ART-BEHIND" not in {e["id"] for e in blind.manifest["exclusions"]}

    def test_a_traversal_the_view_does_not_permit_is_not_followed(self, snap: Snapshot):
        """controlled_revision leaves out validated_by: the milestone behind
        D1.1 -validated_by-> MS1 is excluded, naming the predicate."""
        p = VIEW_POLICIES["controlled_revision"]
        assert "validated_by" not in p.permitted_traversals
        pkg = _pkg(snap, view="controlled_revision")
        assert "D1.1" in _included_ids(pkg)
        assert "MS1" not in _included_ids(pkg)
        ms1 = next(e for e in pkg.manifest["exclusions"] if e["id"] == "MS1")
        assert ms1["reason"] == "policy_forbidden"
        assert ms1["detail"] == "traversal_not_permitted:validated_by"
        assert "MS1" in _included_ids(_pkg(snap, view="engineering"))

    def test_max_depth_bounds_expansion(self, snap: Snapshot):
        pkg = _pkg(snap)
        depth = VIEW_POLICIES["engineering"].max_depth
        assert all(len(i["path"]) <= depth for i in pkg.manifest["included"])



    def test_blind_view_excludes_every_node_derived_from_a_superseded_version(self, tmp_path: Path):
        """A blind package around the new version must not carry the old
        version's passages, claims or commitments, even though the shared
        objective node still links to them. The old version's nodes are
        refused before expansion and recorded as exclusions naming the
        superseded snapshot."""
        root = tmp_path / "repo"
        shutil.copytree(FIXTURE, root)
        first_id, second_id = _supersede(root)
        snap = build_snapshot(root)
        pkg = _pkg(snap, task=second_id, view="blind_pre_evaluation")
        included = _included_ids(pkg)
        assert f"{second_id}#S1" in included
        assert not any(i.startswith(first_id) for i in included), sorted(included)
        stale = [e for e in pkg.manifest["exclusions"] if e["id"].startswith(first_id)]
        assert stale, "the superseded version's nodes are adjacent to the objective; they must be recorded"
        assert {e["reason"] for e in stale} == {"policy_forbidden"}
        assert {e["detail"] for e in stale} == {f"superseded_version:{first_id}"}
        assert not any(i["id"].startswith(first_id) for i in pkg.items)

    def test_a_superseded_version_is_not_a_blind_seed(self, tmp_path: Path):
        root = tmp_path / "repo"
        shutil.copytree(FIXTURE, root)
        first_id, _ = _supersede(root)
        snap = build_snapshot(root)
        with pytest.raises(DevGraphError) as exc:
            _pkg(snap, task=first_id, view="blind_pre_evaluation")
        assert exc.value.kind == "policy_forbidden"
        assert first_id in str(exc.value)

    def test_controlled_revision_still_sees_the_superseded_version(self, tmp_path: Path):
        root = tmp_path / "repo"
        shutil.copytree(FIXTURE, root)
        first_id, second_id = _supersede(root)
        snap = build_snapshot(root)
        pkg = _pkg(snap, task="T03", view="controlled_revision")
        included = _included_ids(pkg)
        assert any(i.startswith(first_id) for i in included), sorted(included)
        assert any(i.startswith(second_id) for i in included), sorted(included)
        assert not any(e["detail"].startswith("superseded_version") for e in pkg.manifest["exclusions"])
        # And the old version can still be a seed under a view that sees it.
        assert first_id in _included_ids(_pkg(snap, task=first_id, view="engineering"))

    def test_a_state_superseded_snapshot_is_hidden_without_an_edge(self, snap: Snapshot):
        """The state field alone marks a version as history."""
        doc = next(n for n in snap.nodes if n["type"] == "artifact_version")
        stale_content = {**doc["content"], "state": "superseded", "content_version": "sha256:" + "1" * 64}
        stale_id = f"{doc['content']['document_id']}@1111111111111111"
        stale = _node(stale_id, "artifact_version", stale_content)
        passage = _node(
            f"{stale_id}#S1",
            "passage",
            {"section_id": "S1", "content": "old", "document": stale_id, "addresses": ["OBJ-1"]},
        )
        nodes = [stale, passage]
        all_nodes = list(snap.nodes) + nodes
        edges = [
            _edge(all_nodes, passage["id"], "expressed_in", stale_id),
            _edge(all_nodes, passage["id"], "addresses", "OBJ-1"),
        ]
        widened = _with_extra(snap, nodes, edges)
        pkg = _pkg(widened, task="OBJ-1", view="blind_pre_evaluation")
        assert not any(i.startswith(stale_id) for i in _included_ids(pkg))
        hit = next(e for e in pkg.manifest["exclusions"] if e["id"] == passage["id"])
        assert hit["detail"] == f"superseded_version:{stale_id}"
        assert passage["id"] in _included_ids(_pkg(widened, task="OBJ-1", view="engineering"))


# --------------------------------------------------------------------------- #
# Budget
# --------------------------------------------------------------------------- #


class TestBudget:
    def test_everything_fits_yields_complete(self, snap: Snapshot):
        pkg = _pkg(snap)
        assert pkg.manifest["completeness"] == "complete"
        assert not _excluded(pkg, "over_budget")

    def test_required_item_over_budget_yields_incomplete_and_is_listed(self, snap: Snapshot):
        pkg = _pkg(snap, budget=1)
        assert pkg.manifest["completeness"] == "incomplete"
        mandatory = {m["id"] for m in pkg.manifest["mandatory_dependencies"]}
        dropped = _excluded(pkg, "over_budget")
        assert mandatory & dropped
        required_dropped = {
            e["id"] for e in pkg.manifest["exclusions"] if e["reason"] == "over_budget" and e["required"]
        }
        assert required_dropped == mandatory & dropped
        issues = [u for u in pkg.manifest["unresolved"] if u["kind"] == "required_over_budget"]
        assert {u["id"] for u in issues} == required_dropped
        # The seed is never dropped: a package that cannot hold its own task
        # is still explicit about what it is for.
        assert "T03" in _included_ids(pkg)

    def test_optional_item_over_budget_is_recorded_and_flips_completeness(self, snap: Snapshot):
        full = _pkg(snap)
        mandatory = {m["id"] for m in full.manifest["mandatory_dependencies"]}
        required_cost = sum(
            i["cost"] for i in full.manifest["included"] if i["id"] in mandatory | {"T03"}
        )
        pkg = _pkg(snap, budget=required_cost)
        assert pkg.manifest["completeness"] == "incomplete"
        assert all(
            not e["required"]
            for e in pkg.manifest["exclusions"]
            if e["reason"] == "over_budget"
        )

    def test_a_seed_larger_than_the_budget_is_included_and_incomplete(self, snap: Snapshot):
        seed_cost = next(i["cost"] for i in _pkg(snap).manifest["included"] if i["id"] == "T03")
        pkg = _pkg(snap, budget=max(1, seed_cost - 1))
        assert "T03" in _included_ids(pkg)
        assert pkg.manifest["completeness"] == "incomplete"
        assert any(u["kind"] == "seed_over_budget" for u in pkg.manifest["unresolved"])

    def test_included_cost_never_exceeds_budget(self, snap: Snapshot):
        full = _pkg(snap)
        total = sum(i["cost"] for i in full.manifest["included"])
        pkg = _pkg(snap, budget=total // 2)
        assert sum(i["cost"] for i in pkg.manifest["included"]) <= total // 2


# --------------------------------------------------------------------------- #
# Stale snapshot
# --------------------------------------------------------------------------- #


class TestStaleSnapshot:
    def test_mismatched_snapshot_id_is_refused(self, snap: Snapshot):
        with pytest.raises(DevGraphError) as exc:
            _pkg(snap, expected_snapshot_id="sha256:" + "0" * 64)
        assert exc.value.kind == "stale_snapshot"
        assert snap.snapshot_id in str(exc.value)

    def test_mismatched_policy_version_is_refused(self, snap: Snapshot):
        with pytest.raises(DevGraphError) as exc:
            _pkg(snap, policy_version="sha256:" + "f" * 64)
        assert exc.value.kind == "stale_policy"


# --------------------------------------------------------------------------- #
# Unresolved claims and contradictions
# --------------------------------------------------------------------------- #


class TestUnresolved:
    def test_unresolved_claims_appear_in_the_unresolved_list(self, snap: Snapshot):
        pkg = _pkg(snap)
        unresolved = [u for u in pkg.manifest["unresolved"] if u["kind"] == "unresolved_claim"]
        assert {u["id"].split("#")[-1] for u in unresolved} == {"CL-4"}
        assert all(u["declared_status"] == "Unresolved" for u in unresolved)

    def test_worst_declared_status_uses_the_shared_severity_table(self, snap: Snapshot):
        from runner.claim_status import worst_status

        pkg = _pkg(snap)
        statuses = [
            i["declared_status"] for i in pkg.manifest["included"] if i["type"] == "claim"
        ]
        assert pkg.manifest["worst_declared_status"] == worst_status(statuses).capitalize()
        assert pkg.manifest["worst_declared_status"] in DECLARED_STATUSES

    def test_packages_module_imports_the_shared_table_not_the_compiler_copy(self):
        import runner.dev_graph.packages as mod

        text = Path(mod.__file__).read_text(encoding="utf-8")
        assert "runner.claim_status" in text
        assert "graph_compiler" not in text
        assert "_CLAIM_STATUS_SEVERITY" not in text

    def test_two_current_versions_of_one_document_are_a_contradiction(self, world: Path):
        cand = _load(world, CANDIDATE)
        cand["sections"][1]["content"] = "Task three is led by Participant C."
        _dump(world, CANDIDATE, cand)
        import_document(world, CANDIDATE, state="draft")
        snap = build_snapshot(world)
        pkg = _pkg(snap)
        contradictions = [u for u in pkg.manifest["unresolved"] if u["kind"] == "contradiction"]
        assert contradictions
        assert any(c["document_id"] == "CAND-1" for c in contradictions)
        assert all(len(c["ids"]) == 2 for c in contradictions)

    def test_approved_but_unresolved_claim_is_a_contradiction(self, world: Path):
        cand = _load(world, CANDIDATE)
        cand["claims"][3]["approval"] = "approved"
        _dump(world, CANDIDATE, cand)
        import_document(world, CANDIDATE, state="draft")
        snap = build_snapshot(world)
        pkg = _pkg(snap)
        contradictions = [u for u in pkg.manifest["unresolved"] if u["kind"] == "contradiction"]
        assert any(c["ids"][0].endswith("#CL-4") for c in contradictions)


# --------------------------------------------------------------------------- #
# Declared status of Tier 3 nodes (not only document claims)
# --------------------------------------------------------------------------- #


class TestTier3DeclaredStatus:
    """A Tier 3 record declares its own §12.2 status in its own field name.

    The manifest's honesty fields were built against document claims. On a real
    world with no candidate yet, every node a package carries is a Tier 3
    record, so a manifest that reads ``declared_status`` alone reports a
    package of Assumed partners and tasks as ``Confirmed``. The lookup is
    declared per node type, never sniffed from the value.
    """

    @pytest.fixture
    def world(self, tmp_path: Path) -> Path:
        """The fixture records with no candidate imported.

        This is the demo world's condition: Tier 3 is populated, Tier 5 is
        empty, so a package carries project records and no document claim at
        all. A manifest that reads claims alone has nothing to report here.
        """
        root = tmp_path / "repo"
        shutil.copytree(FIXTURE, root)
        return root

    def _assumed_partners(self, world: Path) -> None:
        rec = _load(world, PARTNERS_REL)
        for p in rec["partners"]:
            p["participation_status"] = "Assumed"
        _dump(world, PARTNERS_REL, rec)

    def test_the_world_carries_no_claim(self, world: Path):
        snap = build_snapshot(world)
        assert not any(n["type"] == "claim" for n in snap.nodes)

    def test_the_field_name_is_declared_per_node_type(self):
        assert DECLARED_STATUS_FIELDS["participant"] == "participation_status"
        assert DECLARED_STATUS_FIELDS["claim"] == "declared_status"
        assert DECLARED_STATUS_FIELDS["task"] == "validation_status"
        assert set(DECLARED_STATUS_FIELDS) <= NODE_TYPES

    def test_a_value_outside_the_vocabulary_is_no_status(self):
        node = {"type": "task", "content": {"validation_status": {"overall_status": "confirmed"}}}
        assert declared_status(node) is None
        assert declared_status({"type": "task", "content": {}}) is None
        assert declared_status({"type": "source_span", "content": {"status": "Confirmed"}}) is None

    def test_an_assumed_partner_reaches_the_worst_declared_status(self, world: Path):
        self._assumed_partners(world)
        snap = build_snapshot(world)
        pkg = _pkg(snap, expected_snapshot_id=snap.snapshot_id)
        assert any(i["type"] == "participant" for i in pkg.manifest["included"])
        assert pkg.manifest["worst_declared_status"] == "Assumed"

    def test_an_assumed_partner_is_listed_as_unresolved(self, world: Path):
        self._assumed_partners(world)
        snap = build_snapshot(world)
        pkg = _pkg(snap, expected_snapshot_id=snap.snapshot_id)
        listed = {
            u["id"]: u for u in pkg.manifest["unresolved"] if u["kind"] == "declared_status"
        }
        partners = {i["id"] for i in pkg.manifest["included"] if i["type"] == "participant"}
        assert partners and partners <= set(listed)
        assert all(listed[p]["declared_status"] == "Assumed" for p in partners)

    def test_only_included_items_are_listed(self, world: Path):
        self._assumed_partners(world)
        snap = build_snapshot(world)
        pkg = _pkg(snap, expected_snapshot_id=snap.snapshot_id)
        included = {i["id"] for i in pkg.manifest["included"]}
        for u in pkg.manifest["unresolved"]:
            if u["kind"] == "declared_status":
                assert u["id"] in included

    def test_a_confirmed_record_is_not_listed(self, world: Path):
        rec = _load(world, PARTNERS_REL)
        for p in rec["partners"]:
            p["participation_status"] = "Confirmed"
        _dump(world, PARTNERS_REL, rec)
        snap = build_snapshot(world)
        pkg = _pkg(snap, expected_snapshot_id=snap.snapshot_id)
        listed = {u["id"] for u in pkg.manifest["unresolved"] if u["kind"] == "declared_status"}
        partners = {i["id"] for i in pkg.manifest["included"] if i["type"] == "participant"}
        assert partners and not (partners & listed)

    def test_the_item_carries_its_own_declared_status(self, world: Path):
        self._assumed_partners(world)
        snap = build_snapshot(world)
        pkg = _pkg(snap, expected_snapshot_id=snap.snapshot_id)
        for i in pkg.manifest["included"]:
            if i["type"] == "participant":
                assert i["declared_status"] == "Assumed"


class TestDefaultBudget:
    def test_the_default_budget_is_a_declared_positive_constant(self):
        assert isinstance(DEFAULT_PACKAGE_BUDGET, int)
        assert DEFAULT_PACKAGE_BUDGET > 0


# --------------------------------------------------------------------------- #
# Determinism and the registered writer
# --------------------------------------------------------------------------- #


class TestDeterminism:
    def test_two_builds_with_identical_inputs_share_a_package_hash_and_id(self, snap: Snapshot):
        a, b = _pkg(snap), _pkg(snap)
        assert a.manifest == b.manifest
        assert a.manifest["package_hash"] == b.manifest["package_hash"]
        assert a.manifest["package_id"] == b.manifest["package_id"]
        assert a.to_json_bytes() == b.to_json_bytes()

    def test_a_different_view_or_budget_is_a_different_package(self, snap: Snapshot):
        a = _pkg(snap)
        assert a.manifest["package_id"] != _pkg(snap, view="integrity_audit").manifest["package_id"]
        assert a.manifest["package_id"] != _pkg(snap, budget=1).manifest["package_id"]

    def test_manifest_carries_no_wall_clock_field(self, snap: Snapshot):
        text = json.dumps(_pkg(snap).manifest)
        for needle in ("2026-", "_at\"", "timestamp"):
            assert needle not in text


class TestPackageWriterComponent:
    def _request(self, world: Path, snap: Snapshot, **kw) -> None:
        req = {
            "task": "T03",
            "view": "engineering",
            "budget": BIG,
            "project": "SYN-PROJECT",
            "profile_version": "profile-0",
            "policy_version": POLICY_VERSION,
            "snapshot_id": snap.snapshot_id,
        }
        req.update(kw)
        _dump(world, Path(PACKAGE_REQUEST_REL), req)

    def test_registered_and_claude_free(self):
        assert "dev_graph_package_manifest_writer" in COMPONENT_REGISTRY

    def test_byte_equal_replay_through_the_registry(self, world: Path, snap: Snapshot):
        self._request(world, snap)
        rec = invoke_component("dev_graph_package_manifest_writer", "run-1", world)
        assert rec.status == "success", rec.failure_reason
        assert len(rec.outputs_written) == 2
        assert all(p.startswith(PACKAGES_REL) for p in rec.outputs_written)
        manifest_rel = next(p for p in rec.outputs_written if p.endswith("manifest.json"))
        first = (world / manifest_rel).read_bytes()
        package_rel = next(p for p in rec.outputs_written if p.endswith("package.json"))
        first_pkg = (world / package_rel).read_bytes()
        direct = write_package(world)
        assert sorted(p.as_posix() for p in direct) == sorted((world / p).as_posix() for p in rec.outputs_written)
        rec2 = invoke_component("dev_graph_package_manifest_writer", "run-2", world)
        assert rec2.status == "success"
        assert (world / manifest_rel).read_bytes() == first
        assert (world / package_rel).read_bytes() == first_pkg
        manifest = json.loads(first)
        assert manifest["package_id"][len("sha256:"):][:16] in manifest_rel
        assert manifest["snapshot_id"] == snap.snapshot_id

    def test_component_refuses_a_stale_snapshot_id(self, world: Path, snap: Snapshot):
        self._request(world, snap, snapshot_id="sha256:" + "0" * 64)
        rec = invoke_component("dev_graph_package_manifest_writer", "run-1", world)
        assert rec.status == "failure"
        assert "stale_snapshot" in (rec.failure_reason or "")
        assert not (world / PACKAGES_REL).exists()

    def test_component_refuses_a_missing_request(self, world: Path):
        rec = invoke_component("dev_graph_package_manifest_writer", "run-1", world)
        assert rec.status == "failure"
        assert PACKAGE_REQUEST_REL in (rec.failure_reason or "")


# --------------------------------------------------------------------------- #
# Decision log
# --------------------------------------------------------------------------- #


class TestDecisionLog:
    def test_view_policies_entry_exists_and_names_every_view(self):
        log = find_repo_root() / "docs/tier4_orchestration_state/decision_log"
        entries = list(log.glob("dev-graph-view-policies_*.json"))
        assert len(entries) == 1
        rec = json.loads(entries[0].read_text(encoding="utf-8"))
        assert rec["record_type"] == "decision"
        assert set(rec["views"]) == VIEWS
        assert rec["policy_version"] == POLICY_VERSION


class TestAgnosticism:
    def test_lint_covers_the_new_modules(self):
        from runner.agnosticism_lint import lint_generic_layer

        report = lint_generic_layer(find_repo_root())
        scanned = set(report.scanned_files)
        assert {"runner/dev_graph/packages.py", "runner/dev_graph/policies.py"} <= scanned
        assert not [v for v in report.violations if v.path.startswith("runner/dev_graph/")]
