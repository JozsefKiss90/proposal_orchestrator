"""
Deterministic unit-cost budget deriver (CLAUDE.md §8.1 / §17.5.3, roster
component C1/C2).

For **unit-cost instruments** (e.g. MSCA-PF) this repository computes the
budget **internally and deterministically** from published unit costs —
``confirmed_months × published_rates × host_country_coefficient`` — rather
than exchanging it through the external Lump Sum Budget Planner (which serves
**lump-sum instruments** only).  Because the computation is fixed arithmetic
on published constants and carries no judgment, **determinism is the
anti-fabrication guarantee** that externalisation supplies for lump-sum
(C1 amendment record).  The determinism is closed by the byte-equal replay
check ``unit_cost_budget(months, rates, host_coeff) == figure``
(``tests/runner/test_unit_cost_budget.py``).

This module has two layers:

  * :func:`compute_unit_cost_budget` — the **pure** figure.  Given the
    confirmed months, the rate table, and the host-country coefficient, it
    returns the fully-derived line items and total.  It performs no I/O and
    no domain reasoning; it is the byte-equal CI target.  When the host
    coefficient is ``None`` (unresolved) it still computes every
    **host-independent** line and marks the host-dependent living allowance
    ``Unresolved`` — the *informative blocked assessment* that "rides free
    under the block" (D12).

  * :func:`derive_unit_cost_budget` — the **deterministic component** the
    agent runtime invokes within the n07 node body (§17.5.3).  It resolves
    the rate table, the confirmed months, and the host country from durable
    state, calls the pure core, and atomically writes
    ``unit_cost_budget.json``.  Every budget component must resolve to
    Confirmed or operator-declared Assumed for ``gate_pass_declaration`` to
    be ``"pass"``; an unresolved months figure or host coefficient yields a
    ``"fail"`` assessment (the categorical budget block, §8.4 — preserved
    verbatim and instrument-independent).

Constitutional constraints (§8, §17.5.3, §17.6.7):
    * No agent, and no layer of this module, may fabricate, estimate, or
      substitute a budget figure.  Every number here is fixed arithmetic on
      the Tier 2B published unit costs; nothing is inferred.
    * The component performs no domain reasoning and never invokes Claude.
    * It cannot evaluate gates (§17.6.2) and is never invoked by a skill
      (§17.6.4); Python owns the write; it is closed by the byte-equal
      replay guarantee.
    * It **fails closed** (raises :class:`UnitCostBudgetError`) only on a
      malformed rate table or genuinely missing infrastructure; an
      *unresolved* input (months / host) is not an error — it is written as
      an honest ``"fail"`` (blocked) assessment, so the gate can block on it.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from runner.atomic_write import atomic_write_json

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UNIT_COST_RATES_REL: str = (
    "docs/tier2b_topic_and_call_sources/extracted/unit_cost_rates.json"
)
SELECTED_CALL_REL: str = (
    "docs/tier3_project_instantiation/call_binding/selected_call.json"
)
#: Tier 3 operator declaration file (host country / working assumptions).
#: Read-only here (the engine never writes it); the applier + reader that
#: fully consume it are tickets 9/15.  This module only *reads* a declared
#: host country if the file is present — an absent file is a valid state
#: that yields the honest block (α).
WORKING_ASSUMPTIONS_REL: str = (
    "docs/tier3_project_instantiation/working_assumptions.json"
)
OUTPUT_REL: str = (
    "docs/tier4_orchestration_state/phase_outputs"
    "/phase7_budget_gate/unit_cost_budget.json"
)

SCHEMA_ID: str = "orch.phase7.unit_cost_budget.v1"

#: The three claim/derivation status values a budget line can carry.  They
#: mirror the validation-report categories (§12.2): ``Confirmed`` (directly
#: evidenced), ``Assumed`` (operator-declared), ``Unresolved`` (blocks).
STATUS_CONFIRMED: str = "Confirmed"
STATUS_ASSUMED: str = "Assumed"
STATUS_UNRESOLVED: str = "Unresolved"


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class UnitCostBudgetError(Exception):
    """Raised when the unit-cost budget cannot be derived from a valid source.

    Reserved for genuine faults — a malformed/absent rate table, an
    unreadable output directory.  An *unresolved* months figure or host
    coefficient is **not** an error: it produces an honest ``"fail"``
    (blocked) assessment so the budget gate can block on it (§8.4).
    """


# ---------------------------------------------------------------------------
# Pure deterministic core — the byte-equal figure
# ---------------------------------------------------------------------------


def _round2(value: float) -> float:
    """Round to 2 decimals as a ``float``, deterministically.

    Coercing to ``float`` keeps every **computed amount** the same JSON type
    (``NNN.0`` rather than a bare int for whole-euro lines), so the byte-equal
    replay check compares like with like.  The same inputs always yield the
    same rounded float and therefore the same JSON bytes.
    """
    return round(float(value), 2)


def _monthly_rate(rates: dict[str, Any], group: str, line: str) -> int | float:
    """Extract a published per-month rate, failing closed if malformed."""
    grp = rates.get(group)
    if not isinstance(grp, dict):
        raise UnitCostBudgetError(
            f"unit_cost_rates.json missing '{group}' object"
        )
    entry = grp.get(line)
    if not isinstance(entry, dict):
        raise UnitCostBudgetError(
            f"unit_cost_rates.json missing '{group}.{line}' object"
        )
    amount = entry.get("amount_eur_per_month")
    if not isinstance(amount, (int, float)) or isinstance(amount, bool):
        raise UnitCostBudgetError(
            f"unit_cost_rates.json '{group}.{line}.amount_eur_per_month' "
            f"is not a number: {amount!r}"
        )
    return amount


def compute_unit_cost_budget(
    months: int,
    rates: dict[str, Any],
    host_coeff_percent: Optional[float],
    *,
    include_family: bool = False,
) -> dict[str, Any]:
    """Derive the unit-cost budget — the pure, deterministic figure.

    ``budget = confirmed_months × published_rates × host_country_coefficient``
    (§8.1).  The living allowance is the only host-dependent line
    (``living = base × CCC%``); all other lines are host-independent.

    Parameters
    ----------
    months:
        Confirmed fellowship / effort months (positive integer).
    rates:
        The parsed ``unit_cost_rates.json`` object (Tier 2B).
    host_coeff_percent:
        The host country's correction coefficient as a percent (e.g.
        ``100.0`` for BE).  ``None`` means the host is unresolved: every
        host-independent line is still computed and the living allowance is
        marked ``Unresolved`` (the informative blocked assessment, D12).
    include_family:
        Whether the (conditional, "if applicable") family allowance line is
        included.  Defaults to ``False``.

    Returns
    -------
    dict
        ``{"line_items": [...], "total_eur": <float|None>,
        "unresolved_components": [...]}``.  ``total_eur`` is ``None`` iff any
        line is ``Unresolved``.  The dict is JSON-serialisable and
        byte-stable for identical inputs (the replay guarantee).

    Raises
    ------
    UnitCostBudgetError
        Only on a malformed rate table or a non-positive ``months`` — never
        for an unresolved host coefficient (that is a valid blocked state).
    """
    if not isinstance(months, int) or isinstance(months, bool) or months <= 0:
        raise UnitCostBudgetError(
            f"confirmed months must be a positive integer, got {months!r}"
        )

    base_living = _monthly_rate(
        rates, "researcher_unit_contributions", "living_allowance"
    )
    mobility = _monthly_rate(
        rates, "researcher_unit_contributions", "mobility_allowance"
    )
    rtn = _monthly_rate(
        rates, "institutional_unit_contributions", "research_training_networking"
    )
    mgmt = _monthly_rate(
        rates, "institutional_unit_contributions", "management_and_indirect"
    )

    line_items: list[dict[str, Any]] = []
    unresolved: list[str] = []

    # ── Host-dependent line: living allowance = base × CCC% × months ──────
    if host_coeff_percent is None:
        line_items.append({
            "line_id": "living_allowance",
            "host_dependent": True,
            "base_monthly_rate_eur": base_living,
            "coefficient_percent": None,
            "monthly_rate_eur": None,
            "months": months,
            "amount_eur": None,
            "status": STATUS_UNRESOLVED,
        })
        unresolved.append("living_allowance")
    else:
        monthly_living = _round2(base_living * host_coeff_percent / 100.0)
        line_items.append({
            "line_id": "living_allowance",
            "host_dependent": True,
            "base_monthly_rate_eur": base_living,
            "coefficient_percent": host_coeff_percent,
            "monthly_rate_eur": monthly_living,
            "months": months,
            "amount_eur": _round2(monthly_living * months),
            "status": STATUS_CONFIRMED,
        })

    # ── Host-independent lines (always computed) ──────────────────────────
    host_independent: list[tuple[str, int | float]] = [
        ("mobility_allowance", mobility),
    ]
    if include_family:
        # Extracted only when emitted: a rate table lacking the (conditional,
        # "if applicable") family_allowance must not fail a budget that omits it.
        host_independent.append((
            "family_allowance",
            _monthly_rate(rates, "researcher_unit_contributions", "family_allowance"),
        ))
    host_independent.extend([
        ("research_training_networking", rtn),
        ("management_and_indirect", mgmt),
    ])

    for line_id, rate in host_independent:
        line_items.append({
            "line_id": line_id,
            "host_dependent": False,
            "monthly_rate_eur": rate,
            "months": months,
            "amount_eur": _round2(rate * months),
            "status": STATUS_CONFIRMED,
        })

    total_eur: Optional[float]
    if unresolved:
        total_eur = None
    else:
        total_eur = _round2(
            sum(item["amount_eur"] for item in line_items)
        )

    return {
        "line_items": line_items,
        "total_eur": total_eur,
        "unresolved_components": unresolved,
    }


# ---------------------------------------------------------------------------
# Input resolution (durable-state readers; fail-closed only on infra faults)
# ---------------------------------------------------------------------------


def _read_json(path: Path, label: str) -> Any:
    """Read and parse a JSON file, failing closed on any issue."""
    if not path.is_file():
        raise UnitCostBudgetError(f"{label} not found: {path}")
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        raise UnitCostBudgetError(f"Cannot read {label}: {exc}") from exc
    if not text.strip():
        raise UnitCostBudgetError(f"{label} is empty: {path}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise UnitCostBudgetError(f"{label} is not valid JSON: {exc}") from exc


def _read_optional_json(path: Path) -> Optional[dict[str, Any]]:
    """Read an optional JSON object; return ``None`` when absent/unreadable.

    Used for ``working_assumptions.json`` — an absent file is a **valid**
    state (the honest block, α), never an error.
    """
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _resolve_confirmed_months(
    call_data: dict[str, Any],
) -> tuple[Optional[int], str, str]:
    """Resolve the confirmed project (fellowship / effort) months.

    Returns ``(months, status, source)``.  The confirmed months is a
    **project-specific fact** — the call-level *maximum*
    (``max_project_duration_months``) is deliberately **not** used as the
    figure (§13.3: no fabricated project facts).  ``project_duration_months``
    is the confirmed project fact ticket 14 hand-lifts into the call binding;
    when it is absent the months are ``Unresolved`` (the honest block).
    """
    value = call_data.get("project_duration_months")
    if isinstance(value, int) and not isinstance(value, bool) and value > 0:
        return value, STATUS_CONFIRMED, f"{SELECTED_CALL_REL} -> project_duration_months"
    return (
        None,
        STATUS_UNRESOLVED,
        (
            "project_duration_months absent from selected_call.json "
            "(call-level max_project_duration_months is not a project fact); "
            "confirm the fellowship duration (ticket 14) or declare it"
        ),
    )


def _lookup_coefficient(
    rates: dict[str, Any], country: str
) -> Optional[float]:
    """Look up a country's living-allowance correction coefficient (percent)."""
    ccc = rates.get("country_correction_coefficient")
    if not isinstance(ccc, dict):
        return None
    table = ccc.get("coefficients_percent")
    if not isinstance(table, dict):
        return None
    value = table.get(country)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _resolve_host_country(
    call_data: dict[str, Any],
    working_assumptions: Optional[dict[str, Any]],
) -> tuple[Optional[str], str, str]:
    """Resolve the host country ISO code.

    Returns ``(country, status, source)``.  Priority: a **confirmed** host
    country in the call binding (``host_country``); then an
    **operator-declared** host country in ``working_assumptions.json`` (the β
    override — flagged ``Assumed``).  When neither is present the host is
    ``Unresolved`` (the honest block, α).

    The ``working_assumptions.json`` reader here is intentionally minimal:
    it reads a declared ``host_country`` if the file exists.  The full
    declaration substrate + applier are tickets 9/15; this module only needs
    the host-coefficient lookup (D11/D12).
    """
    confirmed = call_data.get("host_country")
    if isinstance(confirmed, str) and confirmed.strip():
        return confirmed.strip(), STATUS_CONFIRMED, f"{SELECTED_CALL_REL} -> host_country"

    if working_assumptions:
        declared = working_assumptions.get("host_country")
        if isinstance(declared, str) and declared.strip():
            return (
                declared.strip(),
                STATUS_ASSUMED,
                f"{WORKING_ASSUMPTIONS_REL} -> host_country (operator-declared)",
            )
    return (
        None,
        STATUS_UNRESOLVED,
        (
            "host country absent from selected_call.json and "
            "working_assumptions.json; the living-allowance coefficient "
            "cannot be resolved (confirm the host or declare it — D11/D12)"
        ),
    )


