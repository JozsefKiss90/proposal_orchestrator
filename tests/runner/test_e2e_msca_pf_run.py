"""Ticket 13 — MSCA-PF end-to-end definition-of-done harness (α / β).

This is the **deterministic guarantee-guard** for the milestone's definition of
done (D14).  Where the live run (``scripts/run_msca_pf_e2e.py``) proves the
*claim* (decomposed drafting fixes the ~10× length shortfall; the honest block /
conscious green work end-to-end) by making real ``claude`` calls, this harness
proves the *guarantees* hold — with **zero LLM calls** — by asserting the two
correct terminal states cohesively:

  α (no declarations)  → the unit-cost budget gate **blocks** honestly on the
                         Unresolved host coefficient + fellowship duration, with
                         the host-independent lines still computed (an
                         informative blocked assessment).  A block is a **PASS**
                         terminal state (§12.4 / §15), never "fixed" green.

  β (host + duration declared) → the budget gate **passes** (every line
                         Confirmed or operator-declared Assumed), the three
                         criterion sections draft (stood in by a deterministic
                         fake drafter) → apply-assumptions → assemble
                         **byte-equal** (no synthesis) → the drafting gates'
                         core predicates green (no Unresolved material claims;
                         W1 satisfied), and the assembled Part B renders to
                         ``.docx``.

The per-sub-section Claude call is stood in by a deterministic fake drafter, so
the whole decompose→apply→assemble→gate→export chain is exercised without a live
model.  The section-specific / preservation predicates (``impact_pathways_
covered``, ``implementation_coverage_complete``, the four canonical-preservation
detectors) are covered exhaustively by the ticket-7/9/11 tracer bullets; this
harness focuses on the cohesive **two-terminal-state** assertion plus the CI
byte-equal guarantees the milestone names.

A companion live-fixture replay (``TestLiveCaptureReplay``) additionally replays
the *actual* ``section_drafts/`` captured by the live β run through the same
byte-equal assembler, when those fixtures are present.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from runner.assumption_applier import apply_assumptions
from runner.decomposed_drafting import draft_section_decomposed
from runner.docx_exporter import export_part_b_docx
from runner.predicates import (
    assumed_claims_are_operator_declared,
    no_unresolved_material_claims,
)
from runner.section_assembler import (
    PROPOSAL_SECTIONS_REL,
    SECTION_DRAFTS_ROOT_REL,
    assemble_section,
)
from runner.unit_cost_budget import derive_unit_cost_budget
from runner.working_assumptions import WORKING_ASSUMPTIONS_REL

RUN_ID = "run-e2e-msca-pf-1"

_SELECTED_CALL_REL = (
    "docs/tier3_project_instantiation/call_binding/selected_call.json"
)
_RATES_REL = "docs/tier2b_topic_and_call_sources/extracted/unit_cost_rates.json"

# Profile sub-sections per criterion (MSCA-PF profile granularity).
_SUBS: dict[str, list[tuple[str, str]]] = {
    "excellence": [
        ("1.1", "Quality and pertinence of the objectives"),
        ("1.2", "Soundness of the proposed methodology"),
    ],
    "impact": [
        ("2.1", "Credibility of the measures to enhance career"),
        ("2.2", "Measures to communicate and disseminate"),
    ],
    "implementation": [
        ("3.1", "Coherence and effectiveness of the work plan"),
        ("3.2", "Quality of the host and resources"),
    ],
}
_CRITERION = {
    "excellence": "Excellence",
    "impact": "Impact",
    "implementation": "Implementation",
}
_EXTRA_FIELDS: dict[str, dict[str, Any]] = {
    "excellence": {},
    "impact": {
        "impact_pathway_refs": ["IP-1", "IP-2"],
        "dec_coverage": {
            "dissemination_addressed": True,
            "exploitation_addressed": True,
            "communication_addressed": True,
        },
    },
    "implementation": {
        "wp_table_refs": ["WP1", "WP2"],
        "gantt_ref": "docs/tier4/phase4/gantt.json",
        "milestone_refs": ["MS1", "MS2"],
        "risk_register_ref": (
            "docs/tier3_project_instantiation/architecture_inputs/risks.json"
        ),
    },
}


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------


def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def _rates() -> dict[str, Any]:
    """A minimal but valid unit_cost_rates.json (BE coefficient 100%)."""
    return {
        "schema_id": "orch.tier2b.unit_cost_rates.v1",
        "instrument_type": "MSCA-PF",
        "currency": "EUR",
        "researcher_unit_contributions": {
            "living_allowance": {"amount_eur_per_month": 6350, "host_dependent": True},
            "mobility_allowance": {"amount_eur_per_month": 710},
            "family_allowance": {"amount_eur_per_month": 660},
        },
        "institutional_unit_contributions": {
            "research_training_networking": {"amount_eur_per_month": 1000},
            "management_and_indirect": {"amount_eur_per_month": 650},
        },
        "country_correction_coefficient": {
            "coefficients_percent": {"BE": 100.0, "HU": 78.7},
        },
    }


def _seed_profile(repo_root: Path) -> None:
    sections: list[dict[str, Any]] = []
    for slug, subs in _SUBS.items():
        crit = _CRITERION[slug]
        parent = slug[0].upper()
        sections.append({
            "section_id": parent, "section_name": crit,
            "section_type": "criterion_section", "criterion": crit,
            "mandatory": True,
        })
        for sid, name in subs:
            sections.append({
                "section_id": sid, "section_name": name,
                "section_type": "proposal_section", "criterion": crit,
                "parent_section_id": parent, "mandatory": True,
                "field_requirements": [f"Describe {name.lower()}."],
            })
    _write(
        repo_root
        / "docs/tier2a_instrument_schemas/extracted/section_schema_registry.json",
        {"instruments": [{
            "instrument_type": "MSCA-PF", "part_b_page_limit_hard": 10,
            "sections": sections,
        }]},
    )
    _write(
        repo_root
        / "docs/tier2a_instrument_schemas/extracted/instrument_registry.json",
        {"instruments": [{
            "instrument_type": "MSCA-PF", "budget_regime": "unit_cost",
            "phases_in_scope": [1, 2, 3, 4, 5, 6, 7, 8],
        }]},
    )


def _seed_env(repo_root: Path, *, declarations: bool) -> None:
    _seed_profile(repo_root)
    _write(repo_root / _RATES_REL, _rates())
    _write(repo_root / _SELECTED_CALL_REL, {
        "instrument_type": "MSCA-PF", "budget_regime": "unit_cost",
        "work_programme": "msca", "topic_code": "HORIZON-MSCA-2026-PF-01-01",
        "max_project_duration_months": 36,
    })
    if declarations:
        _write(repo_root / WORKING_ASSUMPTIONS_REL, {
            "record_type": "working_assumptions",
            "provenance_class": "manually_placed",
            "declarations": [
                {"key": "host_country", "value": "BE",
                 "declared_by": "operator", "declared_on": "2026-07-14",
                 "checklist_ref": "HOST"},
                {"key": "project_duration_months", "value": 24,
                 "declared_by": "operator", "declared_on": "2026-07-14",
                 "checklist_ref": "DURATION"},
            ],
        })


class _FakeDrafter:
    """Deterministic full-length drafter: confirmed claims, no fabrication."""

    def __init__(self, *, chars_per_sub: int = 4000) -> None:
        self.chars_per_sub = chars_per_sub

    def __call__(
        self, sub: dict[str, Any], criterion: str,
        prior_drafts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        sid = sub["section_id"]
        sentence = f"Sub-section {sid} of {criterion} develops the argument in full. "
        content = (sentence * ((self.chars_per_sub // len(sentence)) + 1))[
            : self.chars_per_sub
        ]
        return {
            "content": content,
            "claim_statuses": [{
                "claim_id": f"CS-{sid}", "claim_summary": f"claim {sid}",
                "status": "confirmed",
                "source_ref": "tier3/architecture_inputs.json",
            }],
            "source_refs": [
                {"tier": 3, "source_path": "docs/tier3/architecture_inputs.json"},
            ],
        }


def _draft_apply_assemble(repo_root: Path, slug: str) -> Path:
    draft_section_decomposed(
        RUN_ID, repo_root, slug,
        drafter=_FakeDrafter(), extra_fields=_EXTRA_FIELDS[slug] or None,
    )
    apply_assumptions(RUN_ID, repo_root, slug)
    return assemble_section(RUN_ID, repo_root, slug)


# ---------------------------------------------------------------------------
# α — honest block (a correct terminal state)
# ---------------------------------------------------------------------------


class TestAlphaHonestBlock:
    def test_budget_gate_blocks_on_unresolved_spine(self, tmp_path: Path) -> None:
        _seed_env(tmp_path, declarations=False)  # no working_assumptions.json
        out = derive_unit_cost_budget(RUN_ID, tmp_path)
        data = json.loads(out.read_text("utf-8"))

        # The block is honest and informative, not a crash.
        assert data["gate_pass_declaration"] == "fail"
        unresolved = data["unresolved_components"]
        assert "host_coefficient_unresolved" in unresolved
        assert "confirmed_months_unresolved" in unresolved
        # No total is asserted while any line is Unresolved.
        assert data["total_eur"] is None

    def test_no_section_is_produced_under_the_block(self, tmp_path: Path) -> None:
        # α never reaches Phase 8: no drafts, no assembled sections.
        _seed_env(tmp_path, declarations=False)
        derive_unit_cost_budget(RUN_ID, tmp_path)
        assert not (tmp_path / PROPOSAL_SECTIONS_REL).exists()
        assert not (tmp_path / SECTION_DRAFTS_ROOT_REL).exists()


# ---------------------------------------------------------------------------
# β — conscious green (host + duration declared)
# ---------------------------------------------------------------------------


class TestBetaAllGreen:
    def test_budget_gate_passes_with_declarations(self, tmp_path: Path) -> None:
        _seed_env(tmp_path, declarations=True)
        out = derive_unit_cost_budget(RUN_ID, tmp_path)
        data = json.loads(out.read_text("utf-8"))
        assert data["gate_pass_declaration"] == "pass"
        assert data["derivation"]["host_country_status"] == "Assumed"
        assert data["derivation"]["confirmed_months_status"] == "Assumed"
        assert isinstance(data["total_eur"], (int, float))

    def test_unit_cost_budget_is_byte_equal_on_replay(self, tmp_path: Path) -> None:
        _seed_env(tmp_path, declarations=True)
        first = derive_unit_cost_budget(RUN_ID, tmp_path).read_bytes()
        second = derive_unit_cost_budget(RUN_ID, tmp_path).read_bytes()
        assert first == second  # deterministic derivation (CI guarantee)

    @pytest.mark.parametrize("slug", ["excellence", "impact", "implementation"])
    def test_section_assembles_byte_equal_and_greens(
        self, tmp_path: Path, slug: str
    ) -> None:
        _seed_env(tmp_path, declarations=True)
        section_path = _draft_apply_assemble(tmp_path, slug)
        section = json.loads(section_path.read_text("utf-8"))

        # Byte-equal replay of the assembler (no synthesis by construction).
        replay = assemble_section(RUN_ID, tmp_path, slug).read_bytes()
        assert section_path.read_bytes() == replay

        # Full-length (materially exceeds the old monolithic per-sub cap).
        assert sum(len(s["content"]) for s in section["sub_sections"]) > 2500 * len(
            _SUBS[slug]
        )

        # Core drafting-gate predicates green: no Unresolved claims; W1 vacuous
        # (no Assumed claims to police — every claim is confirmed).
        assert no_unresolved_material_claims(str(section_path), repo_root=tmp_path).passed
        assert assumed_claims_are_operator_declared(
            str(section_path), repo_root=tmp_path
        ).passed

    def test_assembled_sections_export_to_docx(self, tmp_path: Path) -> None:
        _seed_env(tmp_path, declarations=True)
        for slug in ("excellence", "impact", "implementation"):
            _draft_apply_assemble(tmp_path, slug)
        out = export_part_b_docx(tmp_path)
        assert out is not None
        assert out.suffix == ".docx"
        assert out.stat().st_size > 0


# ---------------------------------------------------------------------------
# Live-capture replay — replays the ACTUAL section_drafts/ produced by the live
# β run through the same byte-equal assembler.  This is the fixtures half of the
# hybrid: the non-deterministic drafting was captured once (§9.5 / W2); here it
# replays deterministically with zero LLM calls.  Skips when the fixtures are
# absent (they are committed by the live run, ``scripts/run_msca_pf_e2e.py``).
# ---------------------------------------------------------------------------


_FIXTURES = Path(__file__).resolve().parents[2] / "tests/fixtures/e2e_msca_pf"


def _copy_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for child in src.iterdir():
        if child.is_file():
            (dst / child.name).write_bytes(child.read_bytes())


class TestLiveCaptureReplay:
    """Replay the committed live β drafts through the byte-equal assembler."""

    @pytest.mark.parametrize("slug", ["excellence", "impact", "implementation"])
    def test_live_drafts_assemble_byte_equal(
        self, tmp_path: Path, slug: str
    ) -> None:
        drafts_src = _FIXTURES / "beta" / "section_drafts" / slug
        section_fixture = _FIXTURES / "beta" / f"{slug}_section.json"
        if not drafts_src.is_dir() or not section_fixture.is_file():
            pytest.skip(f"live β fixtures for {slug} not captured yet")

        # The captured spine carries the live run_id the assembler enforces.
        spine = json.loads((drafts_src / "section_spine.json").read_text("utf-8"))
        run_id = spine["run_id"]

        # Replay the assembler over the captured drafts in an isolated root.
        _copy_tree(drafts_src, tmp_path / SECTION_DRAFTS_ROOT_REL / slug)
        assembled = assemble_section(run_id, tmp_path, slug)

        # Byte-equal to the committed section the live run produced: the
        # governed replay reproduces the deliverable with no synthesis.
        assert assembled.read_bytes() == section_fixture.read_bytes()

    def test_live_alpha_budget_is_an_informative_block(self) -> None:
        budget = _FIXTURES / "alpha" / "unit_cost_budget.json"
        if not budget.is_file():
            pytest.skip("live α budget fixture not captured yet")
        data = json.loads(budget.read_text("utf-8"))
        assert data["gate_pass_declaration"] == "fail"
        # Host-independent lines were still computed (rides free under block).
        assert any(
            li.get("status") == "Confirmed" for li in data.get("line_items", [])
        )
        assert "host_coefficient_unresolved" in data["unresolved_components"]
