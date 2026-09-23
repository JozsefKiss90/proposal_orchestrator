"""
Tests for harness/materiality.py — the E3 §10.5 materiality classifier +
its ledger-anchored calibration.

Fully offline: the classifier is driven by an injected fake backend (no
network); seeding/IO use tmp_path.  The load-bearing case is the calibration
precision guard: a positives-only set must report precision=None, never a
spurious 1.0.
"""

from __future__ import annotations

import json
from typing import Any, Callable

import pytest

import harness.materiality as mat
from harness.gold_set import TO_BE_LABELED
from harness.judge import Judge, JudgeConfig, JudgeResponseError
from harness.status_faithfulness import SectionClaim


# --------------------------------------------------------------------------- #
# Fakes (E2 idiom)
# --------------------------------------------------------------------------- #


class RuleBackend:
    def __init__(self, rule: Callable[[str, str], dict[str, Any]]) -> None:
        self._rule = rule
        self.calls: list[tuple[str, str]] = []

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        system = messages[0]["content"]
        user = messages[1]["content"]
        self.calls.append((system, user))
        return {"content": json.dumps(self._rule(system, user)), "tool_calls": None}


def make_judge(rule: Callable[[str, str], dict[str, Any]]) -> tuple[Judge, RuleBackend]:
    backend = RuleBackend(rule)
    judge = Judge(JudgeConfig(model="acme-judge-1", version="v1"), backend=backend)
    return judge, backend


def always(payload: dict[str, Any]) -> Callable[[str, str], dict[str, Any]]:
    return lambda system, user: dict(payload)


def example(eid="e1", text="the fellowship is 24 months", material=None, **kw):
    return mat.MaterialityExample(example_id=eid, text=text, material=material, **kw)


# --------------------------------------------------------------------------- #
# MaterialityExample
# --------------------------------------------------------------------------- #


class TestMaterialityExample:
    def test_empty_id_raises(self):
        with pytest.raises(mat.MaterialityError):
            mat.MaterialityExample(example_id=" ", text="x")

    def test_empty_text_raises(self):
        with pytest.raises(mat.MaterialityError):
            mat.MaterialityExample(example_id="e1", text="  ")

    def test_non_bool_label_raises(self):
        with pytest.raises(mat.MaterialityError):
            mat.MaterialityExample(example_id="e1", text="x", material="yes")

    def test_unlabeled_dict_carries_marker(self):
        d = example().to_dict()
        assert d["labeling_status"] == TO_BE_LABELED
        assert d["material"] is None

    def test_labeled_dict_has_no_marker(self):
        d = example(material=True).to_dict()
        assert "labeling_status" not in d

    def test_round_trip(self):
        e = example(material=False, origin=mat.ORIGIN_PROSE, note="n")
        assert mat.MaterialityExample.from_dict(e.to_dict()) == e


class TestNormalizeText:
    def test_collapses_whitespace_and_case(self):
        assert mat.normalize_text("  The\n Fellowship\tIS 24 months ") == (
            "the fellowship is 24 months"
        )


# --------------------------------------------------------------------------- #
# Seeding
# --------------------------------------------------------------------------- #


class TestSeedPositives:
    def _claims(self):
        return [
            SectionClaim(claim_id="C01", claim_summary="Crop selection: tomato",
                         status="confirmed", source_ref="d", entry_index=0),
            SectionClaim(claim_id="C01", claim_summary="Crop selection:  TOMATO",
                         status="confirmed", source_ref="d", entry_index=43),
            SectionClaim(claim_id="C02", claim_summary="24-month fellowship",
                         status="confirmed", source_ref="d", entry_index=1),
        ]

    def test_dedup_by_normalized_summary_and_auto_label(self):
        out = mat.seed_materiality_positives(self._claims(), section_id="excellence")
        assert [e.text for e in out] == ["Crop selection: tomato", "24-month fellowship"]
        assert all(e.material is True for e in out)
        assert all(e.origin == mat.ORIGIN_LEDGER for e in out)
        assert out[0].claim_id == "C01#0"  # entry_key, not the ambiguous bare id
        assert out[0].section_id == "excellence"
        assert [e.example_id for e in out] == ["mat-pos-001", "mat-pos-002"]

    def test_blank_summaries_skipped(self):
        claims = [SectionClaim(claim_id="C1", claim_summary="x", status="confirmed",
                               source_ref="d")]
        out = mat.seed_materiality_positives(claims)
        assert len(out) == 1


class TestSeedNegativeCandidates:
    PROSE = (
        "# Heading is skipped entirely\n\n"
        "The following sub-sections describe the methodology in detail for the reader. "
        "This paragraph then continues with more framing text of sufficient length here.\n\n"
        "Short.\n\n"
        "Another candidate sentence that is long enough to be a useful labeling span."
    )

    def test_deterministic_unlabeled_candidates(self):
        out1 = mat.seed_negative_candidates([self.PROSE], limit=2)
        out2 = mat.seed_negative_candidates([self.PROSE], limit=2)
        assert out1 == out2
        assert 0 < len(out1) <= 2
        assert all(e.material is None for e in out1)
        assert all(e.origin == mat.ORIGIN_PROSE for e in out1)
        # headings and short fragments never become candidates
        assert all("Heading" not in e.text and e.text != "Short." for e in out1)

    def test_empty_prose_yields_empty(self):
        assert mat.seed_negative_candidates([""], limit=5) == []


# --------------------------------------------------------------------------- #
# Set I/O + hash
# --------------------------------------------------------------------------- #


