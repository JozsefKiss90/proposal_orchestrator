"""AN2 — the anonymisation policy.

Acceptance, from ``.scratch/msca-dn-anonymisation/tickets.md`` AN2:

1. The policy schema validates, the loader refuses a malformed policy, and the
   hash is stable across loads.
2. The starting policy covers every category in the handoff's table, including
   figures needing operator review per figure.
3. The policy's category ids are the fixture's ``CATEGORIES`` ids (set by AN3).
4. The policy names no real entity.

And from the ticket's own text: any change to the policy re-opens acceptance.
The decision record that adopts the starting policy pins its hash, so a policy
edited without a successor record fails here.
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any, Iterator

import pytest

from runner import anonymisation_policy as ap
from tests import _anonymisation_fixture as fx

REPO = Path(__file__).resolve().parents[2]
ADOPTION_RECORD = (
    REPO
    / "docs/tier4_orchestration_state/decision_log"
    / "msca-dn-anonymisation-policy-adoption_2026-10-15.json"
)


@pytest.fixture()
def record() -> dict[str, Any]:
    return json.loads(ap.STARTING_POLICY_PATH.read_text(encoding="utf-8"))


def _write(tmp_path: Path, obj: Any) -> Path:
    path = tmp_path / "policy.json"
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    return path


def _category(record: dict[str, Any], cid: str) -> dict[str, Any]:
    return next(c for c in record["categories"] if c["id"] == cid)


def _refusal(record: dict[str, Any]) -> str:
    with pytest.raises(ap.PolicyRefused) as excinfo:
        ap.validate(record)
    return str(excinfo.value)


# ---------------------------------------------------------------------------
# 1. Schema, refusal and hash
# ---------------------------------------------------------------------------


class TestStartingPolicyLoads:
    def test_loads_and_carries_the_schema(self) -> None:
        policy = ap.load(ap.STARTING_POLICY_PATH)
        assert policy.record["schema"] == ap.SCHEMA == "anonymisation_policy/1"
        assert policy.version == 1
        assert re.fullmatch(r"[0-9a-f]{64}", policy.sha256)

    def test_hash_is_stable_across_loads(self) -> None:
        assert ap.load(ap.STARTING_POLICY_PATH).sha256 == ap.load(ap.STARTING_POLICY_PATH).sha256

    def test_hash_ignores_layout_and_line_endings(self, tmp_path: Path, record: dict) -> None:
        # A CRLF checkout or a re-indent is not a policy change.
        compact = tmp_path / "compact.json"
        compact.write_bytes(json.dumps(record, separators=(",", ":")).encode("utf-8"))
        crlf = tmp_path / "crlf.json"
        crlf.write_bytes(json.dumps(record, indent=4).replace("\n", "\r\n").encode("utf-8"))
        reference = ap.load(ap.STARTING_POLICY_PATH).sha256
        assert ap.load(compact).sha256 == reference
        assert ap.load(crlf).sha256 == reference

    def test_hash_changes_with_any_rule(self, tmp_path: Path, record: dict) -> None:
        _category(record, "grant")["example"] = "a current doctoral network grant"
        assert ap.load(_write(tmp_path, record)).sha256 != ap.load(ap.STARTING_POLICY_PATH).sha256

    def test_loaded_record_is_a_copy(self) -> None:
        policy = ap.load(ap.STARTING_POLICY_PATH)
        policy.record["categories"].clear()
        assert ap.load(ap.STARTING_POLICY_PATH).categories


class TestLoaderRefuses:
    def test_not_json(self, tmp_path: Path) -> None:
        path = tmp_path / "policy.json"
        path.write_text("{not json", encoding="utf-8")
        with pytest.raises(ap.PolicyRefused, match="not valid JSON"):
            ap.load(path)

    def test_not_an_object(self, tmp_path: Path) -> None:
        with pytest.raises(ap.PolicyRefused, match="JSON object"):
            ap.load(_write(tmp_path, []))

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(ap.PolicyRefused, match="cannot be read"):
            ap.load(tmp_path / "absent.json")

    def test_wrong_schema(self, record: dict) -> None:
        record["schema"] = "anonymisation_policy/2"
        assert "schema" in _refusal(record)

    def test_missing_top_level_field(self, record: dict) -> None:
        del record["kept_content"]
        assert "kept_content" in _refusal(record)

    def test_unknown_top_level_field(self, record: dict) -> None:
        record["extra"] = 1
        assert "extra" in _refusal(record)

    @pytest.mark.parametrize("version", [0, -1, "1", 1.0, True])
    def test_bad_version(self, record: dict, version: Any) -> None:
        record["policy_version"] = version
        assert "policy_version" in _refusal(record)

    def test_unknown_rule(self, record: dict) -> None:
        _category(record, "grant")["rule"] = "delete"
        assert "rule" in _refusal(record)

    def test_duplicate_category(self, record: dict) -> None:
        record["categories"].append(copy.deepcopy(record["categories"][0]))
        assert "duplicate" in _refusal(record)

    def test_missing_category_field(self, record: dict) -> None:
        del _category(record, "facility")["consistency"]
        assert "consistency" in _refusal(record)

    def test_unknown_category_field(self, record: dict) -> None:
        _category(record, "facility")["colour"] = "red"
        assert "colour" in _refusal(record)

    def test_status_outside_the_vocabulary(self, record: dict) -> None:
        _category(record, "facility")["declared_status"] = "Probable"
        assert "declared_status" in _refusal(record)

    def test_editing_rule_needs_a_pattern(self, record: dict) -> None:
        _category(record, "person_name")["replacement_pattern"] = None
        assert "replacement_pattern" in _refusal(record)

    def test_flag_may_not_carry_a_pattern(self, record: dict) -> None:
        _category(record, "niche_topic")["replacement_pattern"] = "a field"
        assert "replacement_pattern" in _refusal(record)

    def test_flag_may_not_auto_edit(self, record: dict) -> None:
        _category(record, "niche_topic")["auto_edit"] = True
        assert "auto_edit" in _refusal(record)

    def test_operator_review_needs_a_review_unit(self, record: dict) -> None:
        _category(record, "identifying_figure")["review_unit"] = None
        assert "review_unit" in _refusal(record)

    def test_operator_review_may_not_silently_drop(self, record: dict) -> None:
        _category(record, "identifying_figure")["permitted_actions"].append("drop")
        assert "permitted_actions" in _refusal(record)

    def test_undeclared_placeholder(self, record: dict) -> None:
        _category(record, "person_name")["replacement_pattern"] = "{role} {code} {colour}"
        assert "colour" in _refusal(record)

    def test_unused_placeholder(self, record: dict) -> None:
        _category(record, "person_name")["placeholders"]["colour"] = "unused"
        assert "colour" in _refusal(record)

    def test_threshold_naming_an_unknown_category(self, record: dict) -> None:
        record["reidentification_threshold"]["targets"][0]["category"] = "planet"
        assert "planet" in _refusal(record)

    def test_admissible_guess_needs_the_policy_to_keep_it(self, record: dict) -> None:
        # O3: the country set may be guessed only when the policy keeps it.
        _category(record, "location")["retain"].remove("country")
        assert "country" in _refusal(record)

    def test_open_threshold_must_be_admissible_or_unresolved(self, record: dict) -> None:
        target = next(
            t for t in record["reidentification_threshold"]["targets"]
            if t["target"] == "research_group"
        )
        target["declared_status"] = "Confirmed"
        assert "research_group" in _refusal(record)

    @pytest.mark.parametrize("value", [[], {}])
    def test_unhashable_values_are_refused_not_raised(self, record: dict, value: Any) -> None:
        figure = _category(record, "identifying_figure")
        figure["declared_status"] = value
        figure["permitted_actions"] = [value]
        _category(record, "grant")["rule"] = value
        _category(record, "facility")["consistency"] = value
        record["reidentification_threshold"]["targets"][0]["category"] = value
        message = _refusal(record)
        for name in ("declared_status", "permitted_actions", "rule", "consistency", "category"):
            assert name in message

    def test_repeated_review_action(self, record: dict) -> None:
        _category(record, "identifying_figure")["permitted_actions"] = ["mask", "mask"]
        assert "permitted_actions" in _refusal(record)

    def test_duplicate_json_key(self, tmp_path: Path) -> None:
        path = tmp_path / "policy.json"
        text = ap.STARTING_POLICY_PATH.read_text(encoding="utf-8")
        path.write_text(text.replace('"policy_version": 1,', '"policy_version": 1, "policy_version": 2,'), encoding="utf-8")
        with pytest.raises(ap.PolicyRefused, match="duplicate key"):
            ap.load(path)

    def test_every_problem_is_named_at_once(self, record: dict) -> None:
        del record["kept_content"]
        _category(record, "grant")["rule"] = "delete"
        message = _refusal(record)
        assert "kept_content" in message and "rule" in message


class TestHashBinding:
    def test_matching_hash_passes(self) -> None:
        policy = ap.load(ap.STARTING_POLICY_PATH)
        ap.require_hash(policy, policy.sha256)

    def test_changed_policy_reopens_acceptance(self) -> None:
        policy = ap.load(ap.STARTING_POLICY_PATH)
        with pytest.raises(ap.PolicyChanged, match="re-open"):
            ap.require_hash(policy, "0" * 64)

    def test_adoption_record_pins_the_committed_policy(self) -> None:
        # Editing the policy without a successor adoption record fails here.
        adoption = json.loads(ADOPTION_RECORD.read_text(encoding="utf-8"))
        pinned = adoption["policy"]
        policy = ap.load(REPO / pinned["path"])
        assert pinned["schema"] == ap.SCHEMA
        assert pinned["policy_version"] == policy.version
        ap.require_hash(policy, pinned["sha256"])


# ---------------------------------------------------------------------------
# 2 and 3. Coverage of the handoff's table, with the fixture's ids
# ---------------------------------------------------------------------------


class TestCoverage:
    def test_category_ids_are_the_fixture_ids_in_order(self) -> None:
        policy = ap.load(ap.STARTING_POLICY_PATH)
        assert [c.id for c in policy.categories] == [cid for cid, _ in fx.CATEGORIES]

    def test_labels_are_the_handoff_rows(self) -> None:
        policy = ap.load(ap.STARTING_POLICY_PATH)
        assert [c.label for c in policy.categories] == [label for _, label in fx.CATEGORIES]

    def test_rules_follow_the_handoff_table(self) -> None:
        rules = {c.id: c.rule for c in ap.load(ap.STARTING_POLICY_PATH).categories}
        assert rules == {
            "person_name": "replace",
            "institution": "replace",
            "project_identity": "replace",
            "location": "generalise",
            "facility": "generalise",
            "dataset_cohort": "generalise",
            "grant": "generalise",
            "self_citation": "replace",
            "niche_topic": "flag",
            "identifying_number": "band",
            "identifying_figure": "operator_review",
        }

    def test_figures_need_operator_review_per_figure(self) -> None:
        figure = next(
            c for c in ap.load(ap.STARTING_POLICY_PATH).categories
            if c.id == "identifying_figure"
        )
        assert figure.review_unit == "per_figure"
        assert figure.auto_edit is False
        assert set(figure.permitted_actions) == {"redraw", "mask"}

    def test_citations_keep_count_and_position(self) -> None:
        citation = next(
            c for c in ap.load(ap.STARTING_POLICY_PATH).categories if c.id == "self_citation"
        )
        assert {"count", "position"} <= set(citation.retain)

    def test_o4_location_rule(self) -> None:
        # O4, as clarified by the operator on 2026-10-15: below country level is
        # generalised; the country and the participation status are kept.
        location = next(
            c for c in ap.load(ap.STARTING_POLICY_PATH).categories if c.id == "location"
        )
        assert location.rule == "generalise"
        assert {"country", "participation_status"} <= set(location.retain)

    def test_o3_thresholds(self) -> None:
        targets = {
            t["target"]: t
            for t in ap.load(ap.STARTING_POLICY_PATH).record["reidentification_threshold"]["targets"]
        }
        assert set(targets) == {
            "coordinating_institution", "partner", "supervisor",
            "country_set", "project_acronym", "research_group",
        }
        for name in ("coordinating_institution", "partner", "supervisor", "project_acronym"):
            assert targets[name]["max_correct_guesses"] == 0
        assert targets["country_set"]["guess_admissible"] is True
        # AN0 known gap: no threshold for the research group yet.
        assert targets["research_group"]["max_correct_guesses"] is None
        assert targets["research_group"]["declared_status"] == "Unresolved"

    def test_decisions_applied_point_at_the_an0_record(self) -> None:
        record = ap.load(ap.STARTING_POLICY_PATH).record
        applied = {d["decision"]: d for d in record["decisions_applied"]}
        assert {"O3", "O4"} <= set(applied)
        for entry in applied.values():
            assert (REPO / entry["record"]).is_file()


# ---------------------------------------------------------------------------
# 4. No real entity
# ---------------------------------------------------------------------------


def _strings(obj: Any) -> Iterator[str]:
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for key, value in obj.items():
            yield key
            yield from _strings(value)
    elif isinstance(obj, list):
        yield from (s for item in obj for s in _strings(item))


#: Every capitalised word the policy may use. Each is programme or document
#: vocabulary, a role or a pseudonym prefix, never a name. A new capitalised
#: word fails the test below until someone reviews it and adds it here.
POLICY_VOCABULARY: frozenset[str] = frozenset({
    # Programme and instrument terms (Tier 1 and Tier 2A).
    "EU", "Member", "State", "MSCA", "DN", "PhD", "Beneficiary", "Associated",
    "Partner", "Supervisor", "Table", "Implementation",
    # Document and file vocabulary.
    "PDF", "XMP", "DOI", "ORCID", "NMR",
    # Sentence starts and ordinary words that begin a field value.
    "A", "Any", "Cities", "Citation", "Countries", "Every", "Figures", "Institutions",
    "Named", "Niche", "No", "None", "Numbers", "Person", "Prior", "Project", "Scientific",
    "Self", "The", "Unique", "Zero", "Work", "Deliverable", "Timing", "Methods",
    "Confirmed", "Inferred", "Assumed", "Unresolved", "Handoff", "Operator", "Kept",
    "Replaced", "Rewrite", "Reference", "Same", "Each", "Keeping", "Generalised",
    "Banded", "Flagged", "Masked", "Redrawn", "Read", "Not", "Only", "Rewritten",
    "Initials", "Grant", "PIs",
    # Ticket ids of .scratch/msca-dn-anonymisation/tickets.md.
    "AN0", "AN8b",
    # The neutral citation marker's prefix.
    "R",
})

_CODE = re.compile(r"^[A-Z][0-9]+$")  # pseudonym codes and stage ids: S03, B2, A3, O4


class TestNamesNoRealEntity:
    def test_every_capitalised_word_is_policy_vocabulary(self) -> None:
        text = "\n".join(_strings(ap.load(ap.STARTING_POLICY_PATH).record))
        words = set(re.findall(r"[A-Za-z][A-Za-z0-9]*", text))
        capitalised = {w for w in words if w[0].isupper() and not _CODE.match(w)}
        assert capitalised - POLICY_VOCABULARY == set()

    def test_no_planted_entity_appears(self) -> None:
        # The fixture's invented entities stand in for the real ones.
        text = "\n".join(_strings(ap.load(ap.STARTING_POLICY_PATH).record)).casefold()
        for entity in fx.ENTITIES:
            assert entity["surface"].casefold() not in text, entity["id"]

    def test_no_contact_or_identifier_pattern_appears(self) -> None:
        text = "\n".join(_strings(ap.load(ap.STARTING_POLICY_PATH).record))
        assert not re.search(r"10\.\d{4,}/", text)  # DOI
        assert not re.search(r"\b\d{4}-\d{4}-\d{4}-\d{3}[\dX]\b", text)  # ORCID
        assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", text)  # e-mail
        assert not re.search(r"https?://", text)  # URL
        assert not re.search(r"\d{6,}", text)  # grant numbers, phone numbers
