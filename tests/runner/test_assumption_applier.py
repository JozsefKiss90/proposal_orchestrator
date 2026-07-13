"""Tests for runner.assumption_applier — the β honesty layer's pre-assembly flip.

Covers ticket 9's assumption-applier deterministic component (CLAUDE.md
§17.5.3 / C2):
  - flips ONLY enumerated declared ``unresolved → assumed`` claims (by claim_id),
  - never touches confirmed/inferred claims or undeclared unresolved claims,
  - re-derives the spine's overall_status so the assembled section is consistent,
  - preserves the assembler's byte-equal guarantee (apply → assemble is stable),
  - is idempotent (a second run finds nothing to flip and writes nothing),
  - α (no declarations) is a pure no-op,
  - a fault surfaces through invoke_component as a failure record.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from runner.assumption_applier import AssumptionApplierError, apply_assumptions
from runner.deterministic_components import invoke_component
from runner.section_assembler import (
    PROPOSAL_SECTIONS_REL,
    SECTION_DRAFTS_ROOT_REL,
    assemble_section,
)
from runner.working_assumptions import WORKING_ASSUMPTIONS_REL

RUN_ID = "run-applier-1"
HOST_CLAIM_ID = "spine.host"
HOST_VALUE = "University of Example (host, operator-declared)"


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _write(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _drafts_dir(repo_root: Path, slug: str = "excellence") -> Path:
    d = repo_root / SECTION_DRAFTS_ROOT_REL / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def _spine(**overrides: Any) -> dict[str, Any]:
    spine = {
        "schema_id": "orch.tier5.excellence_section.v1",
        "run_id": RUN_ID,
        "criterion": "Excellence",
        "sub_section_order": ["B.1.1", "B.1.2"],
        "overall_status": "unresolved",  # an unresolved host claim is present
        "no_unsupported_claims_declaration": True,
    }
    spine.update(overrides)
    return spine


def _draft_b11(**overrides: Any) -> dict[str, Any]:
    """B.1.1 — one confirmed claim + one UNRESOLVED host claim (the spine gap)."""
    draft = {
        "sub_section_id": "B.1.1",
        "title": "Objectives and ambition",
        "content": "Alpha beta gamma delta epsilon.",
        "claim_statuses": [
            {
                "claim_id": "CS-01",
                "claim_summary": "OBJ-1 target",
                "status": "confirmed",
                "source_ref": "tier3/objectives.json -> OBJ-1",
            },
            {
                "claim_id": HOST_CLAIM_ID,
                "claim_summary": "Host institution — UNCONFIRMED",
                "status": "unresolved",
            },
        ],
        "source_refs": [
            {"tier": 3, "source_path": "docs/tier3/objectives.json"},
        ],
    }
    draft.update(overrides)
    return draft


def _draft_b12(**overrides: Any) -> dict[str, Any]:
    draft = {
        "sub_section_id": "B.1.2",
        "title": "Methodology",
        "content": "One two three.",
        "claim_statuses": [
            {
                "claim_id": "CS-02",
                "claim_summary": "WP structure",
                "status": "inferred",
                "source_ref": "tier4/wp_structure.json",
            },
        ],
        "source_refs": [
            {"tier": 4, "source_path": "docs/tier4/wp_structure.json"},
        ],
    }
    draft.update(overrides)
    return draft


def _seed_drafts(repo_root: Path) -> Path:
    d = _drafts_dir(repo_root)
    _write(d / "section_spine.json", _spine())
    _write(d / "B.1.1.draft.json", _draft_b11())
    _write(d / "B.1.2.draft.json", _draft_b12())
    return d


def _declare_host(repo_root: Path, value: str = HOST_VALUE) -> None:
    """Write a Tier 3 working_assumptions.json declaring the host claim."""
    _write(
        repo_root / WORKING_ASSUMPTIONS_REL,
        {
            "provenance_class": "manually_placed",
            "declarations": [
                {
                    "key": HOST_CLAIM_ID,
                    "value": value,
                    "declared_by": "operator",
                    "declared_on": "2026-07-13",
                    "checklist_ref": "HOST",
                }
            ],
        },
    )


def _claims_of(draft_path: Path) -> list[dict[str, Any]]:
    return json.loads(draft_path.read_text("utf-8"))["claim_statuses"]


# ---------------------------------------------------------------------------
# The flip: declared unresolved → assumed
# ---------------------------------------------------------------------------


class TestDeclaredFlip:
    def test_declared_unresolved_claim_becomes_assumed(self, tmp_path: Path) -> None:
        d = _seed_drafts(tmp_path)
        _declare_host(tmp_path)

        written = apply_assumptions(RUN_ID, tmp_path, "excellence")

        host = next(
            c for c in _claims_of(d / "B.1.1.draft.json")
            if c["claim_id"] == HOST_CLAIM_ID
        )
        assert host["status"] == "assumed"
        assert host["claim_summary"] == HOST_VALUE  # summary := declared value
        assert host["assumption_declared"] is True
        # The draft and the spine were rewritten.
        assert (d / "B.1.1.draft.json") in written
        assert (d / "section_spine.json") in written

    def test_spine_overall_status_reflects_the_flip(self, tmp_path: Path) -> None:
        d = _seed_drafts(tmp_path)
        _declare_host(tmp_path)

        apply_assumptions(RUN_ID, tmp_path, "excellence")

        spine = json.loads((d / "section_spine.json").read_text("utf-8"))
        # confirmed + assumed + inferred  ->  worst is "assumed" (no longer unresolved)
        assert spine["overall_status"] == "assumed"

    def test_confirmed_claim_is_never_flipped(self, tmp_path: Path) -> None:
        """A declaration keyed to a confirmed claim must not re-judge it."""
        d = _drafts_dir(tmp_path)
        _write(d / "section_spine.json", _spine(overall_status="confirmed"))
        _write(
            d / "B.1.1.draft.json",
            _draft_b11(
                claim_statuses=[
                    {
                        "claim_id": "CS-01",
                        "claim_summary": "OBJ-1 target",
                        "status": "confirmed",
                        "source_ref": "tier3/objectives.json -> OBJ-1",
                    }
                ]
            ),
        )
        _write(d / "B.1.2.draft.json", _draft_b12())
        # Declare against the confirmed claim's id — the applier must ignore it.
        _write(
            tmp_path / WORKING_ASSUMPTIONS_REL,
            {
                "provenance_class": "manually_placed",
                "declarations": [
                    {
                        "key": "CS-01",
                        "value": "something else",
                        "declared_by": "operator",
                        "declared_on": "2026-07-13",
                    }
                ],
            },
        )

        written = apply_assumptions(RUN_ID, tmp_path, "excellence")

        cs01 = _claims_of(d / "B.1.1.draft.json")[0]
        assert cs01["status"] == "confirmed"
        assert cs01["claim_summary"] == "OBJ-1 target"
        assert written == []  # nothing changed

    def test_undeclared_unresolved_claim_stays_unresolved(
        self, tmp_path: Path
    ) -> None:
        """An unresolved claim with no matching declaration is left blocking."""
        d = _seed_drafts(tmp_path)
        # Declare a *different* key — the host claim has no backing.
        _write(
            tmp_path / WORKING_ASSUMPTIONS_REL,
            {
                "provenance_class": "manually_placed",
                "declarations": [
                    {
                        "key": "some.other.claim",
                        "value": "x",
                        "declared_by": "operator",
                        "declared_on": "2026-07-13",
                    }
                ],
            },
        )

        written = apply_assumptions(RUN_ID, tmp_path, "excellence")

        host = next(
            c for c in _claims_of(d / "B.1.1.draft.json")
            if c["claim_id"] == HOST_CLAIM_ID
        )
        assert host["status"] == "unresolved"
        assert written == []


# ---------------------------------------------------------------------------
# α no-op + determinism + idempotency (the determinism guarantee)
# ---------------------------------------------------------------------------


class TestAlphaAndDeterminism:
    def test_alpha_no_declarations_is_a_pure_noop(self, tmp_path: Path) -> None:
        d = _seed_drafts(tmp_path)
        before = {
            p.name: p.read_bytes() for p in sorted(d.glob("*.json"))
        }

        written = apply_assumptions(RUN_ID, tmp_path, "excellence")

        assert written == []
        after = {p.name: p.read_bytes() for p in sorted(d.glob("*.json"))}
        assert after == before  # not a single byte touched

    def test_empty_declarations_file_is_alpha(self, tmp_path: Path) -> None:
        _seed_drafts(tmp_path)
        _write(tmp_path / WORKING_ASSUMPTIONS_REL, {"declarations": []})
        assert apply_assumptions(RUN_ID, tmp_path, "excellence") == []

    def test_idempotent_second_run_writes_nothing(self, tmp_path: Path) -> None:
        d = _seed_drafts(tmp_path)
        _declare_host(tmp_path)

        first = apply_assumptions(RUN_ID, tmp_path, "excellence")
        assert first  # the first run flipped and wrote
        snapshot = {p.name: p.read_bytes() for p in sorted(d.glob("*.json"))}

        second = apply_assumptions(RUN_ID, tmp_path, "excellence")
        assert second == []  # nothing left to flip
        after = {p.name: p.read_bytes() for p in sorted(d.glob("*.json"))}
        assert after == snapshot  # byte-identical

    def test_apply_then_assemble_is_byte_stable(self, tmp_path: Path) -> None:
        """apply → assemble is deterministic across two full runs."""
        def run(root: Path) -> bytes:
            _seed_drafts(root)
            _declare_host(root)
            apply_assumptions(RUN_ID, root, "excellence")
            return assemble_section(RUN_ID, root, "excellence").read_bytes()

        a = run(tmp_path / "a")
        b = run(tmp_path / "b")
        assert a == b

    def test_assembled_section_carries_the_assumed_claim(
        self, tmp_path: Path
    ) -> None:
        _seed_drafts(tmp_path)
        _declare_host(tmp_path)
        apply_assumptions(RUN_ID, tmp_path, "excellence")

        out = json.loads(
            assemble_section(RUN_ID, tmp_path, "excellence").read_text("utf-8")
        )
        vs = out["validation_status"]
        assert vs["overall_status"] == "assumed"
        host = next(
            c for c in vs["claim_statuses"] if c["claim_id"] == HOST_CLAIM_ID
        )
        assert host["status"] == "assumed"
        assert host["claim_summary"] == HOST_VALUE


# ---------------------------------------------------------------------------
# Component substrate: bound, invoked, fault-surfaced
# ---------------------------------------------------------------------------


class TestComponentSubstrate:
    def test_invoke_component_success(self, tmp_path: Path) -> None:
        d = _seed_drafts(tmp_path)
        _declare_host(tmp_path)

        record = invoke_component(
            "excellence_assumption_applier", RUN_ID, tmp_path
        )

        assert record.status == "success"
        # Both rewritten artifacts recorded as repo-relative POSIX paths.
        assert any("B.1.1.draft.json" in o for o in record.outputs_written)
        assert any("section_spine.json" in o for o in record.outputs_written)

    def test_invoke_component_alpha_records_no_outputs(
        self, tmp_path: Path
    ) -> None:
        _seed_drafts(tmp_path)  # no declarations → α no-op
        record = invoke_component(
            "excellence_assumption_applier", RUN_ID, tmp_path
        )
        assert record.status == "success"
        assert record.outputs_written == []

    def test_invoke_component_fault_is_a_failure_record(
        self, tmp_path: Path
    ) -> None:
        # Declarations present but the drafts directory is missing → fault.
        _declare_host(tmp_path)
        record = invoke_component(
            "excellence_assumption_applier", RUN_ID, tmp_path
        )
        assert record.status == "failure"
        assert record.failure_reason


class TestFailClosed:
    def test_unknown_slug_raises(self, tmp_path: Path) -> None:
        with pytest.raises(AssumptionApplierError):
            apply_assumptions(RUN_ID, tmp_path, "nonsense")

    def test_missing_drafts_dir_with_declarations_raises(
        self, tmp_path: Path
    ) -> None:
        _declare_host(tmp_path)  # declarations present, but no drafts seeded
        with pytest.raises(AssumptionApplierError):
            apply_assumptions(RUN_ID, tmp_path, "excellence")
