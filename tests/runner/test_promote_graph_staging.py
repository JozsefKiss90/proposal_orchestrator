"""
Regression seam for ``tools/promote_graph_staging.py`` — the *explicit* half of
the open-Q #4 resolution ("parallel + explicit promote", M2-T10 / DOD-1d).

The open-Q #4 decision
(``decision_log/dod-1d-open-q4-parallel-explicit-promote_2026-07-28.json``)
ratifies that the graph becomes the authoritative Tier-3/Tier-5 source ONLY via
a deliberate, human-invoked, fail-closed promotion — never a silent compiler
auto-overwrite. Before this seam the promote tool carried the whole weight of
that decision with no test at all. These tests pin the load-bearing behaviour
that makes the recorded decision true, so any future change to the promote path
that would falsify it surfaces as a red test:

  * **parallel / non-destructive:** dry-run is the default; nothing is written
    without ``--apply`` (the compiler stages, it never clobbers ``docs/``);
  * **explicit + fail-closed:** a ``project_id`` mismatch refuses to promote, so
    a stale or second-instance staging can never overwrite the active docs;
  * **reversible provenance:** ``--apply`` backs up every overwritten canonical
    file and writes ``promote_record.json`` stamped with ``open_q4_resolution``;
  * **deterministic (§17.5.3):** same staging ⇒ same promotion; a second apply
    reports zero changes — the Claude-free byte-copy guarantee the decision leans on.

Plus a thin consistency check that the durable decision entry exists, records
"parallel + explicit promote", identifies open-Q #4 / DOD-1d, and *references*
(does not duplicate) the LG-1 coarse-ledger decision.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools.promote_graph_staging import (
    BACKUP_REL,
    PART_B_REPORT_REL,
    PromoteError,
    RECORD_REL,
    STAGING_REL,
    promote,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DECISION_LOG_REL = "docs/tier4_orchestration_state/decision_log"
OPEN_Q4_ENTRY = "dod-1d-open-q4-parallel-explicit-promote_2026-07-28.json"
COARSE_LEDGER_ENTRY = "lg1-coarse-claim-ledger-measured_2026-07-27.json"
COARSE_LEDGER_MEASUREMENT = "lg1_ledger_granularity_measurement_2026-07-27.json"
RESOLUTION_STAMP = "parallel + explicit promote (M2-T10)"

# A single staged Tier-5 section, relative to ``staging/docs/``. The canonical
# destination the promote maps it to is ``docs/<REL>`` — the exact string the
# promote reports in promoted_files / changed_files.
STAGED_REL = "tier5_deliverables/proposal_sections/toy_section.json"
CANONICAL_REL = "docs/" + STAGED_REL


def _canonical(repo_root: Path) -> Path:
    return repo_root / "docs" / STAGED_REL


def _make_staging(repo_root: Path, project_id: str, body: str = '{"v": 1}\n') -> None:
    """Write a minimal non-destructive staging tree + part_b_report under repo_root."""
    staged = repo_root / STAGING_REL / "docs" / STAGED_REL
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_text(body, encoding="utf-8")
    report = repo_root / PART_B_REPORT_REL
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps({"project_id": project_id}), encoding="utf-8")


def _make_config(tmp_path: Path, project_id: str) -> Path:
    cfg = tmp_path / "graph.config.yaml"
    cfg.write_text(
        f"project_id: {project_id}\nvault_path: methodology_graph\n",
        encoding="utf-8",
    )
    return cfg


# ===========================================================================
# 1. Parallel / non-destructive: dry-run is the default
# ===========================================================================


class TestNonDestructiveDefault:

    def test_dry_run_writes_nothing(self, tmp_path: Path) -> None:
        """apply=False must not touch docs/ nor write promote_record.json."""
        _make_staging(tmp_path, "toy-instance")
        cfg = _make_config(tmp_path, "toy-instance")
        # A canonical file that DIFFERS from staging — proves dry-run leaves it.
        canonical = _canonical(tmp_path)
        canonical.parent.mkdir(parents=True, exist_ok=True)
        canonical.write_text('{"v": 0}\n', encoding="utf-8")

        rec = promote(tmp_path, cfg, apply=False)

        assert rec["apply"] is False
        # The diff is still computed (so a human can see what WOULD change)...
        assert CANONICAL_REL in rec["changed_files"]
        # ...but nothing on disk moved.
        assert canonical.read_text(encoding="utf-8") == '{"v": 0}\n'
        assert not (tmp_path / RECORD_REL).exists()
        assert not (tmp_path / BACKUP_REL).exists()


# ===========================================================================
# 2. Explicit + fail-closed: project_id guard, missing staging
# ===========================================================================


class TestFailClosed:

    def test_project_id_mismatch_refuses(self, tmp_path: Path) -> None:
        """Staging for another instance can never clobber the active docs."""
        _make_staging(tmp_path, "other-instance")
        cfg = _make_config(tmp_path, "toy-instance")
        canonical = _canonical(tmp_path)
        canonical.parent.mkdir(parents=True, exist_ok=True)
        canonical.write_text('{"v": 0}\n', encoding="utf-8")

        with pytest.raises(PromoteError, match="project_id"):
            promote(tmp_path, cfg, apply=True)

        # Fail-closed: the mismatched instance did not overwrite anything.
        assert canonical.read_text(encoding="utf-8") == '{"v": 0}\n'
        assert not (tmp_path / RECORD_REL).exists()

    def test_missing_staging_tree_refuses(self, tmp_path: Path) -> None:
        cfg = _make_config(tmp_path, "toy-instance")
        with pytest.raises(PromoteError):
            promote(tmp_path, cfg, apply=True)

    def test_missing_reports_refuses(self, tmp_path: Path) -> None:
        """A staging tree with no diff/part_b report cannot assert its project_id."""
        staged = tmp_path / STAGING_REL / "docs" / STAGED_REL
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_text('{"v": 1}\n', encoding="utf-8")
        cfg = _make_config(tmp_path, "toy-instance")
        with pytest.raises(PromoteError):
            promote(tmp_path, cfg, apply=True)


# ===========================================================================
# 3. Reversible provenance: backup + promote_record on --apply
# ===========================================================================


class TestApplyBacksUpAndRecords:

    def test_apply_overwrites_backs_up_and_stamps_record(self, tmp_path: Path) -> None:
        _make_staging(tmp_path, "toy-instance", body='{"v": 1}\n')
        cfg = _make_config(tmp_path, "toy-instance")
        canonical = _canonical(tmp_path)
        canonical.parent.mkdir(parents=True, exist_ok=True)
        canonical.write_text('{"v": 0}\n', encoding="utf-8")

        rec = promote(tmp_path, cfg, apply=True)

        # Canonical now carries the staged bytes.
        assert canonical.read_text(encoding="utf-8") == '{"v": 1}\n'
        # The prior canonical content is preserved for reversal.
        backup = tmp_path / BACKUP_REL / "docs" / STAGED_REL
        assert backup.read_text(encoding="utf-8") == '{"v": 0}\n'
        # The durable record carries the open-Q #4 stamp.
        record_path = tmp_path / RECORD_REL
        assert record_path.exists()
        written = json.loads(record_path.read_text(encoding="utf-8"))
        assert written["open_q4_resolution"] == RESOLUTION_STAMP
        assert written["project_id"] == "toy-instance"
        assert written["apply"] is True
        assert CANONICAL_REL in written["changed_files"]
        assert rec == written


# ===========================================================================
# 4. Deterministic (§17.5.3): same staging ⇒ same promotion
# ===========================================================================


class TestDeterministicIdempotent:

    def test_second_apply_reports_no_changes(self, tmp_path: Path) -> None:
        _make_staging(tmp_path, "toy-instance")
        cfg = _make_config(tmp_path, "toy-instance")

        first = promote(tmp_path, cfg, apply=True)
        # First promote created the file (no prior canonical) => it changed.
        assert CANONICAL_REL in first["changed_files"]

        second = promote(tmp_path, cfg, apply=True)
        # Same staging bytes now equal the canonical => nothing changes.
        assert second["changed_files"] == []
        # But the file is still promoted (listed), just unchanged.
        assert CANONICAL_REL in second["promoted_files"]
        assert second["promoted_files"] == first["promoted_files"]


# ===========================================================================
# 5. The durable open-Q #4 decision entry (DOD-1d)
# ===========================================================================


class TestOpenQ4DecisionEntry:

    def _entry(self) -> dict:
        path = REPO_ROOT / DECISION_LOG_REL / OPEN_Q4_ENTRY
        assert path.is_file(), f"open-Q #4 decision entry missing: {path}"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_entry_exists_and_is_valid_json(self) -> None:
        data = self._entry()
        assert isinstance(data, dict) and data  # non-empty object

    def test_entry_records_the_resolution_and_identifies_open_q4(self) -> None:
        blob = json.dumps(self._entry()).lower()
        # The resolution itself.
        assert "parallel" in blob
        assert "explicit promote" in blob
        # Identifies open-Q #4 and its DOD-1d ticket.
        assert "open-q #4" in blob or "open-q4" in blob or "open_q4" in blob
        assert "dod-1d" in blob
        # Cites the mechanism it ratifies.
        assert "promote_graph_staging" in blob
        assert "promote_record" in blob

    def test_entry_references_but_does_not_duplicate_coarse_ledger(self) -> None:
        """The coarse-ledger property is DECIDED in LG-1; this entry only cites it."""
        blob = json.dumps(self._entry())
        # Delegates to the LG-1 decision + measurement by filename.
        assert COARSE_LEDGER_ENTRY in blob
        assert COARSE_LEDGER_MEASUREMENT in blob
        # Does not re-litigate the measurement: the drafter-vs-graph cardinality
        # numbers (406 / 33.8x) live in LG-1, not here.
        assert "406" not in blob
        assert "33.8" not in blob

    def test_entry_records_the_tools_exact_open_q4_stamp(self) -> None:
        """The entry records the tool's exact open_q4_resolution stamp — the full
        ``parallel + explicit promote (M2-T10)`` string, incl. the M2-T10
        qualifier that the looser resolution check above does not require — tying
        the durable decision to the promote contract (RESOLUTION_STAMP is pinned
        equal to the tool's written record in TestApplyBacksUpAndRecords)."""
        blob = json.dumps(self._entry())
        assert RESOLUTION_STAMP in blob
