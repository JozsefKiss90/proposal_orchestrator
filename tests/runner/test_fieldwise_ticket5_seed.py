"""FIELDWISE ticket 5 — consortium seed acceptance tests.

Pins the durable acceptance criteria of plans/fieldwise_tickets.md ticket 5:
roles.json defines the role tokens, partners.json covers every token the draft
work plan references, MATE / MVCRI / AgroVIR are Unresolved with their missing
fields named rather than guessed, capabilities.json is lifted verbatim from the
draft, and hand_lift_provenance.json covers the three files.

Read-only: these tests never write to docs/.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TIER3 = REPO_ROOT / "docs" / "tier3_project_instantiation"
CONSORTIUM = TIER3 / "consortium"
PROVENANCE = TIER3 / "hand_lift_provenance.json"

THREE_FILES = ["roles.json", "partners.json", "capabilities.json"]

VALID_STATUSES = {"Confirmed", "Inferred", "Assumed", "Unresolved"}

DRAFT_SOURCE = (
    "docs/tier3_project_instantiation/source_materials/part_b_draft_v0/"
    "FIELDWISE_MSCA_Master_Draft.docx"
)

#: The six tokens the ticket names, plus CO_SUPERVISOR, which operator input
#: pack item 7 instructed ticket 5 to add (deviation recorded in the lift log).
TICKET_TOKENS = [
    "FELLOW",
    "HOST",
    "SUPERVISOR",
    "DATA_PARTNER",
    "TRANSFER_PARTNER",
    "VALIDATION_PARTNER",
]
ALL_TOKENS = TICKET_TOKENS + ["CO_SUPERVISOR"]

#: The three organisations item 1 and item 2 still block at ticket 5.
UNRESOLVED_PARTICIPANTS = {
    "DATA_PARTNER": "MATE",
    "TRANSFER_PARTNER": "MVCRI",
    "VALIDATION_PARTNER": "AgroVIR",
}

#: Fields that must exist and be null on the three Unresolved participants —
#: named as missing, never guessed (§13.3).
MUST_BE_NULL = ["legal_name", "pic", "entity_type", "contact_person", "participation_mode"]


def _load(name: str) -> dict:
    path = CONSORTIUM / name
    assert path.is_file(), f"{name} does not exist"
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _iter_status_records(obj, path="$"):
    """Yield (json_path, record) for every dict carrying validation_status."""
    if isinstance(obj, dict):
        if "validation_status" in obj:
            yield path, obj
        for key, value in obj.items():
            yield from _iter_status_records(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from _iter_status_records(item, f"{path}[{i}]")


class TestEnvelope:
    @pytest.mark.parametrize("name", THREE_FILES)
    def test_file_exists_with_section5_envelope(self, name):
        data = _load(name)
        prov = data.get("_provenance")
        assert isinstance(prov, dict), f"{name} missing _provenance envelope"
        assert prov.get("source") == DRAFT_SOURCE
        assert "lift_record" in prov and "fieldwise-tier3-lift" in prov["lift_record"]
        assert prov.get("provenance_manifest") == (
            "docs/tier3_project_instantiation/hand_lift_provenance.json"
        )
        assert any("CLAUDE.md" in a for a in prov.get("authority", []))

    @pytest.mark.parametrize("name", THREE_FILES)
    def test_every_record_carries_exactly_one_valid_status(self, name):
        data = _load(name)
        records = list(_iter_status_records(data))
        assert records, f"{name} carries no status-bearing records"
        for path, record in records:
            status = record["validation_status"]
            assert status in VALID_STATUSES, f"{name} {path}: bad status {status!r}"

    @pytest.mark.parametrize("name", THREE_FILES)
    def test_non_confirmed_records_state_why(self, name):
        data = _load(name)
        for path, record in _iter_status_records(data):
            if record["validation_status"] != "Confirmed":
                assert record.get("note", "").strip(), (
                    f"{name} {path}: {record['validation_status']} record has no note "
                    "(plan §5 requires one on anything not Confirmed)"
                )

    @pytest.mark.parametrize("name", THREE_FILES)
    def test_confirmed_records_cite_a_source(self, name):
        data = _load(name)
        for path, record in _iter_status_records(data):
            if record["validation_status"] == "Confirmed":
                assert record.get("source_ref", "").strip(), (
                    f"{name} {path}: Confirmed record has no source_ref"
                )


class TestRoles:
    def test_defines_the_six_ticket_tokens_plus_co_supervisor(self):
        roles = {r["role_token"] for r in _load("roles.json")["roles"]}
        assert set(TICKET_TOKENS) <= roles
        assert roles == set(ALL_TOKENS)

    def test_identity_spine_is_confirmed_and_cites_input_pack_item_7(self):
        """The draft names no person; item 7 is the only source for these."""
        roles = {r["role_token"]: r for r in _load("roles.json")["roles"]}
        for token in ("FELLOW", "SUPERVISOR", "CO_SUPERVISOR"):
            record = roles[token]
            assert record["validation_status"] == "Confirmed", token
            assert record.get("identity", "").strip(), token
            assert "item 7" in record["source_ref"], token

    def test_host_is_draft_confirmed_and_carries_the_c5_conditionality(self):
        host = next(
            r for r in _load("roles.json")["roles"] if r["role_token"] == "HOST"
        )
        assert host["validation_status"] == "Confirmed"
        assert host["country_code"] == "HU"
        assert "¶425" in host["source_ref"]
        assert "C5" in host["note"]

    def test_every_role_carries_a_checklist_ref_for_ticket_6(self):
        for record in _load("roles.json")["roles"]:
            assert record.get("checklist_ref", "").strip(), record["role_token"]


class TestPartners:
    def test_covers_every_token_referenced_by_the_draft_work_plan(self):
        partners = {p["partner_id"] for p in _load("partners.json")["partners"]}
        assert partners == set(ALL_TOKENS)

    def test_partner_ids_match_role_tokens(self):
        roles = {r["role_token"] for r in _load("roles.json")["roles"]}
        partners = {p["partner_id"] for p in _load("partners.json")["partners"]}
        assert partners == roles, "partners.json must be derived from roles.json"

    def test_host_is_the_sole_beneficiary(self):
        partners = {p["partner_id"]: p for p in _load("partners.json")["partners"]}
        assert partners["HOST"]["beneficiary"] is True
        for pid, record in partners.items():
            if pid != "HOST":
                assert record["beneficiary"] is False, pid

    def test_g04_p07_can_resolve_every_seeded_partner_id(self):
        """The gate predicate's own extractor must see all seven ids."""
        from runner.predicates.coverage_predicates import _extract_partner_ids

        path = CONSORTIUM / "partners.json"
        with path.open(encoding="utf-8") as fh:
            parsed = json.load(fh)
        ids, err = _extract_partner_ids(parsed, path)
        assert err is None, err
        assert ids == set(ALL_TOKENS)


