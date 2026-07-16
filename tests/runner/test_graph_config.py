"""
Tests for runner.graph_config — the graph.config.yaml binding contract.

Covers happy-path loading, binding resolution (folder-prefix / node_type /
wildcard / first-match-wins), source-only bindings, vault_dir resolution, and
fail-closed validation (naming the offending binding).  All fixtures are written
to tmp_path — no real repository files are read.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from runner.graph_config import (
    Binding,
    GraphConfig,
    GraphConfigError,
    load_graph_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


_VALID = """\
project_id: toy-instance
vault_path: nodes
bindings:
  - match:
      node_type: proposal_section
    tier: tier5
    artifact_path: docs/tier5_deliverables/proposal_sections
  - match:
      folder: "04_methodological_routes"
    tier: tier3
  - match:
      node_type: objective
      folder: "11_objectives"
    tier: tier3
    artifact_path: docs/tier3_project_instantiation/architecture_inputs/objectives.json
"""


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_load_valid_config(tmp_path):
    cfg = load_graph_config(_write(tmp_path / "graph.config.yaml", _VALID))
    assert cfg.project_id == "toy-instance"
    assert cfg.vault_path == "nodes"
    assert len(cfg.bindings) == 3
    assert cfg.source_path == (tmp_path / "graph.config.yaml").resolve()


def test_source_only_binding_has_no_artifact_path(tmp_path):
    cfg = load_graph_config(_write(tmp_path / "graph.config.yaml", _VALID))
    routes = cfg.bindings[1]
    assert routes.match_folder == "04_methodological_routes"
    assert routes.tier == "tier3"
    assert routes.artifact_path is None  # source-only


def test_resolve_vault_dir_with_vault_path(tmp_path):
    cfg = load_graph_config(_write(tmp_path / "graph.config.yaml", _VALID))
    assert cfg.resolve_vault_dir() == (tmp_path / "nodes")


def test_resolve_vault_dir_without_vault_path(tmp_path):
    text = "project_id: x\nbindings:\n  - match: {node_type: concept}\n    tier: tier3\n"
    cfg = load_graph_config(_write(tmp_path / "graph.config.yaml", text))
    assert cfg.vault_path is None
    assert cfg.resolve_vault_dir() == tmp_path


# ---------------------------------------------------------------------------
# Binding.matches / GraphConfig.resolve
# ---------------------------------------------------------------------------


def test_binding_matches_node_type_only():
    b = Binding(tier="tier5", match_node_type="proposal_section")
    assert b.matches("anywhere", "proposal_section")
    assert not b.matches("anywhere", "concept")


def test_binding_matches_folder_prefix():
    b = Binding(tier="tier3", match_folder="04_routes")
    assert b.matches("04_routes", "anything")
    assert b.matches("04_routes/sub", "anything")  # prefix
    assert not b.matches("04_routes_other", "anything")  # not a path-prefix
    assert not b.matches("05_other", "anything")


def test_binding_matches_requires_all_present_selectors():
    b = Binding(tier="tier3", match_folder="11_obj", match_node_type="objective")
    assert b.matches("11_obj", "objective")
    assert not b.matches("11_obj", "concept")  # node_type mismatch
    assert not b.matches("12_other", "objective")  # folder mismatch


def test_binding_wildcard_when_no_selector_on_that_axis():
    b = Binding(tier="tier3", match_node_type="risk")
    # folder axis is a wildcard
    assert b.matches("07_risks", "risk")
    assert b.matches("somewhere/else", "risk")


def test_resolve_first_match_wins(tmp_path):
    cfg = load_graph_config(_write(tmp_path / "graph.config.yaml", _VALID))
    # a proposal_section node in 04_methodological_routes matches binding[0] first
    b = cfg.resolve("04_methodological_routes", "proposal_section")
    assert b is not None
    assert b.tier == "tier5"
    assert b.artifact_path == "docs/tier5_deliverables/proposal_sections"


def test_resolve_returns_none_when_no_binding_matches(tmp_path):
    cfg = load_graph_config(_write(tmp_path / "graph.config.yaml", _VALID))
    assert cfg.resolve("99_governance", "governance") is None


# ---------------------------------------------------------------------------
# Fail closed — file / root
# ---------------------------------------------------------------------------


def test_missing_file_fails_closed(tmp_path):
    with pytest.raises(GraphConfigError, match="not found"):
        load_graph_config(tmp_path / "nope.yaml")


def test_empty_file_fails_closed(tmp_path):
    with pytest.raises(GraphConfigError, match="empty"):
        load_graph_config(_write(tmp_path / "graph.config.yaml", "   \n"))


def test_malformed_yaml_fails_closed(tmp_path):
    with pytest.raises(GraphConfigError, match="not valid YAML"):
        load_graph_config(_write(tmp_path / "graph.config.yaml", "project_id: [unclosed\n"))


def test_non_mapping_root_fails_closed(tmp_path):
    with pytest.raises(GraphConfigError, match="not a mapping"):
        load_graph_config(_write(tmp_path / "graph.config.yaml", "- a\n- b\n"))


# ---------------------------------------------------------------------------
# Fail closed — project_id / bindings list
# ---------------------------------------------------------------------------


def test_missing_project_id_fails_closed(tmp_path):
    text = "bindings:\n  - match: {node_type: concept}\n    tier: tier3\n"
    with pytest.raises(GraphConfigError, match="project_id"):
        load_graph_config(_write(tmp_path / "graph.config.yaml", text))


def test_blank_project_id_fails_closed(tmp_path):
    text = "project_id: '   '\nbindings:\n  - match: {node_type: concept}\n    tier: tier3\n"
    with pytest.raises(GraphConfigError, match="project_id"):
        load_graph_config(_write(tmp_path / "graph.config.yaml", text))


def test_empty_bindings_fails_closed(tmp_path):
    text = "project_id: x\nbindings: []\n"
    with pytest.raises(GraphConfigError, match="bindings"):
        load_graph_config(_write(tmp_path / "graph.config.yaml", text))


def test_missing_bindings_fails_closed(tmp_path):
    with pytest.raises(GraphConfigError, match="bindings"):
        load_graph_config(_write(tmp_path / "graph.config.yaml", "project_id: x\n"))


def test_vault_path_wrong_type_fails_closed(tmp_path):
    text = "project_id: x\nvault_path: 123\nbindings:\n  - match: {node_type: concept}\n    tier: tier3\n"
    with pytest.raises(GraphConfigError, match="vault_path"):
        load_graph_config(_write(tmp_path / "graph.config.yaml", text))


# ---------------------------------------------------------------------------
# Fail closed — individual bindings (naming the index)
# ---------------------------------------------------------------------------


def test_binding_missing_tier_fails_closed(tmp_path):
    text = "project_id: x\nbindings:\n  - match: {node_type: concept}\n"
    with pytest.raises(GraphConfigError) as exc:
        load_graph_config(_write(tmp_path / "graph.config.yaml", text))
    assert "bindings[0]" in str(exc.value)
    assert "tier" in str(exc.value)


def test_binding_invalid_tier_fails_closed(tmp_path):
    text = "project_id: x\nbindings:\n  - match: {node_type: concept}\n    tier: tier99\n"
    with pytest.raises(GraphConfigError, match="tier99"):
        load_graph_config(_write(tmp_path / "graph.config.yaml", text))


def test_binding_no_selector_fails_closed(tmp_path):
    text = "project_id: x\nbindings:\n  - match: {}\n    tier: tier3\n"
    with pytest.raises(GraphConfigError) as exc:
        load_graph_config(_write(tmp_path / "graph.config.yaml", text))
    assert "at least one of 'folder' or 'node_type'" in str(exc.value)


def test_binding_unknown_node_type_fails_closed(tmp_path):
    text = "project_id: x\nbindings:\n  - match: {node_type: not_a_type}\n    tier: tier3\n"
    with pytest.raises(GraphConfigError) as exc:
        load_graph_config(_write(tmp_path / "graph.config.yaml", text))
    assert "bindings[0]" in str(exc.value)
    assert "not_a_type" in str(exc.value)


def test_binding_blank_folder_fails_closed(tmp_path):
    text = "project_id: x\nbindings:\n  - match: {folder: '  '}\n    tier: tier3\n"
    with pytest.raises(GraphConfigError, match="folder"):
        load_graph_config(_write(tmp_path / "graph.config.yaml", text))


def test_binding_blank_artifact_path_fails_closed(tmp_path):
    text = (
        "project_id: x\nbindings:\n  - match: {node_type: concept}\n"
        "    tier: tier3\n    artifact_path: '   '\n"
    )
    with pytest.raises(GraphConfigError, match="artifact_path"):
        load_graph_config(_write(tmp_path / "graph.config.yaml", text))


def test_second_binding_error_names_index_1(tmp_path):
    text = (
        "project_id: x\nbindings:\n"
        "  - match: {node_type: concept}\n    tier: tier3\n"
        "  - match: {node_type: bogus}\n    tier: tier3\n"
    )
    with pytest.raises(GraphConfigError) as exc:
        load_graph_config(_write(tmp_path / "graph.config.yaml", text))
    assert "bindings[1]" in str(exc.value)


def test_utf8_bom_config_loads(tmp_path):
    p = tmp_path / "graph.config.yaml"
    p.write_text(_VALID, encoding="utf-8-sig")
    cfg = load_graph_config(p)
    assert cfg.project_id == "toy-instance"
