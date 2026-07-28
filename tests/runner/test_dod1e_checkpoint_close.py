"""
DOD-1e real-run oracle — the msca-pf-graph-01 Phase-8 checkpoint is published
under CHK-1, closing M2-T10 (plans/tickets_phase8_review.md ticket 8.5).

This is an independent, **read-only** oracle over the COMMITTED durable
checkpoint (``docs/tier4_orchestration_state/checkpoints/phase8_checkpoint.json``)
and the committed gate results it inherits from.  It does **not** re-drive
publication: the publisher is write-once, and the one-shot drive that produced
the artifact is recorded in
``decision_log/dod-1e-n08f-checkpoint-published_2026-07-28.json``.  It pins the
three DOD-1e criteria against real data:

  1. the durable checkpoint is published for run ``msca-pf-graph-01``;
  2. it records the cross-run ``inherited_gate_provenance`` quad for the
     bootstrapped ``gate_09`` — copied **verbatim** from the durable gate
     result (so a re-evaluation that drifts the fingerprint is caught);
  3. gate_12's ``checkpoint_published`` predicate (``g11_p06``) passes against
     it — both called directly and dispatched through the gate evaluator's own
     registry, exactly as gate_12 evaluates the predicate.

The exhaustive fixture-level component/predicate behaviour (all-current-run,
fail-closed cross-run, write-once, malformed gates) lives in
``test_checkpoint_publisher.py``; this module is the real-data close and is the
literal end of M2-T10.  It skips (rather than errors) when the reference
artifacts are absent, matching the DOD-1c real-vault-oracle convention.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.checkpoint_publisher import (
    CHECKPOINT_REL,
    CHECKPOINT_SCHEMA_ID,
    CONFIRMED_GATE_IDS,
)
from runner.gate_evaluator import PREDICATE_REGISTRY, _call_predicate
from runner.gate_result_registry import (
    GATE_RESULT_PATHS,
    GATE_RESULT_VERSION_FIELDS,
    TIER4_ROOT_REL,
)
from runner.predicates.schema_predicates import checkpoint_published

_RUN_ID = "msca-pf-graph-01"
_BOOTSTRAPPED_GATE = "gate_09_budget_consistency"
_ORIGINAL_RUN_ID = "msca-pf-real-01"


@pytest.fixture
def real_checkpoint_path(repo_root: Path) -> Path:
    """Path to the committed msca-pf-graph-01 checkpoint; skip if not on this tree."""
    path = repo_root / CHECKPOINT_REL
    if not path.is_file():
        pytest.skip("msca-pf-graph-01 phase8_checkpoint.json not present")
    return path


@pytest.fixture
def real_checkpoint(real_checkpoint_path: Path) -> dict:
    """The committed msca-pf-graph-01 checkpoint, parsed."""
    return json.loads(real_checkpoint_path.read_text(encoding="utf-8-sig"))


# ---------------------------------------------------------------------------
# Criterion 1 — the durable checkpoint is published for the graph run.
# ---------------------------------------------------------------------------


def test_real_checkpoint_published(real_checkpoint: dict):
    cp = real_checkpoint
    assert cp["schema_id"] == CHECKPOINT_SCHEMA_ID
    assert cp["run_id"] == _RUN_ID
    assert cp["status"] == "published"
    assert cp["gate_results_confirmed"] == list(CONFIRMED_GATE_IDS)


# ---------------------------------------------------------------------------
# Criterion 2 — the cross-run provenance quad is recorded, copied verbatim
#               from the durable gate_09 result.
# ---------------------------------------------------------------------------


def test_gate09_durable_result_is_genuinely_cross_run(repo_root: Path):
    """The precondition that makes this a real cross-run close: the durable
    gate_09 result carries a *prior* run_id, so the checkpoint MUST declare a
    quad for it (a degenerate all-current-run checkpoint would not exercise the
    provenance path)."""
    durable_path = repo_root / TIER4_ROOT_REL / GATE_RESULT_PATHS[_BOOTSTRAPPED_GATE]
    if not durable_path.is_file():
        pytest.skip("durable gate_09 result not present")
    durable = json.loads(durable_path.read_text(encoding="utf-8-sig"))
    assert durable["run_id"] == _ORIGINAL_RUN_ID
    assert durable["run_id"] != _RUN_ID
    assert durable["status"] == "pass"


def test_real_checkpoint_records_gate09_quad_verbatim(
    real_checkpoint: dict, repo_root: Path
):
    quad = real_checkpoint.get("inherited_gate_provenance")
    assert quad is not None, "a cross-run checkpoint must record the provenance quad"
    entries = {e["gate_id"]: e for e in quad}
    assert set(entries) == {_BOOTSTRAPPED_GATE}
    entry = entries[_BOOTSTRAPPED_GATE]
    assert entry["original_run_id"] == _ORIGINAL_RUN_ID
    assert entry["evidence_path"] == (
        f"{TIER4_ROOT_REL}/{GATE_RESULT_PATHS[_BOOTSTRAPPED_GATE]}"
    )

    # Every quad field is a verbatim copy of the durable gate result on disk.
    durable_path = repo_root / TIER4_ROOT_REL / GATE_RESULT_PATHS[_BOOTSTRAPPED_GATE]
    durable = json.loads(durable_path.read_text(encoding="utf-8-sig"))
    assert entry["input_fingerprint"] == durable["input_fingerprint"]
    assert entry["versions"] == {k: durable[k] for k in GATE_RESULT_VERSION_FIELDS}


# ---------------------------------------------------------------------------
# Criterion 3 — gate_12's checkpoint_published predicate (g11_p06) passes.
# ---------------------------------------------------------------------------


def test_real_checkpoint_predicate_passes_directly(
    real_checkpoint_path: Path, repo_root: Path
):
    res = checkpoint_published(real_checkpoint_path, repo_root=repo_root)
    assert res.passed, res.reason
    assert res.details["inherited_gate_provenance_checked"] == [_BOOTSTRAPPED_GATE]


def test_g11_p06_passes_via_gate_evaluator_dispatch(
    real_checkpoint_path: Path, repo_root: Path
):
    """The predicate passes through the gate evaluator's own registry lookup +
    arg injection — the exact path gate_12 uses to evaluate g11_p06, with the
    canonical ``path`` arg from gate_rules_library.yaml.  Targets the single
    predicate (not all of gate_12) so it needs no other Phase-8 artifacts.  The
    ``real_checkpoint_path`` fixture is the skip-guard; the predicate resolves the
    same relative path itself."""
    assert PREDICATE_REGISTRY["checkpoint_published"] is checkpoint_published
    res = _call_predicate(
        "checkpoint_published",
        {"path": CHECKPOINT_REL},
        _RUN_ID,
        repo_root,
        None,
    )
    assert res.passed, res.reason