class TestNothingGuessed:
    """What the lift may not do, whether or not the fold has run.

    Ticket 5 left MATE, MVCRI and AgroVIR Unresolved with their missing fields
    named. Ticket 6 folds operator input pack items 1 and 2 and resolves them,
    so the Unresolved state is no longer what these tests can assert; the
    resolved state is pinned by test_fieldwise_ticket6_fold.py. What stays
    true of the lift is that every value on those records is sourced: the
    draft's own facts still stand, and anything the draft cannot supply cites
    the operator pack rather than appearing unattributed.
    """

    @pytest.mark.parametrize("token,short_name", sorted(UNRESOLVED_PARTICIPANTS.items()))
    def test_three_participants_keep_their_draft_short_names(self, token, short_name):
        roles = {r["role_token"]: r for r in _load("roles.json")["roles"]}
        partners = {p["partner_id"]: p for p in _load("partners.json")["partners"]}
        for record in (roles[token], partners[token]):
            assert record["short_name"] == short_name, token
            assert record["validation_status"] in VALID_STATUSES, token

    @pytest.mark.parametrize("token", sorted(UNRESOLVED_PARTICIPANTS))
    def test_missing_fields_are_named_and_never_unattributed(self, token):
        partner = next(
            p for p in _load("partners.json")["partners"] if p["partner_id"] == token
        )
        for field in MUST_BE_NULL:
            assert field in partner, f"{token}: {field} is not named"
            if partner[field] is None:
                continue
            # A filled field is the ticket 6 fold and must cite the operator
            # pack, which is the only authority for anything the draft lacks.
            assert "input pack" in partner["source_ref"].lower(), (
                f"{token}: {field} carries a value with no operator source"
            )

    @pytest.mark.parametrize("token", sorted(UNRESOLVED_PARTICIPANTS))
    def test_notes_tie_the_record_to_the_input_pack_items(self, token):
        partner = next(
            p for p in _load("partners.json")["partners"] if p["partner_id"] == token
        )
        blob = partner["note"] + partner["source_ref"]
        assert "item 1" in blob or "items 1 and 2" in blob, token
        assert "item 2" in blob or "items 1 and 2" in blob, token

    @pytest.mark.parametrize("token", sorted(UNRESOLVED_PARTICIPANTS))
    def test_draft_confirmed_facts_are_still_stated(self, token):
        """The draft's own facts survive the fold (plan §5)."""
        role = next(
            r for r in _load("roles.json")["roles"] if r["role_token"] == token
        )
        assert role["country_code"] in {"HU", "BG"}, token
        assert role["function"].strip(), token
        assert role["work_plan_role"].strip(), token


