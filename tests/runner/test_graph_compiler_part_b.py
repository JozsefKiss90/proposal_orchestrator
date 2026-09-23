"""
Tests for the Part B ``proposal_section`` extraction slice of the graph compiler
(ticket 6).

Two layers, mirroring ``test_graph_compiler.py``:

* **Contract on a controlled fixture vault** — the sub-section extraction shape,
  ``content`` = body prose verbatim (no synthesis), the Appendix-B computed claim
  status (never read), overall-status derivation, section-specific required-field
  enforcement (schema-driven, fail-closed), determinism/byte-stability, non-
  destructiveness, and the fail-closed cases.
* **MSCA oracle** — compiling the real vault.  Ticket 8 authored the
  ``proposal_section`` nodes, so Part B now compiles to the three Tier-5
  sections (excellence / impact / implementation), each honestly
  ``overall_status=inferred``; the real ``docs/tier5_.../proposal_sections``
  is never touched (non-destructive staging).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from runner.graph_compiler import (
    EVIDENCE_TO_CLAIM_STATUS,
    GraphCompileError,
    compile_part_b,
    compile_part_b_and_report,
    extract_sub_section,
    _load_required_section_fields,
)
from runner.vault_reader import VaultReadError, read_vault

_FIXED_NOW = "2026-07-16T00:00:00+00:00"

# The minimal retained-section-schema spec the compiler reads to learn each
# criterion's required extra fields.  A faithful subset of the real
# artifact_schema_specification.yaml (§2.1b–d).
_SCHEMA_SPEC = {
    "artifacts": {
        "excellence_section": {
            "schema_id_value": "orch.tier5.excellence_section.v1",
            "fields": {
                "schema_id": {"required": True},
                "run_id": {"required": True},
                "criterion": {"required": True},
                "sub_sections": {"required": True},
                "validation_status": {"required": True},
                "traceability_footer": {"required": True},
            },
        },
        "impact_section": {
            "schema_id_value": "orch.tier5.impact_section.v1",
            "fields": {
                "schema_id": {"required": True},
                "run_id": {"required": True},
                "criterion": {"required": True},
                "sub_sections": {"required": True},
                "impact_pathway_refs": {"required": True},
                "dec_coverage": {"required": True},
                "validation_status": {"required": True},
                "traceability_footer": {"required": True},
            },
        },
        "implementation_section": {
            "schema_id_value": "orch.tier5.implementation_section.v1",
            "fields": {
                "schema_id": {"required": True},
                "run_id": {"required": True},
                "criterion": {"required": True},
                "sub_sections": {"required": True},
                "wp_table_refs": {"required": True},
                "gantt_ref": {"required": True},
                "milestone_refs": {"required": True},
                "risk_register_ref": {"required": True},
                "validation_status": {"required": True},
                "traceability_footer": {"required": True},
            },
        },
    }
}


# ---------------------------------------------------------------------------
# Helpers — a controlled fixture vault + config
# ---------------------------------------------------------------------------


def _write_node(path: Path, fm: dict, body: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fm_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
    path.write_text(f"---\n{fm_text}---\n\n{body}", encoding="utf-8")
    return path


def _ps_fm(
    node_id: str,
    slug: str,
    sub_id: str,
    criterion: str,
    evidence: str = "source_grounded",
    with_source_ref: bool = True,
    **overrides,
) -> dict:
    fm = {
        "id": node_id,
        "title": f"{node_id} title",
        "node_type": "proposal_section",
        "evidence_strength": evidence,
        "section_slug": slug,
        "criterion": criterion,
        "sub_section_id": sub_id,
    }
    if with_source_ref:
        fm["source_refs"] = [
            {
                "tier": 3,
                "source_path": "docs/tier3_project_instantiation/architecture_inputs/objectives.json",
            }
        ]
    fm.update(overrides)
    return fm


_PARTB_CONFIG = """\
project_id: fixture-partb
vault_path: nodes
bindings:
  - match:
      node_type: proposal_section
    tier: tier5
    artifact_path: docs/tier5_deliverables/proposal_sections
