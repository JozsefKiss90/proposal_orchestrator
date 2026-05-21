"""
Tests for runner.dag_scheduler.ManifestGraph (DAG scheduler Step 1).

Covers:
  - ManifestGraph loads successfully from a synthetic minimal manifest
  - node_ids() preserves registry insertion order
  - node with no incoming edges is ready immediately (entry node)
  - linear dependency chain works correctly
  - fork-join shape works correctly
  - additional_condition is enforced correctly
  - non-pending node is NOT ready
  - unknown node ID passed to graph methods raises DAGSchedulerError
  - malformed manifest raises DAGSchedulerError
  - duplicate node IDs raise DAGSchedulerError
  - edge referencing unknown node raises DAGSchedulerError

Node ID reconciliation tests:
  - canonical node IDs used by ManifestGraph match manifest node_registry
  - PHASE_8_NODE_IDS constant matches Phase 8 node IDs from the manifest
  - _extract_node_id returns canonical IDs from gate library evaluated_at values
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any

import pytest
import yaml

from runner.dag_scheduler import DAGSchedulerError, IncomingCondition, ManifestGraph
from runner.run_context import PHASE_8_NODE_IDS, RunContext
from runner.manifest_reader import MANIFEST_REL_PATH


# ---------------------------------------------------------------------------
# Helpers — synthetic manifest builders
# ---------------------------------------------------------------------------


def _write_manifest(tmp_path: Path, data: dict) -> Path:
    """Write *data* as YAML to a manifest file and return its path."""
    path = tmp_path / "manifest.yaml"
    path.write_text(yaml.dump(data, default_flow_style=False), encoding="utf-8")
    return path


def _write_manifest_str(tmp_path: Path, content: str, filename: str = "manifest.yaml") -> Path:
    """Write a raw YAML string to *tmp_path/filename* and return its path."""
    path = tmp_path / filename
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


def _single_node_manifest() -> dict:
    """Minimal manifest with a single node and no edges."""
    return {
        "name": "test",
        "version": "1.1",
        "node_registry": [
            {
                "node_id": "n01_call_analysis",
                "phase_number": 1,
                "exit_gate": "phase_01_gate",
                "terminal": False,
            }
        ],
        "edge_registry": [],
    }


def _linear_two_node_manifest() -> dict:
    """n01 → n02 with one edge."""
    return {
        "name": "test",
        "version": "1.1",
        "node_registry": [
            {
                "node_id": "n01_call_analysis",
                "phase_number": 1,
                "exit_gate": "phase_01_gate",
                "terminal": False,
            },
            {
                "node_id": "n02_concept_refinement",
                "phase_number": 2,
                "exit_gate": "phase_02_gate",
                "terminal": False,
            },
        ],
        "edge_registry": [
            {
                "edge_id": "e01_to_02",
                "from_node": "n01_call_analysis",
                "to_node": "n02_concept_refinement",
                "gate_condition": "phase_01_gate",
            }
        ],
    }


def _fork_join_manifest() -> dict:
    """
    n01 → n02 → n04 (linear)
    n01 → n02 → n03 (fork from n02)
    n03 → n04 and n02 → n04 (join at n04)

    n04 requires both n02 AND n03 released.
    """
    return {
        "name": "test",
        "version": "1.1",
        "node_registry": [
            {"node_id": "n01", "exit_gate": "g01", "terminal": False},
            {"node_id": "n02", "exit_gate": "g02", "terminal": False},
            {"node_id": "n03", "exit_gate": "g03", "terminal": False},
            {"node_id": "n04", "exit_gate": "g04", "terminal": True},
        ],
        "edge_registry": [
            {
                "edge_id": "e01",
                "from_node": "n01",
                "to_node": "n02",
                "gate_condition": "g01",
            },
            {
                "edge_id": "e02",
                "from_node": "n02",
                "to_node": "n03",
                "gate_condition": "g02",
            },
            {
                "edge_id": "e03",
                "from_node": "n02",
                "to_node": "n04",
                "gate_condition": "g02",
            },
            {
                "edge_id": "e04",
                "from_node": "n03",
                "to_node": "n04",
                "gate_condition": "g03",
            },
        ],
    }


def _additional_condition_manifest() -> dict:
    """
    n01 → n02 (primary)
    n01 → n03 (with additional_condition from n02's gate)
    n02 → n03 (explicit edge providing the additional_condition source)

    n03 requires BOTH n01 AND n02 released.
    The additional_condition on the n01→n03 edge points to n02's gate (g02).
    """
    return {
        "name": "test",
        "version": "1.1",
        "node_registry": [
            {"node_id": "n01", "exit_gate": "g01", "terminal": False},
            {"node_id": "n02", "exit_gate": "g02", "terminal": False},
            {"node_id": "n03", "exit_gate": "g03", "terminal": True},
        ],
        "edge_registry": [
            {
                "edge_id": "e01_to_02",
                "from_node": "n01",
                "to_node": "n02",
                "gate_condition": "g01",
            },
            {
                "edge_id": "e01_to_03",
                "from_node": "n01",
                "to_node": "n03",
                "gate_condition": "g01",
                "additional_condition": "g02",
            },
            {
                "edge_id": "e02_to_03",
                "from_node": "n02",
                "to_node": "n03",
                "gate_condition": "g02",
            },
        ],
    }


def _make_ctx(tmp_path: Path, run_id: str = "test-run") -> RunContext:
    """Create a fresh RunContext in *tmp_path*."""
    return RunContext.initialize(tmp_path, run_id)


# ---------------------------------------------------------------------------
# 1. Load from a synthetic minimal manifest
# ---------------------------------------------------------------------------


class TestManifestGraphLoad:
    def test_load_from_explicit_path(self, tmp_path: Path) -> None:
        path = _write_manifest(tmp_path, _single_node_manifest())
        graph = ManifestGraph.load(path)
        assert "n01_call_analysis" in graph.node_ids()

    def test_load_from_repo_root(self, tmp_path: Path) -> None:
        data = _single_node_manifest()
        manifest_path = tmp_path / MANIFEST_REL_PATH
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            yaml.dump(data, default_flow_style=False), encoding="utf-8"
        )
        graph = ManifestGraph.load(repo_root=tmp_path)
        assert "n01_call_analysis" in graph.node_ids()

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(DAGSchedulerError, match="not found"):
            ManifestGraph.load(tmp_path / "nonexistent.yaml")

    def test_load_invalid_yaml_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.yaml"
        bad.write_text(": invalid: yaml: [unclosed", encoding="utf-8")
        with pytest.raises(DAGSchedulerError, match="Invalid YAML"):
            ManifestGraph.load(bad)

    def test_load_non_dict_root_raises(self, tmp_path: Path) -> None:
        bad = _write_manifest_str(tmp_path, "- just\n- a\n- list\n")
        with pytest.raises(DAGSchedulerError, match="mapping"):
            ManifestGraph.load(bad)

    def test_load_str_path_accepted(self, tmp_path: Path) -> None:
        path = _write_manifest(tmp_path, _single_node_manifest())
        graph = ManifestGraph.load(str(path))
        assert len(graph.node_ids()) == 1


# ---------------------------------------------------------------------------
# 2. node_ids() preserves registry insertion order
# ---------------------------------------------------------------------------


class TestNodeIdsOrder:
    def test_order_matches_registry(self, tmp_path: Path) -> None:
        data = {
            "name": "test",
            "version": "1.1",
            "node_registry": [
                {"node_id": "n_alpha", "terminal": False},
                {"node_id": "n_beta", "terminal": False},
                {"node_id": "n_gamma", "terminal": True},
            ],
            "edge_registry": [],
        }
        graph = ManifestGraph.load(_write_manifest(tmp_path, data))
        assert graph.node_ids() == ["n_alpha", "n_beta", "n_gamma"]

    def test_node_ids_returns_copy(self, tmp_path: Path) -> None:
        graph = ManifestGraph.load(_write_manifest(tmp_path, _single_node_manifest()))
        ids = graph.node_ids()
        ids.append("injected")
        assert "injected" not in graph.node_ids()


# ---------------------------------------------------------------------------
# 3. Node with no incoming edges is ready immediately
# ---------------------------------------------------------------------------


class TestEntryNodeReadiness:
    def test_entry_node_ready_when_pending(self, tmp_path: Path) -> None:
        graph = ManifestGraph.load(_write_manifest(tmp_path, _single_node_manifest()))
        ctx = _make_ctx(tmp_path)
        assert graph.is_ready("n01_call_analysis", ctx) is True

    def test_entry_node_no_incoming_conditions(self, tmp_path: Path) -> None:
        graph = ManifestGraph.load(_write_manifest(tmp_path, _single_node_manifest()))
        assert graph.incoming_conditions("n01_call_analysis") == []


# ---------------------------------------------------------------------------
# 4. Linear dependency chain
# ---------------------------------------------------------------------------


class TestLinearChain:
    def test_downstream_not_ready_until_upstream_released(
        self, tmp_path: Path
    ) -> None:
        graph = ManifestGraph.load(
            _write_manifest(tmp_path, _linear_two_node_manifest())
        )
        ctx = _make_ctx(tmp_path)
        # n02 is not ready while n01 is still pending
        assert graph.is_ready("n02_concept_refinement", ctx) is False

    def test_downstream_ready_after_upstream_released(
        self, tmp_path: Path
    ) -> None:
        graph = ManifestGraph.load(
            _write_manifest(tmp_path, _linear_two_node_manifest())
        )
        ctx = _make_ctx(tmp_path)
        ctx.set_node_state("n01_call_analysis", "released")
        assert graph.is_ready("n02_concept_refinement", ctx) is True

    def test_n01_still_ready_when_n02_pending(self, tmp_path: Path) -> None:
        graph = ManifestGraph.load(
            _write_manifest(tmp_path, _linear_two_node_manifest())
        )
        ctx = _make_ctx(tmp_path)
        assert graph.is_ready("n01_call_analysis", ctx) is True

    def test_incoming_conditions_of_downstream_node(self, tmp_path: Path) -> None:
        graph = ManifestGraph.load(
            _write_manifest(tmp_path, _linear_two_node_manifest())
        )
        conds = graph.incoming_conditions("n02_concept_refinement")
        assert len(conds) == 1
        assert conds[0] == IncomingCondition(
            gate_id="phase_01_gate", source_node_id="n01_call_analysis"
        )


# ---------------------------------------------------------------------------
# 5. Fork-join shape
# ---------------------------------------------------------------------------


class TestForkJoin:
    def _load(self, tmp_path: Path) -> ManifestGraph:
        return ManifestGraph.load(_write_manifest(tmp_path, _fork_join_manifest()))

    def test_n04_not_ready_until_both_n02_and_n03_released(
        self, tmp_path: Path
    ) -> None:
        graph = self._load(tmp_path)
        ctx = _make_ctx(tmp_path)
        ctx.set_node_state("n02", "released")
        # n03 still pending → n04 not ready
        assert graph.is_ready("n04", ctx) is False

    def test_n04_not_ready_with_only_n03_released(self, tmp_path: Path) -> None:
        graph = self._load(tmp_path)
        ctx = _make_ctx(tmp_path)
        ctx.set_node_state("n03", "released")
        assert graph.is_ready("n04", ctx) is False

    def test_n04_ready_when_both_n02_and_n03_released(
        self, tmp_path: Path
    ) -> None:
        graph = self._load(tmp_path)
        ctx = _make_ctx(tmp_path)
        ctx.set_node_state("n02", "released")
        ctx.set_node_state("n03", "released")
        assert graph.is_ready("n04", ctx) is True

    def test_n03_ready_after_n02_released(self, tmp_path: Path) -> None:
        graph = self._load(tmp_path)
        ctx = _make_ctx(tmp_path)
        ctx.set_node_state("n02", "released")
        assert graph.is_ready("n03", ctx) is True

    def test_n04_incoming_conditions_count(self, tmp_path: Path) -> None:
        graph = self._load(tmp_path)
        # Two edges arrive at n04: e03 (from n02) and e04 (from n03)
        conds = graph.incoming_conditions("n04")
        assert len(conds) == 2
        sources = {c.source_node_id for c in conds}
        assert sources == {"n02", "n03"}


# ---------------------------------------------------------------------------
# 6. additional_condition is enforced correctly
# ---------------------------------------------------------------------------


class TestAdditionalCondition:
    def _load(self, tmp_path: Path) -> ManifestGraph:
        return ManifestGraph.load(
            _write_manifest(tmp_path, _additional_condition_manifest())
        )

    def test_n03_not_ready_with_only_n01_released(self, tmp_path: Path) -> None:
        graph = self._load(tmp_path)
        ctx = _make_ctx(tmp_path)
        ctx.set_node_state("n01", "released")
        # n02 still pending — additional_condition not satisfied
        assert graph.is_ready("n03", ctx) is False

    def test_n03_not_ready_with_only_n02_released(self, tmp_path: Path) -> None:
        graph = self._load(tmp_path)
        ctx = _make_ctx(tmp_path)
        ctx.set_node_state("n02", "released")
        # n01 still pending — primary condition on e01_to_03 not satisfied
        assert graph.is_ready("n03", ctx) is False

    def test_n03_ready_when_both_n01_and_n02_released(
        self, tmp_path: Path
    ) -> None:
        graph = self._load(tmp_path)
        ctx = _make_ctx(tmp_path)
        ctx.set_node_state("n01", "released")
        ctx.set_node_state("n02", "released")
        assert graph.is_ready("n03", ctx) is True

    def test_additional_condition_source_resolved_to_exit_gate_producer(
        self, tmp_path: Path
    ) -> None:
        """
        The additional_condition 'g02' must resolve to n02 (which has exit_gate g02),
        not to n01 (the from_node of e01_to_03).
        """
        graph = self._load(tmp_path)
        conds = graph.incoming_conditions("n03")
        additional_conds = [c for c in conds if c.gate_id == "g02"]
        # At least one condition referencing g02 should exist
        assert any(c.source_node_id == "n02" for c in additional_conds), (
            f"Expected g02 additional_condition to resolve to n02; got: {conds!r}"
        )

    def test_n03_incoming_conditions_include_additional(
        self, tmp_path: Path
    ) -> None:
        graph = self._load(tmp_path)
        conds = graph.incoming_conditions("n03")
        gate_ids = [c.gate_id for c in conds]
        # g01 from e01_to_03 primary, g02 from both e01_to_03 additional and e02_to_03 primary
        assert "g01" in gate_ids
        assert "g02" in gate_ids


# ---------------------------------------------------------------------------
# 7. Non-pending node is not ready
# ---------------------------------------------------------------------------


class TestNonPendingNodeNotReady:
    def test_released_node_is_not_ready(self, tmp_path: Path) -> None:
        graph = ManifestGraph.load(_write_manifest(tmp_path, _single_node_manifest()))
        ctx = _make_ctx(tmp_path)
        ctx.set_node_state("n01_call_analysis", "released")
        assert graph.is_ready("n01_call_analysis", ctx) is False

    def test_blocked_at_entry_is_not_ready(self, tmp_path: Path) -> None:
        graph = ManifestGraph.load(_write_manifest(tmp_path, _single_node_manifest()))
        ctx = _make_ctx(tmp_path)
        ctx.set_node_state("n01_call_analysis", "blocked_at_entry")
        assert graph.is_ready("n01_call_analysis", ctx) is False

    def test_blocked_at_exit_is_not_ready(self, tmp_path: Path) -> None:
        graph = ManifestGraph.load(_write_manifest(tmp_path, _single_node_manifest()))
        ctx = _make_ctx(tmp_path)
        ctx.set_node_state("n01_call_analysis", "blocked_at_exit")
        assert graph.is_ready("n01_call_analysis", ctx) is False

    def test_running_is_not_ready(self, tmp_path: Path) -> None:
        graph = ManifestGraph.load(_write_manifest(tmp_path, _single_node_manifest()))
        ctx = _make_ctx(tmp_path)
        ctx.set_node_state("n01_call_analysis", "running")
        assert graph.is_ready("n01_call_analysis", ctx) is False

    def test_hard_block_upstream_is_not_ready(self, tmp_path: Path) -> None:
        graph = ManifestGraph.load(_write_manifest(tmp_path, _single_node_manifest()))
        ctx = _make_ctx(tmp_path)
        ctx.set_node_state("n01_call_analysis", "hard_block_upstream")
        assert graph.is_ready("n01_call_analysis", ctx) is False


# ---------------------------------------------------------------------------
# 8. Unknown node ID raises DAGSchedulerError
# ---------------------------------------------------------------------------


class TestUnknownNodeRaises:
    def _load(self, tmp_path: Path) -> ManifestGraph:
        return ManifestGraph.load(_write_manifest(tmp_path, _single_node_manifest()))

    def test_entry_gate_unknown_node_raises(self, tmp_path: Path) -> None:
        graph = self._load(tmp_path)
        with pytest.raises(DAGSchedulerError, match="Unknown node_id"):
            graph.entry_gate("nonexistent_node")

    def test_exit_gate_unknown_node_raises(self, tmp_path: Path) -> None:
        graph = self._load(tmp_path)
        with pytest.raises(DAGSchedulerError, match="Unknown node_id"):
            graph.exit_gate("nonexistent_node")

    def test_is_terminal_unknown_node_raises(self, tmp_path: Path) -> None:
        graph = self._load(tmp_path)
        with pytest.raises(DAGSchedulerError, match="Unknown node_id"):
            graph.is_terminal("nonexistent_node")

    def test_incoming_conditions_unknown_node_raises(self, tmp_path: Path) -> None:
        graph = self._load(tmp_path)
        with pytest.raises(DAGSchedulerError, match="Unknown node_id"):
            graph.incoming_conditions("nonexistent_node")

    def test_is_ready_unknown_node_raises(self, tmp_path: Path) -> None:
        graph = self._load(tmp_path)
        ctx = _make_ctx(tmp_path)
        with pytest.raises(DAGSchedulerError, match="Unknown node_id"):
            graph.is_ready("nonexistent_node", ctx)


# ---------------------------------------------------------------------------
# 9. Malformed manifest raises DAGSchedulerError
# ---------------------------------------------------------------------------


class TestMalformedManifest:
    def test_missing_node_registry_raises(self, tmp_path: Path) -> None:
        data = {"name": "test", "edge_registry": []}
        with pytest.raises(DAGSchedulerError, match="node_registry"):
            ManifestGraph.load(_write_manifest(tmp_path, data))

    def test_missing_edge_registry_raises(self, tmp_path: Path) -> None:
        data = {
            "name": "test",
            "node_registry": [{"node_id": "n01", "terminal": False}],
        }
        with pytest.raises(DAGSchedulerError, match="edge_registry"):
            ManifestGraph.load(_write_manifest(tmp_path, data))

    def test_non_list_node_registry_raises(self, tmp_path: Path) -> None:
        data = {"name": "test", "node_registry": {"n01": {}}, "edge_registry": []}
        with pytest.raises(DAGSchedulerError, match="node_registry"):
            ManifestGraph.load(_write_manifest(tmp_path, data))

    def test_non_list_edge_registry_raises(self, tmp_path: Path) -> None:
        data = {
            "name": "test",
            "node_registry": [{"node_id": "n01", "terminal": False}],
            "edge_registry": "not a list",
        }
        with pytest.raises(DAGSchedulerError, match="edge_registry"):
            ManifestGraph.load(_write_manifest(tmp_path, data))

    def test_node_without_node_id_raises(self, tmp_path: Path) -> None:
        data = {
            "name": "test",
            "node_registry": [{"phase_number": 1, "terminal": False}],
            "edge_registry": [],
        }
        with pytest.raises(DAGSchedulerError, match="node_id"):
            ManifestGraph.load(_write_manifest(tmp_path, data))

    def test_edge_without_from_node_raises(self, tmp_path: Path) -> None:
        data = {
            "name": "test",
            "node_registry": [{"node_id": "n01", "terminal": False}],
            "edge_registry": [
                {"edge_id": "e01", "to_node": "n01", "gate_condition": "g01"}
            ],
        }
        with pytest.raises(DAGSchedulerError, match="from_node"):
            ManifestGraph.load(_write_manifest(tmp_path, data))

    def test_edge_without_to_node_raises(self, tmp_path: Path) -> None:
        data = {
            "name": "test",
            "node_registry": [{"node_id": "n01", "terminal": False}],
            "edge_registry": [
                {"edge_id": "e01", "from_node": "n01", "gate_condition": "g01"}
            ],
        }
        with pytest.raises(DAGSchedulerError, match="to_node"):
            ManifestGraph.load(_write_manifest(tmp_path, data))


# ---------------------------------------------------------------------------
# 10. Duplicate node IDs raise DAGSchedulerError
# ---------------------------------------------------------------------------


class TestDuplicateNodeIds:
    def test_duplicate_node_id_raises(self, tmp_path: Path) -> None:
        data = {
            "name": "test",
            "version": "1.1",
            "node_registry": [
                {"node_id": "n01_call_analysis", "terminal": False},
                {"node_id": "n01_call_analysis", "terminal": False},  # duplicate
            ],
            "edge_registry": [],
        }
        with pytest.raises(DAGSchedulerError, match="Duplicate node_id"):
            ManifestGraph.load(_write_manifest(tmp_path, data))


# ---------------------------------------------------------------------------
# 11. Edge referencing unknown node raises DAGSchedulerError
# ---------------------------------------------------------------------------


class TestEdgeUnknownNode:
    def test_unknown_from_node_raises(self, tmp_path: Path) -> None:
        data = {
            "name": "test",
            "version": "1.1",
            "node_registry": [{"node_id": "n02", "terminal": False}],
            "edge_registry": [
                {
                    "edge_id": "e01",
                    "from_node": "n01_does_not_exist",
                    "to_node": "n02",
                    "gate_condition": "g01",
                }
            ],
        }
        with pytest.raises(DAGSchedulerError, match="unknown from_node"):
            ManifestGraph.load(_write_manifest(tmp_path, data))

    def test_unknown_to_node_raises(self, tmp_path: Path) -> None:
        data = {
            "name": "test",
            "version": "1.1",
            "node_registry": [{"node_id": "n01", "terminal": False}],
            "edge_registry": [
                {
                    "edge_id": "e01",
                    "from_node": "n01",
                    "to_node": "n99_does_not_exist",
                    "gate_condition": "g01",
                }
            ],
        }
        with pytest.raises(DAGSchedulerError, match="unknown to_node"):
            ManifestGraph.load(_write_manifest(tmp_path, data))


# ---------------------------------------------------------------------------
# Node ID reconciliation tests (Step 1 requirement)
# ---------------------------------------------------------------------------


class TestNodeIdReconciliation:
    """
    Prove that canonical node IDs are consistent across:
    - ManifestGraph (reads manifest.compile.yaml)
    - RunContext / PHASE_8_NODE_IDS
    - gate_evaluator._extract_node_id (reads gate library evaluated_at)
    """

    def test_phase8_node_ids_match_manifest_node_registry(self) -> None:
        """
        PHASE_8_NODE_IDS must exactly match the Phase 8 node_id values in
        manifest.compile.yaml.  This is the canonical HARD_BLOCK list.
        """
        # Load the actual production manifest
        from runner.paths import find_repo_root
        try:
            repo_root = find_repo_root()
        except RuntimeError:
            pytest.skip("repo root not discoverable in this environment")

        manifest_path = repo_root / MANIFEST_REL_PATH
        if not manifest_path.exists():
            pytest.skip("manifest.compile.yaml not present")

        graph = ManifestGraph.load(manifest_path)
        manifest_phase8_ids = {
            nid for nid in graph.node_ids()
            if nid.startswith("n08")
        }
        assert manifest_phase8_ids == PHASE_8_NODE_IDS, (
            f"PHASE_8_NODE_IDS {PHASE_8_NODE_IDS!r} does not match "
            f"manifest Phase 8 node IDs {manifest_phase8_ids!r}"
        )

    def test_manifest_graph_node_ids_are_canonical(self, tmp_path: Path) -> None:
        """
        ManifestGraph.node_ids() returns the canonical IDs from the manifest,
        not short aliases.
        """
        data = {
            "name": "test",
            "version": "1.1",
            "node_registry": [
                {"node_id": "n01_call_analysis", "terminal": False},
                {"node_id": "n08a_excellence_drafting", "terminal": False},
            ],
            "edge_registry": [],
        }
        graph = ManifestGraph.load(_write_manifest(tmp_path, data))
        ids = graph.node_ids()
        assert "n01_call_analysis" in ids
        assert "n08a_excellence_drafting" in ids
        # Short aliases must NOT appear
        assert "n01" not in ids
        assert "n08a" not in ids

    def test_run_context_stores_canonical_ids(self, tmp_path: Path) -> None:
        """
        RunContext stores whatever node_id string is passed to set_node_state.
        After reconciliation, the canonical IDs must be used.
        """
        ctx = RunContext.initialize(tmp_path, "run-canonical")
        ctx.set_node_state("n01_call_analysis", "released")
        ctx.set_node_state("n08a_excellence_drafting", "running")
        ctx.save()

        reloaded = RunContext.load(tmp_path, "run-canonical")
        assert reloaded.get_node_state("n01_call_analysis") == "released"
        assert reloaded.get_node_state("n08a_excellence_drafting") == "running"
        # Short alias returns the default ("pending") — it is a different key
        assert reloaded.get_node_state("n01") == "pending"

    def test_phase8_node_ids_are_canonical_form(self) -> None:
        """
        PHASE_8_NODE_IDS must use canonical full-form IDs, not short aliases.
        This is the definitive post-reconciliation assertion.
        """
        expected = frozenset(
            {
                "n08a_excellence_drafting",
                "n08b_impact_drafting",
                "n08c_implementation_drafting",
                "n08d_assembly",
                "n08e_evaluator_review",
                "n08f_revision",
            }
        )
        assert PHASE_8_NODE_IDS == expected

    def test_extract_node_id_returns_canonical_from_evaluated_at(self) -> None:
        """
        _extract_node_id() splits on whitespace and takes the first token.
        With the reconciled gate library entries (e.g. 'n01_call_analysis entry'),
        it now returns the canonical node ID.
        """
        from runner.gate_evaluator import _extract_node_id

        assert _extract_node_id("n01_call_analysis entry") == "n01_call_analysis"
        assert _extract_node_id("n01_call_analysis exit") == "n01_call_analysis"
        assert _extract_node_id("n02_concept_refinement exit") == "n02_concept_refinement"
        assert _extract_node_id("n03_wp_design exit") == "n03_wp_design"
        assert _extract_node_id("n04_gantt_milestones exit") == "n04_gantt_milestones"
        assert _extract_node_id("n05_impact_architecture exit") == "n05_impact_architecture"
        assert _extract_node_id("n06_implementation_architecture exit") == "n06_implementation_architecture"
        assert _extract_node_id("n07_budget_gate exit") == "n07_budget_gate"
        assert _extract_node_id("n08a_excellence_drafting exit") == "n08a_excellence_drafting"
        assert _extract_node_id("n08b_impact_drafting exit") == "n08b_impact_drafting"
        assert _extract_node_id("n08c_implementation_drafting exit") == "n08c_implementation_drafting"
        assert _extract_node_id("n08d_assembly exit") == "n08d_assembly"
        assert _extract_node_id("n08e_evaluator_review exit") == "n08e_evaluator_review"
        assert _extract_node_id("n08f_revision exit") == "n08f_revision"

    def test_hard_block_sets_canonical_phase8_ids_in_run_context(
        self, tmp_path: Path
    ) -> None:
        """
        mark_hard_block_downstream() must set the CANONICAL Phase 8 node IDs
        to 'hard_block_upstream', not the short aliases.
        """
        ctx = RunContext.initialize(tmp_path, "run-hb")
        ctx.mark_hard_block_downstream()

        for canonical_id in PHASE_8_NODE_IDS:
            assert ctx.get_node_state(canonical_id) == "hard_block_upstream", (
                f"Expected hard_block_upstream for {canonical_id!r}"
            )

        # Short-form aliases must NOT be set
        for short_id in ("n08a", "n08b", "n08c", "n08d", "n08e", "n08f"):
            assert ctx.get_node_state(short_id) == "pending", (
                f"Short alias {short_id!r} should remain pending (not be set)"
            )

    def test_gate_library_evaluated_at_uses_canonical_ids(self) -> None:
        """
        The production gate_rules_library.yaml must use canonical node IDs
        in all 'evaluated_at' fields, not short aliases.
        """
        from runner.paths import find_repo_root
        import yaml as _yaml

        try:
            repo_root = find_repo_root()
        except RuntimeError:
            pytest.skip("repo root not discoverable in this environment")

        lib_path = (
            repo_root
            / ".claude/workflows/system_orchestration/gate_rules_library.yaml"
        )
        if not lib_path.exists():
            pytest.skip("gate_rules_library.yaml not present")

        data = _yaml.safe_load(lib_path.read_text(encoding="utf-8"))
        short_form_found = []
        for gate in data.get("gate_rules", []):
            evaluated_at = gate.get("evaluated_at", "")
            node_part = evaluated_at.split()[0] if evaluated_at else ""
            # A short-form ID has the form "nXX" (2 digits, no underscore suffix)
            import re
            if re.match(r"^n\d{2}[a-f]?$", node_part):
                short_form_found.append(
                    f"{gate['gate_id']}: evaluated_at={evaluated_at!r}"
                )
        assert short_form_found == [], (
            "Found short-form node IDs in gate_rules_library.yaml evaluated_at "
            f"fields (should be canonical): {short_form_found}"
        )


# ---------------------------------------------------------------------------
# Additional graph method tests
# ---------------------------------------------------------------------------


class TestGraphMethods:
    def test_entry_gate_returned(self, tmp_path: Path) -> None:
        data = {
            "name": "test",
            "version": "1.1",
            "node_registry": [
                {
                    "node_id": "n01_call_analysis",
                    "entry_gate": "gate_01_source_integrity",
                    "exit_gate": "phase_01_gate",
                    "terminal": False,
                }
            ],
            "edge_registry": [],
        }
        graph = ManifestGraph.load(_write_manifest(tmp_path, data))
        assert graph.entry_gate("n01_call_analysis") == "gate_01_source_integrity"

    def test_entry_gate_none_when_absent(self, tmp_path: Path) -> None:
        graph = ManifestGraph.load(_write_manifest(tmp_path, _single_node_manifest()))
        assert graph.entry_gate("n01_call_analysis") is None

    def test_exit_gate_returned(self, tmp_path: Path) -> None:
        graph = ManifestGraph.load(_write_manifest(tmp_path, _single_node_manifest()))
        assert graph.exit_gate("n01_call_analysis") == "phase_01_gate"

    def test_exit_gate_none_when_absent(self, tmp_path: Path) -> None:
        data = {
            "name": "test",
            "version": "1.1",
            "node_registry": [{"node_id": "n01", "terminal": True}],
            "edge_registry": [],
        }
        graph = ManifestGraph.load(_write_manifest(tmp_path, data))
        assert graph.exit_gate("n01") is None

    def test_is_terminal_true(self, tmp_path: Path) -> None:
        data = {
            "name": "test",
            "version": "1.1",
            "node_registry": [
                {"node_id": "n01", "terminal": False},
                {"node_id": "n02", "terminal": True},
            ],
            "edge_registry": [],
        }
        graph = ManifestGraph.load(_write_manifest(tmp_path, data))
        assert graph.is_terminal("n02") is True
        assert graph.is_terminal("n01") is False

    def test_is_terminal_defaults_to_false(self, tmp_path: Path) -> None:
        data = {
            "name": "test",
            "version": "1.1",
            "node_registry": [{"node_id": "n01"}],
            "edge_registry": [],
        }
        graph = ManifestGraph.load(_write_manifest(tmp_path, data))
        assert graph.is_terminal("n01") is False

    def test_incoming_conditions_returns_copy(self, tmp_path: Path) -> None:
        graph = ManifestGraph.load(
            _write_manifest(tmp_path, _linear_two_node_manifest())
        )
        conds = graph.incoming_conditions("n02_concept_refinement")
        original_len = len(conds)
        conds.append(IncomingCondition("extra_gate", "extra_node"))
        assert len(graph.incoming_conditions("n02_concept_refinement")) == original_len
