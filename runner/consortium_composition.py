"""The consortium-composition condition, evaluated against Tier 1.

One question, answered deterministically: does a set of partner records satisfy
the Horizon Europe consortium-composition condition? The condition is *read*
from Tier 1 ``extracted/participation_rules.json`` — thresholds and verbatim
spans alike — so no threshold here comes from programme knowledge (CLAUDE.md
§10.6), and every result carries the spans it was decided on (§10.5).

The condition, as the General Annexes put it:

    the consortium includes, as beneficiaries, three legal entities independent
    from each other and each established in a different country, as follows: at
    least one independent legal entity established in a Member State; and at
    least two other independent legal entities, each established in different
    Member States or Associated Countries.

Four limbs, and the evaluator reports which one fails:

``independent_beneficiaries``
    Fewer than three partners are independent beneficiaries. An affiliated
    entity does not sign the grant agreement, so it counts for nothing.
``distinct_countries``
    Fewer than three distinct country slots among those beneficiaries. Two
    partners in one slot count once.
``member_state``
    No slot is a Member State.
``other_countries``
    Fewer than two *further* slots are Member States or Associated Countries.

Why country **slots**
---------------------
Instance two is anonymised. A partner's country is a pseudonymous slot (``C1``,
``C2``, …) carrying only whether it is a Member State or an Associated Country,
because that is the only thing the condition needs. The evaluator therefore
never sees a real country name, and cannot leak one.

Constitutional standing
-----------------------
Subordinate to CLAUDE.md. Pure, deterministic and Claude-free: it reads Tier 1
and Tier 3, returns a result, and writes nothing. It evaluates no gate (§17.6.2)
and is not a manifest-bound deterministic component (§17.5.3) — it is a
repository-level check, like ``runner/agnosticism_lint.py``. A caller that wants
the result durable writes it to Tier 4 itself.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Sequence

# ---------------------------------------------------------------------------
# Slot classes
# ---------------------------------------------------------------------------

#: A country slot standing for a Member State.
MS: str = "MS"

#: A country slot standing for an Associated Country.
AC: str = "AC"

#: Repo-relative path of the Tier 1 rule source.
PARTICIPATION_RULES_REL: str = (
    "docs/tier1_normative_framework/extracted/participation_rules.json"
)

#: Repo-relative path of the Tier 3 partner registry.
PARTNERS_REL: str = "docs/tier3_project_instantiation/consortium/partners.json"

#: The limb names, in the order the condition states them.
LIMBS: tuple[str, ...] = (
    "independent_beneficiaries",
    "distinct_countries",
    "member_state",
    "other_countries",
)


class CompositionError(Exception):
    """Raised when Tier 1 or Tier 3 cannot be read as the evaluator needs it.

    Fail-closed: a missing threshold or an unreadable partner record is never
    defaulted. Guessing a threshold would be the programme-knowledge
    substitution §10.6 forbids, and guessing a slot class would decide
    eligibility on an invention.
    """


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Citation:
    """One verbatim span of a Tier 1 source, as the rule artifact records it."""

    quote: str
    source_document: str
    source_page: int
    source_section: str = ""
    limb: str = ""
    """Which limb of the condition this span evidences, for a legible report."""


@dataclass(frozen=True)
class CompositionRule:
    """The condition as Tier 1 states it: thresholds plus the spans behind them."""

    minimum_independent_beneficiaries: int
    minimum_distinct_countries: int
    minimum_in_a_member_state: int
    minimum_others_in_member_or_associated_countries: int
    affiliated_entities_count: bool
    rule_text: str
    citations: tuple[Citation, ...]
    source_path: str = PARTICIPATION_RULES_REL


@dataclass(frozen=True)
class Beneficiary:
    """One partner record, reduced to what the condition asks about."""

    partner_id: str
    country_slot: str
    slot_class: str
    """:data:`MS`, :data:`AC`, or any other token for a third country."""
    independent: bool
    is_beneficiary: bool

    @property
    def counts(self) -> bool:
        """True when this partner counts towards the minimum at all."""
        return self.independent and self.is_beneficiary


@dataclass(frozen=True)
class CompositionResult:
    """The outcome of evaluating one consortium against the condition."""

    met: bool
    counted: tuple[str, ...]
    """Partner ids that count, sorted."""
    excluded: tuple[str, ...]
    """Partner ids excluded as affiliated or non-beneficiary, sorted."""
    distinct_country_slots: tuple[str, ...]
    member_state_slots: tuple[str, ...]
    associated_country_slots: tuple[str, ...]
    other_slots: tuple[str, ...]
    """Slots that are neither Member State nor Associated Country."""
    failed_limbs: tuple[str, ...]
    satisfying_selection: Optional[tuple[str, ...]]
    """One partner per slot that satisfies the condition, or ``None``."""
    thresholds: tuple[int, int, int, int]
    """The rule's four thresholds, in :data:`LIMBS` order, so a result carries
    what it was judged against."""
    citations: tuple[Citation, ...]

    @property
    def status(self) -> str:
        """``"met"`` or ``"not met"`` — the word a report prints."""
        return "met" if self.met else "not met"

    @property
    def reason(self) -> str:
        """One sentence a reader can check against the counts.

        Derived from the fields rather than passed in: every number it quotes is
        already here, so the sentence cannot drift from the verdict.
        """
        head = (
            f"{len(self.counted)} independent beneficiaries span "
            f"{len(self.distinct_country_slots)} country slots: "
            f"{len(self.member_state_slots)} Member State, "
            f"{len(self.associated_country_slots)} Associated Country"
        )
        if self.other_slots:
            head += f", {len(self.other_slots)} neither"
        if self.met:
            minimum = self.thresholds[0]
            return (
                f"{head}. The condition needs {minimum} beneficiaries in as many "
                "countries, one of them a Member State. Met."
            )
        return f"{head}. Failed limbs: " + ", ".join(self.failed_limbs) + "."


# ---------------------------------------------------------------------------
# Reading the rule (Tier 1)
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> dict:
    """Read a JSON object, failing closed with the path in the message."""
    if not path.is_file():
        raise CompositionError(f"required artifact is absent: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise CompositionError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise CompositionError(
            f"{path} must hold a JSON object, got {type(data).__name__}"
        )
    return data


def _require_int(block: dict, key: str, where: str) -> int:
    value = block.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise CompositionError(
            f"{where} must carry integer '{key}', got {value!r}. The threshold "
            "is read from Tier 1, never defaulted (CLAUDE.md §10.6)."
        )
    return value


def _citation(block: dict, key: str, limb: str) -> Optional[Citation]:
    """Build a :class:`Citation` from a span object, or ``None`` if absent."""
    span = block.get(key)
    if not isinstance(span, dict):
        return None
    quote = span.get("quote")
    document = span.get("source_document")
    page = span.get("source_page")
    if not isinstance(quote, str) or not isinstance(document, str):
        return None
    if not isinstance(page, int) or isinstance(page, bool):
        return None
    return Citation(
        quote=quote,
        source_document=document,
        source_page=page,
        source_section=str(span.get("source_section", "")),
        limb=limb,
    )


def load_composition_rule(repo_root: Path) -> CompositionRule:
    """Read the composition condition out of Tier 1 ``participation_rules.json``."""
    path = repo_root / PARTICIPATION_RULES_REL
    block = _load_json(path).get("consortium_composition")
    if not isinstance(block, dict):
        raise CompositionError(
            f"{path} carries no 'consortium_composition' block. Tier 1 must be "
            "populated before the condition can be evaluated."
        )
    where = f"{PARTICIPATION_RULES_REL} -> consortium_composition"

    spans = [
        _citation(block, "lead_in_source_span", "independent_beneficiaries"),
        _citation(block, "member_state_limb_source_span", "member_state"),
        _citation(block, "other_countries_limb_source_span", "other_countries"),
        _citation(block, "affiliated_entities_source_span", "affiliated_entities"),
    ]
    citations = tuple(span for span in spans if span is not None)
    if not citations:
        raise CompositionError(
            f"{where} carries no source span. A condition without a span is a "
            "condition from memory (CLAUDE.md §10.5)."
        )

    affiliated = block.get("affiliated_entities_count_towards_the_minimum")
    if not isinstance(affiliated, bool):
        raise CompositionError(
            f"{where} must state 'affiliated_entities_count_towards_the_minimum' "
            "as a boolean."
        )

    rule_text = block.get("rule")
    if not isinstance(rule_text, str) or not rule_text.strip():
        raise CompositionError(f"{where} must carry the rule text.")

    return CompositionRule(
        minimum_independent_beneficiaries=_require_int(
            block, "minimum_independent_beneficiaries", where
        ),
        minimum_distinct_countries=_require_int(
            block, "minimum_distinct_countries", where
        ),
        minimum_in_a_member_state=_require_int(
            block, "minimum_in_a_member_state", where
        ),
        minimum_others_in_member_or_associated_countries=_require_int(
            block, "minimum_others_in_member_or_associated_countries", where
        ),
        affiliated_entities_count=affiliated,
        rule_text=rule_text.strip(),
        citations=citations,
    )


# ---------------------------------------------------------------------------
# Reading the partners (Tier 3)
# ---------------------------------------------------------------------------


def load_partners(repo_root: Path) -> tuple[Beneficiary, ...]:
    """Read Tier 3 ``partners.json`` into the records the condition asks about.

    Fails closed on a partner without a country slot or without a slot class:
    the evaluator will not decide eligibility on a defaulted slot.
    """
    path = repo_root / PARTNERS_REL
    entries = _load_json(path).get("partners")
    if not isinstance(entries, list) or not entries:
        raise CompositionError(f"{path} must carry a non-empty 'partners' array.")

    out: list[Beneficiary] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise CompositionError(
                f"{PARTNERS_REL} partners[{index}] must be an object."
            )
        partner_id = entry.get("partner_id")
        if not isinstance(partner_id, str) or not partner_id.strip():
            raise CompositionError(
                f"{PARTNERS_REL} partners[{index}] must carry a 'partner_id'."
            )
        slot = entry.get("country_slot")
        slot_class = entry.get("country_slot_class")
        if not isinstance(slot, str) or not slot.strip():
            raise CompositionError(
                f"{PARTNERS_REL} {partner_id} must carry a 'country_slot'."
            )
        if not isinstance(slot_class, str) or not slot_class.strip():
            raise CompositionError(
                f"{PARTNERS_REL} {partner_id} must carry a 'country_slot_class' "
                f"({MS} or {AC}). A defaulted class would decide eligibility on "
                "an invention."
            )
        out.append(
            Beneficiary(
                partner_id=partner_id.strip(),
                country_slot=slot.strip(),
                slot_class=slot_class.strip(),
                independent=bool(entry.get("independent_legal_entity", True)),
                is_beneficiary=entry.get("participation_role") != "associated_partner",
            )
        )
    return tuple(out)


def partners_by_capability_basis(repo_root: Path) -> dict[str, list[str]]:
    """Group partner ids by their ``capability_basis``, reading Tier 3.

    Which partners are derived and which are invented is a Tier 3 fact, recorded
    once in ``partners.json``. Callers read it from here rather than restating it,
    so a CLI default or a report can never disagree with the registry.
    """
    entries = _load_json(repo_root / PARTNERS_REL).get("partners")
    if not isinstance(entries, list):
        raise CompositionError(f"{PARTNERS_REL} must carry a 'partners' array.")
    grouped: dict[str, list[str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        basis = entry.get("capability_basis")
        partner_id = entry.get("partner_id")
        if isinstance(basis, str) and isinstance(partner_id, str):
            grouped.setdefault(basis, []).append(partner_id)
    for basis in ("derived", "fictional"):
        grouped.setdefault(basis, [])
    return {basis: sorted(ids) for basis, ids in grouped.items()}


# ---------------------------------------------------------------------------
# The evaluation (pure)
# ---------------------------------------------------------------------------


def _first_partner_per_slot(counted: Sequence[Beneficiary]) -> dict[str, str]:
    """Map each slot to its lowest-sorting partner id, so a selection is stable."""
    per_slot: dict[str, str] = {}
    for partner in sorted(counted, key=lambda p: p.partner_id):
        per_slot.setdefault(partner.country_slot, partner.partner_id)
    return per_slot


def evaluate_composition(
    partners: Iterable[Beneficiary], rule: CompositionRule
) -> CompositionResult:
    """Evaluate *partners* against *rule* and report which limbs fail.

    Deterministic: the result, including the satisfying selection, depends on the
    partner set and not on its order.
    """
    all_partners = list(partners)
    counted = [p for p in all_partners if p.counts]
    excluded = tuple(sorted(p.partner_id for p in all_partners if not p.counts))

    by_slot = _first_partner_per_slot(counted)
    slots = tuple(sorted(by_slot))

    # Classify each slot from its lowest-sorting partner, so two partners that
    # disagree about their shared slot's class resolve the same way every run.
    # Order-independence is the §9.5 reproducibility property this evaluator
    # claims; a last-wins dict over an unsorted list would quietly break it.
    classes: dict[str, str] = {}
    for partner in sorted(counted, key=lambda p: p.partner_id):
        classes.setdefault(partner.country_slot, partner.slot_class)
    ms_slots = tuple(s for s in slots if classes[s] == MS)
    ac_slots = tuple(s for s in slots if classes[s] == AC)
    other_slots = tuple(s for s in slots if classes[s] not in (MS, AC))

    failed: list[str] = []
    if len(counted) < rule.minimum_independent_beneficiaries:
        failed.append("independent_beneficiaries")
    if len(slots) < rule.minimum_distinct_countries:
        failed.append("distinct_countries")
    if len(ms_slots) < rule.minimum_in_a_member_state:
        failed.append("member_state")

    # The 'other' limb counts the *further* eligible slots, so the slot already
    # spent on the Member State limb is not counted twice.
    eligible = len(ms_slots) + len(ac_slots)
    others = eligible - min(len(ms_slots), rule.minimum_in_a_member_state)
    if others < rule.minimum_others_in_member_or_associated_countries:
        failed.append("other_countries")

    selection: Optional[tuple[str, ...]] = None
    if not failed:
        chosen_ms = ms_slots[: rule.minimum_in_a_member_state]
        remaining = [s for s in ms_slots + ac_slots if s not in chosen_ms]
        chosen_other = sorted(remaining)[
            : rule.minimum_others_in_member_or_associated_countries
        ]
        selection = tuple(by_slot[s] for s in sorted(chosen_ms) + chosen_other)

    return CompositionResult(
        met=not failed,
        counted=tuple(sorted(p.partner_id for p in counted)),
        excluded=excluded,
        distinct_country_slots=slots,
        member_state_slots=ms_slots,
        associated_country_slots=ac_slots,
        other_slots=other_slots,
        failed_limbs=tuple(limb for limb in LIMBS if limb in failed),
        satisfying_selection=selection,
        thresholds=(
            rule.minimum_independent_beneficiaries,
            rule.minimum_distinct_countries,
            rule.minimum_in_a_member_state,
            rule.minimum_others_in_member_or_associated_countries,
        ),
        citations=rule.citations,
    )


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Scenario:
    """One consortium variant evaluated against the condition."""

    name: str
    question: str
    partner_ids: tuple[str, ...]
    result: CompositionResult


def evaluate_scenarios(
    partners: Sequence[Beneficiary],
    rule: CompositionRule,
    *,
    derived_ids: Sequence[str],
    gap_ids: Sequence[str],
) -> tuple[Scenario, ...]:
    """Evaluate the three readings the consortium ticket asks for.

    All partners; the derived partners alone; and each gap partner removed in
    turn. The last one is the redundancy question: does the consortium still
    meet the condition if any single unconfirmed partner withdraws?
    """
    by_id = {p.partner_id: p for p in partners}

    def scenario(name: str, question: str, ids: Sequence[str]) -> Scenario:
        subset = [by_id[i] for i in ids]
        return Scenario(
            name=name,
            question=question,
            partner_ids=tuple(ids),
            result=evaluate_composition(subset, rule),
        )

    all_ids = [p.partner_id for p in partners]
    out = [
        scenario(
            "all_partners",
            "Does the consortium as designed meet the condition?",
            all_ids,
        ),
        scenario(
            "derived_partners_only",
            "Do the partners derived from instance one meet it without the "
            "fictional gap partners?",
            [i for i in all_ids if i in set(derived_ids)],
        ),
    ]
    for gap_id in gap_ids:
        out.append(
            scenario(
                f"without_{gap_id}",
                f"Does it still meet the condition if {gap_id} withdraws before "
                "confirmation?",
                [i for i in all_ids if i != gap_id],
            )
        )
    return tuple(out)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def format_scenarios(scenarios: Sequence[Scenario]) -> str:
    """Render the scenario table a human reads."""
    lines = ["[composition] Tier 1 consortium-composition condition:"]
    for scenario in scenarios:
        lines.append(
            f"  {scenario.name}: {scenario.result.status} "
            f"({len(scenario.partner_ids)} partners) — {scenario.result.reason}"
        )
    if scenarios:
        for citation in scenarios[0].result.citations:
            lines.append(
                f"  cited: {citation.source_document} p.{citation.source_page} "
                f"({citation.limb})"
            )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI  (python -m runner.consortium_composition)
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> int:
    """Evaluate the demo consortium from the command line.

    Exit codes: ``0`` the condition is met by all partners; ``1`` it is not;
    ``3`` Tier 1 or Tier 3 could not be read.
    """
    parser = argparse.ArgumentParser(
        prog="python -m runner.consortium_composition",
        description=(
            "Evaluate the Tier 1 consortium-composition condition against Tier 3 "
            "partners.json, three ways."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Repository root (default: auto-discovered via find_repo_root).",
    )
    parser.add_argument(
        "--derived",
        default=None,
        help=(
            "Comma-separated partner ids derived from instance one. Default: "
            "every partner whose capability_basis is 'derived'."
        ),
    )
    parser.add_argument(
        "--gap",
        default=None,
        help=(
            "Comma-separated fictional gap-partner ids. Default: every partner "
            "whose capability_basis is 'fictional'."
        ),
    )
    args = parser.parse_args(argv)

    from runner.paths import find_repo_root

    try:
        repo_root = (
            Path(args.repo_root).resolve() if args.repo_root else find_repo_root()
        )
        rule = load_composition_rule(repo_root)
        partners = load_partners(repo_root)
        by_basis = partners_by_capability_basis(repo_root)
        scenarios = evaluate_scenarios(
            partners,
            rule,
            derived_ids=(
                [s for s in args.derived.split(",") if s]
                if args.derived is not None
                else by_basis["derived"]
            ),
            gap_ids=(
                [s for s in args.gap.split(",") if s]
                if args.gap is not None
                else by_basis["fictional"]
            ),
        )
    except CompositionError as exc:
        print(f"[composition] ERROR: {exc}", file=sys.stderr, flush=True)
        return 3
    except Exception as exc:  # noqa: BLE001 — CLI boundary
        print(f"[composition] ERROR: {exc}", file=sys.stderr, flush=True)
        return 3

    text = format_scenarios(scenarios)
    met = scenarios[0].result.met
    print(text, file=sys.stdout if met else sys.stderr, flush=True)
    return 0 if met else 1


if __name__ == "__main__":
    sys.exit(main())
