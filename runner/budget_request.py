"""
Deterministic lump-sum budget request composer (CLAUDE.md §8.2 / §17.5.3).

For **lump-sum instruments** this repository computes no budget figure (§8.1).
What it may do is §8.2's first clause: *prepare structured budget requests* from
the templates in ``docs/integrations/lump_sum_budget_planner/request_templates/``.
The operator then runs the request through the external Lump Sum Budget Planner
and places the response in ``received/``, where ``gate_09``'s lump-sum branch
validates it.

Composing that request is a transform, not a judgment.  Every field is copied
from a durable upstream artifact or is a constant:

====================================  ==================================
Field                                 Source
====================================  ==================================
``call_id``, ``project_duration_months``  Tier 3 ``selected_call.json``
``work_packages[]``                   Phase 3 ``wp_structure.json``
``work_packages[].start/end_month``   Phase 4 ``gantt.json`` task window
``partners[]``                        Tier 3 ``partners.json``
``partners[].management_roles``       Phase 6 ``implementation_architecture.json``
every effort and cost field           the constant sentinel below
====================================  ==================================

So it is a **deterministic component** (§17.5.3, C2), not a skill: no Claude
invocation, no domain reasoning, no inference.  It is bound to ``n07_budget_gate``
in the manifest under ``deterministic_components`` (§16.5, C3) and closed by a
byte-equal replay guarantee — the composed request carries no wall-clock field,
and its ``request_id`` is derived from the call, not the run.

Constitutional constraints (§8.1, §8.3, §8.5, §13.3, §17.6.7)
-------------------------------------------------------------
* **No budget figure is computed, estimated or copied.**  Every effort and cost
  field carries :data:`REQUIRES_EXTERNAL_COMPUTATION`.  The call binding's
  indicative euro amounts are call-level facts, not this project's budget, and
  are not carried into the request.
* **No project fact is invented** (§13.3).  A WP with no Gantt task gets a
  ``null`` month window, not a guessed one.
* **The request is validated against the interface contract before it is
  written** (§8.5).  A non-conforming request is refused, not written.
* **Partner identity is copied verbatim** from Tier 3.  The composer never
  chooses between two spellings of a partner's country: a ``country`` that has
  left its ``country_slot`` is a Tier 3 defect and halts the compose, because
  on this branch a real country name re-identifies a derived partner.
* It evaluates no gate (§17.6.2) and is invoked by no skill (§17.6.4).
* It **fails closed**: a missing or malformed input raises
  :class:`BudgetRequestError` and writes nothing.  A partial budget request is
  worse than none, because the planner would price what it was given.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from runner.atomic_write import atomic_write_json
from runner.instrument_profile import owns_budget_regime, resolve_budget_regime
from runner.interface_contract import validate_payload

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical paths
# ---------------------------------------------------------------------------

#: The composed request — the artifact registry's ``a_t3_budget_request``.
OUTPUT_REL = "docs/tier3_project_instantiation/integration/budget_request.json"

CONTRACT_REL = "docs/integrations/lump_sum_budget_planner/interface_contract.json"
SELECTED_CALL_REL = (
    "docs/tier3_project_instantiation/call_binding/selected_call.json"
)
PARTNERS_REL = "docs/tier3_project_instantiation/consortium/partners.json"
WP_STRUCTURE_REL = (
    "docs/tier4_orchestration_state/phase_outputs/phase3_wp_design/"
    "wp_structure.json"
)
GANTT_REL = (
    "docs/tier4_orchestration_state/phase_outputs/phase4_gantt_milestones/"
    "gantt.json"
)
IMPLEMENTATION_REL = (
    "docs/tier4_orchestration_state/phase_outputs/"
    "phase6_implementation_architecture/implementation_architecture.json"
)

#: The sentinel every effort and cost field carries.  A non-numeric token can
#: never be mistaken for a figure, and it tells the planner exactly which
#: fields it is being asked to compute (§8.1, §8.3).
REQUIRES_EXTERNAL_COMPUTATION = "requires_external_computation"

#: The fields the external planner computes, named in the request itself.
EXTERNALLY_COMPUTED_FIELDS: tuple[str, ...] = (
    "work_packages[].effort_person_months",
    "work_packages[].lump_sum_eur",
    "partners[].total_effort_pm",
    "partners[].cost_eur",
)


class BudgetRequestError(Exception):
    """A budget request could not be composed from durable state."""


# ---------------------------------------------------------------------------
# Pure deterministic core
# ---------------------------------------------------------------------------


def _wp_month_windows(gantt: dict) -> dict[str, tuple[int, int]]:
    """The first and last month of each WP's Gantt tasks.

    A WP with no task appears in no window, and its caller writes ``null``
    months rather than inventing a span.
    """
    windows: dict[str, tuple[int, int]] = {}
    tasks = gantt.get("tasks")
    if not isinstance(tasks, list):
        raise BudgetRequestError("gantt.json carries no tasks list")
    for task in tasks:
        if not isinstance(task, dict):
            continue
        wp_id = task.get("wp_id")
        start = task.get("start_month")
        end = task.get("end_month")
        if not isinstance(wp_id, str):
            continue
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        if wp_id in windows:
            known_start, known_end = windows[wp_id]
            windows[wp_id] = (min(known_start, start), max(known_end, end))
        else:
            windows[wp_id] = (start, end)
    return windows


def _management_roles(implementation: dict) -> dict[str, list[str]]:
    """Each partner's Phase 6 management role names, in declaration order."""
    roles: dict[str, list[str]] = {}
    declared = implementation.get("management_roles")
    if not isinstance(declared, list):
        raise BudgetRequestError(
            "implementation_architecture.json carries no management_roles list"
        )
    for role in declared:
        if not isinstance(role, dict):
            continue
        partner_id = role.get("assigned_to")
        name = role.get("role_name")
        if isinstance(partner_id, str) and isinstance(name, str):
            roles.setdefault(partner_id, []).append(name)
    return roles


