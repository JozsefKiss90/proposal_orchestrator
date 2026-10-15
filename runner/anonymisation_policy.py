"""The anonymisation policy, ``anonymisation_policy/1`` (AN2).

AN2 of ``.scratch/msca-dn-anonymisation/tickets.md``, stage A1 of
``plans/msca_dn_anonymisation_handoff_2026-10-14.md``. The pipeline that turns
the submitted MSCA-DN original into an anonymised derivative applies two
artifacts: a private entity dictionary, which names every concrete entity, and
this public policy, which names none. The policy says, for each category of the
handoff's §5 A1 table, what happens to an entity of that category and what
replaces it.

What a policy holds
-------------------
* One entry per category, in the handoff's order, with the ids the AN3 fixture
  set (``tests/_anonymisation_fixture.CATEGORIES``). Each entry carries a
  :data:`RULES` value, a replacement pattern, the attributes the replacement
  keeps, and a §12.2 status with its basis.
* What the pipeline keeps whatever the category: scientific content, methods,
  work-package logic and the rest of the handoff's "kept" list.
* The re-identification thresholds stage A5 applies (operator decision O3).

The rule values are the handoff table's own: ``replace``, ``generalise``,
``band``, ``flag`` (never edited automatically) and ``operator_review`` (looked
at one item at a time, never silently dropped), plus ``keep`` for a category a
later policy version chooses to leave as it is.

The hash
--------
:func:`policy_sha256` hashes the parsed record in a canonical serialisation
(sorted keys, no whitespace, UTF-8), not the file bytes. A CRLF checkout or a
re-indent is not a policy change; any change to a value, a category or the
order of the categories is. A record bound to the hash — the A2 replay, the A7
acceptance record — calls :func:`require_hash`, and a mismatch means acceptance
is re-opened.

The starting policy, :data:`STARTING_POLICY_PATH`, is adopted by a Tier 4
decision record that pins its hash. Editing it without a successor record fails
the test suite.

Constitutional standing: a reader and validator for an authoring tool. It
evaluates no gate, invokes no Claude, writes nothing and invents no fact
(CLAUDE.md §13.3). It names no entity; the policy's own test asserts that.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

#: Schema of a policy record. A change to the record's shape is a new schema.
SCHEMA = "anonymisation_policy/1"

#: The ``record_type`` a policy carries.
RECORD_TYPE = "anonymisation_policy"

#: The committed starting policy, beside this module.
STARTING_POLICY_PATH: Path = Path(__file__).resolve().parent / "anonymisation_policy_v1.json"

#: What may happen to a category's entities.
RULES: frozenset[str] = frozenset(
    {"keep", "replace", "generalise", "band", "flag", "operator_review"}
)

#: Rules under which the pipeline edits automatically, through a pattern.
PATTERN_RULES: frozenset[str] = frozenset({"replace", "generalise", "band"})

#: How a replacement is reused. ``per_entity``: one entity, one replacement,
#: everywhere. ``document``: one fixed pseudonym across the document.
#: ``per_occurrence``: each occurrence on its own value, as a band is.
CONSISTENCY: frozenset[str] = frozenset({"per_entity", "document", "per_occurrence"})

#: What the operator may do to an item under review. Dropping it is not here:
#: the handoff says never silently drop.
REVIEW_ACTIONS: frozenset[str] = frozenset({"redraw", "mask"})

#: The four statuses CLAUDE.md §12.2 defines.
STATUSES: frozenset[str] = frozenset({"Confirmed", "Inferred", "Assumed", "Unresolved"})

_TOP_FIELDS: tuple[str, ...] = (
    "schema",
    "record_type",
    "policy_id",
    "policy_version",
    "source",
    "decisions_applied",
    "categories",
    "kept_content",
    "reidentification_threshold",
)

_CATEGORY_FIELDS: tuple[str, ...] = (
    "id",
    "label",
    "rule",
    "auto_edit",
    "replacement_pattern",
    "placeholders",
    "example",
    "consistency",
    "retain",
    "review_unit",
    "permitted_actions",
    "note",
    "declared_status",
    "basis",
)

_DECISION_FIELDS: tuple[str, ...] = ("decision", "record", "applied_as")

_TARGET_FIELDS: tuple[str, ...] = (
    "target",
    "category",
    "max_correct_guesses",
    "guess_admissible",
    "kept_by",
    "declared_status",
    "basis",
)

_ID = re.compile(r"^[a-z][a-z0-9_]*$")
_PLACEHOLDER = re.compile(r"\{([^{}]*)\}")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class PolicyRefused(ValueError):
    """The policy is unreadable or malformed. The message names every problem."""


class PolicyChanged(RuntimeError):
    """The policy's hash is not the one a record was bound to."""


