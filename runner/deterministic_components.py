"""
Deterministic-component substrate — manifest-bound, Claude-free node-body passes.

A *deterministic component* (CLAUDE.md §17.5.3, ratified as C2) is a pure-Python
pass that the agent runtime may invoke within a node body.  It reads declared
input artifacts and writes canonical artifacts via an atomic write, performs no
domain reasoning and no inference, and is closed by a determinism guarantee
(byte-equal replay or pure lookup).  Deterministic components are **not skills**
(a skill is defined by Claude invocation, §17.5.2): they are analogous to the
Step-0 Call Slicer (``runner/call_slicer.py``) but node-body-scoped rather than
scheduler-scoped.

This module is the generic binding substrate (C3 / §16.5).  A node spec declares
one or more component ids via the ``deterministic_components`` manifest key; the
node resolver returns them; the agent runtime resolves each id here and invokes
it, recording the result in ``AgentResult.invoked_components``.  The one existing
hardcoded deterministic pass — the Phase-4 dependency normalizer — is registered
here and runs through this same generic path.

Constitutional constraints (§17.5.3, §17.6):
    * Components perform no domain reasoning and never invoke Claude.
    * Components cannot evaluate gates (gate evaluation is the scheduler's
      exclusive responsibility, §17.6.2).
    * Components are not invoked by skills, and do not invoke skills
      (§17.6.4).
    * Python owns all writes; each component is closed by a determinism
      guarantee.
    * A component fault is surfaced by the agent runtime as
      ``failure_origin="agent_body"``,
      ``failure_category="AGENT_EXECUTION_ERROR"``,
      ``can_evaluate_exit_gate=False``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Iterable, Union

from runner.runtime_models import ComponentInvocationRecord

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Component contract
# ---------------------------------------------------------------------------
#
# A deterministic component is a callable ``(run_id, repo_root) -> written``
# where *written* is an iterable of the artifact paths it wrote (absolute or
# repo-relative ``Path`` / ``str``).  It writes canonical artifacts as a side
# effect and raises on any failure (missing input, malformed artifact, etc.).
# ``invoke_component`` converts a raised exception into a failure record — it
# never propagates.

_PathLike = Union[str, Path]
ComponentCallable = Callable[[str, Path], Iterable[_PathLike]]


# ---------------------------------------------------------------------------
# Registered components
# ---------------------------------------------------------------------------


def _run_dependency_normalizer(run_id: str, repo_root: Path) -> list[Path]:
    """Adapter for the Phase-4 dependency normalizer (byte-identical output).

    Wraps ``runner.dependency_normalizer.normalize_dependencies`` so it
    conforms to the :data:`ComponentCallable` contract.  The import is lazy
    to keep this module light and free of import cycles.
    """
    from runner.dependency_normalizer import normalize_dependencies

    return [normalize_dependencies(run_id, repo_root)]


def _run_excellence_section_assembler(run_id: str, repo_root: Path) -> list[Path]:
    """Adapter: assemble the Excellence section from its per-sub-section drafts."""
    from runner.section_assembler import assemble_section

    return [assemble_section(run_id, repo_root, "excellence")]


def _run_impact_section_assembler(run_id: str, repo_root: Path) -> list[Path]:
    """Adapter: assemble the Impact section from its per-sub-section drafts."""
    from runner.section_assembler import assemble_section

    return [assemble_section(run_id, repo_root, "impact")]


def _run_implementation_section_assembler(
    run_id: str, repo_root: Path
) -> list[Path]:
    """Adapter: assemble the Implementation section from its drafts."""
    from runner.section_assembler import assemble_section

    return [assemble_section(run_id, repo_root, "implementation")]


def _run_excellence_assumption_applier(run_id: str, repo_root: Path) -> list[Path]:
    """Adapter: apply operator declarations to the Excellence drafts (pre-assembly)."""
    from runner.assumption_applier import apply_assumptions

    return apply_assumptions(run_id, repo_root, "excellence")


def _run_impact_assumption_applier(run_id: str, repo_root: Path) -> list[Path]:
    """Adapter: apply operator declarations to the Impact drafts (pre-assembly)."""
    from runner.assumption_applier import apply_assumptions

    return apply_assumptions(run_id, repo_root, "impact")


def _run_implementation_assumption_applier(
    run_id: str, repo_root: Path
) -> list[Path]:
    """Adapter: apply operator declarations to the Implementation drafts (pre-assembly)."""
    from runner.assumption_applier import apply_assumptions

    return apply_assumptions(run_id, repo_root, "implementation")


def _run_unit_cost_budget_deriver(run_id: str, repo_root: Path) -> list[Path]:
    """Adapter for the unit-cost budget deriver (§8.1 / C1).

    Derives the MSCA-style unit-cost budget deterministically from published
    rates and writes ``unit_cost_budget.json``.  Closed by the byte-equal
    replay check ``unit_cost_budget(months, rates, host_coeff) == figure``.

    The deriver returns ``None`` (writing nothing) for non-unit-cost
    instruments — the lump-sum gate branch owns those budgets — so the
    adapter records no outputs in that case.
    """
    from runner.unit_cost_budget import derive_unit_cost_budget

    written = derive_unit_cost_budget(run_id, repo_root)
    return [written] if written is not None else []


#: The authoritative registry of deterministic components, keyed by the
#: component id used in the manifest ``deterministic_components`` binding.
#: The section assemblers (one per Phase-8 criterion node) compose the
#: decomposed per-sub-section drafts into a section JSON by array-append,
#: closed by the byte-equal replay check ``assembler(drafts) == section_json``.
#: The unit-cost budget deriver (§8.1 / C1) computes the MSCA-style budget
#: deterministically from published rates, closed by
#: ``unit_cost_budget(months, rates, host_coeff) == figure``.  The
#: assumption-appliers (β honesty layer, ticket 9) flip enumerated declared
#: ``unresolved → assumed`` claims in the section drafts pre-assembly, closed by
#: idempotent byte-equal replay.  The remaining milestone-1 component
#: (canonical-pack deriver, ticket 10) registers here as it is built — binding
#: and logging then work uniformly for each.
COMPONENT_REGISTRY: dict[str, ComponentCallable] = {
    "dependency_normalizer": _run_dependency_normalizer,
    "excellence_section_assembler": _run_excellence_section_assembler,
    "impact_section_assembler": _run_impact_section_assembler,
    "implementation_section_assembler": _run_implementation_section_assembler,
    "excellence_assumption_applier": _run_excellence_assumption_applier,
    "impact_assumption_applier": _run_impact_assumption_applier,
    "implementation_assumption_applier": _run_implementation_assumption_applier,
    "unit_cost_budget_deriver": _run_unit_cost_budget_deriver,
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _to_repo_relative(path: _PathLike, repo_root: Path) -> str:
    """Normalize a written-artifact path to a repo-relative POSIX string."""
    p = Path(path)
    try:
        rel = p.relative_to(repo_root)
    except ValueError:
        # Already relative, or outside repo_root — record as given.
        rel = p
    return str(rel).replace("\\", "/")


def invoke_component(
    component_id: str,
    run_id: str,
    repo_root: Path,
) -> ComponentInvocationRecord:
    """Invoke a bound deterministic component and return an invocation record.

    Resolves *component_id* against :data:`COMPONENT_REGISTRY`, invokes the
    component, and captures the artifact paths it wrote.  This function
    **never raises for a component fault**: an unknown id, a raised
    exception, or any other failure is returned as a
    :class:`ComponentInvocationRecord` with ``status="failure"``.  The agent
    runtime maps that failure to the constitutional
    ``AGENT_EXECUTION_ERROR`` / ``can_evaluate_exit_gate=False`` outcome.

    Parameters
    ----------
    component_id:
        Component identifier from the manifest ``deterministic_components``
        binding.
    run_id:
        Current DAG-runner run UUID, propagated to the component.
    repo_root:
        Absolute path to the repository root.

    Returns
    -------
    ComponentInvocationRecord
        ``status="success"`` with ``outputs_written`` on success; otherwise
        ``status="failure"`` with ``failure_reason`` populated.
    """
    fn = COMPONENT_REGISTRY.get(component_id)
    if fn is None:
        reason = (
            f"Unknown deterministic component {component_id!r}; "
            f"known components: {sorted(COMPONENT_REGISTRY)}"
        )
        logger.error(reason)
        return ComponentInvocationRecord(
            component_id=component_id,
            status="failure",
            failure_reason=reason,
        )

    try:
        written = fn(run_id, repo_root)
    except Exception as exc:  # noqa: BLE001 — fault must become a record
        reason = f"Component {component_id!r} raised {type(exc).__name__}: {exc}"
        logger.error(reason)
        return ComponentInvocationRecord(
            component_id=component_id,
            status="failure",
            failure_reason=reason,
        )

    outputs = [
        _to_repo_relative(p, repo_root) for p in (written or [])
    ]
    logger.info(
        "Deterministic component %s completed: %s", component_id, outputs
    )
    return ComponentInvocationRecord(
        component_id=component_id,
        status="success",
        outputs_written=outputs,
    )
