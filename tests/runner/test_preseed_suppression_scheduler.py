"""
Regression seam for the Phase-8 suppression of draft-consuming deterministic
components (``runner/dag_scheduler.py``, Step 2.45 → Step 3).

The fix under test
------------------
When the drafting skill is superseded for n08a/n08b/n08c — by a manual preseed
(``--preseed-phase8-sections``) *or* by Phase-8 reuse — an authoritative section
artifact already exists on disk and the ``section_drafts/`` are not this run's
product.  The scheduler therefore drops the declared
``DRAFT_CONSUMING_COMPONENTS`` (the section-assemblers and assumption-appliers)
from the node's manifest binding and keeps ``canonical_pack_deriver``.  Without
that suppression the assembler recomposes the section from the drafts on disk,
either clobbering the authoritative prose (drafts under the current run_id) or
failing the node outright on the spine run_id mismatch (drafts carried over from
a prior run — the mode actually observed on ``msca-pf-graph-01``).

What this module asserts
------------------------
The seam is **behavioural, not structural**: the fake ``run_agent`` really
invokes every deterministic component the scheduler hands it, through the same
``invoke_component`` substrate the agent runtime uses.  The prose assertions are
therefore load-bearing — if the suppression is removed, the assembler runs for
real and the assertions go red.  ``TestFixtureIsRedCapable`` proves exactly that
by running the assembler directly over the same fixture and showing it does
damage.

  A. Preseeded prose survives when the drafts are same-run (recomposition hazard)
  B. Preseeded prose survives, node still released, when the drafts are
     foreign-run (the observed spine run_id mismatch)
  C. Suppression is scoped: canonical_pack_deriver is retained, and nothing is
     dropped when neither supersession mode is active
  D. The fixture is red-capable (negative control)
  E. The declared draft-consuming set is a checked invariant, not a coincidence,
     and is not inferred from the component name
  F. Reuse gets the same suppression as preseed (the invariant is "the drafting
     skill was superseded", not "a preseed ran")
  G. The suppression leaves a durable Tier 4 audit record (§9.4)
  H. Preseed rejects a validation roll-up that over-states its claims — the
     derivation the drafted path performs and preseed bypasses (§12.2)

Fixtures are synthetic tmp_path repo roots; ``evaluate_gate`` is patched.  No
live repository artifacts are read or mutated.
"""

from __future__ import annotations

import importlib
import inspect
import json
import re
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
import yaml

