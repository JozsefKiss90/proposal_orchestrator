"""
One content-hash module (overhaul ticket 04).

Two parts, in the order the ticket wrote them:

1. Characterisation. Every hash the harness stores keeps exactly its bytes.
   The literals below were computed by the code at base commit ``92ce1e16``,
   before any hash moved. The committed MSCA-DN blind baseline and its bindings
   must still load and re-derive.
2. The content-hash module: the short form accepts either stored format, the
   numbered-path helper names a bare-hex digest as it names the prefixed one,
   and no harness module outside the hash module calls ``hashlib`` or builds
   canonical JSON for hashing.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

import harness.blind_assessment as ba
import harness.regression as reg
from harness.blind_baseline import load_frozen_baseline
from harness.gold_set import GoldPair, GoldSet, gold_set_hash
from harness.materiality import MaterialityExample, materiality_set_hash
from harness.provenance import prompt_hash
from harness.rubrics import load_profile_bundle, rubric_fingerprint
from runner.paths import find_repo_root
from tests.harness.test_evidence_preflight import _candidate, _realise, _synthetic_profile

REPO = find_repo_root()

# --------------------------------------------------------------------------- #
# 1. Characterisation: literals from the base commit
# --------------------------------------------------------------------------- #

CANDIDATE_HASH = "sha256:d06fae060a717f55e597adc202ae7d036e44f579087f2015aa2275945a99948c"
PROFILE_VERSION = "sha256:dbc3878837ee87469dacea19b92fe64594b438d97a491b68f7efaa55eb483433"
RUBRIC_FINGERPRINT = "sha256:dea0ba753af96e74f69f2df4bc7ea3627cef3c4c93fd07082b4b4e7600f0bc21"
RUBRIC_SET_FINGERPRINT = "sha256:0a54f3c78a37fdcf68f5fa2d994428fa193149da4bae230a135f98623fd32227"
PACK_SET_HASH = "sha256:23a291a796a77d9a76d2070308b31aa42d88a714e5ebfdcf1f49089b5534d3fd"
#: The regression fingerprint stores its canonical hash without a prefix.
REGRESSION_ARTIFACT_SHA256 = "6a5c2ca607736ccb884d58d89428d13326ad6d8087badd342c5ba99d3ce72adf"
REGRESSION_CONTENT_SHA256 = "b1406e6b6fd699da08b76ca5092e20008a655ea5916b7149da732853d79fec13"
GOLD_SET_HASH = "sha256:069e22bc05e5aa33ffa6e656e1df0bcf759b8e8cdfcbfd1867606688bee9e256"
MATERIALITY_SET_HASH = "sha256:c1c3bb9f2f6f45dc60d08ddc7356a4397ebe71c87b662c02ccbfb53c7c6a64b5"
PROMPT_HASH = "sha256:064583047d633909e0bc86ed7f25f082dbaa06bf434c48742b7c59603c69e95b"

#: An E4 section fingerprint as the base commit froze it from :func:`_e4_section`.
E4_FINGERPRINT = {
    "record_type": "regression_section_fingerprint",
    "metric": "regression_golden_set",
    "section_id": "s",
    "artifact_path": "section.json",
    "artifact_sha256": REGRESSION_ARTIFACT_SHA256,
    "frozen_at": "2026-11-11T00:00:00Z",
    "status_counts": {"confirmed": 1},
    "claims": [
        {
            "claim_id": "C01",
            "entry_index": 0,
            "entry_key": "C01#0",
            "claim_summary": "Ő claim",
            "status": "confirmed",
            "source_ref": "docs/x.json",
        }
    ],
    "sub_sections": [
        {
            "sub_section_id": "1",
            "title": "Ü",
            "content_sha256": REGRESSION_CONTENT_SHA256,
            "char_count": 20,
        }
    ],
}

DN_BASELINE_DIR = REPO / "docs/tier4_orchestration_state/msca_dn/baselines/resolved_fixes_2026-10-06"
DN_PROFILE = REPO / "harness/profiles/msca_dn_2026_default.json"


@pytest.fixture
def world(tmp_path: Path):
    profile = _synthetic_profile(tmp_path)
    bundle = load_profile_bundle(profile, repo_root=tmp_path)
    return tmp_path, bundle


def _e4_section(path: Path) -> Path:
    """A section with non-ASCII text, so the canonical rule's ``ensure_ascii=False`` shows."""
    data = {
        "sub_sections": [
            {"sub_section_id": "1", "title": "Ü", "content": "Résumé — naïve café."}
        ],
        "validation_status": {
            "claim_statuses": [
                {
                    "claim_id": "C01",
                    "claim_summary": "Ő claim",
                    "status": "confirmed",
                    "source_ref": "docs/x.json",
                }
            ]
        },
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


class TestEveryStoredHashKeepsItsBytes:
    def test_the_candidate_hash(self, world):
        root, bundle = world
        candidate = ba.load_candidate(_candidate(root), bundle.profile)
        assert ba.candidate_hash(candidate) == CANDIDATE_HASH

    def test_the_profile_version(self, world):
        _root, bundle = world
        assert bundle.version == PROFILE_VERSION

    def test_the_rubric_fingerprint(self, world):
        _root, bundle = world
        assert rubric_fingerprint(bundle.rubric_set.rubrics[0]) == RUBRIC_FINGERPRINT

    def test_the_rubric_set_fingerprint(self, world):
        _root, bundle = world
        assert bundle.rubric_set.fingerprint == RUBRIC_SET_FINGERPRINT

    def test_the_evidence_preflight_pack_set_hash(self, world):
        root, _bundle = world
        assert _realise(world, _candidate(root)).hash == PACK_SET_HASH

    def test_the_regression_section_fingerprint(self, tmp_path):
        fp = reg.freeze_section_fingerprint(
            _e4_section(tmp_path / "section.json"), section_id="s", frozen_at="2026-11-11T00:00:00Z"
        )
        assert fp.artifact_sha256 == REGRESSION_ARTIFACT_SHA256
        assert fp.sub_sections[0].content_sha256 == REGRESSION_CONTENT_SHA256

    def test_the_gold_set_hash(self):
        gold = GoldSet(
            pairs=(
                GoldPair(pair_id="g1", claim="Ő claim", source_ref="docs/x.json",
                         supported=True, source_excerpt="Résumé"),
                GoldPair(pair_id="g2", claim="plain", source_ref="docs/y.json", supported=False),
            )
        )
        assert gold_set_hash(gold) == GOLD_SET_HASH

    def test_the_materiality_set_hash(self):
        examples = [
            MaterialityExample(example_id="m1", text="Ő material", material=True),
            MaterialityExample(example_id="m2", text="framing", material=False),
        ]
        assert materiality_set_hash(examples) == MATERIALITY_SET_HASH

    def test_the_prompt_hash(self):
        assert prompt_hash("système", "user ✓") == PROMPT_HASH


class TestFrozenRecordsStillLoadAndVerify:
    def test_the_committed_blind_baseline_loads_and_its_report_hash_verifies(self):
        frozen = load_frozen_baseline(DN_BASELINE_DIR)
        assert frozen.record["report_sha256"] == (
            "f60ae6e0a2a1ddcdb4a82b1e690941048a286ef72cc016ec8b325c728096bb01"
        )

    def test_the_committed_baselines_bindings_re_derive(self):
        frozen = load_frozen_baseline(DN_BASELINE_DIR)
        bindings = frozen.record["bindings"]
        bundle = load_profile_bundle(DN_PROFILE, repo_root=REPO)
        assert bundle.version == bindings["profile_version"]
        assert bundle.rubric_set.fingerprint == bindings["rubric_set_fingerprint"]
        candidate_dir = REPO / "harness/blind_reports/candidates" / Path(bindings["candidate_path"]).name
        candidate = ba.load_candidate(candidate_dir, bundle.profile)
        assert ba.candidate_hash(candidate) == bindings["candidate_hash"]

    def test_an_e4_fingerprint_frozen_at_the_base_still_loads_and_matches(self, tmp_path):
        golden_path = tmp_path / "s.golden.json"
        golden_path.write_text(json.dumps(E4_FINGERPRINT, ensure_ascii=False), encoding="utf-8")
        golden = reg.load_fingerprint(golden_path)
        current = reg.freeze_section_fingerprint(
            _e4_section(tmp_path / "section.json"), section_id="s", frozen_at="2026-11-11T00:00:00Z"
        )
        result = reg.compare_section(golden, current)
        assert result.artifact_changed is False
        assert result.findings == ()


# --------------------------------------------------------------------------- #
# 2. The content-hash module
# --------------------------------------------------------------------------- #

HEX = "f60ae6e0a2a1ddcdb4a82b1e690941048a286ef72cc016ec8b325c728096bb01"


class TestNumberingAcceptsBothFormats:
    def test_a_bare_hex_digest_is_named_as_its_prefixed_form_is(self, tmp_path):
        bare = ba.next_report_path(tmp_path, HEX, prefix="comparison")
        prefixed = ba.next_report_path(tmp_path, "sha256:" + HEX, prefix="comparison")
        assert bare == prefixed == tmp_path / "comparison_f60ae6e0a2a1_0001.json"

    def test_the_sequence_counts_files_named_from_either_format(self, tmp_path):
        ba.next_report_path(tmp_path, HEX, prefix="comparison").write_text("{}", encoding="utf-8")
        assert ba.next_report_path(tmp_path, "sha256:" + HEX, prefix="comparison").name == (
            "comparison_f60ae6e0a2a1_0002.json"
        )


class TestTheShortForm:
    def test_a_prefixed_and_a_bare_digest_of_the_same_bytes_shorten_alike(self):
        from harness.content_hash import short_hash

        assert short_hash("sha256:" + HEX) == short_hash(HEX) == "f60ae6e0a2a1"


class TestOneModuleComputesEveryHash:
    """No harness module outside the hash module calls ``hashlib`` or builds canonical
    JSON for hashing; the hash module is the only place either appears."""

    HASH_MODULE = REPO / "harness" / "content_hash.py"
    #: The canonical rule's compact separators: the marker of canonical JSON built for a hash.
    CANONICAL_JSON = re.compile(r"""separators\s*=\s*\(\s*["'],["']\s*,\s*["']:["']\s*\)""")

    def _harness_modules(self):
        return [p for p in sorted((REPO / "harness").rglob("*.py")) if p != self.HASH_MODULE]

    def test_no_other_harness_module_imports_or_calls_hashlib(self):
        offenders = [
            p.relative_to(REPO).as_posix()
            for p in self._harness_modules()
            if re.search(r"\bhashlib\b", p.read_text(encoding="utf-8"))
        ]
        assert offenders == []

    def test_no_other_harness_module_builds_canonical_json(self):
        offenders = [
            p.relative_to(REPO).as_posix()
            for p in self._harness_modules()
            if self.CANONICAL_JSON.search(p.read_text(encoding="utf-8"))
        ]
        assert offenders == []

    def test_the_boundary_check_sees_the_hash_module_itself(self):
        text = self.HASH_MODULE.read_text(encoding="utf-8")
        assert re.search(r"\bhashlib\b", text) and self.CANONICAL_JSON.search(text)


class TestTheTwoFormats:
    def test_a_content_hash_is_prefixed_and_formatting_invariant(self):
        from harness.content_hash import content_hash

        a = content_hash({"b": "\u00e9", "a": [1, 2]})
        assert a == content_hash(json.loads('{ "a" : [1,2], "b":"\u00e9" }'))
        assert a.startswith("sha256:") and len(a) == len("sha256:") + 64

    def test_a_file_hash_is_bare_hex_of_bytes_or_of_a_path(self, tmp_path):
        from harness.content_hash import file_hash

        path = tmp_path / "f.bin"
        path.write_bytes(b"abc")
        known = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
        assert file_hash(b"abc") == file_hash(path) == file_hash(str(path)) == known

    def test_the_short_form_keeps_a_label_only_when_asked(self):
        from harness.content_hash import short_hash

        assert short_hash("sha256:" + HEX, keep_prefix=True) == "sha256:f60ae6e0a2a1"
        assert short_hash(HEX, keep_prefix=True) == "f60ae6e0a2a1"
        assert short_hash("") == short_hash("", keep_prefix=True) == ""

    def test_the_response_checkpoint_numbers_through_the_shared_helper(self, tmp_path):
        from harness.response_cache import next_checkpoint_path

        first = next_checkpoint_path(tmp_path, HEX)
        assert first == tmp_path / "checkpoint_f60ae6e0a2a1_0001.jsonl"
        first.write_text("", encoding="utf-8")
        assert next_checkpoint_path(tmp_path, "sha256:" + HEX).name == "checkpoint_f60ae6e0a2a1_0002.jsonl"