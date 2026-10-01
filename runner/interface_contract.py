"""
The Lump Sum Budget Planner interface-contract validator (CLAUDE.md §8.5).

§8.5 requires that every budget request conform to the interface contract at
``docs/integrations/lump_sum_budget_planner/interface_contract.json``, and that
"responses that do not conform to the interface contract must be rejected and
flagged, not silently accepted."

That contract is a **contract document**, not a JSON Schema.  It carries
``request_schema`` and ``response_schema`` blocks naming required fields, an
entry shape for ``work_packages`` and ``partners``, and a ``validation_rules``
block.  Read as a JSON Schema it has no recognised keyword at its root, so a
JSON-Schema validator accepts *every* payload against it — the §8.5 obligation
would be nominally checked and actually unenforced.  This module interprets the
document on its own terms instead.

It is pure: no I/O, no run state, no gate evaluation.  Both callers use it —
``runner.predicates.schema_predicates.interface_contract_conforms`` (``g08_p04``,
the response side) and ``runner.budget_request`` (the request side, which refuses
to write a non-conforming request).

What is checked, and only what the contract states
--------------------------------------------------
``<role>_schema.required_fields``
    Each named field is present at the payload root and is not empty.  ``None``,
    ``""``, ``[]`` and ``{}`` count as missing; ``0`` and ``False`` are values.
``<role>_schema.work_package_entry.required_fields`` / ``partner_entry``
    The matching collection must be a list of objects, and each element must
    carry its required fields, by the same emptiness rule.
``validation_rules.no_negative_values``
    No numeric value anywhere in the payload is negative.  The contract words
    the rule as "all numeric budget values", and the walk does not try to tell
    a budget value from any other number: deciding which field is a budget
    field is judgment, and this module performs none.  Walking everything is
    the no-judgment reading and it fails closed.  Booleans are excluded, since
    a flag is not a value and ``bool`` subclasses ``int`` in Python.

No field-level type constraint beyond the above is invented here.  The contract
says so itself: its ``demo_mode_note`` records that value ranges and field-level
types are a production concern.  A check this module cannot ground in the
contract text is not performed (§10.6, §13.2).

What this module deliberately leaves alone
------------------------------------------
The contract's other two ``validation_rules``, ``wp_coverage`` and
``partner_coverage``, are **not** checked here.  They are cross-artifact rules —
every ``wp_id`` in the request must appear in the response, and likewise every
``partner_id`` — and the gate already owns them as ``g08_p05`` and ``g08_p06``
(``runner/predicates/coverage_predicates.py``), which read the Phase 3 WP
structure and the Tier 3 consortium that this module never sees.  Implementing
them again here would put one rule in two places, where the two can drift.
This module's scope is the payload's own shape; coverage is the pair of
coverage predicates', and ``gate_09`` requires all of them.

One consequence worth stating plainly: because the contract declares no type
for ``lump_sum`` or ``total_effort_pm``, a response carrying those keys with a
non-numeric value conforms.  The entry shapes check that a priced line *has* a
price field, not that the field holds a number.  Closing that needs the
contract to carry the type, which is the production hardening its
``demo_mode_note`` defers.
"""

from __future__ import annotations

from typing import Any, NamedTuple

#: The two payload roles the contract defines, each with its own schema block.
ROLES: tuple[str, ...] = ("request", "response")

#: Collection field name -> the contract key naming its per-element shape.
#: Both are declared by the contract document itself; nothing is inferred.
_ENTRY_SHAPES: tuple[tuple[str, str], ...] = (
    ("work_packages", "work_package_entry"),
    ("partners", "partner_entry"),
)

#: Root keywords that make a document a JSON Schema.  A contract carrying both
#: a ``<role>_schema`` block *and* one of these is a hybrid: both readings
#: apply, and the caller runs both.  Reading only the contract-document half
#: would silently drop whatever the schema half constrains, which is the shape
#: of fail-open this module exists to prevent.
JSON_SCHEMA_ROOT_KEYWORDS: frozenset[str] = frozenset(
    {
        "$schema",
        "$ref",
        "type",
        "properties",
        "required",
        "allOf",
        "anyOf",
        "oneOf",
        "not",
        "patternProperties",
        "additionalProperties",
        "items",
        "prefixItems",
        "enum",
        "const",
    }
)


def carries_json_schema_keywords(contract: Any) -> bool:
    """Whether *contract* also constrains payloads as a JSON Schema."""
    if not isinstance(contract, dict):
        return False
    return bool(JSON_SCHEMA_ROOT_KEYWORDS & set(contract))


class ContractViolation(NamedTuple):
    """One way in which a payload departs from the interface contract.

    *field* locates the offender in the payload (``"$"`` for the payload root,
    ``"partners[0].partner_id"`` for an element field).  *requirement* names the
    contract clause breached, so a reader can go to the contract and see the
    rule.  *detail* says what was found.
    """

    field: str
    requirement: str
    detail: str

    def __str__(self) -> str:  # pragma: no cover — trivial rendering
        return f"{self.field}: {self.detail} ({self.requirement})"