def _entry_ids(container: dict, collection: str, id_field: str) -> list[str]:
    """Sorted string ids of ``container[collection]``, skipping malformed entries.

    A missing or non-list collection yields ``[]``. The caller has already
    refused the work package if its own required fields are absent; a task
    list that is empty is a WP design fact, not a composer error.
    """
    entries = container.get(collection)
    if not isinstance(entries, list):
        return []
    return sorted(
        entry[id_field]
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get(id_field), str)
    )


def _partner_identity(partner: dict) -> tuple[str, str, str]:
    """``(partner_id, pseudonym, country_slot)``, copied verbatim from Tier 3.

    Raises when ``country`` has left ``country_slot``.  The two fields exist
    because the artifact schema requires ``country`` while the branch's
    anonymity constraint requires a slot token; when they disagree, one of them
    is a real country name, and the composer must not pick the safe one and
    carry on (§13.3, and the branch anonymity constraint).
    """
    partner_id = partner.get("partner_id")
    if not isinstance(partner_id, str) or not partner_id:
        raise BudgetRequestError(f"partner entry has no partner_id: {partner!r}")
    name = partner.get("legal_name")
    if not isinstance(name, str) or not name:
        raise BudgetRequestError(f"partner {partner_id} has no legal_name")
    slot = partner.get("country_slot")
    country = partner.get("country")
    if not isinstance(country, str) or not country:
        raise BudgetRequestError(f"partner {partner_id} has no country")
    if slot is not None and slot != country:
        raise BudgetRequestError(
            f"partner {partner_id} declares country {country!r} and "
            f"country_slot {slot!r}. They must agree: one of them is not a "
            f"pseudonymous slot token, and the composer copies identity "
            f"verbatim rather than choosing between them."
        )
    return partner_id, name, country


