"""
Tests for runner.vault_scaffold + the generic template (ticket 5).

Covers: the template itself is reader/compiler-acceptable and Dataview-enabled;
the scaffolder copies it and swaps in the project_id (comments preserved,
deterministic, fail-closed); the scaffolded vault validates; and the template
carries zero project nouns (the ticket-5 acceptance; the full lint is ticket 9).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from runner.graph_compiler import compile_tier3
from runner.graph_config import load_graph_config
from runner.graph_projector import check_no_overlap
from runner.vault_reader import read_vault
from runner.vault_scaffold import (
    DEFAULT_TEMPLATE_REL,
    ScaffoldResult,
    VaultScaffoldError,
    scaffold_vault,
    validate_scaffold,
)


@pytest.fixture
def template_dir(repo_root) -> Path:
    d = repo_root / DEFAULT_TEMPLATE_REL
    if not d.is_dir():
        pytest.skip("template not present")
    return d


# ---------------------------------------------------------------------------
# The template itself
# ---------------------------------------------------------------------------


def test_template_config_loads(template_dir):
    cfg = load_graph_config(template_dir / "graph.config.yaml")
    assert cfg.project_id == "template-instance"
    assert cfg.vault_path == "vault"


def test_template_vault_is_reader_acceptable(template_dir):
    cfg = load_graph_config(template_dir / "graph.config.yaml")
    vault = read_vault(cfg.resolve_vault_dir(), cfg)
    # seed meta node + two dashboards
    assert {n.node_id for n in vault.nodes} == {"TPL-META-001", "TPL-DASH-001", "TPL-DASH-002"}


def test_template_compiles_empty_tier3(template_dir, tmp_path):
    result = compile_tier3(template_dir / "graph.config.yaml", template_dir, staging_root=tmp_path / "s")
    # six tier3 artifacts (objectives, outcomes, impacts, wp, milestones, risks), all empty
    assert len(result.artifacts) == 6
    assert all(a.records == () for a in result.artifacts)


def test_template_has_no_overlap(template_dir):
    cfg = load_graph_config(template_dir / "graph.config.yaml")
    check_no_overlap(cfg)


def test_template_dataview_enabled_and_present(template_dir):
    import json

    plugins = json.loads((template_dir / ".obsidian" / "community-plugins.json").read_text())
    assert "dataview" in plugins
    assert (template_dir / ".obsidian" / "plugins" / "dataview" / "main.js").is_file()
    assert (template_dir / ".obsidian" / "plugins" / "dataview" / "manifest.json").is_file()


def test_template_folder_skeleton_present(template_dir):
    node_root = template_dir / "vault"
    for folder in ("00_meta", "11_objectives", "17_budget", "18_phase_gate_state", "90_dashboards"):
        assert (node_root / folder).is_dir(), folder


# ---------------------------------------------------------------------------
# The "no project nouns" acceptance (ticket 5; full lint is ticket 9)
# ---------------------------------------------------------------------------

_PROJECT_NOUNS = re.compile(
    r"\b(MSCA|irrigation|AquaCrop|PlanetScope|Sentinel|tomato|ELTE|AgroVIR|crop)\b",
    re.IGNORECASE,
)


def test_template_carries_no_project_nouns(template_dir):
    offenders = []
    for path in template_dir.rglob("*"):
        if not path.is_file():
            continue
        # skip the vendored plugin bundle (third-party JS/CSS, not template content)
        if "plugins" in path.relative_to(template_dir).parts:
            continue
        if path.suffix.lower() not in {".md", ".yaml", ".yml", ".json", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for m in _PROJECT_NOUNS.finditer(text):
            offenders.append(f"{path.relative_to(template_dir)}: {m.group(0)!r}")
    assert not offenders, "project nouns leaked into the generic template:\n" + "\n".join(offenders)


# ---------------------------------------------------------------------------
# scaffold_vault
# ---------------------------------------------------------------------------


def test_scaffold_copies_and_sets_project_id(template_dir, tmp_path):
    target = tmp_path / "new_vault"
    result = scaffold_vault(template_dir, target, "acme-ria-2027")
    assert isinstance(result, ScaffoldResult)
    assert result.project_id == "acme-ria-2027"
    assert result.node_root == target / "vault"
    cfg_text = (target / "graph.config.yaml").read_text(encoding="utf-8")
    assert "project_id: acme-ria-2027" in cfg_text
    # comments preserved (targeted line replacement, not a YAML round-trip)
    assert "GENERIC per-project template" in cfg_text
    # Dataview vendored into the copy
    assert (target / ".obsidian" / "plugins" / "dataview" / "main.js").is_file()


def test_scaffolded_vault_validates(template_dir, tmp_path):
    result = scaffold_vault(template_dir, tmp_path / "v", "toy-instance")
    vault = validate_scaffold(result)  # loads config, reads vault, checks no-overlap
    assert len(vault.nodes) == 3


def test_scaffolded_vault_compiles(template_dir, tmp_path):
    result = scaffold_vault(template_dir, tmp_path / "v", "toy-instance")
    compiled = compile_tier3(result.config_path, tmp_path / "v", staging_root=tmp_path / "s")
    assert len(compiled.artifacts) == 6
    cfg = load_graph_config(result.config_path)
    assert cfg.project_id == "toy-instance"


def test_scaffold_blank_project_id_fails_closed(template_dir, tmp_path):
    with pytest.raises(VaultScaffoldError, match="project_id"):
        scaffold_vault(template_dir, tmp_path / "v", "   ")


def test_scaffold_nonempty_target_without_force_fails(template_dir, tmp_path):
    target = tmp_path / "v"
    target.mkdir()
    (target / "existing.txt").write_text("x", encoding="utf-8")
    with pytest.raises(VaultScaffoldError, match="not empty"):
        scaffold_vault(template_dir, target, "toy")


def test_scaffold_force_merges_into_nonempty_target(template_dir, tmp_path):
    target = tmp_path / "v"
    target.mkdir()
    (target / "existing.txt").write_text("x", encoding="utf-8")
    result = scaffold_vault(template_dir, target, "toy", force=True)
    assert result.config_path.is_file()
    assert (target / "existing.txt").is_file()  # pre-existing content untouched


def test_scaffold_is_deterministic(template_dir, tmp_path):
    r1 = scaffold_vault(template_dir, tmp_path / "a", "same-id")
    r2 = scaffold_vault(template_dir, tmp_path / "b", "same-id")
    assert r1.config_path.read_bytes() == r2.config_path.read_bytes()
    nodes1 = {p.name for p in (tmp_path / "a" / "vault").rglob("*.md")}
    nodes2 = {p.name for p in (tmp_path / "b" / "vault").rglob("*.md")}
    assert nodes1 == nodes2


def test_scaffold_missing_template_config_fails_closed(tmp_path):
    empty_template = tmp_path / "empty_template"
    empty_template.mkdir()
    with pytest.raises(VaultScaffoldError, match="no graph.config.yaml"):
        scaffold_vault(empty_template, tmp_path / "v", "toy")