from runner import dag_scheduler
from runner import deterministic_components as dc
from runner.agent_runtime import drafting_skills_superseded_by
from runner.claim_status import normalize_status, rollup_inconsistency
from runner.dag_scheduler import DAGScheduler, ManifestGraph
from runner.deterministic_components import (
    COMPONENT_REGISTRY,
    DRAFT_CONSUMING_COMPONENTS,
    invoke_component,
)
from runner.manifest_reader import MANIFEST_REL_PATH
from runner.phase8_preseed import (
    PRESEED_AUDIT_DIR,
    PRESEED_DIR,
    PRESEED_NODE_CONFIG,
    _validation_status_inconsistency,
    maybe_apply_phase8_preseed,
)
from runner.phase8_reuse import (
    REUSE_ELIGIBLE_NODES,
    ReuseDecision,
    validate_reuse_candidate,
)
from runner.run_context import RunContext
from runner.runtime_models import AgentResult
from runner.section_assembler import (
    PROPOSAL_SECTIONS_REL,
    SECTION_DRAFTS_ROOT_REL,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_NODE_ID = "n08a_excellence_drafting"
_SLUG = "excellence"
_EXIT_GATE = "gate_10a_excellence_completeness"

_EG_TARGET = "runner.dag_scheduler.evaluate_gate"
_RA_TARGET = "runner.dag_scheduler.run_agent"
_GATE_PASS = {"status": "pass"}

#: Prose that the operator preseeded.  It must reach the section artifact and
#: still be there after dispatch.
_PRESEED_PROSE = "PRESEEDED PROSE - operator authored, must survive dispatch."
#: Prose sitting in the stale drafts.  It must never reach the section artifact.
_DRAFT_PROSE = "STALE DRAFT PROSE - must not be recomposed over the preseed."

#: The suffixes the suppression *used* to match on.  Retained only so
#: ``TestDeclaredSetIsNotSuffixInferred`` can prove the behaviour no longer
#: depends on them.
_LEGACY_SUFFIXES = ("_section_assembler", "_assumption_applier")

#: The directory whose contents make a component draft-consuming.  The drift
#: detector looks for *this*, not for module names.
_DRAFTS_DIR_NAME = "section_drafts"


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _write_preseed(repo: Path, run_id: str = "msca-pf-real-01") -> None:
    """Write a valid n08a preseed artifact carrying :data:`_PRESEED_PROSE`."""
    config = PRESEED_NODE_CONFIG[_NODE_ID]
    _write_json(
        repo / PRESEED_DIR / config["source_file"],
        {
            "schema_id": config["schema_id"],
            "run_id": run_id,
            "criterion": "Excellence",
            "sub_sections": [
                {
                    "sub_section_id": "1.1",
                    "title": "Objectives",
                    "content": _PRESEED_PROSE,
                    "word_count": len(_PRESEED_PROSE.split()),
                }
            ],
            "validation_status": {
                "overall_status": "confirmed",
                "claim_statuses": [],
            },
            "traceability_footer": {
                "primary_sources": [
                    {"tier": 3, "source_path": "docs/tier3/objectives.json"}
                ],
                "no_unsupported_claims_declaration": True,
            },
        },
    )


def _write_canonical_pack_inputs(repo: Path) -> None:
    """Write the minimum Tier 3/4 sources the pack deriver needs to succeed.

    ``canonical_pack_deriver`` is the component preseed *keeps*, so the fixture
    has to let it run for real — otherwise its fault would mask the assembler's
    and :class:`_ComponentExecutingAgent` could not faithfully reproduce the
    agent runtime's fail-closed mapping.
    """
    _write_json(
        repo / "docs/tier3_project_instantiation/architecture_inputs"
        / "objectives.json",
        {
            "objectives": [
                {
                    "id": "O1",
                    "title": "Objective one",
                    "measurable_target": "One target",
                }
            ]
        },
    )
    _write_json(
        repo / "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design"
        / "wp_structure.json",
        {
            "work_packages": [
                {
                    "wp_id": "WP1",
                    "title": "Work package one",
                    "deliverables": [
                        {
                            "deliverable_id": "D1.1",
                            "title": "Deliverable one",
                            "due_month": 6,
                        }
                    ],
                }
            ]
        },
    )


def _write_section_drafts(repo: Path, spine_run_id: str) -> Path:
    """Write a complete, assemblable ``section_drafts/excellence/`` fixture.

    The drafts carry :data:`_DRAFT_PROSE`, so any recomposition is visible in
    the section artifact.  *spine_run_id* selects the hazard being modelled:
    the current run (assembler succeeds and clobbers) or a prior run
    (assembler fails closed on the stale-drafts guard).
    """
    drafts_dir = repo / SECTION_DRAFTS_ROOT_REL / _SLUG
    _write_json(
        drafts_dir / "section_spine.json",
        {
            "schema_id": f"orch.tier5.{_SLUG}_section.v1",
            "run_id": spine_run_id,
            "criterion": "Excellence",
            "overall_status": "confirmed",
            "no_unsupported_claims_declaration": True,
            "sub_section_order": ["1.1"],
        },
    )
    _write_json(
        drafts_dir / "1.1.draft.json",
        {
            "sub_section_id": "1.1",
            "title": "Objectives",
            "content": _DRAFT_PROSE,
            "claim_statuses": [],
            "source_refs": [
                {"tier": 3, "source_path": "docs/tier3/objectives.json"}
            ],
        },
    )
    return drafts_dir


def _build_fixture(
    repo: Path,
    *,
    spine_run_id: str,
    preseed_run_id: str = "msca-pf-real-01",
) -> None:
    """The whole hazard fixture: preseed + stale drafts + pack sources."""
    _write_preseed(repo, run_id=preseed_run_id)
    _write_section_drafts(repo, spine_run_id=spine_run_id)
    _write_canonical_pack_inputs(repo)


def _real_n08a_components() -> list[str]:
    """Read n08a's ``deterministic_components`` binding from the live manifest.

    Reading the real binding (rather than hardcoding one) means a rename or
    reordering of the bound components lands in this seam instead of silently
    making the suppression a no-op.
    """
    from runner.paths import find_repo_root

    manifest = yaml.safe_load(
        (find_repo_root() / MANIFEST_REL_PATH).read_text(encoding="utf-8")
    )
    for node in manifest["node_registry"]:
        if node["node_id"] == _NODE_ID:
            return list(node.get("deterministic_components") or [])
    raise AssertionError(f"{_NODE_ID} not found in the live manifest")


#: Matches ``from runner.x import …`` / ``import runner.x`` in module source —
#: including the lazy in-function imports the component adapters use.
_RUNNER_IMPORT_RE = re.compile(
    r"(?:from\s+(runner\.[\w.]+)\s+import|import\s+(runner\.[\w.]+))"
)


def _imported_runner_modules(source: str) -> set[str]:
    return {a or b for a, b in _RUNNER_IMPORT_RE.findall(source)}


def _reaches_section_drafts(entry_source: str) -> bool:
    """True iff ``section_drafts`` is reachable from *entry_source*'s imports.

    Walks the transitive closure of ``runner.*`` modules reachable from the
    source and reports whether any of them names the drafts directory.  This is
    a *reachability* test, not a name test: a component that reads
    ``section_drafts/`` through some third module — never mentioning the
    assembler or the applier — is still detected, which a grep of the adapter
    for ``"section_assembler"`` / ``"assumption_applier"`` could not do.
    """
    pending = list(_imported_runner_modules(entry_source))
    seen: set[str] = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        try:
            module_source = inspect.getsource(importlib.import_module(name))
        except (ImportError, OSError, TypeError):  # pragma: no cover — defensive
            continue
        if _DRAFTS_DIR_NAME in module_source:
            return True
        pending.extend(_imported_runner_modules(module_source))
    return False


def _draft_consuming_component_ids() -> set[str]:
    """Registry ids whose implementation can reach ``section_drafts/``."""
    return {
        component_id
        for component_id, fn in COMPONENT_REGISTRY.items()
        if _reaches_section_drafts(inspect.getsource(fn))
    }


def _section_path(repo: Path) -> Path:
    return repo / PROPOSAL_SECTIONS_REL / f"{_SLUG}_section.json"


def _section_prose(repo: Path) -> str:
    """Concatenate the section artifact's sub-section content."""
    data = json.loads(_section_path(repo).read_text(encoding="utf-8"))
    return " ".join(sub["content"] for sub in data["sub_sections"])


# ---------------------------------------------------------------------------
# Scheduler harness
# ---------------------------------------------------------------------------


def _make_scheduler(
    repo: Path,
    run_id: str,
    *,
    preseed: bool,
    components: list[str],
) -> DAGScheduler:
    """Build a DAGScheduler over a single-node synthetic manifest."""
    manifest_path = repo / "manifest.yaml"
    manifest_path.write_text(
        yaml.dump(
            {
                "name": "test",
                "version": "1.1",
                "node_registry": [
                    {
                        "node_id": _NODE_ID,
                        "exit_gate": _EXIT_GATE,
                        "terminal": True,
                    }
                ],
                "edge_registry": [],
            }
        ),
        encoding="utf-8",
    )
    graph = ManifestGraph.load(manifest_path)
    ctx = RunContext.initialize(repo, run_id)
    sched = DAGScheduler(graph, ctx, repo, preseed_phase8_sections=preseed)

    # The synthetic manifest carries no agent/skill/component fields; inject a
    # resolver that returns the *real* n08a binding so the suppression filter
    # sees what it would see in production.
    resolver = MagicMock()
    resolver.resolve_agent_id.return_value = "excellence_writer"
    resolver.resolve_sub_agent_id.return_value = None
    resolver.resolve_pre_gate_agent_id.return_value = None
    resolver.resolve_skill_ids.return_value = ["excellence-section-drafting"]
    resolver.resolve_phase_id.return_value = "phase_08a_excellence_drafting"
    resolver.resolve_deterministic_components.return_value = list(components)
    sched._DAGScheduler__node_resolver = resolver
    return sched


def _dispatch_reuse_forced(
    repo: Path,
    run_id: str,
    agent: "_ComponentExecutingAgent",
    *,
    components: list[str] | None = None,
) -> tuple[DAGScheduler, Any]:
    """Dispatch n08a with preseed off and reuse forced reusable=True.

    Returns ``(scheduler, result)`` so callers can inspect the persisted reuse
    decision on ``scheduler.ctx`` — needed to prove that a fail-closed skip
    binding writes no false "drafting skipped" audit (PRE-3).
    """
    sched = _make_scheduler(
        repo, run_id, preseed=False,
        components=components if components is not None else _real_n08a_components(),
    )
    decision = ReuseDecision(
        reusable=True,
        reason="reusable",
        artifact_path=REUSE_ELIGIBLE_NODES[_NODE_ID]["artifact_path"],
        source_run_id="msca-pf-real-01",
        input_fingerprint="f" * 64,
        gate_id=_EXIT_GATE,
    )
    with patch(_RA_TARGET, new=agent), patch(
        _EG_TARGET, return_value=_GATE_PASS
    ), patch(
        "runner.dag_scheduler.validate_reuse_candidate", return_value=decision,
    ), patch(
        "runner.dag_scheduler.compute_input_fingerprint", return_value="f" * 64,
    ), patch(
        "runner.dag_scheduler.write_reuse_metadata"
    ):
        result = sched._dispatch_node(_NODE_ID)
    return sched, result


class _ComponentExecutingAgent:
    """A ``run_agent`` stand-in that really runs the components it is handed.

    This is what makes the seam behavioural: the components go through the same
    :func:`invoke_component` substrate the agent runtime uses, so if the
    scheduler stops suppressing the assembler, the assembler genuinely rewrites
    the section artifact and the prose assertions fail.

    It also reproduces the agent runtime's fail-closed mapping (a component
    fault → ``status="failure"`` / ``AGENT_EXECUTION_ERROR`` /
    ``can_evaluate_exit_gate=False``, ``runner/agent_runtime.py`` Phase B), so
    the node-state assertions mean what they say.  Nothing else about the agent
    runtime is modelled — skills are not run.
    """

    def __init__(self) -> None:
        self.components_received: list[str] | None = None
        self.skip_skills: list[str] | None = None
        self.records: list[Any] = []

    def __call__(
        self,
        agent_id: str,
        node_id: str,
        run_id: str,
        repo_root: Path,
        **kwargs: Any,
    ) -> AgentResult:
        self.components_received = list(
            kwargs.get("deterministic_components") or []
        )
        self.skip_skills = kwargs.get("skip_skills")
        for component_id in self.components_received:
            # invoke_component never raises — a fault becomes a failure record.
            record = invoke_component(component_id, run_id, Path(repo_root))
            self.records.append(record)
            if record.status != "success":
                return AgentResult(
                    status="failure",
                    can_evaluate_exit_gate=False,
                    failure_reason=(
                        f"Deterministic component {component_id!r} failed: "
                        f"{record.failure_reason}"
                    ),
                    failure_category="AGENT_EXECUTION_ERROR",
                    invoked_components=self.records,
                )
        return AgentResult(status="success", can_evaluate_exit_gate=True)

    @property
    def invoked_ids(self) -> list[str]:
        return [r.component_id for r in self.records]


# ---------------------------------------------------------------------------
# A. Recomposition hazard — same-run drafts
# ---------------------------------------------------------------------------


class TestPreseededProseSurvivesSameRunDrafts:
    """Drafts fresh enough for the assembler to succeed must not be composed."""

    def test_prose_survives_and_assembler_never_runs(self, tmp_path: Path) -> None:
        run_id = "msca-pf-graph-01"
        _build_fixture(tmp_path, spine_run_id=run_id)

        agent = _ComponentExecutingAgent()
        sched = _make_scheduler(
            tmp_path, run_id, preseed=True, components=_real_n08a_components()
        )
        with patch(_RA_TARGET, new=agent), patch(
            _EG_TARGET, return_value=_GATE_PASS
        ):
            result = sched._dispatch_node(_NODE_ID)

        assert result.final_state == "released"
        assert _PRESEED_PROSE in _section_prose(tmp_path)
        assert _DRAFT_PROSE not in _section_prose(tmp_path)
        assert not [
            cid
            for cid in agent.invoked_ids
            if cid in DRAFT_CONSUMING_COMPONENTS
        ]

    def test_preseed_run_id_rewrite_is_not_undone(self, tmp_path: Path) -> None:
        """The section keeps the current run_id the preseed stamped on it."""
        run_id = "msca-pf-graph-01"
        _build_fixture(
            tmp_path, spine_run_id=run_id, preseed_run_id="msca-pf-real-01"
        )

        agent = _ComponentExecutingAgent()
        sched = _make_scheduler(
            tmp_path, run_id, preseed=True, components=_real_n08a_components()
        )
        with patch(_RA_TARGET, new=agent), patch(
            _EG_TARGET, return_value=_GATE_PASS
        ):
            sched._dispatch_node(_NODE_ID)

        written = json.loads(_section_path(tmp_path).read_text(encoding="utf-8"))
        assert written["run_id"] == run_id

    def test_drafting_skill_is_the_only_skipped_skill(self, tmp_path: Path) -> None:
        """Suppression targets components; the skill skip stays as designed."""
        run_id = "msca-pf-graph-01"
        _build_fixture(tmp_path, spine_run_id=run_id)

        agent = _ComponentExecutingAgent()
        sched = _make_scheduler(
            tmp_path, run_id, preseed=True, components=_real_n08a_components()
        )
        with patch(_RA_TARGET, new=agent), patch(
            _EG_TARGET, return_value=_GATE_PASS
        ):
            sched._dispatch_node(_NODE_ID)

        assert agent.skip_skills == [
            PRESEED_NODE_CONFIG[_NODE_ID]["skipped_skill"]
        ]


# ---------------------------------------------------------------------------
# B. Observed failure mode — foreign-run drafts (spine run_id mismatch)
# ---------------------------------------------------------------------------


class TestPreseededProseSurvivesForeignRunDrafts:
    """The mode observed on msca-pf-graph-01: drafts carried over from a run.

    Un-suppressed, the assembler fails closed on the stale-drafts guard and the
    node blocks at the agent body.  Suppressed, the node dispatches cleanly.
    """

    def test_node_released_and_prose_survives(self, tmp_path: Path) -> None:
        run_id = "msca-pf-graph-01"
        _build_fixture(tmp_path, spine_run_id="msca-pf-real-01")

        agent = _ComponentExecutingAgent()
        sched = _make_scheduler(
            tmp_path, run_id, preseed=True, components=_real_n08a_components()
        )
        with patch(_RA_TARGET, new=agent), patch(
            _EG_TARGET, return_value=_GATE_PASS
        ):
            result = sched._dispatch_node(_NODE_ID)

        assert result.final_state == "released"
        assert result.failure_origin is None
        assert _PRESEED_PROSE in _section_prose(tmp_path)
        assert not [
            cid
            for cid in agent.invoked_ids
            if cid in DRAFT_CONSUMING_COMPONENTS
        ]


# ---------------------------------------------------------------------------
# C. Suppression is scoped
# ---------------------------------------------------------------------------


class TestSuppressionIsScoped:
    """Only the draft-consuming components are dropped, and only in preseed mode."""

    def test_canonical_pack_deriver_is_retained(self, tmp_path: Path) -> None:
        run_id = "msca-pf-graph-01"
        _build_fixture(tmp_path, spine_run_id=run_id)

        agent = _ComponentExecutingAgent()
        sched = _make_scheduler(
            tmp_path, run_id, preseed=True, components=_real_n08a_components()
        )
        with patch(_RA_TARGET, new=agent), patch(
            _EG_TARGET, return_value=_GATE_PASS
        ):
            sched._dispatch_node(_NODE_ID)

        assert "canonical_pack_deriver" in agent.components_received

    def test_binding_is_unfiltered_when_preseed_mode_is_off(
        self, tmp_path: Path
    ) -> None:
        """Guard against over-suppression: no preseed, no filtering."""
        run_id = "msca-pf-graph-01"
        components = _real_n08a_components()
        # Preseed artifact present, but the flag is off — it must be ignored.
        _build_fixture(tmp_path, spine_run_id=run_id)

        agent = _ComponentExecutingAgent()
        sched = _make_scheduler(
            tmp_path, run_id, preseed=False, components=components
        )
        with patch(_RA_TARGET, new=agent), patch(
            _EG_TARGET, return_value=_GATE_PASS
        ):
            sched._dispatch_node(_NODE_ID)

        assert agent.components_received == components

    def test_suppression_drops_exactly_the_draft_consumers(
        self, tmp_path: Path
    ) -> None:
        run_id = "msca-pf-graph-01"
        components = _real_n08a_components()
        _build_fixture(tmp_path, spine_run_id=run_id)

        agent = _ComponentExecutingAgent()
        sched = _make_scheduler(
            tmp_path, run_id, preseed=True, components=components
        )
        with patch(_RA_TARGET, new=agent), patch(
            _EG_TARGET, return_value=_GATE_PASS
        ):
            sched._dispatch_node(_NODE_ID)

        expected = [
            c for c in components if c not in DRAFT_CONSUMING_COMPONENTS
        ]
        assert agent.components_received == expected
        # The fixture must actually exercise the filter, or the assertion above
        # is vacuous.
        assert len(expected) < len(components)


# ---------------------------------------------------------------------------
# D. Negative control — the fixture is red-capable
# ---------------------------------------------------------------------------


class TestFixtureIsRedCapable:
    """Prove the fixture punishes an un-suppressed assembler.

    Without these, every assertion above could pass over a fixture where the
    assembler was harmless.
    """

    def test_assembler_clobbers_preseed_when_drafts_are_same_run(
        self, tmp_path: Path
    ) -> None:
        run_id = "msca-pf-graph-01"
        _build_fixture(tmp_path, spine_run_id=run_id)
        # Stand in for the scheduler's preseed copy step.
        from runner.phase8_preseed import maybe_apply_phase8_preseed

        assert maybe_apply_phase8_preseed(tmp_path, run_id, _NODE_ID).applied
        assert _PRESEED_PROSE in _section_prose(tmp_path)

        record = invoke_component(
            f"{_SLUG}_section_assembler", run_id, tmp_path
        )

        assert record.status == "success"
        assert _DRAFT_PROSE in _section_prose(tmp_path)
        assert _PRESEED_PROSE not in _section_prose(tmp_path)

    def test_assembler_fails_closed_when_drafts_are_foreign_run(
        self, tmp_path: Path
    ) -> None:
        run_id = "msca-pf-graph-01"
        _build_fixture(tmp_path, spine_run_id="msca-pf-real-01")

        record = invoke_component(
            f"{_SLUG}_section_assembler", run_id, tmp_path
        )

        assert record.status == "failure"
        assert "run_id" in (record.failure_reason or "")


# ---------------------------------------------------------------------------
# E. The declared draft-consuming set is a checked invariant
# ---------------------------------------------------------------------------


class TestDeclaredSetInvariant:
    """``DRAFT_CONSUMING_COMPONENTS`` must stay in step with the registry.

    The suppression used to be a name-suffix match — the only name-inferred id
    semantics in ``runner/``, where every other component-id path fails closed
    on an unknown id.  It is now an explicit declaration, but a declaration can
    still drift: a new component that reads ``section_drafts/`` and is not added
    to the set would silently escape suppression.  These tests derive the
    draft-consuming set from the adapters' own source and hold the declaration
    to it, in both directions.
    """

    def test_the_detector_finds_the_known_consumers(self) -> None:
        """Detector self-check: it must find today's six, or it detects nothing.

        A subset assertion, not an equality on the count — a legitimately added
        seventh consumer must fail the *drift* test below with its own name in
        the message, not this one with an arithmetic mismatch.
        """
        assert _draft_consuming_component_ids() >= {
            "excellence_section_assembler",
            "impact_section_assembler",
            "implementation_section_assembler",
            "excellence_assumption_applier",
            "impact_assumption_applier",
            "implementation_assumption_applier",
        }

    def test_every_draft_consuming_component_is_declared(self) -> None:
        draft_consumers = _draft_consuming_component_ids()
        undeclared = sorted(draft_consumers - DRAFT_CONSUMING_COMPONENTS)
        assert undeclared == [], (
            "these components read section_drafts/ but are absent from "
            f"DRAFT_CONSUMING_COMPONENTS, so they would survive suppression in "
            f"dag_scheduler._dispatch_node(): {undeclared}"
        )

    def test_no_non_draft_component_is_declared(self) -> None:
        """The declaration must not drop components that never touch drafts."""
        draft_consumers = _draft_consuming_component_ids()
        over_declared = sorted(DRAFT_CONSUMING_COMPONENTS - draft_consumers)
        assert over_declared == []

    def test_declared_set_is_a_subset_of_the_registry(self) -> None:
        """Fail-closed pairing: a declared id must be a real component."""
        assert DRAFT_CONSUMING_COMPONENTS <= set(COMPONENT_REGISTRY)

    def test_section_drafts_root_is_the_shared_input(self) -> None:
        """Pin the directory the suppression exists to protect against."""
        assert SECTION_DRAFTS_ROOT_REL.endswith("section_drafts")
        assert dc.COMPONENT_REGISTRY  # registry is populated

    def test_a_consumer_reaching_drafts_indirectly_is_detected(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The addition direction: a new consumer via some *other* module.

        The import-time guard in ``deterministic_components`` only catches the
        rename direction (a declared id that left the registry).  The addition
        direction — a newly registered component that reads ``section_drafts/``
        and was never added to ``DRAFT_CONSUMING_COMPONENTS`` — rests entirely on
        this detector, so it must not be satisfiable by naming: a component that
        reaches the drafts through a module that is neither the assembler nor the
        applier has to be caught too.
        """

        def _run_sneaky_composer(run_id: str, repo_root: Path) -> list[Path]:
            from runner.decomposed_drafting import SECTION_DRAFTS_ROOT_REL as _r

            return [Path(_r)]

        # Reaches the drafts, but names neither draft-consuming module — the
        # old substring detector would have waved it through.
        source = inspect.getsource(_run_sneaky_composer)
        assert not any(m in source for m in _LEGACY_SUFFIXES)
        assert _DRAFTS_DIR_NAME not in source

        monkeypatch.setitem(
            COMPONENT_REGISTRY, "sneaky_composer", _run_sneaky_composer
        )

        detected = _draft_consuming_component_ids()

        assert "sneaky_composer" in detected
        # …and that is exactly what makes the declaration test go red for it.
        assert "sneaky_composer" not in DRAFT_CONSUMING_COMPONENTS
        with pytest.raises(AssertionError):
            self.test_every_draft_consuming_component_is_declared()


class TestDeclaredSetIsNotSuffixInferred:
    """The suppression must survive a rename — it is not a suffix heuristic.

    Regression for the "brittle-name-suffix-match" defect: a draft-consuming
    component whose id does *not* end in ``_section_assembler`` /
    ``_assumption_applier`` must still be suppressed, and a harmless component
    that *does* carry such a suffix must not be dropped for its name alone.
    """

    def test_a_renamed_draft_consumer_is_still_suppressed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        renamed = "excellence_prose_composer"  # no legacy suffix
        assert not renamed.endswith(_LEGACY_SUFFIXES)
        monkeypatch.setattr(
            dc,
            "DRAFT_CONSUMING_COMPONENTS",
            frozenset(DRAFT_CONSUMING_COMPONENTS | {renamed}),
        )

        kept, suppressed = dc.partition_draft_consuming(
            ["canonical_pack_deriver", renamed]
        )

        assert suppressed == [renamed]
        assert kept == ["canonical_pack_deriver"]

    def test_a_suffix_bearing_non_consumer_is_not_dropped(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Name alone must not condemn a component that never reads drafts."""
        innocent = "budget_assumption_applier"  # carries the legacy suffix
        assert innocent.endswith(_LEGACY_SUFFIXES)
        assert innocent not in DRAFT_CONSUMING_COMPONENTS

        kept, suppressed = dc.partition_draft_consuming(
            ["canonical_pack_deriver", innocent]
        )

        assert suppressed == []
        assert kept == ["canonical_pack_deriver", innocent]

    def test_an_unknown_id_is_kept_so_it_fails_closed_downstream(self) -> None:
        """Silently dropping an unknown id would turn a hard error into a no-op."""
        kept, suppressed = dc.partition_draft_consuming(["totally_unknown"])

        assert kept == ["totally_unknown"]
        assert suppressed == []
        # And the substrate is what fails it closed.
        record = invoke_component("totally_unknown", "run-1", Path("."))
        assert record.status == "failure"


# ---------------------------------------------------------------------------
# F. Reuse mode is the same hazard and must get the same suppression
# ---------------------------------------------------------------------------


class TestReuseModeSuppression:
    """The invariant is "the drafting skill was superseded", not "preseed ran".

    Regression for the "correctness-and-missed-code-paths" defect: reuse skips
    the same drafting skill over the same three nodes and leaves the same
    authoritative section artifact on disk, but the original fix keyed the
    suppression on ``_preseed_skip_skills is not None`` — so the reuse path kept
    the assembler bound and died in ``section_assembler`` on the identical
    stale-spine ``run_id`` mismatch the fix exists to cure.
    """

    def _dispatch_in_reuse_mode(
        self, repo: Path, run_id: str, agent: "_ComponentExecutingAgent"
    ) -> Any:
        """Dispatch n08a with preseed off and the reuse decision forced on."""
        sched = _make_scheduler(
            repo, run_id, preseed=False, components=_real_n08a_components()
        )
        decision = ReuseDecision(
            reusable=True,
            reason="reusable",
            artifact_path=REUSE_ELIGIBLE_NODES[_NODE_ID]["artifact_path"],
            source_run_id="msca-pf-real-01",
            input_fingerprint="f" * 64,
            gate_id=_EXIT_GATE,
        )
        with patch(_RA_TARGET, new=agent), patch(
            _EG_TARGET, return_value=_GATE_PASS
        ), patch(
            "runner.dag_scheduler.validate_reuse_candidate",
            return_value=decision,
        ), patch(
            "runner.dag_scheduler.compute_input_fingerprint",
            return_value="f" * 64,
        ), patch(
            "runner.dag_scheduler.write_reuse_metadata"
        ):
            return sched._dispatch_node(_NODE_ID)

    def test_reused_section_survives_foreign_run_drafts(
        self, tmp_path: Path
    ) -> None:
        """The observed failure, reached through the reuse path instead."""
        run_id = "msca-pf-graph-01"
        _build_fixture(tmp_path, spine_run_id="msca-pf-real-01")
        # Reuse carries a prior-run section artifact forward; model it on disk.
        _write_json(
            _section_path(tmp_path),
            {
                "schema_id": f"orch.tier5.{_SLUG}_section.v1",
                "run_id": "msca-pf-real-01",
                "criterion": "Excellence",
                "sub_sections": [
                    {
                        "sub_section_id": "1.1",
                        "title": "Objectives",
                        "content": _PRESEED_PROSE,
                        "word_count": len(_PRESEED_PROSE.split()),
                    }
                ],
                "validation_status": {
                    "overall_status": "confirmed",
                    "claim_statuses": [],
                },
                "traceability_footer": {
                    "primary_sources": [
                        {"tier": 3, "source_path": "docs/tier3/objectives.json"}
                    ],
                    "no_unsupported_claims_declaration": True,
                },
            },
        )

        agent = _ComponentExecutingAgent()
        result = self._dispatch_in_reuse_mode(tmp_path, run_id, agent)

        # Un-suppressed, the assembler raises on the stale spine and the node
        # blocks at the agent body (see TestFixtureIsRedCapable).
        assert result.final_state == "released"
        assert result.failure_origin is None
        assert _PRESEED_PROSE in _section_prose(tmp_path)
        assert _DRAFT_PROSE not in _section_prose(tmp_path)

    def test_reuse_suppresses_draft_consumers_and_keeps_the_pack(
        self, tmp_path: Path
    ) -> None:
        run_id = "msca-pf-graph-01"
        _build_fixture(tmp_path, spine_run_id=run_id)

        agent = _ComponentExecutingAgent()
        self._dispatch_in_reuse_mode(tmp_path, run_id, agent)

        assert "canonical_pack_deriver" in agent.components_received
        assert not [
            cid
            for cid in agent.components_received
            if cid in DRAFT_CONSUMING_COMPONENTS
        ]


# ---------------------------------------------------------------------------
# G. The suppression leaves a durable audit record
# ---------------------------------------------------------------------------


class TestSuppressionIsAudited:
    """A manifest-bound component that did not run is a §9.4 durable decision."""

    def _audit_path(self, repo: Path) -> Path:
        return (
            repo / PRESEED_AUDIT_DIR / f"component_suppression_{_NODE_ID}.json"
        )

    def test_preseed_suppression_writes_an_audit_record(
        self, tmp_path: Path
    ) -> None:
        run_id = "msca-pf-graph-01"
        _build_fixture(tmp_path, spine_run_id=run_id)

        agent = _ComponentExecutingAgent()
        sched = _make_scheduler(
            tmp_path, run_id, preseed=True, components=_real_n08a_components()
        )
        with patch(_RA_TARGET, new=agent), patch(
            _EG_TARGET, return_value=_GATE_PASS
        ):
            sched._dispatch_node(_NODE_ID)

        audit = json.loads(
            self._audit_path(tmp_path).read_text(encoding="utf-8")
        )
        assert audit["mode"] == "preseed"
        assert audit["node_id"] == _NODE_ID
        assert audit["run_id"] == run_id
        assert sorted(audit["suppressed_components"]) == sorted(
            c
            for c in _real_n08a_components()
            if c in DRAFT_CONSUMING_COMPONENTS
        )
        assert "canonical_pack_deriver" in audit["retained_components"]

    def test_no_audit_record_when_nothing_is_suppressed(
        self, tmp_path: Path
    ) -> None:
        """No suppression, no record — the audit must mean something."""
        run_id = "msca-pf-graph-01"
        _build_fixture(tmp_path, spine_run_id=run_id)

        agent = _ComponentExecutingAgent()
        sched = _make_scheduler(
            tmp_path, run_id, preseed=False, components=_real_n08a_components()
        )
        with patch(_RA_TARGET, new=agent), patch(
            _EG_TARGET, return_value=_GATE_PASS
        ):
            sched._dispatch_node(_NODE_ID)

        assert not self._audit_path(tmp_path).exists()


# ---------------------------------------------------------------------------
# H. Preseed must not import an over-stated validation roll-up
# ---------------------------------------------------------------------------


class TestPreseedRollUpConsistency:
    """Preseed bypasses the derivation pipeline, so it must check the roll-up.

    Regression for the "canonical_pack-vs-unapplied-assumptions" defect.  The
    drafted path derives ``validation_status.overall_status`` from the claims
    (drafter, then assumption-applier, §12.2 worst-wins).  A preseeded section
    skips all of it, and the gates cannot catch the gap:
    ``no_unresolved_material_claims`` reads only the roll-up and W1
    (``assumed_claims_are_operator_declared``) inspects only ``assumed`` claims —
    so an ``unresolved`` claim under a ``confirmed`` roll-up is a false green.

    Note the fix is *here*, not "stop suppressing the applier": the applier only
    ever reads and rewrites ``section_drafts/``, never the Tier 5 section
    artifact, so running it would not repair a preseeded roll-up — and the
    assembler that would carry its result is the very component that must not
    run.  Preseed has to enforce the invariant itself.
    """

    def _preseed_with(
        self, repo: Path, *, overall: str, claims: list[dict[str, Any]]
    ) -> None:
        config = PRESEED_NODE_CONFIG[_NODE_ID]
        _write_json(
            repo / PRESEED_DIR / config["source_file"],
            {
                "schema_id": config["schema_id"],
                "run_id": "msca-pf-real-01",
                "criterion": "Excellence",
                "sub_sections": [
                    {
                        "sub_section_id": "1.1",
                        "title": "Objectives",
                        "content": _PRESEED_PROSE,
                        "word_count": 5,
                    }
                ],
                "validation_status": {
                    "overall_status": overall,
                    "claim_statuses": claims,
                },
                "traceability_footer": {
                    "primary_sources": [
                        {"tier": 3, "source_path": "docs/tier3/objectives.json"}
                    ],
                    "no_unsupported_claims_declaration": True,
                },
            },
        )

    def test_unresolved_claim_under_confirmed_rollup_is_rejected(
        self, tmp_path: Path
    ) -> None:
        self._preseed_with(
            tmp_path,
            overall="confirmed",
            claims=[{"claim_id": "C1", "status": "unresolved"}],
        )

        result = maybe_apply_phase8_preseed(
            tmp_path, "msca-pf-graph-01", _NODE_ID
        )

        assert result.error is True
        assert result.applied is False
        assert result.failure_category == "MALFORMED_ARTIFACT"
        assert "overstated" in (result.reason or "")
        # Fail-closed: nothing may reach the canonical Tier 5 path.
        assert not _section_path(tmp_path).exists()

    def test_assumed_claim_under_confirmed_rollup_is_rejected(
        self, tmp_path: Path
    ) -> None:
        self._preseed_with(
            tmp_path,
            overall="confirmed",
            claims=[{"claim_id": "C1", "status": "assumed"}],
        )

        result = maybe_apply_phase8_preseed(
            tmp_path, "msca-pf-graph-01", _NODE_ID
        )

        assert result.error is True

    def test_the_node_blocks_on_an_overstated_rollup(
        self, tmp_path: Path
    ) -> None:
        """End-to-end: the scheduler turns the rejection into a blocked node."""
        run_id = "msca-pf-graph-01"
        self._preseed_with(
            tmp_path,
            overall="confirmed",
            claims=[{"claim_id": "C1", "status": "unresolved"}],
        )
        _write_section_drafts(tmp_path, spine_run_id=run_id)
        _write_canonical_pack_inputs(tmp_path)

        agent = _ComponentExecutingAgent()
        sched = _make_scheduler(
            tmp_path, run_id, preseed=True, components=_real_n08a_components()
        )
        with patch(_RA_TARGET, new=agent), patch(
            _EG_TARGET, return_value=_GATE_PASS
        ):
            result = sched._dispatch_node(_NODE_ID)

        assert result.final_state == "blocked_at_exit"
        assert result.failure_origin == "preseed"
        assert result.exit_gate_evaluated is False
        # The agent body must never have been reached.
        assert agent.components_received is None

    def test_a_consistent_rollup_still_applies(self, tmp_path: Path) -> None:
        """The check must not block honest preseeds (over-suppression guard)."""
        self._preseed_with(
            tmp_path,
            overall="unresolved",
            claims=[{"claim_id": "C1", "status": "unresolved"}],
        )

        result = maybe_apply_phase8_preseed(
            tmp_path, "msca-pf-graph-01", _NODE_ID
        )

        assert result.applied is True
        assert result.error is False

    def test_a_conservative_rollup_is_allowed(self, tmp_path: Path) -> None:
        """Under-claiming is honest (§15); only over-claiming is a defect."""
        self._preseed_with(
            tmp_path,
            overall="assumed",
            claims=[{"claim_id": "C1", "status": "confirmed"}],
        )

        result = maybe_apply_phase8_preseed(
            tmp_path, "msca-pf-graph-01", _NODE_ID
        )

        assert result.applied is True
        assert result.error is False


# ---------------------------------------------------------------------------
# I. Reuse must enforce the same roll-up invariant as preseed
# ---------------------------------------------------------------------------


class TestReuseRollUpConsistency:
    """Reuse admits a finished artifact too, so it needs the same §12.2 check.

    Regression for the "canonical_pack-vs-unapplied-assumptions" defect.  The
    roll-up guard was wired into preseed only, while suppression was extended to
    cover reuse — so the reuse path carried forward a section whose roll-up says
    ``confirmed`` over an ``unresolved`` claim, suppressed the components that
    would have re-derived it, and let the retained ``canonical_pack_deriver``
    republish the declaration under the current run_id.  ``gate_10a`` reads only
    the roll-up, so the node goes green on an unresolved claim.

    ``validate_reuse_candidate`` step 4 does not catch it: it rejects only an
    *overall* ``unresolved``.
    """

    def _artifact(
        self, repo: Path, *, overall: str, claims: list[dict[str, Any]]
    ) -> None:
        _write_json(
            _section_path(repo),
            {
                "schema_id": REUSE_ELIGIBLE_NODES[_NODE_ID]["schema_id"],
                "run_id": "msca-pf-real-01",
                "criterion": "Excellence",
                "sub_sections": [
                    {
                        "sub_section_id": "1.1",
                        "title": "Objectives",
                        "content": _PRESEED_PROSE,
                        "word_count": 5,
                    }
                ],
                "validation_status": {
                    "overall_status": overall,
                    "claim_statuses": claims,
                },
                "traceability_footer": {
                    "primary_sources": [
                        {"tier": 3, "source_path": "docs/tier3/objectives.json"}
                    ],
                    "no_unsupported_claims_declaration": True,
                },
            },
        )

    def test_unresolved_claim_under_confirmed_rollup_is_not_reusable(
        self, tmp_path: Path
    ) -> None:
        self._artifact(
            tmp_path,
            overall="confirmed",
            claims=[{"claim_id": "C1", "status": "unresolved"}],
        )

        decision = validate_reuse_candidate(
            _NODE_ID, tmp_path, current_fingerprint="f" * 64
        )

        assert decision.reusable is False
        assert "overstated" in decision.reason

    def test_assumed_claim_under_confirmed_rollup_is_not_reusable(
        self, tmp_path: Path
    ) -> None:
        self._artifact(
            tmp_path,
            overall="confirmed",
            claims=[{"claim_id": "C1", "status": "assumed"}],
        )

        decision = validate_reuse_candidate(
            _NODE_ID, tmp_path, current_fingerprint="f" * 64
        )

        assert decision.reusable is False
        assert "overstated" in decision.reason

    def test_a_conservative_rollup_is_not_rejected_for_the_rollup(
        self, tmp_path: Path
    ) -> None:
        """Over-suppression guard: under-claiming must fail later, if at all."""
        self._artifact(
            tmp_path,
            overall="assumed",
            claims=[{"claim_id": "C1", "status": "confirmed"}],
        )

        decision = validate_reuse_candidate(
            _NODE_ID, tmp_path, current_fingerprint="f" * 64
        )

        # Still not reusable in this bare fixture (no gate result / metadata),
        # but never for the roll-up.
        assert "overstated" not in decision.reason

    def test_preseed_and_reuse_share_one_implementation(self) -> None:
        """The two paths must not be able to drift apart again."""
        overstated = {
            "validation_status": {
                "overall_status": "confirmed",
                "claim_statuses": [{"claim_id": "C1", "status": "unresolved"}],
            }
        }

        assert rollup_inconsistency(overstated, prefix="preseed") is not None
        assert rollup_inconsistency(overstated, prefix="reuse") is not None
        assert _validation_status_inconsistency(overstated) == (
            rollup_inconsistency(overstated, prefix="preseed")
        )


# ---------------------------------------------------------------------------
# I2. normalize_status — the single §12.2 case-normalisation point (PRE-1)
# ---------------------------------------------------------------------------


class TestNormalizeStatus:
    """``normalize_status`` maps any casing of a §12.2 status to lowercase.

    The status-case gate bypass (PRE-1) existed because the roll-up derivation
    lowercased while the gate/reuse admission checks compared exactly.  Both
    sides now route through this one helper, so it is the contract that closes
    the bypass: title-case matches, unknown values never do.
    """

    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("unresolved", "unresolved"),
            ("Unresolved", "unresolved"),
            ("UNRESOLVED", "unresolved"),
            ("Assumed", "assumed"),
            ("Confirmed", "confirmed"),
            ("Inferred", "inferred"),
        ],
    )
    def test_known_statuses_normalise_to_lowercase(
        self, raw: str, expected: str
    ) -> None:
        assert normalize_status(raw) == expected

    @pytest.mark.parametrize("raw", ["", "garbage", "passed", None, 3, [], {}])
    def test_unknown_values_return_none(self, raw: object) -> None:
        assert normalize_status(raw) is None


