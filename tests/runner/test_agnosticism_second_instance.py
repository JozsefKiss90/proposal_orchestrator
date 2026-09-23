"""
Agnosticism proof — the throwaway second instance (milestone 2, ticket 9; §2.7).

The companion to the "no project nouns" lint (``test_agnosticism_lint.py``).  The
lint proves the generic layer carries no instance-#1 noun; this proves the
*positive* half: a second, unrelated toy project
(``tests/fixtures/agnosticism_second_instance/`` — "BorrowBrella", a community
umbrella-lending network) compiles to valid ``docs/**`` artifacts through the
**same** ``runner.graph_compiler`` used by the MSCA-PF reference instance, with
**only its ``graph.config.yaml``** (and its authored vault) as the per-project
layer.  No runner code is edited to support it — the compiler, reader, schema and
pack deriver are untouched.

The toy vault deliberately uses **different folder names** than the reference
instance (``objectives/`` and ``sections/``, not ``11_objectives`` /
``19_proposal_sections``): the compiler learns the vault's shape from the config
alone, so a differently-shaped instance still compiles with no code change.
"""

from __future__ import annotations

import json
from pathlib import Path

from runner.graph_compiler import (
    _load_required_section_fields,
    compile_part_b,
    compile_tier3,
)
from runner.graph_config import load_graph_config

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "agnosticism_second_instance"
CONFIG_PATH = FIXTURE_DIR / "graph.config.yaml"

_FIXED_NOW = "2026-07-20T00:00:00+00:00"


# ---------------------------------------------------------------------------
# The instance is real and instantiated by config alone
# ---------------------------------------------------------------------------


def test_second_instance_is_a_distinct_config_only_instance() -> None:
    cfg = load_graph_config(CONFIG_PATH)
    # A distinct project id from the reference instance and the generic template.
    assert cfg.project_id == "borrowbrella-toy-instance"
    assert cfg.project_id not in {"msca-pf-reference", "template-instance"}
    # Its bindings drive a differently-shaped vault (proves config-driven, not
    # hard-coded folder names): objectives live in `objectives/`, sections match
    # by node_type only.
    assert cfg.resolve("objectives", "objective") is not None
    assert cfg.resolve("sections", "proposal_section") is not None


# ---------------------------------------------------------------------------
# Tier 3 slice compiles
# ---------------------------------------------------------------------------


def test_second_instance_compiles_tier3(tmp_path: Path) -> None:
    result = compile_tier3(CONFIG_PATH, REPO_ROOT, staging_root=tmp_path, now=_FIXED_NOW)

    assert len(result.artifacts) == 1
    art = result.artifacts[0]
    assert (
        art.artifact_path
        == "docs/tier3_project_instantiation/architecture_inputs/objectives.json"
    )
    assert art.collection_key == "objectives"
    assert art.source_node_ids == ("BB-OBJ-1", "BB-OBJ-2")  # vault (path) order

    ids = [r["id"] for r in art.records]
    assert ids == ["BB-OBJ-1", "BB-OBJ-2"]
    # source_grounded → Confirmed (Appendix-B lookup, computed not read)
    assert [r["validation_status"] for r in art.records] == ["Confirmed", "Confirmed"]
    assert [r["evidence_strength"] for r in art.records] == [
        "source_grounded",
        "source_grounded",
    ]
    # declared fields pass through verbatim
    assert art.records[0]["measurable_target"].startswith("40 lending stations")

    # the written staging file is valid JSON in the exact docs/** shape the
    # runner + gates consume (collection key + provenance), non-destructively under
    # the temp staging root (the real docs/ is never touched).
    assert str(tmp_path) in str(art.staging_path)
    obj = json.loads(art.staging_path.read_text(encoding="utf-8"))
    assert [r["id"] for r in obj["objectives"]] == ["BB-OBJ-1", "BB-OBJ-2"]
    assert obj["_provenance"]["source_config_project_id"] == "borrowbrella-toy-instance"


# ---------------------------------------------------------------------------
# Part B slice compiles against the REAL retained Tier-5 schema
# ---------------------------------------------------------------------------


def test_second_instance_compiles_part_b(tmp_path: Path) -> None:
    # The toy uses `excellence`, a real section in the retained schema with no
    # required extra fields — so it compiles against the actual gate-facing schema.
    required = _load_required_section_fields(REPO_ROOT)
    assert "excellence" in required and required["excellence"] == frozenset()

    result = compile_part_b(
        CONFIG_PATH,
        REPO_ROOT,
        staging_root=tmp_path,
        now=_FIXED_NOW,
        run_id="borrowbrella-toy-instance",
    )

    assert len(result.sections) == 1
    sec = result.sections[0]
    assert sec.slug == "excellence"
    assert sec.criterion == "Excellence"
    assert (
        sec.artifact_path
        == "docs/tier5_deliverables/proposal_sections/excellence_section.json"
    )

    s = sec.section
    assert s["schema_id"] == "orch.tier5.excellence_section.v1"
    assert s["run_id"] == "borrowbrella-toy-instance"
    assert [sub["sub_section_id"] for sub in s["sub_sections"]] == [
        "objectives",
        "concept_and_approach",
    ]
    # synthesis → inferred (never confirmed); overall = highest-risk claim
    assert s["validation_status"]["overall_status"] == "inferred"
    assert {c["status"] for c in s["validation_status"]["claim_statuses"]} == {"inferred"}
    # content is the node body prose, verbatim
    assert s["sub_sections"][0]["content"].startswith(
        "BorrowBrella pursues two measurable objectives."
    )
    assert s["sub_sections"][0]["word_count"] > 0
    # traceability footer is non-empty, deduped + sorted across both nodes' refs
    prim = s["traceability_footer"]["primary_sources"]
    assert len(prim) == 2 and all(p["tier"] == 3 for p in prim)

    # the written staging file is the exact Tier-5 section shape the gates read
    written = json.loads(sec.staging_path.read_text(encoding="utf-8"))
    assert written["schema_id"] == "orch.tier5.excellence_section.v1"
    assert len(written["sub_sections"]) == 2


# ---------------------------------------------------------------------------
# Determinism — byte-stable for the unchanged toy graph
# ---------------------------------------------------------------------------


def test_second_instance_is_byte_stable(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"

    t3a = compile_tier3(CONFIG_PATH, REPO_ROOT, staging_root=a, now=_FIXED_NOW)
    t3b = compile_tier3(CONFIG_PATH, REPO_ROOT, staging_root=b, now=_FIXED_NOW)
    assert t3a.artifacts[0].staging_path.read_bytes() == (
        t3b.artifacts[0].staging_path.read_bytes()
    )

    pba = compile_part_b(
        CONFIG_PATH, REPO_ROOT, staging_root=a, now=_FIXED_NOW, run_id="borrowbrella-toy-instance"
    )
    pbb = compile_part_b(
        CONFIG_PATH, REPO_ROOT, staging_root=b, now=_FIXED_NOW, run_id="borrowbrella-toy-instance"
    )
    assert pba.sections[0].staging_path.read_bytes() == (
        pbb.sections[0].staging_path.read_bytes()
    )
