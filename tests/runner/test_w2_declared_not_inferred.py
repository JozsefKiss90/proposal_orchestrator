"""Tests for the W2 predicate ``declared_facts_are_not_inferred``.

W2 closes the escape hatch beside W1.  W1
(``assumed_claims_are_operator_declared``) audits claims already marked
``assumed`` and is silent about a claim that *should* be assumed but is not — so
a drafter that labels an operator declaration ``inferred`` passes W1 vacuously
(nothing to audit), passes ``no_unresolved_material_claims`` (not unresolved
either), and the whole declared-assumption honesty apparatus goes inert on that
section.  That is exactly what happened to the real Excellence section on run
``ec01fb84``: three operator-declared facts were drafted ``inferred``, W1 saw
zero ``assumed`` claims, and the gate reported the section clean on that axis.

Under §12.2 the statuses are not interchangeable.  ``Inferred`` is *derived by
logical reasoning from confirmed evidence*; ``Assumed`` is *adopted in the
absence of direct evidence*.  A declaration is adopted because no evidence
exists, so citing ``working_assumptions.json`` while claiming ``inferred``
misstates provenance to the evaluator.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runner.predicates import declared_facts_are_not_inferred

SECTION_REL = "docs/tier5_deliverables/proposal_sections/excellence_section.json"
WA_PATH = "docs/tier3_project_instantiation/working_assumptions.json"


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _section(repo_root: Path, claims: list[dict[str, Any]]) -> Path:
    path = repo_root / SECTION_REL
    _write(
        path,
        {
            "schema_id": "orch.tier5.excellence_section.v1",
            "run_id": "run-w2-1",
            "criterion": "Excellence",
            "sub_sections": [{"sub_section_id": "1.1", "content": "Prose."}],
            "validation_status": {
                "overall_status": "confirmed",
                "claim_statuses": claims,
            },
        },
    )
    return path


class TestW2CatchesTheMislabel:
    def test_inferred_claim_citing_declarations_fails(self, tmp_path: Path) -> None:
        _section(tmp_path, [
            {
                "claim_id": "CC_PLACEMENT_SUPERVISOR",
                "claim_summary": "operator-declared, not independently verified",
                "status": "inferred",
                "source_ref": WA_PATH,
            },
        ])
        result = declared_facts_are_not_inferred(SECTION_REL, repo_root=tmp_path)
        assert not result.passed
        assert result.failure_category == "POLICY_VIOLATION"
        assert "CC_PLACEMENT_SUPERVISOR" in json.dumps(result.details)

    def test_object_shaped_source_ref_is_also_caught(self, tmp_path: Path) -> None:
        """``source_ref`` appears both as a string and as an object in real drafts."""
        _section(tmp_path, [
            {
                "claim_id": "CC_NO_PRIOR_FUNDED_HOSTING",
                "claim_summary": "operator-declared assumption",
                "status": "inferred",
                "source_ref": {"tier": 3, "source_path": WA_PATH},
            },
        ])
        assert not declared_facts_are_not_inferred(
            SECTION_REL, repo_root=tmp_path
        ).passed

    def test_every_violation_is_reported_not_just_the_first(
        self, tmp_path: Path
    ) -> None:
        _section(tmp_path, [
            {"claim_id": f"C{i}", "claim_summary": "x", "status": "inferred",
             "source_ref": WA_PATH}
            for i in range(3)
        ])
        result = declared_facts_are_not_inferred(SECTION_REL, repo_root=tmp_path)
        assert len(result.details["violations"]) == 3


class TestW2StaysNarrow:
    """It must not become a general-purpose judge of what ought to be assumed."""

    def test_genuinely_inferred_claim_passes(self, tmp_path: Path) -> None:
        _section(tmp_path, [
            {
                "claim_id": "CS-02",
                "claim_summary": "WP structure follows from the objectives",
                "status": "inferred",
                "source_ref": "docs/tier4_orchestration_state/wp_structure.json",
            },
        ])
        assert declared_facts_are_not_inferred(
            SECTION_REL, repo_root=tmp_path
        ).passed

    def test_assumed_claim_citing_declarations_passes(self, tmp_path: Path) -> None:
        """The correct labelling is precisely what W2 must not object to."""
        _section(tmp_path, [
            {
                "claim_id": "mobility_eligibility",
                "claim_summary": "Operator-declared assumption: ...",
                "status": "assumed",
                "source_ref": WA_PATH,
            },
        ])
        assert declared_facts_are_not_inferred(
            SECTION_REL, repo_root=tmp_path
        ).passed

    def test_confirmed_claim_citing_declarations_is_not_w2s_business(
        self, tmp_path: Path
    ) -> None:
        """W2 judges 'inferred' only; a wrongly-Confirmed claim is another rule.

        Narrowness is the point: a predicate that also policed 'confirmed' would
        be inferring which status a claim deserves, which is the judgment a gate
        predicate must not make.
        """
        _section(tmp_path, [
            {"claim_id": "X", "claim_summary": "y", "status": "confirmed",
             "source_ref": WA_PATH},
        ])
        assert declared_facts_are_not_inferred(
            SECTION_REL, repo_root=tmp_path
        ).passed

    def test_section_with_no_claims_passes(self, tmp_path: Path) -> None:
        _section(tmp_path, [])
        assert declared_facts_are_not_inferred(
            SECTION_REL, repo_root=tmp_path
        ).passed


class TestW2FailsClosed:
    def test_missing_section_fails(self, tmp_path: Path) -> None:
        result = declared_facts_are_not_inferred(SECTION_REL, repo_root=tmp_path)
        assert not result.passed
        assert result.failure_category == "MISSING_MANDATORY_INPUT"

    def test_non_array_claim_statuses_is_malformed(self, tmp_path: Path) -> None:
        path = tmp_path / SECTION_REL
        _write(path, {
            "schema_id": "orch.tier5.excellence_section.v1",
            "validation_status": {"claim_statuses": "not-an-array"},
        })
        result = declared_facts_are_not_inferred(SECTION_REL, repo_root=tmp_path)
        assert not result.passed
        assert result.failure_category == "MALFORMED_ARTIFACT"


class TestW2AgainstTheRealRegression:
    """The shape that actually shipped: W1 vacuous, W2 catching it."""

    def test_w1_passes_vacuously_where_w2_fails(self, tmp_path: Path) -> None:
        from runner.predicates import assumed_claims_are_operator_declared

        _section(tmp_path, [
            {"claim_id": "CC_NO_PRIOR_FUNDED_HOSTING", "claim_summary": "a",
             "status": "inferred", "source_ref": WA_PATH},
            {"claim_id": "CC_PLACEMENT_SUPERVISOR", "claim_summary": "b",
             "status": "inferred", "source_ref": WA_PATH},
            {"claim_id": "CC_PLACEMENT_WORKSPACE", "claim_summary": "c",
             "status": "inferred", "source_ref": WA_PATH},
        ])
        _write(tmp_path / WA_PATH, {
            "provenance_class": "manually_placed", "declarations": [],
        })

        # W1: no 'assumed' claims → nothing to audit → passes.  This is the
        # vacuity that let three mislabelled declarations through.
        assert assumed_claims_are_operator_declared(
            SECTION_REL, repo_root=tmp_path
        ).passed
        # W2: catches all three.
        result = declared_facts_are_not_inferred(SECTION_REL, repo_root=tmp_path)
        assert not result.passed
        assert len(result.details["violations"]) == 3
