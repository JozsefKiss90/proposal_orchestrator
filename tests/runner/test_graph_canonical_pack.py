"""
Tests for runner.graph_canonical_pack — pack-from-graph (ticket 7, D13-graph).

Two layers, mirroring the other graph tests:

* **Contract on a controlled fixture vault** — the extraction shape and field
  passthrough, the per-entry provenance (Appendix-B over ``evidence_strength``,
  ``unconfirmed`` never ``confirmed``), the ``source_node`` tag, bound-only
  extraction (methodology role nodes in an unbound folder are excluded),
  determinism/byte-stability, and the **no-drift** property: a pack and a Part B
  section derived from the *same* vault nodes pass the canonical-preservation
  gate.
* **MSCA oracle** — the real methodology-only vault yields an empty pack (the
  binding nodes await ticket 8); the real ``canonical_reference_pack.json`` is
  never touched.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from runner.graph_canonical_pack import (
    SCHEMA_ID,
    build_canonical_pack_from_graph,
    _extract_partners,
)
from runner.graph_compiler import compile_part_b
from runner.graph_config import GraphConfigError, load_graph_config
from runner.predicates.phase8_section_predicates import (
    deliverable_identity_preserved,
    measurable_targets_preserved,
    partner_names_preserved,
)
from runner.vault_reader import VaultReadError, read_vault


# ---------------------------------------------------------------------------
# Helpers — a controlled fixture vault + config
# ---------------------------------------------------------------------------


def _write_node(path: Path, fm: dict, body: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
    path.write_text(f"---\n{fm_text}---\n\n{body}", encoding="utf-8")
    return path


_PACK_CONFIG = """\
project_id: fixture-pack
vault_path: nodes
bindings:
  - match:
      node_type: proposal_section
    tier: tier5
    artifact_path: docs/tier5_deliverables/proposal_sections
  - match:
      folder: "11_objectives"
      node_type: objective
    tier: tier3
    artifact_path: docs/tier3_project_instantiation/architecture_inputs/objectives.json
    collection_key: objectives
  - match:
      folder: "12_outcomes"
      node_type: outcome
    tier: tier3
    artifact_path: docs/tier3_project_instantiation/architecture_inputs/outcomes.json
    collection_key: outcomes
  - match:
      folder: "14_work_packages"
      node_type: work_package
    tier: tier3
    artifact_path: docs/tier3_project_instantiation/architecture_inputs/workpackage_seed.json
    collection_key: work_packages
  - match:
      folder: "10_consortium"
      node_type: partner
    tier: tier3
    artifact_path: docs/tier3_project_instantiation/consortium/partners.json
    collection_key: partners
