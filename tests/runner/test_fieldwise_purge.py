"""FIELDWISE ticket 1 — the durable half of the purge and the decision-log split.

`plans/fieldwise_tickets.md` ticket 1 executes a one-shot state transition: run-scoped
Tier 4 state, all of Tier 5, and the superseded Tier 3 are removed, and the 52-file
decision log is split three ways per `plans/fieldwise_reinstantiation_plan.md` §2.1.

Most of that transition is not an invariant. Tickets 3-5 re-seed Tier 3 and tickets
8-10 re-populate Tier 4 and Tier 5, so a test asserting those directories stay empty
would go red as the frontier advances. This module pins only the part that must hold
for every later ticket:

* the three-way split itself (18 deleted, 5 archived, 29 retained by id),
* the load-bearing archive move that clears the exporter's `SYNTHETIC DEMO` stamp
  (`runner/docx_exporter.py:96` globs `decision_log/synthetic-spine*.json`
  non-recursively, so the record survives in `archive/demo-run/` without stamping the
  FIELDWISE export),
* the §13.11 correction that moved the project draft out of Tier 2A, and
* the §12.3 vault supersession record that ticket 12 closes out.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.docx_exporter import _synthetic_override_active
from runner.paths import find_repo_root


DECISION_LOG = "docs/tier4_orchestration_state/decision_log"
ARCHIVE = f"{DECISION_LOG}/archive/demo-run"

DRAFT_RELPATH = (
    "docs/tier3_project_instantiation/source_materials/part_b_draft_v0/"
    "FIELDWISE_MSCA_Master_Draft.docx"
)

PURGE_RECORD = "fieldwise-purge-and-decision-log-split_2026-08-11.json"
TIER2A_CORRECTION_RECORD = (
    "tier2a-project-draft-misplacement-correction_2026-08-11.json"
)
VAULT_SUPERSESSION_RECORD = "vault-supersession-fieldwise_2026-08-11.json"

# Group 1 of the §2.1 split: runner-written run state referencing artifacts the
# purge deleted. Regenerable, so their absence is durable — a later run writes new
# hash-suffixed files, never these.
DELETED_RUN_RECORDS = (
    "decision-log-update_0401295c.json",
    "decision-log-update_13139efa.json",
    "decision-log-update_4acdc86e.json",
    "decision-log-update_531ec9f0.json",
    "decision-log-update_5952b165.json",
    "decision-log-update_854fd6e8.json",
    "decision-log-update_c084e3dd.json",
    "decision-log-update_d0675cf5.json",
    "decision-log-update_msca-pf-.json",
    "topic-scope-check_0401295c.json",
    "topic-scope-check_80f2c313.json",
    "topic-scope-check_854fd6e8.json",
    "topic-scope-check_c084e3dd.json",
    "topic-scope-check_ec190493.json",
    "topic-scope-check_msca-pf-.json",
    "gate_failure_gate_09_budget_consistency_budget_gate_validator_"
    "2026-07-15T00_00_00Z.json",
    "gate_failure_gate_09_budget_consistency_budget_gate_validator_"
    "2026-07-15T000000Z.json",
    "gate_failure_gate_09_budget_consistency_budget_gate_validator_"
    "2026-07-15T12_00_00Z.json",
)

# Group 2: human decisions about the superseded project. FIELDWISE replaces all five.
ARCHIVED_PROJECT_RECORDS = (
    "13b-real-data-consolidation_2026-07-16.json",
    "action-confirmation-msca-pf_2026-07-13.json",
    "synthetic-concept-override-extension_2026-07-14.json",
    "synthetic-spine-demo-override_2026-07-13.json",
    "tier3-hand-lift-msca-pf_2026-07-13.json",
)

# Group 3: rulings that govern the engine regardless of which call is written.
RETAINED_ENGINE_RULINGS = (
    "chk-1-checkpoint-provenance-quad_2026-07-24.json",
    "d14-refinement-finalization-standard_2026-07-14.json",
    "dod-1-phase1-3-gate-result-conflict-resolution_2026-07-27.json",
    "dod-1c-determinism-recheck-from-graph_2026-07-28.json",
    "dod-1d-open-q4-parallel-explicit-promote_2026-07-28.json",
    "dod-1e-n08f-checkpoint-published_2026-07-28.json",
    "drafting-review-status-skill_2026-07-30.json",
    "e2-status-aware-faithfulness-framework_2026-07-20.json",
    "e3-claim-ledger-completeness_2026-07-21.json",
    "e3.1-materiality-calibration_2026-08-03.json",
    "e4-regression-golden-set_2026-07-21.json",
    "e5f-rubric-grading-budget_2026-08-10.json",
    "final-export-writer-component_2026-07-30.json",
    "gate-result-schema-id-fix-and-backfill_2026-07-22.json",
    "gate10b-canonical-cross-reference-false-positive_2026-07-17.json",
    "graph-topology-d8-absorb_2026-07-16.json",
    "hyg-1-bffe89d-conflict-marker-corruption-sweep_2026-07-27.json",
    "lg1-coarse-claim-ledger-measured_2026-07-27.json",
    "lg1_ledger_granularity_measurement_2026-07-27.json",
    "milestone1-engine-integration-proof_2026-07-15.json",
    "ms2-ticket8-author-proposal-graph_2026-07-20.json",
    "ms2-ticket9-agnosticism-proof_2026-07-20.json",
    "phase7-8-deferral_2026-07-14.json",
    "runtime-skillresult-envelope-normalization_2026-07-14.json",
    "runtime-truncation-fix_2026-07-14.json",
    "section-type-taxonomy-drift-correction_2026-07-29.json",
    "st-1-content-based-staleness_2026-07-27.json",
    "status-vocabulary-correction_2026-07-13.json",
    "transport-stream-json-reassembly_2026-07-30.json",
)


@pytest.fixture(scope="module")
def root() -> Path:
    return find_repo_root()


def _load(root: Path, relpath: str) -> dict:
    path = root / relpath
    assert path.is_file(), f"missing decision-log record: {relpath}"
    return json.loads(path.read_text(encoding="utf-8"))


class TestSplitPartition:
    """The 52 files land in exactly three places, by id."""

    def test_auto_generated_run_records_are_deleted(self, root: Path) -> None:
        log_dir = root / DECISION_LOG
        present = [n for n in DELETED_RUN_RECORDS if (log_dir / n).exists()]
        assert present == [], f"demo-run state survived the purge: {present}"

    def test_auto_generated_run_records_were_not_archived_instead(
        self, root: Path
    ) -> None:
        archive = root / ARCHIVE
        leaked = [n for n in DELETED_RUN_RECORDS if (archive / n).exists()]
        assert leaked == [], f"regenerable run state archived, not deleted: {leaked}"

    def test_project_scoped_decisions_are_archived(self, root: Path) -> None:
        archive = root / ARCHIVE
        missing = [n for n in ARCHIVED_PROJECT_RECORDS if not (archive / n).is_file()]
        assert missing == [], f"missing from {ARCHIVE}: {missing}"

    def test_project_scoped_decisions_left_the_log_root(self, root: Path) -> None:
        log_dir = root / DECISION_LOG
        remaining = [n for n in ARCHIVED_PROJECT_RECORDS if (log_dir / n).exists()]
        assert remaining == [], f"superseded records still at log root: {remaining}"

    def test_engine_rulings_stay_in_place(self, root: Path) -> None:
        log_dir = root / DECISION_LOG
        missing = [n for n in RETAINED_ENGINE_RULINGS if not (log_dir / n).is_file()]
        assert missing == [], f"engine rulings lost to the purge: {missing}"

    def test_retained_engine_rulings_are_readable_json(self, root: Path) -> None:
        for name in RETAINED_ENGINE_RULINGS:
            _load(root, f"{DECISION_LOG}/{name}")

    def test_split_covers_every_file_of_the_original_log(self) -> None:
        total = (
            len(DELETED_RUN_RECORDS)
            + len(ARCHIVED_PROJECT_RECORDS)
            + len(RETAINED_ENGINE_RULINGS)
        )
        assert (18, 5, 29) == (
            len(DELETED_RUN_RECORDS),
            len(ARCHIVED_PROJECT_RECORDS),
            len(RETAINED_ENGINE_RULINGS),
        )
        assert total == 52


class TestSyntheticStampCleared:
    """The archive move is load-bearing, not tidy."""

    def test_exporter_reports_no_synthetic_override(self, root: Path) -> None:
        assert _synthetic_override_active(root) is False

    def test_stamp_glob_matches_nothing_at_the_log_root(self, root: Path) -> None:
        matches = sorted((root / DECISION_LOG).glob("synthetic-spine*.json"))
        assert matches == []

    def test_the_override_record_still_exists_in_the_archive(self, root: Path) -> None:
        record = _load(
            root, f"{ARCHIVE}/synthetic-spine-demo-override_2026-07-13.json"
        )
        assert record["id"] == "synthetic-spine-demo-override"


class TestPurgeRecord:
    """§9.4: the split is a durable decision, so it is written down."""

    def test_purge_record_states_the_three_dispositions(self, root: Path) -> None:
        record = _load(root, f"{DECISION_LOG}/{PURGE_RECORD}")
        split = record["decision_log_split"]
        assert split["deleted"]["count"] == 18
        assert split["archived"]["count"] == 5
        assert split["retained"]["count"] == 29

    def test_purge_record_maps_every_archived_file_to_its_new_path(
        self, root: Path
    ) -> None:
        record = _load(root, f"{DECISION_LOG}/{PURGE_RECORD}")
        moved = record["decision_log_split"]["archived"]["moved"]
        assert sorted(moved) == sorted(ARCHIVED_PROJECT_RECORDS)
        for name, destination in moved.items():
            assert destination == f"{ARCHIVE}/{name}"
            assert (root / destination).is_file()


class TestTier2ADraftCorrection:
    """§13.11: a project draft may not sit in instrument-schema space."""

    def test_tier2a_holds_no_project_draft(self, root: Path) -> None:
        tier2a = root / "docs/tier2a_instrument_schemas"
        strays = sorted(p.name for p in tier2a.rglob("part_b_draft_v0"))
        assert strays == []

    def test_the_draft_lives_in_tier3_source_materials(self, root: Path) -> None:
        assert (root / DRAFT_RELPATH).is_file()

    def test_correction_record_cites_13_11_and_both_paths(self, root: Path) -> None:
        record = _load(root, f"{DECISION_LOG}/{TIER2A_CORRECTION_RECORD}")
        assert "§13.11" in record["authority"]
        assert record["moved_from"].startswith("docs/tier2a_instrument_schemas/")
        assert record["moved_to"] == DRAFT_RELPATH
        assert not (root / record["moved_from"]).exists()
        assert (root / record["moved_to"]).is_file()


class TestVaultSupersession:
    """§12.3: the vault contradicts the incoming Tier 3, so the conflict is logged."""

    def test_supersession_record_names_the_vault_and_the_contradiction(
        self, root: Path
    ) -> None:
        record = _load(root, f"{DECISION_LOG}/{VAULT_SUPERSESSION_RECORD}")
        assert "§12.3" in record["authority"]
        assert record["vault_path"] == "MSCA/methodology_graph"
        assert (root / record["vault_path"]).is_dir()

    def test_supersession_is_open_and_names_its_closing_ticket(
        self, root: Path
    ) -> None:
        record = _load(root, f"{DECISION_LOG}/{VAULT_SUPERSESSION_RECORD}")
        assert record["status"] == "open"
        assert "graph_claim_verifier" in json.dumps(record)
        assert record["closed_by"]