# ---------------------------------------------------------------------------
# Deterministic component — invoked by the agent runtime (n07 node body)
# ---------------------------------------------------------------------------


def derive_unit_cost_budget(run_id: str, repo_root: Path) -> Optional[Path]:
    """Derive the unit-cost budget and write ``unit_cost_budget.json``.

    Reads the Tier 2B rate table, resolves the confirmed months and host
    country from durable state, computes the deterministic figure, and
    atomically writes the assessment to the Phase-7 output directory.

    The assessment's ``gate_pass_declaration`` is ``"pass"`` only when every
    budget component resolves to Confirmed or operator-declared Assumed;
    when the months or host coefficient is ``Unresolved`` it is ``"fail"``
    with a matching ``blocking_inconsistencies`` entry — an **informative
    blocked assessment** with the host-independent lines computed
    (§8.4 categorical block; D12).

    **Instrument guard.** This deriver is bound to the n07 node body for every
    instrument, but the internal unit-cost derivation is meaningful only for
    **unit-cost** instruments.  When the selected call's ``budget_regime`` is
    anything other than ``"unit_cost"`` (e.g. a lump-sum RIA, whose budget is
    the external ``received/`` response and which has no ``unit_cost_rates.json``)
    the deriver **skips** — it returns ``None`` and writes nothing, so the
    lump-sum gate branch is unaffected.  The authoritative instrument branch is
    the gate's ``applies_when`` filter (which uses the profile resolver); this
    guard is the lightweight "should I run" check on the call binding.

    Parameters
    ----------
    run_id:
        Current DAG-runner run UUID (stamped into the artifact).
    repo_root:
        Absolute path to the repository root.

    Returns
    -------
    Optional[Path]
        Absolute path to the written ``unit_cost_budget.json``, or ``None``
        when skipped for a non-unit-cost instrument.

    Raises
    ------
    UnitCostBudgetError
        On a malformed/absent rate table or an unwritable output directory
        **for a unit-cost instrument**.  An unresolved months / host is
        written as a ``"fail"`` assessment, not raised.
    """
    call_data = _read_json(repo_root / SELECTED_CALL_REL, "selected_call.json")
    if not isinstance(call_data, dict):
        raise UnitCostBudgetError("selected_call.json root is not an object")

    # Instrument guard: skip cleanly for non-unit-cost instruments.
    regime = call_data.get("budget_regime")
    if regime is not None and regime != "unit_cost":
        logger.info(
            "unit_cost_budget_deriver skipped: budget_regime=%r is not "
            "unit_cost (the lump-sum branch owns this instrument's budget)",
            regime,
        )
        return None

    rates = _read_json(repo_root / UNIT_COST_RATES_REL, "unit_cost_rates.json")
    if not isinstance(rates, dict):
        raise UnitCostBudgetError("unit_cost_rates.json root is not an object")

    working_assumptions = _read_optional_json(
        repo_root / WORKING_ASSUMPTIONS_REL
    )

    months, months_status, months_source = _resolve_confirmed_months(call_data)
    host_country, host_status, host_source = _resolve_host_country(
        call_data, working_assumptions
    )
    host_coeff = (
        _lookup_coefficient(rates, host_country)
        if host_country is not None
        else None
    )

    # A resolved host country whose coefficient is not in the table is itself
    # unresolved (the Commission decides case-by-case for unlisted countries).
    if host_country is not None and host_coeff is None:
        host_status = STATUS_UNRESOLVED
        host_source = (
            f"host country {host_country!r} has no correction coefficient in "
            f"unit_cost_rates.json (unlisted; decided case-by-case)"
        )

    # ── Compute the figure (host-independent lines always land) ───────────
    # When months is unresolved we cannot multiply any line, so we still emit
    # an assessment naming months as the blocker but with zero computed lines.
    line_items: list[dict[str, Any]] = []
    total_eur: Optional[float] = None
    unresolved_lines: list[str] = []
    if months is not None:
        figure = compute_unit_cost_budget(months, rates, host_coeff)
        line_items = figure["line_items"]
        total_eur = figure["total_eur"]
        unresolved_lines = list(figure["unresolved_components"])

    # ── Aggregate resolution + blocking inconsistencies ───────────────────
    blocking: list[dict[str, Any]] = []
    if months_status == STATUS_UNRESOLVED:
        blocking.append({
            "inconsistency_id": "confirmed_months_unresolved",
            "description": months_source,
            "severity": "blocking",
            "resolution": "unresolved",
        })
    if host_status == STATUS_UNRESOLVED:
        blocking.append({
            "inconsistency_id": "host_coefficient_unresolved",
            "description": host_source,
            "severity": "blocking",
            "resolution": "unresolved",
        })

    all_resolved = not blocking and not unresolved_lines
    gate_pass = "pass" if all_resolved else "fail"

    artifact: dict[str, Any] = {
        "schema_id": SCHEMA_ID,
        "run_id": run_id,
        "instrument_type": call_data.get("instrument_type"),
        "budget_regime": "unit_cost",
        "gate_pass_declaration": gate_pass,
        "derivation": {
            "formula": "confirmed_months x published_rates x host_country_coefficient",
            "confirmed_months": months,
            "confirmed_months_status": months_status,
            "confirmed_months_source": months_source,
            "host_country": host_country,
            "host_country_status": host_status,
            "host_country_source": host_source,
            "host_country_coefficient_percent": host_coeff,
        },
        "line_items": line_items,
        "total_eur": total_eur,
        "unresolved_components": (
            [b["inconsistency_id"] for b in blocking] + unresolved_lines
        ),
        "blocking_inconsistencies": blocking,
        "source_refs": [
            {"tier": 2, "source_path": UNIT_COST_RATES_REL},
            {"tier": 3, "source_path": SELECTED_CALL_REL},
        ],
        "derivation_note": (
            "Unit-cost budget derived internally and deterministically from "
            "published unit costs (CLAUDE.md §8.1 / C1), validated by a "
            "byte-equal replay check. This is a derivation, not an estimate. "
            "The living allowance is the only host-dependent line. Every "
            "component must resolve to Confirmed or operator-declared Assumed "
            "before gate_09 passes; an unresolved figure blocks (§8.4)."
        ),
    }

    output_path = repo_root / OUTPUT_REL
    atomic_write_json(artifact, output_path, prefix="unit_cost_budget_")
    logger.info(
        "unit_cost_budget.json written: gate_pass=%s, %d line(s), total=%s, "
        "unresolved=%s",
        gate_pass,
        len(line_items),
        total_eur,
        artifact["unresolved_components"],
    )
    return output_path