@dataclass(frozen=True)
class CategoryRule:
    """One category of a validated policy."""

    id: str
    label: str
    rule: str
    auto_edit: bool
    replacement_pattern: Optional[str]
    placeholders: Mapping[str, str]
    example: Optional[str]
    consistency: Optional[str]
    retain: tuple[str, ...]
    review_unit: Optional[str]
    permitted_actions: tuple[str, ...]


@dataclass(frozen=True)
class LoadedPolicy:
    """A validated policy, its hash and its categories in order.

    ``record`` is a private copy: changing it changes neither the file nor the
    hash.
    """

    record: dict[str, Any]
    sha256: str
    version: int
    categories: tuple[CategoryRule, ...]


def canonical_bytes(record: Mapping[str, Any]) -> bytes:
    """The serialisation :func:`policy_sha256` hashes."""
    return json.dumps(
        record, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def policy_sha256(record: Mapping[str, Any]) -> str:
    """The policy's hash: sha256 of :func:`canonical_bytes`."""
    return hashlib.sha256(canonical_bytes(record)).hexdigest()


def load(path: Path) -> LoadedPolicy:
    """Read, validate and hash the policy at *path*.

    Raises :class:`PolicyRefused` for an unreadable file, invalid JSON or a
    record :func:`validate` refuses.
    """
    try:
        text = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise PolicyRefused(f"policy {path} cannot be read: {exc}") from exc
    try:
        record = json.loads(text, object_pairs_hook=_refuse_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise PolicyRefused(f"policy {path} is not valid JSON: {exc}") from exc
    validate(record)
    return LoadedPolicy(
        record=copy.deepcopy(record),
        sha256=policy_sha256(record),
        version=record["policy_version"],
        categories=tuple(_category_rule(c) for c in record["categories"]),
    )


def require_hash(policy: LoadedPolicy, expected_sha256: str) -> None:
    """Refuse *policy* unless its hash is *expected_sha256*.

    A record bound to a policy hash — a redaction replay, an acceptance — is
    void for any other policy. Raises :class:`PolicyChanged`.
    """
    if not (isinstance(expected_sha256, str) and _SHA256.match(expected_sha256)):
        raise PolicyChanged(f"recorded policy hash {expected_sha256!r} is not a sha256")
    if policy.sha256 != expected_sha256:
        raise PolicyChanged(
            f"policy hash {policy.sha256} differs from the recorded {expected_sha256}; "
            "the policy changed, which re-opens acceptance"
        )


def validate(record: Any) -> None:
    """Refuse a malformed policy, naming every problem in one message."""
    if not isinstance(record, dict):
        raise PolicyRefused("a policy must be a JSON object")
    problems: list[str] = []
    _check_fields(record, _TOP_FIELDS, "policy", problems)

    if "schema" in record and record["schema"] != SCHEMA:
        problems.append(f"schema must be {SCHEMA!r}, not {record['schema']!r}")
    if "record_type" in record and record["record_type"] != RECORD_TYPE:
        problems.append(f"record_type must be {RECORD_TYPE!r}")
    for field in ("policy_id", "source"):
        if field in record and not _text(record[field]):
            problems.append(f"{field} must be a non-empty string")
    if "policy_version" in record:
        version = record["policy_version"]
        if type(version) is not int or version < 1:
            problems.append("policy_version must be an integer of at least 1")

    if "decisions_applied" in record:
        _check_decisions(record["decisions_applied"], problems)
    if "kept_content" in record:
        kept = record["kept_content"]
        if not (isinstance(kept, list) and kept and all(_text(k) for k in kept)):
            problems.append("kept_content must be a non-empty list of non-empty strings")

    categories: dict[str, dict[str, Any]] = {}
    if "categories" in record:
        categories = _check_categories(record["categories"], problems)
    if "reidentification_threshold" in record:
        _check_thresholds(record["reidentification_threshold"], categories, problems)

    if problems:
        raise PolicyRefused("policy refused:\n- " + "\n- ".join(problems))


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------


class _DuplicateKey(json.JSONDecodeError):
    pass


def _refuse_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Refuse an object that names a key twice.

    ``json`` keeps the last value silently, so the hash would cover a value the
    file's reader may never have seen.
    """
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise _DuplicateKey(f"duplicate key {key!r}", "", 0)
        obj[key] = value
    return obj


def _member(value: Any, allowed: Any) -> bool:
    """``value in allowed`` for a string; false for anything else.

    A list or an object in the record is unhashable, and a plain ``in`` would
    raise ``TypeError`` instead of naming the problem.
    """
    return isinstance(value, str) and value in allowed


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _check_fields(
    obj: Mapping[str, Any], fields: tuple[str, ...], where: str, problems: list[str]
) -> None:
    for name in fields:
        if name not in obj:
            problems.append(f"{where}: missing field {name!r}")
    for name in obj:
        if name not in fields:
            problems.append(f"{where}: unknown field {name!r}")


def _check_status(obj: Mapping[str, Any], where: str, problems: list[str]) -> None:
    if "declared_status" in obj and not _member(obj["declared_status"], STATUSES):
        problems.append(f"{where}: declared_status must be one of {sorted(STATUSES)}")
    if "basis" in obj and not _text(obj["basis"]):
        problems.append(f"{where}: basis must be a non-empty string")


def _check_decisions(decisions: Any, problems: list[str]) -> None:
    if not (isinstance(decisions, list) and decisions):
        problems.append("decisions_applied must be a non-empty list")
        return
    for index, entry in enumerate(decisions):
        where = f"decisions_applied[{index}]"
        if not isinstance(entry, dict):
            problems.append(f"{where} must be an object")
            continue
        _check_fields(entry, _DECISION_FIELDS, where, problems)
        for name in _DECISION_FIELDS:
            if name in entry and not _text(entry[name]):
                problems.append(f"{where}: {name} must be a non-empty string")


def _check_categories(categories: Any, problems: list[str]) -> dict[str, dict[str, Any]]:
    if not (isinstance(categories, list) and categories):
        problems.append("categories must be a non-empty list")
        return {}
    seen: dict[str, dict[str, Any]] = {}
    for index, category in enumerate(categories):
        if not isinstance(category, dict):
            problems.append(f"categories[{index}] must be an object")
            continue
        cid = category.get("id")
        where = f"category {cid!r}" if isinstance(cid, str) else f"categories[{index}]"
        _check_fields(category, _CATEGORY_FIELDS, where, problems)
        if not (isinstance(cid, str) and _ID.match(cid)):
            problems.append(f"{where}: id must be lower snake case")
        elif cid in seen:
            problems.append(f"{where}: duplicate category id")
        else:
            seen[cid] = category
        _check_category(category, where, problems)
    return seen


def _check_category(category: Mapping[str, Any], where: str, problems: list[str]) -> None:
    _check_status(category, where, problems)
    if "label" in category and not _text(category["label"]):
        problems.append(f"{where}: label must be a non-empty string")
    for name in ("example", "note"):
        if name in category and category[name] is not None and not _text(category[name]):
            problems.append(f"{where}: {name} must be a non-empty string or null")

    rule = category.get("rule")
    if not _member(rule, RULES):
        problems.append(f"{where}: rule must be one of {sorted(RULES)}, not {rule!r}")
        return

    edits = rule in PATTERN_RULES
    pattern = category.get("replacement_pattern")
    if edits and not _text(pattern):
        problems.append(f"{where}: rule {rule!r} needs a replacement_pattern")
    if not edits and pattern is not None:
        problems.append(f"{where}: rule {rule!r} takes no replacement_pattern")

    if "auto_edit" in category:
        if not isinstance(category["auto_edit"], bool):
            problems.append(f"{where}: auto_edit must be true or false")
        elif category["auto_edit"] != edits:
            problems.append(f"{where}: auto_edit must be {str(edits).lower()} under rule {rule!r}")

    consistency = category.get("consistency")
    if edits and not _member(consistency, CONSISTENCY):
        problems.append(f"{where}: consistency must be one of {sorted(CONSISTENCY)}")
    if not edits and "consistency" in category and consistency is not None:
        problems.append(f"{where}: rule {rule!r} takes no consistency")

    placeholders = category.get("placeholders")
    if not (isinstance(placeholders, dict) and all(
        _text(k) and _text(v) for k, v in placeholders.items()
    )):
        problems.append(f"{where}: placeholders must map names to descriptions")
    elif isinstance(pattern, str):
        used = set(_PLACEHOLDER.findall(pattern))
        for name in sorted(used - set(placeholders)):
            problems.append(f"{where}: placeholder {name!r} is not declared")
        for name in sorted(set(placeholders) - used):
            problems.append(f"{where}: placeholder {name!r} is declared but unused")
    elif placeholders:
        problems.append(f"{where}: placeholders declared without a replacement_pattern")

    retain = category.get("retain")
    if not (isinstance(retain, list) and all(_text(r) for r in retain)):
        problems.append(f"{where}: retain must be a list of non-empty strings")

    review_unit = category.get("review_unit")
    actions = category.get("permitted_actions")
    if rule == "operator_review":
        if not _text(review_unit):
            problems.append(f"{where}: rule 'operator_review' needs a review_unit")
        if not (
            isinstance(actions, list)
            and actions
            and all(_member(a, REVIEW_ACTIONS) for a in actions)
            and len(set(actions)) == len(actions)
        ):
            problems.append(
                f"{where}: permitted_actions must be distinct members of "
                f"{sorted(REVIEW_ACTIONS)}"
            )
    else:
        if "review_unit" in category and review_unit is not None:
            problems.append(f"{where}: only rule 'operator_review' takes a review_unit")
        if "permitted_actions" in category and actions != []:
            problems.append(f"{where}: only rule 'operator_review' takes permitted_actions")


def _check_thresholds(
    threshold: Any, categories: Mapping[str, Mapping[str, Any]], problems: list[str]
) -> None:
    if not (isinstance(threshold, dict) and set(threshold) == {"targets"}):
        problems.append("reidentification_threshold must be an object holding only 'targets'")
        return
    targets = threshold["targets"]
    if not (isinstance(targets, list) and targets):
        problems.append("reidentification_threshold.targets must be a non-empty list")
        return
    seen: set[str] = set()
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            problems.append(f"reidentification_threshold.targets[{index}] must be an object")
            continue
        name = target.get("target")
        where = f"threshold {name!r}"
        _check_fields(target, _TARGET_FIELDS, where, problems)
        _check_status(target, where, problems)
        if not (isinstance(name, str) and _ID.match(name)):
            problems.append(f"{where}: target must be lower snake case")
        elif name in seen:
            problems.append(f"{where}: duplicate target")
        else:
            seen.add(name)

        category = target.get("category")
        if not _member(category, categories):
            problems.append(f"{where}: category {category!r} is not a policy category")

        maximum = target.get("max_correct_guesses")
        admissible = target.get("guess_admissible")
        if not isinstance(admissible, bool):
            problems.append(f"{where}: guess_admissible must be true or false")
        if maximum is not None and (type(maximum) is not int or maximum < 0):
            problems.append(f"{where}: max_correct_guesses must be a non-negative integer or null")
        if maximum is not None and admissible is True:
            problems.append(f"{where}: an admissible guess takes no max_correct_guesses")
        if maximum is None and admissible is not True and target.get("declared_status") != "Unresolved":
            problems.append(
                f"{where}: with no max_correct_guesses the target must be admissible "
                "or declared Unresolved"
            )

        # O3: a guess is admissible only for what the policy keeps.
        kept_by = target.get("kept_by")
        if admissible is True:
            owner = categories.get(category) if isinstance(category, str) else None
            retain = (owner or {}).get("retain") or []
            if not (_text(kept_by) and kept_by in retain):
                problems.append(
                    f"{where}: an admissible guess needs kept_by naming a retained "
                    f"attribute of {category!r}, and {kept_by!r} is not one"
                )
        elif "kept_by" in target and kept_by is not None:
            problems.append(f"{where}: only an admissible guess takes kept_by")


def _category_rule(category: Mapping[str, Any]) -> CategoryRule:
    return CategoryRule(
        id=category["id"],
        label=category["label"],
        rule=category["rule"],
        auto_edit=category["auto_edit"],
        replacement_pattern=category["replacement_pattern"],
        placeholders=dict(category["placeholders"]),
        example=category["example"],
        consistency=category["consistency"],
        retain=tuple(category["retain"]),
        review_unit=category["review_unit"],
        permitted_actions=tuple(category["permitted_actions"]),
    )