class TestCapabilities:
    def test_two_way_transfer_lists_are_lifted_from_section_1_3(self):
        data = _load("capabilities.json")
        transfers = {t["transfer_id"]: t for t in data["knowledge_transfer"]}
        assert set(transfers) == {"KT1", "KT2", "KT3"}
        assert len(transfers["KT1"]["competences"]) == 11
        assert len(transfers["KT2"]["competences"]) == 9
        assert "¶183-194" in transfers["KT1"]["source_ref"]
        assert "¶195-204" in transfers["KT2"]["source_ref"]

    def test_capacity_statements_cover_all_four_organisations(self):
        data = _load("capabilities.json")
        tokens = {c["role_token"] for c in data["capacity_statements"]}
        assert tokens == {
            "HOST", "DATA_PARTNER", "TRANSFER_PARTNER", "VALIDATION_PARTNER",
        }
        for record in data["capacity_statements"]:
            assert "§3.2" in record["source_ref"], record["capacity_id"]

    def test_partner_contributions_cover_the_three_participants(self):
        data = _load("capabilities.json")
        tokens = {c["role_token"] for c in data["partner_contributions"]}
        assert tokens == set(UNRESOLVED_PARTICIPANTS)

    def test_part_b2_capacity_detail_is_unresolved_not_invented(self):
        detail = _load("capabilities.json")["part_b2_capacity_detail"]
        assert detail["validation_status"] == "Unresolved"
        assert "item 12" in detail["note"]
        assert detail["deferred_fields_named_by_the_operator"]

    def test_every_lifted_string_is_verbatim_draft_text(self):
        """Character-for-character check against the master draft."""
        docx = pytest.importorskip("docx")
        from docx.table import Table
        from docx.text.paragraph import Paragraph

        draft_path = REPO_ROOT / DRAFT_SOURCE
        if not draft_path.is_file():
            pytest.skip("master draft not present")

        document = docx.Document(str(draft_path))
        paragraphs: set[str] = set()
        for child in document.element.body.iterchildren():
            tag = child.tag.split("}")[-1]
            if tag == "p":
                text = Paragraph(child, document).text.strip()
                if text:
                    paragraphs.add(text)
            elif tag == "tbl":
                for row in Table(child, document).rows:
                    for cell in row.cells:
                        for para in cell.paragraphs:
                            text = para.text.strip()
                            if text:
                                paragraphs.add(text)

        data = _load("capabilities.json")
        lifted: list[str] = []
        for transfer in data["knowledge_transfer"]:
            lifted.extend(transfer.get("competences", []))
            if "statement" in transfer:
                lifted.append(transfer["statement"])
        for key in ("partner_contributions", "capacity_statements", "training_and_career"):
            for record in data[key]:
                lifted.append(record["statement"])
                if "heading" in record:
                    lifted.append(record["heading"])

        missing = [s for s in lifted if s not in paragraphs]
        assert not missing, f"{len(missing)} string(s) are not verbatim draft text: {missing[:3]}"


class TestProvenanceManifest:
    def test_manifest_covers_all_three_files(self):
        with PROVENANCE.open(encoding="utf-8") as fh:
            manifest = json.load(fh)
        entries = [
            entry for entry in manifest["lifted_artifacts"]
            if entry["artifact"].startswith("consortium/")
        ]
        assert {e["artifact"].split("/")[-1] for e in entries} == set(THREE_FILES)
        for entry in entries:
            assert entry["ticket"] == 5
            assert entry["source_refs"]
            assert entry["validation_status_summary"].strip()

    def test_lift_record_carries_the_ticket_5_extension(self):
        record = (
            REPO_ROOT / "docs" / "tier4_orchestration_state" / "decision_log"
            / "fieldwise-tier3-lift_2026-08-11.json"
        )
        with record.open(encoding="utf-8") as fh:
            data = json.load(fh)
        extension = next(e for e in data["extensions"] if e["ticket"] == 5)
        assert set(extension["artifacts_written"]) == {
            f"docs/tier3_project_instantiation/consortium/{name}"
            for name in THREE_FILES
        }
        assert extension["co_supervisor_deviation"]["why"].strip()
        assert extension["input_pack_correction"]["evidence"].strip()
