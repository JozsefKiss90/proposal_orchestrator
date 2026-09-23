"""
Tests for runner.vault_reader — the deterministic pure-Python vault reader.

Covers front-matter splitting (leading block only), wikilink basename
resolution, indexing, config binding, determinism, and fail-closed behaviour
(missing/malformed/duplicate nodes named, never a silent skip).

The final section reads the **real** MSCA methodology vault and asserts the
ticket-1 acceptance invariant: all 87 existing methodology nodes validate
unchanged.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest
import yaml

from runner.graph_config import GraphConfig, load_graph_config
from runner.vault_reader import (
    VaultReadError,
    Vault,
    read_vault,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_node(path: Path, fm: dict, body: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
    path.write_text(f"---\n{fm_text}---\n\n{body}", encoding="utf-8")
    return path


def _fm(node_id: str, node_type: str = "concept", **overrides) -> dict:
    fm = {
        "id": node_id,
        "title": node_id.replace("-", " ").title(),
        "node_type": node_type,
        "evidence_strength": "source_grounded",
    }
    fm.update(overrides)
    return fm


@pytest.fixture
def toy_vault(tmp_path) -> Path:
    """A small 3-node vault with folders, wikilinks, and an alias."""
    root = tmp_path / "vault"
    _write_node(
        root / "01_sources" / "Source A.md",
        _fm("TOY-SRC-001", "source", aliases=["SrcA"]),
        "The root source. See [[Concept One]].",
    )
    _write_node(
        root / "02_core" / "Concept One.md",
        _fm("TOY-CORE-001", "concept", evidence_strength="synthesis"),
        "Builds on [[Source A]] and [[SrcA]] and a [[Missing Node]].",
    )
    _write_node(
        root / "Root Note.md",
        _fm("TOY-META-001", "meta"),
        "Top-level note linking [[Concept One|the concept]].",
    )
    return root


# ---------------------------------------------------------------------------
# Happy path + indexing
# ---------------------------------------------------------------------------


def test_reads_all_nodes(toy_vault):
    vault = read_vault(toy_vault)
    assert len(vault.nodes) == 3
    assert set(vault.by_id) == {"TOY-SRC-001", "TOY-CORE-001", "TOY-META-001"}
    assert set(vault.by_basename) == {"Source A", "Concept One", "Root Note"}


def test_nodes_are_ordered_by_rel_path(toy_vault):
    vault = read_vault(toy_vault)
    assert [n.rel_path for n in vault.nodes] == [
        "01_sources/Source A.md",
        "02_core/Concept One.md",
        "Root Note.md",
    ]


def test_folder_computation(toy_vault):
    vault = read_vault(toy_vault)
    assert vault.by_basename["Source A"].folder == "01_sources"
    assert vault.by_basename["Root Note"].folder == ""


def test_status_from_appendix_b_lookup(toy_vault):
    vault = read_vault(toy_vault)
    assert vault.by_basename["Source A"].status == "Confirmed"  # source_grounded
    assert vault.by_basename["Concept One"].status == "Inferred"  # synthesis


def test_body_excludes_front_matter(toy_vault):
    vault = read_vault(toy_vault)
    node = vault.by_basename["Source A"]
    assert "The root source" in node.body
    assert "node_type" not in node.body


# ---------------------------------------------------------------------------
# Optional binding-field properties
# ---------------------------------------------------------------------------


def test_binding_field_properties(tmp_path):
    root = tmp_path / "v"
    _write_node(
        root / "x.md",
        _fm(
            "TOY-PS-001",
            "proposal_section",
            tier="tier5",
            phase=8,
            artifact_path="docs/tier5_deliverables/proposal_sections/excellence_section.json",
            sub_section_id="1.1",
        ),
    )
    node = read_vault(root).by_basename["x"]
    assert node.tier == "tier5"
    assert node.phase == 8
    assert node.artifact_path.endswith("excellence_section.json")
    assert node.sub_section_id == "1.1"


def test_binding_fields_none_when_absent(toy_vault):
    node = read_vault(toy_vault).by_basename["Source A"]
    assert node.tier is None
    assert node.phase is None
    assert node.artifact_path is None
    assert node.sub_section_id is None


# ---------------------------------------------------------------------------
# Wikilinks + basename resolution
# ---------------------------------------------------------------------------


def test_wikilinks_extracted(toy_vault):
    vault = read_vault(toy_vault)
    links = vault.by_basename["Concept One"].wikilinks
    targets = [l.target_basename for l in links]
    assert targets == ["Source A", "SrcA", "Missing Node"]


def test_wikilink_display_alias():
    from runner.vault_reader import _parse_wikilink

    link = _parse_wikilink("Concept One|the concept")
    assert link.target_basename == "Concept One"
    assert link.display == "the concept"


def test_wikilink_folder_and_heading_stripped():
    from runner.vault_reader import _parse_wikilink

    link = _parse_wikilink("04_routes/Route A#Section 2|display")
    assert link.target_basename == "Route A"
    assert link.display == "display"


def test_resolve_link_by_basename(toy_vault):
    vault = read_vault(toy_vault)
    assert vault.resolve_link("Source A").node_id == "TOY-SRC-001"


def test_resolve_link_by_alias(toy_vault):
    vault = read_vault(toy_vault)
    assert vault.resolve_link("SrcA").node_id == "TOY-SRC-001"


def test_resolve_link_dangling_returns_none(toy_vault):
    vault = read_vault(toy_vault)
    assert vault.resolve_link("Missing Node") is None


def test_dangling_links_recorded_not_fatal(toy_vault):
    vault = read_vault(toy_vault)
    dangling = vault.dangling_links()
    assert len(dangling) == 1
    node, link = dangling[0]
    assert node.basename == "Concept One"
    assert link.target_basename == "Missing Node"


def test_basename_wins_over_alias(tmp_path):
    # a node's real basename must never be shadowed by another node's alias
    root = tmp_path / "v"
    _write_node(root / "Real.md", _fm("A", "concept"))
    _write_node(root / "Other.md", _fm("B", "concept", aliases=["Real"]))
    vault = read_vault(root)
    assert vault.resolve_link("Real").node_id == "A"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_same_vault_same_parse(toy_vault):
    v1 = read_vault(toy_vault)
    v2 = read_vault(toy_vault)
    assert [n.rel_path for n in v1.nodes] == [n.rel_path for n in v2.nodes]
    assert [n.wikilinks for n in v1.nodes] == [n.wikilinks for n in v2.nodes]
    assert [n.node_id for n in v1.nodes] == [n.node_id for n in v2.nodes]


def test_ordering_is_cross_os_deterministic_by_posix_string(tmp_path):
    # Ordering follows the POSIX rel-path STRING (ASCII, case-sensitive on every
    # platform), not OS-dependent Path comparison (case-insensitive on Windows).
    # 'Z' (0x5A) sorts before 'a' (0x61) in ASCII everywhere.
    root = tmp_path / "v"
    _write_node(root / "Zebra.md", _fm("Z-1", "concept"))
    _write_node(root / "apple.md", _fm("A-1", "concept"))
    vault = read_vault(root)
    assert [n.basename for n in vault.nodes] == ["Zebra", "apple"]


# ---------------------------------------------------------------------------
# Config binding
# ---------------------------------------------------------------------------


def test_binding_for_with_config(tmp_path):
    root = tmp_path / "vault"
    _write_node(root / "10_ps" / "Excellence 1.md", _fm("PS-1", "proposal_section"))
    cfg_text = (
        "project_id: t\nbindings:\n"
        "  - match: {node_type: proposal_section}\n"
        "    tier: tier5\n    artifact_path: docs/tier5_deliverables/proposal_sections\n"
    )
    (tmp_path / "graph.config.yaml").write_text(cfg_text, encoding="utf-8")
    cfg = load_graph_config(tmp_path / "graph.config.yaml")
    vault = read_vault(root, config=cfg)
    binding = vault.binding_for(vault.by_basename["Excellence 1"])
    assert binding is not None
    assert binding.tier == "tier5"


def test_binding_for_without_config_is_none(toy_vault):
    vault = read_vault(toy_vault)
    assert vault.binding_for(vault.nodes[0]) is None


# ---------------------------------------------------------------------------
# Fail closed
# ---------------------------------------------------------------------------


def test_missing_vault_dir_fails_closed(tmp_path):
    with pytest.raises(VaultReadError, match="not found"):
        read_vault(tmp_path / "nope")


def test_node_without_front_matter_fails_closed(tmp_path):
    root = tmp_path / "v"
    root.mkdir()
    (root / "bad.md").write_text("Just prose, no front-matter.\n", encoding="utf-8")
    with pytest.raises(VaultReadError) as exc:
        read_vault(root)
    assert "bad.md" in str(exc.value)
    assert "front-matter" in str(exc.value)


def test_unclosed_front_matter_fails_closed(tmp_path):
    root = tmp_path / "v"
    root.mkdir()
    (root / "bad.md").write_text("---\nid: X\ntitle: Y\n", encoding="utf-8")
    with pytest.raises(VaultReadError) as exc:
        read_vault(root)
    assert "bad.md" in str(exc.value)
    assert "never closed" in str(exc.value)


def test_non_mapping_front_matter_fails_closed(tmp_path):
    root = tmp_path / "v"
    root.mkdir()
    (root / "bad.md").write_text("---\n- a\n- b\n---\nbody\n", encoding="utf-8")
    with pytest.raises(VaultReadError) as exc:
        read_vault(root)
    assert "bad.md" in str(exc.value)


def test_invalid_yaml_front_matter_fails_closed(tmp_path):
    root = tmp_path / "v"
    root.mkdir()
    (root / "bad.md").write_text("---\nid: [unclosed\n---\nbody\n", encoding="utf-8")
    with pytest.raises(VaultReadError) as exc:
        read_vault(root)
    assert "bad.md" in str(exc.value)
    assert "not valid YAML" in str(exc.value)


def test_schema_violation_fails_closed_naming_node(tmp_path):
    root = tmp_path / "v"
    _write_node(root / "sub" / "weird.md", _fm("W-1", "not_a_real_type"))
    with pytest.raises(VaultReadError) as exc:
        read_vault(root)
    assert "sub/weird.md" in str(exc.value)
    assert "not_a_real_type" in str(exc.value)


def test_duplicate_id_fails_closed(tmp_path):
    root = tmp_path / "v"
    _write_node(root / "a.md", _fm("DUP-1", "concept"))
    _write_node(root / "b.md", _fm("DUP-1", "concept"))
    with pytest.raises(VaultReadError) as exc:
        read_vault(root)
    assert "Duplicate node id" in str(exc.value)
    assert "DUP-1" in str(exc.value)


def test_duplicate_basename_fails_closed(tmp_path):
    root = tmp_path / "v"
    _write_node(root / "x" / "Same.md", _fm("A-1", "concept"))
    _write_node(root / "y" / "Same.md", _fm("A-2", "concept"))
    with pytest.raises(VaultReadError) as exc:
        read_vault(root)
    assert "Duplicate node basename" in str(exc.value)


def test_dot_directories_skipped(tmp_path):
    root = tmp_path / "v"
    _write_node(root / "good.md", _fm("G-1", "concept"))
    # a stray non-node markdown under .obsidian/.trash must NOT fail the read
    (root / ".obsidian").mkdir(parents=True)
    (root / ".obsidian" / "notes.md").write_text("no front-matter here\n", encoding="utf-8")
    (root / ".trash").mkdir()
    (root / ".trash" / "deleted.md").write_text("garbage\n", encoding="utf-8")
    vault = read_vault(root)
    assert {n.basename for n in vault.nodes} == {"good"}


def test_never_silently_skips_a_real_node(tmp_path):
    # one good node + one malformed node at top level: must RAISE, not skip.
    root = tmp_path / "v"
    _write_node(root / "good.md", _fm("G-1", "concept"))
    (root / "malformed.md").write_text("no front-matter\n", encoding="utf-8")
    with pytest.raises(VaultReadError, match="malformed.md"):
        read_vault(root)


# ---------------------------------------------------------------------------
# Real MSCA vault — the ticket-1 acceptance invariant
# ---------------------------------------------------------------------------


@pytest.fixture
def msca_methodology_vault(repo_root) -> Path:
    vault = repo_root / "MSCA" / "methodology_graph"
    if not vault.is_dir():
        pytest.skip("MSCA methodology vault not present")
    return vault


#: Ticket-8 authoring added the Tier-3/4/5 binding folders (11-19); the ticket-1
#: invariant is scoped to the *methodology* folders (00-10, 90, 99) so it keeps
#: asserting exactly what it always meant: the 87 methodology nodes unchanged.
_BINDING_FOLDER_PREFIXES = ("11_", "12_", "13_", "14_", "15_", "16_", "17_", "18_", "19_")


def _methodology_nodes(vault):
    return [n for n in vault.nodes if not n.rel_path.startswith(_BINDING_FOLDER_PREFIXES)]


def test_all_87_methodology_nodes_validate_unchanged(msca_methodology_vault):
    # The whole vault reads cleanly (no VaultReadError, incl. the ticket-8 binding
    # nodes); the 87 methodology nodes (folders 00-10, 90, 99) are unchanged.
    vault = read_vault(msca_methodology_vault)
    assert len(_methodology_nodes(vault)) == 87


def test_msca_evidence_distribution(msca_methodology_vault):
    # Distribution over the 87 methodology nodes is unchanged by ticket 8.
    vault = read_vault(msca_methodology_vault)
    dist = Counter(n.evidence_strength for n in _methodology_nodes(vault))
    assert dist == {
        "source_grounded": 67,
        "synthesis": 14,
        "unconfirmed": 4,
        "inference": 2,
    }


def test_msca_node_types_are_all_in_vocab(msca_methodology_vault):
    from runner.graph_schema import NODE_TYPES

    vault = read_vault(msca_methodology_vault)
    assert {n.node_type for n in vault.nodes} <= NODE_TYPES


def test_msca_elte_node_is_unresolved(msca_methodology_vault):
    # ELTE is unconfirmed in the vault → status Unresolved (never Confirmed).
    vault = read_vault(msca_methodology_vault)
    elte = vault.by_basename["ELTE Role"]
    assert elte.evidence_strength == "unconfirmed"
    assert elte.status == "Unresolved"


def test_msca_ticket8_binding_nodes_authored(msca_methodology_vault):
    # Ticket 8 authored the Tier-3/5 binding + budget nodes in folders 11-19; this
    # pins their node_type distribution (incl. the source-only budget nodes, which
    # have no other oracle).
    vault = read_vault(msca_methodology_vault)
    binding = [n for n in vault.nodes if n.rel_path.startswith(_BINDING_FOLDER_PREFIXES)]
    assert Counter(n.node_type for n in binding) == {
        "objective": 5,
        "outcome": 6,
        "impact": 4,
        "work_package": 5,
        "timeline": 6,
        "risk": 10,
        "budget": 5,
        "proposal_section": 12,
    }
    # Budget lines are the §8.1 unit-cost derivation — all Confirmed today, so
    # source_grounded; the deriver degrades a missing status to unconfirmed, never up.
    budget = [n for n in binding if n.node_type == "budget"]
    assert all(n.evidence_strength == "source_grounded" for n in budget)


def test_msca_schema_node_only_parses_leading_front_matter(msca_methodology_vault):
    # The schema doc has a `node_type: ""` example inside a body code fence;
    # the reader must classify the node by its real front-matter (governance),
    # not the code-fence example.
    vault = read_vault(msca_methodology_vault)
    schema_node = vault.by_basename["Methodology Graph Schema"]
    assert schema_node.node_type == "governance"


def test_msca_read_is_deterministic(msca_methodology_vault):
    v1 = read_vault(msca_methodology_vault)
    v2 = read_vault(msca_methodology_vault)
    assert [n.node_id for n in v1.nodes] == [n.node_id for n in v2.nodes]
