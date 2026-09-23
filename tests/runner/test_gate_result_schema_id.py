"""
Regression seam for the gate-result ``schema_id`` contract.

Three things are pinned here, all of which were unenforced when the emit fix
landed:

1. **At the writer.** Every gate result written by ``evaluate_gate()`` — the
   sole gate-result write path in the runtime (§17.6.3) — carries
   ``schema_id == GATE_RESULT_SCHEMA_ID``.  This is asserted against the
   evaluator's own output, not against a per-caller fixture, so a new gate
   kind or a new early-return branch cannot quietly bypass it.

2. **At the reader.** ``gate_pass_recorded`` rejects a gate result whose
   ``schema_id`` is absent or different, with MALFORMED_ARTIFACT — required by
   artifact_schema_specification.yaml §gate_result_schema.  Without this the
   only consumer that noticed was ``checkpoint-publish`` at n08f.

3. **In the backfill.** ``tools/backfill_gate_result_schema_id.py`` is
   idempotent, and it never rewrites a file that already declares a *different*
   schema_id — silently repairing that is the auto-correction CLAUDE.md §17.6.5
   forbids, and it also contradicts the tool's own "adds only" contract.

Also pinned: the runtime constant matches the value declared in
artifact_schema_specification.yaml, so the two cannot drift.
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

import pytest
import yaml

from runner.gate_evaluator import evaluate_gate
from runner.gate_result_registry import (
    GATE_RESULT_PATHS,
    GATE_RESULT_SCHEMA_ID,
    TIER4_ROOT_REL,
)
from runner.predicates.gate_pass_predicates import gate_pass_recorded
from runner.predicates.types import MALFORMED_ARTIFACT
from runner.versions import MANIFEST_VERSION
from tools.backfill_gate_result_schema_id import backfill

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC_PATH = (
    REPO_ROOT
    / ".claude/workflows/system_orchestration/artifact_schema_specification.yaml"
)
PHASE_OUTPUTS_REL = "docs/tier4_orchestration_state/phase_outputs"


# ===========================================================================
# 0. The constant matches the declared schema contract
# ===========================================================================


class TestSchemaIdMatchesSpecification:

    def test_constant_matches_specification_value(self) -> None:
        """GATE_RESULT_SCHEMA_ID == gate_result_schema.schema_id_value."""
        text = SPEC_PATH.read_text(encoding="utf-8")
        match = re.search(
            r"^gate_result_schema:\s*\n\s*schema_id_value:\s*\"([^\"]+)\"",
            text,
            re.MULTILINE,
        )
        assert match is not None, (
            "gate_result_schema.schema_id_value not found in "
            "artifact_schema_specification.yaml"
        )
        assert match.group(1) == GATE_RESULT_SCHEMA_ID


# ===========================================================================
# 1. Assert at the writer
# ===========================================================================


def _write_library(tmp_path: Path, gates: list[dict]) -> Path:
    lib_path = tmp_path / "gate_rules_library.yaml"
    lib_path.write_text(
        yaml.dump(
            {
                "library_version": "1.0",
                "manifest_version": MANIFEST_VERSION,
                "constitution_version": "seam",
                "gate_rules": gates,
            }
        ),
        encoding="utf-8",
    )
    return lib_path


def _exists_pred(path_str: str) -> dict:
    return {
        "predicate_id": f"p_exists_{path_str.replace('/', '_')}",
        "type": "file",
        "function": "exists",
        "args": {"path": path_str},
        "prose_condition": "Path exists",
        "fail_message": "Required path is missing",
    }


def _gate_entry(gate_id: str, predicates: list[dict]) -> dict:
    return {
        "gate_id": gate_id,
        "gate_kind": "exit",
        "evaluated_at": "n01_call_analysis exit",
        "predicates": predicates,
    }


class TestWriterAlwaysStampsSchemaId:
    """Every artifact the gate evaluator writes must declare the schema_id.

    This is the seam the review asked for: asserted *at the writer*, over the
    pass, fail and HARD_BLOCK outcomes, so no branch of the single write path
    can emit a gate result without the field.
    """

    @pytest.mark.parametrize("outcome", ["pass", "fail"])
    def test_written_gate_result_carries_schema_id(
        self, tmp_path: Path, outcome: str
    ) -> None:
        gate_id = f"gate_seam_{outcome}"
        if outcome == "pass":
            (tmp_path / "present.json").write_text("{}", encoding="utf-8")
            preds = [_exists_pred("present.json")]
        else:
            preds = [_exists_pred("absent.json")]
        lib_path = _write_library(tmp_path, [_gate_entry(gate_id, preds)])

        result = evaluate_gate(
            gate_id, str(uuid.uuid4()), tmp_path, library_path=lib_path
        )

        assert result["status"] == outcome
        assert result["schema_id"] == GATE_RESULT_SCHEMA_ID

        on_disk = json.loads(
            Path(result["report_written_to"]).read_text(encoding="utf-8")
        )
        assert on_disk["schema_id"] == GATE_RESULT_SCHEMA_ID

    def test_hard_block_result_carries_schema_id(self, tmp_path: Path) -> None:
        """The HARD_BLOCK branch adds fields after the dict is built; it must
        not be able to produce a result without the schema_id."""
        gate_id = "gate_09_budget_consistency"
        entry = _gate_entry(
            gate_id,
            [
                {
                    "predicate_id": "p_received_non_empty",
                    "type": "file",
                    "function": "dir_non_empty",
                    "args": {
                        "path": (
                            "docs/integrations/lump_sum_budget_planner/received/"
                        )
                    },
                    "prose_condition": "Budget response received",
                    "fail_message": "No validated budget response",
                }
            ],
        )
        entry["hard_block_on_missing_received_dir"] = True
        lib_path = _write_library(tmp_path, [entry])

        result = evaluate_gate(
            gate_id, str(uuid.uuid4()), tmp_path, library_path=lib_path
        )

        assert result["status"] == "fail"
        assert result["hard_block"] is True, "HARD_BLOCK branch not exercised"
        assert result["schema_id"] == GATE_RESULT_SCHEMA_ID

    def test_source_never_hardcodes_the_literal(self) -> None:
        """The evaluator must stamp the shared constant, not a copy of the
        string — otherwise the spec and the runtime can drift silently."""
        src = (REPO_ROOT / "runner/gate_evaluator.py").read_text(encoding="utf-8")
        assert '"schema_id": GATE_RESULT_SCHEMA_ID' in src
        stamped = re.search(r'"schema_id":\s*"orch\.gate_result', src)
        assert stamped is None, (
            "gate_evaluator.py hard-codes the schema_id literal; it must use "
            "GATE_RESULT_SCHEMA_ID from runner.gate_result_registry."
        )


# ===========================================================================
# 2. Assert at the reader
# ===========================================================================


_BASE_RESULT = {
    "gate_id": "phase_01_gate",
    "gate_kind": "exit",
    "run_id": "reader-run",
    "manifest_version": None,  # filled in below
    "library_version": None,
    "constitution_version": None,
    "evaluated_at": "2099-01-01T00:00:00+00:00",
    "input_fingerprint": "sha256:abc",
    "status": "pass",
}


def _write_result(tier4: Path, **overrides) -> Path:
    from runner.versions import (
        CONSTITUTION_VERSION,
        LIBRARY_VERSION,
        MANIFEST_VERSION,
    )

    data = dict(_BASE_RESULT)
    data["manifest_version"] = MANIFEST_VERSION
    data["library_version"] = LIBRARY_VERSION
    data["constitution_version"] = CONSTITUTION_VERSION
    data["schema_id"] = GATE_RESULT_SCHEMA_ID
    data.update(overrides)
    data = {k: v for k, v in data.items() if v is not _OMIT}
    path = tier4 / GATE_RESULT_PATHS["phase_01_gate"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


class _Omit:
    pass


_OMIT = _Omit()


class TestReaderRejectsBadSchemaId:

    def test_valid_schema_id_passes(self, tmp_path: Path) -> None:
        tier4 = tmp_path / "tier4"
        _write_result(tier4)
        result = gate_pass_recorded("phase_01_gate", "reader-run", tier4)
        assert result.passed is True, result.reason

    def test_absent_schema_id_is_malformed(self, tmp_path: Path) -> None:
        tier4 = tmp_path / "tier4"
        _write_result(tier4, schema_id=_OMIT)
        result = gate_pass_recorded("phase_01_gate", "reader-run", tier4)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert "schema_id" in (result.reason or "")

    def test_wrong_schema_id_is_malformed_not_repaired(
        self, tmp_path: Path
    ) -> None:
        tier4 = tmp_path / "tier4"
        path = _write_result(tier4, schema_id="orch.gate_result.v99")
        result = gate_pass_recorded("phase_01_gate", "reader-run", tier4)
        assert result.passed is False
        assert result.failure_category == MALFORMED_ARTIFACT
        assert result.details["recorded_schema_id"] == "orch.gate_result.v99"
        # §17.6.5: reporting a wrong schema_id must not rewrite the artifact.
        on_disk = json.loads(path.read_text(encoding="utf-8"))
        assert on_disk["schema_id"] == "orch.gate_result.v99"


# ===========================================================================
# 3. Backfill: idempotent, and never overwrites a different schema_id
# ===========================================================================


def _write_legacy(repo_root: Path, name: str, **overrides) -> Path:
    data = {
        "gate_id": "phase_01_gate",
        "gate_kind": "exit",
        "status": "pass",
        "run_id": "legacy-run",
    }
    data.update({k: v for k, v in overrides.items() if v is not _OMIT})
    path = repo_root / PHASE_OUTPUTS_REL / "phase1_call_analysis" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


class TestBackfill:

    def test_adds_absent_schema_id(self, tmp_path: Path) -> None:
        path = _write_legacy(tmp_path, "gate_result.json")

        report = backfill(tmp_path, apply=True)

        assert len(report["changed"]) == 1
        assert report["conflicts"] == []
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_id"] == GATE_RESULT_SCHEMA_ID
        # Nothing else may change — it is a format-only migration.
        assert data["gate_id"] == "phase_01_gate"
        assert data["status"] == "pass"
        assert data["run_id"] == "legacy-run"

    def test_is_idempotent(self, tmp_path: Path) -> None:
        path = _write_legacy(tmp_path, "gate_result.json")

        backfill(tmp_path, apply=True)
        first = path.read_bytes()
        second_report = backfill(tmp_path, apply=True)

        assert second_report["changed"] == []
        assert len(second_report["already_ok"]) == 1
        assert path.read_bytes() == first, "re-run rewrote a conforming file"

    def test_dry_run_writes_nothing(self, tmp_path: Path) -> None:
        path = _write_legacy(tmp_path, "gate_result.json")
        before = path.read_bytes()

        report = backfill(tmp_path, apply=False)

        assert len(report["changed"]) == 1
        assert path.read_bytes() == before

    def test_never_overwrites_a_different_schema_id(
        self, tmp_path: Path
    ) -> None:
        """A present-but-wrong schema_id is a validation failure, not a
        repairable condition (CLAUDE.md §17.6.5).  The tool must report it and
        leave the file byte-identical."""
        path = _write_legacy(
            tmp_path, "gate_result.json", schema_id="orch.gate_result.v0"
        )
        before = path.read_bytes()

        report = backfill(tmp_path, apply=True)

        assert report["changed"] == []
        assert report["conflicts"] == [
            {
                "path": f"{PHASE_OUTPUTS_REL}/phase1_call_analysis/gate_result.json",
                "found_schema_id": "orch.gate_result.v0",
            }
        ]
        assert path.read_bytes() == before, (
            "backfill silently repaired a wrong schema_id"
        )

    def test_conflict_makes_the_cli_fail(self, tmp_path: Path) -> None:
        """A conflict must be surfaced as a non-zero exit, not a quiet skip."""
        from tools.backfill_gate_result_schema_id import main

        _write_legacy(
            tmp_path, "gate_result.json", schema_id="orch.gate_result.v0"
        )

        rc = main(["--repo-root", str(tmp_path), "--apply"])

        assert rc == 1

    def test_clean_run_exits_zero(self, tmp_path: Path) -> None:
        from tools.backfill_gate_result_schema_id import main

        _write_legacy(tmp_path, "gate_result.json")

        assert main(["--repo-root", str(tmp_path), "--apply"]) == 0

    def test_ignores_non_gate_result_files(self, tmp_path: Path) -> None:
        path = tmp_path / PHASE_OUTPUTS_REL / "phase1_call_analysis" / "result.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"some": "other artifact"}), encoding="utf-8")
        before = path.read_bytes()

        report = backfill(tmp_path, apply=True)

        assert report["changed"] == []
        assert report["skipped_non_gate"] == 1
        assert path.read_bytes() == before


# ===========================================================================
# 4. Discovery is registry-driven, not a narrow phase_outputs glob (SCH-1)
# ===========================================================================


def _write_gate_result_at(
    repo_root: Path, rel_under_tier4: str, **overrides
) -> Path:
    """Write a gate-result-shaped JSON at an arbitrary path under tier4."""
    data = {
        "gate_id": "phase_02_gate",
        "gate_kind": "exit",
        "status": "fail",
        "run_id": "legacy-run",
    }
    data.update({k: v for k, v in overrides.items() if v is not _OMIT})
    path = repo_root / TIER4_ROOT_REL / rel_under_tier4
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return path


class TestBackfillRegistryDrivenDiscovery:
    """SCH-1: discovery is driven by the runtime's own knowledge of where gate
    results live — the registry (``GATE_RESULT_PATHS``) plus the evaluator's
    fallback subdir — with a labelled safety-net sweep for preserved artifacts.
    The old ``phase_outputs/**/*result*.json`` glob missed both sibling
    locations named in the finding.
    """

    def test_finds_preserved_non_canonical_result(self, tmp_path: Path) -> None:
        """``alpha_honest_block/phase2_gate_result_HONEST_BLOCK.json`` lives
        *outside* ``phase_outputs/`` and was silently missed.  It must now be
        discovered, backfilled, and reported under ``non_canonical`` so a file
        caught outside the canonical path model is always visible."""
        rel_under = "alpha_honest_block/phase2_gate_result_HONEST_BLOCK.json"
        path = _write_gate_result_at(tmp_path, rel_under, schema_id=_OMIT)

        report = backfill(tmp_path, apply=True)

        rel = f"{TIER4_ROOT_REL}/{rel_under}"
        assert rel in report["changed"]
        assert rel in report["non_canonical"]
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_id"] == GATE_RESULT_SCHEMA_ID

    def test_finds_non_canonical_result_without_result_token(
        self, tmp_path: Path
    ) -> None:
        """A preserved gate result at a non-canonical location whose filename
        lacks the ``result`` token must still be found: discovery keys on the
        gate-result *shape* (gate_id + gate_kind + status), not on a filename
        heuristic, so the sweep cannot be evaded by a name like
        ``phase2_gate_HONEST_BLOCK.json``."""
        rel_under = "alpha_honest_block/phase2_gate_HONEST_BLOCK.json"
        path = _write_gate_result_at(tmp_path, rel_under, schema_id=_OMIT)

        report = backfill(tmp_path, apply=True)

        rel = f"{TIER4_ROOT_REL}/{rel_under}"
        assert rel in report["changed"]
        assert rel in report["non_canonical"]
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_id"] == GATE_RESULT_SCHEMA_ID

    def test_finds_fallback_dir_result_without_result_token(
        self, tmp_path: Path
    ) -> None:
        """The evaluator writes unregistered gate_ids to
        ``gate_results/<gate_id>.json`` — a name with **no** ``result`` token,
        which the old ``*result*.json`` glob could never match.  Discovery via
        the fallback subdir must find and backfill it, and it is *not* flagged
        non-canonical (the fallback dir is a known runtime location)."""
        rel_under = "gate_results/gate_09_budget_consistency.json"
        path = _write_gate_result_at(
            tmp_path,
            rel_under,
            gate_id="gate_09_budget_consistency",
            schema_id=_OMIT,
        )

        report = backfill(tmp_path, apply=True)

        rel = f"{TIER4_ROOT_REL}/{rel_under}"
        assert rel in report["changed"]
        assert rel not in report["non_canonical"]
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["schema_id"] == GATE_RESULT_SCHEMA_ID

    def test_non_canonical_conflict_still_fails_closed(
        self, tmp_path: Path
    ) -> None:
        """A wrong schema_id at a non-canonical location is a conflict and must
        never be rewritten (§17.6.5) — fail-closed is not limited to
        ``phase_outputs/``."""
        path = _write_gate_result_at(
            tmp_path,
            "alpha_honest_block/phase2_gate_result_HONEST_BLOCK.json",
            schema_id="orch.gate_result.v0",
        )
        before = path.read_bytes()

        report = backfill(tmp_path, apply=True)

        assert report["changed"] == []
        assert len(report["conflicts"]) == 1
        assert report["conflicts"][0]["found_schema_id"] == "orch.gate_result.v0"
        assert path.read_bytes() == before


# ===========================================================================
# 5. Root validation + zero-scan is never a silent success (SCH-2)
# ===========================================================================


class TestBackfillRootValidation:
    """SCH-2: a wrong ``--repo-root`` and a zero-scan are each surfaced with a
    distinct non-zero exit, never as a silent clean run.  The old tool
    ``rglob``-ed a missing directory, found nothing, and exited 0 —
    indistinguishable from "all conforming"."""

    def test_wrong_root_is_rejected_distinctly(self, tmp_path: Path) -> None:
        """A ``--repo-root`` without the tier4 tree is a distinct failure (2),
        not 0 (clean) and not 1 (conflict)."""
        from tools.backfill_gate_result_schema_id import main

        # tmp_path has no docs/tier4_orchestration_state/ — a misdirected root.
        assert main(["--repo-root", str(tmp_path), "--apply"]) == 2

    def test_zero_scan_is_not_a_silent_success(self, tmp_path: Path) -> None:
        """A valid root with no gate results at all exits with a distinct code
        (3), never the exit-0 'all conforming' path."""
        from tools.backfill_gate_result_schema_id import main

        (tmp_path / TIER4_ROOT_REL).mkdir(parents=True)

        assert main(["--repo-root", str(tmp_path), "--apply"]) == 3

    def test_all_conforming_exits_zero(self, tmp_path: Path) -> None:
        """One already-conforming gate result is a genuine clean success (0),
        distinct from the zero-scan code."""
        from tools.backfill_gate_result_schema_id import main

        _write_gate_result_at(
            tmp_path,
            "phase_outputs/phase2_concept_refinement/gate_result.json",
            schema_id=GATE_RESULT_SCHEMA_ID,
        )

        assert main(["--repo-root", str(tmp_path), "--apply"]) == 0