def is_planner_contract(contract: Any) -> bool:
    """Return whether *contract* is a planner contract document.

    True when it is an object carrying at least one ``<role>_schema`` block.
    A JSON Schema (or the empty contract ``{}``) is not one, and its caller
    keeps JSON-Schema handling for it.
    """
    if not isinstance(contract, dict):
        return False
    return any(f"{role}_schema" in contract for role in ROLES)


def _is_missing(value: Any) -> bool:
    """Whether *value* counts as an absent required field.

    Structural emptiness only: ``None`` and the empty string / list / dict.
    ``0`` and ``False`` are values a budget payload legitimately carries.
    """
    if value is None:
        return True
    return isinstance(value, (str, list, dict, tuple)) and len(value) == 0


def _required_fields(block: Any) -> list[str]:
    """The ``required_fields`` list of a contract block, or ``[]``."""
    if not isinstance(block, dict):
        return []
    fields = block.get("required_fields")
    if not isinstance(fields, list):
        return []
    return [f for f in fields if isinstance(f, str)]


def _check_required(
    payload: dict, fields: list[str], requirement: str, prefix: str = ""
) -> list[ContractViolation]:
    violations: list[ContractViolation] = []
    for field in fields:
        if field not in payload:
            violations.append(
                ContractViolation(
                    field=f"{prefix}{field}",
                    requirement=requirement,
                    detail="required field absent",
                )
            )
        elif _is_missing(payload[field]):
            violations.append(
                ContractViolation(
                    field=f"{prefix}{field}",
                    requirement=requirement,
                    detail=f"required field is empty ({payload[field]!r})",
                )
            )
    return violations


def _check_negatives(node: Any, where: str) -> list[ContractViolation]:
    """Collect every negative numeric value at or below *node*."""
    violations: list[ContractViolation] = []
    if isinstance(node, bool):
        # bool subclasses int; a flag is not a budget value.
        return violations
    if isinstance(node, (int, float)):
        if node < 0:
            violations.append(
                ContractViolation(
                    field=where,
                    requirement="validation_rules.no_negative_values",
                    detail=f"negative numeric value {node!r}",
                )
            )
        return violations
    if isinstance(node, dict):
        for key in node:
            child = f"{where}.{key}" if where != "$" else str(key)
            violations.extend(_check_negatives(node[key], child))
        return violations
    if isinstance(node, list):
        for index, item in enumerate(node):
            violations.extend(_check_negatives(item, f"{where}[{index}]"))
    return violations


def validate_payload(
    payload: Any, contract: Any, *, role: str
) -> list[ContractViolation]:
    """Validate *payload* against *contract* in the given *role*.

    Returns every violation found, in a stable order: root required fields,
    then each collection's entry fields, then the negative-value rule.  An
    empty list means the payload conforms.

    Raises
    ------
    ValueError
        *role* is not one of :data:`ROLES`, or *contract* carries no schema
        block for that role.  A contract that cannot state the rule must not
        be read as stating that everything passes — that is the fail-open this
        module exists to close.
    """
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}, got {role!r}")
    if not isinstance(contract, dict):
        raise ValueError("interface contract root is not an object")
    block = contract.get(f"{role}_schema")
    if not isinstance(block, dict):
        raise ValueError(
            f"interface contract carries no {role}_schema block; it cannot "
            f"validate a {role} payload"
        )

    if not isinstance(payload, dict):
        return [
            ContractViolation(
                field="$",
                requirement=f"{role}_schema",
                detail=f"payload root is not an object (found {type(payload).__name__})",
            )
        ]

    violations = _check_required(
        payload, _required_fields(block), f"{role}_schema.required_fields"
    )

    for collection, entry_key in _ENTRY_SHAPES:
        entry_fields = _required_fields(block.get(entry_key))
        if not entry_fields:
            continue
        value = payload.get(collection)
        if value is None:
            # Absence is the root required_fields check's business, if the
            # contract requires the collection at all.
            continue
        requirement = f"{role}_schema.{entry_key}"
        if not isinstance(value, list):
            violations.append(
                ContractViolation(
                    field=collection,
                    requirement=requirement,
                    detail=(
                        f"expected a list of entries, found "
                        f"{type(value).__name__}"
                    ),
                )
            )
            continue
        for index, entry in enumerate(value):
            prefix = f"{collection}[{index}]"
            if not isinstance(entry, dict):
                violations.append(
                    ContractViolation(
                        field=prefix,
                        requirement=requirement,
                        detail=(
                            f"expected an entry object, found "
                            f"{type(entry).__name__}"
                        ),
                    )
                )
                continue
            violations.extend(
                _check_required(entry, entry_fields, requirement, prefix=f"{prefix}.")
            )

    rules = contract.get("validation_rules")
    if isinstance(rules, dict) and "no_negative_values" in rules:
        violations.extend(_check_negatives(payload, "$"))

    return violations
