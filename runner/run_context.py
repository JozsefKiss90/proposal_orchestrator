"""
Run context: initialization, manifest management, node state, reuse policy.

Each DAG run has a dedicated subdirectory under ``.claude/runs/<run_id>/``
that contains:

* ``run_manifest.json`` — run identity, versions, node state map, and
  any HARD_BLOCK metadata written during gate evaluation.
* ``reuse_policy.json`` — list of artifact paths approved for reuse across
  runs (populated by operator approval; initially empty).

The :class:`RunContext` is the single point of truth for node state during
a run.  The gate evaluator reads and updates it after each gate evaluation.

Node states (gate_rules_library_plan.md §6.5)
---------------------------------------------
``pending``
    Node is queued; its entry gate has not yet been evaluated.
``running``
    Node is executing; its exit gate has not yet been evaluated.
``blocked_at_entry``
    Entry gate failed; node has not executed; no outputs exist.
``blocked_at_exit``
    Exit gate failed; node executed; outputs exist but are marked invalid.
``released``
    Exit gate passed; outgoing edges are traversable.

Runner-internal transitional state (Step 10 scope)
---------------------------------------------------
``deterministic_pass_semantic_pending``
    All deterministic predicates for the gate passed, but semantic
    predicates exist and have not yet been evaluated (Step 11 is not
    implemented).  This is a runner-internal state.  Downstream work must
    not proceed from a node in this state.

HARD_BLOCK propagation state
-----------------------------
``hard_block_upstream``
    Set on Phase 8 nodes when ``gate_09_budget_consistency`` fails with a
    HARD_BLOCK (missing ``received/`` directory).  Downstream nodes may
    not begin.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from runner.versions import CONSTITUTION_VERSION, LIBRARY_VERSION, MANIFEST_VERSION

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Repo-relative directory for per-run state.
RUNS_DIR_REL: str = ".claude/runs"

RUN_MANIFEST_FILENAME: str = "run_manifest.json"
REUSE_POLICY_FILENAME: str = "reuse_policy.json"

#: All valid node-state values (permanent + runner-internal).
NODE_STATES: frozenset[str] = frozenset(
    {
        "pending",
        "running",
        "blocked_at_entry",
        "blocked_at_exit",
        "released",
        "deterministic_pass_semantic_pending",
        "hard_block_upstream",
    }
)

#: Phase 8 node IDs that are frozen when gate_09 issues a HARD_BLOCK.
#: These must match the canonical node_id values in manifest.compile.yaml exactly.
PHASE_8_NODE_IDS: frozenset[str] = frozenset(
    {
        "n08a_excellence_drafting",
        "n08b_impact_drafting",
        "n08c_implementation_drafting",
        "n08d_assembly",
        "n08e_evaluator_review",
        "n08f_revision",
    }
)


# ---------------------------------------------------------------------------
# RunContext
# ---------------------------------------------------------------------------


class RunContext:
    """
    Manages per-run state: node states, run manifest, and reuse policy.

    Create a new run with :meth:`initialize`.
    Load an existing run with :meth:`load`.
    Persist state with :meth:`save`.
    """

    def __init__(
        self,
        run_id: str,
        repo_root: Path,
        manifest_data: dict,
        reuse_policy: dict,
    ) -> None:
        self.run_id: str = run_id
        self.repo_root: Path = repo_root
        self._manifest: dict = manifest_data
        self._reuse_policy: dict = reuse_policy

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def initialize(
        cls,
        repo_root: Path,
        run_id: Optional[str] = None,
    ) -> "RunContext":
        """
        Create a fresh run context, write the run manifest and reuse policy.

        Parameters
        ----------
        repo_root:
            Repository root directory.
        run_id:
            Explicit run UUID.  When ``None``, a fresh UUID v4 is generated.

        Returns
        -------
        RunContext
            Initialized and persisted context for the new run.
        """
        if run_id is None:
            run_id = str(uuid.uuid4())

        now_iso = datetime.now(timezone.utc).isoformat()

        manifest_data: dict = {
            "run_id": run_id,
            "manifest_version": MANIFEST_VERSION,
            "library_version": LIBRARY_VERSION,
            "constitution_version": CONSTITUTION_VERSION,
            "repo_root": str(repo_root),
            "created_at": now_iso,
            "node_states": {},
        }
        reuse_policy: dict = {
            "reuse_policy_for_run": run_id,
            "approved_artifacts": [],
        }

        ctx = cls(run_id, repo_root, manifest_data, reuse_policy)
        ctx.save()
        return ctx

    @classmethod
    def load_or_initialize(
        cls,
        repo_root: Path,
        run_id: Optional[str] = None,
    ) -> "RunContext":
        """
        Load an existing run context if it exists, otherwise create a new one.

        This preserves node states from prior invocations when re-using a
        ``run_id``.  When the run directory does not yet exist, a fresh
        context is created via :meth:`initialize`.

        Parameters
        ----------
        repo_root:
            Repository root directory.
        run_id:
            Run UUID.  When ``None``, a fresh UUID v4 is generated (and
            ``initialize`` is always called since no prior run can exist).
        """
        if run_id is None:
            return cls.initialize(repo_root)
        try:
            return cls.load(repo_root, run_id)
        except FileNotFoundError:
            return cls.initialize(repo_root, run_id)

    @classmethod
    def load(cls, repo_root: Path, run_id: str) -> "RunContext":
        """
        Load an existing run context from disk.

        Parameters
        ----------
        repo_root:
            Repository root directory.
        run_id:
            UUID of the run to load.

        Raises
        ------
        FileNotFoundError
            If the run manifest does not exist.
        """
        runs_dir = repo_root / RUNS_DIR_REL / run_id
        manifest_path = runs_dir / RUN_MANIFEST_FILENAME
        policy_path = runs_dir / REUSE_POLICY_FILENAME

        if not manifest_path.exists():
            raise FileNotFoundError(
                f"Run manifest not found: {manifest_path}.  "
                f"Call RunContext.initialize(repo_root, run_id={run_id!r}) first."
            )

        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))

        if policy_path.exists():
            reuse_policy = json.loads(policy_path.read_text(encoding="utf-8"))
        else:
            reuse_policy = {
                "reuse_policy_for_run": run_id,
                "approved_artifacts": [],
            }

        return cls(run_id, repo_root, manifest_data, reuse_policy)

    # ------------------------------------------------------------------
    # Paths
    # ------------------------------------------------------------------

    @property
    def run_dir(self) -> Path:
        """Directory for this run's state files."""
        return self.repo_root / RUNS_DIR_REL / self.run_id

    @property
    def run_manifest_path(self) -> Path:
        """Absolute path to ``run_manifest.json``."""
        return self.run_dir / RUN_MANIFEST_FILENAME

    @property
    def reuse_policy_path(self) -> Path:
        """Absolute path to ``reuse_policy.json``."""
        return self.run_dir / REUSE_POLICY_FILENAME

    # ------------------------------------------------------------------
    # Node state
    # ------------------------------------------------------------------

    def get_node_state(self, node_id: str) -> str:
        """Return the current state of *node_id* (default: ``"pending"``)."""
        return self._manifest["node_states"].get(node_id, "pending")

    def set_node_state(
        self,
        node_id: str,
        state: str,
        *,
        failure_origin: str | None = None,
        exit_gate_evaluated: bool | None = None,
        failure_reason: str | None = None,
        failure_category: str | None = None,
    ) -> None:
        """
        Update the state of *node_id* in the in-memory manifest.

        Optional keyword arguments persist failure metadata alongside
        the node state (§9.4 of runtime_integration_plan.md).  Existing
        2-argument calls continue to work unchanged — all kwargs default
        to ``None`` and are only stored when at least one is provided.

        Call :meth:`save` to persist.
        """
        self._manifest["node_states"][node_id] = state

        # Persist failure metadata when any kwarg is explicitly provided.
        has_metadata = (
            failure_origin is not None
            or exit_gate_evaluated is not None
            or failure_reason is not None
            or failure_category is not None
        )
        if has_metadata:
            if "node_failure_details" not in self._manifest:
                self._manifest["node_failure_details"] = {}
            self._manifest["node_failure_details"][node_id] = {
                "failure_origin": failure_origin,
                "exit_gate_evaluated": exit_gate_evaluated,
                "failure_reason": failure_reason,
                "failure_category": failure_category,
            }

    def get_node_failure_details(self, node_id: str) -> dict | None:
        """Return the failure details dict for *node_id*, or ``None``.

        Returns the dict persisted by :meth:`set_node_state` when called
        with failure metadata keyword arguments.  Returns ``None`` if no
        failure metadata has been recorded for *node_id*.
        """
        details = self._manifest.get("node_failure_details")
        if details is None:
            return None
        return details.get(node_id)

    # ------------------------------------------------------------------
    # Continuation acceptance (phase-scoped bootstrap)
    # ------------------------------------------------------------------

    def record_accepted_upstream_gate(
        self,
        gate_id: str,
        original_run_id: str,
        evidence_path: str,
    ) -> None:
        """Record that upstream gate evidence from a prior run was accepted.

        Called by :func:`bootstrap_phase_prerequisites` when prior-run gate
        evidence is accepted to seed an upstream node as ``released``.  The
        record is persisted in the run manifest so that downstream predicates
        (specifically ``gate_pass_recorded``) can verify that the run_id
        mismatch was explicitly accepted by the current run's continuation
        bootstrap — not a stale artifact from an unrelated run.

        The acceptance record preserves provenance: the original artifact's
        ``run_id`` is stored separately from the current run's ``run_id``.

        Does **not** call :meth:`save`; the caller is responsible for
        persisting.
        """
        if "accepted_upstream_gates" not in self._manifest:
            self._manifest["accepted_upstream_gates"] = {}
        self._manifest["accepted_upstream_gates"][gate_id] = {
            "original_run_id": original_run_id,
            "evidence_path": evidence_path,
            "accepted_at": datetime.now(timezone.utc).isoformat(),
            "status": "pass",
        }

    def get_accepted_upstream_gate(self, gate_id: str) -> dict | None:
        """Return the continuation acceptance record for *gate_id*, or None.

        Returns the dict written by :meth:`record_accepted_upstream_gate`
        if the gate was accepted during bootstrap; ``None`` otherwise.
        """
        gates = self._manifest.get("accepted_upstream_gates")
        if gates is None:
            return None
        return gates.get(gate_id)

    # ------------------------------------------------------------------
    # Reuse decisions (Phase 8 section artifact reuse)
    # ------------------------------------------------------------------

    def record_reuse_decision(self, node_id: str, decision: dict) -> None:
        """Record a Phase 8 reuse decision in the run manifest.

        Called by the scheduler after validating reuse eligibility and before
        gate evaluation, so that the ``artifact_owned_by_run`` predicate can
        verify reuse ownership from persisted state.

        Does **not** call :meth:`save`; the caller is responsible for persisting.
        """
        if "reuse_decisions" not in self._manifest:
            self._manifest["reuse_decisions"] = {}
        self._manifest["reuse_decisions"][node_id] = decision

    def get_reuse_decision(self, node_id: str) -> dict | None:
        """Return the reuse decision for *node_id*, or ``None``."""
        decisions = self._manifest.get("reuse_decisions")
        if decisions is None:
            return None
        return decisions.get(node_id)

    # ------------------------------------------------------------------
    # Reuse policy
    # ------------------------------------------------------------------

    def is_artifact_approved(self, artifact_path: str) -> bool:
        """
        Return ``True`` if *artifact_path* is listed in ``approved_artifacts``.

        Both the original string argument and any normalised form may match.
        """
        approved: list = self._reuse_policy.get("approved_artifacts", [])
        return str(artifact_path) in approved

    # ------------------------------------------------------------------
    # HARD_BLOCK propagation
    # ------------------------------------------------------------------

    def mark_hard_block_downstream(
        self, reason: str = "HARD_BLOCK_UPSTREAM"
    ) -> None:
        """
        Set all Phase 8 node IDs to ``"hard_block_upstream"`` and record the
        reason in the manifest.

        Called when ``gate_09_budget_consistency`` fails with a HARD_BLOCK
        (§6.4 of the plan).  Does **not** call :meth:`save`; the caller is
        responsible for persisting.
        """
        for node_id in PHASE_8_NODE_IDS:
            self._manifest["node_states"][node_id] = "hard_block_upstream"
        self._manifest["hard_block_reason"] = reason
        self._manifest["hard_block_gate"] = "gate_09_budget_consistency"

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """
        Write the run manifest and reuse policy to disk.

        Creates the run directory if it does not exist.
        """
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.run_manifest_path.write_text(
            json.dumps(self._manifest, indent=2),
            encoding="utf-8",
        )
        self.reuse_policy_path.write_text(
            json.dumps(self._reuse_policy, indent=2),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a copy of the run manifest dict."""
        return dict(self._manifest)