"""


def _core(node_id: str, node_type: str, evidence: str = "source_grounded", **fm) -> dict:
    base = {
        "id": node_id,
        "title": f"{node_id} title",
        "node_type": node_type,
        "evidence_strength": evidence,
    }
    base.update(fm)
    return base


@pytest.fixture
def pack_repo(tmp_path) -> Path:
    """A repo whose vault carries one of each binding node type + a decoy."""
    root = tmp_path / "repo"
    (root / "graph.config.yaml").parent.mkdir(parents=True, exist_ok=True)
    (root / "graph.config.yaml").write_text(_PACK_CONFIG, encoding="utf-8")
    nodes = root / "nodes"
    _write_node(
        nodes / "11_objectives" / "OBJ-1.md",
        _core(
            "OBJ-1", "objective",
            measurable_target="A calibrated model with honest uncertainty.",
            responsible_partner="FELLOW",
            contributing_partners=["HOST"],
        ),
        "Objective one body.",
    )
    _write_node(
        nodes / "11_objectives" / "OBJ-2.md",
        _core("OBJ-2", "objective", evidence="unconfirmed", measurable_target="Spine-dependent."),
        "Objective two body (synthetic spine).",
    )
    _write_node(
        nodes / "12_outcomes" / "OUT-1.md",
        _core("OUT-1", "outcome", linked_objectives=["OBJ-1"], linked_wp_ids=["WP1"]),
        "Outcome one body.",
    )
    _write_node(
        nodes / "14_work_packages" / "WP1.md",
        _core(
            "WP1", "work_package",
            wp_id="WP1",
            lead_partner="FELLOW",
            deliverables=[
                {"deliverable_id": "D1-01", "title": "Diagnostic report", "due_month": 14, "type": "report"},
            ],
        ),
        "Work package one body.",
    )
    _write_node(
        nodes / "10_consortium" / "AGRI.md",
        _core(
            "AGRI-NODE", "partner",
            short_name="AGRI",
            legal_name="Agricultural Research Institute",
            country="XX",
        ),
        "Partner body.",
    )
    # Decoy: a methodology-style partner role node in an UNBOUND folder → excluded.
    _write_node(
        nodes / "08_partners" / "PI-Role.md",
        _core("METH-PART-003", "partner", evidence="inference", short_name="PI", legal_name="Principal Investigator Role"),
        "Methodology partner role — not a consortium partner.",
    )
    return root


def _config_path(repo: Path) -> Path:
    return repo / "graph.config.yaml"


# ---------------------------------------------------------------------------
# Extraction shape + provenance
# ---------------------------------------------------------------------------


def test_pack_shape_and_arrays(pack_repo, tmp_path):
    _, pack = build_canonical_pack_from_graph(
        _config_path(pack_repo), pack_repo, out_path=tmp_path / "pack.json"
    )
    assert pack["schema_id"] == SCHEMA_ID
    assert pack["run_id"] == "fixture-pack"  # defaults to project_id
    assert {o["id"] for o in pack["objectives"]} == {"OBJ-1", "OBJ-2"}
    assert [o["id"] for o in pack["outcomes"]] == ["OUT-1"]
    assert [w["wp_id"] for w in pack["wps"]] == ["WP1"]
    assert [d["deliverable_id"] for d in pack["deliverables"]] == ["D1-01"]
    assert [p["short_name"] for p in pack["partners"]] == ["AGRI"]
    assert pack["aliases"] == []


def test_pack_carries_provenance_and_source_node(pack_repo, tmp_path):
    _, pack = build_canonical_pack_from_graph(
        _config_path(pack_repo), pack_repo, out_path=tmp_path / "pack.json"
    )
    by_id = {o["id"]: o for o in pack["objectives"]}
    assert by_id["OBJ-1"]["provenance"] == "confirmed"  # source_grounded
    assert by_id["OBJ-1"]["source_node"] == "OBJ-1"
    # ticket 7: each entry carries the raw evidence_strength AND its projection.
    assert by_id["OBJ-1"]["evidence_strength"] == "source_grounded"
    assert by_id["OBJ-2"]["evidence_strength"] == "unconfirmed"
    # unconfirmed node → 'unresolved', NEVER 'confirmed' (anti-fabrication).
    assert by_id["OBJ-2"]["provenance"] == "unresolved"
    assert by_id["OBJ-2"]["provenance"] != "confirmed"


def test_pack_passes_through_declared_fields_verbatim(pack_repo, tmp_path):
    _, pack = build_canonical_pack_from_graph(
        _config_path(pack_repo), pack_repo, out_path=tmp_path / "pack.json"
    )
    obj1 = next(o for o in pack["objectives"] if o["id"] == "OBJ-1")
    assert obj1["measurable_target"] == "A calibrated model with honest uncertainty."
    assert obj1["responsible_partner"] == "FELLOW"
    assert obj1["contributing_partners"] == ["HOST"]
    deliv = pack["deliverables"][0]
    assert deliv["parent_wp"] == "WP1"
    assert deliv["due_month"] == 14
    partner = pack["partners"][0]
    assert partner["legal_name"] == "Agricultural Research Institute"


def test_unbound_methodology_partner_excluded(pack_repo, tmp_path):
    # The 08_partners role node (unbound folder) must NOT appear in the pack —
    # a consortium partner is one the config explicitly binds.
    _, pack = build_canonical_pack_from_graph(
        _config_path(pack_repo), pack_repo, out_path=tmp_path / "pack.json"
    )
    assert all(p.get("short_name") != "PI" for p in pack["partners"])
    assert all(p["source_node"] != "METH-PART-003" for p in pack["partners"])


def test_declared_assumptions_empty_when_absent(pack_repo, tmp_path):
    # No working_assumptions.json in the tmp repo → honest empty (mode α).
    _, pack = build_canonical_pack_from_graph(
        _config_path(pack_repo), pack_repo, out_path=tmp_path / "pack.json"
    )
    assert pack["declared_assumptions"] == []


# ---------------------------------------------------------------------------
# Determinism / byte-stability
# ---------------------------------------------------------------------------


def test_pack_byte_stable(pack_repo, tmp_path):
    p1, _ = build_canonical_pack_from_graph(
        _config_path(pack_repo), pack_repo, out_path=tmp_path / "a.json"
    )
    p2, _ = build_canonical_pack_from_graph(
        _config_path(pack_repo), pack_repo, out_path=tmp_path / "b.json"
    )
    assert p1.read_bytes() == p2.read_bytes()


def test_pack_writes_to_default_staging(pack_repo):
    # No out_path → non-destructive default staging under graph_compile/.
    from runner.graph_canonical_pack import DEFAULT_STAGING_REL

    target, _ = build_canonical_pack_from_graph(_config_path(pack_repo), pack_repo)
    assert target == pack_repo / DEFAULT_STAGING_REL
    assert target.is_file()


# ---------------------------------------------------------------------------
# No pack/prose drift — the D13-graph point
# ---------------------------------------------------------------------------


def test_pack_and_section_share_source_no_drift(tmp_path):
    # Partner + WP(deliverable) + objective nodes, and a proposal_section whose
    # prose references ALL of them correctly (partner short_name, deliverable id,
    # and the objective's measurable-target number).  Because the pack and the
    # section derive from the SAME vault nodes, three distinct canonical-
    # preservation detectors pass — non-vacuously (the prose actually names the
    # facts, so a real drift would be caught).
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    (root / "graph.config.yaml").write_text(_PACK_CONFIG, encoding="utf-8")
    nodes = root / "nodes"
    _write_node(
        nodes / "10_consortium" / "AGRI.md",
        _core("AGRI-NODE", "partner", short_name="AGRI",
              legal_name="Agricultural Research Institute", country="XX"),
        "partner body",
    )
    _write_node(
        nodes / "11_objectives" / "OBJ-1.md",
        _core("OBJ-1", "objective",
              measurable_target="Diagnostic model validated at 90% interval coverage.",
              responsible_partner="AGRI"),
        "objective body",
    )
    _write_node(
        nodes / "14_work_packages" / "WP1.md",
        _core("WP1", "work_package", wp_id="WP1", lead_partner="AGRI",
              deliverables=[{"deliverable_id": "D1-01", "title": "Diagnostic report",
                             "due_month": 14, "type": "report"}]),
        "wp body",
    )
    _write_node(
        nodes / "20_excellence" / "PS-1-1.md",
        {
            "id": "PS-1-1",
            "title": "Objectives",
            "node_type": "proposal_section",
            "evidence_strength": "source_grounded",
            "section_slug": "excellence",
            "criterion": "Excellence",
            "sub_section_id": "1.1",
            "source_refs": [{"tier": 3, "source_path": "docs/tier3_project_instantiation/consortium/partners.json"}],
        },
        "Coordinated with AGRI, objective OBJ-1 targets 90% interval coverage; "
        "deliverable D1-01 (the Diagnostic report) is due in month 14.",
    )
    # Compile the section (ticket 6) and derive the pack (ticket 7) from one vault.
    section_result = compile_part_b(_config_path(root), root, staging_root=tmp_path / "stage")
    section_path = section_result.sections[0].staging_path
    pack_path, _ = build_canonical_pack_from_graph(
        _config_path(root), root, out_path=tmp_path / "pack.json"
    )
    # Three distinct preservation detectors find no drift (shared graph source).
    for detector in (partner_names_preserved, deliverable_identity_preserved,
                     measurable_targets_preserved):
        result = detector(section_path, pack_path)
        assert result.passed, f"{detector.__name__}: {getattr(result, 'reason', '')}"


# ---------------------------------------------------------------------------
# Fail-closed
# ---------------------------------------------------------------------------


def test_malformed_vault_fails_closed(tmp_path):
    root = tmp_path / "repo"
    root.mkdir(parents=True, exist_ok=True)
    (root / "graph.config.yaml").write_text(_PACK_CONFIG, encoding="utf-8")
    p = root / "nodes" / "11_objectives" / "Broken.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("no front matter", encoding="utf-8")
    with pytest.raises(VaultReadError, match=r"Broken\.md"):
        build_canonical_pack_from_graph(_config_path(root), root, out_path=tmp_path / "p.json")


def test_missing_config_fails_closed(tmp_path):
    with pytest.raises(GraphConfigError):
        build_canonical_pack_from_graph(tmp_path / "nope.yaml", tmp_path, out_path=tmp_path / "p.json")


# ---------------------------------------------------------------------------
# MSCA oracle — the real methodology-only vault yields an empty pack
# ---------------------------------------------------------------------------


@pytest.fixture
def msca_config(repo_root) -> Path:
    cfg = repo_root / "MSCA" / "graph.config.yaml"
    if not cfg.is_file():
        pytest.skip("MSCA graph.config.yaml not present")
    return cfg


def test_msca_pack_empty_today(msca_config, tmp_path):
    # repo_root=tmp_path isolates working_assumptions (absent → empty); the vault
    # resolves from the real config.  The 6 methodology partner nodes in the
    # unbound 08_partners folder must be excluded → all confirmed arrays empty.
    target, pack = build_canonical_pack_from_graph(
        msca_config, tmp_path, out_path=tmp_path / "pack.json"
    )
    assert pack["run_id"] == "msca-pf-reference"
    for key in ("objectives", "outcomes", "wps", "deliverables", "partners"):
        assert pack[key] == [], f"{key} should be empty pre-ticket-8"
    assert pack["declared_assumptions"] == []


def test_msca_pack_does_not_touch_real_canonical_pack(msca_config, repo_root, tmp_path):
    from runner.graph_canonical_pack import CANONICAL_PACK_REL

    real = repo_root / CANONICAL_PACK_REL
    before = real.read_bytes() if real.is_file() else None
    build_canonical_pack_from_graph(msca_config, tmp_path, out_path=tmp_path / "pack.json")
    after = real.read_bytes() if real.is_file() else None
    assert before == after


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def test_module_cli_derives_pack(pack_repo, tmp_path, capsys):
    from runner.graph_canonical_pack import main

    out = tmp_path / "pack.json"
    code = main([
        "--config", str(_config_path(pack_repo)),
        "--repo-root", str(pack_repo),
        "--out", str(out),
    ])
    assert code == 0
    assert out.is_file()
    printed = capsys.readouterr().out
    assert "objectives=2" in printed
    assert "partners=1" in printed


def test_module_cli_fail_closed_returns_2(tmp_path, capsys):
    from runner.graph_canonical_pack import main

    code = main(["--config", str(tmp_path / "nope.yaml"), "--repo-root", str(tmp_path)])
    assert code == 2