class TestSetIO:
    def test_template_round_trip(self, tmp_path):
        examples = [example("e1", material=True), example("e2", "another span here")]
        p = tmp_path / "set.jsonl"
        mat.write_materiality_template(examples, p)
        loaded = mat.load_materiality_set(p)
        assert loaded == tuple(examples)

    def test_require_labeled_fails_closed(self, tmp_path):
        p = tmp_path / "set.jsonl"
        mat.write_materiality_template([example("e1")], p)
        with pytest.raises(mat.MaterialityError, match="unlabeled"):
            mat.load_materiality_set(p, require_labeled=True)

    def test_duplicate_example_id_raises(self, tmp_path):
        p = tmp_path / "set.jsonl"
        mat.write_materiality_template([example("e1"), example("e1")], p)
        with pytest.raises(mat.MaterialityError, match="duplicate"):
            mat.load_materiality_set(p)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(mat.MaterialityError, match="not found"):
            mat.load_materiality_set(tmp_path / "nope.jsonl")

    def test_hash_changes_on_label_not_on_note(self):
        base = [example("e1", material=True)]
        relabeled = [example("e1", material=False)]
        noted = [example("e1", material=True, note="a note")]
        h = mat.materiality_set_hash
        assert h(base) != h(relabeled)
        assert h(base) == h(noted)


# --------------------------------------------------------------------------- #
# Prompt + classifier
# --------------------------------------------------------------------------- #


class TestPromptAndClassifier:
    def test_prompt_quotes_section_10_5_verbatim(self):
        system, user = mat.build_materiality_prompt("the host is ELTE")
        assert "Unattributed claims must be flagged, not asserted." in system
        assert system.startswith("You are an independent faithfulness judge"[:20])
        assert '"passed"' in system
        assert "the host is ELTE" in user

    def test_classify_returns_boolean_verdict(self):
        judge, backend = make_judge(always({"passed": True, "score": 0.9, "rationale": "r"}))
        v = mat.classify_materiality(judge, "the host is ELTE", property_key="a1")
        assert v.passed is True
        assert v.metric == mat.MATERIALITY_METRIC
        assert v.property_key == "a1"
        assert len(backend.calls) == 1

    def test_n2_rejected(self):
        judge, _ = make_judge(always({"passed": True, "rationale": "r"}))
        with pytest.raises(ValueError, match="n=2"):
            mat.classify_materiality(judge, "x", property_key="a1", n=2)

    def test_n3_majority(self):
        judge, backend = make_judge(always({"passed": False, "rationale": "r"}))
        v = mat.classify_materiality(judge, "x", property_key="a1", n=3)
        assert v.passed is False
        assert v.n == 3
        assert len(backend.calls) == 3

    def test_malformed_response_raises_not_repaired(self):
        judge = Judge(
            JudgeConfig(model="acme-judge-1", version="v1"),
            backend=lambda messages: {"content": "not json at all", "tool_calls": None},
        )
        with pytest.raises(JudgeResponseError):
            mat.classify_materiality(judge, "x", property_key="a1")


# --------------------------------------------------------------------------- #
# Calibration — the precision guard is the load-bearing case
# --------------------------------------------------------------------------- #


class TestCalibration:
    def test_positives_only_recall_computed_precision_none(self):
        # Classifier flags everything material — on a positives-only set the
        # raw matrix precision would be a spurious 1.0; it must come back None.
        judge, _ = make_judge(always({"passed": True, "rationale": "r"}))
        examples = [example(f"e{i}", f"claim number {i} of the ledger", material=True)
                    for i in range(5)]
        cal = mat.calibrate_materiality(examples, judge, clock=lambda: "T")
        assert cal.recall == 1.0
        assert cal.precision is None
        assert cal.labeled_negatives == 0
        assert cal.has_negatives is False
        assert cal.n_examples == 5
        assert cal.timestamp == "T"
        assert cal.to_dict()["precision"] is None

    def test_precision_computed_with_labeled_negatives(self):
        judge, _ = make_judge(always({"passed": True, "rationale": "r"}))
        examples = [
            example("p1", "a material claim about the host", material=True),
            example("n1", "the following sections describe the approach", material=False),
        ]
        cal = mat.calibrate_materiality(examples, judge)
        # judge flags both material: tp=1 fp=1 -> precision 0.5, recall 1.0
        assert cal.precision == 0.5
        assert cal.recall == 1.0
        assert cal.labeled_negatives == 1

    def test_unlabeled_example_fails_closed(self):
        judge, _ = make_judge(always({"passed": True, "rationale": "r"}))
        with pytest.raises(mat.MaterialityError, match="unlabeled"):
            mat.calibrate_materiality([example("e1")], judge)

    def test_empty_set_raises(self):
        judge, _ = make_judge(always({"passed": True, "rationale": "r"}))
        with pytest.raises(mat.MaterialityError, match="empty"):
            mat.calibrate_materiality([], judge)

    def test_boolean_less_verdict_raises(self):
        judge, _ = make_judge(always({"score": 0.8, "rationale": "r"}))
        with pytest.raises(mat.MaterialityError, match="no boolean"):
            mat.calibrate_materiality([example("e1", material=True)], judge)

    def test_applies_to_repin(self):
        judge, _ = make_judge(always({"passed": True, "rationale": "r"}))
        cal = mat.calibrate_materiality([example("e1", material=True)], judge)
        assert cal.applies_to(JudgeConfig(model="acme-judge-1", version="v1"))
        assert not cal.applies_to(JudgeConfig(model="acme-judge-1", version="v2"))
        assert cal.set_hash.startswith("sha256:")
