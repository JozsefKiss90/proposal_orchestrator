"""
Tests for runner.graph_schema — the additive-superset graph contract.

Covers:
  * the node_type superset vocabulary (15 methodology + 8 binding types)
  * the Appendix-B evidence_strength -> status pure lookup
  * fail-closed front-matter validation (required core, vocab, optional bindings)
  * the additive-superset invariant: a minimal node (required core only) is valid
    and no new required field is introduced.
"""

from __future__ import annotations

import pytest

from runner.graph_schema import (
    BINDING_NODE_TYPES,
    EVIDENCE_STRENGTHS,
    EVIDENCE_TO_STATUS,
    METHODOLOGY_NODE_TYPES,
    NODE_TYPES,
    OPTIONAL_BINDING_FIELDS,
    REQUIRED_CORE_FIELDS,
    TIERS,
    VALIDATION_STATUSES,
    GraphSchemaError,
    map_evidence_to_status,
    validate_front_matter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _minimal_fm(**overrides):
    """A minimal valid node: required core only, no optional binding fields."""
    fm = {
        "id": "TOY-CONCEPT-001",
        "title": "A toy concept",
        "node_type": "concept",
        "evidence_strength": "source_grounded",
    }
    fm.update(overrides)
    return fm


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


def test_methodology_vocab_has_the_15_existing_types():
    expected = {
        "meta",
        "governance",
        "dashboard",
        "source",
        "architecture",
        "state_of_the_art",
        "methodology_route",
        "methodology_problem",
        "decision_method",
        "infrastructure_layer",
        "risk",
        "swot",
        "partner",
        "concept",
        "research_questions",
    }
    assert METHODOLOGY_NODE_TYPES == expected


def test_binding_vocab_has_the_8_new_types():
    expected = {
        "proposal_section",
        "objective",
        "outcome",
        "impact",
        "work_package",
        "timeline",
        "budget",
        "phase_gate_state",
    }
    assert BINDING_NODE_TYPES == expected


def test_node_types_is_the_union_superset():
    assert NODE_TYPES == METHODOLOGY_NODE_TYPES | BINDING_NODE_TYPES
    assert len(NODE_TYPES) == 23


def test_proposal_section_is_a_binding_type():
    assert "proposal_section" in NODE_TYPES
    assert "proposal_section" in BINDING_NODE_TYPES


def test_risk_reuses_the_methodology_type_not_a_new_binding_type():
    # risks bind Tier 3 via the *existing* methodology `risk` type, so `risk`
    # must not be duplicated into the new binding vocabulary.
    assert "risk" in METHODOLOGY_NODE_TYPES
    assert "risk" not in BINDING_NODE_TYPES


def test_methodology_and_binding_vocabs_are_disjoint():
    assert METHODOLOGY_NODE_TYPES.isdisjoint(BINDING_NODE_TYPES)


# ---------------------------------------------------------------------------
# Appendix-B mapping (pure lookup, no inference)
# ---------------------------------------------------------------------------


def test_appendix_b_mapping_exact():
    assert EVIDENCE_TO_STATUS == {
        "source_grounded": "Confirmed",
        "synthesis": "Inferred",
        "inference": "Inferred",
        "unconfirmed": "Unresolved",
    }


@pytest.mark.parametrize(
    "evidence,status",
    [
        ("source_grounded", "Confirmed"),
        ("synthesis", "Inferred"),
        ("inference", "Inferred"),
        ("unconfirmed", "Unresolved"),
    ],
)
def test_map_evidence_to_status(evidence, status):
    assert map_evidence_to_status(evidence) == status


def test_map_is_total_over_evidence_strengths():
    for es in EVIDENCE_STRENGTHS:
        assert map_evidence_to_status(es) in VALIDATION_STATUSES


def test_only_source_grounded_yields_confirmed():
    confirmed = [es for es in EVIDENCE_STRENGTHS if map_evidence_to_status(es) == "Confirmed"]
    assert confirmed == ["source_grounded"]


def test_unconfirmed_is_not_finalizable_unresolved():
    # unconfirmed must never become Confirmed/Inferred — it is Unresolved (the
    # un-declared default the drafting gates block on).
    assert map_evidence_to_status("unconfirmed") == "Unresolved"


def test_map_evidence_raises_on_unknown():
    with pytest.raises(GraphSchemaError, match="Unknown evidence_strength"):
        map_evidence_to_status("totally_made_up")


def test_map_evidence_raises_on_none():
    with pytest.raises(GraphSchemaError):
        map_evidence_to_status(None)  # type: ignore[arg-type]


def test_validation_statuses_are_the_constitutional_four():
    assert VALIDATION_STATUSES == {"Confirmed", "Inferred", "Assumed", "Unresolved"}


# ---------------------------------------------------------------------------
# Field contract
# ---------------------------------------------------------------------------


def test_required_core_is_exactly_four_identity_fields():
    assert REQUIRED_CORE_FIELDS == ("id", "title", "node_type", "evidence_strength")


def test_optional_binding_fields_are_the_four_new_keys():
    assert OPTIONAL_BINDING_FIELDS == ("tier", "phase", "artifact_path", "sub_section_id")


def test_tiers_mirror_the_tier_model():
    assert TIERS == {"tier1", "tier2a", "tier2b", "tier3", "tier4", "tier5"}


# ---------------------------------------------------------------------------
# validate_front_matter — happy paths
# ---------------------------------------------------------------------------


def test_minimal_node_validates_no_new_required_field():
    # The additive-superset invariant: required core ONLY is valid.
    validate_front_matter(_minimal_fm(), "toy.md")


def test_node_with_all_optional_binding_fields_validates():
    fm = _minimal_fm(
        node_type="proposal_section",
        tier="tier5",
        phase=8,
        artifact_path="docs/tier5_deliverables/proposal_sections/excellence_section.json",
        sub_section_id="1.1",
    )
    validate_front_matter(fm, "excellence-1.1.md")


def test_phase_as_string_label_is_valid():
    validate_front_matter(_minimal_fm(phase="phase4"), "n.md")


def test_extra_methodology_fields_are_allowed():
    # optional methodology fields (confidence, domain, ...) do not break validation
    fm = _minimal_fm(confidence="high", domain=["x"], stakeholders=[], maturity="concept")
    validate_front_matter(fm, "n.md")


@pytest.mark.parametrize("node_type", sorted(NODE_TYPES))
def test_every_vocab_node_type_validates(node_type):
    validate_front_matter(_minimal_fm(node_type=node_type), "n.md")


@pytest.mark.parametrize("evidence", sorted(EVIDENCE_STRENGTHS))
def test_every_evidence_strength_validates(evidence):
    validate_front_matter(_minimal_fm(evidence_strength=evidence), "n.md")


@pytest.mark.parametrize("tier", sorted(TIERS))
def test_every_tier_validates(tier):
    validate_front_matter(_minimal_fm(tier=tier), "n.md")


# ---------------------------------------------------------------------------
# validate_front_matter — fail closed (naming the node)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("missing", REQUIRED_CORE_FIELDS)
def test_missing_required_field_fails_closed_naming_node(missing):
    fm = _minimal_fm()
    del fm[missing]
    with pytest.raises(GraphSchemaError) as exc:
        validate_front_matter(fm, "broken-node.md")
    assert "broken-node.md" in str(exc.value)
    assert missing in str(exc.value)


@pytest.mark.parametrize("blankable", REQUIRED_CORE_FIELDS)
def test_blank_required_field_fails_closed(blankable):
    with pytest.raises(GraphSchemaError, match=blankable):
        validate_front_matter(_minimal_fm(**{blankable: "   "}), "n.md")


def test_none_required_field_fails_closed():
    with pytest.raises(GraphSchemaError, match="title"):
        validate_front_matter(_minimal_fm(title=None), "n.md")


def test_unknown_node_type_fails_closed():
    with pytest.raises(GraphSchemaError) as exc:
        validate_front_matter(_minimal_fm(node_type="not_a_type"), "weird.md")
    assert "weird.md" in str(exc.value)
    assert "not_a_type" in str(exc.value)


def test_invalid_evidence_strength_fails_closed():
    with pytest.raises(GraphSchemaError, match="evidence_strength"):
        validate_front_matter(_minimal_fm(evidence_strength="strong"), "n.md")


def test_invalid_tier_fails_closed():
    with pytest.raises(GraphSchemaError) as exc:
        validate_front_matter(_minimal_fm(tier="tier9"), "n.md")
    assert "tier9" in str(exc.value)


def test_invalid_phase_bool_fails_closed():
    with pytest.raises(GraphSchemaError, match="phase"):
        validate_front_matter(_minimal_fm(phase=True), "n.md")


def test_invalid_phase_list_fails_closed():
    with pytest.raises(GraphSchemaError, match="phase"):
        validate_front_matter(_minimal_fm(phase=[1, 2]), "n.md")


def test_blank_artifact_path_fails_closed():
    with pytest.raises(GraphSchemaError, match="artifact_path"):
        validate_front_matter(_minimal_fm(artifact_path="   "), "n.md")


def test_non_string_artifact_path_fails_closed():
    with pytest.raises(GraphSchemaError, match="artifact_path"):
        validate_front_matter(_minimal_fm(artifact_path=123), "n.md")


def test_blank_sub_section_id_fails_closed():
    with pytest.raises(GraphSchemaError, match="sub_section_id"):
        validate_front_matter(_minimal_fm(sub_section_id=""), "n.md")


def test_non_mapping_front_matter_fails_closed():
    with pytest.raises(GraphSchemaError, match="not a mapping"):
        validate_front_matter(["not", "a", "dict"], "n.md")


def test_optional_binding_field_none_is_allowed():
    # explicit null for an optional field is the same as omitting it
    fm = _minimal_fm(tier=None, phase=None, artifact_path=None, sub_section_id=None)
    validate_front_matter(fm, "n.md")
