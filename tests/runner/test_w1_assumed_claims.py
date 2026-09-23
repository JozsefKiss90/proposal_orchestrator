"""Tests for the W1 predicate ``assumed_claims_are_operator_declared`` (ticket 9).

W1 is the β honesty guarantee (CLAUDE.md §13.3): every ``assumed`` claim in a
section must map by ``claim_id`` to a ``manually_placed`` operator declaration
whose declared value equals the claim's ``claim_summary``.  Because the reader
parses only the operator file, a ``run_produced`` value can never back an
``assumed`` claim.

The final class demonstrates ticket 9 **both ways on Excellence**: with a
declaration an ``unresolved`` claim greens as ``assumed`` (W1 + the unresolved
check both pass); without it, an ``assumed`` claim is blocked by W1, and an
undeclared ``unresolved`` claim is blocked by ``no_unresolved_material_claims``
(the honest block, α).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from runner.assumption_applier import apply_assumptions
from runner.predicates import (
    assumed_claims_are_operator_declared,
    no_unresolved_material_claims,
)
from runner.section_assembler import SECTION_DRAFTS_ROOT_REL, assemble_section
from runner.working_assumptions import WORKING_ASSUMPTIONS_REL

RUN_ID = "run-w1-1"
HOST_CLAIM_ID = "spine.host"
HOST_VALUE = "University of Example (host, operator-declared)"
SECTION_REL = "docs/tier5_deliverables/proposal_sections/excellence_section.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _section(claims: list[dict[str, Any]], overall: str = "assumed") -> dict[str, Any]:
    return {
        "schema_id": "orch.tier5.excellence_section.v1",
        "run_id": RUN_ID,
        "criterion": "Excellence",
        "sub_sections": [
            {"sub_section_id": "B.1.1", "title": "T", "content": "c", "word_count": 1}
        ],
        "validation_status": {"overall_status": overall, "claim_statuses": claims},
        "traceability_footer": {
            "primary_sources": [{"tier": 3, "source_path": "docs/tier3/x.json"}],
            "no_unsupported_claims_declaration": True,
        },
    }


def _declare(repo_root: Path, key: str, value: Any) -> None:
    _write(
        repo_root / WORKING_ASSUMPTIONS_REL,
        {
            "provenance_class": "manually_placed",
            "declarations": [
                {
                    "key": key,
                    "value": value,
                    "declared_by": "operator",
                    "declared_on": "2026-07-13",
                }
            ],
        },
    )


def _assumed_claim(**overrides: Any) -> dict[str, Any]:
    claim = {
        "claim_id": HOST_CLAIM_ID,
        "claim_summary": HOST_VALUE,
        "status": "assumed",
        "assumption_declared": True,
    }
    claim.update(overrides)
    return claim


# ---------------------------------------------------------------------------
# W1 unit behaviour
# ---------------------------------------------------------------------------


class TestW1Predicate:
    def test_no_assumed_claims_passes_vacuously(self, tmp_path: Path) -> None:
        _write(tmp_path / "s.json", _section(
            [{"claim_id": "CS-01", "claim_summary": "x", "status": "confirmed"}],
            overall="confirmed",
        ))
        result = assumed_claims_are_operator_declared("s.json", repo_root=tmp_path)
        assert result.passed

    def test_assumed_claim_backed_by_declaration_passes(self, tmp_path: Path) -> None:
        _write(tmp_path / "s.json", _section([_assumed_claim()]))
        _declare(tmp_path, HOST_CLAIM_ID, HOST_VALUE)
        result = assumed_claims_are_operator_declared("s.json", repo_root=tmp_path)
        assert result.passed

    def test_assumed_claim_without_declaration_fails(self, tmp_path: Path) -> None:
        """The core anti-fabrication case: no operator declaration at all."""
        _write(tmp_path / "s.json", _section([_assumed_claim()]))
        # No working_assumptions.json → mode α, no declarations.
        result = assumed_claims_are_operator_declared("s.json", repo_root=tmp_path)
        assert not result.passed
        assert result.failure_category == "POLICY_VIOLATION"
        assert result.details["violations"][0]["claim_id"] == HOST_CLAIM_ID

    def test_run_produced_value_cannot_back_an_assumed(self, tmp_path: Path) -> None:
        """A value that exists only in a run_produced artifact is not a
        declaration — W1 still blocks (§13.3)."""
        _write(tmp_path / "s.json", _section([_assumed_claim()]))
        # A run_produced artifact carrying the same value is irrelevant: only
        # the manually_placed declaration file counts, and it is absent.
        _write(
            tmp_path / "docs/tier4_orchestration_state/run_produced.json",
            {"host": HOST_VALUE},
        )
        result = assumed_claims_are_operator_declared("s.json", repo_root=tmp_path)
        assert not result.passed
        assert result.failure_category == "POLICY_VIOLATION"

    def test_value_mismatch_fails(self, tmp_path: Path) -> None:
        _write(tmp_path / "s.json", _section([_assumed_claim()]))
        _declare(tmp_path, HOST_CLAIM_ID, "a different declared value")
        result = assumed_claims_are_operator_declared("s.json", repo_root=tmp_path)
        assert not result.passed
        assert result.failure_category == "POLICY_VIOLATION"
        assert result.details["violations"][0]["issue"].startswith(
            "claim_summary does not equal"
        )

    def test_assumed_claim_without_claim_id_fails(self, tmp_path: Path) -> None:
        claim = _assumed_claim()
        del claim["claim_id"]
        _write(tmp_path / "s.json", _section([claim]))
        _declare(tmp_path, HOST_CLAIM_ID, HOST_VALUE)
        result = assumed_claims_are_operator_declared("s.json", repo_root=tmp_path)
        assert not result.passed
        assert result.failure_category == "POLICY_VIOLATION"

    def test_malformed_working_assumptions_fails_closed(self, tmp_path: Path) -> None:
        _write(tmp_path / "s.json", _section([_assumed_claim()]))
        # Present with declarations but wrong provenance_class → reader raises.
        _write(
            tmp_path / WORKING_ASSUMPTIONS_REL,
            {
                "provenance_class": "run_produced",
                "declarations": [
                    {
                        "key": HOST_CLAIM_ID,
                        "value": HOST_VALUE,
                        "declared_by": "x",
                        "declared_on": "2026-07-13",
                    }
                ],
            },
        )
        result = assumed_claims_are_operator_declared("s.json", repo_root=tmp_path)
        assert not result.passed
        assert result.failure_category == "MALFORMED_ARTIFACT"

    def test_missing_section_fails(self, tmp_path: Path) -> None:
        result = assumed_claims_are_operator_declared("nope.json", repo_root=tmp_path)
        assert not result.passed
        assert result.failure_category == "MISSING_MANDATORY_INPUT"

    def test_absent_validation_status_passes(self, tmp_path: Path) -> None:
        _write(tmp_path / "s.json", {"schema_id": "x", "run_id": RUN_ID})
        result = assumed_claims_are_operator_declared("s.json", repo_root=tmp_path)
        assert result.passed

    def test_non_string_declared_value_matches_rendered_summary(
        self, tmp_path: Path
    ) -> None:
        """A non-string declared value is matched via its canonical rendering."""
        _write(tmp_path / "s.json", _section([_assumed_claim(claim_summary="36")]))
        _declare(tmp_path, HOST_CLAIM_ID, 36)  # int value → rendered "36"
        result = assumed_claims_are_operator_declared("s.json", repo_root=tmp_path)
        assert result.passed


# ---------------------------------------------------------------------------
# Both ways on Excellence (ticket 9's demonstration criterion)
# ---------------------------------------------------------------------------


def _seed_excellence_with_unresolved_host(repo_root: Path) -> None:
    d = repo_root / SECTION_DRAFTS_ROOT_REL / "excellence"
    d.mkdir(parents=True, exist_ok=True)
    _write(d / "section_spine.json", {
        "schema_id": "orch.tier5.excellence_section.v1",
        "run_id": RUN_ID,
        "criterion": "Excellence",
        "sub_section_order": ["B.1.1"],
        "overall_status": "unresolved",
        "no_unsupported_claims_declaration": True,
    })
    _write(d / "B.1.1.draft.json", {
        "sub_section_id": "B.1.1",
        "title": "Objectives",
        "content": "Alpha beta gamma.",
        "claim_statuses": [
            {
                "claim_id": HOST_CLAIM_ID,
                "claim_summary": "Host institution — UNCONFIRMED",
                "status": "unresolved",
            }
        ],
        "source_refs": [{"tier": 3, "source_path": "docs/tier3/objectives.json"}],
    })


class TestBothWaysOnExcellence:
    def test_beta_declaration_greens_the_section(self, tmp_path: Path) -> None:
        """With a declaration, the unresolved host claim greens as assumed and
        both the unresolved-check and W1 pass — a conscious green."""
        _seed_excellence_with_unresolved_host(tmp_path)
        _declare(tmp_path, HOST_CLAIM_ID, HOST_VALUE)

        apply_assumptions(RUN_ID, tmp_path, "excellence")
        assemble_section(RUN_ID, tmp_path, "excellence")

        unresolved = no_unresolved_material_claims(SECTION_REL, repo_root=tmp_path)
        w1 = assumed_claims_are_operator_declared(SECTION_REL, repo_root=tmp_path)
        assert unresolved.passed  # overall_status flipped to "assumed"
        assert w1.passed          # the assumed claim is operator-declared

    def test_alpha_no_declaration_blocks_honestly(self, tmp_path: Path) -> None:
        """Without a declaration, the claim stays unresolved: the section is
        blocked by the unresolved-check (α honest block), and W1 is vacuous."""
        _seed_excellence_with_unresolved_host(tmp_path)
        # No declaration.

        written = apply_assumptions(RUN_ID, tmp_path, "excellence")
        assert written == []  # applier is a pure no-op in α
        assemble_section(RUN_ID, tmp_path, "excellence")

        unresolved = no_unresolved_material_claims(SECTION_REL, repo_root=tmp_path)
        w1 = assumed_claims_are_operator_declared(SECTION_REL, repo_root=tmp_path)
        assert not unresolved.passed             # honest block on the spine gap
        assert unresolved.failure_category == "POLICY_VIOLATION"
        assert w1.passed                          # no assumed claim ⇒ W1 inert
