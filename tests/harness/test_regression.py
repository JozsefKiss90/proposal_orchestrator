"""
Tests for harness/regression.py — the E4 regression golden-set.

Fully offline: fingerprints are frozen from ``tmp_path`` section fixtures, the
judge lane is driven by an injected fake backend (no network), and the CLI is
exercised through ``main(argv)`` against temp directories.  Nothing here touches
a live model or a real DAG run.

Coverage:
  - LedgerEntry identity (whitespace-normalized meaning, never bare claim_id)
  - freeze_section_fingerprint: ledger + prose capture, canonical artifact hash
    (formatting-invariant), fail-closed on malformed sections
  - fingerprint write/load roundtrip; golden-set dir loader (fail-closed empty)
  - compare_section: every finding kind — claim removed / status changed /
    source_ref changed / added; subsection removed / added / prose changed;
    prose-changed-ledger-unchanged advisory; confirmed-share drop; dedup
  - RegressionReport: advisory=True / blocking=False enforced structurally;
    golden-set comparison (section missing / added)
  - judge lane: freeze_section_grounding / compare_section_grounding reuse of
    E2's baseline machinery (bar regression detected, judge pin carried)
  - CLI: freeze then clean check (exit 0); drifted check (exit 1, advisory
    report printed); fail-closed on an empty golden dir (exit 2)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import pytest

from harness.judge import Judge, JudgeConfig
from runner.working_assumptions import WorkingAssumptions
import harness.regression as reg


# --------------------------------------------------------------------------- #
# Fixture helpers
# --------------------------------------------------------------------------- #


def claim_entry(
    cid: str = "C01",
    summary: str = "the claim",
    status: str = "confirmed",
    source_ref: str = "docs/x.json",
) -> dict[str, Any]:
    return {
        "claim_id": cid,
        "claim_summary": summary,
        "status": status,
        "source_ref": source_ref,
    }


def sub_section(
    sid: str = "1", title: str = "Title", content: str = "Some prose.\n\nMore prose."
) -> dict[str, Any]:
    return {"sub_section_id": sid, "title": title, "content": content}


def write_section(
    path: Path,
    *,
    claims: list[dict[str, Any]] | None = None,
    subs: list[dict[str, Any]] | None = None,
    indent: int | None = 2,
    sort_keys: bool = False,
) -> Path:
    data = {
        "schema_id": "phase8_section",
        "run_id": "run-x",
        "criterion": "excellence",
        "sub_sections": subs if subs is not None else [sub_section()],
        "validation_status": {
            "claim_statuses": claims if claims is not None else [claim_entry()]
        },
    }
    path.write_text(
        json.dumps(data, indent=indent, sort_keys=sort_keys), encoding="utf-8"
    )
    return path


def freeze(path: Path, **kw: Any) -> "reg.SectionFingerprint":
    kw.setdefault("frozen_at", "2026-07-21T00:00:00Z")
    return reg.freeze_section_fingerprint(path, **kw)


class RuleBackend:
    """A fake OpenAI-compatible backend: (system, user) → JSON verdict dict."""

    def __init__(self, rule: Callable[[str, str], dict[str, Any]]) -> None:
        self._rule = rule
        self.calls: list[tuple[str, str]] = []

    def __call__(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        system = messages[0]["content"]
        user = messages[1]["content"]
        self.calls.append((system, user))
        return {"content": json.dumps(self._rule(system, user)), "tool_calls": None}


def make_judge(rule: Callable[[str, str], dict[str, Any]]) -> Judge:
    return Judge(JudgeConfig(model="acme-judge-1", version="v1"), backend=RuleBackend(rule))


EMPTY_WA = WorkingAssumptions(present=True)


# --------------------------------------------------------------------------- #
# LedgerEntry
# --------------------------------------------------------------------------- #


class TestLedgerEntry:
    def test_identity_is_meaning_not_id(self):
        a = reg.LedgerEntry(
            claim_id="C01", claim_summary="x  y", status="confirmed",
            source_ref="docs/a.json", entry_index=0,
        )
        b = reg.LedgerEntry(
            claim_id="ZZZ", claim_summary="x y", status="confirmed",
            source_ref="docs/a.json", entry_index=9,
        )
        assert a.identity == b.identity

    def test_identity_distinguishes_status_and_source(self):
        base = dict(claim_id="C01", claim_summary="x", source_ref="docs/a.json", entry_index=0)
        confirmed = reg.LedgerEntry(status="confirmed", **base)
        inferred = reg.LedgerEntry(status="inferred", **base)
        assert confirmed.identity != inferred.identity

    def test_entry_key_disambiguates(self):
        e = reg.LedgerEntry(
            claim_id="C01", claim_summary="x", status="confirmed",
            source_ref="d", entry_index=171,
        )
        assert e.entry_key == "C01#171"


# --------------------------------------------------------------------------- #
# freeze_section_fingerprint
# --------------------------------------------------------------------------- #


class TestFreezeFingerprint:
    def test_captures_ledger_and_prose(self, tmp_path):
        p = write_section(
            tmp_path / "excellence_section.json",
            claims=[
                claim_entry("C01", "a", "confirmed", "docs/a.json"),
                claim_entry("C02", "b", "inferred", "docs/b.json"),
            ],
            subs=[sub_section("1", "One", "Alpha."), sub_section("1.1", "Sub", "Beta.")],
        )
        fp = freeze(p)
        assert fp.section_id == "excellence_section"
        assert [e.entry_key for e in fp.claims] == ["C01#0", "C02#1"]
        assert [s.sub_section_id for s in fp.sub_sections] == ["1", "1.1"]
        assert fp.sub_sections[0].char_count == len("Alpha.")
        assert fp.status_counts == {"confirmed": 1, "inferred": 1}
        assert fp.confirmed_share == pytest.approx(0.5)
        assert fp.frozen_at == "2026-07-21T00:00:00Z"

    def test_artifact_hash_is_formatting_invariant(self, tmp_path):
        a = write_section(tmp_path / "a.json", indent=2, sort_keys=False)
        b = write_section(tmp_path / "b.json", indent=None, sort_keys=True)
        assert freeze(a).artifact_sha256 == freeze(b).artifact_sha256

    def test_artifact_hash_changes_with_content(self, tmp_path):
        a = write_section(tmp_path / "a.json")
        b = write_section(
            tmp_path / "b.json", subs=[sub_section(content="Different prose.")]
        )
        assert freeze(a).artifact_sha256 != freeze(b).artifact_sha256

    def test_fail_closed_on_missing_file(self, tmp_path):
        with pytest.raises(reg.RegressionError):
            freeze(tmp_path / "nope.json")

    def test_fail_closed_on_missing_ledger(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text(json.dumps({"sub_sections": []}), encoding="utf-8")
        with pytest.raises(Exception):
            freeze(p)

    def test_confirmed_share_none_without_claims(self, tmp_path):
        # An empty (but present) ledger freezes with confirmed_share None.
        p = write_section(tmp_path / "s.json", claims=[])
        fp = freeze(p)
        assert fp.claims == ()
        assert fp.confirmed_share is None


# --------------------------------------------------------------------------- #
# Roundtrip + golden-set loading
# --------------------------------------------------------------------------- #


class TestRoundtrip:
    def test_write_load_roundtrip(self, tmp_path):
        p = write_section(tmp_path / "impact_section.json")
        fp = freeze(p)
        out = tmp_path / "impact_section.golden.json"
        reg.write_fingerprint(fp, out)
        loaded = reg.load_fingerprint(out)
        assert loaded == fp

    def test_load_fingerprint_fail_closed(self, tmp_path):
        with pytest.raises(reg.RegressionError):
            reg.load_fingerprint(tmp_path / "missing.golden.json")

    def test_freeze_golden_set_writes_per_section_files(self, tmp_path):
        s1 = write_section(tmp_path / "excellence_section.json")
        s2 = write_section(tmp_path / "impact_section.json")
        out = tmp_path / "golden"
        frozen = reg.freeze_golden_set([s1, s2], out, frozen_at="t0")
        assert {f.section_id for f in frozen} == {"excellence_section", "impact_section"}
        golden = reg.load_golden_set(out)
        assert set(golden) == {"excellence_section", "impact_section"}
        assert golden["impact_section"].frozen_at == "t0"

    def test_load_golden_set_fail_closed_when_empty(self, tmp_path):
        empty = tmp_path / "golden"
        empty.mkdir()
        with pytest.raises(reg.RegressionError):
            reg.load_golden_set(empty)


# --------------------------------------------------------------------------- #
# compare_section — the deterministic regression lane
# --------------------------------------------------------------------------- #


def compare_two(tmp_path, base_kw: dict[str, Any], cur_kw: dict[str, Any]):
    base = freeze(write_section(tmp_path / "base" / "s_section.json", **base_kw))
    cur = freeze(write_section(tmp_path / "cur" / "s_section.json", **cur_kw))
    return reg.compare_section(base, cur)


@pytest.fixture()
def two_dirs(tmp_path):
    (tmp_path / "base").mkdir()
    (tmp_path / "cur").mkdir()
    return tmp_path


class TestCompareSection:
    def test_identical_sections_are_clean(self, two_dirs):
        result = compare_two(two_dirs, {}, {})
        assert result.findings == ()
        assert result.artifact_changed is False
        assert result.regressed is False

    def test_claim_removed_is_breaking(self, two_dirs):
        result = compare_two(
            two_dirs,
            {"claims": [claim_entry("C01", "a"), claim_entry("C02", "b")]},
            {"claims": [claim_entry("C01", "a")]},
        )
        kinds = [f.kind for f in result.findings]
        assert reg.REGRESSION_CLAIM_REMOVED in kinds
        assert result.regressed is True
        removed = [f for f in result.findings if f.kind == reg.REGRESSION_CLAIM_REMOVED]
        assert removed[0].baseline is not None
        assert "b" in json.dumps(removed[0].baseline)

    def test_status_change_is_breaking(self, two_dirs):
        result = compare_two(
            two_dirs,
            {"claims": [claim_entry("C01", "a", "confirmed")]},
            {"claims": [claim_entry("C01", "a", "inferred")]},
        )
        kinds = [f.kind for f in result.findings]
        assert kinds.count(reg.REGRESSION_STATUS_CHANGED) == 1
        assert reg.REGRESSION_CLAIM_REMOVED not in kinds
        assert result.regressed is True

    def test_source_ref_change_is_breaking(self, two_dirs):
        result = compare_two(
            two_dirs,
            {"claims": [claim_entry("C01", "a", source_ref="docs/a.json")]},
            {"claims": [claim_entry("C01", "a", source_ref="docs/b.json")]},
        )
        kinds = [f.kind for f in result.findings]
        assert kinds.count(reg.REGRESSION_SOURCE_REF_CHANGED) == 1
        assert result.regressed is True

    def test_claim_added_is_advisory_only(self, two_dirs):
        result = compare_two(
            two_dirs,
            {"claims": [claim_entry("C01", "a")]},
            {"claims": [claim_entry("C01", "a"), claim_entry("C02", "new")]},
        )
        kinds = [f.kind for f in result.findings]
        assert reg.REGRESSION_CLAIM_ADDED in kinds
        assert result.regressed is False

    def test_relabelled_claim_id_is_not_a_regression(self, two_dirs):
        # Same meaning under a different id/index: matched by identity, clean.
        result = compare_two(
            two_dirs,
            {"claims": [claim_entry("C01", "a")]},
            {"claims": [claim_entry("C99", "a")]},
        )
        ledger_kinds = [
            f.kind
            for f in result.findings
            if f.kind
            in (
                reg.REGRESSION_CLAIM_REMOVED,
                reg.REGRESSION_CLAIM_ADDED,
                reg.REGRESSION_STATUS_CHANGED,
                reg.REGRESSION_SOURCE_REF_CHANGED,
            )
        ]
        assert ledger_kinds == []

    def test_duplicate_identities_deduped(self, two_dirs):
        result = compare_two(
            two_dirs,
            {"claims": [claim_entry("C01", "a"), claim_entry("C01", "a")]},
            {"claims": [claim_entry("C01", "a")]},
        )
        assert result.regressed is False

    def test_prose_change_with_stable_ledger_is_advisory(self, two_dirs):
        result = compare_two(
            two_dirs,
            {"subs": [sub_section("1", "T", "Old prose.")]},
            {"subs": [sub_section("1", "T", "New, much longer prose.")]},
        )
        kinds = [f.kind for f in result.findings]
        assert reg.REGRESSION_PROSE_CHANGED in kinds
        assert reg.REGRESSION_PROSE_CHANGED_LEDGER_UNCHANGED in kinds
        assert result.artifact_changed is True
        assert result.regressed is False

    def test_prose_change_detail_carries_char_delta(self, two_dirs):
        result = compare_two(
            two_dirs,
            {"subs": [sub_section("1", "T", "aaaa")]},
            {"subs": [sub_section("1", "T", "aaaaaaaa")]},
        )
        prose = [f for f in result.findings if f.kind == reg.REGRESSION_PROSE_CHANGED]
        assert len(prose) == 1
        assert "+4" in prose[0].detail

    def test_subsection_removed_is_breaking(self, two_dirs):
        result = compare_two(
            two_dirs,
            {"subs": [sub_section("1"), sub_section("1.1")]},
            {"subs": [sub_section("1")]},
        )
        kinds = [f.kind for f in result.findings]
        assert reg.REGRESSION_SUBSECTION_REMOVED in kinds
        assert result.regressed is True

    def test_subsection_added_is_advisory(self, two_dirs):
        result = compare_two(
            two_dirs,
            {"subs": [sub_section("1")]},
            {"subs": [sub_section("1"), sub_section("1.2")]},
        )
        kinds = [f.kind for f in result.findings]
        assert reg.REGRESSION_SUBSECTION_ADDED in kinds
        assert result.regressed is False

    def test_confirmed_share_drop_is_advisory(self, two_dirs):
        result = compare_two(
            two_dirs,
            {"claims": [claim_entry("C01", "a", "confirmed"),
                        claim_entry("C02", "b", "confirmed")]},
            {"claims": [claim_entry("C01", "a", "confirmed"),
                        claim_entry("C02", "b2", "inferred", "docs/b2.json"),
                        claim_entry("C03", "c", "inferred", "docs/c.json")]},
        )
        kinds = [f.kind for f in result.findings]
        assert reg.REGRESSION_CONFIRMED_SHARE_DROP in kinds
        drop = [f for f in result.findings if f.kind == reg.REGRESSION_CONFIRMED_SHARE_DROP]
        assert drop[0].breaking is False

    def test_confirmed_share_within_tolerance_not_flagged(self, two_dirs):
        base = {"claims": [claim_entry(f"C{i:02d}", f"s{i}", "confirmed") for i in range(20)]}
        cur_claims = [claim_entry(f"C{i:02d}", f"s{i}", "confirmed") for i in range(20)]
        cur_claims.append(claim_entry("C99", "extra", "inferred", "docs/e.json"))
        result = compare_two(two_dirs, base, {"claims": cur_claims})
        kinds = [f.kind for f in result.findings]
        assert reg.REGRESSION_CONFIRMED_SHARE_DROP not in kinds


# --------------------------------------------------------------------------- #
# RegressionReport + golden-set comparison
# --------------------------------------------------------------------------- #


class TestRegressionReport:
    def test_advisory_and_blocking_are_structural(self):
        with pytest.raises(ValueError):
            reg.RegressionReport(results=(), golden_set_findings=(), advisory=False)
        with pytest.raises(ValueError):
            reg.RegressionReport(results=(), golden_set_findings=(), blocking=True)

    def test_compare_to_golden_set_clean(self, tmp_path):
        s = write_section(tmp_path / "excellence_section.json")
        golden = {"excellence_section": freeze(s)}
        report = reg.compare_to_golden_set(golden, [s])
        assert report.regressed is False
        d = report.to_dict()
        assert d["record_type"] == "regression_golden_report"
        assert d["advisory"] is True
        assert d["blocking"] is False

    def test_missing_section_is_breaking(self, tmp_path):
        s = write_section(tmp_path / "excellence_section.json")
        golden = {"excellence_section": freeze(s), "impact_section": freeze(s)}
        golden["impact_section"] = reg.SectionFingerprint(
            **{**_fp_kwargs(golden["impact_section"]), "section_id": "impact_section"}
        )
        report = reg.compare_to_golden_set(golden, [s])
        kinds = [f.kind for f in report.golden_set_findings]
        assert reg.REGRESSION_SECTION_MISSING in kinds
        assert report.regressed is True

    def test_new_section_is_advisory(self, tmp_path):
        s1 = write_section(tmp_path / "excellence_section.json")
        s2 = write_section(tmp_path / "impact_section.json")
        golden = {"excellence_section": freeze(s1)}
        report = reg.compare_to_golden_set(golden, [s1, s2])
        kinds = [f.kind for f in report.golden_set_findings]
        assert reg.REGRESSION_SECTION_ADDED in kinds
        assert report.regressed is False

    def test_report_summary_counts(self, tmp_path):
        s = write_section(tmp_path / "excellence_section.json",
                          claims=[claim_entry("C01", "a"), claim_entry("C02", "b")])
        golden = {"excellence_section": freeze(s)}
        write_section(tmp_path / "excellence_section.json",
                      claims=[claim_entry("C01", "a")])
        report = reg.compare_to_golden_set(golden, [s])
        d = report.to_dict()
        assert d["regressed"] is True
        assert d["summary"]["breaking"] >= 1


def _fp_kwargs(fp: "reg.SectionFingerprint") -> dict[str, Any]:
    return {
        "section_id": fp.section_id,
        "artifact_path": fp.artifact_path,
        "artifact_sha256": fp.artifact_sha256,
        "frozen_at": fp.frozen_at,
        "claims": fp.claims,
        "sub_sections": fp.sub_sections,
    }


# --------------------------------------------------------------------------- #
# Judge lane — E2 grounding baseline reuse
# --------------------------------------------------------------------------- #


class TestJudgeLane:
    def _section(self, tmp_path) -> Path:
        return write_section(
            tmp_path / "excellence_section.json",
            claims=[
                claim_entry("C01", "solid claim", "confirmed", "docs/a.json"),
                claim_entry("C02", "fragile claim", "confirmed", "docs/b.json"),
            ],
        )

    def test_freeze_section_grounding(self, tmp_path):
        p = self._section(tmp_path)
        judge = make_judge(lambda s, u: {"passed": True, "score": 1.0, "rationale": "ok"})
        baseline = reg.freeze_section_grounding(
            p, judge,
            repo_root=tmp_path,
            working_assumptions=EMPTY_WA,
            source_text_resolver=lambda ref, root: "the source text",
        )
        assert baseline.section_id == "excellence_section"
        assert {s.entry_key for s in baseline.snapshots} == {"C01#0", "C02#1"}
        assert all(s.met_bar for s in baseline.snapshots)
        assert baseline.judge_model == "acme-judge-1"

    def test_compare_section_grounding_flags_bar_regression(self, tmp_path):
        p = self._section(tmp_path)
        good = make_judge(lambda s, u: {"passed": True, "score": 1.0, "rationale": "ok"})
        baseline = reg.freeze_section_grounding(
            p, good,
            repo_root=tmp_path,
            working_assumptions=EMPTY_WA,
            source_text_resolver=lambda ref, root: "src",
        )
        # After a soft-cap lift / model swap the fragile claim loses grounding.
        weakened = make_judge(
            lambda s, u: {
                "passed": "fragile claim" not in u,
                "score": 0.2 if "fragile claim" in u else 1.0,
                "rationale": "r",
            }
        )
        invariance = reg.compare_section_grounding(
            p, baseline, weakened,
            repo_root=tmp_path,
            working_assumptions=EMPTY_WA,
            source_text_resolver=lambda ref, root: "src",
        )
        assert invariance.invariant is False
        assert [v.claim_id for v in invariance.breaking_violations] == ["C02#1"]


# --------------------------------------------------------------------------- #
# CLI — freeze / check (merge-advisory)
# --------------------------------------------------------------------------- #


class TestCli:
    def _setup(self, tmp_path) -> tuple[Path, Path]:
        sections = tmp_path / "sections"
        sections.mkdir()
        write_section(sections / "excellence_section.json",
                      claims=[claim_entry("C01", "a"), claim_entry("C02", "b")])
        write_section(sections / "impact_section.json")
        return sections, tmp_path / "golden"

    def test_freeze_then_clean_check(self, tmp_path, capsys):
        sections, golden = self._setup(tmp_path)
        assert reg.main(["freeze", "--sections", str(sections), "--out", str(golden)]) == 0
        assert sorted(p.name for p in golden.glob("*.golden.json")) == [
            "excellence_section.golden.json",
            "impact_section.golden.json",
        ]
        assert reg.main(["check", "--sections", str(sections), "--golden", str(golden)]) == 0
        out = capsys.readouterr().out
        assert "regression_golden_report" in out

    def test_check_flags_drift_with_exit_1(self, tmp_path, capsys):
        sections, golden = self._setup(tmp_path)
        assert reg.main(["freeze", "--sections", str(sections), "--out", str(golden)]) == 0
        write_section(sections / "excellence_section.json",
                      claims=[claim_entry("C01", "a")])  # C02 vanished
        rc = reg.main(["check", "--sections", str(sections), "--golden", str(golden)])
        assert rc == 1
        out = capsys.readouterr().out
        assert reg.REGRESSION_CLAIM_REMOVED in out

    def test_check_fail_closed_on_empty_golden_dir(self, tmp_path, capsys):
        sections, golden = self._setup(tmp_path)
        golden.mkdir()
        rc = reg.main(["check", "--sections", str(sections), "--golden", str(golden)])
        assert rc == 2

    def test_check_writes_report_file(self, tmp_path, capsys):
        sections, golden = self._setup(tmp_path)
        reg.main(["freeze", "--sections", str(sections), "--out", str(golden)])
        report_path = tmp_path / "report.json"
        reg.main([
            "check", "--sections", str(sections), "--golden", str(golden),
            "--report", str(report_path),
        ])
        data = json.loads(report_path.read_text(encoding="utf-8-sig"))
        assert data["record_type"] == "regression_golden_report"
        assert data["blocking"] is False