def compose_budget_request(
    run_id: str,
    call: dict,
    wp_structure: dict,
    gantt: dict,
    implementation: dict,
    partners_record: dict,
    contract_version: Any = None,
) -> dict:
    """Compose the budget request payload. Pure: no I/O, no clock.

    The byte-equal replay target.  Ordering is by identifier throughout, so the
    payload does not depend on the order of the upstream lists.

    Raises
    ------
    BudgetRequestError
        An input is structurally unusable, a WP identifier is duplicated, or a
        WP names a lead absent from the consortium.
    """
    call_id = call.get("call_id")
    if not isinstance(call_id, str) or not call_id:
        raise BudgetRequestError("selected_call.json carries no call_id")
    duration = call.get("project_duration_months")
    if not isinstance(duration, int) or isinstance(duration, bool):
        raise BudgetRequestError(
            "selected_call.json carries no integer project_duration_months"
        )

    declared_partners = partners_record.get("partners")
    if not isinstance(declared_partners, list) or not declared_partners:
        raise BudgetRequestError("partners.json carries no partners list")

    work_packages = wp_structure.get("work_packages")
    if not isinstance(work_packages, list) or not work_packages:
        raise BudgetRequestError("wp_structure.json carries no work_packages")

    windows = _wp_month_windows(gantt)
    roles = _management_roles(implementation)

    # One pass: the identity triple and the source record, keyed by partner id.
    identities: dict[str, tuple[str, str]] = {}
    source_records: dict[str, dict] = {}
    for partner in declared_partners:
        if not isinstance(partner, dict):
            raise BudgetRequestError(f"partner entry is not an object: {partner!r}")
        partner_id, name, country = _partner_identity(partner)
        if partner_id in identities:
            raise BudgetRequestError(f"duplicate partner_id {partner_id}")
        identities[partner_id] = (name, country)
        source_records[partner_id] = partner

    # --- work packages -----------------------------------------------------
    composed_wps: list[dict] = []
    leads: dict[str, list[str]] = {}
    seen_wp_ids: set[str] = set()
    for wp in sorted(
        (w for w in work_packages if isinstance(w, dict)),
        key=lambda w: str(w.get("wp_id", "")),
    ):
        wp_id = wp.get("wp_id")
        title = wp.get("title")
        lead = wp.get("lead_partner")
        if not isinstance(wp_id, str) or not wp_id:
            raise BudgetRequestError(f"work package has no wp_id: {wp!r}")
        if wp_id in seen_wp_ids:
            raise BudgetRequestError(f"duplicate wp_id {wp_id}")
        seen_wp_ids.add(wp_id)
        if not isinstance(title, str) or not title:
            raise BudgetRequestError(f"work package {wp_id} has no title")
        if not isinstance(lead, str) or lead not in identities:
            raise BudgetRequestError(
                f"work package {wp_id} names lead partner {lead!r}, which is "
                f"absent from the Tier 3 consortium"
            )
        leads.setdefault(lead, []).append(wp_id)

        contributing = [
            p
            for p in wp.get("contributing_partners", [])
            if isinstance(p, str) and p in identities
        ]
        start, end = windows.get(wp_id, (None, None))
        composed_wps.append(
            {
                "wp_id": wp_id,
                "title": title,
                "lead_partner": lead,
                "contributing_partners": sorted(set(contributing)),
                "start_month": start,
                "end_month": end,
                "task_ids": _entry_ids(wp, "tasks", "task_id"),
                "deliverable_ids": _entry_ids(wp, "deliverables", "deliverable_id"),
                "effort_person_months": REQUIRES_EXTERNAL_COMPUTATION,
                "lump_sum_eur": REQUIRES_EXTERNAL_COMPUTATION,
            }
        )

    # --- partners ----------------------------------------------------------
    composed_partners: list[dict] = []
    for partner_id in sorted(identities):
        name, country = identities[partner_id]
        source = source_records[partner_id]
        role = source.get("participation_role")
        composed_partners.append(
            {
                "partner_id": partner_id,
                "name": name,
                "country": country,
                "role": role if isinstance(role, str) and role else "beneficiary",
                "country_slot_class": source.get("country_slot_class"),
                "organisation_type": source.get("organisation_type"),
                "is_coordinator": bool(source.get("is_coordinator")),
                "participation_status": source.get("participation_status"),
                "wps_as_lead": sorted(leads.get(partner_id, [])),
                "management_roles": list(roles.get(partner_id, [])),
                "total_effort_pm": REQUIRES_EXTERNAL_COMPUTATION,
                "cost_eur": REQUIRES_EXTERNAL_COMPUTATION,
            }
        )

    return {
        "request_id": f"budget_request_{call_id}",
        "call_id": call_id,
        "project_duration_months": duration,
        "work_packages": composed_wps,
        "partners": composed_partners,
        "topic_code": call.get("topic_code"),
        "type_of_action": call.get("type_of_action"),
        "budget_regime": call.get("budget_regime"),
        "run_id": run_id,
        "contract_version": contract_version,
        "fields_requiring_external_computation": list(EXTERNALLY_COMPUTED_FIELDS),
        "source_refs": [
            {"tier": 3, "source_path": SELECTED_CALL_REL},
            {"tier": 3, "source_path": PARTNERS_REL},
            {"tier": 4, "source_path": WP_STRUCTURE_REL},
            {"tier": 4, "source_path": GANTT_REL},
            {"tier": 4, "source_path": IMPLEMENTATION_REL},
        ],
        "composition_note": (
            "Structured budget request prepared under CLAUDE.md §8.2 for "
            "submission to the external Lump Sum Budget Planner. Every field is "
            "copied from the named source or is a constant; no budget figure is "
            "computed, estimated or carried here (§8.1, §8.3). The fields named "
            "in fields_requiring_external_computation are the planner's to "
            "compute. Partner identity is the Tier 3 pseudonym and country slot, "
            "verbatim."
        ),
    }