"""


def _write_config(root: Path, cfg: str = _PARTB_CONFIG) -> Path:
    cfg_path = root / "graph.config.yaml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(cfg, encoding="utf-8")
    return cfg_path


def _write_schema_spec(root: Path) -> None:
    p = root / ".claude/workflows/system_orchestration/artifact_schema_specification.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(_SCHEMA_SPEC, sort_keys=False), encoding="utf-8")


@pytest.fixture
def excellence_repo(tmp_path) -> Path:
    """A repo with the schema spec + a 2-sub-section Excellence vault."""
    root = tmp_path / "repo"
    _write_config(root)
    _write_schema_spec(root)
    _write_node(
        root / "nodes" / "20_excellence" / "PS-1-1.md",
        _ps_fm("PS-EXC-11", "excellence", "1.1", "Excellence", page_estimate=3),
        "## 1.1 Objectives\n\nThe first sub-section prose body.",
    )
    _write_node(
        root / "nodes" / "20_excellence" / "PS-1-2.md",
        _ps_fm("PS-EXC-12", "excellence", "1.2", "Excellence", evidence="synthesis"),
        "## 1.2 Methodology\n\nThe second sub-section prose body.",
    )
    return root


def _config_path(repo: Path) -> Path:
    return repo / "graph.config.yaml"


# ---------------------------------------------------------------------------
# extract_sub_section — the extraction contract (verbatim, no synthesis)
# ---------------------------------------------------------------------------


def test_extract_sub_section_shape_and_verbatim(tmp_path):
    root = tmp_path / "v"
    body = "## Heading\n\nParagraph one.\n\nParagraph two with words."
    node = read_vault(
        _write_node(
            root / "PS.md",
            _ps_fm("PS-1", "excellence", "1.1", "Excellence", page_estimate=2),
            body,
        ).parent
    ).by_id["PS-1"]
    entry = extract_sub_section(node)
    assert entry["sub_section_id"] == "1.1"
    assert entry["title"] == "PS-1 title"
    # content is the body verbatim (surrounding blank lines trimmed only).
    assert entry["content"] == body
    assert entry["content"] == node.body.strip()
    # word_count is derived (whitespace token count), never authored.
    assert entry["word_count"] == len(body.split())
    assert entry["page_estimate"] == 2


def test_extract_sub_section_no_synthesis_preserves_words(tmp_path):
    root = tmp_path / "v"
    body = "Alpha beta gamma delta. Epsilon zeta."
    node = read_vault(
        _write_node(root / "PS.md", _ps_fm("PS-1", "e", "1.1", "E"), body).parent
    ).by_id["PS-1"]
    entry = extract_sub_section(node)
    # Every word of the node body survives, none added — the compiler authors nothing.
    assert entry["content"].split() == body.split()


def test_extract_sub_section_optional_source_nodes(tmp_path):
    root = tmp_path / "v"
    node = read_vault(
        _write_node(
            root / "PS.md",
            _ps_fm("PS-1", "e", "1.1", "E", source_nodes=["METH-CORE-001", "METH-SOTA-006"]),
            "body",
        ).parent
    ).by_id["PS-1"]
    entry = extract_sub_section(node)
    assert entry["source_nodes"] == ["METH-CORE-001", "METH-SOTA-006"]


def test_extract_sub_section_page_estimate_must_be_int(tmp_path):
    root = tmp_path / "v"
    node = read_vault(
        _write_node(
            root / "PS.md", _ps_fm("PS-1", "e", "1.1", "E", page_estimate="lots"), "b"
        ).parent
    ).by_id["PS-1"]
    with pytest.raises(GraphCompileError, match=r"page_estimate must be an integer"):
        extract_sub_section(node)


@pytest.mark.parametrize(
    "evidence,status",
    [
        ("source_grounded", "confirmed"),
        ("synthesis", "inferred"),
        ("inference", "inferred"),
        ("unconfirmed", "unresolved"),
    ],
)
def test_claim_status_appendix_b_lowercase(evidence, status):
    assert EVIDENCE_TO_CLAIM_STATUS[evidence] == status


# ---------------------------------------------------------------------------
# compile_part_b — grouping, shape, status derivation
# ---------------------------------------------------------------------------


def test_compile_groups_into_one_section_file(excellence_repo, tmp_path):
    result = compile_part_b(
        _config_path(excellence_repo), excellence_repo, staging_root=tmp_path / "s", now=_FIXED_NOW
    )
    assert result.project_id == "fixture-partb"
    assert [s.slug for s in result.sections] == ["excellence"]
    sec = result.sections[0]
    assert sec.artifact_path == "docs/tier5_deliverables/proposal_sections/excellence_section.json"
    assert sec.staging_path.is_file()
    obj = json.loads(sec.staging_path.read_text(encoding="utf-8"))
    assert obj["schema_id"] == "orch.tier5.excellence_section.v1"
    assert obj["run_id"] == "fixture-partb"  # defaults to project_id
    assert obj["criterion"] == "Excellence"
    assert [s["sub_section_id"] for s in obj["sub_sections"]] == ["1.1", "1.2"]


def test_compile_carries_claim_status_from_evidence(excellence_repo, tmp_path):
    result = compile_part_b(
        _config_path(excellence_repo), excellence_repo, staging_root=tmp_path / "s"
    )
    obj = result.sections[0].section
    claims = obj["validation_status"]["claim_statuses"]
    assert claims[0]["status"] == "confirmed"  # source_grounded
    assert claims[1]["status"] == "inferred"  # synthesis
    # highest-risk across claims → inferred (no assumed/unresolved present).
    assert obj["validation_status"]["overall_status"] == "inferred"
    assert obj["traceability_footer"]["no_unsupported_claims_declaration"] is True


def test_unconfirmed_node_makes_section_unresolved(tmp_path):
    root = tmp_path / "repo"
    _write_config(root)
    _write_schema_spec(root)
    _write_node(
        root / "nodes" / "s" / "PS-1.md",
        _ps_fm("PS-1", "excellence", "1.1", "Excellence"),
        "confirmed body",
    )
    _write_node(
        root / "nodes" / "s" / "PS-2.md",
        _ps_fm("PS-2", "excellence", "1.2", "Excellence", evidence="unconfirmed"),
        "spine-dependent body",
    )
    result = compile_part_b(_config_path(root), root, staging_root=tmp_path / "s")
    obj = result.sections[0].section
    statuses = [c["status"] for c in obj["validation_status"]["claim_statuses"]]
    assert "unresolved" in statuses
    # an unconfirmed node yields an unresolved claim the gates correctly block.
    assert obj["validation_status"]["overall_status"] == "unresolved"
    assert obj["traceability_footer"]["no_unsupported_claims_declaration"] is False


def test_compile_traceability_footer_unions_source_refs(excellence_repo, tmp_path):
    result = compile_part_b(
        _config_path(excellence_repo), excellence_repo, staging_root=tmp_path / "s"
    )
    footer = result.sections[0].section["traceability_footer"]
    assert footer["primary_sources"] == [
        {
            "tier": 3,
            "source_path": "docs/tier3_project_instantiation/architecture_inputs/objectives.json",
        }
    ]


# ---------------------------------------------------------------------------
# Section-specific required fields (schema-driven, fail-closed)
# ---------------------------------------------------------------------------


def test_impact_requires_pathway_refs_and_dec_coverage(tmp_path):
    root = tmp_path / "repo"
    _write_config(root)
    _write_schema_spec(root)
    # An impact section node with NO section_extra_fields → missing required fields.
    _write_node(
        root / "nodes" / "impact" / "PS-2-1.md",
        _ps_fm("PS-IMP-21", "impact", "2.1", "Impact"),
        "impact prose",
    )
    with pytest.raises(GraphCompileError, match=r"impact.*(dec_coverage|impact_pathway_refs)"):
        compile_part_b(_config_path(root), root, staging_root=tmp_path / "s")


def test_impact_passes_when_extra_fields_declared(tmp_path):
    root = tmp_path / "repo"
    _write_config(root)
    _write_schema_spec(root)
    _write_node(
        root / "nodes" / "impact" / "PS-2-1.md",
        _ps_fm(
            "PS-IMP-21",
            "impact",
            "2.1",
            "Impact",
            section_extra_fields={
                "impact_pathway_refs": ["EI-01", "EI-02"],
                "dec_coverage": {
                    "dissemination_addressed": True,
                    "exploitation_addressed": True,
                    "communication_addressed": True,
                },
            },
        ),
        "impact prose",
    )
    result = compile_part_b(_config_path(root), root, staging_root=tmp_path / "s")
    obj = result.sections[0].section
    assert obj["impact_pathway_refs"] == ["EI-01", "EI-02"]
    assert obj["dec_coverage"]["dissemination_addressed"] is True


def test_implementation_required_fields_enforced(tmp_path):
    root = tmp_path / "repo"
    _write_config(root)
    _write_schema_spec(root)
    _write_node(
        root / "nodes" / "impl" / "PS-3-1.md",
        _ps_fm("PS-IMPL-31", "implementation", "3.1", "Quality and efficiency of the implementation"),
        "implementation prose",
    )
    with pytest.raises(GraphCompileError, match=r"implementation.*(wp_table_refs|gantt_ref|milestone_refs|risk_register_ref)"):
        compile_part_b(_config_path(root), root, staging_root=tmp_path / "s")


def test_required_fields_read_from_real_repo_schema(repo_root):
    # The schema-driven required set is sourced from the retained Tier 5 schema,
    # not hard-coded — prove it against the real artifact_schema_specification.yaml.
    required = _load_required_section_fields(repo_root)
    assert required.get("excellence") == frozenset()
    assert required.get("impact") == frozenset({"impact_pathway_refs", "dec_coverage"})
    assert required.get("implementation") == frozenset(
        {"wp_table_refs", "gantt_ref", "milestone_refs", "risk_register_ref"}
    )


def test_required_fields_permissive_when_schema_absent(tmp_path):
    # A throwaway second instance without the schema spec still compiles (D15):
    # required set is empty, so no extra fields are demanded.
    assert _load_required_section_fields(tmp_path) == {}


# ---------------------------------------------------------------------------
# Determinism / byte-stability / non-destructive
# ---------------------------------------------------------------------------


def test_compile_byte_stable(excellence_repo, tmp_path):
    a = compile_part_b(_config_path(excellence_repo), excellence_repo, staging_root=tmp_path / "a")
    b = compile_part_b(_config_path(excellence_repo), excellence_repo, staging_root=tmp_path / "b")
    for sa, sb in zip(a.sections, b.sections):
        assert sa.staging_path.read_bytes() == sb.staging_path.read_bytes()


def test_compile_does_not_touch_real_tier5(excellence_repo, tmp_path):
    real = (
        excellence_repo
        / "docs/tier5_deliverables/proposal_sections/excellence_section.json"
    )
    real.parent.mkdir(parents=True, exist_ok=True)
    original = '{"DO NOT": "TOUCH"}'
    real.write_text(original, encoding="utf-8")
    compile_part_b(_config_path(excellence_repo), excellence_repo, staging_root=tmp_path / "s")
    assert real.read_text(encoding="utf-8") == original


# ---------------------------------------------------------------------------
# Fail-closed
# ---------------------------------------------------------------------------


def test_fail_closed_tier5_binding_matches_non_proposal_section(tmp_path):
    root = tmp_path / "repo"
    cfg = """\
