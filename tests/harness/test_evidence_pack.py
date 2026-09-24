"""
E5b — deterministic evidence-pack builder: selection, budget, explicit truncation.

Offline, zero judge, zero DAG runs.  Fixture sections exercise the selection
grammar (term matching, anchor bonus, document order), the budget contract
(over-budget exclusions flip the pack to ``insufficient_context`` — an explicit
outcome, never a silent short pack), and the no-silent-caps record; real-file
tests assert every pack for the 9 PF rubrics fits one judge call under the
Groq TPM ceiling.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import harness.evidence_pack as ep
from harness.expectations import section_paths_for
from harness.judge import DEFAULT_JUDGE_MAX_TOKENS
from harness.profile import default_profile
from harness.rubrics import build_pack_for, load_rubric_set

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE = default_profile(REPO_ROOT)


# --------------------------------------------------------------------------- #
# Fixture section
# --------------------------------------------------------------------------- #


def _section_data() -> dict:
    return {
        "schema_id": "orch.tier5.excellence_section.v1",
        "criterion": "Excellence",
        "sub_sections": [
            {
                "sub_section_id": "1.1",
                "title": "Objectives",
                "content": (
                    "The objectives are ambitious and pertinent.\n\n"
                    "A connective filler paragraph carrying no keyword.\n\n"
                    "We go beyond the state of the art in modelling."
                ),
            },
            {
                "sub_section_id": "1.2",
                "title": "Methodology",
                "content": (
                    "The methodology uses hosted infrastructure.\n\n"
                    "One further objective is stated here, ambitious in scope."
                ),
            },
        ],
        "validation_status": {
            "overall_status": "inferred",
            "claim_statuses": [
                {
                    "claim_id": "C01",
                    "claim_summary": "The objectives target modelling advances.",
                    "status": "confirmed",
                    "source_ref": "docs/tier3/a.json#x",
                },
                {
                    "claim_id": "C02",
                    "claim_summary": "Something entirely unrelated to any term.",
                    "status": "confirmed",
                    "source_ref": "docs/tier3/b.json",
                },
                {
                    "claim_id": "C01",
                    "claim_summary": "An ambitious objective on data reuse.",
                    "status": "inferred",
                    "source_ref": "docs/tier3/c.json",
                },
            ],
        },
    }


TERMS = ("objective", "objectives", "ambitious", "state of the art")


@pytest.fixture()
def section_path(tmp_path: Path) -> Path:
    p = tmp_path / "excellence_section.json"
    p.write_text(json.dumps(_section_data(), ensure_ascii=False), encoding="utf-8")
    return p


def _build(section_path: Path, **kw) -> ep.EvidencePack:
    defaults = dict(
        expectation_key="exc-obj",
        section_path=section_path,
        selection_terms=TERMS,
        anchor_sub_section_ids=("1.1",),
    )
    defaults.update(kw)
    return ep.build_evidence_pack(**defaults)


# --------------------------------------------------------------------------- #
# Selection
# --------------------------------------------------------------------------- #


class TestSelection:
    def test_term_matching_spans_included(self, section_path):
        pack = _build(section_path)
        keys = [s.key for s in pack.spans]
        assert "1.1¶0" in keys  # "objectives ... ambitious"
        assert "1.1¶2" in keys  # "state of the art"
        assert "1.2¶1" in keys  # "objective ... ambitious" outside the anchor

    def test_anchor_grants_candidacy_to_term_free_paragraph(self, section_path):
        pack = _build(section_path)
        anchored_filler = next(s for s in pack.spans if s.key == "1.1¶1")
        assert anchored_filler.matched_terms == ()
        assert anchored_filler.in_anchor is True

    def test_without_anchor_term_free_paragraph_is_not_relevant(self, section_path):
        pack = _build(section_path, anchor_sub_section_ids=())
        assert all(s.key != "1.1¶1" for s in pack.spans)
        excl = {e.key: e for e in pack.excluded if e.kind == "prose_span"}
        assert excl["1.1¶1"].reason == ep.EXCLUDED_NOT_RELEVANT

    def test_word_boundary_no_substring_match(self, section_path):
        # "hosted" must not match the term "host" (word-boundary, not substring).
        pack = _build(
            section_path, selection_terms=("host",), anchor_sub_section_ids=()
        )
        assert pack.is_empty
        assert pack.status == ep.PACK_COMPLETE

    def test_phrase_term_and_case_insensitivity(self, section_path):
        pack = _build(
            section_path,
            selection_terms=("STATE OF THE ART",),
            anchor_sub_section_ids=(),
        )
        assert [s.key for s in pack.spans] == ["1.1¶2"]

    def test_claims_matched_by_terms_with_entry_key_disambiguation(self, section_path):
        pack = _build(section_path)
        claim_keys = [c.key for c in pack.claims]
        # Two C01 entries at ledger positions 0 and 2 — E3a identity discipline.
        assert claim_keys == ["C01#0", "C01#2"]
        excl = {e.key: e for e in pack.excluded if e.kind == "claim"}
        assert excl["C02#1"].reason == ep.EXCLUDED_NOT_RELEVANT

    def test_included_items_are_in_document_order(self, section_path):
        pack = _build(section_path)
        span_keys = [s.key for s in pack.spans]
        assert span_keys == sorted(
            span_keys, key=lambda k: [s.key for s in pack.spans].index(k)
        )
        # Explicit: 1.1 paragraphs precede 1.2 paragraphs even though ranks differ.
        assert span_keys.index("1.1¶0") < span_keys.index("1.2¶1")

    def test_determinism(self, section_path):
        a = _build(section_path)
        b = _build(section_path)
        assert a.to_dict() == b.to_dict()
        assert a.render() == b.render()


# --------------------------------------------------------------------------- #
# Budget + explicit truncation
# --------------------------------------------------------------------------- #


class TestBudget:
    def test_small_budget_is_explicit_insufficient_context(self, section_path):
        pack = _build(section_path, token_budget=120)
        assert pack.status == ep.PACK_INSUFFICIENT_CONTEXT
        assert ep.pack_forbids_clean_pass(pack)
        over = [e for e in pack.excluded if e.reason == ep.EXCLUDED_OVER_BUDGET]
        assert over, "over-budget exclusions must be part of the record"

    def test_ample_budget_is_complete_and_within_budget(self, section_path):
        pack = _build(section_path)
        assert pack.status == ep.PACK_COMPLETE
        assert not ep.pack_forbids_clean_pass(pack)
        assert pack.token_estimate <= pack.token_budget
        assert not [e for e in pack.excluded if e.reason == ep.EXCLUDED_OVER_BUDGET]

    def test_budget_hard_cap_enforced(self, section_path):
        with pytest.raises(ep.EvidencePackError, match="TPM"):
            _build(section_path, token_budget=ep.MAX_PACK_TOKEN_BUDGET + 1)
        with pytest.raises(ep.EvidencePackError):
            _build(section_path, token_budget=0)

    def test_hard_cap_leaves_room_for_one_judge_call(self):
        assert (
            ep.MAX_PACK_TOKEN_BUDGET
            + DEFAULT_JUDGE_MAX_TOKENS
            + ep.RUBRIC_PROMPT_ALLOWANCE
            == ep.GROQ_TPM_LIMIT
        )
        assert ep.DEFAULT_PACK_TOKEN_BUDGET <= ep.MAX_PACK_TOKEN_BUDGET

    def test_span_fraction_bounds(self, section_path):
        for bad in (0.0, 1.0, -0.2):
            with pytest.raises(ep.EvidencePackError, match="span_budget_fraction"):
                _build(section_path, span_budget_fraction=bad)

    def test_budget_too_small_for_frame_raises(self, section_path):
        with pytest.raises(ep.EvidencePackError, match="frame"):
            _build(section_path, token_budget=10)


# --------------------------------------------------------------------------- #
# Fail-closed inputs
# --------------------------------------------------------------------------- #


class TestFailClosed:
    def test_missing_anchor_raises(self, section_path):
        with pytest.raises(ep.EvidencePackError, match="anchor"):
            _build(section_path, anchor_sub_section_ids=("9.9",))

    def test_empty_terms_raise(self, section_path):
        with pytest.raises(ep.EvidencePackError, match="selection_terms"):
            _build(section_path, selection_terms=("", "  "))

    def test_empty_expectation_key_raises(self, section_path):
        with pytest.raises(ep.EvidencePackError, match="expectation_key"):
            _build(section_path, expectation_key=" ")

    def test_missing_section_raises(self, tmp_path):
        with pytest.raises(ep.EvidencePackError, match="not found"):
            _build(tmp_path / "nope.json")

    def test_invalid_json_raises(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not json", encoding="utf-8")
        with pytest.raises(ep.EvidencePackError, match="valid JSON"):
            _build(p)

    def test_no_sub_sections_raises(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text(json.dumps({"validation_status": {"claim_statuses": []}}))
        with pytest.raises(ep.EvidencePackError, match="sub_sections"):
            _build(p)


# --------------------------------------------------------------------------- #
# Rendering + record
# --------------------------------------------------------------------------- #


class TestRenderAndRecord:
    def test_render_carries_identity_and_status(self, section_path):
        pack = _build(section_path)
        text = pack.render()
        assert "expectation_key: exc-obj" in text
        assert "section: excellence_section" in text
        assert f"pack_status: {ep.PACK_COMPLETE}" in text
        assert ep.SPAN_DIVIDER in text and ep.CLAIM_DIVIDER in text

    def test_claim_render_carries_status_and_source_ref_verbatim(self, section_path):
        pack = _build(section_path)
        text = pack.render()
        assert "[claim C01#0 | status=confirmed | source_ref=docs/tier3/a.json#x]" in text

    def test_to_dict_records_selection_basis_and_exclusions(self, section_path):
        d = _build(section_path).to_dict()
        assert d["selection_terms"] == [t.lower() for t in TERMS]
        assert d["anchor_sub_section_ids"] == ["1.1"]
        assert {e["reason"] for e in d["excluded"]} <= {
            ep.EXCLUDED_NOT_RELEVANT,
            ep.EXCLUDED_OVER_BUDGET,
        }
        # Every candidate is accounted for: included or excluded, never dropped.
        n_spans_total = 5  # 3 paragraphs in 1.1 + 2 in 1.2
        n_claims_total = 3
        assert len(d["spans"]) + sum(
            1 for e in d["excluded"] if e["kind"] == "prose_span"
        ) == n_spans_total
        assert len(d["claims"]) + sum(
            1 for e in d["excluded"] if e["kind"] == "claim"
        ) == n_claims_total

    def test_token_estimate_subadditivity(self, section_path):
        pack = _build(section_path)
        parts = (
            ep.estimate_tokens(
                ep._render_frame(pack.expectation_key, pack.section_id, pack.status)
            )
            + sum(s.token_estimate for s in pack.spans)
            + sum(c.token_estimate for c in pack.claims)
        )
        assert pack.token_estimate <= parts


# --------------------------------------------------------------------------- #
# Real artifacts — the default profile's rubrics against the committed sections
# --------------------------------------------------------------------------- #


class TestRealSections:
    @pytest.fixture(scope="class")
    def rubric_set(self):
        live = REPO_ROOT / "docs/tier5_deliverables/proposal_sections"
        if not any(live.glob("*.json")):
            pytest.skip("no live Tier 5 sections in this checkout (empty project instantiation)")
        return load_rubric_set(profile=PROFILE, repo_root=REPO_ROOT)

    def test_every_rubric_yields_a_bounded_consistent_pack(self, rubric_set):
        for rubric in rubric_set.rubrics:
            (path,) = section_paths_for(rubric.criterion_id, repo_root=REPO_ROOT, profile=PROFILE)
            pack = build_pack_for(rubric, path)
            assert pack.status in (ep.PACK_COMPLETE, ep.PACK_INSUFFICIENT_CONTEXT)
            assert not pack.is_empty, rubric.expectation_key
            assert pack.token_estimate <= pack.token_budget
            over = [
                e for e in pack.excluded if e.reason == ep.EXCLUDED_OVER_BUDGET
            ]
            # Consistency, not content: truncation and status must agree.
            assert bool(over) == (pack.status == ep.PACK_INSUFFICIENT_CONTEXT)

    def test_one_judge_call_fits_the_tpm_ceiling(self, rubric_set):
        from harness.rubrics import build_rubric_prompts

        for rubric in rubric_set.rubrics:
            (path,) = section_paths_for(rubric.criterion_id, repo_root=REPO_ROOT, profile=PROFILE)
            pack = build_pack_for(rubric, path)
            system, user = build_rubric_prompts(rubric, pack)
            call_estimate = (
                ep.estimate_tokens(system)
                + ep.estimate_tokens(user)
                + DEFAULT_JUDGE_MAX_TOKENS
            )
            assert call_estimate <= ep.GROQ_TPM_LIMIT, rubric.expectation_key

    def test_rubric_prompt_overhead_fits_the_allowance(self, rubric_set):
        """The "fits by construction" guard: every rubric's non-pack prompt
        overhead (system prompt + closing question) must stay under
        RUBRIC_PROMPT_ALLOWANCE, or MAX_PACK_TOKEN_BUDGET's arithmetic is a lie."""
        from harness.rubrics import build_rubric_prompts

        for rubric in rubric_set.rubrics:
            (path,) = section_paths_for(rubric.criterion_id, repo_root=REPO_ROOT, profile=PROFILE)
            pack = build_pack_for(rubric, path)
            system, user = build_rubric_prompts(rubric, pack)
            question = user[len(pack.render()):]
            overhead = ep.estimate_tokens(system) + ep.estimate_tokens(question)
            assert overhead <= ep.RUBRIC_PROMPT_ALLOWANCE, (
                rubric.expectation_key,
                overhead,
            )