# ---------------------------------------------------------------------------
# The deterministic component
# ---------------------------------------------------------------------------


def _read_json(repo_root: Path, rel: str) -> Any:
    path = repo_root / rel
    if not path.is_file():
        raise BudgetRequestError(f"required input is absent: {rel}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BudgetRequestError(f"{rel} is not readable JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise BudgetRequestError(f"{rel} root is not an object")
    return data


def derive_budget_request(run_id: str, repo_root: Path) -> Optional[Path]:
    """Compose the budget request and write it to :data:`OUTPUT_REL`.

    **Instrument guard.** The composer is bound to the n07 node body for every
    instrument, but an external budget request is meaningful only for a
    **lump-sum** instrument.  The guard is
    :func:`runner.instrument_profile.owns_budget_regime`, which the unit-cost
    deriver shares, so exactly one of the two components writes on any given
    call.  When this call's regime is not lump-sum the composer skips: it
    returns ``None`` and writes nothing, leaving the internal derivation
    (``runner.unit_cost_budget``) to own that budget.  An **unresolvable**
    regime skips too, and so does the deriver, so nothing is written and
    ``gate_09`` blocks on the missing artifact — the fail-closed answer, since
    the gate's own ``applies_when`` resolution fails closed on the same state.

    Returns
    -------
    Optional[Path]
        Absolute path to the written ``budget_request.json``, or ``None`` when
        skipped for a non-lump-sum instrument.

    Raises
    ------
    BudgetRequestError
        A required input is absent or malformed, the upstream artifacts
        contradict each other, or the composed request does not conform to the
        interface contract.  Nothing is written in any of those cases.
    """
    if not owns_budget_regime(repo_root, "lump_sum"):
        logger.info(
            "budget_request_composer skipped: this call's budget regime is %r, "
            "not lump_sum (None means unresolvable, and no budget component "
            "writes — gate_09 then blocks on the missing artifact)",
            resolve_budget_regime(repo_root),
        )
        return None

    call = _read_json(repo_root, SELECTED_CALL_REL)
    contract = _read_json(repo_root, CONTRACT_REL)
    wp_structure = _read_json(repo_root, WP_STRUCTURE_REL)
    gantt = _read_json(repo_root, GANTT_REL)
    implementation = _read_json(repo_root, IMPLEMENTATION_REL)
    partners_record = _read_json(repo_root, PARTNERS_REL)

    request = compose_budget_request(
        run_id,
        call,
        wp_structure,
        gantt,
        implementation,
        partners_record,
        contract_version=contract.get("contract_version"),
    )

    # §8.5: conformance is checked before the write, not after. A request the
    # contract rejects is never handed to the planner.
    violations = validate_payload(request, contract, role="request")
    if violations:
        raise BudgetRequestError(
            "composed budget request does not conform to the interface "
            f"contract at {CONTRACT_REL}: "
            + "; ".join(str(v) for v in violations)
        )

    output_path = repo_root / OUTPUT_REL
    atomic_write_json(request, output_path, prefix="budget_request_")
    logger.info(
        "budget_request.json written: %d work package(s), %d partner(s), "
        "no budget figure",
        len(request["work_packages"]),
        len(request["partners"]),
    )
    return output_path
