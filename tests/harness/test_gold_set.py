"""
Tests for harness/gold_set.py — human-labeled faithfulness gold set + seeding.

Covers:
  - GoldPair validation + is_labeled + dict round-trip + TO_BE_LABELED marker
  - GoldSet labeled/unlabeled/require_fully_labeled (fail-closed)
  - load_gold_set: JSONL + JSON list, require_labeled gate, dup pair_id
  - gold_set_hash stability + label-sensitivity
  - seed_pairs_from_claim_statuses: deterministic, unlabeled, stratified, capped
"""

from __future__ import annotations

import json

import pytest

from harness.gold_set import (
    TO_BE_LABELED,
    GoldPair,
    GoldSet,
    GoldSetError,
    gold_set_hash,
    load_gold_set,
    seed_pairs_from_claim_statuses,
    write_gold_set_template,
)


def _pair(pid="g1", supported=True, **kw) -> GoldPair:
    base = dict(pair_id=pid, claim="tomato is the crop", source_ref="docs/x.json", supported=supported)
    base.update(kw)
    return GoldPair(**base)


# --------------------------------------------------------------------------- #
# GoldPair
# --------------------------------------------------------------------------- #


class TestGoldPair:
    def test_labeled_flag(self):
        assert _pair(supported=True).is_labeled
        assert _pair(supported=False).is_labeled
        assert not _pair(supported=None).is_labeled

    @pytest.mark.parametrize("bad", ["", "  "])
    def test_empty_fields_rejected(self, bad):
        with pytest.raises(GoldSetError):
            GoldPair(pair_id=bad, claim="c", source_ref="s")
        with pytest.raises(GoldSetError):
            GoldPair(pair_id="g", claim=bad, source_ref="s")
        with pytest.raises(GoldSetError):
            GoldPair(pair_id="g", claim="c", source_ref=bad)

    def test_supported_must_be_bool_or_none(self):
        with pytest.raises(GoldSetError, match="supported"):
            GoldPair(pair_id="g", claim="c", source_ref="s", supported="yes")

    def test_unlabeled_dict_has_marker(self):
        d = _pair(supported=None).to_dict()
        assert d["labeling_status"] == TO_BE_LABELED
        assert d["supported"] is None

    def test_labeled_dict_has_no_marker(self):
        d = _pair(supported=True).to_dict()
        assert "labeling_status" not in d

    def test_from_dict_roundtrip(self):
        p = _pair(supported=False, claim_id="C7", source_excerpt="…", engine_status="confirmed", note="n")
        p2 = GoldPair.from_dict(p.to_dict())
        assert p2 == p


# --------------------------------------------------------------------------- #
# GoldSet
# --------------------------------------------------------------------------- #


class TestGoldSet:
    def test_labeled_unlabeled_split(self):
        gs = GoldSet(pairs=(_pair("a", True), _pair("b", None), _pair("c", False)))
        assert len(gs) == 3
        assert {p.pair_id for p in gs.labeled()} == {"a", "c"}
        assert {p.pair_id for p in gs.unlabeled()} == {"b"}

    def test_require_fully_labeled_passes(self):
        GoldSet(pairs=(_pair("a", True), _pair("b", False))).require_fully_labeled()

    def test_require_fully_labeled_fails(self):
        gs = GoldSet(pairs=(_pair("a", True), _pair("b", None)), gold_set_id="gs")
        with pytest.raises(GoldSetError, match="unlabeled"):
            gs.require_fully_labeled()


# --------------------------------------------------------------------------- #
# load_gold_set
# --------------------------------------------------------------------------- #


class TestLoadGoldSet:
    def test_load_jsonl_labeled(self, tmp_path):
        p = tmp_path / "g.jsonl"
        p.write_text(
            json.dumps(_pair("a", True).to_dict()) + "\n" + json.dumps(_pair("b", False).to_dict()) + "\n",
            encoding="utf-8",
        )
        gs = load_gold_set(p)
        assert len(gs) == 2
        assert gs.gold_set_id == "g"

    def test_load_json_list(self, tmp_path):
        p = tmp_path / "g.json"
        p.write_text(json.dumps([_pair("a", True).to_dict()]), encoding="utf-8")
        assert len(load_gold_set(p)) == 1

    def test_require_labeled_rejects_template(self, tmp_path):
        p = tmp_path / "t.jsonl"
        p.write_text(json.dumps(_pair("a", None).to_dict()) + "\n", encoding="utf-8")
        with pytest.raises(GoldSetError, match="unlabeled"):
            load_gold_set(p)  # require_labeled=True by default

    def test_allow_unlabeled_loads_template(self, tmp_path):
        p = tmp_path / "t.jsonl"
        p.write_text(json.dumps(_pair("a", None).to_dict()) + "\n", encoding="utf-8")
        gs = load_gold_set(p, require_labeled=False)
        assert len(gs.unlabeled()) == 1

    def test_duplicate_pair_id_rejected(self, tmp_path):
        p = tmp_path / "g.jsonl"
        p.write_text(
            json.dumps(_pair("a", True).to_dict()) + "\n" + json.dumps(_pair("a", False).to_dict()) + "\n",
            encoding="utf-8",
        )
        with pytest.raises(GoldSetError, match="duplicate"):
            load_gold_set(p)

    def test_missing_file(self, tmp_path):
        with pytest.raises(GoldSetError, match="not found"):
            load_gold_set(tmp_path / "nope.jsonl")


# --------------------------------------------------------------------------- #
# gold_set_hash
# --------------------------------------------------------------------------- #