# ---------------------------------------------------------------------------
# J. Skip binding is resolved against the manifest and fails closed on drift
# ---------------------------------------------------------------------------


class TestSkipBindingFailsClosedOnDrift:
    """A skip id that matches no manifest skill hard-blocks the node (PRE-2/PRE-3).

    The preseed/reuse drafting-skill skip used to be a hardcoded name-string
    (``PRESEED_NODE_CONFIG`` / ``REUSE_SKIP_SKILLS``) checked against nothing.
    An unmatched id was a silent no-op: the drafter ran and overwrote the
    authoritative section while the audit falsely claimed a skip.  ``b5eb816``
    mitigated it by *carrying the manifest-derived supersession into the skip
    set* — an "add, never replace" workaround.  Ticket 3 replaces that with the
    real fix: the skip id is resolved against the node's manifest ``skill_ids``
    and a drift is a hard failure, so the drafter never gets the chance to run.

    These tests force the hardcoded skip id apart from the manifest binding and
    assert the node blocks fail-closed, writing neither an overwrite nor a false
    audit.
    """

    #: The drafting skill the *manifest binding* supersedes for n08a — the value
    #: the injected resolver returns as the node's only ``skill_id``.
    _BOUND_DRAFTING_SKILL = "excellence-section-drafting"
    #: A drifted hardcoded id — matches no manifest-resolved skill.
    _DRIFTED_SKILL = "excellence-section-drafting-v2"

    def test_the_bound_assembler_names_the_drafting_skill(self) -> None:
        """Pin the manifest-derived supersession helper (still used in-runtime)."""
        assert drafting_skills_superseded_by(_real_n08a_components()) == {
            self._BOUND_DRAFTING_SKILL
        }
        assert drafting_skills_superseded_by([]) == frozenset()
        assert drafting_skills_superseded_by(None) == frozenset()

    def test_preseed_drift_hard_blocks_before_applying(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A drifted preseed skip id blocks the node — no artifact, no drafter."""
        run_id = "msca-pf-graph-01"
        _build_fixture(tmp_path, spine_run_id=run_id)
        # Drift: the preseed config no longer names a skill the manifest binds.
        monkeypatch.setitem(
            PRESEED_NODE_CONFIG[_NODE_ID], "skipped_skill", self._DRIFTED_SKILL
        )

        agent = _ComponentExecutingAgent()
        sched = _make_scheduler(
            tmp_path, run_id, preseed=True, components=_real_n08a_components()
        )
        with patch(_RA_TARGET, new=agent), patch(
            _EG_TARGET, return_value=_GATE_PASS
        ):
            result = sched._dispatch_node(_NODE_ID)

        assert result.final_state == "blocked_at_exit"
        assert result.failure_origin == "preseed"
        assert result.exit_gate_evaluated is False
        assert result.failure_category == "CONSTRAINT_VIOLATION"
        assert self._DRIFTED_SKILL in (result.failure_reason or "")
        # Validated before apply: no artifact reached the canonical path and the
        # agent body (the drafter) was never dispatched.
        assert not _section_path(tmp_path).exists()
        assert agent.components_received is None

    def test_reuse_drift_hard_blocks_and_records_no_false_skip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A drifted reuse skip id blocks; no ``drafting_skipped`` decision persists."""
        run_id = "msca-pf-graph-01"
        _build_fixture(tmp_path, spine_run_id=run_id)
        monkeypatch.setitem(
            dag_scheduler.REUSE_SKIP_SKILLS, _NODE_ID, self._DRIFTED_SKILL
        )

        agent = _ComponentExecutingAgent()
        sched, result = _dispatch_reuse_forced(tmp_path, run_id, agent)

        assert result.final_state == "blocked_at_exit"
        assert result.failure_origin == "reuse"
        assert result.failure_category == "CONSTRAINT_VIOLATION"
        assert agent.components_received is None
        # PRE-3: the Tier-4 reuse decision must not claim a skip that never
        # happened — nothing "reused" is persisted, only the refusal.
        assert sched.ctx.get_reuse_decision(_NODE_ID) is None
        assert sched._reuse_decisions[_NODE_ID]["status"] == "not_reused"

    def test_eligible_but_unbound_node_records_no_false_skip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """PRE-3 core: eligible but absent from the skip binding → no false audit.

        The empty-skip branch of ``validate_skip_binding`` fires: the node is
        reuse-eligible but has no drafting skill to suppress, so it blocks
        instead of recording ``drafting_skipped_audit_executed`` over an
        unsuppressed drafter.
        """
        run_id = "msca-pf-graph-01"
        _build_fixture(tmp_path, spine_run_id=run_id)
        # Eligibility/skip drift: the node is reuse-eligible but bound to no skip.
        monkeypatch.delitem(dag_scheduler.REUSE_SKIP_SKILLS, _NODE_ID)

        agent = _ComponentExecutingAgent()
        sched, result = _dispatch_reuse_forced(tmp_path, run_id, agent)

        assert result.final_state == "blocked_at_exit"
        assert result.failure_origin == "reuse"
        assert "empty" in (result.failure_reason or "")
        assert agent.components_received is None
        assert sched.ctx.get_reuse_decision(_NODE_ID) is None
        assert sched._reuse_decisions[_NODE_ID]["status"] == "not_reused"

    def test_normal_agree_case_dispatches_unchanged(
        self, tmp_path: Path
    ) -> None:
        """The in-agreement case is untouched: skip binding matches, node runs."""
        run_id = "msca-pf-graph-01"
        _build_fixture(tmp_path, spine_run_id=run_id)

        agent = _ComponentExecutingAgent()
        sched = _make_scheduler(
            tmp_path, run_id, preseed=True, components=_real_n08a_components()
        )
        with patch(_RA_TARGET, new=agent), patch(
            _EG_TARGET, return_value=_GATE_PASS
        ):
            result = sched._dispatch_node(_NODE_ID)

        assert result.final_state == "released"
        assert agent.skip_skills == [self._BOUND_DRAFTING_SKILL]
        assert _PRESEED_PROSE in _section_prose(tmp_path)

    def test_no_supersession_is_invented_without_a_binding(
        self, tmp_path: Path
    ) -> None:
        """The single-source skip id is the only skip — nothing is invented."""
        run_id = "msca-pf-graph-01"
        _build_fixture(tmp_path, spine_run_id=run_id)

        agent = _ComponentExecutingAgent()
        sched = _make_scheduler(
            tmp_path, run_id, preseed=True, components=["canonical_pack_deriver"]
        )
        with patch(_RA_TARGET, new=agent), patch(
            _EG_TARGET, return_value=_GATE_PASS
        ):
            sched._dispatch_node(_NODE_ID)

        assert agent.skip_skills == [
            PRESEED_NODE_CONFIG[_NODE_ID]["skipped_skill"]
        ]

    def test_the_skip_set_is_audited(self, tmp_path: Path) -> None:
        """§9.4: the skills that did not run are part of the durable record."""
        run_id = "msca-pf-graph-01"
        _build_fixture(tmp_path, spine_run_id=run_id)

        agent = _ComponentExecutingAgent()
        sched = _make_scheduler(
            tmp_path, run_id, preseed=True, components=_real_n08a_components()
        )
        with patch(_RA_TARGET, new=agent), patch(
            _EG_TARGET, return_value=_GATE_PASS
        ):
            sched._dispatch_node(_NODE_ID)

        audit = json.loads(
            (
                tmp_path
                / PRESEED_AUDIT_DIR
                / f"component_suppression_{_NODE_ID}.json"
            ).read_text(encoding="utf-8")
        )
        assert audit["skipped_skills"] == [self._BOUND_DRAFTING_SKILL]