project_id: x
vault_path: nodes
bindings:
  - match:
      folder: "20_sections"
    tier: tier5
    artifact_path: docs/tier5_deliverables/proposal_sections
"""
    _write_config(root, cfg)
    _write_schema_spec(root)
    _write_node(
        root / "nodes" / "20_sections" / "OBJ.md",
        {
            "id": "OBJ-1",
            "title": "not a section",
            "node_type": "objective",
            "evidence_strength": "source_grounded",
        },
        "body",
    )
    with pytest.raises(GraphCompileError, match=r"only proposal_section nodes"):
        compile_part_b(_config_path(root), root, staging_root=tmp_path / "s")


def test_fail_closed_missing_section_slug(tmp_path):
    root = tmp_path / "repo"
    _write_config(root)
    _write_schema_spec(root)
    fm = _ps_fm("PS-1", "excellence", "1.1", "Excellence")
    del fm["section_slug"]
    _write_node(root / "nodes" / "s" / "PS-1.md", fm, "body")
    with pytest.raises(GraphCompileError, match=r"section_slug"):
        compile_part_b(_config_path(root), root, staging_root=tmp_path / "s")


def test_fail_closed_conflicting_criterion(tmp_path):
    root = tmp_path / "repo"
    _write_config(root)
    _write_schema_spec(root)
    _write_node(
        root / "nodes" / "s" / "PS-1.md",
        _ps_fm("PS-1", "excellence", "1.1", "Excellence"),
        "b1",
    )
    _write_node(
        root / "nodes" / "s" / "PS-2.md",
        _ps_fm("PS-2", "excellence", "1.2", "Excellence (typo)"),
        "b2",
    )
    with pytest.raises(GraphCompileError, match=r"conflicting criterion"):
        compile_part_b(_config_path(root), root, staging_root=tmp_path / "s")


def test_fail_closed_conflicting_extra_fields(tmp_path):
    root = tmp_path / "repo"
    _write_config(root)
    _write_schema_spec(root)
    _write_node(
        root / "nodes" / "s" / "PS-1.md",
        _ps_fm("PS-1", "impact", "2.1", "Impact", section_extra_fields={"impact_pathway_refs": ["EI-01"], "dec_coverage": {"x": True}}),
        "b1",
    )
    _write_node(
        root / "nodes" / "s" / "PS-2.md",
        _ps_fm("PS-2", "impact", "2.2", "Impact", section_extra_fields={"impact_pathway_refs": ["EI-99"]}),
        "b2",
    )
    with pytest.raises(GraphCompileError, match=r"conflicting section_extra_fields"):
        compile_part_b(_config_path(root), root, staging_root=tmp_path / "s")


def test_fail_closed_no_traceability_source(tmp_path):
    root = tmp_path / "repo"
    _write_config(root)
    _write_schema_spec(root)
    _write_node(
        root / "nodes" / "s" / "PS-1.md",
        _ps_fm("PS-1", "excellence", "1.1", "Excellence", with_source_ref=False),
        "body with no declared source",
    )
    with pytest.raises(GraphCompileError, match=r"no traceability source_refs"):
        compile_part_b(_config_path(root), root, staging_root=tmp_path / "s")


def test_fail_closed_unknown_section_slug_when_schema_present(tmp_path):
    # A typo'd section_slug must not silently emit a non-canonical, unenforced
    # section file when the retained schema is available to check against.
    root = tmp_path / "repo"
    _write_config(root)
    _write_schema_spec(root)
    _write_node(
        root / "nodes" / "s" / "PS-1.md",
        _ps_fm("PS-1", "excellance", "1.1", "Excellence"),  # typo: excellance
        "body",
    )
    with pytest.raises(GraphCompileError, match=r"excellance.*not a section in the retained"):
        compile_part_b(_config_path(root), root, staging_root=tmp_path / "s")


def test_unknown_slug_permitted_without_schema(tmp_path):
    # No schema spec → permissive (a throwaway second instance, D15).  An
    # otherwise-well-formed section compiles under any slug.
    root = tmp_path / "repo"
    _write_config(root)  # no _write_schema_spec
    _write_node(
        root / "nodes" / "s" / "PS-1.md",
        _ps_fm("PS-1", "section_a", "1.1", "Section A"),
        "body prose",
    )
    result = compile_part_b(_config_path(root), root, staging_root=tmp_path / "s")
    assert [s.slug for s in result.sections] == ["section_a"]


def test_fail_closed_duplicate_sub_section_id(tmp_path):
    root = tmp_path / "repo"
    _write_config(root)
    _write_schema_spec(root)
    _write_node(
        root / "nodes" / "s" / "PS-1.md",
        _ps_fm("PS-1", "excellence", "1.1", "Excellence"),
        "first body",
    )
    _write_node(
        root / "nodes" / "s" / "PS-2.md",
        _ps_fm("PS-2", "excellence", "1.1", "Excellence"),  # duplicate sub_section_id
        "second body",
    )
    with pytest.raises(GraphCompileError, match=r"duplicate sub_section_id"):
        compile_part_b(_config_path(root), root, staging_root=tmp_path / "s")


def test_fail_closed_empty_body(tmp_path):
    root = tmp_path / "repo"
    _write_config(root)
    _write_schema_spec(root)
    _write_node(
        root / "nodes" / "s" / "PS-1.md",
        _ps_fm("PS-1", "excellence", "1.1", "Excellence"),
        "",  # empty body → content must not be empty
    )
    with pytest.raises(GraphCompileError, match=r"body is empty"):
        compile_part_b(_config_path(root), root, staging_root=tmp_path / "s")


def test_malformed_vault_fails_closed(tmp_path):
    root = tmp_path / "repo"
    _write_config(root)
    p = root / "nodes" / "s" / "Broken.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("no front matter", encoding="utf-8")
    with pytest.raises(VaultReadError, match=r"Broken\.md"):
        compile_part_b(_config_path(root), root, staging_root=tmp_path / "s")


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------


def test_compile_part_b_and_report_writes_report(excellence_repo, tmp_path):
    result, report = compile_part_b_and_report(
        _config_path(excellence_repo), excellence_repo, staging_root=tmp_path / "s", now=_FIXED_NOW
    )
    report_path = excellence_repo / "docs/tier4_orchestration_state/graph_compile/part_b_report.json"
    assert report_path.is_file()
    on_disk = json.loads(report_path.read_text(encoding="utf-8"))
    assert on_disk["record_type"] == "part_b_graph_compile"
    assert on_disk["section_count"] == 1
    assert on_disk["sections"][0]["slug"] == "excellence"
    assert on_disk["sections"][0]["overall_status"] == "inferred"
    assert "unconfirmed->unresolved" in on_disk["appendix_b_mapping"]


# ---------------------------------------------------------------------------
# MSCA oracle — the real vault (ticket 8 authored the proposal_section nodes)
# ---------------------------------------------------------------------------


@pytest.fixture
def msca_config(repo_root) -> Path:
    cfg = repo_root / "MSCA" / "graph.config.yaml"
    if not cfg.is_file():
        pytest.skip("MSCA graph.config.yaml not present")
    return cfg


def test_msca_compiles_part_b_from_authored_nodes(msca_config, repo_root, tmp_path):
    # Ticket 8 authored the proposal_section nodes (folder 19_proposal_sections),
    # so Part B now compiles to the three Tier-5 sections, each honestly
    # overall_status=inferred (drafted narrative is synthesis over confirmed facts).
    result = compile_part_b(msca_config, repo_root, staging_root=tmp_path / "s", now=_FIXED_NOW)
    assert result.project_id == "msca-pf-reference"
    by_slug = {s.slug: s for s in result.sections}
    assert set(by_slug) == {"excellence", "impact", "implementation"}
    assert len(by_slug["excellence"].section["sub_sections"]) == 5
    assert len(by_slug["impact"].section["sub_sections"]) == 4
    assert len(by_slug["implementation"].section["sub_sections"]) == 3
    for sec in result.sections:
        assert sec.section["validation_status"]["overall_status"] == "inferred"
        # every section carries a non-empty traceability footer
        assert sec.section["traceability_footer"]["primary_sources"]
    # section-specific required extras are emitted from the authored nodes
    assert "impact_pathway_refs" in by_slug["impact"].section
    assert "dec_coverage" in by_slug["impact"].section
    impl = by_slug["implementation"].section
    for f in ("wp_table_refs", "gantt_ref", "milestone_refs", "risk_register_ref"):
        assert f in impl


def test_msca_part_b_does_not_mutate_real_tier5(msca_config, repo_root, tmp_path):
    tier5 = repo_root / "docs/tier5_deliverables/proposal_sections"
    before = {p.name: p.read_bytes() for p in tier5.glob("*.json")} if tier5.is_dir() else {}
    compile_part_b(msca_config, repo_root, staging_root=tmp_path / "s", now=_FIXED_NOW)
    after = {p.name: p.read_bytes() for p in tier5.glob("*.json")} if tier5.is_dir() else {}
    assert before == after