class TestGoldSetHash:
    def test_stable(self):
        gs = GoldSet(pairs=(_pair("a", True), _pair("b", False)))
        assert gold_set_hash(gs) == gold_set_hash(gs)

    def test_label_change_changes_hash(self):
        a = GoldSet(pairs=(_pair("a", True),))
        b = GoldSet(pairs=(_pair("a", False),))
        assert gold_set_hash(a) != gold_set_hash(b)

    def test_note_change_does_not_change_hash(self):
        a = GoldSet(pairs=(_pair("a", True, note="x"),))
        b = GoldSet(pairs=(_pair("a", True, note="y"),))
        assert gold_set_hash(a) == gold_set_hash(b)


# --------------------------------------------------------------------------- #
# seed_pairs_from_claim_statuses
# --------------------------------------------------------------------------- #


def _claim_statuses(n_conf=10, n_inf=4):
    cs = []
    for i in range(n_conf):
        cs.append({"claim_id": f"C{i}", "claim_summary": f"confirmed claim {i}", "status": "confirmed", "source_ref": "docs/a.json"})
    for i in range(n_inf):
        cs.append({"claim_id": f"I{i}", "claim_summary": f"inferred claim {i}", "status": "inferred", "source_ref": "docs/b.json"})
    return cs


class TestSeed:
    def test_all_unlabeled(self):
        pairs = seed_pairs_from_claim_statuses(_claim_statuses(), limit=6)
        assert all(not p.is_labeled for p in pairs)  # never fabricated
        assert all(p.supported is None for p in pairs)

    def test_deterministic(self):
        cs = _claim_statuses()
        a = seed_pairs_from_claim_statuses(cs, limit=6)
        b = seed_pairs_from_claim_statuses(cs, limit=6)
        assert [p.claim for p in a] == [p.claim for p in b]

    def test_carries_engine_status_and_ids(self):
        pairs = seed_pairs_from_claim_statuses(_claim_statuses(), limit=6)
        assert all(p.engine_status in ("confirmed", "inferred") for p in pairs)
        assert all(p.claim_id for p in pairs)

    def test_stratified_covers_both_statuses(self):
        pairs = seed_pairs_from_claim_statuses(_claim_statuses(20, 8), limit=10)
        statuses = {p.engine_status for p in pairs}
        assert statuses == {"confirmed", "inferred"}

    def test_dedups_identical_claim_and_source(self):
        # Same (claim_summary, source_ref) twice -> one candidate.
        cs = [
            {"claim_id": "C1", "claim_summary": "same claim", "status": "confirmed", "source_ref": "docs/a.json"},
            {"claim_id": "C1", "claim_summary": "same claim", "status": "confirmed", "source_ref": "docs/a.json"},
            {"claim_id": "C2", "claim_summary": "same claim", "status": "confirmed", "source_ref": "docs/b.json"},
        ]
        pairs = seed_pairs_from_claim_statuses(cs, limit=30)
        # 2 distinct (claim, source) questions survive; same claim + different source is kept.
        assert len(pairs) == 2

    def test_no_duplicate_questions_in_sample(self):
        # Real sections repeat claim_ids; the seeded sample must carry no dup (claim, source).
        cs = _claim_statuses(30, 10) + _claim_statuses(30, 10)  # everything duplicated
        pairs = seed_pairs_from_claim_statuses(cs, limit=30)
        keys = {(p.claim, p.source_ref) for p in pairs}
        assert len(keys) == len(pairs)

    def test_limit_capped_to_available(self):
        pairs = seed_pairs_from_claim_statuses(_claim_statuses(2, 1), limit=30)
        assert len(pairs) == 3

    def test_count_matches_limit(self):
        pairs = seed_pairs_from_claim_statuses(_claim_statuses(50, 20), limit=30)
        assert len(pairs) == 30

    def test_skips_entries_missing_fields(self):
        cs = [{"claim_id": "C1", "claim_summary": "", "status": "confirmed", "source_ref": "d"}]
        assert seed_pairs_from_claim_statuses(cs, limit=5) == []

    def test_write_template(self, tmp_path):
        pairs = seed_pairs_from_claim_statuses(_claim_statuses(), limit=5)
        out = tmp_path / "tmpl.jsonl"
        write_gold_set_template(pairs, out)
        gs = load_gold_set(out, require_labeled=False)
        assert len(gs) == 5
        assert len(gs.unlabeled()) == 5


class TestSeededExcellenceTemplate:
    """The committed real template drawn from excellence_section.json claim_statuses."""

    def _path(self):
        from runner.paths import find_repo_root

        path = find_repo_root() / "harness" / "gold_sets" / "faithfulness_gold_excellence_TEMPLATE.jsonl"
        if not path.is_file():
            pytest.skip(
                "EXCLUDED (not a pass): no seeded gold-set template in this "
                "checkout. Disposition and the work that would lift it: "
                "harness/DATASET_DISPOSITIONS.md"
            )
        return path

    def test_exists_and_loads_as_template(self):
        gs = load_gold_set(self._path(), require_labeled=False)
        assert len(gs) == 30

    def test_is_fully_unlabeled(self):
        # Ships unlabeled — labels are a human deliverable, never fabricated.
        gs = load_gold_set(self._path(), require_labeled=False)
        assert len(gs.unlabeled()) == len(gs)

    def test_no_duplicate_questions(self):
        # Deduped by (claim, source_ref) — no wasted double-labeling.
        gs = load_gold_set(self._path(), require_labeled=False)
        keys = {(p.claim, p.source_ref) for p in gs.pairs}
        assert len(keys) == len(gs)

    def test_calibration_load_is_fail_closed(self):
        # Loading it in calibration mode must refuse (no human labels yet).
        with pytest.raises(GoldSetError, match="unlabeled"):
            load_gold_set(self._path())
